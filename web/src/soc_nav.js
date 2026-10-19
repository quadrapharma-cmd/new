/* Finding and getting around (area social): addresses for pages (#/profile/<id>, #/network, #/messages/<thread>, #/settings…)
   that survive a reload, Back/Forward and sharing; one search for people, companies, products, jobs, groups and posts (top bar,
   Enter, ↑/↓ to choose) and the same in Ctrl+K; Ctrl+K "New post" and "Settings"; one Saved page (posts, jobs, listings);
   every notification opens what it is about.
   Data goes through window.dxSearchSvc: the sample data here, the database in the live app (web/src/live/social.js). */
(function () {
  var D = window.DBK; if (!D || typeof window.goto !== 'function') return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function toast(m) { (window.toast || D.toast)(m); }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function page() { return document.body.getAttribute('data-page') || ''; }
  function inApp() { var a = document.getElementById('app'); return !!a && a.getClientRects().length > 0; }
  function later(fn, ms) { setTimeout(fn, ms || 0); }
  function flash(sel, text) {             /* scroll to the card that names text and mark it (the jobs, groups and listings pages) */
    var t0 = Date.now();
    (function look() {
      var el = [].filter.call(document.querySelectorAll(sel), function (e) { return e.getClientRects().length && txt(e).toLowerCase().indexOf(String(text).toLowerCase()) >= 0; })[0];
      if (!el) { if (Date.now() - t0 < 4000) setTimeout(look, 150); return; }
      el.scrollIntoView({ block: 'center' }); el.classList.remove('dx-post-hit'); void el.offsetWidth; el.classList.add('dx-post-hit');
    })();
  }

  /* ═════ A. addresses (S-21) ═════ */
  var NAV = false, PEND = null, last = { page: null, args: [] };
  function idOf(a) { var L = window.dxLive; return L && L.uuidOf && L.uuidOf(+a) ? L.uuidOf(+a) : String(a); }
  function localOf(x) { var L = window.dxLive; if (/^[0-9a-f-]{36}$/i.test(x) && L && L.aid) return L.aid(x); return parseInt(x, 10); }
  function routeOf(p, args) {
    if (!p) return null;
    if (p === 'profile') { var me = window.ME || {}; return args[0] != null && +args[0] !== me.id ? '#/profile/' + idOf(args[0]) : '#/profile'; }
    if (p === 'tag' && args[0]) return '#/tag/' + encodeURIComponent(String(args[0]).replace(/^#/, '').toLowerCase());
    if (p === 'search' && args[0]) return '#/search/' + encodeURIComponent(args[0]);
    return /^[a-z][a-z0-9-]*$/.test(p) ? '#/' + p : null;
  }
  function record(p, args) {
    if (NAV || !inApp()) return; last = { page: p, args: args || [] };
    var h = routeOf(p, last.args); if (!h) return;
    var url = location.pathname + location.search + h;
    try { if (location.hash === h) history.replaceState({ dx: 1 }, '', url); else if (history.state && history.state.dx) history.pushState({ dx: 1 }, '', url); else history.replaceState({ dx: 1 }, '', url); } catch (e) {}
  }
  function parse(h) {
    var m = /^#\/([a-z][a-z0-9-]*)(?:\/([^?#]*))?$/.exec(h || ''); if (!m) return null;
    return { page: m[1], arg: m[2] ? decodeURIComponent(m[2]) : '' };
  }
  function open(r) {
    if (!r) return false;
    NAV = true;
    try {
      if (r.page === 'post') return false;                          /* a post link is opened by the feed (feedacts) */
      if (r.page === 'privacy' || r.page === 'terms') { if (window.dxLegal) window.dxLegal.open(r.page); return true; }
      if (r.page === 'profile') { if (r.arg) window.gotoProfile(localOf(r.arg)); else window.goto('profile'); return true; }
      if (r.page === 'search') { window.doSearch(r.arg); return true; }
      if (r.page === 'messages') { window.goto('messages'); if (r.arg) openThread(r.arg); return true; }
      if (r.page === 'tag') { window.goto('tag', r.arg); return true; }
      if (document.getElementById('tnb-' + r.page) || (window.dxSocialPages && window.dxSocialPages[r.page]) || /^(feed|network|messages|notifs|saved|market|companies|groups|jobs|training|admin|settings)$/.test(r.page)) { window.goto(r.page); return true; }
      return false;
    } finally { NAV = false; }
  }
  function openThread(key) {
    var t0 = Date.now(), k = /^[0-9a-f-]{36}$/i.test(key) ? 'u' + localOf(key) : key;
    (function look() {
      var el = document.querySelector('.mx-thread[data-person="' + k.replace(/"/g, '') + '"]');
      if (el) { if (window.jumpToThread) window.jumpToThread(k); else el.click(); return; }
      if (Date.now() - t0 < 6000 && page() === 'messages') setTimeout(look, 200);
    })();
  }
  var gotoNav = window.goto;
  window.goto = function (p) { var args = [].slice.call(arguments, 1), r = gotoNav.apply(this, arguments); record(p, args); return r; };
  var gpNav = window.gotoProfile;
  if (gpNav) window.gotoProfile = function (uid) { var r = gpNav.apply(this, arguments); record('profile', [uid]); return r; };
  var oSearch0 = window.doSearch;
  /* a thread opened in Messages is part of the address (reload opens it again) */
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.mx-thread[data-person]'); if (!t || page() !== 'messages') return;
    later(function () { var key = t.dataset.person, L = window.dxLive, m = /^u(\d+)$/.exec(key), id = m && L && L.uuidOf ? L.uuidOf(+m[1]) : null;
      try { history.replaceState({ dx: 1 }, '', location.pathname + location.search + '#/messages/' + encodeURIComponent(id || key)); } catch (x) {} }, 0);
  });
  window.addEventListener('popstate', function () {
    var r = parse(location.hash); if (!r || !inApp()) return;
    open(r);
  });
  /* an address opened before signing in (a shared link, a reload) is opened once the member is in */
  var first = parse(location.hash);
  if (first && first.page !== 'post') PEND = first;
  if (first && (first.page === 'privacy' || first.page === 'terms')) later(function () { if (window.dxLegal) window.dxLegal.open(first.page); }, 300);
  document.addEventListener('dx:page', function () {
    if (!PEND || !inApp()) return; var r = PEND; PEND = null;
    if (r.page === 'privacy' || r.page === 'terms') return;
    later(function () { if (!open(r)) record(page(), []); }, 80);
  });
  window.dxRoute = { open: function (h) { return open(parse(h)); }, pending: function () { return PEND; } };

  /* ═════ B. one search (S-18) ═════ */
  function demoSearch(q) {
    var lq = q.toLowerCase(), words = lq.split(/\s+/).filter(Boolean), out = [];
    function hit(s) { s = String(s || '').toLowerCase(); return words.every(function (w) { return s.indexOf(w) >= 0; }); }
    var me = window.ME || {};
    (window.USERS || []).forEach(function (u) { if (u.id !== me.id && hit(u.name + ' ' + (u.company || '') + ' ' + (u.headline || ''))) out.push({ g: 'people', u: u, t: u.name, s: [(u.headline || '').split('|')[0].trim(), u.company].filter(Boolean).join(' · '), go: function () { window.gotoProfile(u.id); } }); });
    var MAP = { 'Companies': 'companies', 'Products': 'products', 'Listings': 'products', 'Buying requests': 'products', 'Jobs': 'jobs', 'Groups': 'groups', 'Posts': 'posts' };
    var EMO = { companies: '🏢', products: '📦', jobs: '💼', groups: '👥', posts: '📝' };
    (window.dxCmdSearch ? window.dxCmdSearch(q) : []).forEach(function (x) { var g = MAP[x.g]; if (g) out.push({ g: g, e: EMO[g], t: x.t, s: x.s, go: x.go }); });
    (window.PRODUCTS || []).forEach(function (p) { if (hit(p.name + ' ' + (p.desc || '')) && !out.some(function (o) { return o.g === 'products' && o.t === p.name; })) out.push({ g: 'products', e: p.emoji || '📦', t: p.name, s: ((window.U(p.uid) || {}).company || '') + ' · ' + p.price + '/' + p.unit, go: function () { window.goto('market'); var si = document.getElementById('searchIn'); if (si) si.value = p.name; if (window.__mkxFilter) window.__mkxFilter(p.name); } }); });
    return Promise.resolve(out);
  }
  window.dxSearchSvc = window.dxSearchSvc || { live: false, find: demoSearch };
  var GROUPS = [['people', '👥 People'], ['companies', '🏢 Companies'], ['products', '📦 Products & listings'], ['jobs', '💼 Jobs'], ['groups', '👥 Groups'], ['posts', '📝 Posts']];
  var RES = { q: '', list: [], sel: -1, seq: 0 };
  function rowHtml(x, i) {
    var lead = x.u ? window.av(x.u, 42) : '<div class="dx-sres-e" aria-hidden="true">' + esc(x.e || '🔎') + '</div>';
    var act = x.g === 'people' && window.CONN_STATE && window.CONN_STATE[x.u.id] !== 'connected' && window.CONN_STATE[x.u.id] !== 'pending'
      ? '<button class="btn-o" style="font-size:12px;padding:5px 14px;flex:none" data-sr-connect="' + x.u.id + '">Connect</button>' : '';
    return '<div class="search-user dx-sres" role="option" aria-selected="false" id="dxSr' + i + '" data-sr="' + i + '" tabindex="-1" style="cursor:pointer">' + lead +
      '<div style="flex:1;min-width:0"><div style="font-size:14px;font-weight:700;color:var(--cx)" data-noi18n>' + esc(x.t) + (x.u && x.u.verified ? ' ✓' : '') + '</div>' +
      (x.s ? '<div style="font-size:12px;color:#65676b" data-noi18n>' + esc(x.s) + '</div>' : '') + '</div>' + act + '</div>';
  }
  function paint(q, list) {
    var c = document.getElementById('content'); if (!c) return;
    RES.list = []; var html = '';
    GROUPS.forEach(function (g) {
      var xs = list.filter(function (x) { return x.g === g[0]; }); if (!xs.length) return;
      html += '<div class="search-section"><div class="search-section-title">' + g[1] + ' (' + xs.length + ')</div>' + xs.map(function (x) { RES.list.push(x); return rowHtml(x, RES.list.length - 1); }).join('') + '</div>';
    });
    RES.sel = -1;
    c.innerHTML = '<div class="search-wrap"><div style="font-size:18px;font-weight:800;color:var(--cx);margin-bottom:16px">Results for "<em data-noi18n>' + esc(q) + '</em>"</div>' +
      (RES.list.length ? '<div role="listbox" aria-label="Search results" id="dxSrList">' + html + '</div>'
        : '<div style="text-align:center;padding:60px;color:#65676b"><div style="font-size:48px;margin-bottom:12px">🔍</div><div style="font-size:18px;font-weight:700">No results for "<span data-noi18n>' + esc(q) + '</span>"</div><div style="font-size:13px;margin-top:6px">Try a product, a company or a person — or fewer words.</div></div>') + '</div>';
  }
  function choose(i) { var x = RES.list[i]; if (!x) return; try { x.go(); } catch (e) { if (window.console) console.warn(e); } }
  function mark(i) {
    var rows = document.querySelectorAll('#dxSrList .dx-sres'); if (!rows.length) return;
    RES.sel = Math.max(0, Math.min(rows.length - 1, i));
    rows.forEach(function (r, k) { var on = k === RES.sel; r.setAttribute('aria-selected', on ? 'true' : 'false'); r.classList.toggle('dx-kb-active', on); });
    var si = document.getElementById('searchIn'); if (si) si.setAttribute('aria-activedescendant', 'dxSr' + RES.sel);
    rows[RES.sel].scrollIntoView({ block: 'nearest' });
  }
  window.doSearch = function (q) {
    if (!q || !String(q).trim()) return;
    q = String(q).trim().slice(0, 80);
    var c = document.getElementById('content'); if (!c) return oSearch0 && oSearch0(q);
    window.curPage = 'search'; if (window.buildSidebarNav) window.buildSidebarNav();
    var si = document.getElementById('searchIn'); if (si) si.value = q;
    document.body.setAttribute('data-page', 'search');
    var seq = ++RES.seq; RES.q = q;
    paint(q, []); c.querySelector('.search-wrap').insertAdjacentHTML('beforeend', '<div class="dx-sres-wait" style="padding:24px;color:#65676b">Searching…</div>');
    record('search', [q]);
    Promise.resolve(window.dxSearchSvc.find(q)).then(function (list) { if (seq !== RES.seq || page() !== 'search') return; paint(q, list || []); },
      function (e) { if (seq !== RES.seq) return; paint(q, []); toast((e && e.message) || 'Search is not available right now — try again'); });
  };
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-sr-connect]'); if (b) { e.stopPropagation(); window.connect(+b.dataset.srConnect); b.textContent = 'Pending'; b.disabled = true; return; }
    var r = e.target.closest && e.target.closest('#dxSrList .dx-sres'); if (r) choose(+r.dataset.sr);
  });
  /* ↑/↓ in the top search choose a result; Enter opens the chosen one (otherwise it searches) */
  document.addEventListener('keydown', function (e) {
    if (!e.target || e.target.id !== 'searchIn' || page() !== 'search') return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { if (!RES.list.length) return; e.preventDefault(); mark(RES.sel < 0 ? 0 : RES.sel + (e.key === 'ArrowDown' ? 1 : -1)); }
    else if (e.key === 'Enter' && RES.sel >= 0 && e.target.value.trim() === RES.q) { e.preventDefault(); e.stopPropagation(); choose(RES.sel); }
  }, true);
  document.addEventListener('input', function (e) { if (e.target && e.target.id === 'searchIn' && RES.sel >= 0) { RES.sel = -1; document.querySelectorAll('#dxSrList .dx-kb-active').forEach(function (r) { r.classList.remove('dx-kb-active'); r.setAttribute('aria-selected', 'false'); }); } });

  /* ═════ C. Ctrl+K: "New post", "Settings", and (live) the database's results ═════ */
  window.dxCmdFilter = function (idx) {
    var out = window.dxSearchSvc.live ? idx.filter(function (x) { return x.g === 'Pages' || x.g === 'Actions' || x.g === 'Saved searches'; }) : idx.slice();
    var at = 0; while (at < out.length && out[at].g === 'Pages') at++;
    out.splice(at, 0, { g: 'Pages', t: 'Settings', s: 'Go to Settings', ic: 'user', go: function () { window.goto('settings'); } });
    out.splice(at + 1, 0, { g: 'Actions', t: 'New post', s: 'Write a post', ic: 'plus', go: function () { if (page() !== 'feed') window.goto('feed'); later(function () { window.showPostModal && window.showPostModal(); }, 60); } });
    return out;
  };

  /* ═════ D. one Saved place: posts, jobs, listings (J-SOCIAL-48) ═════ */
  window.dxSavedSvc = window.dxSavedSvc || {
    live: false,
    jobs: function () { var l = D.store.get('savedJobs', null); if (l == null) l = sampleJob();   /* the sample starts with one saved job */
      return Promise.resolve((l || []).map(function (t) { return { id: t, title: jobTitle(t), sub: '' }; })); },
    unsaveJob: function (j) { var l = D.store.get('savedJobs', null); if (l == null) l = sampleJob(); D.store.set('savedJobs', (l || []).filter(function (t) { return t !== j.id; })); return Promise.resolve(); },
    openJob: function (j) { window.goto('jobs'); flash('#jx .jcard', j.title); },
    listings: function () { return Promise.resolve((D.store.get('saved', []) || []).map(function (k) { var i = String(k).indexOf(':'); return { id: k, title: i >= 0 ? k.slice(i + 1) : k, sub: '' }; })); },
    unsaveListing: function (l) { D.store.set('saved', (D.store.get('saved', []) || []).filter(function (k) { return k !== l.id; })); return Promise.resolve(); },
    openListing: function (l) { window.goto('market'); var si = document.getElementById('searchIn'); var q = l.title.replace(/^(For Sale|Looking to Buy|Providing|Seeking)\s*/i, '').split('—')[0].trim(); if (si) si.value = q; if (window.__mkxFilter) window.__mkxFilter(q); }
  };
  /* the sample's saved jobs are kept by the card's title text (badges included, as the Jobs page keeps them) */
  var JXD = null;
  function jobCards() { if (!JXD) { JXD = document.createElement('div'); try { JXD.innerHTML = window.JX_HTML || ''; } catch (e) {} } return [].filter.call(JXD.querySelectorAll('.jcard'), function (x) { return x.querySelector('.role-badge.have'); }); }
  function sampleJob() { var c = jobCards()[0]; return c ? [txt(c.querySelector('.jc-title'))] : []; }
  function jobTitle(key) { var c = jobCards().filter(function (x) { return txt(x.querySelector('.jc-title')) === key; })[0]; if (!c) return key;
    var t = c.querySelector('.jc-title').cloneNode(true); t.querySelectorAll('span').forEach(function (x) { x.remove(); }); return txt(t) || key; }
  var SV = { jobs: null, listings: null, seq: 0 };
  function savedSection(kind, title, list, empty) {
    return '<div class="card dx-saved-sec" data-kind="' + kind + '" style="padding:14px;margin-top:14px"><div style="font-size:15px;font-weight:800;color:var(--cx);margin-bottom:8px">' + title + '</div>' +
      (list == null ? '<div style="color:#65676b;font-size:13px">Loading…</div>' : !list.length ? '<div style="color:#65676b;font-size:13px">' + empty + '</div>' :
        list.map(function (x, i) { return '<div class="dx-saved-row" data-k="' + kind + '" data-i="' + i + '"><button type="button" class="dx-saved-open" data-noi18n>' + esc(x.title) + (x.sub ? '<small>' + esc(x.sub) + '</small>' : '') + '</button>' +
          '<button type="button" class="btn-ghost dx-saved-un">Unsave</button></div>'; }).join('')) + '</div>';
  }
  var oRenderSaved = window.renderSaved;
  window.renderSaved = function (c) {
    var r = oRenderSaved.apply(this, arguments); if (!c) return r;
    var h = c.querySelector('h1'); if (h && /Saved Posts/.test(h.textContent)) { h.textContent = '🔖 Saved'; h.insertAdjacentHTML('afterend', '<div style="font-size:15px;font-weight:800;color:var(--cx);margin:4px 0 8px">Posts</div>'); }
    var host = c.querySelector('.saved-list') || c;
    host.insertAdjacentHTML('beforeend', savedSection('jobs', '💼 Jobs', SV.jobs, 'No saved jobs yet — press Save on a job to keep it here.') + savedSection('listings', '📦 Listings', SV.listings, 'No saved listings yet — press Save on a listing in the Marketplace.'));
    var seq = ++SV.seq, S = window.dxSavedSvc;
    Promise.all([S.jobs(), S.listings()]).then(function (a) {
      if (seq !== SV.seq || page() !== 'saved') return; var changed = JSON.stringify(a) !== JSON.stringify([SV.jobs, SV.listings]); SV.jobs = a[0]; SV.listings = a[1];
      if (changed) { var sec = c.querySelectorAll('.dx-saved-sec'); sec.forEach(function (s) { s.remove(); }); host.insertAdjacentHTML('beforeend', savedSection('jobs', '💼 Jobs', SV.jobs, 'No saved jobs yet — press Save on a job to keep it here.') + savedSection('listings', '📦 Listings', SV.listings, 'No saved listings yet — press Save on a listing in the Marketplace.')); }
    }, function (e) { toast((e && e.message) || 'Could not load your saved items'); });
    return r;
  };
  document.addEventListener('click', function (e) {
    var row = e.target.closest && e.target.closest('.dx-saved-row'); if (!row) return;
    var kind = row.dataset.k, x = (kind === 'jobs' ? SV.jobs : SV.listings || [])[+row.dataset.i]; if (!x) return; var S = window.dxSavedSvc;
    if (e.target.closest('.dx-saved-un')) {
      (kind === 'jobs' ? S.unsaveJob(x) : S.unsaveListing(x)).then(function () {
        if (kind === 'jobs') SV.jobs = SV.jobs.filter(function (y) { return y !== x; }); else SV.listings = SV.listings.filter(function (y) { return y !== x; });
        toast(kind === 'jobs' ? 'Removed from saved jobs' : 'Removed from saved listings'); window.renderSaved(document.getElementById('content'));
      }, function (er) { toast((er && er.message) || 'Could not remove it — try again'); });
      return;
    }
    if (e.target.closest('.dx-saved-open')) kind === 'jobs' ? S.openJob(x) : S.openListing(x);
  });

  /* ═════ E. a notification opens what it is about (S-20) ═════ */
  var oRead = window.markNotifRead;
  window.markNotifRead = function (id) {
    var n = (window.NOTIFS || []).find(function (x) { return x.id === id; });
    var r = oRead.apply(this, arguments); if (!n) return r;
    var t = n.type, L = window.dxLive;
    if (n.pid && /^(like|comment|reply|mention|repost)$/.test(t)) { if (!L && window.dxOpenPost) window.dxOpenPost(n.pid, { comments: t === 'comment' || t === 'reply' }); return r; }   /* live: the adapter opens it */
    if (!L && !n.pid && /^(like|comment)$/.test(t) && window.dxOpenPost) {   /* the sample's notices name no post: my post they are about (its words, else my latest) */
      var me = window.ME || {}, mine = (window.POSTS || []).filter(function (p) { return p.uid === me.id; }), words = String(n.text || '').replace(/<[^>]+>/g, '').toLowerCase().split(/\W+/).filter(function (w) { return w.length > 5; });
      var hasC = function (p) { return ((window.COMMENTS || {})[p.id] || []).length > 0; };
      var pick = mine.filter(function (p) { return words.some(function (w) { return String(p.body || '').toLowerCase().indexOf(w) >= 0; }); })[0] || (t === 'comment' ? mine.filter(hasC)[0] : null) || mine[0];
      if (pick) window.dxOpenPost(pick.id, { comments: t === 'comment' }); return r;
    }
    later(function () {
      if (/^(connection|accepted|follow|endorse|connection_request|connection_accepted)$/.test(t) && n.uid > 0) window.gotoProfile(n.uid);
      else if (t === 'message' && n.uid > 0) window.messageUser ? window.messageUser(n.uid) : window.goto('messages');
      else if (t === 'saved_search' && n.data) { if (n.data.kind === 'jobs') { window.goto('jobs'); flash('#jx .jcard', n.data.title || ''); } else { window.goto('market'); var si = document.getElementById('searchIn'); if (si) { si.value = n.data.title || ''; si.dispatchEvent(new Event('input', { bubbles: true })); } } }
      else if (t === 'job_application' || t === 'job') window.goto('jobs');
      else if (t === 'group_invite' || t === 'group') { window.goto('groups'); if (n.data && n.data.name) flash('#gx .gcard', n.data.name); }
      else if (t === 'deal' && window.dxDeals) window.dxDeals.center('received');
      else if (t === 'company_message') window.goto('messages');
    }, 0);
    return r;
  };
  /* every request or acceptance row offers View profile */
  function viewProfileButtons() {
    if (page() !== 'notifs') return;
    document.querySelectorAll('#notifItems .notif-item').forEach(function (row) {
      var n = (window.NOTIFS || []).find(function (x) { return 'notif-' + x.id === row.id; }); if (!n || !/^(accepted|follow|endorse)$/.test(n.type) || n.uid <= 0 || row.querySelector('[data-gp]')) return;
      var host = row.querySelector('.notif-content'); if (!host) return;
      host.insertAdjacentHTML('beforeend', '<div style="display:flex;gap:8px;margin-top:8px"><button class="btn-ghost" style="padding:5px 14px;font-size:12px" data-gp="' + n.uid + '" onclick="event.stopPropagation();markNotifRead(' + n.id + ')">View profile</button></div>');
    });
  }
  if (window.dxCore) window.dxCore.onRender('soc-notif-profile', viewProfileButtons);

  if (window.dxI18nAdd) window.dxI18nAdd({
    'Settings': 'الإعدادات', 'Go to Settings': 'افتح الإعدادات', 'New post': 'منشور جديد', 'Write a post': 'اكتب منشوراً',
    '👥 People': '👥 أشخاص', '🏢 Companies': '🏢 شركات', '📦 Products & listings': '📦 منتجات وعروض', '💼 Jobs': '💼 وظائف', '👥 Groups': '👥 مجموعات', '📝 Posts': '📝 منشورات',
    'Searching…': 'جارٍ البحث…', 'Try a product, a company or a person — or fewer words.': 'جرّب منتجاً أو شركة أو شخصاً — أو كلمات أقل.',
    '🔖 Saved': '🔖 المحفوظات', 'Posts': 'المنشورات', '📦 Listings': '📦 العروض', 'Unsave': 'إلغاء الحفظ', 'Loading…': 'جارٍ التحميل…',
    'No saved jobs yet — press Save on a job to keep it here.': 'لا توجد وظائف محفوظة بعد — اضغط حفظ على أي وظيفة لتظهر هنا.',
    'No saved listings yet — press Save on a listing in the Marketplace.': 'لا توجد عروض محفوظة بعد — اضغط حفظ على أي عرض في السوق.',
    'Removed from saved jobs': 'أُزيلت من الوظائف المحفوظة', 'Removed from saved listings': 'أُزيل من العروض المحفوظة', 'View profile': 'عرض الملف',
    'Search is not available right now — try again': 'البحث غير متاح الآن — حاول مرة أخرى'
  }, [[/^Results for "(.+)"$/, function (m) { return 'نتائج البحث عن "' + m[1] + '"'; }], [/^No results for "(.+)"$/, function (m) { return 'لا توجد نتائج لـ "' + m[1] + '"'; }]]);
})();
