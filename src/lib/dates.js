// Accounting dates are plain 'YYYY-MM-DD' strings: no Date objects, no timezone arithmetic.
// Day arithmetic uses the proleptic Gregorian "days from civil" algorithm.

const ARABIC_INDIC = '٠١٢٣٤٥٦٧٨٩';
const EXTENDED = '۰۱۲۳۴۵۶۷۸۹';
const p2 = (n) => String(n).padStart(2, '0');
const p4 = (n) => String(n).padStart(4, '0');

function westernDigits(s) {
  return String(s).replace(/[٠-٩۰-۹]/g, (c) => {
    const i = ARABIC_INDIC.indexOf(c);
    return String(i >= 0 ? i : EXTENDED.indexOf(c));
  });
}
const arabicDigits = (s) => String(s).replace(/\d/g, (d) => ARABIC_INDIC[Number(d)]);

export function isLeapYear(y) {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}
export const daysInYear = (y) => (isLeapYear(y) ? 366 : 365);
const MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
function daysInMonth(y, m) {
  return m === 2 && isLeapYear(y) ? 29 : MONTH_DAYS[m - 1];
}

function validYMD(y, m, d) {
  return Number.isInteger(y) && y >= 1000 && y <= 9999 && m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m);
}
const toISO = (y, m, d) => `${p4(y)}-${p2(m)}-${p2(d)}`;

/** True for a real calendar date written as YYYY-MM-DD. */
export function isValidISO(s) {
  if (typeof s !== 'string') return false;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  return !!m && validYMD(Number(m[1]), Number(m[2]), Number(m[3]));
}

/** Days since 1970-01-01 for a civil date (Howard Hinnant's algorithm). */
function dayNumber(y, m, d) {
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor(y / 400);
  const yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
  return era * 146097 + doe - 719468;
}
function civil(z) {
  z += 719468;
  const era = Math.floor(z / 146097);
  const doe = z - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  const y = yoe + era * 400;
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153);
  const d = doy - Math.floor((153 * mp + 2) / 5) + 1;
  const m = mp + (mp < 10 ? 3 : -9);
  return [y + (m <= 2 ? 1 : 0), m, d];
}
function split(iso) {
  if (!isValidISO(iso)) throw new TypeError(`dates: invalid ISO date ${JSON.stringify(iso)}`);
  return [Number(iso.slice(0, 4)), Number(iso.slice(5, 7)), Number(iso.slice(8, 10))];
}

/**
 * Parse typed text into ISO 'YYYY-MM-DD' (null when invalid). Accepts dd/mm/yyyy, d/m/yy, yyyy-mm-dd,
 * yyyy/m/d, separators / - . and Arabic-Indic digits. 'd/m' with no year takes opts.defaultYear
 * (default: the current year). Two-digit years: 00-69 -> 2000s, 70-99 -> 1900s.
 */
export function parseDate(input, opts = {}) {
  if (input === null || input === undefined) return null;
  if (input instanceof Date) {
    if (Number.isNaN(input.getTime())) return null;
    return toISO(input.getFullYear(), input.getMonth() + 1, input.getDate());
  }
  if (typeof input !== 'string') return null;
  const s = westernDigits(input)
    .replace(/[‎‏‪-‮⁦-⁩؜]/g, '')
    .trim()
    .replace(/[\\\-.–−]/g, '/');
  let m = /^(\d{4})\/(\d{1,2})\/(\d{1,2})(?:[T ].*)?$/.exec(s);
  if (m) return validYMD(+m[1], +m[2], +m[3]) ? toISO(+m[1], +m[2], +m[3]) : null;
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  if (m) return validYMD(+m[3], +m[2], +m[1]) ? toISO(+m[3], +m[2], +m[1]) : null;
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{2})$/.exec(s);
  if (m) {
    const yy = +m[3];
    const y = yy < 70 ? 2000 + yy : 1900 + yy;
    return validYMD(y, +m[2], +m[1]) ? toISO(y, +m[2], +m[1]) : null;
  }
  m = /^(\d{1,2})\/(\d{1,2})$/.exec(s);
  if (m) {
    const dy = opts.defaultYear !== undefined && opts.defaultYear !== null ? Number(opts.defaultYear) : new Date().getFullYear();
    return validYMD(dy, +m[2], +m[1]) ? toISO(dy, +m[2], +m[1]) : null;
  }
  return null;
}

/** ISO -> 'dd/mm/yyyy' ('' for empty/invalid). opts.digits = 'arabic' for Arabic-Indic digits. */
export function formatDate(iso, opts = {}) {
  if (!isValidISO(iso)) return '';
  const out = `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
  return opts.digits === 'arabic' ? arabicDigits(out) : out;
}

/** Fiscal year = calendar year of the date (null when the date is invalid). */
export function fyOf(iso) {
  return isValidISO(iso) ? Number(iso.slice(0, 4)) : null;
}

/** Signed number of days from a to b (b - a). */
export function daysBetween(a, b) {
  const [ya, ma, da] = split(a);
  const [yb, mb, db] = split(b);
  return dayNumber(yb, mb, db) - dayNumber(ya, ma, da);
}

export function addDays(iso, n) {
  const [y, m, d] = split(iso);
  const [ny, nm, nd] = civil(dayNumber(y, m, d) + n);
  return toISO(ny, nm, nd);
}

/** -1 / 0 / 1; null or invalid sorts before any date. */
export function compareISO(a, b) {
  const va = isValidISO(a);
  const vb = isValidISO(b);
  if (!va && !vb) return 0;
  if (!va) return -1;
  if (!vb) return 1;
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Today's date in the viewer's local calendar (components of the supplied clock; default now). */
export function todayISO(now = new Date()) {
  return toISO(now.getFullYear(), now.getMonth() + 1, now.getDate());
}

export const yearStart = (y) => `${p4(Number(y))}-01-01`;
export const yearEnd = (y) => `${p4(Number(y))}-12-31`;

/** 'YYYY-MM' of a date (the key of audit/<yyyy-mm>). */
export function monthKey(iso) {
  return isValidISO(iso) ? iso.slice(0, 7) : null;
}

/** from/to inclusive; null bounds are open. */
export function isBetween(iso, from, to) {
  if (from && iso < from) return false;
  if (to && iso > to) return false;
  return true;
}
export const minISO = (a, b) => (compareISO(a, b) <= 0 ? a : b);
export const maxISO = (a, b) => (compareISO(a, b) >= 0 ? a : b);
