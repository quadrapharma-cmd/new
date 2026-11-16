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
