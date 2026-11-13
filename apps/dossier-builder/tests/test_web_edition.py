"""The browser edition (web/dist): the same engine runs inside Chromium through Pyodide, with no server.
Needs `python3 web/build.py` first (vendor.sh fetches the runtime once); skipped when dist is absent."""
import functools, http.server, io, pathlib, socket, threading
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')


@pytest.fixture(scope='module')
def site():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


def test_in_browser_journey(site, tmp_path):
    pdf = make_pdf(tmp_path / 'composition.pdf', 'Composition certificate')
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
        page = ctx.new_page()
        errors, console = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)            # engine booted inside the browser
        try:
            page.wait_for_selector('.caps .cap', timeout=120000)
        except Exception:
            raise AssertionError('home did not render; view=' + page.inner_text('#view')[:800] + ' console=' + ' | '.join(console)[:800] + ' errors=' + ' | '.join(errors)[:400])
        assert '101' in page.inner_text('.caps')                                      # capabilities read from the in-browser engine
        page.click('#btnNew')
        page.wait_for_selector('.doccards'); page.click('#wizNext')                 # the wizard opens with the documents step
        page.fill('[data-in=name]', 'Examplol 500 mg FCT')
        page.fill('[data-in=man]', 'Example Pharma')
        page.click('#wizNext'); page.click('[data-k=licence][data-v=toll]')
        page.wait_for_function("(n=>n && +n.innerText > 50)(document.querySelector('#pvBody .n'))", timeout=60000)
        page.click('#wizNext')
        page.fill('[data-api="0"][data-f=name]', 'Paracetamol'); page.fill('[data-api="0"][data-f=manufacturer]', 'Granules India')
        page.click('#wizNext')
        page.fill('[data-in=applicant]', 'Example Pharma S.A.E.'); page.fill('[data-in=tracking]', 'P-MAA-0001')
        page.click('#wizCreate')
        page.wait_for_selector('text=Requirements board', timeout=60000)
        with page.expect_file_chooser() as fc:
            page.locator('tr', has_text='Composition certificate').locator('[data-up]').first.click()
        fc.value.set_files(str(pdf))
        page.wait_for_selector('#toast:not([hidden])', timeout=60000)
        page.click('[data-f=all]')
        page.wait_for_selector('tr:has-text("Composition certificate") .chip.c-ok', state='attached', timeout=60000)
        # a document download goes through the browser (outside claude.ai) — the blob is the stored PDF
        page.locator('tr', has_text='Composition certificate').locator('[data-why]').first.click()
        with page.expect_download(timeout=60000) as dl:
            page.click('#dBody a[href*="/file"]')
        assert dl.value.suggested_filename == 'composition.pdf'
        page.keyboard.press('Escape')
        # the guide computes the next step from the in-browser engine
        page.click('#navGuide')
        page.wait_for_selector('.journey', timeout=60000)
        assert page.locator('.jbar a').count() == 6
        # the workspace persists in this browser: reload (still on the guide), the dossier is still there
        page.reload()
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.journey', timeout=120000)
        assert 'Examplol 500 mg FCT' in page.inner_text('#view') and page.locator('.jbar a').count() == 6
        assert errors == [], errors
        b.close()


def test_the_page_keeps_answering_while_the_engine_works(site):
    """The engine runs in a worker (assets/engine.worker.js): a long reading does not freeze the page. Where a worker cannot be
    used (`?engine=page` stands in for that), the engine runs on the page's thread as before and the page still opens."""
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.caps .cap', timeout=120000)
        assert page.evaluate("() => document.documentElement.dataset.engine") == 'worker'
        r = page.evaluate("""async () => {
            let last = performance.now(), worst = 0;
            const iv = setInterval(() => { const n = performance.now(); worst = Math.max(worst, n - last); last = n; }, 20);
            const files = Array.from({length: 30}, (_, i) => ({filename: 'd' + i + '.pdf', text: ('Certificate of Analysis\\nProduct: Dermacure 500 mg tablets\\nBatch No.: 2401' + i + '\\nAssay | 95.0 - 105.0 % | 99.6 %\\n').repeat(150)}));
            const t0 = performance.now();
            const res = await fetch('/api/extract/text?target=dossier', {method: 'POST', headers: {'content-type': 'application/json', 'X-DB': '1'}, body: JSON.stringify({files})});
            const took = performance.now() - t0; clearInterval(iv);
            return {ok: res.ok, took, worst, n: (await res.json()).files.length}; }""")
        assert r['ok'] and r['n'] == 30, r
        assert r['took'] < 400 or r['worst'] < r['took'] / 3, r                       # the longest pause of the page is a small part of the engine's work
        page.goto(site + '/index.local.html?engine=page#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.caps .cap', timeout=120000)
        assert page.evaluate("() => document.documentElement.dataset.engine") == 'page'
        assert not errors, errors
        b.close()


def test_an_image_put_in_an_item_becomes_a_pdf_inside_the_browser_edition(site):
    """No converter in the in-browser engine: the page decodes the image (here a three-page fax-compressed TIFF) and the engine wraps
    the pages into a PDF, all inside the browser."""
    tif = pathlib.Path(__file__).parent / 'data' / 'images' / 'pages-g4.tif'
    if not (DIST / 'assets' / 'img' / 'UTIF.js').exists():
        pytest.skip('image decoders not vendored (web/vendor.sh)')
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.caps .cap', timeout=120000)
        page.evaluate("() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'fxin'; document.body.appendChild(i); }")
        page.set_input_files('#fxin', str(tif))
        r = page.evaluate("""async () => {
            const j = (u, o) => fetch(u, Object.assign({headers: {'X-DB': '1', 'content-type': 'application/json'}}, o)).then(r => r.json());
            const d = await j('/api/dossiers', {method: 'POST', body: JSON.stringify({name: 'Dermacure', product: {name: 'Dermacure', dosageform: 'tablet', manufacturer: 'Example Pharma'},
                profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Paracetamol', manufacturer: 'Granules', option: 'CEP'}]}})});
            const pdf = await asDossierFile(document.querySelector('#fxin').files[0]);
            const fd = new FormData(); fd.append('file', pdf); fd.append('meta', '{}');
            const doc = await fetch('/api/dossiers/' + d.id + '/slots/M1-05/documents', {method: 'POST', body: fd, headers: {'X-DB': '1'}}).then(r => r.json());
            const head = new Uint8Array(await pdf.slice(0, 5).arrayBuffer());
            return {name: pdf.name, type: pdf.type, head: String.fromCharCode(...head), stored: doc.filename, findings: (doc.findings || []).map(f => f.rule)}; }""")
        assert r['name'] == 'pages-g4.pdf' and r['head'] == '%PDF-' and r['stored'] == 'pages-g4.pdf', r
        assert not errors, errors
        b.close()


def test_a_started_project_is_still_there_after_the_page_is_closed(site, tmp_path):
    """«I started adding a document and left»: the draft and its files are in the browser's storage before their reading ends, so a
    page closed in the middle opens again with the draft in the projects list. A ZIP and a RAR are opened inside the browser (the RAR
    by the page's own reader: the engine has no unpacker there); a 7z says why not."""
    import time, zipfile
    z = tmp_path / 'Dermacure documents.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as f:
        f.writestr('Module 1/pricing certificate.txt', 'Pricing Certificate\nProduct: Dermacure 2 % cream\nPrice: EGP 45.00')
        f.writestr('ثبات.txt', 'Stability Study Report\nProduct: Dermacure\nStorage condition: 30 C / 65 % RH')
    z7 = tmp_path / 'backup.7z'
    z7.write_bytes(b"7z\xbc\xaf'\x1c" + b'\0' * 200)
    rar = pathlib.Path(__file__).parent / 'data' / 'archives' / 'rar' / 'dermacure.rar'      # RAR5, with an Arabic folder and file name inside
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1280, 'height': 800})
        errors = []

        def open_(hash_):
            page = ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
            page.add_init_script("localStorage.setItem('db.lang','en')")
            page.goto(site + '/index.local.html' + hash_)
            page.wait_for_selector('#boot', state='detached', timeout=180000)
            return page

        def give(page, path):
            with page.expect_file_chooser() as fc:
                page.click('#intakeBtn')
            fc.value.set_files(str(path))

        page = open_('#/new')
        page.wait_for_selector('#intakeBtn', timeout=120000)
        give(page, z7)                                                                  # no unpacker for 7z inside a browser: said, with what to do
        page.wait_for_function("() => /ZIP/.test(document.querySelector('#toast').textContent)", timeout=60000)
        assert '7z' in page.inner_text('#toast')
        give(page, z)
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && (S.wiz.allFiles || []).length === 2", timeout=120000)
        give(page, rar)                                                                 # the RAR is opened by the page itself
        end = time.time() + 120
        while time.time() < end:                                                        # the two documents of the ZIP and the four of the RAR are in the draft…
            if page.evaluate("async () => (await (await fetch('/api/intake/drafts', {headers: {'X-DB': '1'}})).json()).some(d => d.files === 6)"):
                break
            page.wait_for_timeout(100)
        else:
            raise AssertionError('the draft never got its files')
        page.wait_for_timeout(600)
        page.close()                                                                    # …and the page goes, with no «leave» pressed
        page = open_('#/dossiers')
        page.wait_for_selector('#draftBox', timeout=120000)
        box = page.inner_text('#draftBox')
        assert 'pricing certificate.txt' in box and 'ثبات.txt' in box
        page.click('[data-draft]')
        try:                                                                                # continued: the documents are read again from the browser's storage
            page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && Object.keys(S.wiz.texts || {}).length === 6", timeout=180000)
        except Exception as e:                                                              # it failed in 2 of 4 runs of the whole suite (13/11/2026), never alone: say where it stood
            st = page.evaluate("async () => ({texts: Object.keys((S.wiz||{}).texts||{}), files: ((S.wiz||{}).allFiles||[]).map(f => f.name), "
                               "docs: (S.wiz||{}).docs || null, unread: ((S.wiz||{}).unread||[]).map(f => f.filename || f.name), "
                               "missing: (S.wiz||{}).missing || null, toast: (document.querySelector('#toast')||{}).textContent, "
                               "drafts: (await (await fetch('/api/intake/drafts', {headers: {'X-DB': '1'}})).json()).map(d => d.files)})")
            raise AssertionError(f'the continued draft did not read its six documents again: {st}; page errors {errors}') from e
        assert page.evaluate("() => Object.keys(S.wiz.texts).sort()") == ['licence.pdf', 'notes.txt', 'pricing certificate (2).txt', 'pricing certificate.txt', 'تقرير الثبات.txt', 'ثبات.txt']
        assert errors == [], errors
        b.close()


def test_a_dossier_for_another_country_in_the_browser(site):
    """The countries travel with the browser edition: the wizard offers them, a Saudi dossier gets the Gulf Module 1 from the engine
    inside the page, its declaration has a template made from what SFDA asks, and it exports as CTD folders."""
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/new')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('#auCountry', timeout=120000)
        assert page.input_value('#auCountry') == 'EG'
        page.select_option('#auCountry', 'SA')
        page.wait_for_function("() => document.querySelector('#auName') && document.querySelector('#auName').textContent.includes('SFDA')", timeout=60000)
        assert "Module 1 from the authority's published text" in page.inner_text('#auCard')
        page.click('#wizNext')
        page.fill('[data-in=name]', 'Dermacure KSA'); page.fill('[data-in=man]', 'Example Pharm Co.')
        page.click('#wizNext'); page.click('[data-k=origin][data-v=imported]')
        page.wait_for_function("() => /1\\.7\\.5/.test(document.querySelector('#pvBody').textContent)", timeout=60000)
        page.click('#wizNext')
        page.fill('[data-api="0"][data-f=name]', 'Neomycin sulphate'); page.fill('[data-api="0"][data-f=manufacturer]', 'Example API Co.')
        page.click('#wizNext')
        page.fill('[data-in=applicant]', 'Example Pharm Co.'); page.fill('[data-in=tracking]', 'T-0001')
        page.click('#wizCreate')
        page.wait_for_selector('[data-tpl="GCC-1.7.5"]', timeout=60000)
        assert 'Saudi Arabia' in page.inner_text('#crumbAu') and page.locator('#navReview').is_hidden()
        page.click('[data-tpl="GCC-1.7.5"]')
        page.wait_for_selector('#tplPanel .docprev', timeout=60000)
        assert 'free from alcohol' in page.inner_text('#tplPanel')
        page.keyboard.press('Escape')
        page.click('#navExport')
        page.wait_for_selector('input[data-out="ectd32"]', timeout=60000)
        assert page.locator('input[data-out]').count() == 3 and page.locator('input[data-out="nees"]').count() == 1   # the Gulf: its eCTD, CTD and a NeeS
        b.close()
    assert not errors, errors



@pytest.fixture(scope='module')
def notice_scan(tmp_path_factory):
    """The fictional Arabic registration notice (test_extract_arabic.LINES) as a scanner gives it: 200 dpi, pages that are images only."""
    import shutil, subprocess
    if not shutil.which('soffice') or not shutil.which('pdftoppm'):
        pytest.skip('LibreOffice and pdftoppm make the fixture')
    Image = pytest.importorskip('PIL.Image')
    import docx
    from test_extract_arabic import LINES
    d = tmp_path_factory.mktemp('notice')
    doc = docx.Document()
    for line in LINES:
        doc.add_paragraph(line).alignment = 2
    doc.save(d / 'ekhtar.docx')
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(d), str(d / 'ekhtar.docx')], capture_output=True, timeout=240)
    if not (d / 'ekhtar.pdf').exists():
        pytest.skip('LibreOffice could not convert')
    subprocess.run(['pdftoppm', '-r', '200', '-png', '-f', '1', '-l', '1', str(d / 'ekhtar.pdf'), str(d / 'p')], capture_output=True, timeout=120, check=True)
    Image.open(next(d.glob('p*.png'))).convert('L').save(d / 'scan.pdf', 'PDF', resolution=200.0)
    return d / 'scan.pdf'


def test_a_scanned_notice_is_read_in_the_browser_and_its_data_taken(site, notice_scan):
    """The browser edition reads scans in the page (ui/assets/ocr.js — the desktop's reading: Tesseract with the accurate Arabic
    model, PaddleOCR's second reader) before the engine takes the file (web/boot.js): the notice's Arabic-Indic number and date come
    back right, its information is taken as from a text PDF, and the same file is not read twice."""
    import base64, time
    if not (DIST / 'assets' / 'ocr' / 'tess' / 'ara.traineddata.gz.b64.txt').exists():
        pytest.skip('the scan reader was not fetched (web/ocr_assets.py)')
    b64 = base64.b64encode(notice_scan.read_bytes()).decode()
    send = """async b64 => {
        const t = document.getElementById('toast'), seen = [];
        const mo = new MutationObserver(() => seen.push(t.textContent)); mo.observe(t, {childList: true, characterData: true, subtree: true});
        const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
        const fd = new FormData(); fd.append('files', new File([u], 'scan0001.pdf', {type: 'application/pdf'}));
        const t0 = performance.now();
        const r = await fetch('/api/extract?target=dossier', {method: 'POST', body: fd, headers: {'X-DB': '1'}}).then(r => r.json());
        mo.disconnect();
        return {f: r.files[0], rules: r.rules, seen, ms: performance.now() - t0}; }"""
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.caps .cap', timeout=120000)
        r = page.evaluate(send, b64)
        f, reg = r['f'], r['rules'].get('registration') or {}
        assert f['scanned'] and f['ocr'] and f['reader'] == 'browser-ocr' and f['kind'] == 'licence', f
        assert reg.get('reg_no') == '34567/2025' and reg.get('reg_date') == '2025-03-15', reg            # the date in Arabic-Indic digits
        assert r['rules']['product']['name'].startswith('إكزامبلول') and r['rules']['documents'][0]['valid_until'] == '2030-03-14'
        q = f['ocr_quality']
        assert {'page': 1, 'now': '١٢٣٤٥/٢٠٢٥'}.items() <= next(c for c in q['changed'] if c['now'] == '١٢٣٤٥/٢٠٢٥').items() and not q['weak']
        assert any('Reading the scan' in s for s in r['seen']) and any('Read ✓' in s for s in r['seen'])
        again = page.evaluate(send, b64)                                                                # kept by its SHA-256: not read again
        assert again['f']['reader'] == 'browser-ocr' and not any('Reading the scan' in s for s in again['seen']) and again['ms'] < 5000
        assert not errors, errors
        b.close()


MOCK_SAMPLE = """window.__calls = []; window.claude = { use: async n => { if (n !== 'sample') return null;
  const s = async () => ({ text: '{}' });
  s.limits = async () => ({ maxPromptBytes: 262144, images: { maxCount: 8, maxInputBytes: 20000000, mediaTypes: ['image/jpeg', 'image/png'] } });
  s.json = async (prompt, o) => { const im = o && o.images ? [].concat(o.images) : [];
    window.__calls.push({ images: im.length, kinds: im.map(b => b.type), prompt: prompt.slice(-900) });
    const name = ((prompt.match(/Document 1: (.*?) \\(kind guess/) || [])[1]) || '';
    return { product: { name: 'Examplol 500 mg' }, registration: { reg_no: '34567/2025', valid_until: '2030-03-14' },
             documents: [{ filename: name, kind: 'licence', valid_until: '2030-03-14', stamped: true }] }; };
  return s; } };"""


def test_with_claude_a_scan_goes_as_its_page_pictures_and_no_upload_waits_for_ocr(site, notice_scan):
    """With claude.ai's model (the sample capability — stood in here by a mock that records what it is sent): the wizard sends a scan
    as its page pictures, two halves a page, says which is which, and never runs the page's own OCR before the upload; the card says
    Claude read it and what it gave, and the data fills from it (the owner, 13/11/2026: «the program used to be smart»)."""
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.add_init_script(MOCK_SAMPLE)
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.click('#btnNew'); page.wait_for_selector('.doccards')
        with page.expect_file_chooser() as fc:
            page.locator('[data-updoc=registration_licence]').first.click()
        fc.value.set_files(str(notice_scan))
        page.wait_for_function("() => { const l = document.querySelector('[data-docline]'); return l && /read by Claude/.test(l.textContent); }", timeout=120000)
        calls = page.evaluate('window.__calls')
        assert len(calls) == 1 and calls[0]['images'] == 2 and set(calls[0]['kinds']) == {'image/jpeg'}, calls
        assert 'the top half of page 1 of 1' in calls[0]['prompt'] and 'read it from its pictures' in calls[0]['prompt']
        assert not page.evaluate('() => !!window.Tesseract')                                       # the page's own reader never ran
        line = page.locator('[data-docline]').first.inner_text()
        assert 'trade name' in line or 'registration no.' in line, line                              # what Claude gave, on the card
        assert 'Examplol' in page.inner_text('#wizLive')
        assert not errors, errors
        b.close()


def test_a_scan_is_made_searchable_inside_the_browser(site, notice_scan):
    """The preparation stage in the browser edition: the scan placed in its item and fixed — its words, read in the page, written
    invisibly under its image (textlayer) — so the stored copy has text of its own: the engine reads its number and date from it."""
    import base64
    if not (DIST / 'assets' / 'ocr' / 'tess' / 'ara.traineddata.gz.b64.txt').exists():
        pytest.skip('the scan reader was not fetched (web/ocr_assets.py)')
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.caps .cap', timeout=120000)
        r = page.evaluate("""async b64 => {
            const j = (u, o) => fetch(u, Object.assign({headers: {'X-DB': '1', 'content-type': 'application/json'}}, o)).then(r => r.json());
            const d = await j('/api/dossiers', {method: 'POST', body: JSON.stringify({name: 'Examplol', product: {name: 'Examplol 500 mg', dosageform: 'film-coated tablet', manufacturer: 'Example Pharma'},
                profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Paracetamol', manufacturer: 'Example API Co.', option: 'CEP'}]},
                envelope: {tracking: 'T-0001', applicant: 'Example Pharma', invented_name: 'Examplol', inn: ['paracetamol']}})});
            const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
            const fd = new FormData(); fd.append('files', new File([u], 'scan0001.pdf', {type: 'application/pdf'})); fd.append('meta', '{}');
            const up = await fetch('/api/dossiers/' + d.id + '/unplaced', {method: 'POST', body: fd, headers: {'X-DB': '1'}}).then(r => r.json());
            const w = (await j('/api/dossiers/' + d.id + '/prepare')).waiting.find(x => x.id === up[0].id);
            const slot = w.auto || (w.suggestions[0] || {}).slot_id;
            const r = await j('/api/dossiers/' + d.id + '/prepare/' + up[0].id, {method: 'POST', body: JSON.stringify({slot_id: slot})});
            const file = await fetch('/api/dossiers/' + d.id + '/documents/' + r.document.id + '/file').then(r => r.blob());
            const fd2 = new FormData(); fd2.append('files', new File([file], 'stored.pdf', {type: 'application/pdf'}));
            const ex = await fetch('/api/extract', {method: 'POST', body: fd2, headers: {'X-DB': '1'}}).then(r => r.json());
            return {steps: r.steps, needs: r.needs_you, reading: w.reading, findings: (r.document.findings || []).map(f => f.rule), f: ex.files[0], rules: ex.rules}; }""",
            base64.b64encode(notice_scan.read_bytes()).decode())
        assert r['reading']['reader'] == 'ocr' and r['reading']['ocr_quality']['corrected'] >= 2, r['reading']
        fixed = next((x for x in r['steps'] if isinstance(x, dict)), {})
        assert 'make_searchable' in fixed.get('fixed', []), r
        assert 'NTA065-N4' not in r['findings'] and not any(x['rule'] == 'NTA065-N4' for x in r['needs'])
        assert not r['f']['scanned'] and r['f']['chars'] > 300 and r['f']['kind'] == 'licence'      # text of its own now
        reg = r['rules'].get('registration') or {}
        assert reg.get('reg_no') == '34567/2025' and reg.get('reg_date') == '2025-03-15', reg
        assert not errors, errors
        b.close()


def test_pdfcraft_runs_inside_the_browser(site, tmp_path):
    """The browser edition runs PdfCraft itself — its program built for WebAssembly, in the engine's thread over an in-memory folder
    (web/pdfcraft.wasi.js) — so the browser makes the fixes the desktop makes: here a document's JavaScript removed, its pages
    drawn for the viewer and its file improved, by the same tool steps as on a computer."""
    import base64
    from pypdf import PdfReader, PdfWriter
    if not (DIST / 'assets' / 'pdfcraft' / 'pdfcraft-cli.json').exists():
        pytest.skip('PdfCraft for WebAssembly was not built (tools/pdfcraft/build-wasm.sh)')
    w = PdfWriter(clone_from=str(make_pdf(tmp_path / 's.pdf', 'Composition certificate')))
    w.add_js('app.alert(1)')
    w.write(open(tmp_path / 'js.pdf', 'wb'))
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1280, 'height': 800}).new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_function("""async () => { const r = await fetch('/api/capabilities', {headers: {'X-DB': '1'}}).then(r => r.json());
            return r.pdf_engine && r.pdf_engine.engine === 'PdfCraft'; }""", timeout=120000, polling=1000)
        r = page.evaluate("""async b64 => {
            const j = (u, o) => fetch(u, Object.assign({headers: {'X-DB': '1', 'content-type': 'application/json'}}, o)).then(r => r.json());
            const caps = await j('/api/capabilities');
            const d = await j('/api/dossiers', {method: 'POST', body: JSON.stringify({name: 'Dermacure', product: {name: 'Dermacure', dosageform: 'tablet', manufacturer: 'Example Pharma'},
                profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Paracetamol', manufacturer: 'Granules', option: 'CEP'}]}})});
            const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
            const fd = new FormData(); fd.append('file', new File([u], 'composition.pdf', {type: 'application/pdf'})); fd.append('meta', '{}');
            const doc = await fetch('/api/dossiers/' + d.id + '/slots/M1-31/documents', {method: 'POST', body: fd, headers: {'X-DB': '1'}}).then(r => r.json());
            const t0 = performance.now();
            const fix = await j('/api/dossiers/' + d.id + '/documents/' + doc.id + '/fix', {method: 'POST'});
            const ms = performance.now() - t0;
            const png = await fetch('/api/dossiers/' + d.id + '/documents/' + fix.document.id + '/pages/1.png');
            const file = new Uint8Array(await (await fetch('/api/dossiers/' + d.id + '/documents/' + fix.document.id + '/file')).arrayBuffer());
            let s = ''; for (let i = 0; i < file.length; i += 8192) s += String.fromCharCode.apply(null, file.subarray(i, i + 8192));
            return {engine: caps.pdf_engine, before: (doc.findings || []).map(f => f.rule), done: fix.done.map(x => x.op), refused: fix.refused,
                    after: (fix.document.findings || []).map(f => f.rule), png: png.status + ' ' + png.headers.get('content-type'), ms, out: btoa(s)}; }""",
            base64.b64encode((tmp_path / 'js.pdf').read_bytes()).decode())
        assert r['engine']['where'] == 'browser' and 'WebAssembly' in r['engine']['version'], r['engine']
        assert 'PDF-JS' in r['before'] and 'remove_javascript' in r['done'] and 'PDF-JS' not in r['after'], r
        assert r['png'] == '200 image/png'                                              # the viewer's page, drawn by PdfCraft here
        out = PdfReader(io.BytesIO(base64.b64decode(r['out'])))
        assert '/JavaScript' not in str(out.trailer['/Root'].get('/Names', {}))
        assert not errors, errors
        b.close()
