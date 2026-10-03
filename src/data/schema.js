// Collection names, limits and defaults for the artifact db (see docs/DATA_MODEL.md in the spec).
import { deepClone } from '../lib/ids.js';

export const DOC_CAP = 5000; // documents per artifact
export const DOC_BYTES_CAP = 256 * 1024; // serialized bytes per document
export const SUBSCRIPTION_CAP = 64; // live subscriptions per view
export const AUDIT_ROLL_BYTES = 180 * 1024; // roll to the next audit doc past this size
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024; // platform limit for assets is 20 MiB

/**
 * One live subscription per collection. `key` is where the docs land in the engine state.
 * 'meta' is special: meta/config -> state.config, meta/counters -> state.counters, meta/groups -> state.groups.
 */
export const COLLECTIONS = [
  { name: 'meta', key: null },
  { name: 'accounts', key: 'accounts' },
  { name: 'costCenters', key: 'costCenters' },
  { name: 'sectors', key: 'sectors' },
  { name: 'parties', key: 'parties' },
  { name: 'documents', key: 'documents' },
  { name: 'entries', key: 'entries' },
  { name: 'fiscalYears', key: 'fiscalYears' },
  { name: 'openItems', key: 'openItems' },
  { name: 'assumptions', key: 'assumptions' },
  { name: 'assets', key: 'assets' },
  { name: 'depRuns', key: 'depRuns' },
  { name: 'reconciliations', key: 'reconciliations' },
  { name: 'templates', key: 'templates' },
  { name: 'registers', key: 'registers' },
  { name: 'audit', key: 'audit' },
  { name: 'importRuns', key: 'importRuns' },
];

export const COLLECTION_NAMES = COLLECTIONS.map((c) => c.name);

export const defaultConfig = () => ({
  schemaVersion: 1,
  company: { name: '', formerName: '', taxNo: '', crNo: '', incorporated: '' },
  baseline: null,
  settings: { digits: 'western' },
});
export const defaultCounters = () => ({ nextEntryNo: 1 });

/** Fresh, empty engine state (plain objects keyed by doc id). */
export function emptyState() {
  return {
    config: defaultConfig(),
    counters: defaultCounters(),
    accounts: {},
    groups: [],
    costCenters: {},
    sectors: {},
    parties: {},
    documents: {},
    entries: {},
    fiscalYears: {},
    openItems: {},
    assumptions: {},
    assets: {},
    depRuns: {},
    reconciliations: {},
    templates: {},
    registers: {},
    audit: {},
    importRuns: {},
  };
}

/** Merge a stored config doc over the defaults (one level deep for company/settings). */
export function mergeConfig(doc) {
  const d = defaultConfig();
  if (!doc) return d;
  const src = deepClone(doc);
  return {
    ...d,
    ...src,
    company: { ...d.company, ...(src.company || {}) },
    settings: { ...d.settings, ...(src.settings || {}) },
  };
}

/** Path helpers */
export const docPath = (collection, id) => `${collection}/${id}`;
export function splitPath(path) {
  const parts = String(path).split('/');
  return { collection: parts.slice(0, -1).join('/'), id: parts[parts.length - 1], depth: parts.length };
}
export const auditDocId = (ym, suffix = '') => `${ym}${suffix ? `-${suffix}` : ''}`;
