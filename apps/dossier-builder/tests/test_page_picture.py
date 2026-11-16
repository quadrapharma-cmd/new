"""A page cleaned in the photo program comes back as a picture and takes its page's place (pdfcraft.page_picture, store.replace_page,
POST /api/dossiers/{did}/documents/{doc}/page): the size the page was shown at (its /Rotate turned in), centred, its bookmarks kept,
the other pages untouched — as a new version, the old one kept. Made-up three-page PDF, made-up picture."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import pdfcraft
from dossier_engine.app.api import create_app
from test_api import PROFILE, PRODUCT, ENV

pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
pypdf = pytest.importorskip('pypdf')
Image = pytest.importorskip('PIL.Image')


def three_pages():
    """Three made-up pages with text; page 2 shown turned (/Rotate 90) and bookmarked."""
    _, out = pdfcraft.run([('doc_create', {'from': 'text', 'text': 'Made-up page one\f Made-up page two\f Made-up page three'}),
                           ('doc_save', {'doc': 1, 'path': 'p.pdf', 'full': True})], {}, read=('p.pdf',))
    w = pypdf.PdfWriter(clone_from=io.BytesIO(out['p.pdf']))
    w.pages[1].rotate(90)
    w.add_outline_item('Page two', 1)
    b = io.BytesIO(); w.write(b)
    return b.getvalue()


def picture(w, h, fmt='PNG'):
    from PIL import ImageDraw
    im = Image.new('RGB', (w, h), 'white'); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w // 4, h // 4], fill='blue')                        # a mark at its top left
    b = io.BytesIO(); im.save(b, fmt); return b.getvalue()


def test_a_page_becomes_the_picture_as_it_was_shown():
    src = three_pages()
    out = pdfcraft.page_picture(src, 2, picture(2200, 1700))               # landscape, as page 2 is shown
    r = pypdf.PdfReader(io.BytesIO(out))
    assert len(r.pages) == 3
    assert [r.pages[0].extract_text().strip(), r.pages[2].extract_text().strip()] == ['Made-up page one', 'Made-up page three']
    assert r.pages[1].extract_text().strip() == ''                           # page 2 is the picture now
    shown = (float(r.pages[1].mediabox.width), float(r.pages[1].mediabox.height)) if not int(r.pages[1].get('/Rotate') or 0) % 180 else \
        (float(r.pages[1].mediabox.height), float(r.pages[1].mediabox.width))
    assert shown == (792.0, 612.0), shown                                   # the size it was shown at: US Letter turned
    assert [r.get_destination_page_number(o) for o in r.outline] == [1]       # its bookmark stays on it
    assert pdfcraft.page_picture(src, 4, picture(10, 10)) is None and pdfcraft.page_picture(src, 0, picture(10, 10)) is None


def test_a_picture_cropped_in_the_program_is_centred_not_stretched(tmp_path):
    out = pdfcraft.page_picture(three_pages(), 1, picture(800, 400, 'JPEG'))  # wider than the portrait page
    (tmp_path / 'o.pdf').write_bytes(out)
    import subprocess
    subprocess.run(['pdftoppm', '-r', '36', '-f', '1', '-l', '1', '-png', '-singlefile', str(tmp_path / 'o.pdf'), str(tmp_path / 'p1')], check=True)
    im = Image.open(tmp_path / 'p1.png').convert('RGB'); W, H = im.size
    blue = [(x, y) for y in range(H) for x in range(W) if im.getpixel((x, y))[2] > 150 and im.getpixel((x, y))[0] < 90]
    ys = [y for _, y in blue]
    assert min(ys) > H * 0.2 and max(ys) < H * 0.5, (min(ys), max(ys), H)    # the picture sits in the middle band, its proportions kept


def test_the_api_keeps_the_cleaned_page_as_a_new_version(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    own = next(s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] == 'company_technical' and s['level'] == 'R')
    d = c.post(f'/api/dossiers/{did}/slots/{own}/documents', files={'file': ('three.pdf', three_pages(), 'application/pdf')}).json()
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/page", data={'page': '2'}, files={'file': ('page 2.png', picture(2200, 1700), 'image/png')})
    assert r.status_code == 201, r.text
    n = r.json()
    assert n['filename'] == 'three.pdf' and n['meta']['page_picture'] == 2 and n['version'] == d['version'] + 1
    assert c.get(f'/api/dossiers/{did}/board').json()['slots'] and [x['id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']
                                                                      for x in s['documents'] if x['filename'] == 'three.pdf'] == [n['id']]
    bad = c.post(f"/api/dossiers/{did}/documents/{n['id']}/page", data={'page': '9'}, files={'file': ('p.png', picture(20, 20), 'image/png')})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-PAGE'
    not_pic = c.post(f"/api/dossiers/{did}/documents/{n['id']}/page", data={'page': '1'}, files={'file': ('p.txt', b'not a picture', 'text/plain')})
    assert not_pic.status_code == 422 and not_pic.json()['detail']['code'] == 'E-PAGE'
    assert n['meta']['from'] == d['id'] and n['doc_class'] == d['doc_class']
    assert [e['detail']['page'] for e in c.get(f'/api/dossiers/{did}/audit').json() if e['event'] == 'document.page.picture'] == [2]


def test_a_page_of_a_third_partys_or_the_authoritys_document_is_never_replaced(tmp_path):
    """A certificate, an authority's letter and an executed record are evidence: only their issuer changes them (guard: replace_page)."""
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    locked = [s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] in ('third_party_certificate', 'eda_document') and s['level'] in ('R', 'O')]
    assert locked
    d = c.post(f"/api/dossiers/{did}/slots/{locked[0]['slot_id']}/documents", files={'file': ('certificate.pdf', three_pages(), 'application/pdf')}).json()
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/page", data={'page': '1'}, files={'file': ('p.png', picture(600, 800), 'image/png')})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-LOCKED', r.text
    assert [x['id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] for x in s['documents']] == [d['id']]      # as it was
