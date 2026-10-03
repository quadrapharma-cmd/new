// DEV STUB ONLY. Used by the build when src/lib/money.js (owner: F2) does not exist yet.
// Same export names as the shared contract; not exact (no half-up string logic). Never imported otherwise.
export const toCents = (n) => Math.round(Number(n) * 100);
export const fromCents = (c) => Math.round(c) / 100;
export const round2 = (n) => Math.round(Number(n) * 100) / 100;
export const mulDivRound = (c, num, den) => Math.round((c * num) / den);
export const sumCents = (arr) => arr.reduce((a, b) => a + b, 0);
export const isMoney = (n) => typeof n === 'number' && Number.isFinite(n) && Math.abs(n * 100 - Math.round(n * 100)) < 1e-6;
const AR = '٠١٢٣٤٥٦٧٨٩';
export function formatMoney(n, { parens = true, zero = '-', digits = 'western' } = {}) {
  const v = round2(n || 0);
  if (v === 0) return zero;
  const body = Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const s = v < 0 ? (parens ? `(${body})` : `-${body}`) : body;
  return digits === 'arabic' ? s.replace(/\d/g, (d) => AR[d]).replace('.', '٫').replace(/,/g, '٬') : s;
}
export function parseAmount(str) {
  if (typeof str === 'number') return Number.isFinite(str) ? str : null;
  let s = String(str ?? '').trim();
  if (!s) return null;
  s = s.replace(/[٠-٩]/g, (d) => AR.indexOf(d)).replace(/٫/g, '.').replace(/[٬,\s]/g, '');
  if (!/^-?\d*\.?\d+$/.test(s)) return null;
  return round2(Number(s));
}
