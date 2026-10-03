// The ledger primitive: posted lines and balances(from, to, filters). Every report is built on these.
import { fromCents } from '../lib/money.js';
import { isValidISO, fyOf, compareISO } from '../lib/dates.js';
import { coll, pick, isNil, compareCode, cents, resolvePartyId } from './util.js';

function asSet(v) {
  if (isNil(v)) return null;
  const arr = Array.isArray(v) ? v : [v];
  const vals = arr.filter((x) => !isNil(x)).map(String);
  return vals.length ? new Set(vals) : null;
}

/**
 * Normalise report filters:
 *   costCenter | costCenters, sector | sectors, party | parties, accounts | acct (single id or array),
 *   includeFiduciary (default true: lines whose cost center is fiduciary are removed when false).
 */
export function normalizeFilters(state, f = {}) {
  const parties = asSet(f.parties ?? f.party);
  return {
    cc: asSet(f.costCenters ?? f.costCenter),
    sector: asSet(f.sectors ?? f.sector),
    party: parties ? new Set([...parties].map((p) => resolvePartyId(state, p))) : null,
    accounts: asSet(f.accounts ?? f.acct),
    includeFiduciary: f.includeFiduciary !== false,
  };
}

export function lineMatches(state, line, nf) {
  if (nf.accounts && !nf.accounts.has(line.acct)) return false;
  if (nf.cc && !nf.cc.has(String(line.cc))) return false;
  if (nf.sector && !nf.sector.has(String(line.sector))) return false;
  if (nf.party && !nf.party.has(resolvePartyId(state, line.partyId))) return false;
  if (!nf.includeFiduciary) {
    const cc = line.cc !== null ? coll(state, 'costCenters')[line.cc] : null;
    if (cc && cc.kind === 'fiduciary') return false;
  }
  return true;
}

function compareLines(a, b) {
  const c = compareISO(a.date, b.date);
  if (c) return c;
  const na = a.no === null ? Infinity : a.no;
  const nb = b.no === null ? Infinity : b.no;
  if (na !== nb) return na < nb ? -1 : 1;
  if (a.entryId !== b.entryId) return a.entryId < b.entryId ? -1 : 1;
  return a.n - b.n;
}

/**
 * Flat, sorted list of ledger lines (date, entry number, line number). Only posted entries unless
 * includeDrafts is set; void entries never appear. Line dimensions are the effective ones: the line's
 * own value, else the entry header's. Amounts are numbers (dr, cr) plus integer cents (drC, crC).
 */
export function postedLines(state, { includeDrafts = false } = {}) {
  const out = [];
  for (const [entryId, e] of Object.entries(coll(state, 'entries'))) {
    if (!e) continue;
    if (e.status !== 'posted' && !(includeDrafts && e.status === 'draft')) continue;
    if (!isValidISO(e.date)) continue;
    const fy = fyOf(e.date);
    const no = Number.isInteger(e.no) ? e.no : null;
    for (const l of e.lines || []) {
      const drC = cents(l.dr);
      const crC = cents(l.cr);
      const lineDocs = Array.isArray(l.docIds) && l.docIds.length ? l.docIds : e.docIds || [];
      out.push({
        entryId,
        no,
        date: e.date,
        fy,
        status: e.status,
        source: e.source || null,
        isLegacy: !!e.isLegacy,
        desc: e.desc || '',
        n: Number.isInteger(l.n) ? l.n : 0,
        acct: String(l.acct ?? ''),
        dr: fromCents(drC),
        cr: fromCents(crC),
        drC,
        crC,
        memo: l.memo || '',
        partyId: isNil(l.partyId) ? null : l.partyId,
        docIds: lineDocs,
        cc: pick(l.cc, e.cc),
        sector: pick(l.sector, e.sector),
        valueDate: l.valueDate || null,
        needsReview: !!l.needsReview,
        reviewReason: l.reviewReason || '',
        legacy: l.legacy || null,
      });
    }
  }
  out.sort(compareLines);
  return out;
}

/**
 * Core accumulation in integer cents. Returns Map(acct -> {openC, drC, crC}) where openC is the signed
 * (debit - credit) total of every line dated before `from`, and drC/crC the sums within [from, to].
 * from = null means no lower bound (opening is zero); to = null means no upper bound.
 */
export function balanceMap(state, lines, { from = null, to = null, filters = {} } = {}) {
  const nf = normalizeFilters(state, filters);
  const map = new Map();
  for (const l of lines) {
    if (to && l.date > to) continue;
    if (!lineMatches(state, l, nf)) continue;
    let r = map.get(l.acct);
    if (!r) {
      r = { openC: 0, drC: 0, crC: 0 };
      map.set(l.acct, r);
    }
    if (from && l.date < from) r.openC += l.drC - l.crC;
    else {
      r.drC += l.drC;
      r.crC += l.crC;
    }
  }
  return map;
}

/** Build a balances row from a {openC, drC, crC} accumulator (all cents). */
export function makeRow(state, acct, r) {
  const a = coll(state, 'accounts')[acct];
  const closeC = r.openC + r.drC - r.crC;
  return {
    acct,
    name: a ? a.name : '(حساب غير موجود)',
    cls: a ? a.cls || null : null,
    type: a ? a.type || null : null,
    normal: a ? a.normal || null : null,
    known: !!a,
    opening: fromCents(r.openC),
    debit: fromCents(r.drC),
    credit: fromCents(r.crC),
    movement: fromCents(r.drC - r.crC),
    closing: fromCents(closeC),
    closingDr: closeC > 0 ? fromCents(closeC) : 0,
    closingCr: closeC < 0 ? fromCents(-closeC) : 0,
    openingDr: r.openC > 0 ? fromCents(r.openC) : 0,
    openingCr: r.openC < 0 ? fromCents(-r.openC) : 0,
    _openC: r.openC,
    _drC: r.drC,
    _crC: r.crC,
    _closeC: closeC,
  };
}

/**
 * THE primitive. balances({ state, from, to, filters, includeDrafts })
 *   opening = all matching posted lines dated before `from`; debit/credit = totals within [from, to];
 *   closing = opening + debit - credit. Signed figures are debit-positive.
 * Returns { from, to, rows, byAcct, totals } with rows sorted by account code, one row per account that
 * has any opening or movement. totals = sums over rows (cents-exact).
 */
export function balances({ state, from = null, to = null, filters = {}, includeDrafts = false, lines = null } = {}) {
  const src = lines || postedLines(state, { includeDrafts });
  const map = balanceMap(state, src, { from, to, filters });
  const rows = [];
  for (const [acct, r] of map) {
    if (r.openC === 0 && r.drC === 0 && r.crC === 0) continue;
    rows.push(makeRow(state, acct, r));
  }
  rows.sort((a, b) => compareCode(a.acct, b.acct));
  const byAcct = {};
  let t = { openC: 0, drC: 0, crC: 0, closeC: 0, closeDrC: 0, closeCrC: 0 };
  for (const r of rows) {
    byAcct[r.acct] = r;
    t.openC += r._openC;
    t.drC += r._drC;
    t.crC += r._crC;
    t.closeC += r._closeC;
    if (r._closeC > 0) t.closeDrC += r._closeC;
    else t.closeCrC += -r._closeC;
  }
  return {
    from,
    to,
    rows,
    byAcct,
    totals: {
      opening: fromCents(t.openC),
      debit: fromCents(t.drC),
      credit: fromCents(t.crC),
      closing: fromCents(t.closeC),
      closingDr: fromCents(t.closeDrC),
      closingCr: fromCents(t.closeCrC),
    },
  };
}

/** Closing balance (signed, debit-positive, in cents) of one account up to and including `to`. */
export function accountBalanceCents(state, acct, { to = null, filters = {}, lines = null, includeDrafts = false } = {}) {
  const src = lines || postedLines(state, { includeDrafts });
  const m = balanceMap(state, src, { from: null, to, filters: { ...filters, accounts: [acct] } });
  const r = m.get(String(acct));
  return r ? r.drC - r.crC : 0;
}
