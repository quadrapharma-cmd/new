"""B4 end-to-end: two people in two browsers — message from a profile, delivery without reload, unread badge, read receipts,
reply arriving live in an open conversation, no demo filler, and row-level security."""
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
def wait_for(pg, js, secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        if pg.evaluate(js): return round(time.time() - t0, 1)
        pg.wait_for_timeout(500)
    return None
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A = b.new_context(viewport={'width': 1440, 'height': 900}).new_page(); B = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
    for pg in (A, B): pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    a_id = signup(A, 'Dr. Amal Writer', f'amal{st}@x.test'); b_id = signup(B, 'Dr. Basem Reader', f'basem{st}@x.test')
    bob = A.evaluate(f"(()=>{{var a=dxLive.aid('{b_id}');USERS.push({{id:a,name:'Dr. Basem Reader',initials:'DB',color:'#1A56DB',headline:'',company:'',verified:false}});return a}})()")
    A.evaluate(f"messageUser({bob})"); A.wait_for_timeout(2500)
    T('Message from a profile opens a conversation with that person', 'Dr. Basem Reader' in A.inner_text('.chat-head') and A.evaluate("!!document.querySelector('#threadList .mx-thread[data-person^=u]')"), A.inner_text('.chat-head')[:80])
    demo = A.inner_text('#threadList') + A.inner_text('#messagesArea')
    T('no demo conversations or seeded filler messages', 'Allison' not in demo and 'following up on our discussion' not in demo, demo[:200])
    A.fill('#composeInput', f'Hello Basem, can you share the COA? {st}'); A.evaluate("sendMessage()"); A.wait_for_timeout(1500)
    T('message saved in the database', sql(f"select count(*) from public.messages where sender_id='{a_id}' and receiver_id='{b_id}' and body like 'Hello Basem%{st}'") == '1')
    A.wait_for_timeout(3500)
    T('no simulated reply appears after sending', A.evaluate("document.querySelectorAll('#messagesArea .msg-row.mx-theirs').length") == 0)
    got = wait_for(B, "(document.getElementById('nb-msg')||{}).textContent==='1'", 30)
    T(f'Basem gets the unread badge without reloading (after {got}s)', got is not None)
    B.evaluate("goto('messages')"); B.wait_for_timeout(3000)
    T('Basem sees the conversation with Amal, marked unread', 'Dr. Amal Writer' in B.inner_text('#threadList') and 'Hello Basem' in B.inner_text('#messagesArea'), B.inner_text('#threadList')[:120])
    B.wait_for_timeout(1500)
    T('opening it marks the message read (read receipt stored)', sql(f"select read_at is not null from public.messages where sender_id='{a_id}' and receiver_id='{b_id}' order by id desc limit 1") == 't')
    T('badge clears after reading', B.evaluate("(document.getElementById('nb-msg')||{}).style.display") == 'none')
    B.fill('#composeInput', f'Sure — COA attached shortly {st}'); B.evaluate("sendMessage()"); B.wait_for_timeout(800)
    got = wait_for(A, f"document.getElementById('messagesArea').innerText.indexOf('COA attached shortly {st}')>=0", 15)
    T(f'reply appears live in Amal\'s open conversation (after {got}s)', got is not None)
    A.reload(wait_until='load'); A.wait_for_timeout(400); A.evaluate('endSplash()'); A.wait_for_timeout(3000); A.evaluate("goto('messages')"); A.wait_for_timeout(3000)
    txt = A.inner_text('#messagesArea')
    T('after reload the whole conversation is there, in order', txt.find('Hello Basem') >= 0 and txt.find('COA attached shortly') > txt.find('Hello Basem'), txt[:200])
    T('conversation summary: Basem has 0 unread from Amal after reading', sql(f"select unread from public.conversation_heads where owner='{b_id}' and partner='{a_id}'") == '0')
    T('conversation summary: Amal sees the reply as the last message', sql(f"select last_body like 'Sure%' and not last_from_me from public.conversation_heads where owner='{a_id}' and partner='{b_id}'") == 't')
    r = A.evaluate(f"dxLive.sb.from('conversation_heads').select('owner').eq('owner','{b_id}').then(r=>(r.data||[]).length)")
    T("cannot read someone else's conversation list", r == 0)
    r = A.evaluate(f"dxLive.sb.from('conversation_heads').update({{unread:99}}).eq('owner','{a_id}').then(r=>!!r.error)")
    T('cannot tamper with the conversation summary', r)
    # security
    c_id = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('third{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Third\"}}') returning id").split('\n')[0]
    sql(f"insert into public.messages (sender_id, receiver_id, body) values ('{b_id}','{c_id}','private between Basem and Third')")
    r = A.evaluate(f"dxLive.sb.rpc('conversation_messages',{{p_partner:'{c_id}'}}).then(r=>(r.data||[]).length)")
    r2 = A.evaluate("dxLive.sb.from('messages').select('body').ilike('body','private between%').then(r=>(r.data||[]).length)")
    T("cannot read other people's conversations", r == 0 and r2 == 0, (r, r2))
    r = A.evaluate(f"dxLive.sb.from('messages').insert({{sender_id:'{b_id}',receiver_id:'{a_id}',body:'forged'}}).then(r=>!!r.error)")
    T("cannot send a message in someone else's name", r)
    mid = sql(f"select id from public.messages where sender_id='{b_id}' and receiver_id='{a_id}' order by id desc limit 1")
    r = A.evaluate(f"dxLive.sb.from('messages').update({{body:'edited by receiver'}}).eq('id',{mid}).then(r=>!!r.error)")
    T('the receiver cannot edit a received message', r and sql(f"select body from public.messages where id={mid}").startswith('Sure'))
    mid2 = sql(f"select id from public.messages where sender_id='{a_id}' and receiver_id='{b_id}' order by id desc limit 1")
    sql(f"update public.messages set read_at=null where id={mid2}")
    r = A.evaluate(f"dxLive.sb.from('messages').update({{read_at:new Date().toISOString()}}).eq('id',{mid2}).select().then(r=>(r.data||[]).length)")
    T('the sender cannot fake a read receipt', r == 0 and sql(f"select read_at is null from public.messages where id={mid2}") == 't')
    T('no errors in the page', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
