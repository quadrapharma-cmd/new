from playwright.sync_api import sync_playwright
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)))
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    for vp in [{'width':1440,'height':900},{'width':390,'height':844}]:
        pg=b.new_page(viewport=vp); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
        pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='networkidle',timeout=60000); pg.evaluate('endSplash()'); pg.wait_for_timeout(600)
        pg.click('.lg-demo'); pg.click('#loginPage .f-btn'); pg.wait_for_timeout(3300)
        if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
        w=vp['width']; tops=[]
        for n,nxt in [('feed','market'),('market','jobs'),('jobs','groups'),('groups','market'),('profile','feed')]:
            pg.evaluate(f"goto('{n}')"); pg.wait_for_timeout(250); pg.mouse.move(w//2, vp['height']//2); pg.mouse.wheel(0,2200); pg.wait_for_timeout(350)
            s=pg.evaluate("document.getElementById('content').scrollTop"); pg.evaluate(f"goto('{nxt}')"); pg.wait_for_timeout(250)
            tops.append((round(s),pg.evaluate("document.getElementById('content').scrollTop")))
        T(f'{w}px: every page opens at the top', all(t[0]>200 and t[1]==0 for t in tops), tops)
        pg.evaluate("goto('feed')"); pg.wait_for_timeout(250); pg.mouse.move(w//2, vp['height']//2); pg.mouse.wheel(0,2200); pg.wait_for_timeout(350)
        pg.evaluate("gotoProfile(3)"); pg.wait_for_timeout(300)
        T(f'{w}px: opening a profile starts at the top', pg.evaluate("document.getElementById('content').scrollTop")==0)
        pg.evaluate("goto('feed')"); pg.wait_for_timeout(300); t=pg.evaluate("POSTS[POSTS.length-1].id"); pg.evaluate(f"dgJump({t})"); pg.wait_for_timeout(900)
        T(f'{w}px: jump to a post still works', 0<=pg.evaluate(f"Math.round(document.getElementById('post-{t}').getBoundingClientRect().top)")<vp['height']*0.6)
        T(f'{w}px: no errors', not errs, errs); pg.close()
    print(sum(R),'/',len(R)); b.close()
