import { useMemo } from 'preact/hooks';
import { S } from '../../lib/i18n.js';
import { toWesternDigits } from '../../lib/digits.js';
import { Combobox } from './Combobox.jsx';
import { rankAccounts } from './rank.js';

/**
 * Pick a postable, active account by typing its code or Arabic name.
 * accounts: state.accounts (map or array).  value: code | null.  onChange(code, account).  recent: recently used codes.
 * Ranking: exact code, code prefix, name matches; recently used first. Tab / leaving the field accepts an exact code.
 */
export function AccountPicker({ id, accounts, value, onChange, recent = [], placeholder = S.kit.account.placeholder, disabled, invalid, includeInactive = false, inputProps }) {
  const list = useMemo(() => (Array.isArray(accounts) ? accounts : Object.values(accounts || {})), [accounts]);
  const current = value ? list.find((a) => String(a.code) === String(value)) : null;
  const keepCodes = value ? [value] : [];
  const make = (a, q) => ({
    value: a.code,
    code: a.code,
    label: a.name,
    sub: a.active === false ? S.kit.account.inactiveNote : !q && recent.includes(a.code) ? S.kit.account.recent : a.cls,
  });
  const options = (q) => rankAccounts(list, q, { recent, includeInactive, keepCodes }).map((a) => make(a, q));
  const autoCommit = (q, items) => {
    const code = toWesternDigits(q).trim();
    return items.find((o) => String(o.value) === code) || null;
  };
  const label = current ? `${current.code} ${current.name}` : value ? String(value) : '';
  return (
    <Combobox
      id={id}
      options={options}
      selectedLabel={label}
      placeholder={placeholder}
      disabled={disabled}
      invalid={invalid || (!!value && !current)}
      emptyText={S.kit.account.none}
      autoCommit={autoCommit}
      inputProps={inputProps}
      onSelect={(o) => onChange && onChange(o.value, list.find((a) => a.code === o.value) || null)}
    />
  );
}
