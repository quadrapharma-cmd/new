from playwright.sync_api import sync_playwright
import random, sys, collections
SEED=int(sys.argv[1]); N=int(sys.argv[2]); MODE=sys.argv[3]
random.seed(SEED)
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"])
    ctx=b.new_context(**(p.devices['Pixel 5'] if MODE=='phone' else {'viewport':{'width':1440,'height':900}}))
    ctx.route(lambda u: not u.startswith('file:') and not u.startswith('data:') and not u.startswith('blob:'), lambda r: r.abort())
    pg=ctx.new_page(); errs=collections.Counter(); ctx.on('page', lambda np: np.close())
    pg.on("pageerror",lambda e:errs.update([str(e)[:140]])); pg.on("dialog", lambda d: d.dismiss())
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pages=['feed','market','companies','jobs','network','groups','messages','notifs','profile','training','saved']
    clicks=0; relog=0
    for i in range(N):
        try:
            if pg.evaluate("document.getElementById('app').offsetWidth===0"):
                relog+=1; pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
                if pg.locator('.lg-demo').is_visible(): pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2500)
                continue
            if i % 60 == 0: pg.evaluate(f"goto('{random.choice(pages)}')"); pg.wait_for_timeout(120)
            n=pg.evaluate("""(()=>{var els=[...document.querySelectorAll('button,a[href],[onclick],label,.hb-card,.dl-row,input[type=checkbox],select')].filter(e=>{var r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.bottom>0&&r.top<innerHeight&&!/logout|sign ?out/i.test(e.textContent||'')&&!e.closest('#dxCoMenu [data-cs-new]')});window.__mk=els;return els.length})()""")
            if not n: continue
            k=random.randrange(n)
            pg.evaluate(f"(()=>{{var e=window.__mk[{k}];if(e.tagName==='SELECT'){{if(e.options.length){{e.selectedIndex=Math.floor(Math.random()*e.options.length);e.dispatchEvent(new Event('change',{{bubbles:true}}))}}}}else if(e.tagName==='A'&&/^https?:|^mailto:|^tel:/.test(e.getAttribute('href')||'')){{}}else e.click()}})()")
            clicks+=1
            if random.random()<0.08: pg.keyboard.press('Escape')
            if random.random()<0.05:
                ins=pg.locator('input[type=text]:visible, textarea:visible, input:not([type]):visible')
                if ins.count(): ins.nth(random.randrange(ins.count())).fill(random.choice(['Metformin','ميتفورمين','test <b>x</b>','0','-5','9999999','   ']))
            pg.wait_for_timeout(35)
        except Exception as e:
            errs.update(['driver: '+str(e)[:100]])
    stuck=pg.evaluate("[...document.querySelectorAll('.dbk-ov')].length")
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    heap=pg.evaluate("performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null")
    print(f'{MODE} seed {SEED}: {clicks} random actions | re-logins {relog} | JS errors {sum(v for k,v in errs.items() if not k.startswith("driver"))} | open dialogs at end {stuck} | heap {heap} MB')
    for k,v in errs.most_common(6): print('   ', v, '×', k)
    b.close()
