"""C1 end-to-end: directory from the database, Arabic ingredient search, company page sites/certificates, the real create wizard,
my companies / acting, page edits saved, verification request, and the database guards."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
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
    T('an unclaimed page from the public list is listed (labelled unclaimed)', pg.evaluate(f"dxDir.companies().some(c=>c.name==='Unclaimed Pharma {st}'&&c.status==='unclaimed'&&c.owner!==ME.id)"))
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
    T('no errors in the page', not errs, errs)
    b.close()
done()
