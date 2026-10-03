import { useEffect, useId, useRef } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';
import { IconButton } from './Button.jsx';

const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/**
 * Accessible dialog: focus moves in, Tab is trapped, Esc and the scrim close it (unless dismissable=false),
 * focus returns to the opener, and the page behind does not scroll.
 * <Modal open title="..." onClose footer={<Button/>} size="md|wide">content</Modal>
 */
export function Modal({ open, onClose, title, footer, size = 'md', dismissable = true, initialFocus, className, children }) {
  const auto = useId();
  const titleId = `modal-${auto}-title`;
  const box = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const opener = document.activeElement;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const t = setTimeout(() => {
      const el = (initialFocus && box.current?.querySelector(initialFocus)) || box.current?.querySelector('[data-autofocus]') || box.current?.querySelector('.modal__body ' + FOCUSABLE) || box.current?.querySelector(FOCUSABLE) || box.current;
      el?.focus();
    }, 0);
    return () => {
      clearTimeout(t);
      document.body.style.overflow = prevOverflow;
      if (opener && typeof opener.focus === 'function' && document.contains(opener)) opener.focus();
    };
  }, [open]);

  if (!open) return null;

  function onKeyDown(e) {
    if (e.key === 'Escape' && dismissable) {
      e.stopPropagation();
      onClose && onClose();
      return;
    }
    if (e.key !== 'Tab') return;
    const nodes = [...box.current.querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null || n === document.activeElement);
    if (!nodes.length) {
      e.preventDefault();
      box.current.focus();
      return;
    }
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (e.shiftKey && (document.activeElement === first || document.activeElement === box.current)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="modal-root" onKeyDown={onKeyDown}>
      <div className="modal-scrim" onClick={dismissable ? onClose : undefined} />
      <div className={cx('modal', size === 'wide' && 'modal--wide', className)} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} ref={box}>
        <div className="modal__head">
          <h2 className="modal__title" id={titleId}>{title}</h2>
          {dismissable ? <IconButton icon="close" label={S.kit.modal.close} onClick={onClose} /> : null}
        </div>
        <div className="modal__body">{children}</div>
        {footer ? <div className="modal__foot">{footer}</div> : null}
      </div>
    </div>
  );
}
