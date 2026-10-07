/* Company hub — screens.
   Directory = find companies (search + filters). Company page = identity. Workspace = the company's own office.
   Marketplace = time-limited listings (surplus, licensing, group buying). Deals = every interaction (top-bar button). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function X() { return window.dxDir; } function H() { return window.dxHubData; } function X2() { return window.dxDir2; } function X3() { return window.dxDir3; } function DL() { return window.dxDeals; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  function toast(m) { D.toast(m); } function later(f) { setTimeout(f, 40); }
  function fmtDate(t) { return new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }); }
  function member(co) { return co && X().myCompanies().some(function (c) { return c.slug === co.slug; }); }
  var ACTIVITIES = ['All', 'Manufacturer', 'Cosmetics', 'CMO / Toll', 'API & excipients', 'Packaging', 'Labs & testing', 'Distribution', 'Regulatory & consulting', 'Supplements'];
  var GOVS = ['All governorates', 'Cairo', 'Giza', 'Alexandria', 'Sharqia', 'Qalyubia', 'Ismailia'];
  var CERTS = ['WHO-GMP', 'ISO 9001', 'ISO 22716', 'ISO 17025', 'GDP', 'EDA licensed'];

  /* ════════ directory ════════ */
  function filtered(S) {
    var q = S.q || '', list = X().companies().map(function (co) { return { co: co, score: H().rankScore(co, q) }; }).filter(function (x) { return x.score >= 0; });
    list = list.filter(function (x) {
      var co = x.co, sites = H().sitesOf(co);
      if (S.sector && S.sector !== 'All' && co.sectors.indexOf(S.sector) < 0) return false;
      if (S.gov && S.gov !== 'All governorates' && !sites.some(function (s) { return s.gov === S.gov; }) && co.gov !== S.gov) return false;
      if (S.certs && S.certs.length && !S.certs.every(function (c) { return H().credentials(co).some(function (k) { return k.name === c && k.state !== 'expired'; }); })) return false;
      if (S.verified && co.status !== 'verified') return false;
      if (S.activeOnly && !H().isActive(co)) return false;
      if (S.form) { var cap = sites.map(function (s) { return s.cap; }).filter(Boolean).find(function (c) { return c.forms.indexOf(S.form) >= 0; }); if (!cap) return false; x.cap = cap; x.next = cap.slots.filter(function (m) { return m >= (S.from || 0); }).sort(function (a, b) { return a - b; })[0]; if (S.from > 0 && x.next == null) return false; }
      return true;
    });
    if (S.sort === 'name') list.sort(function (a, b) { return a.co.name.localeCompare(b.co.name); });
    else if (S.sort === 'newest') list.sort(function (a, b) { return (b.co.createdAt || b.co.founded || 0) - (a.co.createdAt || a.co.founded || 0); });
    else list.sort(function (a, b) { return b.score - a.score; });
    return list;
  }
  function whoMakes(q) {
    if (!q || q.length < 4 || !X2()) return '';
    var nq = H().norm(q), inn = X2().INN.find(function (n) { return nq.indexOf(n.toLowerCase()) >= 0 || n.toLowerCase().indexOf(nq.split(' ')[0]) === 0; }); if (!inn) return '';
    var rows = []; X().companies().forEach(function (co) { co.products.forEach(function (p) { var a = X2().apiOf(p); if (a && (a.toLowerCase() === inn.toLowerCase() || (inn === 'Vitamin C' && a === 'Ascorbic acid'))) rows.push({ co: co, p: p }); }); });
    if (!rows.length) return '';
    return '<section class="wm-panel"><div class="wm-h">' + ic('flask') + '<b>Who makes ' + esc(inn) + ' in Egypt</b><span>' + rows.length + ' products</span></div>' + rows.slice(0, PAGE).map(function (r) {   /* one page of rows at most; the directory below lists every company */
      return '<div class="wm-row"><img src="' + X().pimg(r.co, r.p) + '" alt=""><span class="wm-b"><b>' + esc(r.p.name) + '</b><small>' + esc(H().roleLabel(r.co, r.p)) + ' · ' + esc(r.p.cat) + '</small></span><button type="button" class="dx-colink" data-hopen="' + esc(r.co.slug) + '" data-htab="products">' + esc(r.co.name) + '</button><button type="button" class="dr-btn p sm" data-hrfq="' + esc(r.co.slug) + '" data-hp="' + r.p.id + '">Request a quote</button></div>'; }).join('') + '</section>';
  }
  function cardCtx() { return { picks: window.dxPicks ? window.dxPicks.get() : [], act0: X().mine() }; }   /* computed once per render, not once per card */
  function cover(co) { return (X().cssUrl && X().cssUrl(co.cover)) || '--cc:' + X().safeColor(co.color); }   /* only a safe URL reaches the style attribute */
  function card(x, ctx) {
    ctx = ctx || cardCtx();
    var co = x.co, t = H().track(co.slug), sites = H().sitesOf(co), ar = H().nameAr(co), picks = ctx.picks, act0 = ctx.act0, own = !!(act0 && act0.slug === co.slug);
    return '<article class="dr-card hb-card" data-slug="' + esc(co.slug) + '"><div class="dr-cover" style="' + cover(co) + '"></div><div class="dr-card-b">' + X().logo(co, 'dr-logo') +
      '<div class="dr-name">' + esc(co.name) + (co.status === 'verified' ? '<span class="dr-seal" title="Verified: registry and tax card checked">' + ic('seal') + '</span>' : '') + (H().isActive(co) ? '<span class="hb-active">Active</span>' : '') + (co.status === 'unclaimed' ? '<span class="dr-pend unc">Unclaimed</span>' : '') + '</div>' +
      (ar ? '<div class="hb-ar" lang="ar" dir="rtl">' + esc(ar) + '</div>' : '') + '<div class="dr-meta">' + esc(co.sectors.join(' · ')) + ' · ' + esc(co.city) + ' · ' + sites.length + ' site' + (sites.length === 1 ? '' : 's') + '</div><p class="dr-tag">' + esc(co.tagline) + '</p>' +
      (x.cap ? '<div class="hb-cap">' + ic('factory') + esc(x.cap.capacity) + ' · ' + (x.next != null ? '<b>free from ' + X2().MONTHS[x.next] + '</b>' : 'no free slot soon') + '</div>' : '') +
      '<div class="hb-track' + (t.orders ? '' : ' none') + '">' + ic('chart') + esc(H().trackLine(t)) + '</div>' +
      '<div class="dr-acts"><button type="button" class="dr-btn p" data-hopen="' + esc(co.slug) + '">View page</button>' + (own ? '<span class="hb-own">Your company</span>' : '<button type="button" class="dr-btn" data-hrfq="' + esc(co.slug) + '">Request a quote</button><label class="dr-pick" data-hpick="' + esc(co.slug) + '"><input type="checkbox"' + (picks.indexOf(co.slug) >= 0 ? ' checked' : '') + '> Select</label>') + '</div></div></article>';
  }
  var PAGE = 60;   /* cards drawn per page; the rest come with "Show more" (thousands of cards at once froze the tab) */
  function renderDirectory(c, S) {
    var list = filtered(S), vip = X().companies().filter(function (co) { return X().isVip(co); }), ctx = cardCtx();
    var forms = X2() ? X2().FORMS : [], months = X2() ? X2().MONTHS : [];
    var fsig = [S.q, S.sector, S.gov, (S.certs || []).join(','), S.verified, S.activeOnly, S.form, S.from, S.sort].join('|'); if (S.fsig !== fsig) { S.fsig = fsig; S.shown = PAGE; }   /* a new search starts at the first page */
    var shown = list.slice(0, S.shown || PAGE);
    c.innerHTML = '<div id="dxDir" class="hub"><section class="dr-hero hb-hero"><div><span class="dr-k">COMPANY DIRECTORY</span><h1 class="dr-h">Find any pharma company in Egypt</h1>' +
      '<p class="dr-sub">Search by name, product, active ingredient or what a plant can manufacture — in Arabic or English.</p></div>' +
      '<div class="dr-hero-cta"><button type="button" class="dr-btn p lg" data-hadd="1">' + ic('plus') + 'Add or claim your company</button></div></section>' +
      '<div class="dr-bar"><div class="dr-search">' + ic('search') + '<input type="search" id="hbQ" placeholder="Company, product or ingredient — e.g. ميتفورمين or Metformin" value="' + esc(S.q || '') + '" aria-label="Search companies"></div>' +
      '<select id="hbSort" aria-label="Order"><option value="best"' + (!S.sort || S.sort === 'best' ? ' selected' : '') + '>Best match</option><option value="name"' + (S.sort === 'name' ? ' selected' : '') + '>Name A–Z</option><option value="newest"' + (S.sort === 'newest' ? ' selected' : '') + '>Newest</option></select>' +
      '<button type="button" class="dr-link" data-hrule="1">How results are ordered</button></div>' +
      '<div class="dr-chips">' + ACTIVITIES.map(function (a) { return '<button type="button" class="dr-chip' + ((S.sector || 'All') === a ? ' on' : '') + '" data-hsec="' + esc(a) + '">' + esc(a) + '</button>'; }).join('') + '</div>' +
      '<div class="hb-filters"><label>Can manufacture <select id="hbForm"><option value="">Any</option>' + forms.map(function (f) { return '<option' + (S.form === f ? ' selected' : '') + '>' + f + '</option>'; }).join('') + '</select></label>' +
      (S.form ? '<label>Free from <select id="hbFrom">' + months.map(function (m, i) { return '<option value="' + i + '"' + ((S.from || 0) === i ? ' selected' : '') + '>' + m + '</option>'; }).join('') + '</select></label>' : '') +
      '<label>Governorate <select id="hbGov">' + GOVS.map(function (g) { return '<option' + ((S.gov || 'All governorates') === g ? ' selected' : '') + '>' + g + '</option>'; }).join('') + '</select></label>' +
      '<label class="dr-ver"><input type="checkbox" id="hbVer"' + (S.verified ? ' checked' : '') + '> Verified</label><label class="dr-ver"><input type="checkbox" id="hbAct"' + (S.activeOnly ? ' checked' : '') + '> Active this week</label></div>' +
      '<div class="dr-chips dr-certs"><span>Certified:</span>' + CERTS.map(function (x) { return '<button type="button" class="dr-chip sm' + ((S.certs || []).indexOf(x) >= 0 ? ' on' : '') + '" data-hcert="' + esc(x) + '">' + esc(x) + '</button>'; }).join('') + '</div>' +
      whoMakes(S.q) +
      (vip.length && !S.q ? '<section class="dr-vipstrip"><div class="dr-vs-h">' + ic('crown') + '<b>Sponsored</b><span>Paid placement · does not affect the order below</span></div><div class="dr-vs-row">' + vip.map(function (co) { return '<button type="button" class="dr-vs-card" data-hopen="' + esc(co.slug) + '">' + X().logo(co, 'dr-logo sm') + '<span><b>' + esc(co.name) + '</b><small>' + esc(co.sectors[0]) + ' · ' + esc(co.city) + '</small></span></button>'; }).join('') + '</div></section>' : '') +
      '<div class="dr-count">' + list.length + ' compan' + (list.length === 1 ? 'y' : 'ies') + '</div>' +
      (list.length ? '<div class="dr-grid">' + shown.map(function (x) { return card(x, ctx); }).join('') + '</div>' + (shown.length < list.length ? '<div class="dr-count"><button type="button" class="dr-link" data-hmore="1">Show more (' + shown.length + ' of ' + list.length + ')</button></div>' : '') : '<div class="dbk-empty">No company matches. <button type="button" class="dr-link" data-hreset="1">Clear filters</button></div>') +
      '<div class="hb-foot"><button type="button" class="dr-link" data-hhealth="1">' + ic('chart') + 'Directory health</button></div></div>';
    var ill = c.querySelector('.dr-ill'); if (ill && window.dxIll) ill.innerHTML = window.dxIll('factory');
    if (window.dxPicks) window.dxPicks.draw();
  }

  /* ════════ company page ════════ */
  function credChips(co) { return H().credentials(co).filter(function (k) { return k.state !== 'expired'; }).slice(0, 6).map(function (k) { return '<span class="hb-cred ' + (k.checked ? 'ok' : 'unk') + '" title="' + esc(k.site + ' · ' + k.src + (k.expiry ? ' · expires ' + k.expiry : '')) + '">' + ic(k.checked ? 'seal' : 'doc') + esc(k.name) + '</span>'; }).join(''); }
  function srcLine(co, sec) { var m = H().metaOf(co, sec), st = H().stale(co, sec); return '<div class="hb-src' + (st ? ' old' : '') + '">' + (st ? ic('warning') + 'May be outdated · ' : '') + 'Source: ' + esc(m.src) + ' · updated ' + fmtDate(m.at) + '</div>'; }
  function renderCompany(c, co, S) {
    var mem = member(co), act = X().mine(), here = !!(act && act.slug === co.slug), t = H().track(co.slug), ar = H().nameAr(co), grp = H().groupOf(co), sites = H().sitesOf(co), jobs = X().jobsOf(co), offers = X().offersOf(co), revs = H().reviewsOf(co.slug);
    var listings = offers.length + (X3() ? X3().dossiers().filter(function (d) { return d.slug === co.slug; }).length + X3().surplus().filter(function (s) { return s.slug === co.slug; }).length + X3().groupDeals().filter(function (g) { return g.to.slug === co.slug || g.from.slug === co.slug; }).length : 0);
    var tab = S.tab || 'overview', tabs = [['overview', 'Overview'], ['products', 'Products (' + (co.products.length + H().madeFor(co).length) + ')'], ['sites', 'Sites (' + sites.length + ')'], ['listings', 'Listings (' + listings + ')'], ['jobs', 'Jobs (' + jobs.length + ')'], ['reviews', 'Reviews (' + revs.length + ')'], ['contact', 'Contact']];
    var avl = act && act.slug !== co.slug && X3() ? (X3().avl() || {})[co.slug] : null;
    var head = '<button type="button" class="cp-back" data-hback="1">' + ic('compass') + 'All companies</button>' +
      '<header class="cp-hero"><div class="cp-cover" style="' + cover(co) + '"></div><div class="cp-id">' + X().logo(co, 'cp-logo') +
      '<div class="cp-idt"><h1 class="cp-name">' + esc(co.name) + (co.status === 'verified' ? '<span class="dr-seal" title="Verified: registry and tax card checked">' + ic('seal') + '</span>' : '') + (X().isVip(co) ? '<span class="dr-vip">' + ic('crown') + 'Sponsored</span>' : '') + (H().isActive(co) ? '<span class="hb-active">Active</span>' : '') + '</h1>' +
      (ar ? '<div class="hb-ar lg" lang="ar" dir="rtl">' + esc(ar) + '</div>' : '') + '<p class="cp-tagline">' + esc(co.tagline) + '</p><div class="cp-meta">' + esc(co.sectors.join(' · ')) + ' · ' + esc(co.city) + ', ' + esc(co.gov) + (grp ? ' · part of <b>' + esc(grp.name) + '</b>' : '') + '</div>' +
      '<div class="hb-track big' + (t.orders ? '' : ' none') + '">' + ic('chart') + esc(H().trackLine(t)) + '</div><div class="hb-creds">' + credChips(co) + '</div></div>' +
      '<div class="cp-cta">' + (mem ? '<button type="button" class="dr-btn' + (here ? ' p' : '') + '" data-hws="' + esc(co.slug) + '">' + ic('building') + 'Open company workspace</button>' : '') +
        (here ? '' : '<button type="button" class="dr-btn p" data-hrfq="' + esc(co.slug) + '">Request a quote</button><button type="button" class="dr-btn" data-hmsg="1">' + ic('chat') + 'Message</button><button type="button" class="dr-btn" data-hfollow="1">' + (X().followed(co.slug) ? '✓ Following' : '+ Follow') + '</button>') +
      (act && act.slug !== co.slug && X3() ? '<span class="avl-ctl"><select id="hbAvl" aria-label="Supplier status for ' + esc(act.name) + '"><option value="">Supplier status: not on list</option>' + Object.keys(X3().AVL).map(function (k) { return '<option value="' + k + '"' + (avl && avl.status === k ? ' selected' : '') + '>' + X3().AVL[k][0] + '</option>'; }).join('') + '</select><button type="button" class="dr-btn sm" data-hsq="1">' + ic('clipboard') + 'Questionnaire</button></span>' : '') +
      '<button type="button" class="dr-btn" data-hpdf="1">' + ic('doc') + 'Profile PDF</button><button type="button" class="dr-btn" data-hqr="1">' + ic('target') + 'QR</button><button type="button" class="dr-link" data-hreport="1">Report wrong information</button></div></div></header>' +
      (co.status === 'unclaimed' ? '<div class="cp-banner cp-claim">' + ic('building') + '<span><b>Is this your company?</b> This page was built from public industry lists. Claim it to manage it and receive requests.</span><button type="button" class="dr-btn p sm" data-hclaim="1">Claim this page</button></div>' : '') +
      (H().staleSections(co).length ? '<div class="cp-banner pend">' + ic('warning') + '<span>Some information on this page was last updated more than 6 months ago (' + H().staleSections(co).join(', ') + ').</span></div>' : '') +
      '<nav class="cp-tabs" role="tablist">' + tabs.map(function (x) { return '<button type="button" role="tab" aria-selected="' + (tab === x[0]) + '" class="cp-tab' + (tab === x[0] ? ' on' : '') + '" data-htab2="' + x[0] + '">' + esc(x[1]) + '</button>'; }).join('') + '</nav>';
    var body = '';
    if (tab === 'overview') {
      var team = H().teamOf(co).filter(function (m) { return m.consent; }), look = X3() ? X3().lookingOf(co) : [];
      body = '<div class="cp-two"><section class="cp-sec"><h3>About</h3><p class="cp-about">' + esc(co.about || 'No description yet.') + '</p>' + srcLine(co, 'about') +
        (look.length ? '<h3 style="margin-top:16px">Looking for</h3><div class="cap-forms">' + look.map(function (l) { return '<span class="lk">' + esc(l) + '</span>'; }).join('') + '</div>' : '') +
        (grp ? '<h3 style="margin-top:16px">' + esc(grp.name) + '</h3><div class="hb-grp">' + grp.others.map(function (s) { var o = X().bySlug(s); return o ? '<button type="button" class="dx-colink" data-hopen="' + esc(s) + '">' + esc(o.name) + '</button>' : ''; }).join(' · ') + '</div>' : '') + '</section>' +
        '<aside class="cp-sec"><h3>Credentials</h3>' + (H().credentials(co).length ? H().credentials(co).map(function (k) { return '<div class="hb-crow"><span class="hb-cred ' + (k.checked ? 'ok' : 'unk') + '">' + ic(k.checked ? 'seal' : 'doc') + esc(k.name) + '</span><small>' + esc(k.site) + ' · ' + esc(k.src) + (k.expiry ? ' · ' + (k.state === 'expired' ? '<b class="exp">expired ' + esc(k.expiry) + '</b>' : k.state === 'soon' ? '<b class="soon">expires ' + esc(k.expiry) + '</b>' : 'valid to ' + esc(k.expiry)) : '') + '</small></div>'; }).join('') : '<p class="cp-muted">No credentials listed.</p>') +
        (team.length ? '<h3 style="margin-top:16px">People</h3>' + team.map(function (m) { return '<div class="hb-person"><span class="cp-pav" style="background:#1a56db">' + esc(X().initials(m.name)) + '</span><span><b>' + esc(m.name) + '</b><small>' + esc(m.role) + '</small></span></div>'; }).join('') : '') + '</aside></div>';
    } else if (tab === 'products') {
      var made = H().madeFor(co);
      body = '<div class="cp-pgrid">' + co.products.map(function (p) { return '<article class="cp-prod"><button type="button" class="cp-pimg" data-hpd="' + p.id + '"><img src="' + X().pimg(co, p) + '" alt="' + esc(p.name) + '"></button><div class="cp-pb"><span class="cp-pcat">' + esc(p.cat) + '</span><b>' + esc(p.name) + '</b>' + (p.nameAr ? '<span class="hb-ar" lang="ar" dir="rtl">' + esc(p.nameAr) + '</span>' : '') +
        '<span class="hb-role">' + esc(H().roleLabel(co, p)) + '</span>' + ((p.api || (X2() && X2().apiOf(p))) ? '<small class="hb-api">' + ic('flask') + esc(p.api || X2().apiOf(p)) + '</small>' : '') + '<p>' + esc(p.desc) + '</p><div class="cp-pmeta">' + (p.price ? '<span class="cp-price">' + esc(p.price) + '</span>' : '<span class="cp-por">Price on request</span>') + (p.moq ? '<span>MOQ ' + esc(p.moq) + '</span>' : '') + '</div>' +
        (here ? '' : '<button type="button" class="dr-btn p sm" data-hrfq="' + esc(co.slug) + '" data-hp="' + p.id + '">Request a quote</button>') + '</div></article>'; }).join('') +
        made.map(function (m) { return '<article class="cp-prod"><div class="cp-pimg"><img src="' + X().pimg(m.owner, m.p) + '" alt=""></div><div class="cp-pb"><span class="cp-pcat">' + esc(m.p.cat) + '</span><b>' + esc(m.p.name) + '</b><span class="hb-role">Manufactured here for ' + esc(m.owner.name) + '</span><p>' + esc(m.p.desc) + '</p></div></article>'; }).join('') + '</div>' + srcLine(co, 'products');
    } else if (tab === 'sites') {
      body = '<div class="hb-sites">' + sites.map(function (s) { return '<section class="cp-sec hb-site"><h3>' + ic(s.type === 'Warehouse' ? 'box' : s.type === 'Laboratory' ? 'flask' : s.type === 'Factory' ? 'factory' : 'building') + esc(s.name) + '<small>' + esc(s.type) + ' · ' + esc(s.city) + ', ' + esc(s.gov) + '</small></h3>' +
        '<div class="hb-creds">' + (s.certs || []).map(function (k) { var st = H().certState(k, co); return '<span class="hb-cred ' + (st.checked ? 'ok' : 'unk') + (st.state === 'expired' ? ' exp' : '') + '" title="' + esc(k.src) + '">' + ic(st.checked ? 'seal' : 'doc') + esc(k.name) + (k.expiry ? ' · ' + (st.state === 'expired' ? 'expired ' : 'to ') + esc(k.expiry) : '') + '</span>'; }).join('') + '</div>' +
        (s.cap ? '<div class="cap-forms">' + s.cap.forms.map(function (f) { return '<span>' + esc(f) + '</span>'; }).join('') + '</div><div class="cp-facts"><div><small>Minimum batch</small><b>' + esc(s.cap.minBatch) + '</b></div><div><small>Capacity</small><b>' + esc(s.cap.capacity) + '</b></div></div>' +
          '<div class="cap-slots"><small>Free production slots</small><div>' + X2().MONTHS.map(function (m, i) { var f = s.cap.slots.indexOf(i) >= 0; return '<span class="cap-m' + (f ? ' free' : '') + '">' + esc(m) + '<em>' + (f ? 'Free' : 'Booked') + '</em></span>'; }).join('') + '</div></div>' : '') + '</section>'; }).join('') + '</div>' + srcLine(co, 'sites');
    } else if (tab === 'listings') {
      var ds = X3() ? X3().dossiers().filter(function (d) { return d.slug === co.slug; }) : [], sp = X3() ? X3().surplus().filter(function (s) { return s.slug === co.slug; }) : [], gs = X3() ? X3().groupDeals().filter(function (g) { return g.to.slug === co.slug || g.from.slug === co.slug; }) : [];
      body = '<section class="cp-sec"><h3>Live listings</h3><p class="cp-muted">Time-limited offers in the Marketplace. The permanent catalogue is under Products.</p>' +
        offers.map(function (o) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('box') + '</span><span><b>' + esc(o.t) + '</b><small>' + esc(o.type) + '</small></span><button type="button" class="dr-btn sm" data-hoffer="' + esc(o.t) + '">View in Marketplace</button></div>'; }).join('') +
        sp.map(function (s) { return '<div class="cp-job"><span class="sp-off">−' + esc(s.off) + '%</span><span><b>' + esc(s.product) + '</b><small>Surplus · ' + esc(s.qty) + ' · batch ' + esc(s.batch) + '</small></span>' + (here ? '' : '<button type="button" class="dr-btn p sm" data-hsurp="' + esc(s.id) + '">Make an offer</button>') + '</div>'; }).join('') +
        ds.map(function (d) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('doc') + '</span><span><b>' + esc(d.product) + '</b><small>Licensing · ' + esc(d.status) + ' · ' + esc(d.deal) + '</small></span>' + (here ? '' : '<button type="button" class="dr-btn p sm" data-hdos="' + esc(d.id) + '">Request details</button>') + '</div>'; }).join('') +
        gs.map(function (g) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('users') + '</span><span><b>' + esc(g.lines.product) + '</b><small>Group buying · ' + X3().total(g).toLocaleString() + ' of ' + g.lines.target.toLocaleString() + ' ' + esc(g.lines.unit) + ' · ' + esc(DL().label(g.status)) + '</small></span><button type="button" class="dr-btn sm" data-hgroups="1">Open</button></div>'; }).join('') +
        (offers.length + sp.length + ds.length + gs.length ? '' : '<p class="cp-muted">No live listings.</p>') + '</section>';
    } else if (tab === 'jobs') {
      body = '<section class="cp-sec"><h3>Open positions</h3>' + (jobs.length ? jobs.map(function (j, i) { return '<div class="cp-job"><span class="cp-jic">' + ic('briefcase') + '</span><span><b>' + esc(j.t) + '</b><small>' + esc(j.type) + ' · ' + esc(j.loc) + '</small></span><button type="button" class="dr-btn p sm" data-hjob="' + i + '">Apply</button></div>'; }).join('') : '<p class="cp-muted">No open positions.</p>') + '</section>';
    } else if (tab === 'reviews') {
      body = '<section class="cp-sec"><h3>Reviews from completed orders</h3><p class="cp-muted">Only buyers who received an order can review. The company can reply or ask Drugbox to check a review.</p>' + (revs.length ? revs.map(function (r) { return '<div class="hb-rev"><b>' + '★'.repeat(r.stars) + '<span>' + '★'.repeat(5 - r.stars) + '</span></b> <small>' + esc(r.from) + ' · ' + fmtDate(r.at) + (r.disputed ? ' · <span class="mr-st st-viewed">Under review by Drugbox</span>' : '') + '</small><p>' + esc(r.note || '') + '</p>' + (r.reply ? '<div class="hb-reply"><b>' + esc(co.name) + ' replied:</b> ' + esc(r.reply) + '</div>' : '') + '</div>'; }).join('') : '<p class="cp-muted">No reviews yet.</p>') + '</section>';
    } else if (tab === 'contact') {
      var rt = H().route(co.slug, 'quote');
      body = '<div class="cp-two"><section class="cp-sec"><h3>Contact</h3><div class="cp-contact">' + [[co.phone, 'tel:' + String(co.phone || '').replace(/\s/g, ''), 'chat', 'Phone'], [co.email, 'mailto:' + co.email, 'send', 'Email'], [co.whatsapp ? 'Message on WhatsApp' : '', 'https://wa.me/' + co.whatsapp, 'chat', 'WhatsApp'], [co.website, 'https://' + co.website, 'globe', 'Website'], [co.address, 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(co.address || ''), 'pin', 'Address · directions']].filter(function (x) { return x[0]; }).map(function (x) { return '<a href="' + esc(x[1]) + '"' + (/^http/.test(x[1]) ? ' target="_blank" rel="noopener"' : '') + '>' + ic(x[2]) + '<span><small>' + x[3] + '</small>' + esc(x[0]) + '</span></a>'; }).join('') + '</div>' + srcLine(co, 'contact') + '</section>' +
        '<section class="cp-sec"><h3>Who answers</h3><p class="cp-muted">Quote requests go to <b>' + esc(rt.name) + '</b> (' + esc(rt.role) + '). Questionnaires go to ' + esc(H().route(co.slug, 'questionnaire').name) + '; job applications to ' + esc(H().route(co.slug, 'job').name) + '.</p>' + (here ? '' : '<div class="cp-req-btns"><button type="button" class="dr-btn p" data-hrfq="' + esc(co.slug) + '">' + ic('cart') + 'Request a quote</button><button type="button" class="dr-btn" data-hmsg="1">' + ic('chat') + 'Send a message</button></div>') + '</section></div>';
    }
    c.innerHTML = '<div id="dxDir" class="hub cp">' + head + '<div class="cp-body">' + body + '</div></div>';
  }

  /* ════════ company workspace ════════ */
  var WTABS = [['overview', 'Overview'], ['page', 'Page'], ['sites', 'Sites'], ['team', 'Team'], ['deals', 'Deals'], ['suppliers', 'Suppliers'], ['listings', 'Listings'], ['reports', 'Reports & reviews'], ['activity', 'Activity'], ['plan', 'Plan & verification']];
  function renderWorkspace(c, co, S) {
    var tab = S.wsTab || 'overview', cp = H().completeness(co), t = H().track(co.slug), body = '';
    if (tab === 'overview') {
      var waiting = DL().all().filter(function (d) { return d.to.slug === co.slug && DL().actionsFor(d, 'to').length; }).length, stale = H().staleSections(co);
      body = '<div class="cp-two"><section class="cp-sec"><h3>Page completeness</h3><div class="hb-meter"><i style="width:' + cp.pct + '%"></i></div><b class="hb-pct">' + cp.pct + '%</b>' +
        '<ul class="hb-check">' + cp.items.map(function (i) { return '<li class="' + (i[2] ? 'ok' : '') + '">' + ic(i[2] ? 'seal' : 'plus') + esc(i[1]) + (i[2] ? '' : ' <button type="button" class="dr-link" data-wgo="' + i[0] + '">Do it</button>') + '</li>'; }).join('') + '</ul></section>' +
        '<section class="cp-sec"><h3>At a glance</h3><div class="cp-stats"><div><small>Waiting for you</small><b>' + waiting + '</b></div><div><small>Open requests</small><b>' + DL().openCount(co.slug) + '</b></div><div><small>Completed orders</small><b>' + t.orders + '</b></div><div><small>On time</small><b>' + (t.ontime != null ? t.ontime + '%' : '—') + '</b></div></div>' +
        '<div class="hb-track big' + (t.orders ? '' : ' none') + '">' + ic('chart') + esc(H().trackLine(t)) + '</div><p class="cp-muted">' + (H().isActive(co) ? 'Your page shows as <b>Active</b> this week.' : 'Reply to a request or update your page to show as Active.') + '</p>' +
        (stale.length ? '<div class="cp-banner pend">' + ic('warning') + '<span>Please review: ' + esc(stale.join(', ')) + ' (older than 6 months).</span><button type="button" class="dr-btn sm" data-wconfirm="1">Still correct</button></div>' : '') + '</section></div>';
    } else if (tab === 'page') {
      var look = X3() ? X3().lookingOf(co) : [];
      body = '<section class="cp-sec"><h3>Public page</h3><p class="cp-muted">Logo, cover, about, products, services and contact.</p><button type="button" class="dr-btn p" data-wedit="1">' + ic('pen') + 'Edit page</button> <button type="button" class="dr-btn" data-hopen="' + esc(co.slug) + '">View as visitors see it</button></section>' +
        '<section class="cp-sec"><h3>Arabic name</h3><div class="dbk-row"><div class="dbk-f"><input id="wAr" lang="ar" dir="rtl" value="' + esc(H().nameAr(co)) + '" placeholder="اسم الشركة بالعربي"></div><button type="button" class="dr-btn" data-war="1">Save</button></div></section>' +
        '<section class="cp-sec"><h3>What we are looking for</h3><div class="cap-forms">' + (look.map(function (l) { return '<span class="lk">' + esc(l) + '</span>'; }).join('') || '<span class="cp-muted">Nothing yet</span>') + '</div><button type="button" class="dr-btn sm" data-wlook="1">' + ic('pen') + 'Edit</button></section>' +
        '<section class="cp-sec"><h3>Memberships</h3>' + (X3() ? X3().membersOf(co).map(function (m) { return '<span class="mb-badge' + (m.ok ? '' : ' pend') + '">' + ic('seal') + esc(m.name) + (m.ok ? '' : ' · waiting for the organisation') + '</span>'; }).join(' ') : '') + ' <button type="button" class="dr-btn sm" data-wmember="1">' + ic('plus') + 'Add membership</button></section>';
    } else if (tab === 'sites') {
      body = H().sitesOf(co).map(function (s, i) { return '<section class="cp-sec hb-site"><h3>' + esc(s.name) + '<small>' + esc(s.type) + ' · ' + esc(s.city) + ', ' + esc(s.gov) + '</small></h3>' +
        '<div class="hb-creds">' + (s.certs || []).map(function (k, j) { var st = H().certState(k, co); return '<span class="hb-cred ' + (st.checked ? 'ok' : 'unk') + (st.state === 'expired' ? ' exp' : '') + '">' + esc(k.name) + (k.expiry ? ' · ' + esc(k.expiry) : '') + ' <button type="button" class="hb-x" data-wcdel="' + i + ':' + j + '" aria-label="Remove">×</button></span>'; }).join('') + '<button type="button" class="dr-btn sm" data-wcadd="' + i + '">' + ic('plus') + 'Certificate</button></div>' +
        (s.cap ? '<div class="cap-slots"><small>Free production slots — tap to change</small><div>' + X2().MONTHS.map(function (m, k) { var f = s.cap.slots.indexOf(k) >= 0; return '<button type="button" class="cap-m' + (f ? ' free' : '') + '" data-wslot="' + i + ':' + k + '">' + esc(m) + '<em>' + (f ? 'Free' : 'Booked') + '</em></button>'; }).join('') + '</div></div>' : '') +
        '<div class="hb-row"><button type="button" class="dr-btn sm" data-wcap="' + i + '">' + ic('factory') + (s.cap ? 'Edit capabilities' : 'Add manufacturing capabilities') + '</button><button type="button" class="dr-btn sm dl-d" data-wsdel="' + i + '">Remove site</button></div></section>'; }).join('') +
        '<button type="button" class="dr-btn p" data-wsadd="1">' + ic('plus') + 'Add a site</button>';
    } else if (tab === 'team') {
      var team = H().teamOf(co), me = window.ME || {};
      body = '<section class="cp-sec"><h3>Team</h3><p class="cp-muted">Roles decide who receives each kind of request. A person appears on the public page only after they agree (personal data law 151/2020).</p>' +
        team.map(function (m, i) { return '<div class="hb-tm"><span class="cp-pav" style="background:#1a56db">' + esc(X().initials(m.name)) + '</span><span class="hb-tmn"><b>' + esc(m.name) + (m.uid === me.id ? ' (you)' : '') + '</b><small>' + (m.consent ? 'Shown on the public page' : 'Waiting for their agreement — not shown publicly') + '</small></span>' +
          '<select data-wrole="' + i + '" aria-label="Role">' + H().ROLES.map(function (r) { return '<option' + (m.role === r ? ' selected' : '') + '>' + r + '</option>'; }).join('') + '</select>' + (m.uid === me.id ? '<button type="button" class="dr-btn sm" data-wconsent="' + i + '">' + (m.consent ? 'Hide me' : 'Show me') + '</button>' : '') + '<button type="button" class="hb-x" data-wtdel="' + i + '" aria-label="Remove">×</button></div>'; }).join('') +
        '<button type="button" class="dr-btn p sm" data-winvite="1">' + ic('plus') + 'Invite a colleague</button></section>' +
        '<section class="cp-sec"><h3>Who receives what</h3><table class="cp-spec">' + Object.keys(H().ROUTE).map(function (k) { var r = H().route(co.slug, k); return '<tr><td>' + esc(DL().FLOWS[k].label) + '</td><td><b>' + esc(r.name) + '</b> · ' + esc(r.role) + '</td></tr>'; }).join('') + '</table></section>';
    } else if (tab === 'deals') {
      var sent = DL().all().filter(function (d) { return d.from.slug === co.slug; });
      body = '<section class="cp-sec"><h3>Received</h3>' + DL().receivedHtml(co.slug) + '</section><section class="cp-sec"><h3>Sent by ' + esc(co.name) + '</h3>' + (sent.length ? sent.map(function (d) { return '<button type="button" class="dl-row" data-deal="' + esc(d.id) + '"><span class="dl-b"><b>' + esc(d.title) + '</b><small>' + esc(DL().FLOWS[d.type].label) + ' → ' + esc(d.to.name) + '</small></span><span class="mr-st">' + esc(DL().label(d.status)) + '</span></button>'; }).join('') : '<p class="cp-muted">Nothing sent yet.</p>') + '</section>';
    } else if (tab === 'suppliers') {
      var m = H().store('avl_' + co.slug) || {}, keys = Object.keys(m);
      body = '<section class="cp-sec"><h3>Approved suppliers of ' + esc(co.name) + '</h3><p class="cp-muted">Set a status from any supplier page (while acting as ' + esc(co.name) + ') or send a qualification questionnaire.</p>' + (keys.length ? keys.map(function (k) { var s = X().bySlug(k); if (!s) return ''; var q = X3().qDeal(co.slug, k);
        return '<div class="mr-row">' + X().logo(s, 'dr-logo sm') + '<div class="mr-b"><b>' + esc(s.name) + '</b><small>since ' + esc(m[k].since) + (q ? ' · questionnaire: ' + esc(DL().label(q.status).toLowerCase()) : '') + '</small></div><span class="avl ' + X3().AVL[m[k].status][1] + '">' + X3().AVL[m[k].status][0] + '</span>' + (q ? '<button type="button" class="dr-btn sm" data-deal="' + esc(q.id) + '">Questionnaire</button>' : '') + '<button type="button" class="dr-btn sm" data-hopen="' + esc(k) + '">Open</button></div>'; }).join('') : '<p class="cp-muted">No suppliers on the list yet.</p>') + '</section>';
    } else if (tab === 'listings') {
      var sp = X3().surplus().filter(function (s) { return s.slug === co.slug; }), ds = X3().dossiers().filter(function (d) { return d.slug === co.slug; }), gs = X3().groupDeals().filter(function (g) { return g.from.slug === co.slug || g.to.slug === co.slug || (g.members || []).some(function (mb) { return mb.slug === co.slug; }); });
      body = '<section class="cp-sec"><h3>Your Marketplace listings</h3>' + sp.map(function (s) { return '<div class="cp-job"><span class="sp-off">−' + esc(s.off) + '%</span><span><b>' + esc(s.product) + '</b><small>Surplus · ' + esc(s.qty) + '</small></span></div>'; }).join('') +
        ds.map(function (d) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('doc') + '</span><span><b>' + esc(d.product) + '</b><small>Licensing · ' + esc(d.deal) + '</small></span></div>'; }).join('') +
        gs.map(function (g) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('users') + '</span><span><b>' + esc(g.lines.product) + '</b><small>Group buying · ' + esc(DL().label(g.status)) + '</small></span></div>'; }).join('') + (sp.length + ds.length + gs.length ? '' : '<p class="cp-muted">No listings yet.</p>') +
        '<div class="hb-row"><button type="button" class="dr-btn" data-wl="surplus">' + ic('box') + 'Post surplus stock</button><button type="button" class="dr-btn" data-wl="dossier">' + ic('doc') + 'List a dossier for licensing</button><button type="button" class="dr-btn" data-wl="group">' + ic('users') + 'Start a buying group</button></div></section>';
    } else if (tab === 'reports') {
      var rs = H().reports().filter(function (r) { return r.slug === co.slug; }), rv = H().reviewsOf(co.slug);
      body = '<section class="cp-sec"><h3>Reports of wrong information</h3>' + (rs.length ? rs.map(function (r) { return '<div class="mr-row"><div class="mr-b"><b>' + esc(r.section) + ': ' + esc(r.text) + '</b><small>' + (r.fix ? 'Suggested: ' + esc(r.fix) + ' · ' : '') + 'from ' + esc(r.by) + ' · ' + fmtDate(r.at) + '</small></div>' + (r.status === 'open' ? '<button type="button" class="dr-btn p sm" data-wfix="' + esc(r.id) + '">Mark fixed</button>' : '<span class="mr-st st-acc">Fixed</span>') + '</div>'; }).join('') : '<p class="cp-muted">No reports.</p>') + '</section>' +
        '<section class="cp-sec"><h3>Reviews</h3>' + (rv.length ? rv.map(function (r) { return '<div class="hb-rev"><b>' + '★'.repeat(r.stars) + '</b> <small>' + esc(r.from) + '</small><p>' + esc(r.note || '') + '</p>' + (r.reply ? '<div class="hb-reply">You replied: ' + esc(r.reply) + '</div>' : '<button type="button" class="dr-btn sm" data-wreply="' + esc(r.deal) + '">Reply</button>') + (r.disputed ? ' <span class="mr-st st-viewed">Under review by Drugbox</span>' : ' <button type="button" class="dr-link" data-wdispute="' + esc(r.deal) + '">Ask Drugbox to check this review</button>') + '</div>'; }).join('') : '<p class="cp-muted">No reviews yet.</p>') + '</section>';
    } else if (tab === 'activity') {
      var a = H().activity(co.slug);
      body = '<section class="cp-sec"><h3>Activity log</h3><p class="cp-muted">Who in your team did what.</p><ul class="dl-tl">' + (a.length ? a.map(function (x) { return '<li><b>' + esc(x.who) + '</b> · ' + esc(x.text) + '<small>' + (window.dxFmtDate ? window.dxFmtDate(x.at, true, 'en') : new Date(x.at).toLocaleString()) + '</small></li>'; }).join('') : '<li>No activity yet.</li>') + '</ul></section>';
    } else if (tab === 'plan') {
      body = '<div class="cp-two"><section class="cp-sec"><h3>Verification — free, always</h3><p>' + (co.status === 'verified' ? '✓ Verified: commercial registry and tax card checked.' : co.status === 'pending' ? 'Documents received — being checked.' : 'Not verified yet.') + '</p>' + (co.status === 'verified' || co.status === 'pending' ? '' : '<button type="button" class="dr-btn p" data-wverify="1">Get verified</button>') + '<p class="cp-muted">Verification and your track record can never be bought.</p></section>' +
        '<section class="cp-sec"><h3>Sponsored placement (VIP)</h3><p>' + (X().isVip(co) ? 'Your company appears in the Sponsored row of the directory.' : 'Appear in the Sponsored row of the directory, with your own link and Marketplace boosts. It never changes search order or trust.') + '</p>' + (X().isVip(co) ? '' : '<button type="button" class="dr-btn p" data-wvip="1">' + ic('crown') + 'Get VIP</button>') + '</section></div>';
    }
    var mine = X().myCompanies();
    c.innerHTML = '<div id="dxDir" class="hub ws"><div class="ws-head">' + X().logo(co, 'dr-logo sm') + '<div><span class="dr-k">COMPANY WORKSPACE</span><h1 class="ws-h">' + esc(co.name) + '</h1></div>' +
      (mine.length > 1 ? '<select id="wsSwitch" aria-label="Company">' + mine.map(function (m) { return '<option value="' + esc(m.slug) + '"' + (m.slug === co.slug ? ' selected' : '') + '>' + esc(m.name) + '</option>'; }).join('') + '</select>' : '') + '<button type="button" class="dr-btn" data-hopen="' + esc(co.slug) + '">View public page</button></div>' +
      '<nav class="cp-tabs" role="tablist">' + WTABS.map(function (x) { return '<button type="button" role="tab" aria-selected="' + (tab === x[0]) + '" class="cp-tab' + (tab === x[0] ? ' on' : '') + '" data-wtab="' + x[0] + '">' + esc(x[1]) + '</button>'; }).join('') + '</nav><div class="cp-body">' + body + '</div></div>';
  }

  /* ════════ routing between views ════════ */
  function S() { return X().S; }
  function rerender() { X().render(); var sc = document.getElementById('content'); }
  function openPage(slug, tab) { var s = S(); s.view = null; s.ws = null; s.tab = tab || 'overview'; X().open(slug, tab); var st = S(); st.tab = tab || 'overview'; X().render(); }
  function openWorkspace(slug, tab) { var s = S(); s.view = 'workspace'; s.ws = slug; s.wsTab = tab || 'overview'; s.open = null; window.__dxKeepCompany = true; try { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); else X().render(); } finally { window.__dxKeepCompany = false; } var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0; }
  function render(c, St, co) {
    if (St.view === 'workspace') { var w = St.ws && X().bySlug(St.ws); if (w && member(w)) { renderWorkspace(c, w, St); return true; } St.view = null; }
    if (co) { renderCompany(c, co, St); return true; }
    renderDirectory(c, St); return true;
  }
  document.addEventListener('dx:beforepage', function (e) { if (e.detail.page === 'companies' && !window.__dxKeepCompany && X()) { S().view = null; } });

  /* ════════ dialogs ════════ */
  function ruleDialog() { D.modal({ title: 'How results are ordered', secondary: 'Close', body: '<p>' + esc(H().RANK_RULE) + '</p>' }); }
  function addOrClaim() {
    var m = D.modal({ title: 'Add or claim your company', secondary: 'Close', body: '<p class="cp-muted">A company exists once on Drugbox. Search first — if it is already here, claim it instead of creating a copy.</p><div class="dbk-f"><label for="acQ">Company name</label><input id="acQ" placeholder="Arabic or English"></div><div id="acRes"></div>' });
    var inp = m.el.querySelector('#acQ'), res = m.el.querySelector('#acRes');
    function run() { var q = inp.value.trim(); if (q.length < 2) { res.innerHTML = ''; return; }
      var hits = X().companies().filter(function (co) { return H().relevance(co, q) > 0 && H().norm(co.name + ' ' + H().nameAr(co)).indexOf(H().norm(q).split(' ')[0]) >= 0; }).slice(0, 6);
      res.innerHTML = hits.map(function (co) { return '<div class="mr-row">' + X().logo(co, 'dr-logo sm') + '<div class="mr-b"><b>' + esc(co.name) + '</b><small>' + esc(co.city) + ' · ' + (co.status === 'unclaimed' ? 'not claimed yet' : 'managed by its team') + '</small></div>' + (co.status === 'unclaimed' ? '<button type="button" class="dr-btn p sm" data-acclaim="' + esc(co.slug) + '">Claim</button>' : member(co) ? '<button type="button" class="dr-btn sm" data-acws="' + esc(co.slug) + '">Open workspace</button>' : '<button type="button" class="dr-btn sm" data-acjoin="' + esc(co.slug) + '">Ask to join the team</button>') + '</div>'; }).join('') +
        '<div class="fd-act"><button type="button" class="dr-btn" data-acnew="1">' + ic('plus') + 'My company is not listed — create it</button></div>'; }
    inp.addEventListener('input', run); setTimeout(function () { inp.focus(); }, 30);
    m.el.addEventListener('click', function (e) {
      var cl = e.target.closest('[data-acclaim]'), ws = e.target.closest('[data-acws]'), jn = e.target.closest('[data-acjoin]');
      if (cl) { m.close(); later(function () { X2().claim(X().bySlug(cl.dataset.acclaim)); }); }
      if (ws) { m.close(); openWorkspace(ws.dataset.acws); }
      if (jn) { var co = X().bySlug(jn.dataset.acjoin); m.close(); toast('Request sent to the admin of ' + co.name); }
      if (e.target.closest('[data-acnew]')) { m.close(); later(function () { X().create(); }); }
    });
  }
  function reportDialog(co) {
    D.modal({ title: 'Report wrong information — ' + co.name, body: '<div class="dbk-f"><label for="rpS">Where</label><select id="rpS"><option>About</option><option>Products</option><option>Sites</option><option>Certificates</option><option>Contact</option></select></div><div class="dbk-f"><label for="rpT">What is wrong? *</label><input id="rpT" data-req></div><div class="dbk-f"><label for="rpF">Correct information (if you know it)</label><input id="rpF"></div>',
      primary: { label: 'Send report', onClick: function (b) { if (!D.requireFields(b)) return false; H().addReport(co.slug, b.querySelector('#rpS').value, b.querySelector('#rpT').value.trim(), b.querySelector('#rpF').value.trim()); toast('Thanks — ' + co.name + ' has been asked to check it'); } } });
  }
  function healthDialog() {
    var h = H().health(), pct = function (a) { return h.total ? Math.round(a / h.total * 100) + '%' : '—'; };
    var m = D.modal({ title: 'Directory health', secondary: 'Close', body: '<div class="cp-stats hb-health"><div><small>Companies</small><b>' + h.total + '</b></div><div><small>Claimed</small><b>' + pct(h.claimed) + '</b></div><div><small>Verified</small><b>' + pct(h.verified) + '</b></div><div><small>Pages ≥80% complete</small><b>' + pct(h.complete) + '</b></div>' +
      '<div><small>Average completeness</small><b>' + h.avgComplete + '%</b></div><div><small>Requests answered</small><b>' + (h.responseRate != null ? h.responseRate + '%' : '—') + '</b></div><div><small>Deals · last 30 days</small><b>' + h.dealsMonth + '</b></div><div><small>Active this week</small><b>' + h.active + '</b></div>' +
      '<div><small>Dormant (60+ days)</small><b>' + h.dormant + '</b></div><div><small>Pages with outdated info</small><b>' + h.stale.length + '</b></div><div><small>Open reports</small><b>' + h.openReports + '</b></div><div><small>Reviews under check</small><b>' + h.disputed + '</b></div></div>' +
      (h.stale.length ? '<h4 class="sq-h">Outdated pages</h4>' + h.stale.slice(0, 8).map(function (co) { return '<div class="mr-row"><div class="mr-b"><b>' + esc(co.name) + '</b><small>' + esc(H().staleSections(co).join(', ')) + '</small></div><button type="button" class="dr-btn sm" data-hopen="' + esc(co.slug) + '">Open</button></div>'; }).join('') : '') });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    m.el.addEventListener('click', function (e) { var o = e.target.closest('[data-hopen]'); if (o) { m.close(); openPage(o.dataset.hopen); } });
  }
  function certDialog(co, i) {
    D.modal({ title: 'Add a certificate', body: '<div class="dbk-f"><label for="wcN">Certificate *</label><select id="wcN" data-req><option value="">Choose…</option>' + CERTS.concat(['ISO 15378', 'ISO 14001', 'Halal', 'ISO 22000']).map(function (x) { return '<option>' + x + '</option>'; }).join('') + '</select></div><div class="dbk-row"><div class="dbk-f"><label for="wcE">Valid until</label><input id="wcE" type="month"></div><div class="dbk-f"><label for="wcF">Document</label><input id="wcF" type="file" accept=".pdf,.jpg,.png"></div></div>',
      primary: { label: 'Add', onClick: function (b) { if (!D.requireFields(b)) return false; var ss = H().sitesOf(co); (ss[i].certs = ss[i].certs || []).push({ name: b.querySelector('#wcN').value, expiry: b.querySelector('#wcE').value, src: b.querySelector('#wcF').files.length ? 'Certificate document' : 'Company', checked: new Date().toISOString().slice(0, 10) }); if (!H().saveSites(co.slug, ss)) return false; rerender(); toast('Certificate added'); } } });
  }
  function capDialog(co, i) {
    var ss = H().sitesOf(co), cap = ss[i].cap || { forms: [], minBatch: '', capacity: '', slots: [] };
    D.modal({ title: 'Manufacturing capabilities — ' + ss[i].name, body: '<div class="hb-forms">' + X2().FORMS.map(function (f) { return '<label><input type="checkbox" value="' + f + '"' + (cap.forms.indexOf(f) >= 0 ? ' checked' : '') + '> ' + f + '</label>'; }).join('') + '</div><div class="dbk-row"><div class="dbk-f"><label for="wkB">Minimum batch</label><input id="wkB" value="' + esc(cap.minBatch) + '"></div><div class="dbk-f"><label for="wkC">Capacity</label><input id="wkC" value="' + esc(cap.capacity) + '"></div></div>',
      primary: { label: 'Save', onClick: function (b) { cap.forms = Array.prototype.map.call(b.querySelectorAll('.hb-forms input:checked'), function (x) { return x.value; }); cap.minBatch = b.querySelector('#wkB').value.trim(); cap.capacity = b.querySelector('#wkC').value.trim(); ss[i].cap = cap.forms.length ? cap : null; if (!H().saveSites(co.slug, ss)) return false; rerender(); toast('Capabilities saved'); } } });
  }
  function siteDialog(co) {
    D.modal({ title: 'Add a site', body: '<div class="dbk-f"><label for="wsN">Name *</label><input id="wsN" data-req placeholder="e.g. Sadat City plant"></div><div class="dbk-row"><div class="dbk-f"><label for="wsT">Type</label><select id="wsT"><option>Factory</option><option>Warehouse</option><option>Laboratory</option><option>Office</option><option>Head office</option></select></div><div class="dbk-f"><label for="wsG">Governorate *</label><select id="wsG" data-req>' + GOVS.slice(1).concat(['Menoufia', 'Gharbia', 'Beheira', 'Assiut', 'Sohag', 'Suez', 'Port Said']).map(function (g) { return '<option>' + g + '</option>'; }).join('') + '</select></div></div><div class="dbk-f"><label for="wsC">City / area *</label><input id="wsC" data-req></div>',
      primary: { label: 'Add site', onClick: function (b) { if (!D.requireFields(b)) return false; var ss = H().sitesOf(co); ss.push({ id: 's' + Date.now(), name: b.querySelector('#wsN').value.trim(), type: b.querySelector('#wsT').value, city: b.querySelector('#wsC').value.trim(), gov: b.querySelector('#wsG').value, certs: [] }); if (!H().saveSites(co.slug, ss)) return false; rerender(); toast('Site added'); } } });
  }
  function inviteDialog(co) {
    D.modal({ title: 'Invite a colleague', body: '<div class="dbk-f"><label for="wiN">Name *</label><input id="wiN" data-req></div><div class="dbk-row"><div class="dbk-f"><label for="wiE">Work email *</label><input id="wiE" type="email" data-req></div><div class="dbk-f"><label for="wiR">Role</label><select id="wiR">' + H().ROLES.map(function (r) { return '<option' + (r === 'Sales' ? ' selected' : '') + '>' + r + '</option>'; }).join('') + '</select></div></div><p class="cp-muted">They appear on the public page only after they accept.</p>',
      primary: { label: 'Send invitation', onClick: function (b) { if (!D.requireFields(b)) return false; var t = H().teamOf(co); t.push({ uid: null, name: b.querySelector('#wiN').value.trim(), email: b.querySelector('#wiE').value.trim(), role: b.querySelector('#wiR').value, consent: false }); if (!H().saveTeam(co.slug, t)) return false; H().log(co.slug, 'Invited ' + b.querySelector('#wiN').value.trim() + ' as ' + b.querySelector('#wiR').value); rerender(); toast('Invitation sent'); } } });
  }

  /* ════════ one click handler for the hub ════════ */
  document.addEventListener('click', function (e) {
    var root = e.target.closest && e.target.closest('#dxDir.hub'); if (!root) return;
    var t = e.target.closest('[data-hopen],[data-hrfq],[data-hadd],[data-hsec],[data-hcert],[data-hreset],[data-hmore],[data-hrule],[data-hhealth],[data-hback],[data-htab2],[data-hws],[data-hmsg],[data-hfollow],[data-hsq],[data-hpdf],[data-hqr],[data-hreport],[data-hclaim],[data-hpd],[data-hoffer],[data-hsurp],[data-hdos],[data-hgroups],[data-hjob],[data-wtab],[data-wgo],[data-wconfirm],[data-wedit],[data-war],[data-wlook],[data-wmember],[data-wcadd],[data-wcdel],[data-wslot],[data-wcap],[data-wsdel],[data-wsadd],[data-wconsent],[data-wtdel],[data-winvite],[data-wl],[data-wfix],[data-wreply],[data-wdispute],[data-wverify],[data-wvip]');
    if (!t) { var cardEl = e.target.closest('.hb-card'); if (cardEl && !e.target.closest('button,a,input,select,label')) openPage(cardEl.dataset.slug); return; }
    if (t.hasAttribute('data-hpick')) return;
    e.stopPropagation();
    var St = S(), co = St.open ? X().bySlug(St.open) : St.ws ? X().bySlug(St.ws) : null, ds = t.dataset;
    if (ds.hopen) return openPage(ds.hopen, ds.htab);
    if (ds.hrfq) return X().rfq(ds.hrfq, ds.hp);
    if (ds.hadd) return addOrClaim();
    if (ds.hsec) { St.sector = ds.hsec; return rerender(); }
    if (ds.hcert) { St.certs = St.certs || []; var i = St.certs.indexOf(ds.hcert); if (i >= 0) St.certs.splice(i, 1); else St.certs.push(ds.hcert); return rerender(); }
    if (ds.hreset) { St.q = ''; St.sector = 'All'; St.gov = 'All governorates'; St.certs = []; St.verified = false; St.activeOnly = false; St.form = ''; St.from = 0; return rerender(); }
    if (ds.hmore) { St.shown = (St.shown || PAGE) + PAGE; var y = document.getElementById('content'); var top = y ? y.scrollTop : 0; rerender(); if (y) y.scrollTop = top; return; }
    if (ds.hrule) return ruleDialog();
    if (ds.hhealth) return healthDialog();
    if (ds.hback) { St.open = null; St.view = null; rerender(); var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0; return; }
    if (ds.htab2) { St.tab = ds.htab2; return rerender(); }
    if (ds.hws) return openWorkspace(ds.hws);
    if (ds.hmsg && co) return window.dxOpenChat ? window.dxOpenChat(H().route(co.slug, 'quote').name) : null;
    if (ds.hfollow && co) { var f = H().store('follows') || [], k = f.indexOf(co.slug); if (k >= 0) f.splice(k, 1); else f.push(co.slug); H().store('follows', f); toast(k >= 0 ? 'Unfollowed' : 'Following ' + co.name); return rerender(); }
    if (ds.hsq && co) return X3().sendQuestionnaire(co);
    if (ds.hpdf && co) return X2().brochure(co);
    if (ds.hqr && co) return X2().qr(co);
    if (ds.hreport && co) return reportDialog(co);
    if (ds.hclaim && co) return X2().claim(co);
    if (ds.hpd && co) { var p = co.products.find(function (x) { return x.id === ds.hpd; }); return p && X().productDialog(co, p); }
    if (ds.hoffer) { var q = ds.hoffer.split('—')[0].trim(); window.goto('market'); var si = document.getElementById('searchIn'); if (si) si.value = q; if (window.__mkxFilter) window.__mkxFilter(q); return; }
    if (ds.hsurp) return X3().surplusOffer(X3().surplus().find(function (s) { return s.id === ds.hsurp; }));
    if (ds.hdos) return X3().dossierRequest(X3().dossiers().find(function (d) { return d.id === ds.hdos; }));
    if (ds.hgroups) return X3().groupsDialog();
    if (ds.hjob != null && co) { var job = X().jobsOf(co)[+ds.hjob]; if (!job) return; if (job.onJobs) { window.goto('jobs'); var h = document.querySelector('#jx .mode-opt[data-mode="hunting"]'); if (h) h.click(); setTimeout(function () { var card = Array.prototype.find.call(document.querySelectorAll('#jx #huntingView .jcard'), function (c) { return c.textContent.indexOf(job.t) >= 0; }); if (card) { card.scrollIntoView({ block: 'center' }); var ab = card.querySelector('.apply-btn'); if (ab) ab.click(); } }, 60); } else X().applyDialog(co, job); return; }
    /* workspace */
    if (ds.wtab) { St.wsTab = ds.wtab; return rerender(); }
    if (!co) return;
    if (ds.wgo) { var go = { logo: 'page', about: 'page', sites: 'sites', products: 'page', contact: 'page', team: 'team', certs: 'sites', verify: 'plan', arabic: 'page' }[ds.wgo]; St.wsTab = go; rerender(); if (ds.wgo === 'logo' || ds.wgo === 'about' || ds.wgo === 'products' || ds.wgo === 'contact') later(function () { X().open(co.slug); S().view = 'workspace'; X().editor(ds.wgo === 'products' ? 'products' : null); }); return; }
    if (ds.wconfirm) { H().touch(co.slug); toast('Thanks — marked as up to date'); return rerender(); }
    if (ds.wedit) { S().open = co.slug; return X().editor(); }
    if (ds.war) { var v = document.getElementById('wAr').value.trim(), ed = H().store('company_edits') || {}; ed[co.slug] = Object.assign({}, ed[co.slug] || {}, { nameAr: v }); if (!H().store('company_edits', ed)) return; H().log(co.slug, 'Updated the Arabic name'); toast('Arabic name saved'); return rerender(); }
    if (ds.wlook) { H().store('acting', co.slug); return X3().editLooking(co); }
    if (ds.wmember) return X3().addMembership(co);
    if (ds.wcadd != null) return certDialog(co, +ds.wcadd);
    if (ds.wcdel) { var ij = ds.wcdel.split(':'), ss = H().sitesOf(co); ss[+ij[0]].certs.splice(+ij[1], 1); H().saveSites(co.slug, ss); return rerender(); }
    if (ds.wslot) { var ab2 = ds.wslot.split(':'), s2 = H().sitesOf(co), cp2 = s2[+ab2[0]].cap, n = +ab2[1], kk = cp2.slots.indexOf(n); if (kk >= 0) cp2.slots.splice(kk, 1); else cp2.slots.push(n); H().saveSites(co.slug, s2); toast(X2().MONTHS[n] + (kk >= 0 ? ' booked' : ' free')); return rerender(); }
    if (ds.wcap != null) return capDialog(co, +ds.wcap);
    if (ds.wsdel != null) { var s3 = H().sitesOf(co); s3.splice(+ds.wsdel, 1); H().saveSites(co.slug, s3); return rerender(); }
    if (ds.wsadd) return siteDialog(co);
    if (ds.wconsent != null) { var tm = H().teamOf(co); tm[+ds.wconsent].consent = !tm[+ds.wconsent].consent; H().saveTeam(co.slug, tm); toast(tm[+ds.wconsent].consent ? 'You are shown on the public page' : 'You are hidden from the public page'); return rerender(); }
    if (ds.wtdel != null) { var tm2 = H().teamOf(co); var gone = tm2.splice(+ds.wtdel, 1)[0]; H().saveTeam(co.slug, tm2); H().log(co.slug, 'Removed ' + gone.name + ' from the team'); return rerender(); }
    if (ds.winvite) return inviteDialog(co);
    if (ds.wl) { H().store('acting', co.slug); if (ds.wl === 'surplus') return X3().postSurplus(); if (ds.wl === 'dossier') return X3().addDossier(co); return X3().newGroup(); }
    if (ds.wfix) { var rs = H().reports(); rs.forEach(function (r) { if (r.id === ds.wfix) r.status = 'fixed'; }); H().reports(rs); H().touch(co.slug, null); toast('Marked fixed'); return rerender(); }
    if (ds.wreply) { var id = ds.wreply; return D.modal({ title: 'Reply to the review', body: '<div class="dbk-f"><label for="rrT">Your public reply *</label><textarea id="rrT" data-req></textarea></div>', primary: { label: 'Publish reply', onClick: function (b) { if (!D.requireFields(b)) return false; H().reviewMeta(id, { reply: b.querySelector('#rrT').value.trim() }); H().log(co.slug, 'Replied to a review'); rerender(); toast('Reply published'); } } }); }
    if (ds.wdispute) { H().reviewMeta(ds.wdispute, { disputed: true }); toast('Sent to Drugbox for checking — the review stays visible meanwhile'); return rerender(); }
    if (ds.wverify) return X().verify(co.slug);
    if (ds.wvip) return X().upgrade(co.slug);
  }, true);
  document.addEventListener('change', function (e) {
    var St = X() && S(); if (!St || !(e.target.closest && e.target.closest('#dxDir.hub'))) return;
    var id = e.target.id;
    if (id === 'hbSort') { St.sort = e.target.value; rerender(); } else if (id === 'hbForm') { St.form = e.target.value; St.from = 0; rerender(); } else if (id === 'hbFrom') { St.from = +e.target.value; rerender(); }
    else if (id === 'hbGov') { St.gov = e.target.value; rerender(); } else if (id === 'hbVer') { St.verified = e.target.checked; rerender(); } else if (id === 'hbAct') { St.activeOnly = e.target.checked; rerender(); }
    else if (id === 'hbAvl') { var co = X().bySlug(St.open); X3().setAvl(co.slug, e.target.value); toast(e.target.value ? co.name + ': ' + X3().AVL[e.target.value][0] : co.name + ' removed from your supplier list'); }
    else if (id === 'wsSwitch') { openWorkspace(e.target.value, St.wsTab); }
    else if (e.target.dataset.wrole != null) { var w = X().bySlug(St.ws), tm = H().teamOf(w); tm[+e.target.dataset.wrole].role = e.target.value; H().saveTeam(w.slug, tm); H().log(w.slug, tm[+e.target.dataset.wrole].name + ' is now ' + e.target.value); rerender(); }
    else if (e.target.closest('[data-hpick]')) { var slug = e.target.closest('[data-hpick]').dataset.hpick, p = window.dxPicks.get().slice(); if (e.target.checked) { if (p.length >= 10) { e.target.checked = false; toast('Up to 10 companies per request'); return; } p.push(slug); } else p = p.filter(function (s) { return s !== slug; }); window.dxPicks.set(p); }
  });
  document.addEventListener('input', function (e) {
    if (e.target.id !== 'hbQ') return; var St = S(); St.q = e.target.value; var pos = e.target.selectionStart;
    clearTimeout(window.__hbT); window.__hbT = setTimeout(function () { rerender(); var q = document.getElementById('hbQ'); if (q) { q.focus(); try { q.setSelectionRange(pos, pos); } catch (x) {} } }, 200);
  });

  /* ════════ Marketplace: company listings (surplus · licensing · group buying) ════════ */
  var mkTab = 'surplus';
  function marketListings() {
    var mk = document.getElementById('mkx'); if (!mk || !X3()) return;
    var main = mk.querySelector('#tab-browse .main'); if (!main) return;
    var box = main.querySelector(':scope > .hb-mk'), sp = X3().surplus(), ds = X3().dossiers(), gs = X3().groupDeals();
    var sig = mkTab + '|' + sp.length + '|' + ds.length + '|' + gs.map(function (g) { return g.status + X3().total(g); }).join(',');
    if (box && box.dataset.sig === sig) return;
    if (!box) { box = document.createElement('section'); box.className = 'hb-mk'; var chips = main.querySelector(':scope > .dx-chips, :scope > .dx-saved'); main.insertBefore(box, main.firstChild); }
    box.dataset.sig = sig;
    var rows = mkTab === 'surplus' ? sp.map(function (s) { var co = X().bySlug(s.slug); return '<div class="cp-job"><span class="sp-off">−' + esc(s.off) + '%</span><span><b>' + esc(s.product) + '</b><small>' + esc(s.qty) + ' · batch ' + esc(s.batch) + (s.expiry !== '—' ? ' · expires ' + esc(s.expiry) : '') + ' · ' + esc(co ? co.name : '') + '</small></span><b class="sp-price">' + esc(s.price) + '</b><button type="button" class="dr-btn p sm" data-mks="' + esc(s.id) + '">Make an offer</button></div>'; })
      : mkTab === 'license' ? ds.map(function (d) { var co = X().bySlug(d.slug); return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('doc') + '</span><span><b>' + esc(d.product) + '</b><small>' + esc(d.status) + ' · ' + esc(d.markets) + ' · ' + esc(co ? co.name : '') + '</small></span><span class="avl avl-ev">' + esc(d.deal) + '</span><button type="button" class="dr-btn p sm" data-mkd="' + esc(d.id) + '">Request details</button></div>'; })
      : gs.map(function (g) { var pct = Math.min(100, Math.round(X3().total(g) / g.lines.target * 100)); return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic('users') + '</span><span><b>' + esc(g.lines.product) + '</b><small>' + X3().total(g).toLocaleString() + ' of ' + g.lines.target.toLocaleString() + ' ' + esc(g.lines.unit) + ' · ' + esc(g.lines.price) + ' · ' + esc(DL().label(g.status)) + '</small><span class="gb-bar sm"><i style="width:' + pct + '%"></i></span></span><button type="button" class="dr-btn p sm" data-mkg="1">Join</button></div>'; });
    box.innerHTML = '<div class="hb-mk-h"><b>Company listings</b><div class="hb-mk-tabs">' + [['surplus', 'Surplus stock (' + sp.length + ')'], ['license', 'Licensing dossiers (' + ds.length + ')'], ['groups', 'Group buying (' + gs.length + ')']].map(function (x) { return '<button type="button" class="dr-chip sm' + (mkTab === x[0] ? ' on' : '') + '" data-mkt="' + x[0] + '">' + x[1] + '</button>'; }).join('') + '</div>' +
      '<button type="button" class="dr-btn sm" data-mkpost="1">' + ic('plus') + (mkTab === 'surplus' ? 'Post surplus' : mkTab === 'license' ? 'List a dossier' : 'Start a group') + '</button></div>' + rows.slice(0, 5).join('') + (rows.length > 5 ? '<button type="button" class="dr-link" data-mkall="1">See all ' + rows.length + '</button>' : '');
  }
  document.addEventListener('click', function (e) {
    var box = e.target.closest && e.target.closest('.hb-mk'); if (!box) return;
    var t = e.target.closest('[data-mkt],[data-mks],[data-mkd],[data-mkg],[data-mkpost],[data-mkall]'); if (!t) return; e.stopPropagation();
    if (t.dataset.mkt) { mkTab = t.dataset.mkt; box.dataset.sig = ''; return marketListings(); }
    if (t.dataset.mks) return X3().surplusOffer(X3().surplus().find(function (s) { return s.id === t.dataset.mks; }));
    if (t.dataset.mkd) return X3().dossierRequest(X3().dossiers().find(function (d) { return d.id === t.dataset.mkd; }));
    if (t.dataset.mkg) return X3().groupsDialog();
    if (t.dataset.mkall) return mkTab === 'surplus' ? X3().surplusDialog() : mkTab === 'license' ? X3().dossiersDialog() : X3().groupsDialog();
    if (t.dataset.mkpost) { var a = X().mine(); if (!a) { toast('Create or claim your company page first'); return; } if (mkTab === 'surplus') X3().postSurplus(); else if (mkTab === 'license') X3().addDossier(a); else X3().newGroup(); }
  }, true);

  /* ════════ Deals button in the top bar ════════ */
  function dealsButton() {
    var right = document.querySelector('.topbar .top-right'); if (!right || !DL()) return;
    var b = document.getElementById('dxDealsBtn'), n = DL().waiting();
    if (!b) { b = document.createElement('button'); b.id = 'dxDealsBtn'; b.type = 'button'; b.className = 'dx-search-btn hb-deals'; b.title = 'Requests & deals'; b.setAttribute('aria-label', 'Requests and deals'); b.onclick = function () { var DLx = DL(), recv = DLx.all().some(function (d) { return DLx.sideOf(d) === 'to' && DLx.actionsFor(d, 'to').length; }); DLx.center(recv ? 'received' : 'sent'); }; var sw = document.getElementById('dxCoSwitch'); right.insertBefore(b, sw ? sw.nextSibling : right.firstChild); }
    var html = ic('handshake') + (n ? '<span class="hb-dot">' + n + '</span>' : '');
    if (b.dataset.n !== String(n)) { b.innerHTML = html; b.dataset.n = String(n); }
  }

  /* ════════ Home: matches for the company you act as ════════ */
  function homeMatches() {
    if (document.body.getAttribute('data-page') !== 'feed' || !X3()) return;
    var fy = document.getElementById('dxForYou'), a = X().mine(); if (!fy || !a) return;
    var ms = X3().matchesFor(a), box = document.getElementById('hbMatches'), sig = a.slug + '|' + ms.length;
    if (box && box.dataset.sig === sig) return; if (box) box.remove(); if (!ms.length) return;
    box = document.createElement('div'); box.id = 'hbMatches'; box.dataset.sig = sig;
    box.innerHTML = '<div class="hb-mh">' + ic('handshake') + '<b>Companies that match what ' + esc(a.name) + ' is looking for</b></div><div class="hb-mrow">' + ms.slice(0, 4).map(function (m) { return '<button type="button" class="hb-mcard" data-mco="' + esc(m.co.slug) + '">' + X().logo(m.co, 'dr-logo sm') + '<span><b>' + esc(m.co.name) + '</b><small>' + esc(m.why[0]) + '</small></span></button>'; }).join('') + '</div>';
    fy.appendChild(box);
    box.onclick = function (e) { var b = e.target.closest('[data-mco]'); if (b) openPage(b.dataset.mco); };
  }

  window.dxHub = { render: render, route: function (s, t) { return H().route(s, t); }, log: function (s, t) { H().log(s, t); }, workspace: openWorkspace, page: openPage, health: healthDialog };
  C.onRender('hub-market', marketListings);
  C.onRender('hub-deals-button', dealsButton);
  C.onRender('hub-home-matches', homeMatches);
})();
