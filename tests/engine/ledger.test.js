import test from 'node:test';
import assert from 'node:assert/strict';
import { postedLines, balances, normalizeFilters, accountBalanceCents } from '../../src/engine/ledger.js';
import { buildState, DRAFT_ID, entryId } from '../synthetic/build-state.js';

const state = buildState();

test('postedLines: posted only, void and drafts excluded, sorted by date then number', () => {
  const lines = postedLines(state);
  assert.equal(lines.some((l) => l.status !== 'posted'), false);
  assert.equal(lines.some((l) => l.entryId === entryId(35)), false, 'void excluded');
  assert.equal(lines.some((l) => l.entryId === DRAFT_ID), false, 'draft excluded');
  for (let i = 1; i < lines.length; i++) {
    const a = lines[i - 1];
    const b = lines[i];
    assert.ok(a.date < b.date || (a.date === b.date && a.no <= b.no), `order at ${i}`);
  }
  // entry 9 is dated 2021-06-06 but numbered before entry 10 (2021-01-15): date wins for ordering
  const idx9 = lines.findIndex((l) => l.no === 9);
  const idx10 = lines.findIndex((l) => l.no === 10);
  assert.ok(idx10 < idx9);
  const withDrafts = postedLines(state, { includeDrafts: true });
  assert.ok(withDrafts.some((l) => l.entryId === DRAFT_ID));
  assert.equal(withDrafts.some((l) => l.entryId === entryId(35)), false);
});

test('postedLines: effective dimensions come from the line, else the entry header', () => {
  const s = buildState();
  const e = s.entries[entryId(30)];
  e.lines[0].cc = 'cc3';
  e.lines[1].docIds = ['D0002'];
  const lines = postedLines(s).filter((l) => l.no === 30);
  assert.equal(lines[0].cc, 'cc3');
  assert.equal(lines[1].cc, 'cc1');
  assert.deepEqual(lines[0].docIds, ['D0001']);
  assert.deepEqual(lines[1].docIds, ['D0002']);
  assert.equal(lines[0].sector, 'sec1');
});

test('balances: opening / movement / closing and totals', () => {
  const b = balances({ state, from: '2022-01-01', to: '2022-12-31' });
  const r1340 = b.byAcct['1340'];
  assert.equal(r1340.opening, 807000);
  assert.equal(r1340.debit, 0);
  assert.equal(r1340.closing, 807000);
  const r5290 = b.byAcct['5290'];
  assert.equal(r5290.opening, 120000, 'P&L accounts carry all prior years (no closing entries)');
  assert.equal(r5290.debit, 70000);
  assert.equal(r5290.closing, 190000);
  assert.equal(b.byAcct['1191'].closing, -160000);
  assert.equal(b.byAcct['1191'].closingCr, 160000);
  assert.equal(b.byAcct['1191'].closingDr, 0);
  assert.equal(b.totals.closing, 0);
  assert.equal(b.totals.closingDr, b.totals.closingCr);
  assert.equal(b.totals.debit, 175000);
  assert.equal(b.totals.credit, 175000);
  // rows sorted by account code
  const codes = b.rows.map((r) => r.acct);
  assert.deepEqual(codes, [...codes].sort());
  // closing = opening + movement
  for (const r of b.rows) assert.equal(Math.round(r.closing * 100), Math.round((r.opening + r.movement) * 100));
});

test('balances: from = null means inception, to = null means no upper bound', () => {
  const all = balances({ state });
  assert.equal(all.byAcct['1340'].closing, 1372000);
  assert.equal(all.byAcct['1340'].opening, 0);
  assert.equal(all.totals.debit, all.totals.credit);
  const upTo2020 = balances({ state, to: '2020-12-31' });
  assert.equal(upTo2020.byAcct['1340'].closing, 520000);
  const onlyLast = balances({ state, from: '2023-01-01' });
  assert.equal(onlyLast.byAcct['1340'].opening, 807000);
});

test('balances: filters (cost center, sector, party, accounts, fiduciary)', () => {
  const all = balances({ state });
  assert.equal(all.byAcct['6110'].closing, -5000);
  const noTrust = balances({ state, filters: { includeFiduciary: false } });
  assert.equal(noTrust.byAcct['6110'], undefined);
  assert.equal(noTrust.byAcct['1340'].closing, 1367000);
  const cc2 = balances({ state, filters: { costCenter: 'cc2' } });
  assert.deepEqual(cc2.rows.map((r) => r.acct).sort(), ['1320', '1340', '4110', '5130', '5250'].sort());
  assert.equal(cc2.byAcct['1340'].closing, 120000);
  const cc12 = balances({ state, filters: { costCenters: ['cc2', 'cc3'] } });
  assert.equal(cc12.byAcct['6110'].closing, -5000);
  const sec = balances({ state, filters: { sector: 'sec2' } });
  assert.equal(sec.rows.length, 0);
  const p4 = balances({ state, filters: { party: 'p0004' } });
  assert.equal(p4.byAcct['2322'].closing, -45000);
  assert.equal(p4.byAcct['1250'].closing, 5000);
  // a merged party filter resolves to the survivor
  const viaMerged = balances({ state, filters: { party: 'p0006' } });
  const viaSurvivor = balances({ state, filters: { party: 'p0003' } });
  assert.deepEqual(viaMerged.byAcct, viaSurvivor.byAcct);
  assert.equal(viaSurvivor.byAcct['2110'].closing, -12000);
  const acct = balances({ state, filters: { accounts: ['1320', '1340'] } });
  assert.deepEqual(acct.rows.map((r) => r.acct), ['1320', '1340']);
  const nf = normalizeFilters(state, {});
  assert.equal(nf.includeFiduciary, true);
  assert.equal(nf.cc, null);
});

test('balances: drafts only with includeDrafts', () => {
  assert.equal(balances({ state }).byAcct['1340'].closing, 1372000);
  assert.equal(balances({ state, includeDrafts: true }).byAcct['1340'].closing, 1373500);
});

test('accountBalanceCents', () => {
  assert.equal(accountBalanceCents(state, '1340', { to: '2020-12-31' }), 52000000);
  assert.equal(accountBalanceCents(state, '2310'), -14000000);
  assert.equal(accountBalanceCents(state, '9999'), 0);
});

test('unknown accounts still appear in balances (never silently dropped)', () => {
  const s = buildState();
  s.entries[entryId(30)].lines[0].acct = '9999';
  const b = balances({ state: s });
  assert.equal(b.byAcct['9999'].known, false);
  assert.equal(b.totals.closing, 0);
});
