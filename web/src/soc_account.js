/* Account (area social): "Forgot password?" and a new password, e-mail confirmation with Resend, a clear wrong-password message,
   a clean sign-out on a shared computer, a language switch on the sign-in pages, and the Settings page (e-mail, password, language,
   notifications, privacy, blocked members, download my data, delete my account) with the Privacy Policy and Terms (soc_legal.js).
   Data goes through window.dxAccount: the sample implementation below keeps everything in this browser (the demo); the live app
   replaces it with Supabase Auth and the database (web/src/live/social.js). */
(function () {
  var D = window.DBK; if (!D || typeof window.goto !== 'function') return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function ar() { return document.documentElement.lang === 'ar'; }
  function toast(m) { (window.toast || D.toast)(m); }
  function okEmail(e) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(e || '').trim()); }
  var PREF_KEYS = /^dx_(lang|theme|tour_done|flags)$/;

  /* ── the sample implementation (demo): accounts and settings live in this page / browser ── */
  var ACC = { 'haytham@drugbox.app': 'password123' }, CUR = { email: 'haytham@drugbox.app' };
  var DEFAULTS = { email_messages: true, email_connections: true, email_comments: true, email_mentions: true, email_reactions: false, email_follows: false, email_jobs: true, digest: 'off',
                   show_visits: true, phone_connections: false };
  window.dxAccount = window.dxAccount || {
    live: false,
    email: function () { return CUR.email; },
    forgot: function () { return Promise.resolve({ demo: true }); },
    resend: function () { return Promise.resolve({ demo: true }); },
    setPassword: function (pw) { ACC[CUR.email] = pw; return Promise.resolve(); },
    changePassword: function (cur, next) {
      if (ACC[CUR.email] !== cur) return Promise.reject(new Error('Your current password is not correct'));
      if (cur === next) return Promise.reject(new Error('The new password must be different from the current one'));
      ACC[CUR.email] = next; return Promise.resolve();
    },
    changeEmail: function (e) { return Promise.resolve({ demo: true, to: e }); },
    settings: function () { return Promise.resolve(Object.assign({}, DEFAULTS, D.store.get('settings', {}))); },
    saveSettings: function (o) { D.store.set('settings', Object.assign({}, D.store.get('settings', {}), o)); return Promise.resolve(); },
    blocked: function () { var all = D.store.get('mxPrefs', {}); return Promise.resolve(Object.keys(all).filter(function (k) { return all[k].blocked; }).map(function (k) { return { key: k, name: k.replace(/^u\d+$/, 'Member') }; })); },
    unblock: function (key) { var all = D.store.get('mxPrefs', {}); if (all[key]) all[key].blocked = false; D.store.set('mxPrefs', all); return Promise.resolve(); },
    exportData: function () {
      var me = window.ME || {}, mine = (window.POSTS || []).filter(function (p) { return p.uid === me.id; });
      return Promise.resolve({ exported_at: new Date().toISOString(), note: 'Demo: the data this page keeps for the demo account', profile: { name: me.name, headline: me.headline, company: me.company, location: me.location, bio: me.bio, website: me.web, phone: me.phone },
        posts: mine.map(function (p) { return { id: p.id, body: p.body, category: p.cat }; }), saved_posts: (window.SAVED_POSTS || []).map(function (p) { return p.id; }), settings: D.store.get('settings', {}) });
    },
    deleteAccount: function (pw) { if (ACC[CUR.email] !== pw) return Promise.reject(new Error('Your password is not correct')); return Promise.resolve({ demo: true }); }
  };
  function A() { return window.dxAccount; }

  /* ── sign-in page: a wrong password is one clear message (the same for an unknown e-mail), the password keeps the focus ── */
  var WRONG = 'Email or password is incorrect';
  var oLogin = window.doLogin;
  window.doLogin = function () {
    if (!window.dxLive) {                                             /* the demo: only the accounts this page knows, with their password */
      var e = String(($('loginEmail') || {}).value || '').trim().toLowerCase(), p = ($('loginPw') || {}).value || '';
      if (e && p && ACC[e] !== p) { var er = $('loginErr'); er.textContent = WRONG; er.style.display = 'block'; focusPw(); return; }
      if (e && p) CUR.email = e;
    }
    var r = oLogin.apply(this, arguments);
    /* the demo account stays signed in across a reload / a new tab of this browser, until Sign Out (the live app keeps a real session) */
    if (!window.dxLive && CUR.email === 'haytham@drugbox.app' && $('app').getClientRects().length) try { localStorage.setItem('dx_session', '1'); } catch (x) {}
    return r;
  };
  /* demo: a remembered session opens the app as soon as the sign-in page shows; with none, the sign-in page keeps no member data
     (the sample stores other layers create at load belong to nobody yet) */
  (function () {
    var tries = 0, t = setInterval(function () {
      if (window.dxLive && window.dxLive.k && window.dxLive.k.me) return clearInterval(t);
      var lp = $('loginPage'); if (++tries > 600) return clearInterval(t);
      if (!lp || !lp.getClientRects().length || getComputedStyle(lp).visibility === 'hidden') return;
      clearInterval(t); if (window.dxLive) return clearMember();         /* live: signed out, nothing of a member stays in this browser */
      var has = false; try { has = localStorage.getItem('dx_session') === '1'; } catch (x) {}
      if (has) { $('loginEmail').value = 'haytham@drugbox.app'; $('loginPw').value = ACC['haytham@drugbox.app']; window.doLogin(); $('loginEmail').value = ''; $('loginPw').value = ''; }
      else clearMember();
    }, 150);
  })();
  function clearMember() { try { Object.keys(localStorage).forEach(function (k) { if (/^(dx|dbx)_/.test(k) && !PREF_KEYS.test(k)) localStorage.removeItem(k); }); } catch (x) {} }
  function focusPw() { var p = $('loginPw'); if (p) { p.focus(); try { p.select(); } catch (x) {} } }
  window.dxFocusPw = focusPw;
  var oSignup = window.doSignup;
  window.doSignup = function () {
    var e = String(($('suEmail') || {}).value || '').trim().toLowerCase(), p = ($('suPw') || {}).value || '';
    var r = oSignup.apply(this, arguments);
    if (!window.dxLive && e && p.length >= 8 && !ACC[e] && $('app').getClientRects().length) { ACC[e] = p; CUR.email = e; }
    return r;
  };
  /* sign out on a shared computer: the sign-in fields are empty and this browser keeps nothing of the account but the interface
     preferences (language, theme) */
  var oLogout = window.doLogout;
  window.doLogout = function () {
    var r = oLogout.apply(this, arguments);
    ['loginEmail', 'loginPw', 'suName', 'suEmail', 'suPw', 'suCompany'].forEach(function (id) { var f = $(id); if (f) f.value = ''; });
    var er = $('loginErr'); if (er) er.style.display = 'none'; panel(null);
    clearMember(); setTimeout(clearMember, 400);
    return r;
  };

  /* ── the sign-in box shows one of: the sign-in form (approved), "Forgot password?", "Check your e-mail", a farewell ── */
  var box = document.querySelector('#loginPage .auth-form-box');
  function panel(html) {
    if (!box) return null; var p = box.querySelector('.dx-auth-panel');
    if (!html) { if (p) p.remove(); box.classList.remove('dx-auth-alt'); return null; }
    if (!p) { p = document.createElement('div'); p.className = 'dx-auth-panel'; box.appendChild(p); }
    p.innerHTML = html; box.classList.add('dx-auth-alt');
    var f = p.querySelector('input'); if (f) setTimeout(function () { f.focus(); }, 30);
    return p;
  }
  function showLoginPage() { var w = $('authWrap'); if (w) w.style.display = 'block'; var lp = $('loginPage'), sp = $('signupPage'); if (sp) sp.style.display = 'none'; if (lp) lp.style.display = 'grid'; }
  var BACK = '<div class="f-link"><b role="button" tabindex="0" data-auth="back">← Back to sign in</b></div>';
  function forgotPanel() {
    var cur = String(($('loginEmail') || {}).value || '').trim();
    var p = panel('<div class="auth-title">Reset your password</div><div class="auth-sub">Enter the email of your account. We will send you a link to choose a new password.</div>' +
      '<div class="f-error" id="fpErr" role="alert"></div><div class="dx-auth-ok" id="fpOk" role="status"></div>' +
      '<div class="f-field"><label class="f-label" for="fpEmail">Email</label><input class="f-input" id="fpEmail" type="email" autocomplete="email" placeholder="you@company.com" value="' + esc(cur) + '"></div>' +
      '<button class="f-btn" type="button" data-auth="send">Send reset link →</button>' + BACK);
    p.querySelector('#fpEmail').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); sendReset(); } });
  }
  function msg(id, text) { var e = $(id); if (!e) return; e.textContent = text || ''; e.style.display = text ? 'block' : 'none'; }
  function sendReset() {
    var e = String(($('fpEmail') || {}).value || '').trim(), b = box.querySelector('[data-auth="send"]');
    msg('fpErr', ''); msg('fpOk', '');
    if (!okEmail(e)) { msg('fpErr', 'Please enter a valid email'); return; }
    b.disabled = true; b.setAttribute('aria-busy', 'true');
    A().forgot(e).then(function (r) {
      msg('fpOk', 'If an account exists for this email, we sent it a link to choose a new password. Check your inbox and spam folder.' +
        (r && r.demo ? ' (Demo: no email is sent here — password reset works in the live app.)' : ''));
    }, function (err) { msg('fpErr', (err && err.message) || 'Could not send the link — please try again'); })
      .then(function () { b.disabled = false; b.removeAttribute('aria-busy'); });
  }
  /* sign-up or sign-in waiting for the e-mail confirmation: what happened and a Resend button */
  function confirmPanel(email, why) {
    showLoginPage();
    var p = panel('<div class="auth-title">Confirm your email</div><div class="auth-sub">' + (why === 'login' ? '<span>Your email is not confirmed yet.</span> ' : '') +
      '<span>We sent a confirmation link to</span> <b data-noi18n>' + esc(email) + '</b><span>. Open it to activate your account, then sign in.</span></div>' +
      '<div class="f-error" id="cfErr" role="alert"></div><div class="dx-auth-ok" id="cfOk" role="status"></div>' +
      '<button class="f-btn" type="button" data-auth="resend">Resend confirmation email</button>' + BACK);
    p.dataset.email = email;
  }
  function resend() {
    var p = box.querySelector('.dx-auth-panel'), e = p && p.dataset.email, b = box.querySelector('[data-auth="resend"]'); if (!e) return;
    msg('cfErr', ''); msg('cfOk', ''); b.disabled = true;
    A().resend(e).then(function () { msg('cfOk', 'We sent the link again. It can take a minute — check your spam folder too.'); },
      function (err) { msg('cfErr', (err && err.message) || 'Could not send the email — please try again'); }).then(function () { setTimeout(function () { b.disabled = false; }, 20000); });
  }
  function farewell() { showLoginPage(); panel('<div class="auth-title">Your account was deleted</div><div class="auth-sub">Your profile and personal data were removed from Drugbox. We are sorry to see you go — you are welcome back any time.</div>' + BACK); }
  window.dxAccountUI = { confirm: confirmPanel, farewell: farewell, panel: panel, newPassword: newPassword, focusPw: focusPw };
  if (box) box.addEventListener('click', function (e) {
    var t = e.target.closest('[data-auth]'); if (!t) return;
    var a = t.dataset.auth;
    if (a === 'forgot') forgotPanel(); else if (a === 'back') panel(null); else if (a === 'send') sendReset(); else if (a === 'resend') resend();
  });
  document.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('[data-auth][role=button]')) { e.preventDefault(); e.target.click(); } });
  /* "Forgot password?" under the password field (approved login form, one link added) */
  if (box) {
    var pwf = $('loginPw') && $('loginPw').closest('.f-field');
    if (pwf) pwf.insertAdjacentHTML('afterend', '<div class="dx-forgot"><b role="button" tabindex="0" data-auth="forgot">Forgot password?</b></div>');
    /* the sign-in pages have their own language switch (the top bar is not there before sign-in) */
    var lb = document.createElement('button'); lb.type = 'button'; lb.className = 'dx-auth-lang'; lb.setAttribute('data-noi18n', '');
    function paintLang() { lb.textContent = ar() ? 'English' : 'العربية'; lb.setAttribute('lang', ar() ? 'en' : 'ar'); }
    lb.addEventListener('click', function () { if (window.dxSetLang) window.dxSetLang(ar() ? 'en' : 'ar'); paintLang(); });
    box.insertBefore(lb, box.firstChild); paintLang();
    var sbox = document.querySelector('#signupPage > div');
    if (sbox) { var lb2 = lb.cloneNode(true); lb2.addEventListener('click', function () { if (window.dxSetLang) window.dxSetLang(ar() ? 'en' : 'ar'); paintLang(); lb2.textContent = lb.textContent; }); sbox.insertBefore(lb2, sbox.firstChild);
      new MutationObserver(function () { paintLang(); lb2.textContent = lb.textContent; }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] }); }
  }
  /* sign-up: what creating an account means (Terms and Privacy Policy), under the button */
  var sbtn = document.querySelector('#signupPage button.f-btn');
  if (sbtn) sbtn.insertAdjacentHTML('afterend', '<div class="dx-agree">By creating an account you agree to the <a href="#/terms" data-legal="terms">Terms of Use</a> and the <a href="#/privacy" data-legal="privacy">Privacy Policy</a>.</div>');

  /* a new password (the reset link in the live app opens Drugbox signed in with a recovery session): two fields, checked here and saved */
  function newPassword() {
    return D.modal({ title: 'Choose a new password', body: '<p class="gp-muted">Choose a password you do not use anywhere else. Your other devices will be signed out.</p>' +
      '<div class="dbk-f"><label for="npPw1">New password</label><input id="npPw1" type="password" autocomplete="new-password" minlength="8"></div>' +
      '<div class="dbk-f"><label for="npPw2">New password again</label><input id="npPw2" type="password" autocomplete="new-password"></div><div class="dx-set-msg" id="npMsg" role="alert"></div>',
      primary: { label: 'Save new password', onClick: function (bx, close) {
        var a = bx.querySelector('#npPw1').value, b = bx.querySelector('#npPw2').value, m = bx.querySelector('#npMsg');
        var bad = a.length < 8 ? 'Password must be at least 8 characters' : a !== b ? 'The two passwords do not match' : '';
        if (bad) { m.textContent = bad; m.className = 'dx-set-msg err'; return false; }
        A().setPassword(a).then(function () { close(); toast('Your password was changed'); }, function (e) { m.textContent = (e && e.message) || 'Could not save the password'; m.className = 'dx-set-msg err'; });
        return false;
      } } });
  }

  /* ── Settings: a page like Saved (in the side menu, and "Settings" on your own profile) ── */
  if (window.CMS && !window.CMS.icon_settings) window.CMS.icon_settings = '⚙️';
  if (Array.isArray(window.SB_NAV) && !window.SB_NAV.some(function (x) { return x.page === 'settings'; })) window.SB_NAV.push({ page: 'settings', color: '#f1f5f9', key: 'icon_settings', badge: 0, label: 'Settings' });
  if (window.DG_TITLES) { window.DG_TITLES.settings = 'Settings'; window.DG_TITLES.privacy = 'Privacy Policy'; window.DG_TITLES.terms = 'Terms of Use'; }
  var PAGES = { settings: renderSettings, privacy: function (c) { c.innerHTML = '<div class="dx-legal-page">' + window.dxLegal.html('privacy') + '</div>'; }, terms: function (c) { c.innerHTML = '<div class="dx-legal-page">' + window.dxLegal.html('terms') + '</div>'; } };
  window.dxSocialPages = PAGES;                                          /* other social layers add their pages here (tag, …) */
  var oGoto = window.goto;
  window.goto = function (page) {
    var r = oGoto.apply(this, arguments), f = PAGES[page], c = $('content');
    if (f && c) {
      window.curPage = page; f(c, [].slice.call(arguments, 1));
      if (typeof window.dgFooter === 'function') window.dgFooter(c, page);
      document.body.setAttribute('data-page', page); if (typeof window.dxPageA11y === 'function') window.dxPageA11y(c, page);
    }
    return r;
  };
  /* the sidebar footer: Privacy · Terms open the documents */
  (function () {
    var f = document.querySelector('#sidebar .sb-foot'); if (!f) return;
    var tn = [].find.call(f.childNodes, function (n) { return n.nodeType === 3 && /Privacy · Terms ·/.test(n.nodeValue); }); if (!tn) return;
    var span = document.createElement('span'); span.innerHTML = '<a href="#/privacy" data-legal="privacy" class="dx-foot-l">Privacy</a> · <a href="#/terms" data-legal="terms" class="dx-foot-l">Terms</a> · ';
    tn.nodeValue = tn.nodeValue.replace(/Privacy · Terms ·\s*/, ''); f.insertBefore(span, tn);
  })();

  var SECT = { email_messages: 'Messages', email_connections: 'Connection requests and answers', email_comments: 'Comments and replies on my posts', email_mentions: 'Mentions', email_reactions: 'Reactions to my posts', email_follows: 'New followers', email_jobs: 'Jobs and saved-search alerts' };
  function card(id, title, inner, cls) { return '<section class="card dx-set-card' + (cls ? ' ' + cls : '') + '" id="' + id + '" aria-labelledby="' + id + '-h"><h2 id="' + id + '-h">' + title + '</h2>' + inner + '</section>'; }
  function field(id, label, type, extra) { return '<div class="m-field"><label class="m-label" for="' + id + '">' + label + '</label><input class="m-input" id="' + id + '" type="' + type + '"' + (extra || '') + '></div>'; }
  function renderSettings(c) {
    var live = A().live;
    c.innerHTML = '<div class="dx-set"><h1 class="dx-set-title">⚙️ Settings</h1>' +
      card('setAccount', 'Account', '<div class="dx-set-row"><span>Sign-in email</span><b data-noi18n id="setEmailNow">' + esc(A().email() || '') + '</b></div>' +
        '<h3>Change email</h3>' + field('setNewEmail', 'New email', 'email', ' autocomplete="email"') +
        '<button class="btn-p" type="button" data-set="email">Change email</button><div class="dx-set-msg" id="setEmailMsg" role="status"></div>' +
        '<h3>Change password</h3>' + field('setPwCur', 'Current password', 'password', ' autocomplete="current-password"') + field('setPwNew', 'New password', 'password', ' autocomplete="new-password"') +
        field('setPwNew2', 'New password again', 'password', ' autocomplete="new-password"') +
        '<button class="btn-p" type="button" data-set="password">Change password</button><div class="dx-set-msg" id="setPwMsg" role="status"></div>') +
      card('setLang', 'Language', '<div class="dx-set-choice" role="radiogroup" aria-label="Language"><label><input type="radio" name="setLang" value="en"' + (ar() ? '' : ' checked') + '> <span data-noi18n>English</span></label>' +
        '<label><input type="radio" name="setLang" value="ar"' + (ar() ? ' checked' : '') + '> <span data-noi18n>العربية</span></label></div>') +
      card('setNotif', 'Notifications', '<p class="dx-set-sub">Every notification shows in Drugbox. Choose what also comes by email.</p><div id="setNotifList" class="dx-set-list">Loading…</div>' +
        '<div class="m-field"><label class="m-label" for="setDigest">Email summary</label><select class="m-input" id="setDigest"><option value="off">No summary</option><option value="daily">Daily summary</option><option value="weekly">Weekly summary</option></select></div>' +
        '<button class="btn-p" type="button" data-set="notif">Save notification settings</button><div class="dx-set-msg" id="setNotifMsg" role="status"></div>') +
      card('setPrivacy', 'Privacy', '<div class="dx-set-list"><label class="dx-set-tg"><input type="checkbox" id="setShowVisits"> <span>Show my name when I view someone\'s profile</span></label>' +
        '<label class="dx-set-tg"><input type="checkbox" id="setPhoneConn"> <span>Let my connections see my phone number</span></label></div>' +
        '<button class="btn-p" type="button" data-set="privacy">Save privacy settings</button><div class="dx-set-msg" id="setPrivMsg" role="status"></div>') +
      card('setBlocked', 'Blocked members', '<div id="setBlockedList" class="dx-set-list">Loading…</div>') +
      card('setData', 'Your data', '<p class="dx-set-sub">A copy of what Drugbox keeps about you: your profile, posts, comments, connections, messages, saved items, applications and payments.</p>' +
        '<button class="btn-ghost" type="button" data-set="export">Download my data</button><div class="dx-set-msg" id="setDataMsg" role="status"></div>' +
        '<p class="dx-set-sub"><a href="#/privacy" data-legal="privacy">Privacy Policy</a> · <a href="#/terms" data-legal="terms">Terms of Use</a></p>') +
      card('setDelete', 'Delete account', '<p class="dx-set-sub">Your profile is removed and your posts, comments, reactions, connections, follows, saved items, applications and files are deleted. ' +
        'Messages you exchanged stay with the other person as "Deleted member". Payment records are kept as tax law requires, without your name. This cannot be undone.</p>' +
        '<button class="dx-set-danger" type="button" data-set="delete">Delete my account</button>', 'dx-set-dz') +
      (live ? '' : '<p class="dx-set-sub dx-set-demo">Demo: these settings are kept in this browser. In the live app they are saved to your account.</p>') + '</div>';
    A().settings().then(function (s) {
      var l = $('setNotifList'); if (!l) return;
      l.innerHTML = Object.keys(SECT).map(function (k) { return '<label class="dx-set-tg"><input type="checkbox" data-pref="' + k + '"' + (s[k] ? ' checked' : '') + '> <span>' + SECT[k] + '</span></label>'; }).join('');
      var d = $('setDigest'); if (d) d.value = s.digest || 'off';
      var v = $('setShowVisits'); if (v) v.checked = s.show_visits !== false; var ph = $('setPhoneConn'); if (ph) ph.checked = !!s.phone_connections;
    }, function (e) { var l = $('setNotifList'); if (l) l.textContent = (e && e.message) || 'Could not load your settings'; });
    paintBlocked();
  }
  function paintBlocked() {
    A().blocked().then(function (list) {
      var l = $('setBlockedList'); if (!l) return;
      l.innerHTML = list.length ? list.map(function (b) { return '<div class="dx-set-row"><span data-noi18n>' + esc(b.name) + '</span><button class="btn-ghost" type="button" data-unblock="' + esc(b.key) + '">Unblock</button></div>'; }).join('')
        : '<div class="dx-set-sub">You have not blocked anyone.</div>';
    }, function () { var l = $('setBlockedList'); if (l) l.textContent = 'Could not load the list'; });
  }
  function say(id, text, bad) { var e = $(id); if (!e) return; e.textContent = text; e.className = 'dx-set-msg' + (bad ? ' err' : ' ok'); }
  function busy(b, on) { if (!b) return; b.disabled = on; if (on) b.setAttribute('aria-busy', 'true'); else b.removeAttribute('aria-busy'); }
  document.addEventListener('change', function (e) {
    if (e.target && e.target.name === 'setLang' && window.dxSetLang) { window.dxSetLang(e.target.value); }
  });
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#content [data-set], #content [data-unblock]'); if (!t) return;
    if (t.dataset.unblock != null) { busy(t, true); A().unblock(t.dataset.unblock).then(function () { toast('Unblocked'); paintBlocked(); }, function (er) { busy(t, false); toast((er && er.message) || 'Could not unblock'); }); return; }
    var a = t.dataset.set;
    if (a === 'email') {
      var ne = $('setNewEmail').value.trim();
      if (!okEmail(ne)) return say('setEmailMsg', 'Please enter a valid email', true);
      if (ne.toLowerCase() === String(A().email() || '').toLowerCase()) return say('setEmailMsg', 'This is already your email', true);
      busy(t, true);
      A().changeEmail(ne).then(function (r) { $('setNewEmail').value = '';
        say('setEmailMsg', r && r.demo ? 'Demo: in the live app a confirmation link goes to the new address; the email changes only when it is opened.'
          : 'We sent a confirmation link to the new address. Your sign-in email changes only when you open it; your current address was told too.'); },
        function (er) { say('setEmailMsg', (er && er.message) || 'Could not change the email', true); }).then(function () { busy(t, false); });
    } else if (a === 'password') {
      var cur = $('setPwCur').value, n1 = $('setPwNew').value, n2 = $('setPwNew2').value;
      if (!cur) return say('setPwMsg', 'Enter your current password', true);
      if (n1.length < 8) return say('setPwMsg', 'Password must be at least 8 characters', true);
      if (n1 !== n2) return say('setPwMsg', 'The two passwords do not match', true);
      busy(t, true);
      A().changePassword(cur, n1).then(function () { ['setPwCur', 'setPwNew', 'setPwNew2'].forEach(function (id) { $(id).value = ''; }); say('setPwMsg', 'Your password was changed. Your other devices were signed out.'); },
        function (er) { say('setPwMsg', (er && er.message) || 'Could not change the password', true); }).then(function () { busy(t, false); });
    } else if (a === 'notif') {
      var o = { digest: $('setDigest').value }; document.querySelectorAll('#setNotifList [data-pref]').forEach(function (x) { o[x.dataset.pref] = x.checked; });
      busy(t, true); A().saveSettings(o).then(function () { say('setNotifMsg', 'Notification settings saved'); }, function (er) { say('setNotifMsg', (er && er.message) || 'Could not save', true); }).then(function () { busy(t, false); });
    } else if (a === 'privacy') {
      busy(t, true); A().saveSettings({ show_visits: $('setShowVisits').checked, phone_connections: $('setPhoneConn').checked })
        .then(function () { say('setPrivMsg', 'Privacy settings saved'); }, function (er) { say('setPrivMsg', (er && er.message) || 'Could not save', true); }).then(function () { busy(t, false); });
    } else if (a === 'export') {
      busy(t, true); say('setDataMsg', 'Preparing your data…');
      A().exportData().then(function (d) {
        var blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }), u = URL.createObjectURL(blob), l = document.createElement('a');
        l.href = u; l.download = 'drugbox-my-data-' + new Date().toISOString().slice(0, 10) + '.json'; document.body.appendChild(l); l.click(); l.remove(); setTimeout(function () { URL.revokeObjectURL(u); }, 4000);
        say('setDataMsg', 'Your data was downloaded');
      }, function (er) { say('setDataMsg', (er && er.message) || 'Could not prepare your data', true); }).then(function () { busy(t, false); });
    } else if (a === 'delete') deleteDialog();
  });
  function deleteDialog() {
    D.modal({ title: 'Delete your account', body: '<p>This permanently deletes your Drugbox account:</p><ul class="dx-set-ul"><li>your profile, photo, cover and introduction video</li>' +
      '<li>your posts, comments, reactions, saved items, connections and follows</li><li>your applications, CVs and other private files</li></ul>' +
      '<p class="gp-muted">Messages stay with the people you wrote to, as "Deleted member". Payment records are kept as tax law requires, without your name. Company pages you created stay for their other members.</p>' +
      '<div class="dbk-f"><label for="delWord">Type DELETE to confirm</label><input id="delWord" autocomplete="off" spellcheck="false" data-noi18n></div>' +
      '<div class="dbk-f"><label for="delPw">Your password</label><input id="delPw" type="password" autocomplete="current-password"></div><div class="dx-set-msg" id="delMsg" role="alert"></div>',
      primary: { label: 'Delete my account', danger: true, onClick: function (bx, close) {
        var w = bx.querySelector('#delWord').value.trim(), pw = bx.querySelector('#delPw').value, m = bx.querySelector('#delMsg'), ok = bx.querySelector('[data-a=ok]');
        if (!/^(DELETE|حذف)$/i.test(w)) { m.textContent = 'Type DELETE to confirm'; m.className = 'dx-set-msg err'; return false; }
        if (!pw) { m.textContent = 'Enter your password'; m.className = 'dx-set-msg err'; return false; }
        busy(ok, true); m.textContent = 'Deleting…'; m.className = 'dx-set-msg';
        A().deleteAccount(pw).then(function () { close(); return Promise.resolve(typeof window.doLogout === 'function' ? window.doLogout() : null).then(farewell, farewell); },
          function (er) { busy(ok, false); m.textContent = (er && er.message) || 'Could not delete the account'; m.className = 'dx-set-msg err'; });
        return false;
      } } });
  }

  /* own profile: "Settings" beside Edit Profile and Sign Out (two clicks from any page: avatar → Settings) */
  var oProfile = window.renderProfile;
  window.renderProfile = function (c, uid) {
    var r = oProfile.apply(this, arguments);
    if (uid === (window.ME || {}).id && c) { var so = [].find.call(c.querySelectorAll('.profile-info button'), function (b) { return /doLogout/.test(b.getAttribute('onclick') || ''); });
      if (so && !c.querySelector('[data-goto-settings]')) so.insertAdjacentHTML('beforebegin', '<button class="btn-ghost" type="button" data-goto-settings onclick="goto(\'settings\')">Settings</button>'); }
    return r;
  };
  /* phones: the side menu has the language switch too (the top bar's button does not fit at 390 px) */
  (function () {
    var f = document.querySelector('#sidebar .sb-foot'); if (!f) return;
    var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-sb-lang'; b.setAttribute('data-noi18n', '');
    function paint() { b.textContent = ar() ? '🌐 English' : '🌐 العربية'; }
    b.addEventListener('click', function () { if (window.dxSetLang) window.dxSetLang(ar() ? 'en' : 'ar'); paint(); });
    new MutationObserver(paint).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    f.insertBefore(b, f.firstChild); paint();
  })();

  /* "see more" sits inside the post text, which the translator never touches: the link follows the interface language itself */
  if (window.dxCore) window.dxCore.onRender('soc-see-more', function () {
    var want = ar() ? 'عرض المزيد' : 'see more';
    document.querySelectorAll('#content a[data-ep]').forEach(function (a) { if (a.textContent !== want) a.textContent = want; });
  });
  new MutationObserver(function () { var want = ar() ? 'عرض المزيد' : 'see more'; document.querySelectorAll('#content a[data-ep]').forEach(function (a) { if (a.textContent !== want) a.textContent = want; }); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  /* Arabic for everything above (the i18n layer translates it as it appears) */
  if (window.dxI18nAdd) window.dxI18nAdd({
    'Forgot password?': 'نسيت كلمة المرور؟', 'Reset your password': 'إعادة تعيين كلمة المرور', 'Enter the email of your account. We will send you a link to choose a new password.': 'اكتب البريد الإلكتروني لحسابك وسنرسل إليه رابطًا لاختيار كلمة مرور جديدة.',
    'Send reset link →': 'أرسل رابط إعادة التعيين ←', '← Back to sign in': '→ العودة لتسجيل الدخول', 'Please enter a valid email': 'اكتب بريدًا إلكترونيًا صحيحًا',
    'If an account exists for this email, we sent it a link to choose a new password. Check your inbox and spam folder.': 'إذا كان هناك حساب بهذا البريد فقد أرسلنا إليه رابطًا لاختيار كلمة مرور جديدة. راجع صندوق الوارد والرسائل غير المرغوب فيها.',
    'If an account exists for this email, we sent it a link to choose a new password. Check your inbox and spam folder. (Demo: no email is sent here — password reset works in the live app.)': 'إذا كان هناك حساب بهذا البريد فقد أرسلنا إليه رابطًا لاختيار كلمة مرور جديدة. راجع صندوق الوارد والرسائل غير المرغوب فيها. (العرض التجريبي: لا يُرسل بريد هنا — إعادة تعيين كلمة المرور تعمل على التطبيق الحقيقي.)',
    'Could not send the link — please try again': 'تعذّر إرسال الرابط — حاول مرة أخرى', 'Confirm your email': 'أكّد بريدك الإلكتروني', 'Your email is not confirmed yet.': 'لم يتم تأكيد بريدك الإلكتروني بعد.',
    'We sent a confirmation link to': 'أرسلنا رابط التأكيد إلى', '. Open it to activate your account, then sign in.': '. افتحه لتفعيل حسابك ثم سجّل الدخول.', 'Resend confirmation email': 'إعادة إرسال بريد التأكيد',
    'We sent the link again. It can take a minute — check your spam folder too.': 'أرسلنا الرابط مرة أخرى. قد يستغرق دقيقة — راجع الرسائل غير المرغوب فيها أيضًا.', 'Could not send the email — please try again': 'تعذّر إرسال البريد — حاول مرة أخرى',
    'Your account was deleted': 'تم حذف حسابك', 'Your profile and personal data were removed from Drugbox. We are sorry to see you go — you are welcome back any time.': 'أُزيل ملفك وبياناتك الشخصية من Drugbox. يؤسفنا رحيلك — مرحبًا بعودتك في أي وقت.',
    'Email or password is incorrect': 'البريد الإلكتروني أو كلمة المرور غير صحيحة', 'Wrong email or password': 'البريد الإلكتروني أو كلمة المرور غير صحيحة',
    'By creating an account you agree to the': 'بإنشاء حساب فإنك توافق على', 'Terms of Use': 'شروط الاستخدام', 'and the': 'و', 'Privacy Policy': 'سياسة الخصوصية', 'Privacy': 'الخصوصية', 'Terms': 'الشروط',
    'Choose a new password': 'اختر كلمة مرور جديدة', 'Choose a password you do not use anywhere else. Your other devices will be signed out.': 'اختر كلمة مرور لا تستخدمها في أي مكان آخر. سيتم تسجيل خروج أجهزتك الأخرى.',
    'New password': 'كلمة المرور الجديدة', 'New password again': 'كلمة المرور الجديدة مرة أخرى', 'Save new password': 'احفظ كلمة المرور الجديدة', 'Password must be at least 8 characters': 'يجب ألا تقل كلمة المرور عن 8 أحرف',
    'The two passwords do not match': 'كلمتا المرور غير متطابقتين', 'Your password was changed': 'تم تغيير كلمة المرور', 'Could not save the password': 'تعذّر حفظ كلمة المرور',
    'Settings': 'الإعدادات', '⚙️ Settings': '⚙️ الإعدادات', 'Account': 'الحساب', 'Sign-in email': 'بريد تسجيل الدخول', 'Change email': 'تغيير البريد الإلكتروني', 'New email': 'البريد الإلكتروني الجديد',
    'Change password': 'تغيير كلمة المرور', 'Current password': 'كلمة المرور الحالية', 'Language': 'اللغة', 'Every notification shows in Drugbox. Choose what also comes by email.': 'كل الإشعارات تظهر داخل Drugbox. اختر ما يصلك أيضًا بالبريد الإلكتروني.',
    'Email summary': 'ملخص بالبريد', 'No summary': 'بدون ملخص', 'Daily summary': 'ملخص يومي', 'Weekly summary': 'ملخص أسبوعي', 'Save notification settings': 'احفظ إعدادات الإشعارات',
    'Messages': 'الرسائل', 'Connection requests and answers': 'طلبات الاتصال والردود عليها', 'Comments and replies on my posts': 'التعليقات والردود على منشوراتي', 'Mentions': 'الإشارات', 'Reactions to my posts': 'التفاعلات مع منشوراتي',
    'New followers': 'المتابعون الجدد', 'Jobs and saved-search alerts': 'الوظائف وتنبيهات البحث المحفوظ', "Show my name when I view someone's profile": 'أظهر اسمي عندما أزور ملف شخص', 'Let my connections see my phone number': 'اسمح لاتصالاتي برؤية رقم هاتفي',
    'Save privacy settings': 'احفظ إعدادات الخصوصية', 'Blocked members': 'الأعضاء المحظورون', 'You have not blocked anyone.': 'لم تحظر أي شخص.', 'Unblock': 'إلغاء الحظر', 'Unblocked': 'تم إلغاء الحظر', 'Could not unblock': 'تعذّر إلغاء الحظر',
    'Your data': 'بياناتك', 'A copy of what Drugbox keeps about you: your profile, posts, comments, connections, messages, saved items, applications and payments.': 'نسخة مما يحتفظ به Drugbox عنك: ملفك ومنشوراتك وتعليقاتك واتصالاتك ورسائلك ومحفوظاتك وطلبات التوظيف والمدفوعات.',
    'Download my data': 'تنزيل بياناتي', 'Preparing your data…': 'جارٍ تجهيز بياناتك…', 'Your data was downloaded': 'تم تنزيل بياناتك', 'Could not prepare your data': 'تعذّر تجهيز بياناتك',
    'Delete account': 'حذف الحساب', 'Delete my account': 'احذف حسابي', 'Delete your account': 'حذف حسابك',
    'Your profile is removed and your posts, comments, reactions, connections, follows, saved items, applications and files are deleted. Messages you exchanged stay with the other person as "Deleted member". Payment records are kept as tax law requires, without your name. This cannot be undone.':
      'يُزال ملفك وتُحذف منشوراتك وتعليقاتك وتفاعلاتك واتصالاتك ومتابعاتك ومحفوظاتك وطلبات التوظيف وملفاتك. تبقى الرسائل التي تبادلتها لدى الطرف الآخر باسم "عضو محذوف". تُحفظ سجلات الدفع كما يفرض قانون الضرائب دون اسمك. لا يمكن التراجع عن ذلك.',
    'This permanently deletes your Drugbox account:': 'هذا يحذف حسابك في Drugbox نهائيًا:', 'your profile, photo, cover and introduction video': 'ملفك وصورتك وغلافك وفيديو التعريف',
    'your posts, comments, reactions, saved items, connections and follows': 'منشوراتك وتعليقاتك وتفاعلاتك ومحفوظاتك واتصالاتك ومتابعاتك', 'your applications, CVs and other private files': 'طلبات التوظيف والسير الذاتية والملفات الخاصة الأخرى',
    'Messages stay with the people you wrote to, as "Deleted member". Payment records are kept as tax law requires, without your name. Company pages you created stay for their other members.': 'تبقى الرسائل لدى من راسلتهم باسم "عضو محذوف". تُحفظ سجلات الدفع كما يفرض قانون الضرائب دون اسمك. تبقى صفحات الشركات التي أنشأتها لأعضائها الآخرين.',
    'Type DELETE to confirm': 'اكتب DELETE أو حذف للتأكيد', 'Your password': 'كلمة المرور', 'Enter your password': 'اكتب كلمة المرور', 'Deleting…': 'جارٍ الحذف…', 'Could not delete the account': 'تعذّر حذف الحساب',
    'Your password is not correct': 'كلمة المرور غير صحيحة', 'Your current password is not correct': 'كلمة المرور الحالية غير صحيحة', 'The new password must be different from the current one': 'يجب أن تختلف كلمة المرور الجديدة عن الحالية',
    'Enter your current password': 'اكتب كلمة المرور الحالية', 'This is already your email': 'هذا هو بريدك الحالي', 'Could not change the email': 'تعذّر تغيير البريد الإلكتروني', 'Could not change the password': 'تعذّر تغيير كلمة المرور',
    'Demo: in the live app a confirmation link goes to the new address; the email changes only when it is opened.': 'العرض التجريبي: في التطبيق الحقيقي يُرسل رابط تأكيد إلى العنوان الجديد ولا يتغير البريد إلا بعد فتحه.',
    'We sent a confirmation link to the new address. Your sign-in email changes only when you open it; your current address was told too.': 'أرسلنا رابط تأكيد إلى العنوان الجديد. لن يتغير بريد تسجيل الدخول إلا بعد فتحه، وتم إبلاغ عنوانك الحالي أيضًا.',
    'Your password was changed. Your other devices were signed out.': 'تم تغيير كلمة المرور وتسجيل خروج أجهزتك الأخرى.', 'Notification settings saved': 'تم حفظ إعدادات الإشعارات', 'Privacy settings saved': 'تم حفظ إعدادات الخصوصية',
    'Could not save': 'تعذّر الحفظ', 'Could not load your settings': 'تعذّر تحميل إعداداتك', 'Could not load the list': 'تعذّر تحميل القائمة', 'Loading…': 'جارٍ التحميل…',
    'Demo: these settings are kept in this browser. In the live app they are saved to your account.': 'العرض التجريبي: تُحفظ هذه الإعدادات في هذا المتصفح. في التطبيق الحقيقي تُحفظ في حسابك.',
    'see more': 'عرض المزيد', 'Your session ended — please sign in again': 'انتهت الجلسة — سجّل الدخول مرة أخرى',
    'Your email is confirmed — welcome to Drugbox': 'تم تأكيد بريدك الإلكتروني — مرحبًا بك في Drugbox', 'Your sign-in email was changed': 'تم تغيير بريد تسجيل الدخول',
    'This link is invalid or has expired — ask for a new one': 'هذا الرابط غير صالح أو انتهت صلاحيته — اطلب رابطًا جديدًا', 'This account is suspended': 'هذا الحساب موقوف'
  });
})();
