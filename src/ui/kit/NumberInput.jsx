import { useEffect, useRef, useState } from 'preact/hooks';
import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';
import { getDigitsMode, localizeDigits } from '../../lib/digits.js';
import { parseAmount, formatMoney, isMoney } from '../../lib/money.js';

const show = (n, decimals) => {
  if (n == null) return '';
  if (decimals === 0) return localizeDigits(String(Math.round(n)));
  return formatMoney(n, { parens: false, zero: '0.00', digits: getDigitsMode() });
};

/**
 * Amount input. Accepts Western / Arabic-Indic digits and ٫ ٬ separators (via parseAmount), never negative unless allowNegative.
 * value: number | null.  onChange(number | null, { valid, raw }).  Normalises the text to 1,234.50 on blur.
 */
export function NumberInput({ id, value = null, onChange, allowNegative = false, decimals = 2, className, invalid, placeholder, onBlur, 'aria-invalid': ariaInvalid, ...rest }) {
  const auto = useId();
  const [text, setText] = useState(() => show(value, decimals));
  const [bad, setBad] = useState(null);
  const lastEmitted = useRef(value);

  // follow external value changes (e.g. "=" balancing, template defaults) but not our own echoes
  useEffect(() => {
    if (value !== lastEmitted.current) {
      lastEmitted.current = value;
      setText(show(value, decimals));
      setBad(null);
    }
  }, [value, decimals]);

  function invalidate(message, raw) {
    setBad(message);
    lastEmitted.current = null; // the parent will hold null: do not mistake that echo for an external change
    onChange && onChange(null, { valid: false, raw });
  }
  function commit(raw, final) {
    const trimmed = String(raw).trim();
    if (!trimmed) {
      setBad(null);
      lastEmitted.current = null;
      onChange && onChange(null, { valid: true, raw });
      return;
    }
    const n = parseAmount(trimmed);
    if (n == null) return invalidate(S.kit.number.invalid, raw);
    if (decimals === 2 && !isMoney(n)) return invalidate(S.kit.number.decimals, raw);
    if (n < 0 && !allowNegative) return invalidate(S.kit.number.negative, raw);
    setBad(null);
    lastEmitted.current = n;
    onChange && onChange(n, { valid: true, raw });
    if (final) setText(show(n, decimals));
  }

  return (
    <input
      {...rest}
      id={id || `n-${auto}`}
      type="text"
      inputMode="decimal"
      autoComplete="off"
      dir="ltr"
      className={cx('input', 'input--num', className)}
      value={text}
      placeholder={placeholder ?? (decimals === 0 ? '0' : '0.00')}
      aria-invalid={invalid || bad ? 'true' : ariaInvalid}
      title={bad || undefined}
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
