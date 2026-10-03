// Document id helpers (entries, drafts, parties, documents) plus small shared utilities.
export const pad = (n, width) => String(n).padStart(width, '0');

export function randomString(len = 4, alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789') {
  let out = '';
  const c = globalThis.crypto;
  if (c && c.getRandomValues) {
    const buf = new Uint32Array(len);
    c.getRandomValues(buf);
    for (let i = 0; i < len; i++) out += alphabet[buf[i] % alphabet.length];
  } else {
    for (let i = 0; i < len; i++) out += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return out;
}

/** Numbered entry doc id: 312 -> 'e000312'. */
export const entryDocId = (no) => `e${pad(no, 6)}`;
/** 'e000312' -> 312 (null when the id is not a numbered entry id). */
export function entryNoOf(id) {
  const m = /^e(\d{6,})$/.exec(String(id));
  return m ? Number(m[1]) : null;
}
export const isDraftId = (id) => /^d_[a-z0-9]+_[a-z0-9]+$/.test(String(id));
/** Draft id: d_<base36 time>_<rand>. */
export const newDraftId = (now = Date.now()) => `d_${now.toString(36)}_${randomString(4)}`;

export const partyDocId = (n) => `p${pad(n, 4)}`;
export const docDocId = (n) => `D${pad(n, 4)}`;

/** Numeric part of a sequential id with the given prefix (null when it does not match). */
export function seqOf(id, prefix) {
  const m = new RegExp(`^${prefix}(\\d+)$`).exec(String(id));
  return m ? Number(m[1]) : null;
}
/** Next sequential id after the highest existing one: nextSeqId(['p0001','p0007'], 'p', 4) -> 'p0008'. */
export function nextSeqId(existingIds, prefix, width) {
  let max = 0;
  for (const id of existingIds) {
    const n = seqOf(id, prefix);
    if (n != null && n > max) max = n;
  }
  return `${prefix}${pad(max + 1, width)}`;
}

/** Generic unique id: <prefix>_<time36>_<rand>. */
export const newId = (prefix = 'x') => `${prefix}_${Date.now().toString(36)}_${randomString(4)}`;

/** Per-tab identity used as the lease holder. */
let tab = null;
export function tabId() {
  if (!tab) tab = `t${Date.now().toString(36)}${randomString(5)}`;
  return tab;
}

export const isPlainObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Deep clone of JSON data (delivered snapshots are frozen: clone before editing). */
export function deepClone(v) {
  if (v === undefined) return v;
  return typeof structuredClone === 'function' ? structuredClone(v) : JSON.parse(JSON.stringify(v));
}
