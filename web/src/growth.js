/* AREA w-growth — the owner's growth plan, drawn in the approved look (EN + AR, 1440 + 390).
   1. Official Drugbox channels (W-41): News, Jobs, Regulatory, Market — group cards with the "✓ Drugbox official" badge, their posts
      read as Drugbox (never as a member); Admin → Channels: the content plan (templates), drafts, a schedule in Cairo time, edit,
      cancel, publish now. Live: published by the server's runner (growth_tick, 0100); demo: by this file while the page is open.
   2. Therapeutic areas (W-21): a filter on Home and in the Marketplace, tags on channel posts.
   3. Founding members (W-42), 4. Ask an expert (W-43), 5. Directory import (Admin), 6. signed-out company pages, 7. the six courses
      in Arabic, 8. the one-time specialty question — further down.
   Demo: sample data and what you do kept in this browser (DBK.store). Live: window.dxGrowth (web/src/live/growth.js + the
   "AREA w-growth" block of the adapter) does the same against the database; this file only draws. */
(function () {
  var D = window.DBK; if (!D || !window.dxCore) return;
  var esc = D.esc, C = window.dxCore;
  function live() { var s = window.dxGrowth; return !!(s && s.live && s.ready && s.ready()); }
  function ar() { return document.documentElement.lang === 'ar'; }
  function toast(m) { D.toast(m); }
  function errMsg(e) { return (window.dxLive && window.dxLive.friendly ? window.dxLive.friendly(e) : (e && e.message)) || 'Something went wrong — try again'; }
  function sget(k, d) { try { var v = D.store.get(k, d); return v == null ? d : v; } catch (e) { return d; } }
  function sset(k, v) { try { D.store.set(k, v); } catch (e) {} }
  function tr(s) { return window.dxI18nTr ? window.dxI18nTr(s) : s; }
  function i18n(el) { if (el && window.dxI18nAttrs) window.dxI18nAttrs(el); }
  var GW = window.dxGrowthUI = window.dxGrowthUI || {};

  /* Cairo wall time 'YYYY-MM-DD HH:MM' (the scheduler's clock in the demo; the server keeps its own) */
  function cairoNow(add) {
    var d = new Date(Date.now() + (add || 0)), p = {};
    try { new Intl.DateTimeFormat('en-CA', { timeZone: 'Africa/Cairo', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(d).forEach(function (x) { p[x.type] = x.value; }); }
    catch (e) { return d.toISOString().slice(0, 16).replace('T', ' '); }
    return p.year + '-' + p.month + '-' + p.day + ' ' + (p.hour === '24' ? '00' : p.hour) + ':' + p.minute;
  }
  GW.cairoNow = cairoNow;

  /* ═════════════ 2. therapeutic areas (the same list and dictionary as private.thera_terms, 0100) ═════════════ */
  var THERA = [['biologics', 'Biologics', '🧬'], ['veterinary', 'Veterinary', '🐄'], ['agriculture', 'Agriculture', '🌾'], ['glp1', 'GLP-1', '💉'],
               ['oncology', 'Oncology', '🎗️'], ['growth_hormone', 'Growth hormone', '📏'], ['fertility', 'Fertility', '👶'], ['insulin', 'Insulin', '🩸']];
  var TERMS = { biologics: ['biologic', 'biologics', 'biological', 'biosimilar', 'biosimilars', 'monoclonal', 'mab', 'بيولوجي', 'بيولوجية', 'بايولوجي', 'بيوسيميلر'],
    veterinary: ['veterinary', 'vet', 'poultry', 'livestock', 'بيطري', 'بيطرية', 'دواجن', 'ماشية'],
    agriculture: ['agriculture', 'agricultural', 'agro', 'pesticide', 'pesticides', 'fertilizer', 'fertilizers', 'زراعي', 'زراعية', 'مبيد', 'مبيدات', 'أسمدة', 'سماد'],
    glp1: ['glp-1', 'glp1', 'semaglutide', 'liraglutide', 'tirzepatide', 'dulaglutide', 'سيماجلوتايد', 'سيماجلوتيد', 'ليراجلوتايد'],
    oncology: ['oncology', 'oncologic', 'cancer', 'chemotherapy', 'cytotoxic', 'أورام', 'اورام', 'الأورام', 'سرطان', 'كيماوي'],
    growth_hormone: ['growth hormone', 'somatropin', 'هرمون النمو', 'هرمون نمو', 'سوماتروبين'],
    fertility: ['fertility', 'ivf', 'gonadotropin', 'gonadotrophin', 'hmg', 'fsh', 'خصوبة', 'الخصوبة', 'حقن مجهري', 'تأخر الإنجاب'],
    insulin: ['insulin', 'insulins', 'انسولين', 'إنسولين', 'الانسولين', 'الإنسولين'] };
  function theraOf(text) {
    var t = String(text || ''), low = t.toLowerCase(), out = [];
    Object.keys(TERMS).forEach(function (k) { if (TERMS[k].some(function (w) {
      if (/[a-z]/.test(w)) return new RegExp('(^|[^a-z0-9])' + w.replace(/[.\-+]/g, '\\$&') + '([^a-z0-9]|$)').test(low);
      return t.indexOf(w) >= 0; })) out.push(k); });
    return out;
  }
  function theraLabel(k) { var x = THERA.filter(function (t) { return t[0] === k; })[0]; return x ? x[2] + ' ' + x[1] : k; }
  GW.thera = THERA; GW.theraOf = theraOf; GW.theraLabel = theraLabel;
  function theraSelect(id, cur, label) {
    return '<label class="dx-th-l" for="' + id + '">' + esc(label || '🧬 Therapeutic area') + '</label><select id="' + id + '" class="dx-th-sel"><option value="">All therapeutic areas</option>' +
      THERA.map(function (t) { return '<option value="' + t[0] + '"' + (t[0] === cur ? ' selected' : '') + '>' + esc(t[2] + ' ' + t[1]) + '</option>'; }).join('') + '</select>';
  }

  /* ═════════════ 1. official channels ═════════════ */
  var CHANNELS = [
    { key: 'news', k: 'dbx-news', t: 'Drugbox News', emoji: '📰', bg: 'linear-gradient(135deg,#0a1f4d,#1a56db)', desc: 'Official Drugbox channel: industry news, Drugbox updates and the weekly practical guide.' },
    { key: 'jobs', k: 'dbx-jobs', t: 'Drugbox Jobs', emoji: '💼', bg: 'linear-gradient(135deg,#065f46,#10b981)', desc: 'Official Drugbox channel: the week’s jobs and hiring news across the industry.' },
    { key: 'regulatory', k: 'dbx-regulatory', t: 'Drugbox Regulatory', emoji: '📋', bg: 'linear-gradient(135deg,#4c1d95,#7c3aed)', desc: 'Official Drugbox channel: the weekly regulatory bulletin (EDA, NFSA) and how to read a registration-file ad.' },
    { key: 'market', k: 'dbx-market', t: 'Drugbox Market', emoji: '📈', bg: 'linear-gradient(135deg,#92400e,#f59e0b)', desc: 'Official Drugbox channel: «Wanted today» every evening, the week’s shortages and the agency market — business to business only.' }];
  GW.channels = CHANNELS;
  var DRUGBOX_UID = -41;   /* demo: the author id of a Drugbox post (no member has it) */
  /* demo sample posts of the channels (Drugbox's own, sample data of the demo) */
  var SAMPLE = {
    'dbx-market': [{ id: 941001, body: '🔎 Wanted today — business to business\n\n1. Insulin glargine 100 IU/ml pens — 20,000 pens — Cairo (distributor)\n2. Semaglutide API — 2 kg — Alexandria (manufacturer)\n3. Amber glass vials 10 ml — 200,000 — 6th of October (toll manufacturer)\n\nHave it? Answer from the Marketplace or message the buyer. Companies and their agents only — no sales to pharmacies or the public.', ts: '2h ago', cat: 'market', likes: 18, cmt: 3, views: 940 }],
    'dbx-regulatory': [{ id: 941002, body: '📋 Weekly regulatory bulletin\n\n• EDA: stability data for Zone IVb now required with every new registration file — from 1 December\n• NFSA: the new notification form for supplements opens next week\n\nSource links in the comments. Not legal advice — check the official text.', ts: '1d ago', cat: 'regulatory', likes: 31, cmt: 6, views: 1820 }],
    'dbx-news': [{ id: 941003, body: '🛠 Practical guide of the week: choosing a toll manufacturer for oncology injectables\n\n1. Ask for the cytotoxic suite’s last inspection report\n2. Check the free months on the Sites tab of its company page\n3. Ask an expert: Training → Ask an expert', ts: '3d ago', cat: 'general', likes: 22, cmt: 2, views: 760 }],
    'dbx-jobs': [{ id: 941004, body: '💼 Jobs of the week\n\n• Regulatory Affairs Specialist — Giza\n• QC Microbiologist (biologics) — 10th of Ramadan\n• Export Sales Manager (veterinary) — Cairo\n\nApply from Jobs. Hiring? Post a job for free.', ts: '4d ago', cat: 'job', likes: 12, cmt: 1, views: 610 }] };
  function samplePost(s) { return { id: s.id, uid: DRUGBOX_UID, cat: s.cat, ts: s.ts, likes: s.likes, rx: { like: s.likes }, cmt: s.cmt, sh: 0, views: s.views, body: s.body, cm: [], drugbox: true, thera: theraOf(s.body) }; }
  function planPost(x) { return { id: 950000 + (+x.id), uid: DRUGBOX_UID, cat: { regulatory: 'regulatory', market: 'market', jobs: 'job' }[x.channel] || 'general', ts: x.publishedTs || 'just now', likes: 0, rx: {}, cmt: 0, sh: 0, views: 0,
    body: x.body, cm: [], drugbox: true, thera: (x.thera || []).concat(theraOf(x.body)).filter(function (v, i, l) { return l.indexOf(v) === i; }) }; }
  var SEEDS = {};
  function seedChannels() {
    if (live() || window.dxLive || typeof window.dxGroupsSeed !== 'function') return;
    var plan = sget('gwPlan', []);
    CHANNELS.forEach(function (c) {
      var posts = plan.filter(function (x) { return x.status === 'published' && x.channel === c.key; }).sort(function (a, b) { return String(b.publishedAt).localeCompare(String(a.publishedAt)); }).map(planPost)
        .concat((SAMPLE[c.k] || []).map(samplePost));
      var sd = { k: c.k, t: c.t, official: true, by: null, since: '2026-10-01', focus: [], markets: 'Egypt · Arab region', about: c.desc,
        rules: [['Drugbox speaks here', 'Only Drugbox posts in its channels. Members comment and react.'], ['Business to business', 'Offers and requests are between companies and their agents — never sales to pharmacies or the public.']],
        mem: [], posts: posts, card: { emoji: c.emoji, bg: c.bg, desc: c.desc, count: 0, faces: [], signal: '✓ Drugbox official channel', joined: false, priv: false, grid: 1 } };
      SEEDS[c.k] = sd; window.dxGroupsSeed(sd);
    });
  }
  /* seeded on the first visit to Groups (the live build's adapter loads after this file: only then is it known whether this is the demo) */
  var gotoS = window.goto;
  window.goto = function (p) { if (p === 'groups' && !SEEDS.__done) { SEEDS.__done = 1; seedChannels(); } return gotoS.apply(this, arguments); };
  /* the card: the official badge (the approved priority-badge slot) */
  function badgeCards() {
    document.querySelectorAll('#gx .gcard[data-official="1"]').forEach(function (c) {
      if (c.querySelector('.dx-off-badge')) return;
      var b = document.createElement('div'); b.className = 'priority-badge dx-off-badge'; b.textContent = '✓ Drugbox official'; c.insertBefore(b, c.firstChild);
      var meta = c.querySelector('.gcard-meta'); if (meta && !meta.querySelector('.gtag-official')) meta.insertAdjacentHTML('afterbegin', '<span class="gtag gtag-official">OFFICIAL</span>');
      i18n(c);
    });
  }
  /* a Drugbox post: Drugbox's name, logo and badge instead of a person; no profile link, no "1st/2nd" */
  window.dxPostDecor = function (el, p) {
    if (!el || !p || !p.drugbox) return;
    el.classList.add('dx-dbx-post');
    var av = el.querySelector('.post-av'); if (av) { av.removeAttribute('onclick'); av.removeAttribute('data-gp'); av.removeAttribute('title'); var lg = typeof LOGO_ICON !== 'undefined' ? LOGO_ICON : ''; av.innerHTML = lg ? '<img src="' + esc(lg) + '" alt="Drugbox" style="width:100%;height:100%;object-fit:contain;background:#fff">' : 'DB';   /* the approved page's own logo (a global const) */
      var deg = av.parentNode && av.parentNode.querySelector('span'); if (deg) deg.remove(); }
    var nm = el.querySelector('.post-name'); if (nm) { nm.removeAttribute('onclick'); nm.removeAttribute('data-gp2'); nm.style.cursor = 'default'; nm.innerHTML = '<span data-noi18n>Drugbox</span> <span class="dx-off-chip">✓ Official</span>'; }
    var sub = el.querySelector('.post-sub'); if (sub) sub.textContent = 'Official Drugbox channel';
    el.querySelectorAll('[id^="pm-"] .ctx-item').forEach(function (x) { if (/✏️|Edit/.test(x.textContent)) x.remove(); });
    var tags = (p.thera || []).filter(function (k) { return THERA.some(function (t) { return t[0] === k; }); });
    var body = el.querySelector('.post-body'); if (body && tags.length && !el.querySelector('.dx-th-tags')) body.insertAdjacentHTML('afterend', '<div class="dx-th-tags">' + tags.map(function (k) { return '<span class="dx-th-tag">' + esc(theraLabel(k)) + '</span>'; }).join('') + '</div>');
    i18n(el);
  };
  C.onRender('w-growth', function () {   /* runs after every redraw: each step returns at once when it has nothing to do */
    var page = document.body.getAttribute('data-page');
    if (page === 'groups') { if (document.querySelector('#gx .gcard[data-official="1"]:not(:has(.dx-off-badge))')) badgeCards(); }
    else if (page === 'feed') feedBar();
    else if (page === 'market') marketBar();
    else if (page === 'admin') adminNav();
  });

  /* demo runner: a scheduled post is published when its Cairo time comes (the live app: the server's growth_tick) */
  function demoTick() {
    if (live() || window.dxLive) return;
    var plan = sget('gwPlan', []), now = cairoNow(), n = 0;
    plan.forEach(function (x) { if (x.status === 'scheduled' && x.local && x.local <= now) { x.status = 'published'; x.publishedAt = new Date().toISOString(); n++;
      var c = CHANNELS.filter(function (y) { return y.key === x.channel; })[0], sd = c && SEEDS[c.k]; if (sd) sd.posts.unshift(planPost(x)); } });
    if (n) { sset('gwPlan', plan); if (document.body.getAttribute('data-page') === 'admin' && window.adminTab === 'channels') channelsPage(content()); }
  }
  setInterval(demoTick, 5000); setTimeout(demoTick, 800);

  /* ═════════════ Admin → Channels: the content plan, drafts, schedule, publish ═════════════ */
  var TPL = [
    { key: 'wanted_today', channel_key: 'market', cadence: 'daily', weekday: null, at_time: '21:00', title_en: 'Wanted today', title_ar: 'مطلوب النهارده',
      body_en: '🔎 Wanted today — business to business\n\n1. <product / API> — <quantity> — <city>\n2. …\n\nHave it? Answer from the Marketplace (Create Listing → Supply) or message the buyer. Companies and their agents only — no sales to pharmacies or the public.',
      body_ar: '🔎 مطلوب النهارده — تجارة بين الشركات\n\n1. <المنتج / المادة الخام> — <الكمية> — <المدينة>\n2. …\n\nعندك؟ رد من الماركت (إعلان جديد ← عرض) أو ابعت للمشتري. للشركات ووكلائها فقط — مفيش بيع لصيدليات أو للجمهور.' },
    { key: 'shortages_week', channel_key: 'market', cadence: 'weekly', weekday: 4, at_time: '21:30', title_en: 'This week’s shortages', title_ar: 'نواقص الأسبوع',
      body_en: '📉 This week’s shortages (from requests on Drugbox)\n\n• <product> — <form / strength> — asked by <n> companies\n• …\n\nSuppliers and agents: post your offer in the Marketplace.',
      body_ar: '📉 نواقص الأسبوع (من طلبات Drugbox)\n\n• <المنتج> — <الشكل / التركيز> — طلبته <عدد> شركات\n• …\n\nالموردين والوكلاء: انشروا عرضكم في الماركت.' },
    { key: 'regulatory_bulletin', channel_key: 'regulatory', cadence: 'weekly', weekday: 0, at_time: '21:00', title_en: 'Weekly regulatory bulletin', title_ar: 'النشرة التنظيمية الأسبوعية',
      body_en: '📋 Weekly regulatory bulletin\n\n• EDA: <decree / circular — number — what changes — from when>\n• NFSA: <…>\n• Pricing: <…>\n\nSource links in the comments. Not legal advice — check the official text.',
      body_ar: '📋 النشرة التنظيمية الأسبوعية\n\n• هيئة الدواء: <قرار / منشور — الرقم — إيه اللي اتغير — من إمتى>\n• هيئة سلامة الغذاء: <…>\n• التسعير: <…>\n\nروابط المصدر في التعليقات. مش استشارة قانونية — راجع النص الرسمي.' },
    { key: 'read_file_ad', channel_key: 'regulatory', cadence: 'weekly', weekday: 1, at_time: '21:00', title_en: 'How to read a registration-file ad', title_ar: 'إزاي تقرا إعلان ملف تسجيل',
      body_en: '🧾 How to read a registration-file ad\n\n1. Registration number and holder — check them on the authority’s site.\n2. Status: registered / under registration / box.\n3. Expiry and renewals.\n4. Price and who pays the transfer fees.\n5. Never pay before the transfer papers are checked.',
      body_ar: '🧾 إزاي تقرا إعلان ملف تسجيل\n\n1. رقم التسجيل وصاحب الملف — اتأكد منهم على موقع الهيئة.\n2. الحالة: مسجّل / تحت التسجيل / بوكس.\n3. تاريخ الانتهاء والتجديدات.\n4. السعر ومين بيدفع رسوم نقل الملكية.\n5. ماتدفعش قبل ما أوراق النقل تتراجع.' },
    { key: 'agency_market', channel_key: 'market', cadence: 'weekly', weekday: 2, at_time: '21:00', title_en: 'The agency market this week', title_ar: 'سوق الوكالات الأسبوع ده',
      body_en: '🤝 The agency market this week\n\n• Principals looking for agents / distributors: <…>\n• Agents looking for lines: <…>\n\nPost yours in the Marketplace (License / Service).',
      body_ar: '🤝 سوق الوكالات الأسبوع ده\n\n• شركات بتدور على وكيل / موزّع: <…>\n• وكلاء بيدوروا على خطوط: <…>\n\nانشر طلبك في الماركت (ترخيص / خدمة).' },
    { key: 'practical_guide', channel_key: 'news', cadence: 'weekly', weekday: 3, at_time: '21:00', title_en: 'Practical guide of the week', title_ar: 'الدليل العملي للأسبوع',
      body_en: '🛠 Practical guide of the week: <topic>\n\n1. …\n2. …\n3. …\n\nAsk the expert: Training → Ask an expert.', body_ar: '🛠 الدليل العملي للأسبوع: <الموضوع>\n\n1. …\n2. …\n3. …\n\nاسأل خبير: التدريب ← اسأل خبير.' },
    { key: 'jobs_week', channel_key: 'jobs', cadence: 'weekly', weekday: 0, at_time: '20:00', title_en: 'Jobs of the week', title_ar: 'وظائف الأسبوع',
      body_en: '💼 Jobs of the week\n\n• <title> — <company> — <city>\n• …\n\nApply from Jobs. Hiring? Post a job for free.', body_ar: '💼 وظائف الأسبوع\n\n• <المسمى> — <الشركة> — <المدينة>\n• …\n\nقدّم من الوظائف. بتعيّن؟ انشر وظيفة مجاناً.' }];
  function nextSlot(t) {   /* demo: the template's next Cairo slot, never within 5 minutes */
    var now = cairoNow(5 * 60000), d0 = new Date(now.slice(0, 10) + 'T00:00:00Z');
    for (var i = 0; i < 15; i++) { var d = new Date(d0.getTime() + i * 86400000), ds = d.toISOString().slice(0, 10), c = ds + ' ' + String(t.at_time).slice(0, 5);
      if (c > now && (t.cadence === 'daily' || d.getUTCDay() === t.weekday)) return c; }
    return null;
  }
  var DEMO_CH = {
    templates: function () { return Promise.resolve(TPL); },
    next: function (key) { var t = TPL.filter(function (x) { return x.key === key; })[0]; return Promise.resolve(t ? nextSlot(t) : null); },
    list: function () { var who = (window.ME && ME.name) || 'You';
      return Promise.resolve(sget('gwPlan', []).map(function (x) { var c = CHANNELS.filter(function (y) { return y.key === x.channel; })[0] || {};
        return { id: x.id, channel_key: x.channel, channel_name: c.t, template_key: x.template, body: x.body, thera: x.thera || [], status: x.status, publish_local: x.local || null, created_by_name: who, published_at: x.publishedAt || null }; })
        .sort(function (a, b) { var o = function (s) { return s === 'draft' || s === 'scheduled' ? 0 : 1; }; return o(a.status) - o(b.status) || String(a.publish_local || '').localeCompare(String(b.publish_local || '')) || b.id - a.id; })); },
    save: function (o) {
      var b = String(o.body || '').trim(); if (!b) return Promise.reject(new Error('Write the post first')); if (b.length > 5000) return Promise.reject(new Error('A post is at most 5,000 characters'));
      if (o.status === 'scheduled' && !o.local) return Promise.reject(new Error('Pick the date and time to publish (Cairo time)'));
      if (o.local && !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(o.local)) return Promise.reject(new Error('Give the date and time as YYYY-MM-DD HH:MM (Cairo time)'));
      if (o.status === 'scheduled' && o.local < cairoNow(-60000)) return Promise.reject(new Error('That time has passed — pick a later one or publish now'));
      var plan = sget('gwPlan', []), x = o.id ? plan.filter(function (y) { return y.id === o.id; })[0] : null;
      if (o.id && !x) return Promise.reject(new Error('This planned post is gone'));
      if (x && x.status !== 'draft' && x.status !== 'scheduled') return Promise.reject(new Error('Only a draft or a scheduled post can be changed (this one is ' + x.status + ')'));
      if (!x) { x = { id: plan.reduce(function (m, y) { return Math.max(m, y.id); }, 0) + 1 }; plan.push(x); }
      x.channel = o.channel; x.body = b; x.thera = o.thera || []; x.status = o.status; x.local = o.local || null; x.template = o.template || x.template || null;
      sset('gwPlan', plan); return Promise.resolve(x.id); },
    cancel: function (id) { var plan = sget('gwPlan', []), x = plan.filter(function (y) { return y.id === id; })[0];
      if (!x) return Promise.reject(new Error('This planned post is gone')); if (x.status !== 'draft' && x.status !== 'scheduled') return Promise.reject(new Error('Only a draft or a scheduled post can be cancelled (this one is ' + x.status + ')'));
      x.status = 'cancelled'; sset('gwPlan', plan); return Promise.resolve(); },
    publishNow: function (id) { var plan = sget('gwPlan', []), x = plan.filter(function (y) { return y.id === id; })[0];
      if (!x) return Promise.reject(new Error('This planned post is gone')); if (x.status !== 'draft' && x.status !== 'scheduled') return Promise.reject(new Error('This post is already ' + x.status));
      x.status = 'published'; x.publishedAt = new Date().toISOString(); sset('gwPlan', plan);
      var c = CHANNELS.filter(function (y) { return y.key === x.channel; })[0], sd = c && SEEDS[c.k]; if (sd) sd.posts.unshift(planPost(x)); return Promise.resolve(); }
  };
  function CH() { return live() ? window.dxGrowth.channels : DEMO_CH; }
  function content() { return document.getElementById('adminContent'); }
  var STATUS = { draft: ['📝 Draft', 'dx-st-draft'], scheduled: ['🕘 Scheduled', 'dx-st-sched'], published: ['✓ Published', 'dx-st-pub'], cancelled: ['✕ Cancelled', 'dx-st-off'], failed: ['⚠️ Not published', 'dx-st-fail'] };
  var DOW = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  function chName(k) { var c = CHANNELS.filter(function (x) { return x.key === k; })[0]; return c ? c.emoji + ' ' + c.t : k; }
  var CHS = { rows: [], tpl: [] };
  function channelsPage(c) {
    if (!c) return;
    c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">📣 Channels</div><div class="admin-page-sub">The official Drugbox channels: plan, schedule (Cairo time) and publish posts as Drugbox — nobody else posts there</div></div>' +
      '<div class="admin-section dx-ch" style="margin:0 28px"><div class="dx-ch-bar"><button type="button" class="btn-p dx-ch-new">+ New channel post</button></div>' +
      '<div class="admin-section-title">🗓 Planned and published</div><div class="dx-ch-list"><div class="adm-muted">Loading…</div></div>' +
      '<div class="admin-section-title" style="margin-top:18px">📋 Content plan — ready templates</div><div class="dx-ch-tpl"></div></div>';
    i18n(c);
    Promise.all([CH().list(), CH().templates()]).then(function (r) {
      CHS.rows = r[0] || []; CHS.tpl = r[1] || [];
      var box = c.querySelector('.dx-ch-list'); if (!box) return;
      box.innerHTML = CHS.rows.length ? '<div style="overflow-x:auto"><table class="admin-table dx-ch-tbl"><thead><tr><th>Status</th><th>Channel</th><th>When (Cairo)</th><th>Post</th><th></th></tr></thead><tbody>' + CHS.rows.map(function (x) {
        var st = STATUS[x.status] || [x.status, ''], open = x.status === 'draft' || x.status === 'scheduled';
        return '<tr data-chid="' + x.id + '"><td><span class="dx-st ' + st[1] + '">' + esc(st[0]) + '</span></td><td style="white-space:nowrap">' + esc(chName(x.channel_key)) + '</td>' +
          '<td style="white-space:nowrap" data-noi18n>' + esc(x.publish_local || (x.status === 'published' && x.published_at ? String(x.published_at).slice(0, 16).replace('T', ' ') : '—')) + '</td>' +
          '<td style="max-width:340px"><div class="dx-ch-ex" data-noi18n>' + esc(String(x.body || '').slice(0, 140)) + '</div>' + (x.error ? '<div class="adm-muted" data-noi18n>' + esc(x.error) + '</div>' : '') + '</td>' +
          '<td style="white-space:nowrap">' + (open ? '<button type="button" class="adm-link dx-ch-edit">Edit</button> · <button type="button" class="adm-link dx-ch-pub">Publish now</button> · <button type="button" class="adm-link adm-danger dx-ch-cancel">Cancel</button>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>'
        : '<div class="dbk-empty">Nothing planned yet — start from a template below.</div>';
      var tb = c.querySelector('.dx-ch-tpl');
      if (tb) tb.innerHTML = CHS.tpl.map(function (t) {
        return '<div class="dx-tpl" data-tpl="' + esc(t.key) + '"><div class="dx-tpl-b"><b>' + esc(ar() ? t.title_ar : t.title_en) + '</b><span>' + esc(chName(t.channel_key)) + ' · ' +
          esc(t.cadence === 'daily' ? 'Daily' : 'Weekly, ' + DOW[t.weekday]) + ' · <span data-noi18n>' + esc(String(t.at_time).slice(0, 5)) + '</span></span></div><button type="button" class="btn-ghost dx-tpl-use">Use →</button></div>'; }).join('');
      i18n(c);
    }, function (e) { toast(errMsg(e)); });
  }
  GW.channelsPage = channelsPage;
  function chForm(x, tplKey) {
    x = x || {}; var t = tplKey ? CHS.tpl.filter(function (y) { return y.key === tplKey; })[0] : null;
    var body = x.body || (t ? (ar() ? t.body_ar : t.body_en) : ''), channel = x.channel_key || (t && t.channel_key) || 'news', thera = x.thera || (t && t.thera) || [];
    var when = x.publish_local || '', mode = x.status === 'scheduled' ? 'scheduled' : x.id ? 'draft' : (t ? 'scheduled' : 'draft');
    var m = D.modal({ title: x.id ? 'Edit channel post' : 'New channel post', body:
      '<div class="dbk-f"><label for="chC">Channel *</label><select id="chC">' + CHANNELS.map(function (c) { return '<option value="' + c.key + '"' + (c.key === channel ? ' selected' : '') + '>' + esc(c.emoji + ' ' + c.t) + '</option>'; }).join('') + '</select></div>' +
      '<div class="dbk-f"><label for="chT">Template</label><select id="chT"><option value="">— None —</option>' + CHS.tpl.map(function (y) { return '<option value="' + esc(y.key) + '"' + ((x.template_key || tplKey) === y.key ? ' selected' : '') + '>' + esc(ar() ? y.title_ar : y.title_en) + '</option>'; }).join('') + '</select></div>' +
      '<div class="dbk-f"><label for="chB">Post (as Drugbox) *</label><textarea id="chB" rows="9" maxlength="5000" data-req data-noi18n>' + esc(body) + '</textarea></div>' +
      '<div class="dbk-f"><span class="dbk-lbl">Therapeutic areas</span><div class="dx-th-checks">' + THERA.map(function (k) { return '<label class="dx-th-ck"><input type="checkbox" value="' + k[0] + '"' + (thera.indexOf(k[0]) >= 0 ? ' checked' : '') + '> ' + esc(k[2] + ' ' + k[1]) + '</label>'; }).join('') + '</div></div>' +
      '<div class="dbk-f"><span class="dbk-lbl">When</span><div class="dx-ch-mode">' + [['draft', 'Save as draft'], ['scheduled', 'Schedule'], ['now', 'Publish now']].map(function (o) {
        return '<label><input type="radio" name="chM" value="' + o[0] + '"' + (o[0] === mode ? ' checked' : '') + '> ' + esc(o[1]) + '</label>'; }).join('') + '</div></div>' +
      '<div class="dbk-row dx-ch-when"><div class="dbk-f"><label for="chD">Date (Cairo)</label><input id="chD" type="date" value="' + esc(when.slice(0, 10)) + '"></div><div class="dbk-f"><label for="chH">Time (Cairo)</label><input id="chH" type="time" value="' + esc(when.slice(11, 16)) + '"></div></div>' +
      '<div class="adm-muted">Times are Cairo time (Africa/Cairo). The best hour for the trade is 21:00–23:00.</div>',
      primary: { label: 'Save', onClick: function (bx, close) {
        if (!D.requireFields(bx)) return false;
        var md = (bx.querySelector('input[name=chM]:checked') || {}).value || 'draft', d = bx.querySelector('#chD').value, h = bx.querySelector('#chH').value;
        var o = { id: x.id || null, channel: bx.querySelector('#chC').value, template: bx.querySelector('#chT').value || null, body: bx.querySelector('#chB').value,
          thera: [].map.call(bx.querySelectorAll('.dx-th-ck input:checked'), function (i) { return i.value; }), status: md === 'scheduled' ? 'scheduled' : 'draft', local: d && h ? d + ' ' + h : null };
        if (md === 'scheduled' && !o.local) { toast('Pick the date and time to publish (Cairo time)'); return false; }
        var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        CH().save(o).then(function (id) { return md === 'now' ? CH().publishNow(id).then(function () { return 'Published in ' + chName(o.channel); }) : (md === 'scheduled' ? 'Scheduled for ' + o.local + ' (Cairo)' : 'Draft saved'); })
          .then(function (msg) { close(); toast(msg); channelsPage(content()); }, function (e) { if (ok) ok.disabled = false; toast(errMsg(e)); });
        return false; } } });
    var bx = m.el;
    function syncWhen() { var md = (bx.querySelector('input[name=chM]:checked') || {}).value; bx.querySelector('.dx-ch-when').style.display = md === 'now' ? 'none' : ''; }
    bx.addEventListener('change', function (e) {
      if (e.target.name === 'chM') syncWhen();
      if (e.target.id === 'chT' && e.target.value) {   /* a template fills the text, the channel and its next slot */
        var y = CHS.tpl.filter(function (z) { return z.key === e.target.value; })[0]; if (!y) return;
        bx.querySelector('#chB').value = ar() ? y.body_ar : y.body_en; bx.querySelector('#chC').value = y.channel_key;
        CH().next(y.key).then(function (n) { if (!n) return; bx.querySelector('#chD').value = n.slice(0, 10); bx.querySelector('#chH').value = n.slice(11, 16); var s = bx.querySelector('input[name=chM][value=scheduled]'); if (s) { s.checked = true; syncWhen(); } });
      }
    });
    syncWhen(); i18n(bx);
    if (tplKey && !x.id) CH().next(tplKey).then(function (n) { if (!n) return; bx.querySelector('#chD').value = n.slice(0, 10); bx.querySelector('#chH').value = n.slice(11, 16); });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-ch-new, .dx-tpl-use, .dx-ch-edit, .dx-ch-pub, .dx-ch-cancel'); if (!t) return;
    e.preventDefault();
    if (t.classList.contains('dx-ch-new')) return chForm(null);
    if (t.classList.contains('dx-tpl-use')) return chForm(null, t.closest('[data-tpl]').dataset.tpl);
    var id = +t.closest('[data-chid]').dataset.chid, x = CHS.rows.filter(function (r) { return +r.id === id; })[0]; if (!x) return;
    if (t.classList.contains('dx-ch-edit')) return chForm(x);
    if (t.classList.contains('dx-ch-pub')) { t.disabled = true; CH().publishNow(id).then(function () { toast('Published in ' + chName(x.channel_key)); channelsPage(content()); }, function (er) { t.disabled = false; toast(errMsg(er)); }); return; }
    if (t.classList.contains('dx-ch-cancel')) D.modal({ title: 'Cancel this channel post?', body: '<p>It will not be published. You can plan it again from a template.</p>', secondary: 'Keep it',
      primary: { label: 'Cancel post', danger: true, onClick: function (bx, close) { CH().cancel(id).then(function () { close(); toast('Channel post cancelled'); channelsPage(content()); }, function (er) { toast(errMsg(er)); }); return false; } } });
  });

  /* the admin's tabs (Admin is for Drugbox staff — the database decides in the live app) */
  var ADM = [['channels', '📣 Channels'], ['founders', '🏅 Founders'], ['experts', '🎤 Expert sessions'], ['dirimport', '📥 Directory import']];
  function adminNav() {
    var nav = document.querySelector('.admin-nav'); if (!nav || nav.querySelector('[data-gwadm]')) return;
    var after = nav.querySelector('[onclick*="posts"]');
    ADM.slice().reverse().forEach(function (a) { var it = document.createElement('div'); it.className = 'admin-nav-item' + (window.adminTab === a[0] ? ' active' : ''); it.dataset.gwadm = a[0]; it.textContent = a[1];
      it.setAttribute('onclick', "switchAdminTab('" + a[0] + "')"); if (after && after.nextSibling) nav.insertBefore(it, after.nextSibling); else nav.appendChild(it); });
    i18n(nav);
  }
  var oAdmin = window.renderAdmin;
  if (typeof oAdmin === 'function') window.renderAdmin = function () { var r = oAdmin.apply(this, arguments); adminNav(); return r; };
  var oTab = window.renderAdminTab;
  if (typeof oTab === 'function') window.renderAdminTab = function (tab) {
    var c = content(), f = { channels: channelsPage, founders: GW.foundersPage, experts: GW.expertsAdmin, dirimport: GW.importPage }[tab];
    if (c && f) { document.querySelectorAll('.admin-nav-item').forEach(function (el) { el.classList.toggle('active', el.dataset.gwadm === tab); }); f(c); return; }
    return oTab.apply(this, arguments);
  };

  /* ═════════════ 2b. the therapeutic filter on Home ═════════════ */
  var FEEDTH = '';
  function feedBar() {
    var c = document.getElementById('content'); if (!c || c.querySelector('.dx-th-bar')) return;
    var comp = c.querySelector('.feed-wrap .composer'); if (!comp) return;
    comp.insertAdjacentHTML('afterend', '<div class="dx-th-bar" role="group" aria-label="Therapeutic area">' + theraSelect('dxThFeed', FEEDTH) + '</div>');
    i18n(c.querySelector('.dx-th-bar'));
    if (FEEDTH) applyFeed();
  }
  function feedPosts() { var comp = document.querySelector('#content .feed-wrap .composer'); return comp ? [].filter.call(comp.parentNode.querySelectorAll(':scope > .post'), function () { return true; }) : []; }
  function applyFeed() {
    var bar = document.querySelector('#content .dx-th-bar'); if (!bar) return;
    var old = document.querySelector('#content .dx-th-empty'); if (old) old.remove();
    var oldL = document.querySelector('#content .dx-th-list'); if (oldL) oldL.remove();
    var posts = feedPosts();
    if (!FEEDTH) { posts.forEach(function (p) { p.style.display = ''; }); return; }
    if (live() && window.dxGrowth.feedThera) {   /* live: the server finds every post about the area, not only the ones on screen */
      posts.forEach(function (p) { p.style.display = 'none'; });
      bar.insertAdjacentHTML('afterend', '<div class="dx-th-list"><div class="adm-muted">Loading…</div></div>');
      window.dxGrowth.feedThera(FEEDTH).then(function (list) { var box = document.querySelector('#content .dx-th-list'); if (!box) return;
        box.innerHTML = list.length ? list.map(function (p) { return window.renderPost(p); }).join('') : '<div class="dbk-empty dx-th-empty">No posts about ' + esc(theraLabel(FEEDTH)) + ' yet.</div>'; i18n(box); },
        function (e) { toast(errMsg(e)); });
      return;
    }
    var n = 0;
    posts.forEach(function (el) { var id = +String(el.id).replace('post-', ''), p = (window.POSTS || []).filter(function (x) { return x.id === id; })[0];
      var on = theraOf(p ? p.body : el.innerText).indexOf(FEEDTH) >= 0; el.style.display = on ? '' : 'none'; if (on) n++; });
    if (!n) bar.insertAdjacentHTML('afterend', '<div class="dbk-empty dx-th-empty">No posts about ' + esc(theraLabel(FEEDTH)) + ' yet.</div>');
    i18n(document.getElementById('content'));
  }
  document.addEventListener('change', function (e) {
    if (e.target && e.target.id === 'dxThFeed') { FEEDTH = e.target.value; applyFeed(); }
    if (e.target && e.target.id === 'dxThMk') { GW.marketThera = e.target.value; applyMarket(); }
  });

  /* ═════════════ 2c. the therapeutic filter in the Marketplace (the sidebar's own f-sec look) ═════════════ */
  GW.marketThera = '';
  function marketBar() {
    var side = document.querySelector('#mkx .sidebar, #mkx .fside, #mkx .filters'); var anchor = null;
    if (!side) { var h = [].filter.call(document.querySelectorAll('#mkx .f-hdr'), function (x) { return /Supplier quality|جودة المورّد/.test(x.textContent); })[0]; anchor = h && h.parentNode; side = anchor && anchor.parentNode; }
    if (!side || side.querySelector('.dx-th-sec')) return;
    var sec = document.createElement('div'); sec.className = 'f-sec dx-th-sec';
    sec.innerHTML = '<div class="f-hdr">Therapeutic area</div>' + theraSelect('dxThMk', GW.marketThera, ' ');
    var lab = sec.querySelector('.dx-th-l'); if (lab) { lab.className = 'dx-sr'; lab.textContent = 'Therapeutic area'; }
    var div = document.createElement('div'); div.className = 'fdiv';
    var first = side.querySelector('.f-sec'); side.insertBefore(sec, first); side.insertBefore(div, first);
    i18n(sec);
    if (GW.marketThera) applyMarket();
  }
  function cardText(el) { return el.innerText || ''; }
  function applyMarket() {
    if (live() && window.dxGrowth.marketThera) { window.dxGrowth.marketThera(GW.marketThera); return; }   /* live: the adapter asks the server (market_search_thera) */
    var cards = document.querySelectorAll('#mkx .main .listing-card, #mkx .main .sponsored-card, #mkx .main .lcard, #mkx .main [data-lid]'), n = 0;
    cards.forEach(function (el) { var on = !GW.marketThera || theraOf(cardText(el)).indexOf(GW.marketThera) >= 0; el.style.display = on ? '' : 'none'; if (on) n++; });
    var old = document.querySelector('#mkx .dx-th-empty'); if (old) old.remove();
    if (GW.marketThera && !n) { var m = document.querySelector('#mkx .main'); if (m) { m.insertAdjacentHTML('afterbegin', '<div class="dbk-empty dx-th-empty">No listings about ' + esc(theraLabel(GW.marketThera)) + ' yet — try another area.</div>'); i18n(m.firstElementChild); } }
  }
  GW.applyMarket = applyMarket;
})();

/* ═════════════════════════ AREA w-growth, part 2: founders, Ask an expert, directory import, visitors, courses in Arabic, the specialty question ═════════════════════════ */
(function () {
  var D = window.DBK, GW = window.dxGrowthUI; if (!D || !window.dxCore || !GW) return;
  var esc = D.esc, C = window.dxCore;
  function live() { var s = window.dxGrowth; return !!(s && s.live && s.ready && s.ready()); }
  function isLiveApp() { return !!window.dxLive; }
  function ar() { return document.documentElement.lang === 'ar'; }
  function toast(m) { D.toast(m); }
  function errMsg(e) { return (window.dxLive && window.dxLive.friendly ? window.dxLive.friendly(e) : (e && e.message)) || 'Something went wrong — try again'; }
  function sget(k, d) { try { var v = D.store.get(k, d); return v == null ? d : v; } catch (e) { return d; } }
  function sset(k, v) { try { D.store.set(k, v); } catch (e) {} }
  function i18n(el) { if (el && window.dxI18nAttrs) window.dxI18nAttrs(el); }
  function content() { return document.getElementById('adminContent'); }
  function page() { return document.body.getAttribute('data-page'); }
  function inApp() { var a = document.getElementById('app'); return !!a && a.getClientRects().length > 0 && getComputedStyle(a).visibility !== 'hidden'; }
  function day(t) { return t ? String(t).slice(0, 10) : ''; }
  function copy(text) { try { if (navigator.clipboard) return navigator.clipboard.writeText(text).then(function () { toast('Copied'); }, function () { toast('Select the text and copy it'); }); } catch (e) {} toast('Select the text and copy it'); }

  /* ═════════════ 3. founding members (W-42) ═════════════ */
  var SEG = [['manufacturer', 'Manufacturers', 'مصانع', 8], ['toll_brand', 'Toll manufacturers / brand owners', 'تصنيع لدى الغير / أصحاب براند', 10], ['agency', 'Agencies', 'وكالات', 15],
             ['distributor', 'Distributors / warehouses', 'موزّعين / مخازن', 15], ['file_owner', 'Registration-file owners', 'أصحاب ملفات تسجيل', 5], ['api', 'API / excipient suppliers', 'موردي خامات', 5],
             ['packaging', 'Packaging suppliers', 'موردي عبوات وتغليف', 10], ['regulatory', 'Regulatory consultants', 'استشاريين تسجيل', 5]];
  function segLabel(k, rows) { var r = (rows || []).filter(function (x) { return x.key === k; })[0]; if (r) return ar() ? r.label_ar : r.label_en; var s = SEG.filter(function (x) { return x[0] === k; })[0]; return s ? (ar() ? s[2] : s[1]) : k; }
  function newCode() { var a = '0123456789ABCDEFGHJKMNPQRSTVWXYZ', b = new Uint8Array(20), out = ''; (window.crypto || {}).getRandomValues ? crypto.getRandomValues(b) : b.forEach(function (_, i) { b[i] = Math.floor(Math.random() * 256); });
    for (var i = 0; i < 20; i++) out += a[b[i] % 32]; return 'DBX-' + out.match(/.{4}/g).join('-'); }
  function norm(c) { return String(c || '').replace(/^\s*DBX[-\s]*/i, '').replace(/[^A-Za-z0-9]/g, '').toUpperCase(); }
  /* demo: the invitations, quotas and founders kept in this browser (the live app: hashed codes on the server, 0101) */
  var DEMO_F = {
    overview: function () { var q = sget('gwFQuota', {}), inv = sget('gwFInv', []), mem = sget('gwFMem', []), now = Date.now();
      return Promise.resolve(SEG.map(function (s, i) { return { key: s[0], label_en: s[1], label_ar: s[2], quota: s[0] in q ? q[s[0]] : s[3], sort: i,
        joined: mem.filter(function (m) { return m.segment === s[0]; }).length, open_invites: inv.filter(function (x) { return x.segment === s[0] && !x.used && !x.revoked && x.expires > now; }).length }; })); },
    create: function (seg, note, days) { var rows = null; return DEMO_F.overview().then(function (o) { rows = o; var s = o.filter(function (x) { return x.key === seg; })[0]; if (!s) throw new Error('Pick a segment');
      var taken = sget('gwFInv', []).filter(function (x) { return x.segment === seg && (x.used || (!x.revoked && x.expires > Date.now())); }).length; if (taken >= s.quota) throw new Error('This segment is full (' + s.quota + ' of ' + s.quota + ')');
      var code = newCode(), inv = sget('gwFInv', []), id = inv.reduce(function (m, x) { return Math.max(m, x.id); }, 0) + 1, exp = Date.now() + (days || 60) * 86400000;
      inv.push({ id: id, key: norm(code), hint: norm(code).slice(-4), segment: seg, note: note || '', created: new Date().toISOString(), expires: exp }); sset('gwFInv', inv);
      return { id: id, code: code, expires_at: new Date(exp).toISOString() }; }); },
    list: function () { var now = Date.now(); return Promise.resolve(sget('gwFInv', []).slice().reverse().map(function (x) { return { id: x.id, code_hint: x.hint, segment: x.segment, note: x.note, created_at: x.created, expires_at: new Date(x.expires).toISOString(),
      used_by_name: x.usedBy || '', state: x.used ? 'used' : x.revoked ? 'revoked' : x.expires <= now ? 'expired' : 'open' }; })); },
    revoke: function (id) { var inv = sget('gwFInv', []), x = inv.filter(function (y) { return y.id === id; })[0]; if (!x) return Promise.reject(new Error('This invitation is gone'));
      if (x.used) return Promise.reject(new Error('This invitation was already used')); x.revoked = true; sset('gwFInv', inv); return Promise.resolve(); },
    quota: function (seg, n) { if (!(n >= 0 && n <= 1000)) return Promise.reject(new Error('A quota is 0 to 1,000')); var q = sget('gwFQuota', {}); q[seg] = n; sset('gwFQuota', q); return Promise.resolve(); },
    peek: function (code) { var x = sget('gwFInv', []).filter(function (y) { return y.key === norm(code); })[0], me = (window.ME || {}).id; if (!x) return Promise.resolve({ state: 'unknown' });
      var mine = sget('gwFMem', []).filter(function (m) { return m.user === me; })[0];
      return Promise.resolve({ state: x.used ? (x.usedId === me ? 'mine' : 'used') : x.revoked ? 'revoked' : x.expires <= Date.now() ? 'expired' : mine ? 'already' : 'open', segment: x.segment }); },
    redeem: function (code, co) { var inv = sget('gwFInv', []), x = inv.filter(function (y) { return y.key === norm(code); })[0], me = window.ME || {}, mem = sget('gwFMem', []);
      if (!x) return Promise.resolve({ error: 'invalid' });
      if (x.used) return Promise.reject(new Error(x.usedId === me.id ? 'You are already a founding member' : 'This invitation was already used'));
      if (x.revoked) return Promise.reject(new Error('This invitation was withdrawn by Drugbox')); if (x.expires <= Date.now()) return Promise.reject(new Error('This invitation has expired — ask Drugbox for a new one'));
      if (mem.some(function (m) { return m.user === me.id; })) return Promise.reject(new Error('You are already a founding member'));
      x.used = true; x.usedId = me.id; x.usedBy = me.name; sset('gwFInv', inv); mem.push({ user: me.id, segment: x.segment, at: new Date().toISOString() }); sset('gwFMem', mem);
      return (co ? DEMO_F.applyVip(co) : Promise.resolve(null)).then(function (v) { return { segment: x.segment, vip: v }; }); },
    my: function () { var me = (window.ME || {}).id, m = sget('gwFMem', []).filter(function (x) { return x.user === me; })[0]; return Promise.resolve(m ? { segment: m.segment, joined_at: m.at, vip_open: !m.vipCo, vip_company: m.vipCo || null } : null); },
    applyVip: function (slug) { var me = (window.ME || {}).id, mem = sget('gwFMem', []), m = mem.filter(function (x) { return x.user === me; })[0];
      if (!m) return Promise.reject(new Error('Only founding members have the 3 VIP months')); if (m.vipCo) return Promise.reject(new Error('Your 3 VIP months were already given to a company page'));
      var X = window.dxDir, co = X && X.myCompanies ? X.myCompanies().filter(function (c) { return c.slug === slug; })[0] : null; if (!co) return Promise.reject(new Error('Give the VIP months to a company page you run (owner or admin)'));
      var ed = sget('company_edits', {}), until = new Date(Date.now() + 91 * 86400000).toISOString().slice(0, 10); ed[slug] = Object.assign({}, ed[slug] || {}, { plan: 'vip', vipUntil: until }); sset('company_edits', ed);
      window.__dxStoreVer = (window.__dxStoreVer || 0) + 1; m.vipCo = slug; sset('gwFMem', mem); return Promise.resolve({ company: slug, vip_until: until }); },
    myCompanies: function () { var X = window.dxDir; return Promise.resolve(X && X.myCompanies ? X.myCompanies().filter(function (c) { return c.owner === (window.ME || {}).id; }).map(function (c) { return { id: c.slug, name: c.name }; }) : []); },
    isFounder: function (uid) { return Promise.resolve(sget('gwFMem', []).some(function (m) { return m.user === uid; })); }
  };
  function F() { return live() ? window.dxGrowth.founders : DEMO_F; }
  var FV = { seg: [], inv: [] };
  GW.foundersPage = function (c) {
    if (!c) return;
    c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">🏅 Founding members</div><div class="admin-page-sub">Invite-only early access: a founder badge and 3 months of VIP. Each invitation is for one segment, works once and is shown only once — joining is the invitee’s own choice</div></div>' +
      '<div class="admin-section dx-fnd" style="margin:0 28px"><div class="dx-ch-bar"><button type="button" class="btn-p dx-fnd-new">+ New invitation</button></div><div class="admin-section-title">Segments and quotas</div><div class="dx-fnd-seg"><div class="adm-muted">Loading…</div></div>' +
      '<div class="admin-section-title" style="margin-top:18px">Invitations</div><div class="dx-fnd-inv"></div></div>';
    i18n(c);
    Promise.all([F().overview(), F().list()]).then(function (r) {
      FV.seg = r[0] || []; FV.inv = r[1] || [];
      var sb = c.querySelector('.dx-fnd-seg'); if (!sb) return;
      sb.innerHTML = FV.seg.map(function (s) { var used = s.joined + s.open_invites, pc = s.quota ? Math.min(100, Math.round(100 * used / s.quota)) : 100;
        return '<div class="dx-fnd-card" data-seg="' + esc(s.key) + '"><b>' + esc(ar() ? s.label_ar : s.label_en) + '</b><div class="dx-fnd-bar"><i style="width:' + pc + '%"></i></div>' +
          '<small><span data-noi18n>' + s.joined + '</span> <span>joined</span> · <span data-noi18n>' + s.open_invites + '</span> <span>invited</span> · <span>quota</span> <span data-noi18n>' + s.quota + '</span></small>' +
          '<button type="button" class="adm-link dx-fnd-quota" style="align-self:flex-start">Change quota</button></div>'; }).join('');
      var ib = c.querySelector('.dx-fnd-inv');
      ib.innerHTML = FV.inv.length ? '<div style="overflow-x:auto"><table class="admin-table"><thead><tr><th>Code</th><th>Segment</th><th>For</th><th>State</th><th>Expires</th><th></th></tr></thead><tbody>' + FV.inv.map(function (x) {
        return '<tr data-fid="' + x.id + '"><td data-noi18n>…' + esc(x.code_hint) + '</td><td>' + esc(segLabel(x.segment, FV.seg)) + '</td><td data-noi18n>' + esc(x.note || '') + '</td>' +
          '<td><span class="dx-st ' + ({ open: 'dx-st-sched', used: 'dx-st-pub', revoked: 'dx-st-off', expired: 'dx-st-off' }[x.state] || '') + '">' + esc({ open: 'Open', used: 'Used', revoked: 'Revoked', expired: 'Expired' }[x.state] || x.state) + '</span>' +
          (x.used_by_name ? ' <span class="adm-muted" data-noi18n>' + esc(x.used_by_name) + '</span>' : '') + '</td><td data-noi18n>' + esc(day(x.expires_at)) + '</td>' +
          '<td>' + (x.state === 'open' ? '<button type="button" class="adm-link adm-danger dx-fnd-rev">Revoke</button>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>'
        : '<div class="dbk-empty">No invitations yet.</div>';
      i18n(c);
    }, function (e) { toast(errMsg(e)); });
  };
  function inviteLink(code) { return location.href.split('#')[0] + '#/founder/' + encodeURIComponent(code); }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-fnd-new, .dx-fnd-quota, .dx-fnd-rev, .dx-fnd-copy'); if (!t) return; e.preventDefault();
    if (t.classList.contains('dx-fnd-copy')) return copy(t.dataset.copy);
    if (t.classList.contains('dx-fnd-new')) return D.modal({ title: 'New founding-member invitation', body:
      '<div class="dbk-f"><label for="fnS">Segment *</label><select id="fnS" data-req><option value="">Choose…</option>' + (FV.seg.length ? FV.seg : SEG.map(function (s) { return { key: s[0], label_en: s[1], label_ar: s[2] }; })).map(function (s) { return '<option value="' + esc(s.key) + '">' + esc(ar() ? s.label_ar : s.label_en) + '</option>'; }).join('') + '</select></div>' +
      '<div class="dbk-f"><label for="fnN">Who it is for (your note)</label><input id="fnN" maxlength="200" placeholder="e.g. Eng. Sameh — Delta distribution"></div>' +
      '<div class="dbk-f"><label for="fnD">Valid for (days)</label><input id="fnD" type="number" min="1" max="365" value="60"></div>',
      primary: { label: 'Make invitation', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        F().create(bx.querySelector('#fnS').value, bx.querySelector('#fnN').value.trim(), +bx.querySelector('#fnD').value || 60).then(function (r) { close(); showCode(r); GW.foundersPage(content()); },
          function (er) { if (ok) ok.disabled = false; toast(errMsg(er)); }); return false; } } });
    if (t.classList.contains('dx-fnd-quota')) { var k = t.closest('[data-seg]').dataset.seg, s = FV.seg.filter(function (x) { return x.key === k; })[0] || {};
      return D.modal({ title: 'Quota — ' + segLabel(k, FV.seg), body: '<div class="dbk-f"><label for="fnQ">Founding members in this segment *</label><input id="fnQ" type="number" min="0" max="1000" data-req value="' + (s.quota || 0) + '"></div>',
        primary: { label: 'Save', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; F().quota(k, +bx.querySelector('#fnQ').value).then(function () { close(); toast('Quota saved'); GW.foundersPage(content()); }, function (er) { toast(errMsg(er)); }); return false; } } }); }
    if (t.classList.contains('dx-fnd-rev')) { var id = +t.closest('[data-fid]').dataset.fid;
      return D.modal({ title: 'Revoke this invitation?', body: '<p>The code stops working at once and its place in the segment is free again.</p>', secondary: 'Keep it',
        primary: { label: 'Revoke', danger: true, onClick: function (bx, close) { F().revoke(id).then(function () { close(); toast('Invitation revoked'); GW.foundersPage(content()); }, function (er) { toast(errMsg(er)); }); return false; } } }); }
  });
  function showCode(r) {
    var link = inviteLink(r.code);
    var m = D.modal({ title: 'Invitation ready — copy it now', secondary: 'Done', body: '<p>This code is shown only once. Send the link to the person it is for; they join by their own choice.</p>' +
      '<div class="dbk-f"><span class="dbk-lbl">Code</span><div class="dx-fnd-code" data-noi18n>' + esc(r.code) + '</div></div>' +
      '<div class="dbk-f"><span class="dbk-lbl">Link</span><div class="dx-fnd-code dx-fnd-link" data-noi18n>' + esc(link) + '</div></div>' +
      '<div class="dx-xp-acts"><button type="button" class="dbk-btn s dx-fnd-copy" data-copy="' + esc(r.code) + '">Copy code</button><button type="button" class="dbk-btn p dx-fnd-copy" data-copy="' + esc(link) + '">Copy link</button></div>' +
      '<div class="adm-muted"><span>Expires</span> <span data-noi18n>' + esc(day(r.expires_at)) + '</span></div>' });
    i18n(m.el);
  }
  /* the invitee: #/founder/<code> → after signing in or signing up, the choice to join */
  function codeFromHash() { var m = /^#\/founder\/([^?#]+)/.exec(location.hash || ''); return m ? decodeURIComponent(m[1]) : null; }
  function keepCode() { var c = codeFromHash(); if (c) { try { sessionStorage.setItem('dx_founder_code', c); } catch (e) {} } }
  keepCode(); window.addEventListener('hashchange', function () { keepCode(); offer(); });
  var OFFERING = false;
  function pendingCode() { try { return sessionStorage.getItem('dx_founder_code'); } catch (e) { return null; } }
  function dropCode() { try { sessionStorage.removeItem('dx_founder_code'); } catch (e) {} if (codeFromHash()) try { history.replaceState(history.state, '', location.pathname + location.search + '#/feed'); } catch (e) {} }
  function offer() {
    var code = pendingCode(); if (!code || OFFERING || !inApp() || !window.ME || window.DX_GUEST) return;
    if (isLiveApp() && !live()) return;                     /* the live app: wait until the member's session is ready */
    OFFERING = true;
    F().peek(code).then(function (p) {
      if (!p || p.state === 'unknown') { dropCode(); OFFERING = false; return toast('This invitation code is not valid'); }
      var why = { used: 'This invitation was already used.', revoked: 'This invitation was withdrawn by Drugbox.', expired: 'This invitation has expired — ask Drugbox for a new one.', already: 'You are already a founding member.', mine: 'You are already a founding member.' }[p.state];
      if (why) { dropCode(); OFFERING = false; var w = D.modal({ title: '🏅 Founding members', body: '<p>' + esc(why) + '</p>', secondary: 'Close' }); i18n(w.el); return; }
      return F().myCompanies().then(function (cos) {
        var m = D.modal({ title: '🏅 You are invited to be a founding member', secondary: 'Not now', body:
          '<p><span>Drugbox invites you to join its founding members as:</span> <b>' + esc(segLabel(p.segment)) + '</b>.</p>' +
          '<p>Founders get the founder badge on their profile and 3 months of VIP for a company page they run. Joining is your choice — nothing changes unless you press Join.</p>' +
          (cos.length ? '<div class="dbk-f"><label for="fnCo">Give the 3 VIP months to</label><select id="fnCo"><option value="">Later — I will choose a company page</option>' + cos.map(function (c) { return '<option value="' + esc(c.id) + '">' + esc(c.name) + '</option>'; }).join('') + '</select></div>'
            : '<div class="adm-muted">You can give the 3 VIP months to your company page later, from your profile.</div>'),
          primary: { label: 'Join as a founding member', onClick: function (bx, close) { var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
            var co = bx.querySelector('#fnCo') ? bx.querySelector('#fnCo').value : '';
            F().redeem(code, co || null).then(function (r) { if (r && r.error) { if (ok) ok.disabled = false; return toast('This invitation code is not valid'); }
              dropCode(); close(); toast(co ? 'Welcome, founding member! Your company page is VIP for 3 months' : 'Welcome, founding member!'); BADGE = {}; if (page() === 'profile') paintBadge(true); },
              function (er) { if (ok) ok.disabled = false; toast(errMsg(er)); }); return false; } } });
        m.el.querySelector('[data-a=cancel]').addEventListener('click', dropCode); i18n(m.el); OFFERING = false;
      });
    }).catch(function (e) { OFFERING = false; toast(errMsg(e)); });
  }
  document.addEventListener('dx:page', function () { setTimeout(offer, 400); });
  GW.offerFounder = offer;
  /* the badge on a profile, and my VIP months still to give */
  var BADGE = {};
  function profileUid() { var c = document.getElementById('content'); var b = c && c.querySelector('[data-cu],[data-fu],[data-au]'); if (b) return +(b.dataset.cu || b.dataset.fu || b.dataset.au); return (window.ME || {}).id; }
  function paintBadge(force) {
    var nm = document.querySelector('#content .profile-name'); if (!nm || (!force && nm.dataset.gwf)) return; nm.dataset.gwf = '1';
    var uid = profileUid(), me = window.ME || {};
    var f = live() ? window.dxGrowth.founders.isFounder(uid) : DEMO_F.isFounder(uid);
    f.then(function (yes) { var n2 = document.querySelector('#content .profile-name'); if (!n2) return; var old = n2.querySelector('.dx-fnd-badge'); if (old) old.remove();
      if (yes) { n2.insertAdjacentHTML('beforeend', ' <span class="dx-fnd-badge" title="One of Drugbox’s founding members">🏅 Founding member</span>'); i18n(n2); }
      if (yes && uid === me.id) F().my().then(function (m) { if (!m || !m.vip_open || document.querySelector('#content .dx-fnd-vip')) return;
        n2.insertAdjacentHTML('afterend', '<div class="dx-fnd-vip why-banner" style="margin:8px 0"><span>🎁 You have 3 VIP months to give to a company page you run.</span> <button type="button" class="adm-link dx-fnd-give">Choose a company</button></div>'); i18n(n2.parentNode); }); }, function () {});
  }
  document.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('.dx-fnd-give'); if (!t) return; e.preventDefault();
    F().myCompanies().then(function (cos) {
      if (!cos.length) return toast('Create or claim your company page first');
      var m = D.modal({ title: 'Your 3 VIP months', body: '<div class="dbk-f"><label for="fnCo2">Company page *</label><select id="fnCo2" data-req><option value="">Choose…</option>' + cos.map(function (c) { return '<option value="' + esc(c.id) + '">' + esc(c.name) + '</option>'; }).join('') + '</select></div><p class="adm-muted">This can be done once.</p>',
        primary: { label: 'Give the VIP months', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; F().applyVip(bx.querySelector('#fnCo2').value).then(function () { close(); toast('Your company page is VIP for 3 months'); var v = document.querySelector('#content .dx-fnd-vip'); if (v) v.remove(); }, function (er) { toast(errMsg(er)); }); return false; } } });
      i18n(m.el); }); });

  /* ═════════════ 4. Ask an expert (W-43) — on the Training page ═════════════ */
  var TOPICS = [['file_purchase', 'Buying a registration file safely', 'شراء ملف تسجيل بأمان'], ['nfsa', 'NFSA notification (supplements, food)', 'إخطار هيئة سلامة الغذاء'], ['agency_contract', 'Agency and distribution contracts', 'عقد الوكالة والتوزيع'],
    ['toll_card', 'The toll-manufacturing card', 'كارت التصنيع لدى الغير'], ['pricing', 'Pricing and price increases', 'التسعير وزيادة الأسعار'], ['importer', 'Importing and the importer’s file', 'الاستيراد وملف المستورد'],
    ['cold_chain', 'Cold chain', 'سلسلة التبريد'], ['labs_tracking', 'Authority labs and track & trace', 'معامل الهيئة والتتبع'], ['choose_factory', 'Choosing a factory', 'اختيار مصنع'], ['other', 'Another topic', 'موضوع تاني']];
  function topicLabel(k) { var t = TOPICS.filter(function (x) { return x[0] === k; })[0]; return t ? (ar() ? t[2] : t[1]) : k; }
  function addDays(n, hm) { var d = GW.cairoNow(n * 86400000).slice(0, 10); return d + ' ' + hm; }
  function demoSessions() {
    var s = sget('gwXS', null); if (s) return s;
    s = [{ id: 1, topic: 'file_purchase', title: 'Buying a registration file safely', title_ar: 'شراء ملف تسجيل بأمان', about: 'What to check before you pay: the holder, the status, the transfer papers and who pays the fees.', expert_name: 'Dr. Mona Saleh', expert_line: 'Regulatory consultant, 18 years of registration files', local: addDays(3, '20:00'), minutes: 60, seats: 100, registered: 37, status: 'scheduled', link: 'https://meet.example.com/drugbox-file', q: [] },
         { id: 2, topic: 'toll_card', title: 'The toll-manufacturing card, step by step', title_ar: 'كارت التصنيع لدى الغير خطوة بخطوة', about: 'From the contract to the card: the documents and the order.', expert_name: 'Eng. Karim Adel', expert_line: 'Toll-manufacturing manager', local: addDays(-9, '20:00'), minutes: 60, seats: 80, registered: 64, status: 'done', link: '',
           q: [{ id: 21, who: 'Ahmed R.', body: 'Does the toll card need the factory’s GMP certificate first?', answer: 'Yes — the authority asks for the site’s valid GMP certificate with the contract.', at: '' }] }];
    sset('gwXS', s); return s;
  }
  var DEMO_X = {
    sessions: function () { var me = (window.ME || {}).id, reg = sget('gwXReg', {}), mine = sget('gwXQ', []);
      return Promise.resolve(demoSessions().map(function (s) { var qs = s.q.concat(mine.filter(function (q) { return q.session === s.id; }));
        return { id: s.id, topic: s.topic, title: s.title, title_ar: s.title_ar, about: s.about, expert_name: s.expert_name, expert_line: s.expert_line, starts_local: s.local, minutes: s.minutes, seats: s.seats,
          registered_count: s.registered + (reg[s.id] ? 1 : 0), status: s.status, registered: !!reg[s.id], questions: qs.length, has_link: !!s.link }; })
        .sort(function (a, b) { var up = function (x) { return x.status === 'scheduled' ? 0 : 1; }; return up(a) - up(b) || (up(a) ? String(b.starts_local).localeCompare(a.starts_local) : String(a.starts_local).localeCompare(b.starts_local)); })); },
    questions: function (id) { var s = demoSessions().filter(function (x) { return x.id === id; })[0], mine = sget('gwXQ', []), ans = sget('gwXAns', {});
      return Promise.resolve((s ? s.q : []).concat(mine.filter(function (q) { return q.session === id; }).map(function (q) { return Object.assign({}, q, { answer: ans[q.id] || q.answer || null }); }))); },
    demand: function () { var r = sget('gwXReqs', {}); return Promise.resolve(TOPICS.map(function (t, i) { return { topic: t[0], asked: [4, 2, 6, 3, 5, 1, 2, 3, 2, 0][i] + (r[t[0]] ? 1 : 0), mine: !!r[t[0]] }; })); },
    request: function (topic, note) { if (topic === 'other' && String(note || '').trim().length < 5) return Promise.reject(new Error('Say which topic (a few words)')); var r = sget('gwXReqs', {}); if (r[topic]) return Promise.reject(new Error('You already asked for this topic'));
      r[topic] = note || true; sset('gwXReqs', r); return Promise.resolve(); },
    withdraw: function (topic) { var r = sget('gwXReqs', {}); delete r[topic]; sset('gwXReqs', r); return Promise.resolve(); },
    register: function (id) { var s = demoSessions().filter(function (x) { return x.id === id; })[0]; if (!s || s.status !== 'scheduled') return Promise.reject(new Error('This session is not open'));
      var reg = sget('gwXReg', {}); reg[id] = true; sset('gwXReg', reg); return Promise.resolve(); },
    unregister: function (id) { var reg = sget('gwXReg', {}); delete reg[id]; sset('gwXReg', reg); return Promise.resolve(); },
    link: function (id) { var s = demoSessions().filter(function (x) { return x.id === id; })[0]; if (!sget('gwXReg', {})[id]) return Promise.reject(new Error('Register for the session to get its link'));
      return Promise.resolve(s && s.link ? s.link : null); },
    ask: function (id, body) { body = String(body || '').trim(); if (body.length < 5) return Promise.reject(new Error('Write your question (at least 5 characters)')); if (!sget('gwXReg', {})[id]) return Promise.reject(new Error('Register for the session to ask'));
      var q = sget('gwXQ', []); q.push({ id: Date.now(), session: id, who: (window.ME || {}).name, body: body, answer: null, mine: true }); sset('gwXQ', q); return Promise.resolve(); },
    /* Drugbox (Admin → Expert sessions) */
    adminRequests: function () { return DEMO_X.demand().then(function (d) { var r = sget('gwXReqs', {}); return d.map(function (x) { return { topic: x.topic, asked: x.asked, notes: typeof r[x.topic] === 'string' ? [{ name: (window.ME || {}).name, note: r[x.topic] }] : [] }; }); }); },
    save: function (o) { var s = demoSessions(); if (!o.title || o.title.length < 3) return Promise.reject(new Error('Give the session a title')); if (!o.expert_name) return Promise.reject(new Error('Name the expert'));
      if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(o.local || '')) return Promise.reject(new Error('Give the date and time as YYYY-MM-DD HH:MM (Cairo time)'));
      if (o.link && !/^https:\/\/\S{4,}$/i.test(o.link)) return Promise.reject(new Error('The meeting link must start with https://'));
      var x = o.id ? s.filter(function (y) { return y.id === o.id; })[0] : null; if (!x) { if (o.local <= GW.cairoNow()) return Promise.reject(new Error('Pick a time in the future')); x = { id: s.reduce(function (m, y) { return Math.max(m, y.id); }, 0) + 1, registered: 0, status: 'scheduled', q: [] }; s.push(x); }
      Object.assign(x, { topic: o.topic, title: o.title, title_ar: o.title_ar, about: o.about, expert_name: o.expert_name, expert_line: o.expert_line, local: o.local, minutes: +o.minutes || 60, seats: +o.seats || 100, link: o.link || '' });
      sset('gwXS', s); return Promise.resolve(x.id); },
    status: function (id, st) { var s = demoSessions(), x = s.filter(function (y) { return y.id === id; })[0]; if (!x || x.status !== 'scheduled') return Promise.reject(new Error('This session is already ' + (x ? x.status : 'gone'))); x.status = st; sset('gwXS', s); return Promise.resolve(); },
    answer: function (qid, text) { if (!String(text || '').trim()) return Promise.reject(new Error('Write the answer')); var a = sget('gwXAns', {}); a[qid] = text.trim(); sset('gwXAns', a); return Promise.resolve(); },
    full: function (id) { var s = demoSessions().filter(function (x) { return x.id === id; })[0]; return Promise.resolve(s ? { id: s.id, topic: s.topic, title: s.title, title_ar: s.title_ar, about: s.about, expert_name: s.expert_name, expert_line: s.expert_line, starts_local: s.local, minutes: s.minutes, seats: s.seats, join_url: s.link } : null); }
  };
  function X() { return live() ? window.dxGrowth.experts : DEMO_X; }
  var XV = { open: false };
  function title(s) { return ar() && s.title_ar ? s.title_ar : s.title; }
  function sessHtml(s, admin) {
    var up = s.status === 'scheduled', left = Math.max(0, s.seats - s.registered_count);
    return '<div class="dx-xp-s" data-xsid="' + s.id + '"><h3 data-noi18n>' + esc(title(s)) + '</h3>' +
      '<div class="dx-xp-meta"><span>🎤 <span data-noi18n>' + esc(s.expert_name) + '</span>' + (s.expert_line ? ' — <span data-noi18n>' + esc(s.expert_line) + '</span>' : '') + '</span>' +
      '<span>🗓 <span data-noi18n>' + esc(s.starts_local) + '</span> <span>(Cairo)</span> · <span data-noi18n>' + s.minutes + '</span> <span>min</span></span><span>🏷 ' + esc(topicLabel(s.topic)) + '</span>' +
      (up ? '<span>👥 <span data-noi18n>' + s.registered_count + '</span> <span>registered</span> · <span data-noi18n>' + left + '</span> <span>seats left</span></span>' : '<span>' + (s.status === 'done' ? '✓ Took place' : '✕ Cancelled') + '</span>') + '</div>' +
      (s.about ? '<div style="font-size:13px;color:#374151" data-noi18n>' + esc(s.about) + '</div>' : '') +
      (admin ? '' : '<div class="dx-xp-acts">' + (up ? (s.registered ? '<span class="dx-st dx-st-pub">✓ Registered</span><button type="button" class="dbk-btn p dx-xp-join">▶ Join the session</button><button type="button" class="dbk-btn s dx-xp-unreg">Cancel registration</button>'
        : left > 0 ? '<button type="button" class="dbk-btn p dx-xp-reg">Register</button>' : '<span class="dx-st dx-st-off">Full</span>') : '') +
        '<button type="button" class="dbk-btn s dx-xp-qa">💬 Questions and answers (<span data-noi18n>' + (s.questions || 0) + '</span>)</button></div>') +
      '<div class="dx-xp-qbox" hidden></div></div>';
  }
  function expertView(root) {
    var box = root.querySelector('.dx-xp'); if (!box) return;
    box.innerHTML = '<div class="dx-xp-h"><h2>🎤 Ask an expert</h2><button type="button" class="btn-ghost dx-xp-back">← All courses</button></div>' +
      '<p style="margin:0;font-size:13.5px;color:#4b5563">Sessions arranged on request: ask for a topic, Drugbox invites an expert, you register, get a reminder and the questions and answers stay here.</p>' +
      '<div class="dx-xp-sec">Upcoming sessions</div><div class="dx-xp-up"><div class="adm-muted">Loading…</div></div>' +
      '<div class="dx-xp-sec">Ask for a topic</div><div class="dx-xp-topics"></div>' +
      '<div class="dx-xp-sec">Past sessions — questions and answers</div><div class="dx-xp-past"></div>';
    i18n(box);
    Promise.all([X().sessions(), X().demand()]).then(function (r) {
      var up = r[0].filter(function (s) { return s.status === 'scheduled'; }), past = r[0].filter(function (s) { return s.status !== 'scheduled'; });
      box.querySelector('.dx-xp-up').innerHTML = up.length ? up.map(function (s) { return sessHtml(s); }).join('') : '<div class="dbk-empty">No session is scheduled yet — ask for a topic below.</div>';
      box.querySelector('.dx-xp-past').innerHTML = past.length ? past.map(function (s) { return sessHtml(s); }).join('') : '<div class="adm-muted">No past sessions yet.</div>';
      box.querySelector('.dx-xp-topics').innerHTML = r[1].map(function (d) { return '<div class="dx-xp-topic" data-xtopic="' + esc(d.topic) + '"><b>' + esc(topicLabel(d.topic)) + '</b><small><span data-noi18n>' + d.asked + '</span> <span>asked</span></small>' +
        (d.mine ? '<button type="button" class="dbk-btn s dx-xp-unask">✓ Requested · Withdraw</button>' : '<button type="button" class="dbk-btn p dx-xp-ask">Request this topic</button>') + '</div>'; }).join('');
      i18n(box);
    }, function (e) { toast(errMsg(e)); });
  }
  function openExperts(on) {
    var root = document.querySelector('#content .training-grid'); root = root && root.parentNode; if (!root) return;
    XV.open = on; var grid = root.querySelector('.training-grid'), bar = root.querySelector('.tr-bar');
    if (grid) grid.hidden = on; if (bar) bar.hidden = on;
    var box = root.querySelector('.dx-xp');
    if (!on) { if (box) box.remove(); return; }
    if (!box) { box = document.createElement('div'); box.className = 'dx-xp'; (bar || grid).parentNode.insertBefore(box, bar || grid); }
    expertView(root);
  }
  GW.openExperts = openExperts;
  function trainingBtn() {
    var my = document.querySelector('#content .tr-bar .tr-my'); if (!my || my.parentNode.querySelector('.dx-xp-open')) return;
    my.insertAdjacentHTML('beforebegin', '<button type="button" class="btn-ghost dx-xp-open">🎤 Ask an expert</button>'); i18n(my.parentNode);
  }
  function qaBox(card, id) {
    var qb = card.querySelector('.dx-xp-qbox'); qb.hidden = !qb.hidden; if (qb.hidden) return;
    qb.innerHTML = '<div class="adm-muted">Loading…</div>';
    var s0 = card.closest('.dx-xp-up') ? 1 : 0;
    X().questions(id).then(function (qs) {
      var reg = !!card.querySelector('.dx-xp-unreg');
      qb.innerHTML = (qs.length ? qs.map(function (q) { return '<div class="dx-xp-q"><p><b data-noi18n>' + esc(q.who || q.name || '') + '</b>: <span data-noi18n>' + esc(q.body) + '</span></p>' +
        (q.answer ? '<div class="dx-xp-a"><b>Answer:</b> <span data-noi18n>' + esc(q.answer) + '</span></div>' : '<div class="adm-muted">Not answered yet</div>') + '</div>'; }).join('') : '<div class="adm-muted">No questions yet.</div>') +
        (s0 && reg ? '<div class="dbk-f" style="margin-top:8px"><label for="xpQ' + id + '">Your question for the expert</label><textarea id="xpQ' + id + '" rows="2" maxlength="1000"></textarea></div><button type="button" class="dbk-btn p dx-xp-send">Send question</button>'
          : s0 ? '<div class="adm-muted">Register to ask the expert a question.</div>' : '');
      i18n(qb);
    }, function (e) { toast(errMsg(e)); });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-xp-open, .dx-xp-back, .dx-xp-reg, .dx-xp-unreg, .dx-xp-join, .dx-xp-qa, .dx-xp-send, .dx-xp-ask, .dx-xp-unask'); if (!t) return; e.preventDefault();
    if (t.classList.contains('dx-xp-open')) return openExperts(true);
    if (t.classList.contains('dx-xp-back')) return openExperts(false);
    var root = document.querySelector('#content'), card = t.closest('[data-xsid]'), id = card ? +card.dataset.xsid : null, tp = t.closest('[data-xtopic]');
    function again(msg) { if (msg) toast(msg); expertView(root.querySelector('.dx-xp').parentNode); }
    if (t.classList.contains('dx-xp-reg')) { t.disabled = true; return X().register(id).then(function () { again('Registered — you will get a reminder a day and an hour before'); }, function (er) { t.disabled = false; toast(errMsg(er)); }); }
    if (t.classList.contains('dx-xp-unreg')) return X().unregister(id).then(function () { again('Registration cancelled'); }, function (er) { toast(errMsg(er)); });
    if (t.classList.contains('dx-xp-join')) return X().link(id).then(function (u) { if (u) window.open(u, '_blank', 'noopener'); else toast('The meeting link is not set yet — Drugbox will notify you'); }, function (er) { toast(errMsg(er)); });
    if (t.classList.contains('dx-xp-qa')) return qaBox(card, id);
    if (t.classList.contains('dx-xp-send')) { var ta = card.querySelector('textarea'); t.disabled = true; return X().ask(id, ta.value).then(function () { toast('Question sent'); var qb = card.querySelector('.dx-xp-qbox'); qb.hidden = true; qaBox(card, id); }, function (er) { t.disabled = false; toast(errMsg(er)); }); }
    if (t.classList.contains('dx-xp-unask')) return X().withdraw(tp.dataset.xtopic).then(function () { again('Request withdrawn'); }, function (er) { toast(errMsg(er)); });
    if (t.classList.contains('dx-xp-ask')) { var k = tp.dataset.xtopic;
      var m = D.modal({ title: 'Request: ' + topicLabel(k), body: '<div class="dbk-f"><label for="xpN">' + (k === 'other' ? 'Which topic? *' : 'What do you want to know? (optional)') + '</label><textarea id="xpN" rows="3" maxlength="500"' + (k === 'other' ? ' data-req' : '') + '></textarea></div><p class="adm-muted">Drugbox schedules a session when enough members ask — you are told when it is set.</p>',
        primary: { label: 'Send request', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; X().request(k, bx.querySelector('#xpN').value.trim()).then(function () { close(); again('Request sent — you will be told when a session is set'); }, function (er) { toast(errMsg(er)); }); return false; } } });
      i18n(m.el); }
  });
  /* Admin → Expert sessions */
  var XA = { list: [] };
  GW.expertsAdmin = function (c) {
    if (!c) return;
    c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">🎤 Expert sessions</div><div class="admin-page-sub">What members ask for, the sessions and their questions — members are told when a session on their topic is set and reminded a day and an hour before</div></div>' +
      '<div class="admin-section" style="margin:0 28px"><div class="dx-ch-bar"><button type="button" class="btn-p dx-xa-new">+ Schedule a session</button></div><div class="admin-section-title">Requests by topic</div><div class="dx-xa-req"><div class="adm-muted">Loading…</div></div>' +
      '<div class="admin-section-title" style="margin-top:18px">Sessions</div><div class="dx-xa-list"></div></div>';
    i18n(c);
    Promise.all([X().adminRequests(), X().sessions()]).then(function (r) {
      XA.list = r[1] || [];
      c.querySelector('.dx-xa-req').innerHTML = '<div style="overflow-x:auto"><table class="admin-table"><thead><tr><th>Topic</th><th>Asked</th><th>Notes</th></tr></thead><tbody>' + r[0].slice().sort(function (a, b) { return b.asked - a.asked; }).map(function (x) {
        return '<tr><td>' + esc(topicLabel(x.topic)) + '</td><td data-noi18n>' + x.asked + '</td><td style="font-size:12.5px" data-noi18n>' + (x.notes || []).map(function (n) { return esc((n.name ? n.name + ': ' : '') + n.note); }).join('<br>') + '</td></tr>'; }).join('') + '</tbody></table></div>';
      c.querySelector('.dx-xa-list').innerHTML = XA.list.length ? XA.list.map(function (s) {
        return sessHtml(s, true).replace('<div class="dx-xp-qbox" hidden></div>', '<div class="dx-xp-acts">' + (s.status === 'scheduled' ? '<button type="button" class="dbk-btn s dx-xa-edit">Edit</button><button type="button" class="dbk-btn s dx-xa-done">Mark done</button><button type="button" class="dbk-btn d dx-xa-cancel">Cancel session</button>' : '') +
          '<button type="button" class="dbk-btn s dx-xa-qs">💬 Questions (<span data-noi18n>' + (s.questions || 0) + '</span>)</button></div><div class="dx-xp-qbox" hidden></div>'); }).join('') : '<div class="dbk-empty">No sessions yet.</div>';
      i18n(c);
    }, function (e) { toast(errMsg(e)); });
  };
  function xaForm(s) {
    s = s || {}; var when = s.starts_local || '';
    var m = D.modal({ title: s.id ? 'Edit session' : 'Schedule an expert session', body:
      '<div class="dbk-f"><label for="xaT">Topic *</label><select id="xaT">' + TOPICS.map(function (t) { return '<option value="' + t[0] + '"' + (s.topic === t[0] ? ' selected' : '') + '>' + esc(ar() ? t[2] : t[1]) + '</option>'; }).join('') + '</select></div>' +
      '<div class="dbk-f"><label for="xaTi">Title (English) *</label><input id="xaTi" maxlength="160" data-req value="' + esc(s.title || '') + '"></div>' +
      '<div class="dbk-f"><label for="xaTa">Title (Arabic)</label><input id="xaTa" maxlength="160" dir="rtl" value="' + esc(s.title_ar || '') + '"></div>' +
      '<div class="dbk-f"><label for="xaAb">About</label><textarea id="xaAb" rows="3" maxlength="2000">' + esc(s.about || '') + '</textarea></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="xaEn">Expert *</label><input id="xaEn" maxlength="120" data-req value="' + esc(s.expert_name || '') + '"></div><div class="dbk-f"><label for="xaEl">The expert’s line</label><input id="xaEl" maxlength="200" value="' + esc(s.expert_line || '') + '"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="xaD">Date (Cairo) *</label><input id="xaD" type="date" data-req value="' + esc(when.slice(0, 10)) + '"></div><div class="dbk-f"><label for="xaH">Time (Cairo) *</label><input id="xaH" type="time" data-req value="' + esc(when.slice(11, 16)) + '"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="xaM">Minutes</label><input id="xaM" type="number" min="15" max="240" value="' + (s.minutes || 60) + '"></div><div class="dbk-f"><label for="xaS">Seats</label><input id="xaS" type="number" min="1" max="1000" value="' + (s.seats || 100) + '"></div></div>' +
      '<div class="dbk-f"><label for="xaL">Meeting link (https://…) — given only to the registered, an hour before</label><input id="xaL" type="url" maxlength="400" value="' + esc(s.join_url || '') + '"></div>',
      primary: { label: s.id ? 'Save' : 'Schedule', onClick: function (bx, close) { if (!D.requireFields(bx)) return false; var v = function (id) { return bx.querySelector(id).value.trim(); };
        var o = { id: s.id || null, topic: v('#xaT'), title: v('#xaTi'), title_ar: v('#xaTa'), about: v('#xaAb'), expert_name: v('#xaEn'), expert_line: v('#xaEl'), local: v('#xaD') + ' ' + v('#xaH'), minutes: +v('#xaM') || 60, seats: +v('#xaS') || 100, link: v('#xaL') };
        var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        X().save(o).then(function () { close(); toast(s.id ? 'Session saved' : 'Session scheduled — the members who asked are told'); GW.expertsAdmin(content()); }, function (er) { if (ok) ok.disabled = false; toast(errMsg(er)); }); return false; } } });
    i18n(m.el);
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-xa-new, .dx-xa-edit, .dx-xa-done, .dx-xa-cancel, .dx-xa-qs, .dx-xa-ans'); if (!t) return; e.preventDefault();
    if (t.classList.contains('dx-xa-new')) return xaForm(null);
    var card = t.closest('[data-xsid]'), id = +card.dataset.xsid;
    if (t.classList.contains('dx-xa-edit')) return X().full(id).then(function (s) { if (s) xaForm(s); }, function (er) { toast(errMsg(er)); });
    if (t.classList.contains('dx-xa-done') || t.classList.contains('dx-xa-cancel')) { var st = t.classList.contains('dx-xa-done') ? 'done' : 'cancelled';
      return D.modal({ title: st === 'done' ? 'Mark this session as done?' : 'Cancel this session?', body: '<p>' + (st === 'done' ? 'Its questions and answers stay readable to every member.' : 'The registered members are told.') + '</p>', secondary: 'Back',
        primary: { label: st === 'done' ? 'Mark done' : 'Cancel session', danger: st !== 'done', onClick: function (bx, close) { X().status(id, st).then(function () { close(); toast(st === 'done' ? 'Session marked done' : 'Session cancelled — the registered are told'); GW.expertsAdmin(content()); }, function (er) { toast(errMsg(er)); }); return false; } } }); }
    if (t.classList.contains('dx-xa-qs')) { var qb = card.querySelector('.dx-xp-qbox'); qb.hidden = !qb.hidden; if (qb.hidden) return;
      return X().questions(id).then(function (qs) { qb.innerHTML = qs.length ? qs.map(function (q) { return '<div class="dx-xp-q" data-qid="' + q.id + '"><p><b data-noi18n>' + esc(q.who || q.name || '') + '</b>: <span data-noi18n>' + esc(q.body) + '</span></p>' +
        (q.answer ? '<div class="dx-xp-a"><b>Answer:</b> <span data-noi18n>' + esc(q.answer) + '</span></div>' : '<div class="dbk-f"><label for="xaA' + q.id + '">Answer</label><textarea id="xaA' + q.id + '" rows="2" maxlength="4000"></textarea></div><button type="button" class="dbk-btn p dx-xa-ans">Send answer</button>') + '</div>'; }).join('') : '<div class="adm-muted">No questions yet.</div>'; i18n(qb); }, function (er) { toast(errMsg(er)); }); }
    if (t.classList.contains('dx-xa-ans')) { var qd = t.closest('[data-qid]'), qid = +qd.dataset.qid; t.disabled = true;
      return X().answer(qid, qd.querySelector('textarea').value).then(function () { toast('Answer sent — the member is told'); var q2 = card.querySelector('.dx-xp-qbox'); q2.hidden = true; card.querySelector('.dx-xa-qs').click(); }, function (er) { t.disabled = false; toast(errMsg(er)); }); }
  });

  /* ═════════════ 5. Admin → Directory import (B-01 extended: from the browser, with a dry run first) ═════════════ */
  var SECTORS = ['Manufacturer', 'Cosmetics', 'CMO / Toll', 'API & excipients', 'Packaging', 'Labs & testing', 'Distribution', 'Regulatory & consulting', 'Supplements'];
  var COLS = ['name', 'name_ar', 'sectors', 'governorate', 'city', 'address', 'phone', 'email', 'website', 'registry', 'site', 'dosage_forms', 'certificates', 'source'];
  function parseCsv(text) {
    var rows = [], row = [], f = '', q = false, i = 0, s = String(text || '').replace(/^﻿/, '');
    for (; i < s.length; i++) { var ch = s[i];
      if (q) { if (ch === '"') { if (s[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += ch; continue; }
      if (ch === '"') q = true; else if (ch === ',') { row.push(f); f = ''; } else if (ch === '\n' || ch === '\r') { if (ch === '\r' && s[i + 1] === '\n') i++; row.push(f); f = ''; if (row.some(function (x) { return x.trim(); })) rows.push(row); row = []; } else f += ch; }
    if (f || row.length) { row.push(f); if (row.some(function (x) { return x.trim(); })) rows.push(row); }
    if (!rows.length) return [];
    var head = rows[0].map(function (h) { return h.trim().toLowerCase(); });
    return rows.slice(1).map(function (r) { var o = {}; head.forEach(function (h, k) { if (COLS.indexOf(h) >= 0) o[h] = (r[k] || '').trim(); }); return o; });
  }
  GW.parseCsv = parseCsv;
  function nameKey(n) { return String(n || '').toLowerCase().replace(/[أإآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/[ً-ْ]/g, '').replace(/[^\p{L}\p{N} ]+/gu, ' ')
    .replace(/(^| )(s ?a ?e|sae|co|company|corp|corporation|inc|ltd|llc|limited|plc|ش ?م ?م|شركه)(?= |$)/g, ' ').replace(/\s+/g, ' ').trim(); }
  var DEMO_I = {
    run: function (rows, dry) {
      var X0 = window.dxDir, existing = X0 && X0.companies ? X0.companies() : [], seen = {}, out = [], add = [];
      rows.forEach(function (r, i) { var name = (r.name || '').trim(), sec = String(r.sectors || '').split(';').map(function (x) { return x.trim(); }).filter(Boolean), reg = String(r.registry || '').replace(/\D/g, ''), key = nameKey(name), akey = nameKey(r.name_ar), bad = '';
        if (name.length < 2 || name.length > 200) bad = 'name is missing or longer than 200 characters'; else if (!key) bad = 'the name is only a legal form ("' + name + '") — write the company’s name';
        else if (!r.source) bad = 'source is missing — every imported company names the public list it comes from'; else if (!sec.length) bad = 'sectors are missing';
        else if (sec.some(function (x) { return SECTORS.indexOf(x) < 0; })) bad = 'unknown sector: ' + sec.filter(function (x) { return SECTORS.indexOf(x) < 0; }).join(', ');
        else if (r.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(r.email)) bad = 'e-mail is not valid'; else if (r.phone && !/^\+?[0-9 ()-]{6,30}$/.test(r.phone)) bad = 'phone is not valid';
        if (bad) { out.push({ row: i + 1, name: name, status: 'invalid', reason: bad }); return; }
        var dup = existing.filter(function (c) { return nameKey(c.name) === key || (akey && (nameKey(c.name) === akey || nameKey(c.nameAr || c.name_ar) === akey)) || (reg && String(c.registry || '').replace(/\D/g, '') === reg); })[0];
        if (dup) { out.push({ row: i + 1, name: name, status: 'duplicate', slug: dup.slug, of: dup.name }); return; }
        if (seen[key] || (akey && seen[akey]) || (reg && seen['r' + reg])) { out.push({ row: i + 1, name: name, status: 'invalid', reason: 'duplicate of an earlier row in this file' }); return; }
        seen[key] = 1; if (akey) seen[akey] = 1; if (reg) seen['r' + reg] = 1;
        var slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'company-' + (i + 1);
        add.push({ slug: slug, name: name, name_ar: r.name_ar || '', sector: sec[0], sectors: sec, city: r.city || '', gov: r.governorate || '', registry: reg, source: r.source, phone: r.phone || '', email: r.email || '', website: r.website || '' });
        out.push({ row: i + 1, name: name, status: dry ? 'would create' : 'created', slug: slug }); });
      if (!dry && add.length) { var keep = sget('gwImported', []).concat(add); sset('gwImported', keep); mountImported(); }
      return Promise.resolve({ dry_run: dry, rows: rows.length, created: out.filter(function (o) { return o.status === 'created' || o.status === 'would create'; }).length,
        duplicates: out.filter(function (o) { return o.status === 'duplicate'; }).length, invalid: out.filter(function (o) { return o.status === 'invalid'; }).length, results: out });
    }
  };
  /* demo: imported companies join the directory as unclaimed pages (the approved "public industry list" pages) */
  function mountImported() {
    if (isLiveApp()) return; var list = sget('gwImported', []); if (!list.length) return;
    var seeds = (window.dxDirSeeds || []).filter(function (c) { return !c.__gw; });
    window.dxDirSeeds = seeds.concat(list.map(function (c) { return { __gw: 1, slug: c.slug, name: c.name, nameAr: c.name_ar, status: 'unclaimed', owner: null, plan: 'free', licensed: false, verified: false, level: '', rating: 0, reviews: 0, reply: '—', color: '#64748b',
      sector: c.sector, sectors: c.sectors, city: c.city, gov: c.gov, founded: '—', employees: '—', tagline: '', about: 'Listed from public industry sources. This page has not been claimed by the company yet — details may be incomplete.',
      certs: [], phone: '', email: '', whatsapp: '', website: '', address: [c.city, c.gov].filter(Boolean).join(', '), hours: '', services: [], products: [], jobs: [], source: c.source, registry: c.registry }; }));
    window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;
  }
  var gotoI = window.goto, IMP = false;   /* on the first visit to Companies (see seedChannels: the demo is known only then) */
  window.goto = function (p) { if ((p === 'companies' || p === 'market') && !IMP) { IMP = true; mountImported(); } return gotoI.apply(this, arguments); };
  function I() { return live() ? window.dxGrowth.directory : DEMO_I; }
  var IV = { rows: null, file: '' };
  var SAMPLE_CSV = 'name,name_ar,sectors,governorate,city,registry,source\n"Delta Sterile Pharma S.A.E.","دلتا للمستحضرات المعقمة","Manufacturer;CMO / Toll",Gharbia,Tanta,51234,"EDA licensed manufacturers list, 2026-09"\n"Sinai Packaging Industries",,Packaging,"South Sinai","El Tor",,"Chamber of pharmaceutical industries members list, 2026"\n';
  GW.importPage = function (c) {
    if (!c) return;
    c.innerHTML = '<div class="admin-page-hdr"><div class="admin-page-title">📥 Directory import</div><div class="admin-page-sub">Load companies from an official PUBLIC list (CSV) as unclaimed pages, marked as such; each row names its source. Duplicates (same registry number or name, English or Arabic) are skipped. Check first, then import</div></div>' +
      '<div class="admin-section" style="margin:0 28px"><div class="dbk-f"><label for="impF">CSV file (UTF-8) — columns: ' + COLS.join(', ') + ' (name, sectors and source are required)</label><input id="impF" type="file" accept=".csv,text/csv"></div>' +
      '<div class="dx-xp-acts"><button type="button" class="dbk-btn s dx-imp-sample">⬇ Sample CSV</button><button type="button" class="dbk-btn p dx-imp-check" disabled>Check (nothing is written)</button><button type="button" class="dbk-btn p dx-imp-go" disabled>Import</button></div>' +
      '<div class="dx-imp-out"></div></div>';
    IV.rows = null; i18n(c);
  };
  function impResult(r) {
    var box = document.querySelector('#adminContent .dx-imp-out'); if (!box) return;
    box.innerHTML = '<div class="dx-imp-sum"><span class="dx-imp-ok">' + esc(r.dry_run ? 'Would create' : 'Created') + ': <span data-noi18n>' + r.created + '</span></span><span class="dx-imp-dup">Duplicates: <span data-noi18n>' + r.duplicates + '</span></span><span class="dx-imp-bad">Invalid: <span data-noi18n>' + r.invalid + '</span></span></div>' +
      '<div style="overflow-x:auto"><table class="admin-table"><thead><tr><th>Row</th><th>Company</th><th>Result</th></tr></thead><tbody>' + (r.results || []).map(function (x) {
        return '<tr><td data-noi18n>' + x.row + '</td><td data-noi18n>' + esc(x.name || '') + '</td><td>' + (x.status === 'invalid' ? '<span class="dx-imp-bad">Invalid</span>: <span data-noi18n>' + esc(x.reason || '') + '</span>'
          : x.status === 'duplicate' ? '<span class="dx-imp-dup">Already in the directory</span>' + (x.of ? ' (<span data-noi18n>' + esc(x.of) + '</span>)' : '') : '<span class="dx-imp-ok">' + esc(x.status === 'created' ? 'Created — unclaimed' : 'Would be created — unclaimed') + '</span>') + '</td></tr>'; }).join('') + '</tbody></table></div>';
    i18n(box);
  }
  document.addEventListener('change', function (e) {
    if (!e.target || e.target.id !== 'impF') return; var f = e.target.files && e.target.files[0]; if (!f) return;
    if (f.size > 2 * 1024 * 1024) { toast('The file is larger than 2 MB — split it'); return; }
    var rd = new FileReader(); rd.onload = function () { IV.rows = parseCsv(rd.result); IV.file = f.name; var ch = document.querySelector('.dx-imp-check'), go = document.querySelector('.dx-imp-go');
      if (!IV.rows.length) { toast('No rows found — the first line must be the column names'); if (ch) ch.disabled = true; return; }
      if (IV.rows.length > 2000) { toast('At most 2,000 rows per import'); return; }
      if (ch) ch.disabled = false; if (go) go.disabled = true; toast(IV.rows.length + ' rows read — check them first'); }; rd.readAsText(f, 'utf-8');
  });
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('.dx-imp-sample, .dx-imp-check, .dx-imp-go'); if (!t) return; e.preventDefault();
    if (t.classList.contains('dx-imp-sample')) { var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['﻿' + SAMPLE_CSV], { type: 'text/csv' })); a.download = 'drugbox-companies-sample.csv'; document.body.appendChild(a); a.click(); a.remove(); return; }
    if (!IV.rows) return toast('Choose the CSV file first');
    var dry = t.classList.contains('dx-imp-check'); t.disabled = true;
    I().run(IV.rows, dry).then(function (r) { impResult(r); t.disabled = false; var go = document.querySelector('.dx-imp-go');
      if (dry && go) go.disabled = !r.created; if (!dry) { toast(r.created === 1 ? '1 company imported as an unclaimed page' : r.created + ' companies imported as unclaimed pages'); IV.rows = null; if (go) go.disabled = true; var ch = document.querySelector('.dx-imp-check'); if (ch) ch.disabled = true; } },
      function (er) { t.disabled = false; toast(errMsg(er)); });
  });

  /* ═════════════ 6. visitors (the owner's decision 1): company pages without signing in ═════════════
     The sign-in page offers the company directory; a shared #/companies/<slug> link opens that page. A visitor reads the directory and
     company pages (name, about, products, sites, certificates, the verified badge) — anything else (contact, follow, quote, claim, other
     pages) asks them to sign in. Live: the adapter reads public_* functions (0103) — no phone, e-mail or private data reach a visitor. */
  var GUEST_OK = /^(companies)$/;
  function setMeta(t, d, img) {
    document.title = t;
    function m(sel, attr, key, val) { var el = document.head.querySelector(sel); if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); } el.setAttribute('content', val); }
    m('meta[name="description"]', 'name', 'description', d); m('meta[property="og:title"]', 'property', 'og:title', t); m('meta[property="og:description"]', 'property', 'og:description', d);
    m('meta[property="og:type"]', 'property', 'og:type', 'website'); if (img) m('meta[property="og:image"]', 'property', 'og:image', img);
    var can = document.head.querySelector('link[rel=canonical]'); if (!can) { can = document.createElement('link'); can.rel = 'canonical'; document.head.appendChild(can); } can.href = location.href.split('?')[0];
  }
  GW.setMeta = setMeta;
  var DEF_TITLE = document.title;
  function companyMeta() {   /* SEO basics: an open company page names itself in the title, description and Open Graph tags */
    var S = window.dxDir && window.dxDir.S, slug = S && S.open, X0 = window.dxDir, co = slug && X0 && X0.bySlug ? X0.bySlug(slug) : null;
    if (page() === 'companies' && co) { if (GW.__meta === slug) return; GW.__meta = slug;
      setMeta(co.name + ' — Drugbox', (co.tagline || co.about || (co.sectors || []).join(' · ') + (co.city ? ' — ' + co.city : '')).slice(0, 200) + (co.status === 'unclaimed' ? ' · Listed from public industry sources (unclaimed)' : ''), co.logo || ''); }
    else if (GW.__meta) { GW.__meta = null; setMeta(DEF_TITLE, 'Drugbox — the B2B network of the pharmaceutical industry in Egypt and the Arab region.', ''); }
  }
  function guestBar() {
    if (document.querySelector('.dx-guest-bar')) return;
    var b = document.createElement('div'); b.className = 'dx-guest-bar'; b.setAttribute('role', 'region'); b.setAttribute('aria-label', 'Visitor');
    b.innerHTML = '<span>👋 You are browsing as a visitor — sign in to contact companies, follow them or ask for a quote.</span><span><button type="button" class="dbk-btn s dx-guest-in">Sign in</button> <button type="button" class="dbk-btn p dx-guest-join">Join Drugbox</button></span>';
    var app = document.getElementById('app'); app.insertBefore(b, app.firstChild); i18n(b);
  }
  function enterGuest(slug) {
    if (inApp() && !window.DX_GUEST) return;
    window.DX_GUEST = true; document.documentElement.classList.add('dx-guest');
    if (!isLiveApp() && window.ME && window.ME.id) { GW.__me = window.ME; window.ME = { id: 0, name: 'Visitor', initials: 'V', color: '#64748b', headline: '', company: '', role: 'visitor', verified: false }; }   /* demo: nobody's pages are "mine" */
    if (window.dxGrowth && window.dxGrowth.guest) window.dxGrowth.guest(true);
    var aw = document.getElementById('authWrap'); if (aw) aw.style.display = 'none'; var app = document.getElementById('app'); if (app) app.style.display = 'flex';
    guestBar(); window.goto('companies');
    if (slug && window.dxOpenCompany) setTimeout(function () { window.dxOpenCompany(slug); }, 300);
  }
  function leaveGuest(signup) {
    window.DX_GUEST = false; document.documentElement.classList.remove('dx-guest'); var b = document.querySelector('.dx-guest-bar'); if (b) b.remove();
    if (GW.__me) { window.ME = GW.__me; GW.__me = null; }
    if (window.dxGrowth && window.dxGrowth.guest) window.dxGrowth.guest(false);
    var app = document.getElementById('app'); if (app) app.style.display = 'none'; var aw = document.getElementById('authWrap'); if (aw) aw.style.display = '';
    if (signup && window.showSignup) window.showSignup(); else if (window.showLogin) window.showLogin();
    GW.__meta = null; setMeta(DEF_TITLE, 'Drugbox — the B2B network of the pharmaceutical industry in Egypt and the Arab region.', '');
  }
  GW.enterGuest = enterGuest; GW.leaveGuest = leaveGuest;
  function signInFirst() { toast('Sign in or join Drugbox to do this'); leaveGuest(false); }
  var gotoG = window.goto;
  window.goto = function (p) { if (window.DX_GUEST && !GUEST_OK.test(p)) { signInFirst(); return; } return gotoG.apply(this, arguments); };
  var gpG = window.gotoProfile; if (gpG) window.gotoProfile = function () { if (window.DX_GUEST) return signInFirst(); return gpG.apply(this, arguments); };
  /* a visitor may read: the directory's search, filters, cards, "View page", the page's tabs, "All companies", "Show more" — anything else asks to sign in */
  var READ = /^(view page|عرض الصفحة|all companies|كل الشركات|جميع الشركات|show more|عرض المزيد|overview|products|sites|listings|jobs|reviews|contact|team|نظرة عامة|المنتجات|المواقع|الإعلانات|الوظائف|التقييمات|التواصل|الفريق|←.*|.*→ ?all|clear|امسح.*)/i;
  document.addEventListener('click', function (e) {
    if (!window.DX_GUEST) return;
    var t = e.target.closest && e.target.closest('button, a, [onclick], [role=button], [role=tab], .ctx-item'); if (!t || !document.getElementById('app').contains(t)) return;
    if (t.closest('.dx-guest-bar')) { e.preventDefault(); e.stopImmediatePropagation(); return leaveGuest(t.classList.contains('dx-guest-join')); }
    var inDir = t.closest('#dxDir'), label = ((t.getAttribute('aria-label') || '') + ' ' + (t.innerText || '')).replace(/\s+/g, ' ').trim();
    var oc = t.getAttribute('onclick') || '';
    if (/goto\('companies'\)/.test(oc)) return;
    if (inDir && (t.matches('[data-hopen], [data-htab], [data-hmore], [role=tab], .hb-tab, .dr-chip, .dr-fchip, select, input') || READ.test(label) || /^\s*$/.test(label))) return;
    if (inDir && t.closest('.dr-bar, .hb-filters, .dr-filters, .hb-tabs, .cp-tabs')) return;
    e.preventDefault(); e.stopImmediatePropagation(); signInFirst();
  }, true);
  /* the sign-in page's way in for visitors, and a shared company link opened signed out */
  function browseLink() {
    var lp = document.getElementById('loginPage'); if (!lp || lp.querySelector('.lg-browse')) return;
    var fl = lp.querySelector('.f-link'); if (!fl) return;
    fl.insertAdjacentHTML('afterend', '<button type="button" class="lg-browse">🏭 Browse the company directory without signing in</button>'); i18n(lp);
  }
  browseLink();
  document.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('.lg-browse'); if (!t) return; e.preventDefault(); enterGuest(null); });
  function linkSlug() { var m = /^#\/companies\/([^?#/]+)/.exec(location.hash || ''); return m ? decodeURIComponent(m[1]) : null; }
  function signedOutOnLink() { var lp = document.getElementById('loginPage'); return lp && lp.getClientRects().length > 0 && !inApp(); }
  setTimeout(function wait(n) { n = n || 0; var s = linkSlug(); if (!s) return; if (signedOutOnLink() && (!isLiveApp() || (window.dxGrowth && window.dxGrowth.signedOut && window.dxGrowth.signedOut()))) return enterGuest(s); if (n < 40 && !inApp()) setTimeout(function () { wait(n + 1); }, 250); }, 1200);
  /* signing in from the visitor's page: the app opens as the member */
  var oLogin = window.doLogin; if (oLogin) window.doLogin = function () { if (window.DX_GUEST) leaveGuest(false); return oLogin.apply(this, arguments); };

  /* ═════════════ 7. the six courses in Arabic (decision 7) ═════════════ */
  var COURSE_AR = { 'GMP Fundamentals': ['أساسيات التصنيع الجيد (GMP)', 'ممارسات التصنيع الجيد لإنتاج الدواء وأنظمة الجودة.'], 'EDA Registration Process': ['خطوات التسجيل في هيئة الدواء', 'دليل كامل لتجهيز ملف التسجيل في هيئة الدواء المصرية وتقديمه.'],
    'ICH Guidelines': ['إرشادات ICH', 'إرشادات المجلس الدولي للتنسيق من Q1 إلى Q14.'], 'Cosmetics Regulation': ['تنظيم مستحضرات التجميل', 'إخطار مستحضرات التجميل في مصر والخليج والبطاقة والالتزام بالاشتراطات.'],
    'Stability Studies': ['دراسات الثبات', 'تصميم بروتوكولات الثبات للمنطقتين IVa وIVb وفق ICH Q1A وQ1E.'], 'GCC Market Access': ['دخول أسواق الخليج', 'مسارات التسجيل في السعودية والإمارات والكويت والبحرين وقطر.'] };
  GW.courseAr = COURSE_AR;
  function coursesAr() {
    var ok = ar(), root = document.getElementById('content'); if (!root) return;
    var map = {}; Object.keys(COURSE_AR).forEach(function (en) { map[en] = COURSE_AR[en]; });
    var extra = live() && window.dxGrowth.coursesAr ? window.dxGrowth.coursesAr() : null; if (extra) Object.keys(extra).forEach(function (en) { map[en] = extra[en]; });
    root.querySelectorAll('.tr-card .tr-title, .tr-card .tr-desc').forEach(function (el) {
      var orig = el.dataset.gwen || el.textContent, isT = el.classList.contains('tr-title');
      var hit = map[orig] || (isT ? null : Object.keys(map).map(function (k) { return map[k]; }).filter(function () { return false; })[0]);
      if (!isT) { var card = el.closest('.tr-card'), t = card && card.querySelector('.tr-title'), en = t ? (t.dataset.gwen || t.textContent) : ''; hit = map[en] ? [null, map[en][1]] : null; if (hit && !el.dataset.gwen) el.dataset.gwen = el.textContent; }
      else if (hit && !el.dataset.gwen) el.dataset.gwen = el.textContent;
      if (!el.dataset.gwen) return;
      var want = ok && hit ? hit[isT ? 0 : 1] : el.dataset.gwen; if (want && el.textContent !== want) el.textContent = want;
    });
  }

  /* ═════════════ 8. the one-time specialty question (decision 9) ═════════════ */
  var SPECS = ['Regulatory Affairs', 'Quality Control / QA', 'Sales & Business Dev', 'Production', 'R&D / Formulation', 'CEO / Management'];
  var ASKED = false;
  function specialty() {
    if (ASKED || !inApp() || window.DX_GUEST || !window.ME) return;
    if (isLiveApp() && !live()) return;
    ASKED = true;
    var due = live() ? window.dxGrowth.specialtyDue() : Promise.resolve(window.ME.headline === 'Regulatory Affairs' && !sget('gwSpecAns', null));
    due.then(function (yes) {
      if (!yes) return;
      var m = D.modal({ title: 'Is this still your specialty?', secondary: 'Ask me later', body:
        '<p>Your profile says <b>Regulatory Affairs</b> — the sign-up form used to choose it for everyone. Please confirm it or pick yours, so the right people, jobs and groups find you.</p>' +
        '<div class="dbk-f"><label for="spSel">Your specialty</label><select id="spSel">' + SPECS.map(function (s) { return '<option value="' + esc(s) + '">' + esc(s) + '</option>'; }).join('') + '<option value="__other">Other…</option></select></div>' +
        '<div class="dbk-f" id="spOw" hidden><label for="spOther">Your specialty, in your words</label><input id="spOther" maxlength="120"></div>',
        primary: { label: 'Save', onClick: function (bx, close) { var v = bx.querySelector('#spSel').value, h = v === '__other' ? bx.querySelector('#spOther').value.trim() : v;
          if (v === '__other' && h.length < 2) { toast('Write your specialty'); return false; }
          var p = live() ? window.dxGrowth.specialtyAnswer(h === 'Regulatory Affairs' ? null : h) : (function () { sset('gwSpecAns', h); window.ME.headline = h; return Promise.resolve(h); })();
          p.then(function (saved) { window.ME.headline = saved || h; if (typeof window.updateTopUser === 'function') window.updateTopUser(); close(); toast(h === 'Regulatory Affairs' ? 'Thanks — your specialty is confirmed' : 'Your specialty is saved'); }, function (er) { toast(errMsg(er)); });
          return false; } } });
      m.el.addEventListener('change', function (e) { if (e.target.id === 'spSel') m.el.querySelector('#spOw').hidden = e.target.value !== '__other'; });
      i18n(m.el);
    }, function () { ASKED = false; });
  }
  GW.specialty = function () { ASKED = false; specialty(); };
  document.addEventListener('dx:page', function () { setTimeout(specialty, 900); });
  var oOut = window.doLogout; if (oOut) window.doLogout = function () { ASKED = false; BADGE = {}; return oOut.apply(this, arguments); };

  C.onRender('w-growth-2', function () {
    var p = page();
    if (p === 'training') { trainingBtn(); coursesAr(); }
    else if (p === 'profile') paintBadge(false);
    if (window.DX_GUEST || GW.__meta) companyMeta(); else if (p === 'companies') companyMeta();
    if (!inApp()) browseLink();
  });
})();

/* ═════════════════════════ AREA w-growth, part 3: Arabic (the new labels only; members' and Drugbox's own texts stay as written) ═════════════════════════ */
(function () {
  if (!window.dxI18nExtend) return;
  window.dxI18nExtend({
    /* channels */
    '✓ Drugbox official': '✓ رسمي من Drugbox', 'OFFICIAL': 'رسمي', '✓ Drugbox official channel': '✓ قناة Drugbox الرسمية', '✓ Official': '✓ رسمي', 'Official Drugbox channel': 'قناة Drugbox الرسمية',
    'Drugbox News': 'Drugbox أخبار', 'Drugbox Jobs': 'Drugbox وظائف', 'Drugbox Regulatory': 'Drugbox تسجيل ورقابة', 'Drugbox Market': 'Drugbox السوق',
    'Official Drugbox channel: industry news, Drugbox updates and the weekly practical guide.': 'قناة Drugbox الرسمية: أخبار الصناعة وتحديثات Drugbox والدليل العملي الأسبوعي.',
    'Official Drugbox channel: the week’s jobs and hiring news across the industry.': 'قناة Drugbox الرسمية: وظائف الأسبوع وأخبار التوظيف في الصناعة.',
    'Official Drugbox channel: the weekly regulatory bulletin (EDA, NFSA) and how to read a registration-file ad.': 'قناة Drugbox الرسمية: النشرة التنظيمية الأسبوعية (هيئة الدواء، هيئة سلامة الغذاء) وإزاي تقرا إعلان ملف تسجيل.',
    'Official Drugbox channel: «Wanted today» every evening, the week’s shortages and the agency market — business to business only.': 'قناة Drugbox الرسمية: «مطلوب النهارده» كل مساء ونواقص الأسبوع وسوق الوكالات — تجارة بين الشركات فقط.',
    '✓ Official Drugbox channel — only Drugbox posts here; you can comment and react.': '✓ قناة Drugbox الرسمية — Drugbox بس اللي بينشر هنا؛ تقدر تعلّق وتتفاعل.',
    'Drugbox speaks here': 'Drugbox بيتكلم هنا', 'Only Drugbox posts in its channels. Members comment and react.': 'Drugbox بس اللي بينشر في قنواته. الأعضاء بيعلّقوا ويتفاعلوا.',
    'Business to business': 'تجارة بين الشركات', 'Offers and requests are between companies and their agents — never sales to pharmacies or the public.': 'العروض والطلبات بين الشركات ووكلائها — مفيش بيع لصيدليات أو للجمهور.',
    '📣 Channels': '📣 القنوات', '🏅 Founders': '🏅 الأعضاء المؤسسون', '🎤 Expert sessions': '🎤 جلسات الخبراء', '📥 Directory import': '📥 استيراد الدليل',
    '📣 Channels ': '📣 القنوات', 'The official Drugbox channels: plan, schedule (Cairo time) and publish posts as Drugbox — nobody else posts there': 'قنوات Drugbox الرسمية: خطّط وجدول (بتوقيت القاهرة) وانشر باسم Drugbox — محدش غيره بينشر فيها',
    '+ New channel post': '+ منشور جديد في قناة', '🗓 Planned and published': '🗓 المخطط والمنشور', '📋 Content plan — ready templates': '📋 خطة المحتوى — قوالب جاهزة',
    'Status': 'الحالة', 'Channel': 'القناة', 'When (Cairo)': 'الموعد (القاهرة)', 'Post': 'المنشور', 'Edit': 'تعديل', 'Publish now': 'انشر دلوقتي', 'Cancel': 'إلغاء',
    '📝 Draft': '📝 مسودة', '🕘 Scheduled': '🕘 مجدول', '✓ Published': '✓ اتنشر', '✕ Cancelled': '✕ اتلغى', '⚠️ Not published': '⚠️ ماتنشرش',
    'Nothing planned yet — start from a template below.': 'مفيش حاجة متخططة لسه — ابدأ من قالب تحت.', 'Use →': 'استخدم ←', 'Daily': 'يومي',
    'Weekly, Sunday': 'أسبوعي، الأحد', 'Weekly, Monday': 'أسبوعي، الاتنين', 'Weekly, Tuesday': 'أسبوعي، التلات', 'Weekly, Wednesday': 'أسبوعي، الأربع', 'Weekly, Thursday': 'أسبوعي، الخميس', 'Weekly, Friday': 'أسبوعي، الجمعة', 'Weekly, Saturday': 'أسبوعي، السبت',
    'New channel post': 'منشور جديد في قناة', 'Edit channel post': 'تعديل منشور القناة', 'Channel *': 'القناة *', 'Template': 'القالب', '— None —': '— من غير —', 'Post (as Drugbox) *': 'المنشور (باسم Drugbox) *',
    'Therapeutic areas': 'المجموعات العلاجية', 'When': 'إمتى', 'Save as draft': 'احفظ مسودة', 'Schedule': 'جدول', 'Date (Cairo)': 'التاريخ (القاهرة)', 'Time (Cairo)': 'الساعة (القاهرة)',
    'Times are Cairo time (Africa/Cairo). The best hour for the trade is 21:00–23:00.': 'المواعيد بتوقيت القاهرة. أحسن وقت للسوق من 9 لـ 11 بالليل.', 'Save': 'حفظ',
    'Draft saved': 'اتحفظت المسودة', 'Channel post cancelled': 'اتلغى منشور القناة', 'Cancel this channel post?': 'تلغي منشور القناة ده؟', 'It will not be published. You can plan it again from a template.': 'مش هيتنشر. تقدر تخططه تاني من قالب.',
    'Keep it': 'سيبه', 'Cancel post': 'ألغِ المنشور', 'Pick the date and time to publish (Cairo time)': 'اختار تاريخ وساعة النشر (بتوقيت القاهرة)', 'Write the post first': 'اكتب المنشور الأول',
    'That time has passed — pick a later one or publish now': 'الوقت ده عدّى — اختار وقت بعده أو انشر دلوقتي', 'Give the date and time as YYYY-MM-DD HH:MM (Cairo time)': 'اكتب التاريخ والساعة بالشكل YYYY-MM-DD HH:MM (بتوقيت القاهرة)',
    'Only a Drugbox admin plans channel posts': 'أدمن Drugbox بس اللي بيخطط منشورات القنوات', 'Only a Drugbox admin publishes to the channels': 'أدمن Drugbox بس اللي بينشر في القنوات', 'Pick one of the Drugbox channels': 'اختار قناة من قنوات Drugbox',
    'Wanted today': 'مطلوب النهارده', 'This week’s shortages': 'نواقص الأسبوع', 'Weekly regulatory bulletin': 'النشرة التنظيمية الأسبوعية', 'How to read a registration-file ad': 'إزاي تقرا إعلان ملف تسجيل',
    'The agency market this week': 'سوق الوكالات الأسبوع ده', 'Practical guide of the week': 'الدليل العملي للأسبوع', 'Jobs of the week': 'وظائف الأسبوع',
    /* therapeutic areas */
    '🧬 Therapeutic area': '🧬 المجموعة العلاجية', 'Therapeutic area': 'المجموعة العلاجية', 'All therapeutic areas': 'كل المجموعات العلاجية',
    '🧬 Biologics': '🧬 بيولوجي', '🐄 Veterinary': '🐄 بيطري', '🌾 Agriculture': '🌾 زراعي', '💉 GLP-1': '💉 GLP-1', '🎗️ Oncology': '🎗️ أورام', '📏 Growth hormone': '📏 هرمون النمو', '👶 Fertility': '👶 خصوبة', '🩸 Insulin': '🩸 إنسولين',
    /* founders */
    '🏅 Founding members': '🏅 الأعضاء المؤسسون', 'Invite-only early access: a founder badge and 3 months of VIP. Each invitation is for one segment, works once and is shown only once — joining is the invitee’s own choice': 'دخول مبكر بالدعوة بس: شارة عضو مؤسس و3 شهور VIP. كل دعوة لشريحة واحدة، بتشتغل مرة واحدة وبتظهر مرة واحدة — والانضمام اختيار المدعو نفسه',
    '+ New invitation': '+ دعوة جديدة', 'Segments and quotas': 'الشرائح والحصص', 'Invitations': 'الدعوات', 'joined': 'انضم', 'invited': 'مدعو', 'quota': 'الحصة', 'Change quota': 'غيّر الحصة',
    'Code': 'الكود', 'Segment': 'الشريحة', 'For': 'لمين', 'State': 'الحالة', 'Expires': 'بتنتهي', 'Open': 'مفتوحة', 'Used': 'اتستخدمت', 'Revoked': 'اتسحبت', 'Expired': 'انتهت', 'Revoke': 'اسحب',
    'No invitations yet.': 'مفيش دعوات لسه.', 'New founding-member invitation': 'دعوة عضو مؤسس جديدة', 'Segment *': 'الشريحة *', 'Choose…': 'اختار…', 'Who it is for (your note)': 'لمين (ملاحظتك)',
    'Valid for (days)': 'صالحة لمدة (أيام)', 'Make invitation': 'اعمل الدعوة', 'Founding members in this segment *': 'الأعضاء المؤسسون في الشريحة دي *', 'Quota saved': 'اتحفظت الحصة',
    'Revoke this invitation?': 'تسحب الدعوة دي؟', 'The code stops working at once and its place in the segment is free again.': 'الكود بيبطل يشتغل فوراً ومكانه في الشريحة بيفضى.', 'Invitation revoked': 'اتسحبت الدعوة',
    'Invitation ready — copy it now': 'الدعوة جاهزة — انسخها دلوقتي', 'This code is shown only once. Send the link to the person it is for; they join by their own choice.': 'الكود ده بيظهر مرة واحدة بس. ابعت اللينك للشخص المقصود؛ هو اللي يختار ينضم.',
    'Link': 'اللينك', 'Copy code': 'انسخ الكود', 'Copy link': 'انسخ اللينك', 'Done': 'تمام', 'Copied': 'اتنسخ', 'Select the text and copy it': 'حدد النص وانسخه',
    '🏅 You are invited to be a founding member': '🏅 أنت مدعو تكون عضو مؤسس', 'Drugbox invites you to join its founding members as:': 'Drugbox بيدعوك تنضم لأعضائه المؤسسين كـ:',
    'Founders get the founder badge on their profile and 3 months of VIP for a company page they run. Joining is your choice — nothing changes unless you press Join.': 'المؤسسين بياخدوا شارة عضو مؤسس على البروفايل و3 شهور VIP لصفحة شركة بيديروها. الانضمام اختيارك — مفيش حاجة بتتغير إلا لو دوست انضم.',
    'Give the 3 VIP months to': 'ادّي الـ 3 شهور VIP لـ', 'Later — I will choose a company page': 'بعدين — هختار صفحة شركة', 'You can give the 3 VIP months to your company page later, from your profile.': 'تقدر تدّي الـ 3 شهور VIP لصفحة شركتك بعدين، من البروفايل.',
    'Join as a founding member': 'انضم كعضو مؤسس', 'Not now': 'مش دلوقتي', 'Welcome, founding member!': 'أهلاً بيك عضو مؤسس!', 'Welcome, founding member! Your company page is VIP for 3 months': 'أهلاً بيك عضو مؤسس! صفحة شركتك بقت VIP لمدة 3 شهور',
    'This invitation code is not valid': 'كود الدعوة ده مش صحيح', 'This invitation was already used.': 'الدعوة دي اتستخدمت قبل كده.', 'This invitation was withdrawn by Drugbox.': 'Drugbox سحب الدعوة دي.',
    'This invitation has expired — ask Drugbox for a new one.': 'الدعوة دي انتهت — اطلب دعوة جديدة من Drugbox.', 'You are already a founding member.': 'أنت عضو مؤسس بالفعل.', '🏅 Founding members ': '🏅 الأعضاء المؤسسون',
    '🏅 Founding member': '🏅 عضو مؤسس', '🎁 You have 3 VIP months to give to a company page you run.': '🎁 عندك 3 شهور VIP تدّيها لصفحة شركة بتديرها.', 'Choose a company': 'اختار شركة',
    'Your 3 VIP months': 'الـ 3 شهور VIP بتوعك', 'Company page *': 'صفحة الشركة *', 'This can be done once.': 'ده بيتعمل مرة واحدة.', 'Give the VIP months': 'ادّي شهور الـ VIP', 'Your company page is VIP for 3 months': 'صفحة شركتك بقت VIP لمدة 3 شهور',
    'Create or claim your company page first': 'اعمل أو اطلب صفحة شركتك الأول', 'Manufacturers': 'مصانع', 'Toll manufacturers / brand owners': 'تصنيع لدى الغير / أصحاب براند', 'Agencies': 'وكالات',
    'Distributors / warehouses': 'موزّعين / مخازن', 'Registration-file owners': 'أصحاب ملفات تسجيل', 'API / excipient suppliers': 'موردي خامات', 'Packaging suppliers': 'موردي عبوات وتغليف', 'Regulatory consultants': 'استشاريين تسجيل',
    'This segment is full — ask Drugbox': 'الشريحة دي اتملت — كلّم Drugbox', 'You are already a founding member': 'أنت عضو مؤسس بالفعل', 'This invitation was already used': 'الدعوة دي اتستخدمت قبل كده', 'This invitation was withdrawn by Drugbox': 'Drugbox سحب الدعوة دي',
    'This invitation has expired — ask Drugbox for a new one': 'الدعوة دي انتهت — اطلب دعوة جديدة من Drugbox', 'Too many tries — wait an hour and open your invitation link again': 'محاولات كتير — استنى ساعة وافتح لينك الدعوة تاني',
    'Give the VIP months to a company page you run (owner or admin)': 'ادّي شهور الـ VIP لصفحة شركة بتديرها (مالك أو أدمن)', 'Your 3 VIP months were already given to a company page': 'الـ 3 شهور VIP اتدّوا لصفحة شركة قبل كده',
    'Only founding members have the 3 VIP months': 'الـ 3 شهور VIP للأعضاء المؤسسين بس', 'One of Drugbox’s founding members': 'من أعضاء Drugbox المؤسسين',
    /* ask an expert */
    '🎤 Ask an expert': '🎤 اسأل خبير', '← All courses': '→ كل الدورات', 'Sessions arranged on request: ask for a topic, Drugbox invites an expert, you register, get a reminder and the questions and answers stay here.': 'جلسات بالطلب: اطلب موضوع، Drugbox يجيب خبير، تسجّل، يوصلك تذكير، والأسئلة والإجابات بتفضل هنا.',
    'Upcoming sessions': 'الجلسات الجاية', 'Ask for a topic': 'اطلب موضوع', 'Past sessions — questions and answers': 'جلسات فاتت — الأسئلة والإجابات', 'No session is scheduled yet — ask for a topic below.': 'مفيش جلسة متحددة لسه — اطلب موضوع تحت.',
    'No past sessions yet.': 'مفيش جلسات فاتت لسه.', 'asked': 'طلبوا', 'Request this topic': 'اطلب الموضوع ده', '✓ Requested · Withdraw': '✓ طلبته · اسحب الطلب', 'registered': 'مسجّل', 'seats left': 'مكان فاضي', '(Cairo)': '(القاهرة)', 'min': 'دقيقة',
    '✓ Took place': '✓ اتعملت', '✕ Cancelled ': '✕ اتلغت', '✓ Registered': '✓ مسجّل', '▶ Join the session': '▶ ادخل الجلسة', 'Cancel registration': 'ألغِ التسجيل', 'Register': 'سجّل', 'Full': 'كاملة',
    '💬 Questions and answers (': '💬 الأسئلة والإجابات (', 'Answer:': 'الإجابة:', 'Not answered yet': 'لسه متجاوبش', 'No questions yet.': 'مفيش أسئلة لسه.', 'Your question for the expert': 'سؤالك للخبير', 'Send question': 'ابعت السؤال',
    'Register to ask the expert a question.': 'سجّل عشان تسأل الخبير.', 'Registered — you will get a reminder a day and an hour before': 'اتسجّلت — هيوصلك تذكير قبلها بيوم وبساعة', 'Registration cancelled': 'اتلغى التسجيل',
    'The meeting link is not set yet — Drugbox will notify you': 'لينك الجلسة لسه متحطش — Drugbox هيبلغك', 'Question sent': 'اتبعت السؤال', 'Request withdrawn': 'اتسحب الطلب', 'Which topic? *': 'موضوع إيه؟ *', 'What do you want to know? (optional)': 'عايز تعرف إيه؟ (اختياري)',
    'Drugbox schedules a session when enough members ask — you are told when it is set.': 'Drugbox بيحدد جلسة لما أعضاء كفاية يطلبوا — هيتقالك لما تتحدد.', 'Send request': 'ابعت الطلب', 'Request sent — you will be told when a session is set': 'اتبعت الطلب — هيتقالك لما الجلسة تتحدد',
    'Write your question (at least 5 characters)': 'اكتب سؤالك (5 حروف على الأقل)', 'Register for the session to get its link': 'سجّل في الجلسة عشان تاخد اللينك', 'The link opens an hour before the session': 'اللينك بيفتح قبل الجلسة بساعة',
    'This session has ended — its questions and answers stay here': 'الجلسة دي خلصت — أسئلتها وإجاباتها فاضلة هنا', 'This session is full': 'الجلسة دي اتملت', 'This session has already started': 'الجلسة دي بدأت خلاص', 'Say which topic (a few words)': 'قول موضوع إيه (كام كلمة)',
    'You already asked for this topic': 'أنت طلبت الموضوع ده قبل كده', 'Register for the session to ask': 'سجّل في الجلسة عشان تسأل',
    'Buying a registration file safely': 'شراء ملف تسجيل بأمان', 'NFSA notification (supplements, food)': 'إخطار هيئة سلامة الغذاء', 'Agency and distribution contracts': 'عقد الوكالة والتوزيع', 'The toll-manufacturing card': 'كارت التصنيع لدى الغير',
    'Pricing and price increases': 'التسعير وزيادة الأسعار', 'Importing and the importer’s file': 'الاستيراد وملف المستورد', 'Cold chain': 'سلسلة التبريد', 'Authority labs and track & trace': 'معامل الهيئة والتتبع', 'Choosing a factory': 'اختيار مصنع', 'Another topic': 'موضوع تاني',
    'What members ask for, the sessions and their questions — members are told when a session on their topic is set and reminded a day and an hour before': 'الأعضاء بيطلبوا إيه، والجلسات وأسئلتها — الأعضاء بيتبلغوا لما تتحدد جلسة في موضوعهم وبيتفكروا قبلها بيوم وبساعة',
    '+ Schedule a session': '+ حدد جلسة', 'Requests by topic': 'الطلبات حسب الموضوع', 'Sessions': 'الجلسات', 'Topic': 'الموضوع', 'Asked': 'طلبوا', 'Notes': 'ملاحظات', 'No sessions yet.': 'مفيش جلسات لسه.',
    'Mark done': 'اتعملت', 'Cancel session': 'ألغِ الجلسة', '💬 Questions (': '💬 الأسئلة (', 'Edit session': 'تعديل الجلسة', 'Schedule an expert session': 'حدد جلسة مع خبير', 'Topic *': 'الموضوع *', 'Title (English) *': 'العنوان (إنجليزي) *',
    'Title (Arabic)': 'العنوان (عربي)', 'About': 'عن الجلسة', 'Expert *': 'الخبير *', 'The expert’s line': 'نبذة عن الخبير', 'Date (Cairo) *': 'التاريخ (القاهرة) *', 'Time (Cairo) *': 'الساعة (القاهرة) *', 'Minutes': 'الدقايق', 'Seats': 'الأماكن',
    'Meeting link (https://…) — given only to the registered, an hour before': 'لينك الجلسة (https://…) — بيوصل للمسجّلين بس، قبلها بساعة', 'Session saved': 'اتحفظت الجلسة', 'Session scheduled — the members who asked are told': 'اتحددت الجلسة — اللي طلبوا اتبلغوا',
    'Mark this session as done?': 'الجلسة دي اتعملت؟', 'Cancel this session?': 'تلغي الجلسة دي؟', 'Its questions and answers stay readable to every member.': 'أسئلتها وإجاباتها هتفضل متاحة لكل الأعضاء.', 'The registered members are told.': 'المسجّلين هيتبلغوا.', 'Back': 'رجوع',
    'Session marked done': 'الجلسة اتسجّلت إنها اتعملت', 'Session cancelled — the registered are told': 'اتلغت الجلسة — المسجّلين اتبلغوا', 'Answer': 'الإجابة', 'Send answer': 'ابعت الإجابة', 'Answer sent — the member is told': 'اتبعتت الإجابة — العضو اتبلغ',
    'Give the session a title': 'اكتب عنوان للجلسة', 'Name the expert': 'اكتب اسم الخبير', 'The meeting link must start with https://': 'لينك الجلسة لازم يبدأ بـ https://', 'Pick a time in the future': 'اختار وقت جاي',
    /* directory import */
    'Load companies from an official PUBLIC list (CSV) as unclaimed pages, marked as such; each row names its source. Duplicates (same registry number or name, English or Arabic) are skipped. Check first, then import': 'حمّل شركات من قايمة رسمية علنية (CSV) كصفحات من غير مالك ومتعلّمة كده؛ كل صف بيذكر مصدره. المكرر (نفس رقم السجل أو الاسم، إنجليزي أو عربي) بيتخطى. راجع الأول وبعدين استورد',
    '⬇ Sample CSV': '⬇ ملف CSV نموذجي', 'Check (nothing is written)': 'راجع (مفيش حاجة بتتكتب)', 'Import': 'استورد', 'Would create': 'هيتعمل', 'Created': 'اتعمل', 'Duplicates': 'مكرر', 'Invalid': 'غير صالح', 'Row': 'الصف', 'Company': 'الشركة', 'Result': 'النتيجة',
    'Already in the directory': 'موجودة في الدليل', 'Created — unclaimed': 'اتعملت — من غير مالك', 'Would be created — unclaimed': 'هتتعمل — من غير مالك', 'Choose the CSV file first': 'اختار ملف الـ CSV الأول',
    'No rows found — the first line must be the column names': 'مفيش صفوف — أول سطر لازم يكون أسماء الأعمدة', 'At most 2,000 rows per import': '2,000 صف بالكتير في المرة', 'The file is larger than 2 MB — split it': 'الملف أكبر من 2 ميجا — قسّمه',
    '1 company imported as an unclaimed page': 'اتستوردت شركة واحدة كصفحة من غير مالك',
    /* visitors */
    '👋 You are browsing as a visitor — sign in to contact companies, follow them or ask for a quote.': '👋 أنت بتتصفح كزائر — سجّل دخول عشان تكلّم الشركات أو تتابعها أو تطلب عرض سعر.', 'Sign in': 'تسجيل الدخول', 'Join Drugbox': 'انضم لـ Drugbox',
    '🏭 Browse the company directory without signing in': '🏭 تصفّح دليل الشركات من غير تسجيل', 'Sign in or join Drugbox to do this': 'سجّل دخول أو انضم لـ Drugbox عشان تعمل كده', 'Visitor': 'زائر',
    /* the specialty question */
    'Is this still your specialty?': 'ده لسه تخصصك؟', 'Ask me later': 'اسألني بعدين', 'Your specialty': 'تخصصك', 'Other…': 'تاني…', 'Your specialty, in your words': 'تخصصك بكلامك',
    'Your profile says': 'البروفايل بتاعك بيقول', '— the sign-up form used to choose it for everyone. Please confirm it or pick yours, so the right people, jobs and groups find you.': '— نموذج التسجيل كان بيختاره للكل. أكّده أو اختار تخصصك، عشان الناس والوظايف والجروبات المناسبة توصلك.', 'Write your specialty': 'اكتب تخصصك', 'Thanks — your specialty is confirmed': 'شكراً — تخصصك اتأكد', 'Your specialty is saved': 'اتحفظ تخصصك',
    'Loading…': 'جارٍ التحميل…'
  }, [
    [/^Published in (.+)$/, function (m) { return 'اتنشر في ' + m[1]; }], [/^Scheduled for (.+) \(Cairo\)$/, function (m) { return 'اتجدول لـ ' + m[1] + ' (القاهرة)'; }],
    [/^No posts about (.+) yet\.$/, function (m) { return 'مفيش منشورات عن ' + m[1] + ' لسه.'; }], [/^No listings about (.+) yet — try another area\.$/, function (m) { return 'مفيش إعلانات عن ' + m[1] + ' لسه — جرّب مجموعة تانية.'; }],
    [/^Request: (.+)$/, function (m) { return 'طلب: ' + m[1]; }], [/^Quota — (.+)$/, function (m) { return 'الحصة — ' + m[1]; }], [/^This segment is full \((\d+) of (\d+)\)$/, function (m) { return 'الشريحة دي اتملت (' + m[1] + ' من ' + m[2] + ')'; }],
    [/^(\d+) rows read — check them first$/, function (m) { return 'اتقرا ' + m[1] + ' صف — راجعهم الأول'; }], [/^(\d+) companies imported as unclaimed pages$/, function (m) { return 'اتستوردت ' + m[1] + ' شركة كصفحات من غير مالك'; }],
    [/^posted in "(.+)"$/, function (m) { return 'نشر في "' + m[1] + '"'; }], [/^(\d+) new posts in "(.+)"$/, function (m) { return m[1] + ' منشورات جديدة في "' + m[2] + '"'; }],
    [/^An expert session you asked for: "(.+)"$/, function (m) { return 'جلسة خبير طلبتها: "' + m[1] + '"'; }], [/^The expert session "(.+)" moved to a new time$/, function (m) { return 'جلسة الخبير "' + m[1] + '" اتغير ميعادها'; }],
    [/^The expert session "(.+)" was cancelled$/, function (m) { return 'جلسة الخبير "' + m[1] + '" اتلغت'; }], [/^Tomorrow: the expert session "(.+)"$/, function (m) { return 'بكرة: جلسة الخبير "' + m[1] + '"'; }],
    [/^In an hour: the expert session "(.+)" — the link is open$/, function (m) { return 'كمان ساعة: جلسة الخبير "' + m[1] + '" — اللينك مفتوح'; }], [/^Your question in "(.+)" was answered$/, function (m) { return 'سؤالك في "' + m[1] + '" اتجاوب'; }],
    [/^This post is already (\w+)$/, function (m) { return 'المنشور ده ' + ({ published: 'اتنشر', cancelled: 'اتلغى', failed: 'ماتنشرش' }[m[1]] || m[1]) + ' بالفعل'; }]
  ]);
})();
