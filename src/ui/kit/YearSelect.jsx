import { useMemo } from 'preact/hooks';
import { S } from '../../lib/i18n.js';
import { localizeDigits } from '../../lib/digits.js';
import { Select } from './Select.jsx';

/** Years available in the system: fiscalYears docs, years of existing entries, plus the current one. */
export function availableYears(state, current = new Date().getFullYear()) {
  const ys = new Set([current]);
  for (const k of Object.keys(state?.fiscalYears || {})) if (/^\d{4}$/.test(k)) ys.add(Number(k));
  for (const e of Object.values(state?.entries || {})) if (e && Number.isInteger(e.fy)) ys.add(e.fy);
  return [...ys].sort((a, b) => b - a);
}

/** <YearSelect value={2025} years={[2025,2024]} onChange(year:number) /> */
export function YearSelect({ id = 'year-select', value, years, onChange, className, ...rest }) {
  const options = useMemo(() => years.map((y) => ({ value: y, label: localizeDigits(String(y)) })), [years]);
  return <Select id={id} className={className} options={options} value={value} onChange={(v) => onChange(Number(v))} aria-label={S.app.year} {...rest} />;
}
