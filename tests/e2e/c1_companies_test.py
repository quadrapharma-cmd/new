"""C1 end-to-end: directory from the database, Arabic ingredient search, company page sites/certificates, the real create wizard,
my companies / acting, page edits saved, verification request, the database guards, and the directory a page at a time (F-05):
100 companies when Companies opens, the next 100 on "Show more", a search asks the database, a company from a page not loaded
opens by its slug, and a revisit within 2 minutes downloads nothing. Two accounts creating the same name: the second browser takes
the address the database gave it (x-2) everywhere at once, the editor included (N-11)."""
from playwright.sync_api import sync_playwright
import subprocess, time, os, re
from _dx import APP_URL as U, DB, R, T, sql, ST, STN, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'; CO = f'Nile Test Pharma {st}'
# a verified company with a site, a checked WHO-GMP certificate and a metformin product (set up by the platform)
cid = sql(f"insert into public.companies (owner_id, name, type, status, registry, licensed, sectors, governorate, city, tagline) values ((select id from public.profiles order by created_at limit 1), '{CO}','Manufacturer','verified','55{STN % 100000}',true,'{{Manufacturer}}','Giza','6th of October','Solid dosage forms') returning id").split('\n')[0]
sid = sql(f"insert into public.company_sites (company_id, name, type, city, governorate) values ({cid},'October plant','factory','6th of October','Giza') returning id").split('\n')[0]
sql(f"insert into public.site_certificates (site_id, company_id, name, expiry, checked_at) values ({sid},{cid},'WHO-GMP','2027-04-01',now())")
sql(f"insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, strength, role) values ({cid},'Glucophage-like 500','Metformin HCl','ميتفورمين','Tablet','500 mg','manufacturer')")
slug = sql(f"select slug from public.companies where id={cid}")
sql(f"insert into public.companies (name, type, status, source, sectors, governorate) values ('Unclaimed Pharma {st}','Manufacturer','unclaimed','public_list','{{Manufacturer}}','Cairo')")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_context(viewport={'width': 1440, 'height': 900}).new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'Dr. Company Owner'); pg.fill('#suEmail', f'owner{st}@x.test'); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    me = pg.evaluate("dxLive.uuidOf(ME.id)")
    pg.evaluate("dxDir.S.view=null;goto('companies')"); pg.wait_for_timeout(3000)
    names = pg.evaluate("dxDir.companies().map(c=>c.name)")
    T('directory lists companies from the database, not the 17 demo companies', CO in names and 'Medsinia Industries' not in names, names[:5])
    unc = f"dxDir.companies().some(c=>c.name==='Unclaimed Pharma {st}'&&c.status==='unclaimed'&&c.owner!==ME.id)"
    if not pg.evaluate(unc): pg.fill('#hbQ', f'Unclaimed Pharma {st}'); wait_for(lambda: pg.evaluate(unc), 10); pg.fill('#hbQ', ''); pg.wait_for_timeout(300)   # beyond the first page: found by a search
    T('an unclaimed page from the public list is listed (labelled unclaimed)', pg.evaluate(unc))
    T('the company shows as verified with its certificate', pg.evaluate(f"(()=>{{var c=dxDir.bySlug('{slug}');return c&&c.status==='verified'&&c.certs.indexOf('WHO-GMP')>=0}})()"))
    pg.fill('#hbQ', 'ميتفورمين'); pg.wait_for_timeout(1500)
    T('Arabic active-ingredient search finds the company ("Who makes")', CO in pg.inner_text('#dxDir'), pg.inner_text('#dxDir')[:200])
    pg.fill('#hbQ', ''); pg.evaluate(f"dxHub.page('{slug}','sites')"); pg.wait_for_timeout(2500)
    txt = pg.inner_text('#dxDir')
    T('company page shows its site and certificate expiry from the database', 'october plant' in txt.lower() and '2027-04' in txt, txt[:300])
    # the real creation wizard
    pg.evaluate("dxDir.S.view=null;goto('companies')"); pg.wait_for_timeout(800); pg.evaluate("dxDir.create()"); pg.wait_for_timeout(600)
    NEWCO = f'Owner Labs {st}'
    def dlg(): return pg.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();return o?{inputs:[...o.querySelectorAll('input,select,textarea')].map(i=>(i.id||i.name||i.type)+(i.type?':'+i.type:'')),buttons:[...o.querySelectorAll('button')].map(x=>x.textContent.trim())}:null})()")
    free = pg.locator(".dbk-ov input[name=plPick][value=free]")
    if free.count(): free.first.check()
    pg.locator('.dbk-ov button', has_text='Next: company details').first.click(); pg.wait_for_timeout(700)
    d = dlg()
    name_in = pg.locator('.dbk-ov input[type=text]:not(#ccC):not(#ccP):not(#ccE), .dbk-ov input:not([type]):not(#ccC):not(#ccP):not(#ccE)')
    if name_in.count(): name_in.first.fill(NEWCO)
    if pg.locator('#ccS').count(): pg.select_option('#ccS', index=1)
    if pg.locator('#ccG').count(): pg.select_option('#ccG', index=1)
    for i, v in [('#ccC', 'Dokki'), ('#ccP', '+20 100 000 0000'), ('#ccE', f'info{st}@ownerlabs.test')]:
        if pg.locator(i).count(): pg.fill(i, v)
    pg.locator('.dbk-ov button', has_text='Next: review').first.click(); pg.wait_for_timeout(700)
    d2 = dlg(); last = [x for x in (d2 or {}).get('buttons', []) if x not in ('×', 'Cancel', 'Back')]
    if last: pg.locator('.dbk-ov button', has_text=last[-1]).first.click(); pg.wait_for_timeout(2500)
    print('   wizard steps seen:', d and d['inputs'], '→ final button:', last[-1:])
    row = sql(f"select status||'|'||plan||'|'||coalesce(city,'') from public.companies where name='{NEWCO}'")
    T('the wizard creates the company in the database — pending, free plan', row.startswith('pending|free'), row)
    T('the creator becomes the owner member', sql(f"select role from public.company_members m join public.companies c on c.id=m.company_id where c.name='{NEWCO}' and m.user_id='{me}'") == 'owner')
    nslug = sql(f"select slug from public.companies where name='{NEWCO}'")
    T('it appears under my companies (acting as)', pg.evaluate(f"dxDir.mine&&dxDir.mine()?dxDir.mine().slug:''") == nslug or pg.evaluate(f"dxDir.companies().some(c=>c.slug==='{nslug}'&&c.owner===ME.id)"))
    # page edit through the directory's own store() path
    pg.evaluate(f"(()=>{{var e={{}};e['{nslug}']={{tagline:'Sterile injectables and ophthalmics',about:'We make sterile products.',hours:'Sun–Thu 9–5',services:['Aseptic filling']}};return window.dxStoreHook('company_edits',e)}})()"); pg.wait_for_timeout(1500)
    T('page edits are saved (tagline, about, hours, services)', sql(f"select tagline||'|'||bio||'|'||hours||'|'||(profile->'services'->>0) from public.companies where slug='{nslug}'") == 'Sterile injectables and ophthalmics|We make sterile products.|Sun–Thu 9–5|Aseptic filling')
    # verification request through store(): status pending + registry
    pg.evaluate(f"(()=>{{var c=dxDir.companies().filter(x=>x.slug==='{nslug}').map(x=>Object.assign({{}},x,{{status:'pending',registry:'778899'}}));return window.dxStoreHook('created_companies',c)}})()"); pg.wait_for_timeout(1500)
    T('verification request reaches Drugbox (pending review)', sql(f"select r.status||'|'||r.registry from public.verification_requests r join public.companies c on c.id=r.company_id where c.slug='{nslug}'") == 'pending|778899')
    # database guards through the API
    ncid = sql(f"select id from public.companies where slug='{nslug}'")
    r = pg.evaluate(f"dxLive.sb.from('companies').update({{status:'verified'}}).eq('id',{ncid})" + ERR)
    T('an owner cannot mark their own company verified', refused(r) and sql(f"select status from public.companies where id={ncid}") == 'pending', r)
    r = pg.evaluate(f"dxLive.sb.from('companies').update({{plan:'vip',licensed:true}}).eq('id',{ncid})" + ERR)
    T('an owner cannot give themselves VIP or a licence', refused(r) and sql(f"select plan||'|'||coalesce(licensed::text,'false') from public.companies where id={ncid}") == 'free|false', r)
    r = pg.evaluate(f"dxLive.sb.from('companies').insert({{name:'Sneaky Co {st}',type:'Manufacturer',status:'verified',plan:'vip',owner_id:'{me}'}}).select().single().then(r=>r.data?r.data.status+'|'+r.data.plan:'error')")
    T('a new company can never start verified or VIP', r == 'pending|free', r)
    r = pg.evaluate(f"dxLive.sb.from('companies').update({{tagline:'hacked'}}).eq('id',{cid}).select().then(r=>(r.data||[]).length)")
    T("cannot edit someone else's company", r == 0 and sql(f"select tagline from public.companies where id={cid}") == 'Solid dosage forms')
    # F-05: the directory a page at a time — a fresh tab (same session, a fresh adapter) at 260+ companies
    sql(f"insert into public.companies (name, type, status, source, sectors, governorate) select 'Paging Co {st} '||lpad(g::text,3,'0'),'Manufacturer','unclaimed','public_list','{{Manufacturer}}','Cairo' from generate_series(1,260) g")
    total = int(sql("select count(*) from public.companies where status <> 'suspended'"))
    P2 = pg.context.new_page(); P2.on("pageerror", lambda e: errs.append(str(e)[:150])); calls = []
    P2.on('response', lambda r: calls.append(r) if '/rpc/directory_companies' in r.url else None)
    P2.goto(U, wait_until='load'); P2.wait_for_timeout(400); P2.evaluate('endSplash()'); wait_for(lambda: P2.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); P2.wait_for_timeout(1500)
    T('signing in loads no directory page', not calls, [c.url for c in calls])
    P2.evaluate("dxDir.S.view=null;goto('companies')"); wait_for(lambda: P2.evaluate("document.querySelectorAll('#dxDir .dr-card').length") > 0 and len(calls) >= 1, 10)   # evaluate first: it lets Playwright deliver the response events; P2.wait_for_timeout(800)
    import json as _j
    body = lambda c: _j.loads(c.request.post_data or '{}')
    first = [body(c) for c in calls]; kb = sum(len(c.body()) for c in calls) / 1024
    n1 = P2.evaluate("dxDir.companies().length")
    T('opening Companies downloads ONE page of 100 (not every company)', len(calls) == 1 and first[0].get('p_limit') == 100 and first[0].get('p_offset') == 0 and 100 <= n1 <= 110 and n1 < total, (first, n1, total))
    print(f'   (first open: {len(calls)} request, {kb:.0f} KB for {n1} of {total} companies)')
    T('the old full-directory call is never made', not any(c.url.split('?')[0].endswith('/rpc/directory_companies') for c in calls))
    P2.evaluate("document.querySelector('#dxDir [data-hmore]').click()"); wait_for(lambda: P2.evaluate("dxDir.companies().length") > n1 and len(calls) >= 2, 10)
    T('"Show more" fetches the next page (offset 100)', len(calls) == 2 and body(calls[1]).get('p_offset') == 100 and P2.evaluate("dxDir.companies().length") >= 200, [body(c) for c in calls])
    P2.evaluate("goto('feed')"); P2.wait_for_timeout(300); P2.evaluate("dxDir.S.view=null;goto('companies')"); P2.wait_for_timeout(1200)
    T('a revisit within 2 minutes downloads nothing', len(calls) == 2, [body(c) for c in calls])
    far = f'Paging Co {st} 259'
    T('(a company beyond the loaded pages is not in the list yet)', not P2.evaluate(f"dxDir.companies().some(c=>c.name==='{far}')"))
    P2.fill('#hbQ', far); wait_for(lambda: far in P2.inner_text('#dxDir'), 10)
    T('a search asks the database (p_q) and finds a company beyond the loaded pages', far in P2.inner_text('#dxDir') and any(body(c).get('p_q') == far.lower() and body(c).get('p_offset') == 0 for c in calls), [body(c) for c in calls])
    T('the search box keeps focus while the results arrive', P2.evaluate("document.activeElement && document.activeElement.id") == 'hbQ')
    P2.fill('#hbQ', ''); P2.wait_for_timeout(400)
    s250 = sql(f"select slug from public.companies where name='Paging Co {st} 250'")
    T('(that one is not loaded either)', not P2.evaluate(f"!!dxDir.bySlug('{s250}')"))
    P2.evaluate(f"goto('feed')"); P2.wait_for_timeout(300); P2.evaluate(f"dxDir.open('{s250}')"); wait_for(lambda: f'Paging Co {st} 250' in P2.inner_text('#dxDir'), 10)
    T('a link to a company from a page not loaded opens its page (fetched by its slug)', P2.evaluate(f"dxDir.S.open") == s250 and f'Paging Co {st} 250' in P2.inner_text('#dxDir') and 'Find any pharma company' not in P2.inner_text('#dxDir'), P2.inner_text('#dxDir')[:200])
    P2.close()
    # N-11: two accounts create the same company name; the database gives the second one another address (x → x-2) and its
    # browser takes that address at once — links, my pages, acting as, the open page and the editor — without a reload
    TW = f'Twin Labs {st}'; tbase = re.sub(r'[^a-z0-9]+', '-', TW.lower()).strip('-')[:40].rstrip('-')
    P3 = b.new_context(viewport={'width': 1440, 'height': 900}).new_page(); P3.on("pageerror", lambda e: errs.append(str(e)[:150])); P3.on("dialog", lambda d: d.accept())
    P3.goto(U, wait_until='load'); P3.wait_for_timeout(400); P3.evaluate('endSplash()'); P3.wait_for_timeout(700)
    P3.evaluate("showSignup()"); P3.fill('#suName', 'Dr. Second Owner'); P3.fill('#suEmail', f'second{st}@x.test'); P3.fill('#suPw', PW); P3.click('#signupPage button.f-btn')
    wait_for(lambda: P3.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); P3.wait_for_timeout(1500); me3 = P3.evaluate("dxLive.uuidOf(ME.id)")
    P3.evaluate("dxDir.S.view=null;goto('companies')"); wait_for(lambda: P3.evaluate("document.querySelectorAll('#dxDir .dr-card').length") > 0, 10); P3.evaluate("window.__sameTab = 1")
    # L-scale: a filter that leaves less than a screenful fetches ONE more page by itself, once — not five, not again on every filter
    dcalls = []; P3.on('request', lambda q: dcalls.append(_j.loads(q.post_data or '{}')) if '/rpc/directory_companies_page' in q.url else None)
    for wait in (2500, 600, 1500, 600): P3.click('#hbVer'); P3.wait_for_timeout(wait)
    T('a filter that leaves few companies fetches one more page by itself, once', [c.get('p_offset') for c in dcalls] == [100] and not P3.evaluate("dxDir.S.verified"), dcalls)
    # the first account creates it after the second one's directory loaded (the second browser does not know it yet)
    r = pg.evaluate(f"dxLive.sb.from('companies').insert({{owner_id:'{me}',name:'{TW}',slug:'{tbase}',type:'Manufacturer'}}).select('slug').single().then(r=>r.error?'error '+r.error.message:r.data.slug)")
    T('(the first account has the address)', r == tbase, r)
    # the second account's save answers slowly, as on a real network: the editor opens before the server's answer
    def slow(route):
        if route.request.method == 'POST': time.sleep(1.2)
        route.continue_()
    P3.route('**/rest/v1/companies*', slow)
    def wizard(name, email):   # the real creation wizard, up to "Create my page"
        P3.evaluate("dxDir.create()"); P3.wait_for_timeout(600)
        free = P3.locator(".dbk-ov input[name=plPick][value=free]")
        if free.count(): free.first.check()
        P3.locator('.dbk-ov button', has_text='Next: company details').first.click(); P3.wait_for_timeout(600)
        P3.fill('#ccN', name); P3.select_option('#ccS', index=1); P3.select_option('#ccG', index=1); P3.fill('#ccC', 'Maadi'); P3.fill('#ccP', '+20 100 000 0001'); P3.fill('#ccE', email)
        P3.locator('.dbk-ov button', has_text='Next: review').first.click(); P3.wait_for_timeout(600)
        P3.locator('.dbk-ov button', has_text='Create my page').first.click()
    sent = []; P3.on('request', lambda q: sent.append(q.post_data) if q.method == 'POST' and '/rest/v1/companies' in q.url else None)
    P3.evaluate("""new MutationObserver(function(m,o){if(!document.getElementById('dxEditor'))return;o.disconnect();window.__edOpen=dxDir.S.open}).observe(document.body,{childList:true,subtree:true})""")   # the address the editor opened on
    wizard(TW, f'twin{st}@x.test')
    T('(the second browser sent the same address)', wait_for(lambda: P3.evaluate('1') and any(f'"slug":"{tbase}"' in (x or '') for x in sent), 10), sent)
    srv = wait_for(lambda: P3.evaluate('1') and sql(f"select slug from public.companies where name='{TW}' and owner_id='{me3}'"), 15)
    T('the database gives the second company another address', srv == tbase + '-2' and sql(f"select owner_id from public.companies where slug='{tbase}'") == me, srv)
    wait_for(lambda: P3.evaluate("dxDir.S.open") == srv, 10)
    editor_early = P3.evaluate("window.__edOpen")
    T('(the editor opened before the answer, on the old address)', editor_early == tbase, editor_early)
    T('the open page takes the server address (no reload)', P3.evaluate("dxDir.S.open") == srv and P3.evaluate("window.__sameTab") == 1, P3.evaluate("dxDir.S.open"))
    st3 = P3.evaluate(f"""(()=>{{var L=window.dxLiveCompanies||[];return {{mineNew:L.filter(c=>c.slug==='{srv}'&&c.owner===ME.id).length, mineOld:L.filter(c=>c.slug==='{tbase}'&&c.owner===ME.id).length,
      acting:dxDir.mine()&&dxDir.mine().slug, stored:localStorage.getItem('dx_acting'), id:(dxDir.bySlug('{srv}')||{{}})._id, mine:dxDir.myCompanies().map(c=>c.slug)}}}})()""")
    T('the list, my pages and "acting as" use the server address', st3['mineNew'] == 1 and st3['mineOld'] == 0 and st3['acting'] == srv and st3['stored'] == '"' + srv + '"' and st3['mine'] == [srv]
      and str(st3['id']) == sql(f"select id from public.companies where slug='{srv}'"), st3)
    # the editor that opened on the old address saves to the second company and shows it again
    P3.fill('#edTag', 'Second twin tagline'); P3.click('#edSave'); P3.wait_for_timeout(300)
    wait_for(lambda: sql(f"select coalesce(tagline,'') from public.companies where slug='{srv}'") == 'Second twin tagline', 10)
    T("the editor's save goes to the second company, not the first", sql(f"select coalesce(tagline,'') from public.companies where slug='{srv}'") == 'Second twin tagline'
      and sql(f"select coalesce(tagline,'') from public.companies where slug='{tbase}'") == '', sql(f"select slug||':'||coalesce(tagline,'') from public.companies where name='{TW}'"))
    shown3 = P3.evaluate("[dxDir.S.open, (dxDir.bySlug(dxDir.S.open)||{}).owner===ME.id, (document.querySelector('#dxDir')||{}).innerText||'']")
    T('after the save the page shown is still the second company (mine)', shown3[0] == srv and shown3[1] and TW in shown3[2], shown3[:2] + [shown3[2][:200]])
    # links: in the directory each card opens its own company
    P3.evaluate("dxDir.S.open=null;dxDir.S.view=null;dxDir.render()"); P3.fill('#hbQ', TW)
    wait_for(lambda: P3.locator(f'#dxDir .dr-card[data-slug="{tbase}"]').count() and P3.locator(f'#dxDir .dr-card[data-slug="{srv}"]').count(), 10)
    own = P3.evaluate(f"""(()=>{{var a=document.querySelector('#dxDir .dr-card[data-slug="{srv}"]'),b=document.querySelector('#dxDir .dr-card[data-slug="{tbase}"]');return [a&&!!a.querySelector('.hb-own'),b&&!!b.querySelector('.hb-own'),document.querySelectorAll('#dxDir .dr-card[data-slug="{srv}"]').length]}})()""")
    T('the directory shows both: mine under the server address, the other under its own', own == [True, False, 1], own)
    P3.click(f'#dxDir .dr-card[data-slug="{srv}"] [data-hopen]'); P3.wait_for_timeout(500)
    T('my card opens my page', P3.evaluate("dxDir.S.open") == srv and 'Second twin tagline' in P3.inner_text('#dxDir'))
    P3.evaluate("dxDir.S.open=null;dxDir.render()"); P3.fill('#hbQ', TW); wait_for(lambda: P3.locator(f'#dxDir .dr-card[data-slug="{tbase}"]').count(), 10)
    P3.click(f'#dxDir .dr-card[data-slug="{tbase}"] [data-hopen]'); P3.wait_for_timeout(500)
    T("the other card opens the first account's company", P3.evaluate("dxDir.S.open") == tbase and P3.evaluate(f"(dxDir.bySlug('{tbase}')||{{}}).owner!==ME.id") and 'Second twin tagline' not in P3.inner_text('#dxDir') and P3.evaluate("window.__sameTab") == 1)
    # the same when the editor is saved before the database has answered (a slow network): the save follows the new address
    PD = f'Pending Labs {st}'; pbase = re.sub(r'[^a-z0-9]+', '-', PD.lower()).strip('-')[:40].rstrip('-')
    P3.evaluate("dxDir.S.open=null;dxDir.render()")
    sql(f"insert into public.companies (owner_id, name, slug, type) values ('{me}', '{PD}', '{pbase}', 'Manufacturer')")
    P3.evaluate("""new MutationObserver(function(m,o){var e=document.getElementById('edSave');if(!e)return;o.disconnect();setTimeout(function(){document.getElementById('edTag').value='Saved while pending';e.click();window.__savedAt=dxDir.S.open},50)}).observe(document.body,{childList:true,subtree:true})""")
    wizard(PD, f'pend{st}@x.test')
    pump = lambda: P3.evaluate('1')   # lets Playwright run the slow route (it only runs while Python is inside a Playwright call)
    psrv = wait_for(lambda: pump() and sql(f"select slug from public.companies where name='{PD}' and owner_id='{me3}'"), 15)
    wait_for(lambda: pump() and sql(f"select coalesce(tagline,'') from public.companies where slug='{psrv}'") == 'Saved while pending', 10); wait_for(lambda: P3.evaluate("dxDir.S.open") == psrv, 5)
    T('an editor saved before the answer: the save reaches the new address and its page is shown', psrv == pbase + '-2' and P3.evaluate("window.__savedAt") == pbase
      and sql(f"select coalesce(tagline,'') from public.companies where slug='{psrv}'") == 'Saved while pending' and sql(f"select coalesce(tagline,'') from public.companies where slug='{pbase}'") == ''
      and P3.evaluate("dxDir.S.open") == psrv and P3.evaluate("(dxDir.bySlug(dxDir.S.open)||{}).owner===ME.id"),
      [psrv, P3.evaluate("[window.__savedAt, dxDir.S.open]"), sql(f"select slug||':'||coalesce(tagline,'') from public.companies where name='{PD}'")])
    P3.close()
    T('no errors in the page', not errs, errs)
    b.close()
done()
