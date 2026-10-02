from playwright.sync_api import sync_playwright
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)))
def cur(pg): return pg.evaluate("(()=>{var t=document.querySelector('.lp:target');return t?t.id:'(login)'})()")
with sync_playwright() as p:
    for eng in ('webkit','chromium'):
        for mode, kw, path in (('JS blocked', {}, '/tmp/csp_block.html'), ('JS disabled', {'java_script_enabled': False}, '/tmp/drugbox_brand.html')):
            dev=p.devices['iPhone 12'] if eng=='webkit' else p.devices['Pixel 5']
            b=(p.webkit.launch() if eng=='webkit' else p.chromium.launch(args=["--no-sandbox"])); ctx=b.new_context(**dev, **kw); pg=ctx.new_page()
            pg.goto('file://'+path,wait_until='load'); pg.wait_for_timeout(600)
            tag=f'[{eng} · {mode}] '
            T(tag+'splash shows first', pg.is_visible('#splash') and pg.evaluate("getComputedStyle(document.getElementById('splash')).opacity")=='1')
            pg.wait_for_timeout(4200)
            T(tag+'splash hides by itself → login page', pg.evaluate("getComputedStyle(document.getElementById('splash')).visibility")=='hidden' and pg.is_visible('#loginPage'))
            if eng=='webkit' and mode=='JS blocked': pg.screenshot(path='/tmp/lite_login.png')
            pg.click('#loginPage .dx-lite-enter'); pg.wait_for_timeout(400)
            T(tag+'Sign In → Home', cur(pg)=='p-feed' and pg.is_visible('#p-feed .lh') and pg.is_visible('#p-feed .ln'))
            if eng=='webkit' and mode=='JS blocked': pg.screenshot(path='/tmp/lite_home.png')
            ok=True
            for k in ['market','companies','jobs','messages']:
                pg.click(f'#p-feed .ln a[href="#p-{k}"]') if cur(pg)=='p-feed' else pg.click(f'.lp:target .ln a[href="#p-{k}"]'); pg.wait_for_timeout(250)
                ok = ok and cur(pg)==f'p-{k}' and len(pg.inner_text(f'#p-{k} .lm-c'))>300
            T(tag+'bottom bar switches pages with real content', ok)
            if eng=='webkit' and mode=='JS blocked': pg.click('.lp:target .ln a[href="#p-companies"]'); pg.wait_for_timeout(250); pg.screenshot(path='/tmp/lite_dir.png')
            pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(250)
            T(tag+'menu lists all 12 pages', cur(pg)=='p-menu' and pg.locator('#p-menu .lmenu a').count()==13)
            allok=True
            for k in ['network','notifs','profile','groups','training','saved','company']:
                pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(150); pg.click(f'#p-menu .lmenu a[href="#p-{k}"]'); pg.wait_for_timeout(200)
                allok = allok and cur(pg)==f'p-{k}'
            T(tag+'every page reachable from the menu', allok)
            pg.click('.lp:target .lh a[href="#p-menu"]'); pg.wait_for_timeout(150); pg.click('#p-menu .lmenu-out'); pg.wait_for_timeout(300)
            T(tag+'Sign out → back to the login page', cur(pg)=='(login)' and pg.is_visible('#loginPage'))
            ov=pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
            T(tag+'no sideways overflow', ov<=2, ov)
            b.close()
    # normal browser untouched
    for eng in ('webkit','chromium'):
        dev=p.devices['iPhone 12'] if eng=='webkit' else p.devices['Pixel 5']
        b=(p.webkit.launch() if eng=='webkit' else p.chromium.launch(args=["--no-sandbox"])); ctx=b.new_context(**dev); pg=ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.wait_for_timeout(300)
        lite=pg.evaluate("!!document.getElementById('dxLite')"); link=pg.is_visible('.dx-lite-enter')
        pg.click('#splash'); pg.wait_for_timeout(900); pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3000)
        T(f'[{eng} · browser] full app, lite copy not in the page', (not lite) and (not link) and pg.evaluate("document.getElementById('app').offsetWidth>0") and not errs, (lite, link, errs))
        b.close()
    print(sum(R),'/',len(R))
