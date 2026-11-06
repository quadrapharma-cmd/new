# 01 — Build plan: «Dossier Builder for EDA» (working name)

Version 1.0 · 06/11/2026. This is a plan only; no app code exists yet.
Inputs:
- `../CTD-KNOWLEDGE-BASE.md`
- `../ECTD-KNOWLEDGE-BASE.md`
- `../ectd/*`
- `../checklist/EDA-eCTD-Company-Checklist.xlsx`
- `../data/EDA_VariationTool_2026-11-06.csv`
- `../APP-PLAN.md` (architecture draft)
- `../PRODUCT-DESCRIPTION.md`

## 0. Decisions assumed (owner may change any of them; each one is isolated in the design)

| # | Decision | Assumed | Where it is isolated |
|---|---|---|---|
| D1 | Deployment | **Local-first.** A desktop app (engine + UI on localhost), so files never leave the company. Optional team server mode later | Storage adapter (§LOGIC 2.6) |
| D2 | First output | **CTD One Submission** folder package (what EDA receives today), then eCTD 3.2.2, then eCTD 4.0 | Writer plug-ins (§LOGIC 9) |
| D3 | Users | Roles **Preparer / Reviewer / Approver / Viewer**. A single user may hold all roles | Permission matrix (§LOGIC 2.5) |
| D4 | Business model | **Sellable product**: multi-company workspaces and a licence key per workspace | Workspace layer (§LOGIC 2.1) |
| D5 | Code location | **A new repository** (`eda-dossier-builder`), not inside Drugbox. Drugbox's approved demo must not be touched (CLAUDE.md rule) | — |

## 1. Guiding principles (non-negotiable)

1. **Rules are data, never code.**
   - Every requirement, check, vocabulary and folder name lives in a versioned *rule pack* with a citation to its source (code, version, section, page).
   - A guideline change means a new rule pack, not a release.
2. **One data model, many outputs.** CTD, eCTD 3.2.2 and eCTD 4.0 are writers over the same dossier model.
3. **Third-party documents are read-only.**
   - The engine refuses any content edit to GMP certificates, CPPs, CEPs, EDA approvals, notarised agreements and executed records.
   - Only non-content technical fixes are allowed.
4. **Never claim «EDA-valid».** Until EDA publishes its validation criteria, reports say «conforms to EDA drafts + ICH»; the regional profile is marked *provisional*.
5. **Arabic is first-class:**
   - RTL layout;
   - Arabic documents generated through Word templates (correct shaping);
   - bilingual UI with English for CTD terms.
6. **Explainability.** Every red/amber status shows *why* (rule + source) and *what to do* (fix, rebuild, re-obtain).
7. **No silent data loss.** Every action is versioned and undoable; nothing is overwritten without a new version.

## 2. Phases

Each phase ends with a demo, its acceptance tests and a release note.

| Phase | Goal | Deliverables | Acceptance (all must pass) |
|---|---|---|---|
| **P0 Foundations** | Rule packs + data model + engine skeleton | • Rule-pack format (YAML + JSON schema) • Packs: `eda.ctd.nta065.v5`, `eda.ctd.nta065.v6-draft`, `eda.m1.subguid.v1-draft`, `eda.qm.v2-2023`, `eda.qm.rereg.gl039.v1`, `eda.qm.deficiencies.nta040.v1`, `eda.var.gl026.v6` + variation-tool data, `eda.var.sections.nta112.v1`, `ich.m4.r4`, `ich.ectd.322`, `eda.ectd.eg-m1.v1-draft`, `eg.profile.provisional.v0` • Profile → requirements resolver • Seed product «Examplol 500 mg FCT» | • The resolver reproduces the 91-row Excel checklist for the 3 dossier types (golden test) • Every rule carries a source citation (lint) • Pack switch v5 ↔ v6-draft changes the M1 list exactly as the v6 diff |
| **P1 MVP — CTD One Submission** | A company can prepare and export today's dossier | • Workspace, product wizard, requirement board • Upload and auto-classify • PDF technical checks • Generator: Annex I + Arabic undertaking, composition certificate, salt calculation, CEP commitment, stability commitments, translation declaration, unavailable-data justification, cover letter, tracking table • Export CTD folder package (NP.CAPP.065 numbering) + readiness report | • End-to-end on the seed product in < 30 min by a new user • All generated Arabic text renders correctly (visual test) • Third-party document edit is impossible (negative test) • Export opens and is navigable offline (index.html) |
| **P2 Quality intelligence** | Find what EDA would reject | • Structured M3 data entry: specifications, batches, stability, methods • Generators: M3 tables, 3.2.R.2 method/validation summaries, QOS (innovators) • NP.CAPP.040 deficiency checks • Cross-document checks (CPP↔P.3.1, composition↔CPP, spec↔batch, CEP validity) • Re-registration relaxations (GL.CAPP.039) | • A seeded «bad» dossier triggers ≥ 90% of the NP.CAPP.040 items present in it • No false «Conforming» on the 30-case deficiency test set |
| **P3 Variations** | A variation file from a variation name | • Variation picker (EDA tool data + v6) • PAC class, grouping rule (highest class wins) • CTD sections (NP.CAPP.112) • Required studies and documents • Variation form + declarations (M1 guidance Annex 3) | • For all 90 human variations: correct PAC + sections (table test) • Grouped PAC-B + PAC-II yields PAC-II |
| **P4 eCTD 3.2.2** | eCTD sequences | • ICH folder writer (Appendix 4) • `index.xml` (DTD-valid) + MD5 • `eg-regional.xml` from the provisional EG profile • Sequences, related sequence, lifecycle (new/replace/delete; no append), baseline/reformat • Working-documents folder • Internal validator: ICH + EG draft rules + EU-derived rules, each flagged by origin | • `index.xml` validates against the ICH DTD • EMA example sequences parse • Lifecycle golden tests (replace chain, delete, misplaced leaf fix) • Path ≤ 180 and name ≤ 64 enforced • When EDA publishes the DTD and criteria, only the profile pack changes |
| **P5 eCTD 4.0** | Ready for Q1 2028 | `submissionunit.xml` (HL7 RPS), SHA-256, context-of-use from ICH CV v1.0.3, keywords, document reuse, forward compatibility from 3.2.2 | XSD-valid messages; conversion of a P4 dossier |
| **P6 Team and commercial** | Sell it | Team server mode, roles/approvals, audit trail, licence keys, backups, Drugbox account link (optional) | Security review; restore drill |

**Order of work inside every phase:**
1. Rule-pack data.
2. Engine logic with unit tests.
3. API.
4. UI.
5. End-to-end tests.
6. Arabic visual review.
7. Release note.

## 3. Test strategy

| Layer | What | Pass criterion |
|---|---|---|
| Rule packs | Schema validation; citation lint; no orphan requirement | 100% |
| Resolver | Golden tables: Excel checklist (3 types × new/re-reg × One/Rolling); v6 diff | Exact match |
| Checks | Fixture PDFs (1.3, encrypted, scanned without OCR, portfolio, long name, unicode name, 0-byte, corrupt) | Each rule fires on its fixture and not on clean files |
| Generators | Snapshot tests (EN/AR), Arabic shaping check, field completeness | No missing field; snapshot stable |
| Writers | DTD/XSD validation; MD5/SHA-256; path limits; re-import round-trip | Valid; round-trip identical |
| End-to-end | 12 scripted journeys (see `03-UX.md` §6) in Playwright, AR + EN, desktop + 1280px | All pass |
| Non-functional | 3 GB dossier, 2,000 files: open < 3 s, check < 2 min, export < 5 min on a mid laptop | Within budget |

## 4. Risks and mitigations

| Risk | Mitigation |
|---|---|
| EG DTD, validation criteria and Registration/Marketing Type lists unpublished | `eg.profile.provisional.v0` isolated. Every output is labelled. Early test through the EDA portal's automatic technical validation (TG draft §2.9.11) or a partner with EXTEDO EURSvalidator |
| Drafts change at adoption (NP.CAPP.065 v6, M1 guidance, eCTD TG/spec) | Draft and in-force packs coexist; the user picks the pack per dossier; diff report between packs |
| Arabic rendering in PDFs | Word templates → LibreOffice → PDF; visual regression tests |
| Users edit third-party evidence | Engine-level read-only flag on the document class; only non-content operations are allowed |
| Large files and performance | Streaming hashing; background workers; incremental re-checks |
| Rolling Submission closes 01/12/2026 | The Rolling pathway ships only as «legacy view», not as a creation option |

## 5. Definition of done (every feature)

- Rule pack updated, with citations.
- Unit and end-to-end tests pass in AR and EN.
- Every error state has a message, a reason and an action.
- Keyboard accessible; contrast meets WCAG AA.
- Documented in the user help, both languages.
- Measured performance stays within budget.
