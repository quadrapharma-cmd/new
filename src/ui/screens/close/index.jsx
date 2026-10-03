import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'close';
export const title = S.screens['close'];
export const nav = { group: 'periods', order: 10 };
export const component = function CloseScreen() {
  return <StubScreen id="close" />;
};
