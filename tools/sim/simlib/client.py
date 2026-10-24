"""HTTP client for the API driver: the same Auth / REST / RPC / Storage / Functions requests supabase-js sends, as one account.

Every request goes through one global token bucket (--rps) and a bounded thread pool (the driver), is timed, and keeps the
last request/response for a failure's reproduction. A token is refreshed by signing in again when it is close to expiry."""
import json, threading, time, urllib.parse

import requests

_local = threading.local()


def session():
    s = getattr(_local, 's', None)
    if s is None:
        s = _local.s = requests.Session()
        a = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0); s.mount('http://', a); s.mount('https://', a)
    return s


class Bucket:
    """Token bucket shared by all threads: at most rate requests per second on average, bursts up to burst."""
    def __init__(self, rate, burst=None):
        self.rate = float(rate); self.burst = float(burst or max(1.0, rate)); self.tokens = self.burst; self.t = time.monotonic(); self.lock = threading.Lock()
        self.waited = 0.0

    def take(self):
        """Wait for a token; returns the seconds waited (the simulator's own politeness, not the app's latency)."""
        if self.rate <= 0: return 0.0
        w = 0.0
        while True:
            with self.lock:
                now = time.monotonic(); self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate); self.t = now
                if self.tokens >= 1: self.tokens -= 1; return w
                need = (1 - self.tokens) / self.rate
            self.waited += need; w += need; time.sleep(need)


class Resp:
    __slots__ = ('status', 'data', 'text', 'ms', 'method', 'path', 'body', 'headers', 'wait_ms')

    def __init__(self, status, data, text, ms, method, path, body, headers=None):
        self.status, self.data, self.text, self.ms, self.method, self.path, self.body, self.headers = status, data, text, ms, method, path, body, headers or {}
        self.wait_ms = 0.0

    @property
    def ok(self): return 200 <= self.status < 300

    def err(self):
        if self.ok: return None
        d = self.data if isinstance(self.data, dict) else {}
        return {'status': self.status, 'code': d.get('code') or d.get('error_code') or '', 'message': (d.get('message') or d.get('msg') or d.get('error_description') or d.get('error') or self.text or '')[:300]}

    def repro(self):
        b = '' if self.body is None else (' ' + (self.body if isinstance(self.body, str) else json.dumps(self.body, ensure_ascii=False))[:400])
        return '%s %s%s → %s %s' % (self.method, self.path, b, self.status, (self.text or '')[:300])


class Client:
    def __init__(self, base, anon, bucket, timeout=20):
        self.base = base.rstrip('/'); self.anon = anon; self.bucket = bucket; self.timeout = timeout

    def call(self, method, path, body=None, token=None, headers=None, raw=None, ctype='application/json'):
        waited = self.bucket.take()
        h = {'apikey': self.anon, 'Authorization': 'Bearer ' + (token or self.anon)}
        if ctype: h['Content-Type'] = ctype
        if headers: h.update(headers)
        data = raw if raw is not None else (None if body is None else json.dumps(body, ensure_ascii=False).encode())
        t0 = time.perf_counter()
        try:
            r = session().request(method, self.base + path, data=data, headers=h, timeout=self.timeout)
            ms = (time.perf_counter() - t0) * 1000; text = r.text
            try: d = r.json() if text and text[:1] in '[{"' else (text or None)
            except ValueError: d = text
            out = Resp(r.status_code, d, text, ms, method, path, body if raw is None else '<%d bytes>' % len(raw), dict(r.headers)); out.wait_ms = waited * 1000
            return out
        except requests.RequestException as e:
            ms = (time.perf_counter() - t0) * 1000
            return Resp(599, None, 'network: %s' % str(e)[:200], ms, method, path, body)


class Account:
    """One simulated person's session."""
    def __init__(self, client, p):
        self.c = client; self.p = p; self.email = p['email']; self.pw = p['password']; self.uid = p.get('uid'); self.token = None; self.exp = 0
        self.lock = threading.Lock(); self.last = None; self.calls = []

    def _sess(self, j):
        self.token = j['access_token']; self.exp = time.time() + int(j.get('expires_in') or 3600); self.uid = j['user']['id']; self.p['uid'] = self.uid

    def signup(self, meta):
        r = self.c.call('POST', '/auth/v1/signup', {'email': self.email, 'password': self.pw, 'data': meta})
        if r.ok and isinstance(r.data, dict) and r.data.get('access_token'): self._sess(r.data)
        return r

    def signin(self):
        r = self.c.call('POST', '/auth/v1/token?grant_type=password', {'email': self.email, 'password': self.pw})
        if r.ok and isinstance(r.data, dict) and r.data.get('access_token'): self._sess(r.data)
        return r

    def ensure(self):
        with self.lock:
            if self.token and time.time() < self.exp - 120: return True
            r = self.signin(); return r.ok

    def _rec(self, r): self.last = r; self.calls.append(r); return r

    # PostgREST
    def get(self, table, query, prefer=None):
        return self._rec(self.c.call('GET', '/rest/v1/%s?%s' % (table, query), token=self.token, headers={'Prefer': prefer} if prefer else None))

    def insert(self, table, row, select='*', upsert=None, ignore=False, query=''):
        pref = ['return=representation' if select else 'return=minimal']
        if upsert: pref.append('resolution=%s' % ('ignore-duplicates' if ignore else 'merge-duplicates'))
        q = ('?on_conflict=%s' % upsert) if upsert else ''
        if select: q += ('&' if q else '?') + 'select=' + urllib.parse.quote(select, safe=',*()!:')
        return self._rec(self.c.call('POST', '/rest/v1/%s%s' % (table, q), row, token=self.token, headers={'Prefer': ','.join(pref)}))

    def update(self, table, filt, row, select='*'):
        q = filt + ('&select=' + select if select else '')
        return self._rec(self.c.call('PATCH', '/rest/v1/%s?%s' % (table, q), row, token=self.token, headers={'Prefer': 'return=representation' if select else 'return=minimal'}))

    def delete(self, table, filt, select='*'):
        q = filt + ('&select=' + select if select else '')
        return self._rec(self.c.call('DELETE', '/rest/v1/%s?%s' % (table, q), token=self.token, headers={'Prefer': 'return=representation' if select else 'return=minimal'}))

    def rpc(self, fn, args=None):
        return self._rec(self.c.call('POST', '/rest/v1/rpc/%s' % fn, args or {}, token=self.token))

    # Storage, Functions
    def upload(self, bucket, path, data, ctype):
        return self._rec(self.c.call('POST', '/storage/v1/object/%s/%s' % (bucket, urllib.parse.quote(path)), token=self.token, raw=data, ctype=ctype))

    def sign(self, bucket, path, expires=600):
        return self._rec(self.c.call('POST', '/storage/v1/object/sign/%s/%s' % (bucket, urllib.parse.quote(path)), {'expiresIn': expires}, token=self.token))

    def fetch(self, path):
        return self._rec(self.c.call('GET', path, token=self.token, ctype=None))

    def fn(self, name, body):
        return self._rec(self.c.call('POST', '/functions/v1/%s' % name, body, token=self.token))
