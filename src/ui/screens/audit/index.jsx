import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'audit';
export const title = S.screens['audit'];
export const nav = { group: 'system', order: 10 };
export const component = function AuditScreen() {
  return <StubScreen id="audit" />;
};
