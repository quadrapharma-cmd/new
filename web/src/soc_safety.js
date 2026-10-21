/* Safety (area social, S-09): report a person or one of their comments (with a reason), block or unblock a person from
   their profile (a block covers messages, requests, follows, comments, reactions and mentions — the database enforces it),
   and the Drugbox team's "Reported members" queue in Admin → Review (suspend with a reason, optionally removing their
   posts, or dismiss; every reporter is told). Data goes through window.dxSafetySvc: the sample here, the database in the
   live app (web/src/live/social.js). */
(function () {
  var D = window.DBK; if (!D) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function toast(m) { (window.toast || D.toast)(m); }
  function me() { return window.ME || {}; }
  function U(id) { return window.U ? window.U(id) : {}; }
  var REASONS = [['spam', 'Spam or fake offers'], ['fake', 'Fake profile or impersonation'], ['scam', 'Scam or fraud'], ['abusive', 'Harassment or hate'], ['other', 'Something else']];

  /* ── the sample data source; the live app replaces it ── */
  function prefs() { return D.store.get('mxPrefs', {}) || {}; }
  window.dxSafetySvc = window.dxSafetySvc || {
    live: false,
    report: function (uid, reason, note, comment) {
      var all = D.store.get('memberReports', []) || [];
      if (all.some(function (r) { return r.uid === uid && r.by === me().id && r.open && String(r.cid || '') === String(comment ? comment.id : ''); })) return Promise.resolve('already');
      all.push({ id: Date.now(), uid: uid, by: me().id, reason: reason, note: note, cid: comment ? comment.id : null, text: comment ? comment.text : null, open: true, at: new Date().toISOString() });
      D.store.set('memberReports', all); return Promise.resolve('ok');
    },
    isBlocked: function (uid) { var p = prefs()['u' + uid]; return Promise.resolve(!!(p && p.blocked)); },
    block: function (uid, on) { var all = prefs(), k = 'u' + uid; all[k] = Object.assign({}, all[k], { blocked: !!on }); D.store.set('mxPrefs', all); return Promise.resolve(); },
    queue: function () {
      var by = {}; (D.store.get('memberReports', []) || []).filter(function (r) { return r.open; }).forEach(function (r) {
        var u = U(r.uid), x = by[r.uid] || (by[r.uid] = { id: r.uid, name: u.name || 'Member', headline: u.headline || '', company: u.company || '', reports: 0, reporters: {}, reasons: {}, samples: [], suspended: !!(D.store.get('suspended', {}) || {})[r.uid], posts: (window.POSTS || []).filter(function (p) { return p.uid === r.uid; }).length });
        x.reports++; x.reporters[r.by] = 1; x.reasons[r.reason] = 1; if (r.text || r.note) x.samples.push({ kind: r.cid ? 'comment' : 'member', text: r.text, note: r.note });
      });
      return Promise.resolve(Object.keys(by).map(function (k) { var x = by[k]; x.reporters = Object.keys(x.reporters).length; x.reasons = Object.keys(x.reasons); return x; }));
    },
    decide: function (uid, action, o) {
      uid = +uid; var all = D.store.get('memberReports', []) || [];
      all.forEach(function (r) { if (r.uid === uid && r.open) { r.open = false; r.outcome = action; } }); D.store.set('memberReports', all);
      if (action === 'suspend') { var s = D.store.get('suspended', {}) || {}; s[uid] = (o && o.reason) || ''; D.store.set('suspended', s);
        if (o && o.removePosts && Array.isArray(window.POSTS)) for (var i = window.POSTS.length - 1; i >= 0; i--) if (window.POSTS[i].uid === uid) window.POSTS.splice(i, 1); }
      return Promise.resolve(true);
    }
  };
  function S() { return window.dxSafetySvc; }

  /* ── report a person / a comment ── */
  function reportDialog(uid, comment) {
    var u = U(uid); if (!u || !u.name) return;
    D.modal({ title: comment ? 'Report this comment' : 'Report ' + u.name, body: '<p class="gp-muted">Drugbox reviews every report. ' + (comment ? 'The author' : esc(u.name)) + ' is not told who reported.</p>' +
      (comment ? '<blockquote class="dx-rep-q" data-noi18n>' + esc(String(comment.text || '').slice(0, 300)) + '</blockquote>' : '') +
      REASONS.map(function (r, i) { return '<label class="gp-radio"><input type="radio" name="dxMRep" value="' + r[0] + '"' + (i ? '' : ' checked') + '> <span>' + r[1] + '</span></label>'; }).join('') +
      '<div class="dbk-f"><label for="dxMRepN">Details (optional)</label><textarea id="dxMRepN" maxlength="500" placeholder="What should Drugbox know?"></textarea></div>',
      primary: { label: 'Report', danger: true, onClick: function (bx) {
        var reason = (bx.querySelector('input[name=dxMRep]:checked') || { value: 'other' }).value, note = bx.querySelector('#dxMRepN').value.trim();
        S().report(uid, reason, note, comment || null).then(function (r) { toast(r === 'already' ? 'You already reported this — Drugbox is reviewing it' : 'Thanks — Drugbox will review this report'); },
          function (e) { toast((e && e.message) || 'Could not send the report — try again'); });
      } } });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-crep]'); if (!b) return;
    var pid = b.dataset.crepp, list = (window.COMMENTS || {})[pid] || (window.COMMENTS || {})[+pid] || [], cm = list.find(function (c) { return String(c.id) === String(b.dataset.crep); });
    if (cm) reportDialog(cm.uid, { id: cm.id, text: cm.text });
  });

  /* ── on someone's profile: "⋯" → Report / Block ── */
  function moreMenu() {
    var u = window._profUser; if (document.body.getAttribute('data-page') !== 'profile' || !u || u.id === me().id || u.id < 0) return;
    var msg = document.querySelector('#content [data-mu="' + u.id + '"]'); if (!msg || msg.parentNode.querySelector('.dx-pf-more')) return;
    msg.parentNode.insertAdjacentHTML('beforeend', '<button type="button" class="btn-ghost dx-pf-more" aria-haspopup="menu" aria-expanded="false" aria-label="More: report or block" data-pm="' + u.id + '">⋯</button>');
  }
  if (window.dxCore) window.dxCore.onRender('soc-profile-more', moreMenu);
  function closeMenu() { var m = document.getElementById('dxPfMenu'); if (m) { var b = document.querySelector('.dx-pf-more[aria-expanded=true]'); if (b) b.setAttribute('aria-expanded', 'false'); m.remove(); } }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.dx-pf-more');
    var it = e.target.closest && e.target.closest('#dxPfMenu [data-pma]');
    if (it) { var uid = +it.dataset.uid, a = it.dataset.pma; closeMenu();
      if (a === 'report') reportDialog(uid);
      else if (a === 'block') D.modal({ title: 'Block ' + U(uid).name + '?', body: '<p>They will not be able to message you, send you a connection request, follow you, comment on or react to your posts, or mention you. They are not told.</p>', primary: { label: 'Block', danger: true, onClick: function () {
        S().block(uid, true).then(function () { toast('Blocked — you can unblock in Settings'); }, function (er) { toast((er && er.message) || 'Could not block — try again'); }); } } });
      else if (a === 'unblock') S().block(uid, false).then(function () { toast('Unblocked'); }, function (er) { toast((er && er.message) || 'Could not unblock — try again'); });
      return; }
    if (!b) { if (!(e.target.closest && e.target.closest('#dxPfMenu'))) closeMenu(); return; }
    if (document.getElementById('dxPfMenu')) { closeMenu(); return; }
    var id = +b.dataset.pm;
    S().isBlocked(id).then(function (blocked) {
      b.setAttribute('aria-expanded', 'true');
      var r = b.getBoundingClientRect(), m = document.createElement('div'); m.id = 'dxPfMenu'; m.className = 'dx-pf-menu'; m.setAttribute('role', 'menu');
      m.innerHTML = '<button type="button" role="menuitem" data-pma="report" data-uid="' + id + '">🚩 Report</button><button type="button" role="menuitem" data-pma="' + (blocked ? 'unblock' : 'block') + '" data-uid="' + id + '">' + (blocked ? '✓ Unblock' : '⛔ Block') + '</button>';
      document.body.appendChild(m);
      var rtl = document.documentElement.dir === 'rtl', w = m.offsetWidth;
      m.style.top = (r.bottom + 6 + window.scrollY) + 'px'; m.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, rtl ? r.left : r.right - w)) + 'px';
      var f = m.querySelector('button'); if (f) f.focus();
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && document.getElementById('dxPfMenu')) { var b = document.querySelector('.dx-pf-more[aria-expanded=true]'); closeMenu(); if (b) b.focus(); } });
  document.addEventListener('dx:beforepage', closeMenu);

  /* ── Admin → Review → Reported members ── */
  window.dxSafetyWrapMod = function () {
    var M = window.dxModeration; if (!M || M.__soc) return; M.__soc = true;
    var oLoad = M.load, oDecide = M.decide;
    M.load = function () { return Promise.all([oLoad.apply(M, arguments), S().queue().catch(function () { return []; })]).then(function (a) { var d = a[0] || {}; d.members = a[1] || []; return d; }); };
    M.decide = function (kind, id, value, note) { if (kind === 'members') return S().decide(id, value === 'suspend' ? 'suspend' : 'dismiss', note && typeof note === 'object' ? note : {}); return oDecide.apply(M, arguments); };
  };
  window.dxSafetyWrapMod();

  if (window.dxI18nAdd) window.dxI18nAdd({
    'Report this comment': 'الإبلاغ عن هذا التعليق', 'Spam or fake offers': 'رسائل مزعجة أو عروض وهمية', 'Fake profile or impersonation': 'حساب مزيف أو انتحال شخصية', 'Scam or fraud': 'احتيال أو نصب',
    'Harassment or hate': 'تحرش أو كراهية', 'Something else': 'سبب آخر', 'Details (optional)': 'تفاصيل (اختياري)', 'What should Drugbox know?': 'ما الذي يجب أن يعرفه Drugbox؟', 'Report': 'إبلاغ',
    'Thanks — Drugbox will review this report': 'شكراً — سيراجع Drugbox هذا البلاغ', 'You already reported this — Drugbox is reviewing it': 'سبق أن أبلغت عن هذا — Drugbox يراجعه',
    'Could not send the report — try again': 'تعذر إرسال البلاغ — حاول مرة أخرى', '🚩 Report': '🚩 إبلاغ', '⛔ Block': '⛔ حظر', '✓ Unblock': '✓ إلغاء الحظر', 'Block': 'حظر', 'Unblocked': 'تم إلغاء الحظر',
    'More: report or block': 'المزيد: إبلاغ أو حظر', 'Blocked — you can unblock in Settings': 'تم الحظر — يمكنك إلغاؤه من الإعدادات', 'Could not block — try again': 'تعذر الحظر — حاول مرة أخرى', 'Could not unblock — try again': 'تعذر إلغاء الحظر — حاول مرة أخرى',
    'They will not be able to message you, send you a connection request, follow you, comment on or react to your posts, or mention you. They are not told.': 'لن يستطيع مراسلتك أو إرسال طلب تواصل أو متابعتك أو التعليق أو التفاعل مع منشوراتك أو الإشارة إليك. ولن يُبلَّغ بذلك.',
    'Drugbox reviews every report.': 'يراجع Drugbox كل بلاغ.', 'The author is not told who reported.': 'لا يُبلَّغ الكاتب بمن أبلغ عنه.',
    /* merge: Admin → Review → Reported members in Arabic (S-27) */
    'Reported members': 'الأعضاء المبلغ عنهم', '👤 Reported members': '👤 الأعضاء المبلغ عنهم', 'Suspended': 'موقوف', 'Suspend this account?': 'إيقاف هذا الحساب؟', 'Suspend account': 'إيقاف الحساب',
    'They can no longer post, comment, message, connect or publish listings and jobs, and are told why. Every reporter is told the outcome.': 'لن يستطيع بعد الآن النشر أو التعليق أو المراسلة أو التواصل أو نشر العروض والوظائف، ويُبلَّغ بالسبب. ويُبلَّغ كل من أبلغ بالنتيجة.',
    'Reason (the member sees it)': 'السبب (يراه العضو)', 'Also remove their posts': 'احذف منشوراته أيضًا', 'Nothing changes for the reported member.': 'لا يتغير شيء للعضو المُبلَّغ عنه.'
  }, [[/^(\d+) reports? from (\d+) members? · (.*) · (\d+) posts?$/, function (m) {
        var P = window.dxArPlural || function (n, f) { return f[1]; }, T = window.dxT || function (x) { return x; };
        return m[1] + ' ' + P(+m[1], ['بلاغ', 'بلاغات']) + ' من ' + m[2] + ' ' + P(+m[2], ['عضو', 'أعضاء']) + ' · ' + m[3].split(', ').map(function (r) { return T(r); }).join('، ') + ' · ' + m[4] + ' ' + P(+m[4], ['منشور', 'منشورات']); }],[/^Report (.+)$/, function (m) { return 'الإبلاغ عن ' + m[1]; }], [/^Block (.+)\?$/, function (m) { return 'حظر ' + m[1] + '؟'; }],
      [/^Drugbox reviews every report\. (.+) is not told who reported\.$/, function (m) { return 'يراجع Drugbox كل بلاغ. ' + (m[1] === 'The author' ? 'لا يُبلَّغ الكاتب' : 'لا يُبلَّغ ' + m[1]) + ' بمن أبلغ عنه.'; }]]);
})();
