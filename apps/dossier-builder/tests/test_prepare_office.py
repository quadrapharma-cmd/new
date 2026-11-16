"""«تجهيز» on a document that is not a PDF, and on a document the page still knows by its earlier id.
Before 16/11/2026 every Word and Excel document answered 422 «Pages are split and joined in PDF files only» (one red note per
document in «تجهيز الكل»), and a document whose first preparation wrote a new version answered «Document not found» the next time."""
import pathlib
import docx
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf

H = {'X-DB': '1'}
OFFICE = pathlib.Path(__file__).parent / 'data' / 'office'


def test_prepare_takes_word_and_excel_and_follows_the_current_version(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', headers=H, json={'name': 'Dermacure (made up)', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
                 'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]},
                 'product': {'name': 'Dermacure 20 mg', 'dosageform': 'cream', 'manufacturer': 'Example Pharm'}, 'envelope': {}}).json()['id']
    word = tmp_path / 'made-up-declaration.docx'
    d = docx.Document()
    d.add_heading('Declaration (made up)', 1)
    d.add_paragraph('Example Pharm declares that Dermacure 20 mg cream is made as described. Batch No.: 240101.')
    d.save(str(word))
    files = [make_pdf(tmp_path / 'made-up-composition.pdf', 'Composition certificate\nDermacure 20 mg cream (made up)'), word, OFFICE / 'sheet.xlsx']
    slots = [s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']
             if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents']]
    for f, slot in zip(files, slots):
        assert c.post(f'/api/dossiers/{did}/slots/{slot}/documents', headers=H, files={'file': (f.name, f.read_bytes())}, data={'meta': '{}'}).status_code == 201
    first = c.get(f'/api/dossiers/{did}/prepare').json()['placed']
    assert sorted(x['filename'] for x in first) == sorted(f.name for f in files)
    for x in first:                                                      # every kind is prepared: none is refused for not being a PDF
        r = c.post(f"/api/dossiers/{did}/prepare/{x['id']}", headers=H, json={})
        assert r.status_code == 200, (x['filename'], r.text[:300])
    now = {x['filename']: x['id'] for x in c.get(f'/api/dossiers/{did}/prepare').json()['placed']}
    pdf_before = next(x['id'] for x in first if x['filename'].endswith('.pdf'))
    assert now['made-up-composition.pdf'] != pdf_before                  # its preparation wrote a new version (the document's information)…
    r = c.post(f'/api/dossiers/{did}/prepare/{pdf_before}', headers=H, json={})
    assert r.status_code == 200, r.text[:300]                            # …and the id the page still holds is followed to it
    # what is done on PDF pages only says so in words, for a file that is not one — and never as «not found»
    r = c.post(f"/api/dossiers/{did}/documents/{now['sheet.xlsx']}/reduce", headers=H, json={})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-NOT-PDF' and 'PDF' in r.json()['detail']['ar']
    r = c.post(f'/api/dossiers/{did}/documents/{pdf_before}/reduce', headers=H, json={})
    assert r.status_code == 422 and r.json()['detail']['code'] in ('E-NOT-CURRENT', 'E-REDUCE'), r.text[:300]


def _dossier_with_a_pdf(c, tmp_path):
    did = c.post('/api/dossiers', headers=H, json={'name': 'Dermacure (made up)', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
                 'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]},
                 'product': {'name': 'Dermacure 20 mg', 'dosageform': 'cream', 'manufacturer': 'Example Pharm'}, 'envelope': {}}).json()['id']
    slot = next(s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']
                if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents'])
    f = make_pdf(tmp_path / 'made-up-composition.pdf', 'Composition certificate\nDermacure 20 mg cream (made up)\nExampletine 20 mg')
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', headers=H, files={'file': (f.name, f.read_bytes())}, data={'meta': '{}'})
    assert r.status_code == 201, r.text[:300]
    return did, r.json()['id']


def test_the_viewer_is_shown_the_document_as_it_is_now(tmp_path):
    """The click sweep of 16/11/2026: «الصفحات» pressed on a list that still held the id of a version since replaced answered
    422 E-NOT-CURRENT and the viewer said «تعذّر عرض هذه الصفحة». Looking at a document (its pages, a search in it) now follows it to
    its current version and says which one it showed (X-Doc-Id), so the viewer works on that one. Changing a document through the id of
    an earlier version is still refused, in words — and an id that is no document of this dossier is still «not found»."""
    import uuid
    import pytest
    from dossier_engine import pdfcraft
    if not pdfcraft.available():
        pytest.skip('needs PdfCraft')
    c = TestClient(create_app(tmp_path / 'ws'))
    did, old = _dossier_with_a_pdf(c, tmp_path)
    r = c.get(f'/api/dossiers/{did}/documents/{old}/pages/1.png?dpi=60', headers=H)
    assert r.status_code == 200 and r.headers['x-doc-id'] == old and r.headers['cache-control'] == 'private, max-age=3600'
    r = c.post(f'/api/dossiers/{did}/documents/{old}/pages', headers=H, json={'op': 'rotate', 'pages': [1], 'degrees': 90})
    assert r.status_code == 201, r.text[:300]
    new = r.json()['document']['id']
    assert new != old and r.json()['document']['version'] == 2
    now = c.get(f'/api/dossiers/{did}/documents/{new}/pages/1.png?dpi=60', headers=H)
    was = c.get(f'/api/dossiers/{did}/documents/{old}/pages/1.png?dpi=60', headers=H)
    assert was.status_code == 200 and was.content[:4] == b'\x89PNG' and was.content == now.content      # the page as it is now (turned)…
    assert was.headers['x-doc-id'] == new and now.headers['x-doc-id'] == new                            # …and whose page it is
    assert was.headers['cache-control'] == 'no-store'                                                   # the answer to an old id is not kept: it changes with the next version
    assert c.get(f'/api/dossiers/{did}/documents/{old}/pages', headers=H).json() == {'id': new, 'pages': 1}   # how many pages it has, as it is now
    assert c.get(f'/api/dossiers/{did}/documents/{new}/pages', headers=H).json() == {'id': new, 'pages': 1}
    f = c.get(f'/api/dossiers/{did}/documents/{old}/find?q=Composition', headers=H)
    assert f.status_code == 200 and f.json()['matches'] and f.json() == c.get(f'/api/dossiers/{did}/documents/{new}/find?q=Composition', headers=H).json()
    r = c.post(f'/api/dossiers/{did}/documents/{old}/pages', headers=H, json={'op': 'rotate', 'pages': [1], 'degrees': 90})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-NOT-CURRENT' and 'نسخة سابقة' in r.json()['detail']['ar']
    r = c.get(f'/api/dossiers/{did}/documents/{uuid.uuid4()}/pages/1.png?dpi=60', headers=H)
    assert r.status_code in (404, 422) and r.json()['detail']['code'] == 'E-NOT-FOUND', r.text[:300]
