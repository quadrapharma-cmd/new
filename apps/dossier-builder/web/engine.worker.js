/* The Python engine (Pyodide) in its own thread, so the page never freezes while a document is read, checked or exported.
   boot.js starts this worker and sends it every fetch('/api/…') of the interface; the workspace lives here, on an
   IndexedDB-backed file system. Messages in: {type:'api', id, method, path, query, headers, body} · {type:'sync', id}.
   Messages out: {type:'say', ar, en, pct} while booting · {type:'ready'} · {type:'failed', message} ·
   {type:'api', id, meta, out} · {type:'sync', id, error}. */
'use strict';
const WHEELS = ['typing_extensions-4.12.2-py3-none-any.whl', 'sniffio-1.3.1-py3-none-any.whl', 'idna-3.10-py3-none-any.whl',
  'anyio-4.6.2.post1-py3-none-any.whl', 'starlette-0.46.2-py3-none-any.whl', 'fastapi-0.115.12-py3-none-any.whl',
  'python_multipart-0.0.20-py3-none-any.whl', 'pypdf-7.0.0-py3-none-any.whl', 'python_docx-1.2.0-py3-none-any.whl'];
const PKGS = ['sqlite3', 'hashlib', 'ssl', 'lxml', 'pyyaml', 'pydantic', 'jsonschema'];
const base = new URL('..', self.location.href).href;            // …/assets/engine.worker.js → the page's own folder
const realFetch = self.fetch.bind(self);
const B64 = /\/assets\/.+\.(wasm|zip|whl)$/;
const MIME = { wasm: 'application/wasm', zip: 'application/zip', whl: 'application/zip' };
/* assets.js (put in front of this file by the build): the runtime's files are kept on this device after the first download, and
   the page is told how far the loading is */
let told = 0, later = null;
const tellPage = st => { told = Date.now(); if (later) { clearTimeout(later); later = null; } self.postMessage({ type: 'load', loaded: st.loaded, total: st.total, net: st.net }); };
const runtime = DB_ASSETS(typeof DB_MANIFEST === 'object' && DB_MANIFEST ? DB_MANIFEST : {}, realFetch, st => {
  if (Date.now() - told > 120 || st.loaded >= st.total) tellPage(st);
  else if (!later) later = setTimeout(() => tellPage(st), 150);          // the last figure is always sent, even when nothing follows it
});
// binary assets are published as base64 text (the artifact host serves text, not archives); Pyodide fetches them through here
self.fetch = async function (input, init) {
  const url = typeof input === 'string' ? input : (input && input.url) || String(input);
  let u; try { u = new URL(url, base); } catch (e) { return realFetch(input, init); }
  if (u.origin !== self.location.origin || !B64.test(u.pathname)) return realFetch(input, init);
  let bytes;
  try { bytes = await runtime.get(u.href.startsWith(base) ? u.href.slice(base.length) : u.pathname, u.href + '.b64.txt'); }
  catch (e) { if (e && e.status) return new Response(null, { status: e.status }); throw e; }
  return new Response(bytes, { status: 200, headers: { 'content-type': MIME[u.pathname.split('.').pop()], 'content-length': String(bytes.length) } });
};

let pyodide = null, handle = null, syncTimer = null;
let bigSync = null;                                                 // bigfs.js (put in front of this file by the build): large files as Blobs
const syncfs = (populate) => (bigSync || (bigSync = DB_BIGFS(pyodide.FS.filesystems.IDBFS)))(pyodide.FS, populate);
/* what was written reaches the browser's storage a moment after the request, and never later than a second and a half into a long run
   of requests (a folder being read): closing the page in the middle loses nothing that was already taken */
let syncSince = 0;
function scheduleSync() {
  const now = Date.now(); if (!syncSince) syncSince = now;
  clearTimeout(syncTimer);
  syncTimer = setTimeout(() => { syncSince = 0; syncfs(false).then(() => saved(), e => { console.warn('sync', e); saved(e); }); }, now - syncSince > 1500 ? 0 : 250);
}
let unsaved = false;
function saved(e) {
  if (e) { unsaved = true; self.postMessage({ type: 'storage', error: String(e && (e.name || e.message) || e) }); }
  else if (unsaved) { unsaved = false; self.postMessage({ type: 'storage' }); }
}
const say = (ar, en, pct) => self.postMessage({ type: 'say', ar, en, pct });

const ready = (async () => {
  say('تحميل محرك الملفات…', 'Loading the dossier engine…', 4);
  importScripts(base + 'assets/pyodide/pyodide.js');
  pyodide = await loadPyodide({ indexURL: base + 'assets/pyodide/' });
  DB_SAFEFS(pyodide.FS);                                            // bigfs.js: a file too large for the page's memory is refused, the engine goes on
  say('تحميل المكتبات…', 'Loading libraries…', 45);
  await pyodide.loadPackage(PKGS, { messageCallback: () => {}, errorCallback: m => console.warn(m) });
  const site = pyodide.runPython("import sysconfig; sysconfig.get_paths()['purelib']");
  for (const w of WHEELS) {
    const buf = await (await fetch(base + 'assets/wheels/' + w)).arrayBuffer();
    pyodide.unpackArchive(buf, 'zip', { extractDir: site });
  }
  say('تحميل قواعد الهيئة…', 'Loading the EDA rule packs…', 70);
  pyodide.FS.mkdirTree('/app');
  pyodide.unpackArchive(await (await fetch(base + 'assets/engine.zip')).arrayBuffer(), 'zip', { extractDir: '/app' });
  pyodide.FS.mkdirTree('/workspace');
  pyodide.FS.mount(pyodide.FS.filesystems.IDBFS, {}, '/workspace');
  await syncfs(true);
  say('تشغيل المحرك…', 'Starting the engine…', 86);
  await pyodide.runPythonAsync("import sys; sys.path.insert(0, '/app/apps/dossier-builder/web'); import pybridge");
  handle = pyodide.globals.get('pybridge').handle;
  self.postMessage({ type: 'ready' });
  runtime.tidy();
})();
ready.catch(e => { console.error(e); self.postMessage({ type: 'failed', message: String(e && e.message || e) }); });

self.onmessage = async (ev) => {
  const m = ev.data || {};
  if (m.type === 'api') {
    try {
      await ready;
      const res = await handle(m.method, m.path, m.query, m.headers, new Uint8Array(m.body || new ArrayBuffer(0)));
      const out = res[1], buf = out.byteOffset === 0 && out.byteLength === out.buffer.byteLength ? out.buffer : out.buffer.slice(out.byteOffset, out.byteOffset + out.byteLength);      // the answer's own block goes to the page as it is: a large file is not copied once more
      if (m.method !== 'GET' && m.method !== 'HEAD') scheduleSync();
      self.postMessage({ type: 'api', id: m.id, meta: res[0], out: buf }, [buf]);
    } catch (e) {
      const mem = /MemoryError|alloc|out of memory/i.test(String(e && e.message || e));          // a file larger than what the page can hold
      const body = new TextEncoder().encode(JSON.stringify({ detail: mem ? { code: 'E-MEMORY', en: 'A file this large does not fit in the memory the browser gives the page. Close other tabs and try again, split the file, or use the desktop program, which takes it whole.', ar: 'ملف بالحجم ده أكبر من الذاكرة اللي المتصفح بيديها للصفحة. اقفل تبويبات تانية وجرّب تاني، أو قسّم الملف، أو استخدم برنامج سطح المكتب — بياخده كامل.' }
        : { code: 'E-ENGINE', en: String(e && e.message || e), ar: 'المحرك ما قدرش ينفّذ الطلب.' } }));
      self.postMessage({ type: 'api', id: m.id, meta: JSON.stringify({ status: mem ? 507 : 500, headers: [['content-type', 'application/json']] }), out: body.buffer }, [body.buffer]);
    }
  } else if (m.type === 'sync') {
    try { await ready; await syncfs(false); saved(); self.postMessage({ type: 'sync', id: m.id }); }
    catch (e) { saved(e); self.postMessage({ type: 'sync', id: m.id, error: String(e && (e.name || e.message) || e) }); }
  }
};
