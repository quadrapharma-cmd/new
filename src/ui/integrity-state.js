// Runs engine.checkIntegrity (if the engine has it) on load and on demand; shared by the app shell and the system screen.
import { useEffect, useState } from 'preact/hooks';
import { engineFn, normalizeIntegrity } from './engine.js';

let snapshot = { status: 'idle', at: null, result: null, message: '', ms: 0 };
const listeners = new Set();
const set = (patch) => {
  snapshot = { ...snapshot, ...patch };
  listeners.forEach((fn) => fn(snapshot));
};

export function runIntegrity(state) {
  const fn = engineFn('checkIntegrity');
  if (!fn) {
    set({ status: 'missing', at: Date.now(), result: null, message: '' });
    return snapshot;
  }
  set({ status: 'running' });
  const t0 = Date.now();
  try {
    const raw = fn(state);
    if (raw && typeof raw.then === 'function') {
      raw.then(
        (r) => set({ status: 'done', at: Date.now(), result: normalizeIntegrity(r), ms: Date.now() - t0 }),
        (e) => set({ status: 'error', at: Date.now(), message: String(e?.message || e) }),
      );
    } else {
      set({ status: 'done', at: Date.now(), result: normalizeIntegrity(raw), ms: Date.now() - t0 });
    }
  } catch (e) {
    set({ status: 'error', at: Date.now(), message: String(e?.message || e) });
  }
  return snapshot;
}

export function useIntegrity() {
  const [s, setS] = useState(snapshot);
  useEffect(() => {
    listeners.add(setS);
    setS(snapshot);
    return () => listeners.delete(setS);
  }, []);
  return s;
}
