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
})();
