// Fixed-asset depreciation: per-asset charge by convention, a proposed yearly run (one draft entry, reviewed then
// posted by the owner) and a roll-forward with a tie-to-ledger check. All money maths is integer piastres with
// ROUND_HALF_UP on the exact product (cost x rate x fraction), never on float intermediates.
import { toCents, fromCents, applyRate } from '../lib/money.js';
import { fyOf, yearEnd, yearStart, daysBetween, isValidISO } from '../lib/dates.js';
import { MSG } from './constants.js';
import { coll, compareCode, clone } from './util.js';
import { accountBalanceCents, postedLines } from './ledger.js';
import { planPost, fail, err } from './posting.js';

/** Annual rate as a fraction: 0.05 is 5%; values above 1 are read as percent (5 -> 0.05). */
export function normalizeRate(rate) {
  const r = Number(rate);
  if (!Number.isFinite(r) || r <= 0) return 0;
  return r > 1 ? r / 100 : r;
}

const assetList = (state, assets) => {
  const src = assets || Object.entries(coll(state, 'assets')).map(([k, a]) => ({ ...a, id: a.id ?? k }));
  return src.map((a, i) => ({ ...a, id: a.id ?? `a${i + 1}` })).sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
};

/** Uncapped charge in cents for the year (no residual cap, no accumulation). */
function rawChargeC(asset, year) {
  if (asset.active === false) return { c: 0, basis: 'inactive' };
  const costC = toCents(asset.cost || 0);
  const rate = normalizeRate(asset.rate);
  const convention = asset.convention || 'day_count';
  if (costC <= 0 || rate === 0 || convention === 'none') return { c: 0, basis: 'none' };
  if (!isValidISO(asset.inServiceDate)) return { c: 0, basis: 'no-date' };
  const y0 = fyOf(asset.inServiceDate);
  if (year < y0) return { c: 0, basis: 'not-in-service' };
  if (isValidISO(asset.disposalDate) && fyOf(asset.disposalDate) < year) return { c: 0, basis: 'disposed' };
  if (year > y0) return { c: applyRate(costC, rate), basis: 'full' };
  switch (convention) {
    case 'half_year':
      return { c: applyRate(costC, rate, 1, 2), basis: 'half_year' };
    case 'day_count': {
      const days = Math.min(365, daysBetween(asset.inServiceDate, yearEnd(y0)) + 1);
      return { c: applyRate(costC, rate, days, 365), basis: `day_count:${days}/365` };
    }
    case 'full_next_year':
      return { c: 0, basis: 'full_next_year' };
    case 'full_year':
      return { c: applyRate(costC, rate), basis: 'full' };
    default:
      return { c: 0, basis: 'none' };
  }
}

const capOf = (asset) => Math.max(0, toCents(asset.cost || 0) - toCents(asset.residual || 0));

/** Accumulated depreciation (cents) before `year`, replaying the register's own conventions with the cap. */
export function accumulatedBeforeC(asset, year, opts = {}) {
  if (opts.priorAccum !== undefined && opts.priorAccum !== null) return toCents(opts.priorAccum);
  if (!isValidISO(asset.inServiceDate)) return 0;
  const cap = capOf(asset);
  let acc = 0;
  for (let y = fyOf(asset.inServiceDate); y < year; y++) {
    acc += Math.min(rawChargeC(asset, y).c, Math.max(0, cap - acc));
  }
  return acc;
}

/**
 * computeAssetCharge(asset, year, opts)
 * asset: { id, cost, inServiceDate, rate, convention, residual, active, disposalDate }.
 * Conventions: half_year (cost x rate x 1/2 in the first year), day_count (cost x rate x days/365, days counted
 * inclusively from the in-service date to 31 Dec), full_next_year (nothing in the purchase year), full_year,
 * none (land, work in progress). Later years charge cost x rate. The charge is capped at cost - residual.
 * opts.priorAccum (pounds) overrides the replayed accumulation (e.g. when the ledger is the source of truth).
 * Returns { assetId, year, convention, basis, raw, charge, chargeC, accumBefore, accumAfter, remaining, capped }.
 */
export function computeAssetCharge(asset, year, opts = {}) {
  const raw = rawChargeC(asset, year);
  const before = accumulatedBeforeC(asset, year, opts);
  const room = Math.max(0, capOf(asset) - before);
  const chargeC = Math.min(raw.c, room);
  return {
    assetId: asset.id ?? null,
    year,
    convention: asset.convention || 'day_count',
    basis: raw.c > chargeC ? 'capped' : raw.basis,
    raw: fromCents(raw.c),
    charge: fromCents(chargeC),
    chargeC,
    accumBefore: fromCents(before),
    accumAfter: fromCents(before + chargeC),
    remaining: fromCents(room - chargeC),
    capped: raw.c > chargeC,
  };
}

const yearOk = (y) => Number.isInteger(Number(y)) && /^\d{4}$/.test(String(y));

/**
 * proposeRun({ state, year, assets, date, defaults })
 * One proposed entry per run: a debit line per expense account and a credit line per accumulated-depreciation
 * account (the "asset class"), each the SUM of the rounded per-asset charges, so the entry balances with no plug.
 * `defaults` ({ docIds, cc, sector }) pre-fill the header. Returns
 * { ok, errors, warnings, year, date, lines, skipped, classes, total, run, entry }.
 */
export function proposeRun({ state, year, assets = null, date = null, defaults = {} } = {}) {
  const errors = [];
  const warnings = [];
  if (!yearOk(year)) return { ok: false, errors: [err('year-invalid', MSG.YEAR_INVALID)], warnings, lines: [], skipped: [], classes: [], total: 0, run: null, entry: null };
  const y = Number(year);
  const existing = coll(state, 'depRuns')[y];
  if (existing && existing.status === 'posted') errors.push(err('run-posted', MSG.DEPRUN_POSTED));
  const lines = [];
  const skipped = [];
  const accounts = coll(state, 'accounts');
  for (const asset of assetList(state, assets)) {
    const c = computeAssetCharge(asset, y);
    if (c.chargeC <= 0) {
      skipped.push({ assetId: asset.id, name: asset.name || '', reason: c.basis === 'capped' ? 'fully-depreciated' : c.basis });
      continue;
    }
    for (const k of ['accumAcct', 'expenseAcct']) {
      if (!accounts[asset[k]]) warnings.push({ code: 'asset-account-unknown', msg: `حساب ${k === 'accumAcct' ? 'مجمع الإهلاك' : 'المصروف'} غير موجود للأصل ${asset.name || asset.id}`, assetId: asset.id });
    }
    lines.push({
      assetId: asset.id, name: asset.name || '', acct: asset.acct || null, accumAcct: asset.accumAcct, expenseAcct: asset.expenseAcct,
      convention: c.convention, basis: c.basis, charge: c.charge, chargeC: c.chargeC, accumBefore: c.accumBefore, accumAfter: c.accumAfter, capped: c.capped,
    });
  }
  const sumBy = (key) => {
    const m = new Map();
    for (const l of lines) m.set(l[key], (m.get(l[key]) || 0) + l.chargeC);
    return [...m].sort((a, b) => compareCode(String(a[0]), String(b[0])));
  };
  const expense = sumBy('expenseAcct');
  const accum = sumBy('accumAcct');
  const totalC = lines.reduce((s, l) => s + l.chargeC, 0);
  if (!totalC && !errors.length) errors.push(err('nothing-to-depreciate', MSG.NOTHING_TO_DEPRECIATE));
  const d = date || yearEnd(y);
  const memo = `إهلاك سنة ${y}`;
  const entryLines = [];
  for (const [acct, c] of expense) entryLines.push({ n: entryLines.length + 1, acct: String(acct), dr: fromCents(c), cr: 0, memo });
  for (const [acct, c] of accum) entryLines.push({ n: entryLines.length + 1, acct: String(acct), dr: 0, cr: fromCents(c), memo });
  const entry = {
    no: null, date: d, fy: y, status: 'draft', desc: memo, docIds: defaults.docIds ? defaults.docIds.slice() : [],
    cc: defaults.cc ?? null, sector: defaults.sector ?? null, source: 'depreciation', isLegacy: false, legacyRow: null,
    version: 1, voidReason: null, reversalOf: null, createdBy: null, createdAt: null, postedBy: null, postedAt: null,
    lines: entryLines.map((l) => ({ partyId: null, docIds: [], cc: null, sector: null, valueDate: null, needsReview: false, reviewReason: '', links: [], legacy: null, ...l })),
    history: [],
  };
  const run = {
    year: y, status: 'proposed', postedEntryNo: null, total: fromCents(totalC),
    lines: lines.map(({ chargeC, ...rest }) => rest),
  };
  return {
    ok: errors.length === 0,
    errors,
    warnings,
    year: y,
    date: d,
    lines: lines.map(({ chargeC, ...rest }) => rest),
    skipped,
    classes: { expense: expense.map(([acct, c]) => ({ acct: String(acct), amount: fromCents(c) })), accum: accum.map(([acct, c]) => ({ acct: String(acct), amount: fromCents(c) })) },
    total: fromCents(totalC),
    run,
    entry,
  };
}

/** planProposeRun(state, { year, ... }) — stores depRuns/<year> as 'proposed' (a re-run replaces an unposted proposal only). */
export function planProposeRun(state, params = {}) {
  const r = proposeRun({ state, ...params });
  if (!r.ok) return fail(r.errors, { proposal: r });
  return {
    ok: true,
    writes: [{ op: 'set', path: `depRuns/${r.year}`, data: r.run }],
    audit: { kind: 'depreciation-propose', coll: 'depRuns', id: String(r.year), reason: '', summary: `اقتراح قيد إهلاك سنة ${r.year}` },
    errors: [],
    proposal: r,
    entry: r.entry,
  };
}

/**
 * planPostDepreciation(state, { year, entry, no, user, now, reason, defaults })
 * Posts the (optionally edited) run entry through planPost and marks depRuns/<year> as posted with the number.
 */
export function planPostDepreciation(state, params = {}) {
  const { year, user = null, now, reason = '', defaults, no } = params;
  if (!yearOk(year)) return fail(err('year-invalid', MSG.YEAR_INVALID));
  const y = Number(year);
  const existing = coll(state, 'depRuns')[y];
  if (existing && existing.status === 'posted') return fail(err('run-posted', MSG.DEPRUN_POSTED));
  const proposal = proposeRun({ state, year: y, defaults });
  const entry = params.entry || proposal.entry;
  if (!params.entry && !proposal.ok) return fail(proposal.errors);
  const plan = planPost(state, { entry: { ...entry, source: 'depreciation' }, no, user, now, reason });
  if (!plan.ok) return plan;
  const run = { ...clone(existing || proposal.run), year: y, status: 'posted', postedEntryNo: plan.entryNo };
  plan.writes.push({ op: 'set', path: `depRuns/${y}`, data: run });
  plan.audit = { kind: 'depreciation-post', coll: 'entries', id: plan.id, reason, summary: `ترحيل قيد إهلاك سنة ${y} برقم ${plan.entryNo}` };
  return plan;
}

/**
 * rollForward({ state, year, assets })
 * Register roll-forward per cost account and per accumulated-depreciation account:
 * opening + additions - disposals = closing, tied to the ledger balance at 31 Dec of the year.
 * Differences are reported (ok: false), never forced.
 */
export function rollForward({ state, year, assets = null } = {}) {
  const y = Number(year);
  const from = yearStart(y);
  const cost = new Map();
  const accum = new Map();
  const slot = (m, acct) => {
    if (!m.has(acct)) m.set(acct, { opening: 0, additions: 0, disposals: 0, charge: 0 });
    return m.get(acct);
  };
  for (const asset of assetList(state, assets)) {
    if (!isValidISO(asset.inServiceDate)) continue;
    const y0 = fyOf(asset.inServiceDate);
    if (y0 > y) continue;
    const dy = isValidISO(asset.disposalDate) ? fyOf(asset.disposalDate) : null;
    if (dy !== null && dy < y) continue;
    const costC = toCents(asset.cost || 0);
    const before = accumulatedBeforeC(asset, y);
    const charge = computeAssetCharge(asset, y).chargeC;
    if (asset.acct) {
      const c = slot(cost, String(asset.acct));
      if (y0 < y) c.opening += costC;
      else c.additions += costC;
      if (dy === y) c.disposals += costC;
    }
    if (asset.accumAcct) {
      const a = slot(accum, String(asset.accumAcct));
      a.opening += before;
      a.charge += charge;
      if (dy === y) a.disposals += before + charge;
    }
  }
  const lines = postedLines(state);
  const accounts = coll(state, 'accounts');
  const build = (m, sign, chargeKey) => [...m].sort((p, q) => compareCode(p[0], q[0])).map(([acct, v]) => {
    const closing = v.opening + (chargeKey ? v.charge : v.additions) - v.disposals;
    const ledgerC = sign * accountBalanceCents(state, acct, { to: yearEnd(y), lines });
    const row = {
      acct,
      name: accounts[acct] ? accounts[acct].name : '(حساب غير موجود)',
      opening: fromCents(v.opening),
      disposals: fromCents(v.disposals),
      closing: fromCents(closing),
      ledger: fromCents(ledgerC),
      difference: fromCents(closing - ledgerC),
      ok: closing === ledgerC,
    };
    if (chargeKey) row.charge = fromCents(v.charge);
    else row.additions = fromCents(v.additions);
    return row;
  });
  const costRows = build(cost, 1, false);
  const accumRows = build(accum, -1, true);
  const sum = (rows, k) => fromCents(rows.reduce((s, r) => s + toCents(r[k]), 0));
  return {
    year: y,
    from,
    to: yearEnd(y),
    cost: costRows,
    accum: accumRows,
    totals: {
      cost: { opening: sum(costRows, 'opening'), additions: sum(costRows, 'additions'), disposals: sum(costRows, 'disposals'), closing: sum(costRows, 'closing'), ledger: sum(costRows, 'ledger') },
      accum: { opening: sum(accumRows, 'opening'), charge: sum(accumRows, 'charge'), disposals: sum(accumRows, 'disposals'), closing: sum(accumRows, 'closing'), ledger: sum(accumRows, 'ledger') },
    },
    ok: costRows.every((r) => r.ok) && accumRows.every((r) => r.ok),
  };
}
