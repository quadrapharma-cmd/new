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
                         {'id': 'z1', 'name': 'photo.heic', 'mimeType': 'image/heic', 'size': '9'}]}

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
            assert 'Module 3' in rows and 'licence.pdf' in rows and 'photo.heic' in rows
            assert page.is_checked('[data-drvsel="1"]') and page.is_disabled('[data-drvsel="2"]')     # the PDF is picked, the HEIC cannot be read
            page.locator('#drawer').screenshot(path=f'{OUT}/drive_picker_ar.png')
            page.click('#drvUse')
            page.wait_for_selector('#intakeApply', timeout=120000)
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
                                                 {id:'z1', title:'photo.heic', mimeType:'image/heic', fileSize:'9'}, {id:'g1', title:'SmPC draft', mimeType:'application/vnd.google-apps.document'}],
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
        assert 'Module 3' in rows and 'licence.pdf' in rows and 'photo.heic' in rows and 'SmPC draft.docx' in rows   # a Google Doc is offered as Word
        assert page.is_checked('[data-drvsel="1"]') and page.is_disabled('[data-drvsel="2"]')
        page.click('[data-drvopen="subfolder_0001"]'); page.wait_for_function("() => document.querySelector('#drvFiles').textContent.includes('spec.pdf')")
        page.fill('#drvLink', 'https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv'); page.click('#drvList')
        page.wait_for_function("() => document.querySelector('#drvFiles').textContent.includes('licence.pdf')")
        page.uncheck('[data-drvsel="3"]')                                                        # leave the Google Doc out: the stand-in has no bytes for it
        page.click('#drvUse')
        page.wait_for_selector('#intakeApply', timeout=120000)
        page.wait_for_function("() => document.querySelector('#rv-name') && document.querySelector('#rv-name').value === 'Dermacure'", timeout=20000)
        calls = page.evaluate("() => window.__mcpCalls.map(c => c[1])")
        assert calls.count('download_file_content') == 1 and 'search_files' in calls
        assert all(c[0] == 'Google Drive' for c in page.evaluate("() => window.__mcpCalls"))
        assert not errors, errors
        b.close()
