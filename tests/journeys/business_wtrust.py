"""Business journeys of the trust slice (area w-trust): who stands behind a trade offer — the trade profile before the first
offer (W-10), a company page posts as the company only with the Drugbox badge, everyone else as an individual (W-16), a broker
says so with the owner's authorisation and the commission (W-25), and after a delivered deal the supplier rates the buyer too
(W-19). Drugbox trade is business-to-business before the pharmacy.
Run: python3 tests/journeys/business_wtrust.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

def market(j, pg, tab='browse'):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200)
    t = pg.locator('.master-tab[data-tab=%s]:visible' % tab)
    j.check(t.count(), 'not built: the marketplace has no "%s" tab' % tab); t.first.click(); j.settle(pg, 800)

def fill_ph(j, pg, ph_re, val, root='#tab-create .form-section.active'):
    el = pg.evaluate_handle("([r,p])=>[...document.querySelectorAll(r+' input,'+r+' textarea')].find(e=>e.getClientRects().length&&new RegExp(p,'i').test(e.placeholder||''))||null", [root, ph_re]).as_element()
    if not el: j.notbuilt('no field "%s" in the listing form' % ph_re)
    el.fill(val); return el

def offer_form(j, pg, name, price='4.20', side='offer'):
    """Market → Create Listing → I'm Offering (or Seeking) → the product, a price and the MOQ."""
    market(j, pg, 'create')
    if not pg.locator('#bigOfferBtn:visible').count():
        ch = pg.locator('#tab-create :is(span,button,a):visible', has_text=re.compile(r'Change|تغيير')).first
        if ch.count(): ch.click(); pg.wait_for_timeout(500)
    pg.click('#bigOfferBtn' if side == 'offer' else '#bigSeekBtn'); pg.wait_for_timeout(600)
    if side == 'offer': fill_ph(j, pg, r'Metformin|product', name); fill_ph(j, pg, r'\$|price', price); fill_ph(j, pg, r'500 kg|MOQ', '200 kg')
    else: fill_ph(j, pg, r'Ciprofloxacin|looking', name); fill_ph(j, pg, r'MT/month|Quantity', '2 MT/month')

def posting_as(pg):
    return pg.evaluate("[...document.querySelectorAll('#tab-create .form-section.active .wt-as option')].map(o=>({v:o.value,t:o.textContent.trim(),off:o.disabled}))")

def choose_as(j, pg, value):
    s = pg.locator('#tab-create .form-section.active .wt-as:visible')
    j.check(s.count(), 'not built: the listing form has no "Posting as" choice'); s.first.select_option(value); pg.wait_for_timeout(200)

def preview_publish(j, pg, expect_profile=False, profile=None):
    """Preview Listing → (the trade profile window first, when it is asked) → Publish listing; returns the toasts."""
    mark = j.toast_mark(pg)
    b = pg.locator('#tab-create .form-section.active .btn-create:visible'); j.check(b.count(), "no 'Preview Listing'"); b.first.click(); pg.wait_for_timeout(700)
    t = dlg_text(pg)
    if expect_profile:
        j.check(re.search(r'trade profile|ملفك التجاري', t), 'the first trade offer does not ask for the trade profile first (dialog: "%s")' % t[:160])
    if re.search(r'First, your trade profile|أولاً: ملفك التجاري', t):
        dlg_click(j, pg, r'Add my trade profile|أضف ملفي التجاري', 'Add my trade profile'); fill_profile(j, pg, **(profile or {}))
    j.check(re.search(r'Preview your listing|معاينة', dlg_text(pg)), 'the listing preview did not open (dialog: "%s")' % dlg_text(pg)[:160])
    dlg_click(j, pg, r'Publish listing|انشر', 'Publish listing'); j.settle(pg, 1800)
    return j.toasts_since(pg, mark)

def fill_profile(j, pg, role='distributor', gov='Giza', sells='Excipients and APIs', buys='', company=None):
    j.check(pg.locator('#wtRole:visible').count(), 'not built: no trade profile form (role)')
    pg.select_option('#wtRole', role); pg.select_option('#wtGov', gov); pg.fill('#wtSells', sells); pg.fill('#wtBuys', buys)
    if company is not None: pg.fill('#wtCo', company)
    dlg_click(j, pg, r'Save trade profile|احفظ الملف التجاري', 'Save trade profile'); pg.wait_for_timeout(900)

def browse_card(j, pg, name):
    market(j, pg, 'browse')
    si = pg.locator('#searchIn:visible')
    if si.count(): si.first.fill(name); pg.wait_for_timeout(1200)
    c = pg.locator('#tab-browse :is(.lcard,.dcard)', has_text=name).first
    j.wait(pg, "n=>[...document.querySelectorAll('#tab-browse .lcard,#tab-browse .dcard')].some(c=>c.innerText.includes(n)&&c.querySelector('.wt-as-chip'))", 10, name)
    j.check(c.count(), 'the new offer "%s" is not in the marketplace' % name)
    return c

def chip(card): return card.locator('.wt-as-chip').first.inner_text().strip() if card.locator('.wt-as-chip').count() else ''

def trade_card_text(pg): return pg.evaluate("(document.querySelector('.wt-tcard')||{}).innerText||''")

@journey('J-BUSINESS-W10')
def trade_profile_first(j):
    """Before a member's first trade offer, Drugbox asks for a short trade profile (role, company, governorate, buys / sells) and shows it as a card."""
    name = 'Lactose monohydrate %s' % j.tag
    if j.live:
        a = j.person('Tarek Mansour'); pg = a['page']; b = j.person('Bassem Rizk')
    else: pg = j.demo_signin(j.new_page())
    with j.step('Market → Create Listing → I\'m Offering: Preview asks for the trade profile first'):
        offer_form(j, pg, name); choose_as(j, pg, 'individual')
        b0 = pg.locator('#tab-create .form-section.active .btn-create:visible'); b0.first.click(); pg.wait_for_timeout(700)
        t = dlg_text(pg); j.check(re.search(r'First, your trade profile|أولاً: ملفك التجاري', t), 'the first trade offer does not ask for the trade profile (dialog: "%s")' % t[:160])
        j.check(re.search(r'role, company, governorate|دورك وشركتك ومحافظتك', t), 'the window does not say what the trade profile holds')
    with j.step('Fill it (role, company, governorate, what I sell / buy) → the listing preview continues → Publish'):
        dlg_click(j, pg, r'Add my trade profile|أضف ملفي التجاري', 'Add my trade profile')
        opts = pg.evaluate("[...document.querySelectorAll('#wtRole option')].map(o=>o.value)")
        j.check('pharmacy' not in ' '.join(opts), 'a pharmacy is offered as a trading role (B2B before the pharmacy): %s' % opts)
        dlg_click(j, pg, r'Save trade profile|احفظ الملف التجاري', 'Save trade profile (empty)'); pg.wait_for_timeout(400)
        j.check(pg.locator('#wtRole:visible').count(), 'an empty trade profile was accepted')
        fill_profile(j, pg, role='distributor', gov='Giza', sells='Excipients and APIs', buys='Registration files', company='Nile Trade %s' % j.tag)
        j.check(re.search(r'Preview your listing|معاينة', dlg_text(pg)), 'after the trade profile the preview did not continue (dialog: "%s")' % dlg_text(pg)[:120])
        dlg_click(j, pg, r'Publish listing|انشر', 'Publish listing'); j.settle(pg, 1800)
        if j.live:
            row = j.wait_db("select role||'|'||governorate||'|'||coalesce(company,'') from public.trade_profiles where user_id='%s'" % a['id'], 10)
            j.check(row == 'distributor|Giza|Nile Trade %s' % j.tag, 'the trade profile in the database is "%s"' % row)
            p = j.wait_db("select posted_as from public.products where user_id='%s' and name=$q$%s$q$" % (a['id'], name), 10)
            j.check(p == 'individual', 'the offer was saved as "%s" (expected individual)' % p)
    with j.step('My profile shows the trade card (role, company, governorate, sells / buys) and "Member since"'):
        j.nav(pg, 'profile'); j.settle(pg, 1400)
        t = trade_card_text(pg)
        j.check(re.search(r'Distributor|موزع', t) and re.search(r'Giza|الجيزة', t) and 'Nile Trade %s' % j.tag in t, 'the trade card does not show the profile: "%s"' % t[:200])
        j.check(re.search(r'Excipients and APIs', t) and re.search(r'Registration files', t), 'the trade card does not say what I sell and buy')
        j.check(re.search(r'Member since|عضو منذ', j.text(pg)), 'the profile does not say "Member since"')
        j.check(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), 'the profile scrolls sideways with the trade card')
    with j.step('Edit the trade profile from the card → the change is kept (after a reload)'):
        j.click(pg, r'^\s*(Edit|تعديل)\s*$', scope='.wt-tcard', what='Edit trade profile')
        pg.fill('#wtBuys', 'Toll manufacturing capacity'); dlg_click(j, pg, r'Save trade profile|احفظ الملف التجاري', 'Save trade profile'); pg.wait_for_timeout(900)
        if j.live: j.check(j.wait_db("select buys from public.trade_profiles where user_id='%s'" % a['id'], 8, want='Toll manufacturing capacity'), 'the edit did not reach the database')
        j.reload(pg); j.nav(pg, 'profile'); j.settle(pg, 1400)
        j.check('Toll manufacturing capacity' in trade_card_text(pg), 'after a reload the trade card lost the edit: "%s"' % trade_card_text(pg)[:200])
    if j.demo: return
    with j.step('Another member opens my profile: the trade card, "Member since" and "New account" show; they cannot change my card'):
        pb = b['page']; j.nav(pb, 'feed'); pb.evaluate("u=>gotoProfile(dxLive.aid(u))", a['id']); j.settle(pb, 1800)
        t = trade_card_text(pb); j.check(re.search(r'Distributor|موزع', t) and 'Nile Trade %s' % j.tag in t, 'another member does not see my trade card: "%s"' % t[:200])
        line = pb.evaluate("(document.querySelector('.wt-line')||{}).innerText||''")
        j.check(re.search(r'Member since|عضو منذ', line) and re.search(r'New account|حساب جديد', line), 'the trust line does not show member since / new account: "%s"' % line)
        j.check(not pb.locator('.wt-tcard [data-wt=edit]').count(), 'another member sees Edit on my trade card')
        r = pb.evaluate("u=>dxLive.sb.from('trade_profiles').update({company:'Hacked'}).eq('user_id',u).select().then(r=>({n:(r.data||[]).length,e:r.error&&r.error.message}))", a['id'])
        j.check(r['n'] == 0, "another member changed my trade profile through the API: %s" % r)
        j.check(j.sql1("select company from public.trade_profiles where user_id='%s'" % a['id']) == 'Nile Trade %s' % j.tag, 'my trade profile changed')

@journey('J-BUSINESS-W16')
def verified_company_or_individual(j):
    """A company page posts trade offers as the company only with the Drugbox badge; members post as themselves; every card says which."""
    co_ok, co_new = 'Delta Excipients %s' % j.tag, 'Fresh Pharma %s' % j.tag
    n1, n2 = 'Microcrystalline cellulose %s' % j.tag, 'Povidone K30 %s' % j.tag
    if j.live:
        a = j.person('Sherif Galal'); pg = a['page']; ver = seed_company(j, a['id'], co_ok, sectors=('API & excipients',), status='verified'); j.reload(pg)
        b = j.person('Nadia Fawzy')
    else: pg = j.demo_signin(j.new_page()); co_ok = 'Quadra Pharm'
    with j.step('Create a second company page with the approved wizard (it is not verified yet)'):
        create_company(j, pg, co_new); wizard_details(j, pg, co_new, sector=r'Distribution|توزيع')
        dlg_click(j, pg, r'Next: review|التالي', 'Next: review'); dlg_click(j, pg, r'Create my page|أنشئ', 'Create my page'); j.settle(pg, 1500); close_dialogs(pg)
        if j.live: j.check(j.wait_db("select status from public.companies where name=$q$%s$q$" % co_new, 10) != 'verified', 'a new company page is verified at once')
    with j.step('"Posting as": myself, the verified company — the new page is shown but cannot be chosen ("needs the Drugbox badge")'):
        offer_form(j, pg, n1); o = posting_as(pg)
        j.check(any(x['v'] == 'individual' for x in o), 'no "Myself" in Posting as: %s' % o)
        ok = [x for x in o if co_ok in x['t']]; bad = [x for x in o if co_new in x['t']]
        j.check(ok and not ok[0]['off'], 'the verified company cannot be chosen: %s' % o)
        j.check(bad and bad[0]['off'] and re.search(r'needs the Drugbox badge|محتاجة شارة Drugbox', bad[0]['t']), 'the unverified page is not marked "needs the Drugbox badge" (or can be chosen): %s' % bad)
    if j.live:
        with j.step('The browser cannot post as the unverified company through the API either'):
            cid = j.sql1("select id from public.companies where name=$q$%s$q$" % co_new)
            r = pg.evaluate("([u,c])=>dxLive.sb.from('products').insert({user_id:u,name:'Sneaky offer',type:'supply',category:'api',company_id:+c,posted_as:'company'}).select('id').then(r=>r.error?r.error.message:'saved')", [a['id'], cid])
            j.check(r != 'saved' and re.search(r'verification badge', r), 'the API took an offer as an unverified company: %s' % r)
    with j.step('Publish as the verified company → its card says "✓ Verified company"'):
        choose_as(j, pg, [x['v'] for x in o if co_ok in x['t']][0])
        preview_publish(j, pg, profile={'company': co_ok})
        c = browse_card(j, pg, n1); j.check(re.search(r'Verified company|شركة موثّقة', chip(c)), 'the card of a verified company\'s offer says "%s"' % chip(c))
        if j.live: j.check(j.wait_db("select posted_as||'|'||company_id from public.products where name=$q$%s$q$" % n1, 10) == 'company|%s' % ver['id'], 'the offer is not saved as the verified company')
    with j.step('Publish another as myself → its card says "👤 Individual"'):
        offer_form(j, pg, n2, '2.10'); choose_as(j, pg, 'individual'); preview_publish(j, pg)
        c = browse_card(j, pg, n2); j.check(re.search(r'Individual|فرد', chip(c)), 'the card of a member\'s own offer says "%s"' % chip(c))
        if j.live: j.check(j.wait_db("select posted_as||'|'||coalesce(company_id::text,'none') from public.products where name=$q$%s$q$" % n2, 10) == 'individual|none', 'the offer is not saved as an individual')
    if j.demo: return
    with j.step('Another member sees both cards with the same labels'):
        pb = b['page']; c1 = browse_card(j, pb, n1); c2 = browse_card(j, pb, n2)
        j.check(re.search(r'Verified company|شركة موثّقة', chip(c1)) and re.search(r'Individual|فرد', chip(c2)), 'another member sees "%s" / "%s"' % (chip(c1), chip(c2)))

@journey('J-BUSINESS-W25')
def broker_offer(j):
    """A member who offers someone else's product or file says so: broker, the owner, the owner's authorisation and the commission."""
    name = 'Amoxicillin registration file %s' % j.tag
    if j.live: a = j.person('Hossam Wasit'); pg = a['page']; b = j.person('Mona Buyer')
    else: pg = j.demo_signin(j.new_page())
    with j.step('Create Listing → "Posting as: a broker for someone else" asks for the owner, the commission and the authorisation'):
        offer_form(j, pg, name, '15000'); choose_as(j, pg, 'broker')
        j.check(pg.locator('#tab-create .form-section.active .wt-broker:visible').count(), 'not built: choosing broker shows no broker fields')
    with j.step('Without the authorisation the offer is refused, saying why'):
        box = '#tab-create .form-section.active .wt-broker'
        pg.fill(box + ' .wt-bfor', 'Nile Pharma Industries'); pg.fill(box + ' .wt-bcom', '2.5')
        mark = j.toast_mark(pg); pg.locator('#tab-create .form-section.active .btn-create:visible').first.click(); pg.wait_for_timeout(900)
        if re.search(r'First, your trade profile|أولاً: ملفك التجاري', dlg_text(pg)):
            dlg_click(j, pg, r'Add my trade profile|أضف ملفي التجاري', 'Add my trade profile'); fill_profile(j, pg, role='consultant', gov='Cairo', sells='Registration files for licensing'); pg.wait_for_timeout(800)
        said = ' '.join(j.toasts_since(pg, mark))
        j.check(re.search(r'authorisation|تفويض', said) and not re.search(r'Preview your listing|معاينة', dlg_text(pg)), 'an offer without the owner\'s authorisation went on (toasts: %s)' % said[:160])
    with j.step('Attach the authorisation → Publish → the card says "🤝 Broker · 2.5% commission" and names the owner'):
        pg.set_input_files(box + ' .wt-bauth', PDF)
        preview_publish(j, pg, profile={'role': 'consultant', 'gov': 'Cairo', 'sells': 'Registration files for licensing'})
        c = browse_card(j, pg, name); t = c.inner_text()
        j.check(re.search(r'Broker · 2\.5% commission|وسيط · عمولة 2\.5%', t), 'the card does not say broker with the commission: "%s"' % t[:200])
        j.check('Nile Pharma Industries' in t, 'the card does not name the owner of the file')
        if j.live:
            row = j.wait_db("select posted_as||'|'||broker_for||'|'||broker_commission||'|'||coalesce(broker_auth_path,'') from public.products where name=$q$%s$q$" % name, 10)
            j.check(row and row.startswith('broker|Nile Pharma Industries|2.50|listings/%s/' % a['id']), 'the broker offer in the database: %s' % row)
            j.check(j.sql1("select count(*) from storage.objects where bucket_id='documents' and name='%s'" % row.split('|')[3]) == '1', 'the authorisation file is not in private storage')
            j.data['auth'] = row.split('|')[3]
    if j.demo: return
    with j.step('A buyer sees the same card and can open the authorisation; nobody can turn the broker offer into an individual one'):
        pb = b['page']; c = browse_card(j, pb, name); j.check(re.search(r'Broker|وسيط', chip(c)), 'the buyer sees "%s"' % chip(c))
        u = pb.evaluate("p=>dxLive.sb.storage.from('documents').createSignedUrl(p,60).then(r=>r.error?'ERR '+r.error.message:'ok')", j.data['auth'])
        j.check(u == 'ok', 'the buyer cannot open the owner\'s authorisation: %s' % u)
        r = pg.evaluate("n=>dxLive.sb.from('products').update({posted_as:'individual'}).eq('name',n).select('id').then(r=>r.error?r.error.message:'saved')", name)
        j.check(r != 'saved', 'the broker turned the offer into an individual one with the broker details kept: %s' % r)

@journey('J-BUSINESS-W19')
def rate_the_buyer(j):
    """After a delivered deal the supplier rates the buyer too (both sides rate each other — instead of public shaming)."""
    title = 'Rated order %s' % j.tag
    if j.live:
        buyer = j.person('Karim Buyer'); sup = j.person('Samy Supplier'); ps = sup['page']
        bco = seed_company(j, buyer['id'], 'Karim Distribution %s' % j.tag, sectors=('Distribution',)); sco = seed_company(j, sup['id'], 'Samy APIs %s' % j.tag, sectors=('API & excipients',))
        ref = j.sql1("insert into public.deals (type, title, from_company_id, from_user, to_company_id, status, lines) values ('quote', $q$%s$q$, %s, '%s', %s, 'delivered', '{\"qty\":\"100\",\"unit\":\"kg\"}') returning ref" % (title, bco['id'], buyer['id'], sco['id']))
        j.sql("insert into public.deal_events (deal_id, side, action, note) select id, 'to', 'ship', 'Shipped' from public.deals where ref='%s'" % ref)
        j.reload(ps)
    else:
        ps = j.demo_signin(j.new_page())
        # precondition: a received quote request moved to "delivered" through the deal engine's own steps (both sides)
        title = ps.evaluate("""()=>{const d=dxDeals.all().find(x=>x.type==='quote'&&x.status==='sent'&&dxDeals.sideOf(x)==='to');if(!d)return null;
          [['quote','to',{price:'US$ 4.10/kg',validity:'14 days'}],['accept','from',{}],['confirm','to',{}],['ship','to',{tracking:'AWB 1234'}],['receive','from',{ontime:'yes'}]].forEach(s=>dxDeals.act(d.id,s[0],s[2],s[1]));
          return dxDeals.get(d.id).status==='delivered'?d.title:null}""")
        j.check(title, 'the demo has no received quote request to deliver')
    with j.step('Open the delivered deal in Requests & deals (received) → "★ Rate the buyer"'):
        deals_centre(j, ps, r'Received|الواردة|المستلمة|وارد')
        j.click(ps, re.escape(title), scope='.dbk-ov', what='the deal'); ps.wait_for_timeout(900)
        btn = ps.locator('.dbk-ov [data-wtrate]:visible'); j.wait(ps, "!!document.querySelector('.dbk-ov [data-wtrate]')", 6)
        j.check(btn.count(), 'not built: the delivered deal has no "Rate the buyer" for the supplier (dialog: %s)' % dlg_text(ps)[:200])
    with j.step('Rate 4 stars with a comment → the window says it is rated; the buyer is told'):
        btn.first.click(); ps.wait_for_timeout(600); ps.select_option('#wtStars', '4'); ps.fill('#wtSnote', 'Paid on time, clear specs')
        dlg_click(j, ps, r'Send rating|ابعت التقييم', 'Send rating'); ps.wait_for_timeout(1200)
        j.check(re.search(r'You rated the buyer|قيّمت المشتري', ps.evaluate("document.body.innerText")), 'the deal does not say the buyer was rated')
        if j.live:
            j.check(j.wait_db("select stars from public.deal_ratings r join public.deals d on d.id=r.deal_id where d.ref='%s'" % ref, 8) == '4', 'no rating in the database')
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='deal_rated_buyer'" % buyer['id'], 8, want='1'), 'the buyer was not told')
    with j.step('Once only: the deal shows the rating instead of the button'):
        close_dialogs(ps); deals_centre(j, ps, r'Received|الواردة|المستلمة|وارد'); j.click(ps, re.escape(title), scope='.dbk-ov', what='the deal'); ps.wait_for_timeout(1200)
        j.check(not ps.locator('.dbk-ov [data-wtrate]').count() and ps.locator('.dbk-ov .wt-rated').count(), 'the deal offers "Rate the buyer" again')
        if j.live:
            r = ps.evaluate("r=>dxLive.sb.rpc('deal_rate_buyer',{p_ref:r,p_stars:1}).then(x=>x.error?x.error.message:'saved')", ref)
            j.check(r != 'saved', 'a second rating was saved through the API')
    if j.live:
        with j.step('The buyer cannot rate itself as a buyer'):
            pb = buyer['page']; j.reload(pb)
            r = pb.evaluate("r=>dxLive.sb.rpc('deal_rate_buyer',{p_ref:r,p_stars:5}).then(x=>x.error?x.error.message:'saved')", ref)
            j.check(r != 'saved', 'the buyer rated itself: %s' % r)

if __name__ == '__main__': main()
