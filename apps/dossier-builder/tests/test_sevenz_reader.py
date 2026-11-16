"""The program's own 7z reader (ui/assets/sevenz.js), run in Chromium the way the page runs it: in a worker, and on the page's own
thread where a worker cannot be made. Every archive must give exactly the files that were packed (their sizes and SHA-256), or say
why it does not — and archive.js must take the documents, or hand the archive to the machine's own unpacker where there is one.
The archives are made for these tests by 7-Zip from made-up «Dermacure» documents (skipped where 7-Zip is not installed): its
default (LZMA2, the x86 filter for programs, a packed header), LZMA, each file by itself with a plain header, stored, the delta
filter, BCJ + LZMA, PPMd (not read in the page), a password on the files, a password on the names, and an archive split in parts."""
import hashlib, json, pathlib, random, shutil, subprocess
import pytest
from test_ui_e2e import server, browser          # noqa: F401  (the module's live server and Chromium)

DATA = pathlib.Path(__file__).parent / 'data' / 'archives'
SEVEN = shutil.which('7z') or shutil.which('7za') or shutil.which('7zz')
needs_7zip = pytest.mark.skipif(not SEVEN, reason='7-Zip is not installed: the test archives cannot be made')

KINDS = {                                         # archive → 7-Zip's switches, and a method the reader must really have used
    'default.7z': ([], 'LZMA2'),
    'lzma.7z': (['-m0=LZMA'], 'LZMA'),
    'nonsolid.7z': (['-ms=off', '-mhc=off'], 'LZMA2'),
    'copy.7z': (['-mx=0'], 'Copy'),
    'delta.7z': (['-mf=Delta:4'], 'Delta'),
    'bcj.7z': (['-m0=BCJ', '-m1=LZMA'], 'BCJ'),
    'ppmd.7z': (['-m0=PPMd'], None),
    'pass.7z': (['-pDermacure1'], None),
    'passnames.7z': (['-pDermacure1', '-mhe=on'], None),
    'split.7z': (['-v300k'], None),
}

RUN = """async (opts) => {
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  const files = [...document.querySelector('#fxin').files];
  try {
    const r = await DB7Z.extract(files, opts || {});
    const out = {};
    for (const f of r.files) { const d = await new Blob(f.parts).arrayBuffer(); out[f.name] = [d.byteLength, hex(await crypto.subtle.digest('SHA-256', d))]; }
    return {files: out, skipped: Object.fromEntries(r.skipped.map(s => [s.name, s.why])), methods: Object.keys(r.methods || {}), thread: r.thread, left: r.left};
  } catch (e) { return {error: (e && e.z7) || String(e)}; } }"""

EXPAND = """async () => {
  const hex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
  const r = await DBARCH.expand([...document.querySelector('#fxin').files], {});
  const out = {};
  for (const f of r.files) { const d = await f.arrayBuffer(); out[f.dbPath] = [d.byteLength, hex(await crypto.subtle.digest('SHA-256', d))]; }
  return {files: out, notes: r.notes, summary: DBARCH.summary(r.notes)}; }"""


@pytest.fixture(scope='module')
def made(tmp_path_factory):
    """made-up documents, and every kind of archive 7-Zip makes of them"""
    if not SEVEN:
        pytest.skip('7-Zip is not installed')
    root = tmp_path_factory.mktemp('sevenz')
    src, out = root / 'src', root / 'out'
    (src / 'Module 1').mkdir(parents=True); (src / 'فارغ').mkdir(); out.mkdir()
    rnd = random.Random(7)
    (src / 'Module 1' / 'pricing certificate.txt').write_text('Dermacure 20 mg — pricing certificate (made up)\n' * 3, encoding='utf-8')
    (src / 'ثبات الدواء.txt').write_text('دراسة ثبات مختلقة لمنتج ديرماكيور\n' * 4000, encoding='utf-8')
    (src / 'random.bin').write_bytes(bytes(rnd.getrandbits(8) for _ in range(600_000)))        # cannot be packed: LZMA2 keeps it as it is
    (src / 'specification.txt').write_text(''.join(f'line {i} of a made-up specification, assay {rnd.randint(90, 110)}%\n' for i in range(60_000)))
    (src / 'empty.txt').write_bytes(b'')
    code = bytearray()
    for i in range(20_000):
        code += bytes([0xE8]) + (i * 37).to_bytes(4, 'little') + bytes([0x90, 0x55, 0x89, 0xE5])
    (src / 'tool.exe').write_bytes(bytes(code))                                                 # calls for the x86 filter
    want = {p.relative_to(src).as_posix(): [p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()] for p in src.rglob('*') if p.is_file()}
    for name, (switches, _) in KINDS.items():
        subprocess.run([SEVEN, 'a', '-bd', '-y', *switches, str(out / name), '.'], cwd=src, check=True, capture_output=True)
    return {'src': src, 'out': out, 'want': want}


def _page(browser, server, init=''):
    page = browser.new_page()
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en');" + init)
    page.goto(server + '/#/')
    page.wait_for_function("() => window.DB7Z && window.DBARCH")
    page.evaluate("() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'fxin'; i.multiple = true; document.body.appendChild(i); }")
    return page


def _read(page, paths, opts=None):
    page.set_input_files('#fxin', [str(p) for p in paths])
    return page.evaluate(RUN, opts or {})


@needs_7zip
@pytest.mark.parametrize('name', ['default.7z', 'lzma.7z', 'nonsolid.7z', 'copy.7z', 'delta.7z', 'bcj.7z'])
def test_the_readers_output_is_the_files_that_were_packed(server, browser, made, name):
    page = _page(browser, server)
    got = _read(page, [made['out'] / name])
    assert 'error' not in got, got
    assert got['files'] == made['want'], (sorted(got['files']), got['skipped'])                  # every file, byte for byte; no folder, no extra
    assert KINDS[name][1] in got['methods'], got['methods']                                       # the method was really used
    assert got['thread'] == 'worker'                                                              # the page keeps answering
    assert page.errors == [], page.errors
    page.close()


@needs_7zip
def test_without_a_worker_the_same_reader_runs_on_the_page(server, browser, made):
    page = _page(browser, server, 'window.Worker = undefined;')
    got = _read(page, [made['out'] / 'default.7z'])
    assert got['files'] == made['want'] and got['thread'] == 'page', got.get('skipped')
    page.close()


def test_the_7z_kept_with_the_tests_gives_what_7zip_gives(server, browser):
    page = _page(browser, server)
    got = _read(page, [DATA / 'dermacure.7z'])
    assert sorted(got['files']) == ['Module 1/pricing certificate.txt', 'ثبات.txt'], got
    if SEVEN:
        listing = subprocess.run([SEVEN, 'l', '-slt', str(DATA / 'dermacure.7z')], capture_output=True, text=True, check=True).stdout
        blocks = [dict(line.split(' = ', 1) for line in b.splitlines() if ' = ' in line) for b in listing.split('\n\n')]
        sizes = {d['Path'].removeprefix('./'): int(d['Size']) for d in blocks if 'Path' in d and d.get('Size', '').isdigit() and 'D' not in d.get('Attributes', '')}   # kept as «./name»: the reader drops «./»
        assert {k: v[0] for k, v in got['files'].items()} == {k: v for k, v in sizes.items() if k in got['files']}
    page.close()


@needs_7zip
def test_what_the_page_does_not_read_is_said_with_its_reason(server, browser, made):
    page = _page(browser, server)
    real = {k for k, v in made['want'].items() if v[0]}
    ppmd = _read(page, [made['out'] / 'ppmd.7z'])
    assert set(ppmd['skipped']) == real and set(ppmd['skipped'].values()) == {'unsupported'}, ppmd     # PPMd: named, never half-read
    pw = _read(page, [made['out'] / 'pass.7z'])
    assert set(pw['skipped']) == real and set(pw['skipped'].values()) == {'password'}, pw            # a password is reported, never guessed
    assert _read(page, [made['out'] / 'passnames.7z']) == {'error': 'password'}                        # even the names are under the password
    assert _read(page, [made['out'] / 'split.7z.001']) == {'error': 'volume'}                          # one part of several
    page.close()


@needs_7zip
def test_a_file_that_does_not_match_its_checksum_is_never_handed_over(server, browser, made):
    page = _page(browser, server)
    page.set_input_files('#fxin', str(made['out'] / 'copy.7z'))
    got = page.evaluate("""async () => {
      const f = document.querySelector('#fxin').files[0], d = new Uint8Array(await f.arrayBuffer());
      const at = new TextDecoder('latin1').decode(d).indexOf('pricing certificate (made up)');      // stored: the document's own bytes are in the archive
      d[at + 3] ^= 0x20;                                                                            // one letter changed
      const r = await DB7Z.extract([new File([d], 'changed.7z')], {});
      return {at, names: r.files.map(x => x.name), skipped: Object.fromEntries(r.skipped.map(s => [s.name, s.why]))}; }""")
    assert got['at'] > 0 and got['skipped'] == {'Module 1/pricing certificate.txt': 'unreadable'}, got
    assert 'Module 1/pricing certificate.txt' not in got['names'] and len(got['names']) == len(made['want']) - 1     # the others are still given
    page.close()


@needs_7zip
def test_cut_short_or_not_a_7z_at_all(server, browser, made):
    page = _page(browser, server)
    page.set_input_files('#fxin', str(made['out'] / 'default.7z'))
    got = page.evaluate("""async () => {
      const d = new Uint8Array(await document.querySelector('#fxin').files[0].arrayBuffer()), out = {};
      const run = async (name, bytes) => { try { const r = await DB7Z.extract([new File([bytes], name)], {}); out[name] = {files: r.files.length, skipped: r.skipped.map(s => s.why)}; } catch (e) { out[name] = {error: e.z7 || String(e)}; } };
      await run('half.7z', d.slice(0, d.length >> 1));                                              // a download that stopped
      const noise = d.slice(); for (let i = 40; i < noise.length - 200; i += 7) noise[i] ^= 0x5a;    // the packed data spoilt, the header whole
      await run('noise.7z', noise);
      await run('text.7z', new TextEncoder().encode('this is not an archive'));
      return out; }""")
    assert got['half.7z'] == {'error': 'volume'}, got                                               # said as incomplete, nothing invented
    assert got['noise.7z'].get('error') in ('damaged', 'unreadable') or (got['noise.7z']['files'] <= 1 and got['noise.7z']['skipped']), got
    assert got['text.7z'] == {'error': 'damaged'}, got
    page.close()


@needs_7zip
def test_only_the_names_worth_taking_are_handed_over(server, browser, made):
    page = _page(browser, server)
    got = _read(page, [made['out'] / 'nonsolid.7z'], {'keepRx': r'\.txt$'})
    assert set(got['files']) == {k for k in made['want'] if k.endswith('.txt')}, got
    assert got['left'] == 2                                                                         # random.bin and tool.exe stay packed
    page.close()


def test_an_archive_that_expands_hundreds_of_times_is_refused(server, browser, tmp_path):
    if not SEVEN:
        pytest.skip('7-Zip is not installed')
    zeros = tmp_path / 'zeros.bin'
    with open(zeros, 'wb') as f:
        for _ in range(110):
            f.write(bytes(1024 * 1024))
    subprocess.run([SEVEN, 'a', '-bd', '-y', str(tmp_path / 'bomb.7z'), str(zeros)], check=True, capture_output=True)
    page = _page(browser, server)
    assert _read(page, [tmp_path / 'bomb.7z']) == {'error': 'big'}                                  # refused before anything is unpacked
    page.close()


@needs_7zip
def test_the_page_takes_the_documents_from_a_7z(server, browser, made):
    page = _page(browser, server)
    page.set_input_files('#fxin', [str(made['out'] / 'default.7z')])
    got = page.evaluate(EXPAND)
    assert got['files'] == made['want'], sorted(got['files'])
    assert '«default.7z» unpacked — documents taken: 6' in got['summary'], got['summary']
    page.close()


@needs_7zip
def test_what_the_page_does_not_read_goes_to_the_machines_unpacker(server, browser, made):
    page = _page(browser, server)                                                                   # the desktop and server editions: no DBWEB
    page.set_input_files('#fxin', [str(made['out'] / 'ppmd.7z')])
    got = page.evaluate(EXPAND)
    assert got['files'] == made['want'], got['summary']                                             # 7-Zip on the machine read PPMd
    page.close()


@needs_7zip
def test_in_the_browser_edition_what_it_does_not_read_is_refused_with_the_reason(server, browser, made):
    page = _page(browser, server, 'window.DBWEB = true;')                                           # the claude.ai edition has no unpacker of its own
    page.set_input_files('#fxin', [str(made['out'] / 'ppmd.7z'), str(made['out'] / 'pass.7z')])
    got = page.evaluate(EXPAND)
    assert got['files'] == {}, got
    assert 'compression method this page does not read (PPMd)' in got['summary'], got['summary']
    assert 'protected with a password' in got['summary'], got['summary']
    page.close()
