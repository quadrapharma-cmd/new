import test from 'node:test';
import assert from 'node:assert/strict';
import { nextEntryNo, planSaveDraft, planDeleteDraft, planPost, entryIdFor } from '../../src/engine/posting.js';
import { trialBalance } from '../../src/engine/statements.js';
import { MSG } from '../../src/engine/constants.js';
import { buildState, cloneState, makeEntry, DRAFT_ID, entryId, NOW, USER } from '../synthetic/build-state.js';
import { applyPlan } from '../synthetic/apply-plan.js';
import { emptyState } from '../../src/engine/state.js';

const L = (...a) => a;
const mk = (over = {}) => {
  const e = makeEntry({
    no: null, status: 'draft', date: '2023-12-01', desc: 'اختبار ترحيل', cc: 'cc1', sector: 'sec2', docIds: ['D0001'],
    lines: [L('1340', 100, 0, { partyId: 'p0005' }), L('4110', 0, 100)], ...over,
  });
  e.createdAt = null; // a fresh form state has no creation stamp yet
  e.createdBy = null;
  return e;
};
const codes = (plan) => plan.errors.map((e) => e.code);

test('nextEntryNo is max(posted/void) + 1; drafts never count', () => {
  assert.equal(nextEntryNo(emptyState()), 1);
  assert.equal(nextEntryNo(buildState()), 36, 'void entry 35 keeps its number');
  const s = buildState();
  s.entries.d_zz_zz = makeEntry({ no: null, status: 'draft', date: '2023-01-01', lines: [] });
  s.entries.d_zz_zz.no = 99; // a stray number on a draft must be ignored
  assert.equal(nextEntryNo(s), 36);
  assert.equal(entryIdFor(312), 'e000312');
  assert.equal(entryIdFor(1234567), 'e1234567');
});

test('planSaveDraft: new draft id, no number, no audit, incomplete content allowed', () => {
  const state = buildState();
  const plan = planSaveDraft(state, { entry: mk({ docIds: [], lines: [L('1340', 50, 0)] }), user: USER, now: NOW, rand: () => 0.123456789 });
  assert.equal(plan.ok, true);
  assert.match(plan.id, /^d_[a-z0-9]+_[a-z0-9]{4}$/);
  assert.equal(plan.writes.length, 1);
  assert.deepEqual({ op: plan.writes[0].op, path: plan.writes[0].path }, { op: 'set', path: `entries/${plan.id}` });
  const d = plan.writes[0].data;
  assert.equal(d.status, 'draft');
  assert.equal(d.no, null);
  assert.equal(d.fy, 2023);
  assert.equal(d.createdBy, USER);
  assert.equal(d.createdAt, NOW);
  assert.equal(plan.audit, null);
  assert.equal(plan.validation.ok, false, 'validation is reported, not enforced, for drafts');
  assert.equal(plan.entry.id, plan.id);
  // deterministic id from clock and rand
  const again = planSaveDraft(state, { entry: mk(), user: USER, now: NOW, rand: () => 0.123456789 });
  assert.equal(again.id, plan.id);
});

test('planSaveDraft stores unreadable amounts as 0 (NaN is not a JSON number)', () => {
  const state = buildState();
  const e = mk();
  e.lines[0].dr = NaN;
  const plan = planSaveDraft(state, { entry: e, user: USER, now: NOW });
  assert.equal(plan.writes[0].data.lines[0].dr, 0);
  assert.ok(plan.validation.errors.some((x) => x.code === 'amount-zero'));
});

test('planSaveDraft: updating a draft keeps its creation stamp; posted entries are refused', () => {
  const state = buildState();
  const plan = planSaveDraft(state, { entry: { ...state.entries[DRAFT_ID], id: DRAFT_ID, desc: 'معدلة' }, user: 'u_other', now: NOW });
  assert.equal(plan.ok, true);
  assert.equal(plan.id, DRAFT_ID);
  assert.equal(plan.writes[0].data.createdBy, USER);
  assert.equal(plan.writes[0].data.createdAt, state.entries[DRAFT_ID].createdAt);
  assert.equal(plan.writes[0].data.desc, 'معدلة');
  const refused = planSaveDraft(state, { entry: { ...state.entries[entryId(30)], id: entryId(30) } });
  assert.equal(refused.ok, false);
  assert.deepEqual(codes(refused), ['draft-only']);
  assert.equal(refused.writes.length, 0);
  assert.equal(planSaveDraft(state, { entry: { ...mk(), status: 'posted' } }).ok, false);
  assert.equal(planSaveDraft(state, {}).ok, false);
});

test('planDeleteDraft', () => {
  const state = buildState();
  const plan = planDeleteDraft(state, { id: DRAFT_ID, user: USER, now: NOW });
  assert.equal(plan.ok, true);
  assert.deepEqual(plan.writes, [{ op: 'delete', path: `entries/${DRAFT_ID}` }]);
  assert.equal(plan.audit.kind, 'draft-delete');
  assert.equal(planDeleteDraft(state, { id: entryId(30) }).ok, false);
  assert.equal(planDeleteDraft(state, { id: 'nope' }).ok, false);
});

test('planPost: numbers max+1, marks accounts used, audits (the repo bumps the counter)', () => {
  const state = buildState();
  const before = JSON.stringify(state);
  const plan = planPost(state, { entry: mk({ lines: [L('1310', 100, 0, { partyId: 'p0005' }), L('4110', 0, 100)] }), user: USER, now: NOW });
  assert.equal(JSON.stringify(state), before, 'planning never mutates state');
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.entryNo, 36);
  assert.equal(plan.id, 'e000036');
  const [w0, w1] = plan.writes;
  assert.equal(w0.path, 'entries/e000036');
  assert.equal(w0.data.status, 'posted');
  assert.equal(w0.data.no, 36);
  assert.equal(w0.data.version, 1);
  assert.deepEqual(w0.data.history, []);
  assert.equal(w0.data.postedBy, USER);
  assert.equal(w0.data.postedAt, NOW);
  assert.equal(w0.data.fy, 2023);
  assert.deepEqual(w1, { op: 'update', path: 'accounts/1310', data: { everUsed: true } }, 'only never-used accounts are updated');
  assert.equal(plan.writes.length, 2, 'plans never write meta/counters: the repo allocates the number and bumps the counter');
  assert.equal(plan.writes.some((w) => w.path === 'meta/counters'), false);
  assert.equal(plan.audit.kind, 'post');
  assert.equal(plan.audit.coll, 'entries');
  assert.equal(plan.audit.id, 'e000036');
  assert.match(plan.audit.summary, /36/);
  assert.equal(plan.entry.id, 'e000036');
});

test('planPost from a stored draft deletes the draft and keeps its creator', () => {
  const state = buildState();
  const draft = mk();
  draft.createdBy = 'u_creator';
  draft.createdAt = '2024-02-02T08:00:00.000Z';
  state.entries.d_abc_defg = draft;
  const plan = planPost(state, { id: 'd_abc_defg', user: USER, now: NOW });
  assert.equal(plan.ok, true);
  assert.ok(plan.writes.some((w) => w.op === 'delete' && w.path === 'entries/d_abc_defg'));
  assert.equal(plan.entry.createdBy, 'u_creator');
  assert.equal(plan.entry.postedBy, USER);
  applyPlan(state, plan);
  assert.equal(state.entries.d_abc_defg, undefined);
  assert.equal(state.entries.e000036.status, 'posted');
});

test('planPost refuses invalid entries with the validation errors and no writes', () => {
  const state = buildState();
  const plan = planPost(state, { entry: mk({ lines: [L('1340', 100, 0, { partyId: 'p0005' }), L('4110', 0, 90)] }), user: USER, now: NOW });
  assert.equal(plan.ok, false);
  assert.deepEqual(plan.writes, []);
  assert.ok(codes(plan).includes('unbalanced'));
  assert.equal(plan.validation.balanced, false);
  assert.equal(plan.audit, null);
  assert.equal(planPost(state, { entry: { ...state.entries[entryId(30)], id: entryId(30) } }).ok, false);
  assert.deepEqual(codes(planPost(state, { id: entryId(30) })), ['already-posted']);
  assert.deepEqual(codes(planPost(state, { id: 'missing' })), ['not-found']);
  assert.deepEqual(codes(planPost(state, {})), ['not-found']);
});

test('numbering is gap-free across many posts and void numbers are never reused', () => {
  const state = buildState();
  const nos = [];
  for (let i = 0; i < 6; i++) {
    const plan = planPost(state, { entry: mk({ date: `2023-12-0${i + 1}`, lines: [L('1340', 100 + i, 0, { partyId: 'p0005' }), L('4110', 0, 100 + i)] }), user: USER, now: NOW });
    assert.equal(plan.ok, true, JSON.stringify(plan.errors));
    applyPlan(state, plan);
    nos.push(plan.entryNo);
  }
  assert.deepEqual(nos, [36, 37, 38, 39, 40, 41]);
  assert.equal(state.counters.nextEntryNo, 42);
  assert.equal(nextEntryNo(state), 42);
  // void the newest entry: the next number still moves forward
  state.entries.e000041.status = 'void';
  assert.equal(nextEntryNo(state), 42);
  // reports reflect only what was posted
  const tb = trialBalance({ state, asOf: '2023-12-31' });
  assert.equal(tb.balanced, true);
});

test('period states: locked refuses, closed_reserved needs a reason and is recorded', () => {
  const state = buildState();
  const locked = planPost(state, { entry: mk({ date: '2020-06-01' }), user: USER, now: NOW, reason: 'سبب' });
  assert.equal(locked.ok, false);
  assert.ok(codes(locked).includes('period-locked'));

  const noReason = planPost(state, { entry: mk({ date: '2021-06-01' }), user: USER, now: NOW });
  assert.equal(noReason.ok, false);
  assert.equal(noReason.errors.find((e) => e.code === 'period-closed').msg, MSG.periodClosed(2021));

  const plan = planPost(state, { entry: mk({ date: '2021-06-01' }), user: USER, now: NOW, reason: 'وصل المستند المنتظر' });
  assert.equal(plan.ok, true);
  const doc = plan.writes[0].data;
  assert.equal(doc.history.length, 1);
  assert.deepEqual(doc.history[0], { v: 1, at: NOW, by: USER, kind: 'post', reason: 'وصل المستند المنتظر', before: null, periodState: 'closed_reserved' });
  assert.deepEqual(plan.writes.find((w) => w.path === 'fiscalYears/2021'), { op: 'update', path: 'fiscalYears/2021', data: { revision: 2 } });
  assert.equal(plan.audit.reason, 'وصل المستند المنتظر');
});

test('suggested needs-review flags are written on the posted lines', () => {
  const state = buildState();
  const plan = planPost(state, { entry: mk({ lines: [L('1340', 100, 0), L('4110', 0, 100)] }), user: USER, now: NOW });
  assert.equal(plan.ok, true);
  const lines = plan.writes[0].data.lines;
  assert.equal(lines[0].needsReview, true);
  assert.ok(lines[0].reviewReason.length > 0);
  assert.equal(lines[1].needsReview, false);
});

test('register links: linkedEntries of existing items are updated, new items from extraWrites are patched', () => {
  const state = buildState();
  state.assumptions['5'] = { n: 5, text: 'افتراض تجريبي', status: 'pending', linkedEntries: [3] };
  state.openItems['9'] = { n: 9, item: 'بند تجريبي', status: 'open', linkedEntries: [] };
  const entry = mk({ lines: [
    L('1340', 100, 0, { partyId: 'p0005', links: [{ t: 'a', n: 5 }, { t: 'o', n: 9 }, { t: 'o', n: 10 }, { t: 'a', n: 404 }] }),
    L('4110', 0, 100, { links: [{ t: 'a', n: 5 }] }),
  ] });
  const extra = [{ op: 'set', path: 'openItems/10', data: { n: 10, item: 'بند جديد', status: 'open', linkedEntries: [] } }];
  const plan = planPost(state, { entry, user: USER, now: NOW, extraWrites: extra });
  assert.equal(plan.ok, true);
  assert.deepEqual(plan.writes.find((w) => w.path === 'assumptions/5'), { op: 'update', path: 'assumptions/5', data: { linkedEntries: [3, 36] } });
  assert.deepEqual(plan.writes.find((w) => w.path === 'openItems/9'), { op: 'update', path: 'openItems/9', data: { linkedEntries: [36] } });
  const created = plan.writes.find((w) => w.path === 'openItems/10');
  assert.deepEqual(created.data.linkedEntries, [36]);
  assert.equal(plan.writes.findIndex((w) => w.path === 'openItems/10') > plan.writes.findIndex((w) => w.path === 'entries/e000036'), true, 'extra writes come after the entry');
  assert.equal(plan.writes.some((w) => w.path === 'assumptions/404'), false, 'dangling links are left to the integrity checker');
  assert.deepEqual(extra[0].data.linkedEntries, [], 'caller input is not mutated');
  applyPlan(state, plan);
  assert.deepEqual(state.openItems['10'].linkedEntries, [36]);
});

test('planPost uses the number allocated by the repo when given, and refuses taken or invalid numbers', () => {
  const state = buildState();
  const plan = planPost(state, { entry: mk(), no: 312, user: USER, now: NOW });
  assert.equal(plan.ok, true, JSON.stringify(plan.errors));
  assert.equal(plan.entryNo, 312);
  assert.equal(plan.id, 'e000312');
  assert.equal(plan.writes[0].path, 'entries/e000312');
  assert.equal(plan.writes[0].data.no, 312);
  assert.deepEqual(codes(planPost(state, { entry: mk(), no: 30 })), ['number-collision']);
  assert.deepEqual(codes(planPost(state, { entry: mk(), no: 35 })), ['number-collision'], 'void numbers are taken too');
  assert.deepEqual(codes(planPost(state, { entry: mk(), no: 0 })), ['number-invalid']);
  assert.deepEqual(codes(planPost(state, { entry: mk(), no: 1.5 })), ['number-invalid']);
  assert.equal(planPost(state, { entry: mk(), no: 36 }).ok, true);
});

test('a number collision is refused rather than overwritten', () => {
  const state = buildState();
  state.entries.e000036 = { status: 'draft', date: '2023-01-01', lines: [] };
  const plan = planPost(state, { entry: mk(), user: USER, now: NOW });
  assert.equal(plan.ok, false);
  assert.deepEqual(codes(plan), ['number-collision']);
});

test('posted state is a pure function of the plan: applying the plan yields a consistent state', () => {
  const state = cloneState(buildState());
  const plan = planPost(state, { entry: mk(), user: USER, now: NOW });
  applyPlan(state, plan, { at: NOW });
  assert.equal(state.entries.e000036.no, 36);
  assert.equal(state.counters.nextEntryNo, 37);
  assert.equal(state.accounts['1340'].everUsed, true);
  assert.equal(state.audit['2024-03'].events.length, 1);
  assert.equal(state.audit['2024-03'].events[0].kind, 'post');
});
