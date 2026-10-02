/* Batch 2 — partner levels · certificate wall · skills honeycomb · glossary · quick view · chat dock · filter chips */
(function () {
  var C = window.dxCore; if (!C) return;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  var D = window.DBK;
  var YEAR = new Date().getFullYear();

  /* ── 1. Drugbox partner levels (companies) ── */
  var LEVEL = { 'quadra pharm': 'gold', 'aurobindo pharma': 'gold', 'medsinia industries': 'silver', 'shandong hope biotech': 'silver', 'epione drug store': 'bronze', 'beauty lab egypt': 'bronze' };
  var LV = { gold: ['Gold partner', '3+ years on Drugbox · 50+ completed deals · rating 4.5 or higher'], silver: ['Silver partner', '1+ year on Drugbox · 15+ completed deals · rating 4.2 or higher'], bronze: ['Bronze partner', 'Verified company · 3+ completed deals'] };
  function levelOf(name) { return LEVEL[String(name || '').toLowerCase().replace(/\s*[·|].*$/, '').replace(/✓|verified/gi, '').replace(/^[^a-z]+/, '').trim()] || ''; }
  function badge(lv) { return '<button type="button" class="dx-lvl lv-' + lv + '" data-lvl="' + lv + '" title="' + LV[lv][0] + '"><i></i>' + LV[lv][0].split(' ')[0] + '</button>'; }
  function levels() {
    document.querySelectorAll('#mkx .sp-seller, #jx #huntingView .jc-company, .profile-name').forEach(function (el) {
      if (el.querySelector('.dx-lvl')) return;
      var nameEl = el.matches('.profile-name') ? el : el.querySelector('.seller-name, span');
      var company = el.matches('.jc-company') ? txt(el.querySelector('span')) : el.matches('.profile-name') ? txt(el) : txt(el.querySelector('.seller-info .seller-sub, .seller-sub')) || txt(nameEl);
      var lv = levelOf(company) || levelOf(txt(nameEl)); if (!lv) return;
      (el.matches('.profile-name') ? el : (el.matches('.jc-company') ? el : nameEl.parentNode)).insertAdjacentHTML('beforeend', badge(lv));
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.dx-lvl'); if (!b) return; e.stopPropagation();
    var lv = b.dataset.lvl;
    D && D.modal({ title: 'Drugbox partner levels', secondary: 'Close',
      body: ['gold', 'silver', 'bronze'].map(function (k) { return '<div class="dx-lvl-row' + (k === lv ? ' on' : '') + '">' + badge(k) + '<span>' + LV[k][1] + '</span></div>'; }).join('') +
        '<div class="dbk-note">Levels are earned, never bought: they are based on time on Drugbox, completed deals and users\u2019 own reviews. VIP is a separate paid plan for company pages and is always shown as its own badge.</div>' });
  }, true);

  /* ── 2. certificate wall on profiles ── */
  function certStatus(exp) { var y = parseInt(exp, 10); if (!y) return 'ok'; return y < YEAR ? 'expired' : y === YEAR ? 'soon' : 'ok'; }
  function certWall() {
    var nameEl = document.querySelector('.profile-name'); if (!nameEl) return;
    var host = document.getElementById('profileTabContent'); if (!host || host.parentNode.querySelector('.dx-certwall')) return;
    var name = txt(nameEl).replace(/Gold|Silver|Bronze|HIRING|OPEN TO WORK|✓/g, '').trim();
    var u = (window.USERS || []).find(function (x) { return name.indexOf(x.name) === 0; }); if (!u || !u.certs || !u.certs.length) return;
    var lab = { ok: 'Valid', soon: 'Renew this year', expired: 'Expired' };
    var wall = document.createElement('div'); wall.className = 'dx-certwall';
    wall.innerHTML = '<div class="cw-h">' + ic('seal') + 'Certificate wall<span>' + u.certs.length + ' on record</span></div><div class="cw-grid">' +
      u.certs.map(function (c) { var s = certStatus(c.expiry); return '<div class="cw-seal st-' + s + '" title="' + esc(c.name + ' — ' + c.issuer) + '"><div class="cw-hex">' + ic('seal') + '</div><b>' + esc(c.name) + '</b><small>' + esc(c.issuer) + '</small><em>' + lab[s] + (c.expiry ? ' · ' + esc(c.expiry) : '') + '</em></div>'; }).join('') + '</div>';
    host.parentNode.insertBefore(wall, host);
  }

  /* ── 3. skills honeycomb ── */
  function honeycomb() {
    var host = document.getElementById('profileTabContent'); if (!host) return;
    var h3 = Array.prototype.find.call(host.querySelectorAll('h3'), function (h) { return /^skills$/i.test(txt(h)); }); if (!h3 || h3.parentNode.querySelector('.dx-comb')) return;
    var rows = Array.prototype.filter.call(h3.parentNode.children, function (r) { return r !== h3 && /endorsement/i.test(txt(r)); });
    if (!rows.length) return;
    var data = rows.map(function (r) { var sp = r.querySelectorAll('span'), cnt = sp[1] ? sp[1].firstChild ? sp[1].firstChild.textContent : txt(sp[1]) : ''; return { r: r, name: txt(sp[0]), n: parseInt((String(cnt).match(/(\d+)\s*endorsement/) || [])[1] || '0', 10) }; });
    var max = Math.max.apply(null, data.map(function (d) { return d.n; })) || 1;
    var comb = document.createElement('div'); comb.className = 'dx-comb';
    comb.innerHTML = data.map(function (d, i) { var k = Math.round(1 + 4 * d.n / max); return '<button type="button" class="dx-cell t' + k + '" data-i="' + i + '" title="Endorse ' + esc(d.name) + '"><b>' + esc(d.name) + '</b><small>' + d.n + '</small></button>'; }).join('');
    h3.insertAdjacentElement('afterend', comb);
    data.forEach(function (d) { d.r.classList.add('dx-comb-row'); });
    comb.addEventListener('click', function (e) {
      var c = e.target.closest('.dx-cell'); if (!c || c.classList.contains('done')) return;
      var d = data[+c.dataset.i], btn = d.r.querySelector('button'); if (btn) btn.click();
      c.classList.add('done'); c.querySelector('small').textContent = (d.n + 1) + ' ✓'; if (D) D.toast('You endorsed ' + d.name);
    });
  }

  /* ── 4. glossary: short definitions for trade and regulatory terms ── */
  var TERMS = {
    'WHO-GMP': 'Good Manufacturing Practice certified against World Health Organization standards.',
    'GMP': 'Good Manufacturing Practice — the quality system every pharmaceutical plant must follow.',
    'CEP': 'Certificate of Suitability from EDQM (Europe) proving an API meets the European Pharmacopoeia.',
    'DMF': 'Drug Master File — confidential file a supplier submits to regulators about how an API is made.',
    'USFDA': 'United States Food and Drug Administration.',
    'EDQM': 'European Directorate for the Quality of Medicines, which issues CEPs.',
    'CoA': 'Certificate of Analysis — the lab results for a specific batch.',
    'COA': 'Certificate of Analysis — the lab results for a specific batch.',
    'MOQ': 'Minimum Order Quantity the supplier will accept.',
    'FOB': 'Free On Board — the seller pays until the goods are loaded on the ship; the buyer pays freight and insurance.',
    'CIF': 'Cost, Insurance and Freight — the seller pays shipping and insurance to the destination port.',
    'EXW': 'Ex Works — the buyer collects from the seller\u2019s site and pays all transport.',
    'DDP': 'Delivered Duty Paid — the seller delivers to your door and pays import duties.',
    'CFR': 'Cost and Freight — the seller pays shipping to the port; the buyer insures.',
    'CTD': 'Common Technical Document — the standard dossier format for registering medicines.',
    'EDA': 'Egyptian Drug Authority — Egypt\u2019s medicines regulator.',
    'SFDA': 'Saudi Food and Drug Authority.',
    'DHA': 'Dubai Health Authority.',
    'MOHAP': 'UAE Ministry of Health and Prevention.',
    'NFSA': 'Egypt\u2019s National Food Safety Authority (supplements and food).',
    'API': 'Active Pharmaceutical Ingredient — the substance that makes the medicine work.',
    'CMO': 'Contract Manufacturing Organization — makes products for other companies.',
    'RFQ': 'Request for Quotation — a formal price request to suppliers.',
    'HPLC': 'High-Performance Liquid Chromatography — the main lab test for purity and assay.',
    'ICH': 'International Council for Harmonisation — global technical guidelines for medicines.',
    'ISO 22716': 'The GMP standard for cosmetics manufacturing.',
    'BP/USP': 'Meets both the British and the United States Pharmacopoeia.',
    'Toll': 'Toll manufacturing — a plant produces your product under your licence and formula.'
  };
  var KEYS = Object.keys(TERMS).sort(function (a, b) { return b.length - a.length; });
  var TRX = new RegExp('(^|[^A-Za-z0-9-])(' + KEYS.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&'); }).join('|') + ')(?![A-Za-z0-9-])');
  var GSEL = '#mkx .cert, #mkx .cert-p, #mkx .ti, #mkx .sp-desc, #mkx .lc-desc, #mkx .sc-tag, #mkx .dc-meta, #jx .jt, #jx .jc-desc, .post-body';
  function glossary() {
    document.querySelectorAll(GSEL).forEach(function (el) {
      if (el.dataset.dxg) return; el.dataset.dxg = '1';
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n, list = [];
      while ((n = w.nextNode())) if (!(n.parentElement && n.parentElement.closest('abbr,a,button'))) list.push(n);
      var seen = {};
      list.forEach(function (t) {
        var m = TRX.exec(t.nodeValue); if (!m || seen[m[2]]) return; seen[m[2]] = 1;
        var start = m.index + m[1].length, term = t.splitText(start); term.splitText(m[2].length);
        var ab = document.createElement('abbr'); ab.className = 'dx-term'; ab.tabIndex = 0; ab.dataset.term = m[2]; ab.textContent = m[2];
        term.parentNode.replaceChild(ab, term);
      });
    });
  }
  var tip = document.createElement('div'); tip.id = 'dxTerm'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip);
  function showTip(ab) {
    var k = ab.dataset.term, d = TERMS[k]; if (!d) return;
    tip.innerHTML = '<b>' + esc(k) + '</b>' + esc(d); tip.className = 'on';
    var r = ab.getBoundingClientRect(), w = Math.min(280, innerWidth - 16);
    tip.style.width = w + 'px'; tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
    var top = r.top - tip.offsetHeight - 8; tip.style.top = (top < 8 ? r.bottom + 8 : top) + 'px';
  }
  function hideTip() { tip.className = ''; }
  document.addEventListener('mouseover', function (e) { var a = e.target.closest && e.target.closest('.dx-term'); if (a) showTip(a); else if (!e.target.closest('#dxTerm')) hideTip(); });
  document.addEventListener('focusin', function (e) { if (e.target.classList && e.target.classList.contains('dx-term')) showTip(e.target); });
  document.addEventListener('focusout', hideTip);
  document.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('.dx-term'); if (a) { e.stopPropagation(); showTip(a); } }, true);
  document.addEventListener('scroll', hideTip, true);

  /* ── 5. quick view for marketplace listings ── */
  function quickButtons() {
    document.querySelectorAll('#mkx .sponsored-card, #mkx .lcard, #mkx .scard').forEach(function (c) {
      if (c.querySelector('.dx-qv')) return;
      var tools = c.querySelector(':scope > .dx-tools'); if (!tools) { tools = document.createElement('div'); tools.className = 'dx-tools'; c.appendChild(tools); }
      var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-qv'; b.innerHTML = ic('search') + 'Quick view'; tools.appendChild(b);
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.dx-qv'); if (!b) return; e.stopPropagation(); e.preventDefault();
    var c = b.closest('.sponsored-card,.lcard,.scard'); if (!c || !D) return;
    var t = c.querySelector('.sp-title,.lc-title,.sc-title'), tt = t ? t.cloneNode(true) : null; if (tt) tt.querySelectorAll('.role-badge,.dx-lvl').forEach(function (x) { x.remove(); });
    var pic = c.querySelector('.dx-prod'), price = c.querySelector('.sp-price,.price,.sc-price'), certs = [];
    c.querySelectorAll('.cert,.cert-p,.ti,.sc-tag').forEach(function (x) { var v = txt(x); if (v && certs.indexOf(v) < 0) certs.push(v); });
    var seller = c.querySelector('.sp-seller'), stats = c.querySelector('.sp-analytics');
    var act = c.querySelector('.btn-contact-gold,.btn-contact,.sc-btn');
    var m = D.modal({ title: 'Quick view', secondary: 'Close', primary: act ? { label: txt(act).replace(/→/g, '').trim() || 'Contact', onClick: function () { setTimeout(function () { act.click(); }, 60); } } : null,
      body: '<div class="qv-top" data-dxcat="' + (c.dataset.dxcat || '') + '">' + (pic ? '<div class="qv-pic">' + pic.outerHTML + '</div>' : '') + '<div><div class="qv-type">' + esc(txt(c.querySelector('.lt')) || (c.classList.contains('scard') ? 'SERVICE' : '')) + '</div><div class="qv-title">' + esc(tt ? txt(tt) : '') + '</div>' +
        (price ? '<div class="qv-price">' + price.innerHTML + '</div>' : '') + '<div class="qv-moq">' + esc(txt(c.querySelector('.sp-moq,.moq'))) + '</div></div></div>' +
        '<p class="qv-desc">' + esc(txt(c.querySelector('.sp-desc,.lc-desc'))) + '</p>' +
        (certs.length ? '<div class="qv-certs">' + certs.slice(0, 8).map(function (x) { return '<span>' + esc(x) + '</span>'; }).join('') + '</div>' : '') +
        (seller ? '<div class="qv-seller">' + seller.innerHTML + '</div>' : '') + (stats ? '<div class="qv-stats">' + stats.innerHTML + '</div>' : '') });
    m.el.querySelector('.dbk-box').classList.add('dbk-qv');
  }, true);

  /* ── 6. chat dock (small chat windows, bottom right) ── */
  var dock = document.createElement('div'); dock.id = 'dxDock'; document.body.appendChild(dock);
  var chats = D ? D.store.get('dock', {}) : {}, open = [];
  function saveChats() { if (D) D.store.set('dock', chats); }
  function drawDock() {
    if (document.body.getAttribute('data-page') === 'messages' || !document.getElementById('app') || !document.getElementById('app').offsetWidth) { dock.innerHTML = ''; return; }
    dock.innerHTML = open.map(function (o) {
      var msgs = chats[o.name] || [];
      return '<div class="dk-win' + (o.min ? ' min' : '') + '" data-n="' + esc(o.name) + '" title="' + (o.min ? 'Open chat' : '') + '"><div class="dk-h"><span class="dk-av">' + esc(o.name.replace(/^(Dr\.|Eng\.)\s*/, '').split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2)) + '</span><b>' + esc(o.name) + '</b>' +
        '<button type="button" data-a="full" title="Open full chat">' + ic('chat') + '</button><button type="button" data-a="min" title="Minimize">–</button><button type="button" data-a="x" title="Close">×</button></div>' +
        '<div class="dk-b">' + msgs.slice(-30).map(function (m) { return '<div class="dk-m ' + (m.me ? 'me' : 'them') + '">' + esc(m.text) + '</div>'; }).join('') + '</div>' +
        '<form class="dk-f"><input placeholder="Write a message…" aria-label="Message"><button type="submit">' + ic('send') + '</button></form></div>';
    }).join('');
    dock.querySelectorAll('.dk-b').forEach(function (b) { b.scrollTop = b.scrollHeight; });
  }
  function openChat(name, min) {
    var o = open.find(function (x) { return x.name === name; });
    if (!o) { open.unshift({ name: name, min: !!min }); open = open.slice(0, innerWidth < 700 ? 1 : 2); } else o.min = !!min;
    drawDock();
  }
  window.dxOpenChat = openChat;
  function push(name, m) { (chats[name] = chats[name] || []).push(m); saveChats(); }
  dock.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-a]'), win = e.target.closest('.dk-win'); if (!win) return;
    var name = win.dataset.n, o = open.find(function (x) { return x.name === name; });
    if (b && b.dataset.a === 'x') { open = open.filter(function (x) { return x !== o; }); drawDock(); }
    else if (b && b.dataset.a === 'min') { o.min = !o.min; drawDock(); }
    else if (b && b.dataset.a === 'full') { open = open.filter(function (x) { return x !== o; }); drawDock(); window.__mxTo = name; if (window.goto) window.goto('messages'); }
    else if (e.target.closest('.dk-h') && o.min) { o.min = false; drawDock(); }
  });
  dock.addEventListener('submit', function (e) {
    e.preventDefault(); var f = e.target, win = f.closest('.dk-win'), name = win.dataset.n, inp = f.querySelector('input'), v = inp.value.trim(); if (!v) return;
    push(name, { me: true, text: v }); if (rawSend) rawSend.call(D, { to: name, text: v });   /* straight to the inbox, window stays open */
    drawDock(); var i2 = dock.querySelector('.dk-win[data-n="' + name.replace(/"/g, '') + '"] input'); if (i2) i2.focus();
    setTimeout(function () { push(name, { me: false, text: 'Thanks — I\u2019ll get back to you shortly.' }); if (open.some(function (x) { return x.name === name; })) drawDock(); }, 1800);
  });
  /* messages sent from listings / jobs / hover card open a dock window */
  var rawSend = D && D.sendToOutbox;
  if (D && D.sendToOutbox) {
    var send = D.sendToOutbox;
    D.sendToOutbox = function (item) { var r = send.apply(this, arguments); if (item && item.to && !(chats[item.to] || []).some(function (m) { return m.me && m.text === item.text; })) push(item.to, { me: true, text: item.text }); if (item && item.to) openChat(item.to, true); return r; };   /* opens minimised: never covers the page */
  }
  document.addEventListener('dx:page', function () { open.forEach(function (o) { o.min = true; }); drawDock(); });   /* changing page tucks chats away */

  /* ── 7. active filters as chips + a way out of "no results" ── */
  var touched = false;
  document.addEventListener('change', function (e) { if (e.target.closest && e.target.closest('#mkx .filters')) touched = true; }, true);
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#mkx .f-tag, #mkx .cat-item')) touched = true; }, true);
  function activeFilters() {
    var mk = document.getElementById('mkx'); if (!mk) return [];
    var out = [], cats = mk.querySelectorAll('.cat-cb'), on = Array.prototype.filter.call(cats, function (c) { return c.checked; });
    if (on.length && on.length < cats.length) out.push({ k: 'cats', label: 'Showing: ' + on.map(function (c) { return txt(c.closest('.f-opt')).replace(/\d[\d,]*$/, '').trim(); }).join(', ') });
    if (!touched) return out;
    mk.querySelectorAll('.f-sec').forEach(function (sec) {
      var h = txt(sec.querySelector('.f-hdr')); if (/category/i.test(h)) return;
      sec.querySelectorAll('.f-opt input:checked').forEach(function (cb) { out.push({ k: 'cb', el: cb, label: txt(cb.closest('.f-opt')).replace(/\d[\d,]*$/, '').trim() }); });
    });
    var tag = mk.querySelector('.f-tag.on'); if (tag && !/^all$/i.test(txt(tag))) out.push({ k: 'sector', el: tag, label: 'Sector: ' + txt(tag).replace(/^[^A-Za-z]+/, '') });
    var si = document.getElementById('searchIn'); if (si && si.value.trim()) out.push({ k: 'q', label: '“' + si.value.trim() + '”' });
    return out;
  }
  function visibleCount() { var mk = document.getElementById('mkx'); return mk ? Array.prototype.filter.call(mk.querySelectorAll('#tab-browse .sponsored-card, #tab-browse .lcard, #tab-browse .scard, #tab-browse .jcard'), function (c) { return c.style.display !== 'none'; }).length : 0; }
  function refilter() { if (window.updateLiveCount) window.updateLiveCount(); }
  function removeChip(f) {
    var mk = document.getElementById('mkx');
    if (f.k === 'cats') mk.querySelectorAll('.cat-cb').forEach(function (c) { c.checked = true; });
    if (f.k === 'cb') f.el.checked = false;
    if (f.k === 'sector') { var all = mk.querySelector('.f-tag'); if (all) all.click(); }
    if (f.k === 'q') { var si = document.getElementById('searchIn'); si.value = ''; si.dispatchEvent(new Event('input')); }
    mk.querySelectorAll('.cat-item.on').forEach(function (x) { if (f.k === 'cats') x.classList.remove('on'); });
    refilter();
  }
  var chipSig = '';
  function chips() {
    var mk = document.getElementById('mkx'); if (!mk) return;
    var main = mk.querySelector('#tab-browse .main'); if (!main) return;
    var bar = main.querySelector(':scope > .dx-chips');
    var fs = activeFilters(), n = visibleCount(), sig = fs.map(function (f) { return f.label; }).join('|') + '#' + n;
    if (sig === chipSig && bar) return; chipSig = sig;
    if (!bar) { bar = document.createElement('div'); bar.className = 'dx-chips'; main.insertBefore(bar, main.firstChild); }
    if (!fs.length) { bar.innerHTML = ''; bar.style.display = 'none'; return; }
    bar.style.display = '';
    var html = fs.map(function (f, i) { return '<span class="dx-chip">' + esc(f.label) + '<button type="button" data-i="' + i + '" aria-label="Remove filter">×</button></span>'; }).join('') + '<button type="button" class="dx-chip-clear">Clear all</button>';
    if (n === 0) {
      /* try removing each filter on its own and suggest the one that brings back the most */
      var best = null;
      fs.forEach(function (f, i) {
        if (f.k !== 'cb') return;
        f.el.checked = false; refilter(); var k = visibleCount(); f.el.checked = true; refilter();
        if (k > 0 && (!best || k > best.k)) best = { i: i, k: k, label: f.label };
      });
      html += '<div class="dx-nores">' + ic('search') + 'No listings match all these filters.' + (best ? ' <button type="button" class="dx-suggest" data-i="' + best.i + '">Remove “' + esc(best.label) + '” to see ' + best.k + ' listing' + (best.k === 1 ? '' : 's') + '</button>' : '') + '</div>';
    }
    bar.innerHTML = html;
    bar.onclick = function (e) {
      var b = e.target.closest('button'); if (!b) return;
      if (b.classList.contains('dx-chip-clear')) { activeFilters().forEach(function (f) { if (f.k !== 'sector') removeChip(f); }); var sec = activeFilters().find(function (f) { return f.k === 'sector'; }); if (sec) removeChip(sec); touched = false; chipSig = ''; return; }
      var f = activeFilters()[+b.dataset.i]; if (f) removeChip(f); chipSig = '';
    };
  }

  /* filters change visibility without adding elements — refresh the chips on every filter action */
  function soonChips() { setTimeout(function () { C.run('filter-chips', chips); }, 40); }
  document.addEventListener('change', function (e) { if (e.target.closest && e.target.closest('#mkx')) soonChips(); });
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#mkx .f-tag, #mkx .cat-item, #mkx .f-opt, #mkx .sort-opt, .dbk-empty')) soonChips(); });
  document.addEventListener('input', function (e) { if (e.target.id === 'searchIn') soonChips(); });

  /* partner levels removed by decision: no levels of any kind */
  C.onRender('certificate-wall', certWall);
  C.onRender('skills-honeycomb', honeycomb);
  C.onRender('glossary', glossary);
  C.onRender('quick-view', quickButtons);
  C.onRender('filter-chips', chips);
  C.onPage('chat-dock', drawDock);
})();
