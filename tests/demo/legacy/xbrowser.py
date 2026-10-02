from playwright.sync_api import sync_playwright
import time
STEPS=["goto('feed')","goto('market')","goto('companies')","dxHub.page('quadra-pharm')","dxHub.page('quadra-pharm','sites')","dxHub.workspace('quadra-pharm')","dxHub.workspace('quadra-pharm','team')",
       "goto('jobs')","goto('network')","goto('groups')","goto('messages')","goto('notifs')","goto('profile')","goto('training')","goto('saved')"]
MATRIX=[('chromium','Desktop 1440',{'viewport':{'width':1440,'height':900}}),('firefox','Desktop 1440',{'viewport':{'width':1440,'height':900}}),('webkit','Desktop 1440',{'viewport':{'width':1440,'height':900}}),
        ('chromium','Laptop 1280',{'viewport':{'width':1280,'height':720}}),('firefox','Tablet 820',{'viewport':{'width':820,'height':1180}}),('webkit','iPad Mini','iPad Mini'),
        ('webkit','iPhone SE','iPhone SE'),('webkit','iPhone 12','iPhone 12'),('chromium','Pixel 5','Pixel 5'),('chromium','Galaxy S9+','Galaxy S9+'),('firefox','Phone 360',{'viewport':{'width':360,'height':740},'is_mobile':False})]
with sync_playwright() as p:
    for eng, label, dev in MATRIX:
        L=getattr(p,eng); b=L.launch(args=["--no-sandbox"]) if eng=='chromium' else L.launch()
        opts=p.devices[dev] if isinstance(dev,str) else dev
        if eng=='firefox' and isinstance(dev,dict): opts={k:v for k,v in dev.items() if k!='is_mobile'}
        ctx=b.new_context(**opts); pg=ctx.new_page(); errs=[]
        pg.on("pageerror",lambda e:errs.append(str(e)[:120])); pg.on("dialog", lambda d: d.dismiss())
        t0=time.time(); pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); t_load=time.time()-t0; pg.wait_for_timeout(400)
        pg.click('#splash'); pg.wait_for_timeout(900); pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3000)
        if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
        over=[]; slow=[]
        for s in STEPS:
            t=time.time(); pg.evaluate(s); dt=(time.time()-t)*1000; pg.wait_for_timeout(250)
            if dt>400: slow.append((s,int(dt)))
            if pg.evaluate("document.getElementById('content').scrollWidth-document.getElementById('content').clientWidth")>2: over.append(s)
        ok=pg.evaluate("document.getElementById('app').offsetWidth>0")
        print(f"{eng:8s} {label:13s} load {t_load:4.1f}s | app {'OK' if ok else 'FAIL'} | pages {len(STEPS)-len(over)}/{len(STEPS)} fit | slow {slow or 'none'} | errors {errs[:2] or 'none'}")
        b.close()
