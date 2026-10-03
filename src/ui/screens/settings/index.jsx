import { S } from '../../../lib/i18n.js';
import { StubScreen } from '../_stub.jsx';

// STUB: replace this component with the real screen (keep the exports: id, title, nav, component).
export const id = 'settings';
export const title = S.screens['settings'];
export const nav = { group: 'system', order: 30 };
export const component = function SettingsScreen() {
  return <StubScreen id="settings" />;
};
