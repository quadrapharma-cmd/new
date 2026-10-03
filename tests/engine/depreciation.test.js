import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeAssetCharge, accumulatedBeforeC, proposeRun, planProposeRun, planPostDepreciation, rollForward, normalizeRate,
} from '../../src/engine/depreciation.js';
import { trialBalance } from '../../src/engine/statements.js';
import { toCents } from '../../src/lib/money.js';
import { buildState, makeEntry, entryId, NOW, USER } from '../synthetic/build-state.js';
import { applyPlan } from '../synthetic/apply-plan.js';
import { makeRng } from '../synthetic/rng.js';

const asset = (over = {}) => ({
  id: 'a1', name: 'أصل تجريبي', acct: '1130', accumAcct: '1191', expenseAcct: '5290', cost: 100000, inServiceDate: '2021-03-01',
  rate: 0.1, convention: 'half_year', residual: 0, sourceEntryNo: null, active: true, notes: '', ...over,
});
const charge = (a, y, o) => computeAssetCharge(a, y, o).charge;

test('half_year: half in the first year, full afterwards (ROUND_HALF_UP on the exact product)', () => {
  const a = asset({ cost: 48000, rate: 0.1 });
  assert.equal(charge(a, 2021), 2400);
  assert.equal(charge(a, 2022), 4800);
  assert.equal(charge(a, 2020), 0, 'before the in-service year');
  // half-cent products round up: 822,153 x 5% / 2 = 20,553.825 -> .83 ; 82,175 x 25% / 2 = 10,271.875 -> .88
  assert.equal(charge(asset({ cost: 822153, rate: 0.05 }), 2021), 20553.83);
  assert.equal(charge(asset({ cost: 82175, rate: 0.25 }), 2021), 10271.88);
  assert.equal(charge(asset({ cost: 822153, rate: 0.05 }), 2022), 41107.65);
});

test('day_count: cost x rate x days/365, days inclusive from the in-service date to 31 Dec', () => {
  const a = asset({ cost: 3200, rate: 0.2, convention: 'day_count', inServiceDate: '2023-01-11' });
  const c = computeAssetCharge(a, 2023);
  assert.equal(c.charge, 622.47, '3,200 x 20% x 355/365');
  assert.equal(c.basis, 'day_count:355/365');
  assert.equal(charge(a, 2024), 640);
  // first day of the year: 365/365 days is the full year; leap years never exceed a full year
  assert.equal(charge(asset({ cost: 36500, rate: 0.1, convention: 'day_count', inServiceDate: '2024-01-01' }), 2024), 3650);
  assert.equal(charge(asset({ cost: 1000, rate: 0.1, convention: 'day_count', inServiceDate: '2023-12-31' }), 2023), 0.27, '1/365 of 100.00 -> 0.2739 -> 0.27');
  assert.equal(charge(asset({ cost: 50000, rate: 0.2, convention: 'day_count', inServiceDate: '2022-07-01' }), 2022), 5041.1);
});

test('full_next_year and full_year', () => {
  const next = asset({ cost: 9000, rate: 0.2, convention: 'full_next_year', inServiceDate: '2021-12-31' });
  assert.equal(charge(next, 2021), 0);
  assert.equal(charge(next, 2022), 1800);
  assert.equal(charge(next, 2023), 1800);
  const full = asset({ cost: 9000, rate: 0.2, convention: 'full_year', inServiceDate: '2021-12-31' });
  assert.equal(charge(full, 2021), 1800);
});

test('none (land / work in progress), zero rate, inactive, not in service, disposed', () => {
  assert.equal(charge(asset({ convention: 'none' }), 2023), 0);
  assert.equal(charge(asset({ rate: 0 }), 2023), 0);
  assert.equal(charge(asset({ active: false }), 2023), 0);
  assert.equal(charge(asset({ cost: 0 }), 2023), 0);
  assert.equal(charge(asset({ inServiceDate: '2025-01-01' }), 2023), 0);
  assert.equal(charge(asset({ inServiceDate: '' }), 2023), 0);
  const d = asset({ convention: 'full_year', disposalDate: '2022-06-30' });
  assert.equal(charge(d, 2021), 10000);
  assert.equal(charge(d, 2022), 10000, 'the disposal year is charged by the convention');
  assert.equal(charge(d, 2023), 0);
});

test('rate: fractions and percent notation are equivalent', () => {
  assert.equal(normalizeRate(0.2), 0.2);
  assert.equal(normalizeRate(20), 0.2);
  assert.equal(normalizeRate(7.5), 0.075);
  assert.equal(normalizeRate(1), 1);
  assert.equal(normalizeRate(0), 0);
  assert.equal(normalizeRate('x'), 0);
  assert.equal(charge(asset({ cost: 48000, rate: 10 }), 2021), 2400);
});

test('the charge never exceeds cost less residual (cap), then stops', () => {
  const a = asset({ cost: 5600, rate: 0.2, convention: 'half_year', inServiceDate: '2019-07-02' });
  const seq = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026].map((y) => charge(a, y));
  assert.deepEqual(seq, [560, 1120, 1120, 1120, 1120, 560, 0, 0]);
  assert.equal(computeAssetCharge(a, 2024).capped, true);
  assert.equal(computeAssetCharge(a, 2024).basis, 'capped');
  assert.equal(computeAssetCharge(a, 2024).accumAfter, 5600);
  assert.equal(computeAssetCharge(a, 2024).remaining, 0);
  const res = asset({ cost: 10000, residual: 1000, rate: 0.5, convention: 'full_year', inServiceDate: '2020-01-01' });
  assert.deepEqual([2020, 2021, 2022].map((y) => charge(res, y)), [5000, 4000, 0]);
  assert.equal(toCents(accumulatedBeforeC(res, 2022) / 100), 900000);
});

test('priorAccum override replaces the replayed accumulation', () => {
  const a = asset({ cost: 10000, rate: 0.5, convention: 'full_year', inServiceDate: '2020-01-01' });
  assert.equal(charge(a, 2021, { priorAccum: 8000 }), 2000, 'only 2,000 left to depreciate');
  assert.equal(charge(a, 2021, { priorAccum: 0 }), 5000);
});

test('property: cumulative charges never exceed cost less residual, whatever the convention', () => {
  const rng = makeRng(2024);
  const conventions = ['half_year', 'day_count', 'full_next_year', 'full_year', 'none'];
  for (let i = 0; i < 300; i++) {
    const costC = 1 + rng.int(500_000_000);
    const residC = rng.chance(0.3) ? rng.int(Math.max(1, Math.floor(costC / 2))) : 0;
    const a = asset({
      cost: costC / 100, residual: residC / 100, rate: [0.02, 0.05, 0.1, 0.2, 0.25, 0.333, 1, 0.075][rng.int(8)],
      convention: rng.pick(conventions), inServiceDate: `${2015 + rng.int(8)}-${String(1 + rng.int(12)).padStart(2, '0')}-${String(1 + rng.int(28)).padStart(2, '0')}`,
    });
    let total = 0;
    for (let y = 2014; y <= 2045; y++) {
      const c = computeAssetCharge(a, y);
      assert.ok(c.chargeC >= 0);
      total += c.chargeC;
      assert.ok(total <= costC - residC, `cap broken for ${JSON.stringify(a)} in ${y}`);
      assert.equal(toCents(c.accumAfter), total, 'accumAfter tracks the running total');
    }
  }
});

// ------------------------------------------------------------------ the run

function runState() {
  const s = buildState({ withDraft: false, withYears: false });
  s.entries = {};
  s.counters = { nextEntryNo: 1 };
  for (const a of Object.values(s.accounts)) a.everUsed = false;
  s.assets = {
    a1: asset({ id: 'a1', name: 'آلة 1', cost: 100000, rate: 0.1, convention: 'half_year', inServiceDate: '2021-03-01' }),
    a2: asset({ id: 'a2', name: 'آلة 2', cost: 50000, rate: 0.2, convention: 'day_count', inServiceDate: '2022-07-01' }),
    a3: asset({ id: 'a3', name: 'أثاث', acct: '1150', accumAcct: '1193', cost: 20000, rate: 0.25, convention: 'full_next_year', inServiceDate: '2022-05-01' }),
    a4: asset({ id: 'a4', name: 'أرض', acct: '1120', accumAcct: null, expenseAcct: null, cost: 300000, rate: 0, convention: 'none', inServiceDate: '2021-01-01' }),
  };
  const L = (...x) => x;
  const add = (no, date, desc, lines, src) => { s.entries[entryId(no)] = makeEntry({ no, date, desc, lines, source: src, sector: 'sec2' }); };
  add(1, '2021-01-01', 'شراء أرض', [L('1120', 300000, 0), L('1340', 0, 300000)]);
  add(2, '2021-03-01', 'شراء آلة', [L('1130', 100000, 0), L('1340', 0, 100000)]);
  add(3, '2021-12-31', 'إهلاك 2021', [L('5290', 5000, 0), L('1191', 0, 5000)], 'depreciation');
  add(4, '2022-05-01', 'شراء أثاث', [L('1150', 20000, 0), L('1340', 0, 20000)]);
  add(5, '2022-07-01', 'شراء آلة', [L('1130', 50000, 0), L('1340', 0, 50000)]);
  add(6, '2022-12-31', 'إهلاك 2022', [L('5290', 15041.1, 0), L('1191', 0, 15041.1)], 'depreciation');
  s.counters.nextEntryNo = 7;
  return s;
}

test('proposeRun: one balanced draft entry, a line per expense account and per accumulated account', () => {
  const s = runState();
  const r = proposeRun({ state: s, year: 2023, defaults: { docIds: ['D0001'], cc: 'cc1', sector: 'sec2' } });
  assert.equal(r.ok, true, JSON.stringify(r.errors));
  assert.equal(r.total, 25000);
  assert.deepEqual(r.lines.map((l) => [l.assetId, l.charge]), [['a1', 10000], ['a2', 10000], ['a3', 5000]]);
  assert.deepEqual(r.skipped, [{ assetId: 'a4', name: 'أرض', reason: 'none' }]);
  const e = r.entry;
  assert.equal(e.date, '2023-12-31');
  assert.equal(e.status, 'draft');
  assert.equal(e.source, 'depreciation');
  assert.equal(e.desc, 'إهلاك سنة 2023');
  assert.deepEqual(e.lines.map((l) => [l.acct, l.dr, l.cr]), [['5290', 25000, 0], ['1191', 0, 20000], ['1193', 0, 5000]]);
  assert.deepEqual(r.classes, { expense: [{ acct: '5290', amount: 25000 }], accum: [{ acct: '1191', amount: 20000 }, { acct: '1193', amount: 5000 }] });
  const dr = e.lines.reduce((t, l) => t + toCents(l.dr), 0);
  const cr = e.lines.reduce((t, l) => t + toCents(l.cr), 0);
  assert.equal(dr, cr, 'the offsetting side is the sum of the rounded lines');
  assert.equal(r.run.status, 'proposed');
  assert.equal(r.run.postedEntryNo, null);
  assert.deepEqual(e.docIds, ['D0001']);
  assert.equal(e.cc, 'cc1');
});

test('proposeRun: the offsetting line equals the sum of per-asset rounded lines (no plug)', () => {
  const s = runState();
  s.assets = {
    x1: asset({ id: 'x1', cost: 822153, rate: 0.05, convention: 'half_year', inServiceDate: '2021-02-01' }),
    x2: asset({ id: 'x2', cost: 82175, rate: 0.25, convention: 'half_year', inServiceDate: '2021-02-01' }),
    x3: asset({ id: 'x3', cost: 33333.33, rate: 0.07, convention: 'half_year', inServiceDate: '2021-02-01' }),
  };
  const r = proposeRun({ state: s, year: 2021 });
  const per = r.lines.map((l) => toCents(l.charge));
  assert.deepEqual(r.lines.map((l) => l.charge), [20553.83, 10271.88, 1166.67]);
  const total = per.reduce((a, b) => a + b, 0);
  assert.equal(r.entry.lines[0].dr, total / 100);
  assert.equal(toCents(r.entry.lines[1].cr), total);
});

test('proposeRun errors: nothing to depreciate, a posted run for the year, bad years; unknown accounts warn', () => {
  const s = runState();
  assert.deepEqual(proposeRun({ state: s, year: 2020 }).errors.map((e) => e.code), ['nothing-to-depreciate']);
  s.depRuns[2022] = { year: 2022, status: 'posted', lines: [], postedEntryNo: 6 };
  assert.deepEqual(proposeRun({ state: s, year: 2022 }).errors.map((e) => e.code), ['run-posted']);
  assert.deepEqual(proposeRun({ state: s, year: 'x' }).errors.map((e) => e.code), ['year-invalid']);
  const s2 = runState();
  s2.assets.a1.accumAcct = '9999';
  assert.ok(proposeRun({ state: s2, year: 2023 }).warnings.some((w) => w.code === 'asset-account-unknown'));
});

test('planProposeRun stores the proposal; a re-run replaces an unposted proposal only', () => {
  const s = runState();
  const plan = planProposeRun(s, { year: 2023 });
  assert.equal(plan.ok, true);
  assert.deepEqual(plan.writes.map((w) => [w.op, w.path]), [['set', 'depRuns/2023']]);
  assert.equal(plan.audit.kind, 'depreciation-propose');
  applyPlan(s, plan);
  assert.equal(s.depRuns[2023].status, 'proposed');
  assert.equal(planProposeRun(s, { year: 2023 }).ok, true, 're-run over an unposted proposal');
  s.depRuns[2023].status = 'posted';
  assert.equal(planProposeRun(s, { year: 2023 }).ok, false);
  assert.equal(planProposeRun(s, { year: 2020 }).ok, false);
});

test('planPostDepreciation posts the entry and marks the run posted with its number', () => {
  const s = runState();
  const proposal = proposeRun({ state: s, year: 2023, defaults: { docIds: ['D0001'], cc: 'cc1', sector: 'sec2' } });
  const plan = planPostDepreciation(s, { year: 2023, entry: proposal.entry, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.entryNo, 7);
  const forwarded = planPostDepreciation(s, { year: 2023, entry: proposal.entry, no: 50, user: USER, now: NOW });
  assert.equal(forwarded.entryNo, 50);
  assert.equal(forwarded.writes.find((x) => x.path === 'depRuns/2023').data.postedEntryNo, 50);
  const w = plan.writes.find((x) => x.path === 'depRuns/2023');
  assert.equal(w.data.status, 'posted');
  assert.equal(w.data.postedEntryNo, 7);
  assert.equal(plan.audit.kind, 'depreciation-post');
  applyPlan(s, plan);
  assert.equal(s.entries.e000007.source, 'depreciation');
  assert.equal(planPostDepreciation(s, { year: 2023, entry: proposal.entry }).ok, false, 'cannot post a year twice');
  // without a prepared entry the header dimensions are missing, so posting is refused with the validation errors
  const bare = planPostDepreciation(runState(), { year: 2023, user: USER, now: NOW });
  assert.equal(bare.ok, false);
  assert.ok(bare.errors.some((e) => e.code === 'dim-missing'));
  const withDefaults = planPostDepreciation(runState(), { year: 2023, user: USER, now: NOW, defaults: { docIds: ['D0001'], cc: 'cc1', sector: 'sec2' } });
  assert.equal(withDefaults.ok, true, JSON.stringify(withDefaults.errors));
});

test('rollForward: opening + additions - disposals = closing, tied to the ledger', () => {
  const s = runState();
  const rf = rollForward({ state: s, year: 2022 });
  const cost = Object.fromEntries(rf.cost.map((r) => [r.acct, r]));
  assert.deepEqual([cost['1130'].opening, cost['1130'].additions, cost['1130'].disposals, cost['1130'].closing], [100000, 50000, 0, 150000]);
  assert.deepEqual([cost['1150'].opening, cost['1150'].additions, cost['1150'].closing], [0, 20000, 20000]);
  assert.deepEqual([cost['1120'].opening, cost['1120'].additions, cost['1120'].closing], [300000, 0, 300000]);
  for (const r of rf.cost) assert.equal(Math.round((r.opening + r.additions - r.disposals) * 100), Math.round(r.closing * 100));
  const accum = Object.fromEntries(rf.accum.map((r) => [r.acct, r]));
  assert.deepEqual([accum['1191'].opening, accum['1191'].charge, accum['1191'].closing], [5000, 15041.1, 20041.1]);
  assert.deepEqual([accum['1193'].opening, accum['1193'].charge, accum['1193'].closing], [0, 0, 0]);
  for (const r of rf.accum) assert.equal(Math.round((r.opening + r.charge - r.disposals) * 100), Math.round(r.closing * 100));
  assert.equal(rf.ok, true, 'the register ties to the ledger');
  assert.ok(rf.cost.every((r) => r.difference === 0));
  assert.equal(rf.totals.cost.closing, 470000);
  assert.equal(rf.totals.accum.closing, 20041.1);
  assert.equal(rf.totals.cost.ledger, 470000);
});

test('rollForward reports (never forces) a difference from the ledger', () => {
  const s = runState();
  s.entries[entryId(6)].lines[0].dr = 15000;
  s.entries[entryId(6)].lines[1].cr = 15000;
  const rf = rollForward({ state: s, year: 2022 });
  assert.equal(rf.ok, false);
  const row = rf.accum.find((r) => r.acct === '1191');
  assert.equal(row.ledger, 20000);
  assert.equal(row.closing, 20041.1);
  assert.equal(row.difference, 41.1);
  assert.equal(row.ok, false);
  assert.equal(rf.cost.every((r) => r.ok), true);
  // a cost addition missing from the register shows up too
  const s2 = runState();
  s2.entries[entryId(5)].lines[0].dr = 60000;
  s2.entries[entryId(5)].lines[1].cr = 60000;
  const rf2 = rollForward({ state: s2, year: 2022 });
  assert.equal(rf2.cost.find((r) => r.acct === '1130').difference, -10000);
});

test('rollForward handles disposals', () => {
  const s = runState();
  s.assets.a1.disposalDate = '2022-09-30';
  const rf = rollForward({ state: s, year: 2022 });
  const c = rf.cost.find((r) => r.acct === '1130');
  assert.deepEqual([c.opening, c.additions, c.disposals, c.closing], [100000, 50000, 100000, 50000]);
  const a = rf.accum.find((r) => r.acct === '1191');
  // a1 accumulated 5,000 + 10,000 (2022 charge) is removed on disposal; a2 charges 5,041.10
  assert.deepEqual([a.opening, a.charge, a.disposals, a.closing], [5000, 15041.1, 15000, 5041.1]);
  const next = rollForward({ state: s, year: 2023 });
  assert.equal(next.cost.find((r) => r.acct === '1130').opening, 50000, 'disposed assets drop out the next year');
});

test('run + post keep the books balanced', () => {
  const s = runState();
  applyPlan(s, planPostDepreciation(s, { year: 2023, user: USER, now: NOW, defaults: { docIds: ['D0001'], cc: 'cc1', sector: 'sec2' } }));
  const tb = trialBalance({ state: s, asOf: '2023-12-31' });
  assert.equal(tb.balanced, true);
  const rf = rollForward({ state: s, year: 2023 });
  assert.equal(rf.ok, true, JSON.stringify(rf.accum));
});

test('accumulatedBeforeC is zero for the in-service year and before', () => {
  const a = asset();
  assert.equal(accumulatedBeforeC(a, 2021), 0);
  assert.equal(accumulatedBeforeC(a, 2022), 500000);
  assert.equal(accumulatedBeforeC({ ...a, inServiceDate: '' }, 2030), 0);
});
