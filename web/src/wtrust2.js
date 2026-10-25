/* ===== AREA w-trust (part 2): offers, held posts, groups, Admin → Review =====
   See wtrust.js for the whole area. Everything here draws in the approved visual language (the page's own form fields, chips,
   the kit's windows) and reads / writes through window.dxTrust (demo: this browser; live: web/src/live/wtrust.js). */
(function () {
  var D = window.DBK, C = window.dxCore, UI = window.dxTrustUI; if (!D || !C || !UI) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function me() { return window.ME || {}; }
  function toast(m) { (window.toast || D.toast)(m); }
  function S() { return window.dxTrust; }
  function live() { return !!window.dxLive; }
  function T(s) { return window.dxT ? window.dxT(s) : s; }
  function page() { return document.body.getAttribute('data-page') || ''; }

  /* ══════════ 1. who stands behind an offer (W-16, W-25) ══════════ */
  var TRADE_FORMS = ['supply', 'demand', 'cmo', 'equipment', 'license', 'service'];
  function myCompanies() { var d = window.dxDir; return d && d.myCompanies ? (d.myCompanies() || []) : []; }
  function acting() { var d = window.dxDir, a = d && d.mine && d.mine(); return a && a.slug ? a : null; }
  function asOptions() {
    var cos = myCompanies(), a = acting(), h = '<option value="individual">Myself (an individual)</option>';
    cos.forEach(function (c) { var ok = c.status === 'verified';
      h += '<option value="company:' + esc(c.slug) + '"' + (ok ? '' : ' disabled') + (ok && a && a.slug === c.slug ? ' selected' : '') + ' data-noi18n>' + esc(c.name) + ' — ' + esc(T(ok ? 'verified company' : 'needs the Drugbox badge')) + '</option>'; });
    return h + '<option value="broker">A broker for someone else (وسيط)</option>';
  }
  function asField(type) {
    return '<div class="field wt-as-field" data-wt-form="' + type + '"><label class="field-label">Posting as <span class="req">*</span></label><select class="field-input wt-as" aria-label="Posting as">' + asOptions() + '</select>' +
      '<div class="field-hint wt-as-hint">A company page posts trade offers as the company only with the Drugbox verification badge. Your offer card says who posts it.</div>' +
      '<div class="wt-broker" hidden><div class="field"><label class="field-label">Whose product or file is it? <span class="req">*</span></label><input class="field-input wt-bfor" maxlength="120" placeholder="The owner company or person"></div>' +
      '<div class="field"><label class="field-label">Your commission (%) <span class="req">*</span></label><input class="field-input wt-bcom" inputmode="decimal" maxlength="5" placeholder="e.g. 2.5"></div>' +
      '<div class="field"><label class="field-label">The owner’s authorisation <span class="req">*</span></label><input type="file" class="wt-bauth" accept="application/pdf,image/jpeg,image/png,image/webp"><div class="field-hint">Buyers can open it — it shows you are allowed to offer it.</div></div></div></div>';
  }
  function addAsFields() {
    TRADE_FORMS.forEach(function (t) {
      var f = $('form-' + t); if (!f) return; var cur = f.querySelector('.wt-as-field');
      if (cur) { var s = cur.querySelector('.wt-as'), v = s.value; s.innerHTML = asOptions(); if ([].some.call(s.options, function (o) { return o.value === v && !o.disabled; })) s.value = v; return; }
      var btn = f.querySelector('.btn-create'), host = btn && (btn.closest('.form-actions') || btn.parentElement); if (!host) return;
      host.insertAdjacentHTML('beforebegin', asField(t));
      if (window.dxI18nAttrs) window.dxI18nAttrs(f);
    });
  }
  document.addEventListener('change', function (e) {
    var s = e.target.closest && e.target.closest('.wt-as'); if (!s) return; var b = s.closest('.wt-as-field').querySelector('.wt-broker'); if (b) b.hidden = s.value !== 'broker';
  });
  /* the choice of the form being published, read by the live adapter (window.dxTradeAs) and by the demo card */
  window.__wtAs = null;
  function readAs(f) {
    var box = f.querySelector('.wt-as-field'); if (!box) return { as: 'individual' };
    var v = box.querySelector('.wt-as').value, o = { as: v.indexOf('company:') === 0 ? 'company' : v };
    if (o.as === 'company') { o.slug = v.slice(8); var c = myCompanies().filter(function (x) { return x.slug === o.slug; })[0]; o.name = c ? c.name : ''; }
    if (o.as === 'broker') { o.broker_for = box.querySelector('.wt-bfor').value.trim(); o.commission = box.querySelector('.wt-bcom').value.trim().replace(',', '.').replace('%', ''); o.file = (box.querySelector('.wt-bauth').files || [])[0] || null; }
    return o;
  }
  function checkAs(f, o) {
    var box = f.querySelector('.wt-as-field'); if (!box || o.as !== 'broker') return true;
    var bad = function (sel, m) { var i = box.querySelector(sel); if (i) { i.classList.add('dbk-err'); i.addEventListener('input', function () { i.classList.remove('dbk-err'); }, { once: true }); } toast(m); return false; };
    if (o.broker_for.length < 2) return bad('.wt-bfor', 'A broker names whose product or file this is');
    if (!/^\d{1,2}(\.\d{1,2})?$/.test(o.commission) || +o.commission > 50) return bad('.wt-bcom', 'State the commission as a percentage (0–50)');
    if (!o.file) return bad('.wt-bauth', 'A broker attaches the owner’s authorisation');
    if (o.file.size > 10 * 1024 * 1024) return bad('.wt-bauth', 'The file can be up to 10 MB');
    return true;
  }
  var BYPASS = false;
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mkx .btn-create, #mkx .btn-draft'); if (!b || BYPASS) return;
    var f = b.closest('.form-section'); if (!f) return; var type = f.id.replace('form-', ''); if (TRADE_FORMS.indexOf(type) < 0) return;
    e.preventDefault(); e.stopImmediatePropagation();
    UI.needTradeProfile(function () {
      var o = readAs(f); if (!checkAs(f, o)) return;
      window.__wtAs = o; BYPASS = true; try { b.click(); } finally { BYPASS = false; }
    });
  }, true);

  /* the chip on an offer card: «Verified company» / «Individual» / «Broker · n% commission» / Drugbox */
  function chipHtml(i) {
    if (!i) return '';
    if (i.as === 'company') return '<span class="ti g wt-as-chip" data-wt-as="company">✓ Verified company</span>';
    if (i.as === 'broker') return '<span class="ti o wt-as-chip" data-wt-as="broker" title="' + esc(T('Offered by a broker for the owner')) + '">🤝 Broker' + (i.commission != null && i.commission !== '' ? ' · ' + esc(String(+i.commission)) + '% commission' : '') + '</span>' +
      (i.broker_for ? '<span class="ti wt-as-for" data-noi18n>' + esc(i.broker_for) + '</span>' : '');
    if (i.as === 'drugbox') return '<span class="ti b wt-as-chip" data-wt-as="drugbox">Drugbox</span>';
    return '<span class="ti wt-as-chip" data-wt-as="individual">👤 Individual</span>';
  }
  function badge(card, i) {
    if (!card || !i) return; var tb = card.querySelector('.trust-bar');
    if (!tb) { var host = card.querySelector('.dc-meta, .dc-foot, .lc-inner, .sc-provider'); if (!host) return; host.insertAdjacentHTML('beforeend', '<div class="trust-bar wt-tb"></div>'); tb = card.querySelector('.trust-bar'); }
    [].forEach.call(tb.querySelectorAll('.wt-as-chip, .wt-as-for'), function (x) { x.remove(); });
    tb.insertAdjacentHTML('afterbegin', chipHtml(i)); tb.style.display = '';
    card.dataset.wtAs = i.as;
    if (i.held) heldOnCard(card);
  }
  function heldOnCard(card) { if (card.querySelector('.wt-held')) return; var host = card.querySelector('.lc-inner') || card; host.insertAdjacentHTML('afterbegin', '<div class="wt-held">⏳ Waiting for Drugbox review — only you can see it</div>'); }
  window.dxTrustUI.badge = badge;
  /* the demo's sample cards: sample data says who posts them */
  function demoCards() {
    var n = 0; [].forEach.call(document.querySelectorAll('#mkx .supply-grid .lcard, #mkx .dcard, #mkx .lcard'), function (c) {
      if (c.dataset.wtAs || c.dataset.live) return;
      if (c.dataset.new === '1') return;                                        /* a card just published gets its own choice (below) */
      badge(c, c.classList.contains('dcard') ? { as: 'individual' } : (n++ % 2 === 0 ? { as: 'company' } : { as: 'individual' }));
    });
  }
  /* after Publish: the new card (the approved page inserts it) and, in the demo, the review rules */
  var oHook = window.dxLiveHook;
  window.dxLiveHook = function (kind, d) {
    var r = oHook ? oHook.apply(this, arguments) : undefined;
    if (kind === 'listing' && !live() && d && TRADE_FORMS.indexOf(d.type) >= 0) {
      var o = window.__wtAs || { as: 'individual' }, t = UI.topics([d.title, d.desc, d.price, d.moq, o.broker_for].join(' '));
      var info = { as: o.as, commission: o.commission, broker_for: o.broker_for, held: t.length > 0 };
      D.store.set('wtMyOffers', (D.store.get('wtMyOffers', 0) || 0) + 1);
      if (t.length) { UI.demo.hold('offer', d.title, d.title + ' — ' + (d.desc || ''), t); notifyHeld(t, d.title); }
      setTimeout(function () {
        var c = [].filter.call(document.querySelectorAll('#mkx [data-new="1"]'), function (x) { return !x.dataset.wtAs; })[0];
        if (c) badge(c, info);
        if (t.length) toast('Your offer is waiting for Drugbox review — it looks like ' + UI.why(t) + '. You are told when it is checked.');
      }, 400);
      window.__wtAs = null;
    }
    return r;
  };
  function notifyHeld(t, text) {
    if (live() || !window.NOTIFS) return;
    window.NOTIFS.unshift({ id: Date.now(), uid: me().id, icon: '🔎', text: esc(T('Drugbox is checking your post before it shows') + ' — ' + T('it looks like') + ' ' + UI.why(t) + ': “' + String(text || '').slice(0, 60) + '”'), ts: 'now', read: false, type: 'auto_review' });
    if (window.updateBadges) window.updateBadges();
  }

  /* ══════════ 2. posts held for review (W-17) ══════════ */
  var oSubmit = window.submitPost;
  if (typeof oSubmit === 'function') window.submitPost = function () {
    var b = $('postBody'), body = b ? b.value : '', inGroup = !!document.querySelector('.modal-bg[data-gpk]');
    var r = oSubmit.apply(this, arguments);
    if (!live() && !inGroup && body.trim()) {
      var t = UI.topics(body), p = window.POSTS && window.POSTS[0];
      if (t.length && p && p.uid === me().id) { p.wtHeld = t; UI.demo.hold('post', p.id, body, t); notifyHeld(t, body);
        setTimeout(function () { toast('Your post is waiting for Drugbox review — it looks like ' + UI.why(t) + '. Only you see it until it is checked.'); markHeld(); }, 300); }
    }
    return r;
  };
  var HELD = { at: 0, list: [] };
  function heldList() {
    if (!live()) { HELD.list = (window.POSTS || []).filter(function (p) { return p.wtHeld; }).map(function (p) { return { kind: 'post', item: p.id, topics: p.wtHeld }; }); return Promise.resolve(HELD.list); }
    if (Date.now() - HELD.at < 15000) return Promise.resolve(HELD.list);
    HELD.at = Date.now(); return S().myHeld().then(function (l) { HELD.list = l || []; return HELD.list; }, function () { return HELD.list; });
  }
  window.dxTrustUI.heldChanged = function () { HELD.at = 0; markHeld(); };
  function markHeld() {
    heldList().then(function (l) {
      l.forEach(function (h) {
        if (h.kind === 'post') { var el = $('post-' + h.item); if (el && !el.querySelector('.wt-held')) el.insertAdjacentHTML('afterbegin', '<div class="wt-held">⏳ Waiting for Drugbox review — only you can see this post' + (h.topics && h.topics.length ? ' · <span>it looks like</span> <span>' + esc(UI.why(h.topics)) + '</span>' : '') + '</div>'); }
        if (h.kind === 'offer') { var row = document.querySelector('#tab-manage [data-ml="' + h.item + '"]'), card = document.querySelector('#mkx [data-live="p' + h.item + '"]');
          if (row && !row.querySelector('.wt-held')) row.children[1] && row.children[1].insertAdjacentHTML('beforeend', '<div class="wt-held wt-held-s">⏳ Waiting for Drugbox review</div>');
          if (card) heldOnCard(card); }
        if (h.kind === 'pending') { var gp = $('post-' + h.item) || document.querySelector('#gpBox [data-pid="' + h.item + '"]'); if (gp && !gp.querySelector('.wt-held')) gp.insertAdjacentHTML('afterbegin', '<div class="wt-held">⏳ Waiting for the group’s admins — only you and they can see it</div>'); }
      });
      if (window.dxI18nAttrs) document.querySelectorAll('.wt-held').forEach(function (x) { if (!x.dataset.i18n) { x.dataset.i18n = 1; } });
    });
  }

  /* ══════════ 3. groups: admin tools, rules on join, pending posts, invite links (W-08, W-44) ══════════ */
  function G() { var c = window.dxGroups && window.dxGroups.current && window.dxGroups.current(); return c || null; }
  var TOOLS_KEYS = ['rules_required', 'daily_post_limit', 'slow_mode_minutes', 'block_duplicates', 'block_links', 'review_posts', 'require_category'];
  function toolsHtml(t) {
    function chk(id, on, label) { return '<label class="gp-radio wt-tool"><input type="checkbox" id="' + id + '"' + (on ? ' checked' : '') + '> <span>' + label + '</span></label>'; }
    return '<div class="field wt-tools"><label class="field-label">Admin tools</label>' +
      chk('wtRulesReq', t.rules_required, 'Members read and accept the rules before they join') +
      '<div class="wt-tool-row"><label for="wtDaily">Posts a day per member</label><input class="field-input" id="wtDaily" type="number" min="1" max="50" placeholder="No limit" value="' + esc(t.daily_post_limit || '') + '"></div>' +
      '<div class="wt-tool-row"><label for="wtSlow">Slow mode: minutes between a member’s posts</label><input class="field-input" id="wtSlow" type="number" min="1" max="1440" placeholder="Off" value="' + esc(t.slow_mode_minutes || '') + '"></div>' +
      chk('wtDup', t.block_duplicates, 'Refuse the same post twice in a week') + chk('wtLinks', t.block_links, 'Refuse invite links to outside chat groups (WhatsApp, Telegram…)') +
      chk('wtReview', t.review_posts, 'Admins publish members’ posts first (a review queue)') + chk('wtCat', t.require_category, 'Every post says what it is (a category)') +
      '<div class="field-hint">Admins and Sub-Admins are not limited. A member who is stopped is told why.</div></div>';
  }
  function readTools(ts) {
    var n = function (id) { var v = +(ts.querySelector('#' + id) || {}).value; return v > 0 ? Math.round(v) : null; }, c = function (id) { return !!(ts.querySelector('#' + id) || {}).checked; };
    return { rules_required: c('wtRulesReq'), daily_post_limit: n('wtDaily'), slow_mode_minutes: n('wtSlow'), block_duplicates: c('wtDup'), block_links: c('wtLinks'), review_posts: c('wtReview'), require_category: c('wtCat') };
  }
  function paintTools() {
    var g = G(), ts = $('tab-settings'); if (!g || !ts || !g.admin) return;
    var anchor = ts.querySelector('#gpSetCountry'); anchor = anchor && anchor.closest('.field'); if (!anchor) return;
    if (ts.dataset.wtFor === g.key && ts.querySelector('.wt-tools')) return;
    var old = ts.querySelector('.wt-tools'); if (old) old.remove();
    anchor.insertAdjacentHTML('afterend', toolsHtml(S().tools(g))); ts.dataset.wtFor = g.key;
    if (window.dxI18nAttrs) window.dxI18nAttrs(ts);
  }
  window.addEventListener('click', function (e) {   /* window capture: before the page's own Save (which stops the click) */
    var b = e.target.closest && e.target.closest('#tab-settings .btn-create'); var g = G(), ts = $('tab-settings'); if (!b || !g || !ts || !ts.querySelector('.wt-tools')) return;
    var t = readTools(ts); if (t.daily_post_limit > 50) t.daily_post_limit = 50; if (t.slow_mode_minutes > 1440) t.slow_mode_minutes = 1440;
    S().saveTools(g, t).then(function () { delete ts.dataset.wtFor; }, function (er) { toast((er && er.message) || 'Could not save the admin tools — try again'); });
  }, true);

  /* rules on join: the window with the group's rules and "I accept" */
  function rulesOf(g, card) {
    var r = g && g.rules && g.rules.length ? g.rules : null;
    if (!r && card && card.dataset.rules) { try { r = JSON.parse(card.dataset.rules); } catch (x) {} }
    return (r || []).map(function (x) { return Array.isArray(x) ? x : [String(x), '']; });
  }
  function rulesDialog(title, rules, go) {
    D.modal({ title: 'The group’s rules', body: '<p><span>Before you join</span> <b data-noi18n>' + esc(title) + '</b><span>, read its rules:</span></p>' +
      '<ol class="wt-rules">' + (rules.length ? rules.map(function (r) { return '<li data-noi18n><b>' + esc(r[0]) + '</b>' + (r[1] ? ' — ' + esc(r[1]) : '') + '</li>'; }).join('') : '<li>Respect the members and keep to the group’s topic.</li>') + '</ol>' +
      '<label class="gp-radio"><input type="checkbox" id="wtRulesOk"> <span>I have read the rules and accept them</span></label>',
      primary: { label: 'Accept and join', onClick: function (bx) { var c = bx.querySelector('#wtRulesOk'); if (!c.checked) { c.parentNode.classList.add('dbk-err'); toast('Tick “I accept” to join'); return false; } go(); } } });
  }
  var JB = false;
  window.addEventListener('click', function (e) {
    if (JB) return;
    var b = e.target.closest && e.target.closest('#gpBox [data-gpa="join"], #gpBox [data-gpa="request"], #gpBox [data-gpa="accept"], #groupDetail [data-gpa="join"], #groupDetail [data-gpa="request"], #groupDetail [data-gpa="accept"], #gx .gcard .gcard-btn.btn-join');
    if (!b) return;
    var card = b.closest('.gcard'), g = card ? null : G(); if (!card && g) card = g.card;
    var key = g ? g.key : card && (card.dataset.gid ? 'g' + card.dataset.gid : card.dataset.gk);
    var tools = S().tools(g || { key: key, card: card });
    if (!tools.rules_required || S().accepted(g || { key: key, card: card })) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var title = g ? g.title : (card && card.querySelector('.gcard-title') || {}).textContent || '';
    var seed = !live() && window.dxGroups && window.dxGroups.seed && window.dxGroups.seed[key];
    rulesDialog(title, g ? rulesOf(g, card) : rulesOf(seed ? { rules: seed.rules } : null, card), function () {
      S().acceptRules(g || { key: key, card: card }).then(function () { JB = true; try { b.click(); } finally { JB = false; } }, function (er) { toast((er && er.message) || 'Could not join — try again'); });
    });
  }, true);

  /* the demo keeps the group's posting rules the way the database does in the live app (0094) */
  function demoGroupPosts(key) { var s = D.store.get('groupData', {}) || {}; return ((s.posts || {})[key] || []).filter(function (p) { return !p.del; }); }
  window.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.modal-bg[data-gpk] .btn-p'); if (!b || live()) return;
    var m = b.closest('.modal-bg'), g = G(); if (!g || g.key !== m.getAttribute('data-gpk') || g.admin) return;
    var t = S().tools(g), body = ((m.querySelector('#postBody') || {}).value || '').trim(), cat = (m.querySelector('#postCat') || {}).value || 'general', mine = demoGroupPosts(g.key).filter(function (p) { return p.uid === me().id; });
    var stop = function (msg) { e.preventDefault(); e.stopImmediatePropagation(); toast(msg); return true; };
    if (t.block_links && UI.topics(body).indexOf('invite') >= 0) return stop('Links to outside chat groups are not allowed in this group');
    if (t.require_category && cat === 'general') return stop('This group asks every post to say what it is — choose a category');
    var today = new Date(); today.setHours(0, 0, 0, 0);
    if (t.daily_post_limit && mine.filter(function (p) { return Date.parse(p.at) >= today.getTime(); }).length >= t.daily_post_limit) return stop('This group allows ' + t.daily_post_limit + ' post(s) a day per member — you can post again tomorrow');
    var last = mine.reduce(function (a, p) { var x = Date.parse(p.at) || 0; return x > a ? x : a; }, 0);
    if (t.slow_mode_minutes && last && Date.now() - last < t.slow_mode_minutes * 6e4) return stop('Slow mode: this group allows one post every ' + t.slow_mode_minutes + ' minute(s) — wait ' + Math.max(1, Math.ceil((last + t.slow_mode_minutes * 6e4 - Date.now()) / 6e4)) + ' more');
    if (t.block_duplicates && body.length >= 12 && mine.some(function (p) { return UI.norm(p.body) === UI.norm(body) && Date.now() - (Date.parse(p.at) || 0) < 7 * 864e5; })) return stop('You already posted this in the group this week — edit the earlier post instead of posting it again');
    if (t.review_posts) {
      e.preventDefault(); e.stopImmediatePropagation();
      var all = D.store.get('wtGroupPending', {}) || {}; (all[g.key] = all[g.key] || []).push({ id: 9100000000000 + Date.now(), uid: me().id, body: body, cat: cat, at: new Date().toISOString(), author: me().name });
      D.store.set('wtGroupPending', all); m.remove(); toast('Sent to the group’s admins — it shows once they publish it'); return;
    }
  }, true);

  /* Manage: Pending posts and Invite link tabs (beside the page's Members / Reports / Settings / Requests) */
  function manageTabs() {
    var g = G(), gd = $('groupDetail'), tabs = gd && gd.querySelector('#managePanel .panel-tabs'); if (!g || !tabs || !g.admin) return;
    if (!tabs.querySelector('[data-wt-tab]')) {
      tabs.insertAdjacentHTML('beforeend', '<div class="gx-ptab" data-wt-tab="pending" role="tab" tabindex="0">⏳ Pending posts <span class="ptab-badge wt-pend-badge" style="display:none"></span></div><div class="gx-ptab" data-wt-tab="invite" role="tab" tabindex="0">🔗 Invite link</div>');
      var mp = gd.querySelector('#managePanel'); mp.insertAdjacentHTML('beforeend', '<div class="panel-body wt-pane" id="tab-wtpending" style="display:none"><div class="mod-queue"></div></div><div class="panel-body wt-pane" id="tab-wtinvite" style="display:none"></div>');
      if (window.dxI18nAttrs) window.dxI18nAttrs(tabs);
    }
    S().pending(g).then(function (l) { var bd = tabs.querySelector('.wt-pend-badge'); if (bd) { bd.textContent = l.length; bd.style.display = l.length ? '' : 'none'; } }, function () {});
  }
  function showPane(which) {
    var gd = $('groupDetail'); if (!gd) return;
    gd.querySelectorAll('#managePanel .panel-tabs .gx-ptab').forEach(function (x) { x.classList.toggle('active', x.dataset.wtTab === which); });
    ['members', 'reports', 'settings', 'requests'].forEach(function (k) { var p = $('tab-' + k); if (p) p.style.display = 'none'; });
    ['pending', 'invite'].forEach(function (k) { var p = $('tab-wt' + k); if (p) p.style.display = k === which ? 'block' : 'none'; });
    if (which === 'pending') paintPending(); else paintInvite();
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#managePanel .panel-tabs .gx-ptab'); if (!t) return;
    if (t.dataset.wtTab) { e.preventDefault(); e.stopImmediatePropagation(); showPane(t.dataset.wtTab); }
    else ['pending', 'invite'].forEach(function (k) { var p = $('tab-wt' + k); if (p) p.style.display = 'none'; });
  }, true);
  function paintPending() {
    var g = G(), q = document.querySelector('#tab-wtpending .mod-queue'); if (!g || !q) return; q.innerHTML = '<div class="gp-empty">Loading…</div>';
    S().pending(g).then(function (l) {
      q.innerHTML = l.length ? l.map(function (p) { return '<div class="mod-item" data-wtpid="' + esc(p.id) + '"><div class="mod-icon">⏳</div><div class="mod-content"><div class="mod-title"><b data-noi18n>' + esc(p.author || 'A member') + '</b></div>' +
        '<div class="mod-reason" data-noi18n>“' + esc(p.body) + '”</div><div class="mod-actions"><button type="button" class="mod-btn dismiss" data-wtpub="no">Decline</button><button type="button" class="mod-btn gp-approve" data-wtpub="yes">Publish</button></div></div></div>'; }).join('')
        : '<div class="gp-ok">✓ No posts waiting</div>';
      if (window.dxI18nAttrs) window.dxI18nAttrs(q);
    }, function (er) { q.innerHTML = '<div class="gp-empty">' + esc((er && er.message) || 'Could not load') + '</div>'; });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-wtpub]'); if (!b) return; var row = b.closest('[data-wtpid]'), g = G(); if (!row || !g) return;
    e.preventDefault(); b.disabled = true; var yes = b.dataset.wtpub === 'yes', id = row.dataset.wtpid;
    S().publish(g, id, yes).then(function () {
      if (!live() && yes) {   /* the demo: the post joins the group's posts */
        var all = D.store.get('wtGroupPending', {}) || {}, p = (all[g.key] || []).filter(function (x) { return String(x.id) === String(id); })[0], s = D.store.get('groupData', {}) || {};
        if (p) { s.posts = s.posts || {}; (s.posts[g.key] = s.posts[g.key] || []).unshift({ id: +p.id, uid: p.uid, cat: p.cat, body: p.body, ts: 'just now', likes: 0, rx: {}, cmt: 0, cm: [], sh: 0, views: 0, pin: false, imgs: [], files: [], own: p.uid === me().id, at: new Date().toISOString() }); D.store.set('groupData', s); }
      }
      toast(yes ? 'Published — the author is told' : 'Declined — the author is told'); paintPending(); manageTabs(); if (window.dxGroups) window.dxGroups.refresh('disc');
    }, function (er) { b.disabled = false; toast((er && er.message) || 'Could not save — try again'); });
  });
  function linkUrl(tok) { return location.origin + location.pathname + '#/join/' + tok; }
  function paintInvite() {
    var g = G(), box = $('tab-wtinvite'); if (!g || !box) return;
    var pr = S().partnerOf ? S().partnerOf(g) : null;
    box.innerHTML = '<div class="wt-inv"><h4>Moving a WhatsApp group here, honestly</h4><ol class="wt-steps"><li>Make an invite link below and share it in your WhatsApp group yourself.</li><li>Every member opens it and joins by themselves — after reading the rules.</li><li>Drugbox never imports phone numbers, contacts or members, and nobody is added without asking.</li><li>Sellers post their own offers again here; nobody re-posts them in their name.</li></ol>' +
      '<div class="wt-inv-new"><label for="wtLinkDays">Link works for</label><select class="field-input" id="wtLinkDays"><option value="7">7 days</option><option value="30" selected>30 days</option><option value="">No end date</option></select>' +
      '<label for="wtLinkMax">Uses</label><input class="field-input" id="wtLinkMax" type="number" min="1" max="100000" placeholder="No limit"><button type="button" class="btn-manage" data-wtlink="new">🔗 Make an invite link</button></div>' +
      '<div class="wt-links"><div class="gp-empty">Loading…</div></div>' +
      '<div class="wt-partner">' + (g.role === 'admin' ? (pr && pr.status === 'pending' ? '<p>🤝 Drugbox is checking your request to mark this a Drugbox partner group.</p>' : pr && pr.status === 'approved' ? '<p>🤝 This is a Drugbox partner group.</p>' :
        '<p>Bringing an established trade group? Ask Drugbox to mark it a <b>Drugbox partner group</b> — the badge shows you moved it here openly.</p><button type="button" class="btn-manage" data-wtlink="partner">🤝 Ask Drugbox</button>') : '') + '</div></div>';
    S().links(g).then(function (l) {
      var x = box.querySelector('.wt-links'); if (!x) return;
      x.innerHTML = l.length ? l.map(function (k) { var dead = k.revoked_at || (k.expires_at && Date.parse(k.expires_at) < Date.now()) || (k.max_uses && k.uses >= k.max_uses);
        return '<div class="wt-link-row' + (dead ? ' off' : '') + '" data-wtlid="' + esc(k.id) + '"><code data-noi18n dir="ltr">' + esc(linkUrl(k.token)) + '</code><span>' + esc(k.uses || 0) + (k.max_uses ? ' / ' + esc(k.max_uses) : '') + ' <span>joined</span></span>' +
          (k.expires_at ? '<span><span>until</span> <span data-noi18n>' + esc(String(k.expires_at).slice(0, 10)) + '</span></span>' : '') +
          (dead ? '<span>' + (k.revoked_at ? 'Stopped' : 'Expired') + '</span>' : '<button type="button" class="btn-manage" data-wtlink="copy">Copy</button><button type="button" class="btn-manage" data-wtlink="stop">Stop</button>') + '</div>'; }).join('')
        : '<div class="gp-empty">No invite links yet.</div>';
      if (window.dxI18nAttrs) window.dxI18nAttrs(box);
    }, function (er) { var x = box.querySelector('.wt-links'); if (x) x.innerHTML = '<div class="gp-empty">' + esc((er && er.message) || 'Could not load') + '</div>'; });
    if (window.dxI18nAttrs) window.dxI18nAttrs(box);
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-wtlink]'); if (!b) return; var g = G(); if (!g) return; e.preventDefault();
    var k = b.dataset.wtlink, row = b.closest('[data-wtlid]');
    if (k === 'new') { var days = +($('wtLinkDays') || {}).value || null, mx = +($('wtLinkMax') || {}).value || null; b.disabled = true;
      S().makeLink(g, days, mx).then(function (x) { b.disabled = false; copy(linkUrl(x.token)); paintInvite(); }, function (er) { b.disabled = false; toast((er && er.message) || 'Could not make the link'); }); }
    else if (k === 'copy' && row) copy(row.querySelector('code').textContent);
    else if (k === 'stop' && row) D.modal({ title: 'Stop this link?', body: '<p>Nobody can join with it any more. Members who joined stay.</p>', primary: { label: 'Stop link', danger: true, onClick: function () {
      S().stopLink(g, row.dataset.wtlid).then(function () { toast('Link stopped'); paintInvite(); }, function (er) { toast((er && er.message) || 'Could not stop the link'); }); } } });
    else if (k === 'partner') D.modal({ title: 'Ask Drugbox: partner group', body: '<div class="dbk-f"><label for="wtPn">Tell Drugbox about the group * (where it comes from, how many traders, its topic)</label><textarea id="wtPn" data-req maxlength="1000" rows="4"></textarea></div>',
      primary: { label: 'Send', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; var v = bx.querySelector('#wtPn').value.trim(); if (v.length < 10) { toast('Tell Drugbox about the group in at least 10 characters'); return false; }
        S().partnerAsk(g, v).then(function () { close(); toast('Sent — Drugbox will check it'); paintInvite(); }, function (er) { toast((er && er.message) || 'Could not send — try again'); }); return false; } } });
  });
  function copy(t) { try { navigator.clipboard.writeText(t).then(function () { toast('Invite link copied — share it in your group'); }, function () { toast(t); }); } catch (x) { toast(t); } }

  /* an invite link opened: #/join/<token> — the group, its rules, and Join (the person joins by themselves) */
  var JOIN = (/^#\/join\/([A-Za-z0-9_-]{20,40})$/.exec(location.hash) || [])[1] || null;
  window.addEventListener('hashchange', function () { var m = /^#\/join\/([A-Za-z0-9_-]{20,40})$/.exec(location.hash); if (m) { JOIN = m[1]; tryJoin(); } });
  function inApp() { var a = $('app'); return !!(a && a.getClientRects().length && me().id); }
  function tryJoin() {
    if (!JOIN || !inApp()) return; var tok = JOIN; JOIN = null;
    try { history.replaceState(null, '', location.pathname + location.search); } catch (x) {}
    S().preview(tok).then(function (p) {
      if (!p) { D.modal({ title: 'Invite link', body: '<p>This invite link is not valid — check that you copied all of it.</p>', secondary: 'Close' }); return; }
      if (!p.ok) { D.modal({ title: 'Invite link', body: '<p>This invite link no longer works — ask the group’s admin for a new one.</p>', secondary: 'Close' }); return; }
      if (p.member) { openGroup(p); return; }
      var rules = (p.rules || []).map(function (x) { return Array.isArray(x) ? x : [String(x), '']; });
      D.modal({ title: 'Join a group', body: '<div class="wt-join-h"><span class="wt-join-em">' + esc(p.emoji || '👥') + '</span><div><b data-noi18n>' + esc(p.name) + '</b>' + (p.partner ? ' <span class="wt-chip wt-ok">🤝 Drugbox partner group</span>' : '') +
          '<div class="wt-muted">' + esc((p.member_count || 0) + (p.member_count === 1 ? ' member' : ' members')) + '</div></div></div>' + (p.description ? '<p data-noi18n>' + esc(p.description) + '</p>' : '') +
          (rules.length ? '<div class="wt-muted">The group’s rules</div><ol class="wt-rules">' + rules.map(function (r) { return '<li data-noi18n><b>' + esc(r[0]) + '</b>' + (r[1] ? ' — ' + esc(r[1]) : '') + '</li>'; }).join('') + '</ol>' : '') +
          (p.rules_required ? '<label class="gp-radio"><input type="checkbox" id="wtRulesOk"> <span>I have read the rules and accept them</span></label>' : '') +
          '<div class="dbk-note">You join by yourself. Drugbox never adds people or imports contacts.</div>',
        primary: { label: 'Join group', onClick: function (bx, close) {
          var c = bx.querySelector('#wtRulesOk'); if (c && !c.checked) { toast('Tick “I accept” to join'); return false; }
          S().joinByLink(tok, !!c).then(function () { close(); toast('You joined ' + p.name); openGroup(p); }, function (er) { toast((er && er.message) || 'Could not join — try again'); }); return false; } } });
    }, function (er) { toast((er && er.message) || 'Could not open the invite link'); });
  }
  function openGroup(p) { if (live() && window.dxLive && window.dxLive.openGroup && p.group_id) { window.goto('groups'); setTimeout(function () { window.dxLive.openGroup(p.group_id); }, 400); } else if (window.dxGroups) window.dxGroups.open(p.name); }
  (function () { var n = 0, t = setInterval(function () { if (++n > 600 || !JOIN) return clearInterval(t); if (inApp()) { clearInterval(t); setTimeout(tryJoin, 600); } }, 100); })();
  window.dxTrustUI.join = function (tok) { JOIN = tok; tryJoin(); };

  /* a member asking to join: their trade card in Manage → Requests (W-10) */
  function paintRequestCards() {
    document.querySelectorAll('#tab-requests [data-uid]').forEach(function (row) {
      if (row.dataset.wtCard) return; row.dataset.wtCard = '1'; var uid = +row.dataset.uid;
      S().card(uid).then(function (c) { var p = c && c.profile, host = row.querySelector('.mod-content') || row; if (!host || row.querySelector('.wt-req-card')) return;
        host.insertAdjacentHTML('beforeend', '<div class="wt-req-card">' + (p ? '🏷 <span>' + esc(UI.roleName(p.role)) + '</span>' + (p.company ? ' · <span data-noi18n>' + esc(p.company) + '</span>' : '') + ' · <span>' + esc(p.governorate) + '</span>' +
          (p.sells ? ' · <span>Sells</span> <span data-noi18n>' + esc(p.sells) + '</span>' : '') + (p.buys ? ' · <span>Buys</span> <span data-noi18n>' + esc(p.buys) + '</span>' : '') : '🏷 <span>No trade profile yet</span>') +
          (c && c.new_account ? ' · <span class="wt-chip wt-new">🆕 New account</span>' : '') + '</div>');
        if (window.dxI18nAttrs) window.dxI18nAttrs(row); }, function () {});
    });
  }
  /* the partner badge on a group's card and header */
  function paintPartner() {
    document.querySelectorAll('#gx .gcard[data-partner="1"]').forEach(function (c) { var t = c.querySelector('.gcard-title'); if (t && !c.querySelector('.wt-partner-b')) t.insertAdjacentHTML('afterend', '<div class="wt-partner-b">🤝 Drugbox partner group</div>'); });
    var g = G(), hd = $('groupDetail'); if (g && g.card && g.card.dataset.partner === '1' && hd) { var h = hd.querySelector('.group-header-name, .gd-name, h1, h2'); if (h && !hd.querySelector('.wt-partner-h')) h.insertAdjacentHTML('afterend', '<div class="wt-partner-b wt-partner-h">🤝 Drugbox partner group</div>'); }
  }

  /* ══════════ 4. Messages: a new account is pointed out (W-20) ══════════ */
  var NEWACC = {};
  function paintNewAccount() {
    if (page() !== 'messages' || !window.dxMxOpenUid) return; var uid = window.dxMxOpenUid(); if (!uid || uid === me().id) return;
    var head = document.querySelector('#mx .chat-head, .chat-head'); if (!head) return;
    var box = head.parentNode.querySelector('.wt-newacc'); if (box && +box.dataset.uid === uid) return; if (box) box.remove();
    var go = function (c) { if (!c || !c.new_account || window.dxMxOpenUid() !== uid || head.parentNode.querySelector('.wt-newacc')) return; var d = Math.max(0, Math.floor((Date.now() - Date.parse(c.member_since)) / 864e5));
      head.insertAdjacentHTML('afterend', '<div class="wt-newacc" data-uid="' + uid + '" role="note">🆕 <span>' + (d === 0 ? 'New account — joined today.' : d === 1 ? 'New account — joined yesterday.' : 'New account — joined ' + d + ' days ago.') + '</span> <span>Check who you trade with before you pay or ship.</span></div>');
      if (window.dxI18nAttrs) window.dxI18nAttrs(head.parentNode); };
    if (NEWACC[uid] !== undefined) return go(NEWACC[uid]);
    S().card(uid).then(function (c) { NEWACC[uid] = c || null; go(c); }, function () {});
  }

  /* ══════════ 5. Admin → Review: Held for review, Trader reports, Partner groups ══════════ */
  var TOPIC_SHORT = { retail: 'Retail / patients / pharmacies', controlled: 'Controlled substances', import: 'Import for others', sham: 'Sham papers', invite: 'Invite link' };
  var KIND = { post: 'Post', offer: 'Marketplace offer', listing: 'Deal-room listing' };
  function docs(list, bucket) { return (list || []).map(function (d) { var p = typeof d === 'string' ? d : d.path, l = typeof d === 'string' ? d.split('/').pop() : d.label; return '<button type="button" class="dx-mod-doc" data-doc="' + esc(p) + '" data-bucket="' + esc(bucket || 'documents') + '">📄 <span data-noi18n>' + esc(l) + '</span></button>'; }).join(''); }
  window.dxModX = {
    queues: [['held', '🔎', 'Held for review'], ['traders', '⚖️', 'Trader reports'], ['partners', '🤝', 'Partner groups']],
    row: {
      held: function (x) { return ['<b data-noi18n>' + esc(x.author || 'A member') + '</b><span>' + esc(KIND[x.kind] || x.kind) + (x.group_name ? ' · <span data-noi18n>' + esc(x.group_name) + '</span>' : '') + ' · ' + (x.topics || []).map(function (t) { return esc(TOPIC_SHORT[t] || t); }).join(', ') + '</span><p data-noi18n>“' + esc(x.body || x.excerpt || '') + '”</p>',
        '<button class="dx-mod-ok" data-k="held" data-id="' + esc(x.id) + '" data-v="published">Publish</button><button class="dx-mod-no dx-mod-danger" data-k="held" data-id="' + esc(x.id) + '" data-v="removed">Remove</button>']; },
      traders: function (x) {
        var votes = (x.votes || []).map(function (v) { return '<span data-noi18n>' + esc(v.by) + '</span>: <span>' + (v.uphold ? 'uphold' : 'dismiss') + '</span>'; }).join(' · '), mine = (x.votes || []).some(function (v) { return v.mine; });
        return ['<b><span data-noi18n>' + esc(x.reporter_name || 'A member') + '</span> → <span data-noi18n>' + esc(x.reported_name || 'a member') + '</span></b><span>' + esc(UI.reasonName(x.reason)) + (x.deal_ref ? ' · <span data-noi18n>' + esc(x.deal_ref) + '</span>' : '') + '</span>' +
          '<p data-noi18n>“' + esc(x.details) + '”</p>' + docs(x.evidence) +
          (x.reply ? '<p class="dx-mod-reply"><span>The member replied:</span> <span data-noi18n>“' + esc(x.reply) + '”</span></p>' + docs(x.reply_evidence) : '<span>No reply yet — they can reply until</span> <span data-noi18n>' + esc(x.reply_by || '') + '</span>') +
          '<span>Two moderators decide.</span> ' + (votes ? '<span>Votes:</span> ' + votes : '<span>No votes yet.</span>'),
          !x.can_vote ? '<span class="dx-mod-pill">Waiting for the reply</span>' : mine ? '<span class="dx-mod-pill">You voted — a second moderator decides</span>' :
          '<button class="dx-mod-ok dx-mod-danger" data-k="traders" data-id="' + esc(x.id) + '" data-v="upheld">Uphold</button><button class="dx-mod-no" data-k="traders" data-id="' + esc(x.id) + '" data-v="dismissed">Dismiss</button>']; },
      partners: function (x) { return ['<b data-noi18n>' + esc(x.name) + '</b><span><span>Asked by</span> <span data-noi18n>' + esc(x.who || 'a group admin') + '</span> · ' + esc((x.member_count || 0) + ' members') + '</span><p data-noi18n>“' + esc(x.note) + '”</p>',
        '<button class="dx-mod-ok" data-k="partners" data-id="' + esc(x.id) + '" data-v="approved">Approve</button><button class="dx-mod-no" data-k="partners" data-id="' + esc(x.id) + '" data-v="rejected">Reject</button>']; }
    },
    ask: function (k, v, item, go, setNote) {
      if (k === 'held' && v === 'removed') { D.modal({ title: 'Remove it?', body: '<p>It is deleted and its author is told why.</p><div class="dbk-f"><label for="wtMn">Note for the author (optional)</label><textarea id="wtMn" maxlength="500"></textarea></div>',
        primary: { label: 'Remove', danger: true, onClick: function (bx) { setNote(bx.querySelector('#wtMn').value.trim()); go(); } } }); return true; }
      if (k === 'traders') { D.modal({ title: v === 'upheld' ? 'Uphold this report?' : 'Dismiss this report?', body: '<p>Your vote counts once. The report is decided when a second moderator votes the same way; both members are then told.</p><div class="dbk-f"><label for="wtMn">Your note (for the other moderators)</label><textarea id="wtMn" maxlength="500"></textarea></div>',
        primary: { label: v === 'upheld' ? 'Vote: uphold' : 'Vote: dismiss', danger: v === 'upheld', onClick: function (bx) { setNote(bx.querySelector('#wtMn').value.trim()); go(); } } }); return true; }
      if (k === 'partners' && v === 'rejected') { D.modal({ title: 'Reject this request?', body: '<div class="dbk-f"><label for="wtMn">Reason for the group’s admin *</label><textarea id="wtMn" data-req maxlength="500"></textarea></div>',
        primary: { label: 'Reject', danger: true, onClick: function (bx) { if (!D.requireFields(bx)) return false; setNote(bx.querySelector('#wtMn').value.trim()); go(); } } }); return true; }
      return false;
    }
  };
  /* the demo's side of these queues */
  if (window.dxModeration && !window.dxModeration.__wt) {
    var M = window.dxModeration, oLoad = M.load, oDecide = M.decide; M.__wt = true;
    M.load = function () { return oLoad.apply(M, arguments).then(function (d) {
      if (live()) return d;
      d.held = (D.store.get('wtHeld', []) || []).filter(function (h) { return h.status === 'held'; }).map(function (h) { return { id: h.id, kind: h.kind, author: me().name, topics: h.topics, body: h.excerpt }; });
      d.traders = (D.store.get('wtReports', []) || []).filter(function (r) { return r.status === 'open'; }).map(function (r) { return { id: r.id, reporter_name: me().name, reported_name: r.name, reason: r.reason, details: r.details, evidence: r.files.map(function (f) { return { path: 'demo', label: f }; }),
        reply: r.reply || '', reply_by: new Date(Date.parse(r.at) + 7 * 864e5).toISOString().slice(0, 10), can_vote: true, votes: (r.votes || []).map(function (v) { return { by: v.by, uphold: v.uphold, mine: true }; }) }; });
      var pa = D.store.get('wtPartner', {}) || {}; d.partners = Object.keys(pa).filter(function (k) { return pa[k].status === 'pending'; }).map(function (k) { return { id: k, name: pa[k].name, who: me().name, note: pa[k].note, member_count: 0 }; });
      return d; }); };
    M.decide = function (kind, id, value, note) {
      if (live() || ['held', 'traders', 'partners'].indexOf(kind) < 0) return oDecide.apply(M, arguments);
      if (kind === 'held') { var l = D.store.get('wtHeld', []) || []; l.forEach(function (h) { if (h.id === id) h.status = value; }); D.store.set('wtHeld', l);
        var h = l.filter(function (x) { return x.id === id; })[0]; if (h && h.kind === 'post') (window.POSTS || []).forEach(function (p) { if (p.id === h.item) { if (value === 'published') delete p.wtHeld; else p.del = true; } });
        if (h && h.kind === 'post' && value === 'removed' && window.POSTS) { var i = window.POSTS.findIndex(function (p) { return p.id === h.item; }); if (i >= 0) window.POSTS.splice(i, 1); }
        return oDecide.call(M, 'held', id, value, note); }
      if (kind === 'traders') { var r = D.store.get('wtReports', []) || []; r.forEach(function (x) { if (x.id === id) { x.votes = x.votes || []; x.votes.push({ by: me().name, uphold: value === 'upheld' }); } }); D.store.set('wtReports', r);
        toast('Your vote is saved — a second moderator decides'); return Promise.resolve(true); }
      if (kind === 'partners') { var pa = D.store.get('wtPartner', {}) || {}; if (pa[id]) pa[id].status = value; D.store.set('wtPartner', pa); return oDecide.call(M, 'partners', id, value, note); }
    };
  }

  /* ══════════ after every page draw ══════════ */
  C.onRender('wtrust', function () {
    var p = page();
    if (p === 'market') { addAsFields(); if (!live()) demoCards(); }
    if (p === 'feed' || p === 'market' || p === 'groups' || p === 'profile') markHeld();
    if (p === 'messages') paintNewAccount();
    if (p === 'groups') { paintTools(); manageTabs(); paintRequestCards(); paintPartner(); }
  });
  /* the inside of a group, the market's tabs and the chat are redrawn without a page change: watched */
  var MO = new MutationObserver(function () {
    if (MO.busy) return; MO.busy = true;
    requestAnimationFrame(function () { MO.busy = false; var p = page();
      if (p === 'groups') { paintTools(); manageTabs(); paintRequestCards(); paintPartner(); markHeld(); }
      if (p === 'messages') paintNewAccount();
      if (p === 'market') { addAsFields(); if (!live()) demoCards(); }
    });
  });
  function watch() { var gd = $('groupDetail'), ct = $('content'); if (gd && !gd.__wt) { gd.__wt = 1; MO.observe(gd, { childList: true, subtree: true }); } if (ct && !ct.__wt) { ct.__wt = 1; MO.observe(ct, { childList: true, subtree: true }); } }
  C.onRender('wtrust-watch', watch); setTimeout(watch, 500);
})();
