from playwright.sync_api import sync_playwright
F=[]  # findings
def check(name, ok, detail=''):
    print(('✅ ' if ok else '❌ ')+name+('' if ok else '  → '+str(detail)[:200]))
    if not ok: F.append(name)
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900}); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:200]))
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    E=pg.evaluate
    E("localStorage.setItem('dx_acting',JSON.stringify('quadra-pharm'))")
    # ── A · deals state machine
    E("window.__t=dxDeals.create('quote','medsinia-industries','Audit quote',{qty:'1',unit:'kg',inc:'CIF'},'x')")
    illegal=E("(()=>{var d=__t,r=[];['accept','confirm','ship','receive','rate'].forEach(a=>{r.push(a+':'+!!dxDeals.act(d.id,a,{},'from'))});['accept','rate','receive'].forEach(a=>{r.push('to-'+a+':'+!!dxDeals.act(d.id,a,{},'to'))});return r.filter(x=>x.endsWith('true'))})()")
    check('A1 no step can be skipped or done by the wrong side', illegal==[], illegal)
    E("dxDeals.act(__t.id,'quote',{price:'US$ 1'},'to');dxDeals.act(__t.id,'accept',{},'from');dxDeals.act(__t.id,'confirm',{},'to');dxDeals.act(__t.id,'ship',{},'to');dxDeals.act(__t.id,'receive',{ontime:'yes'},'from');dxDeals.act(__t.id,'rate',{stars:5},'from')")
    check('A2 happy path ends closed', E("dxDeals.get(__t.id).status")=='closed')
    again=E("!!dxDeals.act(__t.id,'rate',{stars:1},'from')")
    check('A3 a closed deal cannot be rated twice', not again)
    check('A4 rating counted once', E("(JSON.parse(localStorage.getItem('dx_supplier_reviews'))['medsinia-industries']||[]).filter(r=>r.deal===__t.id).length")==1)
    # ── B · self-dealing
    self_q=E("(()=>{var d=dxDeals.create('quote','quadra-pharm','Self quote',{},'x');return d&&d.from.slug===d.to.slug})()")
    check('B1 a company cannot send a quote request to itself', not self_q)
    self_s=E("(()=>{var n=dxDeals.all().length;dxDir3.surplusOffer(dxDir3.surplus().find(s=>s.slug==='quadra-pharm'));return dxDeals.all().length===n})()")
    check('B2 a company cannot make an offer on its own surplus', self_s)
    E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    self_g=E("(()=>{var d=dxDeals.mk('group',{slug:'quadra-pharm',name:'Quadra Pharm'},'quadra-pharm','G',{product:'x',target:10,unit:'kg'},'');return d.from.slug===d.to.slug})()")
    # group self-supply is only reachable via the new-group dialog: check the dialog excludes the acting company
    E("dxDir3.newGroup()"); pg.wait_for_timeout(200)
    own_in_list=E("!!document.querySelector('.dbk-ov #ngS option[value=\"quadra-pharm\"]')")
    E("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    check('B3 a buying group cannot name your own company as its supplier', not own_in_list)
    own_dossier=E("(()=>{var n=dxDeals.all().length;var d=dxDir3.dossiers().find(x=>x.slug==='quadra-pharm');dxDeals.create('dossier',d.slug,d.product,{},'x');return dxDeals.all().length>n && dxDeals.all()[0].from.slug===dxDeals.all()[0].to.slug})()")
    check('B4 a company cannot request its own dossier', not own_dossier)
    # bulk request that includes your own company
    E("dxDir.S.view=null;goto('companies')"); pg.wait_for_timeout(300)
    own_pick=E("!!document.querySelector('#dxDir .hb-card[data-slug=\"quadra-pharm\"] [data-hpick]')")
    check('B5 your own company cannot be selected for a multi-company request', not own_pick)
    # ── C · groups
    gid=E("dxDir3.groupDeals()[0].id")
    E(f"(()=>{{var g=dxDeals.get('{gid}');dxDeals.joinGroup('{gid}',{{slug:'quadra-pharm',name:'Quadra Pharm'}},g.lines.target)}})()")
    E(f"dxDeals.act('{gid}','confirm_group',{{}},'to')")
    n1=E(f"dxDeals.all().filter(d=>d.groupOf==='{gid}').length")
    again=E(f"!!dxDeals.act('{gid}','confirm_group',{{}},'to')"); n2=E(f"dxDeals.all().filter(d=>d.groupOf==='{gid}').length")
    check('C1 confirming a group twice does not duplicate orders', (not again) and n1==n2, (n1,n2))
    late=E(f"!!dxDeals.joinGroup('{gid}',{{slug:'medsinia-industries',name:'Medsinia'}},5)")
    check('C2 nobody can join a confirmed group', not late)
    neg=E("(()=>{var g=dxDir3.groupDeals().find(x=>x.status==='open');if(!g)return 'no open group';var before=dxDir3.total(g);dxDeals.joinGroup(g.id,{slug:'medsinia-industries',name:'M'},-500);return dxDir3.total(dxDeals.get(g.id))<before})()")
    check('C3 a negative quantity cannot reduce a group', neg is False or neg=='no open group', neg)
    # ── D · questionnaire → vendor list
    q=E("dxDeals.create('questionnaire','alex-excipients','Q',{},'x',{answers:[['S',[{q:'a',a:'b',src:'x'}]]]}).id")
    E(f"dxDeals.act('{q}','answer',{{}},'to');dxDeals.act('{q}','reject',{{}},'from')")
    check('D1 rejecting a questionnaire marks the supplier suspended', E("JSON.parse(localStorage.getItem('dx_avl_quadra-pharm'))['alex-excipients'].status")=='suspended')
    # ── E · track record
    tr=E("dxHubData.track('medsinia-industries')")
    check('E1 track record counts the completed order', tr['orders']>=1 and tr['rating'] is not None)
    none=E("dxHubData.track('giza-bioequivalence')")
    check('E2 a company with no deals shows no invented numbers', none['orders']==0 and none['rating'] is None and none['ontime'] is None)
    # ── F · quotes & validity
    v=E("(()=>{var d=dxDeals.create('quote','delta-analytical-labs','Validity',{},'x');dxDeals.act(d.id,'quote',{price:'US$ 9',validity:'7 days'},'to');var x=dxDeals.get(d.id);x.updated=Date.now()-10*864e5;x.events[x.events.length-1].at=Date.now()-10*864e5;dxDeals.save(x);return !!dxDeals.act(d.id,'accept',{},'from')})()")
    check('F1 an expired quote (7 days, 10 days old) cannot be accepted', not v)
    # ── G · routing
    r=E("dxHubData.route('quadra-pharm','job')")
    check('G1 routing returns a person for every request type', all(E(f"!!dxHubData.route('quadra-pharm','{t}').name") for t in ['quote','surplus','group','service','questionnaire','dossier','job']))
    # ── H · identity & verification
    E("(()=>{var e=JSON.parse(localStorage.getItem('dx_company_edits')||'{}');e['nile-valley-pharma']={owner:777,status:'unverified',claimed:true};localStorage.setItem('dx_company_edits',JSON.stringify(e))})()")
    E("dxDir.S.view=null;dxHub.page('nile-valley-pharma')"); pg.wait_for_timeout(300)
    check('H1 a page claimed by someone else offers no claim button', E("!document.querySelector('#dxDir [data-hclaim]')"))
    check('H2 someone else\u2019s workspace cannot be opened', E("(()=>{dxHub.workspace('nile-valley-pharma');return !document.querySelector('#dxDir.ws')||document.querySelector('#dxDir .ws-h')===null})()"))
    print('\nJS errors:', errs or 'none'); print('FINDINGS:', F); b.close()
