import { cx } from '../../lib/format.js';
import { Icon } from './icons.jsx';

const ICON = { info: 'info', warn: 'warn', critical: 'critical', good: 'good' };

/** <Banner kind="info|warn|critical|good" title="..." actions={<Button/>}>text</Banner> */
export function Banner({ kind = 'info', title, actions, className, children, role }) {
  return (
    <div className={cx('banner', kind !== 'info' && `banner--${kind}`, className)} role={role || (kind === 'critical' || kind === 'warn' ? 'alert' : 'status')}>
      <Icon name={ICON[kind] || 'info'} />
      <div className="banner__body">
        {title ? <div className="banner__title">{title}</div> : null}
        {children ? <div className="banner__text">{children}</div> : null}
      </div>
      {actions ? <div className="banner__actions">{actions}</div> : null}
    </div>
  );
}
