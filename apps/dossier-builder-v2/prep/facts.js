// What a document says, read by rules from its pages' text (a PDF's text layer, a scanned page's reading, a Word file's text):
// each fact with its page and the words that hold it, so the user can see it on the page. Arabic and English; Arabic-Indic digits
// are read as digits. Nothing is guessed: a field the rules do not find is simply absent.
// The rules read each line folded (core/fold.js: one alef, ya and ta marbuta, Western digits, lower case), so a scan read as
// «الموافقه علي» and a PDF that writes «الموافقة على» say the same; the value a rule finds is taken from the line as written.
import { fold, foldChar } from '../core/fold.js';

const digits = s => String(s).replace(/[٠-٩]/g, c => String(c.charCodeAt(0) - 0x660)).replace(/[۰-۹]/g, c => String(c.charCodeAt(0) - 0x6f0));

// A date as documents write it (dd/mm/yyyy, dd-mm-yyyy, yyyy/mm/dd, 14/Mar/2025, 14 March 2025, March 14, 2025, ١٤ مارس ٢٠٢٥; either
// digits) → 'yyyy-mm-dd', or null.
const MONTHS = [['jan', 'january', 'يناير'], ['feb', 'february', 'فبراير'], ['mar', 'march', 'مارس'], ['apr', 'april', 'ابريل', 'أبريل'],
                ['may', 'مايو'], ['jun', 'june', 'يونيو'], ['jul', 'july', 'يوليو'], ['aug', 'august', 'اغسطس', 'أغسطس'],
                ['sep', 'sept', 'september', 'سبتمبر'], ['oct', 'october', 'اكتوبر', 'أكتوبر'], ['nov', 'november', 'نوفمبر'], ['dec', 'december', 'ديسمبر']];
const monthOf = w => { const f = fold(w); return MONTHS.findIndex(names => names.some(n => f === fold(n))) + 1; };
const ymd = (y, mo, d) => (mo < 1 || mo > 12 || d < 1 || d > 31 || y < 1950 || y > 2100 ? null : `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`);
export function parseDate(s) {
  const t = digits(s);
  const m = t.match(/(\d{1,4})\s*[\/\-.]\s*(\d{1,2})\s*[\/\-.]\s*(\d{1,4})/);
  if (m) {
    const [, a, b, c] = m;
    if (a.length === 4) return ymd(+a, +b, +c);
    return ymd(c.length === 2 ? 2000 + +c : +c, +b, +a);
  }
  const w = t.match(/(\d{1,2})[\s\/\-.]*([A-Za-z\u0600-\u06ff]{3,9})\.?[\s\/\-.,]*(\d{4})/);   // 14/Mar/2025, 14 March 2025, ١٤ مارس ٢٠٢٥
  if (w && monthOf(w[2])) return ymd(+w[3], monthOf(w[2]), +w[1]);
  const v = t.match(/([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})/);                                      // March 14, 2025
  if (v && monthOf(v[1])) return ymd(+v[3], monthOf(v[1]), +v[2]);
  return null;
}

// The words of a company that tell it apart (legal and trade words dropped): «Sinai Test Pharma for Pharmaceutical Industries» → sinai test.
const NOISE = new Set(('pharma pharm pharmaceutical pharmaceuticals industries industry for and the co company ltd llc inc sae s.a.e '
  + 'egypt egyptian international nutraceuticals laboratories labs group of chemical chemicals medical شركه للادويه للصناعات '
  + 'الصناعات الدوائيه والكيماويه الكيماويه لصناعه الادويه مصر').split(' '));
export function companyKey(name) {
  return fold(name).replace(/[^\p{L}\p{N} ]+/gu, ' ').split(/\s+/).filter(w => w.length > 1 && !NOISE.has(w)).slice(0, 2).join(' ');
}
// Which alphabet a name is written in: companies are compared only within one (an Arabic and a Latin name cannot be matched by rule).
export const scriptOf = s => (/[\u0600-\u06ff]/.test(s) ? (/[A-Za-z]/.test(s) ? 'mixed' : 'ar') : 'latin');

// A line folded, with the place in the line each folded character came from (the value is cut from the line as written).
function folded(line) {
  let f = '';
  const at = [];
  for (let i = 0; i < line.length; i++) { const x = foldChar(line[i]); for (let k = 0; k < x.length; k++) at.push(i); f += x; }
  at.push(line.length);
  return { line, f, at };
}
const cut = (L, s, e) => L.line.slice(L.at[s], L.at[e]);
// the text of group `g` of a match (made with the d flag) on the folded line, as written in the line
const group = (L, m, g) => cut(L, m.indices[g][0], m.indices[g][1]);

const LABELS = [   // folded line → the value after the label (group 1)
  ['product_name', /^(?:trade name|product name|name of (?:the )?product|اسم المستحضر|الاسم التجاري)\s*[:：|]?\s*(.+)$|^(?:product|المستحضر)\s*[:：|]\s*(.+)$/d],
  ['dosage_form', /^(?:dosage form|pharmaceutical form|الشكل الصيدلي)\s*[:：|]?\s*(.+)$/d],
  ['manufacturer', /^(?:manufacturer(?: name)?|manufactured by|manufacturing site|site of manufacture|الشركه المصنعه|الجهه المصنعه|جهه التصنيع|المصنع|مكان التصنيع)\s*[:：|]\s*(.+)$/d],
  ['license_holder', /^(?:licen[cs]e holder|marketing authori[sz]ation holder|ma holder|صاحب الترخيص|صاحب الاخطار|صاحب المستحضر|الشركه صاحبه (?:الترخيص|الاخطار|المستحضر))\s*[:：|]\s*(.+)$/d],
  ['applicant', /^(?:applicant(?: name| company)?|مقدم الطلب|الشركه مقدمه الطلب)\s*[:：|]\s*(.+)$/d],
  ['document_code', /(?:document code|doc\.? code|document no\.?|sop no\.?)\s*[:：|]?\s*([a-z0-9][a-z0-9\/\-.]{2,29})/d],
];
const DATES = [
  ['issue_date', /(?:issue date|date of issue|issued on|effective date|تاريخ الاصدار|تاريخ اصدار)\s*[:：|]?\s*/],
  ['review_date', /(?:review date|next review(?: date)?|revision due(?: date)?|revision date|due for revision|تاريخ المراجعه)\s*[:：|]?\s*/],
  ['invalidation_date', /(?:invalidation date|valid until|valid till|licen[cs]e expiry(?: date)?|expiry of (?:the )?licen[cs]e|صالح حتي|ساري حتي|تاريخ انتهاء (?:الترخيص|الاخطار))\s*[:：|]?\s*/],
];
const UNIT = '(mg|g|gm|grams?|mcg|[µμ]g|ug|iu)';   // what one unit of the product holds is weighed (a volume is the product's own)
const STEPS = /^(take|transfer|add|dissolve|weigh|dilute|inject|prepare|mix|heat|cool|fill|pipette|use|accurately|about|approximately|equivalent|containing|of)\b/;   // a method's steps, not an ingredient
// an ingredient's line: a number or a table's rule before it, or the label «Strength(s):», then the name and the amount
const AMOUNT = new RegExp(`^[\\s|_—–\\-:;.]*(?:strengths?\\s*(?:\\(s\\))?\\s*[:：]\\s*)?(?:\\d{1,2}\\s*[.)|\\-]\\s*)?([a-z][a-z \\-(),]{2,60}?)[\\s|.:…]+(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`, 'd');
const CONTAINS = new RegExp(`conta[il1]ns?\\s*:?\\s+([a-z][a-z \\-]{2,60}?)\\s+(\\d+(?:\\.\\d+)?)\\s*${UNIT}\\b`, 'gd');
// «Each sachet contains», as a scan may read it too («Fach sachet contalns»)
const COMPOSITION = /\b[a-z]?ach\s+\w+(?:\s+\w+)?\s+conta[il1]ns?|active ingredients?|active substances?|^composition\b|التركيب|المواد الفعاله|المكونات الفعاله/;
const CONDITIONS = /^(?:special |registration )?conditions?\b|^(?:ال)?شروط(?:\s|:|$)|بالشروط (?:الاتيه|التاليه)|with the following conditions|subject to the following|مع الالتزام بالاتي/;
const CONDITION = /^(\d{1,2})\s*[.\-)]\s*(.{15,})$/d;
const REGISTRATION = /(?:registration no\.?|registration number|reg\.? no\.?|رقم التسجيل|رقم الاخطار)\s*[:：|]?\s*(\d{3,7}\s*\/\s*\d{4})/;
// «Limit of ascorbic acid to be 40 – 110 %» (a scan may lose the %: the words «to be» and the range say it)
const LIMIT = /limit of\s+(.+?)\s+to be\s+(\d+(?:\.\d+)?)\s*%?\s*[–\-−]\s*(\d+(?:\.\d+)?)(?!\d)/d;
const DECISION = /الموافقه علي طلب الشركه|الموافقه علي الطلب|وافقت اللجنه|request (?:is |was |has been )?approved|approval of the (?:company'?s )?request|the committee approved/;
const APPROVES = /الموافقه|وافقت|approv/;
const FEE = [/manufacturing\s+transfer\s+to\s+([a-z\u0600-\u06ff][a-z\u0600-\u06ff .&\-]{2,60})/d, /نقل (?:ال)?تصنيع (?:الي|ل)\s*(.{3,60})/d];
const TRANSFER = /(?:approv\w*|الموافقه علي|وافقت)\s.{0,40}(?:manufacturing\s+transfer|transfer of manufactur\w*|نقل (?:ال)?تصنيع)\s.{0,15}?(?:to|الي)\s+([a-z\u0600-\u06ff][a-z0-9\u0600-\u06ff .&\-]{2,60})/d;
// Every rule, for the test that each is written in folded form (a rule written «هيئة» would never meet a folded «هييه»).
export const RULES = [...LABELS.map(x => x[1]), ...DATES.map(x => x[1]), AMOUNT, CONTAINS, STEPS, COMPOSITION, CONDITIONS, CONDITION, REGISTRATION, LIMIT,
                      DECISION, APPROVES, ...FEE, TRANSFER];

// a value without what a scan leaves around it: direction marks, and rules, dashes and stray signs before its first letter or after
// its last («~=—— Delta Test …» → «Delta Test …»); a closing bracket, a % or a unit's dot stay
const clean = s => String(s).replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, '').replace(/\s+/g, ' ')
  .replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N})%\]]+$/gu, '').trim();
const value = s => clean(String(s).split(/\s{3,}|\t|\s\|\s/)[0]);
const firm = s => value(String(s).split(/\s[—–-]\s|[,،؛;]/)[0]);   // a company's name, without what follows it on the line
const grams = (n, u) => { const v = Number(digits(n)); const k = u.toLowerCase(); return k === 'mg' ? v / 1000 : /^(mcg|[µμ]g|ug)$/.test(k) ? v / 1e6 : v; };

// One document's pages ([{n, text}]) → facts [{field, value, page, quote, ...}].
export function factsOf(pages) {
  const out = [];
  const add = (field, val, page, quote, extra = {}) => {
    if (!val) return;
    if (out.some(f => f.field === field && f.value === val && f.page === page)) return;
    out.push({ field, value: val, page, quote: clean(quote).slice(0, 240), ...extra });
  };
  let conditions = false;
  for (const { n, text } of pages) {
    const lines = String(text || '').replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, '').split(/\n/).map(l => l.trim()).filter(Boolean);
    // the company that wrote the document: an upper-case company name among the first lines (a specification's header)
    head: for (const l of lines.slice(0, 5)) {
      for (const cell of l.split(/\s*\|\s*|\s{3,}|\t/)) {
        if (/\b(PHARMA|PHARMACEUTICALS?|INDUSTRIES|LABORATORIES)\b/.test(cell) && cell === cell.toUpperCase() && !/[:：]/.test(cell)) { add('issuer', clean(cell), n, l); break head; }
      }
    }
    let composition = 0;
    for (const line of lines) {
      const L = folded(line);
      const f = L.f;
      for (const [field, rx] of LABELS) {
        const m = f.match(rx);
        if (!m) continue;
        const g = m[1] !== undefined ? 1 : 2;
        const v = value(group(L, m, g));
        if (v.length >= 2) add(field, v, n, line);
      }
      for (const [field, rx] of DATES) {
        const m = f.match(rx);
        if (m) { const iso = parseDate(f.slice(m.index + m[0].length)); if (iso) add(field, iso, n, line); }
      }
      const reg = f.match(REGISTRATION);
      if (reg) add('registration_number', reg[1].replace(/\s+/g, ''), n, line);
      // the composition: the lines after «Each … contains», «Active ingredients» or «Composition»
      if (COMPOSITION.test(f)) composition = 8;
      else if (composition > 0) {
        composition--;
        const m = f.match(AMOUNT);
        if (m && !STEPS.test(m[1])) {
          const name = clean(group(L, m, 1));
          add('composition', `${name} ${m[2]} ${m[3]}`, n, line, { substance: name.toLowerCase(), grams: grams(m[2], m[3]) });
        }
      }
      for (const m of f.matchAll(CONTAINS)) {
        if (STEPS.test(m[1])) continue;
        const name = clean(group(L, m, 1));
        add('composition', `${name} ${m[2]} ${m[3]}`, n, line, { substance: name.toLowerCase(), grams: grams(m[2], m[3]) });
      }
      // a limit an authority approved, and the decision
      const lim = f.match(LIMIT);
      if (lim) {
        const name = clean(group(L, lim, 1));
        add('approved_limit', `${name} ${lim[2]}–${lim[3]}%`, n, line, { substance: name.toLowerCase(), low: +lim[2], high: +lim[3] });
      }
      if (DECISION.test(f)) add('decision', 'approved', n, line);
      // fees paid for, and approvals of, moving the manufacture to another company
      const fee = f.match(FEE[0]) || f.match(FEE[1]);
      if (fee && !APPROVES.test(f)) add('transfer_fee', firm(group(L, fee, 1)), n, line);
      const appr = f.match(TRANSFER);
      if (appr) add('transfer_approval', firm(group(L, appr, 1)), n, line);
      // the numbered conditions of a licence, after the words that open them
      if (CONDITIONS.test(f)) conditions = true;
      else if (conditions) {
        const c = f.match(CONDITION);
        if (c) add('condition', clean(group(L, c, 2)), n, line, { number: Number(c[1]) });
      }
    }
  }
  return out;
}
