"""B3 end-to-end: two real people in two browsers — request, notification, accept/decline, suggestions by mutual connections,
real network numbers, notification read/clear, the profile/Connect buttons with local ids, and row-level security."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:220]))
def sql(q): return subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-c', q], capture_output=True, text=True).stdout.strip()
st = int(time.time()); PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(3500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    ca, cb = b.new_context(viewport={'width': 1440, 'height': 900}), b.new_context(viewport={'width': 1440, 'height': 900})
    A, B = ca.new_page(), cb.new_page()
    for pg in (A, B): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a_id = signup(A, 'Dr. Alice Sender', f'alice{st}@x.test'); b_id = signup(B, 'Dr. Bob Receiver', f'bob{st}@x.test')
    # a mutual friend of Bob and a friend-of-friend for Alice's suggestions
    m_id = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('mutual{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Dr. Mona Mutual\"}}') returning id").split('\n')[0]
    sql(f"insert into public.connections (requester, addressee, status) values ('{a_id}','{m_id}','accepted')")
    f_id = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('fof{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Dr. Fady Friendof\"}}') returning id").split('\n')[0]
    sql(f"insert into public.connections (requester, addressee, status) values ('{m_id}','{f_id}','accepted')")
    A.evaluate("goto('network')"); A.wait_for_timeout(2500)
    net = A.inner_text('#content')
    T('network shows real people only (no demo people)', 'Dr. Bob Receiver' in net and 'Allison Wang' not in net and 'Muhammed Musthafa' not in net, net[:300])
    sug = A.evaluate("dxLive.sb.rpc('suggest_people',{p_limit:12}).then(r=>(r.data||[]).map(x=>[x.id,x.mutual]))")
    T('a friend-of-friend is suggested first with its mutual count; existing friends are not suggested', sug and sug[0] == [f_id, 1] and all(i != m_id for i, _ in sug) and len({i for i, _ in sug}) == len(sug), sug[:4])
    nums = A.evaluate("[...document.querySelectorAll('#content .net-overview-n')].map(e=>e.textContent)")
    T('network numbers are real (1 connection, not the demo 148)', nums[:1] == ['1'], nums)
    bob = A.evaluate(f"dxLive.aid('{b_id}')"); A.evaluate(f"connect({bob})"); A.wait_for_timeout(1500)
    T('Connect sends a real request', sql(f"select status from public.connections where requester='{a_id}' and addressee='{b_id}'") == 'pending')
    T('the database notifies Bob', sql(f"select count(*) from public.notifications where user_id='{b_id}' and type='connection_request' and from_user='{a_id}'") == '1')
    B.reload(wait_until='load'); B.wait_for_timeout(400); B.evaluate('endSplash()'); B.wait_for_timeout(3500)
    T("Bob's network badge shows the request", B.evaluate("(document.getElementById('nb-net')||{}).textContent") == '1')
    B.evaluate("goto('notifs')"); B.wait_for_timeout(2500)
    txt = B.inner_text('#content'); T('Bob sees "Dr. Alice Sender sent you a connection request" with Accept', 'Dr. Alice Sender sent you a connection request' in txt and B.evaluate("!!document.querySelector('#content [onclick*=acceptConnection]')"), txt[:200])
    B.evaluate("document.querySelector('#content [onclick*=acceptConnection]').click()"); B.wait_for_timeout(1500)
    T('Accept makes it a real connection', sql(f"select status from public.connections where requester='{a_id}' and addressee='{b_id}'") == 'accepted')
    T('Alice is notified that Bob accepted', sql(f"select count(*) from public.notifications where user_id='{a_id}' and type='connection_accepted'") == '1')
    A.evaluate("goto('feed')"); A.wait_for_timeout(300); A.evaluate("goto('notifs')"); A.wait_for_timeout(2500)
    T('Alice sees "Dr. Bob Receiver accepted your connection request"', 'Dr. Bob Receiver accepted your connection request' in A.inner_text('#content'))
    nid = A.evaluate("NOTIFS[0].id"); A.evaluate(f"markNotifRead({nid})"); A.wait_for_timeout(1000)
    T('reading a notification is saved', sql(f"select read from public.notifications where id={nid}") == 't')
    B.evaluate(f"gotoProfile({B.evaluate(f'dxLive.aid(\"{a_id}\")')})"); B.wait_for_timeout(1500)
    T("opening someone's profile shows THEM (local ids work with parseInt)", 'Dr. Alice Sender' in B.inner_text('#content'))
    # decline path
    c_id = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('carl{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Dr. Carl Asker\"}}') returning id").split('\n')[0]
    sql(f"insert into public.connections (requester, addressee, status) values ('{c_id}','{b_id}','pending')")
    B.evaluate("goto('feed')"); B.wait_for_timeout(300); B.evaluate("dxLive.loadConnections().then(dxLive.loadNotifs)"); B.wait_for_timeout(1500); B.evaluate("goto('notifs')"); B.wait_for_timeout(1500)
    B.evaluate("document.querySelector('#content [onclick*=declineConnection]').click()"); B.wait_for_timeout(1500)
    T('Decline is saved (request rejected)', sql(f"select status from public.connections where requester='{c_id}' and addressee='{b_id}'") == 'rejected')
    # security
    r = A.evaluate(f"dxLive.sb.from('connections').insert({{requester:'{m_id}',addressee:'{f_id}',status:'pending'}}).then(r=>!!r.error)")
    T('cannot create a request in someone else\'s name', r)
    sql(f"insert into public.connections (requester, addressee, status) values ('{f_id}','{m_id}','pending') on conflict do nothing")
    r = A.evaluate(f"dxLive.sb.from('connections').update({{status:'accepted'}}).eq('requester','{f_id}').eq('addressee','{m_id}').select().then(r=>(r.data||[]).length)")
    T('cannot accept a request addressed to someone else', r == 0)
    r = A.evaluate(f"dxLive.sb.from('notifications').select('id').eq('user_id','{b_id}').then(r=>(r.data||[]).length)")
    T("cannot read someone else's notifications", r == 0)
    r = A.evaluate("dxLive.sb.rpc('suggest_people',{p_limit:12})"); r2 = A.evaluate("fetch(DRUGBOX_CONFIG.url+'/rest/v1/rpc/suggest_people',{method:'POST',headers:{'apikey':DRUGBOX_CONFIG.anonKey,'content-type':'application/json'},body:'{}'}).then(r=>r.status)")
    T('suggestions need a signed-in user (not open to anonymous calls)', r2 in (401, 403, 404), r2)
    T('no errors in the page', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
