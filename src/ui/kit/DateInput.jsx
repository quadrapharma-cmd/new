import { useEffect, useRef, useState } from 'preact/hooks';
import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';
import { localizeDigits } from '../../lib/digits.js';
import { parseDate, formatDate } from '../../lib/dates.js';

const show = (iso) => (iso ? localizeDigits(formatDate(iso)) : '');

/**
 * dd/mm/yyyy input. value: ISO 'YYYY-MM-DD' | null. onChange(iso | null, { valid, raw }).
 * "5/3" completes the year from `defaultYear`. Arabic digits are accepted.
 */
export function DateInput({ id, value = null, onChange, defaultYear, className, invalid, onBlur, 'aria-invalid': ariaInvalid, ...rest }) {
  const auto = useId();
  const [text, setText] = useState(() => show(value));
  const [bad, setBad] = useState(false);
  const last = useRef(value);

  useEffect(() => {
    if (value !== last.current) {
      last.current = value;
      setText(show(value));
      setBad(false);
    }
  }, [value]);

  function commit(raw, final) {
    const t = raw.trim();
    if (!t) {
      setBad(false);
      last.current = null;
      onChange && onChange(null, { valid: true, raw });
      return;
    }
    const iso = parseDate(t, defaultYear ? { defaultYear } : undefined);
    if (!iso) {
      if (final) setBad(true);
      last.current = null; // the parent will hold null: do not mistake that echo for an external change
      onChange && onChange(null, { valid: false, raw });
      return;
    }
    setBad(false);
    last.current = iso;
    onChange && onChange(iso, { valid: true, raw });
    if (final) setText(show(iso));
  }

  return (
    <input
      {...rest}
      id={id || `d-${auto}`}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      dir="ltr"
      className={cx('input', 'input--date', className)}
      value={text}
      placeholder={S.kit.date.placeholder}
      aria-invalid={invalid || bad ? 'true' : ariaInvalid}
      title={bad ? S.kit.date.invalid : undefined}
      onInput={(e) => {
        setText(e.currentTarget.value);
        commit(e.currentTarget.value, false);
      }}
      onBlur={(e) => {
        commit(e.currentTarget.value, true);
        onBlur && onBlur(e);
      }}
    />
  );
}
