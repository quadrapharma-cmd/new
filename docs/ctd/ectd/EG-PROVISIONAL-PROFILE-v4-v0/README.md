# EG provisional regional profile v0 for eCTD v4.0

> **STATUS: PROVISIONAL — v0 — NOT ISSUED, ENDORSED OR REVIEWED BY THE EGYPTIAN DRUG AUTHORITY (EDA).**
> EDA has published **no** eCTD v4.0 regional (Module 1) package. Both EDA texts available to us are eCTD **v3.2.2**
> drafts: the *EG Module 1 eCTD Specification* DRAFT v1.0 (2026) targets v3.2.2 (SPEC p.13 l.236–237), and the draft
> *Technical Guidance for eCTD Submissions in Egypt* v1.0/2026 never mentions v4 (full-text search of all 75 pages for
> "v4", "4.0", "version 4": no hit; it cites "ICH eCTD specification 3.2.2", TG p.26 l.694–696).
> The statement that EDA will implement full eCTD v4.0 by Q1 2028 comes from the request brief (via
> `../ICH-eCTD-4.0-reference.md` header); it was **not** verified against an EDA document here.
>
> Owner's instruction: *complete what is missing using the EU model.* This profile does exactly that, and marks every
> item with where it came from. It is a planning and tooling baseline (generator / validator design, gap list for EDA),
> **not** something a submission can rely on. Every regional OID in it is a deliberately invalid placeholder.

Prepared 2026-11-06. Nothing here is from memory: every rule cites the ICH IG section, the EU IG heading, or the EG draft
page/line. Where the sources are silent the item is tagged **ASSUMPTION** and listed as a gap.

## 1. Contents

| File | What it is |
|---|---|
| `README.md` | This file: status, provenance tags, sources, OID placeholder plan, how EDA would register real OIDs, gap list |
| `cv/eg-m1-context-of-use.yaml` | **151** EG regional Context-of-Use codes, one per EG Module 1 element of SPEC Appendix 2 (1.0, 1.2.x, 1.3.x … 1.10, responses, additional data), with display name, parent, whether documents are allowed, allowed/required keyword types, the v3.2.2 element/folder/file pattern it maps from, and EU equivalents where the EU IG prints one |
| `cv/eg-submission-units.yaml` | 7 submission-unit types (TG Annex 6) |
| `cv/eg-submission-types.yaml` | 50 submission (regulatory-activity) types from TG Annex 6, with administration and the list of types that need a mode |
| `cv/eg-application-types.yaml` | Application types (EU-derived, anchored to EG M1 1.5 headings) **plus** the small related lists: mode, registration type, marketing type, territorial authority, territory, contact-party role, organisation-id namespace |
| `cv/eg-keyword-definitions.yaml` | EG keyword vocabularies (EG document type, language, country), the regional keyword-definition-type decision, which ICH keyword-definition types may be used in EG M1, and where each v3.2.2 envelope/leaf attribute (registration type, marketing type, product, manufacturer, INN, language…) goes in v4 |
| `rules.md` | EG regional v4 rules: folder/sequence naming, which ICH rules apply, regional rules adapted from the EU v4 IG, envelope → v4 class mapping |
| `migration.md` | eCTD v3.2.2 (EG draft) → v4.0 forward-compatibility mapping, leaf → document/CoU, all 151 M1 elements |
| `examples/1/` | Sequence 1 of a **fictional** product (initial MAA, generic, "Exemplofen 400 mg film-coated tablets"): `submissionunit.xml`, `sha256.txt`, six placeholder PDFs |
| `examples/check_example.py` | Re-runnable check: ICH XSD + a subset of ICH eCTD4 rules + the EG-V4 rules, driven by the YAML files |
| `examples/validation-result.md` | Recorded validation result |
| `tools/` | Generators for the YAML files and the example (`gen_cv.py`, `gen_example.py`, `rows.json`) |

## 2. Provenance tags (used on every rule and code)

| Tag | Meaning |
|---|---|
| **ICH** | Taken from the ICH eCTD v4.0 IG v1.7 (5 May 2026), the ICH CV package v1.0.3 (May 2026), the Q&A v1.10, or the M8 vendor minutes of 30 Sep 2026. Binding in every ICH region. |
| **EU-DERIVED** | Copied in principle from the EU eCTD v4.0 Module 1 IG, *DRAFT for updates 2024, v1.2 (Oct 2024)* (`docs/ctd/sources/ectd/EU_eCTD_v4.0_IG_draft_1.2_2024.docx`, cited by heading name because its headings are unnumbered), and adapted to Egypt. |
| **EG-DRAFT** | Taken from EDA's v3.2.2 drafts: **SPEC** = EG Module 1 eCTD Specification DRAFT v1.0 (cited by page / margin line / Appendix 2 row, via `../EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md`); **TG** = EDA draft Technical Guidance for eCTD Submissions in Egypt v1.0/2026 (cited by PDF page / margin line). |
| **ASSUMPTION** | Not stated by any source; a design decision made here so that the profile is complete. Each one is a question for EDA. |

## 3. Sources actually used

| Short cite | File | Version |
|---|---|---|
| IG | `docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip` → `ICH_eCTDv4_0_ImplementationGuide_v1_7.pdf` + `ICH_eCTD_v4_SchemaFiles/` | IG v1.7, 5 May 2026; RPS R2 schemas |
| CV | `docs/ctd/sources/ectd/ICH_eCTD_v4.0_CV_Package_v1.0.3.zip` → `ICH_eCTDv4_0_CV_v7.xlsx` + genericode | CV package v1.0.3 |
| KB4 | `docs/ctd/ectd/ICH-eCTD-4.0-reference.md` (rules eCTD4-001…085, QA, CRs, VEN minutes) | 2026-11-06 |
| EU-IG | `docs/ctd/sources/ectd/EU_eCTD_v4.0_IG_draft_1.2_2024.docx` (read with python-docx) | v1.2 draft, Oct 2024, OID `2.16.840.1.113883.3.989.5.1.1.6.1.2` |
| SPEC | `docs/ctd/ectd/EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md` (Appendix 2 parsed: 185 rows) | EG draft v1.0, 2026 (consultation 02/09–14/10/2026 per brief) |
| TG | `ectd_draft_2026.pdf` / `.clean.txt` (scratchpad copy of the EDA draft TG; Annex 5 = p.55–58, Annex 6 = p.59–74). Italic (folder-only) rows of Annex 5 were detected from the PDF font `TimesNewRomanPS-ItalicMT`. | TG v1.0/2026 draft |

## 4. OID placeholders — read this before using any code

ICH: "Code systems managed by regions or external organisations will have a registered OID" (IG §4.5.1); every regional
list is identified by an OID in `codeSystem` (IG §6.2), and the header must carry the OID of the Regional/M1 IG
(IG §9.1.2; rule eCTD4-084, CR 00770). EDA has none of these yet.

**Placeholder root used everywhere:** `2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER`

It is deliberately **not** an OID: `x` and `EG-PLACEHOLDER` are not numeric arcs. It passes the XSD only because the
schema types `codeSystem` and `root` as plain strings (`Uid` = `xsd:string`, `hl7-r2_datatypes.xsd` l.370–372). It
**fails** the ICH business rules that require a valid, registered OID (eCTD4-008/009, -031, -081, -083, -084) — and it
must, so that nobody can mistake it for a real EDA value. Do not shorten it, do not replace `x` by a number on your own.

The arc layout below only mirrors the published patterns, so EDA can see what would be needed:

| Placeholder | Stands for | Pattern copied from |
|---|---|---|
| `…EG-PLACEHOLDER` | EDA regional root | EU root `2.16.840.1.113883.3.989.5.1.1` = ich-estri(989).regional-specialised(5).sub-reg(1).eu(1) (EU-IG "CONTROLLED VOCABULARIES"); the IG §9.2.14 sample shows a US-style arc `2.16.840.1.113883.3.989.5.1.2…` |
| `…EG-PLACEHOLDER.6.1.0` | EG M1 IG (this profile, v0) — 2nd header `receiver/device/id/item@root` | EU `…5.1.1.6.1.2` = dossier management(6).M1 IG(1).version(2) |
| `…EG-PLACEHOLDER.6.2.0` | EG M1 CV package v0 | EU `…5.1.1.6.2.1` "EU M1 Controlled vocabularies v1.0" |
| `…EG-PLACEHOLDER.1.<n>.0` | EG code list *n*, version 0 | ICH `2.16.840.1.113883.3.989.2.2.1.x.y` (code-lists.x value set.y version; IG §4.5.1) |

| n | Code list | File |
|---|---|---|
| 1 | EG Context of Use (M1) | `cv/eg-m1-context-of-use.yaml` |
| 2 | EG Submission Unit Type | `cv/eg-submission-units.yaml` |
| 3 | EG Submission Type | `cv/eg-submission-types.yaml` |
| 4 | EG Application Type | `cv/eg-application-types.yaml` |
| 5 | EG Submission Mode | `cv/eg-application-types.yaml` → `related_lists.mode` |
| 6 | EG Registration Type | idem → `registration_type` |
| 7 | EG Marketing Type | idem → `marketing_type` |
| 8 | EG Keyword Definition Type (empty in v0) | `cv/eg-keyword-definitions.yaml` |
| 9 | EG Document Type (keyword) | idem |
| 10 | EG Language (constrained ISO 639-1: ar, en) | idem |
| 11 | EG Country / Territory (constrained ISO 3166-1: eg) | idem + application types file |
| 12 | EG Territorial Authority (EG-EDA) | `cv/eg-application-types.yaml` |
| 13 | EG Contact Party Role | idem |
| 14 | EDA portal organisation-identifier namespace | idem |

The version arc `.0` means "provisional"; per IG §6.6 the first issued EDA version would get its own version OID, and
any later removal/replacement of codes needs a new version OID and end dates (IG §6.6.1–6.6.2.3, rule eCTD4-079).

### 4.1 What EDA would have to do to make this real (what the sources say, nothing more)

1. **Obtain a registered root OID** for EDA's regional eCTD v4 artefacts. The sources show two precedents only:
   the EU root sits under the ICH ESTRI "regional-specialised" arc and is "registered on the HL7 registry"
   (EU-IG "CONTROLLED VOCABULARIES"); the IG uses `2.16.840.1.113883.3.989.5.1.2…` for a US-style example (IG §9.2.14).
   The sources do **not** describe the application procedure; EDA would have to ask ICH M8 / HL7. Sponsors may pick
   any unique OID but **not** one already registered by an agency (VEN Open Discussion #3; IG §6.5.1) — so the EDA arc
   must exist before industry tools hard-code anything.
2. **Assign** under that root: one OID per M1 IG version (header item 2), one per CV package version, and one
   *version* OID per code list (pattern of IG §4.5.1; EU-IG "CONTROLLED VOCABULARIES").
3. **Publish** each list as spreadsheet + OASIS genericode, versioned like ICH (IG §6, §6.6; EU-IG "Keywords and
   Controlled Vocabularies for EU Purpose": "The controlled vocabularies will follow the ICH model … xlsx and genericode").
4. **Ask ICH** (via M8 change request) for an Egyptian value in the "ICH XML Types" list if v3.2.2 EG regional leaves
   are to be referenced by Forward Compatibility (the list holds only `ich`, `us-regional`, `eu-regional`,
   `ca-regional`, `ch-regional`; KB4 §4.2, §7.2). See `migration.md` §2.
5. **Replace** every `2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER` string in these files and in generated messages by
   the assigned OIDs (a mechanical search-and-replace; codes keep their values unless EDA changes them).

## 5. Key design decisions (all flagged in the files)

| # | Decision | Tag | Where |
|---|---|---|---|
| D1 | One CoU per EG M1 element; codes `eg_<CTD no.>` (`eg_responses`, `eg_additional-data`), display "M1.x Title" | EU-DERIVED display; code pattern ASSUMPTION (EU uses opaque SPOR IDs) | `cv/eg-m1-context-of-use.yaml` |
| D2 | Folder-only headings (no documents): 1.2 and its italic sub-groups (TG Annex 5), 1.2.2 (printed non-italic — flagged), 1.3–1.8 parents | EG-DRAFT / ASSUMPTION | idem |
| D3 | 1.3.1 requires 3 keywords = the 3 mandatory `pi-doc` attributes (type, language, country) | EG-DRAFT + EU-DERIVED | idem; `rules.md` EG-V4-030 |
| D4 | Flat `m1/` folder, no `eg/`, no language/country folders, no `eg-regional.xml`, no util | EU-DERIVED + ICH | `rules.md` §2 |
| D5 | Registration type and marketing type carried as two `review/productCategory` codes | ASSUMPTION (no RPS class fits) | `rules.md` §6 |
| D6 | related-sequence disappears: SUs of one regulatory activity share `submission/id/@root`; EDA tracking number in `@extension` | EU-DERIVED | `rules.md` §1, §6 |
| D7 | Consolidation after withdrawal/rejection stays SU type `response` (EG), not EU `consolidating` | EG-DRAFT | `cv/eg-submission-units.yaml` |
| D8 | No regional keyword-definition type in v0 (EU's "strength" unnecessary: one EG application per strength) | ASSUMPTION | `cv/eg-keyword-definitions.yaml` |
| D9 | First-level folder = EDA application number lower-case without punctuation; until EDA defines one, the application UUID | EU-DERIVED / ASSUMPTION | `rules.md` EG-V4-001 |

## 6. Gaps — stated plainly

1. **No EDA v4 source at all.** Every regional value (OIDs, M1 CoU list, SU/submission/application types, folder naming,
   file formats, FC leaf-reference syntax, retention/reuse policy) is provisional.
2. **EDA v3.2.2 CVs are themselves unpublished**: Submission Type, Mode, Submission Unit, Registration Type and Marketing
   Type CVs are "on EDA's webpage" (TG p.27 l.715–724; TG p.28 l.754–759) but not in either draft. Submission types,
   modes and units here come from TG Annex 6; registration/marketing types only from 2–3 printed examples each.
3. **No EG application-type list** exists; ours is EU-derived from the EG M1 1.5 headings.
4. **No RPS class for "registration type" / "marketing type"** — D5 is a stop-gap.
5. **No EG contact-party, organisation register, substance list or file-format list** ("EG Accepted File Formats for
   eCTD" is referenced, SPEC p.6 l.14–15, TG p.14 l.325–328, but not published).
6. **EG drafts contradict each other** (agency code `EG-EDA` vs `EDA`; `var-pac-ii` spelled three ways; PI types;
   where supportive documents go) — inherited conflicts are listed in the YAML notes and `rules.md` §9.
7. **ICH open points** that affect any region: no `sha256.txt` byte format; first-SU sequence `1` vs `last+1` after
   v3.2.2 (IG §8.1 vs eCTD4-014); no baseline/transition message (TMM removed, CR 00710); UUID case-insensitivity
   clarification pending (VEN 2.3); `_$` validation pending (VEN 2.2).
8. **EU model is itself a 2024 draft** (v1.2); its M1 CoU list lives in SPOR-RMS and only three EU M1 codes are printed
   in the IG (`100000164029` M1.0 cover letter, `100000164030` application form [inferred from a sample comment],
   `100000164032` 1.3.1 SmPC/Label/PL).

## 7. How to regenerate

`tools/gen_cv.py` regenerates all `cv/*.yaml` from `tools/rows.json` (the 185 SPEC Appendix 2 rows parsed from
`../EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md` §6.2) plus the TG Annex 5/6 facts transcribed in the script with
their page cites: `python3 -I tools/gen_cv.py .`. `tools/gen_example.py .` rebuilds `examples/1` (fixed UUIDs; output is
byte-identical on re-run, checked 2026-11-06). The validation can be re-run with
`python3 -I examples/check_example.py examples/1 <path>/PORP_IN000001UV.xsd` (the XSD is in
`docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip`, folder `ICH_eCTD_v4_SchemaFiles/multicacheschemas/`).
