from playwright.sync_api import sync_playwright
import random, time, statistics
random.seed(7)
PAGES=['feed','market','jobs','network','groups','messages','notifs','training','companies','saved','profile']
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox","--enable-precise-memory-info","--js-flags=--expose-gc"]); pg=b.new_page(viewport={'width':1440,'height':900})
    errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:160]))
    pg.goto('file:///tmp/backup/drugbox_before_batch4.html',wait_until='networkidle',timeout=90000); pg.evaluate('endSplash()'); pg.wait_for_timeout(600)
    pg.click('.lg-demo'); pg.click('#loginPage .f-btn'); pg.wait_for_timeout(3300)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    def mem(): 
        pg.evaluate("window.gc&&gc()"); return pg.evaluate("performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576):-1")
    def nodes(): return pg.evaluate("document.getElementsByTagName('*').length")
    m0,n0=mem(),nodes(); times=[]
    for i in range(300):
        pgname=random.choice(PAGES)
        t=pg.evaluate(f"(()=>{{var t=performance.now();goto('{pgname}');return performance.now()-t}})()"); times.append(t)
        if i%10==0: pg.wait_for_timeout(60)
        if pgname=='market' and i%7==0:
            pg.evaluate("var c=document.querySelector('#mkx .dx-cmp input'); c&&c.click()")
        if pgname=='jobs' and i%9==0:
            pg.evaluate("var b=document.querySelector('#jx .jx-tool'); b&&b.click(); document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    pg.wait_for_timeout(1500)
    m1,n1=mem(),nodes()
    lt=pg.evaluate("document.querySelectorAll('.dbk-ov,#dxTour').length")
    # wrapped layers on goto
    depth=pg.evaluate("goto.toString().length")
    print(f"page switches: 300 | JS errors: {len(errs)} {errs[:3]}")
    print(f"switch time ms: median {statistics.median(times):.1f} | p95 {sorted(times)[int(len(times)*.95)]:.1f} | max {max(times):.1f}")
    print(f"JS heap MB: start {m0} → end {m1} | DOM nodes: {n0} → {n1} | leftover overlays: {lt}")
    b.close()
