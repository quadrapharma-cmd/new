/* Structured trade offers (W-01 … W-07, W-09, W-13 … W-15, W-18; docs/areas/w-trade-design.md) — on the approved Marketplace:
   · Create Listing: new kinds on the approved type pills (available stock «متوفر», wanted «مطلوب», registration file «ملف تسجيل»,
     file wanted, company for sale, agency «وكالة», distributor, toll capacity «تول», factory wanted, raw materials), the
     stock-line fields in the approved Supply form, «الزق قايمتك» (a pasted WhatsApp list becomes items), price as a number,
     a discount % or «اطلب سعر», the file and toll fields, the private box (رقم الإخطار), the documents Drugbox checks, "Post as"
   · cards: the kind, the items, expiry / source / pack / fridge, discount, «اسأل عن السعر», reserved «محجوز», documents seen
     «مستندات اتشافت», the answer that fits the kind (request the file, apply for the agency, request the capacity)
   · My Listings: reserved / sold (with the buyer, who confirms and rates), renew once a week or feature it, matches, sales
   · search: each card carries its canonical words (dxTradeText) so Arabic ⇄ English, Arabic-Indic digits and forms match
   window.dxTradeSvc: this browser in the demo (sample data, DBK.store), the database in the live app (the adapter replaces it).
   Hooks for the trust session: every trade card has data-trade-kind / data-trade-poster / data-trade-company and calls
   window.dxTradeBadge(card, row); publishing awaits window.dxTradeGate(kind, { asCompany }) — both inert when not defined. */
(function () {
  var C = window.dxCore, D = window.DBK, TT = window.dxTradeText; if (!C || !D || !TT) return;
  var esc = D.esc, DAY = 864e5;
  function ar() { return document.documentElement.lang === 'ar'; }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function orig(el) { return el ? (window.dxOrigText ? window.dxOrigText(el) : el.textContent).replace(/\s+/g, ' ').trim() : ''; }
  function toast(m) { D.toast(m); }

  /* ── the kinds and their words (EN here; Arabic through dxI18nExtend at the end) ── */
  var KIND = {
    stock:        { em: '📦', side: 'supply', tile: 'supply', chip: 'Available', pill: '📦 Available stock', title: 'Available stock', sub: 'Stock lines between companies — one post, many items' },
    materials:    { em: '⚗️', side: 'supply', tile: 'supply', chip: 'Raw materials', pill: '⚗️ Raw materials', title: 'Raw materials & packaging', sub: 'APIs, excipients and packaging' },
    wanted:       { em: '🔍', side: 'demand', tile: 'demand', chip: 'Wanted', pill: '🔍 Wanted', title: 'Wanted item', sub: 'Tell suppliers exactly what you need' },
    file_sale:    { em: '📋', side: 'supply', tile: 'license', chip: 'Registration file', pill: '📋 Registration file', title: 'Registration file for sale', sub: 'A registration file and what comes with it' },
    file_wanted:  { em: '📋', side: 'demand', tile: 'demand', chip: 'File wanted', pill: '📋 File wanted', title: 'Registration file wanted', sub: 'The file you are looking for and your conditions' },
    company_sale: { em: '🏢', side: 'supply', tile: 'supply', chip: 'Company for sale', pill: '🏢 Company for sale', title: 'Company for sale', sub: 'A company with its licences and files' },
    agency:       { em: '🤝', side: 'supply', tile: 'supply', chip: 'Agency', pill: '🤝 Agency', title: 'Agency / distribution rights', sub: 'Your products, looking for a distributor or agent' },
    distributor:  { em: '🚚', side: 'demand', tile: 'demand', chip: 'Distributor', pill: '🚚 Distributor', title: 'Distributor seeking products', sub: 'Your coverage, looking for products to carry' },
    toll:         { em: '🏭', side: 'supply', tile: 'cmo', chip: 'Toll capacity', pill: '🏭 CMO', title: 'Toll manufacturing capacity', sub: 'Free capacity for manufacturing for others' },
    toll_wanted:  { em: '🏭', side: 'demand', tile: 'demand', chip: 'Factory wanted', pill: '🏭 Factory wanted', title: 'Factory wanted', sub: 'The product you need manufactured' }
  };
  var FORM_KIND = { 'form-demand': 'wanted', 'form-cmo': 'toll', 'form-license': 'file_sale' };       /* the approved forms; form-supply: stock or materials */
  var NEW_FORMS = ['file_wanted', 'company_sale', 'agency', 'distributor', 'toll_wanted'];
  var GOVS = [['Greater Cairo', ['cairo', 'giza', 'qalyubia']], ['Alexandria & coast', ['alex', 'beheira', 'matrouh']],
    ['Delta', ['sharqia', 'dakahlia', 'gharbia', 'monufia', 'kafr_el_sheikh', 'damietta']], ['Canal & Sinai', ['port_said', 'ismailia', 'suez', 'north_sinai', 'south_sinai']],
    ['Upper Egypt', ['faiyum', 'beni_suef', 'minya', 'asyut', 'sohag', 'qena', 'luxor', 'aswan']], ['Red Sea & desert', ['red_sea', 'new_valley']]];
  var GOV = { cairo: 'Cairo', giza: 'Giza', qalyubia: 'Qalyubia', alex: 'Alexandria', beheira: 'Beheira', matrouh: 'Matrouh', sharqia: 'Sharqia', dakahlia: 'Dakahlia', gharbia: 'Gharbia',
    monufia: 'Monufia', kafr_el_sheikh: 'Kafr El Sheikh', damietta: 'Damietta', port_said: 'Port Said', ismailia: 'Ismailia', suez: 'Suez', north_sinai: 'North Sinai', south_sinai: 'South Sinai',
    faiyum: 'Faiyum', beni_suef: 'Beni Suef', minya: 'Minya', asyut: 'Asyut', sohag: 'Sohag', qena: 'Qena', luxor: 'Luxor', aswan: 'Aswan', red_sea: 'Red Sea', new_valley: 'New Valley', all: 'All Egypt' };
  var CATS = [['medicines', 'Medicines'], ['supplements', 'Supplements'], ['cosmetics', 'Cosmetics'], ['devices', 'Medical devices'], ['veterinary', 'Veterinary'], ['herbal', 'Herbal'], ['baby', 'Baby care'], ['hospital', 'Hospital & tenders']];
  var FORMS_ = [['tab', 'Tablets'], ['cap', 'Capsules'], ['syrup', 'Syrup'], ['susp', 'Suspension'], ['amp', 'Ampoules'], ['vial', 'Vials'], ['supp', 'Suppositories'], ['cream', 'Cream'],
    ['oint', 'Ointment'], ['gel', 'Gel'], ['drops', 'Drops'], ['spray', 'Spray'], ['sachet', 'Sachets'], ['eff', 'Effervescent'], ['powder', 'Powder'], ['lotion', 'Lotion'], ['solution', 'Solution']];
  var PACKS = [['blister', 'Blister'], ['strip', 'Strip'], ['bottle', 'Bottle'], ['tube', 'Tube'], ['sachet', 'Sachet'], ['vial', 'Vial'], ['amp', 'Ampoule'], ['jar', 'Jar']];
  var UNITS = [['box', 'box'], ['strip', 'strip'], ['carton', 'carton'], ['pack', 'pack'], ['piece', 'piece'], ['bottle', 'bottle'], ['tube', 'tube'], ['vial', 'vial'], ['amp', 'ampoule'], ['kg', 'kg'], ['g', 'g'], ['l', 'litre'], ['ton', 'ton'], ['drum', 'drum'], ['bag', 'bag']];
  var SOURCES = [['company', 'Company'], ['factory', 'Factory'], ['authority', 'Authority (tender)'], ['importer', 'Importer']];
  var PACKST = [['intact', 'Sealed / intact'], ['opened', 'Opened carton'], ['damaged', 'Damaged pack'], ['repacked', 'Repacked']];
  var COUNTRIES = [['EG', 'Egypt'], ['IN', 'India'], ['CN', 'China'], ['DE', 'Germany'], ['FR', 'France'], ['IT', 'Italy'], ['ES', 'Spain'], ['GB', 'United Kingdom'], ['CH', 'Switzerland'],
    ['US', 'United States'], ['TR', 'Türkiye'], ['JO', 'Jordan'], ['SA', 'Saudi Arabia'], ['AE', 'UAE'], ['KR', 'Korea'], ['JP', 'Japan']];
  var CUR = [['EGP', 'EGP'], ['USD', 'US$'], ['EUR', '€'], ['SAR', 'SAR'], ['AED', 'AED']];
  var STAGES = [['submitted', 'Submitted'], ['pricing', 'Pricing'], ['committee', 'Technical committee'], ['analysis', 'Analysis'], ['notification', 'Notification issued'], ['final', 'Final registration']];
  var AUTH = [['eda', 'EDA (Egypt)'], ['sfda', 'SFDA (Saudi)'], ['dha', 'DHA (Dubai)'], ['mohap', 'MOHAP (UAE)'], ['jfda', 'JFDA (Jordan)'], ['other', 'Other']];
  var REGT = [['human', 'Human medicine'], ['supplement', 'Food supplement'], ['cosmetic', 'Cosmetic'], ['device', 'Medical device'], ['vet', 'Veterinary']];
  var INCL = [['brand', 'Brand name'], ['dossier', 'Dossier'], ['studies', 'Studies (stability / BE)'], ['artwork', 'Artwork'], ['stock', 'Stock'], ['trademark', 'Trademark'], ['manufacturing', 'Manufacturing rights']];
  var BCOND = [['own_factory', 'Buyer has a factory'], ['toll_ok', 'Toll manufacturing accepted'], ['licensed_warehouse', 'Licensed warehouse'], ['company_only', 'Companies only']];
  var CTYPES = [['manufacturer', 'Manufacturer'], ['distributor', 'Distributor / warehouse'], ['importer', 'Importer'], ['scientific_office', 'Scientific office'], ['warehouse', 'Licensed warehouse'], ['cosmetics', 'Cosmetics'], ['other', 'Other']];
  var LBL = {}; [CTYPES, GOVS.reduce(function (a, g) { g[1].forEach(function (k) { a.push([k, GOV[k]]); }); return a; }, []), CATS, FORMS_, PACKS, UNITS, SOURCES, PACKST, COUNTRIES, STAGES, AUTH, REGT, INCL, BCOND]
    .forEach(function (l) { l.forEach(function (x) { if (!(x[0] in LBL)) LBL[x[0]] = x[1]; }); });
  function lbl(k) { return LBL[k] || k; }
  function opts(list, blank) { return (blank ? '<option value="">' + esc(blank) + '</option>' : '') + list.map(function (x) { return '<option value="' + esc(x[0]) + '">' + esc(x[1]) + '</option>'; }).join(''); }
  function months(n) { var out = [], d = new Date(); d.setDate(1); for (var i = 0; i < n; i++) { out.push(d.toISOString().slice(0, 7)); d.setMonth(d.getMonth() + 1); } return out; }

  /* ── field builders: the approved form markup (.field / .field-label / .field-input / .chip-row / .radio-row) ── */
  function req(r) { return r ? ' <span class="req">*</span>' : ''; }
  function F(key, label, inner, r, hint) { return '<div class="field" data-tx="' + key + '"><label class="field-label">' + esc(label) + req(r) + '</label>' + inner + (hint ? '<div class="field-hint">' + esc(hint) + '</div>' : '') + '</div>'; }
  function fText(key, label, ph, r, hint, type) { return F(key, label, '<input class="field-input" ' + (type ? 'type="' + type + '" ' : '') + 'placeholder="' + esc(ph || '') + '" maxlength="120">', r, hint); }
  function fSel(key, label, list, r, blank) { return F(key, label, '<select class="field-select">' + opts(list, blank === undefined ? '—' : blank) + '</select>', r); }
  function fChips(key, label, list, r, hint) { return F(key, label, '<div class="chip-row">' + list.map(function (x) { return '<div class="chip" data-v="' + esc(x[0]) + '" role="button" tabindex="0">' + esc(x[1]) + '</div>'; }).join('') + '</div>', r, hint); }
  function fRadio(key, label, list, r, sel) { return F(key, label, '<div class="radio-row">' + list.map(function (x, i) { return '<div class="radio-opt' + ((sel == null ? i === -1 : x[0] === sel) ? ' selected' : '') + '" data-v="' + esc(x[0]) + '" role="button" tabindex="0">' + esc(x[1]) + '</div>'; }).join('') + '</div>', r); }
  function fYesNo(key, label, r) { return fRadio(key, label, [['yes', 'Yes'], ['no', 'No']], r); }
  function fMonth(key, label, r, hint) { return fText(key, label, 'YYYY-MM', r, hint, 'month'); }
  function fGov(key, label, r) {   /* the governorates of Egypt by region — a tap map */
    return F(key, label, '<div class="dx-gov">' + '<div class="chip-row"><div class="chip" data-v="all" role="button" tabindex="0">🇪🇬 All Egypt</div></div>' +
      GOVS.map(function (g) { return '<div class="dx-gov-r"><small>' + esc(g[0]) + '</small><div class="chip-row">' + g[1].map(function (k) { return '<div class="chip" data-v="' + k + '" role="button" tabindex="0">' + esc(GOV[k]) + '</div>'; }).join('') + '</div></div>'; }).join('') + '</div>', r);
  }
  function row2(a, b) { return '<div class="row2">' + a + b + '</div>'; }
  function row3(a, b, c) { return '<div class="row3">' + a + b + c + '</div>'; }
  function common(withGov) {
    return (withGov ? row2(fSel('gov', 'Governorate', GOVS.reduce(function (a, g) { return a.concat(g[1].map(function (k) { return [k, GOV[k]]; })); }, [])), fSel('delivery', 'Delivery', [['seller', 'Pick-up from the seller'], ['buyer', 'Delivered to the buyer'], ['shipping', 'Shipping'], ['agreement', 'By agreement']])) : '');
  }
  function priceBlock(withCur) {
    return F('price_mode', 'Price', '<div class="radio-row"><div class="radio-opt selected" data-v="amount" role="button" tabindex="0">Price</div><div class="radio-opt" data-v="discount" role="button" tabindex="0">Discount %</div><div class="radio-opt" data-v="ask" role="button" tabindex="0">Ask for price</div></div>' +
      '<div class="row2 dx-pm-x"><input class="field-input dx-disc" type="number" min="1" max="95" step="0.5" placeholder="Discount % off the public price" style="display:none">' + (withCur ? '<select class="field-select dx-cur">' + opts(CUR) + '</select>' : '') + '</div>', false,
      'Ask for price: buyers send a price request tied to this listing') +
      row2(fText('credit_days', 'Credit terms (days) — آجل', 'e.g. 60 (empty = cash)', false, '', 'number'), F('urgent', 'Urgent', '<div class="chip-row"><div class="chip" data-v="1" role="button" tabindex="0">⏱ Urgent</div></div>'));
  }
  function postAs() { return '<div class="field dx-postas" data-tx="_as"><label class="field-label">Post as</label><select class="field-select"></select><div class="field-hint">A company page posts offers as the company only with the Drugbox verification badge</div></div>'; }
  function privBox(hint) { return '<div class="dx-priv"><div class="field-label">🔒 Private box — only you, Drugbox and the members you share it with</div>' +
    row2(fText('priv.notif_no', 'Notification number (رقم الإخطار)', 'e.g. 12345/2024'), fText('priv.reg_no', 'Registration / licence number', '')) + (hint ? '<div class="field-hint">' + esc(hint) + '</div>' : '') + '</div>'; }
  function docsZone(label) { return '<div class="field dx-docs-f"><label class="field-label">' + esc(label) + '</label><div class="upload-zone-sm dx-docs" role="button" tabindex="0"><b>Upload</b> documents for Drugbox to check (PDF / photo, up to 6)</div><div class="field-hint">Private: Drugbox checks them and the card shows “Documents seen by Drugbox”</div></div>'; }
  var DISCLAIMER = 'Drugbox saw the documents; it does not guarantee the transfer — moving a registration needs the authority’s approval.';

  /* the extra fields inside the approved forms */
  var EXTRA = {
    'form-supply': function () {
      return '<div class="dx-tx" data-tx-extra="supply">' +
        '<div class="dx-stock"><div class="field"><label class="field-label">Items <span class="req">*</span></label><div class="dx-lines"></div>' +
        '<div class="dx-lines-a"><button type="button" class="dx-tbtn s" data-tx-a="addline">＋ Add another item</button><button type="button" class="dx-tbtn s" data-tx-a="paste">📋 Paste your list</button></div>' +
        '<div class="field-hint">Name (Arabic and English), strength, quantity + unit, expiry, source, pack, fridge — one line per item</div></div></div>' +
        common(true) + priceBlock(true) + postAs() + '</div>';
    },
    'form-demand': function () { return '<div class="dx-tx" data-tx-extra="wanted">' + row2(fText('strength', 'Strength', 'e.g. 500 mg'), fSel('form', 'Dosage form', FORMS_)) +
      row2(fMonth('needed_by', 'Needed by'), fSel('gov', 'Governorate', GOVS.reduce(function (a, g) { return a.concat(g[1].map(function (k) { return [k, GOV[k]]; })); }, []))) + postAs() + '</div>'; },
    'form-cmo': function () { return '<div class="dx-tx" data-tx-extra="toll">' +
      fChips('forms', 'Dosage forms you make', FORMS_, true) + fChips('packs', 'Pack types', PACKS) +
      row2(fText('min_batch', 'Minimum batch', 'e.g. 200,000 tablets', true), fText('lead_time', 'Lead time', 'e.g. 6–8 weeks', true)) +
      F('free_months', 'Free months', '<div class="chip-row">' + months(12).map(function (m) { return '<div class="chip" data-v="' + m + '" role="button" tabindex="0">' + m + '</div>'; }).join('') + '</div>') +
      row2(fYesNo('licensed', 'Licensed by the authority'), fYesNo('reg_contract', 'Contract manufacturing for registration')) +
      fRadio('gmp', 'GMP', [['yes', 'Yes'], ['no', 'No GMP']], true) + row2(fText('gmp_by', 'GMP issued by', 'e.g. EDA / WHO'), fMonth('gmp_date', 'GMP date')) +
      common(true) + postAs() + '</div>'; },
    'form-license': function () { return '<div class="dx-tx" data-tx-extra="file_sale">' +
      row2(fSel('reg_type', 'Registration type', REGT, true), fSel('stage', 'Stage', STAGES, true)) + fChips('stages_done', 'Steps done (checklist)', STAGES) +
      row2(fText('form', 'Dosage form', 'e.g. Tablets'), fText('strength', 'Strength', 'e.g. 500 mg')) +
      row2(fYesNo('decision', 'Registration decision issued'), fMonth('notif_valid_until', 'Notification valid until')) +
      row3(fText('public_price', 'Public price per pack', 'e.g. 85', false, '', 'number'), fText('pack', 'Pack', 'e.g. 20 tablets'), fRadio('price_increase', 'Price increase', [['none', 'None'], ['submitted', 'Submitted'], ['approved', 'Approved']])) +
      row3(fText('asking_price', 'Asking price', 'e.g. EGP 400,000'), fText('commission', 'Commission', 'e.g. 2%'), fText('sales_units', 'Sales per year (units)', '', false, '', 'number')) +
      fChips('buyer_conditions', 'Buyer conditions', BCOND) + row2(fText('factory', 'Factory', 'Who manufactures it'), fMonth('reg_expiry', 'Registration valid until')) +
      privBox('The notification number stays here; share it with a serious buyer from My Listings') + docsZone('Documents for Drugbox (registration, notification)') +
      '<div class="dbk-note dx-disc-note">' + esc(DISCLAIMER) + '</div>' + postAs() + '</div>'; }
  };
  /* the new forms, in the approved wizard markup */
  var NEWF = {
    file_wanted: function () { return fText('_title', 'Registration file you are looking for', 'e.g. Paracetamol 500 mg tablets — EDA', true) + row2(fSel('authority', 'Authority', AUTH), fSel('reg_type', 'Registration type', REGT, true)) +
      row2(fText('form', 'Dosage form', 'e.g. Tablets'), fSel('stage', 'Earliest stage you accept', [['any', 'Any stage']].concat(STAGES))) + row2(fText('budget', 'Budget', 'e.g. up to EGP 500,000'), fSel('gov', 'Governorate', govList())) +
      F('conditions', 'Your conditions', '<textarea class="field-textarea" maxlength="200" placeholder="e.g. with stability studies, transfer within 6 months"></textarea>'); },
    company_sale: function () { return fText('_title', 'Company', 'e.g. Scientific office with 12 registered files', true) + row2(fSel('company_type', 'Company type', [['manufacturer', 'Manufacturer'], ['distributor', 'Distributor / warehouse'], ['importer', 'Importer'], ['scientific_office', 'Scientific office'], ['warehouse', 'Licensed warehouse'], ['cosmetics', 'Cosmetics'], ['other', 'Other']], true), fYesNo('licensed', 'Licensed')) +
      row3(fText('files_count', 'Registered files', '', false, '', 'number'), fText('asking_price', 'Asking price', 'e.g. EGP 3,000,000'), fSel('gov', 'Governorate', govList())) +
      F('reason', 'Why it is for sale (optional)', '<textarea class="field-textarea" maxlength="200"></textarea>') + docsZone('Documents for Drugbox (commercial registry, licences)'); },
    agency: function () { return fText('_title', 'Products / brand', 'e.g. Our vitamin range (12 products)', true) + fChips('cats', 'Categories', CATS, true) + fGov('govs', 'Governorates (map)', true) +
      row3(fYesNo('exclusive', 'Exclusive'), fText('contract_years', 'Contract (years)', '', false, '', 'number'), fText('bonus_pct', 'Bonus %', 'e.g. 7', false, '', 'number')) +
      row2(fText('target', 'Target', 'e.g. EGP 2 M / year'), fText('credit_days', 'Credit terms (days) — آجل', 'e.g. 90', false, '', 'number')) + docsZone('Documents for Drugbox (registrations, authorisation)'); },
    distributor: function () { return fText('_title', 'What you are looking for', 'e.g. Distributor in Upper Egypt looking for supplements', true) + fChips('cats', 'Categories you carry', CATS, true) + fGov('govs', 'Governorates you cover (map)', true) +
      row3(fText('warehouses', 'Warehouses', '', false, '', 'number'), fText('fleet', 'Vehicles', '', false, '', 'number'), fText('agencies', 'Agencies you hold', '', false, '', 'number')) +
      row2(fYesNo('cold_chain', 'Cold chain'), fText('reach', 'Reach', 'e.g. 1,200 accounts in 6 governorates')); },
    toll_wanted: function () { return fText('_title', 'Product to manufacture', 'e.g. Ibuprofen 400 mg tablets', true) + fChips('forms', 'Dosage forms', FORMS_, true) + fChips('packs', 'Pack types', PACKS) +
      row3(fText('batch', 'Batch size', 'e.g. 100,000 tablets'), fMonth('by_when', 'Needed by'), fYesNo('reg_contract', 'Contract for registration')) + fSel('gov', 'Governorate', govList()); }
  };
  function govList() { return GOVS.reduce(function (a, g) { return a.concat(g[1].map(function (k) { return [k, GOV[k]]; })); }, []); }

  /* ── one stock line (W-01) ── */
  function lineHtml(l) {
    l = l || {};
    return '<div class="dx-line">' +
      '<div class="dx-line-h"><b>Item</b><button type="button" class="dx-line-x" data-tx-a="delline" aria-label="Remove item">✕</button></div>' +
      '<div class="row2"><input class="field-input" data-l="name" placeholder="Name (English or Arabic) *" maxlength="160" value="' + esc(l.name || '') + '"><input class="field-input" data-l="name_ar" placeholder="الاسم بالعربي" maxlength="160" dir="auto" value="' + esc(l.name_ar || '') + '"></div>' +
      '<div class="row3"><input class="field-input" data-l="strength" placeholder="Strength (500 mg)" maxlength="40" value="' + esc(l.strength || '') + '"><select class="field-select" data-l="form">' + opts(FORMS_, 'Dosage form') + '</select>' +
      '<input class="field-input" data-l="expiry" type="month" title="Expiry" aria-label="Expiry" value="' + esc(l.expiry || '') + '"></div>' +
      '<div class="row3"><input class="field-input" data-l="qty" type="number" min="1" step="any" placeholder="Quantity *" value="' + esc(l.qty || '') + '"><select class="field-select" data-l="unit">' + opts(UNITS) + '</select>' +
      '<input class="field-input" data-l="price" type="number" min="0" step="any" placeholder="Price (optional)" value="' + esc(l.price || '') + '"></div>' +
      '<div class="row3"><select class="field-select" data-l="source">' + opts(SOURCES, 'Source') + '</select><select class="field-select" data-l="origin_country">' + opts(COUNTRIES, 'Country') + '</select>' +
      '<select class="field-select" data-l="pack_state">' + opts(PACKST, 'Pack condition') + '</select></div>' +
      '<div class="dx-line-f"><label class="dx-chk"><input type="checkbox" data-l="cold"' + (l.cold ? ' checked' : '') + '> ❄️ Fridge item</label><input class="field-input dx-ldisc" data-l="discount_pct" type="number" min="1" max="95" step="0.5" placeholder="Discount %" value="' + esc(l.discount_pct || '') + '"></div></div>';
  }
  function setLine(row, l) { ['form', 'unit', 'source', 'origin_country', 'pack_state'].forEach(function (k) { var s = row.querySelector('[data-l="' + k + '"]'); if (s && l[k]) s.value = l[k]; }); }
  function addLine(form, l) { var box = form.querySelector('.dx-lines'); if (!box) return; var w = document.createElement('div'); w.innerHTML = lineHtml(l); var r = w.firstElementChild; box.appendChild(r); if (l) setLine(r, l); return r; }
  function readLines(form) {
    var out = [];
    form.querySelectorAll('.dx-line').forEach(function (r, i) { var o = { pos: i }; r.querySelectorAll('[data-l]').forEach(function (e) { var k = e.dataset.l, v = e.type === 'checkbox' ? e.checked : e.value.trim();
      if (v === '' || v == null) return; if (k === 'qty' || k === 'price' || k === 'discount_pct') v = +v; o[k] = v; });
      if (o.name || o.name_ar) { if (!o.name) o.name = o.name_ar; out.push(o); } });
    return out;
  }

  /* ── «الزق قايمتك»: a list copied from a chat becomes items (W-14) ── */
  var HEADER = /^\s*\[?\s*\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?|ص|م)?\s*\]?\s*(?:-\s*)?[^:\n]{1,60}?:\s*/;
  var UNIT_W = { box: 'box', strip: 'strip', carton: 'carton', pack: 'pack', piece: 'piece', bottle: 'bottle', tube: 'tube', kg: 'kg', ton: 'ton', drum: 'drum', bag: 'bag', amp: 'amp', vial: 'vial' };
  function digits(s) { return String(s).replace(/[٠-٩]/g, function (c) { return '٠١٢٣٤٥٦٧٨٩'.indexOf(c); }).replace(/[۰-۹]/g, function (c) { return '۰۱۲۳۴۵۶۷۸۹'.indexOf(c); }).replace(/٫/g, '.').replace(/٪/g, '%'); }
  function parseList(text) {
    var out = [];
    String(text || '').split(/\r?\n/).forEach(function (raw) {
      var s = digits(raw).replace(HEADER, '').replace(/[‎‏‪-‮]/g, '');
      s = s.replace(/^[\s\-–—•*·▪●○◦►▶✅✔☑🔹🔸🔻➖➡️👈👉📌⭐🌟🔥💊]+/u, '').replace(/^\s*\d{1,3}\s*[-).]\s+/, '').trim();
      if (!/[A-Za-zء-ي]/.test(s) || s.length < 2) return;
      var n = TT.norm(s); if (/^(متوفر|مطلوب|عندي|available|wanted|السلام عليكم|صباح الخير|مساء الخير|للتواصل|للاستفسار)( |$)/.test(n) && s.length < 25) return;
      var l = {}, rest = s, m;
      if ((m = /(?:\b(?:exp|ex|expiry)\b|انتهاء|تاريخ|صلاحي[هة])?\s*[:\-]?\s*\b(0?[1-9]|1[0-2])\s*[\/\-.]\s*(20\d{2}|\d{2})\b/i.exec(rest))) {
        var y = m[2].length === 2 ? 2000 + +m[2] : +m[2]; if (y >= 2020 && y <= 2045) { l.expiry = y + '-' + ('0' + m[1]).slice(-2); rest = rest.replace(m[0], ' '); } }
      if ((m = /(?:خصم|discount|off)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\s*%?|(\d{1,2}(?:\.\d+)?)\s*%\s*(?:خصم|off|discount)?/i.exec(rest))) { var dp = +(m[1] || m[2]); if (dp > 0 && dp <= 95) l.discount_pct = dp; rest = rest.replace(m[0], ' '); }
      if ((m = /(?:بسعر|سعر|price)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:ج\.?م?|جنيه|egp|le|l\.e)?/i.exec(rest))) { l.price = +m[1]; rest = rest.replace(m[0], ' '); }
      if ((m = /(\d+(?:\.\d+)?)\s*(mg|mcg|g|gm|ml|iu|مجم|ملجم|مللجم|ميكروجرام|جم|جرام|مل|ملل)(?![A-Za-zء-ي])/i.exec(rest))) { l.strength = m[1] + ' ' + m[2]; rest = rest.replace(m[0], ' '); }
      var qtyRx = /(\d+(?:[.,]\d+)?)\s*(علب[هة]?|علب|box(?:es)?|شريط|شرايط|strips?|كرتون[هة]|كراتين|cartons?|عبو[هة]|عبوات|packs?|pcs|قطع[هة]|زجاج[هة]|bottles?|كيلو|kg|طن|tons?|امبول|أمبول|amps?|فيال|vials?|انبوب[هة]|tubes?)/i;
      if ((m = qtyRx.exec(rest))) { l.qty = +m[1].replace(',', '.'); var tk = TT.tokens(m[2])[0]; l.unit = UNIT_W[tk] || (/كيلو|kg/i.test(m[2]) ? 'kg' : 'box'); rest = rest.replace(m[0], ' '); }
      else if ((m = /(?:عدد|كمي[هة]|qty|quantity|×|x)\s*[:\-]?\s*(\d+(?:[.,]\d+)?)/i.exec(rest))) { l.qty = +m[1].replace(',', '.'); l.unit = 'box'; rest = rest.replace(m[0], ' '); }
      if (/ثلاج[هة]|تلاج[هة]|fridge|\bcold\b/i.test(rest)) { l.cold = true; rest = rest.replace(/ثلاج[هة]|تلاج[هة]|fridge|\bcold\b/ig, ' '); }
      if (/مستورد|imported/i.test(rest)) { l.source = 'importer'; rest = rest.replace(/مستورد|imported/ig, ' '); }
      else if (/هيئ[هة]|مناقص[هة]/i.test(rest)) { l.source = 'authority'; rest = rest.replace(/هيئ[هة]|مناقص[هة]/ig, ' '); }
      else if (/فابريك[هة]|\bfactory\b/i.test(rest)) { l.source = 'factory'; rest = rest.replace(/فابريك[هة]|\bfactory\b/ig, ' '); }
      if (/مفتوح|opened/i.test(rest)) { l.pack_state = 'opened'; rest = rest.replace(/مفتوح[هة]?|opened/ig, ' '); }
      else if (/تالف|damaged/i.test(rest)) { l.pack_state = 'damaged'; rest = rest.replace(/تالف[هة]?|damaged/ig, ' '); }
      var fw = rest.split(/\s+/).filter(function (w) { return TT.kind(TT.tokens(w)[0]) === 'form'; })[0]; if (fw) l.form = TT.tokens(fw)[0];
      rest = rest.replace(/\b(متوفر|متاح|available)\b/ig, ' ').replace(/[|،,:;\-–—_*•]+/g, ' ').replace(/\s+/g, ' ').trim();
      if (!/[A-Za-zء-ي]/.test(rest)) return;
      if (/[ء-ي]/.test(rest) && !/[A-Za-z]/.test(rest)) { l.name_ar = rest.slice(0, 160); l.name = rest.slice(0, 160); } else l.name = rest.slice(0, 160);
      if (!l.unit && l.qty) l.unit = 'box';
      out.push(l);
    });
    return out.slice(0, 300);
  }
  function pasteDialog(form) {
    var m = D.modal({ title: '📋 Paste your list', body: '<p class="cp-muted">Copy the list from WhatsApp or a sheet and paste it here — one item per line. Chat headers (date, name) are removed. Check the items before adding them.</p>' +
      '<div class="dbk-f"><label for="dxPaste">Your list</label><textarea id="dxPaste" rows="8" dir="auto" placeholder="بانادول اكسترا 20 علبة exp 5/26 خصم 30%&#10;Concor 5mg 10 box"></textarea></div><div class="dx-paste-out"></div>',
      secondary: 'Cancel', primary: { label: 'Read the list', onClick: function (b) {
        var out = b.querySelector('.dx-paste-out'), rows = parseList(b.querySelector('#dxPaste').value);
        if (out.dataset.read !== '1') {
          if (!rows.length) { toast('No items found — one item per line, with its name'); return false; }
          out.dataset.read = '1'; out.__rows = rows;
          out.innerHTML = '<div class="dbk-note">' + rows.length + (rows.length === 1 ? ' item' : ' items') + ' found — untick any line that is not an item</div>' + rows.map(function (r, i) {
            return '<label class="dx-paste-r"><input type="checkbox" checked data-pr="' + i + '"> <span data-noi18n>' + esc([r.name, r.strength, r.qty ? r.qty + ' ' + (r.unit || '') : '', r.expiry ? 'exp ' + r.expiry : '', r.discount_pct ? r.discount_pct + '%' : '', r.cold ? '❄️' : ''].filter(Boolean).join(' · ')) + '</span></label>'; }).join('');
          var ok = b.parentNode.querySelector('[data-a=ok]'); if (ok) ok.textContent = 'Add the items'; return false;
        }
        var keep = out.__rows.filter(function (r, i) { var c = out.querySelector('[data-pr="' + i + '"]'); return c && c.checked; });
        var box = form.querySelector('.dx-lines'); if (box) box.querySelectorAll('.dx-line').forEach(function (r) { if (!r.querySelector('[data-l="name"]').value.trim() && !r.querySelector('[data-l="name_ar"]').value.trim()) r.remove(); });
        keep.forEach(function (r) { addLine(form, r); }); toast(keep.length + (keep.length === 1 ? ' item added' : ' items added') + ' — add quantities where missing');
      } } });
    return m;
  }

  /* ── reading a form ── */
  function readTx(form) {
    var a = {}, priv = {};
    form.querySelectorAll('[data-tx]').forEach(function (fd) {
      var k = fd.dataset.tx, v; if (k === '_as' || k === '_mode' || k === 'price_mode') return;
      var chips = fd.querySelectorAll('.chip[data-v]'), radios = fd.querySelectorAll('.radio-opt[data-v]'), inp = fd.querySelector('input.field-input, select.field-select, textarea');
      if (fd.querySelector('.dx-gov') || (chips.length && !(k === 'urgent'))) { v = [].map.call(fd.querySelectorAll('.chip.selected[data-v]'), function (c) { return c.dataset.v; }); if (!v.length) v = undefined; }
      else if (k === 'urgent') v = !!fd.querySelector('.chip.selected');
      else if (radios.length) { var r = fd.querySelector('.radio-opt.selected[data-v]'); v = r ? r.dataset.v : undefined; if (v === 'yes' || v === 'no') { if (k !== 'gmp' && k !== 'decision') v = v === 'yes'; } }
      else if (inp) { v = inp.value.trim(); if (v === '') v = undefined; else if (inp.type === 'number') v = +v; }
      if (v === undefined) return;
      if (k.indexOf('priv.') === 0) priv[k.slice(5)] = v; else a[k] = v;
    });
    var cur = form.querySelector('.dx-cur'); if (cur && cur.value) a.currency = cur.value;
    return { attrs: a, priv: priv };
  }
  function kindOf(form) {
    if (!form) return null; if (form.dataset.txKind) return form.dataset.txKind;
    if (form.id === 'form-supply') { var m = form.querySelector('[data-tx="_mode"] .radio-opt.selected'); return m ? m.dataset.v : 'stock'; }
    return FORM_KIND[form.id] || null;
  }
  function priceMode(form) { var r = form.querySelector('[data-tx="price_mode"] .radio-opt.selected'); return r ? r.dataset.v : null; }
  /* the approved chips of the CMO / License forms, read as the fields they mean */
  var APPROVED_FORMS = { Tablets: ['tab'], Capsules: ['cap'], Liquids: ['syrup', 'susp'], 'Creams/Ointments': ['cream', 'oint'], Injectables: ['amp', 'vial'] };
  var APPROVED_INCL = { 'Brand name rights': 'brand', 'Formula/dossier': 'dossier', 'Manufacturing rights': 'manufacturing', Trademark: 'trademark' };
  var APPROVED_AUTH = { 'EDA (Egypt)': 'eda', 'SFDA (Saudi)': 'sfda', 'DHA (Dubai)': 'dha', 'MOHAP (UAE)': 'mohap' };
  function gather(form) {
    var kind = kindOf(form), r = readTx(form), a = r.attrs;
    if (form.id === 'form-cmo') { var f = a.forms || []; form.querySelectorAll('.field').forEach(function (fd) { if (/Dosage forms produced/.test(orig(fd.querySelector('.field-label')))) fd.querySelectorAll('.chip.selected').forEach(function (c) { (APPROVED_FORMS[orig(c)] || []).forEach(function (x) { if (f.indexOf(x) < 0) f.push(x); }); }); }); if (f.length) a.forms = f; }
    if (form.id === 'form-license') { var inc = []; form.querySelectorAll('.chip.selected').forEach(function (c) { var k = APPROVED_INCL[orig(c)]; if (k) inc.push(k); }); if (inc.length) a.included = inc;
      form.querySelectorAll('.field').forEach(function (fd) { if (/Registering authority/.test(orig(fd.querySelector('.field-label')))) { var s = fd.querySelector('select'); var o = s && s.selectedOptions[0]; var k = o && APPROVED_AUTH[o.value || orig(o)]; if (k) a.authority = k; } }); }
    if (form.id === 'form-supply' && kind === 'materials') { delete a.gov; }
    var first = form.querySelector('.field-input'), title = (a._title || (first ? first.value.trim() : '')).slice(0, 200); delete a._title;
    var desc = (form.querySelector('textarea.field-textarea:not([data-l])') || {}).value || '';
    var pm = priceMode(form), disc = form.querySelector('.dx-disc'), ap = '', amoq = '';
    form.querySelectorAll('.wizard-body > .field, .wizard-body > .row2 > .field, .wizard-body > .row3 > .field').forEach(function (fd) { var l = orig(fd.querySelector('.field-label')), i = fd.querySelector('input.field-input');   /* the approved price / quantity fields */
      if (!i || !i.value.trim()) return; if (!ap && /^(Price per unit|Asking price|Target price)/.test(l)) ap = i.value.trim(); if (!amoq && /^(MOQ|Quantity needed|Min\. batch)/.test(l)) amoq = i.value.trim(); });
    var as = form.querySelector('[data-tx="_as"] select');
    var lines = kind === 'stock' ? readLines(form) : [];
    if (kind === 'stock' && pm === 'amount' && !ap && !lines.some(function (l) { return l.price; })) pm = 'ask';   /* no price anywhere: «اطلب سعر», said plainly */
    return { kind: kind, title: title, attrs: a, priv: r.priv, lines: lines, price_mode: pm === 'amount' ? null : pm,
      discount_pct: pm === 'discount' && disc && disc.value ? +disc.value : null, price: pm === 'ask' ? '' : ap, moq: amoq, as: as && as.value ? as.value : '', desc: desc.trim(), docs: (DOCS[form.id] || []).slice() };
  }
  function missing(form, g) {
    var miss = [];
    form.querySelectorAll('[data-tx]').forEach(function (fd) { if (!fd.querySelector(':scope > .field-label .req')) return; var k = fd.dataset.tx;
      if (k === '_mode' || k === '_title') return;
      var has = k in g.attrs || (k === 'forms' && g.attrs.forms && g.attrs.forms.length); if (!has) miss.push(orig(fd.querySelector('.field-label')).replace('*', '').trim()); });
    if (g.kind === 'stock') { if (!g.lines.length) miss.push('Items'); else if (g.lines.some(function (l) { return !(l.qty > 0); })) miss.push('Quantity of every item'); }
    if (g.kind === 'toll' && g.attrs.gmp === 'yes' && (!g.attrs.gmp_by || !g.attrs.gmp_date)) miss.push('GMP issued by and date');
    if (g.price_mode === 'discount' && !(g.discount_pct > 0 && g.discount_pct <= 95)) miss.push('Discount %');
    if (!g.title) miss.push('Name');
    return miss;
  }

  /* ── the demo's service (sample data in this browser); the live adapter replaces window.dxTradeSvc ── */
  var ME_ID = 1;
  function seed() {
    var t = Date.now();
    return [
      { id: 'T1', kind: 'stock', uid: 3, title: 'Cairo warehouse — available stock', co: { name: 'Pharaonic Cold-Chain Logistics', slug: 'pharaonic-logistics', verified: true }, status: 'active', at: t - 2 * DAY,
        attrs: { gov: 'cairo', delivery: 'seller', credit_days: 60, currency: 'EGP' }, price_mode: 'discount', discount_pct: 28,
        lines: [{ name: 'Panadol Extra', name_ar: 'بنادول اكسترا', strength: '500 mg', form: 'tab', qty: 120, unit: 'box', expiry: '2027-03', source: 'company', origin_country: 'EG', pack_state: 'intact' },
          { name: 'Concor 5 mg', name_ar: 'كونكور', strength: '5 mg', form: 'tab', qty: 40, unit: 'box', expiry: '2026-11', source: 'importer', origin_country: 'DE', pack_state: 'intact' },
          { name: 'Insulin pen', name_ar: 'انسولين', strength: '100 iu', form: 'vial', qty: 25, unit: 'pack', expiry: '2026-06', source: 'company', origin_country: 'DK', pack_state: 'intact', cold: true }] },
      { id: 'T2', kind: 'wanted', uid: 4, title: 'Augmentin 1 g tablets — 300 boxes', status: 'active', at: t - 1 * DAY, attrs: { qty: '300 box', gov: 'giza', needed_by: months(2)[1], form: 'tab', strength: '1 g' }, lines: [] },
      { id: 'T3', kind: 'file_sale', uid: 2, title: 'Paracetamol 500 mg tablets — EDA file', status: 'active', at: t - 5 * DAY, docs: 'seen', docsAt: t - 3 * DAY,
        attrs: { authority: 'eda', reg_type: 'human', stage: 'notification', stages_done: ['submitted', 'pricing', 'committee', 'analysis', 'notification'], form: 'Tablets', strength: '500 mg', decision: 'yes',
          notif_valid_until: months(18)[17], public_price: 34, pack: '20 tablets', price_increase: 'submitted', asking_price: 'EGP 450,000', commission: '2%', included: ['brand', 'dossier', 'studies'], buyer_conditions: ['toll_ok'] },
        priv: { notif_no: '7781/2025' }, lines: [] },
      { id: 'T4', kind: 'toll', uid: 5, title: 'Tablet & capsule lines — free capacity', co: { name: 'Medsinia Industries', slug: 'medsinia-industries', verified: true }, status: 'active', at: t - 3 * DAY,
        attrs: { forms: ['tab', 'cap', 'sachet'], packs: ['blister', 'sachet'], min_batch: '150,000 tablets', lead_time: '6 weeks', free_months: months(4).slice(1), licensed: true, reg_contract: true, gmp: 'yes', gmp_by: 'EDA', gmp_date: '2025-04', gov: 'giza' }, lines: [] },
      { id: 'T5', kind: 'agency', uid: 6, title: 'Vitamin & supplement range — 9 products', status: 'active', at: t - 4 * DAY, attrs: { cats: ['supplements'], govs: ['asyut', 'sohag', 'qena', 'luxor', 'aswan'], exclusive: true, contract_years: 3, bonus_pct: 7, credit_days: 90 }, lines: [] },
      { id: 'T6', kind: 'distributor', uid: 7, title: 'Delta distributor looking for medicines and cosmetics', status: 'active', at: t - 6 * DAY, attrs: { cats: ['medicines', 'cosmetics'], govs: ['dakahlia', 'gharbia', 'sharqia', 'damietta'], warehouses: 2, cold_chain: true, fleet: 14, agencies: 5, reach: '900 accounts' }, lines: [] }
    ];
  }
  function all() { var l = D.store.get('tradeL', null); if (!Array.isArray(l)) { l = seed(); D.store.set('tradeL', l); } return l; }
  function keep(l) { D.store.set('tradeL', l); }
  function find(id) { return all().find(function (x) { return String(x.id) === String(id); }); }
  function counterKinds(k) { return { stock: ['wanted'], materials: ['wanted'], wanted: ['stock', 'materials'], file_sale: ['file_wanted'], file_wanted: ['file_sale'], toll: ['toll_wanted'], toll_wanted: ['toll'], agency: ['distributor'], distributor: ['agency'] }[k] || []; }
  function rootsOf(L) {
    var r = [];
    (L.lines || []).forEach(function (l) { var x = TT.root((l.name || '') + ' ' + (l.name_ar || '')); if (x) r.push(x); });
    var t = TT.root(L.title + ' ' + (L.desc || '')); if (t) r.push(t);
    if (L.kind === 'toll' || L.kind === 'toll_wanted') (L.attrs.forms || []).forEach(function (f) { r.push('form:' + f); });
    if (L.kind === 'agency' || L.kind === 'distributor') (L.attrs.cats || []).forEach(function (f) { r.push('cat:' + f); });
    return r;
  }
  function sub(a, b) { a = a.split(' '); b = b.split(' '); return a.every(function (w) { return b.indexOf(w) >= 0; }); }
  function matchPair(A, B) {
    if (counterKinds(A.kind).indexOf(B.kind) < 0 || A.uid === B.uid || B.status !== 'active') return false;
    var ra = rootsOf(A), rb = rootsOf(B);
    if (!ra.some(function (x) { return rb.some(function (y) { return sub(x, y) || sub(y, x); }); })) return false;
    if (A.kind === 'agency' || A.kind === 'distributor') { var ga = A.attrs.govs || [], gb = B.attrs.govs || []; if (!(ga.indexOf('all') >= 0 || gb.indexOf('all') >= 0 || ga.some(function (g) { return gb.indexOf(g) >= 0; }))) return false; }
    return true;
  }
  function notify(uid, icon, text) { if (!Array.isArray(window.NOTIFS)) return; var id = 900000 + Math.floor(Math.random() * 99999);
    window.NOTIFS.unshift({ id: id, uid: uid, icon: icon, text: text, ts: 'Just now', read: false, type: 'trade' }); if (typeof window.updateBadges === 'function') try { window.updateBadges(); } catch (e) {} }
  var demoSvc = {
    live: false,
    rows: function () { return Promise.resolve(all().filter(function (x) { return x.status === 'active' || x.status === 'reserved'; })); },
    publish: function (g, status) {
      var l = all(), fp = TT.norm(g.kind + '|' + g.title + '|' + g.desc + '|' + JSON.stringify(g.lines.map(function (x) { return [TT.key(x.name), x.qty, x.expiry]; })));
      var dup = l.find(function (x) { return x.uid === ME_ID && x.fp === fp && (x.status === 'active' || x.status === 'reserved'); });
      if (dup) { var e = new Error('DUPLICATE'); e.dup = dup.id; return Promise.reject(e); }
      var a = window.dxDir && window.dxDir.mine && window.dxDir.mine(), co = g.as && a && a.slug === g.as && a.status === 'verified' ? { name: a.name, slug: a.slug, verified: true } : null;
      var L = { id: 'M' + Date.now(), kind: g.kind, uid: ME_ID, mine: true, title: g.title, desc: g.desc, price: g.price || '', moq: g.moq || '', co: co, status: status === 'draft' ? 'draft' : 'active', at: Date.now(), attrs: g.attrs, lines: g.lines, price_mode: g.price_mode,
        discount_pct: g.discount_pct, priv: g.priv, docs: g.docs && g.docs.length ? 'waiting' : null, docNames: (g.docs || []).map(function (f) { return f.name; }), fp: fp };
      l.unshift(L);
      var mm = D.store.get('mkMine', null); if (Array.isArray(mm)) { mm.unshift({ id: L.id, title: L.title, em: KIND[L.kind].em, type: KIND[L.kind].tile, status: L.status, boosted: false, posted: L.at,   /* My Listings (market.js) */
        exp: L.status === 'draft' || /file/.test(L.kind) ? null : L.at + (/toll|agency|distributor|company/.test(L.kind) ? 90 : 30) * DAY, views: 0, inquiries: 0, price: g.price || '', moq: g.moq || '', slug: co ? co.slug : null }); D.store.set('mkMine', mm); }
      if (L.status === 'draft') { keep(l); return Promise.resolve({ id: L.id, matches: 0, row: L }); }
      var hits = l.filter(function (x) { return x !== L && matchPair(L, x); }); L.matches = hits.map(function (x) { return x.id; });
      hits.forEach(function (x) { x.matches = (x.matches || []).concat([L.id]); });
      keep(l);
      if (hits.length) notify(hits[0].uid, '🎯', '<b>' + esc(hits.length === 1 ? '1 listing matches' : hits.length + ' listings match') + '</b> ' + esc(L.title) + ' — ' + esc(hits.map(function (x) { return x.title; }).join(' · ')));
      return Promise.resolve({ id: L.id, matches: hits.length, row: L });
    },
    items: function (id) { var L = find(id); return Promise.resolve(L ? L.lines || [] : []); },
    ask: function (id, line, qty, note) { var L = find(id); if (!L) return Promise.reject(new Error('This listing is not available any more'));
      if (L.status === 'reserved') return Promise.reject(new Error('This listing is reserved — the seller is not taking price requests now'));
      if (L.uid === ME_ID) return Promise.reject(new Error('This is your own listing'));
      L.asked = (L.asked || 0) + 1; keep(all().map(function (x) { return x.id === L.id ? L : x; }));
      if (D.sendToOutbox) D.sendToOutbox({ to: L.co ? L.co.name : (window.U ? window.U(L.uid).name : 'Seller'), ctx: L.title, price: '', text: 'Price request: ' + (line || L.title) + (qty ? '\nQuantity: ' + qty : '') + (note ? '\n' + note : '') });
      return Promise.resolve({ kind: 'message' }); },
    respond: function (id, note) { var L = find(id), DL = window.dxDeals, a = window.dxDir && window.dxDir.mine && window.dxDir.mine(); if (!L) return Promise.reject(new Error('This listing is not open'));
      if (!a) return Promise.reject(new Error('Answer on behalf of a company you belong to — or write to the lister'));
      var t = /agency|distributor/.test(L.kind) ? 'agency' : /file/.test(L.kind) ? 'dossier' : 'service';
      if (!DL || !DL.FLOWS[t]) return Promise.reject(new Error('Requests & deals are not available'));
      var other = L.co || { slug: null, name: window.U ? window.U(L.uid).name : 'Member', person: true };
      var d = DL.mk(t, other.slug ? other : { slug: null, name: other.name, person: true }, a.slug, L.title, { product: L.title, listing: L.id, kind: L.kind }, note || ('Answered the Marketplace listing: ' + L.title));
      DL.save(d); return Promise.resolve({ kind: 'deal', type: t }); },
    mine: function () { return Promise.resolve(all().filter(function (x) { return x.uid === ME_ID; })); },
    close: function (id, outcome, who, note) { var l = all(), L = l.find(function (x) { return String(x.id) === String(id); }); if (!L) return Promise.reject(new Error('Only the listing’s owner can do this'));
      if (outcome === 'reserved') { if (L.status !== 'active') return Promise.reject(new Error('Only an open listing can be reserved')); L.status = 'reserved'; }
      else if (outcome === 'reopen') L.status = 'active';
      else if (outcome === 'withdrawn') L.status = 'closed';
      else if (outcome === 'sold') { L.status = 'closed'; L.sold = true; var oc = D.store.get('tradeO', []) || []; oc.unshift({ id: 'O' + Date.now(), listing: L.id, name: L.title, type: KIND[L.kind] ? KIND[L.kind].side : 'supply', mine: true, other: who ? { id: who.id, name: who.name } : null, status: who ? 'pending' : 'none', at: Date.now(), note: note || '' }); D.store.set('tradeO', oc); }
      keep(l); return Promise.resolve(true); },
    counterparts: function (id) { var L = find(id); var us = [2, 3, 4, 6].map(function (u) { var x = window.U ? window.U(u) : { name: 'Member ' + u }; return { id: u, name: x.name }; }); return Promise.resolve(L ? us : []); },
    matches: function () { var l = all(), out = []; l.filter(function (x) { return x.uid === ME_ID && x.matches; }).forEach(function (M) { M.matches.forEach(function (id) { var o = find(id); if (o && (o.status === 'active' || o.status === 'reserved')) out.push({ mine: M.id, mine_name: M.title, id: o.id, name: o.title, kind: o.kind, owner: { name: window.U ? window.U(o.uid).name : '' }, co: o.co || null }); }); }); return Promise.resolve(out); },
    outcomes: function () { return Promise.resolve(D.store.get('tradeO', []) || []); },
    confirm: function (id, yes, stars) { var oc = D.store.get('tradeO', []) || [], o = oc.find(function (x) { return x.id === id; }); if (o) { o.status = yes ? 'confirmed' : 'declined'; o.stars_got = stars || null; } D.store.set('tradeO', oc); return Promise.resolve(true); },
    rate: function (id, stars) { var oc = D.store.get('tradeO', []) || [], o = oc.find(function (x) { return x.id === id; }); if (!o || o.status !== 'confirmed') return Promise.reject(new Error('The other side has not confirmed this sale')); o.stars_given = stars; D.store.set('tradeO', oc); return Promise.resolve(true); },
    privateGet: function (id) { var L = find(id); if (!L) return Promise.reject(new Error('This listing does not exist')); if (L.uid !== ME_ID && !(L.sharedWithMe)) return Promise.reject(new Error('The owner has not shared these details with you')); return Promise.resolve(Object.assign({ checked_at: L.docsAt || null, review_status: L.docs || null }, L.priv || {})); },
    privateShare: function (id, who) { var L = find(id); if (L) { L.shared = (L.shared || []).concat([who.id]); keep(all().map(function (x) { return x.id === L.id ? L : x; })); } return Promise.resolve(true); },
    docsQueue: function () { return all().filter(function (x) { return x.docs === 'waiting'; }).map(function (x) { return { id: x.id, name: x.title, kind: x.kind, owner: { name: window.ME ? window.ME.name : 'You' }, mine: x.uid === ME_ID, docs: (x.docNames || []).map(function (n) { return { label: n, path: 'demo', bucket: 'documents' }; }), notif_no: x.priv && x.priv.notif_no }; }); },
    docsReview: function (id, ok, note) { var l = all(), L = l.find(function (x) { return String(x.id) === String(id); }); if (!L) return Promise.reject(new Error('Nothing waits for a check on this listing'));
      L.docs = ok ? 'seen' : 'rejected'; L.docsAt = ok ? Date.now() : null; L.docsNote = note || ''; keep(l); return Promise.resolve(true); },
    saveLines: function (id, lines) { var l = all(), L = l.find(function (x) { return String(x.id) === String(id); }); if (!L) return Promise.reject(new Error('Only the listing’s owner can change it'));
      L.lines = lines; keep(l); return Promise.resolve(true); },
    renewInfo: function (id) { var L = find(id); return L ? (L.bumped || L.at) : null; },
    distributor: function (slug) { var all_ = D.store.get('tradeDist', null); if (!all_) { all_ = { 'pharaonic-logistics': { govs: ['cairo', 'giza', 'alex', 'qalyubia', 'sharqia', 'dakahlia'], cats: ['medicines', 'supplements'], warehouses: 3, cold_chain: true, fleet: 22, agencies: 7 } }; D.store.set('tradeDist', all_); }
      return Promise.resolve(all_[slug] || null); },
    saveDistributor: function (slug, p) { var all_ = D.store.get('tradeDist', {}) || {}; all_[slug] = p; D.store.set('tradeDist', all_); return Promise.resolve(true); }
  };
  function svc() { return window.dxTradeSvc || demoSvc; }

  /* ── cards: the approved card, filled and labelled ── */
  function priceLabel(L) {
    if (L.price_mode === 'ask') return 'Ask for price';
    if (L.price && L.price_mode !== 'discount') { var cu = L.attrs && L.attrs.currency; return /^[\d.,]+$/.test(String(L.price).trim()) && cu ? (cu === 'USD' ? 'US$ ' : cu + ' ') + L.price : String(L.price); }
    if (L.price_mode === 'discount' && L.discount_pct) return L.discount_pct + '% off';
    var withP = (L.lines || []).filter(function (l) { return l.price; });
    if (withP.length) { var c = (L.attrs && L.attrs.currency) || 'EGP'; return (c === 'USD' ? 'US$ ' : c + ' ') + withP[0].price + (withP.length > 1 ? ' …' : ''); }
    return L.price || L.attrs && (L.attrs.asking_price || L.attrs.budget) || 'On request';
  }
  function lineText(l) { return [l.name_ar && l.name_ar !== l.name ? l.name + ' / ' + l.name_ar : l.name, l.strength, l.form ? lbl(l.form) : '', l.qty ? l.qty + ' ' + lbl(l.unit || 'box') : '', l.expiry ? 'exp ' + l.expiry : '', l.discount_pct ? l.discount_pct + '% off' : ''].filter(Boolean).join(' · '); }
  function summary(L) {
    var a = L.attrs || {};
    if (L.kind === 'stock' && (L.lines || []).length) { var n = L.lines_count || L.lines.length; return L.lines.slice(0, 2).map(lineText).join(' | ') + (n > 2 ? ' | +' + (n - 2) + ' more' : ''); }
    if (L.kind === 'file_sale') return [lbl(a.authority || ''), lbl(a.reg_type || ''), a.stage ? 'Stage: ' + lbl(a.stage) : '', a.public_price ? 'Public price ' + a.public_price + (a.pack ? ' / ' + a.pack : '') : '', a.price_increase && a.price_increase !== 'none' ? 'Price increase: ' + a.price_increase : ''].filter(Boolean).join(' · ');
    if (L.kind === 'toll') return [(a.forms || []).map(lbl).join(', '), a.min_batch ? 'Min. batch ' + a.min_batch : '', a.lead_time ? 'Lead time ' + a.lead_time : '', a.gmp === 'yes' ? 'GMP ' + (a.gmp_by || '') + ' ' + (a.gmp_date || '') : 'No GMP', (a.free_months || []).length ? 'Free: ' + a.free_months.join(', ') : ''].filter(Boolean).join(' · ');
    if (L.kind === 'agency' || L.kind === 'distributor') return [(a.cats || []).map(lbl).join(', '), govText(a.govs), a.exclusive ? 'Exclusive' : '', a.bonus_pct ? 'Bonus ' + a.bonus_pct + '%' : '', a.warehouses ? a.warehouses + ' warehouses' : '', a.cold_chain ? 'Cold chain' : ''].filter(Boolean).join(' · ');
    if (L.kind === 'company_sale') return [lbl(a.company_type || ''), a.files_count ? a.files_count + ' files' : '', a.licensed ? 'Licensed' : ''].filter(Boolean).join(' · ');
    if (L.kind === 'file_wanted') return [lbl(a.authority || ''), lbl(a.reg_type || ''), a.form || '', a.budget ? 'Budget ' + a.budget : ''].filter(Boolean).join(' · ');
    if (L.kind === 'toll_wanted') return [(a.forms || []).map(lbl).join(', '), a.batch ? 'Batch ' + a.batch : '', a.by_when ? 'By ' + a.by_when : ''].filter(Boolean).join(' · ');
    if (L.kind === 'wanted') return [a.qty || '', a.strength || '', a.form ? lbl(a.form) : '', a.needed_by ? 'Needed by ' + a.needed_by : ''].filter(Boolean).join(' · ');
    return L.desc || '';
  }
  function govText(g) { if (!g || !g.length) return ''; if (g.indexOf('all') >= 0) return '📍 All Egypt'; return '📍 ' + (g.length > 3 ? g.slice(0, 3).map(lbl).join(', ') + ' +' + (g.length - 3) : g.map(lbl).join(', ')); }
  function trust(L) {
    var a = L.attrs || {}, out = [];
    if (L.status === 'reserved') out.push('<span class="ti dx-res">🔒 Reserved</span>');
    if (L.docs === 'seen' || L.docs_checked_at) out.push('<span class="ti g dx-docs-seen" title="' + esc(DISCLAIMER) + '">📑 Documents seen by Drugbox</span>');
    if (a.gov) out.push('<span class="ti o">📍 ' + esc(lbl(a.gov)) + '</span>');
    if ((L.lines || []).some(function (l) { return l.cold; }) || a.cold_chain) out.push('<span class="ti b">❄️ Fridge</span>');
    if (a.urgent || L.urgent) out.push('<span class="ti o">⏱ Urgent</span>');
    if (a.credit_days) out.push('<span class="ti b">🗓 Credit ' + (+a.credit_days) + ' days</span>');
    var src = (L.lines || [])[0]; if (src && src.source) out.push('<span class="ti o">' + esc(lbl(src.source)) + (src.origin_country ? ' · ' + esc(src.origin_country) : '') + '</span>');
    return out.join('');
  }
  function answerLabel(k) { return { file_sale: 'Request the file', file_wanted: 'Offer your file', agency: 'Apply for the agency', distributor: 'Offer your products', toll: 'Request capacity', toll_wanted: 'Offer capacity' }[k] || null; }
  function searchWords(L) {   /* the card's canonical words, their variants and Arabic-Indic numbers: the approved search finds them in the card's text */
    var text = [L.title, L.desc, summary(L), (L.lines || []).map(function (l) { return [l.name, l.name_ar, l.strength, l.form].join(' '); }).join(' ')].join(' ');
    var w = TT.tokens(text), extra = [], seen = {};
    w.forEach(function (c) { (TT.terms.find(function (r) { return r[1] === c; }) || [0, 0, []])[2].forEach(function (v) { if (!seen[v]) { seen[v] = 1; extra.push(v); } }); });
    var nums = (text.match(/\d+/g) || []).map(function (n) { return n.replace(/\d/g, function (d) { return '٠١٢٣٤٥٦٧٨٩'[d]; }); });
    return TT.searchText(text) + ' ' + extra.join(' ') + ' ' + nums.join(' ') + ' ' + (KIND[L.kind] ? KIND[L.kind].chip : '');
  }
  function decorate(card, L) {
    if (!card || !L || !L.kind || !KIND[L.kind]) return card;
    var K = KIND[L.kind];
    card.dataset.tradeKind = L.kind; card.dataset.tradeId = L.id; card.dataset.tradePoster = L.co ? 'company' : 'person'; if (L.co && L.co.slug) card.dataset.tradeCompany = L.co.slug; else card.removeAttribute('data-trade-company');
    card.dataset.cat = K.tile; card.dataset.dxcat = K.tile; card.classList.toggle('dx-reserved', L.status === 'reserved');
    var lc = card.classList.contains('lcard');
    var badges = lc ? card.querySelector('.lc-top > div:last-child > div') : null;
    var chip = card.querySelector('.dx-tk'); if (!chip) { chip = document.createElement('span'); chip.className = 'dx-tk'; if (badges) badges.insertBefore(chip, badges.firstChild); else { var t0 = card.querySelector('.dc-title, .lc-title'); if (t0) t0.parentNode.insertBefore(chip, t0); } }
    chip.textContent = K.em + ' ' + K.chip;
    var t = card.querySelector(lc ? '.lc-title' : '.dc-title'); if (t && !lc) { var rb = t.querySelector('.role-badge'); t.textContent = L.title; if (rb) t.insertBefore(rb, t.firstChild); } else if (t) t.textContent = L.title;
    var ds = card.querySelector(lc ? '.lc-desc' : '.dc-det'); var sm = summary(L);
    if (ds && sm) { if (lc) ds.textContent = sm; else { var tail = ds.innerHTML.split('<br>')[1]; ds.textContent = sm; if (tail) ds.insertAdjacentHTML('beforeend', '<br>' + tail); } }
    var tb = card.querySelector('.trust-bar'); var tr = trust(L);
    if (tb) { tb.querySelectorAll('.dx-tr').forEach(function (x) { x.remove(); }); if (tr) { tb.insertAdjacentHTML('afterbegin', '<span class="dx-tr" style="display:contents">' + tr + '</span>'); tb.style.display = ''; } }
    else if (tr && !lc) { var old = card.querySelector('.dx-tbar'); if (old) old.remove(); var b = document.createElement('div'); b.className = 'trust-bar dx-tbar'; b.innerHTML = tr; (card.querySelector('.dc-det') || card).insertAdjacentElement('afterend', b); }
    var pr = card.querySelector('.price'); if (pr && (L.price_mode || (L.lines || []).length || L.kind !== 'materials')) pr.textContent = priceLabel(L);
    /* the buttons the kind needs: ask the price, all the items, the right answer */
    var foot = card.querySelector('.lc-foot > div:last-child') || card.querySelector('.dc-foot, .dc-act') || null;
    var host = foot || card; host.querySelectorAll('.dx-tbtn').forEach(function (x) { x.remove(); });
    var btns = '';
    if ((L.lines || []).length > 1 || (L.lines_count || 0) > 1) btns += '<button type="button" class="dx-tbtn s" data-tx-c="items">' + (L.lines_count || L.lines.length) + ' items</button>';
    if (K.side === 'supply' && (L.kind === 'stock' || L.kind === 'materials') && !L.mine) btns += '<button type="button" class="dx-tbtn" data-tx-c="ask"' + (L.status === 'reserved' ? ' disabled' : '') + '>Ask for price</button>';
    var an = answerLabel(L.kind); if (an && !L.mine) btns += '<button type="button" class="dx-tbtn" data-tx-c="respond"' + (L.status === 'reserved' ? ' disabled' : '') + '>' + esc(an) + '</button>';
    if (L.kind === 'file_sale') btns += '<button type="button" class="dx-tbtn s" data-tx-c="file">File details</button>';
    if (btns) { if (foot) foot.insertAdjacentHTML('afterbegin', btns); else { var bx = document.createElement('div'); bx.className = 'dx-tbtns'; bx.innerHTML = btns; card.appendChild(bx); } }
    var sw = card.querySelector('.dx-tq'); if (!sw) { sw = document.createElement('span'); sw.className = 'dx-tq'; sw.hidden = true; sw.setAttribute('data-noi18n', ''); card.appendChild(sw); }
    sw.textContent = searchWords(L);
    if (typeof window.dxTradeBadge === 'function') try { window.dxTradeBadge(card, L); } catch (e) {}
    return card;
  }
  /* the approved first card of its kind, filled from a listing (demo samples and new demo listings) */
  var TPL = {};
  function tpls() {   /* the approved page's own first cards (from its markup, before any layer filled them) */
    if (TPL.l && TPL.d) return;
    var w = document.createElement('div'); w.innerHTML = typeof window.MKX_HTML === 'string' ? window.MKX_HTML : '';
    var l = w.querySelector('.lcard'), d = w.querySelector('.dcard'); if (l) TPL.l = l.outerHTML; if (d) TPL.d = d.outerHTML;
    var mk = document.getElementById('mkx'); if (mk) { if (!TPL.l) { l = mk.querySelector('.lcard:not([data-trade-id])'); if (l) TPL.l = l.outerHTML; } if (!TPL.d) { d = mk.querySelector('.dcard:not([data-trade-id])'); if (d) TPL.d = d.outerHTML; } } }
  function el(h) { var w = document.createElement('div'); w.innerHTML = h; return w.firstElementChild; }
  function demoCard(L) {
    tpls(); var K = KIND[L.kind], demand = K.side === 'demand', h = demand ? TPL.d : TPL.l, c = h ? el(h) : null; if (!c) return null;
    c.removeAttribute('data-live'); c.style.display = '';
    var who = L.co ? L.co.name : (window.U ? window.U(L.uid).name : 'Member');
    if (demand) {
      var by = c.querySelector('.dc-buyer'); if (by) { var u = window.U ? window.U(L.uid) : { color: '#1a56db', initials: 'M' }; by.innerHTML = '<div class="av" style="background:' + u.color + ';width:17px;height:17px;font-size:7px">' + esc(u.initials) + '</div> <span data-noi18n>' + esc(who) + '</span>' + (L.co && L.co.verified ? ' ✓' : ''); }
      var ub = c.querySelector('.db-badge'); if (ub) ub.style.display = L.attrs.urgent ? '' : 'none';
      var dt = c.querySelector('.dc-det'); if (dt) dt.innerHTML = '<br>' + esc(govText(L.attrs.govs) || (L.attrs.gov ? '📍 ' + lbl(L.attrs.gov) : '')) + ' · ' + agoTxt(L.at);
    } else {
      var em = c.querySelector('.lc-em'); if (em) em.textContent = K.em;
      c.querySelectorAll('.cert-p').forEach(function (x) { x.remove(); });
      var lt = c.querySelector('.lt'); if (lt) lt.textContent = K.tile === 'license' ? 'LICENSE' : K.tile === 'cmo' ? 'CMO' : 'SUPPLY';
      var tb = c.querySelector('.trust-bar'); if (tb) tb.innerHTML = '';
      var mq = c.querySelector('.moq'); if (mq) { mq.textContent = ''; var w = document.createElement('span'); w.setAttribute('data-noi18n', ''); w.textContent = (L.co && L.co.verified ? '✓ ' : '') + who; mq.appendChild(w); }
    }
    c.dataset.new = L.mine ? '1' : ''; return decorate(c, L);
  }
  function agoTxt(t) { var d = Math.floor((Date.now() - t) / DAY); return d <= 0 ? 'today' : d === 1 ? '1 day ago' : d + ' days ago'; }
  function paintDemo() {
    if (svc().live) return; var mk = document.getElementById('mkx'); if (!mk) return; tpls();
    var grid = mk.querySelector('.supply-grid'), anyD = mk.querySelector('.dcard:not([data-trade-id])'), dgrid = anyD ? anyD.parentElement : mk.querySelector('[data-trade-demand]');
    if (anyD) anyD.parentElement.setAttribute('data-trade-demand', '1');
    mk.querySelectorAll('[data-trade-id]').forEach(function (x) { x.remove(); });
    svc().rows().then(function (rows) {
      rows.slice().reverse().forEach(function (L) { var c = demoCard(L); if (!c) return; var K = KIND[L.kind];
        if (K.side === 'demand' && dgrid) { var at = dgrid.querySelector('.db-sub'); if (at) at.insertAdjacentElement('afterend', c); else dgrid.insertBefore(c, dgrid.firstChild); }
        else if (grid) grid.insertBefore(c, grid.firstChild); });
      if (window.updateLiveCount) try { window.updateLiveCount(); } catch (e) {}
      if (window.dxMarket && window.dxMarket.sync) window.dxMarket.sync();
    });
  }

  /* ── injecting the forms and pills into the approved page (once: the page is kept between visits) ── */
  function inject() {
    var mk = document.getElementById('mkx'); if (!mk || mk.dataset.trade) return; mk.dataset.trade = '1';
    Object.keys(EXTRA).forEach(function (id) { var f = document.getElementById(id); if (!f) return; var body = f.querySelector('.wizard-body'); if (!body) return;
      body.insertAdjacentHTML('beforeend', EXTRA[id]()); f.dataset.txForm = '1';
      if (id === 'form-supply') body.insertAdjacentHTML('afterbegin', '<div class="dx-tx">' + F('_mode', 'What are you offering?', '<div class="radio-row"><div class="radio-opt selected" data-v="stock" role="button" tabindex="0">📦 Available stock (finished products)</div><div class="radio-opt" data-v="materials" role="button" tabindex="0">⚗️ Raw materials & packaging</div></div>', true) + '</div>'); });
    var sup = document.getElementById('form-supply'); if (sup) addLine(sup);
    var sel = document.getElementById('typeSelector'), last = document.getElementById('form-training') || mk.querySelector('#tab-create .form-section:last-of-type');
    NEW_FORMS.forEach(function (k) {
      var K = KIND[k];
      if (sel && !sel.querySelector('[data-type="' + k + '"]')) sel.insertAdjacentHTML('beforeend', '<div class="type-pill" data-type="' + k + '" data-tx-pill="1" role="button" tabindex="0">' + esc(K.pill) + '</div>');
      if (!document.getElementById('form-' + k) && last) last.insertAdjacentHTML('afterend', '<div class="wizard form-section" id="form-' + k + '" data-tx-kind="' + k + '" data-tx-form="1"><div class="wizard-head"><div class="wh-icon">' + K.em + '</div><div><div class="wizard-title">' + esc(K.title) + '</div><div class="wizard-sub">' + esc(K.sub) + '</div></div></div>' +
        '<div class="wizard-body"><div class="dx-tx">' + NEWF[k]() + postAs() + '</div></div><div class="wizard-footer"><button class="btn-draft" type="button">Save as Draft</button><button class="btn-create" type="button">Preview Listing →</button></div></div>');
    });
    var q1 = document.getElementById('step1Question'); if (q1 && !q1.querySelector('.dx-tplbox')) q1.insertAdjacentHTML('beforeend', '<div class="dx-tplbox"><div class="dx-tpl-h">Or start from a trade template</div><div class="dx-tpl">' +
      TPL_ORDER.map(function (k) { return '<button type="button" class="dx-tpl-b" data-tx-tpl="' + k + '">' + esc(KIND[k].em + ' ' + KIND[k].title) + '</button>'; }).join('') + '</div><div class="dx-tpl-n">Trade between companies — each template opens its own form</div></div>');
    paintPostAs(); markSupplyMode(sup); if (sup) syncPrice(sup);
    paintDemo(); paintMine();
  }
  function paintPostAs() {
    var a = window.dxDir && window.dxDir.mine && window.dxDir.mine(), me = (window.ME && window.ME.name) || 'Me';
    document.querySelectorAll('#mkx [data-tx="_as"] select').forEach(function (s) {
      var cur = s.value; s.innerHTML = '<option value="">' + esc(me) + ' (myself)</option>' + (a ? '<option value="' + esc(a.slug) + '"' + (a.status === 'verified' ? '' : ' disabled') + '>' + esc(a.name) + (a.status === 'verified' ? ' ✓' : ' — needs verification') + '</option>' : '');
      s.value = cur && s.querySelector('option[value="' + cur + '"]:not([disabled])') ? cur : (a && a.status === 'verified' ? a.slug : ''); });
  }
  function markSupplyMode(f) {   /* stock lines for finished products; the approved raw-material fields for materials */
    if (!f) return; var mode = kindOf(f);
    var st = f.querySelector('.dx-stock'); if (st) st.style.display = mode === 'stock' ? '' : 'none';
    var gov = f.querySelector('[data-tx="gov"]'); if (gov) gov.closest('.row2').style.display = mode === 'stock' ? '' : 'none';
    f.querySelectorAll('.wizard-body .field').forEach(function (fd) { var l = fd.querySelector('.field-label'); if (!l || fd.closest('.dx-tx') || !/^MOQ/.test(orig(l))) return;   /* each item carries its own quantity */
      var r = l.querySelector('.req'); if (mode === 'stock' && r) r.remove(); if (mode !== 'stock' && !r) l.insertAdjacentHTML('beforeend', ' <span class="req">*</span>'); });
  }
  function syncPrice(f) {   /* a discount or «اطلب سعر»: the approved price field is not required */
    var pm = priceMode(f); var disc = f.querySelector('.dx-disc'); if (disc) disc.style.display = pm === 'discount' ? '' : 'none';
    var need = pm === 'amount' && kindOf(f) !== 'stock';   /* stock: each item may carry its price; none at all → «اطلب سعر» */
    f.querySelectorAll('.field').forEach(function (fd) { var l = fd.querySelector('.field-label'); if (!l || fd.closest('.dx-tx') || !/^Price per unit/.test(orig(l))) return;
      var r = l.querySelector('.req'); if (need && !r) l.insertAdjacentHTML('beforeend', ' <span class="req">*</span>'); if (!need && r) r.remove();
      var i = fd.querySelector('input'); if (i) i.disabled = pm === 'ask'; });
  }

  /* ── clicks in the forms (delegated: the approved handlers were bound to the approved elements only) ── */
  document.addEventListener('click', function (e) {
    var t = e.target; if (!t.closest) return;
    var pill = t.closest('#mkx .type-pill[data-tx-pill]');
    if (pill) { document.querySelectorAll('#mkx .type-pill').forEach(function (p) { p.classList.remove('active'); }); pill.classList.add('active');
      document.querySelectorAll('#mkx .form-section').forEach(function (f) { f.classList.remove('active'); }); var f = document.getElementById('form-' + pill.dataset.type); if (f) f.classList.add('active'); paintPostAs(); return; }
    var chip = t.closest('#mkx .dx-tx .chip[data-v]');
    if (chip) { var gov = chip.closest('.dx-gov'); chip.classList.toggle('selected');
      if (gov) { if (chip.dataset.v === 'all' && chip.classList.contains('selected')) gov.querySelectorAll('.chip[data-v]:not([data-v="all"])').forEach(function (c) { c.classList.remove('selected'); });
        else if (chip.dataset.v !== 'all') { var al = gov.querySelector('.chip[data-v="all"]'); if (al) al.classList.remove('selected'); } }
      return; }
    var ro = t.closest('#mkx .dx-tx .radio-opt[data-v]');
    if (ro) { ro.parentElement.querySelectorAll('.radio-opt').forEach(function (x) { x.classList.remove('selected'); }); ro.classList.add('selected');
      var f2 = ro.closest('.form-section'); if (ro.closest('[data-tx="_mode"]')) { markSupplyMode(f2); syncPrice(f2); } if (ro.closest('[data-tx="price_mode"]')) syncPrice(f2); return; }
    var act = t.closest('#mkx [data-tx-a]');
    if (act) { var f3 = act.closest('.form-section'); e.preventDefault();
      if (act.dataset.txA === 'addline') { var r = addLine(f3); if (r) r.querySelector('input').focus(); }
      if (act.dataset.txA === 'delline') { var ln = act.closest('.dx-line'); if (f3.querySelectorAll('.dx-line').length > 1) ln.remove(); else ln.querySelectorAll('input').forEach(function (i) { if (i.type === 'checkbox') i.checked = false; else i.value = ''; }); }
      if (act.dataset.txA === 'paste') pasteDialog(f3);
      return; }
  });
  document.addEventListener('keydown', function (e) { if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('#mkx .dx-tx .chip[data-v], #mkx .dx-tx .radio-opt[data-v], #mkx .type-pill[data-tx-pill]')) { e.preventDefault(); e.target.click(); } });

  /* the documents for Drugbox (license, CMO, new forms): files kept until the listing is published */
  var DOCS = {};
  document.addEventListener('click', function (e) {
    var z = e.target.closest && e.target.closest('#mkx .form-section .upload-zone-sm'); if (!z) return;
    var fd = z.closest('.field'), lab = orig(fd && fd.querySelector('.field-label')); if (/COA|spec/i.test(lab)) return;   /* the COA: market.js */
    var f = z.closest('.form-section'); if (!f || !/form-(license|cmo|company_sale|agency)/.test(f.id)) return;
    e.preventDefault(); var inp = document.createElement('input'); inp.type = 'file'; inp.multiple = true; inp.accept = '.pdf,.jpg,.jpeg,.png';
    inp.addEventListener('change', function () { var fs = [].slice.call(inp.files || []).filter(function (x) { return x.size <= 10 * 1024 * 1024; }).slice(0, 6);
      if (inp.files.length && !fs.length) { toast('Each file must be 10 MB or smaller'); return; }
      DOCS[f.id] = fs; z.setAttribute('data-docs', String(fs.length)); z.textContent = '📄 ' + fs.map(function (x) { return x.name; }).join(', ') + ' · attached'; });
    inp.click();
  });

  /* ── publishing: the approved forms keep their own preview and hook; the new forms get the same preview ── */
  var STASH = null;
  window.addEventListener('click', function (e) {   /* before market.js and the approved handlers (document): a trade draft is saved here */
    var b = e.target.closest && e.target.closest('#mkx .form-section[data-tx-form] .btn-create, #mkx .form-section[data-tx-form] .btn-draft'); if (!b) return;
    var f = b.closest('.form-section'), g = gather(f), draft = b.classList.contains('btn-draft');
    if (!g.kind) return;
    if (!draft) { var miss = missing(f, g); if (miss.length) { e.preventDefault(); e.stopImmediatePropagation(); toast('Please fill: ' + miss.join(', ')); return; } }
    /* a price typed as a bare number carries the currency chosen next to it (market.js wrote US$ before this) */
    if (g.attrs.currency && g.attrs.currency !== 'USD') f.querySelectorAll('.field').forEach(function (fd) { var l = fd.querySelector('.field-label'); var i = fd.querySelector('input'); if (l && i && /^Price per unit/.test(orig(l)) && /^US\$\s*[\d.,]+/.test(i.value)) i.value = g.attrs.currency + ' ' + i.value.replace(/^US\$\s*/, ''); });
    STASH = { g: g, form: f.id, at: Date.now() };
    if (f.dataset.txKind || draft) { e.preventDefault(); e.stopImmediatePropagation(); if (draft) return saveDraft(f, g); return preview(f, g); }
  }, true);
  function gate(g) { if (typeof window.dxTradeGate !== 'function') return Promise.resolve(true); try { return Promise.resolve(window.dxTradeGate(g.kind, { asCompany: !!g.as })); } catch (e) { return Promise.resolve(false); } }
  function preview(f, g) {
    var L = { id: 'preview', kind: g.kind, title: g.title, desc: g.desc, attrs: g.attrs, lines: g.lines, price_mode: g.price_mode, discount_pct: g.discount_pct, status: 'active', at: Date.now(), uid: ME_ID, mine: true,
      co: g.as ? (window.dxDir && window.dxDir.mine && window.dxDir.mine()) : null };
    var card = demoCard(L); if (card) { card.style.maxWidth = '100%'; card.querySelectorAll('button,.btn-save').forEach(function (x) { x.style.pointerEvents = 'none'; }); }
    var m = D.modal({ title: 'Preview your listing', body: '<div class="dbk-note">This is how buyers will see it. You can boost it after publishing.</div><div id="dbkPrev"></div>', secondary: 'Keep editing',
      primary: { label: 'Publish listing', onClick: function () { publish(f, g); } } });
    if (card) m.el.querySelector('#dbkPrev').appendChild(card);
  }
  function clearForm(f) { f.querySelectorAll('input:not([type=file]):not([type=checkbox]),textarea').forEach(function (i) { if (!i.closest('[data-l]') || true) i.value = ''; });
    f.querySelectorAll('.dx-tx .chip.selected[data-v], .dx-line input[type=checkbox]').forEach(function (c) { if (c.type === 'checkbox') c.checked = false; else c.classList.remove('selected'); });
    var lines = f.querySelector('.dx-lines'); if (lines) { lines.innerHTML = ''; addLine(f); } delete DOCS[f.id];
    f.querySelectorAll('.upload-zone-sm[data-docs]').forEach(function (z) { z.removeAttribute('data-docs'); z.innerHTML = '<b>Upload</b> documents for Drugbox to check (PDF / photo, up to 6)'; }); }
  function publish(f, g, draft) {
    return gate(g).then(function (ok) {
      if (ok === false) return;
      return svc().publish(g, draft ? 'draft' : 'active').then(function (r) {
        clearForm(f);
        if (draft) { toast('Draft saved — find it in My Listings'); if (window.switchMasterTab) window.switchMasterTab('manage'); paintMine(); return; }
        if (window.switchMasterTab) window.switchMasterTab('browse');
        var cb = document.querySelector('#mkx .cat-cb[data-cat="' + KIND[g.kind].tile + '"]'); if (cb) cb.checked = true;
        paintDemo(); if (window.dxMarket) window.dxMarket.paint();
        toast('Your listing is live' + (r && r.matches ? ' — ' + r.matches + (r.matches === 1 ? ' listing matches it' : ' listings match it') + ' (My Listings → Matches)' : ''));
      }, function (er) { failed(er, g); });
    });
  }
  function saveDraft(f, g) { if (!g.title) { toast('Add a name first, then save the draft'); return; } publish(f, g, true); }
  function failed(er, g) {
    var m = String((er && er.message) || '');
    if (er && (er.dup || /^DUPLICATE/.test(m))) { var id = er.dup || (/DUPLICATE:(\w+)/.exec(m) || [])[1];
      D.modal({ title: 'You already posted this offer', body: '<p>The same offer is still open in My Listings. Renew that one instead of posting it again — renewing moves it up for free once a week; to reach the top now, feature it.</p>',
        secondary: 'Close', primary: { label: 'Renew that one', onClick: function () { renewTrade(id); } } }); return; }
    toast(m || 'Could not publish');
  }
  /* a listing published from an approved form (supply, demand, CMO, license): the trade fields travel with it */
  var hookPrev = window.dxLiveHook;
  window.dxLiveHook = function (kind, d) {
    if (kind === 'listing' && d && STASH && Date.now() - STASH.at < 600000 && d.type !== 'job') { var g = STASH.g; STASH = null;
      d.trade = g; if (!svc().live) { var f = document.getElementById('form-' + d.type); setTimeout(function () { svc().publish(g, 'active').then(function (r) { if (f) clearForm(f); paintDemo(); var nw = document.querySelector('#mkx .lcard[data-new="1"]:not([data-trade-id]), #mkx .dcard[data-new="1"]:not([data-trade-id])'); if (nw) nw.remove();
        if (r && r.matches) toast(r.matches + (r.matches === 1 ? ' listing matches it' : ' listings match it') + ' — see My Listings → Matches'); if (window.dxMarket) window.dxMarket.paint(); }, function (er) { failed(er, g); }); }, 60);
        return; } }   /* the demo keeps it as a trade listing (not market.js's plain copy) */
    return hookPrev ? hookPrev.apply(this, arguments) : undefined;
  };

  /* ── actions on cards ── */
  function rowOfCard(card) { var id = card.dataset.tradeId; return (window.dxTrade.rowOf && window.dxTrade.rowOf(id, card)) || find(id) || null; }
  window.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#mkx [data-tx-c]'); if (!b) return;
    e.preventDefault(); e.stopPropagation();
    var card = b.closest('[data-trade-id]'), L = card && rowOfCard(card); if (!L) return;
    var c = b.dataset.txC;
    if (c === 'items') return itemsDialog(L);
    if (c === 'ask') return askDialog(L);
    if (c === 'respond') return respondDialog(L);
    if (c === 'file') return fileDialog(L);
  }, true);
  function itemsDialog(L) {
    svc().items(L.id).then(function (lines) {
      var m = D.modal({ title: L.title, secondary: 'Close', body: '<div class="dx-items">' + lines.map(function (l, i) { return '<div class="dx-item"><div><b data-noi18n>' + esc(l.name) + (l.name_ar && l.name_ar !== l.name ? ' / ' + esc(l.name_ar) : '') + '</b><small>' + esc([l.strength, l.form ? lbl(l.form) : '', l.qty ? l.qty + ' ' + lbl(l.unit || 'box') : '', l.expiry ? 'exp ' + l.expiry : '', l.source ? lbl(l.source) + (l.origin_country ? ' · ' + l.origin_country : '') : '', l.pack_state ? lbl(l.pack_state) : '', l.cold ? '❄️ Fridge' : '', l.discount_pct ? l.discount_pct + '% off' : '', l.price ? 'Price ' + l.price : ''].filter(Boolean).join(' · ')) + '</small></div>' +
        (!L.mine && L.status !== 'reserved' ? '<button type="button" class="dx-tbtn s" data-ask-line="' + i + '">Ask for price</button>' : '') + '</div>'; }).join('') + '</div>' });
      m.el.addEventListener('click', function (ev) { var x = ev.target.closest && ev.target.closest('[data-ask-line]'); if (!x) return; m.close(); askDialog(L, lines[+x.dataset.askLine]); });
    }, function (er) { toast(er.message || 'Could not load the items'); });
  }
  function askDialog(L, line) {
    if (L.status === 'reserved') { toast('This listing is reserved — the seller is not taking price requests now'); return; }
    var item = line ? [line.name, line.strength].filter(Boolean).join(' ') : L.title;
    D.modal({ title: 'Ask for price', body: '<div class="dbk-note">About <b data-noi18n>' + esc(item) + '</b></div>' +
      '<div class="dbk-f"><label for="dxAskQ">Quantity you need</label><input id="dxAskQ" maxlength="60" placeholder="e.g. 50 box"></div><div class="dbk-f"><label for="dxAskN">Note</label><textarea id="dxAskN" maxlength="500" placeholder="Delivery, payment terms…"></textarea></div>' +
      '<p class="cp-muted">Company to company it goes to Requests & deals as a quote request; otherwise to the seller’s Messages, naming the listing.</p>',
      primary: { label: 'Send price request', onClick: function (b, close) { var ok = b.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        svc().ask(L.id, line ? (line.id || item) : null, b.querySelector('#dxAskQ').value.trim(), b.querySelector('#dxAskN').value.trim()).then(function (r) { close();
          toast(r && r.kind === 'deal' ? 'Price request sent — follow it in Requests & deals' : 'Price request sent — the answer comes in Messages'); },
          function (er) { if (ok) ok.disabled = false; toast((er && er.message) || 'Could not send'); }); return false; } } });
  }
  function respondDialog(L) {
    var an = answerLabel(L.kind) || 'Answer';
    D.modal({ title: an, body: '<div class="dbk-note" data-noi18n>' + esc(L.title) + '</div><div class="dbk-f"><label for="dxRspN">Message</label><textarea id="dxRspN" maxlength="500" placeholder="Tell them who you are and what you propose"></textarea></div>' +
      (L.kind === 'file_sale' ? '<p class="dbk-note dx-disc-note">' + esc(DISCLAIMER) + '</p>' : '') + '<p class="cp-muted">Sent on behalf of the company you act as — follow it in Requests & deals.</p>',
      primary: { label: 'Send', onClick: function (b, close) { var ok = b.parentNode.querySelector('[data-a=ok]'); if (ok) ok.disabled = true;
        svc().respond(L.id, b.querySelector('#dxRspN').value.trim()).then(function () { close(); toast('Sent — follow it in Requests & deals'); },
          function (er) { if (ok) ok.disabled = false; var m = (er && er.message) || 'Could not send'; toast(m); if (/write to (the lister|them)/i.test(m) && card0(L)) { close(); var c = card0(L).querySelector('.btn-contact, .qt-btn'); if (c) c.click(); } }); return false; } } });
  }
  function card0(L) { return document.querySelector('#mkx [data-trade-id="' + L.id + '"]'); }
  function fileDialog(L) {
    var a = L.attrs || {};
    var rows = [['Authority', lbl(a.authority || '')], ['Registration type', lbl(a.reg_type || '')], ['Stage', lbl(a.stage || '')], ['Steps done', (a.stages_done || []).map(lbl).join(', ')], ['Decision issued', a.decision === 'yes' ? 'Yes' : a.decision === 'no' ? 'No' : ''],
      ['Notification valid until', a.notif_valid_until || ''], ['Public price per pack', a.public_price ? a.public_price + (a.pack ? ' / ' + a.pack : '') : ''], ['Price increase', a.price_increase === 'approved' ? 'Approved' : a.price_increase === 'submitted' ? 'Submitted (not approved yet)' : a.price_increase === 'none' ? 'None' : ''],
      ['Asking price', a.asking_price || ''], ['Commission', a.commission || ''], ['Included', (a.included || []).map(lbl).join(', ')], ['Buyer conditions', (a.buyer_conditions || []).map(lbl).join(', ')], ['Sales per year (units)', a.sales_units || ''], ['Factory', a.factory || ''], ['Registration valid until', a.reg_expiry || '']].filter(function (r) { return r[1]; });
    var m = D.modal({ title: L.title, secondary: 'Close', body: '<table class="cp-spec">' + rows.map(function (r) { return '<tr><th>' + esc(r[0]) + '</th><td data-noi18n>' + esc(r[1]) + '</td></tr>'; }).join('') + '</table>' +
      (L.docs === 'seen' || L.docs_checked_at ? '<p class="dbk-note">📑 Documents seen by Drugbox</p>' : '') + '<p class="dbk-note dx-disc-note">' + esc(DISCLAIMER) + '</p><div class="dx-privout"></div>' +
      '<button type="button" class="dx-tbtn s" data-priv="1">🔒 Notification number</button>' });
    m.el.addEventListener('click', function (ev) { if (!ev.target.closest || !ev.target.closest('[data-priv]')) return;
      svc().privateGet(L.id).then(function (p) { var o = m.el.querySelector('.dx-privout'); o.innerHTML = '<table class="cp-spec">' + [['Notification number', p.notif_no], ['Registration / licence number', p.reg_no || p.licence_no]].filter(function (r) { return r[1]; }).map(function (r) { return '<tr><th>' + esc(r[0]) + '</th><td data-noi18n>' + esc(r[1]) + '</td></tr>'; }).join('') + '</table>' || '<p class="cp-muted">Nothing in the private box yet.</p>'; },
        function (er) { toast((er && er.message) || 'The owner has not shared these details with you'); }); });
  }

  /* ── My Listings: reserved / sold, renew once a week or feature, matches, sales ── */
  function renewTrade(id) {
    var mk = window.dxMarketSvc || (window.dxMarket && window.dxMarket.demoSvc); if (!mk) return;
    Promise.resolve(mk.renew(id)).then(function () { toast('Renewed — it moved up and shows for another 30 days'); if (window.dxMarket) window.dxMarket.paint(); paintMine(); }, function (er) { renewFailed(er, id); });
  }
  function renewFailed(er, id) {
    var m = String((er && er.message) || ''), when = (/RENEW_LIMIT:([\d-]+)/.exec(m) || [])[1];
    if (!when) { toast(m || 'Could not renew'); return; }
    D.modal({ title: 'Renewed this week already', body: '<p>A listing is renewed free once every 7 days — the next free renewal is on <b data-noi18n>' + esc(when) + '</b>. To reach the top now, feature it (Boost or Featured).</p>', secondary: 'Close',
      primary: { label: '⭐ Feature this listing', onClick: function () { window.__dxBoostListing = id; if (typeof window.openBoostModal === 'function') window.openBoostModal('boost'); } } });
  }
  /* the demo's renewal follows the same once-a-week rule as the database (market.js's demo service is wrapped) */
  if (window.dxMarket && window.dxMarket.demoSvc) { var dR = window.dxMarket.demoSvc.renew; window.dxMarket.demoSvc.renew = function (id) {
    var l = D.store.get('mkMine', []) || [], r = l.find(function (x) { return x.id === id; }), last = r ? (r.bumped || r.renewed || r.posted) : 0;
    if (last && Date.now() - last < 7 * DAY && !(r.exp && r.exp <= Date.now())) { var e = new Error('RENEW_LIMIT:' + new Date(last + 7 * DAY).toISOString().slice(0, 10)); return Promise.reject(e); }
    return dR.apply(this, arguments).then(function (x) { var l2 = D.store.get('mkMine', []) || [], r2 = l2.find(function (y) { return y.id === id; }); if (r2) { r2.bumped = Date.now(); D.store.set('mkMine', l2); } return x; }); }; }
  /* the boost window opened from a listing: that listing is chosen (checkout.js fills the list) */
  new MutationObserver(function () { var s = document.getElementById('dxPayListing'); if (s && window.__dxBoostListing && s.options.length > 1) { if (s.querySelector('option[value="' + window.__dxBoostListing + '"]')) s.value = String(window.__dxBoostListing); window.__dxBoostListing = null; } })
    .observe(document.body, { childList: true, subtree: true });
  /* ··· on a My Listings row gets "Reserved / sold"; market.js's renew error is read here */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#tab-manage [data-ml-a="renew"]'); if (!b) return;
    var row = b.closest('[data-ml]') || b.closest('[data-ml-due]'), id = row && (row.getAttribute('data-ml') || row.getAttribute('data-ml-due')); if (!id) return;
    e.preventDefault(); e.stopImmediatePropagation(); renewTrade(isNaN(+id) ? id : +id);
  }, true);
  new MutationObserver(function (muts) {
    muts.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType !== 1 || !n.matches || !n.matches('.dbk-ov')) return;
      var ed = n.querySelector('#mlT'); if (ed && !n.querySelector('[data-tx-items]')) { var rowE = [].find.call(document.querySelectorAll('#tab-manage [data-ml]'), function (r) { var s0 = r.querySelector('[data-noi18n]'); return s0 && s0.textContent === ed.value; });
        var idE = rowE && rowE.getAttribute('data-ml'), LE = idE && ((window.dxTrade.rowOf && window.dxTrade.rowOf(idE)) || find(idE)); if (LE && LE.kind === 'stock') {
          ed.closest('.dbk-f').insertAdjacentHTML('afterend', '<button type="button" class="dbk-btn s" data-tx-items="1">📦 Edit items</button>');
          n.querySelector('[data-tx-items]').addEventListener('click', function () { var x = n.querySelector('.dbk-x'); if (x) x.click(); itemsEditor(isNaN(+idE) ? idE : +idE, ed.value); }); } }
      var btn = n.querySelector('[data-x="del"]'), title = (n.querySelector('.dbk-hd b') || {}).textContent || ''; if (!btn || n.querySelector('[data-x="tx-close"]')) return;
      var row = [].find.call(document.querySelectorAll('#tab-manage [data-ml]'), function (r) { var s = r.querySelector('[data-noi18n]'); return s && s.textContent === title.trim(); });
      if (!row) return; var id = row.getAttribute('data-ml');
      btn.insertAdjacentHTML('beforebegin', '<button type="button" class="dbk-btn s" data-x="tx-close" data-ml-id="' + esc(id) + '">🔒 Reserved / sold</button>');
      var rn = n.querySelector('[data-x="renew"]'); if (rn) rn.addEventListener('click', function (ev) { ev.stopImmediatePropagation(); var x0 = n.querySelector('.dbk-x'); if (x0) x0.click(); renewTrade(isNaN(+id) ? id : +id); }, true);   /* once a week, or feature it */
      n.querySelector('[data-x="tx-close"]').addEventListener('click', function (ev) { ev.stopPropagation(); var x = n.querySelector('.dbk-x'); if (x) x.click(); else n.remove(); closeDialog(isNaN(+id) ? id : +id, title.trim()); });
    }); });
  }).observe(document.body, { childList: true });
  function itemsEditor(id, title) {   /* the items of a published stock listing: change quantities, remove, add */
    svc().items(id).then(function (lines) {
      var m = D.modal({ title: title, body: '<div class="dx-tx" id="dxItemsF"><div class="dx-lines"></div><div class="dx-lines-a"><button type="button" class="dx-tbtn s" data-tx-a="addline">＋ Add another item</button></div></div>',
        primary: { label: 'Save changes', onClick: function (b) { var ls = readLines(b.querySelector('#dxItemsF'));
          if (!ls.length || ls.some(function (l) { return !(l.qty > 0); })) { toast('Please fill: Quantity of every item'); return false; }
          svc().saveLines(id, ls).then(function () { toast('Items saved'); paintDemo(); if (window.dxMarket) window.dxMarket.paint(); }, function (er) { toast((er && er.message) || 'Could not save'); }); } } });
      var f = m.el.querySelector('#dxItemsF'); lines.forEach(function (l) { addLine(f, l); }); if (!lines.length) addLine(f);
      f.addEventListener('click', function (e) { var a = e.target.closest('[data-tx-a]'); if (!a) return; e.preventDefault(); if (a.dataset.txA === 'addline') addLine(f); if (a.dataset.txA === 'delline') { var ln = a.closest('.dx-line'); if (f.querySelectorAll('.dx-line').length > 1) ln.remove(); } });
    }, function (er) { toast((er && er.message) || 'Could not load the items'); });
  }
  function isFile(id) { var L = (window.dxTrade.rowOf && window.dxTrade.rowOf(id)) || find(id); return !!(L && L.kind === 'file_sale'); }
  function closeDialog(id, title) {
    svc().counterparts(id).then(function (who) {
      var m = D.modal({ title: title || 'Reserved / sold', secondary: 'Close', body: '<div class="dx-close">' +
        '<button type="button" class="dbk-btn s" data-o="reserved">🔒 Mark reserved (محجوز)</button><button type="button" class="dbk-btn s" data-o="reopen">🔓 Open it again</button>' +
        '<div class="dbk-f"><label for="dxSoldTo">Sold to / bought from</label><select id="dxSoldTo"><option value="">Someone outside Drugbox</option>' + who.map(function (u) { return '<option value="' + esc(u.id) + '">' + esc(u.name) + (u.company ? ' · ' + esc(u.company) : '') + '</option>'; }).join('') + '</select></div>' +
        '<p class="cp-muted">They are asked to confirm and rate; when both act for companies the sale counts in the company’s track record.</p>' +
        '<button type="button" class="dbk-btn s" data-o="sold">✅ Mark sold (اتباع)</button>' + (isFile(id) ? '<button type="button" class="dbk-btn s" data-o="share">🔒 Share the private box with them</button>' : '') + '<button type="button" class="dbk-btn d" data-o="withdrawn">Withdraw listing</button></div>' });
      m.el.addEventListener('click', function (ev) { var b = ev.target.closest && ev.target.closest('[data-o]'); if (!b) return; var o = b.dataset.o, sel = m.el.querySelector('#dxSoldTo'), w = who.find(function (u) { return String(u.id) === sel.value; }) || null;
        if (o === 'share') { if (!w) { toast('Choose the member to share it with'); return; } b.disabled = true; svc().privateShare(id, w).then(function () { m.close(); toast('Shared with ' + w.name); }, function (er) { b.disabled = false; toast((er && er.message) || 'Could not share'); }); return; }
        b.disabled = true; svc().close(id, o, o === 'sold' ? w : null, '').then(function () { m.close(); toast(o === 'reserved' ? 'Marked reserved — buyers see «Reserved»' : o === 'reopen' ? 'Open again' : o === 'sold' ? (w ? 'Marked sold — ' + w.name + ' is asked to confirm and rate' : 'Marked sold') : 'Listing withdrawn');
          paintDemo(); if (window.dxMarket) window.dxMarket.paint(); paintMine(); }, function (er) { b.disabled = false; toast((er && er.message) || 'Could not save'); }); });
    }, function (er) { toast((er && er.message) || 'Could not load'); });
  }
  function paintMine() {
    var m = document.getElementById('tab-manage'); if (!m) return; var host = m.querySelector('.page-wrap') || m;
    Promise.all([svc().matches(), svc().outcomes()]).then(function (r) {
      var mt = r[0] || [], oc = r[1] || [], box = host.querySelector('.dx-trade-mine'); if (!box) { box = document.createElement('div'); box.className = 'dx-trade-mine'; host.appendChild(box); }
      box.innerHTML = '<h3 class="dx-tm-h">🎯 Matches for your listings <span>' + mt.length + '</span></h3>' + (mt.length ? mt.slice(0, 30).map(function (x, i) {
          return '<div class="dx-tm-r"><div><b data-noi18n>' + esc(x.name) + '</b><small>' + esc((KIND[x.kind] || {}).chip || '') + ' · <span data-noi18n>' + esc((x.co && x.co.name) || (x.owner && x.owner.name) || '') + '</span> · for <span data-noi18n>' + esc(x.mine_name) + '</span></small></div><button type="button" class="dx-tbtn s" data-tm="' + i + '">View</button></div>'; }).join('')
        : '<div class="dx-tm-e">No matches yet — when someone posts what you need (or need what you have), it shows here and you are notified.</div>') +
        (oc.length ? '<h3 class="dx-tm-h">🤝 Sales and purchases</h3>' + oc.slice(0, 30).map(function (o, i) { var other = o.other ? o.other.name : 'outside Drugbox';
          return '<div class="dx-tm-r"><div><b data-noi18n>' + esc(o.name) + '</b><small>' + (o.mine ? 'Sold / closed by you' : 'Named you') + ' · <span data-noi18n>' + esc(other) + '</span> · ' + esc(o.status === 'pending' ? 'Waiting for confirmation' : o.status === 'confirmed' ? 'Confirmed' : o.status === 'declined' ? 'Not confirmed' : 'Closed') +
            (o.stars_got ? ' · ★' + o.stars_got : '') + '</small></div>' + (!o.mine && o.status === 'pending' ? '<button type="button" class="dx-tbtn" data-oc="' + i + '" data-oca="confirm">Confirm and rate</button>' : '') +
            (o.mine && o.status === 'confirmed' && !o.stars_given ? '<button type="button" class="dx-tbtn" data-oc="' + i + '" data-oca="rate">Rate them</button>' : '') + '</div>'; }).join('') : '');
      box.onclick = function (ev) { var v = ev.target.closest && ev.target.closest('[data-tm]'); if (v) { var x = mt[+v.dataset.tm]; if (window.switchMasterTab) window.switchMasterTab('browse'); var c = document.querySelector('#mkx [data-trade-id="' + x.id + '"]'); if (c) { c.style.display = ''; c.scrollIntoView({ behavior: 'smooth', block: 'center' }); c.classList.add('dbk-new'); } else { var si = document.getElementById('searchIn'); if (si) { si.value = x.name; if (window.__mkxFilter) window.__mkxFilter(x.name); } } return; }
        var o = ev.target.closest && ev.target.closest('[data-oc]'); if (o) rateDialog(oc[+o.dataset.oc], o.dataset.oca); };
    }, function () {});
  }
  function rateDialog(o, how) {
    var m = D.modal({ title: how === 'confirm' ? 'Did this sale happen?' : 'Rate them', body: '<div class="dbk-note" data-noi18n>' + esc(o.name) + '</div>' +
      (how === 'confirm' ? '<button type="button" class="dbk-btn s" data-no-sale="1">It did not happen</button>' : '') + '<div class="dbk-f"><label for="dxStars">Rating (1–5)</label><select id="dxStars"><option>5</option><option>4</option><option>3</option><option>2</option><option>1</option></select></div><div class="dbk-f"><label for="dxStarN">Comment</label><textarea id="dxStarN" maxlength="500"></textarea></div>',
      secondary: 'Close',
      primary: { label: how === 'confirm' ? 'Confirm and rate' : 'Rate', onClick: function (b) { var s = +b.querySelector('#dxStars').value, n = b.querySelector('#dxStarN').value.trim();
        (how === 'confirm' ? svc().confirm(o.id, true, s, n) : svc().rate(o.id, s, n)).then(function () { toast('Thank you — rated ' + s + '★'); paintMine(); }, function (er) { toast((er && er.message) || 'Could not save'); }); } } });
    var ns = m.el.querySelector('[data-no-sale]'); if (ns) ns.addEventListener('click', function () { m.close(); svc().confirm(o.id, false).then(function () { toast('Answered — it did not happen'); paintMine(); }, function (er) { toast((er && er.message) || 'Could not save'); }); });
  }
  document.addEventListener('click', function (e) { var t = e.target.closest && e.target.closest('#mkx .master-tab[data-tab="manage"]'); if (t) setTimeout(paintMine, 0); });

  /* ── deals: the agency kind and the checklist before «اتفقنا» on a file deal ── */
  var DL = window.dxDeals;
  if (DL && DL.FLOWS && !DL.FLOWS.agency) DL.FLOWS.agency = { label: 'Agency request', icon: 'users', steps: ['requested', 'talks', 'agreed'],
    acts: { requested: { to: ['talk', 'decline'], from: ['cancel'] }, talks: { to: ['agree', 'decline'], from: ['cancel', 'decline'] } } };
  var CHECK = [['notif_seen', 'I saw the notification number and its validity'], ['stage_understood', 'I understand the file’s stage and what is still missing'], ['price_increase_checked', 'I checked whether a price increase is submitted or approved'],
    ['transfer_needs_approval', 'I know the transfer needs the authority’s approval'], ['docs_reviewed', 'I reviewed the documents shared in this deal']];
  window.dxTradeChecklist = function (d, go) {
    D.modal({ title: 'Before you agree — ' + d.title, body: '<p class="dbk-note dx-disc-note">' + esc(DISCLAIMER) + '</p>' + CHECK.map(function (c) { return '<label class="dx-chk dx-chk-l"><input type="checkbox" data-ck="' + c[0] + '"> ' + esc(c[1]) + '</label>'; }).join(''),
      primary: { label: 'Agree terms', onClick: function (b) { var ck = {}, all_ = true; b.querySelectorAll('[data-ck]').forEach(function (x) { ck[x.dataset.ck] = x.checked; if (!x.checked) all_ = false; });
        if (!all_) { toast('Tick every box before agreeing'); return false; } go({ checklist: ck, note: 'Checklist done' }); } } });
  };

  /* ── Admin → Review → Trade documents (demo; the live adapter answers from the database) ── */
  if (window.dxModeration && !window.dxModeration.__trade) {
    var M = window.dxModeration, mLoad = M.load, mDecide = M.decide;
    M.load = function () { return mLoad.apply(this, arguments).then(function (d) { d.tradedocs = svc().live ? (d.tradedocs || []) : demoSvc.docsQueue(); return d; }); };
    M.decide = function (kind, id, value, note) { if (kind === 'tradedocs' && !svc().live) return demoSvc.docsReview(id, value === 'seen', note); return mDecide.apply(this, arguments); };
    M.__trade = true;
  }

  /* ── the company page: the distributor's profile (W-15) — on the Overview of a page in the Distribution sector ── */
  window.dxTradeDistributor = function (slug) { return svc().distributor(slug); };
  function distSlug() { var b = document.querySelector('#content .cp-hero [data-hws], #content .cp-hero [data-hrfq]'); return b ? (b.getAttribute('data-hws') || b.getAttribute('data-hrfq')) : null; }
  function paintDist() {
    var two = document.querySelector('#content .cp-two'), tab = document.querySelector('#content .cp-tab.on'); if (!two || !tab || tab.getAttribute('data-htab2') !== 'overview' || two.querySelector('.dx-dist')) return;
    var slug = distSlug(), co = slug && window.dxDir && window.dxDir.bySlug && window.dxDir.bySlug(slug); if (!co || !(co.sectors || []).some(function (x) { return /Distribution/.test(x); })) return;
    var sec = two.querySelector('section.cp-sec'); if (!sec) return;
    var box = document.createElement('div'); box.className = 'dx-dist'; box.setAttribute('data-dist', slug); sec.appendChild(box);
    var member = !!document.querySelector('#content .cp-hero [data-hws]');
    svc().distributor(slug).then(function (p) { if (!box.isConnected) return;
      box.innerHTML = '<h3 style="margin-top:16px">Distributor profile</h3>' + (p ? '<div class="cap-forms">' + (p.govs || []).map(function (g) { return '<span class="lk">📍 ' + esc(lbl(g === 'all' ? 'all' : g) === 'all' ? GOV.all : lbl(g)) + '</span>'; }).join('') + (p.cats || []).map(function (c) { return '<span class="lk">' + esc(lbl(c)) + '</span>'; }).join('') + '</div>' +
        '<p class="cp-muted">' + esc([p.warehouses != null ? p.warehouses + ' warehouses' : '', p.fleet != null ? p.fleet + ' vehicles' : '', p.agencies != null ? p.agencies + ' agencies' : '', p.cold_chain ? 'Cold chain' : ''].filter(Boolean).join(' · ')) + '</p>'
        : '<p class="cp-muted">No distributor profile yet.</p>') + (member ? '<button type="button" class="dr-btn sm" data-dist-edit="1">Edit distributor profile</button>' : '');
      var e = box.querySelector('[data-dist-edit]'); if (e) e.addEventListener('click', function () { distEdit(slug, p || {}); });
    }, function () { box.remove(); });
  }
  function distEdit(slug, p) {
    var m = D.modal({ title: 'Distributor profile', body: '<div class="dx-tx" id="dxDistF">' + fChips('cats', 'Categories you carry', CATS) + fGov('govs', 'Governorates you cover (map)') +
      row3(fText('warehouses', 'Warehouses', '', false, '', 'number'), fText('fleet', 'Vehicles', '', false, '', 'number'), fText('agencies', 'Agencies you hold', '', false, '', 'number')) + fYesNo('cold_chain', 'Cold chain') + '</div>',
      primary: { label: 'Save', onClick: function (b) { var r = readTx(b.querySelector('#dxDistF')).attrs, out = { govs: r.govs || [], cats: r.cats || [], warehouses: r.warehouses != null ? r.warehouses : null, fleet: r.fleet != null ? r.fleet : null, agencies: r.agencies != null ? r.agencies : null, cold_chain: !!r.cold_chain };
        svc().saveDistributor(slug, out).then(function () { toast('Distributor profile saved'); var o = document.querySelector('.dx-dist'); if (o) o.remove(); paintDist(); }, function (er) { toast((er && er.message) || 'Could not save'); }); } } });
    var f = m.el.querySelector('#dxDistF');
    (p.cats || []).concat(p.govs || []).forEach(function (v) { var c = f.querySelector('.chip[data-v="' + v + '"]'); if (c) c.classList.add('selected'); });
    ['warehouses', 'fleet', 'agencies'].forEach(function (k) { var i = f.querySelector('[data-tx="' + k + '"] input'); if (i && p[k] != null) i.value = p[k]; });
    var cc = f.querySelector('[data-tx="cold_chain"] .radio-opt[data-v="' + (p.cold_chain ? 'yes' : 'no') + '"]'); if (cc) cc.classList.add('selected');
  }
  /* chips and yes/no in the profile window (outside #mkx) */
  document.addEventListener('click', function (e) { var c = e.target.closest && e.target.closest('#dxDistF .chip[data-v], #dxDistF .radio-opt[data-v]'); if (!c) return;
    if (c.classList.contains('radio-opt')) { c.parentElement.querySelectorAll('.radio-opt').forEach(function (x) { x.classList.remove('selected'); }); c.classList.add('selected'); return; }
    c.classList.toggle('selected'); var gv = c.closest('.dx-gov'); if (gv) { if (c.dataset.v === 'all' && c.classList.contains('selected')) gv.querySelectorAll('.chip[data-v]:not([data-v="all"])').forEach(function (x) { x.classList.remove('selected'); }); else if (c.dataset.v !== 'all') { var al = gv.querySelector('.chip[data-v="all"]'); if (al) al.classList.remove('selected'); } } });
  (function watchCompany() { var ct = document.getElementById('content'); if (!ct) return setTimeout(watchCompany, 500); new MutationObserver(function () { if (document.body.getAttribute('data-page') === 'companies') paintDist(); }).observe(ct, { childList: true }); })();

  /* ── search: every card in the marketplace carries its canonical words (approved cards too) ── */
  function words(card) {
    if (card.dataset.tradeId || card.querySelector(':scope > .dx-tq')) return;
    var t = card.textContent, sw = document.createElement('span'); sw.className = 'dx-tq'; sw.hidden = true; sw.setAttribute('data-noi18n', '');
    sw.textContent = searchWords({ title: t, desc: '', lines: [], attrs: {} }); card.appendChild(sw);
  }
  var CARDS = '.lcard, .dcard, .sponsored-card, .scard';
  new MutationObserver(function (muts) { var mk = document.getElementById('mkx'); if (!mk) return;
    muts.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType !== 1) return; if (n.matches && n.matches(CARDS) && n.closest('#mkx')) words(n); else if (n.querySelectorAll) n.querySelectorAll(CARDS).forEach(function (c) { if (c.closest('#mkx')) words(c); }); }); });
  }).observe(document.body, { childList: true, subtree: true });

  /* ── W-13: the Home composer's "🛒 Product" offers the ten trade templates; each opens Create Listing on its form ── */
  var TPL_ORDER = ['wanted', 'stock', 'file_sale', 'file_wanted', 'company_sale', 'agency', 'distributor', 'toll', 'toll_wanted', 'materials'];
  function openKind(kind) {
    var K = KIND[kind]; if (!K) return; if (document.body.getAttribute('data-page') !== 'market') window.goto('market');
    setTimeout(function () { inject(); if (window.switchMasterTab) window.switchMasterTab('create'); if (window.chooseIntent) window.chooseIntent(K.side === 'demand' ? 'seek' : 'offer');
      var pillT = kind === 'stock' || kind === 'materials' ? 'supply' : kind === 'wanted' ? 'demand' : kind === 'toll' ? 'cmo' : kind === 'file_sale' ? 'license' : kind;
      var pl = document.querySelector('#mkx .type-pill[data-type="' + pillT + '"]'); if (pl) pl.click();
      if (pillT === 'supply') { var r = document.querySelector('#form-supply [data-tx="_mode"] .radio-opt[data-v="' + kind + '"]'); if (r) r.click(); }
      var f = document.querySelector('#mkx .form-section.active .field-input'); if (f) f.focus(); }, 120);
  }
  /* the templates on Create Listing's first step (the composer's '🛒 Product' opens it — soc_nav.js) */
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('#mkx [data-tx-tpl]'); if (!b) return; e.preventDefault(); openKind(b.dataset.txTpl); });
  window.dxTrade = { decorate: decorate, openKind: openKind, parse: parseList, demoSvc: demoSvc, svc: svc, KIND: KIND, lbl: lbl, summary: summary, priceLabel: priceLabel, renewFailed: renewFailed, failed: failed, paint: function () { paintDemo(); paintMine(); },
    rowOf: null, gather: gather, STASH: function () { return STASH; }, clearStash: function () { STASH = null; }, govText: govText, CATS: CATS, GOVS: GOVS, GOV: GOV };
  C.onRender('trade', function () { if (document.body.getAttribute('data-page') === 'companies') paintDist(); if (document.body.getAttribute('data-page') !== 'market') return; inject(); paintPostAs(); var mk = document.getElementById('mkx'); if (mk) mk.querySelectorAll(CARDS).forEach(words); });

  /* ── Arabic: the trade's own words for the new labels (existing wording unchanged) ── */
  var AR = {
    'Available': 'متوفر', 'Raw materials': 'خامات', 'Wanted': 'مطلوب', 'Registration file': 'ملف تسجيل', 'File wanted': 'مطلوب ملف', 'Company for sale': 'شركة للبيع', 'Agency': 'وكالة', 'Distributor': 'موزّع', 'Toll capacity': 'سعة تول', 'Factory wanted': 'مطلوب مصنع',
    '📦 Available stock': '📦 متوفر', '⚗️ Raw materials': '⚗️ خامات وعبوات', '📋 File wanted': '📋 مطلوب ملف', '🏢 Company for sale': '🏢 شركة للبيع', '🤝 Agency': '🤝 وكالة', '🚚 Distributor': '🚚 موزّع بيدوّر على منتج', '🏭 Factory wanted': '🏭 مطلوب مصنع',
    'Available stock': 'متوفر', 'Raw materials & packaging': 'خامات وعبوات', 'Wanted item': 'مطلوب صنف', 'Registration file for sale': 'ملف تسجيل للبيع', 'Registration file wanted': 'مطلوب ملف تسجيل', 'Agency / distribution rights': 'فرصة وكالة / توزيع',
    'Distributor seeking products': 'موزّع بيدوّر على منتج', 'Toll manufacturing capacity': 'سعة تصنيع لدى الغير (تول)',
    'Stock lines between companies — one post, many items': 'أصناف متوفرة للتجارة بين الشركات — بوست واحد وأصناف كتير', 'APIs, excipients and packaging': 'مواد فعالة وسواغات وعبوات', 'Tell suppliers exactly what you need': 'قول للموردين محتاج إيه بالظبط',
    'A registration file and what comes with it': 'ملف تسجيل واللي داخل معاه', 'The file you are looking for and your conditions': 'الملف اللي بتدوّر عليه وشروطك', 'A company with its licences and files': 'شركة بتراخيصها وملفاتها',
    'Your products, looking for a distributor or agent': 'منتجاتك محتاجة موزّع أو وكيل', 'Your coverage, looking for products to carry': 'تغطيتك، وبتدوّر على منتجات توزّعها', 'Free capacity for manufacturing for others': 'سعة فاضية للتصنيع لدى الغير', 'The product you need manufactured': 'المنتج اللي محتاج تصنّعه',
    'What are you offering?': 'بتعرض إيه؟', '📦 Available stock (finished products)': '📦 متوفر (منتج تام)', '⚗️ Raw materials & packaging': '⚗️ خامات وعبوات', 'Items': 'الأصناف', 'Item': 'صنف', '＋ Add another item': '＋ ضيف صنف كمان', '📋 Paste your list': '📋 الزق قايمتك',
    'Name (Arabic and English), strength, quantity + unit, expiry, source, pack, fridge — one line per item': 'الاسم (عربي وإنجليزي)، التركيز، الكمية والوحدة، التاريخ، المصدر، حالة العلبة، ثلاجة — سطر لكل صنف',
    'Name (English or Arabic) *': 'الاسم (إنجليزي أو عربي) *', 'Strength (500 mg)': 'التركيز (500 مجم)', 'Dosage form': 'الشكل الصيدلي', 'Expiry': 'التاريخ', 'Quantity *': 'الكمية *', 'Price (optional)': 'السعر (اختياري)', 'Source': 'المصدر', 'Pack condition': 'حالة العلبة',
    '❄️ Fridge item': '❄️ ثلاجة', 'Discount %': 'خصم %', 'Remove item': 'شيل الصنف', 'Governorate': 'المحافظة', 'Delivery': 'التسليم', 'Pick-up from the seller': 'استلام من البايع', 'Delivered to the buyer': 'توصيل للمشتري', 'Shipping': 'شحن', 'By agreement': 'بالاتفاق',
    'Price': 'السعر', 'Ask for price': 'اسأل عن السعر', 'Discount % off the public price': 'خصم % من سعر الجمهور', 'Ask for price: buyers send a price request tied to this listing': 'اطلب سعر: المشتري يبعت طلب سعر مربوط بالإعلان',
    'Credit terms (days) — آجل': 'آجل (أيام)', 'e.g. 60 (empty = cash)': 'مثلاً 60 (فاضي = كاش)', 'Urgent': 'مستعجل', '⏱ Urgent': '⏱ مستعجل', 'Post as': 'انشر باسم', 'A company page posts offers as the company only with the Drugbox verification badge': 'صفحة الشركة تنشر عروض باسم الشركة بس لما تاخد شارة توثيق Drugbox',
    'Company': 'الشركة', 'Factory': 'فابريكة', 'Authority (tender)': 'هيئة (مناقصة)', 'Importer': 'مستورد', 'Sealed / intact': 'سليمة', 'Opened carton': 'كرتونة مفتوحة', 'Damaged pack': 'علبة تالفة', 'Repacked': 'معاد تغليفها',
    'Strength': 'التركيز', 'Needed by': 'مطلوب قبل', 'Dosage forms you make': 'الأشكال اللي بتصنّعها', 'Pack types': 'أنواع العبوات', 'Minimum batch': 'أقل تشغيلة', 'Lead time': 'مدة التسليم', 'Free months': 'الشهور الفاضية', 'Licensed by the authority': 'مرخّص من الهيئة',
    'Contract manufacturing for registration': 'عقد تصنيع للتسجيل', 'GMP': 'GMP', 'No GMP': 'لا يوجد GMP', 'GMP issued by': 'الـ GMP صادرة من', 'GMP date': 'تاريخ الـ GMP', 'Yes': 'أيوه', 'No': 'لأ',
    'Registration type': 'نوع التسجيل', 'Stage': 'المرحلة', 'Steps done (checklist)': 'الخطوات اللي خلصت', 'Registration decision issued': 'القرار صادر', 'Notification valid until': 'سريان الإخطار لحد', 'Public price per pack': 'سعر الجمهور للعبوة', 'Pack': 'العبوة',
    'Price increase': 'زيادة السعر', 'None': 'لا يوجد', 'Submitted': 'مقدَّمة', 'Approved': 'معتمدة', 'Asking price': 'السعر المطلوب', 'Commission': 'العمولة', 'Sales per year (units)': 'المبيعات في السنة (بالوحدة)', 'Buyer conditions': 'شروط المشتري',
    'Registration valid until': 'التسجيل ساري لحد', 'Who manufactures it': 'مين بيصنّعه', '🔒 Private box — only you, Drugbox and the members you share it with': '🔒 صندوق خاص — ليك ولـ Drugbox وللي تشاركه معاهم بس',
    'Notification number (رقم الإخطار)': 'رقم الإخطار', 'Registration / licence number': 'رقم التسجيل / الترخيص', 'The notification number stays here; share it with a serious buyer from My Listings': 'رقم الإخطار بيفضل هنا؛ شاركه مع مشتري جاد من إعلاناتي',
    'Documents for Drugbox (registration, notification)': 'مستندات لـ Drugbox (التسجيل، الإخطار)', 'Upload': 'ارفع', 'documents for Drugbox to check (PDF / photo, up to 6)': 'مستندات Drugbox تشوفها (PDF / صورة، لحد 6)',
    'Private: Drugbox checks them and the card shows “Documents seen by Drugbox”': 'خاصة: Drugbox بتشوفها والكارت يظهر عليه «مستندات اتشافت»', 'Documents seen by Drugbox': 'مستندات اتشافت', '📑 Documents seen by Drugbox': '📑 مستندات اتشافت',
    'Drugbox saw the documents; it does not guarantee the transfer — moving a registration needs the authority’s approval.': 'Drugbox شافت المستندات، ومش بتضمن نقل الملف — نقل التسجيل محتاج موافقة الهيئة.',
    'Human medicine': 'دواء بشري', 'Food supplement': 'مكمل غذائي', 'Cosmetic': 'مستحضر تجميل', 'Medical device': 'جهاز طبي', 'Veterinary': 'بيطري', 'Pricing': 'تسعير', 'Technical committee': 'لجنة فنية', 'Analysis': 'تحليل', 'Notification issued': 'إخطار صادر', 'Final registration': 'تسجيل نهائي',
    'Brand name': 'الاسم التجاري', 'Dossier': 'الملف', 'Studies (stability / BE)': 'الدراسات (ثبات / تكافؤ)', 'Artwork': 'التصميمات', 'Stock': 'البضاعة', 'Trademark': 'العلامة التجارية', 'Manufacturing rights': 'حق التصنيع',
    'Buyer has a factory': 'المشتري عنده مصنع', 'Toll manufacturing accepted': 'تول مقبول', 'Licensed warehouse': 'مخزن مرخّص', 'Companies only': 'شركات بس',
    'Registration file you are looking for': 'ملف التسجيل اللي بتدوّر عليه', 'Authority': 'الجهة', 'Earliest stage you accept': 'أقل مرحلة تقبلها', 'Any stage': 'أي مرحلة', 'Budget': 'الميزانية', 'Your conditions': 'شروطك',
    'Company type': 'نوع الشركة', 'Manufacturer': 'مصنع', 'Distributor / warehouse': 'موزّع / مخزن', 'Scientific office': 'مكتب علمي', 'Cosmetics': 'مستحضرات تجميل', 'Other': 'أخرى', 'Licensed': 'مرخّصة', 'Registered files': 'ملفات مسجّلة', 'Why it is for sale (optional)': 'سبب البيع (اختياري)',
    'Documents for Drugbox (commercial registry, licences)': 'مستندات لـ Drugbox (السجل التجاري، التراخيص)', 'Products / brand': 'المنتجات / البراند', 'Categories': 'الفئات', 'Governorates (map)': 'المحافظات (الخريطة)', 'Exclusive': 'حصري', 'Contract (years)': 'العقد (سنين)', 'Bonus %': 'البونص %', 'Target': 'التارجت',
    'Documents for Drugbox (registrations, authorisation)': 'مستندات لـ Drugbox (التسجيلات، التفويض)', 'What you are looking for': 'بتدوّر على إيه', 'Categories you carry': 'الفئات اللي بتوزّعها', 'Governorates you cover (map)': 'المحافظات اللي بتغطيها (الخريطة)',
    'Warehouses': 'المخازن', 'Vehicles': 'العربيات', 'Agencies you hold': 'الوكالات اللي معاك', 'Cold chain': 'سلسلة تبريد', 'Reach': 'الانتشار', 'Product to manufacture': 'المنتج المطلوب تصنيعه', 'Dosage forms': 'الأشكال الصيدلية', 'Batch size': 'حجم التشغيلة', 'Contract for registration': 'عقد للتسجيل',
    'Medicines': 'أدوية', 'Supplements': 'مكملات', 'Medical devices': 'مستلزمات طبية', 'Herbal': 'أعشاب', 'Baby care': 'رعاية أطفال', 'Hospital & tenders': 'مستشفيات ومناقصات', '🇪🇬 All Egypt': '🇪🇬 كل مصر', 'All Egypt': 'كل مصر',
    'Greater Cairo': 'القاهرة الكبرى', 'Alexandria & coast': 'إسكندرية والساحل', 'Delta': 'الدلتا', 'Canal & Sinai': 'القناة وسينا', 'Upper Egypt': 'الصعيد', 'Red Sea & desert': 'البحر الأحمر والصحرا',
    'Cairo': 'القاهرة', 'Giza': 'الجيزة', 'Qalyubia': 'القليوبية', 'Alexandria': 'الإسكندرية', 'Beheira': 'البحيرة', 'Matrouh': 'مطروح', 'Sharqia': 'الشرقية', 'Dakahlia': 'الدقهلية', 'Gharbia': 'الغربية', 'Monufia': 'المنوفية', 'Kafr El Sheikh': 'كفر الشيخ', 'Damietta': 'دمياط',
    'Port Said': 'بورسعيد', 'Ismailia': 'الإسماعيلية', 'Suez': 'السويس', 'North Sinai': 'شمال سيناء', 'South Sinai': 'جنوب سيناء', 'Faiyum': 'الفيوم', 'Beni Suef': 'بني سويف', 'Minya': 'المنيا', 'Asyut': 'أسيوط', 'Sohag': 'سوهاج', 'Qena': 'قنا', 'Luxor': 'الأقصر', 'Aswan': 'أسوان', 'Red Sea': 'البحر الأحمر', 'New Valley': 'الوادي الجديد',
    'Tablets': 'أقراص', 'Capsules': 'كبسول', 'Syrup': 'شراب', 'Suspension': 'معلق', 'Ampoules': 'أمبول', 'Vials': 'فيال', 'Suppositories': 'لبوس', 'Cream': 'كريم', 'Ointment': 'مرهم', 'Gel': 'جل', 'Drops': 'نقط', 'Spray': 'بخاخ', 'Sachets': 'أكياس', 'Effervescent': 'فوار', 'Powder': 'بودرة', 'Lotion': 'لوشن', 'Solution': 'محلول',
    'Blister': 'بليستر', 'Strip': 'شريط', 'Bottle': 'زجاجة', 'Tube': 'أنبوبة', 'Sachet': 'كيس', 'Vial': 'فيال', 'Ampoule': 'أمبول', 'Jar': 'برطمان', 'box': 'علبة', 'strip': 'شريط', 'carton': 'كرتونة', 'pack': 'عبوة', 'piece': 'قطعة', 'bottle': 'زجاجة', 'tube': 'أنبوبة', 'vial': 'فيال', 'ampoule': 'أمبول', 'litre': 'لتر', 'ton': 'طن', 'drum': 'برميل', 'bag': 'شيكارة',
    'Egypt': 'مصر', 'India': 'الهند', 'China': 'الصين', 'Germany': 'ألمانيا', 'France': 'فرنسا', 'Italy': 'إيطاليا', 'Spain': 'إسبانيا', 'United Kingdom': 'المملكة المتحدة', 'Switzerland': 'سويسرا', 'United States': 'الولايات المتحدة', 'Türkiye': 'تركيا', 'Jordan': 'الأردن', 'Saudi Arabia': 'السعودية', 'UAE': 'الإمارات', 'Korea': 'كوريا', 'Japan': 'اليابان',
    'EDA (Egypt)': 'هيئة الدواء المصرية', 'SFDA (Saudi)': 'SFDA (السعودية)', 'DHA (Dubai)': 'DHA (دبي)', 'MOHAP (UAE)': 'MOHAP (الإمارات)', 'JFDA (Jordan)': 'JFDA (الأردن)',
    '🔒 Reserved': '🔒 محجوز', '❄️ Fridge': '❄️ ثلاجة', 'Request the file': 'اطلب الملف', 'Offer your file': 'اعرض ملفك', 'Apply for the agency': 'قدّم على الوكالة', 'Offer your products': 'اعرض منتجاتك', 'Request capacity': 'اطلب السعة', 'Offer capacity': 'اعرض سعتك', 'File details': 'تفاصيل الملف',
    'Paste your list': 'الزق قايمتك', '📋 Paste your list': '📋 الزق قايمتك', 'Your list': 'قايمتك', 'Read the list': 'اقرا القايمة', 'Add the items': 'ضيف الأصناف', 'Cancel': 'إلغاء',
    'Copy the list from WhatsApp or a sheet and paste it here — one item per line. Chat headers (date, name) are removed. Check the items before adding them.': 'انسخ القايمة من واتساب أو شيت والزقها هنا — صنف في كل سطر. التاريخ واسم المرسل بيتشالوا. راجع الأصناف قبل ما تضيفها.',
    'Quantity you need': 'الكمية اللي محتاجها', 'Note': 'ملاحظة', 'Send price request': 'ابعت طلب السعر', 'Company to company it goes to Requests & deals as a quote request; otherwise to the seller’s Messages, naming the listing.': 'من شركة لشركة بيروح للطلبات والصفقات كطلب عرض سعر؛ غير كده بيروح لرسايل البايع باسم الإعلان.',
    'Message': 'الرسالة', 'Tell them who you are and what you propose': 'عرّفهم بنفسك وقول عرضك', 'Sent on behalf of the company you act as — follow it in Requests & deals.': 'بيتبعت باسم الشركة اللي بتتصرّف باسمها — تابعه في الطلبات والصفقات.',
    '🔒 Notification number': '🔒 رقم الإخطار', 'Notification number': 'رقم الإخطار', 'Decision issued': 'القرار صادر', 'Steps done': 'الخطوات اللي خلصت', 'Included': 'داخل في الصفقة', 'Submitted (not approved yet)': 'مقدَّمة (لسه متعتمدتش)',
    'You already posted this offer': 'العرض ده منشور قبل كده', 'Renew that one': 'جدّد القديم', 'Renewed this week already': 'اتجدّد الأسبوع ده', '⭐ Feature this listing': '⭐ ميّز إعلانك',
    '🔒 Reserved / sold': '🔒 محجوز / اتباع', '🔒 Mark reserved (محجوز)': '🔒 علّمه محجوز', '🔓 Open it again': '🔓 افتحه تاني', 'Sold to / bought from': 'اتباع لـ / اتشرى من', 'Someone outside Drugbox': 'حد برّه Drugbox', '✅ Mark sold (اتباع)': '✅ علّمه اتباع', 'Withdraw listing': 'اسحب الإعلان',
    'They are asked to confirm and rate; when both act for companies the sale counts in the company’s track record.': 'هيتطلب منه يأكّد ويقيّم؛ ولو الطرفين شركات البيعة بتتحسب في سجل الشركة.',
    '🎯 Matches for your listings': '🎯 المطابقات لإعلاناتك', 'View': 'اعرض', '🤝 Sales and purchases': '🤝 البيع والشراء', 'Sold / closed by you': 'اتباع / اتقفل منك', 'Named you': 'ذكرك', 'Waiting for confirmation': 'مستني التأكيد', 'Confirmed': 'اتأكد', 'Not confirmed': 'ماتأكدش', 'Closed': 'مقفول',
    'Confirm and rate': 'أكّد وقيّم', 'Rate them': 'قيّمه', 'Did this sale happen?': 'البيعة دي حصلت؟', 'Rate': 'قيّم', 'It did not happen': 'ماحصلتش', 'Rating (1–5)': 'التقييم (1–5)',
    'No matches yet — when someone posts what you need (or need what you have), it shows here and you are notified.': 'لسه مفيش مطابقات — لما حد ينشر اللي محتاجه (أو يطلب اللي عندك) هيظهر هنا وهيوصلك إشعار.',
    'Agency request': 'طلب وكالة', 'Open talks': 'ابدأ التفاوض', 'In talks': 'في تفاوض', 'Agree terms': 'اتفقنا', 'Tick every box before agreeing': 'علّم على كل البنود قبل «اتفقنا»',
    'I saw the notification number and its validity': 'شفت رقم الإخطار وسريانه', 'I understand the file’s stage and what is still missing': 'فاهم مرحلة الملف واللي لسه ناقص', 'I checked whether a price increase is submitted or approved': 'اتأكدت إن زيادة السعر مقدَّمة ولا معتمدة',
    'I know the transfer needs the authority’s approval': 'عارف إن نقل الملف محتاج موافقة الهيئة', 'I reviewed the documents shared in this deal': 'راجعت المستندات اللي اتشاركت في الصفقة',
    'e.g. 500 mg': 'مثلاً 500 مجم', 'e.g. 200,000 tablets': 'مثلاً 200,000 قرص', 'e.g. 6–8 weeks': 'مثلاً 6–8 أسابيع', 'e.g. EDA / WHO': 'مثلاً هيئة الدواء / WHO', 'e.g. Tablets': 'مثلاً أقراص', 'e.g. 85': 'مثلاً 85', 'e.g. 20 tablets': 'مثلاً 20 قرص',
    'e.g. EGP 400,000': 'مثلاً 400,000 ج.م', 'e.g. 2%': 'مثلاً 2%', 'e.g. 12345/2024': 'مثلاً 12345/2024', 'e.g. Paracetamol 500 mg tablets — EDA': 'مثلاً باراسيتامول 500 مجم أقراص — هيئة الدواء', 'e.g. up to EGP 500,000': 'مثلاً لحد 500,000 ج.م',
    'e.g. with stability studies, transfer within 6 months': 'مثلاً بدراسات الثبات، والنقل خلال 6 شهور', 'e.g. Scientific office with 12 registered files': 'مثلاً مكتب علمي بـ 12 ملف مسجّل', 'e.g. EGP 3,000,000': 'مثلاً 3,000,000 ج.م',
    'e.g. Our vitamin range (12 products)': 'مثلاً مجموعة الفيتامينات بتاعتنا (12 منتج)', 'e.g. 7': 'مثلاً 7', 'e.g. EGP 2 M / year': 'مثلاً 2 مليون ج.م / سنة', 'e.g. 90': 'مثلاً 90', 'e.g. Distributor in Upper Egypt looking for supplements': 'مثلاً موزّع في الصعيد بيدوّر على مكملات',
    'e.g. 1,200 accounts in 6 governorates': 'مثلاً 1,200 عميل في 6 محافظات', 'e.g. Ibuprofen 400 mg tablets': 'مثلاً ايبوبروفين 400 مجم أقراص', 'e.g. 100,000 tablets': 'مثلاً 100,000 قرص', 'e.g. 50 box': 'مثلاً 50 علبة', 'Delivery, payment terms…': 'التسليم، طريقة الدفع…',
    'Registration file you are looking for': 'ملف التسجيل اللي بتدوّر عليه', 'Edit distributor profile': 'عدّل بروفايل الموزّع', 'No distributor profile yet.': 'لسه مفيش بروفايل موزّع.', 'Distributor profile saved': 'اتحفظ بروفايل الموزّع',
    '🔒 Share the private box with them': '🔒 شارك الصندوق الخاص معاه', 'Choose the member to share it with': 'اختار العضو اللي هتشاركه', 'Before you agree — ': 'قبل «اتفقنا» — ', 'Ask for price': 'اسأل عن السعر',
    'Your listing is live': 'إعلانك اتنشر', 'Price request sent — the answer comes in Messages': 'طلب السعر اتبعت — الرد هيوصلك في الرسايل', 'Price request sent — follow it in Requests & deals': 'طلب السعر اتبعت — تابعه في الطلبات والصفقات',
    'Marked reserved — buyers see «Reserved»': 'اتعلّم محجوز — المشترين هيشوفوا «محجوز»', 'Open again': 'اتفتح تاني', 'Listing withdrawn': 'الإعلان اتسحب', 'Sent — follow it in Requests & deals': 'اتبعت — تابعه في الطلبات والصفقات',
    'Renewed — it moved up and shows for another 30 days': 'اتجدّد — طلع لفوق وهيفضل ظاهر 30 يوم كمان', 'Answered — it did not happen': 'اتسجّل إنها ماحصلتش',
    '📑 Trade documents': '📑 مستندات التجارة', '📦 Edit items': '📦 عدّل الأصناف', 'Items saved': 'الأصناف اتحفظت', 'Or start from a trade template': 'أو ابدأ من قالب تجارة', 'Trade between companies — each template opens its own form': 'تجارة بين الشركات — كل قالب بيفتح الفورم بتاعه', 'Factory wanted': 'مطلوب مصنع', 'Mark seen': 'اتشافت', 'Trade documents': 'مستندات التجارة', 'Distributor profile': 'بروفايل الموزّع'
  };
  if (window.dxI18nExtend) window.dxI18nExtend(AR, [
    [/^(\d+) items$/, function (m) { return m[1] + ' صنف'; }], [/^(\d+(?:\.\d+)?)% off$/, function (m) { return 'خصم ' + m[1] + '%'; }], [/^🗓 Credit (\d+) days$/, function (m) { return '🗓 آجل ' + m[1] + ' يوم'; }],
    [/^Before you agree — (.+)$/, function (m) { return 'قبل الموافقة — ' + m[1]; }], [/^(\d+) (listings? match(?:es)? it) — see My Listings → Matches$/, function (m) { return m[1] + ' إعلان مطابق — شوف إعلاناتي ← المطابقات'; }],
    [/^Your listing is live — (\d+) listings? match(?:es)? it \(My Listings → Matches\)$/, function (m) { return 'إعلانك اتنشر — ' + m[1] + ' إعلان مطابق (إعلاناتي ← المطابقات)'; }], [/^(\d+) items? added — add quantities where missing$/, function (m) { return 'اتضاف ' + m[1] + ' صنف — كمّل الكميات الناقصة'; }],
    [/^(\d+) items? found — untick any line that is not an item$/, function (m) { return m[1] + ' صنف — شيل العلامة من أي سطر مش صنف'; }], [/^Marked sold — (.+) is asked to confirm and rate$/, function (m) { return 'اتعلّم اتباع — هيتطلب من ' + m[1] + ' يأكّد ويقيّم'; }],
    [/^Shared with (.+)$/, function (m) { return 'اتشارك مع ' + m[1]; }], [/^Thank you — rated (\d)★$/, function (m) { return 'شكراً — قيّمت ' + m[1] + '★'; }], [/^(\d+) (?:items?|صنف) · (.+)$/, null],
    [/^Please fill: (.+)$/, function (m) { return 'كمّل: ' + m[1].split(', ').map(function (x) { return AR[x] || ({ Name: 'الاسم', 'Quantity of every item': 'كمية كل صنف', 'GMP issued by and date': 'جهة الـ GMP وتاريخها' })[x] || x; }).join('، '); }]
  ].filter(function (p) { return p[1]; }));
})();
