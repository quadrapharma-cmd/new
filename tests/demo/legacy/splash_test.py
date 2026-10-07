from playwright.sync_api import sync_playwright
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)))
LOGO="(()=>{var i=document.getElementById('splLogo');return !!(i&&i.complete&&i.naturalWidth>0&&i.offsetWidth>0)})()"
with sync_playwright() as p:
    for eng in [e for e in ('webkit','chromium') if e in __import__('os').environ.get('DX_ENGINES','webkit,chromium')]:   # DX_ENGINES: the browsers installed here
        dev=p.devices['iPhone 12'] if eng=='webkit' else p.devices['Pixel 5']
        L=lambda: (p.webkit.launch() if eng=='webkit' else p.chromium.launch(args=["--no-sandbox"]))
        for how in ('tap','skip'):
            b=L(); pg=b.new_context(**dev).new_page(); pg.goto('file://'+__import__('os').environ.get('DEMO_VARIANTS','/tmp')+'/worst.html',wait_until='load'); pg.wait_for_timeout(700)
            t=f'[{eng} · no scripts + no animations · {how}] '
            T(t+'splash shows with the logo', pg.is_visible('#splash') and pg.evaluate(LOGO))
            if eng=='webkit' and how=='tap': pg.screenshot(path='/tmp/worst_splash.png')
            pg.wait_for_timeout(4000)
            T(t+'without animations the splash waits (as expected)', pg.is_visible('#splash'))
            if how=='tap': pg.mouse.click(195, 420)
            else: pg.click('#splash .dx-lite-skip')
            pg.wait_for_timeout(400)
            T(t+'→ login page', (not pg.is_visible('#splash')) and pg.is_visible('#loginPage') and pg.evaluate("(()=>{var i=document.getElementById('formLogo');return i.naturalWidth>0})()"))
            pg.click('#loginPage .dx-lite-enter'); pg.wait_for_timeout(300)
            T(t+'Sign In → Home', pg.evaluate("(document.querySelector('.lp:target')||{}).id")=='p-feed')
            pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(200); pg.click('#p-menu .lmenu-out'); pg.wait_for_timeout(300)
            T(t+'Sign out → login (splash does not come back)', pg.is_visible('#loginPage') and not pg.is_visible('#splash'))
            b.close()
        b=L(); pg=b.new_context(**dev).new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load'); pg.wait_for_timeout(600)
        t=f'[{eng} · browser] '
        T(t+'splash logo visible, lite links hidden', pg.evaluate(LOGO) and not pg.is_visible('.dx-lite-skip') and not pg.is_visible('.dx-lite-tap'))
        pg.wait_for_timeout(6500)
        T(t+'splash ends by itself → login', not pg.is_visible('#splash') and pg.is_visible('#loginPage'))
        pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3000)
        T(t+'app opens, top-bar logo visible, no errors', pg.evaluate("document.getElementById('app').offsetWidth>0") and pg.evaluate("document.getElementById('topLogo').naturalWidth>0") and not errs, errs)
        b.close()
    print(sum(R),'/',len(R))
