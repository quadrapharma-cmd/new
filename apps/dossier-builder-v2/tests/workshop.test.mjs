// Part 2, the workshop's own logic in Node: the conditions of the library's requirements, the board of an Egyptian dossier for each
// case of the product, the rule cards and their sources, the documents of a made-up dossier received, cut, typed, placed and checked
// — the combined file cut into its two documents, the five problems found again, every required place that is empty said — the ZIP
// the workshop writes, and its PDF work (cut, turn, outline, join). Every name and number is made up.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { evaluate } from '../workshop/expr.js';
import { boardOf, ruleCard, FORMAT } from '../workshop/board.js';
import { newDossier, addFiles, understand, moveDoc } from '../workshop/pipeline.js';
import { checkDossier, placeStatus } from '../workshop/checks.js';
import { zipOf } from '../workshop/zipw.js';
import { pdfInfo, cutPdf, turnPages, withOutline, mergePdfs } from '../workshop/pdfops.js';
import { unzip } from '../prep/zip.js';
import { LICENCE, SPEC, STABILITY, RECEIPTS, COA } from './fixtures/dossier.mjs';
import { pdfOf } from './fixtures/pdfs.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const knowledge = JSON.parse(fs.readFileSync(path.join(ROOT, 'dist', 'knowledge.json'), 'utf8'));
const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');

test('the conditions of the library read as Python would', () => {
  const env = { activity: 're_registration', column: 'G_LOC', licence: 'toll', api_options: ['CEP', 'FULL'], dosage_specifics: ['coated'], biowaiver: '' };
  assert.equal(evaluate("activity == 're_registration'", env), true);
  assert.equal(evaluate("column != 'G_LOC' or licence == 'under_licence'", env), false);
  assert.equal(evaluate("licence in ['toll', 'f_toll']", env), true);
  assert.equal(evaluate("'CEP' in api_options", env), true);
  assert.equal(evaluate("'DMF' in api_options", env), false);
  assert.equal(evaluate("'coated' in dosage_specifics or 'pellets' in dosage_specifics", env), true);
  assert.equal(evaluate("eu_legal_basis in ('generic', 'hybrid', 'biosimilar')", env), false);
  assert.equal(evaluate('not store_separate_from_factory', env), true);
  assert.equal(evaluate("biowaiver != ''", env), false);
  assert.throws(() => evaluate('__proto__.x = 1', env));
  // every condition the library holds can be read
  for (const r of knowledge.requirements) {
    if (r.applies && r.applies !== 'true') evaluate(r.applies, env);
    for (const cell of Object.values(r.required || {})) for (const c of cell.cases || []) if (c.when) evaluate(c.when, env);
  }
});

test('the board of an Egyptian dossier follows the product\'s case, and every place has its rule card with sources that exist', () => {
  const loc = boardOf(knowledge, { countryId: 'EG', profile: {} });
  const imp = boardOf(knowledge, { countryId: 'EG', profile: { origin: 'imported' } });
  assert.equal(loc.column, 'G_LOC');
  assert.equal(imp.column, 'G_IMP');
  const level = (b, ctd) => b.places.find(p => p.ctd === ctd)?.level;
  assert.equal(level(loc, '1.1.12'), 'R');                 // the import approval of each API: local products
  assert.ok(['NR', 'NA'].includes(level(imp, '1.1.12')));
  assert.ok(['NR', 'NA'].includes(level(loc, '1.1.14')));  // the list of countries: imported products
  assert.equal(level(imp, '1.1.14'), 'R');
  const rereg = boardOf(knowledge, { countryId: 'EG', profile: { origin: 'imported', activity: 're_registration' } });
  assert.equal(level(imp, '1.1.11'), 'NR');                // the inspection report: re-registration of imported products
  assert.equal(level(rereg, '1.1.11'), 'R');
  assert.equal(loc.places.length, 101);
  const sources = new Set(knowledge.sources.map(s => s.id));
  for (const f of FORMAT) for (const c of f.cite) assert.ok(sources.has(c.src), `${f.id}: ${c.src}`);
  for (const p of loc.places) {
    const card = ruleCard(knowledge, p.id);
    assert.ok(card && card.title.ar && card.party.ar, p.id);
    for (const c of card.cite) assert.ok(sources.has(c.src), `${p.id}: ${c.src}`);
  }
  const gmp = ruleCard(knowledge, 'EG-EDA/M1-37');
  assert.equal(gmp.validity.months, 36);
  assert.equal(gmp.party.party, 'third');
  assert.ok(gmp.recognise.words.includes('gmp certificate'));
  assert.equal(ruleCard(knowledge, 'EG-EDA/M1-01').template.generator, 'annex1');
  for (const id of ['GCC', 'EU', 'US', 'OTHER']) assert.ok(boardOf(knowledge, { countryId: id }).places.length > 50, id);
});

async function madeUpDossier() {
  const blobs = new Map();
  const env = { knowledge, read: { pdfjs }, putBlob: async (id, k, b) => { blobs.set(`${id}/${k}`, b); }, getBlob: async (id, k) => blobs.get(`${id}/${k}`) };
  const files = [
    { name: 'licence and stability.pdf', bytes: await pdfOf([LICENCE, STABILITY]) },        // one file, two documents
    { name: 'specification.pdf', bytes: await pdfOf(SPEC) },
    { name: 'receipts.pdf', bytes: await pdfOf(RECEIPTS) },
    { name: 'coa.pdf', bytes: await pdfOf(COA) },
    { name: 'coa copy.pdf', bytes: await pdfOf(COA) },                                    // the same file twice
  ];
  const d = newDossier({ country: 'EG', profile: {} });
  await addFiles(d, files, env);
  const board = await understand(d, env);
  return { d, board, env };
}

test('a made-up dossier: received, the combined file cut, each document typed and placed, the copy known, the problems found', { timeout: 120000 }, async () => {
  const { d, board, env } = await madeUpDossier();
  const byName = n => d.docs.find(x => x.name === n);
  assert.equal(byName('coa copy.pdf').dup, byName('coa.pdf').id);
  const combined = byName('licence and stability.pdf');
  assert.ok(combined.split, 'the combined file is cut');
  assert.deepEqual(combined.cut.segments, [[1, 2], [3, 3]]);
  const parts = d.docs.filter(x => x.from?.doc === combined.id);
  assert.deepEqual(parts.map(x => x.type), ['registration_licence', 'stability_approval']);
  // a stability approval goes to 3.2.P.8 in a One Submission; Module 1's 1.2.2 holds the approvals only in a Rolling Submission
  assert.deepEqual(parts.map(x => x.place), ['EG-EDA/M1-04', 'EG-EDA/P-16']);
  assert.equal((await pdfInfo(await env.getBlob(d.id, parts[0].sha))).pages, 2);
  assert.equal(byName('specification.pdf').place, 'EG-EDA/P-09');
  assert.equal(byName('coa.pdf').place, 'EG-EDA/P-11');
  assert.equal(parts[0].party, 'eda');
  const findings = await checkDossier(d, board, { ...env, today: '2026-11-14', generators: { 'EG-EDA/M1-01': 'annex1' } });
  const ids = findings.map(f => f.id);
  for (const id of ['cross-manufacturer-changed', 'cross-approved-limit-ascorbic-acid', 'cross-conditions-' + parts[0].id]) assert.ok(ids.includes(id), `${id} not in ${ids.join(' ')}`);
  assert.ok(ids.some(id => id.startsWith('cross-review_date-')), 'the review date that passed');
  assert.ok(ids.some(id => id.startsWith('cross-form-citric-acid')), 'the two forms of citric acid');
  const missing = findings.find(f => f.id === 'missing-EG-EDA/M1-01');
  assert.equal(missing.level, 'amber');                    // the program can write it
  assert.equal(missing.fix.auto, 'create');
  assert.equal(findings.find(f => f.id === 'missing-EG-EDA/M1-37').level, 'red');   // a GMP certificate: only its issuer can give it
  for (const f of findings) assert.ok(f.rule && Array.isArray(f.rule.cite), f.id);
  assert.equal(placeStatus('EG-EDA/M1-37', d, findings), 'empty');
  assert.equal(placeStatus('EG-EDA/M1-04', d, findings), 'red');
  // the viewer moves a document: it is placed there, by them
  moveDoc(d, byName('receipts.pdf').id, 'EG-EDA/M1-03');
  assert.equal(byName('receipts.pdf').placeBy, 'you');
  assert.ok(d.log.some(e => e.what === 'moved'));
});

test('the ZIP the workshop writes opens with Arabic names, and the PDF work keeps pages as they are', async () => {
  const z = await zipOf([{ name: 'Module 1/1.1.1 نموذج الطلب.pdf', bytes: new Uint8Array(500).fill(65) }, { name: 'a.txt', bytes: new TextEncoder().encode('x') }]);
  const { files } = await unzip(z);
  assert.deepEqual(files.map(f => [f.name, f.bytes.length]), [['Module 1/1.1.1 نموذج الطلب.pdf', 500], ['a.txt', 1]]);
  const four = await pdfOf([LICENCE, STABILITY, SPEC]);
  assert.equal((await pdfInfo(four)).pages, 4);
  const cut = await cutPdf(four, 2, 3);
  assert.equal((await pdfInfo(cut)).pages, 2);
  const turned = await pdfInfo(await turnPages(four, { 0: 1 }));
  assert.equal(turned.sizes[0].rotate, 90);
  const marked = await withOutline(four, [{ title: 'الإخطار', page: 1 }, { title: 'Stability', page: 3 }], { title: '1.1.4 Registration licence' });
  const info = await pdfInfo(marked);
  assert.equal(info.outline, true);
  assert.equal(info.title, '1.1.4 Registration licence');
  const doc = await pdfjs.getDocument({ data: new Uint8Array(marked) }).promise;
  assert.deepEqual((await doc.getOutline()).map(x => x.title), ['الإخطار', 'Stability']);
  assert.equal((await pdfInfo(await mergePdfs([cut, four]))).pages, 6);
});
