// Route table. Every screen module exports { id, title, nav:{group,order}, component } and optionally
// path (hash token when it differs from id, e.g. 'entry-new') and aliases (extra hash tokens).
// Hash tokens are plain: #dashboard, #entries, #entry-new, #reports-tb ('reports-' prefix routes to the reports screen).
import * as dashboard from './screens/dashboard/index.jsx';
import * as entries from './screens/entries/index.jsx';
import * as entryForm from './screens/entry-form/index.jsx';
import * as reports from './screens/reports/index.jsx';
import * as parties from './screens/parties/index.jsx';
import * as documents from './screens/documents/index.jsx';
import * as registers from './screens/registers/index.jsx';
import * as assets from './screens/assets/index.jsx';
import * as reconciliation from './screens/reconciliation/index.jsx';
import * as close from './screens/close/index.jsx';
import * as importScreen from './screens/import/index.jsx';
import * as audit from './screens/audit/index.jsx';
import * as system from './screens/system/index.jsx';
import * as settings from './screens/settings/index.jsx';

export const screens = [dashboard, entries, entryForm, reports, parties, documents, registers, assets, reconciliation, close, importScreen, audit, system, settings];

export const DEFAULT_TOKEN = 'dashboard';

export const GROUP_ORDER = ['home', 'journal', 'reports', 'books', 'periods', 'system'];

/** Token (without #) -> { screen, token, sub } or null. 'reports-tb' -> reports screen with sub 'tb'. */
export function resolveRoute(rawToken) {
  const token = String(rawToken || '').replace(/^#/, '') || DEFAULT_TOKEN;
  for (const s of screens) {
    const names = [s.id, s.path, ...(s.aliases || [])].filter(Boolean);
    if (names.includes(token)) return { screen: s, token, sub: '' };
  }
  for (const s of screens) {
    for (const n of [s.id, s.path].filter(Boolean)) {
      if (token.startsWith(`${n}-`)) return { screen: s, token, sub: token.slice(n.length + 1) };
    }
  }
  return null;
}

/** Nav groups: [{ group, items:[screen...] }] in display order (screens without `nav` are not listed). */
export function navGroups() {
  const byGroup = new Map();
  for (const s of screens) {
    if (!s.nav) continue;
    if (!byGroup.has(s.nav.group)) byGroup.set(s.nav.group, []);
    byGroup.get(s.nav.group).push(s);
  }
  const order = [...GROUP_ORDER, ...[...byGroup.keys()].filter((g) => !GROUP_ORDER.includes(g))];
  return order.filter((g) => byGroup.has(g)).map((g) => ({ group: g, items: byGroup.get(g).sort((a, b) => a.nav.order - b.nav.order) }));
}

export const hrefOf = (screen) => `#${screen.path || screen.id}`;
