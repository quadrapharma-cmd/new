// Pure ranking helpers for the pickers (no JSX so they are unit-tested with node --test).
import { normalizeText, matchesTokens } from '../../lib/format.js';
import { toWesternDigits } from '../../lib/digits.js';

const arr = (v) => (Array.isArray(v) ? v : Object.values(v || {}));
/** Text without the Arabic definite article on the first word: 'البنك الأهلي' also answers to 'بنك'. */
const noAl = (t) => (t.startsWith('ال') && t.length > 3 ? t.slice(2) : t);
const wordStarts = (name, q) => name.split(' ').some((w) => w.startsWith(q) || noAl(w).startsWith(q));

/**
 * Accounts ranked for a typed query:
 *   0 exact code, 1 code prefix, 2 name starts with, 3 a word starts with, 4 name contains, 5 all tokens, 6 notes.
 * Order: exact code, then recently used matches (most recent first), then the rest by match quality; recents lead an empty query. Inactive accounts are hidden unless
 * includeInactive or listed in keepCodes (e.g. the current value); non-postable group rows are always hidden.
 */
export function rankAccounts(accounts, query, { recent = [], limit = 50, includeInactive = false, keepCodes = [] } = {}) {
  const q = normalizeText(query);
  const keep = new Set(keepCodes.map(String));
  const recentIdx = new Map(recent.map((c, i) => [String(c), i]));
  const pool = arr(accounts).filter((a) => a && a.postable !== false && (includeInactive || a.active !== false || keep.has(String(a.code))));
  const scored = [];
  for (const a of pool) {
    const code = String(a.code);
    const name = normalizeText(a.name);
    const r = recentIdx.has(code) ? recentIdx.get(code) : Infinity;
    let score;
    if (!q) score = Number.isFinite(r) ? 0 : 1;
    else if (code === q) score = 0;
    else if (/^\d+$/.test(q) && code.startsWith(q)) score = 1;
    else if (name.startsWith(q) || noAl(name).startsWith(q)) score = 2;
    else if (wordStarts(name, q)) score = 3;
    else if (name.includes(q)) score = 4;
    else if (matchesTokens(name, q)) score = 5;
    else if (a.notes && matchesTokens(normalizeText(a.notes), q)) score = 6;
    else continue;
    scored.push({ a, score, r });
  }
  // exact code first, then recently used matches (most recent first), then the rest by match quality
  const tier = (x) => (q && x.score === 0 ? 0 : Number.isFinite(x.r) ? 1 : 2);
  scored.sort((x, y) => tier(x) - tier(y) || (tier(x) === 1 ? x.r - y.r : x.score - y.score) || String(x.a.code).localeCompare(String(y.a.code)));
  return scored.slice(0, limit).map((s) => s.a);
}

/** True when the query is exactly an account code that exists in the (postable, active) pool. */
export function exactAccount(accounts, query, opts = {}) {
  const code = toWesternDigits(String(query ?? '')).trim();
  if (!code) return null;
  return rankAccounts(accounts, code, { ...opts, limit: 1 }).find((a) => String(a.code) === code) || null;
}

/**
 * Parties ranked for a typed query over names AND aliases.
 * 0 exact name, 1 name starts with or exact alias, 2 alias starts with, 3 contains, 4 all tokens.
 * Merged-away and inactive parties are hidden. Result items: { party, via: null | alias text }.
 */
export function rankParties(parties, query, { recent = [], limit = 50, keepIds = [] } = {}) {
  const q = normalizeText(query);
  const keep = new Set(keepIds);
  const recentIdx = new Map(recent.map((c, i) => [c, i]));
  const scored = [];
  for (const p of arr(parties)) {
    if (!p || p.mergedInto || (p.active === false && !keep.has(p.id))) continue;
    const r = recentIdx.has(p.id) ? recentIdx.get(p.id) : Infinity;
    const name = normalizeText(p.name);
    if (!q) {
      scored.push({ party: p, via: null, score: Number.isFinite(r) ? 0 : 1, r });
      continue;
    }
    let best = null;
    const consider = (text, via) => {
      let s;
      if (text === q) s = via ? 1 : 0;
      else if (text.startsWith(q) || noAl(text).startsWith(q)) s = via ? 2 : 1;
      else if (text.includes(q)) s = 3;
      else if (matchesTokens(text, q)) s = 4;
      else return;
      if (!best || s < best.score) best = { party: p, via, score: s, r };
    };
    consider(name, null);
    for (const al of p.aliases || []) consider(normalizeText(al), al);
    if (best) scored.push(best);
  }
  scored.sort((x, y) => x.score - y.score || x.r - y.r || String(x.party.name).localeCompare(String(y.party.name), 'ar'));
  return scored.slice(0, limit).map(({ party, via }) => ({ party, via }));
}

/** Documents ranked over ref, type and note. */
export function rankDocuments(documents, query, { recent = [], limit = 50, excludeIds = [] } = {}) {
  const q = normalizeText(query);
  const ex = new Set(excludeIds);
  const recentIdx = new Map(recent.map((c, i) => [c, i]));
  const scored = [];
  for (const d of arr(documents)) {
    if (!d || ex.has(d.id)) continue;
    const r = recentIdx.has(d.id) ? recentIdx.get(d.id) : Infinity;
    const hay = normalizeText(`${d.id} ${d.ref || ''} ${d.type || ''} ${d.note || ''}`);
    let score;
    if (!q) score = Number.isFinite(r) ? 0 : 1;
    else if (normalizeText(d.id) === q) score = 0;
    else if (normalizeText(d.ref).startsWith(q)) score = 1;
    else if (matchesTokens(hay, q)) score = 2;
    else continue;
    scored.push({ d, score, r });
  }
  scored.sort((x, y) => x.score - y.score || x.r - y.r || String(x.d.id).localeCompare(String(y.d.id)));
  return scored.slice(0, limit).map((s) => s.d);
}
