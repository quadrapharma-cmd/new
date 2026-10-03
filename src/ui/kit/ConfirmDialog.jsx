import { useEffect, useState } from 'preact/hooks';
import { S } from '../../lib/i18n.js';
import { Button } from './Button.jsx';
import { Modal } from './Modal.jsx';
import { Field } from './Field.jsx';
import { Textarea } from './TextInput.jsx';

/**
 * In-page confirmation (the platform never shows window.confirm).
 * With `reasonLabel` the dialog asks for a mandatory written reason and onConfirm(reason) receives it
 * (amendments, reopening a closed year).
 */
export function ConfirmDialog({ open, title, message, confirmLabel = S.common.confirm, cancelLabel = S.common.cancel, danger = false, reasonLabel, reasonHint, busy = false, onConfirm, onCancel }) {
  const [reason, setReason] = useState('');
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (open) {
      setReason('');
      setTouched(false);
    }
  }, [open]);
  const needReason = !!reasonLabel;
  const missing = needReason && !reason.trim();
  function go() {
    if (missing) {
      setTouched(true);
      return;
    }
    onConfirm && onConfirm(needReason ? reason.trim() : undefined);
  }
  return (
    <Modal
      open={open}
      onClose={busy ? undefined : onCancel}
      title={title}
      dismissable={!busy}
      footer={
        <>
          <Button kind={danger ? 'danger' : 'primary'} busy={busy} onClick={go} data-autofocus={needReason ? undefined : ''}>{confirmLabel}</Button>
          <Button onClick={onCancel} disabled={busy}>{cancelLabel}</Button>
        </>
      }
    >
      {message ? <p>{message}</p> : null}
      {needReason ? (
        <Field label={reasonLabel} hint={reasonHint} required error={touched && missing ? S.common.reasonRequired : null} id="confirm-reason">
          {(p) => <Textarea {...p} value={reason} onChange={setReason} data-autofocus="" />}
        </Field>
      ) : null}
    </Modal>
  );
}

// ---- imperative API: confirmAsync({title, message, ...}) -> Promise<false | true | string(reason)> -------------
let current = null;
const listeners = new Set();
const emit = () => listeners.forEach((fn) => fn(current));

/** Resolves false on cancel; true on confirm; the trimmed reason string when `reasonLabel` was given. */
export function confirmAsync(opts) {
  return new Promise((resolve) => {
    if (current) current.resolve(false);
    current = { opts, resolve };
    emit();
  });
}

/** Mount once near the root of the app. */
export function ConfirmHost() {
  const [cur, setCur] = useState(current);
  useEffect(() => {
    listeners.add(setCur);
    return () => listeners.delete(setCur);
  }, []);
  const close = (v) => {
    const c = current;
    current = null;
    emit();
    c && c.resolve(v);
  };
  if (!cur) return null;
  return <ConfirmDialog open {...cur.opts} onConfirm={(reason) => close(reason !== undefined ? reason : true)} onCancel={() => close(false)} />;
}
