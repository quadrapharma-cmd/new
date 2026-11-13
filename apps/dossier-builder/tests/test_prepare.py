"""The preparation stage (the owner, 13/11/2026): the items still asking for a document; every file read — a scan by OCR — its
information kept with it; placed in its item; checked; fixed where the program can; named as the dossier names it. Fictional files."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import pdfcraft
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

GENERIC = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol'])
OCR = bool(pdfcraft.ocr_info())
SPEC = ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white round film-coated tablet',
        'Assay: 95.0 - 105.0 per cent of the labelled amount', 'Dissolution: not less than 80 per cent in 30 minutes']


def scan_of(pdf):
    """The page as a scan would be: drawn at 200 dpi and kept as an image only."""
    from PIL import Image
    png = pdfcraft.page_png(pdf, 1, 200)
    buf = io.BytesIO()
    Image.open(io.BytesIO(png)).convert('L').save(buf, 'PDF', resolution=200)
    return buf.getvalue()


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def stage(c, did, name, data):
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', (name, io.BytesIO(data), 'application/pdf'))], data={'meta': '{}'})
    assert r.status_code == 201, r.text
    return r.json()[0]


@pytest.mark.skipif(not OCR, reason='needs PdfCraft with Tesseract (Arabic and English)')
def test_a_scan_is_read_placed_kept_fixed_and_named(c, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    asked = {x['slot_id'] for x in over['requested']}
    assert 'P-09' in asked or any(x['ctd'] == '3.2.P.5.1' for x in over['requested'])          # the specification is asked for
    assert over['ocr']['language'] in ('ar+en', 'en') and over['engine']['engine'] == 'PdfCraft'
    text = make_pdf_lines(tmp_path / 'spec.pdf', SPEC, 'Specification').read_bytes()
    doc = stage(c, did, 'scan0001.pdf', scan_of(text))                                         # a scanner's file name says nothing
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    w = next(x for x in over['waiting'] if x['id'] == doc['id'])
    assert w['reading']['reader'] == 'ocr' and w['reading']['chars'] > 100 and w['reading']['scanned']
    slot = w['auto'] or w['suggestions'][0]['slot_id']
    r = c.post(f"/api/dossiers/{did}/prepare/{doc['id']}", json={'slot_id': slot}).json()
    assert r['steps'][0] == 'placed' and r['steps'][1] == 'read_ocr'
    fixed = next(x for x in r['steps'] if isinstance(x, dict) and 'fixed' in x)               # (after what it said was kept in its place)
    assert 'make_searchable' in fixed['fixed'], fixed                                           # the scan made searchable …
    new = r['document']
    assert new['meta']['extracted']['reader'] == 'ocr' and 'NTA065-N4' not in {f['rule'] for f in new['findings']}
    got = c.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content
    assert 'Assay: 95.0' in ' '.join(pdfcraft.page_texts(got))                                   # … its text under the picture
    assert pdfcraft.same_pixels(scan_of(text), got)                                             # … the page as it was
    assert r['names'].get('ctd', '').endswith('.pdf') and r['names']['ctd'] != 'scan0001.pdf'   # named as the dossier names it
    placed = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['placed'] if x['id'] == new['id'])
    assert placed['original_name'] == 'scan0001.pdf' and placed['names']['ctd'] == r['names']['ctd'] and not placed['fixable']


@pytest.mark.skipif(not OCR, reason='needs PdfCraft with Tesseract (Arabic and English)')
def test_a_fix_the_program_cannot_make_is_asked_of_the_user_with_why(c, tmp_path):
    """A blank or unreadable scan: «make searchable» is tried once and refused (no words to read). The page then shows it as needing the
    user, with why — not as a fix to offer again — and «prepare them all» leaves it alone; a new scan of it starts afresh."""
    PIL = pytest.importorskip('PIL.Image')
    from PIL import ImageDraw
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    img = PIL.new('RGB', (1240, 1754), 'white')
    ImageDraw.Draw(img).rectangle([100, 100, 600, 160], fill='black')                # a black bar, as a picture: no words
    buf = io.BytesIO()
    img.save(buf, 'PDF', resolution=150)
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    slot = next((x['slot_id'] for x in over['requested'] if x['ctd'] == '3.2.P.5.1'), 'P-09')
    doc = stage(c, did, 'scan0002.pdf', buf.getvalue())
    r = c.post(f"/api/dossiers/{did}/prepare/{doc['id']}", json={'slot_id': slot}).json()
    tried = next(x for x in r['steps'] if isinstance(x, dict))
    assert 'make_searchable' not in tried['fixed'] and any(x['op'] == 'make_searchable' and 'no text could be read' in x['en'].lower()
                                                          for x in tried['refused']), tried
    assert 'NTA065-N4' not in r['fixable'] and any(n['rule'] == 'NTA065-N4' and n['action'] == 'refused' for n in r['needs_you'])
    placed = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['placed'] if x['id'] == r['document']['id'])
    assert 'NTA065-N4' not in placed['fixable']                                                 # not offered again …
    why = next(n for n in placed['needs_you'] if n['rule'] == 'NTA065-N4')
    assert 'no text could be read' in why['en'].lower() and 'امسحه تاني' in why['ar']           # … asked of the user, with why
    text = make_pdf_lines(tmp_path / 'spec.pdf', SPEC, 'Specification').read_bytes()             # a new scan of it, readable this time
    new = c.post(f"/api/dossiers/{did}/slots/{slot}/documents", files=[('file', ('scan0003.pdf', io.BytesIO(scan_of(text)), 'application/pdf'))],
                 data={'meta': '{}', 'replaces': r['document']['id']})
    assert new.status_code in (200, 201), new.text
    again = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['placed'] if x['id'] == new.json()['id'])
    assert 'NTA065-N4' in again['fixable'] and not any(n['rule'] == 'NTA065-N4' for n in again['needs_you'])


def test_a_file_the_program_cannot_place_asks_for_its_item(c, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    vague = make_pdf_lines(tmp_path / 'x.pdf', ['Lorem ipsum dolor sit amet', 'consectetur adipiscing elit, sed do eiusmod tempor'], 'Notes').read_bytes()
    doc = stage(c, did, 'notes.pdf', vague)
    r = c.post(f"/api/dossiers/{did}/prepare/{doc['id']}", json={}).json()
    assert r['steps'] == ['needs_item'] and r['document']['id'] == doc['id']                    # nothing is placed on a guess
    spec = make_pdf_lines(tmp_path / 's.pdf', SPEC, 'Specification').read_bytes()
    d2 = stage(c, did, 'spec-final.pdf', spec)
    r = c.post(f"/api/dossiers/{did}/prepare/{d2['id']}", json={'slot_id': 'P-09'}).json() if any(
        s['slot_id'] == 'P-09' for s in c.get(f'/api/dossiers/{did}/board').json()['slots']) else None
    if r:
        assert r['steps'][0] == 'placed' and r['reading']['reader'] == 'text' and r['document']['slot_id'] == 'P-09'
