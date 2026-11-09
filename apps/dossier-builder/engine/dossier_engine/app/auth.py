"""Authentication for the cloud (hosted) mode — stdlib only.

* Users live in <workspace>/users.json: {username: {salt, hash, role, created}} with scrypt hashes.
  First run: DB_ADMIN_USER + DB_ADMIN_PASSWORD (env) create the admin if no user exists.
* Session: signed cookie (HMAC-SHA256, secret from DB_SECRET or <workspace>/secret.key 0600),
  HttpOnly, SameSite=Strict, Secure when DB_COOKIE_SECURE=1 (behind HTTPS). 12-hour expiry.
* CSRF: state-changing requests must carry the custom header X-DB: 1 (a cross-site page cannot
  send it without CORS, which is not enabled) on top of SameSite=Strict.
* Brute force: 5 failed logins per username+IP in 15 minutes → 429.
"""
import base64, hashlib, hmac, json, os, secrets, threading, time
from pathlib import Path

COOKIE = 'dbsess'
TTL = 12 * 3600


def _scrypt(password, salt):
    return hashlib.scrypt(password.encode('utf-8'), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)


class Auth:
    def __init__(self, workspace, enabled):
        """enabled: True (cloud / forced by the environment), False (never), None (the workspace's switch, auth.json, default off)."""
        self.root = Path(workspace)
        self.root.mkdir(parents=True, exist_ok=True)
        self.switch_file = self.root / 'auth.json'
        self.users_file = self.root / 'users.json'
        self.forced = enabled is True                      # cloud: always on, cannot be switched off
        self.switchable = enabled is None                  # local editions: the Users screen turns it on and off
        if enabled is None:
            try:
                enabled = bool(json.loads(self.switch_file.read_text()).get('enabled')) if self.switch_file.exists() else False
            except (ValueError, OSError):
                enabled = False
            if enabled and not any(u.get('role') == 'admin' for u in self.users().values()):
                enabled = False                            # the switch is on but no administrator could sign in: stay open rather than lock everyone out
        self.enabled = bool(enabled)
        self._fail, self._lock = {}, threading.Lock()
        key = os.environ.get('DB_SECRET')
        kf = self.root / 'secret.key'
        if not key:
            if not kf.exists():
                kf.write_text(secrets.token_hex(32))
                os.chmod(kf, 0o600)
            key = kf.read_text().strip()
        self.key = key.encode()
        self.secure = os.environ.get('DB_COOKIE_SECURE', '0') == '1'
        if enabled and not self.users():
            u, p = os.environ.get('DB_ADMIN_USER'), os.environ.get('DB_ADMIN_PASSWORD')
            if u and p:
                self.add_user(u, p, 'admin')

    # ---- the switch (local editions): on from the Users screen once the first administrator exists
    def set_enabled(self, on):
        self.enabled = bool(on)
        self.switch_file.write_text(json.dumps({'enabled': self.enabled}))
        try:
            os.chmod(self.switch_file, 0o600)
        except OSError:
            pass

    # ---- users
    def users(self):
        return json.loads(self.users_file.read_text()) if self.users_file.exists() else {}

    def remove_user(self, username):
        users = self.users()
        if username not in users:
            raise ValueError('unknown user')
        if users[username].get('role') == 'admin' and sum(1 for u in users.values() if u.get('role') == 'admin') == 1:
            raise ValueError('keep at least one admin')
        del users[username]
        self._save(users)

    def touch_login(self, username):
        users = self.users()
        if username in users:
            users[username]['last_login'] = time.time()
            self._save(users)

    ROLES = ('admin', 'editor', 'viewer', 'disabled')

    def role(self, username):
        r = self.users().get(username, {}).get('role', 'editor')
        return 'editor' if r == 'user' else r            # «user» from the first version = editor

    def add_user(self, username, password, role='editor'):
        if len(password) < 10:
            raise ValueError('password must be at least 10 characters')
        role = 'editor' if role == 'user' else role
        if role not in self.ROLES:
            raise ValueError(f'role must be one of {self.ROLES}')
        if not username or not all(c.isalnum() or c in '._-@' for c in username):
            raise ValueError('username: letters, digits and . _ - @ only')
        users = self.users()
        salt = secrets.token_bytes(16)
        prev = users.get(username, {})
        users[username] = {'salt': salt.hex(), 'hash': _scrypt(password, salt).hex(), 'role': role,
                           'created': prev.get('created', time.time())}
        self._save(users)

    def set_role(self, username, role):
        users = self.users()
        if username not in users or role not in self.ROLES:
            raise ValueError('unknown user or role')
        if users[username].get('role') == 'admin' and role != 'admin' and \
                sum(1 for u in users.values() if u.get('role') == 'admin') == 1:
            raise ValueError('keep at least one admin')
        users[username]['role'] = role
        self._save(users)

    def _save(self, users):
        tmp = self.users_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(users, indent=1))
        os.chmod(tmp, 0o600)
        tmp.replace(self.users_file)

    def check(self, username, password):
        u = self.users().get(username)
        if not u or u.get('role') == 'disabled':
            _scrypt(password, b'0' * 16)          # same cost for unknown users (no user enumeration by timing)
            return False
        return hmac.compare_digest(bytes.fromhex(u['hash']), _scrypt(password, bytes.fromhex(u['salt'])))

    # ---- brute force
    def blocked(self, key):
        now = time.time()
        with self._lock:
            hits = [t for t in self._fail.get(key, []) if now - t < 900]
            self._fail[key] = hits
            return len(hits) >= 5

    def fail(self, key):
        with self._lock:
            self._fail.setdefault(key, []).append(time.time())

    # ---- sessions
    def issue(self, username):
        body = base64.urlsafe_b64encode(json.dumps({'u': username, 'exp': int(time.time()) + TTL}).encode()).decode()
        sig = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return f'{body}.{sig}'

    def verify(self, token):
        try:
            body, sig = token.rsplit('.', 1)
            if not hmac.compare_digest(sig, hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()):
                return None
            data = json.loads(base64.urlsafe_b64decode(body))
            if data['exp'] < time.time() or data['u'] not in self.users() or self.role(data['u']) == 'disabled':
                return None
            return data['u']
        except Exception:
            return None


def install(app, auth, store):
    from fastapi import Request
    from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, Response
    from pydantic import BaseModel

    LOGIN = (Path(__file__).resolve().parents[3] / 'ui' / 'login.html')
    OPEN = {'/login', '/api/login', '/api/health', '/login.html', '/api/auth'}

    @app.middleware('http')
    async def guard(request: Request, call_next):
        path = request.url.path
        internal = request.headers.get('x-db-internal')
        if internal and secrets.compare_digest(internal, getattr(app.state, 'internal_token', None) or '-'):
            from .store import ACTOR                      # the Assistant calling the program's own API in-process
            request.state.user = request.headers.get('x-db-actor') or 'claude'
            request.state.role = 'assistant'
            token = ACTOR.set(request.state.user)
            try:
                return await call_next(request)
            finally:
                ACTOR.reset(token)
        if auth.enabled and path not in OPEN and not path.startswith('/assets/'):
            user = auth.verify(request.cookies.get(COOKIE, ''))
            if not user:
                if path.startswith('/api/'):
                    return JSONResponse({'detail': {'code': 'E-AUTH', 'en': 'Please sign in.', 'ar': 'من فضلك سجّل الدخول.'}},
                                        status_code=401)
                return RedirectResponse('/login', status_code=303)
            if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('x-db') != '1':
                return JSONResponse({'detail': {'code': 'E-CSRF', 'en': 'Request refused.', 'ar': 'الطلب مرفوض.'}},
                                    status_code=403)
            request.state.user = user
            request.state.role = auth.role(user)
            write = request.method not in ('GET', 'HEAD', 'OPTIONS')
            if write and request.state.role == 'viewer' and path not in ('/api/logout', '/api/me/password'):
                return JSONResponse({'detail': {'code': 'E-ROLE', 'en': 'Your role can view only.',
                                                'ar': 'صلاحيتك مشاهدة بس.'}}, status_code=403)
            admin_only = path.startswith('/api/users') or path == '/api/auth/disable' or \
                (write and (path.startswith('/api/assistant/settings') or path.startswith('/api/drive/settings')))
            if admin_only and request.state.role != 'admin':
                return JSONResponse({'detail': {'code': 'E-ROLE', 'en': 'Administrators only: users, sign-in and the keys.',
                                                'ar': 'للمدير بس: المستخدمين وتسجيل الدخول والمفاتيح.'}}, status_code=403)
        from .store import ACTOR
        token = ACTOR.set(getattr(request.state, 'user', None) or 'local')
        try:
            resp = await call_next(request)
        finally:
            ACTOR.reset(token)
        if not auth.enabled:
            return resp                       # local mode: unchanged
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        resp.headers['X-Frame-Options'] = 'DENY'
        resp.headers['Referrer-Policy'] = 'same-origin'
        resp.headers['Content-Security-Policy'] = ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
                                                   "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                                                   "font-src https://fonts.gstatic.com; img-src 'self' data:; "
                                                   "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if auth.secure:
            resp.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return resp

    class Login(BaseModel):
        username: str
        password: str

    @app.get('/login', include_in_schema=False)
    def login_page():
        return HTMLResponse(LOGIN.read_text(encoding='utf-8'))

    @app.post('/api/login')
    def login(body: Login, request: Request):
        key = f"{body.username}|{request.client.host if request.client else '-'}"
        if auth.blocked(key):
            return JSONResponse({'detail': {'code': 'E-RATE', 'en': 'Too many attempts — try again in 15 minutes.',
                                            'ar': 'محاولات كتير — جرّب بعد 15 دقيقة.'}}, status_code=429)
        if not auth.check(body.username, body.password):
            auth.fail(key)
            store.audit(None, 'login.failed', user=body.username)
            return JSONResponse({'detail': {'code': 'E-LOGIN', 'en': 'Wrong username or password.',
                                            'ar': 'اسم المستخدم أو كلمة السر غلط.'}}, status_code=401)
        from .store import ACTOR
        t = ACTOR.set(body.username)
        store.audit(None, 'login', user=body.username)
        ACTOR.reset(t)
        auth.touch_login(body.username)
        r = JSONResponse({'ok': True, 'user': body.username})
        r.set_cookie(COOKIE, auth.issue(body.username), max_age=TTL, httponly=True, samesite='strict', secure=auth.secure)
        return r

    @app.post('/api/logout')
    def logout():
        r = JSONResponse({'ok': True})
        r.delete_cookie(COOKIE)
        return r

    @app.get('/api/me')
    def me(request: Request):
        return {'user': getattr(request.state, 'user', None), 'auth': auth.enabled,
                'role': getattr(request.state, 'role', None) if auth.enabled else 'admin'}

    def bad(code, en, ar, status=422):
        return JSONResponse({'detail': {'code': code, 'en': en, 'ar': ar}}, status_code=status)

    class Pw(BaseModel):
        old: str
        new: str

    @app.post('/api/me/password')
    def change_password(body: Pw, request: Request):
        u = getattr(request.state, 'user', None)
        if not u or not auth.check(u, body.old):
            return bad('E-LOGIN', 'Current password is wrong.', 'كلمة السر الحالية غلط.', 401)
        try:
            auth.add_user(u, body.new, auth.role(u))
        except ValueError as e:
            return bad('E-PASSWORD', str(e), 'كلمة السر لازم تكون 10 حروف على الأقل.')
        store.audit(None, 'user.password_changed', user=u)
        return {'ok': True}

    @app.get('/api/users')
    def users_list():
        return [{'username': k, 'role': auth.role(k), 'created': v.get('created'), 'last_login': v.get('last_login')} for k, v in sorted(auth.users().items())]

    @app.delete('/api/users/{username}')
    def users_delete(username: str, request: Request):
        if username == getattr(request.state, 'user', None):
            return bad('E-SELF', 'You cannot delete your own account.', 'مينفعش تمسح حسابك إنت.')
        try:
            auth.remove_user(username)
        except ValueError as e:
            return bad('E-USER', str(e), 'مينفعش: المستخدم غير موجود أو هو آخر مدير.')
        store.audit(None, 'user.removed', user=username)
        return {'ok': True}

    @app.get('/api/auth')
    def auth_state():
        """Is sign-in on, can it be switched here, how many accounts exist (no names)."""
        return {'enabled': auth.enabled, 'forced': auth.forced, 'switchable': auth.switchable, 'users': len(auth.users()),
                'can_enable': auth.switchable and not auth.enabled, 'can_disable': auth.switchable and auth.enabled}

    class FirstAdmin(BaseModel):
        username: str
        password: str

    @app.post('/api/auth/enable')
    def auth_enable(body: FirstAdmin, request: Request):
        """Local editions: turn sign-in on. No accounts yet → the body creates the first administrator (201); accounts exist →
        the body must be an existing administrator's username and password (200). The caller is signed in at once."""
        if auth.enabled:
            return bad('E-AUTH-ON', 'Sign-in is already on.', 'تسجيل الدخول شغّال بالفعل.', 409)
        if not auth.switchable:
            return bad('E-AUTH-FIXED', 'Sign-in cannot be switched in this edition.', 'تسجيل الدخول مش بيتغيّر في النسخة دي.', 409)
        users = auth.users()
        created = not users
        if users:                                             # a sign-in in effect: same brute-force limit as /api/login; 403, not 401, so the page stays
            key = f"{body.username}|{request.client.host if request.client else '-'}"
            if auth.blocked(key):
                return bad('E-RATE', 'Too many attempts — try again in 15 minutes.', 'محاولات كتير — جرّب بعد 15 دقيقة.', 429)
            if body.username not in users or auth.role(body.username) != 'admin' or not auth.check(body.username, body.password):
                auth.fail(key)
                store.audit(None, 'login.failed', user=body.username)
                return bad('E-LOGIN', 'Accounts exist: sign in as an existing administrator to turn sign-in on.',
                           'في حسابات موجودة: ادخل باسم مدير موجود وكلمة سره.', 403)
        else:
            try:
                auth.add_user(body.username, body.password, 'admin')
            except ValueError as e:
                return bad('E-USER', str(e), 'اسم المستخدم حروف وأرقام و . _ - @ وكلمة السر 10 حروف على الأقل.')
        auth.set_enabled(True)
        from .store import ACTOR
        t = ACTOR.set(body.username)
        store.audit(None, 'auth.enabled', by=body.username)
        if created:
            store.audit(None, 'user.added', user=body.username, role='admin')
        ACTOR.reset(t)
        auth.touch_login(body.username)
        r = JSONResponse({'ok': True, 'user': body.username, 'role': 'admin', 'created': created}, status_code=201 if created else 200)
        r.set_cookie(COOKIE, auth.issue(body.username), max_age=TTL, httponly=True, samesite='strict', secure=auth.secure)
        return r

    @app.post('/api/auth/disable')
    def auth_disable(request: Request):
        """Local editions: turn sign-in off (accounts are kept). Not in the cloud edition."""
        if not auth.switchable:
            return bad('E-AUTH-FORCED', 'Sign-in is always on in this edition.', 'تسجيل الدخول إجباري في النسخة دي.', 409)
        auth.set_enabled(False)
        store.audit(None, 'auth.disabled', by=getattr(request.state, 'user', None))
        r = JSONResponse({'ok': True})
        r.delete_cookie(COOKIE)
        return r

    class NewUser(BaseModel):
        username: str
        password: str
        role: str = 'editor'

    @app.post('/api/users', status_code=201)
    def users_add(body: NewUser):
        if body.username in auth.users():
            return bad('E-DUP', 'This username exists.', 'اسم المستخدم موجود.')
        try:
            auth.add_user(body.username, body.password, body.role)
        except ValueError as e:
            return bad('E-USER', str(e), 'بيانات المستخدم غير صحيحة (كلمة السر 10 حروف على الأقل، والدور مدير/محرّر/مشاهد).')
        store.audit(None, 'user.added', user=body.username, role=body.role)
        return {'ok': True}

    class RoleBody(BaseModel):
        role: str = None
        password: str = None

    @app.put('/api/users/{username}')
    def users_update(username: str, body: RoleBody):
        if username not in auth.users():
            return bad('E-NOT-FOUND', 'User not found.', 'المستخدم غير موجود.', 404)
        try:
            if body.role:
                auth.set_role(username, body.role)
            if body.password:
                auth.add_user(username, body.password, auth.role(username))
        except ValueError as e:
            return bad('E-USER', str(e), 'مينفعش: لازم يفضل مدير واحد على الأقل، وكلمة السر 10 حروف على الأقل.')
        store.audit(None, 'user.updated', user=username, role=body.role, password_reset=bool(body.password))
        return {'ok': True}
