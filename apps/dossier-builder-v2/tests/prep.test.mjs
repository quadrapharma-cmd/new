// Part 2, «الفحص الأول للملف»: what each document is and where it goes, what it says (with its words), and what reading the
// documents side by side finds. Every document here is made up; the made-up dossier holds the same five problems a real one
// showed (a manufacturer changed with only fee receipts, an approved limit missing from the specification, one substance in two
// forms, a review date passed, a licence's conditions).
import test from 'node:test';
import assert from 'node:assert/strict';
import { prepare } from '../prep/index.js';
import { typeOf, TYPES } from '../prep/doctype.js';
import { factsOf, parseDate, companyKey, RULES } from '../prep/facts.js';
import { fold } from '../core/fold.js';
import { sameCompany } from '../prep/checks.js';
import { convert, molarMass } from '../prep/chem.js';
import { loadKnowledge } from '../tools/load.mjs';
import { createKnowledge } from '../core/knowledge.js';

const knowledge = createKnowledge(loadKnowledge());
const TODAY = '2026-11-14';
import { page, LICENCE, SPEC, STABILITY, RECEIPTS, COA, BLANK, DOSSIER } from './fixtures/dossier.mjs';

const squash = s => String(s).replace(/\s+/g, ' ').trim();
const onItsPage = (docs, e) => squash(docs.find(d => d.id === e.doc).pages.find(p => p.n === e.page).text).includes(squash(e.quote));

test('every kind\'s place in the CTD and its document type are records of the library', () => {
  for (const t of TYPES) {
    for (const id of t.places) assert.ok(knowledge.record(id), `${t.type}: ${id}`);
    if (t.doctype) assert.ok(knowledge.record(t.doctype), `${t.type}: ${t.doctype}`);
  }
  assert.equal(knowledge.record('EG-EDA/M1-04').ctd, '1.1.4');
  assert.equal(knowledge.record('EG-EDA/P-09').ctd, '3.2.P.5.1');
  assert.equal(knowledge.record('EG-EDA/P-11').ctd, '3.2.P.5.4');
});

test('every rule is written the way the text it meets is folded (one alef, ya and ta marbuta; no hamza on ya or waw)', () => {
  const sources = [...RULES, ...TYPES.flatMap(t => [t.rx, t.also].filter(Boolean))].map(r => r.source);
  for (const src of sources) {
    const arabic = src.match(/[\u0600-\u06ff]+/g) || [];
    for (const w of arabic) assert.equal(fold(w), w, `«${w}» in ${src.slice(0, 80)}`);
  }
});

test('a document\'s kind comes from its words: the title first, the kind named first, EDA\'s paper only when nothing else fits', () => {
  assert.equal(typeOf(LICENCE.pages).type, 'registration_licence');
  assert.equal(typeOf(SPEC.pages).type, 'specification');
  assert.equal(typeOf(STABILITY.pages).type, 'stability_approval');
  assert.equal(typeOf(RECEIPTS.pages).type, 'fee_receipt');            // on EDA's paper, still a receipt
  assert.equal(typeOf(COA.pages).type, 'coa');                          // it names its specification: still a certificate
  assert.equal(typeOf(BLANK.pages).type, 'unknown');
  // a company's own specification that mentions stability and an approval is not EDA's stability approval
  assert.equal(typeOf([page(1, 'NILE TEST PHARMA\nRelease and Stability Specification\nApproval: QA Manager')]).type, 'specification');
  assert.equal(typeOf([page(1, 'Egyptian Drug Authority\nRef: 123\nDear Sir, please find attached ...')]).type, 'eda_letter');
  assert.equal(typeOf([page(1, 'هيئة الدواء المصرية\nإخطار تسجيل نهائي لمستحضر صيدلي')]).type, 'registration_licence');
  assert.equal(typeOf([page(1, 'Specifications of Testamin powder for oral solution\nTEST | SPECIFICATION | Method of analysis')]).type, 'specification');
  assert.equal(typeOf([page(1, 'Doc. # MON-PRD-0001\nIssue# 01\nMONOGRAPH\nTitle: | Testamin')]).type, 'monograph');
  assert.equal(typeOf([page(1, 'هيئة الدواء المصرية\nتمت الموافقة على نقل تصنيع المستحضر إلى شركة سيناء')]).type, 'transfer_approval');
});

test('dates as EDA writes them, in either digits', () => {
  assert.equal(parseDate('12/03/2024'), '2024-03-12');
  assert.equal(parseDate('٢٠/١١/٢٠٢٥'), '2025-11-20');
  assert.equal(parseDate('2025/11/20'), '2025-11-20');
  assert.equal(parseDate('5-6-23'), '2023-06-05');
  assert.equal(parseDate('14/Mar/2025'), '2025-03-14');
  assert.equal(parseDate('14 March 2025'), '2025-03-14');
  assert.equal(parseDate('March 14, 2025'), '2025-03-14');
  assert.equal(parseDate('١٤ مارس ٢٠٢٥'), '2025-03-14');
  assert.equal(parseDate('14 Marching 2025'), null);
  assert.equal(parseDate('02/2027'), null);
  assert.equal(parseDate('31/13/2024'), null);
});

test('companies: the words that tell them apart, compared within one alphabet', () => {
  assert.equal(companyKey('Sinai Test Pharma for Pharmaceutical Industries'), 'sinai test');
  assert.equal(companyKey('شركة النيل التجريبية للأدوية'), 'النيل التجريبيه');
  assert.equal(sameCompany('Delta Test Manufacturing', 'DELTA TEST INDUSTRIES'), true);
  assert.equal(sameCompany('Delta Test Manufacturing', 'Sinai Test Industries'), false);
  assert.equal(sameCompany('Sinai Test Industries', 'Sinal Test Industries'), true);   // one letter misread on a scan
  assert.equal(sameCompany('Delta Test Manufacturing', 'شركة دلتا للصناعات الدوائية'), null);
});

test('one substance in two forms: the molecular weights and the sum', () => {
  assert.ok(Math.abs(molarMass('C6H8O7') - 192.12) < 0.01);
  const c = convert('citric acid monohydrate', 11, 'citric acid anhydrous');
  assert.ok(Math.abs(c.amount - 10.057) < 0.001, String(c.amount));
  assert.equal(c.ratio, '192.12 ÷ 210.14');
  assert.equal(convert('citric acid monohydrate', 11, 'ascorbic acid'), null);
  assert.equal(convert('unknownium monohydrate', 11, 'unknownium'), null);
});

test('what a document says, each fact with its page and its words — Arabic read the way a scan gives it', () => {
  const lic = factsOf(LICENCE.pages);
  const get = (facts, field) => facts.filter(f => f.field === field).map(f => f.value);
  assert.deepEqual(get(lic, 'manufacturer'), ['Delta Test Manufacturing']);
  assert.deepEqual(get(lic, 'registration_number'), ['98765/2024']);
  assert.deepEqual(get(lic, 'product_name'), ['Testamin powder for oral solution']);
  assert.deepEqual(get(lic, 'composition'), ['Citric Acid Monohydrate 11.000 g', 'Ascorbic Acid 2.500 g', 'Light Magnesium Oxide 3.500 g']);
  assert.equal(lic.find(f => f.field === 'composition').grams, 11);
  assert.deepEqual(lic.filter(f => f.field === 'condition').map(f => f.number), [1, 2, 3]);
  assert.equal(lic.find(f => f.field === 'condition').page, 2);
  const stab = factsOf(STABILITY.pages);
  assert.deepEqual(get(stab, 'approved_limit'), ['ascorbic acid 40–110%']);
  assert.deepEqual(get(stab, 'decision'), ['approved']);
  assert.deepEqual(get(stab, 'manufacturer'), ['Sinai Test Industries']);
  const rec = factsOf(RECEIPTS.pages);
  assert.deepEqual(get(rec, 'transfer_fee'), ['Sinai Test Industries', 'Sinai Test Industries']);   // one on each page
  assert.equal(get(rec, 'transfer_approval').length, 0);
  const spec = factsOf(SPEC.pages);
  assert.deepEqual(get(spec, 'issuer'), ['SINAI TEST INDUSTRIES']);
  assert.deepEqual(get(spec, 'review_date'), ['2025-02-01']);
  assert.deepEqual(get(spec, 'document_code'), ['QC-FPS-042']);
  // the same labels as a scan writes them (no hamza, ه for ة, Arabic-Indic digits)
  const ar = factsOf([page(1, 'الشركه المصنعه: شركة دلتا للصناعات الدوائية\nرقم التسجيل: ٩٨٧٦٥/٢٠٢٤\nتاريخ المراجعه: ٠١/٠٢/٢٠٢٥')]);
  assert.deepEqual(get(ar, 'manufacturer'), ['شركة دلتا للصناعات الدوائية']);
  assert.deepEqual(get(ar, 'registration_number'), ['98765/2024']);
  assert.deepEqual(get(ar, 'review_date'), ['2025-02-01']);
  // a table's review date with the month in words; a method's steps after «Each … contain» are not ingredients
  const method = factsOf([page(1, 'Revision date: | 14/Mar/2025\nProcedure\nEach 1 sachet contain Citric acid anhydrous 10.06 g.\nTake 7.15 ml of previous solution\nTransfer 363.7 mg of Citric acid anhydrous')]);
  assert.deepEqual(get(method, 'review_date'), ['2025-03-14']);
  assert.deepEqual(get(method, 'composition'), ['Citric acid anhydrous 10.06 g']);
  // every fact's words are on its page
  for (const d of DOSSIER) for (const f of factsOf(d.pages)) assert.ok(onItsPage(DOSSIER, { doc: d.id, page: f.page, quote: f.quote }), `${d.name}: ${f.quote}`);
});

test('the made-up dossier: the five problems found, each with the words on its pages', () => {
  const { documents, findings } = prepare(DOSSIER, { today: TODAY, knowledge });
  assert.deepEqual(documents.map(d => d.type), ['registration_licence', 'specification', 'stability_approval', 'fee_receipt', 'coa', 'unknown']);
  assert.deepEqual(documents[0].places, [{ id: 'EG-EDA/M1-04', ctd: '1.1.4', title: knowledge.record('EG-EDA/M1-04').title }]);
  assert.deepEqual(documents[2].places.map(p => p.ctd), ['1.2.2.1–4', '3.2.P.8']);
  assert.deepEqual(documents.map(d => d.read), [2, 1, 1, 2, 1, 0]);   // the blank scan: nothing read, and it says so
  const ids = findings.map(f => f.id);
  assert.deepEqual(ids, ['manufacturer-changed', 'approved-limit-ascorbic-acid', 'form-citric-acid-d2', 'review_date-d2', 'conditions-d1']);
  const [maker, limit, form, review, conds] = findings;
  assert.equal(maker.level, 'red');
  assert.match(maker.detail, /Delta Test Manufacturing/);
  assert.match(maker.detail, /Sinai Test Industries/);
  assert.match(maker.detail, /مالقيتش في الملف موافقة الهيئة على نقل التصنيع/);
  assert.match(maker.detail, /الإيصال مش موافقة/);
  assert.deepEqual([...new Set(maker.evidence.map(e => e.doc))].sort(), ['d1', 'd2', 'd3', 'd4', 'd5']);
  assert.equal(limit.level, 'red');
  assert.match(limit.detail, /ascorbic acid 40–110%/);
  assert.match(limit.detail, /«specification\.doc» بيذكر ascorbic acid من غير الحد ده/);
  assert.ok(limit.evidence.some(e => e.doc === 'd2' && /Assay of ascorbic acid/.test(e.quote)));
  assert.equal(form.level, 'amber');
  assert.match(form.detail, /11 × 192\.12 ÷ 210\.14 = 10\.057/);
  assert.equal(review.level, 'amber');
  assert.match(review.detail, /2025-02-01/);
  assert.equal(conds.level, 'amber');
  assert.equal(conds.evidence.length, 3);
  for (const f of findings) for (const e of f.evidence) assert.ok(onItsPage(DOSSIER, e), `${f.id}: ${e.quote}`);
});

test('what must not be found: the same maker, an approved transfer, the limit in the specification, a review still ahead', () => {
  const sameMaker = { ...SPEC, pages: [page(1, SPEC.pages[0].text.replace('SINAI TEST INDUSTRIES', 'DELTA TEST INDUSTRIES'))] };
  const noSinai = [LICENCE, sameMaker];
  assert.ok(!prepare(noSinai, { today: TODAY }).findings.some(f => f.id.startsWith('manufacturer')));

  const approval = { id: 'd7', name: 'transfer approval.pdf', pages: [page(1, 'هيئة الدواء المصرية\nتمت الموافقة على نقل تصنيع المستحضر إلى Sinai Test Industries')] };
  const withApproval = prepare([...DOSSIER, approval], { today: TODAY }).findings.find(f => f.id === 'manufacturer-changed');
  assert.equal(withApproval.level, 'amber');
  assert.ok(withApproval.evidence.some(e => e.doc === 'd7'));

  const updated = { ...SPEC, pages: [page(1, SPEC.pages[0].text.replace('Assay of ascorbic acid | 90.0 – 110.0 %', 'Assay of ascorbic acid | 40.0 – 110.0 %').replace('Review Date: 01/02/2025', 'Review Date: 01/02/2027'))] };
  const after = prepare([LICENCE, updated, STABILITY], { today: TODAY }).findings.map(f => f.id);
  assert.ok(!after.some(id => id.startsWith('approved-limit')), after.join());
  assert.ok(!after.some(id => id.startsWith('review_date')), after.join());

  // a monograph that names the substance with an empty limit, beside a specification that states the approved one
  const monograph = { id: 'd9', name: 'monograph.doc', pages: [page(1, 'MONOGRAPH\nTitle: Testamin powder for oral solution'),
    page(2, '8. Quantitative Determination of Ascorbic Acid in Testamin\nMethod: HPLC\nLimit:\n9. Impurities')] };
  const mixed = prepare([LICENCE, updated, STABILITY, monograph], { today: TODAY }).findings.find(f => f.id.startsWith('approved-limit'));
  assert.match(mixed.detail, /«monograph\.doc» بيذكر ascorbic acid من غير الحد ده، والحد مكتوب في «specification\.doc»/);
  assert.deepEqual(mixed.evidence.at(-1), { doc: 'd9', name: 'monograph.doc', page: 2, quote: '8. Quantitative Determination of Ascorbic Acid in Testamin' });

  const arabicMaker = { ...LICENCE, pages: [page(1, LICENCE.pages[0].text.replace('Manufacturer: Delta Test Manufacturing', 'الشركة المصنعة: شركة دلتا للصناعات الدوائية'))] };
  const unsure = prepare([arabicMaker, SPEC], { today: TODAY }).findings.filter(f => f.id.startsWith('manufacturer'));
  assert.deepEqual(unsure.map(f => [f.id, f.level]), [['manufacturer-confirm', 'amber']]);

  const wrongAmount = { ...SPEC, pages: [page(1, SPEC.pages[0].text.replace('Citric Acid Anhydrous 10.06 g', 'Citric Acid Anhydrous 9.50 g'))] };
  const form = prepare([LICENCE, wrongAmount], { today: TODAY }).findings.find(f => f.id.startsWith('form-'));
  assert.equal(form.level, 'red');
  assert.match(form.detail, /والمكتوب 9\.5 جم/);

  const expired = { id: 'd8', name: 'old licence.pdf', pages: [page(1, LICENCE.pages[0].text + '\nValid until: 01/01/2026')] };
  assert.equal(prepare([expired], { today: TODAY }).findings.find(f => f.id.startsWith('invalidation_date')).level, 'red');
});
