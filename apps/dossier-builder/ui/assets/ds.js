/* Shared runtime for the Dossier Builder pages: DOM helpers, API, toast, drawer, theme, icons. No dependencies. */
(function(){
  'use strict';
  const $ = (s, el=document) => el.querySelector(s);
  const $$ = (s, el=document) => [...el.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const bdi = s => `<bdi>${esc(s)}</bdi>`;
  const store = {
    get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } },
    set(k, v){ try{ localStorage.setItem(k, v); }catch(e){} },
  };

  /* ---- icons (24x24 strokes) */
  const P = {
    home:'<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    layers:'<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5"/>',
    folder:'<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    branch:'<path d="M6 3v12"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
    checklist:'<path d="m3 7 2 2 4-4"/><path d="m3 17 2 2 4-4"/><path d="M13 6h8M13 12h8M13 18h8"/>',
    database:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    tree:'<rect x="3" y="3" width="7" height="5" rx="1"/><rect x="14" y="10" width="7" height="5" rx="1"/><rect x="14" y="17" width="7" height="4" rx="1"/><path d="M6.5 8v11h7.5M6.5 12.5h7.5"/>',
    shield:'<path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Z"/><path d="m9 12 2 2 4-4"/>',
    package:'<path d="M12 22V12"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7Z"/>',
    download:'<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 21h16"/>',
    upload:'<path d="M12 21V9"/><path d="m7 14 5-5 5 5"/><path d="M4 3h16"/>',
    history:'<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 7v5l3 2"/>',
    compass:'<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/>',
    file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon:'<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
    globe:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    users:'<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M22 20a7 7 0 0 0-5-6.7"/>',
    logout:'<path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M13 3h6v18h-6"/>',
    key:'<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l2 2M14 9l2 2"/>',
    alert:'<path d="M12 3 2 20h20L12 3Z"/><path d="M12 10v4M12 17h.01"/>',
    check:'<path d="m5 12 5 5L20 7"/>',
    x:'<path d="M6 6l12 12M18 6 6 18"/>',
    chevron:'<path d="m9 6 6 6-6 6"/>',
    arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
    external:'<path d="M14 4h6v6"/><path d="M20 4 10 14"/><path d="M19 13v7H4V5h7"/>',
    sparkles:'<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/><path d="M19 17l.8 2.2L22 20l-2.2.8L19 23l-.8-2.2L16 20l2.2-.8L19 17Z"/>',
    wrench:'<path d="M14.7 6.3a4 4 0 0 0 5 5L22 9a6 6 0 0 1-8.5 7.3L7 22.8 1.2 17 7.7 10.5A6 6 0 0 1 15 2Z"/>',
    mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    lock:'<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    activity:'<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    building:'<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2M10 21v-3h4v3"/>',
    book:'<path d="M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 0-3 3Z"/><path d="M4 4v16a3 3 0 0 1 3-3h12"/>',
    grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>',
    flask:'<path d="M9 3h6M10 3v6L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9V3"/><path d="M7 15h10"/>',
    cpu:'<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    link:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    repeat:'<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    pen:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    zap:'<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    table:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
    scan:'<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
    pill:'<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
    stamp:'<path d="M5 22h14"/><path d="M19.3 17.6a1 1 0 0 1-1 1.4H5.7a1 1 0 0 1-1-1.4l1.3-4A1 1 0 0 1 7 13h10a1 1 0 0 1 1 .6Z"/><path d="M10 13V8.2A3 3 0 1 1 14 8.2V13"/>',
    bell:'<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21h4"/>',
    trash:'<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m6 6 1 15h10l1-15"/><path d="M10 11v6M14 11v6"/>',
    undo:'<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  };
  const icon = (n, s=18, cls='') => `<svg class="ic ${cls}" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]||P.info}</svg>`;

  /* ---- API: errors carry {code,en,ar} from the server; X-DB marks a deliberate request (CSRF) */
  /* a thin «working» bar while the engine answers (after a third of a second), so no button looks dead */
  let busyN=0, busyT=null;
  function busy(d){ busyN=Math.max(0, busyN+d); const el=document.getElementById('busy');
    if(busyN&&!busyT&&!(el&&!el.hidden)) busyT=setTimeout(()=>{ busyT=null; if(!busyN||!document.body) return;
      const b=document.getElementById('busy')||document.body.appendChild(Object.assign(document.createElement('div'),{id:'busy'}));
      b.setAttribute('role','status'); b.setAttribute('aria-label', document.documentElement.lang==='en'?'Working…':'شغّال…'); b.hidden=false; }, 350);
    if(!busyN){ clearTimeout(busyT); busyT=null; if(el) el.hidden=true; } }
  /* nothing fails silently: an error the page did not expect is shown, at most once every few seconds */
  let lastErr=0;
  function surface(msg){ const now=Date.now(); if(now-lastErr<4000) return; lastErr=now;
    try{ toast((document.documentElement.lang==='en'?'Something went wrong: ':'حصل خطأ: ')+String(msg).slice(0,200)); }catch(e){} }
  window.addEventListener('error', e=>{ if(e&&e.message&&!/ResizeObserver|Script error/.test(e.message)) surface(e.message+(e.lineno?` (${e.lineno})`:'')); });
  window.addEventListener('unhandledrejection', e=>{ const r=e&&e.reason, m=r&&(r.message||r.code)||(typeof r==='string'?r:''); if(m&&m!=='auth'&&!/AbortError/.test(String(r&&r.name))) surface(m); });
  async function api(path, opt={}, root='/api'){
    busy(1);
    try{ return await apiCall(path, opt, root); } finally{ busy(-1); }
  }
  async function apiCall(path, opt, root){
    opt = Object.assign({}, opt);
    opt.headers = Object.assign({'X-DB':'1'}, opt.headers||{});
    if(opt.json!==undefined){ opt.body = JSON.stringify(opt.json); opt.headers['content-type']='application/json'; delete opt.json; }
    const r = await fetch(root + path, opt);
    if(r.status===401){ location.href='/login'; throw new Error('auth'); }
    const ct = r.headers.get('content-type') || '';
    const body = ct.includes('json') ? await r.json() : null;
    if(!r.ok){ const d = body && body.detail || {}; const lang = document.documentElement.lang || 'ar';
      const e = new Error(d[lang] || d.en || d.ar || r.statusText); e.detail = d; e.status = r.status; throw e; }
    return body;
  }

  /* ---- toast + drawer (elements #toast, #drawer, #dTitle, #dBody, #dClose, #scrim) */
  function toast(msg, ms){ const el=$('#toast'); if(!el) return; el.textContent=msg; el.hidden=false; clearTimeout(toast.h); toast.h=setTimeout(()=>el.hidden=true, ms||3800); }
  function openDrawer(title, html, wide){ $('#dTitle').textContent=title; $('#dBody').innerHTML=html; $('#drawer').classList.toggle('wide', !!wide);
    $('#drawer').hidden=false; $('#scrim').hidden=false;
    setTimeout(()=>{ const f=$('#dBody').querySelector('input:not([type=checkbox]),select,textarea'); (f||$('#dClose')).focus(); }, 30); }
  /* a question asked in the page itself (a browser dialog does not open inside an embedded page): resolves true when the person
     confirms. opts.typed = a text the person must type first (deleting for good). Closing the panel answers nothing. */
  function confirmBox(title, html, okLabel, opts){ opts=opts||{}; return new Promise(done=>{
    openDrawer(title, `<div class="stack gap-s">${html}${opts.typed?`<label class="f"><span>${esc(opts.typedLabel||'')}</span><input type="text" id="cfType" dir="auto" autocomplete="off"></label>`:''}
      <div class="row"><button class="btn ${opts.danger?'danger':'pri'}" id="cfOk" ${opts.typed?'disabled':''}>${esc(okLabel)}</button><button class="btn ghost" id="cfNo">${esc(opts.cancel||'Cancel')}</button></div></div>`);
    let answered=false; const end=v=>{ if(answered) return; answered=true; closeDrawer(); done(v); };
    $('#cfOk').onclick=()=>end(true); $('#cfNo').onclick=()=>end(false);
    if(opts.typed){ const i=$('#cfType'); i.oninput=()=>{ $('#cfOk').disabled=i.value.trim()!==String(opts.typed).trim(); }; }
  }); }
  /* a small delete: the button asks once more before it acts */
  function twoStep(btn, sure, act){ btn.onclick=()=>{ if(btn.dataset.sure){ delete btn.dataset.sure; act(); return; }
    const old=btn.innerHTML; btn.dataset.sure='1'; btn.classList.add('danger'); btn.textContent=sure;
    setTimeout(()=>{ if(btn.isConnected&&btn.dataset.sure){ delete btn.dataset.sure; btn.classList.remove('danger'); btn.innerHTML=old; } }, 5000); }; }
  function closeDrawer(){ const d=$('#drawer'); if(!d) return; d.hidden=true; $('#scrim').hidden=true; d.classList.remove('wide'); }
  function wireChrome(){
    const c=$('#dClose'), s=$('#scrim'); if(c) c.onclick=closeDrawer; if(s) s.onclick=closeDrawer;
    document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeDrawer(); });
  }

  /* ---- theme (dark by default: an instrument panel) */
  const theme = {
    init(){ const t = store.get('db.theme') || 'dark'; document.documentElement.dataset.theme = t; theme.paint(); },
    toggle(){ const r=document.documentElement; r.dataset.theme = r.dataset.theme==='dark' ? 'light' : 'dark'; store.set('db.theme', r.dataset.theme); theme.paint(); },
    paint(){ const b=$('#theme'); if(b) b.innerHTML = icon(document.documentElement.dataset.theme==='dark' ? 'sun' : 'moon', 17); },
  };

  /* ---- small renderers */
  const ring = (pct, cls='') => `<div class="ring ${cls}" style="--v:${Math.max(0,Math.min(100,+pct||0))}"><b>${Math.round(+pct||0)}%</b></div>`;
  const meter = (pct, cls='') => `<div class="meter ${cls}"><i style="width:${Math.max(0,Math.min(100,+pct||0))}%"></i></div>`;
  const fmtDate = (d, lang) => d ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(d) ? d+'T00:00:00' : d).toLocaleDateString(lang==='ar'?'ar-EG':'en-GB',{year:'numeric',month:'short',day:'numeric'}) : '—';
  const fmtTs = (ts, lang) => new Date(ts*1000).toLocaleString(lang==='ar'?'ar-EG':'en-GB');
  const pct = (a, b) => b ? Math.round(100*a/b) : 0;

  /* every document type the engine reads, old formats and new. The bytes decide what a file really is: this list only serves the
     pickers and the filters, and a name with no extension is let through for the engine to look inside. */
  const DOC_EXT = ['pdf','docx','docm','dotx','dotm','doc','dot','rtf','odt','xlsx','xlsm','xltx','xls','xlt','ods','csv','tsv','pptx','ppsx','potx','ppt','pps','odp',
    'txt','md','htm','html','xml','json','svg'];
  const IMG_EXT = ['jpg','jpeg','jfif','jpe','png','gif','bmp','dib','tif','tiff','webp','heic','heif','avif','jp2','j2k','jpx','jpf','pbm','pgm','ppm','pnm','psd','ico','pcx','tga'];      // images of every kind
  DOC_EXT.push(...IMG_EXT);
  const IMG_RX = new RegExp('\\.(' + IMG_EXT.join('|') + ')$', 'i');
  const DOC_RX = new RegExp('\\.(' + DOC_EXT.join('|') + ')$', 'i');
  const isDoc = name => DOC_RX.test(name||'') || !/\.[A-Za-z0-9]{1,6}$/.test(name||'');
  const ARCH_EXT = ['zip','rar','7z','tar','tgz','gz','bz2','xz'];                   // compressed files: opened, and the documents inside taken
  const DOC_ACCEPT = DOC_EXT.concat(ARCH_EXT).map(e => '.' + e).join(',') + ',application/pdf,image/*';
  document.addEventListener('DOMContentLoaded', () => { const p = document.getElementById('picker'); if(p && !p.accept) p.accept = DOC_ACCEPT; });
  window.DS = { $, $$, esc, bdi, store, icon, api, toast, confirmBox, twoStep, DOC_EXT, DOC_RX, DOC_ACCEPT, IMG_EXT, IMG_RX, ARCH_EXT, isDoc, openDrawer, closeDrawer, wireChrome, theme, ring, meter, fmtDate, fmtTs, pct };
})();
