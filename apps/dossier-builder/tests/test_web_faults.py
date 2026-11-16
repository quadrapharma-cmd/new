"""The browser edition says what went wrong, and keeps it (eBOX stage 1, 16/11/2026 — the owner met «اخطاء كتير و رسايل اخطاء»):
a download never fails without a word, a kind claude.ai does not save travels in a ZIP, an error's note is marked and written into
the faults record («سجل الأعطال»), a page's picture is shown where there is no server, and the page opens without a script error.
Each of these was silent, empty or broken in version 50. Needs `python3 web/build.py` first; skipped when dist is absent."""
import functools, http.server, io, os, pathlib, re, socket, threading, zipfile
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(os.environ.get('DB_DIST') or pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist')      # DB_DIST=<folder>: the page as claude.ai serves it, read back after a publish
OFFICE = pathlib.Path(__file__).parent / 'data' / 'office'
pytestmark = pytest.mark.skipif(not (DIST / 'index.html').exists(), reason='web/dist not built')
POLICY = ["default-src 'self'", "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'", "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
          "font-src https://fonts.gstatic.com", "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "frame-src 'none'", "object-src 'none'"]
# claude.ai's viewer, as far as the page can tell: Claude and the downloads are capabilities; a dialog is never shown
CLAUDE = """
window.__saved = []; window.__dl = 'ok';
(() => {
  const downloads = { save: async ({ filename, data }) => {
    if (window.__dl !== 'ok') { const e = new Error(window.__dl); e.code = window.__dl; throw e; }
    window.__saved.push({ filename, bytes: Array.from(new Uint8Array(await data.arrayBuffer())) }); } };
  const sample = async () => ({ text: '{}', truncated: false }); sample.json = async () => ({}); sample.limits = async () => ({ maxPromptBytes: 262144 });
  window.claude = { use: async n => (n === 'downloads' ? downloads : n === 'sample' ? sample : null) };
  window.confirm = () => false; window.prompt = () => null;
})();
"""
NEW = """async () => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
  body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
  product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id"""
PUT = """async ([id, slot, name, data]) => { const fd = new FormData(); fd.append('file', new File([new Uint8Array(data)], name)); fd.append('meta', '{}');
  const r = await fetch(`/api/dossiers/${id}/slots/${encodeURIComponent(slot)}/documents`, {method: 'POST', body: fd}); return [r.status, (await r.json()).id]; }"""
CLICK = "href => { const a = document.createElement('a'); a.href = href; a.textContent = 'x'; document.body.appendChild(a); a.click(); a.parentNode.removeChild(a); }"
TOAST = "() => (t => t && !t.hidden ? {text: t.textContent, bad: t.classList.contains('bad')} : null)(document.getElementById('toast'))"


@pytest.fixture(scope='module')
def site():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8'}

        def end_headers(self):
            self.send_header('Content-Security-Policy', '; '.join(POLICY))
            super().end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


def opened(p, site, errors, lang='ar', fonts=True, grant=()):
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1440, 'height': 900})
    if grant:
        ctx.grant_permissions(list(grant))
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    page.on('response', lambda r: errors.append(f'http {r.status} {r.url}') if r.status >= 400 else None)
    if fonts:
        page.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(status=200, content_type='text/css', body='/* fonts */'))
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    page.add_init_script(CLAUDE)
    page.goto(site + '/index.html#/')
    page.wait_for_selector('#boot', state='detached', timeout=240000)
    page.evaluate('() => DBWEB.ready()')
    return b, page


def dossier(page, files):
    did = page.evaluate(NEW)
    slots = [s['slot_id'] for s in page.evaluate("async id => (await (await fetch(`/api/dossiers/${id}/board`)).json())", did)['slots']
             if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents']]
    ids = {}
    for f, slot in zip(files, slots):
        st, doc = page.evaluate(PUT, [did, slot, f.name, list(f.read_bytes())])
        assert st == 201, (f.name, st)
        ids[f.name] = doc
    return did, ids


def test_the_page_opens_without_a_script_error_and_takes_its_fonts(site):
    with pw.sync_playwright() as p:
        errors = []
        b, page = opened(p, site, errors)
        assert page.title() == 'eBOX'
        page.wait_for_function("() => document.getElementById('dbFonts').media === 'all'", timeout=10000)     # the fonts' sheet is applied once it has come…
        assert errors == [], errors                                                                            # …and nothing was thrown on the way (version 50: a script error at every opening)
        html = (DIST / 'index.html').read_text(encoding='utf-8')
        assert not re.search(r'(?<![\w.$])(?:confirm|prompt|alert)\([^)]', re.sub(r'/\*.*?\*/', '', html, flags=re.S))        # no dialog is waited for: the frame never shows one
        b.close()


def test_a_download_never_fails_without_a_word(site, tmp_path):
    pdf = make_pdf(tmp_path / 'made-up-composition.pdf', 'Composition certificate\nDermacure 20 mg cream (made up)')
    xls = OFFICE / 'sheet.xls'
    with pw.sync_playwright() as p:
        errors = []
        b, page = opened(p, site, errors)
        did, ids = dossier(page, [pdf, xls])
        log = lambda: page.evaluate('() => DS.errlog.list()')
        # a kind claude.ai saves: the file as it is
        page.evaluate(CLICK, f"/api/dossiers/{did}/documents/{ids[pdf.name]}/file")
        page.wait_for_function('() => window.__saved.length === 1', timeout=30000)
        got = page.evaluate('() => window.__saved[0]')
        assert got['filename'] == pdf.name and bytes(got['bytes']) == pdf.read_bytes()
        # a kind it does not save (.xls, .xml, .doc…): the same bytes inside a ZIP of the same name, and the page says so
        page.evaluate(CLICK, f"/api/dossiers/{did}/documents/{ids[xls.name]}/file")
        page.wait_for_function('() => window.__saved.length === 2', timeout=30000)
        got = page.evaluate('() => window.__saved[1]')
        z = zipfile.ZipFile(io.BytesIO(bytes(got['bytes'])))
        assert got['filename'] == 'sheet.xls.zip' and z.namelist() == ['sheet.xls'] and z.testzip() is None and z.read('sheet.xls') == xls.read_bytes()
        said = page.evaluate(TOAST)
        assert said and 'sheet.xls.zip' in said['text'] and '.xls' in said['text'] and not said['bad'] and log() == []
        # the engine has no file to give: its own reason, marked as an error and written into the record
        page.evaluate(CLICK, f"/api/dossiers/{did}/single.pdf?module=5")
        page.wait_for_function("() => (t => t && !t.hidden && t.classList.contains('bad'))(document.getElementById('toast'))", timeout=30000)
        said = page.evaluate(TOAST)
        assert said['text'].startswith('تعذّر تجهيز الملف للتنزيل: ') and len(said['text']) > 40, said
        assert [e['kind'] for e in log()] == ['download'] and log()[0]['msg'] == said['text']
        # claude.ai refuses the save: said with its reason; the person saying «no» is not an error
        page.evaluate("() => { window.__dl = 'rate_limited'; }")
        page.evaluate(CLICK, f"/api/dossiers/{did}/documents/{ids[pdf.name]}/file")
        page.wait_for_function("() => /لم يُنزَّل الملف/.test(document.getElementById('toast').textContent)", timeout=30000)
        assert page.evaluate(TOAST)['bad'] and len(log()) == 2
        page.evaluate("() => { window.__dl = 'declined'; document.getElementById('toast').hidden = true; }")
        page.evaluate(CLICK, f"/api/dossiers/{did}/documents/{ids[pdf.name]}/file")
        page.wait_for_timeout(1500)
        assert page.evaluate(TOAST) is None and len(log()) == 2 and len(page.evaluate('() => window.__saved')) == 2
        assert [e for e in errors if 'single.pdf' not in e] == [], errors
        b.close()


def test_the_faults_record_keeps_what_went_wrong(site):
    with pw.sync_playwright() as p:
        errors = []
        b, page = opened(p, site, errors, grant=('clipboard-read', 'clipboard-write'))
        did = page.evaluate(NEW)
        # the engine refuses something: the note is marked as an error, and the refusal is written down without the dossier's id.
        # (A refusal that is not in the engine's own words — here its check of what the page sent — had an EMPTY note in version 50.)
        page.evaluate("async id => { try { await DS.api(`/dossiers/${id}/slots/no-such-item/documents`, {method: 'POST', json: {}}); } catch (e) { DS.toast(e.message); } }", did)
        page.wait_for_function("() => (t => t && !t.hidden && t.classList.contains('bad'))(document.getElementById('toast'))", timeout=30000)
        assert page.evaluate(TOAST)['text'] == 'لم يقبل المحرك هذا الطلب: بياناته ناقصة أو غير صحيحة.'
        first = page.evaluate('() => DS.errlog.list()[0]')
        assert '→ 422' in first['detail'] and 'file' in first['detail'], first                  # what was wrong with the request, for whoever reads the record
        page.evaluate("() => DS.toast('')")                                                     # and a note is never empty, whatever calls it
        assert page.evaluate(TOAST) == {'text': 'حدث خطأ (لم يُذكر سببه).', 'bad': True}
        # something nobody expected: said in words, and written down
        page.evaluate("() => { setTimeout(() => { throw new Error('made-up failure'); }, 0); }")
        page.wait_for_function("() => /حدث خطأ غير متوقع: .*made-up failure/.test(document.getElementById('toast').textContent)", timeout=10000)
        assert page.evaluate(TOAST)['bad']
        log = page.evaluate('() => DS.errlog.list()')
        assert [e['kind'] for e in log] == ['engine', 'unexpected'] and did not in str(log), log
        page.reload()                                                     # the record is kept on this device
        page.wait_for_selector('#boot', state='detached', timeout=240000)
        page.evaluate("() => { location.hash = '#/faults'; }")
        page.wait_for_selector('#fCopy:not([disabled])', timeout=30000)
        rows = page.inner_text('#view table')
        assert page.inner_text('#view h1') == 'سجل الأعطال' and 'رفض من المحرك' in rows and 'خطأ غير متوقع' in rows and 'made-up failure' in rows
        assert page.locator('#nav a[data-r="faults"]').count() == 1      # it has its place in the menu
        page.click('#fCopy')
        page.wait_for_function("() => document.getElementById('toast').textContent === 'تم النسخ.'", timeout=10000)
        text = page.evaluate('() => navigator.clipboard.readText()')
        assert text.startswith('eBOX ') and 'made-up failure' in text and len(text.strip().split('\n')) >= 3
        page.click('#fClear')                                             # asked once more by the button itself (confirm() answers «no» inside claude.ai)
        assert page.evaluate('() => DS.errlog.list().length') == 2
        page.click('#fClear')
        page.wait_for_selector('#view .empty', timeout=10000)
        assert 'لا توجد أعطال مسجَّلة.' in page.inner_text('#view') and page.evaluate('() => DS.errlog.list()') == []
        assert [e for e in errors if 'made-up failure' not in e and 'no-such-item' not in e and 'Failed to load resource' not in e] == [], errors
        b.close()


def test_a_page_picture_is_shown_where_there_is_no_server(site, tmp_path):
    pdf = make_pdf(tmp_path / 'made-up-composition.pdf', 'Composition certificate\nDermacure 20 mg cream (made up)')
    with pw.sync_playwright() as p:
        errors = []
        b, page = opened(p, site, errors)
        did, ids = dossier(page, [pdf])
        asked = []
        page.on('request', lambda r: asked.append(r.url) if '/api/' in r.url else None)        # the engine is in the page: nothing may ask the network for it
        page.evaluate("id => { location.hash = `#/d/${id}/office`; }", did)
        page.wait_for_selector('[data-offpages]', timeout=60000)
        page.click('[data-offpages]')
        page.wait_for_function("() => { const i = document.getElementById('pgImg'); return i && i.src.startsWith('blob:') && i.naturalWidth > 100; }", timeout=60000)
        assert page.inner_text('#pgNo').strip().startswith('1')
        assert asked == [] and errors == [], (asked, errors)             # version 50: an <img> asked the network for /api/…/pages/1.png and the viewer stayed empty
        b.close()
