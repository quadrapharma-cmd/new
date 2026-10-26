"""W-20 phone verification codes by SMS (migration 0093 + supabase/functions/sms-dispatch), through the real function and the local
SMS stand-in (Twilio's API on the mock port). A member asks for a code; only the server reads or works the outbox; the function refuses
callers without the scheduler's secret, sends the code to the number with the provider's account, keeps a refused SMS for a later try
(at most 3), and never sends a code older than its 10 minutes."""
import json, random, urllib.request, urllib.error
from _dx import APP_URL as U, R, T, sql, ST, fn_env, refused, done   # shared settings: tests/e2e/_dx.py
G = U.rstrip('/')
ENV = fn_env()
ANON, SECRET, MOCK = ENV['SUPABASE_ANON_KEY'], ENV.get('SMS_DISPATCH_SECRET', ''), ENV.get('SMS_API_BASE', 'http://127.0.0.1:54500')
def http(method, path, body=None, token=None, headers=None):
    h = {'Content-Type': 'application/json', 'apikey': ANON, **({'Authorization': 'Bearer ' + token} if token else {}), **(headers or {})}
    req = urllib.request.Request(G + path, method=method, data=None if body is None else json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r: t = r.read().decode(); return r.status, (json.loads(t) if t and t[0] in '{[' else t)
    except urllib.error.HTTPError as e: t = e.read().decode(); return e.code, (json.loads(t) if t and t[0] in '{[' else t)
def user(name):
    s, j = http('POST', '/auth/v1/signup', {'email': f'{name}{ST}@x.test', 'password': 'Strong-pass-2026', 'data': {'name': name}})
    return j.get('access_token') or (j.get('session') or {}).get('access_token'), (j.get('user') or {}).get('id')
def dispatch(secret): return http('POST', '/functions/v1/sms-dispatch', {}, headers={'Authorization': 'Bearer ' + secret} if secret is not None else {})
def smss(): return [x for x in json.loads(urllib.request.urlopen(MOCK + '/log').read()) if '/Messages.json' in x['path']]

T('the local stack has the SMS settings (start-payments.sh with payments.env.example)', SECRET and ENV.get('SMS_PROVIDER') == 'twilio', 'restart tools/local-supabase/start-payments.sh')
sql("update private.sms_outbox set sent_at = now() where sent_at is null")    # earlier runs' codes: not this test's
a_t, a = user('smsa'); b_t, b = user('smsb')
num = '010%08d' % random.randint(0, 99999999); e164 = '+20' + num[1:]
s, j = http('POST', '/rest/v1/rpc/phone_verify_start', {'p_phone': num}, a_t)
T('a member asks for a code', s == 200 and j.get('sent') is True and e164 not in json.dumps(j), (s, j))
s, j = http('POST', '/rest/v1/rpc/phone_verify_start', {'p_phone': '+201099900000'}, b_t)   # the stand-in refuses this number
# ── nobody but the server ──
s, j = http('POST', '/rest/v1/rpc/sms_claim', {'p_limit': 5}, a_t)
T('a member cannot claim the SMS batch (sms_claim is server-only)', s in (401, 403, 404) and sql("select count(*) from private.sms_outbox where attempts > 0 and sent_at is null") == '0', (s, j))
s, j = http('POST', '/rest/v1/rpc/sms_done', {'p_id': 1, 'p_ok': True}, a_t)
T('…nor mark one sent', s in (401, 403, 404), (s, j))
s, j = http('POST', '/rest/v1/rpc/sms_claim', {'p_limit': 5}, ANON)
T('…nor can anon', s in (401, 403, 404), (s, j))
# ── the function ──
before = len(smss())
s, j = dispatch(None); T('the dispatcher refuses a caller without the secret', s == 401, (s, j))
s, j = dispatch('wrong-' + SECRET); T('…and one with a wrong secret', s == 401 and len(smss()) == before, (s, j))
s, j = dispatch(ANON); T('…and the public anon key', s == 401 and len(smss()) == before, (s, j))
s, j = dispatch(SECRET)
T('with the secret it sends what is waiting', s == 200 and j.get('sent', 0) >= 1 and j.get('failed', 0) >= 1, (s, j))
m = [x for x in smss()[before:] if x['body'].get('To') == e164]
T('one SMS to the number, from the configured sender, with the provider account', len(m) == 1 and m[0]['auth_ok'] and m[0]['body'].get('From') == ENV['SMS_FROM'], m)
code = (m[0]['body'].get('Body', '') if m else '')
T('…carrying the 6-digit code, in English and Arabic', m and __import__('re').search(r'Drugbox code: \d{6}', code) and 'رمز Drugbox' in code, code)
T('the outbox marks it sent', sql(f"select (sent_at is not null)||'|'||attempts from private.sms_outbox where phone='{e164}'") == 'true|1')
T('a refused SMS stays for a later try, with the reason', sql("select (sent_at is null)||'|'||attempts||'|'||(last_error like 'provider answered 400%') from private.sms_outbox where phone='+201099900000' order by id desc limit 1") == 'true|1|true')   # the newest: earlier runs leave theirs
s, j = dispatch(SECRET); after = len(smss())
T('a sent SMS is not sent again (the refused one is tried again later, not at once)', s == 200 and j.get('sent', 0) == 0 and len([x for x in smss()[before:] if x['body'].get('To') == e164]) == 1, (s, j))
# the code arrives and verifies
import re
c = re.search(r'(\d{6})', code).group(1) if code else '000000'
s, j = http('POST', '/rest/v1/rpc/phone_verify_confirm', {'p_code': c}, a_t)
T('the code from the SMS verifies the number', s == 200 and j.get('verified') is True, (s, j))
# an old code is never sent
sql("insert into private.sms_outbox (phone, body, created_at) values ('+201011112222', 'Drugbox code: 123456', now() - interval '11 minutes')")
s, j = dispatch(SECRET)
T('a code older than 10 minutes is never sent', not [x for x in smss()[after:] if x['body'].get('To') == '+201011112222'], j)
sql("update private.sms_outbox set sent_at = now() where sent_at is null")
done()
