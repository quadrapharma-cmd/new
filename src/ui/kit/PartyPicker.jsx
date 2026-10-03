import { useMemo, useState } from 'preact/hooks';
import { S, fmt } from '../../lib/i18n.js';
import { normalizeText } from '../../lib/format.js';
import { Combobox } from './Combobox.jsx';
import { rankParties } from './rank.js';

export const PARTY_KIND_LABEL = S.kit.partyKinds;

/**
 * Search party names and aliases. parties: state.parties.  value: party id | null.  onChange(id, party).
 * onCreate(name) -> Promise<id | party>: the inline quick-create hook; when given and nothing matches exactly,
 * the list offers «إضافة «text» كطرف جديد» (only offer it to editors: pass undefined when read-only).
 */
export function PartyPicker({ id, parties, value, onChange, recent = [], onCreate, placeholder = S.kit.party.placeholder, disabled, invalid, inputProps }) {
  const [busy, setBusy] = useState(false);
  const list = useMemo(() => (Array.isArray(parties) ? parties : Object.values(parties || {})), [parties]);
  const current = value ? list.find((p) => p.id === value) : null;
  const options = (q) => {
    const ranked = rankParties(list, q, { recent, keepIds: value ? [value] : [] }).map(({ party, via }) => ({
      value: party.id,
      label: party.name,
      sub: via ? `${S.kit.party.alias}: ${via}` : PARTY_KIND_LABEL[party.kind] || '',
    }));
    const text = q.trim();
    if (onCreate && text.length >= 2) {
      const n = normalizeText(text);
      if (!list.some((p) => normalizeText(p.name) === n && !p.mergedInto)) {
        ranked.push({ value: '__create__', kind: 'create', label: fmt(S.kit.party.create, { name: text }), text });
      }
    }
    return ranked;
  };
  async function onSelect(o) {
    if (o.kind === 'create') {
      setBusy(true);
      try {
        const res = await onCreate(o.text);
        const newId = typeof res === 'string' ? res : res?.id;
        if (newId && onChange) onChange(newId, typeof res === 'object' ? res : null);
      } finally {
        setBusy(false);
      }
      return;
    }
    onChange && onChange(o.value, list.find((p) => p.id === o.value) || null);
  }
  return (
    <Combobox
      id={id}
      options={options}
      selectedLabel={current ? current.name : value ? String(value) : ''}
      placeholder={placeholder}
      disabled={disabled || busy}
      invalid={invalid || (!!value && !current)}
      emptyText={S.kit.party.none}
      inputProps={inputProps}
      onSelect={onSelect}
    />
  );
}
