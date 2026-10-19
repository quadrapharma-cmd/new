"""Business journeys — paying Drugbox: boosting a listing by card, Featured by mobile wallet, Fawry reference, InstaPay
transfer, payment history and invoices, VIP upgrade, included VIP boosts (J-BUSINESS-42 … 48).
Live: the payment functions and the Paymob/Fawry stand-in run (tools/local-supabase/start-payments.sh); the providers'
callbacks are played here with correctly signed webhooks (HMAC-SHA512 for Paymob, SHA-256 V2 for Fawry).
Run: python3 tests/journeys/business_payments.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

BOOST_TOTAL, FEAT_TOTAL = 1653, 4503          # payment_products: 1,450 and 3,950 + 14% VAT

def market(j, pg, tab='browse'):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
    t = pg.locator('.master-tab[data-tab=%s]:visible' % tab)
    if t.count(): t.first.click(); j.settle(pg, 700)
    return pg

def open_boost(j, pg, plan='boost'):
    """Market → the BOOST / FEATURED plan card (as a person clicks it) → the payment window."""
    market(j, pg)
    card = pg.locator('[onclick="openBoostModal(\'%s\')"]:visible' % plan).first
    j.check(card.count(), 'no %s plan card in the marketplace' % plan.upper()); card.click(); j.settle(pg, 1500)
    j.check(pg.locator('#boostModalOverlay.show, #boostModalOverlay:visible').count(), 'the %s card opens no payment window' % plan)
    return pg.evaluate("document.querySelector('#boostModalOverlay').innerText")

def choose_listing(j, pg, name):
    sel = pg.locator('#dxPayListing')
    j.check(sel.count(), 'the payment window does not ask which listing to boost')
    v = pg.evaluate("n=>{const s=document.getElementById('dxPayListing');const o=[...s.options].find(o=>o.textContent.includes(n));if(!o)return null;s.value=o.value;s.dispatchEvent(new Event('change',{bubbles:true}));return o.value}", name)
    j.check(v, 'my listing "%s" is not offered in the payment window' % name)
    return v

def pay(j, pg, method):
    m = pg.locator('#boostModalOverlay input[value=%s]' % method); j.check(m.count(), 'the payment window offers no %s' % method)
    m.first.click(); mark = j.toast_mark(pg)
    pg.click('#bmPayBtn'); j.settle(pg, 3000)
    return j.toasts_since(pg, mark)

def press_pay(j, pg):
    """The VIP payment window's 'Pay EGP …' (waits for it to start the payment; a second press if the first was too early)."""
    for _ in range(2):
        dlg_click(j, pg, r'^\W*(Pay EGP|ادفع)', 'Pay')
        end = time.time() + 8
        while time.time() < end and dlg_open(pg) and 'unifiedcheckout' not in pg.url: pg.wait_for_timeout(400)
        if not dlg_open(pg) or 'unifiedcheckout' in pg.url: return
    j.settle(pg, 1000)

def lister(j, name='Boosting Lister'):
    if j.demo: return {'page': j.demo_signin(j.new_page())}, None, 'Metformin HCl BP/USP'
    me = live_company_person(j, name, '%s Co %s' % (name, j.tag), sectors=('API & excipients',))
    lid = seed_listing(j, me['id'], 'Omeprazole pellets %s' % j.tag); j.reload(me['page'])
    return me, lid, 'Omeprazole pellets %s' % j.tag

def last_order(j, lid=None, cid=None):
    w = ('listing_id=%s' % lid) if lid else ('company_id=%s' % cid)
    return j.sql1("select id from public.payment_orders where %s order by id desc limit 1" % w)

def return_from_provider(j, pg, oid):
    j.open(pg, _dx.APP_URL + '?payment=%s' % oid); j.settle(pg, 2500)
    return pg.evaluate("window.__jt||[]")

@journey('J-BUSINESS-42')
def boost_by_card(j):
    """A lister pays by card to boost a listing so it reaches more buyers for 7 days."""
    me, lid, name = lister(j); pg = me['page']
    with j.step("Market → 'Boost' plan card → choose my listing; the window shows the server price (EGP 1,450 + 14% VAT = 1,653)"):
        t = open_boost(j, pg, 'boost')
        if j.live: choose_listing(j, pg, name); t = pg.evaluate("document.querySelector('#boostModalOverlay').innerText")
        j.check(BOOST_TOTAL in money(t) and 1450 in money(t), 'the boost window shows %s instead of the price EGP 1,450 + VAT = 1,653' % money(t))
        ui_ok(j, pg, 'boost window')
    with j.step("'💳 Card' → 'Pay EGP 1,653 now' → the Paymob page asks for the same amount"):
        said = pay(j, pg, 'card')
        if j.demo: j.skip('the demo takes no payment')
        j.check('unifiedcheckout' in pg.url, 'the card payment does not open the Paymob page (%s)' % pg.url[:80])
        oid = last_order(j, lid); j.check(oid, 'no payment order')
        j.check(j.sql1("select amount_cents||'|'||status||'|'||product_code from public.payment_orders where id=%s" % oid) == '%d00|pending|boost' % BOOST_TOTAL, 'the order is not a pending boost for 1,653 EGP')
        j.data['oid'] = oid
    with j.step("Paymob confirms (signed callback); back in the app: 'Payment received — it is active now'; the listing is BOOSTED for everyone"):
        if j.demo: j.skip('the demo takes no payment')
        oid = j.data['oid']; s_, r = paymob_callback(j, oid); j.check(s_ == 200, 'the signed callback was refused: %s %s' % (s_, r[:80]))
        ts = return_from_provider(j, pg, oid)
        j.check(any(re.search(r'Payment received|تم استلام الدفع', t) for t in ts), "no 'Payment received — it is active now' back in the app")
        j.check(j.sql1("select (boosted_until::date - now()::date) from public.products where id=%s" % lid) in ('7', '6'), 'the listing is not boosted for 7 days')
        o = j.person('Another Buyer'); op = o['page']; market(j, op)
        c = op.locator('#tab-browse :is(.lcard,.sponsored-card)', has_text=name).first
        j.check(c.count(), 'another user does not find the boosted listing on the marketplace page (it does not rank above unboosted listings)')
        j.check(re.search(r'BOOSTED|مميز|معزز', c.inner_text()), 'another user sees the listing without the BOOSTED label')
    with j.step("My Listings shows the boost end date"):
        if j.demo: j.skip('the demo takes no payment (its My Listings rows are the approved samples)')
        market(j, pg, 'manage'); t = pg.evaluate("(document.querySelector('#tab-manage')||{}).innerText||''")
        row = t[t.find(name):t.find(name) + 300] if name in t else ''
        j.check(re.search(r'BOOSTED', row) and re.search(r'until|ends|\d{1,2} \w{3}|حتى', row), 'My Listings does not show the boost with its end date')
    with j.step('A failed card payment: clear message, nothing activated, retry possible, no pile of pending orders'):
        if j.demo: j.skip('the demo takes no payment')
        lid2 = seed_listing(j, me['id'], 'Second listing %s' % j.tag); j.reload(pg)
        open_boost(j, pg, 'boost'); choose_listing(j, pg, 'Second listing %s' % j.tag); pay(j, pg, 'card')
        oid2 = last_order(j, lid2); paymob_callback(j, oid2, success=False)
        ts = return_from_provider(j, pg, oid2)
        j.check(any(re.search(r'fail|not completed|declined|لم يكتمل|فشل', t, re.I) for t in ts), 'a failed payment gives no clear message back in the app')
        j.check(j.sql1("select boosted_until is null from public.products where id=%s" % lid2) == 't', 'a failed payment boosted the listing')
        open_boost(j, pg, 'boost'); choose_listing(j, pg, 'Second listing %s' % j.tag); pay(j, pg, 'card'); j.open(pg, _dx.APP_URL)
        open_boost(j, pg, 'boost'); choose_listing(j, pg, 'Second listing %s' % j.tag); pay(j, pg, 'card')
        n = j.sql1("select count(*) from public.payment_orders where listing_id=%s and status='pending'" % lid2)
        j.check(n == '1', 'retrying leaves %s pending orders for the same listing' % n)
    with j.step('After 7 days the boost ends by itself'):
        if j.demo: j.skip('the clock cannot be moved in the demo')
        j.sql("update public.products set boosted_until=now()-interval '1 minute' where id=%s" % lid)
        o2 = j.person('Later Buyer'); market(j, o2['page'])
        c = o2['page'].locator('#tab-browse .lcard', has_text=name).first
        j.check(c.count() and not re.search(r'BOOSTED', c.inner_text()), 'the listing still shows BOOSTED after its 7 days')

@journey('J-BUSINESS-43')
def featured_by_wallet(j):
    """A lister pays with a mobile wallet (Vodafone Cash) to make a listing Featured for 30 days."""
    me, lid, name = lister(j, 'Featured Lister'); pg = me['page']
    with j.step("'Featured' plan card → the window is titled Featured and shows EGP 3,950 + VAT = 4,503"):
        t = open_boost(j, pg, 'featured')
        if j.live: choose_listing(j, pg, name); t = pg.evaluate("document.querySelector('#boostModalOverlay').innerText")
        j.check(re.search(r'Featured|مميزة|إبراز', t.split('\n')[1] if '\n' in t else t), "the Featured window is titled '%s'" % (t.split('\n')[1] if '\n' in t else t)[:40])
        j.check(FEAT_TOTAL in money(t), 'the Featured window shows %s instead of EGP 3,950 + VAT = 4,503' % money(t))
    with j.step("'📱 Vodafone Cash & wallets' → pay: the wallet integration is used"):
        pay(j, pg, 'wallet')
        if j.demo: j.skip('the demo takes no payment')
        oid = last_order(j, lid); j.check(j.sql1("select method||'|'||product_code from public.payment_orders where id=%s" % oid) == 'wallet|featured', 'the order is not a wallet payment for Featured')
        j.data['oid'] = oid
    with j.step('Paymob confirms the wallet payment: the listing is Featured (Sponsored Listings) for 30 days for everyone'):
        if j.demo: j.skip('the demo takes no payment')
        oid = j.data['oid']; env = fn_env(); s_, r = paymob_callback(j, oid, integration=int(env.get('PAYMOB_WALLET_INTEGRATION_ID', 222222)), src_type='wallet')
        j.check(s_ == 200, 'the wallet callback was refused: %s %s' % (s_, r[:80]))
        j.check(j.sql1("select (featured_until::date - now()::date) from public.products where id=%s" % lid) in ('30', '29'), 'the listing is not featured for 30 days')
        o = j.person('Featured Viewer'); market(j, o['page'])
        sp = o['page'].evaluate("(()=>{const s=[...document.querySelectorAll('#tab-browse .sponsored-card')].map(e=>e.innerText).join(' ');return s})()")
        j.check(name in sp, 'the listing is not in the Sponsored Listings area for another user')

@journey('J-BUSINESS-44')
def pay_at_fawry(j):
    """A lister without a card pays cash at a Fawry outlet using a reference number; the boost activates when Fawry confirms."""
    me, lid, name = lister(j, 'Fawry Lister'); pg = me['page']
    with j.step("Boost window → '🏪 Fawry' → pay: the Fawry reference number and amount are shown with how to pay"):
        open_boost(j, pg, 'boost')
        if j.live: choose_listing(j, pg, name)
        pay(j, pg, 'fawry'); t = dlg_text(pg)
        j.check(re.search(r'Fawry reference|رقم مرجع فوري', t) and re.search(r'\d{6,}', t), 'no Fawry reference number is shown')
        j.check(BOOST_TOTAL in money(t), 'the Fawry window does not show the amount EGP 1,653 (%s)' % money(t))
        j.data['ref'] = re.search(r'(\d{6,})', t).group(1)
    with j.step("Press 'Done'; later find the reference again (My payments / the listing)"):
        dlg_click(j, pg, r'^\W*(Done|تم|إغلاق|Close)\W*$', 'Done')
        reopen(j, pg); t = j.text(pg) + market(j, pg, 'manage').evaluate("(document.querySelector('#tab-manage')||{}).innerText||''")
        j.check(j.data['ref'] in t, 'not built: the Fawry reference cannot be found again after closing the window (no My payments)')
    with j.step("Fawry's signed PAID notification activates the boost and the user is notified; a wrong signature changes nothing"):
        if j.demo: j.skip('the demo takes no payment')
        oid = last_order(j, lid)
        s_, r = fawry_callback(j, oid, forge=True); j.check(j.sql1("select status from public.payment_orders where id=%s" % oid) == 'pending', 'a forged Fawry notification changed the order')
        s_, r = fawry_callback(j, oid, 'PAID'); j.check(s_ == 200, 'the PAID notification was refused: %s %s' % (s_, r[:80]))
        j.check(j.sql1("select boosted_until is not null from public.products where id=%s" % lid) == 't', 'the boost is not active after PAID')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='payment'" % me['id']) not in ('', '0'), 'the user is not notified of the payment')
    with j.step('An EXPIRED notification activates nothing and the user is told'):
        if j.demo: j.skip('the demo takes no payment')
        lid2 = seed_listing(j, me['id'], 'Expiring listing %s' % j.tag); j.reload(pg)
        open_boost(j, pg, 'boost'); choose_listing(j, pg, 'Expiring listing %s' % j.tag); pay(j, pg, 'fawry')
        oid2 = last_order(j, lid2); fawry_callback(j, oid2, 'EXPIRED')
        j.check(j.sql1("select status from public.payment_orders where id=%s" % oid2) == 'expired' and j.sql1("select boosted_until is null from public.products where id=%s" % lid2) == 't', 'an EXPIRED notification activated the boost or left the order pending')
        j.check(int(j.sql1("select count(*) from public.notifications where user_id='%s' and type='payment'" % me['id']) or 0) >= 2, 'the user is not told the Fawry reference expired')

@journey('J-BUSINESS-45')
def pay_by_instapay(j):
    """A lister pays by InstaPay transfer, uploads the receipt, and Drugbox confirms it so the purchase activates."""
    me, lid, name = lister(j, 'InstaPay Lister'); pg = me['page']
    with j.step("Boost window → '⚡ InstaPay' → pay: the InstaPay address and amount are shown"):
        open_boost(j, pg, 'boost')
        if j.live: choose_listing(j, pg, name)
        pay(j, pg, 'instapay'); t = dlg_text(pg)
        j.check(re.search(r'@instapay|InstaPay address|عنوان', t), 'no InstaPay address is shown')
        j.check(BOOST_TOTAL in money(t), 'the InstaPay window does not show EGP 1,653 (%s)' % money(t))
    with j.step("Enter the transfer number and attach the receipt; send: 'we confirm InstaPay transfers within one working day'; the order is Under review"):
        ref = pg.locator('.dbk-ov #dxIpRef, .dbk-ov input[type=text]:visible').first; j.check(ref.count(), 'no transfer number field'); ref.fill('IPN-%s' % j.tag)
        rc = pg.locator('.dbk-ov input[type=file]'); j.check(rc.count(), 'no receipt upload'); rc.first.set_input_files(PNG)
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Send for confirmation|أرسل', 'Send for confirmation'); j.settle(pg, 2000)
        said = ' '.join(j.toasts_since(pg, mark)) + dlg_text(pg)
        j.check(re.search(r'one working day|يوم عمل', said), "no 'we confirm InstaPay transfers within one working day'")
        if j.live: j.check(j.sql1("select status||'|'||(receipt_path like 'payments/%s/%%')::text from public.payment_orders where listing_id=%s order by id desc limit 1" % (me['id'], lid)) == 'review|true', 'the order is not under review with the receipt stored')
    with j.step('Drugbox admin: Admin → Review → Payments shows name, product, amount, transfer number and the receipt; Confirm → the boost activates and the lister is notified'):
        if j.demo: j.skip('Admin decisions are checked in live')
        adm = j.person('Drugbox Finance'); make_admin(j, adm['id']); ap = adm['page']; j.reload(ap)
        t = admin_review(j, ap, 'payments'); j.check(('IPN-%s' % j.tag) in t and '1,653' in t.replace('1653', '1,653'), 'the payment is not in Admin → Review → Payments with its amount')
        admin_decide(j, ap, 'IPN-%s' % j.tag, True)
        j.check(j.sql1("select boosted_until is not null from public.products where id=%s" % lid) == 't', 'confirming did not boost the listing')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='payment'" % me['id']) not in ('', '0'), 'the lister is not notified')
    with j.step('The lister reloads and sees the boost active; another user cannot open the receipt'):
        if j.demo: j.skip('checked in live')
        path = j.sql1("select receipt_path from public.payment_orders where listing_id=%s order by id desc limit 1" % lid)
        o = j.person('Curious User')
        r = o['page'].evaluate("p=>dxLive.sb.storage.from('documents').createSignedUrl(p,60).then(r=>r.error?null:r.data.signedUrl)", path)
        j.check(not r, 'another user can open the InstaPay receipt')

@journey('J-BUSINESS-46')
def payment_history(j):
    """A company sees what it has paid for, the status of each payment, and downloads a tax invoice."""
    if j.live:
        me = live_company_person(j, 'Paying Company Owner', 'Paying Pharma %s' % j.tag); pg = me['page']
        j.sql("insert into public.payment_orders (user_id, product_code, company_id, method, amount_cents, currency, status, paid_at) values ('%s','vip_month',%s,'card',285000,'EGP','paid',now()), ('%s','vip_month',%s,'fawry',285000,'EGP','pending',null)" % (me['id'], me['co']['id'], me['id'], me['co']['id']))
        j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Workspace → Plan & verification lists every payment: date, product, method, amount incl. VAT, status'):
        t = workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة'))
        j.check(re.search(r'Payment history|Billing|Invoices|سجل المدفوعات|الفواتير', t, re.I), 'not built: no payment history (billing) in Plan & verification or anywhere else')
    with j.step('A paid order has a downloadable invoice with VAT and the company name; pending ones can be resumed or cancelled'):
        b = j.find(pg, r'Invoice|Download|فاتورة|تنزيل', scope='#content'); j.check(b, 'not built: no tax invoice to download')
        if j.live: j.check(re.search(r'Waiting for payment|بانتظار الدفع', j.text(pg)), 'the pending Fawry order is not listed as waiting for payment')
        with pg.context.expect_page(timeout=8000) as pi: b.click()
        inv = pi.value; inv.wait_for_load_state(); it = inv.inner_text('body'); inv.close()
        co = me['co']['name'] if j.live else 'Quadra Pharm'
        j.check(re.search(r'Tax invoice', it) and re.search(r'DBX-INV-\d{4}-\d{6}', it) and re.search(r'VAT 14%', it) and co in it, 'the invoice does not show its number, VAT 14%% and the company (%s)' % it[:160].replace('\n', ' '))
        j.check(re.search(r'EGP 2,?500\.00', it) and re.search(r'EGP 350\.00', it) and re.search(r'EGP 2,?850\.00', it), 'the invoice amounts are not EGP 2,500.00 + 350.00 VAT = 2,850.00')
        if j.live:
            o = j.person('Not The Owner'); oid = j.sql1("select id from public.payment_orders where company_id=%s and status='paid' limit 1" % me['co']['id'])
            r = o['page'].evaluate("i=>dxLive.sb.rpc('order_invoice',{p_id:i}).then(r=>r.error?'refused':'given')", int(oid))
            j.check(r == 'refused', "another member can read the company's invoice")

@journey('J-BUSINESS-47')
def upgrade_to_vip(j):
    """A company upgrades to VIP to get top placement, the VIP badge, faster verification and monthly boosts."""
    if j.live:
        me = live_company_person(j, 'Upgrading Owner', 'Upgrade Pharma %s' % j.tag); pg = me['page']; name = me['co']['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Basic Upgrade %s' % j.tag
        create_company(j, pg, name); wizard_details(j, pg, name); dlg_click(j, pg, r'Next: review|التالي', 'Next: review'); dlg_click(j, pg, r'Create my page|أنشئ', 'Create my page'); j.settle(pg, 1200)
    with j.step("Workspace → Plan & verification → 'Get VIP' → VIP Monthly → 'Continue to payment': the server price EGP 2,500 + VAT = 2,850"):
        workspace(j, pg, 'Plan & verification|%s' % (ar('Plan & verification') or 'الخطة'))
        up = j.find(pg, r'^\W*(Get VIP|Upgrade|Upgrade to VIP|ترقية|احصل على VIP)\W*$', scope='#content')
        j.check(up, "no 'Upgrade' / 'Get VIP' in Plan & verification")
        up.click(); pg.wait_for_timeout(700)
        m = pg.locator('.dbk-ov input[name=plBill][value=month]')
        if m.count(): m.first.check()
        dlg_click(j, pg, r'Continue to payment|متابعة الدفع', 'Continue to payment')
        t = dlg_text(pg); j.check(2850 in money(t), 'the VIP payment shows %s instead of EGP 2,500 + VAT = 2,850' % money(t))
    with j.step('Pay by card (Paymob page, signed callback): VIP starts only when the payment is confirmed'):
        if j.demo:
            dlg_click(j, pg, r'^\W*Pay EGP|ادفع', 'Pay'); j.settle(pg, 1200)
        else:
            card = pg.locator('.dbk-ov input[value=card]'); j.check(card.count(), 'no card payment for VIP'); card.first.click()
            press_pay(j, pg)
            j.check(j.sql1("select plan from public.companies where id=%s" % me['co']['id']) == 'free', 'the company is VIP before paying')
            oid = last_order(j, cid=me['co']['id'])
            if not oid: j.fail("'Pay EGP 2,850' starts no payment: %s" % ('; '.join(pg.evaluate("(window.__jt||[]).slice(-3)")) or 'nothing happens'))
            s_, r = paymob_callback(j, oid); j.check(s_ == 200, 'the callback was refused')
            return_from_provider(j, pg, oid)
            j.check(j.sql1("select plan from public.companies where id=%s" % me['co']['id']) == 'vip', 'the company is not VIP after payment')
    with j.step("VIP badge, 'Sponsored' top of the directory for others, 'VIP monthly · renews <date>' in My companies"):
        t = my_companies(j, pg); j.check(re.search(re.escape(name) + r'[\s\S]{0,80}(VIP monthly · renews|VIP[^\n]{0,20}يتجدد)', t), "My companies does not say 'VIP monthly · renews <date>'"); close_dialogs(pg)
        v = j.person('Directory Visitor')['page'] if j.live else pg
        directory(j, v)
        sp = v.evaluate("(()=>{const t=document.querySelector('#dxDir').innerText;const i=t.search(/Sponsored|ممول/);return i>=0?t.slice(i,i+1500):''})()")
        j.check(name in sp, 'the VIP company is not in the Sponsored row')
    with j.step('Promised benefits are delivered: 3 Marketplace boosts a month without payment, verification queue priority, the company link'):
        market(j, pg);
        open_boost(j, pg, 'boost'); t = pg.evaluate("document.querySelector('#boostModalOverlay').innerText")
        j.check(re.search(r'included boost|boosts left|مجانية|متبقية', t, re.I), 'not built: the VIP plan promises 3 Marketplace boosts a month, but the boost window asks VIP companies to pay')
    with j.step('At the end date VIP expires to Basic automatically (with a reminder before)'):
        if j.demo: j.skip('the clock cannot be moved in the demo')
        j.sql("update public.companies set vip_until=now()-interval '1 minute' where id=%s" % me['co']['id']); j.sql("select public.expire_vip_plans()")
        j.check(j.sql1("select plan from public.companies where id=%s" % me['co']['id']) == 'free', 'VIP did not expire')

@journey('J-BUSINESS-48')
def included_boosts(j):
    """A VIP company uses its included monthly boosts without paying again."""
    if j.live:
        me = live_company_person(j, 'VIP Lister', 'VIP Lister Co %s' % j.tag, plan='vip'); pg = me['page']
        seed_listing(j, me['id'], 'VIP listing %s' % j.tag); j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step("My Listings → '⭐ Boost' on a listing → 'Use an included boost' (3 left)"):
        market(j, pg, 'manage')
        b = pg.locator('#tab-manage button:visible', has_text=re.compile(r'^\W*(Boost|ترقية)\W*$')).first      # the row's '⭐ Boost' button (not the 'Boosted' badge)
        j.check(b.count(), "no '⭐ Boost' in My Listings"); b.click(); j.settle(pg, 1200)
        t = pg.evaluate("(document.querySelector('#boostModalOverlay')||{}).innerText||''") + dlg_text(pg)
        j.check(re.search(r'Use an included boost|included boost|استخدم', t), "not built: a VIP company is asked to pay — there is no 'Use an included boost' (VIP promises 3 a month)")
        j.check(re.search(r'\b3 of 3\b|3 من 3|متبقٍ 3', t), "the window does not say 3 of 3 included boosts are left")
    with j.step("'Use an included boost': the listing is boosted for 7 days without a payment; 2 are left; a fourth use this month is refused"):
        mark = j.toast_mark(pg); pg.locator('#boostModalOverlay [data-inc]').first.click(); j.settle(pg, 1500)
        j.check(any(re.search(r'included with VIP|مجانًا مع VIP', x) for x in j.toasts_since(pg, mark)), "no 'Boost activated — included with VIP' confirmation")
        if j.demo: j.skip('the demo keeps the count in this browser; the database checks run in live')
        lid = j.sql1("select id from public.products where name='VIP listing %s'" % j.tag)
        j.check(j.wait_db("select (boosted_until::date - now()::date) from public.products where id=%s" % lid, 6) in ('7', '6'), 'the included boost did not boost the listing for 7 days')
        j.check(j.sql1("select count(*) from public.payment_orders where listing_id=%s" % lid) == '0', 'an included boost created a payment order')
        j.check(j.sql1("select count(*) from public.vip_boost_uses where company_id=%s" % me['co']['id']) == '1', 'the included boost was not counted')
        open_boost(j, pg, 'boost'); t = pg.evaluate("document.querySelector('#boostModalOverlay').innerText")
        j.check(re.search(r'\b2 of 3\b|2 من 3|متبقٍ 2', t), 'the window does not say 2 of 3 are left after one use')
        j.sql("insert into public.vip_boost_uses (company_id, listing_id, month) select %s, %s, date_trunc('month', now())::date from generate_series(1,2)" % (me['co']['id'], lid))
        r = pg.evaluate("([l,c])=>dxLive.sb.rpc('use_included_boost',{p_listing:l,p_company:c}).then(r=>r.error?r.error.message:'ok')", [int(lid), int(me['co']['id'])])
        j.check(r != 'ok' and j.sql1("select count(*) from public.vip_boost_uses where company_id=%s" % me['co']['id']) == '3', 'a fourth included boost this month was allowed: %s' % r)

if __name__ == '__main__': main(__file__)
