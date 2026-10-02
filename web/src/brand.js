/* Drugbox brand layer — A1..A7
   A1 hexagon motif · A2 pharma icon set · A3 illustrations · A4 hex loader
   A5 dark mode · A6 Ramadan / Eid theme · A7 design tokens
   Pure add-on: it never changes page logic, only presentation. */
(function () {
  var HEX = __HEX__, ILL = __ILL__;

  /* ── A2: icon set (24×24, 1.8 stroke, rounded) ── */
  var P = {
    home: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
    cart: 'M3 4h2l2.4 11.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.5L21 8H6|c10 20 1.3|c17 20 1.3',
    handshake: 'M2 11l4-4 3.5 1.2L12 7l2.5 1.2L18 7l4 4|M6 13l4 4a1.5 1.5 0 0 0 2.1 0l.4-.4|M9 15l2 2|M12 12l3.5 3.5a1.5 1.5 0 0 0 2.1-2.1L14 9.8|M2 11l3 3M22 11l-3 3',
    chat: 'M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z',
    bell: 'M6 9a6 6 0 1 1 12 0c0 6.5 3 8 3 8H3s3-1.5 3-8|M10 20a2 2 0 0 0 4 0',
    search: 'c11 11 7|M20 20l-3.5-3.5',
    bookmark: 'M6 3h12v18l-6-4-6 4z',
    camera: 'M3 9a2 2 0 0 1 2-2h2l2-3h6l2 3h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z|c12 13.5 3.5',
    clip: 'M20 11.5l-8.5 8.5a5 5 0 0 1-7-7L13 4.5a3.3 3.3 0 0 1 4.7 4.7l-8.5 8.5a1.7 1.7 0 0 1-2.4-2.4L14.5 7.6',
    box: 'M21 8l-9-5-9 5v8l9 5 9-5z|M3 8l9 5 9-5|M12 13v8',
    briefcase: 'M4 7h16a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z|M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2|M3 13h18',
    thumb: 'M7 11v9H4v-9z|M7 11l4-7a2 2 0 0 1 2 2v4h5.5a2 2 0 0 1 2 2.3l-1.2 6.5a2 2 0 0 1-2 1.7H7',
    comment: 'M4 5h16v11H9l-5 4z',
    repost: 'M17 3l3 3-3 3|M4 12V9a3 3 0 0 1 3-3h13|M7 21l-3-3 3-3|M20 12v3a3 3 0 0 1-3 3H4',
    star: 'M12 3l2.8 5.8 6.2.9-4.5 4.4 1 6.3L12 17.5 6.5 20.4l1-6.3L3 9.7l6.2-.9z',
    ban: 'c12 12 9|M5.6 5.6l12.8 12.8',
    pen: 'M4 20h4L19 9a2.1 2.1 0 0 0-3-3L5 17z|M14 7l3 3',
    scroll: 'M8 3h10a2 2 0 0 1 2 2v12a4 4 0 0 1-4 4H6a2 2 0 0 1-2-2v-2h12v2|M8 3v14|M11 8h6M11 12h6',
    trophy: 'M8 4h8v5a4 4 0 0 1-8 0z|M8 6H5a3 3 0 0 0 3 4|M16 6h3a3 3 0 0 1-3 4|M12 13v4|M8 21h8|M10 17h4l1 4H9z',
    seal: 'M12 2l8.7 5v10L12 22l-8.7-5V7z|M8.5 12l2.5 2.5 4.5-5',
    warning: 'M12 3l10 18H2z|M12 10v5|M12 18h.01',
    clipboard: 'M7 4h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z|M9 3h6v3H9z|M9 11h6M9 15h6M9 19h3',
    flask: 'M9 3h6|M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3|M7.5 15h9',
    basket: 'M4 9h16l-1.6 10.2a2 2 0 0 1-2 1.8H7.6a2 2 0 0 1-2-1.8z|M9 9l3-5 3 5|M10 13v4M14 13v4',
    doc: 'M7 3h7l5 5v13H7z|M14 3v5h5|M10 13h6M10 17h6',
    factory: 'M3 21V11l6 3v-3l6 3V7h3V3h3v18z|M3 21h18|M7 17h2M12 17h2',
    gear: 'c12 12 3|M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1',
    tools: 'M14.5 6.5a4 4 0 0 0 5 5L12 19a2.1 2.1 0 0 1-3-3z|M5 3l3 3-1 3-3 1-3-3',
    cap: 'M2 9l10-5 10 5-10 5z|M6 11v5c3 2.5 9 2.5 12 0v-5|M22 9v5',
    users: 'c9 8 3|M3 20a6 6 0 0 1 12 0|c17 9 2.5|M16 14.2a5 5 0 0 1 5 5.8',
    user: 'c12 8 4|M4 21a8 8 0 0 1 16 0',
    chart: 'M4 20V10|M10 20V4|M16 20v-7|M3 20h18',
    plus: 'M12 5v14M5 12h14',
    megaphone: 'M3 10v4l11 5V5z|M14 8a4 4 0 0 1 0 8|M6 15l1 5h3l-1-4',
    microscope: 'M9 3l4 2-3 6-4-2z|M11 11a5 5 0 0 1 7 4|M5 21h14|M12 18h4',
    trend: 'M3 17l6-6 4 4 8-8|M15 7h6v6',
    crown: 'M3 8l4 4 5-7 5 7 4-4-2 11H5z',
    compass: 'c12 12 9|M15.5 8.5l-2 5-5 2 2-5z',
    sprout: 'M12 21v-9|M12 12c0-4 3-7 7-7 0 4-3 7-7 7z|M12 14c0-3-2-5-6-5 0 3 2 5 6 5z',
    target: 'c12 12 9|c12 12 5|c12 12 1',
    building: 'M5 3h14v18H5z|M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2|M10 21v-3h4v3',
    pill: 'M10.5 3.5a5 5 0 0 1 7 7l-7 7a5 5 0 0 1-7-7z|M7 10l7 7',
    globe: 'c12 12 9|M3 12h18|M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18',
    trash: 'M4 7h16|M9 7V4h6v3|M6 7l1 13h10l1-13',
    bolt: 'M13 2L4 14h7l-1 8 9-12h-7z',
    tag: 'M3 12V4h8l10 10-8 8z|c7.5 7.5 1.4',
    pin: 'M9 3h6l-1 6 3 3H7l3-3z|M12 12v9',
    spark: 'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6',
    moon: 'M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5z',
    sun: 'c12 12 4|M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
    palette: 'M12 3a9 9 0 0 0 0 18c1.2 0 2-.8 2-2 0-1.3 1-2 2-2h2a3 3 0 0 0 3-3 9 9 0 0 0-9-11z|c7.5 11.5 1|c10 7.5 1|c14.5 7.5 1',
    crescent: 'M15 3a9 9 0 1 0 6 13A7 7 0 0 1 15 3z',
    send: 'M22 2L11 13|M22 2l-7 20-4-9-9-4z',
    drop: 'M12 3c3.5 4.6 6 8 6 11.2a6 6 0 0 1-12 0C6 11 8.5 7.6 12 3z|M9.5 15a2.6 2.6 0 0 0 2.6 2.4'
  };
  function svg(name, cls) {
    var d = P[name]; if (!d) return '';
    return '<svg class="' + (cls || 'dx-svg') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + d.split('|').map(function (p) {
      if (p[0] === 'c') { var a = p.slice(1).split(' '); return '<circle cx="' + a[0] + '" cy="' + a[1] + '" r="' + a[2] + '"/>'; }
      return '<path d="' + p + '"/>';
    }).join('') + '</svg>';
  }
  window.dxIll = function (k) { return ILL[k] || ''; };
  window.dxIcon = function (n) { return '<span class="dx-ic">' + svg(n) + '</span>'; };
  var MAP = { '🏠': 'home', '🛒': 'cart', '🤝': 'handshake', '💬': 'chat', '🔔': 'bell', '🔍': 'search', '🔖': 'bookmark', '📷': 'camera', '📎': 'clip', '📦': 'box', '💼': 'briefcase',
    '👍': 'thumb', '🔄': 'repost', '⭐': 'star', '⛔': 'ban', '✍️': 'pen', '✍': 'pen', '📜': 'scroll', '🏆': 'trophy', '🏅': 'seal', '⚠️': 'warning', '⚠': 'warning', '📋': 'clipboard',
    '🟢': 'flask', '🟠': 'basket', '🏭': 'factory', '⚙️': 'gear', '⚙': 'gear', '🛠️': 'tools', '🛠': 'tools', '🎓': 'cap', '👥': 'users', '👤': 'user', '📊': 'chart', '➕': 'plus',
    '📢': 'megaphone', '📄': 'doc', '🔬': 'microscope', '📈': 'trend', '👑': 'crown', '🧭': 'compass', '🌱': 'sprout', '🎯': 'target', '🏢': 'building', '💊': 'pill', '⚗️': 'flask',
    '⚗': 'flask', '🧪': 'flask', '🌍': 'globe', '🗑️': 'trash', '🗑': 'trash', '⚡': 'bolt', '🆓': 'tag', '📌': 'pin', '✨': 'spark', '✉️': 'send', '✉': 'send' };
  var keys = Object.keys(MAP).sort(function (a, b) { return b.length - a.length; });
  var RX = new RegExp('(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')\uFE0F?', 'g');
  /* interface chrome only — posts, comments, messages and listings text are left alone */
  var CHROME = ['.tnb .icon', '.mb-btn', '.pact', '.content h1', '.sec-title', '.mb-flt', '.mb-tab', '.comp-tool', '.composer button', '.comp-act', '.post-actions button', '.pact-btn', '.sb-sec',
    '.jx-ic', '.jx-tool', '.jx-b', '.jx-tab', '#jx .mode-opt', '#jx .cf-tag', '#jx .sen-opt', '#jx .save-btn', '#jx .post-cta-title', '#jx .post-cta-btn', '#jx .role-badge', '#jx .hero-title',
    '#mkx .master-tab', '#mkx .cat-ic', '#mkx .plan', '#mkx .sort-opt', '#mkx .f-tag', '#mkx .sec-title', '#mkx .btn-save', '#mkx .btn-contact', '#mkx .btn-contact-gold', '#mkx .sp-ribbon', '#mkx .role-badge', '#mkx .uc-btn', '#mkx .ss-btn', '#mkx .js-btn', '#mkx .qt-btn',
    '#gx .cf-tag', '#gx .hero-btn', '#gx .sec-title', '#gx .gcard-btn', '#gx .sb-title', '#gx .create-link-ic', '#mx .tp-filter', '.dbk-hd b', '.dbk-btn', '.dg-band-k'].join(',');
  function iconify(root) {
    (root || document).querySelectorAll(CHROME).forEach(function (el) {
      if (el.closest('.post-body,.cmt-text,.bubble,.mx-bubble,textarea,input,[contenteditable]')) return;
      var sig = el.textContent.length; if (el.__dxSig === sig) return;           /* already scanned and unchanged */
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n, hits = [];
      while ((n = w.nextNode())) { RX.lastIndex = 0; if (RX.test(n.nodeValue) && !(n.parentElement && n.parentElement.closest('.dx-ic'))) hits.push(n); }
      hits.forEach(function (t) {
        var frag = document.createDocumentFragment(), s = t.nodeValue, last = 0, m; RX.lastIndex = 0;
        while ((m = RX.exec(s))) {
          if (m.index > last) frag.appendChild(document.createTextNode(s.slice(last, m.index)));
          var sp = document.createElement('span'); sp.className = 'dx-ic'; sp.innerHTML = svg(MAP[m[1]]); frag.appendChild(sp);
          last = m.index + m[0].length;
          if (s[last] === ' ' && s[last + 1] === ' ') last++;
        }
        if (last < s.length) frag.appendChild(document.createTextNode(s.slice(last)));
        t.parentNode.replaceChild(frag, t);
      });
      el.__dxSig = el.textContent.length;
    });
    /* verified ticks next to names become the hexagon seal */
    (root || document).querySelectorAll('.post-name span, #jx .jc-company span, #mkx .seller-name, #mkx .sc-provider span, .jx-b.honor').forEach(function (el) {
      if (el.querySelector('.dx-seal')) return;
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
      while ((n = w.nextNode())) {
        var i = n.nodeValue.indexOf('✓'); if (i < 0) continue;
        var after = n.splitText(i); after.nodeValue = after.nodeValue.slice(1);
        var sp = document.createElement('span'); sp.className = 'dx-ic dx-seal'; sp.title = 'Verified'; sp.innerHTML = svg('seal');
        after.parentNode.insertBefore(sp, after); break;
      }
    });
  }

  /* ── A1: hexagon avatars for companies (people stay round) ── */
  var COMPANY_RX = /pharma|industries|biotech|\blab\b|store|ltd|\bco\b|group|holding|laborator|trading|medical|healthcare|chemical/i;
  function isCompanyName(n) { n = String(n || ''); return !/^(dr|eng|prof)\.?\s/i.test(n) && COMPANY_RX.test(n); }
  function hexify(root) {
    var R = root || document;
    R.querySelectorAll('#jx .jcard .jc-logo').forEach(function (el) { var cand = el.closest('.jcard').querySelector('.role-badge.need'); el.classList.toggle('dx-hex', !cand); });
    R.querySelectorAll('.post-av[data-gp], .notif-item .notif-av, .sugg-av, .pending-card .post-av').forEach(function (el) {
      var id = +(el.getAttribute('data-gp') || 0), u = window.USERS && id ? window.USERS.find(function (x) { return x.id === id; }) : null;
      if (u) el.classList.toggle('dx-hex', isCompanyName(u.name));
    });
    R.querySelectorAll('#mkx .dc-buyer .av, #mkx .sp-seller .seller-av, #mkx .jc-logo').forEach(function (el) {
      var card = el.closest('.sponsored-card,.dcard,.jcard'); var name = card ? (card.querySelector('.seller-name,.dc-buyer,.jc-company span') || {}).textContent : '';
      el.classList.toggle('dx-hex', isCompanyName(name) || el.classList.contains('jc-logo'));
    });
  }

  /* ── A3: illustrations in empty states and hiring banners ── */
  function illustrate(root) {
    var R = root || document, page = document.body.getAttribute('data-page') || 'feed';
    R.querySelectorAll('.dbk-empty').forEach(function (el) {
      if (el.querySelector('.dx-ill')) return;
      var k = /market|companies/.test(page) ? 'shipping' : page === 'jobs' ? 'dossier' : page === 'groups' ? 'factory' : 'lab';
      el.insertAdjacentHTML('afterbegin', '<div class="dx-ill dx-ill-empty">' + ILL[k] + '</div>');
    });
    R.querySelectorAll('#jx .post-cta').forEach(function (el, i) {
      if (el.querySelector('.dx-ill')) return;
      var hunting = !!el.closest('#huntingView');
      el.insertAdjacentHTML('beforeend', '<div class="dx-ill dx-ill-cta" aria-hidden="true">' + ILL[hunting ? 'lab' : 'factory'] + '</div>');
    });
    R.querySelectorAll('#mkx .upgrade-cta').forEach(function (el) { if (!el.querySelector('.dx-ill')) el.insertAdjacentHTML('afterbegin', '<div class="dx-ill dx-ill-side" aria-hidden="true">' + ILL.shipping + '</div>'); });
  }

  /* ── A6: season banner in the home hero ── */
  function seasonal() {
    var hero = document.querySelector('.dg-hero'); if (!hero) return;
    var s = theme.season, ban = hero.parentNode.querySelector('.dx-season');
    if (s === 'standard') { if (ban) ban.remove(); return; }
    var txt = s === 'ramadan' ? ['RAMADAN KAREEM', 'Ramadan Kareem from everyone at Drugbox', 'Profiles show Ramadan working hours — plan calls and deliveries around them.']
                              : ['EID MUBARAK', 'Eid Mubarak from everyone at Drugbox', 'Wishing you and your teams a blessed Eid. Many offices close for the holiday — expect slower replies.'];
    var html = '<div class="dx-season-ic">' + svg('crescent', 'dx-svg dx-cres') + '<span class="dx-star s1"></span><span class="dx-star s2"></span><span class="dx-star s3"></span></div>' +
      '<div><span class="dx-season-k">' + txt[0] + '</span><div class="dx-season-t">' + txt[1] + '</div><div class="dx-season-s">' + txt[2] + '</div></div>';
    if (!ban) { ban = document.createElement('div'); ban.className = 'dx-season'; hero.parentNode.insertBefore(ban, hero); }
    if (ban.dataset.s !== s) { ban.innerHTML = html; ban.dataset.s = s; }
  }


  /* ── numbers → icons in hexagon tiles ── */
  function tile(name, extra) { return '<span class="dx-tile' + (extra ? ' ' + extra : '') + '">' + svg(name) + '</span>'; }
  var NAV_IC = { feed: 'home', network: 'users', messages: 'chat', notifs: 'bell', profile: 'user', saved: 'bookmark', groups: 'handshake', market: 'cart', jobs: 'briefcase', companies: 'building', training: 'cap' };
  var CAT_IC = { regulatory: 'doc', market: 'cart', innovation: 'flask', job: 'briefcase', general: 'megaphone' };
  var PAGE_IC = NAV_IC;
  function tiles() {
    document.querySelectorAll('.nl').forEach(function (el) {
      var num = el.querySelector('.nl-num'); if (!num || num.dataset.dx) return;
      var page = (el.id || '').replace('snl-', ''); num.innerHTML = tile(NAV_IC[page] || 'seal'); num.dataset.dx = '1';
    });
    document.querySelectorAll('.sh-row .sh-ic').forEach(function (el) {
      if (el.dataset.dx) return; var t = el.textContent.trim(); RX.lastIndex = 0; var m = RX.exec(t);
      el.innerHTML = tile(m ? MAP[m[1]] : (/cosmet/i.test(el.parentNode.textContent) ? 'spark' : 'users')); el.dataset.dx = '1';
    });
    document.querySelectorAll('.dg-today li').forEach(function (li) {
      var n = li.querySelector('.dg-n'); if (!n || n.dataset.dx) return;
      var p = window.POSTS && window.POSTS.find(function (x) { return x.id === +li.dataset.jp; });
      n.innerHTML = tile(CAT_IC[p && p.cat] || 'megaphone', 'sm'); n.dataset.dx = '1';
    });
    document.querySelectorAll('.lg-list .lg-n').forEach(function (n, i) {
      if (n.dataset.dx) return; n.innerHTML = tile(['flask', 'doc', 'factory', 'briefcase', 'cap'][i] || 'seal', 'dark'); n.dataset.dx = '1';
    });
    document.querySelectorAll('.dg-foot .dg-pg').forEach(function (n) {
      if (n.dataset.dx) return; var page = document.body.getAttribute('data-page') || 'feed';
      n.innerHTML = tile(PAGE_IC[page] || 'seal', 'sm') + '<span class="dx-foot-brand">Drugbox</span>'; n.dataset.dx = '1';
    });
  }
  /* illustrations next to page titles that have no photo banner */
  var HEAD_ILL = { notifs: 'dossier', saved: 'dossier', profile: 'lab' };
  function headArt() {
    var page = document.body.getAttribute('data-page'), k = HEAD_ILL[page], c = document.getElementById('content');
    if (!c) return;
    var cur = c.querySelector(':scope > .dx-ill-head');
    if (!k) { if (cur) cur.remove(); return; }
    if (cur && cur.dataset.k === k) return; if (cur) cur.remove();
    c.insertAdjacentHTML('afterbegin', '<div class="dx-ill dx-ill-head" data-k="' + k + '" aria-hidden="true">' + ILL[k] + '</div>');
  }
  function createArt() {
    var t = document.querySelector('#mkx #tab-create'); if (!t || t.querySelector('.dx-ill-create')) return;
    var head = t.querySelector('.page-title') || t.firstElementChild; if (!head) return;
    head.insertAdjacentHTML('afterend', '<div class="dx-ill dx-ill-create" aria-hidden="true">' + ILL.dossier + '</div>');
  }

  /* registered on the shared render bus — each part isolated */
  var C = window.dxCore;
  C.onRender('icons', function () { iconify(); });
  C.onRender('hex-avatars', function () { hexify(); });
  C.onRender('illustrations', function () { illustrate(); headArt(); createArt(); });
  C.onRender('icon-tiles', function () { tiles(); });
  C.onRender('season', function () { seasonal(); });
  /* ── A4: hexagon loader (after sign-in and between pages) ── */
  var loader = document.createElement('div'); loader.id = 'dxLoader'; loader.setAttribute('aria-hidden', 'true');
  loader.innerHTML = '<div class="dx-load-hex"><svg viewBox="-60 -60 120 120">' + [0, 1, 2, 3, 4, 5].map(function (i) {
      var a1 = (-90 + i * 60) * Math.PI / 180, a2 = (-30 + i * 60) * Math.PI / 180, r = 48;
      return '<path class="t t' + i + '" d="M0 0L' + (r * Math.cos(a1)).toFixed(1) + ' ' + (r * Math.sin(a1)).toFixed(1) + 'L' + (r * Math.cos(a2)).toFixed(1) + ' ' + (r * Math.sin(a2)).toFixed(1) + 'Z"/>';
    }).join('') + '</svg></div><div class="dx-load-word"><span class="d">DRUG</span><span class="b">BOX</span></div>';
  document.body.appendChild(loader);
  var hideT;
  function showLoader(full, ms) {
    clearTimeout(hideT); loader.className = full ? 'on full' : 'on mini';
    hideT = setTimeout(function () { loader.className = ''; }, ms || 450);
  }
  window.dxShowLoader = showLoader;
  if (typeof window.doLogin === 'function') {
    var origLogin = window.doLogin;
    window.doLogin = function () { var r = origLogin.apply(this, arguments); var e = document.getElementById('loginErr'); setTimeout(function () { if (!e || !e.textContent.trim()) showLoader(true, 1100); }, 30); return r; };
  }
  /* ── A5 + A6: appearance (light / dark · standard / Ramadan / Eid) ── */
  var theme = { mode: 'light', season: 'standard', fs: 'm' };
  try { theme = Object.assign(theme, JSON.parse(localStorage.getItem('dx_theme') || '{}')); } catch (e) {}
  function applyTheme() {
    document.documentElement.classList.toggle('dx-dark', theme.mode === 'dark');
    document.documentElement.classList.remove('dx-ramadan', 'dx-eid', 'dx-fs-l', 'dx-fs-xl');
    if (theme.fs && theme.fs !== 'm') document.documentElement.classList.add('dx-fs-' + theme.fs);
    if (theme.season !== 'standard') document.documentElement.classList.add('dx-' + theme.season);
    try { localStorage.setItem('dx_theme', JSON.stringify(theme)); } catch (e) {}
    var b = document.getElementById('dxThemeBtn'); if (b) b.innerHTML = svg(theme.mode === 'dark' ? 'moon' : 'palette') + '<span class="dx-theme-l">Theme</span>';
    seasonal();
  }
  window.dxTheme = function (k, v) { theme[k] = v; applyTheme(); };
  function addThemeButton() {
    var right = document.querySelector('.topbar .top-right'); if (!right || document.getElementById('dxThemeBtn')) return;
    var btn = document.createElement('button'); btn.id = 'dxThemeBtn'; btn.type = 'button'; btn.className = 'dx-theme-btn'; btn.setAttribute('aria-label', 'Appearance'); btn.title = 'Appearance';
    right.insertBefore(btn, right.firstChild);
    var pop;
    btn.addEventListener('click', function (e) {
      e.stopPropagation(); if (pop) { pop.remove(); pop = null; return; }
      pop = document.createElement('div'); pop.className = 'dx-pop';
      var r = btn.getBoundingClientRect(); pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - 268, r.right - 260)) + 'px';
      function seg(k, opts) { return '<div class="dx-seg">' + opts.map(function (o) { return '<button type="button" data-k="' + k + '" data-v="' + o[0] + '" class="' + (theme[k] === o[0] ? 'on' : '') + '">' + svg(o[2]) + o[1] + '</button>'; }).join('') + '</div>'; }
      pop.innerHTML = '<div class="dx-pop-h">Appearance</div>' + seg('mode', [['light', 'Light', 'sun'], ['dark', 'Dark', 'moon']]) +
        '<div class="dx-pop-h">Text size</div>' + seg('fs', [['m', 'Normal', 'doc'], ['l', 'Large', 'plus'], ['xl', 'Larger', 'plus']]) +
        '<div class="dx-pop-h">Season</div>' + seg('season', [['standard', 'Standard', 'seal'], ['ramadan', 'Ramadan', 'crescent'], ['eid', 'Eid', 'spark']]);
      pop.addEventListener('click', function (ev) { var b = ev.target.closest('button[data-k]'); if (!b) return; theme[b.dataset.k] = b.dataset.v; applyTheme(); pop.querySelectorAll('button[data-k="' + b.dataset.k + '"]').forEach(function (x) { x.classList.toggle('on', x === b); }); });
      document.body.appendChild(pop);
    });
    document.addEventListener('click', function (e) { if (pop && !e.target.closest('.dx-pop')) { pop.remove(); pop = null; } });
    applyTheme();
  }

  /* background tiles */
  var st = document.createElement('style');
  st.textContent = ':root{--dx-hex:url(' + HEX.light + ');--dx-hex-dark:url(' + HEX.dark + ');--dx-hex-gold:url(' + HEX.gold + ')}';
  document.head.appendChild(st);
  addThemeButton(); applyTheme();
})();
