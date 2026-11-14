// The company's own papers the program writes (Part 2, step 2.6): each from the dossier's data — the facts read from its documents,
// each with its page, and what the person entered about the company — as a Word draft that is reviewed, printed on the company's
// paper, signed and stamped. Nothing is guessed: what the program does not know is a marked gap. A sum (a salt's equivalent) is
// worked out here and printed with its formula. The texts follow the old program's generators and EDA's Annex I.
import { evaluate } from './expr.js';
import { formOf, convert, FORMULAS } from '../prep/chem.js';
import ANNEX1 from './templates/annex1.json' with { type: 'json' };

// The place each generator writes for (Egypt) and its name in the interface.
export const GENERATORS = {
  'EG-EDA/M1-01': { name: 'annex1', ar: 'نموذج الطلب (Annex I) والتعهد' },
  'EG-EDA/M1-10': { name: 'translation', ar: 'إقرار ترجمة النشرة' },
  'EG-EDA/M1-31': { name: 'composition', ar: 'شهادة التركيب' },
  'EG-EDA/M1-32': { name: 'salt', ar: 'حساب الملح المكافئ' },
  'EG-EDA/M1-40': { name: 'cep_commitment', ar: 'تعهد الـ CEP' },
  'EG-EDA/M1-43': { name: 'cover', ar: 'خطاب التغطية' },
  'EG-EDA/M1-44': { name: 'tracking', ar: 'جدول المتابعة' },
  'EG-EDA/P-16': { name: 'stability_commitment', ar: 'تعهد الثبات' },
};

// The fields the person gives about the company (the program cannot read them from the documents).
export const COMPANY_FIELDS = [
  ['company', 'اسم الشركة القانوني (مقدم الطلب)'], ['signatory', 'اسم الموقّع'], ['signatory_title', 'صفة الموقّع'],
  ['address', 'عنوان الشركة'], ['contact_person', 'الشخص المسؤول عن الملف'], ['telephone', 'التليفون'], ['email', 'البريد الإلكتروني'],
  ['distributors', 'شركات التوزيع'], ['portal_username', 'اسم المستخدم على بوابة الهيئة'],
];

// The dossier's data as the generators take it: {key: {value, from?}} — the person's own values first, then the facts read from
// the documents (the licence before the others), each with where it was read.
export function dataOf(d) {
  const out = {};
  const put = (key, value, from) => { if (value && !out[key]) out[key] = { value: String(value), ...(from ? { from } : {}) }; };
  for (const [k, v] of Object.entries(d.company || {})) put(k, v, 'you');
  for (const [k, v] of Object.entries(d.product || {})) put(k, v?.value ?? v, v?.from || 'you');
  const docs = d.docs.filter(x => !x.dup && !x.split && x.facts?.length);
  const order = x => (x.type === 'registration_licence' ? 0 : x.party === 'eda' ? 1 : 2);
  for (const doc of [...docs].sort((a, b) => order(a) - order(b))) {
    for (const f of doc.facts) {
      const from = { doc: doc.id, name: doc.name, page: f.page, quote: f.quote };
      if (f.field === 'product_name') put('trade_name', f.value, from);
      else if (['dosage_form', 'manufacturer', 'license_holder', 'registration_number', 'applicant'].includes(f.field)) put(f.field, f.value, from);
    }
  }
  const lic = docs.find(x => x.type === 'registration_licence') || docs.find(x => x.facts.some(f => f.field === 'composition'));
  out.composition = { value: (lic?.facts || []).filter(f => f.field === 'composition').map(f => ({ name: f.value.replace(/\s+[\d.,]+\s*\S+$/, ''), substance: f.substance, grams: f.grams, value: f.value })),
                      from: lic ? { doc: lic.id, name: lic.name } : null };
  if (!out.applicant && out.company) out.applicant = out.company;
  return out;
}

const v = (data, key, label) => (data[key]?.value ? { value: data[key].value, field: key } : { gap: label });
const p = (parts, o = {}) => ({ t: 'p', parts, ...o });
const TO_EDA = 'To: Egyptian Drug Authority — General Administration for Human Pharmaceuticals Registration';
const sign = data => [
  { t: 'gap' },
  p(['Name / الاسم: ', v(data, 'signatory', 'اسم الموقّع')]),
  p(['Title / الصفة: ', v(data, 'signatory_title', 'صفة الموقّع')]),
  p('Signature / التوقيع: ______________________      Company stamp / ختم الشركة:'),
  p('Date / التاريخ: ____/____/________'),
];

function annex1(data, d) {
  const t = ANNEX1;
  const env = { ...d.profile, activity: d.profile?.activity || 'new', origin: d.profile?.origin || 'local', decree_case: d.profile?.decree_case || 'other',
                pending_studies_api_source: !!data.pending_studies_api_source?.value };
  const known = { trade_name: 'trade_name', registration_number: 'registration_number', dosage_form: 'dosage_form', applicant: 'applicant',
                  mah: 'license_holder', manufacturer: 'manufacturer' };
  const blocks = [p('Annex I — Application form', { bold: true, size: 13, align: 'center' }), ...t.salutation_ar.map(l => p(l, { rtl: true }))];
  for (const sec of t.sections) {
    if (sec.title) blocks.push(p(sec.title, { bold: true }));
    blocks.push({ t: 'table', rtl: false, head: ['Field', 'Value'], rows: sec.fields.map(f => [f.label, known[f.key] ? v(data, known[f.key], f.label) : f.required ? { gap: f.label } : 'N/A']) });
  }
  const comp = data.composition?.value || [];
  const apis = comp.length ? comp : [null];
  apis.forEach((a, i) => {
    blocks.push(p(`API ${i + 1}`, { bold: true }));
    blocks.push({ t: 'table', rtl: false, head: ['Field', 'Value'], rows: t.api_box.map(f => [f.label,
      f.key === 'name_form_specs' && a ? { value: a.name, field: 'composition' } : f.key === 'option' ? f.choices.map(c => `☐ ${c}`).join('   ') : f.required ? { gap: f.label } : 'N/A']) });
  });
  blocks.push({ t: 'table', rtl: false, head: ['Contact', ''], rows: t.contact.map(f => [f.label, v(data, f.key, f.label)]) });
  blocks.push({ t: 'gap' });
  const fill = text => {                                      // «{signatory}» in the Arabic clauses → the value, or a gap
    const parts = [];
    let at = 0;
    for (const m of text.matchAll(/\{(\w+)\}/g)) {
      parts.push(text.slice(at, m.index));
      const key = m[1];
      if (key === 'variations_statement') parts.push(t.variations_statement_ar.none);
      else parts.push(v(data, key, { signatory: 'اسم الموقّع', signatory_title: 'صفته', company: 'اسم الشركة', distributors: 'شركات التوزيع',
                                     rereg_studies_api_source: 'مصدر المادة الخام في دراسات إعادة التسجيل', pending_studies_api_source: 'مصدر المادة الخام' }[key] || key));
      at = m.index + m[0].length;
    }
    parts.push(text.slice(at));
    return parts;
  };
  blocks.push(p(fill(t.undertaking_intro_ar), { rtl: true, bold: true }));
  for (const cl of t.undertaking_ar) {
    if (cl.when) { try { if (!evaluate(cl.when, env)) continue; } catch { continue; } }
    blocks.push(p(fill(cl.text), { rtl: true, bullet: true }));
  }
  blocks.push({ t: 'gap' }, ...t.signature_ar.map(l => p(l, { rtl: true })));
  return { title: 'Annex I — Application form', rtl: true, draft: true, blocks, note: t.provenance };
}

function composition(data) {
  const comp = data.composition?.value || [];
  const rows = comp.length ? comp.map(c => [{ value: c.name, field: 'composition' }, { gap: 'الوظيفة' }, { value: c.value.match(/[\d.,]+\s*\S+$/)?.[0] || '', field: 'composition' }, { gap: 'المرجع (BP/USP…)' }])
                           : [[{ gap: 'المادة' }, { gap: 'الوظيفة' }, { gap: 'الكمية في الوحدة' }, { gap: 'المرجع' }]];
  return { title: 'Composition certificate', rtl: false, draft: true, blocks: [
    p(TO_EDA), p('Composition certificate', { bold: true, size: 13, align: 'center' }),
    p(['Trade name: ', v(data, 'trade_name', 'Trade name')]), p(['Dosage form: ', v(data, 'dosage_form', 'Dosage form')]),
    p(['Each unit contains (as in ', data.composition?.from ? { value: data.composition.from.name, field: 'composition' } : { gap: 'the registration licence' }, '):']),
    { t: 'table', head: ['Component', 'Function', 'Quantity per unit', 'Reference standard'], rows: [...rows, [{ gap: 'Inactive ingredients (each line)' }, '', '', '']] },
    p('Function and reference standard of each component, and every inactive ingredient, are completed by the company.', { size: 9 }),
    ...sign(data)] };
}

function salt(data) {
  const comp = data.composition?.value || [];
  const rows = [];
  for (const c of comp) {
    const f = formOf(c.substance || c.name);
    if (f.form === null || !FORMULAS[f.base]) continue;
    const to = f.water ? `${f.base} anhydrous` : f.base;
    const r = convert(c.substance, c.grams, to);
    if (!r) continue;
    rows.push([{ value: c.name, field: 'composition' }, `${f.base} (${FORMULAS[f.base]})`, `${r.mFrom.toFixed(2)} / ${r.mTo.toFixed(2)}`,
               `${c.grams} g × ${r.mTo.toFixed(2)} ÷ ${r.mFrom.toFixed(2)} = ${r.amount.toFixed(3)} g ${to}`]);
  }
  if (!rows.length) rows.push([{ gap: 'Salt / hydrate as used' }, { gap: 'Base' }, { gap: 'MW salt / base' }, { gap: 'Calculation' }]);
  return { title: 'Equivalence (salt) calculation', rtl: false, draft: true, blocks: [
    p('Equivalence (salt / hydrate) calculation', { bold: true, size: 13, align: 'center' }), p(['Product: ', v(data, 'trade_name', 'Trade name')]),
    { t: 'table', head: ['Substance as used', 'Base (formula)', 'Molecular weight used / base', 'Calculation'], rows },
    p('Molecular weights from the IUPAC standard atomic weights (2021, abridged). The company checks each line against the pharmacopoeia it follows.', { size: 9 }),
    ...sign(data)] };
}

function translation(data) {
  return { title: 'Declaration — leaflet translation', rtl: true, draft: true, blocks: [
    p(TO_EDA), p('Declaration — leaflet translation', { bold: true, size: 13, align: 'center' }),
    p(['We, ', v(data, 'company', 'Company'), ', declare that the ', { gap: 'source language' }, ' leaflet of ', v(data, 'trade_name', 'Trade name'),
       ' (version ', { gap: 'leaflet version' }, ') has been translated by an authorised medical translator (', { gap: 'translator' }, '), and that the translation is faithful and complete.']),
    p(['نقر نحن ', v(data, 'company', 'اسم الشركة'), ' بأن نشرة المستحضر ', v(data, 'trade_name', 'اسم المستحضر'), ' (الإصدار ', { gap: 'رقم الإصدار' },
       ') تمت ترجمتها بواسطة مترجم طبي معتمد (', { gap: 'اسم المترجم' }, ') وأن الترجمة مطابقة وكاملة.'], { rtl: true }),
    ...sign(data)] };
}

function cepCommitment(data) {
  return { title: 'Commitment — Certificate of Suitability', rtl: false, draft: true, blocks: [
    p(TO_EDA), p(['Subject: Commitment regarding Certificate of Suitability ', { gap: 'CEP number' }, ' — ', { gap: 'API' }], { bold: true }),
    p(['We, ', v(data, 'company', 'Company'), ', applicant for ', v(data, 'trade_name', 'Trade name'), ', hereby commit to inform the Egyptian Drug Authority without delay of any revision, renewal, suspension or withdrawal of Certificate of Suitability ',
       { gap: 'CEP number' }, ' held by ', { gap: 'CEP holder' }, ' for ', { gap: 'API' }, '.']),
    p('We acknowledge that if the CEP is suspended or withdrawn, full data for section 3.2.S of the CTD will be required.'),
    ...sign(data)] };
}

function cover(data, d) {
  const kind = d.profile?.activity === 're_registration' ? 'Re-registration' : 'New registration';
  return { title: 'Cover letter', rtl: false, draft: true, blocks: [
    p('Date: ____/____/________'), p(TO_EDA),
    p(['Subject: ', v(data, 'trade_name', 'Trade name'), ` — ${kind} dossier (CTD, One Submission)`], { bold: true }),
    { t: 'table', head: ['Item', 'Value'], rows: [['Trade name', v(data, 'trade_name', 'Trade name')], ['Dosage form', v(data, 'dosage_form', 'Dosage form')],
      ['Registration request / registration number', v(data, 'registration_number', 'Registration number')], ['Applicant', v(data, 'company', 'Applicant')],
      ['Licence holder', v(data, 'license_holder', 'Licence holder')], ['Manufacturer', v(data, 'manufacturer', 'Manufacturer')], ['Application', kind]] },
    p('We submit the dossier of the above product in the CTD format of NP.CAPP.065, Modules 1 to 5 as applicable to the product.'),
    p('We confirm that the submission is true, complete and correct.'),
    ...sign(data)] };
}

function tracking(data) {
  return { title: 'Tracking table', rtl: false, draft: true, landscape: true, blocks: [
    p(['Tracking table — ', v(data, 'trade_name', 'Trade name')], { bold: true, size: 13, align: 'center' }),
    { t: 'table', head: ['Sequence', 'Related sequence', 'Description', 'Submission type', 'Submission unit', 'Date submitted', 'Tracking number', 'Status'],
      rows: [['0000', '', { gap: 'Description' }, { gap: 'Type' }, { gap: 'Unit' }, '', { gap: 'Tracking number' }, '']] }] };
}

function stabilityCommitment(data) {
  return { title: 'Stability commitment', rtl: false, draft: true, blocks: [
    p(TO_EDA), p(['Subject: Stability commitment — ', v(data, 'trade_name', 'Trade name')], { bold: true }),
    p(['We, ', v(data, 'company', 'Company'), ', commit for ', v(data, 'trade_name', 'Trade name'), ' (', { gap: 'strengths' }, '; ', { gap: 'container-closure systems' }, ') to:']),
    p(['continue the long-term stability studies on the primary batches until the end of the proposed shelf life of ', { gap: 'shelf life' }, ' at ', { gap: 'long-term condition' }, ';'], { bullet: true }),
    p('place at least three production batches of each strength in each container-closure system on long-term and accelerated stability studies (commitment batches), using the approved protocol;', { bullet: true }),
    p('place at least one production batch per year of each strength in each container-closure system in the ongoing stability programme;', { bullet: true }),
    p('report any confirmed out-of-specification result or significant change to the Egyptian Drug Authority without delay.', { bullet: true }),
    ...sign(data)] };
}

const MAKERS = { annex1, composition, salt, translation, cep_commitment: cepCommitment, cover, tracking, stability_commitment: stabilityCommitment };
// The draft for one place: {model, file name, title} — or null when the program has no generator for it.
export function draftFor(placeId, d) {
  const g = GENERATORS[placeId];
  if (!g) return null;
  const data = dataOf(d);
  return { generator: g.name, ar: g.ar, model: MAKERS[g.name](data, d) };
}
