// The checks that compare a dossier's documents with one another: what a reviewer finds by reading them side by side. Each
// finding says what was found, in which documents, with the words on their pages. Levels: 'red' (it blocks the file as it
// stands), 'amber' (it must be shown, explained or confirmed in the file).
import { fold } from '../core/fold.js';
import { companyKey } from './facts.js';
import { convert, formOf, namesOf } from './chem.js';

const ev = (doc, f) => ({ doc: doc.id, name: doc.name, page: f.page, quote: f.quote });
// a sum, a formula or a date kept left to right inside an Arabic sentence (Unicode isolates; invisible), so it reads as written
const ltr = s => `\u2066${s}\u2069`;
const factsOf = (docs, field, types) => docs.flatMap(d => (types && !types.includes(d.type) ? [] : d.facts.filter(f => f.field === field).map(f => ({ doc: d, f }))));
const MAKERS = ['specification', 'coa', 'validation', 'method'];   // documents a manufacturer writes on its own paper

// Two company names: the same (true), not the same (false), or not comparable by rule (null: no alphabet in common). Within an
// alphabet the first word that tells companies apart decides, one wrong letter allowed in a long word (a scan's misreading).
const keys = name => ({ latin: companyKey(name.replace(/[؀-ۿ]+/g, ' ')), ar: companyKey(name.replace(/[A-Za-z]+/g, ' ')) });
function near(a, b) {
  if (a === b) return true;
  if (Math.min(a.length, b.length) < 5 || Math.abs(a.length - b.length) > 1) return false;
  let i = 0, j = 0, edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) { i++; j++; continue; }
    if (++edits > 1) return false;
    if (a.length > b.length) i++; else if (b.length > a.length) j++; else { i++; j++; }
  }
  return edits + (a.length - i) + (b.length - j) <= 1;
}
export function sameCompany(a, b) {
  const A = keys(a), B = keys(b);
  for (const s of ['latin', 'ar']) if (A[s] && B[s]) return near(A[s].split(' ')[0], B[s].split(' ')[0]);
  return null;
}

// 1. The licence's manufacturer against the manufacturer the other documents name, and an approval of the change.
function manufacturer(docs) {
  const lic = factsOf(docs, 'manufacturer', ['registration_licence']);
  if (!lic.length) return [];
  const others = [...factsOf(docs, 'manufacturer').filter(x => x.doc.type !== 'registration_licence'), ...factsOf(docs, 'issuer', MAKERS)];
  const verdict = x => {
    const r = lic.map(l => sameCompany(l.f.value, x.f.value));
    return r.includes(true) ? true : r.includes(false) ? false : null;
  };
  const differ = others.filter(x => verdict(x) === false);
  const unsure = others.filter(x => verdict(x) === null);
  const out = [];
  if (differ.length) {
    const distinct = list => list.filter((v, i, all) => all.findIndex(w => w === v || sameCompany(w, v)) === i);
    const names = distinct(differ.map(x => x.f.value));
    const approvals = factsOf(docs, 'transfer_approval').filter(x => differ.some(d => sameCompany(d.f.value, x.f.value) !== false));
    const fees = factsOf(docs, 'transfer_fee');
    const feeTo = distinct(fees.map(x => x.f.value));
    out.push({
      id: 'manufacturer-changed', level: approvals.length ? 'amber' : 'red',
      title: 'المصنع في الإخطار غير المصنع في باقي المستندات',
      detail: `الإخطار بيقول المصنع «${lic[0].f.value}»، وباقي المستندات بتقول «${names.join('» و«')}». `
        + (approvals.length ? 'فيه في الملف موافقة على نقل التصنيع: لازم تتقدم مع الإخطار.'
          : `مالقيتش في الملف موافقة الهيئة على نقل التصنيع${fees.length ? `؛ فيه إيصالات سداد رسوم «نقل تصنيع إلى ${feeTo.join('، ')}» بس، والإيصال مش موافقة` : ''}.`),
      evidence: [...lic, ...differ, ...approvals, ...fees].map(x => ev(x.doc, x.f)),
    });
  }
  if (unsure.length) {
    out.push({
      id: 'manufacturer-confirm', level: 'amber', title: 'اتأكد إن المصنع هو نفسه في المستندات',
      detail: `الإخطار بيقول المصنع «${lic.map(x => x.f.value).join('» / «')}»، ومستندات تانية بتقول «${[...new Set(unsure.map(x => x.f.value))].join('» و«')}» `
        + 'بحروف تانية (عربي وإنجليزي)، فمقدرش أقارنهم بالقاعدة.',
      evidence: [...lic, ...unsure].map(x => ev(x.doc, x.f)),
    });
  }
  return out;
}

// 2. A limit a decision approved, and every document in the file that states the product's limits (its specification, monograph and
// method): each that names the substance must state the approved limit.
const num = n => (Number.isInteger(n) ? `${n}(?:\\.0+)?` : `${String(n).replace('.', '\\.')}0*`);
const STATES = ['specification', 'monograph', 'method'];
function approvedLimits(docs) {
  const out = [];
  const holders = docs.filter(d => STATES.includes(d.type));
  for (const { doc, f } of factsOf(docs, 'approved_limit')) {
    const approved = doc.facts.some(x => x.field === 'decision' && x.value === 'approved');
    const names = namesOf(f.substance).map(fold);
    const limit = new RegExp(`(?<![\\d.])${num(f.low)}\\s*%?\\s*(?:[–\\-−]|to|الي)\\s*${num(f.high)}\\s*%`);
    // where a document states the substance's assay (else where it first names it): the words shown beside the finding
    const where = d => {
      let first = null;
      for (const p of d.pageTexts) for (const line of p.text.split('\n')) {
        const l = fold(line);
        if (!names.some(n => l.includes(n))) continue;
        if (/assay|limit|quantitative|determination|content|تعيين|نسبه|حد/.test(l)) return { page: p.n, quote: line.trim() };
        first = first || { page: p.n, quote: line.trim() };
      }
      return first;
    };
    const without = [], stated = [];
    for (const d of holders) {
      const text = fold(d.text);
      if (names.some(n => text.includes(n))) (limit.test(text) ? stated : without).push({ d, at: where(d) });
    }
    if (!without.length && stated.length) continue;
    const list = xs => xs.map(x => `«${x.d.name}»`).join(' و');
    const lead = `«${doc.name}» ${approved ? 'فيه موافقة على' : 'بيذكر'} «${f.value}». `;
    const detail = !holders.length ? lead + 'ومفيش في الملف مواصفة أو مونوجراف أو طريقة تحليل تتقارن بيه.'
      : !without.length ? lead + `ومفيش مواصفة أو مونوجراف أو طريقة تحليل في الملف بتذكر ${f.substance} خالص.`
        : lead + `${list(without)} ${without.length > 1 ? 'بيذكروا' : 'بيذكر'} ${f.substance} من غير الحد ده`
          + (stated.length ? `، والحد مكتوب في ${list(stated)}` : '') + '. لازم كل مستند بيذكره يتحدّث بالحد اللي اتوافق عليه.';
    out.push({
      id: `approved-limit-${f.substance.replace(/\W+/g, '-')}`, level: 'red',
      title: `حد ${f.substance} اللي ${approved ? 'اتوافق عليه' : 'في القرار'} مش مكتوب في ${stated.length ? 'كل مستندات المواصفة' : 'مواصفة الملف'}`,
      detail,
      evidence: [ev(doc, f), ...doc.facts.filter(x => x.field === 'decision').map(x => ev(doc, x)),
                 ...without.filter(x => x.at).map(x => ({ doc: x.d.id, name: x.d.name, page: x.at.page, quote: x.at.quote }))],
    });
  }
  return out;
}

// 3. One substance in two forms (a hydrate and the anhydrous form) in the licence and in other documents: the same amount or not.
// The documents that give the same form and amount make one finding together.
function forms(docs) {
  const out = [];
  const lic = factsOf(docs, 'composition', ['registration_licence']);
  const rest = factsOf(docs, 'composition').filter(x => x.doc.type !== 'registration_licence');
  const w = n => (n ? `·${n === 1 ? '' : n}H2O` : '');
  const done = new Set();
  for (const a of lic) {
    const fa = formOf(a.f.substance);
    const groups = new Map();                                       // the other form and its amount → the documents that give it
    for (const b of rest) {
      const fb = formOf(b.f.substance);
      if (fa.base !== fb.base || (fa.water ?? 0) === (fb.water ?? 0) || !convert(a.f.substance, a.f.grams, b.f.substance)) continue;
      const key = `${fa.base}|${fb.water ?? 0}|${b.f.grams}`;
      if (!groups.has(key)) groups.set(key, []);
      if (!groups.get(key).some(x => x.doc.id === b.doc.id)) groups.get(key).push(b);
    }
    for (const [key, bs] of groups) {
      if (done.has(key)) continue;
      done.add(key);
      const b = bs[0], c = convert(a.f.substance, a.f.grams, b.f.substance);
      const same = Math.abs(c.amount - b.f.grams) / b.f.grams <= 0.01;
      const names = bs.map(x => `«${x.doc.name}»`).join(' و');
      out.push({
        id: `form-${fa.base.replace(/\W+/g, '-')}-${b.doc.id}`, level: same ? 'amber' : 'red',
        title: same ? `${fa.base}: نفس الكمية مكتوبة بصورتين — لازم التحويل يتوضح في الملف` : `${fa.base}: الكمية في ${names} مش بتساوي اللي في الإخطار`,
        detail: `الإخطار: «${a.f.value}»، و${names}: «${b.f.value}». بالحساب: ${ltr(`${a.f.grams} × ${c.ratio} = ${c.amount.toFixed(3)} g`)} `
          + `(من ${ltr(c.formula + w(c.from.water))} إلى ${ltr(c.formula + w(c.to.water))})`
          + (same ? '، يعني الكميتين واحد.' : `، والمكتوب ${ltr(`${b.f.grams} g`)}.`),
        evidence: [ev(a.doc, a.f), ...bs.map(x => ev(x.doc, x.f))],
      });
    }
  }
  return out;
}

// 4. Dates that have passed: a document's review date, a licence's end.
function dates(docs, today) {
  const out = [];
  for (const { doc, f } of [...factsOf(docs, 'review_date'), ...factsOf(docs, 'invalidation_date')]) {
    if (f.value >= today) continue;
    const review = f.field === 'review_date';
    out.push({ id: `${f.field}-${doc.id}`, level: review ? 'amber' : 'red',
      title: review ? `معاد مراجعة «${doc.name}» عدّى` : `«${doc.name}» انتهت صلاحيته`,
      detail: `${review ? 'تاريخ المراجعة' : 'تاريخ الانتهاء'} ${ltr(f.value)}، والنهارده ${ltr(today)}.${review ? ' لازم نسخة متراجعة، أو سبب مكتوب إنها لسه سارية.' : ''}`,
      evidence: [ev(doc, f)] });
  }
  return out;
}

// 5. The conditions a licence sets: each needs its evidence in the file.
function conditions(docs) {
  const out = [];
  for (const d of docs.filter(x => x.type === 'registration_licence')) {
    const cs = d.facts.filter(f => f.field === 'condition');
    if (!cs.length) continue;
    out.push({ id: `conditions-${d.id}`, level: 'amber', title: `الإخطار فيه ${cs.length} شروط لازم الملف يثبت إنها اتنفذت`,
      detail: cs.map(c => `${c.number}. ${c.value}`).join('\n'), evidence: cs.map(c => ev(d, c)) });
  }
  return out;
}

export function check(docs, { today = new Date().toISOString().slice(0, 10) } = {}) {
  return [...manufacturer(docs), ...approvedLimits(docs), ...forms(docs), ...dates(docs, today), ...conditions(docs)]
    .sort((a, b) => (a.level === b.level ? 0 : a.level === 'red' ? -1 : 1));
}
