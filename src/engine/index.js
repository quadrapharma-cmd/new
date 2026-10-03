// Accounting engine barrel: pure ES modules, zero dependencies. See docs/DATA_MODEL.md for the plan/write contract.
export * from './constants.js';
export { emptyState, indexBy, statePathOf } from './state.js';
export { coll, resolvePartyId, entryIdFor, maxEntryNo, normalizeEntry, normalizeLine } from './util.js';
export { postedLines, balances, balanceMap, normalizeFilters, accountBalanceCents } from './ledger.js';
export {
  trialBalance, incomeStatement, incomeComparative, balanceSheet, accountStatement, partyStatement, partyBalances,
  fsLineOf, normalSideOf, yearsWithActivity, boundAccountsOf,
} from './statements.js';
export { validateEntry, periodGate, buildDupIndex } from './validation.js';
export { planPost, planSaveDraft, planDeleteDraft, nextEntryNo, fail as planFailure } from './posting.js';
export {
  planAmend, planVoid, planReverse, planCloseYear, planReopenYear, planLockYear, planUnlockYear,
  closeChecklist, changesSinceClose, snapshotDiff,
} from './amend.js';
export {
  computeAssetCharge, accumulatedBeforeC, proposeRun, planProposeRun, planPostDepreciation, rollForward, normalizeRate,
} from './depreciation.js';
export { applyTemplate, builtinRules, defaultTemplates } from './templates.js';
export { checkIntegrity, summarizeIntegrity } from './integrity.js';
export { normalizeName, stripTitle, suggestMerges } from './party.js';
