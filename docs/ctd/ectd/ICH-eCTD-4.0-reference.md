# KB_V4 — ICH eCTD v4.0 technical reference (for building a v4.0 submission generator for EDA)

**Prepared:** 2026-11-06. **Use:** a future tool that writes eCTD v4.0 submission units for Egypt (EDA).
**Context, from the brief and not checked here:** EDA announced (14/06/2026, Almal News) full eCTD v4.0
implementation in Q1 2028 and an RPM system by Feb 2027. Its current draft guidance is based on v3.2.2. None of the source files below mentions EDA.

## 0. Sources used (only these; nothing from memory)

| Short ref | File (under `scratchpad/ectd/v4/`) | Version / date stated in the file |
|---|---|---|
| **IG** | `ig17/eCTD_v4.0_Implementation_Guide_v1.7/ICH_eCTDv4_0_ImplementationGuide_v1_7.pdf` | ICH eCTD v4.0 IG **v1.7, dated 5 May 2026** on the cover. The brief said "July 2026". The schema files in the zip are dated Jun/Jul 2026. |
| **XSD** | `ig17/.../ICH_eCTD_v4_SchemaFiles/{coreschemas,multicacheschemas}/*.xsd` | HL7 V3 RPS R2 schema set: 5 core + 16 multicache files |
| **CV** | `cv103/eCTD_v4.0_CV_Package_v1.0.3/ICH_eCTDv4_0_CV_v7.xlsx` (+ `Genericode.zip`, now unzipped in `cv103/gc/`, + ReadMe PDF) | CV Package **v1.0.3, May 2026**; spreadsheet v7 |
| **QA** | `qa110/eCTD_4.0_QA_CR_Document_v1.10/ICH_eCTD_v4.0_QA_v1.10.xlsx` | Q&A + Change-Request doc **v1.10, June 2026**: sheets Q&A (#1–27) and Change Requests (00010–00840) |
| **SUP** | `support16.pdf` | Support Documentation for Implementation Package v1.6, May 2024 |
| **ORI** | `orient16.pdf` | Orientation Material for Implementation Package v1.6, May 2024 |
| **VEN** | `vendor_2026_09.pdf` | M8 Vendor Group meeting minutes, 30 Sep 2026 |
| **EU-IG** | `eu_v4_ig.docx` | EU eCTD v4.0 Module 1 IG, "DRAFT for Updates 2024", **v1.2, October 2024**, OID `2.16.840.1.113883.3.989.5.1.1.6.1.2`. Its headings have no numbers, so it is cited here by heading name. |
| **EU-A1** | `eu_v4_annex1.pdf` | Annex 1 to the HMA eSubmission Roadmap, "Implementation of eCTD version 4.0", adopted 15.06.2018. It is **outdated**: it still describes the Transition Mapping Message (TMM), which CR 00710 / IG v1.5 removed. |
| — | `eu_nmv.html` | **Unusable**: the file is an HTTP 404 page. |

Citation style used below: `IG §9.2.6`, `IG Table 9`, `CV sheet "ICH Context of Use"`, `QA #20`, `CR 00780`, `rule eCTD4-080`, `VEN item 2.3`, and `EU-IG "Submission"` (EU-IG cited by heading name).

---

## 1. Concept change from v3.2.2 to v4.0

| Topic | eCTD v3.2.2 (only as the v4.0 sources describe it) | eCTD v4.0 | Source |
|---|---|---|---|
| Standard | DTD-based backbone (VEN Open Discussion #2: "The DTD laid this structure out when it related to 3.2.2") | HL7 V3 **Regulated Product Submission (RPS) Release 2 Normative** (HL7 normative Sept 2014). The IG covers only Modules 2–5; the Regional/M1 IG is needed for a complete message | IG §1, §3.1, §3.3 |
| Backbone files | `index.xml` + regional xml + `stf.xml` (IG Abbreviations "Forward Compatibility"); `util` folder with schema/DTD files (IG §5.1 "the util folder is no longer required"); an md5 checksum file (SUP p.19) | **One** file `submissionunit.xml` for M1–M5 ("replaces the previous v3.2.2 message files (i.e., index, regional and stf XML files)"). **No schema/util folder is sent**: the XML references the interaction schema | IG §5.1; IG §3.4 "Harmonised submission unit"; SUP p.19 ("sha256.txt … Replaces md5.txt") |
| Backbone checksum | MD5 (SUP p.19 says md5.txt is replaced) | **`sha256.txt`** in the sequence folder holds the SHA-256 of `submissionunit.xml` | IG §5.1; rules eCTD4-060/062 |
| File checksums | MD5 per leaf | **SHA-256** for every file referenced by a `document` (`text@integrityCheckAlgorithm="SHA256"` + `text/integrityCheck`). The XSD enumeration `IntegrityCheckAlgorithm` allows `SHA1` and `SHA256`; the IG requires SHA-256 | IG §5.6; IG §9.2.15.2; XSD `hl7-r2_datatypes.xsd` |
| Where a file sits | Folder + leaf in the DTD heading hierarchy | **Context of Use (CoU)**: a `contextOfUse` with a `code` (the CTD heading, from a CV) points to a `document` through `derivedFrom/documentReference/id`. A document with no CoU has no heading. "The folder structure will no longer serve as a reliable mechanism to navigate" | IG §9.2.6, §9.2.8, §11; SUP p.30 |
| Leaf attributes / STF | index.xml attributes (substance, manufacturer, product-name, dosageform, indication, excipient), node-extensions, STF (study-id, title, category, file-tag, property site-id) | **Keywords** on the CoU (`referencedBy/keyword/code`). The keyword is either an ICH/regional CV code or a sender-defined `keywordDefinition` declared once per application. **Context group** = same CoU code + same keyword code(s). Context groups replace the STF | IG §3.4 "Function of context groups"; IG §8.1.2 Table 9; IG §9.2.9; IG §9.2.18 |
| Ordering | Order of leafs in XML | **`priorityNumber`** (1–999999, whole number) per CoU, used within the same CoU-code + keyword-code combination | IG §9.2.5; QA #20; rule eCTD4-018 |
| Lifecycle operators | new / replace / delete / append | **active (new) / replace (new CoU + `replacementOf/relatedContextOfUse`) / suspend (`statusCode="suspended"`)**. `append` removed. `obsolete` is set by the receiver and never sent. Lifecycle happens **only on the CoU**: documents have no status | IG §3.4; IG §9.2.11.3; CV sheet "ICH Context of Use Status"; QA #2; SUP p.31; ORI p.25 |
| Replace cardinality | 1:1 | 1:1, 1:many, many:1, many:many | IG §9.2.16.2–3; SUP p.33 |
| Document reuse | Cross-reference by href to an earlier sequence | Each document has a **UUID** (`document/id@root`), sent once and then referenced by id **within or across submission units and applications**. The file is not re-sent | IG §2; IG §3.4; IG §9.2.17.1 |
| Metadata correction | Not possible without re-sending | `updateMode="R"` on `document/title`, `document/text@language`, `keywordDefinition/value/item/displayName`, and `priorityNumber` (reorder) | IG §9.2.5, §9.2.17.2, §9.2.18.6; SUP p.35 |
| Document label | n/a | Optional `contextOfUse/code/originalText@value` (short label, e.g. `3.2.P.8.3-1`). It cannot be updated and does not drive ordering | IG §9.2.6.2; ORI p.30–32 |
| Identifiers | Leaf IDs | **UUIDs** (8-4-4-4-12 hex) for every `id@root`: submissionUnit, submission, contextOfUse, document. **OIDs** for code systems, and the namespace `2.16.840.1.113883.3.989.2.2.1.13.1` + `@extension` = leaf reference to point at v3.2.2 leafs | IG §4.5; IG §8.1.1; SUP p.23 |
| Sequence number | 4 digits, `0000` first | Whole number **1–999999**. The first v4 SU of a new application is `1`. The second-level folder name = the value (e.g. `999`) | IG §5.1; IG §9.2.12; rules eCTD4-013/014 |
| Hierarchy | Application = dossier | **3 layers: Application ⊃ Submission (regulatory activity) ⊃ Submission Unit (sequence)**. An SU may belong to several submissions in some regions (grouped). The semantics of each layer are regional | SUP p.21; ORI p.11–12; IG §10 |
| Viewing | Style sheet in the browser | No style sheet. A dedicated viewer needs the CV files to display codes | EU-A1 §2.3; IG §6.3 note (no technical codes in the GUI) |
| Compressed archives | — | **Not allowed** for M2–M5 content | IG §5.7 |
| v3.2.2 content | — | Linked by **Forward Compatibility (FC)**, not by a transition message. The Transition Mapping Message was removed (CR 00710, IG v1.5). Once a v4.0 SU is received, any later v3.2.2 SU for that application is **rejected** | IG §8; IG change history v1.5 |

---

## 2. Submission-unit folder and file structure and naming rules

### 2.1 Folder layout (IG §5.1, Figure 1; SUP p.22)

```
<Region Specified Folder>/            ← 1st level: defined regionally (some regions may not use it). EU: application number, lower case, punctuation removed (e.g. ema000123, de2087)
   <sequence number>/                 ← 2nd level: the sequenceNumber value, e.g. 1, 2, 999 (no zero padding)
      submissionunit.xml              ← exactly one; the name is fixed and lower case
      sha256.txt                      ← SHA-256 of submissionunit.xml (the body of the text file)
      m1/                             ← structure per Regional/M1 IG (EU: one flat folder)
      m2/                             ← one flat folder, no subfolders
      m3/ 32-app/ 32-prod/ 32-reg/ 32-sub/ 33-lit/
      m4/ 421-phm/ 422-pk/ 423-tox/ 43-lit/   (+ optional study-id folders)
      m5/ 531-biopharm/ 532-pkbiomat/ 533-humanpk/ 534-pd/ 535-eff-safe/ 536-pms/ 537-listing/ 54-lit/ (+ optional study-id folders)
```

| Rule | Value | Source |
|---|---|---|
| Content of the sequence folder | `submissionunit.xml` (required), `sha256.txt` (required, same directory), `m1`–`m5` folders only when they have content | IG §5.1; rules eCTD4-059/060/061/063 |
| No empty folders | "The submission package should not contain empty folders" | IG §5.1 note |
| Every file must be referenced | All files in m1–m5 must be accounted for in the XML (regional exceptions possible) | IG §5.1; rule eCTD4-069 "Unassociated file found" |
| Files already sent | Do not send them again: reference them by document id or by relative path | IG §5.1; IG §9.2.17.3 |
| Do not send schemas | No `util` folder | IG §5.1 |
| Module 2 folder | `m2`, no subfolders | IG §11.1 |
| Module 3 folders | 3.2.A `32-app`; 3.2.P `32-prod`; 3.2.R `32-reg`; 3.2.S `32-sub`; 3.3 `33-lit`. Folders "can be changed to further reduce or omit folders". Add extra folders only to separate files that have the same name | IG §11.2 |
| Module 4 folders | 4.2.1 `421-phm`; 4.2.2 `422-pk`; 4.2.3 `423-tox`; 4.3 `43-lit`; optional study folders named by study id (e.g. `study-id-1`) | IG §11.3 |
| Module 5 folders | 5.3.1 `531-biopharm`; 5.3.2 `532-pkbiomat`; 5.3.3 `533-humanpk`; 5.3.4 `534-pd`; 5.3.5 `535-eff-safe`; 5.3.6 `536-pms`; 5.3.7 `537-listing`; 5.4 `54-lit` (literature/publications go in 5.4); optional study folders | IG §11.4 |
| Extra folders | Only at the **lowest** level of the given structure, and only for technical reasons | IG §11 intro |

### 2.2 Names, characters and lengths (IG §5.2–5.4)

| Rule | Value | Source / validation |
|---|---|---|
| Case | Folder and file names **lower case only** | IG §5.2 |
| Uniqueness | File names unique within a folder | IG §5.2 |
| Extension | Exactly **one** extension, 3 or 4 characters, showing the format | IG §5.2, §5.2.2 |
| Allowed characters | All alphanumerics plus **only** `$ - _ + ! ' ( )`. Follow IETF URL rules (RFC 3986) "except for period and asterisk". The Regional IG may list more, e.g. for study data | IG §5.2.1 Table 5; rule eCTD4-074 (checked on `text.reference@value`) |
| Max file name | **64** characters including the extension | IG §5.2.2; rule eCTD4-065 |
| Max folder name | **64** | IG §5.2.2; rule eCTD4-066 |
| Max path | **180** characters, counted from the first-level folder (a region may set its own limit; abbreviate if the path is longer) | IG §5.2.2; rule eCTD4-067 |
| Folder depth | No more than **7** folder levels inside the Region Specified Folder (nesting > 6 not acceptable), leaving room under the ISO 9660 limit of 8 | IG §5.4 note |
| Path syntax in XML | Relative to `submissionunit.xml`, separated by `/`, e.g. `m2/23-qos/introduction.pdf`. Reuse across sequences: `../99/m1/x.pdf`. Across applications: `../../NDA123456/99/m1/x.pdf` | IG §5.3; IG §9.2.17.3 |
| File formats | **Not set by ICH**: the Regional/M1 IG and the ICH "Specification for Submission Formats" set them | IG §5.5; SUP p.38 |
| Checksum | SHA-256 for every file referenced in a `document` of the SU, and for `submissionunit.xml` (in `sha256.txt`) | IG §5.1, §5.6; rules eCTD4-062, eCTD4-064 |
| Archives | No zip/tar.gz for M2–M5 | IG §5.7 |

> **Gap:** the IG does not define the exact byte format of `sha256.txt` (hex case, trailing newline,
> whether a file name follows the hash). SUP p.22 says only "SHA-256 checksum value is given as the body of text file".
> The `integrityCheck` samples are 64-character lower-case hex strings (IG §9.2.15.5). The IG also does not say
> whether checksum comparison is case-sensitive. To decide.

---

## 3. The XML message

### 3.1 Schema set (IG §4.3, §7; XSD folder)

| Category | Files present in the IG zip | Role |
|---|---|---|
| Core (HL7 V3) | `datatypes-rX-cs.xsd`, `hl7-r2_datatypes.xsd` (ISO 21090), `infrastructureRoot-r2.xsd`, `NarrativeBlock.xsd`, `voc-r2.xsd` | Data types and vocabulary. Not referenced directly (IG §7.1) |
| Interaction | `PORP_IN000001UV.xsd`, "Submission Unit Sent" | **The schema to validate `submissionunit.xml` against** (QA #14). It includes `MCCI_MT000100UV02.xsd` (transmission wrapper), `MCAI_MT700201UV02.xsd` (control act) and `PORP_MT000001UV01.xsd` (payload) |
| Payload | `PORP_MT000001UV01.xsd` | eCTD payload (submissionUnit, submission, application, contextOfUse, document, keywordDefinition…) |
| CMETs | `COCT_MT030203UV07, 040203UV09, 070000UV01, 090100UV01, 090108UV, 090300UV01, 090303UV01, 150000UV02, 150003UV03, 150007UV, 710000UV07, 960000UV05` | Common Product Model / common message elements |

> **IG inconsistency (flag):** IG §7.2.1.2 / §7.2.1.3 name `MCCI_MT0001000UV01.xsd` and `MCAI_MT700201UV01.xsd`.
> The IG §4.3 table and the files actually shipped are `MCCI_MT000100UV02.xsd` and `MCAI_MT700201UV02.xsd`. Use the shipped files.

### 3.2 Root, namespaces, header (IG §9.1, Table 10, §9.1.2; rule eCTD4-084)

| Item | Required value | Source |
|---|---|---|
| Root element | `PORP_IN000001UV` | IG Table 10; XSD `PORP_IN000001UV.xsd` |
| `@ITSVersion` | `XML_1.0` (fixed in the XSD) | IG §9.1.2 |
| Default namespace | `xmlns="urn:hl7-org:v3"` | IG §9.1.2 |
| xsi | `xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"` | IG §9.1.2 |
| Schema location | `xsi:schemaLocation="urn:hl7-org:v3 PORP_IN000001UV.xsd"` | IG §9.1.2 |
| Encoding | Sample prolog `<?xml version="1.0" encoding="UTF-8"?>`; the Text data type allows any UTF-8 | IG Table 2; IG §4.6; SUP p.27 |
| Header elements excluded by ICH but **required by the schema** | `id`, `creationTime`, `interactionId`, `processingCode`, `processingModeCode`, `acceptAckCode`, `sender/device/id`. Send them as **empty self-closing tags**; any value is ignored | IG §4.7.2; IG Table 10 |
| `receiver/@typeCode` | fixed `RCV` (may be omitted) | IG §9.1.2 |
| `receiver/device@classCode` / `@determinerCode` | `DEV` / `INSTANCE` | IG §9.1.2 |
| `receiver/device/id/item` ×2 | `@root` = OID of the **ICH IG version** and of the **Regional IG version** used; `@identifierName` = a version label (not used by the RA). **Both are required**: rule eCTD4-084 (CR 00770, QA #26) | IG §9.1.2; IG §12.3 |
| `sender/@typeCode` | fixed `SND` (may be omitted) | IG §9.1.2 |
| `sender/device@classCode` / `@determinerCode` | `DEV` / `INSTANCE`; `sender/device/<id/>` empty | IG §9.1.2 |
| ICH IG OID for **IG v1.7** | **`2.16.840.1.113883.3.989.2.2.1.11.6`**. The IG's own sample (§9.1.2.1) still shows `…11.4` "ICH eCTD v4.0 IG v1.5"; that sample is out of date | CV sheet "Index" row "ICH eCTD v4.0 IG Version" (11.1=v1.0, 11.2=v1.3, 11.3=v1.4, 11.4=v1.5, 11.5=v1.6, **11.6=v1.7, start 2026-05**) |
| Payload start | `controlActProcess@classCode="ACTN"`, `@moodCode="EVN"`; `subject@typeCode="SUBJ"` | IG §9.2.2.1 |
| Null flavors | Not used in eCTD v4.0 | IG §4.6 |

### 3.3 Payload: classes, paths, cardinality, code systems

Paths start at `/PORP_IN000001UV/controlActProcess/subject/`. "Fixed" attributes are fixed in the XSD and may be left out. Any other value fails the schema.

| Class / element | XPath (relative to `controlActProcess/subject`) | Card. | Required attributes / children (IG card.) | Code system | Source |
|---|---|---|---|---|---|
| **submissionUnit** (classCode ACT, moodCode EVN fixed) | `submissionUnit` | 1..1 per message (eCTD4-005) | `id@root` UUID [1..1], unique per SU (eCTD4-003/004) | — | IG §9.2.4 |
| ↳ code | `submissionUnit/code` | 1..1 | `@code` [1..1] regional SU type (e.g. original); `@codeSystem` [1..1] regional OID (eCTD4-006..009) | **Regional** "Submission Unit Codes" (EU: `2.16.840.1.113883.3.6905.1.8.1`) | IG §9.2.4.2; IG §6.2 |
| ↳ title | `submissionUnit/title@value` | 0..1 | sender text (e.g. "Presubmission") | — | IG §9.2.4.2 |
| ↳ statusCode | `submissionUnit/statusCode@code` | 0..1 | if present, `code` [1..1] = **`active` only** (eCTD4-010; CR 00800) | HL7 status (no OID sent) | IG §9.2.4.2 |
| **component / priorityNumber** (typeCode COMP fixed) | `submissionUnit/component/priorityNumber@value` | 1..1 per component; ≥1 component per SU (eCTD4-011) | `@value` whole number 1–999999 (eCTD4-017/018/019); `@updateMode="R"` only for reordering | — | IG §9.2.5 |
| **contextOfUse** (DOC/EVN fixed) | `submissionUnit/component/contextOfUse` | 1 per component; 1..* per SU | — | — | IG §9.2.6 |
| ↳ id | `…/contextOfUse/id` | 1..1 | `@root` UUID [1..1] (unique); **or** for FC `@root="2.16.840.1.113883.3.989.2.2.1.13.1"` + `@extension`=leaf reference (only to **suspend** v3.2.2 content) | ICH v3.2.2 FC namespace `…13.1` | IG §9.2.6.2; eCTD4-020/021 |
| ↳ code | `…/contextOfUse/code` | 0..1 (required when active) | `@code` [1..1] e.g. `ich_3.2.p.2.3`; `@codeSystem` [1..1] OID (eCTD4-075, eCTD4-081). Leave it out when suspending or when only reordering | **ICH Context of Use** `2.16.840.1.113883.3.989.2.2.1.1.6` (current); M1 = regional CoU list | IG §9.2.6.2; CV |
| ↳ code/originalText | `…/contextOfUse/code/originalText@value` | 0..1 | Document label; cannot be updated | — | IG §9.2.6.2 |
| ↳ statusCode | `…/contextOfUse/statusCode@code` | 1..1 | `active` or `suspended` only (eCTD4-022/023); never `obsolete` | **ICH Context of Use Status** (HL7; no OID sent; listed as `2.16.840.1.113883.1.11.20523` in the CV Index) | IG §9.2.6.2; CV |
| ↳ primaryInformationRecipient/territorialAuthority/governingAuthority/{id,name} | `…/contextOfUse/primaryInformationRecipient/…` | 0..1 | Regional | Regional | IG Table 11; EU-IG "Territorial Authority (as primary information recipient…)" |
| ↳ replacementOf (typeCode **RPLC**) / relatedContextOfUse/id | `…/contextOfUse/replacementOf/relatedContextOfUse/id` | 0..* | `@root` UUID of the CoU being replaced, or `…13.1` + `@extension` leaf ref (eCTD4-024/025/026) | FC `…13.1` | IG §9.2.7 |
| ↳ derivedFrom (typeCode DRIV fixed in XSD) / documentReference/id | `…/contextOfUse/derivedFrom/documentReference/id` | 0..1; **required if active**, **forbidden if suspended** (eCTD4-027/028) | `@root` document UUID (this SU or earlier), or `…13.1` + `@extension` leaf ref (eCTD4-076) | FC `…13.1` | IG §9.2.8; XSD |
| ↳ subjectOf/submissionReference/id/item | `…/contextOfUse/subjectOf/submissionReference` | 0..1 | Regional (EU: `subjectOf@negationInd="true"` hides a CoU for given submissions) | — | IG Table 11; EU-IG "Submission Reference" |
| ↳ referencedBy (typeCode **REFR** required) / keyword/code | `…/contextOfUse/referencedBy/keyword/code` | 0..* | `@code` [1..1], `@codeSystem` [1..1] (eCTD4-029..032). One code per keyword. Each keyword **type** at most once per CoU (eCTD4-072). Required types must be present (eCTD4-070); types must be allowed for the heading (eCTD4-071) | ICH keyword CVs (document type `…3.4`, duration `…4.2`, route `…6.2`, species `…7.2`, type of control `…10.2`, study group order `…12.2`), or the **sender-defined** code system of a keywordDefinition | IG §9.2.9 |
| **componentOf1 / sequenceNumber** (COMP fixed) | `submissionUnit/componentOf1/sequenceNumber@value` | 1..1 per submission (eCTD4-012/016) | whole number 1–999999 (eCTD4-013); the first SU of the application = `1` (eCTD4-014); unique within the application (eCTD4-015) | — | IG §9.2.12 |
| **submission** | `submissionUnit/componentOf1/submission` | 1..* (SUP p.28) | `id` (item@root **UUID**, eCTD4-033/077); `code@code` + `@codeSystem` regional (eCTD4-034..037) | Regional "Submission Codes" | IG Table 11; IG §12.2 |
| ↳ callBackContact/contactParty/… ; subject2/review (manufacturedProduct, holder/applicant, author/territorialAuthority, subject2/productCategory, subject3/regulatoryStatus); subject3/mode; subject4/regulatoryReviewTime; subject5/submissionGroup | `…/submission/…` | Regional | Regional | Regional CVs (Contact Party, Product Category, Regulatory Status, Mode, Regulatory Review Time) | IG §4.7.1; IG Table 11 |
| ↳ subject1/regulatoryStatus | `…/submission/subject1/regulatoryStatus` | — | **Excluded by ICH** (ignored) | — | IG §4.7.2 |
| **application** (ACT/EVN fixed) | `…/submission/componentOf/application` | 1..* (SUP p.28) | `id/item` [1..*] `@root` OID or UUID [1..1], `@extension` [0..1] regional tracking number (eCTD4-038); `code@code` + `@codeSystem` [1..1] regional (eCTD4-039..042) | Regional "Application Codes" | IG §9.2.14 |
| ↳ holder/applicant/sponsorOrganization{id,name}; informationRecipient/territorialAuthority; subject/reviewProcedure/code; reference/applicationReference/id | `…/application/…` | Regional | Regional | Regional | IG §4.7.1 |
| **document** (DOC/EVN fixed) | `…/application/component/document` | 0..* | `id@root` **UUID** [1..1], unique (eCTD4-043..046); `title@value` [1..1] (eCTD4-047), `title@updateMode` [0..1] = `R`; `text` [0..1] (required for a new document) | — | IG §9.2.15 |
| ↳ text | `…/document/text` | 0..1 | `@integrityCheckAlgorithm` (`SHA256`), `@language` (ISO 639-1, 2-letter), `@mediaType` (regional), `@charset` (regional), `@updateMode` (R); children `reference@value` (relative path), `integrityCheck` (hex SHA-256), `thumbnail@value` (sender only, ignored), `description@value` (regional) | ISO 639-1 | IG §9.2.15.2 |
| ↳ referencedBy/keyword | `…/document/referencedBy/keyword` | — | **Excluded by ICH** (ignored) | — | IG §4.7.2 |
| **keywordDefinition** (ACT/EVN fixed) | `…/application/referencedBy/keywordDefinition` | 0..* (one concept per definition; defined once per application) | `code@code` (keyword **type**, e.g. `ich_keyword_type_3`) + `@codeSystem` [1..1] (eCTD4-052/053/083); `statusCode@code="active"` [1..1]; `value/item` **exactly one** [1..1] (eCTD4-056/057) with `@code`, `@codeSystem` (sender-defined), `displayName@value` [1..1], `displayName@updateMode` [0..1]=`R` | **ICH Keyword Definition Type** `2.16.840.1.113883.3.989.2.2.1.5.4` (or regional type list) | IG §9.2.18 |
| **componentOf2 / categoryEvent** (+ component/categoryEvent) | `submissionUnit/componentOf2/categoryEvent` | Regional | Regional | Regional "Category Event Codes" | IG Table 11; IG §4.7.1 |

**Message order inside `submissionUnit`** (XSD `PORP_MT000001UV01.SubmissionUnit`): `id, code, title, statusCode, component*, componentOf1*, componentOf2*`.
**Inside `contextOfUse`** (XSD): `id, code, statusCode, primaryInformationRecipient, replacementOf*, derivedFrom, subjectOf, referencedBy*`.

**updateMode** (IG §9.2.2.3): optional in the schema, but required when sending an update. The XSD allows `A D R AR N U K`. The IG uses **only `R`**, on `priorityNumber`, `document/title`, `document/text` (language) and `keywordDefinition/value/item/displayName`. Rule eCTD4-085 (CR 00830): a document element sent with `updateMode="R"` must **not** also carry `text@integrityCheckAlgorithm`, `text/integrityCheck` or `reference@value`. To change content, replace the CoU instead.

### 3.4 XML example

**The IG has no single complete, schema-valid instance.** It shows the header (Table 10 / §9.1.2.1) and separate payload
fragments (§9.2.11, §9.2.13, §9.2.15.5, §9.2.18.6). The fragments quoted verbatim are:

*IG §9.1.2.1 header, verbatim (note: the OID shown is the IG v1.5 one):*
```xml
<id/>
<creationTime/>
<interactionId/>
<processingCode/>
<processingModeCode/>
<acceptAckCode/>
<receiver>
  <device classCode="DEV" determinerCode="INSTANCE">
    <id>
      <item root="2.16.840.1.113883.3.989.2.2.1.11.4" identifierName="ICH eCTD v4.0 IG v1.5"/>
      <item root="OID for Regional IG" identifierName="Regional/Module1 IG Version Number"/>
    </id>
  </device>
</receiver>
<sender>
  <device classCode="DEV" determinerCode="INSTANCE">
    <id/>
  </device>
</sender>
```

*IG §9.2.13 submission unit, verbatim (regional OIDs are placeholders in the IG):*
```xml
<subject typeCode="SUBJ">
  <submissionUnit>
    <id root="0d84467e-f20b-42ad-a69a-63e61a4f7ea7"/>
    <code code="regional_sub_unit_type_1" codeSystem="2.16.840.1.113883.3.989.x.x.x"/>
    <title value="Original Submission for pain medication - acetyl salicylic acid tablets"/>
    <statusCode code="active"/>
    …
    <componentOf1>
      <sequenceNumber value="1"/>
      <submission>
        …
        <componentOf>
          …
        </componentOf>
      </submission>
    </componentOf1>
    <componentOf2>
      …
    </componentOf2>
  </submissionUnit>
</subject>
```

*IG §9.2.17.1 "Document Reuse", Sequence 1, verbatim (CoU + document):*
```xml
<component>
  <priorityNumber value="1000"/>
  <contextOfUse>
    <id root="7480bc1a-6486-4714-8d32-a3bd41de9be6"/>
    <code code="ich_3.2.s.2.3" codeSystem="2.16.840.1.113883.3.989.2.2.1.1.1"/>
    <statusCode code="active"/>
    <derivedFrom>
      <documentReference>
        <id root="3d1084fb-56c6-4923-a1e5-8a15e4fdc9c5"/>
      </documentReference>
    </derivedFrom>
  </contextOfUse>
</component>

<document>
  <id root="3d1084fb-56c6-4923-a1e5-8a15e4fdc9c5"/>
  <title value="Excipients X"/>
  <text integrityCheckAlgorithm="SHA256">
    <reference value="m3/32-prod/excipients.pdf"/>
    <integrityCheck>c0d5623550c997a70b62717d95fca1cada201754d1ed9fbbbbfa97bfd64c8ea4</integrityCheck>
  </text>
</document>
```

*IG §9.2.18.6.1 keyword definition, verbatim:*
```xml
<referencedBy>
  <keywordDefinition>
    <code code="ich_keyword_type_3" codeSystem="2.16.840.1.113883.3.989.2.2.1.5.2"/>
    <statusCode code="active"/>
    <value>
      <item code="MANU001" codeSystem="2.16.840.1.113883.3">
        <displayName value="Big Manufacturer"/>
      </item>
    </value>
  </keywordDefinition>
</referencedBy>
```

**Minimal complete skeleton, put together by this KB from the IG fragments above.** It is *not* an IG quote. It **validated with `xmllint --schema PORP_IN000001UV.xsd`** (the copy is `scratchpad/ectd/tools/skeleton_test.xml`) after the placeholders were filled with dummy UUIDs and a dummy hash. Schema validity only: the business rules (e.g. a real regional OID, eCTD4-084) are not checked.
It uses the current CV OIDs. Regional parts are marked `REGIONAL`; their values must come from the EDA M1 IG:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<PORP_IN000001UV ITSVersion="XML_1.0" xmlns="urn:hl7-org:v3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="urn:hl7-org:v3 PORP_IN000001UV.xsd">
  <id/><creationTime/><interactionId/><processingCode/><processingModeCode/><acceptAckCode/>
  <receiver><device classCode="DEV" determinerCode="INSTANCE"><id>
    <item root="2.16.840.1.113883.3.989.2.2.1.11.6" identifierName="ICH eCTD v4.0 IG v1.7"/>
    <item root="REGIONAL-IG-OID" identifierName="REGIONAL M1 IG vX"/>
  </id></device></receiver>
  <sender><device classCode="DEV" determinerCode="INSTANCE"><id/></device></sender>
  <controlActProcess classCode="ACTN" moodCode="EVN">
    <subject typeCode="SUBJ">
      <submissionUnit>
        <id root="0d84467e-f20b-42ad-a69a-63e61a4f7ea7"/>
        <code code="REGIONAL-SU-TYPE" codeSystem="REGIONAL-SU-OID"/>
        <statusCode code="active"/>
        <component>
          <priorityNumber value="1000"/>
          <contextOfUse>
            <id root="7480bc1a-6486-4714-8d32-a3bd41de9be6"/>
            <code code="ich_3.2.s.2.3" codeSystem="2.16.840.1.113883.3.989.2.2.1.1.6"/>
            <statusCode code="active"/>
            <derivedFrom><documentReference><id root="3d1084fb-56c6-4923-a1e5-8a15e4fdc9c5"/></documentReference></derivedFrom>
            <referencedBy typeCode="REFR"><keyword><code code="MANU001" codeSystem="SENDER-OID"/></keyword></referencedBy>
          </contextOfUse>
        </component>
        <componentOf1>
          <sequenceNumber value="1"/>
          <submission>
            <id><item root="REGIONAL: UUID"/></id>
            <code code="REGIONAL-SUBMISSION-TYPE" codeSystem="REGIONAL-SUBMISSION-OID"/>
            <componentOf>
              <application>
                <id><item root="REGIONAL: OID-or-UUID" extension="REGIONAL-APP-NUMBER"/></id>
                <code code="REGIONAL-APP-TYPE" codeSystem="REGIONAL-APP-OID"/>
                <component>
                  <document>
                    <id root="3d1084fb-56c6-4923-a1e5-8a15e4fdc9c5"/>
                    <title value="Excipients X"/>
                    <text integrityCheckAlgorithm="SHA256" language="en">
                      <reference value="m3/32-sub/excipients.pdf"/>
                      <integrityCheck>…64 hex…</integrityCheck>
                    </text>
                  </document>
                </component>
                <referencedBy>
                  <keywordDefinition>
                    <code code="ich_keyword_type_3" codeSystem="2.16.840.1.113883.3.989.2.2.1.5.4"/>
                    <statusCode code="active"/>
                    <value><item code="MANU001" codeSystem="SENDER-OID"><displayName value="Big Manufacturer"/></item></value>
                  </keywordDefinition>
                </referencedBy>
              </application>
            </componentOf>
          </submission>
        </componentOf1>
      </submissionUnit>
    </subject>
  </controlActProcess>
</PORP_IN000001UV>
```
Child order checked in the XSD (`PORP_MT000001UV01.xsd`): application = `id, code, holder, informationRecipient, subject, reference, component, referencedBy`; submission = `id, code, callBackContact, subject1…subject5, componentOf`; document = `id, title, text, confidentialityCode, referencedBy`; keywordDefinition = `code, statusCode, value`.

**Fuller examples in the IG:** Table 11 (full element tree), §9.2.11.1 (CoU with replacement + keywords), §9.2.11.2 (study group order),
§9.2.11.3.1–4 (insert / reorder / suspend / replace, including FC), §9.2.15.5 (document with every optional attribute), §9.2.16.1–3
(group title, 1→many, many→1), §9.2.17.1–3 (reuse, FC reuse, title/text updates, file reuse paths), §9.2.18.5–7 and §9.2.19
(keyword definitions, display-name change, Study-Id_$Title). EU-IG "Guidance regarding Keyword Definition values" has the most complete
*whole-message* sample in the sources (header, SU, CoU with 5 keywords, submission, application, document, keywordDefinition).

> **IG sample caveats (flag):** many IG samples use superseded CV OIDs, e.g. CoU `…1.1.1` / `…1.1.3`, document type `…3.2`,
> keyword type `…5.2`, species `…7.1`. §9.2.19 shows keyword-type OID `2.16.840.1.113883.3.989.2.2.1.95.2`, which does not exist in
> the CV Index and is evidently a typo for `…5.x`. Sender-defined samples use `codeSystem="2.16.840.1.113883.3"`, which is for illustration only.
> A generator must take OIDs from the **CV Index**, not from the IG samples.

---

## 4. Controlled vocabularies

### 4.1 OID tree (IG §4.5.1; Genericode `ICH M8 OID Listing_eCTDv4_v7.xlsx`)
`2.16.840.1.113883.3.989` ich-estri → `.2` msg-stds → `.2.2` m8-ectd → `.2.2.1` code-lists → `.2.2.1.x` value set → `.2.2.1.x.y` value-set **version** (x = code system, y = version).
The `codeSystem` sent in the message is the **version OID**. A code may only be sent with a version that contains it (IG §6.6.1.1).

### 4.2 Every list in the CV package (CV sheet "Index", v1.0.3)

| Code system (sheet) | Type | Current OID (all versions in Index) | Start / end | Used at (XPath) | Purpose |
|---|---|---|---|---|---|
| ICH Context of Use | ICH | **`…2.2.1.1.6`** (1.1 n/a; 1.2 n/a; 1.3 2021-06; 1.4 2022-05; 1.5 2024-05, end blank; 1.6 2026-05) | current start 2026-05 (genericode file says `StartDate 2026-04`) | `…/contextOfUse/code/@code` | CTD headings M2–M5 + allowed keyword types per heading |
| ICH Context of Use Status | HL7 | no OID sent (Index note: HL7 `2.16.840.1.113883.1.11.20523`) | v1 2015-12; v2 2024-05 | `…/contextOfUse/statusCode/@code` | active / suspended / obsolete |
| ICH Document Type | ICH | **`…2.2.1.3.4`** (3.1, 3.2 n/a; 3.3 2022-05) | 2024-05 | `…/contextOfUse/referencedBy/keyword/code/@code` | Replaces the STF file-tag; study document types |
| ICH Duration | ICH | **`…2.2.1.4.2`** (4.1 2015-12) | 2024-05 | keyword | Tox study duration |
| ICH Keyword Definition Type | ICH | **`…2.2.1.5.4`** (5.1 n/a; 5.2 2021-06; 5.3 2022-05) | 2024-05 | `…/application/referencedBy/keywordDefinition/code/@code` | Types of sender-defined keywords |
| ICH Route of Administration for Non-Clinical Study | ICH | **`…2.2.1.6.2`** (6.1 2015-12) | 2024-01 | keyword | Route (order per ICH M4S) |
| ICH Species for Non-Clinical Study | ICH | **`…2.2.1.7.2`** (7.1 2015-12) | 2024-05 | keyword | Species (order per ICH M4S) |
| ICH Type of Control | ICH | **`…2.2.1.10.2`** (10.1 2015-12) | 2024-05 | keyword | Control type for 5.3.5.1 |
| ICH Study Group Order | ICH | **`…2.2.1.12.2`** (12.1 2015-12) | 2024-05 | keyword (the sheet's XPATH cell wrongly says `contextOfUse/code/@code`) | Order of studies, 1–99 |
| ICH eCTD v4.0 IG Version | ICH | **`…2.2.1.11.6`** = IG v1.7 (11.1 v1.0 … 11.5 v1.6) | 2026-05 | `receiver/device/id/item/@root` | Declares the IG version used (eCTD4-084) |
| ICH eCTD v4.0 Controlled Vocabulary Package | ICH | **`…2.2.1.14.2`** = CV v1.0.3 (14.1 = v1.0.2) | 2026-05 | not stated | Identifies the CV package version (**Gap:** neither the IG nor the CV says where, or whether, it goes in the message) |
| ICH XML Types | ICH | no OID sent | 2024-05 | inside the FC leaf reference string | `ich`, `us-regional`, `eu-regional`, `ca-regional`, `ch-regional` |
| ICH v3.2.2 (Forward Compatibility) | ICH | **`2.16.840.1.113883.3.989.2.2.1.13.1`** | 2022-05 | `id@root` of contextOfUse / relatedContextOfUse / documentReference | Namespace for v3.2.2 leaf references |

Code-list governance (IG §6.6): a list version is **valid** while it has no end date. Several versions can be valid at once. Adding codes does not retire the earlier version. A version is retired (end date set) when codes are removed or replaced exclusively (IG §6.6.2.3). Code status is Active or Retired, and retired codes give a "Last Valid Version". Operations are No Code Change / Added / Replaced / Removed (Table 7). **Rule eCTD4-079:** a submission is rejected if a code value is retired. CR 00750 also planned "Code system version is valid" and "Code value exists in code system version" rules. In IG v1.7 they appear only inside eCTD4-079 and the CV-validity rules (eCTD4-075/081/031/083). IG §6.6.2 note: changing a code breaks lifecycle, so content must be resubmitted as new and the old content suspended.

### 4.3 Lists defined outside the ICH CV package (IG §6.2–6.5)

| Owner | Lists | Source |
|---|---|---|
| **Region** (OID registered by the region) | Application; Application Reference Reason; Category Event; Contact Party; **Context of Use (M1)**; Keyword (regional additions); Keyword Definition (regional types); Ingredient Role; Manufactured Product; Media Types; Mode; Place; Product Category; Regulatory Status; Regulatory Review Time; Review Procedure; Submission; Submission Unit; Substance; Territorial Authority Role; Territorial | IG §6.2 |
| **HL7** | Document typeCodes (fixed in the schema, no OID); Status codes (no OID); Update Mode codes | IG §6.3 |
| **ISO** | ISO 639-1 two-letter language (`text@language`); ISO 3166-1 two-letter country | IG §6.4 |
| **Sender** | `keywordDefinition/value/item@code` + `@codeSystem` (OID **or** text; the sender's own assignment). It must not collide with OIDs registered by agencies (VEN item 3.3) | IG §6.5.1; IG §9.2.9.2 |

### 4.4 Full code lists (generated directly from `ICH_eCTDv4_0_CV_v7.xlsx`; CTD section = the prefix of the display name)

Notes: `ich_2` ("m2 common technical document summaries") was **retired/removed** in v6 (CR 00790; last valid version `…1.1.5`).
Active codes: M2 = 24, M3 = 65, M4 = 31, M5 = 22. Total = **142 active + 1 retired (`ich_2`) = 143 rows**. No `ich_2.1`, `ich_3.1`, `ich_4.1` or `ich_5.1` exists, and no table-of-contents code.
The column "Keyword types allowed" is the source for rules eCTD4-070/071 (required/allowed keyword types per heading).

#### ICH Context of Use — `2.16.840.1.113883.3.989.2.2.1.1.6` (sheet "ICH Context of Use", support start 2026-05)

| # | Code | Display name (CV "Description") | Keyword types allowed (R=required, O=optional) | Status | Remarks |
|---|---|---|---|---|---|
| 1 | `ich_2` | m2 common technical document summaries |  | Retired |  |
| 2 | `ich_2.2` | m2.2 introduction |  | Active |  |
| 3 | `ich_2.3` | m2.3 quality overall summary |  | Active |  |
| 4 | `ich_2.3.i` | m2.3 introduction |  | Active |  |
| 5 | `ich_2.3.s` | m2.3.s drug substance | substance (O), manufacturer (O) | Active |  |
| 6 | `ich_2.3.p` | m2.3.p drug product | product (O), dosage form (O) | Active |  |
| 7 | `ich_2.3.a.1` | m2.3.a.1 facilities and equipment | facility (O) | Active |  |
| 8 | `ich_2.3.a.2` | m2.3.a.2 adventitious agents safety evaluation | component (O) | Active |  |
| 9 | `ich_2.3.a.3` | m2.3.a.3 excipients |  | Active |  |
| 10 | `ich_2.3.r` | m2.3.r regional information |  | Active |  |
| 11 | `ich_2.4` | m2.4 nonclinical overview |  | Active |  |
| 12 | `ich_2.5` | m2.5 clinical overview |  | Active |  |
| 13 | `ich_2.6.1` | m2.6.1 introduction |  | Active |  |
| 14 | `ich_2.6.2` | m2.6.2 pharmacology written summary |  | Active |  |
| 15 | `ich_2.6.3` | m2.6.3 pharmacology tabulated summary |  | Active |  |
| 16 | `ich_2.6.4` | m2.6.4 pharmacokinetics written summary |  | Active |  |
| 17 | `ich_2.6.5` | m2.6.5 pharmacokinetics tabulated summary |  | Active |  |
| 18 | `ich_2.6.6` | m2.6.6 toxicology written summary |  | Active |  |
| 19 | `ich_2.6.7` | m2.6.7 toxicology tabulated summary |  | Active |  |
| 20 | `ich_2.7.1` | m2.7.1 summary of biopharmaceutic studies and associated analytical methods |  | Active |  |
| 21 | `ich_2.7.2` | m2.7.2 summary of clinical pharmacology studies |  | Active |  |
| 22 | `ich_2.7.3` | m2.7.3 summary of clinical efficacy | indication (R) | Active |  |
| 23 | `ich_2.7.4` | m2.7.4 summary of clinical safety |  | Active |  |
| 24 | `ich_2.7.5` | m2.7.5 literature references |  | Active |  |
| 25 | `ich_2.7.6` | m2.7.6 synopses of individual studies |  | Active |  |
| 26 | `ich_3.2.s` | m3.2.s drug substance | substance (O) | Active |  |
| 27 | `ich_3.2.s.1` | m3.2.s.1 general information | substance (O), manufacturer (O), group title (O) | Active |  |
| 28 | `ich_3.2.s.2` | m3.2.s.2 manufacture | substance (O), manufacturer (O) | Active |  |
| 29 | `ich_3.2.s.2.1` | m3.2.s.2.1 manufacturer(s) | substance (O), manufacturer (O), group title (O) | Active |  |
| 30 | `ich_3.2.s.2.2` | m3.2.s.2.2 description of manufacturing process and process controls | substance (O), manufacturer (O), group title (O) | Active |  |
| 31 | `ich_3.2.s.2.3` | m3.2.s.2.3 control of materials | substance (O), manufacturer (O), group title (O) | Active |  |
| 32 | `ich_3.2.s.2.4` | m3.2.s.2.4 controls of critical steps and intermediates | substance (O), manufacturer (O), group title (O) | Active |  |
| 33 | `ich_3.2.s.2.5` | m3.2.s.2.5 process validation and/or  evaluation | substance (O), manufacturer (O), group title (O) | Active |  |
| 34 | `ich_3.2.s.2.6` | m3.2.s.2.6 manufacturing process development | substance (O), manufacturer (O), group title (O) | Active |  |
| 35 | `ich_3.2.s.3` | m3.2.s.3 characterisation | substance (O), manufacturer (O) | Active |  |
| 36 | `ich_3.2.s.3.1` | m3.2.s.3.1 elucidation of structure and other characteristics | substance (O), manufacturer (O), group title (O) | Active |  |
| 37 | `ich_3.2.s.3.2` | m3.2.s.3.2 impurities | substance (O), manufacturer (O), group title (O) | Active |  |
| 38 | `ich_3.2.s.4` | m3.2.s.4 control of drug substance | substance (O), manufacturer (O), group title (O) | Active |  |
| 39 | `ich_3.2.s.4.1` | m3.2.s.4.1 specification | substance (O), manufacturer (O), group title (O) | Active |  |
| 40 | `ich_3.2.s.4.2` | m3.2.s.4.2 analytical procedures | substance (O), manufacturer (O), group title (O) | Active |  |
| 41 | `ich_3.2.s.4.3` | m3.2.s.4.3 validation of analytical procedures | substance (O), manufacturer (O), group title (O) | Active |  |
| 42 | `ich_3.2.s.4.4` | m3.2.s.4.4 batch analyses | substance (O), manufacturer (O), group title (O) | Active |  |
| 43 | `ich_3.2.s.4.5` | m3.2.s.4.5 justification of specification | substance (O), manufacturer (O), group title (O) | Active |  |
| 44 | `ich_3.2.s.5` | m3.2.s.5 reference standards or materials | substance (O), manufacturer (O), group title (O) | Active |  |
| 45 | `ich_3.2.s.6` | m3.2.s.6 container closure system | substance (O), manufacturer (O), group title (O) | Active |  |
| 46 | `ich_3.2.s.7` | m3.2.s.7 stability | substance (O), manufacturer (O), group title (O) | Active |  |
| 47 | `ich_3.2.s.7.1` | m3.2.s.7.1 stability summary and conclusions | substance (O), manufacturer (O), group title (O) | Active |  |
| 48 | `ich_3.2.s.7.2` | m3.2.s.7.2 post-approval stability protocol and stability commitment | substance (O), manufacturer (O), group title (O) | Active |  |
| 49 | `ich_3.2.s.7.3` | m3.2.s.7.3 stability data | substance (O), manufacturer (O), descriptor (O),  group title (O) | Active |  |
| 50 | `ich_3.2.p` | m3.2.p drug product | product (O), dosage form (O) | Active |  |
| 51 | `ich_3.2.p.1` | m3.2.p.1 description and composition of the drug product | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 52 | `ich_3.2.p.2` | m3.2.p.2 pharmaceutical development | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 53 | `ich_3.2.p.2.1` | m3.2.p.2.1 components of the drug product | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 54 | `ich_3.2.p.2.2` | m3.2.p.2.2 drug product | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 55 | `ich_3.2.p.2.3` | m3.2.p.2.3 manufacturing process development | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 56 | `ich_3.2.p.2.4` | m3.2.p.2.4 container closure system | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 57 | `ich_3.2.p.2.5` | m3.2.p.2.5 microbiological attributes | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 58 | `ich_3.2.p.2.6` | m3.2.p.2.6 compatibility | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 59 | `ich_3.2.p.3` | m3.2.p.3 manufacture | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 60 | `ich_3.2.p.3.1` | m3.2.p.3.1 manufacturer(s) | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 61 | `ich_3.2.p.3.2` | m3.2.p.3.2 batch formula | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 62 | `ich_3.2.p.3.3` | m3.2.p.3.3 description of manufacturing process and process controls | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 63 | `ich_3.2.p.3.4` | m3.2.p.3.4 controls of critical steps and intermediates | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 64 | `ich_3.2.p.3.5` | m3.2.p.3.5 process validation and/or  evaluation | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 65 | `ich_3.2.p.4` | m3.2.p.4 control of excipients | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 66 | `ich_3.2.p.4.1` | m3.2.p.4.1 specifications | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 67 | `ich_3.2.p.4.2` | m3.2.p.4.2 analytical procedures | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 68 | `ich_3.2.p.4.3` | m3.2.p.4.3 validation of analytical procedures | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 69 | `ich_3.2.p.4.4` | m3.2.p.4.4 justification of specifications | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 70 | `ich_3.2.p.4.5` | m3.2.p.4.5 excipients of human or animal origin | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 71 | `ich_3.2.p.4.6` | m3.2.p.4.6 novel excipients | product (O), dosage form (O), manufacturer (O), excipient (O), group title (O) | Active |  |
| 72 | `ich_3.2.p.5` | m3.2.p.5 control of drug product | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 73 | `ich_3.2.p.5.1` | m3.2.p.5.1 specification(s) | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 74 | `ich_3.2.p.5.2` | m3.2.p.5.2 analytical procedures | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 75 | `ich_3.2.p.5.3` | m3.2.p.5.3 validation of analytical procedures | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 76 | `ich_3.2.p.5.4` | m3.2.p.5.4 batch analyses | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 77 | `ich_3.2.p.5.5` | m3.2.p.5.5 characterisation of impurities | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 78 | `ich_3.2.p.5.6` | m3.2.p.5.6 justification of specifications | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 79 | `ich_3.2.p.6` | m3.2.p.6 reference standards or materials | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 80 | `ich_3.2.p.7` | m3.2.p.7 container closure system | product (O), dosage form (O), manufacturer (O), container (O), group title (O) | Active |  |
| 81 | `ich_3.2.p.8` | m3.2.p.8 stability | product (O), dosage form (O), manufacturer (O) | Active |  |
| 82 | `ich_3.2.p.8.1` | m3.2.p.8.1 stability summary and conclusion | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 83 | `ich_3.2.p.8.2` | m3.2.p.8.2 post-approval stability protocol and stability commitment | product (O), dosage form (O), manufacturer (O), group title (O) | Active |  |
| 84 | `ich_3.2.p.8.3` | m3.2.p.8.3 stability data | product (O), dosage form (O), manufacturer (O), descriptor (O), group title (O) | Active |  |
| 85 | `ich_3.2.a` | m3.2.a appendices |  | Active |  |
| 86 | `ich_3.2.a.1` | m3.2.a.1 facilities and equipment | facility (O), group title (O) | Active |  |
| 87 | `ich_3.2.a.2` | m3.2.a.2 adventitious agents safety evaluation | component (O), group title (O) | Active |  |
| 88 | `ich_3.2.a.3` | m3.2.a.3 excipients | excipient (O), group title (O) | Active |  |
| 89 | `ich_3.2.r` | m3.2 r regional information | group title (O) | Active |  |
| 90 | `ich_3.3` | m3.3 literature references | group title (O) | Active |  |
| 91 | `ich_4.2.1.1` | m4.2.1 1 primary pharmacodynamics | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 92 | `ich_4.2.1.2` | m4.2.1 2 secondary pharmacodynamics | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 93 | `ich_4.2.1.3` | m4.2.1 3 safety pharmacology | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 94 | `ich_4.2.1.4` | m4.2.1 4 pharmacodynamic drug interactions | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 95 | `ich_4.2.2.1` | m4.2.2.1 analytical methods and validation reports | study id_study title (R), document type (R), study group order (O),  group title (O) | Active |  |
| 96 | `ich_4.2.2.2` | m4.2.2 2 absorption | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 97 | `ich_4.2.2.3` | m4.2.2.3 distribution | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 98 | `ich_4.2.2.4` | m4.2.2.4 metabolism | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 99 | `ich_4.2.2.5` | m4.2.2.5 excretion | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 100 | `ich_4.2.2.6` | m4.2.2.6 pharmacokinetic drug interactions | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 101 | `ich_4.2.2.7` | m4.2.2.7 other pharmacokinetic studies | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 102 | `ich_4.2.3.1` | m4.2.3.1 single-dose toxicity | study id_study title (R), document type (R), species (R), route of admin (R), study group order (O), group title (O) | Active |  |
| 103 | `ich_4.2.3.2` | m4.2.3.2 repeat-dose toxicity | study id_study title (R), document type (R), species (R), route of admin (R), duration (O), study group order (O), group title (O) | Active |  |
| 104 | `ich_4.2.3.3.1` | m4.2.3.3.1 in vitro | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 105 | `ich_4.2.3.3.2` | m4.2.3.3.2 in vivo | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 106 | `ich_4.2.3.4.1` | m4.2.3.4.1 long-term studies | study id_study title (R), document type (R), species (R), study group order (O), group title (O) | Active |  |
| 107 | `ich_4.2.3.4.2` | m4.2.3.4.2 short or medium-term studies | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 108 | `ich_4.2.3.4.3` | m4.2.3.4.3 other studies | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 109 | `ich_4.2.3.5.1` | m4.2.3.5.1 fertility and early embryonic development | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 110 | `ich_4.2.3.5.2` | m4.2.3.5.2 embryofetal development | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 111 | `ich_4.2.3.5.3` | m4.2.3.5.3 prenatal and postnatal development, including maternal function | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 112 | `ich_4.2.3.5.4` | m4.2.3.5.4 studies in which the offspring juvenile animals are dosed and/or further evaluated | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 113 | `ich_4.2.3.6` | m4.2.3.6 local tolerance | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 114 | `ich_4.2.3.7.1` | m4.2.3.7.1 antigenicity | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 115 | `ich_4.2.3.7.2` | m4.2.3.7.2 immunotoxicity | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 116 | `ich_4.2.3.7.3` | m4.2.3.7.3 mechanistic studies | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 117 | `ich_4.2.3.7.4` | m4.2.3.7.4 dependence | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 118 | `ich_4.2.3.7.5` | m4.2.3.7.5 metabolites | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 119 | `ich_4.2.3.7.6` | m4.2.3.7.6 impurities | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 120 | `ich_4.2.3.7.7` | m4.2.3.7.7 other | study id_study title (R), document type (R), study group order (O), group title (O) | Active |  |
| 121 | `ich_4.3` | m4.3 literature references | group title (O) | Active |  |
| 122 | `ich_5.2` | m5.2 tabular listing of all clinical studies |  | Active |  |
| 123 | `ich_5.3.1.1` | m5.3.1 1 bioavailability study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 124 | `ich_5.3.1.2` | m5.3.1 2 comparative ba and bioequivalence study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 125 | `ich_5.3.1.3` | m5.3.1 3 in vitro  in vivo correlation study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 126 | `ich_5.3.1.4` | m5.3.1 4 reports of bioanalytical and analytical methods for human studies | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 127 | `ich_5.3.2.1` | m5.3.2.1 plasma protein binding study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 128 | `ich_5.3.2.2` | m5.3.2.2 reports of hepatic metabolism and drug interaction studies | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 129 | `ich_5.3.2.3` | m5.3.2.3 reports of studies using other human biomaterials | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 130 | `ich_5.3.3.1` | m5.3.3.1 healthy subject pk and initial tolerability study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 131 | `ich_5.3.3.2` | m5.3.3.2 patient pk and initial tolerability study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 132 | `ich_5.3.3.3` | m5.3.3 3 intrinsic factor pk study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 133 | `ich_5.3.3.4` | m5.3.3.4 extrinsic factor pk study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 134 | `ich_5.3.3.5` | m5.3.3.5 population pk study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 135 | `ich_5.3.4.1` | m5.3.4.1 healthy subject pd and pk/pd study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 136 | `ich_5.3.4.2` | m5.3.4.2 patient pd and pk/pd study reports | study id_study title (R), document type (R), site-id (O), study group order (O), group title (O) | Active |  |
| 137 | `ich_5.3.5.1` | m5.3.5.1 study reports of controlled clinical studies pertinent to the claimed indication | study id_study title (R), document type (R), indication (R),  type of control (R), site-id (O), study group order (O), group title (O) | Active |  |
| 138 | `ich_5.3.5.2` | m5.3.5.2 study reports of uncontrolled clinical studies | study id_study title (R), document type (R), indication (R), site-id (O), study group order (O), group title (O) | Active |  |
| 139 | `ich_5.3.5.3` | m5.3.5.3 reports of analyses of data from more than one study | study id_study title (R), document type (R), indication (R), site-id (O), study group order (O), group title (O) | Active |  |
| 140 | `ich_5.3.5.4` | m5.3.5.4 other study reports | study id_study title (R), document type (R), indication (R), study group order (O), site-id (O), group title (O) | Active | The indication (R) should be the indication that the application is applied for, but not the indication that the study report itself is for. |
| 141 | `ich_5.3.6` | m5.3.6 reports of postmarketing experience | study id_study title (O), document type (O),  site-id (O), study group order (O), group title (O) | Active |  |
| 142 | `ich_5.3.7` | m5.3.7 case report forms and individual patient listings | study id_study title (O), document type (O),  site-id (O), study group order (O), group title (O) | Active |  |
| 143 | `ich_5.4` | m5.4 literature references | group title (O) | Active |  |

#### ICH Context of Use Status — `n/a` (sheet "ICH Context of Use Status", support start 2024-05)

| Code | Description | Remarks | Status | Operation |
|---|---|---|---|---|
| `active` | current | - | Active | - |
| `suspended` | no longer relevant | - | Active | - |
| `obsolete` | replaced | This code should not be sent in the XML message.  The system will change the status of a Context of Use from active to obsolete once it has been replaced. | Active | - |

#### ICH Document Type — `2.16.840.1.113883.3.989.2.2.1.3.4` (sheet "ICH Document Type", support start 2024-05)

| Code | Description | Content-of-Document | Reference | Status | Operation |
|---|---|---|---|---|---|
| `ich_document_type_1` | preclinical study report | Pre-clinical study report |  | Active | - |
| `ich_document_type_2` | legacy clinical study report | Clinical study report submitted as one file |  | Active | - |
| `ich_document_type_3` | synopsis | Study Report Synopsis | E3 2 | Active | No Code Change |
| `ich_document_type_4` | study report body | Study Report Body | E3 1, 3 to 15 | Active | No Code Change |
| `ich_document_type_5` | protocol or amendment | Protocol and/or amendments | E3 16.1.1 | Active | No Code Change |
| `ich_document_type_6` | sample case report form | Sample Case Report Form | E3 16.1.2 | Active | No Code Change |
| `ich_document_type_7` | iec irb consent form list | IEC and IRB and Consent Form Listings | E3 16.1.3 | Active | No Code Change |
| `ich_document_type_8` | list description investigator site | Description of Investigators and Sites | E3 16.1.4 | Active | No Code Change |
| `ich_document_type_9` | signatures investigators | Signatures of principal or coordinating investigator(s) or sponsor’s responsible officer | E3 16.1.5 | Active | No Code Change |
| `ich_document_type_10` | list patients with batches | Listing of patients receiving test drug(s) from specified batch | E3 16.1.6 | Active | No Code Change |
| `ich_document_type_11` | randomisation scheme | Randomisation Scheme | E3 16.1.7 | Active | No Code Change |
| `ich_document_type_12` | audit certificates report | Audit Certificates or similar documentation | E3 16.1.8 | Active | No Code Change |
| `ich_document_type_13` | statistical methods interim analysis plan | Documentation of statistical methods and interim analysis plans | E3 16.1.9 | Active | No Code Change |
| `ich_document_type_14` | inter-laboratory standardisation methods quality assurance | Documentation of Inter-laboratory Standardisation Methods and Quality Assurance or similar documentation | E3 16.1.10 | Active | No Code Change |
| `ich_document_type_15` | publications based on study | Publications Based on the Study | E3 16.1.11 | Active | No Code Change |
| `ich_document_type_16` | publications referenced in report | Publications Referenced in the Study Report | E3 16.1.12 | Active | No Code Change |
| `ich_document_type_17` | discontinued patients | Discontinued Patients Listing | E3 16.2.1 | Active | No Code Change |
| `ich_document_type_18` | protocol deviations | Protocol Deviation Listing | E3 16.2.2 | Active | No Code Change |
| `ich_document_type_19` | patients excluded from efficacy analysis | Patients Excluded from Efficacy Analysis Listing | E3 16.2.3 | Active | No Code Change |
| `ich_document_type_20` | demographic data | Demographic Data Listing | E3 16.2.4 | Active | No Code Change |
| `ich_document_type_21` | compliance and drug concentration data | Compliance and/or Drug Concentration Data Listing | E3 16.2.5 | Active | No Code Change |
| `ich_document_type_22` | individual efficacy response data | Individual Efficacy Response Data Listing | E3 16.2.6 | Active | No Code Change |
| `ich_document_type_23` | adverse event listings | File contains Adverse Event Listings | E3 16.2.7 | Active | No Code Change |
| `ich_document_type_24` | listing individual laboratory measurements by patient | Individual Laboratory Measurements Listed by Patient | E3 16.2.8 | Active | No Code Change |
| `ich_document_type_25` | case report forms | CRF for an individual subject | E3 16.3 | Active | No Code Change |
| `ich_document_type_74` | csr other | Clinical study report submitted as multiple files and that do not apply to ICH E3 reference headings |  | Active | Added |
| `ich_document_type_26` | available on request | A file listing documents available upon request for a single study. Consult regional guidance for use |  | Active | - |
| `ich_document_type_27` | assay validation | Reports addressing Assay Validation studies |  | Active | - |
| `ich_document_type_28` | biomarkers | Reports indicating uses of Biomarkers in various studies |  | Active | - |
| `ich_document_type_29` | data monitoring review committees | Data Monitoring Review Committee Reports |  | Active | - |
| `ich_document_type_30` | device information | Device description, specifications, performance, handling and complaints |  | Active | - |
| `ich_document_type_31` | diagnostic tests | Diagnostic Tests including Individualised Therapy |  | Active | - |
| `ich_document_type_32` | gene therapy | Include information/reports on: - any clinical pharmacological studies / pharmacokinetics of the vector and vector products - any immunological studies, e.g., development of antibodies to the vector and vector products - a long-term follow-up protocol and any available data (especially with integrated retroviral vectors) - environmental assessments, including shedding studies |  | Active | - |
| `ich_document_type_33` | patient reported outcomes | Reports addressing Patient Reported Outcomes |  | Active | - |
| `ich_document_type_34` | pharmacodynamics | Reports addressing Pharmacodynamics studies |  | Active | - |
| `ich_document_type_35` | pharmacogenomics | Reports addressing Pharmacogenomics studies |  | Active | - |
| `ich_document_type_36` | pharmacokinetics | Reports addressing Pharmacokinetics studies |  | Active | - |
| `ich_document_type_37` | quality of life | Reports addressing Quality of Life studies |  | Active | - |
| `ich_document_type_75` | hepatic impairment study | Hepatic impairment studies conducted to assess the influence of hepatic impairment on pharmacokinetics and, where appropriate, pharmacodynamics of a drug |  | Active | - |
| `ich_document_type_76` | renal impairment study | Renal impairment studies conducted to assess the influence of renal impairment on pharmacokinetics and, where appropriate, pharmacodynamics of a drug |  | Active | Added |
| `ich_document_type_77` | drug-drug interaction study | Drug-drug interaction (DDI) studies conducted to assess the influence of drug-drug interactions on pharmacokinetics and, where appropriate, pharmacodynamics of a drug |  | Active | Added |
| `ich_document_type_78` | mass balance study | Mass balance study to obtain quantitative information on drug absorption, distribution, metabolism, and elimination properties |  | Active | Added |
| `ich_document_type_79` | population pk report | Report summarising population pharmacokinetic (population PK) analyses conducted to inform drug development |  | Active | Added |
| `ich_document_type_80` | population pkpd report | Report summarising population pharmacokinetic/pharmacodynamic analyses conducted to inform drug development |  | Active | Added |
| `ich_document_type_81` | pbpk report | Report summarising physiologically-based pharmacokinetic analyses conducted to inform drug development |  | Active | Added |
| `ich_document_type_82` | pbbm report | Report summarising physiologically-based biopharmaceutics modelling conducted to inform recommendations on biopharmaceutics applications |  | Active | Added |
| `ich_document_type_83` | qsp report | Report summarising population quantitative systems pharmacology analyses conducted to inform drug development |  | Active | Added |
| `ich_document_type_84` | cp general | Checklist document and clinical pharmacology table |  | Active | Added |
| `ich_document_type_85` | qt clinical study | Stand-alone thorough QT studies or QT assessments performed by combining findings from multiple studies together | E14/S7B Q&As | Active | Added |
| `ich_document_type_86` | qt invitro study | Nonclinical in vitro study report summarise patch clamp studies, in vitro assays, etc. for assessing effects of cardiac channels |  | Active | Added |
| `ich_document_type_87` | pd invivo study | In vivo nonclinical mechanism of action or proof of concept studies that supplement standard primary and secondary pharmacology studies |  | Active | Added |
| `ich_document_type_88` | pd invitro study | In vitro nonclinical mechanism of action or proof of concept studies that supplement standard primary and secondary pharmacology studies |  | Active | Added |
| `ich_document_type_38` | stem cells | Include information/reports on: - long-term follow-up for tumorigenicity - any immunological studies, including panel-reactive antibodies - any special biodistribution studies in humans |  | Active | - |
| `ich_document_type_39` | abuse liability | Reports addressing Abuse Liability studies |  | Active | - |
| `ich_document_type_40` | antibody | Reports addressing Antibody Data studies |  | Active | - |
| `ich_document_type_41` | healthcare utilisation | Reports addressing Healthcare Utilisation studies |  | Active | - |
| `ich_document_type_42` | other data not specified | Other data not specified in other sections |  | Active | - |
| `ich_document_type_43` | pk/pd relationship | Reports addressing Pharmacodynamics / Pharmacokinetics Relationship studies |  | Active | - |
| `ich_document_type_44` | specialty report | Reports addressing Specialty studies (e.g., Radioactivity Report-ADME, Dissolution Report, Health Authority Request) |  | Active | - |
| `ich_document_type_45` | bimo | Bioresearch Monitoring Information |  | Active | - |
| `ich_document_type_46` | foreign clinical studies not under ind | Reports of foreign clinical studies not conducted under an IND |  | Active | - |
| `ich_document_type_47` | data tabulation dataset legacy | Data tabulation dataset |  | Active | - |
| `ich_document_type_48` | data tabulation data definition | Data definitions for data tabulation datasets |  | Active | - |
| `ich_document_type_71` | data tabulation dataset sdtm | data tabulation dataset sdtm |  | Active | - |
| `ich_document_type_72` | data tabulation dataset send | data tabulation dataset send |  | Active | - |
| `ich_document_type_49` | data listing dataset | Data listing dataset |  | Active | - |
| `ich_document_type_50` | data listing data definition | Data definitions for data listing datasets |  | Active | - |
| `ich_document_type_51` | analysis dataset legacy | Analysis datasets |  | Active | - |
| `ich_document_type_52` | analysis program | Program file for analysis dataset |  | Active | - |
| `ich_document_type_53` | analysis data definition | Data definition for analysis datasets |  | Active | - |
| `ich_document_type_73` | analysis dataset adam | analysis dataset adam |  | Active | - |
| `ich_document_type_54` | annotated crf | Annotated CRF for datasets |  | Active | - |
| `ich_document_type_55` | ecg | Annotated ECG waveform dataset |  | Active | - |
| `ich_document_type_56` | image | Image files |  | Active | - |
| `ich_document_type_57` | subject profiles | Subject profile |  | Active | - |
| `ich_document_type_58` | safety report | IND safety report |  | Active | - |
| `ich_document_type_59` | antibacterial | Antibacterial microbiology report |  | Active | - |
| `ich_document_type_60` | special pathogen | Special pathogens (e.g., fungi, parasites, mycobacteria) and immune modulator microbiology report |  | Active | - |
| `ich_document_type_61` | antiviral | Antiviral microbiology report |  | Active | - |
| `ich_document_type_62` | iss | Integrated analysis of safety – integrated summary of safety report |  | Active | - |
| `ich_document_type_63` | ise | Integrated analysis of efficacy – integrated summary of efficacy report |  | Active | - |
| `ich_document_type_89` | iscp | Integrated analysis of clinical pharmacology - integrated summary of clinical pharmacology report |  | Active | Added |
| `ich_document_type_90` | isi | Integrated analysis of immunogenicity - integrated summary of immunogenicity report |  | Active | Added |
| `ich_document_type_91` | weight of evidence | Nonclinical weight-of-evidence or risk assessment documents |  | Active | Added |
| `ich_document_type_92` | animal rule efficacy | Nonclinical efficacy studies conducted for products regulated under the Animal Rule |  | Active | Added |
| `ich_document_type_93` | animal rule natural history | Nonclinical natural history studies that are conducted with chemical, biological, radiological, or nuclear agents and used for animal model development for products regulated under the Animal Rule |  | Active | Added |
| `ich_document_type_94` | nonstandard safety study | Studies conducted to provide complementary safety information to standard pharmacology and toxicology studies |  | Active | Added |
| `ich_document_type_64` | pm description | Postmarketing periodic adverse event drug experience report description |  | Active | - |
| `ich_document_type_66` | study data reviewer's guide | Study Data Reviewer's Guide |  | Active | - |
| `ich_document_type_67` | analysis data reviewer's guide | Analysis Data Reviewer's Guide |  | Active | - |
| `ich_document_type_68` | hf validation protocol | Protocol describing the design and methodology for a Human Factors validation study. |  | Active | - |
| `ich_document_type_69` | hf validation report | Report providing the results from a Human Factors validation study. |  | Active | - |
| `ich_document_type_70` | hf validation other | Human Factors information that is not a validation protocol or report. |  | Active | - |

#### ICH Duration — `2.16.840.1.113883.3.989.2.2.1.4.2` (sheet "ICH Duration", support start 2024-05)

| Code | Description | Status | Operation |
|---|---|---|---|
| `ich_duration_1` | short | Active | - |
| `ich_duration_2` | medium | Active | - |
| `ich_duration_3` | long | Active | - |

#### ICH Keyword Definition Type — `2.16.840.1.113883.3.989.2.2.1.5.4` (sheet "ICH Keyword Definition Type", support start 2024-05)

| Code | Description | Remarks | Status | Operation |
|---|---|---|---|---|
| `ich_keyword_type_1` | indication |  | Active | - |
| `ich_keyword_type_2` | substance |  | Active | - |
| `ich_keyword_type_3` | manufacturer |  | Active | - |
| `ich_keyword_type_4` | product | Replaces "product-name" attribute in eCTD v3.2.2 | Active | - |
| `ich_keyword_type_5` | dosage form |  | Active | - |
| `ich_keyword_type_6` | excipient |  | Active | - |
| `ich_keyword_type_7` | container |  | Active | - |
| `ich_keyword_type_8` | study id_study title | Merges Study Id and Study Title | Active | - |
| `ich_keyword_type_10` | site id | The site-id should only be used when one of the following document types is present:  -  ich_document_type_25:  case report forms -  ich_document_type_57:  subject profiles | Active | - |
| `ich_keyword_type_11` | group title |  | Active | - |
| `ich_keyword_type_12` | facility |  | Active | - |
| `ich_keyword_type_13` | component |  | Active | - |
| `ich_keyword_type_14` | descriptor |  | Active | - |

#### ICH Route of Administration for Non-Clinical Study — `2.16.840.1.113883.3.989.2.2.1.6.2` (sheet "ICH Route of Admin", support start 2024-01)

| Code | Description | Status | Operation |
|---|---|---|---|
| `ich_route_1` | oral | Active | - |
| `ich_route_2` | intravenous | Active | - |
| `ich_route_3` | intramuscular | Active | - |
| `ich_route_4` | intraperitoneal | Active | - |
| `ich_route_5` | subcutaneous | Active | - |
| `ich_route_6` | inhalation | Active | - |
| `ich_route_7` | topical | Active | - |
| `ich_route_8` | other | Active | - |

#### ICH Species for Non-Clinical Study — `2.16.840.1.113883.3.989.2.2.1.7.2` (sheet "ICH Species", support start 2024-05)

| Code | Description | Status | Operation |
|---|---|---|---|
| `ich_species_1` | mouse | Active | - |
| `ich_species_2` | rat | Active | - |
| `ich_species_3` | hamster | Active | - |
| `ich_species_4` | other rodent | Active | - |
| `ich_species_5` | rabbit | Active | - |
| `ich_species_6` | dog | Active | - |
| `ich_species_7` | non human primate | Active | - |
| `ich_species_8` | other non rodent mammal | Active | - |
| `ich_species_9` | non mammals | Active | - |

#### ICH Type of Control — `2.16.840.1.113883.3.989.2.2.1.10.2` (sheet "ICH Type of Control", support start 2024-05)

| Code | Description | Status | Operation |
|---|---|---|---|
| `ich_type_of_control_1` | placebo | Active | - |
| `ich_type_of_control_2` | no treatment | Active | - |
| `ich_type_of_control_3` | dose response without placebo | Active | - |
| `ich_type_of_control_4` | active control without placebo | Active | - |
| `ich_type_of_control_5` | external | Active | - |

#### ICH XML Types — `n/a` (sheet "ICH XML Types", support start 2024-05)

| Code | Description | Remarks | Status | Operation |
|---|---|---|---|---|
| `ich` | ICH XML | - | Active | - |
| `us-regional` | US FDA Regional XML | - | Active | - |
| `eu-regional` | EU Regional XML | - | Active | - |
| `ca-regional` | Health Canada Regional XML | - | Active | - |
| `ch-regional` | Swissmedic Regional XML | - | Active | - |

#### ICH Study Group Order Type — `2.16.840.1.113883.3.989.2.2.1.12.2` (sheet "ICH Study Group Order", support start 2024-05)

99 codes: `ich_study_group_order_1` … `ich_study_group_order_99` (description = the integer 1 … 99; all Active).

---

## 5. Rules for document reuse, keywords, grouping, ordering and lifecycle

### 5.1 Keywords and keyword definitions

| Rule | Detail | Source |
|---|---|---|
| Two kinds | (a) **CV keyword**: code taken directly from an ICH or regional list (document type, species, route, duration, type of control, study group order; EU: country, document type, dose form…). (b) **Sender-defined keyword**: a `keywordDefinition` (type from "ICH Keyword Definition Type" or a regional type list) declares `item@code` + `@codeSystem` + `displayName`, and the CoU then references `item@code`/`@codeSystem` | IG §9.2.9; IG §9.2.18 |
| Sender-defined types (ICH) | indication `_1`, substance `_2`, manufacturer `_3`, product `_4` (replaces v3 product-name), dosage form `_5`, excipient `_6`, container `_7`, **study id_study title `_8`**, site id `_10`, group title `_11`, facility `_12`, component `_13`, descriptor `_14` (no `_9`) | CV sheet "ICH Keyword Definition Type" |
| Once per application | Define each keyword once per application, then reference it by code. **Re-define it for each new application** (the same code/value may be re-sent across applications, e.g. grouped submissions) | IG §9.2.18.2; IG §9.2.18.6; IG §6.5.1 note; ORI p.20 |
| One item | Exactly one `value/item` per keywordDefinition (the schema allows more) | IG §9.2.18.2; eCTD4-057 |
| No duplicate concept | "one concept shall not be defined more than once within an application" | IG §9.2.18.7 |
| No reused code pair | The same sender code + codeSystem **may not** be defined for two different keyword types. eCTD4-055 fails in that case, and eCTD4-055 checks more than syntax | **VEN item 2.1** (30 Sep 2026) |
| Display-name fix | Re-send the definition with the same code and `displayName@updateMode="R"`. It applies to **all SUs of that application** (past ones included), not to other applications. If it must not apply to an earlier SU, define a new keyword. A new displayName without `updateMode` → **rejection** (eCTD4-068). It does not change the sha256 of earlier messages | IG §9.2.18.2; IG §9.2.18.6.2; QA #3 |
| Study Id + Title | Display name `studyID_$studyTitle` (delimiter **`_$`**), e.g. `Study-001_$Title A`. eCTD4-073 checks the format | IG §9.2.18.5.1; IG §9.2.19 |
| One type per CoU | A keyword *type* is used at most once on a CoU ("shall"; a rejection rule) | IG §9.2.9.2; QA #16 (CR 00580/00590); eCTD4-072 |
| Required / allowed per heading | Per the CV "Keyword Type that can be applied to this CoU (R/O)" column | IG §9.2.9.2; QA #13; eCTD4-070/071 |
| Site-id | Only with document type case report forms (`ich_document_type_25`) or subject profiles (`_57`) | QA #17; CV remark on `ich_keyword_type_10` |
| 4.2.2.1 | Document type is **required** | QA #18 |
| 5.3.5.4 | Send only one document type; the indication (R) is the *applied-for* indication | QA #21; CV remark |
| Novel excipient | Use the `excipient` keyword (no folder name) | QA #12 |
| facility / component / descriptor | New metadata; follow the M4 Granularity document | QA #9 |
| Study Group Order | Optional; codes 1–99; only with a study id_study title keyword, **ignored** without one. It does **not** replace priorityNumber | IG §9.2.10.1; IG §9.2.11.2; ORI p.40 |
| Group Title | Optional sender-defined keyword that sub-groups content under the lowest heading, only where the Granularity document allows multiple documents (shown as "group title (O)" in the CV). Use it even if there is only one CoU. **Only one** group title per CoU. It replaces node extensions | IG §9.2.10.2; IG §9.2.16.1; QA #10; ORI p.38 |
| Display | Read the display name from the code system, never from the message (EU-IG: displayName in the message is ignored) | IG §9.2.9.2; EU-IG "Keywords and Controlled Vocabularies for EU Purpose" |
| Sender OIDs | Companies may choose any unique identifier/OID, but not one already registered by an agency | VEN item 3.3; IG §6.5.1 |

### 5.2 Context group, priority number, ordering

| Rule | Detail | Source |
|---|---|---|
| Context group | All CoUs with the same **CoU code + codeSystem + keyword code(s)**. If any one differs, the context is different | IG Abbreviations "Context Group"; SUP p.30 |
| priorityNumber | Required on every component; a positive whole number, at most 999999; orders CoUs **within a context group**, within and across SUs of an application | IG §9.2.5; QA #20 (CR 00670); eCTD4-017/018/019 |
| Recommended numbering | Start at 1000 and step by 1000 (2000, 3000…) so you can insert later (e.g. 1500 sits between 1000 and 2000) | IG §9.2.5.2; IG §9.2.11.3.1 |
| No duplicates | Do not duplicate a number inside the same group. Numbers of replaced/suspended CoUs may be reused. Conflict handling is regional | IG §9.2.5.2 |
| Reorder | Send `<priorityNumber value="900" updateMode="R"/>` + CoU `id` + `statusCode active` only (no code, documentReference or keywords). A new CoU in the same SU does not use updateMode. Do not send an SU only to reorder | IG §9.2.11.3.2 |
| Suspend + number | For a suspension, a different priority number is not processed | SUP p.32 |
| Label | `originalText` does not affect order | IG §9.2.6.2; ORI p.31 |

### 5.3 Lifecycle (IG §9.2.11.3, §9.2.16; SUP p.31–35; QA #27)

| Operation | XML | Constraints | Rules |
|---|---|---|---|
| **New** | New CoU UUID, `code`, `statusCode active`, `documentReference` (new or existing document), keywords, `priorityNumber` | — | eCTD4-027, -076 |
| **Replace** (1:1, 1:n, n:1, n:n) | New CoU UUID + `replacementOf typeCode="RPLC"/relatedContextOfUse/id@root=<old CoU id>` (repeat replacementOf for many→1; repeat the same old id in several new CoUs for 1→many) + documentReference | Old and new must have the **same CoU code + keyword code combination**. The old CoU must be **active**: an obsolete CoU cannot be referenced again. The receiver marks the old one `obsolete`. The priority number is released | eCTD4-025, -026 |
| **Re-submit suspended content** | A **new** CoU that references the existing document id (no file re-sent) | Once suspended, a CoU id cannot be reactivated | IG §9.2.11.3.4; SUP p.32 |
| **Suspend (delete)** | `priorityNumber`, CoU `id` (same), `statusCode suspended`; **no** code, documentReference or keywords | Target must exist and be **active**. Transitions suspended→suspended and suspended→active are not allowed | eCTD4-080 (CR 00730, 00780; QA #25, #27); eCTD4-028 |
| **Change keywords / heading** | Suspend the old CoU + send a new CoU with the new combination (it may reuse the same document id). This breaks lifecycle; to keep a relationship, replace in a later sequence | Replacement may not change the combination. This also applies when the M4 Granularity document changes | IG §9.2.11.3; IG §9.2.16.4; SUP p.34 |
| **Change only a keyword display name** | keywordDefinition displayName `updateMode="R"` | Not a new keyword | IG §9.2.11.3; §9.2.18.6.2 |
| **Reorder** | priorityNumber `updateMode="R"` | — | IG §9.2.11.3.2 |
| **Fix a title typo** | `<document><id root=same/><title value="…" updateMode="R"/></document>` | Only for errors. It changes the title **everywhere** the document is referenced, across applications. For a really new title use a new document element (file reuse) | IG §9.2.17.2.1; QA #4; SUP p.35 |
| **Fix language** | `<document><id/><text language="en" updateMode="R"/></document>` | No checksum/reference/algorithm attributes (eCTD4-085) | IG §9.2.17.2.2 |
| Granularity change of headings (removed/added) | Scenarios: (1) keep old content + add new content under the new code (no lifecycle link); (2) suspend the old + add new; (3) suspend the old, re-point the same document under the new code, then replace it in a later sequence (keeps the relationship) | — | IG §9.2.16.4 |
| Removed headings: display | New SUs must not use a removed heading. Viewers keep showing old content under the old heading. **There is no ICH-level table of contents (outline) for v4.0**, and M8 will discuss one. Regions that add granularity to M2–M5 should go through ICH | — | VEN Open Discussion #2 |

### 5.4 Document reuse and file reuse

| Rule | Detail | Source |
|---|---|---|
| Document reuse | Send the `document` once. Afterwards any CoU (same SU, later SU, other submission, other application) references it by `documentReference/id@root`. The document element is not re-sent | IG §9.2.17.1 |
| Relevance | All of the reused document's content, including references and hyperlinks, must be relevant to the reusing submission | IG §9.2.17.1; SUP p.9 |
| Retention | Reuse depends on regional retention; see the Regional IG. **EU:** reuse works for CAPs from the start; NCAs/MRP/DCP need the Common Repository | IG §2 fn 2; EU-IG "Document Reuse" |
| Cross-company | No ICH validation rule stops another company referencing a UUID: regional matter | QA #6 |
| UUID version | No ICH region checks the UUID version. Rejection is for UUID collisions (eCTD4-046) | QA #7 |
| UUID case | **Treat UUIDs as case-insensitive** (ITU-T X.667). M8 agreed this, and an IG/Q&A clarification is pending | **VEN item 2.3** |
| Same document id across regions | Allowed, but the document element **and** file must be submitted to each region/agency | IG §9.2.15.2 |
| Document must be used | Every *new* document in an SU must be referenced by a CoU in **that same** SU | eCTD4-082 (CR 00720; QA #24); "unassociated document" vs "unassociated file" QA #15 |
| File reuse | When the same physical file needs a different title, create a **new document element** (new UUID) whose `reference@value`, `integrityCheckAlgorithm` and `integrityCheck` equal the original's. The path points to the original location: `m1/x.pdf` (same SU), `../99/m1/x.pdf` (another sequence), `../../NDA123456/99/m1/x.pdf` (another application). The file is sent only once | IG §9.2.15.2; IG §9.2.17.3 |
| Document has no status | Lifecycle never acts on a document. A document is relevant only while an active CoU references it | SUP p.31; EU-IG "Document" |

---

## 6. Validation and technical rules (IG §12; "eCTD4-NNN")

ICH rules cause **rejection in all ICH regions**. Regions may add their own (SUP p.37). The sender may resubmit with the **same sequence number** after a rejection (IG §12.2).
Column "Reg." marks rules whose *content* depends on regional CVs/IGs (R) or that apply only with Forward Compatibility (FC).

| Rule | Category | Criterion | Reg. |
|---|---|---|---|
| eCTD4-001 | Schema | Well-formed XML 1.0 | |
| eCTD4-002 | Schema | Valid against the ICH-specified RPS schema version | |
| eCTD4-079 | CV versioning | Code value is active (not retired) | |
| eCTD4-003 / -004 | SU | `submissionUnit/id@root` present / is a UUID | |
| eCTD4-005 | SU | Only one submissionUnit per message | |
| eCTD4-006 / -007 | SU | SU `code@code` present / valid (for the region) | R |
| eCTD4-008 / -009 | SU | SU `@codeSystem` present / valid registered OID | R |
| eCTD4-010 | SU | SU statusCode = `active` | |
| eCTD4-011 | SU | At least one CoU | |
| eCTD4-012 / -013 | Seq | Sequence number present / whole number 1–999999 | |
| eCTD4-014 | Seq | First SU in the application = `1` (see the §8 conflict) | |
| eCTD4-015 | Seq | Unique in the application | |
| eCTD4-016 | Seq | One and only one value per submission | |
| eCTD4-017 / -018 / -019 | Priority | Present / whole number 1–999999 / exactly one (the summary table in §12.1 still says "non-negative real number": superseded by QA #20) | |
| eCTD4-020 / -021 | CoU | `id@root` present / UUID, or namespace OID + local value | FC |
| eCTD4-075 | CoU | CoU code valid for its code system | R (M1) |
| eCTD4-022 / -023 | CoU | statusCode present / `active` or `suspended` | |
| eCTD4-080 | CoU | Suspend only an existing **active** CoU id or v3.2.2 leaf ref, after which it cannot be updated | FC |
| eCTD4-081 | CoU | CoU codeSystem a valid OID | |
| eCTD4-024 | RelCoU | relatedContextOfUse id present | |
| eCTD4-025 | RelCoU | Same CoU code + keyword combination (or matching v3.2.2 equivalents) | FC |
| eCTD4-026 | RelCoU | Only previously submitted **active** CoU / leaf ref (or region does not allow it) | FC, R |
| eCTD4-027 / -028 | DocRef | Required for active new CoU / not allowed for suspended | |
| eCTD4-076 | DocRef | Referenced document exists (v4 id or v3.2.2 leaf ref) | FC |
| eCTD4-029 / -030 | Keyword | code / codeSystem present | |
| eCTD4-031 / -032 | Keyword | codeSystem valid OID / code in an external CV or the application's keyword definitions | |
| eCTD4-070 / -071 / -072 | Keyword | Required keywords present / type valid for heading / one per type | |
| eCTD4-033 / -077 | Submission | id present / UUID | |
| eCTD4-034..037 | Submission | code + codeSystem present and valid **for the region** | R |
| eCTD4-038..042 | Application | id present; code present/valid; codeSystem present/valid OID | R |
| eCTD4-043..046 | Document | id present / valid / UUID / unique (not a duplicate and not a title update) | |
| eCTD4-047 | Document | title present | |
| eCTD4-048 / -049 | Document | Checksum present / valid (except for a title-only update) | |
| eCTD4-050 / -051 | Document | Path present (unless updateMode title change) / file exists | |
| eCTD4-082 | Document | New document referenced by a CoU in the same SU | |
| eCTD4-085 | Document | updateMode="R" not combined with content attributes | |
| eCTD4-052..058 | KeywordDef | code present/valid; value item code present/valid; value present; exactly one item; displayName present | |
| eCTD4-068 | KeywordDef | displayName as previously submitted unless updateMode | |
| eCTD4-073 | KeywordDef | `ich_keyword_type_8` uses `studyID_$studyTitle` | FC-critical |
| eCTD4-078 | KeywordDef | Must exist and match the v3.2.2 value | FC |
| eCTD4-083 | KeywordDef | codeSystem a valid OID | |
| eCTD4-059 | Package | `submissionunit.xml` exists (exact lower-case name) | |
| eCTD4-060 | Package | `sha256.txt` exists (exact lower-case name) | |
| eCTD4-061 | Package | Only one submissionunit.xml | |
| eCTD4-062 | Package | sha256.txt matches the computed hash of submissionunit.xml | |
| eCTD4-063 | Package | submissionunit.xml at the top of the sequence folder | |
| eCTD4-064 | Package | Each document checksum matches its file | |
| eCTD4-065 / -066 / -067 | Package | File name ≤ 64 / folder name ≤ 64 / path ≤ 180 | (R may tighten) |
| eCTD4-074 | Package | Only allowed special characters in the path | |
| eCTD4-069 | Package | Unassociated file found | (R exceptions) |
| eCTD4-084 | Header | Both a valid ICH IG OID and a valid Regional IG OID in the header | R |

Additional notes:
* **Inconsistency in the IG:** rule eCTD4-021 and the §12.1 summary table speak of a "unique identifier" for the CoU; QA #19 / CR 00660 made the UUID type explicit for CoU, Document, SubmissionUnit and Submission.
* **Pending (VEN item 2.2):** regions agree there should be a validation for the `_$` nested node-extension → Group Title mapping. No criterion yet.
* **Regional rules model (EU-IG "XML MESSAGE VALIDATION RULES"):** the EU adds checks on valid code/codeSystem pairs for Territorial Authority, Submission Reference, Submission, Submission Group (must continue through all sequences of the activity), Mode, Applicant (status active), Review Procedure, Application Reference (1..1), Review (only one), Product Category (only one), Regulatory Status (only one). The EU states "All code / codeSystem combinations are expected to be currently valid."

---

## 7. What a region must define, and how the EU did it (the likely EDA model)

### 7.1 Items the ICH IG leaves to the region

| Item | ICH reference | EU solution (EU-IG v1.2 draft) |
|---|---|---|
| Regional IG OID + version (header item 2) | IG §9.1.2; eCTD4-084 | EU root `2.16.840.1.113883.3.989.5.1.1` (ich-estri / regional-specialised(5) / sub-reg(1) / eu(1)). **EU M1 IG v1.2 = `…5.1.1.6.1.2`** (v1.0 = `…6.1.1`). EU M1 CV package = `…5.1.1.6.2.1` ("EU M1 Controlled vocabularies v1.0"; EU-IG "CONTROLLED VOCABULARIES") |
| First-level folder name | IG §5.1, §5.2 | Application number, lower case, punctuation removed: `ema000123`, `de2087`, `de2131577`, `emavr111223`. Grouping/worksharing zip: `de0001g`, `es0002ws`, `ema0011g`. PSUSA: `PSUSA00002172` |
| Sequence folder | IG §5.1 | Sequence number 1–999999; "The first submission in eCTD v4.0 format will have sequence number '1'" |
| m1 structure | IG §5.1 | **Single flat `m1` folder**. Country, dosage, strength and language are keywords, not folders (the 13-pi language folders are replaced by `text@language`) |
| File formats | IG §5.5 | Separate annex "EU Accepted file formats – eCTD v4.0" (e.g. PDF/A-1, PDF/A-2, 1.4–1.7; bmp etc. only for M1.3.2/1.3.3) |
| M1 Context of Use list | IG §6.2 | "EU eCTD Context of Use" OID `2.16.840.1.113883.3.6905.1.17.1`, numeric SPOR-RMS term ids (e.g. `100000164029` = M1.0 Cover Letter, `100000164032` = 1.3.1 SmPC, Label, PL) |
| Regional keyword CVs | IG §6.2 | Country `…6905.1.1.1` (e.g. 100000000395 France); EU document type `…6905.1.18.1` (100000155532 SmPC); dose form `…6905.1.14.1` (100000073665 film-coated tablet); `…6905.1.16.1` used with code `fr` as a CoU keyword (the IG text does not name this list; probably language/country ISO). **Country keyword required** for CoU "10-cover", "12-form", "13-pi", "additional-data", "responses" |
| Regional keyword-definition types | IG §6.2; §9.2.18 | Only **`eu_keyword_definition_type_2` = strength**, type list OID `…6905.5.1.1`, value pattern `FIGURE_UNIT`, e.g. `30_mg`, `1_milligram(s)/millilitre`. It is the only definition allowed in M1. ICH M2–M5 types still apply in M2–M5 |
| Application type | IG §9.2.14 | "EU Application Code – Legal Basis" `…6905.1.4.1` (e.g. 100000116047). `application/id/item@root` = the dossier UUID (the v3.2.2 envelope UUID is kept) + `@extension` = procedure number. For MRP/DCP, repeat `id/item` for national numbers (`de-2189072`, …) |
| Submission (regulatory activity) | IG §6.2 | Submission type `…6905.1.11.1` (100000155689 = initial MA); `id/item@root` UUID stays the same for the whole activity; `@extension` = procedure number; only one item; status only `active` |
| Submission unit type | IG §9.2.4 | `…6905.1.8.1` (100000155047 "Initial"); status only `active`; an SU or Submission cannot be suspended, so a withdrawn or rejected activity is handled by a **"consolidating"** SU |
| Contact party | IG §6.2 | Contact party role `…6905.1.6.1`; contact-party lifecycle section |
| Review / product | IG §4.7.1 | Review with manufacturedProduct (dose form `…1.14.1`; country-specific names through asNamedEntity/assigningTerritory with country `…1.1.1`); authority `…6905.1.12.1` (100000160631 FR-ANSM); product category `…6905.1.9.1` (100000155527 Chemical) |
| Review procedure | IG §4.7.1 | `…6905.1.7.1` (100000155060 Decentralised Procedure) |
| Mode | IG §4.7.1 | `…6905.1.10.1` (100000155556 worksharing); used only for variations/line extensions, in every sequence of that activity |
| Application reference | IG §4.7.1 | Reason `…6905.1.5.1` (100000155053 reference medicinal product for bioequivalence) |
| Substances / organisations | IG §6.2 | SPOR SMS `…6905.2.1` and OMS `…6905.4.1`. These are dynamic lists, **not** in genericode; looked up through UI/API and validated on receipt |
| Extra document metadata | IG §9.2.15 | `document/confidentialityCode` `…6905.1.15.1` (200000004984 Confidential, …85 Public, …86 Restricted); `text@language` required for m1-3-1 documents; `mediaType` for special formats; `description` not used in M1 |
| Elements not used | IG §4.7.1 | EU drops categoryEvent, review.holder.applicant, regulatoryReviewTime |
| Per-CoU addressee | IG Table 11 | `primaryInformationRecipient` restricts a CoU to one authority (e.g. an ANSM fee form in a DCP) |
| Hide CoU for some submissions | IG Table 11 | `subjectOf@negationInd="true"/submissionReference/id/item@root=<submission UUIDs>` (not for CAPs) |
| Dossier management, grouped submissions, two-way communication | IG §4.8; §10 | Grouped: Scenario 1 = one submissionunit.xml per application, with the common files in one of them; Scenario 2 = one XML for several sequences when 100 % of files are common (PSUSA). Joining a grouped v4 submission switches **all** included applications to v4. Two-way communication is not planned in the EU |
| Regional validation rules | IG §12 | See §6 above |
| FC specifics (leaf-reference values, open activities) | IG §8, §8.1.1 | The EU regional backbone type becomes `eu-regional` regardless of the M1 spec version (2.0/3.x). The principles are the same as ICH |
| Maintenance | IG §6.2 | The EU puts all regional CVs in SPOR-RMS and versions them on the ICH model (spreadsheet + genericode). ICH lists are maintained by M2/M8 |

### 7.2 Implications for an EDA M1 (inference; not stated by any source)
EDA will need to: obtain or register an OID branch (the EU pattern is under `2.16.840.1.113883.3.989.5`, regional-specialised); publish an M1 IG with its own OID;
publish versioned regional CVs (CoU M1, SU/Submission/Application types, country/authority, regional keyword types) in genericode + xlsx;
decide the first-level folder and sequence rules, file formats, retention/reuse policy (the EU shows reuse depends on a repository), FC leaf-reference
conventions (`ApplicationTypeApplicationNumber.sequence.xmlType.leafId` needs an EDA application-number syntax and an XML-type code. The ICH XML Types list has **no Egypt/EDA regional value**, so a CR to ICH would be needed if EDA's v3.2.2 regional XML is to be referenced), and grouped-submission rules.
Per VEN Open Discussion #2, any extra M2–M5 granularity should go through ICH.

---

## 8. Transition v3.2.2 → v4.0 (Forward Compatibility)

| Rule | Detail | Source |
|---|---|---|
| When | FC is used for **any** dossier with v3.2.2 content converted to v4.0. Aims: seamless display in one tool, lifecycle of *active* v3.2.2 content, reuse of v3.2.2 documents (also from applications not yet converted) | IG §8 |
| No way back | After the first v4.0 SU of an application, a v3.2.2 SU is **rejected** | IG §8 |
| Open activities | Each region decides | IG §8 |
| Only current content | Lifecycle is only possible on active leafs (new/replace in the current view) | IG §8.1 |
| Sequence number | The first v4.0 SU = **the next number as a whole number**: after v3.2.2 `0003` comes v4.0 `4` | IG §8.1 |
| Leaf reference | `id@root="2.16.840.1.113883.3.989.2.2.1.13.1"` + `id@extension=<leaf ref>`, on contextOfUse (**suspend only**), relatedContextOfUse (replace) or documentReference (reuse) | IG §8.1.1; §9.2.6–9.2.8 |
| Leaf-ref patterns | Same application: `sequenceNumber.xmlType.leafId`, e.g. `0000.ich#NLAS57D17EB601C9EDCA`. Across applications: `ApplicationTypeApplicationNumber.sequenceNumber.xmlType.leafId` (e.g. `nda123456.0000.ich#…`, `nda123456.0000.us-regional#…`) or `UUID.sequenceNumber.xmlType.leafId` (`5f0e8436-…-413deff109e5.0000.ich#…`). Sequence = the 4-digit v3.2.2 value. xmlType from "ICH XML Types" (`ich`, `us-regional`, `eu-regional`, `ca-regional`, `ch-regional`). Exact values: per Regional IG. *(The IG text says "sequenceNumber.xmlType.leafId" but the examples use `#` before the leaf ID, not `.`; follow the examples.)* | IG §8.1.1; CV "ICH XML Types" |
| Validity | The leaf reference must exist in the receiver's system (eCTD4-076/080/026) | IG §9.2.6–9.2.8 |
| Document metadata | A reused v3.2.2 document keeps its existing metadata unchanged | IG §9.2.8.2 |
| Replacing v3.2.2 content | Follows v4.0 context-group rules. The keywords must equal **all** v3.2.2 attributes, node-extensions, file-tags, property and categories. The CoU heading may differ between v3.2.2 and v4.0, but the v4.0 CoU must match the v3.2.2 set of attributes/STF metadata (CR 00820) | IG §8.1.2; IG §9.2.9.2; eCTD4-025 |
| Mapping (Table 9) | index.xml `indication, substance, manufacturer, product-name, dosageform, excipient` → sender keywords (keywordDefinition **first**). `node-extension` → **Group Title** (only when no equivalent keyword exists); nested node-extensions are joined into one Group Title with delimiter **`_$`** (CR 00840). STF `study-id` + `title` → one keyword `ich_keyword_type_8` `studyID_$title` (must match the STF). STF `category` (duration, route, species, type of control) → ICH CV keywords. STF `file-tag` → ICH Document Type keyword. STF `property` site-id → site-id keyword definition | IG §8.1.2 Table 9 |
| Matching values | `keyword.code@code` is only a pointer. What must match the v3.2.2 value is **`displayName@value`**, exactly (no abbreviation or reformatting). Codes need not be readable | IG §8.1.2; IG §9.2.18.2; eCTD4-078 |
| Appended leafs | Replacing in v4.0 lifecycles the appended content together with its leaf | IG §3.4 |
| Baseline / TMM | The **Transition Mapping Message was removed** (CR 00710, IG v1.5) and replaced by FC. **The ICH sources define no baseline/transition submission.** EU-A1 (2018) still describes a TMM, which is outdated. The EU IG says only "Presumably, the same rules on baselining can be applied" for non-eCTD legacy dossiers. QA #8 and #11 refer to TMM-only vocabularies (ICH Submission / Submission Unit types) that are **not** in CV v1.0.3 | IG change history v1.5; EU-IG "COMPATIBILITY…"; EU-A1 §5; QA #8, #11 |
| Pilots / tools | Industry concern over FC test-tool availability was raised; no response | VEN Open Discussion #1 |

> **Conflict to resolve with EDA:** the ICH IG says the first v4 SU after v3.2.2 `0003` is `4` (IG §8.1). Rule eCTD4-014 says the first SU "in the
> application" is `1`, and EU-IG "Second Level Folder Naming Requirements" says "The first submission in eCTD v4.0 format will have sequence number '1'".
> Reading: `1` applies to applications that *start* in v4.0, and `last+1` to converted dossiers. The sources do not say this explicitly.

---

## 9. Latest status: M8 Vendor Group, 30 Sep 2026 (VEN)

| # | Topic | Outcome | Impact on a tool |
|---|---|---|---|
| 1 | Published specs | IG Package **v1.7**, CV Package **v1.0.3**, Q&A **v1.10** posted. The Implementation Status Table was updated in August 2026 (its content is not in the minutes) | Header OID `…11.6`; CoU `…1.1.6` |
| 2.1 | eCTD4-055 | It **fails** when the same sender code + codeSystem is defined for different keyword types. It checks more than syntax. Sponsors may not do this | Keep sender codes unique per type in each application |
| 2.2 | `_$` node-extension delimiter | Regions agree a validation is needed and are still choosing the approach; no rule yet. Vendor concerns: hard to tell continuation from a new study; FDA used STF, not node extensions; M8 will discuss. (Comment: for a *suspend* only the identifier matters, not node-extensions/keywords) | Implement the `_$` concatenation now; expect a future rule |
| 2.3 | UUID case | **Case-insensitive** comparison (ITU-T X.667). An IG/Q&A clarification is coming. Regional documents may be outdated | Compare case-insensitively; keep the original case when emitting |
| OD1 | FC pilots | Tool availability concern; no answer | — |
| OD2 | Removed headings / hierarchy | No ICH outline for v4.0; old content stays visible under retired headings; M8 to consider publishing a ICH-level CTOC; regional M2–M5 granularity should go via ICH | The viewer must build the hierarchy from the CoU code itself |
| OD3 | Sponsor OIDs | Free choice of a unique identifier/OID, but not one already registered | — |
| OD4 | Flat structure | Multiple instances of the same heading with different keywords (e.g. several substances/products in M3) are allowed, "as in 3.2.2" | — |
| Next | — | Next meeting "Winter – TBD". Questions to ICHM8Vendors@ich.org | — |

**Closed CRs in IG v1.7 / CV 1.0.3 (QA sheet "Change Requests"):** 00770 (eCTD4-084 header OIDs), 00780 (eCTD4-080 suspend rules),
00790 (`ich_2` retired), 00800 (SU statusCode only active), 00810 (node-extensions in Table 9), 00820 (FC match on displayName; CoU headings may differ),
00830 (eCTD4-085), 00840 (`_$` delimiter). **No open/proposed CR is listed** after 00840. The next IG version is **not announced** in the sources. The pending items are the UUID case-insensitivity text and a `_$` validation (VEN 2.2, 2.3).

---

## 10. Gaps and items to confirm (stated plainly)

1. **No EDA-specific source** in the folder. Every regional value (OIDs, M1 CoU, SU/submission/application types, folder naming, file formats, FC leaf-reference syntax) is unknown until EDA publishes an M1 v4.0 IG.
2. **No complete IG example instance.** The skeleton in §3.4 is assembled by this KB. It passes the schema, but the business rules eCTD4-001…085 still have to be implemented separately.
3. `sha256.txt` byte format is not specified (§2.2 gap).
4. The `ICH Controlled Vocabulary Package` OID (`…14.2`) has no stated place in the message.
5. CoU v5 (`…1.1.5`) has a blank end date in the Index. Whether v5 is still valid after v6 (which only removed `ich_2`) is not stated. Under IG §6.6.2.3, a removal "may trigger" retirement.
6. CV/genericode start date mismatch for CoU v6 (xlsx 2026-05 vs genericode `2026-04`).
7. IG inconsistencies: schema file names in §7.2.1 vs the shipped UV02; outdated OIDs in samples; the `…95.2` typo in §9.2.19; priority number "real" vs "whole number"; FC pattern dot vs `#`; the sequence-number "1" vs "last+1" conflict (§8). Also, IG §5.3 gives the path example `m2/23-qos/introduction.pdf`, while IG §11.1 says m2 has no subfolders.
8. Baseline/transition submission for v3.2.2 → v4.0 is **not defined by ICH** (TMM removed). Regional business rules are needed.
9. The EU-IG used is a **2024 draft (v1.2)**. Its numbered cross-references (e.g. "section 9.17") do not match its unnumbered headings. Some EU list identities (e.g. `…6905.1.16.1`) are inferred from samples. `eu_nmv.html` is a 404 page, so the EU "NMV" content is missing.
10. EU-A1 (2018) is historical: it describes the TMM and optional use from 2020. Do not use it for current rules.
11. Specification for Submission Formats (PDF rules) is referenced but **not** in the folder.
12. The ICH M4 Granularity document (which headings allow several documents / group title) is referenced but not in the folder. The CV "group title (O)" column stands in for it.
