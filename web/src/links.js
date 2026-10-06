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
    var j = joinedSet(), left = store('groups_left');
    document.querySelectorAll('#gx .gcard').forEach(function (card) {
      var b = card.querySelector('.gcard-btn'); if (!b) return; var t = title(card);
      if (j.indexOf(t) >= 0 && b.classList.contains('btn-join')) paint(b, true);
      if (left.indexOf(t) >= 0 && b.classList.contains('btn-joined')) paint(b, false);
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#gx .gcard-btn'); if (!b) return;
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
  function partner() { var n = partnerName(); return { name: n, user: (window.USERS || []).find(function (u) { return n && (u.name === n || n.indexOf(u.name) === 0); }) }; }
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


  /* ── Jobs: employment-type and country boxes were not connected to any filter; they now filter, on top of category and level ── */
  var COUNTRY = [['Egypt', /egypt|cairo|giza|alex|6th of october|10th of ramadan|sharqia|obour|sadat|mansoura|tanta|القاهرة|مصر/i], ['UAE', /uae|dubai|abu dhabi|sharjah|emirates/i],
                 ['Saudi Arabia', /saudi|ksa|riyadh|jeddah|dammam/i], ['India', /india|mumbai|hyderabad|delhi|bangalore|ahmedabad/i]];
  function jobFilterState() {
    var box = document.querySelector('#jx .filters'); if (!box) return null;
    var types = [], countries = [], inCountry = false;
    Array.prototype.forEach.call(box.children, function (el) {
      if (el.classList.contains('f-hdr')) inCountry = /country/i.test(txt(el));
      if (!el.classList.contains('f-opt')) return;
      var cb = el.querySelector('input'); if (!cb || !cb.checked) return;
      var label = txt(el).replace(/^[^\w]+/, '');
      (inCountry ? countries : types).push(label);
    });
    return { types: types, countries: countries };
  }
  function cardCountry(card) { var t = txt(card); for (var i = 0; i < COUNTRY.length; i++) if (COUNTRY[i][1].test(t)) return COUNTRY[i][0]; return null; }
  function applyExtraJobFilters() {
    var st = jobFilterState(); if (!st) return;
    var cards = Array.prototype.slice.call(document.querySelectorAll('#jx .jcard'));
    cards.forEach(function (card) { if (card.dataset.dxjh) { card.style.display = card.dataset.dxjh === '-' ? '' : card.dataset.dxjh; delete card.dataset.dxjh; } });   /* undo only what this filter hid */
    var pool = cards.filter(function (card) { return card.style.display !== 'none' && card.offsetParent !== null || (card.style.display !== 'none' && getComputedStyle(card).display !== 'none'); });
    var vis = pool.filter(function (card) { return card.offsetParent !== null; }), shown = 0, list = vis.length ? vis[0].parentElement : (pool.length ? pool[0].parentElement : null);   /* the list the user actually sees */
    pool.forEach(function (card) {
      var t = txt(card), remote = /remote/i.test(t);
      var typeOk = st.types.some(function (ty) { return ty === 'Remote' ? remote : t.indexOf(ty) >= 0; });
      var c = cardCountry(card), countryOk = !c || st.countries.indexOf(c) >= 0;
      if (typeOk && countryOk) { if (vis.indexOf(card) >= 0) shown++; return; }   /* count only jobs on screen, not the hidden duplicate list */
      card.dataset.dxjh = card.style.display || '-'; card.style.display = 'none';
    });
    document.querySelectorAll('#jx .dx-jobs-empty').forEach(function (e) { e.remove(); });
    if (!shown && list) {
      var empty = document.createElement('div'); empty.className = 'dx-jobs-empty';
      empty.innerHTML = '<b>No jobs match these filters</b><p>Tick more employment types or countries.</p><button type="button" class="dr-btn p">Clear filters</button>';
      list.appendChild(empty);
      empty.querySelector('button').addEventListener('click', function () { document.querySelectorAll('#jx .filters .f-opt input').forEach(function (cb) { cb.checked = true; }); if (typeof window.applyJobFilters === 'function') window.applyJobFilters(); else applyExtraJobFilters(); });
    }
  }
  function wrapJobFilters() {   /* the jobs page code loads when the page is first opened, so connect then */
    if (typeof window.applyJobFilters !== 'function' || window.applyJobFilters.__dx) return;
    var _ajf = window.applyJobFilters;
    window.applyJobFilters = function () { var r = _ajf.apply(this, arguments); try { applyExtraJobFilters(); } catch (e) { if (window.console) console.warn('job filters:', e && e.message); } return r; };
    window.applyJobFilters.__dx = true;
  }
  document.addEventListener('change', function (e) {
    if (!(e.target.closest && e.target.closest('#jx .filters'))) return;
    wrapJobFilters(); if (typeof window.applyJobFilters === 'function') window.applyJobFilters(); else applyExtraJobFilters();
  });
  C.onRender('jobs-filters', function () { wrapJobFilters(); });


  /* ── Side-column group shortcuts (every page): open that group ── */
  document.addEventListener('click', function (e) {
    var r = e.target.closest && e.target.closest('.sh-row, #sidebar .mygroup'); if (!r || r.getAttribute('onclick') || r.closest('#gx')) return;
    var name = txt(r.querySelector('.sh-name, .mg-name')) || txt(r); if (!name) return;
    e.preventDefault(); e.stopPropagation();
    window.goto('groups');
    setTimeout(function () { openGroupNamed(name.replace(/\s*\d.*$/, '')); }, 120);
  }, true);


  /* ── Workspace heading: the company name opens its public page ── */
  document.addEventListener('click', function (e) {
    var h = e.target.closest && e.target.closest('#dxDir.ws .ws-h'); if (!h) return;
    var co = window.dxDir && (window.dxDir.companies().find(function (c) { return txt(h).indexOf(c.name) === 0; }) || (window.dxDir.mine && window.dxDir.mine()));
    if (co && window.dxHub) { e.preventDefault(); window.dxHub.page(co.slug); }
  }, true);
  C.onRender('ws-heading-link', function () { var h = document.querySelector('#dxDir.ws .ws-h'); if (h && !h.dataset.lk) { h.dataset.lk = '1'; h.style.cursor = 'pointer'; h.setAttribute('title', 'View public page'); h.setAttribute('role', 'link'); h.setAttribute('tabindex', '0'); } });

  C.onRender('groups-joined', applyJoined);
})();
