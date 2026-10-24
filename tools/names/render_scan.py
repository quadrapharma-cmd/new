"""Render check for the name rule (S-03): do two names that LOOK the same always get the same skeleton?
Everything is drawn on a Chromium canvas the way the app draws a name — with the app's own FONT STACKS (English `Poppins, sans-serif`;
Arabic `Poppins, "Segoe UI", …, sans-serif` from web/src/i18n.css; the datalist popup's `system-ui, sans-serif`), so a letter Poppins
lacks is drawn by the fallback font next to a letter Poppins has — at weights 400, 500, 600 and 700 (the thread list and the chat header
draw names in bold) and 14, 15 and 16 px; and with each system font on its own (DejaVu Sans, FreeSans, FreeSerif, Liberation Sans) at
every weight too (sixth version: they were drawn at 400 and 700), for the machines whose fallback differs. Three parts:
  letters    every letter the live app's rule allows (Latin, Arabic, Greek, Cyrillic), alone and with every mark the rule still lets
             stand after it (none under the fourth and fifth versions), against EVERY allowed letter — every script against every
             script, Arabic against Arabic, the Arabic letters in their four joining positions
  sequences  every Arabic bigram and every trigram of the tooth-shaped letters (ب ت ث ن ي ى ی ں ئ پ) in the four positions, against
             every Arabic letter and bigram; bigrams of the basic Latin, Cyrillic and Greek letters against every letter and bigram —
             two sequences one letter apart are left to the letters part, which compares those letters in every joining position (a
             dot next to another letter measures a little under one dot at 16 px: «ہط» / «ہظ» 0.59, v-spoof-r1's 'measurement noise')
  names      whole names: real EN/AR names and every variant the rule allows of them — punctuation swapped, added or removed, spaces,
             word orders, brackets moved — drawn in the interface's direction (English left-to-right, Arabic right-to-left, the popup
             both ways), alone and inside a sentence (an Arabic or a Latin word before and / or after it): a name whose script runs
             against the interface direction is reordered by the bidi algorithm («(MBA) Ahmed Ali» drew exactly as «Ahmed Ali (MBA)»
             in Arabic, «Ali (علي) محمد» as «Ali محمد (علي)» in English — v-spoof-r1)
The difference of two drawings: each is aligned on its ink (centre of its box) and blurred (Gaussian, sigma 1 px — the eye does not see
where within a pixel a small mark sits), and the summed difference of every pixel is divided by ONE ARABIC DOT: the median of ح/خ, ر/ز,
د/ذ, ع/غ, ص/ض, ط/ظ, ٮ/ب, ں/ن drawn in the SAME font string, weight and size (a dot drawn bold is a bold dot: 274 at 400, 742 at 600
for 15 px here — the scan used to measure 400 only; a font without Arabic measures it in the font its stack falls back to). Letters a reader tells apart by a dot are about 1.0; a sukun
where a dot would be is 0.53 («حْ» / «خ», atk-unicode-r3); bold initial ئ / ث 0.35 (v-spoof-r1); bold «İ» / «i» 0.62 (round 5). A pair
below THRESHOLD (default 1.0 — sixth version, it was 0.6: the skeleton over-merges, so whatever draws within ONE dot of another letter in
some font and weight is its twin; one-dot pairs that measure under the median — ح / خ, ب / ن in some fonts — are twins too) whose
skeletons differ fails the scan. A letter no installed font has (drawn as the empty box) is not compared, and counted.
Sequences and whole names are also compared with every empty gap between two inked columns drawn one column wide (sixth version): a
space, or the wider gap after a letter that never joins the next one, does not change what the eye reads — «عبد الله» / «عبدالله» measured
~40 dots apart when the two drawings were only aligned on their centres (round 5). A pair counts when either measure is below THRESHOLD.
Reads the generated rule of web/src/live/adapter.js (run `node tools/names/name_rule.mjs --write` first), or with --rule REV the
adapter of a git revision (`--rule e972163` is the third version, 0039_names_rule_3; `--rule 0fbc662` the fourth, 0039_names_rule_4;
`--rule 91ca446` the fifth, 0039_names_rule_5).
  python3 tools/names/render_scan.py [OUT.json] [THRESHOLD]   Playwright 1.56 Chromium; exit 1 when a pair is found
  --part letters|sequences|names|all   (default all)
  --rule REV            scan the rule of that git revision instead of the working tree
  --must-find U/T       exit 0 only when the pair U / T is among the pairs found, 1 otherwise — the proof that the scan sees a
                        look-alike: --rule e972163 --part letters --must-find حْ/خ ; --rule 0fbc662 --part letters --must-find ث/ئ ;
                        --rule 0fbc662 --part names --must-find "(MBA) Ahmed Ali/Ahmed Ali (MBA)" ; --rule 91ca446 --part letters
                        --must-find İ/i ; --rule 91ca446 --part names --quick --must-find "عبد الله أحمد/عبدالله أحمد"
  --sizes 14,15,16  --weights 400,500,600,700   --quick (letters: the stacks only; sequences and names: 400 and 700 at 15 px)
  --write               add the pairs found (letters and beside parts) to tools/names/pixel-twins.txt — the generator gives each pair one
                        skeleton: two letters, two marks (two letters that differ only in a mark at the same place: é / è), or a
                        letter with a mark (two letters that differ in marks drawn at the same place by that letter only: ģ / ġ);
                        sixth version: a letter + mark and the letter (a mark that draws within a dot of nothing: bold Ḣ / H), and
                        the skeletons of an accented letter and another letter (once no new pair of letters is written). Run it
                        until the letters part finds nothing (each run regenerates nothing: node tools/names/name_rule.mjs --write)
History: 0039 (second version) — African noon ࢽ / ن and qaf ࢼ / ف before a letter; third version — e + U+0335, Τ + U+0304, i/ı/j +
U+0307, Ч / Ɥ U+A78D, the empty boxes of Latin Extended-G, ӏ U+04CF / l; fourth version — every pair compared (it skipped Arabic-Arabic
pairs and compared by a hash, so it could not see «حْ» / «خ»), Arabic diacritics removed; fifth version — the app's font stacks at
every weight (it scanned Poppins alone, 117 letters, and the fallback fonts at 400 only, so bold ئ / ث and ő / ổ passed), sequences,
whole names in both directions (bracket order); sixth version — one Arabic dot (bold İ / i at 0.62 passed 0.6), the system fonts at every
weight, two-letter sequences in the system fonts, gaps drawn one column wide (a space after a letter that never joins)."""
import itertools, json, os, re, subprocess, sys, time, unicodedata
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '../..'))
VALUED = ('--rule', '--must-find', '--sizes', '--weights', '--part')
def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
ARGS = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith('--') and sys.argv[i - 1] not in VALUED]
REV = opt('--rule'); MUST = opt('--must-find'); PART = opt('--part', 'all'); QUICK = '--quick' in sys.argv
SIZES = [int(x) for x in opt('--sizes', '14,15,16').split(',')]
WEIGHTS = [int(x) for x in opt('--weights', '400,500,600,700').split(',')]
OUT = ARGS[0] if ARGS else None
THR = float(ARGS[1]) if len(ARGS) > 1 else 1.0
src = subprocess.run(['git', 'show', REV + ':web/src/live/adapter.js'], cwd=ROOT, capture_output=True, text=True, check=True).stdout if REV \
    else open(os.path.join(ROOT, 'web/src/live/adapter.js'), encoding='utf8').read()
a = src.index('/* >>> generated'); b = src.index('/* <<< generated */'); gen = src[src.index('\n', a) + 1:b]
TWINS = os.path.join(HERE, 'pixel-twins.txt')
css = open(os.path.join(ROOT, 'web/src/i18n.css'), encoding='utf8').read()
AR_STACK = re.search(r'html\[lang=ar\] body[^{]*\{font-family:([^}]*)\}', css).group(1)
STACKS = [('EN', 'Poppins, sans-serif', 'ltr'), ('AR', AR_STACK, 'rtl'), ('UI', 'system-ui, sans-serif', None)]
SINGLE = ['"DejaVu Sans"', '"FreeSans"', '"FreeSerif"', '"Liberation Sans"']
FACES = ''.join(re.findall(r"@font-face\{font-family:'Poppins'[^}]*\}", open(os.path.join(ROOT, 'web/base/app.html'), encoding='utf8').read()))

# ── whole names: real names and their variants (punctuation swapped / added / removed, word orders, brackets moved) ──
BASE = ['Alİ Kaya', 'Ali Kaya', 'أبو بكر', 'نور الدين', 'نورالدين', 'Ahmed Ali', 'Dr. Ahmed Ali', "O'Brien", 'Al-Hassan', 'Ahmed Ali (MBA)', 'Mona El-Sayed', 'Ph/ Ahmed', 'Sara A. Ali', 'Ali, Ahmed',
        'Szőke Anna', 'Saʿīd Ḥasan', 'Νίκος (Nikos)', 'Мария Иванова', 'Dr. Мария Иванова',
        'عبدالله أحمد', 'عبد الله أحمد', 'أبوبكر محمد', 'د/ محمد علي', 'د. هالة الشامي', 'محمد (علي)', 'محمد، علي', 'عبدالرحمن',
        'Ahmed محمد', 'محمد Ahmed', 'ثروت عادل', 'هالة', 'زياد', 'خالد', 'Ziad (زياد)', 'أحمد علي (صيدلي)', 'محمد علي (أبو أحمد)',
        'Ahmed Ali (Pharm.D.)', 'هالة الشامي (Pharm.D.)', 'Dr. محمد علي', 'د. Ahmed Ali', 'محمد علي Ali', 'Mona (منى) Ali', 'علی رضا']
PUN = ['.', ',', '’', '-', '/', '،', '(', ')', ' ']
WRAPS = [('ب ', ' ب'), ('b ', ' b'), ('', ' ب'), ('', ' b'), ('ب ', ''), ('b ', '')]
def variants(s):
    out = {s}
    for i, c in enumerate(s):
        if c in PUN:
            for r in PUN + ['']: out.add(s[:i] + r + s[i + 1:])
    for i in range(len(s) + 1):
        for r in PUN: out.add(s[:i] + r + s[i:])
    w = s.split(' ')
    if len(w) <= 5:
        for perm in itertools.permutations(w): out.add(' '.join(perm))
    t = s.replace('(', '').replace(')', '')
    for i in range(len(t) + 1):
        for j in range(i, len(t) + 1): out.add(t[:i] + '(' + t[i:j] + ')' + t[j:]); out.add(t[:i] + ')' + t[i:j] + '(' + t[j:])
    tw = t.split(' ')
    for k in range(len(tw)):   # one word in brackets, then every order of the words
        ws = tw[:k] + ['(' + tw[k] + ')'] + tw[k + 1:]
        if len(ws) <= 5:
            for perm in itertools.permutations(ws): out.add(' '.join(perm))
    return out
NAMES = sorted(set().union(*[variants(x) for x in BASE]))

SETUP = r"""([gen, part, names]) => {
 const F = new Function(gen + '\nreturn {nmNorm,nmProblem,nmSkel};')();
 const ok = (s) => F.nmProblem(F.nmNorm(s)) === '';
 const L = [], M = [];
 for (let c = 0x41; c <= 0x1FFFF; c++) { if (c >= 0xD800 && c <= 0xDFFF) continue; const s = String.fromCodePoint(c);
   if (/^\p{L}$/u.test(s) && ok(s) && F.nmNorm(s) === s) L.push(s);
   if (/^\p{M}$/u.test(s)) M.push(s); }
 const units = new Set(L);
 for (const l of L) for (const m of M) { const n = F.nmNorm(l + m); if (n !== l && ok(n)) units.add(n); }
 const LS = new Set(L), ar = (s) => /\p{Script=Arabic}/u.test(s);
 const bi = (A) => { const r = []; for (const x of A) for (const y of A) r.push(x + y); return r; };
 let U = [...units], T = L, single = true;
 if (part === 'sequences') {
   const arab = L.filter(ar), tooth = [...'بتثنيىیںئپ'].filter((s) => LS.has(s));
   const lat = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'], cyr = L.filter((s) => s >= 'Ѐ' && s <= 'џ'), grk = L.filter((s) => s >= 'Ά' && s <= 'ώ');
   const tri = []; for (const x of tooth) for (const y of tooth) for (const z of tooth) tri.push(x + y + z);
   const seq = bi(arab).concat(tri, bi(lat), bi(cyr), bi(grk));
   U = seq; T = L.concat(seq); single = false;
 } else if (part === 'names') { U = names; T = names; }
 else if (part === 'beside') { U = L.filter((s) => s.normalize('NFD') !== s && [...s.normalize('NFD')].length > 1); T = []; }
 window.__F = F;
 const nn = (s) => F.nmNorm(s);
 U = [...new Set(U.map(nn).filter((s) => s && F.nmProblem(s) === ''))]; T = [...new Set(T.map(nn).filter((s) => s && F.nmProblem(s) === ''))];
 window.__S = { U, T, single, sk: new Map(U.concat(T).map((u) => [u, F.nmSkel(u)])), isLetter: (u) => LS.has(u) };
 return { letters: L.length, units: U.length, targets: T.length, withMark: part === 'letters' ? U.filter((u) => !LS.has(u)).length : 0 };
}"""

# one drawing context: the font string (a stack or one font), the font string the dot unit is drawn with (the same)
SCAN = r"""([font, arf, dirs, part, thr, check, gap]) => {
 const { U, T, single, sk, isLetter } = window.__S;
 const W = part === 'names' ? 400 : part === 'sequences' ? 112 : 64, H = 48, BASE = 32, SIG = 1, R = 3;
 const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d', { willReadFrequently: true });
 const ar = (s) => /\p{Script=Arabic}/u.test(s);
 const shape = (u, pos) => pos === 'init' ? u + 'ـ' : pos === 'medi' ? 'ـ' + u + 'ـ' : pos === 'fina' ? 'ـ' + u : u;
 const K = []; { let s = 0; for (let i = -R; i <= R; i++) { const v = Math.exp(-i * i / (2 * SIG * SIG)); K.push(v); s += v; } for (let i = 0; i < K.length; i++) K[i] /= s; }
 const tmp = new Float32Array(W * H), t2 = new Float32Array(W * H), SIZE = /^\d+ \d+px/.exec(font)[0];   // *(seventh version) with the weight: Unifont is drawn bold at 600-700 too
 function raw(t, f, dir) { x.clearRect(0, 0, W, H); x.font = f; x.fillStyle = '#000'; x.direction = dir; x.textAlign = 'center'; x.fillText(t, W / 2, BASE); return x.getImageData(0, 0, W, H).data; }
 function hash(d) { let h = 0; for (let i = 3; i < d.length; i += 4) h = (Math.imul(h, 31) + d[i]) | 0; return h; }
 // a font drawn on its own: does it have the letter? (with Unifont behind it, a letter the font lacks looks like Unifont's)
 const has = (u, dir) => hash(raw(u, font + ', Unifont', dir)) !== hash(raw(u, SIZE + ' Unifont', dir));
 const TOFU = new Set(['͸', '', '\u{1FFFD}', 'ࡰ͸'].map((t) => hash(raw(t, font, 'ltr'))));
 function draw(t, f, dir) {
   const d = raw(t, f, dir); let x0 = W, x1 = -1, ink = 0;
   for (let i = 0; i < W * H; i++) { const v = d[i * 4 + 3]; if (v) { ink += v; const c = i % W; if (c < x0) x0 = c; if (c > x1) x1 = c; } }
   if (!ink || x0 === 0 || x1 === W - 1) return null;
   const r = prep((y, c) => d[(y * W + c) * 4 + 3], x0, x1); r.h = hash(d);
   if (gap) {   // *(sixth version) the same drawing with every empty gap between two inked columns one column wide: a space, or a wider gap
                // after a letter that never joins the next one («عبد الله» / «عبدالله»), does not change what the eye reads as the name
     const cols = []; let blank = false;
     for (let c = x0; c <= x1; c++) { let v = 0; for (let y = 0; y < H; y++) v += d[(y * W + c) * 4 + 3];
       if (v) { cols.push(c); blank = false; } else if (!blank) { cols.push(-1); blank = true; } }
     r.g = prep((y, c) => (c < cols.length && cols[c] >= 0 ? d[(y * W + cols[c]) * 4 + 3] : 0), 0, cols.length - 1);
   }
   return r;
 }
 function prep(get, x0, x1) {   // aligned on the ink's centre, blurred, with 8x8 block sums for a quick lower bound
   const sh = Math.round(W / 2 - (x0 + x1 + 1) / 2), a = new Float32Array(W * H);
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const c2 = c - sh; tmp[y * W + c] = c2 >= 0 && c2 < W ? get(y, c2) : 0; }
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { let v = 0; for (let k = -R; k <= R; k++) { const X = c + k; if (X >= 0 && X < W) v += tmp[y * W + X] * K[k + R]; } t2[y * W + c] = v; }
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { let v = 0; for (let k = -R; k <= R; k++) { const Y = y + k; if (Y >= 0 && Y < H) v += t2[Y * W + c] * K[k + R]; } a[y * W + c] = v; }
   const NB = (W >> 3) * (H >> 3), b8 = new Float32Array(NB); let sum = 0;
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const v = a[y * W + c]; b8[(y >> 3) * (W >> 3) + (c >> 3)] += v; sum += v; }
   return { a, b8, sum };
 }
 function l1(p, q, lim) {   // the summed pixel difference, or lim as soon as it reaches lim
   if (Math.abs(p.sum - q.sum) >= lim) return lim;
   let s = 0; for (let i = 0; i < p.b8.length; i++) s += Math.abs(p.b8[i] - q.b8[i]); if (s >= lim) return lim;
   s = 0; for (let i = 0; i < W * H; i++) { s += Math.abs(p.a[i] - q.a[i]); if (s >= lim) return lim; } return s;
 }
 const oneLetter = (p, q) => { const a = [...p], b = [...q]; return a.length === b.length && a.filter((c, i) => c !== b[i]).length === 1; };
 const REF = [['ح', 'خ'], ['ر', 'ز'], ['د', 'ذ'], ['ع', 'غ'], ['ص', 'ض'], ['ط', 'ظ'], ['ٮ', 'ب'], ['ں', 'ن']];
 const dot = REF.map(([p0, q0]) => l1(draw(p0, arf, 'rtl'), draw(q0, arf, 'rtl'), 1e12)).sort((p, q) => p - q)[REF.length >> 1];
 const lim = thr * dot, near = []; let pairs = 0, drawn = 0, tofu = 0, lacks = 0;
 const runs = part === 'names' ? dirs.map((d) => ['name', d]) : ['isol', 'init', 'medi', 'fina'].map((p) => [p, null]);
 for (const [pos, nd] of runs) { const [ndir, pre, post] = nd || [null, '', ''];
   const isol = pos === 'isol' || pos === 'name';
   const us = isol ? U : U.filter(ar), ts = isol ? T : T.filter(ar), bm = new Map();
   for (const u of new Set(us.concat(ts))) {
     const dir = ndir || (ar(u) ? 'rtl' : 'ltr');
     if (check && !has(u, dir)) { if (isol) lacks++; continue; }
     const r = draw(part === 'names' ? pre + u + post : shape(u, pos), font, dir); if (!r) continue;
     if (TOFU.has(r.h)) { if (isol) tofu++; continue; }
     bm.set(u, r);
   }
   if (isol) drawn = Math.max(drawn, bm.size);
   const tl = ts.map((t) => [t, bm.get(t)]).filter((e) => e[1]).sort((p, q) => p[1].sum - q[1].sum), sums = tl.map((e) => e[1].sum);
   for (const u of us) { const p = bm.get(u); if (!p) continue; const ku = sk.get(u), lu = single && (part === 'names' || isLetter(u));
     let lo = 0, hi = sums.length; while (lo < hi) { const m = (lo + hi) >> 1; if (sums[m] <= p.sum - lim) lo = m + 1; else hi = m; }
     for (let j = lo; j < tl.length && tl[j][1].sum < p.sum + lim; j++) { const [t, q] = tl[j];
       if (t === u || (lu && t < u) || sk.get(t) === ku) continue;
       if (part === 'sequences' && oneLetter(u, t)) continue;   // one letter apart: the letters part compares them in every joining position
       pairs++;
       const m = gap ? Math.min(l1(p, q, lim), l1(p.g, q.g, lim)) : l1(p, q, lim); if (m < lim) near.push([font, pos + (ndir ? ':' + ndir + (pre || post ? ':' + pre + '…' + post : '') : ''), u, t, +(m / dot).toFixed(3),
         [...u].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), [...t].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), ku, sk.get(t)]); } }
 }
 return { font, dot: +dot.toFixed(1), drawn, tofu, lacks, pairs, near };
}"""

# *(seventh version) a mark drawn BESIDE its letter, not above or below it: Slovak and Czech ď ľ ť Ľ draw the caron as an apostrophe
# after the letter, Greek capitals carry the tonos and the breathings at their upper left (Ά, Ἀ) — the eye reads letter + ’ (or ’ +
# letter): «Paľo Kováč» drew as «Pal’o Kováč» in the bold thread list (v-spoof6-r1) while the blurred difference above put them ~4 dots
# apart (an apostrophe is not the caron's shape, and sits a gap further). So the GEOMETRY is measured: every allowed letter that NFD
# splits (a letter + marks) is drawn with its base letter at 48 px in each font on its own (Poppins and the system fonts, every
# weight; a font that lacks either is skipped), the base is aligned on the letter (the shift that covers most of its ink), and the ink
# the letter adds (outside the base's ink, grown by 2 px) is measured: when at least BESIDE_MIN of it lies within the rows the base
# letter itself covers — beside it, not above or below it — the letter must have the skeleton of its base letter with an apostrophe
# on that side (the skeleton drops the apostrophe: «Pal’o» = «Palo» = «Paľo»)
BESIDE_MIN = 0.5
BESIDE = r"""([font, check, minf]) => {
 const { U, sk } = window.__S;
 const W = 160, H = 96, BASE = 70;
 const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const x = cv.getContext('2d', { willReadFrequently: true });
 function rawd(t, f) { x.clearRect(0, 0, W, H); x.font = f; x.fillStyle = '#000'; x.direction = 'ltr'; x.textAlign = 'left'; x.fillText(t, 50, BASE); return x.getImageData(0, 0, W, H).data; }
 function alpha(t, f) { const d = rawd(t, f), a = new Uint8Array(W * H); for (let i = 0; i < W * H; i++) a[i] = d[i * 4 + 3]; return a; }
 const hash = (a) => { let h = 0; for (let i = 0; i < a.length; i++) h = (Math.imul(h, 31) + a[i]) | 0; return h; };
 const PRE = /^\d+ \d+px/.exec(font)[0];   // weight and size: Unifont is drawn at the same weight (synthetic bold at 600-700)
 const has = (u) => hash(alpha(u, font + ', Unifont')) !== hash(alpha(u, PRE + ' Unifont'));
 const near = []; let drawn = 0, lacks = 0, pairs = 0;
 for (const u of U) {
   const b = [...u.normalize('NFD')][0];
   if (check && (!has(u) || !has(b))) { lacks++; continue; }
   const A = alpha(u, font), B0 = alpha(b, font); drawn++;
   let best = -1, bs = 0;
   for (let s = -40; s <= 40; s++) { let v = 0; for (let y = 0; y < H; y++) for (let c = Math.max(0, s); c < Math.min(W, W + s); c++) { const q = B0[y * W + c - s]; if (q) v += Math.min(A[y * W + c], q); } if (v > best) { best = v; bs = s; } }
   const B = new Uint8Array(W * H); let y0 = H, y1 = -1, c0 = W, c1 = -1, bsum = 0;
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const c2 = c - bs; const v = c2 >= 0 && c2 < W ? B0[y * W + c2] : 0; B[y * W + c] = v; if (v > 64) { if (y < y0) y0 = y; if (y > y1) y1 = y; if (c < c0) c0 = c; if (c > c1) c1 = c; } bsum += v; }
   if (y1 < 0) continue;
   const near2 = (y, c) => { for (let dy = -2; dy <= 2; dy++) for (let dc = -2; dc <= 2; dc++) { const Y = y + dy, C = c + dc; if (Y >= 0 && Y < H && C >= 0 && C < W && B[Y * W + C] > 32) return true; } return false; };
   let e = 0, inr = 0, cx = 0;
   for (let y = 0; y < H; y++) for (let c = 0; c < W; c++) { const v = A[y * W + c]; if (v > 64 && !near2(y, c)) { e += v; cx += v * c; if (y >= y0 && y <= y1) inr += v; } }
   if (e < bsum * 0.01) continue;   // the mark draws as nothing here (the letters part compares such letters)
   const f = inr / e; if (f < minf) continue;
   pairs++;
   const left = cx / e < (c0 + c1) / 2, t = left ? '’' + b : b + '’';
   const ku = sk.get(u), kt = window.__F.nmSkel(t);
   if (ku !== kt) near.push([font, 'beside:' + (left ? 'left' : 'right'), u, t, +f.toFixed(3), [...u].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '),
     [...t].map((c) => c.codePointAt(0).toString(16).toUpperCase()).join(' '), ku, kt, window.__F.nmSkel(b)]);
 }
 return { font, dot: 0, drawn, tofu: 0, lacks, pairs, near };
}"""

def contexts(part):
    """(font string, Arabic stack for the unit, directions for names, check that the font has the letter)"""
    if part == 'beside':   # *(seventh version) the geometry: each font on its own, every weight, 48 px
        return [('%d 48px %s' % (w, f), None, None, True) for w in WEIGHTS for f in ['Poppins'] + SINGLE]
    ws = [400, 700] if (QUICK and part != 'letters') else WEIGHTS
    ss = [15] if (QUICK and part != 'letters') else SIZES
    out = []
    for w in ws:
        for s in ss:
            for name, st, d in STACKS:
                out.append(('%d %dpx %s' % (w, s, st), '%d %dpx %s' % (w, s, st), [[x, '', ''] for x in ([d] if d else ['ltr', 'rtl'])], False))
            if part == 'names' and w == ws[0] and s == ss[len(ss) // 2]:   # inside a sentence (a notification, a toast): words before / after
                st = STACKS[1][1]; out.append(('%d %dpx %s' % (w, s, st), '%d %dpx %s' % (w, s, st), [[x, a_, b_] for x in ('ltr', 'rtl') for a_, b_ in WRAPS], False))
            if part == 'letters' and not QUICK:   # *(sixth version) the system fonts at every weight too (they were drawn at 400 and 700)
                for f in SINGLE: out.append(('%d %dpx %s' % (w, s, f), '%d %dpx %s' % (w, s, f), ['ltr'], True))
            if part == 'sequences' and not QUICK and s == ss[len(ss) // 2]:   # *(sixth version) two-letter sequences in the system fonts too
                for f in SINGLE: out.append(('%d %dpx %s' % (w, s, f), '%d %dpx %s' % (w, s, f), ['ltr'], True))
    return out

t0 = time.time(); parts = ['letters', 'sequences', 'names', 'beside'] if PART == 'all' else [PART]; near = []; report = {}
with sync_playwright() as p:
    br = p.chromium.launch(args=['--no-sandbox']); pg = br.new_page(); pg.set_content('<style>' + FACES + '</style><p style="font-family:Poppins">x</p>')
    pg.evaluate("Promise.all(['400','500','600','700'].map((w) => document.fonts.load(w + ' 15px Poppins')))")
    assert pg.evaluate("document.fonts.check('700 15px Poppins')"), 'Poppins did not load'
    for part in parts:
        info = pg.evaluate(SETUP, [gen, part, NAMES if part == 'names' else []])
        print('rule', REV or 'working tree', '— part', part, info, 'threshold', THR, flush=True)
        runs = []
        for f, arf, dirs, check in contexts(part):
            r = pg.evaluate(BESIDE, [f, check, BESIDE_MIN]) if part == 'beside' else pg.evaluate(SCAN, [f, arf, dirs, part, THR, check, part != 'letters']); r['part'] = part; runs.append(r)
            print('  %-5s %-44s drawn %5d (no glyph %d%s)  dot %6.1f  pairs %9d  near %d  [%.0fs]' % (part[:5], f[:44], r['drawn'], r['tofu'],
                  (', font lacks %d' % r['lacks']) if check else '', r['dot'], r['pairs'], len(r['near']), time.time() - t0), flush=True)
            for n in r['near']: near.append(n + [part])
        report[part] = {'info': info, 'runs': [{k: v for k, v in r.items() if k != 'near'} for r in runs]}
    br.close()
near.sort(key=lambda n: n[4])
if OUT: json.dump({'rule': REV or 'working tree', 'threshold': THR, 'parts': report, 'near': near}, open(OUT, 'w'), ensure_ascii=False, indent=1)
distinct = {}
for n in near: distinct.setdefault(tuple(sorted((n[2], n[3]))), n)
print('pairs below %.2f of an Arabic dot (or a mark drawn beside its letter) with different skeletons: %d (%d distinct)  [%.0fs]' % (THR, len(near), len(distinct), time.time() - t0))
for n in sorted(distinct.values(), key=lambda n: n[4])[:80]: print('NEAR ', n)
if '--write' in sys.argv:   # add the pairs found (letters) to tools/names/pixel-twins.txt (the generator gives each group one skeleton)
    pairs = set(); ctx = set()   # ctx: (sequence, sequence) of code points in skeleton space
    if os.path.exists(TWINS):
        for l in open(TWINS, encoding='utf8'):
            m = re.match(r'^([0-9A-F]+(?: [0-9A-F]+)*) ; ([0-9A-F]+(?: [0-9A-F]+)*)\s', l)
            if not m: continue
            x, y = tuple(int(h, 16) for h in m[1].split()), tuple(int(h, 16) for h in m[2].split())
            if len(x) == 1 and len(y) == 1: pairs.add((x[0], y[0]))
            else: ctx.add((x, y))
    isM = lambda c: unicodedata.category(c).startswith('M')
    def dropped(L, S):   # S is L with some marks left out: [(kept char before, the marks left out)], else None
        out, i, j = [], 0, 0
        while i < len(L):
            if j < len(S) and L[i] == S[j]: i += 1; j += 1; continue
            if not isM(L[i]) or i == 0: return None
            k = i
            while i < len(L) and isM(L[i]) and not (j < len(S) and L[i] == S[j]): i += 1
            out.append((L[k - 1], L[k:i]))
        return out if j == len(S) and out else None
    unwritten, later, before = [], [], len(pairs)
    for (a_, b_), n in distinct.items():
        if n[-1] == 'beside':   # *(seventh version) a mark drawn beside the letter: the letter's skeleton is its base letter's
            if n[7] != n[9]: ctx.add((tuple(map(ord, n[7])), tuple(map(ord, n[9]))))
            continue
        if n[-1] != 'letters': unwritten.append(n); continue
        ka, kb = n[7], n[8]
        diff = [(i, x, y) for i, (x, y) in enumerate(zip(ka, kb)) if x != y] if len(ka) == len(kb) else None
        ccc = lambda c: unicodedata.combining(c) if unicodedata.combining(c) < 200 or unicodedata.combining(c) >= 230 else 220   # attached below ~ below
        arabic = any('ARABIC' in unicodedata.name(c, '') for c in a_ + b_)   # Arabic: the two letters (a hamza is not three dots everywhere)
        split = lambda x: unicodedata.normalize('NFD', x) != x
        drop = dropped(ka, kb) if len(ka) > len(kb) else dropped(kb, ka) if len(kb) > len(ka) else None
        if len(a_) == 1 and len(b_) == 1 and arabic and not (split(a_) and split(b_)): pairs.add(tuple(sorted((ord(a_), ord(b_)))))   # *(sixth version) آ / أ: their marks
        elif diff and all(isM(x) and isM(y) for _, x, y in diff):
            for i, x, y in diff:
                if ccc(x) == ccc(y): pairs.add(tuple(sorted((ord(x), ord(y)))))       # the same place: the marks
                else: pa, pb = (ord(ka[i - 1]), ord(x)), (ord(kb[i - 1]), ord(y)); ctx.add((min(pa, pb), max(pa, pb)))   # one letter draws them at one place
        elif drop:   # *(sixth version) one is the other with a mark that draws within a dot of nothing (bold Ḣ / H): that letter loses it
            for k, ms in drop: ctx.add((tuple(ord(c) for c in k + ms), (ord(k),)))
        elif len(a_) == 1 and len(b_) == 1 and not split(a_) and not split(b_): pairs.add(tuple(sorted((ord(a_), ord(b_)))))   # two letters
        elif len(a_) == 1 and len(b_) == 1: later.append(n)   # *(sixth version) an accented letter and another letter: their skeletons
        else: unwritten.append(n)
    # *(sixth version) the skeletons of an accented letter (NFD splits it: it has no key of its own) and another letter, as a sequence
    # pair — only once a scan writes no new pair of letters: a new pair of letters (i / l) changes those skeletons, and often makes the
    # pair the same name (Ì / İ once i and l share a key)
    for n in later:
        if len(pairs) > before: print('LATER (written once no pair of letters is new):', n)
        else: ctx.add((tuple(map(ord, n[7])), tuple(map(ord, n[8]))))
    for n in unwritten: print('NOT WRITTEN (not two letters, nor two letters that differ only in marks):', n)
    with open(TWINS, 'w', encoding='utf8') as f:
        f.write('# Letters (and marks) the name rule allows that draw alike while their skeletons differ: tools/names/render_scan.py --write\n'
                '# (blurred drawings within %.2f of an Arabic dot of each other), Chromium canvas, the app\'s font stacks (EN, AR, system-ui) and\n'
                '# the system fonts on their own at weights 400-700, 14-16 px. Two letters that differ only in a mark at the same place give the\n'
                '# pair of marks (é / è: U+0300 / U+0301); a letter that draws two marks at one place gives the pair of letter + mark (ģ / ġ);\n'
                '# a letter whose mark draws within a dot of nothing gives letter + mark ; letter (bold Ḣ / H — sixth version), and so does a\n'
                '# letter whose mark is drawn BESIDE it, within the rows the letter covers (part \'beside\', 48 px: ľ ď ť, Ά — seventh version;\n'
                '# the skeleton drops the apostrophe it reads as). Sequences are in\n'
                '# skeleton space. tools/names/name_rule.mjs gives each group one skeleton. Generated, never edited by hand.\n' % THR)
        nm = lambda c: unicodedata.name(chr(c), '?')
        for a_, b_ in sorted(pairs): f.write('%04X ; %04X # %s / %s — %s / %s\n' % (a_, b_, chr(a_), chr(b_), nm(a_), nm(b_)))
        sq = lambda t: ' '.join('%04X' % c for c in t)
        for x, y in sorted(ctx, key=lambda p: (len(p[0]), len(p[1]), p)):
            f.write('%s ; %s # %s / %s — %s / %s\n' % (sq(x), sq(y), ''.join(map(chr, x)), ''.join(map(chr, y)), ' + '.join(map(nm, x)), ' + '.join(map(nm, y))))
    print('written', TWINS, len(pairs), 'pairs', len(ctx), 'sequence pairs')
if MUST:
    u_, t_ = MUST.split('/')
    hit = [n for n in near if {n[2], n[3]} == {u_, t_}]
    print(('FOUND ' if hit else 'NOT FOUND ') + MUST + (' — e.g. ' + str(hit[0]) if hit else ''))
    sys.exit(0 if hit else 1)
sys.exit(1 if near else 0)
