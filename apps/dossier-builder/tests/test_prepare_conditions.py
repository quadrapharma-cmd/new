"""The preparation stage holds every document to its item's conditions (prepare.py, the owner, 13/11/2026): the form and the content,
each met, fixed, fixed by the program, needing the person, or to be checked by eye — with what Claude saw on the pages kept with the
document (the browser edition posts claude.ai's reading; the server editions read with the key). Fictional files."""
import io
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

GENERIC = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol'])


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


@pytest.fixture()
def did(c):
    return c.post('/api/dossiers', json=dict(name='Examplol', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']


def put(c, did, slot, name, data):
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, io.BytesIO(data), 'application/pdf')})
    assert r.status_code in (200, 201), r.text
    out = r.json()
    return (out[0] if isinstance(out, list) else out.get('document') or out)


def lines_of(c, did, doc_id):
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    d = next(x for x in over['placed'] if x['id'] == doc_id)
    return d, {x['id']: x for x in d['conditions']}


def letter_slot(c, did):
    board = c.get(f'/api/dossiers/{did}/board').json()
    return next(s['slot_id'] for s in board['slots'] if s.get('doc_class') == 'company_letter' and s.get('level') == 'R')


def test_a_licence_claude_read_as_expired_needs_a_current_one(c, did, tmp_path):
    data = make_pdf_lines(tmp_path / 'lic.pdf', ['Final Registration License', 'Product: Examplol 500 mg film-coated tablets',
                                                  'License Holder: Example Pharm Co.'], 'Licence').read_bytes()
    doc = put(c, did, 'M1-04', 'licence.pdf', data)
    d, by = lines_of(c, did, doc['id'])
    assert by['pdf']['status'] == 'ok' and by['pdf']['kind'] == 'form'                       # its own text: searchable
    assert by['valid']['status'] == 'check' and by['valid']['action'] == 'set_validity'      # no end date read yet: asked
    gone = (date.today() - timedelta(days=40)).isoformat()
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/model-reading",
               json={'ai': {'documents': [{'filename': 'licence.pdf', 'kind': 'licence', 'valid_until': gone, 'issued': '2016-01-01'}]}, 'by': 'claude.ai'}).json()
    by = {x['id']: x for x in r['conditions']}
    assert by['valid']['status'] == 'needs_you' and by['valid']['how'] == 'model' and 'Expired' in by['valid']['why']['en']
    assert r['document']['meta']['model']['by'] == 'claude.ai' and r['document']['meta']['valid_until'] == gone
    assert not r['state']['ready'] and r['state']['needs_you'] >= 1


def test_a_letter_claude_saw_unstamped_needs_you_and_without_claude_it_is_asked(c, did, tmp_path):
    slot = letter_slot(c, did)
    data = make_pdf_lines(tmp_path / 'letter.pdf', ['Example Pharm Co.', 'Declaration', 'We declare that the product is as described.'], 'Letter').read_bytes()
    doc = put(c, did, slot, 'declaration.pdf', data)
    d, by = lines_of(c, did, doc['id'])
    assert by['letterhead']['status'] == 'check' and by['letterhead']['action'] == 'attest'      # no model looked: one look answers it
    assert d['model_wanted']                                                                    # only eyes see a stamp: Claude is wanted
    c.post(f'/api/dossiers/{did}/slots/{slot}/attest', json={'answer': 'yes'})
    d, by = lines_of(c, did, doc['id'])
    assert by['letterhead']['status'] == 'ok' and by['letterhead']['how'] == 'person'
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/model-reading",
               json={'ai': {'documents': [{'filename': 'declaration.pdf', 'kind': 'other', 'letterhead': True, 'signed': True, 'stamped': False}]}}).json()
    by = {x['id']: x for x in r['conditions']}
    assert by['letterhead']['status'] == 'needs_you' and by['letterhead']['how'] == 'model' and 'stamped' in by['letterhead']['why']['en']
    d, _ = lines_of(c, did, r['document']['id'])
    assert not d['model_wanted']                                                                # read once: not asked again


def test_what_the_program_cannot_see_is_answered_by_the_person(c, did, tmp_path):
    items = c.get('/api/conditions?country=EG').json()['items']
    board = c.get(f'/api/dossiers/{did}/board').json()
    slot = next(s['slot_id'] for s in board['slots'] if s.get('level') in ('R', 'O') and any(x.get('id') == 'dated' for x in items.get(s['req_id'], [])))
    data = make_pdf_lines(tmp_path / 'u.pdf', ['Example Pharm Co.', 'Commitment', 'We commit to submit the data.'], 'Commitment').read_bytes()
    doc = put(c, did, slot, 'commitment.pdf', data)
    d, by = lines_of(c, did, doc['id'])
    checks = [x for x in d['conditions'] if x['status'] == 'check' and x['id'] not in ('letterhead', 'legalized')]
    if not checks:
        pytest.skip('this item asks nothing the program cannot read')
    cid = checks[0]['id']
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/confirm", json={'cond': cid, 'answer': 'yes'}).json()
    x = next(y for y in r['conditions'] if y['id'] == cid)
    assert x['status'] == 'ok' and x['how'] == 'person'
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/confirm", json={'cond': cid, 'answer': 'no'}).json()
    assert next(y for y in r['conditions'] if y['id'] == cid)['status'] == 'needs_you'
    assert c.post(f"/api/dossiers/{did}/documents/{doc['id']}/confirm", json={'cond': cid, 'answer': 'maybe'}).status_code == 422


def test_preparing_returns_the_conditions_and_a_scan_without_text_is_fixed_by_the_program(c, did, tmp_path):
    from dossier_engine import prepare
    doc = {'filename': 'scan.pdf', 'findings': [{'rule': 'NTA065-N4', 'severity': 'block', 'action': 'auto_fix', 'en': 'Not searchable', 'ar': 'مش قابل للبحث'}],
           'meta': {}}
    from dossier_engine.app.store import Store
    pk = Store(tmp_path / 's').pack('eda.ctd.nta065.v5')
    lines = prepare.verdict(doc, pk.by_id['M1-04'], pk, reading={'scanned': True, 'chars': 0})
    pdf = next(x for x in lines if x['id'] == 'pdf')
    assert pdf['status'] == 'fix' and pdf['action'] == 'fix'
    doc['meta']['fixes'] = ['make_searchable']
    doc['findings'] = []
    lines = prepare.verdict(doc, pk.by_id['M1-04'], pk, reading={'scanned': True, 'chars': 0})
    assert next(x for x in lines if x['id'] == 'pdf')['status'] == 'fixed'
    assert not any(x['id'] in ('fixed:make_searchable', 'rule:NTA065-N4') for x in lines)          # said once, as the item's own condition
    data = make_pdf_lines(tmp_path / 'lic2.pdf', ['Final Registration License', 'Valid until 31/12/2099'], 'Licence').read_bytes()
    up = put(c, did, 'M1-04', 'lic2.pdf', data)
    r = c.post(f"/api/dossiers/{did}/prepare/{up['id']}", json={}).json()
    assert r['conditions'] and {'ok', 'fixed', 'fix', 'needs_you', 'check'} >= {x['status'] for x in r['conditions']}
    assert 'ready' in r['state']


def test_the_kind_claude_read_suggests_the_item_of_a_waiting_scan(c, did, tmp_path):
    from PIL import Image
    buf = io.BytesIO()
    Image.new('L', (800, 1100), 255).save(buf, 'PDF', resolution=100)                         # a page with nothing readable on it
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('scan0007.pdf', io.BytesIO(buf.getvalue()), 'application/pdf'))], data={'meta': '{}'})
    doc = r.json()[0]
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    w = next(x for x in over['waiting'] if x['id'] == doc['id'])
    assert w['model_wanted'] and not w['model']
    c.post(f"/api/dossiers/{did}/documents/{doc['id']}/model-reading", json={'ai': {'documents': [{'filename': 'scan0007.pdf', 'kind': 'gmp', 'title': 'GMP certificate'}]}})
    over = c.get(f'/api/dossiers/{did}/prepare').json()
    w = next(x for x in over['waiting'] if x['id'] == doc['id'])
    assert w['model']['kind'] == 'gmp' and not w['model_wanted']
    homes = {'M1-37', 'M1-38'}                                                                  # a GMP certificate's items, from what Claude read
    assert w['auto'] in homes or any(s['slot_id'] in homes for s in w['suggestions']), (w['auto'], [s['slot_id'] for s in w['suggestions']])
