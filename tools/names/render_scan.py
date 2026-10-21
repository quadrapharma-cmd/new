"""Render check for the name rule (S-03): do two names that LOOK the same always get the same skeleton?
Every letter the live app's rule allows (Latin, Arabic, Greek, Cyrillic), alone and with every mark the rule still lets stand after
it (a mark NFKC joins to the letter gives another letter; under the fourth version no mark stands on its own), is drawn on a canvas
and compared with EVERY allowed letter — every script against every script, Arabic against Arabic included, the Arabic letters in
their four joining positions — in the app's own font (Poppins, embedded in web/base/app.html, regular and semibold; it has no Arabic,
so Arabic falls back like in the app) and the system fonts a browser falls back to here, at 14, 15 and 16 px.
  A letter is drawn with a font only when that font has it (a letter the font lacks is drawn by the fallback font, which is scanned
  on its own). The difference of two drawings: each is aligned on its ink (centre of its box) and blurred (Gaussian, sigma 1 px — the
  eye does not see where within a pixel a small mark sits), and the summed difference of every pixel is divided by what ONE Arabic dot
  adds in the same font and size (the median of ح/خ, ر/ز, د/ذ, ع/غ, ص/ض, ط/ظ, ٮ/ب, ں/ن). Letters a reader tells apart by a dot are
  about 1.0 (the lowest, ص / ض at 16 px, 0.78); a sukun where a dot would be is 0.53 («حْ» / «خ», 15 px FreeSerif — atk-unicode-r3:
  «حْالد» drew as «خالد»). A pair below THRESHOLD (default 0.6) whose skeletons differ fails the scan.
Reads the generated rule of web/src/live/adapter.js (run `node tools/names/name_rule.mjs --write` first), or with --rule REV the
adapter of a git revision (`--rule e972163` is the third version, 0039_names_rule_3).
  python3 tools/names/render_scan.py [OUT.json] [THRESHOLD]   Playwright 1.56 Chromium; exit 1 when a pair is found
  --rule REV            scan the rule of that git revision instead of the working tree
  --must-find U/T       exit 0 only when the pair U / T (e.g. حْ/خ) is among the pairs found, 1 otherwise — the proof that the scan
                        sees a look-alike: python3 tools/names/render_scan.py --rule e972163 --must-find حْ/خ
  --sizes 14,15,16      --fonts-quick (DejaVu Sans and FreeSerif only, the fonts that draw Arabic here)
  --write               add the pairs found (single letters) to tools/names/pixel-twins.txt — the generator gives each pair one
                        skeleton; only for letters that truly draw alike, never for a letter + mark
History: 0039 (second version) — African noon ࢽ / ن and qaf ࢼ / ف before a letter; third version — e + U+0335, Τ + U+0304, i/ı/j +
U+0307, Ч / Ɥ U+A78D, the empty boxes of Latin Extended-G, ӏ U+04CF / l; fourth version — this scan compares every pair (it skipped
Arabic-Arabic pairs and compared drawings by a hash, so it could not see «حْ» / «خ»); Arabic diacritics are removed from names."""
import json, os, re, subprocess, sys, time
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '../..'))
ARGS = [x for x in sys.argv[1:] if not x.startswith('--')]
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
REV = opt('--rule'); MUST = opt('--must-find'); SIZES = [int(x) for x in opt('--sizes', '14,15,16').split(',')]
for v in (REV, MUST, opt('--sizes')):
    if v in ARGS: ARGS.remove(v)
OUT = ARGS[0] if ARGS else None
THR = float(ARGS[1]) if len(ARGS) > 1 else 0.6
src = subprocess.run(['git', 'show', REV + ':web/src/live/adapter.js'], cwd=ROOT, capture_output=True, text=True, check=True).stdout if REV \
    else open(os.path.join(ROOT, 'web/src/live/adapter.js'), encoding='utf8').read()
a = src.index('/* >>> generated'); b = src.index('/* <<< generated */'); gen = src[src.index('\n', a) + 1:b]
TWINS = os.path.join(HERE, 'pixel-twins.txt')
FAMILIES = ['"DejaVu Sans"', '"FreeSerif"'] if '--fonts-quick' in sys.argv else \
    ['Poppins', '600 Poppins', '"DejaVu Sans"', '"FreeSans"', '"FreeSerif"', '"Liberation Sans"', 'sans-serif']
FONTS = [(f.split(' ')[0] + ' ' + str(s) + 'px ' + f.split(' ', 1)[1]) if f.startswith('600 ') else (str(s) + 'px ' + f) for f in FAMILIES for s in SIZES]
FACES = ''.join(re.findall(r"@font-face\{font-family:'Poppins'[^}]*\}", open(os.path.join(ROOT, 'web/base/app.html'), encoding='utf8').read()))

SETUP = r"""([gen]) => {
 const F = new Function(gen + '\nreturn {nmNorm,nmProblem,nmSkel};')();
 const ok = (s) => F.nmProblem(F.nmNorm(s)) === '';
 const L = [], M = [];
 for (let c = 0x41; c <= 0x1FFFF; c++) { if (c >= 0xD800 && c <= 0xDFFF) continue; const s = String.fromCodePoint(c);
   if (/^\p{L}$/u.test(s) && ok(s) && F.nmNorm(s) === s) L.push(s);
   if (/^\p{M}$/u.test(s)) M.push(s); }
 const units = new Set(L);
 for (const l of L) for (const m of M) { const n = F.nmNorm(l + m); if (n !== l && ok(n)) units.add(n); }
 const U = [...units], LS = new Set(L);
 window.__S = { U, T: L, sk: new Map(U.map((u) => [u, F.nmSkel(u)])), isLetter: (u) => LS.has(u) };
 return { letters: L.length, units: U.length, withMark: U.filter((u) => !LS.has(u)).length };
}"""

SCAN = r"""([font, thr]) => {
 const { U, T, sk, isLetter } = window.__S;
 const W = 48, H = 48, BASE = 32, SIG = 1, R = 3;
 const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d', { willReadFrequently: true });
 const ar = (s) => /\p{Script=Arabic}/u.test(s);
 const shape = (u, pos) => pos === 'init' ? u + 'ـ' : pos === 'medi' ? 'ـ' + u + 'ـ' : pos === 'fina' ? 'ـ' + u : u;
 const K = []; { let s = 0; for (let i = -R; i <= R; i++) { const v = Math.exp(-i * i / (2 * SIG * SIG)); K.push(v); s += v; } for (let i = 0; i < K.length; i++) K[i] /= s; }
 const tmp = new Float32Array(W * H), SIZE = /(\d+)px/.exec(font)[1] + 'px';
 function hash(u, f) {   // does the font draw u itself? (with a fallback that draws everything, Unifont, a letter the font lacks looks like Unifont's)
   x.clearRect(0, 0, W, H); x.font = f; x.fillStyle = '#000'; x.direction = ar(u) ? 'rtl' : 'ltr'; x.textAlign = 'center'; x.fillText(u, W / 2, BASE);
   const d = x.getImageData(0, 0, W, H).data; let h = 0; for (let i = 3; i < d.length; i += 4) h = (Math.imul(h, 31) + d[i]) | 0; return h; }
 const has = (u) => hash(u, font + ', Unifont') !== hash(u, SIZE + ' Unifont');
 function draw(u, pos) {
   x.clearRect(0, 0, W, H); x.font = font; x.fillStyle = '#000'; x.direction = ar(u) ? 'rtl' : 'ltr'; x.textAlign = 'center'; x.fillText(shape(u, pos), W / 2, BASE);
   const d = x.getImageData(0, 0, W, H).data; let x0 = W, x1 = -1, ink = 0;
   for (let i = 0; i < W * H; i++) { const v = d[i * 4 + 3]; if (v) { ink += v; const c = i % W; if (c < x0) x0 = c; if (c > x1) x1 = c; } }
   if (!ink) return null;
   const sh = Math.round(W / 2 - (x0 + x1 + 1) / 2), a = new Float32Array(W * H);
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const c2 = c - sh; tmp[y * W + c] = c2 >= 0 && c2 < W ? d[(y * W + c2) * 4 + 3] : 0; }
   const t2 = new Float32Array(W * H);
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { let v = 0; for (let k = -R; k <= R; k++) { const X = c + k; if (X >= 0 && X < W) v += tmp[y * W + X] * K[k + R]; } t2[y * W + c] = v; }
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { let v = 0; for (let k = -R; k <= R; k++) { const Y = y + k; if (Y >= 0 && Y < H) v += t2[Y * W + c] * K[k + R]; } a[y * W + c] = v; }
   const b8 = new Float32Array(36); let sum = 0;
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const v = a[y * W + c]; b8[(y >> 3) * 6 + (c >> 3)] += v; sum += v; }
   return { a, b8, sum };
 }
 function l1(p, q, lim) {   // the summed pixel difference, or lim as soon as it reaches lim (ink and block sums bound it from below)
   if (Math.abs(p.sum - q.sum) >= lim) return lim;
   let s = 0; for (let i = 0; i < 36; i++) s += Math.abs(p.b8[i] - q.b8[i]); if (s >= lim) return lim;
   s = 0; for (let i = 0; i < W * H; i++) { s += Math.abs(p.a[i] - q.a[i]); if (s >= lim) return lim; } return s;
 }
 const REF = [['ح', 'خ'], ['ر', 'ز'], ['د', 'ذ'], ['ع', 'غ'], ['ص', 'ض'], ['ط', 'ظ'], ['ٮ', 'ب'], ['ں', 'ن']];
 const dot = REF.map(([p0, q0]) => l1(draw(p0, 'isol'), draw(q0, 'isol'), 1e12)).sort((p, q) => p - q)[REF.length >> 1];
 const lim = thr * dot, near = []; let pairs = 0, drawn = 0;
 for (const pos of ['isol', 'init', 'medi', 'fina']) {
   const us = pos === 'isol' ? U : U.filter(ar), ts = pos === 'isol' ? T : T.filter(ar), bm = new Map();
   for (const u of us) { if (!has(u)) continue; const r = draw(u, pos); if (r) bm.set(u, r); }
   if (pos === 'isol') drawn = bm.size;
   for (const u of us) { const p = bm.get(u); if (!p) continue; const ku = sk.get(u), lu = isLetter(u);
     for (const t of ts) { if (t === u || (lu && t < u)) continue; const q = bm.get(t); if (!q || sk.get(t) === ku) continue; pairs++;
       const m = l1(p, q, lim); if (m < lim) near.push([font, pos, u, t, +(m / dot).toFixed(3), [...u].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), [...t].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), ku, sk.get(t)]); } }
 }
 return { font, dot: +dot.toFixed(1), drawn, pairs, near };
}"""

t0 = time.time()
with sync_playwright() as p:
    br = p.chromium.launch(args=['--no-sandbox']); pg = br.new_page(); pg.set_content('<style>' + FACES + '</style><p style="font-family:Poppins">x</p>')
    pg.evaluate("Promise.all(['400 15px Poppins', '600 15px Poppins'].map((f) => document.fonts.load(f)))")
    assert pg.evaluate("document.fonts.check('600 15px Poppins')"), 'Poppins did not load'
    info = pg.evaluate(SETUP, [gen])
    print('rule', REV or 'working tree', '— letters', info['letters'], 'units', info['units'], '(with a mark:', str(info['withMark']) + ')', 'threshold', THR, flush=True)
    runs = []
    for f in FONTS:
        r = pg.evaluate(SCAN, [f, THR]); runs.append(r)
        print('  %-26s letters drawn %5d  dot %7.1f  pairs %9d  near %d' % (f, r['drawn'], r['dot'], r['pairs'], len(r['near'])), flush=True)
    br.close()
near = sorted([n for r in runs for n in r['near']], key=lambda n: n[4])
if OUT: json.dump({'rule': REV or 'working tree', 'threshold': THR, 'info': info, 'runs': [{k: v for k, v in r.items() if k != 'near'} for r in runs], 'near': near}, open(OUT, 'w'), ensure_ascii=False, indent=1)
distinct = {}
for n in near: distinct.setdefault(tuple(sorted((n[2], n[3]))), n)
print('pairs below %.2f of a dot with different skeletons: %d (%d distinct)  [%.0fs]' % (THR, len(near), len(distinct), time.time() - t0))
for n in sorted(distinct.values(), key=lambda n: n[4])[:80]: print('NEAR ', n)
if '--write' in sys.argv:   # add the pairs found to tools/names/pixel-twins.txt (the generator gives each group one skeleton)
    import unicodedata
    pairs = set()
    if os.path.exists(TWINS):
        for l in open(TWINS, encoding='utf8'):
            m = re.match(r'^([0-9A-F]+) ; ([0-9A-F]+)', l)
            if m: pairs.add((int(m[1], 16), int(m[2], 16)))
    unwritten = []
    for (a_, b_), n in distinct.items():
        ka, kb = n[7], n[8]
        diff = [(x, y) for x, y in zip(ka, kb) if x != y] if len(ka) == len(kb) else None
        if diff and all(unicodedata.category(x).startswith('M') and unicodedata.category(y).startswith('M') for x, y in diff):
            for x, y in diff: pairs.add(tuple(sorted((ord(x), ord(y)))))          # two letters that differ only in a mark: the marks
        elif len(a_) == 1 and len(b_) == 1: pairs.add(tuple(sorted((ord(a_), ord(b_)))))   # two letters
        else: unwritten.append(n)
    for n in unwritten: print('NOT WRITTEN (not two letters, nor two letters that differ only in a mark):', n)
    with open(TWINS, 'w', encoding='utf8') as f:
        f.write('# Letters (and marks) the name rule allows that draw alike while their skeletons differ: tools/names/render_scan.py --write\n'
                '# (blurred drawings within %.2f of an Arabic dot of each other), Chromium canvas, fonts: %s. Two letters that differ\n'
                '# only in a mark give the pair of marks (é / è: U+0300 / U+0301).\n'
                '# tools/names/name_rule.mjs gives each group one skeleton. Generated, never edited by hand.\n'
                % (THR, ', '.join(FAMILIES) + ' at ' + '/'.join(map(str, SIZES)) + ' px'))
        for a_, b_ in sorted(pairs): f.write('%04X ; %04X # %s / %s — %s / %s\n' % (a_, b_, chr(a_), chr(b_), unicodedata.name(chr(a_), '?'), unicodedata.name(chr(b_), '?')))
    print('written', TWINS, len(pairs), 'pairs')
if MUST:
    u_, t_ = MUST.split('/')
    hit = [n for n in near if {n[2], n[3]} == {u_, t_}]
    print(('FOUND ' if hit else 'NOT FOUND ') + MUST + (' — e.g. ' + str(hit[0]) if hit else ''))
    sys.exit(0 if hit else 1)
sys.exit(1 if near else 0)
