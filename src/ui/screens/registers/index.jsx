import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'registers';
export const title = S.screens['registers'];
export const nav = { group: 'books', order: 30 };
export const component = function RegistersScreen() {
  return <StubScreen id="registers" />;
};
