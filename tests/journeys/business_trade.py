"""Business journeys — structured trade offers (W-trade: J-BUSINESS-W01 … W18): stock lines, price modes and «اسأل عن السعر»,
matching «عندي / محتاج», registration files, toll capacity, synonyms search, renew / duplicates / feature, reserved / sold with
rating, the ten templates, «الزق قايمتك», agency both ways, the file's trust (documents seen, private box, checklist).
Run: python3 tests/journeys/business_trade.py --target demo|live --lang en|ar --width 1440|390 --out DIR [--only J-BUSINESS-W01]"""
import re, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

KIND_PILL = {'stock': 'supply', 'materials': 'supply', 'wanted': 'demand', 'toll': 'cmo', 'file_sale': 'license'}
SEEK = ('wanted', 'file_wanted', 'distributor', 'toll_wanted')

def q(s): return "$q$%s$q$" % s

def market(j, pg, tab='browse'):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
    t = pg.locator('.master-tab[data-tab=%s]:visible' % tab)
    j.check(t.count(), 'not built: the marketplace has no "%s" tab' % tab); t.first.click(); j.settle(pg, 800)
    return pg.evaluate("t=>(document.querySelector('#tab-'+t)||{}).innerText||''", tab)

def trade_form(j, pg, kind):
    """Market → Create Listing → offering / seeking → the kind's pill (and the Supply form's mode) → the form's selector."""
    market(j, pg, 'create')
    if not pg.locator('#bigOfferBtn:visible').count():
        ch = pg.locator('#tab-create :is(span,button,a):visible', has_text=re.compile(r'Change|تغيير')).first
        if ch.count(): ch.click(); pg.wait_for_timeout(400)
    pg.click('#bigSeekBtn' if kind in SEEK else '#bigOfferBtn'); pg.wait_for_timeout(400)
    pill = KIND_PILL.get(kind, kind)
    p = pg.locator('#mkx .type-pill[data-type=%s]' % pill)
    j.check(p.count(), 'not built: no "%s" template in Create Listing' % kind)
    p.first.scroll_into_view_if_needed(); p.first.click(); pg.wait_for_timeout(300)
    f = '#form-%s' % pill
    j.check(pg.locator(f + ':visible').count(), 'the %s form does not open' % kind)
    if pill == 'supply':
        m = pg.locator(f + ' [data-tx=_mode] .radio-opt[data-v=%s]' % kind)
        j.check(m.count(), 'not built: the Supply form does not ask "%s"' % kind); m.click()
    return f

def tx_fill(pg, f, key, val):
    el = pg.locator('%s [data-tx="%s"] :is(input,select,textarea)' % (f, key)).first
    if el.evaluate('e=>e.tagName') == 'SELECT': el.select_option(val)
    else: el.fill(str(val))

def tx_chips(pg, f, key, *vals):
    for v in vals: pg.locator('%s [data-tx="%s"] .chip[data-v="%s"]' % (f, key, v)).first.click()

def tx_radio(pg, f, key, v): pg.locator('%s [data-tx="%s"] .radio-opt[data-v="%s"]' % (f, key, v)).first.click()

def approved(pg, f, ph, val):
    """An approved field of the form, by its original placeholder (the same in Arabic: i18n keeps it in data-i18n-placeholder)."""
    pg.locator('%s :is(input,textarea)[placeholder="%s"], %s :is(input,textarea)[data-i18n-placeholder="%s"]' % (f, ph, f, ph)).first.fill(val)

def title_field(pg, f, val):
    el = pg.locator('%s [data-tx="_title"] input' % f)
    (el.first if el.count() else pg.locator('%s .wizard-body .field-input' % f).first).fill(val)

def line_fill(pg, f, i, d):
    rows = pg.locator(f + ' .dx-line')
    while rows.count() <= i: pg.locator(f + ' [data-tx-a=addline]').click(); pg.wait_for_timeout(150)
    r = rows.nth(i)
    for k, v in d.items():
        el = r.locator('[data-l="%s"]' % k)
        t = el.evaluate('e=>e.tagName+":"+(e.type||"")')
        if t.startswith('SELECT'): el.select_option(v)
        elif t.endswith('checkbox'): (el.check() if v else el.uncheck())
        else: el.fill(str(v))

def publish(j, pg, f, publish_click=True):
    """'Preview Listing →' then 'Publish listing'; returns the toasts (waiting for the database's answer, up to 15 s). When the
    form refuses, returns them without a dialog."""
    pg.evaluate("window.__jt&&window.__jt.push('\u00a7')")   # the toast log skips a repeat of its last line: the same words again are a new notice
    mark = j.toast_mark(pg)
    b = pg.locator(f + ' .btn-create:visible'); j.check(b.count(), "no 'Preview Listing'"); b.first.scroll_into_view_if_needed(); b.first.click(); pg.wait_for_timeout(700)
    if not (dlg_open(pg) and publish_click): pg.wait_for_timeout(300); return [t for t in j.toasts_since(pg, mark) if t != '\u00a7']
    dlg_click(j, pg, r'Publish listing|انشر', 'Publish listing')
    for _ in range(60):
        pg.wait_for_timeout(250); said = [t for t in j.toasts_since(pg, mark) if t != '\u00a7']
        if any(re.search(r'live|اتنشر|منشور|match|مطابق|draft|مسودة|Please|كمّل', t) for t in said) or (dlg_open(pg) and re.search(r'already posted|منشور قبل', dlg_text(pg))): break
    j.settle(pg, 800)
    return [t for t in j.toasts_since(pg, mark) if t != '\u00a7']

def card(pg, title):
    return pg.locator('#tab-browse [data-trade-id]', has_text=title).first

def find_card(j, pg, title, timeout=10):
    market(j, pg)
    j.wait(pg, "t=>[...document.querySelectorAll('#tab-browse [data-trade-id]')].some(c=>c.innerText.includes(t))", timeout, title)
    c = card(pg, title); j.check(c.count(), 'the listing "%s" is not in Browse' % title); c.scroll_into_view_if_needed(); return c

def me_and(j, name, co=True, sector='Distribution'):
    if j.demo: return {'page': j.demo_signin(j.new_page())}
    if co: return live_company_person(j, name, '%s Co %s' % (name, j.tag), sectors=(sector,))
    return j.person(name)

def other(j, name, co=False, sector='API & excipients'):
    if j.demo: return None
    if co: return live_company_person(j, name, '%s Co %s' % (name, j.tag), sectors=(sector,))
    return j.person(name)

def as_member(j, uid, stmt):
    """Live: a statement as that member through the API role (the browser bypassed) — 'ok' or the database's refusal."""
    try: j.sql("begin; set local role authenticated; select set_config('request.jwt.claims', '{\"sub\":\"%s\",\"role\":\"authenticated\"}', true); %s; rollback;" % (uid, stmt)); return 'ok'
    except Exception as e: return str(e)

def lid(j, title): return j.wait_db("select id from public.products where name=%s order by id desc limit 1" % q(title), 8)

# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
@journey('J-BUSINESS-W01')
def stock_lines(j):
    """A distributor posts available stock («متوفر») as lines with name AR+EN, strength, quantity + unit, expiry, source + country, pack, fridge, governorate."""
    me = me_and(j, 'Stock Seller'); pg = me['page']; title = 'Cairo stock %s' % j.tag
    with j.step("Create Listing → Supply → 'Available stock': two items with every stock field, governorate, delivery, urgent, credit 60 days → Publish"):
        f = trade_form(j, pg, 'stock'); title_field(pg, f, title)
        line_fill(pg, f, 0, {'name': 'Panadol Extra', 'name_ar': 'بنادول اكسترا', 'strength': '500 mg', 'form': 'tab', 'qty': 120, 'unit': 'box', 'expiry': '2027-03', 'source': 'company', 'origin_country': 'EG', 'pack_state': 'intact'})
        line_fill(pg, f, 1, {'name': 'Insulin pen %s' % j.tag, 'strength': '100 iu', 'form': 'vial', 'qty': 25, 'unit': 'pack', 'expiry': '2026-12', 'source': 'importer', 'origin_country': 'DE', 'pack_state': 'intact', 'cold': True})
        tx_fill(pg, f, 'gov', 'giza'); tx_fill(pg, f, 'delivery', 'buyer'); tx_chips(pg, f, 'urgent', '1'); tx_fill(pg, f, 'credit_days', 60)
        said = publish(j, pg, f)
        j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), "no 'Your listing is live' (%s)" % said)
        if j.live:
            j.check(j.wait_db("select kind||'|'||status||'|'||(company_id is not null)::text from public.products where name=%s" % q(title), 8) == 'stock|active|true', 'the listing is not stored as an active stock listing of the company')
            j.check(j.sql1("select count(*) from public.listing_lines l join public.products p on p.id=l.listing_id where p.name=%s" % q(title)) == '2', 'the two items are not stored as lines')
            row = j.sql1("select l.name_ar||'|'||l.strength||'|'||l.qty::int||'|'||l.unit||'|'||to_char(l.expiry,'YYYY-MM')||'|'||l.source||'|'||l.origin_country||'|'||l.pack_state from public.listing_lines l join public.products p on p.id=l.listing_id where p.name=%s and l.pos=0" % q(title))
            j.check(row == 'بنادول اكسترا|500 mg|120|box|2027-03|company|EG|intact', 'the first line is not stored with its fields: %s' % row)
            j.check(j.sql1("select cold::text||source from public.listing_lines l join public.products p on p.id=l.listing_id where p.name=%s and l.pos=1" % q(title)) == 'trueimporter', 'the fridge item / importer is not stored')
            j.check(j.sql1("select (attrs->>'gov')||(attrs->>'delivery')||(attrs->>'urgent')||(attrs->>'credit_days') from public.products where name=%s" % q(title)) == 'giza' + 'buyer' + 'true' + '60', 'governorate / delivery / urgent / credit are not stored')
    with j.step("Another member sees the card: 'Available', the items with expiry, governorate, fridge, credit; '2 items' lists both with source, country and pack"):
        op = (other(j, 'Stock Buyer') or {'page': pg})['page']
        c = find_card(j, op, title); t = c.inner_text()
        j.check(re.search(r'Available|متوفر', t), "the card does not say 'Available' (%s)" % t[:120])
        j.check(re.search(r'2027-03', t) and re.search(r'Giza|الجيزة', t) and re.search(r'Fridge|ثلاجة', t) and re.search(r'60', t), 'the card does not show expiry, governorate, fridge and credit: %s' % t[:240].replace('\n', ' '))
        j.check(c.get_attribute('data-trade-kind') == 'stock' and c.get_attribute('data-trade-poster') in ('company', 'person'), 'the card has no trade hooks (data-trade-kind / data-trade-poster)')
        b = c.locator('[data-tx-c=items]'); j.check(b.count(), "no '2 items' on the card"); b.click(); pg.wait_for_timeout(300); op.wait_for_timeout(500)
        d = dlg_text(op)
        j.check('Insulin pen %s' % j.tag in d and re.search(r'Importer|مستورد', d) and 'DE' in d and re.search(r'Sealed|سليمة', d) and re.search(r'Fridge|ثلاجة', d), 'the items window does not list the lines with their fields: %s' % d[:300])
        ui_ok(j, op, 'the items window'); close_dialogs(op)
    with j.step('After a reload the listing and its items are still there'):
        if j.demo: j.demo_persists('the trade listings are kept in this browser')
        reopen(j, pg); c = find_card(j, pg, title); j.check('Panadol Extra' in c.inner_text(), 'the items are gone after the reload')

@journey('J-BUSINESS-W02')
def price_modes(j):
    """A seller prices by number, by discount % or «اطلب سعر»; a buyer asks the price of a listing and the seller receives it tied to the listing."""
    me = me_and(j, 'Price Seller'); pg = me['page']; t1, t2 = 'Discount stock %s' % j.tag, 'Ask stock %s' % j.tag
    with j.step("Publish one stock listing at 'Discount %' 28 and one at 'Ask for price'"):
        for title, mode in ((t1, 'discount'), (t2, 'ask')):
            f = trade_form(j, pg, 'stock'); title_field(pg, f, title)
            line_fill(pg, f, 0, {'name': 'Concor 5 mg %s' % title.split()[0], 'qty': 30, 'unit': 'box', 'expiry': '2027-01'})
            tx_radio(pg, f, 'price_mode', mode)
            if mode == 'discount': pg.locator(f + ' .dx-disc').fill('28')
            said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the %s listing was not published (%s)' % (mode, said))
        if j.live:
            j.check(j.wait_db("select price_mode||coalesce(discount_pct::text,'') from public.products where name=%s" % q(t1)) == 'discount28.00', 'the discount is not stored')
            j.check(j.wait_db("select price_mode from public.products where name=%s" % q(t2)) == 'ask', "'Ask for price' is not stored")
    with j.step("A buyer sees '28% off' and 'Ask for price' on the cards and asks the price of the second one with a quantity"):
        o = other(j, 'Price Buyer'); op = o['page'] if o else pg
        c1 = find_card(j, op, t1); j.check(re.search(r'28% off|خصم 28%', c1.inner_text()), "the card does not show '28%% off': %s" % c1.inner_text()[:160])
        c2 = card(op, t2); j.check(re.search(r'Ask for price|اسأل عن السعر', c2.locator('.price').inner_text()), "the card's price does not say 'Ask for price'")
        if j.demo: j.skip('the demo account owns these listings (asking needs a second member — live)')
        mark = j.toast_mark(op); c2.locator('[data-tx-c=ask]').click(); op.wait_for_timeout(500)
        j.check(dlg_open(op), "'Ask for price' opens no window"); op.locator('#dxAskQ').fill('50 box'); dlg_click(j, op, r'Send price request|ابعت طلب السعر'); j.settle(op, 1500)
        j.check(any(re.search(r'Messages|الرسايل|Requests', t) for t in j.toasts_since(op, mark)), 'no confirmation that the price request was sent')
        pid = lid(j, t2)
        j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s' and body like %s" % (o['id'], me['id'], q('Price request:%%listing #' + pid + '%%')), 8) == '1', 'the seller did not receive a message naming the listing')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='price_ask' and data->>'listing'='%s'" % (me['id'], pid)) == '1', "the seller has no 'price request' notice")
        j.check(j.sql1("select inquiry_count from public.products where id=%s" % pid) == '1', 'the inquiry is not counted on the listing')
    with j.step('The seller is told — the notice names the listing and opens the conversation'):
        if j.demo: j.skip('the asker and the seller are one account in the demo (live)')
        j.reload(pg); j.nav(pg, 'notifs'); j.settle(pg, 1500)
        it = pg.locator('.notif-item', has_text=re.compile(r'asked the price|price request|طلب السعر|سأل عن السعر')).first
        j.check(it.count(), 'the seller sees no price-request notice: %s' % j.text(pg)[:200]); it.click(); j.settle(pg, 1500)
        j.check(re.search(r'Price request|طلب سعر', j.text(pg)), 'the notice does not open the conversation with the request')
    with j.step('Company to company the price request is a quote request in Requests & deals, linked to the listing'):
        if j.demo: j.skip('two companies (live)')
        b2 = other(j, 'Price Company', co=True); bp = b2['page']; j.reload(bp)
        c = find_card(j, bp, t2); c.locator('[data-tx-c=ask]').click(); bp.wait_for_timeout(500); bp.locator('#dxAskQ').fill('80 box'); dlg_click(j, bp, r'Send price request|ابعت طلب السعر'); j.settle(bp, 1500)
        pid = lid(j, t2)
        j.check(j.wait_db("select status||'|'||type from public.deals where lines->>'listing_id'='%s' and from_company_id=%s" % (pid, b2['co']['id']), 8) == 'sent|quote', 'no quote request in the deals engine for the listing')

@journey('J-BUSINESS-W03')
def matching(j):
    """«عندي / محتاج»: a member who needs an item and one who offers it are told of each other (in the app and in the e-mail outbox), the match shows in My Listings, saved searches alert on canonical words."""
    a = me_and(j, 'Match Buyer', co=False); ap = a['page']; need = 'Augmentin 1 g needed %s' % j.tag
    if j.live:
        with j.step("A member posts 'Wanted' Augmentin 1 g"):
            f = trade_form(j, ap, 'wanted'); title_field(ap, f, need); approved(ap, f, '2 MT/month', '300 box')
            said = publish(j, ap, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the wanted listing was not published')
        b = other(j, 'Match Seller'); bp = b['page']; title = 'Weekly list %s' % j.tag
    else:
        b = a; bp = ap; title = 'Weekly list %s' % j.tag
    with j.step("Another member posts available stock with «اوجمنتين ١ جم» (Arabic, Arabic-Indic digits): told at once that a listing matches"):
        f = trade_form(j, bp, 'stock'); title_field(bp, f, title)
        line_fill(bp, f, 0, {'name': 'اوجمنتين ١ جم', 'qty': 40, 'unit': 'box', 'expiry': '2027-02'})
        said = publish(j, bp, f)
        j.check(any(re.search(r'match|مطابق', t) for t in said), 'the poster is not told that a listing matches: %s' % said)
        if j.live:
            s, w = lid(j, title), lid(j, need)
            j.check(j.wait_db("select count(*) from public.trade_matches where a=least(%s,%s) and b=greatest(%s,%s)" % (s, w, s, w), 8) == '1', 'the match is not recorded')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='trade_match' and data->>'listing'='%s'" % (a['id'], s), 8) == '1', 'the buyer has no match notice')
            j.check(j.wait_db("select count(*) from public.notification_outbox o join public.notifications n on n.id=o.notification_id where n.user_id='%s' and n.type='trade_match'" % a['id'], 8) != '0', 'the match notice is not queued for e-mail')
    with j.step("My Listings → 'Matches for your listings' shows the other listing; 'View' shows its card"):
        t = market(j, bp, 'manage'); j.wait(bp, "!!document.querySelector('#tab-manage .dx-trade-mine')", 8)
        j.check(re.search(r'Augmentin', bp.locator('#tab-manage .dx-trade-mine').inner_text()), 'My Listings does not show the match: %s' % bp.locator('#tab-manage .dx-trade-mine').inner_text()[:200])
        bp.locator('#tab-manage [data-tm]').first.click(); j.settle(bp, 800)
        j.check(bp.locator('#tab-browse [data-trade-id]:visible', has_text='Augmentin').count(), "'View' does not show the matching listing")
        ui_ok(j, bp, 'matches')
    with j.step('The buyer is notified in the app; the notice opens My Listings with the match'):
        if j.demo: j.skip('the other member is a sample person in the demo (live has both)')
        j.reload(ap); j.nav(ap, 'notifs'); j.settle(ap, 1500)
        it = ap.locator('.notif-item', has_text=re.compile(r'offer matches|مطابق|match')).first; j.check(it.count(), 'the buyer sees no match notice'); it.click(); j.settle(ap, 1800)
        j.check(re.search(r'Weekly list|' + j.tag, ap.locator('#tab-manage').inner_text()), 'the notice does not open the matches')
    with j.step("A saved search «بنادول» alerts its owner when a listing with 'Panadol' is published"):
        if j.demo: j.skip('saved-search alerts are sent by the database (live)')
        c = j.person('Search Saver'); j.sql("insert into public.saved_searches (user_id, kind, name, q, filters, alert) values ('%s','market','Panadol','بنادول','{}','instant')" % c['id'])
        f = trade_form(j, bp, 'stock'); t3 = 'Panadol list %s' % j.tag; title_field(bp, f, t3); line_fill(bp, f, 0, {'name': 'Panadol Extra', 'qty': 10, 'unit': 'box'}); publish(j, bp, f)
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='saved_search' and data->>'id'='%s'" % (c['id'], lid(j, t3)), 8) == '1', 'the saved search in Arabic is not alerted by an English listing')

@journey('J-BUSINESS-W04')
def file_listing(j):
    """A registration file listed with its structured fields (authority, stage checklist, decision, notification validity, public price, price increase, asking price, commission, included, buyer conditions, sales)."""
    me = me_and(j, 'File Owner', sector='Manufacturer'); pg = me['page']; title = 'Paracetamol 500 tablets file %s' % j.tag
    with j.step('Create Listing → License: every file field, the notification number in the private box → Publish'):
        f = trade_form(j, pg, 'file_sale'); approved(pg, f, 'e.g. EDA Cosmetic Registration — Anti-Acne Lotion', title)
        tx_fill(pg, f, 'reg_type', 'human'); tx_fill(pg, f, 'stage', 'notification'); tx_chips(pg, f, 'stages_done', 'submitted', 'pricing', 'committee')
        tx_fill(pg, f, 'form', 'Tablets'); tx_fill(pg, f, 'strength', '500 mg'); tx_radio(pg, f, 'decision', 'yes'); tx_fill(pg, f, 'notif_valid_until', '2027-06')
        tx_fill(pg, f, 'public_price', 34); tx_fill(pg, f, 'pack', '20 tablets'); tx_radio(pg, f, 'price_increase', 'submitted'); tx_fill(pg, f, 'asking_price', 'EGP 450,000')
        tx_fill(pg, f, 'commission', '2%'); tx_fill(pg, f, 'sales_units', 120000); tx_chips(pg, f, 'buyer_conditions', 'toll_ok'); tx_fill(pg, f, 'priv.notif_no', '7781/%s' % j.tag)
        said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the file was not published (%s)' % said)
        if j.live:
            a = j.wait_db("select (attrs->>'stage')||'|'||(attrs->>'price_increase')||'|'||(attrs->>'public_price')||'|'||(attrs->'stages_done')::text||'|'||kind from public.products where name=%s" % q(title), 8)
            j.check(a == 'notification|submitted|34|["submitted", "pricing", "committee"]|file_sale', 'the file fields are not stored: %s' % a)
            j.check(j.sql1("select notif_no from public.listing_private b join public.products p on p.id=b.listing_id where p.name=%s" % q(title)) == '7781/%s' % j.tag, 'the notification number is not in the private box')
            j.check(j.sql1("select count(*) from public.products where name=%s and (attrs::text like '%%7781%%' or description like '%%7781%%')" % q(title)) == '0', 'the notification number leaked into the public listing')
    with j.step("Another member sees 'Registration file', the stage and the price increase on the card; 'File details' shows every field"):
        o = other(j, 'File Buyer', co=True, sector='Manufacturer'); op = o['page'] if o else pg
        c = find_card(j, op, title); t = c.inner_text()
        j.check(re.search(r'Registration file|ملف تسجيل', t) and re.search(r'Notification issued|إخطار صادر', t) and re.search(r'34', t), 'the card does not show the kind, stage and public price: %s' % t[:200])
        c.locator('[data-tx-c=file]').click(); op.wait_for_timeout(500); d = dlg_text(op)
        for want in (r'EGP 450,000', r'Submitted \(not approved yet\)|مقدَّمة', r'2%', r'120000', r'Toll manufacturing accepted|تول مقبول', r'2027-06'):
            j.check(re.search(want, d), "'File details' does not show %s: %s" % (want, d[:300]))
        j.check(re.search(r'authority’s approval|موافقة الهيئة', d), 'the disclaimer is not shown')
        ui_ok(j, op, 'file details')
    with j.step('The notification number is private: another member cannot read it until the owner shares it'):
        if j.demo: j.skip('one account in the demo: the private box needs a second member (live)')
        op.locator('.dbk-ov [data-priv]').click(); op.wait_for_timeout(800)
        j.check(not re.search('7781', dlg_text(op)), 'another member read the notification number without it being shared')
        close_dialogs(op)
        c = find_card(j, op, title); c.locator('[data-tx-c=respond]').click(); op.wait_for_timeout(400); dlg_click(j, op, r'^\W*(Send|إرسال|ابعت)\W*$', 'Send'); j.settle(op, 1500)
        j.check(j.wait_db("select type||status from public.deals where lines->>'listing_id'=(select id::text from public.products where name=%s)" % q(title), 8) == 'dossierrequested', "'Request the file' did not open a file (dossier) request")
        t = market(j, pg, 'manage'); row = pg.locator('#tab-manage [data-ml]', has_text=title).first; row.locator('[data-ml-a=more]').click(); pg.wait_for_timeout(400)
        dlg_click(j, pg, r'Reserved / sold|محجوز / اتباع'); pg.wait_for_timeout(600)
        pg.locator('#dxSoldTo').select_option(label=re.compile('File Buyer')) if False else pg.evaluate("n=>{const s=document.querySelector('#dxSoldTo');const o=[...s.options].find(o=>o.text.includes(n));s.value=o?o.value:''}", 'File Buyer')
        dlg_click(j, pg, r'Share the private box|شارك الصندوق الخاص'); j.settle(pg, 1200)
        j.check(j.wait_db("select count(*) from public.listing_private_shares s join public.products p on p.id=s.listing_id where p.name=%s and s.user_id='%s'" % (q(title), o['id']), 8) == '1', 'the share is not recorded')
        c = find_card(j, op, title); c.locator('[data-tx-c=file]').click(); op.wait_for_timeout(400); op.locator('.dbk-ov [data-priv]').click(); op.wait_for_timeout(900)
        j.check('7781/%s' % j.tag in dlg_text(op), 'the member it was shared with cannot read the notification number')

@journey('J-BUSINESS-W05')
def toll_capacity(j):
    """A factory offers toll capacity with the required fields (forms, minimum batch, lead time, GMP with its date) — the form refuses it without them."""
    me = me_and(j, 'Toll Plant', sector='CMO / Toll'); pg = me['page']; title = 'Tablet line capacity %s' % j.tag
    with j.step('Create Listing → CMO with only a name: refused, naming the missing fields'):
        f = trade_form(j, pg, 'toll'); approved(pg, f, 'Contract Manufacturing — Tablets & Capsules', title)
        pg.evaluate("f=>document.querySelectorAll(f+' .chip.selected').forEach(c=>c.classList.remove('selected'))", f)   # the approved sample chips (Tablets, Capsules) are not this plant's choice
        said = publish(j, pg, f, publish_click=False)
        j.check(not dlg_open(pg), 'the preview opened without the required toll fields')
        j.check(any(re.search(r'Dosage forms|Minimum batch|Lead time|الأشكال|أقل تشغيلة|مدة التسليم', t) for t in said), 'the refusal does not name the missing fields: %s' % said)
    with j.step("GMP 'Yes' without who issued it and its date is refused too; with them it publishes"):
        tx_chips(pg, f, 'forms', 'tab', 'cap'); tx_chips(pg, f, 'packs', 'blister'); tx_fill(pg, f, 'min_batch', '150,000 tablets'); tx_fill(pg, f, 'lead_time', '6 weeks')
        tx_radio(pg, f, 'gmp', 'yes'); said = publish(j, pg, f, publish_click=False)
        j.check(not dlg_open(pg) and any(re.search(r'GMP', t) for t in said), 'GMP without issuer and date was accepted')
        tx_fill(pg, f, 'gmp_by', 'EDA'); tx_fill(pg, f, 'gmp_date', '2025-04'); tx_radio(pg, f, 'reg_contract', 'yes'); tx_radio(pg, f, 'licensed', 'yes')
        mo = pg.locator(f + ' [data-tx=free_months] .chip[data-v]').nth(2); mo.click(); fm = mo.get_attribute('data-v')
        said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the capacity was not published (%s)' % said)
        if j.live:
            a = j.wait_db("select (attrs->'forms')::text||'|'||(attrs->>'min_batch')||'|'||(attrs->>'lead_time')||'|'||(attrs->>'gmp_by')||(attrs->>'gmp_date')||'|'||(attrs->>'reg_contract')||'|'||(attrs->'free_months')::text from public.products where name=%s" % q(title), 8)
            j.check(a == '["tab", "cap"]|150,000 tablets|6 weeks|EDA2025-04|true|["%s"]' % fm, 'the toll fields are not stored: %s' % a)
            j.check(j.sql1("select kind||category||expires_at::date-created_at::date from public.products where name=%s" % q(title)) == 'tollcmo90', 'toll capacity is not kept 90 days under CMO')
    with j.step('Buyers see the forms, minimum batch, lead time, GMP and free months on the card under CMO'):
        o = other(j, 'Toll Buyer'); op = o['page'] if o else pg
        c = find_card(j, op, title); t = c.inner_text()
        j.check(re.search(r'Tablets|أقراص', t) and '150,000' in t and re.search(r'6 weeks', t) and 'EDA' in t and fm in t, 'the card does not show the toll fields: %s' % t[:240])
        j.check(c.get_attribute('data-cat') == 'cmo', 'the capacity is not under CMO')
    with j.step('The database refuses a toll listing without GMP even when the page is bypassed'):
        if j.demo: j.skip('the database rule (live)')
        err = as_member(j, me['id'], "insert into public.products (user_id, name, kind, attrs, status) values ('%s', 'Bypass toll', 'toll', '{\"forms\":[\"tab\"],\"min_batch\":\"1\",\"lead_time\":\"1\"}', 'active')" % me['id'])
        j.check(err != 'ok' and re.search(r'GMP', err), 'a toll listing without GMP was accepted by the database: %s' % err[:200])

@journey('J-BUSINESS-W06')
def synonyms_search(j):
    """Search finds the item whatever way it is written: Arabic ⇄ English names and forms, Arabic-Indic digits — on the server, beyond the first page."""
    me = me_and(j, 'Search Lister'); pg = me['page']; title = 'Glucophage list %s' % j.tag
    with j.step("A listing has 'Glucophage 850 mg tablets' (English) and «كونكور» (Arabic only)"):
        f = trade_form(j, pg, 'stock'); title_field(pg, f, title)
        line_fill(pg, f, 0, {'name': 'Glucophage', 'strength': '850 mg', 'form': 'tab', 'qty': 60, 'unit': 'box'})
        line_fill(pg, f, 1, {'name': 'كونكور %s' % j.tag, 'qty': 10, 'unit': 'box'})
        publish(j, pg, f)
        if j.live:   # 45 newer listings so it is beyond the first page the browser holds
            j.sql("insert into public.products (user_id, name, category, type, price, active) select '%s', 'Filler %s '||g, 'api', 'supply', '1', true from generate_series(1,45) g" % (me['id'], j.tag))
    o = other(j, 'Search Buyer'); op = o['page'] if o else pg
    for qy, why in (('جلوكوفاج', 'the Arabic name finds the English item'), ('٨٥٠', 'Arabic-Indic digits find 850'), ('اقراص جلوكوفاج', '«اقراص» finds tablets'), ('concor', 'the English name finds the Arabic item')):
        with j.step("Search «%s»: %s" % (qy, why)):
            market(j, op); si = op.locator('#searchIn'); si.fill(''); si.type(qy, delay=20); j.settle(op, 1800)
            j.wait(op, "t=>[...document.querySelectorAll('#tab-browse [data-trade-id]')].some(c=>c.innerText.includes(t)&&c.offsetParent)", 10, title)
            vis = op.evaluate("()=>[...document.querySelectorAll('#tab-browse .lcard,#tab-browse .dcard')].filter(c=>c.offsetParent).map(c=>(c.querySelector('.lc-title,.dc-title')||c).innerText)")
            j.check(any(title in v for v in vis), '%s: the listing is not found (%s)' % (why, vis[:5]))
            j.check(not any(('Filler %s' % j.tag) in v for v in vis), '%s: unrelated listings are shown too' % why)
    with j.step('Clearing the search shows every listing again'):
        op.locator('#searchIn').fill(''); op.evaluate("window.__mkxFilter('')"); j.settle(op, 1500)
        j.check(op.locator('#tab-browse .lcard:visible').count() > 1, 'clearing the search does not show the listings again')

@journey('J-BUSINESS-W07')
def renew_and_duplicates(j):
    """Posting the same offer again is refused — 'Renew that one' instead; renewing is free once a week (it moves the listing up); sooner, «ميّز إعلانك» opens the paid Boost with that listing."""
    me = me_and(j, 'Repeat Poster'); pg = me['page']; title = 'Daily list %s' % j.tag
    def post():
        f = trade_form(j, pg, 'stock'); title_field(pg, f, title); line_fill(pg, f, 0, {'name': 'Brufen 400 mg', 'qty': 70, 'unit': 'box', 'expiry': '2027-05'}); return publish(j, pg, f)
    with j.step('Publish a stock list'):
        said = post(); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the list was not published')
    with j.step("Publish the exact same list again: refused — 'You already posted this offer' with 'Renew that one'"):
        post(); j.wait(pg, "!!document.querySelector('.dbk-ov')", 8)
        j.check(re.search(r'already posted|منشور قبل', dlg_text(pg)), 'the duplicate was not refused: %s' % dlg_text(pg)[:160])
        if j.live: j.check(j.wait_db("select count(*) from public.products where name=%s" % q(title), 6) == '1', 'the duplicate is stored (two rows)')
    with j.step("'Renew that one' just after posting: free renewal once a week — the window offers '⭐ Feature this listing', which opens the Boost window with this listing chosen"):
        dlg_click(j, pg, r'Renew that one|جدّد القديم'); j.wait(pg, "!!document.querySelector('.dbk-ov')", 8)
        j.check(re.search(r'once every 7 days|this week|الأسبوع', dlg_text(pg)), 'the weekly limit is not explained: %s' % dlg_text(pg)[:200])
        dlg_click(j, pg, r'Feature this listing|ميّز إعلانك'); j.wait(pg, "document.getElementById('boostModalOverlay').classList.contains('show')", 8)
        if j.live:
            j.wait(pg, "!!document.getElementById('dxPayListing')&&document.getElementById('dxPayListing').options.length>0", 8)
            j.check(pg.evaluate("document.getElementById('dxPayListing').value") == lid(j, title), 'the Boost window does not choose this listing')
        pg.evaluate("document.getElementById('boostModalOverlay').classList.remove('show')")
    with j.step('A week later the free renewal works and moves it to the top'):
        if j.demo: j.skip('the demo cannot move the clock (live checks the database)')
        j.sql("update public.products set created_at=now()-interval '8 days', bumped_at=null, renewed_at=null where name=%s" % q(title))
        t = market(j, pg, 'manage'); row = pg.locator('#tab-manage [data-ml]', has_text=title).first; row.locator('[data-ml-a=more]').click(); pg.wait_for_timeout(400)
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Renew listing|جدد الإعلان|تجديد'); j.settle(pg, 1500)
        j.check(any(re.search(r'Renewed|اتجدّد', t) for t in j.toasts_since(pg, mark)), 'the renewal is not confirmed')
        j.check(j.wait_db("select (bumped_at > now()-interval '1 minute')::text from public.products where name=%s" % q(title), 6) == 'true', 'the renewal is not stored')

@journey('J-BUSINESS-W09')
def reserved_sold(j):
    """«محجوز / اتباع»: the owner reserves the listing (buyers see it, price requests stop), marks it sold to the member who asked, who confirms and rates; the owner rates back."""
    me = me_and(j, 'Sold Seller'); pg = me['page']; title = 'Weekly offer %s' % j.tag
    with j.step('Publish a stock list; a buyer asks its price'):
        f = trade_form(j, pg, 'stock'); title_field(pg, f, title); line_fill(pg, f, 0, {'name': 'Cataflam 50 mg', 'qty': 90, 'unit': 'box'}); publish(j, pg, f)
        o = other(j, 'Sold Buyer', co=True, sector='Distribution'); op = o['page'] if o else pg
        if j.live: c = find_card(j, op, title); c.locator('[data-tx-c=ask]').click(); op.wait_for_timeout(400); dlg_click(j, op, r'Send price request|ابعت طلب السعر'); j.settle(op, 1500)
    with j.step("My Listings → '···' → 'Reserved / sold' → 'Mark reserved': buyers see «Reserved» and cannot ask the price"):
        market(j, pg, 'manage'); row = pg.locator('#tab-manage [data-ml]', has_text=title).first; j.check(row.count(), 'the listing is not in My Listings')
        row.locator('[data-ml-a=more]').click(); pg.wait_for_timeout(400); dlg_click(j, pg, r'Reserved / sold|محجوز / اتباع'); pg.wait_for_timeout(600)
        dlg_click(j, pg, r'Mark reserved|علّمه محجوز'); j.settle(pg, 1500)
        if j.live: j.check(j.wait_db("select status from public.products where name=%s" % q(title), 6) == 'reserved', 'the reservation is not stored')
        if j.live: j.reload(op)
        c = find_card(j, op, title); j.check(c.locator('.dx-res').count() and re.search(r'Reserved|محجوز', c.locator('.dx-res').inner_text()), 'the card does not say Reserved')
        if j.live: j.check(c.locator('[data-tx-c=ask][disabled]').count(), "'Ask for price' is still open on a reserved listing")
    with j.step("'Mark sold' to the buyer who asked: the listing leaves Browse and the buyer is asked to confirm and rate"):
        market(j, pg, 'manage'); row = pg.locator('#tab-manage [data-ml]', has_text=title).first; row.locator('[data-ml-a=more]').click(); pg.wait_for_timeout(400)
        dlg_click(j, pg, r'Reserved / sold|محجوز / اتباع'); pg.wait_for_timeout(600)
        if j.live: pg.evaluate("n=>{const s=document.querySelector('#dxSoldTo');const o=[...s.options].find(o=>o.text.includes(n));s.value=o?o.value:''}", 'Sold Buyer')
        else: pg.locator('#dxSoldTo').select_option(index=1)
        dlg_click(j, pg, r'Mark sold|علّمه اتباع'); j.settle(pg, 1500)
        market(j, pg); j.check(not card(pg, title).count() or not card(pg, title).is_visible(), 'the sold listing is still in Browse')
        if j.live:
            j.check(j.wait_db("select status||closed_reason from public.products where name=%s" % q(title), 6) == 'closedsold', 'the sale is not stored')
            j.check(j.wait_db("select status from public.trade_outcomes where listing_name=%s" % q(title), 6) == 'pending', 'no sale record waiting for the buyer')
        t = market(j, pg, 'manage'); j.check(re.search(r'Waiting for confirmation|مستني التأكيد', pg.locator('#tab-manage .dx-trade-mine').inner_text()), 'My Listings does not show the sale waiting for confirmation')
    with j.step("The buyer confirms with 4★ — the sale counts for the two companies; the seller rates back"):
        if j.demo: j.skip('the buyer is a second member (live)')
        j.reload(op); t = market(j, op, 'manage'); j.wait(op, "!!document.querySelector('#tab-manage [data-oca=confirm]')", 8)
        op.locator('#tab-manage [data-oca=confirm]').first.click(); op.wait_for_timeout(500); op.locator('#dxStars').select_option('4'); dlg_click(j, op, r'Confirm and rate|أكّد وقيّم'); j.settle(op, 1500)
        j.check(j.wait_db("select status||counterpart_stars||(deal_id is not null)::text from public.trade_outcomes where listing_name=%s" % q(title), 8) == 'confirmed4true', 'the confirmation, stars or the recorded deal are missing')
        j.check(j.sql1("select d.status||(select count(*) from public.deal_events e where e.deal_id=d.id and e.action='rate') from public.deals d join public.trade_outcomes o on o.deal_id=d.id where o.listing_name=%s" % q(title)) == 'closed1', 'the sale is not a closed, rated deal')
        j.reload(pg); market(j, pg, 'manage'); j.wait(pg, "!!document.querySelector('#tab-manage [data-oca=rate]')", 8)
        pg.locator('#tab-manage [data-oca=rate]').first.click(); pg.wait_for_timeout(400); pg.locator('#dxStars').select_option('5'); dlg_click(j, pg, r'^\W*(Rate|قيّم)\W*$'); j.settle(pg, 1200)
        j.check(j.wait_db("select poster_stars from public.trade_outcomes where listing_name=%s" % q(title), 6) == '5', "the seller's rating is not stored")

@journey('J-BUSINESS-W13')
def templates(j):
    """The ten trade templates: from the Home composer's '🛒 Product' and on Create Listing — each opens its form and publishes its kind."""
    me = me_and(j, 'Template Poster', sector='Manufacturer'); pg = me['page']
    with j.step("Home → composer '🛒 Product' opens Create Listing with the ten trade templates; 'Company for sale' opens its form"):
        close_dialogs(pg); j.nav(pg, 'feed'); j.settle(pg, 1000)
        pr = pg.locator('.composer .comp-act:visible', has_text=re.compile(r'Product|منتج')).first; j.check(pr.count(), "no '🛒 Product' in the composer"); pr.click(); j.settle(pg, 1500)
        if not pg.locator('#step1Question:visible').count():
            ch = pg.locator('#tab-create :is(span,button,a):visible', has_text=re.compile(r'Change|تغيير')).first
            if ch.count(): ch.click(); pg.wait_for_timeout(400)
        b = pg.locator('#step1Question .dx-tpl-b:visible'); j.check(b.count() == 10, 'Create Listing does not offer the ten templates (%d)' % b.count())
        pg.locator('#step1Question [data-tx-tpl=company_sale]').click(); j.settle(pg, 1200)
        j.check(pg.locator('#form-company_sale:visible').count(), "the template does not open the 'Company for sale' form")
        ui_ok(j, pg, 'the company-for-sale form')
    for kind, title, fill in (('company_sale', 'Scientific office for sale %s' % j.tag, lambda f: (tx_fill(pg, f, 'company_type', 'scientific_office'), tx_fill(pg, f, 'files_count', 12))),
                              ('file_wanted', 'Wanted EDA file %s' % j.tag, lambda f: (tx_fill(pg, f, 'reg_type', 'human'), tx_fill(pg, f, 'form', 'Tablets'))),
                              ('toll_wanted', 'Factory wanted %s' % j.tag, lambda f: (tx_chips(pg, f, 'forms', 'syrup'), tx_fill(pg, f, 'batch', '50,000 bottles')))):
        with j.step("Template '%s': fill and publish" % kind):
            f = trade_form(j, pg, kind); title_field(pg, f, title); fill(f)
            said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the %s listing was not published (%s)' % (kind, said))
            if j.live: j.check(j.wait_db("select kind||'|'||type from public.products where name=%s" % q(title), 8) == '%s|%s' % (kind, 'demand' if kind in SEEK else 'supply'), 'the %s listing is not stored with its kind and side' % kind)
            c = find_card(j, pg, title); j.check(c.get_attribute('data-trade-kind') == kind, 'the card does not carry its kind')
    with j.step('Every template is reachable on Create Listing (offering and seeking)'):
        for k in ('stock', 'materials', 'wanted', 'file_sale', 'file_wanted', 'company_sale', 'agency', 'distributor', 'toll', 'toll_wanted'):
            trade_form(j, pg, k)

@journey('J-BUSINESS-W14')
def paste_list(j):
    """«الزق قايمتك»: a list copied from WhatsApp (chat header, Arabic-Indic digits, expiry, discount, fridge) becomes items to check, then a listing."""
    me = me_and(j, 'List Paster'); pg = me['page']; title = 'Pasted list %s' % j.tag
    txt = ('[12/10/2025, 10:15 PM] Ali Trader: متوفر\n'
           '1- بانادول اكسترا ٢٠ علبة exp 5/26 خصم 30%\n'
           'Concor 5mg 10 box ثلاجة\n'
           'اوجمنتين 1 جم 15 علبه تاريخ 03/2027 مستورد\n'
           'Brufen 400mg 25 strips\n'
           'للتواصل 0100000000')
    with j.step("Supply → 'Available stock' → '📋 Paste your list': the items are read (names, quantities, expiry, discount, fridge, importer) and the chat header is dropped"):
        f = trade_form(j, pg, 'stock'); title_field(pg, f, title)
        pg.locator(f + ' [data-tx-a=paste]').click(); pg.wait_for_timeout(400); pg.locator('#dxPaste').fill(txt)
        dlg_click(j, pg, r'Read the list|اقرا القايمة'); pg.wait_for_timeout(700); d = dlg_text(pg)
        j.check(re.search(r'4 items|4 صنف|4', d) and 'Ali Trader' not in d, 'the list is not read as 4 items without the header: %s' % d[:300])
        j.check(re.search(r'2026-05', d) and re.search(r'30%', d) and re.search(r'❄️', d), 'the expiry, discount or fridge mark are not read: %s' % d[:300])
    with j.step('Untick the last item, add the others, publish: the listing has those three items'):
        pg.locator('.dbk-ov [data-pr="3"]').uncheck(); pg.wait_for_timeout(600); dlg_click(j, pg, r'Add the items|ضيف الأصناف'); pg.wait_for_timeout(500)
        j.check(pg.locator(f + ' .dx-line').count() == 3, 'the three items are not in the form (%d)' % pg.locator(f + ' .dx-line').count())
        said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the pasted list was not published (%s)' % said)
        if j.live:
            rows = j.sql("select l.qty::int||'|'||coalesce(to_char(l.expiry,'YYYY-MM'),'')||'|'||coalesce(l.discount_pct::int::text,'')||'|'||l.cold::text||'|'||coalesce(l.source,'') from public.listing_lines l join public.products p on p.id=l.listing_id where p.name=%s order by l.pos" % q(title)).split('\n')
            j.check(rows == ['20|2026-05|30|false|', '10|||true|', '15|2027-03||false|importer'], 'the items are not stored as read: %s' % rows)
        c = find_card(j, pg, title); j.check(re.search(r'3 items|3 صنف', c.inner_text()), "the card does not say '3 items'")

@journey('J-BUSINESS-W15')
def agency_both_ways(j):
    """«فرصة وكالة» both ways: a product owner offers an agency by governorate, a distributor looks for products; they match, the distributor applies, they agree; the distributor's profile is on its company page."""
    a = me_and(j, 'Agency Owner', sector='Manufacturer'); ap = a['page']; ta = 'Vitamin range agency %s' % j.tag
    with j.step("Create Listing → 'Agency': categories, governorates on the map, exclusive, contract, bonus → Publish"):
        f = trade_form(j, ap, 'agency'); title_field(ap, f, ta); tx_chips(ap, f, 'cats', 'supplements'); tx_chips(ap, f, 'govs', 'asyut', 'sohag', 'qena')
        tx_radio(ap, f, 'exclusive', 'yes'); tx_fill(ap, f, 'contract_years', 3); tx_fill(ap, f, 'bonus_pct', 7)
        said = publish(j, ap, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the agency was not published (%s)' % said)
        if j.live: j.check(j.wait_db("select (attrs->'govs')::text||(attrs->>'bonus_pct')||(attrs->>'exclusive') from public.products where name=%s" % q(ta), 8) == '["asyut", "sohag", "qena"]7true', 'the agency fields are not stored')
    if j.demo:
        bp = ap; tb = None
    else:
        b = other(j, 'Upper Distributor', co=True, sector='Distribution'); bp = b['page']; tb = 'Upper Egypt distributor %s' % j.tag
    with j.step("A distributor posts 'Distributor seeking products' (supplements, Asyut): both are told of the match"):
        if j.demo: j.skip('the distributor is a sample in the demo (its listing is shown); live posts it')
        f = trade_form(j, bp, 'distributor'); title_field(bp, f, tb); tx_chips(bp, f, 'cats', 'supplements', 'medicines'); tx_chips(bp, f, 'govs', 'asyut', 'minya'); tx_fill(bp, f, 'warehouses', 2); tx_radio(bp, f, 'cold_chain', 'yes')
        said = publish(j, bp, f); j.check(any(re.search(r'match|مطابق', t) for t in said), 'the distributor is not told of the matching agency (%s)' % said)
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='trade_match'" % a['id'], 8) != '0', 'the agency owner is not notified')
    with j.step("The distributor 'Apply for the agency' → an agency request in Requests & deals"):
        c = find_card(j, bp, ta if j.live else 'Vitamin & supplement range'); c.locator('[data-tx-c=respond]').click(); bp.wait_for_timeout(400)
        bp.locator('#dxRspN').fill('We cover Upper Egypt with 2 warehouses'); mark = j.toast_mark(bp); dlg_click(j, bp, r'^\W*(Send|إرسال|ابعت)\W*$', 'Send'); j.settle(bp, 1500)
        j.check(any(re.search(r'Requests|الطلبات', t) for t in j.toasts_since(bp, mark)), 'no confirmation of the application')
        if j.live: j.check(j.wait_db("select type||status from public.deals where lines->>'listing_id'=(select id::text from public.products where name=%s)" % q(ta), 8) == 'agencyrequested', 'no agency request in the deals engine')
    with j.step("The owner opens it: 'Open talks' → 'Agree terms' → Agreed"):
        if j.demo: j.skip('the agency owner is a sample company in the demo')
        j.reload(ap); open_deal(j, ap, ta)
        deal_act(j, ap, r'^\W*(Open talks|ابدأ التفاوض)\W*$'); j.check(j.wait_db("select status from public.deals where lines->>'listing_id'=(select id::text from public.products where name=%s)" % q(ta), 8) == 'talks', 'the talks did not start')
        open_deal(j, ap, ta); deal_act(j, ap, 'Agree terms')
        j.check(j.wait_db("select status from public.deals where lines->>'listing_id'=(select id::text from public.products where name=%s)" % q(ta), 8) == 'agreed', 'the agency was not agreed')
    with j.step("The distributor's company page shows its distributor profile (governorates, categories, warehouses, cold chain)"):
        if j.live:
            directory(j, bp); open_card(j, bp, b['co']['name']); j.settle(bp, 1200)
            e = bp.locator('[data-dist-edit]'); j.check(e.count(), "no 'Edit distributor profile' on the distributor's own page"); e.click(); bp.wait_for_timeout(400)
            for v in ('asyut', 'minya', 'supplements'): bp.locator('#dxDistF .chip[data-v="%s"]' % v).click()
            bp.locator('#dxDistF [data-tx=warehouses] input').fill('2'); bp.locator('#dxDistF [data-tx=cold_chain] .radio-opt[data-v=yes]').click(); dlg_click(j, bp, r'^\W*(Save|حفظ)\W*$'); j.settle(bp, 1500)
            j.check(j.wait_db("select (select array_agg(x order by x) from unnest(govs) x)::text||cats::text||warehouses||cold_chain from public.distributor_profiles where company_id=%s" % b['co']['id'], 8) == '{asyut,minya}{supplements}2true', 'the distributor profile is not stored')
            op = j.person('Profile Viewer')['page']; directory(j, op); open_card(j, op, b['co']['name']); j.settle(op, 1500)
            j.wait(op, "!!document.querySelector('.dx-dist .cap-forms')", 10); t = op.locator('.dx-dist').text_content() if op.locator('.dx-dist').count() else ''
        else:
            directory(j, ap); open_card(j, ap, 'Pharaonic Cold-Chain Logistics'); j.settle(ap, 1500)
            j.wait(ap, "!!document.querySelector('.dx-dist .cap-forms')", 10); t = ap.locator('.dx-dist').text_content() if ap.locator('.dx-dist').count() else ''
        j.check(re.search(r'Distributor profile|بروفايل الموزّع', t, re.I) and re.search(r'warehouses|مخازن', t), 'the company page does not show the distributor profile: %s' % (ap if j.demo else op).evaluate("[...document.querySelectorAll('.dx-dist')].map(e=>e.outerHTML.slice(0,300)).join(' ## ')"))

@journey('J-BUSINESS-W18')
def file_trust(j):
    """Trust around a registration file: the documents go to Drugbox, who marks them seen («مستندات اتشافت» on the card, with the disclaimer); «اتفقنا» on a file deal needs the checklist."""
    me = me_and(j, 'Doc Owner', sector='Manufacturer'); pg = me['page']; title = 'Ibuprofen file docs %s' % j.tag
    with j.step('License form with the registration documents (2 files) → Publish: the documents wait for Drugbox'):
        f = trade_form(j, pg, 'file_sale'); approved(pg, f, 'e.g. EDA Cosmetic Registration — Anti-Acne Lotion', title)
        tx_fill(pg, f, 'reg_type', 'human'); tx_fill(pg, f, 'stage', 'final')
        z = pg.locator(f + ' .dx-docs'); j.check(z.count(), 'no upload for the documents')
        with pg.expect_file_chooser() as fc: z.click()
        fc.value.set_files([PDF, PNG]); pg.wait_for_timeout(400)
        said = publish(j, pg, f); j.check(any(re.search(r'live|اتنشر|منشور', t) for t in said), 'the file was not published (%s)' % said)
        if j.live: j.check(j.wait_db("select review_status||cardinality(doc_paths) from public.listing_private b join public.products p on p.id=b.listing_id where p.name=%s" % q(title), 10) == 'waiting2', 'the documents are not waiting for Drugbox')
    with j.step("Admin → Review → 'Trade documents' → 'Mark seen': the card shows «Documents seen by Drugbox» with the disclaimer"):
        if j.live: ad = j.person('Drugbox Checker'); make_admin(j, ad['id']); adp = ad['page']; j.reload(adp)
        else: adp = pg
        t = admin_review(j, adp, r'Trade documents|مستندات التجارة'); j.check(title in t or (j.demo and 'file' in t.lower()), 'the listing is not in the queue: %s' % t[:200])
        if j.demo: j.skip('the demo account is the owner (nobody checks their own listing) — live has a separate Drugbox checker')
        admin_decide(j, adp, title, ok=True)
        j.check(j.wait_db("select (docs_checked_at is not null)::text from public.products where name=%s" % q(title), 8) == 'true', 'the check is not stored')
        o = j.person('Doc Buyer'); c = find_card(j, o['page'], title)
        j.check(re.search(r'Documents seen by Drugbox|مستندات اتشافت', c.inner_text()), 'the card does not show «Documents seen by Drugbox»')
        j.check(re.search(r'approval|موافقة', c.locator('.dx-docs-seen').get_attribute('title') or ''), 'the badge has no disclaimer')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='document_reviewed' and data->>'listing' is not null" % me['id']) == '1', 'the owner is not told')
    with j.step("A file deal: «اتفقنا» (Agree terms) refuses until every checklist box is ticked; then it is agreed with the checklist kept"):
        if j.demo: j.skip('the file deal has two companies (live)')
        b = other(j, 'Checklist Buyer', co=True, sector='Manufacturer'); bp = b['page']
        c = find_card(j, bp, title); c.locator('[data-tx-c=respond]').click(); bp.wait_for_timeout(400); dlg_click(j, bp, r'^\W*(Send|إرسال|ابعت)\W*$', 'Send'); j.settle(bp, 1500)
        j.reload(pg); open_deal(j, pg, title); deal_act(j, pg, 'Sign NDA'); open_deal(j, pg, title); deal_act(j, pg, 'Share details', {r'Shared|مشترك|شارك': 'Data room: registration certificate %s' % j.tag})
        j.reload(bp); txt = open_deal(j, bp, title); j.check(re.search(r'Agree terms|وافق على الشروط', txt), 'the buyer cannot agree after the details were shared: %s' % txt[:400]); j.click(bp, r'Agree terms|وافق على الشروط', scope='body'); bp.wait_for_timeout(500)
        j.check(re.search(r'Before you agree|قبل الموافقة', dlg_text(bp)), 'no checklist before agreeing')
        mark = j.toast_mark(bp); dlg_click(j, bp, r'Agree terms|وافق على الشروط'); bp.wait_for_timeout(500)
        j.check(dlg_open(bp) and any(re.search(r'Tick every box|علّم على كل', t) for t in j.toasts_since(bp, mark)), 'agreeing without the checklist was not refused')
        bp.locator('.dbk-ov [data-ck]').evaluate_all("l=>l.forEach(c=>{if(!c.checked)c.click()})"); dlg_click(j, bp, r'Agree terms|وافق على الشروط'); j.settle(bp, 1800)
        j.check(j.wait_db("select d.status||(e.data->'checklist'->>'transfer_needs_approval') from public.deals d join public.deal_events e on e.deal_id=d.id and e.action='agree' where d.lines->>'listing_id'=(select id::text from public.products where name=%s)" % q(title), 8) == 'agreedtrue', 'the agreement and its checklist are not stored')

if __name__ == '__main__': main()
