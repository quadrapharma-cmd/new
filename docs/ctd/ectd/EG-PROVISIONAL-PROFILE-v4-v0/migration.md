# EG eCTD v3.2.2 (draft) → eCTD v4.0: forward-compatibility mapping — provisional v0

> **PROVISIONAL — not issued by EDA.** Maps the EG Module 1 eCTD Specification **DRAFT v1.0** (v3.2.2, never adopted as
> of the sources) onto this provisional v4 profile. Tags **ICH / EU-DERIVED / EG-DRAFT / ASSUMPTION** as in `README.md`.
> Mechanism: ICH Forward Compatibility (FC), IG §8, §8.1, §8.1.1, §8.1.2 Table 9, §9.2.6–9.2.8, §9.2.17.1; rules
> eCTD4-020/021, -025, -026, -076, -078, -080; CR 00820, 00840. The Transition Mapping Message no longer exists
> (CR 00710, IG change history v1.5) — FC is the only route.

## 1. Principles (ICH, applied to Egypt)

| # | Rule | Source |
|---|---|---|
| M-01 | FC applies to **every** EG dossier that has v3.2.2 content when it switches to v4: lifecycle of *active* v3.2.2 leaves and reuse of v3.2.2 documents, also from applications not yet converted. | ICH IG §8 |
| M-02 | **No way back**: once EDA receives the first v4 SU of an application, any later v3.2.2 sequence for it is rejected. | ICH IG §8 |
| M-03 | First v4 sequence = last v3.2.2 number + 1, as a whole number (`0007` → `8`); folder `8/`. | ICH IG §8.1; EG-V4-003 |
| M-04 | The application UUID of the v3.2.2 envelope (`identifier`) is kept as `application/id/item@root`. | EU-DERIVED EU-IG "Application"; EG-DRAFT SPEC p.14 E3 |
| M-05 | Only **current** (active) v3.2.2 content can be lifecycled (replace / suspend); deleted or replaced leaves cannot. | ICH IG §8.1; eCTD4-026, -080 |
| M-06 | A v3.2.2 leaf can be: **suspended** (CoU `id` = leaf reference, no code/doc/keywords), **replaced** (`replacementOf/relatedContextOfUse/id` = leaf reference) or **reused** (`derivedFrom/documentReference/id` = leaf reference — the file is not re-sent; it keeps its v3.2.2 metadata). | ICH IG §8.1.1, §9.2.6–9.2.8, §9.2.8.2 |
| M-07 | A v4 CoU that replaces a v3.2.2 leaf must carry keywords equal to **all** that leaf's attributes / node-extensions / STF data; the **displayName** must match the v3.2.2 value exactly (codes are only pointers). The CoU heading may differ, the attribute set may not. | ICH IG §8.1.2, §9.2.18.2; CR 00820; eCTD4-025, -078 |
| M-08 | Node-extension titles → one **group title** keyword (`ich_keyword_type_11`); nested node-extensions joined with `_$`. | ICH IG §8.1.2 Table 9; CR 00840; VEN 2.2 (validation pending) |
| M-09 | Open regulatory activities at the switch: "Each region decides". **EG proposal:** continue the activity in v4; its `submission/id@root` is a new UUID created in the first v4 SU of that activity, `@extension` = the same EDA tracking number; SU type `response`/`additional-info` as usual. | ICH IG §8; proposal = ASSUMPTION |
| M-10 | Non-eCTD (paper / NeeS) dossiers do not use FC: they start in v4 with a `reformat` baseline (SU type `eg_su_reformat`, submission type `eg_st_none`, all CoUs new). | EG-DRAFT TG p.22 l.592–616; EU-IG "COMPATIBILITY…" ("Presumably, the same rules on baselining can be applied"); EG-V4-051 |

## 2. Leaf-reference syntax for EG v3.2.2 content — BLOCKED item

ICH patterns (IG §8.1.1; the IG text writes `.` before the leaf ID but its examples use `#` — follow the examples):

| Case | Pattern | EG example |
|---|---|---|
| Same application | `sequenceNumber.xmlType#leafID` | `0003.ich#ID-1234` (an M2–M5 leaf from `index.xml`) |
| Other application, by UUID | `UUID.sequenceNumber.xmlType#leafID` | `5f0e8436-e1df-4031-90d3-413deff109e5.0003.ich#ID-1234` |
| Other application, by number | `ApplicationTypeApplicationNumber.sequenceNumber.xmlType#leafID` | **not usable**: EDA has no application-number syntax (GAP) |

`id@root` = `2.16.840.1.113883.3.989.2.2.1.13.1` (ICH v3.2.2 FC namespace), `id@extension` = the leaf reference.
Sequence = the 4-digit v3.2.2 value.

**`xmlType` for leaves in `m1/eg/eg-regional.xml`:** the ICH "ICH XML Types" list (CV v1.0.3) contains only `ich`,
`us-regional`, `eu-regional`, `ca-regional`, `ch-regional`. **There is no Egyptian value.** Until ICH adds one
(change request by EDA to M8, README §4.1 step 4) **EG Module 1 v3.2.2 leaves cannot be referenced by FC at all** —
they can only be left as history and their content re-submitted as new v4 documents. This profile *reserves* the string
`eg-regional` (by analogy with `eu-regional`; the EU uses `eu-regional` for every EU M1 version, EU-IG "COMPATIBILITY…")
but **must not be used** before ICH publishes it (eCTD4-076/080 would reject it). M2–M5 leaves (`ich`) are not affected.
Tag: ICH (list content) + ASSUMPTION (reserved value).

## 3. Leaf operation → v4 lifecycle

| v3.2.2 (EG leaf, ICH DTD — SPEC p.7 l.52–53) | v4 | Source |
|---|---|---|
| `operation="new"` | new CoU (new UUID, `code`, `statusCode active`, `derivedFrom` new or reused document, keywords, `priorityNumber`) | IG §9.2.11.3 |
| `operation="replace"` + `modified-file` | new CoU + `replacementOf typeCode="RPLC"/relatedContextOfUse/id` (v4 CoU UUID, or FC leaf reference); same CoU code + keyword combination; 1:1, 1:n, n:1, n:n allowed | IG §9.2.7, §9.2.16.2–3; eCTD4-025 |
| `operation="delete"` | suspend: `priorityNumber`, same CoU `id` (or FC leaf ref), `statusCode="suspended"`, nothing else | IG §9.2.11.3.3; eCTD4-028, -080 |
| `operation="append"` | **removed in v4**: replace the original CoU (the appended content is lifecycled with it) or add a new CoU | IG §3.4; QA #2 |
| leaf `title` | `document/title/@value` (typo fix: `updateMode="R"`) | IG §9.2.15, §9.2.17.2.1 |
| `xlink:href` (relative, e.g. `../../../0000/m2/...`, SPEC p.8 l.62–67) | `document/text/reference/@value`, relative to `submissionunit.xml`; reuse of a file from another sequence = `../<seq>/m1/x.pdf` | IG §5.3, §9.2.17.3 |
| `checksum` (MD5) | `text/integrityCheck` SHA-256 + `integrityCheckAlgorithm="SHA256"` | IG §5.6, §9.2.15.2 |
| leaf `ID` | becomes the `#leafID` part of FC references only | IG §8.1.1 |
| `xml:lang` (leaf) | `document/text/@language` | IG §9.2.15.2 |
| `eg-regional.xml` leaf (always `new`, SPEC App.2 row 2) | **no equivalent** — the regional XML disappears into `submissionunit.xml` | IG §3.4, §5.1 |
| `util/dtd`, `util/style`, `m1/eg/util/dtd` (SPEC rows 180–183) | **not sent** | IG §5.1; EG-V4-011 |
| Cover letter leaves (always `new`, TG p.28 l.763) | keep history: never FC-replace; each v4 SU adds a new `eg_1.0` CoU | EG-V4-032 |

## 4. Attributes and folders → keywords / document metadata

| v3.2.2 (EG) | v4 | Must match on FC replace? | Source |
|---|---|---|---|
| `pi-doc@type` (`spc`, `pl`, `combined`, …) | CoU keyword, EG document type list | **yes** — displayName of the EG code must equal the v3.2.2 token | EG-DRAFT SPEC p.27; ICH IG §8.1.2 |
| `pi-doc@xml:lang` (`ar`/`en`) + language folder `131-spclabelpl/LL` | CoU keyword EG language + `text@language` | **yes** | EG-DRAFT SPEC App.2 rows 129–130; EU-DERIVED |
| `pi-doc@country` (`eg`) | CoU keyword EG country | **yes** | EG-DRAFT SPEC p.27 |
| node-extension in `m1-responses` (title = regulatory activity, SPEC p.10 l.137–142) | group title keyword | **yes** (exact title, nested with `_$`) | ICH IG §8.1.2 Table 9; CR 00840 |
| any other EG M1 leaf (no regional attributes defined, SPEC §5.2 "none") | no keyword | the v4 replacing CoU must carry **no** keyword (except group title if a node-extension existed) | ICH CR 00820 |
| ICH `index.xml` attributes `substance`, `manufacturer`, `product-name`, `dosageform`, `indication`, `excipient` (M2–M5) | ICH keywordDefinitions types 2, 3, 4, 5, 1, 6 (define first, then reference) | yes | ICH IG §8.1.2 Table 9 |
| STF `study-id`+`title`, `category`, `file-tag`, `property site-id` (M4/M5) | `ich_keyword_type_8` `studyID_$title`; ICH CV keywords; ICH document type; site id | yes | ICH IG §8.1.2 Table 9, §9.2.19; eCTD4-073 |
| EG fixed file-name components (`cover`, `tracking`, `generic`, …) | optional EG document-type keyword on `eg_1.0`, `eg_1.5.2` | **must be omitted** when replacing a v3.2.2 leaf (not a v3.2.2 attribute) | ASSUMPTION; ICH CR 00820 |

## 5. Envelope

Field-by-field mapping of `eg-envelope` to v4 classes: `rules.md` §6. The related-sequence chain is replaced by the
activity's `submission/id/@root` (`rules.md` §1).

## 6. Element-by-element mapping: all 151 EG Module 1 elements → v4 Context of Use

Generated from `cv/eg-m1-context-of-use.yaml`. "Docs? = no" means the heading is folder-only in v4 (TG Annex 5 italics / ASSUMPTION, see the YAML
`documents_allowed_basis`). If EDA ever accepted a v3.2.2 leaf directly under such a parent, it is FC-**replaced** by a
CoU on the appropriate child heading: the CoU code may differ between v3.2.2 and v4 as long as the keyword set matches
(ICH CR 00820; eCTD4-025).

| v3.2.2 element (`m1-eg/…`) | v3.2.2 folder (SPEC App.2) | → v4 CoU code | Docs? | Keywords when REPLACING a v3.2.2 leaf (must equal its attributes) | SPEC ref |
|---|---|---|---|---|---|
| `m1-0-cover` | `m1/eg/10-cover` | `eg_1.0` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 3, p.29 |
| `m1-2-form` | `m1/eg/12-form` | `eg_1.2` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 6, p.30 |
| `m1-2-1-af` | `m1/eg/12-form/121-af` | `eg_1.2.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 7, p.30 |
| `m1-2-2-legal` | `m1/eg/12-form/122-legal` | `eg_1.2.2` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 9, p.31 |
| `m1-2-2-1-loattor` | `m1/eg/12-form/122-legal/1221-loattor` | `eg_1.2.2.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 10, p.31 |
| `m1-2-2-2-manlic` | `m1/eg/12-form/122-legal/1222-manlic` | `eg_1.2.2.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 11, p.31 |
| `m1-2-2-3-gmpcert` | `m1/eg/12-form/122-legal/1223-gmpcert` | `eg_1.2.2.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 12, p.31 |
| `m1-2-2-4-trade` | `m1/eg/12-form/122-legal/1224-trade` | `eg_1.2.2.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 13, p.31 |
| `m1-2-2-5-toll` | `m1/eg/12-form/122-legal/1225-toll` | `eg_1.2.2.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 14, p.32 |
| `m1-2-2-6-sol` | `m1/eg/12-form/122-legal/1226-sol` | `eg_1.2.2.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 15, p.32 |
| `m1-2-2-7-import` | `m1/eg/12-form/122-legal/1227-import` | `eg_1.2.2.7` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 16, p.32 |
| `m1-2-2-8-storelic` | `m1/eg/12-form/122-legal/1228-storelic` | `eg_1.2.2.8` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 17, p.32 |
| `m1-2-2-9-authlet` | `m1/eg/12-form/122-legal/1229-authlet` | `eg_1.2.2.9` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 18, p.33 |
| `m1-2-2-10-managre` | `m1/eg/12-form/122-legal/12210-managre` | `eg_1.2.2.10` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 19, p.33 |
| `m1-2-2-11-pacagre` | `m1/eg/12-form/122-legal/12211-pacagre` | `eg_1.2.2.11` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 20, p.33 |
| `m1-2-2-12-storeagre` | `m1/eg/12-form/122-legal/12212-storeagre` | `eg_1.2.2.12` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 21, p.33 |
| `m1-2-2-13-othagre` | `m1/eg/12-form/122-legal/12213-othagre` | `eg_1.2.2.13` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 22, p.33 |
| `m1-2-2-14-term` | `m1/eg/12-form/122-legal/12214-term` | `eg_1.2.2.14` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 23, p.34 |
| `m1-2-2-15-tax` | `m1/eg/12-form/122-legal/12215-tax` | `eg_1.2.2.15` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 24, p.34 |
| `m1-2-2-16-distribut` | `m1/eg/12-form/122-legal/12216-distribut` | `eg_1.2.2.16` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 25, p.34 |
| `m1-2-2-17-ipp` | `m1/eg/12-form/122-legal/12217-ipp` | `eg_1.2.2.17` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 26, p.34 |
| `m1-2-2-18-newlegag` | `m1/eg/12-form/122-legal/12218-newlegag` | `eg_1.2.2.18` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 27, p.35 |
| `m1-2-2-19-loauth` | `m1/eg/12-form/122-legal/12219-loauth` | `eg_1.2.2.19` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 28, p.35 |
| `m1-2-2-20-pvagre` | `m1/eg/12-form/122-legal/12220-pvagre` | `eg_1.2.2.20` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 29, p.35 |
| `m1-2-2-21-gmpcert2` | `m1/eg/12-form/122-legal/12221-gmpcert2` | `eg_1.2.2.21` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 30, p.35 |
| `m1-2-3-edaapp` | `m1/eg/12-form/123-edaapp` | `eg_1.2.3` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 31, p.35 |
| `m1-2-3-1-regreq` | `m1/eg/12-form/123-edaapp/1231-regreq` | `eg_1.2.3.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 32, p.36 |
| `m1-2-3-2-inqapp` | `m1/eg/12-form/123-edaapp/1232-inqapp` | `eg_1.2.3.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 33, p.36 |
| `m1-2-3-3-nameapp` | `m1/eg/12-form/123-edaapp/1233-nameapp` | `eg_1.2.3.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 34, p.36 |
| `m1-2-3-4-reglic` | `m1/eg/12-form/123-edaapp/1234-reglic` | `eg_1.2.3.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 35, p.36 |
| `m1-2-3-5-prelimapp` | `m1/eg/12-form/123-edaapp/1235-prelimapp` | `eg_1.2.3.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 36, p.37 |
| `m1-2-3-6-nonrefapp` | `m1/eg/12-form/123-edaapp/1236-nonrefapp` | `eg_1.2.3.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 37, p.37 |
| `m1-2-3-7-exemptapp` | `m1/eg/12-form/123-edaapp/1237-exemptapp` | `eg_1.2.3.7` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 38, p.37 |
| `m1-2-3-8-price` | `m1/eg/12-form/123-edaapp/1238-price` | `eg_1.2.3.8` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 39, p.37 |
| `m1-2-3-9-pvapp` | `m1/eg/12-form/123-edaapp/1239-pvapp` | `eg_1.2.3.9` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 40, p.37 |
| `m1-2-3-10-insprep` | `m1/eg/12-form/123-edaapp/12310-insprep` | `eg_1.2.3.10` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 41, p.38 |
| `m1-2-3-11-importapp` | `m1/eg/12-form/123-edaapp/12311-importapp` | `eg_1.2.3.11` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 42, p.38 |
| `m1-2-3-12-cadcrep` | `m1/eg/12-form/123-edaapp/12312-cadcrep` | `eg_1.2.3.12` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 43, p.38 |
| `m1-2-3-13-stabstud` | `m1/eg/12-form/123-edaapp/12313-stabstud` | `eg_1.2.3.13` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 44, p.38 |
| `m1-2-3-14-stabprot` | `m1/eg/12-form/123-edaapp/12314-stabprot` | `eg_1.2.3.14` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 45, p.39 |
| `m1-2-3-15-m3app` | `m1/eg/12-form/123-edaapp/12315-m3app` | `eg_1.2.3.15` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 46, p.39 |
| `m1-2-3-16-m5app` | `m1/eg/12-form/123-edaapp/12316-m5app` | `eg_1.2.3.16` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 47, p.39 |
| `m1-2-3-17-preapplet` | `m1/eg/12-form/123-edaapp/12317-preapplet` | `eg_1.2.3.17` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 48, p.39 |
| `m1-2-3-18-varapp` | `m1/eg/12-form/123-edaapp/12318-varapp` | `eg_1.2.3.18` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 49, p.39 |
| `m1-2-3-19-ipsca` | `m1/eg/12-form/123-edaapp/12319-ipsca` | `eg_1.2.3.19` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 50, p.40 |
| `m1-2-3-20-reglicsolv` | `m1/eg/12-form/123-edaapp/12320-reglicsolv` | `eg_1.2.3.20` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 51, p.40 |
| `m1-2-4-declar` | `m1/eg/12-form/124-declar` | `eg_1.2.4` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 52, p.40 |
| `m1-2-4-1-regprod` | `m1/eg/12-form/124-declar/1241-regprod` | `eg_1.2.4.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 53, p.41 |
| `m1-2-4-2-apiman` | `m1/eg/12-form/124-declar/1242-apiman` | `eg_1.2.4.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 54, p.41 |
| `m1-2-4-3-liceholdpac` | `m1/eg/12-form/124-declar/1243-liceholdpac` | `eg_1.2.4.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 55, p.41 |
| `m1-2-4-4-liceholdbulk` | `m1/eg/12-form/124-declar/1244-liceholdbulk` | `eg_1.2.4.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 56, p.41 |
| `m1-2-4-5-apimanappl` | `m1/eg/12-form/124-declar/1245-apimanappl` | `eg_1.2.4.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 57, p.42 |
| `m1-2-4-6-apisupp` | `m1/eg/12-form/124-declar/1246-apisupp` | `eg_1.2.4.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 58, p.42 |
| `m1-2-4-7-siteadd` | `m1/eg/12-form/124-declar/1247-siteadd` | `eg_1.2.4.7` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 59, p.42 |
| `m1-2-4-8-allvar` | `m1/eg/12-form/124-declar/1248-allvar` | `eg_1.2.4.8` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 60, p.42 |
| `m1-2-4-9-decother` | `m1/eg/12-form/124-declar/1249-decother` | `eg_1.2.4.9` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 61, p.43 |
| `m1-2-4-10-countries` | `m1/eg/12-form/124-declar/12410-countries` | `eg_1.2.4.10` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 62, p.43 |
| `m1-2-4-11-tse` | `m1/eg/12-form/124-declar/12411-tse` | `eg_1.2.4.11` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 63, p.43 |
| `m1-2-4-12-bsesafdec` | `m1/eg/12-form/124-declar/12412-bsesafdec` | `eg_1.2.4.12` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 64, p.43 |
| `m1-2-4-13-rawmat` | `m1/eg/12-form/124-declar/12413-rawmat` | `eg_1.2.4.13` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 65, p.43 |
| `m1-2-4-14-exipsup` | `m1/eg/12-form/124-declar/12414-exipsup` | `eg_1.2.4.14` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 66, p.44 |
| `m1-2-4-15-albtraden` | `m1/eg/12-form/124-declar/12415-albtraden` | `eg_1.2.4.15` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 67, p.44 |
| `m1-2-4-16-albstabil` | `m1/eg/12-form/124-declar/12416-albstabil` | `eg_1.2.4.16` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 68, p.44 |
| `m1-2-4-17-plasdersub` | `m1/eg/12-form/124-declar/12417-plasdersub` | `eg_1.2.4.17` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 69, p.44 |
| `m1-2-4-18-nochaadd` | `m1/eg/12-form/124-declar/12418-nochaadd` | `eg_1.2.4.18` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 70, p.45 |
| `m1-2-4-19-pactype` | `m1/eg/12-form/124-declar/12419-pactype` | `eg_1.2.4.19` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 71, p.45 |
| `m1-2-4-20-insdeclet` | `m1/eg/12-form/124-declar/12420-insdeclet` | `eg_1.2.4.20` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 72, p.45 |
| `m1-2-4-21-sitemfdec` | `m1/eg/12-form/124-declar/12421-sitemfdec` | `eg_1.2.4.21` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 73, p.45 |
| `m1-2-4-22-storetemp` | `m1/eg/12-form/124-declar/12422-storetemp` | `eg_1.2.4.22` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 74, p.45 |
| `m1-2-5-refprod` | `m1/eg/12-form/125-refprod` | `eg_1.2.5` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 75, p.46 |
| `m1-2-5-1-refproddoc` | `m1/eg/12-form/125-refprod/1251-refproddoc` | `eg_1.2.5.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 76, p.46 |
| `m1-2-5-2-sciref` | `m1/eg/12-form/125-refprod/1252-sciref` | `eg_1.2.5.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 77, p.46 |
| `m1-2-5-3-reftradn` | `m1/eg/12-form/125-refprod/1253-reftradn` | `eg_1.2.5.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 78, p.46 |
| `m1-2-5-4-recph` | `m1/eg/12-form/125-refprod/1254-recph` | `eg_1.2.5.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 79, p.47 |
| `m1-2-6-importdoc` | `m1/eg/12-form/126-importdoc` | `eg_1.2.6` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 80, p.47 |
| `m1-2-6-1-cpp` | `m1/eg/12-form/126-importdoc/1261-cpp` | `eg_1.2.6.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 81, p.47 |
| `m1-2-6-2-loaff` | `m1/eg/12-form/126-importdoc/1262-loaff` | `eg_1.2.6.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 82, p.47 |
| `m1-2-7-reliance` | `m1/eg/12-form/127-reliance` | `eg_1.2.7` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 83, p.47 |
| `m1-2-7-1-sameness` | `m1/eg/12-form/127-reliance/1271-sameness` | `eg_1.2.7.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 84, p.48 |
| `m1-2-7-2-unredact` | `m1/eg/12-form/127-reliance/1272-unredact` | `eg_1.2.7.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 85, p.48 |
| `m1-2-7-3-rravar` | `m1/eg/12-form/127-reliance/1273-rravar` | `eg_1.2.7.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 86, p.48 |
| `m1-2-7-4-correspond` | `m1/eg/12-form/127-reliance/1274-correspond` | `eg_1.2.7.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 87, p.48 |
| `m1-2-7-5-lofchange` | `m1/eg/12-form/127-reliance/1275-lofchange` | `eg_1.2.7.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 88, p.49 |
| `m1-2-7-6-reject` | `m1/eg/12-form/127-reliance/1276-reject` | `eg_1.2.7.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 89, p.49 |
| `m1-2-8-composit` | `m1/eg/12-form/128-composit` | `eg_1.2.8` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 90, p.49 |
| `m1-2-8-1-compositcert` | `m1/eg/12-form/128-composit/1281-compositcert` | `eg_1.2.8.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 91, p.49 |
| `m1-2-8-2-spec` | `m1/eg/12-form/128-composit/1282-spec` | `eg_1.2.8.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 92, p.49 |
| `m1-2-8-3-compcalc` | `m1/eg/12-form/128-composit/1283-compcalc` | `eg_1.2.8.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 93, p.50 |
| `m1-2-8-4-pelletcomp` | `m1/eg/12-form/128-composit/1284-pelletcomp` | `eg_1.2.8.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 94, p.50 |
| `m1-2-8-5-opadry` | `m1/eg/12-form/128-composit/1285-opadry` | `eg_1.2.8.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 95, p.50 |
| `m1-2-8-6-capshell` | `m1/eg/12-form/128-composit/1286-capshell` | `eg_1.2.8.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 96, p.50 |
| `m1-2-8-7-synonyms` | `m1/eg/12-form/128-composit/1287-synonyms` | `eg_1.2.8.7` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 97, p.51 |
| `m1-2-9-coa` | `m1/eg/12-form/129-coa` | `eg_1.2.9` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 98, p.51 |
| `m1-2-10-postappch` | `m1/eg/12-form/1210-postappch` | `eg_1.2.10` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 99, p.51 |
| `m1-2-10-1-pacapp` | `m1/eg/12-form/1210-postappch/12101-pacapp` | `eg_1.2.10.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 100, p.51 |
| `m1-2-10-2-sumcavar` | `m1/eg/12-form/1210-postappch/12102-sumcavar` | `eg_1.2.10.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 101, p.51 |
| `m1-2-10-3-justpoc` | `m1/eg/12-form/1210-postappch/12103-justpoc` | `eg_1.2.10.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 102, p.52 |
| `m1-2-10-4-anydoc` | `m1/eg/12-form/1210-postappch/12104-anydoc` | `eg_1.2.10.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 103, p.52 |
| `m1-2-11-pop` | `m1/eg/12-form/1211-pop` | `eg_1.2.11` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 104, p.52 |
| `m1-2-12-analysreq` | `m1/eg/12-form/1212-analysreq` | `eg_1.2.12` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 105, p.52 |
| `m1-2-12-1-sop` | `m1/eg/12-form/1212-analysreq/12121-sop` | `eg_1.2.12.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 106, p.53 |
| `m1-2-12-2-sumvacc` | `m1/eg/12-form/1212-analysreq/12122-sumvacc` | `eg_1.2.12.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 107, p.53 |
| `m1-2-13-plasma` | `m1/eg/12-form/1213-plasma` | `eg_1.2.13` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 108, p.53 |
| `m1-2-13-1-pmf` | `m1/eg/12-form/1213-plasma/12131-pmf` | `eg_1.2.13.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 109, p.53 |
| `m1-2-13-2-plasbatch` | `m1/eg/12-form/1213-plasma/12132-plasbatch` | `eg_1.2.13.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 110, p.53 |
| `m1-2-13-3-pmfapp` | `m1/eg/12-form/1213-plasma/12133-pmfapp` | `eg_1.2.13.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 111, p.54 |
| `m1-2-14-scienadv` | `m1/eg/12-form/1214-scienadv` | `eg_1.2.14` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 112, p.54 |
| `m1-2-15-relpv` | `m1/eg/12-form/1215-relpv` | `eg_1.2.15` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 113, p.54 |
| `m1-2-15-1-valpsmfas` | `m1/eg/12-form/1215-relpv/12151-valpsmfas` | `eg_1.2.15.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 114, p.54 |
| `m1-2-15-2-updpsmf` | `m1/eg/12-form/1215-relpv/12152-updpsmf` | `eg_1.2.15.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 115, p.55 |
| `m1-2-15-3-latpsur` | `m1/eg/12-form/1215-relpv/12153-latpsur` | `eg_1.2.15.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 116, p.55 |
| `m1-2-15-4-updrmp` | `m1/eg/12-form/1215-relpv/12154-updrmp` | `eg_1.2.15.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 117, p.55 |
| `m1-2-15-5-egrmp` | `m1/eg/12-form/1215-relpv/12155-egrmp` | `eg_1.2.15.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 118, p.55 |
| `m1-2-16-relinsp` | `m1/eg/12-form/1216-relinsp` | `eg_1.2.16` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 119, p.55 |
| `m1-2-16-1-smfall` | `m1/eg/12-form/1216-relinsp/12161-smfall` | `eg_1.2.16.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 120, p.56 |
| `m1-2-16-2-fullinsprep` | `m1/eg/12-form/1216-relinsp/12162-fullinsprep` | `eg_1.2.16.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 121, p.56 |
| `m1-2-16-3-batchrep` | `m1/eg/12-form/1216-relinsp/12163-batchrep` | `eg_1.2.16.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 122, p.56 |
| `m1-2-16-4-recalls` | `m1/eg/12-form/1216-relinsp/12164-recalls` | `eg_1.2.16.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 123, p.56 |
| `m1-2-16-5-warnlet` | `m1/eg/12-form/1216-relinsp/12165-warnlet` | `eg_1.2.16.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 124, p.57 |
| `m1-2-16-6-annualrev` | `m1/eg/12-form/1216-relinsp/12166-annualrev` | `eg_1.2.16.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 125, p.57 |
| `m1-2-16-7-coldchain` | `m1/eg/12-form/1216-relinsp/12167-coldchain` | `eg_1.2.16.7` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 126, p.57 |
| `m1-3-pi` | `m1/eg/13-pi` | `eg_1.3` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 127, p.57 |
| `m1-3-1-spc-label-pl` | `m1/eg/13-pi/131-spclabelpl` | `eg_1.3.1` | yes | eg document type = `pi-doc@type`, eg language = `pi-doc@xml:lang`, eg country = `pi-doc@country` (all R); + group title only if the leaf sat under a node-extension | SPEC App.2 row 128, p.57 |
| `m1-3-2-mockup` | `m1/eg/13-pi/132-mockup` | `eg_1.3.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 131, p.58 |
| `m1-3-3-specimen` | `m1/eg/13-pi/133-specimen` | `eg_1.3.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 133, p.59 |
| `m1-3-4-consultation` | `m1/eg/13-pi/134-consultation` | `eg_1.3.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 135, p.59 |
| `m1-3-5-approved` | `m1/eg/13-pi/135-approved` | `eg_1.3.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 137, p.60 |
| `m1-3-6-braille` | `m1/eg/13-pi/136-braille` | `eg_1.3.6` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 139, p.60 |
| `m1-4-expert` | `m1/eg/14-expert` | `eg_1.4` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 141, p.61 |
| `m1-4-1-quality` | `m1/eg/14-expert/141-quality` | `eg_1.4.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 142, p.61 |
| `m1-4-2-non-clinical` | `m1/eg/14-expert/142-nonclinical` | `eg_1.4.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 144, p.62 |
| `m1-4-3-clinical` | `m1/eg/14-expert/143-clinical` | `eg_1.4.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 144, p.62 |
| `m1-5-specific` | `m1/eg/15-specific` | `eg_1.5` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 146, p.63 |
| `m1-5-1-bibliographic` | `m1/eg/15-specific/151-bibliographic` | `eg_1.5.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 147, p.63 |
| `m1-5-2-generic-hybrid-bio-similar` | `m1/eg/15-specific/152-generic-hybrid-bio-similar` | `eg_1.5.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 149, p.64 |
| `m1-5-3-data-market-exclusivity` | `m1/eg/15-specific/153-data-market-exclusivity` | `eg_1.5.3` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 151, p.65 |
| `m1-5-4-exceptional-circumstances` | `m1/eg/15-specific/154-exceptional` | `eg_1.5.4` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 153, p.66 |
| `m1-5-5-conditional-ma` | `m1/eg/15-specific/155-conditional-ma` | `eg_1.5.5` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 155, p.66 |
| `m1-6-environrisk` | `m1/eg/16-environrisk` | `eg_1.6` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 157, p.67 |
| `m1-6-1-non-gmo` | `m1/eg/16-environrisk/161-nongmo` | `eg_1.6.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 158, p.67 |
| `m1-6-2-gmo` | `m1/eg/16-environrisk/162-gmo` | `eg_1.6.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 160, p.68 |
| `m1-7-orphan` | `m1/eg/17-orphan` | `eg_1.7` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 162, p.69 |
| `m1-7-1-similarity` | `m1/eg/17-orphan/171-similarity` | `eg_1.7.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 163, p.69 |
| `m1-7-2-market-exclusivity` | `m1/eg/17-orphan/172-market-exclusivity` | `eg_1.7.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 165, p.70 |
| `m1-8-pharmacovigilance` | `m1/eg/18-pharmacovigilance` | `eg_1.8` | no | — (folder-only in v4; a v3.2.2 leaf found here is FC-replaced onto the right child heading, CR 00820) | SPEC App.2 row 167, p.71 |
| `m1-8-1-pharmacovigilance-system` | `m1/eg/18-pharmacovigilance/181-phvig-system` | `eg_1.8.1` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 168, p.71 |
| `m1-8-2-risk-management-system` | `m1/eg/18-pharmacovigilance/182-riskmgt-system` | `eg_1.8.2` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 170, p.72 |
| `m1-9-clinical-trials` | `m1/eg/19-clinical-trials` | `eg_1.9` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 172, p.73 |
| `m1-10-paediatrics` | `m1/eg/110-paediatrics` | `eg_1.10` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 174, p.73 |
| `m1-responses` | `m1/eg/responses` | `eg_responses` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 176, p.74 |
| `m1-additional-data` | `m1/eg/additional-data` | `eg_additional-data` | yes | none (EG M1 leaves carry no attributes); group title only if the leaf sat under a node-extension | SPEC App.2 row 178, p.75 |

Rows of SPEC Appendix 2 with no element (file-pattern rows, the `LL` sub-folder row 129, `eg-regional.xml` row 2, util
rows 180–183) are covered by §3–§4 above. Total App.2 rows: 185 = 151 elements + 1 root `m1-eg` (no v4 code; cf. `ich_2`
retired, CR 00790) + 33 file/folder/util rows.

## 7. Worked FC examples (EG)

**Replace an English SmPC sent in v3.2.2 sequence `0004`, leaf ID `ID-SPC-EN`, in v4 sequence `8`:**

```xml
<component>
  <priorityNumber value="1000"/>
  <contextOfUse>
    <id root="(new UUID)"/>
    <code code="eg_1.3.1" codeSystem="2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER.1.1.0"/>
    <statusCode code="active"/>
    <replacementOf typeCode="RPLC">
      <relatedContextOfUse><id root="2.16.840.1.113883.3.989.2.2.1.13.1" extension="0004.eg-regional#ID-SPC-EN"/></relatedContextOfUse>
    </replacementOf>
    <derivedFrom><documentReference><id root="(new document UUID)"/></documentReference></derivedFrom>
    <referencedBy typeCode="REFR"><keyword><code code="spc" codeSystem="…EG-PLACEHOLDER.1.9.0"/></keyword></referencedBy>
    <referencedBy typeCode="REFR"><keyword><code code="en"  codeSystem="…EG-PLACEHOLDER.1.10.0"/></keyword></referencedBy>
    <referencedBy typeCode="REFR"><keyword><code code="eg"  codeSystem="…EG-PLACEHOLDER.1.11.0"/></keyword></referencedBy>
  </contextOfUse>
</component>
```
`eg-regional` is the **reserved, not yet valid** xmlType (§2) — today this exact replace is impossible; the fallback is to
leave the v3.2.2 leaf as history (it cannot even be suspended without a valid leaf reference) and add the new SmPC as a
new CoU. This is the single largest migration risk for Egypt.

**Reuse a Module 3 document from v3.2.2 sequence `0000` (ICH leaf, works today):**
`<derivedFrom><documentReference><id root="2.16.840.1.113883.3.989.2.2.1.13.1" extension="0000.ich#ID-32P1"/></documentReference></derivedFrom>`
on a new CoU `ich_3.2.p.1` (ICH IG §8.1.1, §9.2.8).

## 8. Gaps

1. No EG value in ICH XML Types (§2) — blocks FC for all EG M1 v3.2.2 content.
2. No EDA application-number syntax — the `ApplicationTypeApplicationNumber` leaf-reference form cannot be used; use the UUID form.
3. The EG v3.2.2 DTD itself was never published (EG reference §8) — leaf IDs and the exact attribute set of EG leaves are
   unknown; this mapping assumes the SPEC tables are complete.
4. Open-activity handling at the switch is a regional decision not yet taken (M-09 is a proposal).
5. If EG v3.2.2 is never adopted (EDA moves straight to v4 in 2028), §2–§4 apply only to whatever v3.2.2 sequences were
   accepted in between; non-eCTD dossiers follow M-10.
