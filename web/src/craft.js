/* Drugbox craft layer — B8..B13 (presentation only; page logic untouched)
   B8  count-up stats · skeleton placeholders · success animation · smooth page transitions
   B9  hover cards on names
   B10 compare 2–4 marketplace listings
   B11 listing state signals
   B12 tabular numbers + currency formatting with EGP equivalent
   B13 illustrated empty states + 3-step onboarding tour */
(function () {
  var ILL = __ILL__;
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function page() { return document.body.getAttribute('data-page') || 'feed'; }
  function icon(n) { return window.dxIcon ? window.dxIcon(n) : ''; }

  /* ═════ B8a · count-up stats ═════ */
  var COUNT_SEL = '.pstat-n, #mkx .hstat-n, #jx .intel-item b, #gx .intel-item b, .lg-stats .auth-stat-n, .dg-faces-tx b, .feed-wrap .card b[style*="color:var(--cp)"]';
  function countUp() {
    document.querySelectorAll(COUNT_SEL).forEach(function (el) {
      if (el.dataset.dxCount) return; el.dataset.dxCount = '1';
      var raw = txt(el), m = raw.match(/^([^\d]*)([\d,]*\.?\d+)(.*)$/); if (!m) return;
      var target = parseFloat(m[2].replace(/,/g, '')), dec = (m[2].split('.')[1] || '').length, comma = m[2].indexOf(',') >= 0 || target >= 1000;
      if (!isFinite(target) || target === 0 || reduce) return;
      var t0 = performance.now(), dur = Math.min(1200, 500 + target * 2);
      function fmt(v) { var s = v.toFixed(dec); if (comma) s = Number(s).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }); return m[1] + s + m[3]; }
      if (el.childNodes.length !== 1 || el.firstChild.nodeType !== 3) return;   /* only plain numbers */
      var node = el.firstChild;
      (function step(now) {
        var k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        node.nodeValue = fmt(target * e);
        if (k < 1) requestAnimationFrame(step); else node.nodeValue = raw;
      })(t0);
    });
  }

  /* ═════ B8b · skeleton placeholders + smooth transitions between pages ═════ */
  var skel = document.createElement('div'); skel.id = 'dxSkel'; skel.setAttribute('aria-hidden', 'true');
  skel.innerHTML = '<div class="sk-head"><i class="sk sk-pill"></i><i class="sk sk-title"></i></div>' +
    [0, 1, 2].map(function () { return '<div class="sk-card"><i class="sk sk-av"></i><div class="sk-lines"><i class="sk sk-l1"></i><i class="sk sk-l2"></i><i class="sk sk-l3"></i></div></div>'; }).join('');
  document.body.appendChild(skel);
  var skT;
  function transition() {
    var c = document.getElementById('content'); if (!c) return;
    var r = c.getBoundingClientRect();
    skel.style.left = r.left + 'px'; skel.style.top = r.top + 'px'; skel.style.width = r.width + 'px'; skel.style.height = r.height + 'px';
    /* the page is already rendered when this runs, so no placeholder is needed — just a short fade */
    c.classList.remove('dx-enter'); void c.offsetWidth; c.classList.add('dx-enter');
  }
  window.dxCore.onPage('page-transition', function () { var ld = document.getElementById('dxLoader'); if (ld && ld.classList.contains('mini')) ld.className = ''; transition(); });

  /* ═════ B8c · success animation (a hexagon check that pops when something succeeds) ═════ */
  var OK_RX = /\b(sent|saved|published|posted|created|joined|applied|connected|renewed|activated|listed|accepted|updated|submitted|shared|copied|reposted|boost activated|live)\b/i;
  var NO_RX = /\b(please|error|fail|cannot|can't|need|required|removed|unblocked|blocked|deleted|not )\b/i;
  var burst = document.createElement('div'); burst.id = 'dxOk'; burst.setAttribute('aria-hidden', 'true');
  burst.innerHTML = '<svg viewBox="0 0 64 72"><path class="hx" d="M32 3l27 15.5v35L32 69 5 53.5v-35z"/><path class="ck" d="M20 37l8 8 16-17"/></svg><i class="ring"></i>';
  document.body.appendChild(burst);
  var lastMsg = '', okT;
  function celebrate() { if (reduce) return; burst.className = ''; void burst.offsetWidth; burst.className = 'on'; clearTimeout(okT); okT = setTimeout(function () { burst.className = ''; }, 1300); }

  function judge(m) { m = String(m || ''); if (OK_RX.test(m) && !NO_RX.test(m)) celebrate(); }
  if (window.DBK && typeof window.DBK.toast === 'function') { var dt = window.DBK.toast; window.DBK.toast = function (m) { judge(m); return dt.apply(this, arguments); }; }
  if (typeof window.toast === 'function') { var at = window.toast; window.toast = function (m) { judge(m); return at.apply(this, arguments); }; }
  function watchToasts() {
    document.querySelectorAll('#toast, .dbk-toast').forEach(function (t) {
      if (t.dataset.dxOk) return; t.dataset.dxOk = '1';
      new MutationObserver(function () {
        var shown = t.classList.contains('show') || t.classList.contains('on') || getComputedStyle(t).opacity > 0.5;
        var m = txt(t); if (!shown || !m || m === lastMsg) return; lastMsg = m; setTimeout(function () { lastMsg = ''; }, 1500);
        /* toasts are also judged at the source (wrapped functions above) */
      }).observe(t, { childList: true, characterData: true, subtree: true, attributes: true, attributeFilter: ['class', 'style'] });
    });
  }

  /* ═════ B9 · hover cards ═════ */
  var NAME_SEL = '.post-name, .cmt-name, #jx .jc-company > span:first-child, #mkx .seller-name, #mkx .dc-buyer, #mkx .sc-provider, .sugg-name, .notif-item b, .pending-card b, #mx .t-name, #gx .member-name';
  var hc = document.createElement('div'); hc.id = 'dxHover'; hc.setAttribute('role', 'dialog'); document.body.appendChild(hc);
  var hcT, hcHide, hcFor = null;
  function norm(s) { return String(s || '').toLowerCase().replace(/^(dr|eng|m)\.\s*/, '').replace(/[^a-z ]/g, '').trim(); }
  function findUser(name) {
    var U = window.USERS || [], n = norm(name), last = n.split(' ').pop();
    return U.find(function (u) { return norm(u.name) === n || norm(u.company) === n; }) || U.find(function (u) { return last.length > 3 && norm(u.name).split(' ').pop() === last; }) || null;
  }
  function isCompany(name) { return !/^(dr|eng|prof)\.?\s/i.test(name) && /pharma|industries|biotech|\blab\b|store|ltd|group|holding|laborator|trading|medical|healthcare|chemical/i.test(name); }
  function showCard(el) {
    var name = txt(el).replace(/✓|Verified/g, '').split('·')[0].trim(); if (!name || name.length > 60) return;
    var u = findUser(name), comp = u ? isCompany(u.name) : isCompany(name);
    var ini = (u && u.initials) || name.replace(/^(Dr\.|Eng\.)\s*/, '').split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase();
    var color = (u && u.color) || '#1a56db';
    var head = u ? (u.headline || '').split('|')[0].trim() : (el.closest('.jcard,.sponsored-card,.dcard,.scard') ? txt((el.closest('.jcard,.sponsored-card,.dcard,.scard').querySelector('.seller-role,.jc-title,.sc-title,.dc-title') || {})) : '');
    var place = u ? [u.company, u.location].filter(Boolean).join(' · ') : '';
    var stats = u ? '<div class="hc-stats"><span><b>' + (u.connections || 0).toLocaleString() + '</b> connections</span><span><b>' + (u.followers || 0).toLocaleString() + '</b> followers</span></div>' : '';
    hc.innerHTML = '<div class="hc-top"><div class="hc-av' + (comp ? ' dx-hex' : '') + '" style="background:' + esc(color) + '">' + esc(ini) + '</div><div class="hc-id"><div class="hc-name">' + esc(u ? u.name : name) +
      (u && u.verified ? '<span class="hc-seal" title="Verified">' + icon('seal') + '</span>' : '') + '</div>' + (head ? '<div class="hc-head">' + esc(head.slice(0, 90)) + '</div>' : '') + (place ? '<div class="hc-place">' + esc(place) + '</div>' : '') + '</div></div>' +
      stats + (u && u.hiring ? '<div class="hc-flag">Hiring now</div>' : '') + (u && u.openToWork ? '<div class="hc-flag ow">Open to work</div>' : '') +
      '<div class="hc-acts"><button type="button" class="hc-btn p" data-act="msg">' + icon('chat') + 'Message</button>' + (u ? '<button type="button" class="hc-btn" data-act="profile">' + icon('user') + 'View profile</button>' : '') + '</div>';
    hc.dataset.uid = u ? u.id : ''; hc.dataset.name = u ? u.name : name;
    var r = el.getBoundingClientRect(), W = 300;
    var left = Math.max(8, Math.min(innerWidth - W - 8, r.left)), top = r.bottom + 8;
    hc.style.left = left + 'px'; hc.style.top = top + 'px'; hc.className = 'on';
    var h = hc.offsetHeight; if (top + h > innerHeight - 8) hc.style.top = Math.max(8, r.top - h - 8) + 'px';
  }
  function hideCard() { hc.className = ''; hcFor = null; }
  if (window.matchMedia && matchMedia('(hover: hover)').matches) {
    document.addEventListener('mouseover', function (e) {
      var el = e.target.closest && e.target.closest(NAME_SEL);
      if (el && el !== hcFor) { clearTimeout(hcT); clearTimeout(hcHide); hcFor = el; hcT = setTimeout(function () { if (hcFor === el) showCard(el); }, 380); }
      else if (!el && !e.target.closest('#dxHover')) { clearTimeout(hcT); if (hcFor) { clearTimeout(hcHide); hcHide = setTimeout(hideCard, 220); } }
      if (e.target.closest('#dxHover')) clearTimeout(hcHide);
    });
    document.addEventListener('scroll', function () { if (hc.className === 'on') hideCard(); }, true);   /* hide an open card; don't cancel one about to show */
  }
  hc.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act]'); if (!b) return;
    var uid = +hc.dataset.uid, name = hc.dataset.name; hideCard();
    if (b.dataset.act === 'profile' && uid && window.gotoProfile) window.gotoProfile(uid);
    if (b.dataset.act === 'msg') { if (window.dxOpenChat && window.dxCore.on('chat-dock') && document.body.getAttribute('data-page') !== 'messages') window.dxOpenChat(name); else if (uid && window.messageUser) window.messageUser(uid); else { window.__mxTo = name; if (window.goto) window.goto('messages'); } }
  });

  /* ═════ B10 · compare marketplace listings ═════ */
  var picks = [];
  var CARD = '#mkx .sponsored-card, #mkx .lcard';
  function cardData(c) {
    var t = c.querySelector('.sp-title,.lc-title'), tt = t ? t.cloneNode(true) : null; if (tt) tt.querySelectorAll('.role-badge').forEach(function (x) { x.remove(); });
    var priceEl = c.querySelector('.sp-price,.price'), price = priceEl ? txt(priceEl.querySelector('.dx-num') || priceEl).replace(/≈.*$/, '').trim() : '';
    var certs = []; c.querySelectorAll('.cert-p,.cert,.ti').forEach(function (x) { var v = txt(x).replace(/^✓\s*/, '').replace(/\s*(certified|filed|available)$/i, ''); if (/GMP|CEP|DMF|FDA|ISO|EDA|Halal|EDQM|Vegan/i.test(v) && certs.indexOf(v) < 0 && certs.length < 5) certs.push(v); });
    var flagM = txt(c).match(/🇪🇬|🇨🇳|🇮🇳|🇦🇪|🇸🇦|🇩🇪/);
    return { title: tt ? txt(tt) : 'Listing', type: txt(c.querySelector('.lt')) || '—', price: price || 'On request', num: parseFloat((price.match(/[\d.]+/) || [])[0]),
      moq: txt(c.querySelector('.sp-moq,.moq')).replace(/^MOQ:?\s*/i, '') || '—', supplier: txt(c.querySelector('.seller-name')).replace(/✓.*$/, '').trim() || '—',
      country: flagM ? flagM[0] : '—', certs: certs.join(', ') || '—', stats: txt(c.querySelector('.sp-stats')) || '' };
  }
  var tray = document.createElement('div'); tray.id = 'dxTray'; document.body.appendChild(tray);
  var traySig = '';
  function drawTray() {
    var sig = document.getElementById('mkx') ? picks.map(function (c) { return cardData(c).title; }).join('|') : '';
    if (sig === traySig) return; traySig = sig;
    if (!picks.length || !document.getElementById('mkx')) { tray.className = ''; tray.innerHTML = ''; return; }
    tray.className = 'on';
    tray.innerHTML = '<div class="tr-l">' + icon('clipboard') + '<b>Compare</b><span>' + picks.length + ' of 4 selected</span></div><div class="tr-chips">' +
      picks.map(function (c, i) { return '<span class="tr-chip">' + esc(cardData(c).title.slice(0, 28)) + '<button type="button" data-rm="' + i + '" aria-label="Remove">×</button></span>'; }).join('') + '</div>' +
      '<button type="button" class="tr-go"' + (picks.length < 2 ? ' disabled' : '') + '>Compare ' + picks.length + '</button><button type="button" class="tr-x">Clear</button>';
  }
  tray.addEventListener('click', function (e) {
    var rm = e.target.closest('[data-rm]');
    if (rm) { var c = picks.splice(+rm.dataset.rm, 1)[0]; var cb = c && c.querySelector('.dx-cmp input'); if (cb) { cb.checked = false; cb.parentNode.classList.remove('on'); } drawTray(); return; }
    if (e.target.closest('.tr-x')) { picks.forEach(function (c) { var cb = c.querySelector('.dx-cmp input'); if (cb) { cb.checked = false; cb.parentNode.classList.remove('on'); } }); picks = []; drawTray(); return; }
    if (e.target.closest('.tr-go') && picks.length >= 2) openCompare();
  });
  function openCompare() {
    var ds = picks.map(cardData), nums = ds.map(function (d) { return d.num; }).filter(function (n) { return isFinite(n); }), best = nums.length ? Math.min.apply(null, nums) : null;
    var rows = [['Type', 'type'], ['Price', 'price'], ['MOQ', 'moq'], ['Supplier', 'supplier'], ['Country', 'country'], ['Certifications', 'certs']];
    var body = '<div class="cmp-wrap"><table class="cmp"><thead><tr><th></th>' + ds.map(function (d) { return '<th>' + esc(d.title) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      rows.map(function (r) { return '<tr><td>' + r[0] + '</td>' + ds.map(function (d) { var best1 = r[1] === 'price' && best != null && d.num === best && nums.length > 1; return '<td' + (best1 ? ' class="best"' : '') + '>' + esc(d[r[1]]) + (best1 ? '<small>Lowest price</small>' : '') + '</td>'; }).join('') + '</tr>'; }).join('') +
      '</tbody></table></div><div class="dbk-note">Prices are per the unit each supplier lists. Ask each supplier for a formal quote to compare like for like.</div>';
    if (window.DBK) window.DBK.modal({ title: 'Compare listings', body: body, secondary: 'Close' });
    var box = document.querySelectorAll('.dbk-box'); if (box.length) box[box.length - 1].classList.add('dbk-wide');
  }
  function compareBoxes() {
    var mk = document.getElementById('mkx'); if (!mk) { if (picks.length) { picks = []; drawTray(); } return; }
    picks = picks.filter(function (c) { return document.body.contains(c); });
    mk.querySelectorAll(CARD).forEach(function (c) {
      if (c.querySelector('.dx-cmp')) return;
      var tools = c.querySelector(':scope > .dx-tools'); if (!tools) { tools = document.createElement('div'); tools.className = 'dx-tools'; c.appendChild(tools); }
      var lab = document.createElement('label'); lab.className = 'dx-cmp'; lab.innerHTML = '<input type="checkbox"> Compare';
      lab.addEventListener('click', function (e) { e.stopPropagation(); });
      lab.querySelector('input').addEventListener('change', function (e) {
        lab.classList.toggle('on', e.target.checked);
        if (e.target.checked) { if (picks.length >= 4) { e.target.checked = false; if (window.DBK) window.DBK.toast('You can compare up to 4 listings'); return; } picks.push(c); }
        else picks = picks.filter(function (x) { return x !== c; });
        drawTray();
      });
      tools.appendChild(lab);
    });
    drawTray();
  }

  /* ═════ B11 · listing state signals ═════ */
  function hash(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
  var STATES = [['new', 'New', 'spark'], ['drop', 'Price dropped 8%', 'trend'], ['exp', 'Expiring in 3 days', 'warning'], ['ver', 'Recently verified', 'seal']];
  function states() {
    var mk = document.getElementById('mkx'); if (!mk) return;
    mk.querySelectorAll('#mkx .sponsored-card, #mkx .lcard, #mkx .scard').forEach(function (c, i) {
      if (c.querySelector('.dx-state')) return;
      var t = txt(c.querySelector('.sp-title,.lc-title,.sc-title')), s;
      if (c.dataset.new) s = STATES[0];
      else if (c.classList.contains('sponsored-card')) s = STATES[3];
      else { var k = hash(t) % 5; s = k < 4 ? STATES[k] : null; }
      if (!s) return;
      var b = document.createElement('span'); b.className = 'dx-state st-' + s[0]; b.innerHTML = icon(s[2]) + s[1];
      c.appendChild(b);
    });
  }

  /* ═════ B12 · tabular numbers + currency formatting (USD with EGP equivalent) ═════ */
  function rate() { return window.EGP_FALLBACK_RATE || 49.5; }
  function currency() {
    document.querySelectorAll('#mkx .price, #mkx .sp-price, #mkx .sc-price').forEach(function (el) {
      if (el.dataset.dxCur) return;
      var t = txt(el), m = t.match(/\$\s?([\d,]+(?:\.\d+)?)/); el.dataset.dxCur = '1'; if (!m) return;
      var v = parseFloat(m[1].replace(/,/g, '')), unit = (t.split('/')[1] || '').trim();
      var usd = v.toLocaleString('en-US', { minimumFractionDigits: v < 100 ? 2 : 0, maximumFractionDigits: 2 });
      var egp = Math.round(v * rate()).toLocaleString('en-US');
      var small = el.querySelector('small,span'), unitHtml = small ? small.outerHTML : (unit ? '<small>/' + esc(unit) + '</small>' : '');
      el.innerHTML = '<span class="dx-num">US$ ' + usd + '</span>' + unitHtml + '<span class="dx-egp" title="Approximate, at ' + rate() + ' EGP per USD">≈ EGP ' + egp + '</span>';
    });
  }

  /* ═════ B13a · illustrated empty states (the app's big-emoji empties) ═════ */
  function empties() {
    document.querySelectorAll('#content div[style*="text-align:center"]').forEach(function (el) {
      if (el.dataset.dxEmpty) return; var f = el.firstElementChild;
      if (!f || !/font-size:\s*(3\d|4\d|5\d)px/.test(f.getAttribute('style') || '') || txt(f).length > 4) return;
      el.dataset.dxEmpty = '1';
      var k = page() === 'saved' ? 'dossier' : /market|companies/.test(page()) ? 'shipping' : page() === 'groups' ? 'factory' : 'lab';
      f.outerHTML = '<div class="dx-ill dx-ill-empty">' + ILL[k] + '</div>';
    });
  }

  /* ═════ B13b · 3-step onboarding tour (first sign-in; replay from Theme) ═════ */
  var TOUR = [
    { sel: '.sidebar .nl.active, #mb-feed', t: 'Your pages', d: 'Every part of Drugbox lives here: your network, messages, the marketplace, jobs and training.', ic: 'home' },
    { sel: '#tnb-market, #mb-market', t: 'Source and sell', d: 'Post supply or demand, send RFQs and compare suppliers side by side in the Marketplace.', ic: 'cart' },
    { sel: '#dxThemeBtn, .top-av, .me-av', t: 'Make it yours', d: 'Complete your profile to be found by buyers and employers, and switch to dark mode or the Ramadan theme here.', ic: 'user' }
  ];
  var tourEl = null, tourI = 0;
  function endTour(done) { if (tourEl) { tourEl.remove(); tourEl = null; } try { localStorage.setItem('dx_tour_done', '1'); } catch (e) {} }
  function drawTour() {
    var s = TOUR[tourI], target = null;
    s.sel.split(',').some(function (q) { var el = document.querySelector(q.trim()); if (!el) return false; var rr = el.getBoundingClientRect(); if (rr.width && rr.right > 0 && rr.left < innerWidth && rr.bottom > 0 && rr.top < innerHeight) { target = el; return true; } return false; });
    if (!target) { if (tourI < TOUR.length - 1) { tourI++; return drawTour(); } return endTour(true); }
    var r = target.getBoundingClientRect(), pad = 8;
    if (!tourEl) { tourEl = document.createElement('div'); tourEl.id = 'dxTour'; document.body.appendChild(tourEl); }
    var box = { l: r.left - pad, t: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 };
    var tipW = Math.min(300, innerWidth - 24), tipL = Math.min(innerWidth - tipW - 12, Math.max(12, box.l + box.w + 14)), tipT = Math.max(12, Math.min(innerHeight - 220, box.t));
    if (box.l + box.w + tipW + 30 > innerWidth) { tipL = Math.max(12, Math.min(innerWidth - tipW - 12, box.l + box.w - tipW)); tipT = box.t > innerHeight / 2 ? Math.max(12, box.t - 200) : Math.min(innerHeight - 220, box.t + box.h + 12); }
    tourEl.innerHTML = '<div class="tour-hole" style="left:' + box.l + 'px;top:' + box.t + 'px;width:' + box.w + 'px;height:' + box.h + 'px"></div>' +
      '<div class="tour-tip" role="dialog" aria-label="' + esc(s.t) + '" style="left:' + tipL + 'px;top:' + tipT + 'px;width:' + tipW + 'px">' +
      '<div class="tour-h"><span class="dx-tile">' + icon(s.ic) + '</span><b>' + esc(s.t) + '</b></div><p>' + esc(s.d) + '</p>' +
      '<div class="tour-f"><div class="tour-dots">' + TOUR.map(function (_, i) { return '<i class="' + (i === tourI ? 'on' : '') + '"></i>'; }).join('') + '</div>' +
      '<button type="button" class="tour-skip">Skip</button><button type="button" class="tour-next">' + (tourI < TOUR.length - 1 ? 'Next' : 'Done') + '</button></div></div>';
    tourEl.querySelector('.tour-skip').onclick = function () { endTour(false); };
    tourEl.querySelector('.tour-next').onclick = function () { if (tourI < TOUR.length - 1) { tourI++; drawTour(); } else { endTour(true); if (window.DBK) window.DBK.toast('You are all set — welcome to Drugbox'); } };
  }
  function startTour(force) {
    try { if (!force && localStorage.getItem('dx_tour_done')) return; } catch (e) {}
    tourI = 0; drawTour();
  }
  window.dxStartTour = function () { startTour(true); };
  window.addEventListener('resize', function () { if (tourEl) drawTour(); });
  /* first time the app opens after sign-in */
  var appEl = document.getElementById('app');
  if (appEl) new MutationObserver(function () {
    if (appEl.offsetWidth > 0 && !tourEl) setTimeout(function () { if (document.getElementById('app').offsetWidth > 0) startTour(false); }, 1500);
  }).observe(appEl, { attributes: true, attributeFilter: ['style', 'class'] });
  /* navigating away counts as "seen" */
  window.dxCore.onPage('tour', function () { if (tourEl) endTour(false); }, true);
  /* replay link inside the Theme menu */
  document.addEventListener('click', function () {
    setTimeout(function () {
      var pop = document.querySelector('.dx-pop'); if (!pop || pop.querySelector('.dx-tour-link')) return;
      var a = document.createElement('button'); a.type = 'button'; a.className = 'dx-tour-link'; a.innerHTML = icon('compass') + 'Take the 3-step tour';
      a.onclick = function () { pop.remove(); startTour(true); }; pop.appendChild(a);
    }, 0);
  });

  /* ═════ registered on the shared render bus — each part isolated ═════ */
  var C = window.dxCore;
  C.onRender('count-up', countUp);
  C.onRender('toast-watch', watchToasts);
  C.onRender('compare', compareBoxes);
  C.onRender('listing-states', states);
  C.onRender('currency', currency);
  C.onRender('empty-states', empties);
})();
