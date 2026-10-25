/* Drugbox live — area w-trust (trust, safety and groups). Loaded after adapter.js (web/build/live.py); replaces the demo service
   of web/src/wtrust.js (window.dxTrust) with the database (migrations 0090–0094) and fills the hooks the adapter calls:
   dxTradeAs / dxTradeAfter (a listing: who posts it), dxPostSaved (a post held or waiting), dxGroupCardHook (a group's admin
   tools and partner badge), dxNotifHook (the sentences of the new notices). */
(function () {
  var L = window.dxLive; if (!L || !L.k || !L.sb || !L.wt) return;
  var sb = L.sb, K = L.k, W = L.wt;
  function me() { return K.me; }
  function toast(m) { if (typeof window.toast === 'function') window.toast(m); }
  function err(r) { if (r.error) throw new Error(W.friendly(r.error)); return r.data; }
  function uuid(id) { if (id == null) return null; if (window.ME && id === window.ME.id) return me(); return W.uuidOf(+id) || null; }
  function esc2(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function gidOf(g) { if (!g) return null; if (g.gid) return +g.gid; var m = /^g(\d+)$/.exec(g.key || ''); if (m) return +m[1]; return g.card && g.card.dataset.gid ? +g.card.dataset.gid : null; }
  function cardOf(g) { var id = gidOf(g); return (g && g.card && g.card.isConnected && g.card) || (id && document.querySelector('#gx .gcard[data-gid="' + id + '"]')) || null; }
  function rulesOf(t) { return String(t || '').split(/\n+/).map(function (l) { return l.trim(); }).filter(Boolean).slice(0, 20).map(function (l) { var m = /^(.{1,80}?)\s*(?:—|:|–)\s+(.+)$/.exec(l); return m ? [m[1], m[2]] : [l, '']; }); }
  async function up(folder, file) { var path = folder + '/' + me() + '/' + W.rid() + '.' + W.extOf(file); await W.upDoc('documents', path, file); return path; }

  /* ===== AREA w-trust: the service ===== */
  var CARD = {}, TP = { at: 0, v: undefined }, ACC = {}, PARTNER = {};
  W.onReset(function () { CARD = {}; TP = { at: 0, v: undefined }; ACC = {}; PARTNER = {}; INFO = {}; });
  var svc = {
    live: true,
    card: async function (id) { var u = uuid(id); if (!u) return null; var c = CARD[u]; if (c && Date.now() - c.at < 30000) return c.v;
      var v = err(await sb.rpc('trade_card', { p_user: u })); CARD[u] = { at: Date.now(), v: v }; return v; },
    myProfile: async function () { if (TP.v !== undefined && Date.now() - TP.at < 60000) return TP.v;
      var r = err(await sb.from('trade_profiles').select('role, company, governorate, sells, buys').eq('user_id', me()).maybeSingle()); TP = { at: Date.now(), v: r || null }; return TP.v; },
    saveProfile: async function (p) { var row = { user_id: me(), role: p.role, company: p.company || null, governorate: p.governorate, sells: p.sells || null, buys: p.buys || null };
      err(await sb.from('trade_profiles').upsert(row, { onConflict: 'user_id' }).select('user_id').single()); TP = { at: Date.now(), v: row }; delete CARD[me()]; return row; },
    phoneStart: async function (ph) { return err(await sb.rpc('phone_verify_start', { p_phone: ph })); },
    phoneConfirm: async function (code) { var r = err(await sb.rpc('phone_verify_confirm', { p_code: code })); delete CARD[me()]; if (window.ME && r && r.phone) window.ME.phone = r.phone; return r; },
    report: async function (id, reason, details, files) { var u = uuid(id); if (!u) throw new Error('Open the member’s profile again and retry');
      var paths = []; for (var i = 0; i < files.length; i++) paths.push(await up('trader-reports', files[i]));
      return err(await sb.rpc('trader_report', { p_user: u, p_reason: reason, p_details: details, p_evidence: paths, p_deal_ref: null })); },
    myReports: async function () { return err(await sb.rpc('my_trader_reports')) || []; },
    reply: async function (id, text, files) { var paths = []; for (var i = 0; i < (files || []).length; i++) paths.push(await up('trader-reports', files[i]));
      err(await sb.rpc('trader_report_reply', { p_report: +id, p_reply: text, p_evidence: paths })); },
    myHeld: async function () {
      var a = await Promise.all([sb.from('content_holds').select('kind, item_id, topics').eq('user_id', me()).eq('status', 'held').limit(100),
                                 sb.from('posts').select('id').eq('user_id', me()).eq('group_pending', true).limit(100)]);
      return (a[0].data || []).map(function (h) { return { kind: h.kind, item: h.item_id, topics: h.topics }; }).concat((a[1].data || []).map(function (p) { return { kind: 'pending', item: p.id }; })); },
    rateBuyer: async function (ref, stars, note) { err(await sb.rpc('deal_rate_buyer', { p_ref: ref, p_stars: stars, p_note: note || null })); },
    buyerRated: async function (ref) { var r = await sb.from('deal_ratings').select('stars, deals!inner(ref)').eq('deals.ref', ref).maybeSingle(); return r.data ? r.data.stars : null; },
    buyerRating: async function (from) { var raw = from.slug && W.CO.raw[from.slug]; if (!raw || !raw.id) return null; return err(await sb.rpc('buyer_rating', { p_company: raw.id, p_user: null })); },
    /* groups */
    tools: function (g) { var c = cardOf(g), t = {}; try { t = c && c.dataset.wt ? JSON.parse(c.dataset.wt) : {}; } catch (x) {}
      return Object.assign({ rules_required: false, daily_post_limit: null, slow_mode_minutes: null, block_duplicates: true, block_links: false, review_posts: false, require_category: false }, t); },
    saveTools: async function (g, t) { var id = gidOf(g); if (!id) throw new Error('Open the group again and retry');
      err(await sb.from('groups').update(t).eq('id', id).select('id').single()); var c = cardOf(g); if (c) c.dataset.wt = JSON.stringify(t); },
    accepted: function (g) { return !!ACC[gidOf(g)]; },
    acceptRules: async function (g) { var id = gidOf(g); err(await sb.rpc('group_accept_rules', { p_group: id })); ACC[id] = true; },
    links: async function (g) { var id = gidOf(g);
      var a = await Promise.all([sb.from('group_invite_links').select('id, token, uses, max_uses, expires_at, revoked_at, created_at').eq('group_id', id).order('created_at', { ascending: false }).limit(20),
                                 sb.from('group_partner_requests').select('status').eq('group_id', id).maybeSingle()]);
      PARTNER[id] = (a[1] && a[1].data) || null; var c = cardOf(g); if (c && c.dataset.partner === '1') PARTNER[id] = { status: 'approved' };
      return err(a[0]) || []; },
    makeLink: async function (g, days, max) { return err(await sb.rpc('group_link_create', { p_group: gidOf(g), p_days: days || null, p_max: max || null })); },
    stopLink: async function (g, id) { err(await sb.rpc('group_link_revoke', { p_link: +id })); },
    preview: async function (tok) { var p = err(await sb.rpc('group_link_preview', { p_token: tok })); if (!p) return null; p.rules = rulesOf(p.rules); return p; },
    joinByLink: async function (tok, ok) { var r = err(await sb.rpc('group_join_by_link', { p_token: tok, p_accept_rules: !!ok })); try { W.GX.at = 0; await W.loadGroups(); } catch (x) {} return r; },
    pending: async function (g) { var l = err(await sb.rpc('group_pending_posts', { p_group: gidOf(g) })) || []; return l.map(function (p) { return { id: p.id, body: p.body, author: p.author, at: p.created_at }; }); },
    publish: async function (g, id, yes) { return err(await sb.rpc('group_publish_post', { p_post: +id, p_publish: !!yes })); },
    partnerAsk: async function (g, note) { err(await sb.rpc('group_partner_request', { p_group: gidOf(g), p_note: note })); PARTNER[gidOf(g)] = { status: 'pending' }; },
    partnerOf: function (g) { return PARTNER[gidOf(g)] || null; },
    openAuth: async function (id) { var r = err(await sb.from('products').select('broker_auth_path').eq('id', +id).maybeSingle()); if (!r || !r.broker_auth_path) return null;
      var u = await sb.storage.from('documents').createSignedUrl(r.broker_auth_path, 300); return u.error ? null : u.data.signedUrl; }
  };
  window.dxTrust = svc;

  /* ===== AREA w-trust: a listing — who posts it (0090) ===== */
  window.dxTradeAs = async function (d, row) {
    var o = window.__wtAs; window.__wtAs = null; if (!o) return {};
    if (o.as === 'company') { var r = W.CO.raw[o.slug]; if (!r || !r.id || !W.CO.roles[r.id]) throw new Error('Choose a company page you belong to');
      return { company_id: r.id, posted_as: 'company' }; }
    if (o.as === 'broker') { var path = await up('listings', o.file);
      return { company_id: null, posted_as: 'broker', broker_for: o.broker_for, broker_commission: +o.commission, broker_auth_path: path }; }
    return { company_id: null, posted_as: 'individual' };
  };
  window.dxTradeAfter = function (data) {
    if (!data || !data.review_hold) return;
    setTimeout(function () { toast('Your offer is waiting for Drugbox review — you are told when it is checked. Only you can see it until then.'); if (window.dxTrustUI) window.dxTrustUI.heldChanged(); }, 900);
  };
  window.dxPostSaved = function (row) {
    if (!row || !(row.review_hold || row.group_pending)) return;
    setTimeout(function () { toast(row.review_hold ? 'Your post is waiting for Drugbox review — only you can see it until it is checked.' : 'Sent to the group’s admins — it shows once they publish it');
      if (window.dxTrustUI) window.dxTrustUI.heldChanged(); }, 900);
  };

  /* ===== AREA w-trust: offer cards say who posts them ===== */
  var INFO = {}, ASKING = {};
  function paintCards() {
    var cards = [].slice.call(document.querySelectorAll('#mkx [data-live^="p"]')), need = [];
    cards.forEach(function (c) { var id = +c.dataset.live.slice(1); if (INFO[id]) { if (c.dataset.wtAs !== INFO[id].as) window.dxTrustUI.badge(c, INFO[id]); } else if (!ASKING[id]) need.push(id); });
    if (!need.length) return; need.forEach(function (id) { ASKING[id] = 1; });
    sb.from('products').select('id, posted_as, broker_for, broker_commission, review_hold').in('id', need.slice(0, 200)).then(function (r) {
      need.forEach(function (id) { delete ASKING[id]; }); (r.data || []).forEach(function (x) { INFO[x.id] = { as: x.posted_as || 'individual', broker_for: x.broker_for, commission: x.broker_commission, held: x.review_hold, id: x.posted_as === 'broker' ? x.id : null }; });
      paintCards();
    });
  }
  /* deal-room listings (group_listings) */
  var LINFO = {}, LASK = {};
  function paintRoom() {
    var cards = [].slice.call(document.querySelectorAll('#gpBox [data-lid]')), need = [];
    cards.forEach(function (c) { var id = +c.dataset.lid; if (!id) return; if (LINFO[id]) { if (c.dataset.wtAs !== LINFO[id].as) window.dxTrustUI.badge(c, LINFO[id]); } else if (!LASK[id]) need.push(id); });
    if (!need.length) return; need.forEach(function (id) { LASK[id] = 1; });
    sb.from('group_listings').select('id, posted_as, broker_for, broker_commission').in('id', need.slice(0, 100)).then(function (r) {
      need.forEach(function (id) { delete LASK[id]; }); (r.data || []).forEach(function (x) { LINFO[x.id] = { as: x.posted_as || 'individual', broker_for: x.broker_for, commission: x.broker_commission }; }); paintRoom(); });
  }
  W.onReset(function () { LINFO = {}; });
  var MO = new MutationObserver(function () { if (MO.t) return; MO.t = setTimeout(function () { MO.t = 0; if (document.querySelector('#mkx [data-live^="p"]')) paintCards(); if (document.querySelector('#gpBox [data-lid]')) paintRoom(); }, 120); });
  (function watch() { var c = document.getElementById('content'), g = document.getElementById('groupDetail'); if (c) MO.observe(c, { childList: true, subtree: true }); if (g) MO.observe(g, { childList: true, subtree: true }); if (!c || !g) setTimeout(watch, 300); })();

  /* ===== AREA w-trust: a group's card carries its admin tools and the partner badge (0094) ===== */
  window.dxGroupCardHook = function (c, g) {
    c.dataset.wt = JSON.stringify({ rules_required: !!g.rules_required, daily_post_limit: g.daily_post_limit || null, slow_mode_minutes: g.slow_mode_minutes || null, block_duplicates: g.block_duplicates !== false,
      block_links: !!g.block_links, review_posts: !!g.review_posts, require_category: !!g.require_category });
    if (g.partner_at) c.dataset.partner = '1'; else delete c.dataset.partner;
  };

  /* ===== AREA w-trust: Admin → Review — Held for review, Trader reports, Partner groups ===== */
  (function () {
    var M = window.dxModeration; if (!M || M.__wtLive) return; M.__wtLive = true;
    var oLoad = M.load, oDecide = M.decide;
    M.load = function () { return oLoad.apply(M, arguments).then(async function (d) {
      var a = await Promise.all([sb.rpc('held_review_queue', { p_limit: 100 }), sb.rpc('trader_reports_queue', { p_limit: 100 }), sb.rpc('group_partner_queue')]);
      d.held = ((a[0] && a[0].data) || []).map(function (x) { return { id: x.id, kind: x.kind, author: x.author, topics: x.topics, body: x.body || x.excerpt, group_name: x.group_name }; });
      d.traders = ((a[1] && a[1].data) || []).map(function (x) { x.evidence = (x.evidence || []).map(function (p) { return { path: p, label: p.split('/').pop() }; });
        x.reply_evidence = (x.reply_evidence || []).map(function (p) { return { path: p, label: p.split('/').pop() }; }); return x; });
      d.partners = ((a[2] && a[2].data) || []).map(function (x) { return { id: x.group_id, name: x.name, who: x.who, note: x.note, member_count: x.member_count }; });
      return d; }); };
    M.decide = async function (kind, id, value, note) {
      if (kind === 'held') return err(await sb.rpc('held_review_decide', { p_hold: +id, p_publish: value === 'published', p_note: note || null }));
      if (kind === 'traders') { var out = err(await sb.rpc('trader_report_vote', { p_report: +id, p_uphold: value === 'upheld', p_note: note || null }));
        if (out === 'voted') toast('Your vote is saved — a second moderator decides'); return out; }
      if (kind === 'partners') return err(await sb.rpc('group_partner_decide', { p_group: +id, p_ok: value === 'approved', p_note: note || null }));
      return oDecide.apply(M, arguments);
    };
    var oDecided = M.decided;
    if (oDecided) M.decided = function () { return oDecided.apply(M, arguments).then(function (l) { (l || []).forEach(function (x) { if (x.kind === 'held' || x.kind === 'trader_report' || x.kind === 'partner') x.undo = false; }); return l; }); };
  })();

  /* ===== AREA w-trust: the sentences of the new notices (written here in English; the Arabic interface translates them) ===== */
  var WHY = { retail: 'a sale to patients, pharmacies or the public (Drugbox is business-to-business)', controlled: 'controlled substances', import: 'importing for others', sham: 'sham or forged papers', invite: 'an invite link to an outside group' };
  var WHAT = { post: 'post', offer: 'offer', listing: 'deal-room listing' };
  var REASON = { non_payment: 'did not pay', non_delivery: 'did not deliver', counterfeit: 'counterfeit or not as agreed', misrepresentation: 'not who they said they were', sham_papers: 'sham or forged papers', other: 'something else' };
  window.dxNotifHook = function (n, o, SYS) {
    var d = n.data && typeof n.data === 'object' ? n.data : {}, t = null, icon = null;
    if (n.type === 'auto_review') { t = 'Drugbox is checking your ' + (WHAT[d.kind] || 'post') + ' before it shows — it looks like ' + (d.topics || []).map(function (x) { return WHY[x] || x; }).join(', ') + ': “' + String(d.excerpt || '') + '”. Only you can see it until then.'; icon = '🔎'; }
    else if (n.type === 'auto_review_decided') { t = d.outcome === 'published' ? 'Drugbox checked your ' + (WHAT[d.kind] || 'post') + ' “' + String(d.excerpt || '') + '” — it now shows to everyone.'
      : 'Drugbox removed your ' + (WHAT[d.kind] || 'post') + ' “' + String(d.excerpt || '') + '”' + (d.note ? ' — reason: ' + String(d.note) : ' — it is outside what Drugbox trades.'); icon = d.outcome === 'published' ? '✅' : '🗑'; }
    else if (n.type === 'trader_report') { t = 'A member reported a problem in a trade with you (' + (REASON[d.reason] || 'other') + '). Reply with your side by ' + String(d.reply_by || '') + ' — open My trade reports on your profile. Two Drugbox moderators decide.'; icon = '⚖️'; }
    else if (n.type === 'trader_report_reply') { t = 'The member you reported replied with their side — Drugbox moderators read both.'; icon = '⚖️'; }
    else if (n.type === 'trader_report_decided') { t = d.side === 'reported' ? (d.outcome === 'upheld' ? 'Drugbox upheld a report about a trade with you — it now counts on your trade card.' : 'Drugbox dismissed a report about a trade with you — nothing changes on your profile.')
      : (d.outcome === 'upheld' ? 'Drugbox upheld your report — it now counts on the trader’s card.' : 'Drugbox checked your report and dismissed it.'); icon = '⚖️'; }
    else if (n.type === 'group_partner_decided') { t = d.outcome === 'approved' ? 'Drugbox marked “' + String(d.group || '') + '” as a Drugbox partner group.' : 'Drugbox could not mark “' + String(d.group || '') + '” as a partner group' + (d.note ? ' — ' + String(d.note) : '') + '.'; icon = '🤝'; }
    else if (n.type === 'deal_rated_buyer') { o.text = '<b>' + esc2((o.text.match(/<b>(.*?)<\/b>/) || [, 'The supplier'])[1]) + '</b> ' + esc2('rated you as a buyer: ' + (d.stars || '') + '/5 for “' + String(d.title || '') + '”'); o.icon = '★'; return o; }
    if (t == null) return o;
    o.text = esc2(t); o.uid = SYS; o.icon = icon || o.icon; o.wtType = n.type; return o;
  };
  /* a trader-report notice opens My trade reports */
  var oRead = window.markNotifRead;
  if (typeof oRead === 'function') window.markNotifRead = function (id) {
    var r = oRead.apply(this, arguments), n = (window.NOTIFS || []).filter(function (x) { return x.id === id; })[0];
    if (n && /^trader_report/.test(n.wtType || n.rawType || '') && window.dxTrustUI) setTimeout(function () { window.dxTrustUI.myReports(); }, 50);
    return r;
  };
})();
