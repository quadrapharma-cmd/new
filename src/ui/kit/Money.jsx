import { cx } from '../../lib/format.js';
import { getDigitsMode } from '../../lib/digits.js';
import { formatMoney } from '../../lib/money.js';

/**
 * Amount in pounds (number with <= 2 decimals), isolated left-to-right inside RTL text.
 * Defaults to the report format: 1,234.50 / (1,234.50) / "-" for zero. Pass cents to give integer piastres instead.
 */
export function Money({ value, cents, parens = true, zero = '-', digits, colorize = false, className }) {
  const n = cents != null ? cents / 100 : Number(value) || 0;
  const text = formatMoney(n, { parens, zero, digits: digits || getDigitsMode() });
  return (
    <span className={cx('money', colorize && n < 0 && 'money--neg', colorize && n === 0 && 'money--zero', className)} dir="ltr">
      {text}
    </span>
  );
}
