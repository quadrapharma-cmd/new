// Look for words in a source's text, with the page they are on: node tools/find-in-source.mjs <source-id> <regex> [context]
// Uses the texts tools/verify-sources.mjs keeps in dist/texts/ (run it first).
import fs from 'node:fs';
import path from 'node:path';
import { ROOT } from './load.mjs';

const [id, pattern, ctx = '90'] = process.argv.slice(2);
if (!id || !pattern) { console.error('usage: node tools/find-in-source.mjs <source-id> <regex> [context chars]'); process.exit(2); }
const f = path.join(ROOT, 'dist', 'texts', `${id}.json`);
if (!fs.existsSync(f)) { console.error(`no text for ${id}: run tools/verify-sources.mjs first`); process.exit(1); }
const { pages } = JSON.parse(fs.readFileSync(f, 'utf8'));
const re = new RegExp(pattern, 'gi');
let n = 0;
pages.forEach((p, i) => {
  const flat = p.replace(/\s+/g, ' ');
  for (const m of flat.matchAll(re)) {
    if (++n > 40) return;
    const a = Math.max(0, m.index - +ctx), b = Math.min(flat.length, m.index + m[0].length + +ctx);
    console.log(`p.${i + 1}: …${flat.slice(a, b)}…`);
  }
});
if (!n) console.log('not found');
