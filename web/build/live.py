"""Live build: the demo build + the data adapter. Writes web/dist/live/ (index.html + separate, cacheable files).
The demo build (web/dist/drugbox.html) is not changed.
Needs DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY (public values; never the service key).
Optional: DRUGBOX_SENTRY_LOADER (the Sentry "Loader Script" URL https://js.sentry-cdn.com/<key>.min.js — injected first in <head>, and its
hosts are allowed by the CSP only then), DRUGBOX_LIVE_OUT (output folder, default web/dist/live), DRUGBOX_DEMO (the demo build to package,
default web/dist/drugbox.html), DRUGBOX_VAPID_PUBLIC_KEY (web push: the PUBLIC VAPID key, base64url of the 65-byte point — never the private
one; without it the app keeps in-app notifications only). Hosting headers come from deploy/vercel.json (the one template).
Installable app (w-pwa): manifest.webmanifest, sw.js (the service worker, its VERSION = this build's stamp) and icons/ (content-hashed
copies of web/src/pwa/*.png, made by tools/pwa/make_icons.py) are written next to index.html; index.html gets the manifest, icon and
iOS tags in <head>."""
import os, re, json, base64, hashlib, glob
from urllib.parse import urlparse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url, key = os.environ.get('DRUGBOX_SUPABASE_URL', ''), os.environ.get('DRUGBOX_SUPABASE_ANON_KEY', '')
if not url or not key: raise SystemExit('Set DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY')
# the key is a JWT: its role is inside the base64url payload, so the literal text "service_role" never appears in a real key
try:
    claims = json.loads(base64.urlsafe_b64decode(key.split('.')[1] + '=' * (-len(key.split('.')[1]) % 4)))
except Exception:
    raise SystemExit('DRUGBOX_SUPABASE_ANON_KEY is not a JWT (copy the "anon public" key from Supabase → Settings → API)')
if claims.get('role') != 'anon':
    raise SystemExit('Refusing to embed a key with role %r in the browser build — only the anon key belongs here' % claims.get('role'))
u = urlparse(url)
if u.scheme not in ('http', 'https') or not u.hostname or (u.scheme == 'http' and u.hostname not in ('localhost', '127.0.0.1')):
    raise SystemExit('DRUGBOX_SUPABASE_URL must be https://<project>.supabase.co (http only for localhost)')
DEMO = os.path.abspath(os.environ.get('DRUGBOX_DEMO') or ROOT + '/dist/drugbox.html')
# Sentry (optional): only the official loader URL is accepted (a pasted <script src="…"> tag is reduced to its URL)
sentry = os.environ.get('DRUGBOX_SENTRY_LOADER', '').strip()
if sentry:
    sm = re.search(r'https://[^\s"\'<>]+', sentry); sentry = sm.group(0) if sm else sentry
    su = urlparse(sentry)
    if su.scheme != 'https' or not (su.hostname or '').endswith('.sentry-cdn.com') or not re.fullmatch(r'/[A-Za-z0-9]+\.min\.js', su.path or '') or su.query:
        raise SystemExit('DRUGBOX_SENTRY_LOADER must be the Sentry loader URL, e.g. https://js.sentry-cdn.com/<public key>.min.js '
                         '(Sentry → Settings → Projects → <project> → Loader Script)')
# web push (optional): the PUBLIC VAPID key only — an uncompressed P-256 point (65 bytes, 0x04 first). The private key is 32 bytes
# and lives only in the Edge Function secrets: a 32-byte value here is refused, so it can never reach the browser by mistake.
vapid = os.environ.get('DRUGBOX_VAPID_PUBLIC_KEY', '').strip()
if vapid:
    try: vk = base64.urlsafe_b64decode(vapid + '=' * (-len(vapid) % 4)) if re.fullmatch(r'[A-Za-z0-9_-]+', vapid) else b''
    except Exception: vk = b''
    if len(vk) == 32: raise SystemExit('DRUGBOX_VAPID_PUBLIC_KEY looks like the PRIVATE key (32 bytes) — only the public key belongs in the browser build')
    if len(vk) != 65 or vk[0] != 4: raise SystemExit('DRUGBOX_VAPID_PUBLIC_KEY must be the base64url public VAPID key (65 bytes, from tools/pwa/vapid_keys.mjs)')
# the live app is the demo build: refuse to package an older demo than the sources (run web/build/build.py first)
srcs = [ROOT + '/base/app.html'] + [f for f in glob.glob(ROOT + '/src/*') if os.path.isfile(f) and not f.endswith(('_static.html', '_static.css'))]
# (web/src/pwa/* is read by this script itself, not by the demo build: not a reason to rebuild the demo)
newer = [os.path.relpath(f, ROOT) for f in srcs if os.path.getmtime(f) > os.path.getmtime(DEMO)] if os.path.exists(DEMO) else ['(no demo build)']
if newer and os.environ.get('DRUGBOX_ALLOW_STALE') != '1':
    raise SystemExit('web/dist/drugbox.html is older than %s — run python3 web/build/build.py first (or DRUGBOX_ALLOW_STALE=1)' % ', '.join(newer[:3]))
OUT = os.path.abspath(os.environ.get('DRUGBOX_LIVE_OUT') or ROOT + '/dist/live'); os.makedirs(OUT + '/js', exist_ok=True); os.makedirs(OUT + '/media', exist_ok=True); os.makedirs(OUT + '/icons', exist_ok=True)
def asset(src, name, sub='js', ext='js', data=None):   # content-hashed file name → safe to cache forever on a CDN
    data = data if data is not None else open(src, 'rb').read(); h = hashlib.sha256(data).hexdigest()[:10]; fn = f'{name}.{h}.{ext}'
    open(f'{OUT}/{sub}/{fn}', 'wb').write(data); return f'{sub}/{fn}'
lib = asset(ROOT + '/src/vendor/supabase-2.45.4.min.js', 'supabase')
ada = asset(ROOT + '/src/live/adapter.js', 'adapter')
# area layers of the live app (web/src/live/<name>.js besides the adapter): loaded right after it, in name order
xtra = [(os.path.basename(f)[:-3], asset(f, os.path.basename(f)[:-3])) for f in sorted(glob.glob(ROOT + '/src/live/*.js')) if os.path.basename(f) != 'adapter.js']
H = open(DEMO, encoding='utf-8').read()
# the splash video is most of the demo's weight: online it is a separate, cacheable file (same bytes, same markup otherwise)
m = re.search(r'<source src="data:video/mp4;base64,([A-Za-z0-9+/=]+)"', H)
if m: H = H[:m.start()] + '<source src="' + asset(None, 'splash', 'media', 'mp4', base64.b64decode(m.group(1))) + '"' + H[m.end():]
# F-71: the scripts are most of the rest. Online every inline classic script over 2 KB (the layers, the app, the people photos)
# becomes a content-hashed file (cacheable for ever) referenced by a plain <script src> in the SAME place with the same attributes:
# parser-blocking, run in document order exactly like the inline copy (no defer/async). Small inline scripts stay inline.
# three.js (inert text read by the lazy-globe loader on large screens only) becomes a file the loader fetches when it needs it.
# The read-only lite copy (0.5 MB of sample screens for file previews that cannot run scripts) is for the offline file only:
# every browser that runs the app deletes it at once. Online, a viewer without scripts gets a short bilingual notice instead.
NOJS = ('<noscript><div role="alert" style="display:flex;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;background:#0a1f4d;color:#fff;'
        'padding:24px;font:16px/1.6 Arial,sans-serif;text-align:center"><div style="max-width:420px"><b style="color:#F3B258">Drugbox</b>'
        '<p dir="rtl" lang="ar" style="margin:14px 0">الصفحة دي محتاجة متصفح علشان تشتغل. افتح الرابط في <b>Chrome</b> أو <b>Safari</b>، وشغّل JavaScript.</p>'
        '<p style="margin:14px 0">This page needs a web browser with JavaScript. Open the link in <b>Chrome</b> or <b>Safari</b>.</p></div></div></noscript>')
H, lite = re.subn(r'<div id="dxStaticWrap">[\s\S]*?<!--/dxStaticWrap--><script>[\s\S]*?</script>', lambda _: NOJS, H, count=1)
moved = []
def outline(mm):
    attrs, body = mm.group(1), mm.group(2)
    if 'src=' in attrs or len(body.encode('utf-8')) < 2048: return mm.group(0)
    if 'id="dxThreeSrc"' in attrs:
        moved.append('three'); return '<script%s data-src="%s"></script>' % (attrs, asset(None, 'three', data=body.encode('utf-8')))
    if re.search(r'\btype=', attrs): return mm.group(0)   # other non-JavaScript blocks stay as they are
    d = re.search(r'data-dx="([\w-]+)"', attrs); name = d.group(1) if d else 'page%d' % (sum(x.startswith('page') for x in moved) + 1)
    moved.append(name); return '<script%s src="%s"></script>' % (attrs, asset(None, name, data=body.encode('utf-8')))
H = re.sub(r'<script([^>]*)>([\s\S]*?)</script>', outline, H)
OLD_LOAD = 's.text=src.text; document.head.appendChild(s); }catch(e){} if(window.dxGlobeStart) setTimeout(window.dxGlobeStart,30); }'
if 'three' in moved:   # the loader: fetch the file once, start the globe when it has run (dxGlobeStart does nothing until THREE exists)
    assert H.count(OLD_LOAD) == 1, 'lazy-globe loader not found: update live.py with web/src/mobile_opt.py'
    H = H.replace(OLD_LOAD, 'if(src.getAttribute(\'data-src\')){ if(src.dataset.loading) return; src.dataset.loading=\'1\'; s.src=src.getAttribute(\'data-src\'); '
                  's.onload=function(){ if(window.dxGlobeStart) setTimeout(window.dxGlobeStart,30); }; } else s.text=src.text; ' + OLD_LOAD[len('s.text=src.text; '):])
# ── installable app (w-pwa): icons, manifest, head tags; the service worker is written below with this build's stamp ──
PWA = ROOT + '/src/pwa'
ico = {n: asset(PWA + '/' + n, n[:-4], 'icons', 'png') for n in ('icon-192.png', 'icon-512.png', 'maskable-192.png', 'maskable-512.png', 'apple-touch-icon.png', 'favicon-32.png', 'badge-72.png')}
manifest = {'id': './', 'name': 'Drugbox', 'short_name': 'Drugbox', 'description': 'The professional network for pharma, cosmetics & medical devices.',
            'lang': 'en', 'dir': 'auto', 'start_url': './', 'scope': './', 'display': 'standalone', 'orientation': 'any',
            'background_color': '#ffffff', 'theme_color': '#ffffff', 'categories': ['business', 'medical', 'social'],
            'icons': [{'src': ico['icon-192.png'], 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
                      {'src': ico['icon-512.png'], 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
                      {'src': ico['maskable-192.png'], 'sizes': '192x192', 'type': 'image/png', 'purpose': 'maskable'},
                      {'src': ico['maskable-512.png'], 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]}
MAN = json.dumps(manifest, indent=1, ensure_ascii=False) + '\n'
open(OUT + '/manifest.webmanifest', 'w', encoding='utf-8').write(MAN)
HEAD = ('<link rel="manifest" href="manifest.webmanifest">\n<meta name="theme-color" content="#ffffff">\n'
        '<link rel="icon" type="image/png" sizes="32x32" href="%s">\n<link rel="apple-touch-icon" href="%s">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="Drugbox">\n<meta name="apple-mobile-web-app-status-bar-style" content="default">\n') % (ico['favicon-32.png'], ico['apple-touch-icon.png'])
hz = H.find('</head>'); assert 0 < hz < H.find('<body'), 'no </head> before <body>: cannot place the app manifest tags'
H = H[:hz] + HEAD + H[hz:]
cfg = json.dumps({'url': url, 'anonKey': key, 'realtime': os.environ.get('DRUGBOX_REALTIME', '1') != '0'}).replace('<', '\\u003c')   # never ends the <script>
live = ('<style data-dx="live">.lg-demo{display:none!important}[data-sim]{display:none!important}</style>\n'
        '<script data-dx="live-config">window.DRUGBOX_CONFIG=' + cfg + ';</script>\n'
        f'<script data-dx="supabase-js" src="{lib}"></script>\n<script data-dx="live-adapter" src="{ada}"></script>\n'
        + ''.join(f'<script data-dx="live-{n}" src="{a}"></script>\n' for n, a in xtra))
z = H.rfind('</body>'); H = H[:z] + live + H[z:]
if sentry:   # first script after the charset: it must be there before anything can throw (the loader queues errors until the SDK arrives)
    cm = re.search(r'<meta charset="[^"]*">', H)
    assert cm and cm.start() < H.find('</head>'), 'no <meta charset> in <head>: cannot place the Sentry loader'
    H = H[:cm.end()] + '\n<script data-dx="sentry-loader" src="%s" crossorigin="anonymous"></script>' % sentry + H[cm.end():]
# the build stamp: everything this deploy serves (the page, the manifest, the worker's source and offline page); it goes into the
# config (window.DRUGBOX_CONFIG.build) and into sw.js — a new deploy is a new worker, which removes the old version's caches
OFFLINE = open(PWA + '/offline.html', encoding='utf-8').read().replace('__ICON_DATA__', 'data:image/png;base64,' + base64.b64encode(open(PWA + '/icon-192.png', 'rb').read()).decode())
SWSRC = open(PWA + '/sw.js', encoding='utf-8').read()
build = hashlib.sha256('\0'.join([H, MAN, SWSRC, OFFLINE]).encode('utf-8')).hexdigest()[:12]
cfgb = cfg[:-1] + ', "build": "%s"' % build + (', "vapidPublicKey": "%s"' % vapid if vapid else '') + '}'
assert H.count('window.DRUGBOX_CONFIG=' + cfg + ';') == 1; H = H.replace('window.DRUGBOX_CONFIG=' + cfg + ';', 'window.DRUGBOX_CONFIG=' + cfgb + ';')
SW = (SWSRC.replace('__VERSION__', build).replace('__ICON__', ico['icon-192.png']).replace('__BADGE__', ico['badge-72.png'])
      .replace('__OFFLINE__', json.dumps(OFFLINE, ensure_ascii=False).replace('<', '\\u003c')))
assert '__' + 'VERSION__' not in SW and '__OFFLINE__' not in SW
open(OUT + '/sw.js', 'w', encoding='utf-8').write(SW)
open(OUT + '/index.html', 'w', encoding='utf-8').write(H)
# N-3: only the files this index.html references are published — older hashed copies (an old adapter, an old video) are removed
used = set(re.findall(r'(?:src|data-src|href)="((?:js|media|icons)/[\w.-]+)"', H)) | set(ico.values()); stale = []
for sub in ('js', 'media', 'icons'):
    for f in sorted(os.listdir(f'{OUT}/{sub}')):
        if f'{sub}/{f}' not in used: os.remove(f'{OUT}/{sub}/{f}'); stale.append(f'{sub}/{f}')
# hosting headers (CSP, frame, cache): ONE template, deploy/vercel.json, with this build's Supabase origin (and Sentry's hosts only when set)
tpl = os.path.join(os.path.dirname(ROOT), 'deploy', 'vercel.json')
if not os.path.exists(tpl): raise SystemExit('deploy/vercel.json (the hosting headers template) is missing')
origin = '%s://%s' % (u.scheme, u.netloc)
vj = json.loads(open(tpl, encoding='utf-8').read().replace('https://YOUR-PROJECT.supabase.co', origin).replace('wss://YOUR-PROJECT.supabase.co', origin.replace('https://', 'wss://').replace('http://', 'ws://')))
def add_src(csp, directive, hosts):
    parts = [p.strip() for p in csp.split(';')]; i = next(k for k, p in enumerate(parts) if p.split(' ')[0] == directive)
    parts[i] = ' '.join([parts[i]] + [h for h in hosts if h not in parts[i].split(' ')]); return '; '.join(parts)
csps = [h for r in vj['headers'] for h in r['headers'] if h['key'] == 'Content-Security-Policy']
assert csps, 'deploy/vercel.json has no Content-Security-Policy'
if sentry:
    for h in csps:
        h['value'] = add_src(h['value'], 'script-src', sorted({'https://' + urlparse(sentry).hostname, 'https://browser.sentry-cdn.com'}))
        h['value'] = add_src(h['value'], 'connect-src', ['https://*.sentry.io'])
vj.pop('$comment', None)   # the template's note is for people; the published file carries only what Vercel reads
assert 'YOUR-PROJECT' not in json.dumps(vj), 'deploy/vercel.json: a YOUR-PROJECT placeholder was not replaced'
open(OUT + '/vercel.json', 'w', encoding='utf-8').write(json.dumps(vj, indent=2, ensure_ascii=False) + '\n')
print('live build →', OUT, '| index.html %.2f MB' % (len(H.encode('utf-8')) / 1e6), '| scripts:', lib, ada, ' '.join(a for _, a in xtra), '+ %d page scripts as files' % len(moved),
      '| media:', 'splash' if m else 'none', '| removed old files: %d' % len(stale), '| lite copy → no-script notice' if lite else '', '| app: sw.js %s, manifest, %d icons%s' % (build, len(ico), ', push' if vapid else ''), '| sentry loader' if sentry else '')
