// Formatting and text helpers that do not depend on money.js / dates.js.
import { getDigitsMode, localizeDigits, toWesternDigits } from './digits.js';

/** classnames: cx('a', cond && 'b', { c: true }, ['d']) */
export function cx(...args) {
  const out = [];
  const add = (a) => {
    if (!a) return;
    if (typeof a === 'string') out.push(a);
    else if (Array.isArray(a)) a.forEach(add);
    else if (typeof a === 'object') for (const k of Object.keys(a)) if (a[k]) out.push(k);
  };
  args.forEach(add);
  return out.join(' ');
}

export function formatInt(n, mode = getDigitsMode()) {
  const v = Number.isFinite(Number(n)) ? Math.round(Number(n)) : 0;
  return localizeDigits(v.toLocaleString('en-US'), mode);
}

export function formatBytes(n, mode = getDigitsMode()) {
  const v = Number(n) || 0;
  let s;
  if (v < 1024) s = `${v} B`;
  else if (v < 1024 * 1024) s = `${(v / 1024).toFixed(1)} KiB`;
  else s = `${(v / 1048576).toFixed(2)} MiB`;
  return mode === 'arabic' ? localizeDigits(s, mode) : s;
}

/** Approximate serialized size of a JSON value in bytes (UTF-8). */
export function jsonBytes(v) {
  const s = JSON.stringify(v) ?? '';
  if (typeof TextEncoder !== 'undefined') return new TextEncoder().encode(s).length;
  return s.length * 2;
}

const p2 = (n) => String(n).padStart(2, '0');
/** ISO timestamp (UTC string) -> 'dd/mm/yyyy hh:mm' in the viewer's local time. Audit stamps only, never accounting dates. */
export function formatTimestamp(iso, { time = true } = {}) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const date = `${p2(d.getDate())}/${p2(d.getMonth() + 1)}/${d.getFullYear()}`;
  return localizeDigits(time ? `${date} ${p2(d.getHours())}:${p2(d.getMinutes())}` : date);
}

/** Coarse relative time in Arabic ("قبل ٣ أيام"). */
export function timeAgo(iso, now = Date.now()) {
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '';
  const s = Math.max(0, Math.round((now - t) / 1000));
  const unit = (n, one, two, few, many) => {
    const w = n === 1 ? one : n === 2 ? two : n >= 3 && n <= 10 ? few : many;
    return n === 1 || n === 2 ? w : `${localizeDigits(String(n))} ${w}`;
  };
  if (s < 60) return 'الآن';
  if (s < 3600) return `قبل ${unit(Math.floor(s / 60), 'دقيقة', 'دقيقتين', 'دقائق', 'دقيقة')}`;
  if (s < 86400) return `قبل ${unit(Math.floor(s / 3600), 'ساعة', 'ساعتين', 'ساعات', 'ساعة')}`;
  return `قبل ${unit(Math.floor(s / 86400), 'يوم', 'يومين', 'أيام', 'يوماً')}`;
}

/**
 * Search normalisation for Arabic text: Western digits, no diacritics/tatweel,
 * أ إ آ ٱ -> ا, ى -> ي, ة -> ه, lower-case Latin, collapsed spaces.
 */
export function normalizeText(s) {
  return toWesternDigits(String(s ?? ''))
    .normalize('NFKC')
    .replace(/[ً-ٰٟـ]/g, '')
    .replace(/[أإآٱ]/g, 'ا')
    .replace(/ى/g, 'ي')
    .replace(/ة/g, 'ه')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

/** True when every whitespace-separated token of the (already normalised) query occurs in the (already normalised) text. */
export function matchesTokens(normText, normQuery) {
  if (!normQuery) return true;
  for (const tok of normQuery.split(' ')) if (tok && !normText.includes(tok)) return false;
  return true;
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
/** base ± spread/2 ms of random jitter. */
export const jitter = (base, spread = base) => Math.max(0, Math.round(base + (Math.random() - 0.5) * spread));

export function debounce(fn, ms) {
  let t;
  const d = (...a) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...a), ms);
  };
  d.cancel = () => clearTimeout(t);
  return d;
}
