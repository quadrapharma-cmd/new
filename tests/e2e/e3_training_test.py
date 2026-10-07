"""E3 end-to-end: training courses from the database (a course added by Drugbox appears), enrollment is stored and survives a reload,
the count moves by one, and the rules: no enrolling others, no adding courses, enrollments are private."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A, M = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(2)]
    for pg in (A, M): pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    adm = signup(A, 'Drugbox Academy', f'acad{st}@x.test'); m = signup(M, 'Dr. Learner', f'learn{st}@x.test'); sql(f"update public.profiles set role='admin' where id='{adm}'")
    A.reload(wait_until='load'); A.wait_for_timeout(400); A.evaluate('endSplash()'); A.wait_for_timeout(4000)
    r = A.evaluate(f"dxLive.sb.from('training_courses').insert({{title:'Cleaning Validation {st}',description:'Limits, swabbing and recovery studies.',emoji:'🧼',duration:'3 hours',level:'Advanced',sort_order:5}}).select().then(r=>!r.error)")
    T('Drugbox adds a course', r)
    cid = sql(f"select id from public.training_courses where title='Cleaning Validation {st}'")
    M.evaluate("goto('training')"); M.wait_for_timeout(2500)
    titles = M.evaluate("[...document.querySelectorAll('.training-grid .tr-card .tr-title')].map(e=>e.textContent)")
    T('the training page shows the courses from the database, including the new one', f'Cleaning Validation {st}' in titles and 'GMP Fundamentals' in titles, titles[:4])
    card = M.evaluate(f"(()=>{{var c=document.querySelector('.tr-card[data-course=\"{cid}\"]');return c?{{hero:c.querySelector('.tr-hero').textContent,meta:c.querySelector('.tr-meta').innerText}}:null}})()")
    T('the card shows its icon, duration and level', card and card['hero'] == '🧼' and '3 hours' in card['meta'] and 'Advanced' in card['meta'], card)
    before = sql(f"select enrolled_count from public.training_courses where id={cid}")
    M.evaluate(f"document.querySelector('.tr-card[data-course=\"{cid}\"] button').click()"); M.wait_for_timeout(1800)
    T('enrolling is stored', sql(f"select status from public.course_enrollments where course_id={cid} and user_id='{m}'") == 'enrolled')
    T('the enrolled count moves by exactly one', int(sql(f"select enrolled_count from public.training_courses where id={cid}")) == int(before) + 1)
    M.reload(wait_until='load'); M.wait_for_timeout(400); M.evaluate('endSplash()'); M.wait_for_timeout(4000); M.evaluate("goto('training')"); M.wait_for_timeout(2500)
    T('after a reload the course still shows "Enrolled"', '✅ Enrolled' in M.evaluate(f"document.querySelector('.tr-card[data-course=\"{cid}\"] button').textContent"))
    r = M.evaluate(f"dxLive.sb.from('course_enrollments').insert({{course_id:{cid},user_id:'{adm}'}})" + ERR)
    T('cannot enroll someone else', r and refused(r) and sql(f"select count(*) from public.course_enrollments where course_id={cid} and user_id='{adm}'") == '0', r)
    r = M.evaluate(f"dxLive.sb.from('training_courses').insert({{title:'My own course {st}',level:'Beginner'}})" + ERR)
    T('a member cannot add courses', r and refused(r) and sql(f"select count(*) from public.training_courses where title='My own course {st}'") == '0', r)
    r = M.evaluate(f"dxLive.sb.from('course_enrollments').select('user_id').eq('course_id',{cid}).neq('user_id','{m}').then(r=>(r.data||[]).length)")
    sql(f"insert into public.course_enrollments (course_id, user_id) values ({cid},'{adm}')")
    r2 = M.evaluate(f"dxLive.sb.from('course_enrollments').select('user_id').eq('course_id',{cid}).then(r=>(r.data||[]).length)")
    T("other people's enrollments are private", r == 0 and r2 == 1)
    T('no errors in the pages', not errs, errs)
    b.close()
done()
