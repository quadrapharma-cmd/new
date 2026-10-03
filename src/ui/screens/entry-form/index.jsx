import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'entry-form';
export const title = S.screens['entry-form'];
export const nav = { group: 'journal', order: 20 };
export const path = 'entry-new';
export const aliases = ['entry-edit'];
export const component = function EntryFormScreen() {
  return <StubScreen id="entry-form" />;
};
