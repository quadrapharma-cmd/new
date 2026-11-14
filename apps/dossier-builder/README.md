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
| **Rebuild/fix loop** | `engine/dossier_engine/fixes.py` + `POST …/fix`, `…/request`, upload with `signed_for` | **(1) Auto-fix:** PDF version → 1.7 (the version line alone: every other byte the same), remove security and JavaScript (company documents only), bookmarks from numbered headings (CTD-style such as 3.2.P.5.1) for documents of 10+ pages. The result is saved as a new version and the original is kept. For third-party evidence, any change that alters the page image (checked by comparison) is refused. A digitally signed file is never touched. **(2) Re-obtain:** an Arabic or English request letter to the issuer, listing the defects found and what the document must meet. The item shows «waiting on issuer» with a follow-up date, and the request closes itself when a conforming copy is uploaded. **(3) Signature:** every generated letter is «unsigned draft»; export is blocked until its signed scan is uploaded. The signed scan replaces the draft and becomes locked like any evidence |
| **External references** | `POST …/slots/{slot}/references` | Register a document that is still on the company Drive (title, link, note) in its section before the file itself is uploaded. It shows as «received — not checked», with a button to open it on Drive and one to upload the file. Export stays blocked (`gate.external_only`) until every reference is replaced by an uploaded file, which is then checked like any other |
| **P3: follow-on sequences** | `engine/dossier_engine/lifecycle.py`, `app/exporter.py` | Every export after the first builds the next sequence automatically (0001… / 2…). It contains only what changed: **new**, **replace** (with `modified-file`) and **delete** in 3.2.2; a new context of use with `replacementOf`, plus suspension, in 4.0. Unchanged documents are not resent, and the tracking table is rebuilt from the history every time. A new cover letter is required for every sequence. Sequences accumulate in a lifecycle folder like a real archive, and the download holds only the new sequence. The validator runs the lifecycle rules (9.8, 11.6, 11.9, 11.10, 13.2) against the earlier sequences. On upload into a section that already has a document, the user is asked «new version or additional document» |
| Auto-classify | `engine/dossier_engine/classify.py` + `rulepacks/…/classify.yaml` | Drop a batch of files and the tool suggests a section for each one (CTD number in the name such as 3.2.P.5.1 or 32p51, keywords in Arabic or English, first-page text, API manufacturer). It never guesses when there is no evidence, and the user confirms |
| **App** | `engine/dossier_engine/app/` + `ui/index.html` | Local workspace (SQLite + files stored by hash: never overwritten, never deleted, every version kept), HTTP API on localhost, and an interface (Arabic/English, light/dark, phone width). Covered by an end-to-end Playwright test |
| **Interface v2** | `ui/assets/ds.css` + `ds.js` (shared design system), `ui/index.html`, `ui/suite/index.html`, `ui/login.html` | Dark-first «regulatory instrument» design, RTL/LTR. **Home** shows what the program does with numbers read live from the engine (`GET /api/capabilities`: requirements by module, variations, generators, PDF checks and fixes, cross-checks, validator rules, document types). **New-dossier wizard** with a live requirements preview on every answer (`POST /api/profile/preview`: slots, counts by level and module, generable and third-party items; works before the APIs are entered). **Guide** per dossier: six stages (profile → data → M1 → M2–5 → checks → export) with their live state, a computed «next step» with its action button, the output formats and the sequence history; a journey strip on every dossier page; the profile can be edited (`PUT …/profile`) and documents keep their place. **Checks** page: every technical finding, cross-document finding, open request, unsigned draft and Drive reference in one place |
| Assembler | `engine/dossier_engine/assemble.py` | Turns slots + files into writer documents. Picks the right node when a requirement has more than one (e.g. M1-04 new vs re-registration) |
| CLI | `tools/resolve.py` | Prints the requirements board for a profile |

## Countries and authorities (November 2026) — «تختار الدولة ويعمل على أساسها موديول ١»

A dossier is built for one country. The wizard opens with «where will this dossier be submitted?»; the country gives the
authority, and the authority gives **Module 1** — its structure, its numbering, what each section must hold, and the text it
was written from. **Modules 2 to 5 are the common CTD** (ICH M4), the same for every authority, with the authority's own
levels where it says otherwise and its regional items under 3.2.R.

| Country | Pack | Module 1 written from | Output |
|---|---|---|---|
| Egypt | `eda.ctd.nta065.v5` | NP.CAPP.065 v5 and the EDA guidelines (as before, untouched) | CTD · eCTD 3.2.2 · eCTD 4.0 |
| Saudi Arabia, UAE, Kuwait, Bahrain, Oman, Qatar, Yemen | `gcc.ctd.m1.v1` | GCC Module 1 Specifications v1.5 (structure, common to the seven) + SFDA «Data Requirements for Human Drugs Submission» v4.0, 3 Aug 2025 (contents, levels) | CTD folders |
| EU / EEA (30 countries) | `eu.ctd.m1.v1` | EU Module 1 eCTD Specification v3.1.1, June 2025 (structure); levels: the general rule of Directive 2001/83/EC and the Notice to Applicants | CTD · **eCTD 3.2.2** (EU M1 3.1.1) |
| United States | `us.ctd.m1.v1` | FDA «The Comprehensive Table of Contents Headings and Hierarchy» v2.3.3 (headings and numbers) | CTD folders |
| Any other country | `intl.ctd.m1.v1` | a **general** Module 1 (marked so on the card and on every item) to be matched to the country's own checklist | CTD folders |

- **What is the authority's own text and what is not is said in the program.** A pack is `verified: true` when its Module 1
  was written from the authority's published document; each requirement names its source. Where the source gives a section
  without saying which applications need it, the item carries a `level_note` (shown in the item drawer, flag `CONFIRM_LEVEL`):
  «the level here is the general practice — confirm it with the authority». The EU levels and the FDA levels are of this kind;
  the GCC contents are SFDA's — another Gulf authority's own forms and certificates are to be checked. Jordan's and the UAE's
  own Module 1 texts could not be downloaded when this was written (JFDA's site, mohap.gov.ae): Jordan gets the general Module 1,
  the UAE the GCC one.
- **Each authority asks its own questions** (`questions` in `pack.yaml`, answered in the wizard's profile step, kept in
  `profile.extra`): the receiving Gulf authority (taken from the country), the EU legal basis (Art. 8(3), 10(1), 10(3), 10(4),
  10a, 10b, 10c) and procedure, the US application type (ANDA, NDA, 505(b)(2), BLA, IND). The requirements follow them — a
  generic EU dossier gets 1.5.2 and no 1.10; an ANDA gets form 356h, the basis-for-submission statement and the comparison with
  the RLD; a Saudi dossier gets the CPP as optional (SFDA v4.0), a Kuwaiti one as required.
- **A pack stands on the common CTD**: `extends: ich.ctd.m4.v1` (a `kind: base` pack, never offered by itself), `overrides`
  (the authority's levels over a common item), `drop`. Egypt's pack is whole in itself and was not changed. Columns stay
  I / G_IMP / G_LOC — the origin is «made in the country of registration, or imported into it».
- **Everything else follows the dossier's pack**: the classifier's keywords (`classify.yaml` of the common CTD, then the
  authority's), the home of each document kind (`kinds` on a requirement: a GMP certificate goes to 1.7.1 in the Gulf, to
  the application form's annexes in the EU), the kind check, the board, the templates and «make it for me» (an item the
  template library does not describe gets its template from the requirement's own words; the model is told which authority
  the document is for), the Assistant's context, the CTD folders. Egypt-only parts are not offered to other dossiers: eCTD 4.0, the review desk (EDA
  assessor rules), NP.CAPP.040's deficiency checks, the Egyptian generators. The regional eCTD 3.2.2 is written for Egypt and
  for the EU (below); every other authority gets the CTD folders (`Pack.ectd_region`, `Pack.outputs`).
- API: `GET /api/authorities` (authorities, their questions and sources, the country list), `country` or `pack` in
  `POST /api/dossiers`, `?country=` / `?pack=` on `POST /api/profile/preview`, `authority` on `GET /api/dossiers/{id}` and in
  the projects list. Tests: `tests/test_authorities.py` (21), `tests/test_ui_country.py` (3).
- **Adding a country**: write `rulepacks/<id>/pack.yaml` (`extends`, `authority {id, countries, name}`, `questions`,
  `sources`, `verified`) and `requirements.yaml` (Module 1 only, each item with its source), `classify.yaml`; lint with
  `packs.lint`. Nothing in the engine or the page changes.

## EU eCTD 3.2.2 — EU Module 1 v3.1.1 (November 2026) — «ملف eCTD لأوروبا»

An EU dossier exports an **eCTD 3.2.2 sequence** beside its CTD folders, on the EMA's own files — nothing provisional:

- **The profile** `docs/ctd/ectd/EU-M1-3.1.1-PROFILE` (built by `tools/build_eu_profile.py`): the util files of the EMA's
  EU M1 3.1 package byte for byte (their MD5 are the published values the criteria quote), all 111 EU validation criteria v8.2
  word for word, and `m1.csv` — each Module 1 section's element, folder and fixed file name from SPEC 3.1.1 Appendix 2.
- **The writer** `writers/ectd32_eu.py`: `m1/eu/eu-regional.xml` (`eu:eu-backbone`, `dtd-version="3.1"`) in the DTD's order;
  **envelopes per procedure** — centralised: one `ema` envelope (agency EU-EMA); decentralised / mutual recognition: one per
  country of the procedure (named on the export page, kept for the follow-ons); national: one, for the country — one UUID in all;
  «to be advised» until the procedure number is given; `related-sequence` the sequence itself for initial / reformat, else the
  one that started the activity. **Country folders**: `ema` (CP), `common` for what the DCP/MRP countries share, the country
  (NP), or the country a document names (`eu_country`: a German SmPC goes to `131-spclabelpl/de/de/de-spc.pdf`); 1.3.1 adds the
  language folder and `pi-doc` (the EU's eight PI types, its 26 languages). Names `cc-fixed[-var].pdf`; the tracking table
  `cc-tracking.pdf`; 2.3 as `qos.pdf`; a 5.3 study in a folder of its own (App. 4 and the EU Q&A on additional folders).
  Modules 2–5 are the ICH App. 4 placement shared with Egypt's writer (`ectd32.place`, `ich_rel_path`, `write_index`, `finish`).
- **The lifecycle** keys a document by its country as well (EU HTG 2.9.6): a German SmPC never replaces the common one; a
  delete reaches the country it was filed for. Egyptian keys are unchanged.
- **The validator** `validators/ectd32_eu.py` reads the sequence back and runs 108 of the 111 criteria (the EG checks that read
  any 3.2.2 sequence, and the EU's own: the published checksums, the DTD order across sequences, the envelopes 14.x, the tracking
  table, the folder and name conventions, the country codes against the folders, the PDF permissions of 1.0/1.2 (revision-aware,
  after PdfCraft — `THIRD-PARTY-NOTICES.md`), Fast Web View, initial view, bookmarks pane, link zoom and targets, CP PI
  properties). 16.6, 16.7 (which eAF a file is) and 16.BP10 are listed as not run, with the reason. The label says it plainly:
  **not an EMA-accepted validator — run one before submission**; the report's header says the same.
- No provisional acknowledgement for the EU (the profile is the EMA's own); eCTD 4.0 stays Egypt's. The page asks the EU 1.3.1
  item for its PI type, language and country, the additional-data item for its country, and the export page for the countries
  of the procedure and its number; follow-ons offer the EU's own submission and unit types (read from the DTD).
- Found on the way: the common CTD mapped its tables of contents (2.1, 3.1, 4.1) to eCTD nodes the ICH DTD does not have — in
  eCTD the backbone is the table of contents, so they are CTD-folder items; and 2.3 is the QOS element itself (App. 4 says so).
- Tests: `tests/test_ectd32_eu.py` (9: DTD validity for the three procedures, what the writer refuses, the validator's pass,
  its catches, a follow-on replace, the API export, the leaflet item), `tests/test_ui_eu_ectd.py`.

## What a person's run on two real products changed (14/11/2026) — «نفذ بنفسك بمستوي انسان»

The owner asked for the whole program to be run as a person would, on the real files of two products (kept on this machine only):
Dramrin (9 files, 13 documents with an archive, one 12-page file holding five documents) and Wouncure (26 files, mostly scans, seven
of them combined). The browser edition was opened fresh, the files given to the wizard in one go, the dossier made, «Prepare them all»
pressed, the export page read. claude.ai's model was stood in by a reading of every page written beforehand from looking at the pages
(the program still drew and sent its own pictures, so its times are its own). Every fault the run met is fixed and held by
`tests/test_trial_human.py`:

- **The wizard merges by authority**: the licence's values come first, not the last answer to arrive; where another document says
  something else (the stability letter's manufacturer after a site transfer) the wizard shows both with their documents — «use this».
  One substance in two spellings (picosulphate / picosulfate) is one substance, the licence's spelling kept. A combination product's
  name carries no one active's strength. A read dose form matches the list's synonyms («Topical Powder» is «Cutaneous powder»).
- **What Claude read goes with each file**: its kind, number, dates, signature and stamp, placed or waiting — so the preparation stage
  does not ask again (the licence's validity), and a scanned certificate is put in its own active substance's item from its title.
- **A combined file is never placed whole**: one Claude saw as several documents waits to be cut; when one part's kind is unknown
  the cut dialog opens on Claude's cuts with each part's kind and title; a carton artwork (layout) and a working standard (refstd) are
  kinds Claude can name; a long file (up to 240 pages) is shown to Claude whole; after a cut the parts show at once with their progress.
- **The data keeps only what is true**: a technical document (method, validation, CoA) fills the product's empty places but never
  contradicts it and adds no active substance once the dossier has its substances; the same price in two currencies, one company in
  two spellings and a scan's stray quotes are not differences; a batch number has digits; a table heading is not a substance; the
  licence's Arabic name is not the Arabic dose form beside it; the wizard's product is what is written.
- **Preparation without noise**: a Word document is prepared (no «PDF files only» stop), a document without headings is told so
  plainly, «Prepare them all» does not toast each fix it could not make, and «improve the file» that found nothing is tried once.

## Claude reads the scans again; each document held to its item's conditions (13/11/2026) — «البرنامج رجع ذكي»

The owner, 13/11/2026: the program had become a page that took scans, acted as if it was reading, and showed nothing — the
12-page licence of a real product took **14 minutes** of in-page OCR (9 of its 12 pages still hard to read), its upload waited for
it, and the card only said «reading the text…». The cause: on 12/11 the page pictures stopped going to the model (the commit «no
OCR anywhere»), and when scans were allowed back their reading was left to OCR. Now:

- **Claude reads a scan from its page pictures.** Browser edition: `ocr.js pageImages` draws the first pages (pdf.js, no reader
  to load: half a second for that licence) as **two halves each**, overlapping by a tenth — the platform brings every picture to
  about 1.2 megapixels, and a whole page would reach the model at about 110 dpi, too little for the small Arabic print of an EDA
  licence's tables; a half reaches it at about 150 dpi. `DBAI.extract` sends them with the prompt (`sample`, declared with
  `images: true`), says which picture is which half of which page, and that any OCR text given is only a help. Server editions:
  `/api/extract/ai` sends the PDF itself (the API reads every page as a picture too); a PDF over 24 MB goes as its first 20 pages.
  The wizard reads the files with text together and **each scan alone** (two readings at a time); a scan the model read is
  accepted (its kind from what the model read, so «not this document» still works) — «no text» is said only when nothing could
  read it. The product-data page and the Regulatory Reviewer send the pictures of the scanned documents they ask about.
- **No upload waits for OCR where the model is.** The page's own OCR runs before an upload only where there is no model — the
  first two pages, quickly — and whole documents are read only to write the text layer when a scan is prepared, `quick`: Tesseract
  alone, two or three pages at a time, a page turned only when it is most likely sideways. Every stage shows on the file itself
  (the wizard's card: «drawing its pages for Claude», «Claude is reading it», «reading the scan · 3 / 12 pages»; the preparation
  page: «making it searchable · 5 of 12 pages»), not in a toast another toast covers (the `db-ocr` event).
- **The key in the Assistant's settings is the key.** On a computer or a company server the intake, the review and the
  preparation stage read with the key saved in the Assistant's settings (mode 0600), not only with `ANTHROPIC_API_KEY`.
- **The preparation stage holds each document to its item's conditions** (`engine/dossier_engine/prepare.py`, one source for the
  page, the item and the Assistant). For every document: read (a scan by Claude) → placed in its item → each condition of that
  item (`conditions.py`, NP.CAPP.065 v5) read against the document — the **form** (a searchable PDF; every PDF rule PdfCraft
  checks: version, security, JavaScript, bookmarks, attachments, size…) and the **content** (dated; valid on the day of submission
  — the date read from it, by Claude or by its text; on letterhead, signed and stamped; legalised; a CoA's batch, manufacturing
  and expiry dates; a translation for another language; the production lines) → fixed where the program can (PdfCraft; the text
  layer under a scan) → each condition shown as **met** (and how the program knows: its text, Claude saw it, you confirmed it),
  **fixed**, **the program fixes it**, **needs you** (why and what to do), or **check it** (one click: «yes» / «not yet»; a date
  field for a validity nobody could read). What Claude read on a document's pages is kept with it (`meta.model`:
  `POST …/documents/{id}/model-reading` from the page, `…/read-by-model` with the key); its kind suggests a waiting scan's item;
  a validity date it read becomes the document's (so the board turns it red the day it expires). The person's answers are kept
  per document (`POST …/documents/{id}/confirm`), the signed / stamped / legalised question per item as before.

## Every value in its place, combined files cut, PdfCraft's tools on each document (13/11/2026) — «عايز الأبلكيشن ذكي»

The owner: «show PdfCraft's tools where they are used; any information it reads it stores and puts in its place; a combined file —
cut it and make from it the papers each item asks for».

- **Every value kept in its place** (`engine/dossier_engine/absorb.py`). After a document is read — its own words through the
  rules, and what Claude read on its pages — every value goes into the dossier's data in the shape the wizard writes: the
  registration (number, dates, validity, shelf life, storage, prices, packs), the product, the active substances (strength,
  manufacturer, country), the composition, the batches, the specification tests and the results. A place that is empty is filled;
  a place already written is never written over — the document's value is kept as a **difference to choose** (data
  «conflicts», with the document it came from), shown at the top of the preparation page with «keep what is written» / «take the
  document's» (`POST …/data/choose`). Where each value came from is kept (data «sources»), and each card says what it gave
  («kept in its place: registration no., shelf life, 3 active substances»). It runs in the preparation stage and whenever
  claude.ai's model reads a placed document.
- **A combined file is cut into its documents** and each part goes to its item. A waiting file of several pages is looked at
  first by its own words (each page's kind, «page 1 of …», a new batch's certificate — `pages.propose`); where they cannot tell
  (a scan), Claude looks at **every page at once**, small and numbered, several to a picture (`ocr.js contactSheets`, `DBAI.bundle`;
  on a computer or a company server, `…/split-by-model` sends the PDF with the key) and says where each document starts and what
  it is (`extract.split_prompt` / `parse_split`: consecutive parts from page 1 to the last, known kinds — anything else is one
  part). When every part's kind is known, «Prepare» cuts the file with PdfCraft (`…/split` with each part's kind and title), each
  part is suggested its item from its kind and prepared there in the same run; otherwise the person confirms the cuts.
- **PdfCraft's tools on each document where it is prepared**, grouped as a person looks for them: view (the pages, find in the
  document, open the file), pages (split it, turn or remove a page), file quality (improve the file, make it smaller), protect
  (redact for real, a copy with the team's notes), convert (as Word), compare (with the previous version). Third-party and
  authority documents are never changed in their content: they keep the view, the turn of a page, Word and the comparison. The
  item's drawer keeps the same tools.

## No OCR — the upload gate (November 2026) — «مفيش OCR: الملف لازم يكون فيه نص»

(Superseded on 13/11/2026 — see the section above; kept for the history.)

Two trials on real products showed the reading of scans as the program's weakest step (about 11 minutes of OCR for 26 files, a
licence nobody recognised, a second pass of «readable copies» that wrote PDF 1.3). The program now does **no OCR anywhere** — not
on the server, not in the desktop build, not in the browser — and sends no page images to a model:

- **The upload gate.** EDA asks every document as a searchable PDF (NP.CAPP.065 v5, general note 4: «All submitted documents
  should be scanned and searchable PDF files»). A file without text of its own — a PDF whose first 12 pages hold fewer than 20
  characters of text, or an image of any kind — is **refused at upload** (`extract.has_text`, `Store.refuse_without_text`: 422
  `E-NOTEXT` with `why: scan | image`) with the reason and what to do, in Arabic and English: make the text layer when scanning
  (the scanner's software, Acrobat, or a phone app that saves searchable PDFs) and add it again. It stands on every way in: an
  item's upload, the bulk upload, the «not placed yet» box, Drive, the Assistant's staging, a signed scan. In the wizard the file's
  line says «no text — not accepted» with the reason and «remove»; its searchable copy added under the same name takes its place;
  a refused file is never read by the model, never fills a field and never reaches the dossier.
- **The PDF version.** A PDF 1.0–1.3 is stored with its first line set to `%PDF-1.7` (`fixes.set_version_17`): the same length,
  every other byte identical — third-party evidence is not altered and no pixel check is needed — and never on a digitally signed
  file (the signature covers that line; the version finding is then a warning). The auto-fix «PDF version» does the same.
- **Reading** is the files' own text only (PDF text layer, Word, Excel, PowerPoint, OpenDocument, RTF, HTML, text); the model
  (claude.ai's in the browser edition, or the API with a key) reads that text.
- **Removed:** tesseract and ocrmypdf (server image, requirements), tesseract.js, pdf.js and the image decoders (browser and desktop
  editions, `web/vendor.sh`, the desktop CI step), `ui/assets/ocr.js`, «Make readable (OCR)» and `…/ocr-layer`, `/api/images/pdf`
  and `/api/images/png`, the wrapping of images into PDFs. Older notes below that still speak of OCR describe the program before.

## What a real product's trial changed (November 2026)

The owner handed over a real product's folder (ten documents: licence, method of analysis, specifications, a batch certificate,
validation chromatograms, a RAR of the new method, a stability letter, fee receipts) and asked for it to be taken to an exported
file. On the version of that day the trial failed: the form was read as «tablet» (a word in a test method), the product as
sterile («sterile peptone water»), 4 of 13 files landed in their place, two generated tables carried wrong data under a green
«conforming», «make it for me» took 78 s an item, and nothing could be exported (the gate). What was changed, each with a test on
fictional documents (`tests/test_trial_fixes.py`, `tests/test_ui_working_copy.py`):

- **A file is read once.** `extract.read_text` keeps each reading by the file's SHA-256 and the pages asked (in memory; a large
  file's reading also in `workspace/cache/text`): the kind rule, a template's base documents and the Assistant get the text without
  reading the file again; the first pages read for the kind rule are not taken for the whole file; a reading kept on disk belongs
  to the reader that made it (`READ_FORMAT` — raise it when what a reading holds changes); the app that answers a request claims
  the cache folder of its own workspace.
- **What a document is and where it goes.** Kinds for a method of analysis, a method validation / chromatograms, a fees receipt,
  a variation approval; phrases that settle the kind wherever they stand (an authority's own title or department); the home of a
  kind follows what the document is about (a certificate or a specification that names the product at its top is the finished
  product's: 3.2.P.5.4 / 3.2.P.5.1; an authority's stability letter goes to the approvals item or, where that does not apply,
  3.2.P.8). Nothing is placed by itself on weak evidence: only the home of a recognised kind or a strong match; a certificate
  that names none of the actives its kind belongs to is offered, not placed. A fixed copy keeps its document's verdict.
- **What the product is comes from the documents that state it** (licence, application form, CPP, SmPC, pricing, composition,
  CADC, variation approval) or from a labelled field / the title of a technical document — never from a word in a method. The
  form is matched against the vocabulary, longest name first, and travels with its standard entry. British and American
  spellings name one substance. The licence's «Manufacturer of active substance — For X:» block names an active whose strength
  line the scanner's text layer garbled; a company name whose first word that layer lost is taken as printed elsewhere in the document. «Invalidation
  date» is not the date of issue; a batch number has a digit; a manufacture date is the one right after its label.
- **Tables are read as tables.** A table row is one line «cell | cell | cell» in a .docx and in an old .doc alike (a cell's own
  paragraphs joined); specifications and results come from the rows under a «Test | Specification | Result | Method» header, one
  specification per dossier (the specification document's), never from sentences of a method.
- **A working copy at any time.** `POST /api/dossiers/{id}/export {"working": true}` (the export page's «working copy» button):
  the CTD folders with every document in the dossier now (Word drafts stay Word, each document keeps its own name where an item
  holds several), `00-navigator.html`, `00-checklist.csv` and `00-MISSING.txt`; marked «not for submission», never recorded as a
  submission. The gate still guards the real export.
- Generators' forms prefill who signs (asked once, remembered across forms), the shelf life, the pack and the composition from
  what the dossier already knows; «Conforms» for a descriptive test is a result, not a missing figure.
- A draft continued right after the page loads is filled once the vocabulary has arrived: the form — and the product's name
  made from it — is written in words, never as the vocabulary's code.

Still open after the trial: the Drive connector refuses a file over 10 MB (the page asks for it from the device); a full dossier
needs documents no reading can supply (third-party certificates, the suppliers' substance files) and the signed copies of what
the program drafts.

## Intake — «upload the documents and the forms fill themselves»

**Documents first.** The new-dossier wizard opens with the documents, not with fields: one named upload button per base document the
program needs (registration licence / notification, pricing certificate, reference SmPC, API CoA, GMP certificates, CEP/DMF, product
analysis / conformity, specifications, stability, agreements / toll card, commercial register, other), plus a drop-everything zone and
Google Drive. Each upload is read at once (its own text: the rules, and the model where available; a file without text is refused on its line) and the recognised values go into the
product, profile, API and submission steps with their source marked; those steps then ask only for what is still missing («missing —
type it») and say so at the top. «Review what was read» opens the full review of every value.
Each upload is read **once**: the texts are cached and only new files go through the reading and the model again; the
cards show **live progress** per file (reading the text, the model reading, read) and **what each document
gave** (trade name, form, manufacturer, 3 actives…), with a running «recognised so far» summary. The **kind rule** refuses a document
uploaded under the wrong name (a stability approval under «pricing certificate»): the card shows «not this document: stability»
with «move it to its card» / «remove»; the same rule runs on every board upload (`extract.kind_check`, `KIND_HOME`): a blocking
finding `DOC-KIND` names the item the file belongs to and «move it» (`POST documents/{id}/move`) takes it there. The wizard's work is
**kept on the server** as it goes (`/api/intake/drafts…`: fields, the files, the readings) and restored after a refresh or on another
computer; a file whose reading was not saved yet is read again on restore; «Start over» discards the draft.

`engine/dossier_engine/extract.py` reads the company's PDFs (CPP, registration licence, GMP, CEP, CoA, specification,
Annex I, SmPC…) into the forms' shape: document kind, certificate numbers, issuers, issue and expiry dates, trade
name, dosage form, strength, manufacturer, active substances, applicant, batches, results. Two layers over the same
text: the **rules** (regular expressions; everywhere, offline) and **Claude** — the `sample` capability in the browser
edition (the documents' text), or `POST /api/extract/ai` through the Anthropic SDK when
`ANTHROPIC_API_KEY` is set on the computer. Endpoints: `POST /api/extract` (files → rules + the AI prompt),
`POST /api/dossiers/{id}/extract` (the dossier's own documents). In the interface: the first wizard step («Upload
documents and fill» → review every value → fill all steps → the files are placed in their sections after creation),
«Extract from the documents» on the product-data page, and the document form of the product file. Every value is
reviewed before it is used; nothing is written without the user's confirmation. **Arabic documents** (EDA letters such as the
registration notification «إخطار تسجيل», Arabic certificates) are read natively: Arabic labels, Arabic dosage forms and units,
Arabic-Indic digits and dates (`engine/dossier_engine/arabic.py`); a scan or a photo has no text of its own and is refused at upload
(see «No OCR — the upload gate»); the review drawer says per file whether it was read or refused.

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
batches into the product data once the dossier exists. A scan without any text is not read at all (no OCR, no page images): it is
refused at upload with its reason, and the drawer names it. Tests: `tests/test_intake_eda.py` (a fictional product on the three forms, clean and OCR-noisy).

### Every document format, old and new

A file is what its bytes say, whatever it is called (`officefiles.sniff`), and every format a company's folders hold is read from the
inside with the standard library and lxml only, so every edition reads them, the browser one included:

| family | new formats | old formats |
|---|---|---|
| Word | `.docx` `.docm` `.dotx` | `.doc` 97-2003 (`msdoc.py`: OLE2 container, FIB, piece table), Word 6/95 when not fast-saved, Word 2003 XML, RTF |
| Excel | `.xlsx` `.xlsm` `.xltx` (shared strings, dates by cell style) | `.xls` 97-2003 (BIFF8, strings across CONTINUE records) and 5/95, Excel 2003 XML, `.csv` `.tsv` |
| PowerPoint | `.pptx` `.ppsx` (slides in their order, tables) | `.ppt` 97-2003 (text atoms; masters and notes left out) |
| OpenDocument | `.odt` `.ods` `.odp` | |
| text | HTML, plain text, XML, JSON in UTF-8 / UTF-16 / Windows-1256 / 1252 | |
| images | every kind, see «Images of every kind» below | |

The text comes out the way the rules read a document: lines in their order, a table or sheet row as «cell | cell», a date as
`YYYY-MM-DD`, a field as what it shows. The kind comes from that text like any other document's; the file is accepted wherever a
document is (upload, Drive, the Assistant, bulk placement, the review); in an item it is a **source file** (`DOCX-DRAFT`, with the
wording of its family) that the PDF replaces, because the dossier takes PDF. Where LibreOffice is installed, `amend_document`
converts a `.doc` to `.docx` first. Not read: password-protected files, fast-saved Word 6/95 files, archives (`.zip` `.rar` `.7z`:
unpack first) — they wait for the person like any unread file. In the Drive list lock files (`~$…`), system files (`Thumbs.db`) and
empty files are left out with their reason, and a file with no extension and a general type is offered (not ticked) and read by its
bytes once fetched. Tests: `tests/test_office_files.py`, `tests/test_word_files.py`, `tests/test_ui_drive.py` (made-up «Dermacure»
fixtures converted by LibreOffice; the Excel reader was also compared with openpyxl on two real workbooks: no word missing).

### Images of every kind

An image is told by its bytes (`imagefiles.image_format`), whatever the file is called: JPEG (also `.jfif`, `.jpe`), PNG, GIF, BMP,
TIFF (multi-page, BigTIFF), WebP, HEIC/HEIF (iPhone photos), AVIF, JPEG 2000, PNM, PSD, ICO, PCX. Two letters are never enough: a
text that starts with «BM» or «P5» is not a picture.

**An image is not a document.** The program does no OCR and wraps no picture in a PDF: an image of any kind put in an item, the
box, the wizard or Drive is refused at the upload gate with its reason (`E-NOTEXT`, `why: image`) — scan the paper to a searchable
PDF, or photograph it with an app that saves searchable PDFs, and add the PDF. Tests: `tests/test_image_files.py`.

### Compressed files

A compressed file given anywhere a document is taken (the wizard, «bulk upload», an item, a drop, a Drive folder) is opened and the
documents inside it take its place (`archives.py`, `POST /api/archives/unpack`, `ui/assets/archive.js`). An archive is told by its
bytes; a Word, Excel or OpenDocument file is a ZIP inside and is never mistaken for one.

| kind | where it opens |
|---|---|
| ZIP, TAR, `.tar.gz` / `.tgz`, `.tar.bz2`, a single `.gz` / `.bz2` | every edition (the standard library), the browser one included |
| `.xz`, `.tar.xz` | the desktop and server editions (the browser edition's Python has no xz: said, with what to do) |
| RAR (RAR 2.9–4.x and RAR5) | **every edition**: the page opens it itself with the program's own reader (`ui/assets/rar.js`, below), the same way everywhere. What the reader does not open (an archive older than RAR 2.9, one the page's memory cannot hold) goes to the unpacker the machine has, in the desktop and server editions (`tar` on Windows 10+ and macOS is bsdtar, else 7-Zip, unrar or unar) |
| 7z | the desktop and server editions (the machine's unpacker). The browser edition refuses it with the reason («unpack it first, or pack the files as ZIP») |

Names keep their Arabic (UTF-8, or the Windows code pages 1256/720 when the UTF-8 flag is missing); `..`, drive letters and leading
slashes are dropped, nothing is written outside a private temporary folder; `__MACOSX`, `Thumbs.db`, `~$…` are left out; an archive
inside the archive is opened too (two levels). There is **no limit of the program's own** on the number of files in an archive or
on their size (see «No limit on what is uploaded» below). Refused with the reason, never half-taken in silence: a password, and an
archive that expands hundreds of times — a «zip bomb»: more than 100 MB coming out of less than a 250th of it, counted on what
really comes out, whatever the format and whatever the headers declare (one found inside an honest archive is left out, the rest
is taken). A TAR cut short keeps what was read before the break. More than 40 documents in one archive are not taken whole: the
person ticks the ones the dossier needs. One item takes one document: an archive with several goes through «bulk upload».
Tests: `tests/test_archives.py` (the RAR samples are libarchive's public test files, fetched by `web/vendor.sh`, skipped when
absent), `tests/test_ui_projects.py`, `tests/test_web_edition.py`.

**No limit on what is uploaded.** Nothing of the program's own stops a file for its size or a batch for its number: a file of a
draft (it was 60 MB), the wizard's saved state, the files of an archive and their size, the pages of a scan turned into a PDF
(it was 300), the files taken from a Drive folder at once (it was 40), the request body behind the cloud proxy (it was 500 MB).
What is left is what the machine itself can hold, and it is never met in silence:
- **memory** — a file larger than the memory answers `E-MEMORY` (507) in words, in every edition, wherever it runs out: the
  upload's body, the engine, the page's RAR reader, the browser edition's bridge; a full disk (desktop, server) answers
  `E-DISK-FULL` the same way;
- **the browser edition's memory** — there the engine and its files live in the page's memory. An upload reaches the engine a
  piece at a time (`web/pybridge.py`), so it is not held several times over; a file sits in one block of memory and the browser
  gives no block over about 2 GB — asking for one used to end the engine without an answer and is now refused in words, the
  engine going on (`DB_SAFEFS` in `web/bigfs.js`). Measured in Chromium: 150 MB, 400 MB, 1 GB and 1.5 GB put in a draft, the
  page closed and opened, read back with the same SHA-256; 2 GB taken and saved (reading the whole of it back needs more memory
  than the test machine had); 2.3 GB refused in five seconds with the message, the engine alive. Files of that size belong in
  the desktop edition, which keeps them on the disk;
- **the browser edition's storage** — the workspace lives in the browser's own storage (IndexedDB). The browser refuses one stored
  value over about 127 MB, and a refused value used to stop every save after it: a large file is now stored as a Blob
  (`web/bigfs.js`), which has no such ceiling — a save is called done only once the large file reads back from the storage, and a browser that
  keeps no Blobs (some private windows) is found out the first time and gets the bytes as before. The quota the browser gives the page is the
  one ceiling left: when it refuses a save, a note stays on the screen for as long as that is true («the browser refused to save…»,
  with what is used of what is allowed, and «try saving again»), a file the storage has no room for leaves the wizard's draft again
  (said on the document's own line; it stays in the page for that visit) so that everything else keeps being saved, and a file
  taken out of a draft frees its space at once;
- **Google Drive inside claude.ai** — the Drive connection of claude.ai does not hand over a file larger than 10 MB. That limit is
  the connection's, not the program's, and it cannot be lifted from here: such a file is marked in the Drive list with «open it
  in Drive» and «upload from the device» (which has no limit). The desktop and server editions read Drive through Google's own
  API, with no such limit.
Tests: `tests/test_no_limits.py`, `tests/test_archives.py`, `tests/test_rar_reader.py`, `tests/test_web_large_files.py`.

**RAR inside the page (`ui/assets/rar.js`).** The page of claude.ai may load nothing but scripts from a few CDNs and no binary
file, so the RAR reader is the program's own code: about 600 lines of JavaScript with no library and nothing fetched, run in a
worker made from its own source (on the page's thread where a worker cannot be made), at about 50 MB a second. It reads the old
format (RAR 2.9–4.x, compression version 29: LZ with Huffman tables, the standard filters — x86, Itanium, delta, RGB, audio — and
the text method of «Best» compression, PPMd variant H) and RAR5 (LZ with the x86, ARM and delta filters), stored files, solid
archives, archives split in parts (`name.part1.rar …`, or `name.rar` + `name.r00 …`: the parts are given together), names in any
language (the old format's packed Unicode names too), self-extracting archives, hard links and «same file» records as copies.
Every file is checked against the CRC-32 the archive keeps for it: one that does not match is reported, never handed over. Left
out, each with its reason: files under a password (the archive is named, the open files are still taken), symbolic links,
archives older than RAR 2.9, and what the page's memory cannot hold (said as that). The reader has no limit of its own on files
or sizes; a «bomb» is refused as in the engine. Only the names worth taking are unpacked (the
documents and the archives inside), except in a solid archive, where what comes before must be unpacked to reach what comes after.
The PPMd model follows Dmitry Shkarin's public-domain design as written out in 7-Zip's Ppmd7 (Igor Pavlov, public domain); the
rest was written from the published format notes and the behaviour of the free unpackers; there is no compression code.
Checked against the original unpacker (RAR 7.00), file by file: three of the owner's own archives (RAR5 and RAR4 with Arabic names;
one of them is cut short, and both programs refuse the same file in it), 17 packings of a 50 MB folder (every method, dictionaries
from 128 KB to 64 MB, solid, up to 11 parts, every filter) and 43 public archives of the libarchive project, among them damaged
ones that must be refused without a crash or a hang. Tests: `tests/test_rar_reader.py` (the archives in
`tests/data/archives/rar` were made for it with RAR 7.00 from made-up documents; the public ones are fetched by `web/vendor.sh`).

### The reading rules, reviewed on real layouts (November 2026)

A review of the intake logic (sixteen independent passes, each attacked and revised, then checked against real registration
notifications, pricing letters, leaflets and certificates) changed how documents are read, judged and placed:

- **Active substances.** A form's substances are the run of «name amount unit» lines under their label and nothing else: the cells
  printed after them (appearance, shelf life, pack, price), the composition table's headings («Quantity», «Specification») and OCR
  fragments are not substances. A name without an amount counts only when no amount is printed at all («Active ingredient:
  Bisoprolol fumarate»). A label is a field, not a word in a sentence («…the excretion of the active ingredients in human milk»).
  Several substances on one line, «name; amount» column edges and «Img» for «1mg» are read; a salt repair never renames the
  substance itself. `clean_apis` (engine) and `cleanApis` (page) drop headings, sentence tails, appearances, companies and
  countries, keep substances that are salts («Sodium chloride»), never merge different ones («Vitamin B1» / «B12», «Salicylic» /
  «Acetylsalicylic acid») and merge spellings, salts and typos of one; both give the same answer (a parity test) and keep up to 40.
- **The kind rule.** A document is known by what is written inside it, never by the name of its file: the text layer, or —
  when its words name no kind — the kind the wizard's reading gave it (kept with the file). A file that
  could not be read is not judged at all: its name only hints where to offer it (`kind_hint`), it is never placed or refused on
  its name (`auto` is null). Inside the text, the heading printed at the top of the page counts before the body, whole words
  («coa» is not the start of «coated»), a reference to another document by its number («…بإخطار التسجيل رقم 123») only when nothing
  else is named. Arabic stability approvals, WHO CPPs, leaflets by their section titles and contracts by «first party / الطرف الأول»
  are recognised. A scan placed from the «not placed yet» box is judged by the reading the wizard made of it.
- **Placement.** Among the per-substance items (CEP, CoA, GMP of each active) the substance the document names decides; a tie
  between two actives is never guessed (`auto` is null and the file waits in the box). A certificate of analysis that names the
  product and none of its actives goes to the product's batch analyses. The leaflet item and Module 5 items ask for the document's
  details (type + language, study) before a file is placed or moved there; a placed file takes the item's title, not its file name.
- **The wizard.** What the user typed outlives a refresh and a new upload; a file the kind rule refused waits in the box after
  creation instead of vanishing; a refresh in the middle of placing resumes it.

Tests: `tests/test_reading_cases.py`, `tests/test_intake_actives.py`, `tests/test_intake_fixes.py`, `tests/test_ui_reading_cases.py`,
`tests/test_ui_intake_fixes.py`.

## Leaving, drafts and deleting

**A project that was started is never lost by leaving.** The wizard keeps its work in a draft from the first document or the first
typed field (`intake_draft` / `intake_file`): the files go into the draft before their reading starts. Leaving — the menu, the
«Leave (the draft is kept)» button, a closed tab — keeps it; the projects list and the home page show «Projects not finished yet»
with **Continue** and a delete button, and «New project» starts a new one while the draft stays. A continued draft shows every file it
holds at once and reads again the ones whose reading was not saved. A draft goes when its project is created (after every file is in
the dossier: a file that could not be moved keeps the draft) or when the person deletes it (two presses; its files leave the disk
when nothing else uses them). A draft that was deleted never comes back through a late save: writing to it answers 404
(`intake_api.py`). In the browser edition the storage is written right after a draft's files are taken, a moment after every other
write, at the latest 1.5 s into a long run of requests, and when the tab is hidden (`web/engine.worker.js`, `web/boot.js`).

**Deleting.**

| what | where | how |
|---|---|---|
| a document of an item | the item's panel and the upload list: «Delete» | two presses; the row is kept as withdrawn (the activity record names it) |
| a project | the projects list and the home page: the bin on its row | to the **Trash** first: it comes back as it was («Bring back»). From the Trash, «Delete for good» asks for the project's name: documents, data, requests, reviews, conversations and exports go, and the stored files nothing else uses leave the disk (`Store.purge_dossier`, `gc_blobs`) |
| a draft | «Projects not finished yet»: the bin; in the wizard: «Start over» | two presses |
| a product of the product file | the product's «Data» tab: «Delete the product» | its name typed; its links to parties and the documents that are only its own go, shared documents stay, a dossier built from it is not touched |
| a library document | its edit panel: «Delete for good» | two presses («Withdraw» stays for a document that was replaced) |

The activity record is append-only: it keeps its lines and adds one saying who deleted what and when. The Assistant never deletes a
project, a product or a library document; with sign-in on, an editor uses the Trash and only an administrator deletes for good.
Tests: `tests/test_delete.py`, `tests/test_ui_projects.py`, `tests/test_suite_ui.py`, `tests/test_web_edition.py`.

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

## Templates and «make it for me» — a form in front of every item, and the program drafts the document

The owner's rule: in front of every requirement, what the document looks like, and an option for the program to make it instead of the
user from the base documents already uploaded. `rulepacks/eda.ctd.nta065.v5/templates/library.yaml` (generated by
`tools/build_template_library.py`, linted by `generate/draft.py:lint`) holds one entry per requirement of the EDA pack (101): `draft` **full**
(18: the program drafts it from the base documents and the product data — lists, statements, nomenclature, manufacturers, composition,
batch formula, justifications, specifications on letterhead, SmPC/PIL from the reference), **partial** (27: the program builds the ICH M4Q
structure and the tables, the company adds the science — development, process, validation, impurities, stability, QOS, master records…),
**generator** (11: an existing generator makes it) or **none** (45: issued by a third party or EDA, uploaded as issued; the entry carries
what an acceptable copy shows). Each template has sections (`para`, `list`, `table` with columns, `fields`), EN/AR titles and hints, the base
document kinds it draws from, letterhead and language. The board shows **«النموذج»** on every row and **«اعمله لي»** on draftable
items; the item drawer shows **the document itself as a live page**: its sections with the product's own data where the program has it and
grey example values elsewhere, every paragraph, table cell and field editable in place (+ row), «make it for me from the documents» fills
the page (`POST …/fill`, nothing stored), «save as Word draft» stores what is on the page. Third-party and EDA items show a live example of the
acceptable document (issuer, what it must show, the product's values) with upload and re-issue. «Make it for me» (`POST /api/dossiers/{id}/slots/{slot}/draft`): the engine assembles the
prompt (template, product data, the texts of the base documents, saved readings) — in the browser edition claude.ai's built-in model answers
it inside the page (no key); on a server with the company's Anthropic key the server asks the model; with neither, the program fills what it
knows from the data and marks the rest — the Word draft is stored in the item as an unsigned version with its **gaps** (what is missing and
which document would give it), its sources per section and the reviewer's notes; the user reviews, completes, prints and signs where the
template says so. The Assistant has `get_draft_template` and `draft_document`. Other endpoints: `GET /api/templates`,
`GET /api/dossiers/{id}/slots/{slot}/template`. Tests: `tests/test_draft.py`, `tests/test_ui_draft.py`.

## Smart fields (controlled vocabularies)

Fields whose answers are a bounded set are dropdowns, filled from vocabularies the engine owns (`rulepacks/vocab/`, served by
`GET /api/vocab`): dose forms as EDQM standard terms with their Arabic names, the spellings documents use and the route each
form implies (`forms.yaml`, 63 terms), countries as ISO 3166-1 with Arabic names (`countries.json`, 249), strength units and
API submission options. The intake matches what it read to the standard entry (`vocab.match_form`, `vocab.match_country`:
«Topical Powder» → Cutaneous powder · topical, «P.R. China» → China · CN, «أقراص مغلفة» → Film-coated tablet) and the dropdown opens
on it; a value that matches nothing stays as printed under «Other…» so nothing read is lost. Choosing a form sets the route of
administration. Free-name fields (applicant, manufacturers, substances) suggest the names already used in this workspace.
Tests: `tests/test_vocab.py`.

## Google Drive as a source

Paste a Drive folder (or file) link and the program lists what is there and reads what it needs. **An open link needs no setup:** server and
desktop editions read folders shared «anyone with the link» through Google's public folder page (verified against a real folder), and the
browser edition reads any link the viewer can open through the viewer's own Google Drive connector in claude.ai (the artifact's `mcp`
capability: `search_files`, `get_file_metadata`, `download_file_content`; Claude asks the viewer's permission once; private folders work
too). The other ways in (`engine/dossier_engine/drive.py`,
`GET/PUT /api/drive/settings`, `POST /api/drive/list`, `GET /api/drive/files/{id}`, `POST /api/dossiers/{id}/drive/stage`). Three ways in,
by what the workspace holds in `drive.json` (mode 600): a **service account** key from Google Cloud — the company shares its folder
with the account's e-mail once and private folders become readable (server editions; the key never goes to a browser); a **Google
API key** for folders shared «anyone with the link» (works in the browser edition too, the Drive API answers CORS); or nothing, for
public folders through Google's embedded folder view and the public download URL (server editions). Google Docs are exported to
Word (so they can be amended), Sheets and Slides to PDF; everything is read-only. In the wizard the intake card has «From Google
Drive»; the board's bulk upload has it too; the Assistant has `drive_list` and `drive_fetch` (a file becomes an unplaced document,
then `read_document` and `place_document`). Tests: `tests/test_drive.py` (a stand-in for Google's HTTP).

**The Drive panel says what it is doing (November 2026).** Reading the folder and fetching the files show on the panel itself (a
count, a bar, the file in hand), not in a passing toast; a file Drive refuses stays listed with Drive's own reason, with «try these
again» and «continue with the ones fetched»; nothing is handed over silently and nothing ends silently. Sub-folders are listed four
at a time. A folder of up to 40 readable files comes pre-selected; a larger one is left for the person to choose from («select all»
exists), and a selection over 40 files or 150 MB is confirmed with a second press, because in the browser edition every file is
fetched and read on the person's own machine. Word files of the old format (`.doc`) are offered like `.docx`; a title with no extension
gets the one of its Drive type. Every item of the board and of the publisher view has a Drive button next to «upload» (one file, the
same checks as an upload), and the last link is kept on the browser. Tests: `tests/test_ui_drive.py`.

**A file over 10 MB (browser edition).** The Drive connection of claude.ai does not download a file over 10 MB (its own limit).
Such a file is marked in the list before anything is fetched and left unticked; asked for anyway, the refusal says what to do in the
person's language. The panel gives the way out in place: «Open in Drive» for each such file, and «Upload from this computer», whose
files join the ones Drive did give and are read with them. The desktop and server editions read Drive through the Drive API and
have no such limit. Tests: `tests/test_ui_drive.py`.

## Users and sign-in

Sign-in is a **switch the owner controls** (`auth.json` in the workspace, `engine/dossier_engine/app/auth.py`). A fresh local or desktop
install opens without a password (one person on one computer). The **Users** screen (`#/users`) turns it on: the owner creates the first
administrator and is signed in at once; from then on the program asks for a username and password, `users.json` holds scrypt hashes
(mode 600), sessions are signed cookies (12 h), writes need the `X-DB: 1` header, five wrong passwords lock a name for 15 minutes.
Roles: **administrator** (everything, plus users, the switch and the keys of the Assistant and Drive), **editor** (builds, uploads,
reviews, exports), **viewer** (reads everything, every write is refused by the server, the page says so and dims the primary buttons),
**disabled** (cannot sign in; the account and its history stay). The administrator adds users, changes roles, sets passwords, deletes
accounts (never their own, never the last administrator), sees the last sign-in, and can turn sign-in off again (accounts kept; turning
it back on needs an administrator's password). Everyone changes their own password from the key button in the header. Every step is in
the activity log with who did it (`auth.enabled`, `auth.disabled`, `user.added`, `user.updated`, `user.removed`, `login`, `login.failed`).
API: `GET /api/auth` (state, counts only), `POST /api/auth/enable`, `POST /api/auth/disable`, `GET/POST /api/users`,
`PUT/DELETE /api/users/{username}`, `POST /api/me/password`. The cloud/company edition (`DB_MODE=cloud` or `DB_AUTH=1`, first
administrator from `DB_ADMIN_USER`/`DB_ADMIN_PASSWORD`) keeps sign-in always on; the browser edition has no accounts (one person,
one browser). A switch left on with no administrator stays open rather than locking everyone out. Tests: `tests/test_users.py`,
`tests/test_ui_users.py`, `tests/test_auth.py`, `tests/test_roles_audit.py`.

## Browser edition (open from a link, nothing to install)

`web/` turns the same app into a claude.ai artifact: the Python engine runs **inside the browser** (Pyodide), the
interface calls it through a fetch shim (`web/boot.js` → `web/pybridge.py`, the FastAPI app called as an ASGI app, no
server), and the workspace lives in the browser's IndexedDB (`/workspace`). Downloads go through the artifact's
`downloads` capability. Without LibreOffice, generated letters come out as **Word drafts**; the user prints, signs,
scans and uploads the PDF, which replaces the draft (export stays blocked until then), and the tracking table is
rendered as a text-only PDF (`docx_kit.basic_pdf`). No ghostscript pixel check there (a fix on third-party
evidence that would rewrite a page is refused rather than applied unverified; the version line is changed everywhere).

**Opening (November 2026).** The runtime's own files — the Python engine, its libraries, the rule packs: about 29 MB on the
wire — used to be fetched at every opening, behind a loading bar that stood at 4 % the whole time: on a slow line an opening looked
stuck. They are now kept in the browser's storage after the first download (`web/assets.js`; each file known by a tag written at
build time into the page and the worker, `DB_MANIFEST`): the next opening fetches none of them (1.9 MB instead of 30.5 MB — the
page itself and two scripts), a new version fetches only the files that changed, and anything wrong with that storage falls back
to the network. The loading screen says how far the download is («12 of 29 MB»), for how long, and — when no data has arrived for
40 seconds — that the line is slow or down, with «try again». The engine itself starts faster: the rule packs are read with the C
YAML parser where the build has one (every edition's does; `dossier_engine/yamlfast.py`), which took the application's start from
1.8 s to 0.24 s natively and about two seconds off every opening in the browser. Measured on a 4 Mbps line with no browser cache:
first opening 50 s with the progress shown, the next 9 s. Tests: `tests/test_web_start.py`.

**The page never waits on the engine (November 2026).** The engine runs in a worker (`web/engine.worker.js`, started by `boot.js`;
`?engine=page` or a browser without workers falls back to the page's own thread). Documents are read one file per request, then the
rules run once on all the texts, so a large selection never becomes one giant request and the memory in use is that of one file.
The rules' patterns are compiled once (`dossier_engine/__init__.py` enlarges `re`'s cache): on three real scans the rules pass went
from about 4 s of frozen page to about a second off the page's thread. Every call that takes more than a third of a second shows a
thin «working» bar (`ds.js`), and an error the page did not expect is shown instead of being swallowed.

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
