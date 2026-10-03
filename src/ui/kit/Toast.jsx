import { useEffect, useState } from 'preact/hooks';
import { S } from '../../lib/i18n.js';
import { cx } from '../../lib/format.js';

// Module-level queue so any code (screens, repo callers) can raise a toast without context.
let items = [];
let nextId = 1;
const listeners = new Set();
const emit = () => listeners.forEach((fn) => fn(items));

function show(text, { kind = 'info', ttl } = {}) {
  const id = nextId++;
  const life = ttl ?? (kind === 'critical' ? 9000 : 4500);
  items = [...items.slice(-3), { id, text: String(text), kind }];
  emit();
  if (life > 0) setTimeout(() => dismiss(id), life);
  return id;
}
function dismiss(id) {
  items = items.filter((t) => t.id !== id);
  emit();
}

export const toast = {
  show,
  info: (t, o) => show(t, { ...o, kind: 'info' }),
  success: (t, o) => show(t, { ...o, kind: 'good' }),
  warn: (t, o) => show(t, { ...o, kind: 'warn' }),
  error: (t, o) => show(t, { ...o, kind: 'critical' }),
  dismiss,
  clear: () => {
    items = [];
    emit();
  },
};

export function ToastHost() {
  const [list, setList] = useState(items);
  useEffect(() => {
    listeners.add(setList);
    return () => listeners.delete(setList);
  }, []);
  return (
    <div className="toasts" aria-live="polite" aria-atomic="false">
      {list.map((t) => (
        <div key={t.id} className={cx('toast', t.kind !== 'info' && `toast--${t.kind}`)} role={t.kind === 'critical' ? 'alert' : 'status'}>
          <div className="toast__text">{t.text}</div>
          <button type="button" className="toast__close" aria-label={S.kit.toast.close} onClick={() => dismiss(t.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
