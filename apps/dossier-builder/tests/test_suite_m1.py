"""Suite module 1: product file, parties, document library with validity, checklist per role, dashboard."""
import io, json
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app

TODAY = date.today()
D = lambda days: (TODAY + timedelta(days=days)).isoformat()


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws'))


@pytest.fixture()
def pdf(tmp_path):
    return make_pdf(tmp_path / 'd.pdf', 'certificate').read_bytes()


def post_doc(c, meta, data=None):
    files = {'file': ('cert.pdf', io.BytesIO(data), 'application/pdf')} if data else None
    return c.post('/api/suite/documents', data={'meta': json.dumps(meta)}, files=files)


def setup_product(c):
    holder = c.post('/api/suite/parties', json={'name': 'Holder Co', 'kind': 'company'}).json()
    maker = c.post('/api/suite/parties', json={'name': 'Toll Maker', 'kind': 'manufacturer'}).json()
    sup = c.post('/api/suite/parties', json={'name': 'API Supplier', 'kind': 'supplier', 'country': 'China'}).json()
    p = c.post('/api/suite/products', json={'name': 'Prod A', 'dosage_form': 'topical powder', 'licence_type': 'toll',
                                            'reg_no': '1/2022', 'reg_date': '2022-03-01', 'packs': ['10 g']}).json()
    for party, role, api in ((holder, 'holder', None), (maker, 'manufacturer', None), (sup, 'api_supplier', 'Glycine')):
        assert c.post(f"/api/suite/products/{p['id']}/parties", json={'party_id': party['id'], 'role': role, 'api_name': api}).status_code == 201
    return p, holder, maker, sup


def test_checklist_lists_what_each_role_needs(c):
    p, holder, maker, sup = setup_product(c)
    prod = c.get(f"/api/suite/products/{p['id']}").json()
    need = {(i['doc_type'], i['for']) for i in prod['checklist']}
    assert ('gmp_certificate', 'api_supplier') in need and ('import_approval', 'api_supplier') in need
    assert ('gmp_certificate', 'manufacturer') in need and ('factory_licence', 'manufacturer') in need
    assert ('commercial_register', 'holder') in need and ('toll_card', 'holder') in need          # toll licence
    assert ('registration_licence', 'product') in need
    assert all(i['status'] == 'missing' for i in prod['checklist']) and prod['readiness'] == 0
    assert prod['renewal']['due'] == '2032-03-01'                                                  # reg date + 10 years


def test_party_document_serves_every_product_using_that_party(c, pdf):
    p, holder, maker, sup = setup_product(c)
    p2 = c.post('/api/suite/products', json={'name': 'Prod B'}).json()
    c.post(f"/api/suite/products/{p2['id']}/parties", json={'party_id': sup['id'], 'role': 'api_supplier', 'api_name': 'Glycine'})
    r = post_doc(c, {'doc_type': 'gmp_certificate', 'issuer': 'NMPA', 'issued': '2021-12-14', 'parties': [sup['id']]}, pdf)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d['end'] == '2024-12-14' and d['validity'] == 'expired' and d['validity_basis'] == 'issued+36'
    assert {x[1] for x in d['affected']} == {'Prod A', 'Prod B'}
    dash = c.get('/api/suite/dashboard').json()
    row = next(i for i in dash['issues'] if i.get('doc_id') == d['id'])
    assert row['severity'] == 'expired' and {x['name'] for x in row['products']} == {'Prod A', 'Prod B'}
    assert 'منتهي' in row['ar'] and 'EudraGMDP' in row['source']


def test_printed_end_date_wins_and_expiring_warns(c, pdf):
    p, holder, maker, sup = setup_product(c)
    d = post_doc(c, {'doc_type': 'gmp_certificate', 'issued': '2020-01-01', 'valid_until': D(60), 'parties': [sup['id']]}, pdf).json()
    assert d['validity'] == 'expiring' and d['days_left'] == 60 and d['validity_basis'] == 'printed'
    d = c.put(f"/api/suite/documents/{d['id']}", json={'valid_until': D(400)}).json()
    assert d['validity'] == 'valid'
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist']
                if i['doc_type'] == 'gmp_certificate' and i['for'] == 'api_supplier')
    assert item['status'] == 'valid' and item['document']['id'] == d['id']


def test_product_party_document_and_needs_date(c):
    p, holder, maker, sup = setup_product(c)
    d = post_doc(c, {'doc_type': 'import_approval', 'url': 'https://drive.google.com/file/d/x/view',
                     'products': [p['id']], 'parties': [sup['id']]}).json()
    assert d['validity'] == 'needs_date'                         # 12-month rule but no date given
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist'] if i['doc_type'] == 'import_approval')
    assert item['status'] == 'needs_date'
    c.put(f"/api/suite/documents/{d['id']}", json={'issued': D(-30)})
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist'] if i['doc_type'] == 'import_approval')
    issued = date.fromisoformat(D(-30))
    assert item['status'] == 'valid' and item['document']['validity_basis'] == 'issued+12'
    assert date.fromisoformat(item['document']['end']) > issued.replace(year=issued.year + 1) - timedelta(days=3)


def test_replace_supersedes_and_readiness_moves(c, pdf):
    p, holder, maker, sup = setup_product(c)
    old = post_doc(c, {'doc_type': 'commercial_register', 'valid_until': D(-5), 'parties': [holder['id']]}, pdf).json()
    assert c.get(f"/api/suite/products/{p['id']}").json()['counts'].get('expired') == 1
    new = post_doc(c, {'doc_type': 'commercial_register', 'valid_until': D(900), 'parties': [holder['id']], 'replaces': old['id']}, pdf).json()
    prod = c.get(f"/api/suite/products/{p['id']}").json()
    assert prod['counts'].get('expired') is None and prod['readiness'] > 0
    assert old['id'] not in {d['id'] for d in prod['documents']}
    assert old['id'] in {d['id'] for d in c.get('/api/suite/documents?state=superseded').json()}
    assert c.get(f"/api/suite/documents/{new['id']}/file").status_code == 200


def test_validation_errors_are_bilingual(c):
    p, holder, maker, sup = setup_product(c)
    bad = [
        ({'doc_type': 'nope', 'url': 'https://x', 'products': [p['id']]}, 'E-TYPE'),
        ({'doc_type': 'other', 'products': [p['id']]}, 'E-FILE'),
        ({'doc_type': 'other', 'url': 'http://x', 'products': [p['id']]}, 'E-URL'),
        ({'doc_type': 'other', 'url': 'https://x'}, 'E-LINK'),
        ({'doc_type': 'other', 'url': 'https://x', 'products': [p['id']], 'issued': '31/12/2026'}, 'E-DATE'),
    ]
    for meta, code in bad:
        r = post_doc(c, meta)
        assert r.status_code == 422 and r.json()['detail']['code'] == code and r.json()['detail']['ar'], (code, r.text)
    r = c.post(f"/api/suite/products/{p['id']}/parties", json={'party_id': sup['id'], 'role': 'api_supplier'})
    assert r.json()['detail']['code'] == 'E-API'
    assert c.get('/api/suite/products/missing').status_code == 404


def test_dashboard_orders_by_severity_and_renewal(c, pdf):
    p, holder, maker, sup = setup_product(c)
    c.put(f"/api/suite/products/{p['id']}", json={'reg_date': (TODAY.replace(year=TODAY.year - 10) + timedelta(days=100)).isoformat()})
    post_doc(c, {'doc_type': 'gmp_certificate', 'valid_until': D(-1), 'parties': [maker['id']]}, pdf)
    post_doc(c, {'doc_type': 'factory_licence', 'url': 'https://drive.google.com/a', 'parties': [maker['id']]})
    dash = c.get('/api/suite/dashboard').json()
    sevs = [i['severity'] for i in dash['issues']]
    assert sevs == sorted(sevs, key=['expired', 'missing', 'needs_date', 'expiring', 'renewal'].index)
    assert 'renewal' in sevs and dash['counts']['expired'] >= 1 and dash['counts']['products'] == 1
    assert c.get('/api/suite/types').json()['types'][0]['source']


def test_written_confirmation_satisfies_api_gmp_and_known_expiry_beats_undated(c, pdf):
    p, holder, maker, sup = setup_product(c)
    post_doc(c, {'doc_type': 'written_confirmation', 'valid_until': D(-3), 'parties': [sup['id']]}, pdf)
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist'] if i['for'] == 'api_supplier' and 'gmp_certificate' in i['alternatives'])
    assert item['status'] == 'expired' and item['doc_type'] == 'written_confirmation' and ' أو ' in item['type_ar']
    post_doc(c, {'doc_type': 'import_approval', 'url': 'https://drive.google.com/old', 'products': [p['id']], 'parties': [sup['id']]})
    post_doc(c, {'doc_type': 'import_approval', 'issued': D(-500), 'url': 'https://drive.google.com/new', 'products': [p['id']], 'parties': [sup['id']]})
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist'] if i['doc_type'] == 'import_approval')
    assert item['status'] == 'expired'
    post_doc(c, {'doc_type': 'gmp_certificate', 'valid_until': D(700), 'parties': [sup['id']]}, pdf)
    item = next(i for i in c.get(f"/api/suite/products/{p['id']}").json()['checklist'] if i['for'] == 'api_supplier' and 'gmp_certificate' in i['alternatives'])
    assert item['status'] == 'valid' and item['doc_type'] == 'gmp_certificate'
