/* The preview of documents on the preparation page (the owner, 15/11: «المستندات و هي بتترفع و تتمسح تظهر بريڤيو ايه اللي بيحصل»):
   each file's pages, small, beside its card; and while a file is worked on, what is happening to it — the step, the page being read,
   and the very pictures Claude is given (boot.js «db-pictures»). Also the small first page of every document in «المكتب».
   It only looks: nothing it does changes how a file is read, placed or prepared — it draws nothing while the scan reader reads or
   draws pictures for Claude (DBOCR.busy()), so those are drawn as they were before there was a preview.
   Pages are drawn in the page with pdf.js where the scan reader's files are (ui/assets/ocr.js drawPages: the browser edition), one
   at a time and only when in view; elsewhere the engine draws them (…/pages/<n>.png). A file over 80 MB, or one that is not a PDF
   or a picture (Word, Excel…), shows its kind instead.

   DBPV.mount(root, dossierId)            fills every [data-pv] (a file's pages) and [data-pvthumb] (its first page) under root
   DBPV.file(key, file)                    a file not stored yet (the new-dossier wizard's): drawn from the browser's own copy
   DBPV.now(docId, {text, page, pages, picture, caption})   what is happening to a document now
   DBPV.end(docId)                         its work is over */
(function (root) {
  'use strict';
  const MAX_BYTES = 80 * 1048576, STRIP = 4;
  const urls = new Map();                 // `${doc}:${page}:${width}` → object URL of the drawn page
  const files = new Map();                // doc → Promise<File> (the last 24)
  const given = new Map();                // key → File: files in the page, not stored yet
  const jobs = [];
  let running = false, dossier = null, styled = false;
  const ar = () => (document.documentElement.lang || 'ar') !== 'en';
  const say = (a, e) => (ar() ? a : e);
  const drawable = name => /\.(pdf|png|jpe?g|tiff?|gif|bmp|webp)$/i.test(String(name || ''));
  const inPage = () => !!(root.DBOCR && root.DBOCR.drawPages);

  const STYLE = `.pv{display:flex;flex-direction:column;gap:6px;margin-top:6px}
.pv-strip{display:flex;gap:6px;flex-wrap:wrap;align-items:flex-start}
.pv-th{display:block;width:64px;min-height:40px;border:1px solid var(--line,#1c2838);border-radius:4px;background:#fff;object-fit:contain}
.pv-th.on{outline:2px solid var(--accent,#a78bfa);outline-offset:1px}
.pv-more{font-size:11.5px;color:var(--muted,#8c9bb0);align-self:center}
.pv-kind{display:grid;place-items:center;width:64px;height:84px;border:1px solid var(--line,#1c2838);border-radius:4px;font:600 11px ui-monospace,monospace;color:var(--muted,#8c9bb0);background:var(--surface-2,#131c2a)}
.pv-now{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;padding:8px;border:1px solid color-mix(in srgb,var(--accent,#a78bfa) 45%,transparent);border-radius:10px;background:color-mix(in srgb,var(--accent,#a78bfa) 7%,transparent)}
.pv-pic{position:relative;flex:0 0 auto;width:min(300px,100%);border:1px solid var(--line,#1c2838);border-radius:6px;overflow:hidden;background:#fff}
.pv-pic img{display:block;width:100%}
.pv-pic i{position:absolute;inset-inline:0;height:3px;top:0;background:var(--accent,#a78bfa);box-shadow:0 0 12px var(--accent,#a78bfa);animation:pvscan 2.2s linear infinite}
@keyframes pvscan{from{top:0}to{top:100%}}
@media (prefers-reduced-motion: reduce){.pv-pic i{animation:none;top:50%}}
.pv-say{flex:1 1 180px;min-width:0;display:flex;flex-direction:column;gap:6px}
.pv-step{font-weight:600}
.pv-cap{font-size:12px;color:var(--muted,#8c9bb0)}
.pv-bar{height:5px;border-radius:3px;background:var(--line,#1c2838);overflow:hidden}
.pv-bar b{display:block;height:100%;width:0;background:var(--accent,#a78bfa);transition:width .25s}`;
  function style() { if (styled) return; const s = document.createElement('style'); s.textContent = STYLE; document.head.appendChild(s); styled = true; }

  function fileOf(doc, name) {
    if (given.has(doc)) return Promise.resolve(given.get(doc));
    if (files.has(doc)) return files.get(doc);
    const p = fetch(`/api/dossiers/${dossier}/documents/${doc}/file`, { headers: { 'X-DB': '1' } }).then(async r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const b = await r.blob();
      if (b.size > MAX_BYTES) throw new Error('too large to draw here');
      return new File([b], name || 'document', { type: b.type || (/\.pdf$/i.test(name || '') ? 'application/pdf' : '') });
    });
    files.set(doc, p);
    p.catch(() => files.delete(doc));
    if (files.size > 24) files.delete(files.keys().next().value);
    return p;
  }
  // pages of one document, drawn once and kept as pictures; → [{page, url}] and how many pages it has
  async function pictures(doc, name, pages, width) {
    const want = pages.filter(k => !urls.has(`${doc}:${k}:${width}`));
    let count = null;
    if (want.length) {
      if (inPage() && (given.has(doc) || dossier)) {
        const f = await fileOf(doc, name);
        const r = await root.DBOCR.drawPages(f, want, width);
        count = r.pages;
        for (const d of r.drawn) {
          const blob = await new Promise(res => d.canvas.toBlob(res, 'image/jpeg', 0.82));
          if (blob) urls.set(`${doc}:${d.page}:${width}`, URL.createObjectURL(blob));
        }
      } else if (!given.has(doc) && dossier) {
        for (const k of want) urls.set(`${doc}:${k}:${width}`, `/api/dossiers/${dossier}/documents/${doc}/pages/${k}.png?dpi=${Math.max(12, Math.round(width / 8.27))}`);
      }
    }
    return { count, got: pages.filter(k => urls.has(`${doc}:${k}:${width}`)).map(k => ({ page: k, url: urls.get(`${doc}:${k}:${width}`) })) };
  }
  function queue(fn) {
    return new Promise((ok, no) => { jobs.push({ fn, ok, no }); pump(); });
  }
  async function pump() {
    if (running) return;
    running = true;
    while (jobs.length) {
      while (root.DBOCR && root.DBOCR.busy && root.DBOCR.busy() > 0) await new Promise(r => setTimeout(r, 150));   // a reading draws: wait
      const j = jobs.shift();
      try { j.ok(await j.fn()); } catch (e) { j.no(e); }
    }
    running = false;
  }
  const kindTile = name => { const m = /\.([a-z0-9]{1,5})$/i.exec(String(name || '')); return `<span class="pv-kind" title="${esc(name)}">${esc((m ? m[1] : '?').toUpperCase())}</span>`; };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  async function fillStrip(el) {
    const doc = el.dataset.pv, name = el.dataset.pvname || '', strip = el.querySelector('.pv-strip');
    if (!strip || strip.dataset.done) return;
    strip.dataset.done = '1';
    if (!drawable(name)) { strip.innerHTML = kindTile(name); return; }
    const total = +(el.dataset.pvpages || 0);
    const pages = Array.from({ length: Math.min(STRIP, total || STRIP) }, (_, i) => i + 1);
    try {
      const r = await queue(() => pictures(doc, name, pages, 128));
      if (!r.got.length) { strip.innerHTML = kindTile(name); return; }        // nothing to draw it with here
      const n = r.count || total || r.got.length;
      el.dataset.pvpages = String(n);
      strip.innerHTML = r.got.filter(g => !n || g.page <= n).map(g => `<img class="pv-th" data-pvpage="${g.page}" alt="${esc(say('صفحة ' + g.page, 'Page ' + g.page))}" src="${g.url}">`).join('')
        + (n > STRIP ? `<span class="pv-more">+${n - STRIP} ${say('صفحة', n - STRIP === 1 ? 'page' : 'pages')}</span>` : '');
      strip.querySelectorAll('img').forEach(i => { i.onerror = () => { strip.innerHTML = kindTile(name); }; });   // a page the engine could not draw
    } catch (e) { strip.innerHTML = kindTile(name); }
  }
  async function fillThumb(img) {
    const doc = img.dataset.pvthumb, name = img.dataset.pvname || '';
    if (img.dataset.done) return;
    img.dataset.done = '1';
    if (!drawable(name)) { img.outerHTML = kindTile(name); return; }
    try { const r = await queue(() => pictures(doc, name, [1], 128)); if (r.got[0]) { img.onerror = () => { img.outerHTML = kindTile(name); }; img.src = r.got[0].url; } else img.outerHTML = kindTile(name); }
    catch (e) { img.outerHTML = kindTile(name); }
  }
  let seen = null;
  function mount(rootEl, dossierId) {
    if (!rootEl) return;
    style();
    if (dossierId && dossierId !== dossier) { dossier = dossierId; files.clear(); }
    const all = [...rootEl.querySelectorAll('[data-pv]'), ...rootEl.querySelectorAll('img[data-pvthumb]')];
    if (!('IntersectionObserver' in root)) { all.forEach(x => (x.dataset.pv ? fillStrip(x) : fillThumb(x))); return; }
    if (!seen) seen = new IntersectionObserver(es => es.forEach(e => { if (!e.isIntersecting) return; seen.unobserve(e.target); (e.target.dataset.pv ? fillStrip : fillThumb)(e.target); }), { rootMargin: '200px' });
    all.forEach(x => seen.observe(x));
  }

  // ── what is happening to a document now ──────────────────────────────────────────────────────────────────────────────────
  const live = new Map();                  // doc → {page, pages, picture url, caption}
  function panel(doc) {
    const host = document.querySelector(`[data-pv="${CSS.escape(doc)}"]`);
    if (!host) return null;
    let p = host.querySelector('.pv-now');
    if (!p) {
      p = document.createElement('div');
      p.className = 'pv-now';
      p.setAttribute('role', 'status');
      p.innerHTML = '<div class="pv-pic" hidden><img alt=""><i></i></div><div class="pv-say"><span class="pv-step"></span><span class="pv-cap"></span><div class="pv-bar" hidden><b></b></div></div>';
      host.insertBefore(p, host.firstChild);
    }
    return { host, p };
  }
  async function now(doc, o) {
    o = o || {};
    style();
    const st = Object.assign(live.get(doc) || {}, o.text != null ? { text: o.text } : {});
    live.set(doc, st);
    const it = panel(doc);
    if (!it) return;
    const { host, p } = it;
    p.hidden = false;
    if (o.text != null) p.querySelector('.pv-step').textContent = o.text;
    if (o.page) {
      st.page = o.page; st.pages = o.pages || st.pages;
      const bar = p.querySelector('.pv-bar');
      if (st.pages) { bar.hidden = false; bar.querySelector('b').style.width = Math.min(100, Math.round(100 * st.page / st.pages)) + '%'; }
      host.querySelectorAll('.pv-th').forEach(x => x.classList.toggle('on', +x.dataset.pvpage === +o.page));
      p.querySelector('.pv-cap').textContent = say(`صفحة ${o.page}${st.pages ? ' من ' + st.pages : ''}`, `Page ${o.page}${st.pages ? ' of ' + st.pages : ''}`);
      if (!o.picture && !st.picture) {                                    // the page being read, as it is
        const name = host.dataset.pvname || '';
        if (drawable(name)) queue(() => pictures(doc, name, [o.page], 420)).then(r => { if (r.got[0] && !(live.get(doc) || {}).picture) show(p, r.got[0].url); }).catch(() => {});
      }
    }
    if (o.picture) {                                                      // the picture Claude is given now
      if (st.picture) URL.revokeObjectURL(st.picture);
      st.picture = URL.createObjectURL(o.picture);
      show(p, st.picture);
      if (o.caption) { st.caption = o.caption; p.querySelector('.pv-cap').textContent = o.caption; }
    }
  }
  function show(p, url) { const box = p.querySelector('.pv-pic'); box.hidden = false; box.querySelector('img').src = url; }
  function end(doc) {
    const st = live.get(doc);
    if (st && st.picture) URL.revokeObjectURL(st.picture);
    live.delete(doc);
    const host = document.querySelector(`[data-pv="${CSS.escape(doc)}"]`);
    if (!host) return;
    const p = host.querySelector('.pv-now');
    if (p) p.remove();
    host.querySelectorAll('.pv-th.on').forEach(x => x.classList.remove('on'));
  }
  // a card drawn again while its document is being worked on: what was shown comes back
  function restore(rootEl) {
    for (const [doc, st] of live) {
      if (!rootEl.querySelector(`[data-pv="${CSS.escape(doc)}"]`)) continue;
      const pic = st.picture, cap = st.caption;
      now(doc, { text: st.text || '', page: st.page, pages: st.pages });
      const it = panel(doc);
      if (it && pic) show(it.p, pic);
      if (it && pic && cap) it.p.querySelector('.pv-cap').textContent = cap;
    }
  }

  function file(key, f) { if (f && f.size <= MAX_BYTES) given.set(key, f); }
  root.DBPV = { mount, now, end, restore, file, _pictures: pictures };
})(window);
