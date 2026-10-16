/* Drugbox live data adapter — B1: real accounts and profile · B2: feed (posts, reactions, comments, saved; 20 at a time).
   The interface is the approved demo, unchanged; this file only replaces where data comes from.
   Loaded only in the live build (web/build/live.py); the demo build never contains it. */
(function () {
  var CFG = window.DRUGBOX_CONFIG, lib = window.supabase;
  if (!CFG || !CFG.url || !CFG.anonKey || !lib) { console.error('Drugbox live: missing configuration'); return; }
  var sb = lib.createClient(CFG.url, CFG.anonKey, { auth: { persistSession: true, autoRefreshToken: true, storageKey: 'dx-auth' } });
  var orig = { login: window.doLogin, signup: window.doSignup, logout: window.doLogout };
  /* People get a small local number for the interface (it writes ids unquoted into buttons and parseInt()s them);
     the adapter converts to the database UUID whenever it talks to the database. */
  var A = {}, Z = {}, SEQ = 1000, ME_UUID = null;
  function aid(u) { if (!u) return null; if (!A[u]) { A[u] = ++SEQ; Z[SEQ] = u; } return A[u]; }
  function uuidOf(a) { return Z[a] || null; }
  var PALETTE = ['#0E1320', '#1A56DB', '#0E8C66', '#7C3AED', '#B45309', '#BE185D', '#0891B2', '#4B5563'];
  function initials(n) { return String(n || '?').trim().split(/\s+/).map(function (w) { return w[0]; }).slice(0, 2).join('').toUpperCase(); }
  function colorFor(id) { var h = 0, s = String(id); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return PALETTE[Math.abs(h) % PALETTE.length]; }
  function show(id, msg) { var e = document.getElementById(id); if (e) { e.textContent = msg; e.style.display = 'block'; } }
  function hide(id) { var e = document.getElementById(id); if (e) e.style.display = 'none'; }
  function busy(on) { document.querySelectorAll('#loginPage button.f-btn, #signupPage button.f-btn').forEach(function (b) { b.disabled = on; b.style.opacity = on ? '.6' : ''; }); }
  /* database text is never trusted as markup (F-02): a URL the interface puts in src / href / url() must be http(s), data:image/ or
     blob: (anything else becomes ''), and identity text (names, headlines, companies…) never carries markup characters */
  function safeUrl(u) { if (window.dxDir && window.dxDir.safeUrl) return window.dxDir.safeUrl(u);
    u = String(u == null ? '' : u).trim(); if (!u || /["'<>()\s\\]/.test(u)) return ''; if (/^data:image\/(png|jpe?g|gif|webp);/i.test(u) || /^blob:/i.test(u)) return u;
    try { var x = new URL(u, location.href); return x.protocol === 'https:' || x.protocol === 'http:' ? u : ''; } catch (e) { return ''; } }
  /* lookalikes, not entities: the approved markup puts this text both through esc() and straight into innerHTML / attributes /
     inline handlers, so it must read the same either way (& only where it would start an entity such as &#39; or &quot — "R&D" stays) */
  function txt(s) { return String(s == null ? '' : s).replace(/[<>"'`\\]|&(?=#|[a-z][a-z0-9]*;|(?:quot|lt|gt|amp)(?![a-z0-9=]))/gi, function (c) { return { '<': '‹', '>': '›', '"': '”', "'": '’', '`': '‘', '\\': '＼', '&': '＆' }[c]; }); }
  /* a company address (slug) is written into the markup unescaped by the approved directory: one with markup characters is never shown */
  function okSlug(s) { return typeof s === 'string' && /^[^\s"'<>`&\\]{1,120}$/.test(s); }
  function sslug(s) { return okSlug(s) ? s : null; }
  /* a person's bio is prose the approved markup only ever writes through esc() / textContent (About tab, candidate cards), so it is
     kept exactly as written — "<b>" stays "<b>" on screen, as text (J-SOCIAL-22) */
  function prose(s) { return String(s == null ? '' : s); }
  function tel(s) { return String(s == null ? '' : s).replace(/[^0-9+\-() ]/g, '').trim(); }
  function hexOr(c, id) { return /^#[0-9a-f]{3,8}$/i.test(String(c || '')) ? c : colorFor(id); }
  /* the columns of a person the interface shows (embedded rows carry these, never phone / résumé fields) */
  var PCOLS = 'id,name,headline,company,country,bio,avatar_url,role,verified,location,open_to_work,hiring,profile_views,followers_count';
  /* errors are shown in words people understand — never raw database text (table, policy or function names) */
  var TECH = /relation|column|function|schema|syntax|constraint|violates|PGRST|null value|operator|SQLSTATE|policy|permission|privilege|JSON object|cannot coerce|does not exist/i;
  function friendly(x) {
    var m = typeof x === 'string' ? x : String((x && x.message) || x || ''), code = x && typeof x === 'object' && x.code ? String(x.code) : '', st = x && typeof x === 'object' ? +x.status || 0 : 0;
    if (/invalid login credentials/i.test(m)) return 'Wrong email or password';
    if (/already registered/i.test(m)) return 'An account with this email already exists — sign in instead';
    if (/at least 8/i.test(m)) return 'Password must be at least 8 characters';
    if (/invalid email|unable to validate email/i.test(m)) return 'Please enter a valid email';
    if (/failed to fetch|networkerror|network request failed|load failed|err_internet/i.test(m) || navigator.onLine === false) return 'Connection problem — check your internet and try again';
    if (code === 'PGRST301' || code === 'PGRST303' || st === 401 || /jwt (expired|malformed)|invalid jwt|auth session missing/i.test(m)) return 'Your session ended — please sign in again';
    if (code === '23505' || /duplicate key/i.test(m)) return 'This already exists';
    /* the text limits (0022) are the *_len / *_size checks and the column checks on what people type (body, title, name, note…) */
    if (code === '23514' || code === '22001' || /check constraint|value too long/i.test(m))
      return code === '22001' || /value too long|_len"|_size"|_(body|title|name|reply|note|issue|correction|description|product|number|registry|text)_check"/i.test(m) ? 'This text is too long — please shorten it' : 'Some of the values are not accepted — please check and try again';
    if (code === '23503' || /foreign key/i.test(m)) return 'This is linked to other records and cannot be changed';
    if (code === '22P02' || code === '22007' || code === '22008' || code === '22003' || /invalid input syntax|out of range/i.test(m)) return 'Please check the values you entered';
    if (code === 'PGRST116' || /JSON object requested/i.test(m)) return 'Not found — or you are not allowed to change it';
    if (/row-level security|permission denied|insufficient.privilege/i.test(m) || (code === '42501' && TECH.test(m))) return 'You are not allowed to do this';
    if (/mime type|file size|maximum allowed size|payload too large/i.test(m) || st === 413) return 'This file type or size is not accepted';
    if (st === 429) return 'Too many requests — please wait a moment and try again';
    if (!m || TECH.test(m) || /^(PGRST|XX|42(?!501)|53|54|55|57|58)/.test(code)) return 'Something went wrong — please try again';
    return m;                                             /* the database's own refusals (raise exception …) are written for people */
  }
  /* everything kept for the signed-in person is dropped when they sign out or their session ends: each part registers its reset */
  var RESETS = [], LEAVING = false, SIGNING = false;
  function onReset(f) { RESETS.push(f); }
  function resetUser() { RESETS.forEach(function (f) { try { f(); } catch (e) { console.error(e); } }); }
  onReset(function () {
    ME_UUID = null; A = {}; Z = {}; SEQ = 1000;
    var U = window.USERS || [], k = U.filter(function (u) { return u.id <= 1000 && u !== window.ME; }); U.length = 0; k.forEach(function (u) { U.push(u); });
    Object.keys(window.CONN_STATE || {}).forEach(function (x) { if (+x > 1000) delete window.CONN_STATE[x]; });
    /* what the interface keeps in this browser for a person (stores dx_*, kit dbx_*) goes too; only the interface preferences stay */
    try { Object.keys(localStorage).forEach(function (x) { if (/^dbx?_/.test(x) && !/^dx_(lang|theme|tour_done|flags)$/.test(x)) localStorage.removeItem(x); }); } catch (e) {}
  });
  /* the demo's sample people, posts, comments and notifications never show in the live app (F-54) */
  function clearSeeds() {
    var U = window.USERS || [], real = U.filter(function (u) { return u.id > 1000 && u.id !== window.ME.id; }); U.length = 0; U.push(window.ME); real.forEach(function (u) { U.push(u); });
    if (window.POSTS) window.POSTS.length = 0; if (window.NOTIFS) window.NOTIFS.length = 0;
    Object.keys(window.COMMENTS || {}).forEach(function (k) { delete window.COMMENTS[k]; });
    /* the sample connections, requests, follows and dismissed suggestions (people 2…7) are not this member's */
    [window.CONN_STATE, window.CONN_IN, window.FOLLOWS, window.SUGG_HIDDEN].forEach(function (o) { Object.keys(o || {}).forEach(function (k) { if (+k <= 1000) delete o[k]; }); });
  }
  /* the signed-in person becomes ME — same fields the interface already reads */
  async function hydrateMe(uid) {
    var r = await sb.from('profiles').select('*').eq('id', uid).single();
    if (r.error) throw r.error;
    var p = r.data; if (ME_UUID && ME_UUID !== p.id) resetUser(); ME_UUID = p.id;
    Object.assign(window.ME, {
      id: aid(p.id), name: txt(p.name), initials: initials(txt(p.name)), headline: txt(p.headline), company: txt(p.company), country: txt(p.country || 'EG'),
      verified: !!p.verified, role: p.role || 'user', bio: prose(p.bio), web: safeUrl(p.website), phone: tel(p.phone), certs: txt(p.certs), avatar: safeUrl(p.avatar_url),
      location: txt(p.location), followers: p.followers_count || 0, openToWork: !!p.open_to_work, hiring: !!p.hiring, color: colorFor(p.id),
      profileViews: p.profile_views || '0', connections: '0'          /* '0', not 0: the approved sidebar shows sample numbers for a falsy value */
    });
    clearSeeds();
    return window.ME;
  }
  function enterApp() {                        /* same steps the interface's own login performs */
    hide('authWrap'); var app = document.getElementById('app'); if (app) app.style.display = 'flex';
    if (typeof window.goto === 'function') window.goto('feed'); if (typeof window.updateTopUser === 'function') window.updateTopUser();
  }
  window.doLogin = async function () {
    var email = (document.getElementById('loginEmail') || {}).value || '', pw = (document.getElementById('loginPw') || {}).value || '';
    hide('loginErr'); email = email.trim();
    if (!email) return show('loginErr', 'Email is required'); if (!pw) return show('loginErr', 'Password is required');
    busy(true); SIGNING = true;
    try { var r = await sb.auth.signInWithPassword({ email: email, password: pw }); if (r.error) return show('loginErr', friendly(r.error));
      await hydrateMe(r.data.user.id); orig.login(); }
    catch (e) { show('loginErr', friendly(e)); } finally { busy(false); SIGNING = false; }
  };
  window.doSignup = async function () {
    var name = ((document.getElementById('suName') || {}).value || '').trim(), email = ((document.getElementById('suEmail') || {}).value || '').trim(), pw = (document.getElementById('suPw') || {}).value || '';
    hide('suErr');
    if (!name) return show('suErr', 'Name is required'); if (!email) return show('suErr', 'Email is required'); if (pw.length < 8) return show('suErr', 'Password must be at least 8 characters');
    busy(true); SIGNING = true;
    try { var co = ((document.getElementById('suCompany') || {}).value || '').trim(), ro = document.getElementById('suRole'), sp = ro && ro.selectedIndex < ro.options.length - 1 ? ro.value.trim() : '';   /* the last choice is "Other": no specialty */
      var r = await sb.auth.signUp({ email: email, password: pw, options: { data: { name: name, company: co, specialty: sp } } }); if (r.error) return show('suErr', friendly(r.error));
      if (!r.data.session) return show('suErr', 'Check your email to confirm your account, then sign in');
      var me = await hydrateMe(r.data.user.id);
      if (typeof window.signupEnter === 'function') window.signupEnter(me.name, me.company, me.headline); else orig.signup(); }
    catch (e) { show('suErr', friendly(e)); } finally { busy(false); SIGNING = false; }
  };
  window.doLogout = async function () { LEAVING = true; try { await sb.auth.signOut(); } catch (e) {} resetUser(); LEAVING = false; orig.logout(); };
  /* A-04: Admin is for Drugbox staff. The sidebar's "⚙️ Admin" shows only to a Drugbox admin (profiles.role, read at sign-in);
     the database stays the authority (is_platform_admin). Anyone else who opens Admin gets the approved "Admin access required"
     page, which says why. */
  function isStaff() { return !!ME_UUID && window.ME.role === 'admin'; }
  function paintAdminEntry() { var on = isStaff(); document.querySelectorAll('#app .sb-foot [onclick="goto(\'admin\')"]').forEach(function (a) { a.style.display = on ? '' : 'none'; }); }
  var gotoA4 = window.goto;
  window.goto = function () { var r = gotoA4.apply(this, arguments); paintAdminEntry(); return r; };
  var rAdminA4 = window.renderAdmin;
  if (typeof rAdminA4 === 'function') window.renderAdmin = function (c) {
    var r = rAdminA4.apply(this, arguments), box = ME_UUID && !isStaff() && c && c.firstElementChild;
    if (box) { var d = document.createElement('div'); d.style.cssText = 'font-size:13px;margin-top:6px'; d.textContent = 'Not allowed for your account — Admin is for Drugbox staff.'; box.appendChild(d); }
    return r;
  };
  paintAdminEntry(); if (window.dxCore) window.dxCore.onRender('live-admin-entry', paintAdminEntry);
  /* the session ended outside this page (signed out in another tab, refresh refused, account removed): back to the login page,
     nothing of that person stays in the page (F-52) */
  function sessionEnded() { if (!ME_UUID || LEAVING) return; resetUser(); orig.logout(); if (typeof window.toast === 'function') window.toast('Your session ended — please sign in again'); }
  sb.auth.onAuthStateChange(function (ev, s) {
    if (ev === 'SIGNED_OUT') setTimeout(sessionEnded, 0);
    else if (ev === 'SIGNED_IN' && s && !LEAVING && !SIGNING) {                   /* signed in in another tab (this tab's own sign-in is SIGNING) */
      if (ME_UUID && s.user.id !== ME_UUID) location.reload();                    /* another account: start clean with it */
      else if (!ME_UUID) setTimeout(function () { restore(s, 0); }, 0);           /* this tab shows the login page: open the app */
    }
  });
  /* a saved session opens the app directly after the splash. The approved endSplash re-shows #authWrap 700 ms after the fade
     starts, so the app opens after that (F-19). The splash is watched, not endSplash: its own 5.2 s timer holds the original
     function. (#splash is position:fixed, so its offsetParent is always null — not used.) */
  function openAfterSplash() { setTimeout(function () { if (ME_UUID) enterApp(); }, 750); }
  function afterSplash() {
    var sp = document.getElementById('splash'), shown = function () { return !!sp && getComputedStyle(sp).display !== 'none'; };
    if (!shown()) return enterApp(); if (sp.classList.contains('hide')) return openAfterSplash();
    var mo = new MutationObserver(function () { if (shown() && !sp.classList.contains('hide')) return; mo.disconnect(); if (shown()) openAfterSplash(); else enterApp(); });
    mo.observe(sp, { attributes: true, attributeFilter: ['class', 'style'] });
  }
  /* only a missing account or a refused session signs out; a network blip keeps the session and tries again (F-53) */
  function authGone(e) { var c = String((e && e.code) || ''), st = +(e && e.status) || 0; return c === 'PGRST116' || c === 'PGRST301' || c === 'PGRST303' || st === 401 || st === 403 || /jwt|session/i.test(String((e && e.message) || '')); }
  var RESTORING = false;
  function restore(s, tries) {
    if (ME_UUID || RESTORING || SIGNING) return; RESTORING = true;                          /* signed in by hand meanwhile, or already opening */
    hydrateMe(s.user.id).then(function () { RESTORING = false; hide('loginErr'); afterSplash(); }, function (e) { RESTORING = false;
      if (authGone(e)) { sb.auth.signOut(); return; }
      show('loginErr', friendly(e));
      if (tries < 5) setTimeout(function () { sb.auth.getSession().then(function (r) { var x = r.data && r.data.session; if (x) restore(x, tries + 1); }); }, 2000 * Math.pow(2, tries));
    });
  }
  sb.auth.getSession().then(function (r) { var s = r.data && r.data.session; if (s) restore(s, 0); });
  window.dxLive = { sb: sb, hydrateMe: function (u) { return hydrateMe(u); }, friendly: friendly, version: 'B1' };

  /* Edit Profile → Save Changes (S-01): the approved form is checked by its own profileForm(), the row is written first (the column guard
     of 0020 keeps role / verified / counters; 0029 limits the contact fields), and only then the approved saveProfile() shows it — with the
     values a reload would show. A refusal keeps the editor open with what was typed and says why. */
  var oSaveProfile = window.saveProfile, PSAVE = false;
  window.saveProfile = async function () {
    if (!ME_UUID || typeof window.profileForm !== 'function') return oSaveProfile.apply(this, arguments);
    if (PSAVE) return; var f = window.profileForm(); if (!f) return;
    var btn = document.querySelector('.modal-bg [onclick^="saveProfile"]'); PSAVE = true; if (btn) { btn.disabled = true; btn.setAttribute('aria-busy', 'true'); }
    try {
      var nul = function (v) { return v ? v : null; };
      var r = await sb.from('profiles').update({ name: f.name, headline: nul(f.headline), company: nul(f.company), location: nul(f.location), website: nul(f.web),
        phone: nul(f.phone), certs: nul(f.certs), bio: nul(f.bio), open_to_work: !!f.openToWork, updated_at: new Date().toISOString() })
        .eq('id', ME_UUID).select('name,headline,company,location,website,phone,certs,bio,open_to_work').single();
      if (r.error) throw r.error;
      var p = r.data;
      oSaveProfile({ name: txt(p.name), headline: txt(p.headline), company: txt(p.company), location: txt(p.location), web: safeUrl(p.website), phone: tel(p.phone),
        certs: txt(p.certs), bio: prose(p.bio), openToWork: !!p.open_to_work });
    } catch (e) { toastErr(e); }
    finally { PSAVE = false; if (btn && btn.isConnected) { btn.disabled = false; btn.removeAttribute('aria-busy'); } }
  };

  /* ═══════════════ B2 — feed: posts, reactions, comments, saved (20 at a time) ═══════════════ */
  var PAGE = 20, FEED = { cursor: null, done: false, loading: false, at: 0 }, CMT_LOADED = {};
  function ago(ts) { var s = (Date.now() - new Date(ts).getTime()) / 1000; if (s < 60) return 'just now'; if (s < 3600) return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago'; if (s < 604800) return Math.floor(s / 86400) + 'd ago'; return new Date(ts).toLocaleDateString(); }
  function userFrom(p) { var u = { id: aid(p.id), name: txt(p.name || 'Member'), initials: initials(txt(p.name)), headline: txt(p.headline), company: txt(p.company), country: txt(p.country || 'EG'),
    verified: !!p.verified, color: colorFor(p.id), role: p.role || 'user', avatar: safeUrl(p.avatar_url), location: txt(p.location), connections: 0, followers: p.followers_count || 0,
    openToWork: !!p.open_to_work, hiring: !!p.hiring, profileViews: p.profile_views || 0, bio: prose(p.bio) };
    /* website and certifications come with a whole profile row (opening the profile), not with the people embedded in lists; a list row
       never blanks what the profile row brought (phone stays private: it is never put on another person) */
    if ('website' in p) { u.web = safeUrl(p.website); u.certs = txt(p.certs); u.full = true; }
    return u; }
  function putUser(p) { if (!p) return; if (p.id === ME_UUID) return; var u = userFrom(p), list = window.USERS, i = list.findIndex(function (x) { return x.id === u.id; }); if (i < 0) list.push(u); else Object.assign(list[i], u); }
  /* mine: Map post id → my reaction kind; kinds: post id → {kind: n} (post_reaction_summary, 0028) */
  function postFrom(r, mine, saved, kinds) { var media = r.post_media || [], rx = (kinds && kinds[r.id]) || null;
    return { id: r.id, uid: aid(r.user_id), cat: r.category, body: r.body, likeCount: r.like_count || 0, liked: mine.has(r.id), myKind: mine.get(r.id) || null, commentCount: r.comment_count || 0, shareCount: r.share_count || 0,
      viewCount: r.view_count || 0, saved: saved.has(r.id), pinned: !!r.pinned, ts: ago(r.created_at), created_at: r.created_at,
      imgs: media.filter(function (m) { return m.type === 'image' && safeUrl(m.url); }).map(function (m) { return safeUrl(m.url); }),
      files: media.filter(function (m) { return m.type !== 'image' && safeUrl(m.url); }).map(function (m) { return { name: txt(m.name), size: +m.size || 0, url: safeUrl(m.url) }; }),
      reactions: rx || (r.like_count ? { like: r.like_count } : {}) }; }
  /* my reaction (and its kind), my saves and the reactions per kind for a set of posts — one round of three requests */
  async function postState(ids) {
    var mine = new Map(), saved = new Set(), kinds = {};
    if (!ids.length) return { mine: mine, saved: saved, kinds: kinds };
    var a = await Promise.all([sb.from('reactions').select('post_id,kind').eq('user_id', ME_UUID).in('post_id', ids), sb.from('saved_posts').select('post_id').eq('user_id', ME_UUID).in('post_id', ids),
                               sb.rpc('post_reaction_summary', { p_ids: ids.slice(0, 100) })]);
    (a[0].data || []).forEach(function (x) { mine.set(x.post_id, x.kind || 'like'); }); (a[1].data || []).forEach(function (x) { saved.add(x.post_id); });
    (a[2].data || []).forEach(function (x) { var k = x.kind === 'love' ? 'support' : x.kind, o = kinds[x.post_id] = kinds[x.post_id] || {}; o[k] = (o[k] || 0) + x.n; });
    return { mine: mine, saved: saved, kinds: kinds };
  }
  var POST_SEL = '*, author:profiles!posts_user_id_fkey(' + PCOLS + '), post_media(*)';
  async function fetchPage() {
    var q = sb.from('posts').select(POST_SEL).is('group_id', null).order('created_at', { ascending: false }).order('id', { ascending: false }).limit(PAGE);
    /* group posts (0027) live in their group, never in the main feed — the filter is also what lets the main feed use its own index;
       keyset (created_at, id) < cursor: the extra created_at <= T is an index condition, so a deep page reads one page of the index
       instead of every newer row (F-111); the or() keeps the exact tie-break */
    if (FEED.cursor) q = q.lte('created_at', FEED.cursor.t).or('created_at.lt.' + FEED.cursor.t + ',and(created_at.eq.' + FEED.cursor.t + ',id.lt.' + FEED.cursor.id + ')');
    var r = await q; if (r.error) throw r.error; var rows = r.data || [], ids = rows.map(function (x) { return x.id; });
    var ps = await postState(ids);
    rows.forEach(function (x) { putUser(x.author); });
    if (rows.length) { var last = rows[rows.length - 1]; FEED.cursor = { t: last.created_at, id: last.id }; }
    if (rows.length < PAGE) FEED.done = true;
    return rows.map(function (x) { return postFrom(x, ps.mine, ps.saved, ps.kinds); });
  }
  async function loadFeed(reset) {
    if (FEED.loading) return; FEED.loading = true;
    try { if (reset) { FEED.cursor = null; FEED.done = false; CMT_LOADED = {}; }
      var posts = await fetchPage(), list = window.POSTS;
      if (reset) { list.length = 0; Object.keys(window.COMMENTS).forEach(function (k) { delete window.COMMENTS[k]; }); }
      posts.forEach(function (p) { if (!list.some(function (x) { return x.id === p.id; })) list.push(p); });
      FEED.at = Date.now(); return posts;
    } finally { FEED.loading = false; }
  }
  onReset(function () { FEED.cursor = null; FEED.done = false; FEED.loading = false; FEED.at = 0; CMT_LOADED = {}; if (io) { io.disconnect(); io = null; }
    if (window.POSTS) window.POSTS.length = 0; Object.keys(window.COMMENTS || {}).forEach(function (k) { delete window.COMMENTS[k]; }); });
  function feedList() { var p = document.querySelector('#content .post'); return p ? p.parentElement : null; }
  var io = null;
  function watchEnd() {
    if (io) io.disconnect(); if (FEED.done || !('IntersectionObserver' in window)) return;
    var posts = document.querySelectorAll('#content .post'), last = posts[posts.length - 1]; if (!last) return;
    io = new IntersectionObserver(function (en) { if (!en[0].isIntersecting || FEED.loading || FEED.done) return; io.disconnect();
      loadFeed(false).then(function (more) { var box = feedList(); if (box && more.length) more.forEach(function (p) { box.insertAdjacentHTML('beforeend', window.renderPost(p)); }); watchEnd(); })
        .catch(function (e) { toastErr(e); }); }, { rootMargin: '600px' });
    io.observe(last);
  }
  function toastErr(e) { if (typeof window.toast === 'function') window.toast(friendly(e)); console.error('Drugbox live:', e);
    if (ME_UUID && authGone(e)) sb.auth.getSession().then(function (r) { if (!(r.data && r.data.session)) sessionEnded(); });   /* a refused session: back to sign-in */ }
  var origGoto = window.goto;
  window.goto = function (page) {
    var r = origGoto.apply(this, arguments);
    if (page === 'feed' && ME_UUID) {
      if (Date.now() - FEED.at > 30000) loadFeed(true).then(function () { if (document.body.getAttribute('data-page') === 'feed') { origGoto('feed'); watchEnd(); } }).catch(toastErr);
      else setTimeout(watchEnd, 0);
    }
    return r;
  };
  /* writes: the interface updates at once; the database confirms or the change is undone */
  var o2 = { submitPost: window.submitPost, likePost: window.likePost, submitComment: window.submitComment, toggleComments: window.toggleComments, savePost: window.savePost, deletePost: window.deletePost };

  /* ═══════════════ E1a — uploads: post photos/files (public), message photos/files (private, signed links) ═══════════════ */
  var EXT = { 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif', 'application/pdf': 'pdf', 'application/zip': 'zip',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx' };
  function rid() { return Math.random().toString(36).slice(2, 10) + Date.now().toString(36); }
  /* a storage key never takes raw text from a file name: letters and digits only, at most 8 (F-123) */
  function safeExt(name) { var n = String(name || ''), i = n.lastIndexOf('.'); return (i > 0 ? n.slice(i + 1).toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 8) : '') || 'bin'; }
  async function blobOf(x) { if (x instanceof Blob) return x;
    var m = /^data:([^;,]+);base64,(.*)$/.exec(String(x));   /* a photo made smaller in the browser (groups.js): decoded here, never fetched (CSP connect-src) */
    if (m) { var bin = atob(m[2]), u8 = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i); return new Blob([u8], { type: m[1] }); }
    var r = await fetch(x); return r.blob(); }
  async function uploadPostMedia(postId, imgs, files) {
    var out = { imgs: [], files: [] }, rows = [];
    for (var i = 0; i < imgs.length; i++) { var b = await blobOf(imgs[i]), path = 'posts/' + ME_UUID + '/' + postId + '-' + rid() + '.' + (EXT[b.type] || 'jpg');
      var up = await sb.storage.from('post-media').upload(path, b, { contentType: b.type || 'image/jpeg' }); if (up.error) { toastErr(up.error); continue; }
      var u = sb.storage.from('post-media').getPublicUrl(path).data.publicUrl; out.imgs.push(u); rows.push({ post_id: postId, url: u, type: 'image', name: 'photo', size: b.size }); }
    for (var j = 0; j < files.length; j++) { var f = files[j], fb = await blobOf(f.url || f.file || f), ext = EXT[fb.type] || safeExt(f.name), p2 = 'posts/' + ME_UUID + '/' + postId + '-' + rid() + '.' + ext;
      var up2 = await sb.storage.from('post-media').upload(p2, fb, { contentType: fb.type || 'application/octet-stream' }); if (up2.error) { toastErr(up2.error); continue; }
      var u2 = sb.storage.from('post-media').getPublicUrl(p2).data.publicUrl; out.files.push({ name: f.name, size: f.size, url: u2 }); rows.push({ post_id: postId, url: u2, type: 'file', name: f.name, size: f.size }); }
    if (rows.length) { var r = await sb.from('post_media').insert(rows); if (r.error) toastErr(r.error); }
    return out;
  }
  function attHtml(att, local) {
    if (!att) return '';
    if (att.kind === 'photo') return '<img class="msg-image dx-signed" ' + (local ? 'src="' + local + '"' : 'data-sign="' + esc2(att.path) + '"') + ' alt="photo" style="max-width:220px;border-radius:10px;display:block;margin-bottom:4px">';
    return '<a class="dx-msg-file dx-signed" ' + (local ? 'href="' + local + '"' : 'data-sign="' + esc2(att.path) + '"') + ' target="_blank" rel="noopener" style="display:inline-flex;gap:6px;align-items:center;padding:6px 10px;border-radius:9px;background:rgba(0,0,0,.06);color:inherit;text-decoration:none;font-size:12.5px">📎 ' + esc2(att.name) + ' · ' + Math.max(1, Math.round((att.size || 0) / 1024)) + ' KB</a>';
  }
  async function signAll(root) {
    var els = [].slice.call((root || document).querySelectorAll('[data-sign]')); if (!els.length) return;
    var paths = els.map(function (e) { return e.getAttribute('data-sign'); });
    var r = await sb.storage.from('message-media').createSignedUrls(paths, 3600); if (r.error) return;
    (r.data || []).forEach(function (x, i) { if (!x.signedUrl) return; var e = els[i]; if (e.tagName === 'IMG') e.src = x.signedUrl; else e.href = x.signedUrl; e.removeAttribute('data-sign'); });
  }
  window.dxLive.signAll = signAll;
  function refreshAfterPost() { var pg = document.body.getAttribute('data-page'); if (pg === 'feed') { origGoto('feed'); watchEnd(); } else if (pg === 'profile' && window.dxProfPostsRefresh) window.dxProfPostsRefresh(); }
  window.submitPost = function () {
    var body = document.getElementById('postBody'), cat = document.getElementById('postCat'), text = body ? body.value.trim() : '', category = cat ? cat.value : 'general';
    var imgs = (window._postImgs || []).slice(), files = (window._postFiles || []).slice();
    if (!text && !imgs.length && !files.length) return o2.submitPost();
    o2.submitPost(); var temp = window.POSTS[0];
    sb.from('posts').insert({ user_id: ME_UUID, body: text, category: category }).select().single().then(function (r) {
      if (r.error) throw r.error; temp.id = r.data.id; temp.created_at = r.data.created_at; temp.uid = window.ME.id;
      return uploadPostMedia(r.data.id, imgs, files).then(function (m) { if (m.imgs.length) temp.imgs = m.imgs; if (m.files.length) temp.files = m.files; refreshAfterPost(); });
    }).catch(function (e) { window.POSTS = window.POSTS.filter(function (p) { return p !== temp; }); refreshAfterPost(); toastErr(e); });
  };
  /* reactions: the interface (feedacts.js doReact) changes the card at once; the database gets the same change, one write after
     the other per post (a quick like → insightful → un-like arrives in that order). A refused write puts the card back. */
  function findPost(id) { return window.POSTS.find(function (x) { return x.id === id; }) || (window.SAVED_POSTS || []).find(function (x) { return x.id === id; }) || null; }
  function kindNow(p) { return p && p.liked ? (p.myKind || 'like') : null; }
  var RX_Q = {}, oReact = window.doReact;
  window.doReact = function (id, kind) {
    var p = findPost(id), before = kindNow(p); oReact.apply(this, arguments);
    if (!p || typeof id !== 'number' || !ME_UUID) return; var after = kindNow(p); if (after === before) return;
    RX_Q[id] = (RX_Q[id] || Promise.resolve()).then(function () {
      return (after ? sb.from('reactions').upsert({ post_id: id, user_id: ME_UUID, kind: after }, { onConflict: 'post_id,user_id' }) : sb.from('reactions').delete().eq('post_id', id).eq('user_id', ME_UUID))
        .then(function (r) { if (r.error) { if (window.dxSetReaction) window.dxSetReaction(id, before); toastErr(r.error); } });
    });
  };
  window.submitComment = function (id) {
    var inp = document.getElementById('ci-' + id), text = inp ? inp.value.trim() : ''; if (!text) return;
    o2.submitComment(id);
    sb.from('comments').insert({ post_id: id, user_id: ME_UUID, body: text }).then(function (r) {
      if (r.error) { var c = window.COMMENTS[id]; if (c) c.pop(); var box = document.getElementById('cmt-' + id), last = box && box.querySelector('.cmt-box .cmt:last-child'); if (last) last.remove(); toastErr(r.error); } });
  };
  window.toggleComments = function (id) {
    var box = document.getElementById('cmt-' + id), opening = box && box.style.display === 'none';
    if (!opening || CMT_LOADED[id] || typeof id !== 'number') return o2.toggleComments(id);
    CMT_LOADED[id] = true;
    sb.from('comments').select('*, author:profiles!comments_user_id_fkey(' + PCOLS + ')').eq('post_id', id).order('created_at', { ascending: true }).order('id', { ascending: true }).limit(50).then(function (r) {
      if (r.error) throw r.error; var p = window.POSTS.find(function (x) { return x.id === id; });
      (r.data || []).forEach(function (c) { putUser(c.author); });
      window.COMMENTS[id] = (r.data || []).map(function (c) { return { uid: aid(c.user_id), text: c.body, ts: ago(c.created_at), likes: 0 }; });
      if (p) p.commentCount = Math.max(0, (p.commentCount || 0) - window.COMMENTS[id].length);   /* the interface shows stored count + loaded comments */
      var el = document.getElementById('post-' + id); if (el && p) el.outerHTML = window.renderPost(p);
      o2.toggleComments(id);
    }).catch(function (e) { CMT_LOADED[id] = false; o2.toggleComments(id); toastErr(e); });
  };
  window.savePost = function (id) {
    var p = findPost(id); o2.savePost(id); if (!p || typeof id !== 'number') return;
    var op = p.saved ? sb.from('saved_posts').upsert({ user_id: ME_UUID, post_id: id }) : sb.from('saved_posts').delete().eq('user_id', ME_UUID).eq('post_id', id);
    op.then(function (r) { if (r.error) { o2.savePost(id); toastErr(r.error); } });
  };
  /* delete keeps the interface's Undo: the database is changed only when the post really leaves the list (undo window over) */
  window.deletePost = function (id) {
    o2.deletePost(id); if (typeof id !== 'number') return;
    var waited = 0, t = setInterval(function () {
      waited += 400; var gone = !window.POSTS.some(function (p) { return p.id === id; });
      if (!gone && waited < 15000) return; clearInterval(t); if (!gone) return;   /* undone, or never confirmed */
      sb.from('posts').delete().eq('id', id).select().then(function (r) { if (r.error || !(r.data || []).length) { FEED.at = 0; origGoto('feed'); toastErr(r.error || { message: 'This post could not be deleted' }); } });
    }, 400);
  };
  /* the feed sidebar's "Who viewed your profile" lists sample people and "Search appearances" is a fixed sample number in the
     demo; the live app keeps neither, so they are left out rather than showing invented figures or real members as viewers (F-54) */
  var oSide = window.renderFeedSidebar;
  if (oSide) window.renderFeedSidebar = function () { var h = oSide.apply(this, arguments); if (!ME_UUID || typeof h !== 'string') return h;
    var k = h.indexOf('Who viewed your profile'), a = k < 0 ? -1 : h.lastIndexOf('<div class="card"', k), z = k < 0 ? -1 : h.indexOf('<div class="card"', k);
    if (a >= 0 && z > a) h = h.slice(0, a) + h.slice(z);
    var s = h.indexOf('>Search appearances<'), ra = s < 0 ? -1 : h.lastIndexOf('<div', s), rz = s < 0 ? -1 : h.indexOf('</div>', s);
    return ra >= 0 && rz > s ? h.slice(0, ra) + h.slice(rz + 6) : h; };
  window.dxLive.loadFeed = loadFeed; window.dxLive.version = 'B2';

  /* ═══════════════ P1 — feed actions on the database: who reacted, Saved, a post opened from a link, reports (0028) ═══════════════ */
  var SAVED = { at: 0, loading: false };
  async function loadSaved() {
    var r = await sb.from('saved_posts').select('created_at, post:posts(' + POST_SEL + ')').eq('user_id', ME_UUID).order('created_at', { ascending: false }).limit(100);
    if (r.error) throw r.error; var rows = (r.data || []).map(function (x) { return x.post; }).filter(Boolean);
    rows.forEach(function (x) { putUser(x.author); });
    var ps = await postState(rows.map(function (x) { return x.id; }));
    window.SAVED_POSTS = rows.map(function (x) { var p = postFrom(x, ps.mine, ps.saved, ps.kinds), f = window.POSTS.find(function (y) { return y.id === p.id; }); return f ? Object.assign(f, { saved: true }) : p; });
    SAVED.at = Date.now();
  }
  onReset(function () { SAVED.at = 0; window.SAVED_POSTS = []; });
  var gotoP1 = window.goto;
  window.goto = function (page) {
    var r = gotoP1.apply(this, arguments);
    if (page === 'saved' && ME_UUID && !SAVED.loading) { SAVED.loading = true;
      loadSaved().then(function () { if (document.body.getAttribute('data-page') === 'saved') origGoto('saved'); }).catch(toastErr).then(function () { SAVED.loading = false; }); }
    return r;
  };
  async function fetchPost(id) {
    var r = await sb.from('posts').select(POST_SEL).eq('id', id).maybeSingle(); if (r.error) throw r.error; if (!r.data) return null;
    putUser(r.data.author); var ps = await postState([r.data.id]); return postFrom(r.data, ps.mine, ps.saved, ps.kinds);
  }
  window.dxPostSvc = {
    reactors: async function (p) {
      if (typeof p.id !== 'number') return [];
      var r = await sb.from('reactions').select('kind, created_at, who:profiles!reactions_user_id_fkey(' + PCOLS + ')').eq('post_id', p.id).order('created_at', { ascending: false }).limit(100);
      if (r.error) throw new Error(friendly(r.error));
      return (r.data || []).filter(function (x) { return x.who; }).map(function (x) { putUser(x.who); return { uid: x.who.id === ME_UUID ? window.ME.id : aid(x.who.id), kind: x.kind === 'love' ? 'support' : x.kind }; });
    },
    reported: async function (p) { var r = await sb.from('post_reports').select('id').eq('post_id', p.id).eq('reporter', ME_UUID).limit(1); if (r.error) throw new Error(friendly(r.error)); return (r.data || []).length > 0; },
    report: async function (p, reason, note) {
      var r = await sb.from('post_reports').insert({ post_id: p.id, reporter: ME_UUID, reason: reason, note: note || null });
      if (r.error) { if (String(r.error.code) === '23505') return 'already'; throw new Error(friendly(r.error)); } return 'ok';
    },
    /* a post opened from a link or a notification: Home is loaded first, then the post is fetched when it is not on the first page */
    open: async function (id) {
      if (Date.now() - FEED.at > 30000) await loadFeed(true);
      var p = window.POSTS.find(function (x) { return x.id === id; }); if (p) return p;
      p = await fetchPost(id); if (p) window.POSTS.unshift(p); return p;
    },
    queue: function () { return []; },
    decide: async function (id, value, note) {
      var r = await sb.rpc('post_report_decide', { p_report: +id, p_remove: value === 'removed', p_note: note || null }); if (r.error) throw new Error(friendly(r.error));
      if (value === 'removed') { FEED.at = 0; } return true;
    }
  };

  /* ═══════════════ B3 — network (requests, connections, suggestions) + notifications ═══════════════ */
  var INCOMING = window.CONN_IN || (window.CONN_IN = {}), NET_AT = 0, NOTIF_AT = 0, NOTIF_IDS = [], SUGG = [], REJ = {};   /* REJ: my requests that were declined */
  function wipe(o) { Object.keys(o).forEach(function (k) { if (+k > 1000) delete o[k]; }); }
  var ICON = { connection_request: '🤝', connection_accepted: '✅', like: '👍', comment: '💬', job_application: '💼', post_removed: '🛡️', report_closed: '🛡️', follow: '👤', company_message: '💬' };
  var esc2 = function (t) { return window.esc ? window.esc(t) : String(t || ''); };
  /* every connection, 1,000 rows a request in id order (the API's row cap) — a big network is never cut short (F-50) */
  async function loadConnections() {
    var rows = [], last = 0;
    for (;;) {
      var r = await sb.from('connections').select('id,requester,addressee,status,rp:profiles!connections_requester_fkey(' + PCOLS + '),ap:profiles!connections_addressee_fkey(' + PCOLS + ')')
        .or('requester.eq.' + ME_UUID + ',addressee.eq.' + ME_UUID).gt('id', last).order('id').limit(1000);
      if (r.error) throw r.error; rows = rows.concat(r.data || []); if ((r.data || []).length < 1000) break; last = r.data[r.data.length - 1].id;
    }
    wipe(window.CONN_STATE); wipe(INCOMING); wipe(REJ);
    var n = 0;
    rows.forEach(function (c) { var mine = c.requester === ME_UUID, other = mine ? c.ap : c.rp; if (!other) return; putUser(other); var a = aid(other.id);
      if (c.status === 'accepted') { window.CONN_STATE[a] = 'connected'; n++; } else if (c.status === 'pending') { if (mine) window.CONN_STATE[a] = 'pending'; else INCOMING[a] = true; }
      /* a request of mine that was declined stays "Pending" for me: the sender is never told (J-SOCIAL-31) and cannot ask again at once (0030) */
      else if (c.status === 'rejected' && mine) { window.CONN_STATE[a] = 'pending'; REJ[a] = true; } });
    window.ME.connections = n || '0';
  }
  onReset(function () { wipe(INCOMING); wipe(REJ); wipe(window.FOLLOWS || {}); wipe(window.SUGG_HIDDEN || {}); SUGG = []; NET_AT = 0; NOTIF_AT = 0; NOTIF_IDS = []; if (window.NOTIFS) window.NOTIFS.length = 0; badges(); });
  /* suggestions in the database's order (mutual connections, colleagues, newest), each with its mutual count for the card's reason */
  async function loadSuggestions() { var r = await sb.rpc('suggest_people', { p_limit: 12 }); if (r.error) throw r.error;
    SUGG = (r.data || []).map(function (p) { putUser(p); var a = aid(p.id), u = window.USERS.find(function (x) { return x.id === a; }); if (u) u.mutual = p.mutual || 0; return a; }); return r.data || []; }
  window.netSuggestions = (function (demo) { return function () {
    if (!ME_UUID) return demo.apply(this, arguments);
    return SUGG.map(function (a) { return window.USERS.find(function (u) { return u.id === a; }); })
      .filter(function (u) { return u && window.CONN_STATE[u.id] !== 'connected' && !INCOMING[u.id] && !(window.SUGG_HIDDEN || {})[u.id]; }); }; })(window.netSuggestions);
  function notifFrom(n) {
    var who = esc2(n.actor ? n.actor.name : 'Someone'), a = aid(n.from_user), t;
    if (n.type === 'connection_request') t = '<b>' + who + '</b> sent you a connection request';
    else if (n.type === 'connection_accepted') t = '<b>' + who + '</b> accepted your connection request';
    else if (n.type === 'like') t = '<b>' + who + '</b> reacted to your post';
    else if (n.type === 'comment') t = '<b>' + who + '</b> commented: "' + esc2(n.message || '') + '"';
    else if (n.type === 'post_removed' || n.type === 'report_closed') t = esc2(n.message || '');
    else t = '<b>' + who + '</b> ' + esc2(n.message || '');
    var type = n.type === 'connection_request' ? (INCOMING[a] ? 'connection' : 'accepted') : n.type === 'connection_accepted' ? 'accepted' : n.type;
    return { id: n.id, uid: a, icon: ICON[n.type] || '🔔', text: t, ts: ago(n.created_at), read: !!n.read, type: type, pid: n.post_id || null };
  }
  async function loadNotifs() {
    var r = await sb.from('notifications').select('*, actor:profiles!notifications_from_user_fkey(' + PCOLS + ')').eq('user_id', ME_UUID).order('created_at', { ascending: false }).limit(50);
    if (r.error) throw r.error; (r.data || []).forEach(function (n) { putUser(n.actor); });
    var list = window.NOTIFS; list.length = 0; (r.data || []).forEach(function (n) { list.push(notifFrom(n)); }); NOTIF_IDS = list.map(function (n) { return n.id; });
    NOTIF_AT = Date.now(); badges();
  }
  function badges() {
    var un = (window.NOTIFS || []).filter(function (n) { return !n.read; }).length, inc = Object.keys(INCOMING).length;
    [['nb-not', un], ['nb-net', inc]].forEach(function (b) { var e = document.getElementById(b[0]); if (e) { e.textContent = b[1]; e.style.display = b[1] ? '' : 'none'; } });
  }
  async function netStats() { var r = await sb.rpc('my_network_stats'); if (r.error) throw r.error; var s = r.data || {};
    var vals = [s.connections || 0, s.profile_views || 0, s.impressions || 0]; document.querySelectorAll('#content .net-overview-n').forEach(function (e, i) { if (i < 3) e.textContent = Number(vals[i]).toLocaleString('en'); }); }
  var origRenderNetwork = window.renderNetwork;
  window.renderNetwork = function (c) {             /* the network shows real people only: demo people are left out of the live network */
    if (!ME_UUID) return origRenderNetwork.apply(this, arguments);
    var all = window.USERS; window.USERS = all.filter(function (u) { return u.id > 1000 || u === window.ME; });
    try { return origRenderNetwork.apply(this, arguments); } finally { window.USERS = all; }
  };
  var gotoB2 = window.goto;
  window.goto = function (page) {
    var r = gotoB2.apply(this, arguments);
    if (!ME_UUID) return r;
    if (page === 'network' && Date.now() - NET_AT > 15000) {
      Promise.all([loadConnections(), loadSuggestions()]).then(function () { NET_AT = Date.now(); badges(); if (document.body.getAttribute('data-page') === 'network') { origGoto('network'); netStats().catch(toastErr); } }).catch(toastErr);
    } else if (page === 'network') netStats().catch(toastErr);
    if ((page === 'notifs' || page === 'notifications') && Date.now() - NOTIF_AT > 10000) {
      loadConnections().then(loadNotifs).then(function () { var pg = document.body.getAttribute('data-page'); if (pg === 'notifs' || pg === 'notifications') origGoto(page); }).catch(toastErr);
    }
    return r;
  };
  var o3 = { connect: window.connect, accept: window.acceptConnection, decline: window.declineConnection, read: window.markNotifRead, readAll: window.markAllRead, clear: window.clearAllNotifs };
  window.connect = function (a) {
    if (!ME_UUID || !uuidOf(a)) return o3.connect(a);
    if (INCOMING[a]) { var n = (window.NOTIFS || []).find(function (x) { return x.uid === a && x.type === 'connection'; }); return window.acceptConnection(a, n ? n.id : null); }
    NET_AT = Date.now();                          /* the page redraw below must not reload the old state over this change */
    var before = window.CONN_STATE[a]; o3.connect(a); var now = window.CONN_STATE[a], other = uuidOf(a);
    if (before === 'pending' && REJ[a]) return;    /* withdrawing a request that was declined: nothing is left to withdraw */
    var op = now === 'pending' ? sb.from('connections').insert({ requester: ME_UUID, addressee: other, status: 'pending' }).select('id')
           : before === 'pending' ? sb.from('connections').delete().eq('requester', ME_UUID).eq('addressee', other).eq('status', 'pending') : null;
    if (op) op.then(function (r) {
      if (r.error && now === 'pending' && r.error.code === '23505') { REJ[a] = true; return; }   /* asked before and declined: it stays "Pending" */
      if (r.error) { window.CONN_STATE[a] = before; window.netRefresh ? window.netRefresh() : gotoB2(window.curPage || 'network'); toastErr(r.error); return; }
      /* one row per pair: a request crossing theirs is accepted by the database and no new row comes back — we are connected */
      if (now === 'pending' && !(r.data || []).length) { window.CONN_STATE[a] = 'connected'; NET_AT = 0; if (document.body.getAttribute('data-page') === 'network') gotoB2('network'); } });
  };
  window.acceptConnection = function (a, nid) {
    if (!ME_UUID || !uuidOf(a)) return o3.accept(a, nid);
    if (nid == null) { var nn = (window.NOTIFS || []).find(function (x) { return x.uid === a && x.type === 'connection'; }); if (nn) nid = nn.id; }
    NET_AT = Date.now(); o3.accept(a, nid); delete INCOMING[a]; badges();
    sb.from('connections').update({ status: 'accepted' }).eq('requester', uuidOf(a)).eq('addressee', ME_UUID).eq('status', 'pending').select().then(function (r) {
      if (r.error || !(r.data || []).length) { window.CONN_STATE[a] = null; NOTIF_AT = 0; NET_AT = 0; toastErr(r.error || { message: 'This request is no longer available' }); return; }
      if (nid) sb.from('notifications').update({ read: true }).eq('id', nid).then(function () {});
    });
  };
  window.declineConnection = function (a, nid) {
    if (!ME_UUID || !uuidOf(a)) return o3.decline(a, nid);
    NET_AT = Date.now(); o3.decline(a, nid); delete INCOMING[a]; badges();
    sb.from('connections').update({ status: 'rejected' }).eq('requester', uuidOf(a)).eq('addressee', ME_UUID).eq('status', 'pending').then(function (r) { if (r.error) { NET_AT = 0; toastErr(r.error); } });
    /* the request's notice goes with the answer (from the Network page there is no notice id: it is found by its sender) */
    sb.from('notifications').delete().eq('user_id', ME_UUID).eq('from_user', uuidOf(a)).eq('type', 'connection_request').then(function () {});
  };
  /* S-10 removing a connection (either side may; the other is not notified) */
  var oDrop = window.dropConnection;
  if (oDrop) window.dropConnection = function (a) {
    if (!ME_UUID || !uuidOf(a)) return oDrop.apply(this, arguments);
    var other = uuidOf(a); NET_AT = Date.now(); oDrop.apply(this, arguments);
    sb.from('connections').delete().in('requester', [ME_UUID, other]).in('addressee', [ME_UUID, other]).eq('status', 'accepted').select('id')   /* the pair, either direction */
      .then(function (r) { if (r.error || !(r.data || []).length) { NET_AT = 0; window.CONN_STATE[a] = 'connected'; if (window.netRefresh) window.netRefresh(); toastErr(r.error || { message: 'This connection could not be removed' }); } });
  };
  /* S-11 following a person (person_followers, 0030) */
  var oFollow = window.followUser;
  if (oFollow) window.followUser = function (a) {
    if (!ME_UUID || !uuidOf(a)) return oFollow.apply(this, arguments);
    var F = window.FOLLOWS, before = !!F[a], other = uuidOf(a); oFollow.apply(this, arguments);
    var op = before ? sb.from('person_followers').delete().eq('user_id', ME_UUID).eq('person_id', other) : sb.from('person_followers').insert({ person_id: other, user_id: ME_UUID });
    op.then(function (r) { if (r.error && !(r.error.code === '23505' && !before)) { F[a] = before; if (window.netRefresh) window.netRefresh(); toastErr(r.error); } });
  };
  async function loadPersonFollows() {
    var F = window.FOLLOWS; if (!F) return; var rows = [], from = 0;
    for (;;) { var r = await sb.from('person_followers').select('person_id').eq('user_id', ME_UUID).order('person_id').range(from, from + 999);
      if (r.error) throw r.error; rows = rows.concat(r.data || []); if ((r.data || []).length < 1000) break; from += 1000; }
    wipe(F); rows.forEach(function (x) { F[aid(x.person_id)] = true; });
  }
  /* J-SOCIAL-34 a dismissed suggestion stays dismissed (people_dismissed, 0030) */
  var oDismiss = window.dismissSuggestion;
  if (oDismiss) window.dismissSuggestion = function (a) {
    if (!ME_UUID || !uuidOf(a)) return oDismiss.apply(this, arguments);
    oDismiss.apply(this, arguments);
    sb.from('people_dismissed').insert({ person_id: uuidOf(a), user_id: ME_UUID }).then(function (r) { if (r.error && r.error.code !== '23505') { delete window.SUGG_HIDDEN[a]; if (window.netRefresh) window.netRefresh(); toastErr(r.error); } });
  };
  window.markNotifRead = function (id) { var n = (window.NOTIFS || []).find(function (x) { return x.id === id; }), was = n && n.read; o3.read(id); badges();
    if (ME_UUID && n && !was) sb.from('notifications').update({ read: true }).eq('id', id).then(function (r) { if (r.error) toastErr(r.error); });
    if (n && n.pid && (n.type === 'like' || n.type === 'comment') && window.dxOpenPost) window.dxOpenPost(n.pid, { comments: n.type === 'comment' }); };   /* a reaction or comment notification opens its post */
  if (o3.readAll) window.markAllRead = function () { o3.readAll(); badges(); if (ME_UUID) sb.from('notifications').update({ read: true }).eq('user_id', ME_UUID).eq('read', false).then(function (r) { if (r.error) toastErr(r.error); }); };
  if (o3.clear) window.clearAllNotifs = function () {            /* keeps the interface's Undo: delete only when the list is really emptied */
    var ids = NOTIF_IDS.slice(); o3.clear(); badges(); if (!ME_UUID || !ids.length) return;
    var waited = 0, t = setInterval(function () { waited += 400; var gone = !(window.NOTIFS || []).length; if (!gone && waited < 15000) return; clearInterval(t); if (!gone) return;
      sb.from('notifications').delete().eq('user_id', ME_UUID).in('id', ids).then(function (r) { if (r.error) toastErr(r.error); }); }, 400);
  };
  /* badges right after sign-in */
  var hydrateB2 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateB2(uid); loadConnections().then(loadNotifs).catch(function (e) { console.error(e); }); loadPersonFollows().catch(function (e) { console.error(e); }); return me; };
  Object.assign(window.dxLive, { uuidOf: uuidOf, aid: aid, loadNotifs: loadNotifs, loadConnections: loadConnections, loadPersonFollows: loadPersonFollows, version: 'B3' });

  /* ═══════════════ B4 — messages + live updates ═══════════════
     The approved messages page is fixed markup; its own first thread row is the template for real conversations,
     and bubbles use the page's own markup. Demo filler (seeded messages, simulated replies) never runs in the live app. */
  var MX = { tpl: null, convs: [], open: null, lastMsg: 0, lastNotif: 0, timer: null, rt: false, to: null };
  var MXP = { mute: {}, block: {}, at: 0 };                              /* my muted and blocked partners (uuid → 1); muted ones are not counted */
  function shortAgo(ts) { var s = (Date.now() - new Date(ts).getTime()) / 1000; if (s < 60) return 'now'; if (s < 3600) return Math.floor(s / 60) + 'm'; if (s < 86400) return Math.floor(s / 3600) + 'h'; return Math.floor(s / 86400) + 'd'; }
  function rowTheirs(u, text, time, att) { return '<div class="msg-row mx-theirs"><div class="av" style="background:' + u.color + ';width:28px;height:28px;font-size:10px;flex-shrink:0">' + esc2(u.initials) + '</div><div><div class="mx-bubble mx-theirs">' + attHtml(att) + esc2(text) + '</div><div class="mx-bubble-time">' + time + '</div></div></div>'; }
  /* my messages carry their state as the demo shows it: ✓ sent, ✓✓ seen (read_at set by the receiver) — J-SOCIAL-38 */
  function stMark(seen) { return ' <span class="mx-st" title="' + (seen ? 'Seen' : 'Sent') + '" aria-label="' + (seen ? 'Seen' : 'Sent') + '" style="color:' + (seen ? '#1a56db' : 'inherit') + '">' + (seen ? '✓✓' : '✓') + '</span>'; }
  function rowMine(text, time, att, local, st) { return '<div class="msg-row mx-mine"' + (st && st.id ? ' data-mid="' + st.id + '"' : '') + '><div><div class="mx-bubble mx-mine" style="white-space:pre-wrap">' + attHtml(att, local) + esc2(text) + '</div><div class="mx-bubble-time" style="text-align:right">' + time + (st ? stMark(st.seen) : '') + '</div></div></div>'; }
  function markSent(bubble, row) { if (!bubble || !row) return; bubble.dataset.mid = row.id; var tm = bubble.querySelector('.mx-bubble-time'); if (tm && !tm.querySelector('.mx-st')) tm.insertAdjacentHTML('beforeend', stMark(!!row.read_at)); }
  /* the open conversation: my messages the other person has read since turn to ✓✓ (on each tick while Messages is open) */
  async function refreshSeen() {
    var area = document.getElementById('messagesArea'), a = MX.open, partner = a && uuidOf(a); if (!area || !partner) return;
    var un = [].slice.call(area.querySelectorAll('.msg-row.mx-mine[data-mid]')).filter(function (r) { var m = r.querySelector('.mx-st'); return m && m.title !== 'Seen'; }); if (!un.length) return;
    var r = await sb.from('messages').select('id').eq('sender_id', ME_UUID).eq('receiver_id', partner).not('read_at', 'is', null).gte('id', +un[0].dataset.mid).limit(200);
    if (r.error || MX.open !== a) return; var seen = {}; (r.data || []).forEach(function (x) { seen[x.id] = 1; });
    un.forEach(function (row) { if (seen[row.dataset.mid]) { var m = row.querySelector('.mx-st'); if (m) m.outerHTML = stMark(true); } });
  }
  function threadFor(c) {
    var a = aid(c.partner), u = window.U(a), key = 'u' + a, box = document.createElement('div'); box.innerHTML = MX.tpl; var el = box.firstElementChild;
    el.className = 'mx-thread' + (c.unread ? ' mx-unread' : ''); el.dataset.name = (c.name || '').toLowerCase(); el.dataset.tags = 'deals'; el.dataset.person = key; el.dataset.uid = a;
    el.setAttribute('onclick', "mxOpenThread(this,'" + key + "')");
    var av = el.querySelector('.av'); if (av) { av.style.background = u.color; av.childNodes[0].textContent = u.initials; var dot = av.querySelector('.online-dot'); if (dot) dot.remove(); }
    var nm = el.querySelector('.t-name'); if (nm) nm.innerHTML = esc2(c.name || 'Member') + (c.verified ? ' <span style="color:#1a56db;font-size:10px">✓</span>' : '');
    var tm = el.querySelector('.t-time'); if (tm) tm.textContent = shortAgo(c.last_at);
    var pv = el.querySelector('.t-preview'); if (pv) { pv.textContent = (c.last_from_me ? 'You: ' : '') + (c.last_body || ''); pv.classList.toggle('unread-text', !!c.unread); }
    var tag = el.querySelector('.t-context-tag'); if (tag) tag.remove();
    var bd = el.querySelector('.t-badge'); if (c.unread) { if (!bd) { bd = document.createElement('div'); bd.className = 't-badge'; el.appendChild(bd); } bd.textContent = c.unread; } else if (bd) bd.remove();
    return el;
  }
  async function loadConvs() { var q = await Promise.all([sb.rpc('my_conversations', { p_limit: 50 }), loadPrefs().catch(function (e) { console.error(e); })]), r = q[0]; if (r.error) throw r.error;
    MX.convs = r.data || []; MX.convs.forEach(function (c) { putUser({ id: c.partner, name: c.name, headline: c.headline, verified: c.verified, avatar_url: c.avatar_url }); }); msgBadge(); return MX.convs; }
  /* the Messages count everywhere it shows — top bar, phone bar, sidebar (the sidebar is rebuilt from SB_NAV) — never the
     demo's fixed "5" (J-SOCIAL-38) */
  function msgBadge() { var n = MX.convs.reduce(function (t, c) { return t + (MXP.mute[c.partner] ? 0 : (c.unread || 0)); }, 0);
    (window.SB_NAV || []).forEach(function (x) { if (x.page === 'messages') x.badge = n; });
    var sl = document.getElementById('snl-messages'), sb2 = sl && sl.querySelector('.nl-badge');
    if (sl && n && !sb2) { sl.insertAdjacentHTML('beforeend', '<span class="nl-badge"></span>'); sb2 = sl.querySelector('.nl-badge'); }
    [document.getElementById('nb-msg'), document.querySelector('#mb-messages .mb-badge'), sb2].forEach(function (e) { if (e) { e.textContent = n; e.style.display = n ? '' : 'none'; } }); }
  function listEl() { return document.getElementById('threadList'); }
  function drawThreads() {
    var list = listEl(); if (!list || !MX.tpl) return; list.querySelectorAll('.mx-thread').forEach(function (t) { t.remove(); });
    var empty = list.querySelector('.dx-mx-empty'); if (empty) empty.remove();
    if (!MX.convs.length) list.insertAdjacentHTML('beforeend', '<div class="dx-mx-empty" style="padding:28px 16px;text-align:center;color:#65676b;font-size:13px">No conversations yet.<br>Open someone\'s profile and press Message.</div>');
    MX.convs.forEach(function (c) { list.appendChild(threadFor(c)); });
    if (window.mxPaintPrefs) window.mxPaintPrefs();                       /* 🔇 and blocked marks on the redrawn list */
    if (window.mxShowSearch) window.mxShowSearch();                       /* and the search typed, if any */
  }
  async function openLive(el, key) {
    var a = +String(key).slice(1), partner = uuidOf(a), area = document.getElementById('messagesArea'); if (!partner || !area) return;
    MX.open = a; area.innerHTML = '<div class="msg-date-divider">Loading…</div>';
    var r = await sb.rpc('conversation_messages', { p_partner: partner, p_limit: 50 }); if (r.error) { toastErr(r.error); return; }
    if (MX.open !== a) return;
    var u = window.U(a), rows = (r.data || []).slice().reverse();
    area.innerHTML = rows.length ? rows.map(function (m) { var t = m.attachment ? (m.body || '') : (m.body || '📷 Photo'); return m.sender_id === ME_UUID ? rowMine(t, shortAgo(m.created_at), m.attachment, null, { id: m.id, seen: !!m.read_at }) : rowTheirs(u, t, shortAgo(m.created_at), m.attachment); }).join('')
      : '<div class="msg-date-divider">Start the conversation with ' + esc2(u.name) + '</div>';
    area.scrollTop = area.scrollHeight; signAll(area); if (window.mxSearchJump) window.mxSearchJump();
    rows.forEach(function (m) { if (m.id > MX.lastMsg && m.receiver_id === ME_UUID) MX.lastMsg = m.id; });
    var c = MX.convs.find(function (x) { return aid(x.partner) === a; });
    if (c && c.unread) { c.unread = 0; msgBadge(); sb.from('messages').update({ read_at: new Date().toISOString() }).eq('sender_id', partner).eq('receiver_id', ME_UUID).is('read_at', null).then(function (x) { if (x.error) toastErr(x.error); }); }
  }

  async function sendAttachments(partner, atts, text, area) {
    for (var i = 0; i < atts.length; i++) { var x = atts[i], b; try { b = await blobOf(x.file || x.url); } catch (e) { toastErr(e); continue; }
      var ext = EXT[b.type] || safeExt(x.name), path = ME_UUID + '/' + partner + '/' + rid() + '.' + ext, kind = x.kind === 'photo' ? 'photo' : 'file';
      var local = URL.createObjectURL(b), att = { path: path, name: String(x.name || 'file').slice(0, 200), size: b.size, kind: kind }, body = i === 0 ? (text || '') : '';
      area.insertAdjacentHTML('beforeend', rowMine(body, 'Sending…', att, local)); var bubble = area.lastElementChild; area.scrollTop = area.scrollHeight;
      var up = await sb.storage.from('message-media').upload(path, b, { contentType: b.type || 'application/octet-stream' });
      if (up.error) { bubble.remove(); toastErr(up.error); continue; }
      var r = await sb.from('messages').insert({ sender_id: ME_UUID, receiver_id: partner, body: body || (kind === 'file' ? '📎 ' + x.name : ''), image_url: kind === 'photo' ? path : null, attachment: att }).select('id,read_at').single();
      if (r.error) { bubble.remove(); toastErr(r.error); continue; }
      var tm = bubble.querySelector('.mx-bubble-time'); if (tm) tm.textContent = 'Just now'; markSent(bubble, r.data); }
  }
  function liveSend() {
    var input = document.getElementById('composeInput'), text = input ? input.value.trim() : '', area = document.getElementById('messagesArea');
    var atts = (window.pendingAttachments || []).slice();
    if ((!text && !atts.length) || !MX.open || !area) return;
    var partner = uuidOf(MX.open); input.value = '';
    if (atts.length) { window.pendingAttachments.length = 0; if (typeof window.renderAttachPreviews === 'function') window.renderAttachPreviews(); sendAttachments(partner, atts, text, area); if (!text) return; text = ''; return; }
    area.insertAdjacentHTML('beforeend', rowMine(text, 'Just now')); var bubble = area.lastElementChild; area.scrollTop = area.scrollHeight;
    var th = listEl() && listEl().querySelector('.mx-thread[data-person="u' + MX.open + '"]');
    if (th) { var pv = th.querySelector('.t-preview'); if (pv) { pv.textContent = 'You: ' + text; pv.classList.remove('unread-text'); } var tm = th.querySelector('.t-time'); if (tm) tm.textContent = 'now'; listEl().insertBefore(th, listEl().firstElementChild); }
    sb.from('messages').insert({ sender_id: ME_UUID, receiver_id: partner, body: text }).select().single().then(function (r) {
      if (r.error) { if (bubble) bubble.remove(); input.value = text; toastErr(r.error); return; }
      markSent(bubble, r.data);
      var c = MX.convs.find(function (x) { return x.partner === partner; });
      if (c) { c.last_body = text; c.last_at = r.data.created_at; c.last_from_me = true; } else MX.convs.unshift({ partner: partner, name: window.U(MX.open).name, last_body: text, last_at: r.data.created_at, last_from_me: true, unread: 0 });
    });
  }
  var origRenderMessages = window.renderMessages;
  window.renderMessages = function (c) {
    var r = origRenderMessages.apply(this, arguments); if (!ME_UUID) return r;
    var list = listEl(), first = list && list.querySelector('.mx-thread'); if (!first) return r;
    if (!MX.tpl) MX.tpl = first.outerHTML;
    var area = document.getElementById('messagesArea'); if (area) area.innerHTML = '<div class="msg-date-divider">Loading your conversations…</div>';
    list.querySelectorAll('.mx-thread').forEach(function (t) { t.remove(); });
    var head = document.querySelector('.chat-head .ch-name'); if (head) head.textContent = '';
    var banner = document.querySelector('.context-banner'); if (banner) banner.style.display = 'none';
    var online = document.querySelector('#mx .online-strip'); if (online) online.style.display = 'none';   /* demo people: there is no presence in the live app yet */
    var cb = document.querySelector('.chat-head'); if (cb) cb.style.visibility = 'hidden';
    loadConvs().then(function () {
      if (document.body.getAttribute('data-page') !== 'messages') return;
      var want = MX.to; MX.to = null;
      if (want && !MX.convs.some(function (x) { return aid(x.partner) === want; })) { var u = window.U(want); MX.convs.unshift({ partner: uuidOf(want), name: u.name, verified: u.verified, last_body: '', last_at: new Date().toISOString(), last_from_me: false, unread: 0 }); }
      drawThreads();
      /* without a person asked for, the newest conversation already read opens: an unread one stays unread (and counted)
         until the member opens it (J-SOCIAL-38) */
      var target = want ? listEl().querySelector('.mx-thread[data-person="u' + want + '"]') : listEl().querySelector('.mx-thread:not(.mx-unread)');
      if (target) { if (cb) cb.style.visibility = ''; window.mxOpenThread(target, target.dataset.person);
        if (want) { var mx = document.getElementById('mx'); if (mx) mx.classList.remove('mx-list'); } }   /* phones: Message opens the conversation, not the list */
      else if (area) area.innerHTML = '<div class="msg-date-divider">' + (MX.convs.length ? 'Choose a conversation' : 'No conversations yet') + '</div>';
    }).catch(toastErr);
    return r;
  };
  /* mxComplete (inside the approved page) defines mxOpenThread/sendMessage each time the page renders: wrap them after it does */
  var gotoB3 = window.goto;
  window.goto = function (page) {
    var r = gotoB3.apply(this, arguments);
    if (page === 'messages' && ME_UUID) {
      var mo = window.mxOpenThread;
      if (mo && !mo.__live) { window.mxOpenThread = function (el, key) { var x = mo.apply(this, arguments); if (/^u\d+$/.test(String(key))) { var cb = document.querySelector('.chat-head'); if (cb) cb.style.visibility = ''; openLive(el, key); } return x; }; window.mxOpenThread.__live = true; }
      window.sendMessage = liveSend;
    }
    return r;
  };
  var origMessageUser = window.messageUser;
  window.messageUser = function (a) { if (ME_UUID && uuidOf(+a)) { MX.to = +a; window.__mxTo = null; window.goto('messages'); return; } return origMessageUser.apply(this, arguments); };

  /* ✎ New message (S-03): the picker offers your conversations, your connections and the members whose name matches what you
     type (with headline and company, so two people with one name can be told apart); Send goes to the one member chosen and
     opens that conversation — never the conversation that happened to be open. A name nobody has, or several people have,
     is not sent. */
  var NM = { people: {}, map: {}, t: null };
  function nmLike(x) { return String(x).replace(/[\\%_]/g, '\\$&'); }
  function nmAdd(p) { if (p && p.id && p.id !== ME_UUID) NM.people[p.id] = { id: p.id, name: txt(p.name || 'Member'), headline: txt(p.headline), company: txt(p.company) }; }
  function nmOptions() {                                       /* option values are unique: a shared name carries the company */
    var all = Object.keys(NM.people).map(function (k) { return NM.people[k]; }), n = {}; NM.map = {};
    all.forEach(function (p) { var k = p.name.toLowerCase(); n[k] = (n[k] || 0) + 1; });
    return all.map(function (p) {
      var v = n[p.name.toLowerCase()] > 1 ? p.name + ' · ' + (p.company || p.headline.split('|')[0].trim() || p.id.slice(0, 8)) : p.name;
      NM.map[v.toLowerCase()] = p.id; return { name: v, label: [p.headline.split('|')[0].trim(), p.company].filter(Boolean).join(' · ').slice(0, 90) };
    });
  }
  function nmPaint() { var dl = document.getElementById('nmList'); if (!dl) return;
    dl.innerHTML = nmOptions().map(function (o) { return '<option value="' + esc2(o.name) + '"' + (o.label ? ' label="' + esc2(o.label) + '"' : '') + '>'; }).join(''); }
  window.dxMxPeople = function () {
    NM.people = {}; if (!ME_UUID) return [];
    MX.convs.forEach(function (c) { var u = window.U(aid(c.partner)); nmAdd({ id: c.partner, name: c.name || u.name, headline: c.headline || u.headline, company: u.company }); });
    Object.keys(window.CONN_STATE || {}).forEach(function (k) { if (window.CONN_STATE[k] !== 'connected' || !uuidOf(+k)) return; var u = window.U(+k); nmAdd({ id: uuidOf(+k), name: u.name, headline: u.headline, company: u.company }); });
    return nmOptions();
  };
  async function nmSearch(q) {
    var r = await sb.from('profiles').select(PCOLS).ilike('name', '%' + nmLike(q.split(' · ')[0]) + '%').neq('id', ME_UUID).order('name').limit(12);
    if (r.error) throw r.error; (r.data || []).forEach(function (p) { putUser(p); nmAdd(p); }); return r.data || [];
  }
  document.addEventListener('input', function (e) {
    if (!ME_UUID || !e.target || e.target.id !== 'nmTo') return;
    var q = e.target.value.trim(); clearTimeout(NM.t); if (q.length < 2 || q.length > 80 || NM.map[q.toLowerCase()]) return;
    NM.t = setTimeout(function () { nmSearch(q).then(nmPaint, function (err) { console.error(err); }); }, 200);
  }, true);
  async function nmResolve(to) {
    var id = NM.map[to.toLowerCase()]; if (id) return { id: id };
    if (to.length <= 200) {
      var m = /^(.+?) · (.+)$/.exec(to), name = m ? m[1].trim() : to, which = m ? m[2].trim().toLowerCase() : '';   /* "Name · Company" as the picker shows it */
      var r = await sb.from('profiles').select(PCOLS).ilike('name', nmLike(name)).neq('id', ME_UUID).limit(m ? 50 : 5); if (r.error) throw r.error;
      var d = (r.data || []).filter(function (p) { return !which || txt(p.company).toLowerCase() === which || txt(p.headline).split('|')[0].trim().toLowerCase() === which || p.id.slice(0, 8) === which; });
      d.forEach(function (p) { putUser(p); nmAdd(p); });
      if (d.length === 1) return { id: d[0].id };
      if (d.length > 1) { nmPaint(); return { err: 'Several members are called ' + to + ' — choose one from the list' }; }
    }
    return { err: 'No member called ' + to + ' — choose someone from the list' };
  }
  window.dxMxNew = function (to, text, box, close) {
    if (!ME_UUID) return false;
    var toEl = box.querySelector('#nmTo'), ok = box.querySelector('[data-a=ok]'); if (ok) { if (ok.disabled) return false; ok.disabled = true; }
    function done() { if (ok) ok.disabled = false; }
    nmResolve(to).then(function (who) {
      if (who.err) { done(); if (toEl) toEl.classList.add('dbk-err'); window.DBK.toast(who.err); return; }
      return sb.from('messages').insert({ sender_id: ME_UUID, receiver_id: who.id, body: text }).select().single().then(function (r) {
        done(); if (r.error) { toastErr(r.error); return; }
        close(); var a = aid(who.id), u = window.U(a), i = MX.convs.findIndex(function (c) { return c.partner === who.id; });
        var c = i >= 0 ? MX.convs.splice(i, 1)[0] : { partner: who.id, name: u.name, verified: u.verified, unread: 0 };
        c.last_body = text; c.last_at = r.data.created_at; c.last_from_me = true; MX.convs.unshift(c);
        if (r.data.id > MX.lastMsg && r.data.receiver_id === ME_UUID) MX.lastMsg = r.data.id;
        if (document.body.getAttribute('data-page') !== 'messages') { MX.to = a; window.goto('messages'); return; }
        drawThreads(); var t = listEl() && listEl().querySelector('.mx-thread[data-person="u' + a + '"]'); if (t) window.mxOpenThread(t, t.dataset.person);
        var mx = document.getElementById('mx'); if (mx) mx.classList.remove('mx-list');                   /* phones: show the conversation */
      });
    }).catch(function (e) { done(); toastErr(e); });
    return false;
  };

  /* 🔍 search what was said (J-SOCIAL-39): my messages that contain the words (the database only shows me my own), as
     conversation keys; a person found this way who is not among the loaded conversations joins the list */
  window.dxMxSearch = async function (q) {
    if (!ME_UUID) return null; var me = ME_UUID;
    var r = await sb.from('messages').select('sender_id,receiver_id,body,created_at').or('sender_id.eq.' + ME_UUID + ',receiver_id.eq.' + ME_UUID)
      .ilike('body', '%' + nmLike(String(q).slice(0, 80)) + '%').order('id', { ascending: false }).limit(100);
    if (r.error || me !== ME_UUID) { if (r.error) console.error(r.error); return null; }
    var hits = {}, missing = {};
    r.data.forEach(function (m) { var p = m.sender_id === ME_UUID ? m.receiver_id : m.sender_id;
      if (!MX.convs.some(function (c) { return c.partner === p; }) && !missing[p]) missing[p] = m; });
    var ids = Object.keys(missing);
    if (ids.length) {
      var pr = await sb.from('profiles').select(PCOLS).in('id', ids.slice(0, 50)); if (me !== ME_UUID) return null;
      (pr.data || []).forEach(function (p) { putUser(p); var m = missing[p.id];
        MX.convs.push({ partner: p.id, name: p.name, verified: p.verified, last_body: m.body, last_at: m.created_at, last_from_me: m.sender_id === ME_UUID, unread: 0 }); });
      if ((pr.data || []).length && document.body.getAttribute('data-page') === 'messages') { var keep = MX.open; drawThreads(); if (keep) { var t = listEl() && listEl().querySelector('.mx-thread[data-person="u' + keep + '"]'); if (t) t.classList.add('active'); } }
    }
    r.data.forEach(function (m) { hits['u' + aid(m.sender_id === ME_UUID ? m.receiver_id : m.sender_id)] = 1; });
    return hits;
  };

  /* ⋯ Mute / Block / Report in a conversation (J-SOCIAL-40) ↔ conversation_mutes, user_blocks, message_reports (0031).
     Mute keeps the messages but leaves them out of the Messages badge and the "New message" notice; Block makes the database
     refuse messages either way; a report copies the reported person's last messages to me (the database does that, not the
     browser) for Admin → Review. */
  async function loadPrefs() {
    var me = ME_UUID, q = await Promise.all([sb.from('conversation_mutes').select('partner').eq('owner', ME_UUID).limit(1000),
                                             sb.from('user_blocks').select('blocked').eq('blocker', ME_UUID).limit(1000)]);
    if (me !== ME_UUID) return; if (q[0].error) throw q[0].error; if (q[1].error) throw q[1].error;
    MXP.mute = {}; MXP.block = {}; q[0].data.forEach(function (x) { MXP.mute[x.partner] = 1; }); q[1].data.forEach(function (x) { MXP.block[x.blocked] = 1; }); MXP.at = Date.now();
  }
  function prefPartner(key) { return /^u\d+$/.test(String(key)) ? uuidOf(+String(key).slice(1)) : null; }
  window.dxMxPrefs = {
    get: function (key) { var p = prefPartner(key); if (!ME_UUID || !p) return {}; return { muted: !!MXP.mute[p], blocked: !!MXP.block[p] }; },
    set: async function (key, what, on) {
      var p = prefPartner(key); if (!ME_UUID || !p) throw new Error('Open a conversation first');
      var t = what === 'muted' ? ['conversation_mutes', 'owner', 'partner', MXP.mute] : ['user_blocks', 'blocker', 'blocked', MXP.block], row = {}, r;
      row[t[1]] = ME_UUID; row[t[2]] = p;
      r = on ? await sb.from(t[0]).upsert(row, { onConflict: t[1] + ',' + t[2], ignoreDuplicates: true }) : await sb.from(t[0]).delete().eq(t[1], ME_UUID).eq(t[2], p);
      if (r.error) throw new Error(friendly(r.error));
      if (on) t[3][p] = 1; else delete t[3][p]; msgBadge();
    },
    report: async function (key, reason, details) {
      var p = prefPartner(key); if (!ME_UUID || !p) throw new Error('Open a conversation first');
      var r = await sb.from('message_reports').insert({ reporter: ME_UUID, reported: p, reason: String(reason || 'Other').slice(0, 120), details: details ? String(details).slice(0, 2000) : null });
      if (r.error) throw new Error(friendly(r.error));
    }
  };
  onReset(function () { MXP.mute = {}; MXP.block = {}; MXP.at = 0; });

  /* live updates: one code path (tick) — triggered by Supabase Realtime when available, and by a gentle timer as a safety net.
     One tick at a time (Realtime events, the timer and a returning tab share the run in progress), each incoming message is shown
     once, and only what a notification is about is reloaded (F-51). */
  var TICK = null, SHOWN = {};
  function tick() { if (TICK) return TICK; TICK = tickOnce().finally(function () { TICK = null; }); return TICK; }
  async function tickOnce() {
    if (!ME_UUID || document.hidden) return false;
    var me = ME_UUID, got = false, r = await sb.rpc('new_messages', { p_after: MX.lastMsg });
    if (me !== ME_UUID) return false;                                            /* signed out meanwhile */
    var rows = (!r.error && r.data || []).filter(function (m) { return m.id > MX.lastMsg && !SHOWN[m.id]; });
    if (rows.length) {
      got = true; var onMx = document.body.getAttribute('data-page') === 'messages', fresh = [];
      rows.forEach(function (m) { MX.lastMsg = Math.max(MX.lastMsg, m.id); SHOWN[m.id] = 1; var a = aid(m.sender_id);
        if (onMx && MX.open === a) { var area = document.getElementById('messagesArea'); if (area) { area.insertAdjacentHTML('beforeend', rowTheirs(window.U(a), m.attachment ? (m.body || '') : (m.body || '📷 Photo'), 'now', m.attachment)); area.scrollTop = area.scrollHeight; signAll(area); }
          sb.from('messages').update({ read_at: new Date().toISOString() }).eq('id', m.id).then(function () {}); }
        else fresh.push(m); });
      await loadConvs(); if (onMx) { var keep = MX.open; drawThreads(); if (keep) { var t = listEl() && listEl().querySelector('.mx-thread[data-person="u' + keep + '"]'); if (t) t.classList.add('active'); } }
      fresh = fresh.filter(function (m) { return !MXP.mute[m.sender_id]; });   /* muted: no notice */
      if (fresh.length && !onMx && typeof window.toast === 'function') window.toast('💬 New message from ' + window.U(aid(fresh[fresh.length - 1].sender_id)).name);
    }
    if (document.body.getAttribute('data-page') === 'messages' && MX.open) await refreshSeen().catch(function () {});
    var n = await sb.from('notifications').select('id,type').eq('user_id', ME_UUID).gt('id', MX.lastNotif).order('id', { ascending: false }).limit(50);
    if (!n.error && (n.data || []).length && me === ME_UUID) {
      got = true; MX.lastNotif = n.data[0].id; var types = n.data.map(function (x) { return x.type; });
      if (types.some(function (t) { return /^connection/.test(t); })) await loadConnections();
      await loadNotifs();
      if (types.indexOf('deal') >= 0 && window.dxLive.loadDeals) await window.dxLive.loadDeals().catch(function () {});
      var pg = document.body.getAttribute('data-page'); if (pg === 'notifs' || pg === 'notifications') origGoto(pg);
    }
    return got;
  }
  /* polling: 5 s on Messages; elsewhere 20 s, slowing to 60 s while nothing arrives; 60 s with Realtime; nothing in a hidden tab */
  function schedule() { clearTimeout(MX.timer); if (!ME_UUID) return;
    var every = MX.rt ? 60000 : (document.body.getAttribute('data-page') === 'messages' ? 5000 : Math.min(60000, 20000 * Math.pow(1.5, MX.idle || 0)));
    MX.timer = setTimeout(function () { if (document.hidden) return schedule(); tick().then(function (b) { MX.idle = b ? 0 : (MX.idle || 0) + 1; }, function (e) { console.error(e); }).then(schedule); }, every); }
  async function startLive() {
    var me = ME_UUID, a = await sb.rpc('my_last_message_id');
    if (a.error) { var x = await sb.from('messages').select('id').eq('receiver_id', ME_UUID).order('id', { ascending: false }).limit(1); a = { data: x.data && x.data[0] ? x.data[0].id : 0 }; }
    var b = await sb.from('notifications').select('id').eq('user_id', ME_UUID).order('id', { ascending: false }).limit(1);
    if (me !== ME_UUID) return;
    MX.lastMsg = +a.data || 0; MX.lastNotif = b.data && b.data[0] ? b.data[0].id : 0; MX.idle = 0;
    loadConvs().catch(function () {});
    if (CFG.realtime !== false && sb.channel) {
      try { sb.channel('dx-' + ME_UUID)
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'messages', filter: 'receiver_id=eq.' + ME_UUID }, function () { tick(); })
        .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'notifications', filter: 'user_id=eq.' + ME_UUID }, function () { tick(); })
        .subscribe(function (st) { MX.rt = st === 'SUBSCRIBED'; }); } catch (e) { MX.rt = false; }
    }
    schedule();
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden && ME_UUID) { MX.idle = 0; tick().catch(function () {}); } });
  var hydrateB3 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateB3(uid); startLive().catch(function (e) { console.error(e); }); return me; };
  onReset(function () { clearTimeout(MX.timer); try { sb.removeAllChannels && sb.removeAllChannels(); } catch (e) {} MX.convs = []; MX.open = null; MX.to = null; MX.lastMsg = 0; MX.lastNotif = 0; MX.rt = false; MX.idle = 0; SHOWN = {}; msgBadge(); });
  /* messages written outside the Messages page — the chat dock and the listing / job buttons — are real messages (F-22).
     The person is the one whose card opened the window (the last click outside a window or the dock), or the one real member
     with the name the interface shows; never a guess between two people with the same name. */
  var LASTUID = { a: 0, at: 0 };
  document.addEventListener('click', function (e) { var t = e.target; if (!t.closest || t.closest('.dbk-ov, #dxDock')) return;
    var c = t.closest('[data-uid]'); LASTUID = c && +c.dataset.uid > 1000 ? { a: +c.dataset.uid, at: Date.now() } : { a: 0, at: 0 }; }, true);
  function lastCard() { return LASTUID.a && Date.now() - LASTUID.at < 120000 ? LASTUID.a : 0; }
  /* a chat window a company page's "Message" opened (B-05): its name → the company; what is written there goes to company_message(),
     which delivers it to the person who answers for that company (unless a person's card was clicked since) */
  var DOCKTO = {};
  function dockCompany(name) { var c = DOCKTO[name]; return c && !(LASTUID.at > c.at) ? c : null; }
  onReset(function () { LASTUID = { a: 0, at: 0 }; DOCKTO = {}; });         /* local numbers start again for the next person */
  function personByName(name) { var n = String(name || '').trim().toLowerCase(); if (!n) return null;
    var hits = (window.USERS || []).filter(function (x) { return x.id > 1000 && x !== window.ME && String(x.name || '').trim().toLowerCase() === n; });
    var u = hits.length === 1 ? hits[0] : hits.find(function (x) { return x.id === lastCard(); }); return u ? uuidOf(u.id) : null; }
  function unreachable(name) { setTimeout(function () { if (typeof window.toast === 'function') window.toast('Could not send to ' + (name || 'this person') + ' — open their profile and press Message'); }, 0); }
  function sendText(to, body) { return sb.from('messages').insert({ sender_id: ME_UUID, receiver_id: to, body: body }).then(function (r) { if (r.error) throw r.error; }); }
  function dockMessage(d) {
    if (d == null) return !!ME_UUID;                                      /* the dock asks whether it can send for real */
    var co = ME_UUID && dockCompany(d.to);
    if (co) { sb.rpc('company_message', { p_company: co.company, p_body: String(d.text || '') }).then(function (r) { if (r.error) throw r.error; }).catch(toastErr); return true; }
    var to = ME_UUID && personByName(d.to); if (!to || to === ME_UUID) { unreachable(d.to); return false; }
    sendText(to, String(d.text || '')).catch(toastErr); return true;
  }
  if (window.DBK) window.DBK.sendToOutbox = function (item) {             /* live: never the browser's outbox */
    item = item || {}; if (!ME_UUID) return;
    var to = personByName(item.to) || (lastCard() ? uuidOf(lastCard()) : null);
    if (!to || to === ME_UUID) { unreachable(item.to); return; }
    sendText(to, (item.ctx ? 'Re: ' + item.ctx + '\n' : '') + (item.price ? 'Price: ' + item.price + '\n' : '') + String(item.text || '')).catch(toastErr);
  };
  Object.assign(window.dxLive, { tick: tick, loadConvs: loadConvs, version: 'B4' });

  /* ═══════════════ C1 — companies: directory, company pages, my companies, create, page edits, verification ═══════════════
     The demo's store() and company list have data hooks (inert in the demo); here they read and write the database.
     Right after sign-in only my own pages load; the directory loads, a page at a time, when the Companies page opens (F-05). */
  var CO = { byId: {}, raw: {}, alias: {}, reopen: null, loaded: false, at: 0, loading: null, roles: {}, mine: false, mineP: null, sitesAt: {}, track: {}, trackAt: {}, seq: {} };
  var TYPE = { factory: 'Factory', warehouse: 'Warehouse', lab: 'Laboratory', office: 'Office', head_office: 'Head office' };
  var ROLE = { registration_holder: 'Registration holder', manufacturer: 'Manufacturer', supplier: 'Supplier' };
  function ym(d) { return d ? String(d).slice(0, 7) : ''; }
  function coFrom(c) { var pr = c.profile || {}, sect = (c.sectors || []).map(txt), role = CO.roles[c.id];
    var owns = !!c.mine && (role ? role === 'owner' || role === 'admin' : !CO.mine);              /* plain members (sales, hr…) do not manage the page (F-121) */
    var vip = c.plan === 'vip' && (!c.vip_until || new Date(c.vip_until) > Date.now());          /* a VIP plan that ran out is free */
    return { slug: c.slug, registry: txt(c.registry), plan: vip ? 'vip' : 'free', licensed: !!c.licensed, status: c.status, name: txt(c.name), name_ar: txt(c.name_ar),
      owner: owns ? window.ME.id : null, color: hexOr(pr.color, c.id), sector: sect[0] || 'Company', sectors: sect, city: txt(c.city), gov: txt(c.governorate),
      founded: c.founded || '', employees: txt(c.employees), verified: c.status === 'verified', level: '', rating: (c.track && c.track.rating) ? +c.track.rating : 0, reviews: (c.track && +c.track.reviews) || 0, reply: '—',
      tagline: txt(c.tagline), about: txt(c.bio), certs: (c.certs || []).map(txt), phone: tel(c.phone), email: txt(c.email), whatsapp: tel(c.whatsapp), website: safeUrl(c.website),
      address: txt(pr.address || c.location), hours: txt(c.hours), services: (pr.services || []).map(txt), jobs: [], team: [], logo: safeUrl(c.logo_url) || null, cover: safeUrl(pr.cover) || null,
      products: (c.products || []).map(function (p) { return { id: 'p' + String(p.name).replace(/\W+/g, '').slice(0, 10), name: txt(p.name), cat: ROLE[p.role] || 'Finished dosage', kind: txt(p.form),
        desc: [p.ingredient ? 'Active ingredient: ' + txt(p.ingredient) : '', txt(p.strength)].filter(Boolean).join(' · '), moq: '', price: '', specs: [] }; }),
      createdAt: new Date(c.created_at).getTime(), updatedAt: fresher(c), _id: c.id, _tier: c.tier };
  }
  /* when the page was last written (companies.updated_at, set by the database on every save, B-22): the "older than 6 months"
     notice counts from it, else from the day the page was made — never from a sample date. The directory's rows do not carry it,
     so an opened page asks for it (loadContacts). */
  function fresher(c) { var u = Date.parse(c.updated_at), m = new Date(c.created_at).getTime(); return u > m ? Math.min(u, Date.now()) : null; }
  function stampFresh(slug) {                  /* "Still correct" / a fix marked: the database moves the page's date to now, for everyone */
    var raw = CO.raw[slug], role = raw && raw.id && CO.roles[raw.id]; if (!raw || !raw.id || (role !== 'owner' && role !== 'admin')) return;
    Promise.resolve(sb.from('companies').update({ updated_at: new Date().toISOString() }).eq('id', raw.id).select('updated_at')).then(function (r) {
      if (r.error) return toastErr(r.error); if (r.data && r.data[0]) { raw.updated_at = r.data[0].updated_at; var l = live(slug); if (l) l.updatedAt = fresher(raw); } });
  }
  /* my pages and my role in each (owner / admin manage the page) — what jobs, listings, suppliers and deals need after sign-in */
  async function loadMine() {
    var me = ME_UUID, q = await Promise.all([sb.from('company_members').select('company_id, role').eq('user_id', ME_UUID).eq('accepted', true), sb.from('companies').select('id').eq('owner_id', ME_UUID)]);
    if (q[0].error) throw q[0].error; if (me !== ME_UUID) return;
    var roles = {}; (q[0].data || []).forEach(function (m) { roles[m.company_id] = m.role; }); (q[1].data || []).forEach(function (c) { roles[c.id] = 'owner'; });
    CO.roles = roles; CO.mine = true;
    var ids = Object.keys(roles).map(Number); if (!ids.length) return;
    var r = await sb.from('companies').select('*').in('id', ids); if (r.error) throw r.error; if (me !== ME_UUID) return;
    var list = window.dxLiveCompanies || (window.dxLiveCompanies = []);
    (r.data || []).forEach(function (c) { if (!okSlug(c.slug)) return; var old = CO.raw[c.slug]; c.mine = true; if (old && old.id) ['track', 'certs', 'products', 'tier'].forEach(function (k) { if (k in old) c[k] = old[k]; });
      CO.raw[c.slug] = c; CO.byId[c.id] = c.slug; var co = coFrom(c), i = list.findIndex(function (x) { return x.slug === c.slug; }); if (i < 0) list.push(co); else list[i] = co; });
    window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;
  }
  /* the directory, 100 companies a request in the directory's order (F-05): the first page when Companies or the Marketplace
     opens, the next one on "Show more" or at the end of the list, and a search asks the database (p_q). Never every company.
     A page is kept for 2 minutes; after that only the first page is asked again (the pages already shown stay). */
  var DIR_PAGE = 100, DIR_FILL = 2, DIR_KEEP = 120000;   /* DIR_FILL: pages the list may fetch by itself, page 1 included */
  function addRows(rows, first) {               /* rows of directory_companies_page (or companies + products): updated in place, new ones added */
    var old = window.dxLiveCompanies || [], list = first ? [] : old, at = {};   /* first: page 1 in the directory's order, then the rest */
    list.forEach(function (x, i) { at[x.slug] = i; });
    rows.forEach(function (c) { if (!okSlug(c.slug)) return; var was = CO.raw[c.slug]; if (was && (was.pending || (was.id && was.id !== c.id))) return;
      if (CO.roles[c.id]) c.mine = true; CO.raw[c.slug] = c; CO.byId[c.id] = c.slug; var co = coFrom(c);
      if (c.slug in at) list[at[c.slug]] = co; else { at[c.slug] = list.length; list.push(co); } });
    if (first) old.forEach(function (x) { if (!(x.slug in at)) { at[x.slug] = list.length; list.push(x); } });
    window.dxLiveCompanies = list; window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;
  }
  function dirKey(q) { q = String(q || '').trim().slice(0, 100).toLowerCase(); return q.length >= 2 ? q : ''; }
  function dirSeq(key) { return CO.seq[key] || (CO.seq[key] = { off: 0, more: true, at: 0, p: null }); }
  /* one page of the list for this search ('' = the whole directory); first = page 1 again (open / refresh) */
  function loadDirPage(q, first) {
    var key = dirKey(q), s = dirSeq(key), me = ME_UUID; if (s.p) return s.p;
    var off = first || !s.off ? 0 : s.off; if (off && !s.more) return Promise.resolve(false);
    s.p = Promise.resolve(sb.rpc('directory_companies_page', { p_limit: DIR_PAGE, p_offset: off, p_q: key || null })).then(function (r) {
      if (r.error) throw r.error; if (me !== ME_UUID) return false;
      var rows = r.data || []; addRows(rows, !key && !off);
      if (off) { s.off = off + rows.length; s.more = rows.length === DIR_PAGE; }
      else { s.at = Date.now(); if (!s.off || rows.length < DIR_PAGE) { s.off = rows.length; s.more = rows.length === DIR_PAGE; } }
      if (!key) { CO.loaded = true; CO.at = s.at; }
      redrawDir(); return rows.length > 0;
    }).finally(function () { s.p = null; if (!key) CO.loading = null; });
    if (!key) CO.loading = s.p;
    return s.p;
  }
  function freshSeq(key) { var s = CO.seq[key]; return s && s.off && Date.now() - s.at < DIR_KEEP; }
  function loadDirectory() { return loadDirPage('', true).then(function () { return window.dxLiveCompanies; }); }
  function curKey() { var S = window.dxDir && window.dxDir.S; return dirKey(S && S.q); }
  function onList() { var S = window.dxDir && window.dxDir.S; return !!S && document.body.getAttribute('data-page') === 'companies' && !S.open && S.view !== 'workspace' && !!document.querySelector('#dxDir.hub .dr-bar'); }
  /* the next page when the list on screen has run out: no "Show more" left and a filter leaves less than a screenful. By itself
     the list never goes beyond DIR_FILL pages (page 1 and one more, once — not five pages on every filter: the directory page is
     the costliest call on the database); scrolling to the end, "Show more" and a search fetch the rest */
  function moreIfShort() {
    if (!ME_UUID || !onList() || document.querySelector('#dxDir.hub [data-hmore]')) return;
    var s = CO.seq[curKey()]; if (!s || !s.off || !s.more || s.p || s.off >= DIR_PAGE * DIR_FILL) return;
    if (document.querySelectorAll('#dxDir.hub .dr-card').length >= 60) return;
    loadDirPage(curKey()).catch(toastErr);
  }
  function redrawDir() {                         /* draw again what is on screen, keeping the search box's caret and the scroll */
    var pg = document.body.getAttribute('data-page');
    var mkl = document.querySelector('#mkx .hb-mk'); if (mkl && pg === 'market') { mkl.dataset.sig = ''; paintMarket(); }   /* the marketplace's company listings name the companies */
    if (pg !== 'companies' || !window.dxDir) return;
    var a = document.activeElement, caret = a && a.id === 'hbQ' ? [a.selectionStart, a.selectionEnd] : null, sc = document.getElementById('content'), top = sc ? sc.scrollTop : 0;
    rerenderCompanies(); if (sc) sc.scrollTop = top;
    if (caret) { var q = document.getElementById('hbQ'); if (q) { q.focus(); try { q.setSelectionRange(caret[0], caret[1]); } catch (x) {} } }
  }
  /* a company that is not in the pages loaded so far (a link from the feed, a deal, a listing): fetched by its slug */
  var COFETCH = {}, CONONE = {};
  function ensureCompanies(slugs) {
    var me = ME_UUID, wait = [], need = [];
    (slugs || []).forEach(function (x) { if (!okSlug(x) || CO.raw[x] || need.indexOf(x) >= 0 || Date.now() - (CONONE[x] || 0) < 60000) return; if (COFETCH[x]) wait.push(COFETCH[x]); else need.push(x); });
    if (me && need.length) { need = need.slice(0, 200);
      var p = Promise.resolve(sb.from('companies').select('*, products:company_products!company_products_company_id_fkey(name, ingredient:active_ingredient, ingredient_ar:active_ingredient_ar, form:dosage_form, strength, role)')
        .in('slug', need).neq('status', 'suspended')).then(function (r) {
        need.forEach(function (x) { delete COFETCH[x]; }); if (me !== ME_UUID || r.error) return;
        need.forEach(function (x) { if (!(r.data || []).some(function (c) { return c.slug === x; })) CONONE[x] = Date.now(); });   /* not found: not asked again for a minute */
        var rows = (r.data || []).filter(function (c) { return !CO.raw[c.slug]; }); if (!rows.length) return;
        addRows(rows, false); redrawDir();
      }, function () { need.forEach(function (x) { delete COFETCH[x]; }); });
      need.forEach(function (x) { COFETCH[x] = p; }); wait.push(p); }
    return Promise.all(wait);
  }
  function openedMissing() { var S = window.dxDir && window.dxDir.S; if (S && S.open && !CO.raw[S.open]) ensureCompanies([S.open]); }
  function refreshCompanies() { return Promise.all([loadMine(), CO.loaded ? loadDirPage('', true) : null]).then(redrawDir); }
  async function loadSites(slug) {
    var r = await sb.rpc('company_sites_public', { p_slug: slug }); if (r.error) throw r.error;
    window.dxLiveSites = window.dxLiveSites || {};
    window.dxLiveSites[slug] = (r.data || []).map(function (s) { return { id: 's' + s.id, name: txt(s.name), type: TYPE[s.type] || 'Factory', city: txt(s.city), gov: txt(s.gov),
      certs: (s.certs || []).map(function (t) { return { name: txt(t.name), expiry: ym(t.expiry), src: t.source === 'public_list' ? 'Public industry list' : 'Certificate document', checked: t.checked ? String(t.checked).slice(0, 10) : '' }; }) }; });
    if (!window.dxLiveSites[slug].length) delete window.dxLiveSites[slug];
    CO.sitesAt[slug] = Date.now();
  }
  /* the full track record of one company (the directory carries only its rating) — loaded when its page opens */
  async function loadTrack(slug) {
    var raw = CO.raw[slug]; if ((!raw || !raw.id) && CO.loading) { try { await CO.loading; } catch (e) {} raw = CO.raw[slug]; }   /* opened while the directory is still loading */
    if (!raw || !raw.id) { await ensureCompanies([slug]); raw = CO.raw[slug]; }                                   /* a company from a page not loaded yet */
    if (!raw || !raw.id) return; var r = await sb.rpc('company_track_record', { p_company: raw.id }); if (r.error) throw r.error; CO.track[slug] = r.data || {}; CO.trackAt[slug] = Date.now(); }
  function rerenderCompanies() { try { if (window.dxDir && document.body.getAttribute('data-page') === 'companies') window.dxDir.render(); } catch (e) { console.error(e); } }
  function live(slug) { return (window.dxLiveCompanies || []).find(function (c) { return c.slug === slug; }); }
  /* writes that the directory makes through store() */
  var SNAP = {};
  async function persistCreated(list) {
    for (var i = 0; i < (list || []).length; i++) {
      var c = list[i], known = CO.raw[c.slug];
      if (!known) {                                         /* a new company: shown at once, saved, undone if the database refuses */
        var shown = Object.assign({}, c, { owner: window.ME.id, status: 'pending', plan: 'free', licensed: false, verified: false });
        (window.dxLiveCompanies || (window.dxLiveCompanies = [])).push(shown);
        var insP = Promise.resolve(sb.from('companies').insert({ owner_id: ME_UUID, name: c.name, slug: c.slug, type: c.sector || 'Manufacturer', sectors: c.sectors || [], city: c.city || null,
          governorate: c.gov || null, location: c.address || null, phone: c.phone || null, email: c.email || null, whatsapp: c.whatsapp || null, tagline: c.tagline || null }).select().single());   /* one request, shared (a query builder re-runs on every await) */
        CO.raw[c.slug] = { pending: insP };                 /* edits saved meanwhile wait for it (F-55) */
        var ins = await insP;
        if (ins.error) { window.dxLiveCompanies = window.dxLiveCompanies.filter(function (x) { return x !== shown; }); delete CO.raw[c.slug]; rerenderCompanies(); toastErr(ins.error); continue; }
        var sv = okSlug(ins.data.slug) ? ins.data.slug : c.slug; if (sv !== c.slug) adoptSlug(c.slug, sv, shown);
        ins.data.mine = true; CO.raw[sv] = ins.data; CO.roles[ins.data.id] = 'owner'; shown._id = ins.data.id; CO.byId[ins.data.id] = sv;
      } else if (c.registry && c.status === 'pending' && known.id && !SNAP['vr_' + c.slug]) {   /* verification documents submitted */
        SNAP['vr_' + c.slug] = 1; var l = live(c.slug); if (l) { l.status = 'pending'; l.registry = c.registry; }
        var docs = {}; try { docs = await window.dxLive.verificationFiles(known.id); } catch (e) { toastErr(e); }
        var vr = await sb.from('verification_requests').insert(Object.assign({ company_id: known.id, submitted_by: ME_UUID, registry: String(c.registry) }, docs));
        if (vr.error) toastErr(vr.error);
      } else if (c.plan === 'vip' && known.plan !== 'vip') {   /* VIP starts only when the payment arrives (window.dxPay) */
        var l2 = live(c.slug); if (l2) l2.plan = coFrom(known).plan; rerenderCompanies();
      }
    }
  }
  /* the database made the new page's address unique (old → old-2, F-74): the page takes the server's address everywhere at once —
     the list, my pages, the company I act as, the page or workspace open now — and the old address is left to the company that
     has it (N-11). The editor opened while it was being saved still holds the old address: its save is moved over (dxStoreHook). */
  function adoptSlug(old, nu, shown) {
    CO.alias[old] = nu; if (CO.raw[old] && CO.raw[old].pending) delete CO.raw[old]; delete CONONE[old];
    shown.slug = nu; if (SNAP[old]) { SNAP[nu] = SNAP[old]; delete SNAP[old]; }
    try { if (localStorage.getItem('dx_acting') === JSON.stringify(old)) localStorage.setItem('dx_acting', JSON.stringify(nu)); } catch (e) {}
    var S = window.dxDir && window.dxDir.S; if (S) { if (S.open === old) S.open = nu; if (S.ws === old) S.ws = nu; }
    window.__dxStoreVer = (window.__dxStoreVer || 0) + 1; rerenderCompanies();
  }
  function mineAt(slug) { var r = CO.raw[slug]; return !!(r && r.id && CO.roles[r.id]); }
  function unalias(edits) {                                 /* edits saved under an address the database changed go to the new one */
    Object.keys(edits || {}).forEach(function (k) { var nu = CO.alias[k]; if (!nu || mineAt(k)) return;
      edits[nu] = edits[k]; delete edits[k]; CO.reopen = { from: k, to: nu }; setTimeout(function () { CO.reopen = null; }, 0); });   /* the editor then opens the old address: the new one is drawn */
    return edits;
  }
  /* page edits: each field is compared with the database row and saved; only what the database accepted is kept, so a failed
     save is sent again next time, and nothing that is not saved online is shown as saved (F-55, F-122) */
  var PAGE_FIELDS = { tagline: 'tagline', about: 'bio', founded: 'founded', employees: 'employees', phone: 'phone', whatsapp: 'whatsapp', email: 'email', website: 'website', hours: 'hours' };
  var PROF_FIELDS = ['services', 'address', 'color'];
  function same(a, b) { var n = function (x) { return x == null || x === '' ? null : x; }; return JSON.stringify(n(a)) === JSON.stringify(n(b)); }
  function names(l) { return (l || []).map(function (p) { return p && p.name; }).join('|'); }
  async function persistEdits(edits) {
    for (var slug in edits) {
      var e = edits[slug] || {}, raw = CO.raw[slug];
      if (raw && raw.pending) { try { await raw.pending; } catch (x) {} if (CO.alias[slug] && !mineAt(slug)) slug = CO.alias[slug]; raw = CO.raw[slug]; }   /* saved before the database answered with another address (N-11) */
      if (!raw || !raw.id) continue;
      var upd = {}, keep = {}, prof = Object.assign({}, raw.profile || {}), l = live(slug), profChanged = false, note = [];
      Object.keys(PAGE_FIELDS).forEach(function (k) { if (!(k in e)) return; var v = e[k] === '' ? null : e[k];
        if (k === 'founded' && v != null) { var y = String(v).match(/\b(1[89]\d\d|20\d\d)\b/); if (!y) { note.push('Founded: enter a year, e.g. 1998'); return; } v = +y[0]; }
        keep[k] = k === 'founded' ? v : e[k]; if (!same(v, raw[PAGE_FIELDS[k]])) upd[PAGE_FIELDS[k]] = v; });
      PROF_FIELDS.forEach(function (k) { if (!(k in e)) return; keep[k] = e[k]; if (!same(e[k], prof[k])) { prof[k] = e[k]; profChanged = true; } });
      if (profChanged) upd.profile = prof;
      if (e.plan === 'vip' && raw.plan !== 'vip') note.push('VIP starts after payment — use Upgrade to VIP on your page');
      if (e.sites && JSON.stringify(e.sites) !== JSON.stringify((SNAP[slug] || {}).sites)) { keep.sites = e.sites; note.push('Site and certificate changes are sent for review in the next update'); }
      if (l && ((('products' in e) && names(e.products) !== names(l.products)) || (('logo' in e) && !same(e.logo, l.logo)) || (('cover' in e) && !same(e.cover, l.cover)) || (e.certsPending || []).length))
        note.push('Products, logo, cover and certificate files are not saved online yet — they come with the next update');
      if (note.length) setTimeout(function (t) { window.toast(t); }, 600, note[0]);    /* after the editor's own "published" message */
      if (!Object.keys(upd).length) { SNAP[slug] = keep; continue; }
      var r = await sb.from('companies').update(upd).eq('id', raw.id).select();
      if (r.error || !(r.data || []).length) { toastErr(r.error || { message: 'Only the page’s owner or admins can change it' }); rerenderCompanies(); continue; }
      Object.assign(raw, r.data[0]); SNAP[slug] = keep;
      if (l) { var fresh = coFrom(raw); Object.keys(keep).forEach(function (k) { if (k in fresh) l[k] = fresh[k]; }); l.updatedAt = fresh.updatedAt; }
    }
  }
  window.dxStoreHook = function (k, v) {
    if (!ME_UUID) return undefined;
    if (k === 'created_companies') { if (v === undefined) return []; persistCreated(v).catch(toastErr); return true; }
    if (k === 'company_edits') { if (v === undefined) return JSON.parse(JSON.stringify(SNAP_EDITS())); persistEdits(unalias(v)).catch(toastErr); return true; }
    if (k === 'supplier_reviews') { if (v === undefined) return {}; return true; }
    if (v && /^meta_/.test(k) && window.dxHubData && window.dxHubData.SECTIONS.every(function (x) { return v[x] && Date.now() - v[x].at < 10000; })) { var sl = k.slice(5); stampFresh(CO.alias[sl] && !mineAt(sl) ? CO.alias[sl] : sl); }   /* the whole page confirmed now */
    return undefined;
  };
  function SNAP_EDITS() { var o = {}; Object.keys(SNAP).forEach(function (k) { if (k.indexOf('vr_') !== 0) o[k] = SNAP[k]; }); return o; }
  /* a company page (or my workspace) loads its sites and full track record when it opens, and is drawn again only if the viewer
     is still on it (F-56) */
  function pageData(slug, ws) {
    var fresh = function (at) { return at && Date.now() - at < 60000; };     /* each kept for a minute */
    if (!ME_UUID || !slug || (fresh(CO.sitesAt[slug]) && fresh(CO.trackAt[slug]) && fresh(CC.at[slug]))) return;
    Promise.all([fresh(CO.sitesAt[slug]) || loadSites(slug), fresh(CO.trackAt[slug]) || loadTrack(slug), fresh(CC.at[slug]) || loadContacts(slug)]).then(function () {
      var S = window.dxDir && window.dxDir.S; if (!S || document.body.getAttribute('data-page') !== 'companies') return;
      if (ws ? S.view === 'workspace' && S.ws === slug : S.open === slug && S.view !== 'workspace') window.dxDir.render();
    }).catch(toastErr);
  }
  /* ── B-05: who answers at a company (0032). The team and the routing are members-only, so a page asks company_contacts() who
     answers each kind of request; the approved "Who answers" / "Who receives what" text and the chat window name that person,
     and "Message" / "Send a message" write to them through company_message() — the database picks the receiver, never a name.
     A company nobody answers for (unclaimed) says so and shows its Contact tab (phone, email, WhatsApp). ── */
  var CC = { at: {}, by: {}, p: {} };
  var CROLE = { owner: 'Owner', admin: 'Admin', sales: 'Sales', quality: 'Quality', regulatory: 'Regulatory', hr: 'HR', member: 'Team member' };
  function loadContacts(slug) {
    var raw = CO.raw[slug], me = ME_UUID; if (!raw || !raw.id) return Promise.resolve(null);
    if (CC.p[slug]) return CC.p[slug];
    var upd = Promise.resolve(sb.from('companies').select('updated_at').eq('id', raw.id)).then(function (q) {   /* the page's last save (B-22) */
      var u = q.data && q.data[0]; if (!u || me !== ME_UUID) return; raw.updated_at = u.updated_at; var l = live(slug); if (l) l.updatedAt = fresher(raw); }, function () {});
    return (CC.p[slug] = Promise.all([sb.rpc('company_contacts', { p_company: raw.id }), upd]).then(function (rr) {
      var r = rr[0]; if (r.error) throw r.error; if (me !== ME_UUID) return null;
      var c = r.data || {}, ids = [];
      Object.keys(c).forEach(function (k) { var x = c[k]; if (x && x.id && x.id !== ME_UUID && ids.indexOf(x.id) < 0) ids.push(x.id); });
      var known = ids.length ? sb.from('profiles').select(PCOLS).in('id', ids).then(function (q) { if (me === ME_UUID) (q.data || []).forEach(putUser); }) : null;   /* the Messages page names them */
      return Promise.resolve(known).then(function () { if (me !== ME_UUID) return null; CC.by[slug] = c; CC.at[slug] = Date.now(); return c; });
    }).finally(function () { delete CC.p[slug]; }));
  }
  function contactsOf(slug) { return CC.at[slug] && Date.now() - CC.at[slug] < 60000 ? Promise.resolve(CC.by[slug]) : loadContacts(slug); }
  onReset(function () { CC = { at: {}, by: {}, p: {} }; });
  function wrapRoute() {
    var HD = window.dxHubData; if (!HD || !HD.route || HD.route.__live) return;
    var o = HD.route;
    HD.route = function (slug, type) {
      var c = ME_UUID && CC.by[slug]; if (!c) return o.apply(this, arguments);
      var x = type in c ? c[type] : c.quote;
      if (!x) return { name: 'nobody on Drugbox yet', role: 'use the Contact tab' };
      return { name: txt(x.name) || 'Drugbox member', role: CROLE[x.role] || 'Team member' };
    };
    HD.route.__live = true;
  }
  window.addEventListener('click', function (e) {                         /* before the page's own handler (a capture on document) */
    var b = ME_UUID && e.target.closest && e.target.closest('#dxDir.hub [data-hmsg]'); if (!b) return;
    var S = window.dxDir && window.dxDir.S, slug = S && (S.open || S.ws), raw = slug && CO.raw[slug]; if (!raw || !raw.id) return;
    e.preventDefault(); e.stopPropagation();
    contactsOf(slug).then(function (c) {
      var q = c && c.quote, name = txt(raw.name);
      if (!q) { window.toast('Nobody at ' + name + ' answers messages on Drugbox yet — call, email or WhatsApp them from the Contact tab');
        if (S.open === slug && S.tab !== 'contact') { S.tab = 'contact'; rerenderCompanies(); } return; }
      if (q.id === ME_UUID) { window.toast('You answer ' + name + '’s messages yourself'); return; }
      var who = txt(q.name) || 'Drugbox member'; DOCKTO[who] = { company: raw.id, uid: q.id, at: Date.now() };
      if (window.dxOpenChat) window.dxOpenChat(who);
    }).catch(toastErr);
  }, true);
  document.addEventListener('click', function (e) {                       /* the chat window's "Open full chat": the real conversation */
    var b = ME_UUID && e.target.closest && e.target.closest('#dxDock [data-a=full]'), w = b && b.closest('.dk-win'), co = w && dockCompany(w.dataset.n);
    if (co && (window.USERS || []).some(function (u) { return u.id === aid(co.uid); })) MX.to = aid(co.uid);
  }, true);
  function wrapHub() {
    var X = window.dxDir, H = window.dxHub; wrapRoute();
    if (X && X.open && !X.open.__live) { var o = X.open; X.open = function (slug) { var r = o.apply(this, arguments); pageData(slug, false); return r; }; X.open.__live = true; }
    if (X && X.render && !X.render.__live) { var rd = X.render; X.render = function () { var r = rd.apply(this, arguments); openedMissing(); setTimeout(moreIfShort, 0); return r; }; X.render.__live = true; }
    if (window.dxOpenCompany && !window.dxOpenCompany.__live) { var oc = window.dxOpenCompany; window.dxOpenCompany = function (slug) { var r = oc.apply(this, arguments); pageData(slug, false); return r; }; window.dxOpenCompany.__live = true; }
    if (H && H.render && !H.render.__live) { var hr = H.render; H.render = function (c, St, co) {      /* the page the editor saved under the old address (N-11) */
      if (CO.reopen && St && St.open === CO.reopen.from) { St.open = CO.reopen.to; co = X && X.bySlug(St.open); } return hr.call(this, c, St, co); }; H.render.__live = true; }
    if (H && H.workspace && !H.workspace.__live) { var w = H.workspace; H.workspace = function (slug) { var r = w.apply(this, arguments); pageData(slug, true); return r; }; H.workspace.__live = true; }
  }
  var gotoB4 = window.goto;
  window.goto = function (page) {
    var r = gotoB4.apply(this, arguments); wrapHub();
    /* the pages that show other companies (the directory, the marketplace's company listings) load it; refreshed after 2 minutes */
    if ((page === 'companies' || page === 'market') && ME_UUID) {
      if (!freshSeq('')) loadDirPage('', true).catch(toastErr);                                   /* page 1, or nothing within 2 minutes */
      var k = curKey(); if (page === 'companies' && k && !freshSeq(k)) loadDirPage(k, true).catch(toastErr);
      if (page === 'companies') openedMissing();
      if (page === 'market' && typeof LIST !== 'undefined' && LIST) ensureCompanies(LIST.surplus.concat(LIST.dossiers).map(function (x) { return x.slug; })).catch(function () {});
    }
    return r;
  };
  /* search: the database answers it (p_q), 350 ms after the last key — the companies found join the list the page filters */
  var DIRQ = null;
  document.addEventListener('input', function (e) {
    if (!ME_UUID || !e.target || e.target.id !== 'hbQ') return; clearTimeout(DIRQ);
    DIRQ = setTimeout(function () { var k = curKey(); if (k && !freshSeq(k)) loadDirPage(k, true).catch(toastErr); }, 350);
  }, true);
  /* "Show more" draws the next 60 companies already here and fetches the next page, so the list never runs dry */
  document.addEventListener('click', function (e) {
    if (!ME_UUID || !e.target.closest || !e.target.closest('#dxDir.hub [data-hmore]')) return;
    var k = curKey(), s = CO.seq[k]; if (s && s.off && s.more) loadDirPage(k).catch(toastErr);
  }, true);
  var DIRS = 0, DIRTOP = new WeakMap();
  document.addEventListener('scroll', function (e) {                                          /* the end of the list: the next page */
    var el = e.target && e.target.nodeType === 1 ? e.target : document.scrollingElement; if (!el) return;
    var was = DIRTOP.get(el) || 0, down = el.scrollTop > was + 1; DIRTOP.set(el, el.scrollTop);   /* only a scroll DOWN: a redraw that shortens the list scrolls too, and must not fetch page after page by itself */
    if (!down || !ME_UUID || Date.now() - DIRS < 300 || !onList() || document.querySelector('#dxDir.hub [data-hmore]')) return; DIRS = Date.now();
    if (el.scrollTop + el.clientHeight < el.scrollHeight - 400) return;
    var k = curKey(), s = CO.seq[k]; if (s && s.off && s.more && !s.p) loadDirPage(k).catch(toastErr);
  }, true);
  /* "Claim this page": a claim request reviewed by Drugbox (claim_company), never an edit made in the browser (F-42) */
  if (window.dxDir2 && window.dxDir2.claim) window.dxDir2.claim = function (co) {
    var raw = co && CO.raw[co.slug]; if (!raw || !raw.id) return;
    window.DBK.modal({ title: 'Claim ' + co.name, body: '<p class="cp-muted">Prove you work at ' + esc2(co.name) + ' and the page becomes yours to manage. Drugbox checks every claim before handing a page over.</p>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="clRole">Your role *</label><input id="clRole" data-req placeholder="e.g. Business Development Manager"></div><div class="dbk-f"><label for="clPhone">Mobile *</label><input id="clPhone" data-req inputmode="tel"></div></div>' +
      '<div class="dbk-f"><label for="clMail">Work email *</label><input id="clMail" data-req type="email" placeholder="you@company.com"></div>',
      primary: { label: 'Send request', onClick: function (b, close) {
        if (!window.DBK.requireFields(b)) return false; var ok = b.querySelector('[data-a=ok]') || b.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        var note = 'Role: ' + b.querySelector('#clRole').value.trim() + ' · Mobile: ' + b.querySelector('#clPhone').value.trim() + ' · Work email: ' + b.querySelector('#clMail').value.trim();
        sb.rpc('claim_company', { p_company_id: raw.id, p_note: note }).then(function (r) { if (ok) ok.disabled = false;
          if (r.error) return toastErr(r.error); close(); window.toast('Claim sent — Drugbox checks it and tells you when the page is yours'); });
        return false; } } });
  };
  var hydrateB4 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateB4(uid); window.dxLiveCompanies = []; CO.seq = {}; CO.loaded = false; CO.mineP = loadMine().then(wrapHub).catch(function (e) { console.error(e); }); return me; };
  onReset(function () { CO.byId = {}; CO.raw = {}; CO.loaded = false; CO.at = 0; CO.roles = {}; CO.mine = false; CO.mineP = null; CO.sitesAt = {}; CO.track = {}; CO.trackAt = {}; CO.seq = {}; CO.alias = {}; CO.reopen = null; COFETCH = {}; CONONE = {}; SNAP = {}; window.dxLiveCompanies = []; window.dxLiveSites = {}; });
  Object.assign(window.dxLive, { loadDirectory: loadDirectory, loadSites: loadSites, version: 'C1' });

  /* ═══════════════ C2 — deals: every step goes through the database engine (deal_create / deal_act) ═══════════════
     The demo's deals.js keeps working unchanged; store('deals') reads the person's real deals and every new deal or
     new step it writes is sent to the engine, which accepts it or refuses it (then the true state is reloaded). */
  var DEALS = { list: [], snap: {}, loaded: false, at: 0, busy: Promise.resolve() };
  function tms(t) { return new Date(t).getTime(); }
  function dealFrom(r) {
    var fc = r.fc, tc = r.tc || {};
    var from = r.from_company_id && fc ? { slug: sslug(fc.slug), name: fc.name } : { slug: null, name: (r.fu && r.fu.name) || 'Member', person: true, userId: aid(r.from_user) };
    var d = { id: r.ref, type: r.type, title: r.title, from: from, to: { slug: sslug(tc.slug), name: tc.name }, lines: r.lines || {}, status: r.status,
      at: tms(r.created_at), updated: tms(r.updated_at),
      events: (r.deal_events || []).slice().sort(function (a, b) { return a.id - b.id; }).map(function (e) { return { at: tms(e.created_at), by: e.side, kind: e.action, text: e.note || '', data: e.data || {} }; }) };
    if (r.offer) d.offer = r.offer; if (r.counter) d.counter = r.counter; if (r.answers) d.answers = r.answers; if (r.ontime !== null && r.ontime !== undefined) d.ontime = r.ontime;
    if (r.group_key) d.group = r.group_key; if (r.assignee) d.assignee = aid(r.assignee);
    return d;
  }
  async function loadDeals() {
    var r = await sb.from('deals').select('*, deal_events(*), fc:companies!deals_from_company_id_fkey(slug,name), tc:companies!deals_to_company_id_fkey(slug,name), fu:profiles!deals_from_user_fkey(name)')
      .order('updated_at', { ascending: false }).limit(300);
    if (r.error) throw r.error;
    DEALS.list = (r.data || []).map(dealFrom); DEALS.snap = {}; DEALS.list.forEach(function (d) { DEALS.snap[d.id] = d.events.length; });
    DEALS.loaded = true; DEALS.at = Date.now(); return DEALS.list;
  }
  function refused(e) { toastErr(e); return loadDeals().then(function () { try { if (document.body.getAttribute('data-page') === 'companies' && window.dxDir) window.dxDir.render(); } catch (x) {} }).catch(function () {}); }
  async function createRemote(d) {
    var first = d.events[0] || {};
    var r = await sb.rpc('deal_create', { p_type: d.type, p_to_slug: d.to.slug, p_from_slug: d.from.slug || null, p_title: d.title, p_lines: d.lines || {},
      p_message: first.text || '', p_group: d.group || null, p_ref: d.id });
    if (r.error) return refused(r.error);
    if (d.events.length > 1) return actRemote(d, d.events.slice(1));
  }
  async function actRemote(d, evs) {
    for (var i = 0; i < evs.length; i++) { var e = evs[i];
      var r = await sb.rpc('deal_act', { p_ref: d.id, p_action: e.kind, p_data: Object.assign({}, e.data || {}, { text: e.text || '' }), p_side: e.by });
      if (r.error) return refused(r.error); }
  }
  function syncDeals(list) {
    DEALS.list = list; var jobs = [];
    list.forEach(function (d) {
      var known = Object.prototype.hasOwnProperty.call(DEALS.snap, d.id), n0 = known ? DEALS.snap[d.id] : 0;
      if (!known) { DEALS.snap[d.id] = d.events.length; jobs.push(function () { return createRemote(d); }); }
      else if (d.events.length > n0) { var fresh = d.events.slice(n0); DEALS.snap[d.id] = d.events.length; jobs.push(function () { return actRemote(d, fresh); }); }
    });
    jobs.forEach(function (j) { DEALS.busy = DEALS.busy.then(j).catch(toastErr); });   /* steps reach the engine in the order they were taken */
  }
  var hookC1 = window.dxStoreHook;
  window.dxStoreHook = function (k, v) {
    if (k === 'deals' && ME_UUID) { if (v === undefined) return DEALS.list; syncDeals(v); return true; }
    return hookC1 ? hookC1(k, v) : undefined;
  };
  /* track record from the database: company_track_record once the page has opened, the directory's rating until then */
  window.dxLiveTrack = function (slug) { var raw = CO.raw[slug], t = CO.track[slug] || (raw && raw.track); if (!t) return null;
    return { orders: t.orders || 0, ontime: t.ontime == null ? null : +t.ontime, rating: t.rating == null ? null : +t.rating, reviews: t.reviews || 0,
             response: t.response == null ? null : +t.response, requests: t.requests || 0, answered: t.answered || 0 }; };
  ICON.deal = '📨';
  var hydrateC1 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateC1(uid); loadDeals().catch(function (e) { console.error(e); }); return me; };
  onReset(function () { DEALS.list = []; DEALS.snap = {}; DEALS.mem = {}; DEALS.loaded = false; DEALS.at = 0; DEALS.busy = Promise.resolve(); });
  window.dxLive.loadDeals = loadDeals; window.dxLive.dealsBusy = function () { return DEALS.busy; }; window.dxLive.version = 'C2';

  /* ═══════════════ C3 — company listings (surplus, dossiers), group buying, approved suppliers ═══════════════ */
  var LIST = { surplus: [], dossiers: [], known: {}, avl: {} };
  function listingFrom(r) { var slug = CO.byId[r.company_id] || sslug(r.co && r.co.slug);
    return r.kind === 'surplus' ? { id: r.ref, slug: slug, product: r.product, qty: r.qty || '', batch: r.batch || '—', expiry: r.expiry || '—', price: r.price || '', off: r.off || 0 }
      : { id: r.ref, slug: slug, product: r.product, status: r.reg_status || '', deal: r.deal_kind || '', markets: r.markets || 'Egypt' }; }
  async function loadListings() {
    window.dxLiveListings = true;                     /* set first: the demo's sample listings never show, even when this load fails (F-54) */
    var r = await sb.from('company_listings').select('*, co:companies(slug)').eq('active', true).order('created_at', { ascending: false }).limit(500); if (r.error) throw r.error;
    LIST.surplus = []; LIST.dossiers = []; (r.data || []).forEach(function (x) { LIST.known[x.ref] = 1; (x.kind === 'surplus' ? LIST.surplus : LIST.dossiers).push(listingFrom(x)); });
  }
  async function persistListings(kind, list) {
    for (var i = 0; i < (list || []).length; i++) { var it = list[i]; if (LIST.known[it.id]) continue; LIST.known[it.id] = 1;
      var raw = CO.raw[it.slug]; if (!raw || !raw.id) continue;
      var row = kind === 'surplus' ? { ref: it.id, company_id: raw.id, kind: 'surplus', product: it.product, qty: it.qty, batch: it.batch, expiry: it.expiry, price: it.price, off: it.off || 0, created_by: ME_UUID }
        : { ref: it.id, company_id: raw.id, kind: 'dossier', product: it.product, reg_status: it.status, deal_kind: it.deal, markets: it.markets, created_by: ME_UUID };
      var r = await sb.from('company_listings').insert(row); if (r.error) { delete LIST.known[it.id]; toastErr(r.error); await loadListings().catch(function () {}); return; } }
    if (kind === 'surplus') LIST.surplus = list; else LIST.dossiers = list;
  }
  async function loadAvl() {
    var mine = (window.dxLiveCompanies || []).filter(function (c) { return c.owner === window.ME.id; }); LIST.avl = {}; if (!mine.length) return;
    var r = await sb.from('approved_suppliers').select('status, updated_at, buyer:companies!approved_suppliers_buyer_company_id_fkey(slug), sup:companies!approved_suppliers_supplier_company_id_fkey(slug)')
      .in('buyer_company_id', mine.map(function (c) { return c._id; })); if (r.error) throw r.error;
    (r.data || []).forEach(function (x) { var b = sslug(x.buyer && x.buyer.slug), s = sslug(x.sup && x.sup.slug); if (!b || !s) return; (LIST.avl[b] = LIST.avl[b] || {})[s] = { status: x.status, since: String(x.updated_at).slice(0, 10) }; });
  }
  async function persistAvl(buyerSlug, map) {
    var before = LIST.avl[buyerSlug] || {}, buyer = CO.raw[buyerSlug]; LIST.avl[buyerSlug] = JSON.parse(JSON.stringify(map || {})); if (!buyer || !buyer.id) return;
    var keys = Object.keys(Object.assign({}, before, map || {}));
    for (var i = 0; i < keys.length; i++) { var s = keys[i], now = (map || {})[s], was = before[s], sup = CO.raw[s]; if (!sup || !sup.id) continue;
      var r = null;
      if (now && (!was || was.status !== now.status)) r = await sb.from('approved_suppliers').upsert({ buyer_company_id: buyer.id, supplier_company_id: sup.id, status: now.status, updated_at: new Date().toISOString() });
      else if (!now && was) r = await sb.from('approved_suppliers').delete().eq('buyer_company_id', buyer.id).eq('supplier_company_id', sup.id);
      if (r && r.error) { toastErr(r.error); await loadAvl().catch(function () {}); return; } }
  }
  var hookC2 = window.dxStoreHook;
  window.dxStoreHook = function (k, v) {
    if (ME_UUID && k === 'groups_seeded') return true;                 /* the demo's sample groups are never created in the live app */
    if (ME_UUID && k === 'groups_new') return v === undefined ? [] : true;
    if (ME_UUID && k === 'groups_state') return v === undefined ? {} : true;
    if (ME_UUID && window.dxLiveListings) {
      if (k === 'surplus_new') { if (v === undefined) return LIST.surplus; persistListings('surplus', v).catch(toastErr); return true; }
      if (k === 'dossiers') { if (v === undefined) return LIST.dossiers; persistListings('dossier', v).catch(toastErr); return true; }
      if (k.indexOf('avl_') === 0) { var b = k.slice(4); if (v === undefined) return LIST.avl[b] || {}; persistAvl(b, v).catch(toastErr); return true; }
    }
    return hookC2 ? hookC2(k, v) : undefined;
  };
  /* group buying on the deals engine: joins go through deal_join; member orders are created by the database */
  DEALS.mem = {};
  var dealFromC2 = dealFrom;
  dealFrom = function (r) { var d = dealFromC2(r);
    if (r.deal_members && r.deal_members.length) d.members = r.deal_members.map(function (m) { return { slug: sslug(m.co && m.co.slug), name: m.co && m.co.name, qty: +m.qty }; });
    if (r.group_of) d.groupOf = r.group_of; return d; };
  loadDeals = async function () {
    var r = await sb.from('deals').select('*, deal_events(*), deal_members(qty, co:companies(slug,name)), fc:companies!deals_from_company_id_fkey(slug,name), tc:companies!deals_to_company_id_fkey(slug,name), fu:profiles!deals_from_user_fkey(name)')
      .order('updated_at', { ascending: false }).limit(300);
    if (r.error) throw r.error;
    var refOf = {}; (r.data || []).forEach(function (x) { refOf[x.id] = x.ref; });
    DEALS.list = (r.data || []).map(dealFrom); DEALS.snap = {}; DEALS.mem = {};
    DEALS.list.forEach(function (d) { if (d.groupOf) d.groupOf = refOf[d.groupOf] || ('G' + d.groupOf); DEALS.snap[d.id] = d.events.length; var m = {}; (d.members || []).forEach(function (x) { m[x.slug] = x.qty; }); DEALS.mem[d.id] = m; });
    DEALS.loaded = true; DEALS.at = Date.now(); return DEALS.list;
  };
  window.dxLive.loadDeals = loadDeals;
  function engineEvents(evs) { return evs.filter(function (e) { return e.by === 'from' || e.by === 'to'; }); }
  async function joins(d) { var before = DEALS.mem[d.id] || {}, now = {};
    (d.members || []).forEach(function (m) { now[m.slug] = (now[m.slug] || 0) + m.qty; });
    for (var slug in now) { var delta = now[slug] - (before[slug] || 0); if (delta > 0) { var r = await sb.rpc('deal_join', { p_ref: d.id, p_from_slug: slug, p_qty: delta }); if (r.error) return refused(r.error); } }
    DEALS.mem[d.id] = now; }
  syncDeals = function (list) {
    DEALS.list = list; var jobs = [];
    list.forEach(function (d) {
      var known = Object.prototype.hasOwnProperty.call(DEALS.snap, d.id), n0 = known ? DEALS.snap[d.id] : 0;
      if (!known) { DEALS.snap[d.id] = d.events.length; if (d.groupOf) return;                       /* member orders come from the database */
        jobs.push(function () { return createRemote(Object.assign({}, d, { events: [d.events[0]].concat(engineEvents(d.events.slice(1))) })).then(function () { if (d.type === 'group') { DEALS.mem[d.id] = {}; return joins(d); } }); }); }
      else if (d.events.length > n0) { var fresh = d.events.slice(n0); DEALS.snap[d.id] = d.events.length;
        jobs.push(function () { return (d.type === 'group' ? joins(d) : Promise.resolve()).then(function () { var ev = engineEvents(fresh); if (ev.length) return actRemote(d, ev); })
          .then(function () { if (fresh.some(function (e) { return e.kind === 'confirm_group'; })) return loadDeals(); }); }); }
    });
    jobs.forEach(function (j) { DEALS.busy = DEALS.busy.then(j).catch(toastErr); });
  };
  var hydrateC2 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateC2(uid); loadListings().then(function () { return CO.mineP; }).then(function () { return loadAvl(); }).catch(function (e) { console.error(e); }); return me; };
  onReset(function () { LIST.surplus = []; LIST.dossiers = []; LIST.known = {}; LIST.avl = {}; });
  Object.assign(window.dxLive, { loadListings: loadListings, loadAvl: loadAvl, version: 'C3' });

  /* ═══════════════ D1 — marketplace: supply and demand cards from the database, using the approved page's own cards as templates ═══════════════ */
  var MKT = { tplL: null, tplD: null, tplS: null, tplM: null, products: [], demand: [], at: 0 };
  var CAT = { supply: 'api', demand: 'api', cmo: 'cmo', license: 'registration', equipment: 'equipment', service: 'service', training: 'service' };
  var FLAG = { EG: '🇪🇬', SA: '🇸🇦', AE: '🇦🇪', CN: '🇨🇳', IN: '🇮🇳', DE: '🇩🇪', US: '🇺🇸', GB: '🇬🇧', JO: '🇯🇴', IQ: '🇮🇶' };
  function promoted(p, k) { return !!p[k] && new Date(p[k]) > Date.now(); }
  async function loadMarket() {
    var now = new Date().toISOString(), sel = '*, seller:profiles!products_user_id_fkey(' + PCOLS + ')';
    var a = await Promise.all([
      sb.from('products').select(sel).eq('active', true).eq('type', 'supply').order('created_at', { ascending: false }).limit(40),
      sb.from('enquiries').select('*, buyer:profiles!enquiries_user_id_fkey(' + PCOLS + ')').eq('status', 'active').eq('type', 'demand').order('created_at', { ascending: false }).limit(40),
      sb.from('products').select(sel).eq('active', true).eq('type', 'supply').or('featured_until.gt.' + now + ',boosted_until.gt.' + now).order('created_at', { ascending: false }).limit(20)]);
    if (a[0].error) throw a[0].error; if (a[1].error) throw a[1].error;
    /* paid placement (F-06): featured listings first, then boosted ones, then the newest; featured ones also fill the sponsored strip */
    var seen = {}, rank = function (p) { return promoted(p, 'featured_until') ? 2 : promoted(p, 'boosted_until') ? 1 : 0; };
    MKT.products = (a[2].data || []).concat(a[0].data || []).filter(function (p) { if (seen[p.id]) return false; seen[p.id] = 1; return true; })
      .map(function (p, i) { return [p, i]; }).sort(function (x, y) { return rank(y[0]) - rank(x[0]) || x[1] - y[1]; }).map(function (x) { return x[0]; });
    MKT.demand = a[1].data || []; MKT.at = Date.now();
    MKT.products.forEach(function (p) { putUser(p.seller); }); MKT.demand.forEach(function (e) { putUser(e.buyer); });
  }
  /* a card from the approved page's first card; the decorations other layers added to that card (the structure chip and its
     "already looked at" mark) are not copied, so they are added for the real product instead */
  function el(html) { var b = document.createElement('div'); b.innerHTML = html;
    b.querySelectorAll('.dx-molchip').forEach(function (x) { x.remove(); }); b.querySelectorAll('[data-dxmol]').forEach(function (x) { x.removeAttribute('data-dxmol'); });
    return b.firstElementChild; }
  function supplyCard(p) {
    var c = el(MKT.tplL), u = p.seller || {}, docs = p.docs || [];
    c.dataset.live = 'p' + p.id; c.dataset.uid = aid(p.user_id);
    var em = c.querySelector('.lc-em'); if (em) em.textContent = p.emoji || '📦';
    c.querySelectorAll('.cert-p').forEach(function (x) { x.remove(); });
    var badges = c.querySelector('.lc-top .lt'); if (badges) docs.slice(0, 3).forEach(function (d) { badges.insertAdjacentHTML('afterend', '<span class="cert-p">' + esc2(d) + '</span>'); });
    var t = c.querySelector('.lc-title'); if (t) t.textContent = p.name;
    var ds = c.querySelector('.lc-desc'); if (ds) ds.textContent = p.description || '';
    if (promoted(p, 'featured_until') || promoted(p, 'boosted_until')) c.dataset.promoted = promoted(p, 'featured_until') ? 'featured' : 'boost';
    var tb = c.querySelector('.trust-bar'); if (tb) { tb.innerHTML = (u.verified ? '<span class="ti g">✓ Verified seller</span>' : '') + docs.slice(0, 2).map(function (d) { return '<span class="ti b">✓ ' + esc2(d) + '</span>'; }).join(''); tb.style.display = tb.innerHTML ? '' : 'none'; }
    var pr = c.querySelector('.price'); if (pr) pr.textContent = (p.price || 'On request') + (p.price && p.unit ? '/' + p.unit : '');
    var mq = c.querySelector('.moq'); if (mq) mq.textContent = (p.moq ? 'MOQ: ' + p.moq + ' · ' : '') + (FLAG[u.country] || '') + ' ' + (u.name || '');
    return c;
  }
  function demandCard(e) {
    var c = el(MKT.tplD), u = e.buyer || {}, a = aid(e.user_id), usr = window.U(a);
    c.dataset.live = 'e' + e.id; c.dataset.uid = a;
    var t = c.querySelector('.dc-title'); if (t) { var badge = t.querySelector('.role-badge'); t.textContent = e.title; if (badge) t.insertBefore(badge, t.firstChild); }
    var ur = c.querySelector('.db-badge'); if (ur) ur.style.display = e.urgent ? '' : 'none';
    var dt = c.querySelector('.dc-det'); if (dt) dt.innerHTML = esc2((e.body || '').slice(0, 70)) + '<br>' + (FLAG[e.country] || esc2(e.flag || '')) + ' ' + esc2(e.country || '') + ' · ' + ago(e.created_at);   /* stored text is escaped (F-02) */
    var by = c.querySelector('.dc-buyer'); if (by) by.innerHTML = '<div class="av" style="background:' + usr.color + ';width:17px;height:17px;font-size:7px">' + esc2(usr.initials) + '</div> ' + esc2(u.name || 'Member') + (u.verified ? ' ✓' : '');
    return c;
  }
  /* a featured listing in the approved sponsored card / mini card (no invented view or enquiry numbers) */
  function sponsoredCard(p) {
    var c = el(MKT.tplS), u = p.seller || {}, docs = p.docs || [], usr = window.U(aid(p.user_id));
    c.dataset.live = 'p' + p.id; c.dataset.uid = aid(p.user_id); c.style.marginBottom = '';
    var lab = c.querySelector('.sp-label'); if (lab) lab.textContent = '⭐ SPONSORED · FEATURED';
    var an = c.querySelector('.sp-analytics'); if (an) an.remove();
    var im = c.querySelector('.sp-img'); if (im) im.textContent = p.emoji || '📦';
    c.querySelectorAll('.sp-meta .cert').forEach(function (x) { x.remove(); });
    var lt = c.querySelector('.sp-meta .lt'); if (lt) docs.slice(0, 3).reverse().forEach(function (d) { lt.insertAdjacentHTML('afterend', '<span class="cert">' + esc2(d) + '</span>'); });
    var t = c.querySelector('.sp-title'); if (t) t.textContent = p.name;
    var ds = c.querySelector('.sp-desc'); if (ds) ds.textContent = p.description || '';
    var tr = c.querySelector('.sp-trust'); if (tr) { tr.innerHTML = (u.verified ? '<span class="ti g">✓ Verified seller</span>' : '') + docs.slice(0, 3).map(function (d) { return '<span class="ti b">✓ ' + esc2(d) + '</span>'; }).join(''); tr.style.display = tr.innerHTML ? '' : 'none'; }
    var av = c.querySelector('.sp-seller .av'); if (av) { av.style.background = usr.color; av.textContent = usr.initials; }
    var sn = c.querySelector('.seller-name'); if (sn) sn.innerHTML = esc2(u.name || 'Member') + (u.verified ? ' <span style="color:#1a56db;font-size:11px">✓ Verified</span>' : '');
    var ss = c.querySelector('.seller-sub'); if (ss) ss.textContent = ((FLAG[u.country] || '') + ' ' + [u.company, String(u.headline || '').split('|')[0].trim()].filter(Boolean).join(' · ')).trim();
    var sr = c.querySelector('.seller-resp'); if (sr) sr.remove();
    var pr = c.querySelector('.sp-price'); if (pr) pr.textContent = (p.price || 'On request') + (p.price && p.unit ? '/' + p.unit : '');
    var mq = c.querySelector('.sp-moq'); if (mq) mq.textContent = p.moq ? 'MOQ: ' + p.moq : '';
    return c;
  }
  function sponsoredMini(p) {
    var c = el(MKT.tplM), u = p.seller || {}; c.dataset.live = 'p' + p.id; c.dataset.uid = aid(p.user_id);
    var t = c.querySelector('.sm-title'); if (t) t.textContent = p.name;
    var pr = c.querySelector('.sm-price'); if (pr) pr.textContent = [(p.price || 'On request') + (p.price && p.unit ? '/' + p.unit : ''), p.moq ? 'MOQ ' + p.moq : ''].filter(Boolean).join(' · ');
    var sl = c.querySelector('.sm-seller'); if (sl) sl.textContent = ((FLAG[u.country] || '') + ' ' + (u.name || 'Member') + (u.verified ? ' · ✓ Verified' : '')).trim();
    return c;
  }
  function paintSponsored(mk) {
    var spDemo = mk.querySelector('.sponsored-card:not([data-live])'), miDemo = mk.querySelector('.sp-mini:not([data-live])');
    if (spDemo) { if (!MKT.tplS) MKT.tplS = spDemo.outerHTML; spDemo.parentElement.setAttribute('data-live-sponsored', '1'); }
    if (miDemo) { if (!MKT.tplM) MKT.tplM = miDemo.outerHTML; miDemo.parentElement.setAttribute('data-live-minis', '1'); }
    var feat = MKT.products.filter(function (p) { return promoted(p, 'featured_until'); }).slice(0, 3);
    [['[data-live-sponsored]', '.sponsored-card', MKT.tplS, sponsoredCard], ['[data-live-minis]', '.sp-mini', MKT.tplM, sponsoredMini]].forEach(function (k) {
      var box = mk.querySelector(k[0]); if (!box) return; box.querySelectorAll(k[1]).forEach(function (x) { x.remove(); });
      if (k[2]) feat.forEach(function (p, i) { var c = k[3](p); if (i === feat.length - 1 && k[1] === '.sponsored-card') c.style.marginBottom = '0'; box.appendChild(c); });
      box.style.display = feat.length ? '' : 'none';                 /* no paid placement → no sponsored block (the demo's samples never show) */
    });
  }
  function paintMarket() {
    var mk = document.getElementById('mkx'); if (!mk) return;
    var anyL = mk.querySelector('.lcard'), anyD = mk.querySelector('.dcard');
    if (!MKT.tplL && anyL) MKT.tplL = anyL.outerHTML; if (!MKT.tplD && anyD) MKT.tplD = anyD.outerHTML;
    var grid = mk.querySelector('.supply-grid');
    if (grid && MKT.tplL) { grid.querySelectorAll('.lcard, .dx-mk-empty').forEach(function (x) { x.remove(); }); MKT.products.forEach(function (p) { grid.appendChild(supplyCard(p)); });
      if (!MKT.products.length) grid.insertAdjacentHTML('beforeend', '<div class="dx-mk-empty" style="padding:18px;color:#65676b;font-size:13px">No supply listings yet — be the first to post one.</div>'); }
    if (anyD) anyD.parentElement.setAttribute('data-live-demand', '1');          /* remember where demand cards live, even after they are cleared */
    var dgrid = mk.querySelector('[data-live-demand]');
    if (dgrid && MKT.tplD) { dgrid.querySelectorAll('.dcard').forEach(function (x) { x.remove(); });   /* under the board's heading, above "Latest Jobs" — where the approved cards are */
      var at = dgrid.querySelector('.db-sub'); MKT.demand.forEach(function (e) { var c = demandCard(e); if (at) { at.insertAdjacentElement('afterend', c); at = c; } else dgrid.appendChild(c); }); }
    paintSponsored(mk);
    /* ticker: admin items if any, otherwise the newest real listings */
    if (window.TICKER_ITEMS && typeof window.buildTicker === 'function') {
      var items = MKT.products.slice(0, 6).map(function (p) { return { label: 'Supply', text: p.name + (p.price ? ' ' + p.price : '') }; })
        .concat(MKT.demand.slice(0, 6).map(function (e) { return { label: 'Demand', text: e.title }; }));
      if (items.length) { window.TICKER_ITEMS.length = 0; items.forEach(function (x) { window.TICKER_ITEMS.push(x); }); window.buildTicker(); }
    }
  }
  /* Contact / Quote on a live card → a conversation with that person; a featured mini card shows its listing */
  document.addEventListener('click', function (e) {
    var mini = e.target.closest && e.target.closest('#mkx .sp-mini[data-live]');
    if (mini) { e.preventDefault(); e.stopPropagation(); var tg = document.querySelector('#mkx .sponsored-card[data-live="' + mini.dataset.live + '"]'); if (tg) tg.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
    var b = e.target.closest && e.target.closest('#mkx [data-live] .btn-contact, #mkx [data-live] .btn-contact-gold, #mkx [data-live] .qt-btn'); if (!b) return;
    var card = b.closest('[data-live]'); e.preventDefault(); e.stopPropagation(); window.messageUser(+card.dataset.uid);
  }, true);
  var origRenderMarket = window.renderMarket;
  window.renderMarket = function () {
    var r = origRenderMarket.apply(this, arguments); if (!ME_UUID) return r;
    paintMarket();
    if (Date.now() - MKT.at > 20000) loadMarket().then(function () { if (document.body.getAttribute('data-page') === 'market') paintMarket(); }).catch(toastErr);
    return r;
  };
  /* publishing from the listing wizard */
  window.dxLiveHook = function (kind, d) {
    if (kind === 'dockMessage') return dockMessage(d);
    if (kind !== 'listing' || !ME_UUID || !d) return;
    if (d.type === 'job') { window.toast('Job posts from the marketplace go live with the Jobs update — use the Jobs page for now'); return; }
    var q = d.type === 'demand'
      ? sb.from('enquiries').insert({ user_id: ME_UUID, type: 'demand', category: CAT[d.type] || 'other', title: d.title, body: [d.desc, d.moq, d.where].filter(Boolean).join(' · '), status: 'active', country: 'EG' })
      : sb.from('products').insert({ user_id: ME_UUID, type: 'supply', category: CAT[d.type] || 'other', name: d.title, price: d.price || null, moq: d.moq || null, description: d.desc || '', docs: d.certs || [], lead_time: d.lead || null, active: true });
    q.then(function (r) { if (r.error) { toastErr(r.error); return; } MKT.at = 0; loadMarket().then(function () { if (document.body.getAttribute('data-page') === 'market') paintMarket(); }); });
  };
  onReset(function () { MKT.products = []; MKT.demand = []; MKT.at = 0; });
  Object.assign(window.dxLive, { loadMarket: loadMarket, version: 'D1' });

  /* ═══════════════ D2a — jobs page from the database (the approved job card is the template) ═══════════════ */
  var JX = { tpl: null, jobs: [], saved: {}, applied: {}, at: 0, cur: null };
  var LEVEL = { entry: '🌱 Entry Level', junior: '⚙️ Junior', mid: '🎯 Mid-Level', senior: '🧭 Senior Mgmt', exec: '👑 Executive' };
  function levelOf(exp) { var n = parseInt(String(exp || '').match(/\d+/) || 0, 10); return !exp ? 'mid' : n < 1 ? 'entry' : n < 3 ? 'junior' : n < 5 ? 'mid' : n < 10 ? 'senior' : 'exec'; }
  async function loadJobs() {
    var a = await Promise.all([
      sb.from('jobs').select('*, poster:profiles!jobs_user_id_fkey(' + PCOLS + ')').eq('active', true).order('created_at', { ascending: false }).limit(60),
      sb.from('saved_jobs').select('job_id').eq('user_id', ME_UUID), sb.from('job_applications').select('job_id').eq('user_id', ME_UUID)]);
    if (a[0].error) throw a[0].error;
    JX.jobs = a[0].data || []; JX.saved = {}; JX.applied = {}; (a[1].data || []).forEach(function (x) { JX.saved[x.job_id] = 1; }); (a[2].data || []).forEach(function (x) { JX.applied[x.job_id] = 1; });
    JX.jobs.forEach(function (j) { putUser(j.poster); }); JX.at = Date.now();
  }
  function jobCard(j) {
    var c = el(JX.tpl), u = j.poster || {}, lvl = LEVEL[j.seniority] ? j.seniority : 'mid';
    c.dataset.cat = j.category || 'other'; c.dataset.level = lvl; c.dataset.live = 'j' + j.id; c.dataset.uid = aid(j.user_id);
    var logo = c.querySelector('.jc-logo'); if (logo) { logo.textContent = initials(j.company || u.name); logo.style.background = colorFor(j.company || j.user_id); }
    var t = c.querySelector('.jc-title'); if (t) { var rb = t.querySelector('.role-badge'), lb = t.querySelector('.level-badge'); t.textContent = j.title;
      if (lb) { lb.className = 'level-badge level-' + lvl; lb.textContent = LEVEL[lvl]; t.insertBefore(lb, t.firstChild); } if (rb) t.insertBefore(rb, t.firstChild); }
    var co = c.querySelector('.jc-company'); if (co) co.innerHTML = '<span>' + esc2(j.company || u.company || '') + '</span> · <span>' + (FLAG[j.country] || '') + ' ' + esc2(j.location || '') + '</span>' + (u.verified ? ' · <span style="color:#1a56db">✓ Verified</span>' : '');
    var tg = c.querySelector('.jc-tags'); if (tg) tg.innerHTML = '<span class="jt jt-ft">' + esc2(j.type || 'Full-time') + '</span>' + (j.tags || []).slice(0, 2).map(function (x) { return '<span class="jt" style="background:#dbeafe;color:#1d4ed8">' + esc2(x) + '</span>'; }).join('') + (j.salary ? '<span class="jt" style="background:#dcfce7;color:#15803d">' + esc2(j.salary) + '</span>' : '');
    var ds = c.querySelector('.jc-desc'); if (ds) ds.textContent = j.description || '';
    var ps = c.querySelector('.jc-posted'); if (ps) ps.textContent = ago(j.created_at);
    var ap = c.querySelector('.apply-btn'); if (ap) { ap.setAttribute('onclick', 'openApplyModal(' + JSON.stringify(j.title) + ',' + JSON.stringify(j.company || '') + ')');   /* setAttribute takes raw text: no HTML escaping */ if (JX.applied[j.id]) { ap.textContent = '✓ Applied'; ap.disabled = true; } }
    var sv = c.querySelector('.save-btn'); if (sv) sv.textContent = JX.saved[j.id] ? '✓ Saved' : '🔖 Save';
    return c;
  }
  function paintJobs() {
    var root = document.getElementById('jx'); if (!root) return;
    var hiring = [].slice.call(root.querySelectorAll('.jcard')).filter(function (c) { return c.querySelector('.role-badge.have') && !c.dataset.live; });
    if (hiring.length) { if (!JX.tpl) JX.tpl = hiring[0].outerHTML; hiring[0].parentElement.setAttribute('data-live-jobs', '1'); }
    var list = root.querySelector('[data-live-jobs]'); if (!list || !JX.tpl) return;
    [].slice.call(list.querySelectorAll('.jcard, .dx-jx-empty')).filter(function (c) { return c.classList.contains('dx-jx-empty') || c.querySelector('.role-badge.have'); }).forEach(function (x) { x.remove(); });
    var anchor = list.querySelector('.jcard');                      /* real jobs go before any candidate cards */
    JX.jobs.forEach(function (j) { list.insertBefore(jobCard(j), anchor); });
    if (!JX.jobs.length) list.insertAdjacentHTML('afterbegin', '<div class="dx-jx-empty" style="padding:18px;color:#65676b;font-size:13px">No open jobs yet.</div>');
  }
  /* remember which job an Apply belongs to; save toggles */
  document.addEventListener('click', function (e) {
    var card = e.target.closest && e.target.closest('#jx [data-live]'); if (!card || !ME_UUID) return;
    var id = +card.dataset.live.slice(1);
    if (e.target.closest('.apply-btn')) JX.cur = id;
    if (e.target.closest('.save-btn')) { e.preventDefault(); e.stopPropagation(); var on = !JX.saved[id], btn = e.target.closest('.save-btn');
      (on ? sb.from('saved_jobs').upsert({ user_id: ME_UUID, job_id: id }) : sb.from('saved_jobs').delete().eq('user_id', ME_UUID).eq('job_id', id)).then(function (r) {
        if (r.error) return toastErr(r.error); if (on) JX.saved[id] = 1; else delete JX.saved[id]; btn.textContent = on ? '✓ Saved' : '🔖 Save'; window.toast(on ? 'Job saved' : 'Removed from saved jobs'); }); }
  }, true);
  function wrapJobFns() {
  if (window.submitApply && !window.submitApply.__live) { var oApply = window.submitApply;
  window.submitApply = function () {
    if (!ME_UUID || !JX.cur) return oApply.apply(this, arguments);
    var id = JX.cur, m = document.getElementById('applyModal'), note = ((m && m.querySelector('textarea')) || {}).value || '';
    var cvIn = document.getElementById('dxCv'), cv = cvIn && cvIn.files && cvIn.files[0];
    (cv ? upDoc('documents', 'cv/' + ME_UUID + '/' + rid() + '.' + extOf(cv), cv) : Promise.resolve(null)).then(function (cvPath) { return sb.from('job_applications').insert({ job_id: id, user_id: ME_UUID, note: note.trim(), status: 'submitted', cv_path: cvPath }); }, function (e) { return { error: e }; }).then(function (r) {
      if (r.error) { window.toast(/duplicate|unique/i.test(r.error.message) ? 'You already applied to this job' : friendly(r.error)); return; }
      if (cvIn) cvIn.value = ''; JX.applied[id] = 1; oApply(); var b = document.querySelector('#jx [data-live="j' + id + '"] .apply-btn'); if (b) { b.textContent = '✓ Applied'; b.disabled = true; } });
  }; window.submitApply.__live = true; }
  if (window.openPostJobModal && !window.openPostJobModal.__live) { var oOpenPost = window.openPostJobModal;
  window.openPostJobModal = function () { var r = oOpenPost.apply(this, arguments); if (!ME_UUID) return r;
    var co = window.dxDir && window.dxDir.mine && window.dxDir.mine(), f = document.querySelector('#postJobModal input[disabled]'); if (f) f.value = co ? co.name : (window.ME.company || ''); return r; }; window.openPostJobModal.__live = true; }
  if (window.submitGeneric && !window.submitGeneric.__live) { var oGeneric = window.submitGeneric;
  window.submitGeneric = function (msg) {
    var m = document.getElementById('postJobModal');
    if (!ME_UUID || !m || !m.classList.contains('show')) return oGeneric.apply(this, arguments);
    /* the form is read by its structure (field order, option position), never by its English text — it works in Arabic too (F-21):
       editable inputs in order = title, location, years of experience, salary min, salary max */
    var f = [].slice.call(m.querySelectorAll('input.field-input:not([disabled])')).map(function (x) { return String(x.value || '').trim(); });
    var pos = function (sel) { var all = [].slice.call(m.querySelectorAll(sel)); return all.indexOf(m.querySelector(sel + '.selected')); };
    var dept = m.querySelector('select'), ta = m.querySelector('textarea'), title = f[0] || '', exp = f[2] || '', co = window.dxDir && window.dxDir.mine && window.dxDir.mine();
    if (!title) { window.toast('Add the job title'); return; }
    var sal = [f[3], f[4]].filter(Boolean).join(' – ');
    var row = { user_id: ME_UUID, title: title, company: co ? co.name : (window.ME.company || ''), location: f[1] || '', country: 'EG', type: ['Full-time', 'Part-time', 'Contract', 'Remote'][pos('.radio-opt')] || 'Full-time',
      seniority: levelOf(exp), category: dept ? (['regulatory', 'qaqc', 'production', 'sales', 'rd'][dept.selectedIndex] || 'other') : 'other', description: ta ? ta.value.trim() : '', salary: sal || null, tags: exp ? [exp + ' yrs exp'] : [], active: true };
    sb.from('jobs').insert(row).then(function (r) { if (r.error) return toastErr(r.error); oGeneric(msg || 'Job posted'); JX.at = 0;
      loadJobs().then(function () { if (document.body.getAttribute('data-page') === 'jobs') paintJobs(); }); });
  }; window.submitGeneric.__live = true; }
  }
  var origRenderJobs = window.renderJobs;
  window.renderJobs = function () {
    var r = origRenderJobs.apply(this, arguments); if (!ME_UUID) return r;
    wrapJobFns(); setTimeout(wrapJobFns, 0); paintJobs(); if (Date.now() - JX.at > 3000 && !JX.loading) { JX.loading = true; loadJobs().then(function () { JX.loading = false; if (document.body.getAttribute('data-page') === 'jobs') paintJobs(); }, function (e) { JX.loading = false; toastErr(e); }); }   /* show what we have, then the latest */
    return r;
  };
  onReset(function () { JX.jobs = []; JX.saved = {}; JX.applied = {}; JX.at = 0; JX.cur = null; });
  Object.assign(window.dxLive, { loadJobs: loadJobs, version: 'D2a' });

  /* ═══════════════ Intro videos on Supabase Storage (replaces the demo's in-browser storage, same interface) ═══════════════ */
  var PV = {};                                                      /* person uuid → intro_video (cached) */
  /* only the fixed intro paths ever become a URL — the stored value is never trusted (F-02) */
  var VPATH = /^(people\/[0-9a-f-]{36}|companies\/\d+)\/intro(-poster\.jpg|\.(webm|mp4|mov))$/;
  function pubUrl(path, v) { if (!VPATH.test(String(path || ''))) return ''; return CFG.url + '/storage/v1/object/public/videos/' + path + (+v ? '?v=' + (+v) : ''); }
  function target(key) {
    var kind = key.slice(0, 1), id = key.slice(2);
    if (kind === 'c') { var raw = CO.raw[id]; return raw && raw.id ? { kind: 'c', folder: 'companies/' + raw.id, row: raw, table: 'companies', rowId: raw.id } : null; }
    var u = uuidOf(+id); return u ? { kind: 'p', folder: 'people/' + u, uuid: u, table: 'profiles', rowId: u } : null;
  }
  async function current(t) { if (t.kind === 'c') return t.row.intro_video || null;
    if (!(t.uuid in PV)) { var r = await sb.from('profiles').select('intro_video').eq('id', t.uuid).single(); PV[t.uuid] = (r.data && r.data.intro_video) || null; } return PV[t.uuid]; }
  function dataUrlBlob(u) { var m = /^data:([^;]+);base64,(.*)$/.exec(u || ''); if (!m) return null; var bin = atob(m[2]), arr = new Uint8Array(bin.length); for (var i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i); return new Blob([arr], { type: m[1] }); }
  window.dxMedia = {
    put: async function (key, file, meta) {
      var t = target(key); if (!t) throw new Error('Save your company or profile first');
      var ext = /webm/.test(file.type) ? 'webm' : /quicktime/.test(file.type) ? 'mov' : 'mp4', path = t.folder + '/intro.' + ext, poster = t.folder + '/intro-poster.jpg', before = await current(t), v = Date.now();
      var up = await sb.storage.from('videos').upload(path, file, { upsert: true, contentType: file.type }); if (up.error) throw new Error(friendly(up.error));
      var pb = dataUrlBlob(meta.poster); if (pb) { var pu = await sb.storage.from('videos').upload(poster, pb, { upsert: true, contentType: 'image/jpeg' }); if (pu.error) throw new Error(friendly(pu.error)); }
      if (before && before.path && before.path !== path) await sb.storage.from('videos').remove([before.path]);
      var val = { path: path, poster: pb ? poster : null, duration: Math.round(meta.duration * 10) / 10, v: v };
      var r = await sb.from(t.table).update({ intro_video: val }).eq('id', t.rowId).select('id'); if (r.error || !(r.data || []).length) throw new Error(friendly(r.error || 'Only the owner can change this video'));
      if (t.kind === 'c') t.row.intro_video = val; else PV[t.uuid] = val;
      return { poster: val.poster ? pubUrl(val.poster, v) : '', duration: val.duration };
    },
    meta: async function (key) { var t = target(key); if (!t) return null; var c = await current(t); return c && pubUrl(c.path) ? { poster: c.poster ? pubUrl(c.poster, c.v) : '', duration: +c.duration || 0 } : null; },
    url: async function (key) { var t = target(key); if (!t) return null; var c = await current(t); return c ? pubUrl(c.path, c.v) || null : null; },
    remove: async function (key) { var t = target(key); if (!t) return; var c = await current(t); if (!c) return;
      await sb.storage.from('videos').remove([c.path].concat(c.poster ? [c.poster] : []));
      var r = await sb.from(t.table).update({ intro_video: null }).eq('id', t.rowId); if (r.error) throw new Error(friendly(r.error));
      if (t.kind === 'c') t.row.intro_video = null; else PV[t.uuid] = null; }
  };

  /* opening the profile of someone not seen yet — or seen only in a list (no website / certifications): fetch the whole row first
     (the interface's U() would otherwise fall back to me) */
  var oGotoProfile = window.gotoProfile;
  window.gotoProfile = function (uid) {
    var a = parseInt(uid, 10), u = uuidOf(a), self = this, args = arguments;
    if (ME_UUID && u && u !== ME_UUID && !window.USERS.some(function (x) { return x.id === a && x.full; })) {
      sb.from('profiles').select('*').eq('id', u).single().then(function (r) { if (r.data) putUser(r.data); oGotoProfile.apply(self, args); }, function () { oGotoProfile.apply(self, args); });
      return;
    }
    return oGotoProfile.apply(this, arguments);
  };
  window.dxLive.version = 'D2a+video';

  /* ═══════════════ D2b — jobs trust layer: candidates, reviews, references, private lists (through the approved code's store) ═══════════════ */
  var TR = { reviews: {}, refs: [], lists: { employer: { white: {}, black: {} }, candidate: { white: {}, black: {} } }, inter: {}, party: {}, cands: [], tplC: null, loaded: false, snap: {} };
  window.dxLiveTrust = { company: function () { var co = window.dxDir && window.dxDir.mine && window.dxDir.mine(); return co ? co.name : ((window.ME || {}).company || ''); },
                         name: function () { return (window.ME || {}).name || ''; } };
  function fill(obj, src) { Object.keys(obj).forEach(function (k) { delete obj[k]; }); Object.keys(src).forEach(function (k) { obj[k] = src[k]; }); return obj; }
  function partyOfUuid(u) { for (var n in TR.party) if (TR.party[n].uuid === u) return n; return null; }
  async function loadTrust() {
    var c = await sb.rpc('open_candidates', { p_limit: 40 }); if (c.error) throw c.error; TR.cands = c.data || [];
    TR.party = {};
    (JX.jobs || []).forEach(function (j) { var co = (window.dxLiveCompanies || []).find(function (x) { return x.name === j.company; }), raw = co && CO.raw[co.slug];
      if (j.company) TR.party[j.company] = { uuid: (raw && raw.owner_id) || j.user_id, role: 'employer' }; });
    TR.cands.forEach(function (p) { putUser(p); TR.party[p.name] = { uuid: p.id, role: 'candidate' }; });
    var emp = [], cnd = []; Object.keys(TR.party).forEach(function (n) { (TR.party[n].role === 'employer' ? emp : cnd).push(TR.party[n].uuid); });
    var q = await Promise.all([sb.rpc('get_reviews_many', { p_ids: emp, p_role: 'employer' }), sb.rpc('get_reviews_many', { p_ids: cnd, p_role: 'candidate' }),
      /* the references of the candidates on the page and my own — not the first 500 of the whole platform (F-50) */
      sb.from('work_references').select('*, au:profiles!work_references_author_fkey(name,company), ca:profiles!work_references_candidate_fkey(name)')
        .or('candidate.in.(' + cnd.concat([ME_UUID]).join(',') + '),author.eq.' + ME_UUID).order('created_at', { ascending: false }).limit(500),
      sb.from('job_lists').select('*, t:profiles!job_lists_target_fkey(name)').eq('owner', ME_UUID), sb.rpc('my_interactions')]);
    var rv = {};
    [q[0], q[1]].forEach(function (r) { (r.data || []).forEach(function (x) { var n = partyOfUuid(x.reviewee); if (!n) return;
      (rv[n] = rv[n] || []).push({ by: x.author || 'Anonymous', anon: x.anonymous ? 1 : 0, when: String(x.created_at).slice(0, 7), c: [x.c1, x.c2, x.c3, x.c4], text: x.body, mine: !!x.mine, _id: x.id }); }); });
    fill(TR.reviews, rv);
    TR.refs.length = 0; (q[2].data || []).forEach(function (x) { TR.refs.push({ cand: x.ca && x.ca.name, company: x.au && (x.au.company || x.au.name), kind: x.kind, from: String(x.from_month).slice(0, 7), to: String(x.to_month).slice(0, 7),
      role: x.role_title, category: x.category || '', text: x.body, reply: x.reply || '', status: x.status, when: String(x.created_at).slice(0, 7), expires: x.expires_at ? String(x.expires_at).slice(0, 7) : '', _id: x.id }); });
    ['employer', 'candidate'].forEach(function (s) { fill(TR.lists[s].white, {}); fill(TR.lists[s].black, {}); });
    (q[3].data || []).forEach(function (x) { var n = x.t && x.t.name; if (n) TR.lists[x.side][x.list][n] = x.list === 'black' ? { reason: x.reason, note: x.note || '', until: x.until } : { since: String(x.created_at).slice(0, 10) }; });
    var it = {}; (q[4].data || []).forEach(function (x) { var n = partyOfUuid(x.party); if (n) it[n] = true; }); fill(TR.inter, it);
    TR.snap = { lists: JSON.stringify(TR.lists), refs: TR.refs.map(function (r) { return r._id + ':' + (r.reply || ''); }).join('|') };
    TR.loaded = true;
  }
  async function syncReviews(v) {
    for (var n in v) { var mine = (v[n] || []).filter(function (r) { return r.mine && !r._id; })[0], p = TR.party[n]; if (!mine || !p) continue;
      var r = await sb.from('job_reviews').upsert({ reviewer: ME_UUID, reviewee: p.uuid, reviewee_role: p.role, c1: mine.c[0], c2: mine.c[1], c3: mine.c[2], c4: mine.c[3], body: mine.text, anonymous: !!mine.anon }, { onConflict: 'reviewer,reviewee,reviewee_role' });
      if (r.error) { window.toast(/row-level|interaction/i.test(r.error.message) ? 'You can review only people or companies you have really dealt with (an application or a conversation)' : friendly(r.error)); await loadTrust(); if (window.dxJxPaint) window.dxJxPaint(); return; }
      mine._id = -1; }
  }
  async function syncRefs(list) {
    for (var i = 0; i < list.length; i++) { var x = list[i], p = TR.party[x.cand];
      if (!x._id) { x._id = -1;
        if (!p) continue;
        if (x.kind === 'warn') {
          if (!DOCS.ev) { window.toast('Attach the evidence document — a warning is never sent without it. Nothing was submitted.'); await loadTrust(); if (window.dxJxPaint) window.dxJxPaint(); return; }
          var ev; try { ev = await upDoc('reference-evidence', ME_UUID + '/' + rid() + '.' + extOf(DOCS.ev), DOCS.ev); } catch (e) { toastErr(e); await loadTrust(); return; }
          DOCS.ev = null;
          var w = await sb.from('work_references').insert({ author: ME_UUID, candidate: p.uuid, kind: 'warn', role_title: x.role, from_month: x.from + '-01', to_month: x.to + '-01', category: x.category, body: x.text, evidence_path: ev });
          if (w.error) { toastErr(w.error); await loadTrust(); if (window.dxJxPaint) window.dxJxPaint(); return; }
          continue;
        }
        var r = await sb.from('work_references').insert({ author: ME_UUID, candidate: p.uuid, kind: 'honor', role_title: x.role, from_month: x.from + '-01', to_month: x.to + '-01', body: x.text, status: 'published' });
        if (r.error) { toastErr(r.error); await loadTrust(); if (window.dxJxPaint) window.dxJxPaint(); return; } }
      else if (x._id > 0 && x.reply && TR.snap.refs.indexOf(x._id + ':' + x.reply) < 0) { var rr = await sb.rpc('reply_to_reference', { ref_id: x._id, reply_text: x.reply, dispute: false }); if (rr.error) toastErr(rr.error); }
    }
    TR.snap.refs = list.map(function (r) { return r._id + ':' + (r.reply || ''); }).join('|');
  }
  async function syncLists(v) {
    var before = JSON.parse(TR.snap.lists || '{}');
    for (var s in v) for (var l in v[s]) { var now = v[s][l], was = (before[s] && before[s][l]) || {};
      for (var n in now) if (!was[n]) { var p = TR.party[n]; if (!p) continue;
        var r = await sb.from('job_lists').upsert({ owner: ME_UUID, target: p.uuid, side: s, list: l, reason: now[n].reason || null, note: now[n].note || null, until: now[n].until || null }, { onConflict: 'owner,target,side' });
        if (r.error) { toastErr(r.error); await loadTrust(); if (window.dxJxPaint) window.dxJxPaint(); return; } }
      for (var m in was) if (!now[m] && !(v[s][l === 'white' ? 'black' : 'white'] || {})[m]) { var q = TR.party[m]; if (q) await sb.from('job_lists').delete().eq('owner', ME_UUID).eq('target', q.uuid).eq('side', s); } }
    TR.snap.lists = JSON.stringify(v);
  }
  window.dxKitHook = function (op, k, v) {
    if (!ME_UUID) return undefined;
    if (op === 'get') { if (k === 'jobReviews') return TR.reviews; if (k === 'jobRefs') return TR.refs; if (k === 'jobLists') return TR.lists; if (k === 'jobInteractions') return TR.inter; return undefined; }
    if (k === 'jobReviews') { syncReviews(v).catch(toastErr); return true; }
    if (k === 'jobRefs') { syncRefs(v).catch(toastErr); return true; }
    if (k === 'jobLists') { syncLists(v).catch(toastErr); return true; }
    if (k === 'jobInteractions') return true;
    return undefined;
  };
  function candCard(p) {
    var c = el(TR.tplC), u = window.U(aid(p.id));
    c.dataset.cat = 'other'; c.dataset.level = 'mid'; c.dataset.live = 'c' + aid(p.id); c.dataset.uid = aid(p.id);
    var logo = c.querySelector('.jc-logo'); if (logo) { logo.textContent = u.initials; logo.style.background = u.color; }
    var t = c.querySelector('.jc-title'); if (t) { var rb = t.querySelector('.role-badge'), lb = t.querySelector('.level-badge'); t.textContent = p.headline || 'Open to work'; if (lb) { lb.className = 'level-badge level-mid'; lb.textContent = LEVEL.mid; t.insertBefore(lb, t.firstChild); } if (rb) t.insertBefore(rb, t.firstChild); }
    var co = c.querySelector('.jc-company'); if (co) co.innerHTML = '<span>' + esc2(p.name) + '</span> · <span>' + (FLAG[p.country] || '') + ' ' + esc2(p.location || '') + '</span>' + (p.verified ? ' · <span style="color:#1a56db">✓ Verified</span>' : '');
    var tg = c.querySelector('.jc-tags'); if (tg) tg.innerHTML = '<span class="jt jt-ft">Open to work</span>';
    var ds = c.querySelector('.jc-desc'); if (ds) ds.textContent = p.bio || '';
    var ps = c.querySelector('.jc-posted'); if (ps) ps.textContent = ago(p.created_at);
    c.querySelectorAll('.jx-trust, .dx-vid-chip').forEach(function (x) { x.remove(); }); delete c.dataset.vid;
    return c;
  }
  var paintJobsD2a = paintJobs;
  paintJobs = function () {
    paintJobsD2a(); var root = document.getElementById('jx'); if (!root) return;
    var demo = [].slice.call(root.querySelectorAll('.jcard')).filter(function (c) { return c.querySelector('.role-badge.need') && !c.dataset.live; });
    if (demo.length) { if (!TR.tplC) TR.tplC = demo[0].outerHTML; demo[0].parentElement.setAttribute('data-live-cands', '1'); }
    var list = root.querySelector('[data-live-cands]'); if (!list || !TR.tplC) return;
    [].slice.call(list.querySelectorAll('.jcard')).filter(function (c) { return c.querySelector('.role-badge.need'); }).forEach(function (x) { x.remove(); });
    TR.cands.forEach(function (p) { list.appendChild(candCard(p)); });
    root.querySelectorAll('.jx-trust').forEach(function (x) { x.remove(); }); if (window.dxJxPaint) window.dxJxPaint();
    if (window.dxVideos) window.dxVideos.refresh();
  };
  document.addEventListener('click', function (e) {                /* Contact on a live candidate → a conversation with them */
    var b = e.target.closest && e.target.closest('#jx [data-live^="c"] .apply-btn'); if (!b) return; e.preventDefault(); e.stopPropagation();
    window.messageUser(+b.closest('[data-live]').dataset.uid);
  }, true);
  onReset(function () { fill(TR.reviews, {}); TR.refs.length = 0; TR.party = {}; TR.cands = []; TR.loaded = false; TR.snap = {}; fill(TR.inter, {});
    ['employer', 'candidate'].forEach(function (x) { fill(TR.lists[x].white, {}); fill(TR.lists[x].black, {}); }); PV = {}; DOCS.vf = {}; DOCS.ev = null; });
  var loadJobsD2a = loadJobs;
  loadJobs = async function () { await loadJobsD2a(); await loadTrust(); };
  var hydrateC3 = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateC3(uid); loadJobs().catch(function (e) { console.error(e); }); return me; };
  Object.assign(window.dxLive, { loadTrust: loadTrust, loadJobs: function () { return loadJobs(); }, version: 'D2b' });

  /* ═══════════════ D3 — groups page from the database (the approved group card is the template) ═══════════════ */
  var GX = { tpl: null, groups: [], mine: {}, at: 0, cur: null, loading: false, snap: {}, inv: {}, req: {}, act: {} };
  var GRAD = [['#1040a0', '#2D6BE4'], ['#0E6B4E', '#16A34A'], ['#6D28D9', '#A855F7'], ['#B45309', '#F59E0B'], ['#0E7490', '#06B6D4'], ['#BE185D', '#EC4899']];
  async function loadGroups() {
    var GCOLS = '*, creator:profiles!groups_created_by_fkey(' + PCOLS + ')';
    var a = await Promise.all([sb.from('groups').select(GCOLS).order('member_count', { ascending: false }).order('created_at', { ascending: false }).limit(60),
                               sb.from('group_members').select('group_id, role').eq('user_id', ME_UUID),
                               sb.from('group_invites').select('group_id, g:groups(' + GCOLS + ')').eq('user_id', ME_UUID).limit(50),
                               sb.from('group_join_requests').select('group_id').eq('user_id', ME_UUID).eq('status', 'pending').limit(50)]);
    if (a[0].error) throw a[0].error; if (a[1].error) throw a[1].error;
    GX.groups = a[0].data || [];
    GX.inv = {}; ((a[2] && a[2].data) || []).forEach(function (x) { GX.inv[x.group_id] = true; });
    GX.req = {}; ((a[3] && a[3].data) || []).forEach(function (x) { GX.req[x.group_id] = true; });
    var inv = ((a[2] && a[2].data) || []).map(function (x) { return x.g; }).filter(function (g) { return g && !GX.groups.some(function (y) { return y.id === g.id; }); });
    GX.groups = inv.concat(GX.groups);                                   /* groups I was invited to come first, so the invitation can be taken up (F-29) */
    var gone = (a[1].data || []).map(function (m) { return m.group_id; }).concat(Object.keys(GX.req).map(Number))
      .filter(function (id, i, l) { return l.indexOf(id) === i && !GX.groups.some(function (g) { return g.id === id; }); }).slice(0, 100);
    if (gone.length) { var mg = await sb.from('groups').select(GCOLS).in('id', gone); if (!mg.error) GX.groups = GX.groups.concat(mg.data || []); }   /* my groups (and my requests) outside the 60 biggest */
    GX.mine = {}; (a[1].data || []).forEach(function (m) { GX.mine[m.group_id] = m.role; }); GX.at = Date.now();
    GX.snap = {}; GX.groups.forEach(function (g) { if (GX.mine[g.id]) GX.snap[g.name] = true; putUser(g.creator); });
    if (GX.cur) GX.cur = GX.groups.find(function (g) { return g.id === GX.cur.id; }) || GX.cur;
    /* "N new posts this week" on the cards and "N new posts today" in the header (0027 group_activity, one call for every card) */
    var ids = GX.groups.map(function (g) { return g.id; }).slice(0, 100);
    if (ids.length) { var ac = await sb.rpc('group_activity', { p_ids: ids }); if (!ac.error) { GX.act = {}; (ac.data || []).forEach(function (x) { GX.act[x.group_id] = x; }); } }
  }
  function groupCard(g) {
    var c = el(GX.tpl), gr = GRAD[g.id % GRAD.length], joined = !!GX.mine[g.id];
    c.dataset.gid = g.id; c.setAttribute('onclick', 'dxLive.openGroup(' + g.id + ')');
    ['.priority-badge', '.member-faces'].forEach(function (s) { var x = c.querySelector(s); if (x) x.remove(); });
    var cv = c.querySelector('.gcard-cover'); if (cv) { cv.textContent = g.emoji || '👥'; cv.style.background = 'linear-gradient(135deg,' + gr[0] + ',' + gr[1] + ')'; }
    var t = c.querySelector('.gcard-title'); if (t) t.textContent = g.name;
    var d = c.querySelector('.gcard-desc'); if (d) d.textContent = g.description || '';
    var deal = /deal/i.test(g.topic || ''), m = c.querySelector('.gcard-meta');   /* the tag classes drive the page's Discussion / Deal Rooms filters */
    if (m) m.innerHTML = '<span class="gtag ' + (deal ? 'gtag-deal' : 'gtag-discuss') + '">' + esc2(g.topic || 'DISCUSS') + '</span><span class="gtag ' + (g.type === 'private' ? 'gtag-private">Private' : 'gtag-public">Public') + '</span>';
    var sig = c.querySelector('.activity-signal'), ac = GX.act[g.id];
    if (sig) { if (ac && ac.posts_week > 0) { sig.className = 'activity-signal'; sig.textContent = ac.posts_week.toLocaleString('en') + (ac.posts_week === 1 ? ' new post this week' : ' new posts this week'); } else sig.remove(); }
    var mc = c.querySelector('.member-count'); if (mc) mc.textContent = (g.member_count || 0).toLocaleString('en') + (g.member_count === 1 ? ' member' : ' members');
    /* what the inside of the group (groups.js) shows under About: the group's own text, rules, creation date and creator */
    c.dataset.about = txt(g.description || ''); c.dataset.rules = JSON.stringify(rulesOf(g.rules)); c.dataset.since = g.created_at || ''; c.dataset.by = g.created_by ? aid(g.created_by) : '';
    paintCardState(c, g);
    return c;
  }
  /* the card's button: ✓ Joined · + Join (public) · ✉️ Accept (invited) · 🔒 Request / ⏳ Requested (private) — as groups.js paints it */
  function cardState(g) { return GX.mine[g.id] ? 'joined' : GX.inv[g.id] ? 'accept' : g.type === 'private' ? (GX.req[g.id] ? 'pending' : 'request') : 'join'; }
  function paintCardState(c, g) {
    var b = c.querySelector('.gcard-btn'), st = cardState(g); if (!b) return;
    var on = st === 'joined', wait = st === 'pending';
    b.classList.toggle('btn-joined', on); b.classList.toggle('btn-join', !on && !wait); b.classList.toggle('gp-pending', wait);
    b.textContent = { joined: '✓ Joined', join: '+ Join', request: '🔒 Request', pending: '⏳ Requested', accept: '✉️ Accept' }[st];
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (st === 'pending' || st === 'request' || st === 'accept') b.dataset.gpq = st; else delete b.dataset.gpq;
    if (st === 'accept') c.dataset.invited = '1'; else delete c.dataset.invited;
    var mc = c.querySelector('.member-count'); if (mc) mc.textContent = (g.member_count || 0).toLocaleString('en') + (g.member_count === 1 ? ' member' : ' members');
  }
  /* groups.rules is plain text, one rule per line ("Title: explanation" or "Title — explanation") */
  function rulesOf(t) {
    return String(t || '').split(/\n+/).map(function (l) { return txt(l.trim()); }).filter(Boolean).slice(0, 20).map(function (l) {
      var m = /^(.{1,80}?)\s*(?:—|:|–)\s+(.+)$/.exec(l); return m ? [m[1], m[2]] : [l, '']; });
  }
  /* Only groups from the database show (G-02): every sample card goes, in every section. My groups fill "Your Groups"; groups I am
     not in fill the next two sections (discussion groups, then deal rooms), invitations first, then by activity. The side list,
     the "My Groups (N)" chip, the activity strip and the section counts come from the same rows (G-03, G-04). */
  var GSEC = ['mine', 'other', 'deal'];
  function actOf(g) { return GX.act[g.id] || { posts_today: 0, posts_week: 0 }; }
  function byActivity(a, b) { var x = actOf(a), y = actOf(b); return (GX.inv[b.id] ? 1 : 0) - (GX.inv[a.id] ? 1 : 0) || y.posts_today - x.posts_today || y.posts_week - x.posts_week || (b.member_count || 0) - (a.member_count || 0); }
  function myGroups() { return GX.groups.filter(function (g) { return !!GX.mine[g.id]; }).sort(byActivity); }
  /* change the words of one text node (found by its English original), keeping icons other layers put around it; the Arabic
     interface translates the new words like any other */
  function origOf(t) { return (window.dxI18nOrig && window.dxI18nOrig(t)) || t.nodeValue; }
  function setTextNode(root, re, make) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var t = w.currentNode, o = origOf(t); if (!re.test(o)) continue;
      var v = make(o); if (v !== o) t.nodeValue = v; return t; }
    return null;
  }
  function gxEmpty(text) { return '<div class="dx-gx-empty" style="padding:18px;color:#65676b;font-size:13px;grid-column:1/-1">' + text + '</div>'; }
  function paintGroups() {
    var root = document.getElementById('gx'); if (!root) return;
    var demo = [].slice.call(root.querySelectorAll('.gcard')).filter(function (c) { return !c.dataset.gid; });
    if (demo.length && !GX.tpl) GX.tpl = demo[0].outerHTML;
    demo.forEach(function (c) { c.remove(); });
    var grids = [].slice.call(root.querySelectorAll('.gx-groups-grid')).slice(0, 3); if (!grids.length || !GX.tpl) return;
    grids.forEach(function (gr, i) { gr.setAttribute('data-live-groups', GSEC[i]); gr.querySelectorAll('.gcard, .dx-gx-empty').forEach(function (x) { x.remove(); }); });
    var mine = myGroups(), rest = GX.groups.filter(function (g) { return !GX.mine[g.id]; }).sort(byActivity);
    var parts = [mine, rest.filter(function (g) { return !/deal/i.test(g.topic || '') || grids.length < 3; }), rest.filter(function (g) { return /deal/i.test(g.topic || ''); })];
    var empty = !GX.at ? ['Loading groups…', '', ''] : ['You have not joined a group yet — join one below or create your own.', 'No other discussion groups yet — create the first one.', 'No other deal rooms yet — create the first one.'];
    grids.forEach(function (gr, i) { parts[i].forEach(function (g) { gr.appendChild(groupCard(g)); }); if (!parts[i].length && empty[i]) gr.insertAdjacentHTML('beforeend', gxEmpty(empty[i])); });
    paintGroupsChrome(root, mine);
  }
  /* everything around the cards that the approved page fills with sample numbers */
  function paintGroupsChrome(root, mine) {
    var q = function (s) { return root.querySelector(s); }, today = mine.filter(function (g) { return actOf(g).posts_today > 0; });
    var items = root.querySelectorAll('.intel-strip .intel-item'), divs = root.querySelectorAll('.intel-strip .intel-divider');
    if (items[0]) { var b0 = items[0].querySelector('b'); if (b0) b0.textContent = today.length; }
    if (items[1]) { var b1 = items[1].querySelector('b'); if (b1) b1.textContent = today.reduce(function (t, g) { return t + actOf(g).posts_today; }, 0).toLocaleString('en');
      var t1 = b1 && b1.nextSibling; if (t1 && t1.nodeType === 3 && !/new posts today/.test(window.dxI18nOrig && window.dxI18nOrig(t1) || t1.nodeValue)) t1.nodeValue = ' new posts today in your groups'; }
    var hot = GX.groups.filter(function (g) { return actOf(g).posts_today > 0; }).sort(function (a, b) { return actOf(b).posts_today - actOf(a).posts_today; })[0];
    if (items[2]) { items[2].style.display = hot ? '' : 'none'; if (divs[1]) divs[1].style.display = hot ? '' : 'none';
      if (hot) { var b2 = items[2].querySelector('b'); if (b2) { b2.textContent = hot.name; b2.setAttribute('data-noi18n', '');
        var t2 = b2.nextSibling, n2 = actOf(hot).posts_today, v2 = ' trending — ' + n2 + (n2 === 1 ? ' post today' : ' posts today'); if (t2 && t2.nodeType === 3) { if ((window.dxI18nOrig && window.dxI18nOrig(t2)) !== v2 && t2.nodeValue !== v2) t2.nodeValue = v2; } else b2.insertAdjacentText('afterend', v2); } } }
    [].forEach.call(root.querySelectorAll('.cat-filter .cf-tag'), function (c) { setTextNode(c, /My Groups \(\d+\)/, function (o) { return o.replace(/\(\d+\)/, '(' + mine.length + ')'); }); });
    var hdrs = root.querySelectorAll('.main .sec-hdr');
    if (hdrs[0]) { var all0 = hdrs[0].querySelector('.sec-all'); if (all0) { var v0 = 'View all ' + mine.length + ' →'; if ((window.dxOrigText ? window.dxOrigText(all0) : all0.textContent).trim() !== v0) all0.textContent = v0; } }
    if (hdrs[1]) { var sub1 = hdrs[1].querySelector('.sec-sub'); if (sub1 && /Matched to your/.test(window.dxOrigText ? window.dxOrigText(sub1) : sub1.textContent)) sub1.textContent = 'Groups you have not joined yet — most active first'; }
    var ip = q('.intel-panel'); if (ip) ip.style.display = 'none';      /* the activity score is not measured in the live app */
    /* the side list "Your Groups": my groups from the database, each opens its own group */
    var side = q('.gx-sidebar'); if (!side) return;
    var rows = [].slice.call(side.querySelectorAll('.mygroup:not([data-gid])')); if (rows.length && !GX.tplMy) GX.tplMy = rows[0].outerHTML; rows.forEach(function (r) { r.remove(); });
    side.querySelectorAll('.mygroup[data-gid], .dx-mg-empty').forEach(function (r) { r.remove(); });
    var at = side.querySelector('.sb-divider'); if (!at || !GX.tplMy) return;
    if (!mine.length) { at.insertAdjacentHTML('beforebegin', '<div class="dx-mg-empty" style="padding:6px 8px 10px;color:#65676b;font-size:12.5px">' + (GX.at ? 'You have not joined a group yet.' : 'Loading groups…') + '</div>'); return; }
    mine.forEach(function (g, i) {
      var r = el(GX.tplMy), a = actOf(g), gr = GRAD[g.id % GRAD.length]; r.removeAttribute('onclick'); r.dataset.gid = g.id; r.setAttribute('role', 'button'); r.setAttribute('tabindex', '0');
      var ic = r.querySelector('.mg-ic'); if (ic) { ic.style.background = gr[0] + '22'; ic.textContent = g.emoji || '👥'; if (a.posts_today > 0) ic.insertAdjacentHTML('beforeend', '<div class="live-pulse"></div>'); }
      var nm = r.querySelector('.mg-name'); if (nm) nm.textContent = g.name;
      var mt = r.querySelector('.mg-meta'); if (mt) { mt.removeAttribute('style'); mt.textContent = a.posts_today > 0 ? a.posts_today + (a.posts_today === 1 ? ' new post today' : ' new posts today') : a.posts_week > 0 ? a.posts_week + (a.posts_week === 1 ? ' new post this week' : ' new posts this week') : 'Quiet today'; }
      var bd = r.querySelector('.mg-badge'); if (a.posts_today > 0) { if (!bd) { bd = document.createElement('div'); bd.className = 'mg-badge'; r.appendChild(bd); } bd.textContent = a.posts_today; } else if (bd) bd.remove();
      at.parentNode.insertBefore(r, at);
    });
  }
  /* my groups changed (joined / left): with a group open only the counts and lists around the cards follow (the open group keeps
     its card); otherwise the cards move to their sections too */
  function refreshMine() {
    var root = document.getElementById('gx'), gd = document.getElementById('groupDetail');
    if (root && gd && gd.classList.contains('show')) { paintGroupsChrome(root, myGroups()); if (typeof syncGroupsGlobal === 'function') syncGroupsGlobal(); }
    else paintGroups();
  }
  document.addEventListener('click', function (e) {                   /* a side-list row opens its group */
    var r = e.target.closest && e.target.closest('#gx .mygroup[data-gid]'); if (!r || !ME_UUID) return;
    e.preventDefault(); e.stopPropagation(); window.dxLive.openGroup(+r.dataset.gid);
  }, true);
  document.addEventListener('keydown', function (e) { if (e.key !== 'Enter' && e.key !== ' ') return; var r = e.target.closest && e.target.closest('#gx .mygroup[data-gid]'); if (r) { e.preventDefault(); r.click(); } });
  window.dxLive.openGroup = function (gid, tab) {
    var g = GX.groups.find(function (x) { return x.id === gid; }); if (!g || !document.getElementById('groupDetail')) return; GX.cur = g;   /* another page is on screen: nothing to open (G-16) */
    var card = document.querySelector('#gx .gcard[data-gid="' + gid + '"]');
    if (card && window.dxGroups && window.dxGroups.pick) window.dxGroups.pick(card, tab);   /* groups.js draws the inside of THIS group */
    var t = document.getElementById('dt-title'); if (t) t.textContent = g.name;
    window.openGroup(GX.mine[gid] === 'admin' ? 'admin' : 'member');
    var gc = document.querySelector('#groupDetail .group-cover'), cv = card && card.querySelector('.gcard-cover'); if (gc && cv) gc.style.background = cv.style.background;
    paintHead(g);
    if (GX.mine[gid] === 'admin') manageLoad(g);
  };
  /* joining / leaving goes through the approved code's store (groupsJoined, keyed by group name) */
  async function syncJoined(v) {
    for (var name in v) { var on = !!v[name], was = !!GX.snap[name], g = GX.groups.find(function (x) { return x.name === name; }); if (!g || on === was) continue;
      var r = on ? await sb.from('group_members').insert({ group_id: g.id, user_id: ME_UUID, role: 'member' }) : await sb.from('group_members').delete().eq('group_id', g.id).eq('user_id', ME_UUID);
      if (r.error) { toastErr(r.error); await loadGroups(); paintGroups(); return; }
      if (on) { GX.mine[g.id] = 'member'; GX.snap[name] = true; } else { delete GX.mine[g.id]; delete GX.snap[name]; } }
  }
  var hookD2b = window.dxKitHook;
  window.dxKitHook = function (op, k, v) {
    if (ME_UUID && k === 'groupsJoined') { if (op === 'get') return Object.assign({}, GX.snap); syncJoined(v || {}).catch(toastErr); return true; }
    return hookD2b ? hookD2b(op, k, v) : undefined;
  };
  /* Join / Joined on a live card (the approved code binds its button handler to its own cards only) */
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('#gx .gcard[data-gid] .gcard-btn'); if (!btn || !ME_UUID) return;
    e.preventDefault(); e.stopPropagation();
    var card = btn.closest('.gcard'), gid = +card.dataset.gid, g = GX.groups.find(function (x) { return x.id === gid; }); if (!g || btn.dataset.busy) return;
    var st = cardState(g), op = st === 'joined' ? 'leave' : st === 'pending' ? 'cancel' : st === 'request' ? 'request' : 'join'; btn.dataset.busy = '1';
    gpJoin(g, op).then(function () { delete btn.dataset.busy; }, function (e) { delete btn.dataset.busy; toastErr(e); });
  }, true);
  document.addEventListener('click', function (e) {
    if (!ME_UUID) return;
    var leave = e.target.closest && e.target.closest('#leaveConfirm .cp-btn-confirm');
    if (leave && GX.cur) { e.preventDefault(); e.stopPropagation(); var g = GX.cur;
      sb.from('group_members').delete().eq('group_id', g.id).eq('user_id', ME_UUID).then(function (r) { if (r.error) return toastErr(r.error);
        delete GX.mine[g.id]; delete GX.snap[g.name]; g.member_count = Math.max(0, (g.member_count || 1) - 1); window.closeGroup(); paintGroups(); window.toast('You left ' + g.name); }); return; }
    /* "Invite" in the admin view — the 2nd secondary button of #adminActions, found by its place, not its (translated) text —
       saves real invitations (group_invites, F-29); the approved toast shows only once they are saved */
    var inv = e.target.closest && e.target.closest('#adminActions .btn-secondary');
    if (inv && GX.cur && [].indexOf.call(document.querySelectorAll('#adminActions .btn-secondary'), inv) === 1) { e.preventDefault(); e.stopPropagation(); inviteDialog(GX.cur); return; }
    /* the approved window's Create button and its choices are found by their place in the markup, never by their (translated)
       text: the 2nd type option is Deal Room, the 2nd privacy option is Private (F-20, F-21) */
    var mk = e.target.closest && e.target.closest('#createModal .modal-footer .btn-create');
    if (mk) { e.preventDefault(); e.stopPropagation();
      var M = document.getElementById('createModal'), name = ((M.querySelector('.field-input') || {}).value || '').trim(), desc = ((M.querySelector('.field-textarea, textarea') || {}).value || '').trim();
      if (!name) { window.toast('Add the group name'); return; }
      var pos = function (sel) { var all = [].slice.call(M.querySelectorAll(sel)); return all.indexOf(M.querySelector(sel + '.selected')); };
      var priv = pos('.privacy-opt') === 1, deal = pos('.type-opt') === 1;
      if (mk.dataset.busy) return; mk.dataset.busy = '1';
      sb.from('groups').insert({ name: name, description: desc, emoji: deal ? '🤝' : '👥', type: priv ? 'private' : 'public', topic: deal ? 'DEAL ROOM' : 'DISCUSS', created_by: ME_UUID, listed: !(priv && deal) }).select().single().then(function (r) { delete mk.dataset.busy;
        if (r.error) return toastErr(r.error); window.closeCreate(); window.toast('Group created'); return loadGroups().then(paintGroups); }); return; }
    var del = e.target.closest && e.target.closest('#deleteConfirmBtn');
    if (del && GX.cur) { e.preventDefault(); e.stopPropagation(); var g2 = GX.cur, typed = ((document.getElementById('deleteConfirmInput') || {}).value || '').trim();
      if (typed !== g2.name && typed.toUpperCase() !== 'DELETE') { window.toast('Type the group name to confirm'); return; }
      sb.from('groups').delete().eq('id', g2.id).select().then(function (r) { if (r.error || !(r.data || []).length) return toastErr(r.error || { message: 'Only the group\u2019s creator can delete it' });
        window.closeDelete(); window.closeGroup(); window.toast(g2.name + ' was deleted'); return loadGroups().then(paintGroups); }); }
  }, true);
  /* the approved "Invite people" window; people are found by the name on their Drugbox profile (e-mail addresses are private) */
  function inviteDialog(g) {
    var D = window.DBK;
    D.modal({ title: 'Invite people', body: '<div class="dbk-f"><label for="ivE">Emails or names *</label><textarea id="ivE" data-req placeholder="one per line or separated by commas"></textarea></div><div class="dbk-f"><label for="ivM">Personal note</label><input id="ivM" placeholder="Optional"></div>',
      primary: { label: 'Send invites', onClick: function (box, close) {
        if (!D.requireFields(box)) return false;
        var ok = box.querySelector('[data-a=ok]') || (box.parentNode && box.parentNode.querySelector('[data-a=ok]')); if (ok) { if (ok.disabled) return false; ok.disabled = true; }
        var items = box.querySelector('#ivE').value.split(/[\n,;]+/).map(function (x) { return x.trim(); }).filter(Boolean).slice(0, 50);
        invitePeople(g, items).then(function (res) { if (ok) ok.disabled = false;
          if (!res.n) { D.toast(res.error || (res.missing.length ? 'No Drugbox member found for ' + res.missing.join(', ') + ' — use the name on their Drugbox profile' : 'Invite someone other than yourself')); return; }
          close(); D.toast('Invites sent to ' + res.n + (res.n === 1 ? ' person' : ' people'));
          if (res.missing.length) setTimeout(function () { D.toast('Not found on Drugbox: ' + res.missing.join(', ')); }, 2200); },
          function (err) { if (ok) ok.disabled = false; toastErr(err); });
        return false; } } });
  }
  async function invitePeople(g, items) {
    var ids = [], missing = [];
    var found = await Promise.all(items.map(function (x) {
      if (x.indexOf('@') >= 0 || x.length > 120) return null;                                           /* no lookup by e-mail address */
      return sb.from('profiles').select('id').ilike('name', x.replace(/[\\%_]/g, '\\$&')).limit(2);
    }));
    found.forEach(function (r, i) { var d = r && !r.error ? r.data || [] : [];
      if (d.length === 1 && d[0].id !== ME_UUID) { if (ids.indexOf(d[0].id) < 0) ids.push(d[0].id); } else if (!(d.length === 1 && d[0].id === ME_UUID)) missing.push(items[i] + (d.length > 1 ? ' (more than one member has this name)' : '')); });
    if (!ids.length) return { n: 0, missing: missing };
    var r = await sb.from('group_invites').upsert(ids.map(function (u) { return { group_id: g.id, user_id: u, invited_by: ME_UUID }; }), { onConflict: 'group_id,user_id', ignoreDuplicates: true });
    if (r.error) return { n: 0, missing: missing, error: /row-level security|42501|permission/i.test(String(r.error.message || r.error.code)) ? 'Only the group\u2019s admins can invite people' : friendly(r.error) };
    return { n: ids.length, missing: missing };
  }
  var origRenderGroups = window.renderGroups;
  window.renderGroups = function () {
    var r = origRenderGroups.apply(this, arguments); if (!ME_UUID) return r;
    paintGroups();
    if (Date.now() - GX.at > 3000 && !GX.loading) { GX.loading = true; loadGroups().then(function () { GX.loading = false; if (document.body.getAttribute('data-page') === 'groups') paintGroups(); }, function (e) { GX.loading = false; toastErr(e); }); }
    return r;
  };

  /* ═══════════════ D3b — inside a group (0027): discussion, members, about, joining, join requests, the admin's Manage panel ═══════════════
     groups.js draws the inside of a group from the approved Home post card and member rows and asks for its data through
     dxLiveHook(kind, payload). A group post IS a post (posts.group_id): likes, comments, photos/files, saves and their
     notifications are the feed's own tables; who may read or write them is decided by the database (0027), never here. */
  var RK_IN = { love: 'support' }, RK_OUT = { support: 'love', appreciation: 'like' };   /* reactions.kind: like love insightful celebrate curious */
  function gOf(d) { var gid = d && d.group ? +d.group.gid : 0, g = GX.groups.find(function (x) { return x.id === gid; }); if (!g) throw new Error('This group is no longer available — open the Groups page again'); return g; }
  function joinedAgo(ts) {
    var d = (Date.now() - new Date(ts).getTime()) / 86400000, n, u;
    if (!(d >= 1)) return 'Joined just now';
    if (d < 7) { n = Math.floor(d); u = 'day'; } else if (d < 30) { n = Math.floor(d / 7); u = 'week'; } else if (d < 365) { n = Math.floor(d / 30); u = 'month'; } else { n = Math.floor(d / 365); u = 'year'; }
    return 'Joined ' + n + ' ' + u + (n === 1 ? '' : 's') + ' ago';
  }
  function gpPost(r, my, saved, cm, pin) {
    var media = r.post_media || [], k = my[r.id], n = r.like_count || 0, rx = n ? { like: n } : {}, kk = k ? (RK_IN[k] || k) : null, c = cm[r.id] || [];
    if (kk && kk !== 'like' && n) { rx.like--; if (!rx.like) delete rx.like; rx[kk] = 1; }
    return { id: r.id, uid: aid(r.user_id), cat: r.category || 'general', body: r.body || '', ts: ago(r.created_at), created_at: r.created_at,
      likes: n, rx: rx, liked: !!k, rk: kk, cmt: Math.max(0, (r.comment_count || 0) - c.length), cm: c, sh: r.share_count || 0, views: r.view_count || 0,
      saved: saved.has(r.id), pin: !!pin && r.id === pin, own: r.user_id === ME_UUID,
      imgs: media.filter(function (m) { return m.type === 'image' && safeUrl(m.url); }).map(function (m) { return safeUrl(m.url); }),
      files: media.filter(function (m) { return m.type !== 'image' && safeUrl(m.url); }).map(function (m) { return { name: txt(m.name), size: +m.size || 0, url: safeUrl(m.url) }; }) };
  }
  /* one request per page: the posts with their author and files, MY reaction and save (embedded rows filtered to me) and each post's
     latest 20 comments — the database's row rules apply to every embedded row as to the posts themselves */
  function gpQuery(g) {
    return sb.from('posts').select('*, author:profiles!posts_user_id_fkey(' + PCOLS + '), post_media(*), my:reactions(kind, user_id), sv:saved_posts(user_id), ' +
      'cm:comments(post_id, user_id, body, created_at, author:profiles!comments_user_id_fkey(' + PCOLS + '))')
      .eq('group_id', g.id).eq('my.user_id', ME_UUID).eq('sv.user_id', ME_UUID)
      .order('created_at', { referencedTable: 'cm', ascending: false }).order('id', { referencedTable: 'cm', ascending: false }).limit(20, { referencedTable: 'cm' });
  }
  /* one page of a group's posts (keyset on created_at, id — as the Home feed, index idx_posts_group_feed); the pinned post
     (groups.pinned_post_id) comes first on page 1 and is skipped on later pages */
  async function gpPage(g, cursor) {
    var pin = g.pinned_post_id || null;
    var q = gpQuery(g).order('created_at', { ascending: false }).order('id', { ascending: false }).limit(PAGE);
    if (cursor) q = q.lte('created_at', cursor.t).or('created_at.lt.' + cursor.t + ',and(created_at.eq.' + cursor.t + ',id.lt.' + cursor.id + ')');
    var jobs = [q]; if (!cursor && pin) jobs.push(gpQuery(g).eq('id', pin).limit(1));
    var a = await Promise.all(jobs); if (a[0].error) throw a[0].error;
    var rows = a[0].data || [], last = rows[rows.length - 1], full = rows.length === PAGE;
    if (a[1] && !a[1].error && (a[1].data || []).length && !rows.some(function (x) { return x.id === pin; })) rows = a[1].data.concat(rows);
    if (cursor && pin) rows = rows.filter(function (x) { return x.id !== pin; });
    var my = {}, saved = new Set(), cm = {};
    rows.forEach(function (x) {
      putUser(x.author);
      if ((x.my || []).length) my[x.id] = x.my[0].kind || 'like';
      if ((x.sv || []).length) saved.add(x.id);
      cm[x.id] = (x.cm || []).slice().reverse().map(function (c) { putUser(c.author); return { uid: aid(c.user_id), text: c.body, ts: ago(c.created_at), likes: 0 }; });
    });
    var out = rows.map(function (x) { return gpPost(x, my, saved, cm, pin); });
    if (full && last) { var next = { t: last.created_at, id: last.id }; out.more = function () { return gpPage(g, next); }; }
    return out;
  }
  async function gpWrite(r, what) { r = await r; if (r.error) throw r.error; if (what && Array.isArray(r.data) && !r.data.length) throw new Error(what); return r.data; }
  /* every change made inside a group: groups.js shows it at once and undoes it when this refuses */
  async function gpOp(d) {
    var g = gOf(d), p = d.post || {}, id = p.id;
    switch (d.op) {
      case 'create': {
        var row = await gpWrite(sb.from('posts').insert({ user_id: ME_UUID, body: p.body || '', category: p.cat || 'general', group_id: g.id }).select().single());
        var imgs = p.imgs && p.imgs.length ? p.imgs : (d.imageFiles || []), files = d.file ? [d.file] : [];
        var m = imgs.length || files.length ? await uploadPostMedia(row.id, imgs, files) : { imgs: [], files: [] };
        var ac = GX.act[g.id] = GX.act[g.id] || { group_id: g.id, posts_today: 0, posts_week: 0 }; ac.posts_today++; ac.posts_week++;
        return { id: row.id, created_at: row.created_at, ts: 'just now', imgs: m.imgs, files: m.files, own: true };
      }
      case 'react': return gpWrite(sb.from('reactions').upsert({ post_id: id, user_id: ME_UUID, kind: RK_OUT[d.kind] || d.kind || 'like' }, { onConflict: 'post_id,user_id' }));
      case 'unreact': return gpWrite(sb.from('reactions').delete().eq('post_id', id).eq('user_id', ME_UUID));
      case 'comment': return gpWrite(sb.from('comments').insert({ post_id: id, user_id: ME_UUID, body: (d.comment && d.comment.text) || '' }));
      case 'commentLike': throw new Error('Liking comments is not available yet');
      case 'share': {   /* "Repost to your feed" (public groups only — groups.js never offers it for a private one) */
        var who = (window.USERS || []).find(function (u) { return u.id === p.uid; }) || window.ME;
        var body = ('Shared from ' + g.name + ' — ' + (who ? who.name : 'a member') + ':\n\n' + (p.body || '')).slice(0, 5000);
        await gpWrite(sb.from('posts').insert({ user_id: ME_UUID, body: body, category: p.cat || 'general' }));
        sb.rpc('increment_post_share', { p_id: id }).then(function () {}, function () {});
        FEED.at = 0; return;
      }
      case 'edit': return gpWrite(sb.from('posts').update({ body: p.body || '' }).eq('id', id).select('id'), 'This post could not be changed');
      case 'delete': case 'remove': {
        await gpWrite(sb.from('posts').delete().eq('id', id).select('id'), 'This post could not be removed');
        if (g.pinned_post_id === id) g.pinned_post_id = null; if (GX.cur && GX.cur.id === g.id && GX.mine[g.id] === 'admin') manageLoad(g); return;
      }
      case 'pin': case 'unpin': {
        var pr = await sb.rpc('group_pin_post', { p_group: g.id, p_post: d.op === 'pin' ? id : null }); if (pr.error) throw pr.error;
        g.pinned_post_id = d.op === 'pin' ? id : null; return;
      }
      case 'save': return gpWrite(sb.from('saved_posts').upsert({ user_id: ME_UUID, post_id: id }, { onConflict: 'user_id,post_id' }));
      case 'unsave': return gpWrite(sb.from('saved_posts').delete().eq('user_id', ME_UUID).eq('post_id', id));
      case 'report': {
        var why = (String(d.reason || 'Breaks the group rules') + (d.note ? ' — ' + d.note : '')).slice(0, 500);
        var rr = await sb.from('group_post_reports').insert({ post_id: id, reporter: ME_UUID, reason: why });
        if (rr.error && rr.error.code !== '23505') throw rr.error; return;   /* reported before: the admins already have it */
      }
    }
    throw new Error('This is not available yet');
  }
  /* members: admins first, then the newest (50 at a time); only what the database lets this person see (0013/0027) */
  async function gmList(g) {
    var r = await sb.from('group_members').select('user_id, role, joined_at, p:profiles!group_members_user_id_fkey(' + PCOLS + ')').eq('group_id', g.id)
      .order('role', { ascending: true }).order('joined_at', { ascending: false }).limit(50);
    if (r.error) throw r.error;
    return (r.data || []).map(function (m) { putUser(m.p); return { uid: aid(m.user_id), role: m.role === 'admin' ? 'admin' : 'member', joined: m.user_id === g.created_by ? 'Created the group' : joinedAgo(m.joined_at), name: m.p ? txt(m.p.name) : '' }; });
  }
  async function gmOp(g, op, uid) {
    var u = uuidOf(uid); if (!u) throw new Error('This member is no longer available');
    if (op === 'subadmin') throw new Error('Sub-admins are not available yet — make them an admin or keep them a member');
    if (op === 'remove') { await gpWrite(sb.from('group_members').delete().eq('group_id', g.id).eq('user_id', u).select('user_id'), 'Only the group’s admins can remove members');
      g.member_count = Math.max(0, (g.member_count || 1) - 1); }
    else if (op === 'admin' || op === 'member') await gpWrite(sb.from('group_members').update({ role: op }).eq('group_id', g.id).eq('user_id', u).select('user_id'), 'Only the group’s admins can change roles');
    else throw new Error('This is not available yet');
    if (GX.cur && GX.cur.id === g.id) manageLoad(g);
  }
  /* joining, leaving, asking to join, withdrawing the request, accepting an invitation — the card, the header and the inside agree */
  async function gpJoin(g, op) {
    var res;
    if (op === 'leave') { await gpWrite(sb.from('group_members').delete().eq('group_id', g.id).eq('user_id', ME_UUID).select('user_id'), 'You are not a member of this group');
      delete GX.mine[g.id]; delete GX.snap[g.name]; g.member_count = Math.max(0, (g.member_count || 1) - 1); res = 'left'; }
    else if (op === 'cancel') { var c = await sb.rpc('group_cancel_request', { p_group: g.id }); if (c.error) throw c.error; delete GX.req[g.id]; res = 'cancelled'; }
    else { var r = await sb.rpc('group_request_join', { p_group: g.id }); if (r.error) throw r.error; res = r.data;
      if (res === 'member') { if (!GX.mine[g.id]) g.member_count = (g.member_count || 0) + 1; GX.mine[g.id] = GX.mine[g.id] || 'member'; GX.snap[g.name] = true; delete GX.req[g.id]; delete GX.inv[g.id]; }
      else if (res === 'pending') GX.req[g.id] = true; }
    var paint = function () { var card = document.querySelector('#gx .gcard[data-gid="' + g.id + '"]'); if (card) paintCardState(card, g); if (GX.cur && GX.cur.id === g.id) paintHead(g); };
    paint(); setTimeout(paint, 0);   /* after groups.js painted the card for the step it asked for (an invitation may make a request a membership) */
    if (res === 'member' || res === 'left') setTimeout(refreshMine, 0);   /* side list, "My Groups (N)", shortcuts */
    window.toast(res === 'member' ? 'You joined ' + g.name : res === 'pending' ? 'Request sent to the admins of ' + g.name : res === 'left' ? 'You left ' + g.name : 'Request cancelled');
    return res;
  }
  /* the header of the open group: who I am in it decides the buttons (approved openGroup shows member or admin actions by role) */
  function paintHead(g) {
    var D = document.getElementById('groupDetail'); if (!D) return;
    var q = function (s) { return D.querySelector(s); }, role = GX.mine[g.id], ac = GX.act[g.id], see = !!role || g.type === 'public';
    if (q('.group-cover-emoji')) q('.group-cover-emoji').textContent = g.emoji || '👥';
    if (q('#dt-title')) q('#dt-title').textContent = g.name;
    if (q('#dt-type')) q('#dt-type').textContent = /deal/i.test(g.topic || '') ? '🤝 Deal Room' : '💬 Discussion';
    if (q('.group-meta-stats')) q('.group-meta-stats').innerHTML = '<div><b>' + (g.member_count || 0).toLocaleString('en') + '</b> members</div>' +
      (see ? '<div><b>' + ((ac && ac.posts_today) || 0).toLocaleString('en') + '</b> new posts today</div>' : '') + '<div>' + (g.type === 'private' ? '🔒 Private' : '🌍 Public') + '</div>';
    if (q('#leaveConfirm .cp-desc')) q('#leaveConfirm .cp-desc').textContent = 'You’ll stop seeing posts from ' + g.name + ' and lose access to its members and listings.';
    var ma = q('#memberActions'), aa = q('#adminActions');
    if (ma) ma.style.display = role === 'admin' ? 'none' : 'flex'; if (aa) aa.style.display = role === 'admin' ? 'flex' : 'none';
    var lb = q('#memberActions .btn-leave') || q('#memberActions [data-dxj]');
    if (lb) {
      var st = cardState(g), lbl = { joined: '🚪 Leave Group', join: '+ Join Group', request: '🔒 Request to join', pending: '⏳ Request sent', accept: '✉️ Accept invitation' }[st];
      lb.textContent = lbl; lb.classList.toggle('btn-leave', st === 'joined'); lb.classList.toggle('btn-manage', st !== 'joined');
      if (st === 'joined') { delete lb.dataset.dxj; lb.onclick = function () { window.toggleLeaveConfirm(); }; } else { lb.dataset.dxj = st; lb.onclick = null; }
    }
    [].forEach.call(D.querySelectorAll('#memberActions .btn-secondary'), function (b) { b.style.display = role ? '' : 'none'; });
    var lc = q('#leaveConfirm'); if (lc && !role) lc.classList.remove('show');
    /* the admin panel never shows the sample members, reports or member count while this group's own load is on its way */
    var n = (g.member_count || 0).toLocaleString('en'), dz = q('.danger-zone .dz-desc'); if (dz) dz.textContent = n + ' real members and their history live in this group. Choose carefully.';
    var sv = q('.danger-zone .choice-card.severe .choice-desc'); if (sv) sv.textContent = 'Removes all ' + n + ' members & history forever. No recovery.';
    if (role === 'admin' && MG.gid !== g.id) {
      var wait = '<div class="dx-gx-empty" style="padding:14px 4px;color:#65676b;font-size:13px">Loading…</div>';
      var ml = q('#tab-members .member-list'); if (ml) ml.innerHTML = wait; var mt = q('#tab-members .member-list-title span'); if (mt) mt.textContent = 'Members (' + n + ')';
      var rq = q('#tab-reports .mod-queue'); if (rq) rq.innerHTML = wait; [].forEach.call(D.querySelectorAll('#managePanel .panel-tabs .ptab-badge'), function (b) { b.style.display = 'none'; });
    }
  }
  /* the admin's Manage panel: members & roles with the join requests on top, reports from members, settings (name, description, rules) */
  var MG = { gid: null, busy: false };
  async function manageLoad(g) {
    if (GX.mine[g.id] !== 'admin') return; MG.gid = g.id;
    var a = await Promise.all([
      sb.from('group_join_requests').select('user_id, message, created_at, p:profiles!group_join_requests_user_id_fkey(' + PCOLS + ')').eq('group_id', g.id).eq('status', 'pending').order('created_at').limit(50),
      sb.from('group_post_reports').select('post_id, reason, created_at, post:posts(id, body, user_id, author:profiles!posts_user_id_fkey(' + PCOLS + '))').eq('group_id', g.id).eq('status', 'open').order('created_at', { ascending: false }).limit(100),
      gmList(g)]).catch(function (e) { toastErr(e); return null; });
    if (!a || MG.gid !== g.id || !GX.cur || GX.cur.id !== g.id) return;
    paintManage(g, a[0].data || [], a[1].data || [], a[2]);
  }
  function paintManage(g, reqs, reps, mem) {
    var D = document.getElementById('groupDetail'); if (!D) return;
    var tm = D.querySelector('#tab-members'), old = tm && tm.querySelector('.dx-gp-reqs'); if (old) old.remove();
    var list = tm && tm.querySelector('.member-list'), title = tm && tm.querySelector('.member-list-title');
    if (list) list.innerHTML = mem.map(function (m) {
      var u = (window.USERS || []).find(function (x) { return x.id === m.uid; }) || (m.uid === window.ME.id ? window.ME : null); if (!u) return '';
      var self = m.uid === window.ME.id, pill = m.role === 'admin' ? '<span class="role-pill rp-admin">👑 Admin</span>' : '<span class="role-pill rp-member">Member</span>';
      var acts = self ? '<div class="gp-you">You</div>' : '<button type="button" class="action-btn" aria-label="Member options" onclick="toggleDropdown(this)">⋯</button><div class="dropdown-menu">' +
        (m.role === 'admin' ? '<div class="dd-item" data-gpd="member" role="button" tabindex="0">👤 Demote to Member</div>' : '<div class="dd-item" data-gpd="admin" role="button" tabindex="0">👑 Promote to Admin</div>') +
        '<div class="dd-divider"></div><div class="dd-item" data-gpd="msg" role="button" tabindex="0">💬 Message</div><div class="dd-item danger" data-gpd="remove" role="button" tabindex="0">🚫 Remove from group</div></div>';
      return '<div class="member-row" data-uid="' + m.uid + '" style="position:relative"><div class="av" style="background:' + esc2(u.color || '#1a56db') + ';width:38px;height:38px;font-size:13px">' + esc2(u.initials || '?') + '</div>' +
        '<div><div class="member-name"><span data-noi18n>' + esc2(u.name) + '</span> ' + pill + '</div><div class="member-meta">' + esc2(m.joined || '') + '</div></div><div class="member-actions">' + acts + '</div></div>';
    }).join('');
    if (title) { var sp = title.querySelector('span'); if (sp) sp.textContent = 'Members (' + (g.member_count || 0).toLocaleString('en') + ')'; }
    /* join requests (private groups): above the member list, in the approved moderation-queue item */
    if (tm && (reqs.length || g.type === 'private')) {
      var h = '<div class="dx-gp-reqs"><div class="member-list-title"><span>Join requests (' + reqs.length + ')</span></div><div class="mod-queue">' + (reqs.length ? reqs.map(function (r) {
        putUser(r.p); var who = r.p ? txt(r.p.name) : 'Member', hl = r.p ? String(txt(r.p.headline) || '').split('|')[0].trim() : '';
        return '<div class="mod-item" data-req="' + aid(r.user_id) + '"><div class="mod-icon">👤</div><div class="mod-content"><div class="mod-title"><b data-noi18n>' + esc2(who) + '</b> <span>asked to join</span></div>' +
          '<div class="mod-meta">' + (hl ? '<span data-noi18n>' + esc2(hl) + '</span> · ' : '') + '<span>' + esc2(ago(r.created_at)) + '</span></div>' + (r.message ? '<div class="mod-reason" data-noi18n>“' + esc2(txt(r.message)) + '”</div>' : '') +
          '<div class="mod-actions"><button type="button" class="mod-btn dismiss" data-dxreq="reject">Decline</button><button type="button" class="mod-btn" style="background:#16a34a;color:#fff" data-dxreq="approve">Approve</button></div></div></div>';
      }).join('') : '<div class="gp-ok">✓ No pending requests</div>') + '</div></div>';
      var anchor = title || list; if (anchor) anchor.insertAdjacentHTML('beforebegin', h); else tm.insertAdjacentHTML('afterbegin', h);
    }
    var tabs = D.querySelectorAll('#managePanel .panel-tabs .gx-ptab');
    if (tabs[0]) { var rb = tabs[0].querySelector('.dx-req-badge'); if (!rb) { tabs[0].insertAdjacentHTML('beforeend', ' <span class="ptab-badge dx-req-badge"></span>'); rb = tabs[0].querySelector('.dx-req-badge'); } rb.textContent = reqs.length; rb.style.display = reqs.length ? '' : 'none'; }
    /* reports, one item per post */
    var by = {}, order = [];
    reps.forEach(function (r) { if (!r.post) return; var x = by[r.post_id]; if (!x) { x = by[r.post_id] = { post: r.post, n: 0, why: [], at: r.created_at }; order.push(x); } x.n++; if (x.why.length < 3 && x.why.indexOf(r.reason) < 0) x.why.push(r.reason); });
    var q = D.querySelector('#tab-reports .mod-queue');
    if (q) q.innerHTML = order.length ? order.map(function (x) {
      var au = x.post.author; putUser(au); var body = String(x.post.body || '');
      return '<div class="mod-item report" data-rpost="' + x.post.id + '"><div class="mod-icon">🚩</div><div class="mod-content"><div class="mod-title"><span>Post by</span> <b data-noi18n>' + esc2(au ? txt(au.name) : 'Member') + '</b> <span>' + (x.n > 1 ? 'reported by ' + x.n + ' members' : 'reported by 1 member') + '</span></div>' +
        '<div class="mod-meta"><span data-noi18n>“' + esc2(txt(body.slice(0, 90)) + (body.length > 90 ? '…' : '')) + '”</span> · <span>' + esc2(ago(x.at)) + '</span></div>' +
        '<div class="mod-reason" data-noi18n>⚠️ ' + esc2(txt(x.why.join(' · '))) + '</div>' +
        '<div class="mod-actions"><button type="button" class="mod-btn dismiss" data-dxrep="dismiss">Dismiss report</button><button type="button" class="mod-btn remove" data-dxrep="remove">Remove post</button></div></div></div>';
    }).join('') : '<div class="gp-ok">✓ No pending reports</div>';
    var badge = D.querySelector('#managePanel .panel-tabs .gx-ptab:nth-child(2) .ptab-badge'); if (badge) { badge.textContent = order.length; badge.style.display = order.length ? '' : 'none'; }
    /* settings: the group's own name, description and rules (one rule per line) */
    var ts = D.querySelector('#tab-settings');
    if (ts) {
      var nm = ts.querySelector('.field-input'), ds = ts.querySelector('.field-textarea:not(.dx-rules)'), ru = ts.querySelector('.dx-rules');
      if (!ru && ds) { var f = ds.closest('.field'); if (f) { f.insertAdjacentHTML('afterend', '<div class="field"><label class="field-label">Group rules</label><textarea class="field-textarea dx-rules" maxlength="4000" placeholder="One rule per line — e.g. Documents first: every offer shows its GMP certificate"></textarea></div>'); ru = ts.querySelector('.dx-rules'); } }
      if (!ts.dataset.dxFilled || ts.dataset.dxFilled !== String(g.id)) { if (nm) nm.value = g.name; if (ds) ds.value = g.description || ''; if (ru) ru.value = g.rules || ''; ts.dataset.dxFilled = g.id; }
    }
  }
  document.addEventListener('click', function (e) {
    if (!ME_UUID || !e.target.closest) return;
    var g = GX.cur, t = e.target;
    /* the header's Join / Request / Accept / Request sent (not a member): the same step as the button inside the group */
    var hb = t.closest('#groupDetail #memberActions [data-dxj]');
    if (hb && g) { e.preventDefault(); e.stopPropagation(); var st = hb.dataset.dxj, op = st === 'pending' ? 'cancel' : st === 'request' ? 'request' : 'join';
      var inner = document.querySelector('#gpBox [data-gpa="' + (st === 'pending' ? 'cancel' : st === 'accept' ? 'accept' : st) + '"]');
      if (inner) inner.click(); else gpJoin(g, op).then(function () { if (window.dxGroups && window.dxGroups.refresh) window.dxGroups.refresh(); }, toastErr); return; }
    var rq = t.closest('#groupDetail [data-dxreq]');
    if (rq && g) { e.preventDefault(); e.stopPropagation(); if (rq.disabled) return;
      var item = rq.closest('[data-req]'), u = uuidOf(+item.dataset.req), yes = rq.dataset.dxreq === 'approve', who = (item.querySelector('.mod-title b') || {}).textContent || '';
      item.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
      sb.rpc('group_decide_request', { p_group: g.id, p_user: u, p_approve: yes }).then(function (r) {
        if (r.error) { item.querySelectorAll('button').forEach(function (b) { b.disabled = false; }); return toastErr(r.error); }
        if (yes) { g.member_count = (g.member_count || 0) + 1; var card = document.querySelector('#gx .gcard[data-gid="' + g.id + '"]'); if (card) paintCardState(card, g); paintHead(g); }
        window.toast(yes ? who + ' is now a member' : 'Request declined'); manageLoad(g); if (yes && window.dxGroups && window.dxGroups.refresh) window.dxGroups.refresh();
      }, toastErr); return; }
    var rp = t.closest('#groupDetail #tab-reports [data-dxrep]');
    if (rp && g) { e.preventDefault(); e.stopPropagation(); if (rp.disabled) return;
      var it = rp.closest('[data-rpost]'), pid = +it.dataset.rpost, rm = rp.dataset.dxrep === 'remove';
      it.querySelectorAll('button').forEach(function (b) { b.disabled = true; });
      (rm ? sb.from('posts').delete().eq('id', pid).select('id') : sb.from('group_post_reports').update({ status: 'dismissed' }).eq('group_id', g.id).eq('post_id', pid).eq('status', 'open').select('post_id')).then(function (r) {
        if (r.error || !(r.data || []).length) { it.querySelectorAll('button').forEach(function (b) { b.disabled = false; }); return toastErr(r.error || { message: 'This report was already answered' }); }
        if (rm && g.pinned_post_id === pid) g.pinned_post_id = null;
        window.toast(rm ? 'Post removed from the group' : 'Report dismissed'); manageLoad(g); if (rm && window.dxGroups && window.dxGroups.refresh) window.dxGroups.refresh();
      }, toastErr); return; }
    var sv = t.closest('#groupDetail #tab-settings .btn-create');
    if (sv && g && GX.mine[g.id] === 'admin') { e.preventDefault(); e.stopPropagation(); if (sv.dataset.busy) return;
      var ts = document.getElementById('tab-settings'), nm = ts.querySelector('.field-input'), ds = ts.querySelector('.field-textarea:not(.dx-rules)'), ru = ts.querySelector('.dx-rules');
      var name = nm ? nm.value.trim() : ''; if (!name) { if (nm) nm.classList.add('dbk-err'); window.toast('Group name is required'); return; } if (nm) nm.classList.remove('dbk-err');
      sv.dataset.busy = '1';
      sb.from('groups').update({ name: name, description: ds ? ds.value.trim() : g.description, rules: ru ? (ru.value.trim() || null) : g.rules }).eq('id', g.id).select().then(function (r) { delete sv.dataset.busy;
        if (r.error || !(r.data || []).length) return toastErr(r.error || { message: 'Only the group’s admins can change its settings' });
        var oldName = g.name, row = r.data[0]; g.name = row.name; g.description = row.description; g.rules = row.rules; if (GX.snap[oldName]) { delete GX.snap[oldName]; GX.snap[g.name] = true; }
        var card = document.querySelector('#gx .gcard[data-gid="' + g.id + '"]');
        if (card) { var nc = groupCard(g); card.replaceWith(nc); if (window.dxGroups && window.dxGroups.pick) window.dxGroups.pick(nc, 'about'); }
        paintHead(g); window.toast('Group settings saved'); if (window.dxGroups && window.dxGroups.refresh) window.dxGroups.refresh('about');
      }, function (e2) { delete sv.dataset.busy; toastErr(e2); }); return; }
    if (t.closest('#groupDetail .choice-btn.archive') && g) { e.preventDefault(); e.stopPropagation(); window.toast('Archiving groups is not available yet — you can delete the group instead'); return; }
    if (t.closest('#groupDetail .btn-manage[onclick*="toggleManage"]') && g) setTimeout(function () { var mp = document.getElementById('managePanel'); if (mp && mp.style.display !== 'none') manageLoad(g); }, 0);
  }, true);
  /* groups.js asks for the inside of a group here */
  var hookD3b = window.dxLiveHook;
  window.dxLiveHook = function (kind, d) {
    if (ME_UUID) {
      if (kind === 'groupPosts') { try { return gpPage(gOf(d)); } catch (e) { return Promise.reject(e); } }
      if (kind === 'groupPost') { if (d === null) return true; return gpOp(d); }
      if (kind === 'groupMembers') { try { var g = gOf(d); return d.op ? gmOp(g, d.op, d.uid) : gmList(g); } catch (e) { return Promise.reject(e); } }
      if (kind === 'groupJoin') { try { var g2 = gOf(d); return gpJoin(g2, d.op === 'accept' ? 'join' : d.op); } catch (e) { return Promise.reject(e); } }
      if (kind === 'groupListings' || kind === 'groupListing') return undefined;     /* deal-room listings inside a group: not in the database yet */
    }
    return hookD3b ? hookD3b(kind, d) : undefined;
  };
  /* a group opened from elsewhere (search, a link, the side list) opens the same way as a click on its card */
  if (window.dxGroups && window.dxGroups.open) {
    var dgOpen = window.dxGroups.open;
    window.dxGroups.open = function (name, tab) {
      if (!ME_UUID) return dgOpen.apply(this, arguments);
      if (document.body.getAttribute('data-page') !== 'groups' && typeof window.goto === 'function') window.goto('groups');
      var c = name && name.nodeType === 1 ? name : [].slice.call(document.querySelectorAll('#gx .gcard[data-gid]')).find(function (x) { var t = x.querySelector('.gcard-title'); return t && t.textContent === name; });
      if (c && c.dataset.gid) { window.dxLive.openGroup(+c.dataset.gid, tab); return true; }
      return dgOpen.apply(this, arguments);
    };
  }
  ICON.group_join_request = '👥'; ICON.group_join_approved = '✅'; ICON.group_invite = '✉️';
  onReset(function () { GX.inv = {}; GX.req = {}; GX.act = {}; MG.gid = null; });

  /* following companies: the directory's store('follows') (a list of slugs) ↔ company_followers */
  var FOL = { list: [], loaded: false };
  async function loadFollows() { var r = await sb.from('company_followers').select('company_id, co:companies(slug)').eq('user_id', ME_UUID); if (r.error) throw r.error;
    FOL.list = (r.data || []).map(function (x) { return CO.byId[x.company_id] || sslug(x.co && x.co.slug); }).filter(Boolean); FOL.loaded = true; }
  async function syncFollows(v) {
    var now = (v || []).slice(), before = FOL.list.slice(); FOL.list = now;
    for (var i = 0; i < now.length; i++) if (before.indexOf(now[i]) < 0) { var raw = CO.raw[now[i]]; if (raw && raw.id) { var r = await sb.from('company_followers').insert({ company_id: raw.id, user_id: ME_UUID }); if (r.error) { toastErr(r.error); return loadFollows(); } } }
    for (var j = 0; j < before.length; j++) if (now.indexOf(before[j]) < 0) { var raw2 = CO.raw[before[j]]; if (raw2 && raw2.id) await sb.from('company_followers').delete().eq('company_id', raw2.id).eq('user_id', ME_UUID); }
  }
  var hookFol = window.dxStoreHook;
  window.dxStoreHook = function (k, v) {
    if (ME_UUID && k === 'follows') { if (v === undefined) return FOL.list.slice(); syncFollows(v).catch(toastErr); return true; }
    return hookFol ? hookFol(k, v) : undefined;
  };
  var hydrateFol = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateFol(uid); loadFollows().catch(function (e) { console.error(e); }); return me; };
  onReset(function () { FOL.list = []; FOL.loaded = false; GX.groups = []; GX.mine = {}; GX.at = 0; GX.cur = null; GX.snap = {}; });

  /* ═══════════════ E1b — private documents: CV with applications, verification documents, evidence for warnings ═══════════════ */
  var DOCS = { vf: {}, ev: null };
  function extOf(f) { return ((f && f.name) || '').split('.').pop().toLowerCase().replace(/[^a-z0-9]/g, '') || 'pdf'; }
  async function upDoc(bucket, path, file) { var r = await sb.storage.from(bucket).upload(path, file, { contentType: file.type || 'application/pdf' }); if (r.error) throw new Error(friendly(r.error)); return path; }
  /* the verification dialog's file fields: keep the files so they can be sent with the request */
  document.addEventListener('change', function (e) { var t = e.target; if (t && /^(vfR|vfT|vfL)$/.test(t.id) && t.files && t.files[0]) DOCS.vf[t.id] = t.files[0]; }, true);
  window.dxLive.verificationFiles = async function (companyId) {
    var out = {}, map = { vfR: 'registry_path', vfT: 'tax_card_path', vfL: 'licence_path' };
    for (var k in DOCS.vf) out[map[k]] = await upDoc('documents', 'verification/' + companyId + '/' + map[k].replace('_path', '') + '-' + rid() + '.' + extOf(DOCS.vf[k]), DOCS.vf[k]);
    DOCS.vf = {}; return out;
  };
  /* the jobs page's apply window gets an optional CV field (live app only) */
  function cvField() { var m = document.getElementById('applyModal'); if (!m || m.querySelector('#dxCv')) return; var ta = m.querySelector('textarea'), host = ta ? ta.parentElement : m.querySelector('.modal-body, .modal');
    if (host) host.insertAdjacentHTML('beforeend', '<label class="dx-cv" style="display:block;margin-top:10px;font:600 12.5px Poppins,sans-serif;color:#334155">CV (PDF or Word, optional)<input type="file" id="dxCv" accept=".pdf,.doc,.docx" style="display:block;margin-top:6px"></label>'); }
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#jx .apply-btn')) setTimeout(cvField, 0); }, true);
  /* a warning's evidence is the approved form's own "Evidence *" field (shown on the Warning tab only, required there by the form);
     the reference waits until it is attached (F-176: no second field, none on the Honour tab) */
  document.addEventListener('change', function (e) { var t = e.target; if (t && t.id === 'rfEv' && t.closest('.dbk-ov')) DOCS.ev = (t.files && t.files[0]) || null; }, true);

  /* the verification dialog only updates companies created in the browser; for real companies the request is sent here */
  var oVerify = window.dxDir && window.dxDir.verify;
  if (oVerify) window.dxDir.verify = function (slug) { DOCS.vslug = slug; DOCS.vf = {}; return oVerify.apply(this, arguments); };
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.dbk-ov [data-a=ok]'); if (!btn || !ME_UUID) return;   /* the window's send button, whatever language its label is in (F-21) */
    var ov = btn.closest('.dbk-ov'), rnEl = ov && ov.querySelector('#vfRN'); if (!rnEl) return;
    var rn = (rnEl.value || '').replace(/\D/g, ''), raw = CO.raw[DOCS.vslug];
    if (rn.length < 4 || !DOCS.vf.vfR || !DOCS.vf.vfT || !raw || !raw.id) return;              /* the dialog's own checks show the message */
    var l = live(DOCS.vslug); if (l) { l.status = 'pending'; l.registry = rn; }
    window.dxLive.verificationFiles(raw.id).then(function (docs) {
      return sb.from('verification_requests').insert(Object.assign({ company_id: raw.id, submitted_by: ME_UUID, registry: rn }, docs));
    }).then(function (r) { if (r && r.error) { toastErr(r.error); return; } SNAP['vr_' + DOCS.vslug] = 1; rerenderCompanies(); }, toastErr);
  }, true);

  /* ═══════════════ E2 — Admin → Review on the database; company reports ═══════════════ */
  window.dxModeration = {
    load: async function () {
      var today = new Date().toISOString().slice(0, 10);
      var q = await Promise.all([
        sb.from('verification_requests').select('*, co:companies(name,slug)').eq('status', 'pending').order('created_at').limit(100),
        sb.from('work_references').select('*, au:profiles!work_references_author_fkey(name,company), ca:profiles!work_references_candidate_fkey(name)').eq('kind', 'warn').eq('status', 'pending').order('created_at').limit(100),
        sb.from('site_certificates').select('*, st:company_sites!site_certificates_site_id_fkey(name), co:companies(name)').is('checked_at', null).or('expiry.is.null,expiry.gte.' + today).order('created_at').limit(100),
        sb.from('company_reports').select('*, co:companies(name)').eq('status', 'open').order('created_at').limit(100)]);
      for (var i = 0; i < q.length; i++) if (q[i].error) throw q[i].error;
      var d = function (path, bucket, label) { return path ? [{ path: path, bucket: bucket, label: label }] : []; };
      return {
        verifications: q[0].data.map(function (v) { return { id: v.id, company: v.co && v.co.name, registry: v.registry, at: String(v.created_at).slice(0, 10),
          docs: d(v.registry_path, 'documents', 'Commercial registry').concat(d(v.tax_card_path, 'documents', 'Tax card'), d(v.licence_path, 'documents', 'Licence')) }; }),
        warnings: q[1].data.map(function (w) { return { id: w.id, company: (w.au && (w.au.company || w.au.name)) || '', candidate: w.ca && w.ca.name, category: w.category, text: w.body, docs: d(w.evidence_path, 'reference-evidence', 'Evidence') }; }),
        certs: q[2].data.map(function (c) { return { id: c.id, company: c.co && c.co.name, site: c.st && c.st.name, name: c.name, expiry: c.expiry ? String(c.expiry).slice(0, 7) : '' }; }),
        reports: q[3].data.map(function (r) { return { id: r.id, company: r.co && r.co.name, section: r.section, issue: r.issue, correction: r.correction }; })
      };
    },
    decide: async function (kind, id, value, note) {
      var r = kind === 'verifications' ? await sb.from('verification_requests').update({ status: value, note: note || null }).eq('id', id).select()
        : kind === 'warnings' ? await sb.rpc('moderate_reference', { ref_id: +id, new_status: value })
        : kind === 'certs' ? await sb.from('site_certificates').update({ checked_at: new Date().toISOString() }).eq('id', id).select()
        : await sb.from('company_reports').update({ status: value }).eq('id', id).select();
      if (r.error) throw new Error(friendly(r.error));
      if (r.data && Array.isArray(r.data) && !r.data.length) throw new Error('Only the Drugbox team can do this');
      if (kind !== 'reports') refreshCompanies().catch(function () {});
      return true;
    },
    link: async function (path, bucket) { var r = await sb.storage.from(bucket).createSignedUrl(path, 600); return r.error ? null : r.data.signedUrl; }
  };
  /* company reports ("Report wrong information") ↔ company_reports. The reporter reads their own reports (Drugbox reads all);
     the reported company's owners and admins read company_reports_received(), without the reporter (0024, F-32). Only Drugbox
     closes a report: "Mark fixed" leaves it open in Admin → Review and says so. */
  var REP = { list: [] };
  function repFrom(x, slug, by) { return { id: 'R' + x.id, _id: x.id, slug: slug, section: x.section, text: x.issue, fix: x.correction || '', by: by, at: new Date(x.created_at).getTime(), status: x.status }; }
  async function loadReports() {
    var me = ME_UUID, q = await Promise.all([sb.from('company_reports').select('*, co:companies(slug), rp:profiles!company_reports_reporter_fkey(name)').order('created_at', { ascending: false }).limit(200),
                                             sb.rpc('company_reports_received')]);
    if (q[0].error) throw q[0].error; if (me !== ME_UUID) return;
    var list = (q[0].data || []).map(function (x) { return repFrom(x, sslug(x.co && x.co.slug), (x.rp && x.rp.name) || 'Member'); });
    if (!q[1].error && (q[1].data || []).length) {
      try { await CO.mineP; } catch (e) {} if (me !== ME_UUID) return;             /* my pages' slugs */
      q[1].data.forEach(function (x) { if (list.some(function (y) { return y._id === x.id; })) return; var slug = CO.byId[x.company_id]; if (slug) list.push(repFrom(x, slug, 'a Drugbox member')); });
      list.sort(function (a, b) { return b.at - a.at; });
    }
    REP.list = list;
  }
  function copies(l) { return (l || []).map(function (r) { return Object.assign({}, r); }); }
  async function syncReports(v, before) {                                        /* before: the list as it was (copies) */
    for (var i = 0; i < (v || []).length; i++) { var x = v[i], raw = CO.raw[x.slug];
      if (!x._id && raw && raw.id) { var r = await sb.from('company_reports').insert({ company_id: raw.id, reporter: ME_UUID, section: x.section, issue: x.text, correction: x.fix || null }).select().single();
        if (r.error) { toastErr(r.error); break; } x._id = r.data.id; REP.list.forEach(function (y) { if (y.id === x.id) y._id = x._id; }); }
      else if (x._id) { var was = (before || []).find(function (y) { return y._id === x._id; }); if (was && was.status !== x.status) {
        var u = await sb.from('company_reports').update({ status: x.status }).eq('id', x._id).select();
        if (u.error || !(u.data || []).length) {                                   /* not closed: Drugbox checks the page first */
          REP.list.forEach(function (y) { if (y._id === x._id) y.status = was.status; });
          setTimeout(function () { window.toast('Thanks — Drugbox checks the page and closes the report'); }, 700); rerenderCompanies(); } } } }
  }
  var hookRep = window.dxStoreHook;
  window.dxStoreHook = function (k, v) {
    if (ME_UUID && k === 'reports') { if (v === undefined) return copies(REP.list); var before = REP.list; REP.list = copies(v); syncReports(v, before).catch(toastErr); return true; }
    return hookRep ? hookRep(k, v) : undefined;
  };
  onReset(function () { REP.list = []; });
  var hydrateRep = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateRep(uid); loadReports().catch(function (e) { console.error(e); }); return me; };

  /* ═══════════════ E4b — checkout in the app (Paymob / Fawry / InstaPay through the payments-create function) ═══════════════ */
  window.dxPay = {
    live: true,
    start: async function (o) {
      var s = await sb.auth.getSession(), tok = s.data && s.data.session && s.data.session.access_token; if (!tok) throw new Error('Sign in first');
      var raw = o.slug && CO.raw[o.slug];
      var r = await fetch(CFG.url + '/functions/v1/payments-create', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok, apikey: CFG.anonKey },
        body: JSON.stringify({ product: o.product, method: o.method, company_id: raw && raw.id, listing_id: o.listing_id }) });
      var j = {}; try { j = await r.json(); } catch (e) {}
      if (!r.ok) throw new Error(j.error || 'The payment could not start'); return j;
    },
    submitInstapay: async function (orderId, ref, file) {
      var path = null; if (file) { path = 'payments/' + ME_UUID + '/' + rid() + '.' + extOf(file); await upDoc('documents', path, file); }
      var r = await sb.rpc('submit_instapay', { p_id: orderId, p_transfer_ref: ref, p_receipt: path }); if (r.error) throw new Error(friendly(r.error));
    },
    listings: async function () { var r = await sb.from('products').select('id,name').eq('user_id', ME_UUID).eq('active', true).order('created_at', { ascending: false }).limit(50); return r.data || []; },
    /* the Boost / Featured window shows the price the server charges (payment_products, same rounding as create_order) —
       never USD × a third-party exchange rate (F-07). Code: 'boost' | 'featured' (any payment_products code). */
    quote: async function (code) {
      var r = await sb.from('payment_products').select('code,amount_egp,vat_rate,duration_days').eq('code', code).eq('active', true).maybeSingle();
      if (r.error) throw new Error(friendly(r.error)); if (!r.data) throw new Error('This product is not on sale at the moment');
      var amount = Number(r.data.amount_egp), total = Math.round(amount * (1 + Number(r.data.vat_rate)) * 100) / 100;
      return { amount_egp: amount, vat_egp: Math.round((total - amount) * 100) / 100, total_egp: total, days: r.data.duration_days };
    }
  };
  /* back from Paymob's page: ?payment=<order id> → tell the person what happened */
  (function () { var m = /[?&]payment=(\d+)/.exec(location.search); if (!m) return; var id = +m[1], tries = 0, waited = 0;
    function check() { if (!ME_UUID) { if ((waited += 800) < 60000) setTimeout(check, 800); return; }   /* not signed in within a minute: stop (F-119) */
      sb.from('payment_orders').select('status').eq('id', id).single().then(function (r) { var st = r.data && r.data.status;
        if (st === 'paid') { window.toast('Payment received — it is active now'); refreshCompanies().catch(function () {}); MKT.at = 0; history.replaceState(null, '', location.pathname); }
        else if (++tries < 10) setTimeout(check, 2000); else window.toast('We have not received the payment confirmation yet — it will activate automatically when it arrives'); }); }
    check(); })();
  /* Review → Payments (InstaPay transfers) */
  var modLoad = window.dxModeration.load, modDecide = window.dxModeration.decide;
  window.dxModeration.load = async function () {
    var d = await modLoad(), r = await sb.from('payment_orders').select('*, pr:payment_products(label), u:profiles(name)').eq('status', 'review').order('created_at').limit(100);
    if (r.error) throw r.error;
    var pr = await sb.from('post_reports').select('*, rp:profiles!post_reports_reporter_fkey(name), au:profiles!post_reports_post_author_fkey(name)').eq('status', 'open').order('created_at').limit(200);
    if (pr.error) throw pr.error; var byPost = {};
    d.posts = [];
    (pr.data || []).forEach(function (x) { var k = x.post_id != null ? 'p' + x.post_id : 'r' + x.id, row = byPost[k];
      if (row) { row.n++; return; }
      row = byPost[k] = { id: x.id, pid: x.post_id, author: (x.au && x.au.name) || 'Member', reporter: (x.rp && x.rp.name) || 'Member', reason: x.reason, note: x.note, excerpt: x.post_excerpt || '', n: 1, at: ago(x.created_at) };
      d.posts.push(row); });
    d.payments = r.data.map(function (o) { return { id: o.id, who: o.u && o.u.name, product: o.pr && o.pr.label, transfer: o.transfer_ref, amount: (o.amount_cents / 100).toLocaleString('en'), reference: o.merchant_ref,
      docs: o.receipt_path ? [{ path: o.receipt_path, bucket: 'documents', label: 'Receipt' }] : [] }; });
    return d;
  };
  /* Review → Message reports (0031): the reported person's messages as the database copied them into the report */
  var modLoadP = window.dxModeration.load;
  window.dxModeration.load = async function () {
    var d = await modLoadP(), r = await sb.from('message_reports').select('*, rp:profiles!message_reports_reporter_fkey(name), rd:profiles!message_reports_reported_fkey(name)').eq('status', 'open').order('created_at').limit(100);
    if (r.error) throw r.error;
    d.messages = r.data.map(function (x) { return { id: x.id, reporter: (x.rp && x.rp.name) || 'Member', who: (x.rd && x.rd.name) || 'Member', reason: x.reason, details: x.details || '', at: String(x.created_at).slice(0, 10),
      excerpt: (x.excerpt || []).map(function (m) { return (m.body || '') + (m.file ? ' 📎 ' + m.file : ''); }) }; });
    return d;
  };
  window.dxModeration.decide = async function (kind, id, value, note) {
    if (kind === 'messages') { var m = await sb.from('message_reports').update({ status: value }).eq('id', +id).select('id'); if (m.error) throw new Error(friendly(m.error));
      if (!(m.data || []).length) throw new Error('Only the Drugbox team can do this'); return true; }
    if (kind === 'posts') return window.dxPostSvc.decide(id, value, note);
    if (kind !== 'payments') return modDecide(kind, id, value, note);
    var r = await sb.rpc('review_instapay', { p_id: +id, p_ok: value === 'paid' }); if (r.error) throw new Error(friendly(r.error)); return true;
  };

  /* ═══════════════ E3 — training: courses and enrollments from the database (the approved course card is the template) ═══════════════ */
  var TRN = { tpl: null, courses: [], mine: {}, at: 0, loading: false };
  async function loadTraining() {
    var a = await Promise.all([sb.from('training_courses').select('*').eq('active', true).order('sort_order').order('created_at').limit(100),
                               sb.from('course_enrollments').select('course_id,status').eq('user_id', ME_UUID)]);
    if (a[0].error) throw a[0].error; TRN.courses = a[0].data || []; TRN.mine = {}; (a[1].data || []).forEach(function (x) { TRN.mine[x.course_id] = x.status; }); TRN.at = Date.now();
  }
  function courseCard(t) {
    var c = el(TRN.tpl), on = !!TRN.mine[t.id]; c.dataset.course = t.id;
    var h = c.querySelector('.tr-hero'); if (h) h.textContent = t.emoji || '🎓';
    var ti = c.querySelector('.tr-title'); if (ti) ti.textContent = t.title;
    var d = c.querySelector('.tr-desc'); if (d) d.textContent = t.description || '';
    var m = c.querySelector('.tr-meta'); if (m) { var sp = m.querySelectorAll('span'); if (sp[0]) sp[0].textContent = '⏱ ' + (t.duration || ''); if (sp[1]) sp[1].textContent = t.level; }
    var b = c.querySelector('button'); if (b) { b.removeAttribute('onclick'); b.textContent = on ? '✅ Enrolled' : 'Enroll Now'; b.style.background = on ? '#16a34a' : ''; }
    return c;
  }
  function paintTraining() {
    var grid = document.querySelector('#content .training-grid'); if (!grid) return;
    var any = grid.querySelector('.tr-card'); if (any && !TRN.tpl) TRN.tpl = any.outerHTML; if (!TRN.tpl || !TRN.at) return;
    grid.innerHTML = ''; TRN.courses.forEach(function (t) { grid.appendChild(courseCard(t)); });
    if (!TRN.courses.length) grid.innerHTML = '<div style="padding:18px;color:#65676b;font-size:13px">No courses yet.</div>';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.training-grid .tr-card[data-course] button'); if (!b || !ME_UUID) return;
    e.preventDefault(); e.stopPropagation(); var id = +b.closest('.tr-card').dataset.course, t = TRN.courses.find(function (x) { return x.id === id; });
    if (TRN.mine[id]) { window.toast('You are already enrolled in ' + t.title); return; }
    b.disabled = true;
    sb.from('course_enrollments').insert({ course_id: id, user_id: ME_UUID }).then(function (r) { b.disabled = false;
      if (r.error && !/duplicate|unique/i.test(r.error.message)) return toastErr(r.error);
      TRN.mine[id] = 'enrolled'; b.textContent = '✅ Enrolled'; b.style.background = '#16a34a'; window.toast('Enrolled in ' + t.title + '!'); });
  }, true);
  var origRenderTraining = window.renderTraining;
  window.renderTraining = function () {
    var r = origRenderTraining.apply(this, arguments); if (!ME_UUID) return r;
    paintTraining();
    if (Date.now() - TRN.at > 3000 && !TRN.loading) { TRN.loading = true; loadTraining().then(function () { TRN.loading = false; if (document.body.getAttribute('data-page') === 'training') paintTraining(); }, function (e) { TRN.loading = false; toastErr(e); }); }
    return r;
  };
  onReset(function () { TRN.courses = []; TRN.mine = {}; TRN.at = 0; });
  window.dxLive.loadTraining = loadTraining;
  window.dxLive.loadGroups = loadGroups; window.dxLive.version = 'E4';

  /* ═══════════════ P1 — no sample content in the live app (S-19, B-06, B-07 rows, G-03/G-04 outside the Groups page) ═══════════════
     Every number, card and name a signed-in person sees comes from the database, or the approved element is left empty / hidden
     (empty states use the page's own style). The approved markup is never restyled: only its words and numbers change. */
  var PG = { my: [], myAt: 0, stats: null, statsAt: 0, jobs: [], loading: false, members: null };
  function onPageNow(p) { return document.body.getAttribute('data-page') === p; }
  /* my groups for the side menu and the network page: the full list once the Groups page loaded it, a light query before */
  async function loadMyGroups() {
    var r = await sb.from('group_members').select('group_id, role, g:groups(id, name, emoji, topic, type, member_count)').eq('user_id', ME_UUID).limit(100);
    if (r.error) throw r.error; PG.my = (r.data || []).map(function (x) { return x.g; }).filter(Boolean); PG.myAt = Date.now(); syncGroupsGlobal();
  }
  function myGroupList() { return GX.at ? myGroups() : PG.my; }
  /* the approved code's own GROUPS list (network page "Groups", the page header counts) becomes the real groups */
  function syncGroupsGlobal() {
    var G = window.GROUPS; if (!Array.isArray(G)) return;
    var src = GX.at ? GX.groups : PG.my, mine = function (g) { return GX.at ? !!GX.mine[g.id] : true; };
    G.length = 0; src.forEach(function (g) { G.push({ id: g.id, emoji: g.emoji || '👥', name: g.name, desc: g.description || '', type: /deal/i.test(g.topic || '') ? 'DEAL ROOM' : 'DISCUSS', members: g.member_count || 0, joined: mine(g), color: GRAD[g.id % GRAD.length][0] }); });
    paintShortcuts(); paintNetGroups();
  }
  /* "Your shortcuts" in the side menu: my groups (up to 5), each opens its group; hidden while I am in none */
  function paintShortcuts() {
    var sb0 = document.getElementById('sidebar'); if (!sb0 || !ME_UUID) return;
    var rows = [].slice.call(sb0.querySelectorAll('.sh-row:not([data-gid])')); if (rows.length && !PG.tplSh) PG.tplSh = rows[0].outerHTML; rows.forEach(function (r) { r.remove(); });
    var sec = [].slice.call(sb0.querySelectorAll('.sb-sec')).find(function (x) { return /shortcuts/i.test(window.dxOrigText ? window.dxOrigText(x) : x.textContent); }); if (!sec || !PG.tplSh) return;
    sb0.querySelectorAll('.sh-row[data-gid]').forEach(function (r) { r.remove(); });
    var list = myGroupList().slice(0, 5), after = sec;
    list.forEach(function (g) { var r = el(PG.tplSh); r.dataset.gid = g.id; r.setAttribute('role', 'button'); r.setAttribute('tabindex', '0'); r.innerHTML = '<div class="sh-ic"></div>'; r.firstChild.textContent = g.emoji || '👥'; r.appendChild(document.createTextNode(g.name)); after.insertAdjacentElement('afterend', r); after = r; });
    sec.style.display = list.length ? '' : 'none'; var dv = after.nextElementSibling; if (dv && dv.classList.contains('sb-div')) dv.style.display = list.length ? '' : 'none';
  }
  /* the network page's "Groups" card: real rows (the approved renderNetwork draws them from GROUPS), each opens its group */
  function paintNetGroups() {
    if (!ME_UUID || !onPageNow('network')) return;
    var card = [].slice.call(document.querySelectorAll('#content .net-sidebar')).find(function (c) { var h = c.firstElementChild; return h && /^Groups$/.test((window.dxOrigText ? window.dxOrigText(h) : h.textContent).trim()); }); if (!card) return;
    var joined = (window.GROUPS || []).filter(function (g) { return g.joined; }), rows = [].slice.call(card.children).slice(1).filter(function (r) { return !r.classList.contains('dx-net-empty'); });
    if (rows.length !== joined.length) { rows.forEach(function (r) { r.remove(); }); card.querySelectorAll('.dx-net-empty').forEach(function (r) { r.remove(); });
      joined.forEach(function (g) { var r = document.createElement('div'); r.setAttribute('style', 'display:flex;align-items:center;gap:8px;padding:6px 0;cursor:pointer;font-size:13px;border-bottom:1px solid #f0f2f5'); r.innerHTML = '<span style="font-size:20px"></span>'; r.firstChild.textContent = g.emoji; r.appendChild(document.createTextNode(g.name)); card.appendChild(r); });
      rows = [].slice.call(card.children).slice(1); }
    rows.forEach(function (r, i) { if (joined[i]) { r.dataset.gid = joined[i].id; r.setAttribute('role', 'button'); r.setAttribute('tabindex', '0'); } });
    if (!joined.length && !card.querySelector('.dx-net-empty')) card.insertAdjacentHTML('beforeend', '<div class="dx-net-empty" role="button" tabindex="0" data-goto="groups" style="padding:6px 0;font-size:13px;color:#65676b;cursor:pointer">You have not joined a group yet — find one on the Groups page.</div>');
  }
  /* a group opened from outside the Groups page: open the page, then the group as soon as its card is there */
  function openGroupFromAnywhere(gid) {
    if (!onPageNow('groups')) window.goto('groups'); var tries = 0;
    (function wait() { if (document.querySelector('#gx .gcard[data-gid="' + gid + '"]') && GX.groups.some(function (g) { return g.id === gid; })) return window.dxLive.openGroup(gid);
      if (++tries < 40) setTimeout(wait, 150); else window.toast('This group is not available any more'); })();
  }
  document.addEventListener('click', function (e) {
    if (!ME_UUID || !e.target.closest) return;
    var r = e.target.closest('#sidebar .sh-row[data-gid], #content .net-sidebar [data-gid]');
    if (r) { e.preventDefault(); e.stopPropagation(); openGroupFromAnywhere(+r.dataset.gid); return; }
    var go = e.target.closest('#content .dx-net-empty[data-goto]'); if (go) { e.preventDefault(); window.goto(go.dataset.goto); }
  }, true);
  document.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && e.target.closest && e.target.closest('#sidebar .sh-row[data-gid], #content .net-sidebar [data-gid], #content .dx-net-empty')) { e.preventDefault(); e.target.click(); } });
  /* the side menu and phone bar badges show the same real counts as the top bar (which the parts above keep: requests, messages, alerts) */
  var NAVB = [['nb-net', 'network'], ['nb-msg', 'messages'], ['nb-not', 'notifs']];
  function navBadges() {
    if (!ME_UUID) return;
    NAVB.forEach(function (b) {
      var top = document.getElementById(b[0]), n = top && top.style.display !== 'none' ? parseInt(top.textContent, 10) || 0 : 0;
      (window.SB_NAV || []).forEach(function (x) { if (x.page === b[1]) x.badge = n; });
      var sl = document.getElementById('snl-' + b[1]), nb = sl && sl.querySelector('.nl-badge');
      if (sl && n && !nb) { sl.insertAdjacentHTML('beforeend', '<span class="nl-badge"></span>'); nb = sl.querySelector('.nl-badge'); }
      var mb = document.querySelector('#mb-' + b[1] + ' .mb-badge');
      [nb, mb].forEach(function (x) { if (!x) return; if (x.textContent !== String(n)) x.textContent = n; var d = n ? '' : 'none'; if (x.style.display !== d) x.style.display = d; });
    });
  }
  if (window.dxCore) window.dxCore.onRender('live-nav-badges', navBadges);
  /* Home: the sample events and hashtags are left out; the member count is the real one */
  var oSideP1 = window.renderFeedSidebar;
  if (oSideP1) window.renderFeedSidebar = function () { var h = oSideP1.apply(this, arguments); if (!ME_UUID || typeof h !== 'string') return h;
    ['>Upcoming Events<', '>Trending in Pharma<'].forEach(function (k) { var i = h.indexOf(k), a = i < 0 ? -1 : h.lastIndexOf('<div class="card"', i), z = i < 0 ? -1 : h.indexOf('<div class="card"', i);
      if (a >= 0) h = h.slice(0, a) + (z > a ? h.slice(z) : ''); });
    return h; };
  var oHeroP1 = window.renderFeedHero;
  if (oHeroP1) window.renderFeedHero = function () { var h = oHeroP1.apply(this, arguments); if (!ME_UUID || typeof h !== 'string') return h;
    return h.replace('<b>12K+</b> professionals', '<b>' + (PG.members == null ? '…' : Number(PG.members).toLocaleString('en')) + '</b> ' + (PG.members === 1 ? 'professional' : 'professionals')); };
  async function loadMembers() { var r = await sb.from('profiles').select('id', { count: 'exact', head: true }); if (r.error) throw r.error; PG.members = r.count || 0;
    var t = document.querySelector('#content .dg-hero .dg-faces-tx b'); if (t) t.textContent = Number(PG.members).toLocaleString('en'); }

  /* ── Marketplace (B-06): counts from market_stats() (0033), the newest real listings and jobs, no sample services / jobs /
     comparisons; My Listings (B-07) lists my own listings only ── */
  async function loadMarketExtra() {
    var a = await Promise.all([sb.rpc('market_stats'), sb.from('jobs').select('id, title, company, location, country, type, seniority, tags, description, created_at, user_id, poster:profiles!jobs_user_id_fkey(' + PCOLS + ')').eq('active', true).order('created_at', { ascending: false }).limit(5)]);
    if (a[0].error) throw a[0].error; PG.stats = a[0].data || {}; PG.jobs = (a[1] && !a[1].error && a[1].data) || []; PG.jobs.forEach(function (j) { putUser(j.poster); }); PG.statsAt = Date.now();
  }
  function stat(k) { var s = PG.stats || {}; return +s[k] || 0; }
  function catN(k) { var s = PG.stats || {}, c = s.by_cat || {}; return +c[k] || 0; }
  function fmtK(n) { return n >= 10000 ? (Math.round(n / 100) / 10).toLocaleString('en') + 'K' : n.toLocaleString('en'); }
  var oPill = window.dgPillText;
  if (oPill) window.dgPillText = function (page) {
    if (ME_UUID && page === 'market') { var f = function (n) { return PG.stats ? fmtK(n) : '…'; }; return f(stat('supply') + stat('demand')) + ' LISTINGS  /  ' + f(stat('supply')) + ' SUPPLY  /  ' + f(stat('demand')) + ' DEMAND  /  ' + f(stat('suppliers')) + ' SUPPLIERS'; }
    return oPill.apply(this, arguments);
  };
  function setNum(e, v) { if (e && e.textContent !== v) e.textContent = v; }
  function hideEl(e) { if (e && e.style.display !== 'none') e.style.display = 'none'; }
  function mkEmpty(text) { return '<div class="dx-mk-empty" style="padding:18px;color:#65676b;font-size:13px;grid-column:1/-1">' + text + '</div>'; }
  function paintMarketChrome() {
    var mk = document.getElementById('mkx'); if (!mk || !ME_UUID) return;
    var q = function (s) { return mk.querySelector(s); }, qa = function (s) { return [].slice.call(mk.querySelectorAll(s)); }, ok = !!PG.stats;
    var counts = { supply: stat('supply'), demand: stat('demand'), cmo: catN('cmo'), equipment: catN('equipment'), license: catN('registration'), service: catN('service'), job: stat('jobs'), training: 0 };
    /* the page pill, hero and category numbers */
    var pill = document.querySelector('#content .dg-pill-page'); if (pill) setNum(pill, window.dgPillText('market'));
    var hs = qa('.hero-stats .hstat-n'), hv = [stat('supply') + stat('demand'), stat('suppliers'), stat('jobs'), catN('service')];
    hs.forEach(function (e, i) { setNum(e, ok ? fmtK(hv[i] || 0) : '…'); });
    var CATS = ['supply', 'demand', 'license', 'cmo', 'equipment', 'service', 'job'];
    qa('.cat-grid .cat-item .cat-count').forEach(function (e, i) { setNum(e, ok ? (counts[CATS[i]] || 0).toLocaleString('en') : '…'); });
    qa('.f-count[data-cat]').forEach(function (e) { var k = e.dataset.cat; if (k === 'training') { hideEl(e); return; } setNum(e, ok ? (counts[k] || 0).toLocaleString('en') : '…'); });
    if (window.categoryTotals) { Object.keys(window.categoryTotals).forEach(function (k) { window.categoryTotals[k] = counts[k] || 0; }); }
    var lr = document.getElementById('liveResultCount'); if (lr && ok && !lr.dataset.dxReal) { lr.dataset.dxReal = '1'; if (typeof window.updateLiveCount === 'function') window.updateLiveCount(); }
    var sc = q('.supply-grid') && q('.supply-grid').parentElement.querySelector('.sec-count'); if (sc) setNum(sc, ok ? stat('supply').toLocaleString('en') + (stat('supply') === 1 ? ' listing' : ' listings') : '');
    var dbn = q('.db-title span'); if (dbn) setNum(dbn, ok ? stat('demand').toLocaleString('en') : '');
    /* promises the live app does not measure or keep: the reach / "8×" claims and the free-vs-sponsored table */
    var pb = q('.pricing-banner'); if (pb) { setTextNode(pb, /reach 150,000\+/, function (o) { return o.replace(/reach 150,000\+.*$/, 'show it at the top of the marketplace'); });
      setTextNode(pb, /8× more views/, function (o) { return o.replace(/Sponsored listings get 8× more views.*$/, 'Boosted and featured listings appear before free ones'); }); }
    hideEl(q('.compare-section'));
    var uc = q('.upgrade-cta'); if (uc) { setTextNode(uc, /Reach 150,000\+/, function (o) { return o.replace(/Reach 150,000\+.*$/, 'Show your listing at the top of the marketplace, before free listings.'); });
      [].forEach.call(uc.querySelectorAll('.fl-item'), function (x) { if (/Analytics|Demand alerts|Verified seller/i.test(window.dxOrigText ? window.dxOrigText(x) : x.textContent)) hideEl(x); }); }
    /* Live now: the newest real listings, requests and jobs */
    var act = q('.activity'); if (act) {
      var feed = [];
      MKT.products.slice(0, 6).forEach(function (p) { var s = p.seller || {}; feed.push({ at: p.created_at, ic: p.category === 'service' ? '🛠' : '📨', b: p.category === 'service' ? 'New service:' : (s.name || 'A member'), t: p.category === 'service' ? p.name + (s.name ? ' by ' + s.name : '') : 'listed ' + p.name }); });
      MKT.demand.slice(0, 4).forEach(function (e) { feed.push({ at: e.created_at, ic: '🔍', b: 'Demand:', t: e.title }); });
      PG.jobs.slice(0, 3).forEach(function (j) { feed.push({ at: j.created_at, ic: '💼', b: 'New job:', t: j.title + (j.location ? ' · ' + j.location : '') }); });
      feed.sort(function (a, b) { return new Date(b.at) - new Date(a.at); }); feed = feed.slice(0, 5);
      var key = feed.map(function (f) { return f.b + f.t; }).join('|') || (MKT.at ? 'none' : 'wait');
      if (act.dataset.dxKey !== key) { act.dataset.dxKey = key; act.querySelectorAll('.act-item').forEach(function (x) { x.remove(); });
        if (!feed.length) act.insertAdjacentHTML('beforeend', '<div class="act-item"><span>🕒</span>' + (MKT.at ? 'Nothing posted yet — new listings show here as they are posted.' : 'Loading…') + '</div>');
        feed.forEach(function (f) { var r = document.createElement('div'); r.className = 'act-item'; r.innerHTML = '<span></span><b data-noi18n></b> '; r.firstChild.textContent = f.ic; r.children[1].textContent = f.b;
          if (/:$/.test(f.b)) r.children[1].removeAttribute('data-noi18n'); var tx = document.createElement('span'); tx.setAttribute('data-noi18n', ''); tx.textContent = f.t; if (/^listed /.test(f.t)) { tx.removeAttribute('data-noi18n'); }
          r.appendChild(tx); act.appendChild(r); }); }
    }
    /* Professional services: real service listings (the approved service card is the template) */
    var sg = q('.services-grid'); if (sg) {
      var demoS = [].slice.call(sg.querySelectorAll('.scard:not([data-live])')); if (demoS.length && !PG.tplS) PG.tplS = demoS[0].outerHTML; demoS.forEach(function (x) { x.remove(); });
      var svc = MKT.products.filter(function (p) { return p.category === 'service'; }), skey = svc.map(function (p) { return p.id; }).join(',') + '|' + !!MKT.at;
      if (PG.tplS && sg.dataset.dxKey !== skey) { sg.dataset.dxKey = skey; sg.querySelectorAll('.scard[data-live], .dx-mk-empty').forEach(function (x) { x.remove(); });
        svc.forEach(function (p) { sg.appendChild(serviceCard(p)); }); if (!svc.length) sg.insertAdjacentHTML('beforeend', mkEmpty(MKT.at ? 'No services listed yet — offer yours with “+ Offer Service”.' : 'Loading…')); }
      var st = q('.ss-title span'); if (st) setNum(st, ok ? stat('service_providers').toLocaleString('en') + (stat('service_providers') === 1 ? ' provider' : ' providers') : '');
    }
    /* Jobs & careers: the newest real jobs; Apply opens the job on the Jobs page, where applications are kept */
    var jl = q('.jobs-list'); if (jl) {
      var demoJ = [].slice.call(jl.querySelectorAll('.jcard:not([data-live])')); if (demoJ.length && !PG.tplJ) PG.tplJ = demoJ[0].outerHTML; demoJ.forEach(function (x) { x.remove(); });
      var jkey = PG.jobs.map(function (j) { return j.id; }).join(',') + '|' + !!PG.statsAt;
      if (PG.tplJ && jl.dataset.dxKey !== jkey) { jl.dataset.dxKey = jkey; jl.querySelectorAll('.jcard[data-live], .dx-mk-empty').forEach(function (x) { x.remove(); });
        PG.jobs.slice(0, 4).forEach(function (j) { jl.appendChild(mkJobCard(j)); }); if (!PG.jobs.length) jl.insertAdjacentHTML('beforeend', mkEmpty(PG.statsAt ? 'No open jobs yet — post the first one with “+ Post a Job”.' : 'Loading…')); }
      var jt = q('.js-title span'); if (jt) setNum(jt, ok ? stat('jobs').toLocaleString('en') + (stat('jobs') === 1 ? ' open position' : ' open positions') : '');
    }
    /* the side column: demand board empty state and the latest jobs */
    var dgrid = q('[data-live-demand]'); if (dgrid) { var de = dgrid.querySelector(':scope > .dx-mk-empty'); if (MKT.at && !MKT.demand.length) { if (!de) { var h = q('.db-sub'); if (h) h.insertAdjacentHTML('afterend', mkEmpty('No open requests yet.')); } } else if (de) de.remove(); }
    var lt = qa('.demand-board > div').find(function (x) { var o = window.dxOrigText ? window.dxOrigText(x) : x.textContent; return /Latest Jobs/.test(o) && o.length < 30; }), box = lt && lt.nextElementSibling;
    if (box) { var lkey = PG.jobs.map(function (j) { return j.id; }).join(',') + '|' + !!PG.statsAt;
      if (box.dataset.dxKey !== lkey) { box.dataset.dxKey = lkey; var tplRow = box.firstElementChild && !box.firstElementChild.dataset.job ? box.firstElementChild.getAttribute('style') : PG.rowStyle; PG.rowStyle = tplRow || PG.rowStyle; box.innerHTML = '';
        PG.jobs.slice(0, 4).forEach(function (j) { var r = document.createElement('div'); r.setAttribute('style', PG.rowStyle || 'cursor:pointer;padding:4px 0;border-bottom:1px solid #f0f4fb'); r.dataset.job = j.id; r.setAttribute('role', 'link'); r.setAttribute('tabindex', '0'); r.setAttribute('data-noi18n', '');
          r.textContent = '→ ' + j.title + (j.company ? ' · ' + j.company : '') + ' ' + (FLAG[j.country] || ''); box.appendChild(r); });
        if (!PG.jobs.length) box.innerHTML = '<div style="padding:4px 0">' + (PG.statsAt ? 'No open jobs yet.' : 'Loading…') + '</div>'; } }
    paintMyListings();
  }
  function serviceCard(p) {
    var c = el(PG.tplS), u = p.seller || {}, docs = p.docs || []; c.dataset.live = 'p' + p.id; c.dataset.uid = aid(p.user_id);
    var ic = c.querySelector('.sc-ic'); if (ic) ic.textContent = p.emoji && p.emoji !== '📦' ? p.emoji : '🛠️';
    var t = c.querySelector('.sc-title'); if (t) t.textContent = p.name;
    var pv = c.querySelector('.sc-provider'); if (pv) { pv.innerHTML = '<span data-noi18n></span>' + (u.verified ? ' · <span style="color:#1a56db">✓ Verified</span>' : ''); pv.firstChild.textContent = [u.name || 'Member', ((FLAG[u.country] || '') + ' ' + (u.location || '')).trim()].filter(Boolean).join(' · '); }
    var tg = c.querySelector('.sc-tags'); if (tg) { tg.innerHTML = ''; docs.slice(0, 3).forEach(function (d) { var s = document.createElement('span'); s.className = 'sc-tag'; s.textContent = d; tg.appendChild(s); }); }
    var pr = c.querySelector('.sc-price'); if (pr) pr.textContent = (p.price || 'On request') + (p.price && p.unit ? '/' + p.unit : '');
    var ra = c.querySelector('.sc-rating'); if (ra) ra.textContent = ago(p.created_at);
    return c;
  }
  function mkJobCard(j) {
    var c = el(PG.tplJ), u = j.poster || {}; c.dataset.live = 'j' + j.id; c.dataset.uid = aid(j.user_id);
    var lg = c.querySelector('.jc-logo'); if (lg) { lg.textContent = initials(j.company || u.name); lg.style.background = colorFor(j.company || j.user_id); }
    var t = c.querySelector('.jc-title'); if (t) { var rb = t.querySelector('.role-badge'); t.textContent = j.title; if (rb) t.insertBefore(rb, t.firstChild); }
    var co = c.querySelector('.jc-company'); if (co) co.innerHTML = '<span>' + esc2(j.company || u.company || u.name || '') + '</span> · <span>' + (FLAG[j.country] || '') + ' ' + esc2(j.location || '') + '</span>' + (u.verified ? ' · <span style="color:#1a56db">✓ Verified</span>' : '');
    var tg = c.querySelector('.jc-tags'); if (tg) { var tags = [String(j.type || 'full-time').replace(/(^|-)([a-z])/g, function (m, a, b) { return a + b.toUpperCase(); })].concat((j.tags || []).slice(0, 2));
      tg.innerHTML = tags.map(function (x, i) { return '<span class="jt' + (i ? '' : ' jt-ft') + '">' + esc2(x) + '</span>'; }).join(''); }
    var ds = c.querySelector('.jc-desc'); if (ds) ds.textContent = String(j.description || '').slice(0, 180);
    var ps = c.querySelector('.jc-posted'); if (ps) ps.textContent = ago(j.created_at);
    var sv = c.querySelector('.save-btn'); if (sv) sv.remove();
    return c;
  }
  /* a job from the marketplace opens on the Jobs page (its Apply there saves the application) */
  function openJob(id) {
    window.goto('jobs'); var tries = 0;
    (function wait() { var b = document.querySelector('#jx .jcard[data-live="j' + id + '"]');
      if (b) { b.scrollIntoView({ block: 'center' }); var ap = b.querySelector('.apply-btn'); if (ap && !ap.disabled) ap.click(); return; }
      if (++tries < 40) setTimeout(wait, 150); })();
  }
  document.addEventListener('click', function (e) {
    if (!ME_UUID || !e.target.closest) return;
    var ap = e.target.closest('#mkx .jcard[data-live] .apply-btn, #mkx .demand-board [data-job]');
    if (ap) { e.preventDefault(); e.stopPropagation(); var id = ap.dataset.job || (ap.closest('[data-live]').dataset.live || '').slice(1); openJob(+id); return; }
    var sv = e.target.closest('#mkx .scard[data-live] .sc-btn'); if (sv) { e.preventDefault(); e.stopPropagation(); window.messageUser(+sv.closest('[data-live]').dataset.uid); }
  }, true);
  /* My Listings: my own listings and requests (no sample rows). Views and inquiries are not counted by the live app yet, so those
     numbers are left out; Boost is the real checkout. Editing, pausing and renewing come with B-07. */
  var ML = { rows: [], at: 0, loading: false };
  async function loadMyListings() {
    var a = await Promise.all([sb.from('products').select('id, name, emoji, category, active, created_at, boosted_until, featured_until').eq('user_id', ME_UUID).order('created_at', { ascending: false }).limit(100),
                               sb.from('enquiries').select('id, title, category, status, created_at').eq('user_id', ME_UUID).eq('type', 'demand').order('created_at', { ascending: false }).limit(100)]);
    if (a[0].error) throw a[0].error; if (a[1].error) throw a[1].error;
    ML.rows = (a[0].data || []).map(function (p) { return { kind: 'p', id: p.id, name: p.name, em: p.emoji || '📦', active: p.active !== false, at: p.created_at, boosted: promoted(p, 'boosted_until') || promoted(p, 'featured_until') }; })
      .concat((a[1].data || []).map(function (e) { return { kind: 'e', id: e.id, name: e.title, em: '🔍', active: e.status === 'active', at: e.created_at, boosted: false, demand: true }; }))
      .sort(function (x, y) { return new Date(y.at) - new Date(x.at); });
    ML.at = Date.now();
  }
  function paintMyListings() {
    var m = document.getElementById('tab-manage'); if (!m) return;
    var stats = [].slice.call(m.querySelectorAll('div[style*="font-size:18px;font-weight:800"]'));
    /* the approved sample rows (and a "just published" row the page adds itself — the database row replaces it) go; a draft the
       page saved in this browser stays: it is this person's own and only exists here */
    var isDraft = function (x) { var b = x.querySelector('span'); return !!b && /^Draft$/i.test(((window.dxOrigText ? window.dxOrigText(b) : b.textContent) || '').trim()); };
    var rows0 = [].slice.call(m.querySelectorAll('div[style*="padding:14px 0"]:not([data-ml])')), list = rows0.length ? rows0[0].parentElement : m.querySelector('[data-ml-list]');
    var sample = rows0.filter(function (x) { return !isDraft(x); });
    if (sample.length && !ML.tpl) ML.tpl = sample[0].outerHTML; sample.forEach(function (x) { x.remove(); }); if (list) list.setAttribute('data-ml-list', '1');
    [].forEach.call(m.querySelectorAll('div[style*="#fffbeb"]'), function (x) { if (/Expiry notice/.test(window.dxOrigText ? window.dxOrigText(x) : x.textContent)) hideEl(x); });
    var act = ML.rows.filter(function (r) { return r.active; }).length, bo = ML.rows.filter(function (r) { return r.boosted; }).length;
    if (stats[0]) setNum(stats[0], ML.at ? act.toLocaleString('en') : '…'); if (stats[3]) setNum(stats[3], ML.at ? bo.toLocaleString('en') : '…');
    [stats[1], stats[2]].forEach(function (s) { if (s && s.parentElement) hideEl(s.parentElement); });
    if (!list || !ML.tpl) return;
    var key = ML.rows.map(function (r) { return r.kind + r.id + (r.active ? 'a' : 'p') + (r.boosted ? 'b' : ''); }).join(',') + '|' + !!ML.at;
    if (list.dataset.dxKey === key && !sample.length) return; list.dataset.dxKey = key;
    list.querySelectorAll('[data-ml], .dx-mk-empty').forEach(function (x) { x.remove(); });
    ML.rows.forEach(function (r) { list.appendChild(myListingRow(r)); });
    if (!ML.rows.length) list.insertAdjacentHTML('beforeend', mkEmpty(ML.at ? 'You have no listings yet — publish one with “New Listing”.' : 'Loading…'));
  }
  function myListingRow(r) {
    var row = el(ML.tpl); row.dataset.ml = r.kind + r.id; row.style.opacity = r.active ? '' : '0.5';
    var kids = row.children, ic = kids[0], info = kids[1], nums = kids[2], acts = kids[3];
    if (ic) ic.textContent = r.em;
    if (info) { var t = info.children[0], sub = info.children[1], badge = t && t.querySelector('span');
      if (t) { t.textContent = ''; var nm = document.createElement('span'); nm.setAttribute('data-noi18n', ''); nm.textContent = r.name; t.appendChild(nm);
        if (badge) { badge.textContent = r.boosted ? 'Boosted' : r.active ? (r.demand ? 'Open request' : 'Active') : 'Closed'; badge.style.background = r.boosted ? '#fef9c3' : r.active ? '#dcfce7' : '#f1f5f9'; badge.style.color = r.boosted ? '#a16207' : r.active ? '#15803d' : '#475569'; t.appendChild(badge); } }
      if (sub) sub.textContent = 'Posted ' + ago(r.at); }
    if (nums) nums.remove();
    if (acts) { acts.innerHTML = ''; if (r.kind === 'p' && r.active && !r.boosted) { var b = document.createElement('button'); b.setAttribute('style', 'padding:6px 12px;border-radius:7px;font-size:11.5px;font-weight:700;border:none;cursor:pointer;background:#fef3c7;color:#92400e'); b.setAttribute('onclick', "openBoostModal('boost')"); b.textContent = '⭐ Boost'; acts.appendChild(b); } }
    return row;
  }
  var oMarketP1 = window.renderMarket;
  window.renderMarket = function () {
    var r = oMarketP1.apply(this, arguments); if (!ME_UUID) return r;
    paintMarketChrome();
    var stale = Date.now() - PG.statsAt > 20000, mlStale = Date.now() - ML.at > 20000;
    if ((stale || mlStale) && !PG.loading) { PG.loading = true;
      Promise.all([stale ? loadMarketExtra() : null, mlStale ? loadMyListings() : null]).then(function () { PG.loading = false; if (onPageNow('market')) paintMarketChrome(); }, function (e) { PG.loading = false; toastErr(e); }); }
    return r;
  };
  var loadMarketD1 = loadMarket;
  loadMarket = async function () { await loadMarketD1(); if (onPageNow('market')) setTimeout(paintMarketChrome, 0); };
  var hookP1 = window.dxLiveHook;   /* a listing just published: My Listings and the counts are read again */
  window.dxLiveHook = function (kind, d) { var r = hookP1 ? hookP1(kind, d) : undefined; if (kind === 'listing' && ME_UUID) { ML.at = 0; PG.statsAt = 0; setTimeout(function () { Promise.all([loadMyListings(), loadMarketExtra()]).then(function () { if (onPageNow('market')) paintMarketChrome(); }).catch(function () {}); }, 1200); } return r; };

  /* Messages: no sample "Online now" strip (the live app has no presence yet), "Unread (N)" from my conversations, and no sample
     chat header while there is no conversation to show */
  function paintMsgChrome() {
    var mx = document.getElementById('mx'); if (!mx || !ME_UUID) return;
    hideEl(mx.querySelector('.online-strip'));
    var un = mx.querySelector('.tp-filter[data-filter="unread"]'), n = MX.convs.filter(function (c) { return c.unread; }).length;
    if (un) setTextNode(un, /^\s*Unread \(\d+\)\s*$/, function (o) { return o.replace(/\(\d+\)/, '(' + n + ')'); });
    var cb = mx.querySelector('.chat-head'); if (cb && !MX.convs.length && !MX.open) cb.style.visibility = 'hidden';
  }
  var oMsgP1 = window.renderMessages;
  window.renderMessages = function () { var r = oMsgP1.apply(this, arguments); if (ME_UUID) paintMsgChrome(); return r; };
  var loadConvsB4 = loadConvs;
  loadConvs = async function () { var r = await loadConvsB4.apply(this, arguments); setTimeout(paintMsgChrome, 0); return r; };

  /* everything above starts empty at sign-in: no sample badge, shortcut, group or connection is ever on screen */
  var hydrateP1 = hydrateMe;
  hydrateMe = async function (uid) {
    var me = await hydrateP1(uid);
    Object.keys(window.CONN_STATE || {}).forEach(function (k) { if (+k <= 1000) delete window.CONN_STATE[k]; });   /* the sample people's connection states */
    ['nb-net', 'nb-msg', 'nb-not'].forEach(function (id) { var e = document.getElementById(id); if (e) { e.textContent = '0'; e.style.display = 'none'; } });
    if (Array.isArray(window.GROUPS)) window.GROUPS.length = 0;
    navBadges(); paintShortcuts();
    loadMyGroups().catch(function (e) { console.error(e); }); loadMembers().catch(function (e) { console.error(e); });
    return me;
  };
  /* the Groups page loaded or changed my groups: the side menu and the network card follow */
  var paintGroupsD3 = paintGroups;
  paintGroups = function () { paintGroupsD3(); if (GX.at) syncGroupsGlobal(); };
  var oNetP1 = window.renderNetwork;
  window.renderNetwork = function () { var r = oNetP1.apply(this, arguments); if (ME_UUID) setTimeout(paintNetGroups, 0); return r; };
  onReset(function () { PG.my = []; PG.myAt = 0; PG.stats = null; PG.statsAt = 0; PG.jobs = []; PG.members = null; ML.rows = []; ML.at = 0; });
  window.dxLive.version = 'P1';











})();
