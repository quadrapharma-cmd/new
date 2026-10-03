// Money helpers. All accounting arithmetic is done in integer piastres (cents); amounts that cross
// module boundaries are JSON numbers with at most 2 decimals. Rounding is ROUND_HALF_UP on the
// decimal representation (ties go away from zero) and never uses toFixed or binary-float maths.

const ARABIC_INDIC = '٠١٢٣٤٥٦٧٨٩';
const EXTENDED = '۰۱۲۳۴۵۶۷۸۹';

/** ٠-٩ and ۰-۹ -> 0-9 (private copy so this module has no dependencies). */
function westernDigits(s) {
  return String(s).replace(/[٠-٩۰-۹]/g, (c) => {
    const i = ARABIC_INDIC.indexOf(c);
    return String(i >= 0 ? i : EXTENDED.indexOf(c));
  });
}

/** Exact plain decimal string of a finite number (never exponent notation). */
function plain(n) {
  const s = String(n);
  if (!/e/i.test(s)) return s;
  const m = /^(-?)(\d+)(?:\.(\d+))?e([+-]\d+)$/i.exec(s);
  if (!m) throw new TypeError(`money: cannot expand ${s}`);
  const sign = m[1];
  const ip = m[2];
  const fp = m[3] || '';
  const e = Number(m[4]);
  const digits = ip + fp;
  const point = ip.length + e;
  if (point <= 0) return `${sign}0.${'0'.repeat(-point)}${digits}`;
  if (point >= digits.length) return `${sign}${digits}${'0'.repeat(point - digits.length)}`;
  return `${sign}${digits.slice(0, point)}.${digits.slice(point)}`;
}

function assertFinite(n, what = 'amount') {
  if (typeof n !== 'number' || !Number.isFinite(n)) throw new TypeError(`money: ${what} must be a finite number`);
}

/** Number of decimal places in the shortest decimal representation of n. */
export function decimalPlaces(n) {
  assertFinite(n);
  const s = plain(n);
  const i = s.indexOf('.');
  return i < 0 ? 0 : s.length - i - 1;
}

/** Scale n by 10^places and round half-up (away from zero) to a BigInt, using the decimal string. */
function scaled(n, places) {
  assertFinite(n);
  const s = plain(n);
  const neg = s[0] === '-';
  const body = neg ? s.slice(1) : s;
  const dot = body.indexOf('.');
  const ip = dot < 0 ? body : body.slice(0, dot);
  const fp = dot < 0 ? '' : body.slice(dot + 1);
  let v;
  if (fp.length <= places) {
    v = BigInt(ip + fp.padEnd(places, '0'));
  } else {
    v = BigInt(ip + fp.slice(0, places));
    if (fp.charCodeAt(places) - 48 >= 5) v += 1n; // half-up: first dropped digit >= 5
  }
  return neg ? -v : v;
}

/** Amount (pounds) -> integer piastres, ROUND_HALF_UP. null/undefined/'' -> 0. */
export function toCents(n) {
  if (n === null || n === undefined || n === '') return 0;
  if (typeof n === 'string') n = Number(n);
  return Number(scaled(n, 2));
}

/** Integer piastres -> amount in pounds with 2 decimals. */
export function fromCents(c) {
  if (!Number.isFinite(c)) throw new TypeError('money: cents must be a finite number');
  return c === 0 ? 0 : c / 100;
}

/** Round an amount to 2 decimals, ROUND_HALF_UP (ties away from zero). */
export function round2(n) {
  return fromCents(toCents(n));
}

/** True when n is a finite number with at most 2 decimals. */
export function isMoney(n) {
  return typeof n === 'number' && Number.isFinite(n) && Math.abs(n) < 1e13 && decimalPlaces(n) <= 2;
}

function assertInt(x, what) {
  if (!Number.isSafeInteger(x)) throw new TypeError(`money: ${what} must be a safe integer`);
}

/** Round BigInt n/d half-up (ties away from zero). d must be non-zero. */
function divRound(n, d) {
  if (d === 0n) throw new RangeError('money: division by zero');
  if (d < 0n) {
    n = -n;
    d = -d;
  }
  const neg = n < 0n;
  const a = neg ? -n : n;
  const q = (2n * a + d) / (2n * d);
  return neg ? -q : q;
}

/** round_half_up(cents * num / den) with all-integer arithmetic (BigInt inside, no overflow). */
export function mulDivRound(cents, num, den) {
  assertInt(cents, 'cents');
  assertInt(num, 'num');
  assertInt(den, 'den');
  if (den === 0) throw new RangeError('money: division by zero');
  return Number(divRound(BigInt(cents) * BigInt(num), BigInt(den)));
}

/** Decimal number/string -> exact rational { n: BigInt, d: BigInt } (d is a power of ten). */
function rational(x) {
  if (typeof x === 'string') x = Number(x);
  assertFinite(x, 'rate');
  const s = plain(x);
  const neg = s[0] === '-';
  const body = neg ? s.slice(1) : s;
  const dot = body.indexOf('.');
  const ip = dot < 0 ? body : body.slice(0, dot);
  const fp = dot < 0 ? '' : body.slice(dot + 1);
  const n = BigInt(ip + fp);
  return { n: neg ? -n : n, d: 10n ** BigInt(fp.length) };
}

/**
 * round_half_up(cents * rate * num / den) where rate is a decimal (0.2 = 20%). Exact: the rate is
 * converted to a rational from its decimal string, e.g. applyRate(320000, 0.2, 355, 365) -> 62247.
 */
export function applyRate(cents, rate, num = 1, den = 1) {
  assertInt(cents, 'cents');
  assertInt(num, 'num');
  assertInt(den, 'den');
  if (den === 0) throw new RangeError('money: division by zero');
  const r = rational(rate);
  return Number(divRound(BigInt(cents) * r.n * BigInt(num), r.d * BigInt(den)));
}

/**
 * round_half_up(100 * (f1 * f2 * ...) / (d1 * d2 * ...)) in cents, exact on the decimal representation of every
 * factor: productCents([3200, 0.2, 355], [365]) -> 62247 (3,200 x 20% x 355/365 = 622.47).
 */
export function productCents(factors, divisors = []) {
  let n = 100n;
  let d = 1n;
  for (const f of factors) {
    const r = rational(f);
    n *= r.n;
    d *= r.d;
  }
  for (const f of divisors) {
    const r = rational(f);
    if (r.n === 0n) throw new RangeError('money: division by zero');
    n *= r.d;
    d *= r.n;
  }
  return Number(divRound(n, d));
}

/**
 * Split totalCents by weights using the largest-remainder method so the parts add up exactly.
 * Ties go to the lower index. Negative totals are allocated by magnitude and negated.
 */
export function allocateCents(totalCents, weights) {
  assertInt(totalCents, 'totalCents');
  if (!Array.isArray(weights) || !weights.length) throw new RangeError('money: weights required');
  const rats = weights.map(rational);
  const k = rats.reduce((m, r) => (r.d > m ? r.d : m), 1n);
  const w = rats.map((r) => (r.n * k) / r.d);
  if (w.some((x) => x < 0n)) throw new RangeError('money: negative weight');
  const W = w.reduce((a, b) => a + b, 0n);
  if (W === 0n) throw new RangeError('money: weights sum to zero');
  const neg = totalCents < 0;
  const T = BigInt(Math.abs(totalCents));
  const parts = w.map((x) => (T * x) / W);
  const rem = w.map((x, i) => ({ i, r: (T * x) % W }));
  let left = T - parts.reduce((a, b) => a + b, 0n);
  rem.sort((a, b) => (a.r === b.r ? a.i - b.i : a.r > b.r ? -1 : 1));
  for (let j = 0; left > 0n; j++, left--) parts[rem[j % rem.length].i] += 1n;
  return parts.map((p) => (neg ? -Number(p) : Number(p)));
}

/** Sum of integer cent values (throws on non-integers so pounds are never summed here by mistake). */
export function sumCents(arr) {
  let s = 0;
  for (const c of arr) {
    assertInt(c, 'cent value');
    s += c;
  }
  return s;
}

/** Sum of pound amounts computed in integer piastres; returns pounds (2dp). */
export function sumMoney(arr) {
  let s = 0;
  for (const x of arr) s += toCents(x);
  return fromCents(s);
}

function group3(intStr) {
  return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Display an amount: '1,234.50' / '(1,234.50)' for negatives / '-' for zero.
 * opts: { parens = true, zero = '-', digits = 'western' | 'arabic' }.
 */
export function formatMoney(n, opts = {}) {
  const { parens = true, zero = '-', digits = 'western' } = opts;
  if (n === null || n === undefined || n === '') return '';
  if (typeof n === 'number' && !Number.isFinite(n)) return '';
  const c = toCents(n);
  if (c === 0) return zero;
  const a = Math.abs(c);
  const ip = Math.floor(a / 100);
  const fp = a % 100;
  let s = `${group3(String(ip))}.${String(fp).padStart(2, '0')}`;
  if (digits === 'arabic') {
    s = s.replace(/\d/g, (d) => ARABIC_INDIC[Number(d)]).replace(/\./g, '٫').replace(/,/g, '٬');
  }
  if (c < 0) s = parens ? `(${s})` : `-${s}`;
  return s;
}

const STRIP = /[\s   ‎‏‪-‮⁦-⁩؜]/g;

/**
 * Parse typed or pasted text into a number (null when it is not a number). Accepts Arabic-Indic and
 * Persian digits, '٫' as the decimal mark, '٬' ',' '،' and spaces as thousands separators, a leading
 * minus (- or U+2212) or enclosing parentheses for negatives. A comma is always a thousands
 * separator. opts.round = true rounds to 2 decimals half-up; otherwise the number is returned as
 * typed (use isMoney to reject more than 2 decimals).
 */
export function parseAmount(input, opts = {}) {
  if (input === null || input === undefined) return null;
  let v;
  if (typeof input === 'number') {
    v = input;
    if (!Number.isFinite(v)) return null;
  } else {
    let s = westernDigits(String(input))
      .replace(STRIP, '')
      .replace(/[−‒–]/g, '-')
      .replace(/٫/g, '.')
      .replace(/[٬,،]/g, '');
    s = s.replace(/^(?:egp|le|l\.e\.|ج\.م\.?|جنيه|جم)/i, '').replace(/(?:egp|le|l\.e\.|ج\.م\.?|جنيه|جم)$/i, '');
    if (!s) return null;
    let neg = false;
    const par = /^\((.*)\)$/.exec(s);
    if (par) {
      neg = true;
      s = par[1];
    }
    if (s[0] === '-') {
      if (neg) return null;
      neg = true;
      s = s.slice(1);
    }
    if (!/^(\d+\.?\d*|\.\d+)$/.test(s)) return null;
    v = Number(s);
    if (!Number.isFinite(v)) return null;
    if (neg) v = -v;
  }
  if (opts.round) v = round2(v);
  return v === 0 ? 0 : v;
}
