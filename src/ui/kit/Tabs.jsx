import { useId, useRef } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { Pill } from './Pill.jsx';

/**
 * <Tabs tabs=[{id,label,badge?}] value onChange(id) label="..."> panel content </Tabs>
 * Arrow keys move between tabs (RTL aware), Home/End jump.
 */
export function Tabs({ tabs, value, onChange, label, idPrefix, children, className }) {
  const auto = useId();
  const prefix = idPrefix || `tabs-${auto}`;
  const list = useRef(null);
  function onKey(e) {
    const i = tabs.findIndex((t) => t.id === value);
    const rtl = getComputedStyle(list.current).direction === 'rtl';
    let n = null;
    if (e.key === 'ArrowRight') n = i + (rtl ? -1 : 1);
    else if (e.key === 'ArrowLeft') n = i + (rtl ? 1 : -1);
    else if (e.key === 'Home') n = 0;
    else if (e.key === 'End') n = tabs.length - 1;
    if (n == null) return;
    e.preventDefault();
    n = (n + tabs.length) % tabs.length;
    onChange(tabs[n].id);
    requestAnimationFrame(() => document.getElementById(`${prefix}-tab-${tabs[n].id}`)?.focus());
  }
  return (
    <div className={className}>
      <div className="tabs" role="tablist" aria-label={label} ref={list} onKeyDown={onKey}>
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            className="tab"
            id={`${prefix}-tab-${t.id}`}
            aria-selected={t.id === value ? 'true' : 'false'}
            aria-controls={`${prefix}-panel-${t.id}`}
            tabIndex={t.id === value ? 0 : -1}
            onClick={() => onChange(t.id)}
          >
            {t.label}
            {t.badge != null ? <Pill className="tab__badge">{t.badge}</Pill> : null}
          </button>
        ))}
      </div>
      {children != null ? (
        <div role="tabpanel" id={`${prefix}-panel-${value}`} aria-labelledby={`${prefix}-tab-${value}`} tabIndex={0}>
          {children}
        </div>
      ) : null}
    </div>
  );
}
