"""Users and user management on a local install: sign-in is off until the owner turns it on from the Users screen (the first
administrator), accounts with roles, password resets, deletion, the switch off again with the accounts kept; the cloud edition
keeps sign-in always on; the browser edition has no accounts."""
import json, os, stat
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}


@pytest.fixture()
def local(tmp_path, monkeypatch):
    monkeypatch.delenv('DB_MODE', raising=False)
    monkeypatch.delenv('DB_AUTH', raising=False)
    monkeypatch.delenv('DB_ADMIN_USER', raising=False)
    monkeypatch.delenv('DB_ADMIN_PASSWORD', raising=False)
    return tmp_path / 'ws'


def enable(c, user='haytham', pw='first admin password'):
    return c.post('/api/auth/enable', json={'username': user, 'password': pw}, headers=H)


def test_off_by_default_then_the_first_admin_turns_it_on(local):
    c = TestClient(create_app(local))
    assert c.get('/api/auth').json() == {'enabled': False, 'forced': False, 'switchable': True, 'users': 0, 'can_enable': True, 'can_disable': False}
    assert c.get('/api/dossiers').status_code == 200                                   # open: one person on one computer
    assert c.get('/api/me').json() == {'user': None, 'auth': False, 'role': 'admin'}
    assert enable(c, pw='short').json()['detail']['code'] == 'E-USER'
    assert enable(c, user='bad name!').json()['detail']['code'] == 'E-USER'
    r = enable(c)
    assert r.status_code == 201 and r.json()['created'] is True and 'dbsess=' in r.headers['set-cookie']
    assert c.get('/api/me').json() == {'user': 'haytham', 'auth': True, 'role': 'admin'}     # signed in at once
    assert json.loads((local / 'auth.json').read_text()) == {'enabled': True}
    assert stat.S_IMODE(os.stat(local / 'auth.json').st_mode) == 0o600
    assert c.get('/api/auth').json()['users'] == 1 and 'haytham' not in c.get('/api/auth').text   # counts only, no names
    assert enable(c).json()['detail']['code'] == 'E-AUTH-ON'

    # the switch is persisted: a fresh start of the program asks for sign-in
    c2 = TestClient(create_app(local))
    assert c2.get('/api/dossiers').status_code == 401
    assert c2.get('/', follow_redirects=False).status_code == 303
    assert c2.get('/api/auth').json()['enabled'] is True                                  # the state itself is open
    assert c2.post('/api/auth/enable', json={'username': 'x', 'password': 'y' * 12}, headers=H).status_code == 401
    assert c2.post('/api/login', json={'username': 'haytham', 'password': 'first admin password'}).status_code == 200
    me = c2.get('/api/me').json()
    assert me['role'] == 'admin'
    users = c2.get('/api/users').json()
    assert users[0]['username'] == 'haytham' and users[0]['last_login']                    # last sign-in recorded


def test_manage_users(local):
    app = create_app(local)
    admin = TestClient(app)
    assert enable(admin).status_code == 201
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}).status_code == 403   # CSRF header
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}, headers=H).status_code == 201
    assert admin.post('/api/users', json={'username': 'omar', 'password': 'viewer password 1', 'role': 'viewer'}, headers=H).status_code == 201
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'another password', 'role': 'editor'}, headers=H).json()['detail']['code'] == 'E-DUP'
    listed = {u['username']: u for u in admin.get('/api/users').json()}
    assert set(listed) == {'haytham', 'sara', 'omar'} and listed['sara']['last_login'] is None and listed['sara']['role'] == 'editor'

    sara = TestClient(app)
    assert sara.post('/api/login', json={'username': 'sara', 'password': 'editor password 1'}).status_code == 200
    assert sara.get('/api/users').status_code == 403                                      # editors do not manage users
    assert sara.post('/api/auth/disable', headers=H).status_code == 403                   # nor the switch
    assert sara.put('/api/assistant/settings', json={'api_key': 'sk-ant-x'}, headers=H).status_code == 403    # nor the keys
    assert sara.put('/api/drive/settings', json={'api_key': 'AIza'}, headers=H).status_code == 403
    assert sara.get('/api/assistant/settings').status_code == 200                          # reading the state is fine
    assert sara.post('/api/me/password', json={'old': 'editor password 1', 'new': 'editor password 2'}, headers=H).status_code == 200

    omar = TestClient(app)
    assert omar.post('/api/login', json={'username': 'omar', 'password': 'viewer password 1'}).status_code == 200
    assert omar.get('/api/dossiers').status_code == 200
    assert omar.post('/api/dossiers', json={}, headers=H).json()['detail']['code'] == 'E-ROLE'    # view only
    assert omar.post('/api/me/password', json={'old': 'viewer password 1', 'new': 'viewer password 2'}, headers=H).status_code == 200

    # role change, password reset, delete rules
    assert admin.put('/api/users/sara', json={'role': 'viewer'}, headers=H).status_code == 200
    assert admin.put('/api/users/sara', json={'password': 'reset by admin 1'}, headers=H).status_code == 200
    s2 = TestClient(app)
    assert s2.post('/api/login', json={'username': 'sara', 'password': 'editor password 2'}).status_code == 401
    assert s2.post('/api/login', json={'username': 'sara', 'password': 'reset by admin 1'}).status_code == 200
    assert s2.post('/api/dossiers', json={}, headers=H).json()['detail']['code'] == 'E-ROLE'      # now a viewer
    assert admin.put('/api/users/omar', json={'role': 'disabled'}, headers=H).status_code == 200
    assert omar.get('/api/dossiers').status_code == 401                                   # a disabled account is signed out at once
    assert admin.put('/api/users/nobody', json={'role': 'viewer'}, headers=H).status_code == 404
    assert admin.delete('/api/users/haytham', headers=H).json()['detail']['code'] == 'E-SELF'
    assert admin.delete('/api/users/nobody', headers=H).json()['detail']['code'] == 'E-USER'
    assert admin.delete('/api/users/omar', headers=H).status_code == 200
    assert admin.put('/api/users/haytham', json={'role': 'editor'}, headers=H).json()['detail']['code'] == 'E-USER'   # keep one admin
    assert admin.post('/api/users', json={'username': 'nour', 'password': 'second admin pw', 'role': 'admin'}, headers=H).status_code == 201
    nour = TestClient(app)
    assert nour.post('/api/login', json={'username': 'nour', 'password': 'second admin pw'}).status_code == 200
    assert nour.delete('/api/users/haytham', headers=H).status_code == 200                # two admins: the other may go
    assert nour.delete('/api/users/nour', headers=H).json()['detail']['code'] == 'E-SELF'
    assert nour.put('/api/users/nour', json={'role': 'viewer'}, headers=H).json()['detail']['code'] == 'E-USER'   # last admin stays admin
    assert {u['username'] for u in nour.get('/api/users').json()} == {'sara', 'nour'}
    assert admin.get('/api/dossiers').status_code == 401                                  # the deleted admin's session is dead


def test_turn_sign_in_off_and_on_again_keeps_the_accounts(local):
    app = create_app(local)
    admin = TestClient(app)
    assert enable(admin).status_code == 201
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}, headers=H).status_code == 201
    r = admin.post('/api/auth/disable', headers=H)
    assert r.status_code == 200 and 'dbsess=' in r.headers['set-cookie']                   # cookie cleared
    assert admin.get('/api/auth').json() == {'enabled': False, 'forced': False, 'switchable': True, 'users': 2, 'can_enable': True, 'can_disable': False}
    assert json.loads((local / 'auth.json').read_text()) == {'enabled': False}
    anyone = TestClient(create_app(local))
    assert anyone.get('/api/dossiers').status_code == 200 and anyone.get('/api/me').json()['auth'] is False
    # on again: with accounts in place only an existing administrator can do it (no new accounts, no password resets by surprise)
    assert anyone.post('/api/auth/enable', json={'username': 'newadmin', 'password': 'brand new password'}, headers=H).json()['detail']['code'] == 'E-LOGIN'
    assert anyone.post('/api/auth/enable', json={'username': 'sara', 'password': 'editor password 1'}, headers=H).status_code == 403   # an editor cannot
    assert anyone.post('/api/auth/enable', json={'username': 'haytham', 'password': 'wrong wrong wrong'}, headers=H).status_code == 403   # 403, not 401: the page must not bounce to /login
    for _ in range(4):                                                                     # 5 misses for this name
        anyone.post('/api/auth/enable', json={'username': 'haytham', 'password': 'wrong wrong wrong'}, headers=H)
    assert anyone.post('/api/auth/enable', json={'username': 'haytham', 'password': 'first admin password'}, headers=H).status_code == 429   # 5 misses: 15 minutes, even with the right password
    anyone = TestClient(create_app(local))                                                  # a fresh process: the counter is in memory
    r = anyone.post('/api/auth/enable', json={'username': 'haytham', 'password': 'first admin password'}, headers=H)
    assert r.status_code == 200 and r.json()['created'] is False
    assert anyone.get('/api/me').json()['user'] == 'haytham' and anyone.get('/api/auth').json()['users'] == 2
    assert TestClient(create_app(local)).get('/api/dossiers').status_code == 401


def test_a_switch_without_an_administrator_stays_open(local):
    local.mkdir()
    (local / 'auth.json').write_text('{"enabled": true}')                                  # on, but nobody could sign in
    c = TestClient(create_app(local))
    assert c.get('/api/auth').json()['enabled'] is False and c.get('/api/dossiers').status_code == 200
    (local / 'auth.json').write_text('not json')                                           # a damaged switch file = off
    assert TestClient(create_app(local)).get('/api/dossiers').status_code == 200


def test_cloud_edition_is_always_on(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PASSWORD', 'correct horse battery')
    monkeypatch.setenv('DB_AUTH', '1')
    c = TestClient(create_app(tmp_path / 'ws'))                                            # the environment forces it on
    assert c.get('/api/auth').json() == {'enabled': True, 'forced': True, 'switchable': False, 'users': 1, 'can_enable': False, 'can_disable': False}
    assert c.post('/api/login', json={'username': 'admin', 'password': 'correct horse battery'}).status_code == 200
    assert c.post('/api/auth/disable', headers=H).json()['detail']['code'] == 'E-AUTH-FORCED'
    assert c.delete('/api/users/admin', headers=H).json()['detail']['code'] == 'E-SELF'
    assert c.get('/api/users').json()[0]['username'] == 'admin'


def test_browser_edition_has_no_accounts(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    assert c.get('/api/auth').json()['switchable'] is False and c.get('/api/auth').json()['can_enable'] is False
    assert c.post('/api/auth/enable', json={'username': 'a', 'password': 'b' * 12}, headers=H).json()['detail']['code'] == 'E-AUTH-FIXED'


def test_auth_events_in_the_audit_trail(local):
    admin = TestClient(create_app(local))
    assert enable(admin).status_code == 201
    assert admin.post('/api/users', json={'username': 'sara', 'password': 'editor password 1', 'role': 'editor'}, headers=H).status_code == 201
    assert admin.delete('/api/users/sara', headers=H).status_code == 200
    assert admin.post('/api/auth/disable', headers=H).status_code == 200
    import sqlite3
    db = sqlite3.connect(local / 'workspace.sqlite')
    rows = db.execute("select event, actor from audit where event like 'auth.%' or event like 'user.%' order by id").fetchall()
    assert [r[0] for r in rows] == ['auth.enabled', 'user.added', 'user.added', 'user.removed', 'auth.disabled']
    assert {r[1] for r in rows} == {'haytham'}                                             # every step signed by who did it
