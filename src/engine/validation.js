// Entry validation: pure, returns Arabic messages, per-line status chips, errors (block posting) and warnings.
// Hard errors: >= 2 lines, balanced, one-sided positive amounts, postable + active account, allowed period,
// required dimensions (document / cost center / sector), party on `required` accounts (new or edited lines only).
// Legacy lines (unchanged from the stored entry) are flagged for review, never blocked.
import { formatMoney, isMoney } from '../lib/money.js';
import { isValidISO, fyOf } from '../lib/dates.js';
import { MSG } from './constants.js';
import { coll, isNil, pick, cents, normalizeEntry, lineSignature, yearInfo, rulesOf } from './util.js';
import { fromCents } from '../lib/money.js';

const hasText = (s) => typeof s === 'string' && s.trim().length > 0;

/**
 * Period gate shared by validation and the planners.
 * Returns { ok, year, periodState, bump, revision, code?, msg?, note? }.
 *   open -> ok; closed_reserved -> ok only with a reason (bump: revision must be incremented);
 *   locked -> never ok.
 */
export function periodGate(state, year, { reason } = {}) {
  if (!Number.isInteger(year)) {
    return { ok: false, code: 'date-invalid', msg: MSG.DATE_INVALID, year: null, periodState: null, bump: false, revision: 0 };
  }
  const info = yearInfo(state, year);
  if (info.state === 'locked') {
    return { ok: false, code: 'period-locked', msg: MSG.periodLocked(year), year, periodState: 'locked', bump: false, revision: info.revision };
  }
  if (info.state === 'closed_reserved') {
    if (hasText(reason)) {
      return { ok: true, year, periodState: 'closed_reserved', bump: true, revision: info.revision, note: MSG.periodReservedNote(year) };
    }
    return { ok: false, code: 'period-closed', msg: MSG.periodClosed(year), year, periodState: 'closed_reserved', bump: false, revision: info.revision };
  }
  return { ok: true, year, periodState: 'open', bump: false, revision: info.revision };
}

const dupKey = (date, l) => `${date}|${l.acct}|${cents(l.dr)}|${cents(l.cr)}|${isNil(l.partyId) ? '' : l.partyId}`;

/** Index of posted lines by (date, account, debit, credit, party) for the duplicate warning. */
export function buildDupIndex(state) {
  const idx = new Map();
  for (const [id, e] of Object.entries(coll(state, 'entries'))) {
    if (!e || e.status !== 'posted' || !isValidISO(e.date)) continue;
    for (const l of e.lines || []) {
      const k = dupKey(e.date, l);
      if (!idx.has(k)) idx.set(k, new Map());
      idx.get(k).set(id, e.no);
    }
  }
  return idx;
}

// error code -> [status, chip text or null (use the message), priority]
const LINE_CODES = {
  'account-unknown': ['unknown', MSG.UNKNOWN_ACCOUNT, 1],
  'amount-both': ['both', MSG.BOTH_SIDES, 2],
  'amount-zero': ['noamount', MSG.NO_AMOUNT, 3],
  'amount-negative': ['badamount', MSG.AMOUNT_NEGATIVE, 4],
  'amount-invalid': ['badamount', MSG.AMOUNT_INVALID, 4],
  'amount-decimals': ['badamount', MSG.AMOUNT_DECIMALS, 4],
  'account-nonpostable': ['nonpostable', MSG.ACCOUNT_NONPOSTABLE, 5],
  'account-inactive': ['inactive', MSG.ACCOUNT_INACTIVE, 6],
  'dim-missing': ['incomplete', MSG.INCOMPLETE, 7],
  'party-required': ['party', MSG.PARTY_REQUIRED, 8],
  'party-unknown': ['badref', null, 9],
  'doc-unknown': ['badref', null, 9],
  'cc-unknown': ['badref', null, 9],
  'sector-unknown': ['badref', null, 9],
};

/**
 * validateEntry(entry, ctx)
 *  ctx: { state, id, original, reason, dupIndex }
 *    state    engine state (accounts, costCenters, sectors, parties, documents, fiscalYears, entries, config)
 *    id       doc id of the entry being validated (excluded from the duplicate check)
 *    original the stored version when amending: lines unchanged from it are legacy (warnings, not errors)
 *    reason   change reason: lets a closed_reserved year through
 * Returns { ok, canPost, errors, warnings, lines, totals, balanced, year, periodState, suggestedFlags } where
 * errors/warnings are [{ code, msg, line? }] and lines are
 * [{ n, status, chip, ok, missing, errors, warnings, needsReview }].
 */
export function validateEntry(entry, ctx = {}) {
  const state = ctx.state || {};
  const rules = rulesOf(state);
  const e = normalizeEntry(entry);
  const accounts = coll(state, 'accounts');
  const costCenters = coll(state, 'costCenters');
  const sectors = coll(state, 'sectors');
  const parties = coll(state, 'parties');
  const documents = coll(state, 'documents');
  const errors = [];
  const warnings = [];
  const suggestedFlags = [];
  const origByN = new Map();
  if (ctx.original) for (const l of normalizeEntry(ctx.original).lines) origByN.set(l.n, lineSignature(l));

  // ---- period
  const year = isValidISO(e.date) ? fyOf(e.date) : null;
  const gate = periodGate(state, year, { reason: ctx.reason });
  if (!gate.ok) errors.push({ code: gate.code, msg: gate.msg });
  else if (gate.note) warnings.push({ code: 'period-reserved', msg: gate.note });
  if (isValidISO(e.date) && state.config && state.config.company && isValidISO(state.config.company.incorporated)
    && e.date < state.config.company.incorporated) {
    warnings.push({ code: 'before-incorporation', msg: MSG.BEFORE_INCORPORATION });
  }

  // ---- lines
  if (e.lines.length < 2) errors.push({ code: 'lines-min', msg: MSG.LINES_MIN });
  const lineResults = [];
  let drC = 0;
  let crC = 0;
  const fiduciary = { has: false, net: 0 };
  let sharedSector = false;
  const fundingLines = [];

  for (const l of e.lines) {
    const lerr = [];
    const lwarn = [];
    const add = (arr, code, msg, extra = {}) => arr.push({ code, msg, line: l.n, ...extra });
    const changed = !ctx.original || origByN.get(l.n) !== lineSignature(l);
    const acct = accounts[l.acct];

    // amounts
    const drOk = Number.isFinite(l.dr);
    const crOk = Number.isFinite(l.cr);
    if (!drOk || !crOk) add(lerr, 'amount-invalid', MSG.AMOUNT_INVALID);
    else if (l.dr < 0 || l.cr < 0) add(lerr, 'amount-negative', MSG.AMOUNT_NEGATIVE);
    else if (l.dr > 0 && l.cr > 0) add(lerr, 'amount-both', MSG.BOTH_SIDES);
    else if (l.dr === 0 && l.cr === 0) add(lerr, 'amount-zero', MSG.NO_AMOUNT);
    else if (!isMoney(l.dr) || !isMoney(l.cr)) add(lerr, 'amount-decimals', MSG.AMOUNT_DECIMALS);
    if (drOk) drC += cents(l.dr);
    if (crOk) crC += cents(l.cr);

    // account
    if (!acct) add(lerr, 'account-unknown', MSG.UNKNOWN_ACCOUNT);
    else {
      if (acct.postable === false) add(lerr, 'account-nonpostable', MSG.ACCOUNT_NONPOSTABLE);
      if (acct.active === false) {
        if (changed) add(lerr, 'account-inactive', MSG.ACCOUNT_INACTIVE);
        else add(lwarn, 'account-inactive', MSG.ACCOUNT_INACTIVE);
      }
    }

    // required dimensions: line value, else header value
    const docs = l.docIds.length ? l.docIds : e.docIds;
    const cc = pick(l.cc, e.cc);
    const sector = pick(l.sector, e.sector);
    const missing = [];
    if (!docs.length) missing.push('doc');
    if (isNil(cc)) missing.push('cc');
    if (isNil(sector)) missing.push('sector');
    if (missing.length) add(lerr, 'dim-missing', MSG.INCOMPLETE, { missing });
    if (!isNil(cc)) {
      if (!costCenters[cc]) add(lerr, 'cc-unknown', MSG.CC_UNKNOWN);
      else if (costCenters[cc].active === false) add(lwarn, 'cc-inactive', MSG.CC_INACTIVE);
    }
    if (!isNil(sector)) {
      if (!sectors[sector]) add(lerr, 'sector-unknown', MSG.SECTOR_UNKNOWN);
      else {
        if (sectors[sector].active === false) add(lwarn, 'sector-inactive', MSG.SECTOR_INACTIVE);
        if (rules.sharedSectorNames.includes(sectors[sector].name)) sharedSector = true;
      }
    }
    for (const d of docs) if (!documents[d]) { add(lerr, 'doc-unknown', `${MSG.DOC_UNKNOWN} (${d})`); break; }

    // party
    let flagReason = null;
    if (!isNil(l.partyId)) {
      const p = parties[l.partyId];
      if (!p) add(lerr, 'party-unknown', MSG.PARTY_UNKNOWN);
      else if (!isNil(p.mergedInto)) add(lwarn, 'party-merged', MSG.PARTY_MERGED);
    } else if (acct && acct.partyRule === 'required') {
      if (changed) add(lerr, 'party-required', MSG.PARTY_REQUIRED);
      else {
        add(lwarn, 'party-required-legacy', MSG.PARTY_REQUIRED_LEGACY);
        flagReason = MSG.PARTY_REQUIRED_LEGACY;
      }
    } else if (acct && acct.partyRule === 'recommended') {
      add(lwarn, 'party-recommended', MSG.PARTY_RECOMMENDED);
      flagReason = MSG.PARTY_RECOMMENDED;
    }
    let needsReview = l.needsReview;
    if (flagReason && !l.needsReview) {
      suggestedFlags.push({ n: l.n, needsReview: true, reviewReason: flagReason });
      needsReview = true;
    }

    // fiduciary tracking
    if (!isNil(cc) && costCenters[cc] && costCenters[cc].kind === 'fiduciary' && drOk && crOk) {
      fiduciary.has = true;
      fiduciary.net += cents(l.dr) - cents(l.cr);
    }
    if (acct && rules.fundingAccounts.includes(l.acct)) fundingLines.push({ l, docs });

    // chip: the highest-priority error, else «سليم»
    let status = 'ok';
    let chip = MSG.OK;
    if (lerr.length) {
      const best = lerr.slice().sort((a, b) => LINE_CODES[a.code][2] - LINE_CODES[b.code][2])[0];
      const [st, text] = LINE_CODES[best.code];
      status = st;
      chip = text || best.msg;
    }
    errors.push(...lerr);
    warnings.push(...lwarn);
    lineResults.push({
      n: l.n,
      status,
      chip,
      ok: lerr.length === 0,
      missing,
      errors: lerr.map((x) => x.code),
      warnings: lwarn.map((x) => x.code),
      needsReview,
    });
  }

  // ---- balance
  const diffC = drC - crC;
  const balanced = diffC === 0;
  if (!balanced && e.lines.length) {
    const side = diffC > 0 ? MSG.DEBIT_LARGER : MSG.CREDIT_LARGER;
    errors.push({ code: 'unbalanced', msg: `${MSG.UNBALANCED_PREFIX} ${formatMoney(fromCents(Math.abs(diffC)), { parens: false })} (${side})` });
  }

  // ---- entry-level warnings
  if (sharedSector) warnings.push({ code: 'sector-shared', msg: MSG.SECTOR_SHARED });
  if (fiduciary.has && fiduciary.net !== 0) {
    warnings.push({ code: 'fiduciary-imbalance', msg: `${MSG.FIDUCIARY_IMBALANCE} (الفرق ${formatMoney(fromCents(Math.abs(fiduciary.net)), { parens: false })})` });
  }
  const evidenceLines = fundingLines.filter(({ docs }) => !docs.some((d) => documents[d] && rules.evidenceGrades.includes(documents[d].grade)));
  if (evidenceLines.length) {
    warnings.push({ code: 'funding-no-evidence', msg: MSG.FUNDING_NO_EVIDENCE, lines: evidenceLines.map((x) => x.l.n) });
  }
  if (isValidISO(e.date)) {
    const idx = ctx.dupIndex || buildDupIndex(state);
    const refs = new Set();
    for (const l of e.lines) {
      if (!Number.isFinite(l.dr) || !Number.isFinite(l.cr)) continue;
      const hit = idx.get(dupKey(e.date, l));
      if (!hit) continue;
      for (const [id, no] of hit) if (id !== ctx.id) refs.add(no);
    }
    if (refs.size) warnings.push({ code: 'possible-duplicate', msg: MSG.POSSIBLE_DUPLICATE, refs: [...refs].sort((a, b) => a - b) });
  }

  return {
    ok: errors.length === 0,
    canPost: errors.length === 0,
    errors,
    warnings,
    lines: lineResults,
    totals: { dr: fromCents(drC), cr: fromCents(crC), difference: fromCents(Math.abs(diffC)), side: diffC > 0 ? 'D' : diffC < 0 ? 'C' : null },
    balanced,
    year,
    periodState: gate.periodState,
    suggestedFlags,
  };
}

