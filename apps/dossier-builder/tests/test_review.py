"""Regulatory Reviewer: pack lint, review run on a seeded dossier, response cycle, letters, sign-off, AI suggestions."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import packs
from dossier_engine.app.api import create_app
from dossier_engine.review import pack as rpack, checks

PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True, dosage_specifics=['coated'],
               apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma', indication='pain-and-fever')
ENV = dict(tracking='P-MAA-0001', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg film-coated tablets', inn=['paracetamol'], description='Initial MAA', portal_id='EXAMPLE-0001')
DATA = {'apis': [dict(name='Paracetamol', manufacturer='Granules India', option='CEP', spec_standard='Ph. Eur. 11.5', cep_no='R1-CEP 2019-123', cep_status='valid', address_gmp='Plot 1, Hyderabad')],
        'batches': [dict(no='EX-23-001', kind='fpp', size='120000', scale='pilot', date='2025-02-10', site='Cairo'),
                    dict(no='PA-001', kind='api', api='Paracetamol', size='50 kg'), dict(no='PA-002', kind='api', api='Paracetamol', size='50 kg')],
        'specs': {'product': [dict(test='Description', limit='white tablets'), dict(test='Identification', limit='IR + HPLC'), dict(test='Assay', limit='95.0–105.0%'),
                              dict(test='Related substances', limit='NMT 0.2%'), dict(test='Dissolution', limit='NLT 80% (Q) in 30 min')]},
        'results': {'EX-23-001': {'Description': 'white tablets', 'Identification': 'complies', 'Assay': '99.1', 'Related substances': '0.05', 'Dissolution': '94'}},
        'composition': [dict(name='Paracetamol', standard='Ph. Eur.', function='active', grade='powder'), dict(name='Opadry II white', standard='in-house', function='', grade='85F18422')]}


def test_pack_is_clean_and_cited():
    p = rpack.load()
    assert rpack.lint(p, packs.load('eda.ctd.nta065.v5'), checks.CHECKS) == []
    assert p.counts()['total'] >= 80
    for q in p.questions:
        assert q['source'].get('code'), q['id']
        if q['layer'] == 'intl':
            assert q['anchor']['code'], q['id']
        assert q['question']['ar'] and q['deficiency']['ar'], q['id']


@pytest.fixture()
def seeded(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Examplol 500 mg FCT', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']

    def up(slot, name, lines, title):
        pdf = make_pdf_lines(tmp_path / name, lines, title)
        r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, io.BytesIO(pdf.read_bytes()), 'application/pdf')}, data={'meta': json.dumps({})})
        assert r.status_code == 201, r.text
    up('M1-43', 'cover.pdf', ['Cover letter', 'We confirm that the submitted data are true, complete and correct.'], 'Cover letter')
    up('P-12', 'imp.pdf', ['Impurities', 'Potential impurities discussed per ICH Q3A. Elemental impurities risk assessment per ICH Q3D attached. Mutagenic impurities assessed per ICH M7. Benzene: not used.'], '3.2.P.5.5')
    up('P-02', 'dev.pdf', ['Pharmaceutical development', 'Reference product: Referenzol 500 mg. QTPP defined. Critical quality attributes (CQA) and critical process parameters (CPP) identified.'], '3.2.P.2')
    up('P-07', 'pv.pdf', ['Process validation', 'Summary of results for one batch only.'], '3.2.P.3.5')
    assert c.put(f'/api/dossiers/{did}/data', json=DATA).status_code == 200
    return c, did


def test_review_run_findings_and_verdicts(seeded):
    c, did = seeded
    r = c.post(f'/api/dossiers/{did}/review', json={'strictness': 'international', 'actor': 'mona'})
    assert r.status_code == 201, r.text
    run, fs = r.json()['run'], r.json()['findings']
    q = {f['question_id']: f for f in fs}
    assert run['verdict'] == 'not_ready' and run['dept_verdicts']['screening']['verdict'] == 'reject'      # 26 required M1 items missing
    assert q['SC-COVER-01']['verdict'] == 'adequate' and q['SC-COVER-01']['payload']['evidence'][0]['page'] == 1
    assert q['QM-S32-02']['verdict'] == 'adequate' and q['QM-P2-01']['verdict'] == 'adequate'
    assert q['QM-P35-01']['verdict'] == 'deficient' and q['QM-P35-01']['origin'] == 'text'
    assert q['QM-P54-01']['verdict'] == 'deficient' and q['QM-P54-01']['severity'] == 'critical'
    assert q['QM-P1-01']['verdict'] == 'deficient' and 'Opadry' in q['QM-P1-01']['payload']['evidence'][1]['value']
    assert q['SC-CEP-01']['verdict'] == 'adequate' and q['QM-P51-01']['verdict'] == 'adequate'
    assert any(f['question_id'].startswith('MISSING-M1-') and f['severity'] == 'critical' for f in fs)
    assert any(f['question_id'].startswith('NP040-') and f['origin'] == 'data' for f in fs)       # the data cross-checks flow into the quality findings
    assert run['clock']['track'] == 'c2_track_c' and [s['wds'] for s in run['clock']['stages']] == [15, 60, 10, 60]
    assert all(f['payload']['source'].get('code') for f in fs)
    # the international layer is present at the default strictness and absent at 'eda'
    assert any(f['layer'] == 'intl' for f in fs)
    r2 = c.post(f'/api/dossiers/{did}/review', json={'strictness': 'eda'}).json()
    assert not any(f['layer'] == 'intl' for f in r2['findings'])
    assert r2['run']['previous_run_id'] == run['id'] and set(r2['run']['diff']) == {'closed', 'new', 'still_open'}
    assert len(c.get(f'/api/dossiers/{did}/review').json()['runs']) == 2


def test_response_cycle_reassess_and_override(seeded):
    c, did = seeded
    r = c.post(f'/api/dossiers/{did}/review', json={}).json()
    run, q = r['run'], {f['question_id']: f for f in r['findings']}
    rid, f = run['id'], q['QM-P54-01']
    assert c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f["id"]}/responses', json={'text': '', 'by': 'mona'}).status_code == 422
    r = c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f["id"]}/responses', json={'text': 'Second batch EX-23-002 added.', 'by': 'mona'})
    assert r.status_code == 201 and r.json()['finding']['status'] == 'answered'
    r = c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f["id"]}/reassess').json()
    assert r['finding']['status'] == 'not_accepted' and r['finding']['verdict'] == 'deficient'          # nothing changed yet
    data = json.loads(json.dumps(DATA))
    data['batches'].append(dict(no='EX-23-002', kind='fpp', size='120000', scale='pilot', date='2025-03-01', site='Cairo'))
    data['results']['EX-23-002'] = dict(data['results']['EX-23-001'])
    c.put(f'/api/dossiers/{did}/data', json=data)
    r = c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f["id"]}/reassess').json()
    assert r['finding']['status'] == 'accepted' and r['finding']['verdict'] == 'adequate'
    assert r['finding']['responses'][-1]['result'] == 'accepted'
    # override needs a reason and lands in the audit log
    f2 = q['QM-P35-01']
    assert c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f2["id"]}', json={'action': 'override', 'verdict': 'adequate', 'by': 'karim'}).status_code == 422
    r = c.post(f'/api/dossiers/{did}/review/{rid}/findings/{f2["id"]}', json={'action': 'override', 'verdict': 'adequate', 'reason': 'validation in annex', 'by': 'karim'}).json()
    assert r['finding']['origin'] == 'human' and r['finding']['override']['reason'] == 'validation in annex'
    events = [a['event'] for a in c.get(f'/api/dossiers/{did}/audit').json()]
    assert 'review.run' in events and 'review.finding.override' in events and 'review.finding.reassessed' in events


def test_letter_report_sign_off_and_ai(seeded):
    c, did = seeded
    r = c.post(f'/api/dossiers/{did}/review', json={}).json()
    rid = r['run']['id']
    assert c.get(f'/api/dossiers/{did}/review/{rid}/letters/quality/file').status_code == 404
    m = c.post(f'/api/dossiers/{did}/review/{rid}/letters/quality').json()
    assert m['docx'] and m['items'] > 5
    d = c.get(f'/api/dossiers/{did}/review/{rid}/letters/quality/file?fmt=docx')
    assert d.status_code == 200 and d.content[:2] == b'PK' and 'attachment' in d.headers['content-disposition']
    p = c.get(f'/api/dossiers/{did}/review/{rid}/letters/quality/file?fmt=pdf')
    assert p.status_code == 200 and p.content[:5] == b'%PDF-'
    assert c.post(f'/api/dossiers/{did}/review/{rid}/reports/quality').status_code == 201
    # second assessor must be a different person
    assert c.post(f'/api/dossiers/{did}/review/{rid}/sign', json={'role': 'assessor', 'by': 'mona'}).status_code == 200
    assert c.post(f'/api/dossiers/{did}/review/{rid}/sign', json={'role': 'peer', 'by': 'mona'}).status_code == 422
    run = c.post(f'/api/dossiers/{did}/review/{rid}/sign', json={'role': 'peer', 'by': 'karim'}).json()['run']
    assert run['signed']['peer']['by'] == 'karim'
    grevp = [f for f in c.get(f'/api/dossiers/{did}/review/{rid}').json()['findings'] if f['question_id'] == 'IN-GREVP-01'][0]
    assert grevp['verdict'] == 'adequate'
    # AI: prompt carries the section's documents; a suggestion never enters the letter before confirmation
    pr = c.get(f'/api/dossiers/{did}/review/{rid}/ai?dept=quality&ctd=3.2.P.5').json()
    assert 'imp.pdf' in [x['filename'] for x in pr['documents']] and 'Return ONLY a JSON object' in pr['prompt']
    fid = pr['findings'][0]
    ans = {'answers': [{'id': fid, 'verdict': 'deficient', 'finding_en': 'The applicant should provide X.', 'finding_ar': 'يجب تقديم X.',
                        'evidence': [{'doc': 'imp.pdf', 'page': 1, 'excerpt': 'Potential impurities discussed'}, {'doc': 'imp.pdf', 'page': 1, 'excerpt': 'text that is not there'}], 'confidence': 0.8}]}
    r = c.post(f'/api/dossiers/{did}/review/{rid}/ai', json={'answers': ans}).json()
    f = r['findings'][0]
    assert f['payload']['ai']['evidence'][0]['verified'] is True and f['payload']['ai']['evidence'][1]['verified'] is False
    before = c.post(f'/api/dossiers/{did}/review/{rid}/letters/quality').json()['items']
    r = c.post(f'/api/dossiers/{did}/review/{rid}/findings/{fid}', json={'action': 'confirm', 'by': 'mona'}).json()
    assert r['finding']['origin'] == 'ai' and r['finding']['confirmed_by'] == 'mona' and r['finding']['verdict'] == 'deficient'
    assert c.post(f'/api/dossiers/{did}/review/{rid}/ai/server?ids=' + fid).status_code == 501     # no key on this machine
    pack = c.get('/api/review/pack').json()
    assert pack['lint'] == [] and pack['counts']['total'] >= 80 and any(d['id'] == 'cadc' for d in pack['departments'])


def test_reliance_route_abbreviates_and_adds_reliance_questions(seeded):
    c, did = seeded
    r = c.post(f'/api/dossiers/{did}/review', json={'reliance': True}).json()
    fs = r['findings']
    assert any(f['dept'] == 'reliance' for f in fs)
    assert all(f['severity'] != 'critical' or f['payload'].get('abbreviated') is None for f in fs if f['dept'] == 'quality' and not f['question_id'].startswith('MISSING-'))
    assert r['run']['clock']['track'] == 'c2_track_c'
