/* PdfCraft in the browser edition: its command-line program built for WebAssembly with a file system of its own (WASI;
   tools/pdfcraft/build-wasm.sh), run in the engine's thread over an in-memory folder — the same steps, the same report, the same
   files the desktop's pdfcraft-cli takes and gives (engine/dossier_engine/pdfcraft.py, Job.run). The folder is lent by the WASI shim
   of @bjorn3/browser_wasi_shim (MIT OR Apache-2.0, assets/pdfcraft/wasi/). The program is fetched with the runtime's other files,
   kept on the device, compiled once; each run is a fresh instance, so one document's run never sees another's.
   self.DB_PDFCRAFT = { load(base, fetch), ready, error, run(stepsJson, files: Map | {name: Uint8Array}) →
                        {code, stdout, stderr, files: [[name, Uint8Array], …]} } */
(function () {
  'use strict';
  const st = { module: null, shim: null, ready: false, error: null, loading: null };
  const gunzip = async bytes => new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());

  /* the program: gzip in base64 text, in parts (a file of the page holds 16 MB at most), kept on the device by its SHA-256 */
  let dbp = null;
  const idb = () => dbp || (dbp = new Promise(res => {
    try { const q = indexedDB.open('db-pdfcraft', 1); q.onupgradeneeded = () => { try { q.result.createObjectStore('files'); } catch (e) {} };
      q.onsuccess = () => res(q.result); q.onerror = q.onblocked = () => res(null); } catch (e) { res(null); }
  }));
  const idbDo = (mode, f) => idb().then(db => db ? new Promise(res => {
    try { const q = f(db.transaction('files', mode).objectStore('files')); q.onsuccess = () => res(q.result); q.onerror = () => res(undefined); }
    catch (e) { res(undefined); } }) : undefined);
  function fromB64(text) { const bin = atob(text.replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }
  async function program(base, realFetch) {
    const meta = await (await realFetch(base + 'assets/pdfcraft/pdfcraft-cli.json')).json();
    const key = 'pdfcraft-cli@' + meta.sha256;
    const kept = await idbDo('readonly', s => s.get(key));
    if (kept && kept.byteLength === meta.bytes) return new Uint8Array(kept);
    let text = '';
    for (let k = 1; k <= meta.parts; k++) {
      const r = await realFetch(base + `assets/pdfcraft/pdfcraft-cli.wasm.gz.b64.${k}.txt`);
      if (!r.ok) throw new Error(`PdfCraft part ${k}: HTTP ${r.status}`);
      text += await r.text();
    }
    const raw = await gunzip(fromB64(text));
    if (raw.byteLength !== meta.bytes) throw new Error('PdfCraft arrived damaged');
    idbDo('readonly', s => s.getAllKeys()).then(keys => (keys || []).forEach(k => { if (k !== key) idbDo('readwrite', s => s.delete(k)); }));
    idbDo('readwrite', s => s.put(raw.buffer.slice(0), key));       // for the next opening; not waited for
    return raw;
  }

  function load(base, realFetch) {                                  // started with the engine; the engine uses PdfCraft once it is ready
    if (!st.loading) st.loading = (async () => {
      try {
        if (typeof DecompressionStream !== 'function') throw new Error('this browser cannot unpack the PDF engine');
        const [shim, raw] = await Promise.all([import(base + 'assets/pdfcraft/wasi/index.js'), program(base, realFetch || fetch)]);
        st.module = await WebAssembly.compile(raw);
        st.shim = shim;
        const foreign = WebAssembly.Module.imports(st.module).filter(i => i.module !== 'wasi_snapshot_preview1');
        st.stubs = {};                                               // anything else it imports is never reached on this path: said if it is
        for (const i of foreign) (st.stubs[i.module] = st.stubs[i.module] || {})[i.name] = () => { throw new Error(`PdfCraft called ${i.module}.${i.name}`); };
        st.ready = true;
      } catch (e) { st.error = String(e && e.message || e); console.warn('PdfCraft (browser)', e); }
    })();
    return st.loading;
  }

  function concat(chunks) { let n = 0; for (const c of chunks) n += c.length; const out = new Uint8Array(n); let k = 0; for (const c of chunks) { out.set(c, k); k += c.length; } return out; }

  function run(stepsJson, files) {
    if (!st.ready) throw new Error('PdfCraft is not loaded in this browser' + (st.error ? ': ' + st.error : ''));
    const { WASI, File, Directory, OpenFile, ConsoleStdout, PreopenDirectory } = st.shim;
    const root = new Map();
    const put = (path, data) => {
      const parts = String(path).split('/').filter(Boolean); let dir = root;
      for (const p of parts.slice(0, -1)) { if (!dir.has(p)) dir.set(p, new Directory(new Map())); dir = dir.get(p).contents; }
      dir.set(parts[parts.length - 1], new File(data));
    };
    const entries = files instanceof Map ? [...files.entries()] : Object.entries(files || {});
    for (const [name, data] of entries) put(name, data);
    put('.steps.json', new TextEncoder().encode(stepsJson));
    const out = [], err = [];
    const fds = [new OpenFile(new File([])), new ConsoleStdout(b => out.push(b.slice())), new ConsoleStdout(b => err.push(b.slice())),
                 new PreopenDirectory('/', root)];
    const wasi = new WASI(['pdfcraft-cli', 'run', '--script', '/.steps.json', '--report'], ['HOME=/', 'PDFCRAFT_SYSTEM_FONTS=0'], fds, { debug: false });
    const inst = new WebAssembly.Instance(st.module, Object.assign({}, st.stubs, { wasi_snapshot_preview1: wasi.wasiImport }));
    let code;
    try { code = wasi.start(inst); } catch (e) { return { code: 101, stdout: concat(out), stderr: new TextEncoder().encode(String(e && e.message || e)), files: [] }; }
    const back = {};
    const walk = (dir, prefix) => { for (const [name, node] of dir) { if (node instanceof Directory) walk(node.contents, prefix + name + '/'); else if (node instanceof File && name !== '.steps.json') back[prefix + name] = node.data; } };
    walk(root, '');
    return { code, stdout: concat(out), stderr: concat(err), files: Object.entries(back) };          // [[name, bytes], …]
  }

  self.DB_PDFCRAFT = { load, run, get ready() { return st.ready; }, get error() { return st.error; } };
})();
