import { cx } from '../../lib/format.js';
import { Icon } from './icons.jsx';

/** One sentence plus one action. icon: any name from icons.jsx. */
export function EmptyState({ icon = 'file', title, text, action, className, children }) {
  return (
    <div className={cx('empty', className)}>
      <Icon name={icon} className="icon empty__icon" />
      {title ? <h2 className="empty__title">{title}</h2> : null}
      {text ? <p className="empty__text">{text}</p> : null}
      {children}
      {action || null}
    </div>
  );
}
