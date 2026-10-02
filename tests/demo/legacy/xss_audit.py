from playwright.sync_api import sync_playwright
P='<img src=x onerror="window.__xss=(window.__xss||[]).concat(\'HIT\')">'
Q='"><svg onload="window.__xss=(window.__xss||[]).concat(\'Q\')">'
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900}); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.dismiss())
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    E=pg.evaluate
    E("localStorage.setItem('dx_acting',JSON.stringify('quadra-pharm'))")
    # plant hostile text in every user-controlled field we store
    E("""([p,q])=>{
      var e=JSON.parse(localStorage.getItem('dx_company_edits')||'{}');
      e['quadra-pharm']=Object.assign({},e['quadra-pharm']||{},{tagline:p,about:p+q,nameAr:p,phone:p,email:q,website:q,address:p,hours:p,services:[p,q],
        products:[{id:'px',name:p,cat:q,kind:'box',desc:p,moq:q,price:p,api:p,specs:[p+':'+q]}], looking:[p,q],
        team:[{uid:1,name:'Dr. Haytham Dweedar',role:'Admin',consent:true},{uid:null,name:p,role:'Sales',consent:true}],
        sites:[{id:'s',name:p,type:'Factory',city:q,gov:'Giza',certs:[{name:p,expiry:'2027-01',src:q}],cap:{forms:[p],minBatch:q,capacity:p,slots:[0]}}]});
      localStorage.setItem('dx_company_edits',JSON.stringify(e));
      var r=JSON.parse(localStorage.getItem('dx_reports')||'[]');r.unshift({id:'Rx',slug:'quadra-pharm',section:p,text:p,fix:q,by:p,at:Date.now(),status:'open'});localStorage.setItem('dx_reports',JSON.stringify(r));
      var d=dxDeals.create('quote','medsinia-industries',p,{qty:p,unit:q,inc:p,to:q,by:p},p+q);
      dxDeals.act(d.id,'quote',{price:p,validity:'14 days',terms:q,lead:p,note:q},'to');
      dxDeals.act(d.id,'counter',{price:q,note:p},'from');
      var rv=JSON.parse(localStorage.getItem('dx_supplier_reviews')||'{}');(rv['quadra-pharm']=rv['quadra-pharm']||[]).push({stars:4,note:p,from:q,at:Date.now(),deal:'DX'});localStorage.setItem('dx_supplier_reviews',JSON.stringify(rv));
      var rm=JSON.parse(localStorage.getItem('dx_review_meta')||'{}');rm['DX']={reply:p+q};localStorage.setItem('dx_review_meta',JSON.stringify(rm));
      var s=JSON.parse(localStorage.getItem('dx_surplus_new')||'[]');s.unshift({id:'sx',slug:'medsinia-industries',product:p,qty:q,batch:p,expiry:q,price:p,off:10});localStorage.setItem('dx_surplus_new',JSON.stringify(s));
      var ds=JSON.parse(localStorage.getItem('dx_dossiers')||'[]');ds.unshift({id:'dx1',slug:'medsinia-industries',product:p,status:q,deal:p,markets:q});localStorage.setItem('dx_dossiers',JSON.stringify(ds));
      dxHubData.log('quadra-pharm',p+q);
    }""", [P,Q])
    hits={}
    def look(where):
        pg.wait_for_timeout(250); x=E("window.__xss||[]")
        if x: hits[where]=len(x); E("window.__xss=[]")
    screens=[("directory","dxDir.S.view=null;goto('companies')"),("directory search",None),("company overview","dxHub.page('quadra-pharm','overview')"),
      ("company products","dxHub.page('quadra-pharm','products')"),("company sites","dxHub.page('quadra-pharm','sites')"),("company listings","dxHub.page('medsinia-industries','listings')"),
      ("company reviews","dxHub.page('quadra-pharm','reviews')"),("company contact","dxHub.page('quadra-pharm','contact')")]
    for w,js in screens:
        if js: E(js)
        else: pg.fill('#hbQ', Q); pg.wait_for_timeout(500)
        look(w)
    for t in ['overview','page','sites','team','deals','suppliers','listings','reports','activity','plan']:
        E(f"dxHub.workspace('quadra-pharm','{t}')"); look('workspace '+t)
    E("dxDeals.center('sent')"); look('deals centre'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("dxDeals.thread(dxDeals.all()[0].id)"); look('deal page'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("dxDir3.surplusDialog()"); look('surplus dialog'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("dxDir3.dossiersDialog()"); look('dossiers dialog'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("goto('market')"); pg.wait_for_timeout(600); look('marketplace listings')
    E("goto('feed')"); pg.wait_for_timeout(500); look('home')
    pg.keyboard.press('Control+k'); pg.keyboard.type(Q); look('Ctrl+K search'); pg.keyboard.press('Escape')
    pg.fill('#searchIn', Q) if pg.locator('#searchIn').count() else None; look('top search')
    E("goto('companies')"); pg.wait_for_timeout(300); E("dxHub.health()"); look('health panel'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    E("dxHub.page('quadra-pharm')"); pg.wait_for_timeout(300); pg.click('#dxDir [data-hqr]') if pg.locator('#dxDir [data-hqr]').count() else None; look('QR dialog'); E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    print('XSS hits by screen:', hits or 'NONE'); print('JS errors:', errs[:5] or 'none'); b.close()
