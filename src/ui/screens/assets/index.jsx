import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'assets';
export const title = S.screens['assets'];
export const nav = { group: 'books', order: 40 };
export const component = function AssetsScreen() {
  return <StubScreen id="assets" />;
};
