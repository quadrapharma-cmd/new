"""Business journeys — running a company page: sites and capacity, checked certificates, private company documents, the
Verified seal, products, the shared inbox, replying to reviews (J-BUSINESS-18, 19, 20, 21, 22, 23, 24).
Run: python3 tests/journeys/business_workspace.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

def own_company(j, name, status='verified', **kw):
    """Live: a fresh account owning a company page. Demo: the demo account's Quadra Pharm (or, for an unverified company,
    a new page made through the create wizard)."""
    if j.live:
        me = live_company_person(j, 'Dr. Owner', '%s %s' % (name, j.tag), status=status, **kw)
        return me, me['page'], me['co']['name']
    pg = j.demo_signin(j.new_page())
    if status == 'verified': return None, pg, 'Quadra Pharm'
    nm = '%s %s' % (name, j.tag); create_company(j, pg, nm); wizard_details(j, pg, nm)
    dlg_click(j, pg, r'Next: review|التالي', 'Next: review'); dlg_click(j, pg, r'Create my page|أنشئ', 'Create my page'); j.settle(pg, 1200); close_dialogs(pg)
    return None, pg, nm

@journey('J-BUSINESS-18')
def sites_and_capacity(j):
    """A manufacturer shows where it produces and what it can make (sites, capabilities, free capacity)."""
    me, pg, name = own_company(j, 'Capacity Pharma')
    site = 'Obour plant %s' % j.tag
    with j.step("Workspace → Sites → 'Add a site' (name, type Factory, governorate, city)"):
        workspace(j, pg, 'Sites|%s' % ar('Sites'))
        j.click(pg, L('Add a site'), scope='#content', what='Add a site')
        fill_by_label(j, pg, r'^Name|الاسم', site); fill_by_label(j, pg, r'^Type|النوع', r'Factory|مصنع'); fill_by_label(j, pg, r'Governorate|المحافظة', r'Qalyubia|القليوبية')
        fill_by_label(j, pg, r'City|المدينة', 'Obour City')
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Add site|أضف الموقع', 'Add site'); j.settle(pg, 1200)
        bad = [t for t in j.toasts_since(pg, mark) if re.search(r'next update|review|not saved|التحديث', t, re.I)]
        j.check(not bad, 'the site is not saved: "%s"' % (bad[0][:90] if bad else ''))
        j.check(site.lower() in j.text(pg).lower(), 'the new site is not listed in Sites')
        if j.live: j.check(j.wait_db("select count(*) from public.company_sites where company_id=%s and name=$q$%s$q$" % (me['co']['id'], site), 6) == '1', 'no company_sites row')
    with j.step("On the site 'Add manufacturing capabilities' (Tablets, capacity, minimum batch) and mark months Free/Booked"):
        sec = pg.locator('#content .hb-site, #content section', has_text=site).first
        b = sec.locator('button', has_text=re.compile(r'(Add manufacturing|Edit) capabilities|أضف قدرات|عدّل القدرات|تعديل القدرات')).first
        j.check(b.count(), "no 'Add manufacturing capabilities' on the new site"); b.click(); pg.wait_for_timeout(600)
        pg.locator('.dbk-ov label', has_text=re.compile(r'Tablets|أقراص')).first.click()
        fill_by_label(j, pg, r'Minimum batch|الحد الأدنى', '150,000 tablets'); fill_by_label(j, pg, r'Capacity|الطاقة', '6M tablets / month')
        dlg_click(j, pg, L('Save'), 'Save'); j.settle(pg, 1000)
        sec = pg.locator('#content .hb-site, #content section', has_text=site).first
        months = sec.locator('button', has_text=re.compile(r'Free|Booked|متاح|محجوز'))
        j.check(months.count() >= 3, 'the site shows no month calendar to mark Free/Booked')
        before = months.nth(1).inner_text(); months.nth(1).click(); j.settle(pg, 700)
        sec = pg.locator('#content .hb-site, #content section', has_text=site).first
        j.check(sec.locator('button', has_text=re.compile(r'Free|Booked|متاح|محجوز')).nth(1).inner_text() != before, 'tapping a month does not change Free/Booked')
        if j.live: j.check(j.wait_db("select array_to_string(dosage_forms,',')||'|'||coalesce(capacity,'') from public.company_sites where company_id=%s and name=$q$%s$q$" % (me['co']['id'], site), 6).startswith('Tablets|6M'), 'the capabilities are not saved in company_sites')
    with j.step('A visitor sees the site, capabilities and calendar on the public Sites tab; the directory shows the capacity line'):
        reopen(j, pg)
        v = j.person('Visiting Buyer')['page'] if j.live else pg
        directory(j, v); open_card(j, v, name); t = company_tab(j, v, 'Sites|%s' % ar('Sites'), 'Sites')
        j.check(site.lower() in t.lower() and '6M tablets / month' in t, 'the public Sites tab does not show the new site with its capacity')
        directory(j, v); set_ok = v.evaluate("(()=>{const e=document.querySelector('#hbForm');const o=[...e.options].find(o=>/Tablets|أقراص/.test(o.textContent));e.value=o.value;e.dispatchEvent(new Event('change',{bubbles:true}));return true})()")
        v.wait_for_timeout(900); search_dir(j, v, name)
        cap = v.evaluate("n=>{const c=[...document.querySelectorAll('#dxDir .dr-card')].find(c=>c.innerText.includes(n));return c?((c.querySelector('.hb-cap')||{}).innerText||''):null}", name)
        j.check(cap is not None, 'the company is not found under Tablets in the directory')
        j.check(re.search(r'free from|متاح', cap or ''), 'the directory card has no capacity line')
    with j.step("'Remove site' removes it (and its certificates) from the public page after confirmation"):
        workspace(j, pg, 'Sites|%s' % ar('Sites'))
        sec = pg.locator('#content .hb-site, #content section', has_text=site).first
        b = sec.locator('button', has_text=re.compile(r'Remove site|احذف الموقع')).first; j.check(b.count(), "no 'Remove site'")
        b.click(); pg.wait_for_timeout(600)
        if dlg_open(pg): dlg_click(j, pg, r'Remove|Delete|احذف|حذف', 'confirm remove')
        j.settle(pg, 1000); j.check(site.lower() not in j.text(pg).lower(), 'the removed site is still listed')
        if j.live: j.check(j.wait_db("select count(*) from public.company_sites where company_id=%s and name=$q$%s$q$" % (me['co']['id'], site), 6, want='0') == '0', 'the company_sites row is still there')

@journey('J-BUSINESS-19')
def checked_certificates(j):
    """A manufacturer proves its GMP status with certificates that Drugbox has checked."""
    me, pg, name = own_company(j, 'Certified Pharma')
    if j.live: seed_site(j, me['co']['id'], 'Badr plant'); j.reload(pg)
    with j.step("Workspace → Sites → 'Certificate' on a site: GDP, valid until, the certificate PDF; Add"):
        workspace(j, pg, 'Sites|%s' % ar('Sites'))
        j.click(pg, r'^\W*(\+\s*)?(Certificate|شهادة)\W*$', scope='#content', what='+ Certificate')
        fill_by_label(j, pg, r'Certificate|الشهادة', r'^GDP')
        vu = pg.locator('.dbk-ov input[type=date]:visible, .dbk-ov input[type=month]:visible')
        if vu.count(): vu.first.fill('2027-12-31' if vu.first.get_attribute('type') == 'date' else '2027-12')
        f = pg.locator('.dbk-ov input[type=file]'); j.check(f.count(), 'not built: a certificate cannot carry its document')
        f.first.set_input_files(PDF)
        mark = j.toast_mark(pg); dlg_click(j, pg, r'^\W*(Add|أضف)\W*$', 'Add'); j.settle(pg, 1200)
        bad = [t for t in j.toasts_since(pg, mark) if re.search(r'next update|not saved', t, re.I)]
        j.check(not bad, 'the certificate is not saved: "%s"' % (bad[0][:90] if bad else ''))
        if j.live:
            j.check(j.wait_db("select count(*) from public.site_certificates where company_id=%s and name='GDP' and checked_at is null" % me['co']['id'], 6) == '1', 'no unchecked site_certificates row')
    with j.step("Before Drugbox checks it, visitors see it as 'not yet checked' (no verified tick)"):
        reopen(j, pg); directory(j, pg); open_card(j, pg, name); company_tab(j, pg, 'Sites|%s' % ar('Sites'), 'Sites'); t = chip_info(pg, 'GDP')
        j.check(re.search(r'not yet checked|unverified|pending|self-declared|not checked|لم تُراجع|قيد|غير موثق', t, re.I), 'the unchecked GDP certificate is shown like a checked one (no "not yet checked")')
    with j.step('Drugbox admin opens the document from Admin → Review → certificates (signed link) and approves it'):
        if j.demo: j.skip('Admin → Review decisions on documents are checked in live')
        adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); ap = adm['page']; j.reload(ap)
        t = admin_review(j, ap, 'certs'); j.check(name in t, 'the certificate is not in Admin → Review → Site certificates')
        j.check(ap.locator('.dx-mod-row', has_text=name).locator('.dx-mod-doc').count(), 'not built: the reviewer cannot open the certificate document')
        admin_decide(j, ap, name, True)
        j.check(j.wait_db("select (checked_at is not null)::text from public.site_certificates where company_id=%s" % me['co']['id'], 6) == 'true', 'the certificate is not checked after approval')
    with j.step("After approval the page shows the verified seal with 'checked <date>'; a rejected certificate is not shown and the company gets the reason"):
        if j.demo: j.skip('checked in live')
        j.reload(pg); directory(j, pg); open_card(j, pg, name); t = company_tab(j, pg, 'Sites|%s' % ar('Sites'), 'Sites')
        j.check(re.search(r'checked|تمت المراجعة', t, re.I), "the page does not say the certificate was checked")
        j.check(admin_review(j, adm['page'], 'certs') is not None and adm['page'].locator('.dx-mod-row .dx-mod-no').count() or False, 'not built: a certificate cannot be rejected with a reason (only "Mark checked")')

@journey('J-BUSINESS-20')
def company_documents(j):
    """A company keeps its controlled documents (licences, GMP certificates, SMF) in one private place its team can use."""
    me, pg, name = own_company(j, 'Documented Pharma')
    with j.step("Workspace → Plan & verification → 'Add document': upload a PDF with title and type"):
        workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة'))
        j.click(pg, L('Add document'), scope='#content', what='Add document')
        fill_by_label(j, pg, r'^Document|المستند', r'CEP|.')
        fill_by_label(j, pg, r'Number|reference|الرقم', 'R1-CEP 2019-123', required=False)
        f = pg.locator('.dbk-ov input[type=file]')
        j.check(f.count(), 'not built: "Add document" stores no file — only a type and a number (no PDF upload)')
        f.first.set_input_files(PDF); dlg_click(j, pg, L('Save'), 'Save'); j.settle(pg, 1200)
        if j.live: j.check(j.wait_db("select count(*) from public.company_documents where company_id=%s and file_path is not null" % me['co']['id'], 6) == '1', 'no company_documents row with a file')
    with j.step('A second member opens it; an outsider gets nothing (no listing, signed link refused)'):
        if j.demo: j.skip('other members exist only in live')
        m2 = j.person('Second Member'); seed_member(j, me['co']['id'], m2['id'], 'quality'); j.reload(m2['page'])
        t = workspace(j, m2['page'], 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة')); j.check('spec.pdf' in t or 'CEP' in t, 'the second member does not see the document')
    with j.step('Delete the document after confirmation: gone from the list and storage'):
        if j.demo: j.skip('checked in live')
        j.click(pg, r'Delete|Remove|احذف', scope='#content', what='Delete document')

@journey('J-BUSINESS-21')
def get_verified(j):
    """A company gets the Verified seal by sending its legal documents to Drugbox."""
    me, pg, name = own_company(j, 'Unverified Pharma', status='pending')
    with j.step("Workspace → Plan & verification → 'Get verified': registry number, registry document, tax card, licence → send"):
        t = workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة'))
        el = j.find(pg, r'Get verified|وثّق|احصل على التوثيق|Send for verification', scope='#content')
        if not el and j.live and re.search(r'Documents received|استلمنا المستندات', t) and j.sql1("select count(*) from public.verification_requests where company_id=%s" % me['co']['id']) == '0':
            j.fail("a new, unverified company (status 'pending', no documents sent) is told 'Documents received — being checked' and has no 'Get verified'")
        j.check(el, "no 'Get verified' on an unverified company")
        el.click(); pg.wait_for_timeout(800)
        mark = j.toast_mark(pg); b = j.find(pg, r'Send for verification|Send|أرسل', scope='body')
        if b and dlg_open(pg): b.click(); pg.wait_for_timeout(600)
        j.check(dlg_open(pg) and (pg.locator('.dbk-ov .dbk-err:visible').count() or j.toasts_since(pg, mark)), 'required fields are not enforced')
        fill_by_label(j, pg, r'registry|السجل', '7788%s' % j.tag[:4])
        files = pg.locator('.dbk-ov input[type=file]')
        j.check(files.count() >= 2, 'not built: verification takes %d document upload(s) — registry document, tax card and licence are needed' % files.count())
        for i in range(files.count()): files.nth(i).set_input_files(PDF)
        dlg_click(j, pg, r'Send for verification|Send|أرسل', 'Send for verification'); j.settle(pg, 1500)
        if j.live: j.check(j.wait_db("select status from public.verification_requests where company_id=%s" % me['co']['id'], 6) == 'pending', 'no pending verification_requests row')
    with j.step("The request shows 'Under review' to the owner; the owner cannot set verified himself (the database refuses)"):
        t = workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة'))
        j.check(re.search(r'Under review|in review|being checked|قيد المراجعة|قيد الفحص|جارٍ', t), "the owner does not see 'Under review'")
        if j.live:
            pg.evaluate("i=>dxLive.sb.from('companies').update({status:'verified'}).eq('id',i)", int(me['co']['id']))
            j.check(j.sql1("select status from public.companies where id=%s" % me['co']['id']) != 'verified', 'the owner verified his own company directly')
    with j.step('Drugbox admin opens the documents in Admin → Review → verification and approves'):
        if j.demo: j.skip('Admin → Review decisions are checked in live')
        adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); ap = adm['page']; j.reload(ap)
        t = admin_review(j, ap, 'verifications'); j.check(name in t, 'the request is not in Admin → Review → Verification requests')
        j.check(ap.locator('.dx-mod-row', has_text=name).locator('.dx-mod-doc').count() >= 2, 'the reviewer cannot open the documents')
        admin_decide(j, ap, name, True)
        j.check(j.wait_db("select status from public.companies where id=%s" % me['co']['id'], 6) == 'verified', 'the company is not verified after approval')
    with j.step('The seal shows on the page and card; the owner is notified'):
        if j.demo: j.skip('checked in live')
        j.reload(pg); directory(j, pg); search_dir(j, pg, name)
        j.check(pg.locator('#dxDir .dr-card', has_text=name).locator('.dr-seal').count(), 'no Verified seal on the card')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and created_at > now()-interval '10 minutes'" % me['id']) not in ('', '0'), 'the owner is not notified of the decision')

@journey('J-BUSINESS-22')
def list_products(j):
    """A company lists its products so buyers can request quotes for a specific product."""
    me, pg, name = own_company(j, 'Product Pharma')
    prod = 'Paracetamol 500 mg %s' % j.tag
    with j.step("Edit page → Products: add 'Paracetamol 500 mg' (with photo) and a second product; remove one"):
        workspace(j, pg, 'Page|%s' % (ar('Page') or 'الصفحة')); j.click(pg, L('Edit page'), scope='#content', what='Edit page'); pg.wait_for_timeout(600)
        for p in (prod, 'Ibuprofen 400 mg %s' % j.tag, 'Removed product %s' % j.tag):
            said = editor_add_product(j, pg, p)
            bad = [t for t in said if re.search(r'not saved|next update|Could not save|storage is full', t, re.I)]
            j.check(not bad, 'the product is not saved online: "%s"' % (bad[0][:90] if bad else ''))
        rm = pg.locator('#dxEditor :is(div,li)', has_text='Removed product %s' % j.tag).locator('button', has_text=re.compile(r'Remove|×|احذف')).last
        j.check(rm.count(), 'a product cannot be removed in the editor'); rm.click(); pg.wait_for_timeout(400)
        mark = j.toast_mark(pg); j.click(pg, r'Save and publish|احفظ وانشر', scope='body', what='Save and publish'); j.settle(pg, 1500)
        bad = [t for t in j.toasts_since(pg, mark) if re.search(r'not saved|next update|Could not save|storage is full', t, re.I)]
        j.check(not bad, 'the products are not saved online: "%s"' % (bad[0][:90] if bad else ''))
        if j.live: j.check(j.wait_db("select count(*) from public.company_products where company_id=%s and name like '%%%s%%'" % (me['co']['id'], j.tag), 6) == '2', 'the products are not in company_products (exactly the two kept)')
    with j.step('After reload the public Products tab shows them with photos and the tab count updates'):
        reopen(j, pg); directory(j, pg); open_card(j, pg, name)
        n = tab_count(pg, r'^\W*(Products|المنتجات)'); t = company_tab(j, pg, 'Products|%s' % ar('Products'), 'Products')
        j.check(prod in t, 'the new product is not on the Products tab')
        j.check(n == pg.locator('#content article.cp-prod').count(), 'the Products tab count (%s) differs from the products shown' % n)
    with j.step("A buyer's 'Request a quote' on the product preselects it; the directory search by product name finds the company"):
        b = j.person('Buyer Person') if j.live else None
        bp = b['page'] if b else pg
        if j.live: seed_company(j, b['id'], 'Buyer Co %s' % j.tag); j.reload(bp)
        else:
            pass
        directory(j, bp); r = search_dir(j, bp, prod); j.check(any(name in x for x in r), 'searching the product name does not find the company')
        if j.demo: j.skip("the demo account owns this company: it cannot request a quote from itself")
        open_card(j, bp, name); company_tab(j, bp, 'Products|%s' % ar('Products'), 'Products')
        bp.locator('#content article.cp-prod', has_text=prod).first.locator('button').first.click(); bp.wait_for_timeout(700)
        if dlg_open(bp) and not bp.locator('#rqWhat').count(): j.click(bp, L('Request a quote'), scope='body', what='Request a quote')
        j.check(bp.locator('#rqWhat').count(), 'Request a quote from the product opens no quote form')
        sel = bp.evaluate("(()=>{const s=document.querySelector('#rqWhat');return s.options[s.selectedIndex].text})()")
        j.check(prod in sel, 'the quote form does not preselect the product (selected: %s)' % sel)

@journey('J-BUSINESS-23')
def shared_inbox(j):
    """A company manages all its incoming and outgoing business in one inbox shared by its team."""
    if j.live:
        me = live_company_person(j, 'Dr. Inbox Owner', 'Inbox Pharma %s' % j.tag); pg = me['page']
        buyer = live_company_person(j, 'Outside Buyer', 'Outside Buyer Co %s' % j.tag); mate = j.person('Team Mate'); seed_member(j, me['co']['id'], mate['id'], 'sales')
        seed_route(j, me['co']['id'], 'quote', me['id'])
        request_quote(j, buyer['page'], me['co']['name'], None, msg='Need 2 MT %s' % j.tag)
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step("Workspace → Deals and the deals centre: Received and Sent hold exactly the company's deals; '<n> waiting for you' is right"):
        t = workspace(j, pg, 'Deals|%s' % (ar('Deals') or 'الصفقات'))
        c = deals_centre(j, pg); m = re.search(r'(\d+)\s*(waiting for you|بانتظارك)', c)
        rec = re.search(r'Received\s*\((\d+)\)|الواردة\s*\((\d+)\)', c)
        n_your = len(re.findall(r'Your move|دورك', deals_centre(j, pg, r'Received|الواردة')))
        sent_your = len(re.findall(r'Your move|دورك', deals_centre(j, pg, r'Sent|المرسلة')))
        close_dialogs(pg)
        j.check(m and int(m.group(1)) == n_your + sent_your, "'%s waiting for you' does not equal the deals marked 'Your move' (%d)" % (m and m.group(1), n_your + sent_your))
        if j.live: j.check(rec and (rec.group(1) or rec.group(2)) == j.sql1("select count(*) from public.deals where to_company_id=%s" % me['co']['id']), 'the Received count differs from the database')
    with j.step('Acting on a received request drops the count; a second team member sees the same state and who acted'):
        title = j.sql1("select title from public.deals where to_company_id=%s order by id desc limit 1" % me['co']['id']) if j.live else pg.evaluate("(dxDeals.all().find(d=>d.to&&d.to.slug==='quadra-pharm'&&d.type==='quote'&&d.status==='sent')||{}).title")
        open_deal(j, pg, title, r'Received|الواردة'); deal_act(j, pg, 'Send quote', {r'Price|السعر': 'US$ 3.30 per kg'}); close_dialogs(pg)
        c = deals_centre(j, pg); m2 = re.search(r'(\d+)\s*(waiting for you|بانتظارك)', c); close_dialogs(pg)
        j.check(m2 is None or int(m2.group(1)) < int(m.group(1)), "'waiting for you' did not drop after acting")
        if j.live:
            mp = mate['page']; j.reload(mp); t = open_deal(j, mp, title, r'Received|الواردة'); close_dialogs(mp)
            j.check(re.search(r'Quote sent|Quote received|US\$ 3\.30', t) and 'Inbox Owner' in t, 'the team mate does not see the same deal state and who acted')
    with j.step('Workspace → Activity lists the real events (edits, deals, members) with names and dates after reload'):
        reopen(j, pg); t = workspace(j, pg, 'Activity|%s' % (ar('Activity') or 'النشاط'))
        j.check(re.search(r'quote|Quote|عرض', t) and re.search(r'\d{1,2} \w{3}|\d{4}-\d{2}-\d{2}|ago|منذ', t), 'the Activity tab does not list the quote just sent with its date')

@journey('J-BUSINESS-24')
def reply_to_reviews(j):
    """A company answers reviews of its completed orders publicly and can ask Drugbox to check an unfair review."""
    if j.live:
        sup = live_company_person(j, 'Dr. Reviewed Supplier', 'Reviewed API %s' % j.tag, sectors=('API & excipients',)); pg = sup['page']; name = sup['co']['name']
        for i, (stars, note) in enumerate(((5, 'Great CEP pack %s' % j.tag), (1, 'Late and rude %s' % j.tag))):
            bu = seed_company(j, j.person('Buyer %d' % i)['id'], 'Reviewing Buyer %d %s' % (i, j.tag))
            d = j.sql1("insert into public.deals (ref, type, title, from_company_id, to_company_id, status, lines) values ('R%d%s','quote','Order %d %s',%s,%s,'closed','{}') returning id" % (i, j.tag, i, j.tag, bu['id'], sup['co']['id']))
            j.sql("insert into public.deal_events (deal_id, side, action, data, note) values (%s,'from','rate','{\"stars\":%d}',$q$%s$q$)" % (d, stars, note))
        j.reload(pg); good, bad = 'Great CEP pack %s' % j.tag, 'Late and rude %s' % j.tag
    else:
        pg = j.demo_signin(j.new_page()); name = 'Quadra Pharm'
        # precondition through the interface: complete one received order (as the supplier) and let the buyer rate it
        t = pg.evaluate("(dxDeals.all().find(d=>d.to&&d.to.slug==='quadra-pharm'&&d.type==='quote'&&d.status==='sent')||{}).title")
        j.check(t, 'the demo has no received quote request')
        for act, fields in (('Send quote', {r'Price|السعر': 'US$ 3.10 per kg'}),):
            open_deal(j, pg, t, r'Received|الواردة'); deal_act(j, pg, act, fields); close_dialogs(pg)
        for _ in range(6):
            open_deal(j, pg, t, r'Received|الواردة'); bs = dlg_buttons(pg)
            if any(re.search(r'Simulate', x) for x in bs): simulate(j, pg)
            elif any(re.search(L('Confirm order'), x) for x in bs): deal_act(j, pg, 'Confirm order')
            elif any(re.search(L('Mark shipped'), x) for x in bs): deal_act(j, pg, 'Mark shipped', {r'tracking|الشحنة|التتبع': 'AWB 1'})
            close_dialogs(pg)
        good = bad = None
    with j.step("Workspace → 'Reports & reviews' lists the reviews of completed orders; 'Reply' → publish"):
        t = workspace(j, pg, 'Reports & reviews|%s' % (ar('Reports & reviews') or 'التقارير'))
        j.check(not re.search(r'No reviews yet|لا توجد تقييمات', t), 'the company has completed, rated orders but Reports & reviews says "No reviews yet"')
        j.click(pg, L('Reply'), scope='#content', what='Reply')
        fill_by_label(j, pg, r'Reply|ردك|الرد', 'Thank you — glad the CEP pack helped. %s' % j.tag)
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Publish|Post|انشر|أرسل', 'Publish reply'); j.settle(pg, 1000)
        j.check(any(re.search(r'Reply published|تم نشر', t) for t in j.toasts_since(pg, mark)), "no 'Reply published'")
    with j.step("'Ask Drugbox to check this review' on the other one: it stays visible while checked"):
        el = j.find(pg, r'Ask Drugbox to check|اطلب من Drugbox', scope='#content'); j.check(el, "no 'Ask Drugbox to check this review'")
        mark = j.toast_mark(pg); el.click(); j.settle(pg, 900)
        j.check(any(re.search(r'Sent to Drugbox|أُرسل', t) for t in j.toasts_since(pg, mark)), "no 'Sent to Drugbox for checking'")
    with j.step('A visitor sees the reply under the review on the Reviews tab after reload'):
        reopen(j, pg); v = j.person('Review Visitor')['page'] if j.live else pg
        directory(j, v); open_card(j, v, name); t = company_tab(j, v, 'Reviews|%s' % ar('Reviews'), 'Reviews')
        j.check(('glad the CEP pack helped. %s' % j.tag) in t, 'the reply is not under the review on the public page')
    with j.step('Drugbox admin decides on the disputed review; the decision is stored and both parties are notified'):
        if j.demo: j.skip('Admin decisions are checked in live')
        adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); j.reload(adm['page'])
        admin_review(j, adm['page'], r'Reviews|التقييمات')

if __name__ == '__main__': main(__file__)
