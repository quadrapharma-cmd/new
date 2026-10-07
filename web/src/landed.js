/* Landed cost calculator: CIF or FOB price → final cost in EGP. Pure arithmetic, runs only when opened. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function idle(fn) { var p = false; return function () { if (p) return; p = true; (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1); })(function () { p = false; try { fn(); } catch (e) {} }, { timeout: 400 }); }; }   /* decoration waits until the page is on screen */
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function num(v) { v = parseFloat(String(v).replace(/[^\d.]/g, '')); return isFinite(v) ? v : 0; }
  function egp(v) { return 'EGP ' + Math.round(v).toLocaleString('en'); }
  function open(pre) {
    pre = pre || {};
    var m = D.modal({ title: 'Landed cost calculator', secondary: 'Close', body:
      '<div class="dx-lc"><div class="dx-lc-f">' +
      '<label>Price per unit (US$)<input id="lcP" type="number" min="0" step="0.01" value="' + esc(pre.price || '') + '" placeholder="5.40"></label>' +
      '<label>Quantity<input id="lcQ" type="number" min="0" step="1" value="' + esc(pre.qty || 1000) + '"></label>' +
      '<label>Unit<input id="lcU" type="text" value="' + esc(pre.unit || 'kg') + '"></label>' +
      '<label>Incoterm<select id="lcI"><option value="CIF"' + (pre.inc === 'FOB' ? '' : ' selected') + '>CIF — freight & insurance included</option><option value="FOB"' + (pre.inc === 'FOB' ? ' selected' : '') + '>FOB — add freight & insurance</option></select></label>' +
      '<label class="dx-lc-fob">Freight (US$)<input id="lcF" type="number" min="0" value="0"></label>' +
      '<label class="dx-lc-fob">Insurance (% of FOB)<input id="lcIns" type="number" min="0" step="0.1" value="0.5"></label>' +
      '<label>Exchange rate (EGP per US$)<input id="lcR" type="number" min="0" step="0.01" value="' + esc(pre.rate || 50) + '"></label>' +
      '<label>Customs duty (%)<input id="lcD" type="number" min="0" step="0.5" value="2"></label>' +
      '<label>VAT (%)<input id="lcV" type="number" min="0" step="0.5" value="14"></label>' +
      '<label>Bank / LC fees (%)<input id="lcB" type="number" min="0" step="0.1" value="1"></label>' +
      '<label>Clearance & port (EGP)<input id="lcCl" type="number" min="0" value="15000"></label>' +
      '<label>Inland transport (EGP)<input id="lcT" type="number" min="0" value="5000"></label>' +
      '</div><div class="dx-lc-out" id="lcOut"></div>' +
      '<p class="dx-lc-note">An estimate to compare offers. Duty depends on the HS code and exemptions — confirm with your customs broker. Enter today’s exchange rate.</p></div>' });
    var el = m.el || document.querySelector('.dbk-ov'); if (!el) return;
    function v(id) { var x = el.querySelector('#' + id); return x ? x.value : ''; }
    function calc() {
      var fob = v('lcI') === 'FOB'; el.querySelectorAll('.dx-lc-fob').forEach(function (l) { l.style.display = fob ? '' : 'none'; });
      var p = num(v('lcP')), q = num(v('lcQ')), r = num(v('lcR')), goods = p * q;
      var cifUsd = fob ? goods + num(v('lcF')) + goods * num(v('lcIns')) / 100 : goods;
      var cv = cifUsd * r, duty = cv * num(v('lcD')) / 100, vat = (cv + duty) * num(v('lcV')) / 100, bank = cv * num(v('lcB')) / 100, cl = num(v('lcCl')), tr = num(v('lcT'));
      var total = cv + duty + vat + bank + cl + tr, per = q ? total / q : 0;
      var parts = [['Customs value (CIF)', cv, '#1A56DB'], ['Customs duty', duty, '#7C3AED'], ['VAT', vat, '#EC4899'], ['Bank / LC fees', bank, '#06B6D4'], ['Clearance & port', cl, '#F59E0B'], ['Inland transport', tr, '#10B981']];
      el.querySelector('#lcOut').innerHTML = '<div class="dx-lc-tot"><span>Landed cost</span><b>' + egp(total) + '</b><em>' + egp(per) + ' per ' + esc(v('lcU') || 'unit') + '</em></div>' +
        '<div class="dx-lc-bar">' + parts.map(function (x) { return '<i style="width:' + (total ? x[1] / total * 100 : 0) + '%;background:' + x[2] + '"></i>'; }).join('') + '</div>' +
        parts.map(function (x) { return '<div class="dx-lc-row"><span><i style="background:' + x[2] + '"></i>' + x[0] + '</span><b>' + egp(x[1]) + '</b></div>'; }).join('');
    }
    el.addEventListener('input', calc); el.addEventListener('change', calc); calc();
  }
  /* entry points: a small "Landed cost" link beside US$ prices in the marketplace and on deal offers */
  function parsePrice(t) { var m = /US\$\s*([\d.,]+)\s*(?:\/\s*([a-zA-Z]+))?/.exec(t || ''); return m ? { price: num(m[1]), unit: m[2] || 'kg' } : null; }
  function mark() {
    var pg = document.body.getAttribute('data-page'); if (pg !== 'market') return;
    document.querySelectorAll('#mkx .sp-price, #mkx .lc-price').forEach(function (el) {   /* full listing cards only — never inside a card that is itself a button */
      if (el.dataset.dxlc) return; if (el.closest('.sp-mini,[onclick]')) { el.dataset.dxlc = '1'; return; }
      var pp = parsePrice(el.textContent); if (!pp) return; el.dataset.dxlc = '1';   /* "$5.80" becomes "US$ 5.80" when craft.js formats it: until then, look again on the next render */
      var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-lc-chip'; b.textContent = 'Landed cost'; b.dataset.p = pp.price; b.dataset.u = pp.unit; el.appendChild(b);
    });
  }
  function markDeal() {
    document.querySelectorAll('.dbk-ov .dl-offer').forEach(function (el) {
      if (el.dataset.dxlc) return; el.dataset.dxlc = '1'; var pp = parsePrice(el.textContent); if (!pp) return;
      var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-lc-chip'; b.textContent = 'Landed cost'; b.dataset.p = pp.price; b.dataset.u = pp.unit; el.appendChild(b);
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.dx-lc-chip'); if (!b) return; e.preventDefault(); e.stopPropagation();
    var inc = /FOB/.test((b.parentElement || {}).textContent || '') ? 'FOB' : 'CIF'; open({ price: b.dataset.p, unit: b.dataset.u, inc: inc });
  }, true);
  var obs = new MutationObserver(function () { if (document.querySelector('.dbk-ov .dl-offer:not([data-dxlc])')) markDeal(); });
  obs.observe(document.body, { childList: true });
  C.onRender('landed-cost', idle(mark));
  window.dxLanded = open;
})();
