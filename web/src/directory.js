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
  function store(k, v) { if (v !== undefined) window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;   /* every write invalidates the memoised company list (directory, hub, tiers) */
    if (window.dxStoreHook) { var __h = window.dxStoreHook(k, v); if (__h !== undefined) return __h; } try { if (v === undefined) return __typed(k, JSON.parse(localStorage.getItem('dx_' + k) || 'null')); localStorage.setItem('dx_' + k, JSON.stringify(v)); return true; } catch (e) { quotaToast(); return false; } }
  var __qt = 0; function quotaToast() { if (Date.now() - __qt < 3000) return; __qt = Date.now(); toast('Could not save — the browser storage is full. Remove large photos or old data and try again.'); }   /* a failed save is never reported as success */
  function toast(m) { if (D) D.toast(m); }
  /* ── sinks: a picture or colour that comes from the store (or the database) is used only when it is a safe URL / colour ── */
  function safeUrl(u) { u = String(u == null ? '' : u).trim(); if (!u || /["'<>()\s\\]/.test(u)) return ''; if (/^data:image\/(png|jpe?g|gif|webp|svg\+xml);/i.test(u) || /^blob:/i.test(u)) return u; try { var x = new URL(u, location.href); return x.protocol === 'https:' || x.protocol === 'http:' ? u : ''; } catch (e) { return ''; } }
  function cssUrl(u) { u = safeUrl(u); return u ? 'background-image:url("' + esc(u) + '")' : ''; }   /* '' → the caller falls back to the brand colour */
  function safeColor(c) { return /^#[0-9a-f]{3,8}$/i.test(String(c || '')) ? c : '#1a56db'; }

  /* ── product pictures (packshots) drawn in the company's colour; owners replace them with real photos ── */
  function packshot(kind, color, label) {
    var c = safeColor(color), l = esc(String(label || '').slice(0, 14)), body;
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

  /* The merged company list is built once per store version (window.__dxStoreVer, bumped by every store() write and by
     each directory render) instead of on every call: a render used to re-read and JSON.parse localStorage per card. */
  var __cc = null, __ed = null;
  function ver() { return window.__dxStoreVer || 0; }
  function edits_() { var v = ver(); if (!__ed || __ed.v !== v) __ed = { v: v, o: store('company_edits') || {} }; return __ed.o; }   /* read-only; writers still call store() */
  function companies(all) {
    var live = window.dxLiveCompanies, v = ver(), seeds = window.dxDirSeeds;
    if (__cc && __cc.v === v && __cc.live === live && __cc.n === (live ? live.length : -1) && __cc.seeds === seeds) return __cc.list;
    var edits = edits_(), created = store('created_companies') || [], rv = store('supplier_reviews') || {};
    var list = (live || SEED.concat(seeds || [], created)).map(function (s) { var e = edits[s.slug], c = e ? Object.assign({}, s, e) : s, r = rv[c.slug];
      if (r && r.length) { var sum = r.reduce(function (a, x) { return a + x.stars; }, 0); c = Object.assign({}, c, { rating: ((c.rating || 0) * (c.reviews || 0) + sum) / ((c.reviews || 0) + r.length), reviews: (c.reviews || 0) + r.length }); }
      return c; });   /* pages are public from creation; unverified ones are labelled */
    __cc = { v: v, live: live, n: live ? live.length : -1, seeds: seeds, list: list };
    return list;
  }
  var __bs = null;
  function bySlug(slug) { var list = companies(); if (!__bs || __bs.list !== list) { var m = Object.create(null); list.forEach(function (c) { if (!(c.slug in m)) m[c.slug] = c; }); __bs = { list: list, m: m }; } return __bs.m[slug]; }
  function myCompanies() { var me = window.ME || {}; return companies().filter(function (c) { return c.owner === me.id; }); }
  function mine() { var list = myCompanies(); if (!list.length) return null; var a = store('acting'); return list.find(function (c) { return c.slug === a; }) || list[0]; }   /* the company you act as */
  function ownsPage(co) { var me = window.ME || {}; return co && co.owner === me.id; }
  /* monogram from the first letter of the first two words — Arabic names included */
  function initials(n) { var w = String(n == null ? '' : n).replace(/^(Dr\.|Eng\.)\s*/i, '').split(/\s+/).map(function (x) { var m = /\p{L}/u.exec(x); return m ? m[0] : ''; }).filter(Boolean); return w.slice(0, 2).join('').toUpperCase(); }
  function logo(c, cls) { var u = safeUrl(c.logo); return u ? '<span class="' + esc(cls) + ' has-img"><img src="' + esc(u) + '" alt=""></span>' : '<span class="' + esc(cls) + '" style="background:' + safeColor(c.color) + '">' + esc(initials(c.name)) + '</span>'; }
  function pimg(c, p) { return safeUrl(p.img) || packshot(p.kind, c.color, String(p.name || '').split(' ')[0]); }


  /* ── one company, everywhere: company names across the app open the company page ── */
  var WORD = /[\p{L}\p{N}]/u;
  function wordAt(text, name) {   /* index of `name` as whole words ('Quadra Pharm' is not linked inside 'Quadra Pharmaceuticals'), else -1 */
    for (var k = text.indexOf(name); k >= 0; k = text.indexOf(name, k + 1)) { var a = text.charAt(k - 1), b = text.charAt(k + name.length); if (!WORD.test(a) && !WORD.test(b)) return k; }
    return -1;
  }
  function linkNames() {
    var list = companies(); if (!list.length) return;
    var names = list.map(function (c) { return { n: c.name, s: c.slug }; }).sort(function (a, b) { return b.n.length - a.n.length; });
    document.querySelectorAll('#mkx .seller-sub, #mkx .sc-provider, #mkx .dc-buyer, #mkx .jc-company, #jx .jc-company > span:first-child, .post-sub').forEach(function (el) {
      if (el.dataset.dxco) return; el.dataset.dxco = '1';
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), n;
      while ((n = w.nextNode())) {
        for (var i = 0; i < names.length; i++) {
          var k = wordAt(n.nodeValue, names[i].n); if (k < 0) continue;
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

  /* The directory, company page and tabs are drawn by the company hub (hub-ui.js); the pre-hub renderers were removed. */
  function render(c) {
    c = c || document.getElementById('content'); if (!c) return;
    c.style.padding = '';
    window.__dxStoreVer = (window.__dxStoreVer || 0) + 1;   /* fresh company list for this render (the live adapter updates company objects in place) */
    var co = S.open && bySlug(S.open);
    if (window.dxHub && window.dxHub.render(c, S, co)) return;   /* the company hub draws the directory, company page and workspace */
    S.open = null; c.innerHTML = '<div id="dxDir"></div>';
  }
  function openCompany(slug, tab) {
    S.open = slug; S.tab = tab || 'overview';
    if (document.body.getAttribute('data-page') !== 'companies') { window.__dxKeepCompany = true; try { window.goto('companies'); } finally { window.__dxKeepCompany = false; } } else { render(); var sc = document.getElementById('content'); if (sc) sc.scrollTop = 0; }
  }
  window.dxOpenCompany = openCompany;
  window.dxDirectory = { list: companies, open: openCompany };
  window.dxDir = { companies: companies, bySlug: bySlug, render: function () { render(); }, S: S, open: function (s, t) { openCompany(s, t); }, rfq: function (s, p, v) { rfqDialog(s, p, v); },
    myCompanies: function () { return myCompanies(); }, mine: function () { return mine(); }, store: store, edits: edits_, logo: logo, initials: initials, safeUrl: safeUrl, cssUrl: cssUrl, safeColor: safeColor, pimg: pimg, packshot: packshot, isVip: isVip, inbox: inbox, myReqs: myReqs,
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
  function rfqDialog(slug, prodId, svc) {
    var co = bySlug(slug); if (!co || !D) return;
    var __a = mine(); if (!__a) { D.toast('Create or claim your company page first'); return; }   /* quotes and service requests are sent on behalf of a company */
    if (__a.slug === co.slug) { D.toast('You are acting as ' + co.name + ' — switch company to request from it'); return; }
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


  /* Arabic letters are transliterated so an Arabic-only name still gets a readable link (drugbox.app/c/shrka-alnyl-lladwya) */
  var AR2L = { 'ا': 'a', 'أ': 'a', 'إ': 'a', 'آ': 'a', 'ب': 'b', 'ت': 't', 'ث': 'th', 'ج': 'g', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'k', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n', 'ه': 'h', 'ة': 'a', 'و': 'w', 'ؤ': 'o', 'ي': 'y', 'ى': 'a', 'ئ': 'e', 'ء': '', 'ـ': '', '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9' };
  function slugify(n) { var s = String(n == null ? '' : n).replace(/[\u064B-\u0652]/g, '').replace(/[\u0600-\u06FF]/g, function (ch) { return ch in AR2L ? AR2L[ch] : ' '; }).normalize('NFD').replace(/[\u0300-\u036F]/g, '').toLowerCase(); return s.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40).replace(/-$/, '') || ('company-' + Date.now()); }
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
    var W = { plan: REQUIRE_VIP_FOR_PAGE ? 'vip' : 'free', billing: 'month' };
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
          D.modal({ title: 'Pay for VIP', body: '<table class="cp-spec" data-billing="' + (billing === 'year' ? 'year' : 'month') + '"><tr><td>' + esc(co.name) + ' · VIP ' + (billing === 'year' ? 'yearly' : 'monthly') + '</td><td>EGP ' + amount.toLocaleString() + '</td></tr><tr><td>VAT 14%</td><td>EGP ' + vat.toLocaleString() + '</td></tr><tr><td><b>Total</b></td><td><b>EGP ' + (amount + vat).toLocaleString() + '</b></td></tr></table><p class="cp-muted">Demo — no payment is taken.</p>',
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
  function addMonths(d, m) { var day = d.getDate(), x = new Date(d.getFullYear(), d.getMonth() + m, 1); x.setDate(Math.min(day, new Date(x.getFullYear(), x.getMonth() + 1, 0).getDate())); return x; }   /* 31 Jan + 1 month = 28/29 Feb, never 3 Mar */
  function myCompaniesDialog() {
    var list = myCompanies();
    var m = D.modal({ title: 'My companies', secondary: 'Close', primary: { label: 'Create another company', onClick: function () { setTimeout(createCompanyDialog, 40); } },
      body: '<p class="cp-muted">Each company has its own page, plan, verification and inbox. “Act as” decides which company sends your requests.</p>' + list.map(function (c) {
        var acting = mine() && mine().slug === c.slug, renew = '';
        if (isVip(c)) { var rd = addMonths(new Date(c.createdAt || Date.now()), c.billing === 'year' ? 12 : 1); renew = ' · renews ' + (window.dxFmtDate ? window.dxFmtDate(rd, false, 'en') : rd.toLocaleDateString()); }
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
    var act = mine(), sig = [act.slug, list.length, act.plan, act.name, act.color, (act.logo || '').length].join('|');   /* a new logo, colour or name redraws the button too */
    if (btn && btn.dataset.sig === sig && !force) return;
    if (!btn) { btn = document.createElement('button'); btn.id = 'dxCoSwitch'; btn.type = 'button'; btn.className = 'dx-coswitch'; btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'false'); right.insertBefore(btn, right.firstChild); }
    btn.dataset.sig = sig; btn.title = 'You are acting as ' + act.name;
    btn.innerHTML = logo(act, 'cs-logo') + '<span class="cs-n">' + esc(act.name) + '</span>' + vipBadge(act) + '<span class="cs-c">▾</span>';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#dxCoSwitch'), pop = document.getElementById('dxCoMenu');
    function closeMenu(back) { if (pop) pop.remove(); var sw = document.getElementById('dxCoSwitch'); if (sw) { sw.setAttribute('aria-expanded', 'false'); if (back) sw.focus(); } }
    if (!b) { if (pop && !e.target.closest('#dxCoMenu')) closeMenu(); return; }
    if (pop) { closeMenu(); return; }
    var r = b.getBoundingClientRect(), list = myCompanies(), act = mine();
    pop = document.createElement('div'); pop.id = 'dxCoMenu'; pop.setAttribute('role', 'menu');
    pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - 288, r.right - 280)) + 'px';
    pop.innerHTML = '<div class="dx-pop-h">Act as</div>' + list.map(function (c) { return '<button type="button" role="menuitemradio" aria-checked="' + (c.slug === act.slug) + '" class="cm-co' + (c.slug === act.slug ? ' on' : '') + '" data-cs="' + c.slug + '">' + logo(c, 'cs-logo') + '<span><b>' + esc(c.name) + '</b><small>' + (isVip(c) ? 'VIP' : 'Basic') + (c.status === 'pending' ? ' · pending' : '') + '</small></span></button>'; }).join('') +
      '<div class="cm-sep"></div><button type="button" role="menuitem" class="cm-co" data-cs-ws="1">' + ic('building') + '<span><b>' + esc(act.name) + '\u2019s workspace</b></span></button><button type="button" role="menuitem" class="cm-co" data-cs-open="1">' + ic('building') + '<span><b>Open ' + esc(act.name) + '\u2019s page</b></span></button><button type="button" role="menuitem" class="cm-co" data-cs-all="1">' + ic('clipboard') + '<span><b>Manage my companies</b></span></button><button type="button" role="menuitem" class="cm-co" data-cs-new="1">' + ic('plus') + '<span><b>Create a company page</b></span></button>';
    document.body.appendChild(pop); b.setAttribute('aria-expanded', 'true');
    /* keyboard: opened with Enter/Space the focus moves in; arrows, Home and End move, Tab and Escape (below) close back to the button */
    var items = [].slice.call(pop.querySelectorAll('button'));
    if (!e.detail) (pop.querySelector('.cm-co.on') || items[0]).focus();
    pop.addEventListener('keydown', function (ev) {
      var k = ev.key, i = items.indexOf(document.activeElement), n = items.length;
      if (k === 'ArrowDown' || k === 'ArrowUp') { ev.preventDefault(); items[i < 0 ? (k === 'ArrowDown' ? 0 : n - 1) : (i + (k === 'ArrowDown' ? 1 : n - 1)) % n].focus(); }
      else if (k === 'Home' || k === 'End') { ev.preventDefault(); items[k === 'Home' ? 0 : n - 1].focus(); }
      else if (k === 'Tab') { ev.preventDefault(); closeMenu(true); }
    });
    pop.addEventListener('click', function (ev) {
      var x = ev.target.closest('button'); if (!x) return; closeMenu(!!x.dataset.cs && !ev.detail);
      if (x.dataset.cs) setActing(x.dataset.cs);
      else if (x.dataset.csWs && window.dxHub) window.dxHub.workspace(mine().slug);
      else if (x.dataset.csOpen) openCompany(mine().slug);
      else if (x.dataset.csAll) { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); myCompaniesDialog(); }
      else if (x.dataset.csNew) { if (document.body.getAttribute('data-page') !== 'companies') window.goto('companies'); createCompanyDialog(); }
    });
  });
  document.addEventListener('keydown', function (e) {
    var pop = document.getElementById('dxCoMenu'); if (e.key !== 'Escape' || !pop || (window.dxTopDialog && window.dxTopDialog())) return;
    var sw = document.getElementById('dxCoSwitch'), back = pop.contains(document.activeElement); pop.remove();
    if (sw) { sw.setAttribute('aria-expanded', 'false'); if (back) sw.focus(); }
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
      if (e.target === el || e.target.closest('.ed-x') || e.target.closest('#edCancel')) { askClose(); return; }
      if (e.target.closest('#edAddP')) { collect(); productForm(null); return; }
      if (e.target.closest('#edCAdd')) { var cn = el.querySelector('#edCName').value, cf = el.querySelector('#edCFile').files[0];
        if (!cn) { toast('Choose the certificate'); return; } if (!cf) { toast('Attach the certificate document'); return; }
        collect(); draft.certsPending = (draft.certsPending || []).concat([{ name: cn, file: cf.name, at: Date.now() }]); draw(); toast(cn + ' sent for verification — it shows on your page once approved'); return; }
      var pe = e.target.closest('[data-pe]'); if (pe) { collect(); productForm(+pe.dataset.pe); return; }
      var pd = e.target.closest('[data-pd]'); if (pd) { collect(); draft.products.splice(+pd.dataset.pd, 1); draw(); return; }
      if (e.target.closest('#edSave')) {
        collect();
        var created = store('created_companies') || []; if (created.some(function (c) { return c.slug === draft.slug; })) { created = created.map(function (c) { return c.slug === draft.slug ? Object.assign({}, c, { tagline: draft.tagline, about: draft.about, founded: draft.founded, employees: draft.employees, phone: draft.phone, whatsapp: draft.whatsapp, email: draft.email, website: draft.website, address: draft.address, hours: draft.hours, services: draft.services, products: draft.products, color: draft.color, logo: draft.logo || null, cover: draft.cover || null, certsPending: draft.certsPending || [] }) : c; }); if (!store('created_companies', created)) { toast('Could not save — the photos are too large for this demo.'); return; } el.remove(); S.open = draft.slug; render(); drawSwitch(true); toast('Page saved'); return; }
        var edits = store('company_edits') || {}; edits[draft.slug] = { tagline: draft.tagline, about: draft.about, founded: draft.founded, employees: draft.employees, phone: draft.phone, whatsapp: draft.whatsapp, email: draft.email, website: draft.website, address: draft.address, hours: draft.hours, services: draft.services, products: draft.products, color: draft.color, logo: draft.logo || null, cover: draft.cover || null, certsPending: draft.certsPending || [] };
        if (!store('company_edits', edits)) { toast('Could not save — the photos are too large for this demo. Try smaller images.'); return; }
        el.remove(); S.open = draft.slug; render(); drawSwitch(true); toast('Company page published');
      }
    });
    el.addEventListener('change', function (e) {
      if (e.target.id === 'edLogo') readImage(e.target.files[0], 400, function (d) { if (d) { collect(); draft.logo = d; draw(); } });
      if (e.target.id === 'edCover') readImage(e.target.files[0], 1600, function (d) { if (d) { collect(); draft.cover = d; draw(); toast('Cover photo ready — save to publish'); } });
    });
    draw(); document.body.appendChild(el);
    /* closing (backdrop, ×, Cancel, Escape) asks first when something was changed and not saved */
    function snap() { collect(); var pn = el.querySelector('#edPName'); return JSON.stringify(draft) + (pn && pn.value.trim() !== pn.defaultValue.trim() ? '|' + pn.value : ''); }
    var start = snap();
    function askClose() {
      if (snap() === start) { el.remove(); return; }
      var q = D.modal({ title: 'Discard your changes?', body: '<p>Your edits to this page are not saved yet.</p>', secondary: 'Keep editing', primary: { label: 'Discard changes', danger: true, onClick: function () { el.remove(); } } });
      q.el.style.zIndex = 3200;   /* above the drawer */
    }
    function onKey(e) {
      if (!el.isConnected) { window.removeEventListener('keydown', onKey); return; }
      if (e.key === 'Escape' && window.dxTopDialog && window.dxTopDialog() === el) { e.preventDefault(); askClose(); }   /* only when no window is open on top of the drawer */
    }
    window.addEventListener('keydown', onKey);
  }

  /* clicks inside the directory are handled by the hub (hub-ui.js) */

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
