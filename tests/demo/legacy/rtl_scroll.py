from playwright.sync_api import sync_playwright
STEPS=["goto('feed')","goto('market')","goto('companies')","dxHub.page('quadra-pharm')","dxHub.workspace('quadra-pharm')","goto('jobs')","goto('network')","goto('groups')","goto('messages')","goto('notifs')","goto('profile')","goto('saved')"]
TRY="""(()=>{var moved=[];[document.scrollingElement,document.getElementById('content')].forEach(function(el){if(!el)return;var a=el.scrollLeft;el.scrollLeft=a+200;var b=el.scrollLeft;el.scrollLeft=a-200;var c=el.scrollLeft;el.scrollLeft=a;if(b!==a||c!==a)moved.push((el.id||'page')+' '+a+'→'+b+'/'+c)});
  var R=document.documentElement.clientWidth, out=[];document.querySelectorAll('#app *').forEach(function(e){var r=e.getBoundingClientRect();if(r.width<2||r.height<2)return;var cs=getComputedStyle(e);if(cs.position==='fixed')return;
    var clip=false;for(var p=e.parentElement;p&&p!==document.body;p=p.parentElement){var pc=getComputedStyle(p);if(pc.overflowX!=='visible'){var pr=p.getBoundingClientRect();if(pr.left>=-1&&pr.right<=R+1){clip=true;break}}}
    if(!clip&&(r.left<-2||r.right>R+2))out.push(e.tagName+'.'+String(e.className).split(' ')[0])});
  return {scrollable:moved,visibleOutside:out.slice(0,4)}})()"""
with sync_playwright() as p:
    for eng, dev in (('webkit','iPhone 12'),('webkit','iPhone SE'),('chromium','Pixel 5'),('chromium',None)):
        for lang in ('ar','en'):
            b=(p.webkit.launch() if eng=='webkit' else p.chromium.launch(args=["--no-sandbox"]))
            ctx=b.new_context(**(p.devices[dev] if dev else {'viewport':{'width':1440,'height':900}})); ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}"%lang)
            pg=ctx.new_page(); errs=[]; pg.on("pageerror",lambda e:errs.append(str(e)[:120]))
            pg.goto('file:///tmp/drugbox_brand.html',wait_until='load'); pg.wait_for_timeout(400); pg.click('#splash'); pg.wait_for_timeout(900)
            pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
            if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
            bad=[]
            for s in STEPS:
                pg.evaluate(s); pg.wait_for_timeout(300); r=pg.evaluate(TRY)
                if r['scrollable'] or r['visibleOutside']: bad.append((s.split("'")[1], r))
            print(f"{(dev or 'Desktop 1440'):12s} {lang}: pages that scroll sideways or show content off-screen: {len(bad)}/12 {bad[:2] if bad else ''} | errors: {errs or 'none'}")
            b.close()
