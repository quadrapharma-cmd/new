from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); pg=ctx.new_page()
    cdp=ctx.new_cdp_session(pg); cdp.send('Emulation.setCPUThrottlingRate',{'rate':4})
    pg.add_init_script("window.__lt=[];new PerformanceObserver(l=>l.getEntries().forEach(e=>window.__lt.push(Math.round(e.duration)))).observe({entryTypes:['longtask']});")
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load',timeout=120000)
    pg.evaluate('endSplash()'); pg.wait_for_timeout(1500)
    pg.evaluate("window.__lt=[]"); pg.wait_for_timeout(4000)
    lt=pg.evaluate("window.__lt"); print('LOGIN idle 4s (4x slower CPU) → long tasks:',len(lt),'total ms:',sum(lt))
    t=pg.evaluate("(()=>{var t=performance.now();document.querySelector('.lg-demo').click();return Math.round(performance.now()-t)})()"); print('demo-box tap handled in:',t,'ms')
    pg.evaluate("doLogin()"); pg.wait_for_timeout(5000)
    if pg.locator('.tour-skip').count(): pg.evaluate("document.querySelector('.tour-skip').click()")
    pg.evaluate("window.__lt=[]"); pg.wait_for_timeout(3000); lt=pg.evaluate("window.__lt"); print('APP idle 3s → long tasks:',len(lt),sum(lt),'ms (globe must be stopped)')
    res=[]
    for page in ['market','jobs','feed','groups','profile','market']:
        pg.evaluate("window.__lt=[]")
        t=pg.evaluate(f"(()=>{{var t=performance.now();goto('{page}');return Math.round(performance.now()-t)}})()"); pg.wait_for_timeout(1800)
        lt=pg.evaluate("window.__lt"); res.append((page,t,max(lt) if lt else 0,sum(lt)))
    for r in res: print(f'  goto {r[0]:8s} sync {r[1]:4d} ms | longest task after {r[2]:4d} ms | total {r[3]} ms')
    top=sorted(pg.evaluate("dxCore.perf").items(),key=lambda x:-x[1]['ms'])[:6]
    print('heaviest features (4x slower CPU):',[(k,round(v['ms']),v['runs'],round(v['max'])) for k,v in top])
    b.close()
