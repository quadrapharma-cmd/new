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
  var PCOLS = 'id,name,headline,company,country,bio,avatar_url,role,verified,location,open_to_work,hiring,profile_views,followers_count,name_needs_fix';
  /* a whole profile (opening someone's profile): every column members may read — phone is private (0036: column privileges, so
     select=* is refused; the signed-in member's own row, phone included, comes from my_profile()) */
  var PFULL = PCOLS + ',cover_url,website,certs,account_type,created_at,updated_at,experience,education,certifications,skills,languages,years_experience,desired_role,desired_type,remote_ok,available_since,intro_video,intents';
  /* errors are shown in words people understand — never raw database text (table, policy or function names) */
  var TECH = /relation|column|function|schema|syntax|constraint|violates|PGRST|null value|operator|SQLSTATE|policy|permission|privilege|JSON object|cannot coerce|does not exist/i;
  function friendly(x) {
    var m = typeof x === 'string' ? x : String((x && x.message) || x || ''), code = x && typeof x === 'object' && x.code ? String(x.code) : '', st = x && typeof x === 'object' ? +x.status || 0 : 0;
    if (/invalid login credentials/i.test(m)) return 'Wrong email or password';
    if (/already registered/i.test(m)) return 'An account with this email already exists — sign in instead';
    if (/at least 8/i.test(m)) return 'Password must be at least 8 characters';
    if (/invalid email|unable to validate email/i.test(m)) return 'Please enter a valid email';
    /* the name rule (0038): the database's sentence is the app's (nmMessage), translated by i18n.js; sign-up's own API only says
       "Database error saving new user" when the sign-up trigger refuses the name */
    if (x && typeof x === 'object' && /^name:/.test(String(x.hint || ''))) return m;
    if (/database error saving new user/i.test(m)) return 'This name cannot be used — a name can only have letters, spaces and . - \' ’ ( ) ,';
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
    var r = await sb.rpc('my_profile').single();                      /* my own row, phone included (0036) */
    if (r.error) throw r.error; if (r.data && r.data.id !== uid) throw new Error('Your session ended — please sign in again');
    var p = r.data; if (ME_UUID && ME_UUID !== p.id) resetUser(); ME_UUID = p.id;
    Object.assign(window.ME, {
      id: aid(p.id), name: txt(p.name), initials: initials(txt(p.name)), headline: txt(p.headline), company: txt(p.company), country: txt(p.country || 'EG'),
      verified: !!p.verified, role: p.role || 'user', bio: prose(p.bio), web: safeUrl(p.website), phone: tel(p.phone), certs: txt(p.certs), avatar: safeUrl(p.avatar_url),
      location: txt(p.location), followers: p.followers_count || 0, openToWork: !!p.open_to_work, hiring: !!p.hiring, color: colorFor(p.id),
      profileViews: p.profile_views || '0', connections: '0',         /* '0', not 0: the approved sidebar shows sample numbers for a falsy value */
      intents: (p.intents && typeof p.intents === 'object') ? p.intents : {},
      nameFix: !!p.name_needs_fix                                       /* my name breaks the name rule (0038): asked to update it */
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
    var nn = nmNorm(name), np = nmProblem(nn); if (np) return show('suErr', nmMessage(nn, np));   /* the name rule of the database (0038), said before anything is sent */
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
  /* the approved page's "Admin access required" (renderAdmin may be replaced when its page script loads, so this runs after
     each render, not as a wrapper) */
  function adminNote() {
    var c = document.getElementById('content'); if (!c || !ME_UUID || isStaff() || document.body.getAttribute('data-page') !== 'admin') return;
    if (c.querySelector('.dx-admin-no')) return;
    var t = Array.prototype.find.call(c.querySelectorAll('div'), function (d) { return !d.firstElementChild && /^(Admin access required|يلزم صلاحية الإدارة)$/.test(d.textContent.trim()); }), box = t && t.parentElement; if (!box) return;
    var d = document.createElement('div'); d.className = 'dx-admin-no'; d.style.cssText = 'font-size:13px;margin-top:6px'; d.textContent = 'Your account is not allowed here — Admin is for Drugbox staff.'; box.appendChild(d);
  }
  paintAdminEntry(); if (window.dxCore) window.dxCore.onRender('live-admin-entry', function () { paintAdminEntry(); adminNote(); });
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
    /* the name rule (0038), said next to the name like the approved form's own checks; a name the rule flagged may be kept while
       the other fields are saved (the database keeps it too) */
    var nn = nmNorm(f.name), np = nmProblem(nn);
    if (np && !(window.ME.nameFix && nn === nmNorm(window.ME.name))) {
      var ne = document.getElementById('ep-name'), er = document.getElementById('ep-err'), msg = nmMessage(nn, np);
      if (ne) { ne.setAttribute('aria-invalid', 'true'); ne.setAttribute('aria-describedby', 'ep-err'); if (er) ne.parentNode.appendChild(er); ne.focus(); }
      if (er) { er.textContent = msg; er.style.display = 'block'; } else if (typeof window.toast === 'function') window.toast(msg);
      return;
    }
    var btn = document.querySelector('.modal-bg [onclick^="saveProfile"]'); PSAVE = true; if (btn) { btn.disabled = true; btn.setAttribute('aria-busy', 'true'); }
    try {
      var nul = function (v) { return v ? v : null; };
      var r = await sb.from('profiles').update({ name: f.name, headline: nul(f.headline), company: nul(f.company), location: nul(f.location), website: nul(f.web),
        phone: nul(f.phone), certs: nul(f.certs), bio: nul(f.bio), open_to_work: !!f.openToWork, updated_at: new Date().toISOString() })
        .eq('id', ME_UUID).select('name,headline,company,location,website,certs,bio,open_to_work,name_needs_fix').single();   /* phone is never read back through the API (0036) */
      if (r.error) throw r.error;
      var p = r.data; p.phone = f.phone; window.ME.nameFix = !!p.name_needs_fix;
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
    if ('website' in p) { u.web = safeUrl(p.website); u.certs = txt(p.certs); u.full = true; if (p.intents && typeof p.intents === 'object') u.intents = p.intents; }
    if ('name_needs_fix' in p) u.nameFix = !!p.name_needs_fix;                                       /* a name that breaks the rule (0038) */
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
  /* Drugbox's own notices (a post removed, a report decided) have no sender: they show Drugbox, never the reader's own initials */
  var SYS_UID = -1, SYS_USER = { id: SYS_UID, name: 'Drugbox', initials: 'DB', color: '#1a56db', headline: '', company: '', verified: true };
  var oU = window.U; if (typeof oU === 'function') window.U = function (id) { return id === SYS_UID ? SYS_USER : oU.apply(this, arguments); };
  var WHY = { spam: 'spam or an unrelated ad', counterfeit: 'an unverified or counterfeit product', misleading: 'misleading information', abusive: 'harassment or hate' };
  /* the sentence is written here from the data 0036 keeps, in English — the Arabic interface translates it like any notice */
  function sysText(n) { var d = n.data && typeof n.data === 'object' ? n.data : null; if (!d) return esc2(n.message || '');
    if (n.type === 'report_closed') return d.outcome === 'removed' ? 'Drugbox reviewed your report and removed the post.' : 'Drugbox reviewed your report — the post stays up.';
    return esc2('Drugbox removed your post “' + String(d.excerpt || '') + '” — reason: ' + (WHY[d.reason] || 'it breaks the Drugbox rules') + '.' + (d.note ? ' Note: ' + String(d.note) : '')); }
  function notifFrom(n) {
    var who = esc2(n.actor ? n.actor.name : 'Someone'), a = aid(n.from_user), t;
    if (n.type === 'connection_request') t = '<b>' + who + '</b> sent you a connection request';
    else if (n.type === 'connection_accepted') t = '<b>' + who + '</b> accepted your connection request';
    else if (n.type === 'like') t = '<b>' + who + '</b> reacted to your post';
    else if (n.type === 'comment') t = '<b>' + who + '</b> commented: "' + esc2(n.message || '') + '"';
    else if (n.type === 'post_removed' || n.type === 'report_closed') { t = sysText(n); if (!n.from_user) a = SYS_UID; }
    else if (n.type === 'company_message' && n.company_id) t = '<b>' + who + '</b> messaged ' + esc2(n.company && n.company.name ? n.company.name : 'your company') + ': "' + esc2(n.message || '') + '"';   /* written here, in the reader's language (0034); older rows carry their sentence */
    else t = '<b>' + who + '</b> ' + esc2(n.message || '');
    var type = n.type === 'connection_request' ? (INCOMING[a] ? 'connection' : 'accepted') : n.type === 'connection_accepted' ? 'accepted' : n.type;
    return { id: n.id, uid: a, icon: ICON[n.type] || '🔔', text: t, ts: ago(n.created_at), read: !!n.read, type: type, pid: n.post_id || null };
  }
  async function loadNotifs() {
    var r = await sb.from('notifications').select('*, actor:profiles!notifications_from_user_fkey(' + PCOLS + '), company:companies(name)').eq('user_id', ME_UUID).order('created_at', { ascending: false }).limit(50);
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
    var nm = el.querySelector('.t-name'), tw = mxTwinFact(c.partner); if (nm) nm.innerHTML = esc2(c.name || 'Member') + (c.verified ? ' <span style="color:#1a56db;font-size:10px">✓</span>' : '') + (tw ? ' <span class="dx-mx-twin" style="color:#65676b;font-weight:400;flex:1 1 0;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">· ' + esc2(tw) + '</span>' : '');
    var tm = el.querySelector('.t-time'); if (tm) tm.textContent = shortAgo(c.last_at);
    var pv = el.querySelector('.t-preview'); if (pv) { pv.textContent = (c.last_from_me ? 'You: ' : '') + (c.last_body || ''); pv.classList.toggle('unread-text', !!c.unread); }
    var tag = el.querySelector('.t-context-tag'); if (tag) tag.remove();
    var bd = el.querySelector('.t-badge'); if (c.unread) { if (!bd) { bd = document.createElement('div'); bd.className = 't-badge'; el.appendChild(bd); } bd.textContent = c.unread; } else if (bd) bd.remove();
    return el;
  }
  /* two conversations with members of the same name (S-03): each says what tells them apart — the company, else the headline,
     else the city, else a short handle from the id — in the list and under the name in the chat header. '' when no other
     conversation or known member shares the name. */
  function mxFacts(id) { var u = nmUser(id); return u ? [String(u.headline || '').split('|')[0].trim(), u.company, u.location].map(nmFact).filter(Boolean) : []; }
  function mxTwinFact(id) {
    var u = nmUser(id), k = u && nmKey(u.name); if (!k) return '';
    var twins = (window.USERS || []).filter(function (x) { return x.id !== u.id && x.id !== aid(ME_UUID) && nmKey(x.name) === k; });   /* same skeleton: looks the same */
    if (!twins.length && !u.nameFix) return '';                                                                                       /* a name that breaks the rule is told apart even alone */
    var mine = mxFacts(id), co = nmFact(u.company), others = twins.map(function (x) { return x.id; });
    if (co && !twins.some(function (x) { return nmKey(x.company) === nmKey(co); })) return co;
    var f = mine.find(function (v) { return !others.some(function (o) { return mxFacts(uuidOf(o)).some(function (w) { return nmKey(w) === nmKey(v); }); }); });
    return f || nmHandle(uuidOf(u.id) || '');
  }
  window.dxMxPartner = function () { return ME_UUID && MX.open ? MX.open : 0; };   /* links.js: 👤 / 📞 act on the open conversation's member, never a name look-up */
  async function loadConvs() { var q = await Promise.all([sb.rpc('my_conversations', { p_limit: 50 }), loadPrefs().catch(function (e) { console.error(e); })]), r = q[0]; if (r.error) throw r.error;
    MX.convs = r.data || []; MX.convs.forEach(function (c) { putUser({ id: c.partner, name: c.name, headline: c.headline, verified: c.verified, avatar_url: c.avatar_url, company: c.company, location: c.location, name_needs_fix: c.name_needs_fix }); }); msgBadge(); return MX.convs; }
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
    /* the header under the name says who this is (headline · company · city) — there is no presence in the live app, so never
       "Last seen recently"; two members with the same name are told apart here too (S-03) */
    var hu = nmUser(partner), st = document.querySelector('.chat-head .ch-status');
    if (st) { var tf = mxTwinFact(partner), hf = mxFacts(partner); st.textContent = hf.concat(tf && tf.charAt(0) === '#' ? [tf] : []).join(' · '); }
    var hn = document.querySelector('.chat-head .ch-name'), hc = MX.convs.find(function (x) { return x.partner === partner; });   /* the name only: the list's "· company" is said on the line below */
    if (hn && hu) hn.innerHTML = esc2(hu.name) + ((hc ? hc.verified : hu.verified) ? ' <span style="color:#1a56db;font-size:11px">✓</span>' : '');
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
    var th = listEl() && listEl().querySelector('.mx-thread[data-person="u' + MX.open + '"]'), was = null;
    if (th) { var pv = th.querySelector('.t-preview'), tm = th.querySelector('.t-time');
      was = { pv: pv && pv.textContent, unread: pv && pv.classList.contains('unread-text'), tm: tm && tm.textContent, next: th.nextSibling };   /* put back if the database refuses */
      if (pv) { pv.textContent = 'You: ' + text; pv.classList.remove('unread-text'); } if (tm) tm.textContent = 'now'; listEl().insertBefore(th, listEl().firstElementChild); }
    sb.from('messages').insert({ sender_id: ME_UUID, receiver_id: partner, body: text }).select().single().then(function (r) {
      if (r.error) { if (bubble) bubble.remove(); input.value = text; toastErr(r.error);
        /* refused (blocked, too long…): the conversation list says what it said before — never "You: …" for a message that was not sent */
        if (th && was && th.isConnected) { var pv2 = th.querySelector('.t-preview'), tm2 = th.querySelector('.t-time');
          if (pv2 && was.pv != null) { pv2.textContent = was.pv; pv2.classList.toggle('unread-text', !!was.unread); } if (tm2 && was.tm != null) tm2.textContent = was.tm;
          if (was.next && was.next.parentNode === th.parentNode) th.parentNode.insertBefore(th, was.next); else if (!was.next) th.parentNode.appendChild(th); }
        return; }
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

  /* ✎ New message (S-03): the picker offers your connections (first), your conversations and the members whose name matches
     what you type. Every option is a different text: members who share a name carry what tells them apart (company, headline,
     city, "your connection") and, when even that is the same, a short handle from their id. Send goes to the one member whose
     option was chosen, checked against every member with that name in the database just before sending — a name (or an option)
     that fits more than one member, or none, is refused and nothing is sent. Never a guess. */
  var NM = { people: {}, map: {}, ci: {}, t: null };
  function nmLike(x) { return String(x).replace(/[\\%_]/g, '\\$&'); }
  /* what a name may contain and when two names are the same name — the rule of the database (0038: person_name_norm,
     person_name_problem, person_name_message, person_name_key), generated with it from the Unicode data by tools/names/name_rule.mjs
     and compared code point by code point by supabase/tests/name_rule.sql:
     nmNorm  what a person reads: invisible characters and the tatweel removed, NFKC, one space between words
     nmProblem  '' when a name is allowed (letters of one script per word — Latin, Arabic; Greek or Cyrillic for the whole name —,
                marks on a letter, space, . - ' ’ ( ) ,), else why not; nmMessage says it (i18n.js translates)
     nmSkel  the TR39 confusable skeleton: "Rana" and "Rаna" (Cyrillic а), "Ilya" and "llya" are the same name here, and told apart */
/* >>> generated by tools/names/name_rule.mjs from Unicode 16.0.0 (UTS #39 data: tools/names/unicode-16.0.0) — do not edit by hand */
  var NM_INVIS = /[\u{1}-\u{8}\u{E}-\u{1F}\u{7F}-\u{84}\u{86}-\u{9F}\u{AD}\u{34F}\u{600}-\u{605}\u{61C}\u{640}\u{6DD}\u{70F}\u{890}-\u{891}\u{8E2}\u{115F}-\u{1160}\u{17B4}-\u{17B5}\u{180B}-\u{180F}\u{200B}-\u{200F}\u{202A}-\u{202E}\u{2060}-\u{206F}\u{2800}\u{3164}\u{FE00}-\u{FE0F}\u{FEFF}\u{FFA0}\u{FFF0}-\u{FFFB}\u{110BD}\u{110CD}\u{13430}-\u{1343F}\u{1BCA0}-\u{1BCA3}\u{1D159}\u{1D173}-\u{1D17A}\u{E0000}-\u{E0FFF}]/gu;
  var NM_SPACE = /[\u{9}-\u{D}\u{20}\u{85}\u{A0}\u{1680}\u{2000}-\u{200A}\u{2028}-\u{2029}\u{202F}\u{205F}\u{3000}]+/gu;
  var NM_DIGIT = /[\u{30}-\u{39}\u{B2}-\u{B3}\u{B9}\u{BC}-\u{BE}\u{660}-\u{669}\u{6F0}-\u{6F9}\u{7C0}-\u{7C9}\u{966}-\u{96F}\u{9E6}-\u{9EF}\u{9F4}-\u{9F9}\u{A66}-\u{A6F}\u{AE6}-\u{AEF}\u{B66}-\u{B6F}\u{B72}-\u{B77}\u{BE6}-\u{BF2}\u{C66}-\u{C6F}\u{C78}-\u{C7E}\u{CE6}-\u{CEF}\u{D58}-\u{D5E}\u{D66}-\u{D78}\u{DE6}-\u{DEF}\u{E50}-\u{E59}\u{ED0}-\u{ED9}\u{F20}-\u{F33}\u{1040}-\u{1049}\u{1090}-\u{1099}\u{1369}-\u{137C}\u{16EE}-\u{16F0}\u{17E0}-\u{17E9}\u{17F0}-\u{17F9}\u{1810}-\u{1819}\u{1946}-\u{194F}\u{19D0}-\u{19DA}\u{1A80}-\u{1A89}\u{1A90}-\u{1A99}\u{1B50}-\u{1B59}\u{1BB0}-\u{1BB9}\u{1C40}-\u{1C49}\u{1C50}-\u{1C59}\u{2070}\u{2074}-\u{2079}\u{2080}-\u{2089}\u{2150}-\u{2182}\u{2185}-\u{2189}\u{2460}-\u{249B}\u{24EA}-\u{24FF}\u{2776}-\u{2793}\u{2CFD}\u{3007}\u{3021}-\u{3029}\u{3038}-\u{303A}\u{3192}-\u{3195}\u{3220}-\u{3229}\u{3248}-\u{324F}\u{3251}-\u{325F}\u{3280}-\u{3289}\u{32B1}-\u{32BF}\u{A620}-\u{A629}\u{A6E6}-\u{A6EF}\u{A830}-\u{A835}\u{A8D0}-\u{A8D9}\u{A900}-\u{A909}\u{A9D0}-\u{A9D9}\u{A9F0}-\u{A9F9}\u{AA50}-\u{AA59}\u{ABF0}-\u{ABF9}\u{FF10}-\u{FF19}\u{10107}-\u{10133}\u{10140}-\u{10178}\u{1018A}-\u{1018B}\u{102E1}-\u{102FB}\u{10320}-\u{10323}\u{10341}\u{1034A}\u{103D1}-\u{103D5}\u{104A0}-\u{104A9}\u{10858}-\u{1085F}\u{10879}-\u{1087F}\u{108A7}-\u{108AF}\u{108FB}-\u{108FF}\u{10916}-\u{1091B}\u{109BC}-\u{109BD}\u{109C0}-\u{109CF}\u{109D2}-\u{109FF}\u{10A40}-\u{10A48}\u{10A7D}-\u{10A7E}\u{10A9D}-\u{10A9F}\u{10AEB}-\u{10AEF}\u{10B58}-\u{10B5F}\u{10B78}-\u{10B7F}\u{10BA9}-\u{10BAF}\u{10CFA}-\u{10CFF}\u{10D30}-\u{10D39}\u{10D40}-\u{10D49}\u{10E60}-\u{10E7E}\u{10F1D}-\u{10F26}\u{10F51}-\u{10F54}\u{10FC5}-\u{10FCB}\u{11052}-\u{1106F}\u{110F0}-\u{110F9}\u{11136}-\u{1113F}\u{111D0}-\u{111D9}\u{111E1}-\u{111F4}\u{112F0}-\u{112F9}\u{11450}-\u{11459}\u{114D0}-\u{114D9}\u{11650}-\u{11659}\u{116C0}-\u{116C9}\u{116D0}-\u{116E3}\u{11730}-\u{1173B}\u{118E0}-\u{118F2}\u{11950}-\u{11959}\u{11BF0}-\u{11BF9}\u{11C50}-\u{11C6C}\u{11D50}-\u{11D59}\u{11DA0}-\u{11DA9}\u{11F50}-\u{11F59}\u{11FC0}-\u{11FD4}\u{12400}-\u{1246E}\u{16130}-\u{16139}\u{16A60}-\u{16A69}\u{16AC0}-\u{16AC9}\u{16B50}-\u{16B59}\u{16B5B}-\u{16B61}\u{16D70}-\u{16D79}\u{16E80}-\u{16E96}\u{1CCF0}-\u{1CCF9}\u{1D2C0}-\u{1D2D3}\u{1D2E0}-\u{1D2F3}\u{1D360}-\u{1D378}\u{1D7CE}-\u{1D7FF}\u{1E140}-\u{1E149}\u{1E2F0}-\u{1E2F9}\u{1E4F0}-\u{1E4F9}\u{1E5F1}-\u{1E5FA}\u{1E8C7}-\u{1E8CF}\u{1E950}-\u{1E959}\u{1EC71}-\u{1ECAB}\u{1ECAD}-\u{1ECAF}\u{1ECB1}-\u{1ECB4}\u{1ED01}-\u{1ED2D}\u{1ED2F}-\u{1ED3D}\u{1F100}-\u{1F10C}\u{1FBF0}-\u{1FBF9}]/u;
  var NM_BAD = /[^\u{20}\u{27}-\u{29}\u{2C}-\u{2E}\u{41}-\u{5A}\u{61}-\u{7A}\u{C0}-\u{D6}\u{D8}-\u{F6}\u{F8}-\u{131}\u{134}-\u{13E}\u{141}-\u{148}\u{14A}-\u{17E}\u{18F}\u{1A0}-\u{1A1}\u{1AF}-\u{1B0}\u{1CD}-\u{1DC}\u{1DE}-\u{1E3}\u{1E6}-\u{1F0}\u{1F4}-\u{1F5}\u{1F8}-\u{21B}\u{21E}-\u{21F}\u{226}-\u{233}\u{259}\u{300}-\u{304}\u{306}-\u{30C}\u{30F}-\u{311}\u{313}-\u{314}\u{31B}\u{323}-\u{328}\u{32D}-\u{32E}\u{330}-\u{331}\u{335}\u{338}-\u{339}\u{342}\u{345}\u{37B}-\u{37D}\u{386}\u{388}-\u{38A}\u{38C}\u{38E}-\u{3A1}\u{3A3}-\u{3CE}\u{3FC}-\u{45F}\u{48A}-\u{4FF}\u{510}-\u{529}\u{52E}-\u{52F}\u{620}-\u{63F}\u{641}-\u{655}\u{670}-\u{672}\u{674}\u{679}-\u{68D}\u{68F}-\u{6A0}\u{6A2}-\u{6D3}\u{6D5}\u{6E5}-\u{6E6}\u{6EE}-\u{6EF}\u{6FA}-\u{6FC}\u{6FF}\u{750}-\u{77F}\u{870}-\u{887}\u{889}-\u{88E}\u{8A0}-\u{8AC}\u{8B2}\u{8B5}-\u{8C9}\u{1E00}-\u{1E99}\u{1E9E}\u{1EA0}-\u{1EF9}\u{1F00}-\u{1F15}\u{1F18}-\u{1F1D}\u{1F20}-\u{1F45}\u{1F48}-\u{1F4D}\u{1F50}-\u{1F57}\u{1F59}\u{1F5B}\u{1F5D}\u{1F5F}-\u{1F70}\u{1F72}\u{1F74}\u{1F76}\u{1F78}\u{1F7A}\u{1F7C}\u{1F80}-\u{1FB4}\u{1FB6}-\u{1FBA}\u{1FBC}\u{1FC2}-\u{1FC4}\u{1FC6}-\u{1FC8}\u{1FCA}\u{1FCC}\u{1FD0}-\u{1FD2}\u{1FD6}-\u{1FDA}\u{1FE0}-\u{1FE2}\u{1FE4}-\u{1FEA}\u{1FEC}\u{1FF2}-\u{1FF4}\u{1FF6}-\u{1FF8}\u{1FFA}\u{1FFC}\u{2019}\u{A67F}\u{A78D}\u{A792}-\u{A793}\u{A7AA}\u{A7C0}-\u{A7CA}\u{A7D0}-\u{A7D1}\u{A7D3}\u{A7D5}-\u{A7D9}\u{AB66}-\u{AB67}\u{1DF00}-\u{1DF1E}\u{1DF25}-\u{1DF2A}\u{1E08F}]/u;
  var NM_LET = /[\u{41}-\u{5A}\u{61}-\u{7A}\u{C0}-\u{D6}\u{D8}-\u{F6}\u{F8}-\u{131}\u{134}-\u{13E}\u{141}-\u{148}\u{14A}-\u{17E}\u{18F}\u{1A0}-\u{1A1}\u{1AF}-\u{1B0}\u{1CD}-\u{1DC}\u{1DE}-\u{1E3}\u{1E6}-\u{1F0}\u{1F4}-\u{1F5}\u{1F8}-\u{21B}\u{21E}-\u{21F}\u{226}-\u{233}\u{259}\u{37B}-\u{37D}\u{386}\u{388}-\u{38A}\u{38C}\u{38E}-\u{3A1}\u{3A3}-\u{3CE}\u{3FC}-\u{45F}\u{48A}-\u{4FF}\u{510}-\u{529}\u{52E}-\u{52F}\u{620}-\u{63F}\u{641}-\u{64A}\u{671}-\u{672}\u{674}\u{679}-\u{68D}\u{68F}-\u{6A0}\u{6A2}-\u{6D3}\u{6D5}\u{6E5}-\u{6E6}\u{6EE}-\u{6EF}\u{6FA}-\u{6FC}\u{6FF}\u{750}-\u{77F}\u{870}-\u{887}\u{889}-\u{88E}\u{8A0}-\u{8AC}\u{8B2}\u{8B5}-\u{8C9}\u{1E00}-\u{1E99}\u{1E9E}\u{1EA0}-\u{1EF9}\u{1F00}-\u{1F15}\u{1F18}-\u{1F1D}\u{1F20}-\u{1F45}\u{1F48}-\u{1F4D}\u{1F50}-\u{1F57}\u{1F59}\u{1F5B}\u{1F5D}\u{1F5F}-\u{1F70}\u{1F72}\u{1F74}\u{1F76}\u{1F78}\u{1F7A}\u{1F7C}\u{1F80}-\u{1FB4}\u{1FB6}-\u{1FBA}\u{1FBC}\u{1FC2}-\u{1FC4}\u{1FC6}-\u{1FC8}\u{1FCA}\u{1FCC}\u{1FD0}-\u{1FD2}\u{1FD6}-\u{1FDA}\u{1FE0}-\u{1FE2}\u{1FE4}-\u{1FEA}\u{1FEC}\u{1FF2}-\u{1FF4}\u{1FF6}-\u{1FF8}\u{1FFA}\u{1FFC}\u{A67F}\u{A78D}\u{A792}-\u{A793}\u{A7AA}\u{A7C0}-\u{A7CA}\u{A7D0}-\u{A7D1}\u{A7D3}\u{A7D5}-\u{A7D9}\u{AB66}-\u{AB67}\u{1DF00}-\u{1DF1E}\u{1DF25}-\u{1DF2A}]/u;
  var NM_WORD = /^[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*(?:[\u{41}-\u{5A}\u{61}-\u{7A}\u{C0}-\u{D6}\u{D8}-\u{F6}\u{F8}-\u{131}\u{134}-\u{13E}\u{141}-\u{148}\u{14A}-\u{17E}\u{18F}\u{1A0}-\u{1A1}\u{1AF}-\u{1B0}\u{1CD}-\u{1DC}\u{1DE}-\u{1E3}\u{1E6}-\u{1F0}\u{1F4}-\u{1F5}\u{1F8}-\u{21B}\u{21E}-\u{21F}\u{226}-\u{233}\u{259}\u{37B}-\u{37D}\u{386}\u{388}-\u{38A}\u{38C}\u{38E}-\u{3A1}\u{3A3}-\u{3CE}\u{3FC}-\u{45F}\u{48A}-\u{4FF}\u{510}-\u{529}\u{52E}-\u{52F}\u{620}-\u{63F}\u{641}-\u{64A}\u{671}-\u{672}\u{674}\u{679}-\u{68D}\u{68F}-\u{6A0}\u{6A2}-\u{6D3}\u{6D5}\u{6E5}-\u{6E6}\u{6EE}-\u{6EF}\u{6FA}-\u{6FC}\u{6FF}\u{750}-\u{77F}\u{870}-\u{887}\u{889}-\u{88E}\u{8A0}-\u{8AC}\u{8B2}\u{8B5}-\u{8C9}\u{1E00}-\u{1E99}\u{1E9E}\u{1EA0}-\u{1EF9}\u{1F00}-\u{1F15}\u{1F18}-\u{1F1D}\u{1F20}-\u{1F45}\u{1F48}-\u{1F4D}\u{1F50}-\u{1F57}\u{1F59}\u{1F5B}\u{1F5D}\u{1F5F}-\u{1F70}\u{1F72}\u{1F74}\u{1F76}\u{1F78}\u{1F7A}\u{1F7C}\u{1F80}-\u{1FB4}\u{1FB6}-\u{1FBA}\u{1FBC}\u{1FC2}-\u{1FC4}\u{1FC6}-\u{1FC8}\u{1FCA}\u{1FCC}\u{1FD0}-\u{1FD2}\u{1FD6}-\u{1FDA}\u{1FE0}-\u{1FE2}\u{1FE4}-\u{1FEA}\u{1FEC}\u{1FF2}-\u{1FF4}\u{1FF6}-\u{1FF8}\u{1FFA}\u{1FFC}\u{A67F}\u{A78D}\u{A792}-\u{A793}\u{A7AA}\u{A7C0}-\u{A7CA}\u{A7D0}-\u{A7D1}\u{A7D3}\u{A7D5}-\u{A7D9}\u{AB66}-\u{AB67}\u{1DF00}-\u{1DF1E}\u{1DF25}-\u{1DF2A}][\u{300}-\u{304}\u{306}-\u{30C}\u{30F}-\u{311}\u{313}-\u{314}\u{31B}\u{323}-\u{328}\u{32D}-\u{32E}\u{330}-\u{331}\u{335}\u{338}-\u{339}\u{342}\u{345}\u{64B}-\u{655}\u{670}\u{1E08F}]{0,3}[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*)+$/u;
  var NM_SCRIPTS = [['Latn', /^[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*(?:[\u{41}-\u{5A}\u{61}-\u{7A}\u{C0}-\u{D6}\u{D8}-\u{F6}\u{F8}-\u{131}\u{134}-\u{13E}\u{141}-\u{148}\u{14A}-\u{17E}\u{18F}\u{1A0}-\u{1A1}\u{1AF}-\u{1B0}\u{1CD}-\u{1DC}\u{1DE}-\u{1E3}\u{1E6}-\u{1F0}\u{1F4}-\u{1F5}\u{1F8}-\u{21B}\u{21E}-\u{21F}\u{226}-\u{233}\u{259}\u{1E00}-\u{1E99}\u{1E9E}\u{1EA0}-\u{1EF9}\u{A78D}\u{A792}-\u{A793}\u{A7AA}\u{A7C0}-\u{A7CA}\u{A7D0}-\u{A7D1}\u{A7D3}\u{A7D5}-\u{A7D9}\u{AB66}-\u{AB67}\u{1DF00}-\u{1DF1E}\u{1DF25}-\u{1DF2A}][\u{300}-\u{304}\u{306}-\u{30C}\u{30F}-\u{311}\u{313}-\u{314}\u{31B}\u{323}-\u{328}\u{32D}-\u{32E}\u{330}-\u{331}\u{335}\u{338}-\u{339}]{0,3}[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*)+$/u], ['Arab', /^[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*(?:[\u{620}-\u{63F}\u{641}-\u{64A}\u{671}-\u{672}\u{674}\u{679}-\u{68D}\u{68F}-\u{6A0}\u{6A2}-\u{6D3}\u{6D5}\u{6E5}-\u{6E6}\u{6EE}-\u{6EF}\u{6FA}-\u{6FC}\u{6FF}\u{750}-\u{77F}\u{870}-\u{887}\u{889}-\u{88E}\u{8A0}-\u{8AC}\u{8B2}\u{8B5}-\u{8C9}][\u{30F}\u{314}\u{31B}\u{326}-\u{328}\u{335}\u{338}-\u{339}\u{64B}-\u{655}\u{670}]{0,3}[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*)+$/u], ['Grek', /^[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*(?:[\u{37B}-\u{37D}\u{386}\u{388}-\u{38A}\u{38C}\u{38E}-\u{3A1}\u{3A3}-\u{3CE}\u{3FC}-\u{3FF}\u{1F00}-\u{1F15}\u{1F18}-\u{1F1D}\u{1F20}-\u{1F45}\u{1F48}-\u{1F4D}\u{1F50}-\u{1F57}\u{1F59}\u{1F5B}\u{1F5D}\u{1F5F}-\u{1F70}\u{1F72}\u{1F74}\u{1F76}\u{1F78}\u{1F7A}\u{1F7C}\u{1F80}-\u{1FB4}\u{1FB6}-\u{1FBA}\u{1FBC}\u{1FC2}-\u{1FC4}\u{1FC6}-\u{1FC8}\u{1FCA}\u{1FCC}\u{1FD0}-\u{1FD2}\u{1FD6}-\u{1FDA}\u{1FE0}-\u{1FE2}\u{1FE4}-\u{1FEA}\u{1FEC}\u{1FF2}-\u{1FF4}\u{1FF6}-\u{1FF8}\u{1FFA}\u{1FFC}][\u{300}-\u{301}\u{304}\u{306}\u{308}\u{30F}\u{313}-\u{314}\u{31B}\u{326}-\u{328}\u{335}\u{338}-\u{339}\u{342}\u{345}]{0,3}[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*)+$/u], ['Cyrl', /^[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*(?:[\u{400}-\u{45F}\u{48A}-\u{4FF}\u{510}-\u{529}\u{52E}-\u{52F}\u{A67F}][\u{300}-\u{302}\u{304}\u{306}\u{308}\u{30B}\u{30F}\u{311}\u{314}\u{31B}\u{326}-\u{328}\u{335}\u{338}-\u{339}\u{1E08F}]{0,3}[\u{27}\u{28}\u{29}\u{2C}\u{2D}\u{2E}\u{2019}]*)+$/u]];
  var NM_MSG = {"empty":"Name is required","long":"A name can be up to 120 characters","digit":"A name cannot contain numbers","char":"A name can only have letters, spaces and . - ' ’ ( ) , — remove “%s” (U+%s)","word":"Each word of a name needs a letter","mark":"An accent or vowel mark must sit on a letter (at most 3 on one letter)","script":"Write each word of a name in one alphabet (Latin or Arabic; Greek or Cyrillic only for the whole name)"};
  var NM_SKEL = (function (d) { var m = new Map(); d.split(',').forEach(function (e) { var p = e.split('='); m.set(String.fromCodePoint(parseInt(p[0], 16)), p[1] ? p[1].split('.').map(function (h) { return String.fromCodePoint(parseInt(h, 16)); }).join('') : ''); }); return m; })(
    '22=27.27,25=BA.2F.2080,30=6F,31=6C,41=61,42=62,43=63,44=64,45=65,46=66,47=67,48=68,49=6C,4A=6A,4B=6B,4C=6C,4D=72.6E,4E=6E,4F=6F,50=70,51=71,52=72,53=73,54=74,55=75,56=76,57=77,58=78,59=79,5A=7A,60=27,6D=72.6E,7C=6C,A2=63.338,A5=79.335,C6=61.65,D0=64.335,D7=78,D8=6F.338,DE=FE,E6=61.65,F0=2202.335,F8=6F.338,110=64.335,111=64.335,126=68.335,127=68.335,131=69,141=6C.338,142=6C.338,14A=14B,152=6F.65,153=6F.65,166=74.335,167=74.335,180=62.335,181=27.62,182=62.304,183=62.304,184=62,186=254,187=63.27,189=64.335,18A=27.64,18B=64.304,18C=64.304,18D=67,18E=1DD,18F=1DD,190=A793,191=66.326,192=66.326,193=67.27,194=79,196=6C,197=6C.335,198=6B.27,199=6B.314,19A=6C.335,19B=3BB.338,19C=77,19D=6E.326,19E=6E.329,19F=6F.335,1A2=1A3,1A4=27.70,1A5=70.314,1A6=72,1A7=32,1A9=283,1AC=27.74,1AD=74.314,1AE=74.328,1B1=28A,1B2=75,1B3=27.79,1B4=79.314,1B5=7A.335,1B6=7A.335,1B7=33,1B8=1B9,1BB=32.335,1BC=35,1BD=73,1BF=FE,1C0=6C,1C1=6C.6C,1C3=21,1E4=67.335,1E5=67.335,1F6=195,1F7=FE,21C=33,220=6E.329,222=38,223=38,224=7A.326,225=7A.326,23A=2C65,23B=63.338,23C=63.338,23D=6C.335,23E=74.338,241=3F,243=62.335,244=75.335,245=28C,246=65.338,247=65.338,248=6A.335,249=6A.335,24A=24B,24C=72.335,24D=72.335,24E=79.335,24F=79.335,251=61,253=62.314,256=64.328,257=64.314,259=1DD,25A=1DD.2DE,25B=A793,260=67.314,261=67,263=79,266=68.314,268=69.335,269=69,26A=69,26B=6C.334,26D=6C.328,26E=6C.21D,26F=77,271=72.6E.326,273=6E.328,275=6F.335,276=6F.1D07,27C=72.329,27D=72.328,282=73.328,28B=75,28F=79,290=7A.328,292=21D,294=3F,2A0=71.314,2A3=64.7A,2A4=64.21D,2A5=64.291,2A6=74.73,2A7=74.283,2A8=74.255,2A9=66.14B,2AA=6C.73,2AB=6C.7A,2B9=27,2BA=27.27,2BB=27,2BC=27,2BD=27,2BE=27,2BF=559,2C2=3C,2C3=3E,2C4=5E,2C6=5E,2C8=27,2CA=27,2CB=27,2D0=3A,2D3=559,2D7=2D,2EE=27.27,2F4=27,2F6=27.27,2F8=3A,2FB=2EA,305=304,30C=306,30D=,310=306.307,311=302,315=313,317=,320=331,321=326,322=328,327=326,336=335,337=338,339=326,342=303,345=328,347=333,357=350,358=307,366=30A,36E=306,370=2C76,372=373,375=2CF,376=1D0E,377=1D0E,37B=254,37D=A73F,37F=6A,391=61,392=62,393=79,394=1E9F,395=65,396=7A,397=68,398=6F.335,399=6C,39A=6B,39B=28C,39C=72.6E,39D=6E,39E=3BE,39F=6F,3A0=3C0,3A1=70,3A3=283,3A4=74,3A5=79,3A6=278,3A7=78,3A8=3C8,3A9=3C9,3B1=61,3B2=DF,3B3=79,3B4=1E9F,3B5=A793,3B7=6E.329,3B8=6F.335,3B9=69,3BA=138,3BD=76,3BF=6F,3C1=70,3C3=6F,3C4=1D1B,3C5=75,3C6=278,3CF=3D7,3D8=3D9,3DA=3C2,3DB=3C2,3DC=66,3DE=3DF,3E0=3E1,3E2=3E3,3E4=3E5,3E6=3E7,3E8=32,3E9=1A8,3EA=3EB,3EC=3ED,3EE=3EF,3F3=6A,3F7=FE,3F8=FE,3FA=72.6E,3FD=254,3FE=37C,3FF=A73F,402=452,404=A793,405=73,406=6C,408=6A,409=459,40A=45A,40B=68.335,40F=45F,410=61,411=62.304,412=62,413=79,414=434,415=65,416=436,417=33,418=1D0E,41A=6B,41B=28C,41C=72.6E,41D=68,41E=6F,41F=3C0,420=70,421=63,422=74,423=79,424=278,425=78,426=446,427=447,428=448,429=449,42A=2C9.62,42B=62.6C,42C=62,42D=44D,42E=6C.6F,42F=1D19,430=61,431=36,432=299,433=72,435=65,437=25C,438=1D0E,43A=138,43C=28D,43D=29C,43E=6F,43F=3C0,440=70,441=63,442=1D1B,443=79,444=278,445=78,44A=2C9.62,44B=185.69,44C=185,44F=1D19,454=A793,455=73,456=69,458=6A,45B=68.335,460=77,461=77,462=62.335,463=62.335,464=465,466=467,468=469,46A=46B,46C=46D,46E=46F,470=3C8,471=3C8,472=6F.335,473=6F.335,474=76,475=76,478=479,47A=47B,47C=77.486.487,47D=77.486.487,47E=47F,480=481,48A=1D0E.326.300,48B=1D0E.326.306,48C=62.335,48D=62.335,48E=48F,490=79.27,491=72.27,492=79.335,493=72.335,494=495,496=436.329,497=436.329,498=33.326,499=25C.326,49A=6B.329,49B=138.329,49C=49D,49E=6B.335,49F=138.335,4A0=4A1,4A2=68.329,4A3=29C.329,4A4=4A5,4A6=4A7,4A8=4A9,4AA=63.326,4AB=63.326,4AC=74.329,4AD=1D1B.329,4AE=79,4AF=79,4B0=79.335,4B1=79.335,4B2=78.329,4B4=4B5,4B6=4B7,4B8=4B9,4BA=68,4BB=68,4BC=65,4BD=65,4BE=65.328,4BF=65.328,4C0=6C,4C3=4C4,4C5=28C.326,4C6=43B.326,4C7=68.326,4C8=29C.326,4C9=68.326,4CA=29C.326,4CB=4B7,4CC=4B7,4CD=72.6E.326,4CE=28D.326,4CF=69,4D4=61.65,4D5=61.65,4D8=1DD,4D9=1DD,4E0=33,4E1=21D,4E8=6F.335,4E9=6F.335,4F6=4F7,4FA=4FB,4FC=4FD,4FE=4FF,500=64,501=64,502=503,504=505,506=507,508=509,50A=195,50C=67,50D=262,50E=50F,510=A793,511=A793,512=513,514=515,516=517,518=519,51A=71,51B=71,51C=77,51D=77,51E=51F,520=521,522=523,524=525,526=527,528=529,52A=52B,52C=52D,52E=52F,531=77,532=562,533=71,534=564,535=565,536=71,537=567,538=568,539=569,53A=56A,53B=12AE,53C=56C,53D=56D,53E=1E9F,53F=56F,540=68,541=571,542=572,543=573,544=1206,545=237,546=576,547=577,548=6E,549=579,54A=1323,54B=57B,54C=1261,54D=75,54E=57E,54F=73,550=580,551=67,552=582,553=278,554=66,555=6F,556=586,55A=27,55D=27,561=77,563=71,566=71,56E=1E9F,570=68,575=237,578=6E,57A=270,57C=6E,57D=75,581=67,584=66,585=6F,589=3A,59C=301,59D=301,5A4=59A,5A8=599,5AD=596,5AE=598,5AF=30A,5B4=323,5B9=307,5BA=307,5C0=6C,5C1=307,5C2=307,5C3=3A,5C4=307,5C5=323,5D5=6C,5D8=76,5D9=27,5DF=6C,5E1=6F,5F0=6C.6C,5F1=6C.27,5F2=27.27,5F3=27,5F4=27.27,609=BA.2F.2080.2080,60A=BA.2F.2080.2080.2080,60D=2C,60F=639,618=301,619=313,61A=,627=6C,62B=649.6DB,634=633.6DB,63D=649.302,63F=649.6DB,647=6F,64A=649,64B=,64C=,64D=,64E=,64F=,650=,651=,652=,653=303,656=329,657=312,658=306,659=304,65A=306,65B=302,65C=323,65D=314,65F=655,660=2E,661=6C,665=6F,667=76,668=28C,66A=BA.2F.2080,66B=2C,66C=60C,66D=2A,66E=649,66F=6A1,670=,672=6C.674,673=6C.655,679=649.615,67E=649.6DB,681=62D.654,685=62D.6DB,688=62F.615,68B=68A.615,68E=62F.6DB,691=631.615,692=631.306,698=631.6DB,69E=635.6DB,69F=637.6DB,6A4=6A1.6DB,6A7=641,6A8=6A1.6DB,6A9=643,6AA=643,6AD=643.6DB,6B4=6AF.6DB,6B5=644.306,6B7=644.6DB,6BA=649,6BB=649.615,6BD=649.6DB,6BE=6F,6C1=6F,6C3=629,6C6=648.306,6C7=648.313,6C8=648,6C9=648.302,6CB=648.6DB,6CC=649,6CE=649.306,6D0=67B,6D1=649.6DB,6D2=649,6D4=2D,6D5=6F,6DF=30A,6E8=306.307,6EC=307,6EE=62F.302,6EF=631.302,6F0=2E,6F1=6C,6F2=662,6F3=663,6F4=664,6F5=6F,6F6=666,6F7=76,6F8=28C,6F9=669,6FD=621.348,6FE=645.348,6FF=6F.302,701=2E,702=2E,703=3A,704=3A,740=307,741=307,742=73C,747=301,751=628.6DB,756=649.306,762=6AC,763=643.6DB,767=754,768=646.615,769=646.306,76C=631.654,771=697.615,772=62D.654,77E=633.302,7C0=6F,7CA=6C,7EB=304,7ED=307,7EE=302,7F3=308,7F4=27,7F5=27,7FA=5F,8A1=628.654,8A4=6A2.6DB,8A7=645.6DB,8A8=649.654,8A9=754,8AE=62F.324.323,8AF=635.324.323,8B0=6AF,8B1=648,8B2=632.302,8B6=628.6E2,8B7=649.6DB.6E2,8B9=631.306.307,8BA=649.306.307,8BB=6A1,8BC=6A1,8BD=649,8E5=,8E8=,8EA=307,8EB=308,8ED=323,8EE=324,8F0=30B,8F1=,8F2=,8F3=313,8F8=350,8F9=354,8FA=355,8FF=350,900=352,901=306.307,902=307,903=3A,904=905.946,906=905.93E,908=930.94D.907,90D=90F.945,90E=90F.946,910=90F.947,911=905.949,912=905.93E.946,913=905.93E.947,914=905.93E.948,93C=323,952=331,953=300,954=301,965=964.964,966=6F,967=669,97D=3F,981=306.307,986=985.9BE,9BC=323,9E0=98B.9C3,9E1=98B.9C3,9E6=6F,9EA=38,9ED=39,A02=307,A03=983,A06=A05.A3E,A07=A72.A3F,A08=A72.A40,A09=A73.A41,A0A=A73.A42,A0F=A72.A47,A10=A05.A48,A14=A05.A4C,A3C=323,A4B=946,A4D=94D,A66=6F,A67=39,A6A=38,A81=306.307,A82=307,A83=3A,A86=A85.ABE,A8D=A85.AC5,A8F=A85.AC7,A90=A85.AC8,A91=A85.ABE.AC5,A93=A85.ABE.AC7,A94=A85.ABE.AC8,ABC=323,ABD=93D,AC1=941,AC2=942,ACD=94D,AE6=6F,AE8=968,AE9=969,AEA=96A,AEE=96E,AF0=970,B01=306.307,B03=38,B06=B05.B3E,B20=6F,B3C=323,B66=6F,B68=39,B82=30A,B8A=B89.BB3,B9C=B90,BB0=B88,BBE=B88,BC8=BA9,BCD=307,BD7=BB3,BE6=6F,BE7=B95,BE8=B89,BEA=B9A,BEB=B88.BC1,BEC=B9A.BC1,BED=B8E,BEE=B85,BF0=BAF,BF2=B9A.BC2,BF4=BAE.BC0,BF5=BF3,BF7=B8E.BB5,BF8=BB7,BFA=BA8.BC0,C00=306.307,C02=6F,C03=983,C13=C12.C55,C14=C12.C4C,C20=C30.5BC,C22=C21.323,C25=C27.5BC,C2D=C2C.323,C2E=C35.C41,C37=C35.323,C39=C35.C3E,C42=C41.C3E,C44=C43.C3E,C60=C0B.C3E,C61=C0C.C3E,C66=6F,C81=306.307,C82=6F,C83=983,C85=C05,C86=C06,C87=C07,C92=C12,C93=C12.C55,C94=C12.C4C,C9C=C1C,C9E=C1E,CA3=C23,CAF=C2F,CB1=C31,CB2=C32,CE1=C8C.CBE,CE6=6F,CE7=C67,CE8=C68,CEF=C6F,D01=306.307,D02=6F,D03=983,D08=D07.D57,D09=B89,D0A=B89.D57,D0C=D28.D41,D10=D0E.D46,D13=D12.D3E,D14=D12.D57,D19=D28.D41,D1C=B90,D20=6F,D23=BA3,D31=D30,D34=BB4,D36=BB6,D3A=B9F.BBF,D3F=BBF,D40=BBF,D42=D41,D43=D41,D48=D46.D46,D4E=971,D5A=D28.D4D.D2E,D5F=6F.D30.6F,D61=D1E,D66=6F,D6A=D30.D4D,D6B=D26.D4D.D30,D6C=D28.D4D.D28,D6D=39,D6E=D35.D4D.D30,D6F=D28.D4D,D76=D39.D4D.D2E,D79=D28.D41,D7B=D28.D4D,D7C=D30.D4D,D82=6F,D83=983,DE9=DE8.DCF,DEA=DA2,DEB=DAF,DEF=DE8.DD3,E03=E02,E0B=E0A,E0F=E0E,E14=E04,E15=E04,E17=E11,E21=E06,E26=E20,E41=E40.E40,E45=E32,E4D=30A,E50=6F,E88=E08,E8D=E22,E9A=E1A,E9B=E1B,E9D=E1D,E9E=E1E,E9F=E1F,EB8=E38,EB9=E39,EC8=E48,EC9=E49,ECA=E4A,ECB=E4B,ECD=30A,ED0=6F,F00=F68.F7C.F7E,F02=F60.F74.F82.F7F,F03=F60.F74.F82.F14,F0E=F0D.F0D,F1B=F1A.F1A,F1E=F1D.F1D,F1F=F1A.F1D,F37=325,F6A=F62,FCE=F1D.F1A,FD5=5350,FD6=534D,1000=1002.102C,1010=6F.102C,101D=6F,101F=1015.102C,1029=101E.103C,102A=101E.103C.1031.102C.103A,1036=30A,1038=983,1040=6F,104B=104A.104A,1065=1041,1066=1015.103E,106F=1015.102C.103E,1070=1003.103E,107E=107D.103E,1081=1002.103E,109E=1083.30A,10A0=A787,10A1=2D01,10A2=2D02,10A3=2D03,10A4=2D04,10A5=2D05,10A6=2D06,10A7=2D07,10A8=2D08,10A9=2D09,10AA=2D0A,10AB=2D0B,10AC=2D0C,10AD=2D0D,10AE=2D0E,10AF=2D0F,10B0=2D10,10B1=2D11,10B2=2D12,10B3=2D13,10B4=2D14,10B5=2D15,10B6=2D16,10B7=2D17,10B8=2D18,10B9=2D19,10BA=2D1A,10BB=2D1B,10BC=2D1C,10BD=2D1D,10BE=2D1E,10BF=2D1F,10C0=2D20,10C1=2D21,10C2=2D22,10C3=2D23,10C4=2D24,10C5=2D25,10C7=2D27,10CD=2D2D,10E7=79,10F3=21D,10FF=6F,1101=1100.1100,1104=1103.1103,1108=1107.1107,110A=1109.1109,110D=110C.110C,1113=1102.1100,1114=1102.1102,1115=1102.1103,1116=1102.1107,1117=1103.1100,1118=1105.1102,1119=1105.1105,111A=1105.1112,111B=1105.110B,111C=1106.1107,111D=1106.110B,111E=1107.1100,111F=1107.1102,1120=1107.1103,1121=1107.1109,1122=1107.1109.1100,1123=1107.1109.1103,1124=1107.1109.1107,1125=1107.1109.1109,1126=1107.1109.110C,1127=1107.110C,1128=1107.110E,1129=1107.1110,112A=1107.1111,112B=1107.110B,112C=1107.1107.110B,112D=1109.1100,112E=1109.1102,112F=1109.1103,1130=1109.1105,1131=1109.1106,1132=1109.1107,1133=1109.1107.1100,1134=1109.1109.1109,1135=1109.110B,1136=1109.110C,1137=1109.110E,1138=1109.110F,1139=1109.1110,113A=1109.1111,113B=1105.1112,113D=113C.113C,113F=113E.113E,1141=110B.1100,1142=110B.1103,1143=110B.1106,1144=110B.1107,1145=110B.1109,1146=110B.1140,1147=110B.110B,1148=110B.110C,1149=110B.110E,114A=110B.1110,114B=110B.1111,114D=110C.110B,114F=114E.114E,1151=1150.1150,1152=110E.110F,1153=110E.1112,1156=1111.1107,1157=1111.110B,1158=1112.1112,115A=1100.1103,115B=1102.1109,115C=1102.110C,115D=1102.1112,115E=1103.1105,1162=1161.4E28,1164=1163.4E28,1166=1165.4E28,1168=1167.4E28,116A=1169.1161,116B=1169.1161.4E28,116C=1169.4E28,116F=116E.1165,1170=116E.1165.4E28,1171=116E.4E28,1173=30FC,1174=30FC.4E28,1175=4E28,1176=1161.1169,1177=1161.116E,1178=1163.1169,1179=1163.116D,117A=1165.1169,117B=1165.116E,117C=1165.30FC,117D=1167.1169,117E=1167.116E,117F=1169.1165,1180=1169.1165.4E28,1181=1169.1167.4E28,1182=1169.1169,1183=1169.116E,1184=116D.1163,1185=116D.1163.4E28,1186=116D.1163,1187=116D.1169,1188=116D.4E28,1189=116E.1161,118A=116E.1161.4E28,118B=116E.1165.30FC,118C=116E.1167.4E28,118D=116E.116E,118E=1172.1161,118F=1172.1165,1190=1172.1165.4E28,1191=1172.1167,1192=1172.1167.4E28,1193=1172.116E,1194=1172.4E28,1195=30FC.116E,1196=30FC.30FC,1197=30FC.4E28.116E,1198=4E28.1161,1199=4E28.1163,119A=4E28.1169,119B=4E28.116E,119C=4E28.30FC,119D=4E28.119E,119F=119E.1165,11A0=119E.116E,11A1=119E.4E28,11A2=119E.119E,11A3=1161.30FC,11A4=1163.116E,11A5=1167.1163,11A6=1169.1163,11A7=1169.1163.4E28,11A8=1100,11A9=1100.1100,11AA=1100.1109,11AB=1102,11AC=1102.110C,11AD=1102.1112,11AE=1103,11AF=1105,11B0=1105.1100,11B1=1105.1106,11B2=1105.1107,11B3=1105.1109,11B4=1105.1110,11B5=1105.1111,11B6=1105.1112,11B7=1106,11B8=1107,11B9=1107.1109,11BA=1109,11BB=1109.1109,11BC=110B,11BD=110C,11BE=110E,11BF=110F,11C0=1110,11C1=1111,11C2=1112,11C3=1100.1105,11C4=1100.1109.1100,11C5=1102.1100,11C6=1102.1103,11C7=1102.1109,11C8=1102.1140,11C9=1102.1110,11CA=1103.1100,11CB=1103.1105,11CC=1105.1100.1109,11CD=1105.1102,11CE=1105.1103,11CF=1105.1103.1112,11D0=1105.1105,11D1=1105.1106.1100,11D2=1105.1106.1109,11D3=1105.1107.1109,11D4=1105.1107.1112,11D5=1105.1107.110B,11D6=1105.1109.1109,11D7=1105.1140,11D8=1105.110F,11D9=1105.1159,11DA=1106.1100,11DB=1106.1105,11DC=1106.1107,11DD=1106.1109,11DE=1106.1109.1109,11DF=1106.1140,11E0=1106.110E,11E1=1106.1112,11E2=1106.110B,11E3=1107.1105,11E4=1107.1111,11E5=1107.1112,11E6=1107.110B,11E7=1109.1100,11E8=1109.1103,11E9=1109.1105,11EA=1109.1107,11EB=1140,11EC=110B.1100,11ED=110B.1100.1100,11EE=110B.110B,11EF=110B.110F,11F0=114C,11F1=110B.1109,11F2=110B.1140,11F3=1111.1107,11F4=1111.110B,11F5=1112.1102,11F6=1112.1105,11F7=1112.1106,11F8=1112.1107,11F9=1159,11FA=1100.1102,11FB=1100.1107,11FC=1100.110E,11FD=1100.110F,11FE=1100.1112,11FF=1102.1102,1200=75,1223=270,1240=278,1260=6E,1294=571,12D0=6F,13A0=64,13A1=72,13A2=74,13A3=AB73,13A4=6F.27,13A5=69,13A6=AB76,13A7=AB77,13A8=2C76,13A9=79,13AA=61,13AB=6A,13AC=65,13AD=AB7D,13AE=3F,13AF=AB7F,13B0=2C76,13B1=79,13B2=AB82,13B3=77,13B4=AB84,13B5=AB85,13B6=AB86,13B7=72.6E,13B8=AB88,13B9=AB89,13BA=AB8A,13BB=68,13BC=AB8C,13BD=79,13BE=6F.335,13BF=1AB,13C0=67,13C1=AB91,13C2=68,13C3=7A,13C4=AB94,13C5=AB95,13C6=AB96,13C7=77,13C8=AB98,13C9=AB99,13CA=AB9A,13CB=A793,13CC=75.335,13CD=AB9D,13CE=34,13CF=62,13D0=ABA0,13D1=ABA1,13D2=72,13D3=ABA3,13D4=77,13D5=73,13D6=ABA6,13D7=ABA7,13D8=ABA8,13D9=76,13DA=73,13DB=ABAB,13DC=ABAC,13DD=ABAD,13DE=6C,13DF=63,13E0=ABB0,13E1=ABB1,13E2=70,13E3=ABB3,13E4=ABB4,13E5=ABB5,13E6=6B,13E7=64,13E8=ABB8,13E9=ABB9,13EA=ABBA,13EB=6F.335,13EC=ABBC,13ED=ABBD,13EE=36,13EF=ABBF,13F0=DF,13F1=13F9,13F2=68.314,13F3=67,13F4=62,13F5=13FD,13FB=262,13FC=299,1400=3D,1403=1E9F,140C=B7.1401,140D=1401.B7,140E=B7.1E9F,140F=1E9F.B7,1410=B7.1404,1411=1404.B7,1412=B7.1405,1413=1405.B7,1414=B7.1406,1415=1406.B7,1417=B7.140A,1418=140A.B7,1419=B7.140B,141A=140B.B7,1427=B7,142B=1401.1420,142C=1E9F.1420,142D=1405.1420,142E=140A.1420,142F=76,1431=28C,1433=3E,1437=B7.3E,1438=3C,143A=B7.76,143B=76.B7,143C=B7.28C,143D=28C.B7,143E=B7.1432,143F=1432.B7,1440=B7.3E,1441=3E.B7,1442=B7.1434,1443=1434.B7,1444=B7.3C,1445=3C.B7,1446=B7.1439,1447=1439.B7,144A=27,144C=75,144E=6E,1454=B7.1450,1457=B7.75,1458=75.B7,1459=B7.6E,145A=6E.B7,145B=B7.144F,145C=144F.B7,145D=B7.1450,145E=1450.B7,145F=B7.1451,1460=1451.B7,1461=B7.1455,1462=1455.B7,1463=B7.1456,1464=1456.B7,1467=75.27,1468=6E.27,1469=1450.27,146A=1455.27,146D=70,146F=64,1472=62,1473=62.307,1474=B7.146B,1475=146B.B7,1476=B7.70,1477=70.B7,1478=B7.146E,1479=146E.B7,147A=B7.64,147B=64.B7,147C=B7.1470,147D=1470.B7,147E=B7.62,147F=62.B7,1480=B7.62.307,1481=62.307.B7,1485=146B.27,1486=70.27,1487=64.27,1488=62.27,148D=6A,1492=B7.1489,1493=1489.B7,1494=B7.148B,1495=148B.B7,1496=B7.148C,1497=148C.B7,1498=B7.6A,1499=6A.B7,149A=B7.148E,149B=148E.B7,149C=B7.1490,149D=1490.B7,149E=B7.1491,149F=1491.B7,14A5=79,14AA=6C,14AC=B7.14A3,14AD=14A3.B7,14AE=B7.79,14AF=79.B7,14B0=B7.14A6,14B1=14A6.B7,14B2=B7.14A7,14B3=14A7.B7,14B4=B7.14A8,14B5=14A8.B7,14B6=B7.6C,14B7=6C.B7,14B8=B7.14AB,14B9=14AB.B7,14BF=32,14C9=B7.14C0,14CA=14C0.B7,14CB=B7.14C7,14CC=14C7.B7,14CD=B7.14C8,14CE=14C8.B7,14D1=1421,14DC=B7.14D3,14DD=14D3.B7,14DE=B7.14D5,14DF=14D5.B7,14E0=B7.14D6,14E1=14D6.B7,14E2=B7.14D7,14E3=14D7.B7,14E4=B7.14D8,14E5=14D8.B7,14E6=B7.14DA,14E7=14DA.B7,14E8=B7.14DB,14E9=14DB.B7,14F6=B7.14ED,14F7=14ED.B7,14F8=B7.14EF,14F9=14EF.B7,14FA=B7.14F0,14FB=14F0.B7,14FC=B7.14F1,14FD=14F1.B7,14FE=B7.14F2,14FF=14F2.B7,1500=B7.14F4,1501=14F4.B7,1502=B7.14F5,1503=14F5.B7,150C=150B.3C,150D=150B.1455,150E=150B.62,150F=150B.1490,1517=B7.1510,1518=1510.B7,1519=B7.1511,151A=1511.B7,151B=B7.1512,151C=1512.B7,151D=B7.1513,151E=1513.B7,151F=B7.1514,1520=1514.B7,1521=B7.1515,1522=1515.B7,1523=B7.1516,1524=1516.B7,152F=B7.34,1530=34.B7,1531=B7.1528,1532=1528.B7,1533=B7.1529,1534=1529.B7,1535=B7.152A,1536=152A.B7,1537=B7.152B,1538=152B.B7,1539=B7.152D,153A=152D.B7,153B=B7.152E,153C=152E.B7,1540=1429,1541=78,154E=B7.154C,154F=154C.B7,155B=B7.155A,155C=155A.B7,1568=B7.1567,1569=1567.B7,1577=1E9F,157C=68,157D=78,157E=1550.146C,157F=1550.70,1580=1550.146E,1581=1550.64,1582=1550.1470,1583=1550.62,1584=1550.62.307,1585=1550.1483,1587=72,158E=1595.148A,158F=1595.148B,1590=1595.148C,1591=1595.6A,1592=1595.148E,1593=1595.1490,1594=1595.1491,15AF=62,15B4=66,15B5=214E,15B7=A7FB,15C4=250,15C5=61,15DE=64,15EA=64,15EF=77,15F0=72.6E,15F7=62,1602=1490,1603=1489,1604=14D3,1607=14DA,1622=1543,1623=1546,1624=154A,162E=28A,162F=3C9,1634=28A,1635=3C9,166D=78,166E=78,166F=1550.146B,1670=1595.1489,1671=1596.148B,1672=1596.148C,1673=1596.6A,1674=1596.148E,1675=1596.1490,1676=1596.1491,1677=15A7.B7,1678=15A8.B7,1679=15A9.B7,167A=15AA.B7,167B=15AB.B7,167C=15AC.B7,167D=15AD.B7,1680=20,16B2=3C,16B7=78,16C1=6C,16C2=16BD,16CC=27,16D5=6B,16D6=72.6E,16D8=3C8,16E1=16BC,16EB=B7,16EC=3A,16ED=2B,16F0=278,1734=1715,1735=2F,17A3=17A2,17B7=E34,17B8=E35,17B9=E36,17BA=E37,17C6=30A,17CB=E48,17D3=30A,17D4=E2F,17D5=E5A,17D9=E4F,17DA=E5B,1803=3A,1809=3A,1855=1835,1896=185C,18B3=B7.18B1,18B6=B7.18B4,18B9=B7.18B8,18C2=B7.18C0,18C6=B7.14C2,18C7=14C2.B7,18C8=B7.14C3,18C9=14C3.B7,18CA=B7.14C4,18CB=14C4.B7,18CC=B7.14C5,18CD=14C5.B7,18CE=B7.1543,18CF=B7.1546,18D0=B7.1547,18D1=B7.1548,18D2=B7.1549,18D3=B7.154B,18DB=18F5,18DC=18DF.141E,18DD=141E.18DF,18E0=1543.B7,18E3=155E.B7,18E4=1566.B7,18E5=156B.B7,18E8=1586.B7,18EA=1597.B7,18ED=77.B7,18F0=15F4.B7,18F2=161B.B7,19D0=199E,19D1=19B1,1A80=1A45,1A90=1A45,1AA9=1AA8.1AA8,1AAB=1AAA.1AA8,1AB4=6DB,1AB7=328,1B52=1B0D,1B53=1B11,1B58=1B28,1B5C=1B50,1B5F=1B5E.1B5E,1C3C=1C3B.1C3B,1C7F=1C7E.1C7E,1C89=1C8A,1C90=10D0,1C91=10D1,1C92=10D2,1C93=10D3,1C94=10D4,1C95=10D5,1C96=10D6,1C97=10D7,1C98=10D8,1C99=10D9,1C9A=10DA,1C9B=10DB,1C9C=10DC,1C9D=10DD,1C9E=10DE,1C9F=10DF,1CA0=10E0,1CA1=10E1,1CA2=10E2,1CA3=10E3,1CA4=10E4,1CA5=10E5,1CA6=10E6,1CA7=79,1CA8=10E8,1CA9=10E9,1CAA=10EA,1CAB=10EB,1CAC=10EC,1CAD=10ED,1CAE=10EE,1CAF=10EF,1CB0=10F0,1CB1=10F1,1CB2=10F2,1CB3=21D,1CB4=10F4,1CB5=10F5,1CB6=10F6,1CB7=10F7,1CB8=10F8,1CB9=10F9,1CBA=10FA,1CBD=10FD,1CBE=10FE,1CBF=6F,1CD0=302,1CD2=304,1CD3=27.27,1CD5=32B,1CD8=32E,1CD9=32D,1CDA=30E,1CDC=329,1CDD=323,1CDE=324,1CED=316,1D04=63,1D08=25C,1D0B=138,1D0D=28D,1D0F=6F,1D10=254,1D11=6F,1D14=1DD.6F,1D1C=75,1D20=76,1D21=77,1D22=7A,1D24=1A8,1D26=72,1D27=28C,1D28=3C0,1D29=1D18,1D2B=43B,1D6B=75.65,1D6E=66.334,1D6F=72.6E.334,1D70=6E.334,1D72=72.334,1D73=27E.334,1D74=73.334,1D75=74.334,1D76=7A.334,1D7B=69.335,1D7C=69.335,1D7D=70.335,1D7E=75.335,1D7F=28A.335,1D83=67,1D8C=79,1D90=24B,1DEE=2DEC,1E9D=66,1E9E=DF,1EFA=1EFB,1EFC=1EFD,1EFE=79,1EFF=79,2010=2D,2012=2D,2013=2D,2014=30FC,2015=30FC,2016=6C.6C,2018=27,2019=27,201A=2C,201B=27,201C=27.27,201D=27.27,201F=27.27,2022=B7,2027=B7,2028=20,2029=20,2030=BA.2F.2080.2080,2031=BA.2F.2080.2080.2080,2032=27,2035=27,2039=3C,203A=3E,2041=2F,2043=2D,2044=2F,204E=2A,2052=BA.2F.2080,2053=7E,205A=3A,205D=2D57,205E=2D42,20A1=63.20EB,20A4=A3,20A5=72.6E.338,20A9=77.335,20AB=64.335.331,20AC=A793,20AD=6B.335,20AE=74.20EB,20B6=6C.74,20BD=66,20DB=6DB,2108=44D,2127=28A,2129=27F,212E=65,2132=214E,2141=A4E8,2142=A4F6,2143=16F00,2183=254,2184=254,2191=16CF,2195=16E8,21B5=21B2,21BA=1F10E,21BE=16DA,21BF=16D0,2200=250,2203=1DD,2206=1E9F,220F=3C0,2211=283,2212=2D,2214=2B.307,2215=2F,2216=5C,2217=2A,2218=B0,2219=B7,221E=6F.6F,2223=6C,2225=6C.6C,2228=76,2229=6E,222A=75,222B=283,2236=3A,2238=2D.307,223C=7E,2250=3D.307,2251=3D.323.307,2257=3D.30A,2259=3D.302,225A=3D.306,225E=3D.36B,2263=2261,226A=3C.3C,226B=3E.3E,2282=1455,2283=1450,2295=102A8,2296=6F.335,2299=298,229D=6F.335,22A4=74,22A5=A4D5,22C0=2227,22C1=76,22C2=6E,22C3=75,22C4=16DC,22C5=B7,22C8=16DE,22D6=3C.B7,22D7=B7.3E,22D8=3C.3C.3C,22D9=3E.3E.3E,22EE=2D57,22EF=B7.B7.B7,22F4=A793,22FF=65,2300=2205,2325=2324,2341=303C,2359=1E9F.332,235A=16DC.332,235C=B0.332,235F=229B,2361=74.308,2362=2207.308,2363=22C6.308,2364=B0.308,2365=629,2368=7E.308,2369=1435,236B=2207.334,236C=6F.335,2373=69,2374=70,2375=3C9,2376=61.332,2377=A793.332,2378=69.332,2379=3C9.332,237A=61,237F=16BD,239C=4E28,239F=4E28,23A2=4E28,23A5=4E28,23AA=4E28,23AE=4E28,23C1=2355,23C2=234E,23C3=234B,23C6=236D,23E8=2081.2080,23FC=23FB,23FD=6C,23FE=263E,244A=5C.5C,2500=30FC,2501=30FC,2503=2502,250F=250C,2523=251C,2571=2F,2573=78,2588=220E,2590=258C,2594=2C9,2597=2596,259D=2598,25A0=220E,25B1=23E5,25B3=1E9F,25B7=22B3,25B8=25B6,25BA=25B6,25BD=102BC,25C1=22B2,25C7=16DC,25CA=16DC,25CB=B0,25CE=233E,25E0=2312,25E6=B0,2609=298,2610=25A1,2625=1099E,2630=2CB7,2638=2388,264E=224F,2662=16DC,2669=1D158.1D165,266A=1D158.1D165.1D16E,26AC=970,2768=28,2769=29,276E=3C,276F=3E,2772=28,2773=29,2774=7B,2775=7D,2795=2B,2796=2D,2797=F7,27C2=A4D5,27C8=5C.1455,27C9=1450.2F,27CB=2F,27CD=5C,27D9=74,27E8=276C,27E9=276D,292B=78,292C=78,2963=16D0.16DA,2965=21C3.21C2,296E=16D0.21C2,296F=21C3.16DA,2999=2D42,29B0=2349,29BE=233E,29C4=303C,29C5=2342,29C7=233B,29D6=102C0,29D9=299A,29F4=3A.2192,29F5=5C,29F6=2F.304,29F8=2F,29F9=5C,2A00=298,2A01=102A8,2A02=2297,2A03=228D,2A04=228E,2A05=2293,2A06=2294,2A1D=16DE,2A20=3E.3E,2A21=16DA,2A22=2B.30A,2A23=2B.302,2A24=2B.303,2A25=2B.323,2A26=2B.330,2A27=2B.2082,2A29=2D.313,2A2A=2D.323,2A2F=78,2A30=78.307,2A3D=2319,2A3E=2A1F,2A3F=2210,2A6A=7E.307,2A6E=3D.20F0,2AA5=3E.3C,2AAA=15D5,2AAB=15D2,2AD7=1450.1455,2AFB=2F.2F.2F,2AFD=2F.2F,2BEC=219E,2BED=219F,2BEE=21A0,2BEF=21A1,2C00=2C30,2C01=2C31,2C02=2C32,2C03=2C33,2C04=2C34,2C05=2C35,2C06=2C36,2C07=2C37,2C08=2C38,2C09=2C39,2C0A=2C3A,2C0B=2C3B,2C0C=2C3C,2C0D=2C3D,2C0E=2C3E,2C0F=2C3F,2C10=2C40,2C11=2C41,2C12=2C42,2C13=2C43,2C14=2C44,2C15=2C45,2C16=2C46,2C17=2C47,2C18=2C48,2C19=2C49,2C1A=2C4A,2C1B=2C4B,2C1C=2C4C,2C1D=2C4D,2C1E=2C4E,2C1F=2C4F,2C20=2C50,2C21=2C51,2C22=2C52,2C23=2C53,2C24=2C54,2C25=2C55,2C26=2C56,2C27=2C57,2C28=2C58,2C29=2C59,2C2A=2C5A,2C2B=2C5B,2C2C=2C5C,2C2D=2C5D,2C2E=2C5E,2C2F=2C5F,2C60=2C61,2C62=6C.334,2C63=70.335,2C64=72.328,2C67=68.329,2C69=6B.329,2C6B=2C6C,2C6D=61,2C6E=72.6E.326,2C6F=250,2C70=252,2C72=2C73,2C75=2C76,2C7E=23F,2C7F=240,2C80=2C81,2C82=2C83,2C84=79,2C85=72,2C86=1E9F,2C88=A793,2C89=A793,2C8A=2C8B,2C8C=2C8D,2C8E=68,2C90=2C91,2C92=6C,2C94=6B,2C95=138,2C96=3BB,2C98=72.6E,2C9A=6E,2C9C=2C9D,2C9E=6F,2C9F=6F,2CA0=3C0,2CA2=70,2CA3=70,2CA4=63,2CA5=63,2CA6=74,2CA8=79,2CAA=278,2CAB=278,2CAC=78,2CAD=3C7,2CAE=3C8,2CB0=3C9,2CB1=3C9,2CB2=2CB3,2CB4=3C.B7,2CB6=2CB7,2CB8=2CB9,2CBA=2D,2CBC=448,2CBD=448,2CBE=2CBF,2CC0=2CC1,2CC2=2CC3,2CC4=2CC5,2CC6=2F,2CC8=2CC9,2CCA=39,2CCC=33,2CCD=21D,2CCE=2CCF,2CD0=6C,2CD1=29F,2CD2=36,2CD4=2CD5,2CD6=2CD7,2CD8=2CD9,2CDA=2CDB,2CDC=3ED,2CDE=2CDF,2CE0=2CE1,2CE2=2CE3,2CE4=3D7,2CE9=2627,2CEB=2CEC,2CED=2CEE,2CF2=2CF3,2CF9=5C.5C,2D31=6F.335,2D37=28C,2D38=76,2D39=65,2D3A=1DD,2D41=6F.338,2D48=B7.B7.B7,2D49=283,2D4F=6C,2D51=21,2D54=6F,2D55=71,2D59=298,2D5D=78,2D60=1E9F,2D63=16EF,2DE8=1DDF,2DEA=30A,2DED=368,2DEF=36F,2DF6=363,2DF7=364,2E1A=2D.308,2E1E=7E.307,2E1F=7E.323,2E26=1455,2E27=1450,2E28=28.28,2E29=29.29,2E2A=2235,2E2B=2234,2E2C=2237,2E2E=61F,2E30=B0,2E31=B7,2E32=60C,2E35=61B,2E39=1E9F,2E3D=2D42,2E3F=B6,2E40=3D,2E82=4E5B,2E83=4E5A,2E85=4EBB,2E89=5202,2E8B=353E,2E8E=5140,2E8F=5C23,2E90=5C22,2E92=5DF3,2E93=5E7A,2E94=5F51,2E96=5FC4,2E97=38FA,2E98=624C,2E99=6535,2E9B=65E1,2E9E=6B7A,2EA0=6C11,2EA1=6C35,2EA2=6C3A,2EA3=706C,2EA4=722B,2EA6=4E2C,2EA8=72AD,2EAB=7F52,2EAD=793B,2EAF=7CF9,2EB1=7F53,2EB2=7F52,2EB9=8002,2EBA=8080,2EBE=8279,2EBF=8279,2EC0=8279,2EC1=864E,2EC2=8864,2EC3=8980,2EC4=897F,2EC5=89C1,2EC8=8BA0,2EC9=8D1D,2ECB=8F66,2ECC=8FB6,2ECD=8FB6,2ECF=961D,2ED0=9485,2ED1=9577,2ED2=9578,2ED3=957F,2ED4=95E8,2ED6=961D,2ED8=9752,2ED9=97E6,2EDA=9875,2EDB=98CE,2EDC=98DE,2EDD=98DF,2EDF=98E0,2EE0=9963,2EE2=9A6C,2EE4=9B3C,2EE5=9C7C,2EE8=9EA6,2EE9=9EC4,2EEB=6589,2EEC=9F50,2EED=6B6F,2EEE=9F7F,2EEF=7ADC,2EF0=9F99,2EF2=4E80,3002=2F3,3003=27.27,3007=6F,3008=276C,3009=276D,3012=20B8,3014=28,3015=29,301A=27E6,301B=27E7,302C=309,302D=325,3033=2F,304F=276C,309A=30A,30A0=3D,30A4=4EBB,30A8=5DE5,30AB=529B,30BF=5915,30C8=535C,30CB=4E8C,30CE=2F,30CF=516B,30D8=3078,30ED=53E3,30FB=B7,3126=513F,31D0=30FC,31D1=4E28,31D3=2F,31D4=5C,31D6=4E5B,31DA=4E85,31DB=276C,31DF=4E5A,31E0=4E59,39B3=363D,439B=3588,4420=3B3B,4E00=30FC,4E36=5C,4E3F=2F,5002=4F75,503C=5024,555F=5553,56D7=53E3,586B=5861,58EB=571F,58FF=58AB,5B00=5AAF,5E32=5E21,5E50=3B3A,6238=6236,6409=3A41,6663=403F,6669=665A,66F6=3ADA,6726=4443,67FF=676E,69E9=3BA3,6A27=699D,6F59=6E88,784F=7814,7D76=7D55,80A6=670C,80CA=6710,80D0=670F,80F6=3B35,8101=6713,8127=6718,8141=80FC,81A7=6723,853F=848D,8641=8637,8A1E=46B6,8A7D=8A2E,8B8F=8B86,8C63=8C5C,8D86=8D7F,8DFA=8DE5,8E9B=8E97,8F27=8EFF,90DE=90CE,93AE=93AD,96B8=96B7,9E43=9E42,9ED2=9ED1,9FC3=4039,A494=A2CD,A49C=A0C0,A49E=A04A,A4A7=A458,A4A8=A132,A4AC=A050,A4B0=A3C2,A4BA=A3BF,A4BE=A2B1,A4BF=A259,A4C0=A3AB,A4C2=A3B5,A4D0=62,A4D1=70,A4D2=64,A4D3=64,A4D4=74,A4D6=67,A4D7=6B,A4D9=6A,A4DA=63,A4DB=254,A4DC=7A,A4DD=66,A4DE=214E,A4DF=72.6E,A4E0=6E,A4E1=6C,A4E2=73,A4E3=72,A4E5=28C,A4E6=76,A4E7=68,A4EA=77,A4EB=78,A4EC=79,A4ED=1660,A4EE=61,A4EF=250,A4F0=65,A4F1=1DD,A4F2=6C,A4F3=6F,A4F4=75,A4F5=6E,A4F7=15E1,A4F8=2E,A4F9=2C,A4FA=2E.2E,A4FB=2E.2C,A4FD=3A,A4FE=2D.2E,A4FF=3D,A60E=2E,A640=A641,A642=A643,A644=32,A645=1A8,A646=69,A647=69,A648=A649,A64A=A64B,A64C=3C9,A64D=3C9,A64E=A64F,A650=2C9.62.6C,A651=2C9.62.69,A652=A653,A654=A655,A656=A657,A658=A659,A65A=A65B,A65C=A65D,A65E=A65F,A660=A661,A662=A663,A664=A665,A666=A667,A668=298,A66A=A66B,A66C=A66D,A66F=20E9,A67C=306,A67E=2C7,A680=A681,A682=A683,A684=A685,A686=A687,A688=A689,A68A=A68B,A68C=A68D,A68E=A68F,A690=A691,A692=A693,A694=68.314,A695=68.314,A696=A697,A698=6F.6F,A699=6F.6F,A69A=102A8,A6A1=1D0E,A6B0=16B9,A6B1=2C76,A6CD=2A1,A6CE=28C,A6DB=3C0,A6DF=76,A6EB=3F,A6EF=32,A6F0=302,A6F1=304,A6F4=A6F3.A6F3,A714=2EB,A716=2EA,A722=A723,A724=A725,A726=A727,A728=74.33,A729=74.21D,A72A=A72B,A72C=A72D,A72E=A72F,A731=73,A732=61.61,A733=61.61,A734=61.6F,A735=61.6F,A736=61.75,A737=61.75,A738=61.76,A739=61.76,A73A=61.76,A73B=61.76,A73C=61.79,A73D=61.79,A73E=A73F,A740=6B.335,A742=A743,A744=A745,A746=A747,A748=A749,A74A=6F.335,A74B=6F.335,A74C=A74D,A74E=6F.6F,A74F=6F.6F,A750=A751,A752=A753,A754=A755,A756=A757,A758=A759,A75A=32,A75C=A75D,A75E=A75F,A760=77.326,A761=77.326,A762=A763,A764=A765,A766=A767,A768=A769,A76A=33,A76B=21D,A76C=A76D,A76E=39,A777=74.66,A778=26,A779=A77A,A77B=A77C,A77D=1D79,A77E=A77F,A780=A781,A782=A783,A784=A785,A786=A787,A789=3A,A78B=27,A78C=27,A78D=265,A78F=B7,A790=A791,A792=A793,A795=A727,A796=A797,A798=66,A799=66,A79A=1043A,A79B=1043A,A79C=29A,A79D=29A,A79E=A4E4,A79F=75,A7A0=A7A1,A7A2=A7A3,A7A4=A7A5,A7A6=A7A7,A7A8=A7A9,A7AA=68.314,A7AB=33,A7AC=67,A7AD=26C,A7AE=69,A7B0=29E,A7B1=A4D5,A7B2=6A,A7B3=78,A7B4=62,A7B5=DF,A7B6=3C9,A7B7=3C9,A7B8=A7B9,A7BA=A7BB,A7BC=A7BD,A7BE=A7BF,A7C0=A7C1,A7C2=A7C3,A7C4=A794,A7C5=73.328,A7C6=1D8E,A7C7=A7C8,A7C9=A7CA,A7CB=264,A7CC=A7CD,A7D0=A7D1,A7D6=DF,A7D8=A7D9,A7DA=28C,A7DB=3BB,A7DC=28C.338,A7F5=A7F6,A7F7=30FC,A830=964,A960=1103.1106,A961=1103.1107,A962=1103.1109,A963=1103.110C,A964=1105.1100,A965=1105.1100.1100,A966=1105.1103,A967=1105.1103.1103,A968=1105.1106,A969=1105.1107,A96A=1105.1107.1107,A96B=1105.1107.110B,A96C=1105.1109,A96D=1105.110C,A96E=1105.110F,A96F=1106.1100,A970=1106.1103,A971=1106.1109,A972=1107.1109.1110,A973=1107.110F,A974=1107.1112,A975=1109.1109.1107,A976=110B.1105,A977=110B.1112,A978=110C.110C.1112,A979=1110.1110,A97A=1111.1112,A97B=1112.1109,A97C=1159.1159,A992=2C3F,A9A3=A99D,A9C6=A9D0,A9CF=662,AA53=AA01,AA56=AA23,AB32=65,AB35=66,AB3D=6F,AB3E=6F.338,AB3F=254.338,AB41=1DD.6F.338,AB42=1DD.6F.335,AB47=72,AB48=72,AB4D=283,AB4E=75,AB52=75,AB53=3C7,AB55=3C7,AB5A=79,AB60=459,AB62=254.65,AB63=75.6F,AB70=1D05,AB71=280,AB72=1D1B,AB74=6F.31B,AB75=69,AB7A=1D00,AB7B=1D0A,AB7C=1D07,AB7E=242,AB80=2C76,AB81=72,AB83=77,AB87=28D,AB8B=29C,AB8E=6F.335,AB90=262,AB93=7A,AB9B=A793,AB9C=75.335,AB9F=185,ABA2=280,ABA9=76,ABAA=73,ABAE=29F,ABAF=63,ABB2=1D18,ABB6=138,ABBB=6F.335,D7B0=1169.1167,D7B1=1169.1169.4E28,D7B2=116D.1161,D7B3=116D.1161.4E28,D7B4=116D.1165,D7B5=116E.1167,D7B6=116E.4E28.4E28,D7B7=1172.1161.4E28,D7B8=1172.1169,D7B9=30FC.1161,D7BA=30FC.1165,D7BB=30FC.1165.4E28,D7BC=30FC.1169,D7BD=4E28.1163.1169,D7BE=4E28.1163.4E28,D7BF=4E28.1167,D7C0=4E28.1167.4E28,D7C1=4E28.1169.4E28,D7C2=4E28.116D,D7C3=4E28.1172,D7C4=4E28.4E28,D7C5=119E.1161,D7C6=119E.1165.4E28,D7CB=1102.1105,D7CC=1102.110E,D7CD=1103.1103,D7CE=1103.1103.1107,D7CF=1103.1107,D7D0=1103.1109,D7D1=1103.1109.1100,D7D2=1103.110C,D7D3=1103.110E,D7D4=1103.1110,D7D5=1105.1100.1100,D7D6=1105.1100.1112,D7D7=1105.1105.110F,D7D8=1105.1106.1112,D7D9=1105.1107.1103,D7DA=1105.1107.1111,D7DB=1105.114C,D7DC=1105.1159.1112,D7DD=1105.110B,D7DE=1106.1102,D7DF=1106.1102.1102,D7E0=1106.1106,D7E1=1106.1107.1109,D7E2=1106.110C,D7E3=1107.1103,D7E4=1107.1105.1111,D7E5=1107.1106,D7E6=1107.1107,D7E7=1107.1109.1103,D7E8=1107.110C,D7E9=1107.110E,D7EA=1109.1106,D7EB=1109.1107.110B,D7EC=1109.1109.1100,D7ED=1109.1109.1103,D7EE=1109.1140,D7EF=1109.110C,D7F0=1109.110E,D7F1=1109.1110,D7F2=1105.1112,D7F3=1140.1107,D7F4=1140.1107.110B,D7F5=114C.1106,D7F6=114C.1112,D7F7=110C.1107,D7F8=110C.1107.1107,D7F9=110C.110C,D7FA=1111.1109,D7FB=1111.1110,FD3E=28,FD3F=29,FFFC=,10101=B7,1018E=6E.30A,10196=78.335,10197=76.335,10198=6C.335.6C.335.73.335,10199=6C.335.6C.335,101A0=2CE8,10282=62,10285=1E9F,10286=65,10287=66,1028A=6C,1028D=28C,10290=78,10292=6F,10294=16DC,10295=70,10296=73,10297=74,1029B=2B,102A0=61,102A1=62,102A2=63,102A3=1E9F,102A5=66,102AB=6F,102AD=3D9,102B0=72.6E,102B1=74,102B2=79,102B3=278,102B4=78,102B5=3C8,102B6=3C9,102B8=2D40,102CF=68,102E1=62F,102E4=648,102E8=637,102F2=635,102F5=7A,10301=62,10302=63,10309=6C,10311=72.6E,10312=3D9,10315=74,10317=78,1031A=38,1031F=2A,10320=6C,10322=78,103D1=10382,103D3=10393,10400=10428,10401=A793,10402=29A,10403=1042B,10404=6F,10405=1042D,10406=1042E,10407=1042F,10408=10430,10409=10431,1040A=10432,1040B=10433,1040C=10434,1040D=10435,1040E=10436,1040F=10437,10410=10438,10411=A4F6,10412=1043A,10413=1043B,10414=1043C,10415=63,10416=1043E,10417=277,10418=10440,10419=10441,1041A=25E,1041B=6C,1041C=10444,1041D=10445,1041E=10446,1041F=252,10420=73,10421=10449,10422=1044A,10423=254,10424=1044C,10425=1D0E,10426=1044E,10427=1044F,10429=A793,1042A=29A,1042C=6F,1043D=63,1043F=277,10442=25E,10443=29F,10448=73,1044B=254,1044D=1D0E,104A0=10486,104B0=28C,104B1=104D9,104B2=104DA,104B3=3BB,104B4=72,104B5=104DD,104B6=104DE,104B7=104DF,104B8=104E0,104B9=104E1,104BA=104E2,104BB=104E3,104BC=4C4,104BD=104E5,104BE=104E6,104BF=104E7,104C0=104E8,104C1=104E9,104C2=6F,104C3=298,104C4=FE,104C5=104ED,104C6=104EE,104C7=104EF,104C8=104F0,104C9=104F1,104CA=104F2,104CB=104F3,104CC=104F4,104CD=68.335,104CE=75,104CF=104F7,104D0=16E6,104D1=3C8,104D2=37,104D3=104FB,104D8=28C,104DB=3BB,104EA=6F,104EB=A669,104F6=75,104F9=3C8,10513=6E,10516=6F,10518=6B,1051C=63,1051D=76,10525=66,10526=6C,10527=78,10570=10597,10571=10598,10572=10599,10573=1059A,10574=1059B,10575=1059C,10576=1059D,10577=1059E,10578=1059F,10579=105A0,1057A=105A1,1057C=105A3,1057D=105A4,1057E=105A5,1057F=105A6,10580=105A7,10581=105A8,10582=105A9,10583=105AA,10584=105AB,10585=105AC,10586=105AD,10587=105AE,10588=105AF,10589=105B0,1058A=105B1,1058C=105B3,1058D=105B4,1058E=105B5,1058F=105B6,10590=105B7,10591=105B8,10592=105B9,10594=105BB,10595=105BC,10A3A=323,10A50=2E,10A57=10A56.10A56,10C80=10CC0,10C81=10CC1,10C82=10CC2,10C83=10CC3,10C84=10CC4,10C85=10CC5,10C86=10CC6,10C87=10CC7,10C88=10CC8,10C89=10CC9,10C8A=10CCA,10C8B=10CCB,10C8C=10CCC,10C8D=10CCD,10C8E=10CCE,10C8F=10CCF,10C90=10CD0,10C91=10CD1,10C92=10CD2,10C93=10CD3,10C94=10CD4,10C95=10CD5,10C96=10CD6,10C97=10CD7,10C98=10CD8,10C99=10CD9,10C9A=10CDA,10C9B=10CDB,10C9C=10CDC,10C9D=10CDD,10C9E=10CDE,10C9F=10CDF,10CA0=10CE0,10CA1=10CE1,10CA2=10CE2,10CA3=10CE3,10CA4=10CE4,10CA5=10CE5,10CA6=10CE6,10CA7=10CE7,10CA8=10CE8,10CA9=10CE9,10CAA=10CEA,10CAB=10CEB,10CAC=10CEC,10CAD=10CED,10CAE=10CEE,10CAF=10CEF,10CB0=10CF0,10CB1=10CF1,10CB2=10CF2,10CFA=10CE5,10CFC=10CC2,10D50=10D70,10D51=10D71,10D52=10D72,10D53=10D73,10D54=10D74,10D55=10D75,10D56=10D76,10D57=10D77,10D58=10D78,10D59=10D79,10D5A=10D7A,10D5B=10D7B,10D5C=10D7C,10D5D=10D7D,10D5E=10D7E,10D5F=10D7F,10D60=10D80,10D61=10D81,10D62=10D82,10D63=10D83,10D64=10D84,10D65=10D85,110BB=970,111C7=970,111CA=323,111CB=93A,111DB=A8FC,111DC=A8FB,111DE=2248,11300=30A,11413=11434.11442.11412,11419=11434.11442.11418,11424=11434.11442.11423,1142A=11434.11442.11429,1142D=11434.11442.1142C,1142F=11434.11442.1142E,1144C=1144B.1144B,11492=998,11494=99A,11496=99C,11498=99E,11499=99F,1149B=9A1,1149D=9B2,1149E=9A4,1149F=9A5,114A0=9A6,114A1=9A7,114A2=9A8,114A3=9AA,114A7=9AE,114A8=9AF,114A9=9AC,114AA=9A3,114AB=9B0,114AD=9B7,114AE=9B8,114B0=9BE,114B1=9BF,114B9=9C7,114BD=9D7,114BF=306.307,114C1=983,114C2=9CD,114C3=323,114C4=9BD,114C5=77.307,114D0=6F,114D1=9E7,114D2=9E8,114D6=9EC,115D8=11582,115D9=11582,115DA=11583,115DB=11584,115DC=115B2,115DD=115B3,11642=11641.11641,11700=72.6E,11706=76,1170A=77,1170E=77,1170F=77,118A0=76,118A1=73,118A2=66,118A3=6C,118A4=79,118A5=118C5,118A6=65,118A7=118C7,118A8=2207,118A9=7A,118AA=33,118AB=118CB,118AC=39,118AD=118CD,118AE=65,118AF=34,118B0=118D0,118B1=118D1,118B2=6C,118B3=118D3,118B4=118D4,118B5=6F,118B6=39,118B7=16DC,118B8=75,118B9=118D9,118BA=118DA,118BB=35,118BC=74,118BD=118DD,118BE=118DE,118BF=118DF,118C0=76,118C1=73,118C2=66,118C3=69,118C4=7A,118C6=37,118C8=6F,118CA=33,118CC=39,118CE=A793,118D5=36,118D6=39,118D7=6F,118D8=75,118DC=79,118E0=6F,118E3=72.6E,118E4=669,118E5=7A,118E6=77,118E9=63,118EC=78,118EF=77,118F2=63,11AE6=11AE5.11AEF,11AE7=11AE5.11AF0,11AE8=11AE5.11AE5,11AE9=11AE5.11AE5.11AEF,11AEA=11AE5.11AE5.11AF0,11AEC=11AEB.11AEF,11AED=11AEB.11AEB,11AEE=11AEB.11AEB.11AEF,11AF4=11AF3.11AEF,11AF5=11AF3.11AF0,11AF6=11AF3.11AF3,11AF7=11AF3.11AF3.11AEF,11AF8=11AF3.11AF3.11AF0,11C42=11C41.11C41,11CB2=11CAA,12038=1039A,132F9=1099E,16E40=16E60,16E41=16E61,16E42=16E62,16E43=16E63,16E44=16E64,16E45=16E65,16E46=16E66,16E47=16E67,16E48=16E68,16E49=16E69,16E4A=16E6A,16E4B=16E6B,16E4C=16E6C,16E4D=16E6D,16E4E=16E6E,16E4F=16E6F,16E50=16E70,16E51=16E71,16E52=16E72,16E53=16E73,16E54=16E74,16E55=16E75,16E56=16E76,16E57=16E77,16E58=16E78,16E59=16E79,16E5A=16E7A,16E5B=16E7B,16E5C=16E7C,16E5D=16E7D,16E5E=16E7E,16E5F=16E7F,16F07=79,16F08=76,16F0A=74,16F16=6C,16F1A=1E9F,16F1C=A659,16F26=A4F6,16F28=6C,16F2D=A793,16F35=72,16F3A=73,16F3B=33,16F3D=28C,16F3F=3E,16F40=61,16F42=75,16F43=79,16F51=27,16F52=27,1D114=7B,1D16D=2E,1D202=4FF,1D206=33,1D20B=1D0E,1D20D=76,1D20F=5C,1D212=37,1D213=66,1D214=102BC,1D215=A4F6,1D216=72,1D217=250,1D21A=6F.335,1D21B=2144,1D21C=A4D5,1D221=A793,1D222=77,1D22A=6C,1D22B=A4F6,1D230=A7FB,1D236=3C,1D237=3E,1D238=228F,1D239=2290,1D23A=2F,1D23B=5C,1D23F=16CB,1D245=6E,1E8C7=6C,1E8C8=2220,1E8C9=663,1E8CB=38,1E8CC=2202,1E8CD=2202.335,1E900=1E922,1E901=1E923,1E902=1E924,1E903=1E925,1E904=1E926,1E905=1E927,1E906=1E928,1E907=1E929,1E908=1E92A,1E909=1E92B,1E90A=1E92C,1E90B=1E92D,1E90C=1E92E,1E90D=1E92F,1E90E=1E930,1E90F=1E931,1E910=1E932,1E911=1E933,1E912=1E934,1E913=1E935,1E914=1E936,1E915=1E937,1E916=1E938,1E917=1E939,1E918=1E93A,1E919=1E93B,1E91A=1E93C,1E91B=1E93D,1E91C=1E93E,1E91D=1E93F,1E91E=1E940,1E91F=1E941,1E920=1E942,1E921=1E943,1F10F=24.20E0,1F16D=33C4.9.20DD,1F16E=63.20E0,1F312=263D,1F318=263E,1F319=263D,1F700=71.65,1F701=A659,1F702=1E9F,1F704=102BC,1F707=61.72,1F708=76.1DE4,1F70A=2629,1F714=6F.335,1F728=102A8,1F73A=29DF,1F74C=63,1F754=16DC,1F755=22A1,1F75C=73.73.73,1F75E=224F,1F768=74,1F76B=72.6E.62,1F76C=76.62,1F771=22A0');
  function nmNorm(x) { return String(x == null ? '' : x).replace(NM_INVIS, '').normalize('NFKC').replace(NM_INVIS, '').replace(NM_SPACE, ' ').replace(/^ | $/g, ''); }
  function nmProblem(n) {
    if (!n) return 'empty'; if (Array.from(n).length > 120) return 'long'; if (NM_DIGIT.test(n)) return 'digit'; if (NM_BAD.test(n)) return 'char';
    var w = n.split(' '); if (w.some(function (x) { return !NM_LET.test(x); })) return 'word'; if (w.some(function (x) { return !NM_WORD.test(x); })) return 'mark';
    var s = w.map(function (x) { var f = NM_SCRIPTS.find(function (p) { return p[1].test(x); }); return f ? f[0] : null; });
    if (s.some(function (x) { return !x; })) return 'script';
    if (s.some(function (x) { return x !== s[0]; }) && s.some(function (x) { return x === 'Grek' || x === 'Cyrl'; })) return 'script';
    return '';
  }
  function nmMessage(n, p) { if (p !== 'char') return NM_MSG[p] || ''; var c = (n.match(NM_BAD) || [''])[0]; return NM_MSG.char.replace('%s', c).replace('%s', (c.codePointAt(0) || 0).toString(16).toUpperCase().padStart(4, '0')); }
  function nmSkel(x) { return Array.from(nmNorm(x).normalize('NFD'), function (c) { var k = NM_SKEL.get(c); return k == null ? c : k; }).join('').normalize('NFD'); }
/* <<< generated */
  function nmKey(x) { return nmSkel(x); }
  /* a fact shown after a name in the picker (company, headline, city): whatever is not a letter, mark, number, space or plain
     punctuation reads " - ", so no fact can draw the picker's "·" or a "✓ Your connection" of its own */
  function nmFact(x) { return nmNorm(x).replace(/[^\p{L}\p{M}\p{N} .,'’()&/+#-]+/gu, ' - ').replace(/ +/g, ' ').replace(/^ | $/g, ''); }
  /* a typed or picked text, compared by skeleton: the separators the picker wrote stay, every part is its skeleton */
  function nmTyped(x) { return String(x == null ? '' : x).split(/\s+\u00B7\s+/).map(nmKey).join(' \u00B7 '); }
  /* the same, ignoring case — only to read what someone TYPED (an option names one member; a bare name typed in lower case still
     finds its one member when nobody else's name reads the same): "ibrahim" for "Ibrahim", whose skeleton is "lbrahirn" */
  function nmTypedCI(x) { return nmTyped(String(x == null ? '' : x).toLowerCase()); }
  function nmHandle(id) { return '#' + String(id).replace(/-/g, '').slice(0, 6); }
  function nmAdd(p) {
    if (!p || !p.id || p.id === ME_UUID) return; var o = NM.people[p.id] || {};
    function pick(k, ok) { return p[k] != null ? String(p[k]) : (o[ok] || ''); }
    var raw = String(p.name || o.raw || 'Member').trim(), u = nmUser(p.id);
    NM.people[p.id] = { id: p.id, raw: raw, name: nmNorm(txt(raw)) || 'Member', headline: nmFact(txt(pick('headline', 'headline'))), company: nmFact(txt(pick('company', 'company'))), city: nmFact(txt(pick('location', 'city'))),
      fix: 'name_needs_fix' in p ? !!p.name_needs_fix : 'fix' in p ? !!p.fix : o.fix != null ? o.fix : !!(u && u.nameFix) };   /* a name that breaks the rule (0038): never sent to by name alone */
  }
  function nmUser(id) { var a = aid(id); return (window.USERS || []).find(function (u) { return u.id === a; }) || null; }   /* never U(): it falls back to me */
  function nmConn(id) { return (window.CONN_STATE || {})[aid(id)] === 'connected'; }
  function nmOptions() {
    var ar = document.documentElement.lang === 'ar', mark = ar ? '✓ من اتصالاتك' : '✓ Your connection',
        same = ar ? '⚠️ نفس الاسم والبيانات لعضو آخر — افتح ملفه وراسله من هناك لتتأكد' : '⚠️ Same name and details as another member — open their profile and message from there to be sure',
        odd = ar ? '⚠️ هذا الاسم فيه حروف لا يسمح بها Drugbox — تأكد أنه الشخص الصحيح' : '⚠️ This name has characters Drugbox does not allow — make sure it is the right person';
    function T(x) { return ar && x && window.dxT ? window.dxT(x) : x; }   /* a role from the sign-up list reads in the interface language */
    var all = Object.keys(NM.people).map(function (k) { return NM.people[k]; }), groups = {}; NM.map = {}; NM.ci = {};
    all.forEach(function (p) { p.conn = nmConn(p.id); p.twin = false; var k = nmKey(p.name); (groups[k] = groups[k] || []).push(p); });
    /* members whose names have the same skeleton are one group (they look the same); a member whose name breaks the rule is
       always told apart, even alone */
    Object.keys(groups).forEach(function (k) {
      var g = groups[k]; if (g.length === 1 && !g[0].fix) { g[0].value = g[0].name; return; }
      g.forEach(function (p) { var h = nmFact(T(p.headline.split('|')[0].trim()));
        p.facts = [p.company, nmKey(h) === nmKey(p.company) ? '' : h, p.city, p.conn ? mark : ''].filter(Boolean); });
      var max = Math.max.apply(null, g.map(function (p) { return p.facts.length; })), L = 1;
      for (; L < max; L++) { var seen = {}, dup = false; g.forEach(function (p) { var v = nmTyped(p.facts.slice(0, L).join(' · ')); if (seen[v]) dup = true; seen[v] = 1; }); if (!dup) break; }
      var n = {}; g.forEach(function (p) { p.value = p.name + (p.facts.length ? ' · ' + p.facts.slice(0, L).join(' · ') : ''); var v = nmTyped(p.value); n[v] = (n[v] || 0) + 1; });
      g.forEach(function (p) { if (n[nmTyped(p.value)] > 1 || !p.facts.length || p.fix) { p.twin = true; p.value += ' · ' + nmHandle(p.id); } });   /* last resort: a short handle — and a warning */
    });
    all.forEach(function (p) { var v = nmTyped(p.value), c = nmTypedCI(p.value);                                    /* a text that fits two people sends to nobody */
      NM.map[v] = v in NM.map && NM.map[v] !== p.id ? null : p.id; NM.ci[c] = c in NM.ci && NM.ci[c] !== p.id ? null : p.id; });
    all.sort(function (a, b) { return (b.conn - a.conn) || a.name.localeCompare(b.name) || a.value.localeCompare(b.value); });
    return all.map(function (p) {
      return { name: p.value, label: (p.fix ? odd + ' · ' : p.twin ? same + ' · ' : '') + [nmFact(T(p.headline.split('|')[0].trim())), p.company, p.city, p.conn ? mark : ''].filter(Boolean).join(' · ').slice(0, 160) };
    });
  }
  function nmPaint() { var dl = document.getElementById('nmList'); if (!dl) return;
    dl.innerHTML = nmOptions().map(function (o) { return '<option value="' + esc2(o.name) + '"' + (o.label ? ' label="' + esc2(o.label) + '"' : '') + '>'; }).join(''); }
  window.dxMxPeople = function () {
    NM.people = {}; if (!ME_UUID) return [];
    MX.convs.forEach(function (c) { var u = nmUser(c.partner) || {}; nmAdd({ id: c.partner, name: c.name || u.name, headline: c.headline || u.headline || '', company: u.company || '', location: u.location || '', fix: !!(c.name_needs_fix || u.nameFix) }); });
    Object.keys(window.CONN_STATE || {}).forEach(function (k) { if (window.CONN_STATE[k] !== 'connected' || !uuidOf(+k)) return; var u = nmUser(uuidOf(+k)); if (u) nmAdd({ id: uuidOf(+k), name: u.name, headline: u.headline || '', company: u.company || '', location: u.location || '', fix: !!u.nameFix }); });
    return nmOptions();
  };
  /* a value inside a PostgREST or=(…) filter: quoted, since a name may hold "," "(" ")" "." */
  function pgq(v) { return '"' + String(v).replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'; }
  /* members whose name contains what was typed, or LOOKS like it (the skeleton): a look-alike always shows next to the real one */
  async function nmSearch(q) {
    var w = nmNorm(q.split(' · ')[0]);
    var r = await sb.from('profiles').select(PCOLS).or('name.ilike.' + pgq('%' + nmLike(w) + '%') + ',name_key.like.' + pgq('%' + nmLike(nmKey(w)) + '%')).neq('id', ME_UUID).order('name').limit(12);
    if (r.error) throw r.error; (r.data || []).forEach(function (p) { putUser(p); nmAdd(p); }); return r.data || [];
  }
  document.addEventListener('input', function (e) {
    if (!ME_UUID || !e.target || e.target.id !== 'nmTo') return;
    var q = e.target.value.trim(); clearTimeout(NM.t); if (q.length < 2 || q.length > 80 || (nmPick(nmTyped(q), nmTypedCI(q)) && q.indexOf(' · ') > 0)) return;   /* a bare name is looked up even when one person with it is known: others may share it */
    NM.t = setTimeout(function () { nmSearch(q).then(nmPaint, function (err) { console.error(err); }); }, 200);
  }, true);
  /* who receives: every member whose name has the chosen name's SKELETON (the same name, or one that looks the same) is fetched
     first, so the options are told apart with all of them known; the text sent must then name exactly one of them */
  function nmPick(key, ci) { return key in NM.map ? NM.map[key] : NM.ci[ci]; }   /* the exact option first; typed case only when no option reads so */
  async function nmResolve(to) {
    var key = nmTyped(to), ci = nmTypedCI(to), was = nmPick(key, ci), p = was && NM.people[was], name = p ? p.raw : nmNorm(to.split(' · ')[0]), sk = nmKey(name);
    if (!name || name.length > 200) return { err: 'No member called ' + to + ' — choose someone from the list' };
    var r = await sb.from('profiles').select(PCOLS + ',name_key').or('name_key.eq.' + pgq(sk) + ',name.ilike.' + pgq(nmLike(name))).neq('id', ME_UUID).limit(50); if (r.error) throw r.error;
    var rows = r.data || [], keys = rows.map(function (x) { return x.name_key; }).filter(function (k, i, a) { return k && k !== sk && a.indexOf(k) === i; });
    if (keys.length) {   /* a name typed in another case: also every member who looks like the ones it found */
      var r2 = await sb.from('profiles').select(PCOLS).in('name_key', keys.slice(0, 10)).neq('id', ME_UUID).limit(50); if (r2.error) throw r2.error; rows = rows.concat(r2.data || []); }
    rows.forEach(function (x) { putUser(x); nmAdd(x); });
    nmOptions(); var id = nmPick(key, ci);
    if (id && (!was || id === was)) return { id: id };
    var same = Object.keys(NM.people).filter(function (k) { return nmKey(NM.people[k].name) === sk || nmTypedCI(NM.people[k].name) === nmTypedCI(name); });
    nmPaint();
    if (same.length > 1) return { err: 'Several members are called ' + txt(name) + ' — choose one from the list' };
    if (same.length === 1 && NM.people[same[0]].fix) return { err: 'Choose ' + txt(name) + ' from the list to be sure who receives it' };
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
      var rows = r.data || []; addRows(rows, !key && !off); sitesFor(rows);
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
  function siteFrom(s) { return { id: 's' + s.id, name: txt(s.name), type: TYPE[s.type] || 'Factory', city: txt(s.city), gov: txt(s.gov != null ? s.gov : s.governorate),
      certs: (s.certs || []).map(function (t) { return { name: txt(t.name), expiry: ym(t.expiry), src: t.source === 'public_list' ? 'Public industry list' : 'Certificate document', checked: (t.checked || t.checked_at) ? String(t.checked || t.checked_at).slice(0, 10) : '' }; }) }; }
  /* a company's sites are exactly its company_sites rows: none in the database → none on the page and "0 sites" on its card — never the
     interface's sample "<city> site · Factory" (that default is for the demo's sample companies only) */
  async function loadSites(slug) {
    var r = await sb.rpc('company_sites_public', { p_slug: slug }); if (r.error) throw r.error;
    window.dxLiveSites = window.dxLiveSites || {};
    window.dxLiveSites[slug] = (r.data || []).map(siteFrom);
    CO.sitesAt[slug] = Date.now(); window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;
  }
  /* the directory cards say "N sites" and filter by certificate: the sites of a directory page come in one request with the page */
  function sitesFor(rows) {
    var me = ME_UUID, want = rows.filter(function (c) { return c && c.id && okSlug(c.slug) && !(CO.sitesAt[c.slug] && Date.now() - CO.sitesAt[c.slug] < 60000); }); if (!want.length) return;
    var slugOf = {}; want.forEach(function (c) { slugOf[c.id] = c.slug; });
    sb.from('company_sites').select('id,company_id,name,type,city,governorate,certs:site_certificates!site_certificates_site_id_fkey(name,expiry,source,checked_at)').in('company_id', want.map(function (c) { return c.id; })).order('id').limit(1000).then(function (r) {
      if (r.error || me !== ME_UUID) { if (r.error) console.error(r.error); return; }
      var by = {}; want.forEach(function (c) { by[c.slug] = []; });
      (r.data || []).forEach(function (s) { var sl = slugOf[s.company_id]; if (sl) by[sl].push(siteFrom(s)); });
      window.dxLiveSites = window.dxLiveSites || {}; var now = Date.now();
      Object.keys(by).forEach(function (sl) { window.dxLiveSites[sl] = by[sl]; CO.sitesAt[sl] = now; });
      window.__dxStoreVer = (window.__dxStoreVer || 0) + 1; redrawDir();
    });
  }
  /* the full track record of one company (the directory carries only its rating) — loaded when its page opens */
  async function loadTrack(slug) {
    var raw = CO.raw[slug]; if ((!raw || !raw.id) && CO.loading) { try { await CO.loading; } catch (e) {} raw = CO.raw[slug]; }   /* opened while the directory is still loading */
    if (!raw || !raw.id) { await ensureCompanies([slug]); raw = CO.raw[slug]; }                                   /* a company from a page not loaded yet */
    if (!raw || !raw.id) return; var r = await sb.rpc('company_track_record', { p_company: raw.id }); if (r.error) throw r.error; CO.track[slug] = r.data || {}; CO.trackAt[slug] = Date.now(); }
  /* B-24: the directory is drawn again when its rows arrive (and on every filter), and a redraw replaces the page — with the footer the
     approved page ends with. The footer comes back after each redraw of the Companies page (the directory's code may arrive with its
     page, so its render is wrapped when first seen). */
  function dirFoot() { var c = document.getElementById('content');
    if (c && document.body.getAttribute('data-page') === 'companies' && !c.querySelector('footer.dg-foot') && typeof window.dgFooter === 'function') window.dgFooter(c, 'companies'); }
  function wrapDir() { var d = window.dxDir; if (!d || typeof d.render !== 'function' || d.render.__foot) return;
    var o = d.render; d.render = function () { var r = o.apply(this, arguments); dirFoot(); return r; }; d.render.__foot = true; }
  function rerenderCompanies() { try { if (window.dxDir && document.body.getAttribute('data-page') === 'companies') { wrapDir(); window.dxDir.render(); } } catch (e) { console.error(e); } }
  wrapDir(); if (window.dxCore) window.dxCore.onRender('live-dir-foot', function () { wrapDir(); dirFoot(); });
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
    paintSponsored(mk);   /* the ticker is filled at sign-in from ticker_feed() (P1b below), not from this page */
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
    var card = e.target.closest && e.target.closest('#jx [data-live^="j"]'); if (!card || !ME_UUID) return;   /* a job card — never a candidate card ("c…"): its id is a person, not a job */
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
      sb.from('profiles').select(PFULL).eq('id', u).single().then(function (r) { if (r.data) putUser(r.data); oGotoProfile.apply(self, args); }, function () { oGotoProfile.apply(self, args); });
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
    /* a member's level is not recorded: no seniority badge (it said "Mid-Level" for everyone) */
    var t = c.querySelector('.jc-title'); if (t) { var rb = t.querySelector('.role-badge'); t.textContent = p.headline || 'Open to work'; if (rb) t.insertBefore(rb, t.firstChild); }
    var co = c.querySelector('.jc-company'); if (co) co.innerHTML = '<span>' + esc2(p.name) + '</span> · <span>' + (FLAG[p.country] || '') + ' ' + esc2(p.location || '') + '</span>' + (p.verified ? ' · <span style="color:#1a56db">✓ Verified</span>' : '');
    var tg = c.querySelector('.jc-tags'); if (tg) tg.innerHTML = '<span class="jt jt-ft">Open to work</span>';
    var ds = c.querySelector('.jc-desc'); if (ds) ds.textContent = p.bio || '';
    var ps = c.querySelector('.jc-posted'); if (ps) ps.textContent = ago(p.created_at);
    c.querySelectorAll('.jx-trust, .dx-vid-chip').forEach(function (x) { x.remove(); }); delete c.dataset.vid;
    /* "Save" on a person saved a job with the person's number (409 from the database): saved jobs are jobs — the button is left out here */
    var sv = c.querySelector('.save-btn'); if (sv) sv.remove();
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
  var RK_IN = { love: 'support' }, RK_OUT = {};   /* reactions.kind holds the six kinds of the panel since 0028 (as on Home); older rows may say 'love' */
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
    if (q('.group-meta-stats')) q('.group-meta-stats').innerHTML = '<div><b>' + (g.member_count || 0).toLocaleString('en') + '</b> ' + (g.member_count === 1 ? 'member' : 'members') + '</div>' +
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
    var pill = document.querySelector('#content .dg-pill-page'); if (pill && window.dgPillText) { var pt = window.dgPillText('training'); if (pill.textContent !== pt) pill.textContent = pt; }
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
    if (ME_UUID && page === 'training') return (TRN.at ? TRN.courses.length : '…') + ' COURSES  /  GMP  /  REGULATORY  /  FORMULATION';   /* the courses the database has, not the demo's six */
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

  /* ═══════════════ P1b — the last sample numbers and lists (S-19 ticker, Home and sign-in page; J-05 Jobs numbers; B-06 My Intents;
     J-SOCIAL-49 profile numbers). Data from 0035 (one call each); the approved markup only gets its words and numbers, and an
     element with nothing real to show is hidden. ═══════════════ */
  function fmtN(n) { return Number(n || 0).toLocaleString('en'); }
  function origT(e) { return e ? (window.dxOrigText ? window.dxOrigText(e) : e.textContent) : ''; }

  /* the top ticker: never the demo's items — empty (and hidden) until ticker_feed() answers, hidden while there is nothing real */
  var TK = { at: 0, p: null };
  var oBuildTicker = window.buildTicker;
  if (typeof oBuildTicker === 'function') window.buildTicker = function () {
    var r = oBuildTicker.apply(this, arguments), t = document.querySelector('.ticker'), d = (window.TICKER_ITEMS || []).length ? '' : 'none';
    if (t && t.style.display !== d) t.style.display = d; return r; };
  function setTicker(items) { var T = window.TICKER_ITEMS; if (!Array.isArray(T)) return; T.length = 0; (items || []).forEach(function (x) { if (x && x.text) T.push({ label: x.label || 'News', text: x.text }); }); if (window.buildTicker) window.buildTicker(); }
  setTicker([]);
  function loadTicker() { if (TK.p) return TK.p;
    TK.p = sb.rpc('ticker_feed').then(function (r) { TK.p = null; if (r.error) throw r.error; TK.at = Date.now(); if (ME_UUID) setTicker(r.data || []); }, function (e) { TK.p = null; throw e; });
    return TK.p; }
  function tickerSoon(age) { if (ME_UUID && Date.now() - TK.at > age) loadTicker().catch(function (e) { console.error(e); }); }

  /* Jobs (J-05): the strip, the seniority counts and the two list headers from jobs_stats(); the reach line from the member count */
  var JS = { s: null, at: 0, p: null };
  function jobStats() { if (JS.p) return JS.p;
    JS.p = sb.rpc('jobs_stats').then(function (r) { JS.p = null; if (r.error) throw r.error; JS.s = r.data || null; JS.at = Date.now(); }, function (e) { JS.p = null; throw e; });
    return JS.p; }
  function paintJobNumbers() {
    var root = document.getElementById('jx'); if (!root || !ME_UUID) return;
    var s = JS.s, ok = !!s, n = function (v) { return ok ? fmtN(v) : '…'; }, lv = (s && s.by_level) || {};
    var ib = root.querySelectorAll('.intel-strip .intel-item b'); [s && s.open, s && s.week, s && s.candidates].forEach(function (v, i) { if (ib[i]) setNum(ib[i], n(v)); });
    [].forEach.call(root.querySelectorAll('#seniorityFilter .sen-opt[data-level] .sen-count'), function (e) { setNum(e, n(lv[e.parentElement.dataset.level])); });
    [].forEach.call(root.querySelectorAll('.sec-title'), function (t) { var sp = t.querySelector('span'), o = origT(t); if (!sp) return;
      if (/^\s*Open Positions/.test(o)) setNum(sp, ok ? fmtN(s.open) + (s.open === 1 ? ' job' : ' jobs') : '…');
      else if (/^\s*Available Candidates/.test(o)) setNum(sp, ok ? fmtN(s.candidates) + (s.candidates === 1 ? ' profile' : ' profiles') : '…'); });
    [].forEach.call(root.querySelectorAll('.post-cta-sub'), function (e) { setTextNode(e, /^Reach (150,000\+|[\d,]+|…) pharma professionals?/, function () {
      return 'Reach ' + (PG.members == null ? '…' : fmtN(PG.members)) + (PG.members === 1 ? ' pharma professional on Drugbox' : ' pharma professionals on Drugbox'); }); });
    /* the candidates are members open to work — the database does not verify them, so the list does not say "Verified" */
    [].forEach.call(root.querySelectorAll('.sec-sub'), function (e) { if (origT(e).trim() === 'Verified professionals actively looking') setTextNode(e, /^Verified professionals actively looking$/, function () { return 'Professionals open to work'; }); });
  }
  var paintJobsP1b = paintJobs;
  paintJobs = function () { paintJobsP1b(); paintJobNumbers(); };
  var loadJobsP1b = loadJobs;
  loadJobs = async function () { await Promise.all([loadJobsP1b(), onPageNow('jobs') ? jobStats().catch(function (e) { console.error(e); }) : null]); };
  var oJobsP1b = window.renderJobs;
  window.renderJobs = function () { var r = oJobsP1b.apply(this, arguments); if (!ME_UUID) return r; paintJobNumbers();
    if (Date.now() - JS.at > 3000) jobStats().then(function () { if (onPageNow('jobs')) paintJobNumbers(); }, function (e) { console.error(e); });
    return r; };
  /* a job saved with seniority "executive" is the Executive level (the counts above count it there too) */
  var jobCardP1b = jobCard;
  jobCard = function (j) { return jobCardP1b(j && j.seniority === 'executive' ? Object.assign({}, j, { seniority: 'exec' }) : j); };

  /* My Intents (B-06): kept with my profile (profiles.intents, 0035) — a new member starts with nothing chosen; never this browser's storage */
  var INT_CATS = ['api', 'cosmetic', 'supplement', 'packaging', 'cmo', 'equipment', 'license', 'service', 'job', 'training'], INT_V = ['i-have', 'i-need', 'both', 'na'];
  var INT_SHORT = { api: '📦 APIs', cosmetic: '💄 Cosmetic Ingredients', supplement: '🥗 Supplements', packaging: '📦 Packaging', cmo: '🏭 CMO', equipment: '⚙️ Equipment', license: '📋 Licenses', service: '🛠️ Services', job: '🏢 Jobs', training: '📚 Training' };
  function cleanIntents(o) { var r = {}; Object.keys(o || {}).forEach(function (k) { if (INT_CATS.indexOf(k) >= 0 && INT_V.indexOf(o[k]) >= 0) r[k] = o[k]; }); return r; }
  var kitP1b = window.dxKitHook;
  window.dxKitHook = function (op, k, v) {
    if (k === 'intents' && ME_UUID) {
      if (op === 'get') return Object.assign({}, window.ME.intents || {});
      var val = cleanIntents(v), prev = window.ME.intents; window.ME.intents = val;
      sb.from('profiles').update({ intents: val }).eq('id', ME_UUID).then(function (r) { if (r.error) { window.ME.intents = prev; toastErr(r.error); } });
      return true;
    }
    return kitP1b ? kitP1b(op, k, v) : undefined;
  };
  function paintIntents() {
    var tab = document.getElementById('tab-intents'); if (!tab || !ME_UUID) return;
    var mine = window.ME.intents || {};
    [].forEach.call(tab.querySelectorAll('.cat-intent-row'), function (row) { var v = mine[row.dataset.cat];
      [].forEach.call(row.querySelectorAll('.it-opt'), function (o) { var on = !!v && o.classList.contains(v); if (o.classList.contains('active') !== on) o.classList.toggle('active', on); }); });
    /* "How this appears on your profile": the same tags the page draws when a choice is clicked */
    var box = tab.querySelector('#profilePreviewTags'); if (!box) return; var tags = [];
    [].forEach.call(tab.querySelectorAll('.cat-intent-row'), function (row) { var a = row.querySelector('.it-opt.active'); if (!a || a.classList.contains('na')) return;
      var cls = a.classList.contains('i-have') ? 'have' : a.classList.contains('i-need') ? 'need' : 'both';
      var name = INT_SHORT[row.dataset.cat] || origT(row.querySelector('.cir-name')).trim(), what = origT(a).replace(/\s+/g, ' ').trim().replace(/^\S+\s*/, '');
      tags.push('<span class="pp-tag ' + cls + '">' + esc2(name.replace(/^\S+\s/, cls === 'both' ? '↔️ ' : cls === 'need' ? '🔍 ' : name.split(' ')[0] + ' ')) + ': ' + esc2(cls === 'both' ? 'Both' : what) + '</span>'); });
    var html = tags.join('') || '<span style="color:#94a3b8;font-size:12px">Nothing selected yet</span>';
    box.innerHTML = html;   /* always: the page's own clicks redraw this box too */
  }
  var oMarketP1b = window.renderMarket;
  window.renderMarket = function () { var r = oMarketP1b.apply(this, arguments); if (ME_UUID) { paintIntents(); tickerSoon(120000); } return r; };
  var hookP1b = window.dxLiveHook;   /* a listing just published: the ticker shows it */
  window.dxLiveHook = function (kind, d) { var r = hookP1b ? hookP1b(kind, d) : undefined; if (kind === 'listing' && ME_UUID) setTimeout(function () { TK.at = 0; tickerSoon(0); }, 1500); return r; };

  /* profile numbers (J-SOCIAL-49): another member's connections from profile_counts(); a visit to someone's profile is recorded
     (increment_profile_view, once per viewer — the database keeps the log), so "Profile views" counts real visitors. Post
     impressions are not recorded by the live app, so that line is left out rather than showing a number that never moves. */
  var PCNT = {}, PVIEW = {};
  var putUserP1b = putUser;
  putUser = function (p) { putUserP1b(p); if (p && PCNT[p.id] != null) { var a = aid(p.id), u = window.USERS.find(function (x) { return x.id === a; }); if (u) u.connections = PCNT[p.id]; } };
  function paintProfCounts() {
    if (!ME_UUID || !onPageNow('profile')) return; var u = window._profUser, id = u && uuidOf(u.id); if (!id || id === ME_UUID || PCNT[id] == null) return;
    var st = document.querySelectorAll('#content .profile-stats .pstat-n'); if (st[1]) setNum(st[1], fmtN(PCNT[id]));
  }
  var oGotoP1b = window.gotoProfile;
  window.gotoProfile = function (uid) {
    var a = parseInt(uid, 10), u = uuidOf(a);
    if (ME_UUID && u && u !== ME_UUID) {
      if (!PVIEW[u]) { PVIEW[u] = 1; sb.rpc('increment_profile_view', { target: u }).then(function (r) { if (r.error) delete PVIEW[u]; }, function () { delete PVIEW[u]; }); }
      sb.rpc('profile_counts', { p_id: u }).then(function (r) { if (r.error || !r.data) return; PCNT[u] = +r.data.connections || 0;
        var x = window.USERS.find(function (y) { return y.id === a; }); if (x) x.connections = PCNT[u]; paintProfCounts(); }, function () {});
    }
    return oGotoP1b.apply(this, arguments);
  };
  if (window.dxCore) window.dxCore.onRender('live-prof-counts', paintProfCounts);
  /* my own profile, when my name breaks the name rule (0038 flagged it): ask me to update it — others see a warning next to it */
  function nameFixNote() {
    var c = document.getElementById('content'), info = c && c.querySelector('.profile-info'), old = c && c.querySelector('.dx-name-fix');
    var mine = ME_UUID && window.ME.nameFix && document.body.getAttribute('data-page') === 'profile' && window._profUser && window._profUser.id === window.ME.id;
    if (!mine) { if (old) old.remove(); return; } if (old || !info) return;
    var d = document.createElement('div'); d.className = 'dx-name-fix'; d.setAttribute('role', 'status');
    d.style.cssText = 'margin:10px 0 0;padding:10px 12px;border:1px solid #f59e0b;background:#fffbeb;color:#92400e;border-radius:9px;font-size:13px;line-height:1.5';
    d.innerHTML = '<span>Please update your name — it has characters Drugbox no longer allows, so other members see a warning next to it.</span> '
      + '<button type="button" class="btn-ghost" style="margin-top:6px" onclick="showEditProfile()">Update my name</button>';
    info.appendChild(d);
  }
  if (window.dxCore) window.dxCore.onRender('live-name-fix', nameFixNote);
  /* "People also viewed" listed the first members loaded, not people who viewed this profile: the live app records no co-views yet,
     so the box is left out rather than invented (J-SOCIAL-49) */
  function hideAlsoViewed() {
    if (!ME_UUID || !onPageNow('profile')) return;
    [].forEach.call(document.querySelectorAll('#content .card > div:first-child'), function (h) {
      var t = (window.dxOrigText ? window.dxOrigText(h) : h.textContent).trim(); if (t !== 'People also viewed') return;
      var col = h.parentElement.parentElement; if (col && col.children.length === 1) col.style.display = 'none'; else h.parentElement.style.display = 'none'; });
  }
  if (window.dxCore) window.dxCore.onRender('live-prof-also', hideAlsoViewed);
  var oSideP1b = window.renderFeedSidebar;
  if (oSideP1b) window.renderFeedSidebar = function () { var h = oSideP1b.apply(this, arguments); if (!ME_UUID || typeof h !== 'string') return h;
    var s = h.indexOf('>Post impressions<'), ra = s < 0 ? -1 : h.lastIndexOf('<div', s), rz = s < 0 ? -1 : h.indexOf('</div>', s);
    return ra >= 0 && rz > s ? h.slice(0, ra) + h.slice(rz + 6) : h; };
  /* every page's footer names the site the app is served from, not the demo's hosting address (drugbox-v3.vercel.app) */
  function footHost(root) { var h = location.host; if (!h) return;
    [].forEach.call((root || document).querySelectorAll('footer.dg-foot > span:first-child'), function (sp) { var i = sp.querySelector('i'), t = i && i.nextSibling;
      if (t && t.nodeType === 3 && t.nodeValue !== h) t.nodeValue = h; }); }
  var oFootP1b = window.dgFooter;
  if (oFootP1b) window.dgFooter = function (c) { var r = oFootP1b.apply(this, arguments); footHost(c); return r; };
  footHost();
  var oNetP1b = window.renderNetwork;
  window.renderNetwork = function () { var r = oNetP1b.apply(this, arguments);
    if (ME_UUID) [].forEach.call(document.querySelectorAll('#content .net-overview-item'), function (e) { if (/Post impressions/.test(origT(e))) hideEl(e); });
    return r; };

  /* Home: real members' photos beside "N professionals" (members who added one; none → no row), and no empty TODAY card */
  PG.faces = null;
  function facesHtml() { var f = (PG.faces || []).filter(function (p) { return safeUrl(p.avatar_url); });
    return f.length ? '<div class="dg-faces-row">' + f.map(function (p) { return '<img src="' + window.escSrc(safeUrl(p.avatar_url)) + '" alt="">'; }).join('') + '</div>' : ''; }
  var oHeroP1b = window.renderFeedHero;
  if (oHeroP1b) window.renderFeedHero = function () { var h = oHeroP1b.apply(this, arguments); if (!ME_UUID || typeof h !== 'string') return h;
    h = h.replace(/<div class="dg-faces-row">[\s\S]*?<\/div>/, facesHtml());
    if (!/<aside class="dg-today">[\s\S]*?<li[\s>]/.test(h)) h = h.replace(/<aside class="dg-today">[\s\S]*?<\/aside>/, '');
    return h; };
  async function loadFaces() {
    var r = await sb.from('profiles').select('id, avatar_url').not('avatar_url', 'is', null).order('created_at', { ascending: false }).limit(6); if (r.error) throw r.error;
    PG.faces = r.data || []; var w = document.querySelector('#content .dg-hero .dg-faces'); if (!w) return;
    var row = w.querySelector('.dg-faces-row'), html = facesHtml(); if (row) row.remove(); if (html) w.insertAdjacentHTML('afterbegin', html);
  }
  var loadMembersP1b = loadMembers;
  loadMembers = async function () { await Promise.all([loadMembersP1b(), loadFaces().catch(function (e) { console.error(e); })]);
    if (onPageNow('jobs')) paintJobNumbers(); };

  /* the sign-in page is shown before sign-in: the anon key runs no function and reads no member data (F-26/F-27), so its sample
     totals ("12K+ professionals", "1,200+ listings", "18 countries") and stock faces are left out rather than counted */
  (function signInPage() {
    var hero = document.querySelector('.lg-hero'); if (!hero) return;
    hero.querySelectorAll('.dg-faces-row').forEach(function (r) { r.remove(); });
    var st = hero.querySelector('.lg-stats'); if (st) st.style.display = 'none';
    var tx = hero.querySelector('.dg-faces-tx'); if (tx && tx.querySelector('b')) tx.textContent = 'Join pharma professionals — from new graduates to industry veterans';
    /* the sign-up page every new member opens claimed "12,000+ pharma professionals are waiting" (S-19): it says what Drugbox is instead */
    var su = document.querySelector('#signupPage .auth-sub'); if (su && /\d/.test(su.textContent)) su.textContent = 'The professional network for pharma, cosmetics & medical devices.';
  })();

  /* sign-in fills the ticker; sign-out empties it */
  var hydrateP1b = hydrateMe;
  hydrateMe = async function (uid) { var me = await hydrateP1b(uid); TK.at = 0; tickerSoon(0); return me; };
  onReset(function () { setTicker([]); TK.at = 0; JS.s = null; JS.at = 0; PCNT = {}; PVIEW = {}; PG.faces = null; });
  window.dxLive.version = 'P1b';











})();
