/* Groups — the inside of a group. Opening any group (every card, the side list, a link from another page) shows the approved group
   header and, under it, tabs built only from parts the app already has:
     Discussion  the Home composer and the Home post card (renderPost): pinned post first; like, react, comment, reply, share, save, report
     Members     the group page's member rows and role pills; Message / Connect; admins keep their tools (⋯)
     About       description, rules, type, privacy, created, admins
     Listings    deal rooms only: the marketplace's request card (RFQ) and offer card (sale / surplus)
   Not a member: a public group is a read-only preview with Join; a private group shows "Request to join" (pending) unless invited.
   Demo: sample content per group; what you write is kept in this browser (DBK.store 'groupData'), so it survives a reload.
   Live (window.dxLive): sample content never shows; data comes through window.dxLiveHook(kind, payload), kinds groupPosts, groupPost,
   groupMembers, groupJoin, groupListings, groupListing — a hook that returns undefined means "not supported yet" (contract: hand-over note). */
(function () {
  var C = window.dxCore, D = window.DBK; if (!C || !D) return;
  var esc = D.esc;
  function txt(el) { return el ? el.textContent.replace(/\s+/g, ' ').trim() : ''; }
  function otxt(el) { return el ? (window.dxOrigText ? window.dxOrigText(el) : el.textContent).replace(/\s+/g, ' ').trim() : ''; }   /* English original, whatever the language shown */
  function num(s) { var m = String(s || '').match(/[\d,]+/); return m ? parseInt(m[0].replace(/,/g, ''), 10) : 0; }
  function fmtN(n) { return (+n || 0).toLocaleString('en-US'); }
  function isLive() { return !!window.dxLive; }
  function hook(kind, d) { if (typeof window.dxLiveHook !== 'function') return undefined; try { return window.dxLiveHook(kind, d); } catch (e) { return Promise.reject(e); } }
  function slug(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9؀-ۿ]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'group'; }
  function me() { return window.ME || { id: 1, name: 'Me', initials: 'ME', color: '#1a56db' }; }
  function person(uid) { var u = (window.USERS || []).find(function (x) { return x.id === uid; }); return u || (uid === me().id ? me() : null); }
  function headline(u) { return u ? String(u.headline || '').split('|')[0].trim() : ''; }

  /* ───────────────────────── sample content (demo only) ───────────────────────── */
  function P(id, uid, cat, ts, likes, rx, cmt, sh, views, body, cm, pin) {
    return { id: id, uid: uid, cat: cat, ts: ts, likes: likes, rx: rx, cmt: cmt, sh: sh, views: views, body: body, pin: !!pin,
      cm: (cm || []).map(function (c) { return { uid: c[0], text: c[1], ts: c[2], likes: c[3] || 0 }; }) };
  }
  function R(id, kind, uid, t, d, x) { return Object.assign({ id: id, kind: kind, uid: uid, t: t, d: d }, x || {}); }
  var SEED = [
    { k: 'api', t: 'API Sourcing & Supply', by: 3, since: '2021-09-14', focus: ['APIs', 'Excipients', 'CEP / DMF', 'Price trends', 'Logistics'], markets: 'Egypt · GCC · Africa · China · India',
      about: 'A deal room for buyers and manufacturers of active pharmaceutical ingredients and key excipients serving Egypt, the GCC and Africa. Post RFQs, compare offers from documented sources, and share price and supply-chain intelligence. Every seller must be the manufacturer or an authorised agent.',
      rules: [['Documents first', 'Every offer names the manufacturer and shows its GMP certificate (WHO-GMP, EU-GMP or USFDA) and a recent CoA.'],
              ['Say who you are', 'Traders state whether they are the manufacturer or an authorised agent, and share the authorisation letter on request.'],
              ['RFQs and offers in Listings', 'Use the Listings tab so buyers can compare like for like; keep discussions in the feed.'],
              ['No counterfeit risk', 'Offers without documents are removed after one warning; repeat offenders leave the group.'],
              ['Respect confidentiality', 'Never post another company’s prices, contracts or DMF content without permission.']],
      mem: [[3, 'admin', 'Created the group'], [5, 'subadmin', 'Joined 3 years ago'], [7, 'member', 'Joined 2 years ago'], [1, 'member', 'Joined 2 years ago'], [2, 'member', 'Joined 1 year ago'], [4, 'member', 'Joined 8 months ago']],
      posts: [
        P(910101, 3, 'general', '2w ago', 86, { like: 60, insightful: 26 }, 9, 4, 2310, 'Welcome to the API Sourcing & Supply deal room 👋\n\nBefore you post:\n• Offers must show the manufacturer, the GMP certificate and a recent CoA\n• Traders: say if you are the manufacturer or an authorised agent\n• Put RFQs and offers in the Listings tab so buyers can compare\n\nUndocumented offers are removed after one warning. Let’s keep this room trusted.', null, 1),
        P(910102, 5, 'market', '2h ago', 34, { like: 22, insightful: 12 }, 5, 2, 640, 'Looking for a second source of Metformin HCl BP/USP (CEP holder) — about 6 MT per quarter for our 500/850/1000 mg lines.\n\nOur current supplier’s lead time slipped to 10 weeks. We need the DMF access letter and 3 recent CoAs. Quotes in the Listings tab or by message, please.',
          [[3, 'We hold a CEP for Metformin and can ship 6 MT from Qingdao in 3 weeks, CIF Alexandria. Sending the CoAs by message now.', '1h ago', 5], [7, 'Indovista can offer USFDA-DMF grade with 4 weeks lead time. Quote sent to your inbox.', '45m ago', 3]]),
        P(910103, 7, 'market', '5h ago', 112, { like: 70, insightful: 42 }, 17, 11, 3120, 'Q4 price update from India 📈\n\n• Paracetamol DC 90%: back to USD 4.20–4.60/kg FOB after the September spike\n• Azithromycin dihydrate: stable\n• Amoxicillin trihydrate: expect it to firm up in November (6-APA supply)\n\nPlan Q1 orders now — January capacity is filling fast.',
          [[5, 'Thanks — any view on Metformin for Q1?', '4h ago', 2]]),
        P(910104, 1, 'regulatory', '1d ago', 21, { like: 14, curious: 7 }, 3, 0, 410, 'Question for the group: has anyone completed an EDA variation for adding a second API source recently? How long did the biowaiver take for you?',
          [[2, 'For a BCS class III API with comparative dissolution in three media we had the waiver in about 7 weeks. Submit the open part of the DMF with the variation.', '20h ago', 6]]),
        P(910105, 3, 'market', '2d ago', 47, { like: 30, insightful: 17 }, 6, 9, 1280, 'Shipping note for buyers in Egypt 🚢\n\nEvery consignment now needs the ACID number on the invoice before loading in China. Send us your ACID early — missing numbers are causing 1–2 week delays at Alexandria.')],
      list: [
        R('L101', 'rfq', 5, 'Metformin HCl BP/USP — 6 MT per quarter', '📦 CEP + DMF access letter · 3 recent CoAs', { where: '🇪🇬 Egypt · 2h ago', badge: 'URGENT' }),
        R('L102', 'rfq', 1, 'Atorvastatin calcium — 300 kg', '📦 EU-GMP or USFDA · Form I', { where: '🇪🇬 Egypt · 1d ago', badge: 'OPEN' }),
        R('L103', 'sale', 3, 'Neomycin Sulfate EP — WHO-GMP', 'Potency ≥ 680 IU/mg. CEP available, 3 weeks to Alexandria.', { em: '⚗️', certs: ['CEP', 'WHO-GMP'], trust: ['✓ WHO-GMP', '✓ CEP'], price: '$118/kg', moq: 'MOQ: 25kg · 🇨🇳' }),
        R('L104', 'sale', 7, 'Paracetamol DC 90% — Direct Compression', 'USFDA-DMF site. 4 weeks lead time, FOB Mumbai.', { em: '💊', certs: ['USFDA DMF'], trust: ['✓ USFDA DMF', '📦 In stock'], price: '$4.40/kg', moq: 'MOQ: 1MT · 🇮🇳' }),
        R('L105', 'surplus', 5, 'Microcrystalline cellulose PH-102 — 750 kg', 'Sealed drums, batch MC-24-0911, expiry 03/2027. 30% below list.', { em: '♻️', certs: [], trust: ['✓ CoA', '📦 In stock'], price: '$2.40/kg', moq: 'MOQ: 100kg · 🇪🇬' })] },

    { k: 'reg', t: 'Regulatory Affairs Egypt', by: 1, since: '2022-02-08', me: 'admin', focus: ['EDA', 'CTD', 'Variations', 'Stability', 'Pricing', 'Pharmacovigilance'], markets: 'Egypt',
      about: 'For regulatory affairs professionals working with the Egyptian Drug Authority: registration and re-registration, variations, stability, pricing, pharmacovigilance and cosmetic notifications. Share what changed, ask what you are unsure about, and help colleagues file right the first time.',
      rules: [['Search before you ask', 'Many questions were answered before — search the group first.'],
              ['No confidential dossier content', 'Never post file numbers, assessment reports or another company’s data.'],
              ['Say the product type', 'Mark your post: human medicine, cosmetic, supplement or medical device.'],
              ['Cite your source', 'When you share a new rule, name the EDA decree or circular.'],
              ['Be kind to beginners', 'Everyone filed a first dossier once.']],
      mem: [[1, 'admin', 'Created the group'], [2, 'subadmin', 'Joined 4 months ago'], [6, 'member', 'Joined 1 year ago'], [4, 'member', 'Joined 9 months ago'], [5, 'member', 'Joined 3 months ago']],
      posts: [
        P(910201, 1, 'general', '1mo ago', 64, { like: 50, support: 14 }, 5, 2, 1880, 'Welcome to Regulatory Affairs Egypt 👋\n\nThis group is for EDA registration, variations, stability and pharmacovigilance questions. Three rules:\n1. Search before you ask\n2. Never share confidential dossier content or file numbers\n3. Mark your post with the product type — human, cosmetic, supplement or device', null, 1),
        P(910202, 2, 'regulatory', '3h ago', 156, { like: 98, insightful: 58 }, 21, 19, 4020, 'EDA e-submission reminder 📌\n\nThe portal now rejects CTD Module 3 PDFs that are not bookmarked to section level. Two of our files bounced last week. Check bookmarks and hyperlinks before you upload — it saves a 2-week resubmission.',
          [[6, 'Same for cosmetic notifications?', '2h ago', 3], [2, 'Not yet — cosmetics still go through the cosmetics department and the bookmark rule does not apply there.', '2h ago', 8]]),
        P(910203, 2, 'regulatory', '6h ago', 41, { like: 30, curious: 11 }, 11, 1, 980, 'سؤال للزملاء: حد قدّم Variation لتغيير مكان التصنيع بعد التعديلات الأخيرة؟\nالهيئة بقت بتطلب Process Validation لتلات تشغيلات قبل الموافقة، ولا البروتوكول لوحده بيكفي؟',
          [[5, 'إحنا قدّمنا الشهر اللي فات وطلبوا تلات تشغيلات كاملة + بيانات ثبات ٣ شهور accelerated.', '5h ago', 4]]),
        P(910204, 6, 'regulatory', '1d ago', 28, { like: 20, curious: 8 }, 9, 0, 760, 'Zone IVb stability for a cosmetic serum: has anyone had EDA accept 6 months accelerated + 6 months real-time with a commitment for the rest, or do they insist on 12 months real-time?'),
        P(910205, 4, 'regulatory', '3d ago', 37, { like: 25, insightful: 12 }, 4, 6, 1110, 'For teams filing in Egypt and Saudi Arabia in parallel: SFDA accepts the EDA GMP certificate as supporting evidence, but sterile products still need their own SFDA inspection. Plan 4–5 months for it.')],
      rep: [{ id: 'R201', kind: 'post', who: 'Unverified Seller (Khalid M.)', text: '“Ready-made CTD dossiers for any product — 50% off this week”', why: 'Selling dossiers that are not theirs — possible fraud', n: 3, ts: '2h ago' },
            { id: 'R202', kind: 'member', who: 'PharmaDeals99', text: 'Posted the same consultancy ad 4 times in 1 hour', why: '', n: 1, ts: '5h ago' }] },

    { k: 'gcc', t: 'GCC Market Access', by: 4, since: '2022-11-20', focus: ['SFDA', 'MOHAP', 'GHC', 'Pricing', 'Local agents'], markets: 'Saudi Arabia · UAE · Kuwait · Qatar · Bahrain · Oman',
      about: 'A private group for market-access and registration professionals covering the six GCC states: SFDA, MOHAP, DHA, DoH Abu Dhabi, QCHP, NHRA, OMSB and MOH Kuwait. Members share timelines, pricing outcomes and agent recommendations that are not public.',
      rules: [['What is shared here stays here', 'No screenshots or forwarding outside the group.'], ['Introduce yourself', 'Say which markets and product types you cover.'],
              ['Facts, not rumours', 'Say whether you saw a decision yourself or heard about it.'], ['No selling', 'Consultancy offers go in direct messages, not in posts.']],
      mem: [[4, 'admin', 'Created the group'], [2, 'member', 'Joined 1 year ago'], [1, 'member', 'Joined 1 year ago'], [7, 'member', 'Joined 6 months ago']],
      posts: [
        P(910301, 4, 'general', '3w ago', 22, { like: 22 }, 14, 0, 640, 'Members-only group 🔒\nMarket intelligence shared here stays here — no screenshots outside the group. Please introduce yourself with the markets and product types you cover.', null, 1),
        P(910302, 4, 'market', '4h ago', 58, { like: 31, insightful: 27 }, 9, 3, 870, 'SFDA pricing: the reference basket for new generics now covers 30 countries. Expect a first price 10–15% lower for files submitted after January.',
          [[1, 'Does that apply to files already under evaluation?', '3h ago', 2], [4, 'No — only new submissions. Files in evaluation keep the old basket.', '3h ago', 5]]),
        P(910303, 2, 'regulatory', '2d ago', 33, { like: 21, insightful: 12 }, 6, 0, 520, 'GCC centralised registration (GHC) is running at about 11 months for generics at the moment. Saudi Arabia on its own track is faster — about 8 months with priority review.'),
        P(910304, 1, 'market', '4d ago', 12, { like: 12 }, 5, 0, 300, 'Looking for a reliable local agent in Kuwait for 4 cosmetic SKUs. Recommendations welcome — message me.')] },

    { k: 'cmo', t: 'CMO & Contract Manufacturing', by: 5, since: '2022-06-01', focus: ['Tablets & capsules', 'Sterile', 'Cosmetics', 'Tech transfer', 'Audits'], markets: 'Egypt · GCC · Africa · India',
      about: 'Toll and contract manufacturing for Egypt and the region: capacity on offer, CMO requests, technology transfer and facility audits. Buyers post what they need (dosage form, batch size, annual volume, markets); manufacturers post free capacity with their GMP certificates.',
      rules: [['A complete request', 'Dosage form, batch size, annual volume, target markets and whether you need tech transfer.'], ['Show the site', 'Capacity offers state the site’s GMP certificates and its last inspection.'],
              ['Confidential terms', 'Prices and contract terms go in messages.']],
      mem: [[5, 'admin', 'Created the group'], [7, 'subadmin', 'Joined 2 years ago'], [6, 'member', 'Joined 1 year ago'], [3, 'member', 'Joined 5 months ago']],
      posts: [
        P(910401, 5, 'general', '1mo ago', 40, { like: 40 }, 3, 0, 1500, 'How to post a CMO request 📋\nDosage form · batch size · annual volume · target markets · tech-transfer support needed (yes/no).\nCapacity offers: state the site’s GMP certificates and the date of the last inspection.', null, 1),
        P(910402, 7, 'market', '6h ago', 64, { like: 40, insightful: 24 }, 8, 7, 1900, 'Capacity available from Q1 2027 🏭\n• Film-coated tablets: 40 million/month\n• Capsules: 8 million/month\nUSFDA + EU-GMP site in Ahmedabad. Our tech-transfer team supports EDA and SFDA dossiers.',
          [[6, 'Do you also do semisolids?', '5h ago', 1], [7, 'Not at this site — our Hyderabad plant does creams and gels. Happy to connect you.', '5h ago', 2]]),
        P(910403, 6, 'market', '1d ago', 19, { like: 19 }, 8, 0, 540, 'Looking for a CMO in Egypt for a cosmetic serum in 30 mL dropper bottles — 20,000 units first batch, ISO 22716 required. Filling and secondary packing only; we supply the bulk.'),
        P(910404, 5, 'market', '3d ago', 26, { like: 18, celebrate: 8 }, 5, 0, 690, 'Medsinia has a free slot on our new effervescent line from November: two shifts, humidity under 20% RH. Message me to arrange a site visit.')],
      list: [
        R('L401', 'rfq', 6, 'Cosmetic serum filling — 20,000 units', '📦 ISO 22716 · 30 mL dropper · bulk supplied', { where: '🇪🇬 Egypt · 1d ago', badge: 'OPEN' }),
        R('L402', 'sale', 7, 'Contract manufacturing — film-coated tablets', '40 million tablets/month from Q1 2027. USFDA + EU-GMP site.', { em: '🏭', certs: ['USFDA', 'EU-GMP'], trust: ['✓ USFDA', '✓ EU-GMP'], price: 'On request', moq: 'MOQ: 1M tablets · 🇮🇳' }),
        R('L403', 'sale', 5, 'Effervescent line — free slot from November', 'Two shifts, under 20% RH. Tablets and granules, EDA GMP certified.', { em: '💧', certs: ['EDA GMP'], trust: ['✓ EDA GMP'], price: 'On request', moq: 'MOQ: 50k units · 🇪🇬' })] },

    { k: 'qa', t: 'QA/QC Professionals', by: 2, since: '2021-05-10', focus: ['GMP audits', 'CAPA', 'OOS', 'Data integrity', 'Validation', 'HPLC'], markets: 'Egypt · MENA',
      about: 'Quality assurance and quality control in pharmaceutical and cosmetic plants: GMP audits, CAPA, deviations, OOS investigations, data integrity, validation and laboratory practice. Practical questions and templates, shared by people who do the work.',
      rules: [['Practical and specific', 'Describe the situation, not the company.'], ['Templates without company data', 'Remove names, batch numbers and logos before you share.'], ['No exam dumps', 'Training material yes, copied exam questions no.']],
      mem: [[2, 'admin', 'Created the group'], [5, 'subadmin', 'Joined 3 years ago'], [7, 'member', 'Joined 1 year ago'], [6, 'member', 'Joined 7 months ago']],
      posts: [
        P(910501, 5, 'general', '5h ago', 88, { like: 52, insightful: 36 }, 14, 12, 2100, 'CAPA tip 💡\nWhen an OOS is traced to analyst error, retraining alone is not an effective CAPA. Inspectors want to know why the error was possible: method clarity, system-suitability limits, workload, interruptions. Fix the system, not just the person.',
          [[2, 'Exactly. We added a second-person check for manual integration and the repeat errors stopped.', '4h ago', 9]]),
        P(910502, 7, 'innovation', '1d ago', 53, { like: 33, insightful: 20 }, 21, 8, 1400, 'Sharing our HPLC data-integrity checklist: audit-trail review frequency, user roles, orphan data, manual integration rules and system clocks. Comment “checklist” and we’ll send the template (no company data in it).'),
        P(910503, 2, 'regulatory', '2d ago', 24, { like: 24 }, 7, 0, 600, 'حد عنده SOP جاهز للـ Annual Product Review بيغطي متطلبات هيئة الدواء؟ محتاجة أقارن بالـ template بتاعنا قبل التفتيش الجاي.')] },

    { k: 'nutra', t: 'Nutraceuticals MENA', by: 6, since: '2025-07-01', focus: ['Formulation', 'NFSA', 'Health claims', 'Labelling', 'Sourcing'], markets: 'Egypt · GCC · North Africa',
      about: 'Food supplements and nutraceuticals across Egypt, the GCC and North Africa: formulation, NFSA and EDA classification, health claims, labelling and ingredient sourcing.',
      rules: [['Claims need evidence', 'Share the source for any health claim you post.'], ['Supplement or medicine?', 'Say how the product is classified in each market.'], ['No miracle products', 'Posts promising cures are removed.']],
      mem: [[6, 'admin', 'Created the group'], [4, 'member', 'Joined 2 months ago'], [3, 'member', 'Joined 1 month ago']],
      posts: [
        P(910601, 6, 'regulatory', '7h ago', 45, { like: 28, insightful: 17 }, 9, 5, 980, 'Classification watch 🇪🇬\nSupplements with more than 2,000 IU of vitamin D per daily dose are now treated as medicines in Egypt. Check your label claims and daily dose before renewal.'),
        P(910602, 4, 'regulatory', '2d ago', 18, { like: 18 }, 3, 0, 410, 'Saudi Arabia: SFDA updated its list of permitted health claims. “Supports normal immune function” is allowed only for vitamin C, zinc or vitamin D at 15% or more of the NRV per serving.')] },

    { k: 'pack', t: 'Packaging & Logistics Deal Room', by: 5, since: '2023-03-15', focus: ['Blister foil', 'Bottles', 'Cartons', 'Cold chain', 'Freight'], markets: 'Egypt · GCC · China',
      about: 'Primary and secondary packaging and logistics for pharma and cosmetics: blister foils, bottles, cartons, leaflets, cold chain and freight forwarding. Buyers post requests; suppliers and forwarders post offers and surplus stock.',
      rules: [['Specs in full', 'Material, dimensions, quantity, artwork status and delivery place.'], ['Pharma grade', 'State the certificates (DMF, ISO 15378, food contact) for primary packaging.'], ['Freight rates have a date', 'Always say when a rate was valid.']],
      mem: [[5, 'admin', 'Created the group'], [3, 'member', 'Joined 1 year ago'], [6, 'member', 'Joined 1 year ago']],
      posts: [
        P(910701, 5, 'market', '3h ago', 14, { like: 14 }, 6, 0, 380, 'Request: PVC/PVDC 250/60 blister film, 8 tons per month, delivered to 10th of Ramadan. ISO 15378 required. Offers in the Listings tab, please.'),
        P(910702, 3, 'market', '1d ago', 22, { like: 15, insightful: 7 }, 4, 3, 640, 'Cold-chain update ❄️ Reefer container rates Shanghai → Alexandria are down to about USD 4,900 this month. Book November space early — the pre-holiday rush starts in December.')],
      list: [
        R('L701', 'rfq', 5, 'PVC/PVDC 250/60 blister film — 8 MT/month', '📦 ISO 15378 · 10th of Ramadan delivery', { where: '🇪🇬 Egypt · 3h ago', badge: 'URGENT' }),
        R('L702', 'surplus', 6, 'Airless bottles 30 mL (white) — 18,000 pcs', 'Surplus after a design change. Unused, in original cartons.', { em: '🧴', certs: [], trust: ['📦 In stock', '✓ 45% off'], price: 'EGP 4.10/pc', moq: 'MOQ: 2,000 pcs · 🇪🇬' }),
        R('L703', 'surplus', 1, 'Printed cartons — Hair Serum (old artwork) — 9,500 pcs', 'Old artwork, fine for samples and export packs.', { em: '📦', certs: [], trust: ['📦 In stock', '✓ 70% off'], price: 'EGP 0.60/pc', moq: 'MOQ: 1,000 pcs · 🇪🇬' })] },

    { k: 'careers', t: 'Careers & Training Egypt', by: 2, since: '2020-10-01', focus: ['Jobs', 'Internships', 'GMP training', 'CV advice'], markets: 'Egypt',
      about: 'Jobs, internships, GMP training and career advice for pharmacists, chemists and engineers in Egypt. Employers post openings, trainers post courses, and experienced members answer career questions.',
      rules: [['Real openings only', 'Job posts name the company or the recruiter.'], ['No fees for jobs', 'Any request for money in exchange for a job is removed.'], ['Courses: say who accredits them', 'State the certificate and the accrediting body.']],
      mem: [[2, 'admin', 'Created the group'], [5, 'member', 'Joined 2 years ago'], [6, 'member', 'Joined 1 year ago']],
      posts: [
        P(910801, 2, 'general', '4h ago', 72, { like: 50, celebrate: 22 }, 26, 15, 2600, 'Free webinar on Thursday at 8 pm (Cairo time): “Writing a CTD Module 3 that passes first time”. Register from the Training page — the recording goes to registered members only.'),
        P(910802, 5, 'job', '1d ago', 39, { like: 39 }, 18, 9, 1700, 'We’re hiring 3 production supervisors (solid dosage forms) at our plant in 10th of Ramadan. 5+ years’ experience and solid GMP knowledge. Apply from the Jobs page.'),
        P(910803, 6, 'general', '2d ago', 95, { like: 60, support: 35 }, 31, 20, 3300, 'نصيحة للخريجين الجدد 💡\nكورس GMP أساسي + تدريب عملي على HPLC بيفرقوا جدًا في الإنترفيو. ابدأوا بالتدريب الصيفي في المصانع حتى لو من غير مرتب — الخبرة دي بتختصر عليكم سنة.')] },

    { k: 'devices', t: 'Medical Devices Egypt', by: 4, since: '2026-04-01', focus: ['EDA devices', 'Distribution', 'Clinical evaluation', 'Tenders'], markets: 'Egypt',
      about: 'Medical device registration, distribution and clinical evaluation in Egypt. Manufacturers find distributors, distributors find products, and regulatory specialists explain the EDA device rules.',
      rules: [['State the class', 'Say the device class (I, IIa, IIb, III) in every post.'], ['Distributors: say where you cover', 'Governorates and hospital segments.'], ['No used devices', 'Refurbished or used devices are not allowed in Listings.']],
      mem: [[4, 'admin', 'Created the group'], [2, 'member', 'Joined 3 months ago']],
      posts: [
        P(910901, 4, 'regulatory', '8h ago', 17, { like: 17 }, 4, 0, 420, 'EDA device files: class IIb devices now need a clinical evaluation report structured like the EU MDR one. Distributors — check that your manufacturers’ technical files are up to date before renewal.'),
        P(910902, 2, 'market', '2d ago', 11, { like: 11 }, 6, 0, 300, 'Looking for an Egyptian distributor for a CE-marked advanced wound-dressing range (class IIa) — hospital and pharmacy channels.')],
      list: [R('L901', 'rfq', 2, 'Distributor for CE-marked wound dressings (class IIa)', '📋 Hospital + pharmacy channels', { where: '🇪🇬 Egypt · 2d ago', badge: 'OPEN' })] },

    { k: 'cosmetics', t: 'Cosmetics Formulators', by: 6, since: '2023-01-12', focus: ['Skincare', 'Haircare', 'Actives', 'Challenge test', 'EDA notification'], markets: 'Egypt · GCC',
      card: { emoji: '💄', bg: 'linear-gradient(135deg,#be185d,#f472b6)', desc: 'Skincare & haircare formulation, actives sourcing and EDA cosmetic notification.', count: 760, faces: [['SE', '#d97706']], signal: 'Quiet today' },
      about: 'Skincare, haircare and personal-care formulation: actives and their suppliers, stability and challenge testing, claims and EDA cosmetic notification. For formulators, R&D managers and the suppliers who work with them.',
      rules: [['Formulas stay yours', 'Share percentages only if you want to — never someone else’s formula.'], ['Use INCI names', 'So everyone can follow which ingredient you mean.'], ['Suppliers: help, don’t spam', 'Answer questions; offers go in messages.']],
      mem: [[6, 'admin', 'Created the group'], [1, 'member', 'Joined 2 years ago'], [2, 'member', 'Joined 1 year ago'], [3, 'member', 'Joined 6 months ago']],
      posts: [
        P(911001, 6, 'regulatory', '1d ago', 31, { like: 20, insightful: 11 }, 7, 4, 820, '“Preservative-free” claims: EDA now asks for the ISO 11930 challenge-test report for any product labelled preservative-free. Plan the test before you print the cartons.'),
        P(911002, 1, 'innovation', '3d ago', 58, { like: 30, celebrate: 28 }, 11, 0, 1500, 'Our Shaft Hair Serum line passed process validation 🎉 Thank you to everyone here who helped with the stability protocol and the packaging-compatibility questions.',
          [[6, 'Congratulations! Well deserved.', '3d ago', 4]]),
        P(911003, 6, 'general', '5d ago', 15, { like: 15 }, 9, 0, 400, 'مين جرّب Niacinamide من مورد صيني جديد؟ عايزة أعرف ثبات اللون والريحة بعد ٣ شهور في الـ serum.')] },

    /* a private group you are not in (Request to join) and a private group you were invited to (Accept invitation) */
    { k: 'pv', t: 'Pharmacovigilance Egypt', by: 2, since: '2024-02-20', focus: ['QPPV', 'PSUR / PBRER', 'Signal detection', 'EDA inspections', 'RMP'], markets: 'Egypt',
      card: { emoji: '🩺', bg: 'linear-gradient(135deg,#0f766e,#2dd4bf)', desc: 'QPPVs and drug-safety teams: signals, PSURs, risk management plans and EDA pharmacovigilance inspections.', count: 410, faces: [['AM', '#7c3aed']], signal: '4 new posts this week', joined: false, priv: true, grid: 1 },
      about: 'A closed group for qualified persons for pharmacovigilance (QPPVs), their deputies and drug-safety teams in Egypt. Members compare notes on signal management, PSUR/PBRER timelines, risk management plans and what EDA inspectors ask for. Membership is reviewed so that case details can be discussed safely.',
      rules: [['No patient data', 'Never post anything that could identify a patient or a reporter.'], ['Say your role', 'Admins approve QPPVs, deputies and safety staff; tell us your role when you ask to join.'], ['Inspection findings stay anonymous', 'Share what was asked, never which company was inspected.']],
      mem: [[2, 'admin', 'Created the group'], [6, 'member', 'Joined 1 year ago'], [5, 'member', 'Joined 6 months ago']],
      posts: [
        P(911101, 2, 'regulatory', '1d ago', 26, { like: 16, insightful: 10 }, 7, 0, 390, 'EDA PV inspections this quarter focused on the PSMF annexes: list of local literature sources, the backup QPPV arrangement and evidence of reconciliation with the call centre. Check yours are current.', null, 1),
        P(911102, 6, 'regulatory', '3d ago', 12, { like: 12 }, 4, 0, 260, 'For a cosmetic with a serious adverse event report: does it go to the EDA PV centre or to the cosmetics department? We had conflicting answers.',
          [[2, 'Serious events for cosmetics go to the cosmetics vigilance unit — the PV centre forwards them, but it costs you two weeks.', '2d ago', 3]])] },
    { k: 'sterile', t: 'Sterile Manufacturing Leaders', by: 5, since: '2023-09-05', inv: 2, focus: ['Annex 1', 'Media fills', 'Isolators', 'Environmental monitoring', 'Lyophilisation'], markets: 'Egypt · GCC · Africa',
      card: { emoji: '💉', bg: 'linear-gradient(135deg,#334155,#64748b)', desc: 'Aseptic processing, EU GMP Annex 1, media fills and sterile line investments — plant and QA leaders.', count: 260, faces: [['OK', '#16a34a'], ['AM', '#7c3aed']], signal: 'Invitation only', joined: false, priv: true, grid: 1 },
      about: 'An invitation-only group for heads of sterile production, QA and engineering. Topics: Annex 1 contamination control strategies, media-fill failures and investigations, isolator versus RABS decisions, environmental monitoring trends and new filling-line projects.',
      rules: [['Invitation only', 'Members invite peers who run or audit sterile operations.'], ['Blame-free', 'Investigations are shared to learn, not to judge.'], ['No vendor pitches', 'Suppliers may answer questions; offers go in messages.']],
      mem: [[5, 'admin', 'Created the group'], [2, 'subadmin', 'Joined 2 years ago'], [7, 'member', 'Joined 1 year ago']],
      posts: [
        P(911201, 5, 'regulatory', '6h ago', 31, { like: 19, insightful: 12 }, 8, 2, 480, 'Annex 1 gap assessment done for our vial line. The biggest gaps were not the cleanroom — they were the contamination control strategy document and the glove-integrity testing frequency. Happy to share our CCS outline with members.'),
        P(911202, 7, 'innovation', '2d ago', 22, { like: 14, insightful: 8 }, 5, 0, 350, 'Isolator or RABS for a new 6,000 vials/hour line? We went isolator: higher capex, but grade C background and far fewer interventions. Payback came from fewer EM excursions.')] }
  ];
  var BY_KEY = {}, BY_TITLE = {};
  SEED.forEach(function (s) { BY_KEY[s.k] = s; BY_TITLE[s.t] = s.k; });
  var NEW_RULES = [['Be respectful', 'Disagree with ideas, never with people.'], ['Stay on topic', 'Posts should match what the group is about.'], ['No spam', 'No unrelated ads or repeated posts.']];

  /* ───────────────────────── what you did (demo, this browser) ───────────────────────── */
  function blank() { return { v: 1, posts: {}, ed: {}, req: {}, rep: {}, lst: {}, quotes: {}, made: [], ov: {}, roles: {}, gone: {}, arch: {}, del: {}, notif: {}, closedL: {}, reqs: {}, noinv: {} }; }
  var S = null;
  function st() {
    if (S) return S;
    var s = null; try { s = D.store.get('groupData', null); } catch (e) {}
    S = s && typeof s === 'object' && s.v === 1 ? s : blank();
    var b = blank(); for (var k in b) if (!(k in S) || typeof S[k] !== typeof b[k]) S[k] = b[k];
    return S;
  }
  function save() {
    if (isLive()) return;
    var s = st(), json = '';
    try { json = JSON.stringify(s); } catch (e) { return; }
    if (json.length > 3500000) {   /* photos are the heavy part: keep the text, drop the oldest photos until it fits this browser's storage */
      Object.keys(s.posts).forEach(function (k) { s.posts[k].slice().reverse().forEach(function (p) { if (json.length > 3500000 && p.imgs && p.imgs.length) { p.imgs = []; p.imgsDropped = 1; json = JSON.stringify(s); } }); });
    }
    D.store.set('groupData', s);
  }
  function ls(k, v) { try { if (v === undefined) { var x = JSON.parse(localStorage.getItem('dx_' + k) || 'null'); return Array.isArray(x) ? x : []; } localStorage.setItem('dx_' + k, JSON.stringify(v)); } catch (e) { return []; } }

  /* ───────────────────────── the group behind a card ───────────────────────── */
  var CUR = null, LAST_CARD = null, OPEN_ARGS = null;
  function cards() { return Array.prototype.slice.call(document.querySelectorAll('#gx .gcard')); }
  function cardKey(card) {
    if (!card) return null;
    if (card.dataset.gid) return 'g' + card.dataset.gid;
    if (card.dataset.gk) return card.dataset.gk;
    var t = otxt(card.querySelector('.gcard-title')); return BY_TITLE[t] || 'u-' + slug(t);
  }
  function cardByKey(k) { return cards().find(function (c) { return cardKey(c) === k; }) || null; }
  function cardByTitle(t) { return cards().find(function (c) { return otxt(c.querySelector('.gcard-title')) === t; }) || null; }
  function cardJoined(card) { var b = card && card.querySelector('.gcard-btn'); return !!(b && b.classList.contains('btn-joined') && !b.dataset.gpq); }   /* gpq: Requested looks pressed but is not membership */
  function model(card, role) {
    var key = cardKey(card), seed = isLive() || card.dataset.gid ? null : BY_KEY[key] || null, made = st().made.find(function (m) { return m.k === key; }) || null;
    var cover = card.querySelector('.gcard-cover'), tag = card.querySelector('.gcard-meta .gtag');
    var member = cardJoined(card), title = otxt(card.querySelector('.gcard-title'));
    var g = { key: key, gid: card.dataset.gid ? +card.dataset.gid : null, card: card, title: title, desc: otxt(card.querySelector('.gcard-desc')),
      emoji: cover ? Array.from(txt(cover)).slice(0, 2).join('').trim() : '👥', bg: cover ? cover.style.background : '',
      deal: tag ? /deal/i.test(otxt(tag)) : false, priv: /private/i.test(otxt(card.querySelector('.gcard-meta'))), member: member,
      count: num(otxt(card.querySelector('.member-count'))), seed: seed, made: made, live: !!card.dataset.gid || isLive() };
    var mine = seed && seed.me ? seed.me : made ? 'admin' : (card.getAttribute('onclick') || '').indexOf('admin') >= 0 ? 'admin' : 'member';
    g.role = member ? (g.live ? (role === 'admin' ? 'admin' : 'member') : (st().roles[key] && st().roles[key][me().id]) || mine) : null;
    var cb = card.querySelector('.gcard-btn');
    g.pending = !member && (g.live ? !!(cb && cb.dataset.gpq === 'pending') : !!st().req[key]);   /* live: the adapter paints the card from group_join_requests */
    g.invited = !member && (g.live ? card.dataset.invited === '1' : !!(seed && seed.inv) && !(st().noinv || {})[g.key]);
    g.since = seed ? seed.since : made ? made.at : null;
    g.by = seed ? seed.by : made ? me().id : null;
    g.about = seed ? seed.about : g.desc;
    g.rules = seed ? seed.rules : made && made.rules ? made.rules.split(/\n+/).map(function (l) { l = l.trim(); var m = /^(.{1,80}?)\s*(?:—|:|–)\s+(.+)$/.exec(l); return m ? [m[1], m[2]] : [l, '']; }).filter(function (r) { return r[0]; }) : NEW_RULES;
    g.focus = seed ? seed.focus : [];
    g.markets = seed ? seed.markets : '';
    var ovr = !g.live && st().ov[key];
    if (ovr) { if (ovr.d != null) g.about = ovr.d; if (ovr.rules) g.rules = ovr.rules; if (ovr.priv != null) g.priv = ovr.priv; }
    g.muted = card.dataset.muted === '1';
    if (g.live) {   /* live: the adapter puts the group's own about, rules, creation date and creator on its card */
      var dz = card.dataset; g.about = dz.about || g.desc; g.since = dz.since || null; g.by = +dz.by || null;
      try { g.rules = dz.rules ? JSON.parse(dz.rules) : []; } catch (e) { g.rules = []; }
    }
    var cd = card.dataset; tagCard(card);
    g.sector = cd.sector || inferSector(title + ' ' + g.desc); g.country = (cd.country || '').split(',').filter(Boolean);
    g.postPolicy = cd.post === 'admins' ? 'admins' : 'members'; g.archived = cd.archived === '1';
    g.admin = g.role === 'admin' || g.role === 'subadmin' || g.role === 'moderator';
    g.canSee = g.member || !g.priv;   /* private: only members see posts, members and listings */
    return g;
  }

  /* ───────────────────────── posts ───────────────────────── */
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function seedPost(p) { var x = clone(p); x.rx = x.rx || {}; x.liked = false; x.rk = null; x.saved = false; x.own = false; return x; }
  function demoPosts(g) {
    var s = st(), out = [];
    (s.posts[g.key] || []).forEach(function (p) { if (!p.del) out.push(p); });
    ((g.seed && g.seed.posts) || []).forEach(function (p) { var e = s.ed[p.id]; var x = e ? e : seedPost(p); if (!x.del) out.push(x); });
    return out;
  }
  function order(list) { return list.map(function (p, i) { return [p, i]; }).sort(function (a, b) { return (b[0].pin ? 1 : 0) - (a[0].pin ? 1 : 0) || a[1] - b[1]; }).map(function (x) { return x[0]; }); }
  function persist(g, p) {   /* demo: your own posts are stored whole; a sample post keeps a copy with your changes */
    if (g.live) return;
    var s = st();
    if (p.own) { var l = s.posts[g.key] = s.posts[g.key] || []; var i = l.findIndex(function (x) { return x.id === p.id; }); if (i >= 0) l[i] = p; else l.unshift(p); }
    else s.ed[p.id] = p;
    save();
  }
  function liveCall(kind, d, onFail) {   /* live: hand the change to the adapter; undo it on screen if the server refuses */
    var r = hook(kind, d); if (!r || typeof r.then !== 'function') return r;
    r.then(null, function (e) { if (onFail) onFail(e); D.toast((window.dxLive && window.dxLive.friendly ? window.dxLive.friendly(e) : (e && e.message)) || 'Could not save — try again'); });
    return r;
  }
  function commit(g, p, op, extra) {
    if (g.live) liveCall('groupPost', Object.assign({ group: pub(g), op: op, post: p }, extra || {}), function () { loadPosts(g, true); });
    else persist(g, p);
  }
  function pub(g) { return { key: g.key, gid: g.gid, title: g.title, deal: g.deal, priv: g.priv, role: g.role, member: g.member }; }
  function postHtml(p) {
    var cmts = (p.cm || []).map(function (c) { return { uid: c.uid, text: c.text, ts: c.ts, likes: c.likes || 0 }; });
    var had = Object.prototype.hasOwnProperty.call(window.COMMENTS || {}, p.id), keep = had ? window.COMMENTS[p.id] : null, html = '';
    if (window.COMMENTS) window.COMMENTS[p.id] = cmts;   /* renderPost reads a post's comments from COMMENTS: lent for this one call */
    try {
      html = window.renderPost({ id: p.id, uid: p.uid, cat: p.cat || 'general', body: p.body || '', likeCount: p.likes || 0, liked: !!p.liked, commentCount: p.cmt || 0,
        shareCount: p.sh || 0, viewCount: p.views || 0, saved: !!p.saved, pinned: !!p.pin, ts: p.ts || 'just now', imgs: p.imgs || [], files: p.files || [], reactions: p.rx || {} });
    } finally { if (window.COMMENTS) { if (had) window.COMMENTS[p.id] = keep; else delete window.COMMENTS[p.id]; } }
    return html;
  }
  /* the card's own buttons run the Home feed's functions (which only know Home posts): here they get a name and our handler instead */
  var MARK = [[/Edit coming soon/, 'edit'], [/Reported!/, 'report'], [/Link copied!/, 'link'], [/Reposted!/, 'share'], [/Saved!/, 'save'], [/Liked!/, 'clike'], [/Reply coming soon/, 'reply'],
              [/deletePost/, 'delete'], [/expandPost/, 'more'], [/submitComment/, 'send'], [/toggleComments/, 'cmts'], [/doReact/, 'react'], [/showReactors/, 'reactors']];
  function stamp(el, p, g) {
    el.querySelectorAll('[onclick],[onkeydown]').forEach(function (x) {
      var oc = x.getAttribute('onclick') || x.getAttribute('onkeydown') || '';
      if (x.tagName === 'INPUT') { if (/submitComment/.test(oc)) x.removeAttribute('onkeydown'); return; }   /* Enter in the comment box: our keydown handler */
      for (var i = 0; i < MARK.length; i++) if (MARK[i][0].test(oc)) {
        x.setAttribute('data-gpm', MARK[i][1]); x.removeAttribute('onclick'); x.removeAttribute('onkeydown');
        if (x.tagName !== 'BUTTON' && x.tagName !== 'INPUT') { x.setAttribute('role', 'button'); if (!x.hasAttribute('tabindex')) x.setAttribute('tabindex', '0'); }
        break;
      }
    });
    var like = el.querySelector('.pact[id^="like-"]'); if (like) { like.setAttribute('tabindex', '0'); like.setAttribute('aria-pressed', p.liked ? 'true' : 'false'); }
    var menu = el.querySelector('[id^="pm-"]');
    if (menu && g.admin) {   /* admins: pin, and remove posts that break the rules */
      menu.insertAdjacentHTML('afterbegin', '<div class="ctx-item" data-gpm="pin" role="button" tabindex="0">' + (p.pin ? '📌 Unpin' : '📌 Pin to top') + '</div>' +
        (p.uid !== me().id ? '<div class="ctx-item ctx-danger" data-gpm="remove" role="button" tabindex="0">🗑 Remove post</div>' : ''));
    }
    if (p.saved) { var sv = el.querySelector('.post-acts [data-gpm="save"]'); if (sv) sv.classList.add('dbk-saved'); }
    el.querySelectorAll('.cmt-box .cmt').forEach(function (cm, i) {   /* my comment, any comment on my post, any comment for the group's admins */
      var c = (p.cm || [])[i]; if (!c || (c.uid !== me().id && p.uid !== me().id && !g.admin)) return;
      var rp = cm.querySelector('[data-gpm="reply"]'), host = rp ? rp.parentNode : (cm.querySelector('.cmt-bubble') || cm);
      host.insertAdjacentHTML('beforeend', ' <button type="button" class="cmt-del" data-gpm="cdel" aria-label="Delete comment">Delete</button>');
    });
    if (p.edited) { var b = el.querySelector('.post-body'); if (b) b.insertAdjacentHTML('beforeend', '<span class="gp-edited"> · edited</span>'); }
    if (p.imgsDropped) { var pb = el.querySelector('.post-body'); if (pb) pb.insertAdjacentHTML('afterend', '<div class="gp-note">The photo was too large to keep in this browser.</div>'); }
    el.querySelectorAll('.post-files .file-chip').forEach(function (fc, i) {   /* an attached file opens (live: its stored link) */
      var f = (p.files || [])[i]; if (!f) return; fc.dataset.gpf = i; fc.setAttribute('role', 'button'); fc.setAttribute('tabindex', '0'); fc.style.cursor = 'pointer';
      if (f.url) fc.dataset.url = f.url;
    });
    el.setAttribute('data-gpp', p.id);
    return el;
  }
  function postEl(p, g) { var t = document.createElement('div'); t.innerHTML = postHtml(p); return stamp(t.firstElementChild, p, g); }
  function findPost(id) { return CUR && CUR.posts ? CUR.posts.find(function (p) { return p.id === id; }) : null; }
  function repaint(p) {
    var old = document.querySelector('#gpBox [data-gpp="' + p.id + '"]'); if (!old || !CUR) return;
    var box = old.querySelector('[id^="cmt-"]'), open = box && box.style.display !== 'none';
    var nu = postEl(p, CUR.g); old.replaceWith(nu); adopt(nu);
    if (open) { var b2 = nu.querySelector('[id^="cmt-"]'); if (b2) b2.style.display = 'block'; }
    return nu;
  }

  /* ───────────────────────── borrowed styles ─────────────────────────
     The group page resets every element inside it (#gx *{margin:0;padding:0}), which would flatten the Home post card, and the
     marketplace cards are styled only inside the marketplace (#mkx …). The same rules are copied once, scoped to the group's inside:
     post-card rules get one more id (so they outrank the reset exactly where they applied before), marketplace rules move from #mkx to it. */
  var ADOPTED = {}, adoptEl = null, ADOPT_PROPS = /^(margin|padding|font-family|box-sizing)/;
  var PSEUDO = /((?:::?(?:before|after|placeholder|selection|marker|first-line|first-letter|backdrop|-webkit-[\w-]+|-moz-[\w-]+))+)$/;
  function splitSel(s) { var out = [], d = 0, cur = ''; for (var i = 0; i < s.length; i++) { var ch = s[i]; if (ch === '(') d++; else if (ch === ')') d--; if (ch === ',' && !d) { out.push(cur); cur = ''; } else cur += ch; } out.push(cur); return out.map(function (x) { return x.trim(); }).filter(Boolean); }
  function reEsc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function adopt(root) {
    if (!root || !root.querySelectorAll) return;
    var fresh = false, all = [root].concat(Array.prototype.slice.call(root.querySelectorAll('[class]')));
    all.forEach(function (e) { var c = typeof e.className === 'string' ? e.className : (e.getAttribute && e.getAttribute('class')) || ''; c.split(/\s+/).forEach(function (k) { if (k && !ADOPTED[k]) { ADOPTED[k] = 1; fresh = true; } }); });
    if (!fresh) return;
    var keys = Object.keys(ADOPTED); if (!keys.length) return;
    var re = new RegExp('\\.(?:' + keys.map(reEsc).join('|') + ')(?![\\w-])'), MK = /#mkx(?![\w-])/;
    if (!adoptEl) { adoptEl = document.createElement('style'); adoptEl.id = 'gpAdopted'; document.head.appendChild(adoptEl); }
    function decl(style, every) {
      var out = ''; for (var i = 0; i < style.length; i++) { var n = style[i]; if (!every && !ADOPT_PROPS.test(n)) continue; out += n + ':' + style.getPropertyValue(n) + (style.getPropertyPriority(n) ? ' !important' : '') + ';'; }
      return out;
    }
    function walk(rules, into) {
      for (var i = 0; i < rules.length; i++) {
        var r = rules[i];
        if (r.type === 1) {
          var sel = r.selectorText; if (!sel || !re.test(sel)) continue;
          var sels = splitSel(sel).map(function (s) {
            if (!re.test(s)) return null;
            if (MK.test(s)) return s.replace(/#mkx(?![\w-])/g, '#gpBox .gp-mk');
            if (/#gpBox/.test(s)) return null;
            var m = PSEUDO.exec(s), pe = m ? m[1] : ''; if (pe) s = s.slice(0, -pe.length); if (!s) return null;
            return '#gpBox :is(' + s + ')' + pe;
          }).filter(Boolean);
          if (!sels.length) continue;
          var mk = sels.some(function (s) { return s.indexOf('.gp-mk') >= 0; });
          var body = decl(r.style, mk); if (body) into.push(sels.join(',') + '{' + body + '}');
        } else if (r.type === 4 && r.cssRules) { var a = []; walk(r.cssRules, a); if (a.length) into.push('@media ' + r.conditionText + '{' + a.join('\n') + '}'); }
        else if (r.type === 12 && r.cssRules) { var b = []; walk(r.cssRules, b); if (b.length) into.push('@supports ' + r.conditionText + '{' + b.join('\n') + '}'); }
      }
    }
    var out = [];
    Array.prototype.forEach.call(document.styleSheets, function (sh) { if (sh.ownerNode === adoptEl) return; try { walk(sh.cssRules, out); } catch (e) {} });
    adoptEl.textContent = out.join('\n');
  }

  /* ───────────────────────── the header (approved markup, filled for this group) ───────────────────────── */
  function today(list) { return (list || []).filter(function (p) { return /^(just now|\d+\s*(m|min|h) ago)$/i.test(p.ts || ''); }).length; }
  function paintHeader(g) {
    var gd = document.getElementById('groupDetail'); if (!gd) return;
    var q = function (s) { return gd.querySelector(s); };
    if (q('#dt-title')) q('#dt-title').textContent = g.title;
    if (q('.group-cover') && g.bg) q('.group-cover').style.background = g.bg;
    if (q('.group-cover-emoji')) q('.group-cover-emoji').textContent = g.emoji || '👥';
    if (q('#dt-type')) q('#dt-type').textContent = g.deal ? '🤝 Deal Room' : '💬 Discussion';
    var posts = g.canSee ? demoPosts(g) : [];
    if (q('.group-meta-stats')) q('.group-meta-stats').innerHTML = '<div><b>' + fmtN(g.count) + '</b> ' + (g.count === 1 ? 'member' : 'members') + '</div>' + (g.canSee ? '<div><b>' + today(posts) + '</b> new posts today</div>' : '') + '<div>' + (g.priv ? '🔒 Private' : '🌍 Public') + '</div>';
    var ma = q('#memberActions'), aa = q('#adminActions');
    if (ma) ma.style.display = g.role === 'admin' ? 'none' : 'flex';
    if (aa) aa.style.display = g.role === 'admin' ? 'flex' : 'none';
    var lb = q('#memberActions [data-gpj]') || q('#memberActions .btn-leave');   /* the approved Leave button; it becomes Join / Request / Accept */
    if (lb) {
      lb.onclick = null; lb.removeAttribute('onclick');
      var state = g.member ? 'leave' : g.invited ? 'accept' : g.priv ? (g.pending ? 'pending' : 'request') : 'join';
      lb.dataset.gpj = state;
      lb.textContent = { leave: '🚪 Leave Group', join: '+ Join Group', request: '🔒 Request to join', pending: '⏳ Request sent', accept: '✉️ Accept invitation' }[state];
      lb.classList.toggle('btn-leave', state === 'leave'); lb.classList.toggle('btn-manage', state !== 'leave');
    }
    Array.prototype.forEach.call(gd.querySelectorAll('#memberActions .btn-secondary'), function (b) { b.style.display = g.member ? '' : 'none'; });
    var lc = q('#leaveConfirm'); if (lc) lc.classList.remove('show');
    var cp = q('#leaveConfirm .cp-desc'); if (cp) cp.textContent = 'You’ll stop seeing posts from ' + g.title + ' and lose access to its members and listings.';
    var mp = q('#managePanel'); if (mp && g.role !== 'admin') mp.style.display = 'none';
    var nm = q('#tab-settings .field-input'); if (nm) nm.value = g.title;
    var ds = q('#tab-settings .field-textarea'); if (ds) ds.value = g.desc;
    var dmt = document.querySelector('#deleteModal .dm-title'); if (dmt) dmt.textContent = 'Delete "' + g.title + '"?';
    var dmd = document.querySelector('#deleteModal .dm-desc'); if (dmd) dmd.textContent = 'This will permanently remove all ' + fmtN(g.count) + ' members, every post, and the full history. There is no undo.';
    var di = document.getElementById('deleteConfirmInput'); if (di) { di.placeholder = g.title; di.value = ''; }
    var dz = q('.danger-zone .dz-desc'); if (dz) dz.textContent = fmtN(g.count) + ' real members and their history live in this group. Choose carefully.';
    var sev = q('.choice-card.severe .choice-desc'); if (sev) sev.textContent = 'Removes all ' + fmtN(g.count) + ' members & history forever. No recovery.';
    if (g.role === 'admin') paintManage(g);
  }

  /* ───────────────────────── members ───────────────────────── */
  var ROLE = { admin: ['rp-admin', '👑 Admin'], subadmin: ['rp-subadmin', '🛡️ Sub-Admin'], moderator: ['rp-subadmin', '🛡️ Sub-Admin'], member: ['rp-member', 'Member'] };
  function demoMembers(g) {
    var s = st(), rm = s.gone[g.key] || {}, ro = s.roles[g.key] || {}, rows = [];
    var base = g.seed ? g.seed.mem : [[me().id, 'admin', 'Created the group']];
    base.forEach(function (m) { if (!rm[m[0]]) rows.push({ uid: m[0], role: ro[m[0]] || m[1], joined: m[2] }); });
    var mine = rows.find(function (r) { return r.uid === me().id; });
    if (g.member && !mine) rows.push({ uid: me().id, role: g.role || 'member', joined: 'Joined just now' });
    if (!g.member && mine) rows = rows.filter(function (r) { return r !== mine; });
    var rank = { admin: 0, subadmin: 1, moderator: 1, member: 2 };
    return rows.filter(function (r) { return person(r.uid); }).sort(function (a, b) { return rank[a.role] - rank[b.role]; });
  }
  function connBtn(uid) {
    var s = (window.CONN_STATE || {})[uid];
    return s === 'connected' ? '<button type="button" class="gcard-btn btn-joined" data-gpa="conn" data-uid="' + uid + '">✓ Connected</button>'
      : s === 'pending' ? '<button type="button" class="gcard-btn btn-joined" data-gpa="conn" data-uid="' + uid + '">⏳ Pending</button>'
      : '<button type="button" class="gcard-btn btn-join" data-gpa="conn" data-uid="' + uid + '">+ Connect</button>';
  }
  function memberRow(m, g, manage) {
    var u = person(m.uid); if (!u) return '';
    var r = ROLE[m.role] || ROLE.member, self = m.uid === me().id;
    var acts = self ? '<div class="gp-you">You</div>' : '<button type="button" class="gcard-btn btn-joined" data-gpa="msg" data-uid="' + m.uid + '">💬 Message</button>' + connBtn(m.uid);
    if (g.admin && !self && (g.role === 'admin' || m.role === 'member')) {
      acts += '<button type="button" class="action-btn" aria-label="Member options" onclick="toggleDropdown(this)">⋯</button><div class="dropdown-menu">' +
        (m.role !== 'admin' && g.role === 'admin' ? '<div class="dd-item" data-gpd="admin" role="button" tabindex="0">👑 Promote to Admin</div>' : '') +
        (m.role === 'member' && g.role === 'admin' ? '<div class="dd-item" data-gpd="subadmin" role="button" tabindex="0">🛡️ Promote to Sub-Admin</div>' : '') +   /* live: role 'moderator' (0061) */
        (m.role !== 'member' ? '<div class="dd-item" data-gpd="member" role="button" tabindex="0">👤 Demote to Member</div>' : '') +
        '<div class="dd-divider"></div><div class="dd-item" data-gpd="msg" role="button" tabindex="0">💬 Message</div><div class="dd-item danger" data-gpd="remove" role="button" tabindex="0">🚫 Remove from group</div></div>';
    }
    return '<div class="member-row" data-uid="' + m.uid + '" style="position:relative">' +
      '<div class="av gp-av" data-gp="' + m.uid + '" role="button" tabindex="0" style="background:' + esc(u.color || '#1a56db') + ';width:38px;height:38px;font-size:13px">' + esc(u.initials || '?') + '</div>' +
      '<div class="gp-mrow-main"><div class="member-name"><span class="gp-name" data-gp="' + m.uid + '" role="button" tabindex="0" data-noi18n>' + esc(u.name) + '</span> <span class="role-pill ' + r[0] + '">' + r[1] + '</span></div>' +
      '<div class="member-meta"><span data-noi18n>' + esc(headline(u)) + '</span>' + (m.joined ? ' · <span>' + esc(m.joined) + '</span>' : '') + '</div></div>' +
      '<div class="member-actions">' + acts + '</div></div>';
  }
  function paintManage(g) {   /* the approved Manage panel lists this group's members and reports */
    var gd = document.getElementById('groupDetail'); if (!gd || g.live) return;
    var list = gd.querySelector('#tab-members .member-list'), mem = demoMembers(g);
    if (list) list.innerHTML = mem.map(function (m) { return memberRow(m, g, true); }).join('');
    var h = gd.querySelector('#tab-members .member-list-title span'); if (h) h.textContent = 'Members (' + fmtN(g.count) + ')';
    var reps = reportsOf(g), q = gd.querySelector('#tab-reports .mod-queue');
    if (q) q.innerHTML = reps.length ? reps.map(reportHtml).join('') : '<div class="gp-ok">✓ No pending reports</div>';
    var badge = gd.querySelector('#managePanel .ptab-badge'); if (badge) { badge.textContent = reps.length; badge.style.display = reps.length ? '' : 'none'; }
  }
  function reportsOf(g) {
    var s = st(), done = s.rep['done:' + g.key] || {};
    var seed = ((g.seed && g.seed.rep) || []).filter(function (r) { return !done[r.id]; });
    var filed = (s.rep[g.key] || []).filter(function (r) { return !done[r.id]; });
    return filed.concat(seed);
  }
  function reportHtml(r) {
    var post = r.kind === 'post';
    return '<div class="mod-item' + (post ? ' report' : '') + '" data-rid="' + esc(r.id) + '"><div class="mod-icon">' + (post ? '🚩' : '👤') + '</div><div class="mod-content">' +
      '<div class="mod-title">' + (post ? 'Post by ' : 'Member ') + '<b data-noi18n>' + esc(r.who) + '</b> ' + (r.n > 1 ? 'reported by ' + r.n + ' members' : 'reported by 1 member') + '</div>' +
      '<div class="mod-meta"><span data-noi18n>' + esc(r.text) + '</span> · ' + esc(r.ts || 'just now') + '</div>' +
      (r.why ? '<div class="mod-reason">⚠️ ' + esc(r.why) + '</div>' : '') +
      '<div class="mod-actions"><button type="button" class="mod-btn dismiss" data-gpr="dismiss">Dismiss report</button><button type="button" class="mod-btn remove" data-gpr="remove">' + (post ? 'Remove post & warn user' : 'Remove from group') + '</button></div></div></div>';
  }

  /* ───────────────────────── listings (deal rooms) ───────────────────────── */
  function demoListings(g) { var s = st(), shut = s.closedL || {}, mine = s.lst[g.key] || []; return mine.concat((g.seed && g.seed.list) || []).filter(function (l) { return !shut[l.id]; }).map(function (l) { return l.uid === me().id && !l.co ? Object.assign({ co: (window.dxDir && window.dxDir.mine && window.dxDir.mine() || {}).name || '', coVerified: true }, l) : l; }); }
  function avMini(u) { return '<div class="av" style="background:' + esc(u.color || '#1a56db') + ';width:17px;height:17px;font-size:7px">' + esc(u.initials || '?') + '</div>'; }
  function coLine(l) { return l.co ? '<div class="gp-lco">🏢 <span data-noi18n>' + esc(l.co) + '</span>' + (l.coVerified ? ' <span class="gp-ver">✓ Verified</span>' : '') + '</div>' : ''; }
  function mineActs(l) { return '<span class="gp-tag">' + (l.kind === 'rfq' ? 'Your request' : 'Your offer') + '</span><button type="button" class="qt-btn gp-lq" data-gpl="deals">' + (l.kind === 'rfq' ? 'Quotes' : 'Enquiries') + ' (' + (+l.responses || 0) + ')</button><button type="button" class="qt-btn gp-lclose" data-gpl="close">Close</button>'; }
  function rfqCard(l) {
    var u = person(l.uid) || me(), quoted = st().quotes[l.id] || l.answered, mine = l.uid === me().id, member = CUR && CUR.g && CUR.g.member;
    return '<div class="dcard" data-lid="' + esc(l.id) + '"><div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">' +
      '<div class="dc-title"><span class="role-badge need" style="margin-right:5px;font-size:8.5px;padding:2px 6px">🔍 Looking to Buy</span><span data-noi18n>' + esc(l.t) + '</span></div>' +
      '<span class="db-badge ' + esc(String(l.badge || 'OPEN').toLowerCase()) + '">' + esc(l.badge || 'OPEN') + '</span></div>' +
      '<div class="dc-det"><span data-noi18n>' + esc(l.d) + '</span><br>' + esc(l.where || '🇪🇬 Egypt · just now') + '</div>' + coLine(l) +
      '<div class="dc-foot"><div class="dc-buyer" data-gp="' + u.id + '" role="button" tabindex="0">' + avMini(u) + ' <span data-noi18n>' + esc(u.name) + '</span>' + (u.verified ? ' ✓' : '') + '</div>' +
      (mine ? mineActs(l) : !member ? '<button type="button" class="qt-btn" data-gpa="join">Join to quote</button>' : '<button type="button" class="qt-btn" data-gpl="quote"' + (quoted ? ' disabled' : '') + '>' + (quoted ? '✓ Quoted' : 'Quote →') + '</button>') + '</div></div>';
  }
  function offerCard(l) {
    var u = person(l.uid) || me(), mine = l.uid === me().id, surplus = l.kind === 'surplus', member = CUR && CUR.g && CUR.g.member, asked = st().quotes[l.id] || l.answered;
    return '<div class="lcard" data-lid="' + esc(l.id) + '"><div class="lc-inner"><div class="lc-top"><div class="lc-em em-supply">' + esc(l.em || '📦') + '</div><div>' +
      '<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px"><span class="role-badge have">' + (surplus ? '♻️ Surplus' : '📦 For Sale') + '</span><span class="lt lt-s">SUPPLY</span>' +
      (l.certs || []).map(function (c) { return '<span class="cert-p">' + esc(c) + '</span>'; }).join('') + '</div>' +
      '<div class="lc-title" data-noi18n>' + esc(l.t) + '</div><div class="lc-desc" data-noi18n>' + esc(l.d) + '</div>' + coLine(l) + '</div></div>' +
      (l.trust && l.trust.length ? '<div class="trust-bar">' + l.trust.map(function (t, i) { return '<span class="ti ' + (i === 0 ? 'g' : 'b') + '">' + esc(t) + '</span>'; }).join('') + '</div>' : '') +
      '<div class="lc-foot"><div><div class="price">' + esc(l.price || 'On request') + '</div><div class="moq">' + esc(l.moq || '') + '</div></div>' +
      '<div style="display:flex;flex-wrap:wrap;justify-content:flex-end;gap:5px;align-items:center"><span class="gp-seller" data-gp="' + u.id + '" role="button" tabindex="0" data-noi18n>' + esc(u.name) + '</span>' +
      (mine ? mineActs(l) : !member ? '<button type="button" class="btn-contact" data-gpa="join">Join to enquire</button>' : '<button type="button" class="btn-contact" data-gpl="contact"' + (asked ? ' disabled' : '') + '>' + (asked ? '✓ Request sent' : 'Request quote →') + '</button>') + '</div></div></div></div>';
  }

  /* ───────────────────────── the inside ───────────────────────── */
  function box() {
    var gd = document.getElementById('groupDetail'); if (!gd) return null;
    var b = document.getElementById('gpBox');
    if (!b) { b = document.createElement('div'); b.id = 'gpBox'; var page = gd.querySelector('.detail-page'); if (!page) return null; page.appendChild(b); }
    return b;
  }
  var TABS = [['disc', '💬 Discussion'], ['members', '👥 Members'], ['about', 'ℹ️ About'], ['listings', '📦 Listings']];
  function render(g, tab) {
    var b = box(); if (!b) return;
    CUR = { g: g, posts: null, tab: tab || 'disc' };
    /* live: a deal room's Listings tab shows only once the adapter keeps them in the database (window.dxLiveGroupListings) — never a
       tab whose Post button cannot save (G-01) */
    var tabs = TABS.filter(function (t) { return t[0] !== 'listings' || (g.deal && (!g.live || window.dxLiveGroupListings)); });
    if (!tabs.some(function (t) { return t[0] === CUR.tab; })) CUR.tab = 'disc';
    b.innerHTML = '<div class="panel-tabs gp-tabs" role="tablist" aria-label="Group sections">' + tabs.map(function (t) {
      var on = t[0] === CUR.tab; return '<div class="gx-ptab' + (on ? ' active' : '') + '" role="tab" tabindex="0" aria-selected="' + on + '" data-gpt="' + t[0] + '">' + t[1] + '</div>'; }).join('') + '</div>' +
      tabs.map(function (t) { return '<div class="gp-pane' + (t[0] === 'disc' ? ' gp-disc' : ' panel-body') + (t[0] === 'listings' ? ' gp-mk' : '') + '" data-pane="' + t[0] + '"' + (t[0] === CUR.tab ? '' : ' hidden') + '></div>'; }).join('');
    paintPane(CUR.tab);
  }
  function pane(name) { return document.querySelector('#gpBox [data-pane="' + name + '"]'); }
  function show(tab) {
    if (!CUR) return; CUR.tab = tab;
    document.querySelectorAll('#gpBox [data-gpt]').forEach(function (t) { var on = t.dataset.gpt === tab; t.classList.toggle('active', on); t.setAttribute('aria-selected', on); });
    document.querySelectorAll('#gpBox [data-pane]').forEach(function (p) { p.hidden = p.dataset.pane !== tab; });
    paintPane(tab);
  }
  function paintPane(tab) {
    var g = CUR && CUR.g, el = pane(tab); if (!g || !el) return;
    if (tab === 'disc') paintDisc(g, el); else if (tab === 'members') paintMembers(g, el); else if (tab === 'about') paintAbout(g, el); else if (tab === 'listings') paintListings(g, el);
  }
  function gate(g) {
    if (g.member) return '';
    if (g.priv) {
      var head = g.invited ? '✉️ You’re invited to this private group' : '🔒 This is a private group';
      var sub = g.invited ? 'Accept the invitation to see the discussions, members and listings.' : g.pending ? 'Your request was sent. An admin will review it — you’ll get a notification.' : 'Only members can see the discussions, members and listings. Ask to join and an admin will review your request.';
      var btn = g.invited ? '<button type="button" class="gcard-btn btn-join" data-gpa="accept">✉️ Accept invitation</button> <button type="button" class="gcard-btn gp-decline" data-gpa="declineinv">✕ Decline</button>'
        : g.pending ? '<button type="button" class="gcard-btn btn-joined" data-gpa="cancel">⏳ Request sent · Cancel</button>' : '<button type="button" class="gcard-btn btn-join" data-gpa="request">🔒 Request to join</button>';
      return '<div class="gp-lock"><div class="gp-lock-ic">' + (g.invited ? '✉️' : '🔒') + '</div><b>' + head + '</b><p>' + sub + '</p>' + btn + '</div>';
    }
    return '<div class="why-banner gp-gate"><span>👀 You’re viewing a preview. Join to post, comment and react.</span><button type="button" class="gcard-btn btn-join" data-gpa="join">+ Join Group</button>' +
      (g.invited ? ' <button type="button" class="gcard-btn gp-decline" data-gpa="declineinv">✕ Decline invitation</button>' : '') + '</div>';
  }
  function loadPosts(g, force) {
    if (!CUR || CUR.g !== g) return;
    if (!g.live) { CUR.posts = order(demoPosts(g)); return; }
    var r = hook('groupPosts', { group: pub(g) });
    if (!r || typeof r.then !== 'function') { CUR.posts = []; CUR.unsupported = true; return; }
    CUR.posts = null; CUR.loading = true;
    r.then(function (list) { if (!CUR || CUR.g !== g) return; CUR.loading = false; CUR.posts = order(Array.isArray(list) ? list : []); CUR.more = list && typeof list.more === 'function' ? list.more : null; if (CUR.tab === 'disc') paintPane('disc'); },
      function (e) { if (!CUR || CUR.g !== g) return; CUR.loading = false; CUR.posts = []; CUR.err = true; if (CUR.tab === 'disc') paintPane('disc'); });
  }
  function paintDisc(g, el) {
    if (!g.canSee) { el.innerHTML = gate(g); return; }
    if (!CUR.posts && !CUR.loading) loadPosts(g);
    var h = gate(g);
    if (g.archived) h += '<div class="why-banner gp-gate gp-arch"><span>📦 This group is archived — you can read its history; nobody can post, comment or join.</span></div>';
    else if (g.member && g.postPolicy === 'admins' && !g.admin) h += '<div class="why-banner gp-gate"><span>📣 Only the admins post in this group — you can comment and react.</span></div>';
    if (g.member && !CUR.unsupported && !g.archived && (g.postPolicy !== 'admins' || g.admin)) h += '<div class="gp-comp">' + (typeof window.renderComposer === 'function' ? window.renderComposer() : '') + '</div>';
    if (CUR.loading && !CUR.posts) h += '<div class="gp-empty">Loading posts…</div>';
    else if (CUR.unsupported) h += '<div class="gp-empty">💬 Group discussions open here soon.</div>';
    else if (!CUR.posts.length) h += '<div class="gp-empty"><b>💬 No posts yet</b><span>' + (g.member ? 'Start the first discussion in this group.' : 'Join to start the first discussion.') + '</span></div>';
    h += '<div class="gp-posts"></div>';
    el.innerHTML = h;
    var list = el.querySelector('.gp-posts');
    (CUR.posts || []).forEach(function (p) { try { list.appendChild(postEl(p, g)); } catch (e) { if (window.console) console.warn('[groups] post', e); } });
    adopt(el); moreCtl(el);
  }
  function endMark(el) {   /* after the last post: the reader knows there is nothing more to load */
    var old = el.querySelector('.gp-end'); if (old) old.remove();
    if (!CUR || CUR.more || !(CUR.posts || []).length) return;
    var list = el.querySelector('.gp-posts'); if (list) list.insertAdjacentHTML('afterend', '<div class="gp-end">✓ You’re all caught up — no more posts in this group</div>');
  }
  /* live: the next page of posts (keyset, as the Home feed) when the end of the list comes into view, or on "Show more posts" */
  var moreIO = null;
  function moreCtl(el) {
    if (moreIO) { moreIO.disconnect(); moreIO = null; }
    var old = el.querySelector('.gp-loadmore'); if (old) old.remove();
    endMark(el);
    if (!CUR || !CUR.more) return;
    var list = el.querySelector('.gp-posts'); if (!list) return;
    list.insertAdjacentHTML('afterend', '<div class="gp-more gp-loadmore" data-gpa="more" role="button" tabindex="0">Show more posts</div>');
    if ('IntersectionObserver' in window) { moreIO = new IntersectionObserver(function (en) { if (en[0] && en[0].isIntersecting) loadMore(); }, { rootMargin: '400px' }); moreIO.observe(el.querySelector('.gp-loadmore')); }
  }
  function loadMore() {
    if (!CUR || !CUR.more || CUR.moreBusy) return;
    var g = CUR.g, r = CUR.more(); if (!r || typeof r.then !== 'function') { CUR.more = null; return; }
    CUR.moreBusy = true;
    r.then(function (list) {
      if (!CUR || CUR.g !== g) return; CUR.moreBusy = false; list = Array.isArray(list) ? list : [];
      var have = {}; (CUR.posts || []).forEach(function (p) { have[p.id] = 1; });
      var fresh = list.filter(function (p) { return !have[p.id]; });
      CUR.posts = (CUR.posts || []).concat(fresh); CUR.more = typeof list.more === 'function' ? list.more : null;
      var el = pane('disc'), ul = el && el.querySelector('.gp-posts'); if (!ul) return;
      fresh.forEach(function (p) { try { ul.appendChild(postEl(p, g)); } catch (e) {} }); adopt(ul); moreCtl(el);
    }, function (e) { if (CUR) CUR.moreBusy = false; D.toast((window.dxLive && window.dxLive.friendly ? window.dxLive.friendly(e) : (e && e.message)) || 'Could not load more posts — try again'); });
  }
  function liveMembers(g) {   /* live: the member list once per opening; the Members and About tabs are drawn again when it arrives */
    if (!g.live || CUR.members || CUR.mLoading) return;
    var r = hook('groupMembers', { group: pub(g) });
    if (r && typeof r.then === 'function') { CUR.mLoading = true; r.then(function (l) { if (!CUR || CUR.g !== g) return; CUR.mLoading = false; CUR.members = Array.isArray(l) ? l : []; if (CUR.tab === 'members' || CUR.tab === 'about') paintPane(CUR.tab); }, function () { if (CUR && CUR.g === g) { CUR.mLoading = false; CUR.members = []; if (CUR.tab === 'members' || CUR.tab === 'about') paintPane(CUR.tab); } }); }
    else CUR.members = [];
  }
  function paintMembers(g, el) {
    liveMembers(g);
    var rows = g.live ? (CUR.members || null) : demoMembers(g);
    if (!g.canSee) rows = rows && rows.filter(function (m) { return m.role === 'admin'; });   /* not a member: the admins only, as the approved page shows */
    var h = '<div class="member-list-title"><span>Members (' + fmtN(Math.max(g.count, (rows || []).length)) + ')</span>' +
      (g.canSee ? '<input type="search" class="member-search gp-msearch" placeholder="🔍 Search members" aria-label="Search members">' : '') + '</div>';
    if (!rows) h += '<div class="gp-empty">Loading members…</div>';
    else {
      h += '<div class="member-list">' + rows.map(function (m) { return memberRow(m, g, false); }).join('') + '</div>';
      var more = g.count - rows.length;
      if (!g.canSee) h += '<div class="gp-more">🔒 The full member list is visible to members only.</div>';
      else if (more > 0) h += '<div class="gp-more">+ ' + fmtN(more) + ' more members</div>';
      h += '<div class="gp-nores gp-empty" hidden>No member matches your search.</div>';
    }
    el.innerHTML = h;
  }
  function paintAbout(g, el) {
    liveMembers(g);
    var by = g.by && person(g.by), d = g.since ? new Date(g.since + (g.since.length === 10 ? 'T12:00:00' : '')) : null;
    var date = d && !isNaN(d) ? (window.dxFmtDate ? window.dxFmtDate(d, false, 'en') : d.toDateString()) : '';
    var admins = (g.live ? (CUR.members || []) : demoMembers(g)).filter(function (m) { return m.role === 'admin' || m.role === 'subadmin' || m.role === 'moderator'; });
    var h = '<div class="gp-sec"><div class="field-label">About this group</div><div class="gp-text" data-noi18n>' + esc(g.about || g.desc || '') + '</div></div>' +
      '<div class="gp-facts">' +
        '<div class="gp-fact"><span class="gp-k">Type</span><span class="gp-v">' + (g.deal ? '🤝 Deal Room' : '💬 Discussion') + '</span><small>' + (g.deal ? 'Buy/sell, RFQs & quotes' : 'Knowledge sharing, Q&A') + '</small></div>' +
        '<div class="gp-fact"><span class="gp-k">Privacy</span><span class="gp-v">' + (g.priv ? '🔒 Private' : '🌍 Public') + '</span><small>' + (g.priv ? 'Members must be approved or invited' : 'Anyone can find, view, and join') + '</small></div>' +
        '<div class="gp-fact"><span class="gp-k">Members</span><span class="gp-v">' + fmtN(g.count) + '</span></div>' +
        (date ? '<div class="gp-fact"><span class="gp-k">Created</span><span class="gp-v">' + esc(date) + '</span>' + (by ? '<small><span>by</span> <span class="gp-name" data-gp="' + by.id + '" role="button" tabindex="0" data-noi18n>' + esc(by.name) + '</span></small>' : '') + '</div>' : '') +
        (g.markets ? '<div class="gp-fact"><span class="gp-k">Markets</span><span class="gp-v" data-noi18n>' + esc(g.markets) + '</span></div>' : '') +
        '<div class="gp-fact"><span class="gp-k">Sector</span><span class="gp-v">' + esc(SECTORS[g.sector] || SECTORS.other) + '</span></div>' +
        (g.country.length ? '<div class="gp-fact"><span class="gp-k">Countries</span><span class="gp-v">' + g.country.map(function (c) { return esc((CFLAG[c] || '') + ' ' + (CNAME[c] || c)); }).join(' · ') + '</span></div>' : '') +
        '<div class="gp-fact"><span class="gp-k">Who can post</span><span class="gp-v">' + (g.postPolicy === 'admins' ? '📣 Admins only' : '👥 All members') + '</span></div>' +
        (g.archived ? '<div class="gp-fact"><span class="gp-k">Status</span><span class="gp-v">📦 Archived</span><small>Read only</small></div>' : '') +
      '</div>' +
      (g.focus && g.focus.length ? '<div class="gp-sec"><div class="field-label">Topics</div><div class="gp-tags" data-noi18n>' + g.focus.map(function (f) { return '<span class="gtag gtag-discuss">' + esc(f) + '</span>'; }).join('') + '</div></div>' : '') +
      '<div class="gp-sec"><div class="field-label">Group rules</div>' + (g.rules && g.rules.length ? '<ol class="gp-rules" data-noi18n>' + g.rules.map(function (r) { return '<li><b>' + esc(r[0]) + '</b><span>' + esc(r[1]) + '</span></li>'; }).join('') + '</ol>' : '<div class="gp-empty">No rules yet.</div>') + '</div>' +
      '<div class="gp-sec"><div class="field-label">Admins</div><div class="member-list">' + admins.map(function (m) { return memberRow(m, g, false); }).join('') + '</div></div>';
    el.innerHTML = h;
  }
  function paintListings(g, el) {
    if (!g.canSee) { el.innerHTML = gate(g); return; }
    var list = null;
    if (g.live) {
      if (!CUR.listings && !CUR.lLoading) {
        var r = hook('groupListings', { group: pub(g) });
        if (r && typeof r.then === 'function') { CUR.lLoading = true; r.then(function (l) { if (!CUR || CUR.g !== g) return; CUR.lLoading = false; CUR.listings = Array.isArray(l) ? l : []; if (CUR.tab === 'listings') paintPane('listings'); }, function () { if (CUR) { CUR.lLoading = false; CUR.listings = []; } }); }
        else CUR.listings = [];
      }
      list = CUR.listings;
    } else list = demoListings(g);
    var rfq = (list || []).filter(function (l) { return l.kind === 'rfq'; }), offers = (list || []).filter(function (l) { return l.kind !== 'rfq'; });
    var h = gate(g) + '<div class="gp-mk-hd"><div><div class="sec-title">🤝 Requests & offers</div><div class="sec-sub">Only members of this deal room see these and can answer.</div></div>' +
      (g.member ? '<button type="button" class="btn-manage" data-gpa="newlisting">➕ Post RFQ / offer</button>' : '') + '</div>';
    if (!list) h += '<div class="gp-empty">Loading listings…</div>';
    else if (!list.length) h += '<div class="gp-empty"><b>📦 No requests or offers yet</b><span>' + (g.member ? 'Post the first RFQ or offer for this group.' : 'Join to post the first request.') + '</span></div>';
    else {
      if (rfq.length) h += '<div class="gp-mk-sub"><span>🔍 Looking to Buy</span> <b>' + rfq.length + '</b></div><div class="gp-rfqs">' + rfq.map(rfqCard).join('') + '</div>';
      if (offers.length) h += '<div class="gp-mk-sub"><span>📦 Offers & surplus</span> <b>' + offers.length + '</b></div><div class="gp-offers">' + offers.map(offerCard).join('') + '</div>';
    }
    el.innerHTML = h; adopt(el);
  }

  /* ───────────────────────── opening a group ───────────────────────── */
  function open(target, tab) {
    var card = target && target.nodeType === 1 ? target : cardByKey(target) || cardByTitle(target);
    if (!card || !document.getElementById('groupDetail')) return false;   /* another page is on screen (a name on the card opened a profile): nothing to open (G-16) */
    LAST_CARD = card; OPEN_ARGS = { tab: tab || 'disc' };
    var g = model(card, null);
    if (typeof window.openGroup === 'function') window.openGroup(g.role === 'admin' ? 'admin' : 'member');
    return true;
  }
  function afterOpen(role) {
    var card = LAST_CARD && LAST_CARD.isConnected ? LAST_CARD : null, args = OPEN_ARGS || {}; OPEN_ARGS = null;
    if (!card) { var t = txt(document.getElementById('dt-title')); card = cardByTitle(t); }
    var b = box(); if (!b) return;
    if (!card) { b.innerHTML = ''; CUR = null; return; }
    var g = model(card, role);
    if (!g.live) paintHeader(g);
    render(g, args.tab);
    pushOpen(); manageExtras(g); paintNotif(notifOn(g));
    var dp = document.querySelector('#groupDetail .detail-overlay, #groupDetail'); if (dp) dp.scrollTop = 0;
  }
  function refresh(tab) {   /* the group on screen changed (joined, left, requested…): header + inside again, same tab */
    if (!CUR) return; var card = CUR.g.card; if (!card || !card.isConnected) card = cardByKey(CUR.g.key); if (!card) return;   /* live: the cards may have been drawn again meanwhile */
    var g = model(card, CUR.g.role); if (!g.live) paintHeader(g); render(g, tab || CUR.tab); manageExtras(g); paintNotif(notifOn(g));
  }

  /* ───────────────────────── membership (demo) ───────────────────────── */
  function paintCard(card, state) {   /* state: joined | join | request | pending | accept (invited) */
    var b = card.querySelector('.gcard-btn'); if (!b) return;
    var on = state === 'joined', wait = state === 'pending';   /* a pending request is not membership (the page's "My Groups" filter counts .btn-joined) */
    b.classList.toggle('btn-joined', on); b.classList.toggle('btn-join', !on && !wait); b.classList.toggle('gp-pending', wait);
    b.textContent = { joined: '✓ Joined', join: '+ Join', request: '🔒 Request', pending: '⏳ Requested', accept: '✉️ Accept' }[state];
    b.setAttribute('aria-pressed', state === 'joined' ? 'true' : 'false');
    if (state === 'pending' || state === 'request' || state === 'accept') b.dataset.gpq = state; else delete b.dataset.gpq;
    if (state === 'joined' || state === 'join') { var wb = card.querySelector('.why-banner'); if (wb && /✉️/.test(wb.textContent)) wb.remove(); }
  }
  function idleState(card) {   /* the card button of a group you are not in */
    if (!/private/i.test(otxt(card.querySelector('.gcard-meta')))) return 'join';
    var k = cardKey(card), sd = BY_KEY[k];
    return sd && sd.inv && !(st().noinv || {})[k] && !card.dataset.gid ? 'accept' : st().req[k] ? 'pending' : 'request';
  }
  function setMember(card, on, quiet) {
    var t = otxt(card.querySelector('.gcard-title')), key = cardKey(card), was = cardJoined(card);
    if (was !== on) {
      var mc = card.querySelector('.member-count');
      if (mc) { var raw = otxt(mc), n = num(raw) + (on ? 1 : -1); mc.textContent = fmtN(Math.max(0, n)) + (/members/.test(raw) ? ' members' : ''); }
    }
    paintCard(card, on ? 'joined' : idleState(card));
    var j = ls('groups_joined').filter(function (x) { return x !== t; }), left = ls('groups_left').filter(function (x) { return x !== t; });
    if (on) j.push(t); else left.push(t);
    ls('groups_joined', j); ls('groups_left', left);
    var gj = {}; try { gj = D.store.get('groupsJoined', {}) || {}; } catch (e) {} gj[t] = on; D.store.set('groupsJoined', gj);
    var s = st(); delete s.req[key]; if (!on && s.roles[key]) delete s.roles[key][me().id]; save();
    if (!quiet) D.toast(on ? 'You joined ' + t : 'You left ' + t);
  }
  function setRequest(card, on) {
    var key = cardKey(card), t = otxt(card.querySelector('.gcard-title')), s = st();
    if (on) s.req[key] = new Date().toISOString(); else delete s.req[key];
    save(); paintCard(card, on ? 'pending' : 'request');
    D.toast(on ? 'Request sent to the admins of ' + t : 'Request cancelled');
  }
  function joinClick(btn, e) {   /* the card's Join / Joined / Request button (links.js hands it here) */
    var card = btn.closest('.gcard'); if (!card || card.dataset.gid || isLive()) return false;
    if (e) { e.preventDefault(); e.stopPropagation(); }
    var g = model(card, null);
    if (g.member) {
      D.modal({ title: 'Leave group?', body: '<div>You will stop seeing posts from <b>' + esc(g.title) + '</b>.</div>', primary: { label: 'Leave', danger: true, onClick: function () { setMember(card, false); if (CUR && CUR.g.key === g.key) refresh(); } } });
    } else if (g.priv && !g.invited) setRequest(card, !g.pending);
    else { setMember(card, true); if (CUR && CUR.g.key === g.key) refresh(); }
    return true;
  }
  function headerJoin(state) {
    var g = CUR && CUR.g; if (!g) return;
    if (g.live) { liveJoin(g, state); return; }
    var card = g.card;
    if (state === 'leave') { window.toggleLeaveConfirm(); return; }
    if (state === 'join' || state === 'accept') { setMember(card, true); refresh(); return; }
    if (state === 'request') { setRequest(card, true); refresh(); return; }
    if (state === 'pending' || state === 'cancel') { D.modal({ title: 'Cancel your request?', body: '<div>You can ask to join <b>' + esc(g.title) + '</b> again later.</div>', primary: { label: 'Cancel request', danger: true, onClick: function () { setRequest(card, false); refresh(); } }, secondary: 'Keep it' }); }
  }
  function declineInvite() {   /* an invitation I do not want: it goes away (the admins can invite me again later) */
    var g = CUR && CUR.g; if (!g || !g.invited) return;
    var done = function () {
      var card = g.card && g.card.isConnected ? g.card : cardByKey(g.key);
      if (card) { delete card.dataset.invited; var wb = card.querySelector('.why-banner'); if (wb && /✉️/.test(wb.textContent)) wb.remove(); paintCard(card, g.priv ? (st().req[g.key] ? 'pending' : 'request') : 'join'); }
      D.toast('Invitation declined');
      if (g.priv && typeof window.closeGroup === 'function') window.closeGroup(); else refresh();
    };
    if (!g.live) { (st().noinv = st().noinv || {})[g.key] = 1; save(); done(); return; }
    var r = hook('groupManage', { group: pub(g), op: 'declineInvite' });
    if (r && typeof r.then === 'function') r.then(done, function (e) { D.toast((e && e.message) || 'Could not save — try again'); }); else D.toast('Could not save — try again');
  }
  function liveJoin(g, state) {   /* live: the adapter decides; until it supports groupJoin, the card's own Join button does it */
    var r = hook('groupJoin', { group: pub(g), op: state === 'cancel' ? 'cancel' : state });
    var done = function () { setTimeout(function () { refresh(); }, 50); };
    if (r && typeof r.then === 'function') { r.then(function () { if (state === 'join' || state === 'accept') { paintCard(g.card, 'joined'); } else if (state === 'request') paintCard(g.card, 'pending'); else if (state === 'cancel') paintCard(g.card, 'request'); done(); }, function (e) { D.toast((e && e.message) || 'Could not update your membership — try again'); }); return; }
    var b = g.card.querySelector('.gcard-btn'); if (!b) return;
    var before = b.className; b.click();
    var n = 0, t = setInterval(function () { if (b.className !== before || ++n > 50) { clearInterval(t); done(); } }, 100);
  }

  /* ───────────────────────── actions inside a group ───────────────────────── */
  function needMember(g) {
    if (g.member) return false;
    D.toast(g.priv ? 'Only members can do that — ask to join first' : 'Join the group to post, comment and react');
    var j = document.querySelector('#gpBox [data-gpa="join"], #gpBox [data-gpa="request"], #gpBox [data-gpa="accept"]'); if (j) { j.classList.remove('dbk-new'); void j.offsetWidth; j.classList.add('dbk-new'); }
    return true;
  }
  function react(p, kind, main) {   /* as on Home: Like (main) or the same kind again takes the reaction back; another kind from the panel replaces it */
    var g = CUR.g; if (needMember(g)) return;
    p.rx = p.rx || {}; kind = kind || 'like';
    var was = p.liked, op, k0 = p.rk || 'like';
    if (p.liked && !main && kind !== k0) { if (p.rx[k0]) { p.rx[k0]--; if (!p.rx[k0]) delete p.rx[k0]; } p.rk = kind; p.rx[kind] = (p.rx[kind] || 0) + 1; op = 'react'; }
    else if (p.liked) { var k = p.rk || 'like'; p.liked = false; p.likes = Math.max(0, (p.likes || 1) - 1); if (p.rx[k]) { p.rx[k]--; if (!p.rx[k]) delete p.rx[k]; } p.rk = null; op = 'unreact'; }
    else { p.liked = true; p.likes = (p.likes || 0) + 1; p.rk = kind || 'like'; p.rx[p.rk] = (p.rx[p.rk] || 0) + 1; op = 'react'; }
    commit(g, p, op, { kind: kind || 'like', was: was }); repaint(p);
  }
  function addComment(p, input) {
    var g = CUR.g; if (needMember(g)) return;
    var v = (input && input.value || '').trim(); if (!v) { if (input) input.focus(); return; }
    if (v.length > 3000) { D.toast('Comments can be up to 3,000 characters'); return; }
    var c = { uid: me().id, text: v, ts: 'just now', likes: 0, id: 'c' + Date.now() };
    p.cm = p.cm || []; p.cm.push(c);
    commit(g, p, 'comment', { comment: c }); var nu = repaint(p);
    var b = nu && nu.querySelector('[id^="cmt-"]'); if (b) b.style.display = 'block';
    D.toast('Comment posted!');
  }
  function toggleCmts(p) {
    var el = document.querySelector('#gpBox [data-gpp="' + p.id + '"] [id^="cmt-"]'); if (!el) return;
    var open = el.style.display === 'none'; el.style.display = open ? 'block' : 'none';
    if (open) { var i = el.querySelector('.cmt-input'); if (i && CUR.g.member) i.focus(); }
  }
  function copyLink(p) {
    var url = 'https://drugbox.app/g/' + slug(CUR.g.title) + (p ? '/p/' + p.id : '');
    var ok = function () { D.toast('Link copied!'); };
    try { if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(url).then(ok, function () { fallback(url); ok(); }); return; } } catch (e) {}
    fallback(url); ok();
  }
  function fallback(url) { try { var t = document.createElement('textarea'); t.value = url; t.style.position = 'fixed'; t.style.opacity = '0'; document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); } catch (e) {} }
  function sharePost(p) {
    var g = CUR.g, live = g.live, canFeed = !live || hook('groupPost', null) === true;
    var m = D.modal({ title: 'Share this post', secondary: 'Close', body:
      (canFeed && !g.priv ? '<button type="button" class="gp-opt" data-so="feed"><b>🔄 Repost to your feed</b><small>Your connections see it on Home, with a link to this group.</small></button>' : '') +
      (g.priv ? '<p class="gp-muted">🔒 Posts in a private group can’t be reposted outside it.</p>' : '') +
      '<button type="button" class="gp-opt" data-so="link"><b>🔗 Copy link</b><small>' + (g.priv ? 'Only members of the group can open it.' : 'Anyone on Drugbox can open it.') + '</small></button>' });
    m.el.addEventListener('click', function (e) {
      var o = e.target.closest && e.target.closest('[data-so]'); if (!o) return;
      m.close();
      if (o.dataset.so === 'link') { copyLink(p); return; }
      var a = person(p.uid) || me();
      p.sh = (p.sh || 0) + 1; commit(g, p, 'share', {}); repaint(p);
      if (!live && Array.isArray(window.POSTS)) window.POSTS.unshift({ id: Date.now(), uid: me().id, cat: p.cat || 'general', body: 'Shared from ' + g.title + ' — ' + a.name + ':\n\n' + (p.body || ''), likeCount: 0, liked: false, commentCount: 0, shareCount: 0, saved: false, pinned: false, ts: 'just now', imgs: (p.imgs || []).slice(), files: (p.files || []).slice(), reactions: {} });
      D.toast('Reposted to your feed');
    });
  }
  function report(p) {
    if (p.reported || (!CUR.g.live && (st().rep[CUR.g.key] || []).some(function (r) { return r.pid === p.id && r.mine; }))) { D.toast('You already reported this post — the admins will check it'); return; }
    var g = CUR.g, REASONS = ['Spam or unrelated ad', 'Unverified or counterfeit product', 'Misleading information', 'Harassment or hate', 'Breaks the group rules'];
    D.modal({ title: 'Report this post', body: '<p class="gp-muted">The group admins review reports. The author is not told who reported.</p>' +
      REASONS.map(function (r, i) { return '<label class="gp-radio"><input type="radio" name="gpRep" value="' + i + '"' + (i ? '' : ' checked') + '> <span>' + r + '</span></label>'; }).join('') +
      '<div class="dbk-f"><label for="gpRepN">Details (optional)</label><textarea id="gpRepN" maxlength="500" placeholder="What should the admins know?"></textarea></div>',
      primary: { label: 'Send report', danger: true, onClick: function (bx) {
        var i = +(bx.querySelector('input[name=gpRep]:checked') || { value: 0 }).value, note = bx.querySelector('#gpRepN').value.trim(), a = person(p.uid);
        var rec = { id: 'r' + Date.now(), kind: 'post', pid: p.id, mine: 1, who: a ? a.name : 'Member', text: '“' + String(p.body || '').slice(0, 90) + (String(p.body || '').length > 90 ? '…' : '') + '”', why: REASONS[i] + (note ? ' — ' + note : ''), n: 1, ts: 'just now' };
        p.reported = 1;
        if (g.live) { var rr = liveCall('groupPost', { group: pub(g), op: 'report', post: p, reason: REASONS[i], note: note }, function () { p.reported = 0; });
          if (rr && rr.then) rr.then(function (res) { D.toast(res === 'already' ? 'You already reported this post — the admins will check it' : 'Reported — the group admins will check it'); }); }
        else { var s = st(); (s.rep[g.key] = s.rep[g.key] || []).unshift(rec); save(); if (g.role === 'admin') paintManage(g); D.toast('Reported — the group admins will check it'); }
      } } });
  }
  function editPost(p) {
    D.modal({ title: 'Edit post', body: '<div class="dbk-f"><label for="gpEd">Your post *</label><textarea id="gpEd" rows="6" maxlength="5000" data-req>' + esc(p.body || '') + '</textarea></div>',
      primary: { label: 'Save', onClick: function (bx) { if (!D.requireFields(bx)) return false; var v = bx.querySelector('#gpEd').value.trim(); if (v === p.body) return; p.body = v; p.edited = 1; commit(CUR.g, p, 'edit', {}); repaint(p); D.toast('Post updated'); } } });
  }
  function deletePost(p, why) {
    var g = CUR.g, el = document.querySelector('#gpBox [data-gpp="' + p.id + '"]');
    if (el) el.style.display = 'none';
    var gone = function () { p.del = 1; commit(g, p, why === 'remove' ? 'remove' : 'delete', {}); if (el) el.remove();
      if (CUR && CUR.g === g) { CUR.posts = (CUR.posts || []).filter(function (x) { return x !== p; }); if (!CUR.posts.length && CUR.tab === 'disc') paintPane('disc'); } };
    if (window.dxUndo) window.dxUndo(why === 'remove' ? 'Post removed from the group' : 'Post deleted', function () { if (el) el.style.display = ''; }, gone);
    else gone();
  }
  function pin(p) {
    var g = CUR.g; p.pin = !p.pin;   /* one pinned post per group (as groups.pinned_post_id): pinning replaces the previous one */
    if (p.pin) (CUR.posts || []).forEach(function (x) { if (x !== p && x.pin) { x.pin = false; if (!g.live) persist(g, x); } });
    commit(g, p, p.pin ? 'pin' : 'unpin', {});
    CUR.posts = g.live ? order(CUR.posts) : order(demoPosts(g)); paintPane('disc'); D.toast(p.pin ? 'Pinned to the top of the group' : 'Post unpinned');
  }
  function savePost(p) { p.saved = !p.saved; commit(CUR.g, p, p.saved ? 'save' : 'unsave', {}); repaint(p); D.toast(p.saved ? 'Post saved! 🔖' : 'Post removed from saved'); }
  function reactors(p) {
    var icons = { like: '👍', celebrate: '🎉', insightful: '💡', support: '❤️', appreciation: '👏', curious: '🤔' }, rx = p.rx || {};
    D.toast(Object.keys(rx).map(function (k) { return (icons[k] || '👍') + ' ' + rx[k]; }).join('  ') || 'No reactions yet');
  }
  function commentAct(p, el, act) {
    var cmt = el.closest('.cmt'), box = el.closest('.cmt-box'); if (!cmt || !box) return;
    var idx = Array.prototype.indexOf.call(box.querySelectorAll('.cmt'), cmt), c = (p.cm || [])[idx]; if (!c) return;
    if (act === 'reply') { if (needMember(CUR.g)) return; var u = person(c.uid), i = box.querySelector('.cmt-input'); if (i) { var at = '@' + (u ? u.name.replace(/^(Dr\.|Eng\.)\s*/, '').split(' ')[0] : '') + ' '; if (i.value.indexOf(at) !== 0) i.value = at + i.value; i.focus(); } return; }
    if (needMember(CUR.g)) return;
    c.liked = !c.liked; c.likes = Math.max(0, (c.likes || 0) + (c.liked ? 1 : -1)); commit(CUR.g, p, 'commentLike', { comment: c }); repaint(p);
  }

  function commentDelete(p, el) {
    var cmt = el.closest('.cmt'), box = el.closest('.cmt-box'); if (!cmt || !box) return;
    var idx = Array.prototype.indexOf.call(box.querySelectorAll('.cmt'), cmt), c = (p.cm || [])[idx]; if (!c) return;
    D.modal({ title: 'Delete this comment?', body: '<div>It is removed for everyone in the group.</div>', primary: { label: 'Delete', danger: true, onClick: function () {
      var keep = p.cm.slice(), was = p.cmt;
      p.cm.splice(idx, 1);
      if (CUR.g.live) liveCall('groupPost', { group: pub(CUR.g), op: 'deleteComment', post: p, comment: c }, function () { p.cm = keep; p.cmt = was; repaint(p); });
      else persist(CUR.g, p);
      var nu = repaint(p), b = nu && nu.querySelector('[id^="cmt-"]'); if (b) b.style.display = 'block'; D.toast('Comment deleted');
    } } });
  }

  /* composer: the Home "Create Post" window, sent to this group */
  var _composeFor = null;
  function compose(mode) {
    var g = CUR && CUR.g; if (!g || needMember(g)) return;
    if (typeof window.showPostModal !== 'function') return;
    window._postImgs = []; window._postFiles = [];
    window.showPostModal(mode === 'img' ? 'img' : undefined);
    var ms = document.querySelectorAll('.modal-bg'), m = ms[ms.length - 1]; if (!m) return;
    m.setAttribute('data-gpk', g.key); _composeFor = g;
    var hd = m.querySelector('.modal-hdr'); if (hd && hd.firstChild && hd.firstChild.nodeType === 3) hd.firstChild.nodeValue = 'Post in this group ';
    var ta = m.querySelector('#postBody'); if (ta) ta.setAttribute('placeholder', g.deal ? 'Share a request, an offer or market news with the group…' : 'Ask a question or share an update with the group…');
    var cat = m.querySelector('#postCat'); if (cat) cat.value = mode === 'product' ? 'market' : mode === 'job' ? 'job' : g.deal ? 'market' : 'general';
    if (mode === 'file') setTimeout(function () { var f = m.querySelectorAll('input[type=file]')[1]; if (f) f.click(); }, 100);
  }
  function shrink(file) {
    return new Promise(function (res) {
      if (!file || !/^image\//.test(file.type)) return res(null);
      var r = new FileReader(); r.onerror = function () { res(null); };
      r.onload = function () { var im = new Image(); im.onerror = function () { res(null); }; im.onload = function () {
        var s = Math.min(1, 1000 / Math.max(im.width || 1, im.height || 1)), c = document.createElement('canvas'); c.width = Math.max(1, Math.round(im.width * s)); c.height = Math.max(1, Math.round(im.height * s));
        try { c.getContext('2d').drawImage(im, 0, 0, c.width, c.height); res(c.toDataURL('image/jpeg', 0.8)); } catch (e) { res(null); } }; im.src = r.result; };
      r.readAsDataURL(file);
    });
  }
  function submitCompose(m) {
    var g = _composeFor; if (!g || !CUR || CUR.g.key !== g.key) { m.remove(); return; }
    var body = (m.querySelector('#postBody') || {}).value || '', cat = (m.querySelector('#postCat') || {}).value || 'general';
    var inputs = m.querySelectorAll('input[type=file]'), imgFiles = inputs[0] ? Array.prototype.slice.call(inputs[0].files || []).slice(0, 4) : [], file = inputs[1] && inputs[1].files && inputs[1].files[0];
    body = body.trim();
    if (!body && !imgFiles.length && !file) { D.toast('Post cannot be empty'); return; }
    if (body.length > 5000) { D.toast('Posts can be up to 5,000 characters'); return; }
    var btn = m.querySelector('.btn-p'); if (btn) { if (btn.disabled) return; btn.disabled = true; }
    Promise.all(imgFiles.map(shrink)).then(function (imgs) {
      var p = { id: 9000000000000 + Date.now(), uid: me().id, cat: cat, body: body, ts: 'just now', likes: 0, rx: {}, cmt: 0, cm: [], sh: 0, views: 0, pin: false,
        imgs: imgs.filter(Boolean), files: file ? [{ name: file.name, size: file.size }] : [], own: true, at: new Date().toISOString() };
      window._postImgs = []; window._postFiles = [];
      m.remove(); _composeFor = null;
      if (g.live) {
        var r = hook('groupPost', { group: pub(g), op: 'create', post: p, imageFiles: imgFiles, file: file || null });
        if (!r || typeof r.then !== 'function') { D.toast('Posting in groups opens soon'); return; }
        r.then(function (saved) { if (saved && saved.id) p = Object.assign(p, saved); CUR.posts = order([p].concat(CUR.posts || [])); paintPane('disc'); D.toast('Post published! ✅'); }, function (e) { D.toast((e && e.message) || 'Could not publish — try again'); });
        return;
      }
      persist(g, p); CUR.posts = order([p].concat(CUR.posts || [])); paintPane('disc');
      var el = document.querySelector('#gpBox [data-gpp="' + p.id + '"]'); if (el) { el.classList.add('dbk-new'); }
      D.toast('Post published! ✅');
    });
  }

  function newListing() {
    var g = CUR && CUR.g; if (!g || needMember(g)) return;
    D.modal({ title: 'Post an RFQ or offer', body:
      '<div class="dbk-f"><label for="gpLk">Type *</label><select id="gpLk"><option value="rfq">🔍 Looking to buy (RFQ)</option><option value="sale">📦 For sale</option><option value="surplus">♻️ Surplus stock</option></select></div>' +
      '<div class="dbk-f"><label for="gpLt">Product or service *</label><input id="gpLt" data-req maxlength="120" placeholder="e.g. Metformin HCl BP — 2 MT"></div>' +
      '<div class="dbk-f"><label for="gpLd">Details *</label><textarea id="gpLd" data-req maxlength="400" placeholder="Specs, certificates (GMP, CEP, DMF), quantity, delivery"></textarea></div>' +
      '<div class="dbk-f"><label for="gpLp">Price (offers)</label><input id="gpLp" maxlength="40" placeholder="e.g. $5.10/kg or On request"></div>',
      primary: { label: 'Post to the group', onClick: function (bx) {
        if (!D.requireFields(bx)) return false;
        var kind = bx.querySelector('#gpLk').value, t = bx.querySelector('#gpLt').value.trim(), d = bx.querySelector('#gpLd').value.trim(), pr = bx.querySelector('#gpLp').value.trim();
        var l = kind === 'rfq' ? { id: 'u' + Date.now(), kind: 'rfq', uid: me().id, t: t, d: d, where: '🇪🇬 Egypt · just now', badge: 'NEW' }
          : { id: 'u' + Date.now(), kind: kind, uid: me().id, t: t, d: d, em: kind === 'surplus' ? '♻️' : '📦', certs: [], trust: ['📦 In stock'], price: pr || 'On request', moq: '🇪🇬 Egypt' };
        if (g.live) { var r = hook('groupListing', { group: pub(g), op: 'create', listing: l }); if (!r || typeof r.then !== 'function') { D.toast('Posting listings in groups opens soon'); return; } r.then(function () { CUR.listings = null; paintPane('listings'); D.toast('Posted to the group'); }, function (e) { D.toast((e && e.message) || 'Could not post — try again'); }); return; }
        var s = st(); (s.lst[g.key] = s.lst[g.key] || []).unshift(l); save(); paintPane('listings'); D.toast('Posted to the group');
      } } });
  }
  /* demo: the company page behind a listing (the seller's or buyer's company in the directory) */
  function demoCo(l) { var u = person(l.uid), X = window.dxDir, list = X && X.companies ? X.companies() : [], name = l.co || (u && u.company) || '';
    var c = list.find(function (x) { return x.name === name; }); return c ? { slug: c.slug, name: c.name } : name ? { slug: slug(name), name: name } : null; }
  function startDeal(l, msg, q) {   /* answering a listing starts a deal in the Deals center: a request for a quote on an offer, an offer on a request */
    var g = CUR.g, type = l.kind === 'rfq' ? 'surplus' : 'quote';
    if (g.live) return hook('groupListing', { group: pub(g), op: 'respond', listing: l, message: msg, price: q && q.price, lead: q && q.lead });
    var co = demoCo(l), X = window.dxDeals; if (!co || !X) return Promise.reject(new Error('This listing has no company page — message its author instead'));
    var d = X.create(type, co.slug, l.t, { listing: l.id, price: q && q.price, lead: q && q.lead }, msg || ''); if (!d) return Promise.reject(new Error(''));
    if (d.to && d.to.name === co.slug) { d.to.name = co.name; X.save(d); }
    return Promise.resolve(d.ref || d.id);
  }
  function listingAct(l, act) {
    var g = CUR.g, u = person(l.uid);
    if (act === 'close') {
      D.modal({ title: 'Close this listing?', body: '<div>It leaves the Listings tab for everyone. Deals already started stay in the Deals center.</div>', primary: { label: 'Yes, close it', danger: true, onClick: function () {
        if (g.live) { var r = hook('groupListing', { group: pub(g), op: 'close', listing: l }); if (r && r.then) r.then(function () { CUR.listings = null; paintPane('listings'); D.toast('Listing closed'); }, function (e) { D.toast((e && e.message) || 'Could not close — try again'); }); return; }
        var s = st(); s.lst[g.key] = (s.lst[g.key] || []).filter(function (x) { return x.id !== l.id; }); (s.closedL = s.closedL || {})[l.id] = 1; save(); paintPane('listings'); D.toast('Listing closed'); } } });
      return;
    }
    if (act === 'deals') { closeAnd(function () { if (window.dxDeals && window.dxDeals.center) window.dxDeals.center('received'); else if (window.goto) window.goto('companies'); }); return; }
    if (act === 'contact') {
      if (needMember(g)) return;
      D.modal({ title: 'Request a quote', body: '<p class="gp-muted"><span>For</span> <b data-noi18n>' + esc(l.t) + '</b>' + (l.co || (u && u.name) ? ' · <span data-noi18n>' + esc(l.co || u.name) + '</span>' : '') + '</p>' +
        '<div class="dbk-f"><label for="gpEq">Your request *</label><textarea id="gpEq" data-req maxlength="600" placeholder="Quantity, delivery terms, documents you need"></textarea></div>' +
        '<div class="gp-muted">It starts a quote request in your Deals center, sent on behalf of your company page.</div>',
        primary: { label: 'Send request', onClick: function (bx) {
          if (!D.requireFields(bx)) return false; var msg = bx.querySelector('#gpEq').value.trim();
          startDeal(l, msg).then(function () { if (!g.live) { st().quotes[l.id] = { msg: msg, at: new Date().toISOString() }; save(); } else l.answered = 1; paintPane('listings'); D.toast('Quote request sent — follow it in your Deals center'); },
            function (e) { if (e && e.message) D.toast(e.message); });
        } } });
      return;
    }
    if (act === 'quote') {
      if (needMember(g)) return;
      D.modal({ title: 'Send a quote', body: '<p class="gp-muted"><span>For</span> <b data-noi18n>' + esc(l.t) + '</b> · <span data-noi18n>' + esc(l.co || (u ? u.name : '')) + '</span></p>' +
        '<div class="dbk-f"><label for="gpQp">Price *</label><input id="gpQp" data-req maxlength="60" placeholder="e.g. $5.20/kg CIF Alexandria"></div>' +
        '<div class="dbk-f"><label for="gpQl">Lead time *</label><input id="gpQl" data-req maxlength="60" placeholder="e.g. 3 weeks"></div>' +
        '<div class="dbk-f"><label for="gpQm">Message</label><textarea id="gpQm" maxlength="600" placeholder="Certificates, validity, payment terms"></textarea></div>',
        primary: { label: 'Send quote', onClick: function (bx) {
          if (!D.requireFields(bx)) return false;
          var q = { price: bx.querySelector('#gpQp').value.trim(), lead: bx.querySelector('#gpQl').value.trim(), msg: bx.querySelector('#gpQm').value.trim(), at: new Date().toISOString() };
          startDeal(l, q.msg, q).then(function () { if (!g.live) { st().quotes[l.id] = q; save(); } else l.answered = 1; paintPane('listings'); D.toast('Quote sent to ' + (l.co || (u ? u.name : 'the buyer')) + ' — follow it in your Deals center'); },
            function (e) { if (e && e.message) D.toast(e.message); });
        } } });
    }
  }
  function closeAnd(fn) { if (typeof window.closeGroup === 'function') window.closeGroup(); setTimeout(fn, 0); }
  function connectTo(uid, btn) {
    var g0 = window.goto; window.goto = function () {};   /* the approved connect() re-renders the page it was called from; the group stays open */
    try { if (typeof window.connect === 'function') window.connect(uid); } finally { window.goto = g0; }
    if (btn) { var t = document.createElement('div'); t.innerHTML = connBtn(uid); btn.replaceWith(t.firstElementChild); }
  }
  function memberAct(uid, act, row) {
    var g = CUR ? CUR.g : null; if (!g) return;
    var u = person(uid), name = u ? u.name : 'member';
    if (act === 'msg') { closeAnd(function () { if (window.messageUser) window.messageUser(uid); else { window.__mxTo = name; window.goto('messages'); } }); return; }
    var s = st();
    var send = function (fin) {   /* live: the change is shown once the database accepted it */
      if (!g.live) return fin();
      var r = hook('groupMembers', { group: pub(g), op: act, uid: uid });
      if (!r || typeof r.then !== 'function') return fin();
      r.then(fin, function (e) { D.toast((window.dxLive && window.dxLive.friendly ? window.dxLive.friendly(e) : (e && e.message)) || 'Could not save — try again'); });
    };
    if (act === 'remove') {
      D.modal({ title: 'Remove ' + name + '?', body: '<div>They will lose access to this group.</div>', primary: { label: 'Remove', danger: true, onClick: function () { send(function () {
        if (!g.live) { (s.gone[g.key] = s.gone[g.key] || {})[uid] = 1; save(); }
        g.count = Math.max(0, g.count - 1); var mc = g.card && g.card.querySelector('.member-count'); if (mc) { var raw = otxt(mc); mc.textContent = fmtN(Math.max(0, num(raw) - 1)) + (/members/.test(raw) ? ' members' : ''); }
        refresh(); D.toast(name + ' removed from the group'); }); } } });
      return;
    }
    send(function () {
      if (!g.live) { (s.roles[g.key] = s.roles[g.key] || {})[uid] = act; save(); }
      refresh(); D.toast(act === 'admin' ? name + ' is now an admin' : act === 'subadmin' ? name + ' is now a sub-admin' : name + ' is now a member');
    });
  }

  /* ───────────────────────── one click handler (capture: before the approved inline handlers) ───────────────────────── */
  function inGroup(el) { return el && el.closest && el.closest('#gpBox'); }
  function openFile(fc) {
    var u = fc.dataset.url || '';
    if (/^https?:\/\//i.test(u)) { window.open(u, '_blank', 'noopener'); return; }
    D.toast('📎 ' + otxt(fc.querySelector('.file-chip-name')) + ' — sample file: attachments open from the live app');
  }
  document.addEventListener('keydown', function (e) { var fc = (e.key === 'Enter' || e.key === ' ') && e.target.closest && e.target.closest('#gpBox .file-chip[data-gpf]'); if (fc) { e.preventDefault(); openFile(fc); } }, true);
  document.addEventListener('click', function (e) {
    var fc = e.target.closest && e.target.closest('#gpBox .file-chip[data-gpf]'); if (fc) { e.preventDefault(); e.stopPropagation(); openFile(fc); return; }
    var t = e.target; if (!t || !t.closest) return;
    var live = isLive();

    /* cards and side rows on the groups page */
    var card = t.closest('#gx .gcard');
    if (card && !t.closest('.gcard-btn') && !t.closest('.dx-entity')) {   /* a person's or company's name on the card opens that page, not the group (G-16) */
      LAST_CARD = card;
      if (card.dataset.gid || live) return;   /* live cards: the adapter opens them (dxLive.openGroup) */
      e.preventDefault(); e.stopPropagation(); open(card); return;
    }
    var mg = t.closest('#gx .mygroup');
    if (mg && !live) { var c2 = cardByTitle(otxt(mg.querySelector('.mg-name'))); if (c2) { e.preventDefault(); e.stopPropagation(); open(c2); } return; }

    /* the header's join / leave / request button (demo) */
    var lb = t.closest('#groupDetail #memberActions [data-gpj]');
    if (lb && lb.dataset.gpj && CUR && !CUR.g.live) { e.preventDefault(); e.stopPropagation(); headerJoin(lb.dataset.gpj); return; }

    /* approved windows that act on "the current group" (demo): leave, save settings, archive, delete */
    if (!live && CUR && !CUR.g.live) {
      var g = CUR.g;
      if (t.closest('#leaveConfirm .cp-btn-confirm')) { e.preventDefault(); e.stopPropagation(); setMember(g.card, false); window.toggleLeaveConfirm(); window.closeGroup(); return; }
      if (t.closest('#tab-settings .btn-create')) {
        e.preventDefault(); e.stopPropagation();
        var nm = document.querySelector('#tab-settings .field-input'), ds = document.querySelector('#tab-settings .field-textarea'), v = nm ? nm.value.trim() : '';
        if (!v) { nm.classList.add('dbk-err'); D.toast('Group name is required'); return; }
        nm.classList.remove('dbk-err');
        var key = g.key; g.card.dataset.gk = key;
        g.card.querySelector('.gcard-title').textContent = v; var cd = g.card.querySelector('.gcard-desc'); if (cd && ds) cd.textContent = ds.value.trim();
        st().ov[key] = { t: v, d: ds ? ds.value.trim() : '' }; save();
        refresh(); D.toast('Group settings saved'); return;
      }
      if (t.closest('.choice-btn.archive')) {
        e.preventDefault(); e.stopPropagation(); g.card.dataset.gk = g.key; st().arch[g.key] = 1; save(); archiveCard(g.card);
        window.closeGroup(); D.toast('Group archived — restore it anytime from settings'); return;
      }
      if (t.closest('#deleteConfirmBtn')) {
        e.preventDefault(); e.stopPropagation();
        var btn = document.getElementById('deleteConfirmBtn'); if (btn.disabled) return;
        st().del[g.key] = 1; save(); g.card.remove();
        window.closeDelete(); window.closeGroup(); D.toast(g.title + ' was deleted permanently'); CUR = null; return;
      }
      var rb = t.closest('#tab-reports .mod-btn[data-gpr]');
      if (rb) {
        e.preventDefault(); e.stopPropagation();
        var item = rb.closest('.mod-item'), rid = item.dataset.rid, remove = rb.dataset.gpr === 'remove', s = st();
        (s.rep['done:' + g.key] = s.rep['done:' + g.key] || {})[rid] = remove ? 'removed' : 'dismissed';
        var rec = (s.rep[g.key] || []).find(function (r) { return r.id === rid; });
        if (remove && rec && rec.pid) { var p0 = findPost(rec.pid) || demoPosts(g).find(function (x) { return x.id === rec.pid; }); if (p0) { p0.del = 1; persist(g, p0); } }
        save(); paintManage(g); if (remove && rec && rec.pid) { CUR.posts = null; if (CUR.tab === 'disc') paintPane('disc'); }
        D.toast(remove ? (item.querySelector('.mod-icon') && /👤/.test(item.querySelector('.mod-icon').textContent) ? 'Member removed from the group' : 'Post removed and the author warned') : 'Report dismissed');
        return;
      }
    }
    var ddm = t.closest('#groupDetail .member-row[data-uid] .dd-item[data-gpd]');
    if (ddm) { e.preventDefault(); e.stopPropagation(); var dm = ddm.closest('.dropdown-menu'); if (dm) dm.classList.remove('show'); memberAct(+ddm.closest('.member-row').dataset.uid, ddm.dataset.gpd === 'msg' ? 'msg' : ddm.dataset.gpd, ddm.closest('.member-row')); return; }

    var B = inGroup(t); if (!B || !CUR) return;
    var gg = CUR.g;
    var tab = t.closest('[data-gpt]'); if (tab) { show(tab.dataset.gpt); return; }
    var pf = t.closest('[data-gp]'); if (pf && !t.closest('.post')) { e.preventDefault(); e.stopPropagation(); var uid = +pf.dataset.gp; if (person(uid)) closeAnd(function () { window.gotoProfile(uid); }); return; }
    var a = t.closest('[data-gpa]');
    if (a) {
      e.preventDefault(); e.stopPropagation(); var act = a.dataset.gpa;
      if (act === 'declineinv') { declineInvite(); return; }
      if (act === 'join' || act === 'request' || act === 'accept' || act === 'cancel') headerJoin(act);
      else if (act === 'msg') memberAct(+a.dataset.uid, 'msg');
      else if (act === 'conn') connectTo(+a.dataset.uid, a);
      else if (act === 'newlisting') newListing();
      else if (act === 'more') loadMore();
      return;
    }
    var la = t.closest('[data-gpl]'); if (la) { e.preventDefault(); e.stopPropagation(); var lc = la.closest('[data-lid]'), all = gg.live ? (CUR.listings || []) : demoListings(gg), l = lc && all.find(function (x) { return String(x.id) === lc.dataset.lid; }); if (l && !la.disabled) listingAct(l, la.dataset.gpl); return; }
    var comp = t.closest('.gp-comp .comp-btn, .gp-comp .comp-act');
    if (comp) { e.preventDefault(); e.stopPropagation(); var modes = ['img', 'file', 'product', 'job'], idx = Array.prototype.indexOf.call(B.querySelectorAll('.gp-comp .comp-act'), comp); compose(idx >= 0 ? modes[idx] : null); return; }
    var pe = t.closest('[data-gpp]'); if (!pe) return;
    var p = findPost(+pe.dataset.gpp); if (!p) return;
    var m = t.closest('[data-gpm]');
    if (!m) { if (t.closest('.pact[id^="like-"]') && !t.closest('.rxn-panel')) { e.preventDefault(); e.stopPropagation(); react(p, 'like', true); } return; }
    e.preventDefault(); e.stopPropagation();
    var menu = m.closest('[id^="pm-"]'); if (menu) menu.style.display = 'none';
    switch (m.dataset.gpm) {
      case 'react': react(p, m.dataset.rk || 'like', !m.dataset.rk); break;
      case 'cmts': toggleCmts(p); break;
      case 'send': addComment(p, pe.querySelector('.cmt-input')); break;
      case 'reactors': reactors(p); break;
      case 'more': var pb = pe.querySelector('.post-body'); if (pb) { pb.style.whiteSpace = 'pre-wrap'; pb.textContent = p.body; } break;
      case 'share': sharePost(p); break;
      case 'save': savePost(p); break;
      case 'report': report(p); break;
      case 'link': copyLink(p); break;
      case 'edit': editPost(p); break;
      case 'delete': deletePost(p, 'delete'); break;
      case 'remove': D.modal({ title: 'Remove this post?', body: '<div>It breaks the group rules and will be removed for everyone.</div>', primary: { label: 'Remove', danger: true, onClick: function () { deletePost(p, 'remove'); } } }); break;
      case 'pin': pin(p); break;
      case 'clike': commentAct(p, m, 'like'); break;
      case 'reply': commentAct(p, m, 'reply'); break;
      case 'cdel': commentDelete(p, m); break;
    }
  }, true);
  /* the composer window's Post button, when it was opened for a group */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.modal-bg[data-gpk] .btn-p'); if (!b) return;
    e.preventDefault(); e.stopPropagation(); submitCompose(b.closest('.modal-bg'));
  }, true);
  /* keyboard: Enter sends a comment; Enter / Space press our role=button controls; arrows move between tabs */
  document.addEventListener('keydown', function (e) {
    var t = e.target; if (!inGroup(t) || !CUR) return;
    if (t.classList && t.classList.contains('cmt-input')) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.stopPropagation(); var pe = t.closest('[data-gpp]'), p = pe && findPost(+pe.dataset.gpp); if (p) addComment(p, t); }
      return;
    }
    if (t.dataset && t.dataset.gpt && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) {
      var tabs = Array.prototype.slice.call(document.querySelectorAll('#gpBox [data-gpt]')), i = tabs.indexOf(t), rtl = document.documentElement.dir === 'rtl';
      var n = tabs[(i + ((e.key === 'ArrowRight') !== rtl ? 1 : -1) + tabs.length) % tabs.length]; if (n) { e.preventDefault(); n.focus(); show(n.dataset.gpt); } return;
    }
    if ((e.key === 'Enter' || e.key === ' ') && t.getAttribute && t.getAttribute('role') === 'button' && t.tagName !== 'BUTTON') { e.preventDefault(); t.click(); }
    if ((e.key === 'Enter' || e.key === ' ') && t.dataset && t.dataset.gpt) { e.preventDefault(); t.click(); }
  }, true);
  document.addEventListener('input', function (e) {
    var t = e.target; if (!t.classList || !t.classList.contains('gp-msearch')) return;
    var q = t.value.trim().toLowerCase(), list = t.closest('[data-pane], #tab-members'), shown = 0; if (!list) return;
    list.querySelectorAll('.member-list .member-row').forEach(function (r) { var ok = !q || r.textContent.toLowerCase().indexOf(q) >= 0; r.style.display = ok ? '' : 'none'; if (ok) shown++; });
    var nr = list.querySelector('.gp-nores'); if (nr) nr.hidden = shown > 0;
  });

  /* ───────────────────────── the groups page: cards that were missing, and what you changed (demo) ───────────────────────── */
  function archiveCard(card) {
    card.style.opacity = '.55';
    var badge = card.querySelector('.priority-badge') || document.createElement('div'); badge.className = 'priority-badge'; badge.textContent = '📦 Archived';
    if (!badge.parentElement) card.insertBefore(badge, card.firstChild);
  }
  function makeCard(tpl, o) {
    var c = tpl.cloneNode(true);
    ['.priority-badge', '.why-banner'].forEach(function (s) { var x = c.querySelector(s); if (x) x.remove(); });
    c.removeAttribute('onclick'); c.dataset.gk = o.k; c.style.opacity = '';
    var by = o.inv && person(o.inv), body = c.querySelector('.gcard-body');
    if (by && body) body.insertAdjacentHTML('afterbegin', '<div class="why-banner">✉️ <span>Invitation from</span> <span data-noi18n>' + esc(by.name) + '</span></div>');
    var cv = c.querySelector('.gcard-cover'); if (cv) { cv.textContent = o.emoji; cv.style.background = o.bg; }
    c.querySelector('.gcard-title').textContent = o.t;
    var d = c.querySelector('.gcard-desc'); if (d) d.textContent = o.desc;
    var m = c.querySelector('.gcard-meta'); if (m) m.innerHTML = '<span class="gtag ' + (o.deal ? 'gtag-deal">DEAL ROOM' : 'gtag-discuss">DISCUSS') + '</span><span class="gtag ' + (o.priv ? 'gtag-private">Private' : 'gtag-public">Public') + '</span>';
    var sig = c.querySelector('.activity-signal'); if (sig) { sig.className = 'activity-signal'; sig.textContent = o.signal || ''; }
    var f = c.querySelector('.member-faces'); if (f) f.innerHTML = (o.faces || []).map(function (x) { return '<div class="mini-av" style="background:' + x[1] + '">' + esc(x[0]) + '</div>'; }).join('');
    var mc = c.querySelector('.member-count'); if (mc) mc.textContent = fmtN(o.count) + (o.countWord ? ' members' : '');
    var b = c.querySelector('.gcard-btn'); if (b) { b.className = 'gcard-btn ' + (o.joined ? 'btn-joined' : 'btn-join'); b.textContent = o.joined ? '✓ Joined' : '+ Join'; }
    if (!o.joined && o.priv) paintCard(c, o.inv ? 'accept' : st().req[o.k] ? 'pending' : 'request');
    return c;
  }
  function initPage(root) {
    if (root.__grp) return; root.__grp = 1;
    if (isLive()) return;
    var s = st(), first = root.querySelector('.gx-groups-grid'), tpl = root.querySelector('.gx-groups-grid .gcard');
    cards().forEach(function (c) { var k = cardKey(c); if (BY_KEY[k]) c.dataset.gk = k; });
    /* "Your Groups" lists four groups; the fourth (Cosmetics Formulators) had no card, so it could not be opened from the list */
    var grids = root.querySelectorAll('.gx-groups-grid'), jn = ls('groups_joined'), lf = ls('groups_left');
    SEED.forEach(function (sd) {
      if (!sd.card || cardByKey(sd.k) || !first || !tpl) return;
      var joined = jn.indexOf(sd.t) >= 0 ? true : lf.indexOf(sd.t) >= 0 ? false : sd.card.joined !== false;
      var c = makeCard(tpl, { k: sd.k, t: sd.t, emoji: sd.card.emoji, bg: sd.card.bg, desc: sd.card.desc, count: sd.card.count + (joined && sd.card.joined === false ? 1 : 0), faces: sd.card.faces, signal: sd.card.signal,
        joined: joined, priv: sd.card.priv, deal: sd.card.deal, inv: joined || (st().noinv || {})[sd.k] ? null : sd.inv, countWord: sd.card.joined === false });
      (grids[sd.card.grid || 0] || first).appendChild(c);
    });
    /* groups you created */
    (s.made || []).forEach(function (m) {
      if (cardByKey(m.k) || !first || !tpl) return;
      var c = makeCard(tpl, { k: m.k, t: m.t, emoji: m.emoji || (m.deal ? '🤝' : '💬'), bg: 'linear-gradient(135deg,#0a1f4d,#1a56db)', desc: m.d || 'New group', count: m.count || 1, countWord: 1, deal: m.deal, priv: m.priv, signal: 'You are the admin', joined: true });
      first.insertBefore(c, first.firstChild);
    });
    cards().forEach(function (c) {
      var k = cardKey(c);
      if (s.del[k]) { c.remove(); return; }
      var ov = s.ov[k]; if (ov) { c.dataset.gk = k; c.querySelector('.gcard-title').textContent = ov.t; var d = c.querySelector('.gcard-desc'); if (d) d.textContent = ov.d; }
      if (s.arch[k]) archiveCard(c);
      if (!cardJoined(c) && /private/i.test(otxt(c.querySelector('.gcard-meta')))) paintCard(c, idleState(c));
    });
  }
  /* creating a group (demo): the approved window makes the card; it is remembered so it is still there after a reload */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#createModal .modal-footer .btn-create'); if (!b || isLive()) return;
    var M = document.getElementById('createModal'), name = ((M.querySelector('.field-input') || {}).value || '').trim(), desc = ((M.querySelector('.field-textarea') || {}).value || '').trim();
    if (!name) return;
    var pos = function (sel) { var all = [].slice.call(M.querySelectorAll(sel)); return all.indexOf(M.querySelector(sel + '.selected')); };
    var rec = { k: 'u' + Date.now(), t: name, d: desc, deal: pos('.type-opt') === 1, priv: pos('.privacy-opt') === 1, at: new Date().toISOString().slice(0, 10), count: 1 };
    setTimeout(function () {
      var c = cards().find(function (x) { return !x.dataset.gk && !x.dataset.gid && otxt(x.querySelector('.gcard-title')) === name; }); if (!c) return;
      c.dataset.gk = rec.k; var s = st(); s.made.push(rec); save();
      var gj = {}; try { gj = D.store.get('groupsJoined', {}) || {}; } catch (er) {} gj[name] = true; D.store.set('groupsJoined', gj);
    }, 0);
  }, true);

  /* ───────────────────────── connecting to the approved code ───────────────────────── */
  function wire() {
    var o = window.openGroup;
    if (typeof o === 'function' && !o.__grp) {
      var w = function (role) { var r = o.apply(this, arguments); try { afterOpen(role); } catch (er) { if (window.console) console.warn('[groups] open', er); } return r; };
      w.__grp = 1; window.openGroup = w;
    }
    var sw = window.switchTab;
    if (typeof sw === 'function' && !sw.__grp) {   /* the Manage panel's tabs: only switch their own row (the group's tabs use the same look) */
      var w2 = function (el, name) {
        var mine = el && el.closest && el.closest('.panel-tabs'), keep = [];
        document.querySelectorAll('#gx .gx-ptab.active').forEach(function (x) { if (!mine || !mine.contains(x)) keep.push(x); });
        var r = sw.apply(this, arguments); keep.forEach(function (x) { x.classList.add('active'); }); return r;
      };
      w2.__grp = 1; window.switchTab = w2;
    }
    var cg = window.closeGroup;
    if (typeof cg === 'function' && !cg.__grp) { var w4 = function () { var r = cg.apply(this, arguments); onClosed(); return r; }; w4.__grp = 1; window.closeGroup = w4; }
    var cd = window.checkDeleteInput;
    if (typeof cd === 'function' && !cd.__grp) {
      var w3 = function () { if (!CUR || CUR.g.live || isLive()) return cd.apply(this, arguments); var v = document.getElementById('deleteConfirmInput').value.trim(), btn = document.getElementById('deleteConfirmBtn'); var ok = v === CUR.g.title; btn.disabled = !ok; btn.style.opacity = ok ? 1 : 0.4; };
      w3.__grp = 1; window.checkDeleteInput = w3;
    }
  }
  /* demo: the "Your Groups" side list and the "My Groups (N)" chip follow what you joined and left (G-10); the live app's
     adapter draws them from the database */
  function syncMine(root) {
    if (isLive() || !root) return;
    var side = root.querySelector('.gx-sidebar'), joined = cards().filter(cardJoined), names = joined.map(function (c) { return otxt(c.querySelector('.gcard-title')); });
    if (side) {
      var rows = Array.prototype.slice.call(side.querySelectorAll('.mygroup')), tpl = rows[0] || null, at = side.querySelector('.sb-divider');
      rows.forEach(function (r) { if (names.indexOf(otxt(r.querySelector('.mg-name'))) < 0) r.remove(); });
      var have = Array.prototype.map.call(side.querySelectorAll('.mygroup .mg-name'), otxt);
      if (tpl && at) joined.forEach(function (c, i) { var t = names[i]; if (have.indexOf(t) >= 0) return;
        var r = tpl.cloneNode(true); r.removeAttribute('onclick'); r.style.cursor = 'pointer';
        var ic = r.querySelector('.mg-ic'), cv = c.querySelector('.gcard-cover'); if (ic) { ic.textContent = cv ? Array.from(txt(cv)).slice(0, 2).join('').trim() : '👥'; ic.style.background = '#eef2ff'; }
        var nm = r.querySelector('.mg-name'); if (nm) nm.textContent = t; var mt = r.querySelector('.mg-meta'); if (mt) { mt.removeAttribute('style'); mt.textContent = 'Quiet today'; }
        var bd = r.querySelector('.mg-badge'); if (bd) bd.remove(); at.parentNode.insertBefore(r, at); have.push(t); });
    }
    Array.prototype.forEach.call(root.querySelectorAll('.cat-filter .cf-tag'), function (c) {
      var w = document.createTreeWalker(c, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var n = w.currentNode, o = (window.dxI18nOrig && window.dxI18nOrig(n)) || n.nodeValue;
        if (/My Groups \(\d+\)/.test(o)) { var v = o.replace(/\(\d+\)/, '(' + joined.length + ')'); if (v !== o) n.nodeValue = v; return; } }
    });
  }
  C.onRender('groups-inside', function () {
    var root = document.getElementById('gx'); if (!root) return;
    wire(); initPage(root); syncMine(root); pageExtras(root);
  });
  document.addEventListener('dx:beforepage', function () { var lc = document.getElementById('leaveConfirm'); if (lc) lc.classList.remove('show'); });


  /* ===== AREA community: groups (G-04 … G-15) — finding groups (search, sector, country, View all), the Back button, the
     Manage panel (member search, join requests, settings, archive), per-group notifications, creating a group with its topic,
     country and rules. Demo: what you change is kept in this browser; live: the adapter (dxLiveHook) keeps it in the database. ===== */
  var CNAME = { EG: 'Egypt', AE: 'UAE', SA: 'Saudi Arabia', KW: 'Kuwait', QA: 'Qatar', BH: 'Bahrain', OM: 'Oman', JO: 'Jordan', LB: 'Lebanon', IQ: 'Iraq', MA: 'Morocco', DZ: 'Algeria', TN: 'Tunisia', LY: 'Libya', SD: 'Sudan', IN: 'India', CN: 'China' };
  var CFLAG = { EG: '🇪🇬', AE: '🇦🇪', SA: '🇸🇦', KW: '🇰🇼', QA: '🇶🇦', BH: '🇧🇭', OM: '🇴🇲', JO: '🇯🇴', LB: '🇱🇧', IQ: '🇮🇶', MA: '🇲🇦', DZ: '🇩🇿', TN: '🇹🇳', LY: '🇱🇾', SD: '🇸🇩', IN: '🇮🇳', CN: '🇨🇳' };
  var SECTORS = { pharma: '💊 Pharma', cosmetics: '💄 Cosmetics', devices: '🩺 Medical devices', supplements: '🥗 Supplements', other: '🧭 Other' };
  var GCC = ['SA', 'AE', 'KW', 'QA', 'BH', 'OM'];
  function inferSector(t) { t = String(t || ''); return /cosmetic|skin|beauty|تجميل/i.test(t) ? 'cosmetics' : /nutraceut|supplement|مكمل/i.test(t) ? 'supplements' : /medical device|devices|أجهزة/i.test(t) ? 'devices' : 'pharma'; }
  function marketsTo(m) { var out = []; String(m || '').split(/·|,/).forEach(function (x) { x = x.trim(); var add = /^GCC|Gulf$/i.test(x) ? GCC : /^MENA$/i.test(x) ? ['EG', 'SA', 'AE', 'JO'] : Object.keys(CNAME).filter(function (k) { return CNAME[k].toLowerCase() === x.toLowerCase(); });
    add.forEach(function (c) { if (out.indexOf(c) < 0) out.push(c); }); }); return out; }
  function tagCard(card) {   /* demo: the sector and countries of a sample group or one you made (the live adapter writes them itself) */
    if (!card || card.dataset.gid || card.dataset.tagged) return;
    var k = cardKey(card), sd = BY_KEY[k], made = st().made.find(function (m) { return m.k === k; }), ov = st().ov[k] || {};
    var text = otxt(card.querySelector('.gcard-title')) + ' ' + otxt(card.querySelector('.gcard-desc'));
    card.dataset.sector = ov.sector || (made && made.sector) || (sd && sd.sector) || inferSector(text);
    card.dataset.country = (ov.country || (made && made.country) || (sd ? marketsTo(sd.markets) : marketsTo(/egypt/i.test(text) ? 'Egypt' : ''))).join(',');
    card.dataset.post = ov.post || (made && made.post) || 'members';
    card.dataset.find = (text + ' ' + (ov.d || '') + ' ' + ((sd && sd.about) || '') + ' ' + ((sd && sd.focus) || []).join(' ') + ' ' + ((made && made.d) || '')).toLowerCase();
    if (st().arch[k]) card.dataset.archived = '1'; else delete card.dataset.archived;
    if (ov.priv != null) { var m = card.querySelector('.gcard-meta .gtag-public, .gcard-meta .gtag-private'); if (m) { m.className = 'gtag ' + (ov.priv ? 'gtag-private' : 'gtag-public'); m.textContent = ov.priv ? 'Private' : 'Public'; } }
    card.dataset.tagged = '1';
  }

  /* ── finding groups: one filter for the chips, the search, the country and "View all" ── */
  var GF = { chip: 'all', q: '', country: null, sec: null };
  function chipKey(t) { return (window.dxOrigText ? window.dxOrigText(t) : t.textContent).replace(/\s+/g, ' ').trim().replace(/^[^A-Za-z]+/, '').replace(/\s*\(\d+\)$/, '').replace(/ ✕$/, '').toLowerCase(); }
  function words(q) { return String(q || '').toLowerCase().split(/\s+/).filter(Boolean); }
  function sections(root) { return [].filter.call(root.querySelectorAll('.main .sec-hdr'), function (h) { return h.nextElementSibling && h.nextElementSibling.querySelector('.gcard'); }); }
  function applyFilter() {
    var root = document.getElementById('gx'); if (!root) return;
    var qw = words(GF.q), secs = sections(root), shown = 0;
    secs.forEach(function (h, i) {
      var grid = h.nextElementSibling, any = 0;
      [].forEach.call(grid.querySelectorAll('.gcard'), function (c) {
        tagCard(c);
        var joined = cardJoined(c), deal = !!c.querySelector('.gtag-deal'), sector = c.dataset.sector || inferSector(c.textContent), countries = (c.dataset.country || '').split(',');
        var text = (otxt(c.querySelector('.gcard-title')) + ' ' + otxt(c.querySelector('.gcard-desc')) + ' ' + (c.dataset.find || '')).toLowerCase();
        var ok = GF.chip === 'my groups' ? joined : GF.chip === 'discussion' ? !deal : GF.chip === 'deal rooms' ? deal : GF.chip === 'pharma' ? sector === 'pharma' : GF.chip === 'cosmetics' ? sector === 'cosmetics' : true;
        if (ok && GF.country) ok = countries.indexOf(GF.country) >= 0;
        if (ok && qw.length) ok = qw.every(function (w) { return text.indexOf(w) >= 0; });
        if (ok && c.dataset.archived === '1' && !joined) ok = false;                 /* archived: hidden from discovery */
        if (ok && GF.sec != null && GF.sec !== i) ok = false;
        c.style.display = ok ? '' : 'none'; if (ok) { any++; shown++; }
      });
      h.style.display = grid.style.display = any ? '' : 'none';
      var all = h.querySelector('.sec-all'); if (all) { if (!all.dataset.orig) all.dataset.orig = (window.dxOrigText ? window.dxOrigText(all) : all.textContent).trim();
        var v = GF.sec === i ? '← All groups' : all.dataset.orig; if (all.textContent !== v && (GF.sec === i || all.dataset.was)) { all.textContent = v; all.dataset.was = GF.sec === i ? '1' : ''; } }
    });
    var main = root.querySelector('.main'), none = root.querySelector('.gx-none');
    if (!shown && main) {
      if (!none) { none = document.createElement('div'); none.className = 'gx-none'; main.appendChild(none); }
      var where = GF.country ? ' in ' + (CNAME[GF.country] || GF.country) : '';
      none.innerHTML = '<b>' + (qw.length ? 'No groups found' : 'No groups' + where + ' yet') + '</b><p>' + (qw.length ? 'Try other words — or start the group yourself.' : 'Be the first to start one.') + '</p><button type="button" class="btn-manage" data-gxa="create">➕ Create Group</button>';
      none.style.display = '';
    } else if (none) none.style.display = 'none';
  }
  function setChipOn(t) { document.querySelectorAll('#gx .cat-filter .cf-tag').forEach(function (x) { x.classList.toggle('on', x === t); }); }
  function countryChoice(chipEl) {
    var have = {}; cards().forEach(function (c) { tagCard(c); (c.dataset.country || '').split(',').filter(Boolean).forEach(function (k) { have[k] = (have[k] || 0) + 1; }); });
    var list = ['EG', 'AE', 'SA', 'KW', 'QA', 'BH', 'OM', 'JO', 'LB', 'IQ', 'MA', 'DZ', 'TN', 'LY', 'SD'];
    var m = D.modal({ title: '🌍 Groups by country', secondary: 'Close', body: '<div class="gp-cgrid">' + list.map(function (c) {
      return '<button type="button" class="gp-cbtn' + (GF.country === c ? ' on' : '') + '" data-c="' + c + '"><span>' + CFLAG[c] + ' ' + esc(CNAME[c]) + '</span><small>' + (have[c] || 0) + '</small></button>'; }).join('') +
      '</div><button type="button" class="gp-cbtn gp-call" data-c="">All countries</button>' });
    m.el.addEventListener('click', function (e) { var b = e.target.closest('[data-c]'); if (!b) return; m.close();
      GF.country = b.dataset.c || null; GF.chip = 'all'; GF.sec = null; setChipOn(GF.country ? chipEl : document.querySelector('#gx .cat-filter .cf-tag'));
      var w = document.createTreeWalker(chipEl, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var n = w.currentNode; if (/[A-Za-z]/.test(n.nodeValue)) { n.nodeValue = GF.country ? '🌍 ' + CNAME[GF.country] + ' ✕' : '🌍 By Country'; if (window.dxI18nAdopt) window.dxI18nAdopt(n); break; } }
      applyFilter(); });
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('#gx .cat-filter .cf-tag'); if (!t) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var k = chipKey(t);
    if (k === 'by country' || /^(egypt|uae|saudi|kuwait|qatar|bahrain|oman|jordan|lebanon|iraq|morocco|algeria|tunisia|libya|sudan)/.test(k)) {
      countryChoice(t); return; }
    GF.chip = k === 'all groups' ? 'all' : k; GF.sec = null;
    if (k === 'all groups' && GF.country) { GF.country = null; document.querySelectorAll('#gx .cat-filter .cf-tag').forEach(function (c) { var w = document.createTreeWalker(c, NodeFilter.SHOW_TEXT); while (w.nextNode()) { var n = w.currentNode, o = (window.dxI18nOrig && window.dxI18nOrig(n)) || n.nodeValue; if (/^🌍 .+ ✕$/.test(o)) { n.nodeValue = '🌍 By Country'; if (window.dxI18nAdopt) window.dxI18nAdopt(n); } } }); }
    setChipOn(t); applyFilter();
  }, true);
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('#gx .main .sec-all'); if (!a) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var root = document.getElementById('gx'), i = sections(root).indexOf(a.closest('.sec-hdr'));
    GF.sec = GF.sec === i ? null : i; applyFilter(); var h = a.closest('.sec-hdr'); if (h) h.scrollIntoView({ block: 'start' });
  }, true);
  document.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('#gx [data-gxa="create"]'); if (b && window.openCreate) window.openCreate(); });
  function searchBar(root) {
    if (root.querySelector('.gx-searchbar')) return; var cf = root.querySelector('.cat-filter'); if (!cf) return;
    var bar = document.createElement('div'); bar.className = 'gx-searchbar';
    bar.innerHTML = '<input type="search" class="gx-q" placeholder="Search groups by name or topic…" aria-label="Search groups">';
    cf.parentNode.insertBefore(bar, cf.nextSibling);
    var q = bar.querySelector('.gx-q'), tmr = null;
    function go() { GF.q = q.value.trim(); GF.sec = null; applyFilter();
      if (isLive() && GF.q.length >= 2) { var r = hook('groupSearch', { q: GF.q }); if (r && r.then) r.then(function () { applyFilter(); }, function () {}); } }
    q.addEventListener('input', function () { clearTimeout(tmr); tmr = setTimeout(go, isLive() ? 350 : 120); });
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter') { clearTimeout(tmr); go(); } });
  }
  window.dxGroupsFilter = applyFilter;
  document.addEventListener('dx:page', function (e) { if (e.detail && e.detail.page === 'groups' && GF.sec != null) { GF.sec = null; applyFilter(); } });   /* a new visit shows every section again */

  /* ── demo: the member numbers on the sample cards are the members the demo has (the header, Members and Manage agree) ── */
  function demoCounts() {
    if (isLive()) return;
    cards().forEach(function (c) { var k = cardKey(c), sd = BY_KEY[k]; if (!sd || c.dataset.counted) return; c.dataset.counted = '1';
      var g0 = { key: k, seed: sd, member: cardJoined(c), role: null }, n = demoMembers(g0).length;
      var mc = c.querySelector('.member-count'); if (mc) mc.textContent = fmtN(n) + (n === 1 ? ' member' : ' members');
      var sg = c.querySelector('.activity-signal'), so = otxt(sg); if (sg && /\d[\d,]*\s+members/.test(so)) sg.textContent = so.replace(/\d[\d,]*\s+members/, fmtN(n) + (n === 1 ? ' member' : ' members')); });   /* the English original, in either language */
  }

  /* ── the browser's Back button closes an open group (and stays in the app) ── */
  var HIST = false;
  function pushOpen() { try { if (!HIST) { history.pushState({ dxGroup: 1 }, ''); HIST = true; } } catch (e) {} }
  window.addEventListener('popstate', function () {
    if (!HIST) return; HIST = false;
    var gd = document.getElementById('groupDetail'); if (gd && gd.classList.contains('show') && window.closeGroup) window.closeGroup();
  });
  function onClosed() { if (HIST) { HIST = false; try { if (history.state && history.state.dxGroup) history.back(); } catch (e) {} } }

  /* ── Manage: member search, join requests, settings (rules, privacy, who posts, sector, countries), archive ── */
  var SEED_REQS = { reg: [{ uid: 6, note: 'I handle cosmetic notifications at Beauty Lab and would like to learn from the RA team.', at: '2h ago' }, { uid: 4, note: '', at: '1d ago' }] };
  function demoReqs(g) { var s = st(), done = (s.reqs[g.key] || {}); return (SEED_REQS[g.key] || []).filter(function (r) { return !done[r.uid] && person(r.uid); }); }
  function manageExtras(g) {
    var gd = document.getElementById('groupDetail'); if (!gd) return;
    var tm = gd.querySelector('#tab-members');
    var span = tm && tm.querySelector('.member-list-title .member-search:not(input)');
    if (span) { var inp = document.createElement('input'); inp.type = 'search'; inp.className = 'member-search gp-msearch'; inp.placeholder = '🔍 Search members'; inp.setAttribute('aria-label', 'Search members'); span.replaceWith(inp); }
    var tabs = gd.querySelector('#managePanel .panel-tabs');
    if (tabs && !tabs.querySelector('[data-gpq-tab]')) {
      tabs.insertAdjacentHTML('beforeend', '<div class="gx-ptab" data-gpq-tab="1" role="tab" tabindex="0">📨 Requests <span class="ptab-badge dx-rq-badge" style="display:none"></span></div>');
      var mp = gd.querySelector('#managePanel'); mp.insertAdjacentHTML('beforeend', '<div class="panel-body" id="tab-requests" style="display:none"><div class="mod-queue"></div></div>');
    }
    settingsFields(g);
    if (!g.live) paintRequests(g);
  }
  function paintRequests(g) {
    var q = document.querySelector('#tab-requests .mod-queue'); if (!q) return;
    var list = demoReqs(g);
    q.innerHTML = list.length ? list.map(function (r) { var u = person(r.uid);
      return '<div class="mod-item req-row" data-uid="' + r.uid + '"><div class="mod-icon">👤</div><div class="mod-content"><div class="mod-title"><b data-noi18n>' + esc(u.name) + '</b> <span>asked to join</span></div>' +
        '<div class="mod-meta"><span data-noi18n>' + esc(headline(u)) + '</span>' + (u.company ? ' · <span data-noi18n>' + esc(u.company) + '</span>' : '') + ' · ' + esc(r.at) + '</div>' + (r.note ? '<div class="mod-reason" data-noi18n>“' + esc(r.note) + '”</div>' : '') +
        '<div class="mod-actions"><button type="button" class="mod-btn dismiss" data-gpqr="no">Decline</button><button type="button" class="mod-btn gp-approve" data-gpqr="yes">Approve</button></div></div></div>'; }).join('') : '<div class="gp-ok">✓ No pending requests</div>';
    var b = document.querySelector('#managePanel .dx-rq-badge'); if (b) { b.textContent = list.length; b.style.display = list.length ? '' : 'none'; }
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#tab-requests [data-gpqr]'); if (!b || !CUR || CUR.g.live) return;
    e.preventDefault(); e.stopPropagation();
    var row = b.closest('[data-uid]'), uid = +row.dataset.uid, yes = b.dataset.gpqr === 'yes', g = CUR.g, s = st(), u = person(uid);
    (s.reqs[g.key] = s.reqs[g.key] || {})[uid] = yes ? 'approved' : 'declined';
    if (yes) { var base = BY_KEY[g.key]; if (base && !base.mem.some(function (m) { return m[0] === uid; })) { base.mem.push([uid, 'member', 'Joined just now']); } }
    save(); paintRequests(g); if (yes) { g.count++; var mc = g.card.querySelector('.member-count'); if (mc) mc.textContent = fmtN(g.count) + ' members'; paintHeader(g); }
    D.toast(yes ? u.name + ' is now a member' : 'Request declined — ' + u.name + ' was told politely');
  }, true);
  document.addEventListener('click', function (e) {   /* the Requests tab: the approved switchTab knows three panels */
    var t = e.target.closest && e.target.closest('#managePanel .panel-tabs .gx-ptab'); if (!t) return;
    var rq = document.getElementById('tab-requests'), on = !!t.dataset.gpqTab; if (!rq) return;
    if (on) { e.preventDefault(); e.stopImmediatePropagation(); document.querySelectorAll('#managePanel .panel-tabs .gx-ptab').forEach(function (x) { x.classList.toggle('active', x === t); });
      ['members', 'reports', 'settings'].forEach(function (k) { var p = document.getElementById('tab-' + k); if (p) p.style.display = 'none'; }); rq.style.display = 'block';
      if (CUR && CUR.g.live) hook('groupManage', { group: pub(CUR.g), op: 'requests' }); }
    else rq.style.display = 'none';
  }, true);
  function sel(id, opts, cur) { return '<select class="field-input" id="' + id + '">' + opts.map(function (o) { return '<option value="' + o[0] + '"' + (String(o[0]) === String(cur) ? ' selected' : '') + '>' + esc(o[1]) + '</option>'; }).join('') + '</select>'; }
  function countryOpts() { return [['', 'Any country (regional)']].concat(Object.keys(CNAME).map(function (c) { return [c, CFLAG[c] + ' ' + CNAME[c]]; })); }
  function settingsFields(g) {
    var ts = document.getElementById('tab-settings'); if (!ts) return;
    var ds = ts.querySelector('.field-textarea:not(.dx-rules)'); if (!ds) return;
    if (!ts.querySelector('.dx-rules')) { var f = ds.closest('.field'); f.insertAdjacentHTML('afterend', '<div class="field"><label class="field-label">Group rules</label><textarea class="field-textarea dx-rules" maxlength="4000" placeholder="One rule per line — e.g. Documents first: every offer shows its GMP certificate"></textarea></div>'); }
    if (!ts.querySelector('#gpSetPriv')) {
      ts.querySelector('.dx-rules').closest('.field').insertAdjacentHTML('afterend',
        '<div class="field gp-set-row"><label class="field-label" for="gpSetPriv">Privacy</label>' + sel('gpSetPriv', [['public', '🌍 Public — anyone can find, read and join'], ['private', '🔒 Private — members are approved or invited']], 'public') + '</div>' +
        '<div class="field gp-set-row"><label class="field-label" for="gpSetPost">Who can post</label>' + sel('gpSetPost', [['members', '👥 All members'], ['admins', '📣 Admins only']], 'members') + '</div>' +
        '<div class="field gp-set-row"><label class="field-label" for="gpSetSec">Sector</label>' + sel('gpSetSec', Object.keys(SECTORS).map(function (k) { return [k, SECTORS[k]]; }), 'pharma') + '</div>' +
        '<div class="field gp-set-row"><label class="field-label" for="gpSetCountry">Country</label>' + sel('gpSetCountry', countryOpts(), '') + '</div>' +
        '<div class="gp-archived-note" hidden>📦 This group is archived. <button type="button" class="btn-manage" data-gps="restore">Restore group</button></div>');
    }
    if (ts.dataset.gpFor !== g.key) {
      ts.dataset.gpFor = g.key;
      var nm = ts.querySelector('.field-input:not(select)'); if (nm && !g.live) nm.value = g.title;
      if (!g.live) { ds.value = g.about || g.desc || ''; ts.querySelector('.dx-rules').value = (g.rules || []).map(function (r) { return r[1] ? r[0] + ': ' + r[1] : r[0]; }).join('\n'); }
      ts.querySelector('#gpSetPriv').value = g.priv ? 'private' : 'public'; ts.querySelector('#gpSetPost').value = g.postPolicy; ts.querySelector('#gpSetSec').value = g.sector || 'pharma'; ts.querySelector('#gpSetCountry').value = g.country[0] || '';
    }
    var an = ts.querySelector('.gp-archived-note'); if (an) an.hidden = !g.archived;
  }
  function readSettings() {
    var ts = document.getElementById('tab-settings'), v = function (s) { var e = ts.querySelector(s); return e ? e.value : ''; };
    var rules = v('.dx-rules').split(/\n+/).map(function (l) { return l.trim(); }).filter(Boolean).slice(0, 20).map(function (l) { var m = /^(.{1,80}?)\s*(?:—|:|–)\s+(.+)$/.exec(l); return m ? [m[1], m[2]] : [l, '']; });
    return { t: (ts.querySelector('.field-input:not(select)') || {}).value.trim(), d: v('.field-textarea:not(.dx-rules)').trim(), rules: rules, rulesText: v('.dx-rules').trim(),
      priv: v('#gpSetPriv') === 'private', post: v('#gpSetPost'), sector: v('#gpSetSec'), country: v('#gpSetCountry') ? [v('#gpSetCountry')] : [] };
  }
  /* settings Save (demo; the live adapter saves them in the database) */
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#tab-settings .btn-create'); if (!b || !CUR || CUR.g.live || isLive()) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var g = CUR.g, f = readSettings(); if (!f.t) { var nm = document.querySelector('#tab-settings .field-input'); if (nm) nm.classList.add('dbk-err'); D.toast('Group name is required'); return; }
    var key = g.key; g.card.dataset.gk = key; delete g.card.dataset.tagged;
    g.card.querySelector('.gcard-title').textContent = f.t; var cd = g.card.querySelector('.gcard-desc'); if (cd) cd.textContent = f.d;
    st().ov[key] = { t: f.t, d: f.d, rules: f.rules, priv: f.priv, post: f.post, sector: f.sector, country: f.country }; save();
    tagCard(g.card); refresh(); D.toast('Group settings saved');
  }, true);
  /* archive (confirm) and restore */
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('#groupDetail .choice-btn.archive, #groupDetail [data-gps="restore"]'); if (!a || !CUR) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var g = CUR.g, restore = a.dataset.gps === 'restore';
    var go = function () {
      if (g.live) { var r = hook('groupManage', { group: pub(g), op: restore ? 'restore' : 'archive' }); if (r && r.then) r.then(function () { D.toast(restore ? 'Group restored — members can post again' : 'Group archived — read only, hidden from discovery'); if (window.dxGroups) window.dxGroups.refresh(); }, function (er) { D.toast((er && er.message) || 'Could not save — try again'); }); return; }
      g.card.dataset.gk = g.key; if (restore) delete st().arch[g.key]; else st().arch[g.key] = 1; save(); delete g.card.dataset.tagged;
      if (restore) { g.card.style.opacity = ''; var pb = g.card.querySelector('.priority-badge'); if (pb && /ARCHIVED/.test(pb.textContent)) pb.remove(); } else archiveCard(g.card);
      tagCard(g.card); refresh(); applyFilter(); D.toast(restore ? 'Group restored — members can post again' : 'Group archived — read only, hidden from discovery');
    };
    if (restore) { go(); return; }
    D.modal({ title: 'Archive this group?', body: '<div>Nobody can post, comment or join. Members can still read the history, and you can restore it from Settings.</div>', primary: { label: 'Archive', onClick: go } });
  }, true);

  /* ── per-group notifications: on / off for me, kept (demo: this browser; live: group_members.muted) ── */
  function notifBtns() { return [].filter.call(document.querySelectorAll('#groupDetail .group-actionbar .btn-secondary'), function (b) { return /Notifications/.test(window.dxOrigText ? window.dxOrigText(b) : b.textContent); }); }
  function paintNotif(on) { notifBtns().forEach(function (b) { var v = on ? '🔔 Notifications' : '🔕 Notifications off'; if (b.textContent !== v) { b.textContent = v; } b.setAttribute('aria-pressed', on ? 'false' : 'true'); }); }
  function notifOn(g) { return g.live ? !g.muted : st().notif[g.key] !== false; }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('#groupDetail .group-actionbar .btn-secondary'); if (!b || notifBtns().indexOf(b) < 0 || !CUR) return;
    e.preventDefault(); e.stopImmediatePropagation();
    var g = CUR.g, on = !notifOn(g);
    if (g.live) { var r = hook('groupManage', { group: pub(g), op: 'mute', on: !on }); if (r && r.then) r.then(function () { g.muted = !on; paintNotif(on); D.toast(on ? 'You’ll be notified about new posts' : 'Notifications turned off for this group'); }, function (er) { D.toast((er && er.message) || 'Could not save — try again'); }); return; }
    st().notif[g.key] = on; save(); paintNotif(on); D.toast(on ? 'You’ll be notified about new posts' : 'Notifications turned off for this group');
  }, true);

  /* ── creating a group: topic (sector), country, rules and emoji; an empty or taken name is refused; the new group opens ── */
  function createFields() {
    var M = document.getElementById('createModal'); if (!M || M.querySelector('#gpCrSec')) return;
    var pv = M.querySelector('.privacy-options'), host = pv ? pv.closest('.field') : null; if (!host) return;
    host.style.marginBottom = '';
    host.insertAdjacentHTML('afterend',
      '<div class="field gp-set-row"><label class="field-label" for="gpCrSec">Topic / sector</label>' + sel('gpCrSec', Object.keys(SECTORS).map(function (k) { return [k, SECTORS[k]]; }), 'pharma') + '</div>' +
      '<div class="field gp-set-row"><label class="field-label" for="gpCrCountry">Country</label>' + sel('gpCrCountry', countryOpts(), 'EG') + '</div>' +
      '<div class="field gp-set-row"><label class="field-label" for="gpCrEmoji">Emoji</label>' + sel('gpCrEmoji', ['💬', '🤝', '🧪', '💊', '💄', '🏭', '📋', '🌍', '🛡️', '⚗️', '📦', '🎓'].map(function (x) { return [x, x]; }), '💬') + '</div>' +
      '<div class="field" style="margin-bottom:0"><label class="field-label" for="gpCrRules">Group rules (one per line)</label><textarea class="field-textarea" id="gpCrRules" maxlength="4000" placeholder="Be respectful: disagree with ideas, never with people"></textarea></div>');
  }
  function createForm() {
    var M = document.getElementById('createModal'), pos = function (s) { var all = [].slice.call(M.querySelectorAll(s)); return all.indexOf(M.querySelector(s + '.selected')); };
    return { name: ((M.querySelector('.field-input:not(select)') || {}).value || '').trim(), desc: ((M.querySelector('.field-textarea:not(#gpCrRules)') || {}).value || '').trim(),
      deal: pos('.type-opt') === 1, priv: pos('.privacy-opt') === 1, sector: (M.querySelector('#gpCrSec') || {}).value || 'pharma',
      country: (M.querySelector('#gpCrCountry') || {}).value ? [M.querySelector('#gpCrCountry').value] : [], emoji: (M.querySelector('#gpCrEmoji') || {}).value || '💬',
      rules: ((M.querySelector('#gpCrRules') || {}).value || '').trim() };
  }
  window.dxGroupsCreateForm = createForm;
  function nameTaken(n) { n = n.toLowerCase(); return cards().some(function (c) { return otxt(c.querySelector('.gcard-title')).toLowerCase() === n; }); }
  window.dxGroupsNameTaken = nameTaken;
  document.addEventListener('click', function (e) {   /* demo (the live adapter checks and saves it itself) */
    var b = e.target.closest && e.target.closest('#createModal .modal-footer .btn-create'); if (!b || isLive()) return;
    var f = createForm();
    if (f.name && nameTaken(f.name)) { e.preventDefault(); e.stopImmediatePropagation(); D.toast('A group with this name already exists — choose another name'); return; }
    if (!f.name) return;   /* the approved window says "Give your group a name" */
    setTimeout(function () {   /* after the approved window made the card: keep what was chosen, then open the new group */
      var rec = st().made.find(function (m) { return m.t === f.name; }); if (!rec) return;
      rec.sector = f.sector; rec.country = f.country; rec.emoji = f.emoji; rec.rules = f.rules; save();
      var c = cardByKey(rec.k); if (!c) return; delete c.dataset.tagged; tagCard(c);
      var cv = c.querySelector('.gcard-cover'); if (cv) cv.textContent = f.emoji;
      var R = document.getElementById('createModal'); if (R) { R.querySelectorAll('#gpCrRules').forEach(function (x) { x.value = ''; }); }
      syncMine(document.getElementById('gx')); open(c);
    }, 30);
  }, true);

  function pageExtras(root) { searchBar(root); demoCounts(); createFields(); applyFilter(); }

  window.dxGroups = {
    open: function (name, tab) { if (document.body.getAttribute('data-page') !== 'groups' && typeof window.goto === 'function') window.goto('groups'); var r = document.getElementById('gx'); if (r) { wire(); initPage(r); } return open(name, tab); },
    pick: function (card, tab) { if (card && card.nodeType === 1) { LAST_CARD = card; OPEN_ARGS = { tab: tab || 'disc' }; } },
    refresh: function (tab) { refresh(tab); },
    joinClick: joinClick, current: function () { return CUR ? { key: CUR.g.key, title: CUR.g.title, tab: CUR.tab, member: CUR.g.member, role: CUR.g.role, posts: (CUR.posts || []).length } : null; },
    seed: SEED, adopt: adopt
  };
})();

/* ===== AREA community: groups — Arabic for the new parts (the interface translates as it draws; what people wrote stays as written) ===== */
(function () {
  if (!window.dxI18nExtend) return;
  window.dxI18nExtend({
    'Search groups by name or topic…': 'ابحث عن جروب بالاسم أو الموضوع…', 'Be respectful: disagree with ideas, never with people': 'احترم الجميع: اختلف مع الأفكار لا مع الأشخاص',
    '🌍 By Country': '🌍 حسب الدولة', '🌍 Groups by country': '🌍 الجروبات حسب الدولة', 'Groups by country': 'الجروبات حسب الدولة', 'All countries': 'كل الدول', 'Any country (regional)': 'أي دولة (إقليمي)',
    'No groups found': 'لا توجد جروبات', 'Try other words — or start the group yourself.': 'جرّب كلمات أخرى — أو ابدأ الجروب بنفسك.', 'No groups': 'لا توجد جروبات', 'Be the first to start one.': 'كن أول من يبدأ واحداً.',
    '← All groups': '→ كل الجروبات', '✓ You’re all caught up — no more posts in this group': '✓ وصلت لآخر المنشورات — لا توجد منشورات أخرى في هذا الجروب',
    'Who can post': 'من يمكنه النشر', '👥 All members': '👥 كل الأعضاء', '📣 Admins only': '📣 المديرون فقط', 'Sector': 'القطاع', 'Countries': 'الدول', 'Status': 'الحالة',
    '📦 Archived': '📦 مؤرشف', 'Archived': 'مؤرشف', 'Active': 'نشط', '💊 Pharma': '💊 أدوية', '💄 Cosmetics': '💄 مستحضرات تجميل', '🩺 Medical devices': '🩺 أجهزة طبية', '🥗 Supplements': '🥗 مكملات غذائية', '🧭 Other': '🧭 أخرى',
    'Egypt': 'مصر', 'Saudi Arabia': 'السعودية', 'UAE': 'الإمارات', 'Kuwait': 'الكويت', 'Qatar': 'قطر', 'Bahrain': 'البحرين', 'Oman': 'عُمان', 'Jordan': 'الأردن', 'Lebanon': 'لبنان', 'Iraq': 'العراق',
    'Morocco': 'المغرب', 'Algeria': 'الجزائر', 'Tunisia': 'تونس', 'Libya': 'ليبيا', 'Sudan': 'السودان', 'India': 'الهند', 'China': 'الصين',
    '📨 Requests': '📨 الطلبات', 'Requests': 'الطلبات', 'asked to join': 'طلب الانضمام', '🔍 Search members': '🔍 ابحث في الأعضاء', 'Search members': 'ابحث في الأعضاء', 'You are the admin': 'أنت المدير',
    '🔒 The member list is visible to members only. The admins are shown under About.': '🔒 قائمة الأعضاء ظاهرة للأعضاء فقط. المديرون ظاهرون في صفحة "حول".',
    '🔔 Notifications': '🔔 الإشعارات', '🔕 Notifications off': '🔕 الإشعارات متوقفة', 'Notifications turned off for this group': 'تم إيقاف إشعارات هذا الجروب', 'You’ll be notified about new posts': 'سيصلك إشعار بالمنشورات الجديدة',
    '🌍 Public — anyone can find, read and join': '🌍 عام — يمكن لأي شخص إيجاده وقراءته والانضمام', '🔒 Private — members are approved or invited': '🔒 خاص — الأعضاء بالموافقة أو الدعوة',
    'Archive this group?': 'أرشفة هذا الجروب؟', 'Archive': 'أرشفة', 'Nobody can post, comment or join. Members can still read the history, and you can restore it from Settings.': 'لن يستطيع أحد النشر أو التعليق أو الانضمام. يظل الأعضاء قادرين على قراءة ما سبق، ويمكنك استعادته من الإعدادات.',
    'Group archived — read only, hidden from discovery': 'تمت أرشفة الجروب — للقراءة فقط ومخفي من البحث', 'Group archived — restore it anytime from settings': 'تمت أرشفة الجروب — يمكنك استعادته في أي وقت من الإعدادات',
    'Group restored — members can post again': 'تمت استعادة الجروب — يمكن للأعضاء النشر مجدداً', '↺ Restore group': '↺ استعادة الجروب', 'Restore': 'استعادة',
    'This group is archived — read only. Nobody can post, comment or join.': 'هذا الجروب مؤرشف — للقراءة فقط. لا يمكن لأحد النشر أو التعليق أو الانضمام.',
    'Only the admins post in this group.': 'المديرون فقط ينشرون في هذا الجروب.', 'Group settings saved': 'تم حفظ إعدادات الجروب', 'Group name is required': 'اسم الجروب مطلوب', 'Could not save — try again': 'تعذّر الحفظ — حاول مرة أخرى',
    'A group with this name already exists — choose another name': 'اسم الجروب مستخدم بالفعل — اختر اسماً آخر', 'Topic': 'الموضوع', 'Country': 'الدولة', 'Emoji': 'الرمز', 'Group rules (one per line)': 'قواعد الجروب (سطر لكل قاعدة)',
    'Delete this comment?': 'حذف هذا التعليق؟', 'It is removed for everyone in the group.': 'سيُحذف لكل أعضاء الجروب.', 'Comment deleted': 'تم حذف التعليق',
    'Reported — the group admins will check it': 'تم الإبلاغ — سيراجعه مديرو الجروب', 'You already reported this post — the admins will check it': 'لقد أبلغت عن هذا المنشور بالفعل — سيراجعه المديرون',
    'Close this listing?': 'إغلاق هذا الإعلان؟', 'It leaves the Listings tab for everyone. Deals already started stay in the Deals center.': 'سيختفي من تبويب الإعلانات للجميع. الصفقات التي بدأت تبقى في مركز الصفقات.',
    'Yes, close it': 'نعم، أغلقه', 'Listing closed': 'تم إغلاق الإعلان', 'Could not close — try again': 'تعذّر الإغلاق — حاول مرة أخرى', 'Your request': 'طلبك', 'Your offer': 'عرضك', 'Quotes': 'العروض', 'Enquiries': 'الاستفسارات',
    'Request a quote': 'اطلب عرض سعر', 'Request quote →': 'اطلب عرض سعر ←', 'Send a quote': 'أرسل عرض سعر', 'Quote →': 'عرض سعر ←', 'Send quote': 'أرسل العرض', 'Send request': 'أرسل الطلب', 'For': 'إلى',
    'Price *': 'السعر *', 'Lead time *': 'مدة التوريد *', 'Message': 'رسالة', 'Your request *': 'طلبك *', 'Quantity, delivery terms, documents you need': 'الكمية وشروط التسليم والمستندات المطلوبة',
    'Certificates, validity, payment terms': 'الشهادات والصلاحية وشروط الدفع', 'e.g. 3 weeks': 'مثال: 3 أسابيع', 'e.g. $5.20/kg CIF Alexandria': 'مثال: 5.20$/كجم CIF الإسكندرية',
    'It starts a quote request in your Deals center, sent on behalf of your company page.': 'يبدأ طلب عرض سعر في مركز الصفقات، باسم صفحة شركتك.',
    'Quote request sent — follow it in your Deals center': 'تم إرسال طلب عرض السعر — تابعه في مركز الصفقات', 'This listing has no company page — message its author instead': 'هذا الإعلان بلا صفحة شركة — راسل صاحبه بدلاً من ذلك',
    '📦 This group is archived — you can read its history; nobody can post, comment or join.': '📦 هذا الجروب مؤرشف — يمكنك قراءة ما سبق؛ لا يمكن لأحد النشر أو التعليق أو الانضمام.',
    '📣 Only the admins post in this group — you can comment and react.': '📣 المديرون فقط ينشرون في هذا الجروب — يمكنك التعليق والتفاعل.', 'Invitation from': 'دعوة من', 'a group admin': 'أحد مديري الجروب',
    '✕ Decline': '✕ رفض', '✕ Decline invitation': '✕ رفض الدعوة', 'Invitation declined': 'تم رفض الدعوة',
    'Join to quote': 'انضم لتقديم عرض', 'Join to enquire': 'انضم للاستفسار', 'Closed': 'مغلق', 'Open': 'مفتوح', 'Joined just now': 'انضم الآن', 'New group': 'جروب جديد'
  }, [
    [/^📎 (.+) — sample file: attachments open from the live app$/, function (m) { return '📎 ' + m[1] + ' — ملف تجريبي: المرفقات تُفتح من التطبيق الفعلي'; }],
    [/^Quote sent to (.+) — follow it in your Deals center$/, function (m) { return 'تم إرسال العرض إلى ' + m[1] + ' — تابعه في مركز الصفقات'; }],
    [/^Request declined — (.+) was told politely$/, function (m) { return 'تم رفض الطلب — تم إبلاغ ' + m[1] + ' بلطف'; }],
    [/^(.+) is now a member$/, function (m) { return m[1] + ' أصبح عضواً الآن'; }],
    [/^(.+) (?:is|are) already invited$/, function (m) { return m[1] + ' مدعو بالفعل'; }], [/^(.+) (?:is|are) already a member$/, function (m) { return m[1] + ' عضو بالفعل'; }],
    [/^Already invited: (.+?)(?: · Already in the group: (.+))?$/, function (m) { return 'مدعو بالفعل: ' + m[1] + (m[2] ? ' · عضو بالفعل: ' + m[2] : ''); }],
    [/^Already in the group: (.+)$/, function (m) { return 'عضو بالفعل: ' + m[1]; }],
    [/^Quotes \((\d+)\)$/, function (m) { return 'العروض (' + m[1] + ')'; }], [/^Enquiries \((\d+)\)$/, function (m) { return 'الاستفسارات (' + m[1] + ')'; }], [/^📨 Requests \((\d+)\)$/, function (m) { return '📨 الطلبات (' + m[1] + ')'; }],
    [/^(\d+) new posts in "(.+)"$/, function (m) { return m[1] + ' منشورات جديدة في "' + m[2] + '"'; }], [/^posted in "(.+)"$/, function (m) { return 'نشر في "' + m[1] + '"'; }], [/^removed you from the group "(.+)"$/, function (m) { return 'أزالك من الجروب "' + m[1] + '"'; }],
    [/^sent an offer for your request "(.+)" in the deal room "(.+)"$/, function (m) { return 'أرسل عرضاً لطلبك "' + m[1] + '" في غرفة الصفقات "' + m[2] + '"'; }],
    [/^sent a quote request for your listing "(.+)" in the deal room "(.+)"$/, function (m) { return 'أرسل طلب عرض سعر لإعلانك "' + m[1] + '" في غرفة الصفقات "' + m[2] + '"'; }],
    [/^removed your post in "(.+)"$/, function (m) { return 'أزال منشورك في "' + m[1] + '"'; }],
    [/^could not accept your request to join "(.+)" this time$/, function (m) { return 'لم يتمكن من قبول طلبك للانضمام إلى "' + m[1] + '" هذه المرة'; }]
  ]);
})();
