"""«المكتب» and the live preview on the preparation page (the owner, 15/11/2026: «محتاج جزء يكون ملحق مع رفع المستندات يكون فيه كل
المستندات ممكن تتعدل … و كمان المستندات و هي بتترفع و تتمسح تظهر بريڤيو ايه اللي بيحصل»): files added there show their pages;
while Claude reads a scan, the very picture it is given is shown with the page and the half; afterwards «المكتب» lists every
document of the file with its first page, opens a Word file in the Word program and comes back to the page; a document of an
authority or a third party is not offered for editing. claude.ai's model is stood in by a mock that records what it is sent
(and takes its time, as a reading does). Page rules as strict as claude.ai's could be. The fixtures are made up."""
import functools, http.server, io, pathlib, socket, threading
import pytest

pw = pytest.importorskip('playwright.sync_api')
docx = pytest.importorskip('docx')
Image = pytest.importorskip('PIL.Image')
APP = pathlib.Path(__file__).resolve().parents[1]
DIST = APP / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'assets' / 'ocr' / 'pdfjs' / 'pdf.min.mjs').exists() or not (DIST / 'assets' / 'programs' / 'wordcraft' / 'glue.js').exists(),
                                reason='web/dist was built without the page reader or the Word program')
GPU = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
POLICY = ["default-src 'self'", "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'", "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "frame-src 'none'", "object-src 'none'"]
MOCK = """window.__calls = []; window.claude = { use: async n => { if (n !== 'sample') return null;
  const s = async () => ({ text: '{}' });
  s.limits = async () => ({ maxPromptBytes: 262144, images: { maxCount: 8, maxInputBytes: 20000000, mediaTypes: ['image/jpeg', 'image/png'] } });
  s.json = async (prompt, o) => { const im = o && o.images ? [].concat(o.images) : [];
    window.__calls.push({ images: im.length, kinds: im.map(b => b.type) });
    await new Promise(r => setTimeout(r, 2500));
    const name = ((prompt.match(/Document 1: (.*?) \\(kind guess/) || [])[1]) || '';
    return { documents: [{ filename: name, kind: 'licence', title: 'Registration notice (made up)', issuer: 'Example Authority', valid_until: '2030-03-14', stamped: true }] }; };
  return s; } };"""


@pytest.fixture(scope='module')
def site():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.html': 'text/html; charset=utf-8',
                          '.js': 'text/javascript; charset=utf-8', '.txt': 'text/plain; charset=utf-8'}

        def end_headers(self):
            self.send_header('Content-Security-Policy', '; '.join(POLICY))
            super().end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


@pytest.fixture(scope='module')
def files(tmp_path_factory):
    d = tmp_path_factory.mktemp('office')
    from PIL import ImageDraw
    page = Image.new('L', (1654, 2339), 255)                         # an A4 page at 200 dpi, as a scanner gives it: a picture only
    g = ImageDraw.Draw(page)
    for i, line in enumerate(['REGISTRATION NOTICE (made up)', 'Product: Dermacure 20 mg cream', 'Holder: Example Pharm', 'Valid until 14/03/2030']):
        g.text((180, 260 + 120 * i), line, fill=0)
    page.save(d / 'made-up-scan.pdf', 'PDF', resolution=200.0)
    w = docx.Document()
    w.add_heading('Cover letter — Dermacure 20 mg cream (made up)', level=1)
    w.add_paragraph('Example Pharm submits the registration file of Dermacure 20 mg cream.')
    w.save(str(d / 'made-up-cover.docx'))
    return [d / 'made-up-scan.pdf', d / 'made-up-cover.docx']


def test_the_new_file_wizard_shows_a_base_document_being_read(site, files):
    """The first upload, in the new-dossier wizard: the scan's page beside its line, then the picture Claude is given (page and
    half), and when the reading is over only what it gave."""
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1280, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script(MOCK)
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.click('#btnNew'); page.wait_for_selector('.doccards')
        with page.expect_file_chooser() as fc:
            page.locator('[data-updoc=registration_licence]').first.click()
        fc.value.set_files(str(files[0]))
        page.wait_for_function("""() => { const l = document.querySelector('[data-docline]'); const img = l && l.querySelector('.pv-pic:not([hidden]) img');
            return img && img.src.startsWith('blob:') && /يقرؤها Claude/.test(l.querySelector('.pv-cap').textContent); }""", timeout=60000)
        page.wait_for_function("() => document.querySelector('[data-docline] .pv-strip img') !== null", timeout=60000)
        page.wait_for_function("() => { const l = document.querySelector('[data-docline]'); return l && !l.querySelector('.pv-now') && /Claude/.test(l.innerText); }", timeout=60000)
        b.close()
    assert not [e for e in errors if 'Invalid or unexpected token' not in e], errors


def test_files_show_their_pages_and_what_claude_is_given_and_the_office_edits_them(site, files):
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script(MOCK)
        page.goto(site + '/index.local.html#/')
        page.evaluate('() => DBWEB.ready()')
        did = page.evaluate("""async () => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
            body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
            product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""")
        page.evaluate('id => { location.hash = `#/d/${id}/prepare`; }', did)
        page.wait_for_selector('#prepFiles', state='attached', timeout=60000)
        page.set_input_files('#prepFiles', [str(f) for f in files])
        # the scan's page beside it, the Word file's kind beside it
        page.wait_for_function("() => [...document.querySelectorAll('[data-pv]')].some(x => x.dataset.pvname === 'made-up-scan.pdf' && x.querySelector('.pv-strip img'))", timeout=60000)
        assert page.evaluate("() => [...document.querySelectorAll('[data-pv]')].find(x => x.dataset.pvname === 'made-up-cover.docx').querySelector('.pv-kind').textContent") == 'DOCX'
        # while Claude reads the scan: the very picture it is given, its page and half, on the scan's card
        page.wait_for_function("""() => { const h = [...document.querySelectorAll('[data-pv]')].find(x => x.dataset.pvname === 'made-up-scan.pdf');
            const img = h && h.querySelector('.pv-pic:not([hidden]) img'); return img && img.src.startsWith('blob:') && /صفحة 1 من 1/.test(h.querySelector('.pv-cap').textContent); }""", timeout=60000)
        cap = page.evaluate("() => [...document.querySelectorAll('[data-pv]')].find(x => x.dataset.pvname === 'made-up-scan.pdf').querySelector('.pv-now').textContent")
        assert 'Claude' in cap and ('الأعلى' in cap or 'الأسفل' in cap), cap
        page.wait_for_function("() => !document.querySelector('.pv-now')", timeout=60000)           # the reading over: the panel goes
        calls = page.evaluate('window.__calls')
        assert calls and calls[0]['images'] == 2 and set(calls[0]['kinds']) == {'image/jpeg'}, calls
        # prepared: the office lists both, each with its first page; the scan (an authority's notice) is not offered for editing
        page.click('#prepAll')
        page.wait_for_function("() => document.querySelectorAll('[data-offdoc]').length === 2 && !document.querySelector('.pv-now')", timeout=240000)
        page.evaluate("() => document.getElementById('office').scrollIntoView()")
        page.wait_for_function("() => [...document.querySelectorAll('#offList img[data-pvthumb]')].every(i => i.src && i.src.startsWith('blob:'))", timeout=60000)
        rows = page.evaluate("() => [...document.querySelectorAll('[data-offdoc]')].map(r => ({text: r.innerText, edit: !!r.querySelector('[data-offedit]')}))")
        scan = next(r for r in rows if 'made-up-scan.pdf' in r['text'])
        word = next(r for r in rows if 'made-up-cover.docx' in r['text'])
        assert not scan['edit'] and 'لا يُعدَّل' in scan['text']
        assert word['edit'] and 'Word' in word['text']
        # the Word file opened from the office, and back on the page
        page.click('[data-offedit]')
        page.wait_for_function("() => document.querySelector('.dbprog') && !document.querySelector('.dbprog-wait')", timeout=240000)
        page.click('.dbprog [data-act="close"]')
        page.wait_for_selector('.dbprog', state='detached', timeout=10000)
        assert page.evaluate('() => location.hash').endswith('/prepare')
        page.wait_for_selector('[data-offdoc]', timeout=30000)
        # from the menu, the office comes first (above the files waiting and placed)
        page.evaluate('id => { location.hash = `#/d/${id}/office`; }', did)
        page.wait_for_function("() => document.querySelectorAll('[data-offdoc]').length === 2", timeout=60000)
        assert page.evaluate("() => document.getElementById('office').getBoundingClientRect().top < document.getElementById('prepOut').getBoundingClientRect().top")
        assert page.evaluate("() => document.querySelector('#navOffice').classList.contains('on') || document.querySelector('#navOffice').getAttribute('aria-current') === 'page'")
        b.close()
    assert not [e for e in errors if 'Invalid or unexpected token' not in e], errors   # (that one is the fonts' link, web/build.py: known)
