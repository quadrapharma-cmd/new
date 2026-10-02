import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = ROOT + '/src'; BUILD = ROOT + '/build'; BASE = ROOT + '/base/app.html'
OUT = os.environ.get('DRUGBOX_OUT', ROOT + '/dist/drugbox.html')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
import json, subprocess
H = open(BASE, encoding='utf-8').read()
HEX, ILL = open(SRC + '/hex.json').read(), open(SRC + '/ill.json').read()
MODULES = [('core', 'core.js'), ('brand', 'brand.js'), ('craft', 'craft.js'), ('batch1', 'batch1.js'), ('batch2', 'batch2.js'), ('batch3', 'batch3.js'), ('directory', 'directory.js'), ('deals', 'deals.js'), ('qrcode', 'qrcode.min.js'), ('directory2', 'directory2.js'), ('directory3', 'directory3.js'), ('hubdata', 'hub-data.js'), ('hubui', 'hub-ui.js'), ('a11y', 'a11y.js'), ('links', 'links.js'), ('afford', 'afford.js'), ('i18n', 'i18n.js'), ('molecules', 'molecules.js'), ('landed', 'landed.js'), ('tiers', 'tiers.js'), ('profposts', 'profposts.js'), ('videos', 'videos.js'), ('moderation', 'moderation.js'), ('checkout', 'checkout.js'), ('share', 'share.js')]
CSS = ['brand.css', 'craft.css', 'batch1.css', 'batch2.css', 'batch3.css', 'directory.css', 'directory2.css', 'directory3.css', 'deals.css', 'hub.css', 'a11y.css', 'i18n.css', 'molecules.css', 'landed.css', 'tiers.css', 'profposts.css', 'videos.css', 'moderation.css', 'checkout.css', 'share.css']
scripts = ''
for name, f in MODULES:
    js = open(SRC + '/' + f, encoding='utf-8').read().replace('__HEX__', HEX).replace('__ILL__', ILL)
    open(BUILD + '/_chk.js', 'w').write(js)
    r = subprocess.run(['node', '--check', BUILD + '/_chk.js'], capture_output=True, text=True)
    print(f'{name:7s} syntax', 'OK' if r.returncode == 0 else 'FAIL ' + r.stderr[:300])
    assert r.returncode == 0
    scripts += '<script data-dx="' + name + '">\n' + js + '\n</script>\n'      # one tag per module: a failure can't stop the others
css = '\n'.join(open(SRC + '/' + c, encoding='utf-8').read() for c in CSS)
k = H.find('</style>'); H = H[:k] + '\n/* ═════════ Drugbox layers: brand · craft · batches ═════════ */\n' + css + H[k:]
z = H.rfind('</body>'); H = H[:z] + scripts + H[z:]
open(OUT, 'w', encoding='utf-8').write(H); print(len(H)//1024, 'KB')
exec(open(SRC + '/mobile_opt.py').read())   # final step: light and safe on phones
