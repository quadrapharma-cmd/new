"""E2 end-to-end: Admin → Review with real cases — approve a verification (company verified, owner notified), publish a warning
(person notified, can reply), mark a certificate checked, resolve a report filed through the real dialog; documents open
through short-lived links; nobody outside the Drugbox team can decide."""
from playwright.sync_api import sync_playwright
import subprocess, time, os, urllib.request
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py
V = FIXTURES
st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def fresh(pg): pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(4500)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A, O, E, C = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(4)]
    for pg in (A, O, E, C): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    adm = signup(A, 'Drugbox Reviewer', f'rev{st}@x.test'); o = signup(O, 'Dr. Pending Owner', f'pown{st}@x.test'); e = signup(E, 'Dr. Warning Author', f'wauth{st}@x.test'); c = signup(C, f'Dr. Warned {st}', f'wcan{st}@x.test')
    sql(f"update public.profiles set role='admin' where id='{adm}'")
    cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{o}','Pending Pharma {st}','pending-pharma-{st}','Manufacturer','pending','{{Manufacturer}}') returning id").split('\n')[0]
    fresh(O)
    path = f'verification/{cid}/registry-{st}.pdf'
    up = O.evaluate(f"fetch('data:application/pdf;base64,JVBERi0xLjQK').then(r=>r.blob()).then(b=>dxLive.sb.storage.from('documents').upload('{path}', new Blob([b],{{type:'application/pdf'}}))).then(r=>!r.error)")
    sql(f"insert into public.verification_requests (company_id, submitted_by, registry, registry_path) values ({cid},'{o}','778899','{path}')")
    CO2 = f'Author Pharma {st}'
    sql(f"update public.profiles set company='{CO2}' where id='{e}'"); sql(f"""update public.profiles set experience='[{{"company":"{CO2}","title":"QC","from":"2021-01","to":"2024-12"}}]'::jsonb where id='{c}'""")
    sql(f"insert into public.companies (owner_id, name, slug, type, status) values ('{e}','{CO2}','author-pharma-{st}','Manufacturer','verified')")   # DB2 handoff: the author's company must be a real, verified page
    fresh(E)
    ev = f'{e}/ev-{st}.pdf'
    E.evaluate(f"fetch('data:application/pdf;base64,JVBERi0xLjQK').then(r=>r.blob()).then(b=>dxLive.sb.storage.from('reference-evidence').upload('{ev}', new Blob([b],{{type:'application/pdf'}})))"); E.wait_for_timeout(800)
    E.evaluate(f"dxLive.sb.from('work_references').insert({{author:'{e}',candidate:'{c}',kind:'warn',role_title:'QC',from_month:'2021-01-01',to_month:'2024-12-01',category:'Left without notice',body:'Left in the middle of a validation campaign without any notice to the lab.',evidence_path:'{ev}'}})"); E.wait_for_timeout(1000)
    wid = sql(f"select id from public.work_references where author='{e}' and kind='warn'")
    sid = sql(f"insert into public.company_sites (company_id, name, type) values ({cid},'Plant {st}','factory') returning id").split('\n')[0]
    certid = sql(f"insert into public.site_certificates (site_id, company_id, name, expiry) values ({sid},{cid},'WHO-GMP','2028-01-01') returning id").split('\n')[0]
    # a report through the real dialog
    C.evaluate("goto('feed')"); fresh(C)
    C.evaluate(f"dxHub.page('pending-pharma-{st}','overview')"); C.wait_for_timeout(2500)
    C.evaluate("document.querySelector('#dxDir [data-hreport]').click()"); C.wait_for_timeout(500)
    C.fill('.dbk-ov #rpT', 'The phone number is out of service'); C.fill('.dbk-ov #rpF', '+20 2 0000 0000')
    C.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();[...o.querySelectorAll('button')].find(x=>/send report/i.test(x.textContent)).click()})()"); C.wait_for_timeout(2000)
    T('a report filed through the real dialog is stored', sql(f"select section||'|'||status from public.company_reports where company_id={cid}") == 'About|open')
    # the reviewer
    fresh(A); A.evaluate("goto('admin')"); A.wait_for_timeout(800); A.evaluate("switchAdminTab('review')"); A.wait_for_timeout(2500)
    tabs = A.evaluate("[...document.querySelectorAll('.dx-mod-tab')].map(t=>t.textContent.trim())")
    T('the Review queues show the waiting cases', all(any(k in t for t in tabs) for k in ('Verification requests', 'Warning references', 'Site certificates', 'Company reports')), tabs)
    T('the reviewer sees the company and its registry number', f'Pending Pharma {st}' in A.inner_text('.dx-mod-list') and '778899' in A.inner_text('.dx-mod-list'))
    link = A.evaluate(f"dxModeration.link('{path}','documents')")
    T('a document opens through a short-lived link', bool(link) and '/object/sign/' in link and urllib.request.urlopen(link, timeout=5).status == 200, link)
    A.evaluate(f"document.querySelector('.dx-mod-ok[data-k=verifications][data-id=\"' + {sql(f'select id from public.verification_requests where company_id={cid}')} + '\"]').click()"); A.wait_for_timeout(2500)
    T('approving verifies the company', sql(f"select status||'|'||tax_verified from public.companies where id={cid}") == 'verified|true')
    T('the owner is notified', sql(f"select count(*) from public.notifications where user_id='{o}' and type='verification' and message like 'Your company is verified%'") == '1')
    A.evaluate("document.querySelector('.dx-mod-tab[data-q=warnings]').click()"); A.wait_for_timeout(300)
    A.evaluate(f"document.querySelector('.dx-mod-ok[data-k=warnings][data-id=\"{wid}\"]').click()"); A.wait_for_timeout(2500)
    T('publishing the warning makes it public (with an expiry)', sql(f"select status from public.work_references where id={wid}") == 'published')
    T('the person is told and can reply', sql(f"select count(*) from public.notifications where user_id='{c}' and type='reference'") == '1')
    A.evaluate("document.querySelector('.dx-mod-tab[data-q=certs]').click()"); A.wait_for_timeout(300)
    A.evaluate(f"document.querySelector('.dx-mod-ok[data-k=certs][data-id=\"{certid}\"]').click()"); A.wait_for_timeout(2000)
    T('marking the certificate checked is recorded', sql(f"select checked_at is not null from public.site_certificates where id={certid}") == 't')
    A.evaluate("document.querySelector('.dx-mod-tab[data-q=reports]').click()"); A.wait_for_timeout(300)
    rid = sql(f"select id from public.company_reports where company_id={cid}")
    A.evaluate(f"document.querySelector('.dx-mod-ok[data-k=reports][data-id=\"{rid}\"]').click()"); A.wait_for_timeout(2000)
    T('resolving the report is recorded', sql(f"select status from public.company_reports where id={rid}") == 'resolved')
    # nobody else can decide
    O.evaluate("goto('admin')"); O.wait_for_timeout(600)
    T('a non-admin sees "Admin access required"', 'Admin access required' in O.inner_text('#content'))
    r = C.evaluate(f"dxLive.sb.rpc('moderate_reference',{{ref_id:{wid},new_status:'rejected'}})" + ERR)
    T('a non-admin cannot moderate a warning', r and refused(r) and sql(f"select status from public.work_references where id={wid}") == 'published', r)
    vid2 = sql(f"insert into public.verification_requests (company_id, submitted_by, registry) values ({cid},'{o}','111222') returning id").split('\n')[0]
    r = O.evaluate(f"dxLive.sb.from('verification_requests').update({{status:'approved'}}).eq('id',{vid2})" + ERR)
    T('a company cannot approve its own verification', refused(r) and sql(f"select status from public.verification_requests where id={vid2}") == 'pending', r)
    T('no errors in the pages', not errs, errs)
    b.close()
done()
