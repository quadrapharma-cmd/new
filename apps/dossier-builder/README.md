# Dossier Builder for EDA — engine (phase P0)

The design lives in `docs/ctd/design/`: `01-PLAN.md`, `02-LOGIC.md`, `03-UX.md`, and the prototype.

This folder is the code skeleton. It is kept here until the separate repository (`eda-dossier-builder`, decision D5) exists, and it touches nothing in Drugbox.

## What works now (P0)

| Part | Path | What it does |
|---|---|---|
| Rule pack | `rulepacks/eda.ctd.nta065.v5/` | 101 requirements (M1–M5) from NP.CAPP.065 v5 + the CTD Quality guideline v2. Each one carries: the matrix cell verbatim (I / G-Imp / G-Loc), an `applies` condition, a document class, the source, and a provenance tag |
| Schema | `rulepacks/schema/requirement.schema.json` | JSON Schema for a requirement record |
| Expression language | `engine/dossier_engine/expr.py` | Safe boolean conditions (`and/or/not/in/==`). Parsed and never executed: no calls, no attributes |
| Profile | `engine/dossier_engine/profile.py` | The product facts. Blocks contradictions with a bilingual message (local + imported bulk, toll + imported, Rolling after 01/12/2026, biological, duplicate API) |
| eCTD placement | `requirements.yaml` → `ectd.nodes` | Each requirement is mapped to its node: `m1/eg` from the provisional profile, M2–M5 from the ICH DTD (tested) |
| Resolver | `engine/dossier_engine/resolver.py` | profile + pack → slots (R / O / NR / NA). Each slot gives a reason and a source. Slots are expanded per API manufacturer (CEP / DMF / FULL). `diff()` reports what a profile change adds or removes |
| **Writer 1: CTD** | `engine/dossier_engine/writers/ctd.py` | A One Submission package numbered per NP.CAPP.065 v5. 3.2.S has one folder per API manufacturer; 1.1.7 has one folder per variation. Adds `00-navigator.html` (Arabic/English: each item with its status and reason) and `00-checklist.csv`. Names are Windows-safe and paths stay ≤ 180 |
| **Writer 2: eCTD 3.2.2** | `engine/dossier_engine/writers/ectd32.py` | Builds a sequence from documents. Element order comes from the DTDs, folders from ICH App. 4 and the EG map. Writes `index.xml`, `m1/eg/eg-regional.xml` (envelope `EG-EDA`), MD5, `util/`. Limits: 64 characters per name, 180 per path. A sequence is never overwritten. Required DTD attributes (substance, manufacturer, product, indication) are filled in |
| **Writer 3: eCTD 4.0** | `engine/dossier_engine/writers/ectd40.py` | `submissionunit.xml` (HL7 RPS) + `sha256.txt`. Context of use comes from the EG M1 list (provisional) and the ICH CV v1.0.3. Keywords follow the CV; a missing required keyword stops the build (eCTD4-070). Sender-defined keyword definitions are written. Flat `m1/`, no `util`. Validated against the ICH XSD. A document's UUID stays the same across sequences. Every EG OID is a PLACEHOLDER until EDA registers real ones |
| PDF checks | `engine/dossier_engine/checks/pdf.py` | PDF version 1.4–1.7, password and security settings, empty or corrupt files, Portfolio, JavaScript, searchable text (a scan is allowed for third-party certificates and blocks company documents), name ≤ 64. Each finding has a rule number, an Arabic/English message and an action (auto_fix / rebuild / re_obtain) |
| Evidence lock | `engine/dossier_engine/guard.py` | Any operation that changes the content of a GMP certificate, CPP, EDA document or executed record → `E-LOCKED` + audit event. Only placement operations are allowed |
| Generators | `engine/dossier_engine/generate/` | Annex I + the Arabic undertaking (text taken from NP.CAPP.065 v5 pp.27–30, conditional clauses: decree 450 case 1/3, re-registration, variations), composition certificate (core/coat, % and totals), salt calculation (formula + MW reference + assay), CEP commitment, translation declaration, cover letter, tracking table. Word with real RTL → PDF via LibreOffice, «مسودة — غير موقّعة» (unsigned draft) watermark. Missing data → `MissingData(fields)`, never a guess |
| **Publisher view (like EXTEDO)** | `ui/index.html` + `GET /preview?output=` | Three panes: section tree (with status) → section documents → properties (element or context of use, path, name/path lengths, operation, SHA-256). Switch CTD / eCTD 3.2.2 / eCTD 4.0 with a live preview that writes nothing; drag a PDF onto any section; Guided ↔ Publisher toggle |
| **Validators** | `engine/dossier_engine/validators/` | They read the output back from disk. **3.2.2:** 91 of the profile's 141 rules are automated; the other 50 are marked «not run» with the reason (they need earlier sequences or a visual check). **4.0:** XSD, SHA-256, references, unassociated files, lengths and names, context of use, required keywords, EG headings. Every export produces `validation-report.html` (Arabic/English), kept outside the submission per EG-BP-E21. Negative tests inject a defect for each rule |
| **P2: product data + cross-checks** | `engine/dossier_engine/crosschecks.py`, «Product data» page | Each fact is entered once: active-substance sources (address as on GMP, CEP, CoA name), batches, specification, results grid, packs. Then the 11 cross-checks from the checklist plus the NP.CAPP.040 deficiencies that can be judged from data (≥ 2 batches, numeric results instead of «complies», dissolution Q, API batches, executed BMR for the BE batch, CEP status and retest period). The findings reach the board status and the export gate |
| **P2: Module 3 tables** | `engine/dossier_engine/generate/m3tables.py` | 3.2.P.5.1 / 3.2.P.5.4 / 3.2.S.4.1 / 3.2.S.4.4, built from the data in one click, printing values exactly as entered |
| **P3: variation picker** | `engine/dossier_engine/variations.py` + `rulepacks/eda.variations.gl026.v6/` + «Variations» page | The EDA list of 90 human variations (from the EDA self-guided tool, matching GL.CAPP.026 v6). Search → choose one or more variations → class (a group takes the highest class) + eCTD submission type (var-pac-n/a/b/ii) + mode (single/grouping) + the conditions and requirements of each, with the source row |
| **Rebuild/fix loop** | `engine/dossier_engine/fixes.py` + `POST …/fix`, `…/request`, upload with `signed_for` | **(1) Auto-fix:** PDF version → 1.7, remove security and JavaScript (company documents only), OCR layer (Arabic + English, tested on a real Arabic scan), bookmarks from numbered headings (CTD-style such as 3.2.P.5.1) for documents of 10+ pages. The result is saved as a new version and the original is kept. For third-party evidence, any change that alters the page image (checked by comparison) is refused. A digitally signed file is never touched. **(2) Re-obtain:** an Arabic or English request letter to the issuer, listing the defects found and what the document must meet. The item shows «waiting on issuer» with a follow-up date, and the request closes itself when a conforming copy is uploaded. **(3) Signature:** every generated letter is «unsigned draft»; export is blocked until its signed scan is uploaded. The signed scan replaces the draft and becomes locked like any evidence |
| **External references** | `POST …/slots/{slot}/references` | Register a document that is still on the company Drive (title, link, note) in its section before the file itself is uploaded. It shows as «received — not checked», with a button to open it on Drive and one to upload the file. Export stays blocked (`gate.external_only`) until every reference is replaced by an uploaded file, which is then checked like any other |
| **P3: follow-on sequences** | `engine/dossier_engine/lifecycle.py`, `app/exporter.py` | Every export after the first builds the next sequence automatically (0001… / 2…). It contains only what changed: **new**, **replace** (with `modified-file`) and **delete** in 3.2.2; a new context of use with `replacementOf`, plus suspension, in 4.0. Unchanged documents are not resent, and the tracking table is rebuilt from the history every time. A new cover letter is required for every sequence. Sequences accumulate in a lifecycle folder like a real archive, and the download holds only the new sequence. The validator runs the lifecycle rules (9.8, 11.6, 11.9, 11.10, 13.2) against the earlier sequences. On upload into a section that already has a document, the user is asked «new version or additional document» |
| Auto-classify | `engine/dossier_engine/classify.py` + `rulepacks/…/classify.yaml` | Drop a batch of files and the tool suggests a section for each one (CTD number in the name such as 3.2.P.5.1 or 32p51, keywords in Arabic or English, first-page text, API manufacturer). It never guesses when there is no evidence, and the user confirms |
| **App** | `engine/dossier_engine/app/` + `ui/index.html` | Local workspace (SQLite + files stored by hash: never overwritten, never deleted, every version kept), HTTP API on localhost, and an interface (Arabic/English, light/dark, phone width). Covered by an end-to-end Playwright test |
| **Interface v2** | `ui/assets/ds.css` + `ds.js` (shared design system), `ui/index.html`, `ui/suite/index.html`, `ui/login.html` | Dark-first «regulatory instrument» design, RTL/LTR. **Home** shows what the program does with numbers read live from the engine (`GET /api/capabilities`: requirements by module, variations, generators, PDF checks and fixes, cross-checks, validator rules, document types). **New-dossier wizard** with a live requirements preview on every answer (`POST /api/profile/preview`: slots, counts by level and module, generable and third-party items; works before the APIs are entered). **Guide** per dossier: six stages (profile → data → M1 → M2–5 → checks → export) with their live state, a computed «next step» with its action button, the output formats and the sequence history; a journey strip on every dossier page; the profile can be edited (`PUT …/profile`) and documents keep their place. **Checks** page: every technical finding, cross-document finding, open request, unsigned draft and Drive reference in one place |
| Assembler | `engine/dossier_engine/assemble.py` | Turns slots + files into writer documents. Picks the right node when a requirement has more than one (e.g. M1-04 new vs re-registration) |
| CLI | `tools/resolve.py` | Prints the requirements board for a profile |

## Intake — «upload the documents and the forms fill themselves»

`engine/dossier_engine/extract.py` reads the company's PDFs (CPP, registration licence, GMP, CEP, CoA, specification,
Annex I, SmPC…) into the forms' shape: document kind, certificate numbers, issuers, issue and expiry dates, trade
name, dosage form, strength, manufacturer, active substances, applicant, batches, results. Two layers over the same
text: the **rules** (regular expressions; everywhere, offline) and **Claude** — the `sample` capability in the browser
edition (page images of scanned PDFs rendered by pdf.js), or `POST /api/extract/ai` through the Anthropic SDK when
`ANTHROPIC_API_KEY` is set on the computer. Endpoints: `POST /api/extract` (files → rules + the AI prompt),
`POST /api/dossiers/{id}/extract` (the dossier's own documents). In the interface: the first wizard step («Upload
documents and fill» → review every value → fill all steps → the files are placed in their sections after creation),
«Extract from the documents» on the product-data page, and the document form of the product file. Every value is
reviewed before it is used; nothing is written without the user's confirmation. **Arabic documents** (EDA letters such as the
registration notification «إخطار تسجيل», Arabic certificates) are read natively: Arabic labels, Arabic dosage forms and units,
Arabic-Indic digits and dates (`engine/dossier_engine/arabic.py`); a **scan or a photo (JPG/PNG) is OCR'd** on the computer when
tesseract with the Arabic language is installed (`apt install tesseract-ocr tesseract-ocr-ara poppler-utils`), and goes to Claude as
page images otherwise; the review drawer says per file whether it was text, an OCR'd scan or a scan without text.
**OCR in the browser:** when the server has no tesseract (the browser edition, a desktop without it), the page itself reads the
scan with tesseract.js (Arabic + English, `ui/assets/ocr.js`; pages rendered by pdf.js, first 4 pages, nothing leaves the browser),
then the rules run again on that text (`POST /api/extract/text`); the chip says «scan read by OCR in the browser». The assets
(~12 MB: library, single-file LSTM cores, fast language data as base64 text, `web/tess/worker.boot.js` decoding it inside the
worker) come from `web/vendor.sh` into `web/vendor/tess`, are served at `/assets/tess/`, bundled by the desktop spec and copied
into the browser edition by `web/build.py`.
**Make readable (OCR):** a stored scan can be converted into a searchable PDF without touching its page images — on a server with
tesseract through the existing auto-fix (ocrmypdf), otherwise in the browser: tesseract.js writes one text-only PDF page per page
(invisible text at the right places), `POST /api/dossiers/{id}/documents/{doc}/ocr-layer` lays them over the original pages with
pypdf (`fixes.overlay_text_pages`) and stores the result as a new version (`fixes: [add_ocr_layer]`, `ocr_where: browser`), so the
searchable-text finding clears and third-party evidence stays unaltered. The item drawer offers it as «Make readable (OCR)» on any
image-only PDF; the intake drawer offers to convert the scanned files right after they are saved.

**EDA forms are read as tables, with understanding of their layout** (`engine/dossier_engine/intake_eda.py`): the Final Registration
License (trade name with its Arabic name, dosage form, one active substance per line after «Each 1g contains» with its strength and
unit equivalence, «Manufacturer Of active substance» paired to each substance — two substances may share one manufacturer —, the
licence holder as applicant, the finished-product manufacturer and its country, registration number, invalidation date, shelf life,
approved pack, one price per pack, toll / local), the PPMA pricing letter («Each 1g contains: A + B …» and the price-table rows, one
per pack and page) and the CADC Notification Letter (batch, expiry, Conform / Non-conform), plus composition tables (ingredient ·
standard · amount · active / excipient). OCR noise is tolerated («Zine» → «Zinc», «10,000 mg» → «10.000 mg» when the form prints
three decimals, «1! mg», junk prefixes, «Co.» never splits a company) and nothing is guessed: an unreadable date stays empty and a
substance whose manufacturer is not printed stays without one, highlighted in the review drawer for the user to complete. The
wizard carries each active substance with strength, manufacturer and country into the dossier, and the composition rows and
batches into the product data once the dossier exists. **A scan without any text is read from its page images**: by Claude in the
browser edition (the `sample` capability receives the rendered pages) or through the Anthropic API on a computer with
`ANTHROPIC_API_KEY` (PDFs attached as documents, photos as images); the drawer names the scans that were read that way and those
that were not read on this computer. Tests: `tests/test_intake_eda.py` (a fictional product on the three forms, clean and OCR-noisy).

## The Assistant («المساعد») — Claude inside the program

A conversation per dossier (floating button on every dossier page) in which Claude does the work through the program's own
operations, exposed to it as 25 tools (`engine/dossier_engine/assistant/tools.py`): read the board and an item's requirement,
read a document's text **and its pages** (the PDF pages are attached, so scans are seen), save a digest of what a document
states (kept in the store so later sessions do not re-read it), write product data and the profile, classify and place unplaced
files, generate the program's documents, run the Regulatory Reviewer and judge its findings from the documents, draft
responses, make letters, open re-issue requests. Writes go through the program's HTTP API in-process with the actor «claude»,
so validation, errors and the audit trail are the same as the screen's (`assistant.tool` rows carry the rationale). Three
tools never run without a person: export, signing a review, withdrawing a document — the drawer shows an approval card and the
run waits (`engine/dossier_engine/assistant/runner.py`: a background thread per run, `claude-opus-5-5` through the Anthropic SDK
with streaming, prompt caching on the system prompt and tools, refusal fallbacks, a per-turn task budget and step limit, context
trimming that keeps attachments only in the last two turns, usage and cost accounting). The company's API key is stored in
`<workspace>/assistant.json` (mode 600) or `ANTHROPIC_API_KEY` and is never returned to the browser; the settings form in the
drawer saves and tests it (`/api/assistant/settings`, admin-only in cloud mode). Endpoints: `GET/POST /api/dossiers/{id}/assistant`,
`…/assistant/messages` (text + files, stored as unplaced documents), `…/approvals/{id}`, `…/stop`, `DELETE …/assistant`,
`…/readings`. Desktop and cloud editions only; the browser edition says so. Tests: `tests/test_assistant.py` (scripted stand-in
for the API client), `tests/test_ui_assistant.py` (the drawer journey). Design note: `docs/ctd/design/05-OPERATOR.md`.

## One document: read → review → amend per the rules

Every document in the item drawer has a **Document review** panel (`engine/dossier_engine/review/docreview.py`). Its rubric is
the review pack's questions that point at the document's CTD item (by requirement id, slot id or CTD number, filtered by the
dossier's profile) plus general document rules by class: text layer, product named, signed, dated (company documents), validity
and issuer (certificates). **Review by the rules** answers what keywords, dates and the validity record can answer
(`POST /api/dossiers/{id}/documents/{doc}/review`); the rest is marked «needs reading». **Review with the Assistant** sends the
document to the Assistant, which reads every page and records one finding per rule with page, excerpt, what is wrong and the
required change, in English and Arabic (`record_document_review`); every review is kept with its origin. **Amend per the rules**:
a Word document is edited with **tracked changes** (`engine/dossier_engine/generate/amend.py`: `w:ins`/`w:del` with author and
date, a change log appended as a final section) and stored as a new unsigned draft version that the company accepts in Word and
signs; a PDF without a Word source gets an **amendment memo** (rule · where · finding · required change) linked to the document;
a third-party document is never altered — the memo goes to the issuer with a re-issue request; a program-generated document is
regenerated from corrected data. Tests: `tests/test_docreview.py`.

## Browser edition (open from a link, nothing to install)

`web/` turns the same app into a claude.ai artifact: the Python engine runs **inside the browser** (Pyodide), the
interface calls it through a fetch shim (`web/boot.js` → `web/pybridge.py`, the FastAPI app called as an ASGI app, no
server), and the workspace lives in the browser's IndexedDB (`/workspace`). Downloads go through the artifact's
`downloads` capability. Without LibreOffice, generated letters come out as **Word drafts**; the user prints, signs,
scans and uploads the PDF, which replaces the draft (export stays blocked until then), and the tracking table is
rendered as a text-only PDF (`docx_kit.basic_pdf`). No OCR and no ghostscript pixel check there (fixes on third-party
evidence are refused rather than applied unverified).

```bash
bash apps/dossier-builder/web/vendor.sh        # once: Pyodide 0.27.7 + wasm wheels + pure wheels (~20 MB, not committed)
python3 apps/dossier-builder/web/build.py      # → web/dist (index.html for the Artifact tool, index.local.html + suite.html, assets/)
python3 -m pytest -q apps/dossier-builder/tests/test_web_edition.py   # the journey inside Chromium, no server
```

## Regulatory Reviewer — the dossier reviewed the way EDA (and the international assessors) review it

`engine/dossier_engine/review/` + `rulepacks/eda.review.v1/` + the «المراجع الرقابي» pages of the builder (`#/d/<id>/review/…`).
One run (`POST /api/dossiers/{id}/review`) resolves the profile, then asks every applicable **assessor question** of the
knowledge pack (226 questions: screening · quality M3 · CADC · stability · bioequivalence · labelling · gates · clinical ·
reliance; layers `eda` = what EDA publishes, `intl` = ICH/WHO/EMA/FDA practice beyond EDA, `prep` = WHO screening
items). Evidence comes from the documents (per-page text, keyword hits with page and excerpt — a scan without a text
layer is «not assessable», never «missing»), from the structured data (named checks in `review/checks.py`), from the
board (missing required items, technical PDF findings) and from the cross-checks. Every finding carries the EDA source
with a verbatim quote and, where it exists, the international anchor; a severity (critical / major / minor / note — the
tool's own scale, EDA publishes none); the authority-voice wording EN + AR; and the action that fixes it. Departments get
a verdict (approve · approve with comments · clock stop · reject), the dossier a readiness verdict, and the regulatory
clock is simulated from the published timelines table (decrees 820/2016 and 450/2023). Outputs: the **deficiency letter**
and the **assessment report** per department (DOCX, PDF with LibreOffice), a response cycle (respond → re-assess closes
the finding only when the question becomes adequate), manual overrides with a reason (audit log), a second-assessor
sign-off (good review practice), and the **AI assessor** — Claude reads a section's documents (browser edition through
the `sample` capability, server through the SDK with a key) and suggests verdicts that enter the letter only after a
human confirms them; quoted excerpts are verified against the document text. Everything says «simulation — EDA decides».
Lint: `python3 -m pytest -q tests/test_review.py` (pack clean and cited, run, responses, letters, sign-off, AI, reliance).

## Run the app

**Online (cloud):** see `deploy/DEPLOY-AR.md` (Docker + login + HTTPS).

### Locally (nothing leaves the machine)

```bash
pip install -r requirements-dev.txt          # + LibreOffice for Word → PDF
python3 tools/serve.py ~/DossierBuilder      # then open http://127.0.0.1:8765/
```
The interface is Arabic first (RTL), with English one click away. The flow: new-dossier wizard (product → profile → active substances → submission) → requirements board (status, «why?», upload with an instant check) → export (gate + provisional acknowledgement → three zips) → activity log (restore anything withdrawn).

## Run (engine and tests)

```bash
pip install -r requirements-dev.txt
python3 -m pytest -q tests                                  # 50+ tests
python3 tools/resolve.py examples/examplol.yaml             # required items
python3 tools/resolve.py examples/examplol.yaml --all --lang ar   # with the reasons, Arabic
python3 tools/export_demo.py examples/examplol.yaml /tmp/out   # the three outputs from one dossier + DTD/XSD validation
```

## Rules for editing the pack

- **The YAML is the source of truth.** `tools/xlsx_to_pack.py` was used once to bootstrap the pack from `docs/ctd/checklist/EDA-eCTD-Company-Checklist.xlsx`.
- `tests/test_pack_vs_checklist.py` keeps the pack and the checklist in agreement: same ids and titles, matrix cells verbatim. An unconditional item must resolve to the matrix level.
- Any logic beyond the matrix is labelled `logic_provenance`. An engineering assumption (e.g. S.2.2–2.6 and S.3.2 «covered by CEP») is tagged `ASSUMPTION` and shows ⚑ in the UI until it is confirmed.

## Next (P0 → P1)

The provisional EG profiles are in `docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0/` (eCTD 3.2.2) and `…-v4-v0/` (eCTD 4.0). After them come the pack of checks (`checks.yaml`), the folder map per output (`folders.yaml`), and the three writers: CTD, eCTD 3.2.2 and eCTD 4.0.
