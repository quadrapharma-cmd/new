"""B4 end-to-end: two people in two browsers — message from a profile, delivery without reload, unread badge, read receipts,
reply arriving live in an open conversation, no demo filler, and row-level security."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(pg, "window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)", 20); pg.wait_for_timeout(2000)
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
    T('no demo conversations or seeded filler messages', 'Vivian' not in demo and 'Allison' not in demo and 'following up on our discussion' not in demo, demo[:200])
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
    # the messages page redefines its functions on every render: sending must still reach the database after a second render
    A.evaluate("goto('feed')"); A.wait_for_timeout(800); A.evaluate("goto('messages')"); A.wait_for_timeout(2000)
    bob = A.evaluate(f"(()=>{{var a=dxLive.aid('{b_id}');if(!USERS.some(u=>u.id===a))USERS.push({{id:a,name:'Dr. Basem Reader',initials:'DB',color:'#1A56DB',headline:'',company:'',verified:false}});return a}})()")   # local ids restart after a reload
    A.evaluate(f"messageUser({bob})"); A.wait_for_timeout(2000)
    A.fill('#composeInput', f'Second render check {st}'); A.evaluate("sendMessage()"); A.wait_for_timeout(1500)
    T('after leaving Messages and coming back, a message is still saved in the database', sql(f"select count(*) from public.messages where sender_id='{a_id}' and receiver_id='{b_id}' and body='Second render check {st}'") == '1')
    r = A.evaluate(f"dxLive.sb.from('conversation_heads').select('owner').eq('owner','{b_id}').then(r=>(r.data||[]).length)")
    T("cannot read someone else's conversation list", r == 0)
    r = A.evaluate(f"dxLive.sb.from('conversation_heads').update({{unread:99}}).eq('owner','{a_id}')" + ERR)
    T('cannot tamper with the conversation summary', refused(r) and sql(f"select count(*) from public.conversation_heads where owner='{a_id}' and unread=99") == '0', r)
    # security
    c_id = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('third{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Third\"}}') returning id").split('\n')[0]
    sql(f"insert into public.messages (sender_id, receiver_id, body) values ('{b_id}','{c_id}','private between Basem and Third')")
    r = A.evaluate(f"dxLive.sb.rpc('conversation_messages',{{p_partner:'{c_id}'}}).then(r=>(r.data||[]).length)")
    r2 = A.evaluate("dxLive.sb.from('messages').select('body').ilike('body','private between%').then(r=>(r.data||[]).length)")
    T("cannot read other people's conversations", r == 0 and r2 == 0, (r, r2))
    r = A.evaluate(f"dxLive.sb.from('messages').insert({{sender_id:'{b_id}',receiver_id:'{a_id}',body:'forged'}})" + ERR)
    T("cannot send a message in someone else's name", r and refused(r) and sql(f"select count(*) from public.messages where body='forged' and sender_id='{b_id}'") == '0', r)
    mid = sql(f"select id from public.messages where sender_id='{b_id}' and receiver_id='{a_id}' order by id desc limit 1")
    r = A.evaluate(f"dxLive.sb.from('messages').update({{body:'edited by receiver'}}).eq('id',{mid})" + ERR)
    T('the receiver cannot edit a received message', refused(r) and sql(f"select body from public.messages where id={mid}").startswith('Sure'), r)
    mid2 = sql(f"select id from public.messages where sender_id='{a_id}' and receiver_id='{b_id}' order by id desc limit 1")
    sql(f"update public.messages set read_at=null where id={mid2}")
    r = A.evaluate(f"dxLive.sb.from('messages').update({{read_at:new Date().toISOString()}}).eq('id',{mid2}).select().then(r=>(r.data||[]).length)")
    T('the sender cannot fake a read receipt', r == 0 and sql(f"select read_at is null from public.messages where id={mid2}") == 't')
    T('no errors in the page', not errs, errs)
    b.close()
done()
