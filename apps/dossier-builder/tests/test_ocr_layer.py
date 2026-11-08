"""A readable copy of a scan: text-only pages (invisible OCR text) laid over the original pages — the images stay byte-identical,
the text becomes searchable; the endpoint stores it as a new version and the searchable-text finding disappears."""
import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from dossier_engine import fixes
from dossier_engine.app.api import create_app

PIL = pytest.importorskip('PIL.Image')
rl = pytest.importorskip('reportlab.pdfgen.canvas')


def scan_pdf(path, w=1240, h=1754):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (w, h), 'white')
    ImageDraw.Draw(img).rectangle([100, 100, 600, 160], fill='black')          # a printed line, as a picture
    img.save(path, 'PDF', resolution=150.0)
    return path.read_bytes()


def text_only_page(words, w=1240, h=1754):
    """What tesseract.js produces with pdfTextOnly: a page the size of the image with invisible text (render mode 3)."""
    buf = io.BytesIO()
    c = rl.Canvas(buf, pagesize=(w, h))
    t = c.beginText(); t.setTextRenderMode(3); t.setFont('Helvetica', 24); t.setTextOrigin(100, h - 140)
    t.textLine(' '.join(words)); c.drawText(t); c.showPage(); c.save()
    return buf.getvalue()


def test_overlay_keeps_images_and_adds_text(tmp_path):
    src = scan_pdf(tmp_path / 'scan.pdf')
    assert (PdfReader(io.BytesIO(src)).pages[0].extract_text() or '').strip() == ''
    out = fixes.overlay_text_pages(src, [text_only_page(['Dermacure', 'Topical', 'Powder'])])
    rd = PdfReader(io.BytesIO(out))
    assert 'Dermacure' in rd.pages[0].extract_text()
    img_before = list(PdfReader(io.BytesIO(src)).pages[0].images)[0].data
    img_after = list(rd.pages[0].images)[0].data
    assert img_after == img_before                                              # the page image is untouched
    # a bad overlay page is skipped; a missing one leaves the page as it is
    out2 = fixes.overlay_text_pages(src, [b'not a pdf'])
    assert len(PdfReader(io.BytesIO(out2)).pages) == 1


def test_ocr_layer_endpoint_makes_a_searchable_version(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json={'name': 'Dermacure', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical',
                                                                       'leaflet': 'english', 'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'X', 'option': 'FULL'}]},
                                        'product': {'name': 'Dermacure'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}}).json()['id']
    slot = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] == 'company_technical' and s['status'] != 'not_applicable')
    src = scan_pdf(tmp_path / 'scan2.pdf')
    d = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/documents", files={'file': ('scan.pdf', src, 'application/pdf')}).json()
    assert any(f['rule'] == 'NTA065-N4' and f['action'] == 'auto_fix' for f in d['findings'])          # image-only company document: blocked
    assert c.get('/api/capabilities').json()['ocr_server'] in (True, False)
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/ocr-layer", files=[('pages', ('p1.pdf', text_only_page(['Dermacure', 'specification']), 'application/pdf'))])
    assert r.status_code == 201, r.text
    new = r.json()
    assert new['version'] == 2 and new['meta']['fixed_from'] == d['id'] and new['meta']['fixes'] == ['add_ocr_layer'] and new['meta']['ocr_where'] == 'browser'
    assert not any(f['rule'] == 'NTA065-N4' for f in new['findings'])                                  # searchable now
    body = c.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content
    assert 'Dermacure' in PdfReader(io.BytesIO(body)).pages[0].extract_text()
    slot2 = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == slot['slot_id'])
    assert [x['version'] for x in slot2['documents']] == [2]                                            # the scan is superseded, not lost
    assert any(a['event'] == 'document.fixed' and a['detail'].get('where') == 'browser' for a in c.get(f'/api/dossiers/{did}/audit').json())
    assert c.post(f"/api/dossiers/{did}/documents/{new['id']}/ocr-layer", files=[('pages', ('p1.pdf', b'nope', 'application/pdf'))]).status_code == 422
