"""A dossier made without the product's indication: the eCTD carries it at the clinical summary (2.7.3) and the efficacy and safety
studies (5.3.5) — ICH eCTD DTD 3.2, «indication CDATA #REQUIRED» — so the export gate asks for it (gate['ectd_indication'], and a field
on the export page) instead of a real export stopping late with «5.3.5.4 needs an indication» (found 15/11/2026). It stops only an
eCTD export: the CTD folders go without it. Made-up product (test_api's)."""
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from test_api import PROFILE, PRODUCT, ENV, up
from fixtures_pdf import make_pdf


@pytest.fixture()
def ready(tmp_path):
    """Every required and optional item filled, the product without its indication."""
    c = TestClient(create_app(tmp_path / 'ws'))
    pr = {k: v for k, v in PRODUCT.items() if k != 'indication'}
    did = c.post('/api/dossiers', json=dict(name='Examplol 500 mg FCT', profile=PROFILE, product=pr, envelope=ENV)).json()['id']
    pdf = make_pdf(tmp_path / 'doc.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started':
            meta = {'pi_type': 'spc', 'lang': 'en'} if s['req_id'] == 'M1-09' else {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {}
            assert up(c, did, s['slot_id'], pdf, meta).status_code == 201
    return c, did


def test_the_gate_asks_for_the_indication_before_an_ectd_export(ready):
    c, did = ready
    g = c.get(f'/api/dossiers/{did}/gate').json()
    assert g['ok'] and 'M5-09' in g['ectd_indication'], g['ectd_indication']        # 5.3.5.4 «other study reports»
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd32'], 'acknowledge_provisional': True})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'E-GATE-INDICATION' and '5.3.5' in r.json()['detail']['ar']
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ctd'], 'acknowledge_provisional': True})
    assert r.status_code == 201, r.text                                                # the CTD folders go without it
    assert c.put(f'/api/dossiers/{did}/indication', json={'indication': '  '}).json()['detail']['code'] == 'E-INDICATION'
    assert c.put(f'/api/dossiers/{did}/indication', json={'indication': ' mild to   moderate pain '}).json()['product']['indication'] == 'mild to moderate pain'
    assert c.get(f'/api/dossiers/{did}/gate').json()['ectd_indication'] == []
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd32', 'ectd40'], 'acknowledge_provisional': True})
    assert r.status_code == 201, r.text
    v = r.json()['validation']
    assert v['eCTD 3.2.2']['ok'] and v['eCTD 4.0']['ok'], v
    assert any(e['event'] == 'product.indication' for e in c.get(f'/api/dossiers/{did}/audit').json())


def test_a_document_that_carries_its_own_indication_needs_none_from_the_product(tmp_path):
    """The writers take a document's own indication first (assemble.docs_for: meta «indication»), then the product's."""
    c = TestClient(create_app(tmp_path / 'ws'))
    pr = {k: v for k, v in PRODUCT.items() if k != 'indication'}
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=pr, envelope=ENV)).json()['id']
    pdf = make_pdf(tmp_path / 'csr.pdf', 'Clinical study report').read_bytes()
    assert up(c, did, 'M5-09', pdf, {'study': 'EXM-01', 'doc_type': 'ich_document_type_2'}).status_code == 201
    assert c.get(f'/api/dossiers/{did}/gate').json()['ectd_indication'] == ['M5-09']
    did2 = c.post('/api/dossiers', json=dict(name='Examplol 2', profile=PROFILE, product=pr, envelope=ENV)).json()['id']
    assert up(c, did2, 'M5-09', pdf, {'study': 'EXM-01', 'doc_type': 'ich_document_type_2', 'indication': 'pain'}).status_code == 201
    assert c.get(f'/api/dossiers/{did2}/gate').json()['ectd_indication'] == []
