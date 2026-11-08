/* Boots the Python engine in the browser (Pyodide) and routes the interface's fetch('/api/…') calls to it.
   Files stay in this browser (IndexedDB); downloads go through the claude.ai «downloads» capability when present. */
(function () {
  'use strict';
  const WHEELS = ['typing_extensions-4.12.2-py3-none-any.whl', 'sniffio-1.3.1-py3-none-any.whl', 'idna-3.10-py3-none-any.whl',
    'anyio-4.6.2.post1-py3-none-any.whl', 'starlette-0.46.2-py3-none-any.whl', 'fastapi-0.115.12-py3-none-any.whl',
    'python_multipart-0.0.20-py3-none-any.whl', 'pypdf-7.0.0-py3-none-any.whl', 'python_docx-1.2.0-py3-none-any.whl'];
  const PKGS = ['sqlite3', 'hashlib', 'ssl', 'lxml', 'pyyaml', 'pydantic', 'jsonschema'];
  const base = new URL('.', document.baseURI).href;
  window.DB_TESS_BASE = base + 'assets/tess/'; window.DB_PDFJS_BASE = base + 'assets/pdfjs/';     // ocr.js (tesseract.js + pdf.js)
  const S = { pyodide: null, handle: null, syncTimer: null, ready: null };
  const AR = (document.documentElement.lang || 'ar') !== 'en';

  const ov = document.createElement('div');
  ov.id = 'boot';
  ov.setAttribute('role', 'status');
  ov.style.cssText = 'position:fixed;inset:0;z-index:1000;display:grid;place-items:center;background:var(--bg,#070B12);color:var(--ink,#E9EFF7);font-family:inherit';
  ov.innerHTML = '<div style="width:min(440px,90vw);display:flex;flex-direction:column;gap:14px;align-items:center;text-align:center">' +
    '<div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(135deg,#22D3EE,#A78BFA);display:grid;place-items:center;font-family:ui-monospace,monospace;font-weight:600;color:#04161B">DB</div>' +
    '<div id="bootMsg" style="font-size:15px;font-weight:600"></div><div id="bootSub" style="font-size:12.5px;color:var(--muted,#8C9BB0)"></div>' +
    '<div style="width:100%;height:6px;border-radius:999px;background:rgba(128,128,128,.2);overflow:hidden"><i id="bootBar" style="display:block;height:100%;width:3%;background:linear-gradient(90deg,#22D3EE,#A78BFA);transition:width .3s"></i></div></div>';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(ov));
  if (document.body) document.body.appendChild(ov);
  const say = (ar, en, pct) => { const m = document.getElementById('bootMsg'), b = document.getElementById('bootBar');
    if (m) m.textContent = AR ? ar : en; if (b && pct != null) b.style.width = pct + '%'; };
  const sub = (ar, en) => { const s = document.getElementById('bootSub'); if (s) s.textContent = AR ? ar : en; };

  const syncfs = (populate) => new Promise((res, rej) => S.pyodide.FS.syncfs(populate, e => e ? rej(e) : res()));
  function scheduleSync() { clearTimeout(S.syncTimer); S.syncTimer = setTimeout(() => syncfs(false).catch(e => console.warn('sync', e)), 600); }

  const nativeFetch = window.fetch.bind(window);
  const B64 = /\/assets\/.+\.(wasm|zip|whl)$/;
  const MIME = { wasm: 'application/wasm', zip: 'application/zip', whl: 'application/zip' };
  function decode64(text) {
    const bin = atob(text), out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  // binary assets are published as base64 text (the artifact host serves text, not archives); Pyodide fetches them through here
  async function fetchAsset(input, init, url) {
    let u; try { u = new URL(url, document.baseURI); } catch (e) { return nativeFetch(input, init); }
    if (u.origin !== location.origin || !B64.test(u.pathname)) return nativeFetch(input, init);
    const r = await nativeFetch(u.href + '.b64.txt');
    if (!r.ok) return r;
    const bytes = decode64(await r.text());
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
    if (b != null) {
      if (typeof b === 'string') body = new TextEncoder().encode(b);
      else if (b instanceof FormData) { const r = new Response(b); headers['content-type'] = r.headers.get('content-type'); body = new Uint8Array(await r.arrayBuffer()); }
      else if (b instanceof Blob) body = new Uint8Array(await b.arrayBuffer());
      else if (b instanceof ArrayBuffer) body = new Uint8Array(b);
      else if (ArrayBuffer.isView(b)) body = new Uint8Array(b.buffer, b.byteOffset, b.byteLength);
    }
    headers['content-length'] = String(body.length);
    const res = await S.handle(method, path, query, JSON.stringify(headers), body);
    const meta = JSON.parse(res[0]), out = res[1];
    if (method !== 'GET' && method !== 'HEAD') scheduleSync();
    return new Response(out.length ? out : null, { status: meta.status, headers: meta.headers });
  };

  S.ready = (async () => {
    say('تحميل محرك الملفات…', 'Loading the dossier engine…', 4);
    sub('أول مرة بس — بعدها بيفتح فوراً', 'First time only — it opens instantly afterwards');
    const pyodide = await loadPyodide({ indexURL: base + 'assets/pyodide/' });
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
    say('جاهز', 'Ready', 100);
    setTimeout(() => ov.remove(), 150);
  })().catch(e => { console.error(e); say('تعذّر تشغيل المحرك', 'The engine could not start', 100); sub(String(e && e.message || e), String(e && e.message || e)); throw e; });

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
  // ---- AI intake (claude.ai only): Claude reads the documents' text, and the page images of scanned PDFs
  let pdfjsP = null;
  function pdfjs() {
    if (!pdfjsP) pdfjsP = import(base + 'assets/pdfjs/pdf.min.mjs').then(m => { m.GlobalWorkerOptions.workerSrc = base + 'assets/pdfjs/pdf.worker.min.mjs'; return m; });
    return pdfjsP;
  }
  async function pageImages(file, max) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    const out = [];
    for (let i = 1; i <= Math.min(doc.numPages, max); i++) {
      const page = await doc.getPage(i), vp = page.getViewport({ scale: 1.4 });
      const c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height;
      await page.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
      out.push(await new Promise(r => c.toBlob(r, 'image/jpeg', 0.85)));
    }
    return out;
  }
  window.DBAI = {
    async available() { try { return !!(window.claude && typeof window.claude.use === 'function' && await window.claude.use('sample')); } catch (e) { return false; } },
    async extract(prompt, files, meta, target) {
      const sample = await window.claude.use('sample');
      if (!sample) throw { code: 'unavailable', message: 'sample unavailable' };
      const lim = await sample.limits().catch(() => null);
      const maxImages = (lim && lim.images && lim.images.maxCount) || 4;     // limits unknown → still send the scans (4 pages)
      const images = [];
      if (files && meta && !(lim && lim.images === false)) {
        for (let i = 0; i < files.length && images.length < maxImages; i++) {
          if (!files[i] || !meta[i] || !meta[i].scanned) continue;
          const isImage = /^image\//.test(files[i].type || '') || /\.(jpe?g|png|webp|gif)$/i.test(files[i].name || '');
          const imgs = (isImage ? [files[i]] : await pageImages(files[i], 3)).slice(0, maxImages - images.length);
          if (imgs.length) { prompt += `\n(Images ${images.length + 1}-${images.length + imgs.length} are the pages of document "${files[i].name}".)`; images.push(...imgs); }
        }
      }
      const opts = { modelTier: target === 'document' ? 'quick' : 'default', cache: false };
      if (images.length) opts.images = images;
      try { return await sample.json(prompt, opts); }
      catch (e) { if (images.length && !(e && e.code === 'declined')) { delete opts.images; return await sample.json(prompt, opts); } throw e; }
    },
    pageImages,
  };
  window.DBWEB = { sync: () => syncfs(false), ready: () => S.ready, pyodide: () => S.pyodide, save: saveFromApi };
})();
