import { useContext, useEffect, useState } from 'preact/hooks';
import { AppContext } from './context.js';

export const useApp = () => useContext(AppContext);

/** Re-renders on every store change and returns the current engine state. */
export function useStoreState() {
  const { store } = useApp();
  const [state, setState] = useState(store.getState());
  useEffect(() => {
    setState(store.getState());
    return store.subscribe((s) => setState(s));
  }, [store]);
  return state;
}

/** Store status: { phase, counts, total, loaded, errors, subscriptions, ... } */
export function useStoreStatus() {
  const { store } = useApp();
  const [status, setStatus] = useState(store.getStatus());
  useEffect(() => {
    setStatus(store.getStatus());
    return store.onStatus((s) => setStatus(s));
  }, [store]);
  return status;
}

const readHash = () => (typeof location === 'undefined' ? '' : location.hash.replace(/^#/, ''));

/** Current hash token (plain token such as 'entries' or 'reports-tb'); '' means the default screen. */
export function useHashToken() {
  const [token, setToken] = useState(readHash());
  useEffect(() => {
    const on = () => setToken(readHash());
    window.addEventListener('hashchange', on);
    return () => window.removeEventListener('hashchange', on);
  }, []);
  return token;
}

export function navigate(token) {
  const t = String(token || '').replace(/^#/, '');
  if (readHash() === t) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = t;
}

/** Calls `fn` on Escape while `active`. */
export function useEscape(fn, active = true) {
  useEffect(() => {
    if (!active) return undefined;
    const on = (e) => e.key === 'Escape' && fn(e);
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  }, [fn, active]);
}
