import { cx } from '../../lib/format.js';
import { Icon } from './icons.jsx';

/** <Button kind="primary|secondary|danger|ghost" size="md|sm" busy block icon="plus">نص</Button>  (onClick as usual) */
export function Button({ kind = 'secondary', size = 'md', busy = false, block = false, icon, type = 'button', disabled, className, children, ...rest }) {
  return (
    <button
      type={type}
      className={cx('btn', kind !== 'secondary' && `btn--${kind}`, size === 'sm' && 'btn--sm', block && 'btn--block', className)}
      disabled={disabled || busy}
      aria-busy={busy ? 'true' : undefined}
      {...rest}
    >
      {busy ? <span className="btn__spin" aria-hidden="true" /> : icon ? <Icon name={icon} /> : null}
      {children}
    </button>
  );
}

/** Icon-only button: `label` is mandatory (it becomes aria-label and title). */
export function IconButton({ icon, label, outline = false, type = 'button', className, ...rest }) {
  return (
    <button type={type} className={cx('icon-btn', outline && 'icon-btn--outline', className)} aria-label={label} title={label} {...rest}>
      <Icon name={icon} />
    </button>
  );
}
