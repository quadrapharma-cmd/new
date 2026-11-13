"""«Improve the file» — PdfCraft's PDF Optimizer in the preparation stage (the owner, 13/11/2026: «PdfCraft has file improvement and
many tools — use them»): a smaller, cleaner new version only when it clearly is, the pages the same. A third party's document only
losslessly (kept only when its pages are the same pixel for pixel); a company's own document also with pictures above 450 ppi brought
to 300 ppi. Fictional files."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import pdfcraft
from dossier_engine.app.api import create_app
from dossier_engine.app.store import Store
from test_reading_cases import PROFILE, PRODUCT, ENV

pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')


def photo_600dpi():
    """A colour page drawn at 600 ppi (a phone or flatbed scan at its highest setting) on a 4 × 4 inch page."""
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (2400, 2400), (250, 248, 240))
    d = ImageDraw.Draw(im)
    for i in range(0, 2400, 40):
        d.rectangle([i, 0, i + 39, 2400], fill=((i * 3) % 255, (i * 5) % 255, 120))
    d.ellipse([400, 400, 2000, 2000], fill=(30, 60, 160))
    buf = io.BytesIO()
    im.save(buf, 'PDF', resolution=600, quality=95)
    return buf.getvalue()


def uncompressed():
    """A page whose drawing is written uncompressed (as some old PDF writers leave it): the same page fits in far fewer bytes."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
    w = PdfWriter()
    page = w.add_blank_page(612, 792)
    ops = ''.join(f'{x} {y} m {x + 40} {y + 3} l S\n' for x in range(50, 550, 25) for y in range(60, 740, 4))
    s = DecodedStreamObject()
    s.set_data(('0.2 0.2 0.6 RG 0.6 w\n' + ops).encode())
    page[NameObject('/Contents')] = w._add_object(s)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


@pytest.fixture(autouse=True)
def no_ocr(monkeypatch):
    """These pictures hold no words: the reading at upload is not what is tested here."""
    monkeypatch.setattr(pdfcraft, 'ocr_info', lambda: None)


@pytest.fixture()
def env(tmp_path):
    ws = tmp_path / 'ws'
    c = TestClient(create_app(ws, auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, Store(ws), did


def slot(st, did, doc_class):
    return next(s.slot_id for s in st.slots(did) if s.active and s.doc_class == doc_class)


def test_a_company_scan_is_made_smaller_and_still_reads_well(env):
    c, st, did = env
    data = photo_600dpi()
    doc = st.add_document(did, slot(st, did, 'company_document') if any(s.doc_class == 'company_document' for s in st.slots(did)) else st.slots(did)[0].slot_id,
                          'scan600.pdf', data, doc_class='company_document')
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/improve").json()
    assert r['document'] and r['after'] < 0.8 * r['before'], r                          # a 600 ppi picture brought to 300 ppi
    new = r['document']
    assert new['meta']['optimized']['resampled'] >= 1 and 'optimize' in new['meta']['fixes'] and new['meta']['fixed_from'] == doc['id']
    again = c.post(f"/api/dossiers/{did}/documents/{new['id']}/improve").json()
    assert again['document'] is None                                                    # once is enough: nothing left to gain
    got = c.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content
    from PIL import Image
    png = Image.open(io.BytesIO(pdfcraft.page_png(got, 1, 72)))
    assert png.size == (288, 288)                                                       # the same page, 4 × 4 inches


def test_a_third_partys_document_is_improved_only_without_changing_a_pixel(env):
    c, st, did = env
    data = uncompressed()
    doc = st.add_document(did, st.slots(did)[0].slot_id, 'certificate.pdf', data, doc_class='third_party_certificate')
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/improve").json()
    assert r['document'] and r['after'] < 0.5 * r['before'], r                          # the drawing compressed, nothing redrawn
    got = c.get(f"/api/dossiers/{did}/documents/{r['document']['id']}/file").content
    assert pdfcraft.same_pixels(data, got) and r['document']['meta']['optimized']['resampled'] == 0
    photo = photo_600dpi()                                                              # a third party's 600 ppi picture is kept as it is
    doc2 = st.add_document(did, st.slots(did)[0].slot_id, 'photo.pdf', photo, doc_class='third_party_certificate')
    r2 = c.post(f"/api/dossiers/{did}/documents/{doc2['id']}/improve").json()
    assert r2['document'] is None and r2['why'] == 'already small'


def test_the_preparation_stage_improves_each_file(env, tmp_path):
    c, st, did = env
    up = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('drawing.pdf', io.BytesIO(uncompressed()), 'application/pdf'))],
                data={'meta': '{}'}).json()[0]
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    w = next(x for x in over['waiting'] if x['id'] == up['id'])
    target = w['auto'] or (w['suggestions'][0]['slot_id'] if w['suggestions'] else st.slots(did)[0].slot_id)
    r = c.post(f"/api/dossiers/{did}/prepare/{up['id']}", json={'slot_id': target}).json()
    imp = next((s for s in r['steps'] if isinstance(s, dict) and 'improved' in s), None)
    assert imp and imp['improved']['after'] < imp['improved']['before'], r['steps']
    placed = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['placed'] if x['id'] == r['document']['id'])
    assert placed['optimized'] and not placed['improvable']                             # shown in the stage, not offered again


def chapters_pdf():
    """Six pages of pictures (about 200 KB each), two chapters of three pages with top-level bookmarks."""
    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    pages = [Image.merge('RGB', [Image.effect_noise((700, 700), 40 + 10 * k + c) for c in range(3)]) for k in range(6)]
    buf = io.BytesIO()
    pages[0].save(buf, 'PDF', resolution=100, save_all=True, append_images=pages[1:], quality=75)
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(buf.getvalue())))
    w.add_outline_item('Chapter 1 — Stability data', 0)
    w.add_outline_item('Chapter 2 — Validation', 3)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


@pytest.mark.parametrize('limit_kb, parts', [(1000, 2), (800, 3)])
def test_a_file_over_the_limit_is_cut_into_parts_that_fit(env, monkeypatch, limit_kb, parts):
    """Over the eCTD's 100 MB a file (here the limit made small): cut at its chapters' bookmarks when each chapter fits, otherwise by
    size; the parts are documents of the same item, the pages unchanged, the original withdrawn."""
    from dossier_engine.checks import pdf as checks
    c, st, did = env
    monkeypatch.setattr(checks, 'SIZE_LIMIT', limit_kb * 1000)
    data = chapters_pdf()
    assert len(data) > limit_kb * 1000
    doc = st.add_document(did, st.slots(did)[0].slot_id, 'stability.pdf', data, 'Stability report', doc_class='third_party_certificate')
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/split-size").json()
    got = [c.get(f"/api/dossiers/{did}/documents/{x['id']}/file").content for x in r['parts']]
    assert len(got) == parts and all(len(x) <= limit_kb * 1000 for x in got), [len(x) for x in got]
    from pypdf import PdfReader
    assert sum(len(PdfReader(io.BytesIO(x)).pages) for x in got) == 6
    assert [x['title'] for x in r['parts']] == [f'Stability report (part {k} of {parts})' for k in range(1, parts + 1)]
    assert all(x['slot_id'] == doc['slot_id'] for x in r['parts'])
    assert st.document(doc['id'])['state'] == 'withdrawn'
    if parts == 2:                                                                       # cut at the chapters
        assert len(PdfReader(io.BytesIO(got[0])).pages) == 3
