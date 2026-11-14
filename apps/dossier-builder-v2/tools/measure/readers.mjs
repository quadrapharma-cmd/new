// Measures the text readers on the made-up scanned pages (tools/measure/pages.mjs): for every page and reader, the share of
// the page's facts the reading holds (tools/measure/score.mjs) and the seconds it took. Run it on an idle machine: the times
// are part of the measure.
//   node tools/measure/readers.mjs [reader…]      readers: tesseract-fast, tesseract-best, tesseract-best-osd
// Writes .cache/measure/readers.json and prints a table. Claude is measured where it runs for the user — inside claude.ai,
// on the user's own account — by the measuring page (tools/measure/claude-page), never by the session that wrote the pages.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { score } from './score.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const PAGES = path.join(ROOT, '.cache', 'measure', 'pages');
const BEST = path.join(ROOT, 'vendor', 'ocr', 'tessdata');
const SYSTEM = '/usr/share/tesseract-ocr/5/tessdata';

// A tessdata folder with the «best» models and the system's orientation model (osd), for the reading that turns the page.
function bestWithOsd() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'tessdata-'));
  for (const f of ['ara.traineddata', 'eng.traineddata']) fs.copyFileSync(path.join(BEST, f), path.join(dir, f));
  if (fs.existsSync(path.join(SYSTEM, 'osd.traineddata'))) fs.copyFileSync(path.join(SYSTEM, 'osd.traineddata'), path.join(dir, 'osd.traineddata'));
  return dir;
}

export const READERS = {
  'tesseract-fast': { what: 'Tesseract 5 with the fast models a Tesseract installer brings', args: f => [f, 'stdout', '-l', 'ara+eng'] },
  'tesseract-best': { what: 'Tesseract 5 with the «best» models the program carries', args: f => [f, 'stdout', '--tessdata-dir', BEST, '-l', 'ara+eng'] },
  'tesseract-best-osd': { what: 'the same, turning the page first (orientation detection)', args: (f, osd) => [f, 'stdout', '--tessdata-dir', osd, '-l', 'ara+eng', '--psm', '1'] },
};

export function measure(names = Object.keys(READERS)) {
  const truth = JSON.parse(fs.readFileSync(path.join(PAGES, 'truth.json'), 'utf8'));
  const osd = bestWithOsd();
  const rows = [];
  for (const file of fs.readdirSync(PAGES).filter(f => f.endsWith('.png')).sort()) {
    const page = file.replace(/-(clean|skew3|rot90|faint)\.png$/, '');
    const variant = file.slice(page.length + 1, -4);
    for (const name of names) {
      const t0 = process.hrtime.bigint();
      let text = '', error = null;
      try { text = execFileSync('tesseract', READERS[name].args(path.join(PAGES, file), osd), { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, OMP_THREAD_LIMIT: '1' } }); }
      catch (e) { error = String(e.stderr || e.message).split('\n')[0]; }
      const seconds = Number(process.hrtime.bigint() - t0) / 1e9;
      rows.push({ reader: name, page, variant, seconds: Math.round(seconds * 10) / 10, error, ...score(truth[page], text) });
    }
  }
  fs.rmSync(osd, { recursive: true, force: true });
  return rows;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const names = process.argv.slice(2).filter(a => READERS[a]);
  const rows = measure(names.length ? names : undefined);
  fs.writeFileSync(path.join(ROOT, '.cache', 'measure', 'readers.json'), JSON.stringify(rows, null, 1));
  const variants = ['clean', 'skew3', 'rot90', 'faint'];
  for (const reader of [...new Set(rows.map(r => r.reader))]) {
    console.log(`\n${reader} — ${READERS[reader].what}`);
    for (const page of [...new Set(rows.map(r => r.page))]) {
      const cells = variants.map(v => { const r = rows.find(x => x.reader === reader && x.page === page && x.variant === v); return r ? `${String(r.pct).padStart(3)}% ${String(r.seconds).padStart(5)}s` : '—'; });
      console.log(`  ${page.padEnd(14)} ${cells.join('   ')}`);
    }
    const mine = rows.filter(r => r.reader === reader);
    const avg = Math.round(mine.reduce((s, r) => s + r.pct, 0) / mine.length);
    console.log(`  ${'average'.padEnd(14)} ${avg}% of the facts · ${(mine.reduce((s, r) => s + r.seconds, 0) / mine.length).toFixed(1)} s a page`);
  }
}
