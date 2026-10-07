from playwright.sync_api import sync_playwright
import collections
PAGES=['feed','market','companies','company','jobs','network','messages','notifs','profile','groups','training','saved']
FIND=r"""((k)=>{var s=document.getElementById('p-'+k); if(!s) return [];
  var names=['Dr. Haytham Dweedar','Dr. Asmaa Meabed','Allison Wang','Muhammed Musthafa','Eng. Omar Khaled','Dr. Sara El-Amin','Aurobindo Pharma'];
  var LINKY=/(^|\s)(tag|chip|pill|hashtag|trend|ad|ads|sponsor|promo|banner|name|title|link|more|see-?all|view-?all|author|company|seller|brand|topic|badge|cta|headline|stat|count|sug|who|person|user|member|jc-title|lc-title|sp-title|sc-title|dc-title|gcard-title|post-name|seller-name)(\s|-|_|$)/i;
  var out=[];
  s.querySelectorAll('.lm-c *').forEach(function(e){
    var r=e.getBoundingClientRect(); if(r.width<3||r.height<3) return; if(e.closest('input,textarea,select,svg,.lx')) return;
    var cs=getComputedStyle(e), own=[...e.childNodes].some(n=>n.nodeType===3&&n.nodeValue.trim().length>1), t=(e.textContent||'').trim().replace(/\s+/g,' ');
    var why='';
    if(cs.cursor==='pointer') why='pointer';
    else if(own && LINKY.test(e.className||'')) why='linky';
    else if(own && t.length<60 && names.indexOf(t)>=0) why='name';
    else if(own && /^#\w/.test(t) && t.length<40) why='hashtag';
    if(!why) return;
    out.push({el:e,why:why,t:t.slice(0,40),cls:String(e.className).slice(0,30),side:!!e.closest('aside,[class*=side],[class*=widget],[class*=rail],[class*=sponsor],[class*=promo],[class*=ad-]')});
  });
  window.__LA=out.map(o=>o.el);
  return out.map(o=>({why:o.why,t:o.t,cls:o.cls,side:o.side}));})"""
with sync_playwright() as p:
    b=p.webkit.launch(); pg=b.new_page(**p.devices['iPhone 12']); pg.goto('file://'+__import__('os').environ.get('DEMO_VARIANTS','/tmp')+'/sanitized.html',wait_until='load'); pg.wait_for_timeout(500)
    T=D=0
    for k in PAGES:
        pg.evaluate(f"location.hash='#p-{k}'"); pg.wait_for_timeout(150)
        items=pg.evaluate(FIND, k); dead=[]
        for i,it in enumerate(items):
            live=pg.evaluate(f"""(()=>{{var e=window.__LA[{i}];e.scrollIntoView({{block:'center',inline:'center'}});var r=e.getBoundingClientRect();var x=Math.max(r.left,0)+Math.min(r.width/2,15),top=Math.max(r.top,70),y=Math.min(top+10,r.bottom-2);var h=document.elementFromPoint(x,y);var a=h&&h.closest('a[href]');return !!a}})()""")
            if not live: dead.append(it)
        T+=len(items); D+=len(dead)
        print(f"{k:10s} looks clickable {len(items):3d} | does nothing {len(dead):3d} ({100*len(dead)//max(1,len(items))}%) | side/ads dead {sum(1 for d in dead if d['side'])}")
        for d in dead[:6]: print(f"      · [{d['why']}] '{d['t'][:36]}' .{d['cls']}")
    print(f"TOTAL looks clickable {T} | does nothing {D} ({100*D//max(1,T)}%)")
    b.close()
