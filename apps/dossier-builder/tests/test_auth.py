"""Cloud mode: everything behind login; CSRF header; brute-force limit; security headers. Local mode unchanged."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from test_api import PROFILE, PRODUCT, ENV


@pytest.fixture()
def cloud(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_ADMIN_USER', 'admin')
    monkeypatch.setenv('DB_ADMIN_PASSWORD', 'correct horse battery')
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=True))


def login(c, pw='correct horse battery'):
    return c.post('/api/login', json={'username': 'admin', 'password': pw})


def test_everything_needs_login(cloud):
    assert cloud.get('/api/dossiers').status_code == 401
    r = cloud.get('/', follow_redirects=False)
    assert r.status_code == 303 and r.headers['location'] == '/login'
    assert cloud.get('/login').status_code == 200 and 'Sign in' in cloud.get('/login').text
    assert cloud.get('/api/health').status_code == 200


def test_login_then_use(cloud):
    assert login(cloud, 'wrong password!').status_code == 401
    r = login(cloud)
    assert r.status_code == 200 and 'httponly' in r.headers['set-cookie'].lower() and 'samesite=strict' in r.headers['set-cookie'].lower()
    assert cloud.get('/api/dossiers').status_code == 200
    body = dict(name='X', profile=PROFILE, product=PRODUCT, envelope=ENV)
    assert cloud.post('/api/dossiers', json=body).status_code == 403                       # no CSRF header
    assert cloud.post('/api/dossiers', json=body, headers={'X-DB': '1'}).status_code == 201
    assert cloud.get('/api/me').json()['user'] == 'admin'


def test_tampered_cookie_rejected(cloud):
    login(cloud)
    tok = cloud.cookies.get('dbsess')
    cloud.cookies.set('dbsess', tok[:-2] + ('00' if tok[-2:] != '00' else '11'))
    assert cloud.get('/api/dossiers').status_code == 401


def test_brute_force_limit(cloud):
    for _ in range(5):
        assert login(cloud, 'nope nope nope').status_code == 401
    assert login(cloud).status_code == 429                                                  # even the right password, for 15 min


def test_security_headers(cloud):
    h = cloud.get('/login').headers
    assert h['x-frame-options'] == 'DENY' and h['x-content-type-options'] == 'nosniff' and "frame-ancestors 'none'" in h['content-security-policy']


def test_password_rules_and_users_file_private(tmp_path):
    import os, stat
    from dossier_engine.app.auth import Auth
    a = Auth(tmp_path, True)
    with pytest.raises(ValueError):
        a.add_user('u', 'short')
    a.add_user('u', 'long enough pw')
    assert a.check('u', 'long enough pw') and not a.check('u', 'long enough pX') and not a.check('nobody', 'x' * 12)
    assert stat.S_IMODE(os.stat(tmp_path / 'users.json').st_mode) == 0o600
    assert 'long enough pw' not in (tmp_path / 'users.json').read_text()


def test_local_mode_has_no_login(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    assert c.get('/api/dossiers').status_code == 200
