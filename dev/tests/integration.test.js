// Store + repo + the real engine planners + the mock runtime, end to end (synthetic data only).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createMockRuntime } from '../mock-runtime.js';
import { buildSyntheticSeed } from '../synthetic-seed.js';
import { initRuntime } from '../../src/data/runtime.js';
import { createStore } from '../../src/data/store.js';
import { createRepo } from '../../src/data/repo.js';
import { planSaveDraft, planPost, checkIntegrity } from '../../src/engine/index.js';

async function boot() {
  const mock = createMockRuntime({ flags: {}, seed: buildSyntheticSeed() });
  const runtime = await initRuntime({ claude: mock.claude });
  const store = createStore(runtime, { batchMs: 0 });
  store.start();
  await store.whenReady();
  const repo = createRepo({ runtime, store, sleepFn: () => new Promise((r) => setTimeout(r, 1)) });
  return { mock, runtime, store, repo };
}
const tick = (ms = 8) => new Promise((r) => setTimeout(r, ms));
const entry = (date, amount, over = {}) => ({
  date, fy: Number(date.slice(0, 4)), desc: 'مصروف تجريبي', docIds: ['D0001'], cc: 'cc_general', sector: 'sec_shared', source: 'user',
  lines: [
    { n: 1, acct: '5250', dr: amount, cr: 0, memo: 'صيانة', partyId: null, docIds: [], cc: 'cc_general', sector: 'sec_shared' },
    { n: 2, acct: '1320', dr: 0, cr: amount, memo: 'خزينة', partyId: null, docIds: [], cc: 'cc_general', sector: 'sec_shared' },
  ],
  ...over,
});

test('draft -> post: planners + repo + store agree (number, draft removal, everUsed, counter, audit, integrity)', async () => {
  const { store, repo, runtime, mock } = await boot();
  const user = runtime.user.id;
  const draftPlan = planSaveDraft(store.getState(), { entry: entry('2025-06-10', 1234.5), user });
  assert.equal(draftPlan.ok, true);
  await repo.applyPlan(draftPlan);
  await tick();
  assert.equal(store.getState().entries[draftPlan.id].status, 'draft');

  const res = await repo.postWithNumber((no) => planPost(store.getState(), { id: draftPlan.id, no, user }));
  assert.equal(res.no, 11);
  assert.equal(res.auditOk, true);
  await tick();
  const s = store.getState();
  assert.equal(s.entries.e000011.status, 'posted');
  assert.equal(s.entries.e000011.no, 11);
  assert.equal(s.entries[draftPlan.id], undefined, 'the draft is gone');
  assert.equal(s.counters.nextEntryNo, 12);
  assert.equal(s.accounts['5250'].everUsed, true);
  const ym = new Date().toISOString().slice(0, 7);
  assert.equal(mock.db.dump()[`audit/${ym}`].events.at(-1).kind, 'post');
  assert.deepEqual(checkIntegrity(s).filter((f) => f.severity === 'error'), []);
});

test('an unbalanced entry is refused by the engine, nothing is written, the counter stays', async () => {
  const { store, repo, runtime, mock } = await boot();
  const bad = entry('2025-06-11', 100);
  bad.lines[1].cr = 90;
  const before = mock.db.size;
  await assert.rejects(
    repo.postWithNumber((no) => planPost(store.getState(), { entry: bad, no, user: runtime.user.id })),
    (e) => e.code === 'plan_rejected' && /غير متوازن/.test(e.message),
  );
  assert.equal(mock.db.size, before);
  assert.equal((await mock.db.namespace.doc('meta/counters').get()).data().nextEntryNo, 11);
});

test('posting into a closed-with-reservations year needs a reason and bumps the year revision', async () => {
  const { store, repo, runtime } = await boot();
  const user = runtime.user.id;
  const e = entry('2024-07-01', 500);
  await assert.rejects(repo.postWithNumber((no) => planPost(store.getState(), { entry: e, no, user })), { code: 'plan_rejected' });
  const r = await repo.postWithNumber((no) => planPost(store.getState(), { entry: e, no, user, reason: 'وصل المستند بعد الإقفال' }));
  assert.equal(r.no, 11);
  await tick();
  assert.equal(store.getState().fiscalYears[2024].revision, 3, 'revision 2 -> 3');
});

test('two tabs posting concurrently through the real planners get distinct gap-free numbers', async () => {
  const mock = createMockRuntime({ flags: {}, seed: buildSyntheticSeed() });
  const tabs = [];
  for (let i = 0; i < 2; i++) {
    const runtime = await initRuntime({ claude: mock.claude });
    const store = createStore(runtime, { batchMs: 0 });
    store.start();
    await store.whenReady();
    tabs.push({ store, runtime, repo: createRepo({ runtime, store, holderId: `tab${i}`, leaseAttempts: 800, sleepFn: () => new Promise((r) => setTimeout(r, 4)) }) });
  }
  const post = (t, amount) => t.repo.postWithNumber((no) => planPost(t.store.getState(), { entry: entry('2025-07-01', amount), no, user: t.runtime.user.id }));
  const out = await Promise.all([post(tabs[0], 10), post(tabs[1], 20), post(tabs[0], 30), post(tabs[1], 40)]);
  assert.deepEqual(out.map((r) => r.no).sort((a, b) => a - b), [11, 12, 13, 14]);
  await tick(30);
  for (const t of tabs) {
    const nos = Object.values(t.store.getState().entries).filter((e) => e.status === 'posted').map((e) => e.no).sort((a, b) => a - b);
    assert.deepEqual(nos.slice(-4), [11, 12, 13, 14], 'both tabs converge on the same books');
  }
});
