"""P3 through the API: initial sequence, then a variation sequence with only the changes."""
import io, json, shutil, zipfile
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_api import new, up

pytestmark = pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (tracking table)')


def fill_all(c, did, pdf):
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started':
            meta = {'pi_type': 'spc', 'lang': 'en'} if s['req_id'] == 'M1-09' else (
                {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {})
            assert up(c, did, s['slot_id'], pdf, meta).status_code == 201


def names(zbytes):
    return zipfile.ZipFile(io.BytesIO(zbytes)).namelist()


def test_initial_then_variation(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    b = c.get(f'/api/dossiers/{did}/board').json()
    assert next(s for s in b['slots'] if s['req_id'] == 'M1-44')['status'] == 'auto'     # tracking table: tool-made
    fill_all(c, did, pdf)
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['sequences']['ectd32']['sequence'] == '0000' and j['sequences']['ectd40']['sequence'] == 1
    assert j['validation']['eCTD 3.2.2']['ok'] and j['validation']['eCTD 4.0']['ok'], j['validation']
    assert any(n.endswith('m1/eg/10-cover/tracking.pdf') for n in names(c.get(j['downloads']['ectd32']).content))
    # follow-on without a type / without a new cover letter is refused
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']})
    assert r.json()['detail']['code'] == 'E-SUBMISSION'
    sub = {'type': 'var-pac-b', 'unit': 'initial', 'mode': 'single', 'description': 'PAC-B: change in batch size', 'tracking': 'P-VAR-PAC-B-0007'}
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], 'submission': sub})
    assert r.json()['detail']['code'] == 'E-COVER'
    # the change: new composition certificate version + new cover letter
    old = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-31')['documents'][0]['id']
    pdf2 = make_pdf(tmp_path / 'd2.pdf', 'composition v2').read_bytes()
    r = c.post(f'/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('comp-v2.pdf', io.BytesIO(pdf2), 'application/pdf')},
               data={'meta': '{}', 'replaces': old})
    assert r.status_code == 201 and r.json()['version'] == 2
    cover_old = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-43')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0001.pdf', io.BytesIO(make_pdf(tmp_path / 'c1.pdf', 'cover 0001').read_bytes()), 'application/pdf')},
           data={'meta': '{}', 'replaces': cover_old})
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32', 'ectd40'], 'submission': sub})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['sequences']['ectd32'] == {'sequence': '0001', 'operations': {'new': 2, 'replace': 1, 'delete': 0}}
    assert j['sequences']['ectd40']['sequence'] == 2 and j['sequences']['ectd40']['operations']['replace'] == 1
    assert j['validation']['eCTD 3.2.2']['ok'] and j['validation']['eCTD 4.0']['ok'], j['validation']
    n = names(c.get(j['downloads']['ectd32']).content)
    assert all(x.startswith('0001/') for x in n)                                       # only the new sequence
    assert any('1281-compositcert' in x for x in n) and not any('32p' in x for x in n)  # unchanged M3 not resent
    hist = c.get(f'/api/dossiers/{did}/submissions').json()
    assert [h['seq'] for h in hist['ectd32']] == ['0000', '0001'] and hist['ectd32'][1]['envelope']['type'] == 'var-pac-b'
