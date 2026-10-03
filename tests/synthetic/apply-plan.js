// Test double for src/data/repo.js: applies an engine write plan to an in-memory state object with the same
// semantics as the artifact db (set replaces, update merges objects recursively and replaces arrays, delete removes).
import { statePathOf } from '../../src/engine/state.js';

const isObj = (x) => x && typeof x === 'object' && !Array.isArray(x);
const clone = (x) => (x === undefined ? undefined : JSON.parse(JSON.stringify(x)));

function deepMerge(target, patch) {
  for (const [k, v] of Object.entries(patch)) {
    if (isObj(v) && isObj(target[k])) deepMerge(target[k], v);
    else target[k] = clone(v);
  }
  return target;
}

export function applyWrite(state, w) {
  const loc = statePathOf(w.path);
  if (!loc) throw new Error(`unmapped path ${w.path}`);
  const data = w.data === undefined ? undefined : clone(w.data);
  if (loc.id === null) {
    // single-doc keys: config, counters, groups ({groups:[...]})
    if (w.op === 'delete') throw new Error('cannot delete single doc');
    if (loc.groups) {
      state.groups = w.op === 'set' ? data.groups : (data.groups || state.groups);
      return;
    }
    if (w.op === 'set') state[loc.key] = data;
    else deepMerge(state[loc.key], data);
    return;
  }
  state[loc.key] = state[loc.key] || {};
  const coll = state[loc.key];
  if (w.op === 'set') coll[loc.id] = data;
  else if (w.op === 'update') {
    if (!coll[loc.id]) throw new Error(`update requires existing doc: ${w.path}`);
    deepMerge(coll[loc.id], data);
  } else if (w.op === 'delete') delete coll[loc.id];
  else throw new Error(`bad op ${w.op}`);
}

/** Apply a plan returned by an engine planner. Throws when the plan is not ok. Returns the state. */
export function applyPlan(state, plan, { by = 'u_tester', at = '2024-03-01T10:00:00.000Z' } = {}) {
  if (!plan.ok) throw new Error(`plan not ok: ${JSON.stringify(plan.errors)}`);
  for (const w of plan.writes) applyWrite(state, w);
  // the repo allocates the entry number under its lease and bumps meta/counters itself (plans never write it)
  if (plan.entryNo !== undefined && plan.entryNo !== null) {
    state.counters = state.counters || { nextEntryNo: 1 };
    state.counters.nextEntryNo = Math.max(state.counters.nextEntryNo || 1, plan.entryNo + 1);
  }
  if (plan.audit) {
    const ym = at.slice(0, 7);
    state.audit = state.audit || {};
    state.audit[ym] = state.audit[ym] || { events: [] };
    state.audit[ym].events.push({ at, by, kind: plan.audit.kind, coll: plan.audit.coll, id: plan.audit.id, reason: plan.audit.reason || '', summary: plan.audit.summary || '' });
  }
  return state;
}
