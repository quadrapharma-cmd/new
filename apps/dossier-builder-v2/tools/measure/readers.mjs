// Measures the text readers on the made-up scanned pages (tools/measure/pages.mjs): for every page and reader, the share of
// the page's facts the reading holds (tools/measure/score.mjs) and the seconds it took. Run it on an idle machine: the times
// are part of the measure.
//   node tools/measure/readers.mjs [reader…]      readers: tesseract-fast, tesseract-best, tesseract-best-osd, qwen3vl
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

// The same instruction Claude gets on the measuring page (tools/measure/claude-page.mjs).
const ASK = 'The image is a scanned page of a pharmaceutical regulatory document. It may be rotated, skewed or faint. Read it in its correct orientation and transcribe every word on it exactly as written, in reading order: Arabic as Arabic, English as English, and every digit as it is drawn (keep Arabic-Indic digits as they are). Include headings, table cells and the text of stamps. Output only the transcription.';
// A vision-language model on this machine through llama.cpp's multimodal command line (LLAMA_MTMD_CLI), the model and its
// image part named by QWEN3VL_MODEL and QWEN3VL_MMPROJ.
const qwen = f => ['-m', process.env.QWEN3VL_MODEL, '--mmproj', process.env.QWEN3VL_MMPROJ, '--image', f, '-p', ASK,
                   '--temp', '0', '-n', '1200', '-t', String(Math.max(1, os.cpus().length)), '--no-warmup'];

export const READERS = {
  'tesseract-fast': { what: 'Tesseract 5 with the fast models a Tesseract installer brings', args: f => [f, 'stdout', '-l', 'ara+eng'] },
  'tesseract-best': { what: 'Tesseract 5 with the «best» models the program carries', args: f => [f, 'stdout', '--tessdata-dir', BEST, '-l', 'ara+eng'] },
  'tesseract-best-osd': { what: 'the same, turning the page first (orientation detection)', args: (f, osd) => [f, 'stdout', '--tessdata-dir', osd, '-l', 'ara+eng', '--psm', '1'] },
  // fed the page at about 1.2 megapixels (pages-1mp), as claude.ai feeds Claude: the full scan does not fit the memory beside a build
  'qwen3vl': { what: 'Qwen3-VL (Apache-2.0) on this machine through llama.cpp, no internet', cmd: () => process.env.LLAMA_MTMD_CLI,
               args: f => qwen(f.replace(`${path.sep}pages${path.sep}`, `${path.sep}pages-1mp${path.sep}`)) },
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
      const cmd = READERS[name].cmd ? READERS[name].cmd() : 'tesseract';
      try { text = execFileSync(cmd, READERS[name].args(path.join(PAGES, file), osd), { encoding: 'utf8', maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, OMP_THREAD_LIMIT: READERS[name].cmd ? '' : '1' } }); }
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
