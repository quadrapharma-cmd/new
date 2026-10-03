// Tiny in-memory navigation parameters shared between screens (hash routes carry only plain tokens, never state).
// Example: reports call openEntry('e000312') -> entries screen reads getNavParam('entryId') and opens the detail.
import { navigate } from './hooks.js';

const params = new Map();
const listeners = new Set();

export function setNavParam(key, value) {
  if (value === undefined || value === null) params.delete(key);
  else params.set(key, value);
  for (const fn of listeners) fn(key, value);
}
export const getNavParam = (key) => params.get(key);
export function takeNavParam(key) {
  const v = params.get(key);
  params.delete(key);
  return v;
}
export function onNavParam(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Open an entry in the entries screen (detail drawer). */
export function openEntry(entryId) {
  setNavParam('entryId', entryId);
  navigate('entries');
}
/** Open the account statement (ledger / bank-cash book) for an account, optionally with year and dates. */
export function openLedger({ acct, year, from, to } = {}) {
  setNavParam('ledger', { acct, year, from, to });
  navigate('reports-ledger');
}
/** Open the party statement. */
export function openPartyStatement({ partyId, acct } = {}) {
  setNavParam('partyStatement', { partyId, acct });
  navigate('reports-party');
}
