"""Community journeys — training: find a course, enrol in a free one, pay for a paid one, study lessons and keep the place,
earn a verifiable certificate, Drugbox publishing courses without SQL (J-COMMUNITY-35 … 40).
Run: python3 tests/journeys/community_training.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
import _dx

ENROLLED = r'Enrolled|مسج\u0651?ل|تم التسجيل'

def training(j, pg):
    tour_off(j, pg); close_dialogs(pg); mclose(pg); j.nav(pg, 'training'); j.settle(pg, 1200)
    if j.live: j.wait(pg, "document.querySelectorAll('#content .training-grid .tr-card').length>0", 8)
    return pg

def courses(pg):
    return pg.evaluate("""()=>[...document.querySelectorAll('#content .tr-card')].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!='none').map(c=>({
        title:((c.querySelector('.tr-title')||{}).innerText||'').trim(), text:c.innerText.replace(/\\s+/g,' ').trim(), btn:((c.querySelector('button')||{}).innerText||'').trim()}))""")

def course(j, pg, title):
    loc = pg.locator('#content .tr-card:visible').filter(has=pg.locator('.tr-title', has_text=title))
    j.check(loc.count(), 'no course card "%s" on Training (cards: %s)' % (title, ', '.join(c['title'] for c in courses(pg))[:160]))
    return loc.first

def seed_course(j, title, desc='', level='Beginner', duration='4 hours', active=True, emoji='🎓'):
    return int(j.sql1("insert into public.training_courses (title, description, level, duration, active, emoji, sort_order) values ($q$%s$q$, $q$%s$q$, '%s', '%s', %s, '%s', 1) returning id" % (title, desc, level, duration, 'true' if active else 'false', emoji)))

def open_course(j, pg, title):
    """Open a course's detail page from its card (title / card click)."""
    c = course(j, pg, title); before = j.text(pg); mark = j.toast_mark(pg)
    c.locator('.tr-title').click(); j.settle(pg, 1000); j.dead_end(pg, mark, 'the course card')
    j.check(mopen(pg) or j.text(pg) != before, 'not built: clicking the course card opens nothing (no course detail page)')
    return mtext(pg) if mopen(pg) else j.text(pg)

@journey('J-COMMUNITY-35')
def find_course(j):
    """A professional finds a course that will develop her skills (GMP, regulatory, formulation)."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; t = j.tag[:4]
        seed_course(j, 'Stability Protocol Design %s' % t, 'Zone IVb stability studies per ICH Q1A', 'Advanced', '6 hours')
        seed_course(j, 'GMP for Supervisors %s' % t, 'Good Manufacturing Practice basics', 'Beginner')
        j.reload(pg); n_db = int(j.sql1('select count(*) from public.training_courses where active'))
    else:
        pg = j.demo_signin(j.new_page()); n_db = None
    with j.step("Open Training: the 'N COURSES' count equals the courses offered"):
        training(j, pg); ui_ok(j, pg, 'Training')
        m = re.search(r'([\d٠-٩]+)\s*(COURSES|دورات|دورة)', j.text(pg)); j.check(m, "no 'N COURSES' count")
        n = num(m.group(1)); j.check(n == len(courses(pg)), "'%d COURSES' but %d cards" % (n, len(courses(pg))))
        if j.live: j.check(n == n_db, "'%d COURSES' but the database has %d active courses" % (n, n_db))
    with j.step("Filter by GMP / Regulatory / Formulation and by level; search 'stability': only matching courses"):
        f = j.find(pg, r'^\W*(GMP)\W*$', scope='#content', kinds='.cf-tag,button,[role=tab],[onclick],select')
        j.check(f, 'not built: no topic filter on Training (GMP / Regulatory / Formulation are only words in the header)')
        f.click(); j.settle(pg, 700); cs = courses(pg)
        j.check(cs and all(re.search(r'GMP|Manufactur', c['text'], re.I) for c in cs), 'the GMP filter shows other courses')
        box = pg.locator('#content input[type=search]:visible, #content input[placeholder*="earch" i]:visible')
        j.check(box.count(), 'not built: no course search'); box.first.fill('stability'); j.settle(pg, 900)
        j.check(all(re.search(r'stabil', c['text'], re.I) for c in courses(pg)) and courses(pg), "searching 'stability' does not narrow to stability courses")
    with j.step('Open a course card: syllabus (lessons with durations), instructor, level, duration, price (Free or EGP incl. VAT), certificate, enrolled count'):
        training(j, pg); d = open_course(j, pg, courses(pg)[0]['title'])
        missing = [k for k, p in (('syllabus / lessons', r'Lesson|Syllabus|Module|الدرس|المنهج'), ('instructor', r'Instructor|by |المحاضر|المدرب'), ('price', r'Free|EGP|مجاني|ج\.م'),
                                  ('certificate', r'Certificate|شهادة'), ('enrolled count', r'enrolled|مسجل')) if not re.search(p, d, re.I)]
        j.check(not missing, 'the course detail has no %s' % ', '.join(missing))

@journey('J-COMMUNITY-36')
def enrol_free(j):
    """A professional enrols in a free course and finds it again in her learning."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; t = j.tag[:4]; title = 'Free GMP Basics %s' % t; cid = seed_course(j, title, 'Free course on GMP basics'); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); title = 'GMP Fundamentals'
    with j.step('Enroll: the card shows Enrolled; the enrolled count +1'):
        training(j, pg); c = course(j, pg, title); n0 = num(re.search(r'([\d,]+)\s*(enrolled|مسجل)', c.inner_text()).group(1)) if re.search(r'([\d,]+)\s*(enrolled|مسجل)', c.inner_text()) else None
        b = c.locator('button').filter(has_text=re.compile(r'Enroll|سج\u0651?ل|التسجيل')); j.check(b.count(), 'no Enroll on the course')
        b.first.click(); j.settle(pg, 1000); confirm(j, pg, r'Enroll|Confirm|Yes|سجل|تأكيد')
        j.check(re.search(ENROLLED, course(j, pg, title).inner_text()), 'the card does not show Enrolled')
        if j.live:
            j.check(j.wait_db("select count(*) from public.course_enrollments where course_id=%d and user_id='%s'" % (cid, me['id']), 5) == '1', 'no course_enrollments row')
            j.check(j.sql1('select enrolled_count from public.training_courses where id=%d' % cid) == '1', 'enrolled_count is not 1')
    with j.step('Leave the page and come back, then reload: still Enrolled'):
        j.nav(pg, 'feed'); training(j, pg); j.check(re.search(ENROLLED, course(j, pg, title).inner_text()), 'after leaving the page the course is not Enrolled')
        reopen(j, pg); training(j, pg); j.check(re.search(ENROLLED, course(j, pg, title).inner_text()), 'after reload the course is not Enrolled')
    with j.step("My courses / My learning lists the course with 0% and 'Start'"):
        el = j.find(pg, r'My courses|My learning|دوراتي|تعلمي', scope='#app'); j.check(el, 'not built: no "My courses"')
        el.click(); j.settle(pg, 1000); t2 = j.text(pg) + mtext(pg)
        j.check(title in t2 and re.search(r'0\s*%', t2) and re.search(r'Start|ابدأ', t2), 'My courses does not list the course with 0% and Start')
    with j.step('Unenrol (confirm): the count goes back; a user cannot enrol someone else'):
        training(j, pg); c = course(j, pg, title); b = c.locator('button').filter(has_text=re.compile(r'Unenrol|Leave|Enrolled|إلغاء'))
        j.check(b.count(), 'not built: no way to unenrol'); b.first.click(); pg.wait_for_timeout(500); confirm(j, pg, r'Unenrol|Leave|Yes|إلغاء|نعم'); j.settle(pg, 900)
        j.check(not re.search(ENROLLED, course(j, pg, title).inner_text()), 'the course is still Enrolled after unenrolling')
        if j.live:
            j.check(j.wait_db("select count(*) from public.course_enrollments where course_id=%d" % cid, 5, want='0') == '0', 'the enrollment row is still there')
            other = seed_user(j, 'Someone Else')
            err = pg.evaluate("([c,u])=>dxLive.sb.from('course_enrollments').insert({course_id:c,user_id:u})" + _dx.ERR, [cid, other])
            j.check(err and j.sql1("select count(*) from public.course_enrollments where user_id='%s'" % other) == '0', 'a user enrolled someone else')

def seed_lessons(j, cid, n=6, video_first=True):
    """Live precondition: the course's lessons (0062) — lesson 1 a video, lesson 2 a PDF, the rest text."""
    kinds = ['video', 'pdf'] + ['text'] * (n - 2) if video_first else ['text'] * n
    for i in range(n):
        j.sql("insert into public.course_lessons (course_id, position, title, kind, minutes, body) values (%d, %d, $q$Part %d$q$, '%s', 10, $q$Notes for part %d$q$)" % (cid, i + 1, i + 1, kinds[i], i + 1))

def seed_quiz(j, cid):
    """Live precondition: a two-question final quiz (answers: first, second)."""
    j.sql("insert into public.course_questions (course_id, position, prompt, options, answer) values (%d, 1, 'Q one', '{right,wrong}', 0), (%d, 2, 'Q two', '{wrong,right}', 1)" % (cid, cid))

def lesson_win(pg):
    return pg.locator('.dbk-ov').last

@journey('J-COMMUNITY-37')
def buy_paid_course(j):
    """A professional pays for a paid course and gets access only after payment is confirmed."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; t = j.tag[:4]; title = 'Paid PV Course %s' % t
        cid = seed_course(j, title, 'Pharmacovigilance in practice'); j.sql("update public.training_courses set price_egp = 1000 where id = %d" % cid); seed_lessons(j, cid, 2)
        j.reload(pg); want = '1,140'
    else:
        pg = j.demo_signin(j.new_page()); title = 'GCC Market Access'; want = '1,710'
    with j.step('Find a paid course (price in EGP) and click Buy / Enroll: checkout shows the server price + 14% VAT'):
        training(j, pg); paid = [c for c in courses(pg) if re.search(r'EGP|ج\.م|\$', c['text'])]
        if j.live: j.check(j.has_column('training_courses', 'price') or j.has_column('training_courses', 'price_egp') or j.sql1("select count(*) from public.payment_products where kind ~ 'course'") != '0', 'not built: courses have no price (no price column, no course payment product)')
        j.check(paid, 'not built: no paid course on Training (every course is free / has no price)')
        j.check(any(c['title'] == title for c in paid), 'the paid course "%s" does not show its price' % title)
        c = course(j, pg, title); c.locator('button').first.click(); j.settle(pg, 1200)
        j.check(mopen(pg) and money(mtext(pg)), 'Buy opens no checkout with an amount')
        j.check(want in mtext(pg), 'the checkout total is not the server price + 14%% VAT (%s): %s' % (want, mtext(pg)[:200]))
    with j.step('Before payment the content is locked; after the card payment is confirmed the course unlocks and the user is notified'):
        mclose(pg); training(j, pg)
        j.check(not re.search(r'Start|Continue|ابدأ|متابعة', course(j, pg, title).inner_text()), 'the paid course content is open before payment')
        if j.live: j.check(j.sql1("select count(*) from public.course_enrollments where course_id=%d" % cid) == '0', 'enrolled before paying')
        course(j, pg, title).locator('button').first.click(); j.settle(pg, 1000)
        mclick(j, pg, r'Pay|ادفع', 'Pay')
        if j.demo:
            training(j, pg); j.check(re.search(r'Start|ابدأ', course(j, pg, title).inner_text()), 'the demo payment does not open the course')
        else:
            oid = j.wait_db("select id from public.payment_orders where user_id='%s' and course_id=%d order by id desc limit 1" % (me['id'], cid), 8)
            j.check(oid, 'no payment_orders row for the course')
            j.check(j.sql1("select amount_cents from public.payment_orders where id=%s" % oid) == '114000', 'the order is not the server price + VAT')
            st, body = paymob_callback(j, oid); j.check(st == 200, 'the payment callback was refused (%s %s)' % (st, body[:80]))
            j.check(j.wait_db("select count(*) from public.course_enrollments where user_id='%s' and course_id=%d and order_id=%s" % (me['id'], cid, oid), 8) == '1', 'no enrollment after the payment')
            reopen(j, pg); training(j, pg)
            j.check(re.search(r'Start|Continue|ابدأ|متابعة', course(j, pg, title).inner_text()), 'the course is still locked after payment')
            j.check(notif_rows(j, me['id'], extra=" and message ~* 'payment'") >= 1, "no 'Payment received' notification")
    with j.step('The browser cannot enrol itself in a paid course (only the server after payment)'):
        if j.demo: j.skip('checked in live')
        other = j.person('Free Rider'); err = other['page'].evaluate("c=>dxLive.sb.from('course_enrollments').insert({course_id:c,user_id:dxLive.uuidOf(ME.id)})" + _dx.ERR, cid)
        j.check(err and j.sql1("select count(*) from public.course_enrollments where user_id='%s'" % other['id']) == '0', 'the browser enrolled itself in a paid course')

@journey('J-COMMUNITY-38')
def study_lessons(j):
    """A learner studies the course content and keeps her place across sessions and devices."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; t = j.tag[:4]; title = 'Lessons Course %s' % t; cid = seed_course(j, title, 'Six lessons'); seed_lessons(j, cid, 6)
        j.sql("insert into public.course_enrollments (course_id, user_id) values (%d,'%s')" % (cid, me['id'])); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); title = 'GMP Fundamentals'
        training(j, pg); course(j, pg, title).locator('button').first.click(); j.settle(pg, 600)
    with j.step('Start the course → lesson 1 (video) opens in the app'):
        training(j, pg); c = course(j, pg, title)
        b = c.locator('button').filter(has_text=re.compile(r'Start|Continue|Open|ابدأ|متابعة'))
        if not b.count():
            open_course(j, pg, title); b = pg.locator('#content button:visible, .modal-overlay.show button:visible').filter(has_text=re.compile(r'Start|Continue|ابدأ|متابعة'))
        j.check(b.count(), 'not built: no Start / Continue on an enrolled course (no lessons)')
        b.first.click(); j.settle(pg, 1200)
        j.check(re.search(r'Lesson 1|الدرس 1|الدرس الأول', j.text(pg) + mtext(pg)), 'Start opens no lesson')
        j.check(pg.locator('video:visible, iframe:visible').count(), 'lesson 1 has no video')
        if j.live: j.check(pg.evaluate("(()=>{const v=document.querySelector('.dbk-ov video');return v?v.getAttribute('src'):''})()").find('/rest/v1/') < 0, 'the lesson video is not a storage link')
    with j.step('Mark lesson 1 complete; open lesson 2 (PDF); progress shows on My courses and the card'):
        b = j.find(pg, r'Mark complete|Complete|إكمال|تم', scope='body', kinds='button'); j.check(b, 'no "Mark complete"'); b.click(); j.settle(pg, 800)
        j.check(re.search(r'1\s*/\s*6|17\s*%|16\s*%', j.text(pg) + mtext(pg)), 'progress does not update')
        if j.live: j.check(j.wait_db("select count(*) from public.lesson_progress where user_id='%s' and course_id=%d" % (me['id'], cid), 5) == '1', 'no lesson_progress row')
        n = j.find(pg, r'Next lesson|الدرس التالي', scope='body', kinds='button'); j.check(n, 'no Next lesson'); n.click(); j.settle(pg, 900)
        j.check(re.search(r'Lesson 2|الدرس 2', mtext(pg)), 'Next does not open lesson 2')
        pdf = j.find(pg, r'PDF', scope='body', kinds='button'); j.check(pdf, 'lesson 2 has no PDF')
        with pg.context.expect_page(timeout=8000) as pop: pdf.click()
        j.check(pop.value, 'the lesson PDF does not open'); pop.value.close()
        mclose(pg); mclose(pg); training(j, pg); j.check(re.search(r'1\s*/\s*6', course(j, pg, title).inner_text()), 'the card does not show 1 / 6')
    with j.step('Sign in on another device: Continue resumes at lesson 2'):
        if j.demo: j.skip('the other device exists only in live')
        p2 = j.new_page(); j.signin(p2, me['email'], me['pw']); training(j, p2)
        course(j, p2, title).locator('button').filter(has_text=re.compile(r'Continue|متابعة')).first.click(); j.settle(p2, 1200)
        j.check(re.search(r'Lesson 2|الدرس 2', j.text(p2) + mtext(p2)), 'Continue does not resume at lesson 2 on another device')
    with j.step('Someone not enrolled cannot open the lessons (no direct link)'):
        if j.demo: j.skip('checked in live')
        o = j.person('Omar Outsider'); lid = int(j.sql1("select id from public.course_lessons where course_id=%d and position=1" % cid))
        err = o['page'].evaluate("l=>dxLive.sb.rpc('lesson_content',{p_lesson:l})" + _dx.ERR, lid); j.check(err, 'an outsider opened a lesson')
        err = o['page'].evaluate("c=>dxLive.sb.from('course_lessons').select('body').eq('course_id',c)" + _dx.ERR, cid); j.check(err, 'an outsider read lesson bodies')

@journey('J-COMMUNITY-39')
def certificate(j):
    """A learner who completes a course gets a verifiable certificate she can show employers."""
    if j.live:
        me = j.person('Mona Fathy'); pg = me['page']; t = j.tag[:4]; title = 'Certificate Course %s' % t; cid = seed_course(j, title); seed_lessons(j, cid, 2, video_first=False); seed_quiz(j, cid)
        j.sql("insert into public.course_enrollments (course_id, user_id) values (%d,'%s')" % (cid, me['id'])); j.reload(pg)
        right, wrong = (0, 1), (1, 1)
    else:
        pg = j.demo_signin(j.new_page()); title = 'ICH Guidelines'; right, wrong = (0, 0, 0), (1, 1, 1)
        training(j, pg); course(j, pg, title).locator('button').first.click(); j.settle(pg, 600)
    with j.step('Finish the lessons, then take the final quiz: failing does not complete the course; passing marks it Completed'):
        training(j, pg)
        for _ in range(8):
            b = course(j, pg, title).locator('button').filter(has_text=re.compile(r'Start|Continue|ابدأ|متابعة'))
            if not b.count(): break
            b.first.click(); j.settle(pg, 700); mclick(j, pg, r'Mark complete|تم الإنجاز', 'Mark complete'); mclose(pg); training(j, pg)
        open_course(j, pg, title)
        q = j.find(pg, r'Quiz|Final test|Exam|اختبار', scope='body'); j.check(q, 'not built: no final quiz')
        q.click(); j.settle(pg, 900)
        def answer(picks):
            for i, k in enumerate(picks): pg.locator('.dbk-ov input[name=trq%d]' % i).nth(k).check()
            mclick(j, pg, r'Submit|أرسل', 'Submit answers'); j.settle(pg, 900)
        answer(wrong); j.check(re.search(r'Not passed|لم تنجح', mtext(pg)), 'a failed quiz is not reported as failed')
        if j.live: j.check(j.sql1("select status from public.course_enrollments where course_id=%d and user_id='%s'" % (cid, me['id'])) == 'enrolled', 'failing completed the course')
        mclick(j, pg, r'Try again|حاول', 'Try again'); answer(right)
        j.check(re.search(r'Passed|ناجح', mtext(pg)), 'passing is not reported')
        if j.live: j.check(j.sql1("select status from public.course_enrollments where course_id=%d and user_id='%s'" % (cid, me['id'])) == 'completed', 'course_enrollments is not completed')
    with j.step('Open the certificate: name, course, date, hours and a unique ID; a public verify link; PDF download'):
        c = j.find(pg, r'Certificate|شهادة', scope='body'); j.check(c, 'not built: no certificate')
        c.click(); j.settle(pg, 900); txt = j.text(pg) + mtext(pg)
        j.check(pg.evaluate('ME.name') in txt and title in txt and re.search(r'ID|رقم', txt), 'the certificate lacks the name, the course or an ID')
        code = re.search(r'DBX-[0-9A-F]{10}', txt); j.check(code, 'the certificate has no unique ID'); code = code.group(0)
        link = pg.locator('.dbk-ov #trVerify').input_value(); j.check(code in link, 'no verify link with the ID')
        with pg.context.expect_page(timeout=8000) as pop: j.find(pg, r'Download PDF|تنزيل', scope='body', kinds='button').click()
        j.check(code in pop.value.content(), 'the PDF view does not show the certificate'); pop.value.close()
        if j.live: j.check(j.sql1("select count(*) from public.certificates where code='%s' and user_id='%s'" % (code, me['id'])) == '1', 'no certificates row')
    with j.step('Signed out, the verify link confirms the certificate'):
        ctx = pg.context.browser.new_context() if j.live else None   # live: a fresh browser, signed out; demo: the same browser (the demo keeps certificates here)
        po = (ctx or pg.context).new_page(); po.goto(link); po.wait_for_timeout(3000)
        v = po.locator('.dbk-ov').last.inner_text() if po.locator('.dbk-ov').count() else ''
        j.check(re.search(r'Valid|صحيحة', v) and pg.evaluate('ME.name') in v and code in v, 'the verify link does not confirm the certificate: %s' % v[:160])
        po.close()
        if ctx: ctx.close()
    with j.step('The certificate appears on her profile'):
        mclose(pg); j.nav(pg, 'profile'); j.settle(pg, 1500); j.check(title in j.text(pg), 'the certificate is not on the profile')

@journey('J-COMMUNITY-40', applies='live')
def publish_courses(j):
    """Drugbox publishes and maintains courses without SQL."""
    a = j.person('Adel Admin'); make_admin(j, a['id']); pg = a['page']; j.reload(pg); t = j.tag[:4]; title = 'Pharmacovigilance Basics %s' % t
    u = j.person('Mona Learner')
    with j.step('Admin → Training / Courses: Add course (title, description, level, duration, price, instructor, lessons)'):
        close_dialogs(pg); a_ = pg.locator("#app [onclick=\"goto('admin')\"]"); j.check(a_.count(), 'no Admin entry for a Drugbox admin')
        if not a_.first.is_visible() and pg.locator('#sbToggle:visible').count(): pg.click('#sbToggle'); pg.wait_for_timeout(400)
        a_.first.click(); j.settle(pg, 1200)
        el = j.find(pg, r'Training|Courses|التدريب|الدورات', scope='#content'); j.check(el, 'not built: Admin has no Training / Courses section (courses are added with SQL only)')
        el.click(); j.settle(pg, 900)
        b = j.find(pg, r'Add course|New course|إضافة دورة', scope='body'); j.check(b, 'not built: no "Add course" in Admin'); b.click(); pg.wait_for_timeout(700)
        mfill(j, pg, r'Title|العنوان', title); mfill(j, pg, r'Description|الوصف', 'Signal detection and ICSRs'); mfill(j, pg, r'Level|المستوى', 'Beginner')
        mfill(j, pg, r'^Duration|^المدة', '3 hours'); mfill(j, pg, r'Price|السعر', '0'); mfill(j, pg, r'^Instructor$|^المحاضر$', 'Dr. Adel PV')
        mclick(j, pg, r'Publish|Save|Create|نشر|حفظ', 'Publish')
        j.check(j.wait_db("select count(*) from public.training_courses where title=$q$%s$q$ and active" % title, 5) == '1', 'no training_courses row')
        cid = int(j.sql1("select id from public.training_courses where title=$q$%s$q$" % title))
        row = pg.locator('#adminContent tr').filter(has_text=title); j.check(row.count(), 'the new course is not listed in Admin → Training')
        row.locator('[data-trles]').click(); pg.wait_for_timeout(700)
        mfill(j, pg, r'Lesson title|عنوان الدرس', 'What is an ICSR'); mfill(j, pg, r'^Text$|^النص$', 'An individual case safety report is…')
        mclick(j, pg, r'Add lesson|إضافة الدرس', 'Add lesson')
        j.check(j.wait_db("select count(*) from public.course_lessons where course_id=%d" % cid, 5) == '1', 'no course_lessons row')
        mclose(pg); row = pg.locator('#adminContent tr').filter(has_text=title); row.locator('[data-trqz]').click(); pg.wait_for_timeout(700)
        mfill(j, pg, r'^Question|^السؤال', 'ICSR stands for?'); mfill(j, pg, r'Answers|الإجابات', 'Individual case safety report\nInternal cost summary'); mfill(j, pg, r'right answer|الإجابة الصحيحة', '1')
        mclick(j, pg, r'Add question|إضافة السؤال', 'Add question')
        j.check(j.wait_db("select answer from public.course_questions where course_id=%d" % cid, 5) == '0', 'no course_questions row with its answer')
        mclose(pg)
    with j.step('A user sees the new course; edits show after reload; a deactivated course leaves the catalog'):
        pu = u['page']; j.reload(pu); training(j, pu); course(j, pu, title)
        row = pg.locator('#adminContent tr').filter(has_text=title); row.locator('[data-tredit]').click(); pg.wait_for_timeout(700)
        mfill(j, pg, r'Description|الوصف', 'Signal detection, ICSRs and PSURs'); mclick(j, pg, r'Save|حفظ', 'Save')
        j.check(j.wait_db("select description from public.training_courses where id=%d" % cid, 5) == 'Signal detection, ICSRs and PSURs', 'the edit is not saved')
        j.reload(pu); training(j, pu); j.check('PSURs' in course(j, pu, title).inner_text(), 'the edit does not show after reload')
        j.sql("insert into public.course_enrollments (course_id, user_id) values (%d, '%s')" % (cid, u['id']))
        row = pg.locator('#adminContent tr').filter(has_text=title); row.locator('[data-tract]').click(); j.settle(pg, 900)
        j.check(j.wait_db("select active from public.training_courses where id=%d" % cid, 5, want='f') == 'f', 'the course is not deactivated')
        other = j.person('Nadia Newcomer'); j.reload(other['page']); training(j, other['page'])
        j.check(title not in j.text(other['page']), 'the deactivated course is still in the catalog')
        j.reload(pu); training(j, pu); course(j, pu, title)   # its learner keeps it
    with j.step('A non-admin cannot manage courses (RLS)'):
        err = u['page'].evaluate("t=>dxLive.sb.from('training_courses').insert({title:t+' x'})" + _dx.ERR, title)
        j.check(err and j.sql1("select count(*) from public.training_courses where title=$q$%s x$q$" % title) == '0', 'a non-admin created a course')
        err = u['page'].evaluate("c=>dxLive.sb.from('course_lessons').insert({course_id:c,position:9,title:'x lesson'})" + _dx.ERR, cid)
        j.check(err, 'a non-admin added a lesson')

if __name__ == '__main__': main(__file__)
