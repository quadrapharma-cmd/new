// The board of a dossier (Part 2, step 2.1): the places of the country's dossier, each with what the product's case makes it —
// required (R), optional (O), not required (NR) or not applying (NA) — and the rule card of the paper that goes there. Everything
// comes from the library (dist/knowledge.json): the requirement sets, their conditions, the document types with their validity,
// the templates and the words that recognise each paper. Nothing here is written for one product.
import { evaluate } from './expr.js';
import { TYPES } from '../prep/doctype.js';

// The countries a new dossier can be for: Egypt with its full rules, the others with their own Module 1 and ICH's Modules 2–5.
export const COUNTRIES = [
  { id: 'EG', ar: 'مصر', en: 'Egypt', authority: 'EG-EDA', sets: ['eg-eda-ctd'], full: true, questions: ['activity', 'dossier_kind', 'origin', 'licence', 'leaflet'],
    note: 'قواعد هيئة الدواء المصرية كاملة (NP.CAPP.065 الإصدار 5).' },
  { id: 'GCC', ar: 'الخليج', en: 'GCC', authority: 'GCC', sets: ['gcc-m1', 'ich-m4-ctd'], full: true, questions: ['gcc_agency', 'activity', 'dossier_kind', 'origin', 'biological_origin_materials', 'novel_excipient'],
    note: 'موديول 1 الخليجي (مواصفة GCC Module 1 الإصدار 1.5، ومتطلبات هيئة الغذاء والدواء السعودية)، والموديولات 2–5 من ICH M4؛ وشكل الملفات من المواصفة الخليجية ومواصفة ICH للـ eCTD.' },
  { id: 'EU', ar: 'أوروبا', en: 'EU', authority: 'EU', sets: ['eu-m1', 'ich-m4-ctd'], full: true, questions: ['eu_procedure', 'eu_legal_basis', 'activity', 'dossier_kind', 'origin', 'biological_origin_materials', 'novel_excipient'],
    note: 'موديول 1 الأوروبي (مواصفة EU M1 الإصدار 3.1.1)، والموديولات 2–5 من ICH M4؛ وشكل الملفات من الإرشاد الأوروبي الموحّد (HTG 6.0.1) ومعايير التحقق 8.2.' },
  { id: 'US', ar: 'أمريكا', en: 'USA', authority: 'US-FDA', sets: ['us-fda-m1', 'ich-m4-ctd'], full: true, questions: ['us_application', 'dossier_kind', 'origin', 'biological_origin_materials', 'novel_excipient'],
    note: 'موديول 1 الأمريكي (FDA)، والموديولات 2–5 من ICH M4؛ وشكل الملفات من معايير التحقق بتاعة FDA ومواصفة ICH للـ eCTD.' },
  { id: 'OTHER', ar: 'دولة تانية', en: 'Other', authority: 'OTHER', sets: ['intl-m1', 'ich-m4-ctd'], full: true, questions: ['activity', 'dossier_kind', 'origin', 'biological_origin_materials', 'novel_excipient'],
    note: 'موديول 1 العام اللي أغلب الهيئات بتطلبه، والموديولات 2–5 من ICH M4؛ وشكل الملفات من مواصفة ICH للـ eCTD. راجع موديول 1 بتاع الدولة نفسها قبل التقديم.' },
];
export const SET_COUNTRY = { 'eg-eda-ctd': 'EG', 'gcc-m1': 'GCC', 'eu-m1': 'EU', 'us-fda-m1': 'US', 'intl-m1': 'OTHER' };
export const country = id => COUNTRIES.find(c => c.id === id) || COUNTRIES[0];

// The product's case, as the wizard asks it (the names the library's conditions use).
export const PROFILE = {
  dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', route: 'one_submission', leaflet: 'english',
  eu_procedure: 'dcp', eu_legal_basis: 'generic', gcc_agency: 'SA', us_application: 'anda',
  pharmacopoeial: false, dosage_specifics: [], apis: [], store_separate_from_factory: false, biological_origin_materials: false,
  novel_excipient: false, local_action: false, aqueous_solution: false, admin_route: 'oral', bcs_waiver: false,
};
export const QUESTIONS = {
  dossier_kind: { ar: 'نوع المستحضر', options: { generic: 'مثيل', innovator: 'مبتكر' } },
  origin: { ar: 'مصدره', options: { local: 'محلي', imported: 'مستورد' } },
  activity: { ar: 'نوع الطلب', options: { new: 'تسجيل جديد', re_registration: 'إعادة تسجيل' } },
  licence: { ar: 'الترخيص', options: { own: 'في مصنع الشركة', toll: 'تصنيع لدى الغير (toll)', f_toll: 'تصنيع لدى الغير لشركة أجنبية (f-toll)',
                                       under_licence: 'تحت ترخيص (under licence)', imported: 'مستورد تام الصنع', imported_bulk: 'مستورد bulk' } },
  leaflet: { ar: 'النشرة', options: { english: 'إنجليزي', non_english: 'بلغة تانية غير الإنجليزي', pil_only: 'نشرة المريض بس' } },
  eu_procedure: { ar: 'الإجراء', options: { cp: 'مركزي (EMA)', dcp: 'لامركزي (DCP)', mrp: 'اعتراف متبادل (MRP)', np: 'وطني (دولة واحدة)' } },
  eu_legal_basis: { ar: 'الأساس القانوني', options: { full: 'ملف كامل — Art. 8(3)', generic: 'مثيل — Art. 10(1)', hybrid: 'هجين — Art. 10(3)', biosimilar: 'بيولوجي مماثل — Art. 10(4)',
                                                    weu: 'استخدام راسخ — Art. 10a', fixed: 'تركيبة ثابتة — Art. 10b', informed: 'موافقة مستنيرة — Art. 10c' } },
  gcc_agency: { ar: 'الهيئة', options: { SA: 'السعودية (SFDA)', AE: 'الإمارات', KW: 'الكويت', BH: 'البحرين', OM: 'عُمان', QA: 'قطر', YE: 'اليمن', GCC: 'التسجيل المركزي الخليجي' } },
  us_application: { ar: 'نوع الطلب', options: { anda: 'ANDA (مثيل)', nda: 'NDA — 505(b)(1)', nda_b2: 'NDA — 505(b)(2)', bla: 'BLA (بيولوجي)', ind: 'IND (دراسة إكلينيكية)' } },
  biological_origin_materials: { ar: 'فيه مواد من أصل حيواني أو بشري؟', bool: true, options: { no: 'لأ', yes: 'أيوه' } },
  novel_excipient: { ar: 'فيه مادة غير فعالة جديدة (novel excipient)؟', bool: true, options: { no: 'لأ', yes: 'أيوه' } },
};
// A question's answer as the conditions read it (a yes/no question is a true/false), and back as the select shows it.
export const answerOf = (key, value) => (QUESTIONS[key]?.bool ? value === 'yes' || value === true : value);
export const shownOf = (key, value) => (QUESTIONS[key]?.bool ? (value === true || value === 'yes' ? 'yes' : 'no') : value);

// The column of NP.CAPP.065's table the product falls in (a local innovator is not in the table: the imported innovator's column, said).
export const columnOf = p => (p.dossier_kind === 'innovator' ? 'I' : p.origin === 'imported' ? 'G_IMP' : 'G_LOC');

function biowaiver(p) {
  if (p.dossier_kind === 'innovator') return '';
  if (p.aqueous_solution && ['parenteral', 'oral', 'ophthalmic', 'otic', 'nasal', 'topical', 'inhalation'].includes(p.admin_route)) return 'aqueous_solution';
  if (p.bcs_waiver && p.admin_route === 'oral') return 'bcs';
  return '';
}

export function envOf(profile = {}) {
  const p = { ...PROFILE, ...profile };
  const bw = biowaiver(p);
  return { ...p, column: columnOf(p), api_options: [...new Set((p.apis || []).map(a => a.option || 'FULL'))].sort(), api_count: (p.apis || []).length,
           biowaiver: bw, local_equivalence: !!(p.local_action && !bw && p.dossier_kind !== 'innovator') };
}

// One requirement's level for this product: NA when its condition does not hold, else its cell of the table (a cell can have cases).
export function levelOf(req, env) {
  if (req.applies && req.applies !== 'true' && !safe(req.applies, env)) return { level: 'NA', why: req.applies };
  const cell = req.required?.[env.column] ?? req.required?.G_LOC ?? 'R';
  if (typeof cell === 'string') return { level: cell, why: null };
  for (const c of cell.cases || []) if (!c.when || safe(c.when, env)) return { level: c.level, why: c.when || null };
  return { level: 'O', why: null };
}
function safe(text, env) { try { return evaluate(text, env); } catch { return true; } }   // a condition the reader cannot read never hides a place

const MODULES = { 1: 'الموديول 1: المستندات الإدارية', 2: 'الموديول 2: الملخصات', 3: 'الموديول 3: الجودة', 4: 'الموديول 4: الدراسات غير السريرية', 5: 'الموديول 5: الدراسات السريرية' };

// The board: the places of the country's sets, each with its level and its rule card's sources, grouped by module.
export function boardOf(knowledge, { countryId = 'EG', profile = {} } = {}) {
  const c = country(countryId), env = envOf(profile);
  const places = [];
  for (const set of c.sets) {
    for (const r of knowledge.requirements.filter(x => x.set === set)) {
      if (set === 'ich-m4-ctd' && r.module === 1) continue;
      const { level, why } = levelOf(r, env);
      places.push({ id: r.id, set, module: r.module, ctd: String(r.ctd || ''), title: r.title, group: r.group || '', level, why,
                    doc_class: r.doc_class || '', produced_by: r.produced_by || '', ectd: r.ectd || [], cite: r.cite || [] });
    }
  }
  const modules = [1, 2, 3, 4, 5].map(n => ({ n, title: MODULES[n], places: places.filter(p => p.module === n) })).filter(m => m.places.length);
  return { country: c, env, column: env.column, places, modules };
}

// ---------------------------------------------------------------------------------------------------------------- rule cards
// Who may change a paper, from its class in the library.
export const PARTY = {
  third_party_certificate: { party: 'third', ar: 'جهة تانية (مصنع، مورد، هيئة في بلد تاني): محتواه ما يتغيرش أبداً. التصليح التقني بس، وكل صفحة تفضل زي الأصل.' },
  eda_document: { party: 'eda', ar: 'هيئة الدواء: محتواه ما يتغيرش أبداً. التصليح التقني بس، وكل صفحة تفضل زي الأصل.' },
  company_letter: { party: 'company', ar: 'الشركة: البرنامج يقدر يعمله ويعدّله، وبعدين يتطبع على ورق الشركة ويتمضي ويتختم.' },
  company_technical: { party: 'company', ar: 'الشركة (مستند فني): الشركة بتكتبه، والبرنامج يراجعه ويصلّح شكله.' },
  generated: { party: 'company', ar: 'الشركة: البرنامج يعمله من معلومات الملف، وانت تراجعه.' },
  executed_record: { party: 'company', ar: 'سجل اتنفّذ (تشغيلة حقيقية): ما يتغيرش، بيتحط زي ما هو.' },
};
export const partyOf = docClass => PARTY[docClass]?.party || 'company';

// Egypt: the document type each place holds (its validity, who issues it), where the library's types name one.
// Where a dossier holds its pack's artwork — the coloured outer and inner packs, the mock-ups, the carton and container labels — in
// each country's Module 1: the design program (DesignCraft) makes or changes it, and gives the PDF that goes in.
export const DESIGN_PLACES = new Set(['EG-EDA/M1-11', 'EU/EU-1.3.2', 'GCC/GCC-1.3.4', 'US-FDA/US-1.14.1.1', 'US-FDA/US-1.14.2.1', 'OTHER/X-1.3.4']);

export const DOCTYPE_OF = {
  'EG-EDA/M1-04': 'registration_licence', 'EG-EDA/M1-05': 'pricing_certificate', 'EG-EDA/M1-06': 'eda_letter', 'EG-EDA/M1-07': 'variation_approval',
  'EG-EDA/M1-09': 'leaflet', 'EG-EDA/M1-11': 'artwork', 'EG-EDA/M1-12': 'analysis_conformity', 'EG-EDA/M1-13': 'import_approval',
  'EG-EDA/M1-18': 'factory_licence', 'EG-EDA/M1-19': 'commercial_register', 'EG-EDA/M1-20': 'toll_card', 'EG-EDA/M1-24': 'manufacturing_contract',
  'EG-EDA/M1-34': 'stability_approval', 'EG-EDA/M1-35': 'api_coa', 'EG-EDA/M1-36': 'specification', 'EG-EDA/M1-37': 'gmp_certificate',
  'EG-EDA/M1-38': 'gmp_certificate', 'EG-EDA/M1-39': 'dmf_cep', 'EG-EDA/P-09': 'specification', 'EG-EDA/P-10': 'specification',
  'EG-EDA/P-16': 'stability_data', 'EG-EDA/S-14': 'stability_data',
};

// What every paper of an Egyptian dossier must be as a file, each rule with the place in its source that says it.
export const FORMAT = [
  { id: 'pdf', ar: 'PDF ممسوح أو مكتوب، ونصه يتبحث فيه (النشرة المقترحة بس بتتقدّم Word)',
    cite: [{ src: 'eda-np-capp-065-v5', at: 'p.13, general note 4' }, { src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.15, l. 353–357' }] },
  { id: 'version', ar: 'نسخة PDF من 1.4 لـ 1.7؛ الأقدم (1.3 وأقل) لازم يتحوّل', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.15, l. 347–352' }] },
  { id: 'open', ar: 'من غير كلمة سر ولا أي حماية على الملف', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.22, §2.10.2, l. 579–586' }] },
  { id: 'fonts', ar: 'الخطوط جوه الملف (embedded) على قد ما يمكن', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.16, l. 376' }] },
  { id: 'size', ar: 'الملف الواحد مايزيدش عن 100 ميجا، والأكبر يتقسم', cite: [{ src: 'ich-ectd-v322', at: 'Appendix 7, p.114, l. 14' }] },
  { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [{ src: 'ich-ectd-v322', at: 'Appendix 7, p.115, l. 32–35' }] },
  { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.20, §2.9.7, l. 495–502' }, { src: 'ich-ectd-v322', at: 'Appendix 7, p.116, l. 41–43' }] },
];

// The same for the other countries, from their own texts (each rule where it is said): the size a file may have is the country's.
const ICH = at => ({ src: 'ich-ectd-v322', at });
export const FORMATS = {
  EG: FORMAT.map(f => (f.id === 'size' ? { ...f, limitMB: 100 } : f.id === 'version' ? { ...f, target: '1.7' } : f)),
  EU: [
    { id: 'pdf', ar: 'PDF (الأشكال التانية في حالات محددة بس)، ونصه يتبحث فيه: الممسوح يتعمله OCR، ما عدا شهادات GMP وشهادات التحليل وتراخيص التصنيع وشهادات الـ CEP والمراجع العلمية وصفحات التوقيع',
      cite: [{ src: 'eu-aff-2024', at: 'p.1, l. 5 and the table, l. 22' }, { src: 'eu-htg-v601', at: 'p.12, l. 6–25' }] },
    { id: 'version', ar: 'نسخة PDF من 1.4 لـ 1.7 (أو PDF/A)؛ 1.3 والأقدم مرفوض من غير استثناء', target: '1.7', cite: [{ src: 'eu-htg-v601', at: 'p.11, l. 49 – p.12, l. 5' }, { src: 'eu-vc-v82', at: 'criteria 16.1 and 16.BP1' }] },
    { id: 'open', ar: 'من غير كلمة سر ولا أي حماية على الملف (ما عدا نموذج الطلب في 1.0 و1.2 بحدود)', cite: [{ src: 'eu-htg-v601', at: 'p.18, §2.10.2, l. 32–39' }, { src: 'eu-vc-v82', at: 'criteria 16.2 and 16.4' }] },
    { id: 'fonts', ar: 'الخطوط جوه الملف (embedded) على قد ما يمكن', cite: [{ src: 'eu-htg-v601', at: 'p.12, l. 30' }] },
    { id: 'size', ar: 'الملف الواحد مايزيدش عن 500 ميجا (أفضل ممارسة)، والأكبر يتقسم', limitMB: 500, cite: [{ src: 'eu-vc-v82', at: 'criterion 15.BP1' }] },
    { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [ICH('Appendix 7, p.115, l. 32–35')] },
    { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس', cite: [{ src: 'eu-htg-v601', at: 'p.16, l. 16–18' }, { src: 'eu-vc-v82', at: 'criteria 16.BP2 and 16.BP8' }] },
  ],
  GCC: [
    { id: 'pdf', ar: 'PDF زي ما مواصفة ICH بتقول، ويتعمل من ملف إلكتروني مش ممسوح على قد ما يمكن (والممسوح نصه يتبحث فيه)',
      cite: [{ src: 'gcc-m1-spec-v15', at: 'p.11, l. 21–22, and Table 1, p.12' }, ICH('Appendix 7, p.116, l. 8–10')] },
    { id: 'version', ar: 'نسخة PDF 1.4 (اللي كل هيئات ICH اتفقت تقبلها)؛ أي نسخة تانية حسب إرشاد الهيئة. القديم (1.3 وأقل) البرنامج بيحفظه 1.4', target: '1.4', cite: [ICH('Appendix 7, p.114, l. 17–20')] },
    { id: 'open', ar: 'من غير كلمة سر ولا أي حماية على الملف أو التقديم', cite: [{ src: 'gcc-m1-spec-v15', at: 'p.13, §2.4.4, l. 25–27' }] },
    { id: 'fonts', ar: 'الخطوط غير الأساسية جوه الملف (embedded) بكل حروفها', cite: [ICH('Appendix 7, p.114, l. 26–28')] },
    { id: 'size', ar: 'الملف الواحد مايزيدش عن 100 ميجا، والأكبر يتقسم', limitMB: 100, cite: [ICH('Appendix 7, p.114, l. 14')] },
    { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [ICH('Appendix 7, p.115, l. 32–35')] },
    { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس', cite: [{ src: 'gcc-m1-spec-v15', at: 'p.11, §2.1.4, l. 3–8' }] },
  ],
  US: [
    { id: 'pdf', ar: 'PDF، ويتعمل من ملف إلكتروني مش ممسوح على قد ما يمكن (الممسوح مابيتبحثش فيه)', cite: [ICH('p.14, l. 13–14'), ICH('Appendix 7, p.116, l. 8–10')] },
    { id: 'version', ar: 'نسخة PDF اللي ICH اتفقت عليها (1.4)؛ أي نسخة تانية حسب إرشاد FDA. القديم (1.3 وأقل) البرنامج بيحفظه 1.4', target: '1.4', cite: [{ src: 'fda-ectd-validation-criteria', at: 'criterion 5035, p.60' }, ICH('Appendix 7, p.114, l. 17–20')] },
    { id: 'open', ar: 'من غير كلمة سر ولا إعدادات حماية (ما عدا نماذج FDA)', cite: [{ src: 'fda-ectd-validation-criteria', at: 'criteria 5050, p.62, and 5020, p.57' }] },
    { id: 'fonts', ar: 'الخطوط غير الأساسية جوه الملف (embedded) بالكامل', cite: [{ src: 'fda-ectd-validation-criteria', at: 'criterion 5005, p.57' }] },
    { id: 'size', ar: 'الملف الواحد مايزيدش عن 400 ميجا', limitMB: 400, cite: [{ src: 'fda-ectd-validation-criteria', at: 'criterion 1238, p.12' }] },
    { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [ICH('Appendix 7, p.115, l. 32–35')] },
    { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس، ومفيش bookmark مكسور', cite: [ICH('Appendix 7, p.116, l. 41–43'), { src: 'fda-ectd-validation-criteria', at: 'p.63–64' }] },
  ],
  OTHER: [
    { id: 'pdf', ar: 'PDF، ويتعمل من ملف إلكتروني مش ممسوح على قد ما يمكن (الممسوح نصه يتبحث فيه)', cite: [ICH('p.14, l. 13–14'), ICH('Appendix 7, p.116, l. 8–10')] },
    { id: 'version', ar: 'نسخة PDF 1.4 (اللي كل هيئات ICH اتفقت تقبلها)؛ PDF/A-1 مابيكفيش للمراجعة، وأي نسخة تانية حسب إرشاد الدولة. القديم البرنامج بيحفظه 1.4', target: '1.4', cite: [ICH('Appendix 7, p.114, l. 17–20')] },
    { id: 'open', ar: 'من غير كلمة سر ولا أي حماية على الملف', cite: [ICH('Appendix 7, p.117, l. 37–39')] },
    { id: 'fonts', ar: 'الخطوط غير الأساسية جوه الملف (embedded) بكل حروفها', cite: [ICH('Appendix 7, p.114, l. 26–28')] },
    { id: 'size', ar: 'الملف الواحد مايزيدش عن 100 ميجا، والأكبر يتقسم', limitMB: 100, cite: [ICH('Appendix 7, p.114, l. 14')] },
    { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [ICH('Appendix 7, p.115, l. 32–35')] },
    { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس', cite: [ICH('Appendix 7, p.116, l. 41–43')] },
  ],
};
export const formatOf = countryId => FORMATS[countryId] || FORMATS.OTHER;

// The rule card of one place: how the paper is recognised, where it goes, what it must hold, how long it is valid, what it must be
// as a file, what the program reads from it, who may change it, what is checked, the template — each with its sources.
export function ruleCard(knowledge, placeId, countryId = null) {
  const r = knowledge.requirements.find(x => x.id === placeId);
  if (!r) return null;
  const cid = countryId || SET_COUNTRY[r.set] || 'OTHER';
  const short = placeId.split('/').pop();
  const types = TYPES.filter(t => (t.places || []).includes(placeId)).map(t => t.ar);
  const words = knowledge.recognition?.[r.set]?.[short] || [];
  const dt = DOCTYPE_OF[placeId] ? knowledge.doctypes.items.find(d => d.id === `EG-EDA/doc/${DOCTYPE_OF[placeId]}`) : null;
  const tpl = r.set === 'eg-eda-ctd' ? knowledge.templates.find(t => t.id === short) : null;
  return {
    id: r.id, ctd: String(r.ctd || ''), title: r.title, group: r.group || '', status: r.status,
    recognise: { types, words },
    place: { ctd: String(r.ctd || ''), ectd: r.ectd || [], module: r.module },
    must: { en: r.acceptance || '', note: r.note || '' },
    validity: dt ? { months: dt.validity_months ?? null, warn_days: dt.warn_days ?? null, title: dt.title, note: dt.note_source || '', cite: dt.cite || [] } : null,
    format: formatOf(cid),
    validity_by: dt ? 'type' : 'dates',                     // its type's validity (Egypt's types), or the dates written on it
    party: { class: r.doc_class, who: r.produced_by, ...(PARTY[r.doc_class] || { party: 'company', ar: '' }) },
    template: tpl ? { kind: tpl.kind, draft: tpl.draft, generator: tpl.generator || null, example: tpl.example || null,
                      sections: (tpl.sections || []).map(s => ({ title: s.title, hint: s.hint })) } : null,
    rebuild: r.rebuild || null,
    cite: r.cite || [], ectd_cite: r.ectd_cite || [],
  };
}
