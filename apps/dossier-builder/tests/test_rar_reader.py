"""The program's own RAR reader (ui/assets/rar.js), run in Chromium the way the page runs it: in a worker, and on the page's own
thread where a worker cannot be made. Every archive must give exactly the files the original unpacker gives (their sizes and SHA-256
were recorded from it), or say why it does not.
- tests/data/archives/rar/*.rar: made for these tests with RAR 7.00 from made-up «Dermacure» documents (RAR5: normal, solid, stored,
  split in four parts, the delta and x86 filters, a password on the files, a password on the names).
- web/vendor/arch/test: libarchive's public test archives (web/vendor.sh), skipped when absent — the old format (RAR 2.9–4.x) with
  its filters and the text method of «Best» compression, names in Unicode, links, a self-extracting archive, split and solid
  archives, and damaged ones that must be refused without a crash or a hang."""
import json, pathlib
import pytest
from test_ui_e2e import server, browser          # noqa: F401  (the module's live server and Chromium)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = pathlib.Path(__file__).parent / 'data' / 'archives' / 'rar'
PUBLIC = ROOT / 'web' / 'vendor' / 'arch' / 'test'
OWN = json.loads((DATA / 'expected.json').read_text(encoding='utf-8'))
PUB = json.loads((DATA / 'public-expected.json').read_text(encoding='utf-8'))

RUN = """async (opts) => {
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  const files = [...document.querySelector('#fxin').files].sort((a, b) => a.name.localeCompare(b.name, undefined, {numeric: true}));
  try {
    const r = await DBRAR.extract(files, opts || {});
    const out = {};
    for (const f of r.files) { const d = await new Blob(f.parts).arrayBuffer(); out[f.name] = [d.byteLength, hex(await crypto.subtle.digest('SHA-256', d))]; }
    return {files: out, skipped: Object.fromEntries(r.skipped.map(s => [s.name, s.why])), format: r.format, filters: Object.keys(r.filters || {}), thread: r.thread, left: r.left};
  } catch (e) { return {error: (e && e.rar) || String(e)}; } }"""


def _page(browser, server, init=''):
    page = browser.new_page()
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en');" + init)
    page.goto(server + '/#/')
    page.wait_for_function("() => window.DBRAR && window.DBARCH")
    page.evaluate("() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'fxin'; i.multiple = true; document.body.appendChild(i); }")
    return page


def _read(page, folder, vols, opts=None):
    page.set_input_files('#fxin', [str(folder / v) for v in vols])
    return page.evaluate(RUN, opts or {})


def _same(got, want):
    if want.get('error'):
        assert got.get('error') == want['error'], got
        return
    assert 'error' not in got, got
    assert got['files'] == {k: v for k, v in want['files'].items()}, (sorted(got['files']), got['skipped'])        # every file, byte for byte
    for name, why in (want.get('skipped') or {}).items():
        assert got['skipped'].get(name) == why, got['skipped']
    if want.get('format'):
        assert got['format'] == want['format']
    for kind in want.get('filters') or []:
        assert kind in got['filters'], got['filters']                                                               # the filter was really used


@pytest.mark.parametrize('key', sorted(OWN))
def test_the_readers_output_is_the_original_files(server, browser, key):
    page = _page(browser, server)
    got = _read(page, DATA, OWN[key]['vols'])
    _same(got, OWN[key])
    if not OWN[key].get('error'):
        assert got['thread'] == 'worker'                                                 # the page keeps answering: the work is not on its thread
    assert page.errors == [], page.errors
    page.close()


@pytest.mark.parametrize('key', ['dermacure-solid.rar', 'dermacure-parts', 'dermacure-delta.rar'])
def test_without_a_worker_the_same_reader_runs_on_the_page(server, browser, key):
    page = _page(browser, server, "window.Worker = undefined;")
    got = _read(page, DATA, OWN[key]['vols'])
    _same(got, OWN[key])
    assert got['thread'] == 'page'
    page.close()


@pytest.mark.parametrize('key', sorted(PUB))
def test_public_archives_old_and_new(server, browser, key):
    want = PUB[key]
    if not all((PUBLIC / v).exists() for v in want['vols']):
        pytest.skip('public RAR samples not fetched (web/vendor.sh)')
    page = _page(browser, server)
    got = _read(page, PUBLIC, want['vols'], {'maxTotal': 2 ** 31, 'maxFile': 2 ** 31})
    _same(got, want)
    if not want['files'] and not want.get('error'):
        assert not got.get('files')                                                      # a damaged archive gives nothing — and neither crashes nor hangs
    assert page.errors == [], page.errors
    page.close()


def test_a_part_that_is_missing_is_said(server, browser):
    page = _page(browser, server)
    got = _read(page, DATA, ['dermacure-parts.part01.rar', 'dermacure-parts.part02.rar'])       # two of the four parts
    assert 'error' not in got and 'volume' in got['skipped'].values(), got                        # the file cut by the missing part is named, not half-given
    whole = OWN['dermacure-parts']['files']
    assert got['files'] and all(whole[k] == v for k, v in got['files'].items())                  # what the two parts hold whole is right
    page.close()


def test_a_file_that_does_not_match_its_checksum_is_never_handed_over(server, browser):
    page = _page(browser, server)
    page.set_input_files('#fxin', str(DATA / 'dermacure-stored.rar'))
    got = page.evaluate("""async () => {
      const f = document.querySelector('#fxin').files[0], d = new Uint8Array(await f.arrayBuffer());
      const at = new TextDecoder('latin1').decode(d).indexOf('Pricing Certificate');             // stored: the document's own bytes are in the archive
      d[at + 3] ^= 0x20;                                                                          // one letter changed
      const r = await DBRAR.extract([new File([d], 'changed.rar')], {});
      return {at, names: r.files.map(x => x.name), skipped: Object.fromEntries(r.skipped.map(s => [s.name, s.why]))}; }""")
    assert got['at'] > 0 and got['skipped'] == {'Module 1/pricing certificate.txt': 'unreadable'}, got
    assert 'Module 1/pricing certificate.txt' not in got['names'] and len(got['names']) == 2      # the others are still given
    page.close()


def test_cut_short_or_not_a_rar_at_all(server, browser):
    page = _page(browser, server)
    page.set_input_files('#fxin', str(DATA / 'dermacure.rar'))
    got = page.evaluate("""async () => {
      const d = new Uint8Array(await document.querySelector('#fxin').files[0].arrayBuffer()), out = {};
      const run = async (name, bytes) => { try { const r = await DBRAR.extract([new File([bytes], name)], {}); out[name] = {files: r.files.length, skipped: r.skipped.map(s => s.why)}; } catch (e) { out[name] = {error: e.rar || String(e)}; } };
      await run('half.rar', d.slice(0, d.length >> 1));                                           // a download that stopped
      await run('noise.rar', new Uint8Array([0x52, 0x61, 0x72, 0x21, 0x1a, 0x07, 0x01, 0x00].concat(Array.from({length: 3000}, (_, i) => (i * 131 + 7) & 255))));
      await run('text.rar', new TextEncoder().encode('this is not an archive'));
      return out; }""")
    assert 'error' not in got['half.rar'] and got['half.rar']['files'] < 5, got                   # what was whole is kept; nothing invented
    assert got['noise.rar'] in ({'files': 0, 'skipped': []}, {'error': 'damaged'}), got
    assert got['text.rar'] == {'error': 'damaged'}, got
    page.close()


def test_limits_and_the_files_worth_taking(server, browser):
    page = _page(browser, server)
    got = _read(page, DATA, ['dermacure.rar'], {'keepRx': r'\.(txt|pdf)$', 'skipRx': r'(^|/)notes\.txt$'})
    assert sorted(got['files']) == ['Module 1/pricing certificate.txt', 'licence.pdf', 'ثبات/تقرير الثبات.txt'] and got['left'] == 1, got      # scan.bin is not unpacked at all
    assert _read(page, DATA, ['dermacure.rar'], {'maxFiles': 2}) == {'error': 'big'}
    assert _read(page, DATA, ['dermacure.rar'], {'maxTotal': 5000}) == {'error': 'big'}
    got = _read(page, DATA, ['dermacure-solid.rar'], {'maxFile': 5000})                            # a solid archive: the large files are passed over, the rest still come out right
    assert got['skipped'] == {'notes.txt': 'too large', 'scan.bin': 'too large'} and len(got['files']) == 3, got
    assert all(OWN['dermacure-solid.rar']['files'][k] == v for k, v in got['files'].items())
    page.close()
