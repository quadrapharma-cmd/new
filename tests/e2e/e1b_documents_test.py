"""E1b end-to-end: CV with an application (applicant + that employer only), verification documents through the real dialog
(company + Drugbox only), warning references need evidence (author + moderators only) and wait for review."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); V = '/tmp/vids'; R = []
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
def fresh(pg): pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(5000)
def can_sign(pg, bucket, path): return pg.evaluate(f"dxLive.sb.storage.from('{bucket}').createSignedUrl('{path}',60).then(r=>!r.error)")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    E, C, X, A = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(4)]
    for pg in (E, C, X, A): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    e = signup(E, 'Dr. Doc Employer', f'demp{st}@x.test'); c = signup(C, f'Dr. Doc Candidate {st}', f'dcan{st}@x.test'); x = signup(X, 'Dr. Doc Outsider', f'dout{st}@x.test'); adm = signup(A, 'Drugbox Reviewer', f'dadm{st}@x.test')
    sql(f"update public.profiles set role='admin' where id='{adm}'")
    CO = f'Doc Pharma {st}'
    cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{e}','{CO}','doc-pharma-{st}','Manufacturer','pending','{{Manufacturer}}') returning id").split('\n')[0]
    jid = sql(f"insert into public.jobs (user_id, title, company, location, country, type, seniority, category, description, active) values ('{e}','Validation Engineer {st}','{CO}','Giza','EG','Full-time','mid','qaqc','Cleaning validation.',true) returning id").split('\n')[0]
    sql(f"update public.profiles set company='{CO}' where id='{e}'"); sql(f"""update public.profiles set open_to_work=true, experience='[{{"company":"{CO}","title":"Validation","from":"2021-01","to":"2024-12"}}]'::jsonb where id='{c}'""")
    for pg in (E, C, A): fresh(pg)
    # CV with an application
    C.evaluate("goto('jobs')"); C.wait_for_timeout(3500)
    C.evaluate(f"document.querySelector('#jx [data-live=\"j{jid}\"] .apply-btn').click()"); C.wait_for_timeout(600)
    T('the apply window offers a CV field', C.evaluate("!!document.getElementById('dxCv')"))
    C.set_input_files('#dxCv', V + '/spec.pdf'); C.fill('#applyModal textarea', 'Cleaning validation for OSD lines.'); C.evaluate("submitApply()"); C.wait_for_timeout(2500)
    cv = sql(f"select coalesce(cv_path,'') from public.job_applications where job_id={jid} and user_id='{c}'")
    T('the application carries the CV, stored privately under the applicant', cv.startswith(f'cv/{c}/'), cv)
    T('the applicant can open their CV', can_sign(C, 'documents', cv))
    T("the employer of that job can open it", can_sign(E, 'documents', cv))
    T('an outsider cannot open it', not can_sign(X, 'documents', cv))
    # verification documents through the real dialog
    E.evaluate(f"dxDir.verify('doc-pharma-{st}')"); E.wait_for_timeout(800)
    inputs = E.evaluate("[...document.querySelectorAll('.dbk-ov input')].map(i=>i.id+':'+i.type)")
    for i in inputs:
        iid, typ = i.split(':')
        if typ == 'file' and iid in ('vfR', 'vfT'): E.set_input_files('#' + iid, V + '/spec.pdf')
        elif typ in ('text', 'number', 'tel') and iid: E.fill('#' + iid, '445566')
    E.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();var b=o&&(o.querySelector('[data-a=ok]')||[...o.querySelectorAll('button')].filter(x=>!/^(×|Cancel|Close)$/.test(x.textContent.trim())).pop());b&&b.click()})()"); E.wait_for_timeout(3500)
    vr = sql(f"select coalesce(registry_path,'')||'|'||coalesce(tax_card_path,'')||'|'||status from public.verification_requests where company_id={cid} order by id desc limit 1")
    T('the verification request reaches Drugbox with the registry and tax-card documents', vr.startswith(f'verification/{cid}/registry-') and f'|verification/{cid}/tax_card-' in vr and vr.endswith('|pending'), (vr, inputs))
    rp = vr.split('|')[0]
    T('Drugbox reviewers can open the documents', can_sign(A, 'documents', rp) if rp else False)
    T('an outsider cannot', not can_sign(X, 'documents', rp) if rp else False)
    # warning reference: evidence required
    E.evaluate("goto('jobs')"); E.wait_for_timeout(3000)
    warn = f"(()=>{{var r=DBK.store.get('jobRefs');r.push({{cand:'Dr. Doc Candidate {st}',company:'{CO}',kind:'warn',from:'2021-01',to:'2024-12',role:'Validation',category:'Left without notice',text:'Left in the middle of a validation campaign without notice to the lab.',status:'pending'}});DBK.store.set('jobRefs',r)}})()"
    E.evaluate(warn); E.wait_for_timeout(2000)
    T('a warning without evidence is not submitted', sql(f"select count(*) from public.work_references where author='{e}' and kind='warn'") == '0')
    E.evaluate("(()=>{var o=document.createElement('div');o.className='dbk-ov';o.innerHTML='<div><label>Category<select id=\"rfCat\"><option>Left without notice</option></select></label></div>';document.body.appendChild(o)})()"); E.wait_for_timeout(500)
    T('the warning form gets a required evidence field', E.evaluate("!!document.getElementById('dxEv')"))
    E.set_input_files('#dxEv', V + '/spec.pdf'); E.wait_for_timeout(300); E.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E.evaluate(warn); E.wait_for_timeout(2500)
    w = sql(f"select status||'|'||coalesce(evidence_path,'') from public.work_references where author='{e}' and kind='warn'")
    T('with evidence, the warning is submitted and waits for review (not published)', w.startswith('pending|' + e + '/'), w)
    ev = w.split('|')[1]
    T('the evidence is readable by its author and Drugbox reviewers only', can_sign(E, 'reference-evidence', ev) and can_sign(A, 'reference-evidence', ev) and not can_sign(X, 'reference-evidence', ev) and not can_sign(C, 'reference-evidence', ev))
    T('no errors in the pages', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
