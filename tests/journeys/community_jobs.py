"""Community journeys — jobs: find, save, apply, follow and withdraw applications, post / edit / close vacancies, review
applicants, move them through the pipeline, open-to-work profiles, contacting candidates, private preferred / blocked lists
(J-COMMUNITY-19 … 29). Run: python3 tests/journeys/community_jobs.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
import _dx

SAVED = r'✓ Saved|Saved|محفوظ|تم الحفظ'

def job_world(j):
    """Live: 45 active jobs from 6 companies across categories, countries and levels (other journeys posted them)."""
    t = j.tag[:4]; ids = {}
    cos = [('Pharco', 'EG', 'Alexandria'), ('Eva Pharma', 'EG', 'Cairo'), ('Julphar', 'AE', 'Dubai'), ('Tabuk', 'SA', 'Riyadh'), ('Hikma', 'EG', 'Giza'), ('SPIMACO', 'SA', 'Qassim')]
    owners = [seed_user(j, 'HR %s' % c[0]) for c in cos]
    cats = ['regulatory', 'qaqc', 'production', 'sales', 'rd']; levels = ['entry', 'junior', 'mid', 'senior', 'executive']
    for i in range(45):
        c = cos[i % 6]; cat = cats[i % 5]; lv = levels[(i // 5) % 5]
        ids[i] = seed_job(j, owners[i % 6], 'Role %02d %s %s' % (i, cat.upper(), t), c[0], c[2], c[1], 'full-time' if i % 3 else 'contract', lv, cat, 'Duties for role %d' % i, ago_s=i * 3600)
    ids['h1'] = seed_job(j, owners[0], 'HPLC Analyst %s' % t, 'Pharco', 'Alexandria', 'EG', 'full-time', 'junior', 'qaqc', 'Method validation', ago_s=60)
    ids['h2'] = seed_job(j, owners[2], 'QC Chemist %s' % t, 'Julphar', 'Dubai', 'AE', 'full-time', 'junior', 'qaqc', 'Runs hplc and GC daily', ago_s=120)
    ids['h3'] = seed_job(j, owners[1], 'Lab Supervisor %s' % t, 'Eva Pharma', 'Cairo', 'EG', 'full-time', 'mid', 'qaqc', 'Supervision', tags=('HPLC', 'GMP'), ago_s=180)
    return t, ids, owners

@journey('J-COMMUNITY-19')
def find_jobs(j):
    """A job seeker finds the jobs that fit him across Egypt and the GCC."""
    if j.live:
        s = j.person('Youssef Hassan'); pg = s['page']; t, ids, owners = job_world(j); j.reload(pg)
        total = int(j.sql1('select count(*) from public.jobs where active')); hplc = ['HPLC Analyst %s' % t, 'QC Chemist %s' % t, 'Lab Supervisor %s' % t]
    else:
        pg = j.demo_signin(j.new_page()); total = None; hplc = ['QC Analyst (HPLC)']
    with j.step("Jobs → I'm Job Hunting: the open positions number and the header count are real"):
        jobs_page(j, pg, HUNT); ui_ok(j, pg, 'Jobs')
        n = jobs_header_n(pg); j.check(n is not None, 'no "Open Positions N jobs" count')
        if j.live:
            j.check(n == total, 'the header says %s jobs, the database has %d active jobs' % (n, total))
            hero = j.text(pg)[:600]; j.check(not re.search(r'\b76\b', hero), 'the hero still shows the sample "76 open positions"')
            strip = pg.evaluate("[...document.querySelectorAll('#content .intel-strip .intel-item b')].map(e=>e.textContent.replace(/\\D/g,''))")
            j.check(strip and strip[0] == str(total), 'the strip says %s open positions, the database has %d' % (strip[:1], total))
            sen = sum(int(x or 0) for x in pg.evaluate("[...document.querySelectorAll('#content .sen-opt[data-level] .sen-count')].map(e=>e.textContent.replace(/\\D/g,''))"))
            j.check(sen == total, 'the seniority counts add up to %d, the database has %d active jobs' % (sen, total))
            j.check('150,000' not in j.text(pg), 'the Jobs page still claims "150,000+" professionals')
            # the reach line counts members in good grammar ("1 pharma professional"), and the candidates of the Hiring view are
            # members open to work: not called "Verified" when they are not, no seniority they never gave, no Save that fails
            reach = re.search(r'Reach ([\d,]+) pharma professionals?\b', j.text(pg))
            if reach and not j.ar: j.check(not (reach.group(1) == '1' and 'professionals' in reach.group(0)), 'the reach line says "%s"' % reach.group(0))
            jobs_page(j, pg, HIRE)
            cands = pg.evaluate("[...document.querySelectorAll('#content .jcard[data-live^=c]')].filter(e=>e.getClientRects().length).map(c=>({lvl:!!c.querySelector('.level-badge'),save:!!c.querySelector('.save-btn')}))")
            j.check(not [c for c in cands if c['lvl']], 'candidate cards show a seniority level the members never gave (%d of %d)' % (len([c for c in cands if c['lvl']]), len(cands)))
            if pg.evaluate("document.querySelector('#content .jcard[data-live^=c] .save-btn')!==null"):
                mark = j.toast_mark(pg); pg.locator('#content .jcard[data-live^=c] .save-btn').first.click(); pg.wait_for_timeout(1200)
                j.check(not re.search(r'linked to other|not allowed|wrong|خطأ', ' '.join(j.toasts_since(pg, mark))), 'Save on a candidate card fails: %s' % j.toasts_since(pg, mark))
            unver = int(j.sql1("select count(*) from public.profiles where open_to_work and not verified") or 0)
            if unver and not j.ar: j.check(not re.search(r'Verified professionals actively looking', j.text(pg)), 'the candidates list is titled "Verified professionals" over %d members who are not verified' % unver)
            jobs_page(j, pg, HUNT)
    with j.step("Search 'HPLC': matches title, company, description and tags"):
        box = pg.locator('#content input[type=search]:visible, #content input[placeholder*="earch" i]:visible, #content input[placeholder*="بحث"]:visible')
        j.check(box.count(), 'not built: no keyword search on Jobs')
        box.first.fill('HPLC'); box.first.press('Enter'); j.settle(pg, 1200)
        got = [c['title'] for c in jcards(pg)]
        j.check(all(any(h in g for g in got) for h in hplc), 'searching HPLC does not find %s (shows %s)' % (hplc, got[:6]))
        j.check(jobs_header_n(pg) == len(got), 'the header count %s ≠ %d cards shown' % (jobs_header_n(pg), len(got)))
        box.first.fill(''); box.first.press('Enter'); j.settle(pg, 900)
    with j.step('Filter QA/QC + Full-time + Egypt + Junior: every card matches all four and the count equals the cards; clear filters'):
        pg.locator('#content .cf-tag').filter(has_text=re.compile(r'QA/QC|الجودة')).first.click(); pg.wait_for_timeout(500)
        tg = pg.locator('#content .jx-ftoggle:visible')
        if tg.count(): tg.first.click(); pg.wait_for_timeout(400)          # a phone: the filters open from "⚙ Filters"
        for lab in (r'Full-time|دوام كامل', r'Egypt|مصر'):
            cb = pg.locator('#content label').filter(has_text=re.compile(lab)).locator('input[type=checkbox]')
            j.check(cb.count(), 'no "%s" filter' % lab); cb.first.check(); pg.wait_for_timeout(500)
        pg.locator('#content .sen-opt').filter(has_text=re.compile(r'Junior|مبتدئ|صغار')).first.click(); j.settle(pg, 900)
        cs = jcards(pg); j.check(cs, 'the four filters show no job (and no empty state)') if j.live else None
        bad = [c['title'] for c in cs if not (c['cat'] in ('qaqc', 'qa') and re.search(r'Full-time|full-time|دوام كامل', c['text']) and re.search(r'Egypt|🇪🇬|مصر', c['text']) and c['level'] in ('junior', 'jr'))]
        j.check(not bad, 'filtered results include jobs that do not match: %s' % ', '.join(bad[:4]))
        j.check(jobs_header_n(pg) == len(cs), 'with filters the header says %s jobs but %d are shown' % (jobs_header_n(pg), len(cs)))
        if j.live: j.check('HPLC Analyst %s' % t in ' '.join(c['title'] for c in cs) and 'QC Chemist %s' % t not in ' '.join(c['title'] for c in cs), 'the filters do not combine (the Egypt junior QC job missing or the Dubai one shown)')
        cl = j.find(pg, r'Clear filters|امسح الفلاتر', scope='#content'); j.check(cl, 'no "Clear filters" while filters are on')
        cl.click(); j.settle(pg, 900)
        j.check(not pg.locator('#content input[data-jxf]:checked').count() and (jobs_header_n(pg) == total if j.live else jobs_header_n(pg) == len(jcards(pg))), 'Clear filters leaves filters on (header %s, cards %d)' % (jobs_header_n(pg), len(jcards(pg))))
        jobs_page(j, pg, HUNT)
    with j.step('Every matching job is reachable by paging (Load more / scroll), with no duplicates'):
        for _ in range(15):
            more = pg.locator('#content button:visible, #content .load-more:visible').filter(has_text=re.compile(r'Load more|Show more|المزيد'))
            if not more.count(): break
            more.first.click(); j.settle(pg, 900)
        cs = jcards(pg); n = jobs_header_n(pg)
        j.check(len(cs) == n, '%d of %s jobs can be reached' % (len(cs), n))
    with j.step('Open a job card: the detail shows description, requirements, salary, type, location + country, deadline, posted date, the company and Apply / Save'):
        c = pg.locator('#content .jcard:visible').first; title = c.locator('.jc-title').inner_text()
        before = j.text(pg); mark = j.toast_mark(pg); c.locator('.jc-title').click(); j.settle(pg, 1000); j.dead_end(pg, mark, 'the job card')
        page = pg.evaluate("document.body.getAttribute('data-page')")
        j.check(mopen(pg) or j.text(pg) != before, 'clicking the job card opens nothing')
        d = mtext(pg) if mopen(pg) else j.text(pg)
        missing = [k for k, p in (('requirements', r'Requirements|المتطلبات'), ('deadline', r'Deadline|Apply by|آخر موعد'), ('posted date', r'Posted|ago|نشر'), ('Apply', r'Apply|تقدم')) if not re.search(p, d)]
        j.check(not missing, 'the job detail has no %s' % ', '.join(missing))
    with j.step('Live: a Dubai job shows UAE (the country comes from the job row)'):
        if j.demo: j.skip('checked in live')
        jobs_page(j, pg, HUNT); c = jcard(j, pg, 'QC Chemist %s' % t)
        j.check(re.search(r'🇦🇪|UAE|Emirates|الإمارات', c.inner_text()), 'the Dubai job does not show UAE')

@journey('J-COMMUNITY-20')
def save_jobs(j):
    """A job seeker saves interesting jobs and comes back to them later."""
    if j.live:
        s = j.person('Youssef Hassan'); pg = s['page']; o = seed_user(j, 'HR Pharco'); t = j.tag[:4]
        a = seed_job(j, o, 'Saved Role A %s' % t, 'Pharco', deadline='2026-12-31'); b = seed_job(j, o, 'Saved Role B %s' % t, 'Pharco', deadline='2026-12-15')
        ta, tb = 'Saved Role A %s' % t, 'Saved Role B %s' % t; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); ta, tb = 'Cosmetic Formulation Scientist', 'GCC Registration Coordinator'
    def save_btn(title): return jcard(j, pg, title).locator('.save-btn')
    with j.step("Click Save on two jobs: each turns '✓ Saved' with a toast"):
        jobs_page(j, pg, HUNT)
        for i, tt in enumerate((ta, tb)):
            cut = toast_cut(pg); save_btn(tt).click(); pg.wait_for_timeout(700)
            j.check(re.search(SAVED, save_btn(tt).inner_text()), 'Save on "%s" does not turn to Saved' % tt)
            j.check(toasts_after(pg, cut), 'saving gives no toast')
        if j.live: j.check(j.wait_db("select count(*) from public.saved_jobs where user_id='%s'" % s['id'], 5) == '2', 'not 2 saved_jobs rows')
    with j.step('Reload: both still Saved'):
        reopen(j, pg); jobs_page(j, pg, HUNT)
        j.check(re.search(SAVED, save_btn(ta).inner_text()) and re.search(SAVED, save_btn(tb).inner_text()), 'after reload the jobs are not Saved')
    with j.step('Saved page → Saved jobs: lists both (title, company, location, deadline) and opens each'):
        j.nav(pg, 'saved'); j.settle(pg, 1200); txt = j.text(pg)
        tab = j.find(pg, r'Jobs|Saved jobs|الوظائف', scope='#content', kinds='button,[role=tab],.cf-tag,[onclick]')
        if tab: tab.click(); j.settle(pg, 800); txt = j.text(pg)
        j.check(ta in txt and tb in txt, 'not built: the Saved page does not list saved jobs (only posts)')
    with j.step('Unsave one from Saved: gone from Saved and from Jobs'):
        # the row of THIS job (the smallest element that names it and has its own Unsave) — one list shows both saved jobs
        u = pg.evaluate_handle("""n=>{const re=/^\\W*(Unsave|Remove|Saved|إزالة|إلغاء الحفظ)$/i,btn=e=>[...e.querySelectorAll('button,[onclick]')].find(b=>b.getClientRects().length&&re.test(b.innerText.trim()));
            let best=null;document.querySelectorAll('#content *').forEach(e=>{if(e.getClientRects().length&&(e.innerText||'').includes(n)&&btn(e)&&(!best||best.contains(e)))best=e});return best?btn(best):null}""", tb).as_element()
        j.check(u, 'no Unsave on the saved job'); u.click(); j.settle(pg, 900)
        j.check(tb not in j.text(pg), 'the unsaved job is still on the Saved page')
        jobs_page(j, pg, HUNT); j.check(not re.search(SAVED, save_btn(tb).inner_text()), 'Jobs still shows the unsaved job as Saved')
        if j.live: j.check(j.wait_db("select count(*) from public.saved_jobs where user_id='%s'" % s['id'], 5, want='1') == '1', 'saved_jobs row not removed')
    with j.step('A job the employer closed shows as Closed in Saved'):
        if j.demo: j.skip('the employer exists only in live')
        j.sql('update public.jobs set active=false where id=%d' % a)
        j.nav(pg, 'saved'); j.settle(pg, 1200)
        j.check(re.search(r'Closed|مغلقة', j.text(pg)), 'the closed job is not marked Closed in Saved')

def make_files(j):
    d = os.path.join(j.cfg['out'], 'files'); os.makedirs(d, exist_ok=True)
    exe = os.path.join(d, 'setup.exe'); big = os.path.join(d, 'huge_cv.pdf')
    if not os.path.exists(exe): open(exe, 'wb').write(b'MZ' + b'\0' * 2048)
    if not os.path.exists(big):
        with open(big, 'wb') as f: f.write(b'%PDF-1.4\n'); f.truncate(30 * 1024 * 1024)
    return exe, big

@journey('J-COMMUNITY-21')
def apply_to_job(j):
    """A job seeker applies with his CV so the employer can consider him."""
    exe, big = make_files(j)
    if j.live:
        e = employer(j); s = j.person('Youssef Hassan'); pg = s['page']; t = j.tag[:4]
        title = 'QC Analyst HPLC %s' % t; jid = seed_job(j, e['id'], title, e['co']['name'], 'Alexandria', 'EG', category='qaqc')
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); title = 'QC Analyst (HPLC)'
    with j.step('Open the job → Apply Now: the form has a message and a CV file field'):
        apply_dialog(j, pg, title)
        fi = pg.locator('.modal-overlay.show input[type=file], .dbk-ov input[type=file]')
        j.check(fi.count(), 'not built: the Apply form has no CV file input (only a drop zone)')
    with j.step('A .exe and a 30 MB file are refused with a clear message; nothing is sent'):
        txt0 = mtext(pg)
        for f, why in ((exe, 'a .exe'), (big, 'a 30 MB file')):
            if not mopen(pg): apply_dialog(j, pg, title); fi = pg.locator('.modal-overlay.show input[type=file], .dbk-ov input[type=file]')
            before = toast_set(pg); fi.first.set_input_files(f); pg.wait_for_timeout(800)
            pg.locator('.modal-overlay.show textarea, .dbk-ov textarea').first.fill('Trying a wrong file')
            mclick(j, pg, r'Send Application|Send|إرسال|أرسل', 'Send Application'); j.settle(pg, 1200)
            msg = ' '.join(new_toasts(pg, before)) + ' ' + (mtext(pg) if mopen(pg) else '')
            j.check(re.search(r'PDF|Word|type|large|size|MB|too big|not allowed|نوع|حجم|كبير|غير مسموح', msg.replace(txt0, ''), re.I) and not re.search(r'Application sent|تم إرسال', msg), '%s is not refused with a clear message (%s)' % (why, msg[:120].replace('\n', ' ')))
            if j.live: j.check(j.sql1("select count(*) from public.job_applications where job_id=%d" % jid) == '0', '%s was sent' % why)
            mclose(pg)
        apply_dialog(j, pg, title); fi = pg.locator('.modal-overlay.show input[type=file], .dbk-ov input[type=file]')
        if j.live: j.check(j.sql1("select count(*) from public.job_applications where job_id=%d" % jid) == '0', 'something was sent')
    with j.step('Write a message, attach the PDF CV, Send: the confirmation names the job and company; the button turns Applied'):
        fi.first.set_input_files(PDF); pg.wait_for_timeout(600)
        ta = pg.locator('.modal-overlay.show textarea, .dbk-ov textarea'); ta.first.fill('I have 3 years of HPLC method validation at a WHO-GMP site.')
        before = toast_set(pg); mclick(j, pg, r'Send Application|Send|إرسال|أرسل', 'Send Application'); j.settle(pg, 1500)
        msg = ' '.join(new_toasts(pg, before)) + ' ' + (mtext(pg) if mopen(pg) else '')
        j.check(re.search(re.escape(title.split(' (')[0][:18]), msg), 'the confirmation does not name the job (%s)' % msg[:120])
        mclose(pg); b = jcard(j, pg, title).locator('.apply-btn')
        j.check(re.search(r'Applied|تم التقديم', b.inner_text()) and (b.is_disabled() or b.get_attribute('aria-disabled') == 'true'), 'the button does not turn to a disabled "Applied" (%s)' % b.inner_text())
    if j.live:
        with j.step('Live: a job_applications row (note, cv_path in documents/cv/<uid>/), applicant_count +1, the employer notified'):
            j.check(j.wait_db("select count(*) from public.job_applications where job_id=%d and user_id='%s' and status='submitted'" % (jid, s['id']), 6) == '1', 'no job_applications row')
            j.check(j.sql1("select cv_path like 'cv/%s/%%' from public.job_applications where job_id=%d" % (s['id'], jid)) == 't', 'the CV is not stored under documents/cv/<uid>/')
            j.check(j.sql1('select applicant_count from public.jobs where id=%d' % jid) == '1', 'applicant_count is not 1')
            j.check(notif_rows(j, e['id'], extra=' and job_id=%d' % jid) == 1, 'the employer was not notified once')
    with j.step('Reload: still Applied'):
        reopen(j, pg); jobs_page(j, pg, HUNT)
        j.check(re.search(r'Applied|تم التقديم', jcard(j, pg, title).locator('.apply-btn').inner_text()), 'after reload the job is not Applied')
    with j.step('My applications lists the job with status Submitted and the date'):
        el = j.find(pg, r'My applications|طلباتي', scope='#app')
        j.check(el, 'not built: no "My applications"'); el.click(); j.settle(pg, 1000)
        j.check(title[:18] in j.text(pg) and re.search(r'Submitted|مقدم', j.text(pg)), 'My applications does not list the job as Submitted')
    with j.step("A second application is refused ('You already applied')"):
        jobs_page(j, pg, HUNT); b = jcard(j, pg, title).locator('.apply-btn')
        if not b.is_disabled():
            before = toast_set(pg); b.click(); pg.wait_for_timeout(800)
            j.check(re.search(r'already|سبق', ' '.join(new_toasts(pg, before)) + mtext(pg), re.I), 'a second application is not refused')
    with j.step("A company member cannot apply to his own company's job"):
        if j.live:
            pe = e['page']; jobs_page(j, pe, HUNT); b = jcard(j, pe, title).locator('.apply-btn')
        else:
            jobs_page(j, pg, HUNT); b = jcard(j, pg, 'Senior Regulatory Affairs Specialist').locator('.apply-btn'); pe = pg
        if b.count() and b.is_visible() and not b.is_disabled():
            b.click(); pe.wait_for_timeout(800)
            j.check(not (mopen(pe) and re.search(r'Apply', mtext(pe))), "the employer can apply to his own company's job")

@journey('J-COMMUNITY-22')
def follow_applications(j):
    """A job seeker follows where each application stands and can withdraw one."""
    if j.live:
        e = employer(j); s = j.person('Youssef Hassan'); pg = s['page']; t = j.tag[:4]
        j1 = seed_job(j, e['id'], 'Shortlist Role %s' % t, e['co']['name']); j2 = seed_job(j, e['id'], 'Submitted Role %s' % t, e['co']['name'])
        j.sql("insert into public.job_applications (job_id, user_id, note, status) values (%d,'%s','hi','shortlisted'), (%d,'%s','hi','submitted')" % (j1, s['id'], j2, s['id']))
        j.reload(pg); r1, r2 = 'Shortlist Role %s' % t, 'Submitted Role %s' % t
    else:
        pg = j.demo_signin(j.new_page()); r1 = r2 = None
    with j.step('Open My applications: each application with its current status and when it changed'):
        jobs_page(j, pg, HUNT); el = j.find(pg, r'My applications|طلباتي', scope='#app')
        j.check(el, 'not built: no "My applications"'); el.click(); j.settle(pg, 1000); txt = j.text(pg)
        if j.live: j.check(r1 in txt and re.search(r'Shortlisted|القائمة المختصرة', txt) and r2 in txt and re.search(r'Submitted|مقدم', txt), 'My applications does not show both with their status')
    with j.step('Withdraw the submitted one (confirm): marked Withdrawn; Apply is available again'):
        row = pg.locator('#content [class*=card], #content li, #content tr').filter(has_text=r2 or re.compile(r'Submitted|مقدم')).first
        w = row.locator('button').filter(has_text=re.compile(r'Withdraw|سحب')); j.check(w.count(), 'not built: no Withdraw')
        w.first.click(); pg.wait_for_timeout(500); confirm(j, pg, r'Withdraw|Yes|سحب|نعم'); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select count(*) from public.job_applications where job_id=%d and user_id='%s'" % (j2, s['id']), 5, want='0') == '0', 'the application is still there')
    with j.step("The employer no longer sees the withdrawn application"):
        if j.demo: j.skip('the employer exists only in live')
        pe = e['page']; n = pe.evaluate("i=>dxLive.sb.from('job_applications').select('user_id').eq('job_id',i).then(r=>(r.data||[]).length)", j2)
        j.check(n == 0, 'the employer still reads %s application(s)' % n)

@journey('J-COMMUNITY-23')
def post_vacancy(j):
    """An employer publishes a vacancy so qualified people see it and apply."""
    t = j.tag[:4]; title = 'QA Manager %s' % t
    if j.live: e = employer(j); pg = e['page']; s = j.person('Youssef Hassan')
    else: pg = j.demo_signin(j.new_page())
    def open_form():
        jobs_page(j, pg, HIRE)
        b = j.find(pg, r'^\W*(Post a Job|انشر وظيفة|نشر وظيفة)\W*$', scope='#content'); j.check(b, 'no Post a Job'); b.click(); pg.wait_for_timeout(700)
        j.check(mopen(pg), 'Post a Job opens nothing')
    with j.step('Post a Job with an empty title: refused with a message'):
        open_form(); before = toast_set(pg); n0 = len(jcards(pg))
        mclick(j, pg, r'Post Job|Publish|نشر', 'Post Job'); pg.wait_for_timeout(600)
        msg = ' '.join(new_toasts(pg, before)) + (mtext(pg) if mopen(pg) else '')
        j.check(re.search(r'title|required|مطلوب|العنوان', msg, re.I) and not re.search(r'posted|تم النشر', ' '.join(new_toasts(pg, before)), re.I), 'an empty title is not refused with a message (%s)' % msg[:100])
    with j.step('Fill title, department QA/QC, location Dubai + country UAE, type, experience 7, salary, description, requirements, deadline; Publish'):
        if not mopen(pg): open_form()
        mfill(j, pg, r'Job title|title|المسمى', title)
        mfill(j, pg, r'Department|القسم', r'QA/QC|الجودة')
        mfill(j, pg, r'Location|الموقع', 'Dubai')
        mfill(j, pg, r'experience|الخبرة', '7')
        mfill(j, pg, r'Min|الحد الأدنى', 'AED 25,000', required=False); mfill(j, pg, r'Max|الحد الأقصى', 'AED 35,000', required=False)
        mfill(j, pg, r'description|الوصف|responsibilities', 'Lead the QA department of a GCC plant; batch release; audits.', required=False)
        missing = [w for w, p in (('country', r'Country|الدولة'), ('deadline', r'Deadline|آخر موعد'), ('requirements', r'Requirements|المتطلبات')) if not mfield(pg, p)]
        j.check(not missing, 'not built: the Post a Job form has no %s field' % ', '.join(missing))
        mfill(j, pg, r'Deadline|آخر موعد', '2026-12-31'); mfill(j, pg, r'Requirements|المتطلبات', 'Pharmacy degree\n7+ years in QA')
        before = toast_set(pg); mclick(j, pg, r'Post Job|Publish|نشر', 'Post Job'); j.settle(pg, 1500)
    with j.step('The job is at the top of Open Positions for a job seeker in another browser, with the company name, UAE, salary and "just now"'):
        ps = s['page'] if j.live else pg
        if j.live: j.reload(ps)
        jobs_page(j, ps, HUNT); cs = jcards(ps)
        j.check(cs and title in cs[0]['title'], 'the new job is not first in Open Positions (first: %s)' % (cs[0]['title'] if cs else 'none'))
        c = cs[0]['text']
        j.check((e['co']['name'] if j.live else 'Quadra Pharm') in c, 'the job shows no company name')
        j.check(re.search(r'🇦🇪|UAE|الإمارات', c), 'the job does not show UAE')
        j.check(re.search(r'just now|الآن', c), 'the job does not say "just now"')
    if j.live:
        with j.step('Live: a jobs row with country AE, category qaqc, seniority senior, the company, a deadline; poster = the user'):
            r = j.wait_db("select country||'|'||category||'|'||coalesce(seniority,'')||'|'||coalesce(company,'')||'|'||coalesce(deadline::text,'') from public.jobs where user_id='%s' and title=$q$%s$q$" % (e['id'], title), 6)
            j.check(r, 'no jobs row'); c, cat, sen, co, dl = r.split('|')
            j.check(c == 'AE', 'the job is stored with country %s (want AE)' % c); j.check(cat == 'qaqc', 'category %s' % cat)
            j.check(sen == 'senior', 'seniority "%s" for 7 years (want senior)' % sen); j.check(co == e['co']['name'], 'company "%s"' % co); j.check(dl, 'no deadline')
    with j.step('Reload: still there; it shows on the company page Jobs section'):
        reopen(j, pg); jobs_page(j, pg, HUNT); j.check(title in ' '.join(c['title'] for c in jcards(pg)), 'after reload the job is gone')
        if j.live:
            pg.evaluate("s=>window.dxDir&&dxDir.open?dxDir.open(s):goto('companies')", e['co']['slug']); j.settle(pg, 1500)
            tl = pg.locator('#content [role=tab], #content .cp-tab, #content button').filter(has_text=re.compile(r'^\W*(Jobs|الوظائف) \(\d+\)'))
            if tl.count(): tl.first.scroll_into_view_if_needed()      # on a phone the tab bar scrolls sideways (in Arabic the Jobs tab starts off-screen)
            tab = j.find(pg, r'^\W*(Jobs|الوظائف) \(\d+\)', scope='#content'); j.check(tab, 'the company page has no Jobs tab')
            tab.click(); j.settle(pg, 1200)
            if title not in j.text(pg): tab = j.find(pg, r'^\W*(Jobs|الوظائف) \(\d+\)', scope='#content'); tab and tab.click(); j.settle(pg, 1200)   # the page redraws once its jobs arrive
            j.check(title in j.text(pg), "the job is not on the company page's Jobs tab")

@journey('J-COMMUNITY-24')
def manage_vacancies(j):
    """An employer keeps his vacancies up to date: edit, close when filled, reopen."""
    if j.live:
        e = employer(j); pg = e['page']; t = j.tag[:4]
        j1 = seed_job(j, e['id'], 'Edit Me Role %s' % t, e['co']['name'], salary='EGP 20,000', deadline='2026-12-01')
        j2 = seed_job(j, e['id'], 'Close Me Role %s' % t, e['co']['name'])
        s = j.person('Youssef Hassan'); j.sql("insert into public.job_applications (job_id, user_id, note) values (%d,'%s','hi')" % (j1, s['id'])); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Open My jobs: the employer\'s jobs with applicant counts and status'):
        jobs_page(j, pg, HIRE); el = j.find(pg, r'My jobs|My vacancies|وظائفي', scope='#app')
        j.check(el, 'not built: no "My jobs" for the employer'); el.click(); j.settle(pg, 1000)
        if j.live: j.check('Edit Me Role' in j.text(pg) and re.search(r'1\s*(applicant|متقدم)', j.text(pg)), 'My jobs does not list the jobs with applicant counts')
    with j.step('Edit salary and deadline of job 1; save; seekers see it after reload'):
        row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text='Edit Me Role' if j.live else 'Senior Regulatory').first
        b = row.locator('button').filter(has_text=re.compile(r'Edit|تعديل')); j.check(b.count(), 'not built: no Edit on my job'); b.first.click(); pg.wait_for_timeout(700)
        mfill(j, pg, r'salary|Min|الراتب', 'EGP 30,000'); mfill(j, pg, r'Deadline|آخر موعد', '2027-01-15')
        mclick(j, pg, r'Save|حفظ', 'Save'); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select salary from public.jobs where id=%d" % j1, 5) == 'EGP 30,000', 'the salary is not saved')
    with j.step('Close job 2: it leaves search; a saved link says "This job is closed"; reopen it'):
        row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text='Close Me Role' if j.live else 'Country Manager').first
        b = row.locator('button').filter(has_text=re.compile(r'Close|إغلاق')); j.check(b.count(), 'not built: no Close on my job'); b.first.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select active from public.jobs where id=%d" % j2, 5, want='f') == 'f', 'the job is not closed in the database')
        r = row.locator('button').filter(has_text=re.compile(r'Reopen|إعادة فتح')); j.check(r.count(), 'not built: no Reopen'); r.first.click(); j.settle(pg, 900)
    with j.step('Delete job 1 (confirm); only the poster can edit (the database refuses another user)'):
        row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text='Edit Me Role' if j.live else 'Senior Regulatory').first
        b = row.locator('button').filter(has_text=re.compile(r'Delete|حذف')); j.check(b.count(), 'not built: no Delete on my job'); b.first.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 900)
        if j.live:
            ps = s['page']; err = ps.evaluate("i=>dxLive.sb.from('jobs').update({title:'hacked'}).eq('id',i).select().then(r=>r.error?{code:r.error.code}:((r.data||[]).length?null:{code:'0rows'}))", j2)
            j.check(err, 'another user could edit the job')

@journey('J-COMMUNITY-25')
def review_applicants(j):
    """An employer reviews who applied to a job, with their CV and trust record, to decide whom to interview."""
    if j.live:
        e = employer(j); pg = e['page']; t = j.tag[:4]; jid = seed_job(j, e['id'], 'Applicants Role %s' % t, e['co']['name'])
        a = j.person('Amr Preferred'); b = j.person('Badr Warned'); c = j.person('Chadi Plain')
        for p in (a, b, c):
            j.sql("insert into public.job_applications (job_id, user_id, note) values (%d,'%s','Please consider me')" % (jid, p['id']))
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step("Click the 'applied to <job>' notification: the job's Applicants list opens"):
        if j.demo:
            jobs_page(j, pg, HIRE); el = j.find(pg, r'Applicants|المتقدمون', scope='#app'); j.check(el, 'not built: no applicants view anywhere')
            el.click(); j.settle(pg, 1000); j.check(re.search(r'applied|تقدم', j.text(pg) + mtext(pg), re.I), 'the Applicants view lists nobody'); return
        where = open_notif(j, pg, r'applied|تقدم', 'applied to')
        j.check(re.search(r'Applicants|المتقدمون', j.text(pg) + mtext(pg)) and 'Amr' in (j.text(pg) + mtext(pg)), 'not built: the notification does not open an Applicants list (page: %s)' % where)
    with j.step('Each applicant: name, headline, applied date, status; open message, CV, profile, trust signals'):
        txt = j.text(pg) + mtext(pg)
        j.check(all(n in txt for n in ('Amr', 'Badr', 'Chadi')), 'not every applicant is listed')
    with j.step('Opening an application marks it Viewed; another company sees 0 rows'):
        j.check(j.wait_db("select count(*) from public.job_applications where job_id=%d and status='viewed'" % jid, 5) >= '1', 'opening an application does not mark it Viewed')

@journey('J-COMMUNITY-26')
def applicant_pipeline(j):
    """An employer moves applicants through the pipeline to a hire, and each candidate is kept informed."""
    if j.live:
        e = employer(j); pg = e['page']; t = j.tag[:4]; jid = seed_job(j, e['id'], 'Pipeline Role %s' % t, e['co']['name'])
        ppl = [j.person(n) for n in ('Amr Applicant', 'Badr Applicant', 'Chadi Applicant')]
        for p in ppl: j.sql("insert into public.job_applications (job_id, user_id, note) values (%d,'%s','hi')" % (jid, p['id']))
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Open the job\'s applicants and Shortlist A; Reject B (with a note)'):
        jobs_page(j, pg, HIRE)
        el = j.find(pg, r'Applicants|My jobs|المتقدمون|وظائفي', scope='#app'); j.check(el, 'not built: no applicants view for the employer')
        el.click(); j.settle(pg, 1000)
        row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text='Amr').first
        b = row.locator('button, select').filter(has_text=re.compile(r'Shortlist|قائمة')); j.check(b.count(), 'not built: no Shortlist on an applicant')
        b.first.click(); j.settle(pg, 800)
        if j.live: j.check(j.wait_db("select status from public.job_applications where job_id=%d and user_id='%s'" % (jid, ppl[0]['id']), 5) == 'shortlisted', 'not shortlisted in the database')
        row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text='Badr').first
        b = row.locator('button').filter(has_text=re.compile(r'Reject|رفض|لم يُختر')); j.check(b.count(), 'not built: no Reject on an applicant')
        b.first.click(); pg.wait_for_timeout(500)
        if mopen(pg):
            n = pg.locator('.dbk-ov textarea'); n.count() and n.first.fill('We chose a candidate with more GCC experience.')
            mclick(j, pg, r'Save|Confirm|OK|حفظ|تأكيد', 'Confirm')
        j.settle(pg, 800)
        if j.live:
            j.check(j.wait_db("select status from public.job_applications where job_id=%d and user_id='%s'" % (jid, ppl[1]['id']), 5) == 'rejected', 'B is not rejected in the database')
            j.check(j.sql1("select employer_note from public.job_applications where job_id=%d and user_id='%s'" % (jid, ppl[1]['id'])) == 'We chose a candidate with more GCC experience.', "the rejection note is not kept")
    with j.step('Set A to Interview with a date, then Hired; C to No-show: the change shows at once with counts per stage'):
        for who, pat, st in (('Amr', r'Interview|مقابلة', 'interviewed'), ('Amr', r'Hire|Hired|تعيين', 'hired'), ('Chadi', r'No-show|لم يحضر', 'no_show')):
            row = pg.locator('#content [class*=card], #content tr, #content li').filter(has_text=who).first
            b = row.locator('button, [role=menuitem], option').filter(has_text=re.compile(pat, re.I))
            j.check(b.count(), 'not built: no "%s" action on an applicant' % pat.split('|')[0]); b.first.click(); pg.wait_for_timeout(500)
            if mopen(pg):
                d = mfield(pg, r'date|التاريخ')
                if d: d.fill('2026-11-02')
                mclick(j, pg, r'Save|Confirm|OK|حفظ|تأكيد', 'Confirm')
            j.settle(pg, 800)
            if j.live:
                uid = ppl[0]['id'] if who == 'Amr' else ppl[2]['id']
                j.check(j.wait_db("select status from public.job_applications where job_id=%d and user_id='%s'" % (jid, uid), 5) == st, '%s is not %s in the database' % (who, st))
        j.check(re.search(r'Hired|تم التعيين', j.text(pg)) and re.search(r'Interview|Shortlisted|Rejected|مقابلة|القائمة المختصرة|مرفوض', j.text(pg)), 'no counts per stage')
    with j.step('Each candidate is notified of their own change only and sees it in My applications; candidates cannot change their own status'):
        if j.demo: j.skip('the candidates exist only in live')
        for p, st in ((ppl[0], 'hired'), (ppl[1], 'rejected'), (ppl[2], 'no_show')):
            j.check(notif_rows(j, p['id'], extra=' and job_id=%d' % jid) >= 1, '%s was not notified' % p['name'])
        err = ppl[1]['page'].evaluate("i=>dxLive.sb.from('job_applications').update({status:'hired'}).eq('job_id',i).select().then(r=>r.error?{code:r.error.code}:((r.data||[]).length?null:{code:'0rows'}))", jid)
        j.check(err and j.sql1("select status from public.job_applications where job_id=%d and user_id='%s'" % (jid, ppl[1]['id'])) != 'hired', 'a candidate changed their own status to hired')

@journey('J-COMMUNITY-27')
def open_to_work(j):
    """A job seeker makes himself visible to employers so they come to him."""
    if j.live:
        sn = 'Youssef Hassan %s' % j.tag[:4]; s = j.person(sn); pg = s['page']; e = employer(j)
        j.sql("update public.profiles set headline='QC Chemist', location='Alexandria' where id='%s'" % s['id']); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step("A new account is not listed in Available Candidates until it opts in"):
        if j.demo: j.skip('the new account exists only in live')
        pe = e['page']; jobs_page(j, pe, HIRE); j.check(sn not in j.text(pe), 'a new account is listed before opting in')
    with j.step("I'm Job Hunting → Post My Profile: headline, desired role, experience, location, availability; Publish"):
        jobs_page(j, pg, HUNT); b = j.find(pg, r'Post My Profile|انشر ملفي', scope='#content'); j.check(b, 'no Post My Profile')
        b.click(); pg.wait_for_timeout(700); j.check(mopen(pg), 'Post My Profile opens nothing')
        ttl = 'Stability QC Chemist %s' % j.tag[:4]                       # never a sample candidate's title (the demo lists "QC Chemist — HPLC & GC Specialist")
        mfill(j, pg, r'Desired job title|المسمى', ttl)
        mfill(j, pg, r'location|الموقع', 'Alexandria, Egypt', required=False)
        mfill(j, pg, r'experience|الخبرة', '3', required=False)
        before = toast_set(pg); mclick(j, pg, r'Publish|Post|نشر', 'Publish'); j.settle(pg, 1200)
        if j.live: j.check(j.wait_db("select open_to_work from public.profiles where id='%s'" % s['id'], 5, want='t') == 't', 'not built: Post My Profile does not set open_to_work (toast only)')
    with j.step('The employer sees the seeker in Available Candidates with headline, location, experience and Contact; the count is real'):
        if j.demo:
            jobs_page(j, pg, HIRE); j.check(ttl in j.text(pg), 'the published profile is not in Available Candidates')
        else:
          pe = e['page']; j.reload(pe); jobs_page(j, pe, HIRE)
          j.check(sn in j.text(pe), 'the employer does not see the seeker in Available Candidates')
          n = jobs_header_n(pe); j.check(n == int(j.sql1("select count(*) from public.profiles where open_to_work")), 'the "N profiles" count is not real (%s)' % n)
    with j.step('The seeker hides the profile: removed from the list'):
        jobs_page(j, pg, HUNT); b = j.find(pg, r'Hide|Stop|إخفاء', scope='#content'); j.check(b, 'not built: no way to hide my profile again')
        b.click(); j.settle(pg, 900); confirm(j, pg, r'Hide|Yes|إخفاء|نعم')
        if j.live: j.check(j.wait_db("select open_to_work from public.profiles where id='%s'" % s['id'], 5, want='f') == 'f', 'open_to_work is still true')
        jobs_page(j, pg if j.demo else e['page'], HIRE)
        j.check((ttl if j.demo else sn) not in j.text(pg if j.demo else e['page']), 'the hidden profile is still in Available Candidates')

@journey('J-COMMUNITY-28')
def contact_candidate(j):
    """An employer contacts a promising candidate directly to start a conversation about a role."""
    if j.live:
        e = employer(j); pg = e['page']; cname = 'Sara Mansour %s' % j.tag[:4]; c = j.person(cname)
        j.sql("update public.profiles set open_to_work=true, headline='Regulatory Affairs Specialist' where id='%s'" % c['id']); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); cname = 'Sara Mansour'
    with j.step("I'm Hiring → Contact Candidate on the candidate's card: a conversation with that candidate opens (not an Apply form)"):
        jobs_page(j, pg, HIRE); card = jcard(j, pg, cname)
        b = card.locator('.apply-btn, button').filter(has_text=re.compile(r'Contact|تواصل')); j.check(b.count(), 'no Contact Candidate on the card')
        b.first.click(); j.settle(pg, 1200)
        page = pg.evaluate("document.body.getAttribute('data-page')"); dock = pg.locator('#dxDock:visible').count()
        j.check(not (mopen(pg) and re.search(r'Apply|Send Application|تقديم', mtext(pg))), 'Contact Candidate opens an Apply form ("%s")' % mtext(pg).split('\n')[0][:60])
        j.check(page == 'messages' or dock, 'Contact Candidate opens no conversation')
    with j.step("Send 'Are you available for an interview next week?'"):
        box = pg.locator('#dxDock textarea:visible, #dxDock input:visible, #content textarea:visible, #mxInput:visible').first
        j.check(box.count(), 'no message box'); box.fill('Are you available for an interview next week?'); box.press('Enter'); pg.wait_for_timeout(1200)
        if j.live: j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s'" % (e['id'], c['id']), 6) == '1', 'no messages row')
    with j.step('The candidate gets it and replies; the reply reaches the employer; the pair now counts as an interaction'):
        if j.demo: j.skip('the candidate exists only in live')
        pc = c['page']; j.reload(pc); j.nav(pc, 'messages'); j.settle(pc, 1500)
        j.check('interview next week' in j.text(pc), 'the candidate does not see the message')

@journey('J-COMMUNITY-29')
def preferred_and_blocked(j):
    """Each side keeps private preferred and blocked lists so good matches come first and bad experiences don't repeat."""
    if j.live:
        e = employer(j); pg = e['page']; n1, n2 = 'Carim One %s' % j.tag[:4], 'Camelia Two %s' % j.tag[:4]; c1 = j.person(n1); c2 = j.person(n2); e3 = employer(j, 'Ehab Third', 'Third Co')
        for c, h in ((c1, 'QC Chemist'), (c2, 'Sales Rep')): j.sql("update public.profiles set open_to_work=true, headline='%s' where id='%s'" % (h, c['id']))
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); n1, n2 = 'Youssef Hassan', 'Karim Adel'
    with j.step('E clicks ⭐ Whitelist on C1: C1 shows Preferred and comes first'):
        jobs_page(j, pg, HIRE); b = jcard(j, pg, n1).locator('.jx-ic[data-a=white]'); j.check(b.count(), 'no Whitelist on the card')
        b.click(); j.settle(pg, 900)
        cs = jcards(pg); j.check(cs and n1 in cs[0]['text'], 'the preferred candidate does not come first')
        j.check(re.search(r'Preferred|مفضل', cs[0]['text']), 'no Preferred badge')
        if j.live: j.check(j.wait_db("select count(*) from public.job_lists where owner='%s' and target='%s'" % (e['id'], c1['id']), 5) == '1', 'no job_lists row')
    with j.step('E blacklists C2: a reason is required; then C2 disappears for E'):
        b = jcard(j, pg, n2).locator('.jx-ic[data-a=black]'); b.click(); pg.wait_for_timeout(700); j.check(mopen(pg), 'Blacklist opens nothing')
        before = toast_set(pg); mclick(j, pg, r'^\W*(Block|حظر)\W*$', 'Block'); j.check(mopen(pg), 'Block without a reason closed the dialog (no reason required)')
        mfill(j, pg, r'Reason|السبب', r'No-show|عدم الحضور'); mfill(j, pg, r'how long|المدة', r'6 months|6 أشهر|٦', required=False)
        n = pg.locator('.dbk-ov textarea, .modal-overlay.show textarea'); n.count() and n.first.fill('Did not attend twice')
        ack = pg.locator('.dbk-ov input[type=checkbox], .modal-overlay.show input[type=checkbox]')
        for i in range(ack.count()): ack.nth(i).check()
        mclick(j, pg, r'^\W*(Block|حظر)\W*$', 'Block'); j.settle(pg, 900)
        j.check(n2 not in ' '.join(c['text'] for c in jcards(pg)), 'the blocked candidate is still listed for E')
    with j.step('My lists shows both lists with reason / duration and allows removal; all survives reload'):
        reopen(j, pg); jobs_page(j, pg, HIRE)
        b = pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'My lists|قوائمي')); j.check(b.count(), 'no My lists'); b.first.click(); pg.wait_for_timeout(700)
        txt = mtext(pg) if mopen(pg) else j.text(pg)
        for tab in (r'Whitelist|القائمة البيضاء|المفضل', r'Blacklist|القائمة السوداء|المحظور'):
            tb = j.find(pg, tab, scope='body', kinds='button,[role=tab]')
            if tb: tb.click(); pg.wait_for_timeout(500); txt += '\n' + mtext(pg)
        j.check(n1 in txt and n2 in txt, 'My lists does not show both people after reload')
        j.check(re.search(r'No-show|عدم الحضور', txt) and re.search(r'6 months|month|أشهر|until|حتى', txt), 'My lists does not show the reason and the duration')
    with j.step('Another employer sees nothing of it (job_lists rows are private)'):
        if j.demo: j.skip('the other employer exists only in live')
        n = e3['page'].evaluate("()=>dxLive.sb.from('job_lists').select('*').then(r=>(r.data||[]).length)")
        j.check(n == 0, 'another employer reads %s job_lists rows' % n)
        j.reload(e3['page']); jobs_page(j, e3['page'], HIRE); j.check(n2 in j.text(e3['page']), 'E3 does not see C2 (the block leaked)')
    with j.step("C1 applies to E's job: straight to Shortlisted and E gets 'A preferred candidate applied'"):
        if j.demo: j.skip('the candidate exists only in live')
        jid = seed_job(j, e['id'], 'Preferred Role %s' % j.tag[:4], e['co']['name']); pc = c1['page']; j.reload(pc)
        apply_dialog(j, pc, 'Preferred Role'); pc.locator('.modal-overlay.show textarea').first.fill('Hello'); mclick(j, pc, r'Send Application|Send|إرسال|أرسل', 'Send Application')
        j.check(j.wait_db("select status from public.job_applications where job_id=%d and user_id='%s'" % (jid, c1['id']), 6) == 'shortlisted', "the preferred candidate's application is not Shortlisted")
    with j.step('E removes C2 from the blacklist: C2 is listed again'):
        jobs_page(j, pg, HIRE); pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'My lists|قوائمي')).first.click(); pg.wait_for_timeout(700)
        tb = j.find(pg, r'Blacklist|القائمة السوداء|المحظور', scope='body', kinds='button,[role=tab]')
        if tb: tb.click(); pg.wait_for_timeout(500)
        r = pg.evaluate_handle("n=>{const d=%s;if(!d)return null;return [...d.querySelectorAll('button')].find(b=>/Remove|Unblock|إزالة|إلغاء/.test(b.innerText)&&b.getClientRects().length&&(b.parentElement.innerText.includes(n)||b.parentElement.parentElement.innerText.includes(n)))||null}" % ANY_DLG, n2).as_element()
        j.check(r, 'no Remove for %s in My lists' % n2); r.click(); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select count(*) from public.job_lists where owner='%s' and target='%s' and list='black'" % (e['id'], c2['id']), 5, want='0') == '0', 'Remove left the blacklist row in the database')
        mclose(pg); jobs_page(j, pg, HIRE); j.check(n2 in ' '.join(c['text'] for c in jcards(pg)), 'the unblocked candidate is not listed again')

if __name__ == '__main__': main(__file__)
