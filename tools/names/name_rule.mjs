// The one rule for a person's display name (S-03, migration 0038): what a name may contain (an ALLOWLIST) and when two names are
// "the same name" (a confusable SKELETON, Unicode TR39). The database (supabase/migrations/0038_names_allowlist.sql) and the live
// app (web/src/live/adapter.js) both carry the code this script prints between their "generated" markers — never edit it by hand:
//   node tools/names/name_rule.mjs --write    rewrite both generated regions (only before 0038 is applied anywhere: an applied
//                                             migration is never edited — a new rule goes into a new migration)
//   node tools/names/name_rule.mjs --check    exit 1 when a region differs from what this script generates
//   node tools/names/name_rule.mjs --expect   --check, then what the ADAPTER's generated code makes of every code point of planes 0-1
//                                             in four places (TSV: code point, place, normalised name, problem, skeleton, NFKC, NFD);
//                                             supabase/tests/name_rule.sql loads it and compares the database's functions with it
// Data: Node's own Unicode tables (General_Category, Script, Script_Extensions, Default_Ignorable_Code_Point, NFKC/NFD) and the
// UTS #39 security data vendored in tools/names/unicode-16.0.0 (IdentifierStatus.txt, confusables.txt — see its README). Node 22
// carries Unicode 16.0, the same version as the vendored data; this script refuses to run on another one.
//
// THE RULE
//  normalise (person_name_norm / nmNorm): remove every invisible character (Default_Ignorable_Code_Point, format Cf, control Cc —
//    tab and line breaks excepted —, U+2800, U+1D159) and the Arabic tatweel U+0640 (it only stretches a joining line: "هـالة" reads
//    "هالة"), NFKC, remove them again (NFKC can produce a tatweel: U+FE71), every kind of space or line break is one space, no space
//    at either end.
//  allowed (person_name_problem / nmProblem: '' when allowed, else the first reason, in this order):
//    empty   nothing left
//    long    more than 120 characters
//    digit   a number of any script (\p{N}: 0-9, ٠-٩, ۰-۹, ①, Ⅻ…)
//    char    anything that is not: a LETTER (\p{L}) of the Latin, Arabic, Greek or Cyrillic script whose Identifier_Status is Allowed
//            (TR39 — so no ꞏ U+A78F, no click letters ǀ ǁ ǂ ǃ, no modifier letters of the Common script ʼ ˑ), a combining MARK (\p{M})
//            with Identifier_Status Allowed, the space, or one of . - ' ’ ( ) ,   (so no symbol, no other punctuation — the picker's
//            separator "·" and every look-alike of it —, no private use, no unassigned code point, no U+FFFC / U+FFFD)
//    word    a word (between spaces) with no letter: " - ", "(", "."
//    mark    a mark that does not sit on a letter, or more than 3 marks on one letter
//    script  a word that mixes scripts: every word is ONE script (its marks are of that script or generic "Inherited" marks), Latin
//            and Arabic words may stand side by side, Greek and Cyrillic only as the script of the whole name (TR39 "single script"
//            per word; whole-name for the scripts whose letters copy Latin ones: "Dr. Rаna" with a Cyrillic а is refused)
//  skeleton (person_name_key / nmSkel): NFD of the normalised name, every character replaced by its key, NFD again. A character's
//    key is the fixed point of: TR39 confusable prototype (confusables.txt) of each character, then lower case, then NFD — and the
//    Arabic short vowels and shadda (U+064B-U+0652, U+0670) are dropped (names are written with or without them), and so is U+FFFC
//    (it draws nothing; names stored before 0038 may hold it). So "Rana" and
//    "Rаna", "Ilya" and "llya", "O'Brien" and "O’Brien", "هالة" and "هال\u064Eة" have the same skeleton: the ✎ New message picker, the
//    resolver and the chat header treat them as the same name and tell the members apart.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const DATA = path.join(ROOT, 'tools/names/unicode-16.0.0');
const MIGRATION = path.join(ROOT, 'supabase/migrations/0038_names_allowlist.sql');
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
const PUNCT = [0x27, 0x28, 0x29, 0x2C, 0x2D, 0x2E, 0x2019];   // ' ( ) , - . ’
const SCRIPTS = [['Latn', 'Latin'], ['Arab', 'Arabic'], ['Grek', 'Greek'], ['Cyrl', 'Cyrillic']];
const stable = (c) => ch(c).normalize('NFKC') === ch(c);
const LET = {}, MARK = {};
for (const [k, sc] of SCRIPTS) {
  const inSc = has(new RegExp(`^\\p{Script=${sc}}$`, 'u')), inScx = has(new RegExp(`^\\p{Script_Extensions=${sc}}$`, 'u'));
  const inherited = has(/^\p{Script_Extensions=Inherited}$/u);
  LET[k] = ranges((c) => ALLOWED.has(c) && /^\p{L}$/u.test(ch(c)) && inSc(c) && stable(c));
  MARK[k] = ranges((c) => ALLOWED.has(c) && /^\p{M}$/u.test(ch(c)) && (inScx(c) || inherited(c)) && stable(c));
}
const union = (...rss) => { const s = new Set(); for (const rs of rss) for (const [a, b] of rs) for (let c = a; c <= b; c++) s.add(c); return ranges((c) => s.has(c)); };
const single = (l) => l.slice().sort((a, b) => a - b).map((c) => [c, c]);
const LET_ANY = union(...SCRIPTS.map(([k]) => LET[k])), MARK_ANY = union(...SCRIPTS.map(([k]) => MARK[k]));
const OK = union(LET_ANY, MARK_ANY, single(PUNCT), [[0x20, 0x20]]);

// ── the skeleton map: every code point of planes 0-1 that can stand in an NFD-normalised name and whose key is not itself ──
const DROP = new Set([0x064B, 0x064C, 0x064D, 0x064E, 0x064F, 0x0650, 0x0651, 0x0652, 0x0670, 0xFFFC]);   // Arabic short vowels, shadda, sukun, dagger alef; U+FFFC draws nothing (a name stored before 0038 may hold it)
const base = (c) => (DROP.has(c) ? '' : CONF.has(c) ? CONF.get(c) : ch(c));
const step = (s) => [...[...s.normalize('NFD')].map((x) => base(x.codePointAt(0))).join('')].map((x) => x.toLowerCase()).join('').normalize('NFD');
function keyOf(c) { let s = ch(c); for (let i = 0; i < 16; i++) { const t = step(s); if (t === s) return s; s = t; } throw new Error('no fixed point for U+' + c.toString(16)); }
const SKEL = [];
for (let c = 1; c <= PLANES01; c++) { if (isSur(c)) continue; const s = ch(c); if (s.normalize('NFD') !== s || !stable(c)) continue; const k = keyOf(c); if (k !== s) SKEL.push([c, k]); }
const hx = (c) => c.toString(16).toUpperCase();
const SKEL_D = SKEL.map(([c, k]) => hx(c) + '=' + [...k].map((x) => hx(x.codePointAt(0))).join('.')).join(',');

// ── printing the classes ──
const SQL_SPECIAL = { 0x2D: '\\-', 0x5D: '\\]', 0x5E: '\\^', 0x5C: '\\\\' };
function sqlClass(rs) { return rs.map(([a, b]) => { const f = (c) => SQL_SPECIAL[c] || (c > 0xFFFF ? '!+' + hx(c).padStart(6, '0') : '!' + hx(c).padStart(4, '0')); return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
function jsClass(rs) { return rs.map(([a, b]) => { const f = (c) => '\\u{' + hx(c) + '}'; return a === b ? f(a) : f(a) + '-' + f(b); }).join(''); }
const U = (s) => `U&'${s}' uescape '!'`;
const sqlWord = (L, M) => `'^[' || ${U(sqlClass(single(PUNCT)))} || ']*(?:[' || ${U(sqlClass(L))} || '][' || ${U(sqlClass(M))} || ']{0,3}[' || ${U(sqlClass(single(PUNCT)))} || ']*)+$'`;
const jsWord = (L, M) => `/^[${jsClass(single(PUNCT))}]*(?:[${jsClass(L)}][${jsClass(M)}]{0,3}[${jsClass(single(PUNCT))}]*)+$/u`;
const HEAD = 'generated by tools/names/name_rule.mjs from Unicode 16.0.0 (UTS #39 data: tools/names/unicode-16.0.0) — do not edit by hand';
const MSG = {
  empty: 'Name is required', long: `A name can be up to ${MAXLEN} characters`, digit: 'A name cannot contain numbers',
  char: 'A name can only have letters, spaces and . - \' ’ ( ) , — remove “%s” (U+%s)', word: 'Each word of a name needs a letter',
  mark: 'An accent or vowel mark must sit on a letter (at most 3 on one letter)',
  script: 'Write each word of a name in one alphabet (Latin or Arabic; Greek or Cyrillic only for the whole name)',
};
const sqlStr = (s) => "'" + s.replace(/'/g, "''") + "'";

function sqlRegion() {
  return `-- >>> ${HEAD}
-- The name as a person reads it: invisible characters and the tatweel removed, NFKC, one space between words, none at the ends.
create or replace function public.person_name_norm(s text)
returns text language sql immutable parallel safe as $$
  select btrim(regexp_replace(regexp_replace(normalize(regexp_replace(coalesce(s, ''),
    '[' || ${U(sqlClass(INVIS))} || ']', '', 'g'), NFKC),
    '[' || ${U(sqlClass(INVIS))} || ']', '', 'g'),
    '[' || ${U(sqlClass(SPACE))} || ']+', ' ', 'g'), ' ')
$$;
-- '' when a (normalised) name is allowed, else the first reason: empty, long, digit, char, word, mark, script
create or replace function public.person_name_problem(n text)
returns text language sql immutable parallel safe as $$
  select case
    when coalesce(n, '') = '' then 'empty'
    when char_length(n) > ${MAXLEN} then 'long'
    when n ~ ('[' || ${U(sqlClass(DIGIT))} || ']') then 'digit'
    when n ~ ('[^' || ${U(sqlClass(OK))} || ']') then 'char'
    else (select case
      when bool_or(w !~ ('[' || ${U(sqlClass(LET_ANY))} || ']')) then 'word'
      when bool_or(w !~ (${sqlWord(LET_ANY, MARK_ANY)})) then 'mark'
      when bool_or(s is null) then 'script'
      when count(distinct s) > 1 and bool_or(s in ('Grek', 'Cyrl')) then 'script'
      else '' end
      from (select w, case
${SCRIPTS.map(([k]) => `              when w ~ (${sqlWord(LET[k], MARK[k])}) then '${k}'`).join('\n')}
            end as s from unnest(string_to_array(n, ' ')) w) x)
  end
$$;
-- the sentence the database and the app say for a reason (the app translates it)
create or replace function public.person_name_message(n text, p text)
returns text language sql immutable parallel safe as $$
  select case p
${Object.entries(MSG).filter(([k]) => k !== 'char').map(([k, v]) => `    when '${k}' then ${sqlStr(v)}`).join('\n')}
    when 'char' then (select format(${sqlStr(MSG.char)}, c, upper(lpad(to_hex(ascii(c)), greatest(4, length(to_hex(ascii(c)))), '0')))
                        from substring(n from ('[^' || ${U(sqlClass(OK))} || ']')) c)
  end
$$;
-- the skeleton: TR39 confusable prototypes, lower case and no Arabic short vowels, per character of the NFD name
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
  select normalize(array_to_string(array(
    select coalesce((select m.sk from private.name_skeleton m where m.ch = c.ch), c.ch)
      from unnest(regexp_split_to_array(normalize(public.person_name_norm(s), NFD), '')) with ordinality c(ch, i) order by c.i), ''), NFD)
$$;
-- <<< generated`;
}

function jsRegion() {
  return `/* >>> ${HEAD} */
  var NM_INVIS = /[${jsClass(INVIS)}]/gu;
  var NM_SPACE = /[${jsClass(SPACE)}]+/gu;
  var NM_DIGIT = /[${jsClass(DIGIT)}]/u;
  var NM_BAD = /[^${jsClass(OK)}]/u;
  var NM_LET = /[${jsClass(LET_ANY)}]/u;
  var NM_WORD = ${jsWord(LET_ANY, MARK_ANY)};
  var NM_SCRIPTS = [${SCRIPTS.map(([k]) => `['${k}', ${jsWord(LET[k], MARK[k])}]`).join(', ')}];
  var NM_MSG = ${JSON.stringify(MSG)};
  var NM_SKEL = (function (d) { var m = new Map(); d.split(',').forEach(function (e) { var p = e.split('='); m.set(String.fromCodePoint(parseInt(p[0], 16)), p[1] ? p[1].split('.').map(function (h) { return String.fromCodePoint(parseInt(h, 16)); }).join('') : ''); }); return m; })(
    '${SKEL_D}');
  function nmNorm(x) { return String(x == null ? '' : x).replace(NM_INVIS, '').normalize('NFKC').replace(NM_INVIS, '').replace(NM_SPACE, ' ').replace(/^ | $/g, ''); }
  function nmProblem(n) {
    if (!n) return 'empty'; if (Array.from(n).length > ${MAXLEN}) return 'long'; if (NM_DIGIT.test(n)) return 'digit'; if (NM_BAD.test(n)) return 'char';
    var w = n.split(' '); if (w.some(function (x) { return !NM_LET.test(x); })) return 'word'; if (w.some(function (x) { return !NM_WORD.test(x); })) return 'mark';
    var s = w.map(function (x) { var f = NM_SCRIPTS.find(function (p) { return p[1].test(x); }); return f ? f[0] : null; });
    if (s.some(function (x) { return !x; })) return 'script';
    if (s.some(function (x) { return x !== s[0]; }) && s.some(function (x) { return x === 'Grek' || x === 'Cyrl'; })) return 'script';
    return '';
  }
  function nmMessage(n, p) { if (p !== 'char') return NM_MSG[p] || ''; var c = (n.match(NM_BAD) || [''])[0]; return NM_MSG.char.replace('%s', c).replace('%s', (c.codePointAt(0) || 0).toString(16).toUpperCase().padStart(4, '0')); }
  function nmSkel(x) { return Array.from(nmNorm(x).normalize('NFD'), function (c) { var k = NM_SKEL.get(c); return k == null ? c : k; }).join('').normalize('NFD'); }
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
  R.forEach((r, i) => r.put()); console.log(`written: ${path.relative(ROOT, MIGRATION)}, ${path.relative(ROOT, ADAPTER)} (${SKEL.length} skeleton entries)`);
} else if (process.argv.includes('--check') || process.argv.includes('--expect')) {
  const bad = R.map((r, i) => (r.old !== want[i] ? [MIGRATION, ADAPTER][i] : null)).filter(Boolean);
  if (bad.length) { console.error('the generated name rule differs from tools/names/name_rule.mjs in: ' + bad.map((f) => path.relative(ROOT, f)).join(', ') + ' — run node tools/names/name_rule.mjs --write'); process.exit(1); }
  if (process.argv.includes('--check')) { console.log('name rule: both generated regions are current'); process.exit(0); }
  // run the adapter's generated code itself, then check it against the rule's own definitions before printing anything
  const body = R[1].old.split('\n').slice(1, -1).join('\n');
  const F = new Function(body + '\nreturn { nmNorm: nmNorm, nmProblem: nmProblem, nmSkel: nmSkel, nmMessage: nmMessage };')();
  const fails = [], expect = (what, got, exp) => { if (got !== exp && fails.length < 40) fails.push(`${what}: got ${JSON.stringify(got)} want ${JSON.stringify(exp)}`); };
  const P = (s) => F.nmProblem(F.nmNorm(s));
  for (const [s, p] of [['د. هالة الشامي', ''], ['Dr. Ahmed El-Sayed', ''], ["O'Brien", ''], ['O’Brien', ''], ['José Müller', ''], ['Ünal', ''], ['د. نرمين أبو زيد\u064D', ''],
    ['Al-Hassan (Pharm.D.)', ''], ['Smith, John', ''], ['Мария Иванова', ''], ['Νίκος Παπαδόπουλος', ''], ['هـالة', ''], ['Dr. Zeina X\u200B', ''], ['Dr. Zeina X\u{1D173}', ''],
    ['Dr. Rana 2', 'digit'], ['Ali ١', 'digit'], ['Dr. Hala X · Pharco X', 'char'], ['Dr. Hala X ꞏ Pharco X', 'char'], ['Dr. Hala X ⸳ Pharco X', 'char'], ['Dr. Hala X \u{11174} Pharco X', 'char'],
    ['Dr. Hala X \u{1F797} Pharco X', 'char'], ['Dr. Hala X \u{111D0} Pharco X', 'digit'], ['Dr. Hala X ∘ Pharco X', 'char'], ['Dr. Hala X ▪ Pharco X', 'char'], ['Dr. Zeina X\uFFFC', 'char'],
    ['Dr. Hala X \uFFFCႉ Pharco X', 'char'], ['Dr. Hala X - Pharco X', 'word'], ['Dr. Rаna X', 'script'], ['Pharm. Иван', 'script'], ['Ivan Ιωάννης', 'script'], ['Ab\u0301\u0301\u0301\u0301', 'mark'], ['Ab \u0301', 'word'], ['Ab \u0301b', 'mark'], ['', 'empty'], ['A'.repeat(121), 'long']])
    expect('allowlist ' + JSON.stringify(s), P(s), p);
  for (const [a, b] of [['Dr. Rana X', 'Dr. Rаna X'], ['Ilya', 'llya'], ["O'Brien", 'O’Brien'], ['هالة', 'هال\u064Eة'], ['Dr. Nermeen X', 'DR. NERMEEN X'], ['Dr. Zeina X', 'Dr. Zeina X\u200B']])
    expect('same skeleton ' + a + ' / ' + b, F.nmSkel(a) === F.nmSkel(b), true);
  expect('different skeleton', F.nmSkel('Dr. Zeina X') === F.nmSkel('Dr. Zeina Y'), false);
  for (let c = 1; c <= PLANES01; c++) {   // the classes as defined: a letter of the four scripts, Allowed, alone in a Latin/Arabic word
    if (isSur(c)) continue; const s = ch(c);
    if (/^\p{N}$/u.test(s) && stable(c)) expect('number U+' + hx(c), P('Ab' + s + 'ab'), 'digit');
    if (PUNCT.includes(c) || isSpace(c) || inR(INVIS)(c)) continue;
    if (stable(c) && /^\p{L}$/u.test(s) && !ALLOWED.has(c)) expect('restricted letter U+' + hx(c), P('Ab' + s + 'ab'), /^\p{N}$/u.test(s) ? 'digit' : 'char');
    if (stable(c) && /^[\p{S}\p{Co}\p{Cn}\p{Zl}\p{Zp}]$/u.test(s) && !DI(c)) expect('symbol / private / unassigned U+' + hx(c), P('Ab' + s + 'ab'), 'char');
    if (stable(c) && /^\p{P}$/u.test(s)) expect('punctuation U+' + hx(c), P('Ab' + s + 'ab'), 'char');
  }
  for (const d of [0x00B7, 0x2022, 0x2219, 0x22C5, 0x30FB, 0xA78F, 0x2E33, 0x11174, 0x1F797, 0x111D0, 0x2218, 0x25AA, 0xFFFC, 0xFFFD, 0x0387, 0x16EB])
    expect('separator look-alike U+' + hx(d), P('Dr. Hala X ' + ch(d) + ' Pharco X') !== '', true);
  if (fails.length) { console.error('the generated name rule does not follow its definition:\n' + fails.join('\n')); process.exit(1); }   // nothing printed yet
  // COPY text format: a backslash is written twice; tabs and line breaks never survive nmNorm (spaces), but NFKC/NFD columns may hold them
  const esc = (t) => t.replace(/\\/g, '\\\\').replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\r/g, '\\r');
  const PLACES = [['w', (s) => 'Ab' + s + 'ab'], ['s', (s) => 'Ab ' + s + ' ab'], ['b', (s) => s + 'ab'], ['r', (s) => 'بب' + s + 'بب']];
  const out = [];
  for (let c = 1; c <= PLANES01; c++) {
    if (isSur(c)) continue; const s = ch(c), nf = esc(s.normalize('NFKC')), nd = esc(s.normalize('NFD'));
    for (const [pl, f] of PLACES) { const n = F.nmNorm(f(s)); out.push(`${c}\t${pl}\t${esc(n)}\t${F.nmProblem(n)}\t${esc(F.nmSkel(f(s)))}\t${nf}\t${nd}`); }
    if (out.length >= 40000) { process.stdout.write(out.join('\n') + '\n'); out.length = 0; }
  }
  process.stdout.write(out.join('\n') + (out.length ? '\n' : ''));
} else console.log('usage: node tools/names/name_rule.mjs --write | --check | --expect');
