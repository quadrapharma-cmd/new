// Property-style tests: hand-written randomised checks with a seeded PRNG (no external library).
import test from 'node:test';
import assert from 'node:assert/strict';
import * as engine from '../../src/engine/index.js';
import { toCents, fromCents, round2, mulDivRound, applyRate, productCents } from '../../src/lib/money.js';
import { addDays } from '../../src/lib/dates.js';
import { makeRng } from '../synthetic/rng.js';
import { buildState, cloneState, addRandomEntries, makeEntry, entryId, NOW, USER } from '../synthetic/build-state.js';
import { applyPlan } from '../synthetic/apply-plan.js';

const {
  balances, trialBalance, incomeStatement, incomeComparative, balanceSheet, partyBalances, postedLines, validateEntry,
  planPost, planAmend, planVoid, planReverse, planSaveDraft, planDeleteDraft, checkIntegrity, nextEntryNo,
} = engine;

const SEEDS = [1, 2, 3, 17, 2024];
const randomState = (seed, n = 120) => {
  const rng = makeRng(seed);
  const s = buildState({ withDraft: false, withYears: false });
  // start from an empty ledger so every figure comes from the random entries
  s.entries = {};
  s.counters = { nextEntryNo: 1 };
  addRandomEntries(rng, s, n);
  return { s, rng };
};
const randomDate = (rng) => addDays('2020-01-01', rng.int(1461));

test('rounding vectors (generic half-cent cases)', () => {
  assert.equal(round2(20553.825), 20553.83);
  assert.equal(round2(10271.875), 10271.88);
  assert.equal(fromCents(productCents([3200, 0.2, 355], [365])), 622.47);
  assert.equal(fromCents(applyRate(toCents(3200), 0.2, 355, 365)), 622.47);
  assert.equal(round2(292027.329), 292027.33);
  assert.equal(fromCents(mulDivRound(toCents(1), 1, 1)), 1);
});

test('rounding: round2 agrees with exact decimal rounding for random 3-decimal numbers', () => {
  const rng = makeRng(99);
  for (let i = 0; i < 2000; i++) {
    const thousandths = rng.int(2_000_000_000) - 1_000_000_000;
    const n = thousandths / 1000;
    const sign = thousandths < 0 ? -1 : 1;
    const a = Math.abs(thousandths);
    const expectedC = sign * Math.floor((a + 5) / 10); // half away from zero on exact integers
    assert.equal(toCents(n), expectedC, `n=${n}`);
    assert.equal(round2(n), expectedC === 0 ? 0 : expectedC / 100);
  }
});

for (const seed of SEEDS) {
  test(`seed ${seed}: random balanced entries => the trial balance balances (cumulative and per year)`, () => {
    const { s, rng } = randomState(seed);
    assert.equal(Object.values(s.entries).every((e) => validateEntry(e, { state: s }).balanced), true);
    for (let i = 0; i < 8; i++) {
      const tb = trialBalance({ state: s, asOf: randomDate(rng) });
      assert.equal(tb.balanced, true);
      assert.equal(tb.totals.closingDr, tb.totals.closingCr);
      assert.equal(tb.totals.debit, tb.totals.credit);
    }
    for (const y of [2020, 2021, 2022, 2023]) {
      const tb = trialBalance({ state: s, mode: 'year', year: y });
      assert.equal(tb.balanced, true);
      assert.equal(tb.totals.openingDr, tb.totals.openingCr);
    }
    assert.equal(balances({ state: s }).totals.closing, 0);
  });

  test(`seed ${seed}: assets = liabilities + equity (derived retained earnings) at every entry date`, () => {
    const { s } = randomState(seed, 80);
    const dates = [...new Set(postedLines(s).map((l) => l.date))];
    assert.ok(dates.length > 20);
    for (const d of dates) {
      const bs = balanceSheet({ state: s, asOf: d });
      assert.equal(bs.check.balanced, true, `difference at ${d}: ${bs.check.difference}`);
      assert.equal(bs.check.difference, 0);
      assert.deepEqual(bs.unclassified, []);
    }
    // equity decomposes: retained (accounts + prior-year results) + current result + the rest
    const bs = balanceSheet({ state: s, asOf: '2022-06-30' });
    const sumC = toCents(bs.equity.capital.total) + toCents(bs.equity.capitalCalled.total) + toCents(bs.equity.settlementShares.total)
      + toCents(bs.equity.retained) + toCents(bs.equity.currentResult);
    assert.equal(sumC, toCents(bs.equity.total));
  });

  test(`seed ${seed}: closing = opening + movement for any period`, () => {
    const { s, rng } = randomState(seed);
    for (let i = 0; i < 12; i++) {
      let a = randomDate(rng);
      let b = randomDate(rng);
      if (a > b) [a, b] = [b, a];
      const r = balances({ state: s, from: a, to: b });
      for (const row of r.rows) {
        assert.equal(toCents(row.closing), toCents(row.opening) + toCents(row.debit) - toCents(row.credit), `${row.acct} ${a}..${b}`);
        assert.equal(toCents(row.movement), toCents(row.debit) - toCents(row.credit));
      }
      assert.equal(r.totals.closing, 0);
      // opening of a period equals closing of the previous day
      const prev = balances({ state: s, to: addDays(a, -1) });
      for (const row of r.rows) assert.equal(toCents(row.opening), toCents(prev.byAcct[row.acct] ? prev.byAcct[row.acct].closing : 0), `${row.acct}`);
    }
  });

  test(`seed ${seed}: results do not depend on entry order, line order, or on splitting lines`, () => {
    const { s, rng } = randomState(seed, 90);
    const base = {
      tb: trialBalance({ state: s, asOf: '2023-12-31' }),
      is: incomeComparative({ state: s }),
      bs: balanceSheet({ state: s, asOf: '2022-09-30' }),
      pb: partyBalances({ state: s, asOf: '2023-12-31' }),
    };
    // shuffle entry insertion order and the line order inside every entry
    const shuffled = cloneState(s);
    shuffled.entries = {};
    for (const [id, e] of rng.shuffle(Object.entries(s.entries))) shuffled.entries[id] = { ...e, lines: rng.shuffle(e.lines) };
    // split every line into two lines on the same account (amounts add up exactly)
    const split = cloneState(s);
    for (const e of Object.values(split.entries)) {
      e.lines = e.lines.flatMap((l) => {
        const side = l.dr > 0 ? 'dr' : 'cr';
        const c = toCents(l[side]);
        if (c < 2) return [l];
        const part = 1 + rng.int(c - 1);
        return [{ ...l, [side]: fromCents(part) }, { ...l, [side]: fromCents(c - part) }];
      }).map((l, i) => ({ ...l, n: i + 1 }));
    }
    for (const variant of [shuffled, split]) {
      assert.deepEqual(trialBalance({ state: variant, asOf: '2023-12-31' }).rows.map((r) => [r.acct, r.closing]), base.tb.rows.map((r) => [r.acct, r.closing]));
      assert.deepEqual(trialBalance({ state: variant, asOf: '2023-12-31' }).totals, base.tb.totals);
      assert.deepEqual(incomeComparative({ state: variant }).totals, base.is.totals);
      assert.deepEqual(balanceSheet({ state: variant, asOf: '2022-09-30' }), base.bs);
      assert.deepEqual(partyBalances({ state: variant, asOf: '2023-12-31' }).accounts.map((a) => [a.acct, a.total, a.unassigned]), base.pb.accounts.map((a) => [a.acct, a.total, a.unassigned]));
    }
    // order invariance is exact, including the flat ledger
    assert.deepEqual(postedLines(shuffled).map((l) => [l.entryId, l.n, l.acct, l.dr, l.cr]), postedLines(s).map((l) => [l.entryId, l.n, l.acct, l.dr, l.cr]));
  });

  test(`seed ${seed}: party balances add up to the account balance (by line party), and cost-center partitions add up`, () => {
    const { s, rng } = randomState(seed);
    for (let i = 0; i < 6; i++) {
      const asOf = randomDate(rng);
      const pb = partyBalances({ state: s, asOf });
      const tb = balances({ state: s, to: asOf });
      assert.equal(pb.accounts.length, tb.rows.length);
      for (const a of pb.accounts) {
        assert.equal(a.ok, true);
        const partyC = a.parties.reduce((t, p) => t + toCents(p.signed), 0);
        assert.equal(partyC + toCents(a.unassignedSigned), toCents(a.signed), `account ${a.acct}`);
        assert.equal(toCents(a.signed), toCents(tb.byAcct[a.acct].closing));
      }
      // partition by cost center: every line has an effective cost center
      const parts = ['cc1', 'cc2', 'cc3'].map((cc) => balances({ state: s, to: asOf, filters: { costCenter: cc } }));
      for (const row of tb.rows) {
        const sum = parts.reduce((t, p) => t + (p.byAcct[row.acct] ? toCents(p.byAcct[row.acct].closing) : 0), 0);
        assert.equal(sum, toCents(row.closing));
      }
      const noTrust = balances({ state: s, to: asOf, filters: { includeFiduciary: false } });
      const onlyTrust = balances({ state: s, to: asOf, filters: { costCenter: 'cc3' } });
      for (const row of tb.rows) {
        const a = noTrust.byAcct[row.acct] ? toCents(noTrust.byAcct[row.acct].closing) : 0;
        const b = onlyTrust.byAcct[row.acct] ? toCents(onlyTrust.byAcct[row.acct].closing) : 0;
        assert.equal(a + b, toCents(row.closing));
      }
    }
  });

  test(`seed ${seed}: yearly results add up to the cumulative P&L and to the derived equity`, () => {
    const { s } = randomState(seed);
    const cmp = incomeComparative({ state: s });
    const total = Object.values(cmp.totals.netResult.byYear).reduce((t, v) => t + toCents(v), 0);
    const whole = incomeStatement({ state: s, from: '2020-01-01', to: '2023-12-31' });
    assert.equal(total, toCents(whole.netResult));
    const bs = balanceSheet({ state: s, asOf: '2023-12-31' });
    assert.equal(toCents(bs.equity.priorResults) + toCents(bs.equity.currentResult), total);
    for (const y of cmp.years) {
      const st = incomeStatement({ state: s, year: y });
      assert.equal(toCents(st.netResult), toCents(st.revenue.net) - toCents(st.cogs.total) - toCents(st.opex.total) - toCents(st.nondeductible.total));
    }
  });
}

test('validation: random entries are balanced; perturbing one amount makes them unbalanced with the right side', () => {
  const rng = makeRng(31);
  const { s } = randomState(31, 40);
  for (const e of Object.values(s.entries)) {
    const v = validateEntry(e, { state: s });
    assert.equal(v.balanced, true);
    assert.equal(v.errors.some((x) => x.code === 'unbalanced'), false);
    const copy = JSON.parse(JSON.stringify(e));
    const l = copy.lines[rng.int(copy.lines.length)];
    const side = l.dr > 0 ? 'dr' : 'cr';
    const bump = 1 + rng.int(500);
    l[side] = fromCents(toCents(l[side]) + bump);
    const bad = validateEntry(copy, { state: s });
    assert.equal(bad.balanced, false);
    assert.equal(toCents(bad.totals.difference), bump);
    assert.equal(bad.totals.side, side === 'dr' ? 'D' : 'C');
  }
});

// ------------------------------------------------------------------ whole-flow property: plans keep the books sound

function randomValidEntry(rng, state, year) {
  const accts = Object.values(state.accounts).filter((a) => a.postable && a.active);
  const k = 2 + rng.int(3);
  const lines = [];
  let diff = 0;
  const party = () => rng.pick(['p0001', 'p0002', 'p0003', 'p0004', 'p0005']);
  for (let i = 0; i < k; i++) {
    const c = 1 + rng.int(900_000);
    const dr = rng.chance(0.5);
    lines.push(dr ? [rng.pick(accts).code, fromCents(c), 0, { partyId: party() }] : [rng.pick(accts).code, 0, fromCents(c), { partyId: party() }]);
    diff += dr ? c : -c;
  }
  if (diff !== 0) lines.push(diff > 0 ? [rng.pick(accts).code, 0, fromCents(diff), { partyId: party() }] : [rng.pick(accts).code, fromCents(-diff), 0, { partyId: party() }]);
  const e = makeEntry({ no: null, status: 'draft', date: `${year}-${String(1 + rng.int(12)).padStart(2, '0')}-${String(1 + rng.int(28)).padStart(2, '0')}`, desc: 'قيد', lines, cc: 'cc1', sector: 'sec2', docIds: ['D0001'] });
  e.createdAt = null;
  e.createdBy = null;
  return e;
}

for (const seed of [5, 6, 7]) {
  test(`seed ${seed}: a random sequence of post / amend / void / reverse / draft plans keeps numbering gap-free and the books sound`, () => {
    const rng = makeRng(seed);
    const s = buildState({ withDraft: false });
    const startNext = nextEntryNo(s);
    let ops = 0;
    for (let i = 0; i < 80; i++) {
      const year = rng.pick([2022, 2023]);
      const posted = Object.entries(s.entries).filter(([, e]) => e.status === 'posted' && e.fy >= 2022);
      const roll = rng.next();
      let plan;
      if (roll < 0.55 || posted.length < 3) plan = planPost(s, { entry: randomValidEntry(rng, s, year), user: USER, now: NOW });
      else if (roll < 0.7) {
        const [id, e] = rng.pick(posted);
        plan = planAmend(s, { id, entry: randomValidEntry(rng, s, e.fy), reason: 'تعديل اختبار', expectedVersion: e.version, user: USER, now: NOW });
      } else if (roll < 0.8) {
        const [id, e] = rng.pick(posted);
        plan = planVoid(s, { id, reason: 'إلغاء اختبار', expectedVersion: e.version, user: USER, now: NOW });
      } else if (roll < 0.9) {
        const [id] = rng.pick(posted);
        plan = planReverse(s, { id, reason: 'عكس اختبار', date: `${year}-12-15`, user: USER, now: NOW });
        if (!plan.ok) {
          assert.deepEqual(plan.errors.map((e) => e.code), ['already-reversed']);
          continue;
        }
      } else if (roll < 0.95) plan = planSaveDraft(s, { entry: randomValidEntry(rng, s, year), user: USER, now: NOW, rand: rng.next });
      else {
        const drafts = Object.keys(s.entries).filter((id) => s.entries[id].status === 'draft');
        if (!drafts.length) continue;
        plan = planDeleteDraft(s, { id: rng.pick(drafts) });
      }
      assert.equal(plan.ok, true, JSON.stringify(plan.errors));
      applyPlan(s, plan);
      ops++;
    }
    assert.ok(ops > 40);
    // numbering: every number from the start of the sequence to the maximum exists exactly once (void keeps its number)
    const nos = Object.values(s.entries).filter((e) => e.status !== 'draft').map((e) => e.no).filter((n) => n >= startNext).sort((a, b) => a - b);
    assert.deepEqual(nos, Array.from({ length: nos.length }, (_, i) => startNext + i));
    assert.equal(s.counters.nextEntryNo, nos.length ? nos[nos.length - 1] + 1 : startNext);
    // the books stay sound
    const errors = checkIntegrity(s, { now: NOW }).filter((f) => f.severity === 'error');
    assert.deepEqual(errors, []);
    assert.equal(trialBalance({ state: s, asOf: '2023-12-31' }).balanced, true);
    assert.equal(balanceSheet({ state: s, asOf: '2023-12-31' }).check.balanced, true);
    // every history chain is consistent with the version
    for (const e of Object.values(s.entries)) {
      if (e.status === 'draft') continue;
      const changes = e.history.filter((h) => h.kind === 'amend' || h.kind === 'void').length;
      assert.equal(e.version, 1 + changes);
    }
  });
}

test('reversal property: posting an entry and then reversing it leaves every later balance unchanged', () => {
  const rng = makeRng(77);
  const s = buildState({ withDraft: false });
  const before = balances({ state: s, to: '2023-12-31' });
  const post = planPost(s, { entry: randomValidEntry(rng, s, 2023), user: USER, now: NOW });
  applyPlan(s, post);
  const rev = planReverse(s, { id: post.id, reason: 'اختبار', date: '2023-12-20', user: USER, now: NOW });
  applyPlan(s, rev);
  const after = balances({ state: s, to: '2023-12-31' });
  assert.deepEqual(after.rows.map((r) => [r.acct, r.closing]).filter(([, c]) => c !== 0), before.rows.map((r) => [r.acct, r.closing]).filter(([, c]) => c !== 0));
  assert.equal(entryId(post.entryNo), post.id);
});

test('engine barrel exports the contract names', () => {
  for (const name of [
    'postedLines', 'balances', 'trialBalance', 'incomeStatement', 'incomeComparative', 'balanceSheet', 'accountStatement',
    'partyStatement', 'partyBalances', 'validateEntry', 'planPost', 'planSaveDraft', 'nextEntryNo', 'planAmend', 'planVoid',
    'planReverse', 'planCloseYear', 'planReopenYear', 'planLockYear', 'planUnlockYear', 'computeAssetCharge', 'proposeRun',
    'rollForward', 'applyTemplate', 'builtinRules', 'checkIntegrity', 'normalizeName', 'suggestMerges',
  ]) assert.equal(typeof engine[name], name === 'builtinRules' ? 'object' : 'function', name);
});
