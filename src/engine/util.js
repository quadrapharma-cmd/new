// Internal helpers shared by the engine modules (not re-exported by the barrel except where noted).
import { toCents, parseAmount } from '../lib/money.js';
import { isValidISO, fyOf } from '../lib/dates.js';
import { DEFAULT_RULES } from './constants.js';

const EMPTY = Object.freeze({});

/** state[name] or a frozen empty object, so engine code never trips over a missing collection. */
export const coll = (state, name) => (state && state[name]) || EMPTY;

export const isNil = (v) => v === null || v === undefined || v === '';
/** First non-empty of (a, b): the effective value of a line dimension (line overrides header). */
export const pick = (a, b) => (isNil(a) ? (isNil(b) ? null : b) : a);

/** Sort account codes numerically when both are numeric, else as text. */
export function compareCode(a, b) {
  const na = /^\d+$/.test(a);
  const nb = /^\d+$/.test(b);
  if (na && nb) {
    if (a.length !== b.length) return a.length - b.length;
  }
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Numbered entry doc id: 312 -> 'e000312'. */
export const entryIdFor = (no) => `e${String(no).padStart(6, '0')}`;
export const isDraftId = (id) => /^d_[a-z0-9]+_[a-z0-9]+$/.test(String(id));

export function cents(x) {
  if (x === null || x === undefined || x === '') return 0;
  if (typeof x === 'string') {
    const p = parseAmount(x);
    return p === null ? 0 : toCents(p);
  }
  return Number.isFinite(x) ? toCents(x) : 0;
}

/** Amount as a finite number, or NaN when it cannot be read (null/''/undefined count as 0). */
export function amountOf(x) {
  if (x === null || x === undefined || x === '') return 0;
  if (typeof x === 'number') return x;
  if (typeof x === 'string') {
    const p = parseAmount(x);
    return p === null ? NaN : p;
  }
  return NaN;
}

export const clone = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));

/** Entry minus its history (what history snapshots store as `before`). */
export function stripHistory(entry) {
  const { history, ...rest } = entry;
  return clone(rest);
}

export function byteSize(obj) {
  const s = JSON.stringify(obj) ?? '';
  return typeof TextEncoder !== 'undefined' ? new TextEncoder().encode(s).length : s.length * 2;
}

/** meta/config.rules merged over the defaults. */
export function rulesOf(state) {
  const r = (state && state.config && state.config.rules) || {};
  return { ...DEFAULT_RULES, ...r, accrualAccountOf: { ...DEFAULT_RULES.accrualAccountOf, ...(r.accrualAccountOf || {}) } };
}

/** Follow party merges (mergedInto chain, cycle-safe) to the surviving party id. */
export function resolvePartyId(state, id) {
  if (isNil(id)) return null;
  const parties = coll(state, 'parties');
  let cur = id;
  const seen = new Set();
  while (parties[cur] && !isNil(parties[cur].mergedInto) && !seen.has(cur)) {
    seen.add(cur);
    cur = parties[cur].mergedInto;
  }
  return cur;
}

/** { state: 'open' | 'closed_reserved' | 'locked', doc, revision } for a fiscal year (missing doc = open). */
export function yearInfo(state, year) {
  const doc = coll(state, 'fiscalYears')[year] || coll(state, 'fiscalYears')[String(year)] || null;
  return { state: (doc && doc.state) || 'open', doc, revision: (doc && Number.isFinite(doc.revision) ? doc.revision : 0) };
}

/** Max entry number among posted/void entries (0 when none). */
export function maxEntryNo(state) {
  let max = 0;
  for (const e of Object.values(coll(state, 'entries'))) {
    if (e && (e.status === 'posted' || e.status === 'void') && Number.isInteger(e.no) && e.no > max) max = e.no;
  }
  return max;
}

/** Normalise one line to the stored shape (amounts stay as typed numbers; NaN marks unreadable input). */
export function normalizeLine(line, idx) {
  const l = line || {};
  return {
    n: Number.isInteger(l.n) && l.n > 0 ? l.n : idx + 1,
    acct: isNil(l.acct) ? '' : String(l.acct).trim(),
    dr: amountOf(l.dr),
    cr: amountOf(l.cr),
    memo: isNil(l.memo) ? '' : String(l.memo),
    partyId: isNil(l.partyId) ? null : l.partyId,
    docIds: Array.isArray(l.docIds) ? l.docIds.slice() : [],
    cc: isNil(l.cc) ? null : l.cc,
    sector: isNil(l.sector) ? null : l.sector,
    valueDate: isNil(l.valueDate) ? null : l.valueDate,
    needsReview: !!l.needsReview,
    reviewReason: isNil(l.reviewReason) ? '' : String(l.reviewReason),
    links: Array.isArray(l.links) ? l.links.map((k) => ({ t: k.t, n: k.n })) : [],
    legacy: l.legacy ? clone(l.legacy) : null,
  };
}

/** Make line numbers unique: keep valid distinct n, otherwise assign the next free number. */
function uniqueNumbers(lines) {
  const used = new Set();
  let max = lines.reduce((m, l) => Math.max(m, l.n), 0);
  for (const l of lines) {
    if (used.has(l.n)) l.n = ++max;
    used.add(l.n);
  }
  return lines;
}

/** Normalise an entry (draft-shaped or stored) to the stored shape; does not decide status/number. */
export function normalizeEntry(entry) {
  const e = entry || {};
  const lines = uniqueNumbers((Array.isArray(e.lines) ? e.lines : []).map(normalizeLine));
  return {
    no: Number.isInteger(e.no) ? e.no : null,
    date: isValidISO(e.date) ? e.date : isNil(e.date) ? '' : e.date,
    fy: isValidISO(e.date) ? fyOf(e.date) : null,
    status: e.status || 'draft',
    desc: isNil(e.desc) ? '' : String(e.desc),
    docIds: Array.isArray(e.docIds) ? e.docIds.slice() : [],
    cc: isNil(e.cc) ? null : e.cc,
    sector: isNil(e.sector) ? null : e.sector,
    source: e.source || 'user',
    isLegacy: !!e.isLegacy,
    legacyRow: Number.isInteger(e.legacyRow) ? e.legacyRow : null,
    version: Number.isInteger(e.version) && e.version > 0 ? e.version : 1,
    voidReason: isNil(e.voidReason) ? null : e.voidReason,
    reversalOf: isNil(e.reversalOf) ? null : e.reversalOf,
    createdBy: isNil(e.createdBy) ? null : e.createdBy,
    createdAt: isNil(e.createdAt) ? null : e.createdAt,
    postedBy: isNil(e.postedBy) ? null : e.postedBy,
    postedAt: isNil(e.postedAt) ? null : e.postedAt,
    lines,
    history: Array.isArray(e.history) ? clone(e.history) : [],
  };
}

/** Material fields of a line, for "was this line edited?" comparisons. */
export function lineSignature(l) {
  return JSON.stringify([
    l.acct, cents(l.dr), cents(l.cr), l.memo || '', l.partyId || null, l.cc || null, l.sector || null,
    (l.docIds || []).slice().sort(), l.valueDate || null,
  ]);
}

export function totalsCents(lines) {
  let dr = 0;
  let cr = 0;
  for (const l of lines) {
    dr += cents(l.dr);
    cr += cents(l.cr);
  }
  return { dr, cr, diff: dr - cr };
}

/** ISO timestamp string for audit stamps. */
export function stampOf(now) {
  if (typeof now === 'string' && now) return now;
  if (now instanceof Date) return now.toISOString();
  if (typeof now === 'number') return new Date(now).toISOString();
  return new Date().toISOString();
}
