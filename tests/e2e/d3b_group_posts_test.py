"""D3b end-to-end: inside a group (migration 0027 + adapter D3b + groups.js). A member posts in a public group through the group's
composer (with a photo) and another signed-in member sees it, likes it and comments; the admin pins it; the Home feed never shows
group posts; the discussion pages 20 at a time (keyset) with "Show more posts"; members and About come from the database.
A private group created from the approved window can be found: an outsider cannot read its posts (REST and interface), asks to join,
the admin approves it in Manage → Members & Roles, and the new member reads and posts. A member reports a post and the admin dismisses
the report in Manage → Reports. The outsider's browser runs in Arabic (the inside of a group is translated)."""
from playwright.sync_api import sync_playwright
import json
from _dx import APP_URL as U, R, T, sql, ST, FIXTURES, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'
GP = f'Formulation Club {st}'; GV = f'QPPV Circle {st}'
TOASTS = "[...document.querySelectorAll('.dbk-toast, #toast')].map(t=>t.textContent).join(' | ')"
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn')
    wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(1500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def groups_page(pg, gid):
    pg.evaluate("goto('feed')"); pg.wait_for_timeout(200); pg.evaluate("dxLive.loadGroups().then(()=>1)"); pg.evaluate("goto('groups')")   # fresh rows (the page itself reloads at most every 3 s)
    return wait_for(lambda: pg.evaluate(f"!!document.querySelector('#gx .gcard[data-gid=\"{gid}\"]')"), 12)
def open_group(pg, gid, tab=None):
    """open the group the way its card does; wait until the discussion has loaded (or shows the private-group notice)"""
    click(pg, f'#gx .gcard[data-gid="{gid}"] .gcard-title')
    wait_for(lambda: pg.evaluate("!!document.querySelector('#gpBox [data-pane=disc]') && !/Loading posts|جارٍ تحميل/.test(document.querySelector('#gpBox [data-pane=disc]').textContent)"), 12)
    if tab: click(pg, f'#gpBox [data-gpt={tab}]'); pg.wait_for_timeout(300)
def click(pg, sel, timeout=10):
    """click an element of the interface once it is there (a busy machine draws a little later)"""
    q = json.dumps(sel); wait_for(lambda: pg.evaluate(f"!!document.querySelector({q})"), timeout)
    pg.evaluate(f"document.querySelector({q}).click()")
def post_ids(pg): return pg.evaluate("[...document.querySelectorAll('#gpBox .gp-posts [data-gpp]')].map(e=>+e.dataset.gpp)")
def compose(pg, text, photo=False):
    click(pg, '#gpBox .gp-comp .comp-btn'); pg.wait_for_timeout(300)
    pg.fill('.modal-bg[data-gpk] #postBody', text)
    if photo: pg.set_input_files('.modal-bg[data-gpk] input[onchange*="previewPostImgs"]', FIXTURES + '/photo.png'); pg.wait_for_timeout(300)
    click(pg, '.modal-bg[data-gpk] .btn-p')

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    ctxA, ctxB = [b.new_context(viewport={'width': 1440, 'height': 900}) for _ in range(2)]
    ctxC = b.new_context(viewport={'width': 1440, 'height': 900}); ctxC.add_init_script("try{localStorage.setItem('dx_lang','ar')}catch(e){}")   # the outsider uses Arabic
    A, B, C = ctxA.new_page(), ctxB.new_page(), ctxC.new_page()
    for pg in (A, B, C): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a = signup(A, 'Dr. Group Admin', f'gpa{st}@x.test'); bb = signup(B, 'Dr. Group Poster', f'gpb{st}@x.test'); c = signup(C, 'Dr. Outside Reader', f'gpc{st}@x.test')

    # ── a public group: a member posts through the group's composer, another member sees it ──
    gid = A.evaluate(f"dxLive.sb.from('groups').insert({{name:'{GP}',description:'Semisolids, stability and scale-up.',type:'public',topic:'DISCUSS',created_by:dxLive.uuidOf(ME.id)}}).select().single().then(r=>r.data&&r.data.id)")
    T('a public group is created (its creator is its admin)', gid and sql(f"select role from public.group_members where group_id={gid} and user_id='{a}'") == 'admin')
    groups_page(B, gid)
    T('the card of a public group offers "+ Join"', '+ Join' in B.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{gid}\"] .gcard-btn').textContent"))
    open_group(B, gid)
    T('a non-member sees a read-only preview: Join, no composer', B.evaluate("!!document.querySelector('#gpBox [data-gpa=join]') && !document.querySelector('#gpBox .gp-comp')"))
    T('the header offers "+ Join Group" to a non-member', '+ Join Group' in B.evaluate("document.querySelector('#memberActions [data-dxj]') ? document.querySelector('#memberActions [data-dxj]').textContent : ''"))
    click(B, '#gpBox [data-gpa=join]')
    wait_for(lambda: sql(f"select count(*) from public.group_members where group_id={gid} and user_id='{bb}'") == '1', 10)
    T('Join inside the group makes a membership (group_request_join)', sql(f"select role from public.group_members where group_id={gid} and user_id='{bb}'") == 'member')
    wait_for(lambda: B.evaluate("!!document.querySelector('#gpBox .gp-comp')"), 8)
    T('…and the composer appears; the card says ✓ Joined; the header offers Leave', B.evaluate("!!document.querySelector('#gpBox .gp-comp')")
      and '✓ Joined' in B.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{gid}\"] .gcard-btn').textContent")
      and 'Leave' in B.evaluate("document.querySelector('#memberActions .btn-leave') ? document.querySelector('#memberActions .btn-leave').textContent : ''"))
    body1 = f'Which HPMC grade do you use for a 12-hour matrix? {st}'
    compose(B, body1, photo=True)
    wait_for(lambda: sql(f"select count(*) from public.posts where group_id={gid} and body='{body1}'") == '1', 15)
    pid = sql(f"select id from public.posts where group_id={gid} and body='{body1}'")
    T('the post is saved IN the group (posts.group_id) by its author', pid != '' and sql(f"select user_id from public.posts where id={pid}") == bb)
    wait_for(lambda: sql(f"select count(*) from public.post_media where post_id={pid}") == '1', 10)
    T('its photo goes through the post-media path (post_media row, public URL)', sql(f"select type||'|'||(url like '%/post-media/posts/{bb}/{pid}-%')::text from public.post_media where post_id={pid}") == 'image|true')
    T('it shows at the top of the discussion', wait_for(lambda: (post_ids(B) or [0])[0] == int(pid), 8), post_ids(B))
    groups_page(A, gid); open_group(A, gid)
    T('another member sees the post, with its photo', int(pid) in post_ids(A) and A.evaluate(f"!!document.querySelector('#gpBox [data-gpp=\"{pid}\"] .post-imgs img')"))
    # like + comment through the post card
    click(A, f'#gpBox [data-gpp="{pid}"] .pact[id^=like-]')
    wait_for(lambda: sql(f"select count(*) from public.reactions where post_id={pid} and user_id='{a}'") == '1', 8)
    T('Like on a group post is a reaction row', sql(f"select kind from public.reactions where post_id={pid} and user_id='{a}'") == 'like')
    click(A, f'#gpBox [data-gpp="{pid}"] [data-gpm=cmts]'); A.wait_for_timeout(200)
    A.fill(f'#gpBox [data-gpp="{pid}"] .cmt-input', 'HPMC K100M at 30% — dissolution looked good.'); A.press(f'#gpBox [data-gpp="{pid}"] .cmt-input', 'Enter')
    wait_for(lambda: sql(f"select count(*) from public.comments where post_id={pid}") == '1', 8)
    T('a comment on a group post is a comment row', sql(f"select user_id from public.comments where post_id={pid}") == a)
    # the author sees the like and the comment on the next visit
    groups_page(B, gid); open_group(B, gid)
    T("the author sees the other member's like and comment", B.evaluate(f"(()=>{{var e=document.querySelector('#gpBox [data-gpp=\"{pid}\"]');var st=e&&e.querySelector('.post-stats [data-sr]');return !!e && /HPMC K100M/.test(e.textContent) && !!st && st.textContent.trim().endsWith('1') && (e.querySelector('.post-stats [data-tc]')||{{}}).textContent==='1 comments'}})()"),
      B.evaluate(f"(document.querySelector('#gpBox [data-gpp=\"{pid}\"] .post-stats')||{{}}).textContent"))
    # the author saves, edits and reposts it to the Home feed (a public group's post)
    click(B, f'#gpBox [data-gpp="{pid}"] .post-acts [data-gpm=save]')
    T('Save on a group post is a saved_posts row', wait_for(lambda: sql(f"select count(*) from public.saved_posts where post_id={pid} and user_id='{bb}'") == '1', 8))
    click(B, f'#gpBox [data-gpp="{pid}"] [data-gpm=edit]'); B.wait_for_timeout(300)
    B.fill('.dbk-box #gpEd', body1 + ' (edited)'); click(B, '.dbk-box [data-a=ok]')
    T('the author edits the post', wait_for(lambda: sql(f"select body from public.posts where id={pid}") == body1 + ' (edited)', 8))
    click(B, f'#gpBox [data-gpp="{pid}"] .post-acts [data-gpm=share]'); B.wait_for_timeout(300)
    click(B, '.dbk-box [data-so=feed]')
    T('"Repost to your feed" makes a Home post that names the group', wait_for(lambda: sql(f"select count(*) from public.posts where user_id='{bb}' and group_id is null and body like 'Shared from {GP} — %'") == '1', 8))
    # the admin pins it (one pinned post per group)
    click(A, f'#gpBox [data-gpp="{pid}"] [data-gpm=pin]')
    wait_for(lambda: sql(f"select coalesce(pinned_post_id::text,'') from public.groups where id={gid}") == pid, 8)
    T('the admin pins the post (groups.pinned_post_id)', sql(f"select pinned_post_id from public.groups where id={gid}") == pid)
    r = B.evaluate(f"dxLive.sb.rpc('group_pin_post',{{p_group:{gid},p_post:null}})" + ERR)
    T('a plain member cannot unpin it', refused(r) and r is not None and sql(f"select pinned_post_id from public.groups where id={gid}") == pid, r)

    # ── the Home feed never shows group posts ──
    B.evaluate("goto('feed')"); B.wait_for_timeout(200)
    B.evaluate("dxLive.loadFeed(true)"); B.wait_for_timeout(1500)
    T('the Home feed does not list the group post', not B.evaluate(f"POSTS.some(p=>p.id==={pid})") and not B.evaluate(f"!!document.getElementById('post-{pid}')"))
    r = B.evaluate(f"dxLive.sb.from('posts').select('id').is('group_id',null).eq('id',{pid}).then(r=>(r.data||[]).length)")
    T("…and the feed's own query (group_id is null) leaves it out", r == 0)

    # ── paging: 20 at a time, keyset ──
    sql(f"update public.posts set created_at = now() - interval '3 days' where id={pid}")   # the pinned post is older than a page: it still comes first
    sql(f"insert into public.posts (user_id, body, category, group_id, created_at) select '{bb}', 'Older note '||g, 'general', {gid}, now() - (g||' hours')::interval from generate_series(1,25) g")
    groups_page(B, gid); open_group(B, gid)
    first = post_ids(B)
    T('the first page shows 20 posts plus the pinned one, the pinned first', len(first) == 21 and first[0] == int(pid), (len(first), first[:2]))
    T('"Show more posts" is offered', B.evaluate("!!document.querySelector('#gpBox .gp-loadmore')"))
    click(B, '#gpBox .gp-loadmore')
    wait_for(lambda: len(post_ids(B)) >= 26, 10)
    allp = post_ids(B)
    T('the next page adds the rest, with no post twice and the pinned post once', len(allp) == 26 and len(set(allp)) == 26 and allp.count(int(pid)) == 1, len(allp))
    T('…and nothing more is offered at the end', wait_for(lambda: not B.evaluate("!!document.querySelector('#gpBox .gp-loadmore')"), 5))

    # ── members and About ──
    click(B, '#gpBox [data-gpt=members]')
    wait_for(lambda: B.evaluate("document.querySelectorAll('#gpBox [data-pane=members] .member-row').length") >= 2, 8)
    T('Members lists the real members, the admin marked', B.evaluate("(()=>{var t=document.querySelector('#gpBox [data-pane=members]').textContent;return /Dr\\. Group Admin/.test(t)&&/Dr\\. Group Poster/.test(t)&&/Admin/.test(t)})()"))
    T('Members shows no phone numbers or other private fields', not B.evaluate("/@x\\.test/.test(document.querySelector('#gpBox [data-pane=members]').textContent)"))

    # ── a report from a member, answered by the admin ──
    r = B.evaluate(f"dxLive.sb.from('group_post_reports').insert({{post_id:{pid},reporter:dxLive.uuidOf(ME.id),reason:'Breaks the group rules'}})" + ERR)
    T('a member reports a group post to its admins', r is None and sql(f"select status from public.group_post_reports where post_id={pid}") == 'open', r)
    groups_page(A, gid); open_group(A, gid)
    A.evaluate("toggleManage()"); A.wait_for_timeout(200)
    A.evaluate("document.querySelectorAll('#managePanel .panel-tabs .gx-ptab')[1].click()")
    wait_for(lambda: A.evaluate(f"!!document.querySelector('#tab-reports [data-rpost=\"{pid}\"]')"), 8)
    T('the admin sees it in Manage → Reports', A.evaluate(f"!!document.querySelector('#tab-reports [data-rpost=\"{pid}\"]')"))
    click(A, f'#tab-reports [data-rpost="{pid}"] [data-dxrep=dismiss]')
    wait_for(lambda: sql(f"select status from public.group_post_reports where post_id={pid}") == 'dismissed', 8)
    T('Dismiss report updates the report', sql(f"select status from public.group_post_reports where post_id={pid}") == 'dismissed')
    # roles: the admin promotes a member in Manage → Members & Roles and demotes them again
    A.evaluate("document.querySelectorAll('#managePanel .panel-tabs .gx-ptab')[0].click()")
    ROW = "[...document.querySelectorAll('#tab-members .member-list .member-row')].find(r=>/Dr\\. Group Poster/.test(r.textContent))"
    def role_click(op):
        wait_for(lambda: A.evaluate(f"!!({ROW}) && !!({ROW}).querySelector('[data-gpd={op}]')"), 10)
        A.evaluate(f"({ROW}).querySelector('[data-gpd={op}]').click()")
    role_click('admin')
    T('Promote to Admin changes the role in the database', wait_for(lambda: sql(f"select role from public.group_members where group_id={gid} and user_id='{bb}'") == 'admin', 8))
    role_click('member')
    T('…and Demote to Member changes it back', wait_for(lambda: sql(f"select role from public.group_members where group_id={gid} and user_id='{bb}'") == 'member', 8))
    r = B.evaluate(f"dxLive.sb.from('group_members').update({{role:'admin'}}).eq('group_id',{gid}).eq('user_id',dxLive.uuidOf(ME.id)).select().then(r=>(r.data||[]).length)")
    T('a member cannot make themself an admin', r == 0 and sql(f"select role from public.group_members where group_id={gid} and user_id='{bb}'") == 'member', r)
    # settings: rules become the About tab
    A.evaluate("document.querySelectorAll('#managePanel .panel-tabs .gx-ptab')[2].click()"); A.wait_for_timeout(200)
    A.fill('#tab-settings .dx-rules', 'Cite your source: name the pharmacopoeia or the paper\nNo selling: offers go in messages')
    click(A, '#tab-settings .btn-create')
    wait_for(lambda: sql(f"select coalesce(rules,'') from public.groups where id={gid}").startswith('Cite your source'), 8)
    T('the admin saves the rules (groups.rules)', sql(f"select coalesce(rules,'') from public.groups where id={gid}").startswith('Cite your source'))
    groups_page(B, gid); open_group(B, gid, 'about')
    T('About shows the description and the rules from the database', B.evaluate("(()=>{var t=document.querySelector('#gpBox [data-pane=about]').textContent;return /Semisolids, stability/.test(t)&&/Cite your source/.test(t)&&/No selling/.test(t)})()"),
      B.evaluate("document.querySelector('#gpBox [data-pane=about]').textContent.slice(0,300)"))

    # ── a private group: found, closed to outsiders, request → approval → posting ──
    groups_page(A, gid); A.evaluate("openCreate()"); A.wait_for_timeout(300)
    A.fill('#createModal input[placeholder^="e.g. Sterile"]', GV); A.fill('#createModal textarea', 'QPPVs and deputies compare PSUR timelines.')
    A.evaluate("document.querySelectorAll('#createModal .privacy-opt')[1].click()")
    A.evaluate("(()=>{var b=[...document.querySelectorAll('#createModal button')].find(x=>/create/i.test(x.textContent)&&!/cancel/i.test(x.textContent));b&&b.click()})()")
    wait_for(lambda: sql(f"select count(*) from public.groups where name='{GV}'") == '1', 10)
    vid = sql(f"select id from public.groups where name='{GV}'")
    T('a private group made in the window is hidden from the list (private, unlisted — J-COMMUNITY-12)', sql(f"select type||'|'||listed from public.groups where id={vid}") == 'private|false')
    sql(f"update public.groups set listed=true where id={vid}")   # setup for the request flow below: a listed private group (as the seeded ones)
    groups_page(A, vid); open_group(A, vid)
    secret = f'PSUR due dates moved for our portfolio {st}'
    compose(A, secret)
    wait_for(lambda: sql(f"select count(*) from public.posts where group_id={vid}") == '1', 10)
    vpid = sql(f"select id from public.posts where group_id={vid}")
    T('the admin posts in the private group', vpid != '')
    groups_page(C, vid)
    T('an outsider sees the card with "🔒 Request" (Arabic: اطلب الانضمام)', 'اطلب الانضمام' in C.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{vid}\"] .gcard-btn').textContent"),
      C.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{vid}\"] .gcard-btn').textContent"))
    r = C.evaluate(f"dxLive.sb.from('posts').select('id,body').eq('group_id',{vid}).then(r=>({{n:(r.data||[]).length,e:r.error&&r.error.message}}))")
    T("an outsider cannot read the private group's posts (REST)", r['n'] == 0 and not r['e'], r)
    r = C.evaluate(f"dxLive.sb.from('posts').select('id').eq('id',{vpid}).then(r=>(r.data||[]).length)")
    T('…not even by its id', r == 0)
    r = C.evaluate(f"dxLive.sb.from('comments').select('id').eq('post_id',{vpid}).then(r=>(r.data||[]).length)")
    T('…nor its comments', r == 0)
    r = C.evaluate(f"dxLive.sb.from('posts').insert({{user_id:dxLive.uuidOf(ME.id),body:'sneaking in',group_id:{vid}}})" + ERR)
    T('an outsider cannot post in it', refused(r) and r is not None and sql(f"select count(*) from public.posts where group_id={vid}") == '1', r)
    r = C.evaluate(f"dxLive.sb.from('group_members').select('user_id').eq('group_id',{vid}).then(r=>(r.data||[]).length)")
    T('…nor list its members', r == 0)
    open_group(C, vid)
    T('the interface shows the private-group notice in Arabic, no posts, no composer',
      C.evaluate("(()=>{var b=document.getElementById('gpBox');return /هذه مجموعة خاصة/.test(b.textContent)&&!b.querySelector('.post')&&!b.querySelector('.gp-comp')})()")
      and secret not in C.evaluate("document.getElementById('gpBox').textContent"),
      C.evaluate("(()=>{var b=document.getElementById('gpBox');return [/هذه مجموعة خاصة/.test(b.textContent),!!b.querySelector('.post'),!!b.querySelector('.gp-comp'),b.querySelector('.post')&&b.querySelector('.post').outerHTML.slice(0,200)]})()"))
    T('the group tabs are in Arabic', C.evaluate("(()=>{var t=[...document.querySelectorAll('#gpBox [data-gpt]')].map(x=>x.textContent).join(' ');return /نقاش|النقاش/.test(t)&&/الأعضاء/.test(t)&&!/Discussion|Members/.test(t)})()"),
      C.evaluate("[...document.querySelectorAll('#gpBox [data-gpt]')].map(x=>x.textContent).join(' | ')"))
    click(C, '#gpBox [data-gpa=request]')
    wait_for(lambda: sql(f"select count(*) from public.group_join_requests where group_id={vid} and user_id='{c}'") == '1', 10)
    T('Request to join files a pending request', sql(f"select status from public.group_join_requests where group_id={vid} and user_id='{c}'") == 'pending')
    T('…the card and the group say the request was sent (Arabic)', wait_for(lambda: 'تم الطلب' in C.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{vid}\"] .gcard-btn').textContent")
      and C.evaluate("!!document.querySelector('#gpBox [data-gpa=cancel]')"), 6), C.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{vid}\"] .gcard-btn').textContent"))
    T("the admin is notified (group_join_request)", sql(f"select count(*) from public.notifications where user_id='{a}' and type='group_join_request' and group_id={vid} and from_user='{c}'") == '1')
    r = C.evaluate("dxT('asked to join the private group \"X\"')")
    T('the notice reads in Arabic too', r == 'طلب الانضمام إلى المجموعة الخاصة "X"', r)
    r = C.evaluate(f"dxLive.sb.rpc('group_decide_request',{{p_group:{vid},p_user:dxLive.uuidOf(ME.id),p_approve:true}})" + ERR)
    T('the requester cannot approve themself', refused(r) and r is not None and sql(f"select count(*) from public.group_members where group_id={vid} and user_id='{c}'") == '0', r)
    groups_page(A, vid); open_group(A, vid)
    A.evaluate("toggleManage()")
    click(A, '#managePanel [data-gpq-tab]'); A.wait_for_timeout(400)   # join requests have their own tab in Manage (G-xx, J-COMMUNITY-10)
    wait_for(lambda: A.evaluate("!!document.querySelector('#tab-requests [data-req]')"), 8)
    T('the admin sees the request in Manage → Requests', 'Dr. Outside Reader' in A.evaluate("(document.querySelector('#tab-requests')||{}).textContent||''"))
    T('…the Manage panel lists the real members, not sample people', A.evaluate("(()=>{var t=document.querySelector('#tab-members .member-list').textContent;return /Dr\\. Group Admin/.test(t)&&!/Alia Mourad|Vivian Zhou/.test(t)})()"))
    click(A, '#tab-requests [data-dxreq=approve]')
    wait_for(lambda: sql(f"select count(*) from public.group_members where group_id={vid} and user_id='{c}'") == '1', 10)
    T('Approve makes the requester a member', sql(f"select role from public.group_members where group_id={vid} and user_id='{c}'") == 'member'
      and sql(f"select status from public.group_join_requests where group_id={vid} and user_id='{c}'") == 'approved')
    T('…and tells them (group_join_approved)', sql(f"select count(*) from public.notifications where user_id='{c}' and type='group_join_approved' and group_id={vid}") == '1')
    groups_page(C, vid)
    T("the new member's card says joined", wait_for(lambda: '✓' in C.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{vid}\"] .gcard-btn').textContent"), 6))
    open_group(C, vid)
    T('the new member reads the private discussion', wait_for(lambda: int(vpid) in post_ids(C), 8) and secret in C.evaluate("document.getElementById('gpBox').textContent"))
    reply = f'Ours moved too — the PBRER cycle is now 6 months {st}'
    compose(C, reply)
    wait_for(lambda: sql(f"select count(*) from public.posts where group_id={vid} and user_id='{c}'") == '1', 10)
    T('…and posts in it (Arabic interface)', sql(f"select body from public.posts where group_id={vid} and user_id='{c}'") == reply)
    click(C, '#gpBox [data-gpt=members]')
    T('Members of the private group are visible to its new member', wait_for(lambda: C.evaluate("document.querySelectorAll('#gpBox [data-pane=members] .member-row').length") >= 2, 8))
    # the outsider who never joined (B) still cannot read it
    r = B.evaluate(f"dxLive.sb.from('posts').select('id').eq('group_id',{vid}).then(r=>(r.data||[]).length)")
    T('a member of another group still cannot read the private group', r == 0)
    # leaving closes it again
    C.evaluate("toggleLeaveConfirm()"); C.wait_for_timeout(200); click(C, '#leaveConfirm .cp-btn-confirm')
    wait_for(lambda: sql(f"select count(*) from public.group_members where group_id={vid} and user_id='{c}'") == '0', 8)
    r = C.evaluate(f"dxLive.sb.from('posts').select('id').eq('group_id',{vid}).then(r=>(r.data||[]).length)")
    T('after leaving, the private posts are closed again (own post aside)', sql(f"select count(*) from public.group_members where group_id={vid} and user_id='{c}'") == '0' and r == 1, r)

    # ── the admin removes a post that breaks the rules ──
    groups_page(A, gid); open_group(A, gid)
    click(A, f'#gpBox [data-gpp="{pid}"] [data-gpm=remove]'); A.wait_for_timeout(300)
    click(A, '.dbk-box [data-a=ok]')
    wait_for(lambda: sql(f"select count(*) from public.posts where id={pid}") == '0', 20)
    T('the admin removes a member’s post from the group (after the Undo window)', sql(f"select count(*) from public.posts where id={pid}") == '0'
      and sql(f"select coalesce(pinned_post_id::text,'none') from public.groups where id={gid}") == 'none')
    T('no errors in the pages', not errs, errs)
    b.close()
done()
