# KB_EU — EU eCTD Module 1 package (closest model for the unpublished "EG Module 1 eCTD Specification")

> **Everything below is EU (EMA / EU network) material, NOT Egyptian.** It is documented because the EDA draft
> "Technical Guidance for eCTD Submissions in Egypt" v1.0/2026 is adapted from the EU *Harmonised Technical Guidance*
> and refers to an "EG Module 1 eCTD Specification" / `eg-regional.xml` / "EG Validation Criteria" / "EG Accepted
> File Formats" that were not available. Egyptian text is cited only in §5 and is marked **EG**.
> Sources were read from the files below only; nothing is from memory. Where something could not be found it says so.

## 0. Sources and how they are cited

| Short cite | File | What it actually is (from its title page) |
|---|---|---|
| **SPEC 3.1.1** | `eu_m1_ig_311.pdf` | *EU Module 1 eCTD Specification, Version 3.1.1, June 2025* (the title says "Specification", not "Implementation Guide"). Page numbers = printed page numbers. |
| **SPEC 3.1** | `eu_m1_spec_31.pdf` | *EU Module 1 eCTD Specification, Version 3.1, June 2024*. Text is identical to 3.1.1 except the changes listed below. |
| **DTD** | `eu_util_new/util/dtd/*` , `util/style/*` | Current EU util package (eu-regional.dtd "EU Backbone 3.1", eu-envelope.mod v3.1 June 2024, eu-leaf.mod v1.4, ich-ectd-3-2.dtd, eu-regional.xsl, ectd-2-0.xsl). |
| **VC** | `eu_vc_82.xlsx` | *EU Region eCTD Validation Criteria Version 8.2, June 2025* — 5 sheets: Document Change Control, eCTD Validation Criteria, File-Folder Structure & Names, Files and Folders Q&A, Picklist Values. |
| **FMT** | `eu_formats_2024.pdf` | *EU Accepted File Formats for eCTD, Version 1.0, June 2024* (2 pages). |
| **HTG** | `eu_htg_601.pdf` | *Harmonised Technical Guidance for eCTD Submissions in the EU, Version 6.0.1* (v6.0 adopted 28 Nov 2024, in effect 1 Mar 2025; 6.0.1 published June 2025). Cited by section; page = TOC page. |
| **EX** | `eu_examples/` (from `eu_examples.zip`) | EMA "CorrectedExamples", 9 examples, files dated Aug 2009, built on EU M1 **DTD 1.4**. |
| **EG** | `src/ectd_draft_2026.clean.txt` | EDA draft v1.0 (2026), cited by its own section numbers. |

**Integrity check done:** MD5 of every util file in `eu_util_new` equals the checksum published in VC rules 1.3, 2.3, 3.3, 4.3, 5.3, 6.3:
`ich-ectd-3-2.dtd 1d6f631cc6b6357f0f4fe378e5f79a27` · `ectd-2-0.xsl 3a07a202455e954a2eb203c5bb443f77` · `eu-regional.dtd f8e473246d58499f9ffff8e51a32380d` ·
`eu-leaf.mod 23b854174e61c68044b9f53c0009af95` · `eu-envelope.mod cf059a8f48c68fe4ce9ad2947ab854ca` · `eu-regional.xsl 474f3fe1fdadb31c74477793e060383d`.

**SPEC 3.1 → 3.1.1 changes** (SPEC 3.1.1 change record, p. 3 entry "3.1.1 23.05.2025"; confirmed by text diff): (a) tracking table not required for EDQM
submissions (App. 2 row 6, p. 34); (b) procedure-number examples changed from `EMEA/H/C/000123/II/0014`, `…/WS0005`, `…/IG0003` to the new
`EMA/VR/xxxxxxxxxx` format for worksharing and (super-)grouping (App. 1.1 `number` and `procedure-tracking/number`, pp. 19–21);
(c) note that the pre-submission product number format `H00XXXX` will be replaced by `H/C/xxxxxx` (Envelope section, p. 10–11). No DTD change.

---

## 1. EU Module 1 folder tree and file names

### 1.1 Tree (SPEC 3.1.1 Appendix 2 "Directory / File Structure for Module 1", pp. 32–49, row numbers = App. 2 "Sequential number")

Codes (App. 2, p. 32): `CC` country/destination code (App. 2.1) · `LL` language code (App. 2.2) · `PIDOC` product-information type (App. 2.3) ·
`VAR` optional variable part · `EXT` extension · `DDDD` 4-digit sequence. "The names of the actual files and directories used should be presented
in lower case" (App. 2 footnote, p. 32).

```
DDDD/                                   sequence folder (VC 13.1: 4 digits 0000-9999)
├── index.xml                           ICH backbone (VC 7.x)
├── index-md5.txt                       MD5 of index.xml (VC 8.x)
├── m1/
│   └── eu/                             row 1  element m1-eu
│       ├── eu-regional.xml             row 2  EU backbone + envelope; its leaf operation "should always be set to 'new'"
│       ├── 10-cover/CC/                rows 3-4  m1-0-cover            (1.0 Cover letter)
│       │     CC-cover-VAR.EXT           row 5  e.g. fr-cover-variationrationale.pdf; "CC-cover.pdf" when alone; letters of undertaking here
│       │     CC-tracking-VAR.EXT        row 6  tracking table: ema-tracking-var.pdf (CP) / common-tracking-var.pdf (MRP/DCP) / be-tracking-var.pdf (NP); not for EDQM
│       ├── 12-form/CC/                 rows 7-8  m1-2-form             (1.2 Application form – any form: new, variation, renewal)
│       │     CC-form-eaf-VAR.EXT        row 9  "CC-form-eaf.pdf" when alone; e.g. fr-form-eaf-tablet.pdf
│       │     CC-form-annex-VAR.EXT      row 10 e.g. fr-form-annex-01.pdf, fr-form-annex-proofpayment.pdf; common-form-annex-12.pdf;
│       │                                       "Supportive documents, which are not part of any M2-5 section or Response to Questions, should be placed here"
│       ├── 13-pi/                      row 11 m1-3-pi                  (1.3 Product information)
│       │   ├── 131-spclabelpl/CC/LL/   rows 12-14 m1-3-1-spc-label-pl  (1.3.1 SmPC, labelling, PL) — country AND language folders
│       │   │     CC-PIDOC-VAR.EXT       row 15 e.g. 13-pi/131-spclabelpl/ema/de/ema-combined-tablet10mgde.pdf
│       │   ├── 132-mockup/CC/          rows 16-17 m1-3-2-mockup   → CC-mockup-VAR.EXT (row 18) e.g. fr-mockup-tablet10mgouter.pdf
│       │   ├── 133-specimen/CC/        rows 19-20 m1-3-3-specimen → CC-specimen-VAR.EXT (row 21)
│       │   ├── 134-consultation/CC/    rows 22-23 m1-3-4-consultation → CC-consultation-VAR.EXT (row 24) e.g. be-consultation-tablet10mgpl.pdf
│       │   ├── 135-approved/CC/        rows 25-26 m1-3-5-approved → CC-approved-VAR.EXT (row 27); CC = receiving country, e.g. fr-approved-poland.pdf
│       │   └── 136-braille/            row 28 m1-3-6-braille      → braille-VAR.EXT (row 29)   (no country folder)
│       ├── 14-expert/                  row 30 m1-4-expert
│       │   ├── 141-quality/            row 31 → quality-VAR.EXT (32)
│       │   ├── 142-nonclinical/        row 33 → nonclinical-VAR.EXT (34)
│       │   └── 143-clinical/           row 35 → clinical-VAR.EXT (36)
│       ├── 15-specific/                row 37 m1-5-specific
│       │   ├── 151-bibliographic/                 row 38 → bibliographic-VAR.EXT (39)
│       │   ├── 152-generic-hybrid-bio-similar/    row 40 → generic-VAR / hybrid-VAR / biosimilar-VAR.EXT (41)
│       │   ├── 153-data-market-exclusivity/       row 42 → datamarketexclusivity-VAR.EXT (43)
│       │   ├── 154-exceptional/                   row 44 → exceptional-VAR.EXT (45)
│       │   └── 155-conditional-ma/                row 46 → conditionalma-VAR.EXT (47)
│       ├── 16-environrisk/             row 48 m1-6-environrisk   (only ONE of 1.6.1 / 1.6.2 may have content in a sequence — rows 50, 52)
│       │   ├── 161-nongmo/             row 49 → nongmo-VAR.EXT (50)
│       │   └── 162-gmo/                row 51 → gmo-VAR.EXT (52)
│       ├── 17-orphan/                  row 53
│       │   ├── 171-similarity/         row 54 → similarity-VAR.EXT (55)
│       │   └── 172-market-exclusivity/ row 56 → marketexclusivity-VAR.EXT (57)
│       ├── 18-pharmacovigilance/       row 58
│       │   ├── 181-phvig-system/       row 59 → phvigsystem-VAR.EXT (60)
│       │   └── 182-riskmgt-system/     row 61 → riskmgtsystem-VAR.EXT (62)
│       ├── 19-clinical-trials/         row 63 → clinicaltrials-VAR.EXT (64)
│       ├── 110-paediatrics/            row 65 → paediatrics-VAR.EXT (66)
│       ├── responses/CC/               rows 67-68 m1-responses → CC-responses-VAR.EXT (69) e.g. be-responses.pdf
│       ├── additional-data/CC/         rows 70-71 m1-additional-data → CC-additionaldata-VAR.EXT (72) e.g. be-additionaldata-yellowpink.pdf
│       └── util/dtd/                   rows 73-74 "Additional folder to hold utility/DTD files used in EU Region only"
├── m2/ … m5/                           ICH (see §3.3 table)
└── util/
    ├── dtd/   ich-ectd-3-2.dtd, eu-regional.dtd, eu-envelope.mod, eu-leaf.mod    row 75 (VC 1.2, 3.2, 4.2, 5.2)
    └── style/ ectd-2-0.xsl, eu-regional.xsl                                       row 76 (VC 2.2, 6.2) — "not to submit customised style-sheets"
```
Notes from App. 2: rows 4, 8, 13, 17, 20, 23, 26, 68, 71 — "Always use the country directory at this level for all procedures even when only one
file is submitted to only one country during the lifecycle"; row 14 — "Always use a language directory at this level". Row 70/72 — Additional
Data "should only be used for information required for National, MR and Decentralised Procedures … not applicable for the Centralised Procedure,
other than for justifications for active substances"; supporting data for variations go to the relevant CTD section, otherwise attach to 1.2.

### 1.2 Country / language sub-folder logic (SPEC 3.1.1 "Directory / File Structure", p. 11; HTG 3.2.1, 3.2.5, 3.2.6)
| Situation | Rule (quoted/condensed) | Source |
|---|---|---|
| Which sections have `CC` folders | "Modules 1.0, 1.2, 1.3.2, 1.3.3, 1.3.4, 1.3.5, 'Additional Data' and 'Responses' have country subdirectories. Module 1.3.1 … has both country and language subdirectories." 1.3.6, 1.4–1.10 have none and fixed names. | SPEC p. 11; p. 13 ("Non-country specific items in Sections 1.4 … 1.10 have fixed file names") |
| Centralised (CP) | country folder "always named either 'ema' or 'common'"; language sub-folders in 1.3.1 use the language code | SPEC p. 11 |
| MRP / DCP / NP | one folder per country; `common` "only … for documents potentially applicable to all EU countries"; in 1.3.1 every document in a language folder "even if the country only has one official language"; multilingual countries (e.g. Belgium) one language folder per language | SPEC pp. 11–12 |
| Several languages outside 1.3.1 | "recommended to use the VAR (variable) part of the filename to identify the language" | SPEC p. 12 |
| MRP/DCP common PI | "always placed under m1/eu/13-pi/131-spclabelpl/common/en" | HTG 3.2.5 |
| MRP/DCP responses | all in `m1/eu/responses/common` regardless of which MS asked | HTG 3.2.6 |
| Why "redundant" folders | "the use of country directories even to place a single file in one submission is justified because it could be used to house several files in a subsequent submission" | SPEC p. 11 (m-1-eu) |
| Additional folders | "In EU module 1, additional folders are not allowed" → warning 15.BP2. M2/M3 none except drug-substance/drug-product branches; optional in 3.2.A, 3.2.R, 3.3, M4 (one level), 5.3.6, 5.4; **required** in M5 except 5.2 (not allowed) | VC sheet "Files and Folders Q&A" |

### 1.3 File-naming convention (SPEC 3.1.1 "File Naming Convention", pp. 12–13)
* Country-specific items in 1.0, 1.2, 1.3, m1-responses, m1-additional-data: **`CC-FIXED-VAR.EXT`**; components separated by hyphens, no spaces,
  hyphens allowed inside VAR. "Fixed components are highly recommended. The variable component is optional." Lower case only.
  Distinguish 1.5 mg vs 15 mg as `1point5mg` or `1-5mg`.
* Examples given: `fr-cover.pdf`, `be-form-eaf.pdf`, `it-form-annex-01.pdf`, `pt-form-annex-proofpayment.pdf`, `se-outer-tablet10mg.pdf`,
  `ema-combined-tablet1-5mg.pdf`, `ema-combined-tablet10mgannotated.pdf`, `nongmo.pdf`.
* Responses: `cc-responses-<regulatory activity type identifier>-<timeline identifier>-<content identifier>.pdf`
  (e.g. `common-responses-maa-d106-clin.pdf` "Day 106 Clinical Responses, MAA"; HTG 3.2.6 Table 8 gives 13 such examples).
* 1.2 file names became **mandatory**: VC "File-Folder" sheet row 34 comment: "The previous recommendation is replaced by a mandatory definition of
  the file names in the EU M1 Specification"; HTG 3.2.4: `cc-form-eaf.pdf` alone, `cc-form-eaf-10mg`/`-20mg` if several; each eAF annex a separate file.
* Path length: ≤180 characters from the first digit of the sequence folder (SPEC p. 13 "EU regional requirement … less than the ICH agreed overall
  path length"; VC 15.3). File and folder names ≤64 characters (VC 15.4, 15.5). Allowed characters a–z, 0–9, hyphen (VC 15.6, 15.7, 11.4).

### 1.4 Pick-lists (SPEC 3.1.1 App. 2.1–2.4, pp. 50–53; VC sheet "Picklist Values")
* **Destination codes (`CC`)**: at be bg **common** cy cz de dk **edqm** ee **el** (Greece – "not an ISO code") **ema** es fi fr hr hu ie is it li lt lu lv mt nl no
  pl pt ro se si sk **uk** ("Not to be used anymore") **xi** (UK Northern Ireland). The DTD entity `%countries;` = the same list; envelope list
  `%env-countries;` = same minus `common`.
* **Language codes (`LL`)**: bg cs da de el en es et fi fr ga hr hu is it lt lv mt nl no pl pt ro sk sl sv (no Arabic — irrelevant for EU).
* **PIDOC** (App. 2.3): `spc` · `annex2` · `outer` · `interpack` (also used "When labelling documents (Outer and Immediate Packaging) are submitted
  as a single file") · `impack` · `other` · `pl` · `combined` (spc+annex2+outer+interpack+impack+other+pl in one file, CP; one file per language).
* **Agency codes** (App. 2.4, pattern `CC-ACRONYM`): AT-BASG, BE-FAMHP, BG-BDA, HR-HALMED, CY-PHS, CZ-SUKL, DK-DKMA, EE-SAM, EU-EDQM, EU-EMA,
  FI-FIMEA, FR-ANSM, DE-BFARM, DE-PEI, EL-EOF, HU-OGYI, IS-IMCA, IE-HPRA, IT-AIFA, LV-ZVA, LI-LLV, LT-SMCA, LU-MINSANT, MT-MEDAUTH, NL-MEB,
  NO-NOMA, PL-URPL, PT-INFARMED, RO-ANMMD, SK-SIDC, SI-JAZMP, ES-AEMPS, SE-MPA, UK-MHRA (= UK(NI) when in an EU eCTD). Identical to the
  `agency code` enumeration in eu-envelope.mod.

### 1.5 Node extensions in EU M1 (SPEC 3.1.1 p. 12; HTG 2.9.8)
Not where ICH sub-headings exist; only at the lowest level; must be kept for the whole lifecycle; may be nested; extra sub-folder optional
("if node extensions are used to further define 'm1-responses', additional folders under 'm1/eu/responses/cc' are not recommended").
HTG 2.9.8: "In Module 1, node extensions should be included to differentiate the responses at different stages of the lifecycle … additional
folders in m1-responses are not allowed". HTG 3.2.6: group responses for one regulatory activity under one node-extension in eu-regional.xml.

---

## 2. eu-regional.xml

### 2.1 Doctype, root, namespaces
* Root element `eu:eu-backbone`, containing exactly `eu-envelope` then `m1-eu` (SPEC 3.1.1 "General Architecture of Module 1", pp. 9–10;
  DTD). Attributes (DTD): `xmlns:eu` FIXED `http://europa.eu.int`, `xmlns:xlink` FIXED `http://www.w3c.org/1999/xlink` (sic, "w3c.org"),
  `xml:lang` optional, **`dtd-version` FIXED `"3.1"`**.
* DTD public identifier (comment at top of eu-regional.dtd): `PUBLIC "-//EU//DTD eCTD EU Backbone 3.1//EN"`, file location `util/dtd/eu-regional.dtd`.
* **Doctype line: no v3.1 instance document exists in the supplied files** (the spec's referenced "annex" of XML examples was not supplied; the only
  instances are the 2009 v1.4 examples, which write `<!DOCTYPE eu:eu-backbone SYSTEM "..\..\util\dtd\eu-regional.dtd">` with back-slashes).
  Derived from the DTD location + VC 9.5 ("reference to the DTD in eu-regional.xml is directed to the DTD provided in the util folder … A valid
  reference means a URI") + SPEC p. 10 (relative references "starting from the location of the XML file"), a current header reads
  (DERIVED, not quoted; validated with xmllint against the v3.1 DTD, see §6.4):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE eu:eu-backbone SYSTEM "../../util/dtd/eu-regional.dtd">
<?xml-stylesheet type="text/xsl" href="../../util/style/eu-regional.xsl"?>
<eu:eu-backbone xmlns:eu="http://europa.eu.int" xmlns:xlink="http://www.w3c.org/1999/xlink" dtd-version="3.1">
```
* "Files can be referred to across modules … or across sequences within the same eCTD application … the reference must always be relative,
  starting from the location of the XML file", e.g. from `0003/m1/eu/eu-regional.xml` to `0000/m2/22-intro/introduction.pdf` =
  `../../../0000/m2/22-intro/introduction.pdf` (SPEC p. 10). Not possible to refer to other eCTD applications (same; HTG 2.9.7).

### 2.2 Verbatim declarations (DTD files in `eu_util_new/util/dtd/`; same text in SPEC App. 3, pp. 54–65)

**eu-regional.dtd** (header comment with contributor list omitted; everything from the first declaration to end of file is verbatim):
```dtd
<!-- General declarations, external modules references................... -->
<!ENTITY % countries "(at|be|bg|common|cy|cz|de|dk|edqm|ee|el|es|ema|fi|fr|hr|hu|ie|is|it|li|lt|lu|lv|mt|nl|no|pl|pt|ro|se|si|sk|uk|xi)">
<!ENTITY % languages "(bg|cs|da|de|el|en|es|et|fi|fr|ga|hr|hu|is|it|lt|lv|mt|nl|no|pl|pt|ro|sk|sl|sv)">

<!ENTITY % leaf-node "(( leaf | node-extension )*)">

<!ENTITY % envelope-module SYSTEM "eu-envelope.mod" >
%envelope-module;

<!ENTITY % leaf-module SYSTEM "eu-leaf.mod" >
%leaf-module;
<!ELEMENT specific (
%leaf-node;
)>
<!ATTLIST specific
country %countries; #REQUIRED
>
<!ELEMENT pi-doc (
%leaf-node;
)>
<!ATTLIST pi-doc
xml:lang %languages; #REQUIRED
type (spc|annex2|outer|interpack|impack|other|pl|combined) #REQUIRED
country %countries; #REQUIRED
>

<!-- Root element ..................................................... -->
<!ELEMENT eu:eu-backbone (
eu-envelope,
m1-eu
)>

<!ATTLIST eu:eu-backbone
xmlns:eu CDATA #FIXED "http://europa.eu.int"
xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
xml:lang CDATA #IMPLIED
dtd-version CDATA #FIXED "3.1"
>

<!-- ................................................................... -->
<!ELEMENT m1-eu (
m1-0-cover,
m1-2-form?,
m1-3-pi?,
m1-4-expert?,
m1-5-specific?,
m1-6-environrisk?,
m1-7-orphan?,
m1-8-pharmacovigilance?,
m1-9-clinical-trials?,
m1-10-paediatrics?,
m1-responses?,
m1-additional-data?
)>

<!-- ................................................................... -->
<!ELEMENT m1-0-cover (
specific+
)>

<!-- ................................................................... -->
<!ELEMENT m1-2-form (
specific+
)>

<!-- ................................................................... -->
<!ELEMENT m1-3-pi (
m1-3-1-spc-label-pl?,
m1-3-2-mockup?,
m1-3-3-specimen?,
m1-3-4-consultation?,
m1-3-5-approved?,
m1-3-6-braille?
)>

<!ELEMENT m1-3-1-spc-label-pl (
pi-doc+
)>
<!ELEMENT m1-3-2-mockup (
specific+
)>
<!ELEMENT m1-3-3-specimen (
specific+
)>
<!ELEMENT m1-3-4-consultation (
specific+
)>
<!ELEMENT m1-3-5-approved (
specific+
)>
<!ELEMENT m1-3-6-braille (
%leaf-node;
)>

<!-- ................................................................... -->
<!ELEMENT m1-4-expert (
m1-4-1-quality?,
m1-4-2-non-clinical?,
m1-4-3-clinical?
)>

<!ELEMENT m1-4-1-quality %leaf-node;>
<!ELEMENT m1-4-2-non-clinical %leaf-node;>
<!ELEMENT m1-4-3-clinical %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-5-specific (
m1-5-1-bibliographic?,
m1-5-2-generic-hybrid-bio-similar?,
m1-5-3-data-market-exclusivity?,
m1-5-4-exceptional-circumstances?,
m1-5-5-conditional-ma?
)>

<!ELEMENT m1-5-1-bibliographic %leaf-node;>
<!ELEMENT m1-5-2-generic-hybrid-bio-similar %leaf-node;>
<!ELEMENT m1-5-3-data-market-exclusivity %leaf-node;>
<!ELEMENT m1-5-4-exceptional-circumstances %leaf-node;>
<!ELEMENT m1-5-5-conditional-ma %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-6-environrisk (
(m1-6-1-non-gmo | m1-6-2-gmo)?
)>
<!ELEMENT m1-6-1-non-gmo %leaf-node;>
<!ELEMENT m1-6-2-gmo %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-7-orphan (
m1-7-1-similarity?,
m1-7-2-market-exclusivity?
)>
<!ELEMENT m1-7-1-similarity %leaf-node;>
<!ELEMENT m1-7-2-market-exclusivity %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-8-pharmacovigilance (
m1-8-1-pharmacovigilance-system?,
m1-8-2-risk-management-system?
)>
<!ELEMENT m1-8-1-pharmacovigilance-system %leaf-node;>
<!ELEMENT m1-8-2-risk-management-system %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-9-clinical-trials %leaf-node;>
<!-- ................................................................... -->

<!ELEMENT m1-10-paediatrics %leaf-node;>

<!-- ................................................................... -->
<!ELEMENT m1-responses (
specific+
)>

<!-- ................................................................... -->
<!ELEMENT m1-additional-data (
specific+
)>
```

**eu-envelope.mod** (v3.1, June 2024; header comment omitted; verbatim to end of file):
```dtd
<!-- ................................................................... -->
<!ELEMENT eu-envelope (
	envelope+
)>

<!ELEMENT envelope (
	identifier,
        submission,
        submission-unit,
	applicant, 
	agency, 
	procedure,
	invented-name+,
	inn*,
	sequence,
	related-sequence+,
	submission-description
)>

<!-- ................................................................... -->
<!ELEMENT identifier            ( #PCDATA )>
<!ELEMENT submission   		( number?, procedure-tracking )>
<!ELEMENT procedure-tracking 	( number+ )>
<!ELEMENT number 		( #PCDATA )>
<!ELEMENT submission-unit 	EMPTY>
<!ELEMENT applicant   		( #PCDATA )>
<!ELEMENT agency		EMPTY>
<!ELEMENT procedure    		EMPTY>
<!ELEMENT invented-name 	( #PCDATA )>
<!ELEMENT inn		        ( #PCDATA )>
<!ELEMENT sequence		( #PCDATA )>
<!ELEMENT related-sequence 	( #PCDATA )>
<!ELEMENT submission-description ( #PCDATA )>

<!-- ................................................................... -->
<!ATTLIST submission
type (maa | var-type1a | var-type1ain | var-type1b | var-type2 | var-nat | extension | rup | psur | psusa | rmp | renewal | pam-sob | pam-anx | pam-mea | pam-leg | pam-sda | pam-capa | pam-p45 | pam-p46 | pam-paes | pam-rec | pass107n | pass107q | asmf | pmf | referral-20 | referral-294 | referral-29p | referral-30 | referral-31 | referral-35 | referral-5-3 | referral-107i | referral-16c1c | referral-16c4 | annual-reassessment | usr | clin-data-pub-rp | clin-data-pub-fv | paed-7-8-30 | paed-29 | paed-45 | paed-46 | article-58 | notification-61-3 | transfer-ma | lifting-suspension | withdrawal | cep | article-18 | none) #REQUIRED
mode ( single | grouping | worksharing ) #IMPLIED
>

<!-- ................................................................... -->
<!ATTLIST submission-unit
type (initial | validation-response | response | additional-info | closing | consolidating | corrigendum | reformat | re-examination ) #REQUIRED
>

<!-- ................................................................... -->
<!ATTLIST agency
code ( AT-BASG | BE-FAMHP | BG-BDA | CY-PHS | CZ-SUKL | DE-BFARM | DE-PEI | DK-DKMA | EE-SAM | EL-EOF | ES-AEMPS | FI-FIMEA | FR-ANSM | HR-HALMED | HU-OGYI | IE-HPRA | IS-IMCA | IT-AIFA | LI-LLV | LT-SMCA | LU-MINSANT | LV-ZVA | MT-MEDAUTH | NL-MEB | NO-NOMA | PL-URPL | PT-INFARMED | RO-ANMMD | SE-MPA | SI-JAZMP | SK-SIDC | UK-MHRA | EU-EMA | EU-EDQM ) #REQUIRED>

<!-- ................................................................... -->
<!ATTLIST procedure
 type (
   centralised
 | national
 | mutual-recognition
 | decentralised
 ) #REQUIRED
>

<!-- ................................................................... -->
<!ENTITY % env-countries "(at|be|bg|cy|cz|de|dk|edqm|ee|el|ema|es|fi|fr|hr|hu|ie|is|it|li|lt|lu|lv|mt|nl|no|pl|pt|ro|se|si|sk|uk|xi)">

<!-- ................................................................... -->
<!ATTLIST envelope country %env-countries; #REQUIRED >

<!-- +++ -->
```

**eu-leaf.mod** (header says "Version 1.4 August 2009 … based on ich-ectd-3-2.dtd"; verbatim):
```dtd
<!-- ============================================================= -->
<!ELEMENT node-extension (title, (leaf | node-extension)+)>
<!ATTLIST node-extension
	ID ID #IMPLIED
	xml:lang CDATA #IMPLIED
>

<!-- ============================================================= -->
<!ENTITY % show-list " (new | replace | embed | other | none) ">
<!ENTITY % actuate-list " (onLoad | onRequest | other | none) ">
<!ENTITY % operation-list " (new | append | replace | delete) ">
<!ENTITY % leaf-element " (title, link-text?) ">
<!ENTITY % leaf-att '
 ID                  ID                #REQUIRED
 application-version CDATA             #IMPLIED
 version             CDATA             #IMPLIED
 font-library        CDATA             #IMPLIED
 operation           %operation-list;  #REQUIRED
 modified-file       CDATA             #IMPLIED
 checksum            CDATA             #REQUIRED
 checksum-type       CDATA             #REQUIRED
 keywords            CDATA             #IMPLIED
 xmlns:xlink         CDATA             #FIXED    "http://www.w3c.org/1999/xlink"
 xlink:type          CDATA             #FIXED    "simple"
 xlink:role          CDATA             #IMPLIED
 xlink:href          CDATA             #IMPLIED
 xlink:show          %show-list;       #IMPLIED
 xlink:actuate       %actuate-list;    #IMPLIED
 xml:lang            CDATA             #IMPLIED
 '>

<!ELEMENT leaf %leaf-element;>
<!ATTLIST leaf
	%leaf-att; 
>
<!ELEMENT title (#PCDATA)>
<!ELEMENT link-text (#PCDATA | xref)*>

<!ELEMENT xref EMPTY>
<!ATTLIST xref
	ID ID #REQUIRED
	xmlns:xlink CDATA #FIXED "http://www.w3c.org/1999/xlink"
	xlink:type CDATA #FIXED "simple"
	xlink:role CDATA #IMPLIED
	xlink:title CDATA #REQUIRED
	xlink:href CDATA #REQUIRED
	xlink:show %show-list; #IMPLIED
	xlink:actuate %actuate-list; #IMPLIED
>

<!-- +++ -->
```
(Header comment omitted; rest verbatim to end of file.)

### 2.3 Envelope elements — meaning, constraints and the rules that test them
(SPEC 3.1.1 "Envelope" pp. 10–11 and App. 1.1 pp. 16–29; HTG 3.2.2; VC rule IDs)

| Element / attribute | Card. (DTD) | EU rule | VC |
|---|---|---|---|
| `envelope/@country` | 1 per envelope | CP: a single envelope `ema`; MRP/DCP/NP: one envelope per receiving Member State; `common` "cannot be used in the envelope"; EDQM: `edqm`; a CMS receiving "for information only" gets no envelope (SPEC p. 10; HTG 3.2.2). *SPEC p. 10 says "country attribute value set to 'EU-EMA'" but DTD/HTG/VC use `ema` — internal inconsistency in the spec.* | 14.1–14.5, 14.BP3 |
| `identifier` | 1 | UUID per ISO/IEC 11578:1996 and ITU-T X.667 \| ISO/IEC 9834-8:2005, form `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`, version 4 recommended, machine generated, same for the whole lifecycle, kept on MAH transfer/RMS change; new UUID only for split/merge or full re-baseline (SPEC "UUID" pp. 13–15; HTG 2.9.1, 2.11.3) | 9.7, 9.8, 9.9 |
| `submission/@type` | 1, required | regulatory-activity type, 52 values (list in 2.2), from RMS 100000155688; "Roman numerals are used for variations … the elements must remain Arabic"; several types in one sequence → highest variation type | — (DTD validity 9.4) |
| `submission/@mode` | optional | `single`/`grouping`/`worksharing`; only variation, extension, worksharing (HTG: also PSUSA) activities, "must be included in every sequence of that activity"; all PSUSA = worksharing | 14.BP4, 14.BP5, 14.BP7, 14.BP8 |
| `submission/number` | 0..1 | high-level number for worksharing / super-grouping of IA variations across MAs (3.1.1: `EMA/VR/xxxxxxxxxx`); empty for single-MA grouping and PSUSA; "to be advised"/"xxxx" if not yet known | 14.BP4, 14.BP5 |
| `submission/procedure-tracking/number` | 1..n | "at least one tracking number identified from the regulators", plus optional applicant number; examples MRP `DE/H/0126/001/MR`, NP `2131577`, CP `EMEA/H/C/000123`, licence `EU/1/00/44/0003 – 0004`, `PL01234/0003-0004`, PSUSA `PSUSA/00123456/201709`; "to be advised" if not allocated | 14.BP6 |
| `submission-unit/@type` | 1, required | initial · validation-response · response · additional-info · closing · consolidating · corrigendum · reformat · re-examination (definitions App. 1.1 p. 22) | 14.6, 14.7 |
| `applicant` | 1 | company name, spelled consistently (HTG 3.2.2) | — |
| `agency/@code` | 1, required | App. 2.4 code | — |
| `procedure/@type` | 1, required | centralised · national · mutual-recognition · decentralised (RMS 100000154442) | 14.1–14.4, 14.9 |
| `invented-name` | 1..n | product name; a simple entry suffices when the eCTD covers several strengths/forms (HTG 3.2.2) | — |
| `inn` | 0..n | INN; required for `maa`+`initial` | 14.8 |
| `sequence` | 1 | 0000, 0001 …; must equal the folder name, cover letter, CESP/Gateway delivery data | 13.1–13.3 |
| `related-sequence` | 1..n | = own number for `initial` and `reformat`; otherwise the sequence that started the activity; >1 when one sequence answers several activities | 14.6, 14.7 |
| `submission-description` | 1 | free text, e.g. "Response to D120 LOQ" | — |

Related-sequence worked tables: SPEC App. 1.1 pp. 24–30 (MAA/var/extension 0000–0010, Tables 1–3 CP/DCP/variation, referral-31 envelopes for EMA and CZ,
reformat 0000–0003, withdrawal 0011–0016); HTG 2.9.5 Tables 1–4, 2.11 Tables 6–7.

### 2.4 Leaf rules
| Rule | Source |
|---|---|
| EU leaf = ICH leaf ("identical to the leaf element described in the ICH eCTD DTD; reference is made to Table 6-8 of the ICH eCTD Specification") | SPEC p. 10 |
| `ID` unique within a sequence; `title` not empty; node-extension `title` not empty | VC 11.11, 11.3, 12.1 |
| `checksum-type` = md5/MD5; checksum must regenerate | VC 11.1, 11.2 |
| `operation` new/replace/append → `xlink:href` required (legal chars a–z 0–9 hyphen); delete → no href; target must exist in this or an earlier sequence of the same application | VC 11.4, 11.5, 11.6 |
| `modified-file` required for replace/delete/append, absent for new; target must exist earlier; same CTD section (incl. section-defining attributes country, xml:lang, type, substance, manufacturer, product-name, dosageform, indication — HTG 2.9.6 Table 5); a file can be replaced/deleted only once | VC 11.7–11.10, 11.12, 11.BP1, 11.BP2 |
| `append` to be avoided in the EU | HTG 2.9.6 |
| eu-regional.xml leaf operation "should always be set to 'new'" | SPEC App. 2 row 2 |
| Cover letter always `new`; application form `new` (or `replace` to correct it); descriptive leaf titles ("Cover Letter for France for Type II Variation 028 (0042)") | HTG 3.2.3.1, 3.2.4 |
| Backbone attributes (e.g. manufacturer, country, language, PI type) cannot be updated during lifecycle — keep the obsolete entry | SPEC "Updating backbone attributes/metadata" p. 9 |
| No placeholder "no relevant content" documents; justify absence in cover letter / M2 | SPEC "Handling of Empty or Missing eCTD Sections" p. 9; HTG 3.2.1 |

### 2.5 How index.xml references eu-regional.xml
* ICH DTD (`ich-ectd-3-2.dtd` line 117): `<!ELEMENT m1-administrative-information-and-prescribing-information (leaf*)>` — Module 1 in index.xml is just
  leaves; the EU regional backbone is one `leaf` there pointing at `m1/eu/eu-regional.xml`.
* Real instance (EX ex2-NPv1.0/0012/index.xml, quoted in §6.2): `<leaf ID="eum1" operation="new" checksum="…" checksum-type="md5" xlink:href="m1/eu/eu-regional.xml"><title>EU Module 1</title></leaf>`.
* The index.xml must reference the ICH DTD and ICH stylesheet in `util/` (VC 7.4–7.6); index-md5.txt holds the MD5 of index.xml (VC 8.3).
  eu-regional.xml must reference `util/dtd/eu-regional.dtd` and `util/style/eu-regional.xsl` (VC 9.5, 9.6) and sit in `/XXXX/m1/eu` (VC 9.1–9.2).
* *The supplied EU files do not themselves state the rule "index.xml must contain a leaf to eu-regional.xml"; that is shown only by the ICH DTD content
  model and the example.*

---

## 3. EU eCTD Validation Criteria v8.2 (VC, June 2025)

### 3.1 Categories (VC sheet "eCTD Validation Criteria", rows 114–116, verbatim condensed)
* **P/F – Pass/Fail**: "eCTDs that fail to meet one or more of these criteria will be returned to the applicant for fixing and resubmission as the
  same sequence number. The pass/fail category has been introduced for the possibility of future automation of eCTD validation."
* **BP – Best Practice**: "Any deviation from the criterion should always be reported by the validating tool … eCTDs that fail to meet one or more of
  these criteria will still be accepted by the agency during technical validation and it is possible that agencies may not even check these
  criteria … Users of the validation tool should also be able to check the eCTD without checking for the Best Practice criteria."
* **'Y' (column "Lifecycle needed?")**: needs the relevant former sequences to be present; "any FAIL results for these criteria should be
  interpreted carefully"; tools should report the missing sequences.
* Count: **111 criteria = 83 P/F + 28 BP** (counted from the sheet). `XXXX` = sequence folder.
* v8.2 changes (sheet "Document Change Control", 2025-05-01): clarifications 14.BP5/14.BP7 (super-grouping); 15.11/15.12 no tracking table for EDQM;
  16.6 how to tell PLM-Portal eAFs from interactive-PDF eAFs; **new 16.7**. v8.1 (2024-09): checksums in 3.3/4.3/5.3/6.3 updated to v3.1 files;
  16.BP11 folder 1.3 → 1.3.1. v8.0 (2024-06) major version.
* Numbering gaps as published: there is no 14.BP1/14.BP2, no 15.1/15.2 (renamed 15.BP1.1/15.BP2.1 in v7.2). HTG 2.4 still cites "validation
  criterion 14 BP2", which **does not exist in v8.2** (14.6/14.7 carry the related-sequence rule and are now P/F).

### 3.2 All criteria (verbatim; LC = "Lifecycle needed? Y")

| ID | Group | Type | LC | Criterion (verbatim) | Comment (verbatim) |
|---|---|---|---|---|---|
| 1.1 | ICH DTD | **P/F** |  | The specified filename is used | File is named ich-ectd-3-2.dtd |
| 1.2 | ICH DTD | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/dtd |
| 1.3 | ICH DTD | **P/F** |  | A currently acceptable version of the DTD is used (checksum matches the published value) | Currently acceptable versions are described in the current ICH eCTD Specification. (The checksum for the DTD in eCTD v3.2 (ich-ectd-3-2.dtd) is 1d6f631cc6b6357f0f4fe378e5f79a27) |
| 1.4 | ICH DTD | **P/F** | Y | The version number of the DTD/specification used in the sequence being tested is higher than or equal to the version of the DTD used in the sequence numerically preceding the incoming sequence in the eCTD lifecycle. | With reference to any transition guidance, going back to an earlier version is not allowed when a newer version has already been used for that eCTD. ‘The sequence numerically preceding the incoming sequence in the eCTD lifecycle‘ refers to the highest numbered sequence that is numerically lower than the incoming sequence. The criterion should only be tested if there are sequences with lower sequence numbers present. |
| 1.5 | ICH DTD | **P/F** | Y | The version number of the DTD/specification used in the sequence being tested is lower than or equal to the version of the DTD used in the sequence numerically succeeding the incoming sequence in the eCTD lifecycle. | This rule specifically tests in situations where sequences have been submitted out of order. ‘The sequence numerically succeeding the incoming sequence in the eCTD lifecycle‘ refers to the lowest numbered sequence that is numerically higher than the incoming sequence. The criterion should only be tested if there are sequences with higher sequence numbers present. |
| 2.1 | ICH stylesheet | **P/F** |  | The specified filename is used | File is named ectd-2-0.xsl |
| 2.2 | ICH stylesheet | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/style |
| 2.3 | ICH stylesheet | **P/F** |  | The checksum for the stylesheet used must match the published checksum for the stylesheet associated with the DTD used for the sequence | For example, the checksum corresponding to the stylesheet from eCTD specification v3.2 (ectd-2-0.xsl) is 3a07a202455e954a2eb203c5bb443f77 |
| 3.1 | EU M1 DTD | **P/F** |  | The specified filename is used | File is named eu-regional.dtd |
| 3.2 | EU M1 DTD | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/dtd |
| 3.3 | EU M1 DTD | **P/F** |  | A currently acceptable version of the DTD is used (checksum matches the published value) | Currently acceptable with reference to any transition guidance (Refer to http://esubmission.ema.europa.eu/eumodule1/index.htm). For example, the checksum for the DTD for EU m1 v3.1 is f8e473246d58499f9ffff8e51a32380d |
| 3.4 | EU M1 DTD | **P/F** | Y | The version number of the DTD/specification used in the sequence being tested is higher than or equal to the version of the DTD used in the sequence numerically preceding the incoming sequence in the eCTD lifecycle. | With reference to any transition guidance, going back to an earlier version is not allowed when a newer version has already been used for that eCTD. ‘The sequence numerically preceding the incoming sequence in the eCTD lifecycle‘ refers to the highest numbered sequence that is numerically lower than the incoming sequence. For example if 0109 used DTD 1.4, 0110 was DTD 2.0, and 0111 is not present, then 0112 must be built in either DTD 2.0 or higher. The criterion should only be tested if there are sequences with lower sequence numbers present. |
| 3.5 | EU M1 DTD | **P/F** | Y | The version number of the DTD/specification used in the sequence being tested is lower than or equal to the version of the DTD used in the sequence numerically succeeding the incoming sequence in the eCTD lifecycle. | This rule specifically tests in situations where sequences have been submitted out of order. ‘The sequence numerically succeeding the incoming sequence in the eCTD lifecycle‘ refers to the lowest numbered sequence that is numerically higher than the incoming sequence. For example if 0010 used DTD 1.4, and 0012 was DTD 2.0, then 0011 must be built in either DTD 2.0 or 1.4. The criterion should only be tested if there are sequences with higher sequence numbers present. |
| 4.1 | EU M1 leaf MOD file | **P/F** |  | The specified filename is used | File is named eu-leaf.mod |
| 4.2 | EU M1 leaf MOD file | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/dtd |
| 4.3 | EU M1 leaf MOD file | **P/F** |  | The checksum for the eu-leaf.mod file used must match the published checksum for the eu-leaf.mod file associated with the DTD used for the sequence | For example, the checksum for eu-leaf.mod from EU eCTD Module 1 v3.1 is 23B854174E61C68044B9F53C0009AF95 |
| 5.1 | EU M1 envelope MOD file | **P/F** |  | The specified filename is used | File is named eu-envelope.mod |
| 5.2 | EU M1 envelope MOD file | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/dtd |
| 5.3 | EU M1 envelope MOD file | **P/F** |  | The checksum for the eu-envelope.mod file used must match the published checksum for the eu-envelope.mod file associated with the DTD used for the sequence | For example, the checksum for eu-envelope.mod from EU eCTD Module 1 v3.1 is cf059a8f48c68fe4ce9ad2947ab854ca . |
| 6.1 | EU M1 stylesheet | **P/F** |  | The specified filename is used | File is named eu-regional.xsl |
| 6.2 | EU M1 stylesheet | **P/F** |  | The file is placed in the correct folder | In the folder /XXXX/util/style |
| 6.3 | EU M1 stylesheet | **P/F** |  | The checksum for the stylesheet used must match the published checksum for the stylesheet associated with the DTD used for the sequence | For example, the checksum for the stylesheet from EU eCTD Module 1 v3.1 is 474f3fe1fdadb31c74477793e060383d |
| 7.1 | Index XML | **P/F** |  | The file is placed in the correct folder | The root folder /XXXX |
| 7.2 | Index XML | **P/F** |  | The file is named correctly | File is named index.xml |
| 7.3 | Index XML | **P/F** |  | The file is well formed | Well formed with respect to the rules of the XML specification |
| 7.4 | Index XML | **P/F** |  | The file is valid | Valid with respect to the ICH eCTD DTD file included in the util/dtd folder |
| 7.5 | Index XML | **P/F** |  | The reference to the DTD in index.xml is directed to the DTD provided in the util folder. | This is the ICH DTD in /XXXX/util/dtd, and tested for validity by rules 1.1 - 1.5. A valid reference means a URI - see http://www.w3.org/TR/xml/ and http://www.ietf.org/rfc/rfc3986.txt (version 2005 page 22, section 3.3). |
| 7.6 | Index XML | **P/F** |  | The reference to the stylesheet in index.xml is directed to the stylesheet provided in the util folder. | This is the ICH stylesheet in /XXXX/util/style and tested for validity by rules 2.1 - 2.3. A valid reference means a URI - see http://www.w3.org/TR/xml/ and http://www.ietf.org/rfc/rfc3986.txt (version 2005 page 22, section 3.3). |
| 8.1 | Index MD5 txt | **P/F** |  | The file is placed in the correct folder | The root folder /XXXX |
| 8.2 | Index MD5 txt | **P/F** |  | The file is named correctly | The file is named index-md5.txt |
| 8.3 | Index MD5 txt | **P/F** |  | The regenerated checksum for the index.xml matches the value in the file index-md5.txt. |  |
| 9.1 | EU regional XML | **P/F** |  | The file is placed in the correct folder | The folder /XXXX/m1/eu |
| 9.2 | EU regional XML | **P/F** |  | The file is named correctly | File is named eu-regional.xml |
| 9.3 | EU regional XML | **P/F** |  | The file is well formed | Well formed with respect to the rules of the XML specification |
| 9.4 | EU regional XML | **P/F** |  | The file is valid | Valid with respect to the EU Module 1 DTD file included in the util/dtd folder. |
| 9.5 | EU regional XML | **P/F** |  | The reference to the DTD in eu-regional.xml is directed to the DTD provided in the util folder. | This is the EU Regional DTD in /XXXX/util/dtd, and tested for validity by rules 3.1-3.5. A valid reference means a URI - see http://www.w3.org/TR/xml/ and http://www.ietf.org/rfc/rfc3986.txt (version 2005 page 22, section 3.3) |
| 9.6 | EU regional XML | **P/F** |  | The reference to the stylesheet in eu-regional.xml is directed to the stylesheet provided in the util folder. | This is the stylesheet in /XXXX/util/style, and tested for validity by rules 6.1-6.3. A valid reference means a URI - see http://www.w3.org/TR/xml/ and http://www.ietf.org/rfc/rfc3986.txt (version 2005 page 22, section 3.3). |
| 9.7 | EU regional XML | **P/F** |  | The UUID is well formed according to ISO/IEC 11578:1996 and ITU-T Rec X.667 \| ISO/IEC 9834-8:2005 | This criterion will test whether the UUID is well formed. |
| 9.8 | EU regional XML | **P/F** | Y | If the sequence already submitted numerically preceding the incoming sequence in the eCTD lifecycle contains a UUID (i.e. was submitted using v3.0 of the EU m1 Specification or higher), then the UUID in this incoming sequence must be identical to the one in the previous sequence. | This rule checks that the UUID is correct and the sequence is being loaded into the correct eCTD Application. |
| 9.9 | EU regional XML | **P/F** |  | The UUID must be identical in all envelopes. | The UUID is unique for each Dossier and is identical with the most recent sequence sent. |
| 10.1 | Submission Structure | **P/F** |  | All the lowest level heading elements in the XML (including node-extensions) included in the submission contain at least one leaf |  |
| 11.1 | leaf attributes | **P/F** |  | The leaf attribute 'checksum-type' has a value of md5 or MD5 | Note that this value is not case sensitive. |
| 11.2 | leaf attributes | **P/F** | Y | The regenerated checksum for each file matches the value in the leaf attribute 'checksum' | Note that if the content file is in an earlier sequence within the same eCTD application then the checksum can only be regenerated if access to this file is available. The MD5 checksum is not case sensitive. |
| 11.3 | leaf attributes | **P/F** |  | For every leaf the 'title' attribute is not empty |  |
| 11.4 | leaf attributes | **P/F** |  | All leaves with an operation attribute value of new, replace or append must have a value for the cross reference (xlink:href) | The value for the cross reference (xlink:href) should be valid, and not contain any illegal characters. (Legal characters are lower case characters a-z, digits 0-9 and hyphens, as documented in the ICH eCTD specification). A valid reference means a URI - see http://www.w3.org/TR/xml/ and http://www.ietf.org/rfc/rfc3986.txt (version 2005 page 22, section 3.3). |
| 11.5 | leaf attributes | **P/F** |  | All leaves with an operation attribute value of delete must have no value for the cross reference (xlink:href) | The attribute does not need to be included, or can be declared but with a null value. |
| 11.6 | leaf attributes | **P/F** | Y | The file referenced by the cross reference (xlink:href) must exist in the same or a previously submitted sequence within the same eCTD application | The link within the XML leaf element is valid, i.e. the target exists. |
| 11.7 | leaf attributes | **P/F** |  | All leaves with an operation attribute value of replace, delete or append must have a value for modified-file | Note - it is recommended that the tracking table is always provided with the operation attribute of 'new', due to national sequences in MRP/DCP. |
| 11.8 | leaf attributes | **P/F** |  | All leaves with an operation attribute value of new must have no value for modified-file | The attribute does not need to be included, or can be declared but with a null value. |
| 11.9 | leaf attributes | **P/F** | Y | The leaf referenced by the modified file must exist in a previously submitted sequence within the same eCTD application. Applies to all leaves except for those with a specific country attribute: m1-0-cover m1-2-form m1-3-1-spc-label-pl m1-3-2-mockup m1-3-3-specimen m1-3-4-consultation m1-3-5-approved m1-responses m1-additional-data | This test applies to all procedures. 'common', 'ema', or 'edqm' are not considered to be country specific attributes. However, in common MRP/DCP sequences, replacing previously submitted national content also in other modules can result in a fail according to this criterion in other member states. Therefore, unless a technical solution to prevent this from occurring is available in the eCTD Building tool, applicants should avoid replacing, deleting or appending to content submitted in national sequences (other than the first national phase before MRP), and vice versa. |
| 11.10 | leaf attributes | **P/F** | Y | For all leaves (except leaves within node extensions and leaves in module 3.2.A) with an operation attribute value of replace, delete or append, the modified file must be present in the same CTD section of the dossier. Note: Using the operation attribute 'delete' to remove content placed in m1-additional-data is exempt from this rule. | 'Same CTD section' refers to the position in the table of contents. Sections are defined by the CTD and also by attributes in the eCTD. For example, applicants cannot replace content in the application form section with revised content that is being provided in the cover letter section. eCTD attributes also create applicant defined sections. For example, each 'substance' or 'manufacturer' attribute in m3-2-s-drug-substance, or 'product-name' attribute in m3-2-p–drug-product will create a new CTD section, and lifecycle between these sections is also not allowed. For further details refer to Section 2.9.6 on page 13 of the Harmonised Technical Guidance for eCTD Submissions in the EU. Due to inconsistency between tools how attributes are handled in the past, attributes in module 3.2.A should be allowed to be edited or not automatically copied. To avoid unnecessary errors these modules are exempt as well. |
| 11.11 | leaf attributes | **P/F** |  | Two leaf elements should not have the same leaf ID. | ID must be unique within each sequence. |
| 11.12 | leaf attributes | **P/F** | Y | For all leaves with an operation attribute value of replace, delete or append the modified file must not have been replaced or deleted by any other leaf element in any sequence including the current one. | Documents can be replaced or deleted just once. The modified file must not have been subject to another replace or delete operation in any of the available sequences. |
| 11.BP1 | leaf attributes | **BP** | Y | The leaf referenced by the modified file must exist in a previously submitted sequence within the same eCTD application. Applies to all leaves with a specific country attribute, i.e. m1-0-cover m1-2-form m1-3-1-spc-label-pl m1-3-2-mockup m1-3-3-specimen m1-3-4-consultation m1-3-5-approved m1-responses m1-additional-data | In common MRP/DCP sequences, replacing previously submitted national content can result in a fail according to this criterion in other member states. Therefore, unless a technical solution to prevent this from occurring is available in the eCTD Building tool, applicants should avoid replacing, deleting or appending to content submitted in national sequences (other than the first national phase before MRP), and vice versa. 'common', 'ema', or 'edqm' are not considered to be country specific attributes. |
| 11.BP2 | leaf attributes | **BP** | Y | For all leaves within node extensions or module 3.2.A with an operation attribute value of replace, delete or append, the modified file should be present in the same node extension or attribute-defined section. | The definition of ‘same CTD section’ is as in criterion 11.10. If the node extension is not in the same section the criterion 11.10 still applies. |
| 11.BP3 | ICH Attributes | **BP** | Y | ICH attributes must not contain leading or trailing spaces, nor start or end with hyphens. | The problem is with attributes in the XML that define re-useable sections. Hyphens or spaces at the beginning or end of a attribute name are not allowed. |
| 12.1 | Node extensions | **P/F** |  | For every node-extension the 'title' attribute is not empty |  |
| 13.1 | Sequence number | **P/F** |  | The sequence folder name is a 4 digit number | i.e. numbers between 0000 and 9999 |
| 13.2 | Sequence number | **P/F** | Y | The sequence number (folder name) has not already been used |  |
| 13.3 | Sequence number | **P/F** |  | The sequence folder name matches the sequence number in each envelope in eu-regional.xml |  |
| 14.1 | Envelope Attributes | **P/F** |  | There is a single envelope with the country attribute value of 'ema' if the procedure type is 'centralised' and the submission type is not 'cep'. | This should be 'ema'. |
| 14.2 | Envelope Attributes | **P/F** |  | There are one or more country specific envelopes if the procedure type is 'mutual-recognition' or 'decentralised'. | The country attribute value must not be 'ema' or 'common' or 'edqm'. |
| 14.3 | Envelope Attributes | **P/F** |  | There is a single country specific envelope if the procedure type is 'national' . | The country attribute value must not be 'ema' or 'common' or 'edqm'. |
| 14.4 | Envelope Attributes | **P/F** |  | There is a single envelope with the country attribute value of edqm if it is the submission type of cep. | This should be 'edqm'. It is expected to use 'centralised' as the procedure type (see criterion 14.9). |
| 14.5 | Envelope Attributes | **P/F** |  | For every country attribute (except 'common') used in country specific leaves with the operation attribute, 'new', 'replace' or 'append' , there is an EU envelope with a matching country attribute value. | Even if no content is specific to that country there must still be an EU envelope for each country receiving an MRP/DCP/NP submission. However, note that there is not a test for this scenario. For CP submissions, there must only be 'ema' or 'common' leaf attribute and a corresponding 'ema' envelope (see 14.1). This rule should not apply to documents in country specific leaves with 'delete' operation attributes. Refer to 14BP3. |
| 14.6 | Envelope Attributes | **P/F** |  | If the submission unit type is ‘initial’ or ‘reformat' then the related-sequence attribute must have a value equal to the current sequence. | Refer to EU m1 specification. When submitting a first submission initialising a regulatory activity or proving a reformatted application, the related sequence attribute should be populated with the same number of that current sequence. Due to some inconsistencies of implementation the criterion is now be considered as P/F. |
| 14.7 | Envelope Attributes | **P/F** |  | If the submission unit type is not equal to ‘initial’ or ‘reformat' then the entry for related sequence must not be equal to the value for the current sequence. | Refer to EU m1 specification. When submitting additional lifecycle sequences within an ongoing regulatory activity, the related sequence attribute should be populated with the number of the sequence that started this regulatory activity. Due to some inconsistencies of implementation the criterion is now be considered as P/F. |
| 14.8 | Envelope Attributes | **P/F** |  | If he submission type is 'maa' and the submission unit type is 'initial' the INN attribute is required | It is the intent to assure the INN data field is completed. It is strongly recommended to re-use the active ingredient name as of the application form. Separation of multiple names by colon. |
| 14.9 | Envelope Attributes | **P/F** |  | The procedure type is ‘centralised’ if the country attribute value is ‘edqm’. | The procedure type should be ‘centralised’ for EDQM. |
| 14.BP3 | Envelope Attributes | **BP** |  | For every country attribute (except 'common') used in country specific leaves with the operation attribute, ‘delete' , there is an EU envelope with a matching country attribute value. | Even if no content is specific to that country there must still be an EU envelope for each country receiving an MRP/DCP/NP submission. If there is a need for removal of earlier content that has erroneously been attributed to a particular country in the leaf metadata without provision of a corresponding envelope entry, then this BP error should be ignored. |
| 14.BP4 | Envelope Attributes | **BP** |  | If submission mode is set to either 'grouping' or 'worksharing' and submission type is not 'psusa' there should be a Number element. | This is the optional element for a high-level submission number, either a ‘worksharing’ number, or the high-level submission number to be used when grouping Type IA variations for multiple marketing authorisations (superg-rouping). Refer to EU m1 Specification and validation criteria 14BP7 and 14BP8. |
| 14.BP5 | Envelope Attributes | **BP** |  | If submission mode is not set to either 'grouping' or 'worksharing' there should not be a Number element in the envelope. | This is the optional element for a high-level submission number, either a ‘worksharing’ number, or the high-level submission number to be used when grouping Type IA variations for multiple marketing authorisations (super-grouping). Therefore, it should not be provided if the mode is not set to ‘grouping’ or ‘worksharing’. Refer to EU m1 Specification. |
| 14.BP6 | Envelope Attributes | **BP** |  | The procedure-tracking element of the envelope should be filled in with the procedure number for the regulatory activity if available |  |
| 14.BP7 | Envelope Attributes | **BP** |  | When submission mode = grouping, submission type must be one of: 'var-type1a', 'var-type1ain', or 'var-type1b', or 'var-type2'; or 'extension'. | Mode grouping refers to; super-grouping where only var-type1a and var-type1ain can be selected and to grouping of multiple different scopes for the single product. |
| 14.BP8 | Envelope Attributes | **BP** |  | When submission mode = ‘worksharing’, submission type must be one of: 'var-type1b', or 'var-type2', or 'psusa'. |  |
| 15.BP1.1 | Files/Folders | **BP** |  | The files provided in the folders for Module 1 are in acceptable formats | Refer to the Acceptable file formats for EU Module 1 |
| 15.BP2.1 | Files/Folders | **BP** |  | The files provided in the folders for Module 2-5 are in acceptable formats | Refer to the Acceptable file formats for EU Module 1 |
| 15.3 | Files/Folders | **P/F** |  | Total file folder path length must not exceed 180 characters | Counting starts from the first digit of the sequence number in the sequence number folder name, and includes the filename. |
| 15.4 | Files/Folders | **P/F** |  | File names, including the extension, must not exceed 64 characters |  |
| 15.5 | Files/Folders | **P/F** |  | Folder names must not exceed 64 characters |  |
| 15.6 | Files/Folders | **P/F** |  | Only valid characters are used in file names | Lower case characters a-z, digits 0-9 and hyphens are allowed (as documented in the ICH eCTD specification). This test should only be applied to the file names in the file system, for checks on the XML see test 11.4. |
| 15.7 | Files/Folders | **P/F** |  | Only valid characters are used in folder names | Lower case characters a-z, digits 0-9 and hyphens are allowed (as documented in the ICH eCTD specification). This test should only be applied to the folder names in the file system, for checks on the XML see test 11.4. |
| 15.8 | Files/Folders | **P/F** |  | There are no unreferenced files in M1, M2, M3, M4 and M5 folders | Including all subfolders within the m1-m5 folders but excluding ‘util’ folder and subfolders |
| 15.9 | Files/Folders | **P/F** |  | The only files in the sequence folder (/XXXX/…) are the index.xml and index-md5.txt |  |
| 15.10 | Files/Folders | **P/F** |  | There are no empty folders |  |
| 15.11 | Files/Folders | **P/F** |  | For all procedure types, except for EDQM submissions, the tracking table file is present in the correct location | The folder is: /XXXX/m1/eu/10-cover/ema (for CP) /XXXX/m1/eu/10-cover/common (for MRP/DCP) /XXXX/m1/eu/10-cover/cc ('cc' being the actual country code for NP) There is no tracking table for EDQM submissions |
| 15.12 | Files/Folders | **P/F** |  | For all relevant procedure types, the tracking table file is correctly named | File is named common-tracking-var.pdf ('common' is the appropriate value for 'cc' in MRP/DCP) File is named ema-tracking-var.pdf ('ema' is the appropriate value for 'cc' in CP) File is named cc-tracking-var.pdf ('cc' being the actual country code for NP) Note that the use of XML format for the Tracking table is not acceptable, since there is no longer a valid EU standard to use for this format. There is no tracking table for EDQM submissions |
| 15.BP1 | Files/Folders | **BP** |  | Individual files (except for video files) do not exceed 500 MB in size | Any deviation should always be reported by the validating tool. Files larger than 500 MB should be avoided due to potential archiving issues and to make the assessment easier. |
| 15.BP2 | Files/Folders | **BP** |  | The recommended folder structure and folder names in the ICH and EU specifications are used | Any deviation, including additional subfolders, should always be reported by the validating tool. Although navigation of an eCTD is typically carried out via the XML backbone, it is also helpful if the underlying files and folders follow the ICH and EU naming guidance. |
| 15.BP3 | Files/Folders | **BP** |  | The recommended file names from the ICH and EU specifications are used for all files | Any deviation should always be reported by the validating tool. Note that the components of the file names in italics in Appendix 4 of the ICH eCTD specification are to be specified by the applicant (i.e. this is variable text). For ASMFs or MAA using an ASMF, it is recommended that the RP and AP are used in the same way for NeeS and eCTD and therefore it is now recommended to use RP and AP as suffix also for eCTD, even if this contradicts the current version of the 'Practical guidelines on the use of the eCTD format for ASMFs for active substance master file holders and marketing authorisation holders'. A Q&A on this is published and the guidance document itself will be updated in due course. However, for now, any BP error due to the use of 'rp' or 'ap' as a prefix should be ignored. The CC code of the filename should not be checked against the CC of the leaf attribute or the folder name. The potential presence of STF files in m4 or m5 should not be tested. Although navigation of an eCTD is typically carried out via the XML backbone, it is also helpful if the underlying files and folders follow the ICH and EU naming guidance. |
| 15.BP4 | Files/Folders | **BP** |  | For all leaves in sections m1-0-cover, m1-2-form, m1-3-1-spc, m1-3-2-mockup, m1-3-3-specimen, m1-3-4-consultation, m1-3-5-approved, m1-responses and m1-additional-data, the folder name in the xlink:href matches the specific country attribute in the XML leaf. | This criterion will check whether the country codes are used consistently. |
| 15.BP5 | Files/Folders | **BP** |  | For all leaves in sections m1-0-cover, m1-2-form, m1-3-1-spc, m1-3-2-mockup, m1-3-3-specimen, m1-3-4-consultation, m1-3-5-approved, m1-responses and m1-additional-data, the file name in the xlink:href matches the specific country attribute in the XML leaf. | This criterion will check whether the country codes are used consistently. |
| 15.BP6 | Files/Folders | **BP** |  | Individual video files do not exceed 1GB in size | Any deviation should always be reported by the validating tool. Video files larger than 1GB should be avoided due to potential archiving issues and to make the assessment easier. |
| 16.1 | PDF Files | **P/F** |  | No PDF has been created and saved as version 1.3 or earlier | PDF 1.3 or earlier is not acceptable for technical reasons. No exceptions will be made. For example, if a literature reference is received in PDF 1.3 or earlier, then the applicant must provide it in PDF 1.4, 1.5, 1.6 or 1.7, even if this means copying the full text into a new document or even getting a paper copy and scanning it. Further guidance is provided about the best ways to check the PDF version in the comment to rule 16.BP1. |
| 16.2 | PDF Files | **P/F** |  | There is no security setting to open any individual file | This includes passwords, certificate security, or adobe policy server settings. This test should not be used to test for corrupted files, instead see 16.5. |
| 16.3 | PDF Files | **P/F** |  | There are no further security settings applied to any individual file (except for files in Modules 1.0, 1.2, 3.3, 4.3 and 5.4). | All 'restrictions' should be 'allowed' when viewing the Document Preferences > Security settings. This includes any of the following document restrictions: printing, changing the document, document assembly, content copying, content copying for accessibility, page extraction, filling of form fields, signing, creation of template pages. This validation criterion does not apply to and will not reject certified or any other type of digitally signed documents. Specific security settings of files in m1.0 and m1.2 are tested in criterion 16.4. |
| 16.4 | PDF Files | **P/F** |  | Individual files in section 1.0 and 1.2 have no security settings except for the following: Changing the document Document assembly Page extraction Commenting Creation of template pages | These limited security settings are allowable for the application form, because they are necessary for the functioning of the eAF and similar forms such as e.g the PAM form. |
| 16.5 | PDF Files | **P/F** |  | The submission does not contain corrupted files | This can be achieved by opening a PDF file in software which is compliant to ISO 32000-1; if the file opens without error, the PDF file is considered to be conformant. Absence of detection of conformance means corrupted PDF. |
| 16.6 | PDF Files | **P/F** |  | eAFs generated in the PLM Portal need to have the FHIR XML attached. The interactive pdf eAFs (from eSubmissions website) must not contain any attachments. | For easier identification of the PLM Portal web-based eAFs vs the interactive pdf eAF, the following details may help; For the eAFs generated from the PLM Portal that have not been altered further by any other tool, in the document properties the name of the application is: PDF generator and the author is 'European Medicines Agency'. For the interactive pdf eAF the name is 'Designer 6.5'. The PLM Portal eAF version number starts with 2.x and for the interactive pdf the version number starts with 1.x. The check on FHIR XML attachment is not applicable for the interactive pdf eAFs. The interactive pdf eAF must not contain any additional attachments. |
| 16.7 | PDF Files | **P/F** |  | The interactive pdf eAFs (from eSubmissions website) must not contain any attachments. | In the document properties the name of author for the interactive pdf eAF the name is 'Designer 6.5'. The interactive pdf the version number starts with 1.x and for the PLM Portal eAF version number starts with 2.x. The check on FHIR XML attachment is not applicable for the interactive pdf eAFs. The interactive pdf eAF must not contain any additional attachments. |
| 16.BP1 | PDF Files | **BP** |  | Files have been created and saved as PDF 1.4, 1.5, 1.6, or PDF 1.7 | For PDF files with apparent versions of 1.3 or earlier, the version information should be taken from the first eight characters from the first line of the header in the file. For versions 1.4 and higher, the version should be taken from the document catalogue dictionary, if present. If both the header information and the catalogue information are present, then the document catalogue dictionary information takes precedent, see PDF 32000-1:2008 specification, chapter 7.5.2 for further details. Only the PDF versions specified are recommended by ICH. This test is important due to archiving and also that PDF files can be correctly open and read by assessors. |
| 16.BP2 | PDF Files | **BP** |  | Hyperlinks and bookmarks within documents, or between documents within the same sequence, have a valid target. | Only links that open in the same software application are tested. Other links (e.g. web links and e-mail addresses) are not considered to link to essential content and should not be tested. If this BP criterion is not met, the assessor might not be able to conveniently find the relevant documents and read the submission as intended by the applicant. |
| 16.BP3 | PDF Files | **BP** | Y | Hyperlinks and bookmarks to destinations in a different sequence in the same eCTD have a valid target. | Only links that open in the same software application are tested. Other links (e.g. web links and e-mail addresses) are not considered to link to essential content and should not be tested. If this BP criterion is not met, the assessor might not be able to conveniently find the relevant documents and read the submission as intended by the applicant. |
| 16.BP4 | PDF Files | **BP** |  | All hyperlinks and bookmarks are set to 'inherit zoom' | Using 'inherit zoom' ensures that assessors do not need to spend time repeatedly setting the view when using the links for navigation to new documents. |
| 16.BP5 | PDF Files | **BP** |  | PDFs except the files from section 1.0 and 1.2 must have 'Fast Web View' active | The use of 'Fast Web View' helps ensure optimum performance of the review system. However, e.g. PAM form and eAF PDF files are exempt from this rule as they cannot be provided as fast web view version. |
| 16.BP6 | PDF Files | **BP** |  | PDF Document Properties for the Initial View are set for 'Page Layout = Default' and 'Magnification = Default' | Setting page layout and magnification to default allows the assessor to set his/her own preferences to define how the PDF is displayed, rather than the settings being taken from each individual PDF file. |
| 16.BP7 | PDF Files | **BP** |  | All PDF hyperlinks and bookmarks are relative | Relative links and bookmarks will continue to work when the submission is copied and loaded into new a environment at the agency side. Absolute (rooted) links and bookmarks will not. |
| 16.BP8 | PDF Files | **BP** |  | The bookmarks pane should be visible if bookmarks are included within a PDF document | Fulfilling this BP criterion make it more convenient for the assessor in knowing there are bookmarks without opening the pane. |
| 16.BP9 | PDF Files | **BP** |  | The bookmarks pane should not be visible if there are no bookmarks included within a PDF document | Fulfilling this BP criterion makes it more convenient for the assessor in knowing there are no bookmarks without opening the pane to check. |
| 16.BP10 | PDF Files | **BP** |  | All hyperlinks and bookmarks between two PDFs must be configured as specified in ISO 32000-1:2008 | Consult the PDF specifications as in ISO 32000-1:2008 for section 7.11.2.3 on how the paths need to be written in PDF. The paths cannot contain back slashes, only forward slashes. See also 12.6.4.3 for the remote goto action. The link to another PDF cannot be made with javascript code in the PDF. Please note, not all PDF tools display the path for the link with forward slashes. However, the presence of a backslash in a link as displayed in a PDF viewer or editor does not necessarily mean that the link is NOT according to the ISO specifications. Therefore, tests for backslashes must be performed in eCTD validation software. This BP criterion is important because links who are not according to section 7.11.2.3 may not work on certain devices, such as non-Windows operating systems or tablets. |
| 16.BP11 | PDF Files | **BP** |  | For SmPC, Labelling and Package Leaflet documents (Module 1.3.1) and for centralised procedures only, the Description of the documents is filled in. | This rule will check whether the Document Properties>Description of the PDF for SmPC, Labelling and Package Leaflet documents is completed (Title, Author, Subject, Keywords). |

### 3.3 Worksheet "File-Folder Structure & Names" (summary)
Legend (sheet rows 1–17): black = fixed text; red = variable text ("multiple files are accepted" where a name is all red or has `-var`);
green = pick-list value (cc, ll, pidoc); **blue = NeeS only**; **pink = eCTD only**; brown "compendial" = folder name prefix after which file names
are entirely variable; bold = folder; "multiple branches possible" / "optional folder" / "folder required and additional folders optional" mark
where extra folders may be added — "In all other locations, additional folders are not allowed". Colours were read from the workbook styles:
the `*-toc.pdf` files are blue (NeeS only); `index.xml`, `index-md5.txt`, `eu-regional.xml`, util files are pink (eCTD only).

**Sequence root, Module 1 and util (all rows):**

| Sheet row | Kind | Path (from sequence folder `0000/`) | Note |
|---|---|---|---|
| 19 | folder | `product-name` |  |
| 20 | folder | `0000` |  |
| 21 | file | `0000/ctd-toc.pdf` | NeeS only (blue in legend) – not used in eCTD |
| 22 | file | `0000/index.xml` |  |
| 23 | file | `0000/index-md5.txt` |  |
| 24 | folder | `0000/m1` |  |
| 25 | file | `0000/m1/m1-toc.pdf` | NeeS only (blue in legend) – not used in eCTD |
| 26 | folder | `0000/m1/eu` |  |
| 27 | file | `0000/m1/eu/eu-regional.xml` |  |
| 28 | folder | `0000/m1/eu/10-cover` |  |
| 29 | folder | `0000/m1/eu/10-cover/cc` |  |
| 30 | file | `0000/m1/eu/10-cover/cc/cc-cover-var.pdf` |  |
| 31 | file | `0000/m1/eu/10-cover/cc/cc-tracking-var.pdf` |  |
| 32 | folder | `0000/m1/eu/12-form` |  |
| 33 | folder | `0000/m1/eu/12-form/cc` |  |
| 34 | file | `0000/m1/eu/12-form/cc/cc-form-eaf-var.pdf` | The previous recommendation is replaced by a mandatory definition of the file names in the EU M1 Specification |
| 35 | file | `0000/m1/eu/12-form/cc/cc-form-annex-var.pdf` |  |
| 36 | folder | `0000/m1/eu/13-pi` |  |
| 37 | folder | `0000/m1/eu/13-pi/131-spclabelpl` |  |
| 38 | folder | `0000/m1/eu/13-pi/131-spclabelpl/cc` |  |
| 39 | folder | `0000/m1/eu/13-pi/131-spclabelpl/cc/ll` |  |
| 40 | file | `0000/m1/eu/13-pi/131-spclabelpl/cc/ll/cc-pidoc-var.pdf` |  |
| 41 | folder | `0000/m1/eu/13-pi/132-mockup` |  |
| 42 | folder | `0000/m1/eu/13-pi/132-mockup/cc` |  |
| 43 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.pdf` |  |
| 44 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.jpg` |  |
| 45 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.jpeg` |  |
| 46 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.gif` |  |
| 47 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.png` |  |
| 48 | file | `0000/m1/eu/13-pi/132-mockup/cc/cc-mockup-var.svg` |  |
| 49 | folder | `0000/m1/eu/13-pi/133-specimen` |  |
| 50 | folder | `0000/m1/eu/13-pi/133-specimen/cc` |  |
| 51 | file | `0000/m1/eu/13-pi/133-specimen/cc/cc-specimen-var.pdf` |  |
| 52 | folder | `0000/m1/eu/13-pi/134-consultation` |  |
| 53 | folder | `0000/m1/eu/13-pi/134-consultation/cc` |  |
| 54 | file | `0000/m1/eu/13-pi/134-consultation/cc/cc-consultation-var.pdf` |  |
| 55 | folder | `0000/m1/eu/13-pi/135-approved` |  |
| 56 | folder | `0000/m1/eu/13-pi/135-approved/cc` |  |
| 57 | file | `0000/m1/eu/13-pi/135-approved/cc/cc-approved-var.pdf` |  |
| 58 | folder | `0000/m1/eu/13-pi/136-braille` |  |
| 59 | file | `0000/m1/eu/13-pi/136-braille/braille-var.pdf` |  |
| 60 | folder | `0000/m1/eu/14-expert` |  |
| 61 | folder | `0000/m1/eu/14-expert/141-quality` |  |
| 62 | file | `0000/m1/eu/14-expert/141-quality/quality-var.pdf` |  |
| 63 | folder | `0000/m1/eu/14-expert/142-nonclinical` |  |
| 64 | file | `0000/m1/eu/14-expert/142-nonclinical/nonclinical-var.pdf` |  |
| 65 | folder | `0000/m1/eu/14-expert/143-clinical` |  |
| 66 | file | `0000/m1/eu/14-expert/143-clinical/clinical-var.pdf` |  |
| 67 | folder | `0000/m1/eu/15-specific` |  |
| 68 | folder | `0000/m1/eu/15-specific/151-bibliographic` |  |
| 69 | file | `0000/m1/eu/15-specific/151-bibliographic/bibliographic-var.pdf` |  |
| 70 | folder | `0000/m1/eu/15-specific/152-generic-hybrid-bio-similar` |  |
| 71 | file | `0000/m1/eu/15-specific/152-generic-hybrid-bio-similar/biosimilar-var.pdf` |  |
| 72 | file | `0000/m1/eu/15-specific/152-generic-hybrid-bio-similar/generic-var.pdf` |  |
| 73 | file | `0000/m1/eu/15-specific/152-generic-hybrid-bio-similar/hybrid-var.pdf` |  |
| 74 | folder | `0000/m1/eu/15-specific/153-data-market-exclusivity` |  |
| 75 | file | `0000/m1/eu/15-specific/153-data-market-exclusivity/datamarketexclusivity-var.pdf` |  |
| 76 | folder | `0000/m1/eu/15-specific/154-exceptional` |  |
| 77 | file | `0000/m1/eu/15-specific/154-exceptional/exceptional-var.pdf` |  |
| 78 | folder | `0000/m1/eu/15-specific/155-conditional-ma` |  |
| 79 | file | `0000/m1/eu/15-specific/155-conditional-ma/conditionalma-var.pdf` |  |
| 80 | folder | `0000/m1/eu/16-environrisk` |  |
| 81 | folder | `0000/m1/eu/16-environrisk/161-nongmo` |  |
| 82 | file | `0000/m1/eu/16-environrisk/161-nongmo/nongmo-var.pdf` |  |
| 83 | folder | `0000/m1/eu/16-environrisk/162-gmo` |  |
| 84 | file | `0000/m1/eu/16-environrisk/162-gmo/gmo-var.pdf` |  |
| 85 | folder | `0000/m1/eu/17-orphan` |  |
| 86 | folder | `0000/m1/eu/17-orphan/171-similarity` |  |
| 87 | file | `0000/m1/eu/17-orphan/171-similarity/similarity-var.pdf` |  |
| 88 | folder | `0000/m1/eu/17-orphan/172-market-exclusivity` |  |
| 89 | file | `0000/m1/eu/17-orphan/172-market-exclusivity/marketexclusivity-var.pdf` |  |
| 90 | folder | `0000/m1/eu/18-pharmacovigilance` |  |
| 91 | folder | `0000/m1/eu/18-pharmacovigilance/181-phvig-system` |  |
| 92 | file | `0000/m1/eu/18-pharmacovigilance/181-phvig-system/phvigsystem-var.pdf` |  |
| 93 | folder | `0000/m1/eu/18-pharmacovigilance/182-riskmgt-system` |  |
| 94 | file | `0000/m1/eu/18-pharmacovigilance/182-riskmgt-system/riskmgtsystem-var.pdf` |  |
| 95 | folder | `0000/m1/eu/19-clinical-trials` |  |
| 96 | file | `0000/m1/eu/19-clinical-trials/clinicaltrials-var.pdf` |  |
| 97 | folder | `0000/m1/eu/110-paediatrics` |  |
| 98 | file | `0000/m1/eu/110-paediatrics/paediatrics-var.pdf` |  |
| 99 | folder | `0000/m1/eu/additional-data` |  |
| 100 | folder | `0000/m1/eu/additional-data/cc` |  |
| 101 | file | `0000/m1/eu/additional-data/cc/cc-additionaldata-var.pdf` |  |
| 102 | folder | `0000/m1/eu/responses` |  |
| 103 | folder | `0000/m1/eu/responses/cc` |  |
| 104 | file | `0000/m1/eu/responses/cc/cc-responses-var.pdf` |  |
| 105 | folder | `0000/m1/eu/util` |  |
| 106 | folder | `0000/m1/eu/util/dtd` |  |
| 107 | file | `0000/m1/eu/util/dtd/var.dtd` |  |
| 108 | file | `0000/m1/eu/util/dtd/var.xsl` |  |
| 115 |  | `(OR)` |  |
| 423 | folder | `0000/util` |  |
| 424 | folder | `0000/util/dtd` |  |
| 425 | file | `0000/util/dtd/eu-regional.dtd` |  |
| 426 | file | `0000/util/dtd/eu-envelope.mod` |  |
| 427 | file | `0000/util/dtd/eu-leaf.mod` |  |
| 428 | file | `0000/util/dtd/ich-ectd-3-2.dtd` |  |
| 429 | folder | `0000/util/style` |  |
| 430 | file | `0000/util/style/ectd-2-0.xsl` |  |
| 431 | file | `0000/util/style/eu-regional.xsl` |  |

**Modules 2–5 (one row per folder; files that sit in it):**

| Sheet row | Folder (from `0000/`) | Recommended file name(s) in it | Folder note |
|---|---|---|---|
| 109 | `0000/m2` | `m2-toc.pdf` (NeeS only (blue in legend) – not used in eCTD) |  |
| 111 | `0000/m2/22-intro` | `introduction-var.pdf` |  |
| 113 | `0000/m2/23-qos` | `qos-var.pdf` |  |
| 116 | `0000/m2/23-qos` (alternative to qos-var.pdf: one file per QOS part) | `introduction-var.pdf`, `drug-substance-var.pdf`, `drug-product-var.pdf`, `appendices-var.pdf`, `regional-information-var.pdf` |  |
| 121 | `0000/m2/24-nonclin-over` | `nonclinical-overview-var.pdf` |  |
| 123 | `0000/m2/25-clin-over` | `clinical-overview-var.pdf` |  |
| 125 | `0000/m2/26-nonclin-sum` | `introduction-var.pdf`, `pharmacol-written-summary-var.pdf`, `pharmacol-tabulated-summary-var.pdf`, `pharmkin-written-summary-var.pdf`, `pharmkin-tabulated-summary-var.pdf`, `toxicology-written-summary-var.pdf`, `toxicology-tabulated-summary-var.pdf` |  |
| 133 | `0000/m2/27-clin-sum` | `summary-biopharm-var.pdf`, `summary-clin-pharm-var.pdf`, `summary-clin-efficacy-var.pdf`, `summary-clin-safety-var.pdf`, `literature-references-var.pdf`, `synopses-indiv-studies-var.pdf` |  |
| 140 | `0000/m3` | `m3-toc.pdf` (NeeS only (blue in legend) – not used in eCTD) |  |
| 142 | `0000/m3/32-body-data` |  |  |
| 143 | `0000/m3/32-body-data/32s-drug-sub` |  |  |
| 144 | `0000/m3/32-body-data/32s-drug-sub/drug-substance` |  | multiple branches possible |
| 145 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s1-gen-info` | `nomenclature-var.pdf`, `structure-var.pdf`, `general-properties-var.pdf` |  |
| 149 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s2-manuf` | `manufacturer-var.pdf`, `manuf-process-and-controls-var.pdf`, `control-of-materials-var.pdf`, `control-critical-steps-var.pdf`, `process-validation-var.pdf`, `manuf-process-development-var.pdf` |  |
| 156 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s3-charac` | `elucidation-of-structure-var.pdf`, `impurities-var.pdf` |  |
| 159 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub` | `ctrlstrat-var.pdf` (Refer to ICH eCTD Q&A 81, additional files are now allowed for control strategy summary.) |  |
| 161 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub/32s41-spec` | `specification-var.pdf` |  |
| 163 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub/32s42-analyt-proc` | `analytical-procedure.pdf` |  |
| 165 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub/32s43-val-analyt-proc` | `validation-analyt-procedure.pdf` |  |
| 167 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub/32s44-batch-analys` | `batch-analyses-var.pdf` |  |
| 169 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s4-contr-drug-sub/32s45-justif-spec` | `justification-of-specification-var.pdf` |  |
| 171 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s5-ref-stand` | `reference-standards-var.pdf` |  |
| 173 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s6-cont-closure-sys` | `container-closure-system-var.pdf` |  |
| 175 | `0000/m3/32-body-data/32s-drug-sub/drug-substance/32s7-stab` | `stability-summary-var.pdf`, `postapproval-stability-var.pdf`, `stability-data-var.pdf` |  |
| 179 | `0000/m3/32-body-data/32p-drug-prod` |  |  |
| 180 | `0000/m3/32-body-data/32p-drug-prod/drug-product` |  | multiple branches possible |
| 181 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p1-desc-comp` | `description-and-composition-var.pdf` |  |
| 183 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p2-pharm-dev` | `pharmaceutical-development-var.pdf` |  |
| 185 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p3-manuf` | `manufacturers-var.pdf`, `batch-formula-var.pdf`, `manuf-process-and-controls-var.pdf`, `control-critical-steps-var.pdf`, `process-validation-var.pdf` |  |
| 191 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p4-contr-excip` | `excipients.pdf` (Refer to ICH eCTD Q&A 73, options 1 & 2, file name entirely variable, multiple files allowed.), `excipients-human-animal-var.pdf`, `novel-excipients-var.pdf` |  |
| 193 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p4-contr-excip/excipient` | `specifications-var.pdf`, `analytical-procedures-var.pdf`, `validation-analyt-procedures-var.pdf`, `justification-of-specifications-var.pdf` | multiple branches possible |
| 198 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p4-contr-excip/compendial-excipients` | `specifications.pdf`, `analytical-procedures.pdf`, `validation-analyt-procedures.pdf`, `justification-of-specifications.pdf` | multiple branches possible |
| 205 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod` | `ctrlstrat-var.pdf` (Refer to ICH eCTD Q&A 81, additional files are now allowed for control strategy summary.) |  |
| 207 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p51-spec` | `specifications-var.pdf` |  |
| 209 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p52-analyt-proc` | `analytical-procedure.pdf` |  |
| 211 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p53-val-analyt-proc` | `validation-analytical-procedures.pdf` |  |
| 213 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p54-batch-analys` | `batch-analyses-var.pdf` |  |
| 215 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p55-charac-imp` | `characterisation-impurities-var.pdf` |  |
| 217 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p5-contr-drug-prod/32p56-justif-spec` | `justification-of-specifications-var.pdf` |  |
| 219 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p6-ref-stand` | `reference-standards-var.pdf` |  |
| 221 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p7-cont-closure-sys` | `container-closure-system-var.pdf` |  |
| 223 | `0000/m3/32-body-data/32p-drug-prod/drug-product/32p8-stab` | `stability-summary-var.pdf`, `postapproval-stability-var.pdf`, `stability-data-var.pdf` |  |
| 227 | `0000/m3/32-body-data/32a-app` |  |  |
| 228 | `0000/m3/32-body-data/32a-app/32a1-fac-equip` |  |  |
| 229 | `0000/m3/32-body-data/32a-app/32a1-fac-equip/manufacturer` | `facilities-and-equipment-report.pdf` | optional folder |
| 231 | `0000/m3/32-body-data/32a-app/32a2-advent-agent` |  |  |
| 232 | `0000/m3/32-body-data/32a-app/32a2-advent-agent/substance` | `adventitious-agents-report.pdf` | optional folder |
| 234 | `0000/m3/32-body-data/32a-app/32a3-excip-substance` |  | multiple branches possible ; In line with ICH eCTD specification, "The directory/file structure would typically follow that of the drug substance section in Module 3.2.S." |
| 235 | `0000/m3/32-body-data/32a-app/32a3-excip-substance/folder` | `substance.pdf` | optional folder |
| 237 | `0000/m3/32-body-data/32r-reg-info` |  |  |
| 238 | `0000/m3/32-body-data/32r-reg-info/folder` | `process-val-scheme.pdf`, `medical-device.pdf`, `certificate-suitability.pdf`, `materials-animal-human-origin.pdf` | optional folder |
| 243 | `0000/m3/33-lit-ref` |  |  |
| 244 | `0000/m3/33-lit-ref/folder` | `reference.pdf` | optional folder |
| 246 | `0000/m4` | `m4-toc.pdf` (NeeS only (blue in legend) – not used in eCTD) |  |
| 248 | `0000/m4/42-stud-rep` |  |  |
| 249 | `0000/m4/42-stud-rep/421-pharmacol` |  |  |
| 250 | `0000/m4/42-stud-rep/421-pharmacol/4211-prim-pd` |  |  |
| 251 | `0000/m4/42-stud-rep/421-pharmacol/4211-prim-pd/study-report` | `study-report.pdf` | optional folder |
| 253 | `0000/m4/42-stud-rep/421-pharmacol/4212-sec-pd` |  |  |
| 254 | `0000/m4/42-stud-rep/421-pharmacol/4212-sec-pd/study-report` | `study-report.pdf` | optional folder |
| 256 | `0000/m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol` |  |  |
| 257 | `0000/m4/42-stud-rep/421-pharmacol/4213-safety-pharmacol/study-report` | `study-report.pdf` | optional folder |
| 259 | `0000/m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact` |  |  |
| 260 | `0000/m4/42-stud-rep/421-pharmacol/4214-pd-drug-interact/study-report` | `study-report.pdf` | optional folder |
| 262 | `0000/m4/42-stud-rep/422-pk` |  |  |
| 263 | `0000/m4/42-stud-rep/422-pk/4221-analyt-met-val` |  |  |
| 264 | `0000/m4/42-stud-rep/422-pk/4221-analyt-met-val/study-report` | `study-report.pdf` | optional folder |
| 266 | `0000/m4/42-stud-rep/422-pk/4222-absorp` |  |  |
| 267 | `0000/m4/42-stud-rep/422-pk/4222-absorp/study-report` | `study-report.pdf` | optional folder |
| 269 | `0000/m4/42-stud-rep/422-pk/4223-distrib` |  |  |
| 270 | `0000/m4/42-stud-rep/422-pk/4223-distrib/study-report` | `study-report.pdf` | optional folder |
| 272 | `0000/m4/42-stud-rep/422-pk/4224-metab` |  |  |
| 273 | `0000/m4/42-stud-rep/422-pk/4224-metab/study-report` | `study-report.pdf` | optional folder |
| 275 | `0000/m4/42-stud-rep/422-pk/4225-excr` |  |  |
| 276 | `0000/m4/42-stud-rep/422-pk/4225-excr/study-report` | `study-report.pdf` | optional folder |
| 278 | `0000/m4/42-stud-rep/422-pk/4226-pk-drug-interact` |  |  |
| 279 | `0000/m4/42-stud-rep/422-pk/4226-pk-drug-interact/study-report` | `study-report.pdf` | optional folder |
| 281 | `0000/m4/42-stud-rep/422-pk/4227-other-pk-stud` |  |  |
| 282 | `0000/m4/42-stud-rep/422-pk/4227-other-pk-stud/study-report` | `study-report.pdf` | optional folder |
| 284 | `0000/m4/42-stud-rep/423-tox` |  |  |
| 285 | `0000/m4/42-stud-rep/423-tox/4231-single-dose-tox` |  |  |
| 286 | `0000/m4/42-stud-rep/423-tox/4231-single-dose-tox/study-report` | `study-report.pdf` | optional folder |
| 288 | `0000/m4/42-stud-rep/423-tox/4232-repeat-dose-tox` |  |  |
| 289 | `0000/m4/42-stud-rep/423-tox/4232-repeat-dose-tox/study-report` | `study-report.pdf` | optional folder |
| 291 | `0000/m4/42-stud-rep/423-tox/4233-genotox` |  |  |
| 292 | `0000/m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro` |  |  |
| 293 | `0000/m4/42-stud-rep/423-tox/4233-genotox/42331-in-vitro/study-report` | `study-report.pdf` | optional folder |
| 295 | `0000/m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo` |  |  |
| 296 | `0000/m4/42-stud-rep/423-tox/4233-genotox/42332-in-vivo/study-report` | `study-report.pdf` | optional folder |
| 298 | `0000/m4/42-stud-rep/423-tox/4234-carcigen` |  |  |
| 299 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud` |  |  |
| 300 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42341-lt-stud/study-report` | `study-report.pdf` | optional folder |
| 302 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud` |  |  |
| 303 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42342-smt-stud/study-report` | `study-report.pdf` | optional folder |
| 305 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud` |  |  |
| 306 | `0000/m4/42-stud-rep/423-tox/4234-carcigen/42343-other-stud/study-report` | `study-report.pdf` | optional folder |
| 308 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox` |  |  |
| 309 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev` |  |  |
| 310 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42351-fert-embryo-dev/study-report` | `study-report.pdf` | optional folder |
| 312 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev` |  |  |
| 313 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42352-embryo-fetal-dev/study-report` | `study-report.pdf` | optional folder |
| 315 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev` |  |  |
| 316 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42353-pre-postnatal-dev/study-report` | `study-report.pdf` | optional folder |
| 318 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv` |  |  |
| 319 | `0000/m4/42-stud-rep/423-tox/4235-repro-dev-tox/42354-juv/study-report` | `study-report.pdf` | optional folder |
| 321 | `0000/m4/42-stud-rep/423-tox/4236-loc-tol` |  |  |
| 322 | `0000/m4/42-stud-rep/423-tox/4236-loc-tol/study-report` | `study-report.pdf` | optional folder |
| 324 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud` |  |  |
| 325 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen` |  |  |
| 326 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42371-antigen/study-report` | `study-report.pdf` | optional folder |
| 328 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox` |  |  |
| 329 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42372-immunotox/study-report` | `study-report.pdf` | optional folder |
| 331 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud` |  |  |
| 332 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42373-mechan-stud/study-report` | `study-report.pdf` | optional folder |
| 334 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep` |  |  |
| 335 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42374-dep/study-report` | `study-report.pdf` | optional folder |
| 337 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab` |  |  |
| 338 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42375-metab/study-report` | `study-report.pdf` | optional folder |
| 340 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp` |  |  |
| 341 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42376-imp/study-report` | `study-report.pdf` | optional folder |
| 343 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other` |  |  |
| 344 | `0000/m4/42-stud-rep/423-tox/4237-other-tox-stud/42377-other/study-report` | `study-report.pdf` | optional folder |
| 346 | `0000/m4/43-lit-ref` |  |  |
| 347 | `0000/m4/43-lit-ref/folder` | `reference.pdf` | optional folder |
| 349 | `0000/m5` | `m5-toc.pdf` (NeeS only (blue in legend) – not used in eCTD) |  |
| 351 | `0000/m5/52-tab-list` | `tabular-listing-var.pdf` |  |
| 353 | `0000/m5/53-clin-stud-rep` |  |  |
| 354 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud` |  |  |
| 355 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep` |  |  |
| 356 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5311-ba-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 358 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep` |  |  |
| 359 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 361 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep` |  |  |
| 362 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5313-in-vitro-in-vivo-corr-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 364 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met` |  |  |
| 365 | `0000/m5/53-clin-stud-rep/531-rep-biopharm-stud/5314-bioanalyt-analyt-met/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 367 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat` |  |  |
| 368 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep` |  |  |
| 369 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5321-plasma-prot-bind-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 371 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud` |  |  |
| 372 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5322-rep-hep-metab-interact-stud/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 374 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat` |  |  |
| 375 | `0000/m5/53-clin-stud-rep/532-rep-stud-pk-human-biomat/5323-stud-other-human-biomat/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 377 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud` |  |  |
| 378 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep` |  |  |
| 379 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5331-healthy-subj-pk-init-tol-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 381 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep` |  |  |
| 382 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5332-patient-pk-init-tol-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 384 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep` |  |  |
| 385 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5333-intrin-factor-pk-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 387 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep` |  |  |
| 388 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5334-extrin-factor-pk-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 390 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep` |  |  |
| 391 | `0000/m5/53-clin-stud-rep/533-rep-human-pk-stud/5335-popul-pk-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 393 | `0000/m5/53-clin-stud-rep/534-rep-human-pd-stud` |  |  |
| 394 | `0000/m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep` |  |  |
| 395 | `0000/m5/53-clin-stud-rep/534-rep-human-pd-stud/5341-healthy-subj-pd-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 397 | `0000/m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep` |  |  |
| 398 | `0000/m5/53-clin-stud-rep/534-rep-human-pd-stud/5342-patient-pd-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 400 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud` |  |  |
| 401 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication` |  | multiple branches possible |
| 402 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5351-stud-rep-contr` |  |  |
| 403 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5351-stud-rep-contr/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 405 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5352-stud-rep-uncontr` |  |  |
| 406 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5352-stud-rep-uncontr/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 408 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5353-rep-analys-data-more-one-stud` |  |  |
| 409 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5353-rep-analys-data-more-one-stud/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 411 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5354-other-stud-rep` |  |  |
| 412 | `0000/m5/53-clin-stud-rep/535-rep-effic-safety-stud/indication/5354-other-stud-rep/study-report` | `study-report.pdf` | folder required and additional folders optional |
| 414 | `0000/m5/53-clin-stud-rep/536-postmark-exp` |  |  |
| 415 | `0000/m5/53-clin-stud-rep/536-postmark-exp/folder` | `study-report.pdf` | optional folder |
| 417 | `0000/m5/53-clin-stud-rep/537-crf-ipl` |  |  |
| 418 | `0000/m5/53-clin-stud-rep/537-crf-ipl/study` | `filename.pdf` | optional folder |
| 420 | `0000/m5/54-lit-ref` |  |  |
| 421 | `0000/m5/54-lit-ref/folder` | `reference.pdf` | optional folder |

### 3.4 Worksheet "Files and Folders Q&A" — see §1.2 last row (EU M1: no additional folders; M5: required except 5.2; etc.).
### 3.5 Worksheet "Picklist Values" — country, language, PI-doc lists as in §1.4 (sheet title "Pick Lists from EU m1 Specification v 3.1").

---

## 4. EU accepted file formats (FMT v1.0, June 2024)

General (FMT p. 1): "The generally accepted file format is the PDF, however, in specific cases, other formats will be exceptionally accepted";
"Unless specifically requested, the documents should only be provided in one format, once in the lifecycle"; "should not be embedded within a PDF
file but submitted as standalone files". Same wording in HTG 2.9.2 and SPEC p. 8 ("Regional File Formats").

| Type | Ext. | Format | Allowed location(s) | Permissible use / comment |
|---|---|---|---|---|
| Documents | .pdf | Portable Document Format | M1–M5 | PDF/A-1, PDF/A-2, 1.4, 1.5, 1.6, 1.7 |
| Images | .bmp | Bitmap | M1.3.2, M1.3.3 | Mock-ups / specimens |
| Images | .gif | GIF | M1.3.2, M1.3.3 | Mock-ups / specimens |
| Images | .jpg, .jpeg | JPEG | M1.3.2, M1.3.3 | Mock-ups / specimens |
| Images | .png | PNG | M1.3.2, M1.3.3 | Mock-ups / specimens |
| Audio/Video | .mp4 | MPEG-4 Part 14 | M1.3, M2, M5 | Labelling, M2 summaries & overviews, CSRs |
| Coding | .dtd | DTD | M1 (`\util\dtd`) | util/dtd folder |
| Coding | .mod | DTD module | M1 (`\util\dtd`) | util/dtd folder |
| Coding | .xml | XML | M1.2, M1.3, M4, M5 | eAF, labelling, datasets, ePI |
| Coding | .xsd | XML Schema | M4, M5 | Clinical (ISS) datasets |
| Coding | .xsl | XSL | M1, M4–M5 | util/style folder, data |
| Data | .csv | CSV | M5.3.3.5 | Population PK studies |
| Data | .svg | SVG | M3–M5 | — |
| Data | .xpt | SAS transport | M3–M5 | — |
| Data | .txt | Text | M5 | Datasets |
| Data | .xlsx | Excel Open XML | M5 | Datasets; "No macros to be included in the file" |

Related limits: PDF ≤1.3 fails (VC 16.1); 1.4–1.7 is BP (16.BP1); file >500 MB (non-video) BP warning (15.BP1); video >1 GB (15.BP6);
format checks are BP (15.BP1.1 M1, 15.BP2.1 M2–5). SPEC p. 8 adds: PDF/A-1 and PDF/A-2 acceptable; later PDF versions only where an agency requires
(e.g. application form). **Inconsistencies inside the EU package:** the VC File-Folder sheet lists `cc-mockup-var.svg` in 1.3.2 (row 48) while FMT
lists .svg only for M3–M5 and lists .bmp for 1.3.2/1.3.3, which the VC sheet does not; FMT has no entry for the `m1/eu/util/dtd/var.xsl` file the
VC sheet shows (row 108).

---

## 5. Egyptian draft (EG) vs EU HTG v6.0.1 — section map and differences

### 5.1 Section-by-section correspondence
"≈" = near-verbatim copy with EU→EG/EDA name substitution; "Δ" = substantive change (detailed in 5.2).

| EG section | EU HTG section | Relation |
|---|---|---|
| 1 Introduction | 1 | Δ "mandatory … for all procedure types for Egypt"; EU sentence on ASMF both parts dropped |
| 1.1 Glossary | 1.1 | Δ adds *Baseline Submission, DTD, Envelope (eg-regional.xml), High Level Number, Non eCTD Submission, Procedure Tracking Number, Working Documents*; eCTD application redefined ("different dosage forms and strengths are submitted under separate applications"); EU "Global Marketing Authorisation Art. 6(2)" dropped |
| 2.1.1 Types of products | 2.1.1 | Δ adds "biological and innovative products", ATMPs; drops herbals/homeopathics |
| 2.1.2 Types of submission | 2.1.2 | Δ drops extensions, PSUR/PSUSA, paediatric, referral, PAM; points to Annex 6 |
| 2.1.3 Types of submission units | 2.1.3 | Δ drops "closing" and "consolidation" sentences; corrigendum "must be discussed and agreed with EDA in advance" |
| — | 2.1.4 Types of procedures, 2.1.5 Exceptions | dropped (no CP/MRP/DCP/NP concept) |
| 2.2 Structure of submissions | 2.2 | Δ **one eCTD per strength or dosage form (mandatory)** |
| 2.3 Transitional arrangements | 2.3 | ≈ |
| 2.4 Change to eCTD format | 2.4 | Δ ongoing activities finish in old format; baseline **required** (EU: recommended); EDQM exception dropped |
| 2.5.1–2.5.3 | 2.5.1–2.5.3 | ≈ (2.5.3 points to "EG eCTD M1 Specification" instead of NtA Vol 2B) — 64/64/180 limits kept |
| 2.6 Correspondence | 2.6 | ≈ (CMDh exception dropped) |
| 2.7 Paper requirements | 2.7 | Δ legalised CPP + labelling hard copy |
| 2.8 Hardware | 2.8 | Δ adds EDA eCTD portal URL |
| 2.9.1 Identifier (UUID) | 2.9.1 | ≈ (refers to EG 2.11.2 = EU 2.11.3) |
| 2.9.2 File formats | 2.9.2 | ≈ but refers to an "EG Accepted File Formats for eCTD" (not supplied) |
| 2.9.3 PDF | 2.9.3 | ≈ (EU signature bullet removed) |
| 2.9.4 Sequence numbers | 2.9.4 | Δ "mandatory to use the EDA Portal"; no EDQM exception |
| 2.9.5 Related sequence | 2.9.5 | Δ only one example table (var-pac-II); PSUSA/referral tables and PAM example dropped |
| 2.9.6 Leaf lifecycle | 2.9.6 + Table 5 | Δ Table 2 has **no Module 1 rows**; examples use `country="eg"`, `xml:lang="ar"`; EU `ema/emea` equivalence and `dk` example dropped; EU m1-additional paragraph kept verbatim |
| 2.9.7 Bookmarks; 2.9.8 Node ext.; 2.9.9 XML | 2.9.7–2.9.9 | ≈ (2.9.9 eAF sentence dropped) |
| 2.9.10 Working documents | 2.9.10 | ≈ minus country sub-folders, ePMF, EudraLink paragraphs |
| 2.9.11 Technical validation | 2.9.11 | Δ EDA Portal runs full validation + e-mail ack; EU "tolerant PSUR validation", envelope-correction exception and historical-sequence paragraphs dropped |
| 2.10.1 Malware | 2.10.1 | ≈ |
| 2.10.2 Security settings | 2.10.2 | Δ EU exception "except for files in Modules 1.0, 1.2, 3.3, 4.3 and 5.4" dropped |
| 2.10.3 Signatures | 2.10.3 | Δ "Electronic signatures are not used" |
| 2.11 Baseline; 2.11.1 | 2.11; 2.11.1 | Δ baseline sections "defined by the authority" (EU: by applicant), required; refers to an EDA baseline guidance |
| — | 2.11.2 Baselines later in lifecycle | dropped |
| 2.11.2 Re-baselining | 2.11.3 | ≈ minus EU examples (one eCTD per strength, MRP models, Art. 30) and the merge-UUID paragraph |
| 2.12 Procedure for sending | 2.12.1–2.12.4 | Δ EDA portal only (CESP / Gateway / CD-DVD / EudraLink dropped) |
| 3.1 General | 3.1 | ≈ minus "a single eCTD application can cover … multiple medicinal products … (different dosage forms or strengths)" |
| 3.2.1 General | 3.2.1 | ≈ minus "country code should appear in the file and folder name" |
| 3.2.2 Envelope | 3.2.2 | Δ see 5.2 |
| 3.2.3.1 Cover letter / 3.2.3.2 Tracking table | 3.2.3.1 / 3.2.3.2 | Δ file name/location |
| 3.2.4 Forms / 3.2.4.1 Application form | 3.2.4 | Δ `form-af.pdf`; additional documents to 1.2 (→ Annex 5 tree) |
| 3.2.5 Product information | 3.2.5 | ≈ first paragraph only (MRP/DCP/CP translation paragraphs dropped) |
| 3.2.6 Responses | 3.2.6 | Δ file-name pattern |
| 3.2.7 Additional data | 3.2.7 | Δ scope |
| 3.3–3.6 (M2–M5) | 3.3–3.6 | ≈ (3.5.1 "FDA"; 3.6.2 keeps "In Europe, node extensions should be used") |
| 4.1 New MAA, 4.2 Variations | 4.1, 4.2 | ≈ minus EU Tables 9–14; point to Annex 6 / Annex 4 |
| — | 4.3 Extensions, 4.5 PSURs, 4.6 Referrals, 4.8 VAMF, 4.12 Clinical data publication, 4.13 Duplicates, 4.14 Informed consent | dropped |
| 4.3 Renewal | 4.4 | ≈ |
| 4.4 ASMF | 4.7 | ≈ (Letter of Access "in m1.2"; EU "Annex 5.10 of the application form … m12/cc") |
| 4.5 PMF | 4.9 | ≈ |
| 4.6 Withdrawal of the MA | 4.10 | Δ whole MA only (EU partial strength/dosage-form withdrawal paragraph dropped) |
| 4.7 Withdrawal/rejection of post-auth. activities | 4.11 | Δ submission unit type "Response" (EU text: "The submission type should be 'consolidating'") |
| Annex 1 Reference documents | Annex 1 | Δ EDA eCTD webpage, EDA portal |
| Annex 2 Tracking table | Annex 2 (A2-2 "for CP and NP") | ≈ format; EG example rows have no sequence numbers in the text available |
| Annex 3 Module 3 | Annex 3 | ≈ minus A3-2.2.1 CP / A3-2.2.2 MRP; A3-2.2 "for each strength and forms" |
| Annex 4 Parallel variations | Annex 4 | ≈ ("EDA decision"; one remnant "original commission decision from sequence 0003" in A4-4.2.2) |
| Annex 5 Section 1.2 tree | — | **new** |
| Annex 6 Controlled vocabulary | (EU: SPEC App. 1.1 + DTD) | **new** |

### 5.2 Where Egypt differs (concrete)
| Topic | EU (cite) | EG draft (cite) | Consequence for an EG M1 modelled on EU |
|---|---|---|---|
| Scope of one eCTD | "Typically, an eCTD application will cover all dosage forms and strengths"; one-per-strength "normally not recommended" (HTG 2.2; A3-2.2.1 CP "should always cover all strengths") | "the applicant should submit one eCTD per strength or dosage form … submission of a single sequence that covers more than one strength or dosage form will not be possible" (EG 2.2; Glossary; A3-2.2 "a single eCTD application is submitted for each strength and forms") | EG copied the EU *consequence* sentence and made it the rule: one UUID per strength/form; every variation submitted N times |
| Procedures / envelopes | 4 procedure types; one envelope per receiving country; `ema`/`edqm` (SPEC p. 10; HTG 3.2.2) | No procedure type and no Country row in the envelope table (EG 3.2.2) | Probably a single envelope; `procedure` element and `country` attribute either dropped or fixed — **not determinable** without the EG spec |
| Agency code | `CC-ACRONYM` picklist, e.g. `EU-EMA`, `BE-FAMHP` (App. 2.4) | "This authority code is 'EDA' for Egypt" (EG 3.2.2) | bare `EDA`, not `EG-EDA` pattern |
| Envelope fields added | — (not in eu-envelope.mod) | **Registration Type** (e.g. Imported Finished, Imported Bulk) and **Marketing Type** (e.g. Local, Tender, Export), each from a controlled vocabulary "published on the EDA web site" (EG 3.2.2) | new envelope elements/attributes; vocabularies **not in the draft** |
| Submission mode | single · grouping · worksharing (DTD) | Single · Grouping · **Parallel Single · Parallel Grouping** ("For Imported Products, evaluation … at the same time with the authority of the country of origin"); no worksharing (EG Annex 6 "EG Submission Modes") | mode only for variations (EG 3.2.2); Number required when grouping (EG 3.2.2 vs EU grouping *or* worksharing) |
| High-level / tracking numbers | from EMA/NCA (SPEC App. 1.1) | "Issued by EDA through the portal" (EG Glossary) | — |
| Submission types | 52 EU values (§2.2) | Own vocabulary (EG Annex 6), see 5.3 | EU types for PSUR, referrals, PAM, paediatrics, extension, rup … absent |
| Submission units | 9 values incl. **closing, consolidating** (DTD) | initial, validation-response ("content validation issues"), response (also for consolidation), additional-info, corrigendum, reformat, re-examination ("MAA, type II variation") (EG Annex 6) | no `closing`/`consolidating`; EG 4.7 uses "Response" for consolidation sequences |
| Folder root / regional file | `m1/eu/`, `eu-regional.xml` | `m1/eg/` (EG 3.2.3.2 "/XXXX/m1/eg/10-cover/"), `eg-regional.xml` (Glossary "Envelope") | — |
| Country prefix / folders | CC folders + `CC-` prefixes (App. 2) | tracking table `tracking-var.pdf` directly in `m1/eg/10-cover/`; form `form-af.pdf`; responses `responses-<type>-<response number>-<content>.pdf` (EG 3.2.3.2, 3.2.4.1, 3.2.6 Table 4) — no CC; yet EG 2.9.6 example keeps `<pi-doc xml:lang="en" type="combined" country="eg">` | EG appears to drop CC folders/prefixes in 1.0, 1.2, responses, but keep pi-doc attributes; **inconsistent / not determinable** |
| Tracking table | `cc-tracking-var.pdf` in `10-cover/cc` (VC 15.11/15.12 P/F) | `tracking-var.pdf` in `10-cover/` | under EU rules would fail 15.11/15.12 |
| Application form | `cc-form-eaf(-var).pdf`, annexes `cc-form-annex-var.pdf` (HTG 3.2.4) | `form-af.pdf`, `form-af-10mg` (EG 3.2.4.1) | — |
| Module 1.2 content | `m1-2-form (specific+)` – flat, eAF + annexes (DTD; App. 2 rows 7–10) | **Annex 5: 1.2.1 Application Form … 1.2.16 Documents related Inspection**, with 3rd-level items (1.2.2 Legal Documents 21 items, 1.2.3 EDA Approvals 20, 1.2.4 Declarations 22, 1.2.5 Reference product 4, 1.2.6 Imported products 2 incl. 1.2.6.1 CPP, 1.2.7 Reliance 6, 1.2.8 Composition 7, 1.2.9 CoA, 1.2.10 PAC 4, 1.2.11 Proof of payment, 1.2.12 Biological analysis 2, 1.2.13 Plasma-derived 3, 1.2.14 Scientific advice, 1.2.15 PV 5 incl. RMP/PSUR/PSMF, 1.2.16 Inspection 7 incl. SMF) | needs new DTD elements (the EU DTD cannot express sub-sections of 1.2); overlaps with EU M1 1.8 (PV/RMP); 1.2.2.3 and 1.2.2.21 are both GMP certificates |
| Paper | "Some NCAs may still require paper copies" (HTG 2.7) | hard copy of legalised CPP and labelling (outer & inner pack, SmPC & PIL) (EG 2.7) | — |
| Channel | CESP / EMA Gateway / national portals / CD-DVD by exception (HTG 2.12) | EDA eCTD Portal `https://reg-submit.edaegypt.gov.eg` only, pre-registered users, zip upload (EG 2.8, 2.12) | — |
| Signatures | eIDAS e-signatures accepted, portal log-on usually sufficient (HTG 2.10.3; SPEC p. 9) | "Electronic signatures are not used" (EG 2.10.3) | — |
| Security settings | allowed restrictions in 1.0/1.2 (eAF) and 3.3/4.3/5.4 (HTG 2.10.2; VC 16.3/16.4) | no exception (EG 2.10.2) | EG text stricter than the EU P/F model |
| Baseline | recommended, applicant defines scope (HTG 2.11) | required, authority defines scope, "baseline guidance document published on the EDA website" (EG 2.4, 2.11) | — |
| Transition | next submission incl. ongoing activities in eCTD (HTG 2.4) | ongoing activities completed in their original format (EG 2.4) | — |
| Additional data | nationally required info in NP/MRP/DCP (HTG 3.2.7) | info "not currently included in the published EG eCTD M1 Specification" (EG 3.2.7) | — |
| Validation criteria | VC v8.2 (P/F + BP) | "EDA has adopted a common set of technical validation criteria"; "EG Validation Criteria" with a "File-Folder Structure & Names" tab (EG 2.5.2, 2.9.11, 3.3.2, Annex 1) — **not supplied** | VC v8.2 is the closest model |
| Accepted formats | FMT v1.0 | "EG Accepted File Formats for eCTD" (EG 2.9.2) — **not supplied** | FMT is the closest model |

### 5.3 Controlled vocabulary of submission types (EG Annex 6 vs EU DTD)
| Group (EG Annex 6 heading) | EG values (as printed) | EU equivalent |
|---|---|---|
| Pharmaceuticals | `maa`; `var-pac-n` (PAC-N notification); `var-pac-b`; `var-pac-a` (annual); `var-pac-ii` (major); `renewal`; `asmf`; `cep` ("EDQM only"); `none`; `preass` (pre-assessment); `pacstab`, `paccadc`, `paci`, `pacqr` (post-MA commitments: stability, CADC analysis, inspection, quality req.); `5yr` (fifth-year report); `appeal`; `preappinq` (preliminary approval inquiry) | `maa`, `renewal`, `asmf`, `cep`, `none` identical; var-pac-* ≈ var-type1a/1ain/1b/2 by function; rest have no EU code |
| Biologics & innovative (general) | `renewal`, `none`, `pacstab`, `paccadc`, `pacqr`, `paci`, `PMF` (upper case), `withdrawal` | `pmf` (lower case in EU), `withdrawal` |
| Innovative products | `maa-inn`; `ipv-admc`, `ipv-admlc` (abbrev. printed "IPV-ADMIC"), `ipv-tlc`, `ipv-pu`, `ipv-safeffc`; `imv-majvar`, `imv-minvar`, `imv-not`; `ibv-majqualc`, `ibv-modqualc`, `ibv-minqualc`, `ibv-qcnoimp` | none |
| Biologicals | `maa-nt`, `maa-ft`, `maa-sb`, `maa-rl1`, `maa-rl2`, `maa-bios`; `np-modqualc`, `np-pilc`, `np-majqualc`, `np-safeffc`, `np-admpilc`, `np-packup`, `np-adminc`; `rp-majcq`, `rp-modqc`, `rl-pilc` (prefix `rl-` not `rp-`); `not-minqc`, `not-qcnoimp` | none |

Observed defects in the EG draft relevant to a DTD enumeration: upper-case `PMF` (EU and ICH file/attribute conventions are lower case);
EG 2.9.5 Table 1 writes `var-pac-II` while Annex 6 writes `var-pac-ii`; mode names contain spaces ("Parallel Single") — a DTD enumeration token
cannot contain spaces, so the real token is unknown; EG 2.1.3 calls corrigendum a "submission type" (copied from HTG 2.1.3) but both DTD and EG
Annex 6 list it as a submission *unit*.

---

## 6. Walk-through of a real (old) EU sequence — EX `ex2-NPv1.0/0012` (national procedure, Belgium)

Why this one: national procedure, single envelope, single agency — closest to the EDA situation. The 9 examples in the zip:

| Example | Envelope country | submission type / mode | procedure | sequence → related | description |
|---|---|---|---|---|---|
| ex1-CPv1.0/0012 | emea | supplemental-info | centralised | 0012 → 0011 | Final amended translations |
| **ex2-NPv1.0/0012** | **be** | **supplemental-info** | **national** | **0012 → 0011** | **Final amended translations** |
| ex3-DCPv1.0/0012 | de | supplemental-info | decentralised | 0012 → 0011 | Final amended translations |
| ex4-MRPv1.0/0012 | de, uk | supplemental-info | mutual-recognition | 0012 → 0011 | Final amended translations |
| ex5-CPv1.0/0022 | emea | var-type1a / single | centralised | 0022 → (none) | Type IA Variation for Change of Address for Big Factory |
| ex6-CPv1.0/0026 | emea | var-type2 / grouping | centralised | 0026 → (none) | Grouped Type II Variation for New Excipient and New Indication |
| ex7-CPv1.0/0029 | emea | var-type2 / grouping | centralised | 0029 → (none) | Grouped Type IB … and Type II Variation … |
| ex8-CPv1.0/MA-000123/0031, MA-000789/0041 | emea | var-type1a / grouping | centralised | (none) | Grouped Type IA Variations (two MAs, one folder each) |
| ex9-CPv1.0/MA-000123/0032, MA-000456/0013 | emea | var-type2 / worksharing | centralised | (none) | Type II Variation for updated DDPS (worksharing) |

### 6.1 Tree (complete)
```
0012/
├── index.xml
├── index-md5.txt                         content: 9db0732116a070b7daec58a9e642a78c  (= MD5 of index.xml, verified)
├── m1/eu/
│   ├── eu-regional.xml                   (MD5 2a8d9a148d6d342631036d68651300e1 = checksum in index.xml leaf, verified)
│   ├── 10-cover/be/be-cover.pdf
│   ├── 12-form/be/be-form.pdf
│   └── 13-pi/131-spclabelpl/be/
│       ├── de/ be-outer.pdf  be-pl.pdf  be-spc.pdf
│       ├── fr/ be-outer.pdf  be-pl.pdf  be-spc.pdf
│       └── nl/ be-outer.pdf  be-pl.pdf  be-spc.pdf
└── util/
    ├── dtd/  eu-envelope.mod  eu-leaf.mod  eu-regional.dtd ("EU Backbone 1.4", Aug 2009)  ich-ectd-3-2.dtd
    └── style/ ectd-2-0.xsl  eu-regional.xsl
```
All 11 PDFs are the same 40 kB dummy file (all MD5 `d026431303be07099618458b24f8d8a9`). Belgium = three languages → three LL folders (SPEC p. 11–12 rule).

### 6.2 index.xml (verbatim, 573 bytes)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="util\style\ectd-2-0.xsl" ?>
<!DOCTYPE ectd:ectd SYSTEM "util\dtd\ich-ectd-3-2.dtd">
<ectd:ectd xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">
	<m1-administrative-information-and-prescribing-information>
		<leaf ID="eum1" operation="new" checksum="2a8d9a148d6d342631036d68651300e1" checksum-type="md5" xlink:href="m1/eu/eu-regional.xml">
			<title>EU Module 1</title>
		</leaf>
	</m1-administrative-information-and-prescribing-information>
</ectd:ectd>
```

### 6.3 m1/eu/eu-regional.xml
The file is one physical line (tags separated by tab characters). Shown here **re-indented only** (line breaks/indentation added; the newlines inside the original `leaf` start-tags before `modified-file` were collapsed to one space; element order, attribute order and all values unchanged):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE eu:eu-backbone SYSTEM "..\..\util\dtd\eu-regional.dtd">
<?xml-stylesheet type="text/xsl" href="..\..\util\style\eu-regional.xsl"?>
<eu:eu-backbone xmlns:eu="http://europa.eu.int" xmlns:xlink="http://www.w3c.org/1999/xlink" dtd-version="1.4">
  <eu-envelope>
    <envelope country="be">
      <submission type="supplemental-info">
        <tracking>
          <number>2131577</number>
        </tracking>
      </submission>
      <applicant>Pharma Unlimited</applicant>
      <agency code="BE-FAMHP"/>
      <procedure type="national"/>
      <invented-name>Magieke Pil</invented-name>
      <invented-name>Pilulle Magique</invented-name>
      <invented-name>Magiesche Pille</invented-name>
      <inn>INN-PIL</inn>
      <sequence>0012</sequence>
      <related-sequence>0011</related-sequence>
      <submission-description>Final amended translations</submission-description>
    </envelope>
  </eu-envelope>
  <m1-eu>
    <m1-0-cover>
      <specific country="be">
        <leaf ID="id-cover-1" operation="new" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md5" xlink:href="10-cover/be/be-cover.pdf">
          <title>Cover Letter for Belgium Agency</title>
        </leaf>
      </specific>
    </m1-0-cover>
    <m1-2-form>
      <specific country="be">
        <leaf ID="id-form-1" operation="new" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md5" xlink:href="12-form/be/be-form.pdf">
          <title>Application Form</title>
        </leaf>
      </specific>
    </m1-2-form>
    <m1-3-pi>
      <m1-3-1-spc-label-pl>
        <pi-doc xml:lang="fr" type="spc" country="be">
          <leaf ID="spc-be-fr" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/fr/be-spc.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#spc-be-fr">
            <title>SPC in French</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="fr" type="outer" country="be">
          <leaf ID="outer-be-fr" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/fr/be-outer.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#outer-be-fr">
            <title>Outer Labelling in French</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="fr" type="pl" country="be">
          <leaf ID="pl-be-fr" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/fr/be-pl.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#pl-be-fr">
            <title>Package Leaflet in French</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="nl" type="spc" country="be">
          <leaf ID="spc-be-nl" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/nl/be-spc.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#spc-be-nl">
            <title>SPC in Dutch</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="nl" type="outer" country="be">
          <leaf ID="outer-be-nl" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/nl/be-outer.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#outer-be-nl">
            <title>Outer Labelling in Dutch</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="nl" type="pl" country="be">
          <leaf ID="pl-be-nl" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/nl/be-pl.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#pl-be-nl">
            <title>Package Leaflet in Dutch</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="de" type="spc" country="be">
          <leaf ID="spc-be-de" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/de/be-spc.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#spc-be-de">
            <title>SPC in German</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="de" type="outer" country="be">
          <leaf ID="outer-be-de" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/de/be-outer.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#outer-be-de">
            <title>Outer Labelling in German</title>
          </leaf>
        </pi-doc>
        <pi-doc xml:lang="de" type="pl" country="be">
          <leaf ID="pl-be-de" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md4" xlink:href="13-pi/131-spclabelpl/be/de/be-pl.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#pl-be-de">
            <title>Package Leaflet in German</title>
          </leaf>
        </pi-doc>
      </m1-3-1-spc-label-pl>
    </m1-3-pi>
  </m1-eu>
</eu:eu-backbone>
```

### 6.4 What has changed since this v1.4 example (checked, not assumed)
Validation with `xmllint --dtdvalid`: the file is **valid against its own 1.4 DTD** and **invalid against the current 3.1 DTD**, which reports:
`dtd-version … must be "3.1"`; envelope "expecting (identifier, submission, submission-unit, applicant, agency, procedure, invented-name+, inn*,
sequence, related-sequence+, submission-description)"; `submission` "expecting (number?, procedure-tracking), got (tracking)";
`"supplemental-info" … is not among the enumerated set`; "No declaration for element tracking".

| Item | v1.4 (example, 2009) | v3.1 (current) | Source of the current rule |
|---|---|---|---|
| `dtd-version` | FIXED "1.4" | FIXED "3.1" | DTD |
| UUID `identifier` | absent | mandatory first child | eu-envelope.mod; SPEC UUID pp. 13–15; VC 9.7–9.9 |
| Sub-activity | encoded in `submission/@type` (25 values incl. `supplemental-info`, `fum`, `specific-obligation`, `corrigendum`, `reformat`) | separate `submission-unit/@type` (initial … re-examination); types now 52 incl. psusa, pam-*, referral-*, paed-*, article-18 | eu-envelope.mod |
| Tracking wrapper | `<tracking><number>` | `<procedure-tracking><number>` | eu-envelope.mod |
| `related-sequence` | 0..n, had a `country` attribute | 1..n, no attribute; = own number for initial/reformat | eu-envelope.mod; VC 14.6/14.7 |
| Country codes | `emea`, no hr/edqm/xi | `ema`, + hr, edqm, xi | DTD |
| Agency codes | 46 codes, e.g. `EU-EMEA`, `FR-AFSSAPS`, `ES-AGEMED`, `UK-VMD` | 34 codes, e.g. `EU-EMA`, `FR-ANSM`, `ES-AEMPS`, `EU-EDQM` | eu-envelope.mod; App. 2.4 |
| 1.3.1 | element `m1-3-1-pim` existed | removed; only `m1-3-1-spc-label-pl` with `pi-doc` | DTD |
| Languages | no `ga` | `ga` added | DTD |
| Tracking table | none in the example | `be-tracking-var.pdf` in `10-cover/be` mandatory (P/F) | VC 15.11, 15.12 |
| Form file name | `be-form.pdf` | `be-form-eaf(-var).pdf` mandatory name | VC File-Folder row 34; HTG 3.2.4 |
| Paths in DOCTYPE / stylesheet PI | back-slashes `..\..\util\dtd\…` | must be valid URI references (forward slashes) | VC 7.5, 7.6, 9.5, 9.6; 16.BP10 (PDF links) |
| `checksum-type` | example has `md4` on all nine pi-doc leaves (checksum value is in fact MD5) | must be md5 | VC 11.1 (P/F) |
| util files | 1.4 checksums (eu-regional.dtd `91654e96…`, eu-envelope.mod `664a76e3…`, eu-leaf.mod `2e976bc6…`, eu-regional.xsl `54f98898…`) | v3.1 checksums (§0) | VC 3.3, 4.3, 5.3, 6.3 |
| Lifecycle | leaves `replace` `../../../0011/m1/eu/eu-regional.xml#spc-be-fr`; sequence 0011 is not in the zip | same mechanism; would be a 'Y' check | VC 11.6, 11.9 |

**Illustrative v3.1 rewrite of the same envelope** (DERIVED by me from eu-envelope.mod v3.1; not an EMA example; UUID is the sample from SPEC p. 14;
submission type/unit chosen as placeholders because the activity started in 0011 is unknown; tracking-table checksum is a dummy). It **passes**
`xmllint --dtdvalid eu_util_new/util/dtd/eu-regional.dtd`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE eu:eu-backbone SYSTEM "../../util/dtd/eu-regional.dtd">
<?xml-stylesheet type="text/xsl" href="../../util/style/eu-regional.xsl"?>
<eu:eu-backbone xmlns:eu="http://europa.eu.int" xmlns:xlink="http://www.w3c.org/1999/xlink" dtd-version="3.1">
  <eu-envelope>
    <envelope country="be">
      <identifier>4cc86cf0-9088-4a3c-9526-fa6320f4c469</identifier>
      <submission type="var-type2" mode="single">
        <procedure-tracking>
          <number>2131577</number>
        </procedure-tracking>
      </submission>
      <submission-unit type="response"/>
      <applicant>Pharma Unlimited</applicant>
      <agency code="BE-FAMHP"/>
      <procedure type="national"/>
      <invented-name>Magieke Pil</invented-name>
      <invented-name>Pilulle Magique</invented-name>
      <invented-name>Magiesche Pille</invented-name>
      <inn>INN-PIL</inn>
      <sequence>0012</sequence>
      <related-sequence>0011</related-sequence>
      <submission-description>Final amended translations</submission-description>
    </envelope>
  </eu-envelope>
  <m1-eu>
    <m1-0-cover>
      <specific country="be">
        <leaf ID="id-cover-1" operation="new" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md5" xlink:href="10-cover/be/be-cover.pdf">
          <title>Cover Letter for Belgium for Sequence 0012</title>
        </leaf>
        <leaf ID="id-tracking-1" operation="new" checksum="00000000000000000000000000000000" checksum-type="md5" xlink:href="10-cover/be/be-tracking.pdf">
          <title>Tracking Table</title>
        </leaf>
      </specific>
    </m1-0-cover>
    <m1-2-form>
      <specific country="be">
        <leaf ID="id-form-1" operation="new" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md5" xlink:href="12-form/be/be-form-eaf.pdf">
          <title>Application Form</title>
        </leaf>
      </specific>
    </m1-2-form>
    <m1-3-pi>
      <m1-3-1-spc-label-pl>
        <pi-doc xml:lang="fr" type="spc" country="be">
          <leaf ID="spc-be-fr" operation="replace" checksum="d026431303be07099618458b24f8d8a9" checksum-type="md5" xlink:href="13-pi/131-spclabelpl/be/fr/be-spc.pdf" modified-file="../../../0011/m1/eu/eu-regional.xml#spc-be-fr">
            <title>SPC in French</title>
          </leaf>
        </pi-doc>
      </m1-3-1-spc-label-pl>
    </m1-3-pi>
  </m1-eu>
</eu:eu-backbone>
```

---

## 7. What could not be found in the supplied files
* The **EG Module 1 eCTD Specification**, `eg-regional.dtd/.xml`, EG envelope module, EG validation criteria, EG accepted file formats, EDA controlled
  vocabularies for *Registration Type* and *Marketing Type*, the EDA baseline guidance and portal guide — none supplied (EG cites them in 2.5.2,
  2.9.2, 2.9.11, 2.11, 2.12, 3.2.2, 3.3.2, Annex 1).
* A **v3.x EU instance** of eu-regional.xml (the SPEC refers to "an annex to this specification" of XML examples — not in the supplied files).
  The doctype line in §2.1 is therefore derived, not quoted.
* An explicit EU sentence requiring the index.xml leaf to eu-regional.xml (only the ICH DTD content model and the example show it).
* Whether EG keeps CC/LL folders and the `procedure`/`country` envelope items (EG text is contradictory — §5.2).
* Internal EU inconsistencies noted, not resolved: SPEC p. 10 "EU-EMA" vs `ema`; SPEC App. 2 row 40 element `m1-5-2-generic-hybrid-biosimilar` vs DTD
  `m1-5-2-generic-hybrid-bio-similar`; HTG 2.4 cites non-existent VC "14 BP2"; HTG 4.11 says "submission type should be 'consolidating'" though
  `consolidating` is a submission-unit value; .svg/.bmp for mock-ups (FMT vs VC sheet).
* `eu_m1_ig_311.pdf` is the M1 *Specification* 3.1.1, not a separate Implementation Guide; no other "IG" document was supplied.
* The EG draft text was a cleaned extraction: table cells in EG 2.9.5 Table 1, 2.11.1 Table 3 and Annex 2 show no sequence numbers and Table 2 contains
  stray numbers ("447", "449" …) — possibly extraction loss; not verified against the original EG PDF.
