"""The largest file follows the dossier's authority (the library's rule cards, each cited to its page and line): 100 MB for Egypt
(as it always was), the Gulf and the others (ICH), 500 MB for the EU (validation criteria v8.2, 15.BP1), 400 MB for the FDA
(criterion 1238). Files of that size are not made here: the check is told the size."""
import io, os
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.checks import pdf as pdfcheck
from dossier_engine.app.api import create_app


def big(monkeypatch, mb, mark):
    real = os.path.getsize
    monkeypatch.setattr(pdfcheck.os.path, 'getsize', lambda p: int(mb * 1e6) if mark in str(p) else real(p))


def size_finding(path, authority):
    return next((f for f in pdfcheck.check(str(path), authority=authority).findings if f.rule == 'PDF-SIZE'), None)


@pytest.mark.parametrize('mb, authority, limit', [
    (150, None, 100), (150, 'EG-EDA', 100), (150, 'GCC', 100), (150, 'OTHER', 100), (150, 'EU', None), (150, 'US-FDA', None),
    (450, 'US-FDA', 400), (450, 'EU', None), (600, 'EU', 500)])
def test_the_limit_is_the_authoritys(tmp_path, monkeypatch, mb, authority, limit):
    f = make_pdf(tmp_path / 'module3.pdf', 'Specification of the finished product')
    big(monkeypatch, mb, 'module3.pdf')
    got = size_finding(f, authority)
    if limit is None:
        assert got is None
    else:
        assert got and f'at most {limit} MB' in got.en and f'والحد الأقصى لملف eCTD {limit} ميغابايت' in got.ar
        assert ({100: 'ICH', 500: 'EU eCTD validation criteria v8.2, criterion 15.BP1', 400: 'FDA eCTD validation criteria, criterion 1238'}[limit]
                in got.source)


def test_egypt_says_exactly_what_it_said(tmp_path, monkeypatch):
    f = make_pdf(tmp_path / 'module3.pdf', 'Specification of the finished product')
    big(monkeypatch, 150, 'module3.pdf')
    got = size_finding(f, 'EG-EDA')
    assert got.en == '150 MB; an eCTD file is at most 100 MB (ICH) — PdfCraft can make it smaller (images above 225 ppi brought to 150 ppi), or split it.'
    assert got.source == 'ICH eCTD specification App. 7 (100 MB a file); ICH M2 file formats v1.3 §2.3 (500 MB)'


@pytest.mark.parametrize('country, flagged', [('EG', True), ('SA', True), ('DE', False), ('US', False)])
def test_a_document_added_to_a_dossier_is_held_to_its_authoritys_limit(tmp_path, monkeypatch, country, flagged):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    h = {'X-DB': '1'}
    prof = dict(dossier_kind='generic', origin='imported' if country != 'EG' else 'local', licence='own', activity='new',
                apis=[dict(name='Exampletine', manufacturer='Example API Co.', option='CEP')])
    body = dict(name='Dermacure (made up)', profile=prof, product=dict(name='Dermacure 20 mg', dosageform='cream', manufacturer='Example Pharm'), envelope={})
    if country != 'EG':
        body['country'] = country
    did = c.post('/api/dossiers', json=body, headers=h).json()['id']
    slot = next(x['slot_id'] for x in c.get(f'/api/dossiers/{did}/board', headers=h).json()['slots'] if x['req_id'] in ('P-09',))
    pdf = make_pdf(tmp_path / 'spec.pdf', 'Specification of the finished product').read_bytes()
    big(monkeypatch, 150, '.check-')                                  # the copy the store checks
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': ('spec.pdf', io.BytesIO(pdf), 'application/pdf')},
               data={'meta': '{}'}, headers=h)
    assert r.status_code == 201, r.text
    rules = {f['rule'] for f in r.json()['findings']}
    assert ('PDF-SIZE' in rules) == flagged, rules
