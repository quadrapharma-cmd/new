import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'entries';
export const title = S.screens['entries'];
export const nav = { group: 'journal', order: 10 };
export const component = function EntriesScreen() {
  return <StubScreen id="entries" />;
};
