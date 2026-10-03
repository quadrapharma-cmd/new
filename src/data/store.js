// Live in-memory state: ONE onSnapshot subscription per collection (17 of the 64 allowed),
// kept in the engine-state shape. Delivered docs are frozen platform objects: never mutate them, clone first.
import { COLLECTIONS, emptyState, defaultCounters, mergeConfig, SUBSCRIPTION_CAP } from './schema.js';

export const PHASES = ['idle', 'loading', 'ready', 'error', 'revoked', 'unavailable'];

/**
 * createStore(runtime, { batchMs, readyGraceMs, retryBaseMs })
 *  - getState(): the current engine state (identity changes only when something changed; untouched collections keep identity)
 *  - getStatus(): { phase, loaded, errors, counts, total, subscriptions, ... }
 *  - subscribe(fn(state, info)) / onStatus(fn(status)): returns an unsubscribe function
 *  - start() / stop(), whenReady(), flush()
 */
export function createStore(runtime, { batchMs = 16, readyGraceMs = 8000, retryBaseMs = 1500, maxRetries = 3 } = {}) {
  let state = emptyState();
  let status = freshStatus(runtime.db ? 'idle' : 'unavailable');
  const rawMaps = {}; // collection -> { id: frozen data }
  const unsubs = new Map();
  const retries = {};
  const listeners = new Set();
  const statusListeners = new Set();
  let pendingChanged = new Set();
  let timer = null;
  let graceTimer = null;
  let seq = 0;
  let started = false;
  const readyWaiters = [];

  function freshStatus(phase) {
    return {
      phase,
      loaded: {}, // definitive (non-cache) first snapshot received
      seen: {}, // any snapshot received
      errors: {},
      counts: {},
      total: 0,
      subscriptions: 0,
      startedAt: null,
      readyAt: null,
      slow: false,
    };
  }

  function setStatus(patch) {
    status = { ...status, ...patch };
    for (const fn of statusListeners) fn(status);
    if (['ready', 'error', 'revoked', 'unavailable'].includes(status.phase)) {
      while (readyWaiters.length) readyWaiters.shift()(status);
    }
  }

  function recomputePhase() {
    const names = COLLECTIONS.map((c) => c.name);
    const errs = Object.keys(status.errors);
    if (status.phase === 'revoked') return;
    if (names.every((n) => status.loaded[n]) && !errs.length) {
      if (status.phase !== 'ready') setStatus({ phase: 'ready', readyAt: Date.now(), slow: false });
    } else if (errs.length) {
      if (status.phase !== 'error') setStatus({ phase: 'error' });
    } else if (status.phase === 'idle') setStatus({ phase: 'loading' });
  }

  function emit() {
    timer = null;
    const changed = [...pendingChanged];
    pendingChanged = new Set();
    if (!changed.length) return;
    seq += 1;
    for (const fn of listeners) fn(state, { changed, seq });
  }
  function scheduleEmit(names) {
    for (const n of names) pendingChanged.add(n);
    if (batchMs <= 0) return emit();
    if (!timer) timer = setTimeout(emit, batchMs);
  }

  function applyCollection(name, map) {
    const def = COLLECTIONS.find((c) => c.name === name);
    if (name === 'meta') {
      state = {
        ...state,
        config: mergeConfig(map.config),
        counters: { ...defaultCounters(), ...(map.counters || {}) },
        groups: Array.isArray(map.groups?.groups) ? map.groups.groups : [],
      };
    } else {
      state = { ...state, [def.key]: map };
    }
  }

  function onSnap(name, snap) {
    retries[name] = 0;
    const prev = rawMaps[name] || {};
    const map = {};
    let n = 0;
    let changed = !rawMaps[name];
    for (const d of snap.docs) {
      const data = d.data();
      map[d.id] = data;
      n += 1;
      if (prev[d.id] !== data) changed = true;
    }
    if (!changed && n !== Object.keys(prev).length) changed = true;
    if (changed) {
      rawMaps[name] = map;
      applyCollection(name, map);
    }
    const definitive = !snap.metadata || snap.metadata.fromCache === false;
    const counts = { ...status.counts, [name]: n };
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    const errors = { ...status.errors };
    delete errors[name];
    setStatus({
      seen: { ...status.seen, [name]: true },
      loaded: definitive ? { ...status.loaded, [name]: true } : status.loaded,
      counts,
      total,
      errors,
    });
    recomputePhase();
    if (changed) scheduleEmit([name]);
  }

  function onErr(name, e) {
    unsubs.delete(name);
    const code = e?.code || 'unavailable';
    setStatus({
      errors: { ...status.errors, [name]: { code, message: e?.message || '' } },
      subscriptions: unsubs.size,
      phase: code === 'revoked' ? 'revoked' : status.phase === 'revoked' ? 'revoked' : 'error',
    });
    // transient failures: resubscribe with backoff; budget/argument/revoked errors are final
    if (!['revoked', 'invalid_argument', 'resource_exhausted', 'not_granted', 'capability_disabled', 'capability_removed'].includes(code)) {
      const k = (retries[name] = (retries[name] || 0) + 1);
      if (k <= maxRetries && started) setTimeout(() => started && subscribeTo(name), retryBaseMs * 2 ** (k - 1));
    }
  }

  function subscribeTo(name) {
    if (unsubs.has(name) || !runtime.db) return;
    try {
      const un = runtime.db.collection(name).onSnapshot(
        (snap) => onSnap(name, snap),
        (e) => onErr(name, e),
      );
      unsubs.set(name, un);
      setStatus({ subscriptions: unsubs.size });
    } catch (e) {
      onErr(name, { code: 'invalid_argument', message: String(e?.message || e) });
    }
  }

  function start() {
    if (started) return;
    started = true;
    if (!runtime.db) {
      setStatus({ phase: 'unavailable' });
      return;
    }
    status = { ...freshStatus('loading'), startedAt: Date.now() };
    for (const fn of statusListeners) fn(status);
    if (COLLECTIONS.length > SUBSCRIPTION_CAP) throw new Error('too many subscriptions');
    for (const c of COLLECTIONS) subscribeTo(c.name);
    graceTimer = setTimeout(() => {
      // Some runtimes only deliver cache-flagged snapshots for a while: accept them once all collections answered.
      const names = COLLECTIONS.map((c) => c.name);
      if (status.phase === 'loading') {
        if (names.every((n) => status.seen[n])) setStatus({ phase: 'ready', readyAt: Date.now() });
        else setStatus({ slow: true });
      }
    }, readyGraceMs);
    graceTimer?.unref?.(); // Node tests: never keep the process alive for this
  }

  function stop() {
    started = false;
    clearTimeout(graceTimer);
    clearTimeout(timer);
    timer = null;
    for (const un of unsubs.values()) {
      try {
        un();
      } catch {
        /* already gone */
      }
    }
    unsubs.clear();
    setStatus({ subscriptions: 0 });
  }

  return {
    getState: () => state,
    getStatus: () => status,
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    onStatus(fn) {
      statusListeners.add(fn);
      return () => statusListeners.delete(fn);
    },
    start,
    stop,
    /** Resolves with the status once the store is ready (or failed / unavailable). */
    whenReady(timeoutMs = 15000) {
      if (['ready', 'error', 'revoked', 'unavailable'].includes(status.phase)) return Promise.resolve(status);
      return new Promise((resolve) => {
        const t = setTimeout(() => resolve(status), timeoutMs);
        readyWaiters.push((s) => {
          clearTimeout(t);
          resolve(s);
        });
      });
    },
    /** Deliver any batched change event immediately (tests, or code that must see fresh state). */
    flush() {
      clearTimeout(timer);
      emit();
    },
  };
}
