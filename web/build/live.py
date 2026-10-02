"""Live build: the demo build + the data adapter. Writes web/dist/live/ (index.html + separate, cacheable script files).
The demo build (web/dist/drugbox.html) is not changed.
Needs DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY (public values; never the service key)."""
import os, json, shutil, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
url, key = os.environ.get('DRUGBOX_SUPABASE_URL'), os.environ.get('DRUGBOX_SUPABASE_ANON_KEY')
if not url or not key: raise SystemExit('Set DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY')
if 'service_role' in key: raise SystemExit('Refusing to embed a service_role key in the browser build')
OUT = ROOT + '/dist/live'; os.makedirs(OUT + '/js', exist_ok=True)
def asset(src, name):                      # content-hashed file name → safe to cache forever on a CDN
    data = open(src, 'rb').read(); h = hashlib.sha256(data).hexdigest()[:10]; fn = f'{name}.{h}.js'
    open(f'{OUT}/js/{fn}', 'wb').write(data); return 'js/' + fn
lib = asset(ROOT + '/src/vendor/supabase-2.45.4.min.js', 'supabase')
ada = asset(ROOT + '/src/live/adapter.js', 'adapter')
H = open(ROOT + '/dist/drugbox.html', encoding='utf-8').read()
live = ('<style data-dx="live">.lg-demo{display:none!important}[data-sim]{display:none!important}</style>\n'
        '<script data-dx="live-config">window.DRUGBOX_CONFIG=' + json.dumps({'url': url, 'anonKey': key, 'realtime': os.environ.get('DRUGBOX_REALTIME', '1') != '0'}) + ';</script>\n'
        f'<script data-dx="supabase-js" src="{lib}"></script>\n<script data-dx="live-adapter" src="{ada}"></script>\n')
z = H.rfind('</body>'); open(OUT + '/index.html', 'w', encoding='utf-8').write(H[:z] + live + H[z:])
print('live build →', OUT, '| scripts:', lib, ada)
