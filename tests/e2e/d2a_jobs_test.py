"""D2a end-to-end: jobs page from the database — an employer posts through the real form (as its company), a candidate sees it,
filters work on real cards, apply (once only), save; no demo jobs; row-level security."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:220]))
def sql(q):
    r = subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-v', 'ON_ERROR_STOP=1', '-c', q], capture_output=True, text=True)
    if r.returncode: raise SystemExit('SQL failed: ' + r.stderr.strip()[:300])
    return r.stdout.strip()
st = int(time.time()); PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(3500)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    E, C = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(2)]
    for pg in (E, C): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    e = signup(E, 'Dr. Hiring Manager', f'hire{st}@x.test'); c = signup(C, 'Dr. Job Seeker', f'seek{st}@x.test')
    SE = f'hiring-pharma-{st}'
    sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{e}','Hiring Pharma {st}','{SE}','Manufacturer','verified','{{Manufacturer}}')")
    E.evaluate(f"localStorage.setItem('dx_acting', JSON.stringify('{SE}'))"); E.reload(wait_until='load'); E.wait_for_timeout(400); E.evaluate('endSplash()'); E.wait_for_timeout(4500)
    E.evaluate("goto('jobs')"); E.wait_for_timeout(2500)
    E.evaluate("openPostJobModal()"); E.wait_for_timeout(500)
    T('the post-job form shows my company (not the demo "Quadra Pharm")', E.evaluate("document.querySelector('#postJobModal input[disabled]').value") == f'Hiring Pharma {st}')
    m = '#postJobModal '
    E.fill(m + 'input[placeholder^="e.g. Senior"]', f'QA Validation Specialist {st}'); E.fill(m + 'input[placeholder="Giza, Egypt"]', '10th of Ramadan, Egypt'); E.fill(m + 'input[placeholder="3-5 years"]', '6')
    opts = E.evaluate(f"[...document.querySelectorAll('{m}select option')].map(o=>o.textContent)"); qa = next((o for o in opts if 'QA' in o or 'Quality' in o), None)
    if qa: E.select_option(m + 'select', label=qa)
    E.fill(m + 'input[placeholder^="Min"]', '30,000 EGP'); E.fill(m + 'textarea', 'Process and cleaning validation for a WHO-GMP solid dosage plant.')
    E.evaluate("(()=>{var b=[...document.querySelectorAll('#postJobModal button')].find(x=>/post/i.test(x.textContent));b&&b.click()})()"); E.wait_for_timeout(2500)
    row = sql(f"select company||'|'||category||'|'||seniority||'|'||coalesce(salary,'') from public.jobs where title='QA Validation Specialist {st}'")
    T('posting saves the job under my company, with category and level', row == f'Hiring Pharma {st}|qaqc|senior|30,000 EGP', (row, opts))
    jid = sql(f"select id from public.jobs where title='QA Validation Specialist {st}'")
    C.evaluate("goto('jobs')"); C.wait_for_timeout(3500)
    titles = C.evaluate("[...document.querySelectorAll('#jx .jcard .jc-title')].map(t=>t.textContent)")
    T('the candidate sees the real job (and no demo jobs)', any(f'QA Validation Specialist {st}' in t for t in titles) and not any('Senior Regulatory Affairs Specialist' == t.split('Mgmt')[-1] for t in titles), titles[:3])
    card = C.evaluate(f"(()=>{{var c=document.querySelector('#jx [data-live=\"j{jid}\"]');return c?{{cat:c.dataset.cat,level:c.dataset.level,co:c.querySelector('.jc-company').innerText,lvl:c.querySelector('.level-badge').textContent}}:null}})()")
    T('the card carries category, level badge and company', card and card['cat'] == 'qaqc' and card['level'] == 'senior' and 'Senior Mgmt' in card['lvl'] and f'Hiring Pharma {st}' in card['co'], card)
    C.evaluate("(()=>{var t=[...document.querySelectorAll('#jx .cf-tag, #jx [data-cat]')].find(x=>/Regulatory/.test(x.textContent)&&!x.classList.contains('jcard'));t&&t.click()})()"); C.wait_for_timeout(600)
    T('the Regulatory filter hides the QA job (filters work on real cards)', not C.evaluate(f"(()=>{{var c=document.querySelector('#jx [data-live=\"j{jid}\"]');return c&&c.offsetWidth>0}})()"))
    C.evaluate("(()=>{var t=[...document.querySelectorAll('#jx .cf-tag')].find(x=>/All Jobs/.test(x.textContent));t&&t.click()})()"); C.wait_for_timeout(600)
    C.evaluate(f"document.querySelector('#jx [data-live=\"j{jid}\"] .apply-btn').click()"); C.wait_for_timeout(500)
    C.fill('#applyModal textarea', 'Eight years of process validation, WHO-GMP audits.'); C.evaluate("submitApply()"); C.wait_for_timeout(2000)
    T('applying saves the application with the note', sql(f"select status||'|'||note from public.job_applications where job_id={jid} and user_id='{c}'") == 'submitted|Eight years of process validation, WHO-GMP audits.')
    T('the database counts the applicant', sql(f"select applicant_count from public.jobs where id={jid}") == '1')
    T('the button shows "Applied"', '✓ Applied' in C.evaluate(f"document.querySelector('#jx [data-live=\"j{jid}\"] .apply-btn').textContent"))
    r = C.evaluate(f"dxLive.sb.from('job_applications').insert({{job_id:{jid},user_id:'{c}',status:'submitted'}}).then(r=>!!r.error)")
    T('applying twice is refused', r)
    C.evaluate(f"document.querySelector('#jx [data-live=\"j{jid}\"] .save-btn').click()"); C.wait_for_timeout(1500)
    T('saving the job is stored', sql(f"select count(*) from public.saved_jobs where job_id={jid} and user_id='{c}'") == '1')
    r = C.evaluate(f"dxLive.sb.from('job_applications').select('user_id').eq('job_id',{jid}).neq('user_id','{c}').then(r=>(r.data||[]).length)")
    T("a candidate cannot see other candidates' applications", r == 0)
    r = E.evaluate(f"dxLive.sb.from('job_applications').select('note').eq('job_id',{jid}).then(r=>(r.data||[]).length)")
    T('the employer sees the applications to its job', r == 1)
    r = C.evaluate(f"dxLive.sb.from('jobs').update({{salary:'1 EGP'}}).eq('id',{jid}).select().then(r=>(r.data||[]).length)")
    T("a candidate cannot edit the employer's job", r == 0)
    T('no errors in the pages', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
