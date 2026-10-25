"""Business journeys of the growth plan (AREA w-growth): the therapeutic filter in the Marketplace (W-21), founding members (W-42),
the directory import from public lists with claims (B-01 extended) and company pages for signed-out visitors (the owner's decision 1).
J-BUSINESS-W01 … W04 (docs/JOURNEYS.md)."""
import re, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main
from _biz import *
import _dx
from _growth import staff, admin_tab, create_listing, market, cards as mk_cards

def T(j, en, ar_): return ar_ if j.ar else en

def mk_area(j, pg, v):
    """Choose a therapeutic area in the Marketplace filters (on a phone the filters open from their '⚙ Filters' button first)."""
    if not pg.locator('#dxThMk').first.is_visible() and pg.locator('.mkx-ftoggle:visible').count(): pg.locator('.mkx-ftoggle').first.click(); pg.wait_for_timeout(400)
    pg.select_option('#dxThMk', v); j.settle(pg, 1800)

@journey('J-BUSINESS-W01')
def market_therapeutic_filter(j):
    """A buyer narrows the Marketplace to one therapeutic area (insulin, oncology …): the server answers for every listing."""
    name = 'Insulin glargine pens %s' % j.tag
    if j.live:
        me = live_company_person(j, 'Insulin Supplier', 'Insulin Supplier Co %s' % j.tag, sectors=('Distribution',)); pg = me['page']
        seed_listing(j, me['id'], name, 'supply', 'finished', '4.20')
        seed_listing(j, me['id'], 'Paracetamol DC %s' % j.tag, 'supply', 'api', '3.10')
        b = j.person('Hospital-tender Buyer'); bp = b['page']
    else:
        pg = j.demo_signin(j.new_page()); bp = pg
    with j.step('A supplier lists insulin pens: the listing is tagged insulin by its words'):
        if j.demo: create_listing(j, pg, 'offer', [(r'Metformin|product', name), (r'\$|price', '4.20'), (r'500 kg|MOQ', '1,000 pens')])
        else: j.check(j.sql1("select thera::text from public.products where name=$q$%s$q$" % name) == '{insulin}', 'the listing is not tagged insulin in the database')
    with j.step('Browse Marketplace has a "Therapeutic area" filter'):
        market(j, bp); j.check(bp.locator('#dxThMk').count(), 'not built: the Marketplace has no therapeutic-area filter')
        ui_ok(j, bp, 'Marketplace with the filter')
    with j.step('Insulin: the insulin listing shows, the paracetamol one does not'):
        mk_area(j, bp, 'insulin')
        vis = [c for c in mk_cards(bp)]
        j.check(any(name in c['txt'] for c in vis), 'the insulin listing is not shown under Insulin')
        j.check(not any(('Paracetamol DC %s' % j.tag) in c['txt'] for c in vis), 'the paracetamol listing shows under Insulin')
    with j.step('Oncology: nothing about it — the page says so; All areas brings the listings back'):
        mk_area(j, bp, 'oncology')
        j.check(not any(name in c['txt'] for c in mk_cards(bp)), 'the insulin listing shows under Oncology')
        if not mk_cards(bp): j.check(re.search(T(j, r'No listings about', r'لا توجد إعلانات'), j.text(bp)), 'an empty result says nothing')
        mk_area(j, bp, '')
        j.check(any(name in c['txt'] for c in mk_cards(bp)), 'the listings did not come back')
        if j.live:
            err = bp.evaluate("async()=>{const r=await dxLive.sb.rpc('market_search_thera',{p_tag:'pharmacy'});return r.error?(r.error.code||'err'):'allowed'}")
            j.check(err == '22023', 'an unknown area was accepted (%s)' % err)

@journey('J-BUSINESS-W02')
def founding_members(j):
    """Drugbox invites founding members by segment (no pharmacy segment); the invitee joins by their own choice and gets the badge and 3 VIP months."""
    if j.live:
        adm = staff(j); ap = adm['page']
        fo = live_company_person(j, 'Eng. Founding Distributor', 'Founding Distribution %s' % j.tag, sectors=('Distribution',)); fp = fo['page']
        x = j.person('Other Member'); xp = x['page']
    else:
        ap = fp = xp = j.demo_signin(j.new_page()); fo = None
    def open_link(p, code):
        p.goto(j.url + '#/founder/' + code, wait_until='load')
        try: p.evaluate('endSplash()')
        except Exception: pass
        if j.demo: j.demo_signin(p) if j.on_login(p) else None
        j.settle(p, 2500)
    with j.step('Admin → Founders: the segments with their quotas — no pharmacy / Rx segment'):
        admin_tab(j, ap, 'founders', 'Founders'); t = j.text(ap, '#adminContent')
        j.check(ap.locator('#adminContent .dx-fnd-card').count() == 8, 'the founders page does not list the 8 segments')
        j.check(not re.search(r'pharmac|Rx|صيدل', t, re.I), 'a pharmacy / Rx segment is offered')
        ui_ok(j, ap, 'Admin → Founders')
    with j.step('Make room in "Distributors / warehouses" (quota) and make an invitation: the code shows once'):
        c = ap.locator('#adminContent .dx-fnd-card[data-seg="distributor"]'); used = [int(n) for n in re.findall(r'\d+', c.inner_text())[:2]]
        c.locator('.dx-fnd-quota').click(); j.settle(ap, 500); ap.fill('#fnQ', str(sum(used) + 3)); dlg_click(j, ap, T(j, r'^\W*Save\W*$', r'^\W*حفظ\W*$'), 'Save'); j.settle(ap, 1000)
        ap.locator('.dx-fnd-new').click(); j.settle(ap, 500); ap.select_option('#fnS', 'distributor'); ap.fill('#fnN', 'Founding distributor %s' % j.tag)
        dlg_click(j, ap, T(j, r'Make invitation', r'إنشاء الدعوة'), 'Make invitation'); j.settle(ap, 1200)
        code = ap.evaluate("(document.querySelector('.dx-fnd-code')||{}).innerText||''").strip()
        j.check(re.match(r'^DBX-[0-9A-Z]{4}(-[0-9A-Z]{4}){4}$', code), 'no invitation code shown (%s)' % code)
        if j.live:
            row = j.sql1("select code_hint||'|'||segment from public.founder_invites where note like '%%%s'" % j.tag)
            j.check(row == code.replace('-', '')[-4:] + '|distributor', 'the invitation is not stored for the segment (%s)' % row)
            j.check(j.sql1("select count(*) from public.founder_invites where position('%s' in encode(code_hash,'escape'))>0" % code.replace('-', '')[4:]) == '0', 'the code itself is stored')
        dlg_click(j, ap, T(j, r'^\W*Done\W*$', r'^\W*تم\W*$'), 'Done')
    with j.step('The invitee opens the link: the invitation says what it is; they choose to join and give the VIP months to their company'):
        open_link(fp, code)
        j.check(dlg_open(fp) and re.search(T(j, r'founding member', r'عضوًا مؤسسًا|عضو مؤسس'), dlg_text(fp)), 'the invitation link offers nothing to the invitee')
        j.check(re.search(T(j, r'Distributors', r'الموزعون'), dlg_text(fp)), 'the invitation does not name the segment')
        sel = fp.locator('#fnCo')
        if sel.count():
            opts = sel.evaluate("s=>[...s.options].map(o=>o.value).filter(Boolean)"); j.check(opts, 'the invitee is offered no company of theirs for the VIP months')
            sel.select_option(opts[0])
        dlg_click(j, fp, T(j, r'Join as a founding member', r'انضم كعضو مؤسس'), 'Join'); j.settle(fp, 1500)
        if j.live:
            j.check(j.wait_db("select segment from public.founder_members where user_id='%s'" % fo['id'], 6) == 'distributor', 'no founder_members row')
            j.check(j.sql1("select (plan='vip' and vip_until between now()+interval '85 days' and now()+interval '95 days')::text from public.companies where id=%s" % fo['co']['id']) == 'true', 'the company did not get 3 months of VIP')
    with j.step('The founder badge shows on the founder’s profile (to others too)'):
        if j.live:
            from _social import goto_profile
            j.reload(xp); goto_profile(j, xp, fo)
        else: j.nav(xp, 'profile')
        j.wait(xp, "!!document.querySelector('#content .dx-fnd-badge')", 8)
        j.check(re.search(T(j, r'Founding member', r'عضو مؤسس'), j.text(xp, '#content .profile-name')), 'no founder badge on the profile')
        ui_ok(j, xp, 'profile with the badge')
    with j.step('The same code cannot be used again'):
        open_link(xp, code)
        j.check(dlg_open(xp) and re.search(T(j, r'already', r'من قبل|بالفعل'), dlg_text(xp)), 'reusing a used code is not refused')
        if j.live: j.check(j.sql1("select count(*) from public.founder_members where user_id='%s'" % x['id']) == '0', 'the other member became a founder with a used code')
        close_dialogs(xp)
    with j.step('A revoked invitation stops working'):
        admin_tab(j, ap, 'founders', 'Founders')
        ap.locator('.dx-fnd-new').click(); j.settle(ap, 500); ap.select_option('#fnS', 'distributor'); ap.fill('#fnN', 'Revoked %s' % j.tag)
        dlg_click(j, ap, T(j, r'Make invitation', r'إنشاء الدعوة'), 'Make invitation'); j.settle(ap, 1200)
        code2 = ap.evaluate("(document.querySelector('.dx-fnd-code')||{}).innerText||''").strip(); dlg_click(j, ap, T(j, r'^\W*Done\W*$', r'^\W*تم\W*$'), 'Done')
        row = ap.locator('#adminContent tr', has_text=code2.replace('-', '')[-4:]).first; row.locator('.dx-fnd-rev').click(); j.settle(ap, 500)
        dlg_click(j, ap, T(j, r'^\W*Revoke\W*$', r'^\W*سحب\W*$'), 'Revoke'); j.settle(ap, 1000)
        j.check(re.search(T(j, r'Revoked', r'مسحوبة'), ap.locator('#adminContent tr', has_text=code2.replace('-', '')[-4:]).first.inner_text()), 'the invitation is not shown as revoked')
        open_link(xp, code2)
        j.check(dlg_open(xp) and re.search(T(j, r'withdrawn|already a founding', r'سحب|بالفعل'), dlg_text(xp)), 'a revoked invitation is not refused')
        close_dialogs(xp)
    with j.step('Guessing codes is blocked by the server (ten wrong codes an hour)'):
        if j.demo: j.skip('the server rule is checked in live')
        res = xp.evaluate("async()=>{const out=[];for(let i=0;i<11;i++){const r=await dxLive.sb.rpc('founder_redeem',{p_code:'DBX-AAAA-AAAA-AAAA-AAAA-AAA'+i,p_company:null});out.push(r.error?r.error.code:(r.data&&r.data.error)||'ok')}return out}")
        j.check(res[-1] == '54000', 'eleven wrong codes in a row are not blocked (%s)' % res[-3:])

@journey('J-BUSINESS-W03')
def directory_import(j):
    """Drugbox imports companies from an official public list (CSV) as unclaimed pages; duplicates are skipped; a company claims its page with documents."""
    tag = j.tag
    if j.live:
        adm = staff(j); ap = adm['page']; dup = seed_company(j, None, 'Duplicate Pharma %s' % tag, status='unclaimed', source='public_list')['name']
        me = j.person('Eng. Delta Claimant'); pg = me['page']; reg = str(int(time.time()))[-8:]
    else:
        ap = pg = j.demo_signin(j.new_page()); dup = 'Quadra Pharm'; reg = '51234'
    new1, new2 = 'Delta Sterile %s S.A.E.' % tag, 'Sinai Pack %s' % tag
    csv = os.path.join(j.cfg['out'], 'import-%s.csv' % tag); os.makedirs(j.cfg['out'], exist_ok=True)
    open(csv, 'w', encoding='utf-8').write('﻿name,name_ar,sectors,governorate,city,registry,source\n'
        '"%s","دلتا للمعقمات %s","Manufacturer;CMO / Toll",Gharbia,Tanta,%s,"EDA licensed manufacturers list, 2026-09"\n' % (new1, tag, reg) +
        '"%s co.",,Manufacturer,Giza,Dokki,,"EDA licensed manufacturers list, 2026-09"\n' % dup.lower() +
        '"Nameless Source %s",,Manufacturer,Cairo,Nasr City,,\n' % tag +
        '"delta sterile %s",,Manufacturer,Gharbia,Tanta,,"Chamber of pharmaceutical industries list, 2026"\n' % tag +
        '"%s",,Packaging,"South Sinai","El Tor",,"Chamber of pharmaceutical industries list, 2026"\n' % new2)
    with j.step('Admin → Directory import: choose the CSV and check it first — nothing is written'):
        admin_tab(j, ap, 'dirimport', 'Directory import')
        ap.set_input_files('#impF', csv); j.settle(ap, 800)
        ap.locator('.dx-imp-check').click(); j.settle(ap, 1500)
        t = j.text(ap, '#adminContent')
        j.check(re.search(T(j, r'Would add: 2', r'ستُضاف: 2'), t), 'the check does not find the 2 new companies (%s)' % t[-300:].replace('\n', ' '))
        j.check(re.search(T(j, r'Duplicates: 1', r'مكررة: 1'), t) and re.search(T(j, r'Invalid: 2', r'غير صالحة: 2'), t), 'the check does not report the duplicate and the 2 invalid rows')
        j.check(re.search(r'source', t, re.I), 'the row without a source is not refused for it')
        if j.live: j.check(j.sql1("select count(*) from public.companies where name in ($q$%s$q$, $q$%s$q$)" % (new1, new2)) == '0', 'the check wrote companies')
        ui_ok(j, ap, 'Directory import')
    with j.step('Import: two unclaimed pages from the public list, named after their source'):
        ap.locator('.dx-imp-go').click(); j.settle(ap, 1800)
        if j.live:
            rows = j.sql("select status||'|'||source||'|'||coalesce(source_ref,'')||'|'||coalesce(registry,'') from public.companies where name in ($q$%s$q$, $q$%s$q$) order by name" % (new1, new2)).split('\n')
            j.check(len(rows) == 2 and all(r.startswith('unclaimed|public_list|') for r in rows), 'the imported companies are not unclaimed public-list pages (%s)' % rows)
            j.check(any(r.endswith('|' + reg) for r in rows), 'the registry number was not kept')
            j.check(j.sql1("select count(*) from public.companies where lower(name) like 'duplicate pharma %s%%'" % tag) == '1', 'the duplicate was imported')
    with j.step('The directory shows the imported page marked "Unclaimed"'):
        directory(j, pg); search_dir(j, pg, 'Delta Sterile %s' % tag, want='Delta Sterile %s' % tag)
        c = pg.locator('#dxDir .dr-card', has_text='Delta Sterile %s' % tag).first
        j.check(c.count(), 'the imported company is not in the directory')
        j.check(re.search(r'Unclaimed|لم يطالب بها أحد', c.inner_text()), 'the imported page is not marked unclaimed')
    with j.step('The company claims it with its commercial registry document; Drugbox finds the claim in Admin → Review → Claims'):
        add_or_claim(j, pg, 'Delta Sterile %s' % tag)
        row = j.find(pg, r'^\W*(Claim|طالب بها|طالب)\W*$', scope='body'); j.check(row, "no 'Claim' on the imported page"); row.click(); pg.wait_for_timeout(800)
        fill_by_label(j, pg, r'role|دورك|وظيفتك', 'General Manager'); fill_by_label(j, pg, r'Mobile|الجوال|الموبايل', '+20 100 777 8899', required=False)
        fill_by_label(j, pg, r'Work email|البريد', 'gm@deltasterile.example')
        pg.locator('.dbk-ov input[type=file]').first.set_input_files(PDF)
        dlg_click(j, pg, r'Send|أرسل', 'Send claim'); j.settle(pg, 1500)
        if j.live:
            cid = j.sql1("select id from public.companies where name=$q$%s$q$" % new1)
            j.check(j.wait_db("select count(*) from public.verification_requests where company_id=%s" % cid, 8) != '0', 'the claim was not stored')
            t = admin_review(j, ap, 'claims'); j.check(('Delta Sterile %s' % tag) in t, 'the claim is not in Admin → Review → Claims')

@journey('J-BUSINESS-W04')
def visitor_company_page(j):
    """A visitor who is not signed in reads a company's public page (name, about, products, sites, verified badge); contacting needs sign-in."""
    if j.live:
        so = j.person('Visible Supplier'); co = seed_company(j, so['id'], 'Visible Sterile %s' % j.tag, sectors=('Manufacturer',), tagline='Sterile injectables for Egypt and the GCC', phone='+20 2 5555 7777', email='sales@visible.example')
        seed_product(j, co['id'], 'Ceftriaxone 1 g vial %s' % j.tag, 'Ceftriaxone', 'سيفترياكسون', 'Powder for injection', '1 g', 'manufacturer')
        name, slug = co['name'], co['slug']
    else:
        name, slug = 'Quadra Pharm', 'quadra-pharm'
    v = j.new_page()
    with j.step('Signed out, the sign-in page offers the company directory; it opens without an account'):
        j.check(j.on_login(v), 'a signed-out visitor does not start at the sign-in page')
        j.click(v, T(j, r'Browse the company directory', r'تصفّح دليل الشركات'), scope='body', what='Browse the company directory'); j.settle(v, 1500)
        j.check(j.in_app(v) and v.locator('#dxDir').count(), 'the visitor does not reach the company directory')
        ui_ok(j, v, 'the directory for a visitor')
    with j.step("Open the company's page: name, about, products, sites and the verified badge — no phone or e-mail"):
        directory(j, v); open_card(j, v, name); t = j.text(v)
        j.check(name in t, 'the page does not show the company name')
        if j.live:
            j.check('Sterile injectables for Egypt' in t, 'the page does not show its about line')
            j.check('5555 7777' not in j.text(v, 'body') and 'sales@visible.example' not in j.text(v, 'body'), 'a visitor sees the phone or e-mail')
            pt = company_tab(j, v, 'Products|%s' % ar('Products'), 'Products'); j.check(('Ceftriaxone 1 g vial %s' % j.tag) in pt, 'a visitor does not see the products')
            company_tab(j, v, 'Sites|%s' % ar('Sites'), 'Sites')
        j.check(v.evaluate('document.title').startswith(name), 'the page title is not the company (%s)' % v.evaluate('document.title'))
        d = v.evaluate("(document.querySelector('meta[property=\"og:title\"]')||{}).content||''"); j.check(d.startswith(name), 'no Open Graph title for the page')
    with j.step('Contacting needs sign-in: Follow / Message / Contact take the visitor to sign in'):
        b = j.find(v, r'Follow|Message|Request a quote|تابع|رسالة|اطلب عرض', scope='#content')
        j.check(b, 'the page has no contact or follow control'); b.click(); j.settle(v, 900)
        j.check(j.on_login(v), 'a visitor could contact or follow without signing in')
        if j.live:
            anon = v.evaluate("async()=>{const r=await dxLive.sb.from('companies').select('phone').eq('slug',%r);return JSON.stringify(r.data||r.error)}" % slug)
            j.check(anon == '[]' or 'permission' in anon or '42501' in anon, 'the companies table answers a visitor directly (%s)' % anon[:80])
            pub = v.evaluate("async()=>{const r=await dxLive.sb.rpc('public_company',{p_slug:%r});return JSON.stringify(r.data||r.error)}" % slug)
            j.check(name in pub and '5555' not in pub and 'sales@' not in pub, 'the public page data carries contact details (%s)' % pub[:120])
    with j.step('A shared link #/companies/<slug> opens the page directly for a visitor'):
        w = j.new_page(url=False); j.open(w, j.url + '#/companies/' + slug); j.settle(w, 3000)
        j.check(j.in_app(w) and name in j.text(w)[:1500], 'the shared link does not open the company page for a visitor')
    with j.step('Signing in from the visitor bar opens the app as the member'):
        if j.demo: j.skip('the demo signs in only its sample account')
        j.click(w, T(j, r'^\W*Sign in\W*$', r'^\W*تسجيل الدخول\W*$'), scope='body', what='Sign in'); j.settle(w, 800)
        j.check(j.on_login(w), "the visitor bar's Sign in does not open the sign-in page")
        j.signin(w, so['email'], so['pw']); j.check(j.in_app(w) and not w.locator('.dx-guest-bar').count(), 'signing in did not leave the visitor view')

if __name__ == '__main__': main(__file__)
