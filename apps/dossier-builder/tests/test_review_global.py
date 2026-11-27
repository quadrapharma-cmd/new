"""The assessor's review for any authority: a dossier going to EDA is reviewed as before (every question, EDA's departments, its
clock); a dossier going to any other authority gets the core questions — those an assessor of any authority asks (an ICH, WHO, EMA,
FDA or pharmacopoeial basis, the common CTD's Modules 2–5) — its own Module 1 items from its requirements pack, the desks named for
any assessor, no simulated clock, and letters that name the authority they simulate. Made-up product and data."""
import io, json
import pytest
from docx import Document
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import packs
from dossier_engine.app.api import create_app
from dossier_engine.review import pack as rpack
from test_review import PROFILE, PRODUCT, ENV, DATA


def test_the_core_is_what_any_assessor_asks():
    p = rpack.load()
    core = [q for q in p.questions if p.scope(q) == 'core']
    common = {r['id'] for r in packs.load('ich.ctd.m4.v1').requirements}
    assert len(core) >= 45 and p.counts()['by_scope'] == {'core': len(core), 'eda': len(p.questions) - len(core)}
    desks = {d['id'] for d in p.departments_for({'id': 'EU'})}
    for q in core:
        assert rpack.INTL.match(q['anchor']['code']), q['id']                                # an international basis
        text = json.dumps([q['title'], q['question'], q['deficiency'], q.get('adequate')], ensure_ascii=False)
        assert not rpack.EG_WORDS.search(text), q['id']                                       # nothing Egyptian in its words
        assert set((q.get('evidence') or {}).get('slots') or []) <= common, q['id']           # only the common CTD's items
        assert q['dept'] in desks and q['dept'] not in rpack.EGYPT_ONLY_Q, q['id']
    by = {q['id']: p.scope(q) for q in p.questions}
    assert by['QM-S32-02'] == 'core' and by['IN-M13A-01'] == 'core'
    assert by['SC-COVER-01'] == 'eda' and by['CD-A2-01'] == 'eda' and by['BE-33'] == 'eda'   # Module 1 desk; EDA's own annexes and sections
    assert len(p.questions_for(None)) == len(p.questions_for({'id': 'EG-EDA'})) == len(p.questions)
    assert [q['id'] for q in p.questions_for({'id': 'US-FDA'})] == [q['id'] for q in core]
    assert {d['id'] for d in p.departments_for(None)} >= {'gates', 'reliance', 'screening'} and not desks & {'gates', 'reliance'}
    assert p.departments_for({'id': 'EU'})[0]['en'] == 'Validation'
    q = dict(next(x for x in p.questions if x['id'] == 'QM-S32-02'), scope='eda')        # an explicit scope in the pack wins
    assert rpack.ReviewPack(p.meta, [q], p.path, p.common).scope(q) == 'eda'


@pytest.fixture()
def eu(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    r = c.post('/api/dossiers', json=dict(name='Examplol 500 mg FCT', country='DE', profile=PROFILE, product=PRODUCT, envelope=ENV))
    assert r.status_code == 201 and r.json()['pack'] == 'eu.ctd.m1.v1', r.text
    did = r.json()['id']

    def up(slot, name, lines, title):
        pdf = make_pdf_lines(tmp_path / name, lines, title)
        r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, io.BytesIO(pdf.read_bytes()), 'application/pdf')}, data={'meta': json.dumps({})})
        assert r.status_code == 201, r.text
    up('P-12', 'imp.pdf', ['Impurities', 'Potential impurities discussed per ICH Q3A. Elemental impurities risk assessment per ICH Q3D attached. Mutagenic impurities assessed per ICH M7. Benzene: not used.'], '3.2.P.5.5')
    up('P-02', 'dev.pdf', ['Pharmaceutical development', 'Reference product: Referenzol 500 mg. QTPP defined. Critical quality attributes (CQA) and critical process parameters (CPP) identified.'], '3.2.P.2')
    up('P-07', 'pv.pdf', ['Process validation', 'Summary of results for one batch only.'], '3.2.P.3.5')
    assert c.put(f'/api/dossiers/{did}/data', json=DATA).status_code == 200
    return c, did


def test_a_dossier_for_the_eu_is_reviewed_with_the_core_and_its_own_module_1(eu):
    c, did = eu
    p = rpack.load()
    core = {q['id'] for q in p.questions if p.scope(q) == 'core'}
    r = c.post(f'/api/dossiers/{did}/review', json={'strictness': 'international', 'actor': 'mona'})
    assert r.status_code == 201, r.text
    run, fs = r.json()['run'], r.json()['findings']
    assert run['options']['authority']['id'] == 'EU' and 'EMA' in run['options']['authority']['name']['en']
    assert not set(run['dept_verdicts']) & {'gates', 'reliance'} and 'quality' in run['dept_verdicts']
    asked = {f['question_id'] for f in fs if not f['question_id'].startswith(('MISSING-', 'TECH-', 'XC-'))}
    assert asked and asked <= core                                                           # no question of EDA's own
    q = {f['question_id']: f for f in fs}
    assert q['QM-S32-02']['verdict'] == 'adequate' and q['QM-P2-01']['verdict'] == 'adequate'
    assert q['QM-P35-01']['verdict'] == 'deficient'                                          # one batch where three are expected
    missing = [f for f in fs if f['question_id'].startswith('MISSING-')]
    board = {s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    assert missing and all(f['slot_id'] in board for f in missing)                          # the EU pack's own items
    assert any(f['dept'] == 'screening' and f['layer'] == 'own' for f in missing)
    assert all('NP.CAPP' not in (f['payload']['source'] or {}).get('code', '') for f in missing)
    assert run['clock']['stages'] == [] and run['clock']['track'] is None and 'not in the program' in run['clock']['label']['en']
    rid = run['id']
    m = c.post(f'/api/dossiers/{did}/review/{rid}/letters/quality').json()
    assert m['docx'] and m['items'] >= 1
    d = c.get(f'/api/dossiers/{did}/review/{rid}/letters/quality/file?fmt=docx')
    text = '\n'.join(x.text for x in Document(io.BytesIO(d.content)).paragraphs)
    assert 'NOT a letter of European Union / EEA' in text and 'ليس خطاباً صادراً عن الاتحاد الأوروبي' in text
    assert 'NOT an EDA letter' not in text and 'Egyptian Drug Authority' not in text and 'Request for supplementary information — Quality' in text
    pk = c.get(f'/api/review/pack?dossier={did}').json()
    assert pk['authority']['id'] == 'EU' and not pk['authority']['egypt'] and pk['counts']['total'] == len(core) and pk['tracks'] == {}
    assert pk['note']['en'].startswith('For an authority other than EDA') and pk['layers']['own']['en'].startswith("The authority's own")
    assert {x['scope'] for x in pk['questions']} == {'core'} and [d['id'] for d in pk['departments']][:2] == ['screening', 'technical']
    ai = c.get(f'/api/dossiers/{did}/review/{rid}/ai', params={'dept': 'quality'}).json()
    assert 'the way European Union / EEA' in ai['prompt'] and 'Egyptian' not in ai['prompt'].split('Answer ONLY')[0]


def test_any_other_country_and_egypt(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    jo = c.post('/api/dossiers', json=dict(name='Examplol', country='JO', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()
    assert jo['pack'] == 'intl.ctd.m1.v1'
    run = c.post(f"/api/dossiers/{jo['id']}/review", json={}).json()['run']
    assert run['options']['authority']['id'] == 'OTHER' and run['clock']['stages'] == []
    m = c.post(f"/api/dossiers/{jo['id']}/review/{run['id']}/letters/screening").json()
    text = '\n'.join(x.text for x in Document(io.BytesIO(c.get(f"/api/dossiers/{jo['id']}/review/{run['id']}/letters/screening/file?fmt=docx").content)).paragraphs)
    assert m['docx'] and 'NOT a letter of the receiving authority' in text
    eg = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()
    run = c.post(f"/api/dossiers/{eg['id']}/review", json={}).json()['run']
    assert run['options']['authority']['id'] == 'EG-EDA' and run['clock']['stages'] and {'gates', 'screening'} <= set(run['dept_verdicts'])
    pk = c.get(f"/api/review/pack?dossier={eg['id']}").json()
    assert pk['authority']['egypt'] and pk['counts']['total'] == len(rpack.load().questions) and pk['note'] is None and pk['tracks']
    assert c.get('/api/review/pack').json()['counts']['total'] == pk['counts']['total']      # no dossier named: EDA's, as before
