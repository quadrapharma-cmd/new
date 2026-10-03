import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'import';
export const title = S.screens['import'];
export const nav = { group: 'periods', order: 20 };
export const component = function ImportScreen() {
  return <StubScreen id="import" />;
};
