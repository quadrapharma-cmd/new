import test from 'node:test';
import assert from 'node:assert/strict';
import { createMockRuntime } from '../mock-runtime.js';

const mk = (opts = {}) => {
  const m = createMockRuntime({ flags: {}, ...opts });
  return { m, db: m.db.namespace };
};

test('path grammar throws TypeError synchronously', () => {
  const { db } = mk();
  assert.throws(() => db.doc('a'), TypeError);
  assert.throws(() => db.collection('a/b'), TypeError);
  assert.throws(() => db.doc('a/..'), TypeError);
  assert.throws(() => db.doc('a/b c'), TypeError);
  assert.doesNotThrow(() => db.doc('a/b'));
  assert.doesNotThrow(() => db.collection('a/b/c'));
});

test('set replaces, update merges objects and replaces arrays, update needs existence', async () => {
  const { db } = mk();
  const ref = db.doc('c/x');
  await assert.rejects(ref.update({ a: 1 }), { code: 'invalid_argument' });
  await ref.set({ a: 1, o: { p: 1, q: 2 }, arr: [1, 2, 3] });
  await ref.update({ o: { q: 9, r: 3 }, arr: [7] });
  assert.deepEqual((await ref.get()).data(), { a: 1, o: { p: 1, q: 9, r: 3 }, arr: [7] });
  await ref.set({ b: 2 });
  assert.deepEqual((await ref.get()).data(), { b: 2 });
  await ref.delete();
  await ref.delete();
  assert.equal((await ref.get()).exists, false);
});

test('snapshot data is frozen and shared; bodies must be plain objects within limits', async () => {
  const { db } = mk();
  await db.doc('c/x').set({ a: { b: 1 } });
  const d = (await db.doc('c/x').get()).data();
  assert.throws(() => {
    'use strict';
    d.a.b = 2;
  });
  assert.equal((await db.doc('c/x').get()).data(), d, 'unchanged doc keeps object identity');
  await assert.rejects(db.doc('c/y').set([1]), { code: 'invalid_argument' });
  await assert.rejects(db.doc('c/y').set({ n: NaN }), { code: 'invalid_argument' });
  await assert.rejects(db.doc('c/y').set({ big: 'x'.repeat(300 * 1024) }), { code: 'invalid_argument' });
  let deep = { v: 1 };
  for (let i = 0; i < 33; i++) deep = { n: deep };
  await assert.rejects(db.doc('c/y').set(deep), { code: 'invalid_argument' });
});

test('5,000 document cap: creates fail with quota_exceeded, writes to existing docs still work', async () => {
  const { m, db } = mk();
  const seed = {};
  for (let i = 0; i < 5000; i++) (seed.big ||= {})[`d${i}`] = { i };
  m.db.load(seed);
  assert.equal(m.db.size, 5000);
  await assert.rejects(db.doc('other/new').set({ a: 1 }), { code: 'quota_exceeded' });
  await db.doc('big/d1').set({ i: 'changed' });
  assert.equal((await db.doc('big/d1').get()).data().i, 'changed');
});

test('queries: where/orderBy/limit, missing field sorts last, default order by id', async () => {
  const { db } = mk();
  await db.doc('n/b').set({ no: 2, k: 'x' });
  await db.doc('n/a').set({ no: 10, k: 'y' });
  await db.doc('n/c').set({ no: null });
  await db.doc('n/d').set({ other: 1 });
  const ids = async (q) => (await q.get()).docs.map((d) => d.id);
  assert.deepEqual(await ids(db.collection('n')), ['a', 'b', 'c', 'd']);
  assert.deepEqual(await ids(db.collection('n').orderBy('no', 'desc')), ['a', 'b', 'c', 'd']);
  assert.deepEqual(await ids(db.collection('n').where('no', '>=', 1).orderBy('no', 'desc').limit(1)), ['a']);
  assert.deepEqual(await ids(db.collection('n').where('k', 'in', ['x', 'y']).orderBy('no')), ['b', 'a']);
  assert.deepEqual(await ids(db.collection('n').where('k', '!=', 'x')), ['a']);
  await assert.rejects(db.collection('n').where('k', '~', 1).get(), { code: 'invalid_argument' });
  await assert.rejects(db.collection('n').limit(0).get(), { code: 'invalid_argument' });
  // nested docs are not part of the parent collection
  await db.doc('n/a/sub/z').set({ no: 1 });
  assert.deepEqual(await ids(db.collection('n')), ['a', 'b', 'c', 'd']);
});

test('acquire: busy for another holder, renewable by the same holder, expires', async () => {
  const { m, db } = mk();
  const ref = db.doc('meta/counters');
  assert.equal((await ref.acquire({ holder: 'A', ttlMs: 5000 })).acquired, true);
  const busy = await ref.acquire({ holder: 'B' });
  assert.equal(busy.acquired, false);
  assert.ok(busy.expiresAt);
  assert.equal(busy.holder, undefined);
  assert.equal((await ref.acquire({ holder: 'A', ttlMs: 1000 })).acquired, true);
  m.db.expireLeases();
  assert.equal((await ref.acquire({ holder: 'B' })).acquired, true);
  // acquire does not create a body unless data is given
  assert.equal((await db.doc('meta/none').get()).exists, false);
  await db.doc('meta/none').acquire({ holder: 'A' });
  assert.equal((await db.doc('meta/none').get()).exists, false);
  await db.doc('meta/none').acquire({ holder: 'A', data: { k: 1 } });
  assert.deepEqual((await db.doc('meta/none').get()).data(), { k: 1 });
});

test('onSnapshot: first delivery, docChanges, unchanged docs keep identity, unsubscribe stops delivery', async () => {
  const { db } = mk();
  await db.doc('c/a').set({ v: 1 });
  const seen = [];
  const un = db.collection('c').onSnapshot((s) => seen.push(s));
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(seen.length, 1);
  assert.equal(seen[0].size, 1);
  assert.equal(seen[0].docChanges()[0].type, 'added');
  const a1 = seen[0].docs[0].data();
  await db.doc('c/b').set({ v: 2 });
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(seen.length, 2);
  assert.deepEqual(seen[1].docChanges().map((c) => c.type), ['added']);
  assert.equal(seen[1].docs[0].data(), a1);
  await db.doc('c/a').update({ v: 5 });
  await db.doc('c/b').delete();
  await new Promise((r) => setTimeout(r, 5));
  const types = seen.slice(2).flatMap((s) => s.docChanges().map((c) => c.type)).sort();
  assert.deepEqual(types, ['modified', 'removed']);
  un();
  const n = seen.length;
  await db.doc('c/z').set({ v: 1 });
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(seen.length, n);
});

test('64 live subscriptions per view: the 65th gets resource_exhausted', async () => {
  const { db } = mk();
  const errors = [];
  for (let i = 0; i < 65; i++) db.collection('c').onSnapshot(() => {}, (e) => errors.push(e));
  await new Promise((r) => setTimeout(r, 10));
  assert.equal(errors.length, 1);
  assert.equal(errors[0].code, 'resource_exhausted');
});

test('read-only flag: writes reject, assets capability is null, user reports viewer', async () => {
  const { m, db } = mk();
  m.flags.readOnly = true;
  await assert.rejects(db.doc('c/x').set({ a: 1 }), { code: 'invalid_argument' });
  assert.equal(await m.claude.use('assets'), null);
  const u = await m.claude.use('user');
  assert.equal(await u.canEdit(), false);
  assert.equal(await u.isOwner(), false);
  m.flags.readOnly = false;
  const m2 = createMockRuntime({ flags: {} });
  assert.ok(await m2.claude.use('assets'));
  assert.equal(await (await m2.claude.use('user')).canEdit(), true);
});

test('capability flags: nodb / nouser resolve null', async () => {
  const m = createMockRuntime({ flags: { noDb: true, noUser: true } });
  assert.equal(await m.claude.use('db'), null);
  assert.equal(await m.claude.use('user'), null);
  assert.equal(await m.claude.use('unknown'), null);
});

test('downloads: allowlist, records calls; assets: type and size rules', async () => {
  const m = createMockRuntime({ flags: {} });
  const dl = await m.claude.use('downloads');
  await assert.rejects(dl.save({ filename: 'x.exe', data: 'a' }), { code: 'rejected_extension' });
  await assert.rejects(dl.save({ filename: 'x.json', data: '' }), { code: 'bad_request' });
  assert.deepEqual(await dl.save({ filename: 'backup.json', data: '{"a":1}' }), { status: 'saved' });
  assert.equal(m.calls.downloads.length, 1);
  assert.equal(m.calls.downloads[0].filename, 'backup.json');
  m.flags.declineDownloads = true;
  await assert.rejects(dl.save({ filename: 'b.json', data: '{}' }), { code: 'declined' });
  const as = await m.claude.use('assets');
  await assert.rejects(as.upload('nope'), { code: 'invalid_request' });
  await assert.rejects(as.upload(new Blob([new Uint8Array(0)], { type: 'image/png' })), { code: 'invalid_request' });
  await assert.rejects(as.upload(new Blob(['x'], { type: 'application/zip' })), { code: 'unsupported_type' });
  await assert.rejects(as.upload(new Blob([new Uint8Array(21 * 1048576)], { type: 'application/pdf' })), { code: 'too_large' });
  const r = await as.upload(new Blob(['%PDF'], { type: 'application/pdf' }));
  assert.match(r.id, /^[0-9a-f]{32}$/);
  assert.equal(r.url, `/_blob/${r.id}`);
  assert.equal((await as.list()).assets.length, 1);
  assert.deepEqual(await as.delete(r.id), { deleted: true });
  assert.deepEqual(await as.delete(r.id), { deleted: false });
});

test('failNext injects transient errors once', async () => {
  const { m, db } = mk();
  m.failNext('set', 'unavailable', 1);
  await assert.rejects(db.doc('c/x').set({ a: 1 }), { code: 'unavailable' });
  await db.doc('c/x').set({ a: 1 });
  assert.equal((await db.doc('c/x').get()).exists, true);
});
