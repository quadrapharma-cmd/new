from playwright.sync_api import sync_playwright
import json, collections
AXE=open('/tmp/axe.min.js').read()
SCREENS=[('login',None),('home',"goto('feed')"),('marketplace',"goto('market')"),('directory',"goto('companies')"),('company page',"dxHub.page('quadra-pharm')"),
         ('workspace',"dxHub.workspace('quadra-pharm')"),('jobs',"goto('jobs')"),('messages',"goto('messages')"),('profile',"goto('profile')")]
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900})
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(900)
    agg=collections.defaultdict(lambda: {'impact':'','screens':set(),'nodes':0,'help':'','sample':''})
    for name, js in SCREENS:
        if name=='home':
            pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
            if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
        if js: pg.evaluate(js); pg.wait_for_timeout(600)
        pg.add_script_tag(content=AXE)
        res=pg.evaluate("axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']},resultTypes:['violations']}).then(r=>r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,n:v.nodes.length,t:v.nodes[0]&&v.nodes[0].target.join(' ')})))")
        for v in res:
            a=agg[v['id']]; a['impact']=v['impact']; a['screens'].add(name); a['nodes']+=v['n']; a['help']=v['help']; a['sample']=a['sample'] or (v['t'] or '')[:70]
    order={'critical':0,'serious':1,'moderate':2,'minor':3}
    for k,v in sorted(agg.items(), key=lambda x:(order.get(x[1]['impact'],9), -x[1]['nodes'])):
        print(f"{v['impact']:9s} {k:32s} {v['nodes']:4d} elements · {len(v['screens'])} screens · {v['help'][:60]} · e.g. {v['sample']}")
    json.dump({k:{**v,'screens':sorted(v['screens'])} for k,v in agg.items()}, open('/tmp/a11y_before.json','w'))
    b.close()
