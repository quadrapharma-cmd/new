import test from 'node:test';
import assert from 'node:assert/strict';
import {
  planAmend, planVoid, planReverse, planCloseYear, planReopenYear, planLockYear, planUnlockYear,
  closeChecklist, changesSinceClose, snapshotDiff,
} from '../../src/engine/amend.js';
import { planPost, nextEntryNo } from '../../src/engine/posting.js';
import { trialBalance, incomeStatement } from '../../src/engine/statements.js';
import { MSG } from '../../src/engine/constants.js';
import { buildState, makeEntry, entryId, DRAFT_ID, NOW, USER } from '../synthetic/build-state.js';
import { applyPlan } from '../synthetic/apply-plan.js';

const codes = (plan) => plan.errors.map((e) => e.code);
const E30 = entryId(30);
const edit = (state, id, fn) => {
  const e = JSON.parse(JSON.stringify(state.entries[id]));
  fn(e);
  return e;
};
const bump = (e) => {
  e.lines[0].dr = 510000;
  e.lines[1].cr = 510000;
};

test('planAmend: snapshot in history, version bump, reason, audit; number and identity preserved', () => {
  const state = buildState();
  const old = JSON.parse(JSON.stringify(state.entries[E30]));
  const before = JSON.stringify(state);
  const plan = planAmend(state, { id: E30, entry: edit(state, E30, bump), reason: 'تصحيح المبلغ بعد وصول المستند', expectedVersion: 1, user: 'u_editor', now: NOW });
  assert.equal(JSON.stringify(state), before, 'pure');
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.writes.length, 1);
  const w = plan.writes[0];
  assert.deepEqual({ op: w.op, path: w.path }, { op: 'set', path: `entries/${E30}` });
  const doc = w.data;
  assert.equal(doc.no, 30);
  assert.equal(doc.status, 'posted');
  assert.equal(doc.version, 2);
  assert.equal(doc.lines[0].dr, 510000);
  assert.equal(doc.isLegacy, false);
  assert.equal(doc.createdBy, old.createdBy);
  assert.equal(doc.postedAt, old.postedAt, 'original posting stamp is kept');
  assert.equal(doc.history.length, 1);
  const h = doc.history[0];
  assert.equal(h.v, 2);
  assert.equal(h.kind, 'amend');
  assert.equal(h.by, 'u_editor');
  assert.equal(h.at, NOW);
  assert.equal(h.reason, 'تصحيح المبلغ بعد وصول المستند');
  assert.equal(h.periodState, undefined);
  const { history, ...oldNoHistory } = old;
  assert.deepEqual(h.before, oldNoHistory, 'before = the previous entry minus its history');
  assert.equal(h.before.lines[0].dr, 500000);
  assert.deepEqual(plan.audit, { kind: 'amend', coll: 'entries', id: E30, reason: 'تصحيح المبلغ بعد وصول المستند', summary: plan.audit.summary });
  assert.match(plan.audit.summary, /30/);
});

test('planAmend: reason and expectedVersion are mandatory; stale versions conflict; no-op refused', () => {
  const state = buildState();
  const e = edit(state, E30, bump);
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: e, reason: '', expectedVersion: 1 })), ['reason-required']);
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: e, reason: '   ', expectedVersion: 1 })), ['reason-required']);
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: e, reason: 'سبب' })), ['version-required']);
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: e, reason: 'سبب', expectedVersion: 7 })), ['version-conflict']);
  const same = edit(state, E30, () => {});
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: same, reason: 'سبب', expectedVersion: 1 })), ['no-changes']);
  assert.deepEqual(codes(planAmend(state, { id: 'e999999', entry: e, reason: 'سبب', expectedVersion: 1 })), ['not-found']);
  assert.deepEqual(codes(planAmend(state, { id: DRAFT_ID, entry: e, reason: 'سبب', expectedVersion: 1 })), ['not-posted']);
  assert.deepEqual(codes(planAmend(state, { id: entryId(35), entry: e, reason: 'سبب', expectedVersion: 1 })), ['entry-void']);
});

test('planAmend: the amended content is fully validated', () => {
  const state = buildState();
  const bad = edit(state, E30, (e) => { e.lines[0].dr = 600000; });
  const plan = planAmend(state, { id: E30, entry: bad, reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(plan.ok, false);
  assert.ok(codes(plan).includes('unbalanced'));
  assert.equal(plan.writes.length, 0);
  const noDoc = planAmend(state, { id: E30, entry: edit(state, E30, (e) => { e.docIds = []; bump(e); }), reason: 'سبب', expectedVersion: 1 });
  assert.ok(codes(noDoc).includes('dim-missing'));
});

test('planAmend: partial `changes` merge over the stored entry', () => {
  const state = buildState();
  const plan = planAmend(state, { id: E30, changes: { desc: 'وصف معدل' }, reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.writes[0].data.desc, 'وصف معدل');
  assert.equal(plan.writes[0].data.lines.length, 2);
});

test('planAmend in a locked year is refused; in a closed_reserved year it records the revision', () => {
  const state = buildState();
  const locked = planAmend(state, { id: entryId(1), changes: { desc: 'x' }, reason: 'سبب', expectedVersion: 1 });
  assert.equal(locked.ok, false);
  assert.ok(codes(locked).includes('period-locked'));

  const closed = planAmend(state, { id: entryId(10), changes: { desc: 'وصف' }, reason: 'وصل مستند', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(closed.ok, true, JSON.stringify(closed.errors));
  assert.equal(closed.writes[0].data.history[0].periodState, 'closed_reserved');
  assert.deepEqual(closed.writes.find((w) => w.path === 'fiscalYears/2021'), { op: 'update', path: 'fiscalYears/2021', data: { revision: 2 } });
});

test('planAmend moving the date across years checks and bumps both years', () => {
  const state = buildState();
  const toClosed = planAmend(state, { id: E30, changes: { date: '2021-03-03' }, reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(toClosed.ok, true, JSON.stringify(toClosed.errors));
  assert.equal(toClosed.writes[0].data.fy, 2021);
  assert.equal(toClosed.writes.filter((w) => w.path.startsWith('fiscalYears/')).length, 1);
  const toLocked = planAmend(state, { id: E30, changes: { date: '2020-03-03' }, reason: 'سبب', expectedVersion: 1 });
  assert.equal(toLocked.ok, false);
  assert.ok(codes(toLocked).includes('period-locked'));
  const fromClosedToOpen = planAmend(state, { id: entryId(10), changes: { date: '2022-01-15' }, reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(fromClosedToOpen.ok, true, JSON.stringify(fromClosedToOpen.errors));
  assert.deepEqual(fromClosedToOpen.writes.filter((w) => w.path.startsWith('fiscalYears/')).map((w) => w.path), ['fiscalYears/2021']);
});

test('legacy lines: editing the header is allowed; editing a line missing its required party is not', () => {
  const state = buildState(); // entry 9 (2021, closed with reservations) has a required-party line without a party
  const header = planAmend(state, { id: entryId(9), changes: { desc: 'وصف معدل' }, reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(header.ok, true, JSON.stringify(header.errors));
  assert.ok(header.writes[0].data.lines[0].needsReview, 'the legacy line is flagged for review, not blocked');
  assert.ok(header.validation.warnings.some((w) => w.code === 'party-required-legacy'));
  const bad = planAmend(state, { id: entryId(9), entry: edit(state, entryId(9), (e) => { e.lines[0].dr = 9000; e.lines[1].cr = 9000; }), reason: 'سبب', expectedVersion: 1 });
  assert.equal(bad.ok, false);
  assert.ok(codes(bad).includes('party-required'));
  const fixed = planAmend(state, { id: entryId(9), entry: edit(state, entryId(9), (e) => { e.lines[0].dr = 9000; e.lines[1].cr = 9000; e.lines[0].partyId = 'p0004'; }), reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(fixed.ok, true, JSON.stringify(fixed.errors));
});

test('history accumulates over successive amendments and versions chain', () => {
  const state = buildState();
  const p1 = planAmend(state, { id: E30, entry: edit(state, E30, bump), reason: 'الأول', expectedVersion: 1, user: USER, now: NOW });
  applyPlan(state, p1);
  const second = edit(state, E30, (e) => { e.lines[0].dr = 520000; e.lines[1].cr = 520000; });
  const p2 = planAmend(state, { id: E30, entry: second, reason: 'الثاني', expectedVersion: 2, user: USER, now: '2024-03-02T10:00:00.000Z' });
  assert.equal(p2.ok, true, JSON.stringify(p2.errors));
  applyPlan(state, p2);
  const e = state.entries[E30];
  assert.equal(e.version, 3);
  assert.deepEqual(e.history.map((h) => [h.v, h.reason, h.before.lines[0].dr, h.before.version]), [[2, 'الأول', 500000, 1], [3, 'الثاني', 510000, 2]]);
  // the stale editor loses
  assert.deepEqual(codes(planAmend(state, { id: E30, entry: second, reason: 'متأخر', expectedVersion: 1 })), ['version-conflict']);
});

test('planAmend refuses when the history would exceed the document size cap', () => {
  const state = buildState();
  const e = state.entries[E30];
  e.history = Array.from({ length: 90 }, (_, i) => ({ v: i + 2, at: NOW, by: USER, kind: 'amend', reason: 'س'.repeat(3000), before: {} }));
  e.version = 91;
  const plan = planAmend(state, { id: E30, entry: edit(state, E30, bump), reason: 'سبب', expectedVersion: 91, user: USER, now: NOW });
  assert.equal(plan.ok, false);
  assert.deepEqual(codes(plan), ['entry-too-large']);
});

test('planVoid keeps the number, needs a reason and the report excludes it afterwards', () => {
  const state = buildState();
  assert.deepEqual(codes(planVoid(state, { id: E30, reason: '', expectedVersion: 1 })), ['reason-required']);
  assert.deepEqual(codes(planVoid(state, { id: E30, reason: 'سبب' })), ['version-required']);
  assert.deepEqual(codes(planVoid(state, { id: E30, reason: 'سبب', expectedVersion: 3 })), ['version-conflict']);
  assert.deepEqual(codes(planVoid(state, { id: entryId(35), reason: 'سبب', expectedVersion: 1 })), ['entry-void']);
  assert.deepEqual(codes(planVoid(state, { id: DRAFT_ID, reason: 'سبب', expectedVersion: 1 })), ['not-posted']);
  const plan = planVoid(state, { id: E30, reason: 'قيد مكرر', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  const doc = plan.writes[0].data;
  assert.equal(doc.status, 'void');
  assert.equal(doc.no, 30);
  assert.equal(doc.voidReason, 'قيد مكرر');
  assert.equal(doc.version, 2);
  assert.equal(doc.history[0].kind, 'void');
  assert.equal(doc.history[0].before.status, 'posted');
  assert.equal(plan.audit.kind, 'void');
  const before = incomeStatement({ state, year: 2023 }).revenue.gross;
  applyPlan(state, plan);
  assert.equal(incomeStatement({ state, year: 2023 }).revenue.gross, before - 500000);
  assert.equal(nextEntryNo(state), 36, 'void keeps its number: nothing is renumbered');
  assert.equal(trialBalance({ state, asOf: '2023-12-31' }).balanced, true);
  // locked / closed years
  assert.ok(codes(planVoid(state, { id: entryId(1), reason: 'سبب', expectedVersion: 1 })).includes('period-locked'));
  const closed = planVoid(state, { id: entryId(10), reason: 'سبب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(closed.ok, true);
  assert.ok(closed.writes.some((w) => w.path === 'fiscalYears/2021'));
});

test('voiding a depreciation entry reopens its proposed run', () => {
  const state = buildState();
  state.entries[entryId(18)].source = 'depreciation';
  state.depRuns[2022] = { year: 2022, status: 'posted', lines: [], postedEntryNo: 18 };
  const plan = planVoid(state, { id: entryId(18), reason: 'إعادة احتساب', expectedVersion: 1, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.deepEqual(plan.writes.find((w) => w.path === 'depRuns/2022'), { op: 'update', path: 'depRuns/2022', data: { status: 'proposed', postedEntryNo: null } });
});

test('planReverse: swapped sides, new number, source and link, cancels the original in the ledger', () => {
  const state = buildState();
  const plan = planReverse(state, { id: E30, reason: 'قيد خاطئ', date: '2023-12-15', user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.entryNo, 36);
  assert.equal(planReverse(state, { id: E30, reason: 'قيد خاطئ', date: '2023-12-15', no: 400, user: USER, now: NOW }).entryNo, 400, 'the repo-allocated number is forwarded');
  const doc = plan.writes[0].data;
  assert.equal(doc.source, 'reversal');
  assert.equal(doc.reversalOf, E30);
  assert.equal(doc.date, '2023-12-15');
  assert.equal(doc.status, 'posted');
  assert.deepEqual(doc.lines.map((l) => [l.acct, l.dr, l.cr]), [['1340', 0, 500000], ['4110', 500000, 0]]);
  assert.match(doc.desc, /30/);
  assert.equal(plan.audit.kind, 'reverse');
  assert.equal(plan.audit.reason, 'قيد خاطئ');
  applyPlan(state, plan);
  const tb = trialBalance({ state, asOf: '2023-12-31' });
  assert.equal(tb.balanced, true);
  assert.equal(state.entries[E30].status, 'posted', 'the original stays; the reversal is a new entry');
  assert.equal(incomeStatement({ state, year: 2023 }).revenue.gross, 0);
  // reasons, duplicates, voids
  assert.deepEqual(codes(planReverse(state, { id: E30, reason: 'سبب', date: '2023-12-16' })), ['already-reversed']);
  assert.deepEqual(codes(planReverse(state, { id: entryId(31), reason: '', date: '2023-12-16' })), ['reason-required']);
  assert.deepEqual(codes(planReverse(state, { id: entryId(35), reason: 'سبب', date: '2023-12-16' })), ['entry-void']);
  assert.deepEqual(codes(planReverse(state, { id: DRAFT_ID, reason: 'سبب', date: '2023-12-16' })), ['not-posted']);
  assert.deepEqual(codes(planReverse(state, { id: 'zzz', reason: 'سبب', date: '2023-12-16' })), ['not-found']);
  assert.ok(codes(planReverse(state, { id: entryId(31), reason: 'سبب', date: 'bad' })).includes('date-invalid'));
});

test('planReverse is the fix for a locked year: reverse in an open period; legacy exceptions do not block it', () => {
  const state = buildState();
  const inLocked = planReverse(state, { id: entryId(1), reason: 'سبب', date: '2020-12-01' });
  assert.equal(inLocked.ok, false);
  assert.ok(codes(inLocked).includes('period-locked'));
  const ok = planReverse(state, { id: entryId(1), reason: 'تصحيح سنة مقفلة', date: '2023-12-01', user: USER, now: NOW });
  assert.equal(ok.ok, true, JSON.stringify(ok.errors));
  // legacy entry 9 has a required-party line without a party: the reversal still goes through
  const legacy = planReverse(state, { id: entryId(9), reason: 'سبب', date: '2023-12-02', user: USER, now: NOW });
  assert.equal(legacy.ok, true, JSON.stringify(legacy.errors));
  // reversal into a closed_reserved year needs the reason and bumps the revision
  const closed = planReverse(state, { id: entryId(30), reason: 'سبب', date: '2021-12-02', user: USER, now: NOW });
  assert.equal(closed.ok, true, JSON.stringify(closed.errors));
  assert.ok(closed.writes.some((w) => w.path === 'fiscalYears/2021'));
});

// ------------------------------------------------------------------ year lifecycle

test('planCloseYear takes a trial-balance snapshot and moves the year to closed_reserved', () => {
  const state = buildState();
  state.entries[DRAFT_ID].date = '2024-01-01'; // drafts of other years do not block
  const plan = planCloseYear(state, { year: 2022, user: USER, now: NOW, reservation: { sources: 'مصادر', notRecorded: 'غير مسجل', text: 'تحفظ', lastUpdate: '2024-03-01' } });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.writes.length, 1);
  const w = plan.writes[0];
  assert.deepEqual({ op: w.op, path: w.path }, { op: 'set', path: 'fiscalYears/2022' });
  const d = w.data;
  assert.equal(d.state, 'closed_reserved');
  assert.equal(d.year, 2022);
  assert.equal(d.closedAt, NOW);
  assert.equal(d.closedBy, USER);
  assert.equal(d.revision, 0);
  assert.equal(d.startDate, '2022-01-01');
  assert.equal(d.endDate, '2022-12-31');
  assert.equal(d.reservation.text, 'تحفظ');
  const tb = trialBalance({ state, asOf: '2022-12-31' });
  assert.equal(d.snapshot.takenAt, NOW);
  assert.deepEqual(d.snapshot.totals, { dr: tb.totals.closingDr, cr: tb.totals.closingCr });
  assert.equal(d.snapshot.totals.dr, d.snapshot.totals.cr);
  assert.deepEqual(d.snapshot.tb, tb.rows.filter((r) => r.closing !== 0).map((r) => ({ acct: r.acct, dr: r.closingDr, cr: r.closingCr })));
  assert.equal(d.snapshot.netResult, incomeStatement({ state, year: 2022 }).netResult);
  assert.equal(plan.audit.kind, 'close');
  assert.ok(plan.checklist.length > 0);
  applyPlan(state, plan);
  // after closing, posting needs a reason
  const posting = planPost(state, { entry: makeEntry({ no: null, status: 'draft', date: '2022-08-08', lines: [['1340', 5, 0, { partyId: 'p0005' }], ['4110', 0, 5]], sector: 'sec2' }), user: USER, now: NOW });
  assert.equal(posting.ok, false);
});

test('planCloseYear refuses pending drafts, already closed or locked years and invalid years', () => {
  const state = buildState();
  const withDraft = planCloseYear(state, { year: 2023, user: USER, now: NOW });
  assert.equal(withDraft.ok, false);
  assert.deepEqual(codes(withDraft), ['drafts-pending']);
  assert.equal(planCloseYear(state, { year: 2023, user: USER, now: NOW, allowDrafts: true }).ok, true);
  assert.deepEqual(codes(planCloseYear(state, { year: 2021, user: USER, now: NOW })), ['year-already-closed']);
  assert.deepEqual(codes(planCloseYear(state, { year: 2020, user: USER, now: NOW })), ['year-already-closed']);
  assert.deepEqual(codes(planCloseYear(state, { year: 'abc' })), ['year-invalid']);
  // a year with no fiscalYears doc is open and can be closed (the doc is created)
  const s2 = buildState({ withDraft: false, withYears: false });
  const created = planCloseYear(s2, { year: 2022, user: USER, now: NOW });
  assert.equal(created.ok, true);
  assert.equal(created.writes[0].data.state, 'closed_reserved');
});

test('planReopenYear: owner only, reason required, bumps revision, keeps the snapshot', () => {
  const state = buildState();
  assert.deepEqual(codes(planReopenYear(state, { year: 2021, reason: 'وصل مستند', isOwner: false })), ['owner-only']);
  assert.deepEqual(codes(planReopenYear(state, { year: 2021, reason: '', isOwner: true })), ['reason-required']);
  assert.deepEqual(codes(planReopenYear(state, { year: 2022, reason: 'سبب', isOwner: true })), ['year-already-open']);
  assert.deepEqual(codes(planReopenYear(state, { year: 2020, reason: 'سبب', isOwner: true })), ['unlock-first']);
  const plan = planReopenYear(state, { year: 2021, reason: 'وصل مستند جديد', isOwner: true, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  const d = plan.writes[0].data;
  assert.equal(d.state, 'open');
  assert.equal(d.revision, 2);
  assert.deepEqual(d.snapshot, state.fiscalYears[2021].snapshot);
  assert.equal(d.reopenReason, 'وصل مستند جديد');
  assert.equal(d.reopenedBy, USER);
  assert.equal(plan.audit.kind, 'reopen');
  assert.equal(plan.audit.reason, 'وصل مستند جديد');
  applyPlan(state, plan);
  assert.equal(state.fiscalYears[2021].state, 'open');
});

test('planLockYear / planUnlockYear', () => {
  const state = buildState();
  assert.deepEqual(codes(planLockYear(state, { year: 2022, user: USER, now: NOW })), ['close-first']);
  assert.deepEqual(codes(planLockYear(state, { year: 2020, user: USER, now: NOW })), ['year-already-locked']);
  const lock = planLockYear(state, { year: 2021, user: USER, now: NOW });
  assert.equal(lock.ok, true, JSON.stringify(lock.errors));
  const d = lock.writes[0].data;
  assert.equal(d.state, 'locked');
  assert.equal(d.lockedBy, USER);
  assert.equal(d.lockedAt, NOW);
  assert.equal(d.snapshot.takenAt, NOW, 'the snapshot is refreshed at lock time');
  assert.equal(lock.audit.kind, 'lock');
  applyPlan(state, lock);
  assert.ok(codes(planAmend(state, { id: entryId(10), changes: { desc: 'x' }, reason: 'سبب', expectedVersion: 1 })).includes('period-locked'));

  assert.deepEqual(codes(planUnlockYear(state, { year: 2021, reason: 'سبب', isOwner: false })), ['owner-only']);
  assert.deepEqual(codes(planUnlockYear(state, { year: 2021, reason: '', isOwner: true })), ['reason-required']);
  assert.deepEqual(codes(planUnlockYear(state, { year: 2022, reason: 'سبب', isOwner: true })), ['year-not-locked']);
  const unlock = planUnlockYear(state, { year: 2021, reason: 'قرار المالك', isOwner: true, user: USER, now: NOW });
  assert.equal(unlock.ok, true, JSON.stringify(unlock.errors));
  assert.equal(unlock.writes[0].data.state, 'closed_reserved');
  assert.equal(unlock.writes[0].data.revision, 2, 'lock keeps the revision; unlock bumps it by one');
  assert.equal(unlock.audit.kind, 'unlock');
  assert.equal(unlock.audit.reason, 'قرار المالك');
});

test('full lifecycle on a fresh state: close -> post with reason -> lock -> refuse -> unlock -> reopen', () => {
  const state = buildState({ withDraft: false });
  applyPlan(state, planCloseYear(state, { year: 2023, user: USER, now: NOW }));
  const e = makeEntry({ no: null, status: 'draft', date: '2023-12-20', sector: 'sec2', lines: [['1340', 10, 0, { partyId: 'p0005' }], ['4110', 0, 10]] });
  assert.equal(planPost(state, { entry: e, user: USER, now: NOW }).ok, false);
  const posted = planPost(state, { entry: e, user: USER, now: NOW, reason: 'مستند متأخر' });
  assert.equal(posted.ok, true, JSON.stringify(posted.errors));
  applyPlan(state, posted);
  assert.equal(state.fiscalYears[2023].revision, 1);
  applyPlan(state, planLockYear(state, { year: 2023, user: USER, now: NOW }));
  assert.equal(planPost(state, { entry: e, user: USER, now: NOW, reason: 'x' }).ok, false);
  applyPlan(state, planUnlockYear(state, { year: 2023, reason: 'سبب', isOwner: true, user: USER, now: NOW }));
  applyPlan(state, planReopenYear(state, { year: 2023, reason: 'سبب', isOwner: true, user: USER, now: NOW }));
  assert.equal(state.fiscalYears[2023].state, 'open');
  assert.equal(planPost(state, { entry: e, user: USER, now: NOW }).ok, true);
  assert.equal(MSG.periodClosed(2023), 'السنة 2023 مقفلة — اطلب إعادة فتحها مع ذكر السبب');
});

test('snapshots record the year revision; closeChecklist previews the close', () => {
  const state = buildState();
  const plan = planCloseYear(state, { year: 2022, user: USER, now: NOW });
  assert.equal(plan.writes[0].data.snapshot.revision, 0);
  const lock = planLockYear(state, { year: 2021, user: USER, now: NOW });
  assert.equal(lock.writes[0].data.snapshot.revision, 1);
  const list = closeChecklist(state, 2023);
  assert.deepEqual(list.map((c) => c.key), ['drafts', 'tb', 'suspense', 'openItems']);
  assert.equal(list.find((c) => c.key === 'drafts').ok, false);
  assert.equal(list.find((c) => c.key === 'tb').ok, true);
  assert.equal(list.find((c) => c.key === 'suspense').ok, false);
  const withAssets = buildState();
  withAssets.assets = { a1: { id: 'a1' } };
  assert.ok(closeChecklist(withAssets, 2023).some((c) => c.key === 'depreciation' && c.ok === false));
  assert.deepEqual(closeChecklist(state, 'zz'), []);
});

test('changesSinceClose lists postings, amendments and voids recorded after the snapshot; snapshotDiff shows live vs closed', () => {
  const state = buildState();
  assert.deepEqual(changesSinceClose(state, 2021), []);
  assert.deepEqual(changesSinceClose(state, 2022), [], 'a year with no close has no baseline');
  assert.equal(snapshotDiff(state, 2021).differs, false);
  assert.equal(snapshotDiff(state, 2022).hasSnapshot, false);
  // a late posting with a reason, then an amendment and a void, all in the closed year 2021
  const e = makeEntry({ no: null, status: 'draft', date: '2021-06-01', sector: 'sec2', desc: 'متأخر', lines: [['1340', 700, 0, { partyId: 'p0005' }], ['4110', 0, 700]] });
  e.createdAt = null;
  const post = planPost(state, { entry: e, user: USER, now: '2024-04-01T10:00:00.000Z', reason: 'مستند متأخر' });
  assert.equal(post.ok, true, JSON.stringify(post.errors));
  applyPlan(state, post, { at: '2024-04-01T10:00:00.000Z' });
  applyPlan(state, planAmend(state, { id: entryId(10), changes: { desc: 'وصف' }, reason: 'تحسين الوصف', expectedVersion: 1, user: 'u2', now: '2024-04-02T10:00:00.000Z' }));
  applyPlan(state, planVoid(state, { id: entryId(12), reason: 'مكرر', expectedVersion: 1, user: 'u3', now: '2024-04-03T10:00:00.000Z' }));
  const changes = changesSinceClose(state, 2021);
  assert.deepEqual(changes.map((c) => [c.no, c.kind, c.reason, c.by]), [
    [post.entryNo, 'post', 'مستند متأخر', USER], [10, 'amend', 'تحسين الوصف', 'u2'], [12, 'void', 'مكرر', 'u3'],
  ]);
  assert.equal(state.fiscalYears[2021].revision, 4, 'each change bumped the revision (1 -> 4)');
  const diff = snapshotDiff(state, 2021);
  assert.equal(diff.differs, true);
  assert.deepEqual(diff.rows.map((r) => [r.acct, r.difference]), [['1320', 25000], ['1340', 700], ['4110', -700], ['5250', -25000]]);
  assert.equal(diff.netResult.snapshot, 205000);
  assert.equal(diff.netResult.live, 205000 + 700 + 25000);
  assert.equal(diff.netResult.difference, 25700);
});

test('a frozen (immutable) state is never mutated by any planner or report', () => {
  const deepFreeze = (o) => {
    if (o && typeof o === 'object' && !Object.isFrozen(o)) {
      Object.freeze(o);
      Object.values(o).forEach(deepFreeze);
    }
    return o;
  };
  const state = deepFreeze(buildState());
  const params = { user: USER, now: NOW };
  const e = makeEntry({ no: null, status: 'draft', date: '2023-12-01', sector: 'sec2', lines: [['1340', 5, 0, { partyId: 'p0005' }], ['4110', 0, 5]] });
  assert.equal(planPost(state, { entry: e, ...params }).ok, true);
  assert.equal(planAmend(state, { id: E30, changes: { desc: 'ز' }, reason: 'س', expectedVersion: 1, ...params }).ok, true);
  assert.equal(planAmend(state, { id: entryId(9), changes: { desc: 'ز' }, reason: 'س', expectedVersion: 1, ...params }).ok, true);
  assert.equal(planVoid(state, { id: E30, reason: 'س', expectedVersion: 1, ...params }).ok, true);
  assert.equal(planReverse(state, { id: E30, reason: 'س', date: '2023-12-02', ...params }).ok, true);
  assert.equal(planCloseYear(state, { year: 2022, ...params }).ok, true);
  assert.equal(planLockYear(state, { year: 2021, ...params }).ok, true);
  assert.equal(planReopenYear(state, { year: 2021, reason: 'س', isOwner: true, ...params }).ok, true);
  assert.equal(planUnlockYear(state, { year: 2020, reason: 'س', isOwner: true, ...params }).ok, true);
  assert.equal(snapshotDiff(state, 2021).differs, false);
  assert.equal(changesSinceClose(state, 2021).length, 0);
});
