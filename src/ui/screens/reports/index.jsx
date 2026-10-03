import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'reports';
export const title = S.screens['reports'];
export const nav = { group: 'reports', order: 10 };
export const component = function ReportsScreen() {
  return <StubScreen id="reports" />;
};
