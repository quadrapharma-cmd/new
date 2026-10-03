import test from 'node:test';
import assert from 'node:assert/strict';
import { rankAccounts, exactAccount, rankParties, rankDocuments } from '../../src/ui/kit/rank.js';
import { buildSyntheticSeed } from '../synthetic-seed.js';

const seed = buildSyntheticSeed();
const accounts = seed.accounts;
const codes = (list) => list.map((a) => a.code);

test('accounts: exact code first, then code prefix, then names', () => {
  assert.deepEqual(codes(rankAccounts(accounts, '1340')).slice(0, 1), ['1340']);
  assert.deepEqual(codes(rankAccounts(accounts, '13')), ['1310', '1320', '1340']);
  assert.equal(rankAccounts(accounts, '١٣٤٠')[0].code, '1340', 'Arabic-Indic digits work');
  assert.equal(rankAccounts(accounts, 'خزينة').length, 2);
  assert.ok(codes(rankAccounts(accounts, 'بنك')).includes('1340'));
  assert.equal(codes(rankAccounts(accounts, 'بنك'))[0], '1340', 'البنك answers to «بنك» (definite article ignored) and beats a mid-name match');
});

test('accounts: recently used win ties and lead an empty query', () => {
  assert.deepEqual(codes(rankAccounts(accounts, '13', { recent: ['1340', '1320'] })), ['1340', '1320', '1310']);
  const empty = codes(rankAccounts(accounts, '', { recent: ['5250', '1340'] }));
  assert.deepEqual(empty.slice(0, 2), ['5250', '1340']);
  assert.ok(empty.length >= 10);
});

test('accounts: order is exact code, then recent matches, then match quality', () => {
  assert.equal(rankAccounts(accounts, '1340', { recent: ['1320'] })[0].code, '1340');
  assert.deepEqual(codes(rankAccounts(accounts, '1', { recent: ['1340'] })).slice(0, 1), ['1340']);
  const q = codes(rankAccounts(accounts, 'خزينة', { recent: ['1310'] }));
  assert.deepEqual(q.slice(0, 2), ['1310', '1320'], 'a recent account beats an equally good non-recent match');
});

test('accounts: inactive hidden unless kept or included; non-postable group rows never offered', () => {
  assert.equal(codes(rankAccounts(accounts, '5211')).length, 0);
  assert.deepEqual(codes(rankAccounts(accounts, '5211', { keepCodes: ['5211'] })), ['5211']);
  assert.deepEqual(codes(rankAccounts(accounts, '5211', { includeInactive: true })), ['5211']);
  const withGroup = { ...accounts, 9900: { code: '9900', name: 'مجموعة', postable: false, active: true } };
  assert.equal(codes(rankAccounts(withGroup, '9900')).length, 0);
});

test('accounts: exactAccount matches only a complete, selectable code', () => {
  assert.equal(exactAccount(accounts, ' 1320 ').code, '1320');
  assert.equal(exactAccount(accounts, '132'), null);
  assert.equal(exactAccount(accounts, '5211'), null);
});

test('parties: names and aliases, hamza/yaa-insensitive, merged and inactive hidden', () => {
  const parties = { ...seed.parties, p9: { id: 'p9', name: 'طرف مدموج', kind: 'other', aliases: [], mergedInto: 'p0001', active: true }, p8: { id: 'p8', name: 'طرف موقوف', kind: 'other', aliases: [], active: false } };
  const names = (q, o) => rankParties(parties, q, o).map((r) => r.party.id);
  assert.deepEqual(names('الوادي').slice(0, 1), ['p0001']);
  const alias = rankParties(parties, 'ك/ رامز')[0];
  assert.equal(alias.party.id, 'p0005');
  assert.equal(alias.via, 'ك/ رامز');
  assert.equal(rankParties(parties, 'مها')[0].party.id, 'p0002');
  assert.equal(rankParties(parties, 'مدموج').length, 0);
  assert.equal(rankParties(parties, 'موقوف').length, 0);
  assert.equal(rankParties(parties, 'موقوف', { keepIds: ['p8'] }).length, 1);
  assert.deepEqual(names('', { recent: ['p0004'] }).slice(0, 1), ['p0004']);
  assert.equal(rankParties(parties, 'ا/ مها')[0]?.party.id, 'p0002', 'alias "أ/ مها سليم" is found with a bare alef');
});

test('documents: id, ref and note search; selected ones excluded', () => {
  const ids = (q, o) => rankDocuments(seed.documents, q, o).map((d) => d.id);
  assert.deepEqual(ids('D0003'), ['D0003']);
  assert.deepEqual(ids('عقد').slice(0, 1), ['D0003']);
  assert.ok(!ids('', { excludeIds: ['D0001'] }).includes('D0001'));
  assert.deepEqual(ids('', { recent: ['D0004'] }).slice(0, 1), ['D0004']);
});
