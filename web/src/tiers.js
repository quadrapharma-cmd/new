/* Verification tiers (1 Registered · 2 Licensed · 3 Inspected) and a compliance passport per company.
   Read-only over existing company/site data; the only new data is documents a company declares (CEP, DMF…). Runs after the page is on screen. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D || !window.dxDir || !window.dxHubData) return;
  function idle(fn) { var p = false; return function () { if (p) return; p = true; (window.requestIdleCallback || function (cb) { return setTimeout(cb, 1); })(function () { p = false; try { fn(); } catch (e) {} }, { timeout: 400 }); }; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function load() { try { var v = JSON.parse(localStorage.getItem('dx_passport') || '{}'); return v && typeof v === 'object' && !Array.isArray(v) ? v : {}; } catch (e) { return {}; } }
  function save(v) { try { localStorage.setItem('dx_passport', JSON.stringify(v)); } catch (e) {} }
  var SEED = { 'cairo-api-trading': [{ type: 'CEP', product: 'Metformin HCl', number: 'R1-CEP 2019-341-Rev 02', expiry: '', status: 'declared' }, { type: 'DMF (US)', product: 'Metformin HCl', number: 'Type II · 2x,xxx', expiry: '', status: 'declared' }] };
  function docsOf(slug) { var s = load(); return (s[slug] || SEED[slug] || []).slice(); }
  var GMP = /GMP|ISO 17025|GDP|ISO 15378|ISO 22716/i;
  var TIER = [['Not verified', '#94A3B8'], ['Registered', '#1A56DB'], ['Licensed', '#7C3AED'], ['Inspected', '#10B981']];
  var MEMO = {};
  function sig(co) { return [co.status, co.licensed, co.registry, (co.certs || []).join(','), window.__dxStoreVer || 0].join('|'); }   /* the store version changes on every write */
  function tierOf(co) { if (!co) return 0; var k = sig(co), m = MEMO[co.slug]; if (m && m.k === k) return m.t; var t = tierCalc(co); MEMO[co.slug] = { k: k, t: t }; return t; }   /* recomputed only when the company's data changes */
  function tierCalc(co) {
    if (!co || co.status !== 'verified' || !co.registry) return 0;
    var lic = co.licensed || (co.certs || []).some(function (c) { return /EDA licensed/i.test(c); });
    if (!lic) return 1;
    var creds = window.dxHubData.credentials(co).filter(function (c) { return !/^Member:/.test(c.name); });
    var insp = creds.some(function (c) { return GMP.test(c.name) && c.state !== 'expired' && c.checked; });
    return insp ? 3 : 2;
  }
  function badge(t, small) { var x = TIER[t]; return '<span class="dx-tier' + (small ? ' sm' : '') + '" style="--tc:' + x[1] + '" title="Verification level ' + t + ' of 3: ' + x[0] + '"><i class="' + (t >= 1 ? 'on' : '') + '"></i><i class="' + (t >= 2 ? 'on' : '') + '"></i><i class="' + (t >= 3 ? 'on' : '') + '"></i>' + (t ? 'Level ' + t + ' · ' : '') + x[0] + '</span>'; }
  var ST = { verified: ['Verified', '#10B981'], declared: ['Self-declared', '#1A56DB'], review: ['Under review', '#F59E0B'], soon: ['Expires soon', '#F59E0B'], expired: ['Expired', '#EF4444'], missing: ['Not provided', '#94A3B8'] };
  function items(co) {
    var out = [], ver = co.status === 'verified';
    out.push({ g: 'Company', n: 'Commercial registry', v: co.registry ? 'No. ' + co.registry : '', s: co.registry ? (ver ? 'verified' : 'declared') : 'missing' });
    out.push({ g: 'Company', n: 'Tax card', v: '', s: ver ? 'verified' : 'missing' });
    out.push({ g: 'Company', n: 'EDA / industrial licence', v: '', s: co.licensed ? 'verified' : 'missing' });
    window.dxHubData.credentials(co).filter(function (c) { return !/^Member:/.test(c.name) && !/EDA licensed/i.test(c.name); }).forEach(function (c) {
      out.push({ g: 'Sites', n: c.name, v: c.site + (c.expiry ? ' · valid to ' + c.expiry : ''), s: c.state === 'expired' ? 'expired' : c.state === 'soon' ? 'soon' : c.checked ? 'verified' : 'declared' });
    });
    var docs = docsOf(co.slug), sect = (co.sectors || []).join(' ');
    docs.forEach(function (d) { out.push({ g: 'Product documents', n: d.type + (d.product ? ' — ' + d.product : ''), v: d.number + (d.expiry ? ' · valid to ' + d.expiry : ''), s: d.status || 'declared' }); });
    if (/API/.test(sect)) ['CEP', 'DMF (US)', 'ASMF (EU)'].forEach(function (t) { if (!docs.some(function (d) { return d.type === t; })) out.push({ g: 'Product documents', n: t, v: '', s: 'missing', req: t }); });
    if (/Distribution/.test(sect) && !(co.certs || []).some(function (c) { return /GDP/.test(c); })) out.push({ g: 'Sites', n: 'GDP', v: '', s: 'missing', req: 'GDP certificate' });
    return out;
  }
  function passportHTML(co, own) {
    var t = tierOf(co), rows = items(co), groups = {};
    rows.forEach(function (r) { (groups[r.g] = groups[r.g] || []).push(r); });
    var h = '<section class="dx-pass"><div class="dx-pass-h"><div><div class="dx-pass-k">COMPLIANCE PASSPORT</div><div class="dx-pass-t">Documents &amp; certificates</div></div>' + badge(t) + '</div>';
    Object.keys(groups).forEach(function (g) {
      h += '<div class="dx-pass-g">' + g + '</div>';
      groups[g].forEach(function (r) { var s = ST[r.s] || ST.declared;
        h += '<div class="dx-pass-r"><div><b>' + esc(r.n) + '</b>' + (r.v ? '<span>' + esc(r.v) + '</span>' : '') + '</div><div class="dx-pass-s"><em style="--sc:' + s[1] + '">' + s[0] + '</em>' +
             (r.req && !own ? '<button type="button" class="dx-pass-req" data-req="' + esc(r.req) + '" data-slug="' + esc(co.slug) + '">Request</button>' : '') + '</div></div>'; });
    });
    h += '<p class="dx-pass-n">Levels: 1 Registered — registry & tax card checked · 2 Licensed — EDA / industrial licence · 3 Inspected — a site with a valid GMP-type certificate. Self-declared documents are shown as provided by the company.</p></section>';
    return h;
  }
  function coFromHeader() { if (!document.querySelector('#dxDir.cp h1.cp-name')) return null; var s = window.dxDir.S && window.dxDir.S.open; return s ? (window.dxDir.bySlug(s) || null) : null; }   /* the open slug, never the heading text: names are not unique */
  function activeTab() { var a = document.querySelector('#dxDir .cp-tabs .on, #dxDir .cp-tabs [aria-selected="true"], #dxDir .cp-tabs .active'); return a ? (window.dxOrigText ? window.dxOrigText(a) : a.textContent).trim() : ''; }
  function decorate() {
    var dir = document.getElementById('dxDir'); if (!dir) return;
    /* directory cards */
    dir.querySelectorAll('.hb-card[data-slug]').forEach(function (card) { if (card.dataset.tier) return; var co = window.dxDir.bySlug(card.dataset.slug); card.dataset.tier = '1'; if (!co) return;
      var t = tierOf(co); if (!t) return; var m = card.querySelector('.dr-meta') || card.querySelector('h3, h4'); if (m) m.insertAdjacentHTML('afterend', '<div class="dx-tier-row">' + badge(t, true) + '</div>'); });
    /* company page: badge + passport on Overview */
    if (dir.classList.contains('cp')) {
      var co = coFromHeader(); if (!co) return; var h1 = dir.querySelector('h1.cp-name');
      if (h1 && !h1.parentElement.querySelector('.dx-tier-h')) h1.insertAdjacentHTML('afterend', '<div class="dx-tier-h">' + badge(tierOf(co)) + '</div>');
      if (/^Overview/.test(activeTab()) && !dir.querySelector('.dx-pass')) { var body = dir.querySelector('.cp-body'); if (body) body.insertAdjacentHTML('afterbegin', passportHTML(co, window.dxDir.ownsPage && window.dxDir.ownsPage(co))); }
    }
    /* workspace: ladder + add documents on "Plan & verification" */
    if (dir.classList.contains('ws') && /Plan/.test(activeTab()) && !dir.querySelector('.dx-ladder')) {
      var mine = window.dxDir.mine && window.dxDir.mine(); var body2 = dir.querySelector('.cp-body'); if (!mine || !body2) return; var t2 = tierOf(mine);
      var steps = [['Registered', 'Commercial registry and tax card checked by Drugbox'], ['Licensed', 'EDA or industrial licence on file'], ['Inspected', 'At least one site with a valid GMP-type certificate']];
      body2.insertAdjacentHTML('afterbegin', '<section class="dx-ladder"><div class="dx-pass-k">VERIFICATION LEVEL</div><div class="dx-lad">' + steps.map(function (s, i) { return '<div class="dx-lad-s' + (t2 > i ? ' on' : t2 === i ? ' next' : '') + '"><i>' + (i + 1) + '</i><b>' + s[0] + '</b><span>' + s[1] + '</span></div>'; }).join('') + '</div>' +
        '<div class="dx-lad-a"><span>' + (t2 >= 3 ? 'Top level reached. Keep certificates current to stay here.' : 'Next: ' + steps[t2][1] + '.') + '</span><button type="button" class="dx-add-doc">Add document</button></div></section>' + passportHTML(mine, true));
    }
  }
  function addDoc() {
    var mine = window.dxDir.mine && window.dxDir.mine(); if (!mine) return;
    var m = D.modal({ title: 'Add a compliance document', secondary: 'Cancel', body:
      '<div class="dx-lc-f"><label>Document<select id="pdT"><option>CEP</option><option>DMF (US)</option><option>ASMF (EU)</option><option>WHO PQ</option><option>GDP certificate</option><option>ISO 9001</option><option>Stability data (Zone IVb)</option></select></label>' +
      '<label>Product / site<input id="pdP" type="text" placeholder="e.g. Metformin HCl"></label><label>Number / reference<input id="pdN" type="text" placeholder="e.g. R1-CEP 20XX-XXX"></label><label>Valid to (optional)<input id="pdE" type="month"></label></div>' +
      '<p class="dx-lc-note">Shown as self-declared until Drugbox checks the document.</p>',
      primary: { label: 'Save', onClick: function (el) { var g = function (id) { var x = el.querySelector('#' + id); return x ? x.value.trim() : ''; }; if (!g('pdN')) { var n = el.querySelector('#pdN'); if (n) { n.focus(); n.style.borderColor = '#EF4444'; } return false; }
        var s = load(); var list = s[mine.slug] || docsOf(mine.slug); list.push({ type: g('pdT'), product: g('pdP'), number: g('pdN'), expiry: g('pdE'), status: 'declared' }); s[mine.slug] = list; save(s);
        setTimeout(function () { document.querySelectorAll('.dx-ladder,.dx-pass').forEach(function (x) { x.remove(); }); decorate(); }, 0); D.toast && D.toast('Document added — shown as self-declared'); } } });
    return m;
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('.dx-add-doc'); if (a) { e.preventDefault(); addDoc(); return; }
    var r = e.target.closest && e.target.closest('.dx-pass-req'); if (!r) return; e.preventDefault(); e.stopPropagation();
    var co = window.dxDir.bySlug(r.dataset.slug); if (!co || !window.dxDeals) return;
    var d = window.dxDeals.create('dossier', co.slug, 'Document request — ' + r.dataset.req, { doc: r.dataset.req }, 'Please share your ' + r.dataset.req + ' for our supplier qualification.');
    if (d) { r.textContent = 'Requested'; r.disabled = true; D.toast && D.toast('Request sent to ' + co.name + ' — follow it in Requests & deals'); }
  }, true);
  C.onRender('tiers', idle(decorate));
  window.dxTiers = { tierOf: tierOf, items: items, addDoc: addDoc };
})();
