import { cx } from '../../lib/format.js';

/** Status pill. kind: neutral | accent | good | warn | critical. Always carries text (never colour alone). */
export function Pill({ kind = 'neutral', dot = false, className, children, title }) {
  return (
    <span className={cx('pill', kind !== 'neutral' && `pill--${kind}`, className)} title={title}>
      {dot ? <span className="pill__dot" aria-hidden="true" /> : null}
      {children}
    </span>
  );
}
export const Badge = Pill;
