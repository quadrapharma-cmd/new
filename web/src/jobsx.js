/* Jobs — the rest of the hiring loop (J-01 … J-07, J-COMMUNITY-19 … 29): keyword search, employment-type / country filters
   that combine with the category and level, paging, the job's details, My applications (status, Withdraw), My jobs with
   their applicants (CV, pipeline: shortlist / interview / hire / reject / no-show), Post My Profile (open to work, CV) and
   hiding it again, saved jobs on the Saved page, saved searches (job alerts).
   Demo: the approved page's own cards and sample data kept in this browser (DBK.store). Live: window.dxJobs, set by the data
   adapter (web/src/live/adapter.js), does the same against the database — this file only draws. Every list row and window is
   built in the approved visual language (the job card, the kit window). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function live() { var s = window.dxJobs; return !!(s && s.live && s.ready && s.ready()); }
  function S() { return live() ? window.dxJobs : DEMO; }
  function T(s) { return window.dxT ? window.dxT(s) : s; }
  function toast(m) { D.toast(m); }
  function jx() { return document.getElementById('jx'); }

  /* ── the job a card shows ─────────────────────────────────────────────────────────────────────────────────────────── */
  var FLAG = { EG: '🇪🇬', AE: '🇦🇪', SA: '🇸🇦', KW: '🇰🇼', QA: '🇶🇦', JO: '🇯🇴', OM: '🇴🇲', BH: '🇧🇭', IN: '🇮🇳', CN: '🇨🇳', LB: '🇱🇧', MA: '🇲🇦', TN: '🇹🇳', DZ: '🇩🇿', IQ: '🇮🇶' };
  var CNAME = { EG: 'Egypt', AE: 'UAE', SA: 'Saudi Arabia', KW: 'Kuwait', QA: 'Qatar', JO: 'Jordan', OM: 'Oman', BH: 'Bahrain', IN: 'India' };
  var BYFLAG = {}; Object.keys(FLAG).forEach(function (k) { BYFLAG[FLAG[k]] = k; });
  /* a place typed in the Post a Job form → its country (the person can still choose another) */
  var PLACE = [['AE', /\b(uae|dubai|abu ?dhabi|sharjah|ajman|emirates)\b|الإمارات|دبي|أبوظبي/i], ['SA', /\b(saudi|ksa|riyadh|jeddah|dammam|qassim|khobar|tabuk)\b|السعودية|الرياض|جدة/i],
               ['KW', /\bkuwait\b|الكويت/i], ['QA', /\b(qatar|doha)\b|قطر|الدوحة/i], ['JO', /\b(jordan|amman)\b|الأردن|عمان/i], ['OM', /\b(oman|muscat)\b|مسقط/i],
               ['BH', /\b(bahrain|manama)\b|البحرين/i], ['IN', /\b(india|mumbai|hyderabad|delhi|bangalore|ahmedabad|pune)\b|الهند/i]];
  function placeCountry(s) { for (var i = 0; i < PLACE.length; i++) if (PLACE[i][1].test(s || '')) return PLACE[i][0]; return 'EG'; }
  var LEVELS = { entry: '🌱 Entry Level', junior: '⚙️ Junior', mid: '🎯 Mid-Level', senior: '🧭 Senior Mgmt', exec: '👑 Executive' };
  function levelOf(exp) { var n = parseInt(String(exp || '').match(/\d+/) || 0, 10); return !exp ? 'mid' : n < 1 ? 'entry' : n < 3 ? 'junior' : n < 5 ? 'mid' : n < 10 ? 'senior' : 'exec'; }
  var CATS = ['regulatory', 'qaqc', 'production', 'sales', 'rd'];
  function titleOf(card) {   /* the job title without the Hiring / level badges */
    var t = card && card.querySelector('.jc-title'); if (!t) return '';
    var s = ''; t.childNodes.forEach(function (n) { if (n.nodeType === 3) s += n.nodeValue; }); return s.replace(/\s+/g, ' ').trim();
  }
  function isJob(card) { return !!(card && card.querySelector('.role-badge.have')); }
  function jobCards(root) { return [].filter.call((root || document).querySelectorAll('#jx .jcard'), isJob); }
  function cardCountry(card) { var co = card.querySelector('.jc-company'), t = co ? co.textContent : '';
    for (var f in BYFLAG) if (t.indexOf(f) >= 0) return BYFLAG[f]; return placeCountry(t); }
  function cardType(card) { var t = card.querySelector('.jt'), s = t ? txt(t).toLowerCase() : ''; return /part/.test(s) ? 'part-time' : /contract/.test(s) ? 'contract' : /remote/.test(s) ? 'remote' : 'full-time'; }
  function cardRemote(card) { return !!card.querySelector('.jt-re') || /remote/i.test(txt(card.querySelector('.jc-tags'))); }

  /* the sample jobs' details (the approved cards carry a summary only) */
  var DETAILS = {
    'Senior Regulatory Affairs Specialist': { salary: 'EGP 35,000 – 45,000 / month', deadline: '2026-11-30', requirements: ['Pharmacy degree', '3–5 years in regulatory affairs', 'EDA dossier and CTD experience', 'Fluent English and Arabic'], benefits: ['Medical insurance', 'Annual bonus', 'Training budget'] },
    'QC Analyst (HPLC) — API Division': { salary: 'INR 6–8 LPA', deadline: '2026-11-20', requirements: ['B.Sc./M.Sc. Chemistry or Pharmacy', '2+ years HPLC method validation', 'USFDA-audited lab experience'], benefits: ['Relocation support', 'Shift allowance'] },
    'Cosmetic Formulation Scientist': { salary: 'EGP 25,000 – 32,000 / month', deadline: '2026-12-10', requirements: ['Pharmacy or Chemistry degree', 'Skincare formulation (serums, creams)', 'EDA cosmetics notification a plus'], benefits: ['Hybrid work', 'Product allowance'] },
    'GCC Registration Coordinator': { salary: 'AED 12,000 – 15,000 / month', deadline: '2026-11-15', requirements: ['2+ years GCC registrations', 'SFDA / DHA / MOHAP portals', 'Arabic and English'], benefits: ['Visa and medical', 'Remote days'] },
    'Production Supervisor — Solid Dosage': { salary: 'EGP 28,000 – 36,000 / month', deadline: '2026-12-01', requirements: ['4+ years solid dosage production', 'WHO-GMP batch documentation', 'Team leadership'], benefits: ['Transport', 'Meals', 'Medical insurance'] },
    'Country Manager — Egypt & North Africa': { salary: 'Competitive', deadline: '2026-12-31', requirements: ['12+ years in pharma, 5 as general manager', 'Full P&L ownership', 'EDA and regional market knowledge'], benefits: ['Car', 'Equity plan', 'Family medical'] },
    'Junior Lab Technician — Fresh Graduate Program': { salary: 'EGP 9,000 – 11,000 / month', deadline: '2026-11-25', requirements: ['Pharmacy or Chemistry graduate (2025–2026)', 'Willing to work shifts'], benefits: ['Full lab training', 'Transport'] }
  };
  var MY_CO = 'Quadra Pharm';   /* the demo account's company */
  function demoMine(card) { return txt(card.querySelector('.jc-company span')) === MY_CO; }

  /* ── demo data (this browser) ─────────────────────────────────────────────────────────────────────────────────────── */
  function today() { return new Date().toISOString().slice(0, 10); }
  function daysAgo(n) { var d = new Date(); d.setDate(d.getDate() - n); return d.toISOString(); }
  var SEED_APPS = [{ title: 'Junior Lab Technician — Fresh Graduate Program', company: 'Medsinia Industries', location: '10th of Ramadan, Egypt', country: 'EG', status: 'shortlisted', created_at: daysAgo(9), status_at: daysAgo(4) },
                   { title: 'GCC Registration Coordinator', company: 'Azurea Drug Store', location: 'Dubai, UAE', country: 'AE', status: 'submitted', created_at: daysAgo(3), status_at: daysAgo(3) }];
  var SEED_APPLICANTS = {
    'Senior Regulatory Affairs Specialist': [
      { name: 'Amr Saleh', headline: 'Regulatory Affairs Specialist', company: 'Pharco', location: 'Alexandria, Egypt', note: 'Five EDA registrations to approval last year; CTD and variations.', cv: true, status: 'submitted', created_at: daysAgo(1) },
      { name: 'Badr Nabil', headline: 'Regulatory Officer', company: 'Eva Pharma', location: 'Cairo, Egypt', note: 'Looking for a senior role in a growing team.', cv: true, status: 'submitted', created_at: daysAgo(2) },
      { name: 'Chadi Haddad', headline: 'Registration Pharmacist', company: 'Hikma', location: 'Giza, Egypt', note: 'GCC and EDA files, stability studies.', cv: false, status: 'viewed', created_at: daysAgo(4) }],
    'Country Manager — Egypt & North Africa': [
      { name: 'Sara Mansour', headline: 'Regulatory Affairs Specialist', company: 'Freelance', location: 'Cairo, Egypt', note: 'Interested in the regional strategy side of the role.', cv: true, status: 'submitted', created_at: daysAgo(5) }]
  };
  var DEMO_STAGES = ['submitted', 'viewed', 'shortlisted', 'interviewed', 'hired', 'rejected', 'no_show'];
  function dstore(k, d) { return D.store.get(k, d); }
  function dsave(k, v) { D.store.set(k, v); }
  function staticJobs() {   /* the approved page's job cards, read once from its markup (also when the Jobs page was never opened) */
    if (staticJobs.v) return staticJobs.v;
    var out = [], tpl = document.createElement('template'); tpl.innerHTML = window.JX_HTML || '';
    [].forEach.call(tpl.content.querySelectorAll('.jcard'), function (c) { if (!isJob(c)) return; out.push(fromCard(c)); });
    return (staticJobs.v = out);
  }
  function fromCard(c) {
    var sp = c.querySelectorAll('.jc-company > span'), place = sp[1] ? txt(sp[1]) : '', t = titleOf(c), d = DETAILS[t] || {};
    var posted = dstore('jxPosted', []).filter(function (p) { return p.title === t; })[0];
    if (posted) return posted;
    return { key: t, title: t, company: txt(sp[0]), location: place.replace(/^\S+\s/, ''), country: cardCountry(c), type: txt(c.querySelector('.jt')) || 'Full-time',
             level: c.dataset.level || 'mid', category: c.dataset.cat || 'other', description: txt(c.querySelector('.jc-desc')), posted: txt(c.querySelector('.jc-posted')),
             verified: /Verified/.test(txt(c.querySelector('.jc-company'))), salary: d.salary || '', deadline: d.deadline || '', requirements: d.requirements || [], benefits: d.benefits || [],
             tags: [].map.call(c.querySelectorAll('.jt'), txt).slice(1), mine: txt(sp[0]) === MY_CO, active: true };
  }
  function demoJob(key) {
    var p = dstore('jxPosted', []).filter(function (x) { return x.key === key; })[0]; if (p) return p;
    var e = dstore('jxEdits', {})[key], j = staticJobs().filter(function (x) { return x.key === key; })[0]; if (!j) return null;
    j = Object.assign({}, j, e || {}); j.active = dstore('jxClosed', {})[key] ? false : true; return j;
  }
  function deleted(key) { return !!dstore('jxDeleted', {})[key]; }

  var DEMO = {
    live: false,
    detail: function (key) { var j = demoJob(key); return Promise.resolve(j && Object.assign({}, j)); },
    myApplications: function () {
      var mine = dstore('jxApps', null); if (!mine) { mine = SEED_APPS.slice(); dsave('jxApps', mine); }
      return Promise.resolve(mine.map(function (a) { var j = demoJob(a.title); return Object.assign({ key: a.title, active: j ? j.active : true }, a); }));
    },
    withdraw: function (key) { dsave('jxApps', dstore('jxApps', []).filter(function (a) { return a.title !== key; }));
      var ap = dstore('jxApplied', {}); delete ap[key]; dsave('jxApplied', ap); return Promise.resolve(); },
    myJobs: function () {
      var all = dstore('jxPosted', []).concat(staticJobs().filter(function (j) { return j.mine; }).map(function (j) { return demoJob(j.key); }))
        .filter(function (j) { return j && !deleted(j.key); });
      return Promise.resolve(all.map(function (j) { var a = demoApplicants(j.key), st = {}; a.forEach(function (x) { st[x.status] = (st[x.status] || 0) + 1; });
        return Object.assign({}, j, { id: j.key, applicant_count: a.length, stages: st, expired: !!(j.deadline && j.deadline < today()) }); }));
    },
    applicants: function (key) { return Promise.resolve(demoApplicants(key)); },
    setStatus: function (key, who, status, extra) {
      var all = dstore('jxApplicants', null) || JSON.parse(JSON.stringify(SEED_APPLICANTS));
      (all[key] || []).forEach(function (a) { if (a.name !== who) return; if (status === 'viewed' && a.status !== 'submitted') return;
        a.status = status; a.status_at = new Date().toISOString(); if (extra && extra.interview_at) a.interview_at = extra.interview_at; if (extra && extra.note != null) a.employer_note = extra.note; });
      dsave('jxApplicants', all); return Promise.resolve();
    },
    openCv: function () { toast('This sample CV opens in the live app (a private link that expires)'); return Promise.resolve(); },
    message: function (key, who) { var u = window.mkxFindUser ? window.mkxFindUser(who) : null; if (u && window.messageUser) window.messageUser(u.id); return Promise.resolve(); },
    profile: function (key, who) { var u = window.mkxFindUser ? window.mkxFindUser(who) : null; if (u && window.gotoProfile) window.gotoProfile(u.id); return Promise.resolve(); },
    updateJob: function (key, f) { var p = dstore('jxPosted', []), hit = p.filter(function (x) { return x.key === key; })[0];
      if (hit) { Object.assign(hit, f); dsave('jxPosted', p); } else { var e = dstore('jxEdits', {}); e[key] = Object.assign(e[key] || {}, f); dsave('jxEdits', e); }
      return Promise.resolve(); },
    setOpen: function (key, open) { var p = dstore('jxPosted', []), hit = p.filter(function (x) { return x.key === key; })[0];
      if (hit) { hit.active = open; dsave('jxPosted', p); } else { var c = dstore('jxClosed', {}); if (open) delete c[key]; else c[key] = 1; dsave('jxClosed', c); }
      return Promise.resolve(); },
    deleteJob: function (key) { var p = dstore('jxPosted', []); if (p.some(function (x) { return x.key === key; })) dsave('jxPosted', p.filter(function (x) { return x.key !== key; }));
      else { var d = dstore('jxDeleted', {}); d[key] = 1; dsave('jxDeleted', d); } return Promise.resolve(); },
    postJob: function (f) { var p = dstore('jxPosted', []), key = f.title; p = p.filter(function (x) { return x.key !== key; });
      p.unshift(Object.assign({ key: key, company: MY_CO, verified: true, mine: true, active: true, created_at: new Date().toISOString() }, f)); dsave('jxPosted', p); return Promise.resolve(key); },
    profileState: function () { return Promise.resolve(dstore('jxMyProfile', { open: false })); },
    publishProfile: function (f) { dsave('jxMyProfile', Object.assign({ open: true, since: new Date().toISOString() }, f)); return Promise.resolve(); },
    hideProfile: function () { var p = dstore('jxMyProfile', {}); p.open = false; dsave('jxMyProfile', p); return Promise.resolve(); },
    savedJobs: function () {
      var keys = dstore('savedJobs', []), out = [];
      keys.forEach(function (k) { var j = staticJobs().concat(dstore('jxPosted', [])).filter(function (x) { return k === x.key || String(k).slice(-x.key.length) === x.key; })[0];
        if (j && !out.some(function (o) { return o.key === j.key; })) out.push(demoJob(j.key) || j); });
      return Promise.resolve(out);
    },
    unsave: function (key) { dsave('savedJobs', dstore('savedJobs', []).filter(function (k) { return !(k === key || String(k).slice(-key.length) === key); })); return Promise.resolve(); },
    isSaved: function (key) { return dstore('savedJobs', []).some(function (k) { return k === key || String(k).slice(-key.length) === key; }); },
    alerts: function () { return Promise.resolve(dstore('jxAlerts', [])); },
    saveAlert: function (a) { var l = dstore('jxAlerts', []); if (l.length >= 20) return Promise.reject(new Error('You can keep up to 20 job alerts'));
      a.id = Date.now(); a.created_at = new Date().toISOString(); l.unshift(a); dsave('jxAlerts', l); return Promise.resolve(a); },
    deleteAlert: function (id) { dsave('jxAlerts', dstore('jxAlerts', []).filter(function (a) { return a.id !== id; })); return Promise.resolve(); }
  };
  function demoApplicants(key) { var all = dstore('jxApplicants', null) || SEED_APPLICANTS; return JSON.parse(JSON.stringify(all[key] || [])); }

  /* ── dates and statuses in words ──────────────────────────────────────────────────────────────────────────────────── */
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function day(s) { if (!s) return ''; var d = new Date(String(s).length === 10 ? s + 'T12:00:00' : s); if (isNaN(d)) return String(s);
    if (document.documentElement.lang === 'ar') try { return d.toLocaleDateString('ar-EG', { day: 'numeric', month: 'long', year: 'numeric' }); } catch (e) {}
    return d.getDate() + ' ' + MON[d.getMonth()] + ' ' + d.getFullYear(); }
  var ST = { submitted: 'Submitted', viewed: 'Viewed', shortlisted: 'Shortlisted', interviewed: 'Interview', hired: 'Hired', rejected: 'Rejected', no_show: 'No-show', withdrawn: 'Withdrawn' };
  function uc(v) { return v ? '<span data-noi18n dir="auto">' + esc(v) + '</span>' : ''; }   /* what people wrote: never translated */
  function stBadge(s) { return '<span class="jx-st jx-st-' + esc(s) + '">' + esc(ST[s] || s) + '</span>'; }

  /* ── 1. the page: search box, filter labels, phone filters, list tools ────────────────────────────────────────────── */
  var F = { q: '', types: [], countries: [], cat: 'all', lvl: 'all' };
  function decorate() {
    var root = jx(); if (!root || root.dataset.jxx) return; root.dataset.jxx = '1';
    /* the employment-type and country options become labels (their text ticks the box) and start empty: nothing ticked = every job */
    var box = root.querySelector('.filters'), group = '';
    if (box) [].slice.call(box.children).forEach(function (el) {
      if (el.classList.contains('f-hdr')) group = /country/i.test(txt(el)) ? 'country' : /employment/i.test(txt(el)) ? 'type' : '';
      if (!el.classList.contains('f-opt') || !group) return;
      var lab = document.createElement('label'); lab.className = 'f-opt'; while (el.firstChild) lab.appendChild(el.firstChild);
      var cb = lab.querySelector('input'); if (cb) { cb.checked = false; cb.removeAttribute('checked'); cb.dataset.jxf = group;
        var v = txt(lab).replace(/^[^A-Za-z]+/, '').trim(); cb.value = group === 'country' ? ({ 'Egypt': 'EG', 'UAE': 'AE', 'Saudi Arabia': 'SA', 'India': 'IN' }[v] || v) : v.toLowerCase(); }
      el.parentNode.replaceChild(lab, el);
    });
    /* phones: the filter column opens from a button (it is hidden under 900 px) */
    var lay = root.querySelector('.layout');
    if (lay && box && !root.querySelector('.jx-ftoggle')) {
      var tg = document.createElement('button'); tg.type = 'button'; tg.className = 'jx-ftoggle'; tg.textContent = '⚙ Filters';
      tg.addEventListener('click', function () { var o = box.classList.toggle('jx-open'); tg.textContent = o ? '✕ Close filters' : '⚙ Filters'; });
      lay.parentNode.insertBefore(tg, lay);
    }
    /* the keyword search and "Save this search" above both lists */
    var main = root.querySelector('.main');
    if (main && !root.querySelector('.jx-searchbar')) {
      var sb = document.createElement('div'); sb.className = 'jx-searchbar';
      sb.innerHTML = '<input type="search" class="jx-q" placeholder="Search jobs: title, company, skill…" aria-label="Search jobs">' +
        '<button type="button" class="jx-tool jx-alert-btn" data-jx="alert">🔔 Save this search</button><button type="button" class="jx-tool jx-clear" data-jx="clear" hidden>✕ Clear filters</button>';
      var hv = root.querySelector('#huntingView'); if (hv) { var cta = hv.querySelector('.post-cta'); hv.insertBefore(sb, cta ? cta.nextSibling : hv.firstChild); }
      var q = sb.querySelector('.jx-q'), tmr = null;
      q.addEventListener('input', function () { clearTimeout(tmr); tmr = setTimeout(function () { F.q = q.value.trim(); run(); }, live() ? 350 : 120); });
      q.addEventListener('keydown', function (e) { if (e.key === 'Enter') { clearTimeout(tmr); F.q = q.value.trim(); run(); } });
    }
    /* the profile bar under "Post My Profile": shown while my profile is visible to companies */
    var hcta = root.querySelector('#huntingView .post-cta');
    if (hcta && !root.querySelector('.jx-otw')) { var bar = document.createElement('div'); bar.className = 'jx-otw'; bar.hidden = true; hcta.parentNode.insertBefore(bar, hcta.nextSibling); }
    /* list tools: my applications and alerts (job seekers), my jobs and applicants (employers) */
    tools();
    root.addEventListener('change', function (e) {
      var cb = e.target.closest && e.target.closest('input[data-jxf]'); if (!cb) return;
      F.types = [].map.call(root.querySelectorAll('input[data-jxf=type]:checked'), function (x) { return x.value; });
      F.countries = [].map.call(root.querySelectorAll('input[data-jxf=country]:checked'), function (x) { return x.value; });
      run();
    });
    root.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('.cf-tag[data-cat], .sen-opt[data-level]'); if (!t) return;
      if (t.dataset.cat) F.cat = t.dataset.cat; if (t.dataset.level) F.lvl = t.dataset.level;
      setTimeout(run, 0);
    });
  }
  function tools() {
    var root = jx(); if (!root) return;
    root.querySelectorAll('.jx-tools').forEach(function (t) {
      if (t.querySelector('[data-jx]')) return;
      if (t.dataset.side === 'candidate') t.insertAdjacentHTML('afterbegin', '<button type="button" class="jx-tool" data-jx="apps">📄 My applications</button><button type="button" class="jx-tool" data-jx="alerts">🔔 Job alerts</button>');
      else t.insertAdjacentHTML('afterbegin', '<button type="button" class="jx-tool" data-jx="myjobs">💼 My jobs</button><button type="button" class="jx-tool" data-jx="applicants">👥 Applicants</button>');
    });
  }

  /* ── 2. filtering: the demo filters the cards on the page; the live app asks the database (one call per page) ──────── */
  function words(s) { return String(s || '').toLowerCase().split(/\s+/).filter(Boolean); }
  function demoMatch(card) {
    var j = fromCard(card), hay = [j.title, j.company, j.location, j.description, (j.tags || []).join(' '), (j.requirements || []).join(' '), txt(card.querySelector('.jc-tags'))].join(' ').toLowerCase();
    if (words(F.q).some(function (w) { return hay.indexOf(w) < 0; })) return false;
    if (F.types.length && !(F.types.indexOf(cardType(card)) >= 0 || (F.types.indexOf('remote') >= 0 && cardRemote(card)))) return false;
    if (F.countries.length && F.countries.indexOf(cardCountry(card)) < 0) return false;
    return true;
  }
  var running = 0;
  function run(more) {
    var root = jx(); if (!root) return;
    if (live()) {
      var my = ++running;
      return window.dxJobs.search({ q: F.q, category: F.cat === 'all' ? null : F.cat, types: F.types, countries: F.countries, level: F.lvl === 'all' ? null : F.lvl }, !!more)
        .then(function () { if (my === running) after(); }, function (e) { toast((e && e.message) || 'Could not load the jobs'); });
    }
    jobCards(root).forEach(function (c) { var k = c.dataset.jxPosted || titleOf(c), dj = demoJob(k); if (deleted(k) || (c.dataset.jxPosted && !dj)) { c.remove(); return; } c.dataset.jxSearch = demoMatch(c) && !(dj && dj.active === false) ? '' : '0'; });
    if (window.dxJxPaint) window.dxJxPaint();
    after();
  }
  function shownJobs() { return jobCards().filter(function (c) { return c.style.display !== 'none' && c.dataset.jxSearch !== '0'; }); }
  function after() {
    var root = jx(); if (!root) return;
    var n = live() ? window.dxJobs.total() : shownJobs().length;
    root.querySelectorAll('.sec-title').forEach(function (t) { var sp = t.querySelector('span'), o = window.dxOrigText ? window.dxOrigText(t) : t.textContent;
      if (sp && /^\s*Open Positions/.test(o)) { sp.textContent = (n == null ? '…' : Number(n).toLocaleString('en')) + (n === 1 ? ' job' : ' jobs'); } });
    var list = jobCards()[0] ? jobCards()[0].parentElement : root.querySelector('#huntingView .job-list');
    root.querySelectorAll('.jx-none, .dx-jobs-empty').forEach(function (e) { e.remove(); });
    var filtered = F.q || F.types.length || F.countries.length || F.cat !== 'all' || F.lvl !== 'all';
    root.querySelectorAll('.jx-clear').forEach(function (b) { b.hidden = !filtered; });
    if (!live()) root.querySelectorAll('.sec-title').forEach(function (t) { var sp = t.querySelector('span'), o = window.dxOrigText ? window.dxOrigText(t) : t.textContent;
      if (sp && /^\s*Available Candidates/.test(o)) { var k = [].filter.call(root.querySelectorAll('.jcard'), function (c) { return c.querySelector('.role-badge.need') && c.style.display !== 'none'; }).length; sp.textContent = k + (k === 1 ? ' profile' : ' profiles'); } });
    if (list && !n && filtered) {
      var e = document.createElement('div'); e.className = 'jx-none';
      e.innerHTML = '<b>No jobs match these filters</b><p>Try other words, or clear the filters.</p><button type="button" class="jx-tool" data-jx="clear">Clear filters</button>';
      list.appendChild(e);
    }
    /* Load more (live): the next page of the same search */
    root.querySelectorAll('.jx-more').forEach(function (b) { b.remove(); });
    if (live() && list && window.dxJobs.hasMore()) {
      var m = document.createElement('button'); m.type = 'button'; m.className = 'jx-more'; m.textContent = 'Load more jobs';
      list.parentNode.insertBefore(m, list.nextSibling);
    }
    paintOwn(); paintSaves(); paintCvButtons();
  }
  function clearFilters() {
    var root = jx(); F.q = ''; F.types = []; F.countries = []; F.cat = 'all'; F.lvl = 'all';
    if (root) { var q = root.querySelector('.jx-q'); if (q) q.value = '';
      root.querySelectorAll('input[data-jxf]').forEach(function (c) { c.checked = false; });
      var a = root.querySelector('.cf-tag[data-cat=all]'), l = root.querySelector('.sen-opt[data-level=all]'); if (a) a.click(); if (l) l.click(); }
    run();
  }
  window.dxJobsFilter = function () { return { q: F.q, category: F.cat === 'all' ? null : F.cat, types: F.types, countries: F.countries, level: F.lvl === 'all' ? null : F.lvl }; };

  /* my own jobs: "Applicants (n)" instead of Apply (nobody applies to his own company's job) */
  function paintOwn() {
    jobCards().forEach(function (c) {
      var mine = live() ? c.dataset.jxMine === '1' : demoMine(c), b = c.querySelector('.apply-btn'); if (!b || !mine) return;
      var n = live() ? +(c.dataset.jxApplicants || 0) : demoApplicants(titleOf(c)).length;
      b.textContent = '👥 Applicants (' + n + ')'; b.removeAttribute('onclick'); b.dataset.jxOwn = live() ? c.dataset.live.slice(1) : titleOf(c); b.disabled = false;
    });
  }
  /* Save buttons follow the saved list wherever it changed (the Saved page, another tab) */
  function paintSaves() {
    if (live()) return;
    jobCards().forEach(function (c) { var b = c.querySelector('.save-btn'); if (!b) return; var on = DEMO.isSaved(titleOf(c));
      b.classList.toggle('dbk-saved', on); b.textContent = on ? '🔖 Saved' : '🔖 Save'; });
  }
  /* the CV a candidate published with Post My Profile (verified companies, through a private link that expires) */
  function paintCvButtons() {
    [].forEach.call(document.querySelectorAll('#jx .jcard'), function (c) {
      if (!c.querySelector('.role-badge.need') || c.dataset.jxMe || c.querySelector('.jx-cvbtn')) return;
      var r = c.querySelector('.jc-right'); if (r) r.insertAdjacentHTML('beforeend', '<button type="button" class="save-btn jx-cvbtn">📄 CV</button>');
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#jx .jx-cvbtn'); if (!b) return; e.preventDefault(); e.stopPropagation();
    var c = b.closest('.jcard');
    if (live() && c.dataset.uid) window.dxJobs.candidateCv(c.dataset.uid).catch(err);
    else toast('Sample CVs open in the live app — a private link that expires');
  }, true);

  /* demo: the jobs I posted, at the top of Open Positions (the approved first job card is the template) */
  function paintPosted() {
    if (live()) return; var root = jx(); if (!root) return;
    var cards = jobCards(root), tpl = cards.filter(function (c) { return !c.dataset.jxPosted; })[0]; if (!tpl) return;
    var list = tpl.parentElement;
    dstore('jxPosted', []).slice().reverse().forEach(function (j) {
      if (root.querySelector('.jcard[data-jx-posted="' + CSS.escape(j.key) + '"]')) return;
      var c = tpl.cloneNode(true); c.dataset.jxPosted = j.key; delete c.dataset.jxIdx; c.dataset.cat = j.category || 'other'; c.dataset.level = j.level || 'mid'; c.style.display = '';
      c.querySelectorAll('.jx-trust').forEach(function (x) { x.remove(); });
      var t = c.querySelector('.jc-title'), rb = t.querySelector('.role-badge'), lb = t.querySelector('.level-badge'); t.textContent = j.title;
      if (lb) { lb.className = 'level-badge level-' + (j.level || 'mid'); lb.textContent = LEVELS[j.level] || LEVELS.mid; t.insertBefore(lb, t.firstChild); } if (rb) t.insertBefore(rb, t.firstChild);
      c.querySelector('.jc-logo').textContent = D.initials(j.company);
      c.querySelector('.jc-company').innerHTML = '<span>' + esc(j.company) + '</span> · <span>' + (FLAG[j.country] || '') + ' ' + esc(j.location || '') + '</span> · <span style="color:#1a56db">✓ Verified</span>';
      c.querySelector('.jc-tags').innerHTML = '<span class="jt jt-ft">' + esc(j.type || 'Full-time') + '</span>' + (j.salary ? '<span class="jt" style="background:#dcfce7;color:#15803d">' + esc(j.salary) + '</span>' : '');
      c.querySelector('.jc-desc').textContent = j.description || '';
      c.querySelector('.jc-posted').textContent = ago(j.created_at);
      var ap = c.querySelector('.apply-btn'); ap.setAttribute('onclick', 'openApplyModal(' + JSON.stringify(j.title) + ',' + JSON.stringify(j.company) + ')'); ap.className = 'apply-btn'; ap.textContent = 'Apply Now →';
      list.insertBefore(c, list.firstChild);
    });
  }
  function ago(s) { var m = Math.max(0, (Date.now() - new Date(s).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? Math.floor(m) + 'm ago' : m < 1440 ? Math.floor(m / 60) + 'h ago' : Math.floor(m / 1440) + 'd ago'; }
  /* demo: an edited / closed / deleted sample job shows that way on the page too */
  function paintDemoState() {
    if (live()) return;
    jobCards().forEach(function (c) { var k = c.dataset.jxPosted || titleOf(c), j = demoJob(k);
      if (!j || deleted(k)) { c.remove(); return; }
      if (j.active === false) c.dataset.jxSearch = '0';
      var sal = c.querySelector('.jx-sal'); if (j.salary && dstore('jxEdits', {})[k] && dstore('jxEdits', {})[k].salary) { if (!sal) { sal = document.createElement('span'); sal.className = 'jt jx-sal'; sal.style.cssText = 'background:#dcfce7;color:#15803d'; c.querySelector('.jc-tags').appendChild(sal); } sal.textContent = j.salary; } });
  }

  /* ── 3. the job's details ─────────────────────────────────────────────────────────────────────────────────────────── */
  function detailModal(key) {
    S().detail(key).then(function (j) {
      if (!j) { toast('This job is no longer available'); return; }
      var closed = j.active === false, mine = !!j.mine;
      var row = function (k, v, raw) { return v ? '<div class="jx-dr"><span>' + esc(k) + '</span><b' + (raw ? '' : ' data-noi18n dir="auto"') + '>' + (raw ? v : esc(v)) + '</b></div>' : ''; };
      var list = function (h, a) { return a && a.length ? '<div class="jx-dh">' + esc(h) + '</div><ul class="jx-dl" data-noi18n dir="auto">' + a.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : ''; };
      var body = (closed ? '<div class="jx-closed">This job is closed — it no longer takes applications.</div>' : '') +
        '<div class="jx-dco"><b class="jx-dcn" data-slug="' + esc(j.slug || '') + '" data-noi18n dir="auto">' + esc(j.company || '') + '</b>' + (j.verified ? ' <span style="color:#1a56db">✓ Verified</span>' : '') + '</div>' +
        '<div class="jx-dgrid">' + row('Location', (FLAG[j.country] || '') + ' ' + uc(j.location) + (CNAME[j.country] && String(j.location || '').indexOf(CNAME[j.country]) < 0 ? (j.location ? ', ' : '') + '<span>' + esc(CNAME[j.country]) + '</span>' : ''), true) +
          row('Type', '<span>' + esc(j.type || '') + '</span>', true) + row('Level', '<span>' + esc((LEVELS[j.level] || '').replace(/^\S+\s/, '')) + '</span>', true) +
          row('Salary', j.salary ? uc(j.salary) : '<span>Not shown</span>', true) + row('Apply by', j.deadline ? esc(day(j.deadline)) : '<span>Open until filled</span>', true) + row('Posted', esc(j.created_at ? day(j.created_at) : j.posted), true) + '</div>' +
        (j.description ? '<div class="jx-dh">Description</div><p class="jx-dp" data-noi18n dir="auto">' + esc(j.description) + '</p>' : '') +
        list('Requirements', j.requirements) + list('Benefits', j.benefits) +
        (!(j.requirements || []).length ? '<div class="jx-dh">Requirements</div><p class="jx-dp jx-muted">Not listed by the employer.</p>' : '');
      var applied = live() ? window.dxJobs.applied(key) : !!dstore('jxApplied', {})[key] || (dstore('jxApps', null) || SEED_APPS).some(function (a) { return a.title === key; });
      var m = D.modal({ title: j.title, body: body, secondary: 'Close',
        primary: closed ? null : mine ? { label: '👥 Applicants', onClick: function () { setTimeout(function () { openJobsPanel(key); }, 30); } }
          : { label: applied ? '✓ Applied' : 'Apply Now →', onClick: function () { if (applied) return; setTimeout(function () { openApply(key, j); }, 30); } } });
      var ft = m.el.querySelector('.dbk-ft');
      if (ft && !mine) { var sv = document.createElement('button'); sv.type = 'button'; sv.className = 'dbk-btn s jx-dsave';
        var on = live() ? window.dxJobs.isSaved(key) : DEMO.isSaved(key); sv.textContent = on ? '✓ Saved' : '🔖 Save'; ft.insertBefore(sv, ft.firstChild);
        sv.addEventListener('click', function () { toggleSave(key, j).then(function (now) { sv.textContent = now ? '✓ Saved' : '🔖 Save'; }); }); }
      if (applied) { var ok = m.el.querySelector('[data-a=ok]'); if (ok) ok.disabled = true; }
      var cn = m.el.querySelector('.jx-dcn'); if (cn && j.slug && window.dxHub) { cn.style.cursor = 'pointer'; cn.addEventListener('click', function () { m.close(); window.dxHub.page(j.slug); }); }
    });
  }
  function openApply(key, j) {
    goJobs(); setTimeout(function () {
      var c = cardFor(key), b = c && c.querySelector('.apply-btn');
      if (b && !b.dataset.jxOwn) { b.click(); return; }
      if (live()) window.dxJobs.setCurrent(key); else lastApply = key;
      if (window.openApplyModal) window.openApplyModal(j.title, j.company); setTimeout(function () { cvInput('applyModal', 'dxCv'); }, 0);
    }, 80);
  }
  function cardFor(key) { return jobCards().filter(function (c) { return (live() ? c.dataset.live === 'j' + key : (c.dataset.jxPosted || titleOf(c)) === key); })[0] || null; }
  function goJobs() { if (document.body.getAttribute('data-page') !== 'jobs' && window.goto) window.goto('jobs'); }
  function toggleSave(key, j) {
    if (live()) return window.dxJobs.toggleSave(key);
    var on = DEMO.isSaved(key);
    if (on) DEMO.unsave(key); else { var l = dstore('savedJobs', []); l.push(key); dsave('savedJobs', l); }
    toast(on ? 'Removed from saved jobs' : 'Saved — find it on your Saved page'); paintSaves(); return Promise.resolve(!on);
  }

  /* ── 4. panels inside the Jobs page: My applications · My jobs and their applicants ─────────────────────────────── */
  var P = { kind: null, focus: null };
  function panel() {
    var root = jx(); if (!root) return null; var p = root.querySelector('#jxPanel');
    if (!p) { p = document.createElement('div'); p.id = 'jxPanel'; p.className = 'jx-panel'; p.hidden = true; var main = root.querySelector('.main'); if (!main) return null; main.insertBefore(p, main.firstChild); }
    return p;
  }
  function showPanel(on) {
    var root = jx(), p = panel(); if (!root || !p) return;
    p.hidden = !on; root.classList.toggle('jx-paneled', !!on);
    if (!on) { P.kind = null; P.focus = null; p.innerHTML = ''; }
  }
  function head(title, n) { return '<div class="jx-ph"><button type="button" class="jx-back" data-jx="back">← Back to jobs</button><div class="sec-title">' + esc(title) + (n != null ? ' <span>' + n + '</span>' : '') + '</div></div>'; }
  function openApps() {
    goJobs(); var p = panel(); if (!p) return; P.kind = 'apps'; showPanel(true); p.innerHTML = head('📄 My applications') + '<div class="jx-loading">Loading…</div>';
    S().myApplications().then(function (rows) {
      if (P.kind !== 'apps') return;
      p.innerHTML = head('📄 My applications', rows.length) + (rows.length ? rows.map(appRow).join('') : '<div class="jx-none"><b>No applications yet</b><p>Apply to a job and follow it here.</p></div>');
    }, err);
  }
  function appRow(a) {
    var open = ['hired', 'rejected', 'no_show'].indexOf(a.status) < 0;
    return '<div class="jx-pcard" data-key="' + esc(a.key || a.job_id) + '"><div class="jc-logo" style="background:#1a56db">' + esc(D.initials(a.company || a.title)) + '</div>' +
      '<div class="jx-pb"><div class="jx-pt"><span class="jx-ptt" data-noi18n dir="auto">' + esc(a.title) + '</span>' + (a.active === false ? ' <span class="jx-st jx-st-closed">Closed</span>' : '') + '</div>' +
      '<div class="jx-pm">' + uc(a.company) + ' · ' + (FLAG[a.country] || '') + ' ' + uc(a.location) + ' · <span>Applied</span> ' + esc(day(a.created_at)) + '</div>' +
      '<div class="jx-pm">' + stBadge(a.status) + ' <span class="jx-since"><span>since</span> ' + esc(day(a.status_at || a.created_at)) + '</span>' + (a.interview_at && a.status === 'interviewed' ? ' · <span>📅 Interview</span> ' + esc(day(a.interview_at)) : '') + '</div>' +
      (a.employer_note ? '<div class="jx-note" data-noi18n dir="auto">“' + esc(a.employer_note) + '”</div>' : '') + '</div>' +
      '<div class="jx-pa"><button type="button" class="jx-tool" data-jx="view">View job</button>' + (open ? '<button type="button" class="jx-tool jx-warn" data-jx="withdraw">Withdraw</button>' : '') + '</div></div>';
  }
  function openJobsPanel(focusJob, focusWho) {
    goJobs(); var p = panel(); if (!p) return; P.kind = 'jobs'; P.focus = focusJob || null; showPanel(true);
    p.innerHTML = head('💼 My jobs and applicants') + '<div class="jx-loading">Loading…</div>';
    S().myJobs().then(function (jobs) {
      if (P.kind !== 'jobs') return;
      if (focusJob != null) jobs.sort(function (a, b) { return (String(b.id) === String(focusJob)) - (String(a.id) === String(focusJob)); });
      p.innerHTML = head('💼 My jobs and applicants', jobs.length) + (jobs.length ? jobs.map(jobRow).join('') :
        '<div class="jx-none"><b>You have not posted a job yet</b><p>Post a job and the people who apply show here.</p><button type="button" class="jx-tool" data-jx="post">➕ Post a Job</button></div>');
      jobs.slice(0, 6).forEach(function (j) { if (j.applicant_count || String(j.id) === String(focusJob)) loadApplicants(j.id, String(j.id) === String(focusJob) ? focusWho : null); });
      if (focusJob != null) { var r = p.querySelector('.jx-job[data-id="' + CSS.escape(String(focusJob)) + '"]'); if (r) r.scrollIntoView({ block: 'start' }); }
    }, err);
  }
  var STAGES = [['submitted', 'Submitted'], ['viewed', 'Viewed'], ['shortlisted', 'Shortlisted'], ['interviewed', 'Interview'], ['hired', 'Hired'], ['rejected', 'Rejected'], ['no_show', 'No-show']];
  function stagesLine(st) { st = st || {}; return STAGES.map(function (s) { return '<span class="jx-stage">' + esc(s[1]) + ' <b>' + (st[s[0]] || 0) + '</b></span>'; }).join(''); }
  function jobRow(j) {
    var state = j.active === false ? 'Closed' : j.expired ? 'Expired' : 'Accepting applications';
    return '<div class="jx-pcard jx-job" data-id="' + esc(j.id) + '"><div class="jc-logo" style="background:#0f172a">' + esc(D.initials(j.company || j.title)) + '</div>' +
      '<div class="jx-pb"><div class="jx-pt"><span class="jx-ptt" data-noi18n dir="auto">' + esc(j.title) + '</span> <span class="jx-st jx-st-' + (state === 'Closed' ? 'closed' : state === 'Expired' ? 'expired' : 'open') + '">' + esc(state) + '</span></div>' +
      '<div class="jx-pm">' + uc(j.company) + ' · ' + (FLAG[j.country] || '') + ' ' + uc(j.location) + (j.salary ? ' · ' + uc(j.salary) : '') + (j.deadline ? ' · <span>Apply by</span> ' + esc(day(j.deadline)) : '') + '</div>' +
      '<div class="jx-pm"><b class="jx-apn">' + (j.applicant_count || 0) + ' ' + (j.applicant_count === 1 ? 'applicant' : 'applicants') + '</b></div><div class="jx-stages">' + stagesLine(j.stages) + '</div></div>' +
      '<div class="jx-pa"><button type="button" class="jx-tool" data-jx="toggle">👥 Applicants (' + (j.applicant_count || 0) + ')</button><button type="button" class="jx-tool" data-jx="edit">✏️ Edit</button>' +
      (j.active === false ? '<button type="button" class="jx-tool" data-jx="reopen">↺ Reopen</button>' : '<button type="button" class="jx-tool" data-jx="close">Close job</button>') +
      '<button type="button" class="jx-tool jx-warn" data-jx="delete">🗑 Delete</button></div></div><div class="jx-apps" data-for="' + esc(j.id) + '" hidden></div>';
  }
  function loadApplicants(id, focusWho) {
    var p = panel(), box = p && p.querySelector('.jx-apps[data-for="' + CSS.escape(String(id)) + '"]'); if (!box) return;
    box.hidden = false; box.innerHTML = '<div class="jx-loading">Loading applicants…</div>';
    S().applicants(id).then(function (rows) {
      box.innerHTML = rows.length ? rows.map(function (a) { return applicantRow(id, a); }).join('') : '<div class="jx-muted" style="padding:8px 14px">No applications yet.</div>';
      if (focusWho != null) { var r = box.querySelector('.jx-app[data-who="' + CSS.escape(String(focusWho)) + '"]'); if (r) { r.classList.add('jx-focus'); r.scrollIntoView({ block: 'center' }); viewed(id, String(focusWho), r); } }
    }, err);
  }
  function applicantRow(id, a) {
    var who = a.who != null ? a.who : a.name;
    return '<div class="jx-pcard jx-app" data-who="' + esc(who) + '" data-st="' + esc(a.status) + '">' + '<div class="jc-logo" style="background:#7A5680">' + esc(D.initials(a.name)) + '</div>' +
      '<div class="jx-pb"><div class="jx-pt"><a class="jx-who" data-jx="profile" data-noi18n dir="auto">' + esc(a.name) + '</a>' + (a.preferred ? ' <span class="jx-b white">⭐ Preferred</span>' : '') + '</div>' +
      '<div class="jx-pm">' + uc([a.headline, a.company, a.location].filter(Boolean).join(' · ')) + '</div>' +
      '<div class="jx-pm"><span>applied</span> ' + esc(day(a.created_at)) + ' · ' + stBadge(a.status) + (a.status_at ? ' <span class="jx-since"><span>since</span> ' + esc(day(a.status_at)) + '</span>' : '') + (a.interview_at && a.status === 'interviewed' ? ' · 📅 ' + esc(day(a.interview_at)) : '') + '</div>' +
      (a.note ? '<div class="jx-note" data-noi18n dir="auto">“' + esc(a.note) + '”</div>' : '') + '</div>' +
      '<div class="jx-pa">' + (a.cv ? '<button type="button" class="jx-tool" data-jx="cv">📄 CV</button>' : '') + '<button type="button" class="jx-tool" data-jx="msg">💬 Message</button>' +
      '<button type="button" class="jx-tool" data-jx="st" data-s="shortlisted">⭐ Shortlist</button><button type="button" class="jx-tool" data-jx="st" data-s="interviewed">📅 Interview</button>' +
      '<button type="button" class="jx-tool" data-jx="st" data-s="hired">✅ Hire</button><button type="button" class="jx-tool jx-warn" data-jx="st" data-s="rejected">✕ Reject</button>' +
      '<button type="button" class="jx-tool" data-jx="st" data-s="no_show">No-show</button></div></div>';
  }
  function viewed(id, who, row) {
    if (!row || row.dataset.st !== 'submitted') return;
    S().setStatus(id, who, 'viewed').then(function () { row.dataset.st = 'viewed'; var b = row.querySelector('.jx-st'); if (b) { b.className = 'jx-st jx-st-viewed'; b.textContent = 'Viewed'; } }, function () {});
  }
  function refreshJob(id) {   /* the job's row (counts per stage) and its applicants, after a change */
    S().myJobs().then(function (jobs) { var j = jobs.filter(function (x) { return String(x.id) === String(id); })[0], p = panel(); if (!j || !p) return;
      var r = p.querySelector('.jx-job[data-id="' + CSS.escape(String(id)) + '"]'); if (r) { var tmp = document.createElement('div'); tmp.innerHTML = jobRow(j); r.parentNode.replaceChild(tmp.firstChild, r); }
      loadApplicants(id); });
  }
  function setStatus(id, who, status, name) {
    var label = { shortlisted: 'shortlisted', interviewed: 'invited to an interview', hired: 'hired', rejected: 'not selected', no_show: 'marked as a no-show' }[status];
    function go(extra) { return S().setStatus(id, who, status, extra || {}).then(function () { toast(name + ' — ' + label + (status === 'viewed' ? '' : '; they were notified')); refreshJob(id); }, err); }
    if (status === 'interviewed') {
      var d = new Date(); d.setDate(d.getDate() + 7);
      D.modal({ title: 'Interview with ' + name, body: '<div class="dbk-f"><label for="jxIvDate">Interview date *</label><input id="jxIvDate" type="date" data-req value="' + d.toISOString().slice(0, 10) + '" min="' + today() + '"></div>' +
        '<div class="dbk-f"><label for="jxIvNote">Message to the candidate (optional)</label><textarea id="jxIvNote" maxlength="1000" placeholder="Place, time and who they will meet"></textarea></div>',
        primary: { label: 'Confirm', onClick: function (b) { if (!D.requireFields(b)) return false; go({ interview_at: b.querySelector('#jxIvDate').value, note: b.querySelector('#jxIvNote').value.trim() }); } } });
    } else if (status === 'rejected') {
      D.modal({ title: 'Not selected: ' + name, body: '<div class="dbk-note">' + esc(name) + ' is told politely that you went ahead with other candidates.</div><div class="dbk-f"><label for="jxRjNote">Note to the candidate (optional)</label><textarea id="jxRjNote" maxlength="1000"></textarea></div>',
        primary: { label: 'Confirm', danger: true, onClick: function (b) { go({ note: b.querySelector('#jxRjNote').value.trim() }); } } });
    } else if (status === 'hired') {
      D.modal({ title: 'Hire ' + name + '?', body: '<div class="dbk-note">' + esc(name) + ' is told the good news. You can both review each other afterwards.</div><label style="display:flex;gap:8px;align-items:center;font-size:12.5px;margin-top:10px"><input type="checkbox" id="jxHireClose" checked> Close this job now (it stops taking applications)</label>',
        primary: { label: 'Confirm', onClick: function (b) { var cl = b.querySelector('#jxHireClose').checked; go({}).then(function () { if (cl) return S().setOpen(id, false).then(function () { refreshJob(id); after(); }); }); } } });
    } else go({});
  }
  function editJob(id) {
    S().detail(id).then(function (j) { if (!j) return;
      D.modal({ title: 'Edit: ' + j.title, body:
        '<div class="dbk-f"><label for="jxEdT">Job title *</label><input id="jxEdT" data-req maxlength="200" value="' + esc(j.title) + '"></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="jxEdS">Salary</label><input id="jxEdS" maxlength="100" value="' + esc(j.salary || '') + '"></div>' +
        '<div class="dbk-f"><label for="jxEdD">Deadline</label><input id="jxEdD" type="date" value="' + esc(j.deadline || '') + '"></div></div>' +
        '<div class="dbk-f"><label for="jxEdL">Location</label><input id="jxEdL" maxlength="200" value="' + esc(j.location || '') + '"></div>' +
        '<div class="dbk-f"><label for="jxEdDesc">Description</label><textarea id="jxEdDesc" maxlength="10000">' + esc(j.description || '') + '</textarea></div>' +
        '<div class="dbk-f"><label for="jxEdR">Requirements (one per line)</label><textarea id="jxEdR">' + esc((j.requirements || []).join('\n')) + '</textarea></div>',
        primary: { label: 'Save changes', onClick: function (b) { if (!D.requireFields(b)) return false;
          var dl = b.querySelector('#jxEdD').value; if (dl && dl < today()) { b.querySelector('#jxEdD').classList.add('dbk-err'); toast('The deadline is in the past'); return false; }
          var lines = function (s) { return s.split('\n').map(function (x) { return x.trim(); }).filter(Boolean).slice(0, 30); };
          S().updateJob(id, { title: b.querySelector('#jxEdT').value.trim(), salary: b.querySelector('#jxEdS').value.trim(), deadline: b.querySelector('#jxEdD').value || null,
            location: b.querySelector('#jxEdL').value.trim(), description: b.querySelector('#jxEdDesc').value.trim(), requirements: lines(b.querySelector('#jxEdR').value) })
            .then(function () { toast('Job updated — job seekers see the change'); refreshJob(id); run(); }, err); } } });
    });
  }
  function err(e) { toast((e && e.message) || 'Something went wrong — please try again'); }

  /* ── 5. Apply: a CV file (PDF or Word, at most 10 MB) — checked before anything is sent ─────────────────────────── */
  var CV_OK = /\.(pdf|docx?)$/i, CV_MAX = 10 * 1024 * 1024;
  function cvCheck(f) { if (!f) return null; if (!CV_OK.test(f.name || '')) return 'The CV must be a PDF or Word file'; if (f.size > CV_MAX) return 'The CV is too large — at most 10 MB'; return null; }
  window.dxJobsCvCheck = cvCheck;
  function cvInput(modalId, id) {
    var m = document.getElementById(modalId); if (!m || m.querySelector('#' + id)) return;
    var zone = m.querySelector('.upload-zone-sm'); if (!zone) return;
    zone.innerHTML = '<label class="jx-file"><b>Upload</b> PDF or Word document <span class="jx-fname"></span><input type="file" id="' + id + '" accept=".pdf,.doc,.docx"></label>';
    var inp = zone.querySelector('input');
    inp.addEventListener('change', function () { var f = inp.files && inp.files[0], bad = cvCheck(f); zone.querySelector('.jx-fname').textContent = f ? '· ' + f.name : '';
      zone.classList.toggle('jx-bad', !!bad); if (bad) toast(bad); });
  }
  var lastApply = null;
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#jx .apply-btn'); if (!b) return;
    var card = b.closest('.jcard');
    if (b.dataset.jxOwn != null && b.dataset.jxOwn !== '') { e.preventDefault(); e.stopPropagation(); openJobsPanel(b.dataset.jxOwn); return; }
    if (card && !isJob(card)) {   /* Contact Candidate: a conversation with that person (the live app handles its own cards) */
      if (live() || card.dataset.live) return;
      e.preventDefault(); e.stopPropagation();
      var name = txt(card.querySelector('.jc-company span')); DEMO.message(null, name); return;
    }
    if (card && !live()) { var k = card.dataset.jxPosted || titleOf(card); if (dstore('jxApplied', {})[k]) { e.preventDefault(); e.stopPropagation(); toast('You already applied to this job'); return; } lastApply = k; }
    setTimeout(function () { cvInput('applyModal', 'dxCv'); }, 0);
  }, true);
  /* Send Application: a wrong file never leaves the browser */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#applyModal .btn-submit'); if (!b) return;
    var f = document.getElementById('dxCv'), bad = cvCheck(f && f.files && f.files[0]);
    if (bad) { e.preventDefault(); e.stopImmediatePropagation(); toast(bad); return; }
    if (!live() && lastApply) {
      var j = demoJob(lastApply) || { title: lastApply }, apps = dstore('jxApps', null) || SEED_APPS.slice();
      apps = apps.filter(function (a) { return a.title !== lastApply; }); apps.unshift({ title: j.title, company: j.company, location: j.location, country: j.country, status: 'submitted', created_at: new Date().toISOString(), status_at: new Date().toISOString(), cv: !!(f && f.files && f.files[0]) });
      dsave('jxApps', apps); var ap = dstore('jxApplied', {}); ap[lastApply] = 1; dsave('jxApplied', ap);
      var name = j.title, co = j.company; setTimeout(function () { toast('Application sent for ' + name + ' at ' + co + ' — follow it in My applications');
        var c = cardFor(lastApply), btn = c && c.querySelector('.apply-btn'); if (btn) { btn.textContent = '✓ Applied'; btn.disabled = true; btn.classList.add('dbk-done'); } if (f) f.value = ''; }, 60);
    }
  }, true);
  /* demo: jobs I applied to stay "Applied" */
  function paintApplied() { if (live()) return; var ap = Object.assign({}, dstore('jxApplied', {}));
    (dstore('jxApps', null) || SEED_APPS).forEach(function (a) { ap[a.title] = 1; });
    jobCards().forEach(function (c) { var k = c.dataset.jxPosted || titleOf(c), b = c.querySelector('.apply-btn'); if (b && ap[k] && !b.dataset.jxOwn) { b.textContent = '✓ Applied'; b.disabled = true; b.classList.add('dbk-done'); } }); }

  /* ── 6. Post a Job: country, deadline, requirements, benefits; the title is required ─────────────────────────────── */
  var COUNTRY_OPTS = ['EG', 'AE', 'SA', 'KW', 'QA', 'JO', 'OM', 'BH', 'IN'];
  function postForm() {
    var m = document.getElementById('postJobModal'); if (!m || m.dataset.jxx) return; m.dataset.jxx = '1';
    var body = m.querySelector('.modal-body'), ins = [].slice.call(m.querySelectorAll('input.field-input:not([disabled])'));
    ['title', 'location', 'exp', 'smin', 'smax'].forEach(function (k, i) { if (ins[i]) ins[i].dataset.jxk = k; });
    var locRow = ins[1] && ins[1].closest('.row2');
    var extra = document.createElement('div'); extra.className = 'row2';
    extra.innerHTML = '<div class="field"><label class="field-label" for="jxCountry">Country</label><select class="field-select" id="jxCountry">' + COUNTRY_OPTS.map(function (c) { return '<option value="' + c + '">' + FLAG[c] + ' ' + CNAME[c] + '</option>'; }).join('') + '</select></div>' +
      '<div class="field"><label class="field-label" for="jxDeadline">Application deadline</label><input class="field-input" type="date" id="jxDeadline" min="' + today() + '"></div>';
    if (locRow) locRow.parentNode.insertBefore(extra, locRow.nextSibling);
    var desc = m.querySelector('textarea'), dfield = desc && desc.closest('.field');
    if (dfield) { dfield.style.marginBottom = ''; dfield.insertAdjacentHTML('afterend',
      '<div class="field"><label class="field-label" for="jxReq">Requirements (one per line)</label><textarea class="field-textarea" id="jxReq" placeholder="Pharmacy degree&#10;3+ years in QA"></textarea></div>' +
      '<div class="field" style="margin-bottom:0"><label class="field-label" for="jxBen">Benefits (one per line)</label><textarea class="field-textarea" id="jxBen" placeholder="Medical insurance&#10;Transport"></textarea></div>'); }
    var sel = m.querySelector('#jxCountry'), touched = false; sel.addEventListener('change', function () { touched = true; });
    if (ins[1]) ins[1].addEventListener('input', function () { if (!touched) sel.value = placeCountry(ins[1].value); });
  }
  function readPost() {
    var m = document.getElementById('postJobModal'), v = function (k) { var e = m.querySelector('[data-jxk=' + k + ']'); return e ? String(e.value || '').trim() : ''; };
    var lines = function (id) { var e = m.querySelector('#' + id); return e ? e.value.split('\n').map(function (x) { return x.trim(); }).filter(Boolean).slice(0, 30) : []; };
    var pos = function (sel) { var all = [].slice.call(m.querySelectorAll(sel)); return all.indexOf(m.querySelector(sel + '.selected')); };
    var dept = m.querySelector('select.field-select:not(#jxCountry)'), ta = m.querySelector('textarea:not(#jxReq):not(#jxBen)'), exp = v('exp');
    var showSal = pos('.st-opt') !== 1, sal = showSal ? [v('smin'), v('smax')].filter(Boolean).join(' – ') : 'Competitive';
    var chips = [].map.call(m.querySelectorAll('.chip.selected'), txt);
    return { title: v('title'), location: v('location'), country: (m.querySelector('#jxCountry') || {}).value || placeCountry(v('location')), type: ['Full-time', 'Part-time', 'Contract', 'Remote'][pos('.radio-opt')] || 'Full-time',
      level: levelOf(exp), category: dept ? (CATS[dept.selectedIndex] || 'other') : 'other', description: ta ? ta.value.trim() : '', salary: sal || '', deadline: (m.querySelector('#jxDeadline') || {}).value || '',
      requirements: lines('jxReq'), benefits: lines('jxBen'), tags: (exp ? [exp.replace(/\s*(years?|yrs?)\s*$/i, '') + ' yrs exp'] : []).concat(chips).slice(0, 6), remote: pos('.radio-opt') === 3, exp: exp,
      error: !v('title') ? 'Add the job title — it is required' : ((m.querySelector('#jxDeadline') || {}).value || '9') < today() ? 'The deadline is in the past' : '' };
  }
  window.dxJobsReadPost = readPost;
  /* the approved Post buttons call submitGeneric(msg) for both forms: checked and kept here (the live app sends them to the database) */
  function wrapSubmit() {
    if (!window.submitGeneric || window.submitGeneric.__jxx) return;
    var o = window.submitGeneric;
    window.submitGeneric = function (msg) {
      var pj = document.getElementById('postJobModal'), pc = document.getElementById('postCandidateModal');
      if (pj && pj.classList.contains('show')) {
        var f = readPost(), t = pj.querySelector('[data-jxk=title]');
        if (t) t.classList.toggle('dbk-err', !f.title);
        if (f.error) { toast(f.error); return; }
        if (live()) return o.apply(this, arguments);
        return DEMO.postJob(f).then(function () { o.call(window, 'Job posted: ' + f.title + ' — now visible in Jobs and Marketplace');
          pj.querySelectorAll('input:not([disabled]),textarea').forEach(function (x) { if (x.type !== 'date' || true) x.value = ''; }); resetPage(); });
      }
      if (pc && pc.classList.contains('show')) return publishProfile(pc, o, msg);
      return o.apply(this, arguments);
    };
    window.submitGeneric.__jxx = true;
  }

  /* ── 7. Post My Profile: open to work for companies (and hide it again) ───────────────────────────────────────────── */
  function publishProfile(m, o) {
    var ins = [].slice.call(m.querySelectorAll('input.field-input')), title = ins[0] ? ins[0].value.trim() : '';
    if (!title) { if (ins[0]) ins[0].classList.add('dbk-err'); toast('Add the job title you are looking for'); return; }
    var cv = m.querySelector('#jxCvP'), file = cv && cv.files && cv.files[0], bad = cvCheck(file); if (bad) { toast(bad); return; }
    var pos = function (sel) { var all = [].slice.call(m.querySelectorAll(sel)); return all.indexOf(m.querySelector(sel + '.selected')); };
    var sels = m.querySelectorAll('select.field-select'), ta = m.querySelector('textarea');
    var f = { title: title, location: ins[1] ? ins[1].value.trim() : '', years: ins[2] ? ins[2].value.trim() : '', type: ['Full-time', 'Part-time', 'Contract', 'Remote'][pos('.radio-opt')] || 'Full-time',
              relocation: sels[0] ? txt(sels[0].options[sels[0].selectedIndex]) : '', dept: sels[1] ? sels[1].selectedIndex : 0, skills: [].map.call(m.querySelectorAll('.chip.selected'), txt),
              about: ta ? ta.value.trim() : '', cv: file || null };
    return S().publishProfile(f).then(function () {
      if (window.closeModal) window.closeModal('postCandidateModal');
      toast('Your profile is now visible to companies' + (live() ? '' : ' in Available Candidates'));
      if (cv) cv.value = ''; paintProfileBar(); resetPage();
    }, err);
  }
  function paintProfileBar() {
    var root = jx(), bar = root && root.querySelector('.jx-otw'); if (!bar) return;
    S().profileState().then(function (p) {
      bar.hidden = !(p && p.open);
      if (p && p.open) bar.innerHTML = '<span>✅ Your profile is visible to companies' + (p.title ? ' as <b>' + esc(p.title) + '</b>' : '') + '.</span><button type="button" class="jx-tool" data-jx="editprofile">✏️ Edit</button><button type="button" class="jx-tool jx-warn" data-jx="hideprofile">Hide my profile</button>';
    }, function () {});
  }
  /* demo: my published profile at the top of Available Candidates (the approved first candidate card is the template) */
  function paintMyCandidate() {
    if (live()) return; var root = jx(); if (!root) return;
    root.querySelectorAll('.jcard[data-jx-me]').forEach(function (x) { x.remove(); });
    var p = dstore('jxMyProfile', {}); if (!p.open) return;
    var tpl = [].filter.call(root.querySelectorAll('.jcard'), function (c) { return c.querySelector('.role-badge.need'); })[0]; if (!tpl) return;
    var c = tpl.cloneNode(true), me = window.ME || {}; c.dataset.jxMe = '1'; delete c.dataset.jxIdx; c.style.display = '';
    c.querySelectorAll('.jx-trust').forEach(function (x) { x.remove(); });
    var t = c.querySelector('.jc-title'), rb = t.querySelector('.role-badge'); t.textContent = p.title; if (rb) t.insertBefore(rb, t.firstChild);
    c.querySelector('.jc-logo').textContent = D.initials(me.name);
    c.querySelector('.jc-company').innerHTML = '<span>' + esc(me.name || 'Me') + '</span> · <span>' + (FLAG[placeCountry(p.location)] || '🇪🇬') + ' ' + esc(p.location || '') + '</span>';
    c.querySelector('.jc-tags').innerHTML = '<span class="jt jt-ft">' + esc(p.type || 'Full-time') + '</span>' + (p.years ? '<span class="jt" style="background:#dcfce7;color:#15803d">' + esc(String(p.years).replace(/\D+$/, '')) + ' yrs exp</span>' : '');
    c.querySelector('.jc-desc').textContent = p.about || '';
    c.querySelector('.jc-posted').textContent = 'just now';
    var b = c.querySelector('.apply-btn'); if (b) b.remove(); var s = c.querySelector('.save-btn'); if (s) s.remove();
    tpl.parentElement.insertBefore(c, tpl);
  }

  /* ── 8. Saved page: Posts · Jobs ──────────────────────────────────────────────────────────────────────────────────── */
  var SAVED_TAB = 'posts';
  function savedTabs() {
    var c = document.getElementById('content'), host = c && c.querySelector('.saved-list'); if (!host || host.querySelector('.jx-stabs')) return;
    var bar = document.createElement('div'); bar.className = 'jx-stabs'; bar.setAttribute('role', 'tablist');
    bar.innerHTML = '<button type="button" role="tab" class="cf-tag" data-st="posts">📝 Posts</button><button type="button" role="tab" class="cf-tag" data-st="jobs">💼 Jobs</button>';
    var h1 = host.querySelector('h1'); host.insertBefore(bar, h1 ? h1.nextSibling : host.firstChild);
    var box = document.createElement('div'); box.className = 'jx-sjobs'; host.appendChild(box);
    bar.addEventListener('click', function (e) { var b = e.target.closest('[data-st]'); if (b) { SAVED_TAB = b.dataset.st; paintSaved(); } });
    paintSaved();
  }
  function paintSaved() {
    var c = document.getElementById('content'), host = c && c.querySelector('.saved-list'); if (!host) return;
    var jobs = SAVED_TAB === 'jobs', box = host.querySelector('.jx-sjobs');
    host.querySelectorAll('.jx-stabs [data-st]').forEach(function (b) { b.classList.toggle('on', b.dataset.st === SAVED_TAB); b.setAttribute('aria-selected', b.dataset.st === SAVED_TAB); });
    [].forEach.call(host.children, function (ch) { if (ch.tagName === 'H1' || ch.classList.contains('jx-stabs') || ch === box) return; ch.style.display = jobs ? 'none' : ''; });
    var h1 = host.querySelector('h1'); if (h1) h1.textContent = jobs ? '🔖 Saved Jobs' : '🔖 Saved Posts';
    if (!box) return; box.hidden = !jobs; if (!jobs) return;
    box.innerHTML = '<div class="jx-loading">Loading…</div>';
    S().savedJobs().then(function (rows) {
      var jt = host.querySelector('.jx-stabs [data-st=jobs]'); if (jt) jt.textContent = '💼 Jobs (' + rows.length + ')';
      box.innerHTML = rows.length ? rows.map(function (j) {
        return '<div class="card jx-saved" data-key="' + esc(j.key || j.id) + '"><div class="jx-pb"><div class="jx-pt"><span class="jx-ptt" data-noi18n dir="auto">' + esc(j.title) + '</span>' + (j.active === false ? ' <span class="jx-st jx-st-closed">Closed</span>' : '') + '</div>' +
          '<div class="jx-pm">' + uc(j.company) + ' · ' + (FLAG[j.country] || '') + ' ' + uc(j.location) + ' · ' + (j.deadline ? '<span>Apply by</span> ' + esc(day(j.deadline)) : '<span>Open until filled</span>') + '</div></div>' +
          '<div class="jx-pa"><button type="button" class="jx-tool" data-jx="sopen">Open</button><button type="button" class="jx-tool jx-warn" data-jx="sremove">Remove</button></div></div>';
      }).join('') : '<div class="jx-none"><b>No saved jobs yet</b><p>Tap 🔖 Save on a job to find it here.</p></div>';
    }, err);
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.jx-saved [data-jx]'); if (!b) return;
    var row = b.closest('.jx-saved'), key = row.dataset.key;
    if (b.dataset.jx === 'sopen') detailModal(live() ? +key : key);
    else if (b.dataset.jx === 'sremove') { (live() ? window.dxJobs.toggleSave(+key, false) : DEMO.unsave(key)).then(function () { row.remove(); if (!live()) toast('Removed from saved jobs'); paintSaved(); }, err); }
  });

  /* ── 9. job alerts: a saved search ────────────────────────────────────────────────────────────────────────────────── */
  function describe(a) {
    var parts = []; if (a.q) parts.push('“' + a.q + '”'); if (a.category) parts.push({ regulatory: 'Regulatory', qaqc: 'QA/QC', production: 'Production', sales: 'Sales & Marketing', rd: 'R&D / Formulation' }[a.category] || a.category);
    (a.types || []).forEach(function (t) { parts.push(t.replace(/^./, function (c) { return c.toUpperCase(); })); }); (a.countries || []).forEach(function (c) { parts.push(CNAME[c] || c); });
    if (a.level) parts.push((LEVELS[a.level] || '').replace(/^\S+\s/, '')); return parts.length ? parts.join(' · ') : 'Every new job';
  }
  function saveAlert() {
    var a = { q: F.q.toLowerCase(), category: F.cat === 'all' ? null : F.cat, types: F.types.slice(), countries: F.countries.slice(), level: F.lvl === 'all' ? null : F.lvl };
    D.modal({ title: '🔔 Save this search', body: '<div class="dbk-note">We notify you when a new job matches:</div><p style="font:700 14px Inter,sans-serif;margin:10px 0">' + esc(describe(a)) + '</p><div class="jx-legal">At most 10 job alerts a day. Manage them under 🔔 Job alerts.</div>',
      primary: { label: 'Save alert', onClick: function () { S().saveAlert(a).then(function () { toast('Job alert saved — we will notify you of new matching jobs'); }, err); } } });
  }
  function alertsModal() {
    S().alerts().then(function (l) {
      var m = D.modal({ title: '🔔 Job alerts', secondary: 'Close', body: l.length ? l.map(function (a) { return '<div class="jx-row"><div class="nm"><b>' + esc(describe(a)) + '</b><small>since ' + esc(day(a.created_at)) + '</small></div><button type="button" class="dbk-btn s" data-del="' + esc(a.id) + '">Delete</button></div>'; }).join('')
        : '<div style="padding:14px 0;color:#64748b">No job alerts yet. Search or filter the jobs, then tap “🔔 Save this search”.</div>' });
      m.el.addEventListener('click', function (e) { var d = e.target.closest('[data-del]'); if (!d) return; S().deleteAlert(isNaN(+d.dataset.del) ? d.dataset.del : +d.dataset.del).then(function () { d.closest('.jx-row').remove(); toast('Job alert deleted'); }, err); });
    }, err);
  }

  /* ── one click handler for the controls above ─────────────────────────────────────────────────────────────────────── */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#jx [data-jx]'); if (!b) return;
    var k = b.dataset.jx, row = b.closest('.jx-pcard');
    if (k === 'apps') openApps(); else if (k === 'myjobs' || k === 'applicants') openJobsPanel();
    else if (k === 'alerts') alertsModal(); else if (k === 'alert') saveAlert();
    else if (k === 'back') { showPanel(false); after(); }
    else if (k === 'clear') clearFilters();
    else if (k === 'post') { showPanel(false); if (window.openPostJobModal) window.openPostJobModal(); }
    else if (k === 'editprofile') { if (window.openPostCandidateModal) window.openPostCandidateModal(); }
    else if (k === 'hideprofile') S().hideProfile().then(function () { toast('Your profile is hidden from companies'); paintProfileBar(); resetPage(); }, err);
    else if (k === 'view' && row) detailModal(live() ? +row.dataset.key : row.dataset.key);
    else if (k === 'withdraw' && row) {
      var key = row.dataset.key, title = txt(row.querySelector('.jx-pt'));
      D.modal({ title: 'Withdraw your application?', body: '<div class="dbk-note">' + esc(title) + ' — the employer no longer sees it and your CV is no longer shared. You can apply again while the job is open.</div>',
        primary: { label: 'Withdraw', danger: true, onClick: function () { S().withdraw(live() ? +key : key).then(function () {
          var st = row.querySelector('.jx-st'); if (st) { st.className = 'jx-st jx-st-withdrawn'; st.textContent = 'Withdrawn'; } var w = row.querySelector('[data-jx=withdraw]'); if (w) w.remove();
          toast('Application withdrawn'); setTimeout(function () { if (row.isConnected) row.remove(); }, 1500); resetPage(); }, err); } } });
    }
    else if (row && row.classList.contains('jx-job')) {
      var id = row.dataset.id; if (live()) id = +id;
      if (k === 'toggle') { var box = panel().querySelector('.jx-apps[data-for="' + CSS.escape(String(row.dataset.id)) + '"]'); if (box && !box.hidden && box.innerHTML) box.hidden = true; else loadApplicants(id); }
      else if (k === 'edit') editJob(id);
      else if (k === 'close' || k === 'reopen') S().setOpen(id, k === 'reopen').then(function () { toast(k === 'close' ? 'Job closed — it no longer appears in search' : 'Job reopened'); refreshJob(id); resetPage(); }, err);
      else if (k === 'delete') D.modal({ title: 'Delete this job?', body: '<div class="dbk-note">' + esc(txt(row.querySelector('.jx-ptt'))) + ' and its applications are removed for good.</div>',
        primary: { label: 'Delete', danger: true, onClick: function () { S().deleteJob(id).then(function () { toast('Job deleted'); var a = row.nextElementSibling; if (a && a.classList.contains('jx-apps')) a.remove(); row.remove(); resetPage(); }, err); } } });
    }
    else if (row && row.classList.contains('jx-app')) {
      var jobRowEl = row.closest('.jx-apps'), jid = jobRowEl ? jobRowEl.dataset.for : null, who = row.dataset.who, name = txt(row.querySelector('.jx-who'));
      if (live()) jid = +jid;
      viewed(jid, who, row);
      if (k === 'st') setStatus(jid, who, b.dataset.s, name);
      else if (k === 'cv') S().openCv(jid, who).catch(err);
      else if (k === 'msg') S().message(jid, who);
      else if (k === 'profile') S().profile(jid, who);
    }
  });
  /* phones and keyboards: Load more */
  document.addEventListener('click', function (e) { var m = e.target.closest && e.target.closest('#jx .jx-more'); if (!m) return; m.disabled = true; m.textContent = 'Loading…'; run(true); });
  /* a job card's title opens its details */
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#jx .jcard .jc-title, #jx .jcard .jc-desc'); if (!t) return;
    var card = t.closest('.jcard'); if (!isJob(card)) return;
    detailModal(live() ? +String(card.dataset.live || '').slice(1) : (card.dataset.jxPosted || titleOf(card)));
  });
  /* demo: Save on a job card keeps the saved list (the Saved page reads it) */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#jx .jcard .save-btn'); if (!b || live()) return;
    var card = b.closest('.jcard'); if (!isJob(card)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    toggleSave(card.dataset.jxPosted || titleOf(card));
  }, true);
  /* switching I'm Hiring / I'm Job Hunting closes a panel */
  document.addEventListener('click', function (e) { if (e.target.closest && e.target.closest('#jx .mode-opt') && P.kind) showPanel(false); }, true);

  function resetPage() { paintPosted(); paintDemoState(); paintMyCandidate(); paintApplied(); run(); }

  /* the page renders once and is kept: everything above is (re)applied on each visit */
  var oRender = window.renderJobs;
  if (typeof oRender === 'function') window.renderJobs = function () {
    var first = !window.__jxNode, r = oRender.apply(this, arguments);
    try { decorate(); wrapSubmit(); postForm(); cvInput('postCandidateModal', 'jxCvP'); tools(); showPanel(false); paintProfileBar(); if (!live()) resetPage(); else after(); } catch (e) { if (window.console) console.warn('jobs:', e); }
    return r;
  };
  C.onRender('jobs-x', function () { if (document.body.getAttribute('data-page') === 'jobs') { tools(); } });

  /* the Saved page gets its Jobs tab */
  var oSaved = window.renderSaved;
  if (typeof oSaved === 'function') window.renderSaved = function () { var r = oSaved.apply(this, arguments); try { savedTabs(); } catch (e) { if (window.console) console.warn('saved jobs:', e); } return r; };


  /* Arabic for everything above (the interface translates as it draws; what people wrote stays as written) */
  if (window.dxI18nExtend) window.dxI18nExtend({
    'Search jobs: title, company, skill…': 'ابحث في الوظائف: المسمى أو الشركة أو المهارة…', 'Search jobs': 'ابحث في الوظائف', '🔔 Save this search': '🔔 احفظ هذا البحث',
    '✕ Clear filters': '✕ امسح الفلاتر', '⚙ Filters': '⚙ الفلاتر', '✕ Close filters': '✕ أغلق الفلاتر', '📄 My applications': '📄 طلباتي', '🔔 Job alerts': '🔔 تنبيهات الوظائف',
    '💼 My jobs': '💼 وظائفي', '👥 Applicants': '👥 المتقدمون', '← Back to jobs': '→ العودة إلى الوظائف', 'Load more jobs': 'تحميل المزيد من الوظائف',
    'Try other words, or clear the filters.': 'جرّب كلمات أخرى أو امسح الفلاتر.', 'View job': 'عرض الوظيفة', 'Open job': 'افتح الوظيفة', '✏️ Edit': '✏️ تعديل', 'Close job': 'إغلاق الوظيفة',
    '↺ Reopen': '↺ إعادة فتح', '🗑 Delete': '🗑 حذف', '📄 CV': '📄 السيرة الذاتية', '💬 Message': '💬 رسالة', '⭐ Shortlist': '⭐ القائمة المختصرة', '📅 Interview': '📅 مقابلة',
    '✅ Hire': '✅ تعيين', '✕ Reject': '✕ رفض', 'No-show': 'لم يحضر', 'Submitted': 'مقدم', 'Viewed': 'تمت مشاهدته', 'Shortlisted': 'في القائمة المختصرة', 'Interview': 'مقابلة',
    'Hired': 'تم التعيين', 'Rejected': 'مرفوض', 'Withdrawn': 'مسحوب', 'Expired': 'منتهية', 'Accepting applications': 'تستقبل الطلبات', '⭐ Preferred': '⭐ مفضّل',
    'Location': 'الموقع', 'Type': 'النوع', 'Level': 'المستوى', 'Salary': 'الراتب', 'Apply by': 'آخر موعد للتقدم', 'Posted': 'تاريخ النشر', 'Description': 'الوصف',
    'Requirements': 'المتطلبات', 'Benefits': 'المزايا', 'Not shown': 'غير معلن', 'Open until filled': 'مفتوحة حتى شغلها', 'Not listed by the employer.': 'لم يذكرها صاحب العمل.',
    'This job is closed — it no longer takes applications.': 'هذه الوظيفة مغلقة — لم تعد تستقبل طلبات.', '✓ Verified': '✓ موثّق',
    'Application deadline': 'آخر موعد للتقدم', 'Requirements (one per line)': 'المتطلبات (سطر لكل بند)', 'Benefits (one per line)': 'المزايا (سطر لكل بند)',
    'Job title *': 'المسمى الوظيفي *', 'Deadline': 'آخر موعد', 'Save changes': 'حفظ التغييرات', '📄 My applications ': '📄 طلباتي', '💼 My jobs and applicants': '💼 وظائفي والمتقدمون',
    'No applications yet': 'لا توجد طلبات بعد', 'Apply to a job and follow it here.': 'قدّم على وظيفة وتابعها هنا.', 'You have not posted a job yet': 'لم تنشر أي وظيفة بعد',
    'Post a job and the people who apply show here.': 'انشر وظيفة وسيظهر هنا من يتقدم لها.', '➕ Post a Job': '➕ انشر وظيفة', 'No applications yet.': 'لا توجد طلبات بعد.',
    'Loading applicants…': 'جارٍ تحميل المتقدمين…', 'Interview date *': 'تاريخ المقابلة *', 'Message to the candidate (optional)': 'رسالة إلى المرشح (اختيارية)',
    'Place, time and who they will meet': 'المكان والوقت ومن سيقابل', 'Confirm': 'تأكيد', 'Note to the candidate (optional)': 'ملاحظة إلى المرشح (اختيارية)',
    'Close this job now (it stops taking applications)': 'أغلق الوظيفة الآن (تتوقف عن استقبال الطلبات)', 'Hide my profile': 'إخفاء ملفي', '✏️ Edit ': '✏️ تعديل',
    '📝 Posts': '📝 المنشورات', '💼 Jobs': '💼 الوظائف', '🔖 Saved Jobs': '🔖 الوظائف المحفوظة', 'No saved jobs yet': 'لا توجد وظائف محفوظة بعد',
    'Tap 🔖 Save on a job to find it here.': 'اضغط 🔖 حفظ على أي وظيفة لتجدها هنا.', 'We notify you when a new job matches:': 'سنبلغك عندما تُنشر وظيفة جديدة مطابقة:',
    'At most 10 job alerts a day. Manage them under 🔔 Job alerts.': '10 تنبيهات وظائف يوميًا على الأكثر. أدِرها من 🔔 تنبيهات الوظائف.', 'Save alert': 'احفظ التنبيه',
    'Every new job': 'كل وظيفة جديدة', 'No job alerts yet. Search or filter the jobs, then tap “🔔 Save this search”.': 'لا توجد تنبيهات بعد. ابحث أو فلتر الوظائف ثم اضغط «🔔 احفظ هذا البحث».',
    'Withdraw your application?': 'سحب طلبك؟', 'Delete this job?': 'حذف هذه الوظيفة؟', 'Job closed — it no longer appears in search': 'تم إغلاق الوظيفة — لم تعد تظهر في البحث',
    'Job reopened': 'أعيد فتح الوظيفة', 'Job deleted': 'تم حذف الوظيفة', 'Application withdrawn': 'تم سحب الطلب', 'Job updated — job seekers see the change': 'تم تحديث الوظيفة — يراها الباحثون عن عمل',
    'Add the job title — it is required': 'أضف المسمى الوظيفي — هذا الحقل مطلوب', 'The deadline is in the past': 'آخر موعد في الماضي',
    'The CV must be a PDF or Word file': 'يجب أن تكون السيرة الذاتية ملف PDF أو Word', 'The CV is too large — at most 10 MB': 'السيرة الذاتية كبيرة جدًا — 10 ميجابايت على الأكثر',
    'You already applied to this job': 'لقد تقدمت لهذه الوظيفة بالفعل', 'Add the job title you are looking for': 'أضف المسمى الوظيفي الذي تبحث عنه',
    'Your profile is now visible to companies': 'ملفك ظاهر الآن للشركات', 'Your profile is now visible to companies in Available Candidates': 'ملفك ظاهر الآن للشركات في المرشحين المتاحين',
    'Your profile is hidden from companies': 'ملفك مخفي الآن عن الشركات', 'Job alert saved — we will notify you of new matching jobs': 'تم حفظ التنبيه — سنبلغك بالوظائف الجديدة المطابقة',
    'Job alert deleted': 'تم حذف التنبيه', 'Removed from saved jobs': 'أزيلت من الوظائف المحفوظة', 'Saved — find it on your Saved page': 'تم الحفظ — تجدها في صفحة المحفوظات',
    'Job saved': 'تم حفظ الوظيفة', 'Something went wrong — please try again': 'حدث خطأ — حاول مرة أخرى', 'This job is no longer available': 'هذه الوظيفة لم تعد متاحة',
    'Search jobs: title, company, skill...': 'ابحث في الوظائف',
    /* the same labels when a layer shows their emoji as an icon */
    'My applications': 'طلباتي', 'Job alerts': 'تنبيهات الوظائف', 'My jobs': 'وظائفي', 'Applicants': 'المتقدمون', 'My jobs and applicants': 'وظائفي والمتقدمون', 'Saved Jobs': 'الوظائف المحفوظة',
    'CV': 'السيرة الذاتية', 'Save this search': 'احفظ هذا البحث', 'Back to jobs': 'العودة إلى الوظائف', 'Filters': 'الفلاتر', 'Close filters': 'أغلق الفلاتر', 'Posts': 'المنشورات',
    'PDF or Word document': 'ملف PDF أو Word', 'Applied': 'تقدمت في', 'applied': 'تقدّم في', 'since': 'منذ', 'Apply by': 'آخر موعد للتقدم', 'Shortlist': 'القائمة المختصرة', 'Hire': 'تعيين', 'Reject': 'رفض',
    'Egypt': 'مصر', 'UAE': 'الإمارات', 'Saudi Arabia': 'السعودية', 'Kuwait': 'الكويت', 'Qatar': 'قطر', 'Bahrain': 'البحرين', 'Oman': 'عُمان', 'Jordan': 'الأردن', 'India': 'الهند', 'Lebanon': 'لبنان', 'Iraq': 'العراق',
    'Morocco': 'المغرب', 'Algeria': 'الجزائر', 'Tunisia': 'تونس', 'Libya': 'ليبيا', 'Sudan': 'السودان', 'China': 'الصين',
    'A preferred candidate applied — added to your shortlist': 'تقدّم مرشح مفضّل — أضيف إلى قائمتك المختصرة',
    'This candidate has not shared a CV — contact them to ask for one': 'لم يشارك هذا المرشح سيرة ذاتية — تواصل معه لطلبها', 'Sample CVs open in the live app — a private link that expires': 'السير الذاتية التجريبية تُفتح في التطبيق الفعلي — رابط خاص ينتهي'
  }, [
    [/^Applicants \((\d+)\)$/, function (m) { return 'المتقدمون (' + m[1] + ')'; }], [/^Jobs \((\d+)\)$/, function (m) { return 'الوظائف (' + m[1] + ')'; }],
    /* job notices (0060) — the reader's own words, the job title as written */
    [/^shortlisted your application for (.+)$/, function (m) { return 'أضاف طلبك للقائمة المختصرة لوظيفة ' + m[1]; }],
    [/^invited you to an interview for (.+?)(?: on (.+))?$/, function (m) { return 'دعاك لمقابلة لوظيفة ' + m[1] + (m[2] ? ' يوم ' + m[2] : ''); }],
    [/^hired you for (.+) — congratulations!$/, function (m) { return 'اختارك لوظيفة ' + m[1] + ' — مبروك!'; }],
    [/^thanks you for applying to (.+) — they went ahead with other candidates this time$/, function (m) { return 'يشكرك على التقدم لوظيفة ' + m[1] + ' — تم اختيار مرشحين آخرين هذه المرة'; }],
    [/^marked your interview for (.+) as missed$/, function (m) { return 'سجّل أنك لم تحضر مقابلة وظيفة ' + m[1]; }],
    [/^updated your application for (.+)$/, function (m) { return 'حدّث طلبك لوظيفة ' + m[1]; }],
    [/^New job matching your alert: (.+)$/, function (m) { return 'وظيفة جديدة تطابق تنبيهك: ' + m[1]; }],
    [/^applied to (.+)$/, function (m) { return 'تقدم لوظيفة ' + m[1]; }],
    [/^since (.+)$/, function (m) { return 'منذ ' + m[1]; }], [/^applied (?!to )(.+)$/i, function (m) { return 'تقدّم في ' + m[1]; }],
    [/^Applied (\d.+)$/, function (m) { return 'تقدمت في ' + m[1]; }], [/^Apply by (.+)$/, function (m) { return 'آخر موعد ' + m[1]; }],
    [/^👥 Applicants \((\d+)\)$/, function (m) { return '👥 المتقدمون (' + m[1] + ')'; }], [/^💼 Jobs \((\d+)\)$/, function (m) { return '💼 الوظائف (' + m[1] + ')'; }],
    [/^(\d+) applicants?$/, function (m) { return m[1] + ' متقدم'; }], [/^📅 Interview (.+)$/, function (m) { return '📅 مقابلة ' + m[1]; }],
    [/^✅ Your profile is visible to companies( as)?\.?$/, function (m) { return '✅ ملفك ظاهر للشركات' + (m[1] ? ' باسم' : '.'); }],
    [/^Interview with (.+)$/, function (m) { return 'مقابلة مع ' + m[1]; }], [/^Not selected: (.+)$/, function (m) { return 'لم يتم الاختيار: ' + m[1]; }],
    [/^Hire (.+)\?$/, function (m) { return 'تعيين ' + m[1] + '؟'; }], [/^Edit: (.+)$/, function (m) { return 'تعديل: ' + m[1]; }],
    [/^(.+) is told politely that you went ahead with other candidates\.$/, function (m) { return 'سيتم إبلاغ ' + m[1] + ' بلطف أنك اخترت مرشحين آخرين.'; }],
    [/^(.+) is told the good news\. You can both review each other afterwards\.$/, function (m) { return 'سيتم إبلاغ ' + m[1] + ' بالخبر السار. يمكنكما تقييم بعضكما بعد ذلك.'; }],
    [/^(.+) — the employer no longer sees it and your CV is no longer shared\. You can apply again while the job is open\.$/, function (m) { return m[1] + ' — لن يراه صاحب العمل ولن تُشارك سيرتك الذاتية. يمكنك التقديم مرة أخرى ما دامت الوظيفة مفتوحة.'; }],
    [/^(.+) and its applications are removed for good\.$/, function (m) { return 'ستُحذف ' + m[1] + ' وطلباتها نهائيًا.'; }],
    [/^Application sent for (.+) at (.+) — follow it in My applications$/, function (m) { return 'تم إرسال طلبك لوظيفة ' + m[1] + ' في ' + m[2] + ' — تابعه في طلباتي'; }],
    [/^Application sent for (.+) — follow it in My applications$/, function (m) { return 'تم إرسال طلبك لوظيفة ' + m[1] + ' — تابعه في طلباتي'; }],
    [/^Job posted: (.+) — now visible in Jobs and Marketplace$/, function (m) { return 'تم نشر الوظيفة: ' + m[1] + ' — تظهر الآن في الوظائف والسوق'; }],
    [/^(.+) — (shortlisted|invited to an interview|hired|not selected|marked as a no-show); they were notified$/, function (m) { return m[1] + ' — ' + ({ shortlisted: 'أضيف للقائمة المختصرة', 'invited to an interview': 'دُعي لمقابلة', hired: 'تم تعيينه', 'not selected': 'لم يتم اختياره', 'marked as a no-show': 'سُجّل أنه لم يحضر' })[m[2]] + '؛ تم إبلاغه'; }],
    [/^Submitted (\d+)$/, function (m) { return 'مقدم ' + m[1]; }]
  ]);
  /* a company page's Jobs section: the demo adds the jobs posted in this browser for that page (the live app answers from the database) */
  window.dxJobsOfCompany = function (co, out) {
    if (live()) return window.dxJobs.ofCompany ? window.dxJobs.ofCompany(co) : null;
    dstore('jxPosted', []).forEach(function (j) { if (j.company === co.name && j.active !== false && !out.some(function (x) { return x.t === j.title; })) out.unshift({ t: j.title, type: j.type, loc: j.location, onJobs: true }); });
    return out;
  };
  /* other parts (a notification, a saved job) open these */
  window.dxJobsUI = { detail: detailModal, applications: openApps, myJobs: openJobsPanel, run: run, after: after, reset: resetPage, savedTab: function (t) { SAVED_TAB = t; } };
})();
