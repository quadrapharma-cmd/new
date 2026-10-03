// Optional end-to-end check: loads the PRIVATE seed into the real engine and compares it with the oracle.
//   node tools/seed/engine_check.mjs        (STRIFA_SEED_DIR / STRIFA_ORACLE_JSON override the default private paths)
// Prints counts only (no names, no amounts). Exit code 0 = PASS. It reads src/engine and dev/load-seed.js, never writes.
import { existsSync, readFileSync } from 'node:fs';
import { loadSeedDir, DEFAULT_SEED_DIR } from '../../dev/load-seed.js';
import {
  emptyState, checkIntegrity, summarizeIntegrity, trialBalance, incomeStatement, balanceSheet, proposeRun, rollForward,
} from '../../src/engine/index.js';

const seedDir = process.env.STRIFA_SEED_DIR || DEFAULT_SEED_DIR;
const oraclePath = process.env.STRIFA_ORACLE_JSON || '/home/user/.strifa-private/oracle.json';
if (!existsSync(seedDir) || !existsSync(oraclePath)) {
  console.log('engine_check: SKIP (seed directory or oracle.json not found)');
  process.exit(0);
}
const seed = loadSeedDir(seedDir);
const oracle = JSON.parse(readFileSync(oraclePath, 'utf8'));
const state = emptyState();
for (const [name, map] of Object.entries(seed)) {
  if (name === 'meta') {
    state.config = { ...state.config, ...map.config };
    state.counters = map.counters;
    state.groups = map.groups.groups;
  } else state[name] = map;
}

let checks = 0;
let bad = 0;
const near = (a, b) => typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) <= 0.005;
const check = (ok) => { checks += 1; if (!ok) bad += 1; return ok; };

const findings = checkIntegrity(state);
const sum = summarizeIntegrity(findings);
check(sum.error === 0);
const warnCodes = {};
for (const f of findings) warnCodes[`${f.severity}:${f.code}`] = (warnCodes[`${f.severity}:${f.code}`] || 0) + 1;

const years = Object.keys(oracle.years).map(Number).sort((a, b) => a - b);
for (const y of years) {
  const o = oracle.years[String(y)];
  const is = incomeStatement({ state, year: y });
  check(near(is.netResult, o.netResult));
  const bs = balanceSheet({ state, asOf: `${y}-12-31` });
  check(near(bs.liabilities?.total ?? bs.liabilities, o.liabilities));
  check(near(bs.equity?.total ?? bs.equity, o.equity));
  check(bs.check.balanced === true);
  const tb = trialBalance({ state, mode: 'cumulative', asOf: `${y}-12-31` });
  check(near(tb.totals.closingDr, o.tbCumulative.debit) && near(tb.totals.closingCr, o.tbCumulative.credit));
  const run = proposeRun({ state, year: y });
  check(near(run.total, o.depreciation ? o.depreciation.total : oracle.depreciationPosted[String(y)].total));
  const by = {};
  for (const c of run.classes.accum) by[c.acct] = c.amount;
  const exp = oracle.depreciationPosted[String(y)].byAccum;
  for (const k of new Set([...Object.keys(by), ...Object.keys(exp)])) check(near(by[k] || 0, exp[k] || 0));
  const rf = rollForward({ state, year: y });
  check(rf.ok === true);
}

console.log(`engine_check: ${bad === 0 ? 'PASS' : 'FAIL'} (checks=${checks}, mismatches=${bad})`);
console.log(`integrity: errors=${sum.error} warnings=${sum.warn} info=${sum.info}`, JSON.stringify(warnCodes));
process.exit(bad === 0 ? 0 : 1);
