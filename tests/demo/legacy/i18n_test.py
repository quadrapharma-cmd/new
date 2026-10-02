from playwright.sync_api import sync_playwright
import collections, json
PAGES=[('home',"goto('feed')"),('market',"goto('market')"),('directory',"goto('companies')"),('company',"dxHub.page('quadra-pharm')"),('workspace',"dxHub.workspace('quadra-pharm')"),
       ('jobs',"goto('jobs')"),('network',"goto('network')"),('groups',"goto('groups')"),('messages',"goto('messages')"),('notifs',"goto('notifs')"),('profile',"goto('profile')"),('saved',"goto('saved')")]
LEFT=r"""(()=>{var skip='script,style,svg,input,textarea,[contenteditable],.post-body,.post-text,.pb-text,.msg-text,.bubble,.mx-msg,.cmt-text,.dx-entity,.post-name,.sugg-name,.dr-card h3,.hb-card h3,.cp-name,.dr-name,.lc-title,.sp-title,.sc-title,.jc-title,.gcard-title,.gcard-desc,.mg-name,.profile-name,.dl-title,.dx-mine-name,[data-noi18n],#dxStaticWrap';
  var names=new Set((window.USERS||[]).map(u=>u.name).concat(window.dxDir?dxDir.companies().map(c=>c.name):[]));
  var ui=0,en=0,left=[];var w=document.createTreeWalker(document.getElementById('app'),NodeFilter.SHOW_TEXT,{acceptNode:n=>{var p=n.parentElement;if(!p||p.closest(skip))return 2;var r=p.getBoundingClientRect();if(r.width<1||r.bottom<0)return 2;var t=n.nodeValue.trim();if(t.length<2||names.has(t))return 2;return 1}});
  while(w.nextNode()){var t=w.currentNode.nodeValue.replace(/\s+/g,' ').trim();if(!/[A-Za-z\u0600-\u06FF]/.test(t))continue;ui++;if(/[A-Za-z]{3}/.test(t)&&!/[\u0600-\u06FF]/.test(t)){en++;left.push(t)}}
  return {ui:ui,en:en,left:left}})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900}); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:150]))
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pg.evaluate("goto('feed')"); pg.wait_for_timeout(400)
    en_before=pg.evaluate("document.getElementById('app').innerText")
    pg.evaluate("toggleLang()"); pg.wait_for_timeout(500)
    print('dir:', pg.evaluate("document.documentElement.dir"), '| lang:', pg.evaluate("document.documentElement.lang"))
    allleft=collections.Counter(); T=E=0
    for name,js in PAGES:
        pg.evaluate(js); pg.wait_for_timeout(600)
        r=pg.evaluate(LEFT); T+=r['ui']; E+=r['en']; allleft.update(r['left'])
        ov=pg.evaluate("document.getElementById('content').scrollWidth-document.getElementById('content').clientWidth")
        print(f"{name:10s} interface texts {r['ui']:4d} | still English {r['en']:4d} ({100*r['en']//max(1,r['ui'])}%) | sideways overflow {ov}")
    print(f'TOTAL {T} | still English {E} ({100*E//max(1,T)}%)')
    pg.evaluate("goto('feed')"); pg.wait_for_timeout(400); pg.evaluate("toggleLang()"); pg.wait_for_timeout(500)
    en_after=pg.evaluate("document.getElementById('app').innerText")
    print('back to English — identical text:', en_before==en_after, '| dir:', pg.evaluate("document.documentElement.dir"))
    json.dump(allleft.most_common(), open('/tmp/i18n_left.json','w'), ensure_ascii=False)
    print('errors:', errs or 'none'); b.close()
