# 01 — Build plan: «Dossier Builder for EDA» (working name)

Version 1.1 · 06/11/2026. **Status: P0 and P1 built and tested** (`apps/dossier-builder/`, 140 tests). See `P1-RELEASE-NOTE.md` for each acceptance criterion and what is still open.
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
| D2 | Outputs | **All three from the first release (owner decision 06/11/2026):** CTD One Submission package, **eCTD 3.2.2** and **eCTD 4.0**, generated from the same dossier. Gaps EDA has not published are completed from the EU model as a **provisional EG profile** (`../ectd/EG-PROVISIONAL-PROFILE-v0/`, `../ectd/EG-PROVISIONAL-PROFILE-v4-v0/`) | Writer plug-ins (§LOGIC 9) + profile packs |
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

**The three outputs ship together in P1 (owner decision 06/11/2026).** P2–P4 deepen what all three writers carry.

| Phase | Goal | Deliverables | Acceptance (all must pass) |
|---|---|---|---|
| **P0 Foundations** | Rule packs, data model, engine skeleton, regional profiles | • Rule-pack format (YAML + JSON schema) • EDA content packs: NP.CAPP.065 v5 / v6-draft, M1 Submission Guidance draft, QM v2, GL.CAPP.039, NP.CAPP.040, NP.CAPP.112, GL.CAPP.026 v6 + EDA variation-tool data • ICH packs: M4(R4), eCTD 3.2.2 (DTD, App. 4), eCTD 4.0 (XSD, CV 1.0.3) • **EG provisional regional profiles**: v3.2.2 (`eg-regional.dtd`, `eg-envelope.mod`, `eg-leaf.mod`, CV lists, validation criteria mapped from EU VC 8.2 + EG drafts) and v4.0 (M1 context-of-use list, keywords, placeholder OIDs) • Profile → requirements resolver • Seed product «Examplol 500 mg FCT» | • The resolver reproduces the 91-row Excel checklist for the 3 dossier types • Every rule carries a source and a provenance tag (EG-DRAFT / EU-DERIVED / ICH / ASSUMPTION) • The provisional DTD and XSD examples validate |
| **P1 MVP: three outputs** | A company prepares a dossier once and exports **CTD, eCTD 3.2.2 and eCTD 4.0** | • Workspace, product wizard, requirements board • Upload, auto-classify, PDF technical checks • Generators: Annex I + Arabic undertaking, composition, salt calculation, CEP commitment, stability commitments, translation declaration, justification, cover letter, tracking table • **Writer 1 CTD** (NP.CAPP.065 numbering + navigator) • **Writer 2 eCTD 3.2.2**: ICH folders, `index.xml` + MD5, `m1/eg/eg-regional.xml`, util/dtd, sequence 0000, working-documents folder • **Writer 3 eCTD 4.0**: `submissionunit.xml` + SHA-256, context-of-use, keywords, UUID document reuse • Internal validator per output (ICH + EG draft + EU-derived rules, each tagged) • Export gate + «provisional profile» acknowledgement | • One seed dossier exports to all three; `index.xml` is DTD-valid, `eg-regional.xml` valid against the provisional DTD, `submissionunit.xml` XSD-valid • Name ≤ 64 and path ≤ 180 enforced in eCTD outputs • End-to-end in < 30 min by a new user • Third-party content edit impossible (negative test) • Arabic generated text renders correctly |
| **P2 Quality intelligence** | Find what EDA would reject | M3 structured data (specs, batches, stability, methods), M3 tables, 3.2.R.2 summaries, QOS, NP.CAPP.040 checks, cross-document checks, re-registration relaxations | A seeded «bad» dossier triggers ≥ 90% of its NP.CAPP.040 items; no false «Conforming» on 30 cases |
| **P3 Lifecycle and variations** | Follow-on sequences in all three outputs | Variation picker (PAC, grouping, NP.CAPP.112 sections), response sequences, baseline/reformat, replace/delete (3.2.2), context-of-use replace/suspend (4.0), 3.2.2 → 4.0 forward compatibility, tracking table | 90 human variations give correct PAC + sections; lifecycle golden tests in both eCTD versions |
| **P4 Swap to official EG files** | When EDA publishes the DTD, criteria and CV | Replace the provisional profiles with official packs; diff report; re-validate stored sequences | Only the profile packs change; no engine change |
| **P5 Team and commercial** | Sell it | Team server mode, roles and approvals, audit, licences, backups, optional Drugbox account link | Security review; restore drill |

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
