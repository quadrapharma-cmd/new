/* The editing programs inside the page — the Word program and the PDF program (the photo and design programs follow the same way).
   Each is the real program, built from its source for the browser (WebAssembly; apps/dossier-builder-v2/tools/craft), and runs in a
   frame of its own above the page. The page writes that frame itself (srcdoc): a written frame is the page's own document under the
   page's own rules — claude.ai refuses frames of other sites, and no address is fetched for this one — and closing it gives its
   memory back. Nothing of a program is loaded until a document is opened in it: its WebAssembly (gzip in base64 text, in parts the
   artifact host can serve) is fetched then, checked against its SHA-256 and kept on the device for the next time.
     · «page» programs (Word, PDF) have a host mode: what the person saves (Ctrl+S, «Save») comes back to the page as a file
       instead of a download, the program says when the document has changed («dirty»), and the page can give it commands (file.save).
     · «drop» programs (photo, design) have none: the frame hands them the file as a dropped file, knows they started when they take
       away their own «loading» note, and keeps the files they save (a link to a blob, clicked) instead of letting them download.
   The page (ui/index.html) decides what a saved file becomes: a new version of the document it was opened from. A save with no
   change made is not kept: the program writes the file anew, and a version that differs from the old one only by that is noise.
   What each program opens was decided on his real files (15/11, apps/dossier-builder/README.md «The Word program»): the Word program
   opens .docx — saved with no change, his .docx files kept every word and their pages; his old .doc files lost table columns and
   footers, so a .doc is not offered — and its own «Export PDF» is not offered (other fonts, more pages, Arabic that breaks apart
   when copied, beside LibreOffice's PDF of the same files): the PDF is still made in Word.
   window.DB_PROGRAMS = {base, apps: {app: {parts, size, bytes, sha256}}} is written by web/build.py; no list, no program
   (the desktop and server editions, a build without them).

   DBPROG.forFile(name) → app | null          the program that opens this file in this edition
   DBPROG.title(app, lang) → 'برنامج الـ Word'
   DBPROG.open(app, {name, bytes, lang, onSave({name, bytes}), onClose()}) → {execute, inspect, close, save, ready, edited} */
(function (root) {
  'use strict';
  const PROGRAMS = {
    wordcraft: { ar: 'برنامج الـ Word', en: 'the Word program', canvas: 'wordcraft_canvas', loading: 'wordcraft_loading', host: 'page',
                 query: '?webgl&control', files: /\.docx$/i,
                 afterSave: { ar: 'الـ PDF بتاعه اعمله من Word على جهازك زي العادة.', en: 'Make its PDF in Word on your computer, as before.' } },
    // PdfCraft's own scan reader is not started (no <meta name="pdfcraft-ocr-worker">): English-only models; the page has its own.
    pdfcraft: { ar: 'برنامج الـ PDF', en: 'the PDF program', canvas: 'pdfcraft', loading: 'pdfcraft_loading', host: 'page',
                query: '?webgl&control', files: /\.pdf$/i },
    // the page opens these two itself (no file kind of the dossier is theirs): a PDF page drawn as a picture for the photo program,
    // an artwork PDF placed into a design in the design program (ui/index.html pageInPhoto, docInDesign)
    photocraft: { ar: 'برنامج الصور', en: 'the photo program', canvas: 'photocraft_canvas', loading: 'photocraft_loading', host: 'drop', query: '', files: null,
                  hint: { ar: 'نضّف الصفحة (قص، عدل، فتّح، امسح) واحفظ بـ Ctrl+S: الصفحة دي بتتبدّل في الملف كنسخة جديدة، والباقي زي ما هو.',
                          en: 'Clean the page (crop, straighten, lighten, erase) and save with Ctrl+S: this page is replaced in the file as a new version; the others stay as they are.' } },
    designcraft: { ar: 'برنامج التصميم', en: 'the design program', canvas: 'designcraft_canvas', loading: 'designcraft_loading', host: 'drop', query: '', files: null,
                   hint: { ar: 'اعمل مستند (Ctrl+N)، وبعدين «حط الملف في التصميم». لما تخلص: File ← Export PDF… والـ PDF بيرجع للبند كنسخة جديدة. (Ctrl+S بيحفظ التصميم نفسه، ومش بيتحط في الملف.)',
                           en: 'Make a document (Ctrl+N), then «Place the file in the design». When done: File ▸ Export PDF… and the PDF comes back to the item as a new version. (Ctrl+S saves the design itself; it does not go into the dossier.)' } },
  };
  const list = () => (root.DB_PROGRAMS && root.DB_PROGRAMS.apps) || {};
  const available = app => !!(PROGRAMS[app] && list()[app] && typeof WebAssembly === 'object' && typeof DecompressionStream === 'function');
  const forFile = name => Object.keys(PROGRAMS).find(a => available(a) && PROGRAMS[a].files && PROGRAMS[a].files.test(String(name || ''))) || null;
  const title = (app, lang) => (PROGRAMS[app] ? PROGRAMS[app][lang === 'en' ? 'en' : 'ar'] : app);
  const abs = rel => new URL(rel, document.baseURI).href;

  const T = {
    loading: { ar: 'بيحمّل {p}…', en: 'Loading {p}…' },
    first: { ar: 'أول مرة بس: البرنامج بيتنزّل على جهازك ({mb} ميجا)، وبعد كده بيفتح على طول.', en: 'The first time only: the program is downloaded to this device ({mb} MB); after that it opens at once.' },
    starting: { ar: 'بيشغّل {p}…', en: 'Starting {p}…' },
    opening: { ar: 'بيفتح الملف…', en: 'Opening the file…' },
    ready: { ar: 'عدّل في الملف، وبعدين «احفظه نسخة جديدة» (أو Ctrl+S). النسخة القديمة بتفضل محفوظة.', en: 'Edit the file, then «Save as a new version» (or Ctrl+S). The old version is kept.' },
    saving: { ar: 'بيحفظ نسخة جديدة…', en: 'Saving a new version…' },
    saved: { ar: 'اتحفظ نسخة جديدة: {n}.', en: 'Saved as a new version: {n}.' },
    nothing: { ar: 'مفيش تعديل يتحفظ.', en: 'Nothing was changed: nothing to save.' },
    noFile: { ar: 'البرنامج مارجّعش الملف. جرّب «احفظه نسخة جديدة» تاني (أو Ctrl+S).', en: 'The program gave no file back. Try «Save as a new version» again (or Ctrl+S).' },
    saveFail: { ar: 'ماقدرتش أحفظ: {e}', en: 'Could not save: {e}' },
    failed: { ar: '{p} ماقدرش يشتغل هنا: {e}', en: '{p} could not start here: {e}' },
    blocked: { ar: 'الصفحة دي مش سامحة بتشغيل البرامج جواها.', en: 'This page does not allow programs to run inside it.' },
    save: { ar: 'احفظه نسخة جديدة', en: 'Save as a new version' },
    close: { ar: 'اقفل', en: 'Close' },
    unsaved: { ar: 'فيه تعديلات ماتحفظتش. تقفل من غير ما تحفظها؟', en: 'There are changes that were not saved. Close without saving them?' },
    discard: { ar: 'اقفل من غير حفظ', en: 'Close without saving' },
    back: { ar: 'ارجع للملف', en: 'Back to the file' },
    place: { ar: 'حط الملف في التصميم', en: 'Place the file in the design' },
    placed: { ar: 'الملف اتحط في الصفحة المفتوحة في البرنامج.', en: 'The file was placed on the page open in the program.' },
  };

  // ── what runs inside the frame: the relay between the program and the page, and the program's loader ──────────────────────
  // Written into the frame as source (frameMain.toString()); it sees only what `cfg` carries.
  function frameMain(cfg) {
    var app = cfg.app, canvas = document.getElementById(cfg.canvas), started = false;
    function up(type, detail, transfer) {
      var m = { dbprog: cfg.key, type: type };
      for (var k in (detail || {})) m[k] = detail[k];
      parent.postMessage(m, '*', transfer || []);
    }
    function fail(err) { up('failed', { error: String((err && (err.message || err.name)) || err), name: String(err && err.name || '') }); }
    window.__dbQuery = cfg.query;                                   // what the program reads as the page's address (glue.js, built)
    if (cfg.host === 'page') {
      ['ready', 'save', 'dirty', 'failed'].forEach(function (t) {
        canvas.addEventListener(app + ':' + t, function (e) {
          if (t === 'ready') { started = true; var n = document.getElementById(cfg.loading); if (n) n.remove(); }
          var d = e.detail || {}, out = {};
          for (var k in d) out[k] = d[k];
          if (t === 'save' && out.bytes && !(out.bytes instanceof ArrayBuffer)) out.bytes = new Uint8Array(out.bytes).slice().buffer;
          up(t, out, t === 'save' && out.bytes ? [out.bytes] : []);
        });
      });
    } else {
      // A «drop» program saves by a download (a link to a blob, clicked): the file goes to the page instead.
      var blobs = new Map(), makeURL = URL.createObjectURL, dropURL = URL.revokeObjectURL, click = HTMLAnchorElement.prototype.click;
      URL.createObjectURL = function (o) { var u = makeURL.call(URL, o); if (o instanceof Blob) blobs.set(u, o); return u; };
      URL.revokeObjectURL = function (u) { blobs.delete(u); return dropURL.call(URL, u); };
      HTMLAnchorElement.prototype.click = function () {
        var blob = this.download ? blobs.get(this.href) : null;
        if (!blob) return click.call(this);
        var name = this.download;
        blob.arrayBuffer().then(function (buf) { up('save', { name: name, bytes: buf }, [buf]); });
      };
      // Started when the program takes its «loading» note away; a note it rewrote is why it could not start.
      var note = document.getElementById(cfg.loading), first = note ? note.textContent : '', done = false;
      new MutationObserver(function () {
        if (done || !wasmGiven) return;
        var el = document.getElementById(cfg.loading);
        if (!el) { done = true; started = true; up('ready'); }
        else if (el.textContent !== first) { done = true; fail(el.textContent.trim().slice(0, 300)); }
      }).observe(document.body, { childList: true, subtree: true, characterData: true });
      var touched = false;                                          // no «dirty» of its own: the first key or click in it is work to keep
      ['keydown', 'pointerdown'].forEach(function (t) { addEventListener(t, function () { if (!touched && started) { touched = true; up('touched'); } }, true); });
    }
    var wasmGiven = false;
    addEventListener('message', function (e) {
      if (e.source !== parent) return;
      var m = e.data || {};
      if (m.dbprog !== cfg.key) return;
      if (m.type === 'open') {
        if (cfg.host === 'page') canvas.dispatchEvent(new CustomEvent(app + ':open', { detail: { name: m.name, bytes: m.bytes } }));
        else {
          canvas.dispatchEvent(new MouseEvent('mouseleave'));
          var dt = new DataTransfer();
          dt.items.add(new File([m.bytes], m.name));
          canvas.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true, clientX: 1, clientY: 1 }));
        }
      }
      if (m.type === 'place') {                                     // into what the design program has open: dropped in the middle of it
        var dp = new DataTransfer();
        dp.items.add(new File([m.bytes], m.name));
        canvas.dispatchEvent(new DragEvent('drop', { dataTransfer: dp, bubbles: true, cancelable: true, clientX: Math.round(innerWidth / 2), clientY: Math.round(innerHeight / 2) }));
      }
      if (m.type === 'execute' || m.type === 'inspect') {
        var api = window[app], kind = m.type === 'execute' ? 'executed' : 'inspected';
        var p = !api ? Promise.reject(new Error('no command API')) : (m.type === 'execute' ? api.execute(m.command, m.params || {}) : api.docInspect());
        Promise.resolve(p).then(function (r) { up(kind, { id: m.id, result: JSON.parse(JSON.stringify(r === undefined ? null : r)) }); },
                                function (err) { up(kind, { id: m.id, error: String((err && err.message) || err) }); });
      }
    });

    // The device keeps the program after its first download (IndexedDB, by its SHA-256); anything wrong there: the network.
    function idb(mode, what) {
      return new Promise(function (res) {
        try {
          var q = indexedDB.open('db-programs', 1);
          q.onupgradeneeded = function () { try { q.result.createObjectStore('files'); } catch (e) { /* there already */ } };
          q.onerror = q.onblocked = function () { res(undefined); };
          q.onsuccess = function () {
            try { var r = what(q.result.transaction('files', mode).objectStore('files')); r.onsuccess = function () { res(r.result); }; r.onerror = function () { res(undefined); }; }
            catch (e) { res(undefined); }
          };
        } catch (e) { res(undefined); }
      });
    }
    async function download() {
      var total = cfg.size, loaded = 0, texts = [];
      for (var k = 1; k <= cfg.parts; k++) {
        var r = await fetch(cfg.base + app + '/wasm.gz.b64.' + k + '.txt');
        if (!r.ok) throw new Error('HTTP ' + r.status + ' (' + app + ' ' + k + '/' + cfg.parts + ')');
        var reader = r.body.getReader(), dec = new TextDecoder(), chunks = [];
        for (;;) {
          var x = await reader.read();
          if (x.done) break;
          chunks.push(dec.decode(x.value, { stream: true }));
          loaded += x.value.length;
          up('progress', { loaded: loaded, total: total });
        }
        chunks.push(dec.decode());
        texts.push(chunks.join(''));
      }
      var bin = atob(texts.join('')), gz = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) gz[i] = bin.charCodeAt(i);
      return gz;
    }
    async function hex(bytes) {
      var d = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), s = '';
      for (var i = 0; i < d.length; i++) s += (d[i] < 16 ? '0' : '') + d[i].toString(16);
      return s;
    }
    (async function () {
      try {
        var kept = await idb('readonly', function (s) { return s.get(app); });
        var fromDevice = !!(kept && kept.sha256 === cfg.sha256 && kept.gz);
        up('loading', { fromDevice: fromDevice });
        var gz = fromDevice ? new Uint8Array(kept.gz) : await download();
        var wasm = new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
        if (wasm.length !== cfg.bytes || await hex(wasm) !== cfg.sha256) {
          if (fromDevice) idb('readwrite', function (s) { return s.delete(app); });
          throw new Error('the program\'s files did not arrive whole (SHA-256)');
        }
        up('starting');
        var mod = await import(cfg.base + app + '/glue.js');
        wasmGiven = true;
        await mod.default({ module_or_path: wasm });
        if (!fromDevice) { var keep = gz.buffer.slice(0); idb('readwrite', function (s) { return s.put({ sha256: cfg.sha256, gz: keep }, app); }); }
        setTimeout(function () { if (!started) fail('it did not start in 120 s'); }, 120000);
      } catch (err) { fail(err); }
    })();
  }

  const FRAME_CSS = 'html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#e6e6e6}'
    + 'canvas{position:absolute;inset:0;width:100%;height:100%;display:block;outline:none}'
    + '.loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#555;font:15px Tahoma,system-ui,sans-serif;pointer-events:none}';
  function frameDoc(app, key) {
    const p = PROGRAMS[app], m = list()[app];
    const cfg = { app, key, canvas: p.canvas, loading: p.loading, host: p.host, query: p.query, base: abs((root.DB_PROGRAMS && root.DB_PROGRAMS.base) || 'assets/programs/'),
                  parts: m.parts, size: m.size, bytes: m.bytes, sha256: m.sha256 };
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
      + `<title>${p.en}</title><style>${FRAME_CSS}</style></head><body>`
      + `<canvas id="${p.canvas}"${p.host === 'page' ? ' data-host="page"' : ''}></canvas><div id="${p.loading}" class="loading"></div>`
      + `<script>(${frameMain.toString()})(${JSON.stringify(cfg).replace(/</g, '\\u003c')});</` + 'script></body></html>';
  }

  // ── the layer above the page ─────────────────────────────────────────────────────────────────────────────────────────────
  const CSS = `.dbprog{position:fixed;inset:0;z-index:2000;display:flex;flex-direction:column;background:var(--bg,#0b1424)}
.dbprog-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:8px max(12px,env(safe-area-inset-right,0px)) 8px max(12px,env(safe-area-inset-left,0px));
  border-bottom:1px solid var(--line,#1c2838);background:var(--surface,#0e1520);color:var(--ink,#e9eff7)}
.dbprog-bar .dbprog-name{font-weight:650;white-space:nowrap}
.dbprog-bar .dbprog-file{min-width:0;flex:1 1 160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted,#8c9bb0)}
.dbprog-bar .dbprog-acts{display:flex;gap:6px;flex-wrap:wrap}
.dbprog-status{flex:1 1 100%;font-size:12.5px;color:var(--muted,#8c9bb0);min-height:1.2em}
.dbprog-status.bad{color:var(--bad,#f87171)} .dbprog-status.good{color:var(--ok,#34d399)}
.dbprog-body{position:relative;flex:1;min-height:0}
.dbprog-body iframe{position:absolute;inset:0;width:100%;height:100%;border:0;background:#e6e6e6}
.dbprog-wait{position:absolute;inset:0;display:flex;flex-direction:column;gap:10px;align-items:center;justify-content:center;background:var(--bg,#0b1424);
  color:var(--ink,#e9eff7);text-align:center;padding:0 16px}
.dbprog-wait .dbprog-meter{width:min(360px,80vw);height:6px;border-radius:3px;background:var(--line,#1c2838);overflow:hidden}
.dbprog-wait .dbprog-meter i{display:block;height:100%;width:0;background:var(--accent,#a78bfa);transition:width .2s}
.dbprog-ask{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:color-mix(in srgb,var(--bg,#0b1424) 70%,transparent)}
.dbprog-ask>div{max-width:420px;margin:0 16px;padding:18px;border-radius:14px;background:var(--surface,#0e1520);border:1px solid var(--line,#1c2838);
  color:var(--ink,#e9eff7);display:flex;flex-direction:column;gap:12px}
.dbprog-ask .row{display:flex;gap:8px;flex-wrap:wrap}`;
  let styled = false, current = null, seq = 0;

  function open(app, opts) {
    if (!available(app)) throw new Error('no ' + app + ' in this edition');
    if (current) current.close(true);
    if (!styled) { const s = document.createElement('style'); s.textContent = CSS; document.head.appendChild(s); styled = true; }
    const lang = opts.lang === 'en' ? 'en' : 'ar', p = PROGRAMS[app], m = list()[app], key = app + '-' + Date.now() + '-' + (++seq);
    const say = (k, v) => Object.entries(v || {}).reduce((s, [a, b]) => s.split('{' + a + '}').join(b), T[k][lang]).split('{p}').join(p[lang]);
    const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const layer = document.createElement('div');
    layer.className = 'dbprog'; layer.setAttribute('role', 'dialog'); layer.setAttribute('aria-modal', 'true'); layer.setAttribute('aria-label', p[lang]);
    layer.dir = lang === 'ar' ? 'rtl' : 'ltr';
    layer.innerHTML = `<div class="dbprog-bar"><span class="dbprog-name">${esc(p[lang])}</span><bdi class="dbprog-file" dir="auto">${esc(opts.name)}</bdi>
      <span class="dbprog-acts">${opts.place ? `<button class="btn sm pri" data-act="place" disabled>${esc(say('place'))}</button>` : ''}${p.host === 'page' ? `<button class="btn sm pri" data-act="save" disabled>${esc(say('save'))}</button>` : ''}
      <button class="btn sm ghost" data-act="close">${esc(say('close'))}</button></span><div class="dbprog-status" role="status" aria-live="polite"></div></div>
      <div class="dbprog-body"><div class="dbprog-wait"><b>${esc(say('loading'))}</b><div class="dbprog-meter"><i></i></div><span class="small muted"></span></div></div>`;
    document.body.appendChild(layer);
    const $ = s => layer.querySelector(s), status = (text, cls) => { const el = $('.dbprog-status'); el.textContent = text || ''; el.className = 'dbprog-status' + (cls ? ' ' + cls : ''); };
    const frame = document.createElement('iframe');
    frame.title = p[lang];
    frame.setAttribute('allow', 'fullscreen; clipboard-read; clipboard-write');
    frame.srcdoc = frameDoc(app, key);
    $('.dbprog-body').insertBefore(frame, $('.dbprog-wait'));
    // unsaved: the program said the document changed since it was opened or last kept here (its «dirty» event)
    let ready = false, closed = false, unsaved = false, pending = new Map(), ids = 0, saving = null;
    const saveBtn = () => $('[data-act="save"]') || { disabled: true };
    const wait = (text, note) => { const w = $('.dbprog-wait'); if (!w) return; w.querySelector('b').textContent = text; if (note !== undefined) w.querySelector('span').textContent = note; };
    const post = (msg, transfer) => frame.contentWindow && frame.contentWindow.postMessage(Object.assign({ dbprog: key }, msg), '*', transfer || []);
    const call = (type, extra, ms) => new Promise((ok, no) => {
      const id = type + '-' + (++ids);
      pending.set(id, { ok, no });
      post(Object.assign({ type, id }, extra));
      setTimeout(() => { if (pending.has(id)) { pending.delete(id); no(new Error(p.en + ' did not answer')); } }, ms || 120000);
    });
    const failed = e => {
      const blocked = /Refused to compile|unsafe-eval|wasm-unsafe-eval|Content Security Policy|CompileError: WebAssembly/i.test(e);
      status(say('failed', { e: blocked ? say('blocked') : e }), 'bad'); wait(say('failed', { e: blocked ? say('blocked') : e }), '');
      const w = $('.dbprog-wait'); if (w) w.querySelector('.dbprog-meter').hidden = true;
    };
    const timer = setTimeout(() => { if (!ready && !closed) failed('it did not start in 300 s'); }, 300000);
    function onMessage(e) {
      if (e.source !== frame.contentWindow) return;
      const msg = e.data || {};
      if (msg.dbprog !== key) return;
      if (msg.type === 'loading') wait(say('loading'), msg.fromDevice ? '' : say('first', { mb: Math.round(m.size / 1e6) }));
      else if (msg.type === 'progress') { const i = layer.querySelector('.dbprog-meter i'); if (i) i.style.width = Math.min(100, Math.round(100 * msg.loaded / msg.total)) + '%'; }
      else if (msg.type === 'starting') { wait(say('starting')); const i = layer.querySelector('.dbprog-meter i'); if (i) i.style.width = '100%'; }
      else if (msg.type === 'ready') {
        ready = true; clearTimeout(timer);
        const w = $('.dbprog-wait'); if (w) w.remove();
        status(say('opening'));
        if (opts.bytes) { const copy = opts.bytes.slice().buffer; post({ type: 'open', name: opts.name, bytes: copy }, [copy]); }
        const pb = $('[data-act="place"]'); if (pb) pb.disabled = false;

        // the hint, once the document is open — unless something was said meanwhile (a save done within these 1.5 s kept «saved»
        // only until this fired: seen when the program opens from the device and the save is quick)
        setTimeout(() => { if (!closed && !saving && $('.dbprog-status').textContent === say('opening')) status((opts.hint || (p.hint ? p.hint[lang] : say('ready'))) + (opts.note ? ' ' + opts.note : '')); }, opts.bytes ? 1500 : 0);
        try { frame.focus(); } catch (err) { /* the frame takes focus on its first click */ }
      } else if (msg.type === 'dirty') { if (msg.dirty !== false) { unsaved = true; saveBtn().disabled = false; } }
      else if (msg.type === 'touched') unsaved = true;
      else if (msg.type === 'failed') failed(msg.error || 'unknown');
      else if (msg.type === 'executed' || msg.type === 'inspected') {
        const q = pending.get(msg.id);
        if (q) { pending.delete(msg.id); msg.error ? q.no(new Error(msg.error)) : q.ok(msg.result); }
      } else if (msg.type === 'save' && msg.bytes) {
        if (!unsaved && p.host === 'page') { status(say('nothing')); return; }   // Ctrl+S with nothing changed: the file as it is stays
        status(say('saving')); saveBtn().disabled = true;
        saving = Promise.resolve().then(() => opts.onSave({ name: msg.name || opts.name, bytes: new Uint8Array(msg.bytes) }))
          .then(said => { unsaved = false; status(typeof said === 'string' ? said : say('saved', { n: msg.name || opts.name }) + (p.afterSave ? ' ' + p.afterSave[lang] : ''), 'good'); },
                e => { saveBtn().disabled = false; status(say('saveFail', { e: (e && e.message) || e }), 'bad'); })
          .finally(() => { saving = null; });
      }
    }
    addEventListener('message', onMessage);
    function close(force) {
      if (closed) return;
      if (!force && unsaved) {
        const ask = document.createElement('div');
        ask.className = 'dbprog-ask';
        ask.innerHTML = `<div><b>${esc(say('unsaved'))}</b><div class="row"><button class="btn sm pri" data-a="save">${esc(say('save'))}</button>`
          + `<button class="btn sm" data-a="discard">${esc(say('discard'))}</button><button class="btn sm ghost" data-a="back">${esc(say('back'))}</button></div></div>`;
        $('.dbprog-body').appendChild(ask);
        ask.querySelector('[data-a="back"]').onclick = () => ask.remove();
        ask.querySelector('[data-a="discard"]').onclick = () => close(true);
        ask.querySelector('[data-a="save"]').onclick = async () => { ask.remove(); await save(); if (!unsaved) close(true); };
        return;
      }
      closed = true; clearTimeout(timer);
      removeEventListener('message', onMessage);
      for (const q of pending.values()) q.no(new Error('closed'));
      layer.remove();
      if (current === handle) current = null;
      try { if (opts.onClose) opts.onClose(); } catch (e) { /* the page's own failure */ }
    }
    // «Save»: the program saves (in host mode the file comes back as a «save» message), and the page keeps it as a new version.
    async function save() {
      if (!ready || !unsaved) return;
      status(say('saving')); saveBtn().disabled = true;                   // said at once: the program answers with the file
      try { await call('execute', { command: 'file.save', params: {} }); }
      catch (e) { saveBtn().disabled = false; status(say('saveFail', { e: e.message }), 'bad'); return; }
      for (let i = 0; i < 300 && !saving && unsaved; i++) await new Promise(r => setTimeout(r, 100));
      if (saving) await saving;
      else if (unsaved && !closed) { saveBtn().disabled = false; status(say('noFile'), 'bad'); }    // no file in 30 s: never a silent wait
    }
    if ($('[data-act="save"]')) saveBtn().onclick = () => save();
    // a question asked in the program's own layer (the page's drawer is under it): → true (yes) | false (no)
    // pictures: [{src, caption}] shown side by side above the buttons (the file before and after)
    function ask(text, yes, no, pictures) {
      return new Promise(done => {
        const a = document.createElement('div');
        a.className = 'dbprog-ask';
        const pics = (pictures || []).map(x => `<figure style="margin:0;display:flex;flex-direction:column;gap:4px;align-items:center;min-width:0;flex:1"><img alt="" src="${esc(x.src)}" style="max-width:100%;max-height:42vh;border:1px solid var(--line,#1c2838);background:#fff"><figcaption class="small" style="text-align:center">${esc(x.caption || '')}</figcaption></figure>`).join('');
        a.innerHTML = `<div style="max-width:min(820px,94vw)"><b>${esc(text)}</b>${pics ? `<div class="row" style="flex-wrap:nowrap;gap:10px;align-items:flex-start">${pics}</div>` : ''}<div class="row"><button class="btn sm pri" data-a="yes">${esc(yes)}</button><button class="btn sm ghost" data-a="no">${esc(no)}</button></div></div>`;
        $('.dbprog-body').appendChild(a);
        a.querySelector('[data-a="yes"]').onclick = () => { a.remove(); done(true); };
        a.querySelector('[data-a="no"]').onclick = () => { a.remove(); done(false); };
      });
    }
    if ($('[data-act="place"]')) $('[data-act="place"]').onclick = () => { if (!ready) return; const copy = opts.place.bytes.slice().buffer;
      post({ type: 'place', name: opts.place.name, bytes: copy }, [copy]); unsaved = true; status(say('placed'), 'good'); };
    layer.querySelector('[data-act="close"]').onclick = () => close(false);
    const handle = { app, close, save, ask, execute: (command, params) => call('execute', { command, params: params || {} }), inspect: () => call('inspect', {}, 20000),
                     get ready() { return ready; }, get unsaved() { return unsaved; } };
    current = handle;
    return handle;
  }

  /* ── what the photo program saves, as a picture a PDF page can carry: its Ctrl+S gives a Photoshop file — the picture it shows is the
     merged image every PSD/PSB carries after its layers (Adobe Photoshop File Formats Specification: the header, three sections
     skipped by their lengths, then the image data, raw or PackBits per row, one plane per channel; from the v2 workshop's psd.js);
     PNG and JPEG as they are; anything else the browser can draw, as PNG. → {bytes: Uint8Array, kind: 'png' | 'jpeg'} */
  function psdComposite(b) {
    const v = new DataView(b.buffer, b.byteOffset, b.byteLength), fail = why => { throw new Error('the photo program\'s file: ' + why); };
    if (b.length < 26 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== '8BPS') fail('not a PSD');
    const version = v.getUint16(4), channels = v.getUint16(12), height = v.getUint32(14), width = v.getUint32(18), depth = v.getUint16(22);
    const mode = { 1: 'gray', 3: 'rgb', 4: 'cmyk' }[v.getUint16(24)];
    if ((version !== 1 && version !== 2) || !mode || (depth !== 8 && depth !== 16) || !width || !height || width * height > 200e6) fail('a kind of PSD not read here');
    let o = 26;
    const need = n => { if (o + n > b.length) fail('cut short'); };
    const skip32 = () => { need(4); o += 4 + v.getUint32(o); };
    skip32(); skip32();                                               // colour mode data, image resources
    if (version === 2) { need(8); o += 8 + v.getUint32(o) * 2 ** 32 + v.getUint32(o + 4); } else skip32();   // layers and masks
    need(2);
    const comp = v.getUint16(o); o += 2;
    const colour = mode === 'gray' ? 1 : mode === 'rgb' ? 3 : 4, planes = Math.min(channels, colour + 1), rowBytes = width * depth / 8, plane = [];
    if (comp === 0) for (let c = 0; c < planes; c++) { need(rowBytes * height); plane[c] = b.subarray(o, o + rowBytes * height); o += rowBytes * height; }
    else if (comp === 1) {
      const cb = version === 2 ? 4 : 2, counts = [];
      need(channels * height * cb);
      for (let i = 0; i < channels * height; i++) counts.push(cb === 4 ? v.getUint32(o + i * 4) : v.getUint16(o + i * 2));
      o += channels * height * cb;
      for (let c = 0; c < planes; c++) {
        const out = new Uint8Array(rowBytes * height);
        for (let y = 0; y < height; y++) {
          const n = counts[c * height + y]; need(n);
          let i = o, j = y * rowBytes; const end = j + rowBytes, to = o + n;      // PackBits
          while (i < to && j < end) { const k = b[i++] << 24 >> 24; if (k >= 0) { for (let q = 0; q <= k && j < end; q++) out[j++] = b[i++]; } else if (k !== -128) { const x = b[i++]; for (let q = 0; q < 1 - k && j < end; q++) out[j++] = x; } }
          o += n;
        }
        plane[c] = out;
      }
    } else fail('compression ' + comp);
    const rgba = new Uint8ClampedArray(width * height * 4), at = depth === 8 ? (q, i) => q[i] : (q, i) => q[i * 2];
    for (let i = 0, n = width * height; i < n; i++) {
      let r, g, bl;
      if (mode === 'gray') r = g = bl = at(plane[0], i);
      else if (mode === 'rgb') { r = at(plane[0], i); g = at(plane[1], i); bl = at(plane[2], i); }
      else { const k = at(plane[3], i) / 255; r = at(plane[0], i) * k; g = at(plane[1], i) * k; bl = at(plane[2], i) * k; }
      rgba[i * 4] = r; rgba[i * 4 + 1] = g; rgba[i * 4 + 2] = bl; rgba[i * 4 + 3] = planes > colour ? at(plane[colour], i) : 255;
    }
    return { width, height, rgba };
  }
  async function picture(bytes) {
    const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return { bytes: b, kind: 'png' };
    if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return { bytes: b, kind: 'jpeg' };
    let bmp;
    if (b[0] === 0x38 && b[1] === 0x42 && b[2] === 0x50 && b[3] === 0x53) { const im = psdComposite(b); bmp = await createImageBitmap(new ImageData(im.rgba, im.width, im.height)); }
    else bmp = await createImageBitmap(new Blob([b]));
    const c = document.createElement('canvas'); c.width = bmp.width; c.height = bmp.height;
    const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0);
    const blob = await new Promise(r => c.toBlob(r, 'image/png'));
    if (!blob) throw new Error('the picture could not be written');
    return { bytes: new Uint8Array(await blob.arrayBuffer()), kind: 'png' };
  }

  root.DBPROG = { PROGRAMS, available, forFile, title, open, frameDoc, picture };
})(window);
