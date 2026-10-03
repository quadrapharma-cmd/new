// DEV STUB ONLY. Used by the build when src/lib/dates.js (owner: F2) does not exist yet.
const AR = '٠١٢٣٤٥٦٧٨٩';
const p2 = (n) => String(n).padStart(2, '0');
export function parseDate(str) {
  let s = String(str ?? '').trim().replace(/[٠-٩]/g, (d) => AR.indexOf(d));
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  let y, mo, d;
  if (m) [y, mo, d] = [+m[1], +m[2], +m[3]];
  else if ((m = s.match(/^(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2}|\d{4}))?$/))) {
    d = +m[1]; mo = +m[2]; y = m[3] ? (m[3].length === 2 ? 2000 + +m[3] : +m[3]) : new Date().getFullYear();
  } else return null;
  const t = new Date(Date.UTC(y, mo - 1, d));
  if (t.getUTCFullYear() !== y || t.getUTCMonth() !== mo - 1 || t.getUTCDate() !== d) return null;
  return `${y}-${p2(mo)}-${p2(d)}`;
}
export const formatDate = (iso) => (iso ? `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}` : '');
export const fyOf = (iso) => Number(String(iso).slice(0, 4));
const ms = (iso) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10));
export const daysBetween = (a, b) => Math.round((ms(b) - ms(a)) / 86400000);
export const addDays = (iso, n) => new Date(ms(iso) + n * 86400000).toISOString().slice(0, 10);
export const compareISO = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
export const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}`; };
export const yearStart = (y) => `${y}-01-01`;
export const yearEnd = (y) => `${y}-12-31`;
