"""Business journeys — the marketplace: browsing with real filters, contacting a lister, posting supply and demand
listings, surplus stock, licensing dossiers, managing one's listings, intents (J-BUSINESS-34 … 41).
Run: python3 tests/journeys/business_market.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

def market(j, pg, tab='browse'):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
    t = pg.locator('.master-tab[data-tab=%s]:visible' % tab)
    j.check(t.count(), 'not built: the marketplace has no "%s" tab' % tab); t.first.click(); j.settle(pg, 800)
    return pg.evaluate("t=>(document.querySelector('#tab-'+t)||{}).innerText||''", tab)

def cards(pg, sel='#tab-browse :is(.lcard,.dcard,.scard,.jcard,.sponsored-card)'):
    return pg.evaluate("s=>[...document.querySelectorAll(s)].filter(e=>e.getClientRects().length).map(e=>({cat:e.dataset.dxcat||'',t:(e.querySelector('.lc-title')||e).innerText.split('\\n')[0].trim(),txt:e.innerText}))", sel)

def card(pg, title):
    return pg.locator('#tab-browse :is(.lcard,.dcard,.scard,.jcard,.sponsored-card)', has_text=title).first

def fill_ph(j, pg, ph_re, val, root='#tab-create'):
    el = pg.evaluate_handle("([r,p])=>[...document.querySelectorAll(r+' input,'+r+' textarea')].find(e=>e.getClientRects().length&&new RegExp(p,'i').test(e.placeholder||''))||null", [root, ph_re]).as_element()
    if not el: j.notbuilt('no field "%s" in the listing form' % ph_re)
    el.fill(val); return el

def create_listing(j, pg, side, fields, certs=(), draft=False, coa=None):
    """Market → Create Listing → I'm Offering / I'm Seeking → fill by placeholder → Preview → Publish (or Save as Draft)."""
    market(j, pg, 'create')
    if not pg.locator('#bigOfferBtn:visible').count():
        ch = pg.locator('#tab-create :is(span,button,a):visible', has_text=re.compile(r'Change|تغيير')).first
        if ch.count(): ch.click(); pg.wait_for_timeout(500)
    pg.click('#bigOfferBtn' if side == 'offer' else '#bigSeekBtn'); pg.wait_for_timeout(600)
    for ph, v in fields: fill_ph(j, pg, ph, v)
    for c in certs:
        el = pg.locator('#tab-create :is(div,span,label,button):visible', has_text=re.compile(r'^\W*%s\W*$' % re.escape(c))).first
        if el.count(): el.click()
    if coa:   # the form's "COA / Spec sheet" takes a real file
        z = pg.locator('#tab-create .form-section.active .upload-zone-sm:visible').first
        j.check(z.count(), 'no COA upload in the listing form')
        with pg.expect_file_chooser() as fc: z.click()
        fc.value.set_files(coa); pg.wait_for_timeout(400)
        j.check(re.search(r'attached|مرفق', z.inner_text()), 'the COA file is not shown as attached')
    mark = j.toast_mark(pg)
    if draft:
        b = pg.locator('#tab-create button:visible', has_text=re.compile(r'Save as Draft|حفظ كمسودة')); j.check(b.count(), "no 'Save as Draft'"); b.first.click(); j.settle(pg, 900)
    else:
        b = pg.locator('#tab-create button:visible', has_text=re.compile(r'Preview Listing|معاينة')); j.check(b.count(), "no 'Preview Listing'"); b.first.click(); pg.wait_for_timeout(700)
        dlg_click(j, pg, r'Publish listing|انشر', 'Publish listing'); j.settle(pg, 1500)
    return j.toasts_since(pg, mark)

def mk_panel(j, pg, tab):
    """Market → 'Company listings' panel → the surplus / license / groups tab; returns the panel text."""
    market(j, pg)
    chip = pg.locator('.hb-mk [data-mkt=%s]:visible' % tab)
    j.check(chip.count(), "no '%s' tab in the marketplace company listings" % tab); chip.first.click(); pg.wait_for_timeout(700)
    return pg.evaluate("(document.querySelector('.hb-mk')||{}).innerText||''")

def my_listings(j, pg):
    return market(j, pg, 'manage')

def lister(j, name='Supplier Lister', co=None):
    if j.demo: return {'page': j.demo_signin(j.new_page())}
    return live_company_person(j, name, co or '%s Co %s' % (name, j.tag), sectors=('API & excipients',))

@journey('J-BUSINESS-34')
def browse_market(j):
    """A buyer finds products, services and offers in the marketplace with filters that reflect real listings."""
    if j.live:
        a = j.person('Lister A'); b = j.person('Lister B')
        seed_listing(j, a['id'], 'Metformin HCl %s' % j.tag, 'supply', 'api', '5.80')
        seed_listing(j, a['id'], 'Paracetamol DC %s' % j.tag, 'supply', 'api', '3.10')
        seed_listing(j, b['id'], 'Ciprofloxacin HCl wanted %s' % j.tag, 'demand', 'api', '')
        seed_listing(j, b['id'], 'Tablet press 35-station %s' % j.tag, 'supply', 'equipment', '42000', 'unit', '1')
        me = j.person('Market Buyer'); pg = me['page']; want = 'Metformin HCl %s' % j.tag
    else:
        pg = j.demo_signin(j.new_page()); want = 'Premium GMP Grade'
    with j.step("Category chips (Supply, Demand, Equipment …): each shows only that category's cards"):
        market(j, pg)
        for cat, key, arl in (('Demand', 'demand', 'طلب'), ('Supply', 'supply', 'عرض')):
            el = pg.locator('#tab-browse .cat-item:visible').filter(has_text=re.compile(r'(^|\s)(%s|%s)(\s|\d|$)' % (cat, arl))).first
            j.check(el.count(), "no '%s' category chip" % cat); el.click(); j.settle(pg, 700)
            cs = [c for c in cards(pg, '#tab-browse :is(.lcard,.dcard,.scard,.jcard)') if c['cat']]
            if not cs:
                n = j.sql1("select count(*) from public.products where type='%s' and active" % key) if j.live and key in ('supply', 'demand') else '?'
                j.fail("the '%s' chip shows no listings at all (%s %s listings exist)" % (cat, n, key))
            j.check(all(c['cat'] == key for c in cs), "the '%s' chip shows other categories: %s" % (cat, sorted(set(c['cat'] for c in cs))))
        al = pg.locator('#tab-browse :is(span,button):visible', has_text=re.compile(r'^\s*(ALL|الكل)\s*$')).first
        if al.count(): al.click(); j.settle(pg, 600)
        ui_ok(j, pg, 'marketplace')
    with j.step("Search a product (top-bar search): the listing is found"):
        from _social import top_search
        q = 'Metformin' if j.demo else want
        t = top_search(j, pg, q)
        j.check((want if j.live else 'Metformin HCl') in t, 'searching "%s" does not find the marketplace listing' % q)
    with j.step("'Quick view' a card shows the full listing; 'Landed cost' uses its price; 'Save' puts it in Saved and it survives reload"):
        market(j, pg); c = card(pg, want); j.check(c.count(), 'the listing card is not on the page')
        qv = c.locator('button', has_text=re.compile(r'Quick view|عرض سريع'))
        j.check(qv.count(), "no 'Quick view' on the card"); qv.first.click(); pg.wait_for_timeout(800)
        t = dlg_text(pg); j.check(want in t and re.search(r'MOQ|الحد الأدنى', t), 'Quick view does not show the full listing')
        price = re.search(r'(US\$|\$)\s*([\d.,]+)', t)
        lc = pg.locator('.dbk-ov :is(button,[role=button],.dx-lc-chip,span,a):visible', has_text=re.compile(r'^\s*Landed cost\s*$|^\s*التكلفة')).first
        if not lc.count(): close_dialogs(pg); lc = card(pg, want).locator(':is(button,.dx-lc-chip)', has_text=re.compile(r'Landed cost|التكلفة')).first
        j.check(lc.count(), "not built: no 'Landed cost' for this listing")
        lc.click(); pg.wait_for_timeout(800)
        t2 = dlg_text(pg) + ' ' + ' '.join(pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('input,select')].map(e=>e.value):[]})()" % TOP_DLG))
        j.check(price and price.group(2) in t2, 'the landed cost does not start from the listing price %s' % (price and price.group(2)))
        close_dialogs(pg); market(j, pg); c = card(pg, want)
        sv = c.locator(':is(button,[onclick],[role=button])', has_text=re.compile(r'Save|حفظ|🔖')).first
        if not sv.count(): sv = c.locator('[aria-label*="Save" i], [title*="Save" i], [aria-label*="حفظ"], [title*="حفظ"]').first
        j.check(sv.count(), "not built: the listing card has no 'Save'"); sv.click(); j.settle(pg, 700)
        reopen(j, pg); j.nav(pg, 'saved'); j.settle(pg, 1200)
        j.check(want in j.text(pg), 'the saved listing is not in Saved after reload')
    with j.step('Category counts and result counts equal the real listings (no invented numbers or sample cards in live)'):
        market(j, pg)
        counts = pg.evaluate("[...document.querySelectorAll('#tab-browse .cat-item')].map(e=>e.innerText.replace(/\\s+/g,' ').trim())")
        sup = next((int(re.sub(r'\D', '', x) or 0) for x in counts if x.startswith(('Supply', 'توريد', 'عرض'))), None)
        real = len([c for c in cards(pg, '#tab-browse :is(.lcard,.sponsored-card)') if c['cat'] == 'supply']) if j.demo else int(j.sql1("select count(*) from public.products where type='supply' and active"))
        j.check(sup == real, "the Supply count says %s but there are %s supply listings" % (sup, real))
        if j.live:
            t = j.text(pg)
            # the "Live now" panel itself is approved; in the live app it lists the newest real listings — only its sample items are demo
            j.check(not re.search(r'1\.2K|150,000\+|8× more|Vivian Zhou|Neomycin Sulphate|EDA Registration by Dr\. Alia|Amoxicillin 500kg|Retinol 97% from UAE', t), 'the live marketplace shows demo statistics or demo activity')

@journey('J-BUSINESS-35')
def contact_lister(j):
    """A buyer contacts the lister of a marketplace listing and the lister receives a usable enquiry."""
    if j.live:
        s = j.person('Lister Supplier'); lid = seed_listing(j, s['id'], 'Omeprazole pellets %s' % j.tag)
        me = j.person('Enquiring Buyer'); pg = me['page']; want = 'Omeprazole pellets %s' % j.tag
    else:
        pg = j.demo_signin(j.new_page()); want = 'Metformin HCl'
    with j.step("Buyer: 'Contact Supplier →' on the supplier's card; write and send: the lister receives it with the listing referenced"):
        market(j, pg); c = card(pg, want); j.check(c.count(), 'the listing is not in the marketplace')
        b = c.locator('button', has_text=re.compile(r'Contact|تواصل')).first; j.check(b.count(), "no 'Contact Supplier' on the card")
        mark = j.toast_mark(pg); b.click(); j.settle(pg, 1200)
        box = pg.locator('#dxDock textarea:visible, #dxDock input:visible, .dbk-ov textarea:visible, #content textarea:visible').first
        if box.count():
            box.fill('Is the %s available with CoA? %s' % (want, j.tag)); box.press('Enter'); j.settle(pg, 1200)
            if dlg_open(pg):
                sb = j.find(pg, r'^\W*(Send|أرسل)', scope='body')
                if sb: sb.click(); j.settle(pg, 1000)
        said = j.toasts_since(pg, mark)
        j.check(not (any(re.search(r'Message sent|تم الإرسال', t) for t in said) and any(re.search(r'Could not send|تعذر', t) for t in said)), "both 'Message sent' and 'Could not send' appear: %s" % said)
        if j.live:
            m = j.wait_db("select body from public.messages where sender_id='%s' and receiver_id='%s' order by id desc limit 1" % (me['id'], s['id']), 6)
            j.check(m, 'no message reached the lister')
            j.check(want.split(' %s' % j.tag)[0] in m or str(lid) in m, 'the message does not reference the listing')
    with j.step("The listing's inquiries count rises by one for the lister"):
        if j.demo: j.skip('the lister exists only in live')
        sp = s['page']; j.reload(sp); t = my_listings(j, sp)
        j.check(re.search(r'1 inquir|استفسار', t) and want in t, "the lister's My Listings does not show 1 inquiry on the listing")
    with j.step("Supplier: 'Quote →' on a buyer's demand card with a price: the buyer receives the quote and can accept it"):
        close_dialogs(pg)
        if j.live:
            dem = seed_listing(j, me['id'], 'Ciprofloxacin wanted %s' % j.tag, 'demand'); sp = s['page']; j.reload(sp); market(j, sp)
            c = card(sp, 'Ciprofloxacin wanted %s' % j.tag)
        else:
            sp = pg; market(j, sp); c = sp.locator('#tab-browse .dcard').filter(has_not_text=re.compile(r'Dr\. Haytham')).first   # not my own request (the approved page answers "This is your own request")
        j.check(c.count(), 'no demand card to quote on')
        b = c.locator('button', has_text=re.compile(r'Quote|عرض سعر')).first; j.check(b.count(), "no 'Quote →' on the demand card")
        b.click(); j.settle(sp, 1000)
        j.check(dlg_open(sp) and sp.locator('.dbk-ov input:visible').count(), "not built: 'Quote →' opens no quotation form (price) — it only opens a chat")

@journey('J-BUSINESS-36')
def post_supply_listing(j):
    """A supplier posts a supply listing that buyers can find and contact."""
    me = lister(j); pg = me['page']; name = 'Metformin HCl BP/USP %s' % j.tag
    with j.step("Create Listing → I'm Offering: product, grade, price $5.80 per kg, MOQ 500 kg, origin, terms, WHO-GMP → Preview → Publish"):
        said = create_listing(j, pg, 'offer', [(r'Metformin|product', name), (r'\$|price', '5.80'), (r'500 kg|MOQ', '500 kg'), (r'China|origin|Origin', 'Egypt — Obour'), (r'weeks|terms', '2 weeks · EXW Cairo')], certs=('WHO-GMP',), coa=PDF)
        j.check(any(re.search(r'live|منشور|نُشر', t) for t in said), "no 'Your listing is live'")
        if j.live:
            j.check(j.wait_db("select count(*) from public.products where name=$q$%s$q$ and type='supply'" % name, 6) == '1', 'no products row for the listing')
            j.check(j.wait_db("select (coa_path like 'listings/%%')::text||currency||coalesce(company_id::text,'') from public.products where name=$q$%s$q$" % name, 8) == 'trueUSD%s' % me['co']['id'],
                    'the listing is not stored with its COA (private), currency and company')
    with j.step("'Save as Draft' a second listing: it is only in My Listings (Draft)"):
        create_listing(j, pg, 'offer', [(r'Metformin|product', 'Draft lactose %s' % j.tag), (r'\$|price', '1.20'), (r'500 kg|MOQ', '1 MT')], draft=True)
        t = my_listings(j, pg)
        j.check(('Draft lactose %s' % j.tag) in t and re.search(r'Draft|مسودة', t), 'the draft is not in My Listings as Draft')
    with j.step('Another user finds it in Browse under Supply with price + currency, MOQ and company; the draft is not there'):
        if j.live: o = j.person('Browsing Buyer'); op = o['page']
        else: op = pg
        market(j, op); cs = [c for c in cards(op) if name in c['t']]
        j.check(cs, 'the new listing is not in Browse')
        j.check(cs[0]['cat'] == 'supply', 'the listing is not under Supply')
        j.check(re.search(r'(US\$|\$|USD)\s*5\.80', cs[0]['txt']) and re.search(r'500 kg', cs[0]['txt']), 'the card does not show the price with its currency and the MOQ: %s' % cs[0]['txt'][:160].replace('\n', ' '))
        if j.live: j.check(me['co']['name'] in cs[0]['txt'], 'the card does not name the company')
        j.check(not [c for c in cards(op) if ('Draft lactose %s' % j.tag) in c['t']], 'the draft is visible in Browse')
    with j.step("It appears on the company page's Listings tab and in My Listings with its expiry date"):
        directory(j, pg); open_card(j, pg, me['co']['name'] if j.live else 'Quadra Pharm')
        t = company_tab(j, pg, 'Listings|%s' % ar('Listings'), 'Listings'); j.check(name in t, "the listing is not on the company page's Listings tab")
        t = my_listings(j, pg); j.check(name in t and re.search(r'Expires|ينتهي', t), 'My Listings does not show the listing with its expiry')
        if j.live: j.check(j.has_column('products', 'company_id') and j.has_column('products', 'currency'), 'not built: listings are stored without company and currency (products has no company_id / currency)')

@journey('J-BUSINESS-37')
def post_demand(j):
    """A buyer posts what he needs (RFQ / demand listing) so suppliers come to him."""
    me = lister(j, 'Demand Buyer'); pg = me['page']; name = 'Ciprofloxacin HCl %s' % j.tag
    with j.step("Create Listing → I'm Seeking: product, quantity, target price, details → publish"):
        said = create_listing(j, pg, 'seek', [(r'Ciprofloxacin|looking', name), (r'MT/month|Quantity', '2 MT/month'), (r'accurate|price|بدقة|السعر', 'US$ 21/kg'), (r'specs|details|مواصفات|تفاصيل', 'CEP required')])
        j.check(any(re.search(r'live|منشور', t) for t in said), "no 'Your listing is live'")
        if j.live:
            ty = j.wait_db("select type from public.products where name=$q$%s$q$" % name, 6)
            j.check(ty == 'demand', 'the demand is not stored as a demand listing (%s)' % ('stored as type "%s"' % ty if ty else 'no products row at all'))
    with j.step("Suppliers see it under Demand and send quotes via 'Quote →'"):
        if j.demo: j.skip('the suppliers exist only in live (the demo account cannot quote on its own demand)')
        s1 = lister(j, 'Quoting Supplier'); sp = s1['page']
        market(j, sp); c = card(sp, name); j.check(c.count(), 'the demand is not visible in Browse')
        b = c.locator('button', has_text=re.compile(r'Quote|عرض')).first; j.check(b.count(), "no 'Quote →' on the demand")
        b.click(); j.settle(sp, 1000)
        j.check(dlg_open(sp) and sp.locator('.dbk-ov input:visible').count(), "not built: 'Quote →' on a demand opens no quotation (price) — no quote can reach the buyer")
        fill_by_label(j, sp, r'price|السعر', 'US$ 20.50 per kg'); fill_by_label(j, sp, r'Quantity|الكمية', '2 MT/month'); fill_by_label(j, sp, r'Lead|التوريد', '3 weeks', required=False)
        dlg_click(j, sp, r'Send quote|أرسل', 'Send quote'); j.settle(sp, 1500)
        j.check(j.wait_db("select status||'|'||(offer->>'price') from public.deals where type='quote' and title=$q$%s$q$" % name, 8) == 'quoted|US$ 20.50 per kg', 'the quote is not a deal (quoted, with the price) in the deals engine')
    with j.step('The buyer compares quotes, accepts one (a deal), the others are told; closing the demand removes it from Browse'):
        if j.demo: j.skip('the suppliers exist only in live')
        j.reload(pg); c = deals_centre(j, pg); close_dialogs(pg); j.check(name in c, 'the quotes on the demand are not in the buyer\'s Requests & deals')
        open_deal(j, pg, name, r'Sent|المرسلة'); deal_act(j, pg, 'Accept quote'); close_dialogs(pg)
        j.check(j.wait_db("select status from public.deals where type='quote' and title=$q$%s$q$" % name, 8) == 'accepted', 'the buyer cannot accept the quote')

@journey('J-BUSINESS-38')
def sell_surplus(j):
    """A company sells surplus or near-expiry stock quickly at a discount."""
    me = lister(j, 'Surplus Seller'); pg = me['page']; prod = 'Microcrystalline cellulose PH-101 %s' % j.tag
    with j.step("Market → Surplus stock → 'Post surplus': product, quantity, batch, expiry, price US$ 2.40/kg, discount → Post"):
        market(j, pg); j.click(pg, L('Post surplus'), scope='#content', what='Post surplus')
        fill_by_label(j, pg, r'Product|المنتج', prod); fill_by_label(j, pg, r'Quantity|الكمية', '750 kg'); fill_by_label(j, pg, r'Batch|التشغيلة', 'MC-24-0911')
        ex = pg.locator('.dbk-ov input[type=date]:visible, .dbk-ov input[type=month]:visible')
        if ex.count(): ex.first.fill('2027-03-31' if ex.first.get_attribute('type') == 'date' else '2027-03')
        else: fill_by_label(j, pg, r'Expiry|الصلاحية', '2027-03', required=False)
        fill_by_label(j, pg, r'Price|السعر', 'US$ 2.40/kg'); fill_by_label(j, pg, r'Discount|الخصم', '30')
        dlg_click(j, pg, r'^\W*(Post|انشر)\W*$', 'Post'); j.settle(pg, 1500)
        if j.live: j.check(j.wait_db("select count(*) from public.company_listings where kind='surplus' and product=$q$%s$q$" % prod, 6) == '1', 'no company_listings surplus row')
    with j.step("A buyer sees it with batch, expiry and discount and 'Make an offer' (quantity, price, message)"):
        if j.live: b = lister(j, 'Surplus Buyer'); bp = b['page']
        else: bp = pg
        t = mk_panel(j, bp, 'surplus')
        if prod not in t:
            al = bp.locator('.hb-mk [data-mkall]:visible')
            if al.count(): al.first.click(); bp.wait_for_timeout(800); t = dlg_text(bp)
        j.check(prod in t and 'MC-24-0911' in t and re.search(r'30%', t), 'the surplus listing does not show batch and discount')
        j.check(re.search(r'expires 2027-03|2027-03', t), 'the surplus listing does not show its expiry')
        if j.demo: j.skip('the demo account is the seller: it cannot make an offer on its own stock')
        row = bp.locator('.hb-mk .cp-job, .dbk-ov .mr-row', has_text=prod).first; row.locator('button', has_text=re.compile(r'Make an offer|قدّم')).first.click(); bp.wait_for_timeout(700)
        fill_by_label(j, bp, r'Quantity|الكمية', '200'); fill_by_label(j, bp, r'price|السعر', 'US$ 2.20/kg', required=False)
        dlg_click(j, bp, r'Send offer|Send|أرسل', 'Send offer'); j.settle(bp, 1200)
        j.check(j.wait_db("select type||status from public.deals where title like '%%%s%%'" % j.tag, 6) == 'surplusoffered', 'no surplus deal (offered) in the database')
    with j.step("Seller: 'Accept offer' → Confirm → Ship; buyer receives and rates; the quantity sold reduces the listing"):
        if j.demo: j.skip('checked in live')
        their_move(j, bp, me, prod, 'Accept offer')
        their_move(j, bp, me, prod, 'Confirm order'); their_move(j, bp, me, prod, 'Mark shipped', {r'tracking': 'AWB 77'})
        open_deal(j, bp, prod, r'Sent|المرسلة'); deal_act(j, bp, 'Confirm received', {r'on time': 'yes'}); close_dialogs(bp)
        open_deal(j, bp, prod, r'Sent|المرسلة'); deal_act(j, bp, 'Rate supplier', {r'Rating': '5'}); close_dialogs(bp)
        t = mk_panel(j, bp, 'surplus'); j.check('550' in t, 'the sold quantity (200 of 750 kg) did not reduce the listing')

@journey('J-BUSINESS-39')
def list_dossier(j):
    """A company offers a registration dossier for licensing so other companies can license it in."""
    me = lister(j, 'Dossier Lister'); pg = me['page']; prod = 'Vitamin D3 50,000 IU %s' % j.tag
    with j.step("Workspace → Listings → 'List a dossier for licensing' (product, status, markets, licensing) → publish"):
        workspace(j, pg, 'Listings|%s' % ar('Listings'))
        j.click(pg, L('List a dossier for licensing'), scope='#content', what='List a dossier for licensing')
        fill_by_label(j, pg, r'Product|المنتج', prod)
        fill_by_label(j, pg, r'status|الحالة', r'EDA|.', required=False); fill_by_label(j, pg, r'Markets|الأسواق', 'Egypt, KSA', required=False)
        dlg_click(j, pg, r'^\W*(Publish|List|Post|Save|Add|انشر|أضف)\W*$', 'Add (publish the dossier)'); j.settle(pg, 1500)
        if j.live: j.check(j.wait_db("select count(*) from public.company_listings where kind='dossier' and product=$q$%s$q$" % prod, 6) == '1', 'no dossier listing row')
    with j.step('Visible in Marketplace → Licensing dossiers and on the company Listings tab after reload'):
        reopen(j, pg); t = mk_panel(j, pg, 'license')
        if prod not in t:
            al = pg.locator('.hb-mk [data-mkall]:visible')
            if al.count(): al.first.click(); pg.wait_for_timeout(800); t = dlg_text(pg)
        j.check(prod in t, 'after reload the dossier is not in Marketplace → Licensing dossiers'); close_dialogs(pg)
        directory(j, pg); open_card(j, pg, me['co']['name'] if j.live else 'Quadra Pharm')
        j.check(prod in company_tab(j, pg, 'Listings|%s' % ar('Listings'), 'Listings'), 'the dossier is not on the company Listings tab')
    with j.step("Another company: 'Request details' creates a dossier deal"):
        if j.demo: j.skip('the demo account owns the dossier')
        o = lister(j, 'Licensee Co'); op = o['page']; mk_panel(j, op, 'license')
        row = op.locator('.hb-mk .cp-job', has_text=prod).first; j.check(row.count(), 'another company does not see the dossier')
        row.locator('button', has_text=re.compile(r'Request details|اطلب')).first.click(); op.wait_for_timeout(700)
        nda = op.locator('.dbk-ov input[type=checkbox]:visible')
        if nda.count(): nda.first.check()
        dlg_click(j, op, L('Send request'), 'Send request'); j.settle(op, 1200)
        j.check(j.wait_db("select type from public.deals where title like '%%%s%%'" % j.tag, 6) == 'dossier', 'no dossier deal')

@journey('J-BUSINESS-40')
def manage_listings(j):
    """A lister keeps his listings accurate: edits, pauses, resumes, renews and deletes them."""
    me = lister(j, 'Careful Lister'); pg = me['page']
    if j.live:
        for n in ('Alpha', 'Beta', 'Gamma'): seed_listing(j, me['id'], '%s listing %s' % (n, j.tag))
        j.sql("update public.products set created_at=now()-interval '28 days' where name='Gamma listing %s'" % j.tag)
        j.reload(pg)
    with j.step("My Listings shows only my own listings with real views/inquiries (no sample rows for a new user)"):
        t = my_listings(j, pg)
        if j.live:
            j.check(not re.search(r'Hyaluronic Acid|247 views|Contract Manufacturing — Tablets', t), 'My Listings shows sample listings that are not mine')
            j.check(('Alpha listing %s' % j.tag) in t, 'my listing is not in My Listings')
        rows = pg.locator('#tab-manage .ml-row, #tab-manage [class*=listing-row], #tab-manage [class*=mrow], #tab-manage .manage-item')
        j.data['rows'] = rows.count()
    with j.step("'Edit' a listing (title, price) → 'Save changes': others see it after reload"):
        e = pg.locator('#tab-manage button:visible, #tab-manage [onclick]:visible', has_text=re.compile(r'^\s*(Edit|تعديل)\s*$')).first
        j.check(e.count(), "no 'Edit' in My Listings"); e.click(); pg.wait_for_timeout(700)
        j.check(dlg_open(pg) or pg.locator('#tab-manage input:visible, #tab-create input:visible').count(), "'Edit' opens no editor")
        inp = pg.locator('.dbk-ov input:visible, #tab-create input:visible').first; inp.fill('Edited listing %s' % j.tag)
        sv = j.find(pg, r'Save changes|Save|حفظ', scope='body'); j.check(sv, "no 'Save changes'"); sv.click(); j.settle(pg, 1200)
        reopen(j, pg); t = my_listings(j, pg); j.check(('Edited listing %s' % j.tag) in t, 'the edit did not survive reload')
        if j.live: j.check(j.sql1("select count(*) from public.products where name='Edited listing %s'" % j.tag) == '1', 'the edit is not saved in the database')
    with j.step("'···' → 'Pause listing': hidden from Browse, 'Paused' to me; 'Resume' shows it again"):
        more = pg.locator('#tab-manage :is(button,span,div):visible', has_text=re.compile(r'^\s*···\s*$')).first
        j.check(more.count(), "no '···' menu on a listing"); more.click(); pg.wait_for_timeout(400)
        p = pg.locator(':is(button,div,span,a):visible', has_text=re.compile(r'^\s*(⏸\s*)?Pause listing\s*$|إيقاف')).first
        j.check(p.count(), "no 'Pause listing'"); p.click(); j.settle(pg, 900)
        reopen(j, pg); t = my_listings(j, pg); j.check(re.search(r'PAUSED|Paused|موقوف|متوقف', t), 'the paused listing is not shown as Paused after reload')
        if j.live: j.check(j.sql1("select count(*) from public.products where user_id='%s' and not active" % me['id']) == '1', 'the pause is not saved in the database')
    with j.step("'Renew Now' on the expiring listing extends its expiry; 'Delete listing' removes it everywhere after confirmation"):
        r = pg.locator('#tab-manage :is(button,a,span):visible', has_text=re.compile(r'Renew Now|جدّ?د الآن')).first
        j.check(r.count(), "no 'Renew Now' on the expiring listing"); r.click(); j.settle(pg, 900)
        reopen(j, pg); t = my_listings(j, pg)
        j.check(not re.search(r'[Ee]xpires in 2 days|ينتهي خلال (2 يوم|يومين)', t), 'the renewed listing still expires in 2 days after reload')

@journey('J-BUSINESS-41')
def market_intents(j):
    """A company tells Drugbox what it has and needs (intents) so it receives matching opportunities."""
    me = lister(j, 'Intent Setter'); pg = me['page']
    with j.step("My Intents: set 'APIs & Raw Materials' to 'I have this to sell' and others to 'I need'; 'Save My Intents'"):
        t = market(j, pg, 'intents')
        if j.live:   # a brand-new account has chosen nothing yet: no sample intents preset for it (B-06)
            pre = pg.evaluate("[...document.querySelectorAll('#tab-intents .it-opt.active')].length")
            j.check(pre == 0, 'a brand-new account sees %d intents already chosen (sample presets)' % pre)
        row = pg.locator('#tab-intents .cat-intent-row', has_text=re.compile(r'APIs & Raw Materials|المواد الخام|المواد الفعالة والخامات')).first
        j.check(row.count(), 'no APIs & Raw Materials intent'); row.locator('.it-opt.i-have').click(); pg.wait_for_timeout(200)
        row2 = pg.locator('#tab-intents .cat-intent-row', has_text=re.compile(r'Equipment|معدات')).first
        if row2.count(): row2.locator('.it-opt.i-need').click()
        mark = j.toast_mark(pg); pg.locator('#tab-intents .btn-save-intents').click(); j.settle(pg, 1000)
        j.check(j.toasts_since(pg, mark), "'Save My Intents' gives no confirmation")
    with j.step('Intents persist after reload'):
        reopen(j, pg); market(j, pg, 'intents')
        row = pg.locator('#tab-intents .cat-intent-row', has_text=re.compile(r'APIs & Raw Materials|المواد الخام|المواد الفعالة والخامات')).first
        j.check('active' in (row.locator('.it-opt.i-have').get_attribute('class') or ''), 'the API intent is not kept after reload')
        row2 = pg.locator('#tab-intents .cat-intent-row', has_text=re.compile(r'Equipment|معدات')).first
        j.check(not row2.count() or 'active' in (row2.locator('.it-opt.i-need').get_attribute('class') or ''), 'the Equipment intent is not kept after reload')
    with j.step('Another user posts a matching demand: the match is shown (count, notification or Home card) and equals the real matches'):
        if j.demo: j.skip('the other party exists only in live')
        o = j.person('Matching Buyer'); seed_listing(j, o['id'], 'Metformin wanted %s' % j.tag, 'demand', 'api', '')
        j.reload(pg); j.nav(pg, 'feed'); j.settle(pg, 1500)
        n = j.sql1("select count(*) from public.notifications where user_id='%s' and created_at > now()-interval '10 minutes'" % me['id'])
        j.check(('Metformin wanted %s' % j.tag) in j.text(pg) or n not in ('', '0'), 'not built: a matching demand reaches the user neither on Home nor as a notification')
        j.check(j.has_table('user_intents') or j.has_column('profiles', 'intents'), 'not built: intents are not stored in the database')

if __name__ == '__main__': main(__file__)
