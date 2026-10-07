from playwright.sync_api import sync_playwright
PAGES=['feed','market','companies','company','jobs','network','messages','notifs','profile','groups','training','saved']
with sync_playwright() as p:
    for eng in [e for e in ('webkit','chromium') if e in __import__('os').environ.get('DX_ENGINES','webkit,chromium')][::-1]:   # DX_ENGINES: the browsers installed here
        b=(p.chromium.launch(args=["--no-sandbox"]) if eng=='chromium' else p.webkit.launch())
        pg=b.new_page(**(p.devices['Pixel 5'] if eng=='chromium' else p.devices['iPhone 12'])); pg.goto('file://'+__import__('os').environ.get('DEMO_VARIANTS','/tmp')+'/sanitized.html',wait_until='load'); pg.wait_for_timeout(500)
        tot=0; dead=[]; wrong=[]
        for k in PAGES:
            pg.evaluate(f"location.hash='#p-{k}'"); pg.wait_for_timeout(120)
            n=pg.evaluate(f"(()=>{{var s=document.getElementById('p-{k}');var els=[...s.querySelectorAll('.lm-c button,.lm-c [role=button],.lm-c a[href],.lm-c .hb-card')].filter(e=>{{var r=e.getBoundingClientRect();return r.width>4&&r.height>4}});window.__L=els;return els.length}})()")
            for i in range(min(n,40)):
                pg.evaluate(f"location.hash='#p-{k}'"); pg.wait_for_timeout(40)
                info=pg.evaluate(f"""(()=>{{var e=window.__L[{i}];e.scrollIntoView({{block:'center'}});var r=e.getBoundingClientRect();var x=r.left+Math.min(r.width/2,20),y=r.top+r.height/2;var hit=document.elementFromPoint(x,y);var a=hit&&hit.closest('a');return {{t:(e.textContent||'').trim().slice(0,26),mine:!!(a&&(a===e||e.contains(a))),href:a?a.getAttribute('href'):null}}}})()""")
                tot+=1
                if not info['href']: dead.append((k,info['t']))
                elif not info['mine']: wrong.append((k,info['t'],info['href']))
        print(f"{eng}: {tot} controls | tap does nothing: {len(dead)} {dead[:4]} | tap lands on another control: {len(wrong)} {wrong[:4]}")
        pg.evaluate("location.hash='#p-companies'"); pg.wait_for_timeout(150)
        pg.evaluate("location.hash='#p-companies'"); pg.wait_for_timeout(150); pg.locator('#p-companies .hb-card[data-slug=quadra-pharm] [data-hopen] .lx').first.click(force=True); pg.wait_for_timeout(200); a=pg.evaluate("location.hash")
        pg.evaluate("location.hash='#p-market'"); pg.wait_for_timeout(150); pg.locator('#p-market button .lx').first.click(); pg.wait_for_timeout(200); c=pg.evaluate("location.hash")
        print(f"   company card → {a} | a marketplace action → {c}")
        b.close()
