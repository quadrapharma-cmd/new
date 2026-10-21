"""Community journeys — Drugbox decisions: company verification, claims, wrong-information reports, warning references,
site certificates, InstaPay confirmations, content reports, decision notifications, accountability and who may reach Admin
(J-COMMUNITY-41 … 50). Run: python3 tests/journeys/community_admin.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
from _biz import workspace, directory, open_card as co_open, add_or_claim, create_company, wizard_details, live_company_person, seed_site, seed_cert, seed_listing
import _dx

PLAN = 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة')

def admin_person(j, name='Drugbox Admin'):
    a = j.person(name); make_admin(j, a['id']); j.reload(a['page']); a['page'].wait_for_timeout(600); tour_off(j, a['page']); return a

def demo_unverified(j, pg, name):
    """Demo: a new, unverified company made through the create wizard (Quadra Pharm is verified already)."""
    create_company(j, pg, name); wizard_details(j, pg, name)
    dlg_click(j, pg, r'Next: review|التالي', 'Next: review'); dlg_click(j, pg, r'Create my page|أنشئ', 'Create my page'); j.settle(pg, 1200); close_dialogs(pg)

def send_verification(j, pg, registry):
    t = workspace(j, pg, PLAN)
    el = j.find(pg, r'Get verified|وثّق|احصل على التوثيق|Send for verification', scope='#content'); j.check(el, "no 'Get verified' on an unverified company")
    el.click(); pg.wait_for_timeout(800)
    fill_by_label(j, pg, r'registry|السجل', registry)
    files = pg.locator('.dbk-ov input[type=file]')
    j.check(files.count() >= 3, 'not built: verification takes %d document upload(s) — registry, tax card and licence are three' % files.count())
    for i in range(files.count()): files.nth(i).set_input_files(PDF)
    dlg_click(j, pg, r'Send for verification|Send|أرسل', 'Send for verification'); j.settle(pg, 1500)

@journey('J-COMMUNITY-41')
def verify_company(j):
    """A company gets the verified badge after Drugbox checks its official documents, so buyers can trust it."""
    t = j.tag[:4]
    if j.live:
        o = live_company_person(j, 'Omar Owner', 'Verify Me Pharma %s' % t, status='pending'); pg = o['page']; name = o['co']['name']; cid = o['co']['id']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Verify Me Pharma %s' % t; demo_unverified(j, pg, name)
    with j.step("O: Get verified → registry number + registry, tax card and licence PDFs → send; the page says 'Under review'"):
        send_verification(j, pg, '7781%s' % t)
        j.check(re.search(r'Under review|being checked|قيد المراجعة|قيد الفحص', workspace(j, pg, PLAN)), "the owner does not see 'Under review'")
        if j.live:
            j.check(j.wait_db("select status from public.verification_requests where company_id=%s" % cid, 6) == 'pending', 'no pending verification_requests row')
            j.check(j.sql1("select count(*) from storage.objects where bucket_id='documents' and name like 'verification/%%'") != '0', 'the documents are not stored privately under documents/verification/')
    with j.step('A non-admin sees no queue (no Admin entry, 0 rows through REST)'):
        if j.demo: j.skip('the demo account is a Drugbox admin — checked in live')
        j.check(not pg.locator("#app [onclick=\"goto('admin')\"]:visible").count(), 'a normal member sees the Admin entry')
        n = pg.evaluate("()=>dxLive.sb.from('verification_requests').select('id').then(r=>(r.data||[]).length)")
        j.check(n <= 1, 'a non-admin reads %s verification requests' % n)
    with j.step('Admin → Review → Verification requests: company, registry, date and the three documents (signed links)'):
        if j.demo: ap = pg
        else: a = admin_person(j); ap = a['page']
        txt = admin_review(j, ap, 'verifications')
        if name not in txt and t in txt:
            shown = next((l for l in txt.split('\n') if t in l), '')
            j.fail('the company name is changed on screen: "%s" is shown as "%s" (the interface translates a company\'s own name)' % (name, shown.strip()))
        j.check(name in txt, 'the request is not in the queue'); ui_ok(j, ap, 'Admin → Review')
        row = ap.locator('.dx-mod-row', has_text=name).first
        j.check(re.search(r'7781', row.inner_text()), 'the registry number is not shown')
        docs = row.locator('.dx-mod-doc, a[href*="token"], a[href*="sign"]'); j.check(docs.count() >= 3, 'the reviewer can open %d document(s) (want 3)' % docs.count())
    with j.step("Reject with 'Tax card expired': O gets 'needs another look: Tax card expired' that opens the company page; O can resubmit"):
        decide(j, ap, name, False, 'Tax card expired')
        if j.live:
            j.check(j.wait_db("select status||'|'||coalesce(note,'') from public.verification_requests where company_id=%s" % cid, 6) == 'rejected|Tax card expired', 'the rejection and note are not stored')
            j.reload(pg); where = open_notif(j, pg, r'another look|Tax card|مراجعة', 'needs another look')
            j.check(re.search(r'Tax card expired', j.text(pg) + ' '.join(pg.evaluate('window.__jt||[]'))) or where in ('companies', 'company'), 'the notification does not show the note or open the company page (page %s)' % where)
        send_verification(j, pg, '7781%s' % t)
    with j.step("Approve: the request leaves the queue; O gets 'Your company is verified ✓'; the badge shows everywhere"):
        txt = admin_review(j, ap, 'verifications'); decide(j, ap, name, True)
        j.check(name not in admin_review(j, ap, 'verifications'), 'the approved request stays in the queue')
        if j.live:
            j.check(j.wait_db("select status from public.companies where id=%s" % cid, 6) == 'verified', 'the company is not verified')
            j.check(j.sql1("select reviewed_by is not null and reviewed_at is not null from public.verification_requests where company_id=%s order by id desc limit 1" % cid) == 't', 'reviewed_by / reviewed_at not stored')
            j.check(notif_rows(j, o['id'], extra=" and message ~* 'verified'") >= 1, "no 'Your company is verified' notification")
        directory(j, pg); pg.fill('#hbQ', name); j.wait(pg, "n=>[...document.querySelectorAll('#dxDir .dr-card')].some(c=>c.innerText.includes(n))", 10, name)   # a directory of hundreds: found the way a person does
        j.check(pg.locator('#dxDir .dr-card', has_text=name).locator('.dr-seal').count(), 'no Verified badge on the directory card')

@journey('J-COMMUNITY-42')
def claim_page(j):
    """A real representative claims an unclaimed company page so the company controls its own information."""
    t = j.tag[:4]
    if j.live:
        c = j.person('Claire Claimant'); pg = c['page']; co = seed_company(j, None, 'Unclaimed Nile Pharma %s' % t, status='unclaimed', source='public_list'); name = co['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Nile Valley Pharmaceuticals'
    with j.step("C opens U → 'This is my company' / Claim, adds a note, submits: 'Your claim is under review'"):
        add_or_claim(j, pg, name if j.live else name)
        row = j.find(pg, r'^\W*(Claim|طالب بها|طالب)\W*$', scope='body'); j.check(row, "no 'Claim' for the unclaimed page")
        row.click(); pg.wait_for_timeout(800)
        pg.fill('.dbk-ov #clRole', 'Regulatory Manager'); pg.fill('.dbk-ov #clPhone', '+20 100 777 8899'); pg.fill('.dbk-ov #clMail', 'ra@nilepharma.com')
        note = pg.locator('.dbk-ov textarea'); note.count() and note.first.fill('I am the regulatory manager there')
        # the commercial registry document (claim_company refuses a claim without it, business 0052)
        doc = pg.locator('.dbk-ov #clDoc'); j.check(doc.count(), 'the claim window does not ask for the commercial registry document')
        doc.set_input_files(files=[{'name': 'registry.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-1.4\n% registry of Nile Pharma\n%%EOF\n'}])
        before = toast_set(pg); dlg_click(j, pg, r'Send claim|Send request|Send code|Send|أرسل', 'Send'); j.settle(pg, 1200)
        if dlg_open(pg) and pg.locator('.dbk-ov #clCode').count():                     # the demo proves the work e-mail with a code
            code = re.search(r'code:?\s*(\d{4,6})', dlg_text(pg)); j.check(code, 'the code step shows no way to get the code')
            pg.fill('.dbk-ov #clCode', code.group(1)); dlg_click(j, pg, r'Claim page|Claim|طالب', 'Claim page'); j.settle(pg, 1200)
        said = ' '.join(new_toasts(pg, before))
        j.check(re.search(r'under review|pending|Drugbox checks|قيد المراجعة|تراجع', said + ' ' + j.text(pg)[:2000], re.I), "C is not told 'Your claim is under review' (%s)" % said[:100])
        if j.live: j.check(j.wait_db("select count(*) from public.verification_requests where company_id=%s and claim" % co['id'], 6) == '1', 'no claim verification_requests row')
    with j.step("C claims again: refused ('already under review')"):
        add_or_claim(j, pg, name); row = j.find(pg, r'^\W*(Claim|طالب بها|طالب)\W*$', scope='body')
        if row:
            row.click(); pg.wait_for_timeout(800)
            before = toast_set(pg)
            if dlg_open(pg) and pg.locator('.dbk-ov #clRole').count():
                pg.fill('.dbk-ov #clRole', 'Regulatory Manager'); pg.fill('.dbk-ov #clPhone', '+20 100 777 8899'); pg.fill('.dbk-ov #clMail', 'ra@nilepharma.com')
                if pg.locator('.dbk-ov #clDoc').count(): pg.locator('.dbk-ov #clDoc').set_input_files(files=[{'name': 'registry.pdf', 'mimeType': 'application/pdf', 'buffer': b'%PDF-1.4\n%%EOF\n'}])
                dlg_click(j, pg, r'Send claim|Send request|Send code|Send|أرسل', 'Send'); j.settle(pg, 1000)
                if dlg_open(pg) and pg.locator('.dbk-ov #clCode').count():
                    code = re.search(r'code:?\s*(\d{4,6})', dlg_text(pg)); pg.fill('.dbk-ov #clCode', code.group(1) if code else '0000'); dlg_click(j, pg, r'Claim page|Claim|طالب', 'Claim page')
            j.check(re.search(r'already|سبق|قيد المراجعة', ' '.join(new_toasts(pg, before)) + dlg_text(pg), re.I), 'a second claim is not refused (%s)' % ' '.join(new_toasts(pg, before))[:100])
        if j.live: j.check(j.sql1("select count(*) from public.verification_requests where company_id=%s" % co['id']) == '1', 'a second claim row was stored')
    with j.step("Admin → Review: the claim is marked as a claim with C's name and note; approve"):
        if j.demo: j.skip('the claim decision is checked in live')
        a = admin_person(j); ap = a['page']; txt = admin_review(j, ap, 'claims')   # Admin → Review → Claims (business B-01)
        row = ap.locator('.dx-mod-row', has_text=name).first; j.check(row.count(), 'the claim is not in the queue')
        j.check(re.search(r'Claim|مطالبة', row.inner_text()) and 'Claire' in row.inner_text(), "the row is not marked as a claim with C's name")
        decide(j, ap, name, True)
        j.check(j.wait_db("select owner_id from public.companies where id=%s" % co['id'], 6) == c['id'], 'C is not the owner after approval')
    with j.step('C is told to send documents for verification and can now edit the page'):
        if j.demo: j.skip('checked in live')
        j.reload(pg); open_notif(j, pg, r'claim|مطالبة', 'claim approved')
        j.check(re.search(r'document|verif|مستندات|توثيق', ' '.join(pg.evaluate('window.__jt||[]')) + j.text(pg)), 'C is not told to submit documents for verification')

@journey('J-COMMUNITY-43')
def wrong_info_report(j):
    """Wrong company information gets reported and corrected so the directory stays accurate."""
    t = j.tag[:4]; issue = 'Factory moved to Obour %s' % t
    if j.live:
        r = j.person('Rami Reporter'); o = live_company_person(j, 'Olfat Owner', 'Reported Pharma %s' % t); pg = r['page']; name = o['co']['name']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'
    with j.step('R opens K → Report wrong information: section, issue, correction; send'):
        directory(j, pg); co_open(j, pg, name)
        j.click(pg, L('Report wrong information'), scope='#content', what='Report wrong information')
        fill_by_label(j, pg, r'Where|أين|القسم', r'Sites|المواقع'); fill_by_label(j, pg, r'What is wrong|ما الخطأ|الخطأ', issue)
        fill_by_label(j, pg, r'correct|التصحيح|الصحيح', 'Obour City, zone A', required=False)
        dlg_click(j, pg, L('Send report'), 'Send report'); j.settle(pg, 1000)
    with j.step('R sees the report in own reports with status Open'):
        el = j.find(pg, r'My reports|بلاغاتي', scope='#app'); j.check(el, 'not built: the reporter has no "My reports"')
        el.click(); j.settle(pg, 900)
        # the list opens in the approved dialog: the row that names this issue says Open
        row = pg.evaluate("""t=>{const root=[...document.querySelectorAll('.dbk-ov')].pop()||document.querySelector('#content');
          const els=[...root.querySelectorAll('*')].filter(e=>(e.innerText||'').includes(t)).sort((a,b)=>a.innerText.length-b.innerText.length);
          const r=els.find(e=>/Open|مفتوح/.test(e.innerText));return r?r.innerText:(els.length?'(no status) '+els[0].innerText:'')}""", issue)
        j.check(issue in row and re.search(r'Open|مفتوح', row) and len(row) < 400, 'my reports do not list it as Open: %s' % row[:120])
    with j.step("O sees it without R's identity; Mark fixed tells O that Drugbox closes it"):
        if j.demo: j.skip('the owner side is checked in live')
        po = o['page']; t2 = workspace(j, po, 'Reports & reviews|%s' % (ar('Reports & reviews') or 'التقارير'))
        j.check(issue in t2 and 'Rami' not in t2, "the owner does not see the report, or sees the reporter's name")
        before = toast_set(po); j.click(po, L('Mark fixed', extra='تم الإصلاح|تم التصحيح'), scope='#content', what='Mark fixed'); j.settle(po, 1200)
        j.check(re.search(r'Drugbox', ' '.join(new_toasts(po, before)) + j.text(po)), 'Mark fixed does not say Drugbox closes it')
    with j.step('Admin → Review → Company reports: company, section, issue, correction; Resolve removes it; R is told'):
        if j.demo: j.skip('checked in live')
        a = admin_person(j); ap = a['page']; txt = admin_review(j, ap, 'reports'); j.check(issue in txt, 'the report is not in the queue')
        decide(j, ap, issue, True); j.check(issue not in admin_review(j, ap, 'reports'), 'the resolved report stays in the queue')
        j.check(j.wait_db("select status from public.company_reports where issue=$q$%s$q$" % issue, 6) == 'resolved', 'not resolved in the database')
        j.check(notif_rows(j, r['id'], extra=" and created_at > now() - interval '10 minutes'") >= 1, 'the reporter is not told the outcome')

@journey('J-COMMUNITY-44')
def moderate_warnings(j):
    """A moderator checks warning references against their evidence before anyone is harmed by them."""
    if j.live:
        e = j.person('Ehab Employer'); s = j.person('Sami Candidate'); d = j.person('Dina Disputer'); v = j.person('Vera Verified')
        j.sql("update public.profiles set verified=true where id='%s'" % v['id'])
        co = employment(j, e['id'], s['id']); employment(j, e['id'], d['id'], co)
        t = j.tag[:4]; wbody = WARN + ' Case %s.' % t   # this run's own rows (a shared database keeps older runs' Sami and Dina)
        w = seed_ref(j, e['id'], s['id'], 'warn', body=wbody, category='Left without notice')
        dd = seed_ref(j, e['id'], d['id'], 'warn', 'disputed', WARN.replace('two', 'three') + ' Case %s.' % t, 'Breach of confidentiality', reply='I never had access to that data.')
        a = admin_person(j); ap = a['page']
    else:
        ap = j.demo_signin(j.new_page())
        with j.step('Demo: the employer (the demo account) files a warning with evidence about a candidate'):
            jobs_page(j, ap, HIRE); card_act(j, ap, 'Youssef Hassan', 'ref', 'Work reference'); mclick(j, ap, r'^\W*(Warning|تحذير)\W*$', 'Warning')
            mfill(j, ap, r'Category|Reason|الفئة|السبب', r'Left without notice|ترك العمل')
            ap.locator('.dbk-ov #rfFrom').last.fill('2022-01'); ap.locator('.dbk-ov #rfTo').last.fill('2024-12'); ap.locator('.dbk-ov #rfRole').last.fill('QC Chemist'); ap.locator('.dbk-ov #rfText').last.fill(WARN)
            if ap.locator('.dbk-ov #rfAck').count(): tick(ap, '#rfAck')
            fi = ap.locator('.dbk-ov input[type=file]'); j.check(fi.count(), 'no evidence field'); fi.first.set_input_files(PDF)
            mclick(j, ap, r'Submit|إرسال|أرسل', 'Submit reference'); j.settle(ap, 1200)
    with j.step('Admin → Review → Warning references: company, candidate, category, facts, reply / dispute, evidence (signed link)'):
        txt = admin_review(j, ap, 'Warning references|التحذير')
        if j.demo:
            j.check('Youssef' in txt and WARN[:20] in txt, 'the warning just filed is not in the queue')
            j.check(ap.locator('.dx-mod-row', has_text='Youssef').locator('.dx-mod-doc, a').count(), 'the evidence cannot be opened')
        else:
            j.check('Sami' in txt and 'Left without notice' in txt and WARN[:20] in txt, 'the pending warning is not shown with candidate, category and facts')
            j.check('I never had access' in txt, "the disputed warning does not show the candidate's reply")
            j.check(ap.locator('.dx-mod-row', has_text='Sami').locator('.dx-mod-doc, a').count(), 'the evidence cannot be opened')
    with j.step('Publish W; Reject D: both decisions stored (decided_by / decided_at)'):
        if j.demo:
            decide(j, ap, 'Youssef', True); j.check('Youssef' not in admin_review(j, ap, 'Warning references|التحذير'), 'the published warning stays in the queue'); return
        decide(j, ap, wbody[-10:], True); decide(j, ap, 'three batches were delayed by a week. Case %s.' % t, False, 'Not supported by the evidence')
        j.check(j.wait_db("select status||'|'||(decided_by is not null) from public.work_references where id=%s" % w, 6) == 'published|true', 'W is not published with decided_by')
        j.check(j.wait_db("select status from public.work_references where id=%s" % dd, 6) == 'rejected', 'D is not rejected')
    with j.step('Author and candidate are notified; a verified employer sees W with "Evidence verified" and the expiry'):
        if j.demo: j.skip('checked in live')
        j.check(notif_rows(j, e['id'], extra=" and created_at > now() - interval '10 minutes'") >= 1 and notif_rows(j, s['id']) >= 1, 'author or candidate not notified')
        n = v['page'].evaluate("c=>dxLive.sb.from('work_references').select('id,expires_at').eq('candidate',c).then(r=>(r.data||[]))", s['id'])
        j.check(len(n) == 1 and n[0]['expires_at'], 'the verified employer does not read the published warning with an expiry')
    with j.step('A non-moderator cannot call moderate_reference'):
        if j.demo: j.skip('checked in live')
        err = e['page'].evaluate("i=>dxLive.sb.rpc('moderate_reference',{ref_id:i,new_status:'published'})" + _dx.ERR, int(dd))
        j.check(err and j.sql1("select status from public.work_references where id=%s" % dd) == 'rejected', 'a non-moderator changed a reference')

@journey('J-COMMUNITY-45')
def check_certificates(j):
    """Drugbox checks uploaded site certificates (GMP, ISO, CEP) so 'level 3' trust is real."""
    t = j.tag[:4]
    if j.live:
        o = live_company_person(j, 'Olfat Owner', 'Cert Pharma %s' % t); sid = seed_site(j, o['co']['id'], 'Obour plant %s' % t)
        c1 = seed_cert(j, o['co']['id'], sid, 'WHO-GMP %s' % t, checked=False); c2 = seed_cert(j, o['co']['id'], sid, 'ISO 9001 %s' % t, checked=False)
        a = admin_person(j); ap = a['page']; n1, n2, name = 'WHO-GMP %s' % t, 'ISO 9001 %s' % t, o['co']['name']
    else:
        ap = j.demo_signin(j.new_page()); n1, n2, name = 'ISO 22000', 'حلال' if j.ar else 'Halal', 'Sinai Herbal Extracts'   # the sample certificate's approved Arabic name
    with j.step('Admin → Review → Site certificates: unchecked, unexpired certificates with company, site, name, expiry; the badge count matches'):
        txt = admin_review(j, ap, 'certs'); j.check(n1 in txt and n2 in txt and name in txt, 'the certificates are not in the queue')
        badge = num(ap.evaluate("((document.querySelectorAll('.dx-mod-tab')[2]||{}).innerText||'')"))
        j.check(badge == ap.locator('.dx-mod-row').count(), 'the badge says %s, the queue has %d' % (badge, ap.locator('.dx-mod-row').count()))
        j.check(re.search(r'20\d\d|expir|ينتهي', txt), 'the expiry date is not shown')
    with j.step('Mark one Checked: it leaves the queue and shows verified on the company page; the owner is notified'):
        decide(j, ap, n1, True); j.check(n1 not in admin_review(j, ap, 'certs'), 'the checked certificate stays in the queue')
        if j.live:
            j.check(j.sql1('select checked_at is not null from public.site_certificates where id=%s' % c1) == 't', 'checked_at not set')
            j.check(notif_rows(j, o['id'], extra=" and created_at > now() - interval '10 minutes'") >= 1, 'the owner is not notified')
    with j.step('Reject the other with a note: the owner sees the reason'):
        row = ap.locator('.dx-mod-row', has_text=n2).first; j.check(row.locator('.dx-mod-no').count(), 'not built: a certificate cannot be rejected (only "Mark checked")')
        decide(j, ap, n2, False, 'The scan is unreadable')
        if j.live: j.check(notif_rows(j, o['id'], extra=" and message ~* 'unreadable'") >= 1, 'the owner does not see the reason')

@journey('J-COMMUNITY-46')
def instapay_confirm(j):
    """A user who pays by InstaPay gets the paid product activated after Drugbox confirms the transfer."""
    t = j.tag[:4]
    if j.live:
        s = live_company_person(j, 'Sherif Supplier', 'Sherif API Co %s' % t, sectors=('API & excipients',)); pg = s['page']
        lid = seed_listing(j, s['id'], 'Boost Me API %s' % t); title = 'Boost Me API %s' % t; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); title = None
    with j.step('Supplier → Boost listing → InstaPay: amount + address; transfer reference + receipt; submit → "Waiting for confirmation" with the order reference'):
        close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
        tab = pg.locator('#content .master-tab').filter(has_text=re.compile(r'My Listings|قوائمي|إعلاناتي'))
        if tab.count(): tab.first.click(); j.settle(pg, 900)
        b = pg.locator('#content [onclick^="openBoostModal"]:visible').first
        if not b.count(): b = pg.locator('[onclick="openBoostModal(\'boost\')"]:visible').first
        j.check(b.count(), 'no Boost for my listing'); b.click(); j.settle(pg, 1200)
        j.check(pg.locator('#boostModalOverlay.show, #boostModalOverlay:visible').count(), 'Boost opens no payment window')
        if j.live:
            v = pg.evaluate("n=>{const s=document.getElementById('dxPayListing');if(!s)return null;const o=[...s.options].find(o=>o.textContent.includes(n));if(!o)return null;s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));return o.value}", title)
            j.check(v, 'my listing is not offered in the payment window')
        m = pg.locator('#boostModalOverlay input[value=instapay]'); j.check(m.count(), 'no InstaPay option'); m.first.evaluate('e=>e.click()')
        pg.click('#bmPayBtn'); j.settle(pg, 3000)
        txt = mtext(pg); j.check(money(txt) and re.search(r'@|InstaPay address|عنوان', txt), 'InstaPay shows no amount and address (%s)' % txt[:120].replace('\n', ' / '))
        ref = pg.locator('.dbk-ov #dxIpRef, .dbk-ov input[type=text]:visible').first; j.check(ref.count(), 'no transfer reference field'); ref.fill('IP%s998877' % t)
        fi = pg.locator('.dbk-ov input[type=file]'); j.check(fi.count(), 'no receipt upload'); fi.first.set_input_files(PNG)
        before = toast_set(pg); mclick(j, pg, r'Send for confirmation|Submit|Send|أرسل', 'Send for confirmation'); j.settle(pg, 2000)
        said = ' '.join(new_toasts(pg, before)) + ' ' + mtext(pg) + ' ' + j.text(pg)
        j.check(re.search(r'Waiting|working day|confirm|بانتظار|يوم عمل|تأكيد', said), "no 'Waiting for confirmation'")
        j.check(re.search(r'DBX\d+', said), 'the supplier is not shown the order reference (DBX…)')
        if j.live: oid = j.wait_db("select id from public.payment_orders where user_id='%s' and method='instapay' and status='review'" % s['id'], 6); j.check(oid, 'no payment_orders row in review')
    with j.step('Admin → Review → Payments: who, product, amount incl. VAT, transfer ref, receipt (signed link); Confirm'):
        if j.demo: j.skip('the confirmation is checked in live')
        a = admin_person(j); ap = a['page']; txt = admin_review(j, ap, 'payments')
        j.check('Sherif' in txt and ('IP%s998877' % t) in txt and money(txt), 'the payment row lacks who / ref / amount')
        decide(j, ap, 'IP%s998877' % t, True)
        j.check(j.wait_db("select status from public.payment_orders where id=%s" % oid, 6) == 'paid', 'the order is not paid')
    with j.step("The supplier is notified 'Payment received — … is active' and the listing is Boosted for others"):
        if j.demo: j.skip('checked in live')
        j.check(notif_rows(j, s['id'], extra=" and message ~* '(payment|active)'") >= 1, 'the supplier is not notified')
        j.check(j.sql1("select count(*) from public.products where id=%s and (boosted_until > now() or featured_until > now())" % lid) == '1', 'the listing is not boosted')

@journey('J-COMMUNITY-47')
def content_reports(j):
    """Harmful posts, people and groups can be reported to Drugbox and acted on, so the network stays professional."""
    t = j.tag[:4]
    if j.live:
        m = j.person('Mona Member'); pg = m['page']; z = seed_user(j, 'Zaki Spammer'); f = j.person('Fake Profile %s' % t)
        p = j.sql1("insert into public.posts (user_id, body) values ('%s', $q$Buy ready-made dossiers now %s$q$) returning id" % (z, t))
        j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','accepted')" % (m['id'], z)); j.reload(pg); body = 'Buy ready-made dossiers now %s' % t
    else:
        pg = j.demo_signin(j.new_page()); body = None
    with j.step('M reports P (reason) and reports the fake profile F'):
        j.nav(pg, 'feed'); j.settle(pg, 1200)
        post = pg.locator('#content .post', has_text=body).first if body else pg.locator('#content .post').filter(has_not=pg.locator('.post-name', has_text=pg.evaluate('ME.name'))).first
        j.check(post.count(), 'the post is not in the feed')
        menu(j, pg, post, r'Report|إبلاغ', 'Report')
        if dlg_open(pg):
            r = pg.locator('.dbk-ov input[type=radio], .dbk-ov label').first; r.count() and r.click()
            dlg_click(j, pg, r'Report|Send|Submit|إبلاغ|إرسال|أرسل', 'Send report')
    with j.step("M reports the fake profile F from F's profile (⋯ → Report, 'Fake profile'): stored once (social S-09)"):
        # demo: a sample member stands in for F; live: F's own account
        floc = pg.evaluate("u=>dxLive.aid(u)", f['id']) if j.live else 6
        fname = ('Fake Profile %s' % t) if j.live else pg.evaluate("id=>U(id).name", floc)
        close_dialogs(pg); pg.evaluate("id=>gotoProfile(id)", floc); j.settle(pg, 1500)
        j.click(pg, r'^(⋯|More: report or block|المزيد: إبلاغ أو حظر)', scope='#content', what='⋯ (more)')
        j.click(pg, r'^\W*(Report|إبلاغ)$', scope='body', what='Report', exact=True)
        pg.check('.dbk-ov input[name=dxMRep][value=fake], .modal-bg input[name=dxMRep][value=fake]')
        pg.fill('#dxMRepN', 'Impersonates a QA manager ' + t)
        j.click(pg, r'^(Report|إبلاغ)$', scope='body', what='Report (confirm)', exact=True); pg.wait_for_timeout(800)
        j.check(any(re.search(r'Thanks|شكراً', x) for x in j.toasts(pg)), 'no confirmation after reporting F')
        if j.live: j.check(j.wait_db("select count(*) from public.member_reports where reported='%s' and reporter='%s' and reason='fake' and status='open'" % (f['id'], m['id']), 6) == '1', 'the report of F is not stored')
    with j.step('Admin → Review has a content-reports queue with reason, reporter, content and count'):
        ap = admin_person(j)['page'] if j.live else pg
        close_dialogs(ap); admin_review(j, ap, 'verifications')
        tabs = ' | '.join(ap.evaluate("[...document.querySelectorAll('.dx-mod-tab')].map(t=>t.innerText.trim())"))
        j.check(re.search(r'Content|Posts|Reported posts|Reports|بلاغات المحتوى|منشورات', tabs.replace('Company reports', '')), 'not built: Admin → Review has no queue for reported posts / people (queues: %s)' % tabs)
        # the people queue (social S-09): F with the reason, how many reports and from how many members
        tab = ap.locator('.dx-mod-tab').filter(has_text=re.compile(r'Reported members|الأعضاء المبلغ عنهم')); j.check(tab.count(), 'no Reported members queue (queues: %s)' % tabs)
        tab.first.click(); ap.wait_for_timeout(800)
        frow = ap.locator('.dx-mod-row').filter(has_text=fname)
        j.check(frow.count() == 1, 'F is not listed once in Reported members')
        j.check(re.search(r'Fake profile|حساب مزيف', frow.first.inner_text()) and re.search(r'1 reports? from 1 members?|بلاغ', frow.first.inner_text()), 'the F row lacks the reason or the count (%s)' % frow.first.inner_text()[:160])
    with j.step('Remove P (deleted for everyone, Z told the reason) and suspend F; F cannot post and sees why'):
        q = body or ''
        tab = ap.locator('.dx-mod-tab').filter(has_text=re.compile(r'Content|Posts|Reported posts|بلاغات المحتوى|منشورات')); j.check(tab.count(), 'no content-reports queue'); tab.first.click(); ap.wait_for_timeout(600)
        row = ap.locator('.dx-mod-row', has_text=q).first; j.check(row.count(), 'the reported post is not in the queue')
        decide(j, ap, q, True)
        if j.live:
            j.check(j.wait_db("select count(*) from public.posts where id=%s" % p, 5, want='0') == '0', 'the reported post is still in the database')
            j.check(notif_rows(j, z, extra=" and created_at > now() - interval '10 minutes'") >= 1, 'Z is not told why the post was removed')
            # suspend F through Admin → Users (account_suspensions, 0063), then F cannot post and is told why
            close_dialogs(ap); ap.evaluate("switchAdminTab('users')"); j.settle(ap, 1200)
            ap.locator('#adminContent .adm-q').fill('Fake Profile %s' % t); j.settle(ap, 1500)
            row = ap.locator('#adminContent tr', has_text='Fake Profile %s' % t).first; j.check(row.count(), 'F is not found in Admin → Users')
            row.locator('.adm-sus-btn').click(); ap.wait_for_timeout(500)
            mfill(j, ap, r'Reason|السبب', 'Fake profile — impersonates a QA manager'); mclick(j, ap, r'^\W*(Suspend|إيقاف)\W*$', 'Suspend'); j.settle(ap, 1200)
            j.check(j.wait_db("select reason from public.account_suspensions where user_id='%s'" % f['id'], 6) == 'Fake profile — impersonates a QA manager', 'F is not suspended in the database')
            fp = f['page']; j.reload(fp); fp.wait_for_timeout(1500)
            j.check(re.search(r'suspended|موقوف', mtext(fp)) and 'impersonates' in mtext(fp), 'F is not told why the account is suspended')
            err = fp.evaluate("()=>dxLive.sb.from('posts').insert({user_id:dxLive.uuidOf(ME.id),body:'still posting'})" + _dx.ERR)
            j.check(err and j.sql1("select count(*) from public.posts where user_id='%s' and body='still posting'" % f['id']) == '0', 'the suspended account can still post')
            # merge: one suspension for the whole app — F's open report is closed (M told) and F is out of search
            j.check(j.wait_db("select count(*) from public.member_reports where reported='%s' and status='open'" % f['id'], 6, want='0') == '0', "F's open report stays in Reported members after the suspension")
            found = pg.evaluate("q=>dxLive.sb.rpc('search_all',{p_q:q}).then(r=>r.error?'error':(r.data.people||[]).length)", 'Fake Profile %s' % t)
            j.check(found == 0, 'the suspended F still appears in search (%s)' % found)
            err = fp.evaluate("u=>dxLive.sb.from('messages').insert({sender_id:dxLive.uuidOf(ME.id),receiver_id:u,body:'still messaging'})" + _dx.ERR, m['id'])
            j.check(err and j.sql1("select count(*) from public.messages where sender_id='%s' and body='still messaging'" % f['id']) == '0', 'the suspended account can still message')

@journey('J-COMMUNITY-48')
def decision_notifications(j):
    """Every moderation or community decision reaches the person it affects, and leads them to the thing decided."""
    t = j.tag[:4]
    if j.live:
        u = j.person('Affected User'); pg = u['page']; x = j.person('Xavier Admin')
        gid = seed_group(j, 'Decision Group %s' % t, x['id'], private=True, desc='private')
        j.sql("insert into public.group_join_requests (group_id, user_id, status) values (%d,'%s','pending')" % (gid, u['id']))
        x['page'].evaluate("([g,uu])=>dxLive.sb.rpc('group_decide_request',{p_group:g,p_user:uu,p_approve:true})", [gid, u['id']])
        g2 = seed_group(j, 'Invited Group %s' % t, x['id'])
        x['page'].evaluate("([g,uu])=>dxLive.sb.from('group_invites').insert({group_id:g,user_id:uu,invited_by:dxLive.uuidOf(ME.id)})", [g2, u['id']])
        j.wait_db("select count(*) from public.notifications where user_id='%s'" % u['id'], 6, want='2'); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Open Notifications: each decision is one human sentence (who / what / outcome)'):
        txt = notifs(j, pg)
        if j.live:
            j.check(notif_rows(j, u['id']) == 2, '%d notifications for 2 decisions' % notif_rows(j, u['id']))
            j.check(re.search(r'approved|قبول|وافق', txt) and re.search(r'invited|دعا', txt), 'the decision notifications are not human sentences: %s' % txt[:200])
    with j.step('Click each: it opens the group decided on (not just the notification list)'):
        if j.demo: j.skip('the decisions exist only in live')
        for pat, g in ((r'approved|قبول|وافق', 'Decision Group %s' % t), (r'invited|دعا', 'Invited Group %s' % t)):
            open_notif(j, pg, pat, pat.split('|')[0])
            j.check(gd_open(pg) and gd_title(pg) == g, "the '%s' notification does not open the group (page %s)" % (pat.split('|')[0], pg.evaluate("document.body.getAttribute('data-page')")))
    with j.step('Mark all read; reload: the badge is 0 and stays read'):
        if j.live:   # the approved page offers "Mark all read" while something is unread: one more decision notice arrives first
            j.sql("insert into public.notifications (user_id, type, message) values ('%s', 'account', 'Drugbox verified your profile ✓')" % u['id']); j.reload(pg)
        notifs(j, pg); b = j.find(pg, r'Mark all read|تعليم الكل كمقروء|تحديد الكل كمقروء|قراءة الكل', scope='#content'); j.check(b, 'no Mark all read'); b.click(); j.settle(pg, 900)
        reopen(j, pg); n = pg.evaluate("((document.querySelector('#tnb-notifs [class*=badge], #snl-notifs [class*=badge]')||{}).innerText||'0').trim()")
        j.check(n in ('', '0'), 'after reload the unread badge shows %s' % n)
    with j.step('Arabic: the sentences show in Arabic; another user cannot read them'):
        if j.demo: j.skip('checked in live')
        pg.evaluate("localStorage.setItem('dx_lang','ar')"); j.reload(pg); txt = notifs(j, pg)
        j.check(not re.search(r'approved your request|invited you', txt), 'the notification sentences stay English in Arabic')
        n = x['page'].evaluate("u=>dxLive.sb.from('notifications').select('id').eq('user_id',u).then(r=>(r.data||[]).length)", u['id'])
        j.check(n == 0, "another user reads %s of the user's notifications" % n)

@journey('J-COMMUNITY-49', applies='live')
def decisions_accountable(j):
    """Drugbox decisions are accountable: two moderators never decide the same item twice and decisions can be looked up."""
    t = j.tag[:4]
    o = live_company_person(j, 'Omar Owner', 'Twice Decided %s' % t, status='pending'); name = o['co']['name']
    j.sql("insert into public.verification_requests (company_id, submitted_by, registry, status) values (%s,'%s','99%s','pending')" % (o['co']['id'], o['id'], t))
    a1 = admin_person(j, 'Admin One'); a2 = admin_person(j, 'Admin Two')
    with j.step('A1 and A2 both open Verification requests'):
        t1 = admin_review(j, a1['page'], 'verifications'); t2 = admin_review(j, a2['page'], 'verifications')
        j.check(name in t1 and name in t2, 'the request is not in both queues')
    with j.step("A1 approves; A2 then rejects the same item: A2 is told 'Already decided by A1' and nothing changes"):
        decide(j, a1['page'], name, True); j.check(j.wait_db("select status from public.verification_requests where company_id=%s" % o['co']['id'], 6) == 'approved', 'A1 approval not stored')
        before = toast_set(a2['page']); decide(j, a2['page'], name, False, 'second opinion')
        j.check(j.sql1("select status from public.verification_requests where company_id=%s" % o['co']['id']) == 'approved', "A2's late rejection overwrote A1's approval")
        j.check(re.search(r'Already decided|already|سبق', ' '.join(new_toasts(a2['page'], before)), re.I), "A2 is not told it was already decided")
    with j.step('A Decided filter / history lists decisions with moderator and time'):
        f = j.find(a1['page'], r'Decided|History|السجل|تم البت', scope='#content'); j.check(f, 'not built: no decision history / Decided filter in Admin → Review')
        f.click(); j.settle(a1['page'], 900); txt = j.text(a1['page'])
        j.check(name in txt and 'Admin One' in txt, 'the history does not show the decision with its moderator')

@journey('J-COMMUNITY-50', applies='live')
def admin_is_staff_only(j):
    """Only Drugbox staff can reach Admin and its decisions, so nobody can verify their own company or approve their own payment."""
    t = j.tag[:4]
    o = live_company_person(j, 'Omar Owner', 'Self Verify %s' % t, status='pending'); pg = o['page']; cid = int(o['co']['id'])
    rq = j.sql1("insert into public.verification_requests (company_id, submitted_by, registry, status) values (%d,'%s','98%s','pending') returning id" % (cid, o['id'], t))
    rp = j.sql1("insert into public.company_reports (company_id, reporter, section, issue, status) values (%d,'%s','Sites','x %s','open') returning id" % (cid, o['id'], t))
    po = j.sql1("insert into public.payment_orders (user_id, product_code, company_id, method, amount_cents, status, transfer_ref) values ('%s','vip_month',%d,'instapay',285000,'review','T%s') returning id" % (o['id'], cid, t))
    sm = seed_user(j, 'Someone Employer'); employment(j, sm, o['id']); ref = seed_ref(j, sm, o['id'], 'warn', body=WARN)
    with j.step("No Admin entry in the menus; goto('admin') shows 'not allowed' or goes home"):
        j.check(not pg.locator("#app [onclick=\"goto('admin')\"]:visible").count(), 'a normal member sees an Admin entry')
        pg.evaluate("goto('admin')"); j.settle(pg, 900)
        j.check(pg.evaluate("document.body.getAttribute('data-page')") != 'admin' or re.search(r'not allowed|غير مسموح', j.text(pg)), "goto('admin') opens Admin for a normal member")
    with j.step('Every direct call is refused and nothing changes'):
        calls = [("verification_requests update", "i=>dxLive.sb.from('verification_requests').update({status:'approved'}).eq('id',i).select()", int(rq), "select status from public.verification_requests where id=%s" % rq, 'pending'),
                 ("moderate_reference", "i=>dxLive.sb.rpc('moderate_reference',{ref_id:i,new_status:'rejected'})", int(ref), "select status from public.work_references where id=%s" % ref, 'pending'),
                 ("review_instapay", "i=>dxLive.sb.rpc('review_instapay',{p_id:i,p_ok:true})", int(po), "select status from public.payment_orders where id=%s" % po, 'review'),
                 ("company_reports update", "i=>dxLive.sb.from('company_reports').update({status:'resolved'}).eq('id',i).select()", int(rp), "select status from public.company_reports where id=%s" % rp, 'open'),
                 ("companies set verified", "i=>dxLive.sb.from('companies').update({status:'verified'}).eq('id',i).select()", cid, "select status from public.companies where id=%d" % cid, 'pending')]
        bad = []
        for what, js, arg, q, want in calls:
            pg.evaluate(js, arg); pg.wait_for_timeout(200)
            if j.sql1(q) != want: bad.append(what)
        j.check(not bad, 'a normal member changed: %s' % ', '.join(bad))

if __name__ == '__main__': main(__file__)
