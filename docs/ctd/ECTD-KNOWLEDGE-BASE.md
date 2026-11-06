# eCTD Knowledge Base — what a tool needs to *produce* eCTD files for Egypt (EDA)

Collected 06/11/2026. **Knowledge and examples only — no tool code.** This is the entry point. The details live in three
reference files under `ectd/`, and the original specifications, schemas and examples are in `sources/ectd/`.

| File | What it gives you |
|---|---|
| `ectd/ICH-eCTD-3.2.2-reference.md` | ICH v3.2.2: the complete Appendix 4 folder/file table (379 rows), naming rules, `index.xml` + DTD verbatim, all 159 heading elements with attributes, lifecycle, MD5, M8 formats, all Q&As |
| `ectd/EU-M1-3.1.1-reference-model-for-EG.md` | EU Module 1 v3.1.1 — **the model the Egyptian draft was adapted from**: `m1/eu` tree, `eu-regional.xml` envelope DTD verbatim, all 111 EU validation criteria v8.2, accepted formats, a section-by-section map of EG draft ↔ EU HTG v6.0.1 with every Egyptian difference, and a real example sequence (`index.xml` + `eu-regional.xml`) |
| `ectd/ICH-eCTD-4.0-reference.md` | ICH v4.0 (IG v1.7, May 2026 cover; CV package v1.0.3; Q&A v1.10): `submissionunit.xml` (HL7 RPS), context-of-use codes (142), keywords, document reuse, lifecycle, SHA-256, rules eCTD4-001…085, what a region must define (EU draft IG as model), forward compatibility from v3.2.2, vendor-group status 30/09/2026 |
| `CTD-KNOWLEDGE-BASE.md` | Dossier *content*: EDA Module 1–5 requirements (NP.CAPP.065 v5), Module 3 rules, deficiencies, variation → sections, WHO QOS/QIS examples |
| `SOURCES-INDEX.md` · `RECONCILIATION-KB-v3.md` | Which document version is in force, and corrections to the external KB v3 |

## الخلاصة بالعربي

- **دلوقتي:** مسودة الهيئة (1/2026، ما اتعتمدتش) مبنية على **ICH eCTD 3.2.2**، ومعاها Module 1 مصري (`m1/eg/…`، و`eg-regional.xml`). ده **منقول تقريباً حرفياً من الدليل الأوروبي**، وفيه فروق مصرية محددة.
- **بعدين:** الهيئة أعلنت **eCTD 4.0 بالكامل في الربع الأول من 2028**، ومنظومة RPM في فبراير 2027. الـ 4.0 اختلافه جذري:
  - ملف واحد `submissionunit.xml` (HL7) بدل `index.xml` والـ regional.
  - SHA-256 بدل MD5.
  - context-of-use بدل الـ leaf، والمستند بيتعاد استخدامه بالـ UUID.
  - append اتلغى.
- **الناقص من الهيئة:** مواصفة الـ EG M1 (الـ DTD/XSD، وأسماء فولدرات Module 1، ونص الـ envelope)، ومعايير التحقق المصرية، والصيغ المقبولة، والقيم المعتمدة لـ Registration Type وMarketing Type. **من غيرهم مفيش أداة تقدر تطلّع ملف مصري يعدّي التحقق الآلي في البوابة.**
  - اللي متاح النهارده: كل الجزء المشترك (Modules 2–5 وقواعد ICH)، ونموذج كامل للـ Module 1 من الدليل الأوروبي.

## 1. The three layers of an eCTD file

| Layer | v3.2.2 (EDA draft, now) | v4.0 (EDA target Q1 2028) | Source status for Egypt |
|---|---|---|---|
| ICH backbone | `NNNN/index.xml` (DTD `ich-ectd-3-2.dtd`), `index-md5.txt`, `util/dtd`, `util/style`, `m2…m5` with fixed folder/file names | `N/submissionunit.xml` (root `PORP_IN000001UV`, ns `urn:hl7-org:v3`) + `sha256.txt`; no util folder | ✅ complete (ICH) |
| Regional Module 1 | `m1/eg/eg-regional.xml` + envelope (`eg-envelope`), folder `m1/eg/10-cover/` (`tracking-var.pdf`), `form-af.pdf`, `responses-…` | Regional CoU list, keyword lists and OIDs defined by EDA | ❌ EG spec not published; EU v3.1.1 / EU v4 draft IG are the models |
| Regional rules | 64-character names, **180-character path** (EDA draft; ICH allows 230), PDF 1.4–1.7/PDF-A, no security, one eCTD per strength/dosage form, Pass/Fail + Best-Practice validation | ICH: ≤ 64 per name, ≤ 180 path, ≤ 7 folder levels, special characters only `$ - _ + ! ' ( )` | ⚠️ partly in the draft; the criteria list is not published |

## 2. Facts that decide the design (each verified in its reference file)

**v3.2.2**
- Names: lowercase a–z, 0–9 and `-` only, one extension, ≤ 64 characters (ICH §App 2). The EDA draft repeats ≤ 64 and adds a path limit of **≤ 180** (ICH 230).
- The DTD spells the attribute **`dosageform`**. The specification tables and Q&A 49 write `dosage-form`, but only `dosageform` validates.
- `index-md5.txt` holds the 32-character MD5 of `index.xml` with no line ending (Q&A 48). A `delete` leaf has an empty checksum.
- Lifecycle `modified-file` = `../0001/index.xml#id`, one target per leaf; a replaced leaf cannot be targeted again. EDA: avoid `append`, and no lifecycle across sections.
- `m3-2-a-3-excipients` is not repeatable, so only one novel excipient fits in 3.2.A.3 (Q&A 12).
- **The EG draft's Annex 6 vocabulary has XML-unsafe values:** uppercase `PMF`, `var-pac-II` in the example table vs `var-pac-ii` in the vocabulary, and submission-mode names with spaces. Raise this with EDA before relying on it.
- Egypt vs EU in Module 1:
  - one eCTD per strength or dosage form;
  - authority code `EDA`;
  - no procedure-type or country rows;
  - extra envelope fields **Registration Type** and **Marketing Type**;
  - modes Single, Grouping, Parallel Single, Parallel Grouping;
  - no `closing` or `consolidating` units;
  - the 16-subsection M1.2 tree (Annex 5);
  - hard-copy legalised CPP and labelling; portal only; no e-signatures.

  The full list is in the EU reference §5.2.

**v4.0**
- Every ID is a UUID, compared case-insensitively (vendor group, 30/09/2026).
- A heading is a **context-of-use code**. The ICH CoU list OID is `2.16.840.1.113883.3.989.2.2.1.1.6`. The header must carry both the ICH and the regional IG OIDs (rule eCTD4-084).
- Lifecycle acts on the context of use: active, replace (1:1 / 1:n / n:1 / n:n) or suspend. "Obsolete" is set by the authority. A suspended context of use never comes back.
- Order within a context group is by **priority number** (whole number 1–999999).
- A document is sent once and reused by UUID across sequences and applications.
- Sequence folder `1…999999`. After v3.2.2 `0003`, the first v4 sequence is `4`. Old leaves are referenced through forward compatibility (`0000.ich#leafId`). Once v4 starts, v3.2.2 sequences are rejected.
- ICH defines no baseline or transition message any more (removed in IG v1.5).

## 3. Examples available (real files, in `sources/ectd/`)

| Example | Where | What it shows |
|---|---|---|
| EMA corrected example sequences (2009, EU M1 v1.x) | `EU_CorrectedExamples_2009.zip` | Full sequence trees with `index.xml`, `index-md5.txt`, `eu-regional.xml`, `util/`. Walked through in the EU reference §6, with what has changed since and a v3.1 rewrite of the envelope. The rewrite is a labelled derivation, not an EMA file. |
| ICH empty-folder template | `ICH_eCTD_Empty_Folder_Template_v3.02.zip` | The complete official v3.2.2 folder skeleton |
| ICH DTD / EU util | `ICH_ich-ectd-3-2_dtd.zip`, `EU_M1_util_v3.1.zip` | Schemas and stylesheets. The EU util MD5s match the checksums published in EU VC v8.2. |
| ICH v4.0 XSD + CV spreadsheets | `ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip`, `…CV_Package…` | Schemas and every code list. The IG has fragments, not a complete message; a minimal skeleton built from them is in the v4 reference and is labelled as a derivation. |
| WHO QOS-PD / QIS templates | `sources/WHO_PQ_*` | What the Module 2.3 *content* looks like |

## 4. Open items to get from EDA (before any eCTD output can be called "valid for Egypt")

1. **EG M1 specification:** `eg-regional` DTD/XSD, envelope element names, the `m1/eg` folder names beyond `10-cover`, and the M1 file names.
2. **EG validation criteria:** Pass/Fail and Best-Practice lists, with the "File-Folder Structure & Names" sheet.
3. **EG accepted file formats.**
4. Controlled vocabularies as files: submission type, unit and mode, **Registration Type**, **Marketing Type**. Also the case and spacing problems in Annex 6.
5. **v4.0 regional package** for 2028: EG CoU list for M1, regional keywords, the regional IG OID. ICH's XML-types list has no Egyptian value, so a v3.2.2 → v4 transition needs an ICH change request (v4 reference §8).
6. Final, adopted version of the eCTD technical guidance (the consultation ended 14/10/2026, per the external KB v3).

Where to look: the "EDA eCTD webpage" named in the draft (not found on the public site), the portal `reg-submit.edaegypt.gov.eg` after login, or a written enquiry to the General Administration for Human Pharmaceuticals Registration.

## 5. Hunt for the EG Module 1 specification (06/11/2026) — result

| Where searched | Result |
|---|---|
| EDA website: guideline and notice indexes, the internal site search («eCTD», «Module 1», «validation criteria»), `/en/ectd/` | Nothing. `/en/ectd/` returns a «Page Not Found» page with HTTP 200 |
| EDA public-consultation page for the eCTD draft | Links only the draft guidance PDF. No M1 specification attached |
| Submission portal `reg-submit.edaegypt.gov.eg` | **GoAnywhere** file-transfer login (`/webclient/Login.xhtml`) and nothing else. No public download area |
| EXTEDO/DAF webinar «Navigate Egypt's Digital Shift to eCTD» (**03/12/2025**, 14:30 Egypt time) | The announcement lists «Module 1 requirements, specifications and validation criteria». The documents are presented at registration-gated sessions and not published on the page |
| EXTEDO Egypt Q&A blog | «eCTD accepted from Q3/2025; mandatory January 2026 (for new pharmaceutical registrations)… An update from the authority is expected». Upload is a zipped package through a browser portal reachable from abroad |
| Web (LinkedIn posts, second-hand) | Describe an **EG Module 1 eCTD Specification Version 1.0 (2026)**: `eg-regional.xml`, with `eg-envelope` and `m1-eg`, used with the ICH spec; path ≤ 180; constant UUID; first sequence 0000. All of this is consistent with the draft guidance. **The document itself was not found publicly** |
| **GL.Bioinn.004 v5 (25/05/2026)**, biologicals file content | Annex I (new registration) and Annex II (re-registration) give Module 1 document lists «aligned with the eCTD format». They match the draft's M1.2 tree (cover letter, application form, product information, PV, legal, EDA approvals, declarations, imported-product documents). **Archived** in `sources/` |

**Conclusion:** the EG M1 specification v1.0 most likely exists but is distributed outside the public website, through the EXTEDO/DAF onboarding or to registered portal users. A company with a portal account or an EXTEDO/DAF contact can obtain it. It cannot be downloaded from here.
