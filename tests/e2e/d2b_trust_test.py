"""D2b end-to-end: real candidate cards; an applicant reviews the employer (anonymous, visible to others without the name); no review
without a real interaction; an honour reference and the candidate's reply; private whitelist; warning references wait for evidence uploads."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def fresh(pg): pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(5000)
def store_get(pg, k): return pg.evaluate(f"JSON.parse(JSON.stringify(DBK.store.get('{k}')))")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    E, C, X = [b.new_context(viewport={'width': 1440, 'height': 900}).new_page() for _ in range(3)]
    for pg in (E, C, X): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    e = signup(E, 'Dr. Trust Employer', f'temp{st}@x.test'); c = signup(C, f'Dr. Candidate {st}', f'tcand{st}@x.test'); x = signup(X, 'Dr. Outsider', f'tout{st}@x.test')
    CO = f'Trust Pharma {st}'
    sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{e}','{CO}','trust-pharma-{st}','Manufacturer','verified','{{Manufacturer}}')")
    jid = sql(f"insert into public.jobs (user_id, title, company, location, country, type, seniority, category, description, active) values ('{e}','QC Analyst {st}','{CO}','Cairo, Egypt','EG','Full-time','junior','qaqc','HPLC and dissolution testing.',true) returning id").split('\n')[0]
    sql(f"update public.profiles set open_to_work=true, headline='QC Analyst — HPLC, dissolution', location='Cairo, Egypt', bio='Four years in a WHO-GMP QC lab.' where id='{c}'")
    sql(f"insert into public.job_applications (job_id, user_id, note, status) values ({jid},'{c}','Interested','submitted')")
    sql(f"update public.profiles set company='{CO}' where id='{e}'")                       # the employer works at the company
    for pg in (E, C, X): fresh(pg)
    E.evaluate("goto('jobs')"); E.wait_for_timeout(3500)
    cards = E.evaluate("[...document.querySelectorAll('#jx .jcard')].filter(c=>c.querySelector('.role-badge.need')).map(c=>c.querySelector('.jc-company span').textContent)")
    T('candidate cards are real open-to-work members (no demo candidates)', f'Dr. Candidate {st}' in cards and 'Sara Mansour' not in cards, cards[:4])
    T('the trust box is painted on the real cards', E.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#jx .jcard')].find(x=>x.innerText.indexOf('Dr. Candidate {st}')>=0);return !!(c&&c.querySelector('.jx-trust'))}})()"))
    # the applicant reviews the employer, anonymously
    C.evaluate("goto('jobs')"); C.wait_for_timeout(3500)
    T('the applicant may review the employer (a real interaction exists)', store_get(C, 'jobInteractions').get(CO) is True, store_get(C, 'jobInteractions'))
    C.evaluate(f"(()=>{{var a=DBK.store.get('jobReviews');a['{CO}']=(a['{CO}']||[]).filter(r=>!r.mine).concat([{{by:'me',anon:1,when:'2026-10',c:[5,4,5,4],text:'Fast, transparent hiring; the salary range was shared up front.',mine:true}}]);DBK.store.set('jobReviews',a)}})()"); C.wait_for_timeout(2000)
    T('the review is stored (anonymous, about the employer)', sql(f"select anonymous||'|'||c1||c2||c3||c4 from public.job_reviews where reviewer='{c}' and reviewee='{e}' and reviewee_role='employer'") == 'true|5454')
    fresh(X); X.evaluate("goto('jobs')"); X.wait_for_timeout(3500)
    rv = store_get(X, 'jobReviews').get(CO, [])
    T('others see it without the reviewer\'s name', len(rv) == 1 and rv[0]['by'] == 'Anonymous' and rv[0]['c'] == [5, 4, 5, 4], rv)
    X.evaluate(f"(()=>{{var a=DBK.store.get('jobReviews');a['{CO}']=(a['{CO}']||[]).concat([{{by:'me',anon:0,when:'2026-10',c:[1,1,1,1],text:'I never dealt with them but I dislike them a lot.',mine:true}}]);DBK.store.set('jobReviews',a)}})()"); X.wait_for_timeout(2000)
    T('no review without a real interaction (refused by the database)', sql(f"select count(*) from public.job_reviews where reviewer='{x}'") == '0')
    # honour reference and reply — only a company the person lists in their experience may write one
    E.evaluate(f"(()=>{{var r=DBK.store.get('jobRefs');r.push({{cand:'Dr. Candidate {st}',company:'{CO}',kind:'honor',from:'2022-01',to:'2025-12',role:'QC Analyst',category:'',text:'Reliable analyst; ran the HPLC lab during two inspections with zero observations.',status:'published',when:'2026-10',expires:''}});DBK.store.set('jobRefs',r)}})()"); E.wait_for_timeout(2000)
    T('no reference from a company the person never listed in their experience', sql(f"select count(*) from public.work_references where author='{e}' and candidate='{c}'") == '0')
    sql(f"""update public.profiles set experience='[{{"company":"{CO}","title":"QC Analyst","from":"2022-01","to":"2025-12"}}]'::jsonb where id='{c}'"""); fresh(E); E.evaluate("goto('jobs')"); E.wait_for_timeout(3000)
    E.evaluate(f"(()=>{{var r=DBK.store.get('jobRefs');r.push({{cand:'Dr. Candidate {st}',company:'{CO}',kind:'honor',from:'2022-01',to:'2025-12',role:'QC Analyst',category:'',text:'Reliable analyst; ran the HPLC lab during two inspections with zero observations.',status:'published',when:'2026-10',expires:''}});DBK.store.set('jobRefs',r)}})()"); E.wait_for_timeout(2000)
    T('the employer\'s honour reference is published', sql(f"select kind||'|'||status from public.work_references where author='{e}' and candidate='{c}'") == 'honor|published')
    fresh(C); C.evaluate("goto('jobs')"); C.wait_for_timeout(3500)
    C.evaluate(f"(()=>{{var r=DBK.store.get('jobRefs');var x=r.find(z=>z.cand==='Dr. Candidate {st}');x.reply='Thank you — it was a great team.';DBK.store.set('jobRefs',r)}})()"); C.wait_for_timeout(2000)
    T('the candidate replies to it (right of reply)', sql(f"select reply from public.work_references where author='{e}' and candidate='{c}'") == 'Thank you — it was a great team.')
    # private whitelist
    E.evaluate(f"(()=>{{var l=DBK.store.get('jobLists');l.candidate.white['Dr. Candidate {st}']={{since:'2026-10-01'}};DBK.store.set('jobLists',l)}})()"); E.wait_for_timeout(1800)
    T('adding to my whitelist is stored', sql(f"select list from public.job_lists where owner='{e}' and target='{c}'") == 'white')
    r = X.evaluate(f"dxLive.sb.from('job_lists').select('owner').eq('owner','{e}').then(r=>(r.data||[]).length)")
    T("someone else's lists are private", r == 0)
    # warning reference needs evidence
    E.evaluate(f"(()=>{{var r=DBK.store.get('jobRefs');r.push({{cand:'Dr. Candidate {st}',company:'{CO}',kind:'warn',from:'2022-01',to:'2025-12',role:'QC Analyst',category:'Left without notice',text:'Left in the middle of a validation campaign without any notice to the lab.',status:'pending'}});DBK.store.set('jobRefs',r)}})()"); E.wait_for_timeout(1800)
    T('a warning without evidence is not published', sql(f"select count(*) from public.work_references where author='{e}' and kind='warn'") == '0')
    E.evaluate("goto('jobs')"); E.wait_for_timeout(1500)
    E.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#jx .jcard')].find(x=>x.innerText.indexOf('Dr. Candidate {st}')>=0);c.querySelector('.apply-btn').click()}})()"); E.wait_for_timeout(3000)
    T('Contact on a candidate opens a conversation with them', E.evaluate("document.body.getAttribute('data-page')") == 'messages' and f'Dr. Candidate {st}' in E.inner_text('.chat-head'))
    T('no errors in the pages', not errs, errs)
    b.close()
done()
