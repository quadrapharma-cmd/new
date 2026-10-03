// The engine state object: plain objects keyed by document id. src/data/store.js builds it from the
// db snapshots; tests build it with tests/synthetic/build-state.js. Every collection may be missing.

/** A state with every collection present and empty (counters start at 1). */
export function emptyState() {
  return {
    config: { schemaVersion: 1, company: {}, baseline: null, settings: { digits: 'western' }, rules: {} },
    counters: { nextEntryNo: 1 },
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
  };
}

/** Index an array of docs by a key field (default 'id'). */
export function indexBy(docs, key = 'id') {
  const out = {};
  for (const d of docs) out[d[key]] = d;
  return out;
}

/** Map a db document path ('entries/e000312', 'meta/counters') to its location in the state object. */
export function statePathOf(path) {
  const [coll, id, ...rest] = String(path).split('/');
  if (rest.length) return null;
  if (coll === 'meta') {
    if (id === 'config') return { key: 'config', id: null };
    if (id === 'counters') return { key: 'counters', id: null };
    if (id === 'groups') return { key: 'groups', id: null, groups: true };
    return null;
  }
  return { key: coll, id };
}
