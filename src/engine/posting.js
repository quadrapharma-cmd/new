// Posting planners. Every planner is PURE: it reads `state` and returns a plan
//   { ok, writes: [{ op: 'set'|'update'|'delete', path, data? }], audit: { kind, coll, id, reason?, summary } | null,
//     entryNo?, errors: [{ code, msg }], ... }
// that src/data/repo.js applies sequentially. `entryNo` is set ONLY by planners that create a numbered entry (post,
// reverse, depreciation post): the repo allocates the number under its lease on meta/counters, passes it in as
// `params.no`, and bumps the counter itself, so plans never write meta/counters. When ok is false the writes are
// empty and `errors` explains why.
import { formatMoney, fromCents } from '../lib/money.js';
import { MSG } from './constants.js';
import {
  coll, isNil, normalizeEntry, entryIdFor, isDraftId, maxEntryNo, stampOf, clone, totalsCents,
} from './util.js';
import { validateEntry, periodGate } from './validation.js';

export { entryIdFor };

/** Plan returned when something is refused. */
export function fail(errors, extra = {}) {
  const list = Array.isArray(errors) ? errors : [errors];
  return { ok: false, writes: [], audit: null, errors: list, ...extra };
}
export const err = (code, msg, extra = {}) => ({ code, msg, ...extra });

/** Next entry number: max(posted/void numbers) + 1, gap-free. Drafts have no number. */
export function nextEntryNo(state) {
  return maxEntryNo(state) + 1;
}

/** True when a posted/void entry already carries this number. */
function numberTaken(state, no) {
  for (const e of Object.values(coll(state, 'entries'))) {
    if (e && (e.status === 'posted' || e.status === 'void') && e.no === no) return true;
  }
  return false;
}

function newDraftId(stamp, rand) {
  const t = Number.isFinite(Date.parse(stamp)) ? Date.parse(stamp) : Date.now();
  let r = (typeof rand === 'function' ? rand() : Math.random()).toString(36).replace(/[^a-z0-9]/g, '');
  r = (r + 'xxxx').slice(0, 4).padEnd(4, 'x');
  return `d_${t.toString(36)}_${r}`;
}

/**
 * planSaveDraft(state, { entry, user, now, rand, extraWrites })
 * Saves an entry as a draft (no number, never validated for posting, never audited: autosave noise).
 * entry.id may name an existing draft; a new draft gets id d_<base36 time>_<rand>.
 */
export function planSaveDraft(state, { entry, user = null, now, rand, extraWrites = [] } = {}) {
  if (!entry || typeof entry !== 'object') return fail(err('entry-required', MSG.NOT_FOUND));
  const stamp = stampOf(now);
  const entries = coll(state, 'entries');
  const existing = entry.id ? entries[entry.id] : null;
  if (existing && existing.status !== 'draft') return fail(err('draft-only', MSG.DRAFT_ONLY));
  if (entry.id && !existing && !isDraftId(entry.id)) return fail(err('draft-only', MSG.DRAFT_ONLY));
  if (entry.status === 'posted' || entry.status === 'void') return fail(err('draft-only', MSG.DRAFT_ONLY));
  const id = entry.id || newDraftId(stamp, rand);
  const e = normalizeEntry(entry);
  // unreadable amounts (NaN) are not storable JSON numbers: a draft keeps them as 0 and validation reports them
  e.lines = e.lines.map((l) => ({ ...l, dr: Number.isFinite(l.dr) ? l.dr : 0, cr: Number.isFinite(l.cr) ? l.cr : 0 }));
  const doc = {
    ...e,
    no: null,
    status: 'draft',
    version: 1,
    history: [],
    voidReason: null,
    postedBy: null,
    postedAt: null,
    createdBy: (existing && existing.createdBy) || e.createdBy || user,
    createdAt: (existing && existing.createdAt) || e.createdAt || stamp,
  };
  return {
    ok: true,
    id,
    writes: [{ op: 'set', path: `entries/${id}`, data: doc }, ...extraWrites.map((w) => ({ ...w, data: w.data === undefined ? undefined : clone(w.data) }))],
    audit: null,
    errors: [],
    entry: { id, ...doc },
    validation: validateEntry(doc, { state, id }),
  };
}

/** planDeleteDraft(state, { id, user, now }) — drafts are hard-deletable (audited); posted entries are voided instead. */
export function planDeleteDraft(state, { id } = {}) {
  const e = coll(state, 'entries')[id];
  if (!e) return fail(err('not-found', MSG.NOT_FOUND));
  if (e.status !== 'draft') return fail(err('draft-only', MSG.DRAFT_ONLY));
  return {
    ok: true,
    writes: [{ op: 'delete', path: `entries/${id}` }],
    audit: { kind: 'draft-delete', coll: 'entries', id, reason: '', summary: `حذف مسودة${e.desc ? ` — ${e.desc}` : ''}` },
    errors: [],
  };
}

/** Link bookkeeping: register items (assumptions/openItems) list the entry numbers that cite them. */
function linkWrites(state, lines, no, oldLinks = new Set(), extraWrites = []) {
  const wanted = new Map(); // `${coll}/${n}` -> {coll, n}
  for (const l of lines) {
    for (const k of l.links || []) {
      if (!k || isNil(k.n) || (k.t !== 'a' && k.t !== 'o')) continue;
      const c = k.t === 'a' ? 'assumptions' : 'openItems';
      const key = `${c}/${k.n}`;
      if (!oldLinks.has(key)) wanted.set(key, { c, n: k.n });
    }
  }
  const writes = [];
  for (const [key, { c, n }] of wanted) {
    const extra = extraWrites.find((w) => w.path === key && w.op === 'set');
    if (extra) {
      const list = Array.isArray(extra.data.linkedEntries) ? extra.data.linkedEntries.slice() : [];
      if (!list.includes(no)) list.push(no);
      extra.data = { ...extra.data, linkedEntries: list };
      continue;
    }
    const item = coll(state, c)[String(n)];
    if (!item) continue; // dangling link: integrity reports it
    const list = Array.isArray(item.linkedEntries) ? item.linkedEntries.slice() : [];
    if (!list.includes(no)) list.push(no);
    writes.push({ op: 'update', path: key, data: { linkedEntries: list } });
  }
  return writes;
}

export function linkKeysOf(lines) {
  const s = new Set();
  for (const l of lines || []) for (const k of l.links || []) if (k && (k.t === 'a' || k.t === 'o') && !isNil(k.n)) s.add(`${k.t === 'a' ? 'assumptions' : 'openItems'}/${k.n}`);
  return s;
}

/** accounts/<code> updates for accounts that have never been used before. */
export function everUsedWrites(state, lines) {
  const writes = [];
  const seen = new Set();
  for (const l of lines) {
    const a = coll(state, 'accounts')[l.acct];
    if (a && a.everUsed !== true && !seen.has(l.acct)) {
      seen.add(l.acct);
      writes.push({ op: 'update', path: `accounts/${l.acct}`, data: { everUsed: true } });
    }
  }
  return writes;
}

/** Apply validation's suggested needs-review flags to normalised lines (never clears an existing flag). */
export function applyFlags(lines, flags) {
  for (const f of flags || []) {
    const l = lines.find((x) => x.n === f.n);
    if (l && !l.needsReview) {
      l.needsReview = true;
      l.reviewReason = l.reviewReason || f.reviewReason || '';
    }
  }
  return lines;
}

const describe = (no, e) => `ترحيل القيد رقم ${no}${e.desc ? ` — ${e.desc}` : ''} (${formatMoney(fromCents(totalsCents(e.lines).dr), { parens: false })})`;

/**
 * planPost(state, { entry | id, no, user, now, reason, original, extraWrites, audit })
 * `no` is the number allocated by the repo under its lease; without it the planner uses max + 1 of `state`.
 * Validates, numbers (max + 1) and posts. `entry` is the content to post (a new object, or the form state of a
 * draft whose id is entry.id / params.id); `id` alone posts the stored draft. `reason` is mandatory for a
 * closed_reserved year (the posting is then recorded in history and bumps the year revision); a locked year
 * refuses. extraWrites are appended after the entry writes (e.g. an openItems doc created by a template rule).
 * Returns { ok, writes, audit, entryNo, id, entry, validation, errors }.
 */
export function planPost(state, params = {}) {
  const { user = null, now, reason = '', original = null, extraWrites = [] } = params;
  const entries = coll(state, 'entries');
  const draftId = params.id || (params.entry && params.entry.id) || null;
  const stored = draftId ? entries[draftId] : null;
  const input = params.entry || stored;
  if (!input) return fail(err('not-found', MSG.NOT_FOUND));
  if ((stored && stored.status !== 'draft') || input.status === 'posted' || input.status === 'void') {
    return fail(err('already-posted', MSG.ENTRY_ALREADY_POSTED));
  }
  const stamp = stampOf(now);
  const e = normalizeEntry(input);
  const validation = validateEntry(e, { state, id: draftId, reason, original });
  if (!validation.ok) return fail(validation.errors, { validation });
  const gate = periodGate(state, e.fy, { reason });
  const no = params.no === undefined || params.no === null ? nextEntryNo(state) : params.no;
  if (!Number.isInteger(no) || no < 1) return fail(err('number-invalid', MSG.NUMBER_COLLISION));
  const id = entryIdFor(no);
  if (entries[id] || numberTaken(state, no)) return fail(err('number-collision', MSG.NUMBER_COLLISION));
  applyFlags(e.lines, validation.suggestedFlags);
  const doc = {
    ...e,
    no,
    status: 'posted',
    version: 1,
    voidReason: null,
    postedBy: user,
    postedAt: stamp,
    createdBy: (stored && stored.createdBy) || e.createdBy || user,
    createdAt: (stored && stored.createdAt) || e.createdAt || stamp,
    history: gate.bump ? [{ v: 1, at: stamp, by: user, kind: 'post', reason, before: null, periodState: 'closed_reserved' }] : [],
  };
  const extra = extraWrites.map((w) => ({ ...w, data: w.data === undefined ? undefined : clone(w.data) }));
  const writes = [{ op: 'set', path: `entries/${id}`, data: doc }];
  if (stored) writes.push({ op: 'delete', path: `entries/${draftId}` });
  writes.push(...everUsedWrites(state, doc.lines));
  if (gate.bump) writes.push({ op: 'update', path: `fiscalYears/${gate.year}`, data: { revision: gate.revision + 1 } });
  writes.push(...linkWrites(state, doc.lines, no, new Set(), extra));
  writes.push(...extra);
  return {
    ok: true,
    id,
    entryNo: no,
    writes,
    audit: params.audit || { kind: 'post', coll: 'entries', id, reason, summary: describe(no, doc) },
    errors: [],
    entry: { id, ...doc },
    validation,
    warnings: validation.warnings,
  };
}

export { linkWrites };
