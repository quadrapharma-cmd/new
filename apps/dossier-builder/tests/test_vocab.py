"""Controlled vocabularies: dose forms (with Arabic names and default routes), countries (ISO, Arabic names), matching of
what documents print, standardisation inside the intake, the /api/vocab endpoint with the workspace's known names."""
from fastapi.testclient import TestClient
from dossier_engine import extract, vocab
from dossier_engine.app.api import create_app
from test_intake_eda import LICENCE


def test_forms_and_countries_match_what_documents_print():
    assert vocab.match_form('Topical Powder')['id'] == 'powder-topical' and vocab.match_form('بودرة موضعية')['route'] == 'topical'
    assert vocab.match_form('F.C.T')['id'] == 'tablet-fc' and vocab.match_form('أقراص مغلفة')['id'] == 'tablet-fc' and vocab.match_form('Film-Coated Tablets')['route'] == 'oral'
    assert vocab.match_form('Hard gelatin capsules')['en'] == 'Capsule, hard' and vocab.match_form('Powder for oral suspension')['id'] == 'powder-oral-susp'
    assert vocab.match_form('eye drops')['route'] == 'ophthalmic' and vocab.match_form('nasal spray')['route'] == 'inhalation' and vocab.match_form('nonsense') is None
    assert vocab.match_country('CHINA') == {'code': 'CN', 'en': 'China', 'ar': 'الصين'} and vocab.match_country('P.R. China')['code'] == 'CN'
    assert vocab.match_country('UK')['code'] == 'GB' and vocab.match_country('مصر')['code'] == 'EG' and vocab.match_country('Republic of India')['code'] == 'IN'
    assert vocab.match_country('Atlantis') is None and vocab.match_country('') is None
    ids = [f['id'] for f in vocab.forms()]
    assert len(ids) == len(set(ids)) >= 60 and all(f['route'] in {r['id'] for r in vocab.ROUTES} for f in vocab.forms())
    assert len(vocab.countries()) >= 240 and all(c['ar'] for c in vocab.countries())


def test_intake_standardises_form_and_countries():
    f = extract.fields_for('licence', 'licence.txt', '\n'.join(LICENCE))
    assert f['product']['dosage_form'] == 'Topical Powder' and f['product']['dosage_form_std'] == 'powder-topical' and f['product']['dosage_form_en'] == 'Cutaneous powder'
    assert f['profile']['admin_route'] == 'topical' and f['product']['manufacturer_country'] == 'Egypt' and f['product']['manufacturer_country_code'] == 'EG'
    a = {x['name']: x for x in f['apis']}
    assert a['Neomycin Sulphate']['country'] == 'China' and a['Neomycin Sulphate']['country_code'] == 'CN'
    assert 'country_code' not in a['Cysteine']                                       # nothing invented for a substance without a printed manufacturer


def test_vocab_endpoint_lists_and_known_names(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    v = c.get('/api/vocab').json()
    assert {x['id'] for x in v['forms']} >= {'tablet-fc', 'powder-topical', 'injection-sol'} and len(v['countries']) >= 240 and 'mg' in v['units']
    assert [o['id'] for o in v['api_options']] == ['CEP', 'DMF', 'PQ', 'FULL'] and v['known'] == {'applicants': [], 'manufacturers': [], 'apis': [], 'api_manufacturers': []}
    c.post('/api/dossiers', json={'name': 'Dermacure', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical', 'leaflet': 'english',
                                                                  'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'Sichuan Example', 'option': 'FULL'}]},
                                  'product': {'name': 'Dermacure', 'manufacturer': 'Example Industries'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}})
    k = c.get('/api/vocab').json()['known']
    assert k == {'applicants': ['EXAMPLE PHARM'], 'manufacturers': ['Example Industries'], 'apis': ['Neomycin Sulphate'], 'api_manufacturers': ['Sichuan Example']}
