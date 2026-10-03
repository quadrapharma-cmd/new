// Shared helper for env-gated acceptance tests: loads the PRIVATE seed directory into an engine state.
// Never commit data; the seed lives outside the repo (STRIFA_SEED_DIR, default /home/user/.strifa-private/seed).
import { existsSync, readFileSync } from 'node:fs';
import { loadSeedDir, DEFAULT_SEED_DIR } from '../../dev/load-seed.js';
import { emptyState } from '../../src/engine/index.js';

export const SEED_DIR = process.env.STRIFA_SEED_DIR || DEFAULT_SEED_DIR;
export const ORACLE_PATH = process.env.STRIFA_ORACLE_JSON || '/home/user/.strifa-private/oracle.json';
export const hasRealData = () => existsSync(SEED_DIR) && existsSync(ORACLE_PATH);

/** Engine state built from the private seed (throws when the seed is absent: guard with hasRealData()). */
export function loadSeedState(dir = SEED_DIR) {
  const seed = loadSeedDir(dir);
  const state = emptyState();
  for (const [name, map] of Object.entries(seed)) {
    if (name === 'meta') {
      state.config = { ...state.config, ...map.config };
      state.counters = map.counters;
      state.groups = map.groups.groups;
    } else state[name] = map;
  }
  return state;
}

export const loadOracle = (p = ORACLE_PATH) => JSON.parse(readFileSync(p, 'utf8'));
