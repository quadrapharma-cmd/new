/* Batch 3 — personalization & discovery
   14 role-based home · 15 match cards with a score · 16 Ctrl+K command search · 17 saved searches with alerts · 18 profile insights */
(function () {
  var C = window.dxCore; if (!C) return;
  var D = window.DBK;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  var __A = /^(deals|created_companies|reports|dossiers|surplus_new|groups_new|follows|saved_searches|my_requests|activity_.*|inbox_.*)$/, __O = /^(company_edits|supplier_reviews|review_meta|avl_.*|groups_state|meta_.*|quoted_.*|sqq_.*)$/, __S = /^(acting|role)$/;
  function __typed(k, v) { if (v == null) return null; if (__A.test(k)) return Array.isArray(v) ? v : null; if (__O.test(k)) return (typeof v === 'object' && !Array.isArray(v)) ? v : null; if (__S.test(k)) return typeof v === 'string' ? v : null; return v; }   /* a stored value of the wrong type is ignored, never trusted */
  function store(k, v) { try { if (v === undefined) return __typed(k, JSON.parse(localStorage.getItem('dx_' + k) || 'null')); localStorage.setItem('dx_' + k, JSON.stringify(v)); } catch (e) { return null; } }
  function page() { return document.body.getAttribute('data-page') || 'feed'; }

  /* ── what we know about the user's interests (demo; production reads profile + My Intents) ── */
  var ME_INTERESTS = { products: ['metformin', 'amoxicillin', 'ciprofloxacin', 'neomycin', 'hyaluronic', 'mcc'], certs: ['who-gmp', 'cep', 'eda', 'usfda'], places: ['egypt', 'uae', 'saudi', 'gcc'], skills: ['regulatory', 'eda', 'gmp', 'registration', 'qa', 'cmo'] };
  function score(item) {
    var t = (item.t + ' ' + (item.tags || []).join(' ') + ' ' + (item.who || '')).toLowerCase(), s = 52, why = [];
    function label(k) { return k.length <= 3 ? k.toUpperCase() : k[0].toUpperCase() + k.slice(1); }
    ME_INTERESTS.products.forEach(function (k) { if (t.indexOf(k) >= 0) { s += 18; why.push(label(k)); } });
    ME_INTERESTS.certs.forEach(function (k) { if (t.indexOf(k) >= 0) { s += 8; why.push(k.toUpperCase()); } });
    ME_INTERESTS.places.forEach(function (k) { if (t.indexOf(k) >= 0) { s += 7; why.push(label(k)); } });
    ME_INTERESTS.skills.forEach(function (k) { if (t.indexOf(k) >= 0 && why.length < 4) { s += 5; why.push(k.toUpperCase() === k ? k : k[0].toUpperCase() + k.slice(1)); } });
    return { pct: Math.min(98, s), why: why.filter(function (w, i) { return why.indexOf(w) === i; }).slice(0, 3) };
  }

  /* ── demo content for each role (production: live queries) ── */
  var DEMAND = [{ t: 'Ciprofloxacin HCl — 2 MT/month', who: 'Pharma manufacturer · Egypt', tags: ['API', 'WHO-GMP', 'Egypt'], when: '2h', q: 'Ciprofloxacin', icon: 'basket' },
    { t: 'MCC PH-102 — 3 MT/month', who: 'Tablet manufacturer · Egypt', tags: ['Excipient', 'WHO-GMP', 'Egypt', 'annual'], when: '5h', q: 'MCC', icon: 'basket' },
    { t: 'Amoxicillin Trihydrate — 1 MT', who: 'Distributor · Saudi Arabia', tags: ['API', 'CEP', 'Saudi'], when: '1d', q: 'Amoxicillin', icon: 'basket' },
    { t: 'Retinol 97%+ — 500 g/month', who: 'Cosmetics brand · UAE', tags: ['ISO 22716', 'UAE'], when: '1h', q: 'Retinol', icon: 'basket' }];
  var SUPPLY = [{ t: 'Metformin HCl BP/USP — GMP grade', who: 'Shandong Hope Biotech · China', tags: ['API', 'WHO-GMP', 'CEP', 'USFDA DMF'], price: 'US$ 5.80/kg', q: 'Metformin', icon: 'flask' },
    { t: 'Neomycin Sulphate EP/USP', who: 'Shandong Hope Biotech · China', tags: ['API', 'CEP'], price: 'US$ 42/kg', q: 'Neomycin', icon: 'flask' },
    { t: 'Hyaluronic Acid — Dual MW cosmetic grade', who: 'Supplier · Egypt', tags: ['ISO 22716', 'Halal', 'Egypt'], price: 'US$ 180/kg', q: 'Hyaluronic', icon: 'drop' },
    { t: 'Amoxicillin Trihydrate — compacted', who: 'Aurobindo Pharma · India', tags: ['API', 'USFDA', 'WHO-GMP'], price: 'US$ 38.50/kg', q: 'Amoxicillin', icon: 'flask' }];
  var JOBS = [{ t: 'Senior Regulatory Affairs Specialist', who: 'Quadra Pharm · Giza, Egypt', tags: ['EDA', 'Regulatory', 'Egypt'], q: 'Senior Regulatory', icon: 'briefcase' },
    { t: 'GCC Registration Coordinator', who: 'Epione Drug Store · Dubai, UAE', tags: ['SFDA/DHA', 'Registration', 'UAE'], q: 'GCC Registration', icon: 'briefcase' },
    { t: 'QC Analyst (HPLC) — API Division', who: 'Aurobindo Pharma · India', tags: ['HPLC', 'QA'], q: 'QC Analyst', icon: 'briefcase' },
    { t: 'Production Supervisor — Solid Dosage', who: 'Medsinia Industries · Egypt', tags: ['GMP', 'Egypt'], q: 'Production Supervisor', icon: 'briefcase' }];
  var CANDS = [{ t: 'Sara Mansour — Regulatory Affairs Specialist', who: '4 yrs · Cairo, Egypt', tags: ['EDA', 'Registration', 'Egypt'], q: 'Sara Mansour', icon: 'user' },
    { t: 'Youssef Hassan — QC Chemist (HPLC & GC)', who: '3 yrs · Alexandria, Egypt', tags: ['QA', 'GMP', 'Egypt'], q: 'Youssef Hassan', icon: 'user' },
    { t: 'Karim Adel — Medical Sales Representative', who: '5 yrs · Dubai, UAE', tags: ['UAE', 'GCC'], q: 'Karim Adel', icon: 'user' },
    { t: 'Nour Farouk — Cosmetic Formulator', who: '2 yrs · Cairo, Egypt', tags: ['ISO 22716', 'Egypt'], q: 'Nour Farouk', icon: 'user' }];
  var REG = [{ t: 'EDA Circular 2025/018 — stability submission update', who: 'Regulatory · Egypt', tags: ['EDA', 'Regulatory', 'Egypt'], q: 'EDA Circular', icon: 'doc', post: 1 },
    { t: 'NFSA Circular 2025/C/003 — supplements labelling', who: 'Regulatory · Egypt', tags: ['Regulatory', 'Egypt'], q: 'NFSA', icon: 'doc' },
    { t: 'Dossier checklist: EDA new registration (CTD)', who: 'Tool', tags: ['EDA', 'Registration'], q: 'checklist', icon: 'clipboard' },
    { t: 'Group: Regulatory Affairs Egypt — 3 new posts', who: 'Community', tags: ['Regulatory', 'EDA', 'Egypt'], q: 'Regulatory Affairs Egypt', icon: 'users' }];
  var ROLES = {
    supplier: { label: 'Sell', icon: 'box', title: 'Buyers looking for what you sell', sub: 'Open requests that match your products — answer first, win first.', items: DEMAND, act: [['Post supply', 'plus', 'create'], ['Boost a listing', 'bolt', 'boost']] },
    buyer: { label: 'Buy', icon: 'cart', title: 'New supply that fits your needs', sub: 'Verified suppliers with the grades and certificates you usually ask for.', items: SUPPLY, act: [['Post a request', 'plus', 'create'], ['Compare suppliers', 'clipboard', 'market']] },
    regulatory: { label: 'Regulatory', icon: 'doc', title: 'Regulatory updates for you', sub: 'Circulars, checklists and discussions in your markets.', items: REG, act: [['Regulatory groups', 'users', 'groups'], ['Regulatory jobs', 'briefcase', 'jobs']] },
    seeker: { label: 'Find a job', icon: 'briefcase', title: 'Jobs that match your profile', sub: 'Based on your skills, experience and preferred locations.', items: JOBS, act: [['Post my profile', 'user', 'jobs'], ['Improve my profile', 'trend', 'profile']] },
    hiring: { label: 'Hire', icon: 'users', title: 'Candidates for your open roles', sub: 'Available professionals ranked by fit and by what past employers say.', items: CANDS, act: [['Post a job', 'plus', 'jobs'], ['Top-rated candidates', 'trophy', 'jobs']] }
  };
  var role = ROLES[store('role')] ? store('role') : 'supplier';   /* an unknown stored role falls back instead of breaking the panel */

  /* ── flash a card after navigating to it ── */
  function flashText(sel, q, tries) {
    tries = tries || 0;
    var el = Array.prototype.find.call(document.querySelectorAll(sel), function (c) { return c.offsetParent !== null && txt(c).toLowerCase().indexOf(q.toLowerCase()) >= 0; });
    if (!el) { if (tries < 8) setTimeout(function () { flashText(sel, q, tries + 1); }, 120); return; }
    el.scrollIntoView({ block: 'center', behavior: 'smooth' }); el.classList.remove('dx-flash'); void el.offsetWidth; el.classList.add('dx-flash');
  }
  function openItem(kind, it) {
    if (kind === 'supplier') { window.goto('market'); flashText('#mkx .dcard', it.q); }
    else if (kind === 'buyer') { window.goto('market'); var si = document.getElementById('searchIn'); if (si) si.value = it.q; if (window.__mkxFilter) window.__mkxFilter(it.q); flashText('#mkx .sponsored-card, #mkx .lcard', it.q); }
    else if (kind === 'regulatory') { if (it.post && window.dgJump) { window.goto('feed'); setTimeout(function () { window.dgJump(it.post); }, 60); } else if (/group/i.test(it.t)) { window.goto('groups'); flashText('#gx .gcard', it.q); } else if (/checklist/i.test(it.t)) { if (D) D.toast('The dossier checklist tool is coming in the regulatory tools batch'); } else { window.goto('feed'); } }
    else if (kind === 'seeker') { window.goto('jobs'); var h = document.querySelector('#jx .mode-opt[data-mode="hunting"]'); if (h) h.click(); flashText('#jx #huntingView .jcard', it.q); }
    else if (kind === 'hiring') { window.goto('jobs'); var g = document.querySelector('#jx .mode-opt[data-mode="hiring"]'); if (g) g.click(); flashText('#jx #hiringView .jcard', it.q); }
  }
  function runAction(a) {
    if (a === 'create') { window.goto('market'); var t = document.querySelector('#mkx .master-tab[data-tab="create"]'); if (t) t.click(); }
    else if (a === 'boost') { window.goto('market'); var m = document.querySelector('#mkx .master-tab[data-tab="manage"]'); if (m) m.click(); }
    else window.goto(a);
  }

  /* ── 14 + 15: the "For you" panel on Home ── */
  function ring(p) { return '<span class="fy-score" style="--p:' + p + '"><b>' + p + '</b><i>%</i></span>'; }
  function forYou() {
    if (page() !== 'feed' || window.dxLive) return;   /* demo content (production: live queries) */
    var hero = document.querySelector('#content > .dg-hero'); if (!hero) return;
    var panel = document.getElementById('dxForYou');
    if (panel && panel.dataset.role === role && panel.previousElementSibling === hero) return;
    if (panel) panel.remove();
    var R = ROLES[role], items = R.items.map(function (it) { var s = score(it); return { it: it, s: s }; }).sort(function (a, b) { return b.s.pct - a.s.pct; });
    panel = document.createElement('section'); panel.id = 'dxForYou'; panel.dataset.role = role;
    panel.innerHTML = '<div class="fy-top"><div><span class="fy-k">FOR YOU</span><h2>' + esc(R.title) + '</h2><p>' + esc(R.sub) + '</p></div>' +
      '<div class="fy-roles" role="tablist" aria-label="I am here to">' + Object.keys(ROLES).map(function (k) { return '<button type="button" role="tab" aria-selected="' + (k === role) + '" class="' + (k === role ? 'on' : '') + '" data-role="' + k + '">' + ic(ROLES[k].icon) + ROLES[k].label + '</button>'; }).join('') + '</div></div>' +
      '<div class="fy-grid">' + items.map(function (x, i) {
        return '<button type="button" class="fy-card" data-i="' + R.items.indexOf(x.it) + '">' + ring(x.s.pct) + '<span class="fy-body"><span class="fy-t"><span class="fy-ic">' + ic(x.it.icon) + '</span>' + esc(x.it.t) + '</span><span class="fy-who">' + esc(x.it.who) + (x.it.when ? ' · ' + esc(x.it.when) + ' ago' : '') + (x.it.price ? ' · <b>' + esc(x.it.price) + '</b>' : '') + '</span>' +
          (x.s.why.length ? '<span class="fy-why">Matches: ' + x.s.why.map(esc).join(' · ') + '</span>' : '') + '</span></button>';
      }).join('') + '</div>' +
      '<div class="fy-acts">' + R.act.map(function (a) { return '<button type="button" class="fy-act" data-act="' + a[2] + '">' + ic(a[1]) + a[0] + '</button>'; }).join('') + '<span class="fy-note">Scores use your profile, skills and My Intents. <button type="button" class="fy-link" data-act="intents">Edit my intents</button></span></div>';
    hero.insertAdjacentElement('afterend', panel);
    panel.addEventListener('click', function (e) {
      var r = e.target.closest('.fy-roles [data-role]'); if (r) { role = r.dataset.role; store('role', role); forYou(); return; }
      var c = e.target.closest('.fy-card'); if (c) { openItem(role, ROLES[role].items[+c.dataset.i]); return; }
      var a = e.target.closest('[data-act]'); if (a) { if (a.dataset.act === 'intents') { window.goto('market'); var t = document.querySelector('#mkx .master-tab[data-tab="intents"]'); if (t) t.click(); } else runAction(a.dataset.act); }
    });
  }

  /* ── 16: command search (Ctrl/⌘ + K, or "/") ── */
  var idx = null;
  function buildIndex() {
    if (idx) return idx; idx = [];
    var PAGES = [['feed', 'Home', 'home'], ['network', 'My Network', 'users'], ['messages', 'Messages', 'chat'], ['notifs', 'Notifications', 'bell'], ['profile', 'My profile', 'user'], ['saved', 'Saved', 'bookmark'],
      ['groups', 'Groups', 'handshake'], ['market', 'Marketplace', 'cart'], ['jobs', 'Jobs', 'briefcase'], ['companies', 'Company Directory', 'building'], ['training', 'Training', 'cap']];
    PAGES.forEach(function (p) { idx.push({ g: 'Pages', t: p[1], s: 'Go to ' + p[1], ic: p[2], go: function () { window.goto(p[0]); } }); });
    [['Company workspace', 'building', function () { var a = window.dxDir && window.dxDir.mine(); if (a && window.dxHub) window.dxHub.workspace(a.slug); }], ['Requests & deals', 'handshake', function () { window.dxDeals && window.dxDeals.center('sent'); }], ['Directory health', 'chart', function () { window.goto('companies'); setTimeout(function () { window.dxHub && window.dxHub.health(); }, 60); }], ['Create a company page', 'building', function () { window.goto('companies'); setTimeout(function () { window.dxCreateCompany && window.dxCreateCompany(); }, 60); }], ['Create a listing', 'plus', function () { runAction('create'); }], ['Post a job', 'briefcase', function () { window.goto('jobs'); var b = document.querySelector('#jx .post-cta-btn'); if (b) b.click(); }],
     ['Switch to dark mode', 'moon', function () { window.dxTheme && window.dxTheme('mode', 'dark'); }], ['Switch to light mode', 'sun', function () { window.dxTheme && window.dxTheme('mode', 'light'); }],
     ['Larger text', 'plus', function () { window.dxTheme && window.dxTheme('fs', 'l'); }], ['Take the 3-step tour', 'compass', function () { window.dxStartTour && window.dxStartTour(); }],
     ['Top-rated employers', 'trophy', function () { window.goto('jobs'); var h = document.querySelector('#jx .mode-opt[data-mode="hunting"]'); if (h) h.click(); setTimeout(function () { var t = document.querySelector('#jx #huntingView .jx-tool[data-a="top"]'); if (t) t.click(); }, 80); }]]
      .forEach(function (a) { idx.push({ g: 'Actions', t: a[0], s: '', ic: a[1], go: a[2] }); });
    (window.USERS || []).forEach(function (u) { idx.push({ g: 'People & companies', t: u.name, s: (u.headline || '').split('|')[0] + (u.company ? ' · ' + u.company : ''), ic: /pharma|industries|biotech/i.test(u.name) ? 'building' : 'user', go: function () { window.gotoProfile && window.gotoProfile(u.id); } }); });
    function parse(html) { var d = document.createElement('div'); d.innerHTML = html; return d; }
    try {
      var mk = parse(window.MKX_HTML || '');
      mk.querySelectorAll('.sponsored-card, .lcard, .scard, .dcard').forEach(function (c) {
        var t = txt(c.querySelector('.sp-title,.lc-title,.sc-title,.dc-title')); if (!t) return;
        var q = t.replace(/^(For Sale|Looking to Buy|Providing|Seeking)\s*/i, '').split('—')[0].trim();
        var demand = c.classList.contains('dcard');
        idx.push({ g: demand ? 'Buying requests' : 'Listings', t: q, s: txt(c.querySelector('.lt')) || (demand ? 'Request for quotation' : 'Service'), ic: demand ? 'basket' : 'box', go: function () { demand ? openItem('supplier', { q: q }) : openItem('buyer', { q: q }); } });
      });
      var jx = parse(window.JX_HTML || '');
      jx.querySelectorAll('.jcard').forEach(function (c) {
        var tt = c.querySelector('.jc-title').cloneNode(true); tt.querySelectorAll('span').forEach(function (s) { s.remove(); });
        var cand = !!c.querySelector('.role-badge.need'), who = txt(c.querySelector('.jc-company span'));
        idx.push({ g: cand ? 'Candidates' : 'Jobs', t: txt(tt), s: who, ic: cand ? 'user' : 'briefcase', go: function () { openItem(cand ? 'hiring' : 'seeker', { q: cand ? who : txt(tt) }); } });
      });
      var gx = parse(window.GX_HTML || '');
      gx.querySelectorAll('.gcard').forEach(function (c) { var t = txt(c.querySelector('.gcard-title')); if (t) idx.push({ g: 'Groups', t: t, s: txt(c.querySelector('.gcard-desc')).slice(0, 70), ic: 'users', go: function () { window.goto('groups'); flashText('#gx .gcard', t); } }); });
    } catch (e) { if (window.console) console.warn('[drugbox] search index', e); }
    (window.dxDirectory ? window.dxDirectory.list() : []).forEach(function (c) { idx.push({ g: 'Companies', t: c.name, s: c.sectors.join(' · ') + ' · ' + c.city, ic: 'building', go: function () { window.dxDirectory.open(c.slug); } }); c.products.forEach(function (p) { idx.push({ g: 'Products', t: p.name, s: c.name + ' · ' + p.cat, ic: 'box', go: function () { window.dxDirectory.open(c.slug, 'products'); } }); }); });
    (window.POSTS || []).slice(0, 60).forEach(function (p) { var u = (window.USERS || []).find(function (x) { return x.id === p.uid; }); idx.push({ g: 'Posts', t: String(p.text || p.body || '').replace(/\s+/g, ' ').slice(0, 80), s: u ? u.name : '', ic: 'megaphone', go: function () { window.goto('feed'); setTimeout(function () { window.dgJump && window.dgJump(p.id); }, 60); } }); });
    (saved() || []).forEach(function (s) { idx.push({ g: 'Saved searches', t: s.name, s: 'Saved search · alerts ' + s.alert, ic: 'bookmark', go: function () { applySaved(s); } }); });
    var seen = {}; idx = idx.filter(function (x) { var k = x.g + '|' + x.t; if (seen[k]) return false; seen[k] = 1; return true; });
    return idx;
  }
  var cmd = document.createElement('div'); cmd.id = 'dxCmd'; cmd.setAttribute('role', 'dialog'); cmd.setAttribute('aria-modal', 'true'); cmd.setAttribute('aria-label', 'Search Drugbox');
  cmd.innerHTML = '<div class="cm-box"><div class="cm-in">' + ic('search') + '<input type="text" placeholder="Search people, listings, jobs, groups, posts or type a command…" aria-label="Search" autocomplete="off"><kbd>Esc</kbd></div><div class="cm-res" role="listbox"></div><div class="cm-foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span><kbd>Ctrl</kbd>+<kbd>K</kbd> anytime</span></div></div>';
  document.body.appendChild(cmd);
  var cin = cmd.querySelector('input'), cres = cmd.querySelector('.cm-res'), sel = 0, shown = [];
  var ORDER = ['Pages', 'Actions', 'Saved searches', 'Companies', 'Products', 'People & companies', 'Listings', 'Buying requests', 'Jobs', 'Candidates', 'Groups', 'Posts'];
  function norm(s) { return String(s || '').toLowerCase(); }
  function search(q) {
    var all = buildIndex(); q = norm(q).trim();
    if (!q) return all.filter(function (x) { return x.g === 'Pages' || x.g === 'Actions' || x.g === 'Saved searches'; }).slice(0, 14);
    var words = q.split(/\s+/);
    return all.map(function (x) { var h = norm(x.t + ' ' + x.s), sc = 0; for (var i = 0; i < words.length; i++) { var k = h.indexOf(words[i]); if (k < 0) return null; sc += k === 0 ? 3 : norm(x.t).indexOf(words[i]) >= 0 ? 2 : 1; } return { x: x, sc: sc }; })
      .filter(Boolean).sort(function (a, b) { return b.sc - a.sc; }).slice(0, 24)
      .sort(function (a, b) { return (ORDER.indexOf(a.x.g) - ORDER.indexOf(b.x.g)) || (b.sc - a.sc); }).map(function (r) { return r.x; });
  }
  function drawRes() {
    shown = search(cin.value); sel = Math.min(sel, Math.max(0, shown.length - 1));
    if (!shown.length) { cres.innerHTML = '<div class="cm-empty">No results for “' + esc(cin.value) + '”. Try a product, a company or a person.</div>'; return; }
    var html = '', last = '';
    shown.forEach(function (x, i) { if (x.g !== last) { html += '<div class="cm-g">' + esc(x.g) + '</div>'; last = x.g; } html += '<div class="cm-i' + (i === sel ? ' on' : '') + '" role="option" aria-selected="' + (i === sel) + '" data-i="' + i + '"><span class="cm-ic">' + ic(x.ic) + '</span><span class="cm-t">' + esc(x.t) + (x.s ? '<small>' + esc(x.s) + '</small>' : '') + '</span></div>'; });
    cres.innerHTML = html;
    var on = cres.querySelector('.cm-i.on'); if (on) on.scrollIntoView({ block: 'nearest' });
  }
  function openCmd() { if (!document.getElementById('app') || !document.getElementById('app').offsetWidth) return; idx = null; cmd.className = 'on'; cin.value = ''; sel = 0; cin.focus(); drawRes(); }   /* focus at once so fast typing is not lost */
  function closeCmd() { cmd.className = ''; }
  function choose(i) { var x = shown[i]; if (!x) return; closeCmd(); try { x.go(); } catch (e) { if (window.console) console.warn(e); } }
  window.dxOpenSearch = openCmd;
  cin.addEventListener('input', function () { sel = 0; drawRes(); });
  cin.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { sel = Math.min(shown.length - 1, sel + 1); drawRes(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { sel = Math.max(0, sel - 1); drawRes(); e.preventDefault(); }
    else if (e.key === 'Enter') { choose(sel); e.preventDefault(); }
    else if (e.key === 'Escape') closeCmd();
  });
  cres.addEventListener('mousemove', function (e) { var r = e.target.closest('.cm-i'); if (r && +r.dataset.i !== sel) { sel = +r.dataset.i; cres.querySelectorAll('.cm-i').forEach(function (x) { x.classList.toggle('on', +x.dataset.i === sel); }); } });
  cres.addEventListener('click', function (e) { var r = e.target.closest('.cm-i'); if (r) choose(+r.dataset.i); });
  cmd.addEventListener('click', function (e) { if (e.target === cmd) closeCmd(); });
  document.addEventListener('keydown', function (e) {
    var typing = e.target.closest && e.target.closest('input,textarea,[contenteditable]');
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); cmd.className === 'on' ? closeCmd() : openCmd(); }
    else if (e.key === '/' && !typing && cmd.className !== 'on') { e.preventDefault(); openCmd(); }
    else if (e.key === 'Escape' && cmd.className === 'on') closeCmd();
  });
  function searchEntry() {
    var si = document.getElementById('searchIn');
    if (si && !si.parentNode.querySelector('.dx-kbd')) { var k = document.createElement('button'); k.type = 'button'; k.className = 'dx-kbd'; k.title = 'Search everything (Ctrl+K)'; k.innerHTML = 'Ctrl K'; k.onclick = openCmd; si.parentNode.appendChild(k); si.parentNode.classList.add('dx-has-kbd'); }
    var right = document.querySelector('.topbar .top-right');
    if (right && !document.getElementById('dxSearchBtn')) { var b = document.createElement('button'); b.id = 'dxSearchBtn'; b.type = 'button'; b.className = 'dx-search-btn'; b.setAttribute('aria-label', 'Search everything'); b.innerHTML = ic('search'); b.onclick = openCmd; right.insertBefore(b, right.firstChild); }
  }

  /* ── 17: saved searches with alerts (Marketplace) ── */
  function saved(v) {   /* stored searches are re-checked on read: numbers stay numbers, anything malformed is dropped */
    if (v !== undefined) return store('saved_searches', v);
    return (store('saved_searches') || []).filter(function (s) { return s && typeof s === 'object' && s.f && typeof s.f === 'object' && Array.isArray(s.f.checks); })
      .map(function (s) { s.id = +s.id || 0; s.name = String(s.name == null ? '' : s.name); if (s.fresh != null) s.fresh = +s.fresh || 0; return s; });
  }
  function mk() { return document.getElementById('mkx'); }
  function captureFilters() {
    var m = mk(); if (!m) return null;
    var checks = []; m.querySelectorAll('.filters .f-opt input').forEach(function (i) { if (i.checked) checks.push(txt(i.closest('.f-opt')).replace(/\d[\d,]*$/, '').trim()); });
    var tag = m.querySelector('.f-tag.on'), si = document.getElementById('searchIn');
    return { checks: checks, sector: tag ? txt(tag) : '', q: si ? si.value.trim() : '' };
  }
  function describe(f) {
    var parts = []; if (f.q) parts.push('“' + f.q + '”'); if (f.sector && !/^all$/i.test(f.sector.replace(/^[^A-Za-z]+/, ''))) parts.push(f.sector.replace(/^[^A-Za-z]+/, ''));
    var important = f.checks.filter(function (c) { return /GMP|CEP|FDA|ISO|EDA|Halal|China|India|UAE|Saudi|Egypt|Verified|Top rated/i.test(c); }).slice(0, 3);
    return parts.concat(important).join(' · ') || 'My marketplace filters';
  }
  function applySaved(s) {
    window.goto('market');
    setTimeout(function () {
      var m = mk(); if (!m) return;
      m.querySelectorAll('.filters .f-opt input').forEach(function (i) { var l = txt(i.closest('.f-opt')).replace(/\d[\d,]*$/, '').trim(), want = s.f.checks.indexOf(l) >= 0; if (i.checked !== want) { i.checked = want; i.dispatchEvent(new Event('change', { bubbles: true })); } });
      var tags = m.querySelectorAll('.f-tag'); Array.prototype.forEach.call(tags, function (t) { if (txt(t) === s.f.sector && !t.classList.contains('on')) t.click(); });
      var si = document.getElementById('searchIn'); if (si) { si.value = s.f.q || ''; si.dispatchEvent(new Event('input', { bubbles: true })); if (window.__mkxFilter) window.__mkxFilter(si.value); }
      if (window.updateLiveCount) window.updateLiveCount();
      var list = saved(); list.forEach(function (x) { if (x.id === s.id) { x.seen = Date.now(); x.fresh = 0; } }); saved(list); savedBar(true);
      if (D) D.toast('Showing “' + s.name + '”');
    }, 30);
  }
  function saveSearchDialog() {
    var f = captureFilters(); if (!f || !D) return;
    var m = D.modal({ title: 'Save this search', body: '<div class="dbk-f"><label for="ssName">Name</label><input id="ssName" data-req value="' + esc(describe(f)) + '"></div>' +
      '<div class="dbk-f"><label>Alert me about new matches</label><div class="ss-seg">' + [['instant', 'Instantly'], ['daily', 'Daily'], ['weekly', 'Weekly'], ['off', 'Off']].map(function (o, i) { return '<label><input type="radio" name="ssAlert" value="' + o[0] + '"' + (i === 1 ? ' checked' : '') + '> ' + o[1] + '</label>'; }).join('') + '</div></div>' +
      '<div class="dbk-note">Alerts arrive in Notifications and, in the full version, by email or WhatsApp.</div>',
      primary: { label: 'Save search', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var s = { id: Date.now(), name: b.querySelector('#ssName').value.trim(), alert: b.querySelector('input[name=ssAlert]:checked').value, f: f, seen: Date.now(), fresh: 0 };
        var list = saved(); list.unshift(s); saved(list.slice(0, 12)); savedBar(true);
        if (s.alert !== 'off' && window.NOTIFS && !window.dxLive) { window.NOTIFS.unshift({ id: Date.now(), uid: (window.ME || {}).id || 1, icon: '🔔', text: 'Saved search <b>' + esc(s.name) + '</b> — we\u2019ll alert you ' + (s.alert === 'instant' ? 'as soon as' : s.alert === 'daily' ? 'daily when' : 'weekly when') + ' new listings match', ts: 'now', read: false, type: 'search' }); if (window.updateBadges) window.updateBadges(); }
        D.toast('Search saved' + (s.alert !== 'off' ? ' — alerts ' + s.alert : ''));
      } } });
  }
  function savedBar(force) {
    var m = mk(); if (!m) return; var main = m.querySelector('#tab-browse .main'); if (!main) return;
    var list = saved(), bar = main.querySelector(':scope > .dx-saved');
    /* demo: pretend new matches arrived since you last opened each search (never in the live app) */
    list.forEach(function (s) { if (window.dxLive) { s.fresh = 0; return; } if (s.fresh == null || (Date.now() - (s.seen || 0) > 60000 && !s.fresh)) s.fresh = s.alert === 'off' ? 0 : (s.id % 4) + 1; });
    var sig = JSON.stringify(list.map(function (s) { return [s.id, s.fresh]; }));
    if (bar && bar.dataset.sig === sig && !force) return;
    if (!list.length) { if (bar) bar.remove(); return; }
    if (!bar) { bar = document.createElement('div'); bar.className = 'dx-saved'; main.insertBefore(bar, main.firstChild); }
    bar.dataset.sig = sig;
    bar.innerHTML = '<span class="ss-l">' + ic('bookmark') + 'Saved searches</span>' + list.map(function (s) { return '<span class="ss-pill"><button type="button" class="ss-go" data-id="' + s.id + '">' + esc(s.name) + (s.fresh ? '<em>' + s.fresh + ' new</em>' : '') + '</button><button type="button" class="ss-x" data-x="' + s.id + '" aria-label="Delete saved search">×</button></span>'; }).join('');
    bar.onclick = function (e) {
      var g = e.target.closest('.ss-go'), x = e.target.closest('.ss-x');
      if (g) { var s = saved().find(function (y) { return String(y.id) === g.dataset.id; }); if (s) applySaved(s); }
      if (x) { var all = saved(), gone = all.find(function (y) { return String(y.id) === x.dataset.x; }); saved(all.filter(function (y) { return y !== gone; })); savedBar(true); if (window.dxUndo && gone) window.dxUndo('Saved search deleted', function () { var l = saved(); l.unshift(gone); saved(l); savedBar(true); }); }
    };
  }
  function saveButton() {
    var m = mk(); if (!m) return; var chips = m.querySelector('.dx-chips');
    if (chips && chips.style.display !== 'none' && chips.innerHTML && !chips.querySelector('.dx-save-search')) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-save-search'; b.innerHTML = ic('bookmark') + 'Save this search'; b.onclick = saveSearchDialog;
      var clear = chips.querySelector('.dx-chip-clear'); chips.insertBefore(b, clear || null);
    }
  }
  document.addEventListener('change', function (e) { if (e.target.closest && e.target.closest('#mkx')) setTimeout(function () { C.run('save-search-button', saveButton); }, 90); });
  document.addEventListener('input', function (e) { if (e.target.id === 'searchIn') setTimeout(function () { C.run('save-search-button', saveButton); }, 90); });

  /* ── 18: profile insights (your own profile) ── */
  function insights() {
    if (window.dxLive) return;   /* demo figures only — the live app has no view statistics yet */
    var nameEl = document.querySelector('.profile-name'), me = window.ME; if (!nameEl || !me || txt(nameEl).indexOf(me.name) !== 0) return;
    var host = document.getElementById('profileTabContent'); if (!host || host.parentNode.querySelector('.dx-insights')) return;
    var views = [38, 44, 41, 57, 63, 59, 71], total = views.reduce(function (a, b) { return a + b; }, 0), prev = 262, delta = Math.round((total - prev) / prev * 100);
    var types = [['Manufacturers', 38], ['Distributors & importers', 24], ['Regulatory consultants', 18], ['Recruiters', 12], ['Other', 8]];
    var viewers = [[3, '2h'], [4, '5h'], [7, '1d'], [2, '1d'], [5, '2d']];
    var terms = [['EDA registration Egypt', 42], ['WHO-GMP manufacturer Egypt', 31], ['CMO tablets Egypt', 18], ['Pharmaceutical CEO', 12], ['GCC registration', 9]];
    var max = Math.max.apply(null, views), days = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
    var box = document.createElement('div'); box.className = 'dx-insights';
    box.innerHTML = '<div class="in-h">' + ic('chart') + 'Profile insights <span>last 7 days · only you can see this</span></div>' +
      '<div class="in-grid"><div class="in-card"><div class="in-k">Profile views</div><div class="in-big">' + total + ' <em class="up">▲ ' + delta + '%</em></div>' +
      '<div class="in-bars">' + views.map(function (v, i) { return '<span title="' + days[i] + ': ' + v + '"><i style="height:' + Math.round(v / max * 100) + '%"></i><small>' + days[i][0] + '</small></span>'; }).join('') + '</div></div>' +
      '<div class="in-card"><div class="in-k">Who viewed you</div>' + types.map(function (t) { return '<div class="in-row"><span>' + t[0] + '</span><span class="in-bar"><i style="width:' + t[1] * 2.4 + '%"></i></span><b>' + t[1] + '%</b></div>'; }).join('') + '</div>' +
      '<div class="in-card"><div class="in-k">Searches that found you</div>' + terms.map(function (t) { return '<div class="in-row"><span>“' + esc(t[0]) + '”</span><b>' + t[1] + '</b></div>'; }).join('') + '</div>' +
      '<div class="in-card"><div class="in-k">Recent viewers</div>' + viewers.map(function (v) { var u = (window.USERS || []).find(function (x) { return x.id === v[0]; }); return u ? '<button type="button" class="in-person" data-uid="' + u.id + '"><span class="in-av" style="background:' + esc(u.color || '#1a56db') + '">' + esc(u.initials || '') + '</span><span><b>' + esc(u.name) + '</b><small>' + esc((u.headline || '').split('|')[0].slice(0, 42)) + '</small></span><em>' + v[1] + '</em></button>' : ''; }).join('') + '</div></div>';
    host.parentNode.insertBefore(box, host);
    box.addEventListener('click', function (e) { var p = e.target.closest('.in-person'); if (p && window.gotoProfile) window.gotoProfile(+p.dataset.uid); });
  }

  C.onRender('for-you', forYou);
  C.onRender('search-entry', searchEntry);
  C.onRender('saved-searches', function () { savedBar(false); saveButton(); });
  C.onRender('profile-insights', insights);
})();
