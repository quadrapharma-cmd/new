# Lite mode: the same app, rendered ahead of time, navigable with HTML + CSS only.
# Used automatically when a viewer blocks JavaScript (phone file previews, WhatsApp viewers, "open with" from Downloads).
import re, sys
from playwright.sync_api import sync_playwright
SRC = sys.argv[1]; OUT = sys.argv[2]
PAGES = [('feed', 'Home', 'home', "goto('feed')"), ('market', 'Marketplace', 'cart', "goto('market')"), ('companies', 'Company directory', 'building', "goto('companies')"),
         ('company', 'Quadra Pharm', 'building', "dxHub.page('quadra-pharm')"), ('jobs', 'Jobs', 'briefcase', "goto('jobs')"), ('network', 'My network', 'users', "goto('network')"),
         ('messages', 'Messages', 'chat', "goto('messages')"), ('notifs', 'Notifications', 'bell', "goto('notifs')"), ('profile', 'My profile', 'user', "goto('profile')"),
         ('groups', 'Groups', 'handshake', "goto('groups')"), ('training', 'Training', 'cap', "goto('training')"), ('saved', 'Saved', 'bookmark', "goto('saved')")]
PIX = 'data:image/gif;base64,R0lGODlhAQABAIAAAMLS5wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=='
# The snapshot must be the same on every build (it is part of the delivered file and of the parity check):
# a fixed date (the hero line names the weekday), a seeded Math.random, no network (fonts, exchange rate), finished
# count-up animations (reduced motion makes them show the final figure) and "settle" waits instead of fixed sleeps.
FIXED_TIME = '2026-10-02T10:00:00+03:00'   # a Friday, as in the approved demo
SEED = ("(function(){var s=20261002;Math.random=function(){s=s+0x6D2B79F5|0;var t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};"
        # idle-time work (the layers' idle() helpers: "Landed cost" chips, molecules…) waits until settle() runs it, after the
        # render layers, so the order of the layers never depends on how busy the machine is
        "var Q={},n=0;window.requestIdleCallback=function(cb){Q[++n]=cb;return n;};window.cancelIdleCallback=function(i){delete Q[i];};"
        "window.__dxRunIdle=function(){var k=Object.keys(Q).map(Number).sort(function(a,b){return a-b;});k.forEach(function(i){var cb=Q[i];delete Q[i];"
        "try{cb({didTimeout:false,timeRemaining:function(){return 0;}});}catch(e){}});return k.length;};})();")
SETTLE = """() => new Promise(done => { var t0 = performance.now(), last = t0, ob = new MutationObserver(() => { last = performance.now(); });
  ob.observe(document.documentElement, {subtree: true, childList: true, attributes: true, characterData: true});
  (function tick() { var now = performance.now(); if (now - last > 500 || now - t0 > 6000) { ob.disconnect(); done(); } else setTimeout(tick, 100); })(); })"""
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1, locale='en-US', timezone_id='Africa/Cairo', reduced_motion='reduce')
    ctx.clock.set_fixed_time(FIXED_TIME); ctx.add_init_script(SEED)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page()
    def settle():   # wait until the page stops changing, run every render layer once more on the final page (a page that changes
        pg.evaluate(SETTLE)   # while the layers run in slices can otherwise miss one: icons, company links), then the idle-time work
        if pg.evaluate("!!(window.dxCore && dxCore.onRender)"): pg.evaluate("dxCore.onRender('snapshot', function () {})"); pg.evaluate(SETTLE)
        for _ in range(2):
            if pg.evaluate("window.__dxRunIdle ? __dxRunIdle() : 0"): pg.evaluate(SETTLE)
    pg.goto('file://' + SRC, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(900)
    pg.click('.lg-demo'); pg.click('#loginPage .f-btn'); pg.wait_for_timeout(3200); settle()
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip'); settle()
    icons = pg.evaluate("(()=>{var o={};['home','cart','building','briefcase','users','chat','bell','user','handshake','cap','bookmark'].forEach(k=>{o[k]=window.dxIcon?window.dxIcon(k):''});return o})()")
    parts = []
    for key, label, icon, js in PAGES:
        pg.evaluate(js); pg.wait_for_timeout(650); settle()
        html = pg.evaluate("""(()=>{var c=document.getElementById('content').cloneNode(true);
          var LITE={feed:1,market:1,companies:1,jobs:1,network:1,messages:1,notifs:1,profile:1,groups:1,training:1,saved:1};
          var SEL='button,[onclick],[role=button],a[href],.hb-card,.dr-card,label.chip,[data-hopen],[data-htab2]';
          var ORIG=[...document.getElementById('content').querySelectorAll(SEL)];
          /* everything that LOOKS clickable (hand cursor, link-like class, a person/company name, a hashtag) — computed on the live page */
          var LINKY=/(^|\s)(tag|chip|pill|hashtag|trend|ad|ads|sponsor|promo|banner|name|title|link|more|see-?all|view-?all|author|company|seller|brand|topic|badge|cta|headline|stat|count|sug|who|person|user|member|mygroup|mg-|sh-row|net-overview|sugg|gcard|me-row|post-av|badge-cat|master-tab|jcard|jc-|lc-title|sp-title|sc-title|dc-title|post-name|seller-name)/i;
          var NAMES=(window.USERS||[]).map(u=>u.name), COS=window.dxDir?dxDir.companies().map(x=>x.name):[];
          var ALL0=[...document.getElementById('content').querySelectorAll('*')], ALLC=[...c.querySelectorAll('*')], CAND=[];
          ALL0.forEach(function(o,i){ if(o.closest('input,textarea,select,svg')) return; var r=o.getBoundingClientRect(); if(r.width<3||r.height<3) return;
            var t=(o.textContent||'').trim().replace(/\s+/g,' '), own=[...o.childNodes].some(n=>n.nodeType===3&&n.nodeValue.trim().length>1);
            if(getComputedStyle(o).cursor==='pointer' || (own&&LINKY.test(o.className||'')) || (own&&t.length<60&&(NAMES.indexOf(t.replace(/[✓✔]/g,'').trim())>=0||COS.indexOf(t)>=0)) || (own&&/^#\w/.test(t)&&t.length<40)) CAND.push(i); });
          function DEST(o){ var t=(o.textContent||'').replace(/[✓✔]/g,'').trim().replace(/\s+/g,' '), cls=String(o.className||'')+' '+String((o.parentElement||{}).className||'');
            var oc=o.getAttribute('onclick')||'', m=/goto\\('(\\w+)'\\)/.exec(oc); if(m&&LITE[m[1]]) return '#p-'+m[1];
            if(/master-tab/.test(cls)) return /browse/i.test(t)?'#p-market':'#p-need';
            if(t==='Quadra Pharm'||/quadra-pharm/.test(o.getAttribute('data-slug')||'')) return '#p-company';
            if(COS.indexOf(t)>=0) return '#p-companies';
            if(NAMES.some(n=>t.indexOf(n)===0)) return t.indexOf((window.ME||{}).name||'@@')===0?'#p-profile':'#p-network';
            if(/sugg|person|member|who|user|post-av|me-row|author/i.test(cls)) return '#p-network';
            if(/mygroup|mg-|gcard|sh-row|group/i.test(cls)) return '#p-groups';
            if(/^connections/i.test(t)) return '#p-network'; if(/profile views|impressions/i.test(t)) return '#p-profile'; if(/saved/i.test(t)) return '#p-saved';
            if(/jcard|jc-/i.test(cls)) return '#p-jobs';
            if(/lc-title|sp-title|sc-title|dc-title|sponsor|promo|ad(s)?\b|seller/i.test(cls)) return '#p-market';
            return '#p-need'; }
          c.querySelectorAll(SEL).forEach(function(e, idx){
            if (e.closest('.lx')) return;
            var oc=e.getAttribute('onclick')||'', href=e.getAttribute('href')||'', to='#p-need', m=/goto\\('(\\w+)'\\)/.exec(oc);
            if (m && LITE[m[1]]) to='#p-'+m[1];
            else if (/gotoProfile/.test(oc)) to='#p-profile';
            else if (e.getAttribute('data-hopen')) to = e.getAttribute('data-hopen')==='quadra-pharm' ? '#p-company' : '#p-companies';
            else if (e.classList.contains('hb-card') || e.classList.contains('dr-card')) to = e.getAttribute('data-slug')==='quadra-pharm' ? '#p-company' : '#p-companies';
            else if (/^https?:|^tel:|^mailto:/.test(href)) return;
            if (e.tagName==='A') { e.setAttribute('href', to); e.removeAttribute('target'); return; }
            var a=document.createElement('a'); a.className = e.querySelector(SEL) ? 'lx lx-card' : 'lx'; a.href=to;   /* a card's own link sits under the buttons inside it */
            if (e.querySelector(SEL)) e.classList.add('lx-host'); a.setAttribute('aria-label',(e.textContent||'').trim().slice(0,40)||'Open');
            var o=ORIG[idx]; if (o && getComputedStyle(o).position==='static') e.style.position='relative';   /* the overlay covers exactly this control */
            if (o && getComputedStyle(o).display==='inline') e.style.display='inline-block';
            e.appendChild(a);
          });
          /* second pass: things that look clickable but are not buttons get a destination too (outermost only) */
          CAND.forEach(function(i){ var e=ALLC[i], o=ALL0[i]; if(!e||!e.isConnected&&!c.contains(e)) return;
            if(e.tagName==='A'||e.querySelector(':scope > a.lx')) return;
            for(var p=e.parentElement;p&&p!==c;p=p.parentElement){ if(p.tagName==='A'||p.querySelector(':scope > a.lx')) {
                var hl=p.querySelector(':scope > a.lx'), ho=ALL0[ALLC.indexOf(p)], orr=o.getBoundingClientRect(), hr=ho?ho.getBoundingClientRect():null;
                if(hl && hr && (orr.top<hr.top-1||orr.left<hr.left-1||orr.right>hr.right+1||orr.bottom>hr.bottom+1)){   /* sticks out of its card: own link, same destination */
                  var a2=document.createElement('a'); a2.className='lx'; a2.href=hl.getAttribute('href'); a2.setAttribute('aria-label',(e.textContent||'').trim().slice(0,40)||'Open');
                  e.style.pointerEvents='auto'; if(getComputedStyle(o).position==='static') e.style.position='relative'; e.appendChild(a2); return; }
                if(!e.querySelector('a,button')) e.style.pointerEvents='none'; return; } }   /* labels on a card let the tap reach the card's link */
            var isCard=!!e.querySelector('button,a,[onclick]'); if(isCard) e.classList.add('lx-host');
            var a=document.createElement('a'); a.className=isCard?'lx lx-card':'lx'; a.href=DEST(o); a.setAttribute('aria-label',(e.textContent||'').trim().slice(0,40)||'Open');
            if(getComputedStyle(o).position==='static') e.style.position='relative'; if(getComputedStyle(o).display==='inline') e.style.display='inline-block';
            e.appendChild(a); });
          c.querySelectorAll('script,noscript,video,canvas,iframe,#dxSkel,.dx-skel').forEach(e=>e.remove());
          c.querySelectorAll('*').forEach(e=>{[...e.attributes].forEach(a=>{if(/^on/i.test(a.name))e.removeAttribute(a.name)}); if(/^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName))e.setAttribute('disabled','')});
          return c.innerHTML;})()""")
        html = re.sub(r'data:image/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]{30000,}', PIX, html)
        parts.append((key, label, icon, html))

    # Several pages show the same things (the feed's posts on the profile, the directory on the company page): an id may
    # appear once only. Later copies get a page-specific id, and the page's own style rules for that id are copied for it.
    seen, renamed = set(), {}
    def uniq(key, html):
        def one(m):
            i = m.group(2)
            if i not in seen: seen.add(i); return m.group(0)
            renamed[i + '--' + key] = i; return m.group(1) + i + '--' + key + m.group(3)
        return re.sub(r'(\sid=")([^"]+)(")', one, html)
    # a page title reads as its name only: the badges after the name (Sponsored, Active, ✓) are hidden from screen readers
    def badges(html):
        def h1(m):
            if not re.match(r'\s*[^<\s]', m.group(2)): return m.group(0)   # only when the title starts with its own text
            return m.group(1) + re.sub(r'<(span|small|b|i|em)(?![^>]*aria-hidden)(\s[^>]*)?>', lambda t: '<' + t.group(1) + (t.group(2) or '') + ' aria-hidden="true">', m.group(2)) + m.group(3)
        return re.sub(r'(<h1\b[^>]*>)([\s\S]*?)(</h1>)', h1, html)
    parts = [(k, l, i, badges(uniq(k, h))) for k, l, i, h in parts]
    ID_CSS = pg.evaluate(r"""(pairs) => { var out = [];   /* only the selectors that name the id: the copy never restyles anything else */
      function split(sel) { var a = [], d = 0, cur = ''; for (var ch of sel) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && !d) { a.push(cur); cur = ''; } else cur += ch; } a.push(cur); return a; }
      function walk(rules, wraps) { for (var r of rules) {
        if (r.selectorText) pairs.forEach(function (p) { if (!/^[\w-]+$/.test(p[1])) return; var re = new RegExp('#' + p[1] + '(?![\\w-])', 'g');
          var sel = split(r.selectorText).filter(function (x) { re.lastIndex = 0; return re.test(x); }).map(function (x) { return x.replace(re, '#' + p[0]).trim(); });
          if (!sel.length) return; var css = sel.join(',') + '{' + r.style.cssText + '}';
          for (var i = wraps.length - 1; i >= 0; i--) css = wraps[i] + '{' + css + '}'; out.push(css); });
        else if (r.cssRules && r.conditionText !== undefined) walk(r.cssRules, wraps.concat([(r instanceof CSSMediaRule ? '@media ' : '@supports ') + r.conditionText])); } }
      for (var sh of document.styleSheets) { try { walk(sh.cssRules, []); } catch (e) {} }
      return out.join(''); }""", [[n, o] for n, o in renamed.items()])
    b.close()

def ic(k): return '<span class="li-ic">' + icons.get(k, '') + '</span>'
NAV5 = [('feed', 'Home', 'home'), ('market', 'Market', 'cart'), ('companies', 'Companies', 'building'), ('jobs', 'Jobs', 'briefcase'), ('messages', 'Messages', 'chat')]
def chrome(active):
    top = ('<header class="lh"><a class="lh-logo" href="#p-feed">DRUG<b>BOX</b></a><span class="lh-sp"></span>'
           '<a class="lh-btn" href="#p-notifs" aria-label="Notifications">' + ic('bell') + '</a><a class="lh-btn" href="#p-menu" aria-label="Menu">☰</a></header>')
    nav = '<nav class="ln">' + ''.join('<a href="#p-%s" class="%s">%s<span>%s</span></a>' % (k, 'on' if k == active else '', ic(i), l) for k, l, i in NAV5) + '</nav>'
    return top, nav
secs = ''
for key, label, icon, html in parts:
    top, nav = chrome(key)
    secs += '<section class="lp" id="p-%s">%s<main class="lm"><h2 class="lm-h">%s</h2><div class="content lm-c">%s</div></main>%s</section>' % (key, top, label, html, nav)
top, nav = chrome('')
need = ('<section class="lp" id="p-need">' + top + '<main class="lm"><div class="lneed"><div class="lneed-i">⚡</div><h2 class="lm-h">This action needs the full app</h2>'
        '<p dir="rtl" lang="ar">الزرار ده محتاج التطبيق الكامل. البرنامج اللي فاتح الملف مانع تشغيل الكود — افتح نفس الملف في متصفح (Chrome أو Safari أو Edge) علشان تستخدمه.</p>'
        '<p>Open the same file in a browser (Chrome, Safari or Edge) to use it. You can keep browsing here.</p>'
        '<div class="lneed-a"><a href="#p-feed">Home</a><a href="#p-menu">All pages</a></div></div></main>' + nav + '</section>')
menu = ('<section class="lp" id="p-menu">' + top + '<main class="lm"><h2 class="lm-h">Menu</h2><div class="lmenu">' +
        ''.join('<a href="#p-%s">%s<span>%s</span></a>' % (k, ic(i), l) for k, l, i, _ in parts) +
        '<a href="#dxLiteGo" class="lmenu-out">⎋<span>Sign out</span></a></div>'
        '<p class="lnote" dir="rtl" lang="ar">نسخة خفيفة: البرنامج اللي فاتح الملف مانع تشغيل الكود، فالتصفح شغال والنشر والإرسال محتاجين متصفح كامل.</p>'
        '<p class="lnote">Lite mode: this viewer blocks scripts, so browsing works; posting or sending needs a full browser.</p></main>' + nav + '</section>')
CSS = ('<style>'
  'html.dx-js #dxLite{display:none!important}'
  'html:not(.dx-js) #app,html:not(.dx-js) #dxNoJs,html:not(.dx-js) #sbToggle,html:not(.dx-js) #mbnav,html:not(.dx-js) #toast,html:not(.dx-js) #lgGlobe{display:none!important}'
  'html:not(.dx-js) #authWrap{display:block!important}html:not(.dx-js) #loginPage{display:grid!important}'
  'html:not(.dx-js) #splash{animation:dxLiteOut .6s ease 3.2s forwards}@keyframes dxLiteOut{to{opacity:0;visibility:hidden}}'
  '#dxLiteGo:target~#splash,html:not(.dx-js) #dxLiteGo:target~#splash{display:none!important}'
  '.dx-lite-skip,.dx-lite-tap{display:none}'
  'html:not(.dx-js) .dx-lite-skip{display:inline-block;text-decoration:none;z-index:7!important}'
  'html:not(.dx-js) .dx-lite-tap{display:block;position:absolute;inset:0;z-index:2}'
  'html:not(.dx-js) #splash video,html:not(.dx-js) #splash .s-ov,html:not(.dx-js) #splash .s-brand,html:not(.dx-js) #splash .s-prog{pointer-events:none}'
  'html:not(.dx-js) .dx-js-only{display:none!important}.dx-lite-enter{display:none!important}html:not(.dx-js) .dx-lite-enter{display:flex!important;align-items:center;justify-content:center;text-decoration:none}'
  '.lp{display:none}.lp:target{display:block;position:fixed;inset:0;z-index:2147483000;overflow-y:auto;-webkit-overflow-scrolling:touch;background:#F4F6FA}'
  '.lh{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:8px;min-height:58px;padding:0 14px;padding-top:env(safe-area-inset-top,0px);background:#fff;border-bottom:1px solid #E6E8EE}'
  '.lh-logo{font:900 20px Poppins,Arial,sans-serif;color:#0a1f4d;text-decoration:none;letter-spacing:.02em}.lh-logo b{color:#1a56db}.lh-sp{flex:1}'
  '.lh-btn{width:40px;height:40px;border-radius:50%;border:1px solid #E6E8EE;display:flex;align-items:center;justify-content:center;color:#374151;text-decoration:none;font-size:18px}'
  '.li-ic{display:inline-flex}.li-ic svg{width:20px;height:20px}'
  '.lm{padding-bottom:84px}.lm-h{margin:0;padding:14px 16px 4px;font:800 20px Poppins,Arial,sans-serif;color:#0a1f4d;text-transform:none;letter-spacing:0}'
  '.lm-c{padding:0!important;margin:0!important;max-width:100%!important;overflow:hidden}.lm-c input,.lm-c select,.lm-c textarea{pointer-events:none}'
  '.lx{position:absolute;inset:0;z-index:4;pointer-events:auto;background:transparent}.lx.lx-card{z-index:1;top:-14px}'   # covers badges that stick out above the card
  '.lx-host *{pointer-events:none!important}.lx-host a,.lx-host a *,.lx-host .lx,.lx-host :has(> a.lx){pointer-events:auto!important}'
  '.lneed{max-width:520px;margin:30px auto;padding:0 18px;text-align:center;font:15px/1.7 Poppins,Arial,sans-serif;color:#374151}.lneed-i{font-size:40px}'
  '.lneed-a{display:flex;gap:10px;justify-content:center;margin-top:14px}.lneed-a a{background:#1a56db;color:#fff;border-radius:999px;padding:10px 18px;text-decoration:none;font-weight:700}'
  '.ln{position:fixed;left:0;right:0;bottom:0;z-index:6;display:flex;background:#fff;border-top:1px solid #E6E8EE;padding-bottom:env(safe-area-inset-bottom,0px)}'
  '.ln a{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;padding:8px 0 10px;color:#64748b;text-decoration:none;font:600 11px Poppins,Arial,sans-serif}.ln a.on{color:#1a56db}'
  '.lmenu{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px 16px}.lmenu a{display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #E6E8EE;border-radius:16px;padding:14px;color:#0E1320;text-decoration:none;font:600 14px Poppins,Arial,sans-serif}'
  '.lmenu .lmenu-out{color:#991B1B}.lnote{margin:6px 16px;color:#64748b;font:13px/1.6 Poppins,Arial,sans-serif}'
  '@media (min-width:900px){.lm{max-width:1100px;margin:0 auto}.ln{max-width:640px;margin:0 auto;border-radius:18px 18px 0 0}}'
  + ID_CSS + '</style>')
def write_if_changed(path, text):   # tracked files: an unchanged snapshot leaves the working tree clean
    try:
        if open(path, encoding='utf-8').read() == text: return False
    except FileNotFoundError: pass
    open(path, 'w', encoding='utf-8').write(text); return True
write_if_changed(OUT.replace('.html', '.css'), CSS.replace('<style>', '').replace('</style>', ''))
LITE = ('<div id="dxStaticWrap"><a id="dxLiteTop"></a><div id="dxLite">' + secs + menu + '</div></div><!--/dxStaticWrap-->'
  + '<script>(function(){var s=document.getElementById("dxStaticWrap");if(s&&s.parentNode)s.parentNode.removeChild(s);})();</script>')
changed = write_if_changed(OUT, LITE)
print('lite app: %d KB, %d pages + menu%s' % (len(LITE) // 1024, len(parts), '' if changed else ' (unchanged)'))
