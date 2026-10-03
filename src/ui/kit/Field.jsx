import { useId } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';
import { Icon } from './icons.jsx';

/**
 * Label + hint + error around one control, with stable ids.
 * children may be a function receiving { id, 'aria-describedby', 'aria-invalid', required } to spread on the control.
 * Pass an explicit `id` (recommended) so the id stays the same across page versions.
 */
export function Field({ label, hint, error, required, id, className, children }) {
  const auto = useId();
  const fid = id || `f-${auto}`;
  const hintId = hint ? `${fid}-hint` : null;
  const errId = error ? `${fid}-err` : null;
  const describedBy = [hintId, errId].filter(Boolean).join(' ') || undefined;
  const props = { id: fid, 'aria-describedby': describedBy, 'aria-invalid': error ? 'true' : undefined, required: required || undefined };
  return (
    <div className={cx('field', className)}>
      {label ? (
        <label className="field__label" htmlFor={fid}>
          {label}
          {required ? <span className="field__req" aria-hidden="true">*</span> : null}
          {required ? <span className="sr-only">({S.common.required})</span> : null}
        </label>
      ) : null}
      {typeof children === 'function' ? children(props) : children}
      {hint ? <div className="field__hint" id={hintId}>{hint}</div> : null}
      {error ? (
        <div className="field__error" id={errId} role="alert">
          <Icon name="critical" />
          <span>{error}</span>
        </div>
      ) : null}
    </div>
  );
}
