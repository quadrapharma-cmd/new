/* ===== AREA community: trust — my own review can be deleted, my own work reference withdrawn, and the records written about
   me (honorable records, warnings) can be read, replied to and a warning disputed (J-COMMUNITY-30 … 33) =====
   The approved Jobs page keeps reviews and references in DBK.store ('jobReviews', 'jobRefs') and draws them; this file adds the
   missing actions to its own windows and writes through the same store. Demo: the store is this browser. Live: the data
   adapter's dxKitHook writes the change to the database (job_reviews, work_references, reply_to_reference) — this file only
   draws. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function T(s) { return s; }   /* the page's translator turns what is drawn into Arabic */
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function meName() { return (window.dxLiveTrust && window.dxLiveTrust.name()) || (D.store.get('user', null) || {}).name || 'Dr. Haytham Dweedar'; }
  function meCo() { return (window.dxLiveTrust && window.dxLiveTrust.company()) || 'Quadra Pharm'; }

  /* demo: the page and this file hold the same objects, so a change here is what the page paints (live: the adapter's store) */
  if (!window.DRUGBOX_CONFIG && !window.dxKitHook) {
    var KEEP = {};
    window.dxKitHook = function (op, k, v) {
      if (k !== 'jobReviews' && k !== 'jobRefs') return undefined;
      if (op === 'get') {
        if (!(k in KEEP)) { var d = k === 'jobRefs' ? [] : {}; try { var s = localStorage.getItem('dbx_' + k); KEEP[k] = s == null ? d : JSON.parse(s); } catch (e) { KEEP[k] = d; } }
        return KEEP[k];
      }
      KEEP[k] = v; try { localStorage.setItem('dbx_' + k, JSON.stringify(v)); } catch (e) {}
      return true;
    };
  }
  function reviews() { return D.store.get('jobReviews', {}); }
  function refs() { return D.store.get('jobRefs', []); }
  function paint() { if (window.dxJxPaint) try { window.dxJxPaint(); } catch (e) { console.error(e); } aboutBtn(); }
  function closeAll() { document.querySelectorAll('.dbk-ov').forEach(function (o) { var x = o.querySelector('.dbk-x'); if (x) x.click(); else o.remove(); }); }
  function topDialog() { var l = document.querySelectorAll('.dbk-ov'); return l.length ? l[l.length - 1] : null; }
  function rowOf(dlg, text) { var hit = null; dlg.querySelectorAll('.jx-rev').forEach(function (r) { var p = r.querySelector('p'); if (!hit && p && txt(p) === String(text).replace(/\s+/g, ' ').trim()) hit = r; }); return hit; }
  function mineRef(r) { return r.mine === undefined ? r.company === meCo() : !!r.mine; }      /* live marks it; the demo only adds my own */
  function aboutMe(r) { return r.aboutMe === undefined ? r.cand === meName() : !!r.aboutMe; }
  function cur(r) { return refs().filter(function (x) { return x === r || (r._id > 0 && x._id === r._id); })[0] || null; }   /* live: the list may have been read again meanwhile */
  function act(label, cls) { return '<button type="button" class="jx-tool ' + cls + '">' + esc(label) + '</button>'; }

  /* ── 1. the ★ rating window: Delete my review ─────────────────────────────────────────────────────────────────── */
  var lastParty = null;
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.jx-rate'); if (!t) return;
    var card = t.closest('.jcard'); lastParty = card ? txt(card.querySelector('.jc-company span')) : null;
    setTimeout(function () {
      var dlg = topDialog(), p = lastParty, mine = p && (reviews()[p] || []).filter(function (r) { return r.mine; })[0]; if (!dlg || !mine) return;
      var row = rowOf(dlg, mine.text); if (!row || row.querySelector('.jx-del-rev')) return;
      var b = document.createElement('div'); b.className = 'jx-own'; b.innerHTML = '<span>' + esc(T('Your review')) + '</span>' + act(T('Delete my review'), 'jx-del-rev'); row.appendChild(b);
      b.querySelector('.jx-del-rev').addEventListener('click', function () {
        D.modal({ title: T('Delete your review?'), body: '<p>' + esc(T('It is removed for everyone and the rating is worked out again. You can write a new one later.')) + '</p>',
          primary: { label: T('Delete'), danger: true, onClick: function () {
            var all = reviews(); all[p] = (all[p] || []).filter(function (r) { return !r.mine; }); D.store.set('jobReviews', all);
            setTimeout(function () { closeAll(); paint(); D.toast(T('Your review is deleted')); }, 0);
          } } });
      });
    }, 60);
  }, true);

  /* ── 2. the Honor / Warning lists: Withdraw my own reference ──────────────────────────────────────────────────── */
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-a="honor-list"], [data-a="warn-list"], .jx-b[data-a="honor"], .jx-b[data-a="warn"]'); if (!t || t.closest('.dbk-ov')) return;
    setTimeout(function () {
      var dlg = topDialog(); if (!dlg) return;
      refs().forEach(function (r) { if (!mineRef(r) || r._id === -1) return; var row = rowOf(dlg, r.text); if (!row || row.querySelector('.jx-wd')) return;
        var b = document.createElement('div'); b.className = 'jx-own'; b.innerHTML = '<span>' + esc(T('Written by you')) + '</span>' + act(T('Withdraw'), 'jx-wd'); row.appendChild(b);
        b.querySelector('.jx-wd').addEventListener('click', function () {
          D.modal({ title: T('Withdraw this reference?'), body: '<p>' + esc(T('It is removed from the person’s profile and from every list. The person is not told.')) + '</p>',
            primary: { label: T('Remove it'), danger: true, onClick: function () {
              var all = refs(), i = all.indexOf(cur(r)); if (i >= 0) all.splice(i, 1); D.store.set('jobRefs', all);
              setTimeout(function () { closeAll(); paint(); D.toast(T('Reference withdrawn')); }, 0);
            } } });
        });
      });
    }, 60);
  }, true);

  /* ── 3. records about me: read, reply, dispute a warning ───────────────────────────────────────────────────────── */
  var STATUS = { pending: 'Pending Drugbox review — only you, the employer and Drugbox see it', published: 'Published', disputed: 'Disputed — Drugbox reviews your reply', rejected: 'Not published by Drugbox' };
  function aboutModal() {
    var list = refs().filter(aboutMe);
    var body = '<div class="jx-legal">' + esc(T('Records that employers wrote about you. Reply to any of them — your reply shows next to it. A warning can be disputed once, before Drugbox decides.')) + '</div>' +
      (list.length ? list.map(function (r, i) {
        var canDispute = r.kind === 'warn' && (r.status === 'pending' || r.status === 'published') && !r.disputed;
        return '<div class="jx-rev" data-i="' + i + '"><div class="jx-rev-h"><span><b>' + (r.kind === 'warn' ? '⚠️ ' + esc(T('Warning')) : '🏅 ' + esc(T('Honorable record'))) + '</b> — <span data-noi18n>' + esc(r.company || '') + '</span></span><span>' + esc(r.from) + ' → ' + esc(r.to) + '</span></div>' +
          '<div style="font-size:12px;color:#64748b;margin-top:2px"><span data-noi18n>' + esc(r.role || '') + '</span>' + (r.category ? ' · ' + esc(r.category) : '') + (r.kind === 'warn' ? ' · ' + esc(T(STATUS[r.status] || r.status)) : '') + '</div>' +
          '<p>' + esc(r.text) + '</p>' + (r.reply ? '<div class="jx-reply"><b>' + esc(T('Your reply:')) + '</b> <span data-noi18n>' + esc(r.reply) + '</span></div>' : '') +
          '<div class="jx-own">' + act(T(r.reply ? 'Edit reply' : 'Reply'), 'jx-ref-reply') + (canDispute ? act(T('Dispute'), 'jx-ref-dispute') : '') + '</div></div>';
      }).join('') : '<div style="padding:14px 0;color:#64748b">' + esc(T('Nothing has been written about you yet.')) + '</div>');
    var m = D.modal({ title: T('📋 About you — work references'), body: body, secondary: 'Close' });
    m.el.addEventListener('click', function (e) {
      var b = e.target.closest('.jx-ref-reply, .jx-ref-dispute'); if (!b) return;
      var r = list[+b.closest('.jx-rev').dataset.i], dispute = b.classList.contains('jx-ref-dispute'); if (r) answer(r, dispute);
    });
  }
  function answer(r, dispute) {
    D.modal({ title: dispute ? T('Dispute this warning') : T('Reply to this record'),
      body: (dispute ? '<p class="jx-legal">' + esc(T('Say what really happened and what proof you have. Drugbox reads your side before deciding; the warning stays hidden from employers while it is disputed.')) + '</p>' : '') +
        '<div class="dbk-f"><label for="jxRefReply">' + esc(T('Your reply * (shown next to the record)')) + '</label><textarea id="jxRefReply" data-req maxlength="2000">' + esc(r.reply || '') + '</textarea></div>',
      primary: { label: dispute ? T('Dispute') : T('Send reply'), onClick: function (bx) {
        var v = bx.querySelector('#jxRefReply').value.trim(); if (v.length < 5) { bx.querySelector('#jxRefReply').classList.add('dbk-err'); D.toast(T('Please write your reply')); return false; }
        var all = refs(), x = cur(r); if (!x) { D.toast(T('This record was withdrawn')); return; } x.reply = v; if (dispute) { x._dispute = true; x.disputed = true; x.status = 'disputed'; } D.store.set('jobRefs', all);
        setTimeout(function () { closeAll(); paint(); D.toast(dispute ? T('Disputed — Drugbox reviews your side before anything is published') : T('Reply saved — it shows next to the record')); aboutModal(); }, 0);
      } } });
  }
  /* the Jobs page offers it while something is written about me */
  function aboutBtn() {
    var any = refs().some(aboutMe);
    document.querySelectorAll('#jx .jx-tools, .jx-tools').forEach(function (t) {
      var b = t.querySelector('.jx-about'); if (!any) { if (b) b.remove(); return; }
      if (!b) { b = document.createElement('button'); b.type = 'button'; b.className = 'jx-tool jx-about'; b.textContent = T('📋 About you'); t.appendChild(b); }
    });
  }
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.jx-about')) aboutModal(); }, true);
  C.onRender('trust-about', function () { if (document.body.getAttribute('data-page') === 'jobs') aboutBtn(); });
  window.dxTrustUI = { aboutMe: function () { aboutBtn(); aboutModal(); } };
})();

/* ===== AREA community: trust — Arabic ===== */
(function () {
  if (!window.dxI18nExtend) return;
  window.dxI18nExtend({
    'Your review': 'تقييمك', 'Delete my review': 'احذف تقييمي', 'Delete your review?': 'هل تحذف تقييمك؟', 'Delete': 'حذف',
    'It is removed for everyone and the rating is worked out again. You can write a new one later.': 'سيُحذف عند الجميع ويُعاد حساب التقييم. يمكنك كتابة تقييم جديد لاحقاً.',
    'Your review is deleted': 'تم حذف تقييمك', 'Written by you': 'كتبتها أنت', 'Withdraw': 'سحب', 'Withdraw this reference?': 'هل تسحب هذه المرجعية؟',
    'It is removed from the person’s profile and from every list. The person is not told.': 'ستُحذف من ملف الشخص ومن كل القوائم. ولن يُبلَّغ الشخص.',
    'Remove it': 'إزالة', 'Reference withdrawn': 'تم سحب المرجعية',
    'Pending Drugbox review — only you, the employer and Drugbox see it': 'قيد مراجعة Drugbox — لا يراه إلا أنت وجهة العمل وDrugbox', 'Published': 'منشور',
    'Disputed — Drugbox reviews your reply': 'معترض عليه — تراجع Drugbox ردّك', 'Not published by Drugbox': 'لم تنشره Drugbox',
    'Records that employers wrote about you. Reply to any of them — your reply shows next to it. A warning can be disputed once, before Drugbox decides.': 'سجلات كتبتها جهات عمل عنك. يمكنك الرد على أي منها — ويظهر ردك بجانبه. ويمكن الاعتراض على التحذير مرة واحدة قبل أن تقرر Drugbox.',
    'Warning': 'تحذير', 'Honorable record': 'سجل مشرف', 'Your reply:': 'ردّك:', 'Edit reply': 'عدّل الرد', 'Reply': 'رد', 'Dispute': 'اعتراض',
    'Nothing has been written about you yet.': 'لم يُكتب عنك شيء بعد.', '📋 About you — work references': '📋 عنك — مرجعيات العمل',
    'Dispute this warning': 'اعترض على هذا التحذير', 'Reply to this record': 'رد على هذا السجل',
    'Say what really happened and what proof you have. Drugbox reads your side before deciding; the warning stays hidden from employers while it is disputed.': 'اذكر ما حدث فعلاً وما لديك من إثبات. تقرأ Drugbox روايتك قبل أن تقرر، ويبقى التحذير مخفياً عن جهات العمل طوال الاعتراض.',
    'Your reply * (shown next to the record)': 'ردّك * (يظهر بجانب السجل)', 'Send reply': 'أرسل الرد', 'Please write your reply': 'اكتب ردّك من فضلك',
    'Disputed — Drugbox reviews your side before anything is published': 'تم الاعتراض — تراجع Drugbox روايتك قبل نشر أي شيء', 'Reply saved — it shows next to the record': 'تم حفظ الرد — يظهر بجانب السجل', 'This record was withdrawn': 'سُحب هذا السجل',
    '📋 About you': '📋 عنك', 'Your company got an anonymous review on Drugbox Jobs': 'حصلت شركتك على تقييم مجهول على وظائف Drugbox',
    'reviewed your company on Drugbox Jobs': 'قيّم شركتك على وظائف Drugbox', 'reviewed you on Drugbox Jobs': 'قيّمك على وظائف Drugbox'
  });
})();
