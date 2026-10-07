from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); pg=ctx.new_page()
    cdp=ctx.new_cdp_session(pg); cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
    pg.add_init_script("""window.__lt=[];new PerformanceObserver(l=>l.getEntries().forEach(e=>window.__lt.push(Math.round(e.duration)))).observe({entryTypes:['longtask']});""")
    t0=pg.evaluate("Date.now()") if False else None
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load',timeout=120000)
    print('load (4x slower CPU):', pg.evaluate("Math.round(performance.getEntriesByType('navigation')[0].loadEventEnd)"),'ms')
    pg.evaluate('endSplash()'); pg.wait_for_timeout(800); pg.click('.lg-demo'); pg.click('#loginPage .f-btn'); pg.wait_for_timeout(4500)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pg.evaluate("""(()=>{window.__runs={};var r=dxCore.run;dxCore.run=function(n,f,a){window.__runs[n]=(window.__runs[n]||0)+1;return r(n,f,a)};})()""")
    for page in ['feed','market']:
        pg.evaluate(f"goto('{page}')"); pg.wait_for_timeout(1500)
        pg.evaluate("window.__lt=[]; window.__mut=0; new MutationObserver(l=>{window.__mut+=l.length}).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true})")
        pg.evaluate("""(()=>{var n=0,t=performance.now();window.__frames=0;(function f(){window.__frames++;if(performance.now()-t<5000)requestAnimationFrame(f)})()})()""")
        pg.wait_for_timeout(5200)
        print(f'[{page}] idle 5s → DOM mutations: {pg.evaluate("window.__mut")} | long tasks: {pg.evaluate("window.__lt")} | frames: {pg.evaluate("window.__frames")}')
    print('render-bus runs during the whole session:', json.dumps(pg.evaluate("window.__runs")))
    # who mutates while idle?
    pg.evaluate("goto('feed')"); pg.wait_for_timeout(1200)
    who=pg.evaluate("""(()=>new Promise(res=>{var m={};var o=new MutationObserver(l=>l.forEach(x=>{var t=x.target,k=(t.id?'#'+t.id:'')+'.'+(t.className&&t.className.baseVal===undefined?String(t.className).split(' ')[0]:'')+':'+x.type;m[k]=(m[k]||0)+1}));o.observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true});setTimeout(()=>{o.disconnect();res(Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,8))},3000)}))()""")
    print('top mutating elements (3s idle on feed):', who)
    b.close()
