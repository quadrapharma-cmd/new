"""Business journeys — a company's own page: creating it (Basic and VIP), claiming a pre-listed page, joining a company's
team, keeping the page complete, building the team, acting for one of several companies
(J-BUSINESS-12, 13, 14, 15, 16, 17, 25).
Run: python3 tests/journeys/business_company.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

@journey('J-BUSINESS-12')
def create_basic_company(j):
    """A company owner puts his company on Drugbox (free Basic page) so buyers can find it."""
    name = 'Zeta Pharma Labs %s' % j.tag
    if j.live:
        me = j.person('Dr. New Owner'); pg = me['page']
        ex = seed_company(j, None, 'Nile Claimable Pharma %s' % j.tag, status='unclaimed', source='public_list', name_ar='النيل للأدوية %s' % j.tag)
        q_ex, q_ar = 'Nile Claimable', 'النيل للأدوية'
    else:
        pg = j.demo_signin(j.new_page()); q_ex, q_ar = 'Nile', 'وادي النيل'
    with j.step("'Add or claim your company' searches first: existing matches appear as you type (English and Arabic) with 'Claim'"):
        t = add_or_claim(j, pg, q_ex)
        if not (re.search(q_ex, t) and re.search(r'\bClaim\b|طالب', t)) and j.live:
            n = j.sql1("select count(*) from public.companies where status<>'suspended'")
            j.fail("typing an existing company's name does not list it with 'Claim' — 'Add or claim' searches only the companies already loaded in the browser (the first page), not the %s in the database" % n)
        j.check(re.search(q_ex, t) and re.search(r'\bClaim\b|طالب', t), "typing an existing company's name does not list it with 'Claim'")
        pg.fill('#acQ', q_ar); pg.wait_for_timeout(1200); t = dlg_text(pg)
        j.check(re.search(r'Nile|النيل', t) and re.search(r'\bClaim\b|طالب', t), 'the Arabic name does not find the existing company')
        ui_ok(j, pg, 'add or claim')
    with j.step("Not listed → 'My company is not listed — create it' → Basic (Free) → 'Next: company details'"):
        pg.fill('#acQ', name); pg.wait_for_timeout(1000)
        dlg_click(j, pg, r'not listed|create it|غير مدرجة|أنشئ', 'My company is not listed — create it')
        free = pg.locator('.dbk-ov input[name=plPick][value=free]'); j.check(free.count(), 'no Basic (Free) plan'); free.first.check()
        dlg_click(j, pg, L('Next: company details'), 'Next: company details')
    with j.step('Required fields are enforced with clear messages; then the details are filled and the page is created'):
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Next: review|التالي', 'Next: review')
        j.check(pg.locator('.dbk-ov .dbk-err:visible, .dbk-ov [aria-invalid=true]:visible').count() or j.toasts_since(pg, mark), 'empty required fields are not flagged')
        wizard_details(j, pg, name)
        dlg_click(j, pg, r'Next: review|التالي', 'Next: review')
        t = dlg_text(pg); j.check(name in t, 'the review step does not show the company')
        j.check(not re.search(r'no payment is taken|لا يُخصم أي مبلغ', t) or j.demo, '')
        dlg_click(j, pg, r'Create my page|أنشئ صفحتي|أنشئ', 'Create my page'); j.settle(pg, 2000)
        if j.live:
            row = j.wait_db("select status||'|'||plan||'|'||owner_id from public.companies where name=$q$%s$q$" % name, 8)
            j.check(row.startswith(('pending|free|', 'unverified|free|')) and row.endswith(me['id']), 'no company row (free, owned by me): %s' % row)
            j.check(j.sql1("select role from public.company_members m join public.companies c on c.id=m.company_id where c.name=$q$%s$q$ and m.user_id='%s'" % (name, me['id'])) in ('owner', 'admin'), 'I am not the admin member of the new company')
    with j.step("I am its admin: the workspace opens; it is in 'My companies' as 'Acting as'; it is in the directory for another user; reload keeps it"):
        t = j.text(pg)
        if not re.search(r'COMPANY WORKSPACE|مساحة عمل', t[:400]): workspace(j, pg)
        j.check(acting(pg) and pg.evaluate("dxDir.mine().name") == name, "the new company is not the one I act as")
        reopen(j, pg); j.check(pg.evaluate("(dxDir.myCompanies()||[]).some(c=>c.name===%r)" % name), "after reload the company is not in 'My companies'")
        t = my_companies(j, pg); close_dialogs(pg)
        j.check(re.search(re.escape(name) + r'\s*(Acting as|تتصرف باسم|بصفتك)', t), "'My companies' does not show the new company as 'Acting as'")
        if j.live:
            o = j.person('Another Buyer'); directory(j, o['page'])
            j.check(any(name in n for n in search_dir(j, o['page'], name)), 'another user does not find the new company in the directory')
    with j.step('A second company with the same name is refused or redirected to claim it; the page has a unique address'):
        t = add_or_claim(j, pg, name)
        j.check(re.search(r'Ask to join|Claim|already|طالب|انضم|موجود', t), 'creating the same name again is not redirected to the existing page')
        close_dialogs(pg)
        if j.live: j.check(j.sql1("select count(*) from public.companies where name=$q$%s$q$" % name) == '1', 'two pages with the same name exist')
    with j.step("The wizard takes the Arabic name, tagline and logo (with a preview)"):
        create_company(j, pg, 'Logo Check %s' % j.tag)
        ins = dlg_inputs(pg); ids = ' '.join('%s %s %s' % (i['id'], i['label'], i['type']) for i in ins)
        j.check(re.search(r'file', ids), 'not built: the create wizard has no logo upload (fields: %s)' % ', '.join(i['label'] or i['id'] for i in ins))
        j.check(re.search(r'Arabic|عربي', ids), 'not built: the create wizard asks no Arabic company name')

@journey('J-BUSINESS-13')
def create_vip_company(j):
    """A company that wants visibility creates its page directly on the VIP plan and pays for it."""
    name = 'Vipco Pharma %s' % j.tag
    if j.live: me = j.person('Dr. VIP Owner'); pg = me['page']
    else: pg = j.demo_signin(j.new_page())
    with j.step("Create → choose VIP, Monthly → details → the last step shows the server price (EGP 2,500 + 14% VAT) and a real pay button"):
        create_company(j, pg, name, 'vip', 'month'); wizard_details(j, pg, name)
        dlg_click(j, pg, r'Next: review|التالي', 'Next: review')
        t = dlg_text(pg); amounts = money(t)
        j.check(2500 in amounts and 2850 in amounts, 'the VIP price shown is not EGP 2,500 + VAT = 2,850 (%s)' % amounts)
        if j.live: j.check(not re.search(r'no payment is taken|لا يُخصم أي مبلغ|Demo|تجريبية', t), "the live wizard says 'Demo — no payment is taken' — the VIP page is created without paying")
        else: j.check(re.search(r'Demo — no money is charged|نسخة تجريبية', t), "the demo wizard's pay step does not say it is a demo (no money is charged)")
        if j.ar: j.check(not re.search(r'· monthly|monthly', t), "the Arabic wizard says 'VIP · monthly' in English")
    with j.step('Pay by card on the payment page and return; until payment the page is Basic and says payment pending'):
        btn = j.find(pg, r'Pay EGP|ادفع', scope='body'); j.check(btn, 'no pay button')
        if j.live:
            card = pg.locator('.dbk-ov input[value=card]')
            j.check(card.count(), 'not built: the create wizard offers no payment method (card, wallet, Fawry, InstaPay)')
            card.first.check(); btn.click(); j.settle(pg, 3000)
            if dlg_open(pg) and 'unifiedcheckout' not in pg.url: btn = j.find(pg, r'Pay EGP|ادفع', scope='body'); btn and btn.click(); j.settle(pg, 3000)
            j.check(j.sql1("select plan from public.companies where name=$q$%s$q$" % name) == 'free', 'the company became VIP before paying')
            oid = j.wait_db("select o.id from public.payment_orders o join public.companies c on c.id=o.company_id where c.name=$q$%s$q$ and o.product_code='vip_month'" % name, 8)
            j.check(oid, 'no vip_month payment order for the new company')
            s_, r = paymob_callback(j, oid); j.check(s_ == 200, 'the signed Paymob callback was refused: %s %s' % (s_, r[:80]))
            j.open(pg, _dx.APP_URL + '?payment=%s' % oid)
        else:
            btn.click(); j.settle(pg, 1500)
    with j.step("After confirmation: VIP badge, 'Sponsored' top placement in the directory and a renewal date"):
        if j.live:
            j.check(j.sql1("select plan||'|'||(vip_until is not null) from public.companies where name=$q$%s$q$" % name) == 'vip|true', 'the company is not VIP with an end date after payment')
        directory(j, pg)
        sp = pg.evaluate("(()=>{const t=document.querySelector('#dxDir').innerText;const i=t.search(/Sponsored|مموّل|ممول/);return i>=0?t.slice(i,i+800):''})()")
        j.check(name in sp, 'the VIP company is not in the Sponsored row of the directory')
        t = workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة')) + my_companies(j, pg)
        j.check(re.search(r'VIP', t) and re.search(r'renews \d|يتجدد', t), 'neither the Plan tab nor My companies shows the VIP renewal date')

@journey('J-BUSINESS-14')
def claim_company(j):
    """A real company takes control of its pre-listed page instead of creating a duplicate."""
    if j.live:
        me = j.person('Eng. Claimant'); pg = me['page']
        co = seed_company(j, None, 'Unclaimed Sterile %s' % j.tag, status='unclaimed', source='public_list'); name = co['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Nile Valley Pharmaceuticals'
    with j.step("'Add or claim your company' → type the name → 'Claim'"):
        add_or_claim(j, pg, name.split(' %s' % j.tag)[0] if j.demo else name)
        row = j.find(pg, r'^\W*(Claim|طالب بها|طالب)\W*$', scope='body')
        if not row and j.live: j.fail("'Add or claim' does not find the unclaimed page %s — it searches only the companies already loaded in the browser (the first page), not the %s in the database" % (name, j.sql1("select count(*) from public.companies")))
        j.check(row, "no 'Claim' on the unclaimed page")
        row.click(); pg.wait_for_timeout(800)
    with j.step('Provide proof (work email on the company domain and the commercial registry document) and send'):
        fill_by_label(j, pg, r'role|دورك|وظيفتك', 'Business Development Manager')
        fill_by_label(j, pg, r'Mobile|الجوال|الموبايل', '+20 100 777 8899', required=False)
        fill_by_label(j, pg, r'Work email|البريد', 'bd@unclaimedsterile.example')
        j.check(pg.locator('.dbk-ov input[type=file]:visible').count(), 'not built: the claim asks for no commercial registry document — a code to an e-mail address is the only proof')
        pg.locator('.dbk-ov input[type=file]').first.set_input_files(PDF)
        dlg_click(j, pg, r'Send|أرسل', 'Send claim'); j.settle(pg, 1500)
    with j.step("Before approval: 'Claim pending' to the claimant only, and he cannot edit the page"):
        directory(j, pg); open_card(j, pg, name)
        j.check(re.search(r'Claim pending|قيد المراجعة|بانتظار', j.text(pg)), "the page does not show 'Claim pending' to the claimant")
        j.check(not j.find(pg, L('Open company workspace'), scope='#content'), 'the claimant can manage the page before approval')
    with j.step('Drugbox admin approves the claim in Admin → Review'):
        if j.demo: j.skip('Admin → Review decisions on claims are checked in live')
        adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); j.reload(adm['page'])
        t = admin_review(j, adm['page'], 'claims'); admin_decide(j, adm['page'], name, True)
        j.check(j.wait_db("select status from public.companies where id=%s" % co['id'], 6) != 'unclaimed', 'the approved claim did not change the page')
    with j.step('After approval the claimant is the admin and is notified; the Unclaimed badge is gone for everyone'):
        if j.demo: j.skip('checked in live')
        j.reload(pg); workspace(j, pg)
        j.check(j.sql1("select owner_id from public.companies where id=%s" % co['id']) == me['id'], 'the claimant is not the owner')

@journey('J-BUSINESS-15')
def join_company_team(j):
    """An employee joins his company's existing page so he can answer its requests."""
    if j.live:
        adm = live_company_person(j, 'Company Admin', 'Joinable Pharma %s' % j.tag)
        me = j.person('Ahmed Employee'); pg = me['page']; name = adm['co']['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Nile Pharma Packaging'; adm = None
    with j.step("On the company page 'Ask to join the team'; choose role Sales; send"):
        directory(j, pg); open_card(j, pg, name)
        el = j.find(pg, r'Ask to join|اطلب الانضمام|انضم', scope='#content')
        if not el:
            add_or_claim(j, pg, name); el = j.find(pg, r'Ask to join|اطلب الانضمام|انضم', scope='body')
        j.check(el, "no 'Ask to join the team' for the company")
        mark = j.toast_mark(pg); el.click(); pg.wait_for_timeout(900)
        j.check(dlg_open(pg) and re.search(r'Role|الدور', dlg_text(pg)), "not built: 'Ask to join the team' asks no role — %s" % ('it only shows the toast "%s"' % j.toasts_since(pg, mark)[0][:60] if j.toasts_since(pg, mark) else 'nothing happens'))
        fill_by_label(j, pg, r'Role|الدور', r'Sales|مبيعات'); dlg_click(j, pg, r'Send|أرسل', 'Send'); j.settle(pg, 1000)
    with j.step('The company admin is notified and sees the pending request in Team; approves it with the role'):
        if j.demo: j.skip('the company admin exists only in live')
        j.check(j.wait_db("select count(*) from public.company_members where company_id=%s and user_id='%s' and not accepted" % (adm['co']['id'], me['id']), 6) == '1', 'no pending company_members row')
        ap = adm['page']; j.reload(ap); t = workspace(j, ap, 'Team|%s' % ar('Team'))
        j.check('Ahmed Employee' in t, 'the request is not in Team')
        j.click(ap, r'Approve|Accept|اقبل|وافق', scope='#content', what='Approve')
        j.check(j.wait_db("select accepted::text||role from public.company_members where company_id=%s and user_id='%s'" % (adm['co']['id'], me['id']), 6) == 'truesales', 'the member is not active with role sales')
    with j.step("The employee reloads: the company is in 'My companies' and he can act for it"):
        if j.demo: j.skip('checked in live')
        j.reload(pg); j.check(pg.evaluate("(dxDir.myCompanies()||[]).some(c=>c.name===%r)" % name), "the company is not in the employee's companies")

@journey('J-BUSINESS-16')
def keep_page_complete(j):
    """A company keeps its public page complete and current so buyers trust it."""
    if j.live:
        me = live_company_person(j, 'Dr. Page Owner', 'Complete Pharma %s' % j.tag, status='pending'); pg = me['page']; name = me['co']['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Quadra Pharm'
    with j.step("Workspace → Overview: 'Page completeness' and each 'Do it' opens the place that fixes it"):
        t = workspace(j, pg)
        m = re.search(r'(\d+)%', t); j.check(m, "no 'Page completeness' percentage"); j.data['before'] = int(m.group(1))
        dos = pg.locator('#content button:visible', has_text=re.compile(r'^\s*(Do it|نفّذ|افعلها|ابدأ)\s*$'))
        j.check(dos.count(), "no 'Do it' on the open completeness items")
        dos.first.click(); pg.wait_for_timeout(900)
        j.check(dlg_open(pg) or re.search(r'Edit|Sites|Team|عدّل', j.text(pg)[:600]), "'Do it' opens nothing")
        close_dialogs(pg)
    with j.step("Page → 'Edit page': new tagline and about, logo, cover, colour, a product with photo → 'Save and publish'"):
        workspace(j, pg, 'Page|%s' % (ar('Page') or 'الصفحة'))
        j.click(pg, L('Edit page'), scope='#content', what='Edit page'); pg.wait_for_timeout(800)
        fill_by_label(j, pg, r'edTag|Tagline|الشعار', 'Sterile injectables %s' % j.tag)
        fill_by_label(j, pg, r'edAbout|About|عن الشركة', 'We make sterile products in Giza. %s' % j.tag)
        for sel in ('#edLogo', '#edCover'):
            j.check(pg.locator(sel).count(), 'not built: the editor has no %s upload' % sel[3:].lower()); pg.set_input_files(sel, PNG); pg.wait_for_timeout(500)
        editor_add_product(j, pg, 'Ceftriaxone 1 g vial %s' % j.tag)
        mark = j.toast_mark(pg); j.click(pg, r'Save and publish|احفظ وانشر', scope='body', what='Save and publish'); j.settle(pg, 2000)
        bad = [t for t in j.toasts_since(pg, mark) if re.search(r'not saved|next update|Could not save|storage is full|لم يُحفظ', t, re.I)]
        j.check(not bad, 'the edit is not saved online: "%s"' % (bad[0][:90] if bad else ''))
        if j.live:
            j.check(j.wait_db("select tagline from public.companies where id=%s" % me['co']['id'], 6) == 'Sterile injectables %s' % j.tag, 'the tagline is not saved in the database')
            j.check(j.sql1("select count(*) from public.company_products where company_id=%s and name like '%%%s%%'" % (me['co']['id'], j.tag)) == '1', 'the product is not saved in the database')
            j.check(j.sql1("select (logo_url is not null)::text||(cover_url is not null)::text from public.companies where id=%s" % me['co']['id']) == 'truetrue', 'the logo and cover are not saved')
    with j.step("Set the Arabic company name and Save; 'Add membership'"):
        workspace(j, pg, 'Page|%s' % (ar('Page') or 'الصفحة'))
        pg.fill('#wAr', 'فارما كاملة %s' % j.tag); j.click(pg, L('Save'), scope='#content', what='Save'); j.settle(pg, 1000)
        j.click(pg, L('Add membership'), scope='#content', what='Add membership')
        j.check(dlg_open(pg), "'Add membership' opens no window")
        fill_by_label(j, pg, r'Organisation|Organization|الجهة|المنظمة', r'Export Council|المجلس التصديري')
        fill_by_label(j, pg, r'Membership number|رقم العضوية', 'EC-%s' % j.tag[:6])
        dlg_click(j, pg, r'Send for confirmation|أرسل للتأكيد|إرسال للتأكيد', 'Send for confirmation'); j.settle(pg, 1200)
        t = workspace(j, pg, 'Page|%s' % (ar('Page') or 'الصفحة'))
        j.check(re.search(r'Export Council[^\n]*(being checked|قيد المراجعة)|المجلس التصديري[^\n]*قيد المراجعة', t), 'the new membership is not shown as being checked by Drugbox')
        if j.live:
            j.check(j.wait_db("select name_ar from public.companies where id=%s" % me['co']['id'], 5) == 'فارما كاملة %s' % j.tag, 'the Arabic name is not saved')
            j.check(j.wait_db("select status||'|'||number from public.company_documents where company_id=%s and type='Membership'" % me['co']['id'], 6) == 'review|EC-%s' % j.tag[:6], 'the membership is not a company_documents row waiting for Drugbox')
            adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); ap = adm['page']; j.reload(ap)
            t = admin_review(j, ap, 'documents'); j.check(name in t and 'Export Council' in t, 'the membership is not in Admin → Review → Compliance documents')
            admin_decide(j, ap, name, True)
            j.check(j.wait_db("select status from public.company_documents where company_id=%s and type='Membership'" % me['co']['id'], 6) == 'verified', 'the membership is not confirmed after Drugbox approves')
    with j.step("'Still correct' on an outdated section clears the flag ('Thanks — marked as up to date')"):
        if j.live: j.sql("set session_replication_role = replica; update public.companies set updated_at=now()-interval '200 days' where id=%s" % me['co']['id']); reopen(j, pg)   # the write trigger stamps now(): aged like a page untouched for 200 days
        directory(j, pg); open_card(j, pg, name)
        el = j.find(pg, r'Still correct|ما زالت صحيحة|لا تزال صحيحة', scope='#content')
        if j.demo and not el and not re.search(r'May be outdated|قد تكون قديمة', j.text(pg)): j.skip('the demo company has no section older than 180 days (its dates cannot be aged)')
        j.check(el, "no 'Still correct' on a section older than 180 days")
        mark = j.toast_mark(pg); el.click(); j.settle(pg, 900)
        j.check(any(re.search(r'up to date|محدّث|محدث', t) for t in j.toasts_since(pg, mark)), "no 'Thanks — marked as up to date'")
    with j.step('After reload a visitor in another browser sees every edit; the Activity tab logs who changed what'):
        reopen(j, pg)
        if j.live: v = j.person('Visitor Buyer')['page']
        else: v = pg
        directory(j, v); open_card(j, v, name); t = j.text(v)
        j.check(('Sterile injectables %s' % j.tag) in t, 'the new tagline is not on the public page after reload')
        t = company_tab(j, v, 'Products|%s' % ar('Products'), 'Products'); j.check(('Ceftriaxone 1 g vial %s' % j.tag) in t, 'the new product is not on the public page')
        t = workspace(j, pg, 'Activity|%s' % (ar('Activity') or 'النشاط'))
        j.check(re.search(r'tagline|page|edited|عدّل|الصفحة', t, re.I) and re.search(r'Page Owner|Haytham|You|أنت', t), 'the Activity tab does not log the edit with who made it')

@journey('J-BUSINESS-17')
def build_team(j):
    """An owner builds his team on Drugbox — invites colleagues with roles and decides who receives which requests."""
    if j.live:
        me = live_company_person(j, 'Dr. Team Owner', 'Team Pharma %s' % j.tag); pg = me['page']
        col = j.person('Mona Colleague'); mail1 = col['email']
    else:
        pg = j.demo_signin(j.new_page()); mail1 = 'mona.%s@quadrapharm.example' % j.tag; col = None
    with j.step("Team → 'Invite a colleague' (Sales) and a second one (Quality); until accepted Team shows 'Invited'"):
        workspace(j, pg, 'Team|%s' % ar('Team'))
        for nm, mail, role in (('Mona Colleague', mail1, 'Sales'), ('Omar Quality', 'omar.%s@teampharma.example' % j.tag, 'Quality')):
            j.click(pg, L('Invite a colleague'), scope='#content', what='Invite a colleague')
            fill_by_label(j, pg, r'^Name|الاسم', nm); fill_by_label(j, pg, r'email|البريد', mail); fill_by_label(j, pg, r'Role|الدور', role)
            dlg_click(j, pg, r'Send invitation|أرسل الدعوة', 'Send invitation'); j.settle(pg, 1000)
        t = j.text(pg); j.check('Mona Colleague' in t and re.search(r'Invited|Waiting for their agreement|مدعو|بانتظار', t), "the Team does not list the invitation as 'Invited'")
        if j.live: j.check(j.wait_db("select count(*) from public.company_members where company_id=%s and user_id='%s'" % (me['co']['id'], col['id']), 6) == '1', 'no company_members row for the invited colleague')
    with j.step('Colleague 1 opens the invitation (notification) and accepts'):
        if j.demo: j.skip('the demo has one account: the invited colleague exists only in live (notification → Accept is checked there)')
        cp = col['page']; j.reload(cp)
        n = j.sql1("select count(*) from public.notifications where user_id='%s' and created_at > now()-interval '10 minutes'" % col['id'])
        j.check(n not in ('', '0'), 'not built: the invited colleague gets no notification of the invitation')
        j.nav(cp, 'notifs'); j.settle(cp, 900)                     # the invitation is in Notifications
        j.click(cp, r'^\W*(Accept|اقبل|قبول)\W*$', scope='#content', what='Accept invitation')
        j.check(j.wait_db("select accepted::text||role from public.company_members where company_id=%s and user_id='%s'" % (me['co']['id'], col['id']), 6) == 'truesales', 'the colleague is not an active sales member after accepting')
    with j.step("Owner changes a role, sets 'Who receives what', 'Hide me' for one member, removes a member — all survive reload"):
        workspace(j, pg, 'Team|%s' % ar('Team'))
        j.check(re.search(r'Who receives what|من يستلم', j.text(pg), re.I), "no 'Who receives what' routing in Team")
        row = lambda nm: pg.locator('#content .hb-tm', has_text=nm).first
        j.check(row('Mona Colleague').count(), 'Mona is not in Team')
        row('Mona Colleague').locator('select').select_option(label=ar('Quality') if j.ar else 'Quality'); j.settle(pg, 1200)
        rm = row('Omar Quality').locator('.hb-x'); j.check(rm.count(), 'no way to remove the second invitation'); rm.click(); j.settle(pg, 1200)
        if j.live:
            j.check(j.wait_db("select role from public.company_members where company_id=%s and user_id='%s'" % (me['co']['id'], col['id']), 6) == 'quality', 'the new role is not saved')
            j.check(j.wait_db("select count(*) from public.company_invites where company_id=%s" % me['co']['id'], 6, want='0') == '0', 'the removed invitation is still stored')
            j.check(j.wait_db("select user_id from public.company_routing where company_id=%s and request_type='questionnaire'" % me['co']['id'], 6) == col['id'], "questionnaires do not go to the new quality member ('Who receives what' does not follow the role)")
        reopen(j, pg); t = workspace(j, pg, 'Team|%s' % ar('Team'))
        j.check('Omar Quality' not in t, 'the removed invitation is back after reload')
        j.check(pg.locator('#content .hb-tm', has_text='Mona Colleague').locator('select').evaluate("s=>s.options[s.selectedIndex].text") in ('Quality', ar('Quality')), "Mona's new role did not survive the reload")
        if j.live:
            j.check('Mona Colleague' in re.split(r'Who receives what|من يستلم', t, flags=re.I)[-1], "'Who receives what' does not name the quality member")

@journey('J-BUSINESS-25')
def act_as_company(j):
    """A person who belongs to more than one company chooses which company he is acting for."""
    if j.live:
        me = live_company_person(j, 'Dr. Two Hats', 'First Hat Pharma %s' % j.tag); pg = me['page']
        second = seed_company(j, me['id'], 'Second Hat Trading %s' % j.tag, sectors=('Distribution',)); j.reload(pg)
        sup = live_company_person(j, 'Supplier Sales', 'Hat Supplier %s' % j.tag, sectors=('API & excipients',)); seed_route(j, sup['co']['id'], 'quote', sup['id'])
        j.reload(pg); co2, supn = second['name'], sup['co']['name']
    else:
        pg = j.demo_signin(j.new_page()); supn = 'Medsinia Industries'
        co2 = 'Second Hat Trading %s' % j.tag
        create_company(j, pg, co2); wizard_details(j, pg, co2, sector=r'Distribution|توزيع')
        dlg_click(j, pg, r'Next: review|التالي', 'Next: review'); dlg_click(j, pg, r'Create my page|أنشئ', 'Create my page'); j.settle(pg, 1200)
    with j.step("Top-bar company switcher → 'Act as' the second company"):
        close_dialogs(pg); directory(j, pg)
        sw = pg.locator('#dxCoSwitch:visible'); j.check(sw.count(), 'no company switcher in the top bar at %dpx' % j.width)
        sw.click(); pg.wait_for_timeout(400)
        it = pg.locator('#dxCoMenu [data-cs]', has_text=co2); j.check(it.count(), "the switcher does not list %s" % co2)
        it.first.click(); j.settle(pg, 900)
        j.check(pg.evaluate("dxDir.mine().name") == co2, 'Act as did not switch to the second company')
    with j.step("Request a quote: the form says 'Requesting as <second company>'; the supplier sees it from that company"):
        directory(j, pg); open_card(j, pg, supn); j.click(pg, L('Request a quote'), scope='#content', what='Request a quote')
        t = dlg_text(pg); j.check(re.search(r'(Requesting as|تطلب باسم)\s*\n?\s*' + re.escape(co2), t), "the quote form does not say 'Requesting as %s'" % co2)
        fill_by_label(j, pg, r'Quantity|الكمية', '10'); fill_by_label(j, pg, r'Message|الرسالة', 'From the trading arm')
        dlg_click(j, pg, L('Send request'), 'Send request'); j.settle(pg, 1200)
        if j.live:
            j.check(j.wait_db("select c.name from public.deals d join public.companies c on c.id=d.from_company_id where d.to_company_id=%s order by d.id desc limit 1" % sup['co']['id'], 6) == co2, 'the deal is not from the acting company')
        else:
            j.check(pg.evaluate("(dxDeals.all().filter(d=>d.to&&d.to.slug==='medsinia-industries').pop()||{from:{}}).from.name") == co2, 'the request is not sent as the acting company')
    with j.step('Switching back changes the workspace shown; each company keeps its own inbox'):
        sw = pg.locator('#dxCoSwitch:visible'); sw.click(); pg.wait_for_timeout(300)
        other = pg.locator('#dxCoMenu [data-cs]').filter(has_not_text=co2); j.check(other.count(), 'the switcher lists only one company')
        other.first.click(); j.settle(pg, 800)
        t = workspace(j, pg); m = re.search(r'(COMPANY WORKSPACE|مساحة عمل الشركة)\s*\n\s*([^\n]+)', t)
        j.check(m and m.group(2).strip() != co2, 'the workspace still shows the second company after switching back')
    with j.step("The page I just made is current and names me as its owner: no 'updated more than 6 months ago' notice; Contact says quote requests go to me (Owner)"):
        close_dialogs(pg); directory(j, pg)
        if j.live:      # a page with no site in the database says so — never an invented "<city> site · Factory"
            sites_db = int(j.sql1("select count(*) from public.company_sites s join public.companies c on c.id=s.company_id where c.name=$q$%s$q$" % co2) or 0)
            card = pg.evaluate("n=>{const c=[...document.querySelectorAll('#content .dr-card,#content .hb-card')].find(e=>e.innerText.indexOf(n)>=0);return c?c.innerText:''}", co2)
            m = re.search(r'(\d+)\s*(sites?|مواقع|موقع)', card)
            j.check(not m or int(m.group(1)) == sites_db, 'the directory card of a page with %d sites in the database says "%s"' % (sites_db, m.group(0) if m else card[:80]))
        open_card(j, pg, co2); t = j.text(pg)
        j.check(not re.search(r'more than 6 months|older than 6 months|May be outdated|أكثر من 6 أشهر|أقدم من 6 أشهر|قد تكون قديمة', t), 'a page made minutes ago says its information is more than 6 months old')
        who = pg.evaluate('ME.name'); ppl = pg.evaluate("[...document.querySelectorAll('#content .hb-person')].map(e=>e.innerText.replace(/\\s+/g,' '))")
        mine_row = [x for x in ppl if who in x]
        j.check(not mine_row or re.search(r'Owner|المالك', mine_row[0]), "the Overview's People box calls the page's owner \"%s\"" % (mine_row[0] if mine_row else ''))
        if j.live:
            has_tab = pg.locator('#content [role=tab], #content .cp-tab').filter(has_text=re.compile(r'^\W*(Sites|%s)\W*(\(\d+\))?$' % (ar('Sites') or 'المواقع'))).count()
            t2 = company_tab(j, pg, 'Sites|%s' % (ar('Sites') or 'المواقع'), 'Sites') if has_tab else ''
            if sites_db == 0: j.check(not re.search(r'(?i)\b\w+ site\b.*(Factory|Warehouse|Office|Laboratory)|موقع .*(مصنع|مستودع|مكتب)', t2.split('Add a site')[0][:600]), 'the Sites tab shows a site the company never added: %s' % t2[:160].replace('\n', ' | '))
            directory(j, pg); open_card(j, pg, co2)
        t = company_tab(j, pg, 'Contact|%s' % ar('Contact'), 'Contact'); who = pg.evaluate('ME.name')
        j.check(re.search(re.escape(who) + r'\s*\((Owner|المالك)\)', t), "Contact does not name the page's owner (%s) as Owner: %s" % (who, (re.search(r'(Quote requests go to|طلبات عروض الأسعار تذهب إلى)[^\n]{0,80}', t) or [''])[0]))
        if j.lang == 'ar': j.check(not re.search(r'Quote requests go to|\((Admin|Owner)\)|Some information on this page', t), 'the Contact tab shows English interface text in Arabic')
    with j.step('Live: acting as a company I am not a member of is refused by the database'):
        if j.demo: j.skip('database checks are live only')
        r = pg.evaluate("s=>dxLive.sb.rpc('deal_create',{p_type:'quote',p_to_slug:s,p_from_slug:%r,p_title:'forged'})%s" % (sup['co']['slug'], _dx.ERR), sup['co']['slug'])
        j.check(r, 'deal_create as a company I am not a member of was accepted')

if __name__ == '__main__': main(__file__)
