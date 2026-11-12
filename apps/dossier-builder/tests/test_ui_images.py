"""Images of every kind in the browser: the page's own pipeline (ocr.js) decodes them — a TIFF page by page, a HEIC photo through
libheif, BMP/GIF/WebP/AVIF through the browser, a phone photo turned the way its EXIF says — reads them (tesseract.js) and turns an
image placed in an item into a PDF. Needs web/vendor (web/vendor.sh): skipped when the browser OCR assets are not there."""
import json, pathlib, socket, threading, time, urllib.request
import pytest
from test_reading_cases import PROFILE, PRODUCT, ENV

pw = pytest.importorskip('playwright.sync_api')
ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'web' / 'vendor'
FX = pathlib.Path(__file__).parent / 'data' / 'images'
HEIC = VENDOR / 'img' / 'test' / 'example.heic'
pytestmark = pytest.mark.skipif(not (VENDOR / 'tess' / 'tesseract.min.js').exists() or not (VENDOR / 'img' / 'UTIF.js').exists(), reason='browser OCR assets not vendored (web/vendor.sh)')


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


@pytest.fixture()
def page(server):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1440, 'height': 960})
        pg.errors = []
        pg.on('pageerror', lambda e: pg.errors.append(str(e)))
        pg.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        pg.add_init_script("localStorage.setItem('db.lang','en')")
        pg.goto(server + '/#/')
        pg.wait_for_function("() => window.DBOCR && window.DS")
        pg.evaluate("() => { const i = document.createElement('input'); i.type = 'file'; i.id = 'fxin'; document.body.appendChild(i); }")
        yield pg
        assert not pg.errors, pg.errors
        b.close()


READ = """async () => { const f = document.querySelector('#fxin').files[0];
    const pages = await DBOCR.images(f, 4); const bmp = await createImageBitmap(pages[0]);
    const o = await DBOCR.readFile(f, {maxPages: 4});
    return {pages: pages.length, size: [bmp.width, bmp.height], text: o.text}; }"""


@pytest.mark.parametrize('name,pages', [('page.png', 1), ('page.jpg', 1), ('page.gif', 1), ('page.bmp', 1), ('page.webp', 1), ('page.avif', 1), ('page-g4.tif', 1), ('page-deflate.tif', 1),
                                        ('pages-g4.tif', 3), ('phone-rotated.jpg', 1), ('page-alpha.png', 1)])
def test_the_browser_reads_every_kind_of_image(page, name, pages):
    page.set_input_files('#fxin', str(FX / name))
    r = page.evaluate(READ)
    assert r['pages'] == pages and r['size'] == [1240, 700], r                                   # decoded, and upright (the phone photo is stored on its side)
    assert 'Pricing Certificate' in r['text'] and 'Dermacure' in r['text']
    if pages == 3:
        assert 'Page two' in r['text'] and 'Page three' in r['text']


@pytest.mark.skipif(not HEIC.exists(), reason='no HEIC sample (web/vendor.sh fetches one)')
def test_an_iphone_photo_is_decoded_in_the_browser(page):
    page.set_input_files('#fxin', str(HEIC))
    r = page.evaluate("""async () => { const f = document.querySelector('#fxin').files[0]; const pages = await DBOCR.images(f, 1); const bmp = await createImageBitmap(pages[0]);
        const c = document.createElement('canvas'); c.width = 64; c.height = 64; const g = c.getContext('2d'); g.drawImage(bmp, 0, 0, 64, 64);
        const d = g.getImageData(0, 0, 64, 64).data; const seen = new Set(); for (let i = 0; i < d.length; i += 4) seen.add((d[i] >> 4) + ',' + (d[i + 1] >> 4) + ',' + (d[i + 2] >> 4));
        return {type: pages[0].type, size: [bmp.width, bmp.height], colours: seen.size}; }""")
    assert r['type'] == 'image/jpeg' and r['size'] == [1280, 854] and r['colours'] > 50, r      # a real picture came out of the HEVC stream, not a blank


def test_what_no_decoder_here_opens_says_so(page):
    page.set_input_files('#fxin', {'name': 'scan.xyz', 'mimeType': 'image/x-unknown', 'buffer': b'\x00\x01\x02\x03 not an image at all ' * 20})
    msg = page.evaluate("async () => { try { await DBOCR.images(document.querySelector('#fxin').files[0], 1); return 'opened'; } catch (e) { return String(e.message); } }")
    assert 'cannot open this kind of image' in msg


def test_an_image_put_in_an_item_is_stored_as_a_pdf(server):
    req = urllib.request.Request(server + '/api/dossiers', data=json.dumps(dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).encode(),
                                 headers={'content-type': 'application/json', 'X-DB': '1'})
    did = json.loads(urllib.request.urlopen(req).read())['id']
    board = lambda: json.loads(urllib.request.urlopen(urllib.request.Request(f'{server}/api/dossiers/{did}/board', headers={'X-DB': '1'})).read())
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_selector('[data-up="M1-05"]')
        with page.expect_file_chooser() as fc:
            page.click('[data-up="M1-05"]')
        fc.value.set_files(str(FX / 'pages-g4.tif'))                                              # a three-page fax-compressed scan
        deadline = time.time() + 120                                                              # the page decodes the three pages, the engine wraps them
        while time.time() < deadline and not next(s for s in board()['slots'] if s['slot_id'] == 'M1-05')['documents']:
            page.wait_for_timeout(300)
        slot = next(s for s in board()['slots'] if s['slot_id'] == 'M1-05')
        assert slot['documents'], (slot, page.inner_text('#toast'))
        doc = slot['documents'][0]
        assert doc['filename'] == 'pages-g4.pdf'
        from pypdf import PdfReader
        import io
        pdf = urllib.request.urlopen(urllib.request.Request(f"{server}/api/dossiers/{did}/documents/{doc['id']}/file", headers={'X-DB': '1'})).read()
        assert len(PdfReader(io.BytesIO(pdf)).pages) == 3
        assert not errors, errors
        b.close()
