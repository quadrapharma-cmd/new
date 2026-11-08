"""Templates and «make it for me»: every requirement has a template entry (what the document looks like, whether the program drafts
it); the item's template view; a draft from the product data alone (gaps marked), from the browser's model answers, and from the
server's model; third-party documents are never drafted."""
import io
import pytest
from docx import Document
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from dossier_engine.generate import draft as _draft
from test_api import PROFILE, PRODUCT, ENV

H = {'X-DB': '1'}


@pytest.fixture()
def app(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    r = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV), headers=H)
    assert r.status_code == 201, r.text
    did = r.json()['id']
    c.put(f'/api/dossiers/{did}/data', json={'composition': [{'name': 'Neomycin sulphate', 'role': 'active', 'standard': 'Ph. Eur.', 'amount': '3.5 mg'},
                                                             {'name': 'Talc', 'role': 'diluent', 'standard': 'Ph. Eur.', 'amount': 'q.s. to 1 g'}],
                                             'batches': [{'no': 'DC2301', 'size': '50 kg', 'date': '2023-05-10', 'scale': 'pilot', 'site': 'Cairo', 'executed_bmr': True}],
                                             'specs': {'product': [{'test': 'Assay', 'limit': '90.0–110.0 %', 'method': 'HPLC'}]},
                                             'results': {'DC2301': {'Assay': '99.1'}}}, headers=H)
    return c, did


def slot_of(c, did, req_id):
    b = c.get(f'/api/dossiers/{did}/board').json()
    return next(s for s in b['slots'] if s['req_id'] == req_id)


def docx_text(blob):
    d = Document(io.BytesIO(blob))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    return '\n'.join(parts)


def test_library_covers_every_requirement():
    assert _draft.lint() == []
    s = _draft.summary()
    assert len(s) == 101
    kinds = {v['draft'] for v in s.values()}
    assert kinds == {'full', 'partial', 'generator', 'none'}
    assert s['P-01']['draft'] == 'full' and s['M1-14']['draft'] == 'none' and s['M1-43']['generator'] == 'cover' and s['M1-09']['lang'] == 'both'
    assert sum(1 for v in s.values() if v['draft'] in ('full', 'partial')) >= 40          # the program drafts (fully or structurally) most authored documents


def test_template_view_and_summary_endpoint(app):
    c, did = app
    s = c.get('/api/templates').json()
    assert s['P-04']['draft'] == 'full'
    slot = slot_of(c, did, 'P-01')
    v = c.get(f"/api/dossiers/{did}/slots/{slot['slot_id']}/template").json()
    assert v['template']['id'] == 'P-01' and v['template']['draft'] == 'full'
    assert [x['id'] for x in v['template']['sections']] == ['description', 'composition', 'removed']
    assert 'Neomycin' in v['prompt'] and 'JSON' in v['prompt'] and 'P-01' in v['prompt']                # the prompt carries the product data
    assert v['requirement']['acceptance'].startswith('API standard')                                       # the requirement's own words
    assert v['ai_server'] is False
    v2 = c.get(f"/api/dossiers/{did}/slots/{slot_of(c, did, 'M1-37')['slot_id']}/template").json()
    assert v2['template']['draft'] == 'none' and 'prompt' not in v2 and 'GMP' in v2['requirement']['title']['en']
    assert 'production lines specified' in v2['template']['example']['en']                                 # what an acceptable copy shows
    v3 = c.get(f"/api/dossiers/{did}/slots/{slot_of(c, did, 'M1-14')['slot_id']}/template").json()           # an item this product does not need: still viewable
    assert v3['template']['draft'] == 'none' and 'Egypt named as importing country' in v3['template']['example']['en']


def test_draft_from_the_data_alone_marks_gaps(app):
    c, did = app
    slot = slot_of(c, did, 'P-01')
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/draft", json={'ai': False, 'lang': 'en'}, headers=H)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['how'] == 'data' and j['document']['meta']['draft_unsigned'] and j['document']['filename'].endswith('.docx')
    assert any('removed' in g['what'].lower() or 'Components removed' in g['what'] for g in j['gaps'])     # a narrative section the data cannot fill
    blob = c.get(f"/api/dossiers/{did}/documents/{j['document']['id']}/file").content
    text = docx_text(blob)
    assert 'Neomycin sulphate' in text and 'Talc' in text and '[…]' in text and 'Gaps in this draft' in text
    assert 'Description & composition' in text
    # it shows on the board as an unsigned draft of the item, with its gaps in the metadata
    s2 = slot_of(c, did, 'P-01')
    assert s2['documents'][0]['meta']['generated'] == 'draft' and len(s2['documents'][0]['meta']['gaps']) == len(j['gaps'])


def test_draft_from_the_browser_models_answers(app):
    c, did = app
    slot = slot_of(c, did, 'M1-36')                                            # specifications: a letter the program drafts fully
    answers = {'sections': {'product': {'trade_name': 'Dermacure', 'dosage_form': 'Topical powder', 'strength': '3.5 mg/g', 'pack': 'Bottle 20 g', 'manufacturer': 'Example Pharm', 'applicant': 'Example Pharm', 'registration_number': '[…]'},
                            'actives': {'rows': [['Neomycin sulphate', 'Assay', '90.0–110.0 %', 'HPLC', 'Ph. Eur. 11.0 (2.2.29)']]},
                            'inactives': {'rows': [['Talc', 'Ph. Eur.', 'Identification', 'IR', 'Ph. Eur. 11.0']]},
                            'signature': {'signatory': 'Dr. Example', 'signatory_title': 'QA Manager', 'company': 'Example Pharm'}},
               'gaps': [{'what': 'Pharmacopoeia edition of the API monograph', 'why': 'not stated in the documents', 'ar': 'طبعة الدستور لمونوجراف المادة الفعالة'}],
               'sources': {'actives': 'coa.pdf'}, 'notes': 'check the edition'}
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/draft", json={'answers': answers, 'lang': 'ar'}, headers=H)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['how'] == 'answers' and j['gaps'][0]['what'].startswith('Pharmacopoeia')
    text = docx_text(c.get(f"/api/dossiers/{did}/documents/{j['document']['id']}/file").content)
    assert 'المواصفات' in text and 'Neomycin sulphate' in text and 'Ph. Eur. 11.0 (2.2.29)' in text        # Arabic edition with the tables
    assert 'طبعة الدستور' in text and 'ورق الشركة' in text and 'check the edition' in text              # the gaps, the letterhead note, the reviewer's note
    assert j['document']['meta']['sources'] == {'actives': 'coa.pdf'} and j['document']['meta']['lang'] == 'ar'


def test_draft_with_the_servers_model(app, monkeypatch):
    c, did = app
    seen = {}
    def fake(prompt):
        seen['prompt'] = prompt
        return {'sections': {'batch_formula': {'rows': [['Neomycin sulphate', '3.5 mg', '175 g', '50 kg', '0%']]}}, 'gaps': [], 'sources': {'batch_formula': 'bmr.pdf'}}
    monkeypatch.setattr(_draft, 'ASK', fake)
    slot = slot_of(c, did, 'P-04')
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/draft", json={}, headers=H)
    assert r.status_code == 201, r.text
    assert r.json()['how'] == 'server-model' and 'P-04' in seen['prompt'] and 'DC2301' in seen['prompt']
    assert '175 g' in docx_text(c.get(f"/api/dossiers/{did}/documents/{r.json()['document']['id']}/file").content)
    # a model answer that is not JSON is refused, nothing stored
    monkeypatch.setattr(_draft, 'ASK', lambda p: (_ for _ in ()).throw(ValueError('the model did not return the expected JSON')))
    r2 = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/draft", json={}, headers=H)
    assert r2.status_code == 422 and r2.json()['detail']['code'] == 'E-DRAFT'


def test_third_party_documents_are_never_drafted(app):
    c, did = app
    slot = slot_of(c, did, 'M1-37')                                            # GMP certificate
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/draft", json={}, headers=H)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-NOT-DRAFTABLE'
    r = c.post(f"/api/dossiers/{did}/slots/{slot_of(c, did, 'M1-36')['slot_id']}/draft", json={'answers': 'not json at all'}, headers=H)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-ANSWERS'
