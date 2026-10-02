/* Checkout: payment methods in the VIP payment window and the boost window — card, Vodafone Cash & wallets, Fawry, InstaPay.
   In the demo the choice is shown and the demo flow continues; in the live app window.dxPay (adapter) starts the real payment. */
(function () {
  var D = window.DBK; if (!D) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var M = [['card', '💳', 'Card', 'Visa · Mastercard · Meeza'], ['wallet', '📱', 'Vodafone Cash & wallets', 'Vodafone Cash · Orange Cash · e& money · WE Pay'],
           ['fawry', '🏪', 'Fawry', 'Pay at any Fawry outlet or in the myFawry app'], ['instapay', '⚡', 'InstaPay', 'Transfer, then send us the receipt']];
  function methods(name) { return '<div class="dx-pay"><div class="dx-pay-t">Pay with</div>' + M.map(function (m, i) { return '<label class="dx-pay-m"><input type="radio" name="' + name + '" value="' + m[0] + '"' + (i ? '' : ' checked') + '><span class="dx-pay-i">' + m[1] + '</span><span><b>' + m[2] + '</b><small>' + m[3] + '</small></span></label>'; }).join('') + '</div>'; }
  function chosen(root, name) { var r = root.querySelector('input[name=' + name + ']:checked'); return r ? r.value : 'card'; }
  if (!window.dxPay) window.dxPay = { live: false };
  var ctx = { slug: null, plan: 'boost' };
  if (window.dxDir && window.dxDir.upgrade) { var oUp = window.dxDir.upgrade; window.dxDir.upgrade = function (s) { ctx.slug = s; return oUp.apply(this, arguments); }; }
  function wrapBoost() {                       /* the marketplace page defines openBoostModal when it renders, so wrap it after each render */
    if (typeof window.openBoostModal !== 'function' || window.openBoostModal.__pay) return;
    var oBoost = window.openBoostModal; window.openBoostModal = function (plan) { ctx.plan = plan; var r = oBoost.apply(this, arguments); setTimeout(boostMethods, 0); return r; }; window.openBoostModal.__pay = true;
  }
  wrapBoost(); if (window.dxCore && window.dxCore.onRender) window.dxCore.onRender('checkout', wrapBoost);
  function boostMethods() {
    var btn = document.getElementById('bmPayBtn'); if (!btn || document.getElementById('boostModalOverlay').querySelector('.dx-pay')) return;
    btn.insertAdjacentHTML('beforebegin', (window.dxPay.live ? '<label class="dx-pay-l">Listing to promote<select id="dxPayListing"><option value="">Loading your listings…</option></select></label>' : '') + methods('dxPayBoost'));
    if (window.dxPay.live) window.dxPay.listings().then(function (l) { var s = document.getElementById('dxPayListing'); if (s) s.innerHTML = l.length ? l.map(function (x) { return '<option value="' + x.id + '">' + esc(x.name) + '</option>'; }).join('') : '<option value="">Post a listing first</option>'; });
  }
  new MutationObserver(function () {                                   /* the VIP payment window is a kit modal appended to <body> */
    document.querySelectorAll('.dbk-ov:not([data-pay])').forEach(function (ov) { if (!/Pay for VIP/.test((ov.innerText || '').slice(0, 80))) return; ov.dataset.pay = '1';
      var tbl = ov.querySelector('table.cp-spec'); if (tbl) tbl.insertAdjacentHTML('afterend', methods('dxPayVip'));
      if (window.dxPay.live) { var n = ov.querySelector('p.cp-muted'); if (n && /Demo/.test(n.textContent)) n.remove(); } });
  }).observe(document.body, { childList: true });
  function result(r, method) {
    if (r.checkout_url) { D.toast('Opening the secure Paymob page…'); window.location.assign(r.checkout_url); return; }
    if (r.fawry_reference) { D.modal({ title: 'Pay at Fawry', secondary: 'Done', body: '<div class="dx-pay-ref"><small>Fawry reference number</small><b>' + esc(r.fawry_reference) + '</b><span>EGP ' + Number(r.amount).toLocaleString('en') + ' · valid until ' + esc(new Date(r.expires_at).toLocaleString()) + '</span></div><ol class="dx-pay-steps"><li>Go to any Fawry outlet, or open myFawry → Pay with reference.</li><li>Give the reference number and pay the amount.</li><li>It activates automatically once Fawry confirms — we notify you.</li></ol>' }); return; }
    if (r.instapay) { D.modal({ title: 'Pay with InstaPay', body: '<div class="dx-pay-ref"><small>Send to</small><b>' + esc(r.instapay.address) + '</b><span>' + esc(r.instapay.name) + ' · EGP ' + Number(r.amount).toLocaleString('en') + '</span></div><p class="dx-pay-note">Write <b>' + esc(r.reference) + '</b> in the transfer note.</p>' +
        '<div class="dbk-f"><label for="dxIpRef">Transfer number *</label><input id="dxIpRef" data-req placeholder="From the InstaPay confirmation"></div><div class="dbk-f"><label for="dxIpRc">Receipt (screenshot or PDF)</label><input id="dxIpRc" type="file" accept=".png,.jpg,.jpeg,.pdf"></div>',
        primary: { label: 'Send for confirmation', onClick: function (b) { if (!D.requireFields(b)) return false; var f = b.querySelector('#dxIpRc').files[0];
          window.dxPay.submitInstapay(r.order_id, b.querySelector('#dxIpRef').value.trim(), f || null).then(function () { D.toast('Thank you — we confirm InstaPay transfers within one working day'); }, function (e) { D.toast(e.message || 'Could not send'); }); } } }); }
  }
  function start(o, btn) { btn.disabled = true; window.dxPay.start(o).then(function (r) { btn.disabled = false; result(r, o.method); }, function (e) { btn.disabled = false; D.toast((e && e.message) || 'The payment could not start'); }); }
  document.addEventListener('click', function (e) {
    if (!window.dxPay.live) return;
    var vip = e.target.closest && e.target.closest('.dbk-ov[data-pay] button'), ov = vip && vip.closest('.dbk-ov');
    if (vip && /^Pay EGP/.test(vip.textContent.trim())) { e.preventDefault(); e.stopImmediatePropagation();
      ov.remove(); start({ product: /yearly/.test(ov.innerText) ? 'vip_year' : 'vip_month', method: chosen(ov, 'dxPayVip'), slug: ctx.slug }, vip); return; }
    var bp = e.target.closest && e.target.closest('#bmPayBtn');
    if (bp) { e.preventDefault(); e.stopImmediatePropagation(); var lid = (document.getElementById('dxPayListing') || {}).value; if (!lid) { D.toast('Choose the listing to promote'); return; }
      document.getElementById('boostModalOverlay').classList.remove('show'); start({ product: ctx.plan === 'featured' ? 'featured' : 'boost', method: chosen(document, 'dxPayBoost'), listing_id: +lid }, bp); }
  }, true);
})();
