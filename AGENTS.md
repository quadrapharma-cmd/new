# AGENTS.md — نظام ستريفا المحاسبي

Single-page accounting system (Preact 10 + JSX, plain CSS) published as ONE `index.html` claude.ai Artifact. Data lives
in the artifact `db` capability (no server). Arabic RTL UI, Node 22 for tests, no framework beyond Preact.

## Commands

| Command | What it does |
|---|---|
| `npm install` | Install pinned dependencies (preact, xlsx 0.18.5, esbuild, playwright-core). Never `playwright install`. |
| `npm run build` | Bundle `src/` to one IIFE, inline CSS + JS into `src/index.html.tpl`, write `dist/index.html`, print the size, fail above 12 MB or on a forbidden pattern (see below). |
| `npm test` | `node --test` over `tests/**/*.test.js` and `dev/tests/**/*.test.js` (passes when there are none). |
| `npm run dev` | Serve `dist/index.html` with the in-memory mock runtime on :5173 (`-- --port 5200`, `--watch` rebuilds on change, `--private` loads the private seed). Gallery of every kit component: `/__gallery`. |
| `npm run shoot` | Playwright screenshots of the built page (1280 and 400 wide, light and dark, mock runtime, synthetic data) into `.local/shots/` plus `report.json` with horizontal overflow, console errors and contrast failures. Options: `-- --routes dashboard,system --quick`. |
| `npm run uicheck` | Keyboard/interaction checks (pickers, modal focus trap, confirm-with-reason, Arabic digit inputs, theme/year persistence, router, drawer, read-only and db-less states). Needs a build first. |

Mock query flags (dev server only): `?ro=1` read-only viewer, `?nodb=1` db unavailable, `?nouser=1`, `?empty=1` empty db,
`?dirty=1` deliberately broken books, `?seed=private`, `?latency=200`.

## Layout and ownership

```
src/index.html.tpl      <title>, <style>, <link> Google Fonts, #root, <script>  (build inlines CSS + JS)
src/styles/             tokens.css (light, bare :root) + dark.css (dark values, assembled by the build into the two
                        dark blocks) + base/layout/components/screens.css
src/lib/                money.js dates.js (engine owner) · ids.js digits.js format.js i18n.js (shell owner)
src/data/               schema.js runtime.js store.js repo.js
src/engine/             pure accounting logic (engine owner)
src/ui/                 main.jsx app.jsx routes.js context.js hooks.js prefs.js engine.js integrity-state.js ErrorBoundary.jsx
src/ui/kit/             shared components (barrel: kit/index.js)
src/ui/screens/<id>/    one folder per screen, one owner each; index.jsx exports { id, title, nav:{group,order}, component }
dev/                    mock-runtime.js, mock-install.js, synthetic-seed.js, load-seed.js, serve.mjs, shoot.mjs, uicheck.mjs, gallery.jsx, tests/
scripts/                build.mjs, test.mjs
```

## Never do (breaks the published page, often silently)

- No `alert()`, `confirm()`, `prompt()`: use `confirmAsync()` / `ConfirmDialog` / `toast`. No `window.print()`.
- No `<a download>`, blob/data download links, `mailto:`/`tel:`. Files leave only through `runtime.downloads.save({filename, data})`
  (allowed extensions: xlsx csv json html pdf txt ...). Uploads only through `repo.uploadAsset(file)` (writers only, 20 MiB).
- No external fetch/XHR/WebSocket, no service worker, no `eval` / `new Function`. External resources: Google Fonts only
  (the template already links them). Everything else is bundled and inlined. SheetJS may be imported lazily (`await import('xlsx')`); it is inlined anyway.
- No literal colours in component CSS or JSX: use tokens (`var(--accent)` ...). Every token is defined on bare `:root`, dark values in `src/styles/dark.css`.
- Never store secrets or user names/emails in the db (store the opaque user id only). `localStorage` only for per-viewer
  conveniences, always through `src/ui/prefs.js` (try/catch).
- Every form control needs a stable `id` (kit components generate one; pass your own when the control is a fixed part of a screen).
- No horizontal page scroll at 400 px: wide tables go in `DataTable` (its wrapper scrolls). Keep a side gutter of at least 16 px.
- No `git add -A`, no commits of `dist/`, `node_modules/`, `.local/`; the lead commits after each phase.
- Do not write to the db from components directly: build a plan with the engine and call `repo.applyPlan(plan)` /
  `repo.postWithNumber(no => plan)`.

The build lint (`scripts/build.mjs`) and `dev/tests/build.test.js` enforce most of the list above.

## Privacy rule

No real company data anywhere in the repo: no real balances, amounts, people, documents, tax or register numbers in code,
tests, fixtures, docs, comments or commit messages. Allowed: chart of accounts, cost-centre and sector names, template names, UI
strings. Real data lives only in the user's artifact db and in `/home/user/.strifa-private/`. Dev data is SYNTHETIC
(`dev/synthetic-seed.js`, `tests/synthetic/`): invent names and amounts. `dev/load-seed.js` reads the private seed only when
`STRIFA_SEED_DIR` (default `/home/user/.strifa-private/seed`) exists and the dev server was started with `--private`.
`python3 tools/privacy/scan.py` is the gate before any push.

## Working with the data layer

```js
const { runtime, store, repo, year, canEdit } = useApp();      // src/ui/hooks.js
const state = useStoreState();                                  // engine-state shape, re-renders on change
state.entries['e000312'];                                       // docs are frozen: clone (deepClone) before editing

// every write is a plan produced by a pure engine function
const res = await repo.postWithNumber((no) => planPost(store.getState(), { id: draftId, no, user: runtime.user.id }));
await repo.applyPlan(planAmend(await freshState(), {...}));     // re-read with repo.readDoc(path) before amend/void
try { ... } catch (e) { toast.error(e.message); }               // RepoError messages are Arabic and user-ready
```

- `repo` refuses writes for read-only viewers (`RepoError code 'read_only'`), refuses plans with `ok:false` (`'plan_rejected'`,
  engine message), and reports partial application (`e.applied / e.total`). Re-apply the SAME plan to finish an interrupted one.
- Numbering: only through `repo.postWithNumber` / `repo.allocateEntryNo` (lease on `meta/counters`, gap-free, never double-issued).
- Sequential ids for new parties/documents: `await repo.claimSeqId('parties', 'p', 4)` then `set` the doc.
- Gate controls with `canEdit` from `useApp()`; a viewer sees everything but cannot change anything.
- Audit events are appended by `applyPlan` from `plan.audit` (best effort, monthly doc, not tamper-proof).

## Adding or replacing a screen

Edit `src/ui/screens/<id>/index.jsx` (keep the exports `id, title, nav, component`; optional `path` and `aliases` for extra
hash tokens, e.g. `entry-new`). Tokens are plain (`#entries`, `#reports-tb`: the `reports-` prefix routes to the reports screen, the
component receives `route.sub = 'tb'`). Use the kit (`src/ui/kit/index.js`), strings from `src/lib/i18n.js` (add new ones there),
and verify with `npm run build && npm run shoot -- --routes <token>` before reporting done.

## Pointers

- `docs/DATA_MODEL.md` schema and plan/write contract; `docs/STATE.md` progress ledger; `docs/CHANGELOG.ar.md` Arabic changelog.
- Build spec, engine/UX/report/migration designs: the lead's scratchpad (`BUILD_SPEC_V2.md`, `design_*.md`); `docs/PLAN.ar.md` is local and untracked.
- Publish: `dist/index.html` is the page content only (no doctype/html/head/body). Capabilities at publish:
  `{db:{rules:[{path:"",read:"interact",write:"admin"}]}, user:{scopes:["profile"]}, downloads:true, assets:{}}`.
