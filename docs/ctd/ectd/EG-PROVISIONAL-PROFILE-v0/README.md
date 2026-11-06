# EG provisional regional profile v0 — eCTD v3.2.2, Module 1 Egypt

> **STATUS: PROVISIONAL — NOT ISSUED BY THE EGYPTIAN DRUG AUTHORITY (EDA).**
> EDA has published (for consultation, 2026) two drafts that describe an Egyptian Module 1 but **do not contain** the
> EG regional DTD, the controlled vocabularies or the validation criteria they refer to. This folder fills those gaps
> from the EU model (EU M1 v3.1.1 / util 3.1 / VC 8.2), as instructed by the owner («complete anything missing from the
> EU»), and merges everything the EDA drafts do say. It is a **specification and data deliverable for a future tool**
> (builder / validator), not an application. Replace any part as soon as EDA issues the real one.
> Built 2026-11-06.

## 1. Sources

| Short cite | Document | Where |
|---|---|---|
| **SPEC** | EDA draft *EG Module 1 eCTD Specification*, Version 1.0, Year 2026 (79 p.) — cited by PDF page and margin line `l.` | `docs/ctd/sources/EDA_EG-Module1-eCTD-Specification_DRAFT_v1.0_2026.pdf`; extraction `docs/ctd/ectd/EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md` |
| **TG** | EDA draft *Technical Guidance for eCTD Submissions in Egypt* v1.0/2026 (75 p.) — PDF page + margin line | `docs/ctd/sources/EDA_eCTD-technical-guidance_DRAFT_v1_2026.pdf` |
| **HPG** | EDA draft *EG Human Pharmaceutical Module 1 Submission Guidance*, Version 1, 2026 (68 p.) — PDF page + margin line. Not in the original input list; found in the repository and used **only** for registration/marketing-type labels and the 1.2.3.18 sub-folder point | `docs/ctd/sources/EDA_EG-Human-Pharma-Module1-Submission-Guidance_DRAFT_2026.pdf` |
| **EU** | EU Module 1 eCTD Specification v3.1.1 and util package 3.1 (`eu-regional.dtd`, `eu-envelope.mod`, `eu-leaf.mod`, `eu-regional.xsl`; MD5s equal the values published in VC 3.3/4.3/5.3/6.3 — re-checked 2026-11-06) | `docs/ctd/ectd/EU-M1-3.1.1-reference-model-for-EG.md` |
| **VC** | EU Region eCTD Validation Criteria v8.2 (June 2025), sheet "eCTD Validation Criteria", 111 criteria | (xlsx used as build input) |
| **ICH** | ICH eCTD v3.2.2, `ich-ectd-3-2.dtd` (MD5 `1d6f631cc6b6357f0f4fe378e5f79a27`), `ectd-2-0.xsl` (`3a07a202455e954a2eb203c5bb443f77`) | `docs/ctd/ectd/ICH-eCTD-3.2.2-reference.md` |

## 2. Provenance rule

Every element, attribute, value and rule in this folder carries one tag:

* **EG-DRAFT** — stated in an EDA draft (SPEC / TG / HPG), with page (and line where printed).
* **EU-DERIVED** — taken from EU v3.1.1 / DTD 3.1 / VC 8.2, with the EU reference.
* **ASSUMPTION** — our choice where both are silent, with the reason. A tool must treat ASSUMPTION items as
  *configurable* and, in validation, report them as warnings/information, never as hard failures.

Where an EDA draft gives a label but not a token (e.g. "Imported Bulk"), the **label** is EG-DRAFT and the **token** is
ASSUMPTION; the vocab file says so.

## 3. Contents

| Path | What | Status |
|---|---|---|
| `util/dtd/eg-regional.dtd` | EG regional DTD: root `eg-backbone` → `eg-envelope` + `m1-eg`; full m1-eg tree from SPEC Appendix 2 (152 sections: 19 parents without documents, 131 leaf containers, 1.3.1 with `pi-doc`) | derived from `eu-regional.dtd` 3.1 |
| `util/dtd/eg-envelope.mod` | Envelope (SPEC App. 1.1): EU envelope minus `procedure`, plus `registration/@type`, `marketing/@type`; EG vocabularies | derived from `eu-envelope.mod` 3.1 |
| `util/dtd/eg-leaf.mod` | ICH leaf + node-extension, unchanged (SPEC p.7 l.52-53) | copy of `eu-leaf.mod` 1.4 body |
| `util/dtd/ich-ectd-3-2.dtd`, `util/style/ectd-2-0.xsl` | ICH files, unchanged | ICH |
| `util/style/eg-regional.xsl` | XSLT 1.0 style sheet: EG envelope (with labels for every vocabulary value) + a table of **all** 151 EG M1 headings whether populated or not (SPEC p.6 l.29-31; TG p.26 l.707-709). Leaf / node-extension templates copied from `eu-regional.xsl` 3.1 | minimal adaptation — feasible, done |
| `vocab/*.yaml` | submission-type (50), submission-unit (7), submission-mode (4), registration-type (6), marketing-type (4), pi-doc-type (7), language (2), country (1), agency-code (1) — each value with label, provenance, source page, note; plus `excluded_values` (EU values deliberately left out, with reason) | |
| `validation-criteria.csv` / `.md` | All 111 EU VC 8.2 criteria mapped (54 KEEP, 44 ADAPT, 13 DROP) + 43 EG-specific rules → **141 active rules: 87 Pass/Fail, 54 Best Practice** | |
| `folders.csv` | Complete `m1/eg` map: 152 sections + language folder + regional XML + util rows (158 rows), element, parent, kind, directory, file-name pattern and its provenance (33 EG-DRAFT, 106 ASSUMPTION — every 1.2.x leaf section; 19 parents hold no files) | |
| `examples/0000/` | Minimal sequence: `index.xml`, `index-md5.txt`, `m1/eg/eg-regional.xml`, 6 placeholder PDFs (cover, tracking, form-af, proof of payment, SmPC en, PL ar), `util/` copies | validated (§6) |
| `_build/` | `build_profile.py` + `profile_data.py` (vocabularies) + `rules_data.py` (VC mapping, EG rules) — the **one source** of everything above; deterministic (two runs → identical MD5s) | |

Rebuild (EU util package and VC xlsx are build inputs, not stored here):
`python3 -I _build/build_profile.py --eu-util <EU util dir with dtd/ and style/> --eu-vc <eu VC 8.2 xlsx>`.
Change a vocabulary or rule in `_build/*.py`, never in the generated files.

Rule ids: `EG-PF-x` = the task's "EG-P/F-x" (slash dropped so ids are safe in file names/URLs); `EG-BP-x` Best Practice.
Kept/adapted EU rules keep the EU number (`EG-PF-15.3` ← VC 15.3); EG-only rules are `EG-PF-E01…E13`, `EG-BP-E01…E30`.

## 4. Decision log (every conflict; chosen value, reason, alternative kept on record)

| # | Topic | Conflict (with cites) | Chosen | Reason | Alternative noted |
|---|---|---|---|---|---|
| D-01 | Agency code | SPEC p.18 & App. 2.4 p.78 l.336-337 `EG-EDA` vs TG p.27 l.743 "This authority code is 'EDA'" | **`EG-EDA`** | SPEC is the XML specification and prints it twice; matches EU `CC-ACRONYM` pattern | `EDA` (vocab/agency-code.yaml `excluded_values`) |
| D-02 | Major variation token | TG Annex 6 p.60 `var-pac-ii`; TG p.17 Table 1 & p.23 Table 3 `var-pac-II`; SPEC p.23-25 `Var PAC-II`; SPEC p.14 N.B. "elements must remain Arabic" | **`var-pac-ii`** | Annex 6 is the CV table; all other tokens are lower case; XML is case-sensitive so one spelling only. SPEC N.B. is an EU remnant (EU tokens `var-type2`) contradicted by EDA's own tokens | `var-pac-II` (rejected by DTD — tested) |
| D-03 | PMF token | TG p.65 prints `PMF` | **`pmf`** | lower-case convention of every other token; EU `pmf` | `PMF` |
| D-04 | `withdrawal` scope | TG Annex 6 lists it only for Biologics/Innovative (p.65); SPEC p.26 l.291-294 & TG p.38 l.1064 general; SPEC p.26 Table 5 `Withdrawal` | **`withdrawal`, all product types** | the procedural text is general | restrict to BI |
| D-05 | Unit typos | SPEC p.25 Table 4 `responses`, l.285 `Response`, TG p.39 l.1074 'Response' | **`response`** | Annex 6 token | — |
| D-06 | Mode tokens | SPEC p.8 l.79 `parallel-single`/`parallel-grouping`; SPEC p.15 "parallel  grouping"; TG p.72 titles "Parallel Single/Grouping"; TG p.17 l.430 "grouped" | **`single`, `grouping`, `parallel-single`, `parallel-grouping`** | only token-shaped spelling in either draft; DTD tokens cannot contain spaces | title-case forms |
| D-07 | Marketing types | SPEC p.19 "e.g. Local or Tender and Export"; HPG p.52 "Local/Tender/Export/Hospital use" | **`local`, `tender`, `export`, `hospital`** | HPG lists them separately; `hospital` included so a hospital pack is not rejected | single value `tender-and-export` |
| D-08 | Country folders / `specific` element | SPEC p.9 l.100 "Country directories are named according to Appendix 2.1" and code `CC` (p.28) vs **no** App. 2 row using `CC` (rows 1-183); TG 3.2.1 drops the EU country sentence | **No CC folders, no CC file prefixes, no EU `specific` wrapper**; `pi-doc/@country` kept (fixed `eg`) | the table and TG agree; one country only | EU `specific country="eg"` + `CC/` folders |
| D-09 | DTD file name | SPEC names only the .mod files (p.7 l.50-51); string `eg-regional.dtd` absent | **`eg-regional.dtd`** (ASSUMPTION) | mirrors `eu-regional.dtd`, consistent with `eg-regional.xml` | — |
| D-10 | DTD location | SPEC row 181 `m1/eg/util/dtd` vs row 182 `util/dtd` (p.76-77) | **`util/dtd`**; `m1/eg/util` unused (EG-BP-E28) | EU has the same two rows (EU App. 2 rows 73-75) and VC 3.2/4.2/5.2 put the files in `util/dtd`; empty folders are forbidden (TG p.26 l.698-699) | `m1/eg/util/dtd` |
| D-11 | Style-sheet name | not stated (SPEC p.6 l.29-31, row 183) | **`eg-regional.xsl`** (ASSUMPTION) | mirrors EU | — |
| D-12 | `procedure` element | in EU; absent from SPEC App. 1.1 and TG 3.2.2 | **dropped** | both EG drafts silent; one procedure type | EU `procedure/@type` |
| D-13 | High-level `number` with grouping | SPEC p.16: leave empty when one MA; TG p.27 l.730-733: "If submission mode is set to 'grouping' there should be a Submission Number" (and l.728-729 "not required in case only one product") | **optional in DTD; EG-BP-14.BP4 = information only** | TG contradicts itself; SPEC = EU logic | P/F requirement |
| D-14 | Per-variation sub-folders in 1.2.3.18 | HPG p.33 l.1007-1009 "Every variation … in separate sub folder" vs EU "no additional folders" (VC 15.BP2) | **allowed, one level, paired with a node-extension** | SPEC p.10 l.133-136 allows node-extension sub-folders outside M5 | no sub-folder |
| D-15 | Number of envelopes | SPEC p.14 `envelope` "Repeatable" but only country `eg` | **DTD `envelope+` (as printed), rule EG-PF-E01: exactly one** | keeps DTD faithful, removes ambiguity | DTD `envelope` |
| D-16 | pi-doc types | SPEC App. 2.3 p.78 `spc`, `pl`; footnote `interpack`; App. 1.2 p.27 example `combined`; SPEC p.11 `outer`; TG p.19 l.473 `other` | **`spc, pl, interpack, outer, impack, combined, other`** | union of what the drafts use + EU `impack` (counterpart of `interpack`); EU `annex2` dropped (EU Annex II) | SPEC's 2-value list |
| D-17 | Application-form name | SPEC row 8 `form-af-VAR`, TG p.29 l.787-789 `form-af.pdf` vs SPEC p.11 l.169 example `form-eaf.pdf`, `form-annex-01.pdf` | **`form-af(-var).pdf`** | table + TG agree; `eaf`/annex are EU remnants | `form-eaf` |
| D-18 | Response sub-folders | SPEC p.10 l.133-136 sub-folders optional vs TG p.20 l.520-522 "additional folders in m1-responses are not allowed" | **no sub-folders in `m1/eg/responses`** (EG-BP-E18); node-extensions in XML | stricter text; EU identical | allow |
| D-19 | Supportive documents not in M2-5 / responses | SPEC row 178 → Additional Data vs TG p.29 l.790-792 → section 1.2; TG p.30 l.828-829 and HPG p.45 limit Additional Data to info not in the EG M1 spec | **1.2 sub-section (e.g. 1.2.10.4) first; Additional Data only for content no EG section covers** | 2 of 3 texts | SPEC row 178 reading |
| D-20 | Root element | SPEC p.7 l.48-49 `eg-backbone` vs SPEC p.14 l.242 "`eg-envelope` … root element" | **`eg-backbone`, unprefixed, no own namespace** | p.7 describes the whole file; p.14 is the envelope table's root. Unprefixed because EDA gives no namespace URI and inventing one would be worse | EU style `eg:eg-backbone xmlns:eg="…"` (a tool should make the root QName configurable) |
| D-21 | `dtd-version` | not stated | **`#FIXED "0.1"`** (ASSUMPTION) | EU has `#FIXED "3.1"`; needed by VC 3.4/3.5 | — |
| D-22 | `procedure-tracking/number` | printed in the *Attribute* column (SPEC p.17) | **element** | EU element; SPEC p.16 high-level `number` is an element | attribute |
| D-23 | `invented-name` | SPEC p.18 "Mandatory / Repeatable … should not be repeated" | **DTD `invented-name+`, EG-BP-E08 one** | faithful + practical | — |
| D-24 | Envelope order | not stated as a content model | **order of SPEC App. 1.1 table**: identifier, submission, submission-unit, applicant, agency, invented-name, registration, marketing, inn, sequence, related-sequence, submission-description | only order EDA gives | EU order + new elements |
| D-25 | `inn` | SPEC p.19 Optional; EU VC 14.8 P/F for maa+initial | **optional; EG-BP-14.8** | do not contradict EDA | P/F |
| D-26 | registration / marketing | SPEC p.18-19 elements with `@type` | **EMPTY elements with `type` #REQUIRED enumerations** | as printed; CVs unpublished, tokens ASSUMPTION | CDATA (lenient) |
| D-27 | File names 1.2.2-1.2.16 | SPEC rows 9-126: folders only (GAP) | **`<folder name without number>-VAR.EXT`**, e.g. `1221-loattor/loattor-…pdf` (ASSUMPTION) | EU CC-FIXED-VAR style without CC; fixed names are only BP (VC 15.BP3) | free names |
| D-28 | m1-eg optionality | not stated | **EU optionality: `m1-0-cover` required, all others optional; 1.6 one-of** | cover letter + tracking table always (TG p.16 l.390-391); 1.6 rule SPEC rows 159/161 | — |
| D-29 | `related-sequence` when unit ≠ initial/reformat | EU VC 14.7 "≠"; SPEC p.21 l.253-255 and TG p.17 l.416-417 "<" | **"<" (EG-PF-14.7)** | EDA text | EU "≠" |
| D-30 | Security settings | EU VC 16.3/16.4 exempt 1.0/1.2/3.3/4.3/5.4; TG p.22 l.580-589 no exemption except signed documents (print + copy allowed) | **EG text (EG-PF-16.3; 16.4 dropped)** | EDA text | EU exemptions |

### Where the EG drafts contradict themselves (beyond the table above)
* TG p.23 l.606 "The submission type reformat" — `reformat` is a submission **unit** (TG p.74, SPEC p.25).
* TG p.10 l.212 calls `corrigendum` a submission type; TG Annex 6 p.73 lists it as a unit.
* SPEC p.15 defines `parallel-single` and `parallel-grouping` identically; TG p.72 the same.
* UUID examples: SPEC p.14 `25635f23-a3a4-c4e0- b994-…` and TG p.14 `123e4567-e89b-12d3-a456- 426655440000` both contain a space and neither is version 4, while SPEC p.12 l.200-201 recommends version 4. TG p.24 l.637-638 allows a new UUID only on re-baselining; SPEC p.12 l.214-218 adds a new UUID re-sent under the same sequence number.
* SPEC p.7 l.54-57 promises XML examples in Appendices 1 and 2 — none exist; SPEC Glossary "Samples are provided in the EG M1 Specification" refers to itself.
* SPEC rows 144/145 used twice; row 5 uses `/XXXX/` not `DDDD`; seven directory rows have a trailing slash (all normalised in `folders.csv`).
* The full list of 38 issues is in `docs/ctd/ectd/EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md` §10.

## 5. What is EG-only (not in the EU model)
`registration/@type`, `marketing/@type`, the four submission modes incl. parallel assessment, the 50 EG submission types
(TG Annex 6), the 120-entry 1.2 tree (16 sub-sections), the `ar` language, one eCTD per strength/dosage form
(TG p.11 l.225-229), the `DDDD-workingdocuments` folder (SPEC Glossary p.4-5; TG p.21 l.536-538), "no validation reports"
(TG p.21 l.539-541), no electronic signatures (TG p.22 l.591), mandatory EDA portal (TG p.26 l.686-688).

## 6. Validation result of `examples/0000` (run 2026-11-06, libxml 2.9.14 / xmllint 20914)

```
$ cd examples/0000
$ xmllint --noout --valid index.xml                 -> valid (no output, exit 0)
$ xmllint --noout --valid m1/eg/eg-regional.xml     -> valid (no output, exit 0)
index-md5.txt == md5(index.xml)                      -> 39b9841028f208e92e828203b3069f12 (match)
6/6 leaf checksums (md5) match their files; all PDFs %PDF-1.4, 1 page, not encrypted (pdfinfo)
longest path from sequence folder: 0000/m1/eg/13-pi/131-spclabelpl/en/spc.pdf = 42 chars (limit 180)
eg-regional.xsl applied with lxml XSLT -> HTML rendered, 151 section headings shown, envelope labels resolved
```

Negative tests (copy of the example, one change each, `xmllint --valid` must **reject**) — all rejected as intended:
agency `EDA`; type `var-pac-II`; EU unit `consolidating`; missing `registration`; pi-doc type `annex2`;
pi-doc `xml:lang="fr"`; envelope country `ema`; a leaf directly inside parent `m1-2-form`; `inn` placed before
`marketing`. Control: `type="var-pac-ii" mode="parallel-grouping"` accepted.

Checksums of the provisional util files (for EG-PF-3.3/4.3/5.3/6.3 in "warning" mode until EDA publishes its own):
`eg-regional.dtd fc48ce1b3cce9168bc1e80244af02c62` · `eg-envelope.mod ee07b29a8ec5a0f490157751131b7913` ·
`eg-leaf.mod e790612a037d6010e8bdf150b7d5351d` · `eg-regional.xsl 427b5606000e041db0631b7684b0dfc5`.

What the DTD cannot check (left to `validation-criteria.csv`): mode-required-for-variations (EG-PF-E04),
reformat⇔none (E05), related-sequence arithmetic (14.6/14.7), non-empty text (E06), lifecycle, files and PDFs.

## 7. Top risks
1. **Everything here can be overruled by the real EDA util package.** Root name/namespace, DTD file name, `dtd-version`, element order and optionality are ASSUMPTIONS; a tool built on them must keep them configurable.
2. **Registration and marketing type tokens are guesses** (only labels are in the drafts). A wrong token makes a real submission DTD-invalid → keep these two enumerations loadable from `vocab/*.yaml`.
3. **Agency code `EG-EDA` vs `EDA`** — a 50/50 conflict between the two EDA drafts.
4. **Submission-type tokens**: Annex 6 is a draft table with case inconsistencies (`var-pac-II`, `PMF`); EDA may change tokens.
5. **1.2.x fixed file names (106 patterns) are ours**; only BP, but builders that hard-code them will need renaming.
6. **Validation criteria**: no EDA VC exists; P/F rules derived from EU could reject submissions EDA would accept — run ASSUMPTION rules as warnings.
7. Single-country design (no `CC`) — if EDA keeps SPEC p.9 l.100 country folders, paths for 1.0, 1.2, 1.3.x, responses and additional-data change.
