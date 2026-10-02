from playwright.sync_api import sync_playwright
import collections
AXE=open('/tmp/axe.min.js').read()
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900})
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(900)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pairs=collections.Counter(); scroll=set(); cmd=set()
    for js in ["goto('feed')","goto('market')","goto('companies')","dxHub.page('quadra-pharm')","dxHub.workspace('quadra-pharm')","goto('jobs')","goto('messages')","goto('profile')"]:
        pg.evaluate(js); pg.wait_for_timeout(500); pg.add_script_tag(content=AXE)
        r=pg.evaluate("""axe.run(document,{runOnly:{type:'rule',values:['color-contrast','scrollable-region-focusable','aria-command-name']}}).then(r=>r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({t:n.target.join(' '),d:(n.any[0]||{}).data||{}}))})))""")
        for v in r:
            for n in v['nodes']:
                if v['id']=='color-contrast': d=n['d']; pairs[(d.get('fgColor'),d.get('bgColor'),round(d.get('contrastRatio',0),2),d.get('expectedContrastRatio'), n['t'].split(' ')[-1][:40])]+=1
                elif v['id']=='scrollable-region-focusable': scroll.add(n['t'][:80])
                else: cmd.add(n['t'][:90])
    print('CONTRAST (fg, bg, ratio, needed, sample) × count:')
    for k,c in pairs.most_common(30): print('  ',c,'×',k)
    print('SCROLLABLE:', sorted(scroll)); print('COMMAND:', sorted(cmd))
    b.close()
