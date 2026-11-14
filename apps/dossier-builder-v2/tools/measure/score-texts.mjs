// Scores the texts one OCR program read (tools/measure/ocr_libs.py → .cache/measure/texts-<engine>.json) with the facts of the
// made-up pages, in the same table as tools/measure/readers.mjs, and keeps the rows in .cache/measure/readers-<engine>.json.
//   node tools/measure/score-texts.mjs <engine> [<engine>…]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { score } from './score.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const MEASURE = path.join(ROOT, '.cache', 'measure');
const VARIANTS = ['clean', 'skew3', 'rot90', 'faint'];

export function scoreTexts(engine) {
  const truth = JSON.parse(fs.readFileSync(path.join(MEASURE, 'pages', 'truth.json'), 'utf8'));
  const texts = JSON.parse(fs.readFileSync(path.join(MEASURE, `texts-${engine}.json`), 'utf8'));
  return Object.entries(texts).map(([file, t]) => {
    const page = file.replace(/-(clean|skew3|rot90|faint)\.png$/, '');
    const variant = file.slice(page.length + 1, -4);
    return { reader: engine, page, variant, seconds: t.seconds, error: t.error || null, ...score(truth[page], t.text) };
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  for (const engine of process.argv.slice(2)) {
    const rows = scoreTexts(engine);
    fs.writeFileSync(path.join(MEASURE, `readers-${engine}.json`), JSON.stringify(rows, null, 1));
    console.log(`\n${engine}`);
    for (const page of [...new Set(rows.map(r => r.page))]) {
      const cells = VARIANTS.map(v => { const r = rows.find(x => x.page === page && x.variant === v); return r ? `${String(r.pct).padStart(3)}% ${String(r.seconds).padStart(5)}s` : '—'; });
      console.log(`  ${page.padEnd(14)} ${cells.join('   ')}`);
    }
    const avg = Math.round(rows.reduce((s, r) => s + r.pct, 0) / rows.length);
    console.log(`  ${'average'.padEnd(14)} ${avg}% of the facts · ${(rows.reduce((s, r) => s + r.seconds, 0) / rows.length).toFixed(1)} s a page`);
  }
}
