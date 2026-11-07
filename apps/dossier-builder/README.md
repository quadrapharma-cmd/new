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
| **P3: follow-on sequences** | `engine/dossier_engine/lifecycle.py`, `app/exporter.py` | Every export after the first builds the next sequence automatically (0001… / 2…). It contains only what changed: **new**, **replace** (with `modified-file`) and **delete** in 3.2.2; a new context of use with `replacementOf`, plus suspension, in 4.0. Unchanged documents are not resent, and the tracking table is rebuilt from the history every time. A new cover letter is required for every sequence. Sequences accumulate in a lifecycle folder like a real archive, and the download holds only the new sequence. The validator runs the lifecycle rules (9.8, 11.6, 11.9, 11.10, 13.2) against the earlier sequences. On upload into a section that already has a document, the user is asked «new version or additional document» |
| Auto-classify | `engine/dossier_engine/classify.py` + `rulepacks/…/classify.yaml` | Drop a batch of files and the tool suggests a section for each one (CTD number in the name such as 3.2.P.5.1 or 32p51, keywords in Arabic or English, first-page text, API manufacturer). It never guesses when there is no evidence, and the user confirms |
| **App** | `engine/dossier_engine/app/` + `ui/index.html` | Local workspace (SQLite + files stored by hash: never overwritten, never deleted, every version kept), HTTP API on localhost, and an interface (Arabic/English, light/dark, phone width). Covered by an end-to-end Playwright test |
| Assembler | `engine/dossier_engine/assemble.py` | Turns slots + files into writer documents. Picks the right node when a requirement has more than one (e.g. M1-04 new vs re-registration) |
| CLI | `tools/resolve.py` | Prints the requirements board for a profile |

## Run the app (local, nothing leaves the machine)

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
