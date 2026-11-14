// The board of a dossier (Part 2, step 2.1): the places of the country's dossier, each with what the product's case makes it —
// required (R), optional (O), not required (NR) or not applying (NA) — and the rule card of the paper that goes there. Everything
// comes from the library (dist/knowledge.json): the requirement sets, their conditions, the document types with their validity,
// the templates and the words that recognise each paper. Nothing here is written for one product.
import { evaluate } from './expr.js';
import { TYPES } from '../prep/doctype.js';

// The countries a new dossier can be for: Egypt with its full rules, the others with their own Module 1 and ICH's Modules 2–5.
export const COUNTRIES = [
  { id: 'EG', ar: 'مصر', en: 'Egypt', authority: 'EG-EDA', sets: ['eg-eda-ctd'], full: true, note: 'قواعد هيئة الدواء المصرية كاملة (NP.CAPP.065 الإصدار 5).' },
  { id: 'GCC', ar: 'الخليج', en: 'GCC', authority: 'GCC', sets: ['gcc-m1', 'ich-m4-ctd'], note: 'موديول 1 الخليجي من المكتبة، والموديولات 2–5 من ICH. كروت القواعد لسه عامة.' },
  { id: 'EU', ar: 'أوروبا', en: 'EU', authority: 'EU', sets: ['eu-m1', 'ich-m4-ctd'], note: 'موديول 1 الأوروبي من المكتبة، والموديولات 2–5 من ICH. كروت القواعد لسه عامة.' },
  { id: 'US', ar: 'أمريكا', en: 'USA', authority: 'US-FDA', sets: ['us-fda-m1', 'ich-m4-ctd'], note: 'موديول 1 الأمريكي من المكتبة، والموديولات 2–5 من ICH. كروت القواعد لسه عامة.' },
  { id: 'OTHER', ar: 'دولة تانية', en: 'Other', authority: 'OTHER', sets: ['intl-m1', 'ich-m4-ctd'], note: 'موديول 1 العام من المكتبة، والموديولات 2–5 من ICH. كروت القواعد لسه عامة.' },
];
export const country = id => COUNTRIES.find(c => c.id === id) || COUNTRIES[0];

// The product's case, as the wizard asks it (the names the library's conditions use).
export const PROFILE = {
  dossier_kind: 'generic', origin: 'local', licence: 'own', activity: 'new', route: 'one_submission', leaflet: 'english',
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
};

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
                    doc_class: r.doc_class || '', produced_by: r.produced_by || '', ectd: r.ectd || [] });
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
    cite: [{ src: 'eda-np-capp-065-v5', at: 'p.13, general note 4' }, { src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.15, l. 352–354' }] },
  { id: 'version', ar: 'نسخة PDF من 1.4 لـ 1.7؛ الأقدم (1.3 وأقل) لازم يتحوّل', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.15, l. 346–351' }] },
  { id: 'open', ar: 'من غير كلمة سر ولا أي حماية على الملف', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.22, §2.10.2, l. 578–580' }] },
  { id: 'fonts', ar: 'الخطوط جوه الملف (embedded) على قد ما يمكن', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.16, l. 375' }] },
  { id: 'size', ar: 'الملف الواحد مايزيدش عن 100 ميجا، والأكبر يتقسم', cite: [{ src: 'ich-ectd-v322', at: 'Appendix 7, p.114' }] },
  { id: 'upright', ar: 'كل صفحة في اتجاهها: الطولي طولي والعرضي عرضي', cite: [{ src: 'ich-ectd-v322', at: 'Appendix 7, p.115' }] },
  { id: 'bookmarks', ar: 'المستند اللي فيه فهرس ليه bookmarks بنفس الفهرس', cite: [{ src: 'eda-ectd-technical-guidance-draft-v1', at: 'p.20, §2.9.7, l. 495–502' }, { src: 'ich-ectd-v322', at: 'Appendix 7, p.116' }] },
];

// The rule card of one place: how the paper is recognised, where it goes, what it must hold, how long it is valid, what it must be
// as a file, what the program reads from it, who may change it, what is checked, the template — each with its sources.
export function ruleCard(knowledge, placeId) {
  const r = knowledge.requirements.find(x => x.id === placeId);
  if (!r) return null;
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
    format: r.set === 'eg-eda-ctd' ? FORMAT : [],
    party: { class: r.doc_class, who: r.produced_by, ...(PARTY[r.doc_class] || { party: 'company', ar: '' }) },
    template: tpl ? { kind: tpl.kind, draft: tpl.draft, generator: tpl.generator || null, example: tpl.example || null,
                      sections: (tpl.sections || []).map(s => ({ title: s.title, hint: s.hint })) } : null,
    rebuild: r.rebuild || null,
    cite: r.cite || [], ectd_cite: r.ectd_cite || [],
  };
}
