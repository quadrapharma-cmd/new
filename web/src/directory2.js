/* Company Directory — batch 1
   1 pre-populated pages that companies claim · 2 toll-manufacturer finder with free capacity
   3 one request to several companies + quote comparison · 4 company profile PDF + QR code
   5 search by active ingredient ("who makes Metformin in Egypt?") */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  function X() { return window.dxDir; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function toast(m) { D.toast(m); }
  var MONTHS = (function () { var out = [], d = new Date(); d.setDate(1); for (var i = 0; i < 6; i++) { out.push(d.toLocaleString('en', { month: 'short', year: 'numeric' })); d.setMonth(d.getMonth() + 1); } return out; })();

  /* ── 1 · pre-populated companies from public sources (unclaimed until the company claims them) ── */
  function Pr(name, cat, kind, desc, api, moq) { return { id: 'u' + Math.random().toString(36).slice(2, 8), name: name, cat: cat, kind: kind, desc: desc, api: api || '', moq: moq || '', price: '', specs: [] }; }
  function U(slug, name, sector, sectors, city, gov, color, tagline, products, extra) {
    return Object.assign({ slug: slug, name: name, status: 'unclaimed', owner: null, plan: 'free', licensed: false, verified: false, level: '', rating: 0, reviews: 0, reply: '—', color: color, sector: sector, sectors: sectors,
      city: city, gov: gov, founded: '—', employees: '—', tagline: tagline, about: 'Listed from public industry sources. This page has not been claimed by the company yet — details may be incomplete.',
      certs: [], phone: '', email: '', whatsapp: '', website: '', address: city + ', ' + gov, hours: '', services: [], products: products, jobs: [], source: 'Public industry lists' }, extra || {});
  }
  window.dxDirSeeds = [
    U('nile-valley-pharma', 'Nile Valley Pharmaceuticals', 'Manufacturer', ['Manufacturer', 'CMO / Toll'], '6th of October', 'Giza', '#2563eb', 'Oral solid and liquid generics.',
      [Pr('Metforal 500 mg', 'Finished dosage', 'blister', 'Metformin HCl film-coated tablets, 30s.', 'Metformin', '50,000 tablets'), Pr('Amoxinile 500 mg', 'Finished dosage', 'box', 'Amoxicillin capsules, 16s.', 'Amoxicillin'), Pr('Paranile 500 mg', 'Finished dosage', 'blister', 'Paracetamol tablets, 20s.', 'Paracetamol')]),
    U('obour-medica', 'Obour Medica Industries', 'Manufacturer', ['Manufacturer', 'CMO / Toll'], 'Obour City', 'Qalyubia', '#0f766e', 'Antibiotics and gastro generics.',
      [Pr('Ciproflox 500 mg', 'Finished dosage', 'blister', 'Ciprofloxacin tablets, 10s.', 'Ciprofloxacin'), Pr('Omeprazole 20 mg', 'Finished dosage', 'box', 'Gastro-resistant capsules, 14s.', 'Omeprazole'), Pr('Metformin 850 mg', 'Finished dosage', 'blister', 'Metformin HCl tablets, 30s.', 'Metformin')]),
    U('alexandria-sterile', 'Alexandria Sterile Products', 'Manufacturer', ['Manufacturer', 'CMO / Toll'], 'Borg El Arab', 'Alexandria', '#7c3aed', 'Sterile injectables and eye drops.',
      [Pr('Ceftriaxone 1 g vial', 'Finished dosage', 'bottle', 'Powder for injection.', 'Ceftriaxone'), Pr('Artificial Tears 10 mL', 'Finished dosage', 'bottle', 'Hypromellose eye drops.', 'Hypromellose')]),
    U('ramadan-pharma', 'Ramadan Pharma Industries', 'Manufacturer', ['Manufacturer', 'CMO / Toll', 'Supplements'], '10th of Ramadan', 'Sharqia', '#c2410c', 'Effervescents, sachets and supplements.',
      [Pr('Vitamin C 1000 Effervescent', 'Supplements', 'box', 'Ascorbic acid effervescent tablets, 20s.', 'Ascorbic acid'), Pr('Paracetamol 500 Sachets', 'Finished dosage', 'sachet', 'Paracetamol powder sachets.', 'Paracetamol')]),
    U('orient-cosmetics', 'Orient Cosmetics Manufacturing', 'Cosmetics', ['Cosmetics', 'CMO / Toll'], '6th of October', 'Giza', '#db2777', 'Creams, serums and shampoos — private label.',
      [Pr('Niacinamide 10% Serum', 'Cosmetics', 'bottle', '30 mL serum.', 'Niacinamide'), Pr('Hyaluronic Moisturiser', 'Cosmetics', 'jar', '50 g cream.', 'Hyaluronic acid')]),
    U('cairo-api-trading', 'Cairo API Trading', 'API & excipients', ['API & excipients', 'Distribution'], 'Cairo', 'Cairo', '#16a34a', 'Importer of APIs with local stock.',
      [Pr('Metformin HCl API', 'API', 'drum', 'BP/USP, 25 kg drums.', 'Metformin', '500 kg'), Pr('Paracetamol DC Grade', 'API', 'drum', 'Directly compressible, 25 kg.', 'Paracetamol', '500 kg'), Pr('Amoxicillin Trihydrate', 'API', 'drum', 'Compacted, 25 kg.', 'Amoxicillin', '100 kg')]),
    U('suez-pharma-packaging', 'Suez Pharma Packaging', 'Packaging', ['Packaging'], 'Ismailia', 'Ismailia', '#475569', 'PET and HDPE bottles for pharma.',
      [Pr('Amber PET Bottle 100 mL', 'Packaging', 'bottle', 'With child-resistant cap.', '', '10,000 pcs'), Pr('HDPE Container 500 cc', 'Packaging', 'jar', 'For tablets and capsules.', '', '10,000 pcs')]),
    U('giza-bioequivalence', 'Giza Bioequivalence Center', 'Labs & testing', ['Labs & testing'], 'Giza', 'Giza', '#9333ea', 'Bioequivalence and dissolution studies.',
      [Pr('Bioequivalence Study', 'Service', 'lab', 'Two-way crossover BE study with EDA-format report.', '', '1 study')])
  ];

  /* ── 2 · manufacturing capabilities (who can make what, and when) ── */
  var CAP = {
    'quadra-pharm': { forms: ['Tablets', 'Capsules', 'Sachets', 'Syrups'], minBatch: '50,000 units', capacity: '3M tablets / month', slots: [1, 2, 4] },
    'medsinia-industries': { forms: ['Tablets', 'Capsules', 'Sachets'], minBatch: '100,000 units', capacity: '8M tablets / month', slots: [0, 1, 3, 5] },
    'beauty-lab-egypt': { forms: ['Creams', 'Serums', 'Shampoos'], minBatch: '3,000 units', capacity: '120,000 units / month', slots: [0, 2, 3] },
    'nile-valley-pharma': { forms: ['Tablets', 'Capsules', 'Syrups'], minBatch: '50,000 units', capacity: '5M tablets / month', slots: [2, 3, 5] },
    'obour-medica': { forms: ['Tablets', 'Capsules'], minBatch: '100,000 units', capacity: '6M tablets / month', slots: [1, 4] },
    'alexandria-sterile': { forms: ['Sterile injectables', 'Eye drops'], minBatch: '10,000 vials', capacity: '400,000 vials / month', slots: [3, 4] },
    'ramadan-pharma': { forms: ['Effervescent tablets', 'Sachets', 'Tablets'], minBatch: '20,000 units', capacity: '2M units / month', slots: [0, 1, 2] },
    'orient-cosmetics': { forms: ['Creams', 'Serums', 'Shampoos', 'Gels'], minBatch: '5,000 units', capacity: '200,000 units / month', slots: [1, 2, 5] }
  };
  var FORMS = ['Tablets', 'Capsules', 'Sachets', 'Syrups', 'Effervescent tablets', 'Sterile injectables', 'Eye drops', 'Creams', 'Serums', 'Gels', 'Shampoos'];
  function capOf(co) { var e = X().edits()[co.slug]; return (e && e.cap && typeof e.cap === 'object' && Array.isArray(e.cap.forms) && Array.isArray(e.cap.slots) ? e.cap : null) || CAP[co.slug] || null; }

  function finderDialog() {
    var m = D.modal({ title: 'Find a toll manufacturer', secondary: 'Close',
      body: '<div class="fd-form"><div class="dbk-f"><label for="fdForm">Dosage form *</label><select id="fdForm">' + FORMS.map(function (f) { return '<option>' + f + '</option>'; }).join('') + '</select></div>' +
        '<div class="dbk-f"><label for="fdQty">Monthly quantity</label><input id="fdQty" inputmode="numeric" placeholder="e.g. 500000"></div>' +
        '<div class="dbk-f"><label for="fdFrom">Start from</label><select id="fdFrom">' + MONTHS.map(function (x, i) { return '<option value="' + i + '">' + x + '</option>'; }).join('') + '</select></div>' +
        '<div class="dbk-f"><label for="fdCert">Certificate</label><select id="fdCert"><option value="">Any</option><option>WHO-GMP</option><option>ISO 9001</option><option>ISO 22716</option></select></div></div>' +
        '<div id="fdRes" class="fd-res"></div>' });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    function run() {
      var form = m.el.querySelector('#fdForm').value, from = +m.el.querySelector('#fdFrom').value, cert = m.el.querySelector('#fdCert').value;
      var rows = X().companies().map(function (co) {
        var cap = capOf(co); if (!cap || cap.forms.indexOf(form) < 0) return null;
        var next = cap.slots.filter(function (s) { return s >= from; })[0], score = 50 + (next != null ? 25 - (next - from) * 5 : 0) + (cert && co.certs.indexOf(cert) >= 0 ? 15 : 0) + (co.status === 'verified' ? 10 : 0);
        if (cert && co.certs.indexOf(cert) < 0) score -= 30;
        return { co: co, cap: cap, next: next, score: score };
      }).filter(Boolean).sort(function (a, b) { return b.score - a.score; });
      var res = m.el.querySelector('#fdRes');
      res.innerHTML = rows.length ? '<div class="fd-h">' + rows.length + ' manufacturer' + (rows.length === 1 ? '' : 's') + ' make ' + esc(form.toLowerCase()) + '</div>' + rows.map(function (r) {
        return '<label class="fd-row"><input type="checkbox" value="' + r.co.slug + '"' + (r.next != null ? ' checked' : '') + '>' + X().logo(r.co, 'dr-logo sm') + '<span class="fd-b"><b>' + esc(r.co.name) + (r.co.status === 'unclaimed' ? ' <em class="dr-pend unc">Unclaimed</em>' : r.co.status === 'verified' ? ' ' + ic('seal') : '') + '</b>' +
          '<small>' + esc(r.cap.forms.join(' · ')) + ' · min ' + esc(r.cap.minBatch) + ' · ' + esc(r.cap.capacity) + '</small>' +
          '<span class="fd-tags">' + (r.next != null ? '<span class="fd-slot">Free from ' + MONTHS[r.next] + '</span>' : '<span class="fd-slot no">No free slot in this window</span>') + (r.co.certs || []).map(function (c) { return '<span class="fd-cert' + (c === cert ? ' hit' : '') + '">' + esc(c) + '</span>'; }).join('') + '</span></span>' +
          '<button type="button" class="dr-btn sm" data-fdopen="' + r.co.slug + '">Page</button></label>'; }).join('') +
        '<div class="fd-act"><button type="button" class="dr-btn p" id="fdSend">' + ic('send') + 'Request quotes from selected</button></div>'
        : '<div class="dbk-empty">No manufacturer lists this dosage form yet.</div>';
    }
    m.el.addEventListener('change', function (e) { if (e.target.matches('#fdForm, #fdFrom, #fdCert')) run(); });   /* quantity does not change the results — no re-render that could swallow a click */
    m.el.addEventListener('click', function (e) {
      var o = e.target.closest('[data-fdopen]'); if (o) { e.preventDefault(); m.close(); setTimeout(function () { X().open(o.dataset.fdopen); }, 40); return; }
      if (e.target.closest('#fdSend')) {
        var picked = Array.prototype.map.call(m.el.querySelectorAll('.fd-row input:checked'), function (i) { return i.value; });
        if (!picked.length) { toast('Select at least one manufacturer'); return; }
        var form = m.el.querySelector('#fdForm').value, qty = m.el.querySelector('#fdQty').value.trim();
        m.close(); setTimeout(function () { bulkRfqDialog(picked, { what: 'Toll manufacturing — ' + form, qty: qty, unit: /Creams|Serums|Gels|Shampoos|Syrups|Eye|Sterile/.test(form) ? 'units' : 'tablets' }); }, 40);
      }
    });
    run();
  }

  /* ── 3 · one request to several companies, then compare their quotes ── */
  var picks = [];
  var tray = document.createElement('div'); tray.id = 'dxRfqTray'; document.body.appendChild(tray);
  function drawTray() {
    var on = picks.length && document.getElementById('dxDir') && !X().S.open && !X().S.view;
    tray.className = on ? 'on' : '';
    tray.innerHTML = on ? '<span>' + ic('send') + '<b>' + picks.length + '</b> selected</span><button type="button" class="tr-go">Request quotes from ' + picks.length + '</button><button type="button" class="tr-x">Clear</button>' : '';
  }
  tray.addEventListener('click', function (e) {
    if (e.target.closest('.tr-x')) { picks = []; document.querySelectorAll('.dr-pick input').forEach(function (i) { i.checked = false; }); drawTray(); }
    if (e.target.closest('.tr-go')) bulkRfqDialog(picks.slice());
  });
  window.dxPicks = { get: function () { return picks; }, set: function (p) { picks = p; drawTray(); }, draw: function () { drawTray(); } };
  /* the hub draws the Select boxes on its cards (data-hpick) and reads window.dxPicks */
  function bulkRfqDialog(slugs, preset) {
    preset = preset || {};
    var act = X().mine(), cos = slugs.map(function (s) { return X().bySlug(s); }).filter(function (c) { return c && !(act && c.slug === act.slug); });   /* never your own company */
    if (!act) { toast('Create or claim your company page first'); return; }   /* quotes are requested on behalf of a company */
    if (!cos.length) { toast('Select other companies — not the one you act as'); return; }
    D.modal({ title: 'Request quotes from ' + cos.length + ' companies',
      body: '<div class="bq-to">' + cos.map(function (c) { return '<span>' + X().logo(c, 'cs-logo') + esc(c.name) + '</span>'; }).join('') + '</div>' + (act ? '<div class="rq-to">' + ic('building') + 'Requesting as <b>' + esc(act.name) + '</b></div>' : '') +
        '<div class="dbk-f"><label for="bqWhat">What do you need? *</label><input id="bqWhat" data-req value="' + esc(preset.what || '') + '" placeholder="e.g. Metformin HCl BP, or Toll manufacturing — tablets"></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="bqQty">Quantity *</label><input id="bqQty" data-req inputmode="decimal" value="' + esc(preset.qty || '') + '"></div><div class="dbk-f"><label for="bqUnit">Unit</label><select id="bqUnit">' + ['kg', 'MT', 'units', 'tablets', 'cartons', 'batches'].map(function (u) { return '<option' + (u === preset.unit ? ' selected' : '') + '>' + u + '</option>'; }).join('') + '</select></div></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="bqTo">Deliver to</label><input id="bqTo" value="Cairo, Egypt"></div><div class="dbk-f"><label for="bqInc">Delivery terms</label><select id="bqInc"><option>EXW</option><option>FOB</option><option selected>CIF</option><option>DDP</option></select></div></div>' +
        '<div class="dbk-f"><label for="bqMsg">Message *</label><textarea id="bqMsg" data-req placeholder="Specs, certificates, payment terms…"></textarea></div>' +
        '<div class="dbk-note">Each company receives its own request and cannot see the others. Quotes are collected side by side in My requests.</div>',
      primary: { label: 'Send to ' + cos.length + ' companies', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var group = Date.now(), what = b.querySelector('#bqWhat').value.trim(), unit = b.querySelector('#bqUnit').value, inc = b.querySelector('#bqInc').value, qty = b.querySelector('#bqQty').value.trim(), msg = b.querySelector('#bqMsg').value.trim(), me = window.ME || {};
        cos.forEach(function (co) { window.dxDeals.create('quote', co.slug, what, { qty: qty, unit: unit, inc: inc, to: b.querySelector('#bqTo').value.trim() }, msg, { group: group }); });
        picks = []; document.querySelectorAll('.dr-pick input').forEach(function (i) { i.checked = false; }); drawTray();
        toast('Sent to ' + cos.length + ' companies — compare their quotes in Requests & deals');
      } } });
  }
  function parseQuote(q) { var m = q.match(/US\$\s*([\d.]+)/); return m ? parseFloat(m[1]) : Infinity; }
  window.dxCompareQuotes = function (group) {
    var DL = window.dxDeals, rows = DL.all().filter(function (d) { return d.group === group; });
    if (!rows.length) return;
    function num(p) { var m = String(p || '').match(/[\d.]+/); return m ? parseFloat(m[0]) : Infinity; }
    var data = rows.map(function (d) { var co = X().bySlug(d.to.slug) || {}; return { d: d, co: co, price: d.offer && ['quoted', 'accepted', 'confirmed', 'shipped', 'delivered', 'closed'].indexOf(d.status) >= 0 ? num(d.offer.price) : Infinity }; });
    var best = Math.min.apply(null, data.map(function (x) { return x.price; }));
    var m = D.modal({ title: 'Compare quotes', secondary: 'Close',
      body: '<p class="cp-muted">' + esc(rows[0].title) + ' · ' + esc(rows[0].lines.qty || '') + ' ' + esc(rows[0].lines.unit || '') + ' · sent ' + new Date(rows[0].at).toLocaleString() + '</p><div class="cmp-wrap"><table class="cmp"><thead><tr><th>Company</th><th>Price</th><th>Terms</th><th>Supplier rating</th><th>Status</th><th></th></tr></thead><tbody>' +
        data.sort(function (a, b) { return a.price - b.price; }).map(function (x) { var d = x.d, o = d.offer;
          return '<tr><td><b>' + esc(d.to.name) + '</b>' + (x.co.status === 'verified' ? ' ' + ic('seal') : '') + '</td><td' + (x.price === best && isFinite(best) ? ' class="best"' : '') + '>' + (isFinite(x.price) ? esc(o.price) + (x.price === best ? '<small>Lowest</small>' : '') : '—') + '</td>' +
            '<td>' + (o ? esc([o.terms, o.validity ? 'valid ' + o.validity : '', o.lead].filter(Boolean).join(' · ')) : '') + '</td><td>' + (x.co.reviews ? '★ ' + x.co.rating.toFixed(1) : '—') + '</td><td>' + '<span class="mr-st">' + esc(DL.label(d.status)) + '</span></td>' +
            '<td>' + (d.status === 'quoted' ? '<button type="button" class="dr-btn p sm" data-accq="' + d.id + '">Accept</button>' : d.status === 'sent' ? '<button type="button" class="dr-btn sm" data-simq="' + d.id + '">Simulate reply (demo)</button>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>' });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    m.el.addEventListener('click', function (e) {
      var s = e.target.closest('[data-simq]'); if (s) { DL.simulate(s.dataset.simq); m.close(); setTimeout(function () { window.dxCompareQuotes(group); }, 40); return; }
      var a = e.target.closest('[data-accq]'); if (!a) return;
      DL.act(a.dataset.accq, 'accept', {}, 'from');
      rows.forEach(function (d) { var cur = DL.get(d.id); if (cur.id !== a.dataset.accq && cur.status === 'quoted') DL.act(cur.id, 'decline', { note: 'Another supplier was selected' }, 'from'); });
      m.close(); var w = DL.get(a.dataset.accq); toast('Accepted ' + w.to.name + '\u2019s quote — the other quotes were declined politely');
    });
  };

  /* ── 4 · company profile (PDF) + QR code ── */
  function pageUrl(co) { return 'https://' + (X().isVip(co) ? co.slug + '.drugbox.app' : 'drugbox.app/c/' + co.slug); }
  function qrSvg(text, size) { if (!window.qrcode) return ''; var q = window.qrcode(0, 'M'); q.addData(text); q.make(); var n = q.getModuleCount(), cell = Math.max(2, Math.floor((size || 200) / (n + 4))); return q.createSvgTag({ cellSize: cell, margin: cell * 2, scalable: true }); }
  function qrDialog(co) {
    var url = pageUrl(co), svg = qrSvg(url, 240), blob = new Blob([svg], { type: 'image/svg+xml' }), href = URL.createObjectURL(blob);
    D.modal({ title: 'QR code — ' + co.name, secondary: 'Close', body: '<div class="qr-box">' + svg + '<div class="qr-u">' + esc(url) + '</div><p class="cp-muted">Print it on business cards, exhibition stands, cartons or trucks — it opens your company page.</p>' +
      '<a class="dr-btn p" download="' + esc(co.slug) + '-qr.svg" href="' + href + '">' + ic('send') + 'Download QR (SVG)</a></div>' });
  }
  function brochure(co) {
    var url = pageUrl(co), cap = capOf(co), w = window.open('', '_blank');
    if (!w) { toast('Allow pop-ups to create the PDF'); return; }
    var lg = X().safeUrl(co.logo), logo = lg ? '<img class="lg" src="' + esc(lg) + '">' : '<div class="lg" style="background:' + X().safeColor(co.color) + '">' + esc(X().initials(co.name)) + '</div>';
    w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>' + esc(co.name) + ' — Company profile</title><style>' +
      '@page{size:A4;margin:14mm}*{box-sizing:border-box}body{font-family:Poppins,Arial,sans-serif;color:#0E1320;margin:0}h1{font-size:28px;margin:0}h2{font-size:15px;color:#1a56db;text-transform:uppercase;letter-spacing:.08em;margin:22px 0 8px;border-bottom:2px solid #E6E8EE;padding-bottom:4px}' +
      '.top{display:flex;gap:16px;align-items:center;border-bottom:6px solid ' + X().safeColor(co.color) + ';padding-bottom:14px}.lg{width:70px;height:78px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:24px;clip-path:polygon(50% 0,100% 25%,100% 75%,50% 100%,0 75%,0 25%);object-fit:cover}' +
      '.tag{color:#374151;margin:4px 0 0}.meta{color:#64748b;font-size:12px;margin-top:2px}.qr{margin-left:auto;text-align:center;font-size:9px;color:#64748b}.qr svg{width:92px;height:92px}' +
      '.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.facts div{background:#F4F6FA;border-radius:8px;padding:8px}.facts small{display:block;color:#64748b;font-size:10px}' +
      '.prods{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.p{border:1px solid #E6E8EE;border-radius:10px;padding:8px;break-inside:avoid}.p img{width:100%;height:110px;object-fit:cover;border-radius:6px;background:#F6F8FC}.p b{display:block;font-size:12.5px;margin-top:4px}.p small{color:#64748b;font-size:10.5px}' +
      '.chips span{display:inline-block;border:1px solid #BBF7D0;background:#ECFDF5;color:#047857;border-radius:99px;padding:2px 9px;font-size:11px;margin:0 4px 4px 0}ul{margin:0;padding-left:18px;font-size:12.5px}td{padding:4px 8px 4px 0;font-size:12.5px;vertical-align:top}.ft{margin-top:24px;font-size:10px;color:#94a3b8;border-top:1px solid #E6E8EE;padding-top:6px}' +
      '</style></head><body><div class="top">' + logo + '<div><h1>' + esc(co.name) + '</h1><p class="tag">' + esc(co.tagline) + '</p><div class="meta">' + esc(co.sectors.join(' · ')) + ' · ' + esc(co.city) + ', ' + esc(co.gov) + (co.status === 'verified' ? ' · Verified on Drugbox' : '') + '</div></div><div class="qr">' + qrSvg(url, 92) + '<div>' + esc(url.replace('https://', '')) + '</div></div></div>' +
      '<h2>About</h2><p style="font-size:13px;line-height:1.6">' + esc(co.about) + '</p><div class="facts"><div><small>Founded</small>' + esc(co.founded) + '</div><div><small>Team</small>' + esc(co.employees) + '</div><div><small>Location</small>' + esc(co.city) + '</div><div><small>Products</small>' + co.products.length + '</div></div>' +
      (co.certs.length ? '<h2>Certificates</h2><div class="chips">' + co.certs.map(function (c) { return '<span>' + esc(c) + '</span>'; }).join('') + '</div>' : '') +
      (cap ? '<h2>Manufacturing capabilities</h2><table><tr><td><b>Dosage forms</b></td><td>' + esc(cap.forms.join(', ')) + '</td></tr><tr><td><b>Minimum batch</b></td><td>' + esc(cap.minBatch) + '</td></tr><tr><td><b>Capacity</b></td><td>' + esc(cap.capacity) + '</td></tr></table>' : '') +
      (co.products.length ? '<h2>Products</h2><div class="prods">' + co.products.map(function (p) { return '<div class="p"><img src="' + X().pimg(co, p) + '"><b>' + esc(p.name) + '</b><small>' + esc(p.cat) + (p.moq ? ' · MOQ ' + esc(p.moq) : '') + '</small></div>'; }).join('') + '</div>' : '') +
      ((co.services || []).length ? '<h2>Services</h2><ul>' + co.services.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ul>' : '') +
      '<h2>Contact</h2><table>' + [['Phone', co.phone], ['Email', co.email], ['WhatsApp', co.whatsapp ? '+' + co.whatsapp : ''], ['Website', co.website], ['Address', co.address], ['Hours', co.hours]].filter(function (r) { return r[1]; }).map(function (r) { return '<tr><td><b>' + r[0] + '</b></td><td>' + esc(r[1]) + '</td></tr>'; }).join('') + '</table>' +
      '<div class="ft">Company profile generated by Drugbox · ' + new Date().toLocaleDateString() + ' · ' + esc(url) + '</div><script>window.onload=function(){setTimeout(function(){window.print()},300)}<\/script></body></html>');
    w.document.close();
  }

  /* ── 5 · who makes an active ingredient ── */
  var INN = ['Metformin', 'Paracetamol', 'Amoxicillin', 'Ciprofloxacin', 'Omeprazole', 'Ceftriaxone', 'Ascorbic acid', 'Vitamin C', 'Niacinamide', 'Hyaluronic acid', 'Neomycin', 'Hypromellose', 'Ibuprofen', 'Azithromycin', 'Atorvastatin', 'Amlodipine', 'Diclofenac', 'Cholecalciferol', 'Vitamin D3'];
  function apiOf(p) { if (p.api) return p.api; var h = (p.name + ' ' + p.desc).toLowerCase(); for (var i = 0; i < INN.length; i++) if (h.indexOf(INN[i].toLowerCase()) >= 0) return INN[i]; return ''; }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-wmco]'); if (a) { e.stopPropagation(); X().open(a.dataset.wmco, 'products'); return; }
    var r = e.target.closest && e.target.closest('[data-wmrfq]'); if (r) { e.stopPropagation(); X().rfq(r.dataset.wmrfq, r.dataset.wmp); }
  }, true);

  /* ── claim an unclaimed page (opened from the hub's claim banner) ── */
  function claimDialog(co) {
    var me = window.ME || {}, code = String(1000 + Math.floor(Math.random() * 9000));
    D.modal({ title: 'Claim ' + co.name, body: '<p class="cp-muted">Prove you work at ' + esc(co.name) + ' and the page becomes yours to manage. Nothing is published until you edit it.</p>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="clRole">Your role *</label><input id="clRole" data-req placeholder="e.g. Business Development Manager"></div><div class="dbk-f"><label for="clPhone">Mobile *</label><input id="clPhone" data-req inputmode="tel"></div></div>' +
      '<div class="dbk-f"><label for="clMail">Work email *</label><input id="clMail" data-req type="email" placeholder="you@company.com"></div>',
      primary: { label: 'Send code', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var mail = b.querySelector('#clMail').value.trim();
        setTimeout(function () {
          D.modal({ title: 'Enter the code', body: '<p class="cp-muted">We sent a 4-digit code to ' + esc(mail) + '. <span class="cl-demo">Demo code: <b>' + code + '</b></span></p><div class="dbk-f"><label for="clCode">Code *</label><input id="clCode" data-req inputmode="numeric" maxlength="4"></div>',
            primary: { label: 'Claim page', onClick: function (b2) {
              if (b2.querySelector('#clCode').value.trim() !== code) { b2.querySelector('#clCode').classList.add('dbk-err'); toast('Wrong code'); return false; }
              var edits = X().store('company_edits') || {}; edits[co.slug] = Object.assign({}, edits[co.slug] || {}, { owner: me.id, status: 'unverified', claimed: true, claimedAt: Date.now(), email: mail, phone: b2 ? co.phone : co.phone, about: co.about.indexOf('public industry sources') >= 0 ? '' : co.about });
              X().store('company_edits', edits); X().store('acting', co.slug); if (window.dxHub) { window.dxHub.log(co.slug, 'Claimed the company page'); window.dxHub.workspace(co.slug); } else X().render(); toast('You now manage ' + co.name + ' — complete the page and get verified');
            } } });
        }, 40);
      } } });
  }
  window.dxFindToll = finderDialog;
  window.dxDir2 = { bulk: function (slugs, preset) { bulkRfqDialog(slugs, preset); }, brochure: brochure, qr: qrDialog, claim: claimDialog, capOf: capOf, MONTHS: MONTHS, FORMS: FORMS, apiOf: apiOf, INN: INN, CAP: CAP };

  document.addEventListener('dx:page', drawTray);
})();
