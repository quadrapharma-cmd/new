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
        self.enabled = enabled
        self._fail, self._lock = {}, threading.Lock()
        self.root = Path(workspace)
        self.root.mkdir(parents=True, exist_ok=True)
        self.users_file = self.root / 'users.json'
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

    # ---- users
    def users(self):
        return json.loads(self.users_file.read_text()) if self.users_file.exists() else {}

    def add_user(self, username, password, role='user'):
        if len(password) < 10:
            raise ValueError('password must be at least 10 characters')
        users = self.users()
        salt = secrets.token_bytes(16)
        users[username] = {'salt': salt.hex(), 'hash': _scrypt(password, salt).hex(), 'role': role, 'created': time.time()}
        tmp = self.users_file.with_suffix('.tmp')
        tmp.write_text(json.dumps(users, indent=1))
        os.chmod(tmp, 0o600)
        tmp.replace(self.users_file)

    def check(self, username, password):
        u = self.users().get(username)
        if not u:
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
            if data['exp'] < time.time() or data['u'] not in self.users():
                return None
            return data['u']
        except Exception:
            return None


def install(app, auth, store):
    from fastapi import Request
    from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, Response
    from pydantic import BaseModel

    LOGIN = (Path(__file__).resolve().parents[3] / 'ui' / 'login.html')
    OPEN = {'/login', '/api/login', '/api/health', '/login.html'}

    @app.middleware('http')
    async def guard(request: Request, call_next):
        path = request.url.path
        if auth.enabled and path not in OPEN:
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
        resp = await call_next(request)
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
        store.audit(None, 'login', user=body.username)
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
        return {'user': getattr(request.state, 'user', None), 'auth': auth.enabled}
