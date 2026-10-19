/* Marketplace — the parts a lister and a buyer need beyond the approved page (B-06 … B-10):
   · My Listings is one list the page draws from a service: Edit, Pause / Resume, Delete, Renew, real views and inquiries
     (window.dxMarketSvc: this browser in the demo, the database in the live app — the adapter replaces it)
   · "Quote →" on a buyer's request sends a priced quote into Requests & deals (never only a chat)
   · the category tiles also show / hide the buyers' requests board, so "Supply" shows only supply
   · a price typed as a bare number carries the form's currency (the field says "$5.80": US$)
   · a company page's Listings tab names the listings its team published
   The approved markup is reused: rows are copies of the approved My Listings row, windows are the kit's windows. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function orig(el) { return el ? (window.dxOrigText ? window.dxOrigText(el) : el.textContent).replace(/\s+/g, ' ').trim() : ''; }
  var DAY = 864e5;
  var EM = { supply: '⚗️', demand: '🔍', cmo: '🏭', equipment: '⚙️', license: '📋', service: '🛠️', job: '💼', training: '🎓' };

  /* ── the demo's service: the demo account's own listings, kept in this browser ── */
  function seedRows() {   /* the approved sample rows are the demo account's listings: read once, then kept */
    var out = [], m = document.getElementById('tab-manage'); if (!m) return out;
    m.querySelectorAll('div[style*="padding:14px 0"]:not([data-ml])').forEach(function (r, i) {
      var info = r.children[1], t = info && info.children[0], b = t && t.querySelector('span'), sub = orig(info && info.children[1]);
      var name = t ? orig(t).replace(orig(b), '').trim() : 'Listing', st = orig(b).toLowerCase();
      var posted = /Posted (\d+) days? ago/.exec(sub), exp = /Expires in (\d+) days?/.exec(sub), nums = r.children[2] ? r.children[2].querySelectorAll('b') : [];
      out.push({ id: 'S' + i, title: name, em: txt(r.children[0]) || '📦', type: /cmo|manufactur/i.test(name) ? 'cmo' : /registration|licen/i.test(name) ? 'license' : 'supply',
        status: st === 'paused' ? 'paused' : 'active', boosted: st === 'boosted', posted: Date.now() - (posted ? +posted[1] : 0) * DAY, exp: exp ? Date.now() + (+exp[1]) * DAY : null,
        views: nums[0] ? +txt(nums[0]).replace(/\D/g, '') : 0, inquiries: nums[1] ? +txt(nums[1]).replace(/\D/g, '') : 0, price: '', moq: '' });
    });
    return out;
  }
  function mine() { var l = D.store.get('mkMine', null); if (!Array.isArray(l)) { l = seedRows(); if (l.length) D.store.set('mkMine', l); } return l || []; }
  function keep(l) { D.store.set('mkMine', l); }
  function period(type) { return type === 'license' ? null : (type === 'cmo' ? 90 : 30) * DAY; }
  var demo = {
    live: false,
    listings: function () { return Promise.resolve(mine()); },
    publish: function (d, status) {
      var a = window.dxDir && window.dxDir.mine && window.dxDir.mine(), l = mine();
      l.unshift({ id: 'L' + Date.now(), title: d.title, em: EM[d.type] || '📦', type: d.type, status: status, boosted: false, posted: Date.now(), exp: status === 'draft' || !period(d.type) ? null : Date.now() + period(d.type),
        views: 0, inquiries: 0, price: d.price || '', moq: d.moq || '', slug: a ? a.slug : null });
      keep(l); return Promise.resolve(true);
    },
    update: function (id, patch) { var l = mine(), r = l.find(function (x) { return x.id === id; }); if (r) Object.assign(r, patch); keep(l); return Promise.resolve(true); },
    remove: function (id) { keep(mine().filter(function (x) { return x.id !== id; })); return Promise.resolve(true); },
    renew: function (id) { var l = mine(), r = l.find(function (x) { return x.id === id; }); if (r) { r.exp = Date.now() + (period(r.type) || 30 * DAY); if (r.status === 'expired') r.status = 'active'; } keep(l); return Promise.resolve(true); },
    quote: function (c, q) {   /* the demo's buyers are sample people: the quote is a deal in this browser, shown in Requests & deals */
      var DL = window.dxDeals, a = window.dxDir && window.dxDir.mine && window.dxDir.mine(); if (!DL) return Promise.reject(new Error('Requests & deals are not available'));
      if (!a) return Promise.reject(new Error('Create or claim your company page first'));
      var d = DL.mk('quote', { slug: null, name: c.buyer || 'Buyer', person: true }, a.slug, c.title, { product: c.title, qty: q.qty || '' }, 'Request posted in the Marketplace: ' + c.title);
      d.status = 'quoted'; d.offer = { price: q.price, validity: '14 days', terms: '', lead: q.lead || '', note: q.note || '' };
      d.events.push({ at: Date.now(), by: 'to', kind: 'quote', text: 'Send quote: ' + q.price + (q.lead ? ' · lead time ' + q.lead : '') + (q.note ? ' — ' + q.note : ''), data: q });
      DL.save(d); return Promise.resolve(true);
    },
    saved: function () {   /* the cards saved with 🔖 on this page (the page keeps them as "<category>:<title>") */
      return Promise.resolve((D.store.get('saved', []) || []).map(function (k) { var i = String(k).indexOf(':'); return { title: String(k).slice(i + 1), cat: String(k).slice(0, i) }; })); },
    companyListings: function (co) { return mine().filter(function (r) { return r.slug === co.slug && r.status === 'active'; }).map(function (r) { return { t: r.title, type: (r.type || 'supply').toUpperCase() }; }); }
  };
  function svc() { return window.dxMarketSvc || demo; }
  window.dxMarket = { paint: function () { paintManage(); }, demoSvc: demo, EM: EM };

  /* ── My Listings, drawn from the service ── */
  var TPL = null;
  function daysTo(t) { return Math.max(0, Math.ceil((t - Date.now()) / DAY)); }
  function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }
  function state(r) {
    if (r.status === 'draft') return 'draft'; if (r.status === 'paused') return 'paused';
    if (r.exp && r.exp <= Date.now()) return 'expired'; if (r.boosted) return 'boosted'; if (r.exp && r.exp - Date.now() < 7 * DAY) return 'soon'; return 'active';
  }
  var BADGE = { draft: ['Draft', '#f1f5f9', '#475569'], paused: ['Paused', '#f1f5f9', '#64748b'], expired: ['Expired', '#fee2e2', '#b91c1c'], boosted: ['Boosted', '#fef9c3', '#a16207'],
    soon: ['Expiring soon', '#fef3c7', '#92400e'], active: ['Active', '#dcfce7', '#15803d'] };
  function btn(label, extra, bg, fg, data) { return '<button type="button" data-ml-a="' + data + '" style="padding:6px 12px;border-radius:7px;font-size:11.5px;font-weight:700;border:none;cursor:pointer;background:' + bg + ';color:' + fg + (extra || '') + '">' + label + '</button>'; }
  function rowEl(r) {
    var row = document.createElement('div'); row.innerHTML = TPL; row = row.firstElementChild; row.setAttribute('data-ml', r.id); row.style.opacity = r.status === 'paused' ? '0.5' : '';
    var k = row.children, s = state(r), b = BADGE[s];
    if (k[0]) k[0].textContent = r.em || '📦';
    var info = k[1], t = info && info.children[0], sub = info && info.children[1];
    if (t) { t.innerHTML = '<span data-noi18n></span> <span style="font-size:9.5px;font-weight:800;padding:2px 7px;border-radius:5px;background:' + b[1] + ';color:' + b[2] + ';text-transform:uppercase"></span>';
      t.children[0].textContent = r.title; t.children[1].textContent = b[0]; }
    var age = Math.floor((Date.now() - (r.renewed || r.posted)) / DAY);
    if (sub) sub.textContent = s === 'draft' ? 'Saved ' + (age ? plural(age, 'day') + ' ago' : 'just now') + ' · not published'
      : (r.renewed ? 'Renewed ' : 'Posted ') + (age ? plural(age, 'day') + ' ago' : 'just now') + ' · ' + (s === 'expired' ? 'Expired — renew to show it again' : r.exp ? 'Expires in ' + plural(daysTo(r.exp), 'day') : 'No expiry (license sale)');
    if (k[2]) k[2].innerHTML = '<div><b style="color:#0f172a">' + (+r.views || 0).toLocaleString('en-US') + '</b> ' + (r.views === 1 ? 'view' : 'views') + '</div><div><b style="color:#0f172a">' + (+r.inquiries || 0).toLocaleString('en-US') + '</b> ' + (r.inquiries === 1 ? 'inquiry' : 'inquiries') + '</div>';
    if (k[3]) k[3].innerHTML = (s === 'paused' ? btn('Resume', '', '#f4f6fb', '#0f172a', 'resume') : s === 'expired' ? btn('Renew Now', '', '#d97706', '#fff', 'renew') : btn('Edit', '', '#f4f6fb', '#0f172a', 'edit')) +
      (s === 'active' || s === 'soon' ? '<button type="button" onclick="openBoostModal(\'boost\')" style="padding:6px 12px;border-radius:7px;font-size:11.5px;font-weight:700;border:none;cursor:pointer;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff">⭐ Boost</button>' : '') +
      btn('···', ';width:32px', '#f4f6fb', '#475569', 'more');
    return row;
  }
  var ROWS = [], PAINTING = 0;
  function paintManage(rows) {
    var m = document.getElementById('tab-manage'); if (!m) return;
    var sample = [].slice.call(m.querySelectorAll('div[style*="padding:14px 0"]:not([data-ml])'));
    if (!TPL && sample.length) TPL = sample[sample.length - 1].outerHTML.replace(/border-bottom:1px solid #f4f6fb;?/, '');
    if (!TPL) return;
    if (!rows) { var my = ++PAINTING; svc().listings().then(function (l) { if (my === PAINTING) paintManage(l || []); }, function (e) { D.toast((e && e.message) || 'Could not load your listings'); }); return; }
    ROWS = rows;
    var list = m.querySelector('[data-ml-list]') || (sample[0] && sample[0].parentElement); if (!list) return; list.setAttribute('data-ml-list', '1');
    sample.forEach(function (x) { x.remove(); }); list.querySelectorAll('[data-ml], .dx-mk-empty').forEach(function (x) { x.remove(); });
    rows.forEach(function (r, i) { var e = rowEl(r); if (i < rows.length - 1) e.style.borderBottom = '1px solid #f4f6fb'; list.appendChild(e); });
    if (!rows.length) list.insertAdjacentHTML('beforeend', '<div class="dx-mk-empty" style="padding:18px;color:#65676b;font-size:13px">You have no listings yet — publish one with “New Listing”.</div>');
    /* the four numbers: active listings, views, inquiries, boosted */
    var st = m.querySelectorAll('div[style*="font-size:18px;font-weight:800"]'), act = rows.filter(function (r) { var s = state(r); return s === 'active' || s === 'soon' || s === 'boosted'; });
    var vals = [act.length, rows.reduce(function (a, r) { return a + (+r.views || 0); }, 0), rows.reduce(function (a, r) { return a + (+r.inquiries || 0); }, 0), rows.filter(function (r) { return state(r) === 'boosted'; }).length];
    [].forEach.call(st, function (e, i) { if (i < 4) { e.textContent = vals[i].toLocaleString('en-US'); if (e.parentElement) e.parentElement.style.display = ''; } });
    /* the expiry notice: the listing that runs out first, within a week */
    var note = [].find.call(m.querySelectorAll('div[style*="#fffbeb"]'), function (x) { return /Expiry notice|Renew/.test(orig(x)); });
    var due = rows.filter(function (r) { return r.status === 'active' && r.exp && r.exp > Date.now() && r.exp - Date.now() < 7 * DAY; }).sort(function (a, b) { return a.exp - b.exp; })[0];
    if (note) {
      if (!due) note.style.display = 'none';
      else { note.style.display = ''; note.setAttribute('data-ml-due', due.id);
        var b = note.querySelector('button'); note.textContent = 'Expiry notice: "' + due.title + '" expires in ' + plural(daysTo(due.exp), 'day') + ' — listings auto-expire to keep the marketplace fresh ';
        if (b) { b.setAttribute('data-ml-a', 'renew'); note.appendChild(b); } }
    }
  }
  function rowOf(el) { var r = el.closest('[data-ml]') || el.closest('[data-ml-due]'), id = r ? r.getAttribute('data-ml') || r.getAttribute('data-ml-due') : null; return ROWS.find(function (x) { return String(x.id) === String(id); }); }
  function done(p, msg) { return Promise.resolve(p).then(function () { if (msg) D.toast(msg); paintManage(); }, function (e) { D.toast((e && e.message) || 'Could not save'); paintManage(); }); }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#tab-manage [data-ml-a]'); if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var r = rowOf(b), a = b.getAttribute('data-ml-a'); if (!r) return;
    if (a === 'renew') return done(svc().renew(r.id), 'Renewed — it shows for another ' + (r.type === 'cmo' ? 90 : 30) + ' days');
    if (a === 'resume') return done(svc().update(r.id, { status: 'active' }), 'Listing resumed');
    if (a === 'edit') {
      D.modal({ title: 'Edit listing', body: '<div class="dbk-f"><label for="mlT">Title *</label><input id="mlT" data-req maxlength="200" value="' + esc(r.title) + '"></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="mlP">Price</label><input id="mlP" maxlength="60" value="' + esc(r.price || '') + '" placeholder="e.g. US$ 5.80"></div><div class="dbk-f"><label for="mlM">MOQ / quantity</label><input id="mlM" maxlength="80" value="' + esc(r.moq || '') + '"></div></div>',
        primary: { label: 'Save changes', onClick: function (box) { if (!D.requireFields(box)) return false;
          done(svc().update(r.id, { title: box.querySelector('#mlT').value.trim(), price: money(box.querySelector('#mlP').value.trim(), '$'), moq: box.querySelector('#mlM').value.trim() }), 'Listing updated'); } } });
      return;
    }
    if (a === 'more') {
      var paused = r.status === 'paused', draft = r.status === 'draft';
      var m = D.modal({ title: r.title, secondary: 'Close', body: (draft ? '<button type="button" class="dbk-btn s" data-x="publish">✅ Publish listing</button>' : '<button type="button" class="dbk-btn s" data-x="boost">⭐ Boost this listing</button><button type="button" class="dbk-btn s" data-x="pause">' + (paused ? '▶ Resume listing' : '⏸ Pause listing') + '</button>') +
        (r.exp || r.status === 'expired' ? '<button type="button" class="dbk-btn s" data-x="renew">🔁 Renew listing</button>' : '') + '<button type="button" class="dbk-btn d" data-x="del">🗑 Delete listing</button>' });
      m.el.addEventListener('click', function (ev) {
        var x = ev.target.closest && ev.target.closest('[data-x]'); x = x && x.getAttribute('data-x'); if (!x) return; m.close();
        if (x === 'boost') window.openBoostModal('boost');
        if (x === 'publish') done(svc().update(r.id, { status: 'active' }), 'Your listing is live');
        if (x === 'pause') done(svc().update(r.id, { status: paused ? 'active' : 'paused' }), paused ? 'Listing resumed' : 'Listing paused — hidden from buyers');
        if (x === 'renew') done(svc().renew(r.id), 'Renewed — it shows for another ' + (r.type === 'cmo' ? 90 : 30) + ' days');
        if (x === 'del') D.modal({ title: 'Delete this listing?', body: '<p>“' + esc(r.title) + '” is removed from the Marketplace and from your company page.</p>', primary: { label: 'Delete listing', danger: true, onClick: function () { done(svc().remove(r.id), 'Listing deleted'); } } });
      });
    }
  }, true);

  /* ── creating: the price keeps its currency; a draft and a published listing are this person's listings ── */
  function money(v, ph) { v = String(v || '').trim(); if (!/^[\d.,]+(\s*\/\s*\S+)?$/.test(v)) return v; var cur = /€/.test(ph) ? '€' : /EGP|ج\.م/.test(ph) ? 'EGP ' : /\$/.test(ph) ? 'US$ ' : ''; return cur ? cur + v : v; }
  function priceInput(f) { var out = null; f.querySelectorAll('.field').forEach(function (fd) { var l = orig(fd.querySelector('.field-label')); if (!out && /price|budget|fee|rate/i.test(l) && !/target/i.test(l)) out = fd.querySelector('input'); }); return out; }
  function formData(f) {
    var v = function (rx) { var out = ''; f.querySelectorAll('.field').forEach(function (fd) { var l = orig(fd.querySelector('.field-label')), i = fd.querySelector('input:not([type=file]),textarea'); if (!out && i && rx.test(l)) out = i.value.trim(); }); return out; };
    var first = f.querySelector('.field-input'), chips = [];
    f.querySelectorAll('.chip.selected,.chip.cert-verified').forEach(function (ch) { chips.push(txt(ch).replace(/^✅\s*/, '')); });
    return { type: f.id.replace('form-', ''), title: first ? first.value.trim() : '', price: v(/price|budget|salary|fee|rate/i), moq: v(/moq|quantity|capacity|volume/i), where: v(/origin|country|location|site|city/i),
      lead: v(/lead time|shipping|timeline|duration/i), desc: (f.querySelector('textarea') || {}).value || '', certs: chips.slice(0, 4) };
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mkx .btn-create, #mkx .btn-draft'); if (!b) return;
    var f = b.closest('.form-section'); if (!f) return;
    var pi = priceInput(f); if (pi) { var nv = money(pi.value, pi.placeholder || ''); if (nv !== pi.value) pi.value = nv; }
    if (b.classList.contains('btn-draft')) { var d = formData(f); if (!d.title) return;
      e.stopImmediatePropagation();   /* the draft is this person's listing (My Listings), in this browser or the database */
      svc().publish(d, 'draft').then(function () { f.querySelectorAll('input:not([type=file]),textarea').forEach(function (i) { i.value = ''; }); D.toast('Draft saved — find it in My Listings'); if (window.switchMasterTab) window.switchMasterTab('manage'); paintManage(); },
        function (er) { D.toast((er && er.message) || 'Could not save the draft'); }); }
  }, true);
  /* published from the preview window (the page's own hook): the demo keeps it among my listings; the live app saves it */
  var hookPrev = window.dxLiveHook;
  window.dxLiveHook = function (kind, d) {
    if (kind === 'listing' && d && !svc().live) { demo.publish(d, 'active'); setTimeout(function () { paintManage(); demoCounts(); }, 50); }
    return hookPrev ? hookPrev.apply(this, arguments) : undefined;
  };

  /* ── "Quote →" on a buyer's request: a priced quote ── */
  function quoteDialog(card) {
    var t = card.querySelector('.dc-title'), tc = t ? t.cloneNode(true) : null; if (tc) tc.querySelectorAll('.role-badge').forEach(function (x) { x.remove(); });
    var c = { title: tc ? txt(tc) : 'Request', buyer: txt(card.querySelector('.dc-buyer')).replace(/✓/g, '').trim(), live: card.getAttribute('data-live') };
    D.modal({ title: 'Send a quote — ' + c.title, body: '<p class="cp-muted">Your quote goes to ' + esc(c.buyer || 'the buyer') + ' in Requests & deals, where they can accept it, counter or decline.</p>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="qtP">Your price *</label><input id="qtP" data-req placeholder="e.g. US$ 21 per kg"></div><div class="dbk-f"><label for="qtQ">Quantity</label><input id="qtQ" placeholder="e.g. 2 MT"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="qtL">Lead time</label><input id="qtL" placeholder="e.g. 3 weeks"></div><div class="dbk-f"><label for="qtN">Note</label><input id="qtN" maxlength="500" placeholder="e.g. CEP and CoA available"></div></div>',
      primary: { label: 'Send quote', onClick: function (box, close) { if (!D.requireFields(box)) return false; var ok = box.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        var q = { price: money(box.querySelector('#qtP').value.trim(), '$'), qty: box.querySelector('#qtQ').value.trim(), lead: box.querySelector('#qtL').value.trim(), note: box.querySelector('#qtN').value.trim() };
        svc().quote(c, q).then(function () { close(); D.toast('Quote sent to ' + (c.buyer || 'the buyer') + ' — follow it in Requests & deals'); },
          function (er) { if (ok) ok.disabled = false; D.toast((er && er.message) || 'Could not send the quote'); });
        return false; } } });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mkx .dcard .qt-btn'); if (!b) return;
    e.preventDefault(); e.stopImmediatePropagation(); quoteDialog(b.closest('.dcard'));
  }, true);

  /* ── the demo's category numbers count the listings on its page (the live app's come from the database) ── */
  function demoCounts() {
    if (svc().live) return; var mk = document.getElementById('mkx'); if (!mk) return;
    var n = {}; mk.querySelectorAll('#tab-browse .lcard, #tab-browse .sponsored-card, #tab-browse .dcard, #tab-browse .scard, #tab-browse .jcard').forEach(function (c) {
      var k = c.classList.contains('dcard') ? 'demand' : c.classList.contains('scard') ? 'service' : c.classList.contains('jcard') ? 'job' : (c.dataset.cat || c.dataset.dxcat || 'supply'); n[k] = (n[k] || 0) + 1; });
    mk.querySelectorAll('.cat-grid .cat-item').forEach(function (it) { var k = it.dataset.dxcat, e = it.querySelector('.cat-count'); if (k && e) { var v = (n[k] || 0).toLocaleString('en-US'); if (e.textContent !== v) e.textContent = v; } });
    mk.querySelectorAll('.f-count[data-cat]').forEach(function (e) { var v = (n[e.dataset.cat] || 0).toLocaleString('en-US'); if (e.textContent !== v) e.textContent = v; });
    if (window.categoryTotals) Object.keys(window.categoryTotals).forEach(function (k) { window.categoryTotals[k] = n[k] || 0; });
  }

  /* ── the buyers' requests board follows the category tiles (it is outside the cards the page filters) ── */
  function syncDemand() {
    var mk = document.getElementById('mkx'); if (!mk) return;
    var cb = mk.querySelector('.cat-cb[data-cat="demand"]'), on = !cb || cb.checked;
    var si = document.getElementById('searchIn'), q = si && si.value ? si.value.trim().toLowerCase() : '';
    mk.querySelectorAll('#tab-browse .dcard').forEach(function (c) { var ok = on && (!q || q.split(/\s+/).every(function (w) { return txt(c).toLowerCase().indexOf(w) >= 0; })); var d = ok ? '' : 'none'; if (c.style.display !== d) c.style.display = d; });
  }
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#mkx')) setTimeout(syncDemand, 0); });
  document.addEventListener('change', function (e) { if (e.target.closest && e.target.closest('#mkx')) setTimeout(syncDemand, 0); });
  document.addEventListener('input', function (e) { if (e.target && e.target.id === 'searchIn') setTimeout(syncDemand, 0); });

  /* ── Saved: the marketplace listings saved with 🔖, below the saved posts ── */
  var CATW = { supply: 'Supply', demand: 'Demand', cmo: 'CMO', equipment: 'Equipment', license: 'License', service: 'Service', job: 'Job', training: 'Training' };
  function paintSaved(c, list) {
    var host = c.querySelector('.saved-list') || c.firstElementChild || c; c.querySelectorAll('.dx-saved-listings').forEach(function (x) { x.remove(); });
    if (!list.length) return;
    var box = document.createElement('div'); box.className = 'dx-saved-listings'; box.style.marginTop = '18px';
    box.innerHTML = '<h2 style="font-size:17px;font-weight:800;color:var(--cx);margin:0 0 10px">🛒 Saved listings</h2>' + list.map(function (x, i) {
      return '<div class="mr-row" style="background:#fff;border:1px solid #eef0f4;border-radius:12px;padding:10px 14px;margin-bottom:8px;display:flex;align-items:center;gap:10px"><div class="mr-b" style="flex:1;min-width:0"><b data-noi18n></b><small>' + esc(CATW[x.cat] || 'Listing') + (x.price ? ' · <span data-noi18n></span>' : '') + '</small></div>' +
        '<button type="button" class="dr-btn sm" data-svl="' + i + '">View in Marketplace</button></div>'; }).join('');
    host.appendChild(box);
    list.forEach(function (x, i) { var r = box.querySelectorAll('.mr-row')[i]; r.querySelector('b').textContent = x.title; var p = r.querySelector('small span'); if (p) p.textContent = x.price; });
    box.addEventListener('click', function (e) { var b = e.target.closest('[data-svl]'); if (!b) return; var x = list[+b.dataset.svl]; window.goto('market');
      var si = document.getElementById('searchIn'); if (si) { si.value = x.title; if (window.__mkxFilter) window.__mkxFilter(x.title); syncDemand(); } });
  }
  var oSaved = window.renderSaved;
  if (typeof oSaved === 'function') window.renderSaved = function (c) {
    var r = oSaved.apply(this, arguments);
    Promise.resolve(svc().saved ? svc().saved() : []).then(function (l) { if (document.body.getAttribute('data-page') === 'saved' && c && c.isConnected) paintSaved(c, l || []); }, function () {});
    return r;
  };

  /* ── the company page's Listings tab: the listings its team published ── */
  function wrapOffers() {
    var X = window.dxDir; if (!X || !X.offersOf || X.offersOf.__mk) return;
    var o = X.offersOf; X.offersOf = function (co) { var base = o.apply(this, arguments) || [], add = co && svc().companyListings ? svc().companyListings(co) || [] : [];
      var seen = {}; base.forEach(function (x) { seen[x.t] = 1; }); return base.concat(add.filter(function (x) { return !seen[x.t]; })); };
    X.offersOf.__mk = true;
  }
  wrapOffers();
  C.onRender('market-manage', function () { wrapOffers(); if (document.body.getAttribute('data-page') !== 'market') return; syncDemand(); demoCounts(); var m = document.getElementById('tab-manage'); if (m && !m.querySelector('[data-ml], [data-ml-list] .dx-mk-empty')) paintManage(); });
  document.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('#mkx .master-tab[data-tab="manage"]'); if (t) setTimeout(function () { paintManage(); }, 0); });
})();
