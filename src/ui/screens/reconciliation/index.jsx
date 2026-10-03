import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'reconciliation';
export const title = S.screens['reconciliation'];
export const nav = { group: 'books', order: 50 };
export const component = function ReconciliationScreen() {
  return <StubScreen id="reconciliation" />;
};
