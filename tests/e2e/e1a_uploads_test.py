"""E1a end-to-end: a post with a photo and a PDF (public storage), a message with a photo and a PDF (private storage, signed links),
and the storage/row rules for an outsider."""
from playwright.sync_api import sync_playwright
import subprocess, time, os, urllib.request
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py
V = FIXTURES
def http(u):
    try: return urllib.request.urlopen(u, timeout=5).status
    except Exception as e: return getattr(e, 'code', 0)
st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A, B, C = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(3)]
    for pg in (A, B, C): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a = signup(A, 'Dr. Upload Author', f'upa{st}@x.test'); bb = signup(B, 'Dr. Upload Reader', f'upb{st}@x.test'); c = signup(C, 'Dr. Outsider', f'upc{st}@x.test')
    # a post with a photo and a PDF
    A.evaluate("showPostModal()"); A.wait_for_timeout(400)
    A.fill('#postBody', f'New CoA format and line photo {st}')
    A.set_input_files('input[onchange*="previewPostImgs"]', V + '/photo.png'); A.wait_for_timeout(300)
    A.set_input_files('input[onchange*="previewPostFile"]', V + '/spec.pdf'); A.wait_for_timeout(300)
    A.evaluate("submitPost()"); A.wait_for_timeout(4000)
    pid = sql(f"select id from public.posts where body='New CoA format and line photo {st}'")
    media = sql(f"select string_agg(type||':'||name,',' order by type) from public.post_media where post_id={pid}")
    T('the post is saved with its photo and its PDF', media == 'file:spec.pdf,image:photo', media)
    url = sql(f"select url from public.post_media where post_id={pid} and type='image'")
    T('the photo is publicly reachable from storage', http(url) == 200, url)
    B.evaluate("goto('feed')"); B.wait_for_timeout(500); B.reload(wait_until='load'); B.wait_for_timeout(400); B.evaluate('endSplash()'); B.wait_for_timeout(4000)
    shown = B.evaluate(f"(()=>{{var p=document.getElementById('post-{pid}');if(!p)return null;var i=p.querySelector('img[src*=\"/post-media/\"]');return {{img:!!i,loaded:i?i.complete&&i.naturalWidth>0:false,file:p.innerText.indexOf('spec.pdf')>=0}}}})()")
    T('another member sees the photo (loaded) and the file in the post', shown and shown['img'] and shown['loaded'] and shown['file'], shown)
    # a private message with a photo and a PDF
    A.evaluate(f"(()=>{{var x=dxLive.aid('{bb}');USERS.push({{id:x,name:'Dr. Upload Reader',initials:'DU',color:'#1A56DB'}});messageUser(x)}})()"); A.wait_for_timeout(2500)
    A.set_input_files('input[onchange*="handleAttach"][onchange*="photo"]', V + '/photo.png'); A.wait_for_timeout(300)
    A.set_input_files('input[onchange*="handleAttach"]:not([onchange*="photo"])', V + '/spec.pdf'); A.wait_for_timeout(300)
    A.fill('#composeInput', 'Photo of the label and the spec'); A.evaluate("sendMessage()"); A.wait_for_timeout(4000)
    rows = sql(f"select string_agg((attachment->>'kind')||':'||(attachment->>'name'),',' order by id) from public.messages where sender_id='{a}' and receiver_id='{bb}'")
    T('the message carries the photo and the PDF', rows == 'photo:photo.png,file:spec.pdf', rows)
    path = sql(f"select attachment->>'path' from public.messages where sender_id='{a}' and attachment->>'kind'='photo'")
    T('message files are stored privately (no public link)', http(f"{U.rstrip('/')}/storage/v1/object/public/message-media/{path}") == 404)
    B.evaluate("goto('messages')"); B.wait_for_timeout(4000)
    got = B.evaluate("(()=>{var i=document.querySelector('#messagesArea img.msg-image');var f=document.querySelector('#messagesArea a.dx-msg-file');return {img:!!i&&/\\/object\\/sign\\//.test(i.src),loaded:i?i.complete&&i.naturalWidth>0:false,file:f?/\\/object\\/sign\\//.test(f.href):false}})()")
    T('the receiver sees the photo and the file through signed links', got['img'] and got['loaded'] and got['file'], got)
    r = C.evaluate(f"dxLive.sb.storage.from('message-media').createSignedUrl('{path}',60)" + ERR)
    ok_owner = B.evaluate(f"dxLive.sb.storage.from('message-media').createSignedUrl('{path}',60).then(r=>!r.error)")
    T('an outsider cannot get a link to a private message file (the receiver can)', r and refused(r) and ok_owner, (r, ok_owner))
    r = C.evaluate(f"dxLive.sb.storage.from('message-media').upload('{a}/{c}/x.png', new Blob([new Uint8Array(8)],{{type:'image/png'}}))" + ERR)
    T("cannot upload into someone else's message folder", r and refused(r) and sql(f"select count(*) from storage.objects where bucket_id='message-media' and name='{a}/{c}/x.png'") == '0', r)
    r = C.evaluate(f"dxLive.sb.storage.from('post-media').upload('posts/{a}/x.png', new Blob([new Uint8Array(8)],{{type:'image/png'}}))" + ERR)
    T("cannot upload into someone else's post folder", r and refused(r) and sql(f"select count(*) from storage.objects where bucket_id='post-media' and name='posts/{a}/x.png'") == '0', r)
    r = C.evaluate(f"dxLive.sb.from('post_media').insert({{post_id:{pid},url:'https://evil.example/x.png',type:'image',name:'x',size:1}})" + ERR)
    T("cannot attach media to someone else's post", r and refused(r) and sql(f"select count(*) from public.post_media where post_id={pid} and url like 'https://evil.example%'") == '0', r)
    r = C.evaluate(f"dxLive.sb.from('messages').insert({{sender_id:'{c}',receiver_id:'{bb}',body:'x',attachment:{{path:'{path}',name:'stolen.png',size:1,kind:'photo'}}}})" + ERR)
    T("cannot point a message at someone else's file", r and refused(r) and sql(f"select count(*) from public.messages where sender_id='{c}' and attachment->>'name'='stolen.png'") == '0', r)
    T('no errors in the pages', not errs, errs)
    b.close()
done()
