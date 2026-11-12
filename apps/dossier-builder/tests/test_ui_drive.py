"""The Drive picker in the browser (Playwright): paste a folder link in the wizard, see the files, pick, and the intake reads them
exactly like uploads — against the stand-in for Google's HTTP from test_drive.py."""
import json, socket, threading, time, urllib.parse
import pytest
from fixtures_pdf import make_pdf_lines
from dossier_engine import drive

pw = pytest.importorskip('playwright.sync_api')
OUT = '/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/arabic'


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


def test_wizard_reads_a_drive_folder(server, tmp_path):
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure', 'Dosage Form: Topical Powder',
                                                     'Active Ingredient(s) & Strength(s): Each 1g contains:', 'NEOMYCIN SULPHATE 3.500 mg ( 3300 unit )', 'License Holder : EXAMPLE PHARM-EGYPT,EGYPT'], 'Licence').read_bytes()
    listing = {'files': [{'id': 'subfolder_0001', 'name': 'Module 3', 'mimeType': drive.FOLDER}, {'id': 'f1', 'name': 'licence.pdf', 'mimeType': 'application/pdf', 'size': str(len(pdf))},
                         {'id': 'z1', 'name': 'movie.mp4', 'mimeType': 'video/mp4', 'size': '9'}]}

    def http(method, url, headers, data):
        u = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(u.query)
        if u.path == '/drive/v3/files':
            return 200, 'application/json', json.dumps(listing).encode()
        if u.path == '/drive/v3/files/f1' and q.get('alt') == ['media']:
            return 200, 'application/pdf', pdf
        return 500, 'text/plain', b'unexpected'
    drive.HTTP = http
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={'width': 1440, 'height': 960}, device_scale_factor=2)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
            page.add_init_script("localStorage.setItem('db.lang','ar')")
            page.goto(server + '/#/new')
            page.wait_for_selector('#intakeDrive')
            page.click('#intakeDrive')
            page.wait_for_selector('#drvLink')
            # no key yet on a server: public mode, the settings form is not forced; set an API key through the gear
            page.click('#drvGear'); page.wait_for_selector('#drvKey'); page.fill('#drvKey', 'AIzaTESTKEY0000000000'); page.click('#drvSave')
            page.wait_for_selector('#drvKey', state='detached')                                  # saved: the form closes, the chip shows the mode
            assert 'مفتاح Google API' in page.inner_text('#drawer .chip')
            page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv?usp=sharing')
            page.click('#drvList')
            page.wait_for_selector('[data-drvsel]')
            rows = page.inner_text('#drvFiles')
            assert 'Module 3' in rows and 'licence.pdf' in rows and 'movie.mp4' in rows
            assert page.is_checked('[data-drvsel="1"]') and page.is_disabled('[data-drvsel="2"]')     # the PDF is picked, the HEIC cannot be read
            page.locator('#drawer').screenshot(path=f'{OUT}/drive_picker_ar.png')
            page.click('#drvUse')
            page.wait_for_selector('#intakeReview', timeout=120000); page.click('#intakeReview'); page.wait_for_selector('#intakeApply')
            page.wait_for_function("document.querySelector('#rv-name') && document.querySelector('#rv-name').value === 'Dermacure'", timeout=20000)
            assert page.input_value('#rv-form') == 'powder-topical' and page.input_value('[data-rva="0"][data-f=name]') == 'Neomycin Sulphate'
            assert 'licence.pdf' in page.inner_text('#dBody')
            assert not errors, errors
            b.close()
    finally:
        drive.HTTP = None


def test_browser_edition_reads_a_link_through_the_viewers_drive_connector(server, tmp_path):
    """claude.ai: `window.claude.use('mcp')` gives the page the viewer's own Google Drive connector — no key, nothing to share.
    A stand-in for that capability answers search_files / get_file_metadata / download_file_content the way the connector does."""
    import base64
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure', 'Dosage Form: Topical Powder',
                                                     'Active Ingredient(s) & Strength(s): Each 1g contains:', 'NEOMYCIN SULPHATE 3.500 mg ( 3300 unit )', 'License Holder : EXAMPLE PHARM-EGYPT,EGYPT'], 'Licence').read_bytes()
    b64 = base64.b64encode(pdf).decode()
    stub = """
    window.__mcpCalls = [];
    const FOLDER = 'application/vnd.google-apps.folder';
    const tree = {'1AbCdEfGhIjKlMnOpQrStUv': [{id:'subfolder_0001', title:'Module 3', mimeType: FOLDER}, {id:'f1', title:'licence.pdf', mimeType:'application/pdf', fileSize:'%d'},
                                                 {id:'z1', title:'movie.mp4', mimeType:'video/mp4', fileSize:'9'}, {id:'g1', title:'SmPC draft', mimeType:'application/vnd.google-apps.document'}],
                  'subfolder_0001': [{id:'f2', title:'spec.pdf', mimeType:'application/pdf', fileSize:'5'}]};
    const mcp = {
      async listTools(server){ return {servers:[{server:'Google Drive', authStatus:'connected', tools:[{name:'search_files'},{name:'get_file_metadata'},{name:'download_file_content'}]}]}; },
      async callTool(server, tool, input){ window.__mcpCalls.push([server, tool, input]);
        if(server!=='Google Drive') throw {code:'not_in_manifest', message:'no'};
        if(tool==='search_files'){ const m=/parentId = '([^']+)'/.exec(input.query); return {payload:{files: tree[m[1]]||[]}}; }
        if(tool==='get_file_metadata') return {payload:{id:input.fileId, title:'single.pdf', mimeType:'application/pdf', fileSize:'%d'}};
        if(tool==='download_file_content'){ if(input.fileId==='f1'||input.fileId==='f2') return {payload:{content:'%s', id:input.fileId, mimeType:'application/pdf', title:'licence.pdf'}};
          throw {code:'tool_error', message:'File not found'}; }
        throw {code:'bad_request', message:'unknown tool '+tool}; } };
    window.claude = { use: async name => name==='mcp' ? mcp : null };
    """ % (len(pdf), len(pdf), b64)
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.add_init_script(stub)
        page.goto(server + '/#/new')
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        assert 'من غير مفتاح' in page.inner_text('#drawer .chip')                              # connector mode, announced
        assert page.locator('#drvKey').count() == 0                                             # no key form forced
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv?usp=sharing')
        page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        rows = page.inner_text('#drvFiles')
        assert 'Module 3' in rows and 'licence.pdf' in rows and 'movie.mp4' in rows and 'SmPC draft.docx' in rows   # a Google Doc is offered as Word
        assert page.is_checked('[data-drvsel="1"]') and page.is_disabled('[data-drvsel="2"]')
        page.click('[data-drvopen="subfolder_0001"]'); page.wait_for_function("() => document.querySelector('#drvFiles').textContent.includes('spec.pdf')")
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList')
        page.wait_for_function("() => document.querySelector('#drvFiles').textContent.includes('licence.pdf')")
        page.uncheck('[data-drvsel="3"]')                                                        # leave the Google Doc out: the stand-in has no bytes for it
        page.click('#drvUse')
        page.wait_for_selector('#intakeReview', timeout=120000); page.click('#intakeReview'); page.wait_for_selector('#intakeApply')
        page.wait_for_function("() => document.querySelector('#rv-name') && document.querySelector('#rv-name').value === 'Dermacure'", timeout=20000)
        calls = page.evaluate("() => window.__mcpCalls.map(c => c[1])")
        assert calls.count('download_file_content') == 1 and 'search_files' in calls
        assert all(c[0] == 'Google Drive' for c in page.evaluate("() => window.__mcpCalls"))
        assert not errors, errors
        b.close()


# ---------------------------------------------------------------- the Drive panel says what it is doing, and reads old Word files
import base64, pathlib
DATA = pathlib.Path(__file__).parent / 'data'


def connector_stub(tree_js, files_js, delay_ms=0):
    """A stand-in for claude.ai's connector capability: `tree` = folder id → entries (as search_files gives them),
    `files` = file id → base64 content, or {error:'…'} for a file Drive refuses."""
    return """
    window.__mcpCalls = [];
    const FOLDER = 'application/vnd.google-apps.folder';
    const tree = %s, files = %s;
    const mcp = {
      async listTools(server){ return {servers:[{server:'Google Drive', authStatus:'connected', tools:[{name:'search_files'},{name:'get_file_metadata'},{name:'download_file_content'}]}]}; },
      async callTool(server, tool, input){ window.__mcpCalls.push([server, tool, input]); await new Promise(r=>setTimeout(r, %d));
        if(tool==='search_files'){ const m=/parentId = '([^']+)'/.exec(input.query); if(!(m[1] in tree)) throw {code:'tool_error', message:'File not found'}; return {payload:{files: tree[m[1]]}}; }
        if(tool==='download_file_content'){ const f=files[input.fileId]; if(!f) throw {code:'tool_error', message:'File not found'}; if(f.error) throw {code:f.code||'tool_error', message:f.error};
          return {payload:{content:f, id:input.fileId, mimeType:'application/octet-stream', title:'x'}}; }
        throw {code:'bad_request', message:'unknown tool '+tool}; } };
    window.claude = { use: async name => name==='mcp' ? mcp : null };
    """ % (tree_js, files_js, delay_ms)


def open_page(p, server, stub, hash_='#/new'):
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': 1440, 'height': 960})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','ar')")
    page.add_init_script(stub)
    page.goto(server + '/' + hash_)
    return b, page, errors


def test_old_word_files_are_selectable_and_read_by_what_is_inside_them(server, tmp_path):
    """The owner's case: a Drive folder with Word 97-2003 files (.doc). They are offered like every readable document, a title with no
    extension gets the one of its Drive type, and what the wizard knows of each file is what is written in it."""
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure', 'Dosage Form: Topical Powder'], 'Licence').read_bytes()
    b64 = lambda data: base64.b64encode(data).decode()
    tree = json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': [
        {'id': 'd1', 'title': 'pricing.doc', 'mimeType': 'application/msword', 'fileSize': '19968'},                     # a misleading name: it is a stability protocol
        {'id': 'd2', 'title': 'تعهد', 'mimeType': 'application/msword', 'fileSize': '19456'},                               # a title with no extension
        {'id': 'f1', 'title': 'licence.pdf', 'mimeType': 'application/pdf', 'fileSize': str(len(pdf))},
        {'id': 'z1', 'title': 'archive.rar', 'mimeType': 'application/rar', 'fileSize': '9'}]})
    files = json.dumps({'d1': b64((DATA / 'dermacure-protocol.doc').read_bytes()), 'd2': b64((DATA / 'dermacure-undertaking.doc').read_bytes()), 'f1': b64(pdf)})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(tree, files))
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        rows = page.inner_text('#drvFiles')
        assert 'pricing.doc' in rows and 'تعهد.doc' in rows and 'Word (.doc)' in rows
        state = page.evaluate("() => [...document.querySelectorAll('[data-drvsel]')].map(c => [c.closest('tr').innerText.split('\\t')[1] || c.closest('tr').innerText, c.checked, c.disabled])")
        assert sum(1 for _, checked, disabled in state if checked and not disabled) == 3 and not any(d for _, c, d in state), state
        assert [c for n, c, d in state if 'archive.rar' in n] == [False]                                               # the compressed file is offered, not ticked
        assert '3' in page.inner_text('#drvCount')
        page.click('#drvUse')
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 3 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=120000)
        kinds = page.evaluate("() => S.wiz.kinds")
        assert kinds['pricing.doc'] == 'stability' and kinds['licence.pdf'] == 'licence', kinds                         # by its content, not by «pricing» in its name
        assert page.evaluate("() => S.wiz.texts['تعهد.doc'].text.slice(0, 5)") == 'إقرار'
        assert page.evaluate("() => localStorage.getItem('db.drive.link')").endswith('1AbCdEfGhIjKlMnOpQrStUv')       # the link is kept for the next place it is needed
        assert not errors, errors
        b.close()


def test_the_panel_shows_progress_and_keeps_what_failed_with_its_reason(server, tmp_path):
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure'], 'Licence').read_bytes()
    tree = json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': [{'id': 'f1', 'title': 'licence.pdf', 'mimeType': 'application/pdf', 'fileSize': str(len(pdf))},
                                                   {'id': 'f2', 'title': 'huge scan.pdf', 'mimeType': 'application/pdf', 'fileSize': '99000000'},
                                                   {'id': 'sub1', 'title': 'Module 3', 'mimeType': drive.FOLDER}],
                       'sub1': [{'id': 'f3', 'title': 'spec.pdf', 'mimeType': 'application/pdf', 'fileSize': str(len(pdf))}]})
    files = json.dumps({'f1': base64.b64encode(pdf).decode(), 'f2': {'error': 'File too large to download'}, 'f3': base64.b64encode(pdf).decode()})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(tree, files, delay_ms=350))
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.check('#drvRec'); page.click('#drvList')
        page.wait_for_selector('#drvProg')                                                     # reading the folder is announced on the panel, not in a passing toast
        page.wait_for_function("() => document.querySelector('#drvFiles').textContent.includes('Module 3/spec.pdf')")
        assert page.locator('#drvProg').count() == 0
        page.click('#drvUse')
        page.wait_for_selector('#drvBar')                                              # fetching: a bar and a count
        page.wait_for_selector('#drvFails')
        fails = page.inner_text('#drvFails')
        assert 'huge scan.pdf' in fails and 'File too large to download' in fails            # the file and Drive's own reason stay on the panel
        assert page.locator('#drawer.open, #drawer:not([hidden])').count() >= 1 and page.locator('#drvGo').count() == 1
        assert page.evaluate("() => !(typeof S !== 'undefined' && S.wiz && S.wiz.allFiles && S.wiz.allFiles.length)")        # nothing is handed over behind the person's back
        page.click('#drvGo')                                                                   # go on with the two that came
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 2 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=120000)
        assert sorted(page.evaluate("() => Object.keys(S.wiz.kinds)")) == ['licence.pdf', 'spec.pdf']                   # the file inside the sub-folder keeps its own name
        assert not errors, errors
        b.close()


def test_a_large_folder_is_not_taken_whole_without_being_asked(server, tmp_path):
    pdf = make_pdf_lines(tmp_path / 'a.pdf', ['Certificate of Analysis', 'Product: Dermacure', 'Batch No.: 240101'], 'CoA').read_bytes()
    entries = [{'id': f'f{i}', 'title': f'scan {i:03d}.pdf', 'mimeType': 'application/pdf', 'fileSize': '4000000'} for i in range(60)]
    tree = json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': entries})
    files = json.dumps({f'f{i}': base64.b64encode(pdf).decode() for i in range(60)})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(tree, files))
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        assert page.evaluate("() => [...document.querySelectorAll('[data-drvsel]')].filter(c => c.checked).length") == 0     # sixty files: the person chooses
        assert '60' in page.inner_text('#drvNote')
        page.click('#drvAll')
        assert page.evaluate("() => [...document.querySelectorAll('[data-drvsel]')].filter(c => c.checked).length") == 60
        page.click('#drvUse')
        page.wait_for_selector('#drvNote')
        assert '240' in page.inner_text('#drvNote') and page.evaluate("() => window.__mcpCalls.filter(c => c[1] === 'download_file_content').length") == 0   # 60 files, 240 MB: asked first
        page.click('#drvNone'); page.check('[data-drvsel="0"]'); page.check('[data-drvsel="1"]'); page.click('#drvUse')
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 2", timeout=120000)
        assert page.evaluate("() => window.__mcpCalls.filter(c => c[1] === 'download_file_content').length") == 2
        assert not errors, errors
        b.close()


def test_drive_is_offered_on_every_item_of_the_board(server, tmp_path):
    """A single item takes its document from Drive too: one file is chosen and it goes through the same checks as an upload."""
    from test_reading_cases import PROFILE, PRODUCT, ENV, PRICE_EN
    import urllib.request
    pdf = make_pdf_lines(tmp_path / 'price.pdf', PRICE_EN.split('\n'), 'Pricing').read_bytes()
    req = urllib.request.Request(server + '/api/dossiers', data=json.dumps(dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).encode(),
                                 headers={'content-type': 'application/json', 'X-DB': '1'})
    did = json.loads(urllib.request.urlopen(req).read())['id']
    tree = json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': [{'id': 'f1', 'title': 'scan0007.pdf', 'mimeType': 'application/pdf', 'fileSize': str(len(pdf))},
                                                   {'id': 'f2', 'title': 'other.pdf', 'mimeType': 'application/pdf', 'fileSize': '5'}]})
    files = json.dumps({'f1': base64.b64encode(pdf).decode()})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(tree, files), f'#/d/{did}/board')
        page.wait_for_selector('[data-updrv]')
        assert page.locator('[data-updrv]').count() == page.locator('[data-up]').count()                 # wherever a file can be uploaded, Drive is offered
        page.click('[data-updrv="M1-05"]'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        assert page.get_attribute('[data-drvsel="0"]', 'type') == 'radio' and page.locator('#drvAll').count() == 0     # one item, one file
        page.check('[data-drvsel="1"]'); page.click('#drvUse')
        def docs():
            r = urllib.request.urlopen(urllib.request.Request(f'{server}/api/dossiers/{did}/board', headers={'X-DB': '1'}))
            return next(s for s in json.loads(r.read())['slots'] if s['slot_id'] == 'M1-05')['documents']
        deadline = time.time() + 60
        while time.time() < deadline and not docs():
            page.wait_for_timeout(300)
        assert [d['filename'] for d in docs()] == ['scan0007.pdf']                                  # the file chosen in Drive is in the item
        assert not errors, errors
        b.close()


def test_every_document_type_old_and_new_is_offered_and_read_by_its_content(server, tmp_path):
    """Excel, PowerPoint and RTF files (old formats and new) are ticked like PDFs; a file with no extension and a general type is
    offered but not ticked, and read by its bytes once fetched; so is a compressed file; lock files, system files and empty files are
    left out, each with its reason in the type column."""
    import gzip
    office = DATA / 'office'
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure', 'Dosage Form: Topical Powder'], 'Licence').read_bytes()
    b64 = lambda data: base64.b64encode(data).decode()
    entries = [
        {'id': 'x1', 'title': 'pricing.xls', 'mimeType': 'application/vnd.ms-excel', 'fileSize': '7168'},                          # a stability sheet under a misleading name
        {'id': 'p1', 'title': 'overview.ppt', 'mimeType': 'application/vnd.ms-powerpoint', 'fileSize': '461824'},
        {'id': 'r1', 'title': 'letter', 'mimeType': 'application/rtf', 'fileSize': '20385'},                                        # no extension: Drive's type names it
        {'id': 'u1', 'title': 'scan0001', 'mimeType': 'application/octet-stream', 'fileSize': str(len(pdf))},                       # no extension, general type: a PDF inside
        {'id': 's1', 'title': 'Thumbs.db', 'mimeType': 'application/octet-stream', 'fileSize': '9000'},
        {'id': 's2', 'title': '~$report.docx', 'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'fileSize': '162'},
        {'id': 'e1', 'title': 'empty.docx', 'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'fileSize': '0'},
        {'id': 'a1', 'title': 'backup.rar', 'mimeType': 'application/rar', 'fileSize': '5000'}]
    files = json.dumps({'x1': b64((office / 'sheet.xls').read_bytes()), 'p1': b64(gzip.decompress((office / 'slides.ppt.gz').read_bytes())), 'r1': b64((office / 'letter.rtf').read_bytes()), 'u1': b64(pdf)})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': entries}), files))
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        rows = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#drvFiles tbody tr')].map(tr => { const c = tr.querySelector('[data-drvsel]'), td = tr.querySelectorAll('td'); return [td[1].innerText.trim(), [c.checked, c.disabled, td[2].innerText.trim()]]; }))")
        assert rows['pricing.xls'] == [True, False, 'Excel (.xls)'] and rows['overview.ppt'] == [True, False, 'PowerPoint (.ppt)'] and rows['letter.rtf'] == [True, False, 'RTF'], rows
        assert rows['scan0001'][:2] == [False, False]                                                # offered, not ticked
        assert rows['Thumbs.db'] == [False, True, 'ملف نظام'] and rows['~$report.docx'] == [False, True, 'ملف نظام'] and rows['empty.docx'] == [False, True, 'ملف فاضي'], rows
        assert rows['backup.rar'][:2] == [False, False] and 'مضغوط' in rows['backup.rar'][2]            # a compressed file: offered, not ticked, opened after it is fetched
        page.check('tr:has-text("scan0001") [data-drvsel]'); page.click('#drvUse')
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 4 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=180000)
        kinds = page.evaluate("() => S.wiz.kinds")
        assert kinds == {'pricing.xls': 'stability', 'overview.ppt': 'stability', 'letter.rtf': 'pricing', 'scan0001': 'licence'}, kinds
        assert 'Assay of Neomycin sulphate | 90.0% - 110.0% | 99.6' in page.evaluate("() => S.wiz.texts['pricing.xls'].text")
        assert not errors, errors
        b.close()


def test_an_old_excel_file_from_this_computer_goes_through_the_wizard(server, tmp_path):
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, 'window.__none = 1;')
        page.wait_for_selector('#intakeBtn')
        assert '.xls' in page.get_attribute('#picker', 'accept') and '.ppt' in page.get_attribute('#picker', 'accept') and '.rtf' in page.get_attribute('#picker', 'accept')
        with page.expect_file_chooser() as fc:
            page.click('#intakeBtn')
        fc.value.set_files([str(DATA / 'office' / 'sheet.xls'), str(DATA / 'office' / 'slides.pptx'), str(DATA / 'office' / 'letter.odt')])
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 3 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=180000)
        assert page.evaluate("() => S.wiz.kinds") == {'sheet.xls': 'stability', 'slides.pptx': 'stability', 'letter.odt': 'pricing'}
        assert not errors, errors
        b.close()


def test_a_compressed_file_in_a_drive_folder_gives_the_documents_inside_it(server, tmp_path):
    """A ZIP in the folder is offered without being ticked; ticked, it is fetched, opened, and the documents inside it are read."""
    import io, zipfile
    pdf = make_pdf_lines(tmp_path / 'licence.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure', 'Dosage Form: Topical Powder'], 'Licence').read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Dermacure/licence.pdf', pdf)
        z.writestr('Dermacure/ملاحظات التسعير.txt', 'Pricing Certificate\nProduct: Dermacure\nPrice: EGP 45.00'.encode())
        z.writestr('__MACOSX/Dermacure/._licence.pdf', b'x')
    tree = json.dumps({'1AbCdEfGhIjKlMnOpQrStUv': [{'id': 'z1', 'title': 'Dermacure documents.zip', 'mimeType': 'application/zip', 'fileSize': str(len(buf.getvalue()))}]})
    files = json.dumps({'z1': base64.b64encode(buf.getvalue()).decode()})
    with pw.sync_playwright() as p:
        b, page, errors = open_page(p, server, connector_stub(tree, files))
        page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList'); page.wait_for_selector('[data-drvsel]')
        assert not page.is_checked('[data-drvsel]') and not page.is_disabled('[data-drvsel]')                          # offered, the person decides
        page.check('[data-drvsel]'); page.click('#drvUse')
        page.wait_for_function("() => typeof S !== 'undefined' && S.wiz && S.wiz.kinds && Object.keys(S.wiz.kinds).length === 2 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=120000)
        assert page.evaluate("() => Object.keys(S.wiz.kinds).sort()") == ['licence.pdf', 'ملاحظات التسعير.txt']
        assert page.evaluate("() => S.wiz.kinds['licence.pdf']") == 'licence'
        assert not errors, errors
        b.close()
