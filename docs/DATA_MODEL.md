# Data model and write-plan contract

Schema of the artifact `db` as the engine (`src/engine/`) reads and writes it, made precise: field types, enums,
invariants, who writes what, and the plan/write contract between the pure engine and `src/data/repo.js`.
Everything here is configuration or structure. **No company data lives in this repository** (see
`BUILD_SPEC_V2.md` rule 1); examples use invented values.

## 1. Conventions

| Topic | Rule |
|---|---|
| Money | JSON numbers with at most 2 decimals, never negative on a line. All arithmetic is in **integer piastres** (`toCents`/`fromCents`). Generated amounts round **ROUND_HALF_UP on the exact decimal product** (ties go away from zero); never `toFixed`. Percentage splits use largest remainder (`allocateCents`) so parts add up. |
| Dates | `'YYYY-MM-DD'` strings. No timezone arithmetic. Fiscal year = calendar year of the entry **header** date (`fy`). Audit stamps (`at`, `createdAt`, ...) are ISO UTC timestamps. |
| Ids | Entries: numbered `e` + 6-digit zero-padded number (`e000312`; more digits past 999,999), drafts `d_<base36 time>_<rand>`. Parties `p0001`, documents `D0001`. Accounts by code string (`'1340'`). Registers by item number (`openItems/81`). Fiscal years by year (`fiscalYears/2024`). Entry docs do **not** store their own id; the engine takes it from the state key. |
| Sign convention | Signed figures in reports are debit-positive (`dr - cr`). Per-account "natural" figures are positive in the account's normal direction. |
| Doc limits | At most 256 KiB / 32 levels per doc, 5,000 docs per artifact, last-writer-wins, no transactions, `update` merges objects but **replaces arrays**, `set` replaces the whole doc. The engine refuses an amended entry whose history would pass 240 KiB (`entry-too-large`): reverse it instead. |
| Purity | Engine functions never mutate their input (tests run them on deeply frozen state) and never touch the db. They return values or write plans. |

## 2. The engine state object

Built by `src/data/store.js` from the db snapshots, consumed by every engine function. Plain objects keyed by doc id;
every collection may be missing (the engine uses `coll(state, name)`).

```
{ config, counters, accounts:{[code]}, groups:[...], costCenters:{[id]}, sectors:{[id]}, parties:{[id]},
  documents:{[id]}, entries:{[id]}, fiscalYears:{[year]}, openItems:{[n]}, assumptions:{[n]}, assets:{[id]},
  depRuns:{[year]}, reconciliations:{[id]}, templates:{[id]}, registers:{[name]}, audit:{[ym]} }
```
`meta/config` -> `config`, `meta/counters` -> `counters`, `meta/groups` -> `groups` (the array inside the doc).
`src/engine/state.js` exports `emptyState()` and `statePathOf(path)`.

## 3. Collections

"Writer" names the code path that creates or changes the doc. Viewers read everything; only editors write
(`db rules: read interact, write admin`).

### 3.1 `meta/config`
| Field | Type | Notes |
|---|---|---|
| `schemaVersion` | integer | `1` |
| `company` | `{name, formerName, taxNo, crNo, incorporated}` | strings; `incorporated` is `'YYYY-MM-DD'` or `''`. Entries dated before it get the warning `before-incorporation`. |
| `baseline` | `{file, sha256, wbCreated, wbModified, importedAt, counts:{...}}` or `null` | importer only |
| `settings` | `{digits: 'western'\|'arabic'}` | display preference |
| `rules` | optional object | engine rules as **data** (defaults in `constants.js` `DEFAULT_RULES`): `fundingAccounts: string[]` (cash-funding accounts), `evidenceGrades: string[]` (default `['A','B']`), `sharedSectorNames: string[]` (default `['مشترك']`), `draftMaxAgeDays` (7), `maxEntryBytes`, `accrualAccountOf: {[fundingAcct]: accrualAcct}` (used by the `cash-funding-evidence` rule) |

Writer: importer (first run), System/Admin screen.

### 3.2 `meta/counters`
`{nextEntryNo: integer}`. **Only the repo writes it**: it allocates numbers under a lease on this doc and bumps the
counter after the numbered entry doc is written. Planners never include a `meta/counters` write. Invariant:
`nextEntryNo > max(no)` over posted/void entries (`counter-behind`, `counter-invalid`).

### 3.3 `meta/groups`
`{groups: [{code: string, name: string, level: 1|2}]}` non-postable section/group rows (6 sections, 17 groups). Importer/admin.

### 3.4 `accounts/<code>`
| Field | Type | Notes |
|---|---|---|
| `code` | string | `^[1-9][0-9]{0,3}$`; immutable once a line uses it (`everUsed`) |
| `name`, `notes` | string | long business notes live in `notes` |
| `cls` | one of the 11 classification words | table below |
| `type` | `asset\|liability\|equity\|revenue\|expense\|suspense` | must agree with `cls` (`account-class-mismatch`) |
| `normal` | `'D'\|'C'` | normal balance side |
| `contra` | boolean | |
| `contraOf` | code or `null` | contra accounts only (`account-contraof-missing`) |
| `fsLine` | `ASSET, ACCUM_DEP, LIABILITY, CAPITAL, CAPITAL_CALLED, SETTLEMENT_SHARES, RETAINED, REVENUE, REVENUE_CONTRA, COGS, OPEX, NONDEDUCTIBLE, SUSPENSE` | statement line. Missing = the default implied by `cls` (`fsLineOf`). `CAPITAL` is the class default for equity, so `SETTLEMENT_SHARES` and `RETAINED` must be set per account. |
| `parent` | string or `null` | group code |
| `postable` | boolean | `false` = header/group row; posting to it is an error |
| `active` | boolean | `false` blocks **new or edited** lines; unchanged legacy lines only warn |
| `partyRule` | `none\|recommended\|required` | `required`: error on new/edited lines; `recommended`: warning that sets needs-review |
| `everUsed` | boolean | set by the planners the first time a posted line uses the account |

Classification table (the engine's `CLS`):

| `cls` | type | normal | contra | default `fsLine` |
|---|---|---|---|---|
| أصول | asset | D | no | ASSET |
| مجمع إهلاك | asset | C | yes | ACCUM_DEP |
| التزامات | liability | C | no | LIABILITY |
| حقوق ملكية | equity | C | no | CAPITAL (per account: SETTLEMENT_SHARES, RETAINED) |
| حقوق ملكية مدين | equity | D | yes | CAPITAL_CALLED |
| إيرادات | revenue | C | no | REVENUE |
| إيرادات مدين | revenue | D | yes | REVENUE_CONTRA |
| تكلفة مبيعات | expense | D | no | COGS |
| مصروفات | expense | D | no | OPEX |
| مصروفات غير واجبة الخصم | expense | D | no | NONDEDUCTIBLE |
| وسيط | suspense | C | no | SUSPENSE |

Writer: importer, Admin (chart). Planners write only `everUsed`.

### 3.5 `costCenters/<id>`, `sectors/<id>`
`costCenters`: `{id, name, kind: 'own'|'fiduciary', active}`. `sectors`: `{id, name, active}`. Ids are opaque strings.
A **fiduciary** cost center is excluded from reports when `includeFiduciary: false`; an entry touching one that does
not net to zero inside it only gets the warning `fiduciary-imbalance`.

### 3.6 `parties/<id>`
| Field | Type | Notes |
|---|---|---|
| `id`, `name` | string | |
| `kind` | `shareholder\|financier\|supplier\|employee\|government\|bank\|customer\|professional\|group\|other` | |
| `aliases` | `string[]` | normalised alias keys feed `suggestMerges` |
| `roles` | `[{role, from, to}]` | dated roles |
| `taxId` | string | |
| `active` | boolean | |
| `mergedInto` | party id or `null` | merged parties are resolved to the survivor by every report/filter (`resolvePartyId`); integrity flags lines not yet re-pointed |
| `defaultAccount` | account code or `null` | used by templates (`party.defaultAccount`) and by the **account-bound** party view |
| `legacyTexts` | `string[]` | original free-text spellings |
| `boundAccounts` | optional `string[]` | additive: accounts bound to the party for the account-bound view; falls back to `[defaultAccount]` |
| `accrualAccount` | optional account code | additive: used by the `cash-funding-evidence` rule when `config.rules.accrualAccountOf` has no entry |

### 3.7 `documents/<id>`
`{id, ref, type, date, grade: 'A'|'B'|'C'|null, status: 'expected'|'received', note, files:[{assetId,name,size,type}], legacyUseCount}`.
Grade A = bank document, B = hand-kept treasury/cash book, C = management statement. The funding-evidence warning
counts a document as evidence when its grade is in `config.rules.evidenceGrades`.

### 3.8 `entries/<id>`
| Field | Type | Notes |
|---|---|---|
| `no` | integer >= 1 or `null` | `null` only while draft; unique across posted/void entries; **never reused** |
| `date` | ISO date | header date; drives the period and `fy` |
| `fy` | integer | `year(date)`, written by the engine |
| `status` | `draft\|posted\|void` | see state machine |
| `desc` | string | |
| `docIds` | `string[]` | header documents; a line with its own non-empty `docIds` overrides |
| `cc`, `sector` | ids or `null` | header defaults; a line value overrides |
| `source` | `legacy\|user\|depreciation\|template:<id>\|reversal` | |
| `isLegacy`, `legacyRow` | boolean, integer or `null` | imported entries |
| `version` | integer >= 1 | `1 + count(history items of kind amend/void)` (`version-history-mismatch`) |
| `voidReason` | string or `null` | mandatory when `void` |
| `reversalOf` | entry doc id or `null` | |
| `createdBy`, `createdAt`, `postedBy`, `postedAt` | user id / ISO timestamp or `null` | |
| `lines` | `Line[]` | |
| `history` | `HistoryItem[]` | append-only by convention |

`Line`: `{n: integer >= 1 (unique in the entry), acct: string, dr: number >= 0, cr: number >= 0, memo, partyId: string|null, docIds: string[], cc, sector, valueDate: ISO|null, needsReview: boolean, reviewReason: string, links: [{t:'a'|'o', n}], legacy: {partyText, docText, row}|null}`.
`links` cite register items: `t:'a'` = `assumptions/<n>`, `t:'o'` = `openItems/<n>`.

`HistoryItem`: `{v: integer, at: ISO timestamp, by: user id|null, kind: 'post'|'amend'|'void', reason: string, before: <entry minus history> | null, periodState?: 'closed_reserved'}`.
`v` is the version created by the change; `before` is the full previous content (version `v - 1`). A `post` item exists
only when an entry is posted into a `closed_reserved` year (it records the reason). `'reopen'` is reserved for
year-level events, which are audited, not stored on entries.

**State machine**

| From | Action (planner) | To | Rules |
|---|---|---|---|
| (new) | `planSaveDraft` | draft | no validation gate, no number, no audit |
| draft | `planDeleteDraft` | (deleted) | audited as `draft-delete` |
| draft / new | `planPost` | posted | full validation, number = max+1, drafts doc deleted, `version 1` |
| posted | `planAmend` | posted | reason + `expectedVersion` mandatory, history snapshot, `version + 1`, number kept |
| posted | `planVoid` | void | reason + `expectedVersion`, keeps its number and history; excluded from every report; terminal |
| posted | `planReverse` | posted + new entry | new numbered entry `source:'reversal'`, `reversalOf`, sides swapped; only one active reversal per entry |

**Dimension precedence.** Effective `cc`, `sector` and documents of a line are the line's own value when non-empty,
else the header's. Posting requires all three (document, cost center, sector) on every line.

### 3.9 `fiscalYears/<year>`
| Field | Type | Notes |
|---|---|---|
| `year`, `startDate`, `endDate`, `legalStart` | integer, ISO, ISO, ISO or `null` | `legalStart` only for report titles |
| `state` | `open\|closed_reserved\|locked` | a year with no doc is `open` |
| `reservation` | `{sources, notRecorded, text, lastUpdate}` | strings (`lastUpdate` ISO date or `null`) |
| `revision` | integer | +1 per change recorded in a `closed_reserved` year, per reopen, per unlock |
| `snapshot` | `{takenAt, totals:{dr,cr}, tb:[{acct,dr,cr}], netResult, revision}` or `null` | cumulative trial balance at 31 Dec, taken at close and refreshed at lock; `netResult` and `revision` are additive |
| `neededDocs` | `[{text}]` | |
| `closedAt`, `closedBy` | ISO timestamp / user id or `null` | |
| `lockedAt`, `lockedBy`, `reopenedAt`, `reopenedBy`, `reopenReason`, `unlockedAt`, `unlockedBy`, `unlockReason` | optional | stamps written by the lifecycle planners |

**Period state machine**

| Transition | Planner | Needs | Effect |
|---|---|---|---|
| open -> closed_reserved | `planCloseYear` | no drafts dated in the year (unless `allowDrafts`), balanced TB | snapshot taken; `revision` unchanged |
| closed_reserved -> open | `planReopenYear` | `isOwner: true`, reason | `revision + 1`, snapshot kept |
| closed_reserved -> locked | `planLockYear` | (editor) | snapshot refreshed |
| locked -> closed_reserved | `planUnlockYear` | `isOwner: true`, reason | `revision + 1` |

Posting/amending/voiding/reversing **into** a year: `open` = fine; `closed_reserved` = a non-empty reason is
mandatory and the planner adds `update fiscalYears/<y> {revision: +1}` (and `periodState` on the history item);
`locked` = refused (`period-locked`, a reason never overrides). An amendment that moves the date between years
gates and bumps both years.

### 3.10 `openItems/<n>` and `assumptions/<n>`
Keyed by the workbook item number. `openItems`: `{n, year, item, effect, docRequired, status: 'open'|'partial'|'closed'|'inquiry', linkedEntries: number[], closedDocId, closedAt, createdBy, createdAt}`.
`assumptions`: `{n, text, effect, docRequired, ifNotReceived, status: 'pending'|'met'|'rejected', linkedEntries: number[], closedDocId, closedAt}`.
`linkedEntries` hold **entry numbers**; planners add the number of an entry whose line `links` cite the item.
The `open-item-on-unknown-source` template rule creates `openItems/<max+1>`.

### 3.11 `assets/<id>` and `depRuns/<year>`
`assets`: `{id, name, acct, accumAcct, expenseAcct, cost, inServiceDate, rate, convention, residual, sourceEntryNo, active, notes}` plus optional `disposalDate`.
`rate` is a fraction per year (`0.05` = 5%; a value above 1 is read as percent). `convention` is one of
`half_year` (cost x rate x 1/2 in the first year), `day_count` (cost x rate x days/365, days counted **inclusively**
from the in-service date to 31 Dec, capped at 365), `full_next_year` (nothing in the purchase year), `full_year`,
`none` (land, work in progress). Later years charge cost x rate. Every charge is capped at `cost - residual` over the
asset's life. `depRuns/<year>`: `{year, status: 'proposed'|'posted', lines:[{assetId,name,acct,accumAcct,expenseAcct,convention,basis,charge,accumBefore,accumAfter,capped}], total, postedEntryNo}`.
A re-run replaces an unposted proposal only.

### 3.12 `reconciliations/<id>`
`{id, acct, asOf, statementBalance, bookBalance, difference, clearedKeys: string[], docId, by, at}`. Written by the reconciliation screen (not by engine planners).

### 3.13 `templates/<id>` (quick-entry data rows)
```
{ id, name, order, active,
  inputs:   [{ key, label, type: 'amount'|'number'|'rate'|'date'|'text'|'party'|'account'|'select'|'docs', required, options?, default? }],
  defaults: { cc, sector, docIds },            // 'fixed:<id>' | 'input:<key>' | null ; docIds: array | 'input:docs'
  lines:    [{ side: 'dr'|'cr', acctFrom, amountFrom?, partyFrom?, memo?, cc?, sector? }],
  descPattern: 'صرف[ {ref}][ — {payee}]',      // {key} placeholders; [...] groups vanish when a placeholder inside is empty
  rule: null | 'cash-funding-evidence' | 'open-item-on-unknown-source',  ruleOptions?: {...} }
```
`acctFrom`: `fixed:1320`, `input:<key>`, `party.defaultAccount`, `party.accrualAccount`. `amountFrom`: `input:amount` (default) or a
product/quotient evaluated **exactly** in decimals: `input:monthly*input:months`, `input:cost*input:rate*input:days/365`.
`partyFrom`: `input:<key>`, `fixed:<partyId>`, `none` (default: the template's party input, if any).
Reserved input keys needing no declaration: `date` (always required), `desc`, `docIds`, `cc`, `sector`.
`defaultTemplates()` returns the five launch rows. Rules (`builtinRules`):
* `cash-funding-evidence` - input `evidence` (`bank`|`treasury`|`none`); anything but bank/treasury reroutes the credit on a funding account to the party's **accrual** account (precedence: `ruleOptions.accrualAccountOf`, then `config.rules.accrualAccountOf`, then `party.accrualAccount`, then `ruleOptions.accrualAcct`) and flags the line for review.
* `open-item-on-unknown-source` - books the deposit and returns a `set openItems/<n>` write; the credit line gets `links:[{t:'o', n}]` and a review flag. The planners patch the new doc's `linkedEntries` with the entry number.

### 3.14 `audit/<yyyy-mm>`
`{events: [{at, by, kind, coll, id, reason, summary}]}`; read-modify-write append by the repo, rolled to `-b`, `-c` past ~180 KiB.
`kind` values the engine emits: `post, amend, void, reverse, draft-delete, close, reopen, lock, unlock, depreciation-propose, depreciation-post`.
Page-written and best-effort, **not tamper-proof**; the UI says so («سجل التعديلات»).

### 3.15 `registers/<name>` and `importRuns/<id>`
Read-only aggregated registers (`legalExpenses, fundingEvidence, payrollExposure, contingentClaims, fundingAllocation, accountantReconciliation, settlementCreditors, workbookNotes`), each `{items:[...], source:{sheet,title}}`; and import run logs `{at, by, fileSha256, counts, warnings, differences}`. The engine does not read them.

## 4. Invariants and where they are enforced

Every invariant is enforced when writing (engine planners) **and** re-checked by `checkIntegrity(state)`, which
returns `[{severity: 'error'|'warn'|'info', code, msg, where}]`.

| # | Invariant | Write-time | Integrity code(s) |
|---|---|---|---|
| 1 | Posted entry balanced, >= 2 lines | `validateEntry` | `entry-unbalanced`, `entry-few-lines` |
| 2 | Lines one-sided, positive, <= 2 decimals | `validateEntry` | `line-bad-amount` |
| 3 | Entry numbers unique, present, never reused, id matches number | `planPost` | `entry-no-duplicate`, `entry-no-missing`, `entry-id-mismatch` |
| 4 | Counter ahead of the maximum | repo | `counter-behind`, `counter-invalid` |
| 5 | Line account exists, is postable (and active for new/edited lines) | `validateEntry` | `line-unknown-account`, `line-nonpostable-account`, `line-inactive-account` (info) |
| 6 | Posting needs document, cost center, sector | `validateEntry` | (legacy data was all complete) |
| 7 | Party on `required` accounts for new/edited lines | `validateEntry` | (legacy exceptions are flagged, not errors) |
| 8 | Period state respected, reason for `closed_reserved`, locked refuses | `periodGate` | `locked-year-changed`, `locked-year-entry-edited`, `locked-year-revision-changed`, `locked-no-snapshot`, `year-state-invalid` |
| 9 | Trial balance debit = credit; assets = liabilities + suspense + equity | derived | `tb-unbalanced`, `bs-unbalanced` |
| 10 | `everUsed` consistent with usage | planners | `account-everused-false`, `account-everused-unused` |
| 11 | References resolve (party, document, cost center, sector, register links) | `validateEntry` | `orphan-party`, `orphan-doc`, `orphan-cc`, `orphan-sector`, `orphan-link`, `party-merged-not-repointed` |
| 12 | Version matches history; void has a reason; reversal target exists | amend planners | `version-history-mismatch`, `void-no-reason`, `reversal-orphan` |
| 13 | Drafts older than 7 days | - | `draft-stale` |
| 14 | Identical posted entries | warning in `validateEntry` | `possible-duplicate` |
| 15 | Suspense settled; wrong-side balances | - | `suspense-nonzero` (warn), `wrong-side-balance` (info) |

Also reported: account class/type/fsLine consistency, party merge chains, asset and depreciation-run references,
register status vocabularies, unknown template rules, and (informational) closed-year differences from the snapshot and
changes since close.

## 5. Reports

All reports read **posted lines only** (drafts via `includeDrafts`), `void` never. There are **no closing entries**:
P&L accounts keep accumulating, so a year-mode trial balance's opening column carries the P&L of prior years.

* `balances({state, from, to, filters})` is the primitive: opening = lines dated before `from`, movement within `[from, to]`.
  Filters: `costCenter(s)`, `sector(s)`, `party/parties` (merges resolved), `accounts`, `includeFiduciary` (default `true`).
* Balance sheet at date D: `assets (ASSET) - accumulated depreciation (ACCUM_DEP)`; liabilities; suspense on its own line;
  equity = `CAPITAL + CAPITAL_CALLED (debit, negative) + SETTLEMENT_SHARES + RETAINED accounts + derived prior-year results
  (all P&L lines before 1 Jan of year(D)) + current-year result`. `check = {assets, liabilities, suspense, equity, difference, balanced}`;
  unclassified accounts show up as a non-zero difference. Wrong-side balances are kept and listed in `wrongSide`.
* Party views: **by line party** (parties plus unassigned always add up to the account total) and **by account binding**
  (`party.boundAccounts` / `defaultAccount`: the whole account balance whatever the line party).

## 6. The plan / write contract

Engine planners are **pure**: `(state, params) -> plan`. `src/data/repo.js` applies plans; it is the only writer.

```
Plan = {
  ok: boolean,
  writes: [ {op:'set',    path:'entries/e000312', data:{...}},     // full replace (creates if absent)
            {op:'update', path:'accounts/1310',   data:{...}},     // merge; the doc must exist; arrays are replaced
            {op:'delete', path:'entries/d_x_y'} ],                 // idempotent
  audit: {kind, coll, id, reason?, summary} | null,
  entryNo?: integer,        // ONLY plans that create a numbered entry
  errors: [{code, msg, line?, key?}],     // [] when ok; `writes` is [] when not ok
  ...extras                  // id, entry, validation, warnings, checklist, snapshot, proposal
}
```

Rules:

1. **Order.** The primary doc comes first, dependent writes next (draft deletion, `everUsed`, revision bumps, register
   `linkedEntries`), caller `extraWrites` last. The repo applies them sequentially; there are no transactions, so a
   failure part-way leaves a prefix applied (the repo reports `applied/total`). Every state a prefix can leave is
   detectable by `checkIntegrity` (orphan links, `everUsed`, counter). To finish an interrupted plan, **re-apply the same
   plan** (same `no`): `set`/`delete` are idempotent and the `update`s only set flags or arrays computed from the plan; do
   not re-plan with a new number, which would post the entry twice.
2. **Numbering handshake.** Numbered plans (`planPost`, `planReverse`, `planPostDepreciation`, `applyTemplate(mode:'post')`)
   take `no` from the caller. The repo's `postWithNumber(no => plan)` acquires the lease on `meta/counters`, computes the
   next number (max of counter and fresh max + 1), builds the plan with `no`, checks that `entries/e<no>` is free, applies
   the writes, **bumps the counter itself** and releases the lease. Without `no`, planners use `max(posted/void no) + 1`
   of the given state (tests, previews like «تلقائي»). Plans refuse a taken or invalid number (`number-collision`, `number-invalid`).
   Amend and void plans have **no** `entryNo` (the repo must not lease for them).
3. **Optimistic concurrency.** `planAmend`/`planVoid` need `expectedVersion` (the version the editor loaded) and compare
   it with the stored doc: the repo must re-read the entry right before planning. Mismatch -> `version-conflict`.
   Year-lifecycle writes are last-writer-wins.
4. **Reasons.** Amend, void, reverse, reopen and unlock require a non-empty reason; posting into a `closed_reserved`
   year does too. Reasons go to the history item and to the audit event.
5. **Audit.** The repo appends `plan.audit` after the writes (best effort). Drafts are not audited (autosave noise) except deletion.
6. **Extra writes.** `extraWrites` (e.g. the `openItems` doc from a template rule) are cloned, appended after the entry
   writes, and their `linkedEntries` are patched with the new entry number.
7. **Validation output** accompanies plans as `plan.validation` (`{ok, errors, warnings, lines, totals, balanced, year, periodState, suggestedFlags}`);
   `suggestedFlags` are already applied to the written lines (`needsReview`/`reviewReason`).

Example (post an entry; ids and amounts invented):
```json
{ "ok": true, "id": "e000036", "entryNo": 36,
  "writes": [
    {"op":"set","path":"entries/e000036","data":{"no":36,"date":"2023-12-01","fy":2023,"status":"posted","version":1,"history":[],"lines":[ "..." ]}},
    {"op":"update","path":"accounts/1310","data":{"everUsed":true}} ],
  "audit": {"kind":"post","coll":"entries","id":"e000036","reason":"","summary":"ترحيل القيد رقم 36 — ..."},
  "errors": [] }
```

## 7. Validation messages

Per-line status chips (`validateEntry(...).lines[i]`): `{n, status, chip, ok, missing, errors, warnings, needsReview}`.

| `status` | chip text |
|---|---|
| `ok` | سليم |
| `incomplete` | ناقص — لا يُرحَّل: ينقص رقم المستند / مركز التكلفة / القطاع القانوني (`missing` lists `doc`/`cc`/`sector`) |
| `noamount` | بلا مبلغ — أدخل مدين أو دائن |
| `both` | السطر يحمل مدين ودائن معاً — اختر جانباً واحداً |
| `unknown` | كود غير موجود |
| `party`, `nonpostable`, `inactive`, `badamount`, `badref` | engine-owned Arabic text |

Entry-level: `القيد غير متوازن — الفرق 1,250.00 (المدين أكبر|الدائن أكبر)`; period: `السنة 2022 مقفلة — اطلب إعادة فتحها مع ذكر السبب`
(closed with reservations and no reason) or a locked-year message. Error codes: `date-invalid, period-locked, period-closed, lines-min,
unbalanced, account-unknown, account-nonpostable, account-inactive, amount-both|zero|negative|invalid|decimals, dim-missing,
party-required, party-unknown, doc-unknown, cc-unknown, sector-unknown`. Warning codes: `period-reserved, before-incorporation,
sector-shared, possible-duplicate, funding-no-evidence, fiduciary-imbalance, party-recommended, party-required-legacy, party-merged,
account-inactive, cc-inactive, sector-inactive`.

## 8. Additions to the build-spec schema (all optional, additive)

`meta/config.rules`; `parties.boundAccounts`, `parties.accrualAccount`; `assets.disposalDate`; `fiscalYears.snapshot.netResult`,
`fiscalYears.snapshot.revision` and the lifecycle stamps; `history[].periodState`; `depRuns.total` and per-line `basis`;
`openItems`/`assumptions` field names above. Nothing in the spec schema was removed or renamed.
