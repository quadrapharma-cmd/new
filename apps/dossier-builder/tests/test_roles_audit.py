"""Company install: roles (admin / editor / viewer / disabled), user management, and an append-only,
hash-chained activity log that records who did what."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PASSWORD', 'correct horse battery')
    monkeypatch.setenv('DB_HOME', 'suite')
    return create_app(tmp_path / 'ws', auth_enabled=True), tmp_path / 'ws'


def client(app, user, pw):
    c = TestClient(app)
    assert c.post('/api/login', json={'username': user, 'password': pw}).status_code == 200
    return c


def test_roles_and_user_admin(app):
    a, ws = app
    admin = client(a, 'admin', 'correct horse battery')
    assert admin.get('/api/me').json()['role'] == 'admin'
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}, headers=H).status_code == 201
    assert admin.post('/api/users', json={'username': 'omar', 'password': 'viewer password 1', 'role': 'viewer'}, headers=H).status_code == 201
    assert admin.post('/api/users', json={'username': 'x', 'password': 'short'}, headers=H).json()['detail']['code'] == 'E-USER'
    assert admin.put('/api/users/admin', json={'role': 'viewer'}, headers=H).json()['detail']['code'] == 'E-USER'   # last admin

    sara = client(a, 'sara', 'editor password 1')
    assert sara.post('/api/suite/parties', json={'name': 'Badr'}, headers=H).status_code == 201
    assert sara.get('/api/users').status_code == 403                                   # admin only

    omar = client(a, 'omar', 'viewer password 1')
    assert omar.get('/api/suite/parties').status_code == 200
    r = omar.post('/api/suite/parties', json={'name': 'X'}, headers=H)
    assert r.status_code == 403 and r.json()['detail']['code'] == 'E-ROLE' and r.json()['detail']['ar']
    assert omar.post('/api/me/password', json={'old': 'viewer password 1', 'new': 'viewer password 2'}, headers=H).status_code == 200

    assert admin.put('/api/users/sara', json={'role': 'disabled'}, headers=H).status_code == 200
    assert sara.get('/api/suite/parties').status_code == 401                           # session ends at once
    assert TestClient(a).post('/api/login', json={'username': 'sara', 'password': 'editor password 1'}).status_code == 401


def test_activity_names_the_actor_and_cannot_be_altered(app):
    a, ws = app
    admin = client(a, 'admin', 'correct horse battery')
    admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1'}, headers=H)
    sara = client(a, 'sara', 'editor password 1')
    sara.post('/api/suite/parties', json={'name': 'Badr'}, headers=H)
    act = admin.get('/api/activity').json()
    assert act['chain_ok'] is True
    rows = {r['event']: r['actor'] for r in act['rows']}
    assert rows['suite.party.added'] == 'sara' and rows['user.added'] == 'admin' and rows['login'] in ('admin', 'sara')
    db = sqlite3.connect(ws / 'workspace.sqlite')
    for sql in ("update audit set actor='someone' where event='suite.party.added'", "delete from audit"):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)
    # bypass the triggers on purpose to prove the chain detects tampering
    db.execute('drop trigger audit_no_update'); db.execute("update audit set actor='someone' where event='suite.party.added'"); db.commit()
    act = admin.get('/api/activity').json()
    assert act['chain_ok'] is False and act['first_bad']


def test_home_opens_product_file_and_migrations_are_recorded(app):
    a, ws = app
    admin = client(a, 'admin', 'correct horse battery')
    r = admin.get('/', follow_redirects=False)
    assert r.status_code == 307 and r.headers['location'] == '/suite/'
    ids = [r[0] for r in sqlite3.connect(ws / 'workspace.sqlite').execute('select id from schema_migrations order by id')]
    assert ids == [1, 2, 3, 4]
    create_app(ws, auth_enabled=True)                    # re-open: idempotent
    assert len(list(sqlite3.connect(ws / 'workspace.sqlite').execute('select id from schema_migrations'))) == 4
