import test from 'node:test';
import assert from 'node:assert/strict';
import { checkIntegrity, summarizeIntegrity } from '../../src/engine/integrity.js';
import { buildState, makeEntry, entryId, DRAFT_ID, NOW } from '../synthetic/build-state.js';

const OPTS = { now: NOW };
const check = (s) => checkIntegrity(s, OPTS);
const codes = (list) => list.map((f) => f.code);
const has = (list, code, severity) => list.some((f) => f.code === code && (!severity || f.severity === severity));
const find = (list, code) => list.find((f) => f.code === code);
const L = (...a) => a;

test('the synthetic state has no errors; only the expected warnings', () => {
  const list = check(buildState());
  assert.deepEqual(list.filter((f) => f.severity === 'error'), []);
  assert.deepEqual(codes(list), ['draft-stale', 'suspense-nonzero']);
  assert.equal(find(list, 'draft-stale').where, `entries/${DRAFT_ID}`);
  const sum = summarizeIntegrity(list);
  assert.deepEqual(sum, { error: 0, warn: 2, info: 0, total: 2, ok: true });
});

test('findings carry severity, code, an Arabic message and a where path; errors sort first', () => {
  const s = buildState();
  s.entries[entryId(30)].lines[0].dr = 1;
  const list = check(s);
  for (const f of list) {
    assert.ok(['error', 'warn', 'info'].includes(f.severity));
    assert.equal(typeof f.code, 'string');
    assert.ok(f.msg.length > 0);
    assert.equal(typeof f.where, 'string');
  }
  const sev = list.map((f) => f.severity);
  assert.deepEqual(sev, [...sev].sort((a, b) => ['error', 'warn', 'info'].indexOf(a) - ['error', 'warn', 'info'].indexOf(b)));
  assert.equal(summarizeIntegrity(list).ok, false);
});

test('posted entries must balance and have at least two lines', () => {
  const s = buildState();
  s.entries[entryId(30)].lines[0].dr = 499999;
  const list = check(s);
  const f = find(list, 'entry-unbalanced');
  assert.equal(f.severity, 'error');
  assert.equal(f.where, `entries/${entryId(30)}`);
  assert.match(f.msg, /1\.00/);
  assert.ok(has(list, 'tb-unbalanced', 'error'));
  assert.ok(has(list, 'bs-unbalanced', 'error'));
  const s2 = buildState();
  s2.entries[entryId(30)].lines = [s2.entries[entryId(30)].lines[0]];
  assert.ok(has(check(s2), 'entry-few-lines', 'error'));
  // drafts and void entries may be unbalanced
  const s3 = buildState();
  s3.entries[entryId(35)].lines[0].dr = 1;
  s3.entries[DRAFT_ID].lines[0].dr = 77;
  assert.equal(has(check(s3), 'entry-unbalanced'), false);
});

test('entry numbers: unique, present on booked entries, matching the doc id; counter ahead of the maximum', () => {
  const s = buildState();
  s.entries.e000099 = { ...s.entries[entryId(30)], no: 30 };
  const list = check(s);
  assert.ok(has(list, 'entry-no-duplicate', 'error'));
  assert.ok(has(list, 'entry-id-mismatch', 'warn'));
  assert.equal(has(list, 'counter-behind'), false);
  const s2 = buildState();
  s2.entries[entryId(31)].no = null;
  assert.ok(has(check(s2), 'entry-no-missing', 'error'));
  const s3 = buildState();
  s3.counters.nextEntryNo = 35;
  const f = find(check(s3), 'counter-behind');
  assert.equal(f.severity, 'error');
  assert.equal(f.where, 'meta/counters');
  s3.counters = {};
  assert.ok(has(check(s3), 'counter-invalid', 'error'));
  const s4 = buildState();
  s4.entries[DRAFT_ID].no = 5;
  assert.ok(has(check(s4), 'entry-no-on-draft'));
});

test('line checks: unknown / non-postable accounts, bad amounts', () => {
  const s = buildState();
  s.entries[entryId(30)].lines[0].acct = '9999';
  s.entries[entryId(31)].lines[0].acct = '1000';
  s.entries[entryId(32)].lines[0].dr = 25000.005;
  s.entries[entryId(33)].lines[0].cr = 5;
  s.entries[entryId(34)].lines[0].dr = -12000;
  const list = check(s);
  assert.ok(has(list, 'line-unknown-account', 'error'));
  assert.ok(has(list, 'line-nonpostable-account', 'error'));
  assert.equal(list.filter((f) => f.code === 'line-bad-amount').length, 3);
  assert.equal(find(list, 'line-unknown-account').where, `entries/${entryId(30)}#1`);
  const s2 = buildState();
  s2.accounts['4110'].active = false;
  assert.ok(has(check(s2), 'line-inactive-account', 'info'));
});

test('references: orphan party / document / cost center / sector / register link, merged party not re-pointed', () => {
  const s = buildState();
  const e = s.entries[entryId(31)];
  e.lines[1].partyId = 'p9999';
  e.lines[0].docIds = ['D9999'];
  e.docIds = ['D9998'];
  e.cc = 'ccX';
  e.sector = 'secX';
  e.lines[0].cc = 'ccY';
  e.lines[0].sector = 'secY';
  e.lines[0].links = [{ t: 'a', n: 404 }, { t: 'o', n: 405 }];
  s.entries[entryId(34)].lines[1].partyId = 'p0006';
  const list = check(s);
  for (const c of ['orphan-party', 'orphan-doc', 'orphan-cc', 'orphan-sector', 'orphan-link', 'party-merged-not-repointed']) assert.ok(has(list, c, 'warn'), c);
  assert.equal(list.filter((f) => f.code === 'orphan-link').length, 2);
});

test('dates, fiscal year field, void reasons, reversal links, versions vs history', () => {
  const s = buildState();
  s.entries[entryId(30)].date = 'bad';
  s.entries[entryId(31)].fy = 1999;
  s.entries[entryId(35)].voidReason = null;
  s.entries[entryId(32)].reversalOf = 'e999999';
  s.entries[entryId(33)].version = 4;
  const list = check(s);
  for (const c of ['entry-bad-date', 'entry-fy-mismatch', 'void-no-reason', 'reversal-orphan', 'version-history-mismatch']) assert.ok(has(list, c), c);
  assert.equal(find(list, 'entry-bad-date').severity, 'error');
});

test('stale drafts are reported after 7 days only', () => {
  const s = buildState();
  s.entries[DRAFT_ID].createdAt = '2024-02-28T00:00:00.000Z';
  assert.equal(has(check(s), 'draft-stale'), false);
  s.entries[DRAFT_ID].createdAt = '2024-02-20T00:00:00.000Z';
  assert.equal(has(check(s), 'draft-stale'), true);
});

test('locked years: any change since the snapshot is an error', () => {
  const s = buildState();
  s.entries[entryId(1)].lines[0].dr = 1100000;
  s.entries[entryId(1)].lines[1].cr = 1100000;
  const list = check(s);
  const f = find(list, 'locked-year-changed');
  assert.equal(f.severity, 'error');
  assert.equal(f.where, 'fiscalYears/2020');
  assert.equal(has(list, 'tb-unbalanced'), false, 'the books still balance: only the lock is violated');
  // an edit recorded after the snapshot is flagged on the entry too
  s.entries[entryId(2)].history = [{ v: 2, at: '2021-06-01T00:00:00.000Z', by: 'x', kind: 'amend', reason: 'x', before: {} }];
  s.entries[entryId(2)].version = 2;
  assert.ok(has(check(s), 'locked-year-entry-edited', 'error'));
  const s2 = buildState();
  s2.fiscalYears[2020].snapshot = null;
  assert.ok(has(check(s2), 'locked-no-snapshot', 'error'));
  const s3 = buildState();
  s3.fiscalYears[2023].state = 'weird';
  assert.ok(has(check(s3), 'year-state-invalid', 'error'));
});

test('a locked year whose revision moved since the lock snapshot is an error', () => {
  const s = buildState();
  s.fiscalYears[2020].snapshot.revision = 0;
  assert.equal(has(check(s), 'locked-year-revision-changed'), false);
  s.fiscalYears[2020].revision = 3;
  assert.ok(has(check(s), 'locked-year-revision-changed', 'error'));
});

test('closed (reserved) years: differences from the snapshot and changes since close are informational', () => {
  const s = buildState();
  s.entries[entryId(10)].lines[0].dr = 310000;
  s.entries[entryId(10)].lines[1].cr = 310000;
  s.entries[entryId(10)].history = [{ v: 2, at: '2022-03-01T00:00:00.000Z', by: 'x', kind: 'amend', reason: 'x', before: {} }];
  s.entries[entryId(10)].version = 2;
  const list = check(s);
  assert.ok(has(list, 'closed-year-differs-from-snapshot', 'info'));
  assert.ok(has(list, 'closed-year-changes', 'info'));
  assert.deepEqual(list.filter((f) => f.severity === 'error'), []);
});

test('accounts: everUsed consistency, class / type consistency, fsLine, contra links', () => {
  const s = buildState();
  s.accounts['1340'].everUsed = false;
  s.accounts['1310'].everUsed = true;
  s.accounts['4110'].type = 'expense';
  s.accounts['4130'].fsLine = 'NOPE';
  s.accounts['1191'].contraOf = '7777';
  s.accounts['5250'].cls = 'تصنيف مجهول';
  s.accounts['2110'].partyRule = 'always';
  const list = check(s);
  assert.ok(has(list, 'account-everused-false', 'warn'));
  assert.ok(has(list, 'account-everused-unused', 'info'));
  assert.ok(has(list, 'account-class-mismatch', 'warn'));
  assert.ok(has(list, 'account-fsline-invalid', 'error'));
  assert.ok(has(list, 'account-contraof-missing', 'warn'));
  assert.ok(has(list, 'account-class-unknown', 'warn'));
  assert.ok(has(list, 'account-partyrule-invalid', 'warn'));
});

test('suspense and unclassified balances', () => {
  const s = buildState();
  const list = check(s);
  assert.ok(has(list, 'suspense-nonzero', 'warn'));
  const s3 = buildState();
  s3.accounts['1340'].cls = 'x';
  s3.accounts['1340'].fsLine = null;
  const un = check(s3);
  assert.ok(has(un, 'account-unclassified', 'warn'));
  assert.ok(has(un, 'bs-unbalanced', 'error'));
});

test('wrong-side balances are listed as information', () => {
  const s = buildState();
  s.entries[entryId(40)] = makeEntry({ no: 40, date: '2023-12-01', lines: [L('1320', 0, 90000), L('2160', 90000, 0, { partyId: 'p0003' })] });
  s.counters.nextEntryNo = 41;
  s.accounts['2160'].everUsed = true;
  const list = check(s);
  const wrong = list.filter((f) => f.code === 'wrong-side-balance');
  assert.deepEqual(wrong.map((f) => f.where).sort(), ['accounts/1320', 'accounts/2160']);
  assert.equal(wrong[0].severity, 'info');
});

test('identical posted entries are listed as possible duplicates, never merged', () => {
  const s = buildState();
  s.entries[entryId(36)] = JSON.parse(JSON.stringify(s.entries[entryId(30)]));
  s.entries[entryId(36)].no = 36;
  s.counters.nextEntryNo = 37;
  const list = check(s);
  const f = find(list, 'possible-duplicate');
  assert.equal(f.severity, 'warn');
  assert.equal(f.where, `entries/${entryId(30)},entries/${entryId(36)}`);
  assert.match(f.msg, /30/);
  assert.match(f.msg, /36/);
  assert.equal(list.filter((x) => x.code === 'possible-duplicate').length, 1);
  assert.deepEqual(list.filter((x) => x.severity === 'error'), []);
});

test('assets, depreciation runs, registers, templates and parties', () => {
  const s = buildState();
  s.assets = { a1: { id: 'a1', name: 'أصل', acct: '9999', accumAcct: '8888', expenseAcct: '7777', cost: 1, inServiceDate: '', convention: 'weird' } };
  s.depRuns = { 2022: { year: 2022, status: 'posted', lines: [], postedEntryNo: 777 } };
  s.openItems = { 1: { n: 1, status: 'weird', linkedEntries: [999] } };
  s.assumptions = { 1: { n: 1, status: 'weird', linkedEntries: [998] } };
  s.templates = { t1: { id: 't1', rule: 'nope' } };
  s.parties.p0001.mergedInto = 'p7777';
  s.parties.p0002.defaultAccount = '9999';
  s.parties.p0003.kind = 'alien';
  s.costCenters.cc1.kind = 'weird';
  const list = check(s);
  for (const c of ['asset-account-missing', 'asset-convention-invalid', 'asset-no-date', 'deprun-entry-missing', 'open-item-bad-status', 'assumption-bad-status', 'linked-entry-missing', 'template-rule-unknown', 'party-merge-broken', 'party-default-account-missing', 'party-kind-invalid', 'cost-center-kind-invalid']) {
    assert.ok(has(list, c, 'warn'), c);
  }
  assert.equal(list.filter((f) => f.code === 'asset-account-missing').length, 3);
  const ok = buildState();
  ok.depRuns = { 2022: { year: 2022, status: 'posted', lines: [], postedEntryNo: 18 } };
  assert.equal(has(check(ok), 'deprun-entry-missing'), false);
});

test('an empty state is clean and does not throw', () => {
  assert.deepEqual(checkIntegrity({}).filter((f) => f.severity === 'error').map((f) => f.code), ['counter-invalid']);
  assert.deepEqual(checkIntegrity({ counters: { nextEntryNo: 1 } }), []);
});

test('checkIntegrity does not mutate the state', () => {
  const s = buildState();
  const before = JSON.stringify(s);
  check(s);
  assert.equal(JSON.stringify(s), before);
});
