/* Dead-end crawler — in-page helpers (injected with add_init_script before the app loads).
   Owned by tools/qa/deadend_crawler.py; nothing here changes the app's behaviour: it only reads the DOM and
   records side effects (clipboard, window.open, share, print, storage writes) so the crawler can tell
   "a toast and nothing else" from "a toast after the link was copied". __QA_CFG__ is replaced by the crawler. */
(function () {
  if (window.__qa) return;
  var CFG = __QA_CFG__;
  var qa = window.__qa = { fx: [], lastMut: 0, toastFired: [], els: [], baseFixed: [], snaps: {}, noise: new Set() };

  /* ---- side-effect recorders ---- */
  function rec(kind, detail) { try { qa.fx.push({ kind: kind, detail: String(detail || '').slice(0, 160) }); } catch (e) {} }
  try {
    var wo = window.open; window.open = function (u) { rec('new_window', u); return null; };
    window.print = function () { rec('print', ''); };
    if (navigator.clipboard) {
      var wt = navigator.clipboard.writeText && navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function (t) { rec('clipboard', t); return Promise.resolve(); };
      navigator.clipboard.write = function () { rec('clipboard', '(data)'); return Promise.resolve(); };
    }
    navigator.share = function (d) { rec('share', d && (d.url || d.title)); return Promise.resolve(); };
    var ec = document.execCommand.bind(document);
    document.execCommand = function (c) { if (/copy/i.test(c)) rec('clipboard', 'execCommand'); return ec.apply(null, arguments); };
    var si = Storage.prototype.setItem;
    Storage.prototype.setItem = function (k, v) {
      if (!CFG.storage_noise || !new RegExp(CFG.storage_noise).test(k)) rec('stored', k);
      return si.apply(this, arguments);
    };
    var ri = Storage.prototype.removeItem;
    Storage.prototype.removeItem = function (k) { rec('stored', '-' + k); return ri.apply(this, arguments); };
  } catch (e) {}
  if (CFG.seed) {   /* deterministic demo: seeded Math.random (mulberry32) */
    var s = CFG.seed >>> 0;
    Math.random = function () { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function startMO() {
    if (qa.mo || !document.body) return;
    qa.mo = new MutationObserver(function (list) {
      var now = performance.now(), real = false;
      for (var i = 0; i < list.length; i++) {
        var t = list[i].target, el = t.nodeType === 1 ? t : t.parentElement;
        if (el && el.closest && el.closest(CFG.toast_sel)) {
          var te = el.closest(CFG.toast_sel); qa.toastFired.push(te);
        } else real = true;
      }
      if (real) qa.lastMut = now;
    });
    qa.mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startMO); else startMO();

  /* ---- helpers ---- */
  function h32(s) { var h = 0x811c9dc5; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0).toString(36); }
  qa.h32 = h32;
  var STATE_CLS = new RegExp(CFG.state_classes, 'i');
  var NOISE_CLS = new RegExp(CFG.noise_classes, 'i');
  function clsOf(el, dropState) {
    var c = typeof el.className === 'string' ? el.className : (el.getAttribute && el.getAttribute('class')) || '';
    return c.split(/\s+/).filter(function (x) { return x && !NOISE_CLS.test(x) && !(dropState && STATE_CLS.test(x)); }).sort().join('.');
  }
  function norm(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
  function visible(el) {
    if (!el.getClientRects().length) return false;
    var r = el.getBoundingClientRect(); if (r.width < 4 || r.height < 4) return false;
    var cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.pointerEvents === 'none') return false;
    if (parseFloat(cs.opacity) < 0.05) return false;
    var p = el.parentElement, n = 0;   // faded-out ancestors (closed dialogs that stay in the DOM)
    while (p && n < 12) { var ps = getComputedStyle(p); if (parseFloat(ps.opacity) < 0.05 || ps.visibility === 'hidden') return false; p = p.parentElement; n++; }
    return true;
  }
  qa.visible = visible;
  function isToast(el) { return !!(el.closest && el.closest(CFG.toast_sel)); }
  /* the innermost position:fixed ancestor that is not part of the page's resting state (qa.baseFixed) — a dialog */
  function overlayOf(el) { var p = el; while (p && p !== document.body) { if (qa.baseFixed.indexOf(p) < 0 && getComputedStyle(p).position === 'fixed') return p; p = p.parentElement; } return null; }
  function fixedRoot(el) { var p = el; while (p && p !== document.body) { if (getComputedStyle(p).position === 'fixed') return p; p = p.parentElement; } return null; }
  function pathOf(el) {
    var parts = []; while (el && el !== document.documentElement) { var p = el.parentElement; if (!p) break; parts.unshift(Array.prototype.indexOf.call(p.children, el)); el = p; }
    return '/' + parts.join('/');
  }
  qa.pathOf = pathOf;

  /* ---- interactive candidates (document-wide, visible) ---- */
  var SEL = CFG.cand_sel;
  qa.cands = function () {
    var content = document.querySelector(CFG.content_sel), seen = new Set(), list = [];
    var nodes = Array.prototype.slice.call(document.querySelectorAll(SEL));
    /* elements made clickable from script (cursor:pointer, outermost) — "cards" without an onclick attribute */
    var root = document.body, all = root.getElementsByTagName('*');
    for (var i = 0; i < all.length; i++) {
      var e = all[i];
      if (e.offsetParent === null && getComputedStyle(e).position !== 'fixed') continue;
      if (getComputedStyle(e).cursor !== 'pointer') continue;
      var pe = e.parentElement; if (pe && getComputedStyle(pe).cursor === 'pointer') continue;
      nodes.push(e);
    }
    nodes.forEach(function (e) {
      if (seen.has(e)) return; seen.add(e);
      if (e.closest('svg') && e.tagName.toLowerCase() !== 'svg') { /* inner svg parts */ if (!e.closest('a,button,[onclick]')) return; else return; }
      if (CFG.ignore_sel && e.closest(CFG.ignore_sel)) return;
      if (!visible(e)) return;
      list.push(e);
    });
    /* document order */
    list.sort(function (a, b) { return a === b ? 0 : (a.compareDocumentPosition(b) & 4 ? -1 : 1); });
    var out = [], keyN = {}, skeyN = {};
    qa.els = list;
    list.forEach(function (e, i) {
      var tag = e.tagName.toLowerCase(), oc = (e.getAttribute('onclick') || '').slice(0, 120), href = e.getAttribute('href') || '';
      var text = norm(e.innerText || e.value || e.getAttribute('aria-label') || e.getAttribute('title') || e.getAttribute('alt') || '').slice(0, 80);
      var cls = clsOf(e, true);
      var region = isToast(e) ? 'toast' : (content && content.contains(e) ? 'content' : 'chrome');
      if (region !== 'toast' && overlayOf(e)) region = 'overlay';
      var key = tag + '|' + e.id + '|' + cls + '|' + oc + '|' + href + '|' + text.slice(0, 40);
      var skey = tag + '|' + e.id + '|' + cls + '|' + oc + '|' + href + '|' + (e.getAttribute('role') || '') + '|' + (e.getAttribute('data-tab') || '');
      keyN[key] = (keyN[key] || 0); skeyN[skey] = (skeyN[skey] || 0);
      var par = e.parentElement;
      var lines = (e.innerText || '').split('\n').map(norm).filter(function (x) { return x.length >= 3; });
      var cardlike = lines.length >= 2 && (e.innerText || '').length > 30 && tag !== 'select';
      /* family = elements that look alike. Cards ignore their click handler: a grid where only some cards have an onclick
         is one family (that is exactly the "only the first two cards work" bug). Buttons keep the handler's shape. */
      var fam = tag + '|' + cls + '|' + (cardlike ? '*' : oc.replace(/'[^']*'|"[^"]*"|\d+/g, '_')) + '|' + href.replace(/\d+/g, '_') + '|' + (par ? par.tagName + '.' + clsOf(par, true) : '');
      var title = '';
      if (cardlike) {
        /* the card's name: the first title-like element with words in it (not the "90 %" score badge) */
        var t = Array.prototype.find.call(e.querySelectorAll(CFG.title_sel), function (x) { return /[A-Za-z\u0600-\u06ff]{3}/.test(x.innerText || ''); });
        title = norm(t ? t.innerText : '').split('\n')[0] || lines.filter(function (l) { return /[A-Za-z\u0600-\u06ff]{3}/.test(l); })[0] || lines[0] || '';
      }
      var rawc = typeof e.className === 'string' ? e.className : (e.getAttribute('class') || '');
      var active = /(^|\s)(active|on|selected|checked|current|sel)(\s|$)/.test(rawc) || e.getAttribute('aria-selected') === 'true' ||
                   e.getAttribute('aria-pressed') === 'true' || e.getAttribute('aria-checked') === 'true' || !!e.getAttribute('aria-current') || !!e.checked;
      var dis = !!(e.disabled || e.getAttribute('aria-disabled') === 'true' || /\bdisabled\b/.test(e.className || ''));
      out.push({ i: i, tag: tag, id: e.id, cls: cls.slice(0, 80), oc: oc, href: href, text: text, key: key, occ: keyN[key]++, skey: skey, socc: skeyN[skey]++,
                 fam: fam, region: region, cardlike: cardlike, title: title.slice(0, 80), disabled: dis,
                 active: active, ctext: cardlike ? norm(e.innerText).slice(0, 600) : '',
                 target: e.getAttribute('target') || '', type: e.getAttribute('type') || '', role: e.getAttribute('role') || '' });
    });
    return out;
  };
  qa.find = function (key, occ) {
    var c = qa.cands(), n = 0;
    for (var i = 0; i < c.length; i++) if (c[i].key === key) { if (n === occ) return c[i]; n++; }
    return null;
  };
  /* a point inside the element that really hits it (not a nested button, not something on top) */
  qa.point = function (i) {
    var el = qa.els[i]; if (!el) return { err: 'gone' };
    el.scrollIntoView({ block: 'center', inline: 'center' });
    var r = el.getBoundingClientRect(), xs = [0.5, 0.2, 0.8, 0.1, 0.9], ys = [0.5, 0.25, 0.75, 0.1, 0.9], hit0 = null;
    for (var a = 0; a < ys.length; a++) for (var b = 0; b < xs.length; b++) {
      var x = r.left + r.width * xs[b], y = r.top + r.height * ys[a];
      if (x < 0 || y < 0 || x >= innerWidth || y >= innerHeight) continue;
      var h = document.elementFromPoint(x, y); if (!hit0) hit0 = h;
      if (!h) continue;
      if (h === el) return { x: x, y: y };
      if (el.contains(h)) {
        /* where a person would click: the centre, unless a separate real control (a button, link, field) sits there —
           a wrapper whose inner label carries the handler (role=button div around an onclick span) is clicked on the label */
        var inner = h.closest(SEL + ',[style*="cursor: pointer"]');
        if (!inner || inner === el || !el.contains(inner)) return { x: x, y: y };
        if (!/^(BUTTON|A|INPUT|SELECT|TEXTAREA|LABEL|SUMMARY)$/.test(inner.tagName)) return { x: x, y: y };
        continue;
      }
    }
    var d = hit0 ? (hit0.tagName.toLowerCase() + (hit0.id ? '#' + hit0.id : '') + (hit0.className && typeof hit0.className === 'string' ? '.' + hit0.className.split(' ')[0] : '')) : 'off-screen';
    return { err: 'covered by ' + d };
  };
  /* an empty field next to the control (a send/post button whose text box is empty) */
  qa.emptyField = function (i) {
    var el = qa.els[i], p = el, n = 0;
    while (p && p !== document.body && n++ < 5) {
      p = p.parentElement; if (!p) break;
      var f = Array.prototype.find.call(p.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=file]):not([type=button]):not([type=submit]),textarea,[contenteditable=true],[contenteditable=""]'),
        function (x) { return x.getClientRects().length && !norm(x.value !== undefined ? x.value : x.innerText); });
      if (f) return f.tagName.toLowerCase() + (f.placeholder ? ' "' + f.placeholder.slice(0, 40) + '"' : '');
      if (p.matches('form,[role=dialog],.modal,.card,.post,section')) break;
    }
    return '';
  };
  qa.selfPath = function (i) { var el = qa.els[i]; return el ? pathOf(el) : ''; };

  /* ---- DOM snapshot (own data of every visible element) and diff ---- */
  qa.snap = function (name) {
    var content = document.querySelector(CFG.content_sel), map = new Map(), fixed = [];
    var vwA = innerWidth * innerHeight;
    function walk(el, path, region) {
      var tag = el.tagName;
      if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'NOSCRIPT' || tag === 'TEMPLATE' || tag === 'LINK' || tag === 'META' || tag === 'svg') return;
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || (el.offsetParent === null && tag !== 'BODY' && cs.position !== 'fixed')) { map.set(path, region + '\u0001H'); return; }
      if (region !== 'toast' && isToast(el)) region = 'toast';
      else if (el === content) region = 'content';
      if (cs && cs.position === 'fixed' && region !== 'toast') {
        var r = el.getBoundingClientRect();
        if (r.width * r.height >= CFG.overlay_min_area * vwA && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0.05) {
          if (qa.baseFixed.indexOf(el) < 0) { region = 'overlay'; }
          fixed.push(el);
        } else if (cs.visibility === 'hidden' || parseFloat(cs.opacity) <= 0.05) { map.set(path, region + '\u0001F'); return; }
      }
      var s = tag + '#' + el.id + '.' + clsOf(el, false);
      for (var k = 0; k < el.attributes.length; k++) {
        var at = el.attributes[k]; if (at.name === 'style' || at.name === 'class' || at.name.indexOf('data-qa') === 0) continue;
        s += '|' + at.name + '=' + at.value.slice(0, 200);
      }
      var st = el.style; if (st) s += '|' + st.display + st.visibility + (st.opacity === '0' ? 'o0' : '') + st.maxHeight + (st.height === '0px' ? 'h0' : '');
      for (var c = el.firstChild; c; c = c.nextSibling) if (c.nodeType === 3) { var tv = c.nodeValue.trim(); if (tv) s += '|' + tv.slice(0, 200); }
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') s += '|v=' + String(el.value).slice(0, 100) + (el.checked ? '|on' : '');
      map.set(path, region + '\u0001' + h32(s));
      var ch = el.children;
      for (var j = 0; j < ch.length; j++) walk(ch[j], path + '/' + j, region);
    }
    walk(document.body, '/1', 'chrome');
    qa.snaps[name] = { map: map, fixed: fixed, url: location.href, view: qa.view(), focus: document.activeElement };
    return map.size;
  };
  qa.learnNoise = function (a, b) {
    var A = qa.snaps[a].map, B = qa.snaps[b].map, n = 0;
    B.forEach(function (v, k) { if (A.get(k) !== v) { qa.noise.add(k); n++; } });
    A.forEach(function (v, k) { if (!B.has(k)) { qa.noise.add(k); n++; } });
    return n;
  };
  qa.diff = function (a, b, selfPath) {
    var A = qa.snaps[a].map, B = qa.snaps[b].map, regions = {}, sample = [], n = 0, self = 0;
    function add(k, v) {
      if (qa.noise.has(k)) return;
      var reg = v.split('\u0001')[0]; regions[reg] = (regions[reg] || 0) + 1; n++;
      if (selfPath && (k === selfPath || k.indexOf(selfPath + '/') === 0)) self++;
      if (sample.length < 6) sample.push(k);
    }
    B.forEach(function (v, k) { var av = A.get(k); if (av !== v) add(k, av || v); });
    A.forEach(function (v, k) { if (!B.has(k)) add(k, v); });
    return { n: n, regions: regions, self: self, sample: sample };
  };
  qa.setBaseFixed = function () { qa.snap('__base'); qa.baseFixed = qa.snaps.__base.fixed.slice(); return qa.baseFixed.length; };
  /* overlays visible in snapshot b that were not in a, with content measurements */
  qa.newOverlays = function (a, b) {
    var A = qa.snaps[a].fixed, out = [];
    qa.snaps[b].fixed.forEach(function (el) { if (A.indexOf(el) < 0 && qa.baseFixed.indexOf(el) < 0 && el.isConnected) out.push(el); });
    out = out.filter(function (el) { return !out.some(function (o) { return o !== el && o.contains(el); }); });
    return out.map(function (el) { return qa.measure(el); });
  };
  qa.goneOverlays = function (a, b) {
    var B = qa.snaps[b].fixed; return qa.snaps[a].fixed.filter(function (el) { return B.indexOf(el) < 0 && qa.baseFixed.indexOf(el) < 0; }).length;
  };
  qa.measure = function (root) {
    var txt = norm(root.innerText || ''), btnChars = 0, buttons = 0;
    var ints = Array.prototype.filter.call(root.querySelectorAll('button,a[href],[role=button],[onclick]'), function (b) { return b.getClientRects().length; });
    ints.forEach(function (b) { if (!ints.some(function (o) { return o !== b && o.contains(b); })) { btnChars += norm(b.innerText).length; buttons++; } });
    var inputs = Array.prototype.filter.call(root.querySelectorAll('input:not([type=hidden]):not([type=button]):not([type=submit]):not([type=file]),textarea,select,[contenteditable=true],[contenteditable=""]'), function (x) { return x.getClientRects().length; }).length;
    var media = Array.prototype.filter.call(root.querySelectorAll('img,video,canvas,iframe,svg'), function (m) { var r = m.getBoundingClientRect(); return r.width * r.height > 6000; }).length;
    var listMax = 0;
    Array.prototype.forEach.call(root.querySelectorAll('*'), function (p) {
      if (p.children.length < 3) return;
      var by = {};
      Array.prototype.forEach.call(p.children, function (c) {
        if (c.matches('input,select,textarea') || !c.getClientRects().length) return;   /* hidden sub-panels do not count */
        /* a list item carries a sentence or several lines — header chips ("3,800 members") do not count */
        var ct = norm(c.innerText), nl = (c.innerText || '').split('\n').filter(function (x) { return norm(x).length >= 3; }).length;
        if (ct.length < 40 && nl < 2) return;
        var k = c.tagName + '.' + clsOf(c, true); by[k] = (by[k] || 0) + 1;
      });
      for (var k in by) if (by[k] > listMax) listMax = by[k];
    });
    var t = root.querySelector('h1,h2,h3,[class*=title],[class*=name],[class*=hdr],[class*=head]');
    var title = norm(t ? t.innerText : '').split('\n')[0] || txt.split(' ').slice(0, 6).join(' ');
    var btnTexts = ints.map(function (b) { return norm(b.innerText).slice(0, 30); }).filter(Boolean).slice(0, 12);
    var box = root, guard = 0;
    while (guard++ < 12) {
      var kids = Array.prototype.filter.call(box.children, function (k) { return k.getClientRects().length && norm(k.innerText).length; });
      if (kids.length !== 1 || norm(kids[0].innerText).length < 0.9 * norm(box.innerText).length) break;
      box = kids[0];
    }
    var r = box.getBoundingClientRect();
    /* the panel's own words: text that is not inside a control */
    var bt = [], tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), tn;
    while ((tn = tw.nextNode())) {
      var pe = tn.parentElement; if (!pe || !norm(tn.nodeValue)) continue;
      if (pe.closest('button,a[href],[role=button],[onclick],select,option,script,style')) continue;
      if (!pe.getClientRects().length) continue;
      bt.push(norm(tn.nodeValue));
    }
    return { body_text: bt.join(' ').slice(0, 3000), chars: txt.length, body_chars: Math.max(0, txt.length - btnChars), inputs: inputs, buttons: buttons, list_max: listMax, media: media,
             title: title.slice(0, 80), text: txt.slice(0, 2500), button_texts: btnTexts, id: root.id || '', cls: clsOf(root, true).slice(0, 60),
             area: Math.round(r.width * r.height / (innerWidth * innerHeight) * 100) };
  };
  qa.view = function () { try { return __QA_VIEW__; } catch (e) { return 'view-error'; } };
  qa.toastText = function () {
    var t = Array.prototype.filter.call(document.querySelectorAll(CFG.toast_sel), function (e) { return e.getClientRects().length && norm(e.innerText); });
    return t.map(function (e) { return norm(e.innerText).slice(0, 120); }).join(' / ');
  };
  qa.focusInfo = function () {
    var a = document.activeElement; if (!a || a === document.body) return '';
    if (a.matches('input,textarea,[contenteditable=true],select')) return a.tagName.toLowerCase() + (a.placeholder ? ' "' + a.placeholder.slice(0, 40) + '"' : '');
    return '';
  };
  qa.text = function (n) { var c = document.querySelector(CFG.content_sel) || document.body; return norm(c.innerText).slice(0, n || 4000); };
  /* a large fixed panel covering the middle of the page in a "fresh" state: try its close control */
  qa.blocking = function () {
    var c = document.querySelector(CFG.content_sel); if (!c) return '';
    var r = c.getBoundingClientRect(), x = Math.max(r.left, 0) + Math.min(r.width, innerWidth) / 2, y = Math.min(Math.max(r.top, 0) + 200, innerHeight / 2);
    var h = document.elementFromPoint(x, y); if (!h) return '';
    var f = fixedRoot(h); if (!f || f.contains(c) || f.querySelector(CFG.content_sel)) return '';
    var fr = f.getBoundingClientRect(); if (fr.width * fr.height < 0.3 * innerWidth * innerHeight) return '';
    if (f.closest('.topbar,#sidebar,.sidebar')) return '';
    var name = f.tagName.toLowerCase() + (f.id ? '#' + f.id : '') + ' "' + norm(f.innerText).slice(0, 50) + '"';
    var close = Array.prototype.find.call(f.querySelectorAll('button,[onclick],[role=button],[class*=close],[aria-label]'), function (b) {
      return b.getClientRects().length && (/close|dismiss/i.test((b.className || '') + ' ' + (b.getAttribute('aria-label') || '')) || /^(×|✕|x|close|إغلاق)$/i.test(norm(b.innerText)));
    });
    if (close) { close.click(); return 'closed ' + name; }
    return 'could not close ' + name;
  };
  /* soft reset helper: close every open dialog (fixed panel not in the resting state) with its own close control */
  qa.closeOverlays = function () {
    var n = 0, els = document.body.getElementsByTagName('*');
    var open = [];
    for (var i = 0; i < els.length; i++) {
      var e = els[i]; if (qa.baseFixed.indexOf(e) >= 0) continue;
      if (!e.getClientRects().length) continue;
      var cs = getComputedStyle(e); if (cs.position !== 'fixed' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) continue;
      var r = e.getBoundingClientRect(); if (r.width * r.height < CFG.overlay_min_area * innerWidth * innerHeight) continue;
      if (isToast(e)) continue;
      open.push(e);
    }
    open.reverse().forEach(function (f) {
      var close = Array.prototype.find.call(f.querySelectorAll('button,[onclick],[role=button],[class*=close],[aria-label]'), function (b) {
        return b.getClientRects().length && (/close|dismiss/i.test((typeof b.className === 'string' ? b.className : '') + ' ' + (b.getAttribute('aria-label') || '')) || /^(×|✕|x|close|cancel|إغلاق|إلغاء)$/i.test(norm(b.innerText)));
      });
      if (close) { close.click(); n++; }
    });
    return n;
  };
  /* fresh-state check: the resting snapshot ("base") is kept by the crawler and compared after every reset */
  qa.exportSnap = function (name) { var o = {}; qa.snaps[name].map.forEach(function (v, k) { if (v.split('\u0001')[0] !== 'toast') o[k] = v; }); return o; };
  qa.loadSnap = function (name, obj) { var m = new Map(); for (var k in obj) m.set(k, obj[k]); qa.snaps[name] = { map: m, fixed: [], url: '', view: '' }; return m.size; };
  qa.addNoise = function (list) { list.forEach(function (k) { qa.noise.add(k); }); return qa.noise.size; };
  qa.noiseList = function () { return Array.from(qa.noise); };
  /* paths that differ between two snapshots (toasts and known noise excluded) */
  qa.diffPaths = function (a, b, limit) {
    var A = qa.snaps[a].map, B = qa.snaps[b].map, out = [];
    function tst(v) { return v && v.split('\u0001')[0] === 'toast'; }
    B.forEach(function (v, k) { if (out.length < limit && A.get(k) !== v && !qa.noise.has(k) && !(tst(v) && (!A.has(k) || tst(A.get(k))))) out.push(k); });
    A.forEach(function (v, k) { if (out.length < limit && !B.has(k) && !qa.noise.has(k) && !tst(v)) out.push(k); });
    return out;
  };
  qa.atBase = function () { qa.snap('cur'); var d = qa.diffPaths('base', 'cur', 8); return { n: d.length, sample: d, view: qa.view() }; };
  qa.fingerprint = function () { var c = qa.cands(); return h32(c.map(function (x) { return x.key; }).join('\n')) + ':' + c.length; };
})();
