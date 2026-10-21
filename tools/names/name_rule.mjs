// The one rule for a person's display name (S-03): what a name may contain (an ALLOWLIST) and when two names are "the same name"
// (a confusable SKELETON, Unicode TR39). The database (supabase/migrations/0039_names_rule_5.sql — 0038, 0039_names_rule_2.sql,
// 0039_names_rule_3.sql and 0039_names_rule_4.sql hold the first four versions and are never edited) and the live app (web/src/live/adapter.js) both carry
// the code this script prints between their "generated" markers — never edit it by hand:
//   node tools/names/name_rule.mjs --write    rewrite both generated regions (only before 0039_names_rule_5 is applied anywhere:
//                                             an applied migration is never edited — a new rule goes into a new migration)
//   node tools/names/name_rule.mjs --check    exit 1 when a region differs from what this script generates
//   node tools/names/name_rule.mjs --expect   --check, then what the ADAPTER's generated code makes of every code point of planes 0-1
//                                             in four places (TSV: code point, place, normalised name, problem, skeleton, NFKC, NFD,
//                                             message); supabase/tests/name_rule.sql loads it and compares the database's functions with it
// Data: Node's own Unicode tables (General_Category, Script, Script_Extensions, Default_Ignorable_Code_Point, Dash, NFKC/NFD),
// the UTS #39 security data vendored in tools/names/unicode-16.0.0 (IdentifierStatus.txt, confusables.txt — see its README), and
// tools/names/pixel-twins.txt (letters that draw alike while TR39 keys them apart — written by tools/names/render_scan.py --write,
// which must exit 0 after any change to the rule). Node 22 carries Unicode 16.0, the same version as the vendored data; this
// script refuses to run on another one.
//
// THE RULE (second version, 0039_names_rule_2 — what changed from 0038 is marked *; the THIRD version, 0039_names_rule_3, is marked
// *(third version) where it is defined below: a mark only when NFKC joins it to its letter or the skeleton drops it — reason
// 'accent' —, letters from each alphabet's everyday blocks, pixel twins, every dash a hyphen, one alphabet per RUN of letters,
// and no 'latin' reason; the FOURTH version, 0039_names_rule_4, is marked *(fourth version): names are stored WITHOUT Arabic
// diacritics — every Arabic vowel mark, tanween, shadda, sukun, superscript alef, Quranic annotation mark (and the small waw / yeh
// of Quranic spelling) is removed, so no mark can stand in for a letter's dot («حْالد» drew as «خالد», atk-unicode-r3) —, a slash
// after a space is joined to the word before it («د / محمد» → «د/ محمد»), ʿ is written ’ like ʾ, a spaced hyphen is refused with a
// suggestion in parentheses (reason 'dash'), a letter of the four alphabets that the rule does not take yet has its own reason
// ('unsupported'), and every name or character a message quotes is isolated (U+2068 … U+2069) so an Arabic sentence keeps its order;
// the FIFTH version, 0039_names_rule_5, is marked *(fifth version): brackets that the bidi algorithm can reorder are refused
// ('bracket': "(MBA) Ahmed Ali" drew exactly as "Ahmed Ali (MBA)" in the Arabic interface, "Ali (علي) محمد" as "Ali محمد (علي)" in
// the English one, v-spoof-r1 — see BRACKETS below) —, the pixel twins of a scan of the app's font stacks at every weight (bold ث / ئ), the Maghrebi ڭ ڢ, a zero-width
// non-joiner between Arabic letters written as a space, a 'dash' suggestion for several dashes, and U+FFFD for a letter of another
// alphabet in the skeleton)
//  normalise (person_name_norm / nmNorm): remove every invisible character (Default_Ignorable_Code_Point, format Cf, control Cc —
//    tab and line breaks excepted —, U+2800, U+1D159) and the Arabic tatweel U+0640 (it only stretches a joining line: "هـالة" reads
//    "هالة"); *write every look-alike of the punctuation a name may hold as that punctuation (PUNCT_LIKE: a punctuation mark, a
//    modifier symbol, a Common-script modifier letter or a dash whose TR39 confusable prototype is the prototype of . - ' ( ) , / —
//    so the non-breaking hyphen and the en dash become "-", ‘ ʼ ´ ` and ' become ’, ﴾ ﴿ become ( ) — the apostrophe is always
//    stored as ’, the way the app shows it); NFKC; both steps again (NFKC can produce a tatweel, U+FE71, or a look-alike); every
//    kind of space or line break is one space, no space at either end.
//  allowed (person_name_problem / nmProblem: '' when allowed, else the first reason, in this order):
//    empty   nothing left
//    long    more than 120 characters
//    digit   a number of any script (\p{N}: 0-9, ٠-٩, ۰-۹, ①, Ⅻ…)
//   *letter  a letter (\p{L}) that is not a letter of the Latin, Arabic, Greek or Cyrillic script whose TR39 Identifier_Status is
//            Allowed (张, א, Ա, ǃ, ꞏ, ʼ standing alone…) — the message says which alphabets are accepted
//            *Arabic letters come from the Arabic and Arabic Supplement blocks only (not Arabic Extended-A/B: African noon and qaf
//            draw as ن and ف before another letter while TR39 gives them the skeleton of their dotless final forms)
//    char    anything else that is not: an allowed letter, a combining MARK (\p{M}) with Identifier_Status Allowed, the space, or one
//            of . - ’ ( ) , *and / (titles: "د/", "Ph/") *and the Arabic comma ، (an Arabic keyboard's comma) — so no symbol, no
//            other punctuation (the picker's separator "·" and every look-alike of it), no private use, no unassigned code point,
//            no U+FFFC / U+FFFD
//    word    a word (between spaces) with no letter: " - ", "(", "." — *the message names it ("join it to the word next to it")
//    mark    a mark that does not sit on a letter, more than 3 marks on one letter, *or the same mark twice on one letter (TR39
//            §5.4: a repeated mark can draw over itself, so "é" and "é́" would look the same and have different skeletons)
//    script  a word that mixes scripts: every word is ONE script (its marks are of that script or generic "Inherited" marks) —
//            TR39 "single script" per word. *Words of different scripts may stand side by side ("Dr. Мария Иванова",
//            "Мария Иванова (Maria Ivanova)"): a whole word in another alphabet that copies a Latin word ("Рара" for "Papa") has the
//            same SKELETON, so it is the same name below — that, not the script, is what keeps it from passing as someone else
//  skeleton (person_name_key / nmSkel): NFD of the normalised name, every character replaced by its key, NFD again *(fourth version)
//    then one of a run of the same mark kept and the first mark above after i or j dropped (it takes the place of the dot). A character's
//    key is the fixed point of: TR39 confusable prototype (confusables.txt) of each character, then lower case, then NFD — and the
//    Arabic short vowels and shadda (U+064B-U+0652, U+0670) are dropped (names are written with or without them), and so is U+FFFC
//    (it draws nothing; names stored before 0038 may hold it). So "Rana" and "Rаna", "Ilya" and "llya", "O'Brien" and "O’Brien",
//    "هالة" and "هال\u064Eة", "فاطمة" and "ڧاطمة" (a qaf with one dot draws as a feh before a letter) have the same skeleton: the
//    ✎ New message picker, the resolver and the chat header treat them as the same name and tell the members apart.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const DATA = path.join(ROOT, 'tools/names/unicode-16.0.0');
const MIGRATION = path.join(ROOT, 'supabase/migrations/0039_names_rule_5.sql');
const ADAPTER = path.join(ROOT, 'web/src/live/adapter.js');
if (process.versions.unicode !== '16.0') { console.error(`Node carries Unicode ${process.versions.unicode}; the vendored data is 16.0 — use Node 22`); process.exit(2); }

const MAXCP = 0x10FFFF, PLANES01 = 0x1FFFF, MAXLEN = 120;
const isSur = (c) => c >= 0xD800 && c <= 0xDFFF;
const ch = (c) => String.fromCodePoint(c);
const has = (re) => (c) => re.test(ch(c));
function ranges(test, max = MAXCP) { const r = []; let s = -1, p = -2; for (let c = 0; c <= max; c++) { if (isSur(c) || !test(c)) continue; if (c !== p + 1) { if (s >= 0) r.push([s, p]); s = c; } p = c; } if (s >= 0) r.push([s, p]); return r; }

// ── the UTS #39 data ──
function readData(file) { const t = fs.readFileSync(path.join(DATA, file), 'utf8'); const v = /# Version: (\S+)/.exec(t); if (!v || v[1] !== '16.0.0') throw new Error(file + ' is not version 16.0.0'); return t; }
const ALLOWED = new Set();
for (const l of readData('IdentifierStatus.txt').split('\n')) {
  const m = /^([0-9A-F]+)(?:\.\.([0-9A-F]+))?\s*;\s*Allowed\b/.exec(l); if (!m) continue;
  for (let c = parseInt(m[1], 16), b = m[2] ? parseInt(m[2], 16) : c; c <= b; c++) ALLOWED.add(c);
}
const CONF = new Map();
for (const l of readData('confusables.txt').split('\n')) {
  const m = /^([0-9A-F]+)\s*;\s*([0-9A-F ]+?)\s*;\s*MA\b/.exec(l); if (m) CONF.set(parseInt(m[1], 16), String.fromCodePoint(...m[2].split(' ').map((x) => parseInt(x, 16))));
}

// ── the classes ──
const SPACE = [[0x09, 0x0D], [0x20, 0x20], [0x85, 0x85], [0xA0, 0xA0], [0x1680, 0x1680], [0x2000, 0x200A], [0x2028, 0x2029], [0x202F, 0x202F], [0x205F, 0x205F], [0x3000, 0x3000]];
const inR = (rs) => (c) => rs.some(([a, b]) => c >= a && c <= b);
const isSpace = inR(SPACE);
const DI = has(/^\p{Default_Ignorable_Code_Point}$/u), CF = has(/^\p{Cf}$/u), CC = has(/^\p{Cc}$/u);
const TATWEEL = 0x0640, BLANK = [0x2800, 0x1D159];
const INVIS = ranges((c) => c !== 0 && !isSpace(c) && (DI(c) || CF(c) || CC(c) || BLANK.includes(c) || c === TATWEEL));
const DIGIT = ranges(has(/^\p{N}$/u));
const PUNCT = [0x28, 0x29, 0x2C, 0x2D, 0x2E, 0x2F, 0x060C, 0x2019];   // ( ) , - . / ، ’   (the apostrophe ' is stored as ’)
const SCRIPTS = [['Latn', 'Latin'], ['Arab', 'Arabic'], ['Grek', 'Greek'], ['Cyrl', 'Cyrillic']];
// Arabic letters: the Arabic block and Arabic Supplement (Blocks.txt: 0600..06FF, 0750..077F — Arabic, Persian, Urdu, Kurdish,
// Pashto, Sindhi…; presentation forms reach them through NFKC). Arabic Extended-A/B (0870..08FF) hold letters for African and other
// languages whose dots show only before another letter (African noon ࢽ draws as ن, African qaf ࢼ as ف, but TR39 maps them to their
// dotless final forms), so they are not accepted (atk-bypass-r1)
// *(0039, third version) every alphabet keeps to the blocks of its everyday letters (Blocks.txt), the ones every font draws:
//   Latin: Basic Latin, Latin-1 Supplement, Latin Extended-A and -B, IPA Extensions (ə), Latin Extended Additional (Vietnamese ệ, ḥ ṣ ṭ
//   of transliteration) — not Latin Extended-C…G, whose letters draw like letters of other alphabets (Ɥ U+A78D is Cyrillic Ч to the
//   pixel) or as an empty box in every installed font (U+1DF00…) (atk-unicode-r2); Greek: Greek and Coptic, Greek Extended;
//   Cyrillic: Cyrillic, Cyrillic Supplement (not Extended-A…D)
// *(fourth version) Arabic letters are the letters of Arabic, Persian, Urdu, Kurdish (Sorani) and Maghrebi Arabic only — the letters
// of other languages written in the Arabic script (Arabic Supplement, Pashto, Sindhi, Uyghur, Kashmiri, Saraiki…) differ from a
// common letter by a small mark that draws like a dot at 14-16 px (ݕ / ي, ڂ / خ, ې / ب, ݵ / ݺ: tools/names/render_scan.py), so they are
// 'unsupported' (not supported yet), like Hausa Ɗ
// *(fifth version) with the Maghrebi gaf ڭ and feh ڢ (v-real-r1: «ڭمال» was 'unsupported' while Maghrebi Arabic is named above)
const ARAB_OK = new Set([...'ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوىيٱٹپچڈڑژڕڢڤڧڨکڭگڵںھۀہۂۃۆیێےۓە'].map((x) => x.codePointAt(0)));
// *(fifth version) a zero-width non-joiner after an Arabic letter that joins on both sides, before another Arabic letter, keeps the
// letters apart (Persian «علی‌رضا», «محمدی‌نژاد»): it is written as a space, so the letters keep the shapes the person typed — removed,
// they joined («علیرضا», v-real-r1). After a letter that never joins the next one (ا د ذ ر ز و ة ء …) it changes nothing and is removed
const ARAB_NOJOIN = new Set([...'ءآأؤإاةدذرزوٱڈڑژڕۀۃۆەےۓ'].map((x) => x.codePointAt(0)));
const BLOCKS = { Latn: [[0x0000, 0x024F], [0x0250, 0x02AF], [0x1E00, 0x1EFF]], Arab: [[0x0600, 0x06FF], [0x0750, 0x077F]],
  Grek: [[0x0370, 0x03FF], [0x1F00, 0x1FFF]], Cyrl: [[0x0400, 0x052F]] };
const stable = (c) => ch(c).normalize('NFKC') === ch(c);
// *(0039, third version) a mark may stand apart from its letter only when the skeleton drops it (the Arabic short vowels, shadda,
// sukun, dagger alef): a mark can then never make two names that look alike different names. Accented Latin, Greek and Cyrillic
// letters are written as ONE character (é, ü, ñ, ệ, ά, й — NFKC joins a typed e + ◌́ into é); a mark NFKC cannot join to its letter
// (e + U+0335, i/ı/j + U+0307, Τ + U+0304, two marks in either order) can draw on a stroke the letter already has and look like
// nothing, so it is refused (atk-unicode-r2, atk-bypass-r2; TR39 §5.4)
const DROP = new Set([0x064B, 0x064C, 0x064D, 0x064E, 0x064F, 0x0650, 0x0651, 0x0652, 0x0670, 0xFFFC]);   // Arabic short vowels, shadda, sukun, dagger alef; U+FFFC draws nothing (a name stored before 0038 may hold it)
// *(fourth version) names are stored WITHOUT Arabic diacritics: after NFKC, every combining mark of the Arabic script is removed —
// Script=Arabic, or an Inherited mark of the Arabic block whose Script_Extensions has Arabic: the vowel marks, tanween, shadda, sukun,
// superscript alef, the Quranic annotation marks of the Arabic blocks (U+0610-061A, 0656-065F, 06D6-06ED, 0897-08FF, 10EFC-10EFF) —
// except the madda and hamza marks U+0653-0655, which NFKC joins to their letter (آ أ إ ؤ ئ ۀ ۂ ۓ) and which are refused where it
// cannot ('accent'); so are the small waw and small yeh of Quranic spelling (U+06E5, U+06E6, letters drawn as marks). A mark drawn
// above a letter without a dot drew like that letter's dot — «حْالد» (ح + sukun) like «خالد», «رْياد» like «زياد» — while the skeleton
// dropped it (atk-unicode-r3); a name that cannot hold the mark cannot be drawn that way. Names are written with or without them,
// and the skeleton always dropped them: no member's skeleton moves.
const ARAB_STRIP = ranges((c) => { const s = ch(c); return c === 0x06E5 || c === 0x06E6 || (/^\p{M}$/u.test(s) && !(c >= 0x0653 && c <= 0x0655)
  && (/^\p{Script=Arabic}$/u.test(s) || (/^\p{Script_Extensions=Arabic}$/u.test(s) && c >= 0x0600 && c <= 0x06FF))); });
const isStrip = inR(ARAB_STRIP);
const LET = {}, MARK = {};
for (const [k, sc] of SCRIPTS) {
  const inSc = has(new RegExp(`^\\p{Script=${sc}}$`, 'u')), inScx = has(new RegExp(`^\\p{Script_Extensions=${sc}}$`, 'u'));
  const inherited = has(/^\p{Script_Extensions=Inherited}$/u);
  LET[k] = ranges((c) => ALLOWED.has(c) && /^\p{L}$/u.test(ch(c)) && inSc(c) && stable(c) && inR(BLOCKS[k])(c) && !isStrip(c) && (k !== 'Arab' || ARAB_OK.has(c)));
  MARK[k] = ranges((c) => ALLOWED.has(c) && /^\p{M}$/u.test(ch(c)) && (inScx(c) || inherited(c)) && stable(c) && DROP.has(c) && !isStrip(c));   // *(fourth version) none left
}
const union = (...rss) => { const s = new Set(); for (const rs of rss) for (const [a, b] of rs) for (let c = a; c <= b; c++) s.add(c); return ranges((c) => s.has(c)); };
const single = (l) => l.slice().sort((a, b) => a - b).map((c) => [c, c]);
const LET_ANY = union(...SCRIPTS.map(([k]) => LET[k])), MARK_ANY = union(...SCRIPTS.map(([k]) => MARK[k]));
const OK = union(LET_ANY, MARK_ANY, single(PUNCT), [[0x20, 0x20]]);
const isOK = inR(OK), isLetAny = inR(LET_ANY);
// *(fifth version) BRACKETS. A pair of brackets takes the direction of what comes before it (Unicode bidi rule N0), not of its
// neighbours like any other punctuation (N1), so two names can draw alike in the interface of the other direction while the words
// are in another order: "(MBA) Ahmed Ali" / "Ahmed Ali (MBA)" (Arabic interface), "Ali (علي) محمد" / "Ali محمد (علي)" (English).
// Without paired brackets every allowed name draws differently from every other (each punctuation mark's place follows from the
// letters around it, which the drawing shows). So a name holds ONE pair of brackets, '(' then ')', after a letter, around letters
// of one direction (Arabic, or Latin/Greek/Cyrillic), and the letters just before '(' and just after ')' (when there are some) run
// in the same direction: then the pair resolves as any other punctuation would and the name draws as written, in both interfaces
// (tools/names/render_scan.py --part names: thousands of variants of real names, alone and inside a sentence, both directions)
const LTR_LET = union(LET.Latn, LET.Grek, LET.Cyrl);
const ZW_BEFORE = ranges((c) => inR(LET.Arab)(c) && !ARAB_NOJOIN.has(c)), ZW_MARK = union(ARAB_STRIP, [[0x0653, 0x0655]]);
// *(fourth version) a letter of another alphabet ('letter') is told apart from a letter of the four alphabets the rule does not take
// (yet): Hausa Ɗ Ƙ Ɓ, Akan Ɔ Ɛ, letters outside the everyday blocks, restricted letters ('unsupported' — "not supported yet", not
// "not one of the alphabets", atk-legit-r3)
const IN_SCRIPT4 = SCRIPTS.map(([, sc]) => new RegExp(`^\\p{Script=${sc}}$`, 'u')), inScript4 = (c) => IN_SCRIPT4.some((re) => re.test(ch(c)));
const OTHER_LET = ranges((c) => /^\p{L}$/u.test(ch(c)) && !isLetAny(c) && !inScript4(c));   // a letter of another alphabet (or of none: ˑ)
const UNSUP_LET = ranges((c) => /^\p{L}$/u.test(ch(c)) && !isLetAny(c) && inScript4(c));    // a letter of the four alphabets not taken (yet)
const MARK_ALL = ranges(has(/^\p{M}$/u));                                                  // any mark (NFD can split an allowed letter)
const MARK_BAD = ranges((c) => /^\p{M}$/u.test(ch(c)) && !inR(MARK_ANY)(c));                 // a mark that may not stand apart from its letter

// ── look-alikes of the punctuation a name may hold: written as that punctuation (TR39 prototypes, so not hand-picked) ──
function proto(s) { for (let i = 0; i < 16; i++) { const t = [...s.normalize('NFD')].map((x) => CONF.get(x.codePointAt(0)) ?? x).join('').normalize('NFD'); if (t === s) return s; s = t; } return s; }
const LIKE_OF = [['.', '.'], ['-', '-'], ["'", '’'], ['(', '('], [')', ')'], [',', ','], ['/', '/']];   // prototype of → written as
const LIKE_KIND = (s) => /^[\p{Pd}\p{Ps}\p{Pe}\p{Pi}\p{Pf}\p{Po}\p{Sk}]$/u.test(s) || (/^\p{Lm}$/u.test(s) && /^\p{Script=Common}$/u.test(s)) || (/^\p{Sm}$/u.test(s) && /^\p{Dash}$/u.test(s));
// *(fourth version) ʿ U+02BF (the ayn of transliteration, "Saʿīd") is written ’ like ʾ U+02BE (TR39 gives it the prototype of the
// Armenian ՙ, not of the apostrophe; atk-legit-r3)
const LIKE_EXTRA = new Map([[0x02BF, '’']]);
const LIKE = [];   // [code point, written as]
for (let c = 1; c <= PLANES01; c++) {
  if (isSur(c) || isOK(c) || isSpace(c) || inR(INVIS)(c)) continue; const s = ch(c);
  if (!LIKE_KIND(s)) continue;
  // *(0039, third version) every dash (\p{Pd}: — ― ⸺ 〜 …) is a hyphen in a name: "Jean—Paul" is stored "Jean-Paul" (atk-legit-r2)
  const dash = /^\p{Pd}$/u.test(s) || /^\p{Pd}$/u.test(s.normalize('NFKC'));
  const p = proto(s), q = proto(s.normalize('NFKC')), hit = LIKE_EXTRA.has(c) ? ['', LIKE_EXTRA.get(c)] : dash ? ['-', '-'] : LIKE_OF.find(([t]) => proto(t) === p || proto(t) === q);
  if (hit) LIKE.push([c, hit[1]]);
}
const LIKE_MAP = new Map(LIKE.map(([c, t]) => [c, t]));

// ── the skeleton map: every code point of planes 0-1 that can stand in an NFD-normalised name and whose key is not itself ──
// *(third version) letters that DRAW alike while TR39 gives them different skeletons (tools/names/pixel-twins.txt, written by
// tools/names/render_scan.py --write from the fonts it lists: ӏ U+04CF is l to the pixel in three fonts but TR39 maps it to i;
// ڒ / ۯ; ݶ / ݻ): each group gets the skeleton of its most common letter (basic Latin, the Arabic alphabet, basic Greek and Cyrillic;
// else the lowest code point) — the letter alone is remapped, never its whole class
// *(fourth version) the pairs may be MARKS too (an accent that draws like another at the same place: é / è, Ŝ / Š, ἀ / ἁ, written by
// render_scan.py when two letters differ only in a mark): a group of marks gets the lowest one. A group of letters gets a letter that
// cannot be remapped itself (one NFD splits, ئ = ي + hamza: its skeleton comes from its parts), else the most common one, else the
// lowest code point
const COMMON = (c) => (c >= 0x41 && c <= 0x7A) || (c >= 0x0621 && c <= 0x064A) || (c >= 0x0391 && c <= 0x03C9) || (c >= 0x0410 && c <= 0x044F);
const SPLITS = (c) => ch(c).normalize('NFD') !== ch(c);
const PIXEL = new Map();
// *(fifth version) a pair of a letter + mark (ģ / ġ: g draws its cedilla above, where ġ has its dot): written in skeleton space
// ("0067 0323 ; 0067 0300" — the keys of the two letters), each group's other sequences become its lowest; applied to the skeleton last
const CTX = [];
{
  const up = new Map(), find = (x) => { while (up.has(x) && up.get(x) !== x) x = up.get(x); return x; };
  for (const l of fs.readFileSync(path.join(ROOT, 'tools/names/pixel-twins.txt'), 'utf8').split('\n')) {
    const m = /^([0-9A-F]+) ([0-9A-F]+) ; ([0-9A-F]+) ([0-9A-F]+)\s/.exec(l); if (!m) continue;
    const a = find(ch(parseInt(m[1], 16)) + ch(parseInt(m[2], 16))), b = find(ch(parseInt(m[3], 16)) + ch(parseInt(m[4], 16)));
    for (const x of [a, b]) if (!up.has(x)) up.set(x, x); if (a !== b) up.set(a < b ? b : a, a < b ? a : b);
  }
  for (const x of up.keys()) if (find(x) !== x) CTX.push([x, find(x)]);
  CTX.sort((p, q) => (p[0] < q[0] ? -1 : 1));
}
{
  const up = new Map(), find = (x) => { while (up.has(x) && up.get(x) !== x) x = up.get(x); return x; };
  for (const l of fs.readFileSync(path.join(ROOT, 'tools/names/pixel-twins.txt'), 'utf8').split('\n')) {
    const m = /^([0-9A-F]+) ; ([0-9A-F]+)/.exec(l); if (!m) continue; const a = find(parseInt(m[1], 16)), b = find(parseInt(m[2], 16));
    for (const x of [a, b]) if (!up.has(x)) up.set(x, x); if (a !== b) up.set(Math.max(a, b), Math.min(a, b));
  }
  const groups = new Map(); for (const x of up.keys()) { const r = find(x); if (!groups.has(r)) groups.set(r, []); groups.get(r).push(x); }
  for (const g of groups.values()) {
    g.sort((a, b) => (SPLITS(b) - SPLITS(a)) || (COMMON(b) - COMMON(a)) || a - b);
    if (g.filter(SPLITS).length > 1) throw new Error('tools/names/pixel-twins.txt: a group holds two letters that NFD splits: ' + g.filter(SPLITS).map((x) => 'U+' + x.toString(16)).join(' '));
    for (const x of g.slice(1)) PIXEL.set(x, g[0]);
  }
}
const base0 = (c) => (DROP.has(c) ? '' : CONF.has(c) ? CONF.get(c) : ch(c));
const base = (c) => (PIXEL.has(c) ? keyOf0(PIXEL.get(c)) : base0(c));
function keyOf0(c) { let s = ch(c); for (let i = 0; i < 16; i++) { const t = [...[...s.normalize('NFD')].map((x) => base0(x.codePointAt(0))).join('')].map((x) => x.toLowerCase()).join('').normalize('NFD'); if (t === s) return s; s = t; } throw new Error('no fixed point for U+' + c.toString(16)); }
const step = (s) => [...[...s.normalize('NFD')].map((x) => base(x.codePointAt(0))).join('')].map((x) => x.toLowerCase()).join('').normalize('NFD');
function keyOf(c) { let s = ch(c); for (let i = 0; i < 16; i++) { const t = step(s); if (t === s) return s; s = t; } throw new Error('no fixed point for U+' + c.toString(16)); }
const SKEL = [];
for (let c = 1; c <= PLANES01; c++) { if (isSur(c)) continue; const s = ch(c); if (s.normalize('NFD') !== s || !stable(c)) continue; const k = keyOf(c); if (k !== s) SKEL.push([c, k]); }
// *(fourth version) marks that draw alike map to one mark (pixel-twins.txt), and two of the same mark stacked on a letter draw like one
// at 14-16 px (Ẵ — breve and tilde — like Ǎ, ǘ like ü): the skeleton keeps one of a run of the same mark.
// *(fourth version) an accent above i or j takes the place of its dot (í is drawn ı + ◌́, and looks like i at 14-16 px): the skeleton
// drops the first mark above that follows i or j (after the marks below it) — "Alí" / "Ali", "ĵ" / "j" (render_scan.py). The
// canonical combining class is read from NFD's own reordering: a mark ABOVE sorts after a dot below (220) and before U+0315 (232)
const reorders = (a, b) => ('a' + a + b).normalize('NFD') !== 'a' + a + b;
const MARK_ABOVE = ranges((c) => /^\p{M}$/u.test(ch(c)) && reorders(ch(c), '\u0323') && reorders('\u0315', ch(c)), PLANES01);
const MARK_BEFORE_ABOVE = ranges((c) => /^\p{M}$/u.test(ch(c)) && reorders('\u0301', ch(c)), PLANES01);   // a mark NFD puts before one above
const hx = (c) => c.toString(16).toUpperCase();
const SKEL_D = SKEL.map(([c, k]) => hx(c) + '=' + [...k].map((x) => hx(x.codePointAt(0))).join('.')).join(',');

// ── printing the classes ──
const SQL_SPECIAL = { 0x2D: '\\-', 0x5D: '\\]', 0x5E: '\\^', 0x5C: '\\\\' };
function sqlClass(rs) { return rs.map(([a, b]) => { const f = (c) => SQL_SPECIAL[c] || (c > 0xFFFF ? '!+' + hx(c).padStart(6, '0') : '!' + hx(c).padStart(4, '0')); return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
function jsClass(rs) { return rs.map(([a, b]) => { const f = (c) => '\\u{' + hx(c) + '}'; return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
const sqlChars = (l) => l.map((c) => (c > 0xFFFF ? '!+' + hx(c).padStart(6, '0') : '!' + hx(c).padStart(4, '0'))).join('');
const U = (s) => `U&'${s}' uescape '!'`;
const sqlWord = (L, M) => `'^[' || ${U(sqlClass(single(PUNCT)))} || ']*(?:[' || ${U(sqlClass(L))} || ']${M.length ? `[' || ${U(sqlClass(M))} || ']{0,3}` : ''}[' || ${U(sqlClass(single(PUNCT)))} || ']*)+$'`;
const jsWord = (L, M) => `/^[${jsClass(single(PUNCT))}]*(?:[${jsClass(L)}]${M.length ? `[${jsClass(M)}]{0,3}` : ''}[${jsClass(single(PUNCT))}]*)+$/u`;
const RUN_SEP = single([0x20, ...PUNCT]);   // *(third version) a run of letters (between spaces and punctuation) is ONE alphabet: "Dr.أحمد" is fine
const OK_OR_ACCENT = union(OK, MARK_BAD);   // 'char' is anything else; a mark that may not stand apart from its letter is 'accent'
const ACCENT_AT = union([[0x20, 0x20]], MARK_ALL);   // the letter an accent sits on: not a space, not a mark
const sqlScriptOf = (w, ind) => `case\n${SCRIPTS.map(([k]) => `${ind}  when ${w} ~ (${sqlWord(LET[k], MARK[k])}) then '${k}'`).join('\n')}\n${ind}end`;
const SQL_REPEAT = `'([' || ${U(sqlClass(MARK_ALL))} || '])[' || ${U(sqlClass(MARK_ALL))} || ']*\\1'`;
const HEAD = 'generated by tools/names/name_rule.mjs from Unicode 16.0.0 (UTS #39 data: tools/names/unicode-16.0.0) — do not edit by hand';
// *(fourth version) every name, word or character a message quotes is isolated (FIRST STRONG ISOLATE … POP DIRECTIONAL ISOLATE):
// an Arabic sentence that quotes a Latin, Greek or Cyrillic character, or a Latin one that quotes an Arabic word, keeps its order
// (atk-legit-r3: the Arabic messages came out scrambled). The app's Arabic sentences (web/src/i18n.js) keep the isolates.
const FSI = '\u2068', PDI = '\u2069', QT = `“${FSI}%s${PDI}”`, CPT = `(${FSI}U+%s${PDI})`;
const MSG = {
  empty: 'Name is required', long: `A name can be up to ${MAXLEN} characters`, digit: 'A name cannot contain numbers',
  letter: `Write a name in Latin, Arabic, Greek or Cyrillic letters — ${QT} ${CPT} is not one of them`,
  unsupported: `The letter ${QT} ${CPT} is not supported in names yet`,
  char: `A name can only have letters, spaces and . - ' ( ) , / ، — remove ${QT} ${CPT}`,
  word: `${QT} is not a word — join it to the word next to it (remove the space)`,
  dash: `Put what follows the name in parentheses — write ${QT}`,
  bracket: `Put the part in brackets after the name — write ${QT}`,
  bracketMix: `What is in brackets is written in one direction — Arabic letters, or Latin, Greek and Cyrillic ones — ${QT} mixes them`,
  mark: 'An accent or vowel mark must sit on a letter, once (at most 3 marks on one letter)',
  script: `Write each word of a name in one alphabet — ${QT} mixes alphabets`,
  accent: `Remove the mark added to ${QT} ${CPT} — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ`,
};
const isoEsc = (s, f) => s.replace(/[\u2068\u2069]/g, (c) => f(c.codePointAt(0).toString(16).toUpperCase()));
const sqlStr = (s) => (/[\u2068\u2069]/.test(s) ? "U&'" + isoEsc(s.replace(/'/g, "''"), (h) => '\\' + h) : "'" + s.replace(/'/g, "''")) + "'";
const sqlHex = (c) => `upper(lpad(to_hex(ascii(${c})), greatest(4, length(to_hex(ascii(${c})))), '0'))`;
const sqlFirstChar = (cls) => `(select coalesce((select x.c from regexp_split_to_table(coalesce(n, ''), '') with ordinality x(c, i)
                                      where public.person_name_norm(x.c) ~ ${cls} order by x.i limit 1),
                                    substring(public.person_name_norm(n) from ${cls})) as c)`;

const sqlBr = { lead: `('^[^' || ${U(sqlClass(LET_ANY))} || ']*[(]')`,
  mix: `('[(][^()]*(?:[' || ${U(sqlClass(LET.Arab))} || '][^()]*[' || ${U(sqlClass(LTR_LET))} || ']|[' || ${U(sqlClass(LTR_LET))} || '][^()]*[' || ${U(sqlClass(LET.Arab))} || '])[^()]*[)]')`,
  side: `('[' || ${U(sqlClass(LET.Arab))} || '][^' || ${U(sqlClass(LET_ANY))} || ']*[(][^()]*[)][^' || ${U(sqlClass(LET_ANY))} || ']*[' || ${U(sqlClass(LTR_LET))} || ']|[' || ${U(sqlClass(LTR_LET))} || '][^' || ${U(sqlClass(LET_ANY))} || ']*[(][^()]*[)][^' || ${U(sqlClass(LET_ANY))} || ']*[' || ${U(sqlClass(LET.Arab))} || ']')` };
// *(fifth version) the letter + mark pairs, last: nested replace() in SQL, one regular expression in the app
const sqlCtx = () => CTX.map(([f, t]) => `, ${U(sqlChars([...f].map((x) => x.codePointAt(0))))}, ${U(sqlChars([...t].map((x) => x.codePointAt(0))))})`).join('');
function sqlRegion() {
  const LIKE_F = U(sqlChars(LIKE.map(([c]) => c))), LIKE_T = U(sqlChars(LIKE.map(([, t]) => t.codePointAt(0))));
  const INV = `'[' || ${U(sqlClass(INVIS))} || ']'`, INV_STRIP = `'[' || ${U(sqlClass(union(INVIS, ARAB_STRIP)))} || ']'`;
  const ZW = `'([' || ${U(sqlClass(ZW_BEFORE))} || '])([' || ${U(sqlClass(ZW_MARK))} || ']*)' || ${U('!200C')} || '+(?=[' || ${U(sqlClass(LET.Arab))} || '])'`;
  return `-- >>> ${HEAD}
-- The name as a person reads it: a zero-width non-joiner between Arabic letters written as a space (fifth version), invisible
-- characters and the tatweel removed, look-alikes of . - ' ( ) , / written as them (the
-- apostrophe as ’), NFKC, the Arabic diacritics removed (vowel marks, tanween, shadda, sukun, superscript alef, Quranic marks), NFKC
-- again, one space between words, none before a slash ("د / محمد" → "د/ محمد") or at the ends.
create or replace function public.person_name_norm(s text)
returns text language sql immutable parallel safe as $$
  select btrim(replace(regexp_replace(normalize(translate(regexp_replace(normalize(translate(regexp_replace(regexp_replace(coalesce(s, ''),
    ${ZW}, '\\1\\2 ', 'g'),
    ${INV}, '', 'g'),
    ${LIKE_F},
    ${LIKE_T}), NFKC),
    ${INV_STRIP}, '', 'g'),
    ${LIKE_F},
    ${LIKE_T}), NFKC),
    '[' || ${U(sqlClass(SPACE))} || ']+', ' ', 'g'), ' /', '/'), ' ')
$$;
-- '' when a (normalised) name is allowed, else the first reason: empty, long, digit, letter, unsupported, char, accent, dash, word,
-- bracket (fifth version: one pair of brackets, after a letter, around letters of one direction, between letters of one direction),
-- mark, script
create or replace function public.person_name_problem(n text)
returns text language sql immutable parallel safe as $$
  select case
    when coalesce(n, '') = '' then 'empty'
    when char_length(n) > ${MAXLEN} then 'long'
    when n ~ ('[' || ${U(sqlClass(DIGIT))} || ']') then 'digit'
    when n ~ ('[' || ${U(sqlClass(OTHER_LET))} || ']') then 'letter'
    when n ~ ('[' || ${U(sqlClass(UNSUP_LET))} || ']') then 'unsupported'
    when n ~ ('[^' || ${U(sqlClass(OK_OR_ACCENT))} || ']') then 'char'
    when n ~ ('[' || ${U(sqlClass(MARK_BAD))} || ']') then 'accent'
    when strpos(n, ' - ') > 0 then 'dash'
    else (select case
      when bool_or(w !~ ('[' || ${U(sqlClass(LET_ANY))} || ']')) then 'word'
      when n !~ '^[^()]*(?:[(][^()]*[)][^()]*)?$' or n ~ ${sqlBr.lead} or n ~ ${sqlBr.mix} or n ~ ${sqlBr.side} then 'bracket'
      when bool_or(w !~ (${sqlWord(LET_ANY, MARK_ANY)})) then 'mark'
      when bool_or(normalize(w, NFD) ~ (${SQL_REPEAT})) then 'mark'
      when exists (select 1 from regexp_split_to_table(n, ${`'[' || ${U(sqlClass(RUN_SEP))} || ']+'`}) r(w)
                    where r.w <> '' and ${sqlScriptOf('r.w', '                      ')} is null) then 'script'
      else '' end
      from unnest(string_to_array(n, ' ')) w)
  end
$$;
-- *(fifth version) the words of a name that hold a letter (what a suggestion keeps), and the name a 'bracket' or 'dash' refusal
-- suggests: every bracketed part moved after the name, in one pair ("(MBA) Ahmed Ali" → "Ahmed Ali (MBA)"; "Ali (علي) محمد" →
-- "Ali محمد (علي)"; two pairs → one), without words that hold no letter; parts of both directions are written without brackets
create or replace function public.person_name_words(s text)
returns text language sql immutable parallel safe as $$
  select coalesce(string_agg(w, ' ' order by i), '') from unnest(string_to_array(public.person_name_norm(s), ' ')) with ordinality u(w, i)
   where w ~ ('[' || ${U(sqlClass(LET_ANY))} || ']')
$$;
create or replace function public.person_name_bracket_fix(m text)
returns text language sql immutable parallel safe as $$
  select public.person_name_norm(case when g is null then base when base !~ ('[' || ${U(sqlClass(LET_ANY))} || ']') then g
                                      when '(' || g || ')' ~ ${sqlBr.mix} then base || ' ' || g2 else base || ' (' || g || ')' end)
    from (select public.person_name_words(regexp_replace(regexp_replace(m, '[(][^()]*(?:[)]|$)', ' ', 'g'), '[()]', ' ', 'g')) as base,
                 string_agg(t, ', ' order by o) as g, string_agg(t, ' ' order by o) as g2
            from (select public.person_name_words(x[1]) as t, o from regexp_matches(coalesce(m, ''), '[(]([^()]*)(?:[)]|$)', 'g') with ordinality r(x, o)) q
           where t <> '') z
$$;
-- the sentence the database and the app say for a reason (the app translates it); n is the name as typed (or normalised): the
-- character named is the one the person typed
create or replace function public.person_name_message(n text, p text)
returns text language sql immutable parallel safe as $$
  select case p
${['empty', 'long', 'digit', 'mark'].map((k) => `    when '${k}' then ${sqlStr(MSG[k])}`).join('\n')}
    when 'letter' then (select format(${sqlStr(MSG.letter)}, c, ${sqlHex('c')})
                          from ${sqlFirstChar(`('[' || ${U(sqlClass(OTHER_LET))} || ']')`)} z)
    when 'unsupported' then (select format(${sqlStr(MSG.unsupported)}, c, ${sqlHex('c')})
                          from ${sqlFirstChar(`('[' || ${U(sqlClass(UNSUP_LET))} || ']')`)} z)
    when 'char' then (select format(${sqlStr(MSG.char)}, c, ${sqlHex('c')})
                        from ${sqlFirstChar(`('[^' || ${U(sqlClass(OK_OR_ACCENT))} || ']')`)} z)
    when 'dash' then (select format(${sqlStr(MSG.dash)}, case when public.person_name_problem(public.person_name_norm(d)) = 'bracket'
                                                                 then public.person_name_bracket_fix(public.person_name_norm(d)) else d end)
                        from (select left(m, strpos(m, ' - ') - 1) || ' (' || replace(substr(m, strpos(m, ' - ') + 3), ' - ', ', ') || ')' as d
                                from (select public.person_name_norm(n) as m) z0) z)
    when 'bracket' then (select case when m ~ ${sqlBr.mix} then format(${sqlStr(MSG.bracketMix)}, substring(m from '[(][^()]*[)]'))
                                     else format(${sqlStr(MSG.bracket)}, public.person_name_bracket_fix(m)) end
                           from (select public.person_name_norm(n) as m) z)
    when 'word' then (select format(${sqlStr(MSG.word)}, w) from unnest(string_to_array(public.person_name_norm(n), ' ')) with ordinality u(w, i)
                       where w !~ ('[' || ${U(sqlClass(LET_ANY))} || ']') order by i limit 1)
    when 'script' then (select format(${sqlStr(MSG.script)}, w) from regexp_split_to_table(public.person_name_norm(n), ${`'[' || ${U(sqlClass(RUN_SEP))} || ']+'`}) with ordinality u(w, i)
                         where w <> '' and ${sqlScriptOf('w', '                         ')} is null order by i limit 1)
    when 'accent' then (select format(${sqlStr(MSG.accent)}, c, ${sqlHex('right(c, 1)')})
                          from (select substring(public.person_name_norm(n) from ('(?:[^' || ${U(sqlClass(ACCENT_AT))} || '])?[' || ${U(sqlClass(MARK_BAD))} || ']')) as c) z)
  end
$$;
-- the skeleton: TR39 confusable prototypes, lower case and no Arabic short vowels, per character of the NFD name; a letter of another
-- alphabet (refused: 'letter') is written U+FFFD with its marks (fifth version: PostgreSQL and the app decompose new letters differently)
create table if not exists private.name_skeleton (ch text primary key, sk text not null);
delete from private.name_skeleton;
insert into private.name_skeleton (ch, sk)
select chr(('x' || lpad(split_part(e, '=', 1), 8, '0'))::bit(32)::int),
       coalesce((select string_agg(chr(('x' || lpad(h, 8, '0'))::bit(32)::int), '' order by o)
                   from unnest(string_to_array(split_part(e, '=', 2), '.')) with ordinality u(h, o)), '')
  from unnest(string_to_array(
'${SKEL_D}', ',')) e;
create or replace function public.person_name_key(s text)
returns text language sql stable parallel safe set search_path = '' as $$
  select ${'replace('.repeat(CTX.length)}regexp_replace(regexp_replace(normalize(array_to_string(array(
    select coalesce((select m.sk from private.name_skeleton m where m.ch = c.ch), c.ch)
      from unnest(regexp_split_to_array(normalize(regexp_replace(public.person_name_norm(s),
        '[' || ${U(sqlClass(OTHER_LET))} || '][' || ${U(sqlClass(MARK_ALL))} || ']*', ${U('!FFFD')}, 'g'), NFD), '')) with ordinality c(ch, i) order by c.i), ''), NFD),
    '([' || ${U(sqlClass(MARK_ALL))} || '])\\1+', '\\1', 'g'),
    '([ij])([' || ${U(sqlClass(MARK_BEFORE_ABOVE))} || ']*)[' || ${U(sqlClass(MARK_ABOVE))} || ']', '\\1\\2', 'g')${sqlCtx()}
$$;
-- <<< generated`;
}

function jsRegion() {
  return `/* >>> ${HEAD} */
  var NM_ZWNJ = /([${jsClass(ZW_BEFORE)}])([${jsClass(ZW_MARK)}]*)\\u200C+(?=[${jsClass(LET.Arab)}])/gu;
  var NM_INVIS = /[${jsClass(INVIS)}]/gu;
  var NM_STRIP = /[${jsClass(union(INVIS, ARAB_STRIP))}]/gu;
  var NM_SPACE = /[${jsClass(SPACE)}]+/gu;
  var NM_LIKE = /[${jsClass(single(LIKE.map(([c]) => c)))}]/gu;
  var NM_LIKE_TO = new Map(${JSON.stringify(LIKE.map(([c, t]) => [ch(c), t]))});
  var NM_DIGIT = /[${jsClass(DIGIT)}]/u;
  var NM_OTHER = /[${jsClass(OTHER_LET)}]/u;
  var NM_UNSUP = /[${jsClass(UNSUP_LET)}]/u;
  var NM_BAD = /[^${jsClass(OK_OR_ACCENT)}]/u;
  var NM_LET = /[${jsClass(LET_ANY)}]/u;
  var NM_WORD = ${jsWord(LET_ANY, MARK_ANY)};
  var NM_REPEAT = /([${jsClass(MARK_ALL)}])[${jsClass(MARK_ALL)}]*\\1/u;
  var NM_ACCENT = /[${jsClass(MARK_BAD)}]/u;
  var NM_ACCENT_AT = /(?:[^${jsClass(ACCENT_AT)}])?[${jsClass(MARK_BAD)}]/u;
  var NM_RUN = /[${jsClass(RUN_SEP)}]+/u;
  var NM_BR_PAIR = /^[^()]*(?:[(][^()]*[)][^()]*)?$/u, NM_BR_LEAD = /^[^${jsClass(LET_ANY)}]*[(]/u;
  var NM_BR_MIX = /[(][^()]*(?:[${jsClass(LET.Arab)}][^()]*[${jsClass(LTR_LET)}]|[${jsClass(LTR_LET)}][^()]*[${jsClass(LET.Arab)}])[^()]*[)]/u;
  var NM_BR_SIDE = /[${jsClass(LET.Arab)}][^${jsClass(LET_ANY)}]*[(][^()]*[)][^${jsClass(LET_ANY)}]*[${jsClass(LTR_LET)}]|[${jsClass(LTR_LET)}][^${jsClass(LET_ANY)}]*[(][^()]*[)][^${jsClass(LET_ANY)}]*[${jsClass(LET.Arab)}]/u;
  var NM_SCRIPTS = [${SCRIPTS.map(([k]) => `['${k}', ${jsWord(LET[k], MARK[k])}]`).join(', ')}];
  var NM_MSG = ${isoEsc(JSON.stringify(MSG), (h) => '\\u' + h)};
  var NM_RUN_MARK = /([${jsClass(MARK_ALL)}])\\1+/gu;
  var NM_SOFT = /([ij])([${jsClass(MARK_BEFORE_ABOVE)}]*)[${jsClass(MARK_ABOVE)}]/gu;
  var NM_OTHER_RUN = /[${jsClass(OTHER_LET)}][${jsClass(MARK_ALL)}]*/gu;
  var NM_CTX = new Map(${JSON.stringify(CTX)});
  var NM_CTX_RE = ${CTX.length ? `/${CTX.map(([f]) => [...f].map((x) => '\\u{' + hx(x.codePointAt(0)) + '}').join('')).join('|')}/gu` : '/(?!)/gu'};
  var NM_SKEL = (function (d) { var m = new Map(); d.split(',').forEach(function (e) { var p = e.split('='); m.set(String.fromCodePoint(parseInt(p[0], 16)), p[1] ? p[1].split('.').map(function (h) { return String.fromCodePoint(parseInt(h, 16)); }).join('') : ''); }); return m; })(
    '${SKEL_D}');
  function nmLikeTo(c) { return NM_LIKE_TO.get(c); }
  function nmNorm(x) { return String(x == null ? '' : x).replace(NM_ZWNJ, '$1$2 ').replace(NM_INVIS, '').replace(NM_LIKE, nmLikeTo).normalize('NFKC').replace(NM_STRIP, '').replace(NM_LIKE, nmLikeTo).normalize('NFKC').replace(NM_SPACE, ' ').replace(/ \\//g, '/').replace(/^ | $/g, ''); }
  function nmWords(x) { return nmNorm(x).split(' ').filter(function (w) { return NM_LET.test(w); }).join(' '); }
  function nmBrFix(m) {
    var g = [], re = /[(]([^()]*)(?:[)]|$)/gu, x; while ((x = re.exec(m))) { var t = nmWords(x[1]); if (t) g.push(t); }
    var base = nmWords(m.replace(/[(][^()]*(?:[)]|$)/gu, ' ').replace(/[()]/gu, ' '));
    return nmNorm(!g.length ? base : !NM_LET.test(base) ? g.join(', ') : NM_BR_MIX.test('(' + g.join(', ') + ')') ? base + ' ' + g.join(' ') : base + ' (' + g.join(', ') + ')');
  }
  function nmScript(w) { var f = NM_SCRIPTS.find(function (p) { return p[1].test(w); }); return f ? f[0] : null; }
  function nmProblem(n) {
    if (!n) return 'empty'; if (Array.from(n).length > ${MAXLEN}) return 'long'; if (NM_DIGIT.test(n)) return 'digit'; if (NM_OTHER.test(n)) return 'letter'; if (NM_UNSUP.test(n)) return 'unsupported'; if (NM_BAD.test(n)) return 'char'; if (NM_ACCENT.test(n)) return 'accent';
    if (n.indexOf(' - ') >= 0) return 'dash';
    var w = n.split(' '); if (w.some(function (x) { return !NM_LET.test(x); })) return 'word';
    if (!NM_BR_PAIR.test(n) || NM_BR_LEAD.test(n) || NM_BR_MIX.test(n) || NM_BR_SIDE.test(n)) return 'bracket';
    if (w.some(function (x) { return !NM_WORD.test(x) || NM_REPEAT.test(x.normalize('NFD')); })) return 'mark';
    return n.split(NM_RUN).some(function (x) { return x !== '' && !nmScript(x); }) ? 'script' : '';
  }
  function nmMessage(s, p) {
    var m = (p === 'bracket' && NM_BR_MIX.test(nmNorm(s)) ? NM_MSG.bracketMix : NM_MSG[p]) || '', n = nmNorm(s), put = function (v) { return m.replace('%s', function () { return v; }); };
    if (p === 'letter' || p === 'unsupported' || p === 'char') { var re = p === 'letter' ? NM_OTHER : p === 'unsupported' ? NM_UNSUP : NM_BAD, c = Array.from(String(s == null ? '' : s)).find(function (x) { return re.test(nmNorm(x)); }) || (n.match(re) || [''])[0];
      m = put(c); return put((c.codePointAt(0) || 0).toString(16).toUpperCase().padStart(4, '0')); }
    if (p === 'word') return put(n.split(' ').find(function (x) { return !NM_LET.test(x); }) || '');
    if (p === 'dash') { var i = n.indexOf(' - '), d = n.slice(0, i) + ' (' + n.slice(i + 3).split(' - ').join(', ') + ')';
      return put(nmProblem(nmNorm(d)) === 'bracket' ? nmBrFix(nmNorm(d)) : d); }
    if (p === 'bracket') return put(NM_BR_MIX.test(n) ? n.match(/[(][^()]*[)]/u)[0] : nmBrFix(n));
    if (p === 'script') return put(n.split(NM_RUN).find(function (x) { return x !== '' && !nmScript(x); }) || '');
    if (p === 'accent') { var a = (n.match(NM_ACCENT_AT) || [''])[0]; m = put(a); return put((Array.from(a).pop() || '').codePointAt(0).toString(16).toUpperCase().padStart(4, '0')); }
    return m;
  }
  function nmSkel(x) { return Array.from(nmNorm(x).replace(NM_OTHER_RUN, '\\uFFFD').normalize('NFD'), function (c) { var k = NM_SKEL.get(c); return k == null ? c : k; }).join('').normalize('NFD').replace(NM_RUN_MARK, '$1').replace(NM_SOFT, '$1$2').replace(NM_CTX_RE, function (m) { return NM_CTX.get(m); }); }
/* <<< generated */`;
}

function region(file, start, end, body) {
  const src = fs.readFileSync(file, 'utf8'), a = src.indexOf(start), b = src.indexOf(end);
  if (a < 0 || b < a) throw new Error(`no generated region in ${path.relative(ROOT, file)}`);
  const nl = src.lastIndexOf('\n', a) + 1, close = b + end.length;
  return { src, old: src.slice(nl, close), put: () => fs.writeFileSync(file, src.slice(0, nl) + body + src.slice(close)) };
}
const R = [region(MIGRATION, '-- >>> generated', '-- <<< generated', sqlRegion()), region(ADAPTER, '/* >>> generated', '/* <<< generated */', jsRegion())];
const want = [sqlRegion(), jsRegion()];

if (process.argv.includes('--write')) {
  R.forEach((r, i) => r.put()); console.log(`written: ${path.relative(ROOT, MIGRATION)}, ${path.relative(ROOT, ADAPTER)} (${SKEL.length} skeleton entries, ${LIKE.length} punctuation look-alikes)`);
} else if (process.argv.includes('--list-like')) {
  console.log(LIKE.map(([c, t]) => `U+${hx(c)} ${ch(c)} → ${t}`).join('\n'));
} else if (process.argv.includes('--check') || process.argv.includes('--expect')) {
  const bad = R.map((r, i) => (r.old !== want[i] ? [MIGRATION, ADAPTER][i] : null)).filter(Boolean);
  if (bad.length) { console.error('the generated name rule differs from tools/names/name_rule.mjs in: ' + bad.map((f) => path.relative(ROOT, f)).join(', ') + ' — run node tools/names/name_rule.mjs --write'); process.exit(1); }
  if (process.argv.includes('--check')) { console.log('name rule: both generated regions are current'); process.exit(0); }
  // run the adapter's generated code itself, then check it against the rule's own definitions before printing anything
  const body = R[1].old.split('\n').slice(1, -1).join('\n');
  const F = new Function(body + '\nreturn { nmNorm: nmNorm, nmProblem: nmProblem, nmSkel: nmSkel, nmMessage: nmMessage };')();
  const fails = [], expect = (what, got, exp) => { if (got !== exp && fails.length < 40) fails.push(`${what}: got ${JSON.stringify(got)} want ${JSON.stringify(exp)}`); };
  const P = (s) => F.nmProblem(F.nmNorm(s));
  for (const [s, p] of [['د. هالة الشامي', ''], ['Dr. Ahmed El-Sayed', ''], ["O'Brien", ''], ['O’Brien', ''], ['José Müller', ''], ['Ünal', ''], ['د. نرمين أبو زيدٍ', ''],
    ['Al-Hassan (Pharm.D.)', ''], ['Smith, John', ''], ['Мария Иванова', ''], ['Νίκος Παπαδόπουλος', ''], ['هـالة', ''], ['Dr. Zeina X​', ''], ['Dr. Zeina X\u{1D173}', ''],
    ['د/ هيثم دويدار', ''], ['Ph/ Mohamed Hassan', ''], ['أ.د/ محمد', ''], ['Dr. Мария Иванова', ''], ['Мария Иванова (Maria Ivanova)', ''], ['Dr. Νίκος Παπαδόπουλος', ''],
    ['Anne‑Marie Dubois', ''], ['Dr. Ahmed El–Sayed', ''], ['د. أحمد علي، صيدلي', ''], ['Марʼяна Григорʼєва', ''], ['O‘Brien Kelly', ''], ['O´Brien Kelly', ''], ['O`Brien', ''],
    ['\u08BDبيل', 'unsupported'], ['ع\u08BCت', 'unsupported'], ['Pharm. Иван', ''], ['Ivan Ιωάννης', ''], ['Вера Иванова', ''], ['Dr. \u0405\u0430\u04CF\u0456\u04BB', ''], ['\u0405\u0430\u04CF\u0456\u04BB \u0405\u0430\u04CF\u0456\u04BB', ''], ['Dr. Рара X', ''],
    // third version: real Greek and Cyrillic names (atk-legit-r2), titles glued to a name, every dash
    ['Μαρία', ''], ['Νίκη', ''], ['Ειρήνη', ''], ['Μαρίνα Μάρκου', ''], ['Άννα Βίσση', ''], ['Dr. Νίκη Βίσση', ''], ['ΑΝΝΑ ΚΑΡΑΤΖΑ', ''], ['Вера Кох', ''], ['ОКСАНА КОРОТКОВА', ''], ['АННА АХМАТОВА', ''],
    ['Dr.أحمد علي', ''], ['د.Ahmed', ''], ['Jean—Paul', ''], ['Ἀλέξανδρος', ''], ['Mo’men Abd El-Raouf', ''], ['مُحَمَّد عَبْدُ الرَّحْمٰن', ''], ['İsmail Ñúñez', ''], ['Nguyễn Thị Ánh', ''], ['Məmmədov', ''],
    // third version: a mark NFKC cannot join to its letter (atk-unicode-r2, atk-bypass-r2), letters outside the everyday blocks
    ['Ahme\u0335d', 'accent'], ['Sali\u0307h', 'accent'], ['Sal\u0131\u0307h', 'accent'], ['j\u0307ana', 'accent'], ['\u03A4\u0304\u0391\u03A3\u039F\u03A3', 'accent'], ['\u0396\u0304\u03B7\u03BD\u03C9', 'accent'],
    ['N\u0335ada', 'accent'], ['\u039D\u0335', 'accent'], ['W\u0335ael', 'accent'], ['o\u0335\u0338', 'accent'], ['o\u0338\u0335', 'accent'], ['\u0173\u0308\u0304', 'accent'], ['Ade\u1ECD\u0301la', 'accent'],
    ['\uA78DEXOB', 'unsupported'], ['Ahmed \u{1DF00}', 'unsupported'], ['Ahmed X\u{1E08F}', 'accent'], ['ب\u0654ب', 'accent'], ['\u0427\u0415\u0425\u041E\u0412', ''],
    ['Dr. Rana 2', 'digit'], ['Ali ١', 'digit'], ['Dr. Hala X · Pharco X', 'char'], ['Dr. Hala X ꞏ Pharco X', 'unsupported'], ['Dr. Hala X ⸳ Pharco X', 'char'], ['Dr. Hala X \u{11174} Pharco X', 'char'],
    ['Dr. Hala X \u{1F797} Pharco X', 'char'], ['Dr. Hala X \u{111D0} Pharco X', 'digit'], ['Dr. Hala X ∘ Pharco X', 'char'], ['Dr. Hala X ▪ Pharco X', 'char'], ['Dr. Zeina X￼', 'char'],
    ['Dr. Hala X ￼ႉ Pharco X', 'char'], ['Dr. Hala X - Pharco X', 'dash'], ['د . أحمد علي', 'word'], ['Ahmed Ali , PhD', 'word'], ['Dr. Rаna X', 'script'], ['张伟 (Zhang Wei)', 'letter'],
    ['Ab́́́́', 'accent'], ['Ab́́', 'accent'], ['é́', 'accent'], ['Ab ́', 'accent'], ['Ab ́b', 'accent'], ['Ahmed "Mido" Ali', 'char'], ['Gal·la', 'char'],
    ['', 'empty'], ['A'.repeat(121), 'long'],
    // fourth version: Arabic diacritics are removed (so a name made of them alone is empty), a spaced slash joins the word before it,
    // ʿ is ’, a spaced hyphen has its own reason, letters of the four alphabets the rule does not take say so (atk-unicode-r3, atk-legit-r3)
    ['دّّ', ''], ['دَُِّ', ''], ['ب َ', ''], ['َ', 'empty'], ['حْالد', ''], ['د / محمد علي', ''], ['ا.د / سامي فهمي', ''], ['د/ سامي / صيدلي', ''], ['Saʿīd Ḥasan', ''],
    ['Ahmed Ali - MBA', 'dash'], ['Hala Ali – Head of QA', 'dash'], ['Ɗanjuma Ƙasim', 'unsupported'], ['Ɔpɔku Mensah', 'unsupported'], ['Ɛfua', 'unsupported'],
    ['Ọláfẹ́mi Adébáyọ̀', 'accent'], ['إِنَّهُۥ', ''], ['ب\u0654\u064Eب', 'accent'],
    // fifth version (v-spoof-r1, v-real-r1): brackets the bidi algorithm can reorder, Maghrebi ڭ ڢ, the zero-width non-joiner
    ['(MBA) Ahmed Ali', 'bracket'], ['(صيدلي) أحمد علي', 'bracket'], ['Ali (علي) محمد', 'bracket'], ['منى (Ali) Mona', 'bracket'], ['Ahmed Ali (MBA', 'bracket'],
    ['Ahmed) Ali', 'bracket'], ['Hala Ali (Head of QA) (Pharco)', 'bracket'], ['Ali (Head, فاركو)', 'bracket'], ['(Ahmed)', 'bracket'],
    ['Ahmed Ali (MBA)', ''], ['أحمد علي (صيدلي)', ''], ['Ali محمد (علي)', ''], ['Ahmed (Mido) Ali', ''], ['Ziad (زياد)', ''], ['Mona (منى) Ali', ''],
    ['ڭمال العلوي', ''], ['ڢاطمة', ''], ['ځلمی', 'unsupported'], ['علی\u200Cرضا', '']])
    expect('allowlist ' + JSON.stringify(s), P(s), p);
  for (const [s, n] of [["O'Brien", 'O’Brien'], ['Anne‑Marie', 'Anne-Marie'], ['El–Sayed', 'El-Sayed'], ['O´Brien', 'O’Brien'], ['﴾صيدلي﴿', '(صيدلي)'], ['هـالة', 'هالة'], ['Mª', 'Ma'], ['Jean—Paul', 'Jean-Paul'], ['Jean〰Paul', 'Jean-Paul'], ['Dr.أحمد', 'Dr.أحمد'], ['Jose\u0301', 'José'],
    ['حْالد', 'حالد'], ['رْياد', 'رياد'], ['دْكي', 'دكي'], ['عْادة', 'عادة'], ['حسںْ', 'حسں'], ['مُحَمَّد عَبْدُ الرَّحْمٰن', 'محمد عبد الرحمن'], ['د. نرمين أبو زيدٍ', 'د. نرمين أبو زيد'], ['إِنَّهُۥ', 'إنه'],
    ['ا\u064E\u0654', 'أ'], ['ا\u06D6\u0654', 'أ'], ['ب َ ب', 'ب ب'], ['ﹰ', ''], ['د / محمد علي', 'د/ محمد علي'], ['ا.د / سامي فهمي', 'ا.د/ سامي فهمي'], ['د/ سامي / صيدلي', 'د/ سامي/ صيدلي'],
    ['Ahmed Ali / Pharco', 'Ahmed Ali/ Pharco'], ['Saʿīd Ḥasan', 'Sa’īd Ḥasan'], ['Fāʾiza', 'Fā’iza'],
    ['علی\u200Cرضا محمدی\u200Cنژاد', 'علی رضا محمدی نژاد'], ['عبد\u200Cالله', 'عبدالله'], ['Ah\u200Cmed', 'Ahmed'], ['عل\u064E\u200Cی', 'عل ی']])
    expect('normalised ' + JSON.stringify(s), F.nmNorm(s), n);
  const iq = (x) => '“\u2068' + x + '\u2069”', icp = (h) => '(\u2068U+' + h + '\u2069)';
  for (const [s, m] of [['د/ هيثم X1', 'A name cannot contain numbers'], ['Anne★Marie', `A name can only have letters, spaces and . - ' ( ) , / ، — remove ${iq('★')} ${icp('2605')}`],
    ['张伟', `Write a name in Latin, Arabic, Greek or Cyrillic letters — ${iq('张')} ${icp('5F20')} is not one of them`], ['د . أحمد', `${iq('.')} is not a word — join it to the word next to it (remove the space)`],
    ['Dr. Rаna', `Write each word of a name in one alphabet — ${iq('Rаna')} mixes alphabets`], ['Ahme\u0335d', `Remove the mark added to ${iq('e\u0335')} ${icp('0335')} — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ`],
    ['Sal\u0131\u0307h', `Remove the mark added to ${iq('\u0131\u0307')} ${icp('0307')} — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ`],
    ['Ahmed X\u{1E08F}', `Remove the mark added to ${iq('X\u{1E08F}')} ${icp('1E08F')} — Drugbox accepts an accented letter typed as one character, such as é, ü or ñ`],
    ['Dr.Rаna', `Write each word of a name in one alphabet — ${iq('Rаna')} mixes alphabets`], ['Ahmed \uFE69x', `A name can only have letters, spaces and . - ' ( ) , / ، — remove ${iq('\uFE69')} ${icp('FE69')}`],
    ['Ahmed Ali - MBA', `Put what follows the name in parentheses — write ${iq('Ahmed Ali (MBA)')}`], ['Hala Ali – Head of QA', `Put what follows the name in parentheses — write ${iq('Hala Ali (Head of QA)')}`],
    ['Ɗanjuma Ƙasim', `The letter ${iq('Ɗ')} ${icp('018A')} is not supported in names yet`], ['Ɔpɔku', `The letter ${iq('Ɔ')} ${icp('0186')} is not supported in names yet`],
    ['Hala Ali – Head of QA – Pharco', `Put what follows the name in parentheses — write ${iq('Hala Ali (Head of QA, Pharco)')}`],
    ['(MBA) Ahmed Ali', `Put the part in brackets after the name — write ${iq('Ahmed Ali (MBA)')}`], ['Ali (علي) محمد', `Put the part in brackets after the name — write ${iq('Ali محمد (علي)')}`],
    ['Hala Ali (Head of QA) (Pharco)', `Put the part in brackets after the name — write ${iq('Hala Ali (Head of QA, Pharco)')}`], ['(Ahmed)', `Put the part in brackets after the name — write ${iq('Ahmed')}`],
    ['Ali (Head, فاركو)', `What is in brackets is written in one direction — Arabic letters, or Latin, Greek and Cyrillic ones — ${iq('(Head, فاركو)')} mixes them`]])
    expect('message ' + JSON.stringify(s), F.nmMessage(s, P(s)), m);
  for (const [a, b] of [['حالد', 'حْالد'], ['خالد', 'خالد'], ['Dr. Rana X', 'Dr. Rаna X'], ['Ilya', 'llya'], ["O'Brien", 'O’Brien'], ['هالة', 'هالَة'], ['Dr. Nermeen X', 'DR. NERMEEN X'], ['Dr. Zeina X', 'Dr. Zeina X​'],
    ['Dr. Papa X', 'Dr. Рара X'], ['Dr. Salih', 'Dr. \u0405\u0430\u04CF\u0456\u04BB'], ['Salih', '\u0405\u0430\u04C0\u0456\u04BB'], ['ЧЕХОВ', 'ЧЕХОВ'], ['زڒ', 'زۯ'], ['فاطمة', 'ڧاطمة'], ['علي', 'على'], ['علي', 'علی'], ['كريم', 'کریم'], ['هالة', 'ہالۃ'], ['Anne-Marie', 'Anne‑Marie'],
    ['ثروت عادل', 'ئروت عادل'], ['Szőke Anna', 'Szổke Anna'], ['Ġorġ', 'Ģorģ'], ['ḁla', 'ạla'], ['علی\u200Cرضا', 'علی رضا'], ['\u{105C9}abc', '\u{11383}abc']])
    expect('same skeleton ' + a + ' / ' + b, F.nmSkel(a) === F.nmSkel(b), true);
  expect('different skeleton', F.nmSkel('Dr. Zeina X') === F.nmSkel('Dr. Zeina Y'), false);
  expect('a letter of another alphabet is U+FFFD in the skeleton', F.nmSkel('\u{105C9}abc'), '\uFFFDabc');
  // *(fourth version) a name with a mark over an undotted letter is STORED without it: what others see is «حالد», not a «خالد» look-alike
  for (const [a, b] of [['حْالد', 'خالد'], ['رْياد', 'زياد'], ['دْكي', 'ذكي'], ['عْادة', 'غادة'], ['حسںْ', 'حسن']]) {
    expect('stored without the mark ' + a, /[\u064B-\u0652\u0670]/u.test(F.nmNorm(a)), false); expect('a different name ' + a + ' / ' + b, F.nmNorm(a) === F.nmNorm(b), false); }
  for (let c = 1; c <= PLANES01; c++) {   // the classes as defined: a letter of the four scripts, Allowed, alone in a Latin/Arabic word
    if (isSur(c)) continue; const s = ch(c);
    if (/^\p{N}$/u.test(s) && stable(c)) expect('number U+' + hx(c), P('Ab' + s + 'ab'), 'digit');
    if (PUNCT.includes(c) || isSpace(c) || inR(INVIS)(c)) continue;
    if (LIKE_MAP.has(c)) { expect('look-alike U+' + hx(c), F.nmNorm('Ab' + s + 'ab'), 'Ab' + LIKE_MAP.get(c) + 'ab'); continue; }
    if (stable(c) && /^\p{L}$/u.test(s) && !ALLOWED.has(c) && !isStrip(c)) expect('restricted letter U+' + hx(c), P('Ab' + s + 'ab'), /^\p{N}$/u.test(s) ? 'digit' : inScript4(c) ? 'unsupported' : 'letter');
    if (isStrip(c)) expect('an Arabic mark is removed U+' + hx(c), F.nmNorm('بب' + s + 'بب'), 'بببب');
    for (const f of [(x) => 'Ab' + x + 'ab', (x) => 'بب' + x + 'بب', (x) => 'Ab ' + x + ' ab']) { const n1 = F.nmNorm(f(s)); expect('normalising twice changes nothing U+' + hx(c), F.nmNorm(n1), n1); }
    if (stable(c) && /^[\p{S}\p{Co}\p{Cn}\p{Zl}\p{Zp}]$/u.test(s) && !DI(c)) expect('symbol / private / unassigned U+' + hx(c), P('Ab' + s + 'ab'), 'char');
    if (stable(c) && /^\p{P}$/u.test(s)) expect('punctuation U+' + hx(c), P('Ab' + s + 'ab'), 'char');
  }
  for (const d of [0x00B7, 0x2022, 0x2219, 0x22C5, 0x30FB, 0xA78F, 0x2E33, 0x11174, 0x1F797, 0x111D0, 0x2218, 0x25AA, 0xFFFC, 0xFFFD, 0x0387, 0x16EB])
    expect('separator look-alike U+' + hx(d), P('Dr. Hala X ' + ch(d) + ' Pharco X') !== '', true);
  for (const [c] of LIKE) expect('a look-alike is never the separator U+' + hx(c), F.nmNorm(ch(c)).includes('·'), false);
  if (fails.length) { console.error('the generated name rule does not follow its definition:\n' + fails.join('\n')); process.exit(1); }   // nothing printed yet
  // COPY text format: a backslash is written twice; tabs and line breaks never survive nmNorm (spaces), but NFKC/NFD columns may hold them
  const esc = (t) => t.replace(/\\/g, '\\\\').replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\r/g, '\\r');
  const PLACES = [['w', (s) => 'Ab' + s + 'ab'], ['s', (s) => 'Ab ' + s + ' ab'], ['b', (s) => s + 'ab'], ['r', (s) => 'بب' + s + 'بب']];
  const out = [];
  for (let c = 1; c <= PLANES01; c++) {
    if (isSur(c)) continue; const s = ch(c), nf = esc(s.normalize('NFKC')), nd = esc(s.normalize('NFD'));
    for (const [pl, f] of PLACES) {
      const raw = f(s), n = F.nmNorm(raw), p = F.nmProblem(n), m = p && (pl === 'w' || pl === 's') ? F.nmMessage(raw, p) : '';
      out.push(`${c}\t${pl}\t${esc(n)}\t${p}\t${esc(F.nmSkel(raw))}\t${nf}\t${nd}\t${esc(m)}`);
    }
    if (out.length >= 40000) { process.stdout.write(out.join('\n') + '\n'); out.length = 0; }
  }
  process.stdout.write(out.join('\n') + (out.length ? '\n' : ''));
} else if (process.argv.includes('--strings')) {
  // *(fourth version) what the ADAPTER's generated code makes of each string of a file (one per line, backslash-escaped, '#' starts a
  // comment): TSV string, normalised name, problem, skeleton, message, and whether the normalised name still holds a combining mark
  // (an allowed one never does: accented letters are one character, Arabic diacritics are removed) — supabase/tests/name_rule.sql
  // compares the database with it for every string the verifiers used (supabase/tests/name_rule_strings.txt)
  const file = process.argv[process.argv.indexOf('--strings') + 1];
  const body = R[1].old.split('\n').slice(1, -1).join('\n');
  const F = new Function(body + '\nreturn { nmNorm: nmNorm, nmProblem: nmProblem, nmSkel: nmSkel, nmMessage: nmMessage };')();
  const esc = (t) => t.replace(/\\/g, '\\\\').replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\r/g, '\\r');
  const unesc = (t) => t.replace(/\\(.)/g, (m, x) => (x === 't' ? '\t' : x === 'n' ? '\n' : x === 'r' ? '\r' : x));
  const out = [];
  for (const l of fs.readFileSync(path.resolve(ROOT, file), 'utf8').split('\n')) {
    if (l === '' || l.startsWith('#')) continue; const raw = unesc(l), n = F.nmNorm(raw), p = F.nmProblem(n);
    out.push([esc(raw), esc(n), p, esc(F.nmSkel(raw)), esc(p ? F.nmMessage(raw, p) : ''), /\p{M}/u.test(n) ? 't' : 'f'].join('\t'));
  }
  process.stdout.write(out.join('\n') + (out.length ? '\n' : ''));
} else console.log('usage: node tools/names/name_rule.mjs --write | --check | --expect | --strings FILE | --list-like');
