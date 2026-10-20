/* Admin — the Drugbox team's tools (A-01, A-02; J-COMMUNITY-47 … 50): Users (search, a page at a time, role, the profile badge,
   suspend with a reason / restore), Posts (search, remove with a reason the author is told, restore from the decision log),
   Dashboard numbers, Ticker / Sponsors / Settings saved for everyone. A suspended member is told why when they come in.
   Demo: the approved admin pages' own sample lists, changes kept in this browser. Live: window.dxAdmin (the data adapter) does the
   same against the database; this file only draws, in the approved admin markup (admin-page-hdr, admin-section, admin-table). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function live() { var s = window.dxAdmin; return !!(s && s.live && s.ready && s.ready()); }
  function S() { return live() ? window.dxAdmin : DEMO; }
  function toast(m) { D.toast(m); }
  function content() { return document.getElementById('adminContent'); }
  function day(t) { return t ? String(t).slice(0, 10) : ''; }

  /* ── demo: the approved sample lists; suspensions, roles, badges and removals kept in this browser ─────────────────── */
  function dget(k, d) { return D.store.get(k, d); }
  function dset(k, v) { D.store.set(k, v); }
  var DEMO = {
    live: false,
    users: function (q, off) {
      var sus = dget('admSusp', {}), roles = dget('admRoles', {}), badge = dget('admBadge', {}), Q = String(q || '').toLowerCase();
      var all = (window.USERS || []).filter(function (u) { return !Q || (u.name + ' ' + (u.headline || '') + ' ' + (u.company || '')).toLowerCase().indexOf(Q) >= 0; });
      return Promise.resolve({ total: all.length, rows: all.slice(off || 0, (off || 0) + 50).map(function (u) {
        return { id: String(u.id), name: u.name, headline: u.headline || '', company: u.company || '', role: roles[u.id] || u.role || 'user', verified: u.id in badge ? badge[u.id] : !!u.verified,
                 suspended: !!sus[u.id], reason: sus[u.id] || '', posts: (window.POSTS || []).filter(function (p) { return p.uid === u.id; }).length, me: window.ME && u.id === ME.id }; }) });
    },
    setRole: function (id, role) { var r = dget('admRoles', {}); r[id] = role; dset('admRoles', r); var u = (window.USERS || []).filter(function (x) { return String(x.id) === String(id); })[0]; if (u) u.role = role; return Promise.resolve(); },
    verify: function (id, on) { var b = dget('admBadge', {}); b[id] = !!on; dset('admBadge', b); var u = (window.USERS || []).filter(function (x) { return String(x.id) === String(id); })[0]; if (u) u.verified = !!on; return Promise.resolve(); },
    suspend: function (id, reason) { var s = dget('admSusp', {}); if (s[id]) return Promise.reject(new Error('This account is already suspended')); s[id] = reason; dset('admSusp', s); return Promise.resolve(); },
    unsuspend: function (id) { var s = dget('admSusp', {}); delete s[id]; dset('admSusp', s); return Promise.resolve(); },
    posts: function (q, off) {
      var Q = String(q || '').toLowerCase(), all = (window.POSTS || []).filter(function (p) { var a = window.U ? U(p.uid) : {}; return !Q || ((p.body || '') + ' ' + (a.name || '')).toLowerCase().indexOf(Q) >= 0; });
      return Promise.resolve({ total: all.length, rows: all.slice(off || 0, (off || 0) + 50).map(function (p) { var a = window.U ? U(p.uid) : {};
        return { id: p.id, author: a.name || '', body: p.body || '', cat: p.cat || 'general', likes: p.likeCount || 0, comments: p.commentCount || 0, at: p.ts || '' }; }) });
    },
    removePost: function (id, reason) { var i = (window.POSTS || []).map(function (p) { return p.id; }).indexOf(+id); if (i < 0) return Promise.reject(new Error('This post is already gone'));
      var p = window.POSTS.splice(i, 1)[0], rm = dget('admRemoved', []); rm.unshift({ id: 'rm' + p.id + '_' + Date.now(), post: p, reason: reason, at: new Date().toISOString(), by: (window.ME && ME.name) || 'You' }); dset('admRemoved', rm.slice(0, 50)); return Promise.resolve(); },
    removed: function () { return Promise.resolve(dget('admRemoved', []).map(function (r) { var a = window.U ? U(r.post.uid) : {}; return { id: r.id, author: a.name || '', body: r.post.body || '', reason: r.reason, at: r.at, by: r.by }; })); },
    restore: function (id) { var rm = dget('admRemoved', []), r = rm.filter(function (x) { return x.id === id; })[0]; if (!r) return Promise.reject(new Error('There is no removed post to restore here'));
      if (!(window.POSTS || []).some(function (p) { return p.id === r.post.id; })) window.POSTS.unshift(r.post); dset('admRemoved', rm.filter(function (x) { return x.id !== id; })); return Promise.resolve(); },
    stats: function () { return Promise.resolve({ users: (window.USERS || []).length, posts: (window.POSTS || []).length, enquiries: (window.ENQUIRIES || []).length, companies: (window.COMPANIES || []).length,
      latest: (window.USERS || []).slice(0, 5).map(function (u) { return { name: u.name, company: u.company || '', role: u.role || 'user' }; }) }); },
    mySuspension: function () { return Promise.resolve(null); }
  };

  /* ── Users ─────────────────────────────────────────────────────────────────────────────────────────────────────── */
  var UV = { q: '', off: 0, rows: [], total: 0 };
  function usersPage(c, more) {
    if (!more) { UV.off = 0; UV.rows = []; }
    if (!c.querySelector('.adm-users')) c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">👥 Users <span class="adm-n"></span></div><div class="admin-page-sub">Find a member, change the role, give the profile badge, suspend an account (the member is told why)</div></div>' +
      '<div class="admin-section adm-users" style="margin:0 28px"><div class="adm-find"><input type="search" class="adm-q" placeholder="Search by name, headline or company…" aria-label="Search members" value="' + esc(UV.q) + '"></div>' +
      '<div class="adm-tbl" style="overflow-x:auto"></div><div class="adm-more-w"></div></div>';
    S().users(UV.q, UV.off).then(function (r) {
      UV.total = r.total; UV.rows = UV.rows.concat(r.rows); UV.off = UV.rows.length;
      var box = c.querySelector('.adm-tbl'); if (!box) return;
      c.querySelector('.adm-n').textContent = '(' + UV.total.toLocaleString('en') + ')';
      box.innerHTML = UV.rows.length ? '<table class="admin-table"><thead><tr><th>Name</th><th>Company</th><th>Role</th><th>Verified</th><th>Account</th></tr></thead><tbody>' + UV.rows.map(function (u) {
        return '<tr data-auid="' + esc(u.id) + '"><td><div style="font-size:13.5px;font-weight:700" data-noi18n>' + esc(u.name) + '</div><div style="font-size:11.5px;color:#6b7280" data-noi18n>' + esc(u.headline) + '</div></td>' +
          '<td style="font-size:13px;color:#374151" data-noi18n>' + esc(u.company || '—') + '</td>' +
          '<td><select class="adm-role" aria-label="Role"' + (u.me ? ' disabled' : '') + '>' + [['user', 'Member'], ['moderator', 'Moderator'], ['admin', 'Admin']].map(function (o) { return '<option value="' + o[0] + '"' + (u.role === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select></td>' +
          '<td>' + (u.verified ? '<button type="button" class="adm-link adm-badge" data-on="0"><span style="color:#16a34a">✓ Verified</span> · <span>remove</span></button>' : '<button type="button" class="adm-link adm-badge" data-on="1">Verify</button>') + '</td>' +
          '<td>' + (u.me ? '<span class="adm-muted">You</span>' : u.suspended ? '<span class="adm-sus" title="' + esc(u.reason) + '">⛔ Suspended</span> <button type="button" class="adm-link adm-unsus">Restore</button>'
            : '<span class="adm-ok">Active</span> <button type="button" class="adm-link adm-danger adm-sus-btn">Suspend</button>') + '</td></tr>'; }).join('') + '</tbody></table>'
        : '<div class="dbk-empty">' + (UV.q ? 'No member matches this search.' : 'No members yet.') + '</div>';
      c.querySelector('.adm-more-w').innerHTML = UV.rows.length < UV.total ? '<button type="button" class="btn-ghost adm-more" data-what="users">Load more</button>' : '';
      if (window.dxI18nAdopt) window.dxI18nAdopt(c);
    }, function (e) { toast(e.message); });
  }
  function userRow(el) { var tr = el.closest('tr[data-auid]'); return tr ? UV.rows.filter(function (u) { return u.id === tr.dataset.auid; })[0] : null; }

  /* ── Posts ─────────────────────────────────────────────────────────────────────────────────────────────────────── */
  var PV = { q: '', off: 0, rows: [], total: 0 };
  function postsPage(c, more) {
    if (!more) { PV.off = 0; PV.rows = []; }
    if (!c.querySelector('.adm-posts')) c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">📝 Posts <span class="adm-n"></span></div><div class="admin-page-sub">Remove a post that breaks the rules — its author is told why; a removed post can be restored</div></div>' +
      '<div class="admin-section adm-posts" style="margin:0 28px"><div class="adm-find"><input type="search" class="adm-q" placeholder="Search posts or authors…" aria-label="Search posts" value="' + esc(PV.q) + '"></div>' +
      '<div class="adm-tbl" style="overflow-x:auto"></div><div class="adm-more-w"></div><div class="admin-section-title" style="margin-top:18px">🗑 Removed posts</div><div class="adm-removed"></div></div>';
    S().posts(PV.q, PV.off).then(function (r) {
      PV.total = r.total; PV.rows = PV.rows.concat(r.rows); PV.off = PV.rows.length;
      var box = c.querySelector('.adm-tbl'); if (!box) return;
      c.querySelector('.adm-n').textContent = '(' + PV.total.toLocaleString('en') + ')';
      box.innerHTML = PV.rows.length ? '<table class="admin-table"><thead><tr><th>Author</th><th>Content</th><th>Likes</th><th>Date</th><th>Actions</th></tr></thead><tbody>' + PV.rows.map(function (p) {
        return '<tr data-apid="' + esc(p.id) + '"><td><div style="font-size:13px;font-weight:700" data-noi18n>' + esc(p.author) + '</div></td><td style="max-width:280px"><div style="font-size:13px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis" data-noi18n>' + esc((p.body || '').slice(0, 120)) + '</div></td>' +
          '<td><div style="font-size:13px">' + (p.likes || 0) + '</div></td><td style="font-size:12px;color:#6b7280" data-noi18n>' + esc(day(p.at) || p.at || '') + '</td>' +
          '<td><button type="button" class="adm-link adm-danger adm-rm">Remove</button></td></tr>'; }).join('') + '</tbody></table>'
        : '<div class="dbk-empty">' + (PV.q ? 'No post matches this search.' : 'No posts yet.') + '</div>';
      c.querySelector('.adm-more-w').innerHTML = PV.rows.length < PV.total ? '<button type="button" class="btn-ghost adm-more" data-what="posts">Load more</button>' : '';
      removedList(c);
      if (window.dxI18nAdopt) window.dxI18nAdopt(c);
    }, function (e) { toast(e.message); });
  }
  function removedList(c) {
    S().removed().then(function (list) { var b = c.querySelector('.adm-removed'); if (!b) return;
      b.innerHTML = list.length ? list.map(function (r) { return '<div class="adm-rm-row"><div><b data-noi18n>' + esc(r.author) + '</b> <span class="adm-muted" data-noi18n>' + esc(day(r.at)) + '</span><p data-noi18n>' + esc((r.body || '').slice(0, 160)) + '</p>' +
        '<span class="adm-muted"><span>Reason:</span> <span data-noi18n>' + esc(r.reason || '') + '</span></span></div><button type="button" class="btn-ghost adm-restore" data-rid="' + esc(r.id) + '">↺ Restore</button></div>'; }).join('')
        : '<div class="adm-muted">No removed posts.</div>';
      if (window.dxI18nAdopt) window.dxI18nAdopt(b); }, function () {});
  }

  /* ── Dashboard: real numbers ─────────────────────────────────────────────────────────────────────────────────────── */
  function dashNumbers(c) {
    if (!live()) return;
    var nums = c.querySelectorAll('.admin-section [style*="font-size:32px"]'); nums.forEach(function (n) { n.textContent = '…'; });
    S().stats().then(function (s) {
      [s.users, s.posts, s.enquiries, s.companies].forEach(function (v, i) { if (nums[i]) nums[i].textContent = Number(v || 0).toLocaleString('en'); });
      var list = c.querySelectorAll('.admin-section')[4] || c.querySelector('.admin-section:last-child'), rows = list ? list.querySelectorAll('div[style*="border-bottom"]') : [];
      rows.forEach(function (r, i) { var u = s.latest[i]; if (!u) { r.style.display = 'none'; return; } var n = r.querySelector('div[style*="font-weight:700"]'), co = r.querySelector('div[style*="color:#6b7280"]');
        if (n) n.textContent = u.name; if (co) co.textContent = u.company || ''; var av = r.firstElementChild; if (av && av.textContent.length <= 3) av.textContent = (u.name || '?').split(/\s+/).map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase(); });
    }, function (e) { toast(e.message); });
  }

  /* ── Ticker / Sponsors / Settings: kept for everyone in the live app ─────────────────────────────────────────────── */
  function tickerPage(c) {
    if (!live()) return false;
    c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">📢 Ticker</div><div class="admin-page-sub">Manage the scrolling news ticker — everyone sees it on their next page</div></div>' +
      '<div class="admin-section" style="margin:0 28px"><div id="tickerList"><div class="adm-muted">Loading…</div></div><div class="admin-add-row">' +
      '<select id="tkLabel" style="height:38px;border:1.5px solid #e5e7eb;border-radius:9px;padding:0 10px;font-size:13px;outline:none;background:#fff">' + ['Supply', 'Demand', 'CMO', 'Job', 'License', 'Deal', 'Equipment', 'News'].map(function (x) { return '<option>' + x + '</option>'; }).join('') + '</select>' +
      '<input id="tkText" placeholder="Ticker item text..." maxlength="200"><button class="admin-add-btn adm-tk-add" type="button">+ Add</button></div></div>';
    window.dxAdmin.ticker().then(function (l) { var b = c.querySelector('#tickerList'); if (!b) return;
      b.innerHTML = l.length ? l.map(function (t) { return '<div class="admin-ticker-item" data-tkid="' + t.id + '"' + (t.active ? '' : ' style="opacity:.55"') + '><span class="ticker-label-badge">' + esc(t.label) + '</span><span style="flex:1;font-size:13.5px" data-noi18n>' + esc(t.text) + '</span>' +
        '<button type="button" class="adm-link adm-tk-on" data-on="' + (t.active ? 0 : 1) + '">' + (t.active ? 'Hide' : 'Show') + '</button> <button type="button" style="border:none;background:#fee2e2;color:#dc2626;padding:4px 10px;border-radius:7px;cursor:pointer;font-size:12px;font-weight:700" class="adm-tk-del">Delete</button></div>'; }).join('')
        : '<div class="adm-muted">No items yet — the ticker shows the newest listings and jobs.</div>';
      if (window.dxI18nAdopt) window.dxI18nAdopt(c); }, function (e) { toast(e.message); });
    return true;
  }
  function sponsorsPage(c) {
    var lv = live();
    (lv ? window.dxAdmin.sponsors() : Promise.resolve((window.SPONSORS || []).map(function (s, i) { return { id: i, name: s.name, description: s.desc, logo_emoji: s.logo, color: s.color, active: true }; }))).then(function (l) {
      c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">🏭 Sponsored Suppliers</div><div class="admin-page-sub">Manage Market Board sidebar sponsors</div></div>' +
        '<div class="admin-section" style="margin:0 28px">' + (l.length ? l.map(function (s) { return '<div style="display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid #f3f4f6" data-spid="' + s.id + '">' +
          '<div style="width:48px;height:48px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:24px;background:' + esc(s.color || '#eef2ff') + '">' + esc(s.logo_emoji || '🏭') + '</div>' +
          '<div style="flex:1"><div style="font-size:14px;font-weight:700;color:#111827" data-noi18n>' + esc(s.name) + '</div><div style="font-size:12.5px;color:#6b7280" data-noi18n>' + esc(s.description || '') + '</div></div>' +
          '<button class="btn-ghost adm-sp-del" type="button" style="font-size:12px;padding:5px 12px;color:#dc2626;border-color:#fca5a5">Remove</button></div>'; }).join('') : '<div class="adm-muted">No sponsors yet.</div>') +
        '<div style="margin-top:16px"><button class="btn-p adm-sp-add" type="button">+ Add Sponsor</button></div></div>';
      if (window.dxI18nAdopt) window.dxI18nAdopt(c);
    }, function (e) { toast(e.message); });
    return true;
  }
  function sponsorForm() {
    D.modal({ title: 'Add a sponsor', body: '<div class="dbk-f"><label for="spN">Name *</label><input id="spN" data-req maxlength="120"></div><div class="dbk-f"><label for="spD">Description</label><input id="spD" maxlength="200"></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="spE">Icon</label><input id="spE" maxlength="4" value="🏭"></div><div class="dbk-f"><label for="spC">Colour</label><input id="spC" type="color" value="#dbeafe"></div></div>',
      primary: { label: 'Add sponsor', onClick: function (bx, close) { if (!D.requireFields(bx)) return false;
        var o = { name: bx.querySelector('#spN').value.trim(), description: bx.querySelector('#spD').value.trim(), logo_emoji: bx.querySelector('#spE').value.trim() || '🏭', color: bx.querySelector('#spC').value };
        (live() ? window.dxAdmin.addSponsor(o) : Promise.resolve((window.SPONSORS = window.SPONSORS || []).push({ name: o.name, desc: o.description, logo: o.logo_emoji, color: o.color })))
          .then(function () { close(); toast('Sponsor added'); sponsorsPage(content()); }, function (e) { toast(e.message); }); return false; } } });
  }

  /* ── the admin tabs: Users, Posts and the live versions of Dashboard / Ticker / Sponsors / Settings ─────────────── */
  var oTab = window.renderAdminTab;
  if (typeof oTab === 'function') window.renderAdminTab = function (tab) {
    var c = content();
    if (c && tab === 'users') { UV.q = ''; c.innerHTML = ''; usersPage(c); return; }
    if (c && tab === 'posts') { PV.q = ''; c.innerHTML = ''; postsPage(c); return; }
    if (c && tab === 'ticker' && tickerPage(c)) return;
    if (c && tab === 'sponsors' && sponsorsPage(c)) return;
    var r = oTab.apply(this, arguments);
    if (c && tab === 'dashboard') dashNumbers(c);
    if (c && tab === 'settings' && live()) settingsLive(c);
    return r;
  };
  function settingsLive(c) {
    var b = c.querySelector('.admin-save-btn'); if (!b) return;
    b.removeAttribute('onclick'); b.classList.add('adm-set-save');
  }

  /* ── clicks and typing ──────────────────────────────────────────────────────────────────────────────────────────── */
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.adm-badge,.adm-sus-btn,.adm-unsus,.adm-more,.adm-rm,.adm-restore,.adm-tk-add,.adm-tk-del,.adm-tk-on,.adm-sp-add,.adm-sp-del,.adm-set-save'); if (!t) return;
    e.preventDefault(); e.stopPropagation(); var c = content(), u = userRow(t);
    if (t.classList.contains('adm-more')) { if (t.dataset.what === 'users') usersPage(c, true); else postsPage(c, true); return; }
    if (t.classList.contains('adm-badge')) { S().verify(u.id, t.dataset.on === '1').then(function () { toast(t.dataset.on === '1' ? u.name + ' is verified ✓' : 'Badge removed'); usersPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-unsus')) { S().unsuspend(u.id).then(function () { toast(u.name + ' can use Drugbox again'); usersPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-sus-btn')) {
      D.modal({ title: 'Suspend ' + u.name + '?', body: '<p>They cannot post, comment, message, connect or list anything until you restore the account. They see the reason when they come in.</p>' +
        '<div class="dbk-f"><label for="admSusR">Reason *</label><textarea id="admSusR" data-req maxlength="500" placeholder="e.g. Fake profile — impersonates a company employee"></textarea></div>',
        primary: { label: 'Suspend', danger: true, onClick: function (bx, close) { if (!D.requireFields(bx)) return false;
          S().suspend(u.id, bx.querySelector('#admSusR').value.trim()).then(function () { close(); toast(u.name + ' is suspended'); usersPage(c); }, function (er) { toast(er.message); }); return false; } } }); return; }
    if (t.classList.contains('adm-rm')) { var id = t.closest('tr').dataset.apid;
      D.modal({ title: 'Remove this post?', body: '<p>It disappears for everyone. The author is told the reason. You can restore it below.</p><div class="dbk-f"><label for="admRmR">Reason *</label><textarea id="admRmR" data-req maxlength="500"></textarea></div>',
        primary: { label: 'Remove post', danger: true, onClick: function (bx, close) { if (!D.requireFields(bx)) return false;
          S().removePost(id, bx.querySelector('#admRmR').value.trim()).then(function () { close(); toast('Post removed — its author is told'); postsPage(c); }, function (er) { toast(er.message); }); return false; } } }); return; }
    if (t.classList.contains('adm-restore')) { t.disabled = true; S().restore(t.dataset.rid).then(function () { toast('Post restored'); postsPage(c); }, function (er) { t.disabled = false; toast(er.message); }); return; }
    if (t.classList.contains('adm-tk-add')) { var tx = document.getElementById('tkText'), lb = document.getElementById('tkLabel'); if (!tx.value.trim()) { toast('Enter ticker text'); return; }
      window.dxAdmin.addTicker(lb.value, tx.value.trim()).then(function () { toast('Ticker item added!'); tickerPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-tk-del')) { window.dxAdmin.delTicker(+t.closest('[data-tkid]').dataset.tkid).then(function () { toast('Deleted'); tickerPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-tk-on')) { window.dxAdmin.showTicker(+t.closest('[data-tkid]').dataset.tkid, t.dataset.on === '1').then(function () { tickerPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-sp-add')) { sponsorForm(); return; }
    if (t.classList.contains('adm-sp-del')) { var sid = t.closest('[data-spid]').dataset.spid;
      (live() ? window.dxAdmin.delSponsor(+sid) : Promise.resolve(window.SPONSORS.splice(+sid, 1))).then(function () { toast('Sponsor removed'); sponsorsPage(c); }, function (er) { toast(er.message); }); return; }
    if (t.classList.contains('adm-set-save')) { var n = document.getElementById('sSiteName').value.trim(), g = document.getElementById('sSiteTag').value.trim();
      window.dxAdmin.saveSettings({ site_name: n, site_tagline: g }).then(function () { window.CMS.site_name = n; window.CMS.site_tagline = g; if (window.applyCMS) window.applyCMS(); toast('Settings saved! ✅'); }, function (er) { toast(er.message); }); return; }
  }, true);
  document.addEventListener('change', function (e) {
    var s = e.target.closest && e.target.closest('.adm-role'); if (!s) return; var u = userRow(s), was = u.role;
    S().setRole(u.id, s.value).then(function () { u.role = s.value; toast(u.name + ' is now ' + ({ user: 'a member', moderator: 'a moderator', admin: 'an admin' })[s.value]); }, function (er) { s.value = was; toast(er.message); });
  }, true);
  document.addEventListener('input', function (e) {
    var q = e.target.closest && e.target.closest('.adm-q'); if (!q) return; var c = content();
    clearTimeout(q.__t); q.__t = setTimeout(function () { if (q.closest('.adm-users')) { UV.q = q.value.trim(); usersPage(c); } else { PV.q = q.value.trim(); postsPage(c); } }, 300);
  }, true);

  /* ── a suspended member is told why, once per visit ─────────────────────────────────────────────────────────────── */
  var told = false;
  window.dxAdminSuspended = function (reason) {
    if (told || !reason) return; told = true;
    D.modal({ title: '⛔ Your account is suspended', secondary: 'Close', body: '<p>Drugbox suspended this account. You can still read, but you cannot post, comment, message, connect or list anything.</p>' +
      '<p class="adm-reason"><b>Reason:</b> <span data-noi18n>' + esc(reason) + '</span></p><p class="adm-muted">If you think this is a mistake, write to support@drugbox.app.</p>' });
  };

  /* ── My reports: the wrong-information reports I sent and what Drugbox decided (J-COMMUNITY-43) ─────────────────── */
  function myReports() { var H = window.dxHubData, me = (window.ME || {}).name; return H && H.reports ? (H.reports() || []).filter(function (r) { return r.by && r.by === me; }) : []; }
  function coName(slug) { var c = window.dxDir && window.dxDir.bySlug ? window.dxDir.bySlug(slug) : null; return (c && c.name) || slug || ''; }
  function paintMyReports() {
    var b = document.querySelector('#content [data-hreport]'); if (!b) return;
    var n = myReports().length, x = b.parentNode.querySelector('.adm-myrep');
    if (!n) { if (x) x.remove(); return; }
    if (!x) { x = document.createElement('button'); x.type = 'button'; x.className = 'dr-link adm-myrep'; b.insertAdjacentElement('afterend', x); }
    x.textContent = '🚩 My reports (' + n + ')';
  }
  document.addEventListener('click', function (e) {
    var x = e.target.closest && e.target.closest('.adm-myrep'); if (!x) return; e.preventDefault(); e.stopPropagation();
    var ST = { open: '🟡 Open', resolved: '✅ Corrected', dismissed: '⚪ Checked — no change' };
    var rows = myReports().map(function (r) { return '<div class="adm-rm-row"><div><b data-noi18n>' + esc(coName(r.slug)) + '</b> · <span>' + esc(r.section || '') + '</span><p data-noi18n>' + esc(r.text || '') + '</p>' +
      (r.fix ? '<span class="adm-muted"><span>Suggested:</span> <span data-noi18n>' + esc(r.fix) + '</span></span>' : '') + '</div><span class="adm-st">' + esc(ST[r.status] || r.status) + '</span></div>'; }).join('');
    var m = D.modal({ title: '🚩 My reports', secondary: 'Close', body: rows || '<div class="dbk-empty">You have not reported anything yet.</div>' }); if (window.dxI18nAdopt) window.dxI18nAdopt(m.el);
  }, true);
  C.onRender('admin-my-reports', function () { setTimeout(paintMyReports, 0); });
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('.dbk-ov [data-a=ok]')) setTimeout(paintMyReports, 900); }, true);

  /* ── demo: notifications stay read after a reload (the live app keeps them in the database) ─────────────────────── */
  if (!window.DRUGBOX_CONFIG && !window.dxLive) {   /* the demo build only (the live build carries its configuration) */
    var readIds = function () { return dget('notifRead', []); };
    var apply = function () { var r = readIds(), all = dget('notifAllRead', false); (window.NOTIFS || []).forEach(function (n) { if (all || r.indexOf(n.id) >= 0) n.read = true; }); if (window.updateBadges) window.updateBadges();
      if (all && !(window.NOTIFS || []).some(function (n) { return !n.read; })) ['nb-not'].forEach(function (id) { var b = document.getElementById(id); if (b) { b.style.display = 'none'; b.textContent = ''; } });   /* hidden as markAllRead leaves it, and no count left behind */ };
    var oRead = window.markNotifRead, oAll = window.markAllRead;
    if (typeof oRead === 'function') window.markNotifRead = function (id) { var r = readIds(); if (r.indexOf(id) < 0) { r.push(id); dset('notifRead', r.slice(-500)); } return oRead.apply(this, arguments); };
    if (typeof oAll === 'function') window.markAllRead = function () { dset('notifAllRead', true); var r = oAll.apply(this, arguments); if (window.updateBadges) window.updateBadges(); return r; };
    apply(); setTimeout(apply, 0); C.onRender('admin-notif-read', apply);
  }
})();

/* ===== AREA community: admin — Arabic ===== */
(function () {
  if (!window.dxI18nExtend) return;
  window.dxI18nExtend({
    'Find a member, change the role, give the profile badge, suspend an account (the member is told why)': 'ابحث عن عضو، غيّر الدور، امنح شارة التوثيق، أوقف حساباً (ويُبلَّغ العضو بالسبب)',
    'Search by name, headline or company…': 'ابحث بالاسم أو المسمى أو الشركة…', 'Search members': 'ابحث في الأعضاء', 'Account': 'الحساب', 'Member': 'عضو', 'Moderator': 'مشرف', 'Admin': 'مدير',
    'Verify': 'توثيق', '✓ Verified': '✓ موثّق', 'remove': 'إزالة', 'You': 'أنت', '⛔ Suspended': '⛔ موقوف', 'Restore': 'استعادة', 'Active': 'نشط', 'Suspend': 'إيقاف', 'Load more': 'تحميل المزيد',
    'No member matches this search.': 'لا يوجد عضو مطابق.', 'No members yet.': 'لا يوجد أعضاء بعد.', 'Remove a post that breaks the rules — its author is told why; a removed post can be restored': 'احذف المنشور المخالف — يُبلَّغ كاتبه بالسبب؛ ويمكن استعادة المنشور المحذوف',
    'Search posts or authors…': 'ابحث في المنشورات أو الكتّاب…', 'Search posts': 'ابحث في المنشورات', '🗑 Removed posts': '🗑 المنشورات المحذوفة', 'Author': 'الكاتب', 'Content': 'المحتوى', 'Likes': 'الإعجابات', 'Date': 'التاريخ', 'Actions': 'الإجراءات',
    'Remove': 'حذف', 'No post matches this search.': 'لا يوجد منشور مطابق.', 'No posts yet.': 'لا توجد منشورات بعد.', 'Reason:': 'السبب:', '↺ Restore': '↺ استعادة', 'No removed posts.': 'لا توجد منشورات محذوفة.',
    'Manage the scrolling news ticker — everyone sees it on their next page': 'إدارة شريط الأخبار — يراه الجميع في صفحتهم التالية', 'Hide': 'إخفاء', 'Show': 'إظهار', 'Delete': 'حذف',
    'No items yet — the ticker shows the newest listings and jobs.': 'لا توجد عناصر بعد — يعرض الشريط أحدث الإعلانات والوظائف.', 'No sponsors yet.': 'لا يوجد رعاة بعد.', 'Add a sponsor': 'إضافة راعٍ', 'Name *': 'الاسم *',
    'Description': 'الوصف', 'Icon': 'الأيقونة', 'Colour': 'اللون', 'Add sponsor': 'إضافة الراعي', 'Sponsor added': 'تمت إضافة الراعي', 'Sponsor removed': 'تم حذف الراعي',
    'They cannot post, comment, message, connect or list anything until you restore the account. They see the reason when they come in.': 'لن يستطيع النشر أو التعليق أو المراسلة أو التواصل أو نشر أي إعلان حتى تستعيد الحساب. وسيرى السبب عند دخوله.',
    'Reason *': 'السبب *', 'e.g. Fake profile — impersonates a company employee': 'مثال: حساب مزيّف — ينتحل صفة موظف في شركة', 'Remove this post?': 'حذف هذا المنشور؟',
    'It disappears for everyone. The author is told the reason. You can restore it below.': 'سيختفي عند الجميع. يُبلَّغ الكاتب بالسبب. ويمكنك استعادته من الأسفل.', 'Remove post': 'حذف المنشور',
    'Post removed — its author is told': 'تم حذف المنشور — وأُبلغ كاتبه', 'Post restored': 'تمت استعادة المنشور', 'Badge removed': 'أُزيلت الشارة', 'Enter ticker text': 'اكتب نص الشريط',
    '⛔ Your account is suspended': '⛔ حسابك موقوف', 'Drugbox suspended this account. You can still read, but you cannot post, comment, message, connect or list anything.': 'أوقفت Drugbox هذا الحساب. يمكنك القراءة، لكن لا يمكنك النشر أو التعليق أو المراسلة أو التواصل أو نشر أي إعلان.',
    'If you think this is a mistake, write to support@drugbox.app.': 'إذا كنت ترى أن هذا خطأ، راسل support@drugbox.app.',
    '🚩 My reports': '🚩 بلاغاتي', 'Your claim is under review — Drugbox checks it and tells you within 2 working days': 'مطالبتك قيد المراجعة — تتحقق منها Drugbox وتبلغك خلال يومي عمل', 'Suggested:': 'المقترح:', '🟡 Open': '🟡 مفتوح', '✅ Corrected': '✅ تم التصحيح', '⚪ Checked — no change': '⚪ تم الفحص — بلا تغيير', 'You have not reported anything yet.': 'لم تبلّغ عن شيء بعد.',
    /* Review (0063) */
    '📝 Content reports': '📝 بلاغات المحتوى', 'Content reports': 'بلاغات المحتوى', '🗂 Decided': '🗂 تم البت', 'Decided': 'تم البت', 'Search this queue…': 'ابحث في هذه القائمة…', 'Search this queue': 'ابحث في هذه القائمة',
    'Claim by': 'مطالبة من', 'The candidate replied:': 'ردّ المرشح:', ' · ⚖️ Disputed': ' · ⚖️ معترض عليه', '↺ Undo': '↺ تراجع', '↺ Restore post': '↺ استعادة المنشور', 'by': 'بواسطة', 'undone': 'تم التراجع',
    'Nothing matches this search.': 'لا يوجد ما يطابق البحث.', 'No decisions yet.': 'لا توجد قرارات بعد.', 'Reject this certificate?': 'رفض هذه الشهادة؟',
    'The company sees the reason and can upload a new scan.': 'سترى الشركة السبب ويمكنها رفع نسخة جديدة.', 'Decision undone — the item is back in its queue': 'تم التراجع عن القرار — عاد العنصر إلى قائمته',
    'Post restored — its author is told': 'تمت استعادة المنشور — وأُبلغ كاتبه', '✅ Approved': '✅ مقبول', '❌ Rejected': '❌ مرفوض', '📣 Published': '📣 منشور', '✅ Checked': '✅ تم الفحص', '✅ Resolved': '✅ تم الحل',
    '🗑 Dismissed': '🗑 مستبعد', '💳 Paid': '💳 مدفوع', '❌ Not received': '❌ لم يُستلم', '🗑 Removed': '🗑 محذوف', '✅ Action taken': '✅ تم الإجراء', '↺ Restored': '↺ مستعاد', '✓ Verified ': '✓ موثّق',
    'Made admin': 'أصبح مديراً', 'Made moderator': 'أصبح مشرفاً', 'Made member': 'أصبح عضواً', 'Could not undo': 'تعذّر التراجع'
  }, [
    [/^(.+) is now (a member|a moderator|an admin)$/, function (m) { return m[1] + ' أصبح ' + ({ 'a member': 'عضواً', 'a moderator': 'مشرفاً', 'an admin': 'مديراً' })[m[2]]; }],
    [/^(.+) is verified ✓$/, function (m) { return 'تم توثيق ' + m[1] + ' ✓'; }], [/^(.+) is suspended$/, function (m) { return 'تم إيقاف ' + m[1]; }],
    [/^(.+) can use Drugbox again$/, function (m) { return 'يمكن لـ' + m[1] + ' استخدام Drugbox مجدداً'; }], [/^Suspend (.+)\?$/, function (m) { return 'إيقاف ' + m[1] + '؟'; }],
    [/^Already decided by (.+?)(?: \((.+)\))?$/, function (m) { return 'سبق البت فيه بواسطة ' + m[1]; }], [/^Already undone by (.+)$/, function (m) { return 'سبق التراجع عنه بواسطة ' + m[1]; }],
    [/^Drugbox removed your post: (.+)$/, function (m) { return 'حذفت Drugbox منشورك: ' + m[1]; }], [/^checked your certificate "(.+)" — it shows as verified on (.+)$/, function (m) { return 'فحص شهادتك "' + m[1] + '" — تظهر موثّقة في ' + m[2]; }],
    [/^could not accept your certificate "(.+)": (.+)$/, function (m) { return 'تعذّر قبول شهادتك "' + m[1] + '": ' + m[2]; }],
    [/^Thank you — your report about (.+) was checked and the page is corrected$/, function (m) { return 'شكراً — تم فحص بلاغك عن ' + m[1] + ' وتصحيح الصفحة'; }],
    [/^Your report about (.+) was checked — the page stays as it is$/, function (m) { return 'تم فحص بلاغك عن ' + m[1] + ' — تبقى الصفحة كما هي'; }],
[/^Waiting for confirmation — order (DBX\d+)\. We confirm InstaPay transfers within one working day$/, function (m) { return 'بانتظار التأكيد — الطلب ' + m[1] + '. نؤكد تحويلات إنستاباي خلال يوم عمل واحد'; }],
    [/^Your claim for (.+) is already under review — Drugbox tells you when it is checked\.$/, function (m) { return 'مطالبتك بصفحة ' + m[1] + ' قيد المراجعة بالفعل — ستبلغك Drugbox عند فحصها.'; }],
    [/^Your claim for (.+) is already under review$/, function (m) { return 'مطالبتك بصفحة ' + m[1] + ' قيد المراجعة بالفعل'; }],
    [/^Drugbox published your (warning|work) reference about (.+)$/, function (m) { return 'نشرت Drugbox ' + (m[1] === 'warning' ? 'تحذيرك' : 'مرجعيتك') + ' عن ' + m[2]; }],
    [/^Drugbox did not publish your (warning|work) reference about (.+)$/, function (m) { return 'لم تنشر Drugbox ' + (m[1] === 'warning' ? 'تحذيرك' : 'مرجعيتك') + ' عن ' + m[2]; }],
    [/^Drugbox reviewed a warning reference about you and did not publish it$/, function () { return 'راجعت Drugbox تحذيراً كُتب عنك ولم تنشره'; }],
    [/^Verification needs another look: (.+)$/, function (m) { return 'التوثيق يحتاج مراجعة أخرى: ' + m[1]; }],
        [/^🚩 My reports \((\d+)\)$/, function (m) { return '🚩 بلاغاتي (' + m[1] + ')'; }],
    [/^\((\d[\d,]*)\)$/, function (m) { return '(' + m[1] + ')'; }]
  ]);
})();
