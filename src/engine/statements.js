// Statements derived from the ledger primitive: trial balance, income statement (single year and
// comparative), balance sheet with derived retained earnings, account and party statements.
// No closing entries exist: P&L accounts keep accumulating and retained earnings are derived.
import { fromCents } from '../lib/money.js';
import { yearStart, yearEnd, addDays, isValidISO, fyOf } from '../lib/dates.js';
import { CLS, CLS_ORDER, PL_LINES } from './constants.js';
import { coll, compareCode, isNil, resolvePartyId } from './util.js';
import { postedLines, balanceMap, balances, normalizeFilters, lineMatches, makeRow } from './ledger.js';

/** Statement line of an account: its own fsLine, else the default implied by its classification. */
export function fsLineOf(account) {
  if (!account) return null;
  return account.fsLine || (account.cls && CLS[account.cls] ? CLS[account.cls].fsLine : null);
}

/** Normal side of an account: its own, else implied by its classification, else from its type. */
export function normalSideOf(account) {
  if (!account) return null;
  if (account.normal) return account.normal;
  if (account.cls && CLS[account.cls]) return CLS[account.cls].normal;
  return ['asset', 'expense'].includes(account.type) ? 'D' : 'C';
}

const nameOf = (state, code) => {
  const a = coll(state, 'accounts')[code];
  return a ? a.name : '(حساب غير موجود)';
};

/** Distinct fiscal years that have posted lines, ascending. */
export function yearsWithActivity(state, { includeDrafts = false, lines = null } = {}) {
  const set = new Set();
  for (const l of lines || postedLines(state, { includeDrafts })) set.add(l.fy);
  return [...set].sort((a, b) => a - b);
}

function periodOf({ year, from, to, asOf }) {
  if (!isNil(year)) return { from: from || yearStart(year), to: to || asOf || yearEnd(year), year: Number(year) };
  return { from: from || null, to: to || asOf || null, year: null };
}

// ---------------------------------------------------------------- trial balance

/**
 * trialBalance({ state, mode, year, asOf, from, to, filters, includeDrafts, includeZero, hideZeroClosing })
 *  mode 'cumulative' (default): from inception to asOf (or end of `year`), opening is zero — the workbook's
 *    trial balance, P&L unclosed.
 *  mode 'year': opening = everything before 1 Jan of `year`, movement within the year, closing.
 * Rows: { acct, name, cls, openingDr, openingCr, debit, credit, closingDr, closingCr, ... }, grouped by class.
 */
export function trialBalance({
  state, mode = 'cumulative', year = null, asOf = null, from = null, to = null,
  filters = {}, includeDrafts = false, includeZero = false, hideZeroClosing = false, lines = null,
} = {}) {
  let f;
  let t;
  if (mode === 'year') {
    if (isNil(year)) throw new TypeError('trialBalance: year is required in year mode');
    f = from || yearStart(year);
    t = to || asOf || yearEnd(year);
  } else {
    f = null;
    t = to || asOf || (isNil(year) ? null : yearEnd(year));
  }
  const b = balances({ state, from: f, to: t, filters, includeDrafts, lines });
  let rows = b.rows;
  if (includeZero) {
    const have = new Set(rows.map((r) => r.acct));
    rows = rows.concat(Object.keys(coll(state, 'accounts')).filter((c) => !have.has(c)).map((c) => makeRow(state, c, { openC: 0, drC: 0, crC: 0 })));
    rows.sort((x, y) => compareCode(x.acct, y.acct));
  }
  if (hideZeroClosing) rows = rows.filter((r) => r._closeC !== 0);
  const groups = [];
  const byCls = new Map();
  for (const r of rows) {
    const key = r.cls || '—';
    if (!byCls.has(key)) {
      const g = { cls: key, rows: [], subtotal: null };
      byCls.set(key, g);
      groups.push(g);
    }
    byCls.get(key).rows.push(r);
  }
  const order = (c) => {
    const i = CLS_ORDER.indexOf(c);
    return i < 0 ? 999 : i;
  };
  groups.sort((a, b) => order(a.cls) - order(b.cls));
  const sum = (rs) => {
    const s = { openDrC: 0, openCrC: 0, drC: 0, crC: 0, closeDrC: 0, closeCrC: 0 };
    for (const r of rs) {
      if (r._openC > 0) s.openDrC += r._openC;
      else s.openCrC += -r._openC;
      s.drC += r._drC;
      s.crC += r._crC;
      if (r._closeC > 0) s.closeDrC += r._closeC;
      else s.closeCrC += -r._closeC;
    }
    return {
      openingDr: fromCents(s.openDrC), openingCr: fromCents(s.openCrC), debit: fromCents(s.drC), credit: fromCents(s.crC),
      closingDr: fromCents(s.closeDrC), closingCr: fromCents(s.closeCrC),
      _closeDrC: s.closeDrC, _closeCrC: s.closeCrC, _drC: s.drC, _crC: s.crC,
    };
  };
  for (const g of groups) g.subtotal = sum(g.rows);
  const totals = sum(rows);
  const balanced = totals._closeDrC === totals._closeCrC && totals._drC === totals._crC
    && sumOpen(rows) === 0;
  return {
    mode, year: isNil(year) ? null : Number(year), from: f, to: t, rows, groups, totals, balanced,
    difference: fromCents(totals._closeDrC - totals._closeCrC),
  };
}
function sumOpen(rows) {
  let s = 0;
  for (const r of rows) s += r._openC;
  return s;
}

// ---------------------------------------------------------------- income statement

/** Income statement over [from,to] (or a whole `year`): movement by fsLine, contras netted. */
export function incomeStatement({ state, year = null, from = null, to = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const p = periodOf({ year, from, to });
  const src = lines || postedLines(state, { includeDrafts });
  // opening is excluded on purpose: only the movement of the period matters
  const m = balanceMap(state, src, { from: p.from, to: p.to, filters });
  const sec = { REVENUE: [], REVENUE_CONTRA: [], COGS: [], OPEX: [], NONDEDUCTIBLE: [] };
  const tot = { REVENUE: 0, REVENUE_CONTRA: 0, COGS: 0, OPEX: 0, NONDEDUCTIBLE: 0 };
  const unclassified = [];
  for (const [acct, r0] of [...m].sort((a, b) => compareCode(a[0], b[0]))) {
    const a = coll(state, 'accounts')[acct];
    const fs = fsLineOf(a);
    const mv = r0.drC - r0.crC; // movement, debit-positive
    if (mv === 0 && r0.drC === 0 && r0.crC === 0) continue;
    if (!fs && a && (a.type === 'revenue' || a.type === 'expense')) {
      unclassified.push({ acct, name: nameOf(state, acct), amount: fromCents(mv) });
      continue;
    }
    if (!PL_LINES.has(fs)) continue;
    const amountC = fs === 'REVENUE' ? -mv : mv;
    if (amountC === 0) continue; // accounts that net to zero in the period are not listed
    sec[fs].push({ acct, name: nameOf(state, acct), amount: fromCents(amountC), _c: amountC });
    tot[fs] += amountC;
  }
  const netRevenueC = tot.REVENUE - tot.REVENUE_CONTRA;
  const grossProfitC = netRevenueC - tot.COGS;
  const netResultC = grossProfitC - tot.OPEX - tot.NONDEDUCTIBLE;
  const strip = (rows) => rows.map(({ _c, ...rest }) => rest);
  return {
    year: p.year,
    from: p.from,
    to: p.to,
    revenue: { rows: strip(sec.REVENUE), gross: fromCents(tot.REVENUE), contraRows: strip(sec.REVENUE_CONTRA), contra: fromCents(tot.REVENUE_CONTRA), net: fromCents(netRevenueC) },
    cogs: { rows: strip(sec.COGS), total: fromCents(tot.COGS) },
    grossProfit: fromCents(grossProfitC),
    opex: { rows: strip(sec.OPEX), total: fromCents(tot.OPEX) },
    nondeductible: { rows: strip(sec.NONDEDUCTIBLE), total: fromCents(tot.NONDEDUCTIBLE) },
    netResult: fromCents(netResultC),
    unclassified,
    _c: { netRevenue: netRevenueC, grossProfit: grossProfitC, netResult: netResultC, ...tot },
  };
}

const TOTAL_KEYS = [
  ['revenueNet', 'صافي الإيرادات', (s) => s._c.netRevenue],
  ['cogs', 'تكلفة المبيعات', (s) => s._c.COGS],
  ['grossProfit', 'مجمل الربح', (s) => s._c.grossProfit],
  ['opex', 'المصروفات', (s) => s._c.OPEX],
  ['nondeductible', 'مصروفات غير واجبة الخصم', (s) => s._c.NONDEDUCTIBLE],
  ['netResult', 'صافي النتيجة', (s) => s._c.netResult],
];

/**
 * Income statement per year side by side.
 * Returns { years, byYear, accounts: [{acct,name,fsLine,byYear}], totals: {key:{label,byYear,changePct}} }.
 * changePct[y] compares y with the previous listed year (null when the base is zero).
 */
export function incomeComparative({ state, years = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const src = lines || postedLines(state, { includeDrafts });
  const ys = (years && years.length ? years.map(Number) : yearsWithActivity(state, { lines: src })).slice().sort((a, b) => a - b);
  const byYear = {};
  const acctMap = new Map();
  for (const y of ys) {
    const s = incomeStatement({ state, year: y, filters, lines: src });
    byYear[y] = s;
    for (const [key, rows] of [['REVENUE', s.revenue.rows], ['REVENUE_CONTRA', s.revenue.contraRows], ['COGS', s.cogs.rows], ['OPEX', s.opex.rows], ['NONDEDUCTIBLE', s.nondeductible.rows]]) {
      for (const r of rows) {
        if (!acctMap.has(r.acct)) acctMap.set(r.acct, { acct: r.acct, name: r.name, fsLine: key, byYear: {} });
        acctMap.get(r.acct).byYear[y] = r.amount;
      }
    }
  }
  const accounts = [...acctMap.values()].sort((a, b) => compareCode(a.acct, b.acct));
  for (const a of accounts) for (const y of ys) if (a.byYear[y] === undefined) a.byYear[y] = 0;
  const totals = {};
  for (const [key, label, get] of TOTAL_KEYS) {
    const by = {};
    const change = {};
    let prev = null;
    for (const y of ys) {
      const c = get(byYear[y]);
      by[y] = fromCents(c);
      change[y] = prev === null || prev === 0 ? null : Math.round(((c - prev) / Math.abs(prev)) * 10000) / 100;
      prev = c;
    }
    totals[key] = { label, byYear: by, changePct: change };
  }
  return { years: ys, byYear, accounts, totals };
}

// ---------------------------------------------------------------- balance sheet

const BS_SECTIONS = {
  ASSET: 'assets', ACCUM_DEP: 'accumDep', LIABILITY: 'liabilities', SUSPENSE: 'suspense',
  CAPITAL: 'capital', CAPITAL_CALLED: 'capitalCalled', SETTLEMENT_SHARES: 'settlementShares', RETAINED: 'retainedAccounts',
};
const DEBIT_PRESENTED = new Set(['ASSET']);

/**
 * balanceSheet({ state, asOf, filters, includeDrafts })
 *  equity = CAPITAL + CAPITAL_CALLED (debit contra, negative) + SETTLEMENT_SHARES + RETAINED accounts
 *           + derived prior-year results (all P&L lines dated before 1 Jan of the as-of year)
 *           + current-year result (P&L lines from 1 Jan to asOf).
 *  Suspense is shown on its own line and takes part in the explicit check:
 *  check = { assets, liabilities, suspense, equity, difference, balanced } with
 *  difference = assets - liabilities - suspense - equity (non-zero also when accounts are unclassified).
 */
export function balanceSheet({ state, asOf, filters = {}, includeDrafts = false, lines = null } = {}) {
  if (!isValidISO(asOf)) throw new TypeError('balanceSheet: asOf (YYYY-MM-DD) is required');
  const year = fyOf(asOf);
  const src = lines || postedLines(state, { includeDrafts });
  const cum = balanceMap(state, src, { from: null, to: asOf, filters });
  const prior = balanceMap(state, src, { from: null, to: addDays(yearStart(year), -1), filters });
  const sections = { assets: [], accumDep: [], liabilities: [], suspense: [], capital: [], capitalCalled: [], settlementShares: [], retainedAccounts: [] };
  const sumC = { assets: 0, accumDep: 0, liabilities: 0, suspense: 0, capital: 0, capitalCalled: 0, settlementShares: 0, retainedAccounts: 0 };
  let priorPLc = 0; // signed debit-positive sum of P&L accounts before the year
  let currentPLc = 0;
  const wrongSide = [];
  const unclassified = [];
  let unclassifiedNaturalC = 0;
  for (const [acct, r] of [...cum].sort((a, b) => compareCode(a[0], b[0]))) {
    const a = coll(state, 'accounts')[acct];
    const closeC = r.drC - r.crC;
    const fs = fsLineOf(a);
    if (PL_LINES.has(fs)) {
      const p = prior.get(acct);
      const pc = p ? p.drC - p.crC : 0;
      priorPLc += pc;
      currentPLc += closeC - pc;
      continue;
    }
    if (closeC === 0) continue;
    const key = BS_SECTIONS[fs];
    if (!key) {
      unclassified.push({ acct, name: nameOf(state, acct), closing: fromCents(closeC) });
      unclassifiedNaturalC += -closeC;
      continue;
    }
    const amountC = DEBIT_PRESENTED.has(fs) ? closeC : -closeC; // contras present as credit-natural amounts
    sections[key].push({ acct, name: nameOf(state, acct), amount: fromCents(amountC), contra: !!(a && a.contra) });
    sumC[key] += amountC;
    const normal = normalSideOf(a);
    if ((normal === 'D' && closeC < 0) || (normal === 'C' && closeC > 0)) {
      wrongSide.push({ acct, name: nameOf(state, acct), closing: fromCents(closeC), normal });
    }
  }
  const priorResultC = -priorPLc;
  const currentResultC = -currentPLc;
  const retainedC = sumC.retainedAccounts + priorResultC;
  const equityC = sumC.capital + sumC.capitalCalled + sumC.settlementShares + retainedC + currentResultC;
  const assetsNetC = sumC.assets - sumC.accumDep;
  const diffC = assetsNetC - sumC.liabilities - sumC.suspense - equityC;
  const section = (key) => ({ rows: sections[key], total: fromCents(sumC[key]) });
  const warnings = [];
  if (sumC.suspense !== 0) warnings.push({ code: 'suspense-nonzero', msg: 'الحسابات الوسيطة غير مصفّرة — يجب تسويتها' });
  if (wrongSide.length) warnings.push({ code: 'wrong-side', msg: `${wrongSide.length} حساب برصيد عكس طبيعته` });
  if (unclassified.length) warnings.push({ code: 'unclassified', msg: 'حسابات بلا بند في القوائم المالية' });
  if (diffC !== 0) warnings.push({ code: 'bs-unbalanced', msg: 'الميزانية غير متوازنة' });
  return {
    asOf,
    year,
    assets: { rows: sections.assets, gross: fromCents(sumC.assets), accumDepRows: sections.accumDep, accumDep: fromCents(sumC.accumDep), net: fromCents(assetsNetC) },
    liabilities: section('liabilities'),
    suspense: section('suspense'),
    equity: {
      capital: section('capital'),
      capitalCalled: section('capitalCalled'),
      settlementShares: section('settlementShares'),
      retainedAccounts: section('retainedAccounts'),
      priorResults: fromCents(priorResultC),
      retained: fromCents(retainedC),
      currentResult: fromCents(currentResultC),
      total: fromCents(equityC),
    },
    totals: {
      assets: fromCents(assetsNetC),
      liabilities: fromCents(sumC.liabilities),
      suspense: fromCents(sumC.suspense),
      equity: fromCents(equityC),
      liabilitiesAndEquity: fromCents(sumC.liabilities + sumC.suspense + equityC),
    },
    check: {
      assets: fromCents(assetsNetC),
      liabilities: fromCents(sumC.liabilities),
      suspense: fromCents(sumC.suspense),
      equity: fromCents(equityC),
      difference: fromCents(diffC),
      balanced: diffC === 0,
    },
    wrongSide,
    unclassified,
    warnings,
  };
}

// ---------------------------------------------------------------- account statement

/**
 * Account statement with running balance. Opening (everything before `from`) is carried.
 * Rows: { date, no, entryId, n, desc, memo, partyId, docIds, dr, cr, balance, balanceNatural }
 * balance is signed (debit positive); balanceNatural is positive in the account's normal direction.
 */
export function accountStatement({ state, acct, from = null, to = null, year = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const p = periodOf({ year, from, to });
  const code = String(acct);
  const a = coll(state, 'accounts')[code];
  const sign = normalSideOf(a) === 'C' ? -1 : 1;
  const nf = normalizeFilters(state, { ...filters, accounts: [code] });
  const src = lines || postedLines(state, { includeDrafts });
  let openC = 0;
  let run = 0;
  let started = false;
  let totDr = 0;
  let totCr = 0;
  const rows = [];
  for (const l of src) {
    if (p.to && l.date > p.to) continue;
    if (!lineMatches(state, l, nf)) continue;
    if (p.from && l.date < p.from) {
      openC += l.drC - l.crC;
      continue;
    }
    if (!started) {
      run = openC;
      started = true;
    }
    run += l.drC - l.crC;
    totDr += l.drC;
    totCr += l.crC;
    rows.push({
      date: l.date, no: l.no, entryId: l.entryId, n: l.n, status: l.status, desc: l.desc, memo: l.memo, partyId: l.partyId,
      docIds: l.docIds, dr: l.dr, cr: l.cr, balance: fromCents(run), balanceNatural: fromCents(sign * run),
    });
  }
  const closeC = openC + totDr - totCr;
  return {
    acct: code,
    name: a ? a.name : '(حساب غير موجود)',
    normal: normalSideOf(a),
    from: p.from,
    to: p.to,
    opening: fromCents(openC),
    openingNatural: fromCents(sign * openC),
    rows,
    totalDr: fromCents(totDr),
    totalCr: fromCents(totCr),
    closing: fromCents(closeC),
    closingNatural: fromCents(sign * closeC),
  };
}

// ---------------------------------------------------------------- parties

/** Accounts a party is bound to (account-bound mode): boundAccounts, else [defaultAccount]. */
export function boundAccountsOf(party) {
  if (!party) return [];
  if (Array.isArray(party.boundAccounts) && party.boundAccounts.length) return party.boundAccounts.map(String);
  return isNil(party.defaultAccount) ? [] : [String(party.defaultAccount)];
}

const partyName = (state, id) => (coll(state, 'parties')[id] ? coll(state, 'parties')[id].name : id === null ? '(بدون طرف)' : '(طرف غير موجود)');

/**
 * partyStatement({ state, partyId, mode, accounts, from, to, filters })
 *  mode 'line' (default): the lines whose line party is this party (merged parties included).
 *  mode 'account': every line of the accounts bound to the party, whatever the line party is.
 * Rows carry a running signed balance across all accounts; byAccount gives opening/debit/credit/closing.
 */
export function partyStatement({ state, partyId, mode = 'line', accounts = null, from = null, to = null, year = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const p = periodOf({ year, from, to });
  const pid = resolvePartyId(state, partyId);
  const party = coll(state, 'parties')[pid];
  const accts = mode === 'account' ? (accounts && accounts.length ? accounts.map(String) : boundAccountsOf(party)) : (accounts && accounts.length ? accounts.map(String) : null);
  const nf = normalizeFilters(state, { ...filters, accounts: accts && accts.length ? accts : undefined });
  const src = lines || postedLines(state, { includeDrafts });
  let openC = 0;
  let run = 0;
  let started = false;
  let totDr = 0;
  let totCr = 0;
  const rows = [];
  const per = new Map();
  const slot = (acct) => {
    if (!per.has(acct)) per.set(acct, { openC: 0, drC: 0, crC: 0 });
    return per.get(acct);
  };
  for (const l of src) {
    if (p.to && l.date > p.to) continue;
    if (!lineMatches(state, l, nf)) continue;
    if (mode === 'account' && !(accts && accts.length)) continue; // a party with no bound account has no account-bound lines
    if (mode !== 'account' && resolvePartyId(state, l.partyId) !== pid) continue;
    const s = slot(l.acct);
    if (p.from && l.date < p.from) {
      openC += l.drC - l.crC;
      s.openC += l.drC - l.crC;
      continue;
    }
    if (!started) {
      run = openC;
      started = true;
    }
    run += l.drC - l.crC;
    totDr += l.drC;
    totCr += l.crC;
    s.drC += l.drC;
    s.crC += l.crC;
    rows.push({
      date: l.date, no: l.no, entryId: l.entryId, n: l.n, acct: l.acct, accName: nameOf(state, l.acct), desc: l.desc, memo: l.memo,
      partyId: l.partyId, docIds: l.docIds, dr: l.dr, cr: l.cr, balance: fromCents(run),
    });
  }
  const byAccount = [...per.entries()].sort((a, b) => compareCode(a[0], b[0])).map(([acct, s]) => ({
    acct, name: nameOf(state, acct), opening: fromCents(s.openC), debit: fromCents(s.drC), credit: fromCents(s.crC), closing: fromCents(s.openC + s.drC - s.crC),
  }));
  return {
    partyId: pid,
    name: partyName(state, pid),
    mode,
    accounts: accts,
    from: p.from,
    to: p.to,
    opening: fromCents(openC),
    rows,
    totalDr: fromCents(totDr),
    totalCr: fromCents(totCr),
    closing: fromCents(openC + totDr - totCr),
    byAccount,
  };
}

/**
 * partyBalances({ state, asOf, accounts, filters })
 *  accounts: per account, the balance split by LINE party plus the unassigned (no party) remainder;
 *            parties + unassigned always add up to the account total (`ok`).
 *  parties:  per line party, the balance by account.
 *  bound:    per ACCOUNT-BOUND party (party.boundAccounts / defaultAccount): the whole balance of its
 *            accounts regardless of the line party — the workbook's partner statement logic.
 * Signed figures are debit-positive; `balance` on account rows is in the account's normal direction.
 */
export function partyBalances({ state, asOf = null, accounts = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const nf = normalizeFilters(state, { ...filters, accounts: accounts && accounts.length ? accounts : undefined });
  const src = lines || postedLines(state, { includeDrafts });
  const acctMap = new Map(); // acct -> { totalC, parties: Map(pid|null -> c) }
  for (const l of src) {
    if (asOf && l.date > asOf) continue;
    if (!lineMatches(state, l, nf)) continue;
    if (!acctMap.has(l.acct)) acctMap.set(l.acct, { totalC: 0, parties: new Map() });
    const s = acctMap.get(l.acct);
    const pid = resolvePartyId(state, l.partyId);
    const d = l.drC - l.crC;
    s.totalC += d;
    s.parties.set(pid, (s.parties.get(pid) || 0) + d);
  }
  const accountRows = [];
  const partyAgg = new Map(); // pid -> Map(acct -> c)
  for (const [acct, s] of [...acctMap].sort((a, b) => compareCode(a[0], b[0]))) {
    const a = coll(state, 'accounts')[acct];
    const sign = normalSideOf(a) === 'C' ? -1 : 1;
    const partyRows = [];
    let assignedC = 0;
    for (const [pid, c] of s.parties) {
      if (pid === null) continue;
      assignedC += c;
      if (!partyAgg.has(pid)) partyAgg.set(pid, new Map());
      partyAgg.get(pid).set(acct, c);
      partyRows.push({ partyId: pid, name: partyName(state, pid), signed: fromCents(c), balance: fromCents(sign * c) });
    }
    partyRows.sort((x, y) => (x.partyId < y.partyId ? -1 : x.partyId > y.partyId ? 1 : 0));
    const noneC = s.parties.get(null) || 0;
    accountRows.push({
      acct,
      name: nameOf(state, acct),
      normal: normalSideOf(a),
      signed: fromCents(s.totalC),
      total: fromCents(sign * s.totalC),
      parties: partyRows,
      unassigned: fromCents(sign * noneC),
      unassignedSigned: fromCents(noneC),
      ok: assignedC + noneC === s.totalC,
    });
  }
  const partyRows = [...partyAgg].map(([pid, m]) => {
    let t = 0;
    const byAcct = [...m].sort((a, b) => compareCode(a[0], b[0])).map(([acct, c]) => {
      t += c;
      return { acct, name: nameOf(state, acct), signed: fromCents(c) };
    });
    return { partyId: pid, name: partyName(state, pid), total: fromCents(t), byAcct };
  }).sort((a, b) => (a.partyId < b.partyId ? -1 : 1));
  const bound = [];
  for (const [pid, party] of Object.entries(coll(state, 'parties'))) {
    if (!party || !isNil(party.mergedInto)) continue;
    const bas = boundAccountsOf(party);
    if (!bas.length) continue;
    let naturalC = 0;
    const rows = bas.map((acct) => {
      const s = acctMap.get(acct);
      const a = coll(state, 'accounts')[acct];
      const sign = normalSideOf(a) === 'C' ? -1 : 1;
      const c = s ? s.totalC : 0;
      naturalC += sign * c;
      return { acct, name: nameOf(state, acct), balance: fromCents(sign * c), signed: fromCents(c) };
    });
    bound.push({ partyId: pid, name: party.name, accounts: bas, rows, balance: fromCents(naturalC) });
  }
  bound.sort((a, b) => (a.partyId < b.partyId ? -1 : 1));
  return { asOf, accounts: accountRows, parties: partyRows, bound };
}
