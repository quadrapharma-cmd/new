"""B-13 e-mail notifications (migration 0059 + supabase/functions/notify-dispatch), through the real function and the local
e-mail stand-in (Resend's API on the mock port). The database queues only business notices, never for someone who turned
e-mails off; nobody but the server reads or works the queue; the function refuses callers without the scheduler's secret,
sends what is pending, and keeps a refused e-mail for a later try (up to 5)."""
import json, urllib.request, urllib.error
from _dx import APP_URL as U, R, T, sql, ST, fn_env, refused, done   # shared settings: tests/e2e/_dx.py
G = U.rstrip('/')
ENV = fn_env()
ANON, SECRET, MOCK = ENV['SUPABASE_ANON_KEY'], ENV.get('NOTIFY_DISPATCH_SECRET', ''), ENV.get('EMAIL_API_BASE', 'http://127.0.0.1:54500')
def http(method, path, body=None, token=None, headers=None):
    h = {'Content-Type': 'application/json', 'apikey': ANON, **({'Authorization': 'Bearer ' + token} if token else {}), **(headers or {})}
    req = urllib.request.Request(G + path, method=method, data=None if body is None else json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r: t = r.read().decode(); return r.status, (json.loads(t) if t and t[0] in '{[' else t)
    except urllib.error.HTTPError as e: t = e.read().decode(); return e.code, (json.loads(t) if t and t[0] in '{[' else t)
def user(name, email=None):
    s, j = http('POST', '/auth/v1/signup', {'email': email or f'{name}{ST}@x.test', 'password': 'Strong-pass-2026', 'data': {'name': name}})
    return j.get('access_token') or (j.get('session') or {}).get('access_token'), (j.get('user') or {}).get('id')
def dispatch(secret, body=None): return http('POST', '/functions/v1/notify-dispatch', body or {}, headers={'Authorization': 'Bearer ' + secret} if secret is not None else {})
def notify(uid, kind, company=None):
    return sql(f"insert into public.notifications (user_id, type, company_id, data) values ('{uid}', '{kind}', {company or 'null'}, '{{}}'::jsonb) returning id").split('\n')[0]
def mails(): return [x for x in json.loads(urllib.request.urlopen(MOCK + '/log').read()) if x['path'] == '/emails']

T('the local stack has the dispatch settings (start-payments.sh with payments.env.example)', SECRET and ENV.get('EMAIL_PROVIDER') == 'resend', 'restart tools/local-supabase/start-payments.sh')
sql("update public.notification_outbox set status='skipped' where status='pending'")    # other suites' notices: not this test's
a_t, a = user('mailyes'); b_t, b = user('mailno'); c_t, c = user('mailbounce', f'bounce{ST}@x.test')
cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{a}','Mail Pharma {ST}','mail-pharma-{ST}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
# ── preferences: your own only ──
s, j = http('POST', '/rest/v1/notification_prefs', {'user_id': b, 'email': False}, b_t, {'Prefer': 'return=minimal'})
T('a member turns e-mails off for themselves', s in (200, 201) and sql(f"select email from public.notification_prefs where user_id='{b}'") == 'f', (s, j))
s, j = http('POST', '/rest/v1/notification_prefs', {'user_id': a, 'email': False}, b_t, {'Prefer': 'return=minimal'})
T("…but cannot change someone else's", refused(j if s >= 400 else None) and sql(f"select count(*) from public.notification_prefs where user_id='{a}'") == '0', (s, j))
# ── what is queued ──
na = notify(a, 'deal', cid); notify(a, 'like'); notify(b, 'deal', cid); nc = notify(c, 'payment')
T('a business notice is queued for an e-mail', sql(f"select count(*) from public.notification_outbox where notification_id={na} and status='pending'") == '1')
T('a like is not', sql(f"select count(*) from public.notification_outbox where user_id='{a}'") == '1')
T('nothing is queued for someone who turned e-mails off', sql(f"select count(*) from public.notification_outbox where user_id='{b}'") == '0')
# ── nobody but the server ──
s, j = http('GET', '/rest/v1/notification_outbox?select=id', token=a_t)
T('a member cannot read the queue (not even their own rows)', s == 200 and j == [] or s in (401, 403), (s, j))
s, j = http('PATCH', f'/rest/v1/notification_outbox?user_id=eq.{a}', {'status': 'sent'}, a_t)
T('…nor mark an e-mail as sent', sql(f"select status from public.notification_outbox where notification_id={na}") == 'pending', (s, j))
s, j = http('POST', '/rest/v1/rpc/outbox_claim', {'p_limit': 5}, a_t)
T('…nor claim the batch (outbox_claim is server-only)', s in (401, 403, 404) and sql(f"select attempts from public.notification_outbox where notification_id={na}") == '0', (s, j))
s, j = http('POST', '/rest/v1/rpc/outbox_done', {'p_id': 1, 'p_ok': True}, a_t)
T('…nor outbox_done', s in (401, 403, 404), (s, j))
# ── the function ──
before = len(mails())
s, j = dispatch(None); T('the dispatcher refuses a caller without the secret', s == 401, (s, j))
s, j = dispatch('wrong-' + SECRET); T('…and one with a wrong secret', s == 401 and len(mails()) == before, (s, j))
s, j = dispatch(ANON); T('…and the public anon key', s == 401 and len(mails()) == before, (s, j))
s, j = dispatch(SECRET, {'limit': 50})
T('with the secret it sends what is pending', s == 200 and j.get('sent', 0) >= 1 and j.get('failed', 0) >= 1, (s, j))
m = [x for x in mails()[before:] if x['body'].get('to') == [f'mailyes{ST}@x.test']]
T('one e-mail to the member, from the configured sender, through the provider key', len(m) == 1 and m[0]['auth_ok'] and m[0]['body']['from'] == ENV['EMAIL_FROM'], m)
T('…with the subject in Drugbox\'s own words and a link — in English and Arabic', m and m[0]['body']['subject'] == 'Drugbox — A request or deal needs you' and 'طلب أو صفقة' in m[0]['body']['text'] and G in m[0]['body']['text'], m and m[0]['body'])
T('…and no text a member wrote (not even the company name)', m and 'Mail Pharma' not in json.dumps(m[0]['body'], ensure_ascii=False), m and m[0]['body'])
T('the queue marks it sent', sql(f"select status||'|'||(sent_at is not null) from public.notification_outbox where notification_id={na}") == 'sent|true')
T('a refused e-mail stays queued with the reason, for a later try', sql(f"select status||'|'||attempts||'|'||(last_error like 'provider answered 422%') from public.notification_outbox where notification_id={nc}") == 'pending|1|true')
s, j = dispatch(SECRET); after = len(mails())
T('a second run does not send the sent e-mail again', [x for x in mails()[before:] if x['body'].get('to') == [f'mailyes{ST}@x.test']].__len__() == 1, j)
tries = int(sql(f"select attempts from public.notification_outbox where notification_id={nc}"))
sql(f"update public.notification_outbox set status='sending', claimed_at=now() where notification_id={nc}"); s, j = dispatch(SECRET)
T('an e-mail another run is sending (claimed minutes ago) is not taken again', sql(f"select attempts from public.notification_outbox where notification_id={nc}") == str(tries), j)
sql(f"update public.notification_outbox set claimed_at=now()-interval '11 minutes' where notification_id={nc}"); dispatch(SECRET)
T('…one a crashed run left behind is taken again after 10 minutes', sql(f"select status||'|'||attempts from public.notification_outbox where notification_id={nc}") == 'pending|%d' % (tries + 1))
sql(f"update public.notification_outbox set attempts=4 where notification_id={nc}"); dispatch(SECRET)
T('after 5 tries it is marked failed and no longer tried', sql(f"select status||'|'||attempts from public.notification_outbox where notification_id={nc}") == 'failed|5')
done()
