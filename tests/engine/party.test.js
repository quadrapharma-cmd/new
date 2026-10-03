import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeName, stripTitle, suggestMerges } from '../../src/engine/party.js';

const P = (id, name, extra = {}) => ({ id, name, kind: 'other', aliases: [], active: true, mergedInto: null, lineCount: 1, ...extra });
const ids = (c) => c.members.map((m) => m.id).sort();
const find = (clusters, id) => clusters.find((c) => c.members.some((m) => m.id === id));

test('normalizeName strips titles in every spelling', () => {
  const same = ['سامي كريم', 'أ/ سامي كريم', 'د/ سامي كريم', 'د. سامي كريم', 'ك/ سامي كريم', 'م/ سامي كريم', 'الدكتور سامي كريم', 'كابتن سامي كريم', 'الأستاذ سامي كريم', 'أستاذ سامي كريم', 'المهندس سامي كريم', '  د /  سامي   كريم  '];
  for (const s of same) assert.equal(normalizeName(s), 'سامي كريم', s);
  assert.equal(normalizeName('أحمد علي'), 'احمد علي', 'a leading hamza letter is part of the name, not a title');
  assert.equal(normalizeName('د/ أ/ سامي'), 'سامي', 'stacked titles');
});

test('normalizeName unifies hamza / yaa / taa-marbuta and removes diacritics, notes and punctuation', () => {
  assert.equal(normalizeName('إيمان أحمد'), normalizeName('ايمان احمد'));
  assert.equal(normalizeName('منى'), normalizeName('مني'));
  assert.equal(normalizeName('فاطمة'), normalizeName('فاطمه'));
  assert.equal(normalizeName('مُحَمَّد'), 'محمد');
  assert.equal(normalizeName('محـــمد'), 'محمد');
  assert.equal(normalizeName('رؤوف'), normalizeName('رءوف'));
  assert.equal(normalizeName('مسؤول'), normalizeName('مسئول'));
  assert.equal(normalizeName('ك/ نادر فهمي (قيد الاستفسار)'), 'نادر فهمي');
  assert.equal(normalizeName('نادر، فهمي - الأول'), 'نادر فهمي الاول');
  assert.equal(normalizeName('عبد الله سامي'), normalizeName('عبدالله سامي'));
  assert.equal(normalizeName('عبد الرحيم'), 'عبدالرحيم');
  assert.equal(normalizeName('شركة ١٢٣'), 'شركه 123');
  assert.equal(normalizeName('ACME  Ltd.'), 'acme ltd');
  assert.equal(normalizeName(null), '');
  assert.equal(normalizeName(undefined), '');
  assert.equal(normalizeName(''), '');
  assert.equal(normalizeName('()'), '');
});

test('stripTitle reports the title kind', () => {
  assert.deepEqual(stripTitle('د/ سامي'), { title: 'dr', rest: 'سامي' });
  assert.deepEqual(stripTitle('أ/ سامي'), { title: 'ustaz', rest: 'سامي' });
  assert.deepEqual(stripTitle('ك/ سامي'), { title: 'captain', rest: 'سامي' });
  assert.deepEqual(stripTitle('كابتن سامي'), { title: 'captain', rest: 'سامي' });
  assert.deepEqual(stripTitle('سامي'), { title: null, rest: 'سامي' });
});

test('same normalised name: high confidence; titles that differ make it identity-sensitive', () => {
  const clusters = suggestMerges([
    P('p1', 'أ/ نادر فهمي', { lineCount: 5 }),
    P('p2', 'نادر فهمي', { lineCount: 9 }),
    P('p3', 'ك/ نادر فهمي (قيد الاستفسار)', { lineCount: 2 }),
  ]);
  assert.equal(clusters.length, 1);
  const c = clusters[0];
  assert.deepEqual(ids(c), ['p1', 'p2', 'p3']);
  assert.equal(c.confidence, 'high');
  assert.equal(c.identitySensitive, true, 'ustaz vs captain: possibly different people');
  assert.equal(c.safe, false);
  assert.ok(c.reasons.includes('same-normalized'));
  assert.ok(c.reasons.includes('title-conflict'));
  assert.equal(c.survivorId, 'p2', 'the most used spelling survives');
  assert.deepEqual(c.members.find((m) => m.id === 'p1').title, 'ustaz');
  assert.equal(c.members.find((m) => m.id === 'p1').normalized, 'نادر فهمي');
});

test('a title on one spelling only is not a conflict: the cluster is safe', () => {
  const [c] = suggestMerges([P('p1', 'د/ ليلى حسني'), P('p2', 'ليلى حسني'), P('p3', 'ليلي حسني')]);
  assert.deepEqual(ids(c), ['p1', 'p2', 'p3']);
  assert.equal(c.confidence, 'high');
  assert.equal(c.identitySensitive, false);
  assert.equal(c.safe, true);
});

test('organisations: generic words are ignored; hamza variants match', () => {
  const [c] = suggestMerges([P('p1', 'بنك الأفق', { kind: 'bank', lineCount: 100 }), P('p2', 'الافق', { kind: 'bank', lineCount: 3 })]);
  assert.deepEqual(ids(c), ['p1', 'p2']);
  assert.equal(c.confidence, 'high');
  assert.equal(c.safe, true);
  assert.ok(c.reasons.includes('same-without-org-words'));
  assert.equal(c.survivorId, 'p1');
  const [d] = suggestMerges([P('p3', 'شركة النور'), P('p4', 'النور')]);
  assert.equal(d.safe, true);
});

test('word order and aliases', () => {
  const [a] = suggestMerges([P('p1', 'كريم سامي نور'), P('p2', 'سامي كريم نور')]);
  assert.equal(a.confidence, 'high');
  assert.ok(a.reasons.includes('same-tokens'));
  const [b] = suggestMerges([P('p3', 'شركة الضياء', { aliases: ['الضياء للتجارة'] }), P('p4', 'الضياء للتجارة')]);
  assert.equal(b.confidence, 'high');
  assert.ok(b.reasons.includes('alias'));
});

test('containment: three-token names are medium and not sensitive; short names are sensitive', () => {
  const [c] = suggestMerges([P('p1', 'سامي كريم نور', { lineCount: 10 }), P('p2', 'سامي كريم نور حسن', { lineCount: 3 })]);
  assert.equal(c.confidence, 'medium');
  assert.equal(c.identitySensitive, false);
  assert.equal(c.safe, false, 'only high-confidence, non-sensitive clusters are safe');
  const [d] = suggestMerges([P('p3', 'سامي كريم'), P('p4', 'سامي كريم حسن')]);
  assert.equal(d.confidence, 'medium');
  assert.equal(d.identitySensitive, true, 'two-token names collide easily');
  const [e] = suggestMerges([P('p5', 'منى'), P('p6', 'منى سالم')]);
  assert.equal(e.confidence, 'low');
  assert.equal(e.identitySensitive, true, 'a lone first name never identifies a person');
});

test('different people sharing a first name stay separate clusters unless a lone first name links them (then it is flagged)', () => {
  const apart = suggestMerges([P('p1', 'منى سالم'), P('p2', 'منى خالد')]);
  assert.deepEqual(apart, []);
  const [c] = suggestMerges([P('p1', 'منى سالم'), P('p2', 'منى خالد'), P('p3', 'منى')]);
  assert.deepEqual(ids(c), ['p1', 'p2', 'p3']);
  assert.equal(c.confidence, 'low');
  assert.equal(c.identitySensitive, true);
  assert.equal(c.safe, false);
  assert.ok(c.reasons.includes('first-name-collision'));
});

test('same name but different party kinds is identity-sensitive', () => {
  const [c] = suggestMerges([P('p1', 'هاني صبري', { kind: 'employee' }), P('p2', 'هاني صبري', { kind: 'shareholder' })]);
  assert.equal(c.confidence, 'high');
  assert.equal(c.identitySensitive, true);
  assert.ok(c.reasons.includes('kind-differs'));
  assert.equal(c.safe, false);
});

test('merged and inactive parties are skipped (inactive can be included)', () => {
  const list = [P('p1', 'ليلى حسني'), P('p2', 'ليلى حسني', { mergedInto: 'p1' }), P('p3', 'ليلى حسني', { active: false })];
  assert.deepEqual(suggestMerges(list), []);
  const [c] = suggestMerges(list, { includeInactive: true });
  assert.deepEqual(ids(c), ['p1', 'p3']);
});

test('accepts an object map, never mutates the input, orders clusters by confidence', () => {
  const map = {
    p1: P('p1', 'ليلى حسني'), p2: P('p2', 'ليلى حسني'),
    p3: P('p3', 'منى'), p4: P('p4', 'منى سالم'),
    p5: P('p5', 'بنك الأفق', { kind: 'bank' }), p6: P('p6', 'الافق', { kind: 'bank' }), p7: P('p7', 'ليلى'),
  };
  const before = JSON.stringify(map);
  const clusters = suggestMerges(map);
  assert.equal(JSON.stringify(map), before);
  assert.deepEqual(clusters.map((c) => c.confidence), ['high', 'high', 'low', 'low']);
  const first = clusters[0];
  assert.ok(['p1', 'p5'].includes(first.members[0].id));
  // a single-token name links to every longer name that contains it, flagged as low confidence
  assert.deepEqual(ids(find(clusters, 'p7')), ['p1', 'p2', 'p7']);
});

test('placeholders and empty names never cluster', () => {
  assert.deepEqual(suggestMerges([P('p1', ''), P('p2', ''), P('p3', '—'), P('p4', '—')]), []);
});

test('property: normalizeName is idempotent', () => {
  const samples = ['أ/ سامي كريم', 'د. إيمان أحمد (مؤقت)', 'عبد الرحمن', 'شركة النور للتجارة', 'ACME Ltd', 'ك/ منى ١٢', '  ', 'مُحَمَّد'];
  for (const s of samples) assert.equal(normalizeName(normalizeName(s)), normalizeName(s), s);
});
