// Amendment planners: controlled edit with history snapshots, void, reversal, and the fiscal-year lifecycle
// (close with a trial-balance snapshot, reopen, lock, unlock). All pure; see posting.js for the plan shape.
import { formatMoney, fromCents, toCents } from '../lib/money.js';
import { isValidISO, fyOf, yearStart, yearEnd, todayISO } from '../lib/dates.js';
import { MSG } from './constants.js';
import {
  coll, normalizeEntry, stampOf, clone, stripHistory, yearInfo, byteSize, rulesOf, totalsCents, compareCode,
} from './util.js';
import { validateEntry, periodGate } from './validation.js';
import { fail, err, planPost, applyFlags, everUsedWrites, linkWrites, linkKeysOf } from './posting.js';
import { trialBalance, incomeStatement } from './statements.js';

const hasText = (s) => typeof s === 'string' && s.trim().length > 0;

/** Look up a posted entry and run the shared mandatory checks (status, reason, optimistic version). */
function loadPosted(state, { id, reason, expectedVersion }, { needVersion = true } = {}) {
  const old = coll(state, 'entries')[id];
  if (!old) return { plan: fail(err('not-found', MSG.NOT_FOUND)) };
  if (old.status === 'void') return { plan: fail(err('entry-void', MSG.ENTRY_VOID)) };
  if (old.status !== 'posted') return { plan: fail(err('not-posted', MSG.ENTRY_NOT_POSTED)) };
  if (!hasText(reason)) return { plan: fail(err('reason-required', MSG.REASON_REQUIRED)) };
  if (needVersion) {
    if (!Number.isInteger(expectedVersion)) return { plan: fail(err('version-required', MSG.VERSION_REQUIRED)) };
    if (expectedVersion !== (old.version || 1)) return { plan: fail(err('version-conflict', MSG.VERSION_CONFLICT)) };
  }
  return { old: normalizeEntry(old) };
}

/** Period gates for every distinct year touched; returns { gates } or { plan } when one refuses. */
function gateYears(state, years, reason) {
  const gates = [];
  for (const y of new Set(years)) {
    const g = periodGate(state, y, { reason });
    if (!g.ok) return { plan: fail(err(g.code, g.msg)) };
    gates.push(g);
  }
  return { gates };
}
const revisionWrites = (gates) => gates.filter((g) => g.bump).map((g) => ({ op: 'update', path: `fiscalYears/${g.year}`, data: { revision: g.revision + 1 } }));

/** Content signature for "nothing changed" detection (history, version and stamps excluded). */
function contentSig(e) {
  return JSON.stringify({
    date: e.date, desc: e.desc, docIds: e.docIds, cc: e.cc, sector: e.sector,
    lines: e.lines.map((l) => [l.acct, l.dr, l.cr, l.memo, l.partyId, l.docIds, l.cc, l.sector, l.valueDate, l.needsReview, l.reviewReason, l.links]),
  });
}

/**
 * planAmend(state, { id, entry | changes, reason, expectedVersion, user, now, extraWrites })
 * Edit a posted entry. `entry` is the full new content, `changes` a partial merged over the stored entry.
 * Needs a non-empty reason and the version the editor loaded (optimistic check). Pushes a history snapshot
 * { v: newVersion, at, by, kind: 'amend', reason, before: <previous entry minus history> }, bumps version, keeps the
 * number, status and creation stamps. Locked years refuse; closed_reserved years record `periodState` in the
 * history item and bump the year revision (both years when the date moves between years).
 */
export function planAmend(state, params = {}) {
  const { id, reason, expectedVersion, user = null, now, extraWrites = [] } = params;
  const loaded = loadPosted(state, { id, reason, expectedVersion });
  if (loaded.plan) return loaded.plan;
  const old = loaded.old;
  const stored = coll(state, 'entries')[id];
  const incoming = params.entry || params.changes;
  if (!incoming) return fail(err('no-changes', MSG.NO_CHANGES));
  const stamp = stampOf(now);
  const merged = normalizeEntry({ ...stored, ...incoming, lines: incoming.lines || stored.lines });
  if (contentSig(merged) === contentSig(old)) return fail(err('no-changes', MSG.NO_CHANGES));

  const gated = gateYears(state, [fyOf(old.date), merged.fy], reason);
  if (gated.plan) return gated.plan;
  const validation = validateEntry(merged, { state, id, original: old, reason });
  if (!validation.ok) return fail(validation.errors, { validation });

  applyFlags(merged.lines, validation.suggestedFlags);
  const reserved = gated.gates.some((g) => g.periodState === 'closed_reserved');
  const item = { v: old.version + 1, at: stamp, by: user, kind: 'amend', reason: reason.trim(), before: stripHistory(old) };
  if (reserved) item.periodState = 'closed_reserved';
  const doc = {
    ...merged,
    no: old.no,
    status: 'posted',
    isLegacy: old.isLegacy,
    legacyRow: old.legacyRow,
    source: old.source,
    reversalOf: old.reversalOf,
    voidReason: null,
    createdBy: old.createdBy,
    createdAt: old.createdAt,
    postedBy: old.postedBy,
    postedAt: old.postedAt,
    version: old.version + 1,
    history: [...old.history, item],
  };
  if (byteSize(doc) > rulesOf(state).maxEntryBytes) return fail(err('entry-too-large', MSG.ENTRY_TOO_LARGE));
  const extra = extraWrites.map((w) => ({ ...w, data: w.data === undefined ? undefined : clone(w.data) }));
  const writes = [{ op: 'set', path: `entries/${id}`, data: doc }];
  writes.push(...revisionWrites(gated.gates));
  writes.push(...everUsedWrites(state, doc.lines));
  writes.push(...linkWrites(state, doc.lines, old.no, linkKeysOf(old.lines), extra));
  writes.push(...extra);
  return {
    ok: true,
    id,
    writes,
    audit: { kind: 'amend', coll: 'entries', id, reason: reason.trim(), summary: `تعديل القيد رقم ${old.no} (النسخة ${doc.version})` },
    errors: [],
    entry: { id, ...doc },
    validation,
    warnings: validation.warnings,
  };
}

/**
 * planVoid(state, { id, reason, expectedVersion, user, now })
 * Marks a posted entry void: it keeps its number, disappears from every report, history keeps the snapshot.
 * A posted depreciation run pointing at the entry goes back to 'proposed'.
 */
export function planVoid(state, params = {}) {
  const { id, reason, expectedVersion, user = null, now } = params;
  const loaded = loadPosted(state, { id, reason, expectedVersion });
  if (loaded.plan) return loaded.plan;
  const old = loaded.old;
  const gated = gateYears(state, [fyOf(old.date)], reason);
  if (gated.plan) return gated.plan;
  const stamp = stampOf(now);
  const item = { v: old.version + 1, at: stamp, by: user, kind: 'void', reason: reason.trim(), before: stripHistory(old) };
  if (gated.gates.some((g) => g.periodState === 'closed_reserved')) item.periodState = 'closed_reserved';
  const doc = { ...old, status: 'void', voidReason: reason.trim(), version: old.version + 1, history: [...old.history, item] };
  const writes = [{ op: 'set', path: `entries/${id}`, data: doc }, ...revisionWrites(gated.gates)];
  for (const [y, run] of Object.entries(coll(state, 'depRuns'))) {
    if (run && run.status === 'posted' && run.postedEntryNo === old.no) {
      writes.push({ op: 'update', path: `depRuns/${y}`, data: { status: 'proposed', postedEntryNo: null } });
    }
  }
  return {
    ok: true,
    id,
    writes,
    audit: { kind: 'void', coll: 'entries', id, reason: reason.trim(), summary: `إلغاء القيد رقم ${old.no} (يحتفظ برقمه)` },
    errors: [],
    entry: { id, ...doc },
  };
}

/**
 * planReverse(state, { id, reason, date, no, user, now })  (`no`: the number allocated by the repo, see planPost)
 * Posts a new entry (source 'reversal', reversalOf = id) with every line's sides swapped, dated in the period
 * where the correction belongs (default today). The original stays posted. This is the fix for a locked year:
 * date the reversal in an open period. Legacy exceptions on the original (e.g. a missing required party) do not
 * block the reversal.
 */
export function planReverse(state, params = {}) {
  const { id, reason, user = null, now } = params;
  const old0 = coll(state, 'entries')[id];
  if (!old0) return fail(err('not-found', MSG.NOT_FOUND));
  if (old0.status === 'void') return fail(err('entry-void', MSG.ENTRY_VOID));
  if (old0.status !== 'posted') return fail(err('not-posted', MSG.ENTRY_NOT_POSTED));
  if (!hasText(reason)) return fail(err('reason-required', MSG.REASON_REQUIRED));
  const date = params.date || todayISO();
  if (!isValidISO(date)) return fail(err('date-invalid', MSG.DATE_INVALID));
  for (const e of Object.values(coll(state, 'entries'))) {
    if (e && e.reversalOf === id && e.status !== 'void') return fail(err('already-reversed', MSG.ALREADY_REVERSED));
  }
  const old = normalizeEntry(old0);
  const rev = {
    ...old,
    id: undefined,
    no: null,
    date,
    status: 'draft',
    desc: `عكس القيد رقم ${old.no}${old.desc ? ` — ${old.desc}` : ''}`,
    source: 'reversal',
    reversalOf: id,
    isLegacy: false,
    legacyRow: null,
    voidReason: null,
    version: 1,
    history: [],
    createdBy: user,
    createdAt: null,
    lines: old.lines.map((l) => ({
      ...l, dr: l.cr, cr: l.dr, needsReview: false, reviewReason: '', links: [], legacy: null,
    })),
  };
  const plan = planPost(state, { entry: rev, no: params.no, user, now, reason: reason.trim(), original: rev });
  if (!plan.ok) return plan;
  plan.audit = {
    kind: 'reverse', coll: 'entries', id: plan.id, reason: reason.trim(),
    summary: `عكس القيد رقم ${old.no} بالقيد رقم ${plan.entryNo} (${formatMoney(fromCents(totalsCents(old.lines).dr), { parens: false })})`,
  };
  return plan;
}

// ------------------------------------------------------------------ fiscal-year lifecycle

function fiscalYearDefaults(y) {
  return {
    year: y, state: 'open', startDate: yearStart(y), endDate: yearEnd(y), legalStart: null,
    reservation: { sources: '', notRecorded: '', text: '', lastUpdate: null }, revision: 0, snapshot: null, neededDocs: [],
    closedAt: null, closedBy: null,
  };
}

const validYear = (y) => (Number.isInteger(Number(y)) && Number(y) >= 1900 && Number(y) <= 2200 && /^\d{4}$/.test(String(y)) ? Number(y) : null);

/** Cumulative trial balance at year end as the snapshot stored in fiscalYears/<y>.snapshot. */
function takeSnapshot(state, y, stamp) {
  const tb = trialBalance({ state, mode: 'cumulative', asOf: yearEnd(y) });
  return {
    tb,
    snapshot: {
      takenAt: stamp,
      revision: yearInfo(state, y).revision,
      totals: { dr: tb.totals.closingDr, cr: tb.totals.closingCr },
      tb: tb.rows.filter((r) => r.closing !== 0).map((r) => ({ acct: r.acct, dr: r.closingDr, cr: r.closingCr })),
      netResult: incomeStatement({ state, year: y }).netResult,
    },
  };
}
function checklistFor(state, y, tb) {
  const items = [];
  const drafts = Object.values(coll(state, 'entries')).filter((e) => e && e.status === 'draft' && fyOf(e.date) === y).length;
  items.push({ key: 'drafts', ok: drafts === 0, level: drafts ? 'error' : 'info', msg: drafts ? `${drafts} مسودة مؤرخة في السنة` : 'لا توجد مسودات' });
  items.push({ key: 'tb', ok: tb.balanced, level: tb.balanced ? 'info' : 'error', msg: tb.balanced ? 'ميزان المراجعة متوازن' : MSG.TB_UNBALANCED });
  const susp = tb.rows.filter((r) => {
    const a = coll(state, 'accounts')[r.acct];
    return a && a.fsLine === 'SUSPENSE' && r.closing !== 0;
  });
  items.push({ key: 'suspense', ok: susp.length === 0, level: susp.length ? 'warn' : 'info', msg: susp.length ? 'الحسابات الوسيطة غير مصفّرة' : 'الحسابات الوسيطة مصفّرة' });
  if (Object.keys(coll(state, 'assets')).length) {
    const run = coll(state, 'depRuns')[y];
    const posted = !!run && run.status === 'posted';
    items.push({ key: 'depreciation', ok: posted, level: posted ? 'info' : 'warn', msg: posted ? 'قيد الإهلاك مرحَّل' : 'قيد الإهلاك غير مرحَّل لهذه السنة' });
  }
  const openItems = Object.values(coll(state, 'openItems')).filter((i) => i && (i.status === 'open' || i.status === 'partial' || i.status === 'inquiry')).length;
  items.push({ key: 'openItems', ok: openItems === 0, level: 'info', msg: `${openItems} بند مفتوح في السجل` });
  return items;
}

/**
 * planCloseYear(state, { year, user, now, reservation, neededDocs, allowDrafts })
 * open -> closed_reserved ("closed with reservations"). Takes a cumulative trial-balance snapshot at year end
 * (fiscalYears/<y>.snapshot = { takenAt, totals:{dr,cr}, tb:[{acct,dr,cr}], netResult }) so the UI can show
 * "live versus as closed". Refuses when drafts dated in the year exist (unless allowDrafts) or the TB is out.
 */
export function planCloseYear(state, params = {}) {
  const { user = null, now, reservation, neededDocs, allowDrafts = false } = params;
  const y = validYear(params.year);
  if (y === null) return fail(err('year-invalid', MSG.YEAR_INVALID));
  const info = yearInfo(state, y);
  if (info.state !== 'open') return fail(err('year-already-closed', MSG.YEAR_ALREADY_CLOSED));
  const stamp = stampOf(now);
  const { tb, snapshot } = takeSnapshot(state, y, stamp);
  const checklist = checklistFor(state, y, tb);
  const drafts = checklist.find((c) => c.key === 'drafts');
  if (!drafts.ok && !allowDrafts) return fail(err('drafts-pending', MSG.DRAFTS_PENDING), { checklist });
  if (!tb.balanced) return fail(err('tb-unbalanced', MSG.TB_UNBALANCED), { checklist });
  const base = info.doc ? clone(info.doc) : fiscalYearDefaults(y);
  const doc = {
    ...base,
    state: 'closed_reserved',
    closedAt: stamp,
    closedBy: user,
    revision: info.revision,
    snapshot,
  };
  if (reservation) doc.reservation = { ...base.reservation, ...reservation };
  if (Array.isArray(neededDocs)) doc.neededDocs = neededDocs;
  return {
    ok: true,
    writes: [{ op: 'set', path: `fiscalYears/${y}`, data: doc }],
    audit: { kind: 'close', coll: 'fiscalYears', id: String(y), reason: '', summary: `إقفال سنة ${y} بتحفظ` },
    errors: [],
    checklist,
    snapshot,
  };
}

/** planReopenYear(state, { year, reason, isOwner, user, now }) — closed_reserved -> open; owner only, reason required, revision + 1. */
export function planReopenYear(state, params = {}) {
  const { reason, isOwner = false, user = null, now } = params;
  const y = validYear(params.year);
  if (y === null) return fail(err('year-invalid', MSG.YEAR_INVALID));
  if (isOwner !== true) return fail(err('owner-only', MSG.OWNER_ONLY));
  if (!hasText(reason)) return fail(err('reason-required', MSG.REASON_REQUIRED));
  const info = yearInfo(state, y);
  if (info.state === 'locked') return fail(err('unlock-first', MSG.YEAR_LOCKED_UNLOCK_FIRST));
  if (info.state === 'open') return fail(err('year-already-open', MSG.YEAR_ALREADY_OPEN));
  const stamp = stampOf(now);
  const doc = { ...clone(info.doc), state: 'open', revision: info.revision + 1, reopenedAt: stamp, reopenedBy: user, reopenReason: reason.trim() };
  return {
    ok: true,
    writes: [{ op: 'set', path: `fiscalYears/${y}`, data: doc }],
    audit: { kind: 'reopen', coll: 'fiscalYears', id: String(y), reason: reason.trim(), summary: `إعادة فتح سنة ${y} (المراجعة ${doc.revision})` },
    errors: [],
  };
}

/** planLockYear(state, { year, user, now }) — closed_reserved -> locked; refreshes the snapshot so integrity can compare against it. */
export function planLockYear(state, params = {}) {
  const { user = null, now } = params;
  const y = validYear(params.year);
  if (y === null) return fail(err('year-invalid', MSG.YEAR_INVALID));
  const info = yearInfo(state, y);
  if (info.state === 'locked') return fail(err('year-already-locked', MSG.YEAR_ALREADY_CLOSED));
  if (info.state === 'open') return fail(err('close-first', MSG.CLOSE_FIRST));
  const stamp = stampOf(now);
  const { tb, snapshot } = takeSnapshot(state, y, stamp);
  if (!tb.balanced) return fail(err('tb-unbalanced', MSG.TB_UNBALANCED));
  const doc = { ...clone(info.doc), state: 'locked', lockedAt: stamp, lockedBy: user, snapshot };
  return {
    ok: true,
    writes: [{ op: 'set', path: `fiscalYears/${y}`, data: doc }],
    audit: { kind: 'lock', coll: 'fiscalYears', id: String(y), reason: '', summary: `قفل سنة ${y} نهائياً` },
    errors: [],
    snapshot,
  };
}

/** planUnlockYear(state, { year, reason, isOwner, user, now }) — locked -> closed_reserved; owner only, reason required, revision + 1. */
export function planUnlockYear(state, params = {}) {
  const { reason, isOwner = false, user = null, now } = params;
  const y = validYear(params.year);
  if (y === null) return fail(err('year-invalid', MSG.YEAR_INVALID));
  if (isOwner !== true) return fail(err('owner-only', MSG.OWNER_ONLY));
  if (!hasText(reason)) return fail(err('reason-required', MSG.REASON_REQUIRED));
  const info = yearInfo(state, y);
  if (info.state !== 'locked') return fail(err('year-not-locked', MSG.YEAR_NOT_LOCKED));
  const stamp = stampOf(now);
  const doc = { ...clone(info.doc), state: 'closed_reserved', revision: info.revision + 1, unlockedAt: stamp, unlockedBy: user, unlockReason: reason.trim() };
  return {
    ok: true,
    writes: [{ op: 'set', path: `fiscalYears/${y}`, data: doc }],
    audit: { kind: 'unlock', coll: 'fiscalYears', id: String(y), reason: reason.trim(), summary: `فك قفل سنة ${y} (المراجعة ${doc.revision})` },
    errors: [],
  };
}

// ------------------------------------------------------------------ year status helpers (read-only)

/** closeChecklist(state, year) -> [{ key, ok, level, msg }]: what to look at before closing a year. */
export function closeChecklist(state, year) {
  const y = validYear(year);
  if (y === null) return [];
  return checklistFor(state, y, trialBalance({ state, mode: 'cumulative', asOf: yearEnd(y) }));
}

/**
 * changesSinceClose(state, year) -> [{ id, no, version, kind, at, by, reason, periodState }] oldest first:
 * every posting, amendment or void of an entry dated in the year recorded after the year's snapshot was taken.
 */
export function changesSinceClose(state, year) {
  const y = validYear(year);
  const doc = y === null ? null : yearInfo(state, y).doc;
  const since = doc ? Date.parse((doc.snapshot && doc.snapshot.takenAt) || doc.closedAt) : NaN;
  if (!Number.isFinite(since)) return [];
  const out = [];
  for (const [id, e] of Object.entries(coll(state, 'entries'))) {
    if (!e || e.fy !== y || (e.status !== 'posted' && e.status !== 'void')) continue;
    const items = (e.history || []).filter((h) => h && Date.parse(h.at) > since);
    for (const h of items) out.push({ id, no: e.no, version: h.v, kind: h.kind, at: h.at, by: h.by, reason: h.reason || '', periodState: h.periodState || null });
    const hasPost = (e.history || []).some((h) => h && h.kind === 'post');
    if (!hasPost && Date.parse(e.postedAt) > since) out.push({ id, no: e.no, version: 1, kind: 'post', at: e.postedAt, by: e.postedBy, reason: '', periodState: null });
  }
  return out.sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : a.no - b.no));
}

/**
 * snapshotDiff(state, year) -> { year, takenAt, netResult: {snapshot, live, difference}, rows, differs }
 * "Live versus as closed": per account, the cumulative year-end balance now against the stored snapshot; rows only
 * for accounts that differ (difference = live - snapshot, debit-positive).
 */
export function snapshotDiff(state, year) {
  const y = validYear(year);
  const doc = y === null ? null : yearInfo(state, y).doc;
  if (!doc || !doc.snapshot) return { year: y, takenAt: null, netResult: null, rows: [], differs: false, hasSnapshot: false };
  const live = trialBalance({ state, mode: 'cumulative', asOf: yearEnd(y) });
  const snap = new Map((doc.snapshot.tb || []).map((r) => [String(r.acct), toCents(r.dr) - toCents(r.cr)]));
  const now = new Map(live.rows.filter((r) => r.closing !== 0).map((r) => [r.acct, toCents(r.closing)]));
  const rows = [];
  for (const k of [...new Set([...snap.keys(), ...now.keys()])].sort((a, b) => compareCode(a, b))) {
    const a = snap.get(k) || 0;
    const b = now.get(k) || 0;
    if (a !== b) rows.push({ acct: k, name: (coll(state, 'accounts')[k] || {}).name || '(حساب غير موجود)', snapshot: fromCents(a), live: fromCents(b), difference: fromCents(b - a) });
  }
  const liveNet = incomeStatement({ state, year: y }).netResult;
  const snapNet = Number.isFinite(doc.snapshot.netResult) ? doc.snapshot.netResult : null;
  return {
    year: y,
    takenAt: doc.snapshot.takenAt,
    hasSnapshot: true,
    netResult: { snapshot: snapNet, live: liveNet, difference: snapNet === null ? null : fromCents(toCents(liveNet) - toCents(snapNet)) },
    rows,
    differs: rows.length > 0,
  };
}
