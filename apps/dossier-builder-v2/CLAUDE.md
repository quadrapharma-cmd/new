# Dossier Builder v2 — the operator's handbook

You are the **operator** of Dossier Builder v2 (this folder). You run the program, its operations and its code for its owner,
**Dr. Haytham Dweedar**: you answer his questions about it, change it when he asks, keep its knowledge current, publish the
library, and tell him plainly what you did and what you found. Read this file at the start of every conversation and keep to it.

## The owner
- He writes in Egyptian Arabic: **answer in Egyptian Arabic**, direct and action-first — what you did, what it gives him, what is
  left. No preamble, no internal jargon; the trade's own terms (CTD, eCTD, PAC, CEP) stay as they are.
- He builds the program **part by part**: a part is built, tested and shown working, and the next starts only when he gives it.
  Never start a new part on your own; propose it and wait.
- He checks results himself. Never say something works before you have tested it the way he will use it (the artifact on
  claude.ai, the desktop zip). Report failures plainly, with the cause and the fix.
- When he says something does not work, reproduce it first, find the cause, fix it, test it, then answer. (His «ما فيش ولا ملف بي دي
  اف فتح» was real: the open buttons did not exist yet.)
- When a choice is truly his (scope, what to add to the knowledge, a new host on the network, anything published), ask in one short
  question with your recommendation first. Otherwise decide and say what you decided.

## The repository
| Path | What |
|---|---|
| `apps/dossier-builder-v2/` | This program. Your workspace. |
| `apps/dossier-builder/` | The old program (v1, **eBOX** since 16/11 — «منشئ ملفات التسجيل» before; private artifact https://claude.ai/artifact/RaqU6QLkLmcANCSVsPXjNR). **The program again since 15/11** (rule 11): new pieces go into it one at a time, each tried on his real files first. Its own README and tests (`python3 -m pytest -q apps/dossier-builder/tests`); build `python3 apps/dossier-builder/web/build.py`. |
| `docs/ctd/sources/` | The copies of the official documents the knowledge cites, and `MANIFEST.json` (file, sha256, size, taken) — the build refuses a copy that differs from its entry. |
| root `CLAUDE.md` | About **Drugbox**, a different program in the same repository. Do not work on Drugbox unless he asks. |

The repository's default branch is `claude/new-session-8nmyo7`; the work lives there. Pull before you start, commit and push every
change (the stop hook checks that nothing is left uncommitted or unpushed).

## What exists — Part 1 (done, tested, shown to him)
| # | Part | Where |
|---|---|---|
| 1a | **The knowledge in code**: 9 authorities, 120 sources (60 with a copy kept), 349 requirements (EDA M1–M5, ICH M2–M5, EU, GCC, US and a general M1), 226 EDA review questions, 90 EDA variations, 21 document types with their validity, 11 countries, 8 eCTD tables. Every record rests on a registered source. | `knowledge/`, `core/` |
| 1b | **The library**: browse and search everything in Arabic and English, in the browser (claude.ai artifact) and on the desktop (offline zip); every citation opens its source document at its page; one search box looks through the knowledge and inside the documents' text (Arabic finds English: `knowledge/vocab/glossary.yaml`). | `library/`, `core/search.js` |
| 1c | **Every record checked against its source**: quotes word for word, places (sections, pages, annexes) exist, CTD numbers exist, each variation's class read from the guideline. Last run (14/11, after Persian ی ک ہ fold as Arabic): verified 413 · located 736 · nothing-to-check 103 · no-copy 276; nothing `partly` or `not-found` (the tests fail on those). EDA's sources checked on EDA's website on 14/11/2026. | `tools/verify-sources.mjs`, `knowledge/checks/` |

## The Operator panel (in progress; asked for on 14/11/2026 — see docs/PART-2-PLAN.md §3.8, the same request)
A fixed part of the program, on every page: the «المشغّل» button opens a conversation with the operator (a Claude Code session
with this handbook). `operator/panel.js` (the panel), `operator/session.js` (connector, tools, transcript reader),
`operator/brief.md` (the standing instruction each operator session is opened with), `operator/panel.css`; tests in
`tests/operator.test.mjs`.
- **claude.ai edition** (step 1, built): the page declares the `mcp` capability for the viewer's «Claude Code Remote» connector,
  tools `list_environments, create_session, send_message, list_events, get_session`. The first message opens a session on this
  repository and branch in the environment «quadrapharma new» (tag `dossier-builder-operator`), later ones go to it by
  `send_message`, replies are read with `list_events`. Runs on the viewer's own claude.ai account. When publishing the
  artifact, pass `capabilities: {mcp: {servers: [{server: "Claude Code Remote", tools: [those five]}]}}` on a full redeclare,
  or omit `capabilities` to keep it.
- **desktop edition** (step 2, not built, to settle with him): either inside the Claude desktop app (the same page, plus a
  Desktop Extension bridge — on his subscription, as PART-2-PLAN §3.8 proposes) or a standalone program on an API key. The panel
  calls `window.DBK_OPERATOR` when a host program provides one. Anthropic does not allow a third-party program to sign in with a
  claude.ai subscription without its approval (Agent SDK docs).

`knowledge/README.md` holds the record shape, the review results and the rules the build enforces — read it before editing knowledge.

## Commands (in `apps/dossier-builder-v2`)
```
npm ci                 # once per fresh container
npm run verify         # reads every kept source into dist/texts/ and checks every citation → knowledge/checks/citations.json
npm run build          # checks the knowledge; writes dist/knowledge.json, dist/library/ (+ dist/Dossier-Builder-Library.zip),
                       # dist/library-artifact.html and dist/artifact-files.json
npm test               # the knowledge, the EDA website check (offline) and the library in a real browser (Playwright)
npm run check:eda      # EDA's website: is each EDA source still the copy EDA publishes? what is new since the last check?
                       # (-- --save keeps this reading as the baseline and dates the sources still published)
node tools/find-in-source.mjs <source-id> <regex> [context]    # where words sit in a kept source
node tools/compare-variations.mjs                               # the guideline items beside each variation (helper)
```
Order matters: `verify` before `build` (the library's search reads `dist/texts/`). The tests run a quiet build that removes the zip,
so run `npm run build` again before sending it. `dist/` is not committed; it is rebuilt from the repository.

## Routine operations
### 1. Check EDA's website (weekly, or when he asks)
1. `npm run check:eda` (about a minute; reads ~18 department pages and ~260 documents).
2. All sources still published and nothing relevant new: tell him in one line, then `npm run check:eda -- --save`, commit and push
   `knowledge/checks/eda-site.json` (and `knowledge/sources.yaml` if dates moved), rebuild and republish only if he should see it.
3. A source no longer at its address, or a new document that looks like a new version of one we cite: download it to the
   scratchpad with curl, read its cover (code, version, issue and effective dates). If it is a new version, follow operation 2.
4. New documents we do not cite: list the ones that bear on registration, variations, CTD/eCTD, quality, BE, stability, labelling,
   pricing or import, with one line each, and ask whether to add them. Add nothing unasked.
5. If the site cannot be read (network, layout), the tool says so and writes nothing: tell him, and do not invent a result.

### 2. A new version of a source
1. Keep the copy: `docs/ctd/sources/EDA_<code>_v<N>_<year>_<short-name>.pdf`, and an entry in `MANIFEST.json` (file, sha256, size,
   taken — the same shape as the others).
2. `knowledge/sources.yaml`: a new entry (`id` like `eda-gl-capp-024-v5`, code, version, title en/ar, status, url, issued,
   effective, supersedes, file, held: true, checked {on, how: cover}, latest {on, where, result: current}, aliases, and
   `numbering: true` if it sets section numbers). The old entry: `status: superseded`, `superseded_by: <new id>`, and its
   `latest.result` says what replaced it.
3. Move every citation of the old source to the new one (`grep -rn "src: <old-id>" knowledge/`), checking each place and quote in
   the new text with `find-in-source.mjs`. Section numbers move between versions (GL.CADC.002 v2→v3: 6.5→5.6, 6.6→5.7); when you
   renumber in bulk, guard against renumbering twice (6.5→5.6 then 5.6→…).
4. `npm run verify` until nothing is `partly` or `not-found`; then `npm run build` and `npm test`.
5. A finding in `knowledge/checks/findings.yaml` (what changed, which records) — the library's «Review» page shows it.
6. Commit, push, publish (operation 4), and tell him what changed for his files.

### 3. Correct or add knowledge
Edit the YAML (shape in `knowledge/README.md`). Every record cites a registered source with its place (`at`); `quote` only for the
source's own words, `gist` for our summary. Never let an in-force requirement rest on a draft alone. A document's kind is read from
its content, never from its file name. Then verify → build → test → commit → publish.

### 4. Publish the library (after any change he should see)
1. `npm run verify && npm run build && npm test && npm run build`.
2. **Artifact** (private, already exists): `https://claude.ai/artifact/6sSh9Tgi3jXji54PJbYcxf`. In a new conversation, first
   `Artifact` action `read` with that url; then publish with `url`, `file_path` = `apps/dossier-builder-v2/dist/library-artifact.html`
   and `files` = the entries of `dist/artifact-files.json` (published path → path in the repository). Only new or changed files are
   needed (files left out stay); at most 255 files and 64 MB per publish. The artifact serves pdf, csv, js, json, txt, md, images,
   fonts and media only — no zip, docx or xlsx (so its page opens only PDF and CSV: `window.DBK_OPEN`) — and refuses the character
   U+FFFD (the build strips it from the texts).
3. **Desktop**: send `dist/Dossier-Builder-Library.zip` with SendUserFile (display: attach) and one line: unzip, open `index.html`.
4. Check it as he will see it: Playwright (preinstalled: `require('playwright')`) on `dist/library/index.html` at 1440 and 390 wide,
   Arabic and English, light and dark; open a source document, search in Arabic and in English. Screenshots go to the scratchpad.

### 4a. Check a published page as claude.ai serves it (rule 13; before telling him it works)
Read the page back (`Artifact` action `read`, `path` `index.html` and its other files, `out_dir` a scratchpad folder; the library's
sources and texts can come from `dist/artifact-files.json`), then `node tools/check-published.mjs <library|workbench|measure> <folder>`:
Chromium under a content security policy like the artifact frame's, with `window.claude` standing in for the viewer
(`tests/helpers/fake-claude.js`, which refuses what claude.ai's `sample` contract refuses). It found the measuring page's whole-page
failure the owner met (`--old-measure` replays it). It cannot reach Claude itself, nor the Claude Code Remote connector.

### 4b. The workbench (Claude with the program's tools inside the page; step 2.0)
Private artifact `https://claude.ai/artifact/SHrw9qKsfnqTYSiXbydbwf`, capability `sample`. Rebuild with `npm run build && node
workbench/build.mjs`, test with `node --test tests/workbench.test.mjs`, then publish `dist/workbench-artifact.html` with `url` and
`files` = {`workbench/pdf.worker.min.js`: `dist/workbench/pdf.worker.min.js`}. claude.ai refuses text files holding control
characters: the build writes them as escapes (`escapeControls`). The bridge for the Claude app: `node bridge/pack.mjs` →
`dist/Dossier-Builder.mcpb` (installed from the Claude app: Settings → Extensions → Advanced settings → Install Extension).

### 4c. «الفحص الأول للملف» (Part 2's first slice, asked for with «أبدا» on 14/11/2026; published 14/11 after his «أبدا»)
Private artifact `https://claude.ai/artifact/Gm4x2sU1BYLu1y6aTewmZr`, capability `{sample: {images: true}}`. Read back after
publishing: every file byte for byte the built one; `check-published.mjs prep` (the scan reader) and `prep-claude` (Claude's reading
through the claude.ai stand-in) pass on the read-back page.
- Scanned pages (owner, 14/11: «أنا عايز. اجرب بنفسي»): Claude reads them on the viewer's account where the view lets the page ask it
  with pictures (`prep/claude-read.js`: each page in two halves of ~1.2 MP, the instruction of the owner's own measure, 97–98 %);
  the viewer can choose the scan reader instead; a page Claude cannot read goes to the scan reader, and after a refusal or a spent
  limit every page does — the page says why. Claude's real answers are tried by the owner himself (no API key here); everything
  else is tested with the stand-in (`tests/helpers/fake-claude.js`: pages answered, not_granted, rate_limited, a failure retried).
The viewer chooses a product's files or folder; the page opens every file by its content (PDF with text, scanned PDF and pictures
through the scan reader, Word .doc and .docx, ZIP and RAR, archives inside archives), types each document and places it in the CTD
(the library's records), reads its facts by rule (each with its page and words), and checks the documents side by side: the
licence's manufacturer against the others (and a transfer approval or only fee receipts), an approved limit missing from the
specification/monograph/method, one substance in two hydrate forms (the molecular-weight sum shown), review and end dates passed,
the licence's numbered conditions. No Claude: rules only.
- Code `prep/` (read.js, zip.js, office.js, rar.js — v1's reader ported, ocr.js — the scan reader, doctype.js, facts.js, chem.js,
  checks.js, index.js, page.js, build.mjs). Needs `vendor/ocr` (`node tools/ocr/fetch.mjs`).
- Build `npm run build && node prep/build.mjs` → `dist/prep-artifact.html` (0.6 MB) + `dist/prep-files.json` (18 files, 40 MB: the
  scan reader's models and WebAssembly as gzip in base64 text, since the artifact host serves text and 16 MB a file).
- Tests `node --test tests/prep.test.mjs tests/read.test.mjs tests/prep-files.test.mjs tests/prep-browser.test.mjs` (they use `zip`,
  `rar`, `soffice` and Chromium; made-up files only). Check as published: `node tools/check-published.mjs prep <folder>`.
- The scan reader needs WebAssembly in the frame (the old program's Pyodide edition ran there); a view that forbids it is told so,
  and the files with text are still checked. Scanned pages are drawn 4,200 px long (A4 at ~360 dpi; a phone scanner's PDF claims
  28 × 42 inches, so its own size is not used). Speed here: a dense scanned page 13–48 s, two at a time on a computer with 4 cores;
  a real product's folder tried locally (13 documents, 28 scanned pages): about 6 minutes, 4 of its 5 known problems found (not
  the licence's conditions: its Arabic reads too blurred; not the receipts: a phone photo the reader cannot read).
- OCR slips the rules already take (keep adding, each with a made-up test): «Fach» for «Each», «contalns», a % read as a digit,
  «هينة» for «هيئة», «الركزية» for «المركزية», direction marks and stray signs around values.
- Republish: `file_path` `apps/dossier-builder-v2/dist/prep-artifact.html` with `url` (above) and `files` = `dist/prep-files.json`
  (its paths are from the repository's root; only changed files need sending); omit `capabilities` to keep `sample` with images.
- Real products are tried locally only (`scratchpad/trial/`), never committed or published.

### 4d. The workshop «تحضير الملف» — all of Part 2 on the computer (asked for on 14/11/2026: «عايز الجزء كامل بادواته بتعديله بتجهيزه بمخرجاته بكل حاجة عايز اجربه»; then Part 3 «تكوين الملف»)
One folder he unzips and opens (`index.html` in Chrome or Edge, file://; no server, nothing to install), the library beside it. The
eight stages of docs/PART-2-PLAN.md §3.3: a new dossier (country, application, product's case, every file or folder) → received
(fingerprints, copies known, archives opened) → read (text, Word, scans by the scan reader or by Claude) → cut, typed, named, placed
on the board → checked (each document on its place's rule card: PDF, searchable, version, protection, size, fonts, outline;
validity from its dates and its type's months; the five cross-document checks; every required empty place) → fixed (a page never
changed: saved again at a current version, an outline from its own table of contents, a picture made a page) and the company's
papers written as Word drafts (Annex I with EDA's Arabic undertaking, composition, salt with its formula, translation declaration,
CEP commitment, cover letter, tracking table, stability commitment; unknowns are marked gaps) → «needs you» (place a document,
confirm a cut, the missing places, a draft's gaps, each finding: open it in its program, Claude, a new version, accept with a
reason) → the ready folder (Egypt's shape, the program's own names because EDA names none for the CTD — the report says so — with
the readiness report and a checklist). «شغّل لوحدك» runs it all; «خطوة بخطوة» stops before the fixes.
- Claude: his own API key (console.anthropic.com, billed by use), typed in «الإعدادات» on his computer, never in the chat; checked by
  listing the models it may use (the SDK sends it as a Bearer token, which the API takes); the most capable family first, he can
  choose. Used for: scans as pictures (two halves, the instruction of his measure, effort low), documents the rules cannot place
  (its answer must be a place of the board), «اسأل Claude» (the workshop's tools: list_documents, read_page, find_in_documents,
  list_findings, board, search_knowledge, get_record, record_fact — words checked on the page — place_document). The key is kept in
  memory, or on the computer if he ticks «افتكر» (said: every page opened from files can read it). No key: everything but Claude.
- The programs (`vendor/craft`, built from source with `tools/craft/patches/<app>/`, each taking the ArtCraft logo and name out of
  its screens, as the brand licence asks of a modified build; copyright notices stay), each in its own page beside the workshop
  (`programs/<app>.html`; a file:// page is its own origin, so a relay there passes messages with postMessage):
  · Word and PDF programs: their «page» host mode (events on the canvas, commands: «اعمله PDF» has the Word program export a Word
    file without a person). The PDF program also carries our OCR patches.
  · Photo program (PhotoCraft) and design program (DesignCraft) have no host mode: the relay drops the file on the canvas as a
    person would (at the window's corner, so the photo program opens it rather than placing it in the open picture), knows they
    started when they take away their own «loading» note, and keeps what they save (they save by a download: a link to a blob,
    clicked) instead of letting it reach the Downloads folder. Ctrl+S in the photo program gives a PSD: `workshop/psd.js` reads its
    shown picture, `workshop/png.js` writes PNG where the browser cannot. Uses: a scanned page cleaned («نضّفها في برنامج الصور»,
    the page at 200 dpi; what comes back replaces that page, same page object — `replacePage`); a picture (made a PDF by the
    picture fix, `doc.picture` keeps its kind, `doc.psd` its layers); the pack's artwork places of each country (`DESIGN_PLACES`)
    made in the design program (its `.designcraft` is the document until File ← Export PDF…, whose PDF goes in — `doc.pdf`);
    a PDF or picture placed into an open design (`doc.design` keeps the design to reopen).
  · Every save is a new version; a new version gets the safe fixes at once (version, outline, picture to PDF, text layer).
  Rebuilt on 15/11 (`WASM_OPT_SKIP=1 node tools/craft/build.mjs <app> web`, then `node tools/craft/optimize.mjs <app>`: the
  JavaScript wasm-opt takes 15–50 min a program). PdfCraft's own web OCR is not used (English-only ocrs models, CC-BY-SA, set aside
  in the plan): the workshop makes the text layer itself (below).
- Searchable scans (`workshop/textlayer.js`, `ocr.layer()` in `prep/ocr.js`): each page without its own text is read as for the
  dossier (upright, straightened) and Tesseract writes its text-only PDF of it (GlyphLessFont, in the core); the workshop lays it
  over the page with the straightening, the turn and the page's /Rotate undone (`layerMatrix`, exact to 1e-13 pt in the tests).
  By itself up to 40 pages (`TEXT_AUTO`), on a click above (its time said).
- Reading also: Excel and PowerPoint old and new (`prep/office.js`: sheets with their dates, slides in order; BIFF8 records and
  [MS-PPT] atoms), 7z (`prep/sevenz.js` + `prep/lzma.js`, written from the public-domain LZMA SDK's spec: LZMA, LZMA2, BCJ, delta,
  copy; PPMd, encryption and split parts said, not read), IDML (its stories' words), DesignCraft and InDesign files, PSD.
- Countries (`board.js`): Egypt, the Gulf, Europe, the US and other countries all «كامل»: each its own questions (the conditions of
  its Module 1: `gcc_agency`, `eu_procedure`, `eu_legal_basis`, `us_application`, `biological_origin_materials`, `novel_excipient`
  — yes/no kept as true/false), its file rules `FORMATS[country]` each cited to page and line (the test reads every cited line in
  `dist/texts`: it caught Egypt's own rules a line off — fixed), its size limit (EG/GCC/OTHER 100 MB, EU 500, US 400) and the PDF
  version its fix writes (1.7 for EG/EU, 1.4 elsewhere, ICH's agreed version). Documents are placed by each country's own words
  (`recognitionOf` in pipeline.js; they were off outside Egypt), known types find the same place of the common modules (P-09…),
  Egypt's words serve ICH's places. Validity outside Egypt: the date written on the document (no type months in those rules).
- Code `workshop/` (expr, board, understand, pipeline, checks, fixes, generators + templates/annex1.json, docx, zipw, store, export,
  needs, claude, tools, programs, psd, png, textlayer, pdfops, desktop-assets, page, body, style, build). The page loads as classic
  scripts only: pdf.js on its own thread (`globalThis.pdfjsWorker`; close a pdf.js file through its loading task, `task.destroy()`),
  the scan reader's files as scripts handing their content to `__dbAsset`, Tesseract's worker a blob carrying its code, core and
  languages (a blob worker may import only blobs it makes itself), the ORT module from a blob.
- Build `npm run build && node workshop/build.mjs [--zip]` → `dist/workshop/` (+ `dist/Dossier-Builder-Workshop.zip`).
- Tests `node --test tests/workshop.test.mjs` (Node: the board for each case and country, every cited line, rule cards, PSD/PNG,
  kinds by content, the text layer's matrix, the made-up dossier for Egypt and the Gulf), `tests/office-7z.test.mjs` (files written
  by LibreOffice and 7-Zip — `apt-get install p7zip-full` for the 7z part) and `tests/workshop-browser.test.mjs` (Chromium from
  file://: the scan reader and the text layer, Claude through `tests/helpers/fake-api.mjs`, a wrong key against the real API, the
  four programs, a Gulf dossier). Made-up files only. `SHOTS=<dir>` keeps a screenshot when the programs' test fails.
- Dossiers are kept in the browser's IndexedDB on his computer; «احفظ نسخة» gives one file (`.dossier.zip`) that opens again.

### 5. The open-source eCTD projects and the eCTD timelines (monthly, or when he asks)
1. Last update of each project the plan uses (`docs/PART-2-PLAN.md` §3.9–3.10):
   `gh api -X GET search/repositories -f q="repo:<owner>/<name>" --jq '.items[] | "\(.full_name) \(.pushed_at) \(.license.spdx_id)"'`
   for PharmaRA/RATools-for-eCTD, randomthingsonlineatsk-cloud/{ectd-dossier-builder,labelling-workbench,variations-classifier},
   zubair0153715/ectd-lite, dayzero/ectd_indexer, cperapa-rgb/phaxton-validator, sebsca/ectd-tool, fabricanda/clinical-drafting-kit.
2. New projects: `gh api -X GET search/repositories -f q='ectd pushed:>YYYY-MM-DD'` (and «common technical document»).
3. For each change: what is new (README, release notes), its licence (MIT/Apache/BSD: code; GPL/AGPL/none: ideas only), and where it
   lands in the plan. Add it to `docs/ctd/UPDATES.md` and the plan's §3.10, then tell him in a few lines.
4. eCTD timelines (EDA, EU, FDA, GCC, eCTD 4.0) from the authorities' own pages: a change goes to the library as a finding.

## Rules that never bend
1. Every record rests on a registered source; nothing is stated that its source does not say.
2. **Company data** from his Drive (Dramrin, Wouncure, any product's files) stays in the scratchpad: never committed, published or
   uploaded anywhere without his explicit yes.
3. Artifacts stay **private**. Publish nothing new without his say.
4. Network only through the environment he approved. Never go around a block, a bot check or a safety check; if a host is blocked,
   say so and ask (adding a host goes through `update_environment`, which he approves).
5. Secrets never in the repository, the browser or the chat; a key file is mode 0600.
6. Commit and push every change; commit messages end with the trailer lines the session gives you; no model names in commits, code
   or files.
7. Test fixtures are made up — never a real company's or product's data.
8. GPL/AGPL code: ideas only, never its code. The ArtCraft name and logos are not used.
9. Desktop builds for Windows or Mac only after he approves.
10. No `rm` with wildcards; `pkill -f` only with an anchored pattern that cannot match your own command.
11. Leave Drugbox alone unless he asks. **`apps/dossier-builder/` (v1, eBOX since 16/11) is the program again since 15/11** (see «His
    decisions»): change it only for what he asks, and never so that it reads his files worse than it does now.
12. Do the work yourself, in lean turns: no sub-agents unless he asks for them.
13. **Nothing reaches him untested** (14/11/2026: «مينفعش تبعت حاجة متجربتش او لم يتم اختبارها انت كدا بتضيع وقت و جهد و فلوس»).
    Before anything is sent or published to him, see it work yourself, end to end, the way he will use it — not a stand-in that is
    easier than the real thing. What cannot be tested from here (Claude answering inside claude.ai on his account; installing on
    his Windows or Mac) is not sent until a way to test it exists; say so before you start, never after he finds it broken.
    On 14/11 the Claude-app extension and the workbench reached him untested and failed for him: that is what this rule stops.
    **Made-up files are not enough (15/11):** the workshop passed 100 tests on files written here and read his real files badly.
    Any change to how documents are read, typed, placed or checked is first run on his real files kept in the scratchpad
    (Dramrin: `trial/dramrin-folder`, with `dramrin/truth`; Wouncure: `wouncure/src`) and compared, field by field, with the old
    program on the same files; it is sent only if it reads them at least as well. Say the comparison when you send it. A reading
    written here in Claude's place (the mock of `sample` in `real_flow.py`) tests the program around the reading, never the reading:
    where Claude's reading is concerned, compare with real calls (an API key for tests, saved as an environment secret, when he
    gives one) or say plainly that it was not compared.
14. **The program speaks formal Arabic (فصحى), never Egyptian colloquial** (16/11/2026: «اللغة هتبقي عربيه فصحي مش لهجة عاميه و محتاج كل
    الاختيارات تبقي تسميه غير محيره لليوزر») — every text a person reads: pages, messages, rule-pack notes, reports. One thing has
    one name (the glossary is in the old program's README, «eBOX, stage 1»). `tests/test_formal_arabic.py` fails on a colloquial
    word. Not interface text, and never «corrected»: the words the program looks for inside his documents (`extract.py`,
    `arabic.py`, `intake_eda.py`, `classify.yaml`), the prompts, the letters' fixed wording, and his own words quoted in comments.
    The chat with him stays Egyptian Arabic.

## His decisions so far
This file is your memory beyond this conversation. When he decides something new — a rule, a preference, a decision about the
program or its knowledge — add it here (or to «Rules that never bend»), with his words where they matter, then commit and push.
When a part is done or an open item is closed, update «What exists» and «Open items» the same way.
- «الجزء المعرفي كله هتحطه في الكود و هتعمل مكتبه اليوزر لو حب يرجع ليها» → Part 1.
- «ناخد القديم ونراجعه» — the v1 knowledge was ported once (`tools/port-v1.mjs`, which refuses to run again without `--force`, so it
  never overwrites edits) and then reviewed.
- «كل الهيئات مرة واحدة» — every authority at once. «الاتنين من الأول» — the claude.ai artifact and the desktop edition from the start.
- «عايز اوبشن بحث في المكتبة عن اي معلومة» → one search over everything, Arabic and English, inside the documents too.
- The 14/11/2026 review: GL.CADC.002 version 3 is in force (its citations moved); 15 variation classes in EDA's online tool differ
  from the guideline GL.CAPP.026 v6 — the program uses the guideline's class and keeps the tool's (`pac_tool`); **confirm the 15
  with EDA before filing** (finding `variation-classes`).
- The Operator, 14/11/2026: «عايز ليك جزء منفصل و ظاهر» in the whole program, «في كل النسخ متوصل بيك», desktop for «الاتنين»
  (Windows and Mac), «اجينت جوا البرنامج بيتوصل بيك عن طريق الاكونت الشخصي لليوزر» — told him the subscription sign-in needs
  Anthropic's approval; he agreed to: claude.ai edition on the viewer's account, desktop on an API key, the same panel («أبدأ»).
- «محتاج اللي يدير البرنامج نسخة منك … يكون ليها تحكم كامل علي البرنامج و علي العمليات و علي الكود» → you.
- **Part 2 «تحضير الملف» (14/11/2026)** — the logic and plan are `docs/PART-2-PLAN.md`; his answers to its decisions:
  - desktop edition: a standalone program for Windows and Mac on an API key; the claude.ai edition on the viewer's own account;
  - «اوك» to building PdfCraft, WordCraft, PhotoCraft and DesignCraft from source (with pdf.js and our RAR reader), and
    llama.cpp to try Qwen3-VL;
  - Egypt's rule cards in full first; other countries take their Module 1 from the library, then GCC and Europe;
  - Part 2 ends at «الملف الجاهز» (the prepared dossier); eCTD is Part 3.
  The 50 eCTD updates (`docs/ctd/UPDATES.md`) each have their place in the plan's §3.10. Step 2.0 (the toolbox and the agent)
  is being built by the planning session: before you build in Part 2 yourself, pull and read the plan's progress so the two
  sessions never build the same thing at once.

- **15/11/2026, after trying the workshop on his files:** «الملفات لا تقرا لا بكلود و لا بالماسح المحلي كل اللي اتقرا اتقرا غلط»,
  «الواجهة سيئة عايز نرجع للواجهة بتاع البرنامج القديم اللي … كان بيقرا المعلومات و بيحطها في مكانها و بيشتغل شغل كويس جدا».
  Measured the same day on Dramrin's nine files: the workshop (scan reader) named the product «p DRAMRIN Casals», garbled the
  manufacturer, cut the 152-page validation file into 11 parts and put the method of analysis in the specification's place (its
  «limit of ascorbic acid 50–120 %» was right after all: EDA's appeal decision of 20/11/2025 adds it to Dramrin's finished-product
  specification — said wrongly to him on 15/11 and corrected the same day); the old program, in the 14/11 run where Claude's reading was a stand-in written
  here from the pages, filled the name, form, manufacturer, the three substances with their makers and the applicant, and placed all
  13 documents (its real reading on his account cannot run here: his own use of it is the evidence — corrected to him on 15/11).
  The live artifact (version 1794612920, 13/11 23:35 UTC) is commit 0cc4d69; `864cd3c` (14/11 00:26, the fixes that run on his real
  files found: the wizard by authority, combined files never placed whole, only true data) was never published. The cause: the old program has Claude read each document and give its
  data (on his account in the claude.ai edition); the workshop used Claude and the scan reader only for text and then rules
  written here, tuned on made-up files. Decision: back to the old program, its interface and its reading; the v2 workshop
  (`workshop/`, delivered 15/11) is frozen and not built on. New parts go into the old program one at a time, each measured on his
  real files first (rule 13). The library (Part 1) stays as it is.
- **15/11/2026, «ok» to the first two pieces in the old program** — published as version 46 of «منشئ ملفات التسجيل» (`7b9c763`…):
  the library inside it (a button, and each item opens its own record there — all 349 links checked against the library as
  published) and 7z opened in the page in every edition (the owner's Dramrin files packed as one 7z gave the same 13 documents,
  byte for byte). Built on the live version (0cc4d69, checked equal to what claude.ai served); `864cd3c` held back until it is
  compared with real Claude readings (the API key: he adds it as an environment variable; not seen by this session yet).
  Opening time unchanged (8 interleaved rounds: first 5.2 s, next 4.6 s, before and after). The whole suite: 777 passed after
  two 7z fixes it found.

- **15/11/2026, «رتبهم خطوة بخطوة و خلصهم» — the scan readers measured on his real pages before anything moved.** Eleven first pages
  of his real scans (Wouncure: final and extension licences, pack addition, conformity, price, toll contract, import approval,
  follow-up receipt; Dramrin: final licence, stability appeal decision, fee receipts), 250 facts written down by eye from the
  pages (kept in the scratchpad only), the same score as the made-up measure (`tools/measure/score.mjs`):
  Tesseract alone with the «best» models (what the old program's claude.ai edition writes as the text layer) **74 %**; the old
  program's desktop reading (its own `pdfcraft.ocr`: PdfCraft's Tesseract, PaddleOCR on the unsure words) 64 % (62 % without the
  PaddleOCR pass); the measure's copy of that way 66 %; **the new reader that scored 94 % on the made-up pages: 58 %** (it lost 29
  Arabic and 26 Latin facts Tesseract alone found, and won 16). So nothing moved: the old program's reader stays, and «94 %» is
  not to be quoted again without «on made-up pages». Claude, the reader that matters in the claude.ai edition, could not be
  measured on these pages here (no API key yet).
- **15/11/2026, steps 3–4: the Word and PDF programs inside the old program — version 48** (`a43b637`; `ui/assets/programs.js`, `web/build.py
  programs_dist`, README «The Word and PDF programs inside the page»). Each runs in a frame the page writes itself (`srcdoc`: no
  address fetched, so claude.ai's refusal of other sites' frames does not apply; checked under `frame-src 'none'` and no `blob:`
  scripts), its glue a module from the page's own files reading `window.__dbQuery` for the address it has none of, its
  WebAssembly fetched only on first use (three parts of ≤ 12 MB each, SHA-256 checked, kept in IndexedDB `db-programs`). Decided
  on his real files: the Word program opens **.docx only** (four of his and two of the program's own Dramrin drafts kept every
  word, table and page; his .doc files lost table columns and a signature footer), **no Word «Export PDF»** (other fonts, more
  pages, Arabic that breaks apart when copied — the PDF is still made in Word), saving only after a change; the PDF program on
  seven of his PDFs appends only the change (the engine's findings the same before and after). What only he can see: a .docx
  saved by the program, opened in Word on his computer (a list's picture bullet is dropped; mixed Arabic/Latin lines are written
  as separate runs). Opening time unchanged (5.6 s / 4.7 s against version 47). The whole suite 800 passed (1 skipped). Published
  as version 48 (31 files: the page and the two programs, 55.6 MB in one publish); every file read back byte for byte equal to
  the build, and both programs edited and saved a made-up file on the page as served. The photo and design programs (steps 5–6)
  and a phone photo as a document (step 7) come next, the same way.
- **15/11/2026, «المكتب» and the live preview** (the owner: «محتاج جزء يكون ملحق مع رفع المستندات يكون فيه كل المستندات ممكن تتعدل
  … و كمان المستندات و هي بتترفع و تتمسح تظهر بريڤيو ايه اللي بيحصل»; `56a592f`; README «المكتب, and what happens to a file…»).
  «المكتب» is on the preparation page and in the menu (`#/d/<id>/office`): every current document with its first page, edited
  in its program where there is one. The preview (`ui/assets/preview.js`) on the preparation page and in the new-dossier wizard:
  each file's pages, and while it is worked on the step, the page being read and the very picture Claude is given (boot.js
  `db-pictures`) or the reader's own page (ocr.js progress `picture`). It draws nothing while the reader reads or draws for
  Claude (`DBOCR.busy()`). Checked that it changes no reading: his nine Dramrin files through version 48 and the new build,
  twice each, the same mock for Claude — the same prompts, page pictures byte for byte, items, names, conditions, OCR quality,
  fields; only the contact sheets for cutting combined files vary run to run, in version 48 as much (pdf.js), with the same cuts.
  Published as **version 49** (index.html and suite.html only — the suite page carries the same reader and boot scripts; every
  other file is version 48's: the page's own record of each file's hash, the programs' and the reader's, is the same). Whole
  suite 802 passed; opening time unchanged (first 5.56 → 5.51 s, next 4.58 → 4.70 s, median of 8 interleaved rounds); both
  files read back byte for byte equal to the build, and the office test passed on the page as served. The Drive tools' names
  checked against their schemas and one real listing call: the fields the page reads are there.
- **15/11/2026, steps 5–6 measured on his real files — nothing added, proposed to him.** Step 5, the photo program: in the old
  program a picture is not a document (the upload gate refuses it, NP.CAPP.065 v5 general note 4), so its one use would be
  cleaning scans, which the PDF program already does in place (Scan & OCR ▸ Enhance ▸ Scanned document, `ocr.enhance`; automation
  `page_enhance_scan`: the same image objects, the text layer and links kept). On the 11 measured pages (250 facts, Tesseract
  «best» at 300 dpi, `scratchpad/scanclean/run.py`, local only): before 185 (74 %); level 25 185; level 50, the default, 184 (won
  13 facts, lost 14); level 75 192 (won 19, lost 12); every file 13–71 % bigger (its JPEG written again at quality 90). His scans
  come from CamScanner, already cleaned. So no automatic cleaning, no photo program; the tool stays in the PDF program's menu for
  a grey photocopy. Claude's reading of cleaned pages was not measured (no API key). Step 6, the design program: DesignCraft
  opens IDML, INDD and its own files and places a PDF whole (vectors, a form XObject); his artwork (Wouncure sticker and leaflet,
  Adobe Illustrator PDFs) has its words in outlines — the only live text is the designer's notes (sticker: 10 lines; leaflet: 10
  English lines) — so no program can change its words; only the designer, from the Illustrator file. The design program would
  only make new artwork from scratch. Both left out unless he wants them for something else.
- **15/11/2026, the working copy with its XML, and the real export from the page** (he asked «ليه مش بيطله امتداد xml ?», then
  «اعمله، خلي نسخة العمل تطلع بالـ XML», «اشتغل زي ما القواعد بتقول», «انا عايز برنامج كامل لكل الدول و مصر بالتلات صيغ اللي اتفقنا
  عليهم», «اي نسخة تصدر للتقديم»; `18f214f`; README «A working copy at any time»). claude.ai lets a page save a zip but never a bare
  `.xml` (the downloads allowlist), so the XML travels in its zip. The working copy now also writes the authority's eCTD
  (`ectd32-working.zip`, and `ectd40-working.zip` for Egypt) by the real export's own code (`exporter._sequences`, `working`), beside
  the export, never recorded, «WORKING COPY — NOT FOR SUBMISSION» in the envelope's description and in a note beside the sequence;
  a Word file without its PDF (the browser edition has no LibreOffice), a sheet or a picture is left out and named («item (file)»
  and why, in both languages). Tried on his real Wouncure files (24 placed by the program's classifier, 33 MB): with LibreOffice
  the two Word leaflets, made PDFs without their PI type and language, cost the whole XML — so now a refused sequence has each
  document written alone (`_cannot_take`) and only those left out; the XML came with 22 of his PDFs both ways, and its checks found
  a CoA PDF with security restrictions, no cover letter yet and scans without a text layer. Also found by the whole suite: the
  programs' delayed «ready» hint wrote over «اتحفظ» when a save ended within 1.5 s of opening (`ui/assets/programs.js`) — the Word
  test's intermittent failure; fixed. Published as **version 50** (`19a1915`; the page, suite.html, engine.worker.js and the
  engine — everything else is version 49's, the page's own record of each file's hash shows only the engine changed): whole suite
  817 passed; opening time unchanged (first 5.16 → 5.04 s, next 4.53 → 4.40 s; version 49 served with its own engine read back);
  the five files read back byte for byte equal to the build; the working copy in the browser edition, the office and both
  programs' tests passed on the page as served.
- **15/11/2026, step 7 measured on his real phone photos — nothing added** (he said «كمل خطتك زي ما كنت»). Photos: five WhatsApp
  pictures of documents from his Drive folder «Wouncure_Inspection_Appeal» (24 there: supply orders and sales reports, on paper and
  on a screen, three of them sideways; kept in `scratchpad/photos-wa`, local only), 62 facts read by eye
  (`scratchpad/photos-wa/truth.json`, `photos-wa-run.py`). The program already makes a photo put in an item a PDF (PdfCraft's
  `image_to_pdf`; in the page, `asDossierFile`), and in claude.ai Claude reads its picture. Tesseract «best» on the photo as it is:
  30/62 (48 %), the same turning the page first (OSD). The PDF program's «Enhance camera image» (`page_enhance_camera`) found the
  sheet's edges by itself on 1 photo of 5 (the screen): there colour 7/14 as before, black-and-white 1/14; with the corners set by
  hand, 6/12 for 7 and 4/12 for 5 — no better. The photos are WhatsApp-compressed (0.7–0.8 megapixels). So no straightening step;
  for a document of the file, CamScanner (as most of his scans already are) or the photo sent «as a document» keeps what a reader
  needs. Claude's reading of the photos was not measured (no API key).
  Found on the way and fixed: **the real export button failed from the page for a first sequence** — the page sends
  `submission: null` and the server refused it with 422 since the EU work (`ef51a39`), and no test clicked that button; now
  `tests/test_ui_export_all.py` clicks it for Egypt (its three formats: `ctd.zip` CTD One Submission, `ectd32.zip`, `ectd40.zip`), the
  EU, the Gulf, the US and another country. And GCC-1.1 (Module 1 table of contents) carried an eCTD node its own text says it
  has none: a document there stopped the Gulf's eCTD; now a CTD-folder item like ICH's M2–M5 tables of contents. **For submission:**
  the «تصدير المخرجات المختارة» button, once the gate is open — for Egypt `ctd.zip` is what EDA receives today (NP.CAPP.065 v5);
  `ectd32.zip` and `ectd40.zip` follow the provisional EG profiles (EDA drafts), ready for when EDA takes eCTD, not «EDA-valid».

- **15/11/2026, «نفذ كل المطلوب و متسيبش اي مرحلة لم تنفذ»: steps 5–7 done, the indication asked first** (README «The photo and
  design programs, a phone photo upright, the indication asked first»).
  · Step 7, a phone photo upright: his whole folder «Wouncure_Inspection_Appeal» fetched (21 distinct WhatsApp photos, 5 sideways,
  `scratchpad/photos-all`, local only). The page reader's own «which way up» test, made strict (a turn only when better than the
  photo as it is and at least twice every other turn read; fewer readings when the words clearly lie flat or stand): 84 cases (each
  photo in four turns) — 71 right, 13 left as they were, none turned wrong; his 21 as they came, 21 right. Reading his 5 photos with
  facts: Tesseract 30 → 35, the engine's reader 28 → 32, the page's reader 42 → 43 of 62. JPEG only. Browser: the photo is written
  again upright (JPEG 0.95) before it leaves the page, and Claude is shown it upright (about 4 s a photo here, 7 s when it turns);
  desktop: the PDF page's /Rotate. PdfCraft already honours a camera's EXIF turn (checked).
  · Step 5, the photo program in «المكتب»: a page of a PDF drawn at 200 dpi, cleaned, saved (Ctrl+S: a PSD — its picture read in the
  page) and put in that page's place (PdfCraft `page_replace`: size as shown, links and bookmarks kept, other pages untouched), a
  new version. His real 12-page scan: page 3 replaced, the other 11 the same content, 3.3 → 4.3 MB, the same findings.
  · Step 6, the design program for the artwork items: his real sticker placed in a design came back scaled and moved even on a page
  of its own size (39 % of pixels different) — so an exported PDF is kept only after the person sees before and after side by side
  with their sizes and says yes; the hint gives the file's size in mm; a new artwork can be made from scratch for an empty item.
  · The indication: the gate lists the 2.7.3 / 5.3.5 items an eCTD export needs it for, the export page asks for it with a field,
  and an eCTD export without it stops at once (`E-GATE-INDICATION`); the CTD folders go without it.
  · Claude's reading (of photos and cleaned pages) not measured: the key form refuses Anthropic's host («authenticated by the session
  itself»), and a call from here without a key is refused (401). He can add `ANTHROPIC_API_KEY` as a variable in the environment's
  settings himself (a new session reads it); never in the chat.

- **16/11/2026, he stopped the work, named the program and gave its order** («وقف حاليا اللي انت بتعمله هنعدل بعض المواضيع و بعدها
  هنكمل اختبارات»). The name: **eBOX** («برنامج مبتكر لتجهيز ملفات التسجيل الموحد يعتمد علي العمل مع الملفات بذكاء و توفير الوقت و
  المجهود»). His order: the library first (every decision and guideline, worldwide); «ملف جديد» → the country (the program lays out
  Module 1) → upload anything, any size or kind → read, show the information, cut, sort, searchable PDF, a new name that fits its
  place → shown as tree points before the file is made → view and review with a toolbar (by hand, or «the program prepares it»),
  the closed and the open points said throughout → the documents placed → the whole tree with help for what is missing → export in
  the formats he chooses → validated after it is built with a validator like the authorities' («مع ان تم التحقق من كل مستند في مرحله
  التجهيز»). He asked for his points in a strong logical order (ease of building first, then validation) and, **before any
  re-ordering is started, a proposal of what else could be done** — given in the chat on 16/11: the stations (home · library ·
  country · upload · read and sort · proposed tree · prepare and review · whole tree and what is missing · validate · export, then
  after submission), «the place before the preparation» (a document's conditions come from its place), «validated before it is
  downloaded», one path bar, three states everywhere, one «what is left» list. **Wait for his answer; change nothing in the
  program's order or name before it.**
  **Version 51 is not published** (the artifact is still version 50). The tree as committed with this entry holds steps 5–7 and the
  indication, with their tests. Whole suite, three runs: 829 passed once; twice one UI test timed out —
  `test_ui_reading_cases.py::test_refused_file_is_not_lost_at_creation` (caught again three times in short loops: the active
  substance's manufacturer typed in «راجع اللي اتقرا» is gone when «أنشئ» is clicked, `typed.apis` is not set, the wizard says «At
  least one API…»; about 1 run in 8 of that file, 2 in 4 after `test_ui_e2e.py`, never in 8 runs alone) and once
  `test_ui_e2e.py::test_generate_from_ui` (its state not caught). Not known yet whether version 50 does it too: run the same loops
  on `dbad9c0` first, then find what re-draws the review drawer or re-fills the wizard between the typing and «املا الخانات». The
  recorder: `scratchpad/flaky/pagedump.py` (`-p pagedump`, `PAGEDUMP=<file>`: the page's address, toast, alerts and the wizard's
  state at a failure). After the last whole run two things were added and only `tests/test_page_picture.py` (4) was run:
  `store.replace_page` asks the guard (a third party's or EDA's page is never replaced: E-LOCKED) and writes its audit line, and
  boot.js ends the photo check with «الصورة معدولة ✓» so the «getting the reader ready» note never stays. The browser edition was
  not rebuilt after that. Before any publish: rebuild, the whole suite clean, opening time, read back.

- **16/11/2026, he agreed, and asked for more before any start** («موافق على الترتيب، والمكتبة وملفاتي جنب بعض، وغيّر الاسم eBOX لكن
  قبل ما نبدا محتاج منك تفكير عميق في اي اقتراحات تانيه»). Decided: the order of the stations with its two changes (the place before
  the preparation; validated before it is downloaded); the home shows the library and «ملفاتي» side by side; the name is eBOX
  (interface, reports, the published page's title). **Still nothing started.** The second proposal, given in the chat:
  (a) in the path itself — the product card confirmed once after the reading (today's «راجع اللي اتقرا»; it decides which items
  are required), the box always open (a file dropped at any time walks the path alone; a newer copy of a certificate offered as a
  new version), «سيبها عليّ» (the program walks stations 4–6 by itself, takes only what it is sure of, never touches content or a
  third party's document, and comes back with one list), every problem said at the first station that can know it (his Wouncure
  files: the protected CoA and the scans without text were said at the end), the library beside every station (the condition and
  its source in a side panel; «ابدأ ملف للدولة دي» from a country's page), two names (a readable one in the tree, the format's own
  at the build); (b) what is missing and the validation — what is missing grouped by who issues it (one request per party, followed
  up), the validation station with two doors (the technical validator, saying whether its rules are official or a draft; the
  review as the authority's assessor does it — the Regulatory Reviewer that exists), a target submission date (a certificate that
  will have expired by then); (c) around the path, later, one at a time — «ملفاتي» by product (countries and sequences; «نفس المنتج
  لدولة تانية» exists and shows there), the company's details once, a one-by-one review queue, the source's quality on each
  document, a made-up trial file. Proposed way of working: four stages, each tried on his real files and published by itself
  (1 name, home, path bar — with the paused tests and steps 5–7; 2 country → upload → reading → product card → proposed tree;
  3 prepare and review → whole tree and what is missing; 4 validate → export → after submission). Said plainly: Claude's reading
  inside claude.ai cannot be measured from here. **Wait for his choice of what goes in now.**

- **16/11/2026, he said go: eBOX in four stages, each delivered by itself** («موافق، وكل مرحلة توصلني لوحدها، ابدأ بالمرحلة الأولى لكن
  اللغة هتبقي عربيه فصحي مش لهجة عاميه و محتاج كل الاختيارات تبقي تسميه غير محيره لليوزر المهم في الامر اني جربت البرنامج لقيت فيه
  اخطاء كتير و رسايل اخطاء و البرامج اللي مكمله اللي احنا وضعناها بتقول ان لازم ننزل حجات علشان اشتغل فو انت بتعدل راجع الكود و
  الاخطاء و صلحها»). Decided: groups (a) and (b) of the second proposal go in with the re-order, (c) later one at a time.
  **The program's interface is in formal Arabic (فصحى), never Egyptian colloquial** — every user-facing text (the chat with him
  stays Egyptian Arabic); every choice, button and menu entry has a name that cannot be confused. He tried version 50 and met
  many errors and error messages, and the editing programs «say things must be downloaded to work»: with every stage, review the
  code and fix the errors (he was asked for screenshots or the messages' text: his claude.ai cannot be opened from here).
  **Stage 1** = the name eBOX, the home (library and «ملفاتي» side by side), the path bar and the menu as stations, formal Arabic
  and clear names, the error sweep and its fixes, the paused tests and steps 5–7; then stages 2 (country → upload → reading →
  product card → proposed tree), 3 (prepare and review → whole tree and what is missing), 4 (validate → export → after submission).
  **The vault, for stage 3** («خاجة باكد عليها في مرحله التجهيز عايز خزنة للملفات اللي اتقرت و اتقطعت و اتجهزت اشوفها و اطلع عليها
  ذاخل البرنامج بدون تنزيل و ابقي شايف قبل ما ندخل علي التكوين اني جاهز»): in the preparation station, every file that was read, cut
  and prepared is kept in a vault he opens and reads inside the program, with no download, and a plain sign that he is ready
  before the file is composed (today's «المكتب» and its page viewer are where it starts).

- **16/11/2026, eBOX stage 1 built** (`6768d73` and the commits after it; the old program's README, «eBOX, stage 1», has the
  whole of it). What it is: the name eBOX everywhere a person reads it; one path bar of nine stations (الرئيسية · الدولة · الرفع ·
  القراءة والفرز · الشجرة المقترحة · التجهيز والمراجعة · شجرة الملف والنواقص · التحقق · التصدير) with one «التالي», and the menu
  ordered as the path; the home with the library beside «ملفاتي» and «بدء ملف لهذه الدولة»; every text in formal Arabic with
  one name for one thing (rule 14). The stations' own screens are still version 50's: they change in stages 2–4.
  **The errors he met, found by walking every screen under a page policy like claude.ai's** (`tests/test_web_sweep.py`; nobody
  can open his claude.ai from here, and he sent no screenshots): «تجهيز» failed on every Word and Excel document (one red note
  per document in «تجهيز الكل»); a document just prepared answered «not found»; a refusal that was not in the engine's own words
  gave a note with **no text at all**; an internal failure showed a Python traceback; the page viewer opened empty; `.xml`,
  `.doc`, `.xls` downloads did nothing; a script error at every opening and the fonts never applied; «مسح المحادثة» and «print»
  did nothing (`confirm()`, `print()` inside the frame); the qualification report failed on the shipped pypdf 7; a typed value
  went into another field now and then (the review race of 16/11: the side panel took the focus 30 ms after opening). The
  editing programs' first-time note no longer reads as «download something»: it says nothing is installed, and the programs a
  dossier's documents need are fetched in the background from «مراجعة المستندات وتعديلها».
  **«سجل الأعطال»** (menu → أدوات عامة): what goes wrong is written down on his device (time, screen, kind, message — never a
  document's content) and copied with one button. **When he reports a problem, ask him for this record first.**
  **How the wording was changed, for the next time** (`apps/dossier-builder/tools/wording/`, with its README): texts were
  replaced at their exact place by a list `id ⇒ new text`, checked for the same placeholders and a clean parse. Two traps cost
  a second pass: Python 3.12+ tokenizes f-strings apart from plain strings (126 messages were missed at first), and a text
  that is one piece of a sentence joined in code must keep its end spaces (25 were lost; `edges.py` finds them).
  **Not changed:** the reading rules and their words, the prompts, the letters' wording, the desktop edition's read-me
  (`desktop/README-AR.txt` is still colloquial and out of date: for the day he approves a desktop build).
- **16/11/2026, eBOX stage 1 delivered: version 51** (`7e010ce`; version id `1794816701-b6db`; the artifact's title is now
  eBOX; private as before, its declaration carried forward). Sent: the page and 37 files — suite.html, engine.worker.js,
  engine.zip.b64.txt, fonts/manifest.txt, and the photo and design programs (10 + 23 files) — so version 51 is also the
  first to hold steps 5–7 and the indication gate, built before the re-ordering and never published until now. The
  artifact holds 140 files; the 102 others are version 50's own, each checked by path and size against the build.
  **Three faults found by the last click sweep, fixed before the publish** (all there since «المكتب» was added, so in
  version 50 too): «المكتب» kept the list it had asked for before a change — after «تجهيز الكل» its buttons held ids of
  versions no longer current, and «الصفحات» showed «تعذّر عرض هذه الصفحة»; the viewer asked for a page by the id it was
  opened with; and after a page was turned, or anything done in an item's drawer, from «تجهيز المستندات», the board was
  drawn in the page's place. Now the prepare page asks for its documents at every drawing, looking at a document by an
  earlier id is shown the current version (`X-Doc-Id`), and `refreshCurrent` draws the screen the person is on. Desktop
  and company editions only: a document of fewer than four pages showed «PDF» in place of its small pages (the engine
  is now asked how many pages there are). Tests: `test_ui_office_fresh.py`, and parts of `test_prepare_office.py` and
  `test_web_faults.py`; the two browser tests fail on the page before the fix.
  **What was run on the tree that was published:** the whole suite, 855 passed and 3 skipped (22:59); every button of
  every screen clicked in the browser edition, both languages (10:19) — what it met: the export gate and «لا يمكن تصغير
  الملف أكثر», each said in words; his real files against version 50 as published, with the same stand-in for Claude —
  Dramrin's 9 files: the same 9 calls, the same prompts word for word, the same 2 waiting and 12 placed with the same
  items, names, conditions, reading quality and fields (the contact sheets of calls 2 and 7 vary from run to run, as
  they did within version 49); Wouncure's 26 files: the same in everything (28 calls, 6 waiting, 20 placed, every
  picture); opening time against version 50, twelve paired rounds: first opening 5.50 s → 5.55 s, later openings
  4.77 s → 4.71 s, the page shown at 105 ms → 122 ms (the page is 68 KB larger) — within the spread of one round.
  **After the publish:** the 38 files read back from claude.ai are the build's, byte for byte, and the tests of the
  browser edition were run on the page as served (`DB_DIST`, `scratchpad/s1/pubsite.py`): 21 passed, 2 skipped (the two
  skipped are the click sweep, run on the build itself before the publish — the served files are the same bytes).
  **Not tested, because it cannot be from here:** Claude's own reading on his account (the comparison above uses a
  stand-in; an API key in the environment would measure it), claude.ai's own «save this file?» step, and the Google
  Drive connector (no call to it was made in this session).
  **Next: stage 2** (الدولة → الرفع → القراءة والفرز → بطاقة المنتج → الشجرة المقترحة) — only when he says go, after he has
  seen stage 1 and the names of the choices (the list was given to him in the chat with version 51).
- **16/11/2026, he said «كمل» (no remark on the names: they stand): stage 2 started.** The design, decided before building
  (the wizard and the prepare page were read whole first):
  · **The wizard (`#/new`) is stations 2, 3, 4 and the product card**, one screen each: step 0 «الدولة» (the country, its
  authority, its Module 1 laid out, its record in the library); step 1 «الرفع» (one box for anything first; the typed cards
  stay below it, optional, with their kind rule); step 2 «القراءة والفرز» (what was read, the files sorted by kind, problems
  first); step 3 «بطاقة المنتج» (product, the answers that decide the items, the actives, the submission — today's steps 1–4
  on one screen, each value with its source; confirmed once). **Reading is not touched**: the same `readFiles`, rules then
  the model, the same merge.
  · **Confirming the card makes the dossier and puts every file in its waiting box** (`/unplaced`, with the kind and text the
  wizard read) — nothing is placed yet. Before stage 2 the wizard placed its files itself (`classify/text`) and a combined file
  went whole into one item; the prepare page's own upload cut it first. Now there is one way in.
  · **Station 5 «الشجرة المقترحة» is a page of the dossier** (`#/d/{id}/tree`, engine `GET|POST /api/dossiers/{id}/tree`):
  combined files cut and unknown scans read on arrival (`prepModelWaiting`, as the prepare page did), then the items by
  module with each waiting file under the item proposed for it and **the name it will carry there** (the CTD writer's own
  naming, a dry run), the files with no sure place, the items still missing; a file's item can be changed; «اعتماد الشجرة»
  places them (`/documents/{id}/place` — no fixes: the preparation is station 6's) and goes to station 6. The same page is
  the box that is always open: a file added later walks the same way.
  · **The prepare page** keeps the placed documents, their conditions and tools; its upload box and waiting list move to the
  tree page (a note with a link when files wait). Stage 3 re-orders the rest of it (the vault).
  · Left for stage 3, said to him: «سيبها عليّ» (stations 4–6 by itself), a newer copy of a certificate offered as a new
  version, the library's side panel beside every station.
  Before a publish: his real files through the new way against version 51 — the reading must be the same, and every
  difference in where a file lands must be explained (the cut of combined files is one that is expected).
- **16/11/2026, eBOX stage 2 delivered: version 52** (`eb3de33`; version id `1794834124-ec9a`; the page, `suite.html`,
  `assets/engine.worker.js` and `assets/engine.zip.b64.txt` republished, the other 136 files carried forward). What it is:
  the README's section «eBOX, stage 2». What it was tested with: the whole suite (871 passed, 3 skipped: 870 in the run, and
  the one whose expected wording had been reworded, run again), every button of every screen clicked in both languages (only
  refusals that give their reason), his real files through BOTH doors against version 51 (below), the opening time (first
  opening 5.37 s → 5.27 s, later 4.57 s → 4.59 s, ten paired rounds), the published files read back byte for byte and the
  browser edition's tests on the page as served (21 passed, 2 skipped).
  · **His real files found six things that no made-up file had** — each fixed, each with a test that fails on the code before:
  the kind rule was not asked again when a scan placed without words was read at its preparation (`store.judge_kind`); a new
  version moved its document to the end of its item and renumbered every name there (`meta.seat`); a combined file was cut
  wherever a page changed subject — a 12-page «specification and test method» into six, a 6-page validation protocol into
  four (`pages.propose`: a part now begins under a title, at «page 1 of N», or at another batch's CoA); «المكتب»'s buttons did
  nothing, silently, while documents were being prepared (`officeDoc`); the bookmarks fix told him «تعذّر التطبيق:
  bookmark_from_text_styles: step 2 …» (`fixes.py`: a scan's invisible text layer has a nameless font; and «no headings» is a
  refusal, said in both languages); «5 مستند» (`tests/test_formal_arabic.py` now refuses a number before a bare singular noun
  in the eBOX page, its scripts and the start-up).
  · **Two mistakes of mine the same files caught before he could**: skipping Claude's reading on the tree for every waiting
  scan «that has a kind» — a kind may be a hint in the file's NAME, which places nothing (two real scans left unread and
  unplaced): the engine now says `known` (an earlier reading gave the kind); and a harness that took «every line says read»
  for «the card is filled» — which showed the card could be confirmed in that moment (`w.busyN`).
  · **The comparison, for the next time a path changes** (scripts and results in the scratchpad, never committed):
  `progproto/same_reading4.py` (files added on the prepare page: version 51 and before), `progproto/same_reading5.py` (added
  on the tree page, the tree approved, then «تجهيز الكل»), `progproto/wizard_real.py old|new` (through «ملف جديد» itself),
  `s1/cmp_same.py` and `s2/explain.py` (side by side: the questions to Claude in order, each document's item, findings, meta,
  the names the tree showed against the names it ended with, the dossier data without run-specific ids). Version 51's
  results: `same-51-dramrin-e.json`, `same-51-wouncure-e.json`, `wiz-51-dramrin.json`, `wiz-51-wouncure.json`; version 52's:
  `same-s2-dramrin-g.json`, `same-s2-wouncure-g.json`, `wiz-s2-dramrin-g.json`, `wiz-s2-wouncure-g.json`. Run two at a time at
  most: with three the machine is slow enough to change what a timing-sensitive wait sees. Dramrin's contact sheets for the
  152-page file still differ in one or two pictures from run to run (as before).
  · **What the comparison says** (the stand-in model calls every scan a licence, so it tests the program around the reading):
  added on the tree — the same questions in the same order less the second look at a file already examined, the same items
  and names for every document both versions place, the same kind objections; new: the RAR opened, the leaflet and SmPC
  placed once their type and language are answered (version 51: E-META, left waiting), the two documents no longer cut.
  Through the wizard — the same reading, the same item for every document version 51 placed, the same data; new: one
  combined-file question for each scan of several pages, the kind rule's objections (Wouncure 0 → 12; version 51's wizard never
  judged a scan by its words), names that stay.
  · **Rules that came out of it.** A change of path changes WHEN something is known: every rule that ran «when the file
  arrives» has to be looked at again (the kind rule; the page's own reading of a scan runs before `/prepare`, not before
  `/place`). His files go through both doors before a publish, not one. A browser test waits for the state it checks, never
  for a neighbouring sign of it (two tests failed only when the machine was busy).
  · **Not done, and said to him**: «سيبها عليّ»; a newer copy of a certificate offered as a new version; the library beside
  every station; the board's own «إضافة مستندات» and waiting box (the old way, until stage 3); the vault. **Seen, for stage 3**:
  the validity date the wizard read for a scan is not carried to the document (the prepare page asks for it again unless
  Claude reads the document there); the prepare cards' own buttons act while «تجهيز الكل» runs; `ui/suite/index.html` still
  has counted nouns («بقي {n} يوم»).
  **Next: stage 3** (التجهيز والمراجعة مع «الخزنة» → شجرة الملف والنواقص) — only when he says go.

## Open items (propose when relevant; do when he asks)
- Old program, next pieces (one at a time, each on his real files first): the 14/11 update and measuring Claude's reading (need
  the API key: `ANTHROPIC_API_KEY` in the environment's settings, added by him), «شروط الشكل لكل دولة», the Assistant on his
  account and «المشغّل» (cannot be tested inside claude.ai from here).
- Online version check of the ICH, EMA, FDA, WHO and GCC sources. Unreachable from this environment: admin.ich.org (ICH's content
  service), esubmission.ema.europa.eu, sfda.gov.sa — they would need his approval to add.
- 64 sources have no copy kept.
- EDA's variation tool also lists 58 herbal and 52 veterinary variations not in the knowledge; the guideline has about 58 human
  items the tool does not list; the variations have no Arabic titles.
- EDA's mock-up, naming and good-review-practice guidelines are registered but not yet tied to review questions.
- The open-document button was tested in a browser, not inside the claude.ai viewer itself: if he reports a problem there, check it.
- The Operator's desktop edition, after he has tried the claude.ai panel; align it with PART-2-PLAN §3.8.
- Two things still untested where he uses them (rule 13): the workbench's real Claude call inside claude.ai, and the `.mcpb`
  extension's install in the Claude app (he reported «غير متعرف عليه»). Neither is to be sent again before a way to test it exists
  (an API key for test calls with the same tools; a Windows or Mac machine for the extension).

## The environment
Personal cloud environment «quadrapharma new»: package registries, Google Drive's APIs, Hugging Face, edaegypt.gov.eg (with www),
www.ich.org, database.ich.org, www.ema.europa.eu, www.fda.gov and www.who.int are reachable; nothing else. WebFetch may fail to
resolve names here: use curl, which goes through the proxy.
**The Anthropic API key for tests (15/11):** a network secret is refused for Anthropic's own hosts (api.anthropic.com is outside
the proxy and answers directly: 401 without a key). He adds `ANTHROPIC_API_KEY` himself as an environment variable of «quadrapharma
new» (environment menu → Edit); a session sees it from its next start or resume. Never print it or write it to a file in the
repository; a key he pastes in the chat is not used (ask him to delete it and make a new one). Say the cost before every billed run;
check the key first with the free model list. Chromium and Playwright are preinstalled; never install another
Playwright. `zip` and Python 3 are there.
