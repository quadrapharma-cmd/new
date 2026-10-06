/* Drugbox deals engine — every interaction between two companies is one deal.
   A deal has two parties (from → to), a type, a status that moves through a state machine,
   and a timeline of events. Each side sees it from its own angle and gets only the actions its role allows.
   In the demo, when the other side is not a company you own, "Simulate their reply (demo)" performs their next step openly. */
(function () {
  var D = window.DBK; if (!D) return;
  function X() { return window.dxDir; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  function toast(m) { D.toast(m); }
  var __A = /^(deals|created_companies|reports|dossiers|surplus_new|groups_new|follows|saved_searches|my_requests|activity_.*|inbox_.*)$/, __O = /^(company_edits|supplier_reviews|review_meta|avl_.*|groups_state|meta_.*|quoted_.*|sqq_.*)$/, __S = /^(acting|role)$/;
  function __typed(k, v) { if (v == null) return null; if (__A.test(k)) return Array.isArray(v) ? v : null; if (__O.test(k)) return (typeof v === 'object' && !Array.isArray(v)) ? v : null; if (__S.test(k)) return typeof v === 'string' ? v : null; return v; }   /* a stored value of the wrong type is ignored, never trusted */
  function store(k, v) { if (v !== undefined) window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;   /* every write invalidates the memoised company list (directory.js) */
    if (window.dxStoreHook) { var __h = window.dxStoreHook(k, v); if (__h !== undefined) return __h; } try { if (v === undefined) return __typed(k, JSON.parse(localStorage.getItem('dx_' + k) || 'null')); localStorage.setItem('dx_' + k, JSON.stringify(v)); return true; } catch (e) { quotaToast(); return false; } }
  var __qt = 0; function quotaToast() { if (Date.now() - __qt < 3000) return; __qt = Date.now(); toast('Could not save — the browser storage is full. Remove large photos or old data and try again.'); }   /* a failed save is never reported as success */
  function later(fn) { setTimeout(fn, 40); }
  function now() { return Date.now(); }

  /* ── state machines: who may do what, in which status ──
     roles: "from" = the side that started the deal (buyer / requester / applicant), "to" = the side that received it */
  var FLOWS = {
    quote: { label: 'Quote request', icon: 'cart', steps: ['sent', 'quoted', 'accepted', 'confirmed', 'shipped', 'delivered', 'closed'],
      acts: { sent: { to: ['quote', 'decline'], from: ['cancel'] }, quoted: { from: ['accept', 'counter', 'decline'], to: ['revise'] }, countered: { to: ['quote', 'decline'], from: ['cancel'] },
        accepted: { to: ['confirm'] }, confirmed: { to: ['ship'] }, shipped: { from: ['receive'] }, delivered: { from: ['rate'] } } },
    service: { label: 'Service request', icon: 'tools', steps: ['sent', 'proposed', 'accepted', 'in_progress', 'delivered', 'closed'],
      acts: { sent: { to: ['propose', 'decline'], from: ['cancel'] }, proposed: { from: ['accept', 'decline'] }, accepted: { to: ['start'] }, in_progress: { to: ['deliver'] }, delivered: { from: ['rate'] } } },
    surplus: { label: 'Surplus offer', icon: 'box', steps: ['offered', 'accepted', 'confirmed', 'shipped', 'delivered', 'closed'],
      acts: { offered: { to: ['accept_offer', 'counter_offer', 'decline'], from: ['cancel'] }, countered: { from: ['accept_counter', 'decline'] }, accepted: { to: ['confirm'] }, confirmed: { to: ['ship'] }, shipped: { from: ['receive'] }, delivered: { from: ['rate'] } } },
    questionnaire: { label: 'Qualification questionnaire', icon: 'clipboard', steps: ['sent', 'answered', 'approved'],
      acts: { sent: { to: ['answer'] }, answered: { from: ['approve', 'reject'] } } },
    dossier: { label: 'Dossier request', icon: 'doc', steps: ['requested', 'nda_signed', 'shared', 'agreed'],
      acts: { requested: { to: ['sign_nda', 'decline'] }, nda_signed: { to: ['share'] }, shared: { from: ['agree', 'decline'], to: ['decline'] } } },
    job: { label: 'Job application', icon: 'briefcase', steps: ['applied', 'shortlisted', 'interview', 'offer', 'hired'],
      acts: { applied: { to: ['shortlist', 'reject'] }, shortlisted: { to: ['interview', 'reject'] }, interview: { to: ['offer', 'reject'] }, offer: { from: ['accept_job', 'decline'] } } },
    group: { label: 'Group order', icon: 'users', steps: ['open', 'target_reached', 'confirmed'],
      acts: { target_reached: { to: ['confirm_group', 'decline'] } } }
  };
  var LABEL = { sent: 'Sent', quoted: 'Quote received', countered: 'Counter-offer', accepted: 'Accepted', confirmed: 'Order confirmed', shipped: 'Shipped', delivered: 'Delivered', closed: 'Closed', declined: 'Declined', cancelled: 'Cancelled',
    proposed: 'Proposal received', in_progress: 'In progress', offered: 'Offer sent', answered: 'Answered', approved: 'Approved', rejected: 'Rejected', requested: 'Requested', nda_signed: 'NDA signed', shared: 'Details shared', agreed: 'Agreed',
    applied: 'Applied', shortlisted: 'Shortlisted', interview: 'Interview', offer: 'Job offer', hired: 'Hired', open: 'Open', target_reached: 'Target reached' };
  var TONE = { declined: 'dec', cancelled: 'dec', rejected: 'dec', closed: 'acc', approved: 'acc', agreed: 'acc', hired: 'acc', delivered: 'acc', confirmed: 'acc', accepted: 'acc' };
  var ACT = {
    quote: ['Send quote', 'p'], revise: ['Revise quote', ''], decline: ['Decline', 'd'], cancel: ['Withdraw', 'd'], accept: ['Accept quote', 'p'], counter: ['Counter-offer', ''], confirm: ['Confirm order', 'p'], ship: ['Mark shipped', 'p'], receive: ['Confirm received', 'p'], rate: ['Rate supplier', 'p'],
    propose: ['Send proposal', 'p'], start: ['Start work', 'p'], deliver: ['Mark delivered', 'p'], accept_offer: ['Accept offer', 'p'], counter_offer: ['Counter-offer', ''], accept_counter: ['Accept counter-offer', 'p'],
    answer: ['Answer questionnaire', 'p'], approve: ['Approve supplier', 'p'], reject: ['Reject', 'd'], sign_nda: ['Sign NDA', 'p'], share: ['Share details', 'p'], agree: ['Agree terms', 'p'],
    shortlist: ['Shortlist', 'p'], interview: ['Invite to interview', 'p'], offer: ['Make offer', 'p'], accept_job: ['Accept job offer', 'p'], confirm_group: ['Confirm group price', 'p']
  };
  /* forms some actions need */
  var FORMS = {
    quote: [['price', 'Price *', 'e.g. US$ 5.40 per kg', 1], ['validity', 'Valid for', '14 days'], ['terms', 'Delivery terms', 'CIF'], ['lead', 'Lead time', '3 weeks']],
    revise: [['price', 'New price *', '', 1], ['validity', 'Valid for', '14 days']],
    counter: [['price', 'Your target price *', '', 1], ['note', 'Note', '']],
    counter_offer: [['price', 'Your price *', '', 1], ['note', 'Note', '']],
    propose: [['price', 'Fee *', 'e.g. EGP 85,000', 1], ['timeline', 'Timeline', '6 weeks'], ['note', 'Scope', '']],
    ship: [['tracking', 'Shipment / tracking reference', 'e.g. AWB 4412-99']],
    receive: [['ontime', 'Delivered on time? *', 'yes', 1]],
    rate: [['stars', 'Rating (1–5) *', '5', 1], ['note', 'Comment', '']],
    offer: [['price', 'Salary offer *', 'e.g. EGP 28,000 / month', 1]],
    interview: [['when', 'Interview date *', '', 1]],
    share: [['note', 'Shared (e.g. dossier summary, stability data room link) *', '', 1]],
    decline: [['note', 'Reason (shared with the other side)', '']]
  };

  /* ── storage ── */
  var __dl = null;
  function all(v) {
    if (v !== undefined) { store('deals', v); return; }
    if (window.dxStoreHook) return store('deals') || seed();   /* live: the adapter's list is always current */
    var ver = window.__dxStoreVer || 0; if (__dl && __dl.v === ver) return __dl.l;   /* demo: parsed once per store version, not once per company per render */
    var l = store('deals') || seed(); __dl = { v: ver, l: l }; return l;
  }
  function seed() {
    var t = now(), d = [
      mk('quote', { slug: null, name: 'Nour Pharma (Cairo)' }, 'quadra-pharm', 'Toll manufacturing — film-coated tablets', { qty: '500,000', unit: 'tablets / year', inc: 'EXW' }, 'We have an EDA-registered formula and need a WHO-GMP site. Toll price per 1,000 tablets and earliest slot?', t - 7200e3),
      mk('service', { slug: null, name: 'Delta Health (Tanta)' }, 'quadra-pharm', 'EDA variation — site transfer', {}, 'Need support for a PAC site-transfer variation for two products.', t - 86400e3),
      mk('job', { slug: null, name: 'Sara Mansour', person: true }, 'quadra-pharm', 'Senior Regulatory Affairs Specialist', {}, 'Four years of EDA dossiers in CTD format. CV attached.', t - 172800e3)
    ];
    store('deals', d); return d;
  }
  function mk(type, from, toSlug, title, lines, message, at) {
    var to = X() && X().bySlug(toSlug), first = FLOWS[type].steps[0];
    return { id: 'D' + Math.random().toString(36).slice(2, 9), type: type, title: title, from: from, to: { slug: toSlug, name: to ? to.name : toSlug }, lines: lines || {}, status: first, at: at || now(), updated: at || now(),
      events: [{ at: at || now(), by: 'from', kind: first, text: message || '' }] };
  }
  function save(d) { var l = all(); var i = l.findIndex(function (x) { return x.id === d.id; }); if (i >= 0) l[i] = d; else l.unshift(d); all(l); }
  function get(id) { return all().find(function (x) { return x.id === id; }); }

  /* ── whose side am I on? ── */
  function myCos() { var me = window.ME || {}; return X() ? X().myCompanies().map(function (c) { return c.slug; }) : []; }
  function sideOf(d) {
    var a = X() && X().mine(), mine = myCos(), me = window.ME || {};
    if (a && d.to.slug === a.slug) return 'to'; if (a && d.from.slug === a.slug) return 'from';
    if (d.from.person && d.from.userId === me.id) return 'from';
    if (mine.indexOf(d.to.slug) >= 0) return 'to'; if (mine.indexOf(d.from.slug) >= 0) return 'from';
    return null;
  }
  function other(d, side) { return side === 'to' ? d.from : d.to; }
  function actionsFor(d, side) { var f = FLOWS[d.type], a = f.acts[d.status]; return a && side && a[side] ? a[side] : []; }
  function counterOwned(d, side) { var o = other(d, side), mine = myCos(); return o.slug && mine.indexOf(o.slug) >= 0; }

  /* ── create ── */
  function create(type, toSlug, title, lines, message, extra) {
    var a = X().mine(), me = window.ME || {};
    if (type !== 'job' && !a) { toast('Create or claim your company page first'); return null; }   /* only a company can send these (the engine refuses person-sent ones) */
    var from = type === 'job' ? { slug: null, name: me.name || 'You', person: true, userId: me.id } : { slug: a.slug, name: a.name };
    if (from.slug && from.slug === toSlug) { toast('You are acting as ' + from.name + ' — you cannot send this to your own company'); return null; }
    var d = mk(type, from, toSlug, title, lines, message); if (extra) Object.keys(extra).forEach(function (k) { d[k] = extra[k]; });
    if (window.dxHub) d.assignee = window.dxHub.route(toSlug, type);
    save(d); notifyOther(d, 'from', FLOWS[type].label + ' from ' + from.name + ': ' + title); return d;
  }
  function notifyOther(d, bySide, text) {
    var o = other(d, bySide); if (!window.NOTIFS || !o) return;
    if (!(o.slug && myCos().indexOf(o.slug) >= 0) && !(o.person && o.userId === (window.ME || {}).id)) return;   /* only notify the user when it concerns one of their companies */
    window.NOTIFS.unshift({ id: now(), uid: (window.ME || {}).id || 1, icon: '📨', text: esc(text), ts: 'now', read: false, type: 'deal' }); if (window.updateBadges) window.updateBadges();
  }

  /* ── act: move the state machine ── */
  var NEXT = { quote: 'quoted', revise: 'quoted', counter: 'countered', accept: 'accepted', confirm: 'confirmed', ship: 'shipped', receive: 'delivered', rate: 'closed', decline: 'declined', cancel: 'cancelled',
    propose: 'proposed', start: 'in_progress', deliver: 'delivered', accept_offer: 'accepted', counter_offer: 'countered', accept_counter: 'accepted', answer: 'answered', approve: 'approved', reject: 'rejected',
    sign_nda: 'nda_signed', share: 'shared', agree: 'agreed', shortlist: 'shortlisted', interview: 'interview', offer: 'offer', accept_job: 'hired', confirm_group: 'confirmed' };
  function offerAt(d) { if (!Array.isArray(d.events)) return d.updated; for (var i = d.events.length - 1; i >= 0; i--) if (['quote', 'revise', 'propose'].indexOf(d.events[i].kind) >= 0) return d.events[i].at; return d.updated; }
  function offerExpired(d) { var m = d.offer && /(\d+)\s*day/.exec(d.offer.validity || ''); return !!(m && Date.now() - offerAt(d) > (+m[1]) * 864e5); }
  function offerExpiry(d) { var m = d.offer && /(\d+)\s*day/.exec(d.offer.validity || ''); return m ? new Date(offerAt(d) + (+m[1]) * 864e5) : null; }
  function act(id, action, data, side) {
    var d = get(id); if (!d) return null;
    side = side || sideOf(d);
    if (actionsFor(d, side).indexOf(action) < 0) { toast('That step is not available now'); return null; }
    if (action === 'accept' && offerExpired(d)) { toast('This offer expired on ' + offerExpiry(d).toLocaleDateString() + ' — ask for a new quote (counter-offer)'); return null; }
    var st = NEXT[action]; if (action === 'accept' && d.type === 'service') st = 'accepted';
    d.status = st; d.updated = now(); data = data || {};
    if (action === 'quote' || action === 'revise' || action === 'propose') d.offer = { price: data.price, validity: data.validity || '14 days', terms: data.terms || d.lines.inc || '', lead: data.lead || data.timeline || '', note: data.note || '' };
    if (action === 'counter' || action === 'counter_offer') d.counter = { price: data.price, note: data.note || '' };
    if (action === 'accept_counter' && d.counter) d.offer = { price: d.counter.price, validity: '7 days', terms: d.lines.inc || '' };
    if (action === 'accept_offer') d.offer = { price: d.lines.price, validity: 'agreed', terms: d.lines.inc || 'EXW' };
    if (action === 'answer') d.answers = data.answers || d.answers;
    if (action === 'receive') d.ontime = (data.ontime || 'yes') !== 'no';
    d.events.push({ at: now(), by: side, kind: action, text: summary(action, data), data: data });
    save(d); effects(d, action, data, side);
    if (window.dxHub) { var mineSide = side === 'to' ? d.to : d.from; if (mineSide.slug && myCos().indexOf(mineSide.slug) >= 0) window.dxHub.log(mineSide.slug, (ACT[action] ? ACT[action][0] : action) + ' — ' + d.title); }
    notifyOther(d, side, (side === 'to' ? d.to.name : d.from.name) + ': ' + (ACT[action] ? ACT[action][0] : action) + ' — ' + d.title);
    return d;
  }
  function summary(action, data) {
    if (data.price) return (ACT[action] ? ACT[action][0] : action) + ': ' + data.price + (data.validity ? ' · valid ' + data.validity : '') + (data.terms ? ' · ' + data.terms : '') + (data.lead ? ' · lead time ' + data.lead : '') + (data.timeline ? ' · ' + data.timeline : '') + (data.note ? ' — ' + data.note : '');
    if (data.stars) return 'Rated ' + data.stars + '★' + (data.note ? ' — ' + data.note : '');
    return (ACT[action] ? ACT[action][0] : action) + (data.tracking ? ': ' + data.tracking : '') + (data.when ? ': ' + data.when : '') + (data.note ? ' — ' + data.note : '');
  }
  /* consequences outside the deal */
  function effects(d, action, data, side) {
    if (action === 'rate' && d.to.slug) { var r = store('supplier_reviews') || {}; (r[d.to.slug] = r[d.to.slug] || []).push({ stars: Math.max(1, Math.min(5, +data.stars || 5)), note: data.note || '', from: d.from.name, at: now(), deal: d.id }); store('supplier_reviews', r); }
    if (d.type === 'questionnaire' && d.from.slug && (action === 'approve' || action === 'reject')) { var k = 'avl_' + d.from.slug, m = store(k) || {}; m[d.to.slug] = { status: action === 'approve' ? 'approved' : 'suspended', since: new Date().toISOString().slice(0, 10), via: d.id }; store(k, m); }
    if (d.type === 'group' && action === 'confirm_group') {
      /* the supplier confirmed the pooled price → one order per member, already accepted at the group price */
      (d.members || []).forEach(function (mb) { var o = mk('quote', { slug: mb.slug, name: mb.name }, d.to.slug, d.lines.product + ' — ' + mb.qty.toLocaleString() + ' ' + d.lines.unit + ' (group order)', { qty: mb.qty, unit: d.lines.unit, inc: d.lines.inc || 'EXW' }, 'Share in group ' + d.title);
        o.status = 'accepted'; o.offer = { price: d.lines.price, validity: 'group price', terms: d.lines.inc || 'EXW' }; o.events.push({ at: now(), by: 'to', kind: 'accept', text: 'Group price confirmed by ' + d.to.name + ': ' + d.lines.price }); o.groupOf = d.id; save(o); });
    }
  }

  /* ── groups: members join; reaching the target moves the deal to the supplier ── */
  function joinGroup(id, member, qty) {
    var d = get(id); if (!d || d.type !== 'group' || d.status !== 'open') return null;
    qty = Math.floor(+qty); if (!(qty > 0)) { toast('Enter a quantity greater than zero'); return null; }
    if (member.slug && member.slug === d.to.slug) { toast('The supplier cannot join its own buying group'); return null; }
    var ex = (d.members || []).find(function (m) { return m.slug === member.slug; });
    if (ex) ex.qty += qty; else (d.members = d.members || []).push({ slug: member.slug, name: member.name, qty: qty });
    d.events.push({ at: now(), by: 'member', kind: 'join', text: member.name + ' joined with ' + qty.toLocaleString() + ' ' + d.lines.unit });
    var sum = d.members.reduce(function (a, m) { return a + m.qty; }, 0);
    if (sum >= d.lines.target) { d.status = 'target_reached'; d.events.push({ at: now(), by: 'system', kind: 'target', text: 'Target reached (' + sum.toLocaleString() + ' ' + d.lines.unit + ') — waiting for ' + d.to.name + ' to confirm the group price' }); }
    d.updated = now(); save(d); return d;
  }

  /* ── demo: perform the other side's next step, openly ── */
  var AUTO = { quote: function (d) { return { price: 'US$ ' + (2 + (d.title.length % 37) + (d.to.name.length % 5) / 10).toFixed(2) + ' per ' + (d.lines.unit || 'unit'), validity: '14 days', terms: d.lines.inc || 'CIF', lead: '3 weeks' }; },
    revise: function (d) { return { price: d.counter ? d.counter.price : 'US$ 4.90', validity: '7 days' }; }, propose: function () { return { price: 'EGP 85,000', timeline: '6 weeks', note: 'Gap analysis, compilation and EDA follow-up' }; },
    ship: function () { return { tracking: 'AWB ' + Math.floor(1000 + Math.random() * 8999) + '-' + Math.floor(10 + Math.random() * 89) }; }, answer: function (d) { return { answers: d.answers }; },
    share: function () { return { note: 'Dossier summary, stability data (Zone IVa) and registration certificate shared in the data room' }; }, offer: function () { return { price: 'EGP 32,000 / month' }; }, interview: function () { return { when: new Date(now() + 5 * 864e5).toISOString().slice(0, 10) }; },
    counter_offer: function (d) { return { price: d.lines.price ? d.lines.price.replace(/[\d.]+/, function (n) { return (parseFloat(n) * 1.1).toFixed(2); }) : 'US$ 2.60 per kg', note: 'Best we can do for this batch' }; },
    rate: function () { return { stars: 5 }; } };
  function simulate(id) {
    var d = get(id), mine = sideOf(d); if (!d || !mine) return;
    var theirs = mine === 'to' ? 'from' : 'to', opts = actionsFor(d, theirs).filter(function (a) { return ['cancel', 'decline', 'reject', 'revise'].indexOf(a) < 0; });
    if (!opts.length) { toast('Nothing for them to do right now'); return; }
    var a = opts[0]; act(id, a, AUTO[a] ? AUTO[a](d) : {}, theirs); toast((theirs === 'to' ? d.to.name : d.from.name) + ': ' + ACT[a][0] + ' (simulated)');
  }

  /* ── views ── */
  function pill(s) { return '<span class="mr-st st-' + (TONE[s] || (s === 'sent' || s === 'requested' || s === 'applied' || s === 'open' || s === 'offered' ? 'sent' : 'quoted')) + '">' + esc(LABEL[s] || s) + '</span>'; }
  function row(d, side) {
    var f = FLOWS[d.type], o = other(d, side), acts = actionsFor(d, side);
    return '<button type="button" class="dl-row" data-deal="' + d.id + '"><span class="dl-ic">' + ic(f.icon) + '</span><span class="dl-b"><b>' + esc(d.title) + '</b><small>' + esc(f.label) + ' · ' + (myCos().length > 1 ? (side === 'to' ? esc(o.name) + ' → ' + esc(d.to.name) : esc(d.from.name) + ' → ' + esc(o.name)) : (side === 'to' ? 'from ' : 'to ') + esc(o.name)) + (d.group ? ' · 1 of a multi-company request' : '') + ' · ' + new Date(d.updated).toLocaleDateString() + '</small></span>' + pill(d.status) +
      (acts.length ? '<span class="dl-todo">Your move</span>' : '') + '</button>';
  }
  function center(tab, typeFilter, coFilter) {
    var a = X().mine(); tab = tab || 'sent';
    var cos = X().myCompanies();
    var list = all().filter(function (d) { var s = sideOf(d); return tab === 'sent' ? s === 'from' : s === 'to'; }).filter(function (d) { return !typeFilter || d.type === typeFilter; })
      .filter(function (d) { return !coFilter || (tab === 'sent' ? d.from.slug : d.to.slug) === coFilter; }).sort(function (x, y) { return y.updated - x.updated; });
    var sent = all().filter(function (d) { return sideOf(d) === 'from'; }).length, recv = all().filter(function (d) { return sideOf(d) === 'to'; }).length;
    var todo = all().filter(function (d) { var s = sideOf(d); return s && actionsFor(d, s).length; }).length;
    var m = D.modal({ title: 'Requests & deals' + (a ? ' — ' + a.name : ''), secondary: 'Close',
      body: '<div class="dl-tabs"><button type="button" class="dr-chip' + (tab === 'sent' ? ' on' : '') + '" data-dtab="sent">Sent (' + sent + ')</button><button type="button" class="dr-chip' + (tab === 'received' ? ' on' : '') + '" data-dtab="received">Received (' + recv + ')</button>' + (todo ? '<span class="dl-todo">' + todo + ' waiting for you</span>' : '') + '</div>' +
        (cos.length > 1 ? '<div class="dl-types"><span class="cp-muted">Company:</span><button type="button" class="dr-chip sm' + (!coFilter ? ' on' : '') + '" data-dco="">All my companies</button>' + cos.map(function (c) { return '<button type="button" class="dr-chip sm' + (coFilter === c.slug ? ' on' : '') + '" data-dco="' + c.slug + '">' + esc(c.name) + '</button>'; }).join('') + '</div>' : '') +
        '<div class="dl-types">' + ['', 'quote', 'service', 'surplus', 'questionnaire', 'dossier', 'group', 'job'].map(function (t) { return '<button type="button" class="dr-chip sm' + ((typeFilter || '') === t ? ' on' : '') + '" data-dtype="' + t + '">' + (t ? FLOWS[t].label : 'All types') + '</button>'; }).join('') + '</div>' +
        (list.length ? list.map(function (d) { return row(d, tab === 'sent' ? 'from' : 'to'); }).join('') : '<p class="cp-muted">Nothing here yet.</p>') });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    m.el.addEventListener('click', function (e) {
      var t = e.target.closest('[data-dtab]'); if (t) { m.close(); later(function () { center(t.dataset.dtab, typeFilter, coFilter); }); return; }
      var dc = e.target.closest('[data-dco]'); if (dc) { m.close(); later(function () { center(tab, typeFilter, dc.dataset.dco || null); }); return; }
      var ty = e.target.closest('[data-dtype]'); if (ty) { m.close(); later(function () { center(tab, ty.dataset.dtype || null, coFilter); }); return; }
      var r = e.target.closest('[data-deal]'); if (r) { m.close(); later(function () { thread(r.dataset.deal, function () { center(tab, typeFilter, coFilter); }); }); }
    });
  }
  function stepper(d) {
    var steps = FLOWS[d.type].steps, cur = steps.indexOf(d.status), end = ['declined', 'cancelled', 'rejected'].indexOf(d.status) >= 0;
    if (d.status === 'countered') cur = 1;
    return '<ol class="dl-steps' + (end ? ' ended' : '') + '">' + steps.map(function (s, i) { return '<li class="' + (i < cur || (i === cur && ['closed', 'approved', 'agreed', 'hired', 'confirmed'].indexOf(s) >= 0 && i === steps.length - 1) ? 'done' : i === cur ? 'cur' : '') + '">' + esc(LABEL[s] || s) + '</li>'; }).join('') + '</ol>' + (end ? '<div class="dl-ended">' + pill(d.status) + '</div>' : '');
  }
  function thread(id, back) {
    var d = get(id); if (!d) return;
    var side = sideOf(d), f = FLOWS[d.type], acts = actionsFor(d, side), o = other(d, side), sim = side && !counterOwned(d, side) && actionsFor(d, side === 'to' ? 'from' : 'to').some(function (a) { return ['cancel', 'decline', 'reject', 'revise'].indexOf(a) < 0; });
    var lines = Object.keys(d.lines || {}).filter(function (k) { return d.lines[k] !== '' && d.lines[k] != null && k !== 'target'; }).map(function (k) { return '<tr><td>' + esc({ qty: 'Quantity', unit: 'Unit', inc: 'Delivery terms', to: 'Deliver to', by: 'Needed by', product: 'Product', price: 'Group price', supplier: 'Supplier' }[k] || k) + '</td><td>' + esc(d.lines[k]) + '</td></tr>'; }).join('');
    var m = D.modal({ title: f.label + ' — ' + d.title, secondary: back ? 'Back' : 'Close',
      body: '<div class="dl-parties"><span>' + ic('building') + '<b>' + esc(d.from.name) + '</b></span><span class="dl-arrow">→</span><span>' + ic('building') + '<b>' + esc(d.to.name) + '</b>' + (d.assignee ? ' <small class="dl-asg">handled by ' + esc(d.assignee.name) + ' · ' + esc(d.assignee.role) + '</small>' : '') + '</span><span class="dl-you">You are ' + (side === 'to' ? 'the receiver' : side === 'from' ? 'the sender' : 'viewing') + '</span></div>' + stepper(d) +
        (lines ? '<table class="cp-spec">' + lines + '</table>' : '') +
        (d.offer ? '<div class="dl-offer' + (offerExpired(d) && ['quoted', 'proposed'].indexOf(d.status) >= 0 ? ' ctr' : '') + '">' + ic('tag') + '<b>' + esc(d.offer.price) + '</b>' + (d.offer.validity ? (offerExpired(d) && ['quoted', 'proposed'].indexOf(d.status) >= 0 ? ' · <b>expired ' + esc(offerExpiry(d).toLocaleDateString()) + '</b>' : ' · valid ' + esc(d.offer.validity) + (offerExpiry(d) ? ' (to ' + esc(offerExpiry(d).toLocaleDateString()) + ')' : '')) : '') + (d.offer.terms ? ' · ' + esc(d.offer.terms) : '') + (d.offer.lead ? ' · ' + esc(d.offer.lead) : '') + '</div>' : '') +
        (d.counter && d.status === 'countered' ? '<div class="dl-offer ctr">' + ic('trend') + 'Counter-offer: <b>' + esc(d.counter.price) + '</b>' + (d.counter.note ? ' — ' + esc(d.counter.note) : '') + '</div>' : '') +
        (d.type === 'group' ? '<div class="dl-members">' + (d.members || []).map(function (mb) { return '<span>' + esc(mb.name) + ' · ' + esc(Number(mb.qty || 0).toLocaleString()) + '</span>'; }).join('') + '</div>' : '') +
        (Array.isArray(d.answers) && (d.status === 'answered' || d.status === 'approved' || d.status === 'rejected') ? '<div class="dl-ans">' + d.answers.filter(function (s) { return Array.isArray(s) && Array.isArray(s[1]); }).map(function (s) { return '<h4 class="sq-h">' + esc(s[0]) + '</h4>' + s[1].map(function (x) { return '<div class="sq-row"><span>' + esc(x.q) + '</span><b>' + esc(x.a || '—') + '</b><small>' + esc(x.src || '') + '</small></div>'; }).join(''); }).join('') + '</div>' : '') +
        '<h4 class="sq-h">Timeline</h4><ul class="dl-tl">' + (Array.isArray(d.events) ? d.events : []).slice().reverse().map(function (ev) { var who = ev.by === 'from' ? d.from.name : ev.by === 'to' ? d.to.name : ev.by === 'member' ? 'Member' : 'Drugbox'; return '<li><b>' + esc(who) + '</b> · ' + esc(LABEL[ev.kind] || (ACT[ev.kind] ? ACT[ev.kind][0] : ev.kind)) + '<small>' + new Date(ev.at).toLocaleString() + '</small>' + (ev.text && ev.text !== (LABEL[ev.kind] || '') ? '<p>' + esc(ev.text) + '</p>' : '') + '</li>'; }).join('') + '</ul>' +
        '<div class="dl-acts">' + acts.map(function (a) { return '<button type="button" class="dr-btn ' + (ACT[a][1] === 'p' ? 'p' : '') + (ACT[a][1] === 'd' ? ' dl-d' : '') + '" data-act="' + a + '">' + esc(ACT[a][0]) + '</button>'; }).join('') +
        (sim ? '<button type="button" class="dr-btn ghost dl-sim" data-sim="1">' + ic('spark') + 'Simulate ' + esc(o.name) + '\u2019s reply (demo)</button>' : '') +
        (d.group ? '<button type="button" class="dr-btn" data-cmpq="1">' + ic('clipboard') + 'Compare all quotes</button>' : '') + (o.name && !o.person ? '<button type="button" class="dr-btn" data-chat="1">' + ic('chat') + 'Message</button>' : '') + (!acts.length && !sim ? '<span class="cp-muted">' + (['closed', 'declined', 'cancelled', 'rejected', 'approved', 'agreed', 'hired', 'confirmed'].indexOf(d.status) >= 0 && FLOWS[d.type].steps.indexOf(d.status) === FLOWS[d.type].steps.length - 1 || ['declined', 'cancelled', 'rejected'].indexOf(d.status) >= 0 ? 'This deal is finished.' : 'Waiting for ' + esc(o.name) + '.') + '</span>' : '') + '</div>' });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    var sec = m.el.querySelector('[data-a=cancel]'); if (sec && back) sec.onclick = function () { later(back); };
    m.el.addEventListener('click', function (e) {
      var b = e.target.closest('[data-act]'); if (b) { m.close(); later(function () { runAction(d, b.dataset.act, side, back); }); return; }
      if (e.target.closest('[data-sim]')) { m.close(); simulate(d.id); later(function () { thread(d.id, back); }); return; }
      if (e.target.closest('[data-cmpq]')) { m.close(); later(function () { window.dxCompareQuotes && window.dxCompareQuotes(d.group); }); return; }
      if (e.target.closest('[data-chat]')) { m.close(); if (window.dxOpenChat) window.dxOpenChat(o.name); }
    });
  }
  function runAction(d, a, side, back) {
    if (a === 'answer') return answerForm(d, back);
    var form = FORMS[a];
    if (!form) { act(d.id, a, {}, side); toast(ACT[a][0] + ' — done'); if (window.dxDir) X().render(); return later(function () { thread(d.id, back); }); }
    D.modal({ title: ACT[a][0] + ' — ' + d.title, body: form.map(function (fl) { return '<div class="dbk-f"><label for="af_' + fl[0] + '">' + esc(fl[1]) + '</label>' + (fl[0] === 'stars' ? '<select id="af_stars"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select>' : fl[0] === 'ontime' ? '<select id="af_ontime"><option value="yes">Yes, on time</option><option value="no">No, late</option></select>' : fl[0] === 'when' ? '<input id="af_when" type="date"' + (fl[3] ? ' data-req' : '') + '>' : '<input id="af_' + fl[0] + '" placeholder="' + esc(fl[2]) + '"' + (fl[3] ? ' data-req' : '') + (fl[0] === 'validity' || fl[0] === 'terms' ? ' value="' + esc(fl[0] === 'terms' ? (d.lines.inc || fl[2]) : fl[2]) + '"' : '') + '>') + '</div>'; }).join(''),
      primary: { label: ACT[a][0], onClick: function (b) {
        if (!D.requireFields(b)) return false; var data = {}; form.forEach(function (fl) { var el = b.querySelector('#af_' + fl[0]); if (el) data[fl[0]] = el.value.trim(); });
        act(d.id, a, data, side); toast(ACT[a][0] + ' — sent to ' + other(d, side).name); if (window.dxDir) X().render(); later(function () { thread(d.id, back); });
      } } });
  }
  function answerForm(d, back) {
    var ans = (Array.isArray(d.answers) ? d.answers : []).filter(function (s) { return Array.isArray(s) && Array.isArray(s[1]); }), idx = 0;
    D.modal({ title: 'Answer questionnaire from ' + d.from.name, body: '<p class="cp-muted">Answers from your company page are pre-filled. Check them and complete the rest.</p>' + ans.map(function (s) { return '<h4 class="sq-h">' + esc(s[0]) + '</h4>' + s[1].map(function (x) { var i = idx++; return '<div class="dbk-f"><label for="qa_' + i + '">' + esc(x.q) + (x.a ? ' <small class="cp-muted">(from ' + esc(x.src) + ')</small>' : ' *') + '</label><input id="qa_' + i + '" value="' + esc(x.a) + '"' + (x.a ? '' : ' data-req') + '></div>'; }).join(''); }).join(''),
      primary: { label: 'Send answers', onClick: function (b) {
        if (!D.requireFields(b)) return false; var i = 0; ans.forEach(function (s) { s[1].forEach(function (x) { var v = b.querySelector('#qa_' + (i++)).value.trim(); if (v !== x.a) { x.a = v; x.src = 'Supplier'; } }); });
        act(d.id, 'answer', { answers: ans }, 'to'); toast('Answers sent to ' + d.from.name); if (window.dxDir) X().render(); later(function () { thread(d.id, back); });
      } } });
  }
  /* inline list for a company page (Requests tab) */
  function receivedHtml(slug) {
    var list = all().filter(function (d) { return d.to.slug === slug; }).sort(function (x, y) { return y.updated - x.updated; });
    return list.length ? list.map(function (d) { return row(d, 'to'); }).join('') : '<p class="cp-muted">No requests yet.</p>';
  }
  document.addEventListener('click', function (e) { var r = e.target.closest && e.target.closest('#dxDir [data-deal]'); if (r) { e.stopPropagation(); thread(r.dataset.deal); } }, true);

  function openCount(slug) { return all().filter(function (d) { return (!slug || d.to.slug === slug) && ['declined', 'cancelled', 'rejected', 'closed', 'approved', 'agreed', 'hired', 'confirmed'].indexOf(d.status) < 0; }).length; }
  function waiting() { return all().filter(function (d) { var s = sideOf(d); return s && actionsFor(d, s).length; }).length; }
  window.dxDeals = { offerExpired: offerExpired, FLOWS: FLOWS, all: all, get: get, create: create, act: act, simulate: simulate, center: center, thread: thread, receivedHtml: receivedHtml, sideOf: sideOf, actionsFor: actionsFor, joinGroup: joinGroup, save: save, mk: mk, openCount: openCount, waiting: waiting, label: function (s) { return LABEL[s] || s; } };
})();
