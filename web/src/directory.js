/* Company Directory — every Egyptian pharma company gets a page that works like its own small website.
   Directory (search + filters) → Company page (about, products with photos, services, jobs, contact)
   → Request a quote / service / apply for a job. Owners edit their page and see incoming requests. */
(function () {
  var C = window.dxCore; if (!C) return;
  var D = window.DBK;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ic(n) { return window.dxIcon ? window.dxIcon(n) : ''; }
  var __A = /^(deals|created_companies|reports|dossiers|surplus_new|groups_new|follows|saved_searches|my_requests|activity_.*|inbox_.*)$/, __O = /^(company_edits|supplier_reviews|review_meta|avl_.*|groups_state|meta_.*|quoted_.*|sqq_.*)$/, __S = /^(acting|role)$/;
  function __typed(k, v) { if (v == null) return null; if (__A.test(k)) return Array.isArray(v) ? v : null; if (__O.test(k)) return (typeof v === 'object' && !Array.isArray(v)) ? v : null; if (__S.test(k)) return typeof v === 'string' ? v : null; return v; }   /* a stored value of the wrong type is ignored, never trusted */
  function store(k, v) { if (window.dxStoreHook) { var __h = window.dxStoreHook(k, v); if (__h !== undefined) return __h; } try { if (v === undefined) return __typed(k, JSON.parse(localStorage.getItem('dx_' + k) || 'null')); localStorage.setItem('dx_' + k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function toast(m) { if (D) D.toast(m); }

  /* ── product pictures (packshots) drawn in the company's colour; owners replace them with real photos ── */
  function packshot(kind, color, label) {
    var c = color || '#1a56db', l = esc(String(label || '').slice(0, 14)), body;
    var S = {
      box: '<rect x="70" y="70" width="160" height="170" rx="10" fill="#fff" stroke="' + c + '" stroke-width="4"/><rect x="70" y="70" width="160" height="46" rx="10" fill="' + c + '"/><path d="M70 70l20-24h120l20 24" fill="#fff" stroke="' + c + '" stroke-width="4"/><rect x="92" y="138" width="116" height="10" rx="5" fill="' + c + '" opacity=".25"/><rect x="92" y="158" width="80" height="10" rx="5" fill="' + c + '" opacity=".18"/>',
      bottle: '<rect x="128" y="40" width="44" height="30" rx="6" fill="' + c + '"/><path d="M112 80h76l12 30v120a14 14 0 0 1-14 14h-72a14 14 0 0 1-14-14V110z" fill="#fff" stroke="' + c + '" stroke-width="4"/><rect x="100" y="140" width="100" height="62" rx="8" fill="' + c + '" opacity=".92"/>',
      jar: '<rect x="96" y="70" width="108" height="30" rx="8" fill="' + c + '"/><rect x="84" y="98" width="132" height="140" rx="22" fill="#fff" stroke="' + c + '" stroke-width="4"/><rect x="84" y="140" width="132" height="54" fill="' + c + '" opacity=".92"/>',
      drum: '<rect x="82" y="56" width="136" height="188" rx="16" fill="#fff" stroke="' + c + '" stroke-width="4"/><path d="M82 96h136M82 204h136" stroke="' + c + '" stroke-width="4"/><rect x="82" y="120" width="136" height="60" fill="' + c + '" opacity=".92"/>',
      tube: '<path d="M112 60h76l-6 150a8 8 0 0 1-8 8h-48a8 8 0 0 1-8-8z" fill="#fff" stroke="' + c + '" stroke-width="4"/><rect x="120" y="218" width="60" height="24" rx="4" fill="' + c + '"/><rect x="116" y="110" width="68" height="56" rx="6" fill="' + c + '" opacity=".92"/>',
      blister: '<rect x="62" y="80" width="176" height="140" rx="14" fill="#fff" stroke="' + c + '" stroke-width="4"/>' + [0, 1, 2, 3].map(function (i) { return [0, 1].map(function (j) { return '<ellipse cx="' + (98 + i * 35) + '" cy="' + (124 + j * 52) + '" rx="13" ry="18" fill="' + c + '" opacity=".85"/>'; }).join(''); }).join(''),
      sachet: '<path d="M96 60h108l-6 180H102z" fill="#fff" stroke="' + c + '" stroke-width="4"/><path d="M96 60l12 12h84l12-12" fill="none" stroke="' + c + '" stroke-width="3" stroke-dasharray="6 5"/><rect x="104" y="120" width="92" height="62" rx="8" fill="' + c + '" opacity=".92"/>',
      lab: '<path d="M126 50h48M134 50v60l-44 96a14 14 0 0 0 13 20h94a14 14 0 0 0 13-20l-44-96V50" fill="#fff" stroke="' + c + '" stroke-width="4"/><path d="M104 176h92l14 30a8 8 0 0 1-7 12H97a8 8 0 0 1-7-12z" fill="' + c + '" opacity=".9"/>'
    };
    body = S[kind] || S.box;
    var labelY = { box: 206, bottle: 177, jar: 173, drum: 156, tube: 144, blister: 250, sachet: 157, lab: 250 }[kind] || 206;
    var col = kind === 'box' || kind === 'blister' || kind === 'lab' ? c : '#fff';
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300"><rect width="300" height="300" fill="#F6F8FC"/><circle cx="150" cy="150" r="118" fill="' + c + '" opacity=".07"/>' + body +
      '<text x="150" y="' + labelY + '" text-anchor="middle" font-family="Poppins,Arial,sans-serif" font-size="17" font-weight="700" fill="' + col + '">' + l + '</text></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  /* ── seed directory (demo) ── */
  function P(name, cat, kind, desc, moq, price, specs) { return { id: 'p' + Math.random().toString(36).slice(2, 8), name: name, cat: cat, kind: kind, desc: desc, moq: moq || '', price: price || '', specs: specs || [] }; }
  var SEED = [
    { slug: 'quadra-pharm', registry: '100100', plan: 'vip', licensed: true, status: 'verified', name: 'Quadra Pharm', owner: 1, color: '#1a56db', sector: 'Manufacturer', sectors: ['Manufacturer', 'CMO / Toll'], city: 'Giza', gov: 'Giza', founded: 2010, employees: '120–200', verified: true, level: 'gold', rating: 4.6, reviews: 23, reply: '2h',
      tagline: 'Solid and liquid dosage forms, regulatory affairs and toll manufacturing for Egypt, the GCC and Africa.',
      about: 'Quadra Pharm develops, registers and manufactures pharmaceutical and cosmetic products under WHO-GMP. We partner with brand owners through toll manufacturing and licensing, and handle EDA registration end to end.',
      certs: ['WHO-GMP', 'ISO 9001', 'EDA licensed'], phone: '+20 2 3456 7890', email: 'info@quadrapharm.com', whatsapp: '201000000001', website: 'quadrapharm.com', address: 'Smart Village, Giza, Egypt', hours: 'Sun–Thu · 9:00–17:00',
      services: ['Toll manufacturing — tablets, capsules, sachets, syrups', 'EDA registration and variations', 'Technology transfer', 'Stability studies (Zone IVa)'],
      products: [P('Dramrin Sachets', 'Finished dosage', 'sachet', 'Oral powder in sachets. Registered with EDA.', '10,000 sachets', '', ['Pack: 10 sachets / box', 'Shelf life: 24 months']), P('Hair Serum', 'Cosmetics', 'bottle', 'Leave-in hair growth serum, 50 mL.', '5,000 units', 'US$ 2.10', ['Volume: 50 mL', 'Notified with EDA cosmetics']),
        P('Film-coated Tablets', 'Toll manufacturing', 'blister', 'Your formula, our WHO-GMP line — from 50,000 tablets.', '50,000 tablets', '', ['Blister: Alu/PVC', 'Capacity: 3M tablets/month']), P('Oral Suspension', 'Finished dosage', 'bottle', 'Paediatric suspension, 100 mL.', '5,000 bottles', '', ['Volume: 100 mL'])],
      jobs: [{ t: 'Senior Regulatory Affairs Specialist', type: 'Full-time', loc: 'Giza' }, { t: 'Country Manager — Egypt & North Africa', type: 'Full-time', loc: 'Giza' }], team: [1, 2] },
    { slug: 'medsinia-industries', registry: '101217', plan: 'free', licensed: true, status: 'verified', name: 'Medsinia Industries', owner: 5, color: '#0E8C66', sector: 'Manufacturer', sectors: ['Manufacturer', 'CMO / Toll'], city: '10th of Ramadan', gov: 'Sharqia', founded: 2014, employees: '200–500', verified: true, level: 'silver', rating: 4.4, reviews: 17, reply: '3h',
      tagline: 'High-volume solid dosage manufacturing with continuous lines.', about: 'Medsinia runs tablet and capsule lines in 10th of Ramadan City, serving local brands and exporters.', certs: ['WHO-GMP', 'ISO 9001'],
      phone: '+20 55 441 2200', email: 'sales@medsinia.example', whatsapp: '201000000002', website: 'medsinia.example', address: '10th of Ramadan City, Sharqia', hours: 'Sat–Thu · 8:00–16:00',
      services: ['Tablet and capsule toll manufacturing', 'Purified water sachets', 'Packaging and serialization'],
      products: [P('Paracetamol 500 mg', 'Finished dosage', 'blister', 'Film-coated tablets, 20s.', '100,000 tablets'), P('Purified Water BP 50 mL', 'Finished dosage', 'sachet', 'Purified water sachets for reconstitution.', '20,000 sachets', 'US$ 0.32'), P('Vitamin C 1000', 'Supplements', 'box', 'Effervescent tablets.', '10,000 tubes')],
      jobs: [{ t: 'Production Supervisor — Solid Dosage', type: 'Full-time', loc: '10th of Ramadan' }, { t: 'Junior Lab Technician — Fresh Graduate', type: 'Full-time', loc: '10th of Ramadan' }], team: [5] },
    { slug: 'beauty-lab-egypt', registry: '102334', plan: 'free', licensed: true, status: 'verified', name: 'Beauty Lab Egypt', color: '#be185d', sector: 'Cosmetics', sectors: ['Cosmetics', 'CMO / Toll'], city: 'Cairo', gov: 'Cairo', founded: 2016, employees: '50–120', verified: true, level: 'bronze', rating: 4.1, reviews: 9, reply: '6h',
      tagline: 'Skincare and haircare formulation and private label.', about: 'Formulation lab and filling lines for creams, serums and shampoos. ISO 22716 certified.', certs: ['ISO 22716', 'EDA licensed'],
      phone: '+20 2 2750 1100', email: 'hello@beautylab.example', whatsapp: '201000000003', website: 'beautylab.example', address: 'Nasr City, Cairo', hours: 'Sun–Thu · 9:00–17:00',
      services: ['Private label skincare', 'Formulation development', 'EDA cosmetics notification'], products: [P('Hyaluronic Serum 30 mL', 'Cosmetics', 'bottle', 'Dual molecular-weight HA serum.', '3,000 units'), P('Niacinamide Cream', 'Cosmetics', 'jar', '50 g day cream.', '3,000 jars'), P('Keratin Shampoo', 'Cosmetics', 'tube', '250 mL.', '5,000 units')],
      jobs: [{ t: 'Cosmetic Formulation Scientist', type: 'Full-time', loc: 'Cairo' }] },
    { slug: 'nile-pharma-packaging', registry: '103451', plan: 'free', licensed: false, status: 'verified', name: 'Nile Pharma Packaging', color: '#475569', sector: 'Packaging', sectors: ['Packaging'], city: 'Alexandria', gov: 'Alexandria', founded: 2008, employees: '120–200', verified: true, level: '', rating: 4.3, reviews: 12, reply: '4h',
      tagline: 'Printed cartons, leaflets, labels and blister foil for pharma.', about: 'GMP-grade printing and converting for pharmaceutical packaging, with artwork approval and serialization-ready codes.', certs: ['ISO 9001', 'ISO 15378'],
      phone: '+20 3 420 1000', email: 'orders@nilepack.example', whatsapp: '201000000004', website: 'nilepack.example', address: 'Borg El Arab, Alexandria', hours: 'Sun–Thu · 8:00–16:00',
      services: ['Folding cartons', 'Leaflets & outserts', 'Labels', 'Blister lidding foil'], products: [P('Folding Cartons', 'Packaging', 'box', 'Offset-printed cartons with Braille.', '20,000 cartons'), P('Alu Blister Foil', 'Packaging', 'blister', 'Printed lidding foil, 20 µm.', '500 kg'), P('Patient Leaflets', 'Packaging', 'box', 'Bilingual Arabic/English leaflets.', '50,000 pcs')], jobs: [] },
    { slug: 'delta-analytical-labs', registry: '104568', plan: 'free', licensed: false, status: 'verified', name: 'Delta Analytical Labs', color: '#7c3aed', sector: 'Labs & testing', sectors: ['Labs & testing'], city: 'Cairo', gov: 'Cairo', founded: 2012, employees: '20–50', verified: true, level: '', rating: 4.7, reviews: 15, reply: '1h',
      tagline: 'Stability, method validation and batch release testing.', about: 'ISO 17025 accredited contract laboratory for HPLC assays, dissolution, microbiology and ICH stability.', certs: ['ISO 17025'],
      phone: '+20 2 2600 3300', email: 'lab@deltalabs.example', whatsapp: '201000000005', website: 'deltalabs.example', address: 'New Cairo', hours: 'Sat–Thu · 9:00–18:00',
      services: ['ICH stability studies (Zone IVa/IVb)', 'HPLC method validation', 'Dissolution profiles & f2', 'Microbial limits'], products: [P('Stability Study Package', 'Service', 'lab', '6-month accelerated + 12-month long-term.', '1 study'), P('Method Validation', 'Service', 'lab', 'ICH Q2(R2) validation report.', '1 method')], jobs: [{ t: 'QC Analyst (HPLC)', type: 'Full-time', loc: 'New Cairo' }] },
    { slug: 'alex-excipients', registry: '105685', plan: 'free', licensed: true, status: 'verified', name: 'Alex Excipients Trading', color: '#16a34a', sector: 'API & excipients', sectors: ['API & excipients', 'Distribution'], city: 'Alexandria', gov: 'Alexandria', founded: 2005, employees: '20–50', verified: true, level: 'bronze', rating: 4.2, reviews: 8, reply: '3h',
      tagline: 'MCC, lactose, starches and coating systems — in stock in Alexandria.', about: 'Importer and distributor of pharmaceutical excipients from EU and Asian producers, with local stock and CoA per batch.', certs: ['GDP'],
      phone: '+20 3 580 7700', email: 'sales@alexexcip.example', whatsapp: '201000000006', website: 'alexexcip.example', address: 'Smouha, Alexandria', hours: 'Sun–Thu · 9:00–17:00',
      services: ['Local stock & delivery', 'Sampling', 'Regulatory documents (CoA, TSE/BSE)'], products: [P('MCC PH-102', 'Excipient', 'drum', 'Microcrystalline cellulose, 25 kg drums.', '500 kg', 'US$ 3.40/kg'), P('Lactose Monohydrate', 'Excipient', 'drum', 'Spray-dried, DC grade.', '500 kg'), P('Film Coating System', 'Excipient', 'drum', 'PVA-based, ready to disperse.', '100 kg')], jobs: [] },
    { slug: 'sinai-herbal-extracts', registry: '106802', plan: 'free', licensed: false, status: 'verified', name: 'Sinai Herbal Extracts', color: '#65a30d', sector: 'API & excipients', sectors: ['API & excipients', 'Supplements'], city: 'Ismailia', gov: 'Ismailia', founded: 2011, employees: '50–120', verified: false, level: '', rating: 3.9, reviews: 5, reply: '1d',
      tagline: 'Standardised botanical extracts for supplements and cosmetics.', about: 'Extraction plant for chamomile, moringa, hibiscus and black seed with HPLC standardisation.', certs: ['ISO 22000', 'Halal'],
      phone: '+20 64 390 1200', email: 'info@sinaiextracts.example', whatsapp: '201000000007', website: 'sinaiextracts.example', address: 'Ismailia Industrial Zone', hours: 'Sun–Thu · 8:00–15:00',
      services: ['Custom extraction', 'Standardisation to marker'], products: [P('Black Seed Oil', 'Supplements', 'bottle', 'Cold-pressed, 1 L and bulk.', '100 L'), P('Moringa Extract 10:1', 'Supplements', 'drum', 'Powder extract.', '25 kg')], jobs: [] },
    { slug: 'pharaonic-logistics', registry: '107919', plan: 'vip', licensed: true, status: 'verified', name: 'Pharaonic Cold-Chain Logistics', color: '#0891b2', sector: 'Distribution', sectors: ['Distribution'], city: 'Cairo', gov: 'Cairo', founded: 2009, employees: '200–500', verified: true, level: 'silver', rating: 4.5, reviews: 20, reply: '2h',
      tagline: 'GDP-compliant warehousing and 2–8 °C distribution across Egypt.', about: 'Temperature-mapped warehouses in Cairo and Alexandria with a validated 2–8 °C fleet and customs clearance.', certs: ['GDP', 'ISO 9001'],
      phone: '+20 2 2200 4400', email: 'ops@pharaonic.example', whatsapp: '201000000008', website: 'pharaonic.example', address: 'Obour City, Qalyubia', hours: '24/7 operations',
      services: ['2–8 °C distribution', 'Bonded warehousing', 'Import clearance for APIs'], products: [P('Cold-Chain Delivery', 'Service', 'box', 'Validated 2–8 °C route to all governorates.', '1 pallet')], jobs: [{ t: 'Warehouse Pharmacist', type: 'Full-time', loc: 'Obour' }] },
    { slug: 'regpath-consulting', registry: '109036', plan: 'vip', licensed: false, status: 'verified', name: 'RegPath Consulting', color: '#ca8a04', sector: 'Regulatory & consulting', sectors: ['Regulatory & consulting'], city: 'Giza', gov: 'Giza', founded: 2017, employees: '10–20', verified: true, level: '', rating: 4.8, reviews: 31, reply: '1h',
      tagline: 'EDA, SFDA and MOHAP registrations — dossier to approval.', about: 'Regulatory team of former reviewers and QA heads handling CTD dossiers, variations and GMP inspection readiness.', certs: [],
      phone: '+20 2 3800 9900', email: 'team@regpath.example', whatsapp: '201000000009', website: 'regpath.example', address: 'Dokki, Giza', hours: 'Sun–Thu · 10:00–18:00',
      services: ['EDA new registration (CTD)', 'Variations (PAC)', 'GMP mock inspections', 'SFDA & MOHAP filings'], products: [P('EDA Registration Package', 'Service', 'lab', 'Dossier gap analysis, compilation and follow-up.', '1 product')], jobs: [{ t: 'Regulatory Affairs Officer', type: 'Full-time', loc: 'Giza' }] }
  ];
  /* who receives requests inside each company (a company is not a person) */
  var CONTACTS = { 'quadra-pharm': { sales: 'Dr. Asmaa Meabed', hr: 'Dr. Asmaa Meabed' }, 'medsinia-industries': { sales: 'Eng. Omar Khaled', hr: 'Eng. Omar Khaled' } };
  function contact(co, kind) { var c = CONTACTS[co.slug]; return c ? c[kind === 'job' ? 'hr' : 'sales'] : co.name + (kind === 'job' ? ' · HR' : ' · Sales'); }
  /* medicines are sold only to licensed buyers (pharmacies, distributors, manufacturers) */
  function licensedOnly(p) { return p && /finished dosage/i.test(p.cat); }

  /* ── company page plans. VIP is a paid plan, shown as its own badge; partner levels stay earned. ── */
  var PLANS = {
    free: { name: 'Basic', price: 0, maxProducts: Infinity, feats: ['Company page in the directory', 'Unlimited products and photos', 'Cover photo and full branding', 'Quote, service and job requests', 'Page views and requests analytics', 'Team seats for sales and HR'] },
    vip: { name: 'VIP', price: 2500, year: 25000, maxProducts: Infinity, feats: ['Everything in Basic', 'VIP badge', 'Top of the directory (marked Sponsored)', 'Your own link: company.drugbox.app', 'Verification within 48 hours', '3 Marketplace boosts every month'] }
  };
  var REQUIRE_VIP_FOR_PAGE = false;   /* set true to make every company page VIP-only */
  function isVip(c) { return c && c.plan === 'vip'; }
  function vipBadge(c) { return isVip(c) ? '<span class="dr-vip" title="VIP company — paid plan">' + ic('crown') + 'VIP</span>' : ''; }
  var SECTORS = ['All', 'Manufacturer', 'Cosmetics', 'CMO / Toll', 'API & excipients', 'Packaging', 'Labs & testing', 'Distribution', 'Regulatory & consulting', 'Supplements'];
  var GOVS = ['All governorates', 'Cairo', 'Giza', 'Alexandria', 'Sharqia', 'Qalyubia', 'Ismailia'];
  var CERTS = ['WHO-GMP', 'ISO 9001', 'ISO 22716', 'ISO 17025', 'GDP', 'EDA licensed'];
  var LV = { gold: 'Gold', silver: 'Silver', bronze: 'Bronze' };

  function companies(all) {
    var edits = store('company_edits') || {}, created = store('created_companies') || [], me = window.ME || {};
    var rv = store('supplier_reviews') || {};
    return (window.dxLiveCompanies || SEED.concat(window.dxDirSeeds || [], created)).map(function (s) { var e = edits[s.slug], c = e ? Object.assign({}, s, e) : s, r = rv[c.slug];
      if (r && r.length) { var sum = r.reduce(function (a, x) { return a + x.stars; }, 0); c = Object.assign({}, c, { rating: ((c.rating || 0) * (c.reviews || 0) + sum) / ((c.reviews || 0) + r.length), reviews: (c.reviews || 0) + r.length }); }
      return c; })
      .filter(function () { return true; });   /* pages are public from creation; unverified ones are labelled */
  }
  function bySlug(slug) { return companies().find(function (c) { return c.slug === slug; }); }
  function myCompanies() { var me = window.ME || {}; return companies().filter(function (c) { return c.owner === me.id; }); }
  function mine() { var list = myCompanies(); if (!list.length) return null; var a = store('acting'); return list.find(function (c) { return c.slug === a; }) || list[0]; }   /* the company you act as */
  function ownsPage(co) { var me = window.ME || {}; return co && co.owner === me.id; }
  function initials(n) { return String(n).replace(/[^A-Za-z ]/g, '').split(/\s+/).filter(Boolean).map(function (w) { return w[0]; }).join('').slice(0, 2).toUpperCase(); }
  function logo(c, cls) { return c.logo ? '<span class="' + cls + ' has-img"><img src="' + c.logo + '" alt=""></span>' : '<span class="' + cls + '" style="background:' + esc(c.color) + '">' + esc(initials(c.name)) + '</span>'; }
  function pimg(c, p) { return p.img || packshot(p.kind, c.color, p.name.split(' ')[0]); }


  /* ── one company, everywhere: company names across the app open the company page ── */
  function linkNames() {
    var list = companies(); if (!list.length) return;
    var names = list.map(function (c) { return { n: c.name, s: c.slug }; }).sort(function (a, b) { return b.n.length - a.n.length; });
    document.querySelectorAll('#mkx .seller-sub, #mkx .sc-provider, #mkx .dc-buyer, #mkx .jc-company, #jx .jc-company > span:first-child, .post-sub').forEach(function (el) {
      if (el.dataset.dxco) return; el.dataset.dxco = '1';
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
      while ((n = w.nextNode())) {
        for (var i = 0; i < names.length; i++) {
          var k = n.nodeValue.indexOf(names[i].n); if (k < 0) continue;
          var mid = n.splitText(k); mid.splitText(names[i].n.length);
          var b = document.createElement('button'); b.type = 'button'; b.className = 'dx-colink'; b.dataset.co = names[i].s; b.title = 'Open company page'; b.textContent = names[i].n;
          mid.parentNode.replaceChild(b, mid); return;
        }
      }
    });
  }
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.dx-colink'); if (!b) return; e.stopPropagation(); e.preventDefault(); openCompany(b.dataset.co); }, true);

  /* the company's live marketplace offers and its jobs come from the same data the Marketplace and Jobs pages use */
  var __parsed = {};
  function parsed(key) { if (!__parsed[key]) { var d = document.createElement('div'); d.innerHTML = window[key] || ''; __parsed[key] = d; } return __parsed[key]; }
  function offersOf(co) {
    var out = [];
    /* a listing belongs to the company when the company posted it or one of its team members did */
    var team = (window.USERS || []).filter(function (u) { return u.company === co.name; }).map(function (u) { return u.name; });
    parsed('MKX_HTML').querySelectorAll('.sponsored-card, .lcard, .scard, .dcard').forEach(function (c) {
      var who = ((c.querySelector('.seller-name, .dc-buyer, .sc-provider') || {}).textContent || '');
      if (c.textContent.indexOf(co.name) < 0 && !team.some(function (n) { return who.indexOf(n) >= 0; })) return;
      var t = c.querySelector('.sp-title,.lc-title,.sc-title,.dc-title'); if (!t) return;
      var tt = t.cloneNode(true); tt.querySelectorAll('.role-badge').forEach(function (x) { x.remove(); });
      out.push({ t: tt.textContent.replace(/\s+/g, ' ').trim(), type: (c.querySelector('.lt') || {}).textContent || (c.classList.contains('dcard') ? 'DEMAND' : c.classList.contains('scard') ? 'SERVICE' : 'SUPPLY') });
    });
    return out;
  }
  function jobsOf(co) {
    var seen = {}, out = [];
    parsed('JX_HTML').querySelectorAll('.jcard').forEach(function (c) {
      if (c.querySelector('.role-badge.need')) return;
      var who = (c.querySelector('.jc-company span') || {}).textContent || ''; if (who.trim() !== co.name) return;
      var tt = c.querySelector('.jc-title').cloneNode(true); tt.querySelectorAll('span').forEach(function (s) { s.remove(); });
      var t = tt.textContent.replace(/\s+/g, ' ').trim(); if (seen[t]) return; seen[t] = 1;
      var tags = Array.prototype.map.call(c.querySelectorAll('.jt'), function (x) { return x.textContent.trim(); });
      out.push({ t: t, type: tags[0] || 'Full-time', loc: ((c.querySelectorAll('.jc-company span')[1] || {}).textContent || co.city).replace(/^[^A-Za-z0-9]+/, '').trim(), onJobs: true });
    });
    (co.jobs || []).forEach(function (j) { if (!seen[j.t]) { seen[j.t] = 1; out.push(j); } });
    return out;
  }
  function employer(co) { var s = window.dxEmployerStats ? window.dxEmployerStats(co.name) : null; return s && s.n ? s : null; }

  /* ── state ── */
  var S = { open: null, q: '', sector: 'All', gov: 'All governorates', certs: [], verified: false, sort: 'rating', tab: 'overview', editing: false };

  /* ── directory view ── */
  function filtered() {
    var q = S.q.toLowerCase();
    return companies().filter(function (c) {
      if (S.sector !== 'All' && c.sectors.indexOf(S.sector) < 0) return false;
      if (S.gov !== 'All governorates' && c.gov !== S.gov) return false;
      if (S.verified && !c.verified) return false;
      if (S.certs.length && !S.certs.every(function (x) { return c.certs.indexOf(x) >= 0; })) return false;
      if (q) { var hay = (c.name + ' ' + c.tagline + ' ' + c.city + ' ' + c.sectors.join(' ') + ' ' + c.products.map(function (p) { return p.name; }).join(' ') + ' ' + (c.services || []).join(' ')).toLowerCase(); if (q.split(/\s+/).some(function (w) { return hay.indexOf(w) < 0; })) return false; }
      return true;
    }).sort(function (a, b) { return (isVip(b) ? 1 : 0) - (isVip(a) ? 1 : 0) || (S.sort === 'name' ? a.name.localeCompare(b.name) : S.sort === 'newest' ? b.founded - a.founded : (b.rating - a.rating) || (b.reviews - a.reviews)); });
  }
  function vipStrip() {
    var v = companies().filter(function (c) { return isVip(c); }); if (!v.length) return '';
    return '<section class="dr-vipstrip"><div class="dr-vs-h">' + ic('crown') + '<b>VIP companies</b><span>Sponsored placement · paid plan</span></div><div class="dr-vs-row">' +
      v.map(function (c) { return '<button type="button" class="dr-vs-card" data-go="' + c.slug + '">' + logo(c, 'dr-logo sm') + '<span><b>' + esc(c.name) + '</b><small>' + esc(c.sectors[0]) + ' · ' + esc(c.city) + '</small></span></button>'; }).join('') + '</div></section>';
  }
  function card(c) {
    return '<article class="dr-card" data-slug="' + c.slug + '"><div class="dr-cover" style="' + (c.cover ? 'background-image:url(' + c.cover + ')' : '--cc:' + esc(c.color)) + '"></div>' +
      '<div class="dr-card-b">' + logo(c, 'dr-logo') + '<div class="dr-name">' + esc(c.name) + (c.verified ? '<span class="dr-seal" title="Verified company">' + ic('seal') + '</span>' : '') + (c.level ? '<span class="dr-lv lv-' + c.level + '">' + LV[c.level] + '</span>' : '') + vipBadge(c) + (c.status !== 'verified' ? '<span class="dr-pend' + (c.status === 'unclaimed' ? ' unc' : '') + '">' + (c.status === 'pending' ? 'Verification in review' : c.status === 'unclaimed' ? 'Unclaimed' : 'Not verified') + '</span>' : '') + '</div>' +
      '<div class="dr-meta">' + esc(c.sectors.join(' · ')) + ' · ' + esc(c.city) + '</div><p class="dr-tag">' + esc(c.tagline) + '</p>' +
      '<div class="dr-stats"><span>' + ic('box') + c.products.length + ' products</span><span title="Rated by buyers">' + (c.reviews ? '★ ' + c.rating.toFixed(1) + ' <small>supplier (' + c.reviews + ')</small>' : '<small>No reviews yet</small>') + '</span>' + (employer(c) ? '<span title="Rated by candidates and employees">★ ' + employer(c).avg.toFixed(1) + ' <small>employer (' + employer(c).n + ')</small></span>' : '') + (c.reply && c.reply !== '—' ? '<span>' + ic('chat') + 'replies in ' + esc(c.reply) + '</span>' : '') + '</div>' +
      '<div class="dr-acts"><button type="button" class="dr-btn p" data-go="' + c.slug + '">Visit page</button><button type="button" class="dr-btn" data-rfq="' + c.slug + '">Request a quote</button></div></div></article>';
  }
  function renderDirectory(c) {
    var list = filtered(), my = mine();
    c.innerHTML = '<div id="dxDir"><section class="dr-hero"><div><span class="dr-k">COMPANY DIRECTORY</span><h1 class="dr-h">Egypt\u2019s pharma companies — one page each</h1>' +
      '<p class="dr-sub">Find manufacturers, suppliers, labs and service providers. See their products, ask for a quote or apply for a job directly from their page.</p></div>' +
      '<div class="dr-hero-cta"><div class="dr-ill" aria-hidden="true"></div><button type="button" class="dr-btn p lg" data-create="1">' + ic('plus') + 'Create a company page</button>' +
      '<div class="dr-hero-row">' + (myCompanies().length ? '<button type="button" class="dr-btn" data-mycos="1">' + ic('building') + 'My companies (' + myCompanies().length + ')</button>' : '') + '<button type="button" class="dr-btn" data-myreq="1">' + ic('clipboard') + 'Requests & deals' + (window.dxDeals && window.dxDeals.waiting() ? ' <em class="dl-todo">' + window.dxDeals.waiting() + '</em>' : '') + '</button></div>' +
      (my ? '<label class="dr-acting">Acting as <select id="drActing">' + myCompanies().map(function (c) { return '<option value="' + c.slug + '"' + (c.slug === my.slug ? ' selected' : '') + '>' + esc(c.name) + '</option>'; }).join('') + '</select></label>' : '') + '</div></section>' +
      (!S.q && S.sector === 'All' && !S.certs.length && S.gov === 'All governorates' && !S.verified ? vipStrip() : '') +
      '<div class="dr-bar"><div class="dr-search">' + ic('search') + '<input type="search" id="drQ" placeholder="Search companies, products or services…" value="' + esc(S.q) + '" aria-label="Search the directory"></div>' +
      '<select id="drGov" aria-label="Governorate">' + GOVS.map(function (g) { return '<option' + (g === S.gov ? ' selected' : '') + '>' + g + '</option>'; }).join('') + '</select>' +
      '<select id="drSort" aria-label="Sort"><option value="rating"' + (S.sort === 'rating' ? ' selected' : '') + '>Top rated</option><option value="name"' + (S.sort === 'name' ? ' selected' : '') + '>Name A–Z</option><option value="newest"' + (S.sort === 'newest' ? ' selected' : '') + '>Newest</option></select></div>' +
      '<div class="dr-chips">' + SECTORS.map(function (s) { return '<button type="button" class="dr-chip' + (S.sector === s ? ' on' : '') + '" data-sector="' + esc(s) + '">' + esc(s) + '</button>'; }).join('') + '</div>' +
      '<div class="dr-chips dr-certs"><span>Certified:</span>' + CERTS.map(function (x) { return '<button type="button" class="dr-chip sm' + (S.certs.indexOf(x) >= 0 ? ' on' : '') + '" data-cert="' + esc(x) + '">' + esc(x) + '</button>'; }).join('') +
      '<label class="dr-ver"><input type="checkbox" id="drVer"' + (S.verified ? ' checked' : '') + '> Verified only</label></div>' +
      '<div class="dr-count">' + list.length + ' compan' + (list.length === 1 ? 'y' : 'ies') + '</div>' +
      (list.length ? '<div class="dr-grid">' + list.map(card).join('') + '</div>' : '<div class="dbk-empty">No company matches these filters. <button type="button" class="dr-link" data-reset="1">Clear filters</button></div>') + '</div>';
    var ill = c.querySelector('.dr-ill'); if (ill && window.dxIll) ill.innerHTML = window.dxIll('factory');
  }

  /* ── company page (storefront) ── */
  function tabs(co, owner) {
    var t = [['overview', 'Overview'], ['products', 'Products (' + co.products.length + ')'], ['offers', 'Marketplace offers (' + offersOf(co).length + ')'], ['services', 'Services'], ['jobs', 'Jobs (' + jobsOf(co).length + ')'], ['contact', 'Contact']];
    if (owner) t.push(['requests', 'Requests (' + (window.dxDeals ? window.dxDeals.openCount(co.slug) : 0) + ')']);
    return '<nav class="cp-tabs" role="tablist">' + t.map(function (x) { return '<button type="button" role="tab" class="cp-tab' + (S.tab === x[0] ? ' on' : '') + '" data-tab="' + x[0] + '">' + esc(x[1]) + '</button>'; }).join('') + '</nav>';
  }
  function productCard(co, p) {
    return '<article class="cp-prod"><button type="button" class="cp-pimg" data-pdetail="' + p.id + '"><img src="' + pimg(co, p) + '" alt="' + esc(p.name) + '"></button>' +
      '<div class="cp-pb"><span class="cp-pcat">' + esc(p.cat) + '</span><b>' + esc(p.name) + '</b><p>' + esc(p.desc) + '</p>' +
      '<div class="cp-pmeta">' + (p.price ? '<span class="cp-price">' + esc(p.price) + '</span>' : '<span class="cp-por">Price on request</span>') + (p.moq ? '<span>MOQ ' + esc(p.moq) + '</span>' : '') + '</div>' +
      '<button type="button" class="dr-btn p sm" data-rfq="' + co.slug + '" data-prod="' + p.id + '">Request a quote</button></div></article>';
  }
  function certWall(co) {
    if (!co.certs.length) return '';
    return '<div class="cp-certs">' + co.certs.map(function (x) { return '<span class="cp-cert">' + ic('seal') + esc(x) + '</span>'; }).join('') + '</div>';
  }
  function renderCompany(c, co) {
    var owner = ownsPage(co), url = (isVip(co) ? co.slug + '.drugbox.app' : 'drugbox.app/c/' + co.slug);
    var team = (co.team || []).map(function (id) { return (window.USERS || []).find(function (u) { return u.id === id; }); }).filter(Boolean);
    var body = '';
    if (S.tab === 'overview') body = '<div class="cp-two"><section class="cp-sec"><h3>About ' + esc(co.name) + '</h3><p class="cp-about">' + esc(co.about) + '</p>' + certWall(co) +
        '<div class="cp-facts"><div><small>Founded</small><b>' + esc(co.founded) + '</b></div><div><small>Team</small><b>' + esc(co.employees) + '</b></div><div><small>Location</small><b>' + esc(co.city) + '</b></div><div><small>Replies</small><b>within ' + esc(co.reply) + '</b></div></div></section>' +
        '<aside class="cp-sec"><h3>Featured products</h3><div class="cp-mini">' + co.products.slice(0, 3).map(function (p) { return '<button type="button" class="cp-mini-i" data-pdetail="' + p.id + '"><img src="' + pimg(co, p) + '" alt=""><span><b>' + esc(p.name) + '</b><small>' + esc(p.cat) + '</small></span></button>'; }).join('') + '</div>' +
        (team.length ? '<h3 style="margin-top:18px">People</h3>' + team.map(function (u) { return '<button type="button" class="cp-person" data-uid="' + u.id + '"><span class="cp-pav" style="background:' + esc(u.color || '#1a56db') + '">' + esc(u.initials || initials(u.name)) + '</span><span><b>' + esc(u.name) + '</b><small>' + esc((u.headline || '').split('|')[0]) + '</small></span></button>'; }).join('') : '') + '</aside></div>';
    else if (S.tab === 'products') body = '<div class="cp-pgrid">' + co.products.map(function (p) { return productCard(co, p); }).join('') + (owner ? '<button type="button" class="cp-add" data-edit="products">' + ic('plus') + 'Add a product</button>' : '') + '</div>';
    else if (S.tab === 'services') body = '<section class="cp-sec"><h3>What we offer</h3><ul class="cp-svc">' + (co.services || []).map(function (s) { return '<li>' + ic('seal') + '<span>' + esc(s) + '</span><button type="button" class="dr-btn sm" data-rfq="' + co.slug + '" data-svc="' + esc(s) + '">Request</button></li>'; }).join('') + '</ul></section>';
    else if (S.tab === 'offers') { var of = offersOf(co); body = '<section class="cp-sec"><h3>Live offers in the Marketplace</h3><p class="cp-muted">Time-limited deals this company is running now. Its permanent catalogue is under Products.</p>' + (of.length ? of.map(function (o) { return '<div class="cp-job"><span class="cp-jic cp-oic">' + ic(/DEMAND/i.test(o.type) ? 'basket' : /SERVICE/i.test(o.type) ? 'tools' : 'box') + '</span><span><b>' + esc(o.t) + '</b><small>' + esc(o.type) + '</small></span><button type="button" class="dr-btn sm" data-offer="' + esc(o.t) + '">View in Marketplace</button></div>'; }).join('') : '<p class="cp-muted">No live offers right now.</p>') + '</section>'; }
    else if (S.tab === 'jobs') { var js = jobsOf(co); body = '<section class="cp-sec"><h3>Open positions</h3><p class="cp-muted">The same jobs as on the Jobs page — applying from here or there is one application.</p>' + (js.length ? js.map(function (j, i) { return '<div class="cp-job"><span class="cp-jic">' + ic('briefcase') + '</span><span><b>' + esc(j.t) + '</b><small>' + esc(j.type) + ' · ' + esc(j.loc) + '</small></span><button type="button" class="dr-btn p sm" data-apply="' + i + '">Apply</button></div>'; }).join('') : '<p class="cp-muted">No open positions right now. <button type="button" class="dr-link" data-follow="1">Follow</button> to hear when they hire.</p>') + '</section>'; }
    else if (S.tab === 'contact') body = '<div class="cp-two"><section class="cp-sec"><h3>Contact ' + esc(co.name) + '</h3><div class="cp-contact">' +
        '<a href="tel:' + esc(co.phone.replace(/\s/g, '')) + '">' + ic('chat') + '<span><small>Phone</small>' + esc(co.phone) + '</span></a>' +
        '<a href="mailto:' + esc(co.email) + '">' + ic('send') + '<span><small>Email</small>' + esc(co.email) + '</span></a>' +
        '<a href="https://wa.me/' + esc(co.whatsapp) + '" target="_blank" rel="noopener">' + ic('chat') + '<span><small>WhatsApp</small>Message on WhatsApp</span></a>' +
        '<a href="https://' + esc(co.website) + '" target="_blank" rel="noopener">' + ic('globe') + '<span><small>Website</small>' + esc(co.website) + '</span></a>' +
        '<a href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(co.address) + '" target="_blank" rel="noopener">' + ic('pin') + '<span><small>Address · get directions</small>' + esc(co.address) + '</span></a>' +
        '<div>' + ic('bell') + '<span><small>Working hours</small>' + esc(co.hours) + '</span></div></div></section>' +
        '<section class="cp-sec"><h3>Send a request</h3><p class="cp-muted">Requests go straight to the company\u2019s inbox on Drugbox and to their team by message.</p><div class="cp-req-btns">' +
        '<button type="button" class="dr-btn p" data-rfq="' + co.slug + '">' + ic('cart') + 'Request a quote</button><button type="button" class="dr-btn" data-rfq="' + co.slug + '" data-svc="' + esc((co.services || [])[0] || '') + '">' + ic('tools') + 'Request a service</button>' +
        '<button type="button" class="dr-btn" data-msg="1">' + ic('chat') + 'Send a message</button></div></section></div>';
    else if (S.tab === 'requests' && owner) { var rv = (store('supplier_reviews') || {})[co.slug] || [];
      body = '<div class="cp-stats"><div><small>Open requests</small><b>' + window.dxDeals.openCount(co.slug) + '</b></div><div><small>Waiting for you</small><b>' + window.dxDeals.all().filter(function (d) { return d.to.slug === co.slug && window.dxDeals.actionsFor(d, 'to').length; }).length + '</b></div><div><small>Completed orders</small><b>' + window.dxDeals.all().filter(function (d) { return d.to.slug === co.slug && d.status === 'closed'; }).length + '</b></div><div><small>Reviews from orders</small><b>' + rv.length + '</b></div></div>' +
        '<section class="cp-sec"><h3>Received by ' + esc(co.name) + '</h3><p class="cp-muted">Quote and service requests go to ' + esc(contact(co, 'rfq')) + ' (sales); job applications to ' + esc(contact(co, 'job')) + ' (HR). Open one to reply — the sender sees each step.</p>' + window.dxDeals.receivedHtml(co.slug) + '</section>'; }
    c.innerHTML = '<div id="dxDir" class="cp"><button type="button" class="cp-back" data-back="1">' + ic('compass') + 'All companies</button>' +
      '<header class="cp-hero"><div class="cp-cover" style="' + (co.cover ? 'background-image:url(' + co.cover + ')' : '--cc:' + esc(co.color)) + '"></div><div class="cp-id">' + logo(co, 'cp-logo') +
      '<div class="cp-idt"><h1 class="cp-name">' + esc(co.name) + (co.verified ? '<span class="dr-seal" title="Verified company">' + ic('seal') + '</span>' : '') + (co.level ? '<span class="dr-lv lv-' + co.level + '">' + LV[co.level] + ' partner</span>' : '') + vipBadge(co) + '</h1>' +
      '<p class="cp-tagline">' + esc(co.tagline) + '</p><div class="cp-meta">' + esc(co.sectors.join(' · ')) + ' · ' + esc(co.city) + ', ' + esc(co.gov) + '</div>' +
      '<div class="cp-ratings"><span title="Rated by buyers after real orders">' + (co.reviews ? '★ ' + co.rating.toFixed(1) + ' <b>as a supplier</b> <small>(' + co.reviews + ' buyers)</small>' : '<b>No supplier reviews yet</b>') + '</span>' + (employer(co) ? '<button type="button" class="cp-rate-emp" data-empreviews="1" title="Rated by candidates and employees in Jobs">★ ' + employer(co).avg.toFixed(1) + ' <b>as an employer</b> <small>(' + employer(co).n + ' reviews)</small></button>' : '') + '</div></div>' +
      '<div class="cp-cta">' + (owner ? '<button type="button" class="dr-btn p" data-edit="all">' + ic('pen') + 'Edit page</button>' : '<button type="button" class="dr-btn p" data-rfq="' + co.slug + '">Request a quote</button><button type="button" class="dr-btn" data-msg="1">' + ic('chat') + 'Message</button><button type="button" class="dr-btn" data-follow="1">' + (followed(co.slug) ? '✓ Following' : '+ Follow') + '</button>') +
      '<button type="button" class="dr-btn ghost" data-share="1" title="Copy the page link">' + ic('send') + '<span class="cp-url">' + esc(url) + '</span></button></div></div></header>' +
      (owner && co.status === 'unverified' ? '<div class="cp-banner pend">' + ic('warning') + '<span><b>Not verified.</b> Your page is live. Verify the company to get the Verified badge.</span><button type="button" class="dr-btn p sm" data-verify="' + co.slug + '">Get verified</button></div>' : '') +
      (owner && co.status === 'pending' ? '<div class="cp-banner pend">' + ic('seal') + '<span><b>Verification in review.</b> We check your documents' + (isVip(co) ? ' within 48 hours (VIP)' : ' within 2 working days') + '. Your page stays live meanwhile.</span></div>' : '') +
      (!owner && co.status !== 'verified' ? '<div class="cp-banner pend">' + ic('warning') + '<span>This company has not been verified by Drugbox yet.</span></div>' : '') +
      (owner && !isVip(co) ? '<div class="cp-banner up">' + ic('crown') + '<span><b>Want more visibility?</b> VIP adds the VIP badge, top placement in the directory, your own link and 3 Marketplace boosts a month.</span><button type="button" class="dr-btn p sm" data-upgrade="' + co.slug + '">See VIP</button></div>' : '') +
      tabs(co, owner) + '<div class="cp-body">' + body + '</div></div>';
  }
  function render(c) {
    c = c || document.getElementById('content'); if (!c) return;
    c.style.padding = '';
    var co = S.open && bySlug(S.open);
    if (window.dxHub && window.dxHub.render(c, S, co)) return;   /* the company hub draws the new directory, company page and workspace */
    if (co) renderCompany(c, co); else { S.open = null; renderDirectory(c); }
  }
  function openCompany(slug, tab) {
    S.open = slug; S.tab = tab || 'overview';
    if (document.body.getAttribute('data-page') !== 'companies') { window.__dxKeepCompany = true; try { window.goto('companies'); } finally { window.__dxKeepCompany = false; } } else { render(); var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0; }
  }
  window.dxOpenCompany = openCompany;
  window.dxDirectory = { list: companies, open: openCompany };
  window.dxDir = { companies: companies, bySlug: bySlug, render: function () { render(); }, S: S, open: function (s, t) { openCompany(s, t); }, rfq: function (s, p, v) { rfqDialog(s, p, v); },
    myCompanies: function () { return myCompanies(); }, mine: function () { return mine(); }, store: store, logo: logo, pimg: pimg, packshot: packshot, isVip: isVip, inbox: inbox, myReqs: myReqs,
    jobsOf: function (c) { return jobsOf(c); }, offersOf: function (c) { return offersOf(c); }, employer: function (c) { return employer(c); }, productDialog: function (c, p) { productDialog(c, p); }, applyDialog: function (c, j) { applyDialog(c, j); },
    editor: function (f) { openEditor(f); }, verify: function (s) { verifyDialog(s); }, upgrade: function (s) { upgradeDialog(s); }, create: function () { createCompanyDialog(); }, myCosDialog: function () { myCompaniesDialog(); }, followed: function (s) { return followed(s); }, esc: esc, ic: ic,
    reqStatus: function (r) { return reqStatus(r); }, quoteFor: function (r) { return quoteFor(r); }, contact: contact, P: P, SECTORS: SECTORS, GOVS: GOVS, CERTS: CERTS, ownsPage: function (c) { return ownsPage(c); } };

  /* ── follows, inbox ── */
  function followed(slug) { return (store('follows') || []).indexOf(slug) >= 0; }
  var SEED_INBOX = { 'quadra-pharm': [{ kind: 'rfq', title: 'Toll manufacturing — film-coated tablets, 500,000/yr', from: 'Nour Pharma (Cairo)', when: '2h ago', text: 'We have an EDA-registered formula and need a WHO-GMP site. Can you share your toll price per 1,000 tablets and earliest slot?' },
    { kind: 'service', title: 'EDA variation — site transfer', from: 'Delta Health (Tanta)', when: 'yesterday', text: 'Need support for a PAC site-transfer variation for two products.' },
    { kind: 'job', title: 'Senior Regulatory Affairs Specialist', from: 'Sara Mansour', when: '2d ago', text: 'Applied with CV — 4 years EDA dossiers, CTD format.' }] };
  function inbox(co) { return (store('inbox_' + co.slug) || []).concat(SEED_INBOX[co.slug] || []); }

  /* ── dialogs ── */
  /* request lifecycle (demo timing; production: real status from the company) */
  function myReqs(v) { if (v === undefined) return store('my_requests') || []; store('my_requests', v); }
  function reqStatus(r) {
    if (r.status === 'accepted' || r.status === 'declined') return r.status;
    var age = (Date.now() - r.at) / 1000;
    if (r.kind === 'job') return age > 20 ? 'viewed' : 'sent';
    if (age < 8) return 'sent'; if (age < 20) return 'viewed';
    return r.kind === 'rfq' ? 'quoted' : 'replied';
  }
  function quoteFor(r) { var h = 0, key = r.title + '|' + (r.to || ''); for (var i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) | 0; var base = 2 + Math.abs(h) % 40; return 'US$ ' + base.toFixed(2) + ' per ' + (r.unit || 'unit') + ' · valid 14 days · ' + (r.inc || 'EXW'); }
  var ST = { sent: ['Sent', 'st-sent'], viewed: ['Viewed', 'st-viewed'], quoted: ['Quote received', 'st-quoted'], replied: ['Replied', 'st-quoted'], accepted: ['Accepted', 'st-acc'], declined: ['Declined', 'st-dec'] };
  function myRequestsDialog() { window.dxDeals.center('sent'); }
  function rfqDialog(slug, prodId, svc) {
    var co = bySlug(slug); if (!co || !D) return;
    var __a = mine(); if (__a && __a.slug === co.slug) { D.toast('You are acting as ' + co.name + ' — switch company to request from it'); return; }
    var isSvc = svc != null && svc !== '';
    var opts = (isSvc ? (co.services || []).map(function (s) { return '<option' + (s === svc ? ' selected' : '') + '>' + esc(s) + '</option>'; }) : co.products.map(function (p) { return '<option value="' + p.id + '"' + (p.id === prodId ? ' selected' : '') + '>' + esc(p.name) + '</option>'; })).join('') + '<option value="other">Something else</option>';
    var prod = !isSvc && prodId ? co.products.find(function (p) { return p.id === prodId; }) : null, me = window.ME || {};
    var act = mine();
    D.modal({ title: (isSvc ? 'Request a service from ' : 'Request a quote from ') + co.name,
      body: (act ? '<div class="rq-to">' + ic('building') + 'Requesting as <b>' + esc(act.name) + '</b></div>' : '') + (licensedOnly(prod) ? '<div class="rq-lic note">' + ic('warning') + 'Medicine — under Egyptian law it may be sold only to licensed pharmacies, distributors and manufacturers. The seller confirms the buyer\u2019s licence before shipping.</div>' : '') +
        '<div class="rq-to">' + ic('user') + 'Goes to <b>' + esc(contact(co, isSvc ? 'service' : 'rfq')) + '</b> (' + (isSvc ? 'business development' : 'sales') + ') at ' + esc(co.name) + '</div>' +
        '<div class="dbk-f"><label for="rqWhat">' + (isSvc ? 'Service' : 'Product') + '</label><select id="rqWhat">' + opts + '</select></div>' +
        (isSvc ? '' : '<div class="dbk-row"><div class="dbk-f"><label for="rqQty">Quantity *</label><input id="rqQty" data-req inputmode="decimal" placeholder="e.g. 500"></div><div class="dbk-f"><label for="rqUnit">Unit</label><select id="rqUnit"><option>kg</option><option>MT</option><option>units</option><option>cartons</option><option>tablets</option><option>batches</option></select></div></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="rqTo">Deliver to *</label><input id="rqTo" data-req placeholder="City, country" value="Cairo, Egypt"></div><div class="dbk-f"><label for="rqInc">Delivery terms</label><select id="rqInc"><option>EXW</option><option>FOB</option><option selected>CIF</option><option>DDP</option></select></div></div>') +
        '<div class="dbk-f"><label for="rqBy">Needed by</label><input id="rqBy" type="date"></div>' +
        '<div class="dbk-f"><label for="rqMsg">Message *</label><textarea id="rqMsg" data-req placeholder="Specs, grade, certificates you need, payment terms…"></textarea></div>',
      primary: { label: 'Send request', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var what = b.querySelector('#rqWhat'), label = what.options[what.selectedIndex].text;
        var lines = [(isSvc ? 'Service request: ' : 'Quote request: ') + label];
        if (!isSvc) lines.push('Quantity: ' + b.querySelector('#rqQty').value + ' ' + b.querySelector('#rqUnit').value, 'Deliver to: ' + b.querySelector('#rqTo').value + ' (' + b.querySelector('#rqInc').value + ')');
        if (b.querySelector('#rqBy').value) lines.push('Needed by: ' + b.querySelector('#rqBy').value);
        lines.push('', b.querySelector('#rqMsg').value.trim());
        var text = lines.join('\n'), me = window.ME || {};
        var who = contact(co, isSvc ? 'service' : 'rfq');
        var __d = window.dxDeals.create(isSvc ? 'service' : 'quote', co.slug, label, isSvc ? {} : { qty: b.querySelector('#rqQty').value.trim(), unit: b.querySelector('#rqUnit').value, inc: b.querySelector('#rqInc').value, to: b.querySelector('#rqTo').value.trim(), by: b.querySelector('#rqBy').value }, b.querySelector('#rqMsg').value.trim());
        if (!__d) return false;
        D.toast('Sent to ' + who + ' at ' + co.name + ' — follow it in Requests & deals');
      } } });
  }
  function sendQuoteDialog(co, i) {
    var r = inbox(co)[i]; if (!r) return;
    D.modal({ title: 'Send a quote to ' + r.from, body: '<p class="cp-muted">' + esc(r.title) + '</p><div class="dbk-row"><div class="dbk-f"><label for="sqP">Price *</label><input id="sqP" data-req placeholder="e.g. US$ 0.45 per tablet"></div><div class="dbk-f"><label for="sqV">Valid for</label><select id="sqV"><option>7 days</option><option selected>14 days</option><option>30 days</option></select></div></div>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="sqI">Delivery terms</label><select id="sqI"><option>EXW</option><option>FOB</option><option selected>CIF</option><option>DDP</option></select></div><div class="dbk-f"><label for="sqL">Lead time</label><input id="sqL" placeholder="e.g. 4 weeks"></div></div><div class="dbk-f"><label for="sqN">Note</label><textarea id="sqN" placeholder="Payment terms, samples, documents…"></textarea></div>',
      primary: { label: 'Send quote', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var q = b.querySelector('#sqP').value.trim() + ' · ' + b.querySelector('#sqI').value + ' · valid ' + b.querySelector('#sqV').value, done = store('quoted_' + co.slug) || {}; done[r.title + '|' + r.from] = q; store('quoted_' + co.slug, done);
        if (D.sendToOutbox) D.sendToOutbox({ to: r.from, text: 'Quote from ' + co.name + ' for “' + r.title + '”: ' + q + (b.querySelector('#sqL').value ? ' · lead time ' + b.querySelector('#sqL').value : '') + (b.querySelector('#sqN').value.trim() ? '\n' + b.querySelector('#sqN').value.trim() : '') });
        D.toast('Quote sent to ' + r.from); render();
      } } });
  }
  function applyDialog(co, job) {
    D.modal({ title: 'Apply: ' + job.t, body: '<p class="cp-muted">' + esc(co.name) + ' · ' + esc(job.type) + ' · ' + esc(job.loc) + '</p>' +
      '<div class="dbk-f"><label for="apCv">CV (PDF or Word) *</label><input id="apCv" type="file" accept=".pdf,.doc,.docx"></div>' +
      '<div class="dbk-f"><label for="apMsg">Why you? *</label><textarea id="apMsg" data-req placeholder="Two or three lines about your experience"></textarea></div>',
      primary: { label: 'Send application', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        if (!b.querySelector('#apCv').files.length) { b.querySelector('#apCv').classList.add('dbk-err'); D.toast('Please attach your CV'); return false; }
        window.dxDeals.create('job', co.slug, job.t, {}, b.querySelector('#apMsg').value.trim() + ' (CV: ' + b.querySelector('#apCv').files[0].name + ')');
        D.toast('Application sent to ' + co.name + ' — follow it in Requests & deals');
      } } });
  }
  function productDialog(co, p) {
    var m = D.modal({ title: p.name, secondary: 'Close', primary: { label: 'Request a quote', onClick: function () { setTimeout(function () { rfqDialog(co.slug, p.id); }, 40); } },
      body: '<div class="cp-pd"><img src="' + pimg(co, p) + '" alt="' + esc(p.name) + '"><div><span class="cp-pcat">' + esc(p.cat) + '</span><p>' + esc(p.desc) + '</p>' +
        '<table class="cp-spec">' + [['Supplier', co.name], ['Minimum order', p.moq || '—'], ['Price', p.price || 'On request']].concat((p.specs || []).map(function (s) { var k = s.split(':'); return [k[0], k.slice(1).join(':').trim() || '✓']; })).map(function (r) { return '<tr><td>' + esc(r[0]) + '</td><td>' + esc(r[1]) + '</td></tr>'; }).join('') + '</table></div></div>' });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
  }

  function listCompanyDialog() {
    D.modal({ title: 'List your company on Drugbox', body: '<p class="cp-muted">Your page goes live after we verify the company — usually within 2 working days. Until then only you can see it.</p>' +
      '<div class="dbk-f"><label for="lcN">Company legal name *</label><input id="lcN" data-req></div><div class="dbk-row"><div class="dbk-f"><label for="lcS">Main activity *</label><select id="lcS" data-req><option value="">Choose…</option>' + SECTORS.slice(1).map(function (s) { return '<option>' + esc(s) + '</option>'; }).join('') + '</select></div><div class="dbk-f"><label for="lcG">Governorate *</label><select id="lcG" data-req><option value="">Choose…</option>' + GOVS.slice(1).map(function (g) { return '<option>' + g + '</option>'; }).join('') + '</select></div></div>' +
      '<div class="dbk-f"><label for="lcR">Commercial registry *</label><input id="lcR" type="file" accept=".pdf,.jpg,.png"></div><div class="dbk-f"><label for="lcT">Tax card *</label><input id="lcT" type="file" accept=".pdf,.jpg,.png"></div><div class="dbk-f"><label for="lcL">Licence (EDA, pharmacy, distribution or industrial) — needed to sell or buy medicines</label><input id="lcL" type="file" accept=".pdf,.jpg,.png"></div>',
      primary: { label: 'Submit for verification', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        if (!b.querySelector('#lcR').files.length || !b.querySelector('#lcT').files.length) { D.toast('Commercial registry and tax card are required'); return false; }
        store('company_application', { name: b.querySelector('#lcN').value.trim(), sector: b.querySelector('#lcS').value, gov: b.querySelector('#lcG').value, licence: !!b.querySelector('#lcL').files.length, at: Date.now(), status: 'pending' });
        D.toast('Submitted — we will verify ' + b.querySelector('#lcN').value.trim() + ' and publish your page');
      } } });
  }

  function slugify(n) { return String(n).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || ('company-' + Date.now()); }
  function planCards(sel, billing) {
    return '<div class="pl-grid">' + ['free', 'vip'].map(function (k) { var p = PLANS[k];
      return '<label class="pl-card' + (sel === k ? ' on' : '') + (k === 'vip' ? ' vip' : '') + '"><input type="radio" name="plPick" value="' + k + '"' + (sel === k ? ' checked' : '') + '>' +
        '<div class="pl-h">' + (k === 'vip' ? ic('crown') : ic('building')) + '<b>' + p.name + '</b>' + (k === 'vip' ? '<em>Recommended</em>' : '') + '</div>' +
        '<div class="pl-price">' + (p.price ? (billing === 'year' ? 'EGP ' + p.year.toLocaleString() + '<small>/year · 2 months free</small>' : 'EGP ' + p.price.toLocaleString() + '<small>/month</small>') : 'Free') + '</div>' +
        '<ul>' + p.feats.map(function (f) { return '<li>' + ic('seal') + esc(f) + '</li>'; }).join('') + '</ul></label>'; }).join('') + '</div>' +
      '<div class="pl-bill"><label><input type="radio" name="plBill" value="month"' + (billing !== 'year' ? ' checked' : '') + '> Monthly</label><label><input type="radio" name="plBill" value="year"' + (billing === 'year' ? ' checked' : '') + '> Yearly</label><span class="cp-muted">Example prices in EGP — set by Drugbox.</span></div>';
  }
  var MAX_PENDING = 3;
  function createCompanyDialog() {
    if (!D) return;
    var W = { plan: REQUIRE_VIP_FOR_PAGE ? 'vip' : 'vip', billing: 'month' };
    function step1() {
      var m = D.modal({ title: 'Create a company page · 1 of 3 — choose a plan', body: planCards(W.plan, W.billing) + (REQUIRE_VIP_FOR_PAGE ? '<p class="cp-muted">Company pages are available on VIP.</p>' : ''),
        primary: { label: 'Next: company details', onClick: function (b) { W.plan = b.querySelector('input[name=plPick]:checked').value; W.billing = b.querySelector('input[name=plBill]:checked').value; if (REQUIRE_VIP_FOR_PAGE && W.plan !== 'vip') { toast('Company pages need VIP'); return false; } setTimeout(step2, 40); } } });
      m.el.querySelector('.dbk-box').classList.add('dbk-wide');
      m.el.addEventListener('change', function (e) { if (e.target.name === 'plPick' || e.target.name === 'plBill') { W.plan = m.el.querySelector('input[name=plPick]:checked').value; W.billing = m.el.querySelector('input[name=plBill]:checked').value; m.el.querySelector('.dbk-bd').innerHTML = planCards(W.plan, W.billing); } });
    }
    function step2() {
      D.modal({ title: 'Create a company page · 2 of 3 — company details', body: '<div class="dbk-f"><label for="ccN">Company legal name *</label><input id="ccN" data-req value="' + esc(W.name || '') + '"></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="ccS">Main activity *</label><select id="ccS" data-req><option value="">Choose…</option>' + SECTORS.slice(1).map(function (s) { return '<option' + (W.sector === s ? ' selected' : '') + '>' + esc(s) + '</option>'; }).join('') + '</select></div>' +
        '<div class="dbk-f"><label for="ccG">Governorate *</label><select id="ccG" data-req><option value="">Choose…</option>' + GOVS.slice(1).map(function (g) { return '<option' + (W.gov === g ? ' selected' : '') + '>' + g + '</option>'; }).join('') + '</select></div></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="ccC">City / area *</label><input id="ccC" data-req value="' + esc(W.city || '') + '"></div><div class="dbk-f"><label for="ccP">Company phone *</label><input id="ccP" data-req value="' + esc(W.phone || '') + '"></div></div>' +
        '<div class="dbk-f"><label for="ccE">Company email *</label><input id="ccE" type="email" data-req value="' + esc(W.email || '') + '"></div>',
        primary: { label: 'Next: review', onClick: function (b) {
          if (!D.requireFields(b)) return false;
          var name = b.querySelector('#ccN').value.trim();
          W.name = name; W.sector = b.querySelector('#ccS').value; W.gov = b.querySelector('#ccG').value; W.city = b.querySelector('#ccC').value.trim(); W.phone = b.querySelector('#ccP').value.trim(); W.email = b.querySelector('#ccE').value.trim();
          setTimeout(step4, 40);
        } } });
    }
    function step4() {
      var p = PLANS[W.plan], amount = W.plan === 'vip' ? (W.billing === 'year' ? p.year : p.price) : 0, vat = Math.round(amount * 0.14);
      D.modal({ title: 'Create a company page · 3 of 3 — review' + (amount ? ' and pay' : ''),
        body: '<table class="cp-spec"><tr><td>Company</td><td>' + esc(W.name) + '</td></tr><tr><td>Activity</td><td>' + esc(W.sector) + '</td></tr><tr><td>Location</td><td>' + esc(W.city) + ', ' + esc(W.gov) + '</td></tr>' +
          '<tr><td>Verification</td><td>Optional, later — from your page (gives the Verified badge)</td></tr><tr><td>Plan</td><td><b>' + p.name + '</b>' + (amount ? ' · ' + (W.billing === 'year' ? 'yearly' : 'monthly') : '') + '</td></tr>' +
          (amount ? '<tr><td>Subtotal</td><td>EGP ' + amount.toLocaleString() + '</td></tr><tr><td>VAT 14%</td><td>EGP ' + vat.toLocaleString() + '</td></tr><tr><td><b>Total</b></td><td><b>EGP ' + (amount + vat).toLocaleString() + '</b></td></tr>' : '') + '</table>' +
          (amount ? '<div class="pay-row"><label><input type="radio" name="pay" checked> Card</label><label><input type="radio" name="pay"> Fawry</label><label><input type="radio" name="pay"> Bank transfer</label></div><p class="cp-muted">Demo — no payment is taken.</p>' : ''),
        primary: { label: amount ? 'Pay EGP ' + (amount + vat).toLocaleString() + ' and create' : 'Create my page', onClick: function () {
          var me = window.ME || {}, base = slugify(W.name), slug = base, n = 2, created = store('created_companies') || [];
          while (companies(true).some(function (c) { return c.slug === slug; })) slug = base + '-' + (n++);   /* same name allowed; the link stays unique */
          var co = { slug: slug, registry: '', plan: W.plan, licensed: false, status: 'unverified', name: W.name, owner: me.id, color: '#1a56db', sector: W.sector, sectors: [W.sector], city: W.city, gov: W.gov,
            founded: new Date().getFullYear(), employees: '—', verified: false, level: '', rating: 0, reviews: 0, reply: '—', tagline: 'Tell buyers what you make or offer.', about: '', certs: [],
            phone: W.phone, email: W.email, whatsapp: W.phone.replace(/\D/g, ''), website: '', address: W.city + ', ' + W.gov, hours: '', services: [], products: [], jobs: [], billing: W.billing, createdAt: Date.now() };
          created.push(co); store('created_companies', created); store('acting', slug); drawSwitch(true);
          S.open = slug; S.tab = 'overview'; window.__dxKeepCompany = true; try { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); else render(); } finally { window.__dxKeepCompany = false; }
          setTimeout(function () { openEditor(); }, 60);
          toast(W.name + ' is live' + (amount ? ' on VIP' : '') + ' — add your products and details');
        } } });
    }
    step1();
  }
  function verifyDialog(slug) {
    var co = bySlug(slug); if (!co || !D) return;
    D.modal({ title: 'Verify ' + co.name, body: '<p class="cp-muted">Checked by Drugbox' + (isVip(co) ? ' within 48 hours (VIP)' : ' within 2 working days') + '. Never shown to other users. Your page stays live meanwhile.</p>' +
      '<div class="dbk-row"><div class="dbk-f"><label for="vfRN">Commercial registry number *</label><input id="vfRN" data-req inputmode="numeric"></div><div class="dbk-f"><label for="vfR">Registry document *</label><input id="vfR" type="file" accept=".pdf,.jpg,.png"></div></div>' +
      '<div class="dbk-f"><label for="vfT">Tax card *</label><input id="vfT" type="file" accept=".pdf,.jpg,.png"></div>' +
      '<div class="dbk-f"><label for="vfL">Licence (EDA, pharmacy, distribution or industrial)</label><input id="vfL" type="file" accept=".pdf,.jpg,.png"><small class="cp-muted">Needed to buy or sell medicines on Drugbox.</small></div>',
      primary: { label: 'Send for verification', onClick: function (b) {
        if (!D.requireFields(b)) return false;
        var rn = b.querySelector('#vfRN').value.replace(/\D/g, '');
        if (rn.length < 4) { b.querySelector('#vfRN').classList.add('dbk-err'); toast('Enter the commercial registry number'); return false; }
        if (!b.querySelector('#vfR').files.length || !b.querySelector('#vfT').files.length) { toast('Registry document and tax card are required'); return false; }
        var created = store('created_companies') || [];
        created.forEach(function (c) { if (c.slug === co.slug) { c.status = 'pending'; c.registry = rn; c.licencePending = !!b.querySelector('#vfL').files.length; } }); store('created_companies', created);
        render(); toast('Documents sent — we will verify ' + co.name);
      } } });
  }
  function upgradeDialog(slug) {
    var co = bySlug(slug); if (!co) return;
    var m = D.modal({ title: 'Upgrade ' + co.name + ' to VIP', body: planCards('vip', 'month'),
      primary: { label: 'Continue to payment', onClick: function (b) {
        var billing = b.querySelector('input[name=plBill]:checked').value, amount = billing === 'year' ? PLANS.vip.year : PLANS.vip.price, vat = Math.round(amount * 0.14);
        setTimeout(function () {
          D.modal({ title: 'Pay for VIP', body: '<table class="cp-spec"><tr><td>' + esc(co.name) + ' · VIP ' + (billing === 'year' ? 'yearly' : 'monthly') + '</td><td>EGP ' + amount.toLocaleString() + '</td></tr><tr><td>VAT 14%</td><td>EGP ' + vat.toLocaleString() + '</td></tr><tr><td><b>Total</b></td><td><b>EGP ' + (amount + vat).toLocaleString() + '</b></td></tr></table><p class="cp-muted">Demo — no payment is taken.</p>',
            primary: { label: 'Pay EGP ' + (amount + vat).toLocaleString(), onClick: function () {
              var created = store('created_companies') || [], edits = store('company_edits') || {};
              if (created.some(function (c) { return c.slug === slug; })) { created.forEach(function (c) { if (c.slug === slug) { c.plan = 'vip'; c.billing = billing; } }); store('created_companies', created); }
              else { edits[slug] = Object.assign({}, edits[slug] || {}, { plan: 'vip', billing: billing }); store('company_edits', edits); }
              render(); toast(co.name + ' is now VIP');
            } } });
        }, 40);
      } } });
    m.el.querySelector('.dbk-box').classList.add('dbk-wide');
    m.el.addEventListener('change', function (e) { if (e.target.name === 'plBill' || e.target.name === 'plPick') { m.el.querySelector('.dbk-bd').innerHTML = planCards('vip', m.el.querySelector('input[name=plBill]:checked').value); } });
  }
  function myCompaniesDialog() {
    var list = myCompanies();
    var m = D.modal({ title: 'My companies', secondary: 'Close', primary: { label: 'Create another company', onClick: function () { setTimeout(createCompanyDialog, 40); } },
      body: '<p class="cp-muted">Each company has its own page, plan, verification and inbox. “Act as” decides which company sends your requests.</p>' + list.map(function (c) {
        var acting = mine() && mine().slug === c.slug, renew = '';
        if (isVip(c)) { var d = new Date(c.createdAt || Date.now()); if (c.billing === 'year') d.setFullYear(d.getFullYear() + 1); else d.setMonth(d.getMonth() + 1); renew = ' · renews ' + d.toLocaleDateString(); }
        return '<div class="mr-row">' + logo(c, 'dr-logo sm') + '<div class="mr-b"><b>' + esc(c.name) + (acting ? ' <span class="mr-st st-acc">Acting as</span>' : '') + '</b><small>' + (isVip(c) ? 'VIP' + (c.billing === 'year' ? ' yearly' : ' monthly') : 'Basic') + renew + ' · ' + (c.status === 'verified' ? 'verified' : c.status === 'pending' ? 'verification in review' : 'not verified') + ' · ' + c.products.length + ' products · ' + (window.dxDeals ? window.dxDeals.openCount(c.slug) : 0) + ' open requests</small></div>' +
          '<span class="mr-acts"><button type="button" class="dr-btn sm" data-open2="' + c.slug + '">Open</button>' + (acting ? '' : '<button type="button" class="dr-btn sm" data-act2="' + c.slug + '">Act as</button>') + (isVip(c) ? '' : '<button type="button" class="dr-btn p sm" data-up2="' + c.slug + '">Upgrade</button>') + '</span></div>'; }).join('') });
    m.el.addEventListener('click', function (e) { var o = e.target.closest('[data-open2]'), u = e.target.closest('[data-up2]'), a = e.target.closest('[data-act2]');
      if (o) { m.close(); openCompany(o.dataset.open2); } if (u) { m.close(); upgradeDialog(u.dataset.up2); }
      if (a) { setActing(a.dataset.act2); m.close(); myCompaniesDialog(); } });
  }
  window.dxCreateCompany = function () { createCompanyDialog(); };
  function setActing(slug) { store('acting', slug); var c = bySlug(slug); toast('Now acting as ' + (c ? c.name : slug)); drawSwitch(true); if (document.body.getAttribute('data-page') === 'companies') render(); }
  window.dxActing = function () { return mine(); };
  function drawSwitch(force) {
    var right = document.querySelector('.topbar .top-right'); if (!right) return;
    var list = myCompanies(), btn = document.getElementById('dxCoSwitch');
    if (!list.length) { if (btn) btn.remove(); return; }
    var act = mine(), sig = act.slug + '|' + list.length + '|' + act.plan;
    if (btn && btn.dataset.sig === sig && !force) return;
    if (!btn) { btn = document.createElement('button'); btn.id = 'dxCoSwitch'; btn.type = 'button'; btn.className = 'dx-coswitch'; btn.setAttribute('aria-haspopup', 'menu'); right.insertBefore(btn, right.firstChild); }
    btn.dataset.sig = sig; btn.title = 'You are acting as ' + act.name;
    btn.innerHTML = logo(act, 'cs-logo') + '<span class="cs-n">' + esc(act.name) + '</span>' + vipBadge(act) + '<span class="cs-c">▾</span>';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#dxCoSwitch'), pop = document.getElementById('dxCoMenu');
    if (!b) { if (pop && !e.target.closest('#dxCoMenu')) pop.remove(); return; }
    if (pop) { pop.remove(); return; }
    var r = b.getBoundingClientRect(), list = myCompanies(), act = mine();
    pop = document.createElement('div'); pop.id = 'dxCoMenu'; pop.setAttribute('role', 'menu');
    pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - 288, r.right - 280)) + 'px';
    pop.innerHTML = '<div class="dx-pop-h">Act as</div>' + list.map(function (c) { return '<button type="button" role="menuitemradio" aria-checked="' + (c.slug === act.slug) + '" class="cm-co' + (c.slug === act.slug ? ' on' : '') + '" data-cs="' + c.slug + '">' + logo(c, 'cs-logo') + '<span><b>' + esc(c.name) + '</b><small>' + (isVip(c) ? 'VIP' : 'Basic') + (c.status === 'pending' ? ' · pending' : '') + '</small></span></button>'; }).join('') +
      '<div class="cm-sep"></div><button type="button" class="cm-co" data-cs-ws="1">' + ic('building') + '<span><b>' + esc(act.name) + '\u2019s workspace</b></span></button><button type="button" class="cm-co" data-cs-open="1">' + ic('building') + '<span><b>Open ' + esc(act.name) + '\u2019s page</b></span></button><button type="button" class="cm-co" data-cs-all="1">' + ic('clipboard') + '<span><b>Manage my companies</b></span></button><button type="button" class="cm-co" data-cs-new="1">' + ic('plus') + '<span><b>Create a company page</b></span></button>';
    document.body.appendChild(pop);
    pop.addEventListener('click', function (ev) {
      var x = ev.target.closest('button'); if (!x) return; pop.remove();
      if (x.dataset.cs) setActing(x.dataset.cs);
      else if (x.dataset.csWs && window.dxHub) window.dxHub.workspace(mine().slug);
      else if (x.dataset.csOpen) openCompany(mine().slug);
      else if (x.dataset.csAll) { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); myCompaniesDialog(); }
      else if (x.dataset.csNew) { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); createCompanyDialog(); }
    });
  });
  /* ── owner editor (drawer) ── */
  function readImage(file, max, cb) {
    if (!file) return cb(null);
    if (!/^image\//.test(file.type)) { toast('Please choose an image file'); return cb(null); }
    var r = new FileReader(); r.onload = function () { var im = new Image(); im.onload = function () { var k = Math.min(1, max / Math.max(im.width, im.height)), cv = document.createElement('canvas'); cv.width = Math.round(im.width * k); cv.height = Math.round(im.height * k); cv.getContext('2d').drawImage(im, 0, 0, cv.width, cv.height); cb(cv.toDataURL('image/jpeg', 0.82)); }; im.onerror = function () { cb(null); }; im.src = r.result; }; r.readAsDataURL(file);
  }
  function openEditor(focus) {
    var cur = S.open && bySlug(S.open), co = cur && ownsPage(cur) ? cur : mine(); if (!co) { toast('Only company owners can edit a page'); return; }
    var draft = JSON.parse(JSON.stringify(co));
    var el = document.createElement('div'); el.id = 'dxEditor'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-label', 'Edit company page');
    function prodRows() { return draft.products.map(function (p, i) { return '<div class="ed-prod"><img src="' + pimg(draft, p) + '" alt=""><span><b>' + esc(p.name) + '</b><small>' + esc(p.cat) + (p.moq ? ' · MOQ ' + esc(p.moq) : '') + '</small></span><button type="button" data-pe="' + i + '">Edit</button><button type="button" data-pd="' + i + '" aria-label="Delete">×</button></div>'; }).join(''); }
    function draw() {
      el.innerHTML = '<div class="ed-box"><div class="ed-h"><b>Edit your company page</b><button type="button" class="ed-x" aria-label="Close">×</button></div><div class="ed-b">' +
        '<div class="ed-sec"><h4>Branding</h4><div class="ed-brand">' + logo(draft, 'cp-logo sm') + '<label class="dr-btn sm">Upload logo<input type="file" accept="image/*" id="edLogo" hidden></label>' +
        '<label class="dr-btn sm">Upload cover photo<input type="file" accept="image/*" id="edCover" hidden></label>' + '<input type="color" id="edColor" value="' + esc(draft.color) + '" aria-label="Brand colour"></div></div>' +
        '<div class="ed-sec"><h4>About</h4><div class="dbk-f"><label for="edTag">Tagline</label><input id="edTag" value="' + esc(draft.tagline) + '" maxlength="140"></div>' +
        '<div class="dbk-f"><label for="edAbout">Description</label><textarea id="edAbout" rows="4">' + esc(draft.about) + '</textarea></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="edFounded">Founded</label><input id="edFounded" value="' + esc(draft.founded) + '"></div><div class="dbk-f"><label for="edEmp">Team size</label><input id="edEmp" value="' + esc(draft.employees) + '"></div></div></div>' +
        '<div class="ed-sec"><h4>Products <small>' + draft.products.length + '</small></h4><div class="ed-prods">' + prodRows() + '</div><button type="button" class="dr-btn sm" id="edAddP">' + ic('plus') + 'Add a product</button><div id="edPForm"></div></div>' +
        '<div class="ed-sec"><h4>Certificates <small>verified by Drugbox before they show</small></h4><div class="ed-certs">' + draft.certs.map(function (x) { return '<span class="cp-cert">' + ic('seal') + esc(x) + ' <small>verified</small></span>'; }).join('') + (draft.certsPending || []).map(function (x) { return '<span class="cp-cert pend">' + ic('warning') + esc(x.name) + ' <small>under review</small></span>'; }).join('') + '</div>' +
        '<div class="dbk-row" style="margin-top:8px"><div class="dbk-f"><label for="edCName">Certificate</label><select id="edCName"><option value="">Choose…</option><option>WHO-GMP</option><option>ISO 9001</option><option>ISO 22716</option><option>ISO 17025</option><option>GDP</option><option>EDA licensed</option><option>Halal</option></select></div><div class="dbk-f"><label for="edCFile">Certificate document</label><input id="edCFile" type="file" accept=".pdf,.jpg,.png"></div></div><button type="button" class="dr-btn sm" id="edCAdd">' + ic('plus') + 'Send for verification</button></div>' +
        '<div class="ed-sec"><h4>Services <small>one per line</small></h4><textarea id="edSvc" rows="4">' + esc((draft.services || []).join('\n')) + '</textarea></div>' +
        '<div class="ed-sec"><h4>Contact</h4><div class="dbk-row"><div class="dbk-f"><label for="edPhone">Phone</label><input id="edPhone" value="' + esc(draft.phone) + '"></div><div class="dbk-f"><label for="edWa">WhatsApp (digits)</label><input id="edWa" value="' + esc(draft.whatsapp) + '" inputmode="numeric"></div></div>' +
        '<div class="dbk-row"><div class="dbk-f"><label for="edEmail">Email</label><input id="edEmail" type="email" value="' + esc(draft.email) + '"></div><div class="dbk-f"><label for="edWeb">Website</label><input id="edWeb" value="' + esc(draft.website) + '"></div></div>' +
        '<div class="dbk-f"><label for="edAddr">Address</label><input id="edAddr" value="' + esc(draft.address) + '"></div><div class="dbk-f"><label for="edHours">Working hours</label><input id="edHours" value="' + esc(draft.hours) + '"></div></div>' +
        '</div><div class="ed-f"><button type="button" class="dr-btn" id="edCancel">Cancel</button><button type="button" class="dr-btn p" id="edSave">Save and publish</button></div></div>';
      if (focus === 'products') { var s = el.querySelector('#edAddP'); if (s) setTimeout(function () { s.scrollIntoView({ block: 'center' }); s.click(); }, 50); focus = null; }
    }
    function collect() {
      var v = function (id) { var x = el.querySelector('#' + id); return x ? x.value.trim() : ''; };
      draft.tagline = v('edTag'); draft.about = v('edAbout'); draft.founded = v('edFounded'); draft.employees = v('edEmp'); draft.phone = v('edPhone'); draft.whatsapp = v('edWa').replace(/\D/g, '');
      draft.email = v('edEmail'); draft.website = v('edWeb').replace(/^https?:\/\//, ''); draft.address = v('edAddr'); draft.hours = v('edHours');
      draft.services = v('edSvc').split('\n').map(function (s) { return s.trim(); }).filter(Boolean); draft.color = el.querySelector('#edColor').value;
    }
    function productForm(i) {
      var p = i != null ? draft.products[i] : { id: 'p' + Date.now(), name: '', cat: 'Finished dosage', kind: 'box', desc: '', moq: '', price: '', specs: [] };
      var f = el.querySelector('#edPForm');
      f.innerHTML = '<div class="ed-pform"><div class="ed-pimg"><img id="edPImg" src="' + (p.name || p.img ? pimg(draft, p) : packshot(p.kind, draft.color, 'Photo')) + '" alt=""><label class="dr-btn sm">Upload photo<input type="file" accept="image/*" id="edPFile" hidden></label></div>' +
        '<div class="dbk-f"><label for="edPName">Product name *</label><input id="edPName" value="' + esc(p.name) + '"></div><div class="dbk-row"><div class="dbk-f"><label for="edPCat">Category</label><select id="edPCat">' + ['Finished dosage', 'Cosmetics', 'Supplements', 'API', 'Excipient', 'Packaging', 'Toll manufacturing', 'Service'].map(function (x) { return '<option' + (x === p.cat ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select></div>' +
        '<div class="dbk-f"><label for="edPKind">Pack</label><select id="edPKind">' + [['box', 'Carton'], ['bottle', 'Bottle'], ['blister', 'Blister'], ['sachet', 'Sachet'], ['jar', 'Jar'], ['tube', 'Tube'], ['drum', 'Drum / bulk'], ['lab', 'Service']].map(function (x) { return '<option value="' + x[0] + '"' + (x[0] === p.kind ? ' selected' : '') + '>' + x[1] + '</option>'; }).join('') + '</select></div></div>' +
        '<div class="dbk-f"><label for="edPDesc">Description</label><textarea id="edPDesc" rows="2">' + esc(p.desc) + '</textarea></div><div class="dbk-row"><div class="dbk-f"><label for="edPMoq">Minimum order</label><input id="edPMoq" value="' + esc(p.moq) + '"></div><div class="dbk-f"><label for="edPPrice">Price (optional)</label><input id="edPPrice" value="' + esc(p.price) + '" placeholder="e.g. US$ 2.10"></div></div>' +
        '<div class="ed-pacts"><button type="button" class="dr-btn sm" id="edPCancel">Cancel</button><button type="button" class="dr-btn p sm" id="edPSave">' + (i != null ? 'Update product' : 'Add product') + '</button></div></div>';
      f.querySelector('#edPFile').onchange = function (e) { readImage(e.target.files[0], 900, function (d) { if (d) { p.img = d; f.querySelector('#edPImg').src = d; } }); };
      f.querySelector('#edPCancel').onclick = function () { f.innerHTML = ''; };
      f.querySelector('#edPSave').onclick = function () {
        var name = f.querySelector('#edPName').value.trim(); if (!name) { f.querySelector('#edPName').classList.add('dbk-err'); toast('Product name is required'); return; }
        p.name = name; p.cat = f.querySelector('#edPCat').value; p.kind = f.querySelector('#edPKind').value; p.desc = f.querySelector('#edPDesc').value.trim(); p.moq = f.querySelector('#edPMoq').value.trim(); p.price = f.querySelector('#edPPrice').value.trim();
        collect(); if (i == null) draft.products.push(p); draw(); toast(i == null ? 'Product added — save to publish' : 'Product updated — save to publish');
      };
      f.querySelector('#edPName').focus();
    }
    el.addEventListener('click', function (e) {
      if (e.target === el || e.target.closest('.ed-x') || e.target.closest('#edCancel')) { el.remove(); return; }
      if (e.target.closest('#edAddP')) { collect(); productForm(null); return; }
      if (e.target.closest('#edCAdd')) { var cn = el.querySelector('#edCName').value, cf = el.querySelector('#edCFile').files[0];
        if (!cn) { toast('Choose the certificate'); return; } if (!cf) { toast('Attach the certificate document'); return; }
        collect(); draft.certsPending = (draft.certsPending || []).concat([{ name: cn, file: cf.name, at: Date.now() }]); draw(); toast(cn + ' sent for verification — it shows on your page once approved'); return; }
      var pe = e.target.closest('[data-pe]'); if (pe) { collect(); productForm(+pe.dataset.pe); return; }
      var pd = e.target.closest('[data-pd]'); if (pd) { collect(); draft.products.splice(+pd.dataset.pd, 1); draw(); return; }
      if (e.target.closest('#edSave')) {
        collect();
        var created = store('created_companies') || []; if (created.some(function (c) { return c.slug === draft.slug; })) { created = created.map(function (c) { return c.slug === draft.slug ? Object.assign({}, c, { tagline: draft.tagline, about: draft.about, founded: draft.founded, employees: draft.employees, phone: draft.phone, whatsapp: draft.whatsapp, email: draft.email, website: draft.website, address: draft.address, hours: draft.hours, services: draft.services, products: draft.products, color: draft.color, logo: draft.logo || null, cover: draft.cover || null, certsPending: draft.certsPending || [] }) : c; }); if (!store('created_companies', created)) { toast('Could not save — the photos are too large for this demo.'); return; } el.remove(); S.open = draft.slug; render(); toast('Page saved'); return; }
        var edits = store('company_edits') || {}; edits[draft.slug] = { tagline: draft.tagline, about: draft.about, founded: draft.founded, employees: draft.employees, phone: draft.phone, whatsapp: draft.whatsapp, email: draft.email, website: draft.website, address: draft.address, hours: draft.hours, services: draft.services, products: draft.products, color: draft.color, logo: draft.logo || null, cover: draft.cover || null, certsPending: draft.certsPending || [] };
        if (!store('company_edits', edits)) { toast('Could not save — the photos are too large for this demo. Try smaller images.'); return; }
        el.remove(); S.open = draft.slug; render(); toast('Company page published');
      }
    });
    el.addEventListener('change', function (e) {
      if (e.target.id === 'edLogo') readImage(e.target.files[0], 400, function (d) { if (d) { collect(); draft.logo = d; draw(); } });
      if (e.target.id === 'edCover') readImage(e.target.files[0], 1600, function (d) { if (d) { collect(); draft.cover = d; draw(); toast('Cover photo ready — save to publish'); } });
    });
    draw(); document.body.appendChild(el);
  }

  /* ── one click handler for the whole directory ── */
  document.addEventListener('click', function (e) {
    var root = e.target.closest && e.target.closest('#dxDir'); if (!root) return;
    var t = e.target.closest('[data-go],[data-rfq],[data-mine],[data-sector],[data-cert],[data-reset],[data-back],[data-tab],[data-edit],[data-msg],[data-follow],[data-share],[data-apply],[data-pdetail],[data-uid],[data-reply],[data-offer],[data-empreviews],[data-myreq],[data-sendquote],[data-create],[data-mycos],[data-upgrade],[data-verify]');
    if (!t) { var cardEl = e.target.closest('.dr-card'); if (cardEl && !e.target.closest('button,a,input,select')) openCompany(cardEl.dataset.slug); return; }
    var co = S.open && bySlug(S.open);
    if (t.dataset.go) openCompany(t.dataset.go);
    else if (t.dataset.rfq) rfqDialog(t.dataset.rfq, t.dataset.prod, t.dataset.svc);
    else if (t.dataset.mine) { var my = mine(); if (my) { openCompany(my.slug); setTimeout(function () { openEditor(); }, 30); } else listCompanyDialog(); }
    else if (t.dataset.sector) { S.sector = t.dataset.sector; render(); }
    else if (t.dataset.cert) { var i = S.certs.indexOf(t.dataset.cert); if (i >= 0) S.certs.splice(i, 1); else S.certs.push(t.dataset.cert); render(); }
    else if (t.dataset.reset) { S.q = ''; S.sector = 'All'; S.gov = 'All governorates'; S.certs = []; S.verified = false; render(); }
    else if (t.dataset.back) { S.open = null; render(); var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0; }
    else if (t.dataset.tab) { S.tab = t.dataset.tab; render(); }
    else if (t.dataset.edit) openEditor(t.dataset.edit);
    else if (t.dataset.msg && co) { if (window.dxOpenChat) window.dxOpenChat(co.name); else { window.__mxTo = co.name; window.goto('messages'); } }
    else if (t.dataset.follow && co) { var f = store('follows') || [], k = f.indexOf(co.slug); if (k >= 0) f.splice(k, 1); else f.push(co.slug); store('follows', f); render(); toast(k >= 0 ? 'Unfollowed ' + co.name : 'Following ' + co.name + ' — you\u2019ll see their new products and jobs'); }
    else if (t.dataset.share && co) { var url = 'https://drugbox.app/c/' + co.slug; if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { toast('Link copied: ' + url); }, function () { toast(url); }); else toast(url); }
    else if (t.dataset.apply != null && co) { var job = jobsOf(co)[+t.dataset.apply]; if (!job) return;
      if (job.onJobs) { window.goto('jobs'); var h = document.querySelector('#jx .mode-opt[data-mode="hunting"]'); if (h) h.click();
        setTimeout(function () { var card = Array.prototype.find.call(document.querySelectorAll('#jx #huntingView .jcard'), function (c) { return c.textContent.indexOf(job.t) >= 0; }); if (card) { card.scrollIntoView({ block: 'center' }); card.classList.add('dx-flash'); var ab = card.querySelector('.apply-btn'); if (ab && !ab.classList.contains('dbk-done')) ab.click(); } }, 60); }
      else applyDialog(co, job); }
    else if (t.dataset.offer) { var q = t.dataset.offer.split('—')[0].trim(); window.goto('market'); var si = document.getElementById('searchIn'); if (si) si.value = q; if (window.__mkxFilter) window.__mkxFilter(q); }
    else if (t.dataset.empreviews && co) { window.goto('jobs'); var hm = document.querySelector('#jx .mode-opt[data-mode="hunting"]'); if (hm) hm.click(); setTimeout(function () { var card = Array.prototype.find.call(document.querySelectorAll('#jx #huntingView .jcard'), function (c) { return (c.querySelector('.jc-company span') || {}).textContent === co.name; }); var r = card && card.querySelector('.jx-rate'); if (r) r.click(); }, 80); }
    else if (t.dataset.myreq) myRequestsDialog();
    else if (t.dataset.create) createCompanyDialog();
    else if (t.dataset.mycos) myCompaniesDialog();
    else if (t.dataset.upgrade) upgradeDialog(t.dataset.upgrade);
    else if (t.dataset.verify) verifyDialog(t.dataset.verify);
    else if (t.dataset.sendquote && co) sendQuoteDialog(co, +t.dataset.sendquote);
    else if (t.dataset.pdetail && co) { var p = co.products.find(function (x) { return x.id === t.dataset.pdetail; }); if (p) productDialog(co, p); }
    else if (t.dataset.uid && window.gotoProfile) window.gotoProfile(+t.dataset.uid);
    else if (t.dataset.reply && window.dxOpenChat) window.dxOpenChat(t.dataset.reply);
  });
  document.addEventListener('input', function (e) {
    if (e.target.id !== 'drQ') return; S.q = e.target.value; var pos = e.target.selectionStart;
    clearTimeout(window.__drT); window.__drT = setTimeout(function () { render(); var q = document.getElementById('drQ'); if (q) { q.focus(); try { q.setSelectionRange(pos, pos); } catch (x) {} } }, 180);
  });
  document.addEventListener('change', function (e) {
    if (e.target.id === 'drActing') { setActing(e.target.value); return; }
    if (e.target.id === 'drGov') { S.gov = e.target.value; render(); } else if (e.target.id === 'drSort') { S.sort = e.target.value; render(); } else if (e.target.id === 'drVer') { S.verified = e.target.checked; render(); }
  });

  function profileCompanies() {
    var nameEl = document.querySelector('.profile-name'), me = window.ME; if (!nameEl || !me || nameEl.textContent.indexOf(me.name) !== 0) return;
    var host = document.getElementById('profileTabContent'); if (!host || host.parentNode.querySelector('.dx-mycos')) return;
    var list = myCompanies(), box = document.createElement('div'); box.className = 'dx-mycos';
    box.innerHTML = '<div class="in-h">' + ic('building') + 'My companies <span>' + list.length + '</span></div><div class="mc-row">' + list.map(function (c) { return '<button type="button" class="mc-co" data-mc="' + c.slug + '">' + logo(c, 'dr-logo sm') + '<span><b>' + esc(c.name) + '</b><small>' + (isVip(c) ? 'VIP' : 'Basic') + (c.status !== 'verified' ? ' · not verified' : '') + '</small></span></button>'; }).join('') +
      '<button type="button" class="mc-new" data-mcnew="1">' + ic('plus') + 'Create a company page</button></div>';
    host.parentNode.insertBefore(box, host);
    box.addEventListener('click', function (e) { var c = e.target.closest('[data-mc]'); if (c) openCompany(c.dataset.mc); if (e.target.closest('[data-mcnew]')) createCompanyDialog(); });
  }
  C.onRender('profile-companies', profileCompanies);
  C.onRender('company-switch', function () { drawSwitch(false); });
  C.onRender('company-links', linkNames);
  /* ── take over the old Market Board route ── */
  window.renderMarketBoard = function (c) { render(c); };
  /* leaving the directory from the sidebar returns to the list next time */
  document.addEventListener('dx:beforepage', function (e) { if (e.detail.page === 'companies' && !window.__dxKeepCompany) S.open = null; });   /* plain navigation → the directory list */
  var origOpen = openCompany;
  window.dxOpenCompany = function (slug, tab) { window.__dxKeepCompany = true; origOpen(slug, tab); window.__dxKeepCompany = false; };
  document.addEventListener('click', function (e) { var n = e.target.closest && e.target.closest('#snl-companies, #mb-companies'); if (n) { S.open = null; } }, true);
})();
