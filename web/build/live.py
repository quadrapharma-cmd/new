"""Live build: the demo build + the data adapter. Writes web/dist/live/ (index.html + separate, cacheable files).
The demo build (web/dist/drugbox.html) is not changed.
Needs DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY (public values; never the service key)."""
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
DEMO = ROOT + '/dist/drugbox.html'
# the live app is the demo build: refuse to package an older demo than the sources (run web/build/build.py first)
srcs = [ROOT + '/base/app.html'] + [f for f in glob.glob(ROOT + '/src/*') if os.path.isfile(f) and not f.endswith(('_static.html', '_static.css'))]
newer = [os.path.relpath(f, ROOT) for f in srcs if os.path.getmtime(f) > os.path.getmtime(DEMO)] if os.path.exists(DEMO) else ['(no demo build)']
if newer and os.environ.get('DRUGBOX_ALLOW_STALE') != '1':
    raise SystemExit('web/dist/drugbox.html is older than %s — run python3 web/build/build.py first (or DRUGBOX_ALLOW_STALE=1)' % ', '.join(newer[:3]))
OUT = ROOT + '/dist/live'; os.makedirs(OUT + '/js', exist_ok=True); os.makedirs(OUT + '/media', exist_ok=True)
def asset(src, name, sub='js', ext='js', data=None):   # content-hashed file name → safe to cache forever on a CDN
    data = data if data is not None else open(src, 'rb').read(); h = hashlib.sha256(data).hexdigest()[:10]; fn = f'{name}.{h}.{ext}'
    open(f'{OUT}/{sub}/{fn}', 'wb').write(data); return f'{sub}/{fn}'
lib = asset(ROOT + '/src/vendor/supabase-2.45.4.min.js', 'supabase')
ada = asset(ROOT + '/src/live/adapter.js', 'adapter')
H = open(DEMO, encoding='utf-8').read()
# the splash video is most of the demo's weight: online it is a separate, cacheable file (same bytes, same markup otherwise)
m = re.search(r'<source src="data:video/mp4;base64,([A-Za-z0-9+/=]+)"', H)
if m: H = H[:m.start()] + '<source src="' + asset(None, 'splash', 'media', 'mp4', base64.b64decode(m.group(1))) + '"' + H[m.end():]
cfg = json.dumps({'url': url, 'anonKey': key, 'realtime': os.environ.get('DRUGBOX_REALTIME', '1') != '0'}).replace('<', '\\u003c')   # never ends the <script>
live = ('<style data-dx="live">.lg-demo{display:none!important}[data-sim]{display:none!important}</style>\n'
        '<script data-dx="live-config">window.DRUGBOX_CONFIG=' + cfg + ';</script>\n'
        f'<script data-dx="supabase-js" src="{lib}"></script>\n<script data-dx="live-adapter" src="{ada}"></script>\n')
z = H.rfind('</body>'); open(OUT + '/index.html', 'w', encoding='utf-8').write(H[:z] + live + H[z:])
# hosting headers (CSP, frame, cache): the template in the repository root, with this build's Supabase origin
tpl = os.path.join(os.path.dirname(ROOT), 'vercel.json')
if os.path.exists(tpl):
    origin = '%s://%s' % (u.scheme, u.netloc)
    open(OUT + '/vercel.json', 'w', encoding='utf-8').write(open(tpl, encoding='utf-8').read().replace('https://YOUR-PROJECT.supabase.co', origin).replace('wss://YOUR-PROJECT.supabase.co', origin.replace('https://', 'wss://').replace('http://', 'ws://')))
print('live build →', OUT, '| scripts:', lib, ada, '| media:', 'splash' if m else 'none')
