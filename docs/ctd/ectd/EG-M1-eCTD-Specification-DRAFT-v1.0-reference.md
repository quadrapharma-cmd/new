# EG Module 1 eCTD Specification — DRAFT v1.0 (2026): implementation reference

> **STATUS: DRAFT — NOT ADOPTED.** This file documents the Egyptian Drug Authority (EDA) public-consultation draft
> *"EG Module 1 eCTD Specification", Year 2026, Version No: 1.0* (Code, Issue Date and Effective date printed blank).
> Consultation window 02/09/2026 – 14/10/2026 and the source URL
> `https://edaegypt.gov.eg/media/5bqn4tnh/draft-of-eg-module-1-ectd-specification-_2026.pdf` come from the request that
> commissioned this file — **the PDF itself never uses the words "draft" or "consultation"** (checked by full-text search).
> Anything here can change before adoption. Do not build a validator that rejects real submissions on the basis of this file
> without re-checking the adopted text.
>
> **Rules of this file.** Every rule cites the page (printed page = PDF page, 1–79) and, where the draft prints them, its
> margin line numbers (`l. 1–347`). Nothing is from memory. Text in "quotes" or in code blocks is verbatim. Where the draft
> is silent, wrong or self-contradictory this file says so (**GAP**, **AMBIGUOUS**, **ERROR**). Comparison material
> (EU M1 v3.1.1, ICH eCTD v3.2.2, the EG *Technical Guidance* draft) is used **only** in §9 and in clearly marked notes.

Source file used: local copy `eg_m1_spec_draft.pdf`, 79 pages, MD5 `1919ea99a00183c322988018261ddda9`; PDF metadata:
Author "qa4", Creator "Microsoft® Word for Microsoft 365", Producer "iLovePDF", CreationDate 2026-08-30, ModDate 2026-09-02.
The only images in the PDF are the page-header logos (checked with `pdfimages -list`), so no content is hidden in pictures.
Text extracted with `pdftotext -layout` and `-raw`; the Appendix 2 table was parsed programmatically and checked by hand.

Short cites used below: **SPEC** = this EG draft; **TG** = EDA draft *Technical Guidance for eCTD Submissions in Egypt*
v1.0/2026 (cited by its own section numbers); **EU** = EU Module 1 eCTD Specification v3.1.1 / EU DTD 3.1 as recorded in
`docs/ctd/ectd/EU-M1-3.1.1-reference-model-for-EG.md`; **ICH** = `docs/ctd/ectd/ICH-eCTD-3.2.2-reference.md`.

---

## 1. Document identity, scope and glossary

### 1.1 Identity (SPEC p. 1–2, p. 79)

| Item | Value as printed | Page |
|---|---|---|
| Title | "EG Module 1 eCTD Specification" / "Year 2026" | 1 |
| Document class | "Guideline" | every page header |
| Issuing bodies (header) | Central Administration of Pharmaceutical Products — General Administration For Human Pharmaceuticals Registration; Central Administration for Biologics, Innovative Products, and Clinical Studies — General Administration of Biological Products; General Administration of Innovative Products | every page header |
| Code | blank ("Code:" / "Code: ………………") | 1, footers |
| Version | "Version No: 1.0"; footer "Version/year: 01/2026" | 1, footers |
| Issue date / Effective date | "--/--/----" / "--/--/----" | 1 |
| History table | "New Issue", Issue date blank, Version 1.0 | 79 (l. 343–344) |
| Table of contents | Glossary 3 · Introduction 6 · Regional File Formats 6 · Module 1 6 · Handling of Empty or Missing eCTD Sections 6 · Updating backbone attributes/metadata 7 · General Architecture of Module 1 7 · Envelope 8 · m-1-eg 8 · Directory / File Structure 9 · Node Extensions 9 · File Naming Convention 10 · Folder and File Name Path Length 11 · UUID 11 · Change Control 13 · Appendix 1 14 · Appendix 2 28 · History Table 79 | 2 |

Section headings are **unnumbered** in the body; this file cites them by page and margin line.

### 1.2 Scope (SPEC p. 6 l. 1–6; p. 13 l. 236–237)
* "This document specifies Module 1 of the electronic Common Technical Document (eCTD) for the Egyptian Drug Authority
  (“EDA”) in Egypt (“EG)”." (l. 2–3)
* "This document should be read together with the ICH eCTD Specification to prepare a valid eCTD submission for EDA. The
  latest version of the ICH eCTD Specification can be found at: https://www.ich.org/page/electronic-standards-estri." (l. 4–6)
* The eCTD version is named only once: "For any proposed changes to the eCTD v3.2.2 specification or the related validation
  rules, please raise a support ticket via the online form in the portal." (p. 13 l. 236–237) → the draft targets
  **ICH eCTD v3.2.2** (DTD-based), not eCTD 4.0.
* **GAP:** the draft never states which product types, procedures or applicants are in scope. It points to the TG three
  times, without version or date: "associated technical guidance for eCTD submissions Egypt" (p. 8 l. 84–85),
  "Technical Guidance for eCTD Submissions in Egypt" (p. 10 l. 146–147) and "Technical Guidance Document" (p. 17).

### 1.3 Glossary (SPEC p. 3–5) — terms that matter for implementation

| Term | Definition (verbatim, condensed only where marked …) | Implementation consequence |
|---|---|---|
| Applicant | "The authorized person or company who submits an application for marketing authorization of a new medical product, an update to an existing marketing authorization or a variation to an existing marketing authorization." | `applicant` envelope element |
| Applicant's Information | "Regulatory information submitted by an applicant for, or to maintain, a marketing authorisation that falls within the scope of this guidance document." | — |
| DTD | "A set of rules that defines the structure, elements, and attributes allowed in an XML file. … The DTD acts like a blueprint …" | the EG DTD itself is **not** in the draft (see §3, §8) |
| eCTD application / dossier | "A collection of electronic documents compiled by a pharmaceutical company or its agent in compliance with Egyptian legislation and guidelines in order to seek marketing authorisation or any amendments thereof. An eCTD application may comprise a large number of regulatory activities. For products with different dosage forms and strengths are submitted under separate applications." | **one eCTD application (one UUID) per strength / dosage form** (sentence is ungrammatical but the intent is clear) |
| Envelope | "Part of the eg-regional.xml file containing high-level metadata about the submission package. See section Envelope" | file name `eg-regional.xml` |
| High Level Number | "Submission Number. This number represents the high-level procedure number related to the regulatory activity in case of submissions of grouped variations if multiple products are concerned. Samples are provided in the EG M1 Specification. Note: not required in case only one product is concerned. Issued by EDA through the portal." | `submission/number`; self-reference "Samples are provided in the EG M1 Specification" inside the EG M1 Specification (copied from TG) |
| Procedure Tracking Number | "Unique identifier assigned to the application procedure. Issued through the EDA portal" | `procedure-tracking/number` |
| Regulatory Activity | "A single sequence or a collection of sequences covering the start to the end of a specific business process, e.g. an MA application or variation. … classified using a controlled vocabulary (submission type or regulatory activity type) and a free text field for a short narrative description." | `submission/@type` + `submission-description` |
| Sequence | "… Sequences may be related to one another within one regulatory activity. The related sequence number should always be stated. In case of activities with only one sequence the same sequence number will be used." | `related-sequence` always present |
| Submission Type | "The submission type describes the regulatory activity to which the content will be submitted." | — |
| Submission Unit Type | "… describes the content at a lower level (a “sub-activity”) which is submitted in relation to a defined regulatory activity such as the initial submission, the applicant response to validation issues or list of questions or any other additional information." | `submission-unit/@type` |
| Working Documents | "working-documents folder can be added to a submission for documents requested by the authority these documents should be placed outside the eCTD structure and named for example 0000-workingdocuments. The working document folder can be included in the zip file at the top-level structure for example 0000 and 0000-workingdocuments would be the two folders in the zip file." | zip layout: `DDDD/` + `DDDD-workingdocuments/` side by side |

Terms the TG glossary has but this draft does **not**: Active Substance Master File holder, Baseline Submission,
Non eCTD Submission.

---

## 2. Regional file formats, empty sections, backbone metadata

| Topic | Rule (verbatim or close paraphrase) | Cite |
|---|---|---|
| Recommended format | "Generally, the recommended file format for content documents is PDF." | p. 6 l. 10 |
| PDF versions | "All PDF files included in an eCTD (irrespective of the module) should be versions 1.4, 1.5, 1.6, 1.7, PDF/A-1 and PDF/A-2 except where there is an agency-specific requirement for a later version (e.g. for an application form)." | p. 6 l. 10–13 |
| Format list | "For the latest acceptable file formats list, please refer to the document “EG Accepted File Formats for eCTD”." **GAP:** that document is not part of the draft. | p. 6 l. 14–15 |
| Other formats | "Other formats (not specified in the document) for Module 1 content provided outside of the eCTD in the working-documents folder should be used as required by EDA." / requested data in other formats: "follow the instructions given by requestor". | p. 6 l. 15–19 |
| Placeholders | "Placeholder documents highlighting 'no relevant content' should not be included in the eCTD." Sections without information "should be left empty and justified in the respective Module 2 document, as relevant." | p. 6 l. 21–24 |
| "Not Applicable" M1 docs | "should not be included in the eCTD unless requested by EDA. However, when a justification for the absence of a certain document in Module 1 is required, such justification should be provided in its corresponding section in the eCTD structure." | p. 6 l. 25–28 |
| Style sheet | "The EG Module 1 is provided with a standard style sheet … designed to display the complete Module 1 table of contents (i.e. all the sections), irrespective of whether files are present". **GAP:** style-sheet file name and content not supplied. | p. 6 l. 29–31 |
| Updating backbone attributes | "It is not possible to update XML backbone attributes such as ‘manufacturer’ during the eCTD lifecycle, nor is it necessary to attempt workarounds such as deleting existing documents and resubmitting them with new attributes. The recommendation is to retain the obsolete entry and to rely on the document content to explain the current details unless otherwise requested by EDA." | p. 7 l. 33–36 |
| Changing EG M1 metadata mid-procedure | "deemed to be very rare"; "recommended to contact EDA whether such change could be done during the procedure, along with other changes, or as part of an eCTD “reformat” submission." | p. 7 l. 37–40 |
| No re-submission of documents | "any file(s)/document(s) already submitted in previous sequences should not be added again in eCTD … Applicants are encouraged to provide cross reference/hyperlink across sequences" | p. 8 l. 68–71 |

Engineering reading: an M1 builder must never emit an empty "N/A" leaf; empty element nodes are simply omitted from
`eg-regional.xml` (the style sheet still shows the heading). For backbone attributes that cannot change (e.g. `pi-doc`
`xml:lang/type/country`), a change is out-of-band (contact EDA / reformat).

---

## 3. General architecture (SPEC p. 7 l. 42–60; p. 8 l. 62–67)

| Item | What the draft says | Cite | Status |
|---|---|---|---|
| Model | "EG Module 1 architecture is similar to that of Modules 2 to 5 of the eCTD, comprising a directory structure and a backbone with leaves." | p. 7 l. 43–44 | — |
| Validity | "The backbone must be a valid XML document according to the EG Regional Document Type Definition (DTD)." | p. 7 l. 44–45 | DTD not supplied |
| Instance file | "The backbone instance (the “eg-regional.xml” file) contains meta-data for the leaves, including pointers to the files in the directory structure." Location `m1/eg/eg-regional.xml` (App. 2 row 2). | p. 7 l. 45–47; p. 29 | — |
| Root element | "The root element is “eg-backbone” and contains two elements: “eg-envelope” and “m1-eg”." | p. 7 l. 48–49 | **AMBIGUOUS**: App. 1.1 calls `eg-envelope` "the root element" (p. 14 l. 242 and table row 1) |
| Modules | "The EG Regional DTD is modularised, i.e. the envelope and leaves are referenced from the main part of the DTD as external entities called respectively "eg-envelope.mod" and "eg-leaf.mod "." | p. 7 l. 50–51 | file names given; content not supplied |
| Leaf | "The EG “leaf” is identical to the leaf element described in the ICH eCTD DTD; reference is made to Table 6-8 of the ICH eCTD Specification." | p. 7 l. 52–53 | → ICH leaf attributes apply |
| XML examples | "Examples of XML coding for a simple new application, specific regulatory activities are provided as an appendix to this specification. Examples of XML coding that support the variation regulation are provided as well in Appendix 1 … and Appendix 2". | p. 7 l. 54–57 | **ERROR/GAP**: neither appendix contains any XML |
| Cross-references | "Files can be referred to across modules (e.g. from Module 1 to Module 2) or across sequences within the same eCTD application; note however that it is not possible to refer to files in sequences in other eCTD applications." | p. 7 l. 58–60 | — |
| Relative hrefs | "the reference must always be relative, starting from the location of the XML file." Example: from `0003/m1/eg/eg-regional.xml` to `0000/m2/22-intro/introduction.pdf` → `"../../../0000/m2/22-intro/introduction.pdf"` ("This example is not business-specific"). | p. 8 l. 62–67 | — |
| DTD file name | **not stated** (the string `eg-regional.dtd` does not occur anywhere) | — | **GAP** |
| DTD version / `dtd-version` attribute | **not stated** | — | **GAP** |
| DOCTYPE / public identifier | **not stated** | — | **GAP** |
| Namespaces (`xmlns:eg`, `xmlns:xlink`) | **not stated**; whether the root is prefixed (`eg:eg-backbone`, as `eu:eu-backbone` in the EU) is unknown | — | **GAP** |
| Style-sheet file name / `<?xml-stylesheet?>` | **not stated**; only "The style-sheet to be used should be the most recent version, which is always published as part of the specification package for download" (App. 2 row 183, p. 77) | p. 77 | **GAP** (no "specification package" accompanies the draft) |
| Where the EG DTD lives | Row 181 `m1/eg/util/dtd` "Additional folder to hold DTD files used in EG." vs row 182 `util/dtd` "ICH specified location for eCTD DTD files." | p. 76–77 | **AMBIGUOUS**: which of the two holds `eg-regional.dtd` / `.mod` files |
| How `index.xml` references `eg-regional.xml` | **not stated** in the draft. (ICH note, not EG text: the ICH DTD models Module 1 in `index.xml` as leaves, and the regional XML is "referenced by a leaf in index.xml" — ICH reference file, tree comment for `m1/`; ICH App. 4 row 7 `m1/xx` "the regional xml instance should be located in this folder".) | — | **GAP** |
| `eg-regional.xml` leaf operation | "Note that the operation attribute for the eg.regional.xml should always be set to ‘new’." (sic "eg.regional.xml") | p. 29 row 2 | — |

---

## 4. Envelope (SPEC p. 8 l. 72–88; Appendix 1.1, p. 14–26)

### 4.1 General rules from the body text
* "The “eg-envelope” element is designed to be used for all types of submissions (MAAs, variations, renewals, etc.) for a
  given medicinal product and will mainly be used for the first simple processing at EDA level. The envelope provides
  meta-data at the eCTD application and sequence level." (p. 8 l. 73–76)
* "The envelope element submission ‘mode’ should only be used in variation regulatory activities, and the value can be set
  to: ‘single’, ‘grouping’, ‘parallel-single’ or ‘parallel-grouping’ (see examples in Appendix 1.1)." (p. 8 l. 78–80) —
  **GAP:** Appendix 1.1 has no mode examples.
* High-level number: "An additional high-level submission number should also be provided in the envelope under the following
  circumstance: • For submissions of grouped variations that affect multiple marketing authorisations Here, the submission
  ‘mode’ will be ‘grouping’ and the high-level number applied is generated from the EDA portal." (p. 8 l. 80–85) "Such a
  high-level number, if appropriate, should be provided in addition to the usual product-specific procedure tracking
  numbers." (l. 86–88)
* Intro to App. 1.1: "The list of elements is provided in the Controlled Vocabulary (CV) Lists. The following table indicates
  a subset of data elements taken from different controlled vocabulary lists and describes the only allowed terms for usage
  in eCTD submissions." (p. 14 l. 243–244) — **GAP:** none of the CV lists (Submission Type CV, submission mode CV-list,
  Submission Unit CV, Registration Type CV, Marketing Type CV) is reproduced in the draft.

### 4.2 Every element and attribute (App. 1.1 table, p. 14–20), in the draft's order

"Constraint" and "Occurrence" columns are copied as printed. "Kind" = whether the draft puts the name in its *Element* or
*Attribute* column (the draft's column layout is the only evidence of element vs attribute).

| # | Name | Kind (column) | Parent (inferred from table order) | Constraint | Occurrence | Description / instruction (verbatim, condensed with …) | Example (verbatim) | Page |
|---|---|---|---|---|---|---|---|---|
| E1 | `eg-envelope` | Element | `eg-backbone` (p. 7) | Mandatory | Unique | "Root element that provides meta-data for the submission." | N/A | 14 |
| E2 | `envelope` | Element | `eg-envelope` | Mandatory | **Repeatable** | "Parent element for the submission meta-data." | N/A | 14 |
| A1 | `country` | Attribute | `envelope` | Mandatory | Unique | "The country is EGYPT (EG)." | `eg` | 14 |
| E3 | `identifier` | Element | `envelope` | Mandatory | Unique | "A UUID as specified by ISO/IEC 11578:1996 and ITU-T Rec X.667 \| ISO/IEC 9834-8:2005. The same UUID will be used for all sequences of an eCTD application." | `25635f23-a3a4-c4e0- b994-99c5f074960f` (printed with a space; see §10) | 14 |
| E4 | `submission` | Element | `envelope` | Mandatory | Unique | "Provides administrative information associated with the submission." | N/A | 14 |
| A2 | `type` | Attribute | `submission` | Mandatory | Unique | "The type of regulatory activity to which the content will be submitted. The list is available in the Submission Type CV. N.B. Officially, Roman numerals are used for variations, e.g. Type VAR PAC-II – the elements must remain Arabic, however." | `maa` | 14 |
| A3 | `mode` | Attribute | `submission` | Optional "(note that this element must be populated for sequences in variations)" | Unique | "The high-level handling of the information submitted as part of variation(s) The mode should only be used in variation regulatory activities and must be included in every sequence of that activity. The list is available in the submission mode CV-list:" (values in §4.3) | — (none) | 15 |
| E5 | `number` | Element | `submission` | Optional | Unique | "This is the high-level submission number, to be used when grouping variations for multiple marketing authorisations. In case of a grouping concerning only one single marketing authorisation this number field should be left empty. In case of grouped variations applying to more than one MA, a separate eCTD submission must be built for each MA covered by the variation. In the envelope of each of the eCTD submissions, the high-level submission number will be the same, but the individual tracking numbers listed here should be specific to the MA in question. Please ensure that these grouping numbers are always mentioned in the case of additional information otherwise the Agency might not be able to process your submission correctly. (Note that for submissions affecting multiple MAs, the ‘xxxx’ used in the submission number is a sequential number) This number is issued through the online form on the EDA portal." | `B-GV-xxxx` or `B-PGV-xxxx` or `I-GV-xxxx` | 16 |
| E6 | `procedure-tracking` | Element | `submission` | Mandatory | Unique | "Provides administrative information to track the submission." | N/A | 17 |
| A4/E7 | `number` | printed in the **Attribute** column | `procedure-tracking` | Mandatory | **Repeatable** | "This is any number used by the EDA or the applicant to track the submission, in any procedure, in relation to a particular product. This could be one or more of the following: • P-VAR-PAC-N-0002 • I-IPV-PU-0001. There must be at least one tracking number identified from EDA and, in addition, the applicant can choose to include an internal tracking number. This procedure tracking number is issued through the EDA portal. In case grouped variations applying to more than one MA, a separate eCTD submission must be built for each MA … the high-level submission number will be the same, but the individual tracking numbers listed here should be specific to the MA in question. For more information see Technical Guidance Document. Please ensure that these grouping numbers are always mentioned in the case of additional information or corrigendum otherwise EDA might not be able to process your submission correctly." | "For example, see bullet points in the column on the left-hand side" | 17–18 |
| E8 | `submission-unit` | Element | `envelope` | Mandatory | Unique | "Provides administrative information associated with the submission unit." | N/A | 18 |
| A5 | `type` | Attribute | `submission-unit` | Mandatory | Unique | "Submission unit type describes the content at a lower level (a “sub-activity”) which is submitted in relation to a defined regulatory activity. The list is available in the Submission Unit CV." | `response` | 18 |
| E9 | `applicant` | Element | `envelope` | Mandatory | Unique | "The name of the company submitting the eCTD." | `Pharma Company Ltd.` | 18 |
| E10 | `agency` | Element | `envelope` | Mandatory | Unique | "Parent element for the identification of the receiving agency." | N/A | 18 |
| A6 | `code` | Attribute | `agency` | Mandatory | Unique | "The identification of the receiving agency EDA (see Appendix 2.4)." | `EG-EDA` | 18 |
| E11 | `invented-name` | Element | `envelope` | Mandatory | **Repeatable** | "The name of the medicinal product (should not be repeated for EDA submission.)" | `WonderPill` | 18 |
| E12 | `registration` | Element | `envelope` | Mandatory | Unique | "Provides information associated with the registration of the product." | N/A | 18 |
| A7 | `type` | Attribute | `registration` | Mandatory | Unique | "Registration type of the product, e.g. Imported Finished or Imported Bulk. The list is available in the Registration Type CV." | `local` | 18 |
| E13 | `marketing` | Element | `envelope` | Mandatory | Unique | "Provides information associated with the marketing of the product in Egypt." | N/A | 19 |
| A8 | `type` | Attribute | `marketing` | Mandatory | Unique | "Marketing type of the product, e.g. Local or Tender and Export. The list is available in Marketing Type CV." | `local` | 19 |
| E14 | `inn` | Element | `envelope` | Optional | Repeatable | "International Non-proprietary Name, used to identify pharmaceutical substances or active pharmaceutical ingredients. Each INN is a unique name that is globally recognized and is public property. A non-proprietary name is also known as a generic name." | `Pioglitazone hydrochloride` | 19 |
| E15 | `sequence` | Element | `envelope` | Mandatory | Unique | "This is the sequence number of the submission – this should start at 0000 for the initial submission, and then increase incrementally with each subsequent submission related to the same product e.g. 0000, 0001, 0002, 0003 etc." | `0000` | 19 |
| E16 | `related-sequence` | Element | `envelope` | Mandatory | Repeatable | "This is the sequence number of previous submission(s) to which this submission relates e.g. the responses to questions to a particular variation. In the case of submission unit types ‘initial’ and ‘reformat’, the related sequence is identical to the sequence number." | `0001` "See appendix 1.1." | 19 |
| E17 | `submission-description` | Element | `envelope` | Mandatory | Unique | "This element is used to provide a free text description of the submission. The list below provides additional examples for such a field: ▪ For an MAA: Original MAA Application for <Product X> ▪ For a variation: Please quote the scope of variation from the Application Form ▪ For responses: Response to validation questions / Response to Questions ▪ For supplementary information: Providing supplementary information regarding xx" | `Response to LOQ` | 19–20 |

Not in the EG table at all: any `procedure` element / `procedure/@type` (EU has one), any `dtd-version`, any
`xml:lang` on the root.

### 4.3 Controlled vocabularies — every value the draft actually prints

| Field | Values printed in SPEC (verbatim) | Where | Notes |
|---|---|---|---|
| `envelope/@country` | `eg` ("The country is EGYPT (EG)") | p. 14; App. 2.1 p. 78 (`eg` — Egypt — "ISO-3166-1-alpha-2 code") | only one value exists, yet `envelope` is "Repeatable" |
| `submission/@type` | `maa` (p. 14, 22, 24) · `Var PAC-II` (p. 23–25, examples) · "Type VAR PAC-II" (p. 14 N.B., p. 23) · `none` (p. 25 Table 3) · `Withdrawal` (p. 26 Table 5; body text l. 293 ‘withdrawal’) | p. 14–26 | **GAP**: the "Submission Type CV" is not in the draft. The worked examples print the human title `Var PAC-II`, not a token. TG Annex 6 has the token list (see §9.3). |
| `submission/@mode` | `single` · `grouping` · `parallel-single` · `parallel-grouping` (p. 8 l. 79); table p. 15 prints `single`, `grouping`, `parallel-single`, "parallel  grouping" (no hyphen) | p. 8, 15 | definitions below |
| `submission/number` format | `B-GV-xxxx`, `B-PGV-xxxx`, `I-GV-xxxx`; "the ‘xxxx’ used in the submission number is a sequential number" | p. 16 | prefix meanings **not defined** (B/I/GV/PGV) |
| `procedure-tracking/number` format | `P-VAR-PAC-N-0002`, `I-IPV-PU-0001` | p. 17 | prefix meanings **not defined**; at least one EDA-issued number, optional applicant internal number |
| `submission-unit/@type` | `initial`, `response`, `additional-info` (p. 22 "additional-info"; p. 21 l. 264), `validation-response` (p. 24), `reformat` (p. 25), `responses` (p. 25 Table 4 — **typo**), "‘Response’" (p. 25 l. 285, capitalised) | p. 18–26 | **GAP**: "Submission Unit CV" not in the draft; `corrigendum` only appears as a word in the tracking-number text (p. 18); `re-examination`, `closing`, `consolidating` never appear |
| `agency/@code` | `EG-EDA` (Country Egypt — Agency Name "Egyptian Drug Authority") | p. 18; App. 2.4 p. 78 l. 336–337 | "The Agency Code is the value to use from within the EG Module 1 XML file." |
| `registration/@type` | example `local`; description examples "Imported Finished", "Imported Bulk" | p. 18 | **GAP**: "Registration Type CV" not in the draft; token spelling of the two description examples unknown |
| `marketing/@type` | example `local`; description examples "Local", "Tender and Export" | p. 19 | **GAP**: "Marketing Type CV" not in the draft; whether "Tender and Export" is one value or two is unknown |
| `pi-doc/@xml:lang` | `ar` Arabic, `en` English | App. 2.2 p. 78 | |
| `pi-doc/@type` | App. 2.3 table: `spc` Summary of Product Characteristics, `pl` Package Leaflet; footnote: "‘interpack’ should be used" when outer and immediate labelling are one file; example in App. 1.2: `combined`; file-name examples p. 11: `outer`, `combined` | p. 27, 78, 11 | **AMBIGUOUS**: allowable list = 2 values in the table, 5 tokens used across the draft |
| `pi-doc/@country` | `eg` | p. 27; App. 2.1 | |

**Submission mode definitions (p. 15, verbatim):**

| Value | Definition |
|---|---|
| `single` | "a single regulatory activity (e.g. a Type II variation)" |
| `grouping` | "= Several variations grouped to a single submission for a single product for Human Pharmaceuticals = For Biological and Innovative Products: - Several variations grouped to a single submission for a single product Or - Several variations grouped into a single submission for multiple products Or - Single variation submitted for multiple products" |
| `parallel-single` | "Parallel Assessment. Imported Products, evaluation of the procedure at the same time with the authority of the country of origin." |
| `parallel-grouping` (printed "parallel  grouping") | "Parallel Assessment. Imported Products, evaluation of the procedure at the same time with the authority of the country of origin." (identical to parallel-single) |

### 4.4 Sequence / related-sequence / submission-unit rules (p. 21–26)

| Rule | Verbatim / condensed | Cite |
|---|---|---|
| Purpose | "The related-sequence element is used to identify sequences belonging to the same ‘regulatory activity’. … The Submission Unit type element describes the stage within the regulatory activity, such as initial, response." | p. 21 l. 246–249 |
| New activity / reformat | "For new regulatory activities (“initial”) and for “reformat”, the related-sequence attribute should always be equal to the sequence number." | l. 250–251 |
| Continuation | "When submitting lifecycle sequences within an existing activity, the related-sequence attribute should be populated with the sequence number the regulatory activity has been started with." | l. 251–252 |
| Invariant (testable) | "when submission unit = initial or submission_unit = reformat, then the related sequence number is always = sequence number and vice versa, when the submission unit ≠ initial or the submission_unit ≠ reformat, the related sequence is always < sequence number." | l. 253–255 |
| Several related sequences | "usually just one related sequence, but … e.g. there are two post authorisation measures (sequence 0050 and sequence 0060) and a single response (sequence 0070) is produced that relates to both". | l. 258–260 |
| Mixed categories | "If more than one different category of activities (submission types) is referred to (as related sequence), then the “highest category” should be used in the envelope attributes. If any of the related variations were grouped, then ‘grouping’ should be used." | l. 260–262 |
| Units per type | "For any of the submission types (regulatory activities), an initial and any of the additional submission unit types can be used, e.g. ‘response’ … The post authorisation measure may have an initial and additional-info submission unit type." | l. 262–264 |
| Multi-MA variation | "Special attention should be paid to the correct use of the related-sequence element when the regulatory activity is a variation that covers more than one Marketing Authorisation. An example is given in the Appendix." **GAP:** no such example exists. | l. 266–267 |
| Initial unit | "For the submission unit type that initiates a regulatory activity the term ‘initial’ should always be used." Related sequence "especially meaningful in case of parallel variations." | p. 24 l. 269–273 |
| Reformat | "The submission unit type ‘reformat’ should be used for each baseline submission. Related sequence should be equal to the sequence number’ Baseline for all modules need to be submitted in one submission." | p. 25 l. 279–280 |
| Withdrawal/rejection of one activity | "the sequence needs to re-establish the previous status of the dossier. Submitted documents justifying the regulatory activity … need to be deleted or replaced by the previous version … The submission unit type of that sequence is ‘Response’. The submission description should include some text to identify the sequence as a consolidation sequence after rejection/withdrawal". | p. 25 l. 283–287 |
| Withdrawal of whole MA | "the submission type is ‘withdrawal’, the submission unit type ‘initial’ and the related sequence will be identical with the sequence number." | p. 26 l. 291–294 |
| UUID correction re-send | new UUID, **same sequence number**, comment in the application form "that the eCTD is a technically corrected sequence (corrected UUID) that is re-sent". | p. 12 l. 214–218 |

**Worked examples (verbatim values):**

| Table (page) | Seq | Description | Submission type | Related | Unit |
|---|---|---|---|---|---|
| unnamed (p. 22–23) | 0000 | Original MAA application | maa | 0000 | initial |
| | 0001 | Responses to questions on the original application | maa | 0000 | response |
| | 0002 | Further Responses to further questions on the original application | maa | 0000 | response |
| | 0003 | Letter of Undertaking (submission unit type: additional info) | maa | 0000 | additional-info |
| | 0004 | Type VAR PAC-II variation for ‘Treatment of Pain’ indication | Var PAC-II | 0004 | initial |
| | 0005 | Type VAR PAC-II variation for a change in manufacturing site (Westferry) | Var PAC-II | 0005 | initial |
| | 0006 | Responses to questions on Type II variation for ‘Treatment of Pain’ indication | Var PAC-II | 0004 | response |
| | 0007 | Responses to questions on Type II variation for change in manufacturing site (Westferry) | Var PAC-II | 0005 | response |
| | 0008 | Updated, agreed, product information taking into account new indication (Treatment of Pain’) | Var PAC-II | 0004 | response |
| Table 1 MAA (p. 24) | 0000–0004 | MAA / Validation update / Responses / Responses / Agreed English product information | maa | 0000 | initial / validation-response / response / response / response |
| Table 2 Variation (p. 24) | 0008–0010 | Variation for new indication of COPD / Validation update / Responses to questions | Var PAC-II | 0008 | initial / validation-response / response |
| Table 3 reformat (p. 25) | 0000 | Baseline of M1 – M5 | none | 0000 | reformat |
| | 0001 | Variation for a new indication of COPD | Var PAC-II | 0001 | initial |
| | 0002 | Responses to questions | Var PAC-II | 0001 | response |
| Table 4 withdrawal of one activity (p. 25) | 0006 | Withdrawal of variation to change manufacturing site ‘Westferry’ | Var PAC-II | 0005 | responses (sic) |
| | 0007 | Variation for new indication of back pain | Var PAC-II | 0007 | initial |
| | 0008 | Response to clinical questions | Var PAC-II | 0007 | response |
| Table 5 withdrawal of MA (p. 26) | 0016 | Withdrawal of the MA application (entirely) | Withdrawal | 0016 | initial |

### 4.5 UUID (`identifier`) rules (SPEC p. 11 l. 185–190; p. 12 l. 191–218)

| Rule | Verbatim / condensed | Line |
|---|---|---|
| Mandatory | "all eCTD sequences built in accordance with this specification must contain a UUID, linking the sequence to the eCTD application to which it belongs." | 189–190 |
| Use | archiving and "automated sorting of incoming eCTD submissions to the correct eCTD lifecycle" | 191–193 |
| Uniqueness, generation | "unique for each eCTD lifecycle and should therefore always be machine generated, i.e. be created by the eCTD building tool or, if not possible, by using an online UUID generator." | 193–195 |
| Case | "Creating the UUID with uppercases or lowercases is not restricted but needs to be kept as chosen during the full lifecycle." | 195–196 |
| Standard and form | "based on ISO/IEC 11578:1996 and ITU-T Rec X.667 \| ISO/IEC 9834-8:2005. It is a hexadecimal number in the form of xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx, showing 32 digits and 4 hyphens. The ‘x’ will be replaced by a number or a letter." | 197–200 |
| Version | "It is recommended to use randomly generated sections (version 4 of UUID types). Such UUID would for example look like 4cc86cf0-9088-4a3c-9526-fa6320f4c469." | 200–201 |
| When created | "generated for the first time when creating the first sequence following the implementation of the UUID requirement in the specification and will be provided in the eCTD envelope. All subsequent sequences for that same eCTD lifecycle should contain the same UUID." | 202–207 |
| Duplicate across lifecycles | EDA "can also check that the UUID is not the same as in another already existing eCTD lifecycle"; "even if this is not part of the eCTD technical validation criteria, in such cases, the EDA will contact the applicant/MAH and request an updated eCTD sequence with a new UUID." | 208–215 |
| Correction | "The updated eCTD sequence should be submitted with a new UUID to EDA using the same sequence number. A comment should be included in the application form that the eCTD is a technically corrected sequence (corrected UUID) that is re-sent." | 216–218 |

Implementable check (derived from l. 197–200, case rule l. 195–196): `^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`,
same string (same case) in every sequence of the lifecycle. Version 4 is only *recommended*, so a validator should not
fail other versions.

---

## 5. `m1-eg` content (SPEC p. 8 l. 89–95; p. 9 l. 96–132; p. 10 l. 133–147; App. 1.2 p. 27; App. 2)

### 5.1 Body rules
* "The “m1-eg” element of the EG regional DTD is based on the same conceptual approach as the common part of the ICH eCTD
  DTD. It provides an XML catalogue with meta-data at the leaf level including pointers to the location of files in a
  directory structure. As for the ICH eCTD DTD, the “m1-eg” element maps to the directory structure." (p. 8 l. 90–93)
* App. 1 intro: "The EG Module 1 XML Submission contains an element for each document in Module 1 as per Appendix 2" (p. 14 l. 239).
* Directory structure "strongly recommended": same high-level structure for all submission types; "Country directories are named
  according to Appendix 2.1"; "Language directories are named according to Appendix 2.2"; "In Module 1.3.1, every document should
  be placed in an appropriately named language subdirectory, which has the appropriate language identifier." (p. 9 l. 97–105)

### 5.2 Element list (from App. 2; full row detail in §6)
Section-level elements (parents) and their children, as listed in App. 2. Whether each is optional, and the order inside
`m1-eg`, is **not stated** (no DTD). Every element that has no child element in App. 2 is a leaf container.

| CTD no. | Element | Children in App. 2 | Leaf-level attributes stated |
|---|---|---|---|
| — | `m1-eg` | m1-0-cover, m1-2-form, m1-3-pi, m1-4-expert, m1-5-specific, m1-6-environrisk, m1-7-orphan, m1-8-pharmacovigilance, m1-9-clinical-trials, m1-10-paediatrics, m1-responses, m1-additional-data | — |
| 1.0 | `m1-0-cover` | (leaves: cover, tracking) | none |
| 1.2 | `m1-2-form` | m1-2-1-af … m1-2-16-relinsp (16 sub-sections) | none |
| 1.2.1 | `m1-2-1-af` | leaves | none |
| 1.2.2 | `m1-2-2-legal` | m1-2-2-1 … m1-2-2-21 (21) | none |
| 1.2.3 | `m1-2-3-edaapp` | m1-2-3-1 … m1-2-3-20 (20) | none |
| 1.2.4 | `m1-2-4-declar` | m1-2-4-1 … m1-2-4-22 (22) | none |
| 1.2.5 | `m1-2-5-refprod` | 4 | none |
| 1.2.6 | `m1-2-6-importdoc` | 2 | none |
| 1.2.7 | `m1-2-7-reliance` | 6 | none |
| 1.2.8 | `m1-2-8-composit` | 7 | none |
| 1.2.9 | `m1-2-9-coa` | leaves | none |
| 1.2.10 | `m1-2-10-postappch` | 4 | none |
| 1.2.11 | `m1-2-11-pop` | leaves | none |
| 1.2.12 | `m1-2-12-analysreq` | 2 | none |
| 1.2.13 | `m1-2-13-plasma` | 3 | none |
| 1.2.14 | `m1-2-14-scienadv` | leaves | none |
| 1.2.15 | `m1-2-15-relpv` | 5 | none |
| 1.2.16 | `m1-2-16-relinsp` | 7 | none |
| 1.3 | `m1-3-pi` | m1-3-1-spc-label-pl, m1-3-2-mockup, m1-3-3-specimen, m1-3-4-consultation, m1-3-5-approved, m1-3-6-braille | — |
| 1.3.1 | `m1-3-1-spc-label-pl` | `pi-doc` (repeatable) → leaves | `pi-doc` `xml:lang`, `type`, `country` |
| 1.3.2–1.3.6 | `m1-3-2-mockup` … `m1-3-6-braille` | leaves | **none stated** (no country folder either) |
| 1.4 | `m1-4-expert` | m1-4-1-quality, m1-4-2-non-clinical, m1-4-3-clinical | — |
| 1.5 | `m1-5-specific` | m1-5-1-bibliographic, m1-5-2-generic-hybrid-bio-similar, m1-5-3-data-market-exclusivity, m1-5-4-exceptional-circumstances, m1-5-5-conditional-ma | — |
| 1.6 | `m1-6-environrisk` | m1-6-1-non-gmo, m1-6-2-gmo — "Only one of the 2 folders 1.6.1 or 1.6.2 can have content when sending a sequence." (rows 159, 161) | — |
| 1.7 | `m1-7-orphan` | m1-7-1-similarity, m1-7-2-market-exclusivity | — |
| 1.8 | `m1-8-pharmacovigilance` | m1-8-1-pharmacovigilance-system, m1-8-2-risk-management-system | — |
| 1.9 | `m1-9-clinical-trials` | leaves | — |
| 1.10 | `m1-10-paediatrics` | leaves | — |
| (none) | `m1-responses` | leaves / node-extensions | — |
| (none) | `m1-additional-data` | leaves | — |

There is **no section 1.1** (no element, no folder) in the draft.

### 5.3 `pi-doc` (App. 1.2, SPEC p. 27 l. 301–304)
"The “m1-3-1-spc-label-pl”. can have multiple child “pi-doc” elements that allow identification of product information
language, document type and applicable country as described below."

| Element | Attribute | Description (verbatim) | Example | Constraint | Occurrence |
|---|---|---|---|---|---|
| `pi-doc` | — | "Parent element for identification of the type, language and country of one or more product information documents." | N/A | Mandatory | Repeatable |
| | `xml:lang` | "The language that the product information is written in (see Appendix 2.2 for allowable values)." | `ar` | Mandatory | Unique |
| | `type` | "The type of product information document (see Appendix 2.3 for allowable values)." | `combined` | Mandatory | Unique |
| | `country` | "The receiving country for the product information (see Appendix 2.1 for full list of allowable values)" | `eg` | Mandatory | Unique |

Folder/file rule (App. 2 rows 129–130, p. 58): `m1/eg/13-pi/131-spclabelpl/LL/PIDOC-VAR.EXT`; "Always use a language
directory at this level during the lifecycle of the submission (Arabic or English)."; "Summary of Product Characteristics
"spc" & Package Leaflet "pl" are required by EDA"; example `m1/eg/13-pi/131-spclabelpl/ar/spc-tablet10mgar.pdf`.
Note: unlike `LL`, there is **no** `CC` folder level in this path although `pi-doc/@country` is mandatory.

### 5.4 Node extensions (SPEC p. 9 l. 106–132; p. 10 l. 133–147)

| # | Rule (verbatim or near-verbatim) | Line |
|---|---|---|
| N1 | Purpose: "extra organisational information"; "visualised as an extra heading in the CTD structure and should be displayed as such when the XML backbone is viewed." | 107–109 |
| N2 | "the use of node extensions should be limited to those areas where it is critical." | 110–113 |
| N3 | "Node extensions must not be used where ICH-specified sub-headings already exist (e.g. indication, manufacturer, drug substance and drug product are all-ICH specified node extensions)." | 115–117 |
| N4 | "Node extensions must only be used at the lowest level of the eCTD structure (e.g. a node extension can be used at the level 5.3.5.1 but must not be used at the level 5.3)." | 118–119 |
| N5 | "mainly to be used to group together documents made up of multiple leaf elements (e.g. a clinical study … grouped together under a node extension with the Study Identifier as its Title attribute)." | 120–123 |
| N6 | "Node extensions must be maintained over the entire life of the eCTD lifecycle (… any files submitted in a later sequence must also be placed under a node extension, even if only one file is submitted)." | 124–127 |
| N7 | "Node extensions may be nested … However, … the first node extension must be at the lowest level in the eCTD structure … Further node extensions may be added as children of the Study Identifier node, separating CRFs from individual patient listings." | 128–132 |
| N8 | "The content associated with a node extension can be placed in a separate sub folder in the submission; this is recommended for studies in Module 5 where study reports are provided as multiple files. However, there is no specific requirement for an additional subfolder in other modules." | 133–136 |
| N9 | Responses: "the responses relating to a particular regulatory activity should be grouped under a node-extension in the eg-regional.xml file. The title of the node extension should identify the regulatory activity (e.g. Responses to Questions for the Initial Application, Responses to Questions for Variation 028, etc.). It is recommended that the applicant provides a full copy of the list of questions received from the authority as the first leaf in this section." | 137–142 |
| N10 | Response file names: `responses-<regulatory activity type identifier>-<response number>-<content identifier>.pdf`, "using the -var component of the filename to define the content." | 143–147 |

---

## 6. Directory / file structure — Appendix 2 reproduced completely (SPEC p. 28–78)

### 6.1 Table conventions (p. 28 l. 305–312)
Columns defined by the draft: "Sequential number — Each item in the table has a unique sequentially assigned reference number.
These reference numbers can change with each version of this appendix." · Number = CTD section number · Title = CTD title ·
Element = "Element name in the EG Backbone" · File/Directory = "File/Directory name from m1/eg – should be relative path from
m1/eg/ e.g. 12-form/121-af/form-af.pdf. This is consistent with ICH standards. The file extension corresponds to the file type,
i.e. the “pdf” extension is only illustrative." · Comment.

| Code | Definition (verbatim) |
|---|---|
| CC | "Country Code, also referred to as the destination code as per Appendix 2.1" |
| LL | "Local Language code as per Appendix 2.2" |
| EXT | "File extension." |
| PIDOC | "Product Information Document identifier as per Appendix 2.3" |
| VAR | "Variable component of the filename." |
| DDDD | "A sequence number made of 4 digits (e.g. 0000)" |

"* = The names of the actual files and directories used should be presented in lower case in accordance with the eCTD
specification. The use of upper case for codes is for illustrative purposes only to show differentiation between the
variable parts and the fixed part of the name." (l. 310–312)

**Facts about the table (checked):** 185 rows; sequential numbers printed 1–183 with **144 and 145 each used twice**
(1.4.2/its file and 1.4.3/its file, p. 62–63); the definition says paths are "relative path from m1/eg/" but every row
actually prints the full `m1/eg/...` path (rows 182–183 print `util/...`, which is at sequence level). `CC` and `DDDD`
are defined but **never used** in any row (row 5 uses `/XXXX/`). Seven directory paths carry a trailing slash (rows 7,
111, 112, 113, 114, 115, 121) and the rest do not. Line-wrapped paths in the PDF (rows 150, 152, 166, 169, 171) are
re-joined here without the wrap space.

### 6.2 Appendix 2 — every row

| # (as printed) | Page | CTD no. | Title | Element | Directory | File (pattern) | Comment (verbatim) |
|---|---|---|---|---|---|---|---|
| 1 | 29 |  | EG Module 1 | `m1-eg` | `m1/eg` |  | Top level directory for the EG Module 1 as per ICH eCTD Specification. |
| 2 | 29 |  |  |  |  | `m1/eg/eg-regional.xml` | The EG Regional XML instance including envelope information. Note that the operation attribute for the eg.regional.xml should always be set to ‘new’. |
| 3 | 29 | 1.0 | Cover Letter | `m1-0-cover` | `m1/eg/10-cover` |  |  |
| 4 | 29 |  |  |  |  | `m1/eg/10-cover/cover-VAR.EXT` | Filename for the Cover Letter composed of a fixed component “cover” and an optional variable component |
| 5 | 30 |  |  |  |  | `m1/eg/10-cover/tracking-VAR.EXT` | A tracking table should always be included in addition to the cover letter for submissions within all procedures The file should be named tracking-var.pdf (‘var’ for the variable part) and be placed in /XXXX/m1/eg/10-cover |
| 6 | 30 | 1.2 | Application Forms | `m1-2-form` | `m1/eg/12-form` |  | General placeholder for forms and annexes |
| 7 | 30 | 1.2.1 | Application Form | `m1-2-1-af` | `m1/eg/12-form/121-af/` |  |  |
| 8 | 30 |  |  |  |  | `m1/eg/12-form/121-af/form-af-VAR.EXT` | Filename for the Application Form composed of a fixed component ‘form-af’ and an optional variable component to be used if required (e.g. form-af-tablet.pdf) |
| 9 | 31 | 1.2.2 | Legal Documents | `m1-2-2-legal` | `m1/eg/12-form/122-legal` |  |  |
| 10 | 31 | 1.2.2.1 | Letter of Attorney for Company Representative | `m1-2-2-1-loattor` | `m1/eg/12-form/122-legal/1221-loattor` |  |  |
| 11 | 31 | 1.2.2.2 | Manufacturing License and IDA License | `m1-2-2-2-manlic` | `m1/eg/12-form/122-legal/1222-manlic` |  |  |
| 12 | 31 | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | `m1-2-2-3-gmpcert` | `m1/eg/12-form/122-legal/1223-gmpcert` |  |  |
| 13 | 31 | 1.2.2.4 | The Register of Trade | `m1-2-2-4-trade` | `m1/eg/12-form/122-legal/1224-trade` |  |  |
| 14 | 32 | 1.2.2.5 | Toll Manufacturer License | `m1-2-2-5-toll` | `m1/eg/12-form/122-legal/1225-toll` |  |  |
| 15 | 32 | 1.2.2.6 | Scientific Office License | `m1-2-2-6-sol` | `m1/eg/12-form/122-legal/1226-sol` |  |  |
| 16 | 32 | 1.2.2.7 | Importers Register License | `m1-2-2-7-import` | `m1/eg/12-form/122-legal/1227-import` |  |  |
| 17 | 32 | 1.2.2.8 | Store License | `m1-2-2-8-storelic` | `m1/eg/12-form/122-legal/1228-storelic` |  |  |
| 18 | 33 | 1.2.2.9 | Authorisation Letter / Agency Agreement | `m1-2-2-9-authlet` | `m1/eg/12-form/122-legal/1229-authlet` |  |  |
| 19 | 33 | 1.2.2.10 | Manufacturing Agreement | `m1-2-2-10-managre` | `m1/eg/12-form/122-legal/12210-managre` |  |  |
| 20 | 33 | 1.2.2.11 | Packaging Agreement | `m1-2-2-11-pacagre` | `m1/eg/12-form/122-legal/12211-pacagre` |  |  |
| 21 | 33 | 1.2.2.12 | Storage Agreement | `m1-2-2-12-storeagre` | `m1/eg/12-form/122-legal/12212-storeagre` |  |  |
| 22 | 33 | 1.2.2.13 | Other Agreements | `m1-2-2-13-othagre` | `m1/eg/12-form/122-legal/12213-othagre` |  |  |
| 23 | 34 | 1.2.2.14 | Termination / Waiver | `m1-2-2-14-term` | `m1/eg/12-form/122-legal/12214-term` |  |  |
| 24 | 34 | 1.2.2.15 | Tax Card | `m1-2-2-15-tax` | `m1/eg/12-form/122-legal/12215-tax` |  |  |
| 25 | 34 | 1.2.2.16 | List of Distributors | `m1-2-2-16-distribut` | `m1/eg/12-form/122-legal/12216-distribut` |  |  |
| 26 | 34 | 1.2.2.17 | IP Protection Law No. 82 of 2002 Commitment | `m1-2-2-17-ipp` | `m1/eg/12-form/122-legal/12217-ipp` |  |  |
| 27 | 35 | 1.2.2.18 | NEW local MA legal Agreement | `m1-2-2-18-newlegag` | `m1/eg/12-form/122-legal/12218-newlegag` |  |  |
| 28 | 35 | 1.2.2.19 | Letter of Authorisation for a new Applicant in Egypt | `m1-2-2-19-loauth` | `m1/eg/12-form/122-legal/12219-loauth` |  |  |
| 29 | 35 | 1.2.2.20 | PV Agreement between the MAH & the Service Provider | `m1-2-2-20-pvagre` | `m1/eg/12-form/122-legal/12220-pvagre` |  |  |
| 30 | 35 | 1.2.2.21 | GMP Certificate | `m1-2-2-21-gmpcert2` | `m1/eg/12-form/122-legal/12221-gmpcert2` |  |  |
| 31 | 35 | 1.2.3 | EDA Approvals | `m1-2-3-edaapp` | `m1/eg/12-form/123-edaapp` |  |  |
| 32 | 36 | 1.2.3.1 | Registration Request Approval | `m1-2-3-1-regreq` | `m1/eg/12-form/123-edaapp/1231-regreq` |  |  |
| 33 | 36 | 1.2.3.2 | Inquiry Approval | `m1-2-3-2-inqapp` | `m1/eg/12-form/123-edaapp/1232-inqapp` |  |  |
| 34 | 36 | 1.2.3.3 | Name Approval | `m1-2-3-3-nameapp` | `m1/eg/12-form/123-edaapp/1233-nameapp` |  |  |
| 35 | 36 | 1.2.3.4 | Registration License | `m1-2-3-4-reglic` | `m1/eg/12-form/123-edaapp/1234-reglic` |  |  |
| 36 | 37 | 1.2.3.5 | Preliminary Approval | `m1-2-3-5-prelimapp` | `m1/eg/12-form/123-edaapp/1235-prelimapp` |  |  |
| 37 | 37 | 1.2.3.6 | Non-Reference Approval | `m1-2-3-6-nonrefapp` | `m1/eg/12-form/123-edaapp/1236-nonrefapp` |  |  |
| 38 | 37 | 1.2.3.7 | Exemption Approval | `m1-2-3-7-exemptapp` | `m1/eg/12-form/123-edaapp/1237-exemptapp` |  |  |
| 39 | 37 | 1.2.3.8 | Pricing Certificate | `m1-2-3-8-price` | `m1/eg/12-form/123-edaapp/1238-price` |  |  |
| 40 | 37 | 1.2.3.9 | Pharmacovigilance Approval | `m1-2-3-9-pvapp` | `m1/eg/12-form/123-edaapp/1239-pvapp` |  |  |
| 41 | 38 | 1.2.3.10 | Inspection Report | `m1-2-3-10-insprep` | `m1/eg/12-form/123-edaapp/12310-insprep` |  |  |
| 42 | 38 | 1.2.3.11 | Importation Approval for each API | `m1-2-3-11-importapp` | `m1/eg/12-form/123-edaapp/12311-importapp` |  |  |
| 43 | 38 | 1.2.3.12 | CADC Report | `m1-2-3-12-cadcrep` | `m1/eg/12-form/123-edaapp/12312-cadcrep` |  |  |
| 44 | 38 | 1.2.3.13 | Stability Study Approval | `m1-2-3-13-stabstud` | `m1/eg/12-form/123-edaapp/12313-stabstud` |  |  |
| 45 | 39 | 1.2.3.14 | Stability Protocol Approval | `m1-2-3-14-stabprot` | `m1/eg/12-form/123-edaapp/12314-stabprot` |  |  |
| 46 | 39 | 1.2.3.15 | Module 3 Approval | `m1-2-3-15-m3app` | `m1/eg/12-form/123-edaapp/12315-m3app` |  |  |
| 47 | 39 | 1.2.3.16 | Module 5 Approval | `m1-2-3-16-m5app` | `m1/eg/12-form/123-edaapp/12316-m5app` |  |  |
| 48 | 39 | 1.2.3.17 | Pre-approved letters from EDA concerning the product | `m1-2-3-17-preapplet` | `m1/eg/12-form/123-edaapp/12317-preapplet` |  |  |
| 49 | 39 | 1.2.3.18 | Variation Approvals | `m1-2-3-18-varapp` | `m1/eg/12-form/123-edaapp/12318-varapp` |  |  |
| 50 | 40 | 1.2.3.19 | Innovative Products Scientific Committee Approval | `m1-2-3-19-ipsca` | `m1/eg/12-form/123-edaapp/12319-ipsca` |  |  |
| 51 | 40 | 1.2.3.20 | Registration License for the Solvent | `m1-2-3-20-reglicsolv` | `m1/eg/12-form/123-edaapp/12320-reglicsolv` |  |  |
| 52 | 40 | 1.2.4 | Declarations | `m1-2-4-declar` | `m1/eg/12-form/124-declar` |  |  |
| 53 | 41 | 1.2.4.1 | Declaration Letter stating the list of Registered & Under-Registration Products owned by the Toll Company | `m1-2-4-1-regprod` | `m1/eg/12-form/124-declar/1241-regprod` |  |  |
| 54 | 41 | 1.2.4.2 | Declaration Letter from the License Holder specifying the API Manufacturers | `m1-2-4-2-apiman` | `m1/eg/12-form/124-declar/1242-apiman` |  |  |
| 55 | 41 | 1.2.4.3 | Declaration letter from the license holder specifying approved pack in Egypt | `m1-2-4-3-liceholdpac` | `m1/eg/12-form/124-declar/1243-liceholdpac` |  |  |
| 56 | 41 | 1.2.4.4 | Declaration Letter from the License Holder stating the Form of Bulk (Strips, Capsules, etc.) | `m1-2-4-4-liceholdbulk` | `m1/eg/12-form/124-declar/1244-liceholdbulk` |  |  |
| 57 | 42 | 1.2.4.5 | Declaration Letter from the Manufacturer of the Active Substance to inform the Applicant in case of Modification of the manufacturing Process or Specifications | `m1-2-4-5-apimanappl` | `m1/eg/12-form/124-declar/1245-apimanappl` |  |  |
| 58 | 42 | 1.2.4.6 | Declaration Letter from API Supplier | `m1-2-4-6-apisupp` | `m1/eg/12-form/124-declar/1246-apisupp` |  |  |
| 59 | 42 | 1.2.4.7 | Declaration Letter for Site Addition | `m1-2-4-7-siteadd` | `m1/eg/12-form/124-declar/1247-siteadd` |  |  |
| 60 | 42 | 1.2.4.8 | Declaration Letter Form LH stating all Variations & Justification for the Change | `m1-2-4-8-allvar` | `m1/eg/12-form/124-declar/1248-allvar` |  |  |
| 61 | 43 | 1.2.4.9 | Other declarations requested by Egyptian Drug Authority | `m1-2-4-9-decother` | `m1/eg/12-form/124-declar/1249-decother` |  |  |
| 62 | 43 | 1.2.4.10 | List of the Countries where the Product is registered & marketed | `m1-2-4-10-countries` | `m1/eg/12-form/124-declar/12410-countries` |  |  |
| 63 | 43 | 1.2.4.11 | Ph. Eur. Certificate(s) of Suitability for TSE | `m1-2-4-11-tse` | `m1/eg/12-form/124-declar/12411-tse` |  |  |
| 64 | 43 | 1.2.4.12 | TSE/BSE Supplier Safety Declaration (if CEP not available) | `m1-2-4-12-bsesafdec` | `m1/eg/12-form/124-declar/12412-bsesafdec` |  |  |
| 65 | 43 | 1.2.4.13 | Raw Materials Storage Responsibility Declaration (for local Products) | `m1-2-4-13-rawmat` | `m1/eg/12-form/124-declar/12413-rawmat` |  |  |
| 66 | 44 | 1.2.4.14 | Excipient/s Supplier Name & Origin | `m1-2-4-14-exipsup` | `m1/eg/12-form/124-declar/12414-exipsup` |  |  |
| 67 | 44 | 1.2.4.15 | Trade Name of the Albumin used as Stabilizer | `m1-2-4-15-albtraden` | `m1/eg/12-form/124-declar/12415-albtraden` |  |  |
| 68 | 44 | 1.2.4.16 | Albumin as Stabilizer Batch Release Certificate | `m1-2-4-16-albstabil` | `m1/eg/12-form/124-declar/12416-albstabil` |  |  |
| 69 | 44 | 1.2.4.17 | Plasma Derivative Supplier Safety and Efficacy Commitment | `m1-2-4-17-plasdersub` | `m1/eg/12-form/124-declar/12417-plasdersub` |  |  |
| 70 | 45 | 1.2.4.18 | No Change in physical Address and Product related Processes Declaration | `m1-2-4-18-nochaadd` | `m1/eg/12-form/124-declar/12418-nochaadd` |  |  |
| 71 | 45 | 1.2.4.19 | Pack Type Declaration | `m1-2-4-19-pactype` | `m1/eg/12-form/124-declar/12419-pactype` |  |  |
| 72 | 45 | 1.2.4.20 | Insert Declaration Letter | `m1-2-4-20-insdeclet` | `m1/eg/12-form/124-declar/12420-insdeclet` |  |  |
| 73 | 45 | 1.2.4.21 | Site Master File Declaration | `m1-2-4-21-sitemfdec` | `m1/eg/12-form/124-declar/12421-sitemfdec` |  |  |
| 74 | 45 | 1.2.4.22 | Storage Temperature at 25 °C Declaration | `m1-2-4-22-storetemp` | `m1/eg/12-form/124-declar/12422-storetemp` |  |  |
| 75 | 46 | 1.2.5 | Reference Product Document / Compendial | `m1-2-5-refprod` | `m1/eg/12-form/125-refprod` |  |  |
| 76 | 46 | 1.2.5.1 | The Reference Product Documents | `m1-2-5-1-refproddoc` | `m1/eg/12-form/125-refprod/1251-refproddoc` |  |  |
| 77 | 46 | 1.2.5.2 | Scientific Reference (Trials & Literature) | `m1-2-5-2-sciref` | `m1/eg/12-form/125-refprod/1252-sciref` |  |  |
| 78 | 46 | 1.2.5.3 | Reference for the trade name change | `m1-2-5-3-reftradn` | `m1/eg/12-form/125-refprod/1253-reftradn` |  |  |
| 79 | 47 | 1.2.5.4 | The latest recent Pharmacopeia | `m1-2-5-4-recph` | `m1/eg/12-form/125-refprod/1254-recph` |  |  |
| 80 | 47 | 1.2.6 | Imported Products Documents | `m1-2-6-importdoc` | `m1/eg/12-form/126-importdoc` |  |  |
| 81 | 47 | 1.2.6.1 | Certificate of Pharmaceutical Product (CPP) | `m1-2-6-1-cpp` | `m1/eg/12-form/126-importdoc/1261-cpp` |  |  |
| 82 | 47 | 1.2.6.2 | List of Affiliates / Subsidiaries | `m1-2-6-2-loaff` | `m1/eg/12-form/126-importdoc/1262-loaff` |  |  |
| 83 | 47 | 1.2.7 | Reliance Documents | `m1-2-7-reliance` | `m1/eg/12-form/127-reliance` |  |  |
| 84 | 48 | 1.2.7.1 | Sameness Letter | `m1-2-7-1-sameness` | `m1/eg/12-form/127-reliance/1271-sameness` |  |  |
| 85 | 48 | 1.2.7.2 | Unredacted Assessment Report | `m1-2-7-2-unredact` | `m1/eg/12-form/127-reliance/1272-unredact` |  |  |
| 86 | 48 | 1.2.7.3 | RRA Variation Application with Annexes | `m1-2-7-3-rravar` | `m1/eg/12-form/127-reliance/1273-rravar` |  |  |
| 87 | 48 | 1.2.7.4 | Correspondences between the Applicant and the Reference Agency | `m1-2-7-4-correspond` | `m1/eg/12-form/127-reliance/1274-correspond` |  |  |
| 88 | 49 | 1.2.7.5 | List of Changes after first MA issued from EMA or FDA | `m1-2-7-5-lofchange` | `m1/eg/12-form/127-reliance/1275-lofchange` |  |  |
| 89 | 49 | 1.2.7.6 | Rejection or Amendment Reporting Commitment | `m1-2-7-6-reject` | `m1/eg/12-form/127-reliance/1276-reject` |  |  |
| 90 | 49 | 1.2.8 | Composition Documents | `m1-2-8-composit` | `m1/eg/12-form/128-composit` |  |  |
| 91 | 49 | 1.2.8.1 | Composition Certificate | `m1-2-8-1-compositcert` | `m1/eg/12-form/128-composit/1281-compositcert` |  |  |
| 92 | 49 | 1.2.8.2 | Specifications | `m1-2-8-2-spec` | `m1/eg/12-form/128-composit/1282-spec` |  |  |
| 93 | 50 | 1.2.8.3 | Any Composition Calculations | `m1-2-8-3-compcalc` | `m1/eg/12-form/128-composit/1283-compcalc` |  |  |
| 94 | 50 | 1.2.8.4 | Pellets / Premix Composition and Certificates | `m1-2-8-4-pelletcomp` | `m1/eg/12-form/128-composit/1284-pelletcomp` |  |  |
| 95 | 50 | 1.2.8.5 | Opadry / Coating Premix Composition | `m1-2-8-5-opadry` | `m1/eg/12-form/128-composit/1285-opadry` |  |  |
| 96 | 50 | 1.2.8.6 | Capsule Shell Composition | `m1-2-8-6-capshell` | `m1/eg/12-form/128-composit/1286-capshell` |  |  |
| 97 | 51 | 1.2.8.7 | Synonyms Evidence | `m1-2-8-7-synonyms` | `m1/eg/12-form/128-composit/1287-synonyms` |  |  |
| 98 | 51 | 1.2.9 | Certificate of Analysis | `m1-2-9-coa` | `m1/eg/12-form/129-coa` |  |  |
| 99 | 51 | 1.2.10 | Post Approval Changes Requirements | `m1-2-10-postappch` | `m1/eg/12-form/1210-postappch` |  |  |
| 100 | 51 | 1.2.10.1 | PAC Approval from the COO (Imported Products) | `m1-2-10-1-pacapp` | `m1/eg/12-form/1210-postappch/12101-pacapp` |  |  |
| 101 | 51 | 1.2.10.2 | Summary of Change for Variation | `m1-2-10-2-sumcavar` | `m1/eg/12-form/1210-postappch/12102-sumcavar` |  |  |
| 102 | 52 | 1.2.10.3 | Justification of the proposed Post Approval Change | `m1-2-10-3-justpoc` | `m1/eg/12-form/1210-postappch/12103-justpoc` |  |  |
| 103 | 52 | 1.2.10.4 | Any additional Documents relevant to Variations | `m1-2-10-4-anydoc` | `m1/eg/12-form/1210-postappch/12104-anydoc` |  |  |
| 104 | 52 | 1.2.11 | Proof of Payment | `m1-2-11-pop` | `m1/eg/12-form/1211-pop` |  |  |
| 105 | 52 | 1.2.12 | Analysis Requirements Documentation (for Biological Products only) | `m1-2-12-analysreq` | `m1/eg/12-form/1212-analysreq` |  |  |
| 106 | 53 | 1.2.12.1 | Detailed Standard Operating Procedures (SOP) | `m1-2-12-1-sop` | `m1/eg/12-form/1212-analysreq/12121-sop` |  |  |
| 107 | 53 | 1.2.12.2 | Summary Protocol for Vaccines and Plasma derived Medicinal Products | `m1-2-12-2-sumvacc` | `m1/eg/12-form/1212-analysreq/12122-sumvacc` |  |  |
| 108 | 53 | 1.2.13 | For Plasma derived Medicinal Products | `m1-2-13-plasma` | `m1/eg/12-form/1213-plasma` |  |  |
| 109 | 53 | 1.2.13.1 | Plasma Master File | `m1-2-13-1-pmf` | `m1/eg/12-form/1213-plasma/12131-pmf` |  |  |
| 110 | 53 | 1.2.13.2 | Certificate of Plasma Batch Release from Health Authority | `m1-2-13-2-plasbatch` | `m1/eg/12-form/1213-plasma/12132-plasbatch` |  |  |
| 111 | 54 | 1.2.13.3 | PMF Approval from Country of Origin | `m1-2-13-3-pmfapp` | `m1/eg/12-form/1213-plasma/12133-pmfapp/` |  |  |
| 112 | 54 | 1.2.14 | Scientific Advice Report | `m1-2-14-scienadv` | `m1/eg/12-form/1214-scienadv/` |  |  |
| 113 | 54 | 1.2.15 | Documents related PV | `m1-2-15-relpv` | `m1/eg/12-form/1215-relpv/` |  |  |
| 114 | 54 | 1.2.15.1 | Latest valid PSMF Assessment Report / Confirmation E-mail of PSMF Document(s) Receival | `m1-2-15-1-valpsmfas` | `m1/eg/12-form/1215-relpv/12151-valpsmfas/` |  |  |
| 115 | 55 | 1.2.15.2 | Updated Version of Summary of PSMF(s) / PSSF | `m1-2-15-2-updpsmf` | `m1/eg/12-form/1215-relpv/12152-updpsmf/` |  |  |
| 116 | 55 | 1.2.15.3 | The latest PSUR(s) (or the ACO in Case of Renewal) | `m1-2-15-3-latpsur` | `m1/eg/12-form/1215-relpv/12153-latpsur` |  |  |
| 117 | 55 | 1.2.15.4 | The most updated EU/Global/Core-Risk Management Plan (RMP) | `m1-2-15-4-updrmp` | `m1/eg/12-form/1215-relpv/12154-updrmp` |  |  |
| 118 | 55 | 1.2.15.5 | The Egyptian Display of EU-RMP / Global-RMP | `m1-2-15-5-egrmp` | `m1/eg/12-form/1215-relpv/12155-egrmp` |  |  |
| 119 | 55 | 1.2.16 | Documents related Inspection | `m1-2-16-relinsp` | `m1/eg/12-form/1216-relinsp` |  |  |
| 120 | 56 | 1.2.16.1 | Site Master File for all Manufacturers | `m1-2-16-1-smfall` | `m1/eg/12-form/1216-relinsp/12161-smfall` |  |  |
| 121 | 56 | 1.2.16.2 | Latest Full Inspection Report(s) by SRA (past 3 Years) | `m1-2-16-2-fullinsprep` | `m1/eg/12-form/1216-relinsp/12162-fullinsprep/` |  |  |
| 122 | 56 | 1.2.16.3 | One completed Batch Manufacturing and Packaging Record | `m1-2-16-3-batchrep` | `m1/eg/12-form/1216-relinsp/12163-batchrep` |  |  |
| 123 | 56 | 1.2.16.4 | List of any Recalls with Quality Defects (past 3 Years) (if found) | `m1-2-16-4-recalls` | `m1/eg/12-form/1216-relinsp/12164-recalls` |  |  |
| 124 | 57 | 1.2.16.5 | Any Warning Letter or equivalent regulatory Action (Production-line specific) (if found) | `m1-2-16-5-warnlet` | `m1/eg/12-form/1216-relinsp/12165-warnlet` |  |  |
| 125 | 57 | 1.2.16.6 | Last Annual Product Quality Review | `m1-2-16-6-annualrev` | `m1/eg/12-form/1216-relinsp/12166-annualrev` |  |  |
| 126 | 57 | 1.2.16.7 | Cold Chain Storage & Transportation Procedures including Excursion allowed | `m1-2-16-7-coldchain` | `m1/eg/12-form/1216-relinsp/12167-coldchain` |  |  |
| 127 | 57 | 1.3 | Product Information | `m1-3-pi` | `m1/eg/13-pi` |  | General placeholder for Product Information. |
| 128 | 57 | 1.3.1 | SmPC, Labelling and Package Leaflet | `m1-3-1-spc-label-pl` | `m1/eg/13-pi/131-spclabelpl` |  | General placeholder for SmPC, Package Leaflet. |
| 129 | 58 |  |  |  | `m1/eg/13-pi/131-spclabelpl/LL` |  | Always use a language directory at this level during the lifecycle of the submission (Arabic or English). |
| 130 | 58 |  |  |  |  | `m1/eg/13-pi/131-spclabelpl/LL/PIDOC-VAR.EXT` | Filename for the spc-label-pl document composed of a fixed component “PIDOC” as per table of Appendix 2.3 and an optional variable component to be used if needed (e.g. m1/eg/13-pi/131-spclabelpl/ar/spc-tablet10mgar.pdf). Summary of Product Characteristics "spc" & Package Leaflet "pl" are required by EDA |
| 131 | 58 | 1.3.2 | Mock-up | `m1-3-2-mockup` | `m1/eg/13-pi/132-mockup` |  |  |
| 132 | 59 |  |  |  |  | `m1/eg/13-pi/132-mockup/mockup-VAR.EXT` | Filename for the mock-up document composed of a fixed component “mockup” and an optional variable component to be used if needed (e.g. mockup-tablet10mgouter.pdf). |
| 133 | 59 | 1.3.3 | Specimen | `m1-3-3-specimen` | `m1/eg/13-pi/133-specimen` |  |  |
| 134 | 59 |  |  |  |  | `m1/eg/13-pi/133-specimen/specimen-VAR.EXT` | Filename for the list of physical specimens provided with the submission composed of a fixed component “specimen” and an optional variable component to be used if needed (e.g. specimen.pdf). |
| 135 | 59 | 1.3.4 | Consultation with Target Patient Groups | `m1-3-4-consultation` | `m1/eg/13-pi/134-consultation` |  |  |
| 136 | 60 |  |  |  |  | `m1/eg/13-pi/134-consultation/consultation-VAR.EXT` | Filename for the results of assessments carried out in cooperation with target patient groups on the package leaflet, composed of a fixed component “consultation” and an optional variable component to be used if needed (e.g. consultation-tablet10mgpl.pdf). |
| 137 | 60 | 1.3.5 | Product Information already approved in the Member States | `m1-3-5-approved` | `m1/eg/13-pi/135-approved` |  |  |
| 138 | 60 |  |  |  |  | `m1/eg/13-pi/135-approved/approved-VAR.EXT` | Filename for the approved Product Information document composed of a fixed component “approved” and an optional variable component to be used if needed. |
| 139 | 60 | 1.3.6 | Braille | `m1-3-6-braille` | `m1/eg/13-pi/136-braille` |  |  |
| 140 | 61 |  |  |  |  | `m1/eg/13-pi/136-braille/braille-VAR.EXT` | Filename for the Braille information is composed of a fixed component “braille” and an optional variable component to be used if needed. (e.g. braille.pdf). |
| 141 | 61 | 1.4 | Information about the Experts | `m1-4-expert` | `m1/eg/14-expert` |  | General placeholder for Expert Information. |
| 142 | 61 | 1.4.1 | Quality | `m1-4-1-quality` | `m1/eg/14-expert/141-quality` |  | General placeholder for quality information. |
| 143 | 61 |  |  |  |  | `m1/eg/14-expert/141-quality/quality-VAR.EXT` | Filename for the quality expert document composed of a fixed component “quality” and an optional variable component to be used if needed (e.g. quality.pdf). |
| 144 | 62 | 1.4.2 | Non-Clinical | `m1-4-2-non-clinical` | `m1/eg/14-expert/142-nonclinical` |  | General placeholder for non-clinical information. |
| 145 | 62 |  |  |  |  | `m1/eg/14-expert/142-nonclinical/nonclinical-VAR.EXT` | Filename for the non-clinical expert document composed of a fixed component “nonclinical” and an optional variable component to be used if needed (e.g. nonclinical.pdf). |
| 144 | 62 | 1.4.3 | Clinical | `m1-4-3-clinical` | `m1/eg/14-expert/143-clinical` |  | General placeholder for clinical information. |
| 145 | 63 |  |  |  |  | `m1/eg/14-expert/143-clinical/clinical-VAR.EXT` | Filename for the clinical expert document composed of a fixed component “clinical” and an optional variable component to be used if needed (e.g. clinical.pdf). |
| 146 | 63 | 1.5 | Specific Requirements for Different Types of Applications | `m1-5-specific` | `m1/eg/15-specific` |  | General placeholder for Specific Information. |
| 147 | 63 | 1.5.1 | Information for Bibliographical Applications | `m1-5-1-bibliographic` | `m1/eg/15-specific/151-bibliographic` |  | General placeholder for bibliographical applications. |
| 148 | 64 |  |  |  |  | `m1/eg/15-specific/151-bibliographic/bibliographic-VAR.EXT` | Filename for the specific bibliographic submission information composed of a fixed component “bibliographic” and an optional variable component to be used if needed (e.g. bibliographic.pdf). |
| 149 | 64 | 1.5.2 | Information for Generic, Hybrid’ or Bio-similar Applications | `m1-5-2-generic-hybrid-bio-similar` | `m1/eg/15-specific/152-generic-hybrid-bio-similar` |  | General placeholder for generic, hybrid’ or bio-similar applications. |
| 150 | 64 |  |  |  |  | `m1/eg/15-specific/152-generic-hybrid-bio-similar/generic-VAR.EXT` or `m1/eg/15-specific/152-generic-hybrid-bio-similar/hybrid-VAR.EXT` or `m1/eg/15-specific/152-generic-hybrid-bio-similar/biosimilar-VAR.EXT` | Filename for the specific generic, hybrid or bio-similar submission information composed of a fixed component “generic” or “hybrid” or “biosimilar”, and an optional variable component to be used if needed (e.g. generic.pdf). |
| 151 | 65 | 1.5.3 | (Extended) Data/Market Exclusivity | `m1-5-3-data-market-exclusivity` | `m1/eg/15-specific/153-data-market-exclusivity` |  | General placeholder for (extended) data/market exclusivity. |
| 152 | 65 |  |  |  |  | `m1/eg/15-specific/153-data-market-exclusivity/datamarketexclusivity-VAR.EXT` | Filename for the data / market exclusivity composed of a fixed component “datamarketexclusivity” and an optional variable component to be used if needed (e.g. datamarketexclusivity.pdf). |
| 153 | 66 | 1.5.4 | Exceptional Circumstances | `m1-5-4-exceptional-circumstances` | `m1/eg/15-specific/154-exceptional` |  | General placeholder for marketing authorisation granted under exceptional circumstances. |
| 154 | 66 |  |  |  |  | `m1/eg/15-specific/154-exceptional/exceptional-VAR.EXT` | Filename for marketing authorisation granted under exceptional circumstances, composed of a fixed component “exceptional” and an optional variable component to be used if needed (e.g. exceptional.pdf). |
| 155 | 66 | 1.5.5 | Conditional Marketing Authorisation | `m1-5-5-conditional-ma` | `m1/eg/15-specific/155-conditional-ma` |  | General placeholder for conditional marketing authorisation. |
| 156 | 67 |  |  |  |  | `m1/eg/15-specific/155-conditional-ma/conditionalma-VAR.EXT` | Filename for conditional marketing authorisation, composed of a fixed component “conditionalma” and an optional variable component to be used if needed (e.g. conditionalma.pdf). |
| 157 | 67 | 1.6 | Environmental Risk Assessment | `m1-6-environrisk` | `m1/eg/16-environrisk` |  | General placeholder for Environmental Risk Assessment. |
| 158 | 67 | 1.6.1 | Non-GMO | `m1-6-1-non-gmo` | `m1/eg/16-environrisk/161-nongmo` |  | General placeholder for non-GMO. |
| 159 | 68 |  |  |  |  | `m1/eg/16-environrisk/161-nongmo/nongmo-VAR.EXT` | Filename for the environmental risk assessment non-GMO composed of a fixed component “nongmo” and an optional variable component to be used if needed (e.g. nongmo.pdf). Only one of the 2 folders 1.6.1 or 1.6.2 can have content when sending a sequence. |
| 160 | 68 | 1.6.2 | GMO | `m1-6-2-gmo` | `m1/eg/16-environrisk/162-gmo` |  | General placeholder for GMO. |
| 161 | 69 |  |  |  |  | `m1/eg/16-environrisk/162-gmo/gmo-VAR.EXT` | Filename for the environmental risk assessment GMO-composed of a fixed component “gmo” and an optional variable component to be used if needed (e.g. gmo.pdf). Only one of the 2 folders 1.6.1 or 1.6.2 can have content when sending a sequence. |
| 162 | 69 | 1.7 | Information relating to Orphan Market Exclusivity | `m1-7-orphan` | `m1/eg/17-orphan` |  | General placeholder for Orphan Market Exclusivity information. |
| 163 | 69 | 1.7.1 | Similarity | `m1-7-1-similarity` | `m1/eg/17-orphan/171-similarity` |  | General placeholder for information on similarity with authorised orphan product. |
| 164 | 70 |  |  |  |  | `m1/eg/17-orphan/171-similarity/similarity-VAR.EXT` | Filename for the information on similarity composed of a fixed component “similarity” and an optional variable component to be used if needed. |
| 165 | 70 | 1.7.2 | Market Exclusivity | `m1-7-2-market-exclusivity` | `m1/eg/17-orphan/172-market-exclusivity` |  | General placeholder for information on market exclusivity. |
| 166 | 71 |  |  |  |  | `m1/eg/17-orphan/172-market-exclusivity/marketexclusivity-VAR.EXT` | Filename for information on market exclusivity composed of a fixed component “marketexclusivity” and an optional variable component to be used if needed. |
| 167 | 71 | 1.8 | Information relating to Pharmacovigilance | `m1-8-pharmacovigilance` | `m1/eg/18-pharmacovigilance` |  | General placeholder for information on pharmacovigilance. |
| 168 | 71 | 1.8.1 | Pharmacovigilance System | `m1-8-1-pharmacovigilance-system` | `m1/eg/18-pharmacovigilance/181-phvig-system` |  | General placeholder for information on pharmacovigilance system. |
| 169 | 72 |  |  |  |  | `m1/eg/18-pharmacovigilance/181-phvig-system/phvigsystem-VAR.EXT` | Filename for information on pharmacovigilance system composed of a fixed component “phvigsystem” and an optional variable component to be used if needed. |
| 170 | 72 | 1.8.2 | Risk-management System | `m1-8-2-risk-management-system` | `m1/eg/18-pharmacovigilance/182-riskmgt-system` |  | General placeholder for information on risk management system. |
| 171 | 72 |  |  |  |  | `m1/eg/18-pharmacovigilance/182-riskmgt-system/riskmgtsystem-VAR.EXT` | Filename for information on pharmacovigilance system composed of a fixed component “riskmgtsystem” and an optional variable component to be used if needed. |
| 172 | 73 | 1.9 | Information relating to Clinical Trials | `m1-9-clinical-trials` | `m1/eg/19-clinical-trials` |  | General placeholder for information on clinical trials. |
| 173 | 73 |  |  |  |  | `m1/eg/19-clinical-trials/clinicaltrials-VAR.EXT` | Filename for information on clinical trials composed of a fixed component “clinicaltrials” and an optional variable component to be used if needed. |
| 174 | 73 | 1.10 | Information relating to Paediatrics | `m1-10-paediatrics` | `m1/eg/110-paediatrics` |  | General placeholder for information on paediatrics. |
| 175 | 74 |  |  |  |  | `m1/eg/110-paediatrics/paediatrics-VAR.EXT` | Filename for information on paediatrics composed of a fixed component “paediatrics” and an optional variable component to be used if needed. |
| 176 | 74 |  | Responses to Questions | `m1-responses` | `m1/eg/responses` |  |  |
| 177 | 75 |  |  |  | `m1/eg/responses` | `m1/eg/responses/responses-VAR.EXT` | Placeholder for responses document. For file name of the response document please see section Node Extensions |
| 178 | 75 |  | Additional Data | `m1-additional-data` | `m1/eg/additional-data` |  | The section 'Additional Data’ should only be used for required information that is not currently included in the EG eCTD M1 Specification. Supportive documents, which are not part of any M2-5 section or Response to Questions, should be placed here. Any updates to documents originating from M2-5 should replace the outdated version in its original location in M2-5. Supportive documents submitted as answers to questions should be placed in Module 1 Responses to Questions. This section is not intended for including already submitted documents. Any information/file which was already submitted in a previous sequence should not be submitted again in eCTD. For already submitted documents, a reference/hyperlink/cross-link to the existing file should be created. This helps to avoid multiple lifecycles and repetitions of the files. |
| 179 | 76 |  |  |  |  | `m1/eg/additional-data/additionaldata-VAR.EXT` | Filename for additional information requested composed of a fixed component “additionaldata” and an optional variable component to be used if needed (e.g. additionaldata-yellowpink.pdf)." |
| 180 | 76 |  |  |  | `m1/eg/util` |  | Additional folder to hold utility files used in EG |
| 181 | 76 |  |  |  | `m1/eg/util/dtd` |  | Additional folder to hold DTD files used in EG. |
| 182 | 77 |  |  |  | `util/dtd` |  | ICH specified location for eCTD DTD files. |
| 183 | 77 |  |  |  | `util/style` |  | ICH specified location for eCTD style-sheet files. The style-sheet to be used should be the most recent version, which is always published as part of the specification package for download. Note that the XML instance can only point to one style-sheet and that referencing a customised style-sheet will effectively prevent the EDA using the official one. It is therefore recommended not to submit customised style-sheets. |

Column notes: rows with an empty "CTD no." are the file-name or sub-directory rows belonging to the section above them.
Rows 9–126 (all of 1.2.2–1.2.16) give a **directory only — no file-name row, no fixed file-name component**; only
1.0 (`cover`, `tracking`) and 1.2.1 (`form-af`) inside 1.0–1.2 have file-name patterns. **GAP** for any tool that
enforces fixed file names.

### 6.3 Appendix 2.1–2.4 (SPEC p. 78 l. 328–337)

| Appendix | Content (verbatim) |
|---|---|
| 2.1 Destination Codes | "In most cases the destination code is an ISO-3166-1-alpha-2 code usually called “country code” or “CC” in this specification." Table: `eg` — Egypt — "ISO-3166-1-alpha-2 code" |
| 2.2 Language Codes | `ar` — Arabic; `en` — English |
| 2.3 SPC, Labelling and Package Leaflet File Name Identifiers | PI DOC `spc` — Summary of Product Characteristics; `pl` — Package Leaflet. Footnote: "* = When labelling documents (Outer and Immediate Packaging) are submitted as a single file, the type ‘interpack’ should be used" (the `*` is not attached to any table row) |
| 2.4 Agency Codes and Names | "The table below provides the Agency Code for the Egyptian Drug Authority. The Agency Code is the value to use from within the EG Module 1 XML file." Egypt — `EG-EDA` — Egyptian Drug Authority |

### 6.4 Folder tree (condensed view of §6.2; folder names exactly as printed)

```
DDDD/                                  (sequence folder; DDDD = 4 digits, p. 28)
├── m1/
│   └── eg/                            m1-eg (row 1)
│       ├── eg-regional.xml            row 2 — leaf operation always 'new'
│       ├── 10-cover/                  1.0  cover-VAR.EXT, tracking-VAR.EXT
│       ├── 12-form/                   1.2  (no files directly; "General placeholder for forms and annexes")
│       │   ├── 121-af/                1.2.1  form-af-VAR.EXT
│       │   ├── 122-legal/1221-loattor … 12221-gmpcert2/       1.2.2.1–1.2.2.21
│       │   ├── 123-edaapp/1231-regreq … 12320-reglicsolv/     1.2.3.1–1.2.3.20
│       │   ├── 124-declar/1241-regprod … 12422-storetemp/     1.2.4.1–1.2.4.22
│       │   ├── 125-refprod/1251…1254/                         1.2.5.1–1.2.5.4
│       │   ├── 126-importdoc/1261-cpp, 1262-loaff/            1.2.6.1–1.2.6.2
│       │   ├── 127-reliance/1271…1276/                        1.2.7.1–1.2.7.6
│       │   ├── 128-composit/1281…1287/                        1.2.8.1–1.2.8.7
│       │   ├── 129-coa/                                       1.2.9
│       │   ├── 1210-postappch/12101…12104/                    1.2.10.1–1.2.10.4
│       │   ├── 1211-pop/                                      1.2.11
│       │   ├── 1212-analysreq/12121-sop, 12122-sumvacc/       1.2.12.1–1.2.12.2
│       │   ├── 1213-plasma/12131-pmf, 12132-plasbatch, 12133-pmfapp/   1.2.13.1–1.2.13.3
│       │   ├── 1214-scienadv/                                 1.2.14
│       │   ├── 1215-relpv/12151…12155/                        1.2.15.1–1.2.15.5
│       │   └── 1216-relinsp/12161…12167/                      1.2.16.1–1.2.16.7
│       ├── 13-pi/
│       │   ├── 131-spclabelpl/LL/     PIDOC-VAR.EXT   (LL = ar | en)
│       │   ├── 132-mockup/            mockup-VAR.EXT
│       │   ├── 133-specimen/          specimen-VAR.EXT
│       │   ├── 134-consultation/      consultation-VAR.EXT
│       │   ├── 135-approved/          approved-VAR.EXT
│       │   └── 136-braille/           braille-VAR.EXT
│       ├── 14-expert/141-quality, 142-nonclinical, 143-clinical/   quality- / nonclinical- / clinical-VAR.EXT
│       ├── 15-specific/151-bibliographic, 152-generic-hybrid-bio-similar, 153-data-market-exclusivity,
│       │               154-exceptional, 155-conditional-ma/
│       ├── 16-environrisk/161-nongmo | 162-gmo/  (only one of the two may have content in a sequence)
│       ├── 17-orphan/171-similarity, 172-market-exclusivity/
│       ├── 18-pharmacovigilance/181-phvig-system, 182-riskmgt-system/
│       ├── 19-clinical-trials/        clinicaltrials-VAR.EXT
│       ├── 110-paediatrics/           paediatrics-VAR.EXT
│       ├── responses/                 responses-VAR.EXT
│       ├── additional-data/           additionaldata-VAR.EXT
│       └── util/dtd/                  rows 180–181 "DTD files used in EG"
├── m2 … m5/                           (ICH)
└── util/dtd/, util/style/             rows 182–183 (ICH locations)
DDDD-workingdocuments/                 (outside the eCTD, same zip; Glossary p. 4–5)
```

---

## 7. File naming, variable part, path length, change control

### 7.1 File-naming convention (SPEC p. 10 l. 148–165; p. 11 l. 167–178)

| # | Rule | Line |
|---|---|---|
| F1 | "File names have the general structure FIXED-VAR.EXT, where FIXED is a defined component of the filename based on the CTD section and VAR is an additional optional variable component. EXT represents the file extension." | 149–151 |
| F2 | "Components are separated by a hyphen (except the dot for the file extension). No spaces should be used within each component, but hyphens can be used in the variable part to separate several words." | 151–153 |
| F3 | "Fixed components are highly recommended. The variable component is optional and should be used as appropriate … should be a meaningful concatenation of words with the option of hyphens for separators and should be kept as brief and descriptive as possible to avoid exceeding the maximum path length." | 154–157 |
| F4 | "The first should be the document type code, as per Appendix 2 and 2.3. The second component if necessary, should be the variable component." | 159–160 |
| F5 | Strength differentiation: "the word 'point' written in full (i.e. ‘1point5mg’) or a hyphen can be used (i.e.’1-5mg’)." | 160–162 |
| F6 | "There are no recommendations for variable components in this specification." | 163 |
| F7 | "File names should always be in lowercase, in line with the ICH eCTD specification." | 164–165 |
| F8 | Examples (verbatim): `cover.pdf` · `form-eaf.pdf` · `form-annex-01.pdf` · `outer-tablet10mg.pdf` · `combined-tablet1-5mg.pdf` · `combined-tablet10mgannotated.pdf nongmo.pdf` (two names printed on one line) | 167–173 |
| F9 | Responses: "In m1-responses, the recommendation is to use responses-<regulatory activity type identifier>-<response number>-<content identifier>.pdf" | 174–177 |

Response examples (p. 11 l. 178, verbatim):

| Suggested Filename | Suggested Leaf Title |
|---|---|
| responses-maa-clin.pdf | Clinical Responses, MAA |
| responses-maa-2nd-clin.pdf | 2nd Clinical Responses, MAA |
| responses-maa-3rd-clin.pdf | 3rd Clinical Responses, MAA |
| responses-maa-3rd-clinq4.pdf | 3rd Clinical Response Question 4, MAA |
| responses-maa-3rd-clinq7.pdf | 3rd Clinical Response Question 7, MAA |
| responses-var03-clin.pdf | Clinical Responses, Var03 |
| responses-var03-2nd-clin.pdf | 2nd Clinical Responses, Var03 |
| responses-maa-qual.pdf | Quality Responses, MAA |

Not stated in this draft: allowed character set (a–z, 0–9, hyphen), maximum file-name length, maximum folder-name
length — TG 2.5.2 gives 64 characters each (see §9).

### 7.2 Path length (SPEC p. 11 l. 180–183)
"The overall folder and file name path length starting from the sequence number should not exceed 180 characters, for any
file in any module. This is an EG regional requirement, and it is acknowledged that this is less than the ICH agreed
overall path length." Longest fixed path in App. 2 (computed here): `0000/m1/eg/15-specific/153-data-market-exclusivity/datamarketexclusivity-VAR.EXT`
= 80 characters before VAR is expanded, so ~100 characters remain for VAR + extension in the worst M1 case.
"starting from the sequence number" — whether the 4 digits themselves count is not said here (TG 2.5.2: "Counting starts
from the first digit of the sequence number").

### 7.3 Change control (SPEC p. 13 l. 223–237)
"The EG Module 1 specification is likely to change with time." Factors: change in M1 content; regional requirements outside
the CTD; update of standards in use; new standards; new functional requirements; "Experience of use of the eCTD by all
parties, in particular Module 1." Change requests: "raise a support ticket via the online form in the portal."
**GAP:** no versioning rule for the DTD, no transition rule (contrast TG 3.2.7 which mentions "an old version of a DTD …
during an agreed transition period").

---

## 8. Appendix 1 "XML" — what is (and is not) in the draft

**There are no DTD or `.mod` declarations and no XML instance examples anywhere in the draft.** Appendix 1 (p. 14–27)
consists only of the two description tables (envelope, `pi-doc`) and the related-sequence tables reproduced in §4–§5.
This was checked by full-text search of the `-layout` and `-raw` extractions for `<!ELEMENT`, `<!ATTLIST`, `<!DOCTYPE`,
`xmlns`, `<?xml`, `xlink` (zero hits) and by confirming the PDF contains no images other than the header logos. The body
text nevertheless promises them: "Examples of XML coding for a simple new application, specific regulatory activities are
provided as an appendix to this specification. Examples of XML coding that support the variation regulation are provided as
well in Appendix 1 … and Appendix 2" (p. 7 l. 54–57).

Everything the draft states about the XML artefacts, verbatim:

```text
p. 7 l. 44-49   The backbone must be a valid XML document according to the EG Regional Document Type Definition (DTD).
                The backbone instance (the "eg-regional.xml" file) contains meta-data for the leaves, including pointers
                to the files in the directory structure. In addition, the EG Regional DTD defines meta-data at the
                submission level in the form of an envelope. The root element is "eg-backbone" and contains two
                elements: "eg-envelope" and "m1-eg".
p. 7 l. 50-53   The EG Regional DTD is modularised, i.e. the envelope and leaves are referenced from the main part of
                the DTD as external entities called respectively "eg-envelope.mod" and "eg-leaf.mod ".
                The EG "leaf" is identical to the leaf element described in the ICH eCTD DTD; reference is made to
                Table 6-8 of the ICH eCTD Specification.
p. 29 row 2     m1/eg/eg-regional.xml — The EG Regional XML instance including envelope information. Note that the
                operation attribute for the eg.regional.xml should always be set to 'new'.
p. 76 row 181   m1/eg/util/dtd — Additional folder to hold DTD files used in EG.
p. 77 row 182   util/dtd — ICH specified location for eCTD DTD files.
p. 77 row 183   util/style — ICH specified location for eCTD style-sheet files. ... Note that the XML instance can only
                point to one style-sheet and that referencing a customised style-sheet will effectively prevent the
                EDA using the official one. It is therefore recommended not to submit customised style-sheets.
```

### 8.1 DERIVED content model (NOT EDA text — reconstructed from the draft's tables for engineering planning only)
Derived solely from App. 1.1/1.2 Constraint/Occurrence columns and App. 2 element names; order follows the draft's tables;
`?` optional, `+` 1..n, `*` 0..n. The real EG DTD may differ in names, order, element-vs-attribute choices and optionality.

```text
eg-backbone                                   p.7  (prefix, namespaces, dtd-version: UNKNOWN)
├── eg-envelope                               1
│   └── envelope  @country="eg"               1..n per table ("Repeatable"), only one country value exists
│       ├── identifier                        1    UUID
│       ├── submission @type @mode?           1    mode required for variation sequences
│       │   ├── number                        0..1 high-level number (B-GV-xxxx …)
│       │   └── procedure-tracking            1
│       │       └── number                    1..n (printed in the Attribute column — element in EU)
│       ├── submission-unit @type             1
│       ├── applicant                         1
│       ├── agency @code="EG-EDA"             1
│       ├── invented-name                     1..n per table ("should not be repeated for EDA submission")
│       ├── registration @type                1
│       ├── marketing @type                   1
│       ├── inn                               0..n
│       ├── sequence                          1
│       ├── related-sequence                  1..n
│       └── submission-description            1
└── m1-eg
    ├── m1-0-cover ── leaf*                   (optionality of every m1 element: UNKNOWN)
    ├── m1-2-form ── m1-2-1-af … m1-2-16-relinsp (each with its App. 2 children) ── leaf*
    ├── m1-3-pi ── m1-3-1-spc-label-pl ── pi-doc+ @xml:lang @type @country ── leaf*
    │          └── m1-3-2-mockup … m1-3-6-braille ── leaf*
    ├── m1-4-expert … m1-10-paediatrics (children per App. 2) ── leaf*
    ├── m1-responses ── (leaf | node-extension)*
    └── m1-additional-data ── leaf*
```

---

## 9. Comparison: EG M1 Spec draft vs EU M1 v3.1.1 vs EG Technical Guidance draft

EU facts are taken only from `EU-M1-3.1.1-reference-model-for-EG.md` (its own citations given in brackets); TG facts from
`ectd_draft_2026.clean.txt` by TG section. "=" agreement, "≠" contradiction, "~" partial.

### 9.1 Architecture, envelope and vocabularies

| Topic | EG M1 Spec draft (page) | EU M1 3.1.1 / DTD 3.1 | EG TG draft | Verdict |
|---|---|---|---|---|
| Regional file / folder | `m1/eg/eg-regional.xml` (p. 7, 29) | `m1/eu/eu-regional.xml` | `eg-regional.xml` (Glossary "Envelope"), `/XXXX/m1/eg/10-cover/` (3.2.3.2) | = (EG mirrors EU) |
| Root | `eg-backbone` with `eg-envelope`, `m1-eg` (p. 7); App. 1.1 also calls `eg-envelope` "root" (p. 14) | `eu:eu-backbone` (`eu-envelope`, `m1-eu`), `xmlns:eu`, `xmlns:xlink`, `dtd-version="3.1"` | silent | = structure; EG omits namespaces/version; EG text internally inconsistent about the root |
| Modules | `eg-envelope.mod`, `eg-leaf.mod` (p. 7) | `eu-envelope.mod`, `eu-leaf.mod` | silent | = by name |
| DTD text / examples | none (promised p. 7) | full DTD in SPEC App. 3 + util package | TG 2.9.5 "Further examples are provided in the EG eCTD M1 Specification document" | EG gap |
| `envelope/@country` | `eg`, envelope "Repeatable" (p. 14) | one envelope per receiving country; list of ~34 | TG 3.2.2 envelope table has **no country row** | ~ |
| `procedure/@type` | absent | required (centralised/national/MR/DC) | absent | EG drops — consistent with TG |
| `registration/@type`, `marketing/@type` | new, Mandatory (p. 18–19) | not in EU | present (3.2.2), CVs "published on the EDA web site" | = EG-only; CV values missing in both |
| `agency/@code` | `EG-EDA` (p. 18, 78) | `CC-ACRONYM` list, e.g. `EU-EMA` | "This authority code is ‘EDA’ for Egypt." (3.2.2) | **≠** Spec vs TG |
| `submission/@mode` values | `single`, `grouping`, `parallel-single`, `parallel-grouping` (p. 8); "parallel  grouping" (p. 15) | `single`, `grouping`, `worksharing` | Annex 6: "Single", "Grouping", "Parallel Single", "Parallel Grouping" (title case, spaces) | **≠** spellings; Spec p. 8 is the only token-like form |
| When mode is used | "only … in variation regulatory activities", every sequence of the activity (p. 8, 15) | variation, extension, worksharing (+PSUSA per HTG) | "only contain a value in case of variations regulatory activities and must be included in every sequence" (3.2.2) | = Spec/TG |
| High-level `number` when grouping | only for grouping across **multiple MAs**; "In case of a grouping concerning only one single marketing authorisation this number field should be left empty." (p. 16) | worksharing / super-grouping; empty for single-MA grouping | "If submission mode is set to 'grouping’ there should be a Submission Number … identical with the variation procedure number included in a Variation Application Form." (3.2.2) — but also "not required in case only one product is concerned" | **≠** TG self-contradictory; Spec = EU logic |
| `number` formats | `B-GV-xxxx`, `B-PGV-xxxx`, `I-GV-xxxx` (p. 16) | `EMA/VR/xxxxxxxxxx` | none | EG-only |
| Tracking numbers | ≥1 EDA number + optional internal; examples `P-VAR-PAC-N-0002`, `I-IPV-PU-0001` (p. 17) | ≥1 regulator number; "to be advised" if unknown | "Always to be completed" (3.2.2) | = ; EG has no "to be advised" rule |
| `invented-name` | Mandatory Repeatable, "should not be repeated for EDA submission" (p. 18) | `invented-name+` | "a simple entry … will suffice" (3.2.2) | ~ (EG cardinality vs instruction clash) |
| `inn` | Optional Repeatable (p. 19) | `inn*`; required for maa+initial (VC 14.8) | listed, no cardinality | = ; EG has no maa rule |
| `sequence` | from 0000, increase incrementally (p. 19) | must equal folder name | "must match the sequence number in the folder structure and on the Cover letter" (3.2.2) | = (folder-match rule only in TG) |
| `related-sequence` rules | p. 19, 21 | same wording | 2.9.5 same | = |
| "highest category" wording | "‘grouping’ should be used" (p. 21 l. 262) | — | "should state ‘grouped’" (2.9.5) | ≠ token (`grouping` vs "grouped") |
| `submission/@type` N.B. | "Officially, Roman numerals are used for variations, e.g. Type VAR PAC-II – the elements must remain Arabic, however." (p. 14) | EU sentence; EU tokens are Arabic (`var-type2`) | Annex 6 token `var-pac-ii` (Roman); 2.9.5 Table 1 `var-pac-II` | **≠** — the N.B. is an EU remnant contradicted by the EG tokens |
| Variation type in examples | `Var PAC-II` (p. 23–25) | `var-type2` | `var-pac-II` (2.9.5) / `var-pac-ii` (Annex 6) / "Var PAC-II" = Annex 6 *title* column | **≠** three spellings for one value |
| Withdrawal type | `Withdrawal` (p. 26 table), ‘withdrawal’ (l. 293) | `withdrawal` | `withdrawal` (4.6; Annex 6 biologics list only) | ~ case; TG lists it only under Biologics & Innovative |
| Reformat type | `none` + unit `reformat` (p. 25) | `none` + `reformat` | Annex 6 `none`; `reformat` "always … together with the submission type ‘none’" | = |
| Submission units | initial, response, additional-info, validation-response, reformat (+ typo `responses`) | initial, validation-response, response, additional-info, closing, consolidating, corrigendum, reformat, re-examination | Annex 6: initial, validation-response, response, additional-info, corrigendum, reformat, re-examination | = subset; neither EG text has closing/consolidating |
| Consolidation after rejection/withdrawal | unit ‘Response’ (p. 25) | EU HTG: "consolidating" (per EU ref §5.1 note on HTG 4.11) | ‘Response’ (4.7; Annex 6) | Spec = TG ≠ EU |
| UUID | ISO/ITU refs, 8-4-4-4-12, v4 recommended, case free but stable, re-send with new UUID same sequence (p. 11–12) | same refs and v4; new UUID only on split/merge/re-baseline | 2.9.1: random, example `123e4567-e89b-12d3-a456- 426655440000` (a version-1 pattern); change only per 2.11.2 re-baselining | ~ (TG example contradicts v4 advice; Spec adds duplicate-UUID re-send rule) |
| Path length | 180 from the sequence number (p. 11) | 180 | 180; 64 for file and folder names (2.5.2) | = ; 64-char limits only in TG |
| File formats | PDF 1.4–1.7, PDF/A-1, PDF/A-2; "EG Accepted File Formats for eCTD" (p. 6) | FMT v1.0 | same sentence (2.9.2) | = ; referenced list not published in either |
| Placeholder/N.A. docs | not included; justify in M2 / in the M1 section (p. 6) | same | 3.2.1 same; "all section titles should always appear … displayed by the style sheet" | = |
| Node extensions | rules N1–N10 (p. 9–10); subfolders optional outside M5 | same | 2.9.8: "additional folders in m1-responses are not allowed" | ~ TG stricter than Spec |
| Cover / tracking | `cover-VAR.EXT`, `tracking-VAR.EXT` in `10-cover/` (rows 4–5) | `CC-cover-VAR`, `CC-tracking-VAR` in `10-cover/CC/` | `tracking-var.pdf` in `/XXXX/m1/eg/10-cover/` (3.2.3.2) | Spec = TG ≠ EU (no CC) |
| Application form | `form-af-VAR.EXT` in `12-form/121-af/` (row 8); file-name example `form-eaf.pdf` (p. 11 l. 169) | `CC-form-eaf-VAR` in `12-form/CC/` | `form-af.pdf`, `form-af-10mg` (3.2.4.1) | **≠** Spec internal (`form-af` vs `form-eaf`); TG = row 8 |
| Annexes to the form | `form-annex-01.pdf` example (p. 11) but no annex row in App. 2 | `CC-form-annex-VAR` | none | EU remnant |
| Supportive docs not in M2–5 / not responses | row 178: "should be placed here" (Additional Data) | EU HTG/Spec: attach to 1.2 (rows 9–10, App. 2) | 3.2.4.1: "should be placed in the application form section 1.2" ; 3.2.7: Additional Data only for info "not currently included in the published EG eCTD M1 Specification" | **≠** Spec row 178 vs TG 3.2.4.1 |
| Country folders | p. 9 "Country directories are named according to Appendix 2.1", `CC` code defined (p. 28) — but no row uses `CC` | CC folders in 1.0, 1.2, 1.3.2–1.3.5, responses, additional-data; CC+LL in 1.3.1 | TG 3.2.1 drops EU "country code should appear in the file and folder name"; 2.9.6 example `<pi-doc … country="eg">` | Spec internal ≠ (text vs table); table = TG |
| Language folders | only 1.3.1 `LL` (`ar`/`en`) (rows 129–130) | 1.3.1 `CC/LL` | 2.9.6 examples `xml:lang="en"`, `"ar"` | = |
| PI types | table: `spc`, `pl`; footnote `interpack`; examples `combined`, `outer` | spc, annex2, outer, interpack, impack, other, pl, combined | 2.9.6 examples `type="combined"`, `type="other"` | **≠** Spec App. 2.3 too short for its own and TG's examples |
| Responses folder | `m1/eg/responses/responses-VAR.EXT` (no CC) | `responses/CC/CC-responses-VAR` | same pattern as Spec (3.2.6 Table 4 = Spec p. 11 table, identical 8 rows) | Spec = TG |
| Section 1.2 tree | 16 sub-sections, 120 numbered 1.2.x entries with elements and folders (rows 6–126) | flat `m1-2-form` | Annex 5 Table 7: same 120 numbers and titles (checked programmatically — identical apart from letter case); TG says "Titles in italics are folders, containing subfolders but do not contain documents" | = numbering; Spec adds elements/folders, TG adds the "no documents in parent folders" rule which Spec does not state |
| 1.3–1.10 | EU structure kept (consultation, "approved in the Member States", orphan, paediatrics, …) | identical element names and folders | silent | = EU (EU-specific titles left in) |
| Style sheet | "published as part of the specification package" (row 183) | `eu-regional.xsl` | "displayed by the style sheet" (3.2.1) | neither EG doc names the file |
| Validation criteria | p. 13 "the related validation rules" | VC v8.2 | "EG Validation Criteria" (2.9.11, Annex 1) | not published with either draft |

### 9.2 Submission-type tokens (Spec examples vs TG Annex 6)

| Concept | SPEC (where) | TG | Note |
|---|---|---|---|
| MA application | `maa` (p. 14, 22, 24) | `maa` (Pharmaceuticals); `maa-inn`, `maa-nt`, `maa-ft`, `maa-sb`, `maa-rl1`, `maa-rl2`, `maa-bios` (Innovative/Biologicals) | Spec shows only `maa` |
| Major pharma variation | `Var PAC-II`, "Type VAR PAC-II" | `var-pac-ii` (Annex 6 token), `var-pac-II` (2.9.5 Table 1), title "Var PAC-II" | three spellings; XML is case-sensitive, so only one can be valid |
| Reformat / baseline | `none` | `none` | = |
| Withdrawal of MA | `Withdrawal` / ‘withdrawal’ | `withdrawal` (only in the Biologics & Innovative general list) | case; and whether pharmaceuticals may use it |
| Other TG tokens (never in Spec) | — | `var-pac-n`, `var-pac-b`, `var-pac-a`, `renewal`, `asmf`, `cep`, `preass`, `pacstab`, `paccadc`, `paci`, `pacqr`, `5yr`, `appeal`, `preappinq`, `PMF` (upper case), `ipv-admc`, `ipv-admlc` (abbrev. printed "IPV-ADMIC"), `ipv-tlc`, `ipv-pu`, `ipv-safeffc`, `imv-majvar`, `imv-minvar`, `imv-not`, `ibv-majqualc`, `ibv-modqualc`, `ibv-minqualc`, `ibv-qcnoimp`, `np-modqualc`, `np-pilc`, `np-majqualc`, `np-safeffc`, `np-admpilc`, `np-packup`, `np-adminc`, `rp-majcq`, `rp-modqc`, `rl-pilc`, `not-minqc`, `not-qcnoimp` | Spec's tracking-number examples `P-VAR-PAC-N-0002` / `I-IPV-PU-0001` line up with TG tokens `var-pac-n` / `ipv-pu` (an inference, not stated) |

---

## 10. Ambiguities, errors and gaps worth raising with EDA

Numbered for use in a consultation comment table. Page/line in brackets.

**A. Missing normative artefacts**
1. No EG regional DTD, `eg-envelope.mod`, `eg-leaf.mod`, style sheet, or XML examples, although p. 7 l. 54–57 says XML
   examples are in Appendix 1/2 and row 183 refers to a "specification package". Without them no tool can produce a valid
   `eg-regional.xml`. Ask EDA to publish the util package (with MD5 checksums) together with the adopted spec.
2. DTD file name, DTD version / `dtd-version`, DOCTYPE system identifier, namespaces (`xmlns:eg`?, `xmlns:xlink`) and
   whether the root is prefixed are not stated (p. 7).
3. None of the five controlled vocabularies the envelope relies on (Submission Type, Submission Mode, Submission Unit,
   Registration Type, Marketing Type) is included (p. 14 l. 243–244; p. 15, 18, 19). Registration/Marketing types are
   undefined in both EG drafts beyond examples.
4. "EG Accepted File Formats for eCTD" (p. 6 l. 14–15) and the EG validation rules (p. 13 l. 236) are referenced but not published.
5. How `index.xml` must reference `eg-regional.xml` (leaf ID/title, checksum) is not stated.
6. Which `util/dtd` folder holds the EG DTD: `m1/eg/util/dtd` (row 181) or `util/dtd` (row 182)?
7. No fixed file-name components for any 1.2.2–1.2.16 section or sub-section (rows 9–126); only folders are given.
8. Missing examples promised in the text: mode examples "in Appendix 1.1" (p. 8 l. 79–80); multi-MA related-sequence
   example "given in the Appendix" (p. 21 l. 266–267); "Samples are provided in the EG M1 Specification" (Glossary p. 3,
   a self-reference).

**B. Internal contradictions in the Spec draft**
9. Root element: `eg-backbone` (p. 7 l. 48–49) vs "The “eg-envelope” element is the root element" (p. 14 l. 242, table).
10. `envelope` "Repeatable" (p. 14) while the only `country` value is `eg` — when would a second envelope be used?
11. `invented-name` "Mandatory / Repeatable" but "(should not be repeated for EDA submission.)" (p. 18).
12. N.B. "the elements must remain Arabic" (p. 14) contradicts the EG tokens that carry Roman "ii" (`var-pac-ii` in TG
    Annex 6) and the Spec's own examples `Var PAC-II`.
13. Submission-type values in the worked examples are human titles (`Var PAC-II`, `Withdrawal`) not tokens; one table
    uses unit `responses` (p. 25 Table 4) and the text ‘Response’ (p. 25 l. 285) — neither matches the token `response`.
14. Mode token `parallel-grouping` (p. 8 l. 79) vs "parallel  grouping" (p. 15); `parallel-single` and `parallel-grouping`
    have identical definitions (p. 15) — the difference (one vs several variations?) is not written.
15. Country directories "named according to Appendix 2.1" (p. 9 l. 100) and code `CC` (p. 28) — but no Appendix 2 path
    uses a country directory; `pi-doc/@country` is mandatory without a CC folder.
16. Appendix 2.3 allows only `spc` and `pl`, yet the draft uses `combined` (App. 1.2 example, p. 27; p. 11 l. 172–173),
    `outer` (p. 11 l. 171) and `interpack` (footnote p. 78, whose `*` points at nothing). TG 2.9.6 additionally uses `other`.
17. File-name examples `form-eaf.pdf` and `form-annex-01.pdf` (p. 11 l. 169–170) contradict row 8 `form-af-VAR.EXT`;
    there is no annex row. `combined-tablet10mgannotated.pdf nongmo.pdf` is printed as one line (l. 173).
18. Appendix 2 sequential numbers 144 and 145 are used twice (p. 62–63); row 129 has no Title line; row 177 repeats the
    directory of row 176; row 5 uses `/XXXX/` instead of the defined `DDDD`; row 2 says "eg.regional.xml".
19. The App. 2 definition says paths are relative to `m1/eg/` ("e.g. 12-form/121-af/form-af.pdf", p. 28) but every row
    prints `m1/eg/...`; seven directory paths have a trailing slash and the rest do not.
20. 1.2.2.3 "GMP Certificate(s) / Alternative Documents" (`gmpcert`) and 1.2.2.21 "GMP Certificate" (`gmpcert2`) overlap;
    1.2.15 PV documents (PSMF, PSUR, RMP) overlap with 1.8.1/1.8.2 (pharmacovigilance system / risk-management system);
    1.2.4.11 Ph. Eur. CEP for TSE vs 1.2.4.12 TSE declaration are fine but 1.2.13.1 Plasma Master File vs submission type
    `PMF` placement is not explained. Placement rules are needed to keep lifecycle consistent.
21. EU-only content left in: 1.3.5 "Product Information already approved in the Member States" (row 137); "post
    authorisation measures" (p. 21 l. 259, 264) for which EG has no submission type; "Examples of XML coding that support
    the variation regulation" (p. 7); UUID "first sequence following the implementation of the UUID requirement" (p. 12
    l. 202–204) — meaningless for a new eCTD region.
22. UUID example in App. 1.1 `25635f23-a3a4-c4e0- b994-99c5f074960f` contains a space and has `c` in the version
    position (not a v1–v5 UUID per ISO/IEC 9834-8); "The ‘x’ will be replaced by a number or a letter" should read "a
    hexadecimal digit (0–9, a–f)" (p. 12 l. 199).
23. `procedure-tracking`'s `number` is printed in the Attribute column (p. 17) while the high-level `number` is an element
    (p. 16); state element vs attribute explicitly.
24. Path-length start point: "starting from the sequence number" (p. 11 l. 181) — say whether the 4 sequence digits count
    (TG: from the first digit).
25. Node-extension sub-folders: Spec allows optional sub-folders outside M5 (p. 10 l. 133–136) — TG 2.9.8 forbids
    additional folders in `m1-responses`. Pick one.
26. 1.6.1/1.6.2 "Only one of the 2 folders … can have content when sending a sequence" (rows 159, 161) — per sequence or
    per lifecycle? (cumulative view could show both).
27. Change-control (p. 13) has no DTD versioning or transition rule.
28. Scope gaps: no statement of which product types / administrations use which submission types; the `grouping` mode
    has a different meaning for Human Pharmaceuticals vs Biological/Innovative (p. 15) but nothing in the envelope says
    which administration a sequence goes to (only implied by number prefixes P-/B-/I-, which are never defined).

**C. Contradictions between the Spec draft and the TG draft**
29. Agency code `EG-EDA` (Spec p. 18, App. 2.4) vs ‘EDA’ (TG 3.2.2).
30. High-level number with grouping: Spec "left empty" for single-MA grouping (p. 16) vs TG "If submission mode is set to
    'grouping’ there should be a Submission Number … identical with the variation procedure number included in a
    Variation Application Form" (TG 3.2.2).
31. Variation token spellings: Spec `Var PAC-II` / "VAR PAC-II" vs TG `var-pac-II` (2.9.5) vs `var-pac-ii` (Annex 6).
32. Mode spellings: Spec `parallel-single`/`parallel-grouping` vs TG "Parallel Single"/"Parallel Grouping"; "grouping"
    (Spec p. 21) vs "grouped" (TG 2.9.5).
33. Where supportive documents not belonging to M2–5 or Responses go: Spec row 178 → Additional Data; TG 3.2.4.1 → section
    1.2 (and TG 3.2.7 limits Additional Data to information not in the M1 spec).
34. UUID example in TG 2.9.1 (`123e4567-e89b-12d3-a456-…`, a version-1 layout, also with a stray space) vs Spec
    recommendation of version 4; TG allows UUID change only on re-baselining (2.11.2), Spec adds a duplicate-UUID re-send
    with a new UUID under the same sequence number (p. 12 l. 214–218).
35. 64-character file/folder name limits and allowed characters exist only in TG 2.5.2, not in the Spec.
36. `pi-doc/@type="other"` used in TG 2.9.6 is not in Spec App. 2.3.
37. TG Annex 5 says parent ("italic") folders in 1.2 contain no documents; the Spec does not say this, and its 1.2.x
    parents have elements that could carry leaves under an EU-style DTD.
38. `withdrawal` appears in TG Annex 6 only under "Biologics and Innovative Products", while the Spec (p. 26) and TG 4.6
    present it as general.
