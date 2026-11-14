// Builds the page of «الفحص الأول للملف» (Part 2): the program reads a dossier's files in the browser — scans included — and shows
// what each document is, where it goes in the CTD, and what reading them side by side finds.
//   node prep/build.mjs → dist/prep-artifact.html   the page without a document shell (the Artifact tool adds it)
//                         dist/prep-site/           the same page with a shell (index.html) and every file it loads, at the paths it
//                                                   is published under: run it locally, check it (tools/check-published.mjs prep)
//                         dist/prep-files.json      published path → file, for the Artifact tool's `files`
// Needs dist/knowledge.json (npm run build) and vendor/ocr (node tools/ocr/fetch.mjs). The scan reader's models, its WebAssembly
// runtime and its language data are written as gzip in base64 text (<name>.gz.b64.txt): the artifact host serves text, and holds a
// file of 16 MB at most (Tesseract's «best» English model would be 17 MB that way: the page carries the «fast» one, which reads
// English as well on our measures — tools/ocr/fetch.mjs).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';
import { escapeControls } from '../workbench/build.mjs';
import { TYPES } from './doctype.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const DIST = path.join(ROOT, 'dist');
const OCR = path.join(ROOT, 'vendor', 'ocr');
const LIMIT = 16_000_000;
const FONTS = 'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+Arabic:wght@400;500;600&family=Readex+Pro:wght@500;600&display=swap';

// The ONNX model's own list of the characters it reads (its metadata «character»): read from the protobuf without a library.
export function onnxCharacters(bytes) {
  let p = 0;
  const varint = () => { let v = 0, s = 0, b; do { b = bytes[p++]; v += (b & 0x7f) * 2 ** s; s += 7; } while (b & 0x80); return v; };
  const text = (a, b) => new TextDecoder().decode(bytes.subarray(a, b));
  while (p < bytes.length) {
    const tag = varint(), field = Math.floor(tag / 8), wire = tag & 7;
    if (wire === 0) { varint(); continue; }
    if (wire === 1) { p += 8; continue; }
    if (wire === 5) { p += 4; continue; }
    if (wire !== 2) throw new Error(`the model's file is not an ONNX model (wire type ${wire})`);
    const len = varint(), start = p;
    p += len;
    if (field !== 14) continue;                                  // metadata_props: {key: 1, value: 2}
    let q = start, key = null, value = null;
    const v2 = () => { let v = 0, s = 0, b; do { b = bytes[q++]; v += (b & 0x7f) * 2 ** s; s += 7; } while (b & 0x80); return v; };
    while (q < start + len) {
      const t = v2(), n = v2();
      if (t >> 3 === 1) key = text(q, q + n); else if (t >> 3 === 2) value = text(q, q + n);
      q += n;
    }
    if (key === 'character') return value.split(/\r?\n/).filter((c, i, a) => i < a.length - 1 || c !== '');
  }
  throw new Error('the model keeps no list of its characters');
}

const packed = bytes => zlib.gzipSync(bytes, { level: 9 }).toString('base64');

// The scan reader's files, at the paths the page loads them from (prep/ocr.js, base «ocr/»): {published path: text or bytes}
export function ocrFiles() {
  if (!fs.existsSync(path.join(OCR, 'paddle', 'arabic_PP-OCRv5_rec_mobile.onnx'))) throw new Error('vendor/ocr is missing: run node tools/ocr/fetch.mjs');
  const read = rel => fs.readFileSync(path.join(OCR, rel));
  const model = read('paddle/arabic_PP-OCRv5_rec_mobile.onnx');
  const files = {
    'ocr/tess/tesseract.min.js': read('tess/tesseract.min.js').toString('utf8'),
    'ocr/tess/worker.min.js': read('tess/worker.min.js').toString('utf8'),
    'ocr/tess/worker.boot.js': fs.readFileSync(path.join(HERE, 'ocr-worker.boot.js'), 'utf8'),
    'ocr/tess/tesseract-core-simd-lstm.wasm.js': read('tess/tesseract-core-simd-lstm.wasm.js').toString('utf8'),
    'ocr/tess/tesseract-core-lstm.wasm.js': read('tess/tesseract-core-lstm.wasm.js').toString('utf8'),
    'ocr/tess/ara.traineddata.gz.b64.txt': packed(read('tessdata/ara.traineddata')),
    'ocr/tess/eng.traineddata.gz.b64.txt': packed(read('tessdata/eng.fast.traineddata')),
    'ocr/ort/ort.wasm.bundle.min.js': read('ort/ort.wasm.bundle.min.mjs').toString('utf8'),
    'ocr/ort/ort-wasm-simd-threaded.wasm.gz.b64.txt': packed(read('ort/ort-wasm-simd-threaded.wasm')),
    'ocr/paddle/arabic_PP-OCRv5_rec_mobile.onnx.gz.b64.txt': packed(model),
    'ocr/paddle/characters.json': JSON.stringify(onnxCharacters(new Uint8Array(model))),
    'ocr/LICENSE.tesseract.js.txt': read('tess/LICENSE.tesseract.js.md').toString('utf8'),
    'ocr/LICENSE.tesseract.js-core.txt': read('tess/LICENSE.tesseract.js-core.txt').toString('utf8'),
    'ocr/LICENSE.tessdata.txt': read('tessdata/LICENSE').toString('utf8'),
    'ocr/LICENSE.onnxruntime.txt': read('ort/LICENSE.onnxruntime.txt').toString('utf8'),
    'ocr/LICENSE.PaddleOCR.txt': read('paddle/LICENSE-PaddleOCR').toString('utf8'),
    'ocr/LICENSE.RapidOCR.txt': read('paddle/LICENSE-RapidOCR').toString('utf8'),
  };
  for (const [name, body] of Object.entries(files)) {
    if (Buffer.byteLength(body) > LIMIT) throw new Error(`${name}: ${Buffer.byteLength(body)} bytes, over the 16 MB a published file may hold`);
    if (typeof body === 'string' && /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]/.test(body)) files[name] = escapeControls(body);
  }
  return files;
}

// The library's records the page names (each kind's places in the CTD and its document type): their CTD number and title only.
function places() {
  const k = JSON.parse(fs.readFileSync(path.join(DIST, 'knowledge.json'), 'utf8'));
  const all = new Map();
  const walk = v => { if (Array.isArray(v)) v.forEach(walk); else if (v && typeof v === 'object') { if (typeof v.id === 'string') all.set(v.id, v); Object.values(v).forEach(walk); } };
  walk(k);
  const out = {};
  for (const t of TYPES) for (const id of [...t.places, t.doctype].filter(Boolean)) {
    const r = all.get(id);
    if (!r) throw new Error(`${t.type}: ${id} is not a record of the library`);
    out[id] = { ctd: r.ctd || null, title: r.title };
  }
  return out;
}

export async function buildPrep() {
  if (!fs.existsSync(path.join(DIST, 'knowledge.json'))) throw new Error('dist/knowledge.json is missing: run npm run build first');
  const bundle = await esbuild.build({
    entryPoints: [path.join(HERE, 'page.js')], bundle: true, format: 'iife', minify: true, target: ['es2020'],
    write: false, legalComments: 'none', logLevel: 'error', define: { 'import.meta.url': '""' },
  });
  const js = escapeControls(bundle.outputFiles[0].text).replace(/<\/script/gi, '<\\/script');
  const css = fs.readFileSync(path.join(HERE, 'style.css'), 'utf8');
  const { BODY, TITLE } = await import('./page-body.mjs');
  const page = [
    `<title>${TITLE}</title>`,
    '<meta name="claude:viewport-fit-sides" content="cover">',
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    `<link rel="stylesheet" href="${FONTS}">`,
    `<style>${css}</style>`,
    BODY,
    `<script type="application/json" id="places">${JSON.stringify(places()).replace(/</g, '\\u003c')}</script>`,
    `<script>${js}</script>`,
  ].join('\n');
  const site = path.join(DIST, 'prep-site');
  fs.rmSync(site, { recursive: true, force: true });
  const files = { ...ocrFiles(), 'pdf.worker.min.js': escapeControls(fs.readFileSync(path.join(ROOT, 'node_modules', 'pdfjs-dist', 'legacy', 'build', 'pdf.worker.min.mjs'), 'utf8')) };
  const map = {};
  for (const [name, body] of Object.entries(files)) {
    const file = path.join(site, name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, body);
    map[name] = path.relative(path.resolve(ROOT, '..', '..'), file);
  }
  fs.writeFileSync(path.join(DIST, 'prep-artifact.html'), page);
  fs.writeFileSync(path.join(site, 'index.html'), `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>${page}</body></html>`);
  fs.writeFileSync(path.join(DIST, 'prep-files.json'), JSON.stringify(map, null, 1));
  return { page: path.join(DIST, 'prep-artifact.html'), bytes: Buffer.byteLength(page), files: Object.keys(map).length,
           total: Object.values(files).reduce((n, b) => n + Buffer.byteLength(b), 0) };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const r = await buildPrep();
  console.log(`${path.relative(process.cwd(), r.page)}: ${(r.bytes / 1048576).toFixed(2)} MB; ${r.files} files beside it, ${(r.total / 1048576).toFixed(1)} MB (dist/prep-site, dist/prep-files.json)`);
}
