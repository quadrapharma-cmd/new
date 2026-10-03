import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'parties';
export const title = S.screens['parties'];
export const nav = { group: 'books', order: 10 };
export const component = function PartiesScreen() {
  return <StubScreen id="parties" />;
};
