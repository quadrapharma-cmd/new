from playwright.sync_api import sync_playwright
import sys, json, collections
PAGES=sys.argv[1].split(',')
GO={'co_overview':"dxHub.page('medsinia-industries','overview')",'co_products':"dxHub.page('medsinia-industries','products')",'co_sites':"dxHub.page('medsinia-industries','sites')",
    'co_listings':"dxHub.page('medsinia-industries','listings')",'co_jobs':"dxHub.page('medsinia-industries','jobs')",'co_reviews':"dxHub.page('quadra-pharm','reviews')",'co_contact':"dxHub.page('medsinia-industries','contact')",
    'ws_overview':"dxHub.workspace('quadra-pharm','overview')",'ws_page':"dxHub.workspace('quadra-pharm','page')",'ws_sites':"dxHub.workspace('quadra-pharm','sites')",'ws_team':"dxHub.workspace('quadra-pharm','team')",
    'ws_deals':"dxHub.workspace('quadra-pharm','deals')",'ws_suppliers':"dxHub.workspace('quadra-pharm','suppliers')",'ws_listings':"dxHub.workspace('quadra-pharm','listings')",
    'ws_reports':"dxHub.workspace('quadra-pharm','reports')",'ws_activity':"dxHub.workspace('quadra-pharm','activity')",'ws_plan':"dxHub.workspace('quadra-pharm','plan')",'feed':"goto('feed')",'market':"goto('market')",'companies':"goto('companies')",'company':"dxHub.page('medsinia-industries')",'jobs':"goto('jobs')",'network':"goto('network')",
    'groups':"goto('groups')",'messages':"goto('messages')",'notifs':"goto('notifs')",'profile':"goto('profile')",'training':"goto('training')",'saved':"goto('saved')"}
FIND=r"""(()=>{
  var names=(window.USERS||[]).map(u=>u.name), cos=window.dxDir?dxDir.companies().map(c=>c.name):[];
  var LINKY=/(^|\s)(tag|chip|pill|hashtag|trend|ad|ads|sponsor|promo|banner|name|title|link|more|see-?all|view-?all|author|company|seller|brand|topic|kw|badge|cta|headline|stat|count|meta-link|sug|who|person|user|member|item-name|job-t|jc-title|lc-title|sp-title|sc-title|dc-title|gcard-title|post-name|seller-name)(\s|-|_|$)/i;
  var seen=new Set(), out=[], i=+(document.body.getAttribute('data-afn')||0);
  var roots=[document.getElementById('content'),document.getElementById('sidebar'),document.querySelector('.topbar')].filter(Boolean);
  roots.forEach(function(root){ root.querySelectorAll('*').forEach(function(e){
    var r=e.getBoundingClientRect(); if(r.width<3||r.height<3) return;
    if(e.closest('input,textarea,select,svg,.dx-ic,#dxDock,.dbk-ov')) return;
    var cs=getComputedStyle(e), own=[...e.childNodes].some(n=>n.nodeType===3&&n.nodeValue.trim().length>1);
    var t=(e.textContent||'').trim().replace(/\s+/g,' ');
    var why='';
    if(cs.cursor==='pointer') why='pointer cursor';
    else if(e.tagName==='A') why='link';
    else if(own && LINKY.test(e.className||'')) why='looks like '+String(e.className).split(' ')[0];
    else if(own && t.length<60 && (names.indexOf(t)>=0||cos.indexOf(t)>=0)) why='name';
    else if(own && /^#\w/.test(t) && t.length<40) why='hashtag';
    if(!why) return;
    if(e.parentElement && out.length && e.parentElement.getAttribute('data-af')!=null && getComputedStyle(e.parentElement).cursor==='pointer' && why==='pointer cursor') return;   /* child of an already-listed clickable */
    if(e.hasAttribute('data-af')) return;   /* keep the first numbering */
    var key=(e.tagName+'|'+t.slice(0,40)+'|'+String(e.className).slice(0,40)); if(seen.has(key)) return; seen.add(key);
    e.setAttribute('data-af',i); out.push({i:i++,why:why,t:t.slice(0,48),tag:e.tagName,cls:String(e.className).slice(0,40),side:!!e.closest('.side-col,.right-col,.rcol,.sidebar-right,.feed-side,aside,[class*=side],[class*=widget],[class*=rail]')});
  });});
  document.body.setAttribute('data-afn',i); return out;})()"""
SIG="""(()=>{var c=document.getElementById('content');var ov=[...document.querySelectorAll('.dbk-ov,.modal-bg.show,[class*=modal].show,[class*=overlay].show,#dxCmd.on,#dxEditor,#dxCoMenu,#dxHover.on,#dxTerm.on,.dx-pop')].filter(e=>e.offsetWidth>0).length;
 var t=document.querySelector('.dbk-toast,#toast');var h=0,s=c?c.innerHTML:'';for(var i=0;i<s.length;i+=5)h=(h*31+s.charCodeAt(i))|0;
 return [document.body.getAttribute('data-page'),location.hash,ov,t?(t.textContent+t.className).slice(0,50):'',h,(document.getElementById('dxDock')||{}).innerHTML?.length||0,Math.round((c||{}).scrollTop||0),[...document.querySelectorAll('#content input:checked')].length,[...document.querySelectorAll('#content *')].filter(e=>e.offsetParent).length,document.documentElement.dir].join('|')})()"""
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); ctx=b.new_context(viewport={'width':1440,'height':900})
    ctx.route(lambda u: not u.startswith('file:') and not u.startswith('data:') and not u.startswith('blob:'), lambda r: r.abort())
    pg=ctx.new_page(); pops=[]; pg.on("dialog", lambda d: (pops.append(1), d.dismiss())); pg.on("filechooser", lambda f: pops.append(1)); ctx.on('page', lambda np: (pops.append(1), np.close()))
    pg.goto('file://'+__import__('os').environ.get('DEMO_FILE','/tmp/drugbox_brand.html'),wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(3200)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    summary={}
    for name in PAGES:
        if pg.evaluate("document.getElementById('app').offsetWidth===0"): pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2500)
        pg.evaluate(GO[name]); pg.wait_for_timeout(700)
        items=pg.evaluate(FIND); dead=[]
        pri=[x for x in items if x['side'] or x['why']!='pointer cursor' or x['tag'] not in ('BUTTON',)]
        rest=[x for x in items if x not in pri]
        pick=pri[:170]
        if len(pick)<170 and rest: step=max(1,len(rest)//(170-len(pick))); pick+=rest[::step][:170-len(pick)]
        total=len(items)
        for it in pick:
            if 'logout' in it['t'].lower() or 'sign out' in it['t'].lower(): continue
            try:
                loc=pg.locator(f'[data-af="{it["i"]}"]')
                if not loc.count(): pg.evaluate(GO[name]); pg.wait_for_timeout(300); items2=pg.evaluate(FIND); loc=pg.locator(f'[data-af="{it["i"]}"]')
                if not loc.count(): continue
                loc.first.scroll_into_view_if_needed(timeout=1200); pg.wait_for_timeout(60)
                a=pg.evaluate(SIG); n0=len(pops)
                loc.first.click(timeout=1200, force=True); pg.wait_for_timeout(650)
                if pg.evaluate(SIG)==a and len(pops)==n0: dead.append(it)
                pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove());var m=document.getElementById('dxEditor');m&&m.remove()")
                if pg.evaluate("document.getElementById('app').offsetWidth===0"): pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2500)
                exp='companies' if (name=='company' or name.startswith('co_') or name.startswith('ws_')) else name
                if pg.evaluate("document.body.getAttribute('data-page')")!=exp or (name.startswith('co_') and not pg.evaluate("!!document.querySelector('#dxDir.cp')")) or (name.startswith('ws_') and not pg.evaluate("!!document.querySelector('#dxDir.ws')")):
                    pg.evaluate(GO[name]); pg.wait_for_timeout(350); pg.evaluate(FIND)
            except Exception as ex: pass
        tested=len(pick); summary[name]={'tested':tested,'dead':dead,'total':total}
        by=collections.Counter(d['why'].split(' ')[0] if not d['why'].startswith('looks') else 'looks-like' for d in dead)
        print(f"{name:10s} found {total:3d}, tested {tested:3d} | inactive {len(dead):3d} ({(100*len(dead)//max(1,tested))}%) | side-column inactive {sum(1 for d in dead if d['side'])} | {dict(by)}")
        for d in dead[:14]: print(f"      · [{d['why'][:22]}] {d['tag']} '{d['t'][:40]}' .{d['cls'][:30]}{' (side)' if d['side'] else ''}")
    json.dump(summary, open('/tmp/afford_'+'_'.join(PAGES)+'.json','w'))
    b.close()
