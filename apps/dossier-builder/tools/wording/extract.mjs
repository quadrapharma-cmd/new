// Every Arabic text of the page's files, with its exact place: string literals, template literals (whole when small, by piece when
// they hold other Arabic strings inside), and the static HTML around the scripts.
//   node extract.mjs <out.json> <file>...
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const acorn = require('acorn');

const AR = /[؀-ۿ]/;
const out = [];

function walk(node, fn, parent) {
  if (!node || typeof node.type !== 'string') return;
  fn(node, parent);
  for (const k of Object.keys(node)) {
    if (k === 'type' || k === 'start' || k === 'end' || k === 'loc' || k === 'range') continue;
    const v = node[k];
    if (Array.isArray(v)) v.forEach(c => c && typeof c.type === 'string' && walk(c, fn, node));
    else if (v && typeof v.type === 'string') walk(v, fn, node);
  }
}

function hasArabicInside(node, src) {            // an Arabic string or template nested in this subtree
  let found = false;
  walk(node, n => {
    if (found) return;
    if (n.type === 'Literal' && typeof n.value === 'string' && AR.test(src.slice(n.start, n.end))) found = true;
    if (n.type === 'TemplateLiteral' && n.quasis.some(q => AR.test(src.slice(q.start, q.end)))) found = true;
  });
  return found;
}

// pieces of a template's text that are Arabic: the text between tags, and quoted attribute values inside tags
function segments(text, base) {
  const res = [];
  const re = /<[^<>]*>|[^<>]+/g;
  let m;
  while ((m = re.exec(text))) {
    const s = m[0];
    if (!AR.test(s)) continue;
    if (s[0] === '<') {                                             // a tag: its quoted values
      const q = /"([^"]*)"|'([^']*)'/g;
      let a;
      while ((a = q.exec(s))) { const v = a[1] !== undefined ? a[1] : a[2]; if (AR.test(v)) res.push({ start: base + m.index + a.index + 1, end: base + m.index + a.index + 1 + v.length }); }
    } else {
      const lead = s.length - s.trimStart().length, trail = s.length - s.trimEnd().length;
      res.push({ start: base + m.index + lead, end: base + m.index + s.length - trail });
    }
  }
  return res;
}

function script(src, offset, file, whole) {
  let ast;
  try { ast = acorn.parse(src, { ecmaVersion: 'latest', sourceType: 'script', allowReturnOutsideFunction: true }); }
  catch (e) { console.error(`${file}: script at ${offset} does not parse: ${e.message}`); process.exitCode = 1; return; }
  const inTemplate = new Set();
  walk(ast, (n, parent) => {
    if (n.type === 'Literal' && typeof n.value === 'string') {
      const raw = src.slice(n.start + 1, n.end - 1);
      if (AR.test(raw)) out.push({ file, kind: 'str', q: src[n.start], start: offset + n.start + 1, end: offset + n.end - 1 });
    } else if (n.type === 'TemplateLiteral') {
      if (!n.quasis.some(q => AR.test(src.slice(q.start, q.end)))) return;
      const nested = n.expressions.some(e => hasArabicInside(e, src));
      const body = src.slice(n.start + 1, n.end - 1);
      if (!nested && body.length <= 400 && !/<(div|section|table|tr|td|th|label|select|button|input|ul|li|header|p|h[1-6])\b/.test(body))
        out.push({ file, kind: 'tpl', q: '`', start: offset + n.start + 1, end: offset + n.end - 1 });
      else for (const q of n.quasis) {
        const t = src.slice(q.start, q.end);
        if (!AR.test(t)) continue;
        for (const s of segments(t, offset + q.start)) out.push({ file, kind: 'seg', q: '`', start: s.start, end: s.end });
      }
    }
  });
}

for (const file of process.argv.slice(3)) {
  const whole = fs.readFileSync(file, 'utf8');
  if (/\.html?$/.test(file)) {
    const re = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;
    let m, last = 0;
    const statics = [];
    while ((m = re.exec(whole))) {
      const off = m.index + m[0].indexOf('>') + 1;
      statics.push([last, m.index]);
      script(m[1], off, file, whole);
      last = re.lastIndex;
    }
    statics.push([last, whole.length]);
    for (const [a, b] of statics) {                                  // the HTML outside the scripts (style blocks left out)
      const part = whole.slice(a, b).replace(/<style[\s\S]*?<\/style>/g, s => ' '.repeat(s.length));
      for (const s of segments(part, a)) out.push({ file, kind: 'html', q: '', start: s.start, end: s.end });
    }
  } else script(whole, 0, file, whole);
}
const files = {};
for (const u of out) { files[u.file] = files[u.file] || fs.readFileSync(u.file, 'utf8'); u.text = files[u.file].slice(u.start, u.end); u.line = files[u.file].slice(0, u.start).split('\n').length; }
out.sort((a, b) => a.file < b.file ? -1 : a.file > b.file ? 1 : a.start - b.start);
fs.writeFileSync(process.argv[2], JSON.stringify(out, null, 0));
const by = {};
for (const u of out) { const k = path.basename(u.file) + ' ' + u.kind; by[k] = (by[k] || 0) + 1; }
console.log(JSON.stringify(by, null, 1));
console.log('units', out.length, 'unique', new Set(out.map(u => u.text)).size, 'chars', out.reduce((a, u) => a + u.text.length, 0));
