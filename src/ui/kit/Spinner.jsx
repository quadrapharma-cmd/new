import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';

export function Spinner({ small = false, label = S.kit.spinner }) {
  return <span className={cx('spinner', small && 'spinner--sm')} role="status" aria-label={label} />;
}

export function Loading({ text = S.common.loading }) {
  return (
    <div className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}
