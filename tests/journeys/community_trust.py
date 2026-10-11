"""Community journeys — the jobs trust layer: reviews after a real interaction, honorable records, evidence-backed warnings,
the candidate's reply / dispute, and who may see which signal (J-COMMUNITY-30 … 34).
Run: python3 tests/journeys/community_trust.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
import _dx

def stars(pg, v=4):
    for i in range(4):
        s = pg.locator('.dbk-ov .jx-stars[data-i="%d"] .jx-star[data-v="%d"]' % (i, v))
        if s.count(): s.first.click()

def rating_text(j, pg, name):
    c = jcard(j, pg, name); r = c.locator('.jx-rate'); j.check(r.count(), 'no ★ rating on the card of %s' % name)
    r.first.click(); pg.wait_for_timeout(900); t = mtext(pg); mclose(pg); return t, c.inner_text()

@journey('J-COMMUNITY-30')
def reviews(j):
    """People and companies rate each other after a real interaction, so trustworthy employers and candidates stand out."""
    t = j.tag[:4]; body = 'Clear interview process, answered within a week and explained the salary band. %s' % t
    if j.live:
        e = employer(j, 'Ehab Employer', 'Indovista Pharma'); s = j.person('Youssef Hassan %s' % t); pg = s['page']; f = employer(j, 'Fady NoContact', 'Beauty Lab')
        je = seed_job(j, e['id'], 'Reviewed Role %s' % t, e['co']['name']); seed_job(j, f['id'], 'Unrelated Role %s' % t, f['co']['name'])
        j.sql("insert into public.job_applications (job_id, user_id, note) values (%d,'%s','hi')" % (je, s['id']))
        j.sql("update public.profiles set open_to_work=true, headline='QC Chemist' where id='%s'" % s['id'])
        j.reload(pg); fcard, ecard = 'Unrelated Role %s' % t, 'Reviewed Role %s' % t; sname = 'Youssef Hassan %s' % t
    else:
        pg = j.demo_signin(j.new_page()); fcard, ecard = 'Cosmetic Formulation Scientist', 'QC Analyst (HPLC)'; sname = 'Youssef Hassan'
    with j.step("Without an interaction: Write a review on F's card explains why and opens no form"):
        jobs_page(j, pg, HUNT); ts = card_act(j, pg, fcard, 'write', 'Write a review')
        j.check(not pg.locator('.dbk-ov #jxT').count(), 'a review form opens without any interaction')
        j.check(re.search(r'after applying|after contacting|بعد', ' '.join(ts)), 'no message explains why (%s)' % ts)
        if j.live: j.check(j.sql1("select count(*) from public.job_reviews where reviewer='%s'" % s['id']) == '0', 'a review was stored')
    with j.step("After applying: E's card → Write a review; a text under 20 characters is refused; a valid anonymous review is published"):
        if j.demo:
            apply_dialog(j, pg, ecard); pg.locator('.modal-overlay.show textarea').first.fill('I would like to apply.'); mclick(j, pg, r'Send Application|إرسال|أرسل', 'Send Application')
        jobs_page(j, pg, HUNT); card_act(j, pg, ecard, 'write', 'Write a review')
        j.check(pg.locator('.dbk-ov #jxT').count(), 'no review form after a real interaction')
        stars(pg, 4); pg.fill('.dbk-ov #jxT', 'Too short'); mclick(j, pg, r'Publish review|Publish|نشر', 'Publish review')
        j.check(mopen(pg), 'a too-short review was published')
        pg.fill('.dbk-ov #jxT', body); j.check(pg.locator('.dbk-ov #jxAnon').count(), 'no anonymous option'); tick(pg, '#jxAnon')
        mclick(j, pg, r'Publish review|Publish|نشر', 'Publish review'); j.settle(pg, 1200)
        if j.live: j.check(j.wait_db("select anonymous from public.job_reviews where reviewer='%s' and reviewee='%s'" % (s['id'], e['id']), 6) == 't', 'no anonymous job_reviews row')
    with j.step("Reload; E's ★ rating lists the review as Anonymous (no name) and the count went up"):
        reopen(j, pg); jobs_page(j, pg, HUNT); rt, ct = rating_text(j, pg, ecard)
        j.check(body[:30] in rt, "E's reviews do not include the new review")
        me = pg.evaluate('ME.name'); j.check(me not in rt and re.search(r'Anonymous|Verified applicant|مجهول|متقدم', rt), 'the anonymous review leaks the name or is not marked anonymous')
        if j.live:
            g = pg.evaluate("u=>dxLive.sb.rpc('get_reviews',{p:u,p_role:'employer'}).then(r=>JSON.stringify(r.data||r.error))", e['id'])
            j.check(s['id'] not in g and 'Youssef' not in g and re.search(r'Anonymous|Verified applicant', g), 'get_reviews leaks the reviewer: %s' % g[:200])
    with j.step('Edit the review (one per pair: it is replaced); delete it: removed and the average recomputed'):
        card_act(j, pg, ecard, 'write', 'Write a review')
        j.check(pg.locator('.dbk-ov #jxT').count() and body[:20] in pg.input_value('.dbk-ov #jxT'), 'writing again does not edit my review (the form is empty)')
        pg.fill('.dbk-ov #jxT', body + ' Edited.'); mclick(j, pg, r'Publish|Update|Save|نشر|تحديث|حفظ', 'Update review'); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select count(*)||'|'||max(body) from public.job_reviews where reviewer='%s' and reviewee='%s'" % (s['id'], e['id']), 5).startswith('1|') and 'Edited' in j.sql1("select body from public.job_reviews where reviewer='%s'" % s['id']), 'editing did not replace the one review')
        rt, _ = rating_text(j, pg, ecard)
        c = jcard(j, pg, ecard); c.locator('.jx-rate').first.click(); pg.wait_for_timeout(800)
        d = j.find(pg, r'Delete|Remove|حذف', scope='body', kinds='button')
        j.check(d, 'not built: no Delete for my own review'); d.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 900); mclose(pg)
        rt, _ = rating_text(j, pg, ecard); j.check(body[:30] not in rt, 'the deleted review is still listed')
    with j.step("E reviews S, signed with the company name (companies cannot post anonymously); S is notified"):
        if j.demo: j.skip('the employer side of the same pair exists only in live')
        pe = e['page']; j.reload(pe); jobs_page(j, pe, HIRE); card_act(j, pe, sname, 'write', 'Write a review')
        j.check(pe.locator('.dbk-ov #jxT').count(), 'the employer gets no review form for an applicant')
        j.check(not pe.locator('.dbk-ov #jxAnon').count(), 'a company is offered anonymity')
        stars(pe, 5); pe.fill('.dbk-ov #jxT', 'Punctual and well prepared for the technical interview. %s' % t); mclick(j, pe, r'Publish|نشر', 'Publish review')
        j.check(j.wait_db("select count(*) from public.job_reviews where reviewer='%s' and reviewee='%s' and not anonymous" % (e['id'], s['id']), 6) == '1', 'no signed review row')
        j.check(notif_rows(j, s['id'], extra=" and type ~ 'review'") >= 1, 'S was not notified of the review')

@journey('J-COMMUNITY-31')
def honor_record(j):
    """A former employer publishes an honourable work record so a good employee's track record is public."""
    if j.live:
        e = employer(j); sname = 'Karim Adel %s' % j.tag[:4]; s = j.person(sname); pg = e['page']; employment(j, e['id'], s['id'], e['co'])
        j.sql("update public.profiles set open_to_work=true, headline='Medical Sales Representative' where id='%s'" % s['id']); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); sname = 'Nour Farouk'
    def ref_form():
        jobs_page(j, pg, HIRE); card_act(j, pg, sname, 'ref', 'Work reference'); j.check(mopen(pg) and pg.locator('#rfText').count(), 'Work reference opens no form')
    with j.step("S's card → Work reference → Honorable record: facts under 40 characters or no confirmation are refused"):
        ref_form(); mclick(j, pg, r'Honorable record|سجل مشرف', 'Honorable record')
        pg.locator('.dbk-ov #rfFrom').last.fill('2022-01'); pg.locator('.dbk-ov #rfTo').last.fill('2024-12'); pg.locator('.dbk-ov #rfRole').last.fill('Medical Sales Representative')
        pg.locator('.dbk-ov #rfText').last.fill('Great colleague.'); tick(pg, '#rfAck'); mclick(j, pg, r'Submit reference|Submit|إرسال|أرسل', 'Submit reference')
        j.check(mopen(pg), 'facts under 40 characters were accepted')
        pg.locator('.dbk-ov #rfText').last.fill(FACTS); tick(pg, '#rfAck', False); mclick(j, pg, r'Submit reference|Submit|إرسال|أرسل', 'Submit reference')
        j.check(mopen(pg), 'a reference without the confirmation was accepted')
    with j.step('With facts ≥ 40 and the confirmation: published at once — on the public Honor list and the card shows Honor ×N'):
        tick(pg, '#rfAck'); mclick(j, pg, r'Submit reference|Submit|إرسال|أرسل', 'Submit reference'); j.settle(pg, 1200)
        if j.live: j.check(j.wait_db("select status from public.work_references where author='%s' and candidate='%s' and kind='honor'" % (e['id'], s['id']), 6) == 'published', 'no published honor row')
        jobs_page(j, pg, HIRE); j.check(re.search(r'Honor ×\s*\d|(تكريم|شرف)\s*×\s*[\d٠-٩]', jcard(j, pg, sname).inner_text()), "the card does not show 'Honor ×N'")
        b = pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'Honor list|قائمة الشرف')); j.check(b.count(), 'no Honor list'); b.first.click(); pg.wait_for_timeout(800)
        j.check(sname in mtext(pg) and FACTS[:25] in mtext(pg), 'the Honor list does not show the record'); mclose(pg)
    with j.step("S is notified ('added an honorable work record to your profile') and the record is on S's profile"):
        if j.demo: j.skip('the candidate exists only in live')
        ps = s['page']; j.reload(ps); open_notif(j, ps, r'honorable|honou?r|سجل', 'honorable record')
        j.check(FACTS[:25] in j.text(ps) + mtext(ps), 'the notification does not lead to the record')
    with j.step('S replies to the record: the reply shows under it'):
        if j.demo: j.skip('the candidate exists only in live')
        b = j.find(ps, r'Reply|رد', scope='body', kinds='button'); j.check(b, 'not built: S has no Reply on the record'); b.click(); ps.wait_for_timeout(500)
        ta = ps.locator('.dbk-ov textarea, #content textarea:visible').first; ta.fill('Thank you, it was a pleasure.'); mclick(j, ps, r'Send|Save|Reply|إرسال|أرسل|حفظ', 'Send reply')
        j.check(j.wait_db("select count(*) from public.work_references where candidate='%s' and reply like 'Thank you%%'" % s['id'], 5) == '1', 'the reply is not stored')
    with j.step('E withdraws it: removed everywhere'):
        jobs_page(j, pg, HIRE); b = pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'Honor list|قائمة الشرف')); b.first.click(); pg.wait_for_timeout(800)
        w = j.find(pg, r'Withdraw|سحب', scope='body', kinds='button'); j.check(w, 'not built: no Withdraw for my own reference'); w.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 900)
        if j.live: j.check(j.wait_db("select count(*) from public.work_references where author='%s' and candidate='%s'" % (e['id'], s['id']), 5, want='0') == '0', 'the reference is still stored')

@journey('J-COMMUNITY-32')
def warning_reference(j):
    """An employer warns other employers about serious misconduct, backed by evidence, without defaming anyone."""
    if j.live:
        e = employer(j); sname = 'Karim Adel %s' % j.tag[:4]; s = j.person(sname); pg = e['page']; e3 = employer(j, 'Eman Third', 'Third Pharma')
        j.sql("update public.profiles set verified=true where id in ('%s','%s')" % (e['id'], e3['id'])); employment(j, e['id'], s['id'], e['co'])
        j.sql("update public.profiles set open_to_work=true, headline='Medical Sales Representative' where id='%s'" % s['id']); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); sname = 'Youssef Hassan'
    with j.step("S's card → Work reference → Warning: category, dates, role, facts; Submit without evidence is refused with a reason"):
        jobs_page(j, pg, HIRE); card_act(j, pg, sname, 'ref', 'Work reference'); j.check(mopen(pg), 'Work reference opens nothing')
        mclick(j, pg, r'^\W*(Warning|تحذير)\W*$', 'Warning')
        mfill(j, pg, r'Category|Reason|الفئة|السبب', r'Left without notice|ترك العمل')
        pg.locator('.dbk-ov #rfFrom').last.fill('2022-01'); pg.locator('.dbk-ov #rfTo').last.fill('2024-12'); pg.locator('.dbk-ov #rfRole').last.fill('QC Chemist'); pg.locator('.dbk-ov #rfText').last.fill(WARN)
        if pg.locator('#rfAck').count(): tick(pg, '#rfAck')
        before = toast_set(pg); mclick(j, pg, r'Submit|إرسال|أرسل', 'Submit reference')
        j.check(mopen(pg), 'a warning without evidence was submitted')
        j.check(re.search(r'evidence|إثبات|دليل', ' '.join(new_toasts(pg, before)) + mtext(pg), re.I), 'no message says evidence is needed')
    with j.step("Attach the evidence and Submit: E sees 'Pending Drugbox review'"):
        fi = pg.locator('.dbk-ov input[type=file]'); j.check(fi.count(), 'not built: no evidence file field'); fi.first.set_input_files(PDF); pg.wait_for_timeout(600)
        before = toast_set(pg); mclick(j, pg, r'Submit|إرسال|أرسل', 'Submit reference'); j.settle(pg, 1300)
        j.check(re.search(r'Pending|review|مراجعة', ' '.join(new_toasts(pg, before)) + j.text(pg)), "E is not told it is 'Pending Drugbox review'")
        if j.live:
            r = j.wait_db("select status||'|'||coalesce(category,'')||'|'||coalesce(evidence_path,'') from public.work_references where author='%s' and candidate='%s' and kind='warn'" % (e['id'], s['id']), 6)
            j.check(r and r.startswith('pending|Left without notice|'), 'the warning row is %s (want pending, category, evidence)' % r)
            ev = r.split('|')[2]; j.check(j.sql1("select count(*) from storage.objects where bucket_id='reference-evidence' and name='%s'" % ev) == '1' and ev.startswith(e['id']), 'the evidence is not in reference-evidence/<author>/')
    with j.step('S is notified and can reply or dispute before publication; nobody else (a verified employer included) sees it while pending'):
        if j.demo: j.skip('the other people exist only in live')
        ps = s['page']; j.reload(ps); open_notif(j, ps, r'warning|reference|تحذير|مرجع', 'warning')
        j.check(re.search(r'Reply|Dispute|رد|اعتراض', j.text(ps) + mtext(ps)), 'S has no Reply / Dispute')
        n = e3['page'].evaluate("u=>dxLive.sb.from('work_references').select('id').eq('candidate',u).then(r=>(r.data||[]).length)", s['id'])
        j.check(n == 0, 'a verified employer reads the pending warning')
    with j.step('Only E and moderators can open the evidence'):
        if j.demo: j.skip('checked in live')
        ev = j.sql1("select evidence_path from public.work_references where author='%s' and kind='warn'" % e['id'])
        url = e3['page'].evaluate("p=>dxLive.sb.storage.from('reference-evidence').createSignedUrl(p,60).then(r=>r.data&&r.data.signedUrl||'')", ev)
        j.check(not url, 'another employer can open the evidence')

@journey('J-COMMUNITY-33', applies='live')   # the demo account is the employer, never the person warned about
def dispute_warning(j):
    """A person warned about can tell his side and dispute an unfair warning before it is published."""
    if j.live:
        e = employer(j); s = j.person('Karim Adel %s' % j.tag[:4]); ps = s['page']
        employment(j, e['id'], s['id'], e['co']); rid = seed_ref(j, e['id'], s['id'], 'warn', body=WARN, category='Left without notice')
        j.reload(ps)
    else:
        ps = j.demo_signin(j.new_page())
    with j.step('S clicks the notification: the warning about S opens with Reply / Dispute (not the evidence file)'):
        if j.demo: j.skip('the demo account is the employer, never the person warned about — checked in live')
        open_notif(j, ps, r'reference|warning|مرجع|تحذير', 'reference about you')
        txt = j.text(ps) + mtext(ps)
        j.check(WARN[:25] in txt, 'the notification does not open the warning')
        j.check(re.search(r'Reply|رد', txt) and re.search(r'Dispute|اعتراض', txt), 'no Reply / Dispute on the warning')
    with j.step('Write a reply and choose Dispute: saved, shown next to the warning; status disputed'):
        if j.demo: j.skip('checked in live')
        b = j.find(ps, r'Dispute|اعتراض', scope='body', kinds='button'); b.click(); ps.wait_for_timeout(500)
        ta = ps.locator('.dbk-ov textarea, #content textarea:visible').first; j.check(ta.count(), 'no reply box'); ta.fill('I resigned in writing with a month of notice; the letter is signed by HR.')
        mclick(j, ps, r'Dispute|Send|إرسال|أرسل|اعتراض', 'Send dispute')
        if j.live: j.check(j.wait_db("select status from public.work_references where id=%d" % rid, 5) == 'disputed', 'the warning is not disputed')
    with j.step('After the moderator decided, a second dispute is refused; only the reply can be updated'):
        if j.demo: j.skip('the moderator exists only in live')
        j.sql("update public.work_references set status='rejected', decided_at=now() where id=%d" % rid)
        err = ps.evaluate("i=>dxLive.sb.rpc('reply_to_reference',{ref_id:i,reply_text:'again',dispute:true})" + _dx.ERR, rid)
        j.check(err, 'a second dispute after the decision was accepted')

@journey('J-COMMUNITY-34')
def trust_visibility(j):
    """Trust signals are shown to the right audience only, so the trust layer is useful and fair."""
    if j.live:
        s = j.person('Karim Adel %s' % j.tag[:4]); v = employer(j, 'Vera Verified', 'Verified Pharma'); u = j.person('Umar Unverified')
        a1 = seed_user(j, 'Old Boss One'); a2 = seed_user(j, 'Old Boss Two'); a3 = seed_user(j, 'Old Boss Three')
        for a_ in (a1, a2, a3): employment(j, a_, s['id'])
        j.sql("update public.profiles set verified=true where id='%s'" % v['id'])
        j.sql("update public.profiles set open_to_work=true, headline='Medical Sales Representative' where id='%s'" % s['id'])
        seed_ref(j, a1, s['id'], 'honor')
        pub = seed_ref(j, a1, s['id'], 'warn', 'published', WARN, 'Left without notice')
        exp = seed_ref(j, a2, s['id'], 'warn', 'published', WARN.replace('two', 'three'), 'Breach of confidentiality', "now() - interval '1 day'")
        rej = seed_ref(j, a3, s['id'], 'warn', 'rejected', WARN.replace('two', 'four'), 'False documents or certificates')
        for p in (v, u, s): j.reload(p['page'])
        sname = 'Karim Adel %s' % j.tag[:4]
    else:
        pg = j.demo_signin(j.new_page()); sname = 'Karim Adel'
    with j.step("A verified employer sees S's ratings, honors and only the published, unexpired warning"):
        pg = v['page'] if j.live else pg
        jobs_page(j, pg, HIRE); c = jcard(j, pg, sname).inner_text()
        j.check(re.search(r'warning|تحذير', c), 'the verified employer does not see the published warning on the card')
        b = pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'Warning list|قائمة التحذير')); j.check(b.count(), 'no Warning list'); b.first.click(); pg.wait_for_timeout(800)
        wl = mtext(pg); mclose(pg); j.check(sname in wl, 'the Warning list does not include S')
        if j.live: j.check('three' not in wl and 'four' not in wl, 'the Warning list shows an expired or rejected warning')
    with j.step('Top rated / Honor list reflect real data'):
        b = pg.locator('#content .jx-tool:visible').filter(has_text=re.compile(r'Honor list|قائمة الشرف')); b.first.click(); pg.wait_for_timeout(800)
        hn = sname if j.live else 'Sara Mansour'                        # the demo's honoured candidate
        j.check(hn in mtext(pg), 'the Honor list does not include %s' % hn); mclose(pg)
    with j.step('An unverified member sees no warning at all (card, list and REST)'):
        if j.demo: j.skip('the unverified member exists only in live')
        pu = u['page']; jobs_page(j, pu, HIRE)
        j.check(not re.search(r'warning|تحذير', jcard(j, pu, sname).inner_text()), 'an unverified member sees the warning on the card')
        n = pu.evaluate("c=>dxLive.sb.from('work_references').select('id').eq('candidate',c).eq('kind','warn').then(r=>(r.data||[]).length)", s['id'])
        j.check(n == 0, 'an unverified member reads %s warnings through REST' % n)
        n = v['page'].evaluate("c=>dxLive.sb.from('work_references').select('id').eq('candidate',c).eq('kind','warn').then(r=>(r.data||[]).map(x=>x.id))", s['id'])
        j.check(n == [pub], 'a verified employer reads warnings %s (want only the published one %d)' % (n, pub))
    with j.step('S sees the warnings about himself'):
        if j.demo: j.skip('S exists only in live')
        n = s['page'].evaluate("c=>dxLive.sb.from('work_references').select('id').eq('candidate',c).then(r=>(r.data||[]).length)", s['id'])
        j.check(n == 4, 'S reads %s of the 4 references about him' % n)

if __name__ == '__main__': main(__file__)
