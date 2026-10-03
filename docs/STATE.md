# STATE — progress ledger

Updated by each engineer when a task finishes. Newest first. No real company data here.

## Phase 1 — foundation

| Task | Owner | Status | Notes |
|---|---|---|---|
| F1 shell, build, runtime, data layer, UI kit | F1 | done | see below |
| F2 money/dates libs and engine | F2 | in progress | `src/engine/*`, `tests/engine/*` |
| F3 seed tooling, privacy scan, synthetic fixtures | F3 | in progress | `tools/`, `tests/synthetic/` |

### F1 delivered

- npm project, exact pins, `package-lock.json`; scripts: build, test, dev, shoot, uicheck.
- `scripts/build.mjs`: IIFE bundle, CSS + JS inlined into `src/index.html.tpl`, `</script` and `<!--` escaped, size printed, 12 MB cap,
  source lint for platform-forbidden patterns. If `src/lib/money.js` / `dates.js` were missing the build falls back to `dev/stubs/` (not used any more).
- Design system (`src/styles`): paper-and-ink neutrals leaning green, one accent (ink blue), separate good/warning/critical,
  tokens on bare `:root` + dark values assembled into both dark blocks, tabular figures, RTL, sticky safe-area header, reduced motion.
- Data layer: `runtime.js` (null-safe wrappers), `store.js` (17 subscriptions, one per collection, engine-state shape, ready/error status,
  batched change events), `repo.js` (`applyPlan`, `postWithNumber`, `allocateEntryNo`, `appendAudit` with `-b` roll, `claimSeqId`, `readDoc`,
  `uploadAsset`, Arabic `RepoError`s), `schema.js`.
- UI kit (`src/ui/kit`): Button, IconButton, Field, TextInput, Textarea, NumberInput, DateInput, Select, Checkbox, Tabs, Modal, ConfirmDialog
  (+ `confirmAsync`), Toast, Pill/Badge, Banner, EmptyState, Spinner, DataTable, Money, Combobox, AccountPicker, PartyPicker, DocPicker,
  YearSelect, PeriodBanner, PageHead.
- Shell: header, year selector, theme toggle (persisted), read-only badge and banner, side nav / phone drawer, hash router, error boundary,
  db-unavailable state, integrity banner, `unhandledrejection` toast.
- Screens: real `system` and minimal `dashboard`; stubs for entries, entry-form, reports, parties, documents, registers, assets,
  reconciliation, close, import, audit, settings.
- Dev: `dev/mock-runtime.js` (db/user/downloads/assets contracts), synthetic seed, dev server, screenshots, kit gallery, interaction checks.
- Tests: `dev/tests/*` (libs, mock runtime, store/repo, engine integration, rank, build contract).

### Open items for later phases

- Screens still to build: dashboard (full), entries, entry-form, reports, parties, documents, registers, assets, reconciliation,
  close, import, audit, settings (stubs exist).
- Backup button (`downloads.save` of JSON + Excel pack) and the Excel/HTML export helpers are not built yet.
- `load-seed.js` expects the private seed layout documented in its header; adjust when the seed generator's layout is final.
