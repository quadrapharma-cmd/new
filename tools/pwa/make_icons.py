"""App icons of the installable live app (w-pwa), made from the approved Drugbox mark (LOGO_ICON in web/base/app.html).
Writes web/src/pwa/*.png — committed, so the live build only copies them (web/build/live.py) and stays deterministic.
Run again only when the mark changes: python3 tools/pwa/make_icons.py  (same input → the same bytes)."""
import os, re, io, base64
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'web', 'src', 'pwa')
H = open(os.path.join(ROOT, 'web', 'base', 'app.html'), encoding='utf-8').read()
m = re.search(r'\bLOGO_ICON\s*=\s*["\']data:image/png;base64,([A-Za-z0-9+/=]+)', H)
if not m: raise SystemExit('LOGO_ICON (data:image/png) not found in web/base/app.html')
mark = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert('RGBA')
mark = mark.crop(mark.getbbox())                        # the mark only, no empty border

def icon(size, share, bg):
    """the mark centred, its longer side = share × size, on bg (None: transparent)"""
    im = Image.new('RGBA', (size, size), bg or (0, 0, 0, 0))
    k = share * size / max(mark.size); w, h = max(1, round(mark.width * k)), max(1, round(mark.height * k))
    im.alpha_composite(mark.resize((w, h), Image.LANCZOS), ((size - w) // 2, (size - h) // 2))
    return im if bg is None else im.convert('RGB')

WHITE = (255, 255, 255, 255)
ICONS = {   # name: (size, share of the side, background)
    'icon-192.png': (192, .92, None), 'icon-512.png': (512, .92, None),            # purpose "any": the mark as it is
    'maskable-192.png': (192, .60, WHITE), 'maskable-512.png': (512, .60, WHITE),  # purpose "maskable": inside the 80 % safe circle
    'apple-touch-icon.png': (180, .74, WHITE),                                      # iOS fills transparency with black: white tile
    'favicon-32.png': (32, 1.0, None),
}
def badge(size):
    """Android's status-bar badge: one colour (white) on transparent — the mark's outline only"""
    a = icon(size, .92, None).getchannel('A').point(lambda v: 255 if v > 96 else 0)
    im = Image.new('RGBA', (size, size), (255, 255, 255, 0)); im.putalpha(a); return im
os.makedirs(OUT, exist_ok=True)
for name, (size, share, bg) in ICONS.items():
    icon(size, share, bg).save(os.path.join(OUT, name), format='PNG', optimize=False, compress_level=9)
    print(name, size, os.path.getsize(os.path.join(OUT, name)), 'bytes')
badge(72).save(os.path.join(OUT, 'badge-72.png'), format='PNG', optimize=False, compress_level=9); print('badge-72.png 72')
