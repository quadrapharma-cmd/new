# Final build step: make the page light and safe on phones. Idempotent.
import re, base64, io, sys
from PIL import Image   # required (build.py checks it before writing anything)
P = OUT
H = open(P, encoding='utf-8').read()
before = len(H.encode())

# 1 · three.js (globe) is not parsed on phones: stored as inert text, loaded only on large screens after the page is shown
mark = '/**\n * @license\n * Copyright 2010-2021 Three.js Authors'
i = H.find(mark)
if i > 0 and 'id="dxThreeSrc"' not in H:
    j = H.rfind('<script', 0, i)
    close = H.find('>', j) + 1
    H = H[:j] + '<script type="text/x-dx-lazy" id="dxThreeSrc">' + H[close:]
if 'window.dxGlobeStart=start;' not in H:
    H = H.replace('  var ob=window.endSplash;\n', '  window.dxGlobeStart=start;\n  var ob=window.endSplash;\n', 1)
LOADER = """<script data-dx="lazy-globe">
(function(){ function big(){ return (window.innerWidth||0)>900 && !(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches); }
  function load(){ if(window.THREE||!big()) return; var src=document.getElementById('dxThreeSrc'); if(!src) return; try{ var s=document.createElement('script'); s.text=src.text; document.head.appendChild(s); }catch(e){} if(window.dxGlobeStart) setTimeout(window.dxGlobeStart,30); }
  if(document.readyState==='complete') setTimeout(load,400); else window.addEventListener('load',function(){ setTimeout(load,400); });
  window.addEventListener('resize',function(){ if(big()) load(); });
})();
</script>
"""
if 'data-dx="lazy-globe"' not in H:
    z = H.rfind('</body>'); H = H[:z] + LOADER + H[z:]

# 2 · large PNGs (logo, repeated) → WebP, max 512 px
def shrink(m):
    raw = base64.b64decode(m.group(1))
    im = Image.open(io.BytesIO(raw)); im.thumbnail((512, 512))
    out = io.BytesIO(); im.save(out, 'WEBP', quality=86, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(out.getvalue()).decode()
H = re.sub(r'data:image/png;base64,([A-Za-z0-9+/=]{100000,})', shrink, H)

# 3 · if the page is opened in a viewer that does not run apps (phone file preview), say how to open it
if 'id="dxNoJs"' not in H:
    H = H.replace('<html', '<html class="dx-nojs"', 1)
    H = H.replace('<head>', '<head><script>document.documentElement.classList.remove("dx-nojs");document.documentElement.classList.add("dx-js")</script>', 1)
    NOJS = ('<div id="dxNoJs" role="alert"><div><b>Drugbox</b><p dir="rtl" lang="ar">الصفحة دي محتاجة متصفح علشان تشتغل. افتح الرابط في <b>Chrome</b> أو <b>Safari</b> — مش من معاينة الملفات أو واتساب.</p>'
            '<p>This page needs a web browser to run. Open the link in <b>Chrome</b> or <b>Safari</b>, not in a file preview or WhatsApp.</p></div></div>')
    H = re.sub(r'(<body[^>]*>)', r'\1' + NOJS, H, count=1)
    CSS = ('#dxNoJs{display:none}.dx-nojs #dxNoJs{display:flex;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;background:#0a1f4d;color:#fff;padding:24px;font:16px/1.6 Arial,sans-serif;text-align:center}'
           '.dx-nojs #dxNoJs>div{max-width:420px}.dx-nojs #dxNoJs b{color:#F3B258}.dx-nojs #dxNoJs p{margin:14px 0}'
           'html.dx-js .dx-lite-skip,html.dx-js .dx-lite-tap,html.dx-js .dx-lite-enter,html.dx-js #dxLiteGo{display:none!important}'
           '.topbar{padding-top:env(safe-area-inset-top,0px)}.mb-nav,.mobile-nav,.bottom-nav{padding-bottom:env(safe-area-inset-bottom,0px)}')
    k = H.find('</style>'); H = H[:k] + CSS + H[k:]

# 4 · splash video: original quality (audio track removed, faststart), full-size poster frame, no duplicate blurred copy on phones, tap to skip
VID = base64.b64encode(open(SRC + '/splash_full.mp4', 'rb').read()).decode()   # 690x1132, 60 fps, H.264 Main CRF 18 (SSIM 0.992 vs the 4.6 MB master)
POS = base64.b64encode(open(SRC + '/splash_poster_full.webp', 'rb').read()).decode()
H = re.sub(r'<source src="data:video/mp4;base64,[A-Za-z0-9+/=]+"', '<source src="data:video/mp4;base64,' + VID + '"', H, count=1)
if 'poster="data:image/webp' not in H:
    H = H.replace('<video id="splVid" autoplay muted playsinline loop', '<video id="splVid" autoplay muted playsinline loop preload="auto" poster="data:image/webp;base64,' + POS + '"', 1)
H = H.replace("(function(){\n  var v=document.getElementById('splVid'); if(!v)return;\n  var src=v.querySelector('source');", "(function(){\n  var v=document.getElementById('splVid'); if(!v)return; if((window.innerWidth||0)<=900)return;   /* no duplicate blurred copy on phones */\n  var src=v.querySelector('source');", 1)
SKIP = """<script data-dx="splash-skip">
(function(){ var s=document.getElementById('splash'); if(!s) return; s.style.cursor='pointer'; s.setAttribute('title','Tap to skip');
  s.addEventListener('click',function(){ if(window.endSplash) window.endSplash(); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&window.endSplash) window.endSplash(); });
})();
</script>
"""
if 'data-dx="splash-skip"' not in H:
    z = H.rfind('</body>'); H = H[:z] + SKIP + H[z:]

# 5 · a read-only static copy of the key screens for viewers that cannot run apps (iPhone file preview, mail previews)
open(P, 'w', encoding='utf-8').write(H)
import subprocess
r = subprocess.run([sys.executable, SRC + '/snapshot.py', P, SRC + '/_static.html'], capture_output=True, text=True, timeout=300)
print(r.stdout.strip())
if r.returncode:   # never ship the previous build's snapshot silently
    raise SystemExit('lite snapshot failed (the build is not written):\n' + r.stderr[-1500:])
H = open(P, encoding='utf-8').read()
H = re.sub(r'<noscript id="dxStaticWrap">[\s\S]*?</noscript>', '', H)
H = re.sub(r'<div id="dxStaticWrap">[\s\S]*?<!--/dxStaticWrap--><script>[\s\S]*?</script>', '', H)
H = re.sub(r'<div id="dxNoJs"[\s\S]*?</div></div>', '', H, count=1)
ST = open(SRC + '/_static.html', encoding='utf-8').read()
LCSS = open(SRC + '/_static.css', encoding='utf-8').read()
H = re.sub(r'/\*dx-lite-css\*/[\s\S]*?/\*/dx-lite-css\*/', '', H)
k = H.find('</style>'); H = H[:k] + '/*dx-lite-css*/' + LCSS + '/*/dx-lite-css*/' + H[k:]   # lite styles live in the head
for _b in ('<button class="f-btn" onclick="doLogin()">', '<button class="f-btn" onclick="doSignup()">', '<button class="s-skip" onclick="endSplash()">'):
    H = H.replace(_b, _b.replace('class="f-btn"', 'class="f-btn dx-js-only"').replace('class="s-skip"', 'class="s-skip dx-js-only"'), 1)
_icon = re.search(r'const LOGO_ICON = "(data:image/webp;base64,[^"]+)"', H)
_full = re.search(r'const LOGO = "(data:image/webp;base64,[^"]+)"', H)
if _icon and _full:   # every logo is in the page itself (the app sets the same images), so it shows even when scripts are blocked
    # (the sign-up logo and the app bar's logo only show after a script ran, and the scripts set them: no copy needed)
    for _id, _src in (('splLogo', _full), ('formLogo', _full), ('heroLogo', _icon)):
        H = re.sub(r'(<img[^>]*id="%s"[^>]*?)src=""' % _id, lambda mm: mm.group(1) + 'src="' + _src.group(1) + '"', H, count=1)
        H = re.sub(r'<img([^>]*?)src=""([^>]*id="%s")' % _id, lambda mm: '<img' + mm.group(1) + 'src="' + _src.group(1) + '"' + mm.group(2), H, count=1)
# splash without scripts or animations: tap anywhere or "Skip" goes to the login page (plain links)
if 'id="dxLiteGo"' not in H:
    H = H.replace('<div id="splash">', '<a id="dxLiteGo" aria-hidden="true"></a><div id="splash">', 1)
    H = re.sub(r'(<button class="s-skip[^"]*" onclick="endSplash\(\)">Skip →</button>)', r'\1<a class="s-skip dx-lite-skip" href="#dxLiteGo">Skip →</a><a class="dx-lite-tap" href="#dxLiteGo" aria-label="Continue"></a>', H, count=1)
if 'class="f-btn dx-lite-enter"' not in H:   # lite mode: the login button becomes a link into the app
    H = re.sub(r'(<button class="f-btn[^"]*" onclick="doLogin\(\)">Sign In →</button>)', r'\1<a class="f-btn dx-lite-enter" href="#p-feed">Sign In →</a>', H, count=1)
H = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + ST, H, count=1)

H = re.sub(r'(<img id="__logo" src=")data:image/\w+;base64,[A-Za-z0-9+/=]+(" style="display:none">)', r'\1data:image/gif;base64,R0lGODlhAQABAIAAAMLS5wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==\2', H, count=1)   # hidden, never used: 1 px instead of a 28 KB third copy of the logo

# 6 · every <style> that lives in the body moves to the head, same order (some viewers drop body styles)
_hi = H.find('<body')
_parts = re.split(r'(<script[^>]*>[\s\S]*?</script>)', H[_hi:])   # never touch text inside scripts
_body_styles = []
for _i in range(0, len(_parts), 2):
    _body_styles += re.findall(r'<style[^>]*>[\s\S]*?</style>', _parts[_i])
    _parts[_i] = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', _parts[_i])
if _body_styles:
    _head = H[:_hi]; _he = _head.rfind('</head>')
    H = _head[:_he] + '\n'.join(_body_styles) + '\n' + _head[_he:] + ''.join(_parts)

# 7 · approved-page fix (layered, source untouched): the boost modal waits for an exchange rate; if the user left the page meanwhile, stop quietly
H = H.replace("  var rate = await getLiveUsdToEgpRate();\n  var baseEgp", "  var rate = await getLiveUsdToEgpRate();\n  if (!document.getElementById('bmEgpAmount') || !document.getElementById('boostModalOverlay')) return;   /* the page changed while waiting */\n  var baseEgp", 1)

open(P, 'w', encoding='utf-8').write(H)
print('mobile step: %.2f MB → %.2f MB' % (before / 1e6, len(H.encode()) / 1e6))
