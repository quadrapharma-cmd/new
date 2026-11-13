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


def test_an_image_is_kept_aside_too(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('IMG_0001.JPG', fx('phone-rotated.jpg'), 'image/jpeg'))], data={'meta': '{}'})
    assert r.status_code == 201, r.text
    assert c.get(f'/api/dossiers/{did}/board').json()['unassigned']
    assert c.post('/api/images/pdf', files=[('files', ('p1.jpg', fx('page.jpg'), 'image/jpeg'))]).status_code in (404, 405)        # no picture-to-PDF service any more
