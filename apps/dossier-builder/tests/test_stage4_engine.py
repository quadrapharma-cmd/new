"""eBOX stage 4, the engine: station 8 validates the package before it is downloaded at station 9, so each build keeps a record of
what went into it (build.json: the documents of the active items with their files' digests and what the writers read from them, the
product, the envelope, the profile, the sequences recorded) and GET /builds says, for the last build for submission and the last
working copy, whether the dossier still holds what went into it — and if not, what changed —, with the rules of its validation:
those failed and warned in full, each with its provenance (official: ICH, the EMA in force, the SFDA's GCC Module 1; or one of the
provisional Egyptian kinds: an EDA draft, taken from the EU's criteria, an assumption — EG-PROVISIONAL-PROFILE-v0 README §2) and
the documents its failures name. The suite's letters of the authority are listed by dossier («ما بعد التقديم»).
Made-up data only."""
import io, json, shutil
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_api import new, up
from test_lifecycle_api import fill_all

SOFFICE = pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (tracking table)')


@pytest.fixture
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws'))


def slot_of(c, did, sid):
    return next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == sid)


@SOFFICE
def test_a_build_keeps_what_went_into_it_and_says_what_changed_after(c, tmp_path):
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    assert c.get(f'/api/dossiers/{did}/builds').json() == {'submission': None, 'working': None}
    fill_all(c, did, pdf)
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True})
    assert r.status_code == 201, r.text
    b = c.get(f'/api/dossiers/{did}/builds').json()['submission']
    assert b['id'] == r.json()['id'] and b['current'] is True and b['changed'] == [] and not b['working']
    assert b['downloads'] == r.json()['downloads'] and b['sequences']['ectd32']['sequence'] == '0000'
    assert set(b['rules']) == {'eCTD 3.2.2', 'eCTD 4.0'}
    r32 = b['rules']['eCTD 3.2.2']
    assert r32['ok'] and r32['counts']['fail'] == 0 and r32['problems'] == []
    assert sum(r32['counts'].values()) == len(r32['others'])                     # every rule there, passed and not run listed short
    assert {x['kind'] for x in r32['others']} == {'draft'}                        # Egypt's 3.2.2 rules: all provisional
    assert {x['of'] for x in r32['others']} <= {'eda_draft', 'eu_derived', 'assumption'}
    r40 = b['rules']['eCTD 4.0']
    assert {'official', 'draft'} <= {x['kind'] for x in r40['others'] + r40['problems']}     # ICH's rules beside EDA's drafts
    # marked as submitted: still what was validated
    assert c.post(f'/api/dossiers/{did}/submissions/ectd32/0000/submitted', data={'meta': json.dumps({'submitted': '2026-11-17'})}).status_code == 200
    assert c.get(f'/api/dossiers/{did}/builds').json()['submission']['current'] is True
    # a new version of a document: no longer what was validated, and said
    old = slot_of(c, did, 'M1-31')['documents'][0]['id']
    pdf2 = make_pdf(tmp_path / 'd2.pdf', 'composition v2').read_bytes()
    assert c.post(f'/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('comp-v2.pdf', io.BytesIO(pdf2), 'application/pdf')},
                  data={'meta': '{}', 'replaces': old}).status_code == 201
    b = c.get(f'/api/dossiers/{did}/builds').json()['submission']
    assert b['current'] is False and {'kind': 'replaced', 'slot_id': 'M1-31', 'name': 'comp-v2.pdf'} in b['changed']
    # the product's data changed too: said as such
    d = c.get(f'/api/dossiers/{did}').json()
    assert c.put(f'/api/dossiers/{did}/indication', json={'indication': 'Made-up indication for a test'}).status_code in (200, 204)
    kinds = {x['kind'] for x in c.get(f'/api/dossiers/{did}/builds').json()['submission']['changed']}
    assert {'replaced', 'product'} <= kinds, kinds
    assert d['product'] != c.get(f'/api/dossiers/{did}').json()['product']


@SOFFICE
def test_withdrawing_the_sequence_of_a_build_makes_it_out_of_date(c, tmp_path):
    did = new(c)
    fill_all(c, did, make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes())
    assert c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True}).status_code == 201
    assert c.delete(f'/api/dossiers/{did}/submissions/ectd32/0000').status_code == 200
    b = c.get(f'/api/dossiers/{did}/builds').json()['submission']
    assert b['current'] is False and {'kind': 'sequences'} in b['changed']


def test_a_working_copy_is_recorded_and_a_failed_rule_names_its_document(c, tmp_path):
    """A PDF with a security restriction (EG-PF-16.3, an EDA draft's rule) in a working copy: the rule fails, says it is a draft's,
    and names the very document — the way back to it."""
    from pypdf import PdfWriter
    did = new(c)
    w = PdfWriter(clone_from=str(make_pdf(tmp_path / 's.pdf', 'Restricted made-up letter')))
    w.encrypt(user_password='', owner_password='owner', permissions_flag=0)
    p = tmp_path / 'restricted.pdf'
    with open(p, 'wb') as fh:
        w.write(fh)
    doc = up(c, did, 'M1-11', p.read_bytes()).json()
    up(c, did, 'M1-31', make_pdf(tmp_path / 'c.pdf', 'Composition').read_bytes())
    r = c.post(f'/api/dossiers/{did}/export', json={'working': True, 'outputs': ['ctd']})
    assert r.status_code == 201, r.text
    bs = c.get(f'/api/dossiers/{did}/builds').json()
    assert bs['submission'] is None
    b = bs['working']
    assert b['working'] is True and b['current'] is True and b['id'] == r.json()['id'] and b['missing_required'] > 0
    rules = b['rules']['eCTD 3.2.2']
    sec = next(x for x in rules['problems'] if x['rule'] == 'EG-PF-16.3')
    assert sec['status'] == 'fail' and sec['kind'] == 'draft' and sec['of'] == 'eda_draft' and sec['provenance'] == 'EG-DRAFT'
    assert [x['doc_id'] for x in sec['documents']] == [doc['id']] and sec['documents'][0]['slot_id'] == 'M1-11'
    assert rules['problems'][0]['status'] == 'fail'                               # the failed first, then the warned
    # nothing changed: still current; a document added: out of date, and said
    up(c, did, 'M1-05', make_pdf(tmp_path / 'p.pdf', 'Pricing').read_bytes())
    b = c.get(f'/api/dossiers/{did}/builds').json()['working']
    assert b['current'] is False and [x['kind'] for x in b['changed']] == ['added'] and b['changed'][0]['slot_id'] == 'M1-05'


def test_a_build_made_before_its_record_says_so(c, tmp_path):
    did = new(c)
    up(c, did, 'M1-31', make_pdf(tmp_path / 'c.pdf', 'Composition').read_bytes())
    r = c.post(f'/api/dossiers/{did}/export', json={'working': True, 'outputs': ['ctd']}).json()
    (tmp_path / 'ws' / 'exports' / did / r['id'] / 'build.json').unlink()        # as an export of version 54 and before
    b = c.get(f'/api/dossiers/{did}/builds').json()['working']
    assert b == {'id': r['id'], 'created': b['created'], 'legacy': True, 'working': True, 'current': False}


def test_the_authoritys_letters_are_listed_by_dossier(c, tmp_path):
    a, b = new(c), new(c)
    for did, subject in ((a, 'Comments on the made-up dossier A'), (b, 'Comments on the made-up dossier B')):
        r = c.post('/api/suite/letters', data={'meta': json.dumps({'subject': subject, 'dossier_id': did, 'received': '2026-11-17'})})
        assert r.status_code == 201, r.text
    got = c.get('/api/suite/letters', params={'dossier': a}).json()
    assert [x['subject'] for x in got] == ['Comments on the made-up dossier A'] and got[0]['dossier_id'] == a
    assert len(c.get('/api/suite/letters').json()) == 2                           # unfiltered: all of them, as before
