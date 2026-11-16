// Put the formal-Arabic texts in place: every Arabic text of the files that equals a listed old text is replaced by its new one,
// at its exact place. Checked before anything is written: the same {placeholders}, the same ${…} expressions, the same tags, no
// quote that would end the string early; and the scripts still parse afterwards.
//   node apply.mjs <ids.json> <tm.tsv>[,<tm2.tsv>…] <file>...        (--dry: check only)
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2).filter(a => a !== '--dry');
const dry = process.argv.includes('--dry');
const ids = JSON.parse(fs.readFileSync(args[0], 'utf8'));
const tm = new Map(), byCtx = new Map();
for (const f of args[1].split(',')) {
  for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
    if (!line.trim() || line.startsWith('#')) continue;
    const SEP = ' ⇒ ';                                              // id ⇒ new text (a tab is taken too)
    const i = line.indexOf(SEP) >= 0 ? line.indexOf(SEP) : line.indexOf('\t');
    if (i < 0) throw new Error(`${f}: no separator in «${line.slice(0, 60)}»`);
    let id = line.slice(0, i).trim(); const neu = line.slice(i + (line.indexOf(SEP) >= 0 ? SEP.length : 1));
    let ctx = null;                                                  // id@@words: only where these words stand just before the text
    if (id.includes('@@')) { ctx = id.slice(id.indexOf('@@') + 2); id = id.slice(0, id.indexOf('@@')); }
    if (!(id in ids)) throw new Error(`${f}: unknown id ${id}`);
    if (ctx) { if (!byCtx.has(ids[id])) byCtx.set(ids[id], []); byCtx.get(ids[id]).push({ ctx, neu, used: 0 }); continue; }
    if (tm.has(ids[id]) && tm.get(ids[id]) !== neu) throw new Error(`${f}: ${id} given twice, differently`);
    tm.set(ids[id], neu);
  }
}
const files = args.slice(2);
const tmp = path.join(here, '.apply-units.json');
execFileSync('node', [path.join(here, 'extract.mjs'), tmp, ...files], { stdio: ['ignore', 'ignore', 'inherit'] });
const units = JSON.parse(fs.readFileSync(tmp, 'utf8'));

const multiset = (s, re) => (s.match(re) || []).slice().sort().join('\u0001');
const problems = [];
function check(u, neu) {
  const old = u.text, where = `${path.basename(u.file)}:${u.line}`;
  const say = m => problems.push(`${where} ${m}\n   old: ${old.slice(0, 160)}\n   new: ${neu.slice(0, 160)}`);
  if (multiset(old, /\{[a-zA-Z_][a-zA-Z0-9_]*\}/g) !== multiset(neu, /\{[a-zA-Z_][a-zA-Z0-9_]*\}/g)) say('placeholders differ');
  if (multiset(old, /\$\{/g) !== multiset(neu, /\$\{/g)) say('${…} count differs');
  if (u.kind === 'tpl' || u.kind === 'seg') {
    const ex = s => { const out = []; let i = 0; while ((i = s.indexOf('${', i)) >= 0) { let d = 1, j = i + 2; while (j < s.length && d) { if (s[j] === '{') d++; else if (s[j] === '}') d--; j++; } out.push(s.slice(i, j)); i = j; } return out.sort().join('\u0001'); };
    if (ex(old) !== ex(neu)) say('${…} expressions differ');
    if (/`/.test(neu)) say('a backtick in the new text');
  }
  if (multiset(old, /<\/?[a-zA-Z][^<>]*>/g) !== multiset(neu, /<\/?[a-zA-Z][^<>]*>/g)) say('tags differ');
  if (u.q === "'" && /(^|[^\\])'/.test(neu)) say("an unescaped ' in the new text");
  if (u.q === '"' && /(^|[^\\])"/.test(neu)) say('an unescaped " in the new text');
  if (/\n/.test(neu) !== /\n/.test(old)) say('line breaks differ');
  if (/\\(?![n'"\\`$u{}])/.test(neu) && !/\\(?![n'"\\`$u{}])/.test(old)) say('a new backslash');
  if (u.kind === 'html' && /[<>]/.test(neu)) say('< or > in an HTML text');
}
const byFile = new Map();
let n = 0;
const srcOf = new Map();
for (const u of units) {
  let neu = tm.has(u.text) ? tm.get(u.text) : null;
  if (byCtx.has(u.text)) {
    if (!srcOf.has(u.file)) srcOf.set(u.file, fs.readFileSync(u.file, 'utf8'));
    const before = srcOf.get(u.file).slice(Math.max(0, u.start - 90), u.start);
    const hit = byCtx.get(u.text).find(c => before.includes(c.ctx));
    if (hit) { neu = hit.neu; hit.used++; }
  }
  if (neu === null || neu === u.text) continue;
  check(u, neu);
  if (!byFile.has(u.file)) byFile.set(u.file, []);
  byFile.get(u.file).push({ start: u.start, end: u.end, neu });
  n++;
}
for (const [t, list] of byCtx) for (const c of list) if (!c.used) problems.push(`the context «${c.ctx}» was not found before «${t.slice(0, 40)}»`);
const used = new Set(units.map(u => u.text));
const unused = [...tm.keys()].filter(t => !used.has(t));
if (problems.length) { console.error(problems.join('\n')); console.error(`${problems.length} problem(s): nothing written`); process.exit(1); }
for (const [file, reps] of byFile) {
  let s = fs.readFileSync(file, 'utf8');
  reps.sort((a, b) => b.start - a.start);
  for (const r of reps) s = s.slice(0, r.start) + r.neu + s.slice(r.end);
  if (!dry) fs.writeFileSync(file, s);
}
if (!dry) {                                                          // the scripts still parse (extract.mjs fails loudly when one does not)
  execFileSync('node', [path.join(here, 'extract.mjs'), tmp, ...files], { stdio: ['ignore', 'ignore', 'inherit'] });
}
console.log(`${dry ? 'would replace' : 'replaced'} ${n} text(s) in ${byFile.size} file(s); ${tm.size} in the list, ${unused.length} not found in the files`);
if (unused.length) console.log('not found:\n  ' + unused.slice(0, 12).map(t => t.slice(0, 80)).join('\n  '));
