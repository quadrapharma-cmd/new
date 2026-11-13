"""A combined file — several documents scanned into one PDF — is found, cut where each document starts (its words; or Claude reading its
pages, small and numbered), and each part goes to the box of files waiting to be placed with its kind, so its item is suggested from
what it is (the owner, 13/11/2026: «a combined file: cut it, and make from it the papers each item asks for»). Fictional files."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import extract
from dossier_engine.app.api import create_app
from test_priority2 import combined

GENERIC = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol'])


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


@pytest.fixture()
def did(c):
    return c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']


def stage(c, did, name, data):
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', (name, io.BytesIO(data), 'application/pdf'))], data={'meta': '{}'})
    assert r.status_code == 201, r.text
    return r.json()[0]


def test_the_model_answer_is_made_sound():
    ok = extract.parse_split({'parts': [{'from': 1, 'to': 2, 'kind': 'licence', 'title': 'Final Registration License'},
                                        {'from': 3, 'to': 5, 'kind': 'COA', 'title': 'Certificate of Analysis'}]}, 5)
    assert [(p['from'], p['to'], p['kind']) for p in ok] == [(1, 2, 'licence'), (3, 5, 'coa')] and ok[1]['kind_name']['en'] == 'certificate of analysis'
    assert extract.parse_split({'parts': [{'from': 1, 'to': 2, 'kind': 'licence'}]}, 5) == [{'from': 1, 'to': 5, 'kind': 'other', 'title': '', 'kind_name': None}]
    assert extract.parse_split({'parts': [{'from': 2, 'to': 5, 'kind': 'gmp'}]}, 5)[0]['to'] == 5          # not from page 1: one part
    assert extract.parse_split({'parts': [{'from': 1, 'to': 5, 'kind': 'invented'}]}, 5)[0]['kind'] == 'other'
    assert 'It has 7 pages' in extract.split_prompt(7, pictures=True) and 'labelled with its page number' in extract.split_prompt(7, pictures=True)


def test_a_combined_file_is_cut_with_each_parts_kind_and_each_part_is_offered_its_item(c, did, tmp_path):
    doc = stage(c, did, 'scan0042.pdf', combined(tmp_path))
    prop = c.get(f"/api/dossiers/{did}/documents/{doc['id']}/split").json()
    assert [p['kind'] for p in prop['parts']] == ['licence', 'pricing', 'coa', 'coa']                    # its own words tell the documents apart
    q = c.get(f"/api/dossiers/{did}/documents/{doc['id']}/split-prompt").json()
    assert q['pages'] == 5 and 'It has 5 pages' in q['prompt']
    chk = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/split-check", json={'answer': {'parts': [
        {'from': 1, 'to': 1, 'kind': 'licence', 'title': 'Licence'}, {'from': 2, 'to': 2, 'kind': 'pricing', 'title': 'Pricing'},
        {'from': 3, 'to': 5, 'kind': 'coa', 'title': 'CoA'}]}}).json()
    assert [(p['from'], p['to']) for p in chk['parts']] == [(1, 1), (2, 2), (3, 5)] and chk['by'] == 'model'
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/split", json={'starts': [1, 2, 3], 'kinds': ['licence', 'pricing', 'coa'],
                                                                          'titles': ['Licence', 'Pricing', 'CoA'], 'by': 'model'})
    assert r.status_code == 201, r.text
    parts = r.json()['parts']
    assert [p['meta']['kind'] for p in parts] == ['licence', 'pricing', 'coa'] and parts[0]['meta']['split_by'] == 'model'
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    waiting = {w['id']: w for w in over['waiting']}
    assert doc['id'] not in waiting and all(p['id'] in waiting for p in parts)                            # the combined file gone, its parts waiting
    lic = waiting[parts[0]['id']]
    assert lic['split_from'] == doc['id'] and lic['pages_of'] == [1, 1] and lic['split_title'] == 'Licence'
    assert lic['auto'] == 'M1-04' and waiting[parts[1]['id']]['auto'] == 'M1-05'                          # each offered its own item
    done = c.post(f"/api/dossiers/{did}/prepare/{parts[1]['id']}", json={}).json()                       # and prepared there
    assert done['steps'][0] == 'placed' and done['document']['slot_id'] == 'M1-05' and done['conditions']
