from playwright.sync_api import sync_playwright
F=[]
def check(n, ok, d=''):
    print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)[:220]))
    if not ok: F.append(n)
def boot(pg):
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
def tour(pg):
    bad=[]
    for s in ["goto('feed')","goto('market')","goto('companies')","dxHub.page('quadra-pharm')","dxHub.page('quadra-pharm','reviews')","dxHub.workspace('quadra-pharm')","dxHub.workspace('quadra-pharm','team')","dxHub.workspace('quadra-pharm','suppliers')","dxDeals.center('sent')","goto('jobs')","goto('profile')","goto('messages')"]:
        try: pg.evaluate(s); pg.wait_for_timeout(250); pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
        except Exception as e: bad.append((s, str(e)[:90]))
    return bad
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); pg=ctx.new_page(); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:160])); pg.on("dialog", lambda d: d.dismiss())
    boot(pg); E=pg.evaluate
    E("localStorage.setItem('dx_acting',JSON.stringify('quadra-pharm'))")
    did=E("dxDeals.create('quote','medsinia-industries','Persist test',{qty:'2',unit:'kg'},'x').id")
    E("dxHub.workspace('quadra-pharm','page')"); pg.wait_for_timeout(200); pg.fill('#wAr','اسم للاختبار'); pg.click('#dxDir [data-war]'); pg.wait_for_timeout(200)
    E("dxDir3.setAvl('alex-excipients','approved')")
    pg.reload(); boot(pg)
    check('1 deal survives reload', E(f"!!dxDeals.get('{did}')"))
    check('1 edited Arabic name survives reload', E("dxHubData.nameAr(dxDir.bySlug('quadra-pharm'))")=='اسم للاختبار')
    check('1 approved-vendor status survives reload', E("dxDir3.avl()['alex-excipients'].status")=='approved')
    check('1 acting company survives reload', 'Quadra' in pg.inner_text('#dxCoSwitch'))
    # 2 · corrupted storage
    E("Object.keys(localStorage).filter(k=>k.indexOf('dx_')===0).forEach(k=>localStorage.setItem(k,'{{broken json'))")
    errs.clear(); pg.reload(); boot(pg)
    bad=tour(pg)
    check('2 app opens with every stored value corrupted', E("document.getElementById('app').offsetWidth>0"))
    check('2 every screen renders with corrupted storage', not bad, bad)
    check('2 no script errors with corrupted storage', not errs, errs[:3])
    # 3 · wrong types
    E("""(()=>{['dx_deals','dx_company_edits','dx_created_companies','dx_supplier_reviews','dx_review_meta','dx_reports','dx_saved_searches','dx_follows','dx_avl_quadra-pharm','dx_dossiers','dx_surplus_new','dx_groups_state','dx_acting','dx_my_requests'].forEach((k,i)=>localStorage.setItem(k, JSON.stringify([42,'x',null,{},true][i%5])))})()""")
    errs.clear(); pg.reload(); boot(pg)
    bad=tour(pg)
    check('3 every screen renders with wrong-type storage', not bad, bad)
    check('3 no script errors with wrong-type storage', not errs, errs[:3])
    b.close()
    # 4 · storage blocked entirely
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 12'])
    ctx.add_init_script("(()=>{var e=function(){throw new DOMException('insecure','SecurityError')};try{Object.defineProperty(window,'localStorage',{get:e,configurable:true})}catch(x){}})()")
    pg=ctx.new_page(); errs2=[]; pg.on("pageerror",lambda e:errs2.append(str(e)[:160])); pg.on("dialog", lambda d: d.dismiss())
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.wait_for_timeout(400); pg.click('#splash'); pg.wait_for_timeout(900)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3000)
    bad=tour(pg)
    check('4 storage blocked: every screen renders', not bad, bad)
    check('4 storage blocked: no script errors', not errs2, errs2[:3])
    b.close()
    print('FINDINGS:', F)
