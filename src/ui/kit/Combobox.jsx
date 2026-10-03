import { useEffect, useId, useRef, useState } from 'preact/hooks';
import { cx } from '../../lib/format.js';
import { S } from '../../lib/i18n.js';

/**
 * Generic type-ahead (ARIA 1.2 combobox with listbox popup). Used by AccountPicker, PartyPicker and DocPicker.
 *  options(query) -> [{ value, label, code?, sub?, disabled?, kind? }]   (called on every render while open)
 *  onSelect(option)            selected by click, Enter or (with autoCommit) Tab / blur
 *  selectedLabel               text shown while closed
 *  autoCommit(query, list)     optional: returns the option to accept when the user tabs / blurs away with text typed
 *  onBackspaceEmpty()          optional: Backspace in an empty box (multi-select chips)
 */
export function Combobox({ id, options, selectedLabel = '', onSelect, placeholder, disabled, invalid, emptyText, autoCommit, onBackspaceEmpty, mono = false, className, inputProps = {} }) {
  const auto = useId();
  const cid = id || `cb-${auto}`;
  const listId = `${cid}-list`;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [pos, setPos] = useState(null);
  const inputRef = useRef(null);

  // The list is position:fixed so it is never clipped by an overflow container (tables, grids, modals)
  useEffect(() => {
    if (!open) return undefined;
    const place = () => {
      const el = inputRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const below = window.innerHeight - r.bottom;
      const width = Math.max(r.width, 260);
      const left = Math.min(Math.max(8, r.right - width), window.innerWidth - width - 8); // aligned to the input's start edge (right in RTL)
      const flip = below < 200 && r.top > below;
      setPos(flip ? { left, width, bottom: window.innerHeight - r.top + 4, maxHeight: Math.min(280, r.top - 12) } : { left, width, top: r.bottom + 4, maxHeight: Math.min(280, Math.max(120, below - 12)) });
    };
    place();
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [open]);

  const list = open ? options(query) : [];
  const act = Math.min(active, Math.max(0, list.length - 1));

  useEffect(() => {
    if (open) document.getElementById(`${cid}-opt-${act}`)?.scrollIntoView({ block: 'nearest' });
  }, [act, open, list.length]);

  function close() {
    setOpen(false);
    setQuery('');
    setActive(0);
  }
  function choose(o) {
    if (!o || o.disabled) return;
    close();
    onSelect(o);
  }
  function onKeyDown(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) setOpen(true);
      else setActive(Math.min(list.length - 1, act + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) setOpen(true);
      else setActive(Math.max(0, act - 1));
    } else if (e.key === 'Enter') {
      if (open && list[act]) {
        e.preventDefault();
        choose(list[act]);
      }
    } else if (e.key === 'Escape') {
      if (open) {
        e.stopPropagation();
        close();
      }
    } else if (e.key === 'Tab') {
      if (open && query && autoCommit && !e.shiftKey) {
        const o = autoCommit(query, list);
        if (o) choose(o);
        else close();
      } else close();
    } else if (e.key === 'Backspace' && !query && onBackspaceEmpty) {
      onBackspaceEmpty();
    }
  }
  function onBlur() {
    if (open && query && autoCommit) {
      const o = autoCommit(query, list);
      if (o) {
        choose(o);
        return;
      }
    }
    close();
  }

  return (
    <div className={cx('combo', className)}>
      <input
        id={cid}
        type="text"
        role="combobox"
        aria-expanded={open ? 'true' : 'false'}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && list.length ? `${cid}-opt-${act}` : undefined}
        aria-invalid={invalid ? 'true' : undefined}
        autoComplete="off"
        spellCheck={false}
        ref={inputRef}
        className={cx('input', mono && 'input--code')}
        disabled={disabled}
        value={open ? query : selectedLabel}
        placeholder={open && selectedLabel ? selectedLabel : placeholder}
        onFocus={() => {
          setOpen(true);
          setQuery('');
          setActive(0);
        }}
        onInput={(e) => {
          setOpen(true);
          setQuery(e.currentTarget.value);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        {...inputProps}
      />
      {open ? (
        <ul className="combo__list" role="listbox" id={listId} style={pos || { visibility: 'hidden' }}>
          {list.length === 0 ? <li className="combo__empty" role="presentation">{emptyText || S.common.noResults}</li> : null}
          {list.map((o, i) => (
            <li
              key={`${o.kind || 'o'}-${o.value}`}
              id={`${cid}-opt-${i}`}
              role="option"
              className="combo__opt"
              aria-selected={i === act ? 'true' : 'false'}
              aria-disabled={o.disabled ? 'true' : undefined}
              onMouseDown={(e) => e.preventDefault()}
              onMouseMove={() => i !== act && setActive(i)}
              onClick={() => choose(o)}
            >
              {o.code ? <span className="combo__code">{o.code}</span> : null}
              <span className={cx('combo__label', o.kind === 'create' && 'combo__create')}>{o.label}</span>
              {o.sub ? <span className="combo__sub">{o.sub}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
