"""Every value the program reads from a document is kept in its place in the dossier's data (absorb.py; the owner, 13/11/2026): empty
places filled, nothing written over — a different value kept as a difference for the person to choose. Fictional values."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import absorb
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

GENERIC = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol'])


def doc_with(fields, model=None):
    return {'id': 'd1', 'filename': 'licence.pdf', 'meta': {'extracted': {'fields': fields}, **({'model': {'fields': model}} if model else {})}}


def test_empty_places_are_filled_and_where_each_came_from_is_kept():
    data = {}
    got = absorb.absorb(data, doc_with({'registration': {'reg_no': '12345/2025', 'valid_until': '2030-03-14'},
                                        'apis': [{'name': 'Paracetamol', 'strength': '500 mg', 'manufacturer': 'Example API Co.'}],
                                        'batches': [{'no': 'B001', 'size': '100,000 tablets'}],
                                        'results': [{'batch': 'B001', 'test': 'Assay', 'value': '99.8'}]}))
    assert data['registration']['reg_no'] == '12345/2025' and data['registration']['valid_until'] == '2030-03-14'
    assert data['apis'][0]['name'] == 'Paracetamol' and data['apis'][0]['strength'] == '500 mg'
    assert data['batches'][0]['no'] == 'B001' and data['results']['B001']['Assay'] == '99.8'
    assert data['sources']['registration.reg_no']['filename'] == 'licence.pdf'
    assert {a['field'] for a in got['added']} >= {'registration.reg_no', 'apis', 'batches', 'results'} and not got['conflicts']
    assert next(a for a in got['added'] if a['field'] == 'registration.reg_no')['ar'] == 'رقم التسجيل'


def test_nothing_written_over_a_difference_is_kept_to_choose():
    data = {'registration': {'reg_no': '12345/2025'}, 'apis': [{'name': 'Paracetamol', 'manufacturer': ''}]}
    got = absorb.absorb(data, doc_with({'registration': {'reg_no': '99999/2024'}, 'apis': [{'name': 'paracetamol', 'manufacturer': 'Example API Co.'}]}))
    assert data['registration']['reg_no'] == '12345/2025'                                  # what was written stays
    assert got['conflicts'] and got['conflicts'][0]['field'] == 'registration.reg_no' and got['conflicts'][0]['read'] == '99999/2024'
    assert data['apis'] == [{'name': 'Paracetamol', 'manufacturer': 'Example API Co.'}]     # an empty cell of the same row filled
    again = absorb.absorb(data, doc_with({'registration': {'reg_no': '99999/2024'}}))
    assert not again['conflicts'] and len(data['conflicts']) == 1                           # the same difference is kept once


def test_what_claude_read_wins_over_the_rules_for_the_same_place():
    data = {}
    absorb.absorb(data, doc_with({'registration': {'reg_no': '1234/2025'}}, model={'registration': {'reg_no': '12345/2025', 'shelf_life': '36 months'}}))
    assert data['registration'] == {'reg_no': '12345/2025', 'shelf_life': '36 months'}


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def test_preparing_a_document_keeps_what_it_says_in_the_data_and_the_person_chooses(c, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    c.put(f'/api/dossiers/{did}/data', json={'registration': {'reg_no': '11111/2020'}})
    data = make_pdf_lines(tmp_path / 'lic.pdf', ['Final Registration License', 'Product: Examplol 500 mg film-coated tablets'], 'Licence').read_bytes()
    doc = c.post(f'/api/dossiers/{did}/slots/M1-04/documents', files={'file': ('licence.pdf', io.BytesIO(data), 'application/pdf')}).json()
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/model-reading", json={'ai': {
        'registration': {'reg_no': '12345/2025', 'valid_until': '2030-03-14', 'shelf_life': '36 months'},
        'apis': [{'name': 'Paracetamol', 'strength': '500 mg'}],
        'documents': [{'filename': 'licence.pdf', 'kind': 'licence', 'valid_until': '2030-03-14'}]}}).json()
    fields = {a['field'] for a in r['absorbed']['added']}
    assert {'registration.valid_until', 'registration.shelf_life'} <= fields
    assert r['absorbed']['conflicts'][0]['field'] == 'registration.reg_no'
    d = c.get(f'/api/dossiers/{did}/data').json()
    assert d['registration']['shelf_life'] == '36 months' and d['registration']['reg_no'] == '11111/2020'
    assert next(a for a in d['apis'] if a['name'] == 'Paracetamol')['strength'] == '500 mg'
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    assert over['conflicts'] and over['conflicts'][0]['read'] == '12345/2025'
    assert next(x for x in over['placed'] if x['id'] == doc['id'])['absorbed']['added']
    out = c.post(f'/api/dossiers/{did}/data/choose', json={'field': 'registration.reg_no', 'value': '12345/2025', 'doc_id': doc['id']}).json()
    assert out['conflicts'] == [] and c.get(f'/api/dossiers/{did}/data').json()['registration']['reg_no'] == '12345/2025'
    assert c.post(f'/api/dossiers/{did}/data/choose', json={'field': 'apis', 'value': 'x'}).status_code == 422
