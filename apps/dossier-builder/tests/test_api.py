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


def test_external_reference_blocks_until_file_uploaded(c, pdf):
    """A document registered from the company Drive shows as «received», blocks export, and is replaced by the real file."""
    did = new(c)
    url = 'https://drive.google.com/file/d/abc/view'
    r = c.post(f'/api/dossiers/{did}/slots/M1-31/references', json={'title': 'GMP certificate', 'url': url, 'ref_id': 'abc'})
    assert r.status_code == 201, r.text
    ref = r.json()
    assert ref['check_status'] == 'received' and ref['meta']['external'] and ref['sha256'] == ''
    b = c.get(f'/api/dossiers/{did}/board').json()
    s = next(x for x in b['slots'] if x['slot_id'] == 'M1-31')
    assert s['status'] == 'received' and s['external'] == [ref['id']]
    assert 'M1-31' in c.get(f'/api/dossiers/{did}/gate').json()['external_only']
    assert c.get(f"/api/dossiers/{did}/documents/{ref['id']}/file").status_code == 404
    assert c.post(f"/api/dossiers/{did}/documents/{ref['id']}/fix").status_code == 422
    rows = c.get(f'/api/dossiers/{did}/preview?output=ectd32').json()['rows']
    assert any(x['doc_id'] == ref['id'] and x['external'] == url for x in rows)
    assert c.post(f'/api/dossiers/{did}/slots/M1-14/references', json={'title': 'x', 'url': url}).status_code == 422
    assert c.post(f'/api/dossiers/{did}/slots/M1-31/references', json={'title': 'x'}).status_code == 422
    r = c.post(f'/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('composition certificate.pdf', io.BytesIO(pdf), 'application/pdf')},   # a file named like a GMP certificate is refused here by the kind rule
               data={'replaces': ref['id']})
    assert r.status_code == 201 and r.json()['check_status'] == 'conforming'
    s = next(x for x in c.get(f'/api/dossiers/{did}/board').json()['slots'] if x['slot_id'] == 'M1-31')
    assert s['status'] == 'conforming' and not s['external']
    assert 'M1-31' not in c.get(f'/api/dossiers/{did}/gate').json()['external_only']
    assert any(e['event'] == 'reference.added' for e in c.get(f'/api/dossiers/{did}/audit').json())


def test_expired_evidence_blocks_item(c, pdf):
    """A certificate past its validity date makes its item non-conforming and blocks export; 90 days before, a warning."""
    from datetime import date, timedelta
    did = new(c)
    d = up(c, did, 'M1-31', pdf).json()
    assert d['check_status'] == 'conforming'
    past = (date.today() - timedelta(days=10)).isoformat()
    r = c.put(f"/api/dossiers/{did}/documents/{d['id']}/validity", json={'valid_until': past})
    assert r.status_code == 200 and r.json()['check_status'] == 'non_conforming'
    assert r.json()['findings'][-1]['rule'] == 'DOC-EXPIRED' and 'منتهي' in r.json()['findings'][-1]['ar']
    s = next(x for x in c.get(f'/api/dossiers/{did}/board').json()['slots'] if x['slot_id'] == 'M1-31')
    assert s['status'] == 'non_conforming'
    assert 'M1-31' in c.get(f'/api/dossiers/{did}/gate').json()['non_conforming']
    soon = (date.today() + timedelta(days=30)).isoformat()
    r = c.put(f"/api/dossiers/{did}/documents/{d['id']}/validity", json={'valid_until': soon})
    assert r.json()['check_status'] == 'needs_attention' and r.json()['findings'][-1]['rule'] == 'DOC-EXPIRING'
    far = (date.today() + timedelta(days=400)).isoformat()
    assert c.put(f"/api/dossiers/{did}/documents/{d['id']}/validity", json={'valid_until': far}).json()['check_status'] == 'conforming'
    assert c.put(f"/api/dossiers/{did}/documents/{d['id']}/validity", json={'valid_until': '31/12/2026'}).status_code == 422
    ref = c.post(f'/api/dossiers/{did}/slots/M1-19/references',
                 json={'title': 'Register', 'url': 'https://drive.google.com/x', 'valid_until': past}).json()
    assert ref['check_status'] == 'non_conforming'


def test_capabilities_are_counted_from_the_engine(c):
    d = c.get('/api/capabilities').json()
    assert d['requirements']['total'] == 101 and d['requirements']['by_module']['1'] == 45
    assert d['variations']['total'] == 90 and d['validators']['ectd32']['automated'] > 80
    assert {g['kind'] for g in d['generators']} >= {'cover', 'composition', 'salt', 'p51'}
    assert 'XC-06' in d['checks']['cross'] and 'NP040-NUM' in d['checks']['cross']
    assert d['doc_types'] == 21 and d['outputs'] == ['ctd', 'ectd32', 'ectd40']


def test_profile_preview_before_any_dossier(c):
    p = c.post('/api/profile/preview', json={**PROFILE, 'licence': 'toll'}).json()
    assert p['counts']['R'] > 60 and p['column'] == 'G_LOC' and not p['column_assumed']
    ids = {s['req_id'] for s in p['slots'] if s['level'] == 'R'}
    assert 'M1-20' in ids and 'M1-31' in ids                      # toll licence + composition certificate
    assert 'M1-31' in p['generable'] and 'M1-37' in p['third_party']
    assert any(s['slot_id'].startswith('S-') and s['item'] for s in p['slots'])   # per-API expansion
    # the wizard asks for the APIs in step 3: the preview still works without them
    p0 = c.post('/api/profile/preview', json={**PROFILE, 'apis': []}).json()
    assert p0['counts']['R'] > 40 and not any(s['item'] for s in p0['slots'])
    # a real contradiction is still refused with its explanation
    r = c.post('/api/profile/preview', json={**PROFILE, 'origin': 'local', 'licence': 'imported'})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-PROFILE'


def test_dossier_list_carries_profile_and_product(c):
    did = new(c)
    row = next(d for d in c.get('/api/dossiers').json() if d['id'] == did)
    assert row['profile']['licence'] == 'own' and row['product']['name'] == PRODUCT['name']


def test_without_libreoffice_word_drafts_and_text_tracking_table(c, pdf, monkeypatch):
    """Browser edition, or a desktop without LibreOffice: generated letters are Word drafts that the uploaded PDF
    replaces; the export still carries its tracking table as a text-only PDF."""
    from dossier_engine.app import api as api_mod, exporter

    def no_soffice(*a, **k):
        raise RuntimeError('LibreOffice not found')
    monkeypatch.setattr(api_mod, 'find_soffice', lambda: None)
    monkeypatch.setattr(exporter, 'to_pdf', no_soffice)
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/generate/composition', json={'slot_id': 'M1-31', 'data': dict(
        trade_name='Examplol 500 mg', dosage_form='film-coated tablet', signatory='A. Example', signatory_title='MD',
        components=[dict(name='Paracetamol', function='API', qty_mg=500, standard='Ph. Eur.'),
                    dict(name='Opadry II', function='Film coat', qty_mg=15, standard='In-house', part='coat')])})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d['filename'] == 'composition.docx' and d['check_status'] == 'needs_attention' and d['meta']['draft_unsigned']
    assert d['findings'][0]['rule'] == 'DOCX-DRAFT'
    f = c.get(f'/api/dossiers/{did}/documents/{d["id"]}/file')
    assert f.status_code == 200 and f.content[:2] == b'PK' and 'wordprocessingml' in f.headers['content-type']
    assert 'M1-31' in c.get(f'/api/dossiers/{did}/gate').json()['unsigned']
    r2 = up(c, did, 'M1-31', pdf, {'signed_for': d['id']})                    # the signed PDF replaces the draft
    assert r2.status_code == 201 and r2.json()['version'] == 2 and r2.json()['check_status'] == 'conforming'
    assert 'M1-31' not in c.get(f'/api/dossiers/{did}/gate').json()['unsigned']
    r3 = c.post(f'/api/dossiers/{did}/slots/M1-37/request', json={'issuer': 'GMP authority', 'lang': 'en', 'signatory': 'A', 'signatory_title': 'B'})
    assert r3.status_code == 201, r3.text
    letter = c.get(r3.json()['letter'])
    assert letter.status_code == 200 and letter.content[:2] == b'PK' and 'wordprocessingml' in letter.headers['content-type']
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] in ('not_started', 'waiting'):
            meta = {'pi_type': 'spc', 'lang': 'en'} if s['req_id'] == 'M1-09' else (
                {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {})
            assert up(c, did, s['slot_id'], pdf, meta).status_code == 201, s['slot_id']
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True})
    assert r.status_code == 201, r.text
    v = r.json()['validation']
    assert v['eCTD 3.2.2']['ok'] and v['eCTD 4.0']['ok'], v


def test_profile_preview_accepts_a_stringified_specifics_list(tmp_path):
    """The browser's model once returned dosage_specifics as the text «[]»: the preview must not read it as the values '[' and ']'."""
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    for sp, want in (("[]", []), ("['coated']", ['coated']), ("coated, sterile", ['coated', 'sterile']), ([' coated '], ['coated'])):
        r = c.post('/api/profile/preview', json={**PROFILE, 'dosage_specifics': sp}, headers={'X-DB': '1'})
        assert r.status_code == 200, (sp, r.text)
    r = c.post('/api/profile/preview', json={**PROFILE, 'dosage_specifics': "['nonsense']"}, headers={'X-DB': '1'})
    assert r.status_code == 422 and 'nonsense' in r.text                                      # unknown values are still refused, by name


def test_a_file_must_be_the_document_its_item_expects(tmp_path):
    """The kind rule: a stability approval uploaded to the pricing item is refused (blocking finding naming the item it belongs to)
    and «move» takes it there; the intake drafts keep the wizard's work (state + files) on the server."""
    from fixtures_pdf import make_pdf_lines
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='X', profile=PROFILE, product=PRODUCT, envelope=ENV), headers={'X-DB': '1'}).json()['id']
    slots = {s['req_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    stab = make_pdf_lines(tmp_path / 'stability approval.pdf', ['Egyptian Drug Authority', 'Stability Study Approval', 'Trade name: X', 'Shelf life: 24 months'], 'Stability').read_bytes()
    r = c.post(f"/api/dossiers/{did}/slots/{slots['M1-05']['slot_id']}/documents", files={'file': ('stability approval.pdf', io.BytesIO(stab), 'application/pdf')}, data={'meta': '{}'})
    d = r.json()
    assert r.status_code == 201 and d['check_status'] == 'non_conforming'
    f = d['findings'][0]
    assert f['rule'] == 'DOC-KIND' and f['severity'] == 'block' and f['action'] == 'move' and f['extra']['kind'] == 'stability'
    assert f['extra']['suggested_slot'] in {slots[k]['slot_id'] for k in ('M1-34', 'S-14', 'P-16') if k in slots} and 'مستند ثبات' in f['ar']
    mv = c.post(f"/api/dossiers/{did}/documents/{d['id']}/move", json={'slot_id': f['extra']['suggested_slot']}, headers={'X-DB': '1'}).json()
    assert mv['slot_id'] == f['extra']['suggested_slot'] and mv['check_status'] == 'conforming' and mv['meta']['moved_from'] == slots['M1-05']['slot_id']
    after = {s['req_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    assert all(x['id'] != d['id'] for x in after['M1-05']['documents'])                       # gone from the pricing item
    # the right document in the right item passes the rule
    price = make_pdf_lines(tmp_path / 'pricing.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: X', 'Public price: 45 EGP'], 'Pricing').read_bytes()
    r2 = c.post(f"/api/dossiers/{did}/slots/{slots['M1-05']['slot_id']}/documents", files={'file': ('pricing.pdf', io.BytesIO(price), 'application/pdf')}, data={'meta': '{}'})
    assert r2.status_code == 201 and not any(x['rule'] == 'DOC-KIND' for x in r2.json()['findings'])
    # intake drafts
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0}}, headers={'X-DB': '1'}).json()
    c.put(f"/api/intake/drafts/{dr['id']}", json={'state': {'step': 1, 'd': {'trade': 'X'}, 'texts': {'a.pdf': {'text': 'abc'}}}}, headers={'X-DB': '1'})
    c.post(f"/api/intake/drafts/{dr['id']}/files", files={'file': ('a.pdf', io.BytesIO(stab), 'application/pdf')}, data={'kind': 'stability_data'}, headers={'X-DB': '1'})
    g = c.get(f"/api/intake/drafts/{dr['id']}").json()
    assert g['state']['d']['trade'] == 'X' and g['files'][0]['filename'] == 'a.pdf' and g['files'][0]['kind'] == 'stability_data'
    assert c.get(f"/api/intake/drafts/{dr['id']}/files/a.pdf").content == stab
    assert [x['id'] for x in c.get('/api/intake/drafts').json()] == [dr['id']]
    assert c.delete(f"/api/intake/drafts/{dr['id']}", headers={'X-DB': '1'}).json()['ok'] and c.get(f"/api/intake/drafts/{dr['id']}").status_code == 404
