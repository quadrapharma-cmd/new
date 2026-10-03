# tools/seed — workbook to seed, oracle and batches

Code only. These tools read the company workbook and write **private** files; nothing they produce may enter this
repository (the tools refuse to write inside it). Tests use an invented workbook (`make_synthetic_workbook.py`).

Requirements: Python 3.11 with `openpyxl` and `pandas`; Node 22 only for the optional `engine_check.mjs`.
Set `PYTHONDONTWRITEBYTECODE=1` to keep `__pycache__` out of the tree.

## Run order

```bash
python3 tools/seed/make_seed.py       # 1. workbook -> <private>/seed/<collection>/<doc id>.json (+ <private>/review/*.csv)
python3 tools/seed/make_oracle.py     # 2. workbook -> <private>/oracle.json (independent of the seed) + PASS/FAIL self-check
python3 tools/seed/verify_seed.py     # 3. gate: replays the SEED and compares it with the oracle (PASS/FAIL, counts only)
python3 tools/seed/make_batches.py    # 4. seed -> <private>/batches/batch_NNN.json + index.json (<= 50 writes per batch)
node    tools/seed/engine_check.mjs   # optional: loads the seed into src/engine and compares with the oracle
python3 -m unittest discover -s tests/seed -v     # unit tests on the synthetic workbook
```

| Setting | Default | Meaning |
|---|---|---|
| `STRIFA_REAL_XLSX` / `--xlsx` | the single `*.xlsx` under `/root/.claude/uploads/*/` | workbook (read-only) |
| `STRIFA_PRIVATE_DIR` / `--out` | `/home/user/.strifa-private` | private output root (never inside the repo) |
| `--imported-at` | the workbook's modified stamp | `meta/config.baseline.importedAt` and the stamps on legacy entries; the default keeps output byte-identical between runs, pass the real paste time if you prefer |
| `--overrides` | `<private>/config/party_overrides.json` | private party decisions (below) |

`make_seed.py` rebuilds `<private>/seed` from scratch every run (stale files disappear). Output is deterministic: sorted
keys, stable ids, no wall-clock stamps; the same workbook always gives the same bytes. Every document is checked to be
at most 200 KiB. Exit codes: 0 ok, 1 check failed, 2 input problem (the message never contains names or amounts).

## Private files

```
<private>/seed/<collection>/<id>.json      one file per db document (meta/config, meta/counters, meta/groups, accounts/<code>,
                                           costCenters, sectors, parties, documents, entries/e000312, fiscalYears/<year>,
                                           openItems/<n>, assumptions/<n>, assets/<id>, templates/<id>, registers/<name>, importRuns/<id>)
<private>/review/party_alias_review.csv    raw,lines,years,top_accounts,proposed_party,kind,confidence,identity_sensitive
<private>/review/funding_account_owners.csv  account -> owner party (how it was found)
<private>/review/crossref_proposed.csv     lines with parsed "افتراض N" / "بند N" links (all start as needing review)
<private>/review/asset_additions_seed.csv  the asset register that was built (originals, inferred additions, balance rows)
<private>/config/party_overrides.json      optional decisions the text alone cannot give (see below)
<private>/oracle.json                      acceptance numbers
<private>/batches/batch_NNN.json           {"writes":[{"op":"set","collection","doc_id","file_path"}]}  + index.json
```

### party_overrides.json (all keys optional)

```json
{ "merge":         [["spelling a", "spelling b"]],   // force into one party
  "separate":      [["spelling a", "spelling b"]],   // never merge (cannot-link; also flagged identity_sensitive)
  "null_parties":  ["role word or document type typed in the party column"],
  "group_parties": ["a string naming a group of people"],
  "kinds":         {"spelling": "supplier"},          // shareholder|financier|supplier|employee|government|bank|customer|professional|group|other
  "owners":        {"2310": "spelling"} }             // force the owner party of a funding/payroll/share account
```

Generic rules in code (`parties.py`): placeholders and trade words become *no party* (the text stays in `line.legacy`);
group words become `kind: group`; spellings merge automatically only when the normalised name is identical (titles,
qualifiers in brackets, article, "بنك"/"شركة" removed) or one name has at least two tokens and is contained in the other
with the same title. Anything looser (a lone first name, a shared surname, a shared token) stays separate and is flagged
`identity_sensitive=1` in the CSV. Lines on funding / payroll accounts typed with a placeholder take the account owner as
their party (owner = the party whose full name appears in the account name).

## What the seed contains (default decisions)

* **Accounts**: all chart accounts, codes unchanged, notes moved out of names, `type/normal/contra/contraOf/fsLine/parent/
  postable/active/partyRule/everUsed`. Active only if used or on the allow-list in `make_seed.py` (`ACTIVE_ALLOW`: retained
  earnings anchors, settlement liability, payroll tax and insurance, licence amortisation, inventory provision); a note that
  starts with "مغلق" keeps the account inactive. Sections (level 1) and 2-digit groups (level 2) come from the codes into `meta/groups`.
* **Entries**: one posted legacy entry per workbook entry number; lines in Excel row order; header date = most common line
  date (ties: latest), a line on another date keeps it in `valueDate`; header document / cost centre / sector = most common
  value, a differing line overrides. Each line keeps `legacy: {partyText, docText, row}`.
* **Review flags** (`needsReview` + `reviewReason`): parsed assumption / open-item links (contract clauses like "البند 2-7" and
  counts like "41 بنداً" are not links), any text with "استفسار", entries dated before incorporation (linked to the open item
  that cites that date when exactly one does), identical entries (possible duplicate, never merged), lines on a party-required
  account without a party.
* **Fiscal years**: from the close-status sheet; closed years are `closed_reserved` with the reservation text, sources, not-recorded,
  last update, needed documents and a baseline `snapshot` (cumulative trial balance at 31 Dec) so "changed since close" works.
* **Assets**: originals from the assets sheet, additions inferred from the depreciation wording ("cost × rate% × fraction"), one
  row per year for non-depreciating balances (licences, work in progress), and a negative-cost row for any credit on a cost
  account, so register cost equals ledger cost at every year end. Posted depreciation is never corrected.
* **Registers** (`registers/<name>`, values only, `{items, source}` plus extras): settlementCreditors, contingentClaims,
  financierFunding, legalExpenses, payrollExposure, accountantReconciliation, fundingAllocation, fundingEvidence (grades
  normalised to A/B/C, status included/after_close/excluded), cashSourcesUses, workbookNotes (all narrative text).

## oracle.json (keys)

`meta`, `years[y]` (debit, credit, netResult, assetsGross, accumDep, netAssets, liabilities, suspense, equity, equityParts,
tbCumulative, openingGross, balanceCheck), `accounts[code][y]` (openGrossDr/Cr as sheet 3 shows them = gross prior-year debits
and credits, openDr/Cr = netted, movDr/Cr, closeDr/Cr), `reports[y]` (incomeStatement, balanceSheet, trialBalance: replay and the
workbook's cached figures side by side), `partyBalances`, `cashChange`, `legalExpenses`, `payroll`, `settlementShares`,
`allocation` (price per share, total shares, ownership), `evidence`, `depreciationPosted[y]` (by accumulated account), `assetsSheet`,
`counts` (incl. `seedDerived` for parties after merge and the asset register), `selfCheck`. Money is in pounds with 2 decimals.

## Tests

`tests/seed/test_seed.py` builds an invented workbook (fictional company and people, same 21-sheet layout) and checks schema
fields, balanced entries, derived hierarchy, link parsing, party rules, asset inference and its replay against posted
depreciation, determinism (also across `PYTHONHASHSEED`), batches, the oracle self-check (and that it detects a wrong cached
figure), size and location guards, and that `templates_seed.py` still equals `defaultTemplates()` in `src/engine/templates.js`.
