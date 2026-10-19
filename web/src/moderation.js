/* Admin → Review: the queues for the Drugbox team — verification requests, warning references, site certificates,
   company reports, payments, reported conversations and reported Home posts (feedacts.js; window.dxPostSvc). Data goes through window.dxModeration: demo data in the demo, the database in the live app. */
(function () {
  var D = window.DBK; if (!D) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  /* ── demo source (in-memory decisions; the live adapter replaces this) ── */
  if (!window.dxModeration) {
    var decided = {};
    window.dxModeration = {
      load: function () {
        var cos = (window.dxDir && window.dxDir.companies()) || [], refs = (D.store.get('jobRefs', []) || []), H = window.dxHubData;
        return Promise.resolve({
          reviews: (function () { var meta = (window.dxDir && window.dxDir.store('review_meta')) || {}, rv = (window.dxDir && window.dxDir.store('supplier_reviews')) || {}, out = [];
            Object.keys(rv).forEach(function (slug) { (rv[slug] || []).forEach(function (r) { var m = meta[r.deal] || {}; if (m.disputed && !m.decision && !decided['r' + r.deal]) { var co = window.dxDir.bySlug(slug); out.push({ id: r.deal, company: co ? co.name : slug, from: r.from, stars: r.stars, note: r.note, dispute: '', at: '' }); } }); });
            return out; })(),
          claims: (window.dxClaims ? window.dxClaims.list() : []).filter(function (c) { return c.status === 'pending'; }).map(function (c) { return { id: c.id, company: c.company, who: c.who, role: c.role, mail: c.mail, at: c.at ? new Date(c.at).toISOString().slice(0, 10) : '', docs: [] }; }),
          verifications: cos.filter(function (c) { return c.status === 'pending' && !decided['v' + c.slug]; }).map(function (c) { return { id: c.slug, company: c.name, registry: c.registry || '—', at: '', docs: [] }; }),
          warnings: refs.filter(function (r) { return r.kind === 'warn' && r.status === 'pending' && !decided['w' + r.cand + r.text]; }).map(function (r) { return { id: r.cand + r.text, company: r.company, candidate: r.cand, category: r.category, text: r.text, docs: [] }; }),
          certs: H ? cos.slice(0, 30).reduce(function (a, c) { (H.credentials(c) || []).forEach(function (x) { if (!x.checked && !/^Member:/.test(x.name) && !decided['c' + c.slug + '|' + x.name]) a.push({ id: c.slug + '|' + x.name, company: c.name, site: x.site, name: x.name, expiry: x.expiry }); }); return a; }, []) : [],
          payments: [],
          messages: (D.store.get('mxReports', []) || []).filter(function (r) { return !decided['m' + r.id]; }).map(function (r) { return { id: r.id, reporter: (window.ME && window.ME.name) || 'You', who: r.who, reason: r.reason, details: r.details, at: r.at, excerpt: r.excerpt ? [r.excerpt] : [] }; }),
          reports: H && H.reports ? H.reports().filter(function (r) { return r.status === 'open' && !decided['r' + r.id]; }).map(function (r) { return { id: r.id, company: r.slug, section: r.section, issue: r.text, correction: r.fix }; }) : [],
          posts: window.dxPostSvc && window.dxPostSvc.queue ? window.dxPostSvc.queue() : []
        });
      },
      decide: function (kind, id, value, note) {
        if (kind === 'posts' && window.dxPostSvc && window.dxPostSvc.decide) return window.dxPostSvc.decide(id, value, note);
        if (kind === 'claims' && window.dxClaims) return window.dxClaims.decide(id, value === 'approved', note);
        if (kind === 'reviews' && window.dxDir) { var m = window.dxDir.store('review_meta') || {}; m[id] = Object.assign({}, m[id] || {}, { decision: value }); if (value === 'removed') m[id].hidden = true; window.dxDir.store('review_meta', m); }
        decided[kind.charAt(0) + id] = value; return Promise.resolve(true); },
      link: function () { return Promise.resolve(null); }
    };
  }
  var Q = [['claims', '🏷️', 'Claims'], ['verifications', '🏢', 'Verification requests'], ['warnings', '⚠️', 'Warning references'], ['certs', '📜', 'Site certificates'], ['reports', '🚩', 'Company reports'], ['payments', '💳', 'Payments'], ['reviews', '⭐', 'Reviews'], ['messages', '💬', 'Message reports'], ['posts', '🚩', 'Reported posts']];
  var cur = 'verifications', data = null;
  function docs(list) { return (list || []).map(function (d) { return '<button type="button" class="dx-mod-doc" data-doc="' + esc(d.path) + '" data-bucket="' + esc(d.bucket) + '">📄 ' + esc(d.label) + '</button>'; }).join(''); }
  function row(kind, x) {
    var body = '', acts = '';
    if (kind === 'verifications') { body = '<b data-noi18n>' + esc(x.company) + '</b><span>Commercial registry ' + esc(x.registry) + (x.at ? ' · sent ' + esc(x.at) : '') + '</span>' + docs(x.docs);
      acts = '<button class="dx-mod-ok" data-k="verifications" data-id="' + esc(x.id) + '" data-v="approved">Approve</button><button class="dx-mod-no" data-k="verifications" data-id="' + esc(x.id) + '" data-v="rejected">Reject</button>'; }
    if (kind === 'claims') { body = '<b data-noi18n>' + esc(x.company) + '</b><span>Claimed by ' + esc(x.who || 'a member') + (x.role ? ' · ' + esc(x.role) : '') + (x.mail ? ' · ' + esc(x.mail) : '') + (x.at ? ' · sent ' + esc(x.at) : '') + '</span>' + (x.note ? '<p>' + esc(x.note) + '</p>' : '') + docs(x.docs);
      acts = '<button class="dx-mod-ok" data-k="claims" data-id="' + esc(x.id) + '" data-v="approved">Approve</button><button class="dx-mod-no" data-k="claims" data-id="' + esc(x.id) + '" data-v="rejected">Reject</button>'; }
    if (kind === 'reviews') { body = '<b data-noi18n>' + esc(x.company) + '</b><span>' + '★'.repeat(Math.max(1, Math.min(5, +x.stars || 1))) + ' from ' + esc(x.from || 'a buyer') + (x.at ? ' · asked ' + esc(x.at) : '') + '</span><p>' + esc(x.note || '') + '</p>' + (x.dispute ? '<span>Company: ' + esc(x.dispute) + '</span>' : '');
      acts = '<button class="dx-mod-ok" data-k="reviews" data-id="' + esc(x.id) + '" data-v="kept">Keep review</button><button class="dx-mod-no" data-k="reviews" data-id="' + esc(x.id) + '" data-v="removed">Remove review</button>'; }
    if (kind === 'warnings') { body = '<b data-noi18n>' + esc(x.company) + ' → ' + esc(x.candidate) + '</b><span>' + esc(x.category) + '</span><p>' + esc(x.text) + '</p>' + docs(x.docs);
      acts = '<button class="dx-mod-ok" data-k="warnings" data-id="' + esc(x.id) + '" data-v="published">Publish</button><button class="dx-mod-no" data-k="warnings" data-id="' + esc(x.id) + '" data-v="rejected">Reject</button>'; }
    if (kind === 'certs') { body = '<b data-noi18n>' + esc(x.company) + '</b><span>' + esc(x.name) + ' · ' + esc(x.site || '') + (x.expiry ? ' · valid to ' + esc(x.expiry) : '') + '</span>' + docs(x.docs);
      acts = '<button class="dx-mod-ok" data-k="certs" data-id="' + esc(x.id) + '" data-v="checked">Mark checked</button><button class="dx-mod-no" data-k="certs" data-id="' + esc(x.id) + '" data-v="rejected">Reject</button>'; }
    if (kind === 'reports') { body = '<b>' + esc(x.company) + ' · ' + esc(x.section) + '</b><p>' + esc(x.issue) + '</p>' + (x.correction ? '<span>Suggested: ' + esc(x.correction) + '</span>' : '');
      acts = '<button class="dx-mod-ok" data-k="reports" data-id="' + esc(x.id) + '" data-v="resolved">Resolved</button><button class="dx-mod-no" data-k="reports" data-id="' + esc(x.id) + '" data-v="dismissed">Dismiss</button>'; }
    if (kind === 'payments') { body = '<b>' + esc(x.who) + ' · ' + esc(x.product) + '</b><span>InstaPay transfer ' + esc(x.transfer) + ' · EGP ' + esc(x.amount) + ' · note ' + esc(x.reference) + '</span>' + docs(x.docs);
      acts = '<button class="dx-mod-ok" data-k="payments" data-id="' + esc(x.id) + '" data-v="paid">Confirm payment</button><button class="dx-mod-no" data-k="payments" data-id="' + esc(x.id) + '" data-v="failed">Not received</button>'; }
    if (kind === 'messages') { body = '<b>' + esc(x.reporter) + ' reported ' + esc(x.who) + '</b><span>' + esc(x.reason) + (x.at ? ' · ' + esc(x.at) : '') + '</span>' + (x.details ? '<p>' + esc(x.details) + '</p>' : '') +
        (x.excerpt || []).map(function (m) { return '<p>“' + esc(m) + '”</p>'; }).join('');
      acts = '<button class="dx-mod-ok" data-k="messages" data-id="' + esc(x.id) + '" data-v="actioned">Action taken</button><button class="dx-mod-no" data-k="messages" data-id="' + esc(x.id) + '" data-v="dismissed">Dismiss</button>'; }
    if (kind === 'posts') { var RS = { spam: 'Spam or unrelated ad', counterfeit: 'Unverified or counterfeit product', misleading: 'Misleading information', abusive: 'Harassment or hate', other: 'Something else' };
      body = '<b data-noi18n>' + esc(x.author) + '</b><span>Reported by ' + esc(x.reporter) + (x.n > 1 ? ' and ' + (x.n - 1) + ' more' : '') + ' · ' + esc(RS[x.reason] || x.reason) + (x.at ? ' · ' + esc(x.at) : '') + '</span>' +
        '<p>“' + esc(x.excerpt) + '”</p>' + (x.note ? '<span>' + esc(x.note) + '</span>' : '');
      acts = '<button class="dx-mod-no" data-k="posts" data-id="' + esc(x.id) + '" data-v="removed">Remove post</button><button class="dx-mod-ok" data-k="posts" data-id="' + esc(x.id) + '" data-v="dismissed">Dismiss</button>'; }
    return '<div class="dx-mod-row"><div class="dx-mod-b">' + body + '</div><div class="dx-mod-a">' + acts + '</div></div>';
  }
  function paint(c) {
    if (!data) { c.innerHTML = '<div class="dx-mod"><div class="dx-mod-empty">Loading the review queues…</div></div>'; return; }
    c.innerHTML = '<div class="dx-mod"><div class="dx-mod-h"><h2>Review</h2><span>Decisions here change what everyone sees — verification, published warnings, level 3.</span></div>' +
      '<div class="dx-mod-tabs">' + Q.map(function (q) { var n = (data[q[0]] || []).length; return '<button class="dx-mod-tab' + (q[0] === cur ? ' on' : '') + '" data-q="' + q[0] + '">' + q[1] + ' ' + q[2] + (n ? ' <i>' + n + '</i>' : '') + '</button>'; }).join('') + '</div>' +
      '<div class="dx-mod-list">' + ((data[cur] || []).length ? data[cur].map(function (x) { return row(cur, x); }).join('') : '<div class="dx-mod-empty">Nothing waiting here.</div>') + '</div></div>';
  }
  function open(c) { data = null; paint(c); window.dxModeration.load().then(function (d) { data = d; paint(c); }).catch(function (e) { D.toast && D.toast((e && e.message) || 'Could not load the queues'); }); }
  var oTab = window.renderAdminTab;
  if (typeof oTab === 'function') window.renderAdminTab = function (tab) { if (tab === 'review') { var c = document.getElementById('adminContent'); if (c) open(c); return; } return oTab.apply(this, arguments); };
  var oAdmin = window.renderAdmin;
  if (typeof oAdmin === 'function') window.renderAdmin = function (c) {
    var r = oAdmin.apply(this, arguments), nav = document.querySelector('.admin-nav');
    if (nav && !nav.querySelector('[data-review]')) { nav.insertAdjacentHTML('afterbegin', '<div class="admin-nav-item' + (window.adminTab === 'review' ? ' active' : '') + '" data-review="1" onclick="switchAdminTab(\'review\')">🛡️ Review</div>'); }
    return r;
  };
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-mod-tab, .dx-mod-ok, .dx-mod-no, .dx-mod-doc'); if (!t) return; e.preventDefault();
    var c = document.getElementById('adminContent');
    if (t.classList.contains('dx-mod-tab')) { cur = t.dataset.q; paint(c); return; }
    if (t.classList.contains('dx-mod-doc')) { window.dxModeration.link(t.dataset.doc, t.dataset.bucket).then(function (u) { if (u) window.open(u, '_blank', 'noopener'); else D.toast && D.toast('Documents open in the live app'); }); return; }
    var k = t.dataset.k, id = t.dataset.id, v = t.dataset.v, note = '';
    function go() { t.disabled = true;
      window.dxModeration.decide(k, id, v, note).then(function () { data[k] = (data[k] || []).filter(function (x) { return String(x.id) !== String(id); }); paint(c); D.toast && D.toast('Done'); },
        function (err) { t.disabled = false; D.toast && D.toast((err && err.message) || 'Could not save the decision'); }); }
    if (k === 'posts' && v === 'removed') {   /* the author is told why: an optional note goes with the decision */
      D.modal({ title: 'Remove this post?', body: '<p>The author is told it was removed and why. Every reporter is told the outcome.</p><div class="dbk-f"><label for="dxModNote">Note for the author (optional)</label><textarea id="dxModNote" maxlength="500"></textarea></div>',
        primary: { label: 'Remove post', danger: true, onClick: function (bx) { note = bx.querySelector('#dxModNote').value.trim(); go(); } } }); return; }
    if (v === 'rejected' && (k === 'verifications' || k === 'certs' || k === 'claims')) {   /* the company is told why: the reason is written in the window (Cancel keeps the request) */
      D.modal({ title: k === 'certs' ? 'Reject this certificate?' : k === 'claims' ? 'Reject this claim?' : 'Reject this verification request?', body: '<p>' + (k === 'certs' ? 'It is removed from the page and the company is told why.' : k === 'claims' ? 'The page stays unclaimed and the claimant is told why.' : 'The company is told why and can send new documents.') + '</p><div class="dbk-f"><label for="dxModWhy">Reason for the company (they will see it) *</label><textarea id="dxModWhy" data-req maxlength="300">' + esc(k === 'certs' ? 'The certificate document is not readable' : 'The registry document is not readable') + '</textarea></div>',
        primary: { label: 'Reject', danger: true, onClick: function (bx) { if (!D.requireFields(bx)) return false; note = bx.querySelector('#dxModWhy').value.trim(); go(); } } }); return; }
    if (k === 'reviews' && v === 'removed') { D.modal({ title: 'Remove this review?', body: '<p>It disappears from the company page and from its rating. Both sides are told.</p>', primary: { label: 'Remove review', danger: true, onClick: function () { go(); } } }); return; }
    var ask = { rejected: ['Reject this reference?', 'It will not be published.', 'Reject'], dismissed: ['Dismiss this report?', k === 'posts' ? 'The post stays up.' : 'The company page stays as it is.', 'Dismiss'], failed: ['Mark this transfer as not received?', 'The order stays unpaid.', 'Not received'] }[v];
    if (k === 'messages' && v === 'dismissed') ask = ['Dismiss this report?', 'Nothing changes for the reported member.', 'Dismiss'];
    if (ask) { D.modal({ title: ask[0], body: '<p>' + esc(ask[1]) + '</p>', primary: { label: ask[2], danger: true, onClick: function () { go(); } } }); return; }   /* destructive decisions are confirmed first */
    go();
  });
})();
