import test from 'node:test';
import assert from 'node:assert/strict';
import {
  trialBalance, incomeStatement, incomeComparative, balanceSheet, accountStatement, partyStatement, partyBalances,
  fsLineOf, yearsWithActivity,
} from '../../src/engine/statements.js';
import { buildState, entryId } from '../synthetic/build-state.js';

const state = buildState();

test('fsLineOf falls back to the class default', () => {
  assert.equal(fsLineOf({ cls: 'مجمع إهلاك' }), 'ACCUM_DEP');
  assert.equal(fsLineOf({ cls: 'حقوق ملكية', fsLine: 'RETAINED' }), 'RETAINED');
  assert.equal(fsLineOf({ cls: 'حقوق ملكية' }), 'CAPITAL');
  assert.equal(fsLineOf(null), null);
});

test('trial balance, cumulative mode: both sides equal, P&L unclosed', () => {
  const tb = trialBalance({ state, asOf: '2023-12-31' });
  assert.equal(tb.mode, 'cumulative');
  assert.equal(tb.totals.closingDr, 2492000);
  assert.equal(tb.totals.closingCr, 2492000);
  assert.equal(tb.balanced, true);
  assert.equal(tb.difference, 0);
  const r = Object.fromEntries(tb.rows.map((x) => [x.acct, x]));
  assert.equal(r['1340'].closingDr, 1372000);
  assert.equal(r['1191'].closingCr, 160000);
  assert.equal(r['3120'].closingDr, 100000, 'capital called is a debit balance in equity');
  assert.equal(r['5290'].closingDr, 190000);
  assert.equal(r['6110'].closingCr, 5000);
  // cumulative mode has no opening column values
  assert.equal(tb.totals.openingDr, 0);
  // groups follow the classification order and carry subtotals
  assert.equal(tb.groups[0].cls, 'أصول');
  assert.equal(tb.groups[tb.groups.length - 1].cls, 'وسيط');
  const totalFromGroups = tb.groups.reduce((s, g) => s + Math.round(g.subtotal.closingDr * 100), 0);
  assert.equal(totalFromGroups, 249200000);
});

test('trial balance, cumulative as of an earlier year-end', () => {
  const tb = trialBalance({ state, year: 2020 });
  assert.equal(tb.to, '2020-12-31');
  assert.equal(tb.totals.closingDr, 1340000);
  assert.equal(tb.totals.closingCr, 1340000);
});

test('trial balance, single-year mode: opening / movement / closing', () => {
  const tb = trialBalance({ state, mode: 'year', year: 2022 });
  assert.equal(tb.from, '2022-01-01');
  assert.equal(tb.to, '2022-12-31');
  const r = Object.fromEntries(tb.rows.map((x) => [x.acct, x]));
  assert.equal(r['1340'].openingDr, 807000);
  assert.equal(r['1340'].debit, 0);
  assert.equal(r['1340'].closingDr, 807000);
  assert.equal(r['5290'].openingDr, 120000);
  assert.equal(r['5290'].debit, 70000);
  assert.equal(r['5290'].closingDr, 190000);
  assert.equal(tb.totals.debit, 175000);
  assert.equal(tb.totals.credit, 175000);
  assert.equal(tb.totals.openingDr, tb.totals.openingCr);
  assert.equal(tb.totals.closingDr, tb.totals.closingCr);
  assert.equal(tb.balanced, true);
  assert.throws(() => trialBalance({ state, mode: 'year' }), TypeError);
});

test('trial balance options: includeZero lists the whole chart, hideZeroClosing drops settled accounts', () => {
  const full = trialBalance({ state, asOf: '2023-12-31', includeZero: true });
  assert.equal(full.rows.length, Object.keys(state.accounts).length);
  const hidden = trialBalance({ state, mode: 'year', year: 2020, hideZeroClosing: true });
  assert.ok(hidden.rows.every((r) => r.closing !== 0));
  const filtered = trialBalance({ state, asOf: '2023-12-31', filters: { includeFiduciary: false } });
  assert.equal(filtered.rows.some((r) => r.acct === '6110'), false);
});

test('income statement, single year', () => {
  const is = incomeStatement({ state, year: 2021 });
  assert.equal(is.from, '2021-01-01');
  assert.equal(is.revenue.gross, 300000);
  assert.equal(is.revenue.contra, 10000);
  assert.equal(is.revenue.net, 290000);
  assert.equal(is.cogs.total, 0);
  assert.equal(is.grossProfit, 290000);
  assert.equal(is.opex.total, 85000);
  assert.deepEqual(is.opex.rows.map((r) => [r.acct, r.amount]), [['5250', 25000], ['5290', 60000]]);
  assert.equal(is.nondeductible.total, 0);
  assert.equal(is.netResult, 205000);
  assert.deepEqual(is.revenue.contraRows.map((r) => [r.acct, r.amount]), [['4130', 10000]]);
  assert.deepEqual(is.unclassified, []);
});

test('income statement lists no accounts that net to zero in the period', () => {
  const s = buildState();
  const mk = (no, date, l1, l2) => ({ ...s.entries[entryId(30)], no, date, lines: [l1, l2].map((l, i) => ({ ...s.entries[entryId(30)].lines[0], n: i + 1, ...l })) });
  s.entries.e000041 = mk(41, '2023-05-01', { acct: '5330', dr: 100, cr: 0 }, { acct: '1320', dr: 0, cr: 100 });
  s.entries.e000042 = mk(42, '2023-05-02', { acct: '1320', dr: 100, cr: 0 }, { acct: '5330', dr: 0, cr: 100 });
  const is = incomeStatement({ state: s, year: 2023 });
  assert.deepEqual(is.nondeductible.rows, []);
  assert.equal(is.nondeductible.total, 0);
  assert.equal(is.netResult, 448000);
});

test('income statement ignores balance-sheet accounts and the suspense account', () => {
  const is = incomeStatement({ state, from: '2021-05-01', to: '2021-05-31' });
  assert.equal(is.netResult, 0);
  assert.equal(is.revenue.gross, 0);
});

test('income comparative over years with change %', () => {
  const c = incomeComparative({ state });
  assert.deepEqual(c.years, [2020, 2021, 2022, 2023]);
  assert.deepEqual(c.totals.netResult.byYear, { 2020: 30000, 2021: 205000, 2022: -70000, 2023: 448000 });
  assert.equal(c.totals.netResult.changePct[2020], null);
  assert.equal(c.totals.netResult.changePct[2021], 583.33);
  assert.equal(c.totals.revenueNet.byYear[2021], 290000);
  const row4110 = c.accounts.find((a) => a.acct === '4110');
  assert.deepEqual(row4110.byYear, { 2020: 200000, 2021: 300000, 2022: 0, 2023: 500000 });
  const total = Object.values(c.totals.netResult.byYear).reduce((a, b) => a + b, 0);
  assert.equal(total, 613000);
  const two = incomeComparative({ state, years: [2023, 2022] });
  assert.deepEqual(two.years, [2022, 2023]);
  assert.deepEqual(yearsWithActivity(state), [2020, 2021, 2022, 2023]);
});

test('balance sheet at a year-end: derived retained earnings, contras, suspense, explicit check', () => {
  const bs = balanceSheet({ state, asOf: '2023-12-31' });
  assert.equal(bs.year, 2023);
  assert.equal(bs.assets.gross, 2005000);
  assert.equal(bs.assets.accumDep, 190000);
  assert.equal(bs.assets.net, 1815000);
  assert.deepEqual(bs.assets.accumDepRows.map((r) => [r.acct, r.amount]), [['1191', 160000], ['1192', 30000]]);
  assert.equal(bs.liabilities.total, 197000);
  assert.equal(bs.suspense.total, 5000);
  assert.equal(bs.equity.capital.total, 1100000);
  assert.equal(bs.equity.capitalCalled.total, -100000);
  assert.equal(bs.equity.priorResults, 165000);
  assert.equal(bs.equity.retained, 165000);
  assert.equal(bs.equity.currentResult, 448000);
  assert.equal(bs.equity.total, 1613000);
  assert.deepEqual(bs.check, { assets: 1815000, liabilities: 197000, suspense: 5000, equity: 1613000, difference: 0, balanced: true });
  assert.ok(bs.warnings.some((w) => w.code === 'suspense-nonzero'));
  assert.equal(bs.wrongSide.length, 0);
});

test('balance sheet at a mid-year date and at the first date', () => {
  const mid = balanceSheet({ state, asOf: '2022-06-30' });
  assert.equal(mid.equity.priorResults, 235000);
  assert.equal(mid.equity.currentResult, 0);
  assert.equal(mid.check.difference, 0);
  const first = balanceSheet({ state, asOf: '2020-01-10' });
  assert.equal(first.assets.net, 1000000);
  assert.equal(first.equity.total, 1000000);
  assert.equal(first.check.balanced, true);
  const before = balanceSheet({ state, asOf: '2019-12-31' });
  assert.equal(before.assets.net, 0);
  assert.equal(before.check.balanced, true);
  assert.throws(() => balanceSheet({ state, asOf: 'x' }), TypeError);
});

test('balance sheet: retained-earnings accounts add to the derived part; wrong-side balances are kept and flagged', () => {
  const s = buildState();
  s.entries[entryId(40)] = {
    ...s.entries[entryId(30)], no: 40, date: '2023-12-01', desc: 'رصيد مرحل',
    lines: [
      { n: 1, acct: '3150', dr: 0, cr: 7000, memo: '', partyId: null, docIds: [], cc: null, sector: null, valueDate: null, needsReview: false, reviewReason: '', links: [], legacy: null },
      { n: 2, acct: '1320', dr: 7000, cr: 0, memo: '', partyId: null, docIds: [], cc: null, sector: null, valueDate: null, needsReview: false, reviewReason: '', links: [], legacy: null },
    ],
  };
  const bs = balanceSheet({ state: s, asOf: '2023-12-31' });
  assert.equal(bs.equity.retainedAccounts.total, 7000);
  assert.equal(bs.equity.retained, 172000);
  assert.equal(bs.check.balanced, true);
  // push the cash account to a credit balance
  s.entries[entryId(41)] = {
    ...s.entries[entryId(30)], no: 41, date: '2023-12-02', desc: 'سحب زائد',
    lines: [
      { n: 1, acct: '1320', dr: 0, cr: 90000, memo: '', partyId: null, docIds: [], cc: null, sector: null, valueDate: null, needsReview: false, reviewReason: '', links: [], legacy: null },
      { n: 2, acct: '2160', dr: 90000, cr: 0, memo: '', partyId: 'p0003', docIds: [], cc: null, sector: null, valueDate: null, needsReview: false, reviewReason: '', links: [], legacy: null },
    ],
  };
  const bs2 = balanceSheet({ state: s, asOf: '2023-12-31' });
  assert.equal(bs2.check.balanced, true, 'wrong-side balances are never dropped');
  assert.deepEqual(bs2.wrongSide.map((w) => w.acct).sort(), ['1320', '2160']);
});

test('balance sheet exposes unclassified accounts through the check difference', () => {
  const s = buildState();
  s.accounts['1340'].cls = 'غير معروف';
  s.accounts['1340'].fsLine = null;
  const bs = balanceSheet({ state: s, asOf: '2023-12-31' });
  assert.equal(bs.check.balanced, false);
  assert.equal(bs.check.difference, -1372000);
  assert.equal(bs.unclassified.length, 1);
  assert.equal(bs.unclassified[0].acct, '1340');
  assert.ok(bs.warnings.some((w) => w.code === 'unclassified'));
});

test('account statement: opening carried, running balance, void excluded', () => {
  const st = accountStatement({ state, acct: '1340', year: 2023 });
  assert.equal(st.opening, 807000);
  assert.deepEqual(st.rows.map((r) => [r.no, r.dr, r.cr, r.balance]), [
    [30, 500000, 0, 1307000],
    [32, 0, 25000, 1282000],
    [33, 90000, 0, 1372000],
  ]);
  assert.equal(st.closing, 1372000);
  assert.equal(st.totalDr, 590000);
  assert.equal(st.totalCr, 25000);
  assert.equal(st.normal, 'D');
  const none = accountStatement({ state, acct: '1340', year: 2022 });
  assert.equal(none.rows.length, 0);
  assert.equal(none.opening, 807000);
  assert.equal(none.closing, 807000);
});

test('account statement of a credit-normal account reads in its natural direction', () => {
  const st = accountStatement({ state, acct: '2322', year: 2023 });
  assert.equal(st.opening, -30000);
  assert.equal(st.openingNatural, 30000);
  assert.deepEqual(st.rows.map((r) => r.balanceNatural), [70000, 45000]);
  assert.equal(st.closingNatural, 45000);
  const contra = accountStatement({ state, acct: '1191', from: '2021-01-01', to: '2021-12-31' });
  assert.equal(contra.normal, 'C');
  assert.equal(contra.closingNatural, 120000);
  const missing = accountStatement({ state, acct: '9999', year: 2023 });
  assert.equal(missing.rows.length, 0);
});

test('party statement by line party and by account binding', () => {
  const byLine = partyStatement({ state, partyId: 'p0004' });
  assert.deepEqual(byLine.rows.map((r) => [r.no, r.acct, r.balance]), [
    [4, '2322', -30000], [16, '1250', -25000], [31, '2322', -65000], [32, '2322', -40000],
  ]);
  assert.equal(byLine.closing, -40000);
  assert.deepEqual(byLine.byAccount.map((a) => [a.acct, a.closing]), [['1250', 5000], ['2322', -45000]]);
  const yr = partyStatement({ state, partyId: 'p0004', year: 2023 });
  assert.equal(yr.opening, -25000);
  assert.equal(yr.rows.length, 2);
  const bound = partyStatement({ state, partyId: 'p0004', mode: 'account' });
  assert.deepEqual(bound.accounts, ['2322']);
  assert.equal(bound.closing, -45000);
  const unbound = partyStatement({ state, partyId: 'p0005', mode: 'account' });
  assert.deepEqual(unbound.rows, [], 'a party with no bound account has no account-bound lines');
  assert.equal(unbound.closing, 0);
  const viaMerged = partyStatement({ state, partyId: 'p0006' });
  assert.equal(viaMerged.partyId, 'p0003');
  assert.equal(viaMerged.closing, -12000);
});

test('party balances: parties + unassigned equal the account balance; account-bound totals', () => {
  const pb = partyBalances({ state, asOf: '2023-12-31' });
  assert.ok(pb.accounts.every((a) => a.ok));
  const a2322 = pb.accounts.find((a) => a.acct === '2322');
  assert.equal(a2322.total, 45000);
  assert.equal(a2322.parties[0].balance, 45000);
  assert.equal(a2322.unassigned, 0);
  const a1340 = pb.accounts.find((a) => a.acct === '1340');
  assert.equal(a1340.total, 1372000);
  assert.equal(a1340.parties.find((p) => p.partyId === 'p0005').signed, 65000);
  assert.equal(a1340.unassigned, 1307000);
  const a2310 = pb.accounts.find((a) => a.acct === '2310');
  assert.equal(a2310.total, 140000);
  const boundBy = Object.fromEntries(pb.bound.map((b) => [b.partyId, b.balance]));
  assert.equal(boundBy.p0002, 140000);
  assert.equal(boundBy.p0004, 45000);
  assert.equal(boundBy.p0003, 12000);
  assert.equal(boundBy.p0001, 0);
  assert.equal(boundBy.p0006, undefined, 'merged parties are not listed');
  const p4 = pb.parties.find((p) => p.partyId === 'p0004');
  assert.equal(p4.total, -40000);
  const early = partyBalances({ state, asOf: '2020-12-31', accounts: ['2310'] });
  assert.equal(early.accounts.length, 1);
  assert.equal(early.accounts[0].total, 50000);
});

test('boundAccounts overrides defaultAccount for the account-bound view', () => {
  const s = buildState();
  s.parties.p0002.boundAccounts = ['2310', '2311'];
  const pb = partyBalances({ state: s, asOf: '2023-12-31' });
  const b = pb.bound.find((x) => x.partyId === 'p0002');
  assert.deepEqual(b.accounts, ['2310', '2311']);
  assert.equal(b.balance, 140000);
});
