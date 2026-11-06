"""API: create -> board -> upload (checks) -> gate -> generate -> export (3 outputs), safety rules."""
import io, json
from datetime import date
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app

PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True,
               dosage_specifics=['coated'], apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma', indication='pain-and-fever')
ENV = dict(tracking='P-MAA-0001', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg film-coated tablets',
           inn=['paracetamol'], description='Initial MAA', portal_id='EXAMPLE-0001')


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws'))


@pytest.fixture()
def pdf(tmp_path):
    return make_pdf(tmp_path / 'doc.pdf', 'content').read_bytes()


def new(c):
    r = c.post('/api/dossiers', json=dict(name='Examplol 500 mg FCT', profile=PROFILE, product=PRODUCT, envelope=ENV))
    assert r.status_code == 201, r.text
    return r.json()['id']


def up(c, did, slot, data, meta=None):
    return c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': ('x.pdf', io.BytesIO(data), 'application/pdf')},
                  data={'meta': json.dumps(meta or {})})


def test_profile_contradiction_is_explained(c):
    r = c.post('/api/dossiers', json=dict(name='x', profile={**PROFILE, 'licence': 'imported_bulk'}, product=PRODUCT))
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-PROFILE'
    assert r.json()['detail']['ar']


def test_board_upload_and_status(c, pdf):
    did = new(c)
    b = c.get(f'/api/dossiers/{did}/board').json()
    st = {s['slot_id']: s['status'] for s in b['slots']}
    assert st['M1-01'] == 'not_started' and st['M1-14'] == 'not_applicable'
    r = up(c, did, 'M1-31', pdf)
    assert r.status_code == 201 and r.json()['check_status'] == 'conforming' and r.json()['version'] == 1
    assert up(c, did, 'M1-31', pdf).json()['version'] == 2                     # new version, nothing overwritten
    old = pdf.replace(b'%PDF-1.4', b'%PDF-1.3', 1)
    up(c, did, 'M1-02', old)
    st = {s['slot_id']: s['status'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    assert st['M1-31'] == 'conforming' and st['M1-02'] == 'non_conforming'
    r = up(c, did, 'M1-14', pdf)                                                # not applicable slot
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-SLOT-INACTIVE'


def test_withdraw_keeps_blob_and_audit(c, pdf):
    did = new(c)
    doc = up(c, did, 'M1-31', pdf).json()
    c.post(f"/api/dossiers/{did}/documents/{doc['id']}/withdraw")
    assert c.get(f'/api/dossiers/{did}/board').json()['counts'].get('conforming', 0) == 0
    assert c.get(f"/api/dossiers/{did}/documents/{doc['id']}/file").status_code == 200   # still recoverable
    c.post(f"/api/dossiers/{did}/documents/{doc['id']}/restore")
    events = [a['event'] for a in c.get(f'/api/dossiers/{did}/audit').json()]
    assert events[-3:] == ['document.added', 'document.withdrawn', 'document.restored']


def test_locked_op_refused(c, pdf):
    did = new(c)
    doc = up(c, did, 'M1-37', pdf).json()                 # GMP certificate
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/ops", json={'op': 'edit_text'})
    assert r.status_code == 403 and r.json()['detail']['code'] == 'E-LOCKED'
    assert c.post(f"/api/dossiers/{did}/documents/{doc['id']}/ops", json={'op': 'rename'}).json()['allowed']
    assert 'E-LOCKED' in [a['event'] for a in c.get(f'/api/dossiers/{did}/audit').json()]


def test_profile_change_moves_docs_to_unassigned(c, pdf):
    did = new(c)
    up(c, did, 'M1-33', pdf)                              # coating premix (coated)
    r = c.put(f'/api/dossiers/{did}/profile', json={**PROFILE, 'dosage_specifics': []}).json()
    assert 'M1-33' in r['removed'] and len(r['moved_to_unassigned']) == 1
    assert len(c.get(f'/api/dossiers/{did}/board').json()['unassigned']) == 1


def test_generate_requests_missing_data(c):
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/generate/salt', json={'data': {'trade_name': 'X'}})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-MISSING-DATA'
    assert 'apis' in r.json()['detail']['request_data']


def test_gate_and_full_export(c, pdf):
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/export', json={})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'E-GATE'
    board = c.get(f'/api/dossiers/{did}/board').json()
    for s in board['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started':
            meta = {}
            if s['req_id'] == 'M1-09':
                meta = {'pi_type': 'spc', 'lang': 'en'}
            elif s['module'] == 5:
                meta = {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'}
            assert up(c, did, s['slot_id'], pdf, meta).status_code == 201
    r = c.post(f'/api/dossiers/{did}/export', json={})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'E-PROVISIONAL-ACK'
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True})
    assert r.status_code == 201, r.text
    for k, url in r.json()['downloads'].items():
        z = c.get(url)
        assert z.status_code == 200 and z.content[:2] == b'PK', k
    assert 'not «EDA-valid»' in r.json()['label']
    v = r.json()['validation']
    assert v['eCTD 3.2.2']['ok'] and v['eCTD 4.0']['ok'], v
    rep = c.get(r.json()['report'])
    assert rep.status_code == 200 and 'EG-PF-15.11' in rep.text


@pytest.mark.skipif(not __import__('shutil').which('soffice'), reason='LibreOffice not installed')
def test_generate_cover_letter_into_slot(c):
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/generate/cover', json={'data': dict(
        trade_name='Examplol 500 mg', sequence='0000', submission_type='maa', unit='initial', tracking='P-MAA-0001',
        description='Initial MAA', company='Example Pharma S.A.E.', signatory='A. Example', signatory_title='MD')})
    assert r.status_code == 201, r.text
    assert r.json()['slot_id'] == 'M1-43' and r.json()['meta']['draft_unsigned'] is True
    assert r.json()['check_status'] in ('conforming', 'needs_attention')


def test_preview_three_outputs(c, pdf):
    did = new(c)
    up(c, did, 'M1-31', pdf)
    up(c, did, 'M1-09', pdf, {'pi_type': 'pl', 'lang': 'ar'})
    up(c, did, 'S-08@Paracetamol|Granules India', pdf)
    p3 = {r['slot_id']: r for r in c.get(f'/api/dossiers/{did}/preview?output=ectd32').json()['rows']}
    assert p3['M1-31']['path'] == 'm1/eg/12-form/128-composit/1281-compositcert/compositcert.pdf'
    assert p3['M1-31']['target'] == 'm1-2-8-1-compositcert'
    assert p3['M1-09']['path'] == 'm1/eg/13-pi/131-spclabelpl/ar/pl.pdf'
    assert p3['S-08@Paracetamol|Granules India']['target'] == 'm3-2-s-4-1-specification'
    p4 = {r['slot_id']: r for r in c.get(f'/api/dossiers/{did}/preview?output=ectd40').json()['rows']}
    assert p4['M1-31']['target'] == 'eg_1.2.8.1' and p4['M1-31']['path'] == 'm1/compositcert.pdf'
    assert p4['M1-09']['path'] == 'm1/pl-ar.pdf' and p4['S-08@Paracetamol|Granules India']['target'] == 'ich_3.2.s.4.1'
    pc = {r['slot_id']: r for r in c.get(f'/api/dossiers/{did}/preview?output=ctd').json()['rows']}
    assert pc['M1-31']['path'].startswith('Examplol 500 mg FCT/Module 1/')
    assert not list((c.app.state.store.root).glob('exports/*'))          # preview writes nothing


def test_concurrent_requests(c, pdf):
    """Board + preview + gate in parallel threads (the UI does this) must not break the store."""
    from concurrent.futures import ThreadPoolExecutor
    did = new(c)
    up(c, did, 'M1-31', pdf)
    urls = [f'/api/dossiers/{did}/board', f'/api/dossiers/{did}/preview?output=ectd32', f'/api/dossiers/{did}/gate'] * 8
    with ThreadPoolExecutor(8) as ex:
        codes = list(ex.map(lambda u: c.get(u).status_code, urls))
    assert codes == [200] * len(urls)


def test_generator_schemas_and_prefill(c):
    did = new(c)
    sch = c.get('/api/generators').json()
    assert {'cover', 'tracking', 'composition', 'salt', 'cep_commitment', 'stability_commitment', 'justification'} <= set(sch)
    assert any(f['type'] == 'list' for f in sch['composition']['fields'])
    pf = c.get(f'/api/dossiers/{did}/generate/cover/prefill').json()
    assert pf['trade_name'] == 'Examplol 500 mg film-coated tablets' and pf['tracking'] == 'P-MAA-0001'
    assert pf['company'] == 'Example Pharma S.A.E.' and 'signatory' not in pf          # never guessed
    pf = c.get(f'/api/dossiers/{did}/generate/cep_commitment/prefill?slot_id=M1-40@Paracetamol|Granules India').json()
    assert pf['api'] == 'Paracetamol' and pf['cep_holder'] == 'Granules India'
    assert c.get(f'/api/dossiers/{did}/generate/salt/prefill').json()['apis'] == [{'name_base': 'Paracetamol'}]


@pytest.mark.skipif(not __import__('shutil').which('soffice'), reason='LibreOffice not installed')
def test_generate_stability_commitment_and_reuse_data(c):
    did = new(c)
    data = dict(trade_name='Examplol 500 mg', strengths='500 mg', containers='Alu/PVC blister', long_term_condition='30 °C / 75 % RH',
                shelf_life='36 months', company='Example Pharma S.A.E.', signatory='A. Example', signatory_title='MD')
    r = c.post(f'/api/dossiers/{did}/generate/stability_commitment', json={'data': data})
    assert r.status_code == 201, r.text
    assert r.json()['slot_id'] == 'P-16'
    pf = c.get(f'/api/dossiers/{did}/generate/stability_commitment/prefill').json()
    assert pf['signatory'] == 'A. Example'                                            # last entered data reused


def test_structured_data_drives_cross_checks(c, pdf):
    from test_crosschecks import GOOD
    import copy
    did = new(c)
    up(c, did, 'M1-05', pdf)                                     # pricing certificate uploaded and conforming
    assert c.put(f'/api/dossiers/{did}/data', json=GOOD).json()['cross'] == []
    bad = copy.deepcopy(GOOD)
    bad['pack']['units_pricing'] = '1 x 10'
    r = c.put(f'/api/dossiers/{did}/data', json=bad).json()
    assert [f['id'] for f in r['cross']] == ['XC-07']
    b = c.get(f'/api/dossiers/{did}/board').json()
    s = next(x for x in b['slots'] if x['slot_id'] == 'M1-05')
    assert s['status'] == 'non_conforming' and s['cross'][0]['id'] == 'XC-07'      # document fine, dossier inconsistent
    g = c.get(f'/api/dossiers/{did}/gate').json()
    assert not g['ok'] and g['cross_blocking'][0]['id'] == 'XC-07'


@pytest.mark.skipif(not __import__('shutil').which('soffice'), reason='LibreOffice not installed')
def test_m3_tables_from_data(c):
    from test_crosschecks import GOOD
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/generate/p54', json={'data': {}})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-MISSING-DATA'          # no data yet
    c.put(f'/api/dossiers/{did}/data', json=GOOD)
    r = c.post(f'/api/dossiers/{did}/generate/p54', json={'data': {}})
    assert r.status_code == 201, r.text
    pdf = c.get(f"/api/dossiers/{did}/documents/{r.json()['id']}/file").content
    import io
    from pypdf import PdfReader
    txt = ' '.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)
    assert 'EX0001' in txt and '99.8' in txt and '3.2.P.5.4' in txt
    r = c.post(f'/api/dossiers/{did}/generate/s44', json={'data': {}, 'slot_id': 'S-10@Paracetamol|Granules India'})
    assert r.status_code == 201 and r.json()['slot_id'] == 'S-10@Paracetamol|Granules India'
