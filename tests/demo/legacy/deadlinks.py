from playwright.sync_api import sync_playwright
import sys, json, hashlib
PAGES=sys.argv[1].split(',')
GO={'feed':"goto('feed')",'market':"goto('market')",'companies':"goto('companies')",'company':"dxHub.page('medsinia-industries')",'workspace':"dxHub.workspace('quadra-pharm')",
    'jobs':"goto('jobs')",'network':"goto('network')",'groups':"goto('groups')",'messages':"goto('messages')",'notifs':"goto('notifs')",'profile':"goto('profile')",'training':"goto('training')",'saved':"goto('saved')"}
SIG="""(()=>{var c=document.getElementById('content');var ov=[...document.querySelectorAll('.dbk-ov,.modal-bg.show,.modal.show,[class*=modal][class*=show],[class*=overlay].show,.show[role=dialog],#dxCmd.on,#dxEditor,#dxCoMenu,.dx-pop,#dxHover.on,#dxTerm.on')].filter(e=>e.offsetWidth>0).length;
 var t=document.querySelector('.dbk-toast,#toast,.toast');var dock=document.getElementById('dxDock');
 var h=0,s=c?c.innerHTML:'';for(var i=0;i<s.length;i+=7)h=(h*31+s.charCodeAt(i))|0;
 return [document.body.getAttribute('data-page'),location.hash,ov,t?(t.className+t.textContent).slice(0,60)+(t.offsetWidth>0):'',dock?dock.innerHTML.length:0,h,Math.round((c||{}).scrollTop||0),document.querySelectorAll('.show,.open,.active,.on,.expanded,.checked').length,(document.activeElement||{}).tagName].join('|')})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900})
    ctx.route(lambda u: not u.startswith('file:') and not u.startswith('data:') and not u.startswith('blob:'), lambda r: r.abort())
    newpages=[]
    pg=ctx.new_page(); pg.on("dialog", lambda d: (newpages.append(1), d.dismiss()))
    ctx.on('page', lambda np: (newpages.append(1), np.close()))
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pg.evaluate("localStorage.setItem('dx_tour_done','1')")
    report={}
    def relog():
        if pg.evaluate("document.getElementById('app').offsetWidth===0"):
            pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
            if pg.locator('.lg-demo').is_visible(): pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2500)
    for name in PAGES:
        relog(); pg.evaluate(GO[name]); pg.wait_for_timeout(600)
        items=pg.evaluate("""(()=>{var seen=new Set(),out=[];document.querySelectorAll('#content a[href],#content button,#content [onclick],#content [role=button],#content .hb-card,#content label.chip,#content [data-tab],.topbar a,.topbar button,#sidebar a,#sidebar button,#sidebar [onclick]').forEach((e,i)=>{
            var r=e.getBoundingClientRect(); if(r.width<2||r.height<2) return; if(e.disabled) return;
            var key=(e.tagName+'|'+(e.getAttribute('onclick')||e.getAttribute('href')||'')+'|'+(e.textContent||'').trim().slice(0,40)+'|'+e.className).slice(0,160);
            if(seen.has(key)) return; seen.add(key); e.setAttribute('data-dl',out.length); out.push({k:key,t:(e.textContent||e.getAttribute('aria-label')||e.getAttribute('title')||'').trim().replace(/\\s+/g,' ').slice(0,50),tag:e.tagName,href:e.getAttribute('href')||'',oc:(e.getAttribute('onclick')||'').slice(0,60),cls:String(e.className).slice(0,50)})});return out})()""")
        dead=[]
        for i,it in enumerate(items[:140]):
            if it['href'] and (it['href'].startswith('http') or it['href'].startswith('tel:') or it['href'].startswith('mailto:')): continue
            if 'logout' in (it['oc']+it['k']).lower() or 'sign out' in it['t'].lower() or 'log out' in it['t'].lower(): continue
            try:
                loc=pg.locator(f'[data-dl="{i}"]')
                if not loc.count(): 
                    pg.evaluate(GO[name]); pg.wait_for_timeout(300)
                    pg.evaluate(f"""(()=>{{var e=[...document.querySelectorAll('*')].find(x=>x.getAttribute('data-dl')==='{i}');}})()""")
                    continue
                before=pg.evaluate(SIG); np0=len(newpages)
                loc.first.scroll_into_view_if_needed(timeout=1500)
                before=pg.evaluate(SIG)
                loc.first.click(timeout=1500, force=True); pg.wait_for_timeout(280)
                after=pg.evaluate(SIG)
                if before==after and len(newpages)==np0: dead.append(it)
                # restore
                pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove());var m=document.getElementById('dxEditor');m&&m.remove()")
                if pg.evaluate("document.body.getAttribute('data-page')")!=(name if name not in ('company','workspace') else 'companies') or (name in('company','workspace') and not pg.evaluate("!!document.querySelector('#dxDir.cp, #dxDir.ws')")):
                    pg.evaluate(GO[name]); pg.wait_for_timeout(350)
                    items2=pg.evaluate("""(()=>{var seen=new Set(),n=0;document.querySelectorAll('#content a[href],#content button,#content [onclick],#content [role=button],#content .hb-card,#content label.chip,#content [data-tab],.topbar a,.topbar button,#sidebar a,#sidebar button,#sidebar [onclick]').forEach(e=>{var r=e.getBoundingClientRect(); if(r.width<2||r.height<2||e.disabled) return; var key=(e.tagName+'|'+(e.getAttribute('onclick')||e.getAttribute('href')||'')+'|'+(e.textContent||'').trim().slice(0,40)+'|'+e.className).slice(0,160); if(seen.has(key)) return; seen.add(key); e.setAttribute('data-dl',n++)});return n})()""")
            except Exception as ex:
                pass
        report[name]={'checked':min(len(items),140),'dead':dead}
        print(f"{name:10s} checked {min(len(items),140):3d} | inactive {len(dead)}")
        for d in dead[:40]: print(f"      · {d['tag']:6s} '{d['t'][:45]}'  onclick={d['oc'][:40]!r} href={d['href'][:30]!r} cls={d['cls'][:35]!r}")
    json.dump(report, open('/tmp/dead_'+sys.argv[1].replace(',','_')+'.json','w'))
    b.close()
