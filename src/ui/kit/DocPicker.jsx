import { useMemo, useState } from 'preact/hooks';
import { S } from '../../lib/i18n.js';
import { Combobox } from './Combobox.jsx';
import { Button } from './Button.jsx';
import { Icon } from './icons.jsx';
import { rankDocuments } from './rank.js';

/**
 * Multi-select of supporting documents (an entry can cite several; one document backs many entries).
 * documents: state.documents.  value: string[] of doc ids.  onChange(ids).
 * reuse: ids of the previous entry's documents (shows a one-click "same as previous entry" button).
 * onCreate(): optional hook for the inline "+ مستند جديد" flow; must resolve the new doc id.
 */
export function DocPicker({ id, documents, value = [], onChange, reuse = [], recent = [], onCreate, placeholder = S.kit.doc.placeholder, disabled, invalid, inputProps }) {
  const [busy, setBusy] = useState(false);
  const list = useMemo(() => (Array.isArray(documents) ? documents : Object.values(documents || {})), [documents]);
  const byId = useMemo(() => new Map(list.map((d) => [d.id, d])), [list]);
  const options = (q) => {
    const ranked = rankDocuments(list, q, { recent: [...recent, ...reuse], excludeIds: value }).map((d) => ({
      value: d.id,
      code: d.id,
      label: d.ref || d.type || d.id,
      sub: d.status === 'expected' ? S.kit.doc.expected : d.type,
    }));
    if (onCreate) ranked.push({ value: '__create__', kind: 'create', label: `+ ${S.kit.doc.create}` });
    return ranked;
  };
  async function onSelect(o) {
    if (o.kind === 'create') {
      setBusy(true);
      try {
        const newId = await onCreate();
        if (newId) onChange([...value, newId]);
      } finally {
        setBusy(false);
      }
      return;
    }
    onChange([...value, o.value]);
  }
  const canReuse = reuse.length > 0 && reuse.join() !== value.join();
  return (
    <div className="stack-sm">
      {value.length ? (
        <ul className="chips" style={{ listStyle: 'none', margin: 0, padding: 0 }} aria-label={S.screens.documents}>
          {value.map((did) => {
            const d = byId.get(did);
            return (
              <li key={did} className="chip">
                <span className="mono">{did}</span>
                <span className="chip__label">{d?.ref || ''}</span>
                {!disabled ? (
                  <button type="button" className="chip__x" aria-label={`${S.common.remove} ${did}`} onClick={() => onChange(value.filter((x) => x !== did))}>
                    <Icon name="close" />
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
      {!disabled ? (
        <>
          <Combobox
            id={id}
            options={options}
            selectedLabel=""
            placeholder={placeholder}
            disabled={busy}
            invalid={invalid}
            emptyText={S.kit.doc.none}
            inputProps={inputProps}
            onBackspaceEmpty={() => value.length && onChange(value.slice(0, -1))}
            onSelect={onSelect}
          />
          {canReuse ? (
            <div>
              <Button size="sm" kind="ghost" onClick={() => onChange([...reuse])}>{S.kit.doc.reuse}</Button>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
