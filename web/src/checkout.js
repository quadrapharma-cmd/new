/* Checkout: payment methods in the VIP payment window, the create-company wizard and the boost window — card, Vodafone Cash &
   wallets, Fawry, InstaPay; included VIP boosts; My payments (Market → My Listings) and the company's payment history with its
   invoices (Workspace → Plan & verification). In the live app window.dxPay (adapter) starts the real payment and reads the
   orders; in the demo the same steps run on sample data kept in this browser (no money moves). */
(function () {
  var D = window.DBK; if (!D) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var M = [['card', '💳', 'Card', 'Visa · Mastercard · Meeza'], ['wallet', '📱', 'Vodafone Cash & wallets', 'Vodafone Cash · Orange Cash · e& money · WE Pay'],
           ['fawry', '🏪', 'Fawry', 'Pay at any Fawry outlet or in the myFawry app'], ['instapay', '⚡', 'InstaPay', 'Transfer, then send us the receipt']];
  var MNAME = { card: 'Card', wallet: 'Mobile wallet', fawry: 'Fawry', instapay: 'InstaPay' };
  function methods(name) { return '<div class="dx-pay"><div class="dx-pay-t">Pay with</div>' + M.map(function (m, i) { return '<label class="dx-pay-m"><input type="radio" name="' + name + '" value="' + m[0] + '"' + (i ? '' : ' checked') + '><span class="dx-pay-i">' + m[1] + '</span><span><b>' + m[2] + '</b><small>' + m[3] + '</small></span></label>'; }).join('') + '</div>'; }
  function chosen(root, name) { var r = root.querySelector('input[name=' + name + ']:checked'); return r ? r.value : 'card'; }
  /* amounts: 'EGP 1,653' in English, '1,653 ج.م' in Arabic — Latin digits in both, like the rest of the Arabic interface */
  function ar() { return window.LANG === 'ar'; }
  function egp(n) { n = Math.round(Number(n) || 0).toLocaleString('en', { maximumFractionDigits: 0 }); return ar() ? n + ' ج.م' : 'EGP ' + n; }
  function fmt(t, time) { return t ? (window.dxFmtDate ? window.dxFmtDate(t, !!time, 'en') : new Date(t).toLocaleString()) : ''; }

  /* ── the demo's payment service (the live adapter replaces window.dxPay): the server's prices, sample orders in this browser ── */
  var PRICES = { boost: [1450, 7, 'Marketplace boost', 'boost'], featured: [3950, 30, 'Featured listing', 'featured'], vip_month: [2500, 30, 'VIP — monthly', 'vip'], vip_year: [25000, 365, 'VIP — yearly', 'vip'] };   /* = payment_products */
  function st(k, v) { try { if (v === undefined) return JSON.parse(localStorage.getItem('dx_' + k) || 'null'); localStorage.setItem('dx_' + k, JSON.stringify(v)); } catch (e) { return null; } }
  function demoOrders() { var l = st('payments'); if (!Array.isArray(l)) l = []; return l; }
  function demoSave(l) { st('payments', l.slice(0, 100)); }
  function month() { return new Date().toISOString().slice(0, 7); }
  function split(code) { var p = PRICES[code], net = p[0], vat = Math.round(net * 14) / 100; return { net: net, vat: vat, total: net + vat }; }
  function demoOrder(code, method, o, status) {
    var l = demoOrders(), n = 9000 + l.length + 1, s = split(code), now = new Date().toISOString();
    var x = { id: 'D' + n, order: 'DBX' + n, code: code, product: PRICES[code][2], kind: PRICES[code][3], method: method, status: status, total: s.total, net: s.net, vat: s.vat, created_at: now,
      paid_at: status === 'paid' ? now : null, invoice_no: status === 'paid' ? 'DBX-INV-' + now.slice(0, 4) + '-' + ('00000' + (l.filter(function (y) { return y.invoice_no; }).length + 1)).slice(-6) : null,
      listing: o.listing || '', company: o.company || '', slug: o.slug || null };
    if (method === 'fawry') { x.fawry_reference = String(Math.floor(1e11 + Math.random() * 9e11)); x.fawry_expires_at = new Date(Date.now() + 48 * 3600e3).toISOString(); }
    l.unshift(x); demoSave(l); return x;
  }
  function demoCompany(slug) { var c = slug && window.dxDir && window.dxDir.bySlug(slug); return c ? c.name : ''; }
  if (!window.dxPay) window.dxPay = {
    live: false,
    quote: function (code) { var p = PRICES[code]; if (!p) return Promise.reject(new Error('This product is not on sale at the moment')); var s = split(code); return Promise.resolve({ amount_egp: s.net, vat_egp: s.vat, total_egp: s.total, days: p[1] }); },
    start: function (o) {
      var x = demoOrder(o.product, o.method, { listing: o.listingName || '', company: demoCompany(o.slug), slug: o.slug }, o.method === 'card' || o.method === 'wallet' ? 'paid' : 'pending');
      if (x.method === 'fawry') return Promise.resolve({ order_id: x.id, reference: x.order, amount: x.total, fawry_reference: x.fawry_reference, expires_at: x.fawry_expires_at, demo: true });
      if (x.method === 'instapay') return Promise.resolve({ order_id: x.id, reference: x.order, amount: x.total, instapay: { address: 'drugbox@instapay', name: 'Drugbox Egypt' }, demo: true });
      return Promise.resolve({ order_id: x.id, reference: x.order, amount: x.total, paid: true, demo: true });
    },
    cancel: function (id) { var l = demoOrders(), hit = false; l.forEach(function (x) { if (x.id === id && x.status === 'pending') { x.status = 'cancelled'; hit = true; } }); demoSave(l);
      return hit ? Promise.resolve('cancelled') : Promise.reject(new Error('Only a payment that is still waiting can be cancelled')); },
    submitInstapay: function (id, ref) { var l = demoOrders(); l.forEach(function (x) { if (x.id === id) { x.status = 'review'; x.transfer = ref; } }); demoSave(l); return Promise.resolve(); },
    orders: function (slug) { var me = (window.ME || {}).id;
      if (slug === 'quadra-pharm' && !st('payments_seeded')) {               /* the demo's VIP company has paid for its VIP once */
        var l = demoOrders(), s = split('vip_month'); l.push({ id: 'D8001', order: 'DBX8001', code: 'vip_month', product: 'VIP — monthly', kind: 'vip', method: 'card', status: 'paid', total: s.total, net: s.net, vat: s.vat,
          created_at: '2026-09-20T09:12:00Z', paid_at: '2026-09-20T09:14:00Z', invoice_no: 'DBX-INV-2026-000001', company: 'Quadra Pharm', slug: 'quadra-pharm' }); demoSave(l); st('payments_seeded', 1); }
      return Promise.resolve(demoOrders().filter(function (x) { return slug ? x.slug === slug && x.kind === 'vip' : x.kind !== 'vip' || !x.slug; })); },
    invoice: function (id) { var x = demoOrders().find(function (y) { return y.id === id; }); if (!x || x.status !== 'paid') return Promise.reject(new Error('An invoice is issued once the payment is confirmed'));
      return Promise.resolve({ invoice_no: x.invoice_no, issued_at: x.paid_at, order: x.order, method: x.method, product: x.product, days: PRICES[x.code][1], net: x.net, vat: x.vat, vat_rate: 0.14, total: x.total, currency: 'EGP',
        seller: { name: 'Drugbox', tax_reg_no: null, address: null }, buyer: { name: (window.ME || {}).name || '' }, company: x.company ? { name: x.company } : null, listing: x.listing || null, demo: true }); },
    included: function (slug) { var c = slug && window.dxDir && window.dxDir.bySlug(slug); if (!c || c.plan !== 'vip') return Promise.resolve(0); var u = st('vip_boosts') || {}; return Promise.resolve(Math.max(0, 3 - ((u[slug] || {})[month()] || 0))); },
    useIncluded: function (lid, slug) { var u = st('vip_boosts') || {}, m = month(); u[slug] = u[slug] || {}; if ((u[slug][m] || 0) >= 3) return Promise.reject(new Error('All 3 included boosts of this month are used — they renew on the 1st'));
      u[slug][m] = (u[slug][m] || 0) + 1; st('vip_boosts', u); return Promise.resolve({ left: 3 - u[slug][m] }); }
  };

  /* Boost / Featured: window.dxPay.quote gives the price the server charges — never USD × a third-party FX rate, and no FX request
     is made (the demo's quote is the same price list as payment_products). */
  function hasQuote() { return !!(window.dxPay && typeof window.dxPay.quote === 'function'); }
  function paintQuote(q, plan) {
    var $ = function (id) { return document.getElementById(id); }; if (!$('bmPayBtn')) return;
    var base = Number(q.amount_egp) || 0, vat = Number(q.vat_egp) || 0, total = Number(q.total_egp) || base + vat, feat = plan === 'featured';
    var bm = $('boostModalOverlay'), A = ar(), lb = bm.querySelectorAll('.bm-row > span:first-child'), cb = bm.querySelector('.btn-bm-close'), box = bm.querySelector('.boost-modal'), days = Number(q.days) || 0;
    /* the same labels and direction as the approved window draws for the interface language (it is not called here: it would fetch the FX rate) */
    if (box) box.style.direction = A ? 'rtl' : 'ltr'; if (cb) { cb.style.left = A ? '' : 'auto'; cb.style.right = A ? '' : '18px'; }
    if (bm.querySelector('.bm-title')) bm.querySelector('.bm-title').textContent = feat ? (A ? '⭐ إعلان مميز (Featured)' : '⭐ Make your listing Featured') : (A ? '⭐ ترقية الإعلان (Boost)' : '⭐ Boost your listing');
    if (bm.querySelector('.bm-rate-note')) bm.querySelector('.bm-rate-note').textContent = A ? (days ? days + (days >= 3 && days <= 10 ? ' أيام' : ' يومًا') + ' · ' : '') + 'السعر بالجنيه المصري وشامل ضريبة القيمة المضافة' : (days ? days + ' days · ' : '') + 'Price in Egyptian pounds, VAT included';
    (A ? [feat ? 'رسوم الإعلان المميز' : 'رسوم الترقية', 'ضريبة القيمة المضافة (14%)', 'الإجمالي'] : [feat ? 'Featured fee' : 'Boost fee', 'VAT (14%)', 'Total']).forEach(function (t, i) { if (lb[i]) lb[i].textContent = t; });
    var n = Math.round(total).toLocaleString('en', { maximumFractionDigits: 0 }); $('bmEgpAmount').innerHTML = ar() ? esc(n) + ' <span>ج.م</span>' : '<span>EGP</span> ' + esc(n); $('bmBaseEgp').textContent = egp(base); $('bmVatEgp').textContent = egp(vat); $('bmTotalEgp').textContent = egp(total);
    $('bmPayBtn').textContent = ar() ? '🔒 ادفع ' + egp(total) + ' الآن' : '🔒 Pay ' + egp(total) + ' now';
  }
  function quoted(plan) {
    return Promise.resolve().then(function () { return window.dxPay.quote(plan === 'featured' ? 'featured' : 'boost'); }).then(function (q) {
      if (!q || q.total_egp == null) throw new Error('The price could not be loaded — please try again');
      var ov = document.getElementById('boostModalOverlay'); ov.querySelectorAll('.dx-pay, .dx-pay-l, .dx-inc').forEach(function (x) { x.remove(); });
      paintQuote(q, plan); ov.classList.add('show'); boostMethods(plan);
    }).catch(function (e) { D.toast((e && e.message) || 'The price could not be loaded — please try again'); });
  }
  var ctx = { slug: null, plan: 'boost' };
  if (window.dxDir && window.dxDir.upgrade) { var oUp = window.dxDir.upgrade; window.dxDir.upgrade = function (s) { ctx.slug = s; return oUp.apply(this, arguments); }; }
  function wrapBoost() {                       /* the marketplace page defines openBoostModal when it renders, so wrap it after each render */
    if (typeof window.openBoostModal !== 'function' || window.openBoostModal.__pay) return;
    var oBoost = window.openBoostModal; window.openBoostModal = function (plan) { ctx.plan = plan; if (hasQuote()) return quoted(plan); var r = oBoost.apply(this, arguments); setTimeout(function () { boostMethods(plan); }, 0); return r; }; window.openBoostModal.__pay = true;
  }
  wrapBoost(); if (window.dxCore && window.dxCore.onRender) window.dxCore.onRender('checkout', wrapBoost);
  function acting() { var a = window.dxDir && window.dxDir.mine && window.dxDir.mine(); return a ? a.slug : null; }
  function boostMethods(plan) {
    var ov = document.getElementById('boostModalOverlay'), btn = document.getElementById('bmPayBtn'); if (!btn || ov.querySelector('.dx-pay')) return;
    btn.insertAdjacentHTML('beforebegin', (window.dxPay.live ? '<label class="dx-pay-l">Listing to promote<select id="dxPayListing"><option value="">Loading your listings…</option></select></label>' : '') + methods('dxPayBoost'));
    if (window.dxPay.live) window.dxPay.listings().then(function (l) { var s = document.getElementById('dxPayListing'); if (s) s.innerHTML = l.length ? l.map(function (x) { return '<option value="' + x.id + '">' + esc(x.name) + '</option>'; }).join('') : '<option value="">Post a listing first</option>'; });
    /* VIP: 3 included boosts a month — offered before paying (B-16) */
    var slug = acting(); if (plan === 'featured' || !slug || !window.dxPay.included) return;
    window.dxPay.included(slug).then(function (n) {
      if (!n || ov.querySelector('.dx-inc') || !ov.classList.contains('show')) return;
      var pay = ov.querySelector('.dx-pay'); if (!pay) return;
      pay.insertAdjacentHTML('beforebegin', '<div class="dx-inc"><button type="button" class="dx-inc-b" data-inc="1">👑 Use an included boost</button><small>' + n + ' of 3 included boosts left this month with VIP — no payment</small></div>');
    }).catch(function () {});
  }
  /* the VIP payment window (upgrade) and the last step of the create-company wizard get the payment methods */
  new MutationObserver(function () {
    document.querySelectorAll('.dbk-ov:not([data-pay])').forEach(function (ov) { var head = (ov.innerText || '').slice(0, 120);
      var vip = /Pay for VIP/.test(head), wiz = /review and pay/.test(head); if (!vip && !wiz) return; ov.dataset.pay = vip ? 'vip' : 'wizard';
      var tbl = ov.querySelector('table.cp-spec'), old = ov.querySelector('.pay-row'); if (old) old.remove();
      if (tbl) tbl.insertAdjacentHTML('afterend', methods('dxPayVip'));
      var n = ov.querySelectorAll('p.cp-muted'); [].forEach.call(n, function (p) { if (/Demo/.test(p.textContent)) { if (window.dxPay.live) p.remove(); else p.textContent = 'Demo — no money is charged; the steps are the real ones.'; } });
      if (wiz && !window.dxPay.live && tbl) { var pm = ov.querySelector('.dx-pay'); if (pm) pm.insertAdjacentHTML('afterend', '<p class="cp-muted dx-demo-note">Demo — no money is charged; the steps are the real ones.</p>'); } });   /* the demo says it is a demo, never the live app */
  }).observe(document.body, { childList: true });

  /* what the payment provider asks next: the Paymob page, a Fawry reference, the InstaPay transfer */
  function result(r) {
    if (r.checkout_url) { D.toast('Opening the secure Paymob page…'); window.location.assign(r.checkout_url); return; }
    if (r.fawry_reference) { D.modal({ title: 'Pay at Fawry', secondary: 'Done', body: '<div class="dx-pay-ref"><small>Fawry reference number</small><b>' + esc(r.fawry_reference) + '</b><span>' + esc(egp(r.amount)) + ' · valid until ' + esc(fmt(r.expires_at, true)) + '</span></div><ol class="dx-pay-steps"><li>Go to any Fawry outlet, or open myFawry → Pay with reference.</li><li>Give the reference number and pay the amount.</li><li>It activates automatically once Fawry confirms — we notify you. You find this reference again in My payments.</li></ol>' +
      (r.demo ? '<p class="dx-pay-note dx-demo-note">Demo — a sample reference number; Fawry is not contacted and nothing is charged.</p>' : '') }); refreshPay(); return; }
    if (r.instapay) { instapayDialog(r); return; }
    if (r.paid) { refreshPay(); }
  }
  function instapayDialog(r) {
    D.modal({ title: 'Pay with InstaPay', body: '<div class="dx-pay-ref"><small>Send to</small><b>' + esc(r.instapay.address) + '</b><span>' + esc(r.instapay.name) + ' · ' + esc(egp(r.amount)) + '</span></div><p class="dx-pay-note">Write <b>' + esc(r.reference) + '</b> in the transfer note.</p>' + (r.demo ? '<p class="dx-pay-note dx-demo-note">Demo — a sample InstaPay address; send no money, nothing is charged.</p>' : '') +
      '<div class="dbk-f"><label for="dxIpRef">Transfer number *</label><input id="dxIpRef" data-req placeholder="From the InstaPay confirmation"></div><div class="dbk-f"><label for="dxIpRc">Receipt (screenshot or PDF)</label><input id="dxIpRc" type="file" accept=".png,.jpg,.jpeg,.pdf"></div>',
      primary: { label: 'Send for confirmation', onClick: function (b, close) { if (!D.requireFields(b)) return false; var f = b.querySelector('#dxIpRc').files[0], ok = b.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        window.dxPay.submitInstapay(r.order_id, b.querySelector('#dxIpRef').value.trim(), f || null).then(function () { close(); D.toast('Thank you — we confirm InstaPay transfers within one working day'); refreshPay(); }, function (e) { if (ok) ok.disabled = false; D.toast(e.message || 'Could not send'); });
        return false; } } });
  }
  function start(o, btn, done) { btn.disabled = true; window.dxPay.start(o).then(function (r) { btn.disabled = false; if (done) done(r); result(r); }, function (e) { btn.disabled = false; D.toast((e && e.message) || 'The payment could not start'); }); }
  function billingOf(ov) { var tbl = ov.querySelector('table.cp-spec'); return tbl && tbl.dataset.billing === 'year' || /yearly/.test(ov.innerText) ? 'vip_year' : 'vip_month'; }
  document.addEventListener('click', function (e) {
    var inc = e.target.closest && e.target.closest('#boostModalOverlay [data-inc]');
    if (inc) { e.preventDefault(); e.stopImmediatePropagation(); var slug = acting(), lid = (document.getElementById('dxPayListing') || {}).value;
      if (window.dxPay.live && !lid) { D.toast('Choose the listing to promote'); return; }
      inc.disabled = true;
      window.dxPay.useIncluded(window.dxPay.live ? +lid : null, slug).then(function (r) { document.getElementById('boostModalOverlay').classList.remove('show');
        D.toast('Boost activated — included with VIP (' + r.left + ' left this month)'); refreshPay(); if (window.dxPay.live && window.dxLive && window.dxLive.loadMarket) window.dxLive.loadMarket().catch(function () {}); },
        function (er) { inc.disabled = false; D.toast((er && er.message) || 'Could not use an included boost'); }); return; }
    var vip = e.target.closest && e.target.closest('.dbk-ov[data-pay="vip"] [data-a=ok]'), ov = vip && vip.closest('.dbk-ov');   /* the window's pay button, whatever language its label is in */
    if (vip) { var m = chosen(ov, 'dxPayVip'), tbl = ov.querySelector('table.cp-spec'), slug2 = (tbl && tbl.dataset.slug) || ctx.slug;
      if (!window.dxPay.live && (m === 'card' || m === 'wallet')) { window.dxPay.start({ product: billingOf(ov), method: m, slug: slug2 }); return; }   /* the demo's own window activates VIP (no money moves) */
      e.preventDefault(); e.stopImmediatePropagation();
      start({ product: billingOf(ov), method: m, slug: slug2 }, vip, function () { ov.remove(); }); return; }
    var wiz = e.target.closest && e.target.closest('.dbk-ov[data-pay="wizard"] [data-a=ok]');
    if (wiz) { var ow = wiz.closest('.dbk-ov'); window.__dxVipPending = { product: billingOf(ow), method: chosen(ow, 'dxPayVip'), at: Date.now() }; return; }   /* the wizard creates the page first (directory.js), then the payment starts */
    var bp = e.target.closest && e.target.closest('#bmPayBtn');
    if (bp) { var meth = chosen(document, 'dxPayBoost'), prod = ctx.plan === 'featured' ? 'featured' : 'boost';
      if (!window.dxPay.live) { if (meth === 'card' || meth === 'wallet') { window.dxPay.start({ product: prod, method: meth, slug: acting() }); return; }   /* the approved demo window shows "Boost activated" */
        e.preventDefault(); e.stopImmediatePropagation(); start({ product: prod, method: meth, slug: acting() }, bp, function () { document.getElementById('boostModalOverlay').classList.remove('show'); }); return; }
      e.preventDefault(); e.stopImmediatePropagation(); var lid2 = (document.getElementById('dxPayListing') || {}).value; if (!lid2) { D.toast('Choose the listing to promote'); return; }
      start({ product: prod, method: meth, listing_id: +lid2 }, bp, function () { document.getElementById('boostModalOverlay').classList.remove('show'); }); }
  }, true);
  /* the wizard has created the page: its VIP payment starts now (the page stays Basic until the payment is confirmed) */
  window.dxCheckout = { result: result, startVip: function (slug, pend) { var p = pend || window.__dxVipPending; window.__dxVipPending = null; if (!p || !slug) return;
    window.dxPay.start({ product: p.product, method: p.method, slug: slug }).then(function (r) { if (!window.dxPay.live && r.paid) activateDemoVip(slug, p.product); result(r); }, function (e) { D.toast((e && e.message) || 'The payment could not start'); }); } };
  function activateDemoVip(slug, product) { var X = window.dxDir; if (!X) return; var created = X.store('created_companies') || [];
    created.forEach(function (c) { if (c.slug === slug) { c.plan = 'vip'; c.billing = product === 'vip_year' ? 'year' : 'month'; } }); X.store('created_companies', created); X.render(); D.toast('Payment received — VIP is active (demo: no card was charged)'); }

  /* ── My payments (Market → My Listings) and the company's payment history (Workspace → Plan & verification) ── */
  var STATUS = { pending: 'Waiting for payment', review: 'Under review', paid: 'Paid', failed: 'Did not go through', expired: 'Expired', refunded: 'Refunded', cancelled: 'Cancelled' };
  var PAY = { me: null, co: {}, at: 0, coAt: {} };
  function payRow(x, co) {
    var sub = [x.listing || x.company || '', MNAME[x.method] || x.method, fmt(x.created_at)].filter(Boolean).join(' · '), extra = '', acts = '';
    if (x.method === 'fawry' && x.fawry_reference && x.status === 'pending') extra = '<small class="dx-pr-ref">Fawry reference ' + esc(x.fawry_reference) + (x.fawry_expires_at ? ' · pay by ' + esc(fmt(x.fawry_expires_at, true)) : '') + '</small>';
    if (x.method === 'instapay' && x.status === 'review' && x.transfer) extra = '<small class="dx-pr-ref">Transfer ' + esc(x.transfer) + ' — Drugbox confirms within one working day</small>';
    if (x.status === 'paid' && x.invoice_no) acts = '<button type="button" class="dr-btn sm" data-inv="' + esc(x.id) + '">Invoice</button>';
    else if (x.method === 'instapay' && x.status === 'pending' && x.mine !== false) acts = '<button type="button" class="dr-btn sm" data-ipsend="' + esc(x.id) + '" data-ipref="' + esc(x.order) + '" data-ipamt="' + esc(x.total) + '">Send the transfer</button>';
    else if (x.status === 'pending' && x.mine !== false && (x.method === 'card' || x.method === 'wallet'))   /* left on the Paymob page: continue (a new checkout) or cancel */
      acts = '<button type="button" class="dr-btn sm" data-paycont="' + esc(x.id) + '">Continue payment</button><button type="button" class="dr-btn sm ghost" data-paycancel="' + esc(x.id) + '">Cancel</button>';
    else if (x.status === 'pending' && x.mine !== false && x.method === 'fawry') acts = '<button type="button" class="dr-btn sm ghost" data-paycancel="' + esc(x.id) + '" data-fawry="1">Cancel</button>';
    else if ((x.status === 'failed' || x.status === 'expired') && x.kind !== 'vip') acts = '<button type="button" class="dr-btn sm" data-payagain="' + esc(x.kind) + '">Pay again</button>';
    else if ((x.status === 'failed' || x.status === 'expired') && x.kind === 'vip' && co) acts = '<button type="button" class="dr-btn sm" data-wvip="1">Pay again</button>';
    return '<div class="mr-row dx-pr" data-pay="' + esc(x.id) + '"><div class="mr-b"><b>' + esc(x.product) + ' · ' + esc(egp(x.total)) + ' <span class="mr-st st-' + (x.status === 'paid' ? 'acc' : x.status === 'failed' || x.status === 'expired' || x.status === 'cancelled' ? 'dec' : 'viewed') + '">' + esc(STATUS[x.status] || x.status) + '</span></b><small>' + esc(sub) + (x.vat ? ' · incl. VAT ' + esc(egp(x.vat)) : '') + '</small>' + extra + '</div>' + (acts ? '<span class="mr-acts">' + acts + '</span>' : '') + '</div>';
  }
  function loadMine(force) { if (!window.dxPay.orders || (!force && Date.now() - PAY.at < 15000)) return; PAY.at = Date.now();
    window.dxPay.orders(null).then(function (l) { PAY.me = l || []; paintMyPayments(); }).catch(function () {}); }
  function refreshPay() { PAY.at = 0; PAY.coAt = {}; loadMine(true); var w = document.querySelector('#dxDir.hub.ws'); if (w && window.dxDir) setTimeout(function () { window.dxDir.render(); }, 0); }
  window.dxPayRefresh = refreshPay;
  function paintMyPayments() {
    var m = document.getElementById('tab-manage'), wrap = m && m.querySelector('.page-wrap'); if (!wrap) return;
    var box = wrap.querySelector('#dxMyPay'), l = PAY.me;
    if (!l) { loadMine(); return; }
    var html = '<div class="dx-mypay-h"><div style="font-size:15px;font-weight:800;color:#0f172a">My payments</div><div style="font-size:11.5px;color:#64748b;margin-top:2px">Boosts and Featured listings you paid for — references, receipts and invoices</div></div>' +
      '<div class="dx-mypay-l">' + (l.length ? l.map(function (x) { return payRow(x); }).join('') : '<div class="cp-muted" style="padding:12px 0">No payments yet.</div>') + '</div>';
    if (!box) { box = document.createElement('div'); box.id = 'dxMyPay'; box.className = 'dx-mypay'; wrap.appendChild(box); }
    if (box.dataset.sig !== html) { box.innerHTML = html; box.dataset.sig = html; }
  }
  if (window.dxCore && window.dxCore.onRender) window.dxCore.onRender('my-payments', function () { if (document.body.getAttribute('data-page') === 'market') { paintMyPayments(); loadMine(); } });
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#mkx .master-tab[data-tab=manage]')) setTimeout(function () { paintMyPayments(); loadMine(); }, 0); }, true);
  /* the company's payment history, drawn by the workspace's Plan tab (hub-ui) from what is loaded; read again when it opens */
  window.dxBilling = {
    html: function (co) {
      var l = PAY.co[co.slug]; if (!PAY.coAt[co.slug] || Date.now() - PAY.coAt[co.slug] > 15000) { PAY.coAt[co.slug] = Date.now();
        if (window.dxPay.orders) window.dxPay.orders(co.slug).then(function (r) { PAY.co[co.slug] = r || []; var w = document.querySelector('#dxDir.hub.ws'); if (w && window.dxDir && window.dxDir.S.ws === co.slug) window.dxDir.render(); }).catch(function () {}); }
      return '<section class="cp-sec dx-billing"><h3>Payment history</h3><p class="cp-muted">Every payment for ' + esc(co.name) + '’s plan, with its status. Paid ones have a tax invoice (VAT 14% included).</p>' +
        (l == null ? '<p class="cp-muted">Loading…</p>' : l.length ? l.map(function (x) { return payRow(x, co); }).join('') : '<p class="cp-muted">No payments yet.</p>') + '</section>';
    }
  };
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-inv],[data-ipsend],[data-payagain],[data-paycont],[data-paycancel]'); if (!t) return;
    e.preventDefault(); e.stopPropagation();
    if (t.dataset.inv) { t.disabled = true; window.dxPay.invoice(isNaN(+t.dataset.inv) ? t.dataset.inv : +t.dataset.inv).then(function (v) { t.disabled = false; invoiceWindow(v); }, function (er) { t.disabled = false; D.toast((er && er.message) || 'The invoice could not be opened'); }); return; }
    if (t.dataset.ipsend) { instapayDialog({ order_id: isNaN(+t.dataset.ipsend) ? t.dataset.ipsend : +t.dataset.ipsend, reference: t.dataset.ipref, amount: +t.dataset.ipamt, instapay: window.dxPay.instapayTo ? window.dxPay.instapayTo() : { address: 'drugbox@instapay', name: 'Drugbox Egypt' } }); return; }
    var key = function (v) { return isNaN(+v) ? v : +v; }, find = function (id) { var all = (PAY.me || []).slice(); Object.keys(PAY.co).forEach(function (k) { all = all.concat(PAY.co[k] || []); }); return all.filter(function (x) { return String(x.id) === String(id); })[0]; };
    if (t.dataset.paycont) { var x = find(t.dataset.paycont); if (!x) return;   /* the same thing again, by the same method: the server supersedes the abandoned checkout */
      start({ product: x.code, method: x.method, listing_id: x.listing_id || null, slug: x.slug || null, listingName: x.listing }, t); return; }
    if (t.dataset.paycancel) { var fw = !!t.dataset.fawry;
      D.modal({ title: 'Cancel this payment?', body: '<p>' + (fw ? 'Its Fawry reference can no longer be used. Nothing was charged.' : 'Nothing was charged. If you already paid on the payment page, do not cancel — the payment confirms itself.') + '</p>',
        secondary: 'Keep it', primary: { label: 'Cancel payment', danger: true, onClick: function () { window.dxPay.cancel(key(t.dataset.paycancel)).then(function () { D.toast('Payment cancelled — nothing was charged'); refreshPay(); }, function (er) { D.toast((er && er.message) || 'Could not cancel'); refreshPay(); }); } } });
      return; }
    if (t.dataset.payagain) { if (typeof window.openBoostModal === 'function') window.openBoostModal(t.dataset.payagain === 'featured' ? 'featured' : 'boost'); }
  }, true);
  /* the tax invoice: the server's numbers (order_invoice), printed or saved as PDF from the browser */
  function invoiceWindow(v) {
    var w = window.open('', '_blank'); if (!w) { D.toast('Allow pop-ups to open the invoice'); return; }
    var A = ar(), L = function (en, a) { return A ? a : en; }, s = v.seller || {}, M = A ? { card: 'بطاقة بنكية', wallet: 'محفظة الموبايل', fawry: 'فوري', instapay: 'إنستاباي' } : MNAME;
    var money = function (n) { var t = Number(n).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); return A ? t + ' ج.م' : 'EGP ' + t; };
    var row = function (a, b) { return '<tr><td>' + esc(a) + '</td><td class="n">' + esc(b) + '</td></tr>'; }, prod = A && window.dxT ? window.dxT(v.product || '') : v.product;
    var days = v.days ? (A ? ' (' + v.days + (v.days >= 3 && v.days <= 10 ? ' أيام' : ' يومًا') + ')' : ' (' + v.days + ' days)') : '';
    w.document.write('<!doctype html><html lang="' + (A ? 'ar' : 'en') + '" dir="' + (A ? 'rtl' : 'ltr') + '"><head><meta charset="utf-8"><title>' + L('Invoice ', 'فاتورة ') + esc(v.invoice_no) + '</title><style>body{font:14px/1.5 Arial,sans-serif;color:#0f172a;max-width:720px;margin:32px auto;padding:0 20px}h1{font-size:22px;margin:0}table{width:100%;border-collapse:collapse;margin:18px 0}td{padding:8px;border-bottom:1px solid #e2e8f0}td.n{text-align:' + (A ? 'left' : 'right') + ';direction:ltr;unicode-bidi:embed}.t td{font-weight:700;border-top:2px solid #0f172a}small{color:#64748b}.ltr{direction:ltr;unicode-bidi:embed}.rf{color:#b91c1c;font-weight:700}@media print{button{display:none}}</style></head><body>' +
      '<h1>' + L('Tax invoice', 'فاتورة ضريبية') + '</h1>' + (v.refunded ? '<p class="rf">' + L('Refunded — this payment was returned to the buyer.', 'مُستردة — أُعيد هذا المبلغ إلى المشتري.') + '</p>' : '') +
      '<p><b class="ltr">' + esc(v.invoice_no) + '</b> · ' + esc(A && window.dxFmtDate ? window.dxFmtDate(v.issued_at, true, 'ar') : fmt(v.issued_at, true)) + '<br><small>' + L('Order ', 'الطلب ') + '<span class="ltr">' + esc(v.order) + '</span>' + L(' · paid by ', ' · الدفع عن طريق ') + esc(M[v.method] || v.method) + '</small></p>' +
      '<p><b>' + L('Seller:', 'البائع:') + '</b> ' + esc(s.name || 'Drugbox') + (s.address ? '<br>' + esc(s.address) : '') + '<br>' + L('Tax registration no.: ', 'رقم التسجيل الضريبي: ') + (s.tax_reg_no ? '<span class="ltr">' + esc(s.tax_reg_no) + '</span>' : esc(L('pending — added by Drugbox', 'قيد الإضافة — يضيفه Drugbox'))) + '</p>' +
      '<p><b>' + L('Buyer:', 'المشتري:') + '</b> ' + esc((v.company && v.company.name) || (v.buyer && v.buyer.name) || '') + (v.company && v.company.registry ? '<br>' + L('Commercial registry ', 'السجل التجاري ') + '<span class="ltr">' + esc(v.company.registry) + '</span>' : '') + (v.company && v.buyer ? '<br>' + L('Ordered by ', 'طلبه ') + esc(v.buyer.name) : '') + '</p>' +
      '<table>' + row(prod + (v.listing ? ' — ' + v.listing : '') + days, money(v.net)) + row(L('VAT ', 'ضريبة القيمة المضافة ') + Math.round(Number(v.vat_rate || 0.14) * 100) + '%', money(v.vat)) +
      '<tr class="t"><td>' + L('Total', 'الإجمالي') + '</td><td class="n">' + money(v.total) + '</td></tr></table>' + (v.demo ? '<p><small>' + L('Demo invoice — sample data, no money was charged.', 'فاتورة تجريبية — بيانات توضيحية، ولم يُخصم أي مبلغ.') + '</small></p>' : '') +
      '<button onclick="print()">' + L('Print or save as PDF', 'اطبع أو احفظ PDF') + '</button></body></html>');
    w.document.close();
  }
})();
