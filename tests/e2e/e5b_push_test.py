"""Web push (w-pwa, migration 0110 + supabase/functions/notify-email + _shared/webpush.js) through the real function and the local push
service stand-in (tools/local-supabase/push-standin.mjs, started by start-payments.sh). A fake browser subscription (its own keys, like a
browser makes) is saved for member A; a real action of member B (a comment on A's post) makes the function send A a push that the
stand-in accepts only with a valid VAPID signature, and that decrypts with A's keys to Drugbox's own words + B's name + the link —
never the comment's text. Nobody else reads or removes A's device; a device the push service no longer knows is removed; nothing comes
from someone A blocked; only the scheduler (service role) runs the function."""
import json, base64, urllib.request, urllib.error, uuid
from _dx import APP_URL as U, R, T, sql, ST, fn_env, refused, wait_for, done   # shared settings: tests/e2e/_dx.py
from _webpush import FakeSubscription
G = U.rstrip('/')
ENV = fn_env()
ANON, PUSH = ENV['SUPABASE_ANON_KEY'], ENV.get('PUSH_URL', 'http://127.0.0.1:54600/push')
def http(method, path, body=None, token=None, headers=None):
    h = {'Content-Type': 'application/json', 'apikey': ANON, **({'Authorization': 'Bearer ' + token} if token else {}), **(headers or {})}
    req = urllib.request.Request(G + path, method=method, data=None if body is None else json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r: t = r.read().decode(); return r.status, (json.loads(t) if t and t[0] in '{[' else t)
    except urllib.error.HTTPError as e: t = e.read().decode(); return e.code, (json.loads(t) if t and t[0] in '{[' else t)
def user(name):
    s, j = http('POST', '/auth/v1/signup', {'email': f'{name.lower()}{ST}@x.test', 'password': 'Strong-pass-2026', 'data': {'name': name}})
    return j.get('access_token'), (j.get('user') or {}).get('id')
def pushes(pid): return json.loads(urllib.request.urlopen(PUSH + '/log?id=' + pid).read())
def subscribe(tok, sub): return http('POST', '/rest/v1/rpc/push_subscribe', {'p_endpoint': sub.endpoint, 'p_p256dh': sub.p256dh, 'p_auth': sub.auth}, tok)

T('the local stack sends pushes (VAPID keys and the push stand-in from start-payments.sh)', ENV.get('VAPID_PUBLIC_KEY') and ENV.get('VAPID_PRIVATE_KEY'), 'restart start.sh, then start-payments.sh')
a_t, a = user('Pusha'); b_t, b = user('Pushb'); c_t, c = user('Pushc')
pid = 'dev' + uuid.uuid4().hex[:12]; sub = FakeSubscription(f'{PUSH}/{pid}')
s, j = subscribe(a_t, sub); T('A saves this device (push_subscribe)', s == 200 and sql(f"select count(*) from public.push_subscriptions where user_id='{a}'") == '1', (s, j))
s, j = http('GET', '/rest/v1/push_subscriptions?select=id,endpoint', token=b_t)
T("B does not see A's device", s == 200 and j == [], (s, j))
s, j = http('GET', '/rest/v1/push_subscriptions?select=p256dh,auth', token=a_t)
T('A cannot read the device keys back (server only)', s in (401, 403), (s, j))
s, j = http('DELETE', f'/rest/v1/push_subscriptions?user_id=eq.{a}', token=b_t)
T("B cannot remove A's device", sql(f"select count(*) from public.push_subscriptions where user_id='{a}'") == '1', (s, j))
s, j = http('POST', '/rest/v1/push_subscriptions', {'user_id': b, 'endpoint': f'{PUSH}/x{pid}', 'p256dh': sub.p256dh, 'auth': sub.auth}, b_t)
T('nobody adds a device by writing the table', refused(j if s >= 400 else None) and s >= 400, (s, j))
s, j = subscribe(b_t, FakeSubscription('https://attacker.example/push/x'))
T('an address that is not a push service is refused', s >= 400 and 'push service' in json.dumps(j), (s, j))
s, j = http('POST', '/rest/v1/rpc/push_outbox_claim', {'p_limit': 5}, a_t)
T('a member cannot claim the queue (it carries device keys)', s in (401, 403, 404), (s, j))
s, j = http('POST', '/functions/v1/notify-email', {}, a_t)
T('only the scheduler runs the sender (a member is refused)', s == 401, (s, j))

post = sql(f"insert into public.posts (user_id, body) values ('{a}', 'Push post {ST}') returning id").split('\n')[0]
s, j = http('POST', '/rest/v1/comments', {'post_id': int(post), 'user_id': b, 'body': f'SECRET COMMENT TEXT {ST}'}, b_t, {'Prefer': 'return=minimal'})
T("B comments on A's post (a real notice for A)", s in (200, 201), (s, j))
got = wait_for(lambda: pushes(pid), 30, 0.5)
T('the function sends A a push within 30 s', got, 'nothing reached the push stand-in — see /tmp/drugbox-fn.log')
if got:
    e = got[-1]
    T('signed with the VAPID key (the stand-in checked the ES256 signature, audience and expiry)', e['vapid_ok'], e)
    T('encrypted as aes128gcm with a TTL', e['encoding'] == 'aes128gcm' and int(e['ttl'] or 0) > 0, e)
    try: msg = json.loads(sub.decrypt(base64.b64decode(e['body']))); ok = True
    except Exception as x: msg, ok = {'error': str(x)}, False
    T("…and decrypts with A's device keys", ok, msg)
    T('it says who and what in Drugbox\'s words, opening the post', 'Pushb' in msg.get('title', '') and 'comment' in msg.get('title', '').lower() and msg.get('url') == f'#/post/{post}', msg)
    T('…and never what B wrote', 'SECRET' not in json.dumps(msg), msg)
T('the notice is marked sent', wait_for(lambda: sql(f"select count(*) from private.push_outbox where user_id='{a}' and sent_at is not null and error is null") == '1', 10))
# a device the push service no longer knows
gone = FakeSubscription(f'{PUSH}/gone{uuid.uuid4().hex[:10]}'); s, j = subscribe(a_t, gone)
before = len(pushes(pid))
sql(f"insert into public.notifications (user_id, type, from_user, message) values ('{a}', 'connection_request', '{b}', 'wants to connect')")
T('a device that answers 410 is removed', wait_for(lambda: sql(f"select count(*) from public.push_subscriptions where endpoint='{gone.endpoint}'") == '0', 30))
T('…while the live device still gets it', wait_for(lambda: len(pushes(pid)) > before, 10))
# blocks and switches
s, j = http('POST', '/rest/v1/user_blocks', {'blocker': a, 'blocked': c}, a_t, {'Prefer': 'return=minimal'})
before = len(pushes(pid))
sql(f"insert into public.notifications (user_id, type, from_user, message) values ('{a}', 'connection_request', '{c}', 'wants to connect')")
http('PATCH', f'/rest/v1/member_settings?user_id=eq.{a}', {'push_connections': False}, a_t)
sql(f"insert into public.notifications (user_id, type, from_user, message) values ('{a}', 'connection_accepted', '{b}', 'accepted')")
sql(f"insert into public.notifications (user_id, type, from_user, message) values ('{a}', 'mention', '{b}', 'mentioned you')")
T('a kind A allows still arrives (mention)', wait_for(lambda: len(pushes(pid)) > before, 30))
T('nothing from someone A blocked, nothing of a kind A switched off', len(pushes(pid)) == before + 1 and sql(f"select count(*) from private.push_outbox where user_id='{a}' and sent_at is null") == '0', len(pushes(pid)) - before)
# signing out on that device: the row goes (the page does it with the session; here the same REST call)
s, j = http('DELETE', f'/rest/v1/push_subscriptions?endpoint=eq.{sub.endpoint}', token=a_t)
T('A removes the device (sign-out / Turn off)', sql(f"select count(*) from public.push_subscriptions where user_id='{a}'") == '0', (s, j))
done()
