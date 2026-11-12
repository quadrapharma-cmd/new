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

**Documents first.** The new-dossier wizard opens with the documents, not with fields: one named upload button per base document the
program needs (registration licence / notification, pricing certificate, reference SmPC, API CoA, GMP certificates, CEP/DMF, product
analysis / conformity, specifications, stability, agreements / toll card, commercial register, other), plus a drop-everything zone and
Google Drive. Each upload is read at once (rules, OCR in the page, the model where available) and the recognised values go into the
product, profile, API and submission steps with their source marked; those steps then ask only for what is still missing («missing —
type it») and say so at the top. «Review what was read» opens the full review of every value.
Each upload is read **once**: the texts (OCR included) are cached and only new files go through text, OCR and the model again; the
cards show **live progress** per file (reading the text, OCR page n/N, the model reading the pages, read) and **what each document
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

| where | what reads it |
|---|---|
| in the browser (every edition; the only reader in the browser edition) | `ui/assets/ocr.js`: JPEG and PNG as they are; a phone photo turned the way its EXIF says; GIF, BMP, WebP, AVIF, ICO through the browser's decoder; **TIFF** page by page with UTIF.js (LZW, PackBits, CCITT G3/G4 fax, JPEG, Deflate); **HEIC/HEIF** with libheif (WebAssembly). Then tesseract.js. |
| on the machine (desktop and server editions) | tesseract opens JPEG, PNG, GIF, BMP, TIFF (page by page, up to the page limit), WebP, JPEG 2000, PNM itself; the others (AVIF, PSD, PCX, ICO, HEIC) and a photo on its side go through `imagefiles.to_png`: Pillow where installed (the desktop build bundles it), else `sips` on macOS, ImageMagick, `heif-convert`, ffmpeg. `POST /api/images/png` lends that converter to the page for the kinds a browser cannot decode. |

**An image placed in an item becomes a PDF** — the dossier takes PDF. A JPEG is wrapped as it is (`imagefiles.jpegs_pdf`: the image
bytes untouched, the page turned by `/Rotate` when the EXIF says the photo is on its side, its own size when it states a sensible
resolution, else fitted on A4); a TIFF keeps its pages; every other kind is decoded first — by the page before it uploads (so the
browser edition does it too, `POST /api/images/pdf`), by Pillow in the engine. What is left is the scan's text layer, the same
one-click OCR fix as any scanned PDF. An image nothing here can open is kept, with that reason. Not read inside the browser
edition: JPEG 2000, PSD, PCX, PNM (no decoder in a browser); the desktop and server editions read them.
The decoders — UTIF.js 3.1.0 (MIT), pako's inflate 2.1.0 (MIT/Zlib), libheif-js 1.23.5 (LGPL-3.0) — are vendored by `web/vendor.sh` into
`web/vendor/img` (not committed, each with its licence file) and served at `/assets/img` by the desktop and server editions. The page
published on claude.ai carries no copy: it loads the same releases from jsDelivr (unpkg as a second mirror), each checked against its
SHA-384 (a file that differs is refused and the person is told the image could not be opened). Tests: `tests/test_image_files.py`, `tests/test_ui_images.py`, `tests/test_web_edition.py`.

### Compressed files

A compressed file given anywhere a document is taken (the wizard, «bulk upload», an item, a drop, a Drive folder) is opened and the
documents inside it take its place (`archives.py`, `POST /api/archives/unpack`, `ui/assets/archive.js`). An archive is told by its
bytes; a Word, Excel or OpenDocument file is a ZIP inside and is never mistaken for one.

| kind | where it opens |
|---|---|
| ZIP, TAR, `.tar.gz` / `.tgz`, `.tar.bz2`, a single `.gz` / `.bz2` | every edition (the standard library), the browser one included |
| `.xz`, `.tar.xz` | the desktop and server editions (the browser edition's Python has no xz: said, with what to do) |
| RAR (old and RAR5), 7z | the desktop and server editions, through the unpacker the machine has: `tar` on Windows 10+ and macOS is bsdtar (libarchive), else 7-Zip, unrar or unar. The browser edition has no unpacker: the RAR is refused with that reason («unpack it first, or pack the files as ZIP») |

Names keep their Arabic (UTF-8, or the Windows code pages 1256/720 when the UTF-8 flag is missing); `..`, drive letters and leading
slashes are dropped, nothing is written outside a private temporary folder; `__MACOSX`, `Thumbs.db`, `~$…` are left out; an archive
inside the archive is opened too (two levels). Refused with the reason, never half-taken in silence: more than 600 files, more than
800 MB unpacked (200 MB in the browser edition, where everything is in memory), an archive that expands too much (a «zip bomb»), a
password. A TAR cut short keeps what was read before the break. More than 40 documents in one archive are not taken whole: the
person ticks the ones the dossier needs. One item takes one document: an archive with several goes through «bulk upload».
Tests: `tests/test_archives.py` (the RAR samples are libarchive's public test files, fetched by `web/vendor.sh`, skipped when
absent), `tests/test_ui_projects.py`, `tests/test_web_edition.py`.

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
- **The kind rule.** A document is known by what is written inside it, never by the name of its file: the text layer, the reading
  the wizard made of a scan (browser OCR, sent with the upload), or an OCR of the first page where the machine can. A file that
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
exists), and a selection over 40 files or 150 MB is confirmed with a second press, because in the browser edition every scan is
read by OCR on the person's own machine. Word files of the old format (`.doc`) are offered like `.docx`; a title with no extension
gets the one of its Drive type. Every item of the board and of the publisher view has a Drive button next to «upload» (one file, the
same checks as an upload), and the last link is kept on the browser. Tests: `tests/test_ui_drive.py`.

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
rendered as a text-only PDF (`docx_kit.basic_pdf`). No OCR and no ghostscript pixel check there (fixes on third-party
evidence are refused rather than applied unverified).

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
