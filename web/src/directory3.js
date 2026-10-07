/* Company Directory — batch 2
   1 approved vendor list (per acting company) + 2 qualification questionnaire filled from the page
   3 "What we're looking for" + matchmaking · 4 dossiers for licensing · 5 group buying · 6 surplus stock
   7 membership badges confirmed by industry bodies */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function X() { return window.dxDir; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  function toast(m) { D.toast(m); }
  function st(k, v) { return X().store(k, v); }
  function ed(co) { return X().edits()[co.slug]; }   /* company_edits parsed once per store version */
  function acting() { return X().mine(); }
  function later(fn) { setTimeout(fn, 40); }

  /* ── seed data (demo) ── */
  var LOOKING = {
    'quadra-pharm': ['Distributor — Upper Egypt', 'Export partner — GCC', 'API supplier — Metformin'],
    'beauty-lab-egypt': ['Packaging supplier — airless bottles', 'Distributor — pharmacies'],
    'alex-excipients': ['Manufacturer customers — tablets'],
    'nile-pharma-packaging': ['Manufacturer customers — cartons'],
    'orient-cosmetics': ['Brand owners — private label creams'],
    'pharaonic-logistics': ['Manufacturers — cold-chain products']
  };
  var MEMBERS = {
    'quadra-pharm': [['Chamber of Pharmaceutical Industries', 'CPI'], ['Export Council for Medical Industries', 'ECMI']],
    'medsinia-industries': [['Chamber of Pharmaceutical Industries', 'CPI']],
    'pharaonic-logistics': [['Federation of Egyptian Chambers of Commerce — Pharma Division', 'FEDCOC']],
    'beauty-lab-egypt': [['Chamber of Cosmetics Industries', 'CCI']]
  };
  var BODIES = ['Chamber of Pharmaceutical Industries', 'Chamber of Cosmetics Industries', 'Export Council for Medical Industries', 'Federation of Egyptian Chambers of Commerce — Pharma Division', 'Egyptian Pharmaceutical Trading Association'];
  var DOSSIERS = [
    { slug: 'quadra-pharm', product: 'Esomeprazole 40 mg tablets', status: 'EDA registered', markets: 'Egypt · CTD ready for GCC', deal: 'License out', id: 'd1' },
    { slug: 'quadra-pharm', product: 'Cefixime 400 mg capsules', status: 'CTD dossier ready', markets: 'Egypt, Iraq, Yemen', deal: 'Sell dossier', id: 'd2' },
    { slug: 'nile-valley-pharma', product: 'Sitagliptin 100 mg tablets', status: 'Under EDA review', markets: 'Egypt', deal: 'Co-marketing', id: 'd3' },
    { slug: 'medsinia-industries', product: 'Vitamin D3 50,000 IU capsules', status: 'EDA registered', markets: 'Egypt · Africa', deal: 'License out', id: 'd4' }
  ];
  var GROUPS = [
    { id: 'g1', product: 'Metformin HCl BP — CEP', supplier: 'Cairo API Trading', target: 3000, unit: 'kg', price: 'US$ 5.10/kg at 3 MT (vs 5.80)', deadline: '2026-11-10', shares: [['Nile Valley Pharmaceuticals', 900], ['Obour Medica Industries', 700], ['Ramadan Pharma Industries', 200]] },
    { id: 'g2', product: 'MCC PH-102', supplier: 'Alex Excipients Trading', target: 2000, unit: 'kg', price: 'US$ 2.90/kg at 2 MT (vs 3.40)', deadline: '2026-10-30', shares: [['Obour Medica Industries', 800], ['Medsinia Industries', 400]] }
  ];
  var SURPLUS = [
    { id: 's1', slug: 'medsinia-industries', product: 'Microcrystalline cellulose PH-101', qty: '750 kg', batch: 'MC-24-0911', expiry: '2027-03', price: 'US$ 2.40/kg', off: 30 },
    { id: 's2', slug: 'beauty-lab-egypt', product: 'Airless bottles 30 mL (white)', qty: '18,000 pcs', batch: 'AB-3012', expiry: '—', price: 'EGP 4.10/pc', off: 45 },
    { id: 's3', slug: 'quadra-pharm', product: 'Printed cartons — Hair Serum (old artwork)', qty: '9,500 pcs', batch: 'CT-HS-07', expiry: '—', price: 'EGP 0.60/pc', off: 70 },
    { id: 's4', slug: 'nile-valley-pharma', product: 'Paracetamol DC grade', qty: '300 kg', batch: 'PC-25-044', expiry: '2026-12', price: 'US$ 3.10/kg', off: 25 }
  ];
  function lookingOf(co) { var e = ed(co); return (e && Array.isArray(e.looking) ? e.looking : null) || LOOKING[co.slug] || []; }
  function membersOf(co) { var e = ed(co), pend = e && Array.isArray(e.memberPending) ? e.memberPending : []; return MEMBERS[co.slug] ? MEMBERS[co.slug].map(function (m) { return { name: m[0], short: m[1], ok: true }; }).concat(pend) : pend; }
  function dossiers() { return (window.dxLiveListings ? [] : DOSSIERS).concat(st('dossiers') || []); }
  function groups() { var extra = st('groups_state') || {}; return (window.dxLiveListings ? [] : GROUPS).concat(st('groups_new') || []).map(function (g) { var x = extra[g.id]; return x ? Object.assign({}, g, { shares: g.shares.concat(x) }) : g; }); }
  function surplus() { return (st('surplus_new') || []).concat((window.dxLiveListings ? [] : SURPLUS)); }

  /* ── 1 · approved vendor list (belongs to the company you act for) ── */
  var AVL = { approved: ['Approved', 'avl-ok'], evaluation: ['Under evaluation', 'avl-ev'], suspended: ['Suspended', 'avl-sus'] };
  function avl(v) { var a = acting(); if (!a) return {}; return v === undefined ? (st('avl_' + a.slug) || {}) : st('avl_' + a.slug, v); }
  function setAvl(slug, status) {
    var m = avl(); if (status) m[slug] = { status: status, since: new Date().toISOString().slice(0, 10) }; else delete m[slug]; avl(m);
  }
  function cell(v) { v = String(v == null ? '' : v); if (/^[=+\-@\t\r]/.test(v)) v = "'" + v; return '"' + v.replace(/"/g, '""') + '"'; }   /* a company name is never a spreadsheet formula */
  function vendorDialog() {
    var a = acting(); if (!a) { toast('Act as a company to keep an approved vendor list'); return; }
    var m = avl(), keys = Object.keys(m);
    var dlg = D.modal({ title: a.name + ' — approved vendor list', secondary: 'Close',
      body: '<p class="cp-muted">Private to ' + esc(a.name) + '. Your team sees the status on every supplier page.</p>' + (keys.length ? keys.map(function (k) { var co = X().bySlug(k); if (!co) return ''; var q = qDeal(a.slug, k);
        return '<div class="mr-row">' + X().logo(co, 'dr-logo sm') + '<div class="mr-b"><b>' + esc(co.name) + '</b><small>since ' + esc(m[k].since) + (q ? ' · questionnaire: ' + window.dxDeals.label(q.status).toLowerCase() : '') + '</small></div><span class="avl ' + AVL[m[k].status][1] + '">' + AVL[m[k].status][0] + '</span>' +
          (q ? '<button type="button" class="dr-btn sm" data-sqview="' + q.id + '">Questionnaire</button>' : '') + '<button type="button" class="dr-btn sm" data-avlopen="' + k + '">Open</button></div>'; }).join('')
        : '<p class="cp-muted">No suppliers yet. Open a supplier page and set its vendor status.</p>') +
        (keys.length ? '<div class="fd-act"><a class="dr-btn" id="avlCsv" download="approved-vendors.csv">' + ic('doc') + 'Export CSV</a></div>' : '') });
    var csv = dlg.el.querySelector('#avlCsv');
    if (csv) csv.href = URL.createObjectURL(new Blob(['Supplier,Status,Since\n' + keys.map(function (k) { var co = X().bySlug(k); return [co ? co.name : k, AVL[m[k].status][0], m[k].since].map(cell).join(','); }).join('\n')], { type: 'text/csv' }));
    dlg.el.addEventListener('click', function (e) {
      var o = e.target.closest('[data-avlopen]'); if (o) { dlg.close(); later(function () { X().open(o.dataset.avlopen); }); }
      var v = e.target.closest('[data-sqview]'); if (v) { dlg.close(); later(function () { window.dxDeals.thread(v.dataset.sqview, vendorDialog); }); }
    });
  }

  /* ── 2 · qualification questionnaire filled from the supplier's page ── */
  function qDeal(fromSlug, toSlug) { return window.dxDeals.all().filter(function (d) { return d.type === 'questionnaire' && d.from.slug === fromSlug && d.to.slug === toSlug; })[0]; }
  function answersFor(co) {
    var A = function (q, a, src) { return { q: q, a: a, src: a ? src : 'To be answered by the supplier' }; };
    return [
      ['Company', [A('Legal name', co.name, 'Company page'), A('Address', co.address, 'Company page'), A('Commercial registry number', co.registry || '', 'Verification'), A('Year founded', String(co.founded || ''), 'Company page'), A('Employees', co.employees, 'Company page')]],
      ['Quality system', [A('Certificates', (co.certs || []).join(', '), co.status === 'verified' ? 'Verified by Drugbox' : 'Company page'), A('Verification status', co.status === 'verified' ? 'Verified' : 'Not verified', 'Drugbox'),
        A('Last regulatory inspection (date, outcome)', '', ''), A('Change-control notification to customers', '', '')]],
      ['Products & capacity', [A('Products offered', co.products.map(function (p) { return p.name; }).join(', '), 'Catalogue'), A('Services', (co.services || []).join(', '), 'Company page')]],
      ['Contacts', [A('Sales contact', X().contact(co, 'rfq'), 'Company page'), A('Phone / email', [co.phone, co.email].filter(Boolean).join(' · '), 'Company page')]]
    ];
  }
  function sendQuestionnaire(co) {
    var a = acting(); if (!a) { toast('Act as a company to send a questionnaire'); return; }
    var secs = answersFor(co), filled = 0, total = 0; secs.forEach(function (s) { s[1].forEach(function (x) { total++; if (x.a) filled++; }); });
    D.modal({ title: 'Supplier qualification questionnaire', body: '<p>From <b>' + esc(a.name) + '</b> to <b>' + esc(co.name) + '</b>.</p><div class="sq-meter"><i style="width:' + Math.round(filled / total * 100) + '%"></i></div><p class="cp-muted">' + filled + ' of ' + total + ' answers are already filled from ' + esc(co.name) + '\u2019s page. The supplier reviews them and answers the rest.</p>',
      primary: { label: 'Send questionnaire', onClick: function () {
        window.dxDeals.create('questionnaire', co.slug, 'Supplier qualification questionnaire', {}, filled + ' of ' + total + ' answers pre-filled from your company page — review and complete the rest.', { answers: secs });
        if (!avl()[co.slug]) setAvl(co.slug, 'evaluation');
        toast('Questionnaire sent — ' + co.name + ' is now “Under evaluation” on your vendor list'); X().render();
      } } });
  }
  /* ── 3 · what we're looking for + matchmaking ── */
  function offersOf(co) {
    var out = co.sectors.map(function (s) { return { 'Manufacturer': 'Toll manufacturer', 'CMO / Toll': 'Toll manufacturer', 'Distribution': 'Distributor', 'Packaging': 'Packaging supplier', 'API & excipients': 'API supplier', 'Cosmetics': 'Private label cosmetics', 'Labs & testing': 'Testing lab', 'Regulatory & consulting': 'Regulatory consultant' }[s]; }).filter(Boolean);
    if (/upper egypt|assiut|sohag/i.test(co.tagline + co.about)) out.push('Distributor — Upper Egypt');
    return out;
  }
  function matchesFor(a) {
    var need = lookingOf(a).map(function (x) { return x.toLowerCase(); }), mine = offersOf(a).map(function (x) { return x.toLowerCase(); }), out = [];
    X().companies().forEach(function (co) {
      if (co.slug === a.slug) return;
      var why = [];
      need.forEach(function (n) { var head = n.split(' — ')[0], tail = (n.split(' — ')[1] || ''); offersOf(co).forEach(function (o) { if (o.toLowerCase().indexOf(head.replace(/s$/, '')) === 0 && (!tail || (co.products.map(function (p) { return p.name + ' ' + (p.api || ''); }).join(' ') + ' ' + co.tagline).toLowerCase().indexOf(tail.split(' ')[0]) >= 0 || /partner|upper|pharmac/.test(tail))) why.push('They offer: ' + o); }); });
      lookingOf(co).forEach(function (l) { var head = l.toLowerCase().split(' — ')[0]; mine.forEach(function (o) { if (head.indexOf(o.split(' ')[0].toLowerCase()) >= 0 || o.indexOf(head.split(' ')[0]) === 0) why.push('They look for: ' + l); }); });
      if (why.length) out.push({ co: co, why: why.filter(function (w, i) { return why.indexOf(w) === i; }).slice(0, 2) });
    });
    return out;
  }
  function matchesDialog() {
    var a = acting(); if (!a) { toast('Act as a company to see matches'); return; }
    var ms = matchesFor(a);
    var dlg = D.modal({ title: 'Matches for ' + a.name, secondary: 'Close', body: '<p class="cp-muted">' + esc(a.name) + ' is looking for: ' + (lookingOf(a).map(esc).join(', ') || '— add it on your page') + '</p>' +
      (ms.length ? ms.map(function (x) { return '<div class="mr-row">' + X().logo(x.co, 'dr-logo sm') + '<div class="mr-b"><b>' + esc(x.co.name) + '</b><small>' + x.why.map(esc).join(' · ') + '</small></div><button type="button" class="dr-btn sm" data-mopen="' + x.co.slug + '">Open</button><button type="button" class="dr-btn p sm" data-mmsg="' + esc(x.co.name) + '">Message</button></div>'; }).join('') : '<p class="cp-muted">No matches yet.</p>') });
    dlg.el.addEventListener('click', function (e) { var o = e.target.closest('[data-mopen]'), g = e.target.closest('[data-mmsg]'); if (o) { dlg.close(); later(function () { X().open(o.dataset.mopen); }); } if (g) { dlg.close(); if (window.dxOpenChat) window.dxOpenChat(g.dataset.mmsg); } });
  }
  function editLooking(co) {
    D.modal({ title: 'What is ' + co.name + ' looking for?', body: '<div class="dbk-f"><label for="lkT">One per line</label><textarea id="lkT" rows="5" placeholder="Distributor — Upper Egypt\nExport partner — GCC\nToll manufacturer — creams">' + esc(lookingOf(co).join('\n')) + '</textarea></div>',
      primary: { label: 'Save', onClick: function (b) { var e = st('company_edits') || {}; e[co.slug] = Object.assign({}, e[co.slug] || {}, { looking: b.querySelector('#lkT').value.split('\n').map(function (s) { return s.trim(); }).filter(Boolean) }); st('company_edits', e); X().render(); toast('Saved — matching companies will see you'); } } });
  }

  /* ── 4 · dossiers for licensing ── */
  function dossiersDialog() {
    var list = dossiers();
    var dlg = D.modal({ title: 'Dossiers for licensing', secondary: 'Close', body: '<p class="cp-muted">Registered products and CTD dossiers companies will license, sell or co-market. Details are shared after a confidentiality agreement.</p>' +
      list.map(function (d) { var co = X().bySlug(d.slug); return '<div class="mr-row"><span class="cp-jic cp-oic">' + ic('doc') + '</span><div class="mr-b"><b>' + esc(d.product) + '</b><small>' + esc(d.status) + ' · ' + esc(d.markets) + ' · by ' + esc(co ? co.name : '') + '</small></div><span class="avl avl-ev">' + esc(d.deal) + '</span><button type="button" class="dr-btn p sm" data-dreq="' + d.id + '">Request details</button></div>'; }).join('') });
    dlg.el.querySelector('.dbk-box').classList.add('dbk-wide');
    dlg.el.addEventListener('click', function (e) { var r = e.target.closest('[data-dreq]'); if (!r) return; var d = dossiers().find(function (x) { return x.id === r.dataset.dreq; }); dlg.close(); later(function () { dossierRequest(d); }); });
  }
  function dossierRequest(d) {
    var co = X().bySlug(d.slug), a = acting(); if (!a) { toast('Create or claim your company page first'); return; }   /* only a company can request a dossier */
    if (co && a.slug === co.slug) { toast('This is your own dossier'); return; }
    D.modal({ title: 'Request dossier details', body: '<p><b>' + esc(d.product) + '</b> — ' + esc(d.status) + ' · ' + esc(d.deal) + '</p><label class="sq-nda"><input type="checkbox" id="dNda"> ' + esc(a ? a.name : 'I') + ' agrees to the standard mutual NDA before details are shared.</label><div class="dbk-f"><label for="dMsg">Message</label><textarea id="dMsg" placeholder="Target markets, expected volumes, timeline…"></textarea></div>',
      primary: { label: 'Send request', onClick: function (b) {
        if (!b.querySelector('#dNda').checked) { toast('Please accept the NDA'); return false; }
        var __dd = window.dxDeals.create('dossier', d.slug, d.product, { deal: d.deal, markets: d.markets, status: d.status }, ((b.querySelector('#dMsg').value || '').trim() || 'Interested in ' + d.deal.toLowerCase() + '.') + ' · Mutual NDA accepted by the requester.');
        if (!__dd) return false;
        toast('Request sent to ' + (co ? co.name : '') + ' — they sign the NDA, then share details');
      } } });
  }
  function addDossier(co) {
    D.modal({ title: 'Add a dossier', body: '<div class="dbk-f"><label for="dsP">Product *</label><input id="dsP" data-req placeholder="e.g. Esomeprazole 40 mg tablets"></div><div class="dbk-row"><div class="dbk-f"><label for="dsS">Status</label><select id="dsS"><option>EDA registered</option><option>Under EDA review</option><option>CTD dossier ready</option></select></div><div class="dbk-f"><label for="dsD">Deal</label><select id="dsD"><option>License out</option><option>Sell dossier</option><option>Co-marketing</option></select></div></div><div class="dbk-f"><label for="dsM">Markets</label><input id="dsM" placeholder="Egypt · GCC"></div>',
      primary: { label: 'Add', onClick: function (b) { if (!D.requireFields(b)) return false; var l = st('dossiers') || []; l.unshift({ id: 'd' + Date.now(), slug: co.slug, product: b.querySelector('#dsP').value.trim(), status: b.querySelector('#dsS').value, deal: b.querySelector('#dsD').value, markets: b.querySelector('#dsM').value.trim() || 'Egypt' }); st('dossiers', l); X().render(); toast('Dossier listed'); } } });
  }

  /* ── 5 · group buying ── */
  function groupDeals() {
    var DL = window.dxDeals, have = DL.all().filter(function (d) { return d.type === 'group'; });
    if (!have.length && !st('groups_seeded')) {
      GROUPS.forEach(function (g) {
        var sup = X().companies().find(function (c) { return c.name === g.supplier; }), org = X().companies().find(function (c) { return c.name === g.shares[0][0]; }); if (!sup) return;
        var d = DL.mk('group', { slug: org ? org.slug : null, name: g.shares[0][0] }, sup.slug, 'Group buy — ' + g.product, { product: g.product, target: g.target, unit: g.unit, price: g.price.split(' at ')[0], inc: 'EXW', by: g.deadline }, 'Buying group opened');
        d.members = g.shares.map(function (s) { var c = X().companies().find(function (x) { return x.name === s[0]; }); return { slug: c ? c.slug : null, name: s[0], qty: s[1] }; }); DL.save(d);
      });
      st('groups_seeded', true); have = DL.all().filter(function (d) { return d.type === 'group'; });
    }
    return have;
  }
  function total(d) { return (d.members || []).reduce(function (a, m) { return a + m.qty; }, 0); }
  function groupsDialog() {
    var gs = groupDeals(), a = acting(), DL = window.dxDeals;
    var dlg = D.modal({ title: 'Group buying', secondary: 'Close', primary: { label: 'Start a group', onClick: function () { later(newGroup); } },
      body: '<p class="cp-muted">Small factories combine orders to reach the supplier\u2019s minimum order and a better price. When the target is reached the supplier confirms the group price, and every member gets its own order.</p>' + gs.map(function (g) { var have = total(g), pct = Math.min(100, Math.round(have / g.lines.target * 100)), mineIn = a && (g.members || []).some(function (s) { return s.slug === a.slug; });
        return '<div class="gb-card"><div class="gb-h"><b>' + esc(g.lines.product) + '</b><span>supplier ' + esc(g.to.name) + ' · organised by ' + esc(g.from.name) + ' · closes ' + esc(g.lines.by) + '</span></div><div class="gb-bar"><i style="width:' + pct + '%"></i></div>' +
          '<div class="gb-meta"><span><b>' + have.toLocaleString('en-US') + '</b> of ' + g.lines.target.toLocaleString('en-US') + ' ' + esc(g.lines.unit) + ' · ' + (g.members || []).length + ' companies</span><span class="gb-price">' + esc(g.lines.price) + '</span></div>' +
          (g.status === 'confirmed' ? '<span class="avl avl-ok">Supplier confirmed — orders created for every member</span>' : g.status === 'target_reached' ? '<div class="gb-join"><span class="avl avl-ev">Target reached — waiting for ' + esc(g.to.name) + '</span>' + (DL.sideOf(g) === 'to' ? '<button type="button" class="dr-btn p sm" data-gconf="' + g.id + '">Confirm group price</button>' : '<button type="button" class="dr-btn ghost sm" data-gsim="' + g.id + '">Simulate supplier confirmation (demo)</button>') + '</div>'
            : (mineIn ? '<span class="avl avl-ok">You joined</span> ' : '') + '<div class="gb-join"><input type="number" min="1" placeholder="' + (mineIn ? 'Add more' : 'Your quantity') + ' (' + esc(g.lines.unit) + ')" data-gq="' + g.id + '"><button type="button" class="dr-btn p sm" data-gjoin="' + g.id + '">' + (mineIn ? 'Add' : 'Join') + '</button></div>') + '</div>'; }).join('') });
    dlg.el.querySelector('.dbk-box').classList.add('dbk-wide');
    dlg.el.addEventListener('click', function (e) {
      var c = e.target.closest('[data-gconf],[data-gsim]'); if (c) { var id = c.dataset.gconf || c.dataset.gsim; DL.act(id, 'confirm_group', {}, 'to'); dlg.close(); toast('Group price confirmed — one order created for each member'); later(groupsDialog); return; }
      var j = e.target.closest('[data-gjoin]'); if (!j) return;
      if (!a) { toast('Act as a company to join'); return; }
      var q = +(dlg.el.querySelector('[data-gq="' + j.dataset.gjoin + '"]').value || 0); if (!(q > 0)) { toast('Enter your quantity'); return; }
      var d = DL.joinGroup(j.dataset.gjoin, { slug: a.slug, name: a.name }, q); if (!d) return;
      dlg.close(); toast(d && d.status === 'target_reached' ? 'Target reached! ' + d.to.name + ' now confirms the group price' : a.name + ' joined with ' + q.toLocaleString('en-US')); later(groupsDialog);
    });
  }
  function newGroup() {
    var sups = X().companies().filter(function (c) { return /API|excipient|Packaging|Distribution/i.test(c.sectors.join(' ')); });
    D.modal({ title: 'Start a buying group', body: '<div class="dbk-f"><label for="ngP">Product *</label><input id="ngP" data-req></div><div class="dbk-row"><div class="dbk-f"><label for="ngS">Supplier *</label><select id="ngS" data-req><option value="">Choose…</option>' + sups.map(function (c) { return '<option value="' + c.slug + '">' + esc(c.name) + '</option>'; }).join('') + '</select></div><div class="dbk-f"><label for="ngT">Target quantity *</label><input id="ngT" data-req type="number" min="1"></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="ngU">Unit</label><select id="ngU"><option>kg</option><option>MT</option><option>pcs</option></select></div><div class="dbk-f"><label for="ngQ">Your share *</label><input id="ngQ" data-req type="number" min="1"></div></div><div class="dbk-f"><label for="ngR">Target price</label><input id="ngR" placeholder="e.g. US$ 2.90/kg"></div>',
      primary: { label: 'Start group', onClick: function (b) { if (!D.requireFields(b)) return false; var a = acting(); if (!a) { toast('Act as a company to start a group'); return false; }
        var tgt = Math.floor(+b.querySelector('#ngT').value), share = Math.floor(+b.querySelector('#ngQ').value); if (!(tgt > 0) || !(share > 0)) { toast('Quantities must be at least 1'); return false; }
        var DL = window.dxDeals, d = DL.mk('group', { slug: a.slug, name: a.name }, b.querySelector('#ngS').value, 'Group buy — ' + b.querySelector('#ngP').value.trim(), { product: b.querySelector('#ngP').value.trim(), target: tgt, unit: b.querySelector('#ngU').value, price: b.querySelector('#ngR').value.trim() || 'To be confirmed', inc: 'EXW', by: new Date(Date.now() + 21 * 864e5).toISOString().slice(0, 10) }, 'Buying group opened');
        d.members = [{ slug: a.slug, name: a.name, qty: share }]; DL.save(d); toast('Group started — other companies can join now'); later(groupsDialog); } } });
  }

  /* ── 6 · surplus stock ── */
  function surplusDialog() {
    var dlg = D.modal({ title: 'Surplus stock', secondary: 'Close', primary: { label: 'Post surplus', onClick: function () { later(postSurplus); } },
      body: '<p class="cp-muted">Unused raw materials, packaging and near-expiry stock at a discount — turn frozen stock into cash.</p>' + surplus().map(function (s) { var co = X().bySlug(s.slug);
        return '<div class="mr-row"><span class="sp-off">−' + esc(s.off) + '%</span><div class="mr-b"><b>' + esc(s.product) + '</b><small>' + esc(s.qty) + ' · batch ' + esc(s.batch) + (s.expiry !== '—' ? ' · expires ' + esc(s.expiry) : '') + ' · ' + esc(co ? co.name : '') + '</small></div><b class="sp-price">' + esc(s.price) + '</b><button type="button" class="dr-btn p sm" data-soffer="' + s.id + '">Make an offer</button></div>'; }).join('') });
    dlg.el.querySelector('.dbk-box').classList.add('dbk-wide');
    dlg.el.addEventListener('click', function (e) { var o = e.target.closest('[data-soffer]'); if (!o) return; var s = surplus().find(function (x) { return x.id === o.dataset.soffer; }); dlg.close(); later(function () { surplusOffer(s); }); });
  }
  function surplusOffer(s) {
    var co = X().bySlug(s.slug), a = acting(); if (!a) { toast('Act as a company to make an offer'); return; }
    if (co && a.slug === co.slug) { toast('This is your own surplus'); return; }
    D.modal({ title: 'Make an offer — ' + s.product, body: '<p class="cp-muted">' + esc(s.qty) + ' · batch ' + esc(s.batch) + (s.expiry !== '—' ? ' · expires ' + esc(s.expiry) : '') + ' · listed at ' + esc(s.price) + ' by ' + esc(co ? co.name : '') + '</p>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="soQ">Quantity you want *</label><input id="soQ" data-req value="' + esc(s.qty) + '"></div><div class="dbk-f"><label for="soP">Your price *</label><input id="soP" data-req value="' + esc(s.price) + '"></div></div><div class="dbk-f"><label for="soM">Message</label><textarea id="soM" placeholder="Collection date, payment…"></textarea></div>',
      primary: { label: 'Send offer', onClick: function (b) { if (!D.requireFields(b)) return false;
        window.dxDeals.create('surplus', s.slug, s.product + ' (surplus)', { qty: b.querySelector('#soQ').value.trim(), price: b.querySelector('#soP').value.trim(), batch: s.batch, expiry: s.expiry }, (b.querySelector('#soM').value || '').trim());
        toast('Offer sent to ' + (co ? co.name : '') + ' — they can accept, counter or decline'); } } });
  }
  function postSurplus() {
    var a = acting(); if (!a) { toast('Act as a company to post surplus'); return; }
    D.modal({ title: 'Post surplus stock', body: '<div class="dbk-f"><label for="spP">Product *</label><input id="spP" data-req></div><div class="dbk-row"><div class="dbk-f"><label for="spQ">Quantity *</label><input id="spQ" data-req></div><div class="dbk-f"><label for="spB">Batch</label><input id="spB"></div></div><div class="dbk-row"><div class="dbk-f"><label for="spE">Expiry</label><input id="spE" type="month"></div><div class="dbk-f"><label for="spR">Price *</label><input id="spR" data-req placeholder="e.g. US$ 2.40/kg"></div></div><div class="dbk-f"><label for="spO">Discount %</label><input id="spO" type="number" min="0" max="95" value="30"></div>',
      primary: { label: 'Post', onClick: function (b) { if (!D.requireFields(b)) return false; var l = st('surplus_new') || []; l.unshift({ id: 's' + Date.now(), slug: a.slug, product: b.querySelector('#spP').value.trim(), qty: b.querySelector('#spQ').value.trim(), batch: b.querySelector('#spB').value.trim() || '—', expiry: b.querySelector('#spE').value || '—', price: b.querySelector('#spR').value.trim(), off: Math.min(95, Math.max(0, Math.round(+b.querySelector('#spO').value) || 0)) }); st('surplus_new', l); toast('Surplus posted'); later(surplusDialog); } } });
  }

  /* ── 7 · memberships ── */
  function addMembership(co) {
    D.modal({ title: 'Add a membership', body: '<div class="dbk-f"><label for="mbB">Organisation *</label><select id="mbB" data-req><option value="">Choose…</option>' + BODIES.map(function (b) { return '<option>' + esc(b) + '</option>'; }).join('') + '</select></div><div class="dbk-f"><label for="mbN">Membership number *</label><input id="mbN" data-req></div><p class="cp-muted">The organisation confirms your membership before the badge shows.</p>',
      primary: { label: 'Send for confirmation', onClick: function (b) { if (!D.requireFields(b)) return false; var e = st('company_edits') || {}, cur = (e[co.slug] && e[co.slug].memberPending) || []; e[co.slug] = Object.assign({}, e[co.slug] || {}, { memberPending: cur.concat([{ name: b.querySelector('#mbB').value, short: b.querySelector('#mbB').value.split(' ').map(function (w) { return w[0]; }).join('').replace(/[^A-Z]/g, ''), ok: false }]) }); st('company_edits', e); X().render(); toast('Sent to ' + b.querySelector('#mbB').value + ' for confirmation'); } } });
  }

  window.dxVendor = { list: vendorDialog, set: setAvl, get: function () { return avl(); } };
  window.dxDir3 = { AVL: AVL, avl: avl, setAvl: setAvl, vendorDialog: vendorDialog, sendQuestionnaire: sendQuestionnaire, qDeal: function (f, t) { return qDeal(f, t); }, lookingOf: lookingOf, editLooking: editLooking, matchesFor: matchesFor, membersOf: membersOf, addMembership: addMembership,
    dossiers: dossiers, dossierRequest: dossierRequest, addDossier: addDossier, groupDeals: groupDeals, total: total, groupsDialog: groupsDialog, newGroup: newGroup, surplus: surplus, surplusOffer: surplusOffer, postSurplus: postSurplus, dossiersDialog: dossiersDialog, surplusDialog: surplusDialog };
})();
