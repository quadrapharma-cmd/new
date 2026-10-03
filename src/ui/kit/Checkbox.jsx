import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';

export function Checkbox({ id, checked = false, onChange, label, className, disabled, ...rest }) {
  const auto = useId();
  const cid = id || `c-${auto}`;
  return (
    <label className={cx('check', className)} htmlFor={cid}>
      <input {...rest} id={cid} type="checkbox" checked={!!checked} disabled={disabled} onChange={(e) => onChange && onChange(e.currentTarget.checked, e)} />
      <span>{label}</span>
    </label>
  );
}
