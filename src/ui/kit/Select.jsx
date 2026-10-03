import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';

/** <Select options=[{value,label,disabled}] value onChange(value) placeholder="..." /> */
export function Select({ id, options = [], value, onChange, placeholder, className, invalid, 'aria-invalid': ariaInvalid, ...rest }) {
  const auto = useId();
  const v = value == null ? '' : String(value);
  return (
    <select
      {...rest}
      id={id || `s-${auto}`}
      className={cx('select', className)}
      value={v}
      onChange={(e) => onChange && onChange(e.currentTarget.value, e)}
      aria-invalid={invalid ? 'true' : ariaInvalid}
    >
      {placeholder != null ? <option value="" disabled={rest.required}>{placeholder === true ? S.common.selectPlaceholder : placeholder}</option> : null}
      {options.map((o) => (
        <option key={o.value} value={String(o.value)} disabled={o.disabled}>{o.label}</option>
      ))}
    </select>
  );
}
