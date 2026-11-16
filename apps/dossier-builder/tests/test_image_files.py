"""Images of every kind are told by their bytes. An image is kept, never refused (the owner, 13/11/2026): where PdfCraft is, a PNG,
JPEG, TIFF, GIF or BMP becomes a PDF page, its words are read (OCR, Arabic and English) and the «make searchable» fix gives it its text
layer; an image PdfCraft cannot take (or any image where it is not) is kept with the finding that says what to do (NP.CAPP.065 v5
general note 4: every document a searchable PDF). Fixtures: one made-up page («Dermacure» pricing certificate) drawn with Pillow and
saved in each format."""
from dossier_engine import pdfcraft
OCR = bool(pdfcraft.ocr_info())
PDFCRAFT_TAKES = {'png', 'jpeg', 'gif', 'bmp', 'tiff'}
import io, json, pathlib, shutil, struct
import pytest
from fastapi.testclient import TestClient
from dossier_engine import arabic, extract, imagefiles as I, officefiles as O
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV

FX = pathlib.Path(__file__).parent / 'data' / 'images'
fx = lambda name: (FX / name).read_bytes()


@pytest.mark.parametrize('name,fmt', [('page.png', 'png'), ('page.jpg', 'jpeg'), ('page.gif', 'gif'), ('page.webp', 'webp'), ('page.avif', 'avif'), ('page.bmp', 'bmp'),
                                      ('page-g4.tif', 'tiff'), ('pages-g4.tif', 'tiff'), ('page-deflate.tif', 'tiff'), ('phone-rotated.jpg', 'jpeg'), ('page-alpha.png', 'png')])
def test_an_image_is_told_by_its_bytes_whatever_it_is_called(name, fmt):
    for called in (name, 'scan0001', 'report.pdf', 'notes.txt'):
        assert I.image_format(fx(name)) == fmt and O.sniff(called, fx(name)) == 'image'
        r = extract.read_text(called, fx(name))
        assert r['kind_of_file'] == 'image' and r['scanned'] and extract.has_text(called, fx(name)) == 'image'
        if OCR and fmt in PDFCRAFT_TAKES:                # read by PdfCraft (OCR): the made-up certificate's words
            assert r.get('ocr') and 'dermacure' in r['text'].lower(), (name, r['text'][:200])
        else:
            assert r['text'] == ''


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
    assert extract.read_text('x', fx('pages-g4.tif'))['pages'] == 3


@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, did


@pytest.mark.parametrize('name', ['phone-rotated.jpg', 'page.png', 'pages-g4.tif', 'page.bmp', 'page.gif', 'page.webp', 'page-alpha.png'])
def test_an_image_put_in_an_item_is_kept_and_made_a_searchable_pdf_where_pdfcraft_is(dossier, name):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': (name, fx(name), 'application/octet-stream')})
    assert r.status_code == 201, r.text                                           # kept, never refused
    d = r.json()
    f = {x['rule']: x for x in d['findings']}
    if pdfcraft.available() and I.image_format(fx(name)) in PDFCRAFT_TAKES:
        assert d['filename'].endswith('.pdf') and 'image_to_pdf' in d['meta']['converted'] and d['meta']['original_name'] == name
        assert f['NTA065-N4']['action'] == ('auto_fix' if OCR else 'user_fix')
        if OCR:                                                                    # «Fix»: the text under the picture, the page as it was
            fixed = c.post(f"/api/dossiers/{did}/documents/{d['id']}/fix").json()
            assert 'make_searchable' in [x['op'] for x in fixed['done']], fixed
            new = fixed['document']
            assert 'NTA065-N4' not in {x['rule'] for x in new['findings']}
            text = pdfcraft.page_texts(c.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content)
            assert 'dermacure' in ' '.join(text).lower()
    else:                                                                          # kept with what to do
        assert f['NTA065-N4']['severity'] == 'block' and 'searchable PDF' in f['NTA065-N4']['en'] and 'قابل للبحث' in f['NTA065-N4']['ar']


@pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
def test_a_tiff_of_several_pages_becomes_a_pdf_of_as_many_pages(dossier, monkeypatch):
    """16/11/2026: the image was given to PdfCraft twice and «page 2» taken off — right for an image of one page; a three-page TIFF (a
    fax, a scanner's file) came out as five pages: 1, 3, 1, 2, 3. Its second copy is taken off whole; and where PdfCraft finds another
    number of pages than the file's header says, its own count is the one used."""
    from pypdf import PdfReader
    count = lambda pdf: len(PdfReader(io.BytesIO(pdf)).pages)
    tif = fx('pages-g4.tif')
    assert count(pdfcraft.image_to_pdf(tif, 'pages-g4.tif')) == 3
    c, did = dossier                                                                # and so the document kept in its item
    d = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pages-g4.tif', tif, 'image/tiff')}).json()
    assert d['filename'] == 'pages-g4.pdf' and count(c.get(f"/api/dossiers/{did}/documents/{d['id']}/file").content) == 3
    for one in ('page-g4.tif', 'page-deflate.tif', 'page.png', 'page.jpg', 'page.gif', 'page.bmp'):      # one page stays one page
        assert count(pdfcraft.image_to_pdf(fx(one), one)) == 1, one
    for said in (5, 2, 1):                                                          # a header that says more pages than there are, or fewer
        monkeypatch.setattr(I, 'tiff_pages', lambda data, said=said: said)
        assert count(pdfcraft.image_to_pdf(tif, 'pages-g4.tif')) == 3, said


@pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
def test_the_pages_of_a_tiff_keep_their_order_in_the_pdf(monkeypatch):
    pytest.importorskip('PIL.Image')
    import image_pages
    tif = fx('pages-g4.tif')
    assert image_pages.shows(pdfcraft.image_to_pdf(tif, 'pages-g4.tif'), tif) == [1, 2, 3]
    for said in (5, 2, 1):
        monkeypatch.setattr(I, 'tiff_pages', lambda data, said=said: said)
        assert image_pages.shows(pdfcraft.image_to_pdf(tif, 'pages-g4.tif'), tif) == [1, 2, 3], said


def test_an_image_is_kept_aside_too(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('IMG_0001.JPG', fx('phone-rotated.jpg'), 'image/jpeg'))], data={'meta': '{}'})
    assert r.status_code == 201, r.text
    assert c.get(f'/api/dossiers/{did}/board').json()['unassigned']
    assert c.post('/api/images/pdf', files=[('files', ('p1.jpg', fx('page.jpg'), 'image/jpeg'))]).status_code in (404, 405)        # no picture-to-PDF service any more


@pytest.mark.skipif(not OCR, reason='needs recognition (PdfCraft OCR)')
def test_a_phone_photo_taken_sideways_is_turned_upright():
    """A phone lying flat on a desk does not know how it is held, so a photo of a sheet often comes sideways (5 of the owner's 21
    WhatsApp photos of documents, 15/11/2026). The page reader's own test (pdfcraft.upright_turn, as ocr.js turnOf) turns it upright —
    the page's /Rotate only, the picture is not written again — and the page is then read upright. An upright photo, a photo upright
    by its EXIF turn and a PNG (a screenshot or a drawing, whose turn is its maker's) stay as they are. Fixture: a made-up supply
    order turned a quarter clockwise (the top of the sheet at the right edge, as his photos came), no EXIF."""
    from pypdf import PdfReader
    pdf, turn = pdfcraft.photo_page(fx('phone-sideways.jpg'), 'IMG-20250318.jpg')
    assert turn == 270 and PdfReader(io.BytesIO(pdf)).pages[0].get('/Rotate') == 270
    assert 'supply order 40417' in pdfcraft.page_texts(pdfcraft.ocr(pdf)[0])[0].lower()
    assert pdfcraft.photo_page(fx('page.jpg'), 'page.jpg')[1] == 0 and pdfcraft.photo_page(fx('phone-rotated.jpg'), 'p.jpg')[1] == 0
    Image = pytest.importorskip('PIL.Image')
    buf = io.BytesIO(); Image.open(io.BytesIO(fx('phone-sideways.jpg'))).save(buf, 'PNG')
    assert pdfcraft.photo_page(buf.getvalue(), 'screen.png')[1] == 0


@pytest.mark.skipif(not OCR, reason='needs recognition (PdfCraft OCR)')
def test_a_sideways_photo_put_in_an_item_is_kept_upright(dossier):
    c, did = dossier
    d = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('IMG-20250318.jpg', fx('phone-sideways.jpg'), 'image/jpeg')}).json()
    assert d['meta']['converted'] == ['image_to_pdf', 'turned_upright_270'] and d['meta']['original_name'] == 'IMG-20250318.jpg'
    from pypdf import PdfReader
    assert PdfReader(io.BytesIO(c.get(f"/api/dossiers/{did}/documents/{d['id']}/file").content)).pages[0].get('/Rotate') == 270
    d2 = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('page.jpg', fx('page.jpg'), 'image/jpeg')}).json()
    assert d2['meta']['converted'] == ['image_to_pdf']
