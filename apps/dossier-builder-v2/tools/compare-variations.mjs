// Part 1c helper: the guideline's own variation items (GL.CAPP.026 v6), and for each variation of EDA's tool the closest
// items — a list to read when deciding by hand which guideline item a variation is (the decision is written into the
// variation's record: guideline section, item and class). Prints only. Needs dist/texts/ (run verify-sources.mjs first).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadKnowledge, ROOT, KNOWLEDGE } from './load.mjs';
import { fold } from '../core/knowledge.js';

const STOP = new Set('a an the of for to in on or and by with from at as be is are its it this that which may new change changes changed'.split(' '));
const wordsOf = s => (fold(s).match(/[\p{L}\p{N}]+/gu) || []).filter(w => w.length > 2 && !STOP.has(w));
const stem = w => w.replace(/(isation|ization|ations?|ments?|ings?|ies|es|s|ed)$/, '');

// The guideline's items: each table row ends in its class (PAC-N, PAC-A, PAC-B, PAC-II).
export function guidelineItems(pages) {
  // The running header of every page, then the text before the first section (the guideline's introduction).
  let flat = pages.map(p => p.replace(/\s+/g, ' ')).join(' ')
    .replace(/(?:Egyptian Drug Authority\s*)?(?:Central Administration of Pharmaceutical Products\s*)?General Administration of Human Pharmaceuticals Registration Administration of Variations of Human Pharmaceuticals Registration \d+ Guideline Guideline GUIDELINES ON Human Pharmaceuticals Variations Code: EDREX: GL\.CAPP\.026 Version\/Year:\s*\S+/g, ' ');
  const start = flat.search(/3\.1\.1\.?\s*Change in Name/);
  if (start > 0) flat = flat.slice(start);
  const items = [];
  let section = '', heading = '';
  let last = 0;
  const re = /PAC-\s?(N|A|B|II)\b/g;
  let m;
  while ((m = re.exec(flat))) {
    const seg = flat.slice(last, m.index);
    last = m.index + m[0].length;
    const h = [...seg.matchAll(/(\d\.\d\.\d+(?:\.\d+)?)\.?\s*(.*?)\s*Conditions to be fulfilled\s*Requirements to be fulfilled\s*Procedure type/g)].pop();
    let item = seg;
    if (h) { section = h[1]; heading = h[2].trim(); item = seg.slice(h.index + h[0].length); }
    item = item.replace(/[\s\d,–-]+$/, '').trim();          // the numbers of its conditions and requirements
    items.push({ section, heading, item: item.replace(/Central Administration for Pharmaceutical Products\s*/g, '').trim(), pac: `PAC-${m[1]}` });
  }
  return items;
}

export function compare() {
  const data = loadKnowledge();
  const f = path.join(ROOT, 'dist', 'texts', 'eda-gl-capp-026-v6.json');
  if (!fs.existsSync(f)) throw new Error('no text for GL.CAPP.026 v6: run tools/verify-sources.mjs first');
  const items = guidelineItems(JSON.parse(fs.readFileSync(f, 'utf8')).pages);
  const df = new Map();
  const bags = items.map(it => new Set(wordsOf(`${it.heading} ${it.item}`).map(stem)));
  for (const b of bags) for (const w of b) df.set(w, (df.get(w) || 0) + 1);
  const idf = w => Math.log((items.length + 1) / ((df.get(w) || 0) + 0.5));
  const out = [];
  for (const v of data.variations.items) {
    const ws = [...new Set(wordsOf(v.title.en).map(stem))];
    const weight = ws.reduce((n, w) => n + idf(w), 0);
    let best = null;
    items.forEach((it, i) => {
      const hit = ws.filter(w => bags[i].has(w)).reduce((n, w) => n + idf(w), 0);
      const extra = [...bags[i]].filter(w => !ws.includes(w)).length;
      const score = hit / weight - Math.min(0.15, extra * 0.005);
      if (!best || score > best.score) best = { ...it, score: Math.round(score * 100) / 100 };
    });
    const verdict = best.score < 0.6 ? 'no-clear-match' : best.pac === v.pac ? 'same-class' : 'different-class';
    out.push({ id: v.id, tool: { title: v.title.en, pac: v.pac }, guideline: best, verdict });
  }
  const summary = out.reduce((a, x) => ((a[x.verdict] = (a[x.verdict] || 0) + 1), a), {});
  const report = { guideline_items: items.length, summary, variations: out };
  return report;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const r = compare();
  console.log(`guideline items ${r.guideline_items} · ${Object.entries(r.summary).map(([k, v]) => `${k} ${v}`).join(' · ')}`);
  for (const x of r.variations.filter(x => x.verdict !== 'same-class')) {
    console.log(`\n${x.id} [${x.verdict}] tool ${x.tool.pac}: ${x.tool.title}\n   guideline ${x.guideline.section} ${x.guideline.pac} (${x.guideline.score}): ${x.guideline.heading} — ${x.guideline.item.slice(-140)}`);
  }
}
