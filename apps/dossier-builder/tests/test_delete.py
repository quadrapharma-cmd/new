"""Deleting what is no longer wanted: a project goes to the trash and comes back, or is deleted for good with everything it holds;
a product of the product file is deleted with its own documents; the stored files nothing refers to any more leave the disk; the
activity record keeps its lines and says who deleted what. Made-up data («Dermacure»)."""
import io, json, time
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV, PRICE_EN

H = {'X-DB': '1'}


@pytest.fixture()
def ws(tmp_path):
    return tmp_path / 'ws'


@pytest.fixture()
def c(ws):
    return TestClient(create_app(ws))


def new_dossier(c, name='Dermacure'):
    return c.post('/api/dossiers', json=dict(name=name, profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']


def put_doc(c, did, tmp_path, slot='M1-05', text=PRICE_EN, name='pricing.pdf'):
    pdf = make_pdf(tmp_path / name, text.split('\n')[1]).read_bytes()
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, pdf, 'application/pdf')}, data={'meta': json.dumps({'text': text})})
    assert r.status_code == 201, r.text
    return r.json(), pdf


def blobs(ws):
    return {p.name for p in (ws / 'blobs').iterdir() if len(p.name) == 64}


def old(ws):
    """The stored files look older than the guard that protects an upload on its way."""
    import os
    for p in (ws / 'blobs').iterdir():
        os.utime(p, (time.time() - 3600, time.time() - 3600))


def test_a_project_goes_to_the_trash_and_comes_back(c, tmp_path):
    did = new_dossier(c)
    put_doc(c, did, tmp_path)
    r = c.delete(f'/api/dossiers/{did}')
    assert r.status_code == 200 and r.json()['deleted'] is True
    assert c.get('/api/dossiers').json() == []                                              # gone from the list…
    trash = c.get('/api/dossiers?deleted=1').json()
    assert [(d['id'], d['documents']) for d in trash] == [(did, 1)]                         # …and in the trash, with what it holds
    assert c.post(f'/api/dossiers/{did}/restore').json()['deleted'] is False
    assert [d['id'] for d in c.get('/api/dossiers').json()] == [did] and c.get('/api/dossiers?deleted=1').json() == []
    assert len(next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-05')['documents']) == 1   # nothing was lost


def test_deleting_for_good_needs_the_trash_or_the_name(c, tmp_path):
    did = new_dossier(c)
    assert c.delete(f'/api/dossiers/{did}?permanent=1').json()['detail']['code'] == 'E-CONFIRM'             # not by accident
    assert c.delete(f'/api/dossiers/{did}?permanent=1&confirm=Wrong name').status_code == 422
    assert c.delete(f'/api/dossiers/{did}?permanent=1&confirm=Dermacure').status_code == 200                 # its name typed
    assert c.get(f'/api/dossiers/{did}').status_code == 404
    did = new_dossier(c)
    c.delete(f'/api/dossiers/{did}')
    assert c.delete(f'/api/dossiers/{did}?permanent=1').status_code == 200                                  # from the trash: one step
    assert c.delete('/api/dossiers/missing').status_code == 404


def test_deleting_for_good_takes_everything_and_only_what_is_the_projects(c, ws, tmp_path):
    keep = new_dossier(c, 'Dermacure keep')
    gone = new_dossier(c, 'Dermacure gone')
    shared, pdf = put_doc(c, keep, tmp_path)                                                # the same file in both projects
    put_doc(c, gone, tmp_path)
    own, _ = put_doc(c, gone, tmp_path, slot='P-16', text='Stability Study Report\nProduct: Dermacure\nStorage condition: 30 C / 65 % RH', name='stability.pdf')
    c.post(f'/api/dossiers/{gone}/unplaced', files=[('files', ('note.pdf', make_pdf(tmp_path / 'n.pdf', 'A note').read_bytes(), 'application/pdf'))], data={'meta': '{}'})
    (ws / 'exports' / gone).mkdir(parents=True)
    (ws / 'exports' / gone / 'x.zip').write_bytes(b'zip')
    run = c.post(f'/api/dossiers/{gone}/review', json={}, headers=H)                         # a review with findings and an answer to one of them
    assert run.status_code == 201, run.text
    rid, finding = run.json()['run']['id'], run.json()['findings'][0]
    assert c.post(f"/api/dossiers/{gone}/review/{rid}/findings/{finding['id']}/responses", json={'text': 'Answered with the attached certificate.', 'by': 'mona'}, headers=H).status_code == 201
    assert c.post(f"/api/dossiers/{gone}/documents/{own['id']}/review", json={}, headers=H).status_code == 201     # and a review of one document
    before = blobs(ws)
    old(ws)
    r = c.delete(f'/api/dossiers/{gone}?permanent=1&confirm=Dermacure gone')
    assert r.status_code == 200 and r.json()['documents'] >= 3 and r.json()['files_removed'] >= 1, r.text
    assert not (ws / 'exports' / gone).exists()
    after = blobs(ws)
    assert shared['sha256'] in after and own['sha256'] not in after and len(after) < len(before)             # the shared file stays, the project's own is gone
    assert c.get(f"/api/dossiers/{keep}/documents/{shared['id']}/file").content == pdf                       # the other project is untouched
    import sqlite3
    db = sqlite3.connect(ws / 'workspace.sqlite')
    for (t,) in db.execute("select name from sqlite_master where type='table'").fetchall():
        cols = [x[1] for x in db.execute(f'pragma table_info("{t}")')]
        if 'dossier_id' in cols and t != 'audit':
            assert db.execute(f'select count(*) from "{t}" where dossier_id=?', (gone,)).fetchone()[0] == 0, t
    assert db.execute('select count(*) from review_response where run_id=?', (rid,)).fetchone()[0] == 0     # the table that hangs off a review, not off the project
    assert db.execute('select count(*) from review_run').fetchone()[0] == 0 and db.execute('select count(*) from doc_review').fetchone()[0] == 0
    events = [json.loads(d) | {'event': e} for e, d in db.execute("select event, detail from audit where event='dossier.deleted'")]
    assert events and events[-1]['name'] == 'Dermacure gone' and events[-1]['id'] == gone                    # the record says what was deleted
    assert db.execute('select count(*) from audit where dossier_id=?', (gone,)).fetchone()[0] > 0            # and keeps the project's own lines (append-only)
    assert c.get(f'/api/dossiers/{keep}/audit/verify').status_code in (200, 404)


def test_a_file_just_stored_is_not_cleared_under_an_upload(c, ws, tmp_path):
    did = new_dossier(c)
    doc, _ = put_doc(c, did, tmp_path)
    c.delete(f'/api/dossiers/{did}?permanent=1&confirm=Dermacure')
    assert doc['sha256'] in blobs(ws)                                                       # younger than the guard: left for the next clean-up
    old(ws)
    from dossier_engine.app.store import Store
    assert Store(ws).gc_blobs()['files'] >= 1 and doc['sha256'] not in blobs(ws)


def test_a_product_is_deleted_with_its_own_documents_only(c, tmp_path):
    pdf = make_pdf(tmp_path / 'd.pdf', 'certificate').read_bytes()
    sup = c.post('/api/suite/parties', json={'name': 'Supplier Co', 'kind': 'manufacturer'}).json()
    a = c.post('/api/suite/products', json={'name': 'Dermacure A'}).json()
    b = c.post('/api/suite/products', json={'name': 'Dermacure B'}).json()
    c.post(f"/api/suite/products/{a['id']}/parties", json={'party_id': sup['id'], 'role': 'api_supplier', 'api_name': 'Glycine'})
    post = lambda meta: c.post('/api/suite/documents', data={'meta': json.dumps(meta)}, files={'file': ('cert.pdf', io.BytesIO(pdf), 'application/pdf')}).json()
    own = post({'doc_type': 'pricing_certificate', 'products': [a['id']]})
    both = post({'doc_type': 'registration_licence', 'products': [a['id'], b['id']]})
    party = post({'doc_type': 'gmp_certificate', 'parties': [sup['id']]})
    r = c.delete(f"/api/suite/products/{a['id']}")
    assert r.status_code == 200 and r.json()['documents'] == 1, r.text
    assert c.get(f"/api/suite/products/{a['id']}").status_code == 404
    left = {d['id'] for d in c.get('/api/suite/documents').json()}
    assert own['id'] not in left and both['id'] in left and party['id'] in left             # what other products and parties use stays
    assert c.get(f"/api/suite/products/{b['id']}").status_code == 200 and c.get('/api/suite/parties').json()
    assert c.delete(f"/api/suite/documents/{both['id']}").status_code == 200 and both['id'] not in {d['id'] for d in c.get('/api/suite/documents').json()}
    assert c.delete('/api/suite/products/missing').status_code == 404


def test_the_assistant_and_viewers_do_not_delete(ws, monkeypatch):
    app = create_app(ws)
    c = TestClient(app)
    did = new_dossier(c)
    app.state.internal_token = 'tok'
    as_assistant = {'x-db-internal': 'tok', 'x-db-actor': 'claude'}
    assert c.delete(f'/api/dossiers/{did}', headers=as_assistant).json()['detail']['code'] == 'E-ROLE'
    assert c.delete(f'/api/dossiers/{did}?permanent=1&confirm=Dermacure', headers=as_assistant).status_code == 403
    p = c.post('/api/suite/products', json={'name': 'Dermacure A'}).json()
    assert c.delete(f"/api/suite/products/{p['id']}", headers=as_assistant).status_code == 403
    assert [d['id'] for d in c.get('/api/dossiers').json()] == [did]


def test_with_sign_in_an_editor_trashes_and_only_an_administrator_deletes_for_good(ws, monkeypatch):
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PASSWORD', 'correct horse battery')
    app = create_app(ws, auth_enabled=True)
    admin = TestClient(app)
    assert admin.post('/api/login', json={'username': 'admin', 'password': 'correct horse battery'}).status_code == 200
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}, headers=H).status_code == 201
    did = admin.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV), headers=H).json()['id']
    sara = TestClient(app)
    assert sara.post('/api/login', json={'username': 'sara', 'password': 'editor password 1'}).status_code == 200
    assert sara.delete(f'/api/dossiers/{did}?permanent=1&confirm=Dermacure', headers=H).json()['detail']['code'] == 'E-ROLE'
    assert sara.delete(f'/api/dossiers/{did}', headers=H).status_code == 200                # the trash is hers to use
    assert sara.delete(f'/api/dossiers/{did}?permanent=1', headers=H).status_code == 403
    assert admin.delete(f'/api/dossiers/{did}?permanent=1', headers=H).status_code == 200


# ---------------- a project that was started and left: its draft stays, a deleted draft stays deleted
def test_a_draft_stays_until_it_is_deleted_and_never_comes_back(c, ws, tmp_path):
    pdf = make_pdf(tmp_path / 'p.pdf', 'A scanned page of the leaflet').read_bytes()
    other = make_pdf(tmp_path / 'o.pdf', 'Stability Study Report').read_bytes()
    did = new_dossier(c)
    kept, _ = put_doc(c, did, tmp_path)                                                    # a project's own file with the same content as a draft file
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0, 'd': {'name': 'Dermacure 2 % cream'}}}, headers=H).json()['id']
    same = (tmp_path / 'pricing.pdf').read_bytes()
    for name, data in (('pricing.pdf', same), ('stability.pdf', other), ('scan.pdf', pdf)):
        assert c.post(f'/api/intake/drafts/{dr}/files', files={'file': (name, io.BytesIO(data), 'application/pdf')}, data={'kind': 'other'}, headers=H).status_code == 201
    listed = c.get('/api/intake/drafts').json()
    assert [(x['id'], x['files'], x['state']['d']['name']) for x in listed] == [(dr, 3, 'Dermacure 2 % cream')]       # what the projects list shows
    before = blobs(ws)
    old(ws)
    r = c.delete(f'/api/intake/drafts/{dr}?free=1', headers=H).json()
    assert r['ok'] and r['files_removed'] == 2                                             # its own two files left the disk…
    assert kept['sha256'] in blobs(ws) and len(before - blobs(ws)) == 2                    # …the one a project uses stayed
    assert c.get('/api/intake/drafts').json() == []
    # a save or an upload that arrives late (another tab, a slow connection) does not bring the draft back
    assert c.put(f'/api/intake/drafts/{dr}', json={'state': {'step': 1}}, headers=H).status_code == 404
    assert c.post(f'/api/intake/drafts/{dr}/files', files={'file': ('late.pdf', io.BytesIO(pdf), 'application/pdf')}, data={'kind': 'other'}, headers=H).status_code == 404
    assert c.get('/api/intake/drafts').json() == [] and c.delete(f'/api/intake/drafts/{dr}', headers=H).json()['ok']


def test_a_draft_that_became_a_project_needs_no_clean_up(c, ws, tmp_path):
    pdf = make_pdf(tmp_path / 'p.pdf', 'Pricing Certificate').read_bytes()
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0}}, headers=H).json()['id']
    c.post(f'/api/intake/drafts/{dr}/files', files={'file': ('pricing.pdf', io.BytesIO(pdf), 'application/pdf')}, data={'kind': 'other'}, headers=H)
    old(ws)
    n = len(blobs(ws))
    assert c.delete(f'/api/intake/drafts/{dr}', headers=H).json() == {'ok': True, 'files_removed': 0}       # the plain delete (the wizard, once the project exists)
    assert len(blobs(ws)) == n
