/* Batch 1 — category colour system · product icons in hexagons · hexagon live signals · undo instead of "Are you sure?" */
(function () {
  var C = window.dxCore; if (!C) return;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }

  /* ── 1. one colour per listing type, everywhere ── */
  var TYPE_RX = [['supply', /supply|for sale|selling/i], ['demand', /demand|buying|looking to buy|wanted/i], ['license', /licen[cs]e|registration dossier/i],
    ['cmo', /\bcmo\b|toll|contract manufactur/i], ['equipment', /equipment|machine|press/i], ['service', /service|providing/i], ['job', /\bjobs?\b|hiring/i], ['training', /training|course/i]];
  function typeOf(s) { s = String(s || ''); for (var i = 0; i < TYPE_RX.length; i++) if (TYPE_RX[i][1].test(s)) return TYPE_RX[i][0]; return ''; }
  function colours() {
    document.querySelectorAll('#mkx .sponsored-card, #mkx .lcard, #mkx .scard, #mkx .dcard, #mkx .jcard').forEach(function (c) {
      if (c.dataset.dxcat) return;
      var t = c.classList.contains('scard') ? 'service' : c.classList.contains('dcard') ? 'demand' : c.classList.contains('jcard') ? 'job' : (c.dataset.cat || typeOf(txt(c.querySelector('.lt'))) || 'supply');
      c.dataset.dxcat = t;
    });
    document.querySelectorAll('#mkx .cat-item').forEach(function (c) { if (!c.dataset.dxcat) c.dataset.dxcat = typeOf(txt(c.querySelector('.cat-label'))) || ''; });
    document.querySelectorAll('#mkx .lt').forEach(function (l) { if (!l.dataset.dxcat) l.dataset.dxcat = typeOf(txt(l)); });
    document.querySelectorAll('#mkx .f-opt .cat-cb').forEach(function (cb) { var o = cb.closest('.f-opt'); if (o && !o.dataset.dxcat) o.dataset.dxcat = cb.dataset.cat; });
    document.querySelectorAll('.tick-i b').forEach(function (b) { if (!b.dataset.dxcat) b.dataset.dxcat = typeOf(txt(b)) || 'other'; });
  }

  /* ── 2. product pictures: a category-coloured hexagon with a product-type icon ── */
  var PRODUCT = [[/cosmetic|serum|hyaluron|retinol|niacinamide|skin|cream/i, 'drop'], [/tablet|capsule|dosage|finished|sachet/i, 'pill'], [/registration|dossier|ctd|eda|sfda|licen/i, 'doc'],
    [/cmo|toll|manufactur|facility|plant/i, 'factory'], [/equipment|press|machine|hplc system|blister/i, 'gear'], [/stability|testing|lab|analysis|qc|qa/i, 'microscope'],
    [/formulation|develop/i, 'flask'], [/gcc|export|shipping|freight/i, 'globe'], [/consult|gap analysis|audit/i, 'clipboard'], [/api|hcl|sulphate|sulfate|powder|bp\/usp|raw/i, 'flask']];
  function productIcon(title) { for (var i = 0; i < PRODUCT.length; i++) if (PRODUCT[i][0].test(title)) return PRODUCT[i][1]; return 'box'; }
  function pictures() {
    document.querySelectorAll('#mkx .sp-img, #mkx .lc-em, #mkx .sc-ic').forEach(function (el) {
      if (el.dataset.dx) return;
      var card = el.closest('.sponsored-card,.lcard,.scard'); if (!card) return;
      var title = txt(card.querySelector('.sp-title,.lc-title,.sc-title')) + ' ' + txt(card.querySelector('.sp-desc,.lc-desc'));
      el.innerHTML = '<span class="dx-prod">' + ic(productIcon(title)) + '</span>'; el.dataset.dx = '1'; el.classList.add('dx-prod-box');
    });
  }

  /* ── 3. live signals become pulsing hexagons (CSS does the work; mark the ones drawn as text) ── */
  function live() {
    document.querySelectorAll('.act-title, #mkx .act-title').forEach(function (t) {
      if (t.dataset.dx) return; t.dataset.dx = '1';
      var w = document.createTreeWalker(t, NodeFilter.SHOW_TEXT, null), n;
      while ((n = w.nextNode())) { var i = n.nodeValue.indexOf('●'); if (i >= 0) { n.nodeValue = n.nodeValue.replace('●', ''); var s = document.createElement('i'); s.className = 'dx-live'; t.insertBefore(s, t.firstChild); break; } }
    });
  }

  /* ── 4. undo instead of confirm (feed posts, clearing notifications) ── */
  if (typeof window.deletePost === 'function' && window.dxUndo) {
    var origDelete = window.deletePost;
    window.deletePost = function (postId) {
      var el = document.getElementById('post-' + postId); if (!el) return origDelete.apply(this, arguments);
      el.classList.add('dx-gone');
      window.dxUndo('Post deleted', function () { el.classList.remove('dx-gone'); }, function () {
        var oc = window.confirm, ot = window.toast; window.confirm = function () { return true; }; window.toast = function () {};
        try { origDelete(postId); } finally { window.confirm = oc; window.toast = ot; }
      });
    };
  }
  if (typeof window.clearAllNotifs === 'function' && window.dxUndo) {
    var origClear = window.clearAllNotifs;
    window.clearAllNotifs = function () {
      var keep = (window.NOTIFS || []).slice(), ot = window.toast; window.toast = function () {};
      try { origClear.apply(this, arguments); } finally { window.toast = ot; }
      window.dxUndo('Notifications cleared', function () {
        window.NOTIFS.length = 0; keep.forEach(function (n) { window.NOTIFS.push(n); });
        var c = document.getElementById('content'); if (c && typeof window.renderNotifs === 'function' && document.body.getAttribute('data-page') === 'notifs') window.renderNotifs(c);
        if (typeof window.updateBadges === 'function') window.updateBadges();
      });
    };
  }

  C.onRender('mobile-nav-class', function () { var b = document.querySelector('.mb-btn'); if (b && b.parentNode && !b.parentNode.classList.contains('dx-mbnav')) b.parentNode.classList.add('dx-mbnav'); });
  C.onRender('ptab-row', function () { var t = document.querySelector('.ptab'); if (t && t.parentNode && !t.parentNode.classList.contains('dx-ptabs')) t.parentNode.classList.add('dx-ptabs'); });
  C.onRender('pstat-row', function () { var n = document.querySelector('.pstat-n'); var row = n && n.parentNode && n.parentNode.parentNode; if (row && !row.classList.contains('dx-pstats')) row.classList.add('dx-pstats'); });
  C.onRender('flt-row', function () { var f = document.querySelector('.mb-flt'); if (f && f.parentNode && !f.parentNode.classList.contains('dx-fltrow')) f.parentNode.classList.add('dx-fltrow'); });
  C.onRender('category-colours', colours);
  C.onRender('product-pictures', pictures);
  C.onRender('live-signals', live);
})();
