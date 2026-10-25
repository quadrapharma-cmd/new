/* ===== AREA w-trust: trust, safety and groups (W-08, W-10, W-16, W-17, W-19, W-20, W-25, W-44) =====
   Drugbox trade is business-to-business before the pharmacy. This layer adds, in the approved visual language:
   · the trade profile (role, company, governorate, what you sell / buy) — asked before a member's first trade offer, shown as a
     card on the profile, in a group's join requests and with the trust line (member since, verified phone, new account)
   · who stands behind an offer: «Verified company» / «Individual» / «Broker» (owner, authorisation, commission) on the offer
     cards, and "Posting as" in Create Listing — a company page posts as the company only with the Drugbox badge
   · posts and offers that look out of scope (sales to patients / pharmacies / the public, controlled substances, import for
     others, sham papers, invite links) wait for Drugbox review — the author sees "Waiting for review" and is told why
   · "Report a trade problem" with evidence; the member reported replies; two Drugbox moderators decide
   · a verified phone that stays private
   · group admin tools (rules on join, daily limit, slow mode, duplicates, outside links, posts reviewed first, a category)
     and invite links the group's admin shares — every member joins by themselves; "Drugbox partner group"
   Data goes through window.dxTrust: the sample implementation below keeps everything in this browser (the demo); the live app
   replaces it with the database (web/src/live/wtrust.js). The rules for holding a post are the database's (0091) — the demo
   copy below is only for the demo. */
(function () {
  var D = window.DBK, C = window.dxCore; if (!D || !C) return;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function $(id) { return document.getElementById(id); }
  function me() { return window.ME || {}; }
  function ar() { return document.documentElement.lang === 'ar'; }
  function toast(m) { (window.toast || D.toast)(m); }
  function live() { return !!window.dxLive; }
  function T(s) { return window.dxT ? window.dxT(s) : s; }

  var ROLES = [['manufacturer', 'Manufacturer'], ['toll_manufacturer', 'Toll manufacturer'], ['file_owner', 'Registration-file / brand owner'], ['importer_exporter', 'Importer / exporter'],
    ['distributor', 'Distributor / agent / warehouse'], ['supplier', 'API / excipient / packaging / equipment supplier'], ['service_provider', 'Service provider'], ['consultant', 'Consultant / broker']];
  var GOVS = ['Cairo', 'Giza', 'Alexandria', 'Qalyubia', 'Sharqia', 'Dakahlia', 'Gharbia', 'Monufia', 'Beheira', 'Kafr El Sheikh', 'Damietta', 'Port Said', 'Ismailia', 'Suez',
    'North Sinai', 'South Sinai', 'Red Sea', 'Matrouh', 'New Valley', 'Faiyum', 'Beni Suef', 'Minya', 'Asyut', 'Sohag', 'Qena', 'Luxor', 'Aswan', 'Outside Egypt'];
  var REASONS = [['non_payment', 'Did not pay'], ['non_delivery', 'Did not deliver'], ['counterfeit', 'Counterfeit or not as agreed'], ['misrepresentation', 'Not who they said they were'],
    ['sham_papers', 'Sham or forged papers'], ['other', 'Something else']];
  function roleName(r) { var x = ROLES.filter(function (o) { return o[0] === r; })[0]; return x ? x[1] : r; }
  function reasonName(r) { var x = REASONS.filter(function (o) { return o[0] === r; })[0]; return x ? x[1] : r; }
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function monthYear(iso) { var d = new Date(iso); return isNaN(d) ? '' : MON[d.getMonth()] + ' ' + d.getFullYear(); }
  function daysSince(iso) { var d = Date.parse(iso); return isNaN(d) ? null : Math.max(0, Math.floor((Date.now() - d) / 864e5)); }

  /* ── the words that send a post to Drugbox review (demo copy of 0091's rules; the database decides in the live app) ── */
  function norm(s) { return String(s || '').toLowerCase().replace(/[ً-ٰٟـ​-‏‪-‮⁦-⁩﻿­]/g, '')
    .replace(/[أإآٱ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي').replace(/\s+/g, ' '); }
  function arw(words, pre) { return new RegExp('(^|[^ء-ي])(و|ف)?' + (pre ? '(ب|ل|ك)?(ال|ل)?' : '') + '(' + words + ')([^ء-ي]|$)'); }
  var RULES = [
    ['retail', /\b(for|to) (a|my|the|our|this) patient\b|\bpatient (needs|is looking|urgently)|\b(retail|consumer) (sale|sales|price|customers?|buyers?)\b|\b(sell|selling|sale|supply|supplying|deliver|delivery) (to|for) (the )?(public|consumers?|pharmac(y|ies))\b|\bhome delivery\b|\b(single|one|loose|open(ed)?) (box|pack|strip)s?\b/],
    ['retail', arw('لمريض|للمريض|لمريضه|للمريضه|للعيان|لعيان|حاله انسانيه|حالات انسانيه|محتاج دوا|محتاجه دوا|روشته|بالروشته|الروشته|قطاعي|بالقطاعي|للجمهور|توصيل للمنازل|توصيل للبيت|دليفري|للصيدليات|لصيدليه|لصيدليتي|بيع للصيدليات|توزيع علي الصيدليات|طلبيه صيدليه|علبه واحده|شريط واحد|علب مفتوحه|علبه مفتوحه|فرط|بالفرط|بالشريط')],
    ['controlled', /\b(tramadol|tapentadol|pregabalin|lyrica|codeine|morphine|fentanyl|oxycodone|methadone|alprazolam|xanax|clonazepam|rivotril|diazepam|valium|zolpidem|ketamine|methylphenidate|ritalin|captagon|fenethylline|nalbuphine|pethidine|buprenorphine)\b|\b(controlled (substances?|drugs?|medicines?)|psychotropics?|narcotics?)\b/],
    ['controlled', arw('ترامادول|ترامال|تامول|ليريكا|بريجابالين|كودايين|كوديين|مورفين|فنتانيل|زاناكس|زانكس|ريفوتريل|كلونازيبام|فاليوم|ديازيبام|كيتامين|ريتالين|كبتاجون|نالبوفين|بيثيدين', true)],
    ['controlled', arw('ادويه الجدول|ادويه جدول|جدول اول|جدول ثاني|جدول تاني|من الجدول|مخدر|مخدرات|المخدرات|ادويه نفسيه|موثر عقلي|موثرات عقليه|الموثرات العقليه')],
    ['import', /\bimport(ing)? (on behalf of|for others|for clients|for a client|under (my|our|your) licen[cs]e)|\b(rent|hire|lend)(ing)? (an |my |our )?import (licen[cs]e|card|registration)/],
    ['import', arw('استيراد لحساب|استيراد للغير|استيراد باسم|استيراد لصالح|استيراد علي سجلي|استيراد علي سجلنا|استيراد علي بطاقتي|استيراد علي بطاقتنا|استيراد علي رخصتي|استيراد علي رخصتنا|تاجير سجل|تاجير بطاقه استيراد|بطاقه استيراديه للايجار|سجل مستوردين للايجار|ايجار سجل')],
    ['sham', /\b(sham|fake|fictitious) (contracts?|invoices?|tenders?|coas?|certificates?|papers?)\b|\b(backdated|forged) (contracts?|invoices?|papers?|documents?|certificates?)\b/],
    ['sham', arw('عقد صوري|عقود صوريه|فاتوره وهميه|فواتير وهميه|فواتير مضروبه|شهاده مضروبه|شهادات مضروبه|ورق مضروب|اوراق مضروبه|مزوره|مزور|تزوير')],
    ['invite', /chat\.whatsapp\.com|wa\.me\/|whatsapp\.com\/(channel|invite)|t\.me\/|telegram\.(me|dog)\/|telegram\.org\/joinchat|discord\.(gg|com\/invite)|invite\.viber\.com|vb\.me\//]
  ];
  function topics(s) { var t = norm(s), out = []; RULES.forEach(function (r) { if (r[1].test(t) && out.indexOf(r[0]) < 0) out.push(r[0]); }); return out; }
  var TOPIC = { retail: 'a sale to patients, pharmacies or the public (Drugbox is business-to-business)', controlled: 'controlled substances', import: 'importing for others',
    sham: 'sham or forged papers', invite: 'an invite link to an outside group' };
  function why(t) { return (t || []).map(function (x) { return TOPIC[x] || x; }).join(', '); }
  var LINK_RX = RULES[RULES.length - 1][1];

  /* ── the sample implementation (demo): this browser ── */
  function dget(k, d) { var v = D.store.get(k, d); return v == null ? d : v; }
  function dset(k, v) { D.store.set(k, v); }
  function sampleSince(uid) { if (uid === me().id) return '2024-03-12T09:00:00Z'; var n = +uid || 0; if (n === 6) return new Date(Date.now() - 9 * 864e5).toISOString();   /* sample people: one new account */
    return new Date(Date.UTC(2023 + (n % 3), (n * 5) % 12, 1 + (n % 27))).toISOString(); }
  function wait(x) { return new Promise(function (r) { setTimeout(function () { r(x); }, 60); }); }
  var demo = {
    live: false,
    card: function (uid) {
      var tp = dget('wtTrade', {}), ph = dget('wtPhone', {}), reps = dget('wtReports', []), mine = dget('wtMyOffers', 0);
      return wait({ member_since: sampleSince(uid), new_account: daysSince(sampleSince(uid)) < 30, profile: tp[uid] || null, phone_verified: !!ph[uid],
        offers: uid === me().id ? (mine || 0) + 3 : 0, reports_upheld: reps.filter(function (r) { return r.uid === uid && r.status === 'upheld'; }).length, buyer_rating: null });
    },
    myProfile: function () { return Promise.resolve(dget('wtTrade', {})[me().id] || null); },
    saveProfile: function (p) { var tp = dget('wtTrade', {}); tp[me().id] = p; dset('wtTrade', tp); return wait(p); },
    phoneStart: function (phone) { var d = String(phone || '').replace(/[\s().-]/g, '').replace(/[٠-٩]/g, function (c) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(c); });
      if (!/^(\+20|0020|20)?0?1[0125]\d{8}$/.test(d) && !/^(\+|00)[1-9]\d{6,14}$/.test(d)) return Promise.reject(new Error('Enter a mobile number (e.g. 010 1234 5678 or +971 50 123 4567)'));
      var code = String(100000 + Math.floor(Math.random() * 900000)); dset('wtPhoneCode', { code: code, phone: d }); return wait({ to: d.slice(0, 4) + '•••' + d.slice(-2), demoCode: code }); },
    phoneConfirm: function (code) { var c = dget('wtPhoneCode', null); if (!c || String(code).replace(/\D/g, '') !== c.code) return Promise.reject(new Error('That code is not right'));
      var ph = dget('wtPhone', {}); ph[me().id] = true; dset('wtPhone', ph); dset('wtPhoneCode', null); return wait({ verified: true }); },
    report: function (uid, reason, details, files) { var l = dget('wtReports', []);
      if (l.some(function (r) { return r.uid === uid && r.status === 'open'; })) return Promise.reject(new Error('You already have an open report about this member — Drugbox is checking it'));
      var u = window.U ? window.U(uid) : {}; l.push({ id: 'R' + Date.now(), uid: uid, name: u.name || 'Member', reason: reason, details: details, files: (files || []).map(function (f) { return f.name; }), status: 'open', at: new Date().toISOString(), votes: [] });
      dset('wtReports', l); return wait(true); },
    myReports: function () { return wait(dget('wtReports', []).map(function (r) { return { id: r.id, side: 'sent', reason: r.reason, details: r.details, status: r.status, reported_name: r.name, reporter_name: me().name, created_at: r.at, reply: r.reply || '' }; })); },
    reply: function () { return Promise.reject(new Error('In the demo nobody has reported you — this works in the live app')); },
    myHeld: function () { return Promise.resolve(dget('wtHeld', []).filter(function (h) { return h.status === 'held'; })); },
    hold: function (kind, id, text, t) { var l = dget('wtHeld', []); l.push({ id: 'H' + Date.now(), kind: kind, item: id, excerpt: String(text || '').slice(0, 200), topics: t, status: 'held', at: new Date().toISOString() }); dset('wtHeld', l); },
    rateBuyer: function (id, stars, note) { var r = dget('wtBuyerRatings', {}); if (r[id]) return Promise.reject(new Error('You already rated this buyer')); var d = window.dxDeals && window.dxDeals.get(id);
      r[id] = { stars: stars, note: note, buyer: d && d.from ? (d.from.slug || d.from.name) : '' }; dset('wtBuyerRatings', r); return wait(true); },
    buyerRated: function (id) { var r = dget('wtBuyerRatings', {})[id]; return Promise.resolve(r ? r.stars : null); },
    buyerRating: function (from) { var all = dget('wtBuyerRatings', {}), k = from.slug || from.name, l = Object.keys(all).map(function (x) { return all[x]; }).filter(function (x) { return x.buyer === k; });
      return Promise.resolve(l.length ? { n: l.length, avg: (l.reduce(function (a, x) { return a + x.stars; }, 0) / l.length).toFixed(1) } : null); },
    /* groups */
    tools: function (g) { return Object.assign({ rules_required: false, daily_post_limit: null, slow_mode_minutes: null, block_duplicates: true, block_links: false, review_posts: false, require_category: false, partner: false }, (dget('wtGroupTools', {})[g.key] || {})); },
    saveTools: function (g, t) { var all = dget('wtGroupTools', {}); all[g.key] = Object.assign({}, all[g.key] || {}, t); dset('wtGroupTools', all); return wait(true); },
    accepted: function (g) { return !!(dget('wtRulesOk', {})[g.key]); },
    acceptRules: function (g) { var a = dget('wtRulesOk', {}); a[g.key] = new Date().toISOString(); dset('wtRulesOk', a); return wait(true); },
    links: function (g) { return wait((dget('wtLinks', {})[g.key] || []).slice()); },
    makeLink: function (g, days, max) { var all = dget('wtLinks', {}), l = all[g.key] = all[g.key] || [];
      if (l.filter(function (x) { return !x.revoked_at; }).length >= 5) return Promise.reject(new Error('A group keeps at most 5 active invite links — stop one first'));
      var tok = Array.from({ length: 40 }, function () { return '0123456789abcdef'[Math.floor(Math.random() * 16)]; }).join('');
      var x = { id: tok.slice(0, 8), token: tok, uses: 0, max_uses: max || null, expires_at: days ? new Date(Date.now() + days * 864e5).toISOString() : null, created_at: new Date().toISOString(), group: g.title };
      l.unshift(x); dset('wtLinks', all); return wait(x); },
    stopLink: function (g, id) { var all = dget('wtLinks', {}); (all[g.key] || []).forEach(function (x) { if (x.id === id) x.revoked_at = new Date().toISOString(); }); dset('wtLinks', all); return wait(true); },
    preview: function (token) { var all = dget('wtLinks', {}), hit = null; Object.keys(all).forEach(function (k) { (all[k] || []).forEach(function (x) { if (x.token === token) hit = { key: k, x: x }; }); });
      if (!hit) return wait(null);
      var sd = [].concat((window.dxGroups && window.dxGroups.seed) || []).filter(function (x) { return x && x.k === hit.key; })[0], card = document.querySelector('#gx .gcard[data-gk="' + hit.key + '"]'), b = card && card.querySelector('.gcard-btn');
      return wait({ key: hit.key, name: hit.x.group, rules: sd ? sd.rules : [], rules_required: !!demo.tools({ key: hit.key }).rules_required, member: !!(b && b.classList.contains('btn-joined') && !b.dataset.gpq),
        ok: !hit.x.revoked_at && (!hit.x.expires_at || Date.parse(hit.x.expires_at) > Date.now()) && (!hit.x.max_uses || hit.x.uses < hit.x.max_uses) }); },
    joinByLink: function (token, ok) { var all = dget('wtLinks', {}), hit = null; Object.keys(all).forEach(function (k) { (all[k] || []).forEach(function (x) { if (x.token === token) hit = { key: k, x: x }; }); });
      if (!hit || hit.x.revoked_at) return Promise.reject(new Error('This invite link no longer works — ask the group\'s admin for a new one'));
      if (demo.tools({ key: hit.key }).rules_required && !ok) return Promise.reject(new Error('Read and accept the group\'s rules first'));
      hit.x.uses = (hit.x.uses || 0) + 1; dset('wtLinks', all); var card = document.querySelector('#gx .gcard[data-gk="' + hit.key + '"]');
      if (card && window.dxGroups && window.dxGroups.joinClick) { var b = card.querySelector('.gcard-btn'); if (b && !b.classList.contains('btn-joined')) window.dxGroups.joinClick(b); }
      return wait('member'); },
    pending: function (g) { return wait((dget('wtGroupPending', {})[g.key] || []).filter(function (p) { return !p.done; })); },
    publish: function (g, id, yes) { var all = dget('wtGroupPending', {}); (all[g.key] || []).forEach(function (p) { if (String(p.id) === String(id)) p.done = yes ? 'published' : 'declined'; }); dset('wtGroupPending', all); return wait(yes ? 'published' : 'declined'); },
    partnerAsk: function (g, note) { var all = dget('wtPartner', {}); all[g.key] = { note: note, status: 'pending', name: g.title, at: new Date().toISOString() }; dset('wtPartner', all); return wait(true); },
    partnerOf: function (g) { return (dget('wtPartner', {})[g.key] || null); }
  };
  window.dxTrust = window.dxTrust || demo;
  function S() { return window.dxTrust; }
  window.dxTrustUI = { topics: topics, why: why, norm: norm, roleName: roleName, reasonName: reasonName, demo: demo };

  /* ── the trade profile window ── */
  function opts(list, cur, ph) { return (ph ? '<option value="">' + esc(ph) + '</option>' : '') + list.map(function (o) { var v = Array.isArray(o) ? o[0] : o, l = Array.isArray(o) ? o[1] : o; return '<option value="' + esc(v) + '"' + (v === cur ? ' selected' : '') + '>' + esc(l) + '</option>'; }).join(''); }
  function tradeProfileDialog(after) {
    S().myProfile().then(function (p) {
      p = p || {};
      D.modal({ title: 'Your trade profile', body:
        '<div class="dbk-note">Drugbox trade is between companies and businesses — before the pharmacy. Your trade card shows with your offers, so others know who they trade with. Pharmacists are welcome as members (network, jobs, training).</div>' +
        '<div class="dbk-f"><label for="wtRole">What you do in the trade *</label><select id="wtRole" data-req>' + opts(ROLES, p.role, 'Choose…') + '</select></div>' +
        '<div class="dbk-f"><label for="wtCo">Company or trade name</label><input id="wtCo" maxlength="120" value="' + esc(p.company || me().company || '') + '" placeholder="e.g. Nile Pharma Trading"></div>' +
        '<div class="dbk-f"><label for="wtGov">Governorate *</label><select id="wtGov" data-req>' + opts(GOVS, p.governorate, 'Choose…') + '</select></div>' +
        '<div class="dbk-f"><label for="wtSells">What you sell or offer</label><input id="wtSells" maxlength="300" value="' + esc(p.sells || '') + '" placeholder="e.g. APIs, excipients, toll manufacturing capacity"></div>' +
        '<div class="dbk-f"><label for="wtBuys">What you buy or look for</label><input id="wtBuys" maxlength="300" value="' + esc(p.buys || '') + '" placeholder="e.g. registration files, distribution rights"></div>' +
        '<div class="dx-set-msg err" id="wtTpErr" role="alert"></div>',
        primary: { label: 'Save trade profile', onClick: function (bx, close) {
          if (!D.requireFields(bx)) return false;
          var v = { role: bx.querySelector('#wtRole').value, company: bx.querySelector('#wtCo').value.trim(), governorate: bx.querySelector('#wtGov').value, sells: bx.querySelector('#wtSells').value.trim(), buys: bx.querySelector('#wtBuys').value.trim() };
          var er = bx.querySelector('#wtTpErr');
          if (v.sells.length < 2 && v.buys.length < 2) { er.textContent = T('Say what you sell or what you buy'); er.style.display = 'block'; bx.querySelector('#wtSells').classList.add('dbk-err'); return false; }
          var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
          S().saveProfile(v).then(function () { close(); toast('Trade profile saved'); MYTP = v; repaintProfile(); if (after) after(v); },
            function (e) { if (ok) ok.disabled = false; er.textContent = T((e && e.message) || 'Could not save — try again'); er.style.display = 'block'; });
          return false; } } });
    });
  }
  var MYTP = undefined;
  /* before a trade offer: the trade profile first (the database refuses an offer without it: DX410) */
  function needTradeProfile(go) {
    S().myProfile().then(function (p) { MYTP = p; if (p) return go();
      D.modal({ title: 'First, your trade profile', body: '<p>Before your first trade offer, tell the trade who you are: your role, company, governorate and what you buy or sell. It takes a minute and shows with your offers.</p>',
        primary: { label: 'Add my trade profile', onClick: function () { setTimeout(function () { tradeProfileDialog(function () { go(); }); }, 30); } } });
    }, function () { go(); });
  }
  window.dxTrustUI.needTradeProfile = needTradeProfile; window.dxTrustUI.tradeProfileDialog = tradeProfileDialog;

  /* ── the profile: the trust line and the trade card ── */
  function chips(c, own) {
    var h = [];
    if (c.member_since) h.push('<span class="wt-chip">🗓 <span>Member since</span> <span data-noi18n>' + esc(monthYear(c.member_since)) + '</span></span>');
    if (c.phone_verified) h.push('<span class="wt-chip wt-ok">📱 Phone verified</span>');
    else if (own) h.push('<button type="button" class="wt-chip wt-act" data-wt="phone">📱 Verify my phone</button>');
    if (c.new_account && !own) h.push('<span class="wt-chip wt-new" title="Joined less than 30 days ago">🆕 New account</span>');
    if (c.reports_upheld) h.push('<span class="wt-chip wt-warn">⚠️ <span>' + c.reports_upheld + (c.reports_upheld === 1 ? ' report upheld by Drugbox' : ' reports upheld by Drugbox') + '</span></span>');
    return h.join('');
  }
  function tradeCardHtml(c, own) {
    var p = c && c.profile, h = '<div class="card wt-tcard"><div class="wt-th"><b>🏷 Trade profile</b>' + (own ? '<button type="button" class="wt-link" data-wt="edit">' + (p ? 'Edit' : '+ Add') + '</button>' : '') + '</div>';
    if (p) h += '<div class="wt-trole">' + esc(roleName(p.role)) + '</div>' + (p.company ? '<div class="wt-tline" data-noi18n>' + esc(p.company) + '</div>' : '') +
      '<div class="wt-tline">📍 <span>' + esc(p.governorate) + '</span></div>' + (p.sells ? '<div class="wt-tkv"><span>Sells</span> <span data-noi18n>' + esc(p.sells) + '</span></div>' : '') + (p.buys ? '<div class="wt-tkv"><span>Buys</span> <span data-noi18n>' + esc(p.buys) + '</span></div>' : '');
    else h += '<div class="wt-tline wt-muted">' + (own ? 'Add your trade profile before your first trade offer.' : 'No trade profile yet.') + '</div>';
    if (c && c.offers) h += '<div class="wt-tline wt-muted">' + c.offers + (c.offers === 1 ? ' offer published' : ' offers published') + '</div>';
    if (c && c.buyer_rating && c.buyer_rating.n) h += '<div class="wt-tline">★ ' + esc(c.buyer_rating.avg) + ' <span>as a buyer</span> (' + c.buyer_rating.n + ')</div>';
    if (own) h += '<button type="button" class="wt-link wt-mine" data-wt="myreports">⚖️ My trade reports</button>';
    else h += '<button type="button" class="wt-link wt-rep" data-wt="report">⚑ Report a trade problem</button>';
    return h + '</div>';
  }
  var PROF = { uid: null };
  function repaintProfile() { var c = $('content'); if (c && PROF.uid != null && document.body.getAttribute('data-page') === 'profile') paintTrust(c, PROF.uid); }
  function paintTrust(c, uid) {
    var own = uid === me().id;
    S().card(uid).then(function (card) {
      if (!card || PROF.uid !== uid || !c.isConnected) return;
      var hl = c.querySelector('.profile-headline'), loc = hl && hl.nextElementSibling;
      var line = c.querySelector('.wt-line'); if (!line && loc) { loc.insertAdjacentHTML('afterend', '<div class="wt-line"></div>'); line = c.querySelector('.wt-line'); }
      if (line) line.innerHTML = chips(card, own);
      var side = [].filter.call(c.querySelectorAll('div[style*="width:260px"]'), function (d) { return d.querySelector('.card'); })[0];
      var old = c.querySelector('.wt-tcard'); if (old) old.remove();
      if (side) side.insertAdjacentHTML('afterbegin', tradeCardHtml(card, own)); else if (line) line.insertAdjacentHTML('afterend', tradeCardHtml(card, own));
      if (window.dxI18nAttrs) window.dxI18nAttrs(c);
    }, function () {});
  }
  var oProfile = window.renderProfile;
  if (typeof oProfile === 'function') window.renderProfile = function (c, uid) { var r = oProfile.apply(this, arguments); PROF.uid = uid == null ? me().id : uid; paintTrust(c, PROF.uid); return r; };

  /* ── phone: a code to the number, typed back (the number stays private) ── */
  function phoneDialog() {
    D.modal({ title: 'Verify your phone', body: '<div class="dbk-note">We send a 6-digit code by SMS. Your number stays private — members see only that it is verified.</div>' +
      '<div class="dbk-f"><label for="wtPh">Mobile number *</label><input id="wtPh" type="tel" inputmode="tel" data-req maxlength="20" placeholder="010 1234 5678" value="' + esc(me().phone || '') + '"></div>' +
      '<div class="dx-set-msg err" id="wtPhErr" role="alert"></div>',
      primary: { label: 'Send code', onClick: function (bx, close) {
        if (!D.requireFields(bx)) return false; var er = bx.querySelector('#wtPhErr'), ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        S().phoneStart(bx.querySelector('#wtPh').value).then(function (r) { close(); codeDialog(r); }, function (e) { if (ok) ok.disabled = false; er.textContent = T((e && e.message) || 'Could not send the code'); er.style.display = 'block'; });
        return false; } } });
  }
  function codeDialog(r) {
    D.modal({ title: 'Enter the code', body: '<p><span>We sent a code to</span> <b data-noi18n dir="ltr">' + esc(r.to || '') + '</b>. <span>It expires in 10 minutes.</span></p>' +
      (r.demoCode ? '<div class="dbk-note">Demo: no SMS is sent — your code is <b data-noi18n>' + esc(r.demoCode) + '</b></div>' : '') +
      '<div class="dbk-f"><label for="wtCode">Code *</label><input id="wtCode" inputmode="numeric" autocomplete="one-time-code" data-req maxlength="6" placeholder="123456"></div><div class="dx-set-msg err" id="wtCodeErr" role="alert"></div>',
      primary: { label: 'Verify', onClick: function (bx, close) {
        if (!D.requireFields(bx)) return false; var er = bx.querySelector('#wtCodeErr'), ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        S().phoneConfirm(bx.querySelector('#wtCode').value).then(function () { close(); toast('Your phone is verified — the number stays private'); repaintProfile(); },
          function (e) { if (ok) ok.disabled = false; er.textContent = T((e && e.message) || 'That code is not right'); er.style.display = 'block'; });
        return false; } } });
  }

  /* ── a trade problem: reported with evidence; the member replies; two Drugbox moderators decide ── */
  function reportDialog(uid) {
    var u = window.U ? window.U(uid) : { name: 'this member' };
    D.modal({ title: 'Report a trade problem', body:
      '<div class="dbk-note">Drugbox tells <b data-noi18n>' + esc(u.name) + '</b> and lets them answer with their side. Two Drugbox moderators decide. Nothing is posted publicly — an upheld report shows only as a count on their trade card.</div>' +
      '<div class="dbk-f"><label for="wtRr">What happened *</label><select id="wtRr" data-req>' + opts(REASONS, '', 'Choose…') + '</select></div>' +
      '<div class="dbk-f"><label for="wtRd">Details * (dates, amounts, the deal)</label><textarea id="wtRd" data-req maxlength="2000" rows="4" placeholder="e.g. Paid 50% in advance on 2 Sept, nothing delivered by 15 Oct"></textarea></div>' +
      '<div class="dbk-f"><label for="wtRf">Evidence * (1–5 files: invoice, chat, delivery note)</label><input id="wtRf" type="file" multiple accept="application/pdf,image/jpeg,image/png,image/webp"></div>' +
      '<div class="dx-set-msg err" id="wtRErr" role="alert"></div>',
      primary: { label: 'Send to Drugbox', onClick: function (bx, close) {
        if (!D.requireFields(bx)) return false;
        var er = bx.querySelector('#wtRErr'), files = [].slice.call(bx.querySelector('#wtRf').files || []), det = bx.querySelector('#wtRd').value.trim();
        function bad(m, f) { er.textContent = T(m); er.style.display = 'block'; if (f) bx.querySelector(f).classList.add('dbk-err'); return false; }
        if (det.length < 20) return bad('Say what happened in at least 20 characters', '#wtRd');
        if (!files.length) return bad('Attach at least one piece of evidence (an invoice, a chat, a delivery note…)', '#wtRf');
        if (files.length > 5) return bad('At most 5 files', '#wtRf');
        if (files.some(function (f) { return f.size > 10 * 1024 * 1024; })) return bad('Each file can be up to 10 MB', '#wtRf');
        var ok = bx.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        S().report(uid, bx.querySelector('#wtRr').value, det, files).then(function () { close(); toast('Sent — Drugbox will check it, and ' + u.name + ' can reply'); },
          function (e) { if (ok) ok.disabled = false; bad((e && e.message) || 'Could not send the report — try again'); });
        return false; } } });
  }
  var ST = { open: '⏳ Being checked', upheld: '⚠️ Upheld', dismissed: '✓ Dismissed' };
  function myReportsDialog(focusId) {
    S().myReports().then(function (list) {
      var h = list.length ? list.map(function (r) {
        var about = r.side === 'about_me';
        return '<div class="wt-rep-row" data-rid="' + esc(r.id) + '"><div><b>' + (about ? '<span>About you, from</span> <span data-noi18n>' + esc(r.reporter_name || 'a member') + '</span>' : '<span>You reported</span> <span data-noi18n>' + esc(r.reported_name || 'a member') + '</span>') + '</b> · <span>' + esc(reasonName(r.reason)) + '</span> · <span>' + esc(ST[r.status] || r.status) + '</span></div>' +
          '<p data-noi18n>“' + esc(r.details) + '”</p>' + (r.reply ? '<p class="wt-reply"><span>Reply:</span> <span data-noi18n>“' + esc(r.reply) + '”</span></p>' : '') +
          (about && r.status === 'open' ? '<div class="dbk-f"><label for="wtRp' + esc(r.id) + '">Your side *' + (r.reply_by ? ' <span>(reply by</span> <span data-noi18n>' + esc(r.reply_by) + '</span>)' : '') + '</label><textarea id="wtRp' + esc(r.id) + '" maxlength="2000" rows="3">' + esc(r.reply || '') + '</textarea></div>' +
            '<div class="dbk-f"><label for="wtRpf' + esc(r.id) + '">Your files (optional, up to 5)</label><input id="wtRpf' + esc(r.id) + '" type="file" multiple accept="application/pdf,image/jpeg,image/png,image/webp"></div><button type="button" class="dbk-btn p" data-wtreply="' + esc(r.id) + '">Send my reply</button>' : '') + '</div>';
      }).join('') : '<p>No trade reports — none sent and none about you.</p>';
      var m = D.modal({ title: 'My trade reports', body: '<div class="wt-reps">' + h + '</div>', secondary: 'Close' });
      if (focusId) { var row = m.el.querySelector('[data-rid="' + focusId + '"] textarea'); if (row) setTimeout(function () { row.focus(); }, 60); }
      m.el.addEventListener('click', function (e) {
        var b = e.target.closest('[data-wtreply]'); if (!b) return; var id = b.dataset.wtreply, ta = m.el.querySelector('#wtRp' + id), fi = m.el.querySelector('#wtRpf' + id);
        if (!ta || ta.value.trim().length < 10) { if (ta) ta.classList.add('dbk-err'); toast('Write your side in at least 10 characters'); return; }
        b.disabled = true; S().reply(id, ta.value.trim(), [].slice.call((fi && fi.files) || []).slice(0, 5)).then(function () { m.close(); toast('Your reply is with Drugbox — the moderators read both sides'); },
          function (er) { b.disabled = false; toast((er && er.message) || 'Could not send — try again'); });
      });
      if (window.dxI18nAttrs) window.dxI18nAttrs(m.el);
    }, function (e) { toast((e && e.message) || 'Could not load the reports'); });
  }
  window.dxTrustUI.myReports = myReportsDialog; window.dxTrustUI.report = reportDialog; window.dxTrustUI.phone = phoneDialog;
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-wt]'); if (!b) return; var k = b.dataset.wt;
    if (k === 'edit') { e.preventDefault(); tradeProfileDialog(); }
    else if (k === 'phone') { e.preventDefault(); phoneDialog(); }
    else if (k === 'report') { e.preventDefault(); if (PROF.uid != null) reportDialog(PROF.uid); }
    else if (k === 'myreports') { e.preventDefault(); myReportsDialog(); }
  });

  /* ===== part 2 (offers, holds, groups, Admin → Review) follows in wtrust2.js ===== */
})();
