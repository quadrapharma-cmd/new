"""Images of every kind are told by their bytes, read (OCR) page by page, and become a PDF when they go into an item.
Fixtures: one made-up page («Dermacure» pricing certificate) drawn with Pillow and saved in each format."""
import io, json, pathlib, shutil, struct
import pytest
from fastapi.testclient import TestClient
from dossier_engine import arabic, extract, imagefiles as I, officefiles as O
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV

FX = pathlib.Path(__file__).parent / 'data' / 'images'
fx = lambda name: (FX / name).read_bytes()
needs_ocr = pytest.mark.skipif(not arabic.ocr_available(), reason='tesseract is not installed')
try:
    from PIL import Image
except ImportError:                                                          # the converter is optional
    Image = None
needs_pillow = pytest.mark.skipif(Image is None, reason='Pillow is not installed')


@pytest.mark.parametrize('name,fmt', [('page.png', 'png'), ('page.jpg', 'jpeg'), ('page.gif', 'gif'), ('page.webp', 'webp'), ('page.avif', 'avif'), ('page.bmp', 'bmp'),
                                      ('page-g4.tif', 'tiff'), ('pages-g4.tif', 'tiff'), ('page-deflate.tif', 'tiff'), ('phone-rotated.jpg', 'jpeg'), ('page-alpha.png', 'png')])
def test_an_image_is_told_by_its_bytes_whatever_it_is_called(name, fmt):
    for called in (name, 'scan0001', 'report.pdf', 'notes.txt'):
        assert I.image_format(fx(name)) == fmt and O.sniff(called, fx(name)) == 'image'
        assert extract.read_text(called, fx(name), ocr=False)['kind_of_file'] == 'image'


def test_the_other_kinds_by_their_headers():
    heic = struct.pack('>I', 24) + b'ftypheic' + b'\x00\x00\x00\x00' + b'mif1heic' + b'\x00' * 40
    avif = struct.pack('>I', 28) + b'ftypavif' + b'\x00\x00\x00\x00' + b'avifmif1miaf' + b'\x00' * 40
    mif1_avif = struct.pack('>I', 28) + b'ftypmif1' + b'\x00\x00\x00\x00' + b'mif1avifmiaf' + b'\x00' * 40
    assert I.image_format(heic) == 'heic' and I.image_format(avif) == 'avif' and I.image_format(mif1_avif) == 'avif'
    assert I.image_format(b'\x00\x00\x00\x0cjP  \r\n\x87\n' + b'\x00' * 20) == 'jp2' and I.image_format(b'\xff\x4f\xff\x51' + b'\x00' * 20) == 'jp2'
    assert I.image_format(b'P5\n# made by a scanner\n640 480\n255\n' + b'\x00' * 50) == 'pnm' and I.image_format(b'8BPS\x00\x01' + b'\x00' * 30) == 'psd'
    assert I.image_format(b'II+\x00\x08\x00\x00\x00' + b'\x00' * 20) == 'tiff'                      # BigTIFF
    assert I.image_mime(fx('page.jpg')) == 'image/jpeg' and arabic.image_type(heic) == 'image/heic'


def test_text_and_other_files_are_not_taken_for_images():
    for data in (b'BMR-001 batch manufacturing record\nProduct: Dermacure\n' * 5, b'BM', b'P5 is the fifth page of the protocol\n' * 4, b'GIF8 is not enough', b'II is a roman numeral\n' * 3,
                 b'RIFF\x24\x00\x00\x00WAVEfmt ' + b'\x00' * 40, b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom' + b'\x00' * 40, b'\x00\x00\x01\x00' + b'\xff' * 40, b'%PDF-1.4'):
        assert I.image_format(data) is None, data[:12]
    assert extract.read_text('bmr.txt', b'BMR-001 batch manufacturing record\nProduct: Dermacure\n' * 5)['kind_of_file'] == 'text'


def test_pages_of_a_tiff_and_the_way_up_of_a_phone_photo():
    assert I.tiff_pages(fx('pages-g4.tif')) == 3 and I.tiff_pages(fx('page-g4.tif')) == 1 and I.tiff_pages(b'II*\x00' + b'\xff' * 12) == 1
    assert I.exif_orientation(fx('phone-rotated.jpg')) == 6 and I.exif_orientation(fx('page.jpg')) in (None, 1) and I.exif_orientation(fx('page.png')) is None
    assert extract.read_text('x', fx('pages-g4.tif'), ocr=False)['pages'] == 3


@needs_ocr
@pytest.mark.parametrize('name', ['page.png', 'page.jpg', 'page.gif', 'page.webp', 'page.bmp', 'page-g4.tif', 'page-deflate.tif', 'page-alpha.png'])
def test_every_kind_is_read(name):
    r = extract.read_text('scan0001', fx(name))
    assert r['ocr'] and 'Pricing Certificate' in r['text'] and 'Dermacure' in r['text'] and extract.content_kind(r['text']) == 'pricing'


@needs_ocr
def test_a_tiff_is_read_page_by_page_up_to_the_limit():
    r = extract.read_text('scan.tif', fx('pages-g4.tif'))
    assert r['pages'] == 3 and 'Pricing Certificate' in r['text'] and 'Page two' in r['text'] and 'Page three' in r['text']
    assert 'Page three' in extract.read_text('scan.tif', fx('pages-g4.tif'), ocr_pages=1)['text']      # the reading already made answers a narrower question
    extract._READ.clear(); extract._KEPT.clear()                                                        # a first reading stops at the limit
    r = extract.read_text('scan.tif', fx('pages-g4.tif'), ocr_pages=1)
    assert 'Pricing Certificate' in r['text'] and 'Page two' not in r['text']
    assert 'Page three' in extract.read_text('scan.tif', fx('pages-g4.tif'))['text']                    # and the first page is not taken for the whole file


@needs_ocr
@needs_pillow
def test_kinds_the_ocr_engine_does_not_open_and_a_photo_on_its_side_go_through_a_conversion(tmp_path):
    assert 'Pricing Certificate' in extract.read_text('IMG_0001.JPG', fx('phone-rotated.jpg'))['text']         # turned the way its EXIF says
    assert 'Pricing Certificate' in extract.read_text('photo', fx('page.avif'))['text']
    im = Image.open(io.BytesIO(fx('page.png')))
    for fmt, kw in (('JPEG2000', {}), ('PCX', {}), ('PPM', {})):
        buf = io.BytesIO(); im.save(buf, fmt, **kw)
        assert 'Pricing Certificate' in extract.read_text('scan', buf.getvalue())['text'], fmt
    png = I.to_png(fx('page.avif'))
    assert png[:8] == b'\x89PNG\r\n\x1a\n' and I.for_model(fx('page.avif'))[0] == 'image/png' and I.for_model(fx('page.jpg')) == ('image/jpeg', fx('page.jpg'))


def read_pdf(pdf):
    from pypdf import PdfReader
    return PdfReader(io.BytesIO(pdf))


def test_jpeg_pages_become_a_pdf_without_being_recompressed():
    jpg = fx('page.jpg')
    assert I.jpeg_info(jpg)[:3] == (1240, 700, 3)
    pdf = I.jpegs_pdf([jpg, fx('phone-rotated.jpg')], 'شهادة تسعير', rotate=[0, 90])
    rd = read_pdf(pdf)
    assert len(rd.pages) == 2 and rd.metadata.title == 'شهادة تسعير' and jpg in pdf                               # the image bytes are in the file as they came
    assert [round(float(v)) for v in rd.pages[0].mediabox[2:]] == [842, 595] and rd.pages[1].get('/Rotate') == 90   # fitted on A4, on its side; the phone photo turned
    w, h = 2480, 3508                                                                                              # a 300-dpi A4 scan keeps its own size
    assert [round(v) for v in I.page_size(w, h, 300)[:2]] == [595, 842] and [round(v) for v in I.page_size(4032, 3024, 72)[:2]] == [842, 595]
    with pytest.raises(ValueError):
        I.jpegs_pdf([b'not a jpeg'])


@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, did


def test_a_photo_placed_in_an_item_becomes_a_pdf(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('IMG_0001.JPG', fx('phone-rotated.jpg'), 'image/jpeg')})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d['filename'] == 'IMG_0001.pdf' and d['meta']['from_image'] == 'IMG_0001.JPG'
    assert not any('Not a PDF' in f['en'] for f in d['findings'])                                  # the old dead end is gone
    assert d['findings'] and all(f['action'] == 'auto_fix' for f in d['findings'])                  # what is left is the scan's text layer: one click (OCR)
    got = c.get(f"/api/dossiers/{did}/documents/{d['id']}/file")
    assert got.headers['content-type'].startswith('application/pdf') and len(read_pdf(got.content).pages) == 1 and read_pdf(got.content).pages[0].get('/Rotate') == 90


@needs_pillow
def test_other_kinds_of_image_become_a_pdf_too_and_a_tiff_keeps_its_pages(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('scan.tif', fx('pages-g4.tif'), 'image/tiff')}).json()
    assert r['filename'] == 'scan.pdf' and len(read_pdf(c.get(f"/api/dossiers/{did}/documents/{r['id']}/file").content).pages) == 3
    for name in ('page.png', 'page.bmp', 'page.gif', 'page.webp', 'page-alpha.png'):
        r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': (name, fx(name), 'application/octet-stream')}).json()
        assert r['filename'].endswith('.pdf') and r['meta']['from_image'] == name, name


def test_an_image_this_machine_cannot_open_is_kept_with_a_plain_reason(dossier, monkeypatch):
    c, did = dossier
    monkeypatch.setattr(I, 'to_jpegs', lambda data, max_pages=200: None)                            # as in the browser edition: no converter in the engine
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('scan.png', fx('page.png'), 'image/png')}).json()
    assert r['filename'] == 'scan.png' and [f['rule'] for f in r['findings']][-1] == 'DOCX-DRAFT' and 'image' in r['findings'][-1]['en'].lower()


def test_the_page_sends_decoded_pages_and_gets_a_pdf(dossier):
    c, did = dossier
    r = c.post('/api/images/pdf', files=[('files', ('p1.jpg', fx('page.jpg'), 'image/jpeg')), ('files', ('p2.jpg', fx('phone-rotated.jpg'), 'image/jpeg'))], data={'title': 'scan.tif'})
    assert r.status_code == 200 and r.headers['content-type'] == 'application/pdf' and len(read_pdf(r.content).pages) == 2
    assert c.post('/api/images/pdf', files=[('files', ('p1.png', fx('page.png'), 'image/png'))]).status_code == 422
    if Image is not None:
        r = c.post('/api/images/png', files={'file': ('x.avif', fx('page.avif'), 'image/avif')})
        assert r.status_code == 200 and r.content[:8] == b'\x89PNG\r\n\x1a\n'
    assert c.post('/api/images/png', files={'file': ('x.txt', b'not an image', 'text/plain')}).status_code == 422
