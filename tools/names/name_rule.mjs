// The one rule that turns a typed name into the name a person sees (S-03): the database (clean_person_name, 0037) and the live
// app (nmClean in web/src/live/adapter.js) apply the same steps with the same character classes, printed by this script.
//   node tools/names/name_rule.mjs --classes   the classes, as SQL (U&'…' uescape '!') and as JavaScript (/[…]/u)
//   node tools/names/name_rule.mjs --expect    checks the adapter's nmClean against the rule's definition (every character that is
//                                              default-ignorable, a format or control character, a space, a dot look-alike, a
//                                              free-standing combining mark), then prints, for every code point, what nmClean makes
//                                              of it in three places (TSV: code point, place, result as hex code points) — the
//                                              database suite supabase/tests/name_rule.sql loads it and compares clean_person_name
// Steps (the same order in both):
//   1. remove INVIS: every Default_Ignorable_Code_Point, every format (Cf) and control (Cc) character that is not a line break or
//      tab, and the characters that draw nothing (braille blank U+2800, musical null notehead U+1D159)
//   2. NFKC (full-width, ligatures, compatibility forms: "Ｄｒ" is "Dr", "･" is "・")
//   3. every kind of space, tab or line break is one plain space
//   4. a combining mark with no letter before it (at the start or after a space) is removed: it would draw a free dot or line
//   5. a dot or bullet look-alike (the picker writes "name · company") becomes " - ", and so does an Arabic-Indic zero standing alone
//   6. runs of spaces are one space; no space at either end
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const MAXCP = 0x10FFFF;
const isSur = (c) => c >= 0xD800 && c <= 0xDFFF;
function ranges(test) { const r = []; let s = -1, p = -2; for (let c = 0; c <= MAXCP; c++) { if (isSur(c) || !test(c)) continue; if (c !== p + 1) { if (s >= 0) r.push([s, p]); s = c; } p = c; } if (s >= 0) r.push([s, p]); return r; }
const has = (re) => (c) => re.test(String.fromCodePoint(c));
const SPACE_CPS = [[0x09, 0x0D], [0x20, 0x20], [0x85, 0x85], [0xA0, 0xA0], [0x1680, 0x1680], [0x2000, 0x200A], [0x2028, 0x2029], [0x202F, 0x202F], [0x205F, 0x205F], [0x3000, 0x3000]];
const inR = (rs) => (c) => rs.some(([a, b]) => c >= a && c <= b);
const isSpace = inR(SPACE_CPS);
const DI = has(/^\p{Default_Ignorable_Code_Point}$/u), CF = has(/^\p{Cf}$/u), CC = has(/^\p{Cc}$/u), MARK = has(/^\p{M}$/u);
const BLANK = [0x2800, 0x1D159];
const INVIS = ranges((c) => !isSpace(c) && (DI(c) || CF(c) || CC(c) || BLANK.includes(c)));
const MARKS = ranges((c) => MARK(c) && !DI(c));
// a dot or a bullet drawn at mid or raised height, in any script — read as the picker's "·"
const DOTS = [0x00B7, 0x02D1, 0x0387, 0x0887, 0x0888, 0x0971, 0x0F0B, 0x0F0C, 0x119E, 0x1427, 0x16EB, 0x16EC, 0x18DF, 0x2022, 0x2023, 0x2027, 0x2043,
  0x204C, 0x204D, 0x2219, 0x22C5, 0x25CF, 0x25D8, 0x25E6, 0x2619, 0x26AB, 0x2765, 0x2767, 0x2981, 0x29BE, 0x29BF, 0x2B24, 0x2E30, 0x2E31, 0x2E33,
  0x30FB, 0x318D, 0xA78F, 0xFE45, 0xFE46, 0xFF65, 0x10101, 0x1091F, 0x10A50, 0x10AF4, 0x11049, 0x1123A, 0x115C4, 0x11A41, 0x11A9A, 0x11C43, 0x1F784];
const ZEROS = [0x0660, 0x06F0];   // ٠ ۰ draw a dot at mid height: read as "·" when they stand alone between spaces

const hx = (c) => c.toString(16).toUpperCase();
function sqlClass(rs) { return rs.map(([a, b]) => { a = Math.max(a, 1);   /* a database text never holds U+0000 */ const f = (c) => (c > 0xFFFF ? '!+' + hx(c).padStart(6, '0') : '!' + hx(c).padStart(4, '0')); return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
function jsClass(rs) { return rs.map(([a, b]) => { const f = (c) => '\\u{' + hx(c) + '}'; return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
const single = (l) => l.slice().sort((a, b) => a - b).map((c) => [c, c]);

if (process.argv.includes('--classes')) {
  for (const [n, rs] of [['INVIS', INVIS], ['SPACE', SPACE_CPS], ['MARKS', MARKS], ['DOTS', single(DOTS)], ['ZEROS', single(ZEROS)]]) {
    console.log(`-- ${n} (${rs.length} ranges)\nSQL ${n}: ${sqlClass(rs)}\nJS  ${n}: ${jsClass(rs)}\n`);
  }
} else if (process.argv.includes('--expect')) {
  // nmClean exactly as the adapter has it (its one line), run here
  const src = fs.readFileSync(path.join(ROOT, 'web/src/live/adapter.js'), 'utf8');
  const lines = src.split('\n').filter((l) => /^\s*var NM_[A-Z]+ = /.test(l) || /^\s*function nmClean\(/.test(l));
  if (lines.length < 2) { console.error('nmClean not found in adapter.js'); process.exit(2); }
  const nmClean = new Function(lines.join('\n') + '\nreturn nmClean;')();
  const fails = [];
  const want = (name, got, exp) => { if (got !== exp && fails.length < 40) fails.push(`${name}: got ${JSON.stringify(got)} want ${JSON.stringify(exp)}`); };
  for (let c = 1; c <= MAXCP; c++) {
    if (isSur(c)) continue; const s = String.fromCodePoint(c);
    if (isSpace(c)) want('space U+' + hx(c), nmClean('a' + s + 'b'), 'a b');
    else if (DI(c) || CF(c) || CC(c)) want('invisible U+' + hx(c), nmClean('a' + s + 'b'), 'ab');
    if (MARK(c) && !DI(c) && s.normalize('NFKC') === s) want('free mark U+' + hx(c), nmClean('a ' + s + 'b'), 'a b');
  }
  for (const d of DOTS) { const s = String.fromCodePoint(d); want('dot U+' + hx(d), nmClean('Dr. Hala X ' + s + ' Pharco X'), 'Dr. Hala X - Pharco X'); want('dot (tight) U+' + hx(d), nmClean('X' + s + 'Y'), 'X - Y'); }
  for (const z of ZEROS) { const s = String.fromCodePoint(z); want('zero U+' + hx(z), nmClean('هالة ' + s + ' فاركو'), 'هالة - فاركو'); want('zero in a number U+' + hx(z), nmClean('Lab 1' + s + '1'), 'Lab 1' + s.normalize('NFKC') + '1'); }
  // the strings the verifier used (p1b reverify1, s03b.py)
  want('verifier U+A78F', nmClean('Dr. Hala Tufice ꞏ Pharco Tufice'), 'Dr. Hala Tufice - Pharco Tufice');
  want('verifier U+2E33', nmClean('Dr. Hala Tufice ⸳ Pharco Tufice'), 'Dr. Hala Tufice - Pharco Tufice');
  want('verifier U+1D173', nmClean('Dr. Zeina Tufice\u{1D173}'), 'Dr. Zeina Tufice');
  want('verifier U+1BCA0', nmClean('Dr. Zeina\u{1BCA0} Tufice'), 'Dr. Zeina Tufice');
  want('Arabic name kept', nmClean('د. نرمين  أبو زيد'), 'د. نرمين أبو زيد');
  if (fails.length) { console.error('nmClean does not follow the name rule:\n' + fails.join('\n')); process.exit(1); }   // nothing written yet
  // what nmClean makes of every code point, in three places — inside a word (w), alone between spaces (s), at the start (b) — and
  // what NFKC makes of the character here (the database skips a code point whose NFKC differs: a newer Unicode in one of them).
  // COPY text format: a backslash is written twice; the results hold no tab or line break (step 3).
  const out = [], esc = (t) => t.replace(/\\/g, '\\\\');
  for (let c = 1; c <= MAXCP; c++) {
    if (isSur(c)) continue; const s = String.fromCodePoint(c), nf = esc(s.normalize('NFKC')).replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\r/g, '\\r');
    out.push(`${c}\tw\t${esc(nmClean('a' + s + 'b'))}\t${nf}`, `${c}\ts\t${esc(nmClean('a ' + s + ' b'))}\t${nf}`, `${c}\tb\t${esc(nmClean(s + 'b'))}\t${nf}`);
    if (out.length >= 30000) { process.stdout.write(out.join('\n') + '\n'); out.length = 0; }
  }
  process.stdout.write(out.join('\n') + (out.length ? '\n' : ''));
} else console.log('usage: node tools/names/name_rule.mjs --classes | --expect');
