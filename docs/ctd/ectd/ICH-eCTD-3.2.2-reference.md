# KB_ICH — ICH eCTD v3.2.2 knowledge base (implementation reference)

**Sources used (only these):**

| Key | File | What it is |
|---|---|---|
| **SPEC** | `ich_ectd_322.pdf` / `ich.txt` | ICH eCTD Specification v3.2.2, 16-July-2008. Page numbers are the printed ones ("p. 6-3" = Appendix 6, page 3). |
| **DTD** | `ich_dtd.zip` → `ich_dtd/ich-ectd-3-2.dtd` | ICH eCTD DTD v3.2 (Nov 21, 2003), 773 lines. Its element list matches SPEC Appendix 8 exactly (165 `<!ELEMENT>` declarations in both). MD5 of the supplied file, computed here: `1d6f631cc6b6357f0f4fe378e5f79a27`. The *ICH-published* checksum Q&A 36 item 2 tells you to compare against is **not** in these files. |
| **FMT** | `ich_formats.pdf` | ICH M8 "Specification for Submission Formats for eCTD" v1.3, 2 June 2021. Section numbers are given as §2.x; the extracted text drops the heading numbers, so they come from the TOC order (2.1 Restrictions … 2.18 Plug-ins). §2.1, 2.3, 2.15 and 2.17 are confirmed by references inside the text. |
| **QA** | `ich_qa.zip` → `ICH_eCTDv3.2_QA_V1.33_2024_0521.xlsx` | eCTD IWG Q&A and Change Request document v1.33, May 2024. Sheets: "Q&A" (current), "Q&A No. 36" (the validation checklist), "Retired Q&A", "Change Requests". |

**Precedence (QA 82):** FMT *replaces* SPEC Appendix 7; the region sets the date it takes effect. Where FMT and Appendix 7 differ, both are shown below.

---

## 1. Submission folder structure

### 1.1 Top level and sequence folder

| Rule | Value | Source |
|---|---|---|
| Top-level folder | Set by the region. It identifies the application uniquely in that region. The original and every later amendment/variation use the **same** top-level folder name. Example: `ctd-123456` | SPEC App 6 p. 6-1; Table 6-1 |
| Sequence folder | One subfolder per submission, named by its **sequence number**: `0000` original, `0001`, `0002`, … `nnnn` | SPEC p. 6-1, Table 6-1 |
| Sequence number format | **4 digits** (0000–9999) | QA 36 item 18 |
| Uniqueness | Unique within the whole application (all regions) | SPEC p. 6-1; Retired QA 33 |
| Consecutive? | **Required** in Japan; preferred but not required elsewhere | SPEC p. 6-1; Retired QA 33 |
| Sequence folder contents | At least two files (the instance `index.xml` and its MD5 file `index-md5.txt`) and one or more directories | SPEC App 2 p. 2-1 |
| Folder name vs regional XML | The sequence folder name must match the sequence number in `xx-regional.xml` (not applicable in Japan) | QA 36 item 19 |
| Empty eCTD folder template | The ICH site has one with every Module 2–5 folder from Appendix 4. You add the regional m1 folders, util folders and XML. | SPEC p. 2-1; Retired QA 13 |
| Empty folders | **Should not be submitted** | QA 54. SPEC p. 3-2: "Empty directories can be omitted"; if content was expected, justify why it is missing (regional guidance) |
| Extra sub-folders | Allowed (an extra level to help build the submission). Tell the authority according to regional guidance. | Retired QA 17; SPEC p. 3-1 + footnote 1 |
| Global multi-region eCTD | "This is not advised" (one eCTD for several regions where each region ignores the others' material) | SPEC p. 1-2; Retired QA 29 |
| Reasonable entries per directory | "There should be a reasonable maximum number of entries (directories and files) per directory". **No number is given.** | SPEC p. 2-1 |

### 1.2 Files and folders inside a sequence (SPEC Table 6-2, p. 6-2; App 4 rows 1–7, 370–379)

```
ctd-123456/                      <- top-level (regional rule)
  0000/                          <- sequence (4 digits)
    index.xml                    <- ICH backbone (App 4 row 1)
    index-md5.txt                <- MD5 of index.xml (row 2)
    m1/                          <- row 3; only ONE regional sub-dir is needed
      us/  (or eu/, jp/, xx/)    <- rows 4-7; xx = ISO-3166-1 two-character country code
        us-regional.xml          <- regional backbone, referenced by a leaf in index.xml
    m2/ m3/ m4/ m5/              <- App 4 rows 8-369
    util/                        <- row 370 "utilities"
      dtd/                       <- row 371
        ich-ectd-3-2.dtd         <- row 372 "ich-ectd-n.dtd": the DTD version USED to build the sequence MUST be included
        us-regional-n.dtd        <- rows 373-376 (eu-regional-n.dtd, jp-regional-n.xsd, us-regional-n.dtd, xx-regional-n.dtd)
      style/                     <- row 377 ICH + regional stylesheets
        ectd-n.xsl               <- row 378 the ICH stylesheet version used as a reference
        xx-regional-n.xsl        <- row 379
```

| Rule | Source |
|---|---|
| `index.xml` is one file in the sequence folder; there is an index.xml in **each** sequence folder (0000, 0001, 0002 …) | SPEC p. 6-2 |
| `index-md5.txt` sits in each folder next to its index.xml | SPEC p. 6-2; p. 5-2 |
| The DTD for index.xml is in `util` for **each** submission; the regional DTD is there too | SPEC p. 6-2 |
| Regional DTDs/schemas: only the one for the target region is needed. Names in rows 372–379 are **illustrative**; regional guidance gives the current names and versions | App 4 row 371 (p. 4-64) |
| `util/dtd` and `util/style` may hold only the ICH and regional files that support structure, validation and viewing (DTDs, regional `.mod` files, `valid-values.xml`, stylesheets). Nothing else. Files for other regions are allowed and do not break validation. | QA 51 |
| Stylesheets: include the approved ICH and regional ones; applicants **should not** submit their own | QA 50 (it replaces Retired QA 30 "consult regional guidance"); SPEC p. 1-1 |
| A separate MD5 file for the regional XML (`xx-regional-md5.txt`) is **not needed**: index.xml carries its checksum | SPEC p. 5-2, p. 6-2; Retired QA 31 |
| No unreferenced files in m1–m5 (subfolders other than `util`) | QA 36 item 13 |
| Every lowest-level heading element in the submission has at least one leaf | QA 36 item 16 |
| Module folders are named `m1`, `m2`, `m3`, `m4`, `m5` | SPEC App 3 pp. 3-2…3-9 |

### 1.3 Folder names per module (SPEC Appendix 3, Tables 3-2…3-5): recommended; "can be further reduced or omitted to minimize path length issues"

The complete list (folders **and** file names) is the Appendix 4 table in §1.4. Appendix 3 has the same folder names, except for one typo: Table 3-3 prints `32s42- analyt-proc` with a space, while Appendix 4 row 57 prints `32s42-analyt-proc`. Use the Appendix 4 form, because a space is not an allowed character (SPEC p. 2-3).

### 1.4 COMPLETE Appendix 4 table: file organization (Table 4-1, SPEC pp. 4-2 … 4-65)

Read before use (SPEC p. 4-1):
* Row numbers are "sequentially assigned … can change with each version of this appendix".
* "The file and folder names shown within modules 2-5 are **not mandatory, but recommended**, and can be further reduced or omitted to avoid path length issues." (Also SPEC p. 3-1; Retired QA 15: "Filenames in the eCTD are optional. The ones provided are highly recommended.")
* "Where file and folder names are presented in *italics* applicants would substitute these with appropriate file names in accordance with their own naming conventions." Here the italic parts are marked **†**. They were detected from the PDF's italic font: `substance-1-manufacturer-1`, `product-1`, `excipient-1`, `excip-name-1/-2`, `indication-1`, `study-report-n`, `study-n`, `filename-n`, `reference-n`, `analytical-procedure-n`, `validation-analyt-procedure-n`, `validation-analytical-procedures-n`, `facilities-and-equipment-report-n`, `adventitious-agents-report-n`, the "name" in `drug-product-name.pdf`, the "indication" in `summary-clin-efficacy-indication.pdf`. (`m1/xx` and the `-n` version suffixes in rows 372–379 are printed in roman type but are placeholders too, per their comments.)
* The `.pdf` extension "is only illustrative" (it follows the file type). Granularity (one file or several) follows the M4 Organisation Granularity Annex. "Where there is no definition … applicants are free to construct the dossier as they see fit".
* D = Directory, F = File. Rows 12/13 and 77/78 sit in one merged cell in the PDF; they are split here to match the printed text.
* In Module 5 the `study-report-n` rows are **directories** ("A directory should be created for each study", row 276 comment).


| # | CTD § | Title (Appendix 4, verbatim) | Element in backbone | D/F | Relative path (verbatim; † = contains an *italic* placeholder the applicant substitutes) | p. | Comment (verbatim, condensed only by "see #n" for repeats) |
|---|---|---|---|---|---|---|---|
| 1 |  |  |  | F | `index.xml` | 4-2 | This is the Backbone |
| 2 |  |  |  | F | `index-md5.txt` | 4-2 | The MD5 of the Backbone |
| 3 | 1 | Administrative Information and Prescribing Information | `m1-administrative-information-and-prescribing-information` | D | `m1` | 4-3 | Only one of the regional directories is needed |
| 4 |  |  |  | D | `m1/eu` | 4-3 | EU directory: In addition to the appropriate regional documents, the regional xml instance should be located in this folder. Referto regional guidance for details |
| 5 |  |  |  | D | `m1/jp` | 4-3 | Japan directory: In addition to the appropriate regional documents, the regional xml instance should be located in this folder. Refer to regional guidance for details |
| 6 |  |  |  | D | `m1/us` | 4-3 | US directory: In addition to the appropriate regional documents, the regional xml instance should be located in this folder. Refer to regional guidance for details |
| 7 |  |  |  | D | `m1/xx` | 4-3 | xx directory; where xx is a two character country code from ISO-3166-1. In addition to the appropriate regional documents, the regional xml instance should be located in this folder. Refer to regional guidance for details |
| 8 | 2 | Common Technical Document Summaries | `m2-common-technical-document-summaries` | D | `m2` | 4-4 |  |
| 9 | 2.2 | Introduction | `m2-2-introduction` | D | `m2/22-intro` | 4-4 |  |
| 10 | 2.2 | Introduction | `m2-2-introduction` | F | `m2/22-intro/introduction.pdf` | 4-4 |  |
| 11 | 2.3 | Quality Overall Summary | `m2-3-quality-overall-summary` | D | `m2/23-qos` | 4-4 | Refer to the Granularity Annex of the M4 Organisation Document for guidance on the flexibility of multiple documents for the Quality Overall Summary |
| 12 | 2.3 | Introduction | `m2-3-introduction` | F | `m2/23-qos/introduction.pdf` | 4-4 |  |
| 13 | 2.3.S | Drug Substance - Name - Manufacturer | `m2-3-s-drug-substance` | F | `m2/23-qos/drug-substance.pdf` | 4-4 | Refer to the Granularity Annex of the M4 Organisation Document for guidance on the flexibility of multiple documents for the Quality Overall Summary Where there are more than one drug substance and/or manufacturer, separate files can be provided for each. |
| 14 | 2.3.P | Drug Product -Name | `m2-3-p-drug-product` | F | `m2/23-qos/drug-product-name.pdf` † | 4-5 | Refer to the Granularity Annex of the M4 Organisation Document for guidance on the flexibility of multiple documents for the Quality Overall Summary Refer to regional guidance for definition of what constitutes a drug product and the acceptability of more than one drug product in an application. Where more than one drug product is acceptable in an application, a separate file can be provided for each drug product. |
| 15 | 2.3.A | Appendices | `m2-3-a-appendices` | F | `m2/23-qos/appendices.pdf` | 4-5 | see #11 |
| 16 | 2.3.R | Regional Information | `m2-3-r-regional-information` | F | `m2/23-qos/regional-information.pdf` | 4-5 | see #11 |
| 17 | 2.4 | Nonclinical Overview | `m2-4-nonclinical-overview` | D | `m2/24-nonclin-over` | 4-5 |  |
| 18 | 2.4 | Nonclinical Overview | `m2-4-nonclinical-overview` | F | `m2/24-nonclin-over/nonclinical-overview.pdf` | 4-5 | Typically, this document should consist of a single file. The CTD defines further heading levels and navigation should be provided within the document to these sub-headings. |
| 19 | 2.5 | Clinical Overview | `m2-5-clinical-overview` | D | `m2/25-clin-over` | 4-6 |  |
| 20 | 2.5 | Clinical Overview | `m2-5-clinical-overview` | F | `m2/25-clin-over/clinical-overview.pdf` | 4-6 | see #18 |
| 21 | 2.6 | Nonclinical Written and Tabulated Summaries | `m2-6-nonclinical-written-and-tabulated-summaries` | D | `m2/26-nonclin-sum` | 4-6 |  |
| 22 | 2.6.1 | Introduction | `m2-6-1-introduction` | F | `m2/26-nonclin-sum/introduction.pdf` | 4-6 |  |
| 23 | 2.6.2 | Pharmacology Written Summary | `m2-6-2-pharmacology-written-summary` | F | `m2/26-nonclin-sum/pharmacol-written-summary.pdf` | 4-6 | see #18 |
| 24 | 2.6.3 | Pharmacology Tabulated Summary | `m2-6-3-pharmacology-tabulated-summary` | F | `m2/26-nonclin-sum/pharmacol-tabulated-summary.pdf` | 4-6 | Should have further navigation via bookmarks |
| 25 | 2.6.4 | Pharmacokinetics Written Summary | `m2-6-4-pharmacokinetics-written-summary` | F | `m2/26-nonclin-sum/pharmkin-written-summary.pdf` | 4-6 | see #18 |
| 26 | 2.6.5 | Pharmacokinetics Tabulated Summary | `m2-6-5-pharmacokinetics-tabulated-summary` | F | `m2/26-nonclin-sum/pharmkin-tabulated-summary.pdf` | 4-7 | see #24 |
| 27 | 2.6.6 | Toxicology Written Summary | `m2-6-6-toxicology-written-summary` | F | `m2/26-nonclin-sum/toxicology-written-summary.pdf` | 4-7 | see #18 |
| 28 | 2.6.7 | Toxicology Tabulated Summary | `m2-6-7-toxicology-tabulated-summary` | F | `m2/26-nonclin-sum/toxicology-tabulated-summary.pdf` | 4-7 | see #24 |
| 29 | 2.7 | Clinical Summary | `m2-7-clinical-summary` | D | `m2/27-clin-sum` | 4-7 |  |
| 30 | 2.7.1 | Summary of Biopharmaceutic Studies and Associated Analytical Methods | `m2-7-1-summary-of-biopharmaceutic-studies-and-associated-analytical-methods` | F | `m2/27-clin-sum/summary-biopharm.pdf` | 4-7 | see #18 |
| 31 | 2.7.2 | Summary of Clinical Pharmacology Studies | `m2-7-2-summary-of-clinical-pharmacology-studies` | F | `m2/27-clin-sum/summary-clin-pharm.pdf` | 4-7 | see #18 |
| 32 | 2.7.3 | Summary of Clinical Efficacy – Indication | `m2-7-3-summary-of-clinical-efficacy` | F | `m2/27-clin-sum/summary-clin-efficacy-indication.pdf` † | 4-8 | The file name should always include the indication being claimed (abbreviated if appropriate) e.g., 'summary-clin-efficacy-asthma.pdf'. Where there is more than one indication (e.g., asthma & migraine) then the first indication has a file name 'summary-clin-efficacy- asthma.pdf' and the second 'summary-clin-efficacy-migraine.pdf'. Typically, this document should consist of a single file. The CTD defines further heading levels and navigation should be provided within the document to these sub-headings. The ‘indication’ attribute in the backbone should be consistent with that used in the filename but can be different. For example, an ‘indication’ attribute value of ‘Non-Small Cell Lung Cancer’ could be expressed as ‘NSCLC’ in the filename for that document (i.e., summclineff-nsclc.pdf). There is currently no standard terminology list for ‘indication’ and applicants should choose these attributes carefully as they can not be easily changed during the life cycle of the application. The only way this can be accomplished currently is to delete all the leaf elements with the incorrect attribute value and provide new leaf elements for those files with the modified attribute value. Applicants should consult with the regional authority before attempting to modify these attributes to discuss the appropriateness of, and approach to be taken for, this type of change. |
| 33 | 2.7.4 | Summary of Clinical Safety | `m2-7-4-summary-of-clinical-safety` | F | `m2/27-clin-sum/summary-clin-safety.pdf` | 4-8 | see #18 |
| 34 | 2.7.5 | Literature References | `m2-7-5-literature-references` | F | `m2/27-clin-sum/literature-references.pdf` | 4-8 |  |
| 35 | 2.7.6 | Synopses of Individual Studies | `m2-7-6-synopses-of-individual-studies` | F | `m2/27-clin-sum/synopses-indiv-studies.pdf` | 4-8 | These synopses should already be located in the Clinical Study Reports in Module 5 and should not, therefore, be repeated in Module 2. It is considered sufficient to provide hyperlinks from the listing of the studies, located here, to the locations of the synopses in Module 5. |
| 36 | 3 | Quality | `m3-quality` | D | `m3` | 4-10 | Refer to the Granularity Annex of the M4 Organisation Document for guidance on the flexibility of multiple documents for Module 3 |
| 37 | 3.2 | Body of Data | `m3-2-body-of-data` | D | `m3/32-body-data` | 4-10 |  |
| 38 | 3.2.S | Drug Substance | `m3-2-s-drug-substance` | D | `m3/32-body-data/32s-drug-sub` | 4-10 |  |
| 39 | 3.2.S | Drug Substance - Drug Substance Name - Manufacturer | `m3-2-s-drug-substance` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1` † | 4-10 | In this section, it can be helpful if the folder name includes the name of the drug substanceand manufacturer. This applies particularly when there are multiple drug substances and/or manufacturers. When naming folders, attention should be paid to the length of the name of the folder on the overall length of the full path. Abbreviations can help control the length of the path. The ‘substance’ and ‘manufacturer’ attribute values in the backbone should be consistent with that used in the folder name but can be different. For example, a ‘manufacturer’ attribute value of ‘Company XXX, City Name, Country Name’ could be expressed as ‘xxx’ in the folder name. There is currently no standard terminology list for these attributes and applicants should choose these attributes carefully as they can not be easily changed during the life cycle of the application. The only way this can be accomplished currently is to delete all the leaf elements with the incorrect attribute value and provide new leaf elements for those files with the modified attribute value. Applicants should consult with the regional authority before attempting to modify these attributes to discuss the appropriateness of, and approach to be taken for, this type of change. |
| 40 | 3.2.S.1 | General Information (name, manufacturer) | `m3-2-s-1-general-information` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s1-gen-info` † | 4-10 |  |
| 41 | 3.2.S.1.1 | Nomenclature (name, manufacturer) | `m3-2-s-1-1-nomenclature` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s1-gen-info/nomenclature.pdf` † | 4-11 |  |
| 42 | 3.2.S.1.2 | Structure (name, manufacturer) | `m3-2-s-1-2-structure` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s1-gen-info/structure.pdf` † | 4-11 |  |
| 43 | 3.2.S.1.3 | General Properties (name, manufacturer) | `m3-2-s-1-3-general-properties` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s1-gen-info/general-properties.pdf` † | 4-11 |  |
| 44 | 3.2.S.2 | Manufacture (name, manufacturer) | `m3-2-s-2-manufacture` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf` † | 4-11 |  |
| 45 | 3.2.S.2.1 | Manufacturer(s) (name, manufacturer) | `m3-2-s-2-1-manufacturer` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/manufacturer.pdf` † | 4-11 | For this document there should be only information regarding one manufacturer |
| 46 | 3.2.S.2.2 | Description of Manufacturing Process and Process Controls (name, manufacturer) | `m3-2-s-2-2-description-of-manufacturing-process-and-process-controls` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/manuf-process-and-controls.pdf` † | 4-11 |  |
| 47 | 3.2.S.2.3 | Control of Materials (name, manufacturer) | `m3-2-s-2-3-control-of-materials` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/control-of-materials.pdf` † | 4-12 |  |
| 48 | 3.2.S.2.4 | Controls of Critical Steps and Intermediates (name, manufacturer) | `m3-2-s-2-4-controls-of-critical-steps-and-intermediates` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/control-critical-steps.pdf` † | 4-12 |  |
| 49 | 3.2.S.2.5 | Process Validation and/or Evaluation (name, manufacturer) | `m3-2-s-2-5-process-validation-and-or-evaluation` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/process-validation.pdf` † | 4-12 |  |
| 50 | 3.2.S.2.6 | Manufacturing Process Development (name, manufacturer) | `m3-2-s-2-6-manufacturing-process-development` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s2-manuf/manuf-process-development.pdf` † | 4-12 |  |
| 51 | 3.2.S.3 | Characterisation (name, manufacturer) | `m3-2-s-3-characterisation` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s3-charac` † | 4-12 |  |
| 52 | 3.2.S.3.1 | Elucidation of Structure and Other Characteristics (name, manufacturer) | `m3-2-s-3-1-elucidation-of-structure-and-other-characteristics` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s3-charac/elucidation-of-structure.pdf` † | 4-12 |  |
| 53 | 3.2.S.3.2 | Impurities (name, manufacturer) | `m3-2-s-3-2-impurities` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s3-charac/impurities.pdf` † | 4-12 |  |
| 54 | 3.2.S.4 | Control of Drug Substance (name, manufacturer) | `m3-2-s-4-control-of-drug-substance` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub` † | 4-13 |  |
| 55 | 3.2.S.4.1 | Specification (name, manufacturer) | `m3-2-s-4-1-specification` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s41-spec` † | 4-13 |  |
| 56 | 3.2.S.4.1 | Specification (name, manufacturer) | `m3-2-s-4-1-specification` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s41-spec/specification.pdf` † | 4-13 |  |
| 57 | 3.2.S.4.2 | Analytical Procedures (name, manufacturer) | `m3-2-s-4-2-analytical-procedures` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s42-analyt-proc` † | 4-13 | The example below shows how a multiple file approach, where a separate file is provided for each analytical procedure, can be organized. CTD numbering is not defined below this level (e.g., 3.2.S.4.2.1). |
| 58 |  | Analytical Procedure-1 | `m3-2-s-4-2-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s42-analyt-proc/analytical-procedure-1.pdf` † | 4-13 |  |
| 59 |  | Analytical Procedure-2 | `m3-2-s-4-2-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s42-analyt-proc/analytical-procedure-2.pdf` † | 4-13 |  |
| 60 |  | Analytical Procedure-3 | `m3-2-s-4-2-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s42-analyt-proc/analytical-procedure-3.pdf` † | 4-14 |  |
| 61 | 3.2.S.4.3 | Validation of Analytical Procedures (name, manufacturer) | `m3-2-s-4-3-validation-of-analytical-procedures` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s43-val-analyt-proc` † | 4-14 | The example below shows how a multiple file approach, where a separate file is provided for each analytical procedure, can be organized. CTD numbering is not defined below this level (e.g., 3.2.S.4.3.1). |
| 62 |  | Validation of Analytical Procedure-1 | `m3-2-s-4-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s43-val-analyt-proc/validation-analyt-procedure-1.pdf` † | 4-14 |  |
| 63 |  | Validation of Analytical Procedure-2 | `m3-2-s-4-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s43-val-analyt-proc/validation-analyt-procedure-2.pdf` † | 4-14 |  |
| 64 |  | Validation of Analytical Procedure-3 | `m3-2-s-4-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s43-val-analyt-proc/validation-analyt-procedure-3.pdf` † | 4-14 |  |
| 65 | 3.2.S.4.4 | Batch Analyses (name, manufacturer) | `m3-2-s-4-4-batch-analyses` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s44-batch-analys` † | 4-14 |  |
| 66 | 3.2.S.4.4 | Batch Analyses (name, manufacturer) | `m3-2-s-4-4-batch-analyses` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s44-batch-analys/batch-analyses.pdf` † | 4-14 |  |
| 67 | 3.2.S.4.5 | Justification of Specification (name, manufacturer) | `m3-2-s-4-5-justification-of-specification` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s45-justif-spec` † | 4-15 |  |
| 68 | 3.2.S.4.5 | Justification of Specification (name, manufacturer) | `m3-2-s-4-5-justification-of-specification` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s4-contr-drug-sub/32s45-justif-spec/justification-of-specification.pdf` † | 4-15 |  |
| 69 | 3.2.S.5 | Reference Standards or Materials (name, manufacturer) | `m3-2-s-5-reference-standards-or-materials` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s5-ref-stand` † | 4-15 |  |
| 70 | 3.2.S.5 | Reference Standards or Materials (name, manufacturer) | `m3-2-s-5-reference-standards-or-materials` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s5-ref-stand/reference-standards.pdf` † | 4-15 | Where a multiple file approach is taken for this section, the file names should indicate which reference standard is covered in the document. |
| 71 | 3.2.S.6 | Container Closure System (name, manufacturer) | `m3-2-s-6-container-closure-system` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s6-cont-closure-sys` † | 4-15 |  |
| 72 | 3.2.S.6 | Container Closure System (name, manufacturer) | `m3-2-s-6-container-closure-system` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s6-cont-closure-sys/container-closure-system.pdf` † | 4-15 |  |
| 73 | 3.2.S.7 | Stability (name, manufacturer) | `m3-2-s-7-stability` | D | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s7-stab` † | 4-16 |  |
| 74 | 3.2.S.7.1 | Stability Summary and Conclusions (name, manufacturer) | `m3-2-s-7-1-stability-summary-and-conclusions` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s7-stab/stability-summary.pdf` † | 4-16 |  |
| 75 | 3.2.S.7.2 | Post-approval Stability Protocol and Stability Commitment (name, manufacturer) | `m3-2-s-7-2-post-approval-stability-protocol-and-stability-commitment` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s7-stab/postapproval-stability.pdf` † | 4-16 |  |
| 76 | 3.2.S.7.3 | Stability Data (name, manufacturer) | `m3-2-s-7-3-stability-data` | F | `m3/32-body-data/32s-drug-sub/substance-1-manufacturer-1/32s7-stab/stability-data.pdf` † | 4-16 |  |
| 77 | 3.2.P | Drug Product (name, dosage form) | `m3-2-p-drug-product` | D | `m3/32-body-data/32p-drug-prod` | 4-16 |  |
| 78 | 3.2.P | Drug Product (name, dosage form) – Name | `m3-2-p-drug-product` | D | `m3/32-body-data/32p-drug-prod/product-1` † | 4-16 | In this section, it can be helpful if the folder name includes the name of the drug product. This applies particularly where there is more than one drug product (e.g., powder for reconstitution and diluent); the first drug product would have a folder 'powder-for-reconstitution' and the second, 'diluent'. Refer to regional guidance for definition of what constitutes a drug product and the acceptability of more than one drug product in an application. The ‘product-name’ attribute value in the backbone should be consistent with that used in the folder name but can be different. For example, a ‘product-name’ attribute value of ‘Lyophilized Powder for Reconstitution’ could be expressed as ‘powder’ in the folder name. There is currently no standard terminology list for these attributes and applicants should choose these attributes carefully as they can not be easily changed during the life cycle of the application. The only way this can be accomplished currently is to delete all the leaf elements with the incorrect attribute value and provide new leaf elements for those files with the modified attribute value. Applicants should consult with the regional authority before attempting to modify these attributes to discuss the appropriateness of, and approach to be taken for, this type of change. |
| 79 | 3.2.P.1 | Description and Composition of the Drug Product (name, dosage form) | `m3-2-p-1-description-and-composition-of-the-drug-product` | D | `m3/32-body-data/32p-drug-prod/product-1/32p1-desc-comp` † | 4-17 |  |
| 80 | 3.2.P.1 | Description and Composition of the Drug Product (name, dosage form) | `m3-2-p-1-description-and-composition-of-the-drug-product` | F | `m3/32-body-data/32p-drug-prod/product-1/32p1-desc-comp/description-and-composition.pdf` † | 4-17 |  |
| 81 | 3.2.P.2 | Pharmaceutical Development (name, dosage form) | `m3-2-p-2-pharmaceutical-development` | D | `m3/32-body-data/32p-drug-prod/product-1/32p2-pharm-dev` † | 4-17 | Refer to the M4 Organisation Document: Granularity Annex for guidance on the flexibility of multiple documents for the Pharmaceutical Development section. |
| 82 | 3.2.P.2 | Pharmaceutical Development (name, dosage form) | `m3-2-p-2-pharmaceutical-development` | F | `m3/32-body-data/32p-drug-prod/product-1/32p2-pharm-dev/pharmaceutical-development.pdf` † | 4-17 | see #81 |
| 83 | 3.2.P.3 | Manufacture (name, dosage form) | `m3-2-p-3-manufacture` | D | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf` † | 4-18 |  |
| 84 | 3.2.P.3.1 | Manufacturer(s) (name, dosage form) | `m3-2-p-3-1-manufacturers` | F | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf/manufacturers.pdf` † | 4-18 |  |
| 85 | 3.2.P.3.2 | Batch Formula (name, dosage form) | `m3-2-p-3-2-batch-formula` | F | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf/batch-formula.pdf` † | 4-18 |  |
| 86 | 3.2.P.3.3 | Description of Manufacturing Process and Process Controls (name, dosage form) | `m3-2-p-3-3-description-of-manufacturing-process-and-process-controls` | F | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf/manuf-process-and-controls.pdf` † | 4-18 |  |
| 87 | 3.2.P.3.4 | Controls of Critical Steps and Intermediates (name, dosage form) | `m3-2-p-3-4-controls-of-critical-steps-and-intermediates` | F | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf/control-critical-steps.pdf` † | 4-18 |  |
| 88 | 3.2.P.3.5 | Process Validation and/or Evaluation (name, dosage form) | `m3-2-p-3-5-process-validation-and-or-evaluation` | F | `m3/32-body-data/32p-drug-prod/product-1/32p3-manuf/process-validation.pdf` † | 4-18 | The applicant has the option to submit one or multiple files, one for each validation or evaluation. |
| 89 | 3.2.P.4 | Control of Excipients (name, dosage form) | `m3-2-p-4-control-of-excipients` | D | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip` † | 4-19 |  |
| 90 | 3.2.P.4 | Control of Excipients (name, dosage form) – Excipient | `m3-2-p-4-control-of-excipients` | D | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipient-1` † | 4-19 | For a drug product containing more than one excipient, the information requested for sections 3.2.P.4.1 – 3.2.P.4.4 should be provided in its entirety for each excipient. Refer to the ICH eCTD QA and Change Requests document, Q&A No.4 for additional suggestions on structuring this section. For compendial excipient(s) without additional specification tests, it is appropriate to have all information in one file, making sure to introduce a folder for each of new documents to avoid mixing files and folders at the same level. Non-compendial excipients should follow the structure outlined below. The ‘excipient’ attribute value in the backbone should be consistent with that used in the folder name but can be different. There is currently no standard terminology list for these attributes and applicants should choose these attributes carefully as they can not be easily changed during the life cycle of the application. The only way this can be accomplished currently is to delete all the leaf elements with the incorrect attribute value and provide new leaf elements for those files with the modified attribute value. Applicants should consult with the regional authority before attempting to modify these attributes to discuss the appropriateness of, and approach to be taken for, this type of change. |
| 91 | 3.2.P.4.1 | Specifications (name, dosage form) | `m3-2-p-4-1-specifications` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipient-1/specifications.pdf` † | 4-19 | See comment under 3.2.P.4. |
| 92 | 3.2.P.4.2 | Analytical Procedures (name, dosage form) | `m3-2-p-4-2-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipient-1/analytical-procedures.pdf` † | 4-19 | see #91 |
| 93 | 3.2.P.4.3 | Validation of Analytical Procedures (name, dosage form) | `m3-2-p-4-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipient-1/validation-analyt-procedures.pdf` † | 4-19 | see #91 |
| 94 | 3.2.P.4.4 | Justification of Specifications (name, dosage form) | `m3-2-p-4-4-justification-of-specifications` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipient-1/justification-of-specifications.pdf` † | 4-20 | see #91 |
| 95 | 3.2.P.4.5 | Excipients of Human or Animal Origin (name, dosage form) | `m3-2-p-4-5-excipients-of-human-or-animal-origin` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/excipients-human-animal.pdf` † | 4-20 |  |
| 96 | 3.2.P.4.6 | Novel Excipients (name, dosage form) | `m3-2-p-4-6-novel-excipients` | F | `m3/32-body-data/32p-drug-prod/product-1/32p4-contr-excip/novel-excipients.pdf` † | 4-20 |  |
| 97 | 3.2.P.5 | Control of Drug Product (name, dosage form) | `m3-2-p-5-control-of-drug-product` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod` † | 4-20 |  |
| 98 | 3.2.P.5.1 | Specification(s) (name, dosage form) | `m3-2-p-5-1-specifications` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p51-spec` † | 4-20 |  |
| 99 | 3.2.P.5.1 | Specification(s) (name, dosage form) | `m3-2-p-5-1-specifications` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p51-spec/specifications.pdf` † | 4-20 |  |
| 100 | 3.2.P.5.2 | Analytical Procedures (name, dosage form) | `m3-2-p-5-2-analytical-procedures` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p52-analyt-proc` † | 4-20 | The example below shows how a multiple file approach, where a separate file is provided for each analytical procedure, may be organized. CTD numbering is not defined below this level (e.g., 3.2.P.5.2.1). |
| 101 |  | Analytical Procedure – 1 | `m3-2-p-5-2-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p52-analyt-proc/analytical-procedure-1.pdf` † | 4-21 |  |
| 102 |  | Analytical Procedure – 2 | `m3-2-p-5-2-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p52-analyt-proc/analytical-procedure-2.pdf` † | 4-21 |  |
| 103 |  | Analytical Procedure – 3 | `m3-2-p-5-2-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p52-analyt-proc/analytical-procedure-3.pdf` † | 4-21 |  |
| 104 | 3.2.P.5.3 | Validation of Analytical Procedures (name, dosage form) | `m3-2-p-5-3-validation-of-analytical-procedures` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p53-val-analyt-proc` † | 4-21 | The example below shows how a multiple file approach, where a separate file is provided for each analytical procedure, may be organized. CTD numbering is not defined below this level (e.g., 3.2.P.5.3.1). |
| 105 |  | Validation of Analytical Procedures – 1 | `m3-2-p-5-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p53-val-analyt-proc/validation-analytical-procedures-1.pdf` † | 4-21 |  |
| 106 |  | Validation of Analytical Procedures – 2 | `m3-2-p-5-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p53-val-analyt-proc/validation-analytical-procedures-2.pdf` † | 4-21 |  |
| 107 |  | Validation of Analytical Procedures – 3 | `m3-2-p-5-3-validation-of-analytical-procedures` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p53-val-analyt-proc/validation-analytical-procedures-3.pdf` † | 4-22 |  |
| 108 | 3.2.P.5.4 | Batch Analyses (name, dosage form) | `m3-2-p-5-4-batch-analyses` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p54-batch-analys` † | 4-22 |  |
| 109 | 3.2.P.5.4 | Batch Analyses (name, dosage form) | `m3-2-p-5-4-batch-analyses` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p54-batch-analys/batch-analyses.pdf` † | 4-22 |  |
| 110 | 3.2.P.5.5 | Characterisation of Impurities (name, dosage form) | `m3-2-p-5-5-characterisation-of-impurities` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p55-charac-imp` † | 4-22 |  |
| 111 | 3.2.P.5.5 | Characterisation of Impurities (name, dosage form) | `m3-2-p-5-5-characterisation-of-impurities` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p55-charac-imp/characterisation-impurities.pdf` † | 4-22 |  |
| 112 | 3.2.P.5.6 | Justification of Specifications (name, dosage form) | `m3-2-p-5-6-justification-of-specifications` | D | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p56-justif-spec` † | 4-22 |  |
| 113 | 3.2.P.5.6 | Justification of Specifications (name, dosage form) | `m3-2-p-5-6-justification-of-specifications` | F | `m3/32-body-data/32p-drug-prod/product-1/32p5-contr-drug-prod/32p56-justif-spec/justification-of-specifications.pdf` † | 4-23 |  |
| 114 | 3.2.P.6 | Reference Standards or Materials (name, dosage form) | `m3-2-p-6-reference-standards-or-materials` | D | `m3/32-body-data/32p-drug-prod/product-1/32p6-ref-stand` † | 4-23 |  |
| 115 | 3.2.P.6 | Reference Standards or Materials (name, dosage form) | `m3-2-p-6-reference-standards-or-materials` | F | `m3/32-body-data/32p-drug-prod/product-1/32p6-ref-stand/reference-standards.pdf` † | 4-23 | When a multiple file approach is taken for this section, the file names should indicate which reference standard is covered in the document. |
| 116 | 3.2.P.7 | Container Closure System (name, dosage form) | `m3-2-p-7-container-closure-system` | D | `m3/32-body-data/32p-drug-prod/product-1/32p7-cont-closure-sys` † | 4-23 |  |
| 117 | 3.2.P.7 | Container Closure System (name, dosage form) | `m3-2-p-7-container-closure-system` | F | `m3/32-body-data/32p-drug-prod/product-1/32p7-cont-closure-sys/container-closure-system.pdf` † | 4-23 |  |
| 118 | 3.2.P.8 | Stability (name, dosage form) | `m3-2-p-8-stability` | D | `m3/32-body-data/32p-drug-prod/product-1/32p8-stab` † | 4-23 |  |
| 119 | 3.2.P.8.1 | Stability Summary and Conclusion (name, dosage form) | `m3-2-p-8-1-stability-summary-and-conclusion` | F | `m3/32-body-data/32p-drug-prod/product-1/32p8-stab/stability-summary.pdf` † | 4-23 |  |
| 120 | 3.2.P.8.2 | Post-approval Stability Protocol and Stability Commitment (name, dosage form) | `m3-2-p-8-2-post-approval-stability-protocol-and-stability-commitment` | F | `m3/32-body-data/32p-drug-prod/product-1/32p8-stab/postapproval-stability.pdf` † | 4-24 |  |
| 121 | 3.2.P.8.3 | Stability Data (name, dosage form) | `m3-2-p-8-3-stability-data` | F | `m3/32-body-data/32p-drug-prod/product-1/32p8-stab/stability-data.pdf` † | 4-24 |  |
| 122 | 3.2.A | Appendices | `m3-2-a-appendices` | D | `m3/32-body-data/32a-app` | 4-24 |  |
| 123 | 3.2.A.1 | Facilities and Equipment (name, manufacturer) | `m3-2-a-1-facilities-and-equipment` | D | `m3/32-body-data/32a-app/32a1-fac-equip` | 4-24 | Several reports are likely to be included in this appendix. The organisation is left to the applicant to define. However, where there is more than one manufacturer a folder should be created for each manufacturer and the identity of the manufacturer included in the directory name. CTD numbering is not defined below this level (e.g., 3.2.A.1.1). |
| 124 |  | Facilities and Equipment Report 1 | `m3-2-a-1-facilities-and-equipment` | F | `m3/32-body-data/32a-app/32a1-fac-equip/facilities-and-equipment-report-1.pdf` † | 4-24 |  |
| 125 |  | Facilities and Equipment Report 2 | `m3-2-a-1-facilities-and-equipment` | F | `m3/32-body-data/32a-app/32a1-fac-equip/facilities-and-equipment-report-2.pdf` † | 4-24 |  |
| 126 |  | Facilities and Equipment Report 3 | `m3-2-a-1-facilities-and-equipment` | F | `m3/32-body-data/32a-app/32a1-fac-equip/facilities-and-equipment-report-3.pdf` † | 4-25 |  |
| 127 | 3.2.A.2 | Adventitious Agents Safety Evaluation (name, dosage form, manufacturer) | `m3-2-a-2-adventitious-agents-safety-evaluation` | D | `m3/32-body-data/32a-app/32a2-advent-agent` | 4-25 | Nonviral adventitious agents reports should be placed in this folder. For viral adventitious agents the following sub-folder structure should be used. However, where there is more than one drug substance, drug product, manufacturer etc., a directory should be created for each option and its identity included in the directory name. CTD numbering is not defined below this level (e.g., 3.2.A.2.1). |
| 128 |  | Adventitious Agents Safety Evaluation Report 1 | `m3-2-a-2-adventitious-agents-safety-evaluation` | F | `m3/32-body-data/32a-app/32a2-advent-agent/adventitious-agents-report-1.pdf` † | 4-25 |  |
| 129 |  | Adventitious Agents Safety Evaluation Report 2 | `m3-2-a-2-adventitious-agents-safety-evaluation` | F | `m3/32-body-data/32a-app/32a2-advent-agent/adventitious-agents-report-2.pdf` † | 4-25 |  |
| 130 |  | Adventitious Agents Safety Evaluation Report 3 | `m3-2-a-2-adventitious-agents-safety-evaluation` | F | `m3/32-body-data/32a-app/32a2-advent-agent/adventitious-agents-report-3.pdf` † | 4-25 |  |
| 131 | 3.2.A.3 | Excipients – Name | `m3-2-a-3-excipients` | D | `m3/32-body-data/32a-app/32a3-excip-name-1` † | 4-25 | The name of any novel excipient should be included in the folder name. If there is more than one novel excipient then each folder should have unique identification through the use of different names e.g., '32a3-excip-name-1' and '32a3-excip-name-2'. The directory/file structure would typically follow that of the drug substance section in Module 3.2.S. Refer to regional guidances for the need for such information to be included in the submission directly as opposed to its inclusion in a Drug Master File. |
| 132 | 3.2.R | Regional Information | `m3-2-r-regional-information` | D | `m3/32-body-data/32r-reg-info` | 4-26 | Refer to the M4 Organisation Document: Granularity Annex for the approach to take with this section. |
| 133 | 3.3 | Literature References | `m3-3-literature-references` | D | `m3/33-lit-ref` | 4-26 | Copies of literature references should ordinarily be submitted as individual files (i.e., one for each reference).CTD numbering is not defined below this level (e.g., 3.3.1). |
| 134 |  | Reference 1 | `m3-3-literature-references` | F | `m3/33-lit-ref/reference-1.pdf` † | 4-26 |  |
| 135 |  | Reference 2 | `m3-3-literature-references` | F | `m3/33-lit-ref/reference-2.pdf` † | 4-26 |  |
| 136 |  | Reference 3 | `m3-3-literature-references` | F | `m3/33-lit-ref/reference-3.pdf` † | 4-26 |  |
| 137 | 4 | Nonclinical Study Reports | `m4-nonclinical-study-reports` | D | `m4` | 4-27 |  |
| 138 | 4.2 | Study Reports | `m4-2-study-reports` | D | `m4/42-stud-rep` | 4-27 |  |
| 139 | 4.2.1 | Pharmacology | `m4-2-1-pharmacology` | D | `m4/42-stud-rep/421-pharmacol` | 4-27 |  |
| 140 | 4.2.1.1 | Primary Pharmacodynamics | `m4-2-1-1-primary-pharmacodynamics` | D | `m4/42-stud-rep/421-pharmacol/4211-prim-pd` | 4-27 |  |
| 141 |  | Study Report 1 | `m4-2-1-1-primary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4211-prim-pd/study-report-1.pdf` † | 4-27 | This comment is applicable to all study reports in Module 4. A single file can be provided for each study report document in Module 4. However, where the study report is large (e.g., a carcinogenicity study) the applicant can choose to submit the report as more than one file. In this case the text portion of the report should be one file and the appendices can be one or more files. In choosing the level of granularity for these reports, the applicant should consider that, when relevant information is changed at any point in the product's life cycle, replacements of complete files should be provided. Where submission as a collection of multiple files is used it is recommended that a directory is created at the study report level and the relevant files included within the directory. It is possible to have the additional graphical file(s) inserted directly into the PDF file, thus making management of the file easier. Alternatively, the applicant can choose to manage graphical files independently. Individual studies and files do not have specific CTD numbers. |
| 142 |  | Study Report 2 | `m4-2-1-1-primary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4211-prim-pd/study-report-2.pdf` † | 4-28 |  |
| 143 |  | Study Report 3 | `m4-2-1-1-primary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4211-prim-pd/study-report-3.pdf` † | 4-28 |  |
| 144 | 4.2.1.2 | Secondary Pharmacodynamics | `m4-2-1-2-secondary-pharmacodynamics` | D | `m4/42-stud-rep/421-pharmacol/4212-sec-pd` | 4-28 |  |
| 145 |  | Study Report 1 | `m4-2-1-2-secondary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4212-sec-pd/study-report-1.pdf` † | 4-28 |  |
| 146 |  | Study Report 2 | `m4-2-1-2-secondary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4212-sec-pd/study-report-2.pdf` † | 4-28 |  |
| 147 |  | Study Report 3 | `m4-2-1-2-secondary-pharmacodynamics` | F | `m4/42-stud-rep/421-pharmacol/4212-sec-pd/study-report-3.pdf` † | 4-29 |  |
| 148 | 4.2.1.3 | Safety Pharmacology | `m4-2-1-3-safety-pharmacology` | D | `m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol` | 4-29 |  |
| 149 |  | Study Report 1 | `m4-2-1-3-safety-pharmacology` | F | `m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol/study-report-1.pdf` † | 4-29 |  |
| 150 |  | Study Report 2 | `m4-2-1-3-safety-pharmacology` | F | `m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol/study-report-2.pdf` † | 4-29 |  |
| 151 |  | Study Report 3 | `m4-2-1-3-safety-pharmacology` | F | `m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol/study-report-3.pdf` † | 4-29 |  |
| 152 | 4.2.1.4 | Pharmacodynamic Drug Interactions | `m4-2-1-4-pharmacodynamic-drug-interactions` | D | `m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact` | 4-29 |  |
| 153 |  | Study Report 1 | `m4-2-1-4-pharmacodynamic-drug-interactions` | F | `m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact/study-report-1.pdf` † | 4-30 |  |
| 154 |  | Study Report 2 | `m4-2-1-4-pharmacodynamic-drug-interactions` | F | `m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact/study-report-2.pdf` † | 4-30 |  |
| 155 |  | Study Report 3 | `m4-2-1-4-pharmacodynamic-drug-interactions` | F | `m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact/study-report-3.pdf` † | 4-30 |  |
| 156 | 4.2.2 | Pharmacokinetics | `m4-2-2-pharmacokinetics` | D | `m4/42-stud-rep/422-pk` | 4-30 |  |
| 157 | 4.2.2.1 | Analytical Methods and Validation Reports (if separate reports are available) | `m4-2-2-1-analytical-methods-and-validation-reports` | D | `m4/42-stud-rep/422-pk/4221-analyt-met-val` | 4-30 |  |
| 158 |  | Study Report 1 | `m4-2-2-1-analytical-methods-and-validation-reports` | F | `m4/42-stud-rep/422-pk/4221-analyt-met-val/study-report-1.pdf` † | 4-30 |  |
| 159 |  | Study Report 2 | `m4-2-2-1-analytical-methods-and-validation-reports` | F | `m4/42-stud-rep/422-pk/4221-analyt-met-val/study-report-2.pdf` † | 4-30 |  |
| 160 |  | Study Report 3 | `m4-2-2-1-analytical-methods-and-validation-reports` | F | `m4/42-stud-rep/422-pk/4221-analyt-met-val/study-report-3.pdf` † | 4-31 |  |
| 161 | 4.2.2.2 | Absorption | `m4-2-2-2-absorption` | D | `m4/42-stud-rep/422-pk/4222-absorp` | 4-31 |  |
| 162 |  | Study Report 1 | `m4-2-2-2-absorption` | F | `m4/42-stud-rep/422-pk/4222-absorp/study-report-1.pdf` † | 4-31 |  |
| 163 |  | Study Report 2 | `m4-2-2-2-absorption` | F | `m4/42-stud-rep/422-pk/4222-absorp/study-report-2.pdf` † | 4-31 |  |
| 164 |  | Study Report 3 | `m4-2-2-2-absorption` | F | `m4/42-stud-rep/422-pk/4222-absorp/study-report-3.pdf` † | 4-31 |  |
| 165 | 4.2.2.3 | Distribution | `m4-2-2-3-distribution` | D | `m4/42-stud-rep/422-pk/4223-distrib` | 4-31 |  |
| 166 |  | Study Report 1 | `m4-2-2-3-distribution` | F | `m4/42-stud-rep/422-pk/4223-distrib/study-report-1.pdf` † | 4-32 |  |
| 167 |  | Study Report 2 | `m4-2-2-3-distribution` | F | `m4/42-stud-rep/422-pk/4223-distrib/study-report-2.pdf` † | 4-32 |  |
| 168 |  | Study Report 3 | `m4-2-2-3-distribution` | F | `m4/42-stud-rep/422-pk/4223-distrib/study-report-3.pdf` † | 4-32 |  |
| 169 | 4.2.2.4 | Metabolism | `m4-2-2-4-metabolism` | D | `m4/42-stud-rep/422-pk/4224-metab` | 4-32 |  |
| 170 |  | Study Report 1 | `m4-2-2-4-metabolism` | F | `m4/42-stud-rep/422-pk/4224-metab/study-report-1.pdf` † | 4-32 |  |
| 171 |  | Study Report 2 | `m4-2-2-4-metabolism` | F | `m4/42-stud-rep/422-pk/4224-metab/study-report-2.pdf` † | 4-32 |  |
| 172 |  | Study Report 3 | `m4-2-2-4-metabolism` | F | `m4/42-stud-rep/422-pk/4224-metab/study-report-3.pdf` † | 4-32 |  |
| 173 | 4.2.2.5 | Excretion | `m4-2-2-5-excretion` | D | `m4/42-stud-rep/422-pk/4225-excr` | 4-33 |  |
| 174 |  | Study Report 1 | `m4-2-2-5-excretion` | F | `m4/42-stud-rep/422-pk/4225-excr/study-report-1.pdf` † | 4-33 |  |
| 175 |  | Study Report 2 | `m4-2-2-5-excretion` | F | `m4/42-stud-rep/422-pk/4225-excr/study-report-2.pdf` † | 4-33 |  |
| 176 |  | Study Report 3 | `m4-2-2-5-excretion` | F | `m4/42-stud-rep/422-pk/4225-excr/study-report-3.pdf` † | 4-33 |  |
| 177 | 4.2.2.6 | Pharmacokinetic Drug Interactions (nonclinical) | `m4-2-2-6-pharmacokinetic-drug-interactions` | D | `m4/42-stud-rep/422-pk/4226-pk-drug-interact` | 4-33 |  |
| 178 |  | Study Report 1 | `m4-2-2-6-pharmacokinetic-drug-interactions` | F | `m4/42-stud-rep/422-pk/4226-pk-drug-interact/study-report-1.pdf` † | 4-33 |  |
| 179 |  | Study Report 2 | `m4-2-2-6-pharmacokinetic-drug-interactions` | F | `m4/42-stud-rep/422-pk/4226-pk-drug-interact/study-report-2.pdf` † | 4-33 |  |
| 180 |  | Study Report 3 | `m4-2-2-6-pharmacokinetic-drug-interactions` | F | `m4/42-stud-rep/422-pk/4226-pk-drug-interact/study-report-3.pdf` † | 4-34 |  |
| 181 | 4.2.2.7 | Other Pharmacokinetic Studies | `m4-2-2-7-other-pharmacokinetic-studies` | D | `m4/42-stud-rep/422-pk/4227-other-pk-stud` | 4-34 |  |
| 182 |  | Study Report 1 | `m4-2-2-7-other-pharmacokinetic-studies` | F | `m4/42-stud-rep/422-pk/4227-other-pk-stud/study-report-1.pdf` † | 4-34 |  |
| 183 |  | Study Report 2 | `m4-2-2-7-other-pharmacokinetic-studies` | F | `m4/42-stud-rep/422-pk/4227-other-pk-stud/study-report-2.pdf` † | 4-34 |  |
| 184 |  | Study Report 3 | `m4-2-2-7-other-pharmacokinetic-studies` | F | `m4/42-stud-rep/422-pk/4227-other-pk-stud/study-report-3.pdf` † | 4-34 |  |
| 185 | 4.2.3 | Toxicology | `m4-2-3-toxicology` | D | `m4/42-stud-rep/423-tox` | 4-34 |  |
| 186 | 4.2.3.1 | Single-Dose Toxicity (in order by species, by route) | `m4-2-3-1-single-dose-toxicity` | D | `m4/42-stud-rep/423-tox/4231-single-dose-tox` | 4-35 |  |
| 187 |  | Study Report 1 | `m4-2-3-1-single-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4231-single-dose-tox/study-report-1.pdf` † | 4-35 |  |
| 188 |  | Study Report 2 | `m4-2-3-1-single-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4231-single-dose-tox/study-report-2.pdf` † | 4-35 |  |
| 189 |  | Study Report 3 | `m4-2-3-1-single-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4231-single-dose-tox/study-report-3.pdf` † | 4-35 |  |
| 190 | 4.2.3.2 | Repeat-Dose Toxicity (in order by species, by route, by duration, including supportive toxicokinetics evaluations) | `m4-2-3-2-repeat-dose-toxicity` | D | `m4/42-stud-rep/423-tox/4232-repeat-dose-tox` | 4-35 |  |
| 191 |  | Study Report 1 | `m4-2-3-2-repeat-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4232-repeat-dose-tox/study-report-1.pdf` † | 4-35 |  |
| 192 |  | Study Report 2 | `m4-2-3-2-repeat-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4232-repeat-dose-tox/study-report-2.pdf` † | 4-35 |  |
| 193 |  | Study Report 3 | `m4-2-3-2-repeat-dose-toxicity` | F | `m4/42-stud-rep/423-tox/4232-repeat-dose-tox/study-report-3.pdf` † | 4-36 |  |
| 194 | 4.2.3.3 | Genotoxicity | `m4-2-3-3-genotoxicity` | D | `m4/42-stud-rep/423-tox/4233-genotox` | 4-36 |  |
| 195 | 4.2.3.3.1 | In vitro | `m4-2-3-3-1-in-vitro` | D | `m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro` | 4-36 |  |
| 196 |  | Study Report 1 | `m4-2-3-3-1-in-vitro` | F | `m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro/study-report-1.pdf` † | 4-36 |  |
| 197 |  | Study Report 2 | `m4-2-3-3-1-in-vitro` | F | `m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro/study-report-2.pdf` † | 4-36 |  |
| 198 |  | Study Report 3 | `m4-2-3-3-1-in-vitro` | F | `m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro/study-report-3.pdf` † | 4-36 |  |
| 199 | 4.2.3.3.2 | In vivo (including supportive toxicokinetics evaluations) | `m4-2-3-3-2-in-vivo` | D | `m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo` | 4-37 |  |
| 200 |  | Study Report 1 | `m4-2-3-3-2-in-vivo` | F | `m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo/study-report-1.pdf` † | 4-37 |  |
| 201 |  | Study Report 2 | `m4-2-3-3-2-in-vivo` | F | `m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo/study-report-2.pdf` † | 4-37 |  |
| 202 |  | Study Report 3 | `m4-2-3-3-2-in-vivo` | F | `m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo/study-report-3.pdf` † | 4-37 |  |
| 203 | 4.2.3.4 | Carcinogenicity (including supportive toxicokinetics evaluations) | `m4-2-3-4-carcinogenicity` | D | `m4/42-stud-rep/423-tox/4234-carcigen` | 4-37 |  |
| 204 | 4.2.3.4.1 | Long-term studies (in order by species, including range-finding studies that cannot be appropriately included under repeat-dose toxicity or pharmacokinetics) | `m4-2-3-4-1-long-term-studies` | D | `m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud` | 4-37 |  |
| 205 |  | Study Report 1 | `m4-2-3-4-1-long-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud/study-report-1.pdf` † | 4-37 |  |
| 206 |  | Study Report 2 | `m4-2-3-4-1-long-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud/study-report-2.pdf` † | 4-38 |  |
| 207 |  | Study Report 3 | `m4-2-3-4-1-long-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud/study-report-3.pdf` † | 4-38 |  |
| 208 | 4.2.3.4.2 | Short- or medium-term studies (including range-finding studies that cannot be appropriately included under repeat-dose toxicity or pharmacokinetics) | `m4-2-3-4-2-short-or-medium-term-studies` | D | `m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud` | 4-38 |  |
| 209 |  | Study Report 1 | `m4-2-3-4-2-short-or-medium-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud/study-report-1.pdf` † | 4-38 |  |
| 210 |  | Study Report 2 | `m4-2-3-4-2-short-or-medium-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud/study-report-2.pdf` † | 4-38 |  |
| 211 |  | Study Report 3 | `m4-2-3-4-2-short-or-medium-term-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud/study-report-3.pdf` † | 4-38 |  |
| 212 | 4.2.3.4.3 | Other studies | `m4-2-3-4-3-other-studies` | D | `m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud` | 4-39 |  |
| 213 |  | Study Report 1 | `m4-2-3-4-3-other-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud/study-report-1.pdf` † | 4-39 |  |
| 214 |  | Study Report 2 | `m4-2-3-4-3-other-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud/study-report-2.pdf` † | 4-39 |  |
| 215 |  | Study Report 3 | `m4-2-3-4-3-other-studies` | F | `m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud/study-report-3.pdf` † | 4-39 |  |
| 216 | 4.2.3.5 | Reproductive and Developmental Toxicity (including range-finding studies and supportive toxicokinetics evaluations) (If modified study designs are used, the following subheadings should be modified accordingly) | `m4-2-3-5-reproductive-and-developmental-toxicity` | D | `m4/42-stud-rep/423-tox/4235-repro-dev-tox` | 4-39 |  |
| 217 | 4.2.3.5.1 | Fertility and early embryonic development | `m4-2-3-5-1-fertility-and-early-embryonic-development` | D | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev` | 4-39 |  |
| 218 |  | Study Report 1 | `m4-2-3-5-1-fertility-and-early-embryonic-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev/study-report-1.pdf` † | 4-39 |  |
| 219 |  | Study Report 2 | `m4-2-3-5-1-fertility-and-early-embryonic-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev/study-report-2.pdf` † | 4-40 |  |
| 220 |  | Study Report 3 | `m4-2-3-5-1-fertility-and-early-embryonic-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev/study-report-3.pdf` † | 4-40 |  |
| 221 | 4.2.3.5.2 | Embryo-fetal development | `m4-2-3-5-2-embryo-fetal-development` | D | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev` | 4-40 |  |
| 222 |  | Study Report 1 | `m4-2-3-5-2-embryo-fetal-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev/study-report-1.pdf` † | 4-40 |  |
| 223 |  | Study Report 2 | `m4-2-3-5-2-embryo-fetal-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev/study-report-2.pdf` † | 4-40 |  |
| 224 |  | Study Report 3 | `m4-2-3-5-2-embryo-fetal-development` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev/study-report-3.pdf` † | 4-40 |  |
| 225 | 4.2.3.5.3 | Prenatal and postnatal development, including maternal function | `m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function` | D | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev` | 4-41 |  |
| 226 |  | Study Report 1 | `m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev/study-report-1.pdf` † | 4-41 |  |
| 227 |  | Study Report 2 | `m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev/study-report-2.pdf` † | 4-41 |  |
| 228 |  | Study Report 3 | `m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev/study-report-3.pdf` † | 4-41 |  |
| 229 | 4.2.3.5.4 | Studies in which the offspring (juvenile animals) are dosed and/or further evaluated | `m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated` | D | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv` | 4-41 |  |
| 230 |  | Study Report 1 | `m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv/study-report-1.pdf` † | 4-41 |  |
| 231 |  | Study Report 2 | `m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv/study-report-2.pdf` † | 4-41 |  |
| 232 |  | Study Report 3 | `m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated` | F | `m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv/study-report-3.pdf` † | 4-42 |  |
| 233 | 4.2.3.6 | Local Tolerance | `m4-2-3-6-local-tolerance` | D | `m4/42-stud-rep/423-tox/4236-loc-tol` | 4-42 |  |
| 234 |  | Study Report 1 | `m4-2-3-6-local-tolerance` | F | `m4/42-stud-rep/423-tox/4236-loc-tol/study-report-1.pdf` † | 4-42 |  |
| 235 |  | Study Report 2 | `m4-2-3-6-local-tolerance` | F | `m4/42-stud-rep/423-tox/4236-loc-tol/study-report-2.pdf` † | 4-42 |  |
| 236 |  | Study Report 3 | `m4-2-3-6-local-tolerance` | F | `m4/42-stud-rep/423-tox/4236-loc-tol/study-report-3.pdf` † | 4-42 |  |
| 237 | 4.2.3.7 | Other Toxicity Studies (if available) | `m4-2-3-7-other-toxicity-studies` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud` | 4-42 |  |
| 238 | 4.2.3.7.1 | Antigenicity | `m4-2-3-7-1-antigenicity` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen` | 4-43 |  |
| 239 |  | Study Report 1 | `m4-2-3-7-1-antigenicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen/study-report-1.pdf` † | 4-43 |  |
| 240 |  | Study Report 2 | `m4-2-3-7-1-antigenicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen/study-report-2.pdf` † | 4-43 |  |
| 241 |  | Study Report 3 | `m4-2-3-7-1-antigenicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen/study-report-3.pdf` † | 4-43 |  |
| 242 | 4.2.3.7.2 | Immunotoxicity | `m4-2-3-7-2-immunotoxicity` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox` | 4-43 |  |
| 243 |  | Study Report 1 | `m4-2-3-7-2-immunotoxicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox/study-report-1.pdf` † | 4-43 |  |
| 244 |  | Study Report 2 | `m4-2-3-7-2-immunotoxicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox/study-report-2.pdf` † | 4-43 |  |
| 245 |  | Study Report 3 | `m4-2-3-7-2-immunotoxicity` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox/study-report-3.pdf` † | 4-44 |  |
| 246 | 4.2.3.7.3 | Mechanistic studies (if not included elsewhere) | `m4-2-3-7-3-mechanistic-studies` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud` | 4-44 |  |
| 247 |  | Study Report 1 | `m4-2-3-7-3-mechanistic-studies` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud/study-report-1.pdf` † | 4-44 |  |
| 248 |  | Study Report 2 | `m4-2-3-7-3-mechanistic-studies` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud/study-report-2.pdf` † | 4-44 |  |
| 249 |  | Study Report 3 | `m4-2-3-7-3-mechanistic-studies` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud/study-report-3.pdf` † | 4-44 |  |
| 250 | 4.2.3.7.4 | Dependence | `m4-2-3-7-4-dependence` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep` | 4-44 |  |
| 251 |  | Study Report 1 | `m4-2-3-7-4-dependence` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep/study-report-1.pdf` † | 4-44 |  |
| 252 |  | Study Report 2 | `m4-2-3-7-4-dependence` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep/study-report-2.pdf` † | 4-45 |  |
| 253 |  | Study Report 3 | `m4-2-3-7-4-dependence` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep/study-report-3.pdf` † | 4-45 |  |
| 254 | 4.2.3.7.5 | Metabolites | `m4-2-3-7-5-metabolites` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab` | 4-45 |  |
| 255 |  | Study Report 1 | `m4-2-3-7-5-metabolites` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab/study-report-1.pdf` † | 4-45 |  |
| 256 |  | Study Report 2 | `m4-2-3-7-5-metabolites` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab/study-report-2.pdf` † | 4-45 |  |
| 257 |  | Study Report 3 | `m4-2-3-7-5-metabolites` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab/study-report-3.pdf` † | 4-45 |  |
| 258 | 4.2.3.7.6 | Impurities | `m4-2-3-7-6-impurities` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp` | 4-46 |  |
| 259 |  | Study Report 1 | `m4-2-3-7-6-impurities` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp/study-report-1.pdf` † | 4-46 |  |
| 260 |  | Study Report 2 | `m4-2-3-7-6-impurities` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp/study-report-2.pdf` † | 4-46 |  |
| 261 |  | Study Report 3 | `m4-2-3-7-6-impurities` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp/study-report-3.pdf` † | 4-46 |  |
| 262 | 4.2.3.7.7 | Other | `m4-2-3-7-7-other` | D | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other` | 4-46 |  |
| 263 |  | Study Report 1 | `m4-2-3-7-7-other` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other/study-report-1.pdf` † | 4-46 |  |
| 264 |  | Study Report 2 | `m4-2-3-7-7-other` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other/study-report-2.pdf` † | 4-46 |  |
| 265 |  | Study Report 3 | `m4-2-3-7-7-other` | F | `m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other/study-report-3.pdf` † | 4-47 |  |
| 266 | 4.3 | Literature References | `m4-3-literature-references` | D | `m4/43-lit-ref` | 4-47 | Copies of literature references should ordinarily be submitted as individual files (i.e., one for each reference). |
| 267 |  | Reference 1 | `m4-3-literature-references` | F | `m4/43-lit-ref/reference-1.pdf` † | 4-47 |  |
| 268 |  | Reference 2 | `m4-3-literature-references` | F | `m4/43-lit-ref/reference-2.pdf` † | 4-47 |  |
| 269 |  | Reference 3 | `m4-3-literature-references` | F | `m4/43-lit-ref/reference-3.pdf` † | 4-47 |  |
| 270 | 5 | Clinical Study Reports | `m5-clinical-study-reports` | D | `m5` | 4-48 |  |
| 271 | 5.2 | Tabular Listing of all Clinical Studies | `m5-2-tabular-listing-of-all-clinical-studies` | D | `m5/52-tab-list` | 4-48 |  |
| 272 | 5.2 | Tabular Listing of all Clinical Studies | `m5-2-tabular-listing-of-all-clinical-studies` | F | `m5/52-tab-list/tabular-listing.pdf` | 4-48 |  |
| 273 | 5.3 | Clinical Study Reports | `m5-3-clinical-study-reports` | D | `m5/53-clin-stud-rep` | 4-48 |  |
| 274 | 5.3.1 | Reports of Biopharmaceutic Studies | `m5-3-1-reports-of-biopharmaceutic-studies` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud` | 4-48 |  |
| 275 | 5.3.1.1 | Bioavailability (BA) Study Reports | `m5-3-1-1-bioavailability-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep` | 4-48 |  |
| 276 |  | Study Report 1 | `m5-3-1-1-bioavailability-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep/study-report-1` † | 4-48 | This comment is applicable to all study reports in Module 5. The applicants should ordinarily provide the study reports as multiple files (a synopsis, a main body and appropriate appendices). Appendices should be organized in accordance with the ICH E3 guideline, which describes the content and format of the clinical study report. In choosing the level of granularity for reports the applicant should consider that, when relevant information is changed at any point in the product's life cycle, replacements of complete files should be provided. A directory should be created for each study and the files associated with the study report should be organized within the directory. Individual studies and files do not have specific CTD numbers. |
| 277 |  | Study Report 2 | `m5-3-1-1-bioavailability-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep/study-report-2` † | 4-49 |  |
| 278 |  | Study Report 3 | `m5-3-1-1-bioavailability-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep/study-report-3` † | 4-49 |  |
| 279 | 5.3.1.2 | Comparative BA and Bioequivalence (BE) Study Reports | `m5-3-1-2-comparative-ba-and-bioequivalence-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep` | 4-49 |  |
| 280 |  | Study Report 1 | `m5-3-1-2-comparative-ba-and-bioequivalence-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep/study-report-1` † | 4-49 |  |
| 281 |  | Study Report 2 | `m5-3-1-2-comparative-ba-and-bioequivalence-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep/study-report-2` † | 4-49 |  |
| 282 |  | Study Report 3 | `m5-3-1-2-comparative-ba-and-bioequivalence-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep/study-report-3` † | 4-50 |  |
| 283 | 5.3.1.3 | In vitro – In vivo Correlation Study Reports | `m5-3-1-3-in-vitro-in-vivo-correlation-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep` | 4-50 |  |
| 284 |  | Study Report 1 | `m5-3-1-3-in-vitro-in-vivo-correlation-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep/study-report-1` † | 4-50 |  |
| 285 |  | Study Report 2 | `m5-3-1-3-in-vitro-in-vivo-correlation-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep/study-report-2` † | 4-50 |  |
| 286 |  | Study Report 3 | `m5-3-1-3-in-vitro-in-vivo-correlation-study-reports` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep/study-report-3` † | 4-50 |  |
| 287 | 5.3.1.4 | Reports of Bioanalytical and Analytical Methods for Human Studies | `m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met` | 4-50 |  |
| 288 |  | Study Report 1 | `m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met/study-report-1` † | 4-50 |  |
| 289 |  | Study Report 2 | `m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met/study-report-2` † | 4-51 |  |
| 290 |  | Study Report 3 | `m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies` | D | `m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met/study-report-3` † | 4-51 |  |
| 291 | 5.3.2 | Reports of Studies Pertinent to Pharmacokinetics using Human Biomaterials | `m5-3-2-reports-of-studies-pertinent-to-pharmacokinetics-using-human-biomaterials` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat` | 4-51 |  |
| 292 | 5.3.2.1 | Plasma Protein Binding Study Reports | `m5-3-2-1-plasma-protein-binding-study-reports` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep` | 4-51 |  |
| 293 |  | Study Report 1 | `m5-3-2-1-plasma-protein-binding-study-reports` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep/study-report-1` † | 4-51 |  |
| 294 |  | Study Report 2 | `m5-3-2-1-plasma-protein-binding-study-reports` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep/study-report-2` † | 4-51 |  |
| 295 |  | Study Report 3 | `m5-3-2-1-plasma-protein-binding-study-reports` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep/study-report-3` † | 4-52 |  |
| 296 | 5.3.2.2 | Reports of Hepatic Metabolism and Drug Interaction Studies | `m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud` | 4-52 |  |
| 297 |  | Study Report 1 | `m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud/study-report-1` † | 4-52 |  |
| 298 |  | Study Report 2 | `m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud/study-report-2` † | 4-52 |  |
| 299 |  | Study Report 3 | `m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud/study-report-3` † | 4-52 |  |
| 300 | 5.3.2.3 | Reports of Studies Using Other Human Biomaterials | `m5-3-2-3-reports-of-studies-using-other-human-biomaterials` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat` | 4-52 |  |
| 301 |  | Study Report 1 | `m5-3-2-3-reports-of-studies-using-other-human-biomaterials` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat/study-report-1` † | 4-52 |  |
| 302 |  | Study Report 2 | `m5-3-2-3-reports-of-studies-using-other-human-biomaterials` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat/study-report-2` † | 4-53 |  |
| 303 |  | Study Report 3 | `m5-3-2-3-reports-of-studies-using-other-human-biomaterials` | D | `m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat/study-report-3` † | 4-53 |  |
| 304 | 5.3.3 | Reports of Human Pharmacokinetic (PK) Studies | `m5-3-3-reports-of-human-pharmacokinetics-pk-studies` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud` | 4-53 |  |
| 305 | 5.3.3.1 | Healthy Subject PK and Initial Tolerability Study Reports | `m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep` | 4-53 |  |
| 306 |  | Study Report 1 | `m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep/study-report-1` † | 4-53 |  |
| 307 |  | Study Report 2 | `m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep/study-report-2` † | 4-53 |  |
| 308 |  | Study Report 3 | `m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep/study-report-3` † | 4-53 |  |
| 309 | 5.3.3.2 | Patient PK and Initial Tolerability Study Reports | `m5-3-3-2-patient-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep` | 4-54 |  |
| 310 |  | Study Report 1 | `m5-3-3-2-patient-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep/study-report-1` † | 4-54 |  |
| 311 |  | Study Report 2 | `m5-3-3-2-patient-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep/study-report-2` † | 4-54 |  |
| 312 |  | Study Report 3 | `m5-3-3-2-patient-pk-and-initial-tolerability-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep/study-report-3` † | 4-54 |  |
| 313 | 5.3.3.3 | Intrinsic Factor PK Study Reports | `m5-3-3-3-intrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep` | 4-54 |  |
| 314 |  | Study Report 1 | `m5-3-3-3-intrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep/study-report-1` † | 4-54 |  |
| 315 |  | Study Report 2 | `m5-3-3-3-intrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep/study-report-2` † | 4-55 |  |
| 316 |  | Study Report 3 | `m5-3-3-3-intrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep/study-report-3` † | 4-55 |  |
| 317 | 5.3.3.4 | Extrinsic Factor PK Study Reports | `m5-3-3-4-extrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep` | 4-55 |  |
| 318 |  | Study Report 1 | `m5-3-3-4-extrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep/study-report-1` † | 4-55 |  |
| 319 |  | Study Report 2 | `m5-3-3-4-extrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep/study-report-2` † | 4-55 |  |
| 320 |  | Study Report 3 | `m5-3-3-4-extrinsic-factor-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep/study-report-3` † | 4-55 |  |
| 321 | 5.3.3.5 | Population PK Study Reports | `m5-3-3-5-population-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep` | 4-55 |  |
| 322 |  | Study Report 1 | `m5-3-3-5-population-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep/study-report-1` † | 4-56 |  |
| 323 |  | Study Report 2 | `m5-3-3-5-population-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep/study-report-2` † | 4-56 |  |
| 324 |  | Study Report 3 | `m5-3-3-5-population-pk-study-reports` | D | `m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep/study-report-3` † | 4-56 |  |
| 325 | 5.3.4 | Reports of Human Pharmacodynamic (PD) Studies | `m5-3-4-reports-of-human-pharmacodynamics-pd-studies` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud` | 4-56 |  |
| 326 | 5.3.4.1 | Healthy Subject PD and PK/PD Study Reports | `m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep` | 4-56 |  |
| 327 |  | Study Report 1 | `m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep/study-report-1` † | 4-56 |  |
| 328 |  | Study Report 2 | `m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep/study-report-2` † | 4-57 |  |
| 329 |  | Study Report 3 | `m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep/study-report-3` † | 4-57 |  |
| 330 | 5.3.4.2 | Patient PD and PK/PD Study Reports | `m5-3-4-2-patient-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep` | 4-57 |  |
| 331 |  | Study Report 1 | `m5-3-4-2-patient-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep/study-report-1` † | 4-57 |  |
| 332 |  | Study Report 2 | `m5-3-4-2-patient-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep/study-report-2` † | 4-57 |  |
| 333 |  | Study Report 3 | `m5-3-4-2-patient-pd-and-pk-pd-study-reports` | D | `m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep/study-report-3` † | 4-57 |  |
| 334 | 5.3.5 | Reports of Efficacy and Safety Studies | `m5-3-5-reports-of-efficacy-and-safety-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud` | 4-57 |  |
| 335 | 5.3.5 | Reports of Efficacy and Safety Studies - Indication Name | `m5-3-5-reports-of-efficacy-and-safety-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1` † | 4-58 | The folder name should always include the indication being claimed, for example, 'asthma' (abbreviated if appropriate). Where there is more than one indication (e.g., asthma and migraine), then the first indication has a folder 'asthma' and the second 'migraine'. The ‘indication’ attribute in the backbone should be consistent with that used in the folder name but can be different. For example, an ‘indication’ attribute value of ‘Non-Small Cell Lung Cancer’ could be expressed as ‘NSCLC’ in the folder name. There is currently no standard terminology list for ‘indication’ and applicants should choose the ‘indication’ attributes carefully as they can not be easily changed during the life cycle of the application. The only way this can be accomplished currently is to delete all the leaf elements with the incorrect attribute value and provide new leaf elements for those files with the modified attribute value. Applicants should consult with the regional authority before attempting to modify these attributes to discuss the appropriateness of, and approach to be taken for, this type of change. |
| 336 | 5.3.5.1 | Study Reports of Controlled Clinical Studies Pertinent to the Claimed Indication | `m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5351-stud-rep-contr` † | 4-58 |  |
| 337 |  | Study Report 1 | `m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5351-stud-rep-contr/study-report-1` † | 4-58 |  |
| 338 |  | Study Report 2 | `m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5351-stud-rep-contr/study-report-2` † | 4-58 |  |
| 339 |  | Study Report 3 | `m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5351-stud-rep-contr/study-report-3` † | 4-58 |  |
| 340 | 5.3.5.2 | Study Reports of Uncontrolled Clinical Studies | `m5-3-5-2-study-reports-of-uncontrolled-clinical-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5352-stud-rep-uncontr` † | 4-59 |  |
| 341 |  | Study Report 1 | `m5-3-5-2-study-reports-of-uncontrolled-clinical-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5352-stud-rep-uncontr/study-report-1` † | 4-59 |  |
| 342 |  | Study Report 2 | `m5-3-5-2-study-reports-of-uncontrolled-clinical-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5352-stud-rep-uncontr/study-report-2` † | 4-59 |  |
| 343 |  | Study Report 3 | `m5-3-5-2-study-reports-of-uncontrolled-clinical-studies` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5352-stud-rep-uncontr/study-report-3` † | 4-59 |  |
| 344 | 5.3.5.3 | Reports of Analyses of Data from More than One Study | `m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5353-rep-analys-data-more-one-stud` † | 4-59 |  |
| 345 |  | Study Report 1 | `m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5353-rep-analys-data-more-one-stud/study-report-1` † | 4-59 |  |
| 346 |  | Study Report 2 | `m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5353-rep-analys-data-more-one-stud/study-report-2` † | 4-59 |  |
| 347 |  | Study Report 3 | `m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5353-rep-analys-data-more-one-stud/study-report-3` † | 4-60 |  |
| 348 | 5.3.5.4 | Other Study Reports | `m5-3-5-4-other-study-reports` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5354-other-stud-rep` † | 4-60 |  |
| 349 |  | Study Report 1 | `m5-3-5-4-other-study-reports` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5354-other-stud-rep/study-report-1` † | 4-60 |  |
| 350 |  | Study Report 2 | `m5-3-5-4-other-study-reports` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5354-other-stud-rep/study-report-2` † | 4-60 |  |
| 351 |  | Study Report 3 | `m5-3-5-4-other-study-reports` | D | `m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5354-other-stud-rep/study-report-3` † | 4-60 |  |
| 352 | 5.3.6 | Reports of Postmarketing Experience | `m5-3-6-reports-of-postmarketing-experience` | D | `m5/53-clin-stud-rep/536-postmark-exp` | 4-60 |  |
| 353 | 5.3.7 | Case Report Forms and Individual Patient Listings | `m5-3-7-case-report-forms-and-individual-patient-listings` | D | `m5/53-clin-stud-rep/537-crf-ipl` | 4-61 |  |
| 354 |  | Study 1 | `m5-3-7-case-report-forms-and-individual-patient-listings` | D | `m5/53-clin-stud-rep/537-crf-ipl/study-1` † | 4-61 |  |
| 355 |  | Document/Dataset 1 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-1/filename-1.pdf` † | 4-61 | The filename and extension should include the description of the file and appropriate file extension according to Appendix 2. Reference should be made to regional guidance for the acceptability of submission of datasets |
| 356 |  | Document/Dataset 2 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-1/filename-2.pdf` † | 4-61 |  |
| 357 |  | Document/Dataset 3 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-1/filename-3.pdf` † | 4-61 |  |
| 358 |  | Study 2 | `m5-3-7-case-report-forms-and-individual-patient-listings` | D | `m5/53-clin-stud-rep/537-crf-ipl/study-2` † | 4-61 | define element |
| 359 |  | Document/Dataset 1 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-2/filename-1.pdf` † | 4-61 |  |
| 360 |  | Document/Dataset 2 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-2/filename-2.pdf` † | 4-62 |  |
| 361 |  | Document/Dataset 3 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-2/filename-3.pdf` † | 4-62 |  |
| 362 |  | Study 3 | `m5-3-7-case-report-forms-and-individual-patient-listings` | D | `m5/53-clin-stud-rep/537-crf-ipl/study-3` † | 4-62 | see #358 |
| 363 |  | Document/Dataset 1 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-3/filename-1.pdf` † | 4-62 |  |
| 364 |  | Document/Dataset 2 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-3/filename-2.pdf` † | 4-62 |  |
| 365 |  | Document/Dataset 3 | `m5-3-7-case-report-forms-and-individual-patient-listings` | F | `m5/53-clin-stud-rep/537-crf-ipl/study-3/filename-3.pdf` † | 4-62 |  |
| 366 | 5.4 | Literature References | `m5-4-literature-references` | D | `m5/54-lit-ref` | 4-63 | Copies of literature references should ordinarily be submitted as individual files (i.e,. one for each reference). |
| 367 |  | Reference 1 | `m5-4-literature-references` | F | `m5/54-lit-ref/reference-1.pdf` † | 4-63 |  |
| 368 |  | Reference 2 | `m5-4-literature-references` | F | `m5/54-lit-ref/reference-2.pdf` † | 4-63 |  |
| 369 |  | Reference 3 | `m5-4-literature-references` | F | `m5/54-lit-ref/reference-3.pdf` † | 4-63 |  |
| 370 |  |  |  | D | `util` | 4-64 | utilities |
| 371 |  |  |  | D | `util/dtd` | 4-64 | DTDs/Schemas – it is not necessary to include regional DTDs/Schemas other than the one for the region to which the application is being made. File names in rows 372 - 379 are illustrative only. Please consult regional guidance for the current name and version of the files. |
| 372 |  |  |  | F | `util/dtd/ich-ectd-n.dtd` | 4-64 | DTD for the instance – the version used to create the eCTD submission must be included. “n” denotes the specific version (e.g., 3-2). |
| 373 |  |  |  | F | `util/dtd/eu-regional-n.dtd` | 4-64 | DTD for the EU specific documentation. “n” denotes the specific version (e.g., 1-1). |
| 374 |  |  |  | F | `util/dtd/jp-regional-n.xsd` | 4-64 | Schema for the Japan specific documentation. “n” denotes the specific version (e.g., 1-0). |
| 375 |  |  |  | F | `util/dtd/us-regional-n.dtd` | 4-64 | DTD for the US specific documentation. “n” denotes the specific version (e.g., 1-0). |
| 376 |  |  |  | F | `util/dtd/xx-regional-n.dtd` | 4-65 | DTD for the xx specific documentation, where xx is a two character country code from ISO-3166-1. “n” denotes the specific version (e.g., 1-0). |
| 377 |  |  |  | D | `util/style` | 4-65 | Directory for style sheets – ICH and regional stylesheets |
| 378 |  |  |  | F | `util/style/ectd-n.xsl` | 4-65 | The specific version of the eCTD stylesheet used by the applicant as a reference during the creation of the submission should be included. “n” denotes the specific version (e.g., 1-0). |
| 379 |  |  |  | F | `util/style/xx-regional-n.xsl` | 4-65 | Stylesheet for the xx specific documentation, where xx is a two character country code from ISO-3166-1. “n” denotes the specific version (e.g., 1-0). |

---

## 2. Naming rules

| Rule | Value | Source |
|---|---|---|
| Allowed characters in a *name* | `a`–`z` (U+0061–U+007A), `0`–`9` (U+0030–U+0039), `-` (HYPHEN-MINUS U+002D). Nothing else. | SPEC App 2 "Name" p. 2-3 |
| Explicitly not allowed (examples given) | space, `.` inside a name, `:`, `_` (LOW LINE), UPPERCASE | SPEC pp. 2-3/2-4 |
| Case | "Only lower case letters should be used in all file and directory names" | SPEC p. 2-4; p. 3-1 |
| Japanese characters | Not allowed in file or folder names | SPEC p. 2-3; Retired QA 32 |
| Directory name | = one *name* | SPEC p. 2-4 |
| File name | *name* + `.` (FULL STOP U+002E) + *name* (extension). So **exactly one** dot. | SPEC p. 2-4 |
| Extension | "All files should have one and only one file extension". The extension shows the format. A missing extension is incorrect (`hello`). | SPEC p. 2-3, p. 2-4, p. 3-1 |
| Max length of one folder or file name | **64 characters including the extension** | SPEC p. 2-4; p. 3-1 |
| Max path length | **230 characters including file name and extension** (this leaves regulators 26 characters for their review environment). Regions may set further limits: "Consult regional guidance for further restrictions on the maximum path length." → **ICH sets 230; a region may set a lower limit.** If too long: first shorten the applicant-created names, then the Appendix 4 recommended names. Also check the media/folder limits of the region and M2. | SPEC p. 2-4 |
| Where the path is counted from | Not stated explicitly. Appendix 4 paths are relative to the sequence folder ("Refer to Table 6.1, Appendix 6, for details for the head of the path name", p. 4-1). The Example 6-1 text calls `m2/25-clin-over/` "the one starting below the dossier number directory" (p. 6-11). | SPEC p. 4-1, p. 6-11 |
| Names are identifiers | Short; not meant to carry metadata, but not random; added names should be "descriptive, logical and brief" | SPEC p. 2-1 |
| Document name | The first name of the file name (`docname` in `docname.ext`) | SPEC p. 2-4 |
| File names over the life cycle | Not fixed. Names do not have to stay the same (e.g. `structure.pdf` replaced by `structure2.pdf`), except names the spec or region predefines, e.g. `index.xml` | SPEC pp. 6-4/6-5; Retired QA 23 |
| Folder names across sequences | Do not have to stay the same and may change (e.g. if too long); build tools should not enforce it | QA 59 |
| Folder names vs attribute metadata | No technical requirement that `substance`/`manufacturer`/`product-name`… equal the folder names; tools should let them differ | QA 58; App 4 rows 39, 78, 90 |
| Unique file names in one folder | If all 2.3 files share `23-qos`, every file name "must technically be unique" | QA 65 |
| Character encoding preference | UTF-8 / Unicode 16-bit (ISO-10646) › ISO-8859-1 or -x › SHIFT_JIS › other regionally agreed | SPEC p. 2-4 |
| Example study-file naming | `study-report-1.pdf` … (applicant's internal numbering is typical) | SPEC Table 3-1 p. 3-2 |
| Indication in names | 2.7.3: the file name should always include the indication, e.g. `summary-clin-efficacy-asthma.pdf`. 5.3.5: the folder name should include the indication (`asthma`, `migraine`). The attribute may differ from the name (`Non-Small Cell Lung Cancer` → `nsclc`). | App 4 rows 32, 335 |
| **"-var" convention** | **Not in the ICH spec.** The only ICH mention is QA 73: "a suggested file name is 'excipients.pdf' for a single file or 'excipients-var.pdf' for multiple files where var = a variable portion that differentiates the files". QA 81 suggests `ctrlstrat.pdf` for control-strategy summaries. Any general "-var" rule comes from regional guidance, which is not among these files. | QA 73, QA 81 |
| Validator check | All file/folder names must meet the length limits and allowed characters. (QA 36 item 15 cites "Appendix 6"; the rules are actually in SPEC Appendix 2, p. 2-3/2-4.) | QA 36 item 15 |

### 2.1 Extension ↔ format mapping (SPEC p. 2-3)

| IANA type | ext | | Non-IANA | ext |
|---|---|---|---|---|
| text/css | css | | DTD | dtd |
| text/html | html or htm | | XPT (SAS) | xpt |
| text/xml | xml | | XSL | xsl |
| application/pdf | pdf | | | |
| application/rtf | rtf | | | |
| application/vnd.ms-excel | xls | | | |
| image/jpeg | jpg | | | |
| image/png | png | | | |
| image/gif | gif | | | |

"The presence of a format in this list does not imply that it would be considered an acceptable format." For other formats, use the widely used mapping (p. 2-3). `.tiff` is **not supported** (QA 20).

---

## 3. index.xml (the ICH backbone)

### 3.1 Prolog, root, namespaces

Verbatim from Example 6-1 (SPEC p. 6-11). The spec's typographic quotes are normalised here.
```xml
<?xml version = "1.0" encoding = "UTF-8"?>
<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-x.dtd">
<?xml-stylesheet type="text/xsl" href="util/style/ectd-2-1-x.xsl"?>
<ectd:ectd xmlns:ectd = "http://www.ich.org/ectd" xmlns:xlink = "http://www.w3c.org/1999/xlink">
  <m2-common-technical-document-summaries>
    <m2-5-clinical-overview xml:lang = "en">
      <leaf ID="s123456" operation = "new" xlink:type = "simple" checksum-type="md5"
            checksum = "e854d3002c02a61fe5cbe926fd973401"
            xlink:href = "m2/25-clin-over/clinical-overview.pdf" application-version = "PDF 1.4">
        <title>Clinical Overview</title>
      </leaf>
    </m2-5-clinical-overview>
  </m2-common-technical-document-summaries>
</ectd:ectd>
```

| Item | Rule | Source |
|---|---|---|
| File name / place | `index.xml`, in the sequence folder | SPEC p. 6-2; App 4 row 1 |
| Top 3 lines | XML version, stylesheet type and address, DTD name and address | SPEC App 7 p. 7-5 |
| DOCTYPE | `<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-x.dtd">`, a relative path to the DTD copy in this sequence's `util/dtd`. With the supplied DTD the file is `ich-ectd-3-2.dtd` (row 372: "n … e.g., 3-2"). | SPEC p. 6-11; App 4 row 372 |
| Root element | `ectd:ectd` (namespace prefix `ectd`) | DTD; SPEC p. 8-2 |
| Namespaces (FIXED in DTD) | `xmlns:ectd="http://www.ich.org/ectd"`, `xmlns:xlink="http://www.w3c.org/1999/xlink"`. Note: **w3c.org**, as written in the DTD (`#FIXED`), not the W3C XLink URI | DTD `ATTLIST ectd:ectd`, `leaf`, `xref` |
| Other root attributes | `xml:lang CDATA #IMPLIED`; `dtd-version CDATA #FIXED "3.2"` | DTD |
| Validation | Validate index.xml against the DTD version in `util/dtd`; the DTD's checksum must equal the ICH-published one | QA 36 items 2–4 |
| Primary modules | `m1-administrative-information-and-prescribing-information`, `m2-common-technical-document-summaries`, `m3-quality`, `m4-nonclinical-study-reports`, `m5-clinical-study-reports`, each optional (`?`) and in this order | DTD; SPEC p. 6-8 |
| xml:lang | "not currently used in the ICH eCTD backbone"; see regional guidance for m1. (Table 6-8 still lists it with example `en`, ISO-639.) | QA 57; SPEC p. 6-9 |

### 3.2 DTD declarations (verbatim from `ich-ectd-3-2.dtd`; also SPEC App 8 p. 8-2)

```dtd
<!ENTITY % att " ID       ID     #IMPLIED
   xml:lang CDATA  #IMPLIED">
<!ELEMENT ectd:ectd (m1-administrative-information-and-prescribing-information?, m2-common-technical-document-summaries?, m3-quality?, m4-nonclinical-study-reports?, m5-clinical-study-reports?)>
<!ATTLIST ectd:ectd
	xmlns:ectd CDATA #FIXED "http://www.ich.org/ectd"
	xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
	xml:lang CDATA #IMPLIED
	dtd-version CDATA #FIXED "3.2"
>
<!ELEMENT leaf (title, link-text?)>
<!ATTLIST leaf
	ID ID #REQUIRED
	application-version CDATA #IMPLIED
	version CDATA #IMPLIED
	font-library CDATA #IMPLIED
	operation (new | append | replace | delete) #REQUIRED
	modified-file CDATA #IMPLIED
	checksum CDATA #REQUIRED
	checksum-type CDATA #REQUIRED
	keywords CDATA #IMPLIED
	xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
	xlink:type CDATA #FIXED "simple"
	xlink:role CDATA #IMPLIED
	xlink:href CDATA #IMPLIED
	xlink:show (new | replace | embed | other | none) #IMPLIED
	xlink:actuate (onLoad | onRequest | other | none) #IMPLIED
	xml:lang CDATA #IMPLIED
>
<!ELEMENT title (#PCDATA)>
<!ATTLIST title
	ID ID #IMPLIED
>
<!ELEMENT link-text (#PCDATA | xref)*>
<!ATTLIST link-text
	ID ID #IMPLIED
>
<!ELEMENT xref EMPTY>
<!ATTLIST xref
	ID ID #REQUIRED
	xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
	xlink:type CDATA #FIXED "simple"
	xlink:role CDATA #IMPLIED
	xlink:title CDATA #REQUIRED
	xlink:href CDATA #REQUIRED
	xlink:show (new | replace | embed | other | none) #IMPLIED
	xlink:actuate (onLoad | onRequest | other | none) #IMPLIED
>
<!ELEMENT node-extension (title, (leaf | node-extension)+)>
<!ATTLIST node-extension
	ID ID #IMPLIED
	xml:lang CDATA #IMPLIED
>
<!ELEMENT m1-administrative-information-and-prescribing-information (leaf*)>
<!ATTLIST m1-administrative-information-and-prescribing-information
	%att; 
>
```
DTD change log (DTD comment header): in v3.2 `indication` became **#REQUIRED** on `m2-7-3-summary-of-clinical-efficacy` and `m5-3-5-reports-of-efficacy-and-safety-studies`, and `ID` went back to **#IMPLIED** for `%att;` and `node-extension` ("ID is only needed for files referenced in a LEAF").

### 3.3 `<leaf>`: every attribute (DTD + SPEC Table 6-8 pp. 6-9…6-11 + QA)

| Attribute | DTD | Meaning / rule | Example | Source |
|---|---|---|---|---|
| `ID` | ID **#REQUIRED** | Unique reference. An XML ID starts with a letter or `_`. A numbers-only generator → prefix it with a letter or `_`. **Unique within the XML instance** (a duplicate is a parse error); not technically required to be unique within a sequence. | `id050520`, `a1234567` | Table 6-8; QA 52; QA 36 item 4; Retired QA 11 |
| `operation` | (new\|append\|replace\|delete) **#REQUIRED** | See §3.7 | `new` | Table 6-8, 6-3 |
| `modified-file` | CDATA #IMPLIED | `../<seq>/index.xml#<leafID>` of the leaf being replaced, appended or deleted. Required in practice for append/replace/delete; empty or absent for new. | `../0001/index.xml#a1234567` | p. 6-4; Table 6-8; QA 36 item 4 |
| `checksum` | CDATA **#REQUIRED** | MD5 of the file. For `delete`: empty `""` | `e854d3002c02a61fe5cbe926fd97b001` | Table 6-8; Table 6-3; QA 49 |
| `checksum-type` | CDATA **#REQUIRED** | Algorithm. For `delete`: empty in all regions **except Japan** (Japan: `checksum=""` and `checksum-type="md5"`) | `MD5` (Table 6-8) / `md5` (all XML examples) | Table 6-8; QA 49 |
| `xlink:href` | CDATA #IMPLIED (in the DTD) | Relative path + file name of the content file. Need not be in the same sequence (see §3.7). Must point to an existing file for new/append/replace; not needed for delete. | `m2/25-clin-over/clinical-overview.pdf` | Table 6-8; QA 36 items 4, 12; QA 49 |
| `xlink:type` | #FIXED `"simple"` | Fixed | `simple` | DTD; Table 6-8 |
| `application-version` | #IMPLIED | Version of the file format. Use **only** for PDF leaf elements, to state the PDF version. | `PDF 1.4` | Table 6-8; QA 56 |
| `version` | #IMPLIED | Submitter's internal version id | `V23.5` | Table 6-8 |
| `font-library` | #IMPLIED | Reserved for Future Use; no agency uses it | — | Table 6-8; Retired QA 19 |
| `keywords` | #IMPLIED | Reserved for Future Use | — | Table 6-8 |
| `xlink:role`, `xlink:show`, `xlink:actuate` | #IMPLIED | Reserved for Future Use | — | Table 6-8 |
| `xml:lang` | #IMPLIED | Not used in the ICH backbone | — | QA 57 |
| `xmlns:xlink` | #FIXED | `http://www.w3c.org/1999/xlink` | — | DTD |

"There are four technically required attributes for each leaf element: ID, operation, checksum and checksum-type." (QA 49). For `#IMPLIED` attributes with no value, **omit the attribute** (QA 49). An empty `modified-file=""` equals leaving it out (p. 6-4).

Child `<title>` (required, `#PCDATA`, optional `ID`): a practical, concise name. **Max 1024 bytes (512 characters) proposed.** Must not be empty, except for a `delete` leaf (regional) (Table 6-8 p. 6-11; QA 36 item 20). `<link-text>` and `<xref>`: "Reserved for Future Use" (Table 6-8).

### 3.4 Table-of-contents (heading) elements and their attributes

* Every heading element has `%att;` = `ID ID #IMPLIED` + `xml:lang CDATA #IMPLIED` (ID is optional at this level: Table 6-8).
* Content models: lowest-level headings = `((leaf | node-extension)*)`. Higher headings = `(leaf*, child-heading?, …)`, i.e. leaves allowed but **no node-extension**.
* Repeatable (`*`) headings, keyed by attributes: `m2-3-s-drug-substance*`, `m2-3-p-drug-product*`, `m2-7-3-summary-of-clinical-efficacy*`, `m3-2-s-drug-substance*`, `m3-2-p-drug-product*`, `m3-2-p-4-control-of-excipients*`, `m3-2-a-1-facilities-and-equipment*`, `m3-2-a-2-adventitious-agents-safety-evaluation*`, `m5-3-5-reports-of-efficacy-and-safety-studies*`. These are the only `*` headings in the DTD. `m3-2-a-3-excipients` is `?` (at most once) and has no attribute. This is why QA 12 says the spec "allows for one novel excipient in 3.2.A.3" (CR 00050: consult the authority if there is more than one).
* **Attribute name spelling:** the DTD uses **`dosageform`** (no hyphen). SPEC Table 6-8 text and QA 49's XML example write `dosage-form`, but that does not validate against this DTD. SPEC Table 6-11/Example 6-4B and QA 68/70 use `dosageform`.

| Element | Attribute | DTD | Guidance | Source |
|---|---|---|---|---|
| `m2-3-s-drug-substance`, `m3-2-s-drug-substance` | `substance` | **#REQUIRED** | INN recommended (shorten long ones; company code if no INN) | DTD; QA 66, 67; Table 6-10 |
| same | `manufacturer` | **#REQUIRED** | Short; the firm's name or abbreviation, may include the site. Umbrella terms `all` / `applicant` / `not specified` allowed | QA 66, 67 |
| `m2-3-p-drug-product`, `m3-2-p-drug-product` | `product-name`, `dosageform`, `manufacturer` | #IMPLIED | Optional; short; trade names not recommended; product manufacturer may differ from substance manufacturer | DTD; QA 68–70; Table 6-11 |
| `m3-2-p-4-control-of-excipients` | `excipient` | #IMPLIED | Optional; if 3.2.P.4 repeats, use it. General terms (`all`, `compendial`, `coating agent`, `non-compendial`) or names | DTD; QA 72 |
| `m3-2-a-1-facilities-and-equipment`, `m3-2-a-2-adventitious-agents-safety-evaluation` | `manufacturer`, `substance`, `dosageform`, `product-name` | #IMPLIED | No link needed to 3.2.S/3.2.P values; pick any or none | DTD; QA 78, 79 |
| `m2-7-3-summary-of-clinical-efficacy`, `m5-3-5-reports-of-efficacy-and-safety-studies` | `indication` | **#REQUIRED** | Free text, no controlled list; applies to all headings below it | DTD; Table 6-9; Retired QA 7 |
| all of the above | — | — | "can not be easily changed during the life cycle"; the only way to change one is to delete all leaves under the old value and re-submit them under the new one; consult the authority first | SPEC pp. 6-9, 6-12…6-14; App 4 rows 32, 39, 78, 90, 335; QA 45, 75; Retired QA 3 |
| — | — | — | Module 3 XML structure need **not** match Module 2.3 (e.g. 2.3.S `manufacturer="all"` while 3.2.S has one per manufacturer) | QA 65 |

### 3.5 Every heading element in the DTD (generated from `ich-ectd-3-2.dtd`; CTD § from App 4)


| Element (DTD order) | CTD § | Content model (L = `((leaf \| node-extension)*)` = lowest level, node-extension allowed) | Attributes besides `%att;` (`ID ID #IMPLIED`, `xml:lang CDATA #IMPLIED`) |
|---|---|---|---|
| `m1-administrative-information-and-prescribing-information` | 1 | (leaf*) | — |
| `m2-common-technical-document-summaries` | 2 | (leaf*, m2-2-introduction?, m2-3-quality-overall-summary?, m2-4-nonclinical-overview?, m2-5-clinical-overview?, m2-6-nonclinical-written-and-tabulated-summaries?, m2-7-clinical-summary?) | — |
| `m2-2-introduction` | 2.2 | L | — |
| `m2-3-quality-overall-summary` | 2.3 | (leaf*, m2-3-introduction?, m2-3-s-drug-substance*, m2-3-p-drug-product*, m2-3-a-appendices?, m2-3-r-regional-information?) | — |
| `m2-3-introduction` | 2.3 | L | — |
| `m2-3-s-drug-substance` | 2.3.S | L | substance CDATA #REQUIRED; manufacturer CDATA #REQUIRED |
| `m2-3-p-drug-product` | 2.3.P | L | product-name CDATA #IMPLIED; dosageform CDATA #IMPLIED; manufacturer CDATA #IMPLIED |
| `m2-3-a-appendices` | 2.3.A | L | — |
| `m2-3-r-regional-information` | 2.3.R | L | — |
| `m2-4-nonclinical-overview` | 2.4 | L | — |
| `m2-5-clinical-overview` | 2.5 | L | — |
| `m2-6-nonclinical-written-and-tabulated-summaries` | 2.6 | (leaf*, m2-6-1-introduction?, m2-6-2-pharmacology-written-summary?, m2-6-3-pharmacology-tabulated-summary?, m2-6-4-pharmacokinetics-written-summary?, m2-6-5-pharmacokinetics-tabulated-summary?, m2-6-6-toxicology-written-summary?, m2-6-7-toxicology-tabulated-summary?) | — |
| `m2-6-1-introduction` | 2.6.1 | L | — |
| `m2-6-2-pharmacology-written-summary` | 2.6.2 | L | — |
| `m2-6-3-pharmacology-tabulated-summary` | 2.6.3 | L | — |
| `m2-6-4-pharmacokinetics-written-summary` | 2.6.4 | L | — |
| `m2-6-5-pharmacokinetics-tabulated-summary` | 2.6.5 | L | — |
| `m2-6-6-toxicology-written-summary` | 2.6.6 | L | — |
| `m2-6-7-toxicology-tabulated-summary` | 2.6.7 | L | — |
| `m2-7-clinical-summary` | 2.7 | (leaf*, m2-7-1-summary-of-biopharmaceutic-studies-and-associated-analytical-methods?, m2-7-2-summary-of-clinical-pharmacology-studies?, m2-7-3-summary-of-clinical-efficacy*, m2-7-4-summary-of-clinical-safety?, m2-7-5-literature-references?, m2-7-6-synopses-of-individual-studies?) | — |
| `m2-7-1-summary-of-biopharmaceutic-studies-and-associated-analytical-methods` | 2.7.1 | L | — |
| `m2-7-2-summary-of-clinical-pharmacology-studies` | 2.7.2 | L | — |
| `m2-7-3-summary-of-clinical-efficacy` | 2.7.3 | L | indication CDATA #REQUIRED |
| `m2-7-4-summary-of-clinical-safety` | 2.7.4 | L | — |
| `m2-7-5-literature-references` | 2.7.5 | L | — |
| `m2-7-6-synopses-of-individual-studies` | 2.7.6 | L | — |
| `m3-quality` | 3 | (leaf*, m3-2-body-of-data?, m3-3-literature-references?) | — |
| `m3-2-body-of-data` | 3.2 | (leaf*, m3-2-s-drug-substance*, m3-2-p-drug-product*, m3-2-a-appendices?, m3-2-r-regional-information?) | — |
| `m3-2-s-drug-substance` | 3.2.S | (leaf*, m3-2-s-1-general-information?, m3-2-s-2-manufacture?, m3-2-s-3-characterisation?, m3-2-s-4-control-of-drug-substance?, m3-2-s-5-reference-standards-or-materials?, m3-2-s-6-container-closure-system?, m3-2-s-7-stability?) | substance CDATA #REQUIRED; manufacturer CDATA #REQUIRED |
| `m3-2-s-1-general-information` | 3.2.S.1 | (leaf*, m3-2-s-1-1-nomenclature?, m3-2-s-1-2-structure?, m3-2-s-1-3-general-properties?) | — |
| `m3-2-s-1-1-nomenclature` | 3.2.S.1.1 | L | — |
| `m3-2-s-1-2-structure` | 3.2.S.1.2 | L | — |
| `m3-2-s-1-3-general-properties` | 3.2.S.1.3 | L | — |
| `m3-2-s-2-manufacture` | 3.2.S.2 | (leaf*, m3-2-s-2-1-manufacturer?, m3-2-s-2-2-description-of-manufacturing-process-and-process-controls?, m3-2-s-2-3-control-of-materials?, m3-2-s-2-4-controls-of-critical-steps-and-intermediates?, m3-2-s-2-5-process-validation-and-or-evaluation?, m3-2-s-2-6-manufacturing-process-development?) | — |
| `m3-2-s-2-1-manufacturer` | 3.2.S.2.1 | L | — |
| `m3-2-s-2-2-description-of-manufacturing-process-and-process-controls` | 3.2.S.2.2 | L | — |
| `m3-2-s-2-3-control-of-materials` | 3.2.S.2.3 | L | — |
| `m3-2-s-2-4-controls-of-critical-steps-and-intermediates` | 3.2.S.2.4 | L | — |
| `m3-2-s-2-5-process-validation-and-or-evaluation` | 3.2.S.2.5 | L | — |
| `m3-2-s-2-6-manufacturing-process-development` | 3.2.S.2.6 | L | — |
| `m3-2-s-3-characterisation` | 3.2.S.3 | (leaf*, m3-2-s-3-1-elucidation-of-structure-and-other-characteristics?, m3-2-s-3-2-impurities?) | — |
| `m3-2-s-3-1-elucidation-of-structure-and-other-characteristics` | 3.2.S.3.1 | L | — |
| `m3-2-s-3-2-impurities` | 3.2.S.3.2 | L | — |
| `m3-2-s-4-control-of-drug-substance` | 3.2.S.4 | (leaf*, m3-2-s-4-1-specification?, m3-2-s-4-2-analytical-procedures?, m3-2-s-4-3-validation-of-analytical-procedures?, m3-2-s-4-4-batch-analyses?, m3-2-s-4-5-justification-of-specification?) | — |
| `m3-2-s-4-1-specification` | 3.2.S.4.1 | L | — |
| `m3-2-s-4-2-analytical-procedures` | 3.2.S.4.2 | L | — |
| `m3-2-s-4-3-validation-of-analytical-procedures` | 3.2.S.4.3 | L | — |
| `m3-2-s-4-4-batch-analyses` | 3.2.S.4.4 | L | — |
| `m3-2-s-4-5-justification-of-specification` | 3.2.S.4.5 | L | — |
| `m3-2-s-5-reference-standards-or-materials` | 3.2.S.5 | L | — |
| `m3-2-s-6-container-closure-system` | 3.2.S.6 | L | — |
| `m3-2-s-7-stability` | 3.2.S.7 | (leaf*, m3-2-s-7-1-stability-summary-and-conclusions?, m3-2-s-7-2-post-approval-stability-protocol-and-stability-commitment?, m3-2-s-7-3-stability-data?) | — |
| `m3-2-s-7-1-stability-summary-and-conclusions` | 3.2.S.7.1 | L | — |
| `m3-2-s-7-2-post-approval-stability-protocol-and-stability-commitment` | 3.2.S.7.2 | L | — |
| `m3-2-s-7-3-stability-data` | 3.2.S.7.3 | L | — |
| `m3-2-p-drug-product` | 3.2.P | (leaf*, m3-2-p-1-description-and-composition-of-the-drug-product?, m3-2-p-2-pharmaceutical-development?, m3-2-p-3-manufacture?, m3-2-p-4-control-of-excipients*, m3-2-p-5-control-of-drug-product?, m3-2-p-6-reference-standards-or-materials?, m3-2-p-7-container-closure-system?, m3-2-p-8-stability?) | product-name CDATA #IMPLIED; dosageform CDATA #IMPLIED; manufacturer CDATA #IMPLIED |
| `m3-2-p-1-description-and-composition-of-the-drug-product` | 3.2.P.1 | L | — |
| `m3-2-p-2-pharmaceutical-development` | 3.2.P.2 | L | — |
| `m3-2-p-3-manufacture` | 3.2.P.3 | (leaf*, m3-2-p-3-1-manufacturers?, m3-2-p-3-2-batch-formula?, m3-2-p-3-3-description-of-manufacturing-process-and-process-controls?, m3-2-p-3-4-controls-of-critical-steps-and-intermediates?, m3-2-p-3-5-process-validation-and-or-evaluation?) | — |
| `m3-2-p-3-1-manufacturers` | 3.2.P.3.1 | L | — |
| `m3-2-p-3-2-batch-formula` | 3.2.P.3.2 | L | — |
| `m3-2-p-3-3-description-of-manufacturing-process-and-process-controls` | 3.2.P.3.3 | L | — |
| `m3-2-p-3-4-controls-of-critical-steps-and-intermediates` | 3.2.P.3.4 | L | — |
| `m3-2-p-3-5-process-validation-and-or-evaluation` | 3.2.P.3.5 | L | — |
| `m3-2-p-4-control-of-excipients` | 3.2.P.4 | (leaf*, m3-2-p-4-1-specifications?, m3-2-p-4-2-analytical-procedures?, m3-2-p-4-3-validation-of-analytical-procedures?, m3-2-p-4-4-justification-of-specifications?, m3-2-p-4-5-excipients-of-human-or-animal-origin?, m3-2-p-4-6-novel-excipients?) | excipient CDATA #IMPLIED |
| `m3-2-p-4-1-specifications` | 3.2.P.4.1 | L | — |
| `m3-2-p-4-2-analytical-procedures` | 3.2.P.4.2 | L | — |
| `m3-2-p-4-3-validation-of-analytical-procedures` | 3.2.P.4.3 | L | — |
| `m3-2-p-4-4-justification-of-specifications` | 3.2.P.4.4 | L | — |
| `m3-2-p-4-5-excipients-of-human-or-animal-origin` | 3.2.P.4.5 | L | — |
| `m3-2-p-4-6-novel-excipients` | 3.2.P.4.6 | L | — |
| `m3-2-p-5-control-of-drug-product` | 3.2.P.5 | (leaf*, m3-2-p-5-1-specifications?, m3-2-p-5-2-analytical-procedures?, m3-2-p-5-3-validation-of-analytical-procedures?, m3-2-p-5-4-batch-analyses?, m3-2-p-5-5-characterisation-of-impurities?, m3-2-p-5-6-justification-of-specifications?) | — |
| `m3-2-p-5-1-specifications` | 3.2.P.5.1 | L | — |
| `m3-2-p-5-2-analytical-procedures` | 3.2.P.5.2 | L | — |
| `m3-2-p-5-3-validation-of-analytical-procedures` | 3.2.P.5.3 | L | — |
| `m3-2-p-5-4-batch-analyses` | 3.2.P.5.4 | L | — |
| `m3-2-p-5-5-characterisation-of-impurities` | 3.2.P.5.5 | L | — |
| `m3-2-p-5-6-justification-of-specifications` | 3.2.P.5.6 | L | — |
| `m3-2-p-6-reference-standards-or-materials` | 3.2.P.6 | L | — |
| `m3-2-p-7-container-closure-system` | 3.2.P.7 | L | — |
| `m3-2-p-8-stability` | 3.2.P.8 | (leaf*, m3-2-p-8-1-stability-summary-and-conclusion?, m3-2-p-8-2-post-approval-stability-protocol-and-stability-commitment?, m3-2-p-8-3-stability-data?) | — |
| `m3-2-p-8-1-stability-summary-and-conclusion` | 3.2.P.8.1 | L | — |
| `m3-2-p-8-2-post-approval-stability-protocol-and-stability-commitment` | 3.2.P.8.2 | L | — |
| `m3-2-p-8-3-stability-data` | 3.2.P.8.3 | L | — |
| `m3-2-a-appendices` | 3.2.A | (leaf*, m3-2-a-1-facilities-and-equipment*, m3-2-a-2-adventitious-agents-safety-evaluation*, m3-2-a-3-excipients?) | — |
| `m3-2-a-1-facilities-and-equipment` | 3.2.A.1 | L | manufacturer CDATA #IMPLIED; substance CDATA #IMPLIED; dosageform CDATA #IMPLIED; product-name CDATA #IMPLIED |
| `m3-2-a-2-adventitious-agents-safety-evaluation` | 3.2.A.2 | L | manufacturer CDATA #IMPLIED; substance CDATA #IMPLIED; dosageform CDATA #IMPLIED; product-name CDATA #IMPLIED |
| `m3-2-a-3-excipients` | 3.2.A.3 | L | — |
| `m3-2-r-regional-information` | 3.2.R | L | — |
| `m3-3-literature-references` | 3.3 | L | — |
| `m4-nonclinical-study-reports` | 4 | (leaf*, m4-2-study-reports?, m4-3-literature-references?) | — |
| `m4-2-study-reports` | 4.2 | (leaf*, m4-2-1-pharmacology?, m4-2-2-pharmacokinetics?, m4-2-3-toxicology?) | — |
| `m4-2-1-pharmacology` | 4.2.1 | (leaf*, m4-2-1-1-primary-pharmacodynamics?, m4-2-1-2-secondary-pharmacodynamics?, m4-2-1-3-safety-pharmacology?, m4-2-1-4-pharmacodynamic-drug-interactions?) | — |
| `m4-2-1-1-primary-pharmacodynamics` | 4.2.1.1 | L | — |
| `m4-2-1-2-secondary-pharmacodynamics` | 4.2.1.2 | L | — |
| `m4-2-1-3-safety-pharmacology` | 4.2.1.3 | L | — |
| `m4-2-1-4-pharmacodynamic-drug-interactions` | 4.2.1.4 | L | — |
| `m4-2-2-pharmacokinetics` | 4.2.2 | (leaf*, m4-2-2-1-analytical-methods-and-validation-reports?, m4-2-2-2-absorption?, m4-2-2-3-distribution?, m4-2-2-4-metabolism?, m4-2-2-5-excretion?, m4-2-2-6-pharmacokinetic-drug-interactions?, m4-2-2-7-other-pharmacokinetic-studies?) | — |
| `m4-2-2-1-analytical-methods-and-validation-reports` | 4.2.2.1 | L | — |
| `m4-2-2-2-absorption` | 4.2.2.2 | L | — |
| `m4-2-2-3-distribution` | 4.2.2.3 | L | — |
| `m4-2-2-4-metabolism` | 4.2.2.4 | L | — |
| `m4-2-2-5-excretion` | 4.2.2.5 | L | — |
| `m4-2-2-6-pharmacokinetic-drug-interactions` | 4.2.2.6 | L | — |
| `m4-2-2-7-other-pharmacokinetic-studies` | 4.2.2.7 | L | — |
| `m4-2-3-toxicology` | 4.2.3 | (leaf*, m4-2-3-1-single-dose-toxicity?, m4-2-3-2-repeat-dose-toxicity?, m4-2-3-3-genotoxicity?, m4-2-3-4-carcinogenicity?, m4-2-3-5-reproductive-and-developmental-toxicity?, m4-2-3-6-local-tolerance?, m4-2-3-7-other-toxicity-studies?) | — |
| `m4-2-3-1-single-dose-toxicity` | 4.2.3.1 | L | — |
| `m4-2-3-2-repeat-dose-toxicity` | 4.2.3.2 | L | — |
| `m4-2-3-3-genotoxicity` | 4.2.3.3 | (leaf*, m4-2-3-3-1-in-vitro?, m4-2-3-3-2-in-vivo?) | — |
| `m4-2-3-3-1-in-vitro` | 4.2.3.3.1 | L | — |
| `m4-2-3-3-2-in-vivo` | 4.2.3.3.2 | L | — |
| `m4-2-3-4-carcinogenicity` | 4.2.3.4 | (leaf*, m4-2-3-4-1-long-term-studies?, m4-2-3-4-2-short-or-medium-term-studies?, m4-2-3-4-3-other-studies?) | — |
| `m4-2-3-4-1-long-term-studies` | 4.2.3.4.1 | L | — |
| `m4-2-3-4-2-short-or-medium-term-studies` | 4.2.3.4.2 | L | — |
| `m4-2-3-4-3-other-studies` | 4.2.3.4.3 | L | — |
| `m4-2-3-5-reproductive-and-developmental-toxicity` | 4.2.3.5 | (leaf*, m4-2-3-5-1-fertility-and-early-embryonic-development?, m4-2-3-5-2-embryo-fetal-development?, m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function?, m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated?) | — |
| `m4-2-3-5-1-fertility-and-early-embryonic-development` | 4.2.3.5.1 | L | — |
| `m4-2-3-5-2-embryo-fetal-development` | 4.2.3.5.2 | L | — |
| `m4-2-3-5-3-prenatal-and-postnatal-development-including-maternal-function` | 4.2.3.5.3 | L | — |
| `m4-2-3-5-4-studies-in-which-the-offspring-juvenile-animals-are-dosed-and-or-further-evaluated` | 4.2.3.5.4 | L | — |
| `m4-2-3-6-local-tolerance` | 4.2.3.6 | L | — |
| `m4-2-3-7-other-toxicity-studies` | 4.2.3.7 | (leaf*, m4-2-3-7-1-antigenicity?, m4-2-3-7-2-immunotoxicity?, m4-2-3-7-3-mechanistic-studies?, m4-2-3-7-4-dependence?, m4-2-3-7-5-metabolites?, m4-2-3-7-6-impurities?, m4-2-3-7-7-other?) | — |
| `m4-2-3-7-1-antigenicity` | 4.2.3.7.1 | L | — |
| `m4-2-3-7-2-immunotoxicity` | 4.2.3.7.2 | L | — |
| `m4-2-3-7-3-mechanistic-studies` | 4.2.3.7.3 | L | — |
| `m4-2-3-7-4-dependence` | 4.2.3.7.4 | L | — |
| `m4-2-3-7-5-metabolites` | 4.2.3.7.5 | L | — |
| `m4-2-3-7-6-impurities` | 4.2.3.7.6 | L | — |
| `m4-2-3-7-7-other` | 4.2.3.7.7 | L | — |
| `m4-3-literature-references` | 4.3 | L | — |
| `m5-clinical-study-reports` | 5 | (leaf*, m5-2-tabular-listing-of-all-clinical-studies?, m5-3-clinical-study-reports?, m5-4-literature-references?) | — |
| `m5-2-tabular-listing-of-all-clinical-studies` | 5.2 | L | — |
| `m5-3-clinical-study-reports` | 5.3 | (leaf*, m5-3-1-reports-of-biopharmaceutic-studies?, m5-3-2-reports-of-studies-pertinent-to-pharmacokinetics-using-human-biomaterials?, m5-3-3-reports-of-human-pharmacokinetics-pk-studies?, m5-3-4-reports-of-human-pharmacodynamics-pd-studies?, m5-3-5-reports-of-efficacy-and-safety-studies*, m5-3-6-reports-of-postmarketing-experience?, m5-3-7-case-report-forms-and-individual-patient-listings?) | — |
| `m5-3-1-reports-of-biopharmaceutic-studies` | 5.3.1 | (leaf*, m5-3-1-1-bioavailability-study-reports?, m5-3-1-2-comparative-ba-and-bioequivalence-study-reports?, m5-3-1-3-in-vitro-in-vivo-correlation-study-reports?, m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies?) | — |
| `m5-3-1-1-bioavailability-study-reports` | 5.3.1.1 | L | — |
| `m5-3-1-2-comparative-ba-and-bioequivalence-study-reports` | 5.3.1.2 | L | — |
| `m5-3-1-3-in-vitro-in-vivo-correlation-study-reports` | 5.3.1.3 | L | — |
| `m5-3-1-4-reports-of-bioanalytical-and-analytical-methods-for-human-studies` | 5.3.1.4 | L | — |
| `m5-3-2-reports-of-studies-pertinent-to-pharmacokinetics-using-human-biomaterials` | 5.3.2 | (leaf*, m5-3-2-1-plasma-protein-binding-study-reports?, m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies?, m5-3-2-3-reports-of-studies-using-other-human-biomaterials?) | — |
| `m5-3-2-1-plasma-protein-binding-study-reports` | 5.3.2.1 | L | — |
| `m5-3-2-2-reports-of-hepatic-metabolism-and-drug-interaction-studies` | 5.3.2.2 | L | — |
| `m5-3-2-3-reports-of-studies-using-other-human-biomaterials` | 5.3.2.3 | L | — |
| `m5-3-3-reports-of-human-pharmacokinetics-pk-studies` | 5.3.3 | (leaf*, m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports?, m5-3-3-2-patient-pk-and-initial-tolerability-study-reports?, m5-3-3-3-intrinsic-factor-pk-study-reports?, m5-3-3-4-extrinsic-factor-pk-study-reports?, m5-3-3-5-population-pk-study-reports?) | — |
| `m5-3-3-1-healthy-subject-pk-and-initial-tolerability-study-reports` | 5.3.3.1 | L | — |
| `m5-3-3-2-patient-pk-and-initial-tolerability-study-reports` | 5.3.3.2 | L | — |
| `m5-3-3-3-intrinsic-factor-pk-study-reports` | 5.3.3.3 | L | — |
| `m5-3-3-4-extrinsic-factor-pk-study-reports` | 5.3.3.4 | L | — |
| `m5-3-3-5-population-pk-study-reports` | 5.3.3.5 | L | — |
| `m5-3-4-reports-of-human-pharmacodynamics-pd-studies` | 5.3.4 | (leaf*, m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports?, m5-3-4-2-patient-pd-and-pk-pd-study-reports?) | — |
| `m5-3-4-1-healthy-subject-pd-and-pk-pd-study-reports` | 5.3.4.1 | L | — |
| `m5-3-4-2-patient-pd-and-pk-pd-study-reports` | 5.3.4.2 | L | — |
| `m5-3-5-reports-of-efficacy-and-safety-studies` | 5.3.5 | (leaf*, m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication?, m5-3-5-2-study-reports-of-uncontrolled-clinical-studies?, m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study?, m5-3-5-4-other-study-reports?) | indication CDATA #REQUIRED |
| `m5-3-5-1-study-reports-of-controlled-clinical-studies-pertinent-to-the-claimed-indication` | 5.3.5.1 | L | — |
| `m5-3-5-2-study-reports-of-uncontrolled-clinical-studies` | 5.3.5.2 | L | — |
| `m5-3-5-3-reports-of-analyses-of-data-from-more-than-one-study` | 5.3.5.3 | L | — |
| `m5-3-5-4-other-study-reports` | 5.3.5.4 | L | — |
| `m5-3-6-reports-of-postmarketing-experience` | 5.3.6 | L | — |
| `m5-3-7-case-report-forms-and-individual-patient-listings` | 5.3.7 | L | — |
| `m5-4-literature-references` | 5.4 | L | — |

### 3.6 node-extension

| Rule | Source |
|---|---|
| Model: `<!ELEMENT node-extension (title, (leaf \| node-extension)+)>`. A title first, then at least one leaf or nested node-extension. ID optional. | DTD |
| Only under the **lowest** defined heading (only those have `(leaf \| node-extension)*`). E.g. `m2-3-r-regional-information` can be extended, `m2-3-quality-overall-summary` cannot. | SPEC p. 6-9, p. 6-15 (Ex 6-5) |
| "discouraged and should be done only when unavoidable"; check regional guidance first | SPEC p. 6-9, p. 6-15 |
| One `<node-extension>` per new TOC node. The node-extension's `<title>` describes the extension. | SPEC p. 6-15 |
| To update a file in an extended node, re-submit with **exactly the same element and node-extension information, including the node-extension `<title>`** | SPEC p. 6-15 |
| Regions: FDA case-by-case; others accept appropriate use; see EU/MHLW guidance | Retired QA 28 |
| Node-extension title must not be empty | QA 36 item 20 |
| Example (SPEC p. 6-15): `<m2-3-r-regional-information><node-extension><title>special-summary</title><leaf …><title>Extra Quality Summary</title></leaf></node-extension></m2-3-r-regional-information>` | SPEC Ex 6-5 |
| Without node extensions you cannot create sub-headings under 3.2.P.7, and S.7/P.8/3.2.P.7 do not repeat. Use structured leaf titles instead (e.g. "HDPE Bottle – 50 mL – Specification"; "Aclar blister – 10 mg – accelerated"). Avoid "all strengths". | QA 76, 77 |

### 3.7 Life cycle: operation attribute and modified-file (SPEC App 6 pp. 6-2…6-5, Table 6-3)

| operation | Meaning | modified-file | file / checksum | Reviewer sees (this / previous) |
|---|---|---|---|---|
| `new` | No relation to earlier leaves. Several `new` leaves in one element are OK, in the same or later sequences. | empty or absent | file + MD5 | Current / — |
| `append` | Adds to an existing leaf (missing or new information). Not recommended for two leaves in the **same** submission (e.g. a file split for size). It may fit a document + its amendment in one sequence; consult the authority first. | required | file + MD5 | Current / Current-Appended |
| `replace` | The new leaf replaces an existing leaf | required | file + MD5 | Current / Replaced |
| `delete` | No new file; the target is "no longer relevant to the review" | required | no `xlink:href`; `checksum=""` (and `checksum-type` empty, or `"md5"` in Japan) | — / No longer relevant |

| Rule | Source |
|---|---|
| The new leaf goes in the **same location in the backbone** (same element, same attributes) as the leaf it appends, replaces or deletes | SPEC p. 6-3; Ex 6-2 p. 6-12 |
| `modified-file` = path to the target sequence's `index.xml` + `#` + target leaf ID, e.g. `modified-file="../0001/index.xml#a1234567"` | SPEC p. 6-4; Table 6-8 |
| It targets **one** leaf only; one leaf cannot replace several | SPEC p. 6-4; Retired QA 43 |
| A replaced or deleted leaf is no longer current and **cannot be targeted again**; only the current leaf can be replaced | SPEC p. 6-4; Retired QA 44 |
| Since v3.2.1, `append` may modify a leaf in the same sequence | SPEC change history |
| `modified-file=""` equals not having the attribute | SPEC p. 6-4 |
| Validator: new → modified-file empty or absent; append/replace/delete → valid modified-file; new/append/replace → valid xlink:href; ID starts with a letter or `_` | QA 36 item 4 |
| Use the format of modified-file that matches the referenced DTD (Spec 3.0 vs 3.2) | QA 36 item 14 |
| Only four operations exist; no "reference/reuse" operation will be added | Retired QA 37, 38 |
| A metadata change or file move is never a reason for its own sequence. A leaf's life cycle must not be split across CTD sections (no "replace" in a new heading). A `new` copy in a new heading would break the viewer's life cycle. | QA 75 |
| Attribute values cannot be changed; the workaround is delete + re-submit under the new value | QA 45, 75; SPEC p. 6-12 |
| Use a current DTD as accepted by the region; ICH/regions decide when new DTD releases apply | QA 27 |
| Forward compatibility 3.0→3.2: use IDs even with 3.0 | QA 26 |
| Worked cases: Table 6-4 (new), 6-5 (replace `structure.pdf` by `structure2.pdf`), 6-6 (append), 6-7 (delete) | SPEC pp. 6-4/6-5 |

**File reuse (SPEC pp. 6-5/6-6):** one physical file can be referenced by several leaf elements. Provide each file **once** per sequence and add as many leaves as needed (Retired QA 1). An `xlink:href` may point into **earlier sequences or even other applications**; validators should allow that. Consult the authority first; QA 36 item 12 makes this a regional decision. Caution: several pointers to one file make its life cycle harder to manage (p. 6-1).

**Literature / CRFs (SPEC p. 3-13; Retired QA 42):** literature files sit physically in the 5.4 folder. Their leaves go under the same heading as the study report (with STF info where the region uses it), **plus** a repeated leaf under 5.4. CRFs, datasets and patient listings follow regional guidance.

---

## 4. Checksums

| Item | Rule | Source |
|---|---|---|
| Algorithm | MD5 ("Initially"); RFC 1321 cited | SPEC p. 2-2, p. 2-5 |
| Per file | Every content file has its MD5 in the `checksum` attribute of the leaf that references it, with `checksum-type` = MD5 | SPEC p. 2-2, p. 5-2, Table 6-8 |
| index.xml | MD5 of index.xml goes in **`index-md5.txt`**, in the same folder as index.xml | SPEC p. 5-2, p. 6-2; App 4 row 2 |
| `index-md5.txt` format | **Only the 32 characters of the MD5** of index.xml. **No other characters (including carriage returns and other non-printing characters) before or after.** | QA 48 |
| Letter case of the hex digest | Not stated. All spec examples are lowercase hex (`e854d3002c02a61fe5cbe926fd97b001`) | SPEC Table 6-8, examples |
| Print it | Print the contents of index-md5.txt and put the paper copy with the paper cover letter | SPEC p. 5-2 |
| Regional XML | No separate MD5 file; its checksum is in the index.xml leaf that points to it | SPEC p. 5-2, p. 6-2; Retired QA 31 |
| DTD/util files | Their checksums must match the ICH- and regionally published values | QA 36 items 2, 6, 8 |
| Validation | Every file's checksum = the value in index.xml / xx-regional.xml / index-md5.txt | QA 36 item 11 |
| Delete leaf | `checksum=""` | Table 6-3; QA 49 |

---

## 5. How the regional Module 1 is referenced

| Rule | Source |
|---|---|
| `<!ELEMENT m1-administrative-information-and-prescribing-information (leaf*)>`. In the ICH backbone, m1 holds **only leaf elements** (no ICH sub-headings, no node-extension). | DTD / SPEC p. 8-2 |
| The regional XML backbone (e.g. `us-regional.xml`; generic `xx-regional.xml`) is in the region-specific m1 folder (`m1/eu`, `m1/jp`, `m1/us`, `m1/xx`) of **each** sequence, with the regional documents | SPEC p. 6-2, Table 6-2; App 4 rows 3–7 |
| It is referenced by a `<leaf>` in index.xml (with its checksum) → no separate md5 file | SPEC p. 5-2, p. 6-2 |
| Operation of that leaf: "For each sequence, the operation attribute of the leaf element referencing this file is always 'new'" (SPEC p. 6-2). **But** QA 24 (updated Nov 2008, CR 1870) answers "Refer to regional guidance", says this was not put into v3.2.2 and that the answer "is still valid". → Treat as **regional**; `new` is the ICH default text. | SPEC p. 6-2; QA 24 |
| Regional DTD/schema goes in `util/dtd` of each submission | SPEC p. 6-2 |
| Validator: an `xx-regional.xml` exists in the right folder and validates against the regional DTD/schema/mod files in util/dtd | QA 36 items 5–7, 10 |
| Only one regional directory is needed. A single global multi-region eCTD is not advised. | App 4 row 3; SPEC p. 1-2 |
| Minimal fragment (built from the rules above; **no verbatim m1 leaf example exists in these files**): `<m1-administrative-information-and-prescribing-information><leaf ID="…" operation="new" checksum-type="md5" checksum="<md5 of m1/xx/xx-regional.xml>" xlink:type="simple" xlink:href="m1/xx/xx-regional.xml"><title>…</title></leaf></m1-administrative-information-and-prescribing-information>` | derived |
| The content of Module 1, the regional DTD, the m1 heading list, the cover letter content in m1, URLs in m1 (QA 64), "related sequence" (QA 35), sequence-number/regional metadata: **all regional, not in these files** | SPEC App 5; QA 35, 64 |
| Cover letter: a PDF (e.g. `cover.pdf`) with: a description of the submission; which sections are paper / electronic / both; the media (type, number, approximate size); a virus-free statement + the software used; regulatory and IT contacts | SPEC p. 5-2 |

---

## 6. File formats (SPEC Appendix 7 v3.2.2 vs FMT v1.3, which replaces it per QA 82)

| Topic | SPEC App 7 (2008) | FMT v1.3 (2021) | Related QA |
|---|---|---|---|
| Common formats | PDF narrative; XML structured; graphics: PDF where possible, else JPEG, PNG, SVG, GIF (p. 2-2) | PDF; XML only where the region accepts it (§3); SVG (§4); study datasets are regional (§5) | QA 20: no TIFF; Retired QA 39: XML narratives not supported |
| PDF version | **PDF 1.4** accepted by all regions; PDF/A-1 does not meet review needs (p. 7-1) | Versions as listed on the ICH M2 recommendations web page; readable by Adobe Reader/Acrobat **8+** without extra software/plug-ins (§2.2) | QA 71: PDF 1.4, 1.5, 1.6, 1.7 (with M2 restrictions) accepted by all ICH regulators. QA 80: PDF/A-1 and A-2 permitted (regional acceptance). Retired QA 46/47 |
| Restrictions | — | **No JavaScript, dynamic content (audio/video/effects), attachments or 3D. No annotations** except in Annotated CRFs (§2.1) | — |
| File size | **≤ 100 MB** per PDF (p. 7-1) | **≤ 500 MB**; split larger files (§2.3) | QA 36 item 17 (100 MB, from the 2009 checklist) |
| Fonts | Embed **all** characters of all non-standard fonts (full set, not subset). Guaranteed only: Times New Roman, Arial, Courier + Acrobat fonts. Limit the number of fonts; True Type or Adobe Type 1; no custom fonts. Japanese: subset embedding allowed (pp. 7-1/7-2) | Embed all fonts; **only OpenType or TrueType**; no custom fonts. Preferred (Table 1): Times New Roman (+Italic/Bold/Bold Italic), Arial (+…), Courier New (+…), Symbol, Zapf Dingbats; Japanese: MS Mincho, MS Gothic, Chu-Gothic, Sai-Mincho (§2.4) | — |
| Font size | TNR 12 pt for narrative; 9–10 pt acceptable in tables; avoid smaller (p. 7-2) | **9–12 pt**; TNR 12 narrative; tables 9–10; footnotes 10 pt; figures/tables ≥ 8 pt; Japan: MS Mincho 10.5 pt (§2.4.1) | — |
| Colour | Black text; blue for links; avoid light colours and background shadowing; test on a grayscale printer (p. 7-2) | Black; blue for links; avoid light colours and background shading (§2.4.2) | — |
| Orientation | Portrait as portrait, landscape set to landscape before the final save (p. 7-2) | same (§2.5) | — |
| Page size / margins | Fits A4 (210×297 mm) **and** Letter (8.5×11 in). Left margin ≥ 2.5 cm. Landscape: ≥ 2.0 cm top, ≥ 0.8 cm left/right. Header/footer may be inside the margins but not too close to the edge (p. 7-2) | Fits both A4 and Letter. **≥ 2.5 cm on the binding edge** (left in portrait, top in landscape); **other margins ≥ 1.0 cm**. Header/footer and page numbers **not in the margins** (§2.6) | — |
| Headers/footers | A unique identifier on every page (e.g. study id, batch no.); it need not be the CTD section (pp. 7-2/7-3) | same (§2.7) | Retired QA 41 |
| Source | From electronic source; avoid scanning (p. 7-3) | Avoid image-based PDF; if scanned, make it text-searchable and check the OCR (§2.8) | — |
| Scanning resolution | 300 dpi in general (grayscale/colour discouraged for size); no resampling down. Handwritten notes ≥ 300 dpi, black ink. Non-Western characters (Kanji) 600 dpi. Photos 600 dpi (8-bit gray / 24-bit RGB). Gels/karyotypes 600 dpi 8-bit gray, scanned directly. Plotter 300 dpi. HPLC 300 dpi. No non-uniform scaling (p. 7-3) | Table 2: handwritten 300 dpi (black ink); plotter 300; photo B/W 600 (8-bit gray); photo colour 600 (24-bit RGB); gels/karyotypes 600 (8-bit gray); HPLC 300 (§2.9) | — |
| Image compression | No downsampling. **Lossless:** Zip/Flate (RFC 1950/1951) for colour/gray; CCITT Group 4 for B/W (p. 7-3) | **JPEG 2000** for colour/gray, **JBIG2** for monochrome; both have lossless options (§2.10) | — |
| Colour management | — | Use **ICC profiles** (ISO 15076; OutputIntent) (§2.11–2.12) | — |
| Bookmarks | For documents with a TOC: a bookmark for each TOC item incl. all tables, figures, publications, references, appendices. Same hierarchy as the TOC, no extra levels; ≤ 4 levels recommended. Expanded vs collapsed: no formal guidance, be consistent (pp. 7-3/7-4) | Bookmarks expected **even without a TOC**. Hyperlinked TOC + bookmarks for documents **≥ 5 pages**. Bookmark all tables/figures/publications/references/appendices even if not in the TOC. ≤ 4 levels recommended (more allowed if useful). **Bookmarks collapsed to the first level on open.** Literature references are excepted (§2.13) | QA 53: a document with a TOC must have bookmarks; others where they help navigation |
| Hyperlinks | Thin-line rectangle or blue text. **Relative** paths; absolute links break. **Inherit Zoom** (pp. 7-3/7-4); App 2: links relative, self-contained (p. 2-2) | same; relative for cross-document links; Inherit Zoom (§2.13) | QA 36 item 22: links and bookmarks relative. QA 64: no URLs to websites (m1 = regional) |
| Page numbering | Internal 1…n only; page 1 = first page; Arabic numerals, no Roman, no unnumbered pages. Exception: a file split for size continues the numbering (p. 7-4) | same + exception for literature references (§2.14) | — |
| Document information fields | Regional (p. 7-4) | — | QA 55 |
| Initial view | Bookmarks and Page (Page only if there are no bookmarks); Magnification and Page Layout = default (p. 7-4) | same (§2.15) | QA 55: Show = Bookmarks Panel and Page; Layout default; Magnification default; open to page 1 |
| Fast web view | Optimise (p. 7-1) | Optimise (§2.16) | QA 36 item 23; QA 55 |
| Security | **No security settings, no passwords**; allow printing, changes, selecting text/graphics, notes/form fields (p. 7-4; also p. 5-2 for all files) | **No open-password.** If editing restrictions are applied, the receiver must still be able to open, view, extract form data, print and copy text/images/content. Fix third-party signing/creation tools that block this (§2.17) | QA 36 item 21: no file-level security or password. QA 14: digital signatures are regional |
| Plug-ins | Allowed for creation; review must need no plug-ins beyond Acrobat's (p. 7-5) | same (§2.18) | — |
| Full-text index | Not planned (p. 7-4) | — | QA 16: not required |
| XML files | Only for structured info; narrative XML only by regional agreement; top 3 lines = XML version, stylesheet, DTD (p. 7-5) | XML used for some eCTD content; ask the region (§3) | Retired QA 39 |
| SVG | Discuss use with the authority (pp. 7-5/7-6) | + **SVG must not contain JavaScript** (§4) | — |
| Study datasets | xpt in the extension list (p. 2-3) | Regional: formats, sizes, file names, characters (§5) | — |
| Encryption / transport | Encrypt per ICH M2 Recommendation 4.1 when the region has it; always when sending over the Internet; optional on physical media; the applicant is liable until delivery. Media: regional (pp. 5-2) | — | — |
| Granularity | Per the M4 Granularity Annex; legacy single-file reports are OK; new reports should follow the annex | — | QA 22; App 4 rows 141, 276 (M4: text one file + appendices; M5: synopsis + body + appendices, one directory per study) |

---

## 7. Implementation-relevant Q&As (QA v1.33, sheet "Q&A"; † = retired sheet, still useful)

| No. | Topic | One-line answer |
|---|---|---|
| 8 | append in review tools | The spec covers transport only; ask each region about its review tools |
| 12 | >1 novel excipient in 3.2.A.3 | Consult the authority (CR 00050 open) |
| 14 | Digital signatures | No M2 plans; regional |
| 16 | Full-text indices | Not required |
| 20 | TIFF | Not supported; see App 7 |
| 22 | Legacy single-file reports | Acceptable; new reports should follow the Granularity Annex |
| 24 | Operation of the m1 regional XML leaf | Refer to regional guidance (still valid after the v3.2.1 text "always new") |
| 26 | v3.0→3.2 compatibility | Use IDs even in 3.0; consult the agency on earlier files |
| 27 | DTD version over the life of an application | Use the current DTD accepted by the region; ICH/regions set the timing |
| 35 | related-sequence | Regional |
| 36 | Common misinterpretations | Use the 23-item checklist (below) |
| 48 | index-md5.txt | Only the 32-char MD5; no CR/LF or other characters |
| 49 | Missing attribute values | Omit an IMPLIED attribute that has no value; leaf requires ID, operation, checksum, checksum-type. delete: no href, checksum `""`, checksum-type empty (Japan: `"md5"`) |
| 50 | Applicant stylesheets | Don't; only ICH + regional approved stylesheets |
| 51 | util/dtd, util/style contents | Only ICH/regional DTDs, .mod, valid-values.xml, stylesheets |
| 52 | Leaf ID uniqueness | Unique within the XML instance (parse error otherwise); not required across a sequence |
| 53 | Bookmarks | Required where a TOC exists; otherwise where they help |
| 54 | Empty folders | Not submitted |
| 55 | PDF document properties | PDF version per QA 71; fast web view; no security; Initial View: Bookmarks Panel and Page, Layout/Magnification default, page 1 |
| 56 | application-version | Only for PDF leaves = PDF version (e.g. "PDF 1.4") |
| 57 | xml:lang | Not used in the ICH backbone; m1 regional |
| 58 | Metadata = folder names? | No; tools must allow them to differ (helps path length) |
| 59 | Same folder names across sequences? | No; may change |
| 60 | One STF from several leaves/sequences | Not recommended; no multiple STFs with the same Study ID |
| 61 | STF referencing leaves in other elements/sequences | Not recommended; no duplicate Study IDs |
| 62 | One study in several CTD subsections | One STF in one subsection + a pointer document elsewhere; or several STFs with suffixed IDs (`ADME123-absorption`); never the same Study ID twice |
| 63 | Time-specific analyses in one subsection | Same ID = same study; use suffixes (`abc123-6month`, `abc123-12month`) |
| 64 | URLs | Don't link to websites; include the references; m1 regional |
| **65** | M3 XML structure vs M2.3 | Need not match; 2.3 can be one file (no attributes) or 2.3.S with different values (e.g. `manufacturer="all"`); file names in `23-qos` must be unique |
| **66** | substance/manufacturer needed? | Yes, technically #REQUIRED in 2.3.S and 3.2.S even for one; umbrella terms `all`/`applicant`/`not specified` OK |
| **67** | Text for substance/manufacturer | Short; INN (shortened) or company code; manufacturer = firm/abbreviation(+site); no controlled vocabulary |
| **68** | product-name/manufacturer/dosageform needed? | No, #IMPLIED; useful when 3.2.P repeats or for later line extensions |
| **69** | Product manufacturer ≠ substance manufacturer | Yes, they may differ |
| **70** | Text for product attributes | Short and free text; product-name may be INN/active/diluent/type/strength; avoid trade names; dosageform e.g. "powder for suspension", "diluent" |
| 71 | PDF versions | 1.4, 1.5, 1.6, 1.7 (with M2 restrictions) accepted by all ICH regulators |
| **72** | excipient attribute required? | No (#IMPLIED); use it if 3.2.P.4 repeats; general terms (`all`, `compendial`, `coating agent`, `non-compendial`) or names |
| **73** | Excipient granularity | Option 1: one 3.2.P.4 file; Option 2: repeated 3.2.P.4 per excipient/group at the P.4 level; Option 3: repeated P.4 with P.4.x files. Options 2+3 can be combined. File names `excipients.pdf` / `excipients-var.pdf` |
| **74** | List of excipients | In 3.2.P.1 (with function + standard); specs in 3.2.P.4.1; re-listing in P.4 optional |
| **75** | Excipient becomes compendial / is renamed / no longer novel | Never a sequence only for metadata; don't split a life cycle across headings; replace/delete as described; renaming = delete + new (life cycle disjointed) or wait for the next eCTD version; keep 3.2.A.3 |
| 76 | Container closure organisation | One or many 3.2.P.7 files; no sub-headings (except node-extension); structured leaf titles; keep the approach |
| 77 | Stability organisation | S.7/P.8 not repeatable; structured P.8.3 leaf titles; avoid "all strengths" |
| 78 | Link between 3.2.S/P and 3.2.A.1/A.2 metadata | None needed; A.1/A.2 attributes free (e.g. `manufacturer="East Park Building 2"`) |
| 79 | manufacturer in 3.2.A.1 | Applicant's choice; unique values; prefer fewer sections; shared files once, several leaves |
| 80 | PDF/A | PDF/A-1 and A-2 permitted (regional acceptance) |
| 81 | Control strategy summaries | May go in S.2.6/P.2 or S.4/P.5 etc.; say where in 2.3; file name `ctrlstrat.pdf` |
| 82 | App 7 vs Formats spec | The Formats spec replaces App 7 (regional effective date) |
| 83 | STF unviewable in viewers | Put the sequence number in the STF leaf reference, e.g. `xlink:href="../../../../../../../0004/index.xml#a8d1f…"` |
| †1 | Duplicate documents | One file, several leaves |
| †3/†45 | Changing attribute values | Not possible; delete all + re-submit under the new value (consult the agency) |
| †5 | Which TOC attributes to fill | Always as appropriate: substance, manufacturer, product-name, excipient, indication, dosage form |
| †11 | ID content | Internal IDs are OK; start with a letter or `_` |
| †15 | App 4 file names | Optional, highly recommended |
| †17 | Extra sub-folders | Yes |
| †19 | font-library | Unused |
| †21 | delete checksum | `""` |
| †23 | File name fixed over the life cycle? | No (except predefined names like index.xml) |
| †28 | Node extensions | FDA case-by-case; others accept appropriate use |
| †29 | Global multi-region eCTD | Not advised |
| †31 | Regional md5 file | Not needed |
| †32 | Japanese names | Not allowed |
| †33 | Consecutive sequences | Required in Japan only; unique everywhere |
| †34 | `new` in a node that already has a file | Yes (mostly M1 cover letters/forms) |
| †37/†38 | Reuse operation | No new operations; viewers should show reuse visually |
| †42 | Literature/CRF placement | Literature files in 5.4; leaves under the study heading + a repeat under 5.4; CRFs regional |
| †43 | One leaf replaces many | No; one leaf → one leaf |
| †44 | Replace a leaf twice | No; only the current leaf can be replaced |
| †47 | PDF/A-1 | (2007) not acceptable; superseded by QA 80 |
| †4 | 3.2.P.4 construction | Withdrawn Nov-2011 → see QA 72–75 (App 4 row 90 still cites "Q&A No.4") |

### 7.1 QA 36 validation checklist (sheet "Q&A No. 36", updated June 2009). Verbatim intent.

| # | Check |
|---|---|
| 1 | `index.xml` exists in the sequence folder |
| 2 | ICH-published checksum of the eCTD DTD = checksum of the DTD in `util/dtd` |
| 3 | index.xml validates against that DTD in `util/dtd` |
| 4 | Logical attribute content: new → modified-file empty/absent; append/replace/delete → valid modified-file; new/append/replace → valid xlink:href; ID starts with a letter or `_` |
| 5 | `xx-regional.xml` (xx = eu/jp/us) in the right folder |
| 6 | Regional DTD/Schema/related file checksums = published values |
| 7 | Regional index validates against the regional DTD/Schema/mod files in util/dtd |
| 8–9 | Same as 6–7 for regionally required instance files (e.g. STF) |
| 10 | Regional XML: correct syntax and attribute content (regional) |
| 11 | Every file's checksum = the value in index.xml / xx-regional.xml / index-md5.txt |
| 12 | Every xlink:href target exists (the region decides whether a target may be outside the sequence) |
| 13 | No unreferenced files in m1–m5 (other than util) |
| 14 | modified-file format matches the DTD (3.0 vs 3.2) |
| 15 | File/folder names comply (length, characters) |
| 16 | Each lowest-level heading present has ≥ 1 leaf |
| 17 | No PDF > 100 MB (cf. FMT §2.3: 500 MB) |
| 18 | Sequence numbers have 4 digits (0000–9999) |
| 19 | Sequence folder name = sequence number in xx-regional.xml (not Japan) |
| 20 | Leaf / node-extension title not empty (except delete, regional) |
| 21 | No file-level security / passwords |
| 22 | PDF links and bookmarks relative |
| 23 | PDFs optimised for fast web view |

---

## 8. Not found in these files (needs regional guidance or other ICH documents)

* **Module 1**: its content, heading elements, regional DTD/schema and file names (e.g. the EU/EDA `m1` structure, the regional XML root and envelope, sequence and related-sequence metadata, submission types). ICH only defines the m1 leaf pointer (§5).
* A general **"-var" file-naming convention**. Only QA 73 (`excipients-var.pdf`) mentions it; it is not in SPEC.
* Any **path-length limit other than 230** (regional limits are referenced, not stated).
* **The ICH-published MD5 of the DTD and stylesheet** (QA 36 item 2 / QA 50 refer to them; the values are not in these files). The stylesheet `ectd-2-1-x.xsl` itself is **not** in these files.
* The **STF (Study Tagging File) specification** itself (DTD, `stf-` names, study-id rules beyond QA 60–63, 83), the **M4 Granularity Annex** and **ICH M2 Recommendation 4.1** (encryption): cited, not supplied.
* The list of "currently recommended PDF versions" on the ICH M2 web page (FMT §2.2): only cited.
* Letter case of the MD5 hex in `checksum` / `index-md5.txt`, and the case of the `checksum-type` value (`MD5` in Table 6-8 vs `md5` in every example and QA 49): not specified.
* Maximum number of entries per directory: "reasonable", no number (SPEC p. 2-1).
* Study dataset rules (formats, sizes, names): regional (FMT §5).


---
*Generated from the four ICH source files listed at the top. The Appendix 4 table was extracted with pdfplumber from the PDF table cells (379 rows, rows 12/13 and 77/78 split by hand from merged cells; row 61 title fragment re-joined). The heading-element table was parsed from `ich-ectd-3-2.dtd`.*
