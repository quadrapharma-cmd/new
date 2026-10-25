// The @username rule (S-03, the owner's decision of 25 Oct — «خد قاعدة الفيسبوك في تشابه الاسماء معندهمش اي قيود و بيدي في الاخر يوزر
// لكل واحد»: Facebook's rule — names may be alike, every member has a unique username). One source for the database
// (supabase/migrations/0070_usernames.sql) and the app: the demo layer web/src/username.js (what a username may be, its key, the
// sentences — the demo's Edit Profile and ✎ picker use it, and so does the live app) and the live adapter web/src/live/adapter.js
// (the username made from a name, usBase — it needs the name rule's nmNorm and NM_TITLE, which live there). This script prints the
// code between their "generated" markers — never edit it by hand:
//   node tools/names/username_rule.mjs --write     rewrite the three generated regions (only before 0070_usernames is applied anywhere:
//                                                  an applied migration is never edited — a new rule goes into a new migration)
//   node tools/names/username_rule.mjs --check     exit 1 when a region differs from what this script generates
//   node tools/names/username_rule.mjs --expect    --check, then what the APP's generated code makes of every name of
//                                                  tests/names/username_names.txt (TSV: name, base) and of every username of
//                                                  tests/names/username_strings.txt (TSV: username, key, problem, message);
//                                                  supabase/tests/usernames.sql compares the database's functions with it
// THE RULE
//  a username  a-z, 0-9 and '.', 5-30 characters, at least one letter, no dot at either end or after another dot. Capitals typed are
//              written small («Ahmed.Ali» is «ahmed.ali»).
//  its KEY     (profiles.username_key — unique): the username in small letters without its dots, every character that draws like
//              another written as it: confusables.txt (Unicode 16.0.0, vendored in tools/names/unicode-16.0.0) for ASCII gives 0 / o,
//              1 / l / I and m / rn; tools/names/username-twins.txt adds the owner's i / l, vv / w, cl / d and what
//              tools/names/render_scan.py --part usernames finds in the app's fonts. So «ahmed.ali» = «ahmedali» = «ahrned.ali» =
//              «ahmed.a1i»: one of them can be taken, never two — two usernames can never draw alike.
//  reserved    a username whose key is one of RESERVED_WHOLE, or one of whose dot-separated parts (digits left out) is one of
//              RESERVED_PART («drugbox.support», «admin2», «help.desk»), or that holds the key of «drugbox» anywhere, is Drugbox's.
//  made from a name (usBase — sign-up, and every member who had none when 0070 ran): the name as the name rule writes it, its titles
//              left out (the name rule's own list: «Dr.», «د.», «Eng.» …), the part in brackets left out; the words, a particle joined
//              to the word after it (عبد، أبو، بن، ابن، بنت، أم، آل; Abd, Abdel, Abu, El, Al, Ibn, Bin, Ben, Bint, Om, Umm…); each word in
//              Latin letters — a Latin word without its accents (José → jose, ø → o, ß → ss: the Unicode root collation), a Greek or
//              Cyrillic word romanised (GREEK, CYRILLIC below), an Arabic word as Egyptians write it: tools/names/translit-ar.txt
//              («محمد» → mohamed, «عبد الرحمن» → abdelrahman, «ال…» → el…), else letter by letter (LETTERS below); the first and
//              the last word, joined by a dot («محمد أحمد علي» → mohamed.ali), at most 30 characters; «member» when nothing is left
//              or the result is reserved. The database then takes the first free one of base, base.2, base.3 … (a short base gets
//              a number at once: «ali» → ali.1), race-free (0070: username_assign).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const DATA = path.join(ROOT, 'tools/names/unicode-16.0.0');
const MIGRATION = path.join(ROOT, 'supabase/migrations/0070_usernames.sql');
const LAYER = path.join(ROOT, 'web/src/username.js');
const ADAPTER = path.join(ROOT, 'web/src/live/adapter.js');
const APP = path.join(ROOT, 'web/base/app.html');
if (process.versions.unicode !== '16.0') { console.error(`Node carries Unicode ${process.versions.unicode}; the vendored data is 16.0 — use Node 22`); process.exit(2); }
const ch = (c) => String.fromCodePoint(c);
const hx = (c) => c.toString(16).toUpperCase().padStart(4, '0');
const MIN = 5, MAX = 30;

// ── the key: ASCII look-alikes ──
const conf = fs.readFileSync(path.join(DATA, 'confusables.txt'), 'utf8');
if (!/# Version: 16\.0\.0/.test(conf)) throw new Error('confusables.txt is not version 16.0.0');
const ALNUM = 'abcdefghijklmnopqrstuvwxyz0123456789';
const PAIRS = [];   // [one character, what it draws as]
for (const l of conf.split('\n')) {
  const m = /^([0-9A-F]+)\s*;\s*([0-9A-F ]+?)\s*;\s*MA\b/.exec(l); if (!m) continue;
  const s = ch(parseInt(m[1], 16)).toLowerCase(), t = m[2].split(' ').map((x) => ch(parseInt(x, 16))).join('').toLowerCase();
  if (s.length === 1 && ALNUM.includes(s) && t !== s && [...t].every((x) => ALNUM.includes(x))) PAIRS.push([s, t, 'confusables.txt']);
}
for (const l of fs.readFileSync(path.join(ROOT, 'tools/names/username-twins.txt'), 'utf8').split('\n')) {
  const m = /^([a-z0-9]+) ; ([a-z0-9]+)\s*(?:#.*)?$/.exec(l); if (!m) continue;
  const [a, b] = m[1].length === 1 ? [m[1], m[2]] : [m[2], m[1]];
  if (a.length !== 1) throw new Error('tools/names/username-twins.txt: one side must be one character: ' + l);
  PAIRS.push([a, b, 'username-twins.txt']);
}
// single characters that draw alike are one character (the lowest letter, else the lowest digit); a character that draws like a
// sequence is written as that sequence, in which each character is written as its own key
const up = new Map(), find = (x) => { while (up.get(x) !== x) x = up.get(x); return x; };
for (const c of ALNUM) up.set(c, c);
const rank = (c) => (/[a-z]/.test(c) ? 0 : 1) * 100 + ALNUM.indexOf(c);
for (const [a, b] of PAIRS) if (b.length === 1) { const x = find(a), y = find(b); if (x !== y) { const [lo, hi] = rank(x) < rank(y) ? [x, y] : [y, x]; up.set(hi, lo); } }
const KEY = new Map();
for (const c of ALNUM) if (find(c) !== c) KEY.set(c, find(c));
for (const [a, b] of PAIRS) if (b.length > 1) {
  const t = [...b].map((x) => find(x)).join(''); if (KEY.has(a) && KEY.get(a) !== t) throw new Error(`the key of ${a} is both ${KEY.get(a)} and ${t}`);
  KEY.set(a, t); for (const x of ALNUM) if (find(x) === a && x !== a) KEY.set(x, t);
}
for (const t of KEY.values()) for (const x of t) if (KEY.has(x)) throw new Error('a key is not a fixed point: ' + x);
const KEY1 = [...KEY].filter(([, t]) => t.length === 1), KEYN = [...KEY].filter(([, t]) => t.length > 1);
const keyOf = (u) => [...String(u).toLowerCase().replace(/\./g, '')].map((x) => KEY.get(x) ?? x).join('');

// ── reserved ──
const RESERVED_PART = ['drugbox', 'admin', 'administrator', 'support', 'help', 'helpdesk', 'official', 'moderator', 'moderators', 'staff', 'team',
  'security', 'payments', 'payment', 'billing', 'verify', 'verified', 'verification', 'system', 'root', 'noreply', 'abuse', 'trust', 'safety'];
const RESERVED_WHOLE = ['about', 'account', 'accounts', 'alerts', 'anonymous', 'api', 'careers', 'channel', 'channels', 'companies', 'contact', 'deals',
  'directory', 'email', 'events', 'everyone', 'feed', 'groups', 'info', 'insights', 'jobs', 'legal', 'login', 'logout', 'mail', 'market', 'marketplace',
  'members', 'messages', 'network', 'news', 'notifications', 'null', 'postmaster', 'privacy', 'profile', 'register', 'sales', 'settings', 'signin',
  'signup', 'terms', 'training', 'undefined', 'updates', 'username', 'usernames', 'webmaster', 'academy', 'drugboxnews', 'drugboxjobs', 'drugboxacademy',
  'drugboxmarket', 'drugboxdeals', 'drugboxinsights', 'drugboxteam', 'drugboxofficial', 'drugboxsupport', 'member'];
const RES_PART_K = [...new Set(RESERVED_PART.map(keyOf))], RES_WHOLE_K = [...new Set([...RESERVED_WHOLE, ...RESERVED_PART].map(keyOf))], RES_BRAND_K = keyOf('drugbox');
// «member» is whole-reserved only as the BARE fallback is numbered: usBase never returns a reserved word but «member», and username_assign
// numbers it (member.2 …) — so the bare «member» stays free of a person who chose it
RES_WHOLE_K.splice(RES_WHOLE_K.indexOf(keyOf('member')), 1);

// ── made from a name: the tables ──
// Latin, Greek, Cyrillic: each letter of the everyday blocks (the name rule's: Basic Latin … Latin Extended Additional, Greek and Coptic,
// Greek Extended, Cyrillic, Cyrillic Supplement) in plain small Latin letters
const BLOCKS = [[0x0041, 0x024F], [0x0250, 0x02AF], [0x1E00, 0x1EFF], [0x0370, 0x03FF], [0x1F00, 0x1FFF], [0x0400, 0x052F]];
const GREEK = { α: 'a', β: 'v', γ: 'g', δ: 'd', ε: 'e', ζ: 'z', η: 'i', θ: 'th', ι: 'i', κ: 'k', λ: 'l', μ: 'm', ν: 'n', ξ: 'x', ο: 'o', π: 'p', ρ: 'r', σ: 's', ς: 's',
  τ: 't', υ: 'y', φ: 'f', χ: 'ch', ψ: 'ps', ω: 'o', ϝ: 'w', ϲ: 's', ϳ: 'j', ϗ: 'k' };
const CYRILLIC = { а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ж: 'zh', з: 'z', и: 'i', й: 'y', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r', с: 's',
  т: 't', у: 'u', ф: 'f', х: 'kh', ц: 'ts', ч: 'ch', ш: 'sh', щ: 'shch', ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya', ё: 'e', і: 'i', ї: 'yi', є: 'ye', ґ: 'g',
  ў: 'u', ђ: 'dj', ј: 'j', љ: 'lj', њ: 'nj', ћ: 'c', џ: 'dz', ѕ: 'dz', ғ: 'gh', қ: 'q', ң: 'ng', ү: 'u', ұ: 'u', һ: 'h', ә: 'a', ө: 'o', ӏ: 'l', ҳ: 'h', ҷ: 'j', ӣ: 'i', ӯ: 'u' };
const LATIN_EXTRA = { þ: 'th', ð: 'd', ŋ: 'n', ə: 'e', ɛ: 'e', ɔ: 'o', ı: 'i', ĸ: 'k', ſ: 's', ƒ: 'f', ʒ: 'z', ß: 'ss', ŀ: 'l', ɨ: 'i', ʉ: 'u', ɑ: 'a', ɡ: 'g', ɪ: 'i', ʊ: 'u' };
const COLL = new Intl.Collator('und', { sensitivity: 'base' }), AZ = [...'abcdefghijklmnopqrstuvwxyz'];
const ASCII = new Map();   // a letter → its Latin letters
for (const [a, b] of BLOCKS) for (let c = a; c <= b; c++) {
  const s = ch(c); if (!/^\p{L}$/u.test(s) || /^[a-z]$/.test(s)) continue; const lo = s.toLowerCase(), bare = lo.normalize('NFD').replace(/\p{M}/gu, '');
  let t = null;
  if (/^\p{Script=Latin}$/u.test(s)) {
    if (/^[a-z]+$/.test(bare)) t = bare; else if (lo in LATIN_EXTRA) t = LATIN_EXTRA[lo]; else if (bare in LATIN_EXTRA) t = LATIN_EXTRA[bare];
    else { t = AZ.find((x) => COLL.compare(lo, x) === 0) || AZ.flatMap((x) => AZ.map((y) => x + y)).find((xy) => COLL.compare(lo, xy) === 0) || ''; }
  } else if (/^\p{Script=Greek}$/u.test(s)) t = GREEK[lo] ?? GREEK[bare] ?? '';
  else if (/^\p{Script=Cyrillic}$/u.test(s)) t = CYRILLIC[lo] ?? CYRILLIC[bare] ?? '';
  else continue;
  ASCII.set(s, t);
}
// Arabic: a word of tools/names/translit-ar.txt, looked up after the typing fold (AR_FOLD: the hamza / madda forms as their letter, ة → ه,
// ى → ي — the name rule's search key does the same); a word not listed is written letter by letter: LETTERS gives each letter ONE
// character — a capital or a digit for a consonant (1 th, 2 kh, 3 sh, 4 gh, 5 ch, 6 zh), a small letter for a vowel —, an «a» goes
// between two consonants (Arabic writes no short vowels: «حسن» → hasan), and the result is written small with the digits spelled
const AR_FOLD = { 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ؤ': 'و', 'ئ': 'ي', 'ى': 'ي', 'ة': 'ه', 'ی': 'ي', 'ک': 'ك', 'ۀ': 'ه', 'ۃ': 'ه', 'ھ': 'ه', 'ہ': 'ه', 'ە': 'ه', 'ے': 'ي', 'ء': '' };
const LETTERS = { 'ا': 'a', 'أ': 'a', 'إ': 'e', 'آ': 'a', 'ٱ': 'a', 'ء': '', 'ؤ': 'o', 'ئ': 'e', 'ب': 'B', 'ت': 'T', 'ث': '1', 'ج': 'G', 'ح': 'H', 'خ': '2', 'د': 'D',
  'ذ': 'Z', 'ر': 'R', 'ز': 'Z', 'س': 'S', 'ش': '3', 'ص': 'S', 'ض': 'D', 'ط': 'T', 'ظ': 'Z', 'ع': 'a', 'غ': '4', 'ف': 'F', 'ق': 'K', 'ك': 'K', 'ل': 'L', 'م': 'M',
  'ن': 'N', 'ه': 'H', 'و': 'o', 'ي': 'i', 'ى': 'a', 'ة': 'a', 'پ': 'P', 'چ': '5', 'ژ': '6', 'گ': 'G', 'ک': 'K', 'ی': 'i', 'ڤ': 'V', 'ڨ': 'G', 'ڭ': 'G', 'ڢ': 'F',
  'ڧ': 'K', 'ٹ': 'T', 'ڈ': 'D', 'ڑ': 'R', 'ڕ': 'R', 'ڵ': 'L', 'ں': 'N', 'ھ': 'H', 'ہ': 'H', 'ۀ': 'H', 'ۂ': 'H', 'ۃ': 'a', 'ۆ': 'o', 'ێ': 'i', 'ے': 'i', 'ۓ': 'e', 'ە': 'a' };
// before LETTERS: و / ي starting a word are consonants (W, Y); after it: an «a» between two consonants, then the digits spelled
const AR_PRE = [['^و', 'W'], ['^[يی]', 'Y']];
const AR_POST = [['([B-Z1-6])(?=[B-Z1-6])', '$1a']];
const DIGRAPH = { 1: 'th', 2: 'kh', 3: 'sh', 4: 'gh', 5: 'ch', 6: 'zh' };
const AR_FOLD_FROM = Object.keys(AR_FOLD).sort((a, b) => (AR_FOLD[a] === '') - (AR_FOLD[b] === '')).join(''), AR_FOLD_TO = [...AR_FOLD_FROM].map((x) => AR_FOLD[x]).join('');
const arFold = (w) => [...w].map((x) => AR_FOLD[x] ?? x).join('');
const TABLE = new Map();
for (const l of fs.readFileSync(path.join(ROOT, 'tools/names/translit-ar.txt'), 'utf8').split('\n')) {
  if (!l.trim() || l.startsWith('#')) continue; const m = /^(\S+) ; ([a-z]+)$/.exec(l.trim()); if (!m) throw new Error('tools/names/translit-ar.txt: ' + l);
  const k = arFold(m[1]); if (TABLE.has(k) && TABLE.get(k) !== m[2]) throw new Error(`tools/names/translit-ar.txt: ${m[1]} is both ${TABLE.get(k)} and ${m[2]}`); TABLE.set(k, m[2]);
}
for (const k of TABLE.keys()) for (const x of k) if (!(x in LETTERS)) throw new Error('tools/names/translit-ar.txt: a letter LETTERS does not know: ' + x + ' in ' + k);
const PART_LAT = ['abd', 'abdel', 'abdul', 'abdal', 'abu', 'abou', 'abo', 'el', 'al', 'ibn', 'bin', 'ben', 'bint', 'om', 'umm', 'um', 'oum'];
const PART_AR = ['عبد', 'ابو', 'ابن', 'بن', 'بنت', 'ام', 'ال', 'ال'].map(arFold);
// the name rule's titles (dxGreetName's T in the approved demo — the same list the name rule reads)
const TITLES = (() => { const m = /\bT=\/\^\(\?:([^)]*)\)\$\/i,/.exec(fs.readFileSync(APP, 'utf8')); if (!m) throw new Error('web/base/app.html: no title list T in dxGreetName'); return m[1].split('|'); })();

// ── printing ──
const HEAD = 'generated by tools/names/username_rule.mjs (confusables.txt 16.0.0, tools/names/username-twins.txt, tools/names/translit-ar.txt) — do not edit by hand';
const MSG = {
  empty: 'Choose a username',
  char: 'A username can only have small letters a-z, numbers 0-9 and dots — remove “⁦%s⁩”',
  short: `A username has at least ${MIN} characters`,
  long: `A username has at most ${MAX} characters`,
  dot: 'A dot cannot start or end a username or follow another dot',
  letter: 'A username needs at least one letter',
  reserved: '“⁦%s⁩” is kept for Drugbox — choose another username',
  taken: '“⁦%s⁩” is taken — choose another username',
  held: '“⁦%s⁩” was just given up by a member and is kept for them for 30 days — choose another username',
  rate: 'You changed your username too often today — try again tomorrow',
  slow: 'Too many tries — wait a minute and try again',
  signin: 'Sign in to choose a username',
};
const sqlStr = (s) => (/[^\x20-\x7e]/.test(s) ? "U&'" + [...s.replace(/'/g, "''")].map((x) => (x.charCodeAt(0) < 128 && x !== '\\' ? x : '\\' + (x.codePointAt(0) > 0xFFFF ? '+' + x.codePointAt(0).toString(16).toUpperCase().padStart(6, '0') : hx(x.codePointAt(0))))).join('') : "'" + s.replace(/'/g, "''")) + "'";
const low = (x) => `translate(${x}, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')`;
const sqlRe = (re) => re.replace(/\$(\d)/g, '\\$1');
const anyCase = (w) => w.replace(/\\.|[A-Za-z]/g, (x) => (x.length === 2 ? x : `[${x.toLowerCase()}${x.toUpperCase()}]`));
const TITLE_HEAD = `^(?:(?:${TITLES.map(anyCase).join('|')})(?:[./]*[,،]? |[./]+)|[^ ./,،]{1,5}(?:[./]+[^ ./,،]{1,5})*[./]+(?:[,،]? )?)+`;
// «a letter follows» (a title alone is a name): a normalised name holds letters, spaces and . - ’ ( ) , / ، only
const AFTER = `(?=.*[^ .\\-’(),/،])`;
const ROWS = (m) => [...m].map(([k, v]) => k + '=' + v).join('\u0001');

function sqlRegion() {
  const fold1 = KEY1.map(([a, b]) => [a, b]);
  return `-- >>> ${HEAD}
-- the key (profiles.username_key, unique): small letters, no dots, the look-alikes of confusables.txt and username-twins.txt written as one
-- (${[...KEY].map(([a, b]) => a + ' → ' + b).join(', ')})
create or replace function public.username_key(u text)
returns text language sql immutable parallel safe as $$
  select ${'replace('.repeat(KEYN.length)}translate(replace(translate(coalesce(u, ''), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '.', ''), '${fold1.map(([a]) => a).join('')}', '${fold1.map(([, b]) => b).join('')}')${KEYN.map(([a, b]) => `, '${a}', '${b}')`).join('')}
$$;
-- '' when a username may be used, else the first reason: empty, char, short, long, dot, letter, reserved (capitals are written small first)
create or replace function public.username_problem(u text)
returns text language sql immutable parallel safe as $$
  select case
    when coalesce(u, '') = '' then 'empty'
    when translate(u, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') ~ '[^a-z0-9.]' then 'char'
    when char_length(u) < ${MIN} then 'short'
    when char_length(u) > ${MAX} then 'long'
    when u ~ '^[.]|[.]$|[.][.]' then 'dot'
    when translate(u, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') !~ '[a-z]' then 'letter'
    when public.username_key(u) in (${RES_WHOLE_K.map((k) => `'${k}'`).join(', ')})
      or strpos(public.username_key(u), '${RES_BRAND_K}') > 0
      or exists (select 1 from unnest(string_to_array(translate(u, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '.')) p(w)
                  where public.username_key(regexp_replace(p.w, '[0-9]', '', 'g')) in (${RES_PART_K.map((k) => `'${k}'`).join(', ')})) then 'reserved'
    else '' end
$$;
-- the sentence for a reason (the app says the same — web/src/username.js — and translates it); u is the username as typed
create or replace function public.username_message(u text, p text)
returns text language sql immutable parallel safe as $$
  select case p
${Object.keys(MSG).map((k) => `    when '${k}' then ${MSG[k].includes('%s') ? `format(${sqlStr(MSG[k])}, ${k === 'char' ? `substring(${low('u')} from '[^a-z0-9.]')` : low('u')})` : sqlStr(MSG[k])}`).join('\n')}
  end
$$;
-- the n-th username to try for a base: the base itself (n = 1, when it has ${MIN} characters), else base.n — the number padded with 0 so the
-- username has ${MIN} characters («ali» → ali.1, «om» → om.01), the base cut so it has at most ${MAX}
create or replace function public.username_candidate(b text, n int)
returns text language sql immutable parallel safe as $$
  select case when n <= 1 and char_length(b) >= ${MIN} then left(b, ${MAX})
              else rtrim(left(b, ${MAX - 1} - char_length(d)), '.') || '.' || d end
    from (select case when char_length(b) + 1 + char_length(n::text) < ${MIN} then lpad(greatest(n, 1)::text, ${MIN - 1} - char_length(b), '0') else greatest(n, 1)::text end as d) z
$$;
-- made from a name: the tables (private: read by username_base as the writer)
create table if not exists private.username_ascii (ch text primary key, s text not null);
delete from private.username_ascii;
insert into private.username_ascii (ch, s) select split_part(e, '=', 1), split_part(e, '=', 2) from unnest(string_to_array(${sqlStr(ROWS(ASCII))}, ${sqlStr('\u0001')})) e;
create table if not exists private.username_translit (ar text primary key, s text not null);
delete from private.username_translit;
insert into private.username_translit (ar, s) select split_part(e, '=', 1), split_part(e, '=', 2) from unnest(string_to_array(${sqlStr(ROWS(TABLE))}, ${sqlStr('\u0001')})) e;
-- one Arabic word in Latin letters: the table, «ال…» → el…, «عبد…» → abd…, else letter by letter
create or replace function public.username_ar_word(w text)
returns text language plpgsql stable parallel safe set search_path = '' as $$
declare k text := translate(w, ${sqlStr(AR_FOLD_FROM)}, ${sqlStr(AR_FOLD_TO)}); t text; x text;
begin
  if k = '' then return ''; end if;
  select s into t from private.username_translit where ar = k; if t is not null then return t; end if;
  if char_length(k) > 2 and left(k, 2) = 'ال' then return 'el' || public.username_ar_word(substr(w, 3)); end if;
  if char_length(k) > 3 and left(k, 3) = 'عبد' then return 'abd' || public.username_ar_word(substr(w, 4)); end if;
  x := w;
${AR_PRE.map(([a, b]) => `  x := regexp_replace(x, ${sqlStr(a)}, ${sqlStr(b)});`).join('\n')}
  x := translate(x, ${sqlStr(Object.keys(LETTERS).filter((y) => LETTERS[y].length === 1).join(''))}, ${sqlStr(Object.keys(LETTERS).filter((y) => LETTERS[y].length === 1).map((y) => LETTERS[y]).join(''))});
  x := translate(x, ${sqlStr(Object.keys(LETTERS).filter((y) => LETTERS[y] === '').join(''))}, '');
${AR_POST.map(([a, b]) => `  x := regexp_replace(x, ${sqlStr(a)}, ${sqlStr(sqlRe(b))}, 'g');`).join('\n')}
  x := translate(x, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz');
${Object.keys(DIGRAPH).map((d) => `  x := replace(x, '${d}', '${DIGRAPH[d]}');`).join('\n')}
  return regexp_replace(x, '[^a-z]', '', 'g');
end $$;
-- the username a name gives (before the database numbers it): see tools/names/username_rule.mjs
create or replace function public.username_base(name text)
returns text language plpgsql stable parallel safe set search_path = '' as $$
declare n text; w text; words text[] := '{}'; toks text[] := '{}'; tok text; open boolean := false; s text; r text; i int;
begin
  n := regexp_replace(public.person_name_norm(name), ${sqlStr(TITLE_HEAD + AFTER)}, '');
  n := regexp_replace(regexp_replace(n, '[(][^()]*(?:[)]|$)', ' ', 'g'), '[()]', ' ', 'g');
  foreach w in array regexp_split_to_array(n, '[ .,،/]+') loop
    w := replace(replace(replace(w, '-', ''), '’', ''), '''', '');
    if w = '' then continue; end if;
    if open then toks[cardinality(toks)] := toks[cardinality(toks)] || ' ' || w; else toks := toks || w; end if;
    open := translate(w, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = any (array[${PART_LAT.map((x) => `'${x}'`).join(', ')}]) or translate(w, ${sqlStr(AR_FOLD_FROM)}, ${sqlStr(AR_FOLD_TO)}) = any (array[${[...new Set(PART_AR)].map((x) => sqlStr(x)).join(', ')}]);
  end loop;
  foreach tok in array toks loop
    if tok ~ ('^[' || ${sqlStr('؀-ۿݐ-ݿ ')} || ']+$') then
      select t.s into s from private.username_translit t where t.ar = translate(replace(tok, ' ', ''), ${sqlStr(AR_FOLD_FROM)}, ${sqlStr(AR_FOLD_TO)});
      if s is null then
        select string_agg(public.username_ar_word(p.x), '' order by p.o) into s from unnest(string_to_array(tok, ' ')) with ordinality p(x, o);
      end if;
    else
      select string_agg(case when c.x ~ '[a-z]' then c.x else coalesce((select a.s from private.username_ascii a where a.ch = c.x),
                                                                 case when c.x ~ ${sqlStr('[؀-ۿݐ-ݿ]')} then public.username_ar_word(c.x) else '' end) end, '' order by c.o)
        into s from unnest(regexp_split_to_array(translate(replace(tok, ' ', ''), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '')) with ordinality c(x, o);
    end if;
    s := regexp_replace(coalesce(s, ''), '[^a-z0-9]', '', 'g');
    -- a word Drugbox keeps (moderator, support, drugbox…) is left out: «Dr. Maha Moderator» → maha
    if s <> '' and public.username_key(regexp_replace(s, '[0-9]', '', 'g')) <> all (array[${RES_PART_K.map((k) => `'${k}'`).join(', ')}])
       and strpos(public.username_key(s), '${RES_BRAND_K}') = 0 then words := words || s; end if;
  end loop;
  if cardinality(words) = 0 then return 'member'; end if;
  r := case when cardinality(words) = 1 then words[1] else words[1] || '.' || words[cardinality(words)] end;
  r := rtrim(left(r, ${MAX}), '.');
  if r !~ '[a-z]' or public.username_problem(r) = 'reserved' then return 'member'; end if;
  return r;
end $$;
-- <<< generated`;
}

const jsKey = () => `function usKey(u) { return String(u == null ? '' : u).replace(/[A-Z]/g, function (c) { return c.toLowerCase(); }).replace(/\\./g, '')${KEY1.length ? `.replace(/[${KEY1.map(([a]) => a).join('')}]/g, function (c) { return US_K1[c]; })` : ''}${KEYN.map(([a, b]) => `.split('${a}').join('${b}')`).join('')}; }`;
function layerRegion() {
  return `/* >>> ${HEAD} */
  var US_MIN = ${MIN}, US_MAX = ${MAX};
  var US_K1 = ${JSON.stringify(Object.fromEntries(KEY1))};
  var US_RES_WHOLE = ${JSON.stringify(RES_WHOLE_K)}, US_RES_PART = ${JSON.stringify(RES_PART_K)}, US_RES_BRAND = '${RES_BRAND_K}';
  var US_MSG = ${JSON.stringify(MSG).replace(/[⁦⁩]/g, (c) => '\\u' + hx(c.codePointAt(0)))};
  ${jsKey()}
  function usProblem(u) {
    u = String(u == null ? '' : u); var l = u.replace(/[A-Z]/g, function (c) { return c.toLowerCase(); }), n = Array.from(u).length;
    if (!u) return 'empty'; if (/[^a-z0-9.]/.test(l)) return 'char'; if (n < US_MIN) return 'short'; if (n > US_MAX) return 'long';
    if (/^[.]|[.]$|[.][.]/.test(u)) return 'dot'; if (!/[a-z]/.test(l)) return 'letter';
    var k = usKey(u);
    if (US_RES_WHOLE.indexOf(k) >= 0 || k.indexOf(US_RES_BRAND) >= 0 || l.split('.').some(function (w) { return US_RES_PART.indexOf(usKey(w.replace(/[0-9]/g, ''))) >= 0; })) return 'reserved';
    return '';
  }
  function usMessage(u, p) { var m = US_MSG[p] || '', l = String(u == null ? '' : u).replace(/[A-Z]/g, function (c) { return c.toLowerCase(); }); return m.replace('%s', function () { return p === 'char' ? (l.match(/[^a-z0-9.]/u) || [''])[0] : l; }); }
  function usReservedWord(w) { var k = usKey(w); return US_RES_PART.indexOf(usKey(w.replace(/[0-9]/g, ''))) >= 0 || k.indexOf(US_RES_BRAND) >= 0; }
  function usCandidate(b, n) { var d = String(Math.max(n, 1)); if (n <= 1 && b.length >= US_MIN) return b.slice(0, US_MAX); if (b.length + 1 + d.length < US_MIN) d = d.padStart(US_MIN - 1 - b.length, '0');
    return b.slice(0, US_MAX - 1 - d.length).replace(/[.]+$/, '') + '.' + d; }
/* <<< generated */`;
}
function adapterRegion() {
  const arF = JSON.stringify(AR_FOLD), lets = JSON.stringify(LETTERS);
  return `/* >>> ${HEAD} */
  var US_ASCII = new Map(${JSON.stringify([...ASCII])});
  var US_TR = new Map(${JSON.stringify([...TABLE])});
  var US_AR_FOLD = ${arF}, US_LETTERS = ${lets}, US_DIGRAPH = ${JSON.stringify(DIGRAPH)};
  var US_AR_PRE = [${AR_PRE.map(([a, b]) => `[/${a}/u, ${JSON.stringify(b)}]`).join(', ')}], US_AR_POST = [${AR_POST.map(([a, b]) => `[/${a}/gu, ${JSON.stringify(b)}]`).join(', ')}];
  var US_PART_LAT = ${JSON.stringify(PART_LAT)}, US_PART_AR = ${JSON.stringify([...new Set(PART_AR)])};
  var US_TITLE = new RegExp(${JSON.stringify(TITLE_HEAD + AFTER)}, 'u');
  function usArFold(w) { return Array.from(w, function (x) { var f = US_AR_FOLD[x]; return f == null ? x : f; }).join(''); }
  function usArWord(w) {
    var k = usArFold(w), t; if (!k) return '';
    if (US_TR.has(k)) return US_TR.get(k);
    if (Array.from(k).length > 2 && k.slice(0, 2) === 'ال') return 'el' + usArWord(Array.from(w).slice(2).join(''));
    if (Array.from(k).length > 3 && k.slice(0, 3) === 'عبد') return 'abd' + usArWord(Array.from(w).slice(3).join(''));
    var x = US_AR_PRE.reduce(function (s, r) { return s.replace(r[0], r[1]); }, w);
    x = Array.from(x, function (c) { var l = US_LETTERS[c]; return l == null ? c : l; }).join('');
    x = US_AR_POST.reduce(function (s, r) { return s.replace(r[0], r[1]); }, x).replace(/[A-Z]/g, function (c) { return c.toLowerCase(); });
    Object.keys(US_DIGRAPH).forEach(function (d) { x = x.split(d).join(US_DIGRAPH[d]); });
    return x.replace(/[^a-z]/g, '');
  }
  function usBase(name) {
    var n = nmNorm(name).replace(US_TITLE, '').replace(/[(][^()]*(?:[)]|$)/gu, ' ').replace(/[()]/g, ' '), toks = [], open = false;
    n.split(/[ .,،/]+/).forEach(function (w) { w = w.replace(/[-’']/g, ''); if (!w) return;
      if (open) toks[toks.length - 1] += ' ' + w; else toks.push(w);
      open = US_PART_LAT.indexOf(w.replace(/[A-Z]/g, function (c) { return c.toLowerCase(); })) >= 0 || US_PART_AR.indexOf(usArFold(w)) >= 0; });
    var words = toks.map(function (tok) { var s;
      if (/^[\\u0600-\\u06FF\\u0750-\\u077F ]+$/.test(tok)) { var j = usArFold(tok.replace(/ /g, '')); s = US_TR.has(j) ? US_TR.get(j) : tok.split(' ').map(usArWord).join(''); }
      else s = Array.from(tok.replace(/ /g, '').replace(/[A-Z]/g, function (c) { return c.toLowerCase(); }), function (c) { return /[a-z]/.test(c) ? c : US_ASCII.has(c) ? US_ASCII.get(c) : /[\\u0600-\\u06FF\\u0750-\\u077F]/.test(c) ? usArWord(c) : ''; }).join('');
      return s.replace(/[^a-z0-9]/g, ''); }).filter(function (s) { return s && !window.dxUsername.reservedWord(s); });   /* «Dr. Maha Moderator» → maha */
    if (!words.length) return 'member';
    var r = (words.length === 1 ? words[0] : words[0] + '.' + words[words.length - 1]).slice(0, ${MAX}).replace(/[.]+$/, '');
    return !/[a-z]/.test(r) || window.dxUsername.problem(r) === 'reserved' ? 'member' : r;
  }
/* <<< generated username */`;
}

function region(file, start, end, body) {
  const src = fs.readFileSync(file, 'utf8'), a = src.indexOf(start), b = src.indexOf(end, a);
  if (a < 0 || b < a) throw new Error(`no generated region in ${path.relative(ROOT, file)}`);
  const nl = src.lastIndexOf('\n', a) + 1, close = b + end.length;
  return { old: src.slice(nl, close), put: () => fs.writeFileSync(file, src.slice(0, nl) + body + src.slice(close)) };
}
const want = [sqlRegion(), layerRegion(), adapterRegion()];
const R = [region(MIGRATION, '-- >>> generated by tools/names/username_rule.mjs', '-- <<< generated', want[0]),
  region(LAYER, '/* >>> generated by tools/names/username_rule.mjs', '/* <<< generated */', want[1]),
  region(ADAPTER, '/* >>> generated by tools/names/username_rule.mjs', '/* <<< generated username */', want[2])];
const FILES = [MIGRATION, LAYER, ADAPTER];

// the app's generated code, run here: the layer's and the adapter's regions (the adapter's needs the name rule's nmNorm and NM_TITLE)
function app() {
  const nameRegion = (() => { const s = fs.readFileSync(ADAPTER, 'utf8'), a = s.indexOf('/* >>> generated by tools/names/name_rule.mjs'), b = s.indexOf('/* <<< generated */', a);
    return s.slice(s.indexOf('\n', a) + 1, b); })();
  const body = (r) => r.old.split('\n').slice(1, -1).join('\n');
  // the layer in its own scope (as web/src/username.js is), the adapter's region next to the name rule's (as in the adapter)
  return new Function(`var window = { dxUsername: null };\n(function () {\n${body(R[1])}\nwindow.dxUsername = { key: usKey, problem: usProblem, message: usMessage, candidate: usCandidate, reservedWord: usReservedWord };\n})();\n${nameRegion}\n${body(R[2])}\nvar L = window.dxUsername; return { key: L.key, problem: L.problem, message: L.message, candidate: L.candidate, base: usBase };`)();
}
const lines = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8').split('\n').filter((l) => l && !l.startsWith('#'));
const esc = (t) => String(t).replace(/\\/g, '\\\\').replace(/\t/g, '\\t').replace(/\n/g, '\\n').replace(/\r/g, '\\r');

if (process.argv.includes('--write')) {
  R.forEach((r) => r.put()); console.log(`written: ${FILES.map((f) => path.relative(ROOT, f)).join(', ')} (${KEY.size} look-alikes in the key, ${ASCII.size} letters in Latin, ${TABLE.size} Arabic words)`);
} else if (process.argv.includes('--check') || process.argv.includes('--expect')) {
  const bad = R.map((r, i) => (r.old !== want[i] ? FILES[i] : null)).filter(Boolean);
  if (bad.length) { console.error('the generated username rule differs from tools/names/username_rule.mjs in: ' + bad.map((f) => path.relative(ROOT, f)).join(', ') + ' — run node tools/names/username_rule.mjs --write'); process.exit(1); }
  if (process.argv.includes('--check')) { console.log('username rule: the three generated regions are current'); process.exit(0); }
  const F = app(), fails = [], expect = (what, got, exp) => { if (got !== exp && fails.length < 40) fails.push(`${what}: got ${JSON.stringify(got)} want ${JSON.stringify(exp)}`); };
  // the definition, checked on the app's code before anything is printed
  for (const [a, b] of [['ahmed.ali', 'ahmedali'], ['Ahmed.Ali', 'ahmedali'], ['ahmed.ali', 'ahrned.ali'], ['ahmed.ali', 'ahmed.a1i'], ['ahmed.ali', 'ahmed.aIi'], ['ahmed.ali', 'ahmecl.ali'],
    ['wael.saad', 'vvael.saad'], ['omar.ali', '0mar.ali'], ['ali.hassan', 'all.hassan'], ['salma.ali', 'salrna.ali']]) expect('one key ' + a + ' / ' + b, F.key(a), F.key(b));
  for (const [a, b] of [['ahmed.ali', 'ahmed.aly'], ['mona.ali', 'mona.ali2'], ['sara.adel', 'sara.adam']]) expect('two keys ' + a + ' / ' + b, F.key(a) === F.key(b), false);
  for (const [u, p] of [['', 'empty'], ['ahmed', ''], ['ahmed.ali', ''], ['Ahmed.Ali', ''], ['ali', 'short'], ['a'.repeat(31), 'long'], ['a'.repeat(30), ''], ['.ahmed', 'dot'], ['ahmed.', 'dot'], ['ahmed..ali', 'dot'],
    ['12345', 'letter'], ['ahmed_ali', 'char'], ['ahmed ali', 'char'], ['أحمد.علي', 'char'], ['ahmed@ali', 'char'], ['drugbox', 'reserved'], ['drug.box', 'reserved'], ['drugb0x.eg', 'reserved'],
    ['ahmed.drugbox', 'reserved'], ['admin', 'reserved'], ['admin2', 'reserved'], ['ahmed.support', 'reserved'], ['help.desk', 'reserved'], ['support', 'reserved'], ['news', 'short'], ['newss', ''],
    ['payments', 'reserved'], ['jobs.eg', ''], ['marketplace', 'reserved'], ['adrnin', 'reserved'], ['member', ''], ['member.2', ''], ['ali.1', ''], ['om.01', '']]) expect('problem ' + JSON.stringify(u), F.problem(u), p);
  for (const [b, n, c] of [['ahmed.ali', 1, 'ahmed.ali'], ['ahmed.ali', 2, 'ahmed.ali.2'], ['ali', 1, 'ali.1'], ['ali', 7, 'ali.7'], ['om', 1, 'om.01'], ['om', 12, 'om.12'], ['a', 1, 'a.001'], ['a'.repeat(30), 2, 'a'.repeat(28) + '.2']])
    expect('candidate ' + b + ' ' + n, F.candidate(b, n), c);
  for (const [nm, b] of [['محمد أحمد', 'mohamed.ahmed'], ['عبد الرحمن', 'abdelrahman'], ['José Ali', 'jose.ali'], ['Dr. Haytham Dweedar', 'haytham.dweedar'], ['د. محمد أحمد علي', 'mohamed.ali'],
    ['عبد الله السيد', 'abdallah.elsayed'], ['عبدالرحمن محمد', 'abdelrahman.mohamed'], ['أبو بكر الصديق', 'abobakr.elseddik'], ['Abd El Rahman Ali', 'abdelrahman.ali'], ['El Sayed Mohamed', 'elsayed.mohamed'],
    ['Ahmed Ali (MBA)', 'ahmed.ali'], ['Søren Łukasz', 'soren.lukasz'], ['Strauß', 'strauss'], ['Мария Иванова', 'mariya.ivanova'], ['Νίκος Παπαδόπουλος', 'nikos.papadopoylos'], ['إبراهيم حسن', 'ibrahim.hassan'],
    ['ابراهيم حسن', 'ibrahim.hassan'], ['فاطمه الزهراء', 'fatma.elzahraa'], ['Mo’men Abd El-Raouf', 'momen.abdelraouf'], ['Admin Support', 'member'], ['Drugbox', 'member'], ['Dr. Maha Moderator', 'maha'], ['Drugbox Finance', 'finance'], ['Ahmed Admin Ali', 'ahmed.ali'], ['هيثم دويدار', 'haytham.dweedar'],
    ['Om Kalthoum Ibrahim', 'omkalthoum.ibrahim'], ['Ali', 'ali'], ['مي', 'mai'], ['حسن شحاتة', 'hassan.shehata'], ['Dr. Ahmed El-Sayed', 'ahmed.elsayed'], ['Eng. Omar Khaled', 'omar.khaled']])
    expect('made from ' + nm, F.base(nm), b);
  for (const nm of lines('tests/names/username_names.txt')) { const b = F.base(nm); expect('a base is a username or short ' + nm, ['', 'short'].includes(F.problem(b)) && /^[a-z0-9.]+$/.test(b), true); }
  if (fails.length) { console.error('the generated username rule does not follow its definition:\n' + fails.join('\n')); process.exit(1); }
  const out = [];
  for (const nm of lines('tests/names/username_names.txt')) out.push(['n', esc(nm), F.base(nm), '', ''].join('\t'));
  for (const u of lines('tests/names/username_strings.txt')) { const p = F.problem(u); out.push(['u', esc(u), F.key(u), p, esc(p ? F.message(u, p) : '')].join('\t')); }
  for (const b of ['ali', 'om', 'a', 'ahmed.ali', 'x'.repeat(30), 'mohamed.abdelrahman.elsayed']) for (const n of [1, 2, 9, 10, 123]) out.push(['c', b, F.candidate(b, n), String(n), ''].join('\t'));
  process.stdout.write(out.join('\n') + '\n');
} else console.log('usage: node tools/names/username_rule.mjs --write | --check | --expect');
