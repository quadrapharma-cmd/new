/* Controls that did nothing (found by the inactive-link audit) now do what they say. */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function digits(s) { return String(s == null ? '' : s).replace(/[^0-9+]/g, ''); }   /* tel: and wa.me links carry digits only — never text a company admin typed */
  function store(k, v) { try { if (v === undefined) { var x = JSON.parse(localStorage.getItem('dx_' + k) || 'null'); return Array.isArray(x) ? x : []; } localStorage.setItem('dx_' + k, JSON.stringify(v)); } catch (e) { return []; } }

  /* ── Groups: "+ Join" / "✓ Joined" join and leave, remembered ── */
  function title(card) { return txt(card && card.querySelector('.gcard-title')) || txt(card); }
  function paint(btn, joined) {
    btn.classList.toggle('btn-join', !joined); btn.classList.toggle('btn-joined', joined);
    btn.textContent = joined ? '✓ Joined' : '+ Join'; btn.setAttribute('aria-pressed', joined ? 'true' : 'false');
  }
  function joinedSet() { return store('groups_joined'); }
  function applyJoined() {
    if (window.dxLive) return;
    var j = joinedSet(), left = store('groups_left');
    document.querySelectorAll('#gx .gcard').forEach(function (card) {
      var b = card.querySelector('.gcard-btn'); if (!b || b.dataset.gpq) return; var t = title(card);   /* gpq: a private group's request state (groups.js) */
      if (j.indexOf(t) >= 0 && b.classList.contains('btn-join')) paint(b, true);
      if (left.indexOf(t) >= 0 && b.classList.contains('btn-joined')) paint(b, false);
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#gx .gcard-btn'); if (!b) return;
    if (window.dxGroups && window.dxGroups.joinClick(b, e)) return;   /* groups.js: join, leave and private-group requests */
    if (window.dxLive) return;                                          /* live app: membership is the database's (the adapter), never kept in this browser */
    e.preventDefault(); e.stopPropagation();          /* joining does not open the group */
    var card = b.closest('.gcard'), t = title(card), j = joinedSet(), left = store('groups_left');
    if (b.classList.contains('btn-join')) {
      paint(b, true); if (j.indexOf(t) < 0) j.push(t); store('groups_joined', j); store('groups_left', left.filter(function (x) { return x !== t; }));
      D.toast('You joined ' + t);
    } else {
      paint(b, false); store('groups_joined', j.filter(function (x) { return x !== t; })); if (left.indexOf(t) < 0) left.push(t); store('groups_left', left);
      if (window.dxUndo) window.dxUndo('You left ' + t, function () { paint(b, true); var j2 = joinedSet(); j2.push(t); store('groups_joined', j2); store('groups_left', store('groups_left').filter(function (x) { return x !== t; })); });
      else D.toast('You left ' + t);
    }
  }, true);

  /* ── Messages: 👤 opens the contact's profile; 📞 shows how to call them ── */
  function partnerName() { var h = Array.prototype.find.call(document.querySelectorAll('#mx *'), function (e) { return /ch-name|chat-name|ch-title/.test(e.className) && e.offsetWidth > 0; }); return h ? txt(h).replace(/[✓✔]/g, '').trim() : ''; }
  /* the live app knows WHICH member the open conversation is with (window.dxMxPartner, the adapter): two members can share a name */
  function partner() { var n = partnerName(), id = window.dxMxPartner && window.dxMxPartner();
    if (id) return { name: n, user: (window.USERS || []).find(function (u) { return u.id === id; }) || { id: id, name: n } };
    return { name: n, user: (window.USERS || []).find(function (u) { return n && (u.name === n || n.indexOf(u.name) === 0); }) }; }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mx .ch-action-btn'); if (!b) return;
    var oc = b.getAttribute('onclick') || '', label = txt(b);
    if (/profile/i.test(oc) || label === '👤') {
      e.preventDefault(); e.stopImmediatePropagation();
      var p = partner();
      if (p.user && window.gotoProfile) window.gotoProfile(p.user.id);
      else D.toast(p.name ? p.name + ' has no public profile yet' : 'Open a conversation first');
    } else if (/Calling/i.test(oc) || label === '📞') {
      e.preventDefault(); e.stopImmediatePropagation();
      var q = partner(), co = q.user && window.dxDir ? window.dxDir.companies().find(function (c) { return c.name === q.user.company; }) : null;
      var phone = co && co.phone, wa = co && digits(co.whatsapp);
      D.modal({ title: 'Call ' + (q.name || 'contact'), secondary: 'Close',
        body: phone || wa ? '<p>' + (q.user && q.user.company ? 'Company phone of ' + esc(q.user.company) + ':' : 'Phone:') + '</p>' +
            (phone ? '<p><a class="dr-btn p" href="tel:' + esc(digits(phone)) + '">📞 ' + esc(phone) + '</a></p>' : '') + (wa ? '<p><a class="dr-btn" href="https://wa.me/' + esc(wa) + '" target="_blank" rel="noopener">WhatsApp</a></p>' : '')
          : '<p>' + esc(q.name || 'This contact') + ' has not shared a phone number. Send a message and ask for a call — the quick reply “Schedule a call” does it in one tap.</p>' });
    }
  }, true);


  /* ── Home: "N reposts" shows who reposted; a post's category label searches that category ── */
  document.addEventListener('click', function (e) {
    var s = e.target.closest && e.target.closest('#content .post-stats span'); if (!s || s.getAttribute('onclick')) return;
    var m = /(\d[\d,]*)\s*reposts?/i.exec(txt(s)); if (!m) return;
    if (window.dxLive) return;   /* live: only a count is known — the demo list of sample people must not be shown as reposters */
    e.preventDefault(); e.stopPropagation();
    var people = (window.USERS || []).slice(0, Math.min(6, parseInt(m[1].replace(/,/g, ''), 10) || 1));
    D.modal({ title: m[1] + ' reposts', secondary: 'Close', body: people.map(function (u) { return '<div class="mr-row"><div class="mr-b"><b>' + esc(u.name) + '</b><small>' + esc((u.headline || '').split('|')[0]) + '</small></div><button type="button" class="dr-btn sm" data-rp="' + (+u.id || 0) + '">Profile</button></div>'; }).join('') + (parseInt(m[1], 10) > people.length ? '<p class="cp-muted">and ' + (parseInt(m[1], 10) - people.length) + ' more in your network</p>' : '') }).el.addEventListener('click', function (ev) { var b = ev.target.closest('[data-rp]'); if (b && window.gotoProfile) { document.querySelectorAll('.dbk-ov').forEach(function (o) { o.remove(); }); window.gotoProfile(+b.dataset.rp); } });
  }, true);
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#content .badge-cat'); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    if (window.dxOpenSearch) { window.dxOpenSearch(); var i = document.querySelector('#dxCmd input'); if (i) { i.value = txt(b); i.dispatchEvent(new Event('input', { bubbles: true })); } }
  }, true);

  /* ── Groups: every card and side row opens its group (7 of 9 cards had no action) ── */
  function openGroupNamed(name) {
    if (window.dxGroups && window.dxGroups.open(name)) return;   /* groups.js opens the group with its inside (posts, members, about) */
    var card = Array.prototype.find.call(document.querySelectorAll('#gx .gcard'), function (c) { return txt(c.querySelector('.gcard-title')) === name; });
    var joined = card && card.querySelector('.btn-joined');
    if (typeof window.openGroup === 'function') window.openGroup(joined ? 'member' : 'member');
    var gd = document.getElementById('groupDetail'); if (!gd) return;
    function leaf(sel) { return Array.prototype.find.call(gd.querySelectorAll(sel), function (e) { return !e.children.length; }); }   /* only an element with no children, never a wrapper */
    var t = document.getElementById('dt-title') || leaf('[class*="title"]'); if (t) t.textContent = name;
    var d = document.getElementById('dt-desc') || leaf('[class*="desc"]'); if (d && card && card.querySelector('.gcard-desc')) d.textContent = txt(card.querySelector('.gcard-desc'));
  }
  document.addEventListener('click', function (e) {
    var c = e.target.closest && e.target.closest('#gx .gcard, #gx .mygroup, #gx .sh-row'); if (!c || e.target.closest('.gcard-btn,button,a')) return;
    if (window.dxGroups) return;   /* groups.js handles every card and side row */
    if (c.getAttribute('onclick')) return;
    var name = txt(c.querySelector('.gcard-title, .mg-name')) || txt(c); if (!name) return;
    e.preventDefault(); e.stopPropagation(); openGroupNamed(name.replace(/\s*\d.*$/, ''));
  }, true);


  /* ── Filter options built as <div><input> text</div>: clicking the text ticks the box and applies the filter ── */
  document.addEventListener('click', function (e) {
    var o = e.target.closest && e.target.closest('#content .f-opt'); if (!o || o.tagName === 'LABEL' || e.target.tagName === 'INPUT' || e.target.closest('label')) return;
    var cb = o.querySelector('input[type=checkbox],input[type=radio]'); if (!cb) return;
    e.preventDefault(); cb.click();   /* a real click on the box: runs every filter handler exactly as a direct tick would */
  }, true);


  /* (Jobs: the employment-type and country filters are in jobsx.js, with the keyword search and paging) */


  /* ── Side-column group shortcuts (every page): open that group ── */
  document.addEventListener('click', function (e) {
    var r = e.target.closest && e.target.closest('.sh-row, #sidebar .mygroup'); if (!r || r.getAttribute('onclick') || r.dataset.gid || r.closest('#gx')) return;   /* data-gid: a live group row, opened by the adapter */
    var name = txt(r.querySelector('.sh-name, .mg-name')) || txt(r); if (!name) return;
    e.preventDefault(); e.stopPropagation();
    window.goto('groups');
    setTimeout(function () { openGroupNamed(name.replace(/\s*\d.*$/, '')); }, 120);
  }, true);


  /* ── Workspace heading: the company name opens its public page ── */
  document.addEventListener('click', function (e) {
    var h = e.target.closest && e.target.closest('#dxDir.ws .ws-h'); if (!h) return;
    var X = window.dxDir, name = txt(h), co = X && ((X.S && X.S.ws && X.bySlug(X.S.ws)) ||   /* the workspace on screen, by slug */
      X.companies().find(function (c) { return c.name === name; }) || (X.mine && X.mine()));     /* never a name prefix: 'Look Pharma X' is not 'Look Pharma X Egypt' */
    if (co && window.dxHub) { e.preventDefault(); window.dxHub.page(co.slug); }
  }, true);
  C.onRender('ws-heading-link', function () { var h = document.querySelector('#dxDir.ws .ws-h'); if (h && !h.dataset.lk) { h.dataset.lk = '1'; h.style.cursor = 'pointer'; h.setAttribute('title', 'View public page'); h.setAttribute('role', 'link'); h.setAttribute('tabindex', '0'); } });

  C.onRender('groups-joined', applyJoined);
})();
