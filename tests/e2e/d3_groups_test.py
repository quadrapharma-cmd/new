"""D3 end-to-end: groups from the database — create through the window (creator becomes admin), another member joins with the card button,
opens the real group detail, leaves; security on roles, private groups and deletion; the creator deletes the group."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'; G = f'Sterile Manufacturing {st}'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A, B = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(2)]
    for pg in (A, B): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a = signup(A, 'Dr. Group Creator', f'gcre{st}@x.test'); bb = signup(B, 'Dr. Group Member', f'gmem{st}@x.test')
    A.evaluate("goto('groups')"); A.wait_for_timeout(2500)
    T('the groups page shows real groups, not the demo ones', not A.evaluate("[...document.querySelectorAll('#gx .gcard-title')].some(t=>t.textContent==='API Sourcing & Supply')"))
    A.evaluate("openCreate()"); A.wait_for_timeout(400)
    A.fill('#createModal input[placeholder^="e.g. Sterile"]', G); A.fill('#createModal textarea', 'Aseptic processing, media fills and Annex 1 readiness.')
    A.evaluate("(()=>{var b=[...document.querySelectorAll('#createModal button')].find(x=>/create/i.test(x.textContent)&&!/cancel/i.test(x.textContent));b&&b.click()})()"); A.wait_for_timeout(2500)
    gid = sql(f"select id from public.groups where name='{G}'")
    T('creating through the window saves the group', gid != '')
    T('the creator becomes its admin; member count 1', sql(f"select role from public.group_members where group_id={gid} and user_id='{a}'") == 'admin' and sql(f"select member_count from public.groups where id={gid}") == '1')
    T('the new group appears as a card', A.evaluate(f"!!document.querySelector('#gx .gcard[data-gid=\"{gid}\"]')"))
    B.evaluate("goto('groups')"); B.wait_for_timeout(3000)
    B.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{gid}\"] .gcard-btn').click()"); B.wait_for_timeout(2000)
    T('another member joins with the card button', sql(f"select role from public.group_members where group_id={gid} and user_id='{bb}'") == 'member')
    T('the database counts 2 members', sql(f"select member_count from public.groups where id={gid}") == '2')
    T('the card shows "✓ Joined"', '✓ Joined' in B.evaluate(f"document.querySelector('#gx .gcard[data-gid=\"{gid}\"] .gcard-btn').textContent"))
    B.evaluate(f"dxLive.openGroup({gid})"); B.wait_for_timeout(700)
    T('the group detail shows THIS group', B.evaluate("document.getElementById('dt-title').textContent") == G and '2' in B.evaluate("document.querySelector('#groupDetail .group-meta-stats').innerText"))
    T('a member sees member actions, not admin tools', B.evaluate("getComputedStyle(document.getElementById('adminActions')).display") == 'none')
    B.evaluate("toggleLeaveConfirm()"); B.wait_for_timeout(300); B.evaluate("document.querySelector('#leaveConfirm .cp-btn-confirm').click()"); B.wait_for_timeout(2000)
    T('leaving removes the membership', sql(f"select count(*) from public.group_members where group_id={gid} and user_id='{bb}'") == '0')
    r = B.evaluate(f"dxLive.sb.from('group_members').insert({{group_id:{gid},user_id:'{bb}',role:'admin'}})" + ERR)
    T('cannot join as an admin', refused(r) and sql(f"select count(*) from public.group_members where group_id={gid} and user_id='{bb}' and role='admin'") == '0', r)
    pid = sql(f"insert into public.groups (name, description, type, created_by) values ('Private room {st}','Invite only','private','{a}') returning id").split('\n')[0]
    r = B.evaluate(f"dxLive.sb.from('group_members').insert({{group_id:{pid},user_id:'{bb}',role:'member'}})" + ERR)
    T('cannot join a private group without an invitation', refused(r) and sql(f"select count(*) from public.group_members where group_id={pid} and user_id='{bb}'") == '0', r)
    r = B.evaluate(f"dxLive.sb.from('group_members').select('user_id').eq('group_id',{pid}).then(r=>(r.data||[]).length)")
    T("a private group's members are hidden from outsiders", r == 0)
    r = B.evaluate(f"dxLive.sb.from('groups').delete().eq('id',{gid}).select().then(r=>(r.data||[]).length)")
    T("cannot delete someone else's group", r == 0 and sql(f"select count(*) from public.groups where id={gid}") == '1')
    A.evaluate("goto('feed')"); A.wait_for_timeout(300); A.evaluate("goto('groups')"); A.wait_for_timeout(2500)
    A.evaluate(f"dxLive.openGroup({gid})"); A.wait_for_timeout(500)
    T('the creator sees admin tools', A.evaluate("getComputedStyle(document.getElementById('adminActions')).display") != 'none')
    A.evaluate("openDelete()"); A.wait_for_timeout(300); A.fill('#deleteConfirmInput', G); A.evaluate("document.getElementById('deleteConfirmBtn').disabled=false;document.getElementById('deleteConfirmBtn').click()"); A.wait_for_timeout(2000)
    T('the creator deletes the group (typed name confirmed)', sql(f"select count(*) from public.groups where id={gid}") == '0')
    T('no errors in the pages', not errs, errs)
    b.close()
done()
