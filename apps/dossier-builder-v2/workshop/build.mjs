// Builds the desktop workshop (Part 2): a folder the person opens from the computer (index.html in Chrome or Edge, file://), with
// everything beside it — no server, nothing to install:
//   node workshop/build.mjs [--zip]   → dist/workshop/                     index.html, app/ (the page, the library's data, the scan
//                                                                           reader's files), programs/ (the Word, PDF, photo and design
//                                                                           programs, where they are built here), library/ (Part 1, the desktop library)
//                                       dist/Dossier-Builder-Workshop.zip  (with --zip) the folder in one file, to hand over
// A page opened from the disk cannot fetch the files beside it, start a worker from a file or import a module from one: the page is
// one classic script, pdf.js runs on its thread, and every other file is a script that hands its content over when it loads
// (workshop/desktop-assets.js). Needs dist/knowledge.json and dist/library (npm run build) and vendor/ocr (node tools/ocr/fetch.mjs).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';
import { onnxCharacters } from '../prep/build.mjs';
import { PROGRAMS, programPage } from './programs.js';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const DIST = path.join(ROOT, 'dist');
const OUT = path.join(DIST, 'workshop');
const OCR = path.join(ROOT, 'vendor', 'ocr');
const CRAFT = path.join(ROOT, 'vendor', 'craft');
const FOLDER = 'Dossier Builder - الورشة';

const asset = (name, value) => `__dbAsset(${JSON.stringify(name)},${JSON.stringify(value)});\n`;
const packed = bytes => zlib.gzipSync(bytes, { level: 9 }).toString('base64');

function ocrFiles() {
  const read = rel => fs.readFileSync(path.join(OCR, rel));
  if (!fs.existsSync(path.join(OCR, 'paddle', 'arabic_PP-OCRv5_rec_mobile.onnx'))) throw new Error('vendor/ocr is missing: run node tools/ocr/fetch.mjs');
  const model = read('paddle/arabic_PP-OCRv5_rec_mobile.onnx');
  return {
    'tesseract.js': read('tess/tesseract.min.js').toString('utf8'),
    'worker.js': asset('tess/worker.min.js', read('tess/worker.min.js').toString('utf8')),
    'core-simd.js': asset('tess/core-simd', read('tess/tesseract-core-simd-lstm.wasm.js').toString('utf8')),
    'core.js': asset('tess/core', read('tess/tesseract-core-lstm.wasm.js').toString('utf8')),
    'ara.js': asset('tess/ara', packed(read('tessdata/ara.traineddata'))),
    'eng.js': asset('tess/eng', packed(read('tessdata/eng.fast.traineddata'))),
    'ort.js': asset('ort/ort.wasm.bundle.min.js', read('ort/ort.wasm.bundle.min.mjs').toString('utf8')),
    'ort-wasm.js': asset('ort/ort-wasm-simd-threaded.wasm', packed(read('ort/ort-wasm-simd-threaded.wasm'))),
    'paddle.js': asset('paddle/arabic_PP-OCRv5_rec_mobile.onnx', packed(model)),
    'chars.js': asset('paddle/characters.json', onnxCharacters(new Uint8Array(model))),
    'licenses/tesseract.js.txt': read('tess/LICENSE.tesseract.js.md').toString('utf8'),
    'licenses/tesseract.js-core.txt': read('tess/LICENSE.tesseract.js-core.txt').toString('utf8'),
    'licenses/tessdata.txt': read('tessdata/LICENSE').toString('utf8'),
    'licenses/onnxruntime.txt': read('ort/LICENSE.onnxruntime.txt').toString('utf8'),
    'licenses/PaddleOCR.txt': read('paddle/LICENSE-PaddleOCR').toString('utf8'),
    'licenses/RapidOCR.txt': read('paddle/LICENSE-RapidOCR').toString('utf8'),
  };
}

// The real programs built on this machine (tools/craft/build.mjs → vendor/craft/<app>-web): each one's glue as one module (its
// snippets bundled in) and its WebAssembly as gzip in base64, beside its own page with the relay (workshop/programs.js).
export async function programFiles(out, craft = CRAFT) {
  const built = [];
  for (const [app, p] of Object.entries(PROGRAMS)) {
    const dir = path.join(craft, `${app}-web`);
    if (!fs.existsSync(path.join(dir, 'index.html'))) continue;
    const glueFile = fs.readdirSync(dir).find(f => new RegExp(`^${app}-web-[0-9a-f]+\\.js$`).test(f));
    const wasmFile = fs.readdirSync(dir).find(f => new RegExp(`^${app}-web-[0-9a-f]+_bg\\.wasm$`).test(f));
    if (!glueFile || !wasmFile) throw new Error(`${app}: the built program has no glue or WebAssembly in ${dir}`);
    const glue = (await esbuild.build({ entryPoints: [path.join(dir, glueFile)], bundle: true, format: 'esm', write: false, logLevel: 'error', minify: true })).outputFiles[0].text;
    const target = path.join(out, 'programs', app);
    fs.mkdirSync(target, { recursive: true });
    fs.writeFileSync(path.join(target, 'glue.js'), asset(`${app}/glue`, glue));
    fs.writeFileSync(path.join(target, 'wasm.js'), asset(`${app}/wasm`, packed(fs.readFileSync(path.join(dir, wasmFile)))));
    if (fs.existsSync(path.join(dir, 'licenses'))) copyDir(path.join(dir, 'licenses'), path.join(target, 'licenses'));
    fs.writeFileSync(path.join(out, 'programs', `${app}.html`), programPage(app, { canvas: p.canvas, title: p.ar, host: p.host, loading: p.loading }));
    built.push(app);
  }
  return built;
}

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const e of fs.readdirSync(from, { withFileTypes: true })) {
    const a = path.join(from, e.name), b = path.join(to, e.name);
    if (e.isDirectory()) copyDir(a, b); else fs.copyFileSync(a, b);
  }
}

export async function buildWorkshop({ zip = false } = {}) {
  const knowledge = path.join(DIST, 'knowledge.json');
  if (!fs.existsSync(knowledge)) throw new Error('dist/knowledge.json is missing: run npm run build first');
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(path.join(OUT, 'app', 'ocr'), { recursive: true });
  const bundle = await esbuild.build({
    entryPoints: [path.join(HERE, 'page.js')], bundle: true, format: 'iife', minify: true, target: ['es2021'], write: false,
    legalComments: 'none', logLevel: 'error', define: { 'import.meta.url': '"file:///app/app.js"' },
  });
  fs.writeFileSync(path.join(OUT, 'app', 'app.js'), bundle.outputFiles[0].text);
  const programs = await programFiles(OUT);
  fs.writeFileSync(path.join(OUT, 'app', 'knowledge.js'), `window.DB_PROGRAMS=${JSON.stringify(programs)};\nwindow.DB_KNOWLEDGE=${fs.readFileSync(knowledge, 'utf8')};\n`);
  for (const [name, body] of Object.entries(ocrFiles())) {
    const file = path.join(OUT, 'app', 'ocr', name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, body);
  }
  const { TITLE, BODY } = await import('./body.mjs');
  const css = fs.readFileSync(path.join(HERE, 'style.css'), 'utf8');
  fs.writeFileSync(path.join(OUT, 'index.html'), `<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${TITLE}</title><style>${css}</style></head>
<body>${BODY}
<script src="app/knowledge.js"></script>
<script src="app/app.js"></script>
</body></html>
`);
  // Part 1, the library, beside it (its own desktop build)
  const lib = path.join(DIST, 'library');
  if (fs.existsSync(path.join(lib, 'index.html'))) copyDir(lib, path.join(OUT, 'library'));
  fs.writeFileSync(path.join(OUT, 'اقرأني.txt'), '\ufeff' + [
    'Dossier Builder — الورشة (تحضير الملف)',
    '',
    '1. فك الملف المضغوط في أي مكان على جهازك.',
    '2. افتح index.html بـ Chrome أو Edge (دبل كليك، أو اسحبه على نافذة المتصفح).',
    '3. علشان Claude يشتغل: «الإعدادات» ← حط مفتاح API من console.anthropic.com ← «اختبر المفتاح».',
    '   من غير مفتاح كل حاجة بتشتغل ما عدا شغل Claude (الممسوح بيقراه قارئ المسح على الجهاز).',
    '4. «ملف جديد» ← الدولة (مصر، الخليج، أوروبا، أمريكا، أو دولة تانية) ونوع الطلب ← ارمي ملفات المستحضر ← «شغّل لوحدك».',
    '',
    'ملفاتك بتتحفظ في المتصفح على جهازك بس. «احفظ نسخة» بيطلّع الملف كله في ملف واحد تقدر تفتحه تاني.',
    'مكتبة المعرفة (الجزء الأول) في فولدر library، وبتتفتح من زرار «المكتبة».',
  ].join('\r\n'));
  let zipPath = null;
  if (zip) {
    zipPath = path.join(DIST, 'Dossier-Builder-Workshop.zip');
    fs.rmSync(zipPath, { force: true });
    const stage = path.join(DIST, '.zip-stage');
    fs.rmSync(stage, { recursive: true, force: true });
    fs.mkdirSync(stage, { recursive: true });
    fs.renameSync(OUT, path.join(stage, FOLDER));
    try { execFileSync('zip', ['-q', '-r', '-X', zipPath, FOLDER], { cwd: stage }); }
    finally { fs.renameSync(path.join(stage, FOLDER), OUT); fs.rmSync(stage, { recursive: true, force: true }); }
  }
  const size = dir => fs.readdirSync(dir, { withFileTypes: true }).reduce((n, e) => n + (e.isDirectory() ? size(path.join(dir, e.name)) : fs.statSync(path.join(dir, e.name)).size), 0);
  return { dir: OUT, bytes: size(OUT), zip: zipPath, zipBytes: zipPath ? fs.statSync(zipPath).size : 0, programs };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const r = await buildWorkshop({ zip: process.argv.includes('--zip') });
  console.log(`dist/workshop: ${(r.bytes / 1048576).toFixed(1)} MB, programs: ${r.programs.join(', ') || 'none built here'}${r.zip ? `; ${path.relative(process.cwd(), r.zip)}: ${(r.zipBytes / 1048576).toFixed(1)} MB` : ''}`);
}
