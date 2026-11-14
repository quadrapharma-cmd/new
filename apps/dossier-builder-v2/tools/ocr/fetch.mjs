// The text readers the program carries, fetched at fixed releases and checked (SHA-256 for the models, npm's integrity for
// the packages) into vendor/ocr/ (not committed). Every licence here lets a closed commercial program ship the file unchanged
// (Apache-2.0, MIT, Zlib); each licence text is written beside its files. Files already in place and matching are kept.
//
//   tessdata/  Tesseract's accurate («best») Arabic and English models, tessdata_best 4.1.0, and the English «fast» one for the
//              browser (English reads the same with either on our measures; «best» Arabic: 3.1 % of the characters wrong on a
//              made-up registration notice scanned at 200 dpi, against 14.7 % with the «fast» Arabic model).
//   paddle/    PaddleOCR's Arabic recognition model (PP-OCRv5 mobile, the ONNX conversion of RapidOCR v3.10.0): the second
//              reader for the words Tesseract is unsure of, the Arabic-Indic digits first. Its characters are in its metadata.
//   tess/      tesseract.js 7.0.0 and the Tesseract 5 cores of tesseract.js-core 6.1.2 (the reader in the browser).
//   ort/       onnxruntime-web 1.31.1 (the second reader's runtime in the browser).
//   img/       UTIF.js 3.1.0 and pako's inflate 2.1.0 (the pages of a TIFF scan).
// The same pins and checksums as the old program's tools/ocr/fetch.py and web/ocr_assets.py (13/11/2026).
//
//   node tools/ocr/fetch.mjs [--out DIR]
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const BEST = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/4.1.0/';
const FAST = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/';
const RAPID = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv5/rec/';

export const MODELS = {   // file under the output folder: [where from, SHA-256]
  'tessdata/ara.traineddata': [BEST + 'ara.traineddata', 'ab9d157d8e38ca00e7e39c7d5363a5239e053f5b0dbdb3167dde9d8124335896'],
  'tessdata/eng.traineddata': [BEST + 'eng.traineddata', '8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba'],
  'tessdata/eng.fast.traineddata': [FAST + 'eng.traineddata', '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'],
  'tessdata/LICENSE': [BEST + 'LICENSE', 'a6cba85bc92e0cff7a450b1d873c0eaa2e9fc96bf472df0247a26bec77bf3ff9'],
  'paddle/arabic_PP-OCRv5_rec_mobile.onnx': [RAPID + 'arabic_PP-OCRv5_rec_mobile.onnx', 'c1192e632d0baa9146ae5b756a0e635e3dc63c1733737ebfd1629e87144e9295'],
  'paddle/LICENSE-PaddleOCR': ['https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/v3.0.0/LICENSE', '3840c5c0c61c294264d2dd77b8777be6ddd90121ef4e0e64abcd22edea581d6e'],
  'paddle/LICENSE-RapidOCR': ['https://raw.githubusercontent.com/RapidAI/RapidOCR/v3.10.0/LICENSE', '3e0af25fdd06aa9586ae97adb00ea927ebe5a3805ac77d2d3a81ce5f55693333'],
};

export const NPM = {   // package: [version, integrity, {member in the tarball: file under the output folder}]
  'tesseract.js': ['7.0.0', 'sha512-exPBkd+z+wM1BuMkx/Bjv43OeLBxhL5kKWsz/9JY+DXcXdiBjiAch0V49QR3oAJqCaL5qURE0vx9Eo+G5YE7mA==',
    { 'package/dist/tesseract.min.js': 'tess/tesseract.min.js', 'package/dist/worker.min.js': 'tess/worker.min.js', 'package/LICENSE.md': 'tess/LICENSE.tesseract.js.md' }],
  'tesseract.js-core': ['6.1.2', 'sha512-pv4GjmramjdObhDyR1q85Td8X60Puu/lGQn7Kw2id05LLgHhAcWgnz6xSdMCSxBMWjQDmMyDXPTC2aqADdpiow==',
    { 'package/tesseract-core-simd-lstm.wasm.js': 'tess/tesseract-core-simd-lstm.wasm.js', 'package/tesseract-core-lstm.wasm.js': 'tess/tesseract-core-lstm.wasm.js',
      'package/LICENSE': 'tess/LICENSE.tesseract.js-core.txt' }],
  'utif': ['3.1.0', 'sha512-WEo4D/xOvFW53K5f5QTaTbbiORcm2/pCL9P6qmJnup+17eYfKaEhDeX9PeQkuyEoIxlbGklDuGl8xwuXYMrrXQ==',
    { 'package/UTIF.js': 'img/UTIF.js', 'package/LICENSE': 'img/LICENSE.utif.txt' }],
  'pako': ['2.1.0', 'sha512-w+eufiZ1WuJYgPXbV/PO3NCMEc3xqylkKHzp8bxp1uW4qaSNQUkwmLLEc3kKsfz8lpV1F8Ht3U1Cm+9Srog2ug==',
    { 'package/dist/pako_inflate.min.js': 'img/pako_inflate.min.js', 'package/LICENSE': 'img/LICENSE.pako.txt' }],
  'onnxruntime-web': ['1.31.1', 'sha512-5GeH+bWQ+HxM10z7erGlsWqryrwMbSvm/1tkIsKTT48g0fI19VXVVC435t4t7VsPdSQeS7NmuZPXrQ73k82URw==',
    { 'package/dist/ort.wasm.bundle.min.mjs': 'ort/ort.wasm.bundle.min.mjs', 'package/dist/ort-wasm-simd-threaded.wasm': 'ort/ort-wasm-simd-threaded.wasm' }],
};
const ORT_LICENCE = 'MIT License — Copyright (c) Microsoft Corporation. https://github.com/microsoft/onnxruntime/blob/main/LICENSE\n';

const sha256 = buf => crypto.createHash('sha256').update(buf).digest('hex');
const curl = (url, file) => execFileSync('curl', ['-sS', '-f', '-L', '-m', '600', '--retry', '2', '-o', file, url], { stdio: ['ignore', 'pipe', 'pipe'] });

export function fetchAll(out) {
  const done = [];
  for (const [rel, [url, want]] of Object.entries(MODELS)) {
    const dest = path.join(out, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (fs.existsSync(dest) && sha256(fs.readFileSync(dest)) === want) { done.push(`${rel}: in place`); continue; }
    const tmp = dest + '.part';
    curl(url, tmp);
    const got = sha256(fs.readFileSync(tmp));
    if (got !== want) { fs.rmSync(tmp, { force: true }); throw new Error(`${rel}: SHA-256 ${got} is not the pinned ${want} — not used`); }
    fs.renameSync(tmp, dest);
    done.push(`${rel}: fetched and checked`);
  }
  for (const [name, [version, integrity, members]] of Object.entries(NPM)) {
    const base = name.split('/').pop();
    const url = `https://registry.npmjs.org/${name}/-/${base}-${version}.tgz`;
    const tmpDir = fs.mkdtempSync(path.join(out, '.npm-'));
    try {
      const tgz = path.join(tmpDir, 'p.tgz');
      curl(url, tgz);
      const [algo, want] = integrity.split('-', 2);
      const got = crypto.createHash(algo).update(fs.readFileSync(tgz)).digest('base64');
      if (got !== want) throw new Error(`${name} ${version}: not the package npm signs — not used`);
      execFileSync('tar', ['-xzf', tgz, '-C', tmpDir]);
      for (const [member, rel] of Object.entries(members)) {
        const dest = path.join(out, rel);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.copyFileSync(path.join(tmpDir, member), dest);
      }
      done.push(`${name} ${version}: fetched and checked`);
    } finally { fs.rmSync(tmpDir, { recursive: true, force: true }); }
  }
  fs.writeFileSync(path.join(out, 'ort', 'LICENSE.onnxruntime.txt'), ORT_LICENCE);
  const lines = [...Object.entries(MODELS).map(([rel, [url, h]]) => `${rel}  ${url}  sha256 ${h}`),
                 ...Object.entries(NPM).map(([n, [v, i]]) => `${n}@${v}  ${i}`)];
  fs.writeFileSync(path.join(out, 'SOURCES.txt'), lines.join('\n') + '\n');
  return done;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const i = process.argv.indexOf('--out');
  const out = i > 0 ? path.resolve(process.argv[i + 1]) : path.join(ROOT, 'vendor', 'ocr');
  fs.mkdirSync(out, { recursive: true });
  try { for (const line of fetchAll(out)) console.log(line); }
  catch (e) { console.error(e.message); process.exit(1); }
}
