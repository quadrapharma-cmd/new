# EG provisional regional rules for eCTD v4.0 — v0

> **PROVISIONAL — not issued by EDA.** See `README.md` for status, sources and the OID placeholder
> `2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER`. Tags: **ICH**, **EU-DERIVED**, **EG-DRAFT**, **ASSUMPTION**.
> Cites: IG = ICH eCTD v4.0 IG v1.7 §; eCTD4-NNN = ICH rule (IG §12); QA/CR/VEN = ICH Q&A v1.10, change requests, M8 vendor
> minutes 30 Sep 2026 (via `../ICH-eCTD-4.0-reference.md`); EU-IG "heading" = EU v4 M1 IG draft v1.2; SPEC p./l./row =
> EG M1 Spec draft v1.0; TG p./l. = EDA draft Technical Guidance v1.0/2026.
>
> Rule IDs `EG-V4-NNN` are this profile's own. Severity: **R** = reject (technical validation failure), **W** = warning /
> best practice. ICH rules are always R (IG §12; EU-IG "XML MESSAGE VALIDATION RULES": "The principles of validation rules
> for eCTD v4.0 messages will not differ between regions").

## 1. The three layers in Egypt (application ⊃ submission ⊃ submission unit)

| Layer | EG meaning | v4 element | Identifier rule | Tag / source |
|---|---|---|---|---|
| Application | One EG eCTD lifecycle = one product, **one strength / dosage form** ("For products with different dosage forms and strengths are submitted under separate applications") | `submission/componentOf/application` | `id/item@root` = application UUID; for a converted v3.2.2 dossier **the v3.2.2 envelope `identifier` UUID is kept**. `@extension` = EDA registration/application number once EDA defines one (else omitted). `code` from `eg-application-type` | EG-DRAFT SPEC Glossary p.3–4, App.1.1 E3 p.14; EU-DERIVED EU-IG "Application" ("Root reflects the UUID introduced in eCTD v3.2.2"); ASSUMPTION for `@extension` |
| Submission | One regulatory activity (MAA, a variation, renewal, PMF, …) | `submissionUnit/componentOf1/submission` | `id/item@root` = **one UUID for the whole activity**, unchanged in every SU of that activity; exactly one `item`; `@extension` = the EDA procedure tracking number (e.g. `P-VAR-PAC-N-0002`); `code` from `eg-submission-type` | EU-DERIVED EU-IG "Submission" (root changes only for a new activity; one item; extension = procedure number); EG-DRAFT SPEC p.17 (tracking numbers); IG Table 11, eCTD4-033/077 |
| Submission unit | One sequence | `submissionUnit` | `id@root` new UUID per SU; `code` from `eg-submission-unit`; `statusCode` only `active`; `title` = the v3.2.2 *submission-description* text | ICH IG §9.2.4, eCTD4-003/004/010; EU-IG "Sequence Number" ("The title element can be completed as currently done for submission description"); EG-DRAFT SPEC p.19–20 E17 |

Consequence: the v3.2.2 *related-sequence* element (SPEC p.19 E16, p.21 l.246–262) has **no v4 element**. The link
"this sequence belongs to the activity started in sequence N" is expressed by re-using that activity's
`submission/id/@root`. A response that serves two activities (SPEC p.21 l.258–260: one response to sequences 0050 and
0060) repeats `componentOf1` once per submission, with the same `sequenceNumber` in each (IG Table 11 allows 1..*;
eCTD4-016 one value per submission). **ASSUMPTION** — the EU allows several submissions in one SU only for grouped
variations / worksharing (EU-IG "Submission").

## 2. Folder, file and sequence rules

| ID | Rule | Sev. | Tag / source |
|---|---|---|---|
| EG-V4-001 | **First-level folder** = the EDA application number, lower case, punctuation removed (EU pattern `ema000123`, `de2087`). Until EDA defines an application number, use the application UUID in lower case. A grouped transmission (see §8) is named by the high-level number, lower case, punctuation removed (e.g. `b-gv-0001` → `bgv0001`). | W | ICH IG §5.1 (first level "defined regionally"); EU-DERIVED EU-IG "First Level Folder Naming Recommendation"; ASSUMPTION for the UUID fallback and the EG grouping name |
| EG-V4-002 | **Second-level folder** = `sequenceNumber` value, whole number 1–999999, **no zero padding** (`1`, `2`, `27`). The v3.2.2 `DDDD` 4-digit form (SPEC p.28; TG p.16 l.392) is not used in v4. | R | ICH IG §5.1, §9.2.12, eCTD4-013; EU-IG "Second Level Folder Naming Requirements" |
| EG-V4-003 | First v4 SU of a **new** application = `1` (eCTD4-014; EU-IG). First v4 SU of an application **converted from v3.2.2** = last v3.2.2 number + 1 as a whole number (after `0007` comes `8`) (IG §8.1). | R | ICH (conflict IG §8.1 vs eCTD4-014 flagged in KB4 §8; reading adopted: `1` only for applications that start in v4) |
| EG-V4-004 | After a **technical** rejection re-send with the **same** sequence number; after a **content** finding send a **new** sequence number. | R | ICH IG §12.2 (resubmit with same number); EG-DRAFT TG p.16 l.399–404, TG p.24 l.569–572 |
| EG-V4-005 | Sequence numbers should follow submission order (out-of-order receipt tolerated). | W | EG-DRAFT TG p.16 l.384–389 |
| EG-V4-006 | Sequence folder content: `submissionunit.xml` (exact lower-case name), `sha256.txt` (64 lower-case hex digits, SHA-256 of `submissionunit.xml`; no file name; no trailing newline recommended), `m1`…`m5` only when they hold files. No empty folders. | R | ICH IG §5.1, §5.6; eCTD4-059/060/061/062/063; byte format of sha256.txt = **ASSUMPTION** (IG gap, KB4 §2.2) |
| EG-V4-007 | **Module 1 is one flat folder `m1/`.** No `m1/eg/`, no section folders (`10-cover`, `12-form/122-legal/…`), no language (`ar`/`en`) or country folders: heading = CoU code, language = `text@language` + keyword, country = keyword. | W (structure is not validated by ICH) | EU-DERIVED EU-IG "Folder Hierarchy" ("Module 1 will be a single folder with no additional folder structure") and "Naming Conventions"; ICH IG §5.1; replaces SPEC App.2 folders and SPEC p.9 l.97–105 |
| EG-V4-008 | M2–M5 folders as ICH (`m2` flat; `m3/32-sub`, `32-prod`, …). | W | ICH IG §11 |
| EG-V4-009 | File names: lower case; one extension of 3–4 characters; only a–z, 0–9 and `$ - _ + ! ' ( )`; keep the EG fixed components as the start of the name (`cover-…`, `tracking-…`, `form-af-…`, `spc-…`, `pl-…`, `mockup-…`, `responses-<activity>-<n>-<content>.pdf`, `additionaldata-…`) because the folder no longer tells the reader what a file is. | R (characters, case) / W (fixed components) | ICH IG §5.2, §5.2.1 Table 5, eCTD4-074; EG-DRAFT SPEC p.10–11 l.148–178 (FIXED-VAR.EXT), App.2 rows 4–179 |
| EG-V4-010 | Lengths: file name ≤ 64, folder name ≤ 64, path ≤ **180 counted from the first-level folder** (ICH counting). The EG v3.2.2 rule counted from the first digit of the sequence folder (SPEC p.11 l.180–183; TG p.12 l.275–277); in v4 the stricter ICH counting applies. | R | ICH IG §5.2.2, eCTD4-065/066/067 |
| EG-V4-011 | No `util/` folder, no DTD, no style sheet, no `eg-regional.xml`, no `index.xml`, no `md5.txt`. | R (any such file is an unassociated file, eCTD4-069) | ICH IG §5.1; EU-IG "Submission Unit Content in eCTD v4.0 Messages"; replaces SPEC App.2 rows 2, 180–183 |
| EG-V4-012 | **Working documents** (e.g. Word versions requested by EDA) stay **outside** the sequence folder, as a sibling `<seq>-workingdocuments/` in the same upload (e.g. `1/` and `1-workingdocuments/`). | W | EG-DRAFT SPEC Glossary "Working Documents" p.4–5; TG p.14 l.332–337; ICH eCTD4-069 (every file inside m1–m5 must be referenced) — placement = ASSUMPTION |
| EG-V4-013 | File formats: PDF 1.4–1.7, PDF/A-1, PDF/A-2 unless EDA requires otherwise; other formats only per the (unpublished) "EG Accepted File Formats for eCTD"; `text@mediaType` must be given for any non-PDF file. No archives in M2–M5. | R | EG-DRAFT SPEC p.6 l.10–15, TG p.14 l.319–331; ICH IG §5.5, §5.7; EU-DERIVED EU-IG "Document" ("text@mediaType should be provided if there is a special file format") |
| EG-V4-014 | No file-level security, passwords or restrictions; no electronic signatures required. | R | EG-DRAFT TG p.24 l.579–591 |
| EG-V4-015 | Transport: upload the zipped first-level folder through the EDA portal. | W | EG-DRAFT TG p.26 l.685–691 (portal); zip of the transport package is outside ICH IG §5.7 (which forbids archives *inside* M2–M5) |

## 3. Which ICH rules apply

**All ICH rules eCTD4-001 … eCTD4-085 of IG v1.7 §12 apply unchanged** (listed in `../ICH-eCTD-4.0-reference.md` §6).
The ones whose *content* depends on this regional profile:

| ICH rule | What the EG profile supplies | Status in v0 |
|---|---|---|
| eCTD4-006/007, -008/009 | SU code from `eg-submission-unit`; codeSystem = EG list OID | codes ready; OID **placeholder → fails -008/-009** |
| eCTD4-034…037 | Submission code from `eg-submission-type` | same |
| eCTD4-038…042 | Application id + code from `eg-application-type` | same |
| eCTD4-075, -081 | M1 CoU code valid in `eg-context-of-use` | same |
| eCTD4-070, -071, -072 | Required / allowed keyword types per EG CoU (`keyword_types` in the CoU YAML) | defined |
| eCTD4-031, -032, -083 | EG keyword code systems (document type, language, country) | placeholder OIDs |
| eCTD4-084 | Header item 2 = EG M1 IG OID (`…EG-PLACEHOLDER.6.1.0`) | placeholder → fails |
| eCTD4-026 | "or region does not allow it" — EG allows replacing active v3.2.2 leaves through FC | ASSUMPTION (see `migration.md`) |
| eCTD4-065/066/067 | EG keeps the ICH limits (no tighter regional limit) | EG-V4-010 |
| eCTD4-069 | No regional exception: working documents must be outside the sequence folder | EG-V4-012 |
| eCTD4-079 | EG lists versioned per IG §6.6; retired codes rejected | process for EDA |
| eCTD4-025/076/078/080 (FC) | Leaf-reference syntax for EG v3.2.2 content | **blocked**: no EG value in "ICH XML Types" (see `migration.md` §2) |

ICH items the profile simply follows: UUIDs everywhere (`id@root`), compared case-insensitively (VEN 2.3); `priorityNumber`
1–999999 (start 1000, step 1000; IG §9.2.5.2); lifecycle only on the CoU (new / replace / suspend; no append; IG §9.2.11.3);
document reuse by UUID (IG §9.2.17.1); keyword definition once per application, display-name corrections only with
`updateMode="R"` (IG §9.2.18; eCTD4-068); SHA-256 checksums (IG §5.6).

## 4. EG regional validation rules (adapted from the EU v4 IG validation table + EG drafts)

| ID | Element | Criterion | Sev. | Tag / source |
|---|---|---|---|---|
| EG-V4-020 | document/text | `text@language` present on **every** M1 document; value `ar` or `en`. (EU requires it only for m1-3-1.) | R | EU-DERIVED EU-IG "Document" (text@language for m1-3-1); EG-DRAFT App.2.2 p.78 (ar/en); extension to all M1 = ASSUMPTION (EG documents are bilingual) |
| EG-V4-021 | document/text | `text/description` and `thumbnail` are ignored by EDA; `confidentialityCode` not used (no EG list). | W | EU-DERIVED EU-IG "Document"; ASSUMPTION for confidentialityCode |
| EG-V4-022 | contextOfUse/code | A CoU must not use an EG heading whose `documents_allowed` is `false` (1.2, 1.2.2–1.2.8 groups, 1.2.10, 1.2.12, 1.2.13, 1.2.15, 1.2.16, 1.3–1.8 parents). | R | EG-DRAFT TG p.55 l.1414 ("Titles in italics are folders … do not contain documents"); ASSUMPTION for 1.2.2 and 1.3–1.8 |
| EG-V4-023 | contextOfUse/keyword | Keyword values from EG code systems must be in the values allowed for that CoU (e.g. PI document type only on `eg_1.3.1`). | R | ASSUMPTION (same principle as eCTD4-071) |
| EG-V4-030 | `eg_1.3.1` | Three keywords **required**: EG document type (`spc`, `pl`, `interpack`, `combined`, `outer`, `other`), EG language (`ar`/`en`), EG country (`eg`); and `text@language` must equal the language keyword. | R | EG-DRAFT pi-doc attributes all Mandatory (SPEC p.27); EU-DERIVED EU-IG "Product Information Texts in EU Module 1.3.1" and keyword-definition sample (document type + country + language keywords); equality check = ASSUMPTION |
| EG-V4-031 | `eg_1.6.1` / `eg_1.6.2` | Only one of the two may hold **active** CoUs in the current view of an application. | R | EG-DRAFT SPEC App.2 rows 159, 161 ("only one … can have content when sending a sequence"); "current view" reading = ASSUMPTION |
| EG-V4-032 | `eg_1.0` | Every SU contains at least one active new CoU on `eg_1.0` with document type `cover`, and one with `tracking`. Cover letters are **never replaced or suspended** — each SU adds a new CoU (title e.g. "Cover Letter for Sequence 12"). | R (cover) / W (tracking) | EG-DRAFT TG p.28 l.763–780 (cover always operation "new"; tracking table always included), SPEC App.2 row 5; EU-IG "Submission Unit" (application form and cover letter retained to keep history) |
| EG-V4-033 | `eg_responses` | Responses of one regulatory activity share one group-title keyword naming the activity (e.g. "Responses to Questions for Variation 028"); the list of questions should be the first document (lowest priorityNumber). | W | EG-DRAFT SPEC p.10 l.137–142; ICH group title IG §9.2.10.2 |
| EG-V4-034 | `eg_additional-data` | Only for information not covered by another EG heading; never for documents already submitted (reuse the document UUID instead). | W | EG-DRAFT SPEC App.2 row 178; ICH IG §9.2.17.1 |
| EG-V4-035 | keywordDefinition | No EG regional keyword-definition types in v0; sender-defined keywords in M1 only with ICH types `ich_keyword_type_11` (group title) and `ich_keyword_type_3` (manufacturer, on the headings that list it). | R (via eCTD4-071) | ASSUMPTION; EU-DERIVED (EU allows only one regional type in M1, EU-IG "Keyword Definition") |
| EG-V4-040 | submission/id | Exactly one `id/item`; `@root` UUID constant across all SUs of the activity; `@extension` = EDA procedure tracking number. | R | EU-DERIVED EU-IG "Submission" ("Only one item element should be provided"); EG-DRAFT SPEC p.17 |
| EG-V4-041 | submission/subject3/mode | Required, with a code from `eg-mode`, in **every** SU of a variation-type activity (28 tokens listed in `cv/eg-submission-types.yaml` → `mode_required_for`); not used otherwise. | R | EG-DRAFT SPEC p.8 l.78–80, p.15; TG p.27 l.722–724; EU-IG "Mode"; token list = ASSUMPTION |
| EG-V4-042 | submission/callBackContact | At least one contact party in the first SU of each activity; later SUs send only changes (suspend with `statusCode updateMode="R"`, update with `updateMode` R/N); contact type cannot be changed. | R | EU-DERIVED EU-IG "Contact Party" and "Contact party lifecycle"; EG drafts have no contact concept (GAP) |
| EG-V4-043 | submission/subject2/review | Required in the SU of type `initial` of an MAA-type submission (`eg_st_maa*`): one `review` with `manufacturedProduct` name (= v3.2.2 invented-name) and one `ingredient classCode="ACTI"` per INN. Only one review per message. Ignored for other SUs. | R | EU-DERIVED EU-IG "Review", "Manufactured Product", validation table ("Only one Review element"); EG-DRAFT SPEC p.18–19 E11, E14 |
| EG-V4-044 | review/subject2/productCategory | Exactly **two** productCategory codes when `review` is sent: one from `eg-registration-type`, one from `eg-marketing-type`. | R | ASSUMPTION (EU allows one productCategory; EG needs two v3.2.2 mandatory envelope values, SPEC p.18–19 E12–E13) |
| EG-V4-045 | application/informationRecipient | One `territorialAuthority` with `territory/code="eg"` and `governingAuthority/id@extension="EG-EDA"` (`@root` = EG authority list OID). | R | EG-DRAFT SPEC p.18 A6, App.2.4 p.78; EU-DERIVED EU-IG "Territorial Authority (as information recipient related to application)" |
| EG-V4-046 | application/holder/applicant | `sponsorOrganization/name` required, spelled consistently in every SU; `id/item@root` = EDA organisation-id namespace, `@extension` = EDA portal applicant ID. | R (name) / W (id) | EG-DRAFT TG p.27 l.739–741 (consistent applicant spelling); EU-DERIVED EU-IG "Applicant" (OMS LOC-ID); ID namespace = ASSUMPTION |
| EG-V4-047 | submission/subject5/submissionGroup | When an activity is grouped across several applications (SPEC "grouped variations that affect multiple marketing authorisations"), every SU of every member carries the same `submissionGroup/id@root` (UUID) with `@extension` = the EDA high-level number (`B-GV-xxxx`, `B-PGV-xxxx`, `I-GV-xxxx`), in all sequences of the activity. | R | EG-DRAFT SPEC p.8 l.80–88, p.16 E5; TG p.27 l.725–738; EU-DERIVED EU-IG "Submission Group" + validation table ("must be completed through all sequences"); `@extension` use = ASSUMPTION |
| EG-V4-048 | elements not used | `componentOf2/categoryEvent`, `submission/subject4/regulatoryReviewTime`, `review/holder` are ignored if sent; `submission/subject1/regulatoryStatus` is excluded by ICH. | — | EU-DERIVED EU-IG "Elements not required for EU Module 1"; ICH IG §4.7.2 |
| EG-V4-049 | contextOfUse/primaryInformationRecipient, subjectOf/submissionReference | Not used in Egypt (one authority; one product per application). | — | ASSUMPTION; EU-IG "Territorial Authority (as primary information recipient…)", "Submission Reference" |
| EG-V4-050 | document reuse | Reuse of a document UUID is allowed **within the same application**. Reuse **across applications** of the same applicant is allowed only once EDA confirms its repository retains documents across applications — the EG v3.2.2 rule forbids cross-application references ("it is not possible to refer to files in sequences in other eCTD applications", SPEC p.7 l.58–60). | R (until EDA decides) | ICH IG §9.2.17.1, IG §2 fn 2 (reuse depends on regional retention); EU-IG "Document Reuse"; EG-DRAFT SPEC p.7 l.58–60 |
| EG-V4-051 | SU code `reformat` | Only with submission type `eg_st_none`, only for a **non-eCTD → v4** baseline, all CoUs new; never for a v3.2.2 → v4 switch (use FC). | R | EG-DRAFT TG p.22 l.592–616, TG p.74; SPEC p.25 l.279–280; ICH IG §8 (FC), CR 00710 (no TMM); EU-IG "COMPATIBILITY…" |
| EG-V4-052 | withdrawal / rejection of **one** activity | Consolidating SU of type `eg_su_response` in that activity: suspend CoUs that are no longer relevant, replace adjusted ones, keep cover letter and application form; submission title states "consolidation after withdrawal/rejection". An SU or a submission can never be suspended. | R | EG-DRAFT SPEC p.25 l.283–287, TG p.73 (response); EU-DERIVED EU-IG "Submission Unit" (consolidation; SU cannot be suspended) |
| EG-V4-053 | withdrawal of the **whole** MA | New activity with submission type `eg_st_withdrawal`, SU type `eg_su_initial`. | R | EG-DRAFT SPEC p.26 l.291–294; TG p.65 |
| EG-V4-054 | UUID correction | If EDA finds an application UUID already used by another lifecycle, re-send the SU with a new application UUID and the same sequence number, stating it in the cover letter. A re-baseline (broken lifecycle) gets a new application UUID and starts at sequence `1`. | R | EG-DRAFT SPEC p.12 l.208–218; TG p.23–24 l.617–660 (re-baselining; restart at 0000 → `1` in v4 per EG-V4-003) |

## 5. Keywords and Context of Use in Egypt

* Heading list, parents, allowed keywords: `cv/eg-m1-context-of-use.yaml` (151 codes, 132 accept documents).
* Display names come from the code system, never from the message (EU-IG "ECTD 4.0 XML MESSAGE" note; IG §9.2.9.2).
* `originalText` (document label) may be used freely; it does not order content (IG §9.2.6.2).
* Order inside a context group by `priorityNumber` only (IG §9.2.5; QA #20).
* M2–M5 use the ICH CoU list `2.16.840.1.113883.3.989.2.2.1.1.6` and ICH keyword rules unchanged. Extra M2–M5
  granularity must go through ICH, not the region (VEN Open Discussion #2).

## 6. Envelope / application metadata: `eg-envelope` (v3.2.2 draft) → v4 classes

XPaths start at `/PORP_IN000001UV/controlActProcess/subject/submissionUnit`. EG element numbers (E/A) as in
`../EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md` §4.2 (SPEC App.1.1 p.14–20).

| # | EG v3.2.2 envelope item (SPEC App.1.1) | Card. (EG) | v4 location | Code system / value | Tag / source |
|---|---|---|---|---|---|
| E1/E2 | `eg-envelope`, `envelope` | 1 / 1..n | none — the whole message replaces it | — | ICH IG §3.4 (one submissionunit.xml replaces index/regional XML) |
| A1 | `envelope/@country` = `eg` | 1 | `componentOf1/submission/componentOf/application/informationRecipient/territorialAuthority/territory/code` | `eg-country` (`eg`) | EU-DERIVED EU-IG "Territorial Authority (as information recipient…)" |
| E3 | `identifier` (UUID) | 1 | `…/application/id/item/@root` | UUID (same value kept) | EU-DERIVED EU-IG "Application" |
| E4/A2 | `submission/@type` | 1 | `componentOf1/submission/code/@code` | `eg-submission-type` (`eg_st_<token>`) | ICH IG Table 11; EU-IG "Submission"; EG-DRAFT TG Annex 6 |
| A3 | `submission/@mode` | 0..1 (required for variations) | `…/submission/subject3/mode/code` | `eg-mode` | EU-DERIVED EU-IG "Mode"; EG-DRAFT SPEC p.15 |
| E5 | `submission/number` (high-level number) | 0..1 | `…/submission/subject5/submissionGroup/id` (`@root` shared UUID, `@extension` = number) | — | EU-DERIVED EU-IG "Submission Group"; ASSUMPTION for `@extension` |
| E6/A4 | `procedure-tracking/number` | 1..n | `…/submission/id/item/@extension` (EDA number). **Only one item is allowed**, so an applicant's internal tracking number has no place (GAP; keep it in the cover letter). | — | EU-DERIVED EU-IG "Submission" (extension = procedure number, one item) |
| E8/A5 | `submission-unit/@type` | 1 | `submissionUnit/code/@code` | `eg-submission-unit` (`eg_su_<token>`) | ICH IG §9.2.4 |
| E9 | `applicant` | 1 | `…/application/holder/applicant/sponsorOrganization/name/part/@value` (+ `id/item`) | EDA org-id namespace (placeholder) | EU-DERIVED EU-IG "Applicant" |
| E10/A6 | `agency/@code` = `EG-EDA` | 1 | `…/application/informationRecipient/territorialAuthority/governingAuthority/id/@extension` | `eg-authority` | EU-DERIVED EU-IG "Territorial Authority…"; EG-DRAFT SPEC p.18 |
| E11 | `invented-name` | 1..n | `…/submission/subject2/review/subject1/manufacturedProduct/manufacturedProduct/name` | free text | EU-DERIVED EU-IG "Manufactured Product" (initial MAA only) |
| E12/A7 | `registration/@type` | 1 | `…/review/subject2/productCategory/code` (1st) | `eg-registration-type` | **ASSUMPTION** (no RPS class; alternative = `componentOf2/categoryEvent`, IG Table 11) |
| E13/A8 | `marketing/@type` | 1 | `…/review/subject2/productCategory/code` (2nd) | `eg-marketing-type` | **ASSUMPTION** |
| E14 | `inn` | 0..n | `…/manufacturedProduct/manufacturedProduct/ingredient[@classCode='ACTI']/ingredientSubstance/name` | name only (no EG substance list) | EU-DERIVED EU-IG "Manufactured Product" (EU codes from SPOR SMS) |
| E15 | `sequence` | 1 | `componentOf1/sequenceNumber/@value` + second-level folder name | 1–999999 | ICH IG §9.2.12 |
| E16 | `related-sequence` | 1..n | **no element** — same `submission/id/@root` as the activity (see §1) | — | EU-DERIVED EU-IG "Submission" |
| E17 | `submission-description` | 1 | `submissionUnit/title/@value` | free text | EU-DERIVED EU-IG "Sequence Number" |
| — | `pi-doc` @type / @xml:lang / @country | 1 each | CoU keywords on `eg_1.3.1` + `document/text/@language` | `eg-document-type`, `eg-language`, `eg-country` | EG-V4-030 |
| — | leaf `xlink:href`, `checksum` (MD5), `title`, `operation`, node-extension | — | `document/text/reference`, `text/integrityCheck` (SHA-256), `document/title`, CoU lifecycle, group-title keyword | — | ICH IG §9.2.15, §9.2.11.3, §8.1.2 Table 9 |
| — | (no EG equivalent) | — | `submission/callBackContact` (EG-V4-042) | `eg-contact-party-role` | EU-DERIVED |

**Header** (IG §9.1.2; EU-IG "Example for the header as to be used in the EU region"): the ICH-excluded header elements
are sent empty; `receiver/device/id/item` ×2 = `2.16.840.1.113883.3.989.2.2.1.11.6` "ICH eCTD v4.0 IG v1.7" (CV Index) and
`2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER.6.1.0` "EG M1 v4 provisional profile v0 (PLACEHOLDER)".

## 7. Lifecycle notes specific to Egypt

* v3.2.2 advice "retain the obsolete entry" because backbone attributes cannot change (SPEC p.7 l.33–36) is superseded:
  in v4 change keywords by **suspend + new CoU** (may reuse the same document UUID) and fix keyword display names with
  `updateMode="R"` (IG §9.2.11.3, §9.2.18.6.2).
* No re-submission of documents already sent (SPEC p.8 l.68–71) → in v4 reference the document UUID (IG §9.2.17.1).
* PI language versions are separate context groups (language keyword), so Arabic and English SmPC/PL have independent
  lifecycles (EG-V4-030).

## 8. Grouped submissions across applications

EG v3.2.2: "a separate eCTD submission must be built for each MA covered by the variation", same high-level number,
product-specific tracking numbers (SPEC p.16–18). v4 equivalent: EU **Scenario 1** — one `submissionunit.xml` per
application in one transmission, common files placed with one of them and reused by UUID by the others, plus a shared
`submissionGroup` (EG-V4-047). EU Scenario 2 (one XML for several sequences, PSUSA) has no EG use case → not adopted.
Cross-application reuse inside such a group is subject to EG-V4-050. (EU-DERIVED: EU-IG "Grouped Submissions
functionality", "First Level Folder Naming Recommendation".)

## 9. Inherited conflicts in the EG drafts (decisions taken here)

| Conflict | Decision in v0 |
|---|---|
| Agency code `EG-EDA` (SPEC p.18, App.2.4) vs `EDA` (TG p.27) | `EG-EDA` |
| `Var PAC-II` / `var-pac-II` / `var-pac-ii` | `var-pac-ii` → `eg_st_var-pac-ii` |
| Mode `parallel-grouping` vs "parallel  grouping" / "Parallel Grouping" | `parallel-grouping` |
| PI types: App.2.3 has only `spc`, `pl`; drafts also use `interpack`, `combined`, `outer`, `other` | all six |
| Supportive documents: Additional Data (SPEC row 178) vs section 1.2 (TG 3.2.4.1) | unresolved — noted on both CoUs |
| `withdrawal` listed only for Biologics & Innovative (TG p.65) but general in SPEC p.26 | offered to all |
| 1.2.2 printed non-italic in TG Annex 5 although folder-only | folder-only (ASSUMPTION) |
| Consolidation SU type: EG `response` vs EU `consolidating` | EG `response` |
