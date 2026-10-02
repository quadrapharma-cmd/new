from playwright.sync_api import sync_playwright
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)))
def cur(pg): return pg.evaluate("(()=>{var t=document.querySelector('.lp:target');return t?t.id:'(login)'})()")
def signins(pg): return pg.evaluate("[...document.querySelectorAll('#loginPage .f-btn')].filter(e=>e.offsetWidth>0&&getComputedStyle(e).display!=='none'&&/Sign In/.test(e.textContent)).length")
with sync_playwright() as p:
    for eng in ('webkit','chromium'):
        dev=p.devices['iPhone 12'] if eng=='webkit' else p.devices['Pixel 5']
        L=lambda: (p.webkit.launch() if eng=='webkit' else p.chromium.launch(args=["--no-sandbox"]))
        for name, path, extra in (('stripped viewer', '/tmp/sanitized.html', {'java_script_enabled': False}), ('scripts blocked + no animations', '/tmp/worst.html', {})):
            b=L(); pg=b.new_context(**dev, **extra).new_page(); pg.goto('file://'+path, wait_until='load'); pg.wait_for_timeout(700)
            t=f'[{eng} · {name}] '
            T(t+'splash with logo', pg.is_visible('#splash') and pg.evaluate("document.getElementById('splLogo').naturalWidth>0"))
            T(t+'lite pages hidden (not one long sheet)', pg.evaluate("[...document.querySelectorAll('.lp')].filter(e=>e.offsetHeight>0).length")==0)
            pg.mouse.click(195, 420); pg.wait_for_timeout(400)
            T(t+'tap → login page', (not pg.is_visible('#splash')) and pg.is_visible('#loginPage'))
            T(t+'exactly one Sign In button', signins(pg)==1, signins(pg))
            if eng=='webkit' and name=='stripped viewer': pg.screenshot(path='/tmp/san_login.png')
            pg.click('#loginPage .dx-lite-enter'); pg.wait_for_timeout(350)
            T(t+'Sign In → app Home (one page at a time)', cur(pg)=='p-feed' and pg.evaluate("[...document.querySelectorAll('.lp')].filter(e=>e.offsetHeight>0).length")==1)
            if eng=='webkit' and name=='stripped viewer': pg.screenshot(path='/tmp/san_home.png')
            pg.click('.lp:target .ln a[href="#p-market"]'); pg.wait_for_timeout(300)
            T(t+'bottom bar → Marketplace', cur(pg)=='p-market')
            pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(250); pg.click('#p-menu .lmenu a[href="#p-profile"]'); pg.wait_for_timeout(250)
            T(t+'menu → Profile', cur(pg)=='p-profile')
            pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(250); pg.click('#p-menu .lmenu-out'); pg.wait_for_timeout(300)
            T(t+'sign out → login', cur(pg)=='(login)' and pg.is_visible('#loginPage') and not pg.is_visible('#splash'))
            b.close()
        b=L(); pg=b.new_context(**dev).new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.wait_for_timeout(6800)
        t=f'[{eng} · browser] '
        T(t+'splash ends → login with ONE Sign In', (not pg.is_visible('#splash')) and signins(pg)==1, signins(pg))
        pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3000)
        T(t+'full app opens, no lite pages, no errors', pg.evaluate("document.getElementById('app').offsetWidth>0") and not pg.evaluate("!!document.getElementById('dxLite')") and not errs, errs)
        b.close()
    print(sum(R),'/',len(R))
