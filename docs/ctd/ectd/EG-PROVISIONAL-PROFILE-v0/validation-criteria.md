# EG provisional validation criteria v0 - summary

> **PROVISIONAL - not issued by EDA.** EDA says it has 'adopted a common set of technical validation criteria' (TG p.21 l.544-547) and refers to
> 'EG Validation Criteria' with a 'File-Folder Structure & Names' sheet (TG p.12 l.278-279; p.31 l.844; p.40 l.1104) - none was published with the drafts.
> This set maps every criterion of the EU Region eCTD Validation Criteria v8.2 (June 2025) and adds the rules the EDA drafts state.
> Full table: `validation-criteria.csv` (one row per rule; columns rule_id, category, rule_text, check_logic, provenance, source, eu_vc_ref, mapping, mapping_reason).

`EG-PF-` = Pass/Fail (the task's 'EG-P/F-'; the slash is left out so IDs are safe in file names and URLs), `EG-BP-` = Best Practice.
Kept/adapted EU rules keep the EU number (`EG-PF-15.3` <- EU 15.3); EG-only rules are numbered `E01`... Dropped EU rules are listed as `DROPPED-EU-<n>`.
Category meanings follow TG p.21 l.548-562 (Pass/Fail -> rejected, re-send with the same sequence number; Best Practice -> accepted).

## Counts

| Group | Rules |
|---|---|
| EU VC 8.2 criteria read | 111 |
| KEEP | 54 |
| ADAPT | 44 |
| DROP | 13 |
| EG-specific (from EDA drafts / decisions) | 43 |
| **Active EG rules (KEEP + ADAPT + EG-specific)** | **141** - Pass/Fail 87, Best Practice 54 |
| Provenance of active rules | EG-DRAFT 80, EU-DERIVED 53, ASSUMPTION 8 |

## Dropped EU rules

| EU rule | Reason |
|---|---|
| 11.BP1 | Only concerns EU country-specific sections; EG has none, so the check is part of EG-PF-11.9. |
| 14.1 | EU procedure types (centralised, 'ema' envelope) do not exist in EG; EG has no procedure element (decision D-12). |
| 14.2 | MRP/DCP envelopes per member state; not applicable. |
| 14.3 | National-procedure envelope rule; replaced by EG-PF-E01 (one envelope, country eg). |
| 14.4 | EDQM envelope; not applicable. |
| 14.9 | EDQM procedure type; not applicable. |
| 14.BP3 | Country-specific delete leaves; EG has one country. |
| 15.BP4 | EG App. 2 has no country folders (decision D-08). |
| 15.BP5 | EG file names have no country prefix (SPEC p.29-30 rows 4-5, p.30 row 8). |
| 16.4 | EU eAF exception for 1.0/1.2; EG grants no such exception (TG p.22 l.585-589); folded into EG-PF-16.3. |
| 16.6 | EU PLM-portal eAF / FHIR attachment; not applicable. |
| 16.7 | EU interactive eAF; not applicable. |
| 16.BP11 | Applies to EU centralised procedure only. |

## Adapted EU rules (what changed)

| EG rule | Category | Change |
|---|---|---|
| EG-PF-3.1 | Pass/Fail | The EG regional DTD is named eg-regional.dtd. - File name not stated by EDA; mirrors eu-regional.dtd (decision D-09). |
| EG-PF-3.2 | Pass/Fail | The EG regional DTD is placed in /XXXX/util/dtd. - Decision D-10: row 182 (ICH location) chosen over row 181. |
| EG-PF-3.3 | Pass/Fail | A currently acceptable version of the EG DTD is used (checksum matches the value published by EDA). - No EDA checksum exists yet. |
| EG-PF-3.4 | Pass/Fail | EG DTD version of this sequence >= that of the nearest lower-numbered sequence. |
| EG-PF-3.5 | Pass/Fail | EG DTD version of this sequence <= that of the nearest higher-numbered sequence. |
| EG-PF-4.1 | Pass/Fail | The leaf module is named eg-leaf.mod. |
| EG-PF-4.2 | Pass/Fail | eg-leaf.mod is placed in /XXXX/util/dtd. - Decision D-10. |
| EG-PF-4.3 | Pass/Fail | Checksum of eg-leaf.mod matches the value published for the EG DTD version used. |
| EG-PF-5.1 | Pass/Fail | The envelope module is named eg-envelope.mod. |
| EG-PF-5.2 | Pass/Fail | eg-envelope.mod is placed in /XXXX/util/dtd. - Decision D-10. |
| EG-PF-5.3 | Pass/Fail | Checksum of eg-envelope.mod matches the value published for the EG DTD version used. |
| EG-PF-6.1 | Pass/Fail | The EG style sheet is named eg-regional.xsl. - Decision D-11. |
| EG-PF-6.2 | Pass/Fail | eg-regional.xsl is placed in /XXXX/util/style. |
| EG-PF-6.3 | Pass/Fail | Checksum of eg-regional.xsl matches the value EDA publishes ('not to submit customised style-sheets'). |
| EG-PF-9.1 | Pass/Fail | eg-regional.xml is placed in /XXXX/m1/eg. |
| EG-PF-9.2 | Pass/Fail | The regional file is named eg-regional.xml. |
| EG-PF-9.3 | Pass/Fail | eg-regional.xml is well formed. |
| EG-PF-9.4 | Pass/Fail | eg-regional.xml is valid against the EG DTD in util/dtd. |
| EG-PF-9.5 | Pass/Fail | The DOCTYPE of eg-regional.xml points to util/dtd/eg-regional.dtd. |
| EG-PF-9.6 | Pass/Fail | The xml-stylesheet of eg-regional.xml points to util/style/eg-regional.xsl. |
| EG-PF-9.7 | Pass/Fail | The UUID (envelope/identifier) is well formed. |
| EG-PF-9.8 | Pass/Fail | The UUID equals the UUID of the nearest lower-numbered sequence of the same lifecycle, character for character (case included). - EU condition 'if submitted with v3.0 or higher' dropped: every EG sequence has a UUID. |
| EG-PF-9.9 | Pass/Fail | The UUID is identical in all envelopes of the sequence. |
| EG-PF-11.9 | Pass/Fail | The leaf referenced by modified-file exists in a previously submitted sequence of the same eCTD application. Applies to ALL leaves (EG has no country-specific sections). - EU exception list for country-specific m1 sections removed (decision D-08). |
| EG-PF-11.10 | Pass/Fail | For all leaves (except within node extensions and m3-2-a) with operation replace/delete/append the modified leaf is in the same CTD section; sections are also defined by the attributes in TG Table 2 and by pi-doc xml:lang/type/country. Deleting content in m1-additional-data is exempt. |
| EG-PF-13.2 | Pass/Fail | The sequence number has not already been used in this lifecycle, except to re-send a sequence that failed technical validation (same number) or a UUID-corrected sequence. - EU rule lacks the explicit re-send exception. |
| EG-PF-13.3 | Pass/Fail | The sequence folder name equals envelope/sequence in eg-regional.xml. |
| EG-PF-14.5 | Pass/Fail | For every pi-doc/@country used by leaves with operation new/replace/append there is an envelope with the same country. |
| EG-PF-14.6 | Pass/Fail | If the submission unit is 'initial' or 'reformat', there is exactly one related-sequence and it equals the sequence number. - 'exactly one' added (SPEC: 'always = sequence number'). |
| EG-PF-14.7 | Pass/Fail | If the submission unit is not 'initial'/'reformat', every related-sequence is numerically lower than the sequence number. - EG says '<', EU says '!='. |
| EG-BP-14.8 | Best Practice | If the submission type is maa or maa-* and the unit is 'initial', at least one inn element is present. - Downgraded to Best Practice: SPEC declares inn Optional, a P/F rule would contradict the EG draft. |
| EG-BP-14.BP4 | Best Practice | If submission mode is 'grouping' or 'parallel-grouping' there should be a submission/number (high-level number). - Decision D-13 (SPEC vs TG conflict on single-MA grouping). |
| EG-BP-14.BP5 | Best Practice | If submission mode is not 'grouping'/'parallel-grouping' there should not be a submission/number. |
| EG-BP-14.BP7 | Best Practice | When submission mode is 'grouping', the submission type is a variation type. |
| EG-BP-14.BP8 | Best Practice | When submission mode is 'parallel-single' or 'parallel-grouping', the submission type is a variation type. - EU worksharing rule re-used for the EG parallel modes. |
| EG-BP-15.BP1.1 | Best Practice | Files in m1 are in formats accepted by EDA. - EG list referenced but not published. |
| EG-BP-15.BP2.1 | Best Practice | Files in m2-m5 are in formats accepted by EDA. |
| EG-PF-15.11 | Pass/Fail | A tracking table is present in /XXXX/m1/eg/10-cover/ in every sequence (all procedures, no exception). - No country folder; no EDQM exception. |
| EG-PF-15.12 | Pass/Fail | The tracking table is named tracking.pdf or tracking-<var>.pdf. - EU 'cc-tracking' prefix removed. |
| EG-BP-15.BP2 | Best Practice | The folder structure and names of ICH and of folders.csv (EG App. 2) are used; no additional folders except node-extension sub-folders in m4/m5 and the 1.2.3.18 per-variation sub-folders (decision D-14). |
| EG-BP-15.BP3 | Best Practice | The recommended file names of ICH and of folders.csv are used (fixed component + optional -var). |
| EG-PF-16.3 | Pass/Fail | No PDF has any security restriction. Exception: digitally signed documents, where at least printing and content copying are allowed. No section is exempt (EU exemption for m1.0, m1.2, 3.3, 4.3, 5.4 not applied). - EG stricter than EU. |
| EG-BP-16.BP1 | Best Practice | PDFs are version 1.4, 1.5, 1.6 or 1.7 (PDF/A-1 and PDF/A-2 included), unless EDA requires a later version for a specific form. |
| EG-BP-16.BP5 | Best Practice | PDFs have Fast Web View (linearised). |

## EG-specific rules

| Rule | Category | Rule | Provenance | Source |
|---|---|---|---|---|
| EG-PF-E01 | Pass/Fail | eg-regional.xml contains exactly one envelope and its country attribute is 'eg'. | EG-DRAFT | SPEC p.14 (country 'The country is EGYPT (EG)'), App. 2.1 p.78; decision D-15 ('Repeatable' vs one country) |
| EG-PF-E02 | Pass/Fail | The agency code is 'EG-EDA'. | EG-DRAFT | SPEC p.18, App. 2.4 p.78 l.336-337; decision D-01 |
| EG-PF-E03 | Pass/Fail | registration/@type and marketing/@type are present and taken from the EG vocabularies. | EG-DRAFT | SPEC p.18-19 (Mandatory); TG p.28 l.754-759; tokens ASSUMPTION (vocab files) |
| EG-PF-E04 | Pass/Fail | submission/@mode is present in every sequence whose submission type is a variation type. | EG-DRAFT | SPEC p.8 l.78-80, p.15 ('must be populated for sequences in variations'); TG p.27 l.722-724 |
| EG-PF-E05 | Pass/Fail | Submission unit 'reformat' is used if and only if the submission type is 'none'. | EG-DRAFT | TG p.74 (reformat 'always … together with the submission type none'); TG p.61 ('none' only for reformatting); TG p.25 l.655-656; SPEC p.25 Table 3 |
| EG-PF-E06 | Pass/Fail | Mandatory text elements are not empty: identifier, applicant, invented-name, procedure-tracking/number, sequence, related-sequence, submission-description. | EG-DRAFT | SPEC App. 1.1 p.14-20 (Constraint 'Mandatory'); TG p.27 l.735 ('Always to be completed') |
| EG-PF-E07 | Pass/Fail | envelope/sequence and every related-sequence are four digits. | EG-DRAFT | SPEC p.19, p.28 (DDDD) |
| EG-PF-E08 | Pass/Fail | index.xml m1-administrative-information-and-prescribing-information contains exactly one leaf whose xlink:href is 'm1/eg/eg-regional.xml'. | EU-DERIVED | ICH DTD line 117 (m1 = leaf*); EU example ex1-CPv1.0/0012/index.xml; SPEC is silent (GAP, EG reference §3) |
| EG-PF-E09 | Pass/Fail | The submission package (zip root) contains only the sequence folder DDDD and, optionally, DDDD-workingdocuments with the same number. | EG-DRAFT | SPEC Glossary p.4-5 'Working Documents'; TG p.21 l.536-538; TG p.22 l.567-568 |
| EG-PF-E10 | Pass/Fail | No file in the submission contains malware. | EG-DRAFT | TG p.22 l.574-578 |
| EG-PF-E11 | Pass/Fail | Section 1.2 parent sections (1.2, 1.2.2-1.2.8, 1.2.10, 1.2.12, 1.2.13, 1.2.15, 1.2.16) contain no leaves and their folders contain no files directly. | EG-DRAFT | TG p.55 l.1414 ('Titles in italics are folders, containing subfolders but do not contain documents'); SPEC p.30 row 6 |
| EG-PF-E12 | Pass/Fail | At most one of m1-6-1-non-gmo / m1-6-2-gmo is present in a sequence. | EG-DRAFT | SPEC p.68-69 rows 159, 161 |
| EG-PF-E13 | Pass/Fail | pi-doc carries xml:lang in {ar, en}, a type from the pi-doc vocabulary and country 'eg'. | EG-DRAFT | SPEC p.27 l.301-304, App. 2.2-2.3 p.78; type list extended (decision D-16) |
| EG-BP-E01 | Best Practice | A cover letter (cover.pdf or cover-<var>.pdf) is present in m1/eg/10-cover/ in every sequence. | EG-DRAFT | SPEC p.29 row 4; TG p.28 l.761-770; HPG p.8 l.157-162 |
| EG-BP-E02 | Best Practice | Cover-letter and tracking-table leaves use operation 'new'. | EG-DRAFT | TG p.28 l.763; VC 11.7 comment (tracking table 'new') |
| EG-BP-E03 | Best Practice | The application form uses operation 'new', or 'replace' only to correct an earlier form. | EG-DRAFT | TG p.29 l.783-786 |
| EG-BP-E04 | Best Practice | One application form is named form-af.pdf; several are named form-af-<var>.pdf (e.g. form-af-10mg.pdf). | EG-DRAFT | SPEC p.30 row 8; TG p.29 l.787-789 (SPEC p.11 l.169 example 'form-eaf.pdf' contradicts - decision D-17) |
| EG-BP-E05 | Best Practice | The eg-regional.xml leaf in index.xml uses operation 'new'. | EG-DRAFT | SPEC p.29 row 2 |
| EG-BP-E06 | Best Practice | Operation 'append' is not used. | EG-DRAFT | TG p.18 l.434-435; TG p.29 l.802-803 |
| EG-BP-E07 | Best Practice | submission/@mode is used only for variation types. | EG-DRAFT | SPEC p.8 l.78; p.15 |
| EG-BP-E08 | Best Practice | Only one invented-name is given. | EG-DRAFT | SPEC p.18 ('should not be repeated for EDA submission'); TG p.27 l.744-746 |
| EG-BP-E09 | Best Practice | applicant is spelled identically in every sequence of the lifecycle. | EG-DRAFT | TG p.27 l.739-742 |
| EG-BP-E10 | Best Practice | The first sequence of a lifecycle is 0000 (otherwise the cover letter explains why). | EG-DRAFT | TG p.16 l.392-395; SPEC p.19 |
| EG-BP-E11 | Best Practice | A baseline (unit reformat) is sequence 0000, is a separate submission and contains no new regulatory activity. | EG-DRAFT | TG p.23 l.607-610; TG p.25 l.654-660 |
| EG-BP-E12 | Best Practice | Submission type 'withdrawal' uses unit 'initial' (related-sequence = sequence) and normally contains only a cover letter (and tracking table). | EG-DRAFT | SPEC p.26 l.291-294; TG p.38 l.1061-1064 |
| EG-BP-E13 | Best Practice | High-level submission number follows the EDA pattern, e.g. B-GV-xxxx, B-PGV-xxxx, I-GV-xxxx. | ASSUMPTION | SPEC p.16 (examples only; prefixes never defined) |
| EG-BP-E14 | Best Practice | At least one procedure-tracking number is an EDA portal number, e.g. P-VAR-PAC-N-0002, I-IPV-PU-0001. | ASSUMPTION | SPEC p.17 (examples only) |
| EG-BP-E15 | Best Practice | UUID is version 4 (random). | EG-DRAFT | SPEC p.12 l.200-201; TG p.14 l.315-318 |
| EG-BP-E16 | Best Practice | Product-information files of 1.3.1 are in m1/eg/13-pi/131-spclabelpl/<LL>/ where LL equals the pi-doc xml:lang. | EG-DRAFT | SPEC p.58 rows 129-130; SPEC p.9 l.104-105 |
| EG-BP-E17 | Best Practice | Leaves in m1-responses are grouped under a node-extension named after the regulatory activity; the list of questions is the first leaf. | EG-DRAFT | SPEC p.10 l.137-142; TG p.29 l.804-809 |
| EG-BP-E18 | Best Practice | No sub-folders under m1/eg/responses. | EG-DRAFT | TG p.20 l.520-522 (SPEC p.10 l.133-136 would allow them - decision D-18) |
| EG-BP-E19 | Best Practice | Response files are named responses-<activity>-<response number>-<content>.pdf. | EG-DRAFT | SPEC p.10 l.143-147, p.11 table; TG p.30 l.820-825 |
| EG-BP-E20 | Best Practice | No MS Word or other editable working files inside m1-m5; they go to DDDD-workingdocuments. | EG-DRAFT | TG p.14 l.336-338; TG p.21 l.533-538; TG p.29 l.794-796 |
| EG-BP-E21 | Best Practice | No validation reports in DDDD-workingdocuments. | EG-DRAFT | TG p.21 l.539-541 ('must NOT be included'); kept BP because detection is heuristic |
| EG-BP-E22 | Best Practice | One eCTD application (one UUID) per strength or dosage form. | EG-DRAFT | TG p.11 l.225-229; SPEC Glossary p.3-4 ('eCTD application') |
| EG-BP-E23 | Best Practice | PDFs are not PDF Portfolios, have embedded fonts, are tagged where possible and text-searchable (OCR for scans except the listed document types). | EG-DRAFT | TG p.15 l.353-374; TG p.16 l.376-379 |
| EG-BP-E24 | Best Practice | No 'not applicable' placeholder documents; absence is justified in the corresponding section or Module 2. | EG-DRAFT | SPEC p.6 l.21-28; TG p.26 l.705-707 |
| EG-BP-E25 | Best Practice | Node extensions only at the lowest level, not where an ICH sub-heading exists, and kept for the whole lifecycle. | EG-DRAFT | SPEC p.9 l.106-132 |
| EG-BP-E26 | Best Practice | m1-additional-data is used only for information not covered by any EG M1 section and never for documents submitted before. | EG-DRAFT | SPEC p.75 row 178; TG p.30 l.828-832; HPG p.45 l.1467-1476 (TG p.29 l.790-792 sends supportive documents to 1.2 - decision D-19) |
| EG-BP-E27 | Best Practice | Submission unit 'corrigendum' only after case-by-case agreement with EDA. | EG-DRAFT | TG p.10 l.212-214; TG p.73 |
| EG-BP-E28 | Best Practice | No files in m1/eg/util (EG DTD files are in util/dtd). | ASSUMPTION | SPEC p.76 rows 180-181; decision D-10 |
| EG-BP-E29 | Best Practice | Files already submitted in an earlier sequence are not submitted again; refer to them instead. | EG-DRAFT | SPEC p.8 l.68-71; SPEC p.75 row 178 |
| EG-BP-E30 | Best Practice | Several related sequences of different categories: the envelope uses the highest category; if any related activity was grouped, mode 'grouping'. | EG-DRAFT | SPEC p.21 l.260-262; TG p.17 l.429-430 |

## Kept EU rules

EG-PF-1.1, EG-PF-1.2, EG-PF-1.3, EG-PF-1.4, EG-PF-1.5, EG-PF-2.1, EG-PF-2.2, EG-PF-2.3, EG-PF-7.1, EG-PF-7.2, EG-PF-7.3, EG-PF-7.4, EG-PF-7.5, EG-PF-7.6, EG-PF-8.1, EG-PF-8.2, EG-PF-8.3, EG-PF-10.1, EG-PF-11.1, EG-PF-11.2, EG-PF-11.3, EG-PF-11.4, EG-PF-11.5, EG-PF-11.6, EG-PF-11.7, EG-PF-11.8, EG-PF-11.11, EG-PF-11.12, EG-BP-11.BP2, EG-BP-11.BP3, EG-PF-12.1, EG-PF-13.1, EG-BP-14.BP6, EG-PF-15.3, EG-PF-15.4, EG-PF-15.5, EG-PF-15.6, EG-PF-15.7, EG-PF-15.8, EG-PF-15.9, EG-PF-15.10, EG-BP-15.BP1, EG-BP-15.BP6, EG-PF-16.1, EG-PF-16.2, EG-PF-16.5, EG-BP-16.BP2, EG-BP-16.BP3, EG-BP-16.BP4, EG-BP-16.BP6, EG-BP-16.BP7, EG-BP-16.BP8, EG-BP-16.BP9, EG-BP-16.BP10 - text unchanged from EU VC 8.2 (see CSV).

## Notes for a validator author

* Rules on checksums of the EG util files (EG-PF-3.3, 4.3, 5.3, 6.3) cannot pass/fail until EDA publishes the files: report a warning.
* Everything the DTD enforces (vocabularies, agency code, envelope order, m1-eg tree, 1.6 choice, 1.2 parents without leaves) is caught by EG-PF-9.4;
  the separate EG-PF-E rules exist so that a failure message names the EG rule.
* Lifecycle rules (`lifecycle_needed = Y`, and EG-PF-9.8, 13.2, EG-BP-E09/E10) need the earlier sequences of the same UUID.
* Rules tagged ASSUMPTION must stay warnings/information only in production until EDA confirms them.
