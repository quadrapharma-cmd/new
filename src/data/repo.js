// Write side of the data layer. Engine mutators are pure and return write plans:
//   { writes:[{op:'set'|'update'|'delete', path:'entries/e000312', data?}], audit:{kind,coll,id,reason?,summary}, entryNo?:number }
// applyPlan() runs them sequentially (there are no transactions), allocates entry numbers under a lease on
// meta/counters, appends the audit event, and turns platform errors into Arabic RepoError messages.
// Every write checks canEdit() first.
import { S, fmt } from '../lib/i18n.js';
import { jsonBytes, formatBytes, sleep, jitter } from '../lib/format.js';
import { entryDocId, isPlainObject, newId, nextSeqId, seqOf, pad, tabId } from '../lib/ids.js';
import { AUDIT_ROLL_BYTES, DOC_BYTES_CAP, MAX_UPLOAD_BYTES, auditDocId } from './schema.js';

export { newId };

export class RepoError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.name = 'RepoError';
    this.code = code;
    Object.assign(this, extra);
  }
}

/** Platform/db error -> RepoError with an Arabic message. RepoErrors pass through unchanged. */
export function toRepoError(e) {
  if (e instanceof RepoError) return e;
  const code = e?.code || 'unknown';
  const map = {
    quota_exceeded: S.repo.quota,
    resource_exhausted: S.repo.rate,
    unavailable: S.repo.unavailable,
    invalid_argument: S.repo.invalid,
    transform_error: S.repo.invalid,
    revoked: S.repo.revoked,
    not_granted: S.repo.notGranted,
    capability_disabled: S.repo.notGranted,
    capability_removed: S.repo.notGranted,
  };
  return new RepoError(code, map[code] || S.repo.unknown, { cause: e });
}

const UPLOAD_TYPES = {
  pdf: 'application/pdf',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
};

export function createRepo({ runtime, store, sleepFn = sleep, leaseTtlMs = 20000, leaseAttempts = 12, now = () => new Date(), holderId = tabId() }) {
  const { user } = runtime;
  // One holder per tab for the counters and audit leases: in-tab mutexes serialise those flows, and a shared holder
  // lets a flow renew the lease at once instead of waiting for the previous one to lapse. Slot claims use a fresh holder.
  const tabHolder = `${user.id || 'anon'}:${holderId}`;
  let holderSeq = 0;
  const nextHolder = () => `${tabHolder}:${(holderSeq += 1)}`;

  function assertCanEdit() {
    if (!runtime.db) throw new RepoError('no_db', S.repo.noDb);
    if (!user.canEdit()) throw new RepoError('read_only', S.repo.readOnly);
  }
  const db = () => runtime.db;

  /** Run a db call; one automatic retry (after a random pause) for transient `unavailable`. */
  async function call(fn) {
    try {
      return await fn();
    } catch (e) {
      if (e?.code === 'unavailable') {
        await sleepFn(jitter(400, 400));
        try {
          return await fn();
        } catch (e2) {
          throw toRepoError(e2);
        }
      }
      throw toRepoError(e);
    }
  }

  // ---------- leases ----------
  async function acquire(path, holder, ttlMs) {
    return call(() => db().doc(path).acquire({ holder, ttlMs }));
  }
  async function shorten(path, holder) {
    try {
      await db().doc(path).acquire({ holder, ttlMs: 1000 });
    } catch {
      /* the lease expires by itself */
    }
  }
  async function acquireWithRetry(path, holder, ttlMs, attempts) {
    for (let i = 0; i < attempts; i++) {
      const r = await acquire(path, holder, ttlMs);
      if (r.acquired) return true;
      await sleepFn(jitter(120 * (i + 1), 200));
    }
    return false;
  }

  // in-tab mutexes: leases are per holder, so two flows in one tab must not interleave
  const makeMutex = () => {
    let chain = Promise.resolve();
    return (fn) => {
      const run = chain.then(fn, fn);
      chain = run.catch(() => {});
      return run;
    };
  };
  const inTab = makeMutex(); // meta/counters
  const inAudit = makeMutex(); // audit month docs

  async function withNumberLease(fn) {
    return inTab(async () => {
      const holder = tabHolder;
      if (!(await acquireWithRetry('meta/counters', holder, leaseTtlMs, leaseAttempts))) throw new RepoError('lease_busy', S.repo.leaseBusy);
      try {
        return await fn();
      } finally {
        await shorten('meta/counters', holder);
      }
    });
  }

  async function computeNextNo() {
    let fromCounter = 1;
    const snap = await call(() => db().doc('meta/counters').get());
    if (snap.exists) fromCounter = Number(snap.data()?.nextEntryNo) || 1;
    let freshMax = 0;
    try {
      const q = await db().collection('entries').where('no', '>=', 1).orderBy('no', 'desc').limit(1).get();
      if (!q.empty) freshMax = Number(q.docs[0].data()?.no) || 0;
    } catch {
      /* fall back to what the store already knows */
    }
    let stateMax = 0;
    for (const e of Object.values(store?.getState().entries || {})) if (e && Number.isInteger(e.no) && e.no > stateMax) stateMax = e.no;
    return Math.max(fromCounter, freshMax + 1, stateMax + 1);
  }

  async function bumpCounters(nextNo) {
    const ref = db().doc('meta/counters');
    const snap = await call(() => ref.get());
    const cur = snap.exists ? Number(snap.data()?.nextEntryNo) || 1 : 0;
    if (!snap.exists) await call(() => ref.set({ nextEntryNo: nextNo }));
    else if (nextNo > cur) await call(() => ref.update({ nextEntryNo: nextNo }));
  }

  /**
   * Reserve the next entry number. Holds a lease on meta/counters until commit() or release().
   * commit() advances the counter (call it only after the entry document was written: numbers stay gap-free);
   * release() abandons the number. Prefer postWithNumber(), which does all of this.
   */
  async function allocateEntryNo() {
    assertCanEdit();
    let finish;
    const gate = new Promise((r) => (finish = r));
    const started = new Promise((resolve, reject) => {
      inTab(async () => {
        const holder = tabHolder;
        try {
          if (!(await acquireWithRetry('meta/counters', holder, leaseTtlMs, leaseAttempts))) throw new RepoError('lease_busy', S.repo.leaseBusy);
          const no = await computeNextNo();
          let done = false;
          const settle = async (commit) => {
            if (done) return;
            done = true;
            try {
              if (commit) await bumpCounters(no + 1);
            } finally {
              await shorten('meta/counters', holder);
              finish();
            }
          };
          const guard = setTimeout(() => settle(false), leaseTtlMs);
          guard?.unref?.();
          resolve({
            no,
            commit: async () => {
              clearTimeout(guard);
              await settle(true);
            },
            release: async () => {
              clearTimeout(guard);
              await settle(false);
            },
          });
        } catch (e) {
          reject(toRepoError(e));
          finish();
        }
        await gate;
      });
    });
    return started;
  }

  // ---------- plans ----------
  function checkWrite(w, i) {
    const bad = () => new RepoError('bad_plan', S.repo.badPlan, { index: i });
    if (!isPlainObject(w) || typeof w.path !== 'string') throw bad();
    const parts = w.path.split('/');
    if (parts.length % 2 !== 0 || parts.some((p) => !p)) throw bad();
    if (!['set', 'update', 'delete'].includes(w.op)) throw bad();
    if (w.op !== 'delete') {
      if (!isPlainObject(w.data)) throw bad();
      if (jsonBytes(w.data) > DOC_BYTES_CAP) throw new RepoError('doc_too_big', S.repo.docTooBig, { index: i, path: w.path });
    }
  }

  /** A plan the engine refused (ok:false) is never applied: surface its first Arabic messages instead. */
  function assertPlanOk(plan) {
    if (isPlainObject(plan) && plan.ok === false) {
      const errors = Array.isArray(plan.errors) ? plan.errors : [];
      const msg = errors.map((e) => e && (e.msg || e.message)).filter(Boolean).slice(0, 3).join(' — ') || S.repo.badPlan;
      throw new RepoError('plan_rejected', msg, { errors, plan });
    }
  }

  async function execPlan(plan, { checkNumber = false } = {}) {
    assertPlanOk(plan);
    if (!isPlainObject(plan) || !Array.isArray(plan.writes)) throw new RepoError('bad_plan', S.repo.badPlan);
    plan.writes.forEach(checkWrite);
    if (checkNumber && plan.entryNo != null) {
      const path = `entries/${entryDocId(plan.entryNo)}`;
      if (plan.writes.some((w) => w.op === 'set' && w.path === path)) {
        const snap = await call(() => db().doc(path).get());
        if (snap.exists) throw new RepoError('number_taken', fmt(S.repo.numberTaken, { no: plan.entryNo }), { no: plan.entryNo });
      }
    }
    let applied = 0;
    for (const w of plan.writes) {
      try {
        const ref = db().doc(w.path);
        await call(() => (w.op === 'set' ? ref.set(w.data) : w.op === 'update' ? ref.update(w.data) : ref.delete()));
        applied += 1;
      } catch (e) {
        const re = toRepoError(e);
        if (applied > 0) {
          re.message = `${re.message} ${fmt(S.repo.partial, { done: applied, total: plan.writes.length })}`;
        }
        re.applied = applied;
        re.total = plan.writes.length;
        throw re;
      }
    }
    return applied;
  }

  async function finishAudit(plan, skip) {
    if (skip || !plan.audit) return true;
    try {
      await appendAudit(plan.audit);
      return true;
    } catch {
      return false;
    }
  }

  /** Apply a write plan. Resolves { ok, applied, auditOk, entryNo }. Throws RepoError (Arabic message). */
  async function applyPlan(plan, { skipAudit = false } = {}) {
    assertCanEdit();
    if (!isPlainObject(plan)) throw new RepoError('bad_plan', S.repo.badPlan);
    assertPlanOk(plan);
    let applied;
    if (plan.entryNo != null) {
      applied = await withNumberLease(async () => {
        const n = await execPlan(plan, { checkNumber: true });
        await bumpCounters(plan.entryNo + 1);
        return n;
      });
    } else {
      applied = await execPlan(plan);
    }
    const auditOk = await finishAudit(plan, skipAudit);
    return { ok: true, applied, auditOk, entryNo: plan.entryNo ?? null };
  }

  /**
   * Post with a fresh gap-free number: buildPlan(no) must return a plan (it may throw a validation error).
   * Lease -> number -> plan -> writes -> counter bump -> release.
   */
  async function postWithNumber(buildPlan, { skipAudit = false } = {}) {
    assertCanEdit();
    const h = await allocateEntryNo();
    let plan;
    try {
      plan = await buildPlan(h.no);
      if (!isPlainObject(plan)) throw new RepoError('bad_plan', S.repo.badPlan);
      assertPlanOk(plan);
      plan = { ...plan, entryNo: h.no };
      const applied = await execPlan(plan, { checkNumber: true });
      await h.commit();
      const auditOk = await finishAudit(plan, skipAudit);
      return { ok: true, applied, auditOk, entryNo: h.no, no: h.no };
    } catch (e) {
      await h.release();
      throw toRepoError(e);
    }
  }

  // ---------- audit ----------
  /** Append an event to audit/YYYY-MM (rolls to -b, -c ... past ~180 KiB). Read-modify-write under a lease on the month doc. */
  async function appendAudit(ev) {
    assertCanEdit();
    const at = now().toISOString();
    const event = { at, by: user.id || null, kind: ev.kind, coll: ev.coll, id: ev.id, summary: ev.summary };
    if (ev.reason) event.reason = ev.reason;
    const ym = at.slice(0, 7);
    const lockPath = `audit/${auditDocId(ym)}`;
    return inAudit(async () => {
      // best effort: the audit trail must never block a save, so a busy lease only downgrades to an unlocked append
      const locked = await acquireWithRetry(lockPath, tabHolder, 8000, 5).catch(() => false);
      try {
        for (const suf of ['', ...'bcdefghijklmnopqrstuvwxyz']) {
          const path = `audit/${auditDocId(ym, suf)}`;
          const snap = await call(() => db().doc(path).get());
          const data = snap.exists ? snap.data() || {} : null;
          if (data && jsonBytes(data) >= AUDIT_ROLL_BYTES) continue;
          if (!data) await call(() => db().doc(path).set({ events: [event] }));
          else await call(() => db().doc(path).update({ events: [...(Array.isArray(data.events) ? data.events : []), event] }));
          return { path, rolled: suf !== '' };
        }
        throw new RepoError('audit_full', S.repo.auditFailed);
      } finally {
        if (locked) await shorten(lockPath, tabHolder);
      }
    });
  }

  // ---------- ids ----------
  /**
   * Claim a sequential id such as p0123 / D0045 without clobbering a concurrent creator:
   * lease the candidate document, read it, and move on to the next number if it already holds data.
   * Returns the id; the caller then writes the document with set().
   */
  async function claimSeqId(collection, prefix, width) {
    assertCanEdit();
    const ids = Object.keys(store?.getState()[collection] || {});
    let n = seqOf(nextSeqId(ids, prefix, width), prefix);
    const holder = nextHolder();
    for (let tries = 0; tries < 40; tries++, n++) {
      const id = `${prefix}${pad(n, width)}`;
      const path = `${collection}/${id}`;
      const r = await acquire(path, holder, 8000);
      if (!r.acquired) continue;
      const snap = await call(() => db().doc(path).get());
      const body = snap.exists ? snap.data() : null;
      if (!body || !Object.keys(body).length) return id;
    }
    throw new RepoError('id_claim_failed', S.repo.leaseBusy);
  }

  // ---------- assets ----------
  function extOf(name) {
    const m = /\.([a-z0-9]+)$/i.exec(name || '');
    return m ? m[1].toLowerCase() : '';
  }
  /** Validate a File for upload; returns { type } or throws a RepoError with an Arabic message. */
  function checkUpload(file) {
    const ext = extOf(file?.name);
    if (!file || !file.size) throw new RepoError('empty', S.repo.upload.empty);
    if (ext === 'heic' || ext === 'heif' || /heic|heif/i.test(file.type || '')) throw new RepoError('heic', S.repo.upload.heic);
    const type = UPLOAD_TYPES[ext] || (Object.values(UPLOAD_TYPES).includes(file.type) ? file.type : null);
    if (!type) throw new RepoError('bad_type', S.repo.upload.badType);
    if (file.size > MAX_UPLOAD_BYTES) {
      throw new RepoError('too_large', fmt(S.repo.upload.tooLarge, { size: formatBytes(file.size), max: formatBytes(MAX_UPLOAD_BYTES) }));
    }
    return { type };
  }
  /** Upload a File via the assets capability. Resolves { assetId, name, size, type } (the documents.files[] shape). */
  async function uploadAsset(file) {
    assertCanEdit();
    const { type } = checkUpload(file);
    if (!runtime.assets.available) throw new RepoError('assets_unavailable', S.repo.upload.unavailable);
    let r = await runtime.assets.upload(file, { type });
    if (!r.ok && r.code === 'store_unavailable') {
      await sleepFn(jitter(500, 400));
      r = await runtime.assets.upload(file, { type });
    }
    if (!r.ok) {
      const msg = {
        too_large: S.repo.upload.tooLarge,
        unsupported_type: S.repo.upload.badType,
        quota_or_state: S.repo.upload.quota,
        rate_limited: S.repo.upload.rate,
        not_granted: S.repo.upload.unavailable,
        capability_disabled: S.repo.upload.unavailable,
        capability_removed: S.repo.upload.unavailable,
      }[r.code];
      const text = r.code === 'too_large' ? fmt(msg, { size: formatBytes(file.size), max: formatBytes(MAX_UPLOAD_BYTES) }) : msg;
      throw new RepoError(r.code, text || S.repo.upload.failed);
    }
    return { assetId: r.id, name: file.name, size: r.sizeBytes ?? file.size, type: r.contentType ?? type };
  }

  // ---------- reads ----------
  /** Fresh read straight from the db (not the live state): use right before planning an amend/void (optimistic version check). */
  async function readDoc(path) {
    if (!runtime.db) throw new RepoError('no_db', S.repo.noDb);
    const snap = await call(() => db().doc(path).get());
    return snap.exists ? snap.data() : null;
  }

  // ---------- single-document helpers ----------
  async function setDoc(path, data) {
    return applyPlan({ writes: [{ op: 'set', path, data }] }, { skipAudit: true });
  }
  async function updateDoc(path, data) {
    return applyPlan({ writes: [{ op: 'update', path, data }] }, { skipAudit: true });
  }
  async function deleteDoc(path) {
    return applyPlan({ writes: [{ op: 'delete', path }] }, { skipAudit: true });
  }

  return {
    canEdit: () => !!runtime.db && user.canEdit(),
    assertCanEdit,
    applyPlan,
    postWithNumber,
    allocateEntryNo,
    appendAudit,
    claimSeqId,
    readDoc,
    uploadAsset,
    checkUpload,
    setDoc,
    updateDoc,
    deleteDoc,
    newId,
  };
}
