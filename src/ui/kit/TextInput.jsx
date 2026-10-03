import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';

/** Controlled text input. onChange receives the string value (not the event). */
export function TextInput({ id, value = '', onChange, className, mono = false, invalid, type = 'text', 'aria-invalid': ariaInvalid, ...rest }) {
  const auto = useId();
  return (
    <input
      {...rest}
      id={id || `t-${auto}`}
      type={type}
      className={cx('input', mono && 'input--code', className)}
      value={value ?? ''}
      onInput={(e) => onChange && onChange(e.currentTarget.value, e)}
      aria-invalid={invalid ? 'true' : ariaInvalid}
    />
  );
}

export function Textarea({ id, value = '', onChange, className, invalid, rows = 3, 'aria-invalid': ariaInvalid, ...rest }) {
  const auto = useId();
  return (
    <textarea
      {...rest}
      id={id || `ta-${auto}`}
      className={cx('textarea', className)}
      rows={rows}
      value={value ?? ''}
      onInput={(e) => onChange && onChange(e.currentTarget.value, e)}
      aria-invalid={invalid ? 'true' : ariaInvalid}
    />
  );
}
