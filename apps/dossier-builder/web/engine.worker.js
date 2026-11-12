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
function decode64(text) {
  const bin = atob(text), out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
// binary assets are published as base64 text (the artifact host serves text, not archives); Pyodide fetches them through here
self.fetch = async function (input, init) {
  const url = typeof input === 'string' ? input : (input && input.url) || String(input);
  let u; try { u = new URL(url, base); } catch (e) { return realFetch(input, init); }
  if (u.origin !== self.location.origin || !B64.test(u.pathname)) return realFetch(input, init);
  const r = await realFetch(u.href + '.b64.txt');
  if (!r.ok) return r;
  const bytes = decode64(await r.text());
  return new Response(bytes, { status: 200, headers: { 'content-type': MIME[u.pathname.split('.').pop()], 'content-length': String(bytes.length) } });
};

let pyodide = null, handle = null, syncTimer = null;
const syncfs = (populate) => new Promise((res, rej) => pyodide.FS.syncfs(populate, e => e ? rej(e) : res()));
/* what was written reaches the browser's storage a moment after the request, and never later than a second and a half into a long run
   of requests (a folder being read): closing the page in the middle loses nothing that was already taken */
let syncSince = 0;
function scheduleSync() {
  const now = Date.now(); if (!syncSince) syncSince = now;
  clearTimeout(syncTimer);
  syncTimer = setTimeout(() => { syncSince = 0; syncfs(false).catch(e => console.warn('sync', e)); }, now - syncSince > 1500 ? 0 : 250);
}
const say = (ar, en, pct) => self.postMessage({ type: 'say', ar, en, pct });

const ready = (async () => {
  say('تحميل محرك الملفات…', 'Loading the dossier engine…', 4);
  importScripts(base + 'assets/pyodide/pyodide.js');
  pyodide = await loadPyodide({ indexURL: base + 'assets/pyodide/' });
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
})();
ready.catch(e => { console.error(e); self.postMessage({ type: 'failed', message: String(e && e.message || e) }); });

self.onmessage = async (ev) => {
  const m = ev.data || {};
  if (m.type === 'api') {
    try {
      await ready;
      const res = await handle(m.method, m.path, m.query, m.headers, new Uint8Array(m.body || new ArrayBuffer(0)));
      const out = res[1], buf = out.buffer.slice(out.byteOffset, out.byteOffset + out.byteLength);
      if (m.method !== 'GET' && m.method !== 'HEAD') scheduleSync();
      self.postMessage({ type: 'api', id: m.id, meta: res[0], out: buf }, [buf]);
    } catch (e) {
      const body = new TextEncoder().encode(JSON.stringify({ detail: { code: 'E-ENGINE', en: String(e && e.message || e), ar: 'المحرك ما قدرش ينفّذ الطلب.' } }));
      self.postMessage({ type: 'api', id: m.id, meta: JSON.stringify({ status: 500, headers: [['content-type', 'application/json']] }), out: body.buffer }, [body.buffer]);
    }
  } else if (m.type === 'sync') {
    try { await ready; await syncfs(false); self.postMessage({ type: 'sync', id: m.id }); }
    catch (e) { self.postMessage({ type: 'sync', id: m.id, error: String(e && e.message || e) }); }
  }
};
