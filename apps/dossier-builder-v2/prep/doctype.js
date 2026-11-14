// What a document is, read from its content (never from its file name), and where it goes: the kinds the preparation meets most,
// each tied to the library's record for its place in the Egyptian CTD (checked to exist by tests/prep.test.mjs).
// A document's title (its first lines) decides first, the words of its first two pages only when the title says nothing; among the
// kinds whose words are there, the one named first wins (a certificate of analysis that cites its specification is a certificate).
// «A letter from EDA» is the general kind, read only when no other fits, so a receipt or a decision on EDA's paper is what it is;
// an approval is EDA's only when EDA's name or a committee is on it (`also`).
import { fold } from '../core/fold.js';

export const TYPES = [
  { type: 'registration_licence', ar: 'إخطار / رخصة تسجيل', rx: /final registration licen[cs]e|registration licen[cs]e for (pharmaceutical|human)|اخطار (ال)?تسجيل (ال)?نهايي|ترخيص تسجيل/i,
    doctype: 'EG-EDA/doc/registration_licence', places: ['EG-EDA/M1-04'] },
  { type: 'transfer_approval', ar: 'موافقة على نقل التصنيع', rx: /(approv\w*|الموافقه علي)\s.{0,30}(manufacturing\s+transfer|transfer of manufactur|نقل (ال)?تصنيع)/i,
    also: /egyptian drug authority|هييه الدواء|central administration|الاداره المركزيه|committee|لجنه|edaegypt/, doctype: 'EG-EDA/doc/variation_approval', places: [] },
  { type: 'stability_approval', ar: 'موافقة / قرار الثبات', rx: /(decision letter|قرار|موافقه)[^]{0,200}(ثبات|stability)|(ثبات|stability)[^]{0,200}(decision letter|approval|committee|لجنه)/i,
    also: /egyptian drug authority|هييه الدواء|central administration|الاداره المركزيه|committee|لجنه|edaegypt/, doctype: 'EG-EDA/doc/stability_approval', places: ['EG-EDA/M1-34', 'EG-EDA/P-16'] },
  { type: 'specification', ar: 'مواصفة المنتج النهائي', rx: /(finished product|release|stability|shelf.life|product|document)( and (release|stability|shelf.life))? specifications?\b|specifications? and test methods?|^\s*specifications?\s*:?\s*$|مواصفات المنتج/im,
    doctype: 'EG-EDA/doc/specification', places: ['EG-EDA/P-09'] },
  { type: 'coa', ar: 'شهادة تحليل', rx: /certificate of analysis|شهاده (ال)?تحليل/i, doctype: null, places: ['EG-EDA/P-11'] },
  { type: 'validation', ar: 'تحقق من طريقة التحليل', rx: /method validation|validation of (the )?analytical|analytical (method )?validation|validation report/i,
    doctype: 'EG-EDA/doc/specification', places: ['EG-EDA/P-10'] },
  { type: 'method', ar: 'طريقة التحليل', rx: /method of analysis|analytical (procedure|method)s?\b|test methods?\b|طريقه (ال)?تحليل/i,
    doctype: 'EG-EDA/doc/specification', places: ['EG-EDA/P-10'] },
  { type: 'fee_receipt', ar: 'إيصال سداد رسوم', rx: /ايصال (سداد|دفع|استلام نقدي)|قسيمه (سداد|دفع)|payment receipt|receipt of payment|سداد (ال)?رسوم|رسوم .{0,20}(نقل|تسجيل|تغيير)/i,
    doctype: null, places: [] },
  { type: 'eda_letter', ar: 'خطاب من الهيئة', general: true, rx: /decision letter|egyptian drug authority|هييه الدواء المصريه/i, doctype: 'EG-EDA/doc/eda_letter', places: [] },
];
export const UNKNOWN = { type: 'unknown', ar: 'مش معروف نوعه', doctype: null, places: [] };
// the rules meet folded text (core/fold.js): «هيئة» is read as «هييه», «الآتية» as «الاتيه»

// pages [{text}] → the kind named first in the document's title, else in its first two pages; else a letter from EDA; else UNKNOWN.
export function typeOf(pages) {
  const first = String(pages[0]?.text || '').split('\n').map(l => l.trim()).filter(Boolean);
  const title = fold(first.slice(0, 12).join('\n'));
  const head = fold(pages.slice(0, 2).map(p => p.text || '').join('\n'));
  const named = text => {
    let best = null, at = Infinity;
    for (const t of TYPES) {
      if (t.general || (t.also && !t.also.test(head))) continue;
      const m = t.rx.exec(text);
      if (m && m.index < at) { best = t; at = m.index; }
    }
    return best;
  };
  return named(title) || named(head) || TYPES.find(t => t.general && t.rx.test(head)) || UNKNOWN;
}
