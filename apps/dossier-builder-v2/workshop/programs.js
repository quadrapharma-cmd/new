// The real programs inside the workshop (Part 2, step 2.7): the Word program (WordCraft) and the PDF program (PdfCraft), built from
// their source (tools/craft/build.mjs), each in a frame of its own page beside the workshop (programs/<app>.html, written by
// workshop/build.mjs). A page opened from the disk is its own origin, so the program runs in its page's own document («page» host
// mode: the program's messages are events on its canvas) and a small relay there passes them to the workshop and back with
// postMessage. The workshop hands the program a document (open), keeps every file the program saves as a new version of it (save),
// and can ask it to work by its commands (execute; inspect: what the program has open) — the Word program turning a Word file into a
// PDF without a person.
export const PROGRAMS = {
  wordcraft: { ar: 'برنامج الـ Word', canvas: 'wordcraft_canvas', kinds: ['docx', 'doc'] },
  pdfcraft: { ar: 'برنامج الـ PDF', canvas: 'pdfcraft', kinds: ['pdf'] },
};
export const programFor = kind => Object.keys(PROGRAMS).find(k => PROGRAMS[k].kinds.includes(kind)) || null;
export const available = app => (globalThis.DB_PROGRAMS || []).includes(app);

export function createPrograms({ base = 'programs/', mount }) {
  const frames = {};                               // app → {iframe, ready: Promise, pending: Map}
  const listeners = new Set();
  let seq = 0;
  addEventListener('message', e => {
    const app = Object.keys(frames).find(a => frames[a].iframe.contentWindow === e.source);
    if (!app) return;
    const m = e.data || {}, f = frames[app];
    if (m.type === `${app}:ready`) f.markReady();
    else if (m.type === `${app}:failed`) f.markFailed(m.error || 'the program could not start');
    else if (m.type === `${app}:executed` || m.type === `${app}:inspected`) { const p = f.pending.get(m.id); if (p) { f.pending.delete(m.id); m.error ? p.no(new Error(m.error)) : p.ok(m.result); } }
    else if (m.type === `${app}:save` || m.type === `${app}:dirty`) for (const l of listeners) { try { l({ app, ...m }); } catch { /* a listener's own failure */ } }
  });
  function frame(app) {
    if (frames[app]) return frames[app];
    const iframe = document.createElement('iframe');
    iframe.title = PROGRAMS[app].ar;
    iframe.src = `${base}${app}.html?webgl&control`;
    const f = { iframe, pending: new Map() };
    f.ready = new Promise((ok, no) => { f.markReady = ok; f.markFailed = e => no(Object.assign(new Error(e), { code: 'program-failed' })); });
    setTimeout(() => f.markFailed('the program did not start in 180 s'), 180000);
    mount(iframe, app);
    frames[app] = f;
    return f;
  }
  const call = (app, type, extra = {}, ms = 120000) => new Promise((ok, no) => {
    const f = frames[app], id = `${type}-${++seq}`;
    f.pending.set(id, { ok, no });
    f.iframe.contentWindow.postMessage({ type: `${app}:${type}`, id, ...extra }, '*');
    setTimeout(() => { if (f.pending.has(id)) { f.pending.delete(id); no(new Error(`${PROGRAMS[app].ar} did not answer`)); } }, ms);
  });
  return {
    frame: app => frame(app).iframe,
    onMessage: fn => { listeners.add(fn); return () => listeners.delete(fn); },
    async open(app, name, bytes) {
      const f = frame(app);
      await f.ready;
      f.iframe.contentWindow.postMessage({ type: `${app}:open`, name, bytes }, '*');
    },
    execute: (app, command, params = {}) => frames[app].ready.then(() => call(app, 'execute', { command, params })),
    inspect: app => frames[app].ready.then(() => call(app, 'inspect', {}, 20000)),
    // A Word file as a PDF, by the Word program: opened, waited on until it is the open document, exported.
    async wordToPdf(name, bytes, firstText = '') {
      const app = 'wordcraft';
      const got = new Promise((ok, no) => {
        const off = this.onMessage(m => { if (m.app === app && m.type === `${app}:save` && /\.pdf$/i.test(m.name || '')) { off(); ok(new Uint8Array(m.bytes)); } });
        setTimeout(() => { off(); no(new Error('the Word program gave no PDF in 120 s')); }, 120000);
      });
      await this.open(app, name, bytes);
      const want = String(firstText).replace(/\s+/g, ' ').trim().slice(0, 40);
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 400));
        const doc = await this.inspect(app).catch(() => null);
        const texts = (doc?.blocks || []).slice(0, 6).map(b => String(b.text || '').replace(/\s+/g, ' '));
        if (doc && (!want || texts.some(t => t.includes(want) || want.includes(t.slice(0, 40))))) break;
      }
      await this.execute(app, 'file.exportPdf', {});
      return got;
    },
  };
}

// The relay in a program's own page (programs/<app>.html), and its loader: the program's glue as a module made from a blob, its
// WebAssembly from the gzip in base64 its script hands over. Written into the page by workshop/build.mjs.
export function programPage(app, { canvas, title }) {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title><style>html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#e6e6e6}
canvas{position:absolute;inset:0;width:100%;height:100%;display:block;outline:none}#loading{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#555;font:15px Tahoma,system-ui,sans-serif}</style></head>
<body><canvas id="${canvas}" data-host="page"></canvas><div id="loading">بيفتح ${title}…</div>
<script>window.__dbAssets={};window.__dbAsset=function(n,v){window.__dbAssets[n]=v;};</script>
<script src="${app}/glue.js"></script><script src="${app}/wasm.js"></script>
<script>
(function () {
  var app = ${JSON.stringify(app)}, canvas = document.getElementById(${JSON.stringify(canvas)});
  function up(type, detail) { var m = { type: app + ':' + type }; for (var k in (detail || {})) m[k] = detail[k]; parent.postMessage(m, '*'); }
  ['ready', 'save', 'dirty', 'failed'].forEach(function (t) { canvas.addEventListener(app + ':' + t, function (e) { if (t === 'ready') document.getElementById('loading').remove(); up(t, e.detail); }); });
  addEventListener('message', function (e) {
    if (e.source !== parent) return;
    var m = e.data || {};
    if (m.type === app + ':open') canvas.dispatchEvent(new CustomEvent(app + ':open', { detail: { name: m.name, bytes: m.bytes } }));
    var api = window[app];
    function answer(kind, p) { Promise.resolve(p).then(function (r) { up(kind, { id: m.id, result: JSON.parse(JSON.stringify(r === undefined ? null : r)) }); }, function (err) { up(kind, { id: m.id, error: String(err && err.message || err) }); }); }
    if (m.type === app + ':execute') answer('executed', api ? api.execute(m.command, m.params || {}) : Promise.reject(new Error('no command API')));
    if (m.type === app + ':inspect') answer('inspected', api ? api.docInspect() : Promise.reject(new Error('no command API')));
  });
  (async function () {
    try {
      var bin = atob(window.__dbAssets[app + '/wasm']), gz = new Uint8Array(bin.length);
      for (var i = 0; i < bin.length; i++) gz[i] = bin.charCodeAt(i);
      delete window.__dbAssets[app + '/wasm'];
      var wasm = new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
      var mod = await import(URL.createObjectURL(new Blob([window.__dbAssets[app + '/glue']], { type: 'text/javascript' })));
      await mod.default({ module_or_path: wasm });
    } catch (err) { up('failed', { error: String(err && err.message || err) }); }
  })();
})();
</script></body></html>`;
}
