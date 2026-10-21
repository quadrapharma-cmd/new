"""Render check for the name rule (S-03): do two names that LOOK the same always get the same skeleton?
Every letter the live app's rule allows (Latin, Arabic, Greek, Cyrillic), alone and with each mark the rule lets stand apart from it
(Arabic in its four joining positions), is drawn on a canvas with each font and size below, and compared:
  exact  units that draw the SAME pixels but have DIFFERENT skeletons (any two allowed units)
  near   units that draw within THRESHOLD of a common letter (basic Latin, the Arabic alphabet, basic Greek and Cyrillic, common
         accented letters) — the difference measured as in atk-unicode-r2: the sum of the alpha differences over the common
         letter's ink — but have a different skeleton
Reads the generated rule of web/src/live/adapter.js (run `node tools/names/name_rule.mjs --write` first).
  python3 tools/names/render_scan.py [OUT.json] [THRESHOLD]      (Playwright 1.56 Chromium; default threshold 0.025 = 2.5%)
Exit 1 when an exact pair is found, or a near pair below the threshold that is not one of the Arabic dot pairs every Arabic reader
tells apart (ص/ض, ط/ظ, ع/غ, ح/خ/ج … — letters of the Arabic block whose difference is a dot or a stroke of their own).
History: 0039 (second version) — African noon ࢽ / ن and qaf ࢼ / ف before a letter; third version — e + U+0335, Τ + U+0304, i/ı/j +
U+0307 (marks that NFKC cannot join are refused), Ч / Ɥ U+A78D and the empty boxes of Latin Extended-G (letters from the everyday
blocks only), ӏ U+04CF / l (the skeleton maps ӏ to l: tools/names/name_rule.mjs, PIXEL_TWINS)."""
import json, os, sys
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, '../../web/src/live/adapter.js'), encoding='utf8').read()
a = src.index('/* >>> generated'); b = src.index('/* <<< generated */'); gen = src[src.index('\n', a) + 1:b]
ARGS = [x for x in sys.argv[1:] if not x.startswith('--')]
OUT = ARGS[0] if ARGS else None
THR = float(ARGS[1]) if len(ARGS) > 1 else 0.025
TWINS = os.path.join(HERE, 'pixel-twins.txt')
# the fonts: the app's own Latin font (Poppins, embedded in web/base/app.html), and the system fonts a browser falls back to here
FONTS = ['14px "DejaVu Sans"', '15px "DejaVu Sans"', '32px "DejaVu Sans"', '15px "FreeSans"', '15px "FreeSerif"', '15px "Liberation Sans"', '15px sans-serif',
         '15px Poppins', '600 15px Poppins']
import re
FACES = ''.join(re.findall(r"@font-face\{font-family:'Poppins'[^}]*\}", open(os.path.join(HERE, '../../web/base/app.html'), encoding='utf8').read()))
JS = r"""([gen, fonts, thr]) => {
 const F = new Function(gen + '\nreturn {nmNorm,nmProblem,nmSkel};')();
 const ok = (s) => F.nmProblem(F.nmNorm(s)) === '';
 const L = [], M = [];
 for (let c = 0x41; c <= 0x1FFFF; c++) { if (c >= 0xD800 && c <= 0xDFFF) continue; const s = String.fromCodePoint(c);
   if (/^\p{L}$/u.test(s) && ok(s) && F.nmNorm(s) === s) L.push(s);
   if (/^\p{M}$/u.test(s)) M.push(s); }
 const units = new Set();
 for (const l of L) { units.add(l); for (const m of M) { const n = F.nmNorm(l + m); if (n !== l && ok(n)) units.add(n); } }
 const U = [...units];
 const ar = (s) => /\p{Script=Arabic}/u.test(s);
 const T = [];
 for (const s of 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') T.push(s);
 for (const s of 'ابتثجحخدذرزسشصضطظعغفقكلمنهوياأإآةىئؤء') T.push(s);
 for (let c = 0x410; c <= 0x44F; c++) T.push(String.fromCharCode(c));
 for (let c = 0x391; c <= 0x3C9; c++) if (/\p{L}/u.test(String.fromCharCode(c))) T.push(String.fromCharCode(c));
 for (const s of ['é','è','á','à','ó','ö','ü','ç','ñ','í','ï','â','ê','î','ô','û','ş','ğ','ı','İ','ë','ё','й']) T.push(s.normalize('NFC'));
 const Tu = [...new Set(T)];
 const W = 64, H = 64;
 const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d', {willReadFrequently: true});
 const shape = (u, pos) => !ar(u) ? u : pos === 'init' ? u + 'ـ' : pos === 'medi' ? 'ـ' + u + 'ـ' : pos === 'fina' ? 'ـ' + u : u;
 function bmp(u, pos, font) { x.clearRect(0, 0, W, H); x.font = font; x.fillStyle = '#000'; x.direction = ar(u) ? 'rtl' : 'ltr'; x.textAlign = 'center'; x.fillText(shape(u, pos), W / 2, 44);
   const d = x.getImageData(0, 0, W, H).data, a = new Uint8Array(W * H); let ink = 0, h = 0; for (let i = 0; i < W * H; i++) { a[i] = d[i * 4 + 3]; ink += a[i]; h = (Math.imul(h, 31) + a[i]) | 0; } return {a, ink, h}; }
 const exact = [], near = [];
 for (const font of fonts) for (const pos of ['isol', 'init', 'medi', 'fina']) {
   const g = new Map(); const bm = new Map();
   for (const u of U) { if (pos !== 'isol' && !ar(u)) continue; const r = bmp(u, pos, font); if (!r.ink) continue; bm.set(u, r);
     const k = (ar(u) ? 'A' : 'X') + r.h; if (!g.has(k)) g.set(k, []); g.get(k).push(u); }
   for (const us of g.values()) if (us.length > 1 && new Set(us.map(F.nmSkel)).size > 1) exact.push([font, pos, us.map((s) => [s, [...s].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), F.nmSkel(s)])]);
   if (!/^15px/.test(font)) continue;
   for (const t of Tu) { if (pos !== 'isol' && !ar(t)) continue; const tb = bmp(t, pos, font), tk = F.nmSkel(t); if (!tb.ink) continue; const lim = thr * tb.ink;
     for (const [u, ub] of bm) { if (F.nmSkel(u) === tk || Math.abs(tb.ink - ub.ink) > 3 * lim) continue;
       let s = 0; for (let i = 0; i < W * H && s <= lim; i++) s += Math.abs(tb.a[i] - ub.a[i]);
       if (s <= lim) near.push([font, pos, t, u, +(s / tb.ink).toFixed(4), [...u].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), tk, F.nmSkel(u)]); } }
 }
 near.sort((p, q) => p[4] - q[4]);
 return {letters: L.length, units: U.length, exact, near};
}"""
with sync_playwright() as p:
    br = p.chromium.launch(args=['--no-sandbox']); pg = br.new_page(); pg.set_content('<style>' + FACES + '</style><p style="font-family:Poppins">x</p>')
    pg.evaluate("Promise.all(['400 15px Poppins', '600 15px Poppins'].map((f) => document.fonts.load(f)))")
    assert pg.evaluate("document.fonts.check('600 15px Poppins')"), 'Poppins did not load'
    r = pg.evaluate(JS, [gen, FONTS, THR]); br.close()
if OUT: json.dump(r, open(OUT, 'w'), ensure_ascii=False, indent=1)
# the Arabic dot pairs: two letters of the Arabic block that are different letters to every reader (a dot, a stroke, a hamza)
arabic_block = lambda s: all(0x0600 <= ord(c) <= 0x06FF or 0x0750 <= ord(c) <= 0x077F for c in s)
bad_near = [n for n in r['near'] if not (arabic_block(n[2]) and arabic_block(n[3]))]
print('letters', r['letters'], 'units', r['units'], 'exact pairs', len(r['exact']), 'near pairs', len(r['near']), 'near outside the Arabic dot pairs', len(bad_near))
for e in r['exact'][:40]: print('EXACT', e)
for n in bad_near[:60]: print('NEAR ', n)
for n in [n for n in r['near'] if n not in bad_near][:12]: print('arabic', n)
if '--write' in sys.argv:   # add the pairs found to tools/names/pixel-twins.txt (the generator gives them one skeleton)
    pairs = set()
    if os.path.exists(TWINS):
        for l in open(TWINS, encoding='utf8'):
            m = re.match(r'^([0-9A-F]+) ; ([0-9A-F]+)', l)
            if m: pairs.add((int(m[1], 16), int(m[2], 16)))
    base = lambda u: [ord(c) for c in u if not (0x064B <= ord(c) <= 0x0652 or ord(c) == 0x0670)]   # the harakat the skeleton drops
    found = [[e[2][0][0], m[0]] for e in r['exact'] for m in e[2][1:]] + [[n[2], n[3]] for n in bad_near]
    for a_, b_ in found:
        x, y = base(a_), base(b_)
        if len(x) == 1 and len(y) == 1 and x != y: pairs.add(tuple(sorted((x[0], y[0]))))
    import unicodedata
    with open(TWINS, 'w', encoding='utf8') as f:
        f.write('# Letters the name rule allows that draw alike (the same pixels, or within %.1f%% of a common letter) while their TR39 skeletons\n'
                '# differ: tools/names/render_scan.py --write, Chromium canvas, fonts: %s.\n'
                '# tools/names/name_rule.mjs gives each pair one skeleton (the skeleton of the more common letter). Generated, never edited by hand.\n'
                % (THR * 100, ', '.join(FONTS)))
        for a_, b_ in sorted(pairs): f.write('%04X ; %04X # %s / %s — %s / %s\n' % (a_, b_, chr(a_), chr(b_), unicodedata.name(chr(a_), '?'), unicodedata.name(chr(b_), '?')))
    print('written', TWINS, len(pairs), 'pairs')
sys.exit(1 if r['exact'] or bad_near else 0)
