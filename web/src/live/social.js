/* Drugbox live — area social & account. Loaded right after adapter.js (web/build/live.py); uses the adapter's internals
   (window.dxLive.k). Each block replaces a demo service of the social layers (web/src/soc_*.js) with the database. */
(function () {
  var L = window.dxLive; if (!L || !L.k || !L.sb) return;
  var sb = L.sb, K = L.k, CFG = window.DRUGBOX_CONFIG || {};
  function me() { return K.me; }
  function $(id) { return document.getElementById(id); }
  function friendly(e) { return K.friendly(e); }
  function fail(e) { return Promise.reject(new Error(friendly(e))); }
  function home() { return location.origin + location.pathname; }
  function toast(m) { if (typeof window.toast === 'function') window.toast(m); }

  /* ===== AREA social: account — sign-up confirmation, password reset, Settings, delete my account, download my data ===== */
  var ACC = { email: '', signup: null, login: null, settings: null };
  var hp = new URLSearchParams(String(K.hash || '').replace(/^#\/?/, ''));
  var LINK = hp.get('error_code') || hp.get('error') ? { error: hp.get('error_description') || 'invalid' } : hp.get('access_token') ? { type: hp.get('type') } : null;
  /* sign-up: the Terms version agreed to and the address the confirmation link comes back to; what came back is remembered */
  var oSignUp = sb.auth.signUp.bind(sb.auth);
  sb.auth.signUp = function (cred) {
    cred = Object.assign({}, cred); cred.options = Object.assign({}, cred.options); cred.options.data = Object.assign({}, cred.options.data, { terms: window.dxLegal ? window.dxLegal.version : 'unversioned' });
    cred.options.emailRedirectTo = cred.options.emailRedirectTo || home();
    return oSignUp(cred).then(function (r) { ACC.signup = { email: cred.email, waiting: !r.error && r.data && r.data.user && !r.data.session }; return r; });
  };
  var oSignIn = sb.auth.signInWithPassword.bind(sb.auth);
  sb.auth.signInWithPassword = function (cred) { return oSignIn(cred).then(function (r) { ACC.login = { email: cred.email, code: r.error ? String(r.error.code || '') : '', msg: r.error ? String(r.error.message || '') : '' }; return r; }); };
  /* the sign-up form waiting for its e-mail: what happened, to which address, and Resend — on the form itself */
  var aSignup = window.doSignup;
  window.doSignup = async function () {
    ACC.signup = null; var r = await aSignup.apply(this, arguments);
    var s = ACC.signup, er = $('suErr');
    if (s && s.waiting && er) {
      er.innerHTML = '<span>We sent a confirmation link to</span> <b data-noi18n></b><span>. Open it to activate your account, then sign in.</span> <button type="button" class="dx-su-resend">Resend confirmation email</button>';
      er.querySelector('b').textContent = s.email; er.classList.add('dx-auth-info'); er.style.display = 'block';
    } else if (er) er.classList.remove('dx-auth-info');
    return r;
  };
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.dx-su-resend'); if (!b || !ACC.signup) return;
    b.disabled = true; window.dxAccount.resend(ACC.signup.email).then(function () { b.textContent = 'Sent again — check your inbox'; setTimeout(function () { b.disabled = false; b.textContent = 'Resend confirmation email'; }, 20000); },
      function (x) { b.disabled = false; toast((x && x.message) || 'Could not send the email — please try again'); });
  });
  /* sign-in: not confirmed yet → Resend; suspended → said so; wrong → one message, the password keeps the focus */
  var aLogin = window.doLogin;
  window.doLogin = async function () {
    ACC.login = null; var r = await aLogin.apply(this, arguments), l = ACC.login;
    if (l && l.code === 'email_not_confirmed' && window.dxAccountUI) { var er = $('loginErr'); if (er) er.style.display = 'none'; window.dxAccountUI.confirm(l.email, 'login'); }
    else if (l && (l.code === 'user_banned' || /banned/i.test(l.msg))) { var e2 = $('loginErr'); if (e2) { e2.textContent = 'This account is suspended'; e2.style.display = 'block'; } }
    else if (l && l.code && window.dxFocusPw) window.dxFocusPw();
    return r;
  };
  /* after an e-mail link: the app opens signed in (confirmation, new e-mail) or asks for the new password (reset); a used or
     expired link says so on the sign-in page */
  if (LINK && LINK.error) setTimeout(function () { var er = $('loginErr'); if (er && !me()) { er.textContent = 'This link is invalid or has expired — ask for a new one'; er.style.display = 'block'; } }, 1200);
  K.onSignIn(function () {
    sb.auth.getUser().then(function (r) { if (r.data && r.data.user) ACC.email = r.data.user.email || ''; });
    ACC.settings = null; loadSettings().catch(function () {});
    if (LINK && LINK.type) { var t = LINK.type; LINK = null;
      setTimeout(function () { if (t === 'recovery' && window.dxAccountUI) window.dxAccountUI.newPassword();
        else if (t === 'signup') toast('Your email is confirmed — welcome to Drugbox'); else if (t === 'email_change') toast('Your sign-in email was changed'); }, 1500); }
    checkSession();
  });
  /* a session ended elsewhere (password changed, signed out everywhere, account suspended or deleted): this tab signs out too */
  function checkSession() {
    if (!me()) return; sb.auth.getUser().then(function (r) { var e = r.error; if (!e || !me()) return; var st = +e.status || 0;
      if (st === 401 || st === 403 || st === 404 || /session|not found|banned/i.test(String(e.message || ''))) sb.auth.signOut({ scope: 'local' }); }, function () {});
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) checkSession(); });
  setInterval(function () { if (!document.hidden) checkSession(); }, 60000);

  var DEF = { email_messages: true, email_connections: true, email_comments: true, email_mentions: true, email_reactions: false, email_follows: false, email_jobs: true, digest: 'off', show_visits: true, phone_connections: false };
  async function loadSettings() {
    var r = await sb.from('member_settings').select('email_messages,email_connections,email_comments,email_mentions,email_reactions,email_follows,email_jobs,digest,show_visits,phone_connections,lang').eq('user_id', me()).maybeSingle();
    if (r.error) throw r.error; ACC.settings = Object.assign({}, DEF, r.data || {}); return ACC.settings;
  }
  async function saveSettings(o) {
    var row = Object.assign({ user_id: me() }, o), r = await sb.from('member_settings').upsert(row, { onConflict: 'user_id' }).select('user_id');
    if (r.error) throw r.error; ACC.settings = Object.assign({}, ACC.settings || DEF, o);
  }
  /* e-mails come in the interface language: the choice is kept with the settings */
  var LANG_T = null;
  new MutationObserver(function () { if (!me()) return; clearTimeout(LANG_T); LANG_T = setTimeout(function () { var l = document.documentElement.lang === 'ar' ? 'ar' : 'en';
    if (ACC.settings && ACC.settings.lang === l) return; saveSettings({ lang: l }).catch(function () {}); }, 800); }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
  K.onReset(function () { ACC.email = ''; ACC.settings = null; });

  window.dxAccount = {
    live: true,
    email: function () { return ACC.email; },
    forgot: function (email) { return sb.auth.resetPasswordForEmail(email, { redirectTo: home() }).then(function (r) { if (r.error && +r.error.status !== 404) return fail(r.error); return {}; }); },
    resend: function (email) { return sb.auth.resend({ type: 'signup', email: email, options: { emailRedirectTo: home() } }).then(function (r) { if (r.error) return fail(r.error); }); },
    setPassword: async function (pw) {
      var r = await sb.auth.updateUser({ password: pw }); if (r.error) throw new Error(/different from the old/i.test(r.error.message) ? 'The new password must be different from the current one' : friendly(r.error));
      await sb.auth.signOut({ scope: 'others' }).catch(function () {});
    },
    changePassword: async function (cur, next) {
      var v = await sb.rpc('verify_my_password', { p_password: cur }); if (v.error) throw new Error(friendly(v.error)); if (v.data !== true) throw new Error('Your current password is not correct');
      if (cur === next) throw new Error('The new password must be different from the current one');
      var r = await sb.auth.updateUser({ password: next }); if (r.error) throw new Error(/different from the old/i.test(r.error.message) ? 'The new password must be different from the current one' : friendly(r.error));
      await sb.auth.signOut({ scope: 'others' }).catch(function () {});
    },
    changeEmail: async function (e) { var r = await sb.auth.updateUser({ email: e }, { emailRedirectTo: home() }); if (r.error) throw new Error(/already been registered/i.test(r.error.message) ? 'This email cannot be used — choose another' : friendly(r.error)); return {}; },
    settings: function () { return ACC.settings ? Promise.resolve(Object.assign({}, ACC.settings)) : loadSettings(); },
    saveSettings: function (o) { return saveSettings(o).catch(fail); },
    blocked: async function () {
      var r = await sb.from('user_blocks').select('blocked, who:profiles!user_blocks_blocked_fkey(name)').eq('blocker', me()).order('created_at', { ascending: false }).limit(500);
      if (r.error) throw new Error(friendly(r.error)); return (r.data || []).map(function (x) { return { key: x.blocked, name: (x.who && x.who.name) || 'Deleted member' }; });
    },
    unblock: async function (id) { var r = await sb.from('user_blocks').delete().eq('blocker', me()).eq('blocked', id); if (r.error) throw new Error(friendly(r.error)); if (L.loadConvs) L.loadConvs().catch(function () {}); },
    exportData: async function () { var r = await sb.rpc('export_my_data'); if (r.error) throw new Error(friendly(r.error)); return r.data; },
    deleteAccount: async function (pw) {
      var s = await sb.auth.getSession(), tok = s.data && s.data.session && s.data.session.access_token; if (!tok) throw new Error('Your session ended — please sign in again');
      var r = await fetch(CFG.url + '/functions/v1/account-delete', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok, apikey: CFG.anonKey }, body: JSON.stringify({ password: pw, confirm: 'DELETE' }) });
      var j = {}; try { j = await r.json(); } catch (e) {}
      if (!r.ok) throw new Error(j.error || 'Could not delete the account'); return j;
    }
  };
  if (window.dxI18nAdd) window.dxI18nAdd({ 'Sent again — check your inbox': 'أُرسل مرة أخرى — راجع بريدك', 'This email cannot be used — choose another': 'لا يمكن استخدام هذا البريد — اختر غيره',
    'Too many wrong passwords — wait 15 minutes and try again': 'محاولات خاطئة كثيرة — انتظر 15 دقيقة ثم حاول مرة أخرى', 'This account deletion was not confirmed by its member': 'لم يؤكد صاحب الحساب هذا الحذف' });

  /* ===== AREA social: feed — edit, repost, send, replies and comment likes, mentions, hashtags, views (0041) ===== */
  var FD = { rep: [], repAt: 0, loading: false, viewed: {}, vq: [], vt: null };
  function post(id) { return window.dxSocFeed ? window.dxSocFeed.find(id) : null; }
  async function postsFrom(rows) {
    rows = (rows || []).filter(Boolean); rows.forEach(function (x) { K.putUser(x.author); });
    var ps = await K.postState(rows.map(function (x) { return x.id; }));
    return rows.map(function (x) { var p = K.postFrom(x, ps.mine, ps.saved, ps.kinds), f = (window.POSTS || []).find(function (y) { return y.id === p.id; }); return f || p; });
  }
  /* reposts in Home: the newest 20 (anyone's), each with its post — loaded with Home, never more than every 30 s */
  async function loadReposts() {
    var r = await sb.from('reposts').select('note, created_at, user_id, who:profiles!reposts_user_id_fkey(' + K.PCOLS + '), post:posts(' + K.POST_SEL + ')').order('created_at', { ascending: false }).limit(20);
    if (r.error) throw r.error; var rows = (r.data || []).filter(function (x) { return x.post && x.who; });
    rows.forEach(function (x) { K.putUser(x.who); });
    var ps = await postsFrom(rows.map(function (x) { return x.post; }));
    FD.rep = rows.map(function (x, i) { return { pid: x.post.id, post: ps[i], uid: x.user_id === me() ? window.ME.id : L.aid(x.user_id), note: x.note || '', created_at: x.created_at }; });
    FD.repAt = Date.now();
  }
  var gotoFD = window.goto;
  window.goto = function (page) {
    var r = gotoFD.apply(this, arguments);
    if (page === 'feed' && me() && !FD.loading && Date.now() - FD.repAt > 30000) { FD.loading = true;
      loadReposts().then(function () { if (document.body.getAttribute('data-page') === 'feed' && FD.rep.length) K.origGoto('feed'); }, function (e) { console.error(e); }).then(function () { FD.loading = false; }); }
    return r;
  };
  K.onReset(function () { FD.rep = []; FD.repAt = 0; FD.viewed = {}; FD.vq = []; });
  function people(q) {
    return sb.from('profiles').select(K.PCOLS).ilike('name', '%' + String(q).replace(/[\\%_]/g, '\\$&').slice(0, 60) + '%').neq('id', me()).order('name').limit(8).then(function (r) {
      if (r.error) throw new Error(friendly(r.error)); (r.data || []).forEach(function (x) { K.putUser(x); }); var ids = (r.data || []).map(function (x) { return L.aid(x.id); });
      return ids.map(function (a) { return (window.USERS || []).find(function (u) { return u.id === a; }); }).filter(Boolean); });
  }
  function untilSaved(p, ms) { return new Promise(function (ok, no) { var t0 = Date.now(); (function w() { if (typeof p.id === 'number' && p.id < 1e12) return ok(p.id); if (Date.now() - t0 > (ms || 15000)) return no(new Error('The post was not saved')); setTimeout(w, 200); })(); }); }
  window.dxFeedSvc = {
    live: true,
    edit: async function (p, body, cat) {
      var r = await sb.from('posts').update({ body: body, category: cat }).eq('id', p.id).eq('user_id', me()).select('body, category, edited_at');
      if (r.error) throw new Error(friendly(r.error)); if (!(r.data || []).length) throw new Error('Only the author can edit this post');
      p.body = r.data[0].body; p.cat = r.data[0].category; p.edited = !!r.data[0].edited_at; return p;
    },
    repost: async function (p, note) {
      var r = await sb.from('reposts').insert({ user_id: me(), post_id: p.id, note: note || null }).select('created_at').single();
      if (r.error && r.error.code !== '23505') throw new Error(friendly(r.error));
      p.reposted = true; if (!r.error) p.shareCount = (p.shareCount || 0) + 1;
      FD.rep = FD.rep.filter(function (x) { return !(x.pid === p.id && x.uid === window.ME.id); }); FD.rep.unshift({ pid: p.id, post: p, uid: window.ME.id, note: note || '', created_at: r.data ? r.data.created_at : new Date().toISOString() });
    },
    unrepost: async function (p) {
      var r = await sb.from('reposts').delete().eq('user_id', me()).eq('post_id', p.id).select('post_id'); if (r.error) throw new Error(friendly(r.error));
      p.reposted = false; if ((r.data || []).length) p.shareCount = Math.max(0, (p.shareCount || 1) - 1); FD.rep = FD.rep.filter(function (x) { return !(x.pid === p.id && x.uid === window.ME.id); });
    },
    reposts: function () { return FD.rep; },
    people: people,
    send: async function (u, text) { var to = L.uuidOf(u.id); if (!to) throw new Error('Choose a member from the list');
      var r = await sb.from('messages').insert({ sender_id: me(), receiver_id: to, body: text }).select('id'); if (r.error) throw new Error(friendly(r.error)); },
    comment: async function (pid, text, parent) {
      var r = await sb.from('comments').insert({ post_id: pid, user_id: me(), body: text, parent_id: typeof parent === 'number' ? parent : null }).select('id').single();
      if (r.error) throw new Error(friendly(r.error)); return { id: r.data.id };
    },
    likeComment: async function (c, on) { if (typeof c.id !== 'number') throw new Error('Wait a moment — the comment is still being saved');
      var r = on ? await sb.from('comment_reactions').insert({ comment_id: c.id, user_id: me() }) : await sb.from('comment_reactions').delete().eq('comment_id', c.id).eq('user_id', me());
      if (r.error && r.error.code !== '23505') throw new Error(friendly(r.error)); },
    byTag: async function (tag) {
      var r = await sb.from('post_tags').select('post_id, post:posts(' + K.POST_SEL + ')').eq('tag', String(tag).toLowerCase()).order('post_id', { ascending: false }).limit(40);
      if (r.error) throw new Error(friendly(r.error)); return postsFrom((r.data || []).map(function (x) { return x.post; }));
    },
    done: function () { return !!K.FEED.done; },
    mentions: function (p, list) {
      return untilSaved(p).then(function (id) { var rows = list.map(function (m) { return { post_id: id, user_id: L.uuidOf(m.uid) }; }).filter(function (x) { return x.user_id && x.user_id !== me(); });
        if (!rows.length) return; return sb.from('post_mentions').insert(rows).then(function (r) { if (r.error) K.toastErr(r.error); }); }, function () {});
    }
  };
  /* comments: one request with the threads, the like counts and my likes; the approved toggle shows them */
  async function loadComments(id) {
    var r = await sb.from('comments').select('id, post_id, parent_id, body, created_at, like_count, user_id, author:profiles!comments_user_id_fkey(' + K.PCOLS + ')').eq('post_id', id).order('created_at', { ascending: true }).order('id', { ascending: true }).limit(200);
    if (r.error) throw r.error; var rows = r.data || [], ids = rows.map(function (c) { return c.id; });
    var mine = ids.length ? await sb.from('comment_reactions').select('comment_id').eq('user_id', me()).in('comment_id', ids) : { data: [] }, liked = {};
    (mine.data || []).forEach(function (x) { liked[x.comment_id] = 1; });
    rows.forEach(function (c) { K.putUser(c.author); });
    var list = rows.map(function (c) { return { id: c.id, uid: c.user_id === me() ? window.ME.id : L.aid(c.user_id), text: c.body, ts: K.ago(c.created_at), likes: c.like_count || 0, liked: !!liked[c.id], parent: c.parent_id }; });
    Object.defineProperty(list, '__live', { value: true });
    var p = post(id); window.COMMENTS[id] = list;
    if (p) { p.__cmtBase = p.__cmtBase != null ? p.__cmtBase : (p.commentCount || 0); p.commentCount = Math.max(0, p.__cmtBase - list.length); }
    return p;
  }
  window.toggleComments = function (id) {
    var T0 = window.dxSocFeed && window.dxSocFeed.toggle0, box = document.getElementById('cmt-' + id), opening = box && box.style.display === 'none';
    var have = window.COMMENTS[id] && window.COMMENTS[id].__live;
    if (!me() || !opening || have || typeof id !== 'number' || !T0) return T0 ? T0(id) : undefined;
    loadComments(id).then(function (p) { if (p && window.dxRepaintPost) window.dxRepaintPost(p); T0(id); if (window.dxSocFeed) window.dxSocFeed.redraw(id); },
      function (e) { T0(id); K.toastErr(e); });
  };
  window.submitComment = function (id) {
    if (!me() || !window.dxSocFeed) return;
    if (window.dxSocFeed.replyOf(id)) return window.dxSocFeed.submitReply(id);
    var inp = document.getElementById('ci-' + id), text = inp ? inp.value.trim() : ''; if (!text) return;
    window.dxSocFeed.submit(id);
    var list = window.COMMENTS[id] || [], c = list[list.length - 1];
    window.dxFeedSvc.comment(id, text, null).then(function (r) { if (c) { c.id = r.id; window.dxSocFeed.redraw(id); } },
      function (e) { var i = list.indexOf(c); if (i >= 0) list.splice(i, 1); window.dxSocFeed.redraw(id); toast(e.message); if (inp) inp.value = text; });
  };
  /* a post seen on a page counts as one view per member (increment_post_views keeps one row per viewer) */
  function queueViews() {
    if (!me()) return;
    document.querySelectorAll('#content .post[id^="post-"]').forEach(function (el) { var id = +el.id.slice(5); if (!id || id > 1e12 || FD.viewed[id]) return; FD.viewed[id] = 1; FD.vq.push(id); });
    if (!FD.vq.length || FD.vt) return;
    FD.vt = setTimeout(function () { var ids = FD.vq.splice(0, 200); FD.vt = null; sb.rpc('increment_post_views', { post_ids: ids }).then(function (r) { if (r.error) ids.forEach(function (i) { delete FD.viewed[i]; }); }); }, 1500);
  }
  if (window.dxCore) window.dxCore.onRender('live-soc-views', queueViews);
  if (window.dxI18nAdd) window.dxI18nAdd({ 'mentioned you in a post': 'أشار إليك في منشور', 'reposted your post': 'أعاد نشر منشورك', 'Only the author can edit this post': 'لا يعدّل المنشور إلا كاتبه',
    'Wait a moment — the comment is still being saved': 'لحظة — التعليق ما زال يُحفظ', 'The post was not saved': 'لم يُحفظ المنشور' },
    [[/^replied to your comment: (.+)$/, function (m) { return 'ردّ على تعليقك: ' + m[1]; }]]);
})();
