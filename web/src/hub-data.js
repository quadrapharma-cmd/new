/* Company hub — data layer.
   The company is the core entity. It has sites (plants, warehouses, labs) that hold certificates and capabilities,
   products where it plays a role (registration holder / manufacturer / supplier), a team with roles that receives
   requests, credentials with source and expiry, and a track record computed only from real deals. No levels, no restrictions. */
(function () {
  function X() { return window.dxDir; }
  var __A = /^(deals|created_companies|reports|dossiers|surplus_new|groups_new|follows|saved_searches|my_requests|activity_.*|inbox_.*)$/, __O = /^(company_edits|supplier_reviews|review_meta|avl_.*|groups_state|meta_.*|quoted_.*|sqq_.*)$/, __S = /^(acting|role)$/;
  function __typed(k, v) { if (v == null) return null; if (__A.test(k)) return Array.isArray(v) ? v : null; if (__O.test(k)) return (typeof v === 'object' && !Array.isArray(v)) ? v : null; if (__S.test(k)) return typeof v === 'string' ? v : null; return v; }   /* a stored value of the wrong type is ignored, never trusted */
  function store(k, v) { if (v !== undefined) window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;   /* every write invalidates the memoised company list (directory.js) */
    if (window.dxStoreHook) { var __h = window.dxStoreHook(k, v); if (__h !== undefined) return __h; } try { if (v === undefined) return __typed(k, JSON.parse(localStorage.getItem('dx_' + k) || 'null')); localStorage.setItem('dx_' + k, JSON.stringify(v)); return true; } catch (e) { quotaToast(); return false; } }
  var __qt = 0; function quotaToast() { if (Date.now() - __qt < 3000) return; __qt = Date.now(); if (window.DBK) window.DBK.toast('Could not save — the browser storage is full. Remove large photos or old data and try again.'); }   /* a failed save is never reported as success */
  function ver() { return window.__dxStoreVer || 0; }
  var __rc = null;   /* read-only stored values parsed once per store version: a directory render asks for supplier_reviews / meta_<slug> about a thousand times */
  function cached(k) { var v = ver(); if (!__rc || __rc.v !== v) __rc = { v: v, m: Object.create(null) }; if (!(k in __rc.m)) __rc.m[k] = store(k); return __rc.m[k]; }
  function edits() { return X() && X().edits ? X().edits() : (store('company_edits') || {}); }   /* company_edits parsed once per store version, shared with the directory */
  var DAY = 864e5, NOW = function () { return Date.now(); };

  /* ── Arabic ⇄ English search ── */
  var AR = { 'ميتفورمين': 'metformin', 'باراسيتامول': 'paracetamol', 'اموكسيسيلين': 'amoxicillin', 'سيبروفلوكساسين': 'ciprofloxacin', 'اوميبرازول': 'omeprazole', 'سيفترياكسون': 'ceftriaxone',
    'فيتامين سي': 'vitamin c ascorbic', 'نياسيناميد': 'niacinamide', 'هيالورونيك': 'hyaluronic', 'اقراص': 'tablets', 'كبسولات': 'capsules', 'شراب': 'syrups', 'كريم': 'creams', 'معقم': 'sterile', 'حقن': 'sterile injectables',
    'قطره': 'eye drops', 'اكياس': 'sachets', 'فوار': 'effervescent', 'تغليف': 'packaging', 'عبوات': 'packaging bottle', 'كرتون': 'cartons', 'توزيع': 'distribution', 'مصنع': 'manufacturer', 'تجميل': 'cosmetics', 'معمل': 'lab testing', 'تحاليل': 'lab testing', 'مواد خام': 'api', 'تسجيل': 'registration regulatory' };
  function base(s) { return String(s || '').toLowerCase().replace(/[\u064B-\u0652\u0640]/g, '').replace(/[إأآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه'); }
  var ARB = {}; Object.keys(AR).forEach(function (k) { ARB[base(k)] = AR[k]; });
  function norm(s) { var b = base(s), add = []; Object.keys(ARB).forEach(function (k) { if (b.indexOf(k) >= 0) add.push(ARB[k]); }); return b + (add.length ? ' ' + add.join(' ') : ''); }
  /* a search query: Arabic terms we know are replaced by their English term, anything else is kept (so Arabic company names still match) */
  function queryWords(q) { var b = base(q); Object.keys(ARB).sort(function (x, y) { return y.length - x.length; }).forEach(function (k) { if (b.indexOf(k) >= 0) b = b.split(k).join(' ' + ARB[k].split(' ')[0] + ' '); }); return b.split(/\s+/).filter(Boolean); }
  var NAME_AR = { 'quadra-pharm': 'كوادرا فارم', 'medsinia-industries': 'مدسينيا للصناعات الدوائية', 'beauty-lab-egypt': 'بيوتي لاب مصر', 'nile-pharma-packaging': 'النيل لتغليف الأدوية', 'delta-analytical-labs': 'معامل دلتا للتحاليل',
    'alex-excipients': 'الإسكندرية لتجارة الإضافات الدوائية', 'sinai-herbal-extracts': 'سيناء للمستخلصات النباتية', 'pharaonic-logistics': 'الفرعونية للنقل المبرد', 'regpath-consulting': 'ريج باث للاستشارات التسجيلية', 'nile-valley-pharma': 'وادي النيل للأدوية',
    'obour-medica': 'العبور ميديكا للصناعات', 'alexandria-sterile': 'الإسكندرية للمستحضرات المعقمة', 'ramadan-pharma': 'رمضان فارما للصناعات', 'orient-cosmetics': 'أورينت لتصنيع مستحضرات التجميل', 'cairo-api-trading': 'القاهرة لتجارة المواد الخام',
    'suez-pharma-packaging': 'السويس لعبوات الأدوية', 'giza-bioequivalence': 'مركز الجيزة للتكافؤ الحيوي' };
  function nameAr(co) { var e = edits()[co.slug]; return (e && e.nameAr) || co.nameAr || NAME_AR[co.slug] || ''; }

  /* ── sites: certificates and capabilities belong to a site, not to the whole company ── */
  function Cf(name, expiry, src, checked) { return { name: name, expiry: expiry || '', src: src || 'Certificate document', checked: checked || '2025-11-02' }; }
  var SITES = {
    'quadra-pharm': [{ id: 'hq', name: 'Head office', type: 'Head office', city: 'Smart Village', gov: 'Giza', certs: [] },
      { id: 'giza', name: 'Giza plant', type: 'Factory', city: 'Giza', gov: 'Giza', certs: [Cf('WHO-GMP', '2026-12'), Cf('ISO 9001', '2025-06'), Cf('EDA licensed', '')] }],
    'medsinia-industries': [{ id: 'r10', name: '10th of Ramadan plant', type: 'Factory', city: '10th of Ramadan', gov: 'Sharqia', certs: [Cf('WHO-GMP', '2027-04'), Cf('ISO 9001', '2027-01')] }],
    'beauty-lab-egypt': [{ id: 'nc', name: 'Nasr City plant', type: 'Factory', city: 'Nasr City', gov: 'Cairo', certs: [Cf('ISO 22716', '2027-02'), Cf('EDA licensed', '')] }],
    'nile-pharma-packaging': [{ id: 'bea', name: 'Borg El Arab plant', type: 'Factory', city: 'Borg El Arab', gov: 'Alexandria', certs: [Cf('ISO 9001', '2026-10'), Cf('ISO 15378', '2026-10')] }],
    'delta-analytical-labs': [{ id: 'lab', name: 'New Cairo laboratory', type: 'Laboratory', city: 'New Cairo', gov: 'Cairo', certs: [Cf('ISO 17025', '2027-05')] }],
    'alex-excipients': [{ id: 'wh', name: 'Smouha warehouse', type: 'Warehouse', city: 'Smouha', gov: 'Alexandria', certs: [Cf('GDP', '2026-11')] }],
    'pharaonic-logistics': [{ id: 'ob', name: 'Obour cold store', type: 'Warehouse', city: 'Obour City', gov: 'Qalyubia', certs: [Cf('GDP', '2027-03'), Cf('ISO 9001', '2026-12')] },
      { id: 'alx', name: 'Alexandria cold store', type: 'Warehouse', city: 'Amreya', gov: 'Alexandria', certs: [Cf('GDP', '2026-08')] }],
    'regpath-consulting': [{ id: 'dk', name: 'Dokki office', type: 'Office', city: 'Dokki', gov: 'Giza', certs: [] }]
  };
  function siteType(co) { var s = co.sectors.join(' '); return /Labs/.test(s) ? 'Laboratory' : /Distribution|API/.test(s) && !/Manufacturer/.test(s) ? 'Warehouse' : /Regulatory/.test(s) ? 'Office' : 'Factory'; }
  var __sites = typeof WeakMap === 'function' ? new WeakMap() : null;   /* per company object and store version: the directory asks for sites several times per card */
  function sitesOf(co) {
    var ls = window.dxLiveSites && window.dxLiveSites[co.slug], v = ver(), m = __sites && __sites.get(co);
    if (m && m.v === v && m.ls === ls) return m.list;
    var e = edits()[co.slug];
    var list = ls || (e && Array.isArray(e.sites) ? e.sites : null) || SITES[co.slug] || [{ id: 'main', name: co.city + ' site', type: siteType(co), city: co.city, gov: co.gov, certs: (co.certs || []).map(function (n) { return Cf(n, '', co.status === 'unclaimed' ? 'Public industry list' : 'Company', '2025-06-01'); }) }];
    var cap = window.dxDir2 ? window.dxDir2.capOf(co) : null, gave = false;
    list = list.map(function (s) { var o = JSON.parse(JSON.stringify(s)); if (!o.cap && cap && !gave && (o.type === 'Factory' || o.type === 'Laboratory')) { o.cap = cap; gave = true; } if (!Array.isArray(o.certs)) o.certs = []; return o; });
    if (__sites) __sites.set(co, { v: v, ls: ls, list: list });
    return list;
  }
  function saveSites(slug, sites) { var e = store('company_edits') || {}; e[slug] = Object.assign({}, e[slug] || {}, { sites: sites }); if (!store('company_edits', e)) return false; touch(slug, 'sites'); return true; }
  function certState(c, co) {
    var t = new Date().toISOString().slice(0, 7), exp = c.expiry, st = 'valid';
    if (exp && exp < t) st = 'expired'; else if (exp) { var d = new Date(exp + '-01').getTime() - NOW(); if (d < 90 * DAY) st = 'soon'; }
    return { state: st, checked: co.status === 'verified' && c.src !== 'Public industry list' && c.src !== 'Company' };
  }
  function credentials(co) {
    var out = [];
    sitesOf(co).forEach(function (s) { (s.certs || []).forEach(function (c) { out.push(Object.assign({ site: s.name }, c, certState(c, co))); }); });
    if (window.dxDir3) window.dxDir3.membersOf(co).forEach(function (m) { out.push({ name: 'Member: ' + (m.short || m.name), full: m.name, site: 'Company', src: m.ok ? 'Confirmed by the organisation' : 'Waiting for the organisation', expiry: '', state: m.ok ? 'valid' : 'pending', checked: !!m.ok }); });
    return out;
  }

  /* ── products: the company's role in each product ── */
  var PROLE = { 'nile-valley-pharma|Metforal 500 mg': { holder: 'nile-valley-pharma', maker: 'obour-medica' } };
  function rolesOf(co, p) {
    var r = p.roles || PROLE[co.slug + '|' + p.name]; if (r) return r;
    var s = co.sectors.join(' ');
    if (/Service/.test(p.cat)) return { provider: co.slug };
    if (/API|Excipient|Packaging/.test(p.cat) && !/Manufacturer|Packaging/.test(s)) return { supplier: co.slug };
    if (/Packaging/.test(p.cat)) return { maker: co.slug };
    if (/Toll/.test(p.cat)) return { provider: co.slug };
    if (/API|Excipient/.test(p.cat)) return { supplier: co.slug };
    return { holder: co.slug, maker: co.slug };
  }
  function nm(slug) { var c = X().bySlug(slug); return c ? c.name : slug; }
  function roleLabel(co, p) {
    var r = rolesOf(co, p);
    if (r.provider) return 'Service by ' + co.name;
    if (r.supplier) return 'Supplied by ' + co.name;
    if (r.holder === co.slug && r.maker === co.slug) return 'Registration holder and manufacturer';
    if (r.holder === co.slug && r.maker) return 'Registration holder · made by ' + nm(r.maker);
    if (r.maker === co.slug && r.holder) return 'Manufacturer for ' + nm(r.holder);
    return 'Manufacturer';
  }
  /* products a company makes for others appear on the maker's page too — one maker index per company list, not a scan of every company per company */
  var __mf = null;
  function madeFor(co) {
    var list = X().companies();
    if (!__mf || __mf.list !== list) { var idx = {}; list.forEach(function (o) { (o.products || []).forEach(function (p) { var r = rolesOf(o, p); if (r.maker && r.maker !== o.slug && r.holder !== r.maker) (idx[r.maker] = idx[r.maker] || []).push({ owner: o, p: p }); }); }); __mf = { list: list, idx: idx }; }
    return __mf.idx[co.slug] || [];
  }

  /* ── corporate groups ── */
  var CGROUPS = [{ name: 'Ramadan Group', members: ['ramadan-pharma', 'orient-cosmetics'] }];
  function groupOf(co) { var g = CGROUPS.find(function (x) { return x.members.indexOf(co.slug) >= 0; }); return g ? { name: g.name, others: g.members.filter(function (s) { return s !== co.slug; }) } : null; }

  /* ── team, roles and routing ── */
  var ROLES = ['Admin', 'Management', 'Sales', 'Quality', 'Regulatory', 'HR'];
  var TEAM = {
    'quadra-pharm': [{ uid: 1, name: 'Dr. Haytham Dweedar', role: 'Admin', consent: true }, { uid: 2, name: 'Dr. Alia Mourad', role: 'Regulatory', consent: true }, { uid: null, name: 'Mona Adel', role: 'Sales', consent: true }, { uid: null, name: 'Eng. Karim Fouad', role: 'Quality', consent: false }],
    'medsinia-industries': [{ uid: 5, name: 'Eng. Omar Khaled', role: 'Admin', consent: true }, { uid: null, name: 'Hany Samir', role: 'Sales', consent: true }],
    'beauty-lab-egypt': [{ uid: 6, name: 'Dr. Sara El-Amin', role: 'Admin', consent: true }]
  };
  function teamOf(co) {
    var e = edits()[co.slug]; if (e && Array.isArray(e.team)) return e.team;
    if (TEAM[co.slug]) return TEAM[co.slug].map(function (m) { return Object.assign({}, m); });
    if (co.owner) { var u = (window.USERS || []).find(function (x) { return x.id === co.owner; }); return [{ uid: co.owner, name: u ? u.name : (window.ME || {}).name || 'Owner', role: 'Admin', consent: true }]; }
    return [];
  }
  function saveTeam(slug, team) { var e = store('company_edits') || {}; e[slug] = Object.assign({}, e[slug] || {}, { team: team }); return store('company_edits', e); }
  var ROUTE = { quote: ['Sales', 'Management', 'Admin'], surplus: ['Sales', 'Admin'], group: ['Sales', 'Admin'], service: ['Sales', 'Management', 'Admin'], questionnaire: ['Quality', 'Regulatory', 'Admin'], dossier: ['Regulatory', 'Management', 'Admin'], job: ['HR', 'Management', 'Admin'] };
  function route(slug, type) {
    var co = X().bySlug(slug); if (!co) return null;
    var t = teamOf(co), pref = ROUTE[type] || ['Admin'];
    for (var i = 0; i < pref.length; i++) { var m = t.find(function (x) { return x.role === pref[i]; }); if (m) return { name: m.name, role: m.role }; }
    return { name: co.name + ' team', role: pref[0] };
  }

  /* ── freshness: every section has a source and a date ── */
  var SECTIONS = ['about', 'products', 'sites', 'contact'];
  function metaOf(co, sec) {
    var m = (cached('meta_' + co.slug) || {})[sec];
    if (m) return m;
    if (co.status === 'unclaimed') return { src: 'Public industry list', at: new Date('2025-03-01').getTime() };
    var seedAt = { 'quadra-pharm': '2026-08-20', 'medsinia-industries': '2026-07-02', 'delta-analytical-labs': '2026-09-01', 'pharaonic-logistics': '2026-06-15', 'regpath-consulting': '2026-05-10' }[co.slug] || '2025-12-10';
    return { src: 'Company', at: new Date(seedAt).getTime() };
  }
  function touch(slug, sec, src) { var m = store('meta_' + slug) || {}; (sec ? [sec] : SECTIONS).forEach(function (s) { m[s] = { src: src || 'Company', at: NOW() }; }); store('meta_' + slug, m); log(slug, 'Updated ' + (sec || 'page')); }
  function stale(co, sec) { return NOW() - metaOf(co, sec).at > 180 * DAY; }
  function staleSections(co) { return SECTIONS.filter(function (s) { return stale(co, s); }); }

  /* ── reports of wrong information, review replies and disputes ── */
  function reports(v) { if (v === undefined) return store('reports') || []; store('reports', v); }
  function addReport(slug, section, text, fix) { var l = reports(); l.unshift({ id: 'R' + NOW(), slug: slug, section: section, text: text, fix: fix, by: (window.ME || {}).name || 'User', at: NOW(), status: 'open' }); reports(l); }
  function reviewsOf(slug) { var rv = (cached('supplier_reviews') || {})[slug] || [], meta = cached('review_meta') || {}; return rv.map(function (r) { return Object.assign({}, r, meta[r.deal] || {}); }); }
  function reviewMeta(dealId, patch) { var m = store('review_meta') || {}; m[dealId] = Object.assign({}, m[dealId] || {}, patch); store('review_meta', m); }

  /* ── activity log (inside the company) ── */
  function log(slug, text) { var k = 'activity_' + slug, l = store(k) || []; l.unshift({ at: NOW(), who: (window.ME || {}).name || 'Team', text: text }); store(k, l.slice(0, 200)); }
  function activity(slug) { return store('activity_' + slug) || []; }

  /* ── track record: computed only from real deals ── */
  function track(slug) {
    if (window.dxLiveTrack) { var __lt = window.dxLiveTrack(slug); if (__lt) return __lt; }   /* live app: the track record from the database (inert in the demo) */
    var DL = window.dxDeals; if (!DL) return { orders: 0 };
    var recv = DL.all().filter(function (d) { return d.to.slug === slug; });
    var done = recv.filter(function (d) { return ['quote', 'surplus', 'service'].indexOf(d.type) >= 0 && ['delivered', 'closed'].indexOf(d.status) >= 0; });
    var ontime = done.filter(function (d) { return d.ontime !== false; }).length, rv = (cached('supplier_reviews') || {})[slug] || [];
    var resp = recv.map(function (d) { var e = d.events.find(function (x) { return x.by === 'to'; }); return e ? (e.at - d.at) / 36e5 : null; }).filter(function (x) { return x != null; }).sort(function (a, b) { return a - b; });
    return { orders: done.length, ontime: done.length ? Math.round(ontime / done.length * 100) : null, rating: rv.length ? rv.reduce(function (a, r) { return a + r.stars; }, 0) / rv.length : null, reviews: rv.length,
      response: resp.length ? resp[Math.floor(resp.length / 2)] : null, requests: recv.length, answered: recv.filter(function (d) { return d.events.some(function (x) { return x.by === 'to'; }); }).length };
  }
  function trackLine(t) {
    if (!t.orders && !t.requests) return 'No track record yet';
    var p = []; if (t.orders) p.push(t.orders + ' completed order' + (t.orders === 1 ? '' : 's')); if (t.ontime != null) p.push(t.ontime + '% on time'); if (t.rating != null) p.push('★ ' + t.rating.toFixed(1)); if (t.response != null) p.push('replies in ~' + (t.response < 1 ? '<1' : Math.round(t.response)) + 'h');
    if (!p.length) p.push(t.requests + ' request' + (t.requests === 1 ? '' : 's') + ' received');
    return p.join(' · ');
  }

  /* ── active ── */
  var SEED_ACTIVE = { 'quadra-pharm': 2, 'medsinia-industries': 5, 'delta-analytical-labs': 1, 'pharaonic-logistics': 3, 'beauty-lab-egypt': 20, 'regpath-consulting': 40 };
  var __la = null;
  function dealTimes() {   /* last deal event per company, computed once per store version instead of a pass over every deal for every company */
    var v = ver(); if (__la && __la.v === v) return __la.m;
    var m = {}; if (window.dxDeals) window.dxDeals.all().forEach(function (d) { (d.events || []).forEach(function (e) { var s = e.by === 'to' ? d.to.slug : e.by === 'from' ? d.from.slug : null; if (s && !(m[s] >= e.at)) m[s] = e.at; }); });
    __la = { v: v, m: m }; return m;
  }
  function lastActive(co) {
    var t = 0, a = activity(co.slug)[0]; if (a) t = a.at;
    t = Math.max(t, dealTimes()[co.slug] || 0);
    SECTIONS.forEach(function (s) { var m = (cached('meta_' + co.slug) || {})[s]; if (m) t = Math.max(t, m.at); });
    if (SEED_ACTIVE[co.slug] != null) t = Math.max(t, NOW() - SEED_ACTIVE[co.slug] * DAY);
    return t;
  }
  function isActive(co) { return NOW() - lastActive(co) < 7 * DAY; }
  function isDormant(co) { return NOW() - lastActive(co) > 60 * DAY; }

  /* ── completeness + next step ── */
  function completeness(co) {
    var items = [
      ['logo', 'Add your logo', !!co.logo], ['about', 'Describe the company', (co.about || '').length > 40], ['sites', 'Add your sites (plants, warehouses)', !!((edits()[co.slug] || {}).sites || SITES[co.slug])],
      ['products', 'Add products', co.products.length > 0], ['contact', 'Add phone or email', !!(co.phone || co.email)], ['team', 'Invite your team', teamOf(co).length >= 2],
      ['certs', 'Add certificates with expiry dates', credentials(co).length > 0], ['verify', 'Get verified (free)', co.status === 'verified' || co.status === 'pending'], ['arabic', 'Add the Arabic company name', !!nameAr(co)]];
    var done = items.filter(function (i) { return i[2]; }).length;
    return { pct: Math.round(done / items.length * 100), items: items, next: items.find(function (i) { return !i[2]; }) };
  }

  /* ── ranking: one published rule ── */
  var RANK_RULE = 'Results are ordered by: how well the company matches your search, then verification, then its track record from real deals (completed orders, on-time delivery, rating), then recent activity and page completeness. Sponsored (VIP) companies appear only in the separate Sponsored row and never change this order.';
  function relevance(co, q) {
    if (!q) return 1;
    var words = queryWords(q), hay = norm(co.name + ' ' + nameAr(co) + ' ' + co.tagline + ' ' + co.sectors.join(' ') + ' ' + co.city + ' ' + co.gov + ' ' + (co.services || []).join(' ')),
      prod = norm(co.products.map(function (p) { return p.name + ' ' + (p.api || '') + ' ' + p.desc + ' ' + (p.nameAr || ''); }).join(' ') + ' ' + madeFor(co).map(function (m) { return m.p.name + ' ' + (m.p.api || ''); }).join(' '));
    var cap = sitesOf(co).map(function (s) { return s.cap ? s.cap.forms.join(' ') : ''; }).join(' ').toLowerCase();
    var score = 0;
    for (var i = 0; i < words.length; i++) { var w = words[i]; if (norm(co.name + ' ' + nameAr(co)).indexOf(w) >= 0) score += 3; else if (prod.indexOf(w) >= 0) score += 2; else if (hay.indexOf(w) >= 0 || cap.indexOf(w) >= 0) score += 1; else return 0; }
    return score;
  }
  function rankScore(co, q) {
    var r = relevance(co, q); if (!r) return -1;
    var t = track(co.slug);
    return r * 100 + (co.status === 'verified' ? 20 : 0) + Math.min(20, t.orders * 2) + (t.ontime || 0) / 10 + (t.rating || 0) * 3 + (isActive(co) ? 10 : 0) - (isDormant(co) ? 15 : 0) + completeness(co).pct / 10;
  }

  /* ── directory health (admin) ── */
  function health() {
    var cs = X().companies(), DL = window.dxDeals, all = DL ? DL.all() : [], month = all.filter(function (d) { return NOW() - d.at < 30 * DAY; });
    var recv = all.filter(function (d) { return d.to.slug; }), answered = recv.filter(function (d) { return d.events.some(function (e) { return e.by === 'to'; }); });
    var __m = cached('review_meta') || {}, disputed = Object.keys(__m).filter(function (k) { return __m[k].disputed; });
    return { total: cs.length, claimed: cs.filter(function (c) { return c.status !== 'unclaimed'; }).length, verified: cs.filter(function (c) { return c.status === 'verified'; }).length,
      complete: cs.filter(function (c) { return completeness(c).pct >= 80; }).length, avgComplete: Math.round(cs.reduce(function (a, c) { return a + completeness(c).pct; }, 0) / cs.length),
      responseRate: recv.length ? Math.round(answered.length / recv.length * 100) : null, dealsMonth: month.length, stale: cs.filter(function (c) { return staleSections(c).length; }),
      active: cs.filter(isActive).length, dormant: cs.filter(isDormant).length, openReports: reports().filter(function (r) { return r.status === 'open'; }).length, disputed: disputed.length };
  }

  window.dxHubData = { norm: norm, queryWords: queryWords, nameAr: nameAr, sitesOf: sitesOf, saveSites: saveSites, certState: certState, credentials: credentials, rolesOf: rolesOf, roleLabel: roleLabel, madeFor: madeFor, groupOf: groupOf,
    ROLES: ROLES, teamOf: teamOf, saveTeam: saveTeam, route: route, ROUTE: ROUTE, metaOf: metaOf, touch: touch, stale: stale, staleSections: staleSections, SECTIONS: SECTIONS,
    reports: reports, addReport: addReport, reviewsOf: reviewsOf, reviewMeta: reviewMeta, log: log, activity: activity, track: track, trackLine: trackLine, lastActive: lastActive, isActive: isActive, isDormant: isDormant,
    completeness: completeness, RANK_RULE: RANK_RULE, relevance: relevance, rankScore: rankScore, health: health, store: store };
})();
