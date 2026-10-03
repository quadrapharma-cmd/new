import test from 'node:test';
import assert from 'node:assert/strict';
import { createMockRuntime } from '../mock-runtime.js';
import { buildSyntheticSeed } from '../synthetic-seed.js';
import { initRuntime } from '../../src/data/runtime.js';
import { createStore } from '../../src/data/store.js';
import { createRepo, RepoError } from '../../src/data/repo.js';
import { COLLECTIONS, SUBSCRIPTION_CAP } from '../../src/data/schema.js';
import { entryDocId } from '../../src/lib/ids.js';

async function boot({ seed = buildSyntheticSeed(), flags = {}, mockOpts = {}, repoOpts = {} } = {}) {
  const mock = createMockRuntime({ flags, seed, ...mockOpts });
  const runtime = await initRuntime({ claude: mock.claude });
  const store = createStore(runtime, { batchMs: 0 });
  store.start();
  await store.whenReady();
  const repo = createRepo({ runtime, store, sleepFn: () => new Promise((r) => setTimeout(r, 1)), ...repoOpts });
  return { mock, runtime, store, repo };
}
const tick = (ms = 5) => new Promise((r) => setTimeout(r, ms));

test('runtime wrappers are null-safe when every capability is missing', async () => {
  const rt = await initRuntime({ claude: undefined });
  assert.equal(rt.db, null);
  assert.equal(rt.caps.db, false);
  assert.equal(rt.user.canEdit(), false);
  assert.equal(rt.user.isOwner(), false);
  assert.equal(rt.user.id, null);
  assert.equal(rt.user.level, 'unknown');
  assert.deepEqual(Object.keys(await rt.user.profiles(['u1'])), ['u1']);
  assert.equal((await rt.downloads.save({ filename: 'a.json', data: '{}' })).ok, false);
  assert.equal((await rt.assets.upload(new Blob(['x']))).ok, false);
  const store = createStore(rt);
  store.start();
  assert.equal(store.getStatus().phase, 'unavailable');
});

test('runtime: owner / viewer levels come from user.me()', async () => {
  const owner = await initRuntime({ claude: createMockRuntime({ flags: {} }).claude });
  assert.equal(owner.user.level, 'owner');
  assert.equal(owner.user.canEdit(), true);
  const viewer = await initRuntime({ claude: createMockRuntime({ flags: { readOnly: true } }).claude });
  assert.equal(viewer.user.level, 'viewer');
  assert.equal(viewer.user.canEdit(), false);
  assert.equal(viewer.assets.available, false);
  assert.equal(viewer.downloads.available, true);
});

test('store: one subscription per collection, engine-state shape, ready status', async () => {
  const { store, mock } = await boot();
  const st = store.getStatus();
  assert.equal(st.phase, 'ready');
  assert.equal(st.subscriptions, COLLECTIONS.length);
  assert.ok(COLLECTIONS.length <= 30 && COLLECTIONS.length < SUBSCRIPTION_CAP);
  assert.equal(mock.db.listeners(), COLLECTIONS.length);
  const s = store.getState();
  for (const k of ['config', 'counters', 'accounts', 'groups', 'costCenters', 'sectors', 'parties', 'documents', 'entries', 'fiscalYears', 'openItems', 'assumptions', 'assets', 'depRuns', 'reconciliations', 'templates', 'registers', 'audit']) {
    assert.ok(k in s, `state.${k}`);
  }
  assert.equal(s.config.company.name, 'شركة المثال التجريبية');
  assert.equal(s.counters.nextEntryNo, 11);
  assert.equal(s.groups.length, 2);
  assert.ok(s.entries.e000001);
  assert.equal(s.entries.e000001.no, 1);
  assert.ok(s.accounts['1340']);
  assert.equal(st.counts.entries, Object.keys(s.entries).length);
  assert.equal(st.total, mock.db.size);
  assert.equal(s.fiscalYears[2024].state, 'closed_reserved');
});

test('store: defaults for an empty database and change events only touch changed collections', async () => {
  const { store, mock } = await boot({ seed: null });
  const s0 = store.getState();
  assert.equal(store.getStatus().phase, 'ready');
  assert.equal(s0.counters.nextEntryNo, 1);
  assert.equal(s0.config.settings.digits, 'western');
  assert.deepEqual(s0.groups, []);
  const events = [];
  store.subscribe((state, info) => events.push(info.changed));
  const entriesBefore = s0.entries;
  await mock.db.namespace.doc('parties/p0001').set({ id: 'p0001', name: 'اختبار' });
  await tick();
  const s1 = store.getState();
  assert.notEqual(s1, s0);
  assert.equal(s1.entries, entriesBefore, 'untouched collection keeps identity');
  assert.deepEqual(s1.parties.p0001, { id: 'p0001', name: 'اختبار' });
  assert.deepEqual(events.flat(), ['parties']);
  await mock.db.namespace.doc('parties/p0001').delete();
  await tick();
  assert.deepEqual(store.getState().parties, {});
});

test('store: a failing collection marks status error and revoked is terminal', async () => {
  const mock = createMockRuntime({ flags: {}, seed: buildSyntheticSeed() });
  const runtime = await initRuntime({ claude: mock.claude });
  const real = runtime.db.collection.bind(runtime.db);
  const patched = { ...runtime, db: { doc: runtime.db.doc, collection: (n) => (n === 'audit' ? { onSnapshot: (_n, e) => { setTimeout(() => e({ code: 'revoked' }), 1); return () => {}; } } : real(n)) } };
  const store = createStore(patched, { batchMs: 0, readyGraceMs: 50 });
  store.start();
  await tick(30);
  assert.equal(store.getStatus().phase, 'revoked');
  assert.equal(store.getStatus().errors.audit.code, 'revoked');
});

test('repo: read-only users cannot write (Arabic message), nothing is written', async () => {
  const { repo, mock } = await boot({ flags: { readOnly: true } });
  const before = mock.db.size;
  await assert.rejects(repo.applyPlan({ writes: [{ op: 'set', path: 'parties/p9', data: { id: 'p9' } }] }), (e) => e instanceof RepoError && e.code === 'read_only' && /للعرض فقط/.test(e.message));
  await assert.rejects(repo.setDoc('parties/p9', { a: 1 }), { code: 'read_only' });
  await assert.rejects(repo.appendAudit({ kind: 'x', coll: 'c', id: '1', summary: 's' }), { code: 'read_only' });
  assert.equal(mock.db.size, before);
  assert.equal(repo.canEdit(), false);
});

test('repo: without db every write fails with an Arabic message', async () => {
  const rt = await initRuntime({ claude: undefined });
  const repo = createRepo({ runtime: rt, store: createStore(rt) });
  await assert.rejects(repo.setDoc('a/b', {}), { code: 'no_db' });
});

test('repo.applyPlan: sequential writes, merge update, delete, audit event appended', async () => {
  const { repo, mock, store } = await boot();
  const res = await repo.applyPlan({
    writes: [
      { op: 'set', path: 'parties/p0100', data: { id: 'p0100', name: 'طرف جديد', aliases: [] } },
      { op: 'update', path: 'parties/p0100', data: { aliases: ['اسم بديل'] } },
      { op: 'delete', path: 'documents/D0004' },
    ],
    audit: { kind: 'create', coll: 'parties', id: 'p0100', summary: 'إضافة طرف', reason: 'اختبار' },
  });
  assert.equal(res.applied, 3);
  assert.equal(res.auditOk, true);
  await tick();
  const dump = mock.db.dump();
  assert.deepEqual(dump['parties/p0100'].aliases, ['اسم بديل']);
  assert.equal(dump['documents/D0004'], undefined);
  const ym = new Date().toISOString().slice(0, 7);
  const ev = dump[`audit/${ym}`].events.at(-1);
  assert.equal(ev.kind, 'create');
  assert.equal(ev.reason, 'اختبار');
  assert.equal(ev.by, 'u_mock_owner');
  assert.ok(ev.at);
  assert.ok(store.getState().parties.p0100);
});

test('repo.applyPlan: invalid plans are refused before any write; partial failure reports progress', async () => {
  const { repo, mock } = await boot();
  const before = mock.db.size;
  for (const bad of [null, {}, { writes: [{ op: 'set', path: 'a', data: {} }] }, { writes: [{ op: 'nope', path: 'a/b', data: {} }] }, { writes: [{ op: 'set', path: 'a/b', data: [1] }] }]) {
    await assert.rejects(repo.applyPlan(bad), { code: 'bad_plan' });
  }
  await assert.rejects(repo.applyPlan({ writes: [{ op: 'set', path: 'a/b', data: { big: 'x'.repeat(300 * 1024) } }] }), { code: 'doc_too_big' });
  assert.equal(mock.db.size, before);
  // second write fails (update of a missing doc): first one is applied and reported
  await assert.rejects(
    repo.applyPlan({ writes: [{ op: 'set', path: 'parties/p0200', data: { id: 'p0200' } }, { op: 'update', path: 'parties/missing', data: { a: 1 } }] }),
    (e) => e.code === 'invalid_argument' && e.applied === 1 && e.total === 2 && /نُفِّذ/.test(e.message),
  );
});

test('repo: transient unavailable is retried once; quota error carries an Arabic message', async () => {
  const { repo, mock } = await boot();
  mock.failNext('set', 'unavailable', 1);
  await repo.setDoc('parties/p0300', { id: 'p0300' });
  assert.ok(mock.db.dump()['parties/p0300']);
  mock.failNext('set', 'unavailable', 2);
  await assert.rejects(repo.setDoc('parties/p0301', { id: 'p0301' }), (e) => e.code === 'unavailable' && /مؤقتاً/.test(e.message));
  mock.failNext('set', 'quota_exceeded', 1);
  await assert.rejects(repo.setDoc('parties/p0302', { id: 'p0302' }), (e) => e.code === 'quota_exceeded' && /5,000/.test(e.message));
});

test('entry numbers: concurrent allocation from two tabs never double-issues and stays gap-free', async () => {
  const mock = createMockRuntime({ flags: {}, seed: buildSyntheticSeed() });
  let tabNo = 0;
  const mk = async () => {
    const runtime = await initRuntime({ claude: mock.claude });
    const store = createStore(runtime, { batchMs: 0 });
    store.start();
    await store.whenReady();
    return createRepo({ runtime, store, holderId: `tab${(tabNo += 1)}`, leaseAttempts: 800, sleepFn: () => new Promise((r) => setTimeout(r, 4)) });
  };
  const [a, b] = [await mk(), await mk()];
  const post = (repo, tag) => repo.postWithNumber((no) => ({
    writes: [{ op: 'set', path: `entries/${entryDocId(no)}`, data: { no, status: 'posted', desc: tag, date: '2025-04-01', fy: 2025, lines: [] } }],
    audit: { kind: 'post', coll: 'entries', id: entryDocId(no), summary: tag },
  }));
  const results = await Promise.all([post(a, 'a1'), post(b, 'b1'), post(a, 'a2'), post(b, 'b2'), post(a, 'a3'), post(b, 'b3')]);
  const nos = results.map((r) => r.no).sort((x, y) => x - y);
  assert.deepEqual(nos, [11, 12, 13, 14, 15, 16], 'unique and gap-free, continuing after the seed max');
  assert.equal((await mock.db.namespace.doc('meta/counters').get()).data().nextEntryNo, 17);
  const posted = Object.entries(mock.db.dump()).filter(([p]) => /^entries\/e0000(1[1-6])$/.test(p));
  assert.equal(posted.length, 6);
});

test('entry numbers: a failed post releases the number (no gap), counter untouched', async () => {
  const { repo, mock } = await boot();
  await assert.rejects(repo.postWithNumber(() => { throw new RepoError('validation', 'غير صالح'); }), { code: 'validation' });
  assert.equal((await mock.db.namespace.doc('meta/counters').get()).data().nextEntryNo, 11);
  const r = await repo.postWithNumber((no) => ({ writes: [{ op: 'set', path: `entries/${entryDocId(no)}`, data: { no, status: 'posted' } }] }));
  assert.equal(r.no, 11);
});

test('entry numbers: counter behind reality is corrected from the entries themselves', async () => {
  const seed = buildSyntheticSeed();
  seed.meta.counters = { nextEntryNo: 3 };
  const { repo } = await boot({ seed });
  const h = await repo.allocateEntryNo();
  assert.equal(h.no, 11, 'max(existing no)+1 wins over a stale counter');
  await h.release();
});

test('applyPlan with a numbered entry refuses to overwrite an existing number', async () => {
  const { repo, mock } = await boot();
  await assert.rejects(
    repo.applyPlan({ entryNo: 5, writes: [{ op: 'set', path: `entries/${entryDocId(5)}`, data: { no: 5, status: 'posted' } }] }),
    (e) => e.code === 'number_taken' && /رقم القيد/.test(e.message),
  );
  const r = await repo.applyPlan({ entryNo: 11, writes: [{ op: 'set', path: `entries/${entryDocId(11)}`, data: { no: 11, status: 'posted' } }] });
  assert.equal(r.entryNo, 11);
  assert.equal((await mock.db.namespace.doc('meta/counters').get()).data().nextEntryNo, 12);
});

test('lease busy: a lease held elsewhere surfaces an Arabic error after the retries', async () => {
  const { repo, mock } = await boot({ repoOpts: { leaseAttempts: 3 } });
  await mock.db.namespace.doc('meta/counters').acquire({ holder: 'someone-else', ttlMs: 60000 });
  await assert.rejects(repo.allocateEntryNo(), (e) => e.code === 'lease_busy' && /مستخدم آخر/.test(e.message));
  mock.db.expireLeases();
  const h = await repo.allocateEntryNo();
  assert.equal(h.no, 11);
  await h.release();
});

test('audit: appends to the month doc and rolls to -b past ~180 KiB', async () => {
  const { repo, mock } = await boot({ seed: null });
  const ym = new Date().toISOString().slice(0, 7);
  await repo.appendAudit({ kind: 'k', coll: 'c', id: '1', summary: 'first' });
  assert.equal(mock.db.dump()[`audit/${ym}`].events.length, 1);
  await repo.appendAudit({ kind: 'k', coll: 'c', id: '2', summary: 'second', reason: 'r' });
  assert.deepEqual(mock.db.dump()[`audit/${ym}`].events.map((e) => e.summary), ['first', 'second']);
  const filler = Array.from({ length: 700 }, (_, i) => ({ at: 'x', by: 'u', kind: 'k', coll: 'c', id: String(i), summary: 'ص'.repeat(120) }));
  await mock.db.namespace.doc(`audit/${ym}`).set({ events: filler });
  assert.ok(JSON.stringify(mock.db.dump()[`audit/${ym}`]).length > 180 * 1024 / 2);
  const out = await repo.appendAudit({ kind: 'k', coll: 'c', id: '3', summary: 'third' });
  assert.equal(out.path, `audit/${ym}-b`);
  assert.equal(mock.db.dump()[`audit/${ym}-b`].events[0].summary, 'third');
  assert.equal(mock.db.dump()[`audit/${ym}`].events.length, 700);
});

test('audit failure does not fail the save but is reported', async () => {
  const { repo, mock } = await boot();
  mock.failNext('acquire', 'resource_exhausted', 20);
  const r = await repo.applyPlan({ writes: [{ op: 'set', path: 'parties/p0400', data: { id: 'p0400' } }], audit: { kind: 'k', coll: 'parties', id: 'p0400', summary: 's' } });
  assert.equal(r.applied, 1);
  assert.ok(mock.db.dump()['parties/p0400']);
});

test('claimSeqId: skips taken ids and survives acquire creating empty docs', async () => {
  const { repo, mock } = await boot({ mockOpts: { acquireCreatesDoc: true } });
  const id1 = await repo.claimSeqId('parties', 'p', 4);
  assert.equal(id1, 'p0007');
  await mock.db.namespace.doc(`parties/${id1}`).set({ id: id1, name: 'x' });
  const id2 = await repo.claimSeqId('parties', 'p', 4);
  assert.equal(id2, 'p0008');
});

test('uploadAsset: validates type and size, returns the documents.files[] shape', async () => {
  const { repo, mock } = await boot();
  const pdf = new File([new Uint8Array(1000)], 'كشف.pdf', { type: 'application/pdf' });
  const out = await repo.uploadAsset(pdf);
  assert.match(out.assetId, /^[0-9a-f]{32}$/);
  assert.deepEqual({ name: out.name, size: out.size, type: out.type }, { name: 'كشف.pdf', size: 1000, type: 'application/pdf' });
  assert.equal(mock.calls.uploads.length, 1);
  await assert.rejects(repo.uploadAsset(new File(['x'], 'a.exe', { type: 'application/x-msdownload' })), { code: 'bad_type' });
  await assert.rejects(repo.uploadAsset(new File(['x'], 'a.heic', { type: 'image/heic' })), (e) => e.code === 'heic' && /HEIC/.test(e.message));
  await assert.rejects(repo.uploadAsset(new File([], 'a.png', { type: 'image/png' })), { code: 'empty' });
  const big = { name: 'big.pdf', type: 'application/pdf', size: 21 * 1048576 };
  await assert.rejects(repo.uploadAsset(big), (e) => e.code === 'too_large' && /MiB/.test(e.message));
  const { repo: ro } = await boot({ flags: { readOnly: true } });
  await assert.rejects(ro.uploadAsset(pdf), { code: 'read_only' });
});

test('plans refused by the engine (ok:false) are never applied and carry the engine message', async () => {
  const { repo, mock } = await boot();
  const before = mock.db.size;
  const refused = { ok: false, writes: [], errors: [{ code: 'unbalanced', msg: 'القيد غير متوازن — الفرق 10.00' }], audit: null };
  await assert.rejects(repo.applyPlan(refused), (e) => e.code === 'plan_rejected' && /غير متوازن/.test(e.message) && e.errors.length === 1);
  await assert.rejects(repo.postWithNumber(() => refused), (e) => e.code === 'plan_rejected');
  assert.equal(mock.db.size, before);
  assert.equal((await mock.db.namespace.doc('meta/counters').get()).data().nextEntryNo, 11, 'a refused plan never advances the counter');
  const ok = await repo.applyPlan({ ok: true, writes: [{ op: 'set', path: 'parties/p0500', data: { id: 'p0500' } }], audit: null, errors: [] });
  assert.equal(ok.applied, 1);
});

test('readDoc returns fresh data or null', async () => {
  const { repo, mock } = await boot();
  assert.equal((await repo.readDoc('entries/e000001')).no, 1);
  assert.equal(await repo.readDoc('entries/e999999'), null);
  const rt = await initRuntime({ claude: undefined });
  await assert.rejects(createRepo({ runtime: rt, store: createStore(rt) }).readDoc('a/b'), { code: 'no_db' });
});
