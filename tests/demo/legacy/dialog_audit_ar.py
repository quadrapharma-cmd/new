from playwright.sync_api import sync_playwright
import sys, collections
DIALOGS={
 'rfq':"dxHub.page('medsinia-industries','products');setTimeout(function(){var b=document.querySelector('#dxDir [data-hrfq]');b&&b.click()},50)",
 'deals_center':"dxDeals.center('received')",
 'deal_thread':"(function(){if(!window.__dd){var d=dxDeals.create('quote','medsinia-industries','Audit deal',{qty:'2',unit:'MT'},'x');dxDeals.act(d.id,'quote',{price:'US$ 5.40 / kg',validity:'14 days'},'to');window.__dd=d.id}dxDeals.thread(window.__dd)})()",
 'health':"dxHub.health()",'create':"dxDir.create()",'verify':"dxDir.verify('quadra-pharm')",
 'qr':"dxHub.page('medsinia-industries');setTimeout(function(){var b=document.querySelector('#dxDir [data-hqr]');b&&b.click()},50)",
 'report':"dxHub.page('medsinia-industries');setTimeout(function(){var b=document.querySelector('#dxDir [data-hreport]');b&&b.click()},50)",
 'surplus':"dxDir3.surplusDialog()",'dossiers':"dxDir3.dossiersDialog()",'newgroup':"dxDir3.newGroup()",
 'molecule':"goto('market');dxMol.open('metformin')",'landed':"dxLanded({price:5.4,unit:'kg'})",
 'compare':"(function(){var g='GA';['medsinia-industries','obour-medica'].forEach(function(s){var d=dxDeals.create('quote',s,'Cmp',{qty:'1',unit:'kg'},'x',{group:g});if(d)dxDeals.act(d.id,'quote',{price:'US$ 5',validity:'14 days'},'to')});dxCompareQuotes(g)})()",
 'cmdk':"document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}))",
 'switcher':"goto('companies');setTimeout(function(){var b=document.getElementById('dxCoSwitch');b&&b.click()},50)",
 'boost':"goto('market');openBoostModal('boost')",
 'group':"goto('groups');openGroup('member')",
 'share':"dxHub.page('medsinia-industries','overview');setTimeout(function(){var b=document.querySelector('#dxDir .dx-sh-open');b&&b.click()},450)",
 'tradeshow':"dxShare.tradeShow(dxDir.bySlug('medsinia-industries'))",
 'adddoc':"dxHub.workspace('quadra-pharm','plan');setTimeout(function(){dxTiers.addDoc()},60)",
}
CONT=".dx-ts, .dbk-ov, #dxCmd.on, #dxCoMenu, #boostModalOverlay.show, #groupDetail.show, .modal-bg.show"
LIST="""(()=>{var c=[...document.querySelectorAll('%s')].filter(e=>e.offsetWidth>0).pop();if(!c)return [];var out=[],seen=new Set();
  c.querySelectorAll('button,a[href],[onclick],[role=button],[data-a],[data-t],[data-hopen],label.chip,.chip,[class*=tab],[class*=opt],li[data-i],.cm-item,[data-go]').forEach(function(e,i){var r=e.getBoundingClientRect();if(r.width<3||r.height<3||e.disabled)return;
   if(e.closest('input,select,textarea'))return;var k=(e.tagName+'|'+(e.textContent||'').trim().slice(0,30)+'|'+e.className).slice(0,120);if(seen.has(k))return;seen.add(k);e.setAttribute('data-dg',out.length);out.push({t:(e.textContent||e.getAttribute('aria-label')||'').trim().replace(/\\s+/g,' ').slice(0,40),tag:e.tagName,cls:String(e.className).slice(0,30)})});return out})()""" % CONT
SIG="""(()=>{var c=[...document.querySelectorAll('%s')].filter(e=>e.offsetWidth>0);var h=0;c.forEach(function(x){var s=x.innerHTML;for(var i=0;i<s.length;i+=3)h=(h*31+s.charCodeAt(i))|0});
  var t=document.querySelector('.dbk-toast,#toast');return [c.length,h,t?(t.textContent+t.className).slice(0,60):'',document.body.getAttribute('data-page'),location.hash,[...document.querySelectorAll('input:checked')].length,(document.activeElement||{}).id||'',document.querySelectorAll('.dbk-ov').length].join('|')})()""" % CONT
def close(pg):
    pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove());var m=document.getElementById('dxCoMenu');m&&m.remove();var c=document.getElementById('dxCmd');c&&c.classList.remove('on');var b=document.getElementById('boostModalOverlay');b&&b.classList.remove('show');document.querySelectorAll('.dx-ts').forEach(function(t){var x=t.querySelector('.dx-ts-x');x?x.click():t.remove()});typeof closeGroup==='function'&&closeGroup()")
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900}); ctx.add_init_script("try{localStorage.setItem('dx_lang','ar')}catch(e){}")
    ctx.route(lambda u: not u.startswith('file:') and not u.startswith('data:') and not u.startswith('blob:'), lambda r: r.abort())
    pg=ctx.new_page(); pops=[]; errs=[]; pg.on("dialog", lambda d: (pops.append(1), d.dismiss())); pg.on("filechooser", lambda f: pops.append(1)); pg.on("pageerror",lambda e:errs.append(str(e)[:120]))
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pg.evaluate("localStorage.setItem('dx_acting',JSON.stringify('quadra-pharm'))")
    ctx.on('page', lambda np: (pops.append(1), np.close()))
    names=sys.argv[1].split(',') if len(sys.argv)>1 else list(DIALOGS)
    for name in names:
        close(pg); pg.evaluate(DIALOGS[name]); pg.wait_for_timeout(900); items=pg.evaluate(LIST); dead=[]
        for i,it in enumerate(items[:40]):
            close(pg); pg.evaluate(DIALOGS[name]); pg.wait_for_timeout(800); pg.evaluate(LIST)
            loc=pg.locator(f'[data-dg="{i}"]')
            if not loc.count(): continue
            a=pg.evaluate(SIG); n0=len(pops)
            try: loc.first.click(timeout=1500, force=True)
            except Exception: continue
            pg.wait_for_timeout(550)
            if pg.evaluate(SIG)==a and len(pops)==n0: dead.append(it)
        print(f"{name:13s} controls {min(len(items),40):3d} | do nothing {len(dead)}", flush=True)
        for d in dead: print(f"      · {d['tag']} '{d['t']}' .{d['cls']}")
    close(pg); print('JS errors:', errs[:3] or 'none'); b.close()
