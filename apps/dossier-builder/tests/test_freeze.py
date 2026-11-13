"""A sequence is frozen once submitted (updates list, item 19): its receipt is kept with it, it can never be replaced or discarded;
a sequence not submitted yet is replaced by the next export (the same number) or discarded."""
import io, json, shutil
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_api import new
from test_lifecycle_api import fill_all

pytestmark = pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (tracking table)')


def test_a_submitted_sequence_is_frozen_and_a_draft_one_is_replaced(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    exp = lambda **kw: c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], **kw})
    assert exp().json()['sequences']['ectd32']['sequence'] == '0000'
    r = exp(replace_last=True)                                                       # not submitted yet: the same number again
    assert r.status_code == 201 and r.json()["sequences"]["ectd32"]["sequence"] == "0000", r.text
    assert [h['seq'] for h in c.get(f'/api/dossiers/{did}/submissions').json()['ectd32']] == ['0000']
    receipt = make_pdf(tmp_path / 'r.pdf', 'EDA receipt').read_bytes()
    r = c.post(f'/api/dossiers/{did}/submissions/ectd32/0000/submitted',
               data={'meta': json.dumps({'submitted': '2026-11-10', 'tracking': 'P-MAA-0001', 'ack': '2026-11-12'})},
               files={'file': ('receipt.pdf', io.BytesIO(receipt), 'application/pdf')})
    assert r.status_code == 200 and r.json()['tracking'] == 'P-MAA-0001'
    h = c.get(f'/api/dossiers/{did}/submissions').json()['ectd32'][0]
    assert h['frozen'] and h['receipt']['submitted'] == '2026-11-10'
    assert c.get(f'/api/dossiers/{did}/submissions/ectd32/0000/receipt').content[:4] == b'%PDF'
    assert c.delete(f'/api/dossiers/{did}/submissions/ectd32/0000').json()['detail']['code'] == 'E-FROZEN'
    sub = {'type': 'var-pac-b', 'unit': 'initial', 'mode': 'single', 'description': 'PAC-B', 'tracking': 'P-VAR-0007'}
    cover = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-43')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0001.pdf', io.BytesIO(make_pdf(tmp_path / 'c.pdf', 'cover 0001').read_bytes()), 'application/pdf')},
           data={'meta': '{}', 'replaces': cover})
    r = exp(replace_last=True, submission=sub)                                       # the last one was submitted: never replaced
    assert r.status_code == 201 and r.json()['sequences']['ectd32']['sequence'] == '0001'
    cover = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-43')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0002.pdf', io.BytesIO(make_pdf(tmp_path / 'c2.pdf', 'cover 0002').read_bytes()), 'application/pdf')},
           data={'meta': '{}', 'replaces': cover})
    r2 = exp(submission={k: v for k, v in sub.items() if k != 'tracking'})                     # the next one names no tracking number
    assert r2.status_code == 201 and r2.json()['sequences']['ectd32']['sequence'] == '0002', r2.text
    assert c.get(f'/api/dossiers/{did}/submissions').json()['ectd32'][-1]['envelope']['tracking'] == 'P-VAR-0007'   # filled from the one before
    assert c.delete(f'/api/dossiers/{did}/submissions/ectd32/0002').json() == {'ok': True}
    assert c.delete(f'/api/dossiers/{did}/submissions/ectd32/0001').json() == {'ok': True}      # not submitted: it can go
    assert [h['seq'] for h in c.get(f'/api/dossiers/{did}/submissions').json()['ectd32']] == ['0000']
    assert c.post(f'/api/dossiers/{did}/submissions/ectd32/0000/submitted', data={'meta': json.dumps({'ack': '12/11/2026'})}).json()['detail']['code'] == 'E-DATE'


def test_the_submitted_dossier_four_ways(tmp_path):
    """Item 23: cumulative, by sequence, by activity, by study."""
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    assert c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']}).status_code == 201
    v = c.get(f'/api/dossiers/{did}/views').json()
    assert v['sequences'][0]['seq'] == '0000' and all(x['op'] == 'new' for x in v['sequences'][0]['leaves'])
    assert len(v['cumulative']) == len(v['sequences'][0]['leaves']) and v['activities'][0]['sequences'][0]['seq'] == '0000'
    st = {s['study']: s for s in v['studies']}
    assert 'EXM-BE-01' in st and all(x['node'].startswith('5') for x in st['EXM-BE-01']['leaves'])      # the tabular listing has no study: its own group
    assert c.get(f'/api/dossiers/{did}/views', params={'output': 'nope'}).status_code == 422


def test_a_document_of_an_earlier_sequence_is_referred_to_not_sent_again(tmp_path):
    """Item 22: the item takes the document from submitted sequence 0000; sequence 0001 refers to that file («../0000/…») and
    carries no copy; the validator, given the earlier sequence, passes it."""
    import zipfile
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']})
    assert r.status_code == 201, r.text
    leaves = c.get(f'/api/dossiers/{did}/views').json()['sequences'][0]['leaves']
    comp = next(x for x in leaves if x['node'] == '1.2.8.1' or 'compositcert' in (x['href'] or ''))
    old = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-31')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/documents/{old}/withdraw')                                     # the item's document was withdrawn by mistake
    bad = c.post(f'/api/dossiers/{did}/slots/M1-31/reference', json={'seq': '0000', 'href': comp['href']})
    assert bad.json()['detail']['code'] == 'E-REF'                                              # 0000 was not submitted yet
    c.post(f'/api/dossiers/{did}/submissions/ectd32/0000/submitted', data={'meta': '{}'})
    ref = c.post(f'/api/dossiers/{did}/slots/M1-31/reference', json={'seq': '0000', 'href': comp['href']})
    assert ref.status_code == 201, ref.text
    assert ref.json()['meta']['reference'] == {'output': 'ectd32', 'seq': '0000', 'href': comp['href']}
    cover = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-43')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0001.pdf', io.BytesIO(make_pdf(tmp_path / 'c.pdf', 'cover 0001').read_bytes()), 'application/pdf')},
           data={'meta': '{}', 'replaces': cover})
    sub = {'type': 'var-pac-n', 'unit': 'initial', 'mode': 'single', 'description': 'PAC-N'}
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], 'submission': sub})
    assert r.status_code == 201, r.text
    names = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['ectd32']).content)).namelist()
    assert not any('compositcert' in n for n in names)                                           # not sent again
    j = r.json()
    assert j['validation']['eCTD 3.2.2']['ok'], str(j['validation']['eCTD 3.2.2'])[:3000]
    seq1 = c.get(f'/api/dossiers/{did}/views').json()['sequences'][1]['leaves']
    assert any((x['href'] or '').startswith('../0000/') for x in seq1)
