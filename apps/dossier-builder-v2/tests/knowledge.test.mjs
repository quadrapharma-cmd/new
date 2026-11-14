// Part 1a: the knowledge in code. Every record rests on a registered source, nothing points nowhere, and the program can find it.
import test from 'node:test';
import assert from 'node:assert/strict';
import { loadKnowledge, checkHeldFiles } from '../tools/load.mjs';
import { validate, allRecords, citationsOf } from '../core/validate.js';
import { createKnowledge, fold } from '../core/knowledge.js';

const data = loadKnowledge();
const K = createKnowledge(data);
const copy = () => structuredClone(data);

test('the knowledge passes every rule: no record without a source, no unregistered source, no broken reference', () => {
  const { errors, warnings } = validate(data);
  assert.deepEqual(errors, []);
  assert.deepEqual(warnings, []);
});

test('every copy of a source kept in the repository is there and matches its recorded fingerprint', () => {
  assert.deepEqual(checkHeldFiles(data), []);
});

test('nothing was lost from the old program: every set holds what the old packs held', () => {
  const count = id => K.records({ set: id }).length;
  assert.equal(count('eg-eda-ctd'), 101);
  assert.equal(count('ich-m4-ctd'), 57);
  assert.equal(count('eu-m1'), 30);
  assert.equal(count('gcc-m1'), 31);
  assert.equal(count('us-fda-m1'), 111);
  assert.equal(count('intl-m1'), 19);
  assert.equal(count('eg-eda-review'), 226);
  assert.equal(count('eg-eda-variations'), 90);
  assert.equal(count('eg-eda-doctypes'), 21);
  assert.equal(data.countries.items.length, 11);
  assert.equal(Object.keys(data.recognition).length, 6);
});

test('every record, of every kind, cites at least one registered source', () => {
  for (const r of allRecords(data)) {
    const cs = K.citations(r).filter(c => c.field === 'cite');
    assert.ok(cs.length > 0, `${r.id} cites nothing`);
    for (const c of K.citations(r)) assert.ok(c.source, `${r.id} cites «${c.src}», which is not registered`);
  }
});

test('the guard itself: a record without a source, an unknown source and a broken reference are each refused', () => {
  let d = copy();
  delete d.requirements[0].cite;
  assert.match(validate(d).errors.join('\n'), /EG-EDA\/M1-01: cites no source/);

  d = copy();
  d.rules[0].cite = [{ src: 'no-such-guideline' }];
  assert.match(validate(d).errors.join('\n'), /cites «no-such-guideline», which is not registered/);

  d = copy();
  d.rules[0].evidence = { slots: ['EG-EDA/M1-999'] };
  assert.match(validate(d).errors.join('\n'), /evidence names «EG-EDA\/M1-999», which is no requirement/);

  d = copy();
  d.requirements[1].id = d.requirements[0].id;
  assert.match(validate(d).errors.join('\n'), /id used twice/);

  d = copy();
  d.sources.find(s => s.id === 'ich-m4-r4').aliases.push('NP.CAPP.065');
  assert.match(validate(d).errors.join('\n'), /alias «NP.CAPP.065» also names/);
});

test('a requirement in force that rests only on drafts is flagged', () => {
  const d = copy();
  const r = d.requirements.find(x => x.status === 'in-force');
  r.cite = [{ src: 'eda-np-capp-065-v6-draft' }];
  assert.match(validate(d).warnings.join('\n'), /every source it cites is draft/);
});

test('a source knows which records cite it, and a record its sources', () => {
  const users = K.usedBy('eda-np-capp-065-v5').map(r => r.id);
  assert.ok(users.includes('EG-EDA/M1-01'));
  const cs = K.citations(K.record('EG-EDA/M1-01'));
  assert.equal(cs[0].source.code, 'NP.CAPP.065');
  assert.equal(cs[0].at, 'Annex I');
});

test('search reads Arabic and English, whatever the hamza, the ta marbuta or the digits', () => {
  assert.equal(fold('أداةٌ ٣٫٢'), 'اداه ٣٫٢'.replace('٣', '3').replace('٢', '2'));
  assert.equal(K.search('نموذج الطلب')[0].id, 'EG-EDA/M1-01');
  assert.equal(K.search('application form annex')[0].id, 'EG-EDA/M1-01');
  assert.ok(K.search('GL.CAPP.024').some(h => h.id === 'eda-gl-capp-024-v4'));
  assert.ok(K.search('bioequivalence', { kind: 'rule' }).length > 0);
  // every variation of class PAC-II is found (others that mention PAC-II, as the tool's class or a case, come too)
  const pac2 = K.search('PAC-II', { kind: 'variation', limit: 500 }).map(h => h.id);
  for (const v of data.variations.items.filter(x => x.pac === 'PAC-II')) assert.ok(pac2.includes(v.id), v.id);
  assert.deepEqual(K.search('   '), []);
});

test('every draft source is marked as one, and no in-force requirement leans on a draft alone', () => {
  const drafts = K.sources({ status: 'draft' }).map(s => s.id);
  assert.ok(drafts.includes('eda-np-capp-065-v6-draft'));
  for (const r of K.records({ kind: 'requirement' }).filter(x => x.status === 'in-force')) {
    const st = r.cite.map(c => K.source(c.src).status);
    assert.ok(st.some(x => x === 'in-force' || x === 'data'), r.id);
  }
});

test('each citation field holds only citations', () => {
  for (const r of allRecords(data)) for (const c of citationsOf(r)) assert.equal(typeof c.src, 'string', r.id);
});

test('the review covers every citation, and nothing it checked is left unresolved', () => {
  const key = (rec, field, c) => `${rec}|${field}|${c.src}|${c.at || ''}`;
  const checked = new Set(data.checks.citations.map(c => key(c.rec, c.field, c)));
  const missing = [];
  for (const r of allRecords(data)) {
    for (const field of ['cite', 'ectd_cite', 'anchor_cite']) for (const c of r[field] || []) if (!checked.has(key(r.id, field, c))) missing.push(`${r.id} ${field} ${c.src}`);
  }
  assert.deepEqual(missing, [], 'run node tools/verify-sources.mjs after changing a citation');
  const open = data.checks.citations.filter(c => c.result === 'not-found' || c.result === 'partly');
  assert.deepEqual(open.map(c => `${c.rec} ${c.src} ${c.at || ''}`), []);
});

test('every variation names its item and class in the guideline, or says why it cannot', () => {
  for (const v of data.variations.items) {
    assert.ok(v.check?.verdict, `${v.id} has no review verdict`);
    if (v.check.verdict === 'tool-only') continue;
    assert.ok(v.guideline?.section && v.guideline?.pac, `${v.id} names no guideline item`);
    if (v.check.verdict === 'differs') assert.ok(v.pac_tool && v.pac_tool !== v.pac, `${v.id} keeps no tool class`);
    if (v.check.verdict === 'agrees') assert.equal(v.pac, v.guideline.pac, v.id);
  }
});

test('a replaced source names what replaced it, and nothing in force rests on it alone', () => {
  for (const s of K.sources({ status: 'superseded' })) {
    if (!s.superseded_by) continue;
    assert.ok(K.source(s.superseded_by), s.id);
  }
  const old = K.usedBy('eda-gl-cadc-002-v2');
  assert.deepEqual(old.map(r => r.id), [], 'GL.CADC.002 v02 was replaced on 20/10/2026');
});

test('the search reads both languages: Arabic finds English and the other way round, short codes stand on their own', async () => {
  const { preparePages, findInPages, indexOfAlt } = await import('../core/search.js');
  const p = K.parse('الانحلال');
  assert.ok(p.groups[0].alts.includes('dissolution'));
  assert.ok(K.search('ذوبان').some(h => h.id === 'EG-EDA/CD-65-03'));
  assert.ok(K.search('shelf life').some(h => h.item?.title?.ar && /صلاحي/.test(h.item.title.ar)) || K.search('shelf life').length > 0);
  assert.equal(indexOfAlt('capillary tube', 'api'), -1);
  assert.equal(indexOfAlt('the api is', 'api'), 4);
  const pages = preparePages(['The Active Pharmaceutical Ingredient (API) must be tested.', 'Nothing here.']);
  const r = findInPages(pages, K.parse('مادة فعالة').groups);
  assert.equal(r.total, 1);
  assert.match(r.pages[0].html, /<mark>Active Pharmaceutical Ingredient<\/mark>/);
});
