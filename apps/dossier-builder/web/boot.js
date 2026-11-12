/* Boots the Python engine in the browser (Pyodide) and routes the interface's fetch('/api/…') calls to it.
   The engine runs in a worker (assets/engine.worker.js), so the page keeps answering while a document is read; where a
   worker cannot start, it runs on the page's own thread as before.
   Files stay in this browser (IndexedDB); downloads go through the claude.ai «downloads» capability when present. */
(function () {
  'use strict';
  const WHEELS = ['typing_extensions-4.12.2-py3-none-any.whl', 'sniffio-1.3.1-py3-none-any.whl', 'idna-3.10-py3-none-any.whl',
    'anyio-4.6.2.post1-py3-none-any.whl', 'starlette-0.46.2-py3-none-any.whl', 'fastapi-0.115.12-py3-none-any.whl',
    'python_multipart-0.0.20-py3-none-any.whl', 'pypdf-7.0.0-py3-none-any.whl', 'python_docx-1.2.0-py3-none-any.whl'];
  const PKGS = ['sqlite3', 'hashlib', 'ssl', 'lxml', 'pyyaml', 'pydantic', 'jsonschema'];
  const base = new URL('.', document.baseURI).href;
  const S = { pyodide: null, handle: null, worker: null, syncTimer: null, ready: null };
  const AR = (document.documentElement.lang || 'ar') !== 'en';

  const ov = document.createElement('div');
  ov.id = 'boot';
  ov.setAttribute('role', 'status');
  ov.style.cssText = 'position:fixed;inset:0;z-index:1000;display:grid;place-items:center;background:var(--bg,#070B12);color:var(--ink,#E9EFF7);font-family:inherit';
  ov.innerHTML = '<div style="width:min(440px,90vw);display:flex;flex-direction:column;gap:14px;align-items:center;text-align:center">' +
    '<div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(135deg,#22D3EE,#A78BFA);display:grid;place-items:center;font-family:ui-monospace,monospace;font-weight:600;color:#04161B">DB</div>' +
    '<div id="bootMsg" style="font-size:15px;font-weight:600"></div><div id="bootSub" style="font-size:12.5px;color:var(--muted,#8C9BB0)"></div>' +
    '<div style="width:100%;height:6px;border-radius:999px;background:rgba(128,128,128,.2);overflow:hidden"><i id="bootBar" style="display:block;height:100%;width:3%;background:linear-gradient(90deg,#22D3EE,#A78BFA);transition:width .3s"></i></div>' +
    '<div id="bootTime" style="font-size:12px;color:var(--muted,#8C9BB0);font-variant-numeric:tabular-nums;min-height:1.4em"></div>' +
    '<div id="bootHelp" hidden style="font-size:13px;line-height:1.7;display:flex;flex-direction:column;gap:10px;align-items:center"><span></span>' +
    '<button type="button" style="font:inherit;padding:7px 18px;border-radius:9px;border:1px solid var(--line,rgba(128,128,128,.45));background:transparent;color:inherit;cursor:pointer"></button></div></div>';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(ov));
  if (document.body) document.body.appendChild(ov);
  /* the loading screen says what is happening, how far it is and for how long — and, when nothing has moved for a while, that it
     is the line that is slow, with a way to try again: an opening that is slow never looks like one that is stuck */
  const L0 = { started: Date.now(), moved: Date.now(), bar: 3, done: false, failed: false, loaded: 0, total: 0, net: 0 };
  const bar = pct => { const b = document.getElementById('bootBar'); if (pct > L0.bar) L0.bar = pct; if (b) b.style.width = L0.bar + '%'; };
  const say = (ar, en, pct) => { const m = document.getElementById('bootMsg'); L0.moved = Date.now();
    if (m) m.textContent = AR ? ar : en; if (pct != null) bar(pct); };
  const sub = (ar, en) => { const s = document.getElementById('bootSub'); if (s) s.textContent = AR ? ar : en; };
  const mb = n => (n / 1048576).toFixed(n < 10485760 ? 1 : 0);
  function loadProgress(st) {                                       // bytes of the runtime's files, from the network or from this device
    if (st.loaded > L0.loaded) L0.moved = Date.now();
    L0.loaded = st.loaded; L0.total = st.total; L0.net = st.net;
    if (st.total) bar(4 + 60 * Math.min(1, st.loaded / st.total));
    if (st.net > 0) sub(`بينزّل ملفات التشغيل: ${mb(st.loaded)} من ${mb(st.total)} ميجا — أول مرة بس، بعدها بتتفتح من جهازك`, `Downloading the runtime: ${mb(st.loaded)} of ${mb(st.total)} MB — the first time only; afterwards it opens from this device`);
    else if (st.loaded > 0) sub('بيفتح من الملفات المحفوظة على جهازك — مفيش تنزيل', 'Opening from the files kept on this device — nothing to download');
  }
  const tick = setInterval(() => {
    const t = document.getElementById('bootTime'), h = document.getElementById('bootHelp');
    if (L0.done || !document.getElementById('boot')) { clearInterval(tick); return; }
    const secs = Math.round((Date.now() - L0.started) / 1000), still = Math.round((Date.now() - L0.moved) / 1000);
    if (t && secs >= 8 && !L0.failed) t.textContent = AR ? `بقاله ${secs} ثانية` : `${secs} s so far`;
    const fetching = !L0.total || L0.loaded < L0.total;                // still waiting for bytes; after them the engine works with no news for a while
    const stuck = L0.failed || still >= (fetching ? 40 : 150);
    if (h) { h.hidden = !stuck;
      if (stuck) { h.firstChild.textContent = L0.failed ? (AR ? 'ما فتحش. جرّب تاني؛ ولو اتكررت ابعت السطر اللي فوق.' : 'It did not open. Try again; if it repeats, send the line above.')
          : fetching ? (AR ? `مفيش بيانات وصلت من ${still} ثانية: الاتصال بطيء أو مقطوع. استنى شوية أو جرّب تاني.` : `No data has arrived for ${still} s: the line is slow or down. Wait a little, or try again.`)
          : (AR ? `المحرك بيشتغل من ${still} ثانية من غير رد. استنى شوية أو جرّب تاني.` : `The engine has been starting for ${still} s with no answer. Wait a little, or try again.`);
        h.lastChild.textContent = AR ? 'حاول تاني' : 'Try again'; h.lastChild.onclick = () => location.reload(); } }
  }, 1000);

  let bigSync = null;                                               // bigfs.js: large files of the workspace are stored as Blobs
  const syncfs = (populate) => (bigSync || (bigSync = DB_BIGFS(S.pyodide.FS.filesystems.IDBFS)))(S.pyodide.FS, populate);
  function scheduleSync() {                                         // as in the worker: soon after a write, and at the latest 1.5 s into a run of requests
    const now = Date.now(); if (!S.syncSince) S.syncSince = now;
    clearTimeout(S.syncTimer);
    S.syncTimer = setTimeout(() => { S.syncSince = 0; syncfs(false).then(() => storageNote(), e => { console.warn('sync', e); storageNote(String(e && (e.name || e.message) || e)); }); }, now - S.syncSince > 1500 ? 0 : 250);
  }
  /* the browser refused to save (its storage for this page is full, or closed to it): said on the screen for as long as it is true —
     nothing is lost in silence. The note goes away with the first save that goes through. */
  function storageNote(error) {
    let el = document.getElementById('dbStorage');
    if (!error) { if (el) el.remove(); return; }
    const ar = (document.documentElement.lang || 'ar') !== 'en', full = /quota/i.test(error);
    if (!el) {
      el = document.createElement('div'); el.id = 'dbStorage'; el.setAttribute('role', 'alert');
      el.style.cssText = 'position:fixed;inset-inline:0;bottom:0;z-index:900;padding:12px max(16px,env(safe-area-inset-right,0px)) calc(12px + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px));background:var(--surface,#111826);color:var(--ink,#E9EFF7);border-top:2px solid var(--warn,#FBBF24);font-size:13.5px;line-height:1.6;display:flex;gap:12px;align-items:center;flex-wrap:wrap;box-shadow:0 -8px 24px rgba(0,0,0,.25)';
      (document.body || document.documentElement).appendChild(el);
    }
    const text = full
      ? (ar ? 'المتصفح رفض يحفظ آخر تغييرات: مساحة التخزين اللي سامح بيها للصفحة دي خلصت. اللي بتعمله دلوقتي مش بيتحفظ. فضّي مساحة: شيل الملف الكبير اللي لسه ضايفه، أو احذف مشروع قديم وفضّي «المحذوفات» — أو استخدم برنامج سطح المكتب للملفات الكبيرة جدًا.'
            : 'The browser refused to save the last changes: the storage it allows this page is full. What you do now is not being saved. Free some space: remove the large file you just added, or delete an old project and empty the trash — or use the desktop program for very large files.')
      : (ar ? 'المتصفح ما قدرش يحفظ آخر تغييرات (' + error + '). اللي بتعمله دلوقتي مش بيتحفظ: جرّب تاني، ولو فضلت الرسالة افتح الصفحة من جديد.'
            : 'The browser could not save the last changes (' + error + '). What you do now is not being saved: try again, and reload the page if this note stays.');
    el.innerHTML = '<span style="flex:1 1 320px;min-width:0"></span><span id="dbStorageUse" style="color:var(--muted,#8C9BB0);font-variant-numeric:tabular-nums"></span><button type="button" style="font:inherit;padding:6px 14px;border-radius:8px;border:1px solid var(--warn,#FBBF24);background:transparent;color:inherit;cursor:pointer"></button>';
    el.firstChild.textContent = '⚠ ' + text;
    const btn = el.lastChild; btn.textContent = ar ? 'جرّب الحفظ تاني' : 'Try saving again';
    btn.onclick = () => { btn.disabled = true; window.DBWEB.sync().then(() => storageNote(), e => storageNote(String(e && e.message || e))); };
    if (navigator.storage && navigator.storage.estimate) navigator.storage.estimate().then(q => { const u = document.getElementById('dbStorageUse');
      if (u && q && q.quota) u.textContent = (ar ? 'مستخدم ' : 'used ') + (q.usage / 1048576).toFixed(0) + (ar ? ' من ' : ' of ') + (q.quota / 1048576).toFixed(0) + (ar ? ' ميجا' : ' MB'); }).catch(() => {});
  }

  const nativeFetch = window.fetch.bind(window);
  const B64 = /\/assets\/.+\.(wasm|zip|whl)$/;
  const MIME = { wasm: 'application/wasm', zip: 'application/zip', whl: 'application/zip' };
  function decode64(text) {
    const bin = atob(text), out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  // binary assets are published as base64 text (the artifact host serves text, not archives); Pyodide fetches them through here
  const runtime = DB_ASSETS(typeof DB_MANIFEST === 'object' && DB_MANIFEST ? DB_MANIFEST : {}, nativeFetch, st => { if (!L0.done) loadProgress(st); });      // assets.js: kept on this device after the first download
  async function fetchAsset(input, init, url) {
    let u; try { u = new URL(url, document.baseURI); } catch (e) { return nativeFetch(input, init); }
    if (u.origin !== location.origin || !B64.test(u.pathname)) return nativeFetch(input, init);
    let bytes;
    try { bytes = await runtime.get(u.href.startsWith(base) ? u.href.slice(base.length) : u.pathname, u.href + '.b64.txt'); }
    catch (e) { if (e && e.status) return new Response(null, { status: e.status }); throw e; }
    return new Response(bytes, { status: 200, headers: { 'content-type': MIME[u.pathname.split('.').pop()], 'content-length': String(bytes.length) } });
  }
  window.fetch = async function (input, init) {
    init = init || {};
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    if (!url.startsWith('/api/')) return fetchAsset(input, init, url);
    await S.ready;
    const method = (init.method || (input && input.method) || 'GET').toUpperCase();
    const q = url.indexOf('?');
    const path = q < 0 ? url : url.slice(0, q), query = q < 0 ? '' : url.slice(q + 1);
    const headers = {};
    new Headers(init.headers || {}).forEach((v, k) => { headers[k] = v; });
    let body = new Uint8Array(0);
    const b = init.body;
    if (b != null) try {
      if (typeof b === 'string') body = new TextEncoder().encode(b);
      else if (b instanceof FormData) { const r = new Response(b); headers['content-type'] = r.headers.get('content-type'); body = new Uint8Array(await r.arrayBuffer()); }
      else if (b instanceof Blob) body = new Uint8Array(await b.arrayBuffer());
      else if (b instanceof ArrayBuffer) body = new Uint8Array(b.slice(0));                        // a copy: the caller keeps its buffer
      else if (ArrayBuffer.isView(b)) body = new Uint8Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
    } catch (e) {                                                      // the upload itself does not fit in the page's memory: said, not thrown
      return new Response(JSON.stringify({ detail: { code: 'E-MEMORY', en: 'A file this large does not fit in the memory the browser gives the page. Close other tabs and try again, split the file, or use the desktop program, which takes it whole.', ar: 'ملف بالحجم ده أكبر من الذاكرة اللي المتصفح بيديها للصفحة. اقفل تبويبات تانية وجرّب تاني، أو قسّم الملف، أو استخدم برنامج سطح المكتب — بياخده كامل.' } }), { status: 507, headers: { 'content-type': 'application/json' } });
    }
    headers['content-length'] = String(body.length);
    let meta, out;
    if (S.worker) {
      const m = await ask({ type: 'api', method, path, query, headers: JSON.stringify(headers), body: body.buffer }, [body.buffer]);
      meta = JSON.parse(m.meta); out = new Uint8Array(m.out);
    } else {
      const res = await S.handle(method, path, query, JSON.stringify(headers), body);
      meta = JSON.parse(res[0]); out = res[1];
      if (method !== 'GET' && method !== 'HEAD') scheduleSync();
    }
    return new Response(out.length ? out : null, { status: meta.status, headers: meta.headers });
  };

  // ---- the engine in its own thread: requests go out with an id and come back with it
  const pending = new Map(); let seq = 0;
  function ask(msg, transfer) { return new Promise(res => { const id = ++seq; pending.set(id, res); S.worker.postMessage(Object.assign({ id }, msg), transfer || []); }); }
  function engineDown(why) {                                       // the worker died after it was ready: every waiting call gets an answer
    const body = new TextEncoder().encode(JSON.stringify({ detail: { code: 'E-ENGINE', en: 'The engine stopped (' + why + '). Reload the page.', ar: 'المحرك وقف. افتح الصفحة من جديد.' } }));
    for (const [id, res] of pending) res({ id, meta: JSON.stringify({ status: 500, headers: [['content-type', 'application/json']] }), out: body.slice().buffer });
    pending.clear();
  }
  function startWorker() {
    return new Promise((resolve, reject) => {
      let w, settled = false, alive = false;
      const fail = why => { if (settled) return; settled = true; clearTimeout(timer); try { w.terminate(); } catch (e) {} reject(new Error(why)); };
      try { w = new Worker(base + 'assets/engine.worker.js'); } catch (e) { reject(e); return; }
      const timer = setTimeout(() => { if (!alive) fail('the engine worker did not answer'); }, 20000);
      w.onerror = e => { const why = (e && e.message) || 'worker error'; if (!settled) fail(why); else { console.error('engine worker', why); engineDown(why); } };
      w.onmessage = ev => {
        const m = ev.data || {}; alive = true;
        if (m.type === 'say') say(m.ar, m.en, m.pct);
        else if (m.type === 'load') loadProgress(m);
        else if (m.type === 'ready') { settled = true; clearTimeout(timer); resolve(w); }
        else if (m.type === 'failed') fail(m.message || 'the engine could not start');
        else if (m.type === 'storage') storageNote(m.error);
        else if (m.type === 'api' || m.type === 'sync') { const res = pending.get(m.id); if (res) { pending.delete(m.id); res(m); } }
      };
    });
  }
  async function bootHere() {                                      // the engine on the page's own thread (no worker available)
    say('تحميل محرك الملفات…', 'Loading the dossier engine…', 4);
    const pyodide = await loadPyodide({ indexURL: base + 'assets/pyodide/' });
    DB_SAFEFS(pyodide.FS);                                          // bigfs.js: a file too large for the page's memory is refused, the engine goes on
    S.pyodide = pyodide;
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
    S.handle = pyodide.globals.get('pybridge').handle;
  }
  S.ready = (async () => {
    say('تحميل محرك الملفات…', 'Loading the dossier engine…', 4);
    let inWorker = false;
    if (window.Worker && !/[?&]engine=page\b/.test(location.search)) {
      try { S.worker = await startWorker(); inWorker = true; }
      catch (e) { S.worker = null; console.warn('engine worker unavailable; the engine runs in the page:', e && e.message); }
    }
    if (!inWorker) { await bootHere(); runtime.tidy(); }
    document.documentElement.dataset.engine = inWorker ? 'worker' : 'page';
    L0.done = true;
    say('جاهز', 'Ready', 100);
    setTimeout(() => ov.remove(), 150);
  })().catch(e => { console.error(e); L0.failed = true; say('تعذّر تشغيل المحرك', 'The engine could not start', 100); sub(String(e && e.message || e), String(e && e.message || e)); throw e; });

  async function saveFromApi(url) {
    const r = await window.fetch(url);
    if (!r.ok) { const t = document.getElementById('toast'); if (t) { t.textContent = AR ? 'تعذّر تحميل الملف' : 'Could not fetch the file'; t.hidden = false; } return; }
    const blob = await r.blob();
    const cd = r.headers.get('content-disposition') || '';
    const m1 = cd.match(/filename\*=UTF-8''([^;]+)/i), m2 = cd.match(/filename="?([^";]+)"?/i);
    const name = m1 ? decodeURIComponent(m1[1]) : m2 ? m2[1] : (url.split('/').pop().split('?')[0] || 'file');
    const dl = (window.claude && typeof window.claude.use === 'function') ? await window.claude.use('downloads') : null;
    if (dl) { try { await dl.save({ filename: name, data: blob }); } catch (e) { if (!e || e.code !== 'declined') console.warn('download', e); } return; }
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }
  document.addEventListener('click', e => {
    const a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    const href = a.getAttribute('href') || '';
    if (href.startsWith('/api/')) { e.preventDefault(); e.stopPropagation(); saveFromApi(href); }
  }, true);
  const nativeOpen = window.open;
  window.open = function (u) { if (typeof u === 'string' && u.startsWith('/api/')) { saveFromApi(u); return null; } return nativeOpen.apply(window, arguments); };
  // ---- AI intake (claude.ai only): Claude reads the documents' own text, sent in the prompt — no OCR and no page images
  // (a file without text is refused at the upload gate: NP.CAPP.065 v5 general note 4 wants every document searchable)
  window.DBAI = {
    async available() { try { return !!(window.claude && typeof window.claude.use === 'function' && await window.claude.use('sample')); } catch (e) { return false; } },
    async extract(prompt, files, meta, target) {
      const sample = await window.claude.use('sample');
      if (!sample) throw { code: 'unavailable', message: 'sample unavailable' };
      return await sample.json(prompt, { modelTier: target === 'document' ? 'quick' : 'default', cache: false });
    },
    /* one JSON answer from claude.ai's model for a prompt the engine wrote (drafting a document, filling a template) */
    async ask(prompt, opts) {
      const sample = await window.claude.use('sample');
      if (!sample) throw { code: 'unavailable', message: 'sample unavailable' };
      return await sample.json(prompt, Object.assign({ modelTier: 'default', cache: false }, opts || {}));
    },
  };
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden' && window.DBWEB) window.DBWEB.sync().catch(() => {}); });   // leaving the tab: write the storage now
  window.DBWEB = { sync: () => S.worker ? ask({ type: 'sync' }).then(m => { if (m.error) throw new Error(m.error); }) : syncfs(false).then(() => storageNote(), e => { storageNote(String(e && (e.name || e.message) || e)); throw e; }), ready: () => S.ready, pyodide: () => S.pyodide,
    engine: () => S.worker ? 'worker' : 'page', save: saveFromApi };
})();
