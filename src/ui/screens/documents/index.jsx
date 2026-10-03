import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'documents';
export const title = S.screens['documents'];
export const nav = { group: 'books', order: 20 };
export const component = function DocumentsScreen() {
  return <StubScreen id="documents" />;
};
