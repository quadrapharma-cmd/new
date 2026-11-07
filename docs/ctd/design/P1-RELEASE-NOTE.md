# P0 + P1 release note — Dossier Builder for EDA

06/11/2026 · code at `apps/dossier-builder/`, branch `claude/new-session-8nmyo7`.
The code lives inside the Drugbox repository until the separate repository exists (decision D5). It touches nothing in Drugbox.

## 1. What the release does

One product profile → requirements board → documents (uploaded, checked, or generated) → three outputs from the same data:
- **CTD One Submission package**: NP.CAPP.065 v5 numbering, bilingual navigator and checklist.
- **eCTD 3.2.2**: `index.xml` + `m1/eg/eg-regional.xml` + MD5 + `util`.
- **eCTD 4.0**: `submissionunit.xml` + SHA-256.

Run it with `python3 apps/dossier-builder/tools/serve.py`, then open `http://127.0.0.1:8765/`. The interface is Arabic first; English is one click away.

## 2. Acceptance criteria (01-PLAN §2)

| Phase | Criterion | Status | Evidence |
|---|---|---|---|
| P0 | The resolver reproduces the Excel checklist for the 3 dossier types | ✅ | `tests/test_pack_vs_checklist.py`: same 101 ids, titles and matrix cells (verbatim); unconditional items equal the matrix for I / G-Imp / G-Loc |
| P0 | Every rule carries a source and a provenance tag | ✅ | `tests/test_pack_lint.py` (JSON Schema + citation lint); eCTD placement tagged ICH / EG-DRAFT / ASSUMPTION |
| P0 | The provisional DTD and XSD examples validate | ✅ | `xmllint --valid` on the 3.2.2 example; `xmllint --schema` (ICH XSD) on the 4.0 example |
| P1 | One seed dossier exports to all three; `index.xml` DTD-valid, `eg-regional.xml` valid against the provisional DTD, `submissionunit.xml` XSD-valid | ✅ | `tests/test_e2e_seed.py`, `tools/export_demo.py`, and `apps/dossier-builder/examples/examplol-three-outputs-demo.zip` |
| P1 | Name ≤ 64 and path ≤ 180 enforced in the eCTD outputs | ✅ | `test_writer_ectd32.py::test_path_limit`, the eCTD4-065/066/067 checks in the 4.0 writer, `test_layout` |
| P1 | End to end in < 30 min by a new user | ⏳ | Needs a real user. The Playwright journey (wizard → upload → check → export gate) runs in about 2 s of automation |
| P1 | Third-party content edit impossible (negative test) | ✅ | `test_checks_pdf.py::test_locked_content_edit_impossible` (20 cases), plus the same check through the API and the UI (`E-LOCKED`, audit event) |
| P1 | Arabic generated text renders correctly | ✅ technical / ⏳ owner review | Word with real RTL → LibreOffice PDF; `pdftotext` returns the Arabic words in the right order; I checked the page images visually. The owner's own review is still to come |

**Tests:** 158 automated tests, all passing:
- engine and writers;
- checks and lock;
- generators;
- API (including concurrency);
- 5 browser journeys (Arabic and English, desktop and phone width).

## 3. Delivered against the P1 list

| Plan deliverable | Delivered |
|---|---|
| Workspace, product wizard, requirements board | ✅ Local workspace (SQLite + content-addressed files). Four-step wizard. Board with status, filters, and a «why?» drawer giving the reason and source |
| Upload, auto-classify, PDF technical checks | ✅ Upload with an instant check. Batch auto-classify (CTD number, Arabic/English keywords, first page; no guess without evidence). Checks: version, security, corruption, Portfolio, JavaScript, searchable text by document class, name length |
| Generators | ✅ Annex I + the Arabic undertaking (from the source text, with conditional clauses), composition, salt calculation, CEP commitment, stability commitment, translation declaration, justification, cover letter, tracking table. Each is prefilled from the dossier; missing data is asked for, never guessed |
| Writer 1 CTD | ✅ |
| Writer 2 eCTD 3.2.2 | ✅ |
| Writer 3 eCTD 4.0 | ✅ |
| Internal validator per output | ✅ It reads the output back from disk. **3.2.2:** 91/141 profile rules automated (the rest are «not run» with the reason). **4.0:** XSD, SHA-256, references, unassociated files, context of use, keywords, EG headings. Report in Arabic/English with every export. The validator caught a real defect in our own demo — the tracking table was named `cover-2.pdf` (EG-PF-15.11/15.12) — and it is fixed |
| Export gate + «provisional profile» acknowledgement | ✅ Export stops if a required item is missing or a document is non-conforming, and stops if the eCTD acknowledgement is not given |
| **Publisher view (owner request: like EXTEDO)** | ✅ Section tree → documents → properties. Switch CTD / 3.2.2 / 4.0 with a live preview; drag files onto sections |

## 4. Defects found and fixed during the build

All were found by the tests:
- **Required ICH DTD attribute:** `indication` on `m5-3-5` / `m2-7-3` is required by the DTD; now handled.
- **Concurrent requests:** two parallel requests broke the store; it now uses one connection per thread + WAL.
- **CTD path length:** the length limit was exceeded; file names now fit the remaining path budget.
- **«32p51» naming:** misread; now parsed correctly.
- **Lists in generator forms:** an empty list disappeared from the form; fixed.
- **Arabic layout:** the version label and Latin text inside Arabic fields were broken; fixed.
- **Two profiles out of step:** the registration and marketing types in the 3.2.2 and 4.0 profiles did not match; they are now aligned (6 + 4, from the M1 guidance draft).

## 5. Still open (none of it blocks the next phase)

**Waiting on the owner:**
1. Try the app on a real product (the 30-minute criterion).
2. Review the Arabic in the generated files.
3. Check the transcribed Annex I text against the official EDA form (`templates/annex1.yaml` → `transcription_check: pending`).
4. The company letterhead.

**Waiting on EDA:**
- the EG DTD;
- the validation criteria;
- the code lists (registration / marketing types, the EG-EDA vs EDA agency code);
- the v4 OIDs.

Until then the eCTD outputs say «conforms to EDA drafts + ICH», never «EDA-valid». P4 swaps the profile packs only.

**Engineering:**
- Automate the remaining 3.2.2 rules (lifecycle across sequences — arrives with P3 — plus links and bookmarks inside PDFs).
- ~~Automatic fixes~~ ✅ done 07/11/2026: version, security, JavaScript, OCR, with a pixel guard on evidence; issuer request letter + «waiting» status; signed-scan linking + gate on unsigned drafts. Bookmarks too (from the numbered headings) and an Arabic OCR test on a real scan.
- Roles and approvals (P5).

## 6. Next phase (P2: quality intelligence)

Structured Module 3 data (specifications, batches, stability, methods) → automatic tables in M3 and 3.2.R.2. Also: the QOS, the NP.CAPP.040 checks, cross-document checks (the 11 in the Excel), and the re-registration relaxations (GL.CAPP.039).
