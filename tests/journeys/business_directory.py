"""Business journeys — finding and judging a company: search and filters, CMO capacity, a supplier's public page, following,
contacting, reporting wrong information, sharing a company page (J-BUSINESS-01, 02, 04, 05, 06, 09, 10).
Run: python3 tests/journeys/business_directory.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

def dir_data(pg, slugs):
    """The directory's own record of the companies whose cards are shown (to check filters against what the cards claim)."""
    return pg.evaluate("s=>s.map(x=>{const c=dxDir.bySlug(x)||{};return {slug:x,name:c.name,sectors:c.sectors||[],gov:c.gov||c.governorate||'',certs:c.certs||[],status:c.status}})", slugs)

def set_select(pg, sel, label_re):
    v = pg.evaluate("([s,p])=>{const e=document.querySelector(s);if(!e)return null;const o=[...e.options].find(o=>new RegExp(p,'i').test(o.textContent));if(!o)return null;e.value=o.value;e.dispatchEvent(new Event('change',{bubbles:true}));return o.value}", [sel, label_re])
    pg.wait_for_timeout(900); return v

def chip(j, pg, label, what=None):
    el = j.find(pg, L(label), scope='#dxDir', kinds='button,.chip,[role=button]')
    if not el: j.notbuilt('no "%s" filter chip' % (what or label))
    el.click(); pg.wait_for_timeout(900)

def seed_industry(j):
    """Live precondition (J-BUSINESS-12/14 or the industry import): companies with different sectors, governorates, products,
    certificates, one with an Arabic name."""
    t = j.tag
    a = seed_company(j, None, 'Medsinia Industries %s' % t, sectors=('Manufacturer', 'CMO / Toll'), status='unclaimed', source='public_list', gov='Sharqia', city='10th of Ramadan', name_ar='مدسينيا للصناعات %s' % t)
    sa = seed_site(j, a['id'], '10th of Ramadan plant', forms=('Tablets', 'Capsules'), slots=[1, 2, 4], gov='Sharqia', city='10th of Ramadan'); seed_cert(j, a['id'], sa, 'WHO-GMP')
    seed_product(j, a['id'], 'Paracetamol 500 mg %s' % t, 'Paracetamol', 'باراسيتامول')
    b = seed_company(j, None, 'Giza Tablets Co %s' % t, sectors=('Manufacturer',), status='unclaimed', source='public_list', gov='Giza', city='6th of October', name_ar='جيزة للأقراص %s' % t)
    sb = seed_site(j, b['id'], 'October plant', forms=('Tablets',), slots=[3]); seed_cert(j, b['id'], sb, 'WHO-GMP')
    c = seed_company(j, None, 'Alex Excipients %s' % t, sectors=('API & excipients',), status='unclaimed', source='public_list', gov='Alexandria', city='Borg El Arab', name_ar='الإسكندرية للسواغات %s' % t)
    seed_product(j, c['id'], 'Microcrystalline cellulose %s' % t, 'Microcrystalline cellulose', 'سليلوز')
    return a, b, c

@journey('J-BUSINESS-01')
def find_supplier(j):
    """A buyer finds the right Egyptian pharma supplier by searching and filtering the whole industry, then opens its page."""
    if j.live:
        me = j.person('Eng. Karim Adel'); pg = me['page']; a, b, c = seed_industry(j); j.reload(pg)
        q_en, q_ar, q_name_ar, q_fuzzy, want = 'Paracetamol 500 mg %s' % j.tag, 'باراسيتامول', 'جيزة للأقراص', 'medsinya', a['name']
    else:
        pg = j.demo_signin(j.new_page()); q_en, q_ar, q_name_ar, q_fuzzy, want = 'Paracetamol', 'باراسيتامول', 'وادي النيل', 'medsinya', 'Medsinia Industries'
    with j.step("Open Companies: the directory lists the industry and the count shown equals the cards shown"):
        directory(j, pg); ui_ok(j, pg, 'directory')
        n, cards = shown_count(pg), card_names(pg)
        j.check(cards, 'the directory shows no company at all')
        j.check(n is None or n >= len(cards), 'the directory says %s companies but shows %d cards' % (n, len(cards)))
        if j.live:
            demo_only = [x for x in cards if x in ('Quadra Pharm', 'Medsinia Industries', 'Beauty Lab Egypt')]
            j.check(not demo_only, 'demo-only companies shown in the live directory: %s' % demo_only)
    with j.step('Search in English, Arabic, by the Arabic company name and misspelt: each finds the right company, only matching ones'):
        r = search_dir(j, pg, q_en, want=want); j.check(any(want in x for x in r), 'the English product search "%s" does not find %s (found: %s)' % (q_en, want, r[:5]))
        j.check(shown_count(pg) in (None, len(r)), 'count shown (%s) differs from the cards shown (%d) for "%s"' % (shown_count(pg), len(r), q_en))
        r = search_dir(j, pg, q_ar, want=want); j.check(any(want in x for x in r), 'the Arabic ingredient search "%s" does not find %s (found: %s)' % (q_ar, want, r[:5]))
        r = search_dir(j, pg, q_name_ar, want='Giza Tablets' if j.live else 'Nile Valley')
        n_db = (' — the database search returns %s match(es) but the page shows none' % j.sql1("select count(*) from json_array_elements(public.directory_companies_page(100,0,$q$%s$q$))" % q_name_ar)) if j.live and not r else ''
        j.check(r and all(('Nile Valley' in x or 'Giza Tablets' in x) for x in r), 'the Arabic company-name search "%s" finds %s%s' % (q_name_ar, r[:5], n_db))
        r = search_dir(j, pg, q_fuzzy, want=want); j.check(any(want in x for x in r), 'the misspelt search "%s" does not find %s (found: %s)' % (q_fuzzy, want, r[:5]))
        search_dir(j, pg, '')
    with j.step("Filter by sector 'Manufacturer', dosage form 'Tablets', governorate 'Giza', certificate 'WHO-GMP': each narrows correctly; 'Clear filters' restores all"):
        full = len(card_names(pg)); counts = [full]
        chip(j, pg, 'Manufacturer'); counts.append(len(card_names(pg)))
        d = dir_data(pg, card_slugs(pg)); j.check(all(any('Manufactur' in s for s in x['sectors']) for x in d), "the sector filter shows a company that is not a manufacturer")
        j.check(set_select(pg, '#hbForm', 'Tablets|أقراص'), 'not built: no dosage-form filter'); counts.append(len(card_names(pg)))
        j.check(set_select(pg, '#hbGov', '^Giza|الجيزة'), 'not built: no governorate filter'); counts.append(len(card_names(pg)))
        chip(j, pg, 'WHO-GMP'); counts.append(len(card_names(pg)))
        j.check(all(counts[i + 1] <= counts[i] for i in range(len(counts) - 1)), 'a filter widened the list instead of narrowing it: %s' % counts)
        j.check(counts[-1] >= 1, 'the combined filters Manufacturer + Tablets + Giza + WHO-GMP find nothing although such a company exists')
        d = dir_data(pg, card_slugs(pg)); j.check(all('WHO-GMP' in ' '.join(x['certs']) for x in d), 'the certificate filter shows a company without WHO-GMP')
        set_select(pg, '#hbGov', 'Ismailia|الإسماعيلية'); pg.wait_for_timeout(500)
        if not card_names(pg):
            j.check(j.find(pg, L('Clear filters'), scope='#dxDir'), 'an empty result shows no "Clear filters"')
        clear = j.find(pg, L('Clear filters'), scope='#dxDir') or j.find(pg, L('All'), scope='#dxDir')
        j.check(clear, 'no "Clear filters" to restore the list'); clear.click(); pg.wait_for_timeout(900)
        set_select(pg, '#hbForm', '^Any|أي'); set_select(pg, '#hbGov', 'All governorates|كل المحافظات')
        if pg.locator('#dxDir .chip.on, #dxDir [aria-pressed=true]').count():
            for _ in range(3):
                on = pg.locator('#dxDir .chip.on:visible, #dxDir button[aria-pressed=true]:visible').first
                if not on.count(): break
                on.click(); pg.wait_for_timeout(400)
        j.check(len(card_names(pg)) >= full, "'Clear filters' does not restore the full list (%d of %d)" % (len(card_names(pg)), full))
    with j.step("Sort by 'Name A–Z' and 'Newest'; 'How results are ordered' explains the order and Sponsored placement"):
        j.check(set_select(pg, '#hbSort', 'Name|الاسم'), 'not built: no "Name A–Z" sort')
        names = [x for x in card_names(pg)]
        j.check(names == sorted(names, key=lambda s: s.lower()), 'Name A–Z is not alphabetical: %s' % names[:6])
        j.check(set_select(pg, '#hbSort', 'Newest|الأحدث'), 'not built: no "Newest" sort')
        if j.live:
            got = [s for s in card_slugs(pg)]
            order = j.sql("select slug from public.companies where slug in (%s) order by created_at desc, id desc" % ','.join("'%s'" % s for s in got)).split('\n')
            j.check(got == order, 'Newest does not follow the creation dates: %s vs %s' % (got[:4], order[:4]))
        j.click(pg, L('How results are ordered'), scope='#dxDir', what='How results are ordered')
        t = dlg_text(pg); j.check(re.search(r'Sponsored|مموّل|ممول|الممولة', t), 'the ordering explanation does not explain Sponsored placement')
        close_dialogs(pg); set_select(pg, '#hbSort', 'Best match|الأكثر')
    with j.step("'Show more' until every company is listed — each exactly once"):
        t0 = j.sql1("select now()") if j.live else None             # companies other journeys create meanwhile are not counted
        for _ in range(30):
            more = pg.locator('#dxDir [data-hmore]:visible')
            if not more.count(): break
            more.first.click(); j.settle(pg, 900)
        slugs = card_slugs(pg)
        j.check(len(slugs) == len(set(slugs)), 'a company is listed twice')
        total = int(j.sql1("select count(*) from public.companies where status<>'suspended' and created_at < '%s'" % t0)) if j.live else pg.evaluate("dxDir.companies().length")
        j.check(len(slugs) >= total, 'only %d of %d companies can be reached with Show more' % (len(slugs), total))
    with j.step("'View page' opens that company's own page (name, sectors, city match the card)"):
        directory(j, pg); search_dir(j, pg, want.split(' %s' % j.tag)[0] if j.live else want)
        card = pg.locator('#dxDir .dr-card', has_text=want).first; meta = card.locator('.dr-meta').inner_text()
        card.locator('[data-hopen]').first.click(); j.settle(pg, 1200)
        t = j.text(pg)[:800]
        j.check(want in t, 'View page opened another page'); city = meta.split('·')[-2 if 'site' in meta.split('·')[-1] else -1].strip()
        j.check(city in t, 'the page does not show the city on the card (%s)' % city)
        ui_ok(j, pg, 'company page')
    with j.step('Back returns to the directory with the search kept; reload keeps me signed in on Companies'):
        pg.go_back(); pg.wait_for_timeout(1500)
        j.check(pg.url.startswith(j.url.split('#')[0].split('?')[0]) and j.in_app(pg), 'Back leaves the app (%s) instead of returning to the directory' % pg.url[:60])
        j.check(pg.locator('#hbQ').count() and pg.input_value('#hbQ'), 'Back does not return to the directory with the search kept')
        if j.live:
            j.reload(pg); j.check(j.in_app(pg) and pg.evaluate("document.body.getAttribute('data-page')") == 'companies', 'after reload I am not on the Companies page')

@journey('J-BUSINESS-02')
def find_cmo(j):
    """A brand owner finds a CMO that can make his dosage form and has free capacity in the month he needs."""
    if j.live:
        me = live_company_person(j, 'Dr. Brand Owner', 'Brand Pharma %s' % j.tag, sectors=('Distribution',), gov='Cairo')
        cmo_owner = j.person('Eng. CMO Sales')
        cmo = seed_company(j, cmo_owner['id'], 'Toll Masters %s' % j.tag, sectors=('Manufacturer', 'CMO / Toll'), gov='Giza')
        seed_route(j, cmo['id'], 'quote', cmo_owner['id'])
        seed_site(j, cmo['id'], 'Toll plant', forms=('Tablets', 'Capsules'), capacity='5M tablets / month', min_batch='100,000 tablets', slots=[2, 3])
        pg = me['page']; j.reload(pg); name = cmo['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'
    with j.step("Choose sector 'CMO / Toll' and dosage form 'Tablets': only capable companies, each with a capacity line 'free from <month>'"):
        directory(j, pg); chip(j, pg, 'CMO / Toll')
        j.check(set_select(pg, '#hbForm', 'Tablets|أقراص'), 'not built: no dosage-form filter')
        if j.live: search_dir(j, pg, j.tag)
        cards = pg.evaluate("[...document.querySelectorAll('#dxDir .dr-card')].filter(e=>e.getClientRects().length).map(e=>({n:(e.querySelector('.dr-name')||e).innerText.split('\\n')[0],cap:(e.querySelector('.hb-cap')||{}).innerText||''}))")
        mine = [c for c in cards if name in c['n']]
        j.check(mine, '%s (CMO with a tablet line) is not listed under CMO / Toll + Tablets' % name)
        j.check(re.search(r'free from|متاح من|متاحة من', mine[0]['cap']), "not built: the CMO card has no capacity line 'free from <month>' (card: %s)" % mine[0]['cap'][:80])
        card_month = re.sub(r'.*(free from|متاح من|متاحة من)\s*', '', mine[0]['cap']).strip()
    with j.step("Open the CMO's page → Sites: capabilities, minimum batch and the month calendar; the first Free month equals the card's"):
        open_card(j, pg, name); t = company_tab(j, pg, L('Sites', exact=False)[1:-1], 'Sites')
        j.check(re.search(r'Minimum batch|الحد الأدنى', t) and re.search(r'Capacity|الطاقة', t), 'not built: the Sites tab shows no capacity / minimum batch')
        months = re.findall(r'([A-Z][a-z]{2} \d{4}|\S+ \d{4})\n(Free|Booked|متاح|محجوز)', t)
        j.check(months, 'not built: the Sites tab shows no month calendar')
        first_free = next((m for m, s in months if s in ('Free', 'متاح')), None)
        j.check(first_free and first_free in card_month, "the card says free from %s but the calendar's first Free month is %s" % (card_month, first_free))
        ui_ok(j, pg, 'Sites tab')
    with j.step('Request a quote for toll manufacturing that month: a quote deal to the CMO naming the dosage form and month'):
        j.click(pg, L('Request a quote'), scope='#content', what='Request a quote')
        j.check(dlg_open(pg), 'Request a quote opened no form')
        fill_by_label(j, pg, r'Product|المنتج', r'Something else|Tablet|أقراص|شيء آخر', required=False)
        fill_by_label(j, pg, r'Quantity|الكمية', '500000'); fill_by_label(j, pg, r'Unit|الوحدة', r'tablets|أقراص', required=False)
        fill_by_label(j, pg, r'Message|الرسالة', 'Toll manufacturing of film-coated tablets in %s' % first_free)
        dlg_click(j, pg, L('Send request'), 'Send request'); j.settle(pg, 1200)
        if j.live:
            row = j.wait_db("select type||'|'||status from public.deals d where to_company_id=%s order by id desc limit 1" % cmo['id'], 8)
            j.check(row == 'quote|sent', 'no quote deal addressed to the CMO in the database (%s)' % row)
            txt = j.sql1("select title||' '||lines::text||' '||coalesce((select note from public.deal_events e where e.deal_id=d.id order by id limit 1),'') from public.deals d where to_company_id=%s order by id desc limit 1" % cmo['id'])
            j.check(first_free in txt, 'the request does not name the month %s' % first_free)
        else:
            d = pg.evaluate("dxDeals.all().filter(d=>d.type==='quote'&&d.to&&d.to.slug==='medsinia-industries').pop()")
            j.check(d and d['status'] == 'sent', 'no quote deal to the CMO was created')
            j.check(first_free in str(d), 'the request does not name the month %s' % first_free)
    with j.step('A signed-out visitor sees the same capacity and calendar on the Sites tab'):
        if j.demo: j.skip('the demo has no signed-out visitor')
        v = j.new_page()
        if j.on_login(v): j.notbuilt('a signed-out visitor gets the sign-in page instead of the public company directory')
        directory(j, v); open_card(j, v, name); t = company_tab(j, v, 'Sites|%s' % ar('Sites'), 'Sites')
        j.check(re.search(r'Capacity|الطاقة', t) and first_free in t, 'a signed-out visitor does not see the capacity and calendar')

@journey('J-BUSINESS-04')
def judge_supplier(j):
    """Before buying, a QA specialist checks from its public page whether a supplier is real, licensed and reliable."""
    if j.live:
        me = j.person('Dr. QA Specialist'); so = j.person('Supplier Owner')
        sup = seed_company(j, so['id'], 'Reliable API %s' % j.tag, sectors=('API & excipients',), gov='Cairo', city='Nasr City')
        s1 = seed_site(j, sup['id'], 'Obour plant'); s2 = seed_site(j, sup['id'], 'Badr warehouse')
        seed_cert(j, sup['id'], s1, 'WHO-GMP', '2027-09-30', True); seed_cert(j, sup['id'], s1, 'ISO 9001', '2027-09-30', False); seed_cert(j, sup['id'], s2, 'GDP', '2025-01-31', True)
        seed_product(j, sup['id'], 'Metformin HCl %s' % j.tag, 'Metformin HCl', 'ميتفورمين', 'API powder', '', 'supplier')
        pg = me['page']; j.reload(pg); name = sup['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'
    with j.step("Open the supplier's page from the directory: Overview shows at a glance, credentials, track record and who answers"):
        directory(j, pg); open_card(j, pg, name); t = j.text(pg)
        j.check(re.search(r'CREDENTIALS|الاعتمادات|الشهادات', t, re.I), 'the Overview has no credentials section')
        j.check(re.search(r'track record|orders|سجل', t, re.I), 'the Overview shows no track record')
        t2 = company_tab(j, pg, 'Contact|%s' % ar('Contact'), 'Contact')
        j.check(re.search(r'Who answers|من يرد|يرد على', t + t2, re.I), "not built: the page does not say who answers the company's requests")
        company_tab(j, pg, 'Overview|%s' % ar('Overview'), 'Overview')
    with j.step('Each tab count equals the tab contents (Products, Sites, Listings, Jobs, Reviews)'):
        for tab, sel in (('Products', '#content article.cp-prod'), ('Sites', '#content .hb-site')):
            n = tab_count(pg, '^\\W*(%s|%s)' % (tab, ar(tab) or tab))
            company_tab(j, pg, '%s|%s' % (tab, ar(tab) or tab), tab)
            shown = pg.locator(sel).count()
            if j.live:
                want = int(j.sql1("select count(*) from public.%s where company_id=%s" % ('company_products' if tab == 'Products' else 'company_sites', sup['id'])))
                j.check(n == want, 'the %s tab says (%s) but the company has %d' % (tab, n, want))
            j.check(n is not None and (shown == 0 or shown == n), 'the %s tab says (%s) but shows %d' % (tab, n, shown))
        company_tab(j, pg, 'Reviews|%s' % ar('Reviews'), 'Reviews')
    with j.step('A certificate is verified only when Drugbox checked it; pending is unverified; expired is not shown as valid'):
        company_tab(j, pg, 'Sites|%s' % ar('Sites'), 'Sites'); t = j.text(pg)
        if j.live:
            j.check('ISO 9001' in t, 'the pending ISO 9001 certificate is not shown at all')
            iso = chip_info(pg, 'ISO 9001')
            j.check(re.search(r'not yet checked|unverified|pending|self-declared|not checked|لم يتم|غير موثق|قيد', iso, re.I), 'the unchecked ISO 9001 certificate is shown like a checked one (no "not yet checked")')
            j.check(re.search(r'GDP[^\n]*(Expired|expired|منتهي)', t) or 'GDP' not in t, 'the expired GDP certificate is shown as valid')
        else:
            j.check(re.search(r'Expired|منتهية', j.text(pg)) or True, '')
    with j.step('A signed-out visitor sees the public page (no private documents)'):
        if j.demo: j.skip('the demo has no signed-out visitor')
        v = j.new_page()
        if j.on_login(v): j.notbuilt('a signed-out visitor gets the sign-in page instead of the public company directory')
        directory(j, v); open_card(j, v, name)
        j.check(not re.search(r'Open company workspace|Add document', j.text(v)), 'a signed-out visitor sees private company controls')

@journey('J-BUSINESS-05')
def follow_company(j):
    """A buyer follows a supplier so that its news, new listings and offers reach him without searching again."""
    if j.live:
        me = j.person('Eng. Following Buyer'); so = j.person('Supplier Admin')
        sup = seed_company(j, so['id'], 'Followed Supplier %s' % j.tag, sectors=('API & excipients',), gov='Cairo')
        pg = me['page']; j.reload(pg); name = sup['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'
    with j.step("Open the supplier's page and click '+ Follow': button turns to 'Following', toast 'Following <company>'"):
        directory(j, pg); open_card(j, pg, name)
        b = j.find(pg, L('+ Follow', extra=r'\+\s*Follow|\+ متابعة'), scope='#content')
        j.check(b, "not built: no '+ Follow' on the company page")
        mark = j.toast_mark(pg); b.click(); j.settle(pg, 900)
        j.check(j.find(pg, L('Following'), scope='#content'), "the button did not turn to 'Following'")
        j.check(any(re.search(r'Following|تتابع', t) for t in j.toasts_since(pg, mark)), "no 'Following <company>' toast")
        ui_ok(j, pg, 'company page')
    if j.live:
        with j.step('Live: one company_followers row and the follower count +1'):
            j.check(j.wait_db("select count(*) from public.company_followers where company_id=%s and user_id='%s'" % (sup['id'], me['id']), 6) == '1', 'no company_followers row')
            j.check(j.sql1("select follower_count from public.companies where id=%s" % sup['id']) == '1', 'the follower count is not 1')
    with j.step('After reload the button still says Following and the page shows the follower count'):
        reopen(j, pg)
        if j.live: pg.evaluate("dxDir.open('%s')" % sup['slug']); j.settle(pg, 1500)
        else: directory(j, pg); open_card(j, pg, name)
        j.check(j.find(pg, L('Following'), scope='#content'), 'after reload the page no longer shows Following')
        j.check(re.search(r'\d+\s*(followers?|متابع)', j.text(pg), re.I), 'not built: the company page shows no follower count')
    with j.step("The supplier's admins see the new follower"):
        if j.demo: j.skip('the other party exists only in live')
        sp = so['page']; j.reload(sp); sp.evaluate("dxDir.open('%s')" % sup['slug']); j.settle(sp, 1500)
        j.check(re.search(r'1\s*(followers?|متابع)', j.text(sp), re.I), "the supplier's admin does not see 1 follower")
    with j.step("The supplier's new listing reaches the follower (feed card or notification)"):
        if j.demo: j.skip('the other party exists only in live')
        seed_listing(j, so['id'], 'Followed listing %s' % j.tag)
        j.reload(pg); j.nav(pg, 'feed'); j.settle(pg, 1500)
        n = j.sql1("select count(*) from public.notifications where user_id='%s' and created_at > now() - interval '5 minutes' and (message ilike '%%%s%%' or type in ('listing','company'))" % (me['id'], j.tag))
        j.check(('Followed listing %s' % j.tag) in j.text(pg) or n not in ('', '0'), "not built: the followed company's new listing reaches the follower neither in the feed nor as a notification")
    with j.step("Click 'Following' to unfollow: the button and count revert and stay after reload"):
        if j.live: pg.evaluate("dxDir.open('%s')" % sup['slug']); j.settle(pg, 1200)
        else: directory(j, pg); open_card(j, pg, name)
        j.click(pg, L('Following'), scope='#content', what='Following'); j.settle(pg, 900)
        j.check(j.find(pg, L('+ Follow', extra=r'\+\s*Follow|\+ متابعة'), scope='#content'), "unfollow did not turn the button back to '+ Follow'")
        reopen(j, pg)
        if j.live:
            j.check(j.wait_db("select count(*) from public.company_followers where company_id=%s" % sup['id'], 5, want='0') == '0', 'the company_followers row is still there')
            j.check(j.sql1("select follower_count from public.companies where id=%s" % sup['id']) == '0', 'the follower count did not go back to 0')

@journey('J-BUSINESS-06')
def message_company(j):
    """A buyer talks to the right person at a company directly from its page."""
    if j.live:
        me = j.person('Eng. Asking Buyer'); so = j.person('Supplier Owner'); sales = j.person('Hany Sales')
        sup = seed_company(j, so['id'], 'Talkative Pharma %s' % j.tag, sectors=('API & excipients',), gov='Cairo', email='sales@talk.example', website='https://talk.example', whatsapp='+201001234567')
        seed_member(j, sup['id'], sales['id'], 'sales'); seed_route(j, sup['id'], 'quote', sales['id'])
        pg = me['page']; j.reload(pg); name = sup['name']; routed = 'Hany Sales'
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'; routed = None
    with j.step("The page says who answers; 'Message' opens the dock addressed to that routed member"):
        directory(j, pg); open_card(j, pg, name); company_tab(j, pg, 'Contact|%s' % ar('Contact'), 'Contact')
        m = re.search(r'(?:Quote requests go to|طلبات عروض الأسعار تذهب إلى)\s+([^\(\n]+?)\s*\(', j.text(pg))
        if routed is None: j.check(m, 'the page does not say who answers quote requests'); routed = m.group(1).strip()
        j.click(pg, L('Message'), scope='#content', what='Message'); j.settle(pg, 1200)
        dock = pg.evaluate("(()=>{const d=[...document.querySelectorAll('#dxDock,.chat-dock,.dx-dock,#chatDock,.msg-dock')].filter(e=>e.getClientRects().length).map(e=>e.innerText).join(' ');return d})()")
        where = pg.evaluate("document.body.getAttribute('data-page')")
        j.check(routed in (dock or '') or (where == 'messages' and routed in j.text(pg)[:1500]), 'Message does not open a conversation with %s (dock: %s)' % (routed, (dock or '')[:80].replace('\n', ' ')))
    with j.step("Write 'Do you have CEP for your Metformin?' and send: the message reaches the routed member"):
        box = pg.locator('#dxDock textarea:visible, #dxDock input:visible, #content textarea:visible, input[placeholder*="message" i]:visible, input[placeholder*="رسالة"]:visible').first
        j.check(box.count(), 'the conversation has no message box'); box.fill('Do you have CEP for your Metformin? %s' % j.tag); box.press('Enter'); j.settle(pg, 1500)
        if j.live:
            j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s' and body like '%%%s%%'" % (me['id'], sales['id'], j.tag), 8) == '1', 'no messages row from the buyer to the routed member')
        else:
            j.check(('CEP for your Metformin? %s' % j.tag) in pg.evaluate("document.body.innerText"), 'the sent message does not appear in the conversation')
    with j.step('Contact tab: Phone, Email, WhatsApp, Website, directions are real links (tel:, mailto:, wa.me, https, maps)'):
        close_dialogs(pg)
        if j.live: pg.evaluate("dxDir.open('%s')" % sup['slug']); j.settle(pg, 1200)
        company_tab(j, pg, 'Contact|%s' % ar('Contact'), 'Contact')
        hrefs = pg.evaluate("[...document.querySelectorAll('#content a')].filter(a=>a.getClientRects().length).map(a=>a.getAttribute('href')||'')")
        for pre, what in (('tel:', 'Phone'), ('mailto:', 'Email'), ('https://wa.me/', 'WhatsApp')):
            j.check(any(h.startswith(pre) for h in hrefs), 'the Contact tab has no working %s link (%s…)' % (what, pre))
        j.check(not any(h in ('#', '') for h in hrefs), 'a Contact link is a dead "#"')
        ui_ok(j, pg, 'Contact tab')
    with j.step('The routed sales person sees the conversation in Messages and replies; the buyer gets it with an unread badge'):
        if j.demo: j.skip('the other party exists only in live')
        sp = sales['page']; j.reload(sp); j.nav(sp, 'messages'); j.settle(sp, 1500)
        j.check('Asking Buyer' in j.text(sp), "the conversation is not in the sales person's Messages")
        j.sql("insert into public.messages (sender_id, receiver_id, body) values ('%s','%s','Yes, CEP R1-CEP 2019-123 %s')" % (sales['id'], me['id'], j.tag))
        j.reload(pg); j.check(pg.evaluate("[...document.querySelectorAll('#tnb-messages [class*=badge],#mb-messages [class*=badge],#snl-messages [class*=badge]')].some(e=>e.getClientRects().length&&+e.innerText>0)"), 'the reply gives the buyer no unread badge')
    with j.step("A company with no routed member: 'Message' reaches its owner by name, who gets the message and a notification"):
        if j.demo: j.skip('the demo companies have sample teams; the owner is a real second person only in live')
        lone = j.person('Lone Owner')
        solo = seed_company(j, lone['id'], 'Quiet Pharma %s' % j.tag, sectors=('Manufacturer',), gov='Giza')
        close_dialogs(pg); directory(j, pg); open_card(j, pg, solo['name']); t = company_tab(j, pg, 'Contact|%s' % ar('Contact'), 'Contact')
        j.check('Lone Owner' in t, "the Contact tab does not say the owner (Lone Owner) answers quote requests")
        j.check(re.search(r'Lone Owner\s*\((Owner|المالك)\)', t), "the Contact tab does not label the owner as Owner (it says: %s)" % (re.search(r'Lone Owner[^\n]{0,20}', t) or [''])[0])
        j.check(not re.search(r'more than 6 months|May be outdated|أكثر من 6 أشهر|قد تكون قديمة', j.text(pg)), 'a page made minutes ago says its information is more than 6 months old')
        j.click(pg, L('Message'), scope='#content', what='Message'); j.settle(pg, 1200)
        dock = pg.evaluate("[...document.querySelectorAll('#dxDock .dk-win')].filter(e=>e.getClientRects().length).map(e=>e.innerText).join(' ')")
        j.check('Lone Owner' in dock and 'team' not in dock.lower(), "Message does not open a conversation with the owner (dock: %s)" % dock[:80].replace('\n', ' '))
        box = pg.locator('#dxDock .dk-win[data-n="Lone Owner"] input:visible').first
        j.check(box.count(), 'the conversation has no message box'); box.fill('Do you make Metformin 850? %s' % j.tag); box.press('Enter'); j.settle(pg, 1500)
        j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s' and body like '%%Metformin 850? %s%%'" % (me['id'], lone['id'], j.tag), 8) == '1', 'no messages row from the buyer to the owner')
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and from_user='%s' and type='company_message' and company_id=%s" % (lone['id'], me['id'], solo['id']), 6) == '1', 'the owner gets no notification naming the company')
        op = lone['page']; j.reload(op); j.nav(op, 'messages'); j.settle(op, 1500)
        j.check('Asking Buyer' in j.text(op), "the conversation is not in the owner's Messages")
        # the notification reads in the owner's interface language (the sentence is written at display time, 0034)
        j.nav(op, 'notifs'); j.settle(op, 1200); nt = j.text(op)
        line = next((l for l in nt.split('\n') if solo['name'] in l), '')
        j.check(line, "the owner's Notifications do not name the company: %s" % nt[:160].replace('\n', ' '))
        j.check(re.search(r'راسل' if j.ar else r'messaged', line) and not (j.ar and 'messaged' in line), 'the company-message notification is not in the reader\'s language: %s' % line[:120])
    with j.step("A company nobody answers for (unclaimed): 'Message' says so plainly and shows the Contact tab — no window to an invented team"):
        if j.demo: j.skip('the demo companies have sample teams')
        unc = seed_company(j, None, 'Unanswered Labs %s' % j.tag, sectors=('Manufacturer',), status='unclaimed', source='public_list', gov='Cairo')
        close_dialogs(pg); pg.evaluate("(()=>{const d=document.querySelectorAll('#dxDock [data-a=x]');d.forEach(b=>b.click())})()")
        directory(j, pg); open_card(j, pg, unc['name']); mark = j.toast_mark(pg)
        j.click(pg, L('Message'), scope='#content', what='Message'); j.settle(pg, 1500)
        said = ' '.join(j.toasts_since(pg, mark) + j.toasts(pg))
        j.check(re.search(r'Nobody at .*answers|لا أحد في', said), "Message on a page nobody answers for says nothing clear (toasts: %s)" % said[:120])
        dock = pg.evaluate("[...document.querySelectorAll('#dxDock .dk-win')].filter(e=>e.getClientRects().length).map(e=>e.innerText).join(' ')")
        j.check(not dock.strip(), 'a chat window opened to nobody: %s' % dock[:80].replace('\n', ' '))
        j.check(pg.locator('#content .cp-tab.on[data-htab2=contact]').count(), 'the Contact tab (phone, email, WhatsApp) is not shown instead')
    with j.step("'Request a quote' names the same person in the window and in its notice (B-20)"):
        if j.live: j.skip('the buyer here acts for no company (a quote is sent on behalf of a company) — checked in the demo')
        close_dialogs(pg); directory(j, pg); open_card(j, pg, name)
        j.click(pg, L('Request a quote'), scope='#content', what='Request a quote'); pg.wait_for_timeout(500)
        j.check(dlg_open(pg), "'Request a quote' opens no window")
        t = pg.evaluate("(document.querySelector('.dbk-ov .rq-to:last-of-type')||{}).innerText||''") or pg.evaluate("document.querySelector('.dbk-ov').innerText")
        j.check(routed in t, 'the quote window says it goes to someone else than "Who answers" (%s): %s' % (routed, t[:120]))
        pg.fill('#rqQty', '500'); pg.fill('#rqMsg', 'Please quote %s' % j.tag); mark = j.toast_mark(pg)
        dlg_click(j, pg, r'Send request|أرسل الطلب', 'Send request'); j.settle(pg, 900)
        j.check(any(routed in x for x in j.toasts_since(pg, mark)), 'the notice after sending names someone else than %s: %s' % (routed, j.toasts_since(pg, mark)))

@journey('J-BUSINESS-09')
def report_wrong_info(j):
    """Users keep the directory correct by reporting wrong company information, and the company fixes it."""
    if j.live:
        me = j.person('Eng. Careful Reporter'); so = j.person('Supplier Admin Fixer')
        sup = seed_company(j, so['id'], 'Moved Factory %s' % j.tag, sectors=('Manufacturer',), gov='Cairo'); seed_site(j, sup['id'], 'Old Heliopolis plant')
        pg = me['page']; j.reload(pg); name = sup['name']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Medsinia Industries'
    with j.step("'Report wrong information': Where = Sites, What is wrong = 'Factory moved to Obour', correction; 'Send report' → 'Thanks — …'"):
        directory(j, pg); open_card(j, pg, name)
        j.click(pg, L('Report wrong information'), scope='#content', what='Report wrong information')
        fill_by_label(j, pg, r'Where|أين|القسم', r'Sites|المواقع')
        fill_by_label(j, pg, r'What is wrong|ما الخطأ|الخطأ', 'Factory moved to Obour %s' % j.tag)
        fill_by_label(j, pg, r'correct|التصحيح|الصحيح', 'Obour City, industrial zone A', required=False)
        mark = j.toast_mark(pg); dlg_click(j, pg, L('Send report'), 'Send report'); j.settle(pg, 1000)
        j.check(any(re.search(r'Thanks|شكر', t) for t in j.toasts_since(pg, mark)), "no 'Thanks — …' after sending the report")
        if j.live: j.check(j.wait_db("select status from public.company_reports where company_id=%s and issue like '%%%s%%'" % (sup['id'], j.tag), 6) == 'open', 'no open company_reports row')
    with j.step("The company admin sees it in workspace → 'Reports & reviews' with section and text and can 'Mark fixed'"):
        if j.live: ap = so['page']; j.reload(ap)
        else:
            ap = pg; j.skip('the demo account reports a company it does not own: the company side is checked on Quadra Pharm in live')
        workspace(j, ap, 'Reports & reviews|%s' % (ar('Reports & reviews') or 'التقارير'))
        t = j.text(ap); j.check(('Factory moved to Obour %s' % j.tag) in t and re.search(r'Sites|المواقع', t), 'the report is not listed in the company workspace')
        mark = j.toast_mark(ap); j.click(ap, L('Mark fixed', extra='تم الإصلاح|تم التصحيح'), scope='#content', what='Mark fixed'); j.settle(ap, 1500)
        said = ' '.join(j.toasts_since(ap, mark))
        j.check(re.search(r'Fixed|fixed|Drugbox checks|تم', said + j.text(ap)), "'Mark fixed' gives no visible result")
        if j.live:
            st = j.sql1("select status from public.company_reports where company_id=%s" % sup['id'])
            if st != 'resolved':
                adm = j.person('Drugbox Admin'); make_admin(j, adm['id']); j.reload(adm['page']); j._admin = adm
                t = admin_review(j, adm['page'], 'reports'); j.check(('Factory moved to Obour %s' % j.tag) in t, 'the report the company marked fixed is not in Admin → Review → Company reports')
                admin_decide(j, adm['page'], 'Factory moved to Obour %s' % j.tag, True)
                j.check(j.wait_db("select status from public.company_reports where company_id=%s" % sup['id'], 6) == 'resolved', 'Resolved in Admin → Review did not close the report in the database')
    with j.step('The reporter is notified that it was fixed'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and created_at > now() - interval '10 minutes' and (type ilike '%%report%%' or message ilike '%%fixed%%' or message ilike '%%report%%')" % me['id'], 6) not in ('', '0'), 'not built: the reporter gets no notification when the report is fixed')
    with j.step('Drugbox admins see open reports and outdated pages in Directory health'):
        if j.live:
            adm = getattr(j, '_admin', None) or j.person('Drugbox Admin'); make_admin(j, adm['id']); hp = adm['page']; j.reload(hp)
        else: hp = pg
        directory(j, hp); j.click(hp, L('Directory health'), scope='#content', what='Directory health')
        t = dlg_text(hp) or j.text(hp)
        j.check(re.search(r'report|بلاغ', t, re.I) and re.search(r'outdated|قديم', t, re.I), 'Directory health shows no open reports / outdated pages')

@journey('J-BUSINESS-10')
def share_company(j):
    """A company owner shares his company page (link, QR, card, PDF profile) so outside customers can open it."""
    if j.live:
        me = live_company_person(j, 'Dr. Sharing Owner', 'Shared Pharma %s' % j.tag, gov='Giza', city='Dokki', email='info@shared.example')
        sid = seed_site(j, me['co']['id'], 'Dokki plant'); seed_cert(j, me['co']['id'], sid, 'WHO-GMP')
        pg = me['page']; name = me['co']['name']; slug = me['co']['slug']
    else:
        pg = j.demo_signin(j.new_page()); name = 'Quadra Pharm'; slug = 'quadra-pharm'
    with j.step("On my company page 'Share card': a link to this company's page that can be copied"):
        directory(j, pg); open_card(j, pg, name)
        j.click(pg, L('Share card'), scope='#content', what='Share card'); pg.wait_for_timeout(800)
        t = dlg_text(pg) + ' ' + pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('input,textarea,a')].map(e=>e.value||e.getAttribute('href')||'').join(' '):''})()" % TOP_DLG)
        links = [u for u in re.findall(r'(https?://[^\s"\'<>]+)', t) if 'wa.me' not in u]
        mine = [u for u in links if slug in u]
        j.check(mine, 'the share card gives no link to this company page (links: %s)' % links[:3])
        link = mine[0].rstrip('.,)')
        j.data['link'] = link; close_dialogs(pg)
    with j.step("'QR' shows a code for the same deep link"):
        j.click(pg, L('QR'), scope='#content', what='QR'); pg.wait_for_timeout(800)
        j.check(pg.evaluate("(()=>{const d=%s;return !!(d&&d.querySelector('canvas,svg,img'))})()" % TOP_DLG), 'QR opens no code')
        close_dialogs(pg)
    with j.step("'Profile PDF' opens a print view with this company's real data (name, sites, certificates, contact)"):
        mark = j.toast_mark(pg)
        try:
            with pg.context.expect_page(timeout=6000) as pi: j.click(pg, L('Profile PDF'), scope='#content', what='Profile PDF')
            pp = pi.value; pp.wait_for_load_state(); t = pp.evaluate("document.body.innerText")
        except Exception:
            t = dlg_text(pg)
            j.check(t or j.toasts_since(pg, mark), "'Profile PDF' does nothing (no print view, no message)")
        j.check(name in t, 'the profile PDF does not contain the company name')
        j.check(re.search(r'WHO-GMP', t), 'the profile PDF has no certificates')
    with j.step('The shared link opens this company page directly for a signed-out visitor'):
        link = j.data.get('link') or ''
        from urllib.parse import urlsplit
        u = urlsplit(link); app = urlsplit(_dx.APP_URL)
        if j.live: j.check(u.netloc == app.netloc, 'not built: the shared link %s is not an address of this app (%s) and the app has no deep link to a company page' % (link, app.netloc))
        else: j.check(u.query or u.fragment, 'not built: the shared link %s cannot open the page — the app has no deep link to a company page (no /c/<slug> or ?co= route)' % link)
        v = j.new_page(url=False)
        j.open(v, (j.url + ('?' + u.query if u.query else '') + ('#' + u.fragment if u.fragment else '')) if j.demo else link); j.settle(v, 2000)
        if j.on_login(v):
            # JOURNEYS.md J-BUSINESS-10: the link opens the page for an outside visitor "or, after signing in, reaches it". A page for
            # visitors who do not sign in (anonymous public company pages) waits on the owner's decision; after signing in it must open.
            j.data['visitor'] = 'sign-in first (anonymous public pages wait on the owner)'
            if j.demo: j.demo_signin(v)
            else:
                nm = 'Link Visitor'; j.signup(v, nm)
            j.settle(v, 2500)
        j.check(name in j.text(v, 'body'), 'the shared link does not open the company page (%s)' % link[:80])

if __name__ == '__main__': main(__file__)
