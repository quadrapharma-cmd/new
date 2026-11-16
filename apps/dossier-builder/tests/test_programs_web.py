"""The editing programs inside the browser edition (ui/assets/programs.js, web/build.py programs_dist): the Word program opens a
Word file of an item, the PDF program a PDF, in a frame the page writes itself, and what the person saves after changing it becomes
a new version.
Run under page rules as strict as claude.ai's could be — no frame fetched from any address, no script from a blob:, WebAssembly
allowed — and once without WebAssembly, where the program must say it cannot run instead of waiting for ever.
The fixtures are made up. Needs `python3 web/build.py` with the Word program built (dossier-builder-v2/tools/craft/build.mjs)."""
import base64, functools, gzip, hashlib, http.server, io, json, pathlib, re, socket, threading
import pytest

pw = pytest.importorskip('playwright.sync_api')
docx = pytest.importorskip('docx')
APP = pathlib.Path(__file__).resolve().parents[1]
DIST = APP / 'web' / 'dist'
PROG = DIST / 'assets' / 'programs' / 'wordcraft'
pytestmark = pytest.mark.skipif(not (PROG / 'glue.js').exists(), reason='web/dist was built without the Word program')
GPU = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
POLICY = ["default-src 'self'", "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'", "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: blob:", "connect-src 'self'", "worker-src 'self' blob:", "frame-src 'none'", "object-src 'none'"]


def serve(policy):
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()

    class H(http.server.SimpleHTTPRequestHandler):
        extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.html': 'text/html; charset=utf-8',
                          '.js': 'text/javascript; charset=utf-8', '.txt': 'text/plain; charset=utf-8'}

        def end_headers(self):
            self.send_header('Content-Security-Policy', '; '.join(policy))
            super().end_headers()

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(H, directory=str(DIST)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{port}'


@pytest.fixture(scope='module')
def site():
    srv, url = serve(POLICY)
    yield url
    srv.shutdown()


def letter(path):
    d = docx.Document()
    d.add_heading('Cover letter — Dermacure 20 mg cream (made up)', level=1)
    d.add_paragraph('Example Pharm, 12 Example Street, Example City')
    d.add_paragraph('نتقدم بملف تسجيل مستحضر ديرماكيور ٢٠ مجم كريم (مثال مؤلف للاختبار).')
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = 'Product', 'Dermacure 20 mg cream'
    t.cell(1, 0).text, t.cell(1, 1).text = 'Pack', 'Tube of 30 g'
    d.save(str(path))
    return path


def page_text():
    return (DIST / 'index.html').read_text(encoding='utf-8')


@pytest.mark.parametrize('app', ['wordcraft', 'pdfcraft'])
def test_the_program_is_served_in_parts_the_artifact_host_takes(app):
    m = json.loads(re.search(r'window\.DB_PROGRAMS=(\{.*?\});', page_text()).group(1))
    w = m['apps'][app]
    PROG = DIST / 'assets' / 'programs' / app
    parts = [PROG / f'wasm.gz.b64.{k}.txt' for k in range(1, w['parts'] + 1)]
    assert all(p.stat().st_size <= 12_000_000 for p in parts)                  # a file of the page holds 16 MB
    text = ''.join(p.read_text() for p in parts)
    assert len(text) == w['size']
    raw = gzip.decompress(base64.b64decode(text))
    assert len(raw) == w['bytes'] and hashlib.sha256(raw).hexdigest() == w['sha256']
    glue = (PROG / 'glue.js').read_text(encoding='utf-8')
    assert glue.count("const ret = typeof globalThis.__dbQuery === 'string' ? globalThis.__dbQuery : arg1.search;") == 1
    assert 'const ret = arg1.search;' not in glue
    for f in re.findall(r"from '(\./snippets/[^']+)'", glue):                  # what the glue imports is beside it
        assert (PROG / f).is_file()
    lic = [p.name for p in (PROG / 'licenses').rglob('*') if p.is_file()]
    assert lic and all(n.endswith(('.txt', '.md')) for n in lic)


def test_the_page_carries_the_whole_loader():
    """A script that writes «</body>» in a string must not end the page there (web/build.py took the first </body> once)."""
    src = (APP / 'ui' / 'assets' / 'programs.js').read_text(encoding='utf-8')
    assert src.strip() in page_text()
    assert 'function openInProgram(' in page_text()


def open_board(page, url, tmp_path, files):
    page.goto(url + '/index.local.html#/')
    page.evaluate('() => DBWEB.ready()')
    did = page.evaluate("""async () => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
        body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
        product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""")
    board = page.evaluate("async id => (await (await fetch(`/api/dossiers/${id}/board`)).json())", did)
    slots = [s['slot_id'] for s in board['slots'] if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents']]
    placed = []
    for f, slot in zip(files, slots):
        st = page.evaluate("""async ([id, slot, name, data]) => { const fd = new FormData(); fd.append('file', new File([new Uint8Array(data)], name)); fd.append('meta', '{}');
            return (await fetch(`/api/dossiers/${id}/slots/${encodeURIComponent(slot)}/documents`, {method: 'POST', body: fd})).status; }""", [did, slot, f.name, list(f.read_bytes())])
        assert st == 201
        placed.append(slot)
    page.evaluate('id => { location.hash = `#/d/${id}/board`; }', did)
    page.wait_for_function("id => typeof S === 'object' && S.dossier && S.dossier.id === id && S.board && S.board.slots.some(s => s.documents.length)", arg=did, timeout=60000)
    return did, placed


def status(page):
    return page.evaluate("() => document.querySelector('.dbprog-status').textContent")


def test_a_word_file_is_edited_in_the_program_and_kept_as_a_new_version(site, tmp_path):
    w = letter(tmp_path / 'made-up-letter.docx')
    old = tmp_path / 'made-up-old.doc'
    old.write_bytes(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\0' * 1024)        # an old .doc: no button (the program loses its tables)
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 860})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        did, (slot, slot_doc) = open_board(page, site, tmp_path, [w, old])
        page.evaluate('() => { window.__m = []; addEventListener("message", e => { const m = e.data || {}; if (m.dbprog) window.__m.push([m.type, m.fromDevice, m.dirty, m.name || "", m.bytes ? m.bytes.byteLength : null]); }); }')
        page.evaluate('s => openWhy(s)', slot_doc)
        page.wait_for_selector('#dBody .finding', timeout=20000)
        assert not page.query_selector('[data-prog]')
        page.evaluate('s => openWhy(s)', slot)
        page.wait_for_selector('[data-prog]', timeout=20000)
        assert 'Word' in page.inner_text('[data-prog]')
        for round_ in (1, 2):                                                  # the second time the program comes from the device
            page.click('[data-prog]')
            page.wait_for_function("() => window.DBPROG && document.querySelector('.dbprog') && !document.querySelector('.dbprog-wait')", timeout=240000)
            page.wait_for_function("() => { const f = document.querySelector('.dbprog iframe'); return f && f.contentWindow.wordcraft; }", timeout=60000)
            page.wait_for_function("""async () => { const d = await document.querySelector('.dbprog iframe').contentWindow.wordcraft.docInspect();
                return (d.blocks || []).some(x => /Dermacure/.test(x.text || '')); }""", timeout=60000)
            assert page.evaluate("() => document.querySelector('.dbprog [data-act=\"save\"]').disabled")      # nothing changed yet
            assert not page.query_selector('.dbprog [data-act="pdf"]')                                       # the program's PDF is not offered
            box = page.query_selector('.dbprog iframe').bounding_box()
            page.mouse.click(box['x'] + box['width'] * 0.5, box['y'] + box['height'] * 0.6)
            page.keyboard.press('Control+Home')
            page.keyboard.type(f'EDITED{round_} ')
            page.wait_for_function("() => !document.querySelector('.dbprog [data-act=\"save\"]').disabled", timeout=20000)
            page.click('.dbprog [data-act="save"]')
            try:
                page.wait_for_function("() => /حُفظت|Saved/.test(document.querySelector('.dbprog-status').textContent)", timeout=60000)
            except Exception:
                raise AssertionError(f'round {round_}: not saved — status «{status(page)}», messages {page.evaluate("() => window.__m")}, errors {errors}')
            page.click('.dbprog [data-act="close"]')
            page.wait_for_selector('.dbprog', state='detached', timeout=10000)        # saved: closing asks nothing
            page.wait_for_selector('[data-prog]', timeout=20000)                       # the item's drawer is back
        loads = [m[1] for m in page.evaluate('() => window.__m') if m[0] == 'loading']
        assert loads == [False, True]
        docs = page.evaluate("async ([id, slot]) => (await (await fetch(`/api/dossiers/${id}/board`)).json()).slots.find(s => s.slot_id === slot).documents", [did, slot])
        assert [(d['version'], d['filename']) for d in docs] == [(3, 'made-up-letter.docx')]
        data = bytes(page.evaluate("async ([id, doc]) => Array.from(new Uint8Array(await (await fetch(`/api/dossiers/${id}/documents/${doc}/file`)).arrayBuffer()))", [did, docs[0]['id']]))
        b.close()
    saved = docx.Document(io.BytesIO(data))
    texts = [x.text for x in saved.paragraphs]
    assert texts[0].startswith('EDITED2 EDITED1 Cover letter — Dermacure 20 mg cream (made up)')
    assert 'نتقدم بملف تسجيل مستحضر ديرماكيور ٢٠ مجم كريم (مثال مؤلف للاختبار).' in texts
    assert [[c.text for c in r.cells] for r in saved.tables[0].rows] == [['Product', 'Dermacure 20 mg cream'], ['Pack', 'Tube of 30 g']]
    assert not [e for e in errors if 'Invalid or unexpected token' not in e]   # (that one is the fonts' link, web/build.py: known)


def made_up_pdf(path):
    """Two pages written by hand (no library): a made-up certificate."""
    objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 7 0 R >> >> >>', None,
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 6 0 R /Resources << /Font << /F1 7 0 R >> >> >>', None,
            '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    texts = {3: 'BT /F1 16 Tf 72 760 Td (Certificate of analysis - Exampletine 20 mg, made up) Tj ET',
             5: 'BT /F1 16 Tf 72 760 Td (Batch EX-001 - Example Pharm, made up) Tj ET'}
    for i, t in texts.items():
        objs[i] = f'<< /Length {len(t)} >>\nstream\n{t}\nendstream'
    out, offs = b'%PDF-1.7\n', []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f'{n} 0 obj\n{o}\nendobj\n'.encode('latin1')
    x = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode() + b''.join(f'{o:010d} 00000 n \n'.encode() for o in offs)
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
    path.write_bytes(out)
    return path


def test_a_pdf_page_is_turned_in_the_pdf_program_and_kept_as_a_new_version(site, tmp_path):
    pypdf = pytest.importorskip('pypdf')
    pdf = made_up_pdf(tmp_path / 'made-up-certificate.pdf')
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 860})
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        did, (slot,) = open_board(page, site, tmp_path, [pdf])
        page.evaluate('s => openWhy(s)', slot)
        page.wait_for_selector('[data-prog]', timeout=20000)
        assert 'PDF' in page.inner_text('[data-prog]')
        page.click('[data-prog]')
        page.wait_for_function("() => document.querySelector('.dbprog') && !document.querySelector('.dbprog-wait')", timeout=240000)
        page.wait_for_function("""async () => { const f = document.querySelector('.dbprog iframe'); if (!f || !f.contentWindow.pdfcraft) return false;
            const d = await f.contentWindow.pdfcraft.docInspect(); return (d.documents || []).some(x => x.pages === 2); }""", timeout=60000)
        box = page.query_selector('.dbprog iframe').bounding_box()
        page.mouse.click(box['x'] + box['width'] * 0.6, box['y'] + box['height'] * 0.5)
        page.keyboard.press('Control+s')                                               # nothing changed: nothing kept
        page.wait_for_function("() => /لا يوجد تعديل|Nothing was changed/.test(document.querySelector('.dbprog-status').textContent)", timeout=20000)
        assert page.evaluate("() => document.querySelector('.dbprog [data-act=\"save\"]').disabled")
        page.evaluate("async () => { await document.querySelector('.dbprog iframe').contentWindow.pdfcraft.execute('page.rotate', {}); }")   # a sideways scan's page
        page.wait_for_function("() => !document.querySelector('.dbprog [data-act=\"save\"]').disabled", timeout=20000)
        page.click('.dbprog [data-act="save"]')
        page.wait_for_function("() => /حُفظت|Saved/.test(document.querySelector('.dbprog-status').textContent)", timeout=60000)
        assert 'Word' not in page.evaluate("() => document.querySelector('.dbprog-status').textContent")
        page.click('.dbprog [data-act="close"]')
        page.wait_for_selector('.dbprog', state='detached', timeout=10000)
        docs = page.evaluate("async ([id, slot]) => (await (await fetch(`/api/dossiers/${id}/board`)).json()).slots.find(s => s.slot_id === slot).documents", [did, slot])
        assert [(d['version'], d['filename']) for d in docs] == [(2, 'made-up-certificate.pdf')]
        data = bytes(page.evaluate("async ([id, doc]) => Array.from(new Uint8Array(await (await fetch(`/api/dossiers/${id}/documents/${doc}/file`)).arrayBuffer()))", [did, docs[0]['id']]))
        b.close()
    r = pypdf.PdfReader(io.BytesIO(data))
    assert len(r.pages) == 2 and (r.pages[0].get('/Rotate') or 0) % 360 == 90 and (r.pages[1].get('/Rotate') or 0) % 360 == 0
    assert 'Exampletine 20 mg' in r.pages[0].extract_text() and 'Batch EX-001' in r.pages[1].extract_text()


def test_without_webassembly_the_program_says_it_cannot_run(tmp_path):
    srv, url = serve([x.replace(" 'wasm-unsafe-eval'", '') for x in POLICY])
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(args=GPU)
            page = b.new_page()
            page.goto(url + '/index.local.html#/')
            page.wait_for_function('() => window.DBPROG')
            page.evaluate("data => { window.__h = DBPROG.open('wordcraft', {name: 'made-up.docx', bytes: new Uint8Array(data), lang: 'ar', onSave() {}}); }",
                          list(letter(tmp_path / 'made-up.docx').read_bytes()))
            page.wait_for_function("() => /تعذّر تشغيل/.test(document.querySelector('.dbprog-status').textContent)", timeout=240000)
            assert 'لا تسمح بتشغيل البرامج' in status(page)
            page.click('.dbprog [data-act="close"]')
            assert page.query_selector('.dbprog') is None
            b.close()
    finally:
        srv.shutdown()


def office(page, did):
    page.evaluate('id => { location.hash = `#/d/${id}/office`; }', did)
    page.wait_for_selector('#offList [data-offdoc]', timeout=60000)


def started(page, app):
    page.wait_for_selector('.dbprog iframe', timeout=60000)
    page.frame_locator('.dbprog iframe').locator(f'#{app}_loading').wait_for(state='detached', timeout=240000)


def keys(page, *names):
    box = page.query_selector('.dbprog iframe').bounding_box()
    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    for k in names:
        page.keyboard.press(k)
        page.wait_for_timeout(1200)
    return box


@pytest.mark.skipif(not (DIST / 'assets' / 'programs' / 'photocraft' / 'glue.js').exists(), reason='built without the photo program')
def test_a_page_cleaned_in_the_photo_program_takes_its_place_as_a_new_version(site, tmp_path):
    """«المكتب»: page 2 of a made-up two-page PDF drawn at 200 dpi and opened in the photo program; its save (Ctrl+S gives a Photoshop
    file) comes back as the picture it shows and takes page 2's place — the same size, page 1 untouched — as version 2."""
    pypdf = pytest.importorskip('pypdf')
    pdf = made_up_pdf(tmp_path / 'made-up-certificate.pdf')
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 860})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        did, (slot,) = open_board(page, site, tmp_path, [pdf])
        office(page, did)
        page.fill('[data-offpg]', '2')
        page.click('[data-offphoto]')
        started(page, 'photocraft')
        page.wait_for_timeout(2500)                                       # the page is dropped on the program and opened
        keys(page, 'Control+s')
        page.wait_for_function("() => /استُبدلت|replaced/.test(document.querySelector('.dbprog-status').textContent)", timeout=180000)
        page.click('.dbprog [data-act="close"]')
        page.wait_for_selector('.dbprog', state='detached', timeout=10000)
        docs = page.evaluate("async ([id, slot]) => (await (await fetch(`/api/dossiers/${id}/board`)).json()).slots.find(s => s.slot_id === slot).documents", [did, slot])
        assert [(d['version'], d['filename'], d['meta'].get('page_picture')) for d in docs] == [(2, 'made-up-certificate.pdf', 2)], docs
        data = bytes(page.evaluate("async ([id, doc]) => Array.from(new Uint8Array(await (await fetch(`/api/dossiers/${id}/documents/${doc}/file`)).arrayBuffer()))", [did, docs[0]['id']]))
        assert not errors, errors
        b.close()
    r = pypdf.PdfReader(io.BytesIO(data))
    assert len(r.pages) == 2 and 'Exampletine 20 mg' in r.pages[0].extract_text() and r.pages[1].extract_text().strip() == ''
    assert [round(float(x)) for x in r.pages[1].mediabox] == [0, 0, 595, 842]


@pytest.mark.skipif(not (DIST / 'assets' / 'programs' / 'designcraft' / 'glue.js').exists(), reason='built without the design program')
def test_an_artwork_pdf_placed_in_a_design_comes_back_as_its_exported_pdf(site, tmp_path):
    """«المكتب»: the layout item's PDF (Egypt M1-11, made up) in the design program — a new document (Ctrl+N), the file placed in it
    («Place the file in the design»), File ▸ Export PDF… — comes back as a new version of the artwork; the design's own file
    (Ctrl+S) is the program's and does not go into the dossier."""
    pypdf = pytest.importorskip('pypdf')
    pdf = made_up_pdf(tmp_path / 'made-up-layout.pdf')
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 860})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.goto(site + '/index.local.html#/')
        page.evaluate('() => DBWEB.ready()')
        did = page.evaluate("""async data => { const id = (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
            body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
            product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id;
            const fd = new FormData(); fd.append('file', new File([new Uint8Array(data)], 'made-up-layout.pdf')); fd.append('meta', '{}');
            const st = (await fetch(`/api/dossiers/${id}/slots/M1-11/documents`, {method: 'POST', body: fd})).status;
            if (st !== 201) throw new Error('upload ' + st); return id; }""", list(pdf.read_bytes()))
        office(page, did)
        page.click('[data-offdesign]')
        started(page, 'designcraft')
        page.wait_for_function("() => /210 × 297/.test(document.querySelector('.dbprog-status').textContent)", timeout=20000)   # its size, said
        page.wait_for_timeout(1500)
        keys(page, 'Control+n', 'Enter')                                   # a new document, the dialog's OK
        page.click('.dbprog [data-act="place"]')
        page.wait_for_timeout(2500)
        keys(page, 'Enter')                                                # «Place PDF»: page 1, OK
        box = keys(page, 'Control+s')                                     # the design itself: told, not kept
        page.wait_for_function("() => /التصميم نفسه|design itself/.test(document.querySelector('.dbprog-status').textContent)", timeout=120000)
        page.mouse.click(box['x'] + 59, box['y'] + 18)                     # File
        page.wait_for_timeout(800)
        page.mouse.click(box['x'] + 81, box['y'] + 324)                    # Export PDF…
        page.wait_for_timeout(1500)
        page.keyboard.press('Enter')                                       # the dialog's OK
        page.wait_for_selector('.dbprog-ask img', timeout=180000)          # never in its place silently: before and after, and a question
        ask = page.inner_text('.dbprog-ask')
        assert '210 × 297' in ask and '216 × 279' in ask, ask               # the made-up A4 file; the program's Letter page
        assert page.evaluate("() => [...document.querySelectorAll('.dbprog-ask img')].every(i => i.naturalWidth > 0)")
        page.click('.dbprog-ask [data-a="yes"]')
        page.wait_for_function("() => /حُفظت|Saved/.test(document.querySelector('.dbprog-status').textContent)", timeout=180000)
        page.click('.dbprog [data-act="close"]')
        page.wait_for_selector('.dbprog', state='detached', timeout=10000)
        docs = page.evaluate("async id => (await (await fetch(`/api/dossiers/${id}/board`)).json()).slots.find(s => s.slot_id === 'M1-11').documents", did)
        assert [(d['version'], d['filename']) for d in docs] == [(2, 'made-up-layout.pdf')], docs
        data = bytes(page.evaluate("async ([id, doc]) => Array.from(new Uint8Array(await (await fetch(`/api/dossiers/${id}/documents/${doc}/file`)).arrayBuffer()))", [did, docs[0]['id']]))
        assert not errors, errors
        b.close()
    assert data[:5] == b'%PDF-' and len(pypdf.PdfReader(io.BytesIO(data)).pages) >= 1


@pytest.mark.skipif(not (DIST / 'assets' / 'programs' / 'designcraft' / 'glue.js').exists(), reason='built without the design program')
def test_a_new_artwork_made_in_the_design_program_is_the_items_document(site, tmp_path):
    """An empty artwork item (Egypt M1-11, made-up dossier): «Make it in the design program» — a new document (Ctrl+N), File ▸ Export
    PDF… — and the PDF is the item's first document."""
    with pw.sync_playwright() as p:
        b = p.chromium.launch(args=GPU)
        page = b.new_page(viewport={'width': 1280, 'height': 860})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.goto(site + '/index.local.html#/')
        page.evaluate('() => DBWEB.ready()')
        did = page.evaluate("""async () => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
            body: JSON.stringify({name: 'Dermacure (made up)', profile: {dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', apis: [{name: 'Exampletine', manufacturer: 'Example API Co.', option: 'CEP'}]},
            product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""")
        page.evaluate('id => { location.hash = `#/d/${id}/board`; }', did)
        page.wait_for_function("id => typeof S === 'object' && S.dossier && S.dossier.id === id && S.board", arg=did, timeout=60000)
        page.evaluate("() => openWhy('M1-11')")
        page.click('[data-designnew]')
        started(page, 'designcraft')
        page.wait_for_timeout(1500)
        box = keys(page, 'Control+n', 'Enter')
        page.mouse.click(box['x'] + 59, box['y'] + 18)                     # File
        page.wait_for_timeout(800)
        page.mouse.click(box['x'] + 81, box['y'] + 324)                    # Export PDF…
        page.wait_for_timeout(1500)
        page.keyboard.press('Enter')
        page.wait_for_function("() => /حُفظت|Saved/.test(document.querySelector('.dbprog-status').textContent)", timeout=180000)
        page.click('.dbprog [data-act="close"]')
        page.wait_for_selector('.dbprog', state='detached', timeout=10000)
        docs = page.evaluate("async id => (await (await fetch(`/api/dossiers/${id}/board`)).json()).slots.find(s => s.slot_id === 'M1-11').documents", did)
        assert len(docs) == 1 and docs[0]['version'] == 1 and docs[0]['filename'].endswith('.pdf'), docs
        assert not errors, errors
        b.close()
