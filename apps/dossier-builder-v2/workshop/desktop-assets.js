// The scan reader's files for a page opened from the computer's disk (file://), where a page cannot fetch anything beside it: each
// file is a script beside the page (app/ocr/*.js, written by workshop/build.mjs) that hands its content to window.__dbAsset when it
// loads — text as it is, binaries as gzip in base64 — and Tesseract's worker is made from a blob that carries its own code, its
// core and its language data (a worker made from a blob may load only what it makes itself). The same five calls as prep/ocr.js's
// own (packed, script, module, json, tesseract), so the reader is the same reader.
const FILES = {
  'tess/tesseract.min.js': 'tesseract.js', 'tess/worker.min.js': 'worker.js', 'tess/core-simd': 'core-simd.js', 'tess/core': 'core.js',
  'tess/ara': 'ara.js', 'tess/eng': 'eng.js', 'ort/ort.wasm.bundle.min.js': 'ort.js', 'ort/ort-wasm-simd-threaded.wasm': 'ort-wasm.js',
  'paddle/arabic_PP-OCRv5_rec_mobile.onnx': 'paddle.js', 'paddle/characters.json': 'chars.js',
};
const store = (globalThis.__dbAssets = globalThis.__dbAssets || {});
globalThis.__dbAsset = (name, value) => { store[name] = value; };

const fromB64 = t => { const bin = atob(String(t).replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; };
const gunzip = async gz => new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
const simd = () => { try { return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11])); } catch { return false; } };

// Runs inside Tesseract's worker: its own blob URLs for its code and core, its language data answered from memory.
function workerBoot(SRC, LANG) {
  const realImport = self.importScripts.bind(self), realFetch = self.fetch.bind(self);
  const own = {};
  const urlOf = name => own[name] || (own[name] = URL.createObjectURL(new Blob([SRC[name]], { type: 'text/javascript' })));
  const bytes = t => { const bin = atob(t), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; };
  self.importScripts = function (...urls) {
    for (const u of urls) realImport(/tesseract-core/.test(u) ? urlOf('core') : /worker\.min\.js$/.test(u) ? urlOf('worker') : u);
  };
  self.fetch = function (url, opts) {
    const u = typeof url === 'string' ? url : (url && url.url) || '';
    const m = /([a-z]+)\.traineddata(\.gz)?$/.exec(u);
    if (m && LANG[m[1]]) return Promise.resolve(new Response(bytes(LANG[m[1]]), { status: 200, headers: { 'content-type': 'application/octet-stream' } }));
    return realFetch(url, opts);
  };
  realImport(urlOf('worker'));
}

export function desktopAssets(base = 'app/ocr/') {
  const loading = new Map();
  const load = file => {
    if (!loading.has(file)) {
      loading.set(file, new Promise((ok, no) => {
        const s = document.createElement('script');
        s.src = base + file;
        s.onload = ok;
        s.onerror = () => { loading.delete(file); no(Object.assign(new Error(`the scan reader's file ${file} is missing beside the page`), { why: 'missing' })); };
        document.head.appendChild(s);
      }));
    }
    return loading.get(file);
  };
  const get = async name => { if (!(name in store)) await load(FILES[name]); return store[name]; };
  let boot = null;
  return {
    packed: async rel => gunzip(fromB64(await get(rel))),
    script: rel => load(FILES[rel]),
    module: async rel => import(/* @vite-ignore */ URL.createObjectURL(new Blob([await get(rel)], { type: 'text/javascript' }))),
    json: rel => get(rel),
    async tesseract() {
      if (!boot) {
        const core = simd() ? 'tess/core-simd' : 'tess/core';
        const SRC = { worker: await get('tess/worker.min.js'), core: await get(core) };
        const LANG = { ara: await get('tess/ara'), eng: await get('tess/eng') };
        const text = `(${workerBoot.toString()})(${JSON.stringify(SRC)}, ${JSON.stringify(LANG)});`;
        boot = URL.createObjectURL(new Blob([text], { type: 'text/javascript' }));
      }
      return { workerPath: boot, corePath: 'desktop/tesseract-core-simd-lstm.wasm.js', langPath: 'desktop', gzip: true, workerBlobURL: false, cacheMethod: 'none' };
    },
  };
}
