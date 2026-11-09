"""The non-conforming → conforming loop through the API: auto-fix, re-obtain request, signed scan."""
import io, json, shutil
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_api import PROFILE, PRODUCT, ENV, new, up

SOFFICE = pytest.mark.skipif(not (shutil.which('soffice') and shutil.which('gs')), reason='LibreOffice/ghostscript missing')


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws'))


@pytest.fixture()
def pdf13(tmp_path):
    return make_pdf(tmp_path / 'g.pdf', 'GMP').read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1)


def status(c, did, sid):
    return next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == sid)


@SOFFICE
def test_auto_fix_makes_new_conforming_version(c, pdf13):
    did = new(c)
    doc = up(c, did, 'M1-37', pdf13).json()                         # GMP certificate, PDF 1.3
    assert status(c, did, 'M1-37')['status'] == 'non_conforming'
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/fix").json()
    assert [x['op'] for x in r['done']] == ['pdf_version_normalise'] and r['document']['check_status'] == 'conforming'
    s = status(c, did, 'M1-37')
    assert s['status'] == 'conforming' and [d['version'] for d in s['documents']] == [2]   # original superseded, kept
    assert c.get(f"/api/dossiers/{did}/documents/{doc['id']}/file").status_code == 200


@SOFFICE
def test_reobtain_request_waiting_then_closed(c, tmp_path):
    from pypdf import PdfWriter
    src = make_pdf(tmp_path / 's.pdf', 'GMP')
    w = PdfWriter(clone_from=str(src)); w.encrypt(user_password='', owner_password='o', permissions_flag=0)
    p = tmp_path / 'sec.pdf'; w.write(open(p, 'wb'))
    did = new(c)
    doc = up(c, did, 'M1-37', p.read_bytes().replace(b'%PDF-1.3', b'%PDF-1.4', 1)).json()
    assert c.post(f"/api/dossiers/{did}/documents/{doc['id']}/fix").json()['document'] is None   # evidence: issuer only
    r = c.post(f'/api/dossiers/{did}/slots/M1-37/request', json={'issuer': 'Example Pharma QA', 'signatory': 'A. Example',
                                                                 'signatory_title': 'RA Manager'})
    assert r.status_code == 201, r.text
    assert any('security' in x.lower() for x in r.json()['problems'])
    assert c.get(r.json()['letter']).content[:5] == b'%PDF-'
    s = status(c, did, 'M1-37')
    assert s['status'] == 'waiting' and s['request']['issuer'] == 'Example Pharma QA'
    assert 'M1-37' in c.get(f'/api/dossiers/{did}/gate').json()['non_conforming']
    up(c, did, 'M1-37', make_pdf(tmp_path / 'ok.pdf', 'GMP ok').read_bytes())                 # issuer sent a good copy
    assert c.get(f'/api/dossiers/{did}/requests').json() == []
    assert 'request.closed' in [a['event'] for a in c.get(f'/api/dossiers/{did}/audit').json()]


@SOFFICE
def test_signed_scan_replaces_draft(c, tmp_path):
    did = new(c)
    g = c.post(f'/api/dossiers/{did}/generate/cover', json={'data': dict(
        trade_name='Examplol', sequence='0000', submission_type='maa', unit='initial', tracking='P-MAA-0001',
        description='Initial MAA', company='Example Pharma S.A.E.', signatory='A. Example', signatory_title='MD')}).json()
    s = status(c, did, 'M1-43')
    assert s['unsigned'] == [g['id']] and s['status'] == 'needs_attention'
    assert 'M1-43' in c.get(f'/api/dossiers/{did}/gate').json()['unsigned']
    signed = make_pdf(tmp_path / 'signed.pdf', 'signed cover').read_bytes()
    r = up(c, did, 'M1-43', signed, {'signed_for': g['id']}).json()
    assert r['doc_class'] == 'signed_scan'
    s = status(c, did, 'M1-43')
    assert s['unsigned'] == [] and [d['id'] for d in s['documents']] == [r['id']] and s['status'] == 'conforming'
    lock = c.post(f"/api/dossiers/{did}/documents/{r['id']}/ops", json={'op': 'edit_text'})
    assert lock.status_code == 403                                   # signed copy is evidence now
    bad = up(c, did, 'M1-31', signed, {'signed_for': g['id']})       # wrong section
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-SIGNED-FOR'
