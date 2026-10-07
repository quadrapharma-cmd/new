from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); pg=ctx.new_page()
    cdp=ctx.new_cdp_session(pg); cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
    pg.add_init_script("window.__lt=[];new PerformanceObserver(l=>l.getEntries().forEach(e=>window.__lt.push(Math.round(e.duration)))).observe({entryTypes:['longtask']});")
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load',timeout=120000)
    pg.evaluate('endSplash()'); pg.wait_for_timeout(1500)
    pg.evaluate("window.__lt=[]"); pg.wait_for_timeout(4000)
    lt=pg.evaluate("window.__lt"); print('LOGIN idle 4s → long tasks:',len(lt),'total ms:',sum(lt))
    # stop the globe to see its share
    pg.evaluate("document.getElementById('lgGlobe').style.display='none'")
    t=pg.evaluate("(()=>{var t=performance.now();for(var i=0;i<3;i++);return 0})()")
    pg.evaluate("document.getElementById('loginEmail').value='haytham@drugbox.app';document.getElementById('loginPw').value='password123';doLogin()")
    pg.wait_for_timeout(5000)
    if pg.locator('.tour-skip').count(): pg.evaluate("document.querySelector('.tour-skip').click()")
    pg.evaluate("""(()=>{window.__runs={};var r=dxCore.run;dxCore.run=function(n,f,a){window.__runs[n]=(window.__runs[n]||0)+1;return r(n,f,a)};})()""")
    for page in ['feed','market','jobs']:
        pg.evaluate(f"goto('{page}')"); pg.wait_for_timeout(2500)
        pg.evaluate("window.__lt=[];window.__mut=0;window.__mo=new MutationObserver(l=>{window.__mut+=l.length});window.__mo.observe(document.body,{childList:true,subtree:true})")
        pg.wait_for_timeout(4000)
        lt=pg.evaluate("window.__lt"); print(f'[{page}] idle 4s → childList mutations: {pg.evaluate("window.__mut")} | long tasks: {len(lt)} total {sum(lt)}ms'); pg.evaluate("window.__mo.disconnect()")
    runs=pg.evaluate("window.__runs"); print('render-bus runs since hooks:', sum(runs.values()), json.dumps(dict(sorted(runs.items(),key=lambda x:-x[1])[:6])))
    who=pg.evaluate("""(()=>new Promise(res=>{var m={};var o=new MutationObserver(l=>l.forEach(x=>{var t=x.target;var k=(t.id?'#'+t.id:'')+'.'+String(t.className||'').split(' ')[0];m[k]=(m[k]||0)+1}));o.observe(document.body,{childList:true,subtree:true});setTimeout(()=>{o.disconnect();res(Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,8))},3000)}))()""")
    print('who adds nodes while idle (3s):', who)
    t=pg.evaluate("(()=>{var t=performance.now();goto('market');return Math.round(performance.now()-t)})()"); pg.wait_for_timeout(1500)
    print('goto(market) sync time at 4x slower CPU:', t, 'ms')
    lt=pg.evaluate("window.__lt"); print('long tasks right after goto(market):', lt[-5:])
    b.close()
