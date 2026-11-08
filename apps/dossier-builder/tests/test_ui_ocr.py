"""OCR in the browser (tesseract.js): a scanned, image-only PDF uploaded in the wizard on a server WITHOUT tesseract is read in the
page itself, the rules run on that text, and the drawer fills. Needs web/vendor/tess (web/vendor.sh); skipped otherwise."""
import pathlib, socket, threading, time
import pytest

pw = pytest.importorskip('playwright.sync_api')
PIL = pytest.importorskip('PIL.Image')
TESS = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'vendor' / 'tess'
pytestmark = pytest.mark.skipif(not (TESS / 'tesseract.min.js').exists(), reason='web/vendor/tess not fetched')


def scan_pdf(path, lines):
    """An image-only PDF (no text layer) with printed lines: what a scanner produces."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (1240, 1754), 'white')
    dr = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 34)
    except Exception:
        f = ImageFont.load_default()
    y = 120
    for line in lines:
        dr.text((100, y), line, fill='black', font=f)
        y += 70
    img.save(path, 'PDF', resolution=150.0)
    return path


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine import arabic
    from dossier_engine.app.api import create_app
    real = arabic.ocr_available
    arabic.ocr_available = lambda: False                                    # a computer without tesseract
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True
    arabic.ocr_available = real


def test_scan_is_read_by_ocr_in_the_browser(server, tmp_path):
    pdf = scan_pdf(tmp_path / 'scan.pdf', ['Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure',
                                            'Dosage Form: Topical Powder', 'Active Ingredient(s) & Strength(s): Each 1g contains:', 'NEOMYCIN SULPHATE 3.500 mg (3300 unit)',
                                            'Bacitracin Zinc 4.200 mg (250 unit)', 'Registration No.: 29925/2022  Invalidation Date: 10-11-2032', 'License Holder : EXAMPLE PHARM-EGYPT,EGYPT'])
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(server + '/#/new')
        page.wait_for_selector('#intakeBtn')
        assert page.evaluate('window.DBOCR && window.DBOCR.available()')          # the assets are served
        with page.expect_file_chooser() as fc:
            page.click('#intakeBtn')
        fc.value.set_files([str(pdf)])
        page.wait_for_selector('#intakeApply', timeout=240000)                  # the OCR runs in the page (wasm): allow time
        page.wait_for_function("document.querySelector('#rv-name') && document.querySelector('#rv-name').value.length > 0", timeout=20000)
        assert page.input_value('#rv-name') == 'Dermacure' and page.input_value('#rv-form').lower() == 'topical powder'
        assert page.input_value('[data-rva="0"][data-f=name]') == 'Neomycin Sulphate' and page.input_value('[data-rva="0"][data-f=strength]') == '3.500 mg'
        assert page.input_value('#rv-applicant') == 'EXAMPLE PHARM-EGYPT'
        chips = page.inner_text('#dBody')
        assert 'OCR in the browser' in chips and 'not read on this computer' not in chips
        assert page.is_checked('#rvReadable')                                    # the readable-copy option is offered for scans
        assert not errors, errors
        b.close()


def test_make_readable_from_the_item_drawer(server, tmp_path):
    """A scan stored in a company item is blocked (not searchable); «Make readable (OCR)» runs the OCR in the browser and stores a
    new version whose text is searchable while the page images stay as they were."""
    import io, json, urllib.request
    from pypdf import PdfReader
    pdf = scan_pdf(tmp_path / 'spec.pdf', ['Dermacure Topical Powder', 'Finished product specification', 'Shelf life: 36 months'])
    def api(method, path, data=None, headers=None):
        req = urllib.request.Request(server + path, data=data, method=method, headers={'X-DB': '1', **(headers or {})})
        return json.loads(urllib.request.urlopen(req).read())
    did = api('POST', '/api/dossiers', json.dumps({'name': 'Dermacure', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical',
                                                 'leaflet': 'english', 'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'X', 'option': 'FULL'}]},
                                                 'product': {'name': 'Dermacure'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}}).encode(), {'content-type': 'application/json'})['id']
    slot = next(s for s in api('GET', f'/api/dossiers/{did}/board')['slots'] if s['doc_class'] == 'company_technical' and s['status'] != 'not_applicable')
    boundary = 'XxBoundaryXx'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="spec.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode() + pdf.read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    doc = api('POST', f"/api/dossiers/{did}/slots/{slot['slot_id']}/documents", body, {'content-type': f'multipart/form-data; boundary={boundary}'})
    assert any(f['rule'] == 'NTA065-N4' for f in doc['findings'])
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(server + f'/#/d/{did}/board')
        page.wait_for_selector('#bulkBtn')
        page.evaluate(f"openWhy({json.dumps(slot['slot_id'])})")
        page.wait_for_selector('[data-fix]')
        assert 'Make readable (OCR)' in page.inner_text('[data-fix]')
        page.click('[data-fix]')
        page.wait_for_selector('text=Readable copy saved', timeout=240000)
        assert not errors, errors
        b.close()
    slot2 = next(s for s in api('GET', f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == slot['slot_id'])
    assert [d['version'] for d in slot2['documents']] == [2] and slot2['documents'][0]['meta']['ocr_where'] == 'browser'
    assert not any(f['rule'] == 'NTA065-N4' for f in slot2['documents'][0]['findings'])
    text = PdfReader(io.BytesIO(urllib.request.urlopen(server + f"/api/dossiers/{did}/documents/{slot2['documents'][0]['id']}/file").read())).pages[0].extract_text()
    assert 'Dermacure' in text and 'specification' in text.lower()
