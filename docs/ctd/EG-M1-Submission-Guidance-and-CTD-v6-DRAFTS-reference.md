# ⚠️ DRAFT — EDA "EG Human Pharmaceutical Module 1 Submission Guidance" (v1/2026) and NP.CAPP.065 v6 (CTD submission guidance) — reference and diff vs v5

> **STATUS: BOTH DOCUMENTS ARE DRAFTS under EDA public consultation (15/10/2026 – 29/10/2026, as given by the EDA download page / task brief; the PDFs themselves carry no consultation dates, no issue date and no effective date).**
> **Nothing here is in force.** The in-force CTD guidance remains **EDREX:NP.CAPP.065 v5 (issue/effective 01/11/2025)** — summarised in `CTD-KNOWLEDGE-BASE.md` §3–4.
> Everything below is taken from the PDFs only (read in full with `pdftotext -layout`, tables checked with `pdfplumber`, image-only pages rendered and read). Page numbers are the printed page numbers (they equal the PDF page numbers in all three files). "l." = the draft's own line numbers where it has them. Where the drafts are silent or contradict themselves, it is said plainly (marked **GAP** or **INCONSISTENCY**). Interpretations of mine are marked *(interpretation)*.

Sources (archived copies are byte-identical to the downloads, checked with `cmp`):

| Tag | Document | URL | Local copy |
|---|---|---|---|
| **A** | EG Human Pharmaceutical Module 1 Submission Guidance, Version 1, Year 2026, Code: *(blank)* — 68 pp. | https://edaegypt.gov.eg/media/odgpnm43/draft-of-eg-human-pharmaceutical-module-1-submission-guidance-2.pdf | `sources/EDA_EG-Human-Pharma-Module1-Submission-Guidance_DRAFT_2026.pdf` |
| **B** | Submission Guidance for The Common Technical Document for Human Pharmaceutical Products, EDREX:NP.CAPP.065, Version 6, Year 2026 — 20 pp. | https://edaegypt.gov.eg/media/rdoj1r25/draft-of-submission-guidance-for-ctd-for-human-pharmaceutical-products-2.pdf | `sources/EDA_NP.CAPP.065_v6_DRAFT_2026_CTD-submission-guidance.pdf` |
| **v5** | Same title + "Registration", EDREX:NP.CAPP.065, Version 5, issue/effective 1/11/2025 — 30 pp. (in force) | — | `sources/EDA_NP.CAPP.065_v5_2025_CTD-submission-guidance.pdf` |
| **eCTD** | Technical Guidance for eCTD Submissions in Egypt, v1.0, 2026 (DRAFT) — Annex 5 "Section 1.2" (Table 7) | — | `sources/EDA_eCTD-technical-guidance_DRAFT_v1_2026.pdf` |
| **SPEC** | EG Module 1 eCTD Specification, v1.0, Year 2026 (DRAFT), Code blank | — | `sources/EDA_EG-Module1-eCTD-Specification_DRAFT_v1.0_2026.pdf` |

---

## الخلاصة بالعربي (للدكتور هيثم)

- **المسودتين مش ساريتين.** الساري لحد دلوقتي هو NP.CAPP.065 الإصدار 5 (01/11/2025).
- **المسودة A (68 صفحة) هي الجديدة:** دليل كامل لـ Module 1 بس، بترقيم الـ eCTD المصري (1.0 / 1.2.1 … 1.2.11 / 1.3.1 / 1.3.2 / Responses / Additional Data). كل مستند مكتوب له: إمتى يتقدم (تسجيل جديد / متغير / موافقة مبدئية لإعادة التسجيل / تجديد)، ولأي نوع مستحضر (محلي / F-Toll / تول / ترخيص / مستورد ومستورد بالك)، وشروطه (توثيق بنك / الشئون القانونية بالهيئة / غرفة تجارية + سفارة / الشهر العقاري / ورق الشركة / ختم وتوقيع).
- **فيها 3 ملاحق:** (1) جدول تتبع الـ sequences، (2) استمارة التسجيل/إعادة التسجيل — هي نفسها Annex I بتاع v5 حرفياً، (3) استمارة المتغيرات + 6 نماذج تعهدات بالعربي.
- **المسودة B (الإصدار 6 من دليل الـ CTD):** شالت استمارة التسجيل (Annex I) ونقلتها للمسودة A، وغيّرت Module 1 بالكامل لترقيم الـ eCTD (1.2.x بدل 1.1.x/1.2.x القديم)، وأحالت التفاصيل للمسودة A.
- **Modules 2 و3 و4 زي ما هم بالظبط.**
- **Module 5 اتغير في 4 بنود للجنيس:** 5.3.2.2 بقى NR، و5.3.3.1 بقى NR، و5.3.5.4 بقى NR، و5.3.7 (CRFs) بقى Optional. 5.3.1.2 (BE) و5.3.1.4 فضلوا R.
- **أهم تغيير عملي:** Unredacted Assessment Report بقى **R** للمستورد (كان O). كمان Module 1 في v6 بيقول R للمحلي في بنود كتير كانت NR (قائمة الدول، إقرار مصنعي المادة الخام، الـ solvent، الفارماكوبيا…).
- **تناقضات لازم تتسأل للهيئة:**
  - B بيطلب 1.3.5 «Product Information already approved in the member states»، وA مفيهوش.
  - B بيطلب Packaging Agreement للمحلي، وA بيقصره على المستورد بالك.
  - الـ CEP والتعهد الخاص بيه اختفوا كبند مستقل.
  - مصطلح «F-Toll» مش متعرّف في أي مكان.
- التفاصيل الكاملة والأسئلة المقترحة للهيئة في §6 و§7.

---

## 1. Identity of each draft

| | **A — EG Human Pharmaceutical Module 1 Submission Guidance** | **B — NP.CAPP.065 v6** |
|---|---|---|
| Type | "Notice to applicant" (header, every page) | "Notice to applicant" (header) |
| Issuer | Central Administration of Pharmaceutical Products — General Administration of Human Pharmaceuticals Registration (p.1) | Same CA — "General Administration For Human Pharmaceuticals Registration" (p.1) |
| Code | **blank** ("Code:" empty, p.1 and every footer) | **EDREX:NP.CAPP.065** (p.1) |
| Version / year | **1 / 2026** ("Version/Year: 1/2026", footers) | **6 / 2026** (footers); history table: "6 — 10/2026" (p.20) |
| Issue / effective date | blank / blank (p.1) | blank / blank (p.1) |
| PDF metadata | created 15 Oct 2026 07:27 UTC (Word 365 → iLovePDF) | created 15 Oct 2026 07:28 UTC |
| Pages | 68 | 20 |
| Watermark | "Draft" diagonal watermark on pages (visible in rendered pp.6, 7, 49) | — (text-only check) |
| Scope (verbatim) | "This notice to applicant is applied for both local and imported Human Pharmaceutical Products that are submitting their applications for **registration, re-registration or variation**." (p.3, l.8–10) | "This guidance is applied to local and imported pharmaceutical products. It provides a standardized approach to the submission of regulatory information…" (p.3, l.1–4) |
| Purpose | "…guidance on the format of Module 1 of the human pharmaceutical products and indicates where the information should be located in the Module." Module 1 = "specific EG-requirements for the administrative data (e.g. the application form, the proposed summary of product characteristics, labelling and package leaflet, etc.)" (p.3, l.1–7) | Format of a well-organised CTD dossier (Modules 1–5) with an R/NR/O/P matrix (p.3, l.6–12) |
| Product categories used | **Registration types:** Locally Manufactured Products; **F-Toll** Products; Toll Products; Under License Products; Imported / Imported Bulk Products (p.9–12, Fig. 2 p.7). "Innovator" appears only in the PIL declaration (p.36) and Annex 3 ("The Product Is Innovator", p.55). | **Columns:** I (Innovators), G (Imported), G (Local) (p.3) |
| Regulatory activities (routes) | **New Registration · Variation · Re-registration Preliminary Approval · Renewal** (e.g. p.8). Variation sub-routes in Annex 3: Single / Grouped PAC; Full Evaluation / Reliance Evaluation route; Appeal / Inquiry with assessment / Inquiry without assessment / Post Marketing Variation approval / Reliance route; Administrative / Quality change (p.51). | Not split by activity. Note p.7 l.16–21 sends readers to A for activity-level detail. |
| Annexes | Annex (1) Tracking Table (p.46); Annex (2) Registration / Re-registration Application form (pp.47–50); Annex (3) Variation Application Form of Post Marketed Human Products (pp.51–67), with its own Annex I, Annex II "Technical Justification & Supportive Data" and Annex II "Declarations" Templates 1–6 | **None.** History: "Removing Annex I application form" (p.20) |
| History table | "New Issue — Version 1", issue date blank (p.68) | v1 14/8/2023 New issue; v2 21/12/2023 Updating module 1; v3 31/3/2024 Updating module 1; v4 23/7/2024 Updating Module 1 and Module 5; v5 1/11/2025 Updating Module 1 (leaflet and mock-up aligned with One Submission, pp.3–5; Annex I updated, pp.28–30); **v6 10/2026: Updating Module 1, Updating Module 5, Removing Annex I application form** (p.20) |
| References | none listed | ICH CTD page; Singapore HSA application dossier (p.20) — unchanged from v5 |

**GAP:** "F-Toll" is never defined in A (used on pp.7, 9–10, 15–17). *(interpretation: probably "foreign toll", i.e. a foreign licence holder manufactured by an Egyptian toll manufacturer — must be confirmed with EDA.)*

---

## 2. Draft A — Module 1 in full

### 2.1 The Module 1 tree as printed (A p.3–5, l.11–105; Fig. 1 p.6)

```
1.0  Cover Letter                      (+ Tracking Table, Annex 1)
1.2  Application Form
  1.2.1  Application Form              (Annex 2)
  1.2.2  Legal Documents               1.2.2.1 … 1.2.2.14 (all 14 numbers used)
  1.2.3  EDA Approvals                 1.2.3.1, .3, .4, .5, .6, .8, .9, .10, .11, .12, .13, .15, .16, .17, .18, .20
                                       (no .2, .7, .14, .19)
  1.2.4  Declarations                  1.2.4.1 … 1.2.4.10
  1.2.5  Reference Product Document / Compendial   1.2.5.1, 1.2.5.4   (no .2, .3)
  1.2.6  Imported Products Documents   1.2.6.1, 1.2.6.2
  1.2.7  Reliance Documents            1.2.7.1, 1.2.7.2, 1.2.7.3
  1.2.8  Composition Documents         1.2.8.1 … 1.2.8.7
  1.2.9  Certificate of Analysis
  1.2.10 Post Approval Changes Requirements        1.2.10.1 … 1.2.10.4
  1.2.11 Proof of Payment
1.3  Product Information
  1.3.1  SPC, Labelling and Package Leaflet
  1.3.2  Mock-up
Responses to Questions
Additional Data
```

There is **no 1.1 and no 1.3.3–1.3.6, 1.4–1.10** in A (compare §5).

**Document mapping (A p.7, l.131–139, Fig. 2), verbatim:**
- "All relevant documents are provided within the designated folders organized by regulatory activity (New, Renewal, variation)."
- "The Legal Documents folder is organized differently from the other document folders, with its contents categorized according to the registration type with the applicable legal documents identified under each category."

Figure 2 numbers the folders 1–14:
1. Application & General Documents
2. Legal Documents
3. EDA Approvals
4. Declarations
5. Reference Product / Compendial
6. Imported Products Documents
7. Reliance Documents
8. Composition Documents
9. Certificate of Analysis
10. Post Approval Changes Requirements
11. Proof of Payment
12. Product Information
13. Responses to Questions
14. Additional Data

Under Legal Documents, the five registration types each show: Letter of Attorney · IDA License · GMP Certificate · Trade/Store License · Agreements · Termination / Waiver.

**INCONSISTENCY:** Figure 2 and the bullet name three activities (New, Renewal, variation). The text uses a fourth one throughout: "Re-registration Preliminary Approval".

### 2.2 Abbreviations used below
- NR = New Registration · V = Variation · RPA = Re-registration Preliminary Approval · RN = Renewal.
- Product types: Local = Locally Manufactured; FT = F-Toll; T = Toll; UL = Under License; Imp = Imported / Imported Bulk.
- "All types" = the draft does not restrict by product type for that item.

### 2.3 1.0 Cover Letter and 1.2.1 Application Form

| EG M1 § | Document | Applicability (draft's words) | Conditions (format, letterhead, signature, legalisation, validity) | Notes | Page |
|---|---|---|---|---|---|
| 1.0 | Cover Letter | New registration · Variation · Re-registration Preliminary Approval · Renewal (all types) | "submitted on company letter head signed, stamped, and dated" | Must include: Introduction of the submission; Clarification of Submission Type (e.g., new registration, variation, or renewal…..etc); Sequence number; Point of Contact for regulatory correspondence | p.8 l.144–162 |
| 1.0 | Tracking Table (Annex 1) | Same four activities | — | "A table contains submissions history to track and summarize all changes, updates, and sequences that have been submitted throughout the lifecycle of the regulatory application." Template: Annex 1 (§3.1). | p.8 l.153–162; p.46 |
| 1.2.1 | Application Form (Annex 2; variations: Annex 3) | New registration · Variation · Re-registration Preliminary Approval · Renewal | "on company letterhead signed, stamped and dated" | Annex 2 is titled "Registration / Re-registration Application form". Annex 3 is the variation form. | p.8 l.167–176 |

### 2.4 1.2.2 Legal Documents

#### 2.4.1 The draft's own summary table, verbatim (A pp.9–12)

Columns as printed: Registration Type | Section No. | Legal Document | Applicability.

| Registration Type | Section No. | Legal Document | Applicability |
|---|---|---|---|
| **Locally Manufactured Products** | 1.2.2.1 | Letter of Attorney for Company Representative | New Registration; Variation; Re-Registration Preliminary Approval; Renewal |
| | 1.2.2.2 | Manufacturing License and IDA License | New Registration; Variation; Renewal |
| | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | New Registration; Variation; Renewal |
| | 1.2.2.4 | Register of Trade | New Registration; Variation; Renewal |
| | 1.2.2.8 | Store License | New registration; Variation; Renewal |
| | 1.2.2.12 | Storage Agreement | New registration; Variation; Renewal |
| | 1.2.2.13 | Other Agreements | Where applicable |
| | 1.2.2.14 | Termination Letter / Waiver Letter | Renewal; Variation |
| **F-Toll Products** | 1.2.2.1 | Letter of Attorney for Company Representative | New Registration; Variation; Re-registration Preliminary Approval; Renewal |
| | 1.2.2.2 | Manufacturing License and IDA License | New Registration; Variation; Renewal |
| | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | New Registration; Variation; Renewal |
| | 1.2.2.4 | Register of Trade | New Registration; Variation; Renewal |
| | 1.2.2.10 | Manufacturing Agreement | New Registration; Variation; Renewal |
| | 1.2.2.12 | Storage Agreement | New Registration; Variation; Renewal |
| | 1.2.2.13 | Other Agreements | Where applicable |
| | 1.2.2.14 | Termination Letter / Waiver Letter | Renewal; Variation |
| **Toll Products** | 1.2.2.1 | Letter of Attorney for Company Representative | New Registration; Variation; Re-registration Preliminary Approval; Renewal |
| | 1.2.2.2 | Manufacturing License and IDA License | New Registration; Variation; Renewal |
| | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | New Registration; Variation; Renewal |
| | 1.2.2.4 | Register of Trade | New Registration; Variation; Renewal |
| | 1.2.2.5 | Toll Manufacturer License | New Registration; Variation; Renewal |
| | 1.2.2.8 | Store License | New Registration; Variation; Renewal |
| | 1.2.2.10 | Manufacturing Agreement | New Registration; Variation; Renewal |
| | 1.2.2.12 | Storage Agreement | New Registration; Variation; Renewal |
| | 1.2.2.13 | Other Agreements | Where applicable |
| | 1.2.2.14 | Termination Letter / Waiver Letter | Renewal; Variation |
| **Under License Products** | 1.2.2.1 | Letter of Attorney for Company Representative | New Registration; Variation; Re-registration Preliminary Approval; Renewal |
| | 1.2.2.2 | Manufacturing License and IDA License | New Registration; Variation; Renewal |
| | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | New Registration; Variation; Renewal |
| | 1.2.2.4 | Register of Trade | New Registration; Variation; Renewal |
| | 1.2.2.6 | Scientific Office License | New registration; Variation; Renewal |
| | 1.2.2.8 | Store License | New registration; Variation; Renewal |
| | 1.2.2.9 | Authorization Letter / Agency Agreement | New Registration; Variation; Renewal |
| | 1.2.2.10 | Manufacturing Agreement | New Registration; Variation; Renewal |
| | 1.2.2.12 | Storage Agreement | New Registration; Variation; Renewal |
| | 1.2.2.13 | Other Agreements | Where applicable |
| | 1.2.2.14 | Termination Letter /Waiver Letter | Renewal; Variation |
| **Imported / Imported Bulk Products** | 1.2.2.1 | Letter of Attorney for Company Representative | New Registration; Variation; Re-registration Preliminary Approval; Renewal |
| | 1.2.2.2 | Manufacturing License and IDA License | New Registration; Variation; Renewal |
| | 1.2.2.3 | GMP Certificate(s) / Alternative Documents | New Registration; Variation; Renewal |
| | 1.2.2.4 | Register of Trade | New Registration; Variation; Renewal |
| | 1.2.2.6 | Scientific Office License | New registration; Variation; Renewal |
| | 1.2.2.7 | Importers Register License | New Registration; Variation; Renewal |
| | 1.2.2.8 | Store License | New Registration; Variation; Renewal |
| | 1.2.2.9 | Authorization Letter / Agency Agreement | New Registration; Variation; Renewal |
| | 1.2.2.11 | Packaging Agreement | New Registration; Variation |
| | 1.2.2.12 | Storage Agreement | New Registration; Renewal |
| | 1.2.2.13 | Other Agreements | Where applicable |
| | 1.2.2.14 | Termination Letter/ Waiver Letter | Renewal; Variation |

**Not listed for a type in the summary table:**
- Local: 1.2.2.5, .6, .7, .9, .10, .11.
- F-Toll: 1.2.2.5, .6, .7, .8, .9, .11.
- Toll: 1.2.2.6, .7, .9, .11.
- Under Licence: 1.2.2.5, .7, .11.
- Imported: 1.2.2.5, .10.

#### 2.4.2 Detailed requirements per document and type (A pp.12–27) — every row

| EG M1 § | Document | Type | Applicability (detailed text) | Conditions | Notes | Page |
|---|---|---|---|---|---|---|
| 1.2.2.1 | Letter of Attorney for Company representative | Local, FT, T, UL, Imp (identical text) | New registration; Variation; Re-registration Preliminary Approval; Renewal | "must be valid (stating the validity date) and authenticated by a bank" | Definition: "A formal document in which a company grants authority to an individual to represent the company in dealings with Egyptian Drug Authority (EDA), or other legal entities… authorizes the representative to sign, receive and submit regulatory documents on behalf of the company." | Local p.12; FT p.15; T p.17–18; UL p.20–21; Imp p.24 |
| 1.2.2.2 | Manufacturing License and IDA License | Local | New registration; Variation; Renewal | "IDA License and/or EDA Data Certificate shall be provided." | — | p.13 |
| 1.2.2.2 | Manufacturing License and IDA License | FT | New registration; Variation; Renewal | IDA License and/or EDA Data Certificate "for **both parties** (License Holder and Manufacturer)" | — | p.15 |
| 1.2.2.2 | Manufacturing License and IDA License | T | New registration; Variation; Renewal | IDA License and/or EDA Data Certificate | — | p.18 |
| 1.2.2.2 | Manufacturing License and IDA License | UL | New registration; Variation; Renewal | IDA License and/or EDA Data Certificate | — | p.21 |
| 1.2.2.2 | Manufacturing License and IDA License | Imp | New registration (In case of Imported Bulk); Variation (In case of Imported Bulk); Renewal | IDA License and/or EDA Data Certificate | Renewal is not qualified "Imported Bulk" — **ambiguous** whether imported finished products need it at renewal | p.24 |
| 1.2.2.3 | GMP certificate(s) / Alternative documents | Local, FT, T, UL | New registration; Variation; Renewal | FPP manufacturer(s): "Valid GMP (Purpose of the GMP is for EDA Departments or company)"; "Production lines are specified." Plus GMP of API manufacturer(s) | "Alternative documents" never defined (**GAP**) | Local p.13; FT p.15; T p.18; UL p.21 |
| 1.2.2.3 | GMP certificate(s) / Alternative documents | Imp | New registration; Variation; Renewal | FPP manufacturer(s): Valid GMP, production lines specified. **GMP of Packager (In case of imported bulk)**: "Purpose of the GMP is for EDA Departments or company", valid, lines specified. Plus GMP of API manufacturer(s) | — | p.24 |
| 1.2.2.4 | The Register of Trade | Local, Imp | New registration; **Variation (for License Holder only)**; Renewal | "Valid Register of Trade shall be provided." | — | Local p.13; Imp p.25 |
| 1.2.2.4 | The Register of Trade | FT, T, UL | New registration; Variation (for License Holder only); Renewal | Valid Register of Trade "for **both parties** (License Holder and Manufacturer)" | — | FT p.15–16; T p.18; UL p.21 |
| 1.2.2.5 | Toll Manufacturer License | T | New registration; Variation; Renewal | "The Toll Manufacturer License (Toll card) shall be valid and clearly specify the Factory and storage site" | — | p.18 |
| 1.2.2.6 | Scientific Office License | UL, Imp | New registration; Variation; Renewal | "submitted where the scientific office acts as the applicant" | — | UL p.21; Imp p.25 |
| 1.2.2.7 | Importers Register License | Imp | New registration; Variation; Renewal | "should be submitted where the importer acts as the applicant" | — | p.25 |
| 1.2.2.8 | Store License | Local, T, UL | New registration; Variation; Renewal | "shall be submitted in cases where the storage site differs from the factory" | — | Local p.13; T p.19; UL p.22 |
| 1.2.2.8 | Store License | Imp | New registration — Imported Bulk: "where the storage site differs from the manufacturer"; Imported Finished: "where the storage site differs from that stated in the Importers Register License"; Variation; Renewal | "A Store License should be submitted." | — | p.25 |
| 1.2.2.9 | Authorization letter / Agency agreement | UL, Imp (identical text) | New Registration; Re-registration Preliminary Approval; Renewal; Variation | "must be valid"; "on the License Holder's letterhead"; "legalized and authenticated by the Chamber of Commerce from the country of origin **or a Notary Public**, and the Egyptian consulate/embassy". Must include: Trade Name, Dosage form and strength; Registration number; "Name and address of the new applicant" | Definition: "legal agreement between the applicant and the license holder authorizing the applicant to act on behalf of the license holder in registration… clarifying its responsibilities for registration, all regulatory activities and signing contracts." **INCONSISTENCY:** the summary table omits RPA for 1.2.2.9; the detailed text includes it. | UL p.22; Imp p.26 |
| 1.2.2.10 | Manufacturing Agreement | FT | New registration; Variation; Renewal | "has to be valid"; "authenticated by the bank and Legal department of EDA"; manufactured products specified in an annex to the agreement (Trade Name, Dosage form, Strength) | Definition adds: "outlining the terms, conditions and responsibilities for the production of pharmaceutical products" | p.16 |
| 1.2.2.10 | Manufacturing Agreement | T | New registration; Variation; Renewal | valid; authenticated by the bank and Legal department of EDA; product annex (Trade Name, Dosage form, Strength) | — | p.19 |
| 1.2.2.10 | Manufacturing Agreement | UL | New registration; Variation; Renewal | valid; "authenticated by the bank and Legal department of EDA **or** legalized by the Chamber of Commerce and the Egyptian Embassy"; product annex | — | p.22 |
| 1.2.2.11 | Packaging Agreement | Imp | New Registration (In case of Imported Bulk products); Variation (same); Renewal (same) | agreement "between the applicant/License Holder/MAH and the packager"; "Authenticated by the bank and Legal department of EDA or legalized by the Chamber of Commerce and the Egyptian Embassy"; valid | **INCONSISTENCIES:** the applicability sentence reads "The Authorization letter / Agency agreement is submitted for" (copy-paste error). The summary table gives New + Variation only; the detail adds Renewal. | p.26 |
| 1.2.2.12 | Storage Agreement | Local, FT, T | New registration; Variation; Renewal | "between the applicant/License Holder and the storage site"; valid; "authenticated by the bank and Legal department of EDA" | — | Local p.14; FT p.16; T p.19 |
| 1.2.2.12 | Storage Agreement | UL | New registration; Variation; Renewal | valid; "authenticated by the bank, Legal department of EDA or legalized by the Chamber of Commerce and the Egyptian Embassy" | — | p.23 |
| 1.2.2.12 | Storage Agreement | Imp | New registration; Renewal (no Variation) | valid; authenticated by the bank and Legal department of EDA or legalized by the Chamber of Commerce and the Egyptian Embassy | — | p.26 |
| 1.2.2.13 | Other Agreements | all types | "Where applicable" (summary table) | — | "Any additional agreements in the dossier other than previously mentioned should be included here." | p.14, 16, 19, 23, 27 |
| 1.2.2.14 | Termination / Waiver — **Waiver Letter** | Local, FT, T | Renewal; Variation | **Submitted on:** for a license-holder transfer, "Real Estate Registry at Ministry of Justice letterhead"; for a manufacturing-site transfer, "the old manufacturing site letterhead". **Includes:** Product Trade Name, Strength, Dosage Form, Registration number. **Authenticated:** for a LH transfer, by the Real Estate Registry at Ministry of Justice and EDA legal Affairs; for a site transfer, by the Bank and EDA legal Affairs. | Definition: "a formal document in which one party voluntarily gives up a specific right, claim, or condition outlined in the agreement…" | Local p.14; FT p.17; T p.20 |
| 1.2.2.14 | Termination / Waiver — **Termination Letter** | UL, Imp | Renewal; Variation | "on the License Holder/Marketing Authorization Holder's letterhead in the case of Applicant Change". **Includes:** Product Trade Name; Registration number; "Reference to the manufacturing agreement date". "authenticated from chamber of commerce from country of origin and the Egyptian consulate/embassy" | Definition: notifies the parties "of the decision to end or cancel the agreement before its intended completion…" | UL p.23; Imp p.27 |

### 2.5 1.2.3 EDA Approvals (A pp.28–33)

| EG M1 § | Document | Applicability | Conditions / content | Notes | Page |
|---|---|---|---|---|---|
| 1.2.3.1 | Registration Request Approval | New Registration; Variation (In case of License Holder transfer for local products) | — | "Approval allows the product to proceed in the registration process." | p.28 |
| 1.2.3.3 | Name Approval | New Registration; Variation (In case of change of Finished Product name after issuing registration license) | "must be obtained prior to proceeding with the registration process" | — | p.28 |
| 1.2.3.4 | Registration License | Renewal; Re-Registration Preliminary Approval; Variation | — | "Approval granted by EDA that allows a product to be legally marketed." | p.28 |
| 1.2.3.5 | Preliminary Approval | Renewal; Variation | — | "An approval granted in the renewal process to proceed with fulfilling the renewal requirements and studies." | p.28 |
| 1.2.3.6 | Non-Reference Approval | New Registration; Renewal (Purpose of approval: re-registration process) | — | Granted by the "Evaluation unit of scientific data and drug development for Human Pharmaceuticals" to a product without a scientific reference (same API, form, concentration or route) in any reference country on the list approved by the Technical Committee of Drug Control. | p.29 |
| 1.2.3.8 | Pricing Certificate | New Registration; Variation; Renewal | Must be valid. If expired: evidence of a pricing-update request (e.g., screenshot). **New:** "In case of old pricing with no expiration, evidence of submission of a pricing update request (e.g., screenshot) must be provided." If re-evaluation is required, the updated certificate. | — | p.29 |
| 1.2.3.9 | Pharmacovigilance Approval | New Registration; Variation; Renewal (Purpose of approval: re-registration process) | — | No content requirements given (**GAP**) | p.29 |
| 1.2.3.10 | Inspection Report | **New Registration:** inspection report for pilot/production batch (locally manufactured); site inspection report for imported products from non-reference countries not marketed in reference countries; inspection report for the BE study naming the BE centre. **Renewal:** inspection report for a valid and marketed batch (if not applicable, see 1.2.3.17 — Exemptions from Decree 600); BE study inspection report naming the BE centre. **Variation:** clarification of any variation; batch size (addition/change/size of first production batch); Final approval (report for inspection sampling stating batch number and production dates / evaluation of process validation). | — | "A Report that provides a detailed account of an inspection conducted by EDA's authorized inspector." | pp.29–30 |
| 1.2.3.11 | Importation approval for each API | **New Registration:** locally manufactured — "In case of Release Letter, an invoice should be submitted". **Renewal:** "referred to as an Importation Plan. It must be the most recent version." **Variation:** addition/clarification of API manufacturer — importation approvals or production plans, customs releases, invoices and supplier certificates "have the same batch numbers that were imported". | Must specify company name, API supplier name, trade name | — | p.30 |
| 1.2.3.12 | CADC Report | **New Registration:** imported — "Optional; however, it is mandatory in case of imported products from non-reference countries and not marketed in reference countries"; local — "In case of production batches… CADC certificate + CADC composition". **Renewal:** CADC certificate + CADC composition + Renewal certificate (if not yet issued: "the Variation Referral for Analysis File Renewal"). **Variation:** CADC Certificate (Administration of Evaluation and Approval or Administration of Post-Approval Control) OR Detailed CADC Certificate (Post-Approval Control) + CADC Composition Certificate + relevant official CADC letters or e-mails. | Must be "confirm" and include: Trade Name and Strength; FPP manufacturer and licence holder; API manufacturer; Batch Number and Batch Type; chemical, physical and microbiological tests | — | pp.30–31 |
| 1.2.3.13 | Stability Study Approval | Renewal (Long Term stability study); Variation | — | **Not listed for New Registration** | p.31 |
| 1.2.3.15 | Module 3 Approval | New Registration; Variation | — | Issued by the "Administration of Technical Affairs for Human Pharmaceuticals" (drug substance, drug product, packaging, sites, QC procedures) | p.32 |
| 1.2.3.16 | Module 5 Approval | New Registration ("BE study decision letter is submitted for locally manufactured products"); Renewal (Purpose of study approval: re-registration or Exemption from the study); Variation | Must include: Trade Name and Strength; FPP manufacturer and licence holder; API manufacturer; Batch Number; Purpose of study; Composition | Issued by the "Evaluation Unit of Bioavailability and Bioequivalence Studies of Human Pharmaceuticals". BE need "determined based on the specific dosage form and in accordance with applicable published regulatory guidelines". | p.32 |
| 1.2.3.17 | Pre-approved letters from EDA concerning the product | New Registration; Renewal; Re-registration Preliminary Approval; Variation | — | "may be but not limited to": Technical committee decisions; Exemptions from Decree 600 (when the marketed-batch inspection report is not applicable); Extension Approval; "Approval to produce production batches instead of pilot batches" | p.33 |
| 1.2.3.18 | Variation Approvals | Renewal; Re-registration Preliminary Approval; Variation | "Every variation is to be submitted in separate sub folder named with the variation type (e.g., Addition of Manufacturer of API, or composition change) in addition to all required studies arranged by date." | "Post marketing variation approval / appeals for Administrative and/or quality post-authorization changes" | p.33 |
| 1.2.3.20 | Registration license for the solvent | New Registration; Renewal; Variation (In case of solvent change / addition /clarification variation) | The licence "shall specify the pack of the attached solvent (same solvent type and volume as those supplied with the product)" | Required when "the dosage form needs a solvent and the solvent is attached with the product" | p.33 |

### 2.6 1.2.4 Declarations (A pp.34–37)

| EG M1 § | Document | Applicability | Conditions | Notes | Page |
|---|---|---|---|---|---|
| 1.2.4.1 | Declaration letter stating the list of (Registered & Under-Registration) products owned by the toll company | New Registration (For Toll Products); Variation (In case of License Holder transfer to toll company — list of the new owner) | "on the applicant letter head signed, stamped and dated"; must list products **with their active ingredients** | Template 3 (Annex 3) has this layout | p.34 |
| 1.2.4.2 | Declaration letter from the LH specifying the API manufacturers | New Registration (For Under License Products/Imported products); Renewal (same); Variation | "should be legalized by the chamber of commerce and the Egyptian embassy"; names **and complete addresses** for each API | — | p.34 |
| 1.2.4.3 | Declaration letter from the LH specifying approved pack in Egypt | New Registration (UL/Imported); Renewal (UL/Imported); Variation | legalised (chamber of commerce + Egyptian embassy) | "Detailed description of pack registered in Egypt." | p.34 |
| 1.2.4.4 | Declaration letter from the LH stating the form of bulk (strips, Capsules, etc……) | New Registration, Renewal, Variation (For Imported Bulk products) | legalised (chamber + embassy); "In case of same entity or affiliate it might be on the License Holder letter head." | — | p.35 |
| 1.2.4.5 | Declaration letter from the manufacturer of the active substance to inform the applicant in case of modification of the manufacturing process or specifications | Variation | legalised (chamber + embassy) | — | p.35 |
| 1.2.4.6 | Declaration Letter from API Supplier | Variation (In case of clarifying Compaction or Mixture ratio or Polymorphism, …..etc) | — | — | p.35 |
| 1.2.4.7 | Declaration Letter for Site Addition | Variation | "authenticated by the Bank and legal department of EDA"; includes trade name, registration number, name of old factories | The company "takes full legal responsibility for adding a new site without any responsibility on EDA, regarding the obligations and duties imposed under the manufacturing contract with the old factory (factories)." Template 4. | p.35 |
| 1.2.4.8 | Declaration letter from LH stating all variations & justification for the change | Variation | — | No content requirements (**GAP**) | p.36 |
| 1.2.4.9 | Other declarations requested by EDA | New Registration; Variation; Renewal; Re-registration Preliminary Approval | See notes | "may be but not limited to": **Letter of access**; **SmPC/PIL declarations**: (a) imported and innovator products with PIL only — a legalised letter from the country of origin that the attached PIL (trade name, generic name, concentration, version date and number) is marketed and registered there and will be translated into Arabic; (b) non-English leaflets — a legalised LH letter committing to an authorised medical translation (signature and stamp), **or** a legalised head-office letter making the scientific office responsible (the 2-language translation signed and stamped by the scientific office). If not legalised: a scientific-office declaration that the letter will be legalised within 6 months. | p.36 |
| 1.2.4.10 | List of countries where the product is registered and marketed | New Registration (UL and Imported); Variation (For imported products); Renewal (UL and Imported) | "A Letter from License Holder…"; "Authenticated by chamber of commerce and the Egyptian embassy" | — | p.37 |

### 2.7 1.2.5 Reference / compendial, 1.2.6 Imported, 1.2.7 Reliance (A pp.37–39)

| EG M1 § | Document | Applicability | Conditions | Notes | Page |
|---|---|---|---|---|---|
| 1.2.5.1 | The reference product document | New Registration; Variation; Re-registration Preliminary Approval; Renewal | Reference product "identical to the submitted product in terms of the active ingredient, concentration, dosage form and **route of administration**" | Includes: recent on-line reference (FDA, MHRA, EMA, ANSM, Swissmedic, TGA, Pmda, etc.) where registered and marketed, OR the latest edition of BNF; the most updated SmPC and PIL of the reference product; an authorised translation (non-English reference); "Clear scanned strip/pack for the reference and test product" | p.37 |
| 1.2.5.4 | The latest recent pharmacopeia | New Registration; Variation; Re-registration Preliminary Approval; Renewal | "in case of Pharmacopeial/compendial Finished Products" | — | p.37 |
| 1.2.6.1 | Certificate of Pharmaceutical Product (CPP) / eCPP issued by Competent Authorities in Country of Origin | New Registration, Variation, Renewal — each "(In case of Imported and Under license products)" | Valid; from the country of origin; issued and authenticated by the competent authority; signed and stamped by Chamber of Commerce or Notary Public or Foreign Affairs (if applicable); legalised by the Egyptian Embassy (*eCPP exempted from legalization*); Egypt named as importing country; date of issue; trade name; dosage form(s) and strength(s); LH (address, city, country) | Product marketed in the COO for ≥ 1 year (else explain). Composition: actives by salt/hydrate with quantity per unit dose; inactives with quantities (may be an attachment); capsule-shell composition for capsules. If the Egyptian name differs it must be noted, otherwise a separate legalised declaration on LH letterhead. | p.38 |
| 1.2.6.2 | List of affiliates / Subsidiaries | New Registration (Imported and UL); Variation; Renewal (Imported and UL) | — | No content requirements (**GAP**) | p.38 |
| 1.2.7.1 | Sameness Letter | New Registration (For Imported Products); Variation (For Imported Products) | — | "authorized document issued by the License Holder to assure the same quality of the product and to provide transparency about any potential differences compared to the reference Stringent Regulatory Authority (SRAs)" | p.39 |
| 1.2.7.2 | Unredacted Assessment Report | New Registration (For Imported Products); Variation (For Imported Products) | — | "complete version of assessment report of the SRA in which no information has been blacked out" | p.39 |
| 1.2.7.3 | RRA Variation application with annexes | Variation | "Application and approval are required." | RRA = "Request for Regulatory Approval", filed by the LH of the reference product with the foreign authority | p.39 |

### 2.8 1.2.8 Composition, 1.2.9 CoA, 1.2.10 PAC, 1.2.11 Payment (A pp.40–44)

| EG M1 § | Document | Applicability | Conditions | Notes | Page |
|---|---|---|---|---|---|
| 1.2.8.1 | Composition Certificate | New Registration ("identical to the inspection composition in case of Local New registration"); Variation ("The old and new compositions are submitted"); Renewal | On "the applicant head letter signed and stamped", **or** on LH or manufacturer letterhead **and legalised** if the composition is not attached to the CPP (imported and UL) | Must include: trade name; dosage form; actives (hydrate and salt) per unit dose and **function**; inactives per unit dose with **grade and function**; actives and inactives separated; any overage; "Most recent specifications of each ingredient". Coated tablets: core and coat separate, tablet weight; coating composition goes to 1.2.8.5. Hard gelatin capsules: body and cap separate, capsule size; shell composition goes to 1.2.8.6. | p.40 |
| 1.2.8.2 | Specification | New Registration; Variation (old and new specifications); Renewal | Recent pharmacopoeial and/or in-house specifications; in-house specifications of all inactives "on the company letter head signed and stamped" | — | p.41 |
| 1.2.8.3 | Any Composition calculations | New Registration; Variation ("Calculations of pellets/Premix and Calculation of approved limit in 1.2.8.4 (In case of presence of Methyl paraben and propyl paraben in oral liquid dosage forms 'suspension and syrup')"); Renewal | "on the applicant letter head signed and stamped, with reference for the molecular weight" | Equivalence calculation | p.41 |
| 1.2.8.4 | Pellets / Premix Composition and Certificates | New Registration; Variation; Renewal | Pellets: supplier-letterhead composition + pellet calculation (weight/capsule) on company letterhead. Premix: supplier-letterhead composition. | — | p.41 |
| 1.2.8.5 | Opadry / Coating Premix composition | New Registration; Variation; Renewal | On the supplier's letterhead | Coated tablets | p.42 |
| 1.2.8.6 | Capsule shell composition | New Registration; Variation; Renewal | On the supplier's letterhead | Hard gelatin capsules | p.42 |
| 1.2.8.7 | Synonyms Evidence | New Registration; Variation (In case of Change in name of the active substance or of an excipient); Renewal | — | Active/salt must be identical to the supplier CoA, otherwise submit synonyms | p.42 |
| 1.2.9 | Certificate of Analysis | New Registration; Variation; Renewal | Signed and stamped; manufacturing date, expiry date and batch number specified | "for **Active Substance and Finished Pharmaceutical Product**" | p.42 |
| 1.2.10.1 | PAC Approval from the COO (Imported Products) | Variation (In case of reliance evaluation routes for imported products) | — | Approval of the change by the reference authority in the country of manufacture | p.43 |
| 1.2.10.2 | Summary of change for variation | Variation (In case of Full evaluation and Reliance evaluation routes for imported products) | — | — | p.43 |
| 1.2.10.3 | Justification of the proposed Post approval Change | Variation | — | Must show the change does not affect safety, efficacy or compliance | p.43 |
| 1.2.10.4 | Any additional documents relevant to Variations | Variation (In addition to reliance documents) | — | e.g. "List of machines, Manufacturing process flow chart, risk-based assessments, TSE/BSE supplier safety declaration, etc" | p.43 |
| 1.2.11 | Proof of Payment | New Registration; Variation; Renewal | "Fees payment receipt in accordance with the relevant decree / case requirements." | — | p.44 |

**General legalisation note (A p.44, l.1413–1416), verbatim:**
> "If any document requires legalization but cannot be legalized at the time of submission, the applicant must submit a declaration undertaking to complete the legalization process within six months."

### 2.9 1.3 Product Information, Responses, Additional Data (A pp.44–45)

| EG M1 § | Document | Applicability | Conditions | Notes | Page |
|---|---|---|---|---|---|
| 1.3.1 (A) | Approved leaflet | Renewal | "Valid & Updated Leaflet with recent warnings if available"; "Manufacturer and excipients must be mentioned" | — | p.44 |
| 1.3.1 (B) | Proposed Leaflet | New Registration | **English and Arabic, Word format (SmPC & PIL)**; "Pharmacology guidelines for warnings and exceptions should be checked" | No rule for Variation or RPA (**GAP**) | p.44 |
| 1.3.2 (A) | Approved Mock-up | Renewal | "Different mockups are submitted for each manufacturer." | — | p.45 |
| 1.3.2 (B) | Proposed Mock-up | New Registration | "Colored stamped outer and inner layout (an editable PDF is preferable)"; "Complete image of the original pack (For imported and under-license products)"; if the soft layout is accepted, the hard coloured stamped outer and inner layout goes to the unit administrator for signing and stamping | Definition: "A virtual full-sized model… It also can be defined as layout or artwork." | p.45 |
| Responses to Questions | Written responses to questions, deficiency letters or inquiries | (any) | "All supporting documents are submitted within the relevant folders and file structure, in alignment with the CTD format." | — | p.45 |
| Additional Data | — | (any) | Only for required information "not currently included in the published EG M1 or EG eCTD M1 Specification". It may also be used in eCTD when an old DTD version is used during an agreed transition period. | **Do not re-submit** files from earlier sequences; use a reference, hyperlink or cross-link ("to avoid multiple lifecycles and repetitions of the files") | p.45 |

---

## 3. Draft A — annexes, templates and declaration wording (verbatim)

### 3.1 Annex (1) Tracking Table (A p.46)

Header: **Product Name**. Columns: **Sequence Number | Submission Description | Submission Date**.

Example rows, verbatim:

| Sequence Number | Submission Description | Submission Date |
|---|---|---|
| 0006 | Preliminary Approval | Dec-2023 |
| 0005 | Variation (ex: Administrative Change – PAC N) | Jul-2023 |
| 0004 | Responses to Letter of Comments | Oc-2022 |
| 0003 | Variation (ex: Quality Change – PAC B) | Sep-2022 |
| 0002 | Responses to Letter of Comments | May-2022 |
| 0001 | Responses to Letter of Comments | Feb-2022 |
| 0000 | New Marketing Authorization | May-2022 |

**INCONSISTENCY in the example:** 0000 is dated May-2022, after 0001 (Feb-2022). "Oc-2022" is a typo.

### 3.2 Annex (2) Registration / Re-registration Application form (A pp.47–50)

This is **word-for-word the Annex I of NP.CAPP.065 v5 (v5 pp.27–30)**. The only change is the title: v5 "Application form", A "Registration / Re-registration Application form" (checked by text comparison).

**Addressee and opening (Arabic):**

> السيد الدكتور/ رئيس هيئة الدواء المصرية
> تحية طيبة وبعد،،،،
> نتقدم لسيادتكم بملف التسجيل للحصول على رخصة تسويق المستحضر الآتي:

**Fields, verbatim and in order:**

- **Product:**
  - Trade Name: English and Arabic
  - Registration Request number /Registration number
  - Active Ingredient(s) & Strength (s):
  - Pharmaceutical dosage form:
  - Route of administration:
  - Physical Characters:
  - Shelf Life:
  - Storage Condition:
  - Approved Price Pack: — *Note: Kindly Specify No. of Units according to the Pricing Certificate & Packaging Material according to the Stability Approval.*
  - Price:
- **Reference drug product** (*Note: According to bioequivalence approval*):
  - Name of reference product (RLD, RS,….:
  - Name of MAH, Manufacturer and country of origin:
  - Reference Link:
- **Classification:**
  - Therapeutic Group:
  - ATC Code:
  - Approved Indication
- **Parties and sites:**
  - Applicant:
  - Company Profile Username:
  - Marketing Authorization Holder/License Holder:
  - Manufacturer:
  - Manufacturer of Solvent/ Accessories (If Applicable):
  - Packager:
  - Batch releaser:
  - Storage Site & Address:
- **Registration and batches:**
  - Type of registration:
  - Market status:
  - EDA Chairman Decree:
  - Batch Type
  - Batch Number(s)
- **API box** (*Note: The above box can be repeated according to No. of APIs in Product*):
  - API information submitted as: □ Prequalification □ DMF □ CEP □ Full details in the PD
  - CEP number & issue date: ″If applicable‶
  - API Name /Form/ Specs:
  - Name of Manufacturer & country of origin + Address as in the manufacturer's GMP":
  - Studies that had been performed on each manufacturer of API
- **Contact:**
  - Contact person:
  - Telephone number:
  - E-mail:

**Undertaking (A p.49, l.1512–1545)** — transcribed from the rendered page. The pdftotext output breaks the lam-alif ligatures, so the Arabic below was corrected against the page image:

> وأتعهد أنا الموقع أدناه .................. رئيس مجلس إدارة (أو /العضو المنتدب/ المفوض بالإمضاء) شركة .................. بالآتي:
> ● بأن كافة البيانات المذكورة أعلاه صحيحة ودقيقة وكاملة.
> ● الالتزام بأحكام قانون حماية حقوق الملكية الفكرية رقم ٨٢ لسنة ٢٠٠٢ ولائحته التنفيذية دون أدنى مسؤولية على هيئة الدواء المصرية.
> ● الالتزام بطباعة اسم المصنع وعنوانه والشركة مالكة المستحضر (أو اسم الشركة مالكة الحق في التسويق للمستحضرات المستوردة بدلاً من الشركة مالكة المستحضر وذلك طبقاً لشهادة CPP المقدمة) وتاريخ الإنتاج وتاريخ انتهاء الصلاحية ورقم التشغيلة ورقم التسجيل والسعر على العبوة الخارجية وعدم إحداث أي تغيير في المستحضر إلا بعد الحصول على موافقة هيئة الدواء المصرية.
> ● إخطار هيئة الدواء المصرية بأسماء جميع الموزعين المعتمدين وبأي تغيير يطرأ على البيانات الخاصة بهم والتأكد من أن الموزع المعتمد يطبق قواعد التخزين والتوزيع الجيد (GSP&GDP) ومتابعتها من قبل الإدارة العامة للتفتيش على المصانع.
> ● عدم تغيير مصادر المادة الخام الفعالة إلا بعد موافقة الإدارة العامة لتسجيل المستحضرات البشرية، وإلا يلغى إخطار التسجيل.
> ● تحمل المسئولية الكاملة عن تخزين المواد الخام، وعن جميع مراحل تصنيع المستحضر، وعن مطابقة المستحضر للمواصفات الفنية وتخزين المنتج حتى تمام التوزيع وفى حالة التصنيع لدى الغير يشترط أن يكون المصنع مرخصاً وأن يلتزم بجميع الالتزامات الواردة بهذا القرار بقواعد التصنيع الجيد وما ورد بالقرار الوزاري ٥٣٩ لسنة ٢٠٠٧ بشأن اعتماد المدونة المصرية لأساليب التصنيع الجيد للمستحضرات الصيدلية.
> ● لا يتم نقل مكان التصنيع أو نقل الملكية إلا بعد موافقة الإدارة العامة لتسجيل المستحضرات البشرية، وإلا يلغى إخطار التسجيل.
> ● لا يتم نقل ملكية المستحضرات المحلية إلا بعد مرور ثلاث سنوات من التداول المحلي وموافقة الإدارة العامة لتسجيل المستحضرات البشرية، وإلا يلغى إخطار التسجيل (في حالة المستحضرات المقدمة طبقاً للقرار الوزاري ٤٢٥/٢٠١٥ وقرار رئيس هيئة الدواء المصرية رقم ٤٥٠/٢٠٢٣ الحالة الأولى)
> ● لا يتم نقل ملكية المستحضرات المحلية إلا بعد مرور خمس سنوات من التداول المحلي وموافقة الإدارة العامة لتسجيل المستحضرات البشرية، وإلا يلغى إخطار التسجيل (في حالة المستحضرات المقدمة طبقاً للقرار الوزاري ٦٤٥/٢٠١٨ وقرار رئيس هيئة الدواء المصرية رقم ٤٥٠/٢٠٢٣ الحالة الثالثة)
> ● أن جميع البيانات المقدمة بملف التحليل بالإدارة المركزية للرقابة الدوائية للمستحضر مطابقة لما تم تقديمه بملف التسجيل بهيئة الدواء المصرية وأن جميع المستندات والبيانات صحيحة وعلى مسئوليتي الخاصة.
> ● تقديم شهادة الـ GMP وشهادة التحليل الخاصة بالمادة الخام، وذلك عند التقدم لاستيراد المادة الخام بهيئة الدواء المصرية.
> ● إبلاغ الإدارة العامة لليقظة الصيدلية عن أى آثار عكسية خطيرة يتم رصدها عن هذا المستحضر وتقديم تقرير Safety Periodic Report Update، متابعة مأمونية مستحضراتها وتنفيذ جميع أنشطة اليقظة الدوائية وذلك وفقاً للمهل المحددة والقواعد الواردة بأسس الممارسة الجيدة لليقظة الدوائية الصادرة والمفعلة من الإدارة.
> ● سوف يتم توزيع المستحضر عن طريق الشركات الآتية:
> ● تم إجراء دراسات إعادة التسجيل (تحليل بالإدارة المركزية للرقابة الدوائية / دراسة الثبات / دراسة التكافؤ الحيوى / معدل الذوبان) على تشغيلات إنتاجية باستخدام مصدر المادة الخام: ..................
> ● تتعهد الشركة باستكمال الدراسات على تشغيلات إنتاجية باستخدام مصدر المادة الخام: .........
> ● تم عمل المتغيرات (Variations) الآتية / لم يتم عمل أى متغيرات (Variations) للمستحضر عن آخر إخطار تسجيل للمستحضر (لإعادة التسجيل) / موافقة طلب الاستعلام (للمستحضرات الجديدة):

**Variations table (p.50):** Type of Variation | From | To | Status (Final /Conditioned).

**Signature block (p.50):**
- رئيس مجلس الإدارة او المفوض إليه بالإمضاء
- الاسم:
- التوقيع:
- التاريخ:
- ختم الشركة

### 3.3 Annex (3) Variation Application Form of Post Marketed Human Products (A pp.51–67)

#### Annex I: Product Information, Classification of Proposed Changes and General Amendments and Data (pp.51–55)

**1-Product Information**, laid out in two columns:

| Left column | Right column |
|---|---|
| Trade Name: | Applicant: |
| Dosage form: | License Holder/MAH : |
| Active substance(s): | Manufacturer of Finished Pharmaceutical product: |
| Concentration: | Primary /Secondary Packager/Batch Releaser: |
| Registration Decree: | Manufacturer of solvent: |
| Registration number: | Storage Site: |
| Type of License: | Type of Marketing: |

**2-Classification of the Submitted Variation According to Variation Guidelines** (Tick √):
- Mode of Submission: Single PAC / Grouped PAC
- Variation Evaluation Route: Full Evaluation Route / Reliance Evaluation Route
- Categorization of submission: Appeal / Inquiry with assessment / Inquiry without assessment / Post Marketing Variation approval / Reliance route
- Type of the request: Administrative Change / Quality Change

**Variation changes** — tick Change / Addition / Clarify; "Please Tick all the variations submitted in case of multiple variations" (pp.52–53):

- **A) Composition & Specification Changes As:**
  - Name of active substance
  - Name of an Excipient
  - Imprints / Embossing / other marking
  - Scoring
  - Shape of pharmaceutical finished product
  - Dimensions of pharmaceutical finished product
  - Excipient
  - Coating weight / weight of capsule shell
  - Color of (coat / capsule shell, etc ….)
  - Specification of Finished Pharmaceutical product
  - Shelf life
  - Storage Conditions
  - API form as salt equivalence and/or crystalline state
  - Test procedure
  - The particle size of API (state D90)
  - Solvents
  - Specification of Active ingredient
  - Specification of Inactive ingredients
  - Route of Administration
  - Dosage Form
- **B) Container Closure System Changes As:**
  - Primary packaging of finished pharmaceutical product
  - Shape of container
  - Pack size of finished pharmaceutical product
  - Part of primary packaging material not in contact with the finished product formulation
  - Supplier of packaging components / Devices
  - Clarify the change concerning which type of packs: Local/Tender/Export/Hospital use
- **C) Ownership / Manufacturing Changes As:**
  - Name of License holder
  - Address of License holder
  - Name of Manufacturer site
  - Address of Manufacturer site
  - Applicant for imported FPPs
  - Modification of Registration License
  - License Holder Transfer
  - Marketing Authorization holder Transfer
  - Marketing Authorization holder in Egypt
  - Solvent Manufacturer
  - Manufacture site
  - Primary Packager
  - Secondary Packager
  - Storage Site
  - Batch Releaser
  - Batch size factor of 10 X
  - Batch size over 10 X
  - Change Registration Type
  - Addition of Manufacturer for Export only
  - In-Process Control
  - Manufacturing process
- **D) API Manufacturer changes as:**
  - Name of API Manufacturer
  - Address of API Manufacturer
  - Deletion of API Manufacturer
  - API Manufacturer (with DMF or Not)
  - Manufacturing process of API
  - Batch size of API
  - In process tests during the manufacture of API
  - Specification parameters &/or limits of API
  - Test Procedures during the manufacture of API
  - Primary packaging of API
  - Retest period/storage period of API
  - Storage condition of API
  - CEP
- **E) Miscellaneous** (Tick for required Issue):
  - Extensions
  - Updating Analysis File
  - Cancelling previous variation approvals
  - Re-issuing Approvals
  - Non-Reportable Requests: (Please Describe the request)

**3-kindly fulfill the following Amendments by Yes / NO** (p.54), verbatim:
1. Is All documents & information submitted in the file are correct and on the responsibility of the applicant
2. Is the submitted file contains all the approvals for the product that were not mentioned in the last released registration license
3. Is the submitted file contains the latest issued registration license
4. Is the submitted file contains Valid registration license (In case of Invalidation Please submit registration renewal or validity extension)
5. Is the submitted file contains Valid Pricing license
6. Is the submitted EDA lab composition and its certificate of analysis is the last composition analyzed by CADC Labs.
7. Is the submitted file contains all approvals, variations, decisions & exemptions issued for the product from different EDA departments
8. Is the submitted request fulfilling all conditions stated in guidelines
9. Is the Manufacturing Site Registered Capable for production of the container closure system (In case of change /addition of pack)?

**4-Kindly state the following data** (pp.54–55):
1. Any previous variations' approvals, variations, decisions & exemptions issued for the product from different EDA departments (please arrange the with dates if available) — numbered list.
2. Data of the last manufactured/imported production batch: A- Batch No.; B- Production date; C- Expiry date. Then: "Is a Ministerial decree 600/2018 exemption approval (If needed) is Attached: Yes / No".
3. "If New Registration license is registered according to 425 or 645 (In case of Batch Size) (Please clarify if change is related to first three production batches manufactured or No) Yes / No"
4. Status from submission to pharmacovigilance (In case of changing the applicant)
5. Payment receipt No: "(Its Value according to Variation Request, must be directed to variation department and stamped with EDA Stamp with the Product Name, Concentration, Dosage Form, Type of variation."
6. "Name & address of Manufacturers of API of product as stated in GMP Name & address of suppliers of API of product"
7. Please Clarify:
   - A- BCS Class of Active Substance (attach the Biopharmaceutics Classification System reference): ☐ Class I ☐ Class II ☐ Class III ☐ Class IV
   - B- The Product Is Innovator: ☐ Yes ☐ No

#### Annex II: Technical Justification & Supportive Data (pp.55–61)

1. **Summary of Change** — Current Approved Status | Proposed Status.
2. **Scientific Justification & Reason for Change.**
3. **Impacted CTD Part(s)** — ☐ Module 1 (Administrive /Labeling) ☐ Module 3 (Quality /CMC).
4. **Impacted CTD Parts — Module 3 tick list:**
   - 3.1
   - 3.2
   - 3.2.S.1–S.1.3
   - 3.2.S.2–S.2.6
   - 3.2.S.3.1–3.2
   - 3.2.S.4.1–4.5
   - 3.2.S.5
   - 3.2.S.6
   - 3.2.S.7.1–7.2
   - 3.2.P
   - 3.2.P.1
   - 3.2.P.2–P.2.6 (with P.2.1.1, P.2.1.2, P.2.2.1–2.2.3)
   - 3.2.P.3.1–3.5
   - 3.2.P.4.1–4.6
   - 3.2.P.5.1–5.6
   - 3.2.P.6
   - 3.2.P.7
   - 3.2.P.8.1–8.3
   - 3.2.A.1–A.3

   Then "Module 1 (Write the parts will be affected)". *Typos in the source: "3.2.P.4 Control of FPP" should be P.5. The list has no 3.2.S.7.3 and no 3.2.R.*
5. **Risk Assessment For the Change.**

**A — Supportive Documents for Post Marketing Variation Approval & Inquiry with Assessment Submissions:**

1. **Supportive documents for DMF.**
   - Comparison table: Specifications according to the monograph | Current Suppliers Specification Limits | Specification (S4.1) of Current Suppliers in case it is supported by DMF | Proposed Suppliers COA Specification Limits | Specification (S4.1) of Proposed Suppliers | Justification for any change.
   - DMF sections to submit as a PDF (in a separate folder):
     - Manufacturer S.2.1
     - Organic impurities & residual solvents (S.3.2)
     - Specifications of API S.4.1
     - Batch analysis S.4.4
     - Container closure system S.6
     - Stability Specification S.7.1 & S.7.2
     - GMP with License
     - Letter of Access and Statement of Commitment
   - "N.B. Comparison should be made for specification values, not the result value."
2. **Change of API or FP specification (Inquiry with assessment).**
   - FP table: Old FP Specifications | New FP Specifications | Justification.
   - API table: Specification limit of COA of old supplier(s) | *(second column also printed "old supplier(s)" — **error in source**)* | Tests mentioned in monograph.
   - Note: "Mention all tests, please specify the applicable reference or standard, indicating whether the test is based on an in-house method or a pharmacopeial reference."
3. **Post-Marketing Variation Approval.**
   - Yes / No / No. of Batches:
     1. Batch Analysis Data [No. of batches – Result: Conform/Non-conform]
     2. Stability Data [type of study (6 months Accelerated & Long-term), Result (e.g. Pass) & Date of Approval]
     3. Comparative dissolution study / bioequivalence [Result: conform]
     4. Process Validation Report [3 consecutive batches successfully produced – type of batches (pilot or production)]
   - Comparison table: Approved Finished Product Specification 3.2.P.5.1 | CADAC Specification | Stability Approval Specification | Stability data 3.2.P.8.3 | Justification for any Changes.

**B — Inquiry without assessment:**
- "If the submitted request will affect the approved specifications of the finished product?" Yes / No.
- "*Note: Please Attach The cover letter mentioned in (Annex II Declarations template 5 Signed and Stamped)".

**C — Appeal Submissions:**
- Full Description of the appeal
- Applicant Justification
- Supportive Documents/Studies

**D — Reliance Submissions** (Yes / No):
1. Valid Certificate of Pharmaceutical Product (CPP).
2. Updated relevant sections of CTD dossier. "(However, the non-sequential order of versions of the Common Technical Document (CTD) makes the reliance evaluation unreliable as the company must submit the updated version contains all sequential updates)".
3. Verification of Sameness. (Sameness Letter signed and stamped on — *text truncated in source*)
4. Unredacted Assessment report and/or Q&A (otherwise justified).
5. Proof of Approval from at least one reference regulatory authority.
6. Application submitted to the SRA (A linking between the application and the approval from the Reference Authority must be declared (unless otherwise justified)).

Then:
- "*Please Identify the Climatic Zone on which the stability study in country of origin was approved."
- A second table (Yes / No / No. of Batches / Result):
  1. Batch Analysis Data
  2. Stability Data (type & date of approval)
  3. Comparative dissolution / bioequivalence
  4. Process Validation Report (type of batches)

**Closing declaration (p.61), verbatim:**
> "I hereby declare that all information and accompanying supporting data provided in this application and dossier are accurate, authentic, and complete. The proposed variation complies with all regulatory and quality standards."

Signature fields: Signature by the Authorized Person; Company Stamp; Official Title; Date.

#### Annex II: Declarations — Templates 1–6 (pp.62–67)

Heading: "(In case of License holder Transfer -Addition of Manufacturing Site -Inquiry Without Assessment/Fullfilling Studies)". Note: "All declarations (of the request) shall be submitted attached with the application".

**Common header block** (Templates 1, 2, 4, 5 and 6):
- Addressee (Arabic): «السيد / رئيس الإدارة المركزية للمستحضرات الصيدلية — الإدارة العامة لتسجيل المستحضرات البشرية — إدارة المتغيرات للمستحضرات البشرية — تحية طيبة وبعد،،،،، بخصوص المستحضر الآتي:». Template 5 has no «السيد / رئيس…» line.
- Fields:
  - Trade Name
  - Dosage Form
  - Active Ingredients / Strength
  - Registration No.
  - Applicant Company
  - License Holder / MAH
  - Manufacturer / Packager
  - License Validity: o Valid / o In-valid; o Re-Reg 296/2009 / o Re-Reg 425/2015 / o Re-Reg 150/2022
  - Current status
  - Proposed status
- Each template closes with «وتفضلوا بقبول وافر الاحترام والتقدير،،،،،» and is signed «رئيس مجلس إدارة الشركة» + «ختم الشركة».

**The six templates:**

| Template | Use (inferred from heading and wording) | Undertaking text (Arabic, ligatures corrected) | Page |
|---|---|---|---|
| 1 | LH transfer — old owner | «أتعهد أنا ............ رئيس مجلس إدارة شركة ............ (المالك القديم للمستحضر) ............ بأن المستحضر ليس له تركيزات أخرى من نفس الشكل الصيدلي أو أشكال صيدلية أخرى مسجلة أو تحت التسجيل مملوكة للشركة.» | p.62 |
| 2 | LH transfer — new owner | Same as Template 1 with «(المالك الجديد للمستحضر)» | p.63 |
| 3 | List of registered and under-registration products (cf. 1.2.4.1) | «أتعهد أنا ............ رئيس مجلس إدارة شركة ............ بأن المستحضرات المملوكة للشركة هم كالآتي:». Table: Registered Product (Trade Name / Dosage Form · API / Strength · Reg. Decree) and Under-Registration Products (same three columns). No product header block. | p.64 |
| 4 | Site addition (cf. 1.2.4.7) | «أتعهد أنا ............ رئيس مجلس إدارة شركة ............ بتحمل كافة المسؤولية القانونية لإضافة مكان التصنيع .......(اسم المصنع الجديد/المصانع الجديدة)....... دون أدنى مسؤولية على هيئة الدواء المصرية تجاه عقود التصنيع المبرمة بين شركة .........(اسم المالك للمستحضر)......... وشركة .........(اسم المصنع القديم/المصانع القديمة).........» | p.65 |
| 5 | Inquiry without assessment (cover letter cited in Annex II-B) | Table: Current Status / Proposed Status / Justification for the change. Then: «*اتعهد انا شركة ......... بان الطلب المقدم لادارة المتغيرات inquiry without assessment وبان التغيير المذكور اعلاه سوف (يؤثر / لا يؤثر) علي المواصفات النهائية للمستحضر وان الشركة سوف تقوم بالتغيير علي مسؤليتها» | p.66 |
| 6 | Completing studies | «أتعهد أنا شركة ......... باستكمال دراسة الثبات طويلة المدي على التشغيلة الانتاجية الاولي (..........) وفي حالة حدوث اي تغيير في مواصفات المستحضر النهائية وله تاثير سلبي علي جودة وفاعلية المستحضر نتعهد بابلاغ ادارة المتغيرات بهذا التغيير.» | p.67 |

**History table (p.68):** Summary of Changes "New Issue"; Issue date blank; Version No. 1.

---

## 4. Draft B — NP.CAPP.065 v6: full content and precise diff vs v5

### 4.1 What v6 contains (pp.1–20)

| Part | v6 pages | Content |
|---|---|---|
| Cover, TOC | 1–2 | TOC is **new** (v5 had none). |
| Scope, Objective | 3 | Minor wording changes (§4.3). |
| Module 1 matrix | 3–6 | Rows 1.0 … Additional Data with I / G(Imported) / G(Local) — reproduced in full in §4.2. |
| Note | 7 (l.16–21) | Verbatim: "This Notice to Applicants presents the required documents according to the application categories (Innovator, Imported Generic, and Local products). For detailed guidance on the applicable Module 1 documents for each regulatory activity (New Registration, Renewals, Variation) and submission scenario, applicants should refer to **Module 1 Submission Guidance**." |
| Module 2 | 7–12 | 2.1 → 2.7.6. All R for I, NR for both G — **identical to v5**. |
| Module 3 | 12–15 | 3.1 → 3.3, all R/R/R — **identical to v5**. |
| Module 4 | 16–17 | 4.1 → 4.2.3.7.7 R/NR/NR; 4.3 R/O/O — **identical to v5**. |
| Module 5 | 18–19 | Changed in 4 rows (§4.4). |
| Summary of CTD Structure | 19 | Innovators R R R R R; Generics R · "Incorporated in Modules 3, 4 & 5" · R · O · P — **identical to v5**. |
| Abbreviations | 19 | Same list; definition of O changed (§4.3). |
| References | 20 | Unchanged (ICH CTD; HSA Singapore). |
| History Table | 20 | Adds v6. |
| Annex I | — | **Removed.** Now A Annex (2). |

### 4.2 v6 Module 1 matrix (B pp.3–6) — every row

All rows verified with `pdfplumber` x-positions. Columns: I | G (Imported) | G (Local).

| v6 § | Item | I | G-Imp | G-Loc |
|---|---|---|---|---|
| 1.0 | Cover Letter | R | R | R |
| 1.0 | Tracking Table | R | R | R |
| 1.2.1 | Application Form | R | R | R |
| 1.2.2.1 | Letter of Attorney for Company Representative | R | R | R |
| 1.2.2.2 | Manufacturing License and IDA License | R | R | R |
| 1.2.2.3 | GMP Certificate(s) / Alternative Documents | R | R | R |
| 1.2.2.4 | The Register of Trade | R | R | R |
| 1.2.2.5 | Toll Manufacturer License | NR | NR | R |
| 1.2.2.6 | Scientific Office License | R | R | NR |
| 1.2.2.7 | Importers Register License | R | R | NR |
| 1.2.2.8 | Store License | R | R | R |
| 1.2.2.9 | Authorisation Letter / Agency Agreement | R | R | R |
| 1.2.2.10 | Manufacturing Agreement | R | R | R |
| 1.2.2.11 | Packaging Agreement | R | R | R (the "R" is printed one line lower, but it sits in the Local column) |
| 1.2.2.12 | Storage Agreement | R | R | R |
| 1.2.2.13 | Other Agreements | R | R | R |
| 1.2.2.14 | Termination / Waiver | R | R | R |
| 1.2.3.1 | Registration Request Approval | R | R | R |
| 1.2.3.3 | Name Approval | R | R | R |
| 1.2.3.4 | Registration License | R | R | R |
| 1.2.3.5 | Preliminary Approval | R | R | R |
| 1.2.3.6 | Non-Reference Approval | R | R | R |
| 1.2.3.8 | Pricing Certificate | R | R | R |
| 1.2.3.9 | Pharmacovigilance Approval | R | R | R |
| 1.2.3.10 | Inspection Report | R | R | R |
| 1.2.3.11 | Importation Approval for each API | NR | NR | R |
| 1.2.3.12 | CADC Report | R | R | R |
| 1.2.3.13 | Stability Study Approval | R | R | R |
| 1.2.3.15 | Module 3 Approval | R | R | R |
| 1.2.3.16 | Module 5 Approval | R | R | R |
| 1.2.3.17 | Pre-approved letters from EDA concerning the product | R | R | R |
| 1.2.3.18 | Variation Approvals | R | R | R |
| 1.2.3.20 | Registration License for the Solvent | R | R | R |
| 1.2.4.1 | Declaration … Products owned by the Toll Company | NR | NR | R |
| 1.2.4.2 | Declaration … LH specifying the API Manufacturers | R | R | R |
| 1.2.4.3 | Declaration … LH specifying approved pack in Egypt | R | R | R |
| 1.2.4.4 | Declaration … LH stating the Form of Bulk | R | R | NR |
| 1.2.4.5 | Declaration … manufacturer of the active substance (modification) | R | R | R |
| 1.2.4.6 | Declaration Letter from API Supplier | R | R | R |
| 1.2.4.7 | Declaration Letter for Site Addition | R | R | R |
| 1.2.4.8 | Declaration Letter Form LH stating all Variations & Justification | R | R | R |
| 1.2.4.9 | Other declarations requested by EDA | R | R | R |
| 1.2.4.10 | List of the Countries where the Product is registered & marketed | R | R | R |
| 1.2.5.1 | The Reference Product Documents | R | R | R |
| 1.2.5.4 | The latest recent Pharmacopeia | R | R | R |
| 1.2.6.1 | Certificate of Pharmaceutical Product (CPP) | R | R | R |
| 1.2.6.2 | List of Affiliates / Subsidiaries | R | R | R |
| 1.2.7.1 | Sameness Letter | R | R | NR |
| 1.2.7.2 | Unredacted Assessment Report | R | R | NR |
| 1.2.7.3 | RRA Variation Application with Annexes | R | R | R |
| 1.2.8.1 – 1.2.8.7 | Composition Certificate; Specifications; Any Composition Calculations; Pellets / Premix; Opadry / Coating Premix; Capsule Shell; Synonyms Evidence | R | R | R (each row) |
| 1.2.9 | Certificate of Analysis | R | R | R |
| 1.2.10.1 – 1.2.10.4 | PAC Approval from the COO; Summary of Change; Justification; Additional documents | R | R | R (each row) |
| 1.2.11 | Proof of Payment | R | R | R |
| 1.3.1 | SPC, Labelling and Package Leaflet | R | R | R |
| 1.3.2 | Mock up | R | R | R |
| **1.3.5** | **Product Information already approved in the member states** | R | R | R |
| — | Responses to Questions | R | R | R |
| — | Additional Data | R | R | R |

The matrix gives no conditions at all. Every condition, legalisation rule and activity qualifier now lives only in A. B's "R" means "required when applicable per A" — **that reading is my interpretation**, prompted by the B p.7 note and by the many "R" entries for local products on items that A restricts to imported products. This needs EDA confirmation.

### 4.3 Diff v5 → v6: non-matrix changes

| Item | v5 (in force) | v6 draft | Ref |
|---|---|---|---|
| Title | "…Human Pharmaceutical Products **Registration**" | "…Human Pharmaceutical Products" | v5 p.1 / B p.1 |
| Header | "General Administration For Human Pharmaceuticals Registeration" (typo) | "…Registration" | all pages |
| TOC | none | added | B p.2 |
| Line numbers | none | added | B passim |
| Scope | "applied **on** local and imported…" | "applied **to** local and imported…" | v5 p.2 / B p.3 |
| Objective | "…compile applications **for the registration of human pharmaceutical products**." | phrase deleted | v5 p.2 / B p.3 |
| Module 1 structure | 1.1 Administrative Requirements (1.1.1–1.1.20) + 1.2 Technical Studies/Approval (1.2.1–1.2.5.2), each with conditions in the cell | eCTD-style 1.0 / 1.2.1–1.2.11 / 1.3.x / Responses / Additional Data, matrix only, no conditions | v5 pp.2–12 / B pp.3–6 |
| General notes after M1 | v5 p.13, 5 notes: (1) soft copies must be complete for acceptance; (2) originals in hard copy after assessment, for issuing the MA licence; (3) imported — do not re-submit documents already in other modules; (4) **all documents scanned, searchable PDF**; (5) definitions of **Rolling Submission** and **One Submission** | **All removed.** A does not restate them either (no "searchable", "Rolling", "One Submission" or "hard copy original" anywhere in A — searched). A keeps only the Additional Data rule against re-submitting earlier files. | v5 p.13 |
| Note pointing to A | — | New note (quoted in §4.1) | B p.7 l.16–21 |
| Abbreviation "O" | "…the **Registration & Drug Control Department** has the right to ask…" | "…the **General Administration for Human Pharmaceuticals Registration** has the right to ask…" | v5 p.26 / B p.19 |
| Section order at end | Abbreviations → Document History → References → Annexes | Abbreviations → References → History Table | v5 p.26 / B pp.19–20 |
| Annex I application form | v5 pp.27–30 | **Removed** (history: "Removing Annex I application form"). The same form, unchanged, is A Annex (2). | B p.20; A pp.47–50 |

### 4.4 Diff v5 → v6: Modules 2–5 R/NR/O matrix

- **Method:** row-by-row parse of both texts. Every section number with its I / G-Imp / G-Loc values was extracted and compared. A word-multiset comparison of all titles followed.
- **Modules 2, 3 and 4:** zero changes in values and in titles. Only line wrapping differs.
- **Module 5:** 4 changes, all for generics, all relaxations:

| § | Title | v5 (p.24–25) I / G-Imp / G-Loc | v6 (p.18–19) I / G-Imp / G-Loc | Change |
|---|---|---|---|---|
| 5.3.2.2 | Reports of Hepatic Metabolism and Drug Interaction Studies | R / R (If applicable) / R (If applicable) | R / **NR** / **NR** | relaxed |
| 5.3.3.1 | Healthy Subject PK and Initial Tolerability study report | R / R / R | R / **NR** / **NR** | relaxed |
| 5.3.5.4 | Other Study Reports | R / R / R | R / **NR** / **NR** | relaxed |
| 5.3.7 | Case Report Forms and Individual Listings | R / R / R | R / **O** / **O** | relaxed |

Unchanged Module 5 rows (I / G-Imp / G-Loc):
- 5.1 R/R/R
- 5.2 R/R/R
- 5.3.1.1 R/O/O
- **5.3.1.2 Comparative BA & BE R/R/R**
- 5.3.1.3 R/O/O
- **5.3.1.4 Bioanalytical and Analytical Methods R/R/R**
- 5.3.2.1 R / R (If applicable) / R (If applicable)
- 5.3.2.3 R/NR/NR
- 5.3.3.2–5.3.3.5 R/NR/NR
- 5.3.4.1–5.3.4.2 R/NR/NR
- 5.3.5.1–5.3.5.3 R/NR/NR
- 5.3.6 R/NR/NR
- 5.4 R/R/R

### 4.5 Diff v5 → v6: Module 1 item by item (v5 number → v6/A number)

| v5 § (page) | v5 item and I/G-Imp/G-Loc | → v6/A § | v6 I/G-Imp/G-Loc | What changed |
|---|---|---|---|---|
| 1.1.1 (p.2) | Application form, Annex I — R/R/R | 1.2.1 | R/R/R | Form moved to A Annex (2); variations get a separate form (A Annex 3) |
| 1.1.2 (p.2) | Letter of Attorney — R/R/R | 1.2.2.1 | R/R/R | A adds: valid, with validity date, authenticated by a bank |
| 1.1.3 (p.2) | Fees payment receipt — R/R/R | 1.2.11 | R/R/R | Renamed "Proof of Payment" |
| 1.1.4 (p.2) | Action Letter & Name Approval (new) / Registration Licence & Preliminary Approval (re-reg) — R/R/R | 1.2.3.1, 1.2.3.3, 1.2.3.4, 1.2.3.5 | R/R/R each | Split. "Action Letter" no longer named; *(interpretation)* replaced by "Registration Request Approval" |
| 1.1.5 (p.2–3) | Pricing Certificate — R/R/R | 1.2.3.8 | R/R/R | **Added:** old pricing with no expiry date also needs evidence of an update request |
| 1.1.6 (p.3) | Pre-approved EDA letters — R/R/R | 1.2.3.17 | R/R/R | Examples added: Decree 600 exemptions; approval to produce production instead of pilot batches |
| 1.1.7 (p.3) | Variation approvals (re-reg) — R/R/R | 1.2.3.18 | R/R/R | Same sub-folder rule; now also for RPA and Variation |
| 1.1.8 (p.3) | PV approval — R/R/R | 1.2.3.9 | R/R/R | — |
| 1.1.9 (pp.3–4) | Leaflet (Rolling: approved; One Submission: proposed EN+AR Word SmPC & PIL, reference SmPC/PIL, PIL-only and translation letters, non-referenced → committee approval, translated reference) — R/R/R | 1.3.1 + 1.2.4.9 + 1.2.5.1 + 1.2.3.6 | R/R/R | Split by activity, not by Rolling/One Submission: approved leaflet = **Renewal**, proposed = **New**. PIL/translation letters → 1.2.4.9. Reference SmPC/PIL and translated reference → 1.2.5.1. A adds "Manufacturer and excipients must be mentioned" (approved leaflet). |
| 1.1.10 (pp.4–5) | Layout (Rolling: approved; One Submission: coloured stamped layout, pharmacopoeial monograph, original-pack image) — R/R/R | 1.3.2 (+ 1.2.5.4) | R/R/R | Approved mock-up = Renewal, "different mockups for each manufacturer"; proposed = New. The monograph item no longer sits under layout (latest pharmacopoeia is 1.2.5.4). |
| 1.1.11 (p.5) | Inspection report: pilot/production batches (new) NR/NR/R; valid marketed batch (re-reg) R/R/R | 1.2.3.10 | R/R/R | **Added:** site inspection for imports from non-reference countries not marketed in reference countries; BE-study inspection report naming the BE centre (new and renewal); variation cases |
| 1.1.12 (p.5) | Importation approval per API — NR/NR/R | 1.2.3.11 | NR/NR/R | Added: release letter → invoice; renewal → latest Importation Plan; API-maker variation → matching batch-number evidence |
| 1.1.13 (pp.5–6) | CPP/eCPP — R/R/R (local: "For Under-License Products") | 1.2.6.1 | R/R/R | Same content; the local qualifier now lives only in A ("Imported and Under license") |
| 1.1.14 (p.6) | List of countries — R/R/**NR** | 1.2.4.10 | R/R/**R** | Local now R in the matrix. A: UL and Imported only, legalised. |
| 1.1.15 (p.6) | Sameness letter — R/R/NR | 1.2.7.1 | R/R/NR | A: New and Variation, imported |
| 1.1.16 (p.6) | Unredacted Assessment Report — **O/O**/NR | 1.2.7.2 | **R/R**/NR | **Tightened: Optional → Required** for innovators and imported generics |
| 1.1.17.1 (p.6) | Factory licence & IDA — R (imported bulk only) / R (imported bulk only) / R | 1.2.2.2 | R/R/R | Matrix drops the "imported bulk only" qualifier. A keeps it for New/Variation but not for Renewal. A adds "and/or EDA Data Certificate" and "both parties" (F-Toll). |
| 1.1.17.2 (p.6) | Register of trade — R/R/R | 1.2.2.4 | R/R/R | A: "Variation (for License Holder only)"; both parties for FT/T/UL |
| 1.1.17.3 (p.6) | Toll manufacturer licence — NR/NR/R | 1.2.2.5 | NR/NR/R | A: must name factory and storage site |
| 1.1.17.4 (p.7) | Scientific office licence — R/R/NR | 1.2.2.6 | R/R/NR | A also lists it for Under-Licence (local) products |
| 1.1.17.5 (p.7) | Importers register — R/R/NR | 1.2.2.7 | R/R/NR | — |
| 1.1.17.6 (p.7) | Store licence (if different from factory) — R/R/R | 1.2.2.8 | R/R/R | Imported rule refined (differs from manufacturer / from the importer licence) |
| 1.1.17.7 (p.7) | Agreements (manufacturing — imported exempt; storage; packaging — bulk; authorisation/agency — UL/imported) — R/R/R | 1.2.2.9, .10, .11, .12, .13, .14 | R/R/R each | Split into six rows. **New:** 1.2.2.13 Other Agreements; 1.2.2.14 Termination/Waiver (Real Estate Registry / Ministry of Justice route for LH transfer). Packaging and storage agreements for imports may now be **either** bank + EDA legal **or** chamber + embassy. Agency letter: chamber **or notary public** + embassy. |
| 1.1.17.8 (p.7) | Toll company product-list declaration — NR/NR/R | 1.2.4.1 | NR/NR/R | Also for Variation (LH transfer to a toll company), with active ingredients |
| 1.1.17.9 (p.8) | LH declaration of API manufacturers (UL) — NR/NR/R | 1.2.4.2 | R/R/R | Extended to imported products; "complete addresses"; legalised |
| 1.1.17.10 (p.8) | LH declaration of API manufacturers + Module 3 (re-reg) — O/O/O | 1.2.4.2 | R/R/R | Merged into 1.2.4.2 — no longer optional |
| 1.1.17.11 (p.8) | Bulk-form declaration — R/R/NR | 1.2.4.4 | R/R/NR | A: may be on LH letterhead if same entity or affiliate |
| 1.1.18 (p.8) | Solvent licence ("Powder for Injection") — NR/NR/**R** | 1.2.3.20 | **R/R/R** | Now any dosage form that needs an attached solvent; licence must show the solvent pack |
| 1.1.19 (p.8) | Latest pharmacopoeia — NR/NR/**R** | 1.2.5.4 | **R/R/R** | Imported products too |
| 1.1.20 (p.8) | **Letter of Access (API master file)** — NR/NR/R | (only a bullet in 1.2.4.9; DMF list in Annex 3) | — | **No longer its own row** |
| 1.2.1 (pp.8–10) | Composition certificate with 8 N.B. points — R/R/R | 1.2.8.1–1.2.8.7 | R/R/R | Split into seven sub-sections. **New content:** function of each ingredient; excipient grade; "most recent specifications of each ingredient"; local New = identical to the inspection composition; Variation = old + new composition; paraben-limit calculation for oral liquids |
| 1.2.2.1 (p.10) | CADC certificate + composition (Rolling) — R/R/R | 1.2.3.12 | R/R/R | No longer "Rolling only". Activity-specific rules; batch type added; **"must be confirm"** |
| 1.2.2.2 (p.10–11) | Stability approval (Rolling) — R/R/R | 1.2.3.13 | R/R/R | A: **Renewal (long-term) and Variation only — not New** |
| 1.2.2.3 (p.11) | BE / comparative in-vitro approval (Rolling) — R/R/R | 1.2.3.16 "Module 5 Approval" | R/R/R | New local: "BE study decision letter"; renewal: re-registration or exemption |
| 1.2.2.4 (p.11) | Technical Affairs approval (Rolling) — R/R/R | 1.2.3.15 "Module 3 Approval" | R/R/R | Renamed; New and Variation |
| 1.2.3.1 (p.11) | CoA of active substance (on supplier letterhead) — R/R/R | 1.2.9 | R/R/R | Now **API and FPP**. "Supplier letterhead" wording dropped. |
| 1.2.3.2 (p.11) | Specifications — R/R/R | 1.2.8.2 | R/R/R | Variation: old and new |
| 1.2.4.1–1.2.4.2 (p.12) | GMP of FPP and API makers — R/R/R | 1.2.2.3 | R/R/R | Moved into Legal Documents; "Alternative Documents" added; GMP "purpose" wording; packager GMP for imported bulk |
| **1.2.4.3 (p.12)** | **CEP incl. annexes + written commitment if CEP revised/renewed/withdrawn — O/O/O** | **— none** | — | **Removed as a row.** CEP survives only as an Annex 2 tick-box/field and an Annex 3 variation item. *(The eCTD Annex 5 has 1.2.4.11 "Ph. Eur. CEP for TSE" — a TSE CEP, not the API CEP.)* |
| 1.2.5.1 (p.12) | Reference (online/textbook) **or** Non-Reference Approval — R/R/R | 1.2.5.1 + 1.2.3.6 | R/R/R | "Route of administration" added to identity; scanned strip/pack of reference and test product added |
| 1.2.5.2 (p.12) | Leaflet of the reference product — R/R/R | inside 1.2.5.1 | — | Merged |
| — | — | **New in v6/A:** 1.0 Cover letter + Tracking table; 1.2.4.3 approved-pack declaration; 1.2.4.5 API-maker change declaration; 1.2.4.6 API supplier declaration; 1.2.4.7 site addition; 1.2.4.8 LH variations declaration; 1.2.6.2 affiliates list; 1.2.7.3 RRA variation application; 1.2.10.1–4 PAC requirements; 1.3.5 (B only); Responses to Questions; Additional Data | see §4.2 | All new rows |

---

## 5. How A and B relate to each other and to the EG eCTD Module 1 tree

1. **Division of labour.** B v6 keeps the CTD-wide R/NR/O/P matrix for Modules 1–5 by product category (I / G-Imp / G-Loc). A is the only place that says, per regulatory activity and per registration type, which Module 1 document is needed and in what form (B p.7 note). B's Annex I application form has moved into A (Annex 2). In short: **Module 1 detail moved out of B into A**; Modules 2–5 stay in B.
2. **Numbering.** A and B share the same EG eCTD Module 1 numbering: 1.0 / 1.2.x / 1.3.x, the same numbers as the eCTD technical guidance draft, Annex 5 "Section 1.2", Table 7 (eCTD draft, TOC p.55). The 1.2.x list in the EG M1 eCTD Specification draft (Appendix 2) has the same 119 node numbers as Annex 5 (checked by list comparison). Wherever A uses a number, the title equals the Annex 5 title.
3. **A uses a subset of the eCTD tree.** The tree nodes A skips (and B's matrix skips too) are:
   - **1.2.2:** .15 Tax Card; .16 List of Distributors; .17 IP Protection Law 82/2002 Commitment; .18 NEW local MA legal Agreement; .19 Letter of Authorisation for a new Applicant in Egypt; .20 PV Agreement MAH–Service Provider; .21 GMP Certificate.
   - **1.2.3:** .2 Inquiry Approval; .7 Exemption Approval; .14 Stability Protocol Approval; .19 Innovative Products Scientific Committee Approval.
   - **1.2.4:** .11 to .22 (TSE CEP; TSE/BSE declaration; raw-material storage responsibility (local); excipient supplier and origin; albumin trade name and batch release; plasma-derivative commitment; no-change-of-address; pack type; insert declaration; SMF declaration; storage at 25 °C).
   - **1.2.5:** .2 Scientific Reference; .3 Reference for trade-name change.
   - **1.2.7:** .4 to .6 (correspondence with the reference agency; list of changes since the first EMA/FDA MA; rejection or amendment reporting commitment).
   - **1.2.12** biologicals analysis; **1.2.13** plasma-derived; **1.2.14** scientific advice; **1.2.15** PV documents (PSMF, PSUR, RMP); **1.2.16** inspection documents (SMF, SRA reports, BMR/BPR, recalls, warning letters, APQR, cold chain).
   - *(interpretation)* By their titles, 1.2.12–1.2.13 and the albumin/plasma items are biologics-specific, and 1.2.3.19 / 1.2.14 are innovative-products items. A is the human-pharmaceuticals (chemical) subset. A does not say this; it is inferred from the gaps.
   - **INCONSISTENCY:** some skipped items are topics A itself mentions. "Exemptions from Decree 600" sit in 1.2.3.17, not 1.2.3.7. TSE/BSE declarations go in 1.2.10.4, not 1.2.4.12. The Inquiry approval is referred to in the Annex 2 undertaking («موافقة طلب الاستعلام») but has no 1.2.3.2 folder.
4. **Section 1.3.** The SPEC draft defines:
   - 1.3.1 SmPC, Labelling and Package Leaflet
   - 1.3.2 Mock-up
   - 1.3.3 Specimen
   - 1.3.4 Consultation with Target Patient Groups
   - 1.3.5 Product Information already approved in the Member States (`m1/eg/13-pi/135-approved`, SPEC p.60)
   - 1.3.6 Braille

   SPEC also defines 1.4 Experts, 1.5 Specific requirements, 1.6 ERA, 1.7 Orphan, 1.8 PV, 1.9 Clinical trials and 1.10 Paediatrics (SPEC pp.61ff). A uses only 1.3.1 and 1.3.2. **B's matrix additionally lists 1.3.5 as R/R/R, but A has no 1.3.5 section — INCONSISTENCY.**
5. **1.0, Responses, Additional Data.** A's 1.0 (cover letter + tracking table) matches the eCTD draft §3.2.3 "Module 1.0 Containing Cover Letter and Tracking Table". It also matches the SPEC 1.0 node (`m1/eg/10-cover`, SPEC p.29). A's Additional Data text is near-verbatim from eCTD draft §3.2.7. "Responses to Questions" and "Additional Data" are SPEC nodes (pp.74–75).
6. **Folder logic.** A says Legal Documents are organised by registration type and all other folders by activity (A p.7). A does not say whether that means sub-folders inside `m1/eg/122-legal` (or equivalent) or only a reading aid. The SPEC folder naming would govern; this was not mapped here (**GAP**, see Q-list).
7. **v5 vs eCTD numbering.** The KB note in `CTD-KNOWLEDGE-BASE.md` §8 says the old 1.1.x/1.2.x numbering differs from the eCTD 1.2.x tree. With A and B v6, **if adopted**, the paper/PDF CTD and the eCTD use **one** numbering, and the v5 → v6 map in §4.5 is the crosswalk.

---

## 6. Practical consequences for a company preparing a dossier now (November 2026)

1. **File under v5 today.** Both drafts are unadopted (blank code for A, blank issue/effective dates for both). The consultation closed 29/10/2026. Keep a v5-compliant dossier (1.1.x / 1.2.x numbering, Annex I form, searchable PDFs, One Submission rules) until EDA publishes the final versions and an effective date.
2. **Build every new dossier so it can be re-labelled cheaply.** Keep one file per A-level document (1.2.2.1 … 1.2.11, 1.3.1, 1.3.2) with the v5↔v6 crosswalk (§4.5) as the index. Re-numbering will then be a renaming job, not a re-split. In practice this means:
   - split the v5 "Agreements" bundle into 1.2.2.9–1.2.2.14;
   - split composition into 1.2.8.1–1.2.8.7;
   - move GMP into Legal (1.2.2.3);
   - keep the reference SmPC/PIL with the reference documents (1.2.5.1).
3. **Start a sequence tracking table now** (A Annex 1 format: Sequence Number | Submission Description | Submission Date) and a cover letter carrying a sequence number and a regulatory contact. Both are mandatory in A and in the eCTD drafts.
4. **Legalisation lead times — plan now:**
   - **bank** authentication of the Letter of Attorney (with validity date);
   - bank + EDA legal for manufacturing and storage agreements (local, toll, F-toll);
   - chamber of commerce (or notary) + Egyptian embassy for imported/UL agency letters, LH declarations, list of countries and termination letters;
   - the **Real Estate Registry (Ministry of Justice)** route for waiver letters on LH transfer.

   The six-month legalisation undertaking (A p.44) is a fallback, not a plan.
5. **Imported products: get the unredacted SRA assessment report.** v5 has it as Optional; v6 makes it **Required** for I and G-Imp (1.2.7.2), together with the Sameness Letter. Reliance variations also need the RRA application and approval (1.2.7.3), the COO PAC approval (1.2.10.1) and a declared link between the application and the approval (Annex 3-D).
6. **Local products: items moving from NR to R in the matrix** — list of countries (1.2.4.10), LH API-manufacturer declaration (1.2.4.2), solvent licence (1.2.3.20), latest pharmacopoeia (1.2.5.4), CPP (1.2.6.1), packaging agreement (1.2.2.11). A restricts most of these to UL or imported cases. Until EDA clarifies, prepare them where the product actually has the relevant feature (under-licence, solvent, compendial…) and expect queries otherwise.
7. **Composition package gets heavier:** the function of every ingredient, excipient grades, current specifications of each ingredient, equivalence calculations with the MW reference, and supplier-letterhead compositions for coating, capsule shell, pellets and premix. For local New, the composition must be identical to the inspection composition.
8. **Module 5 for generics gets lighter (if adopted):**
   - 5.3.3.1, 5.3.2.2 and 5.3.5.4 become NR, and CRFs (5.3.7) become Optional.
   - BE reports (5.3.1.2) and bioanalytical reports (5.3.1.4) stay **R**.
   - Do not remove CRFs from current submissions until v6 is in force.
9. **Variations:** A's Annex 3 form is much more structured than anything in v5. It needs:
   - the evaluation route and the categorisation;
   - the CTD-section tick list;
   - BCS class;
   - innovator yes/no;
   - the last batch data and the Decree 600/2018 exemption;
   - supporting-data tables (DMF comparison, FP/API spec comparison, batch, stability, dissolution/BE and PV summaries).

   Pre-build these as company templates. Templates 1–6 are the Arabic undertakings to have ready for LH transfer, site addition, inquiry without assessment and post-approval stability completion.
10. **CEP users:** v5's explicit CEP row (with the EDQM revision/withdrawal commitment) has no home in A. Keep the CEP and the commitment in Module 3 (3.2.S, per the EDA quality guideline — see KB §5), tick CEP in the application form, and ask EDA where the commitment goes.
11. **Stability approval is no longer listed for New Registration** in A (Renewal and Variation only), and the Rolling/One Submission vocabulary is gone. Under One Submission, stability data are assessed inside Module 3. Do not drop the stability package from Module 3.
12. **Drugbox/CTD tool implications** (for `docs/ctd/APP-PLAN.md`): the checklist engine needs two keys per M1 item — registration type (5 values incl. F-Toll) × activity (4 values) — plus the v6 I/G-Imp/G-Loc matrix for Modules 2–5. Model it as data with a "DRAFT" flag; do not hard-code it before EDA adopts it.

---

## 7. Open questions to ask EDA (consultation follow-up or pre-submission meeting)

1. **Status and dates:** Have both drafts been adopted after 29/10/2026? What code will A carry, and what are the effective dates? Will there be a transition period for dossiers already compiled under v5 (and for products already under Rolling Submission)?
2. **F-Toll:** What exactly is an "F-Toll" product, and how does it differ from "Toll" and from "Under License"?
3. **B matrix vs A applicability:** Does "R" in B mean "required when A says it applies"? In particular:
   - Packaging Agreement (1.2.2.11) for local products: A says imported bulk only.
   - CPP (1.2.6.1) and list of countries (1.2.4.10) for G-Local: A says UL and imported only.
   - RRA Variation Application (1.2.7.3) for local: A gives no local case.
4. **1.3.5 "Product Information already approved in the member states"** is in B but not in A. Is it required? For whom? Which "member states"?
5. **Missing eCTD nodes:** Where do these go in a chemical human-pharma dossier?
   - Inquiry Approval (1.2.3.2), Exemption Approval (1.2.3.7), Stability Protocol Approval (1.2.3.14);
   - tax card, distributor list, IP-law commitment (1.2.2.15–1.2.2.17);
   - TSE/BSE declarations (1.2.4.11–1.2.4.12);
   - PSMF/PSUR/RMP (1.2.15.x).

   Should 1.2.3.17 / 1.2.10.4 / Additional Data be used, or the Annex 5 nodes?
6. **CEP:** Where do the CEP copy, its annexes and the EDQM revision/withdrawal commitment go now that v5 1.2.4.3 has gone (Module 3 only, or M1 1.2.4.9)?
7. **Letter of Access:** Is it still mandatory for every local product using an API master file (v5 1.1.20, R for G-Local), or only "where requested" (A 1.2.4.9)?
8. **Removed v5 general notes:** Do these still apply?
   - searchable PDF;
   - hard-copy originals after assessment for issuing the MA licence;
   - "do not re-submit documents already in other modules" for imported products;
   - One Submission vs Rolling Submission definitions.
9. **Stability Study Approval for New Registration:** Is it really no longer an M1 item for new local products (A lists Renewal and Variation only)?
10. **Manufacturing licence for imported finished products at Renewal** (A 1.2.2.2 does not qualify "Imported Bulk" for Renewal): is it required?
11. **Storage Agreement for imported products at Variation:** omitted in both the table and the text. Intentional?
12. **"GMP Alternative Documents":** Which documents are acceptable, and what does "Purpose of the GMP is for EDA Departments or company" require on the certificate?
13. **Folder layout:** Should the per-registration-type grouping of Legal Documents (A p.7) be built as eCTD sub-folders / node-extensions, or only as a reading aid? Which SPEC directory names apply?
14. **Annex 3 errors to correct:**
    - the API specification table has two "old supplier" columns;
    - reliance item 3 is truncated ("signed and stamped on …");
    - "3.2.P.4 Control of FPP" should read 3.2.P.5;
    - the Packaging Agreement applicability sentence cites the "Authorization letter";
    - the tracking-table example has its dates out of order.
15. **Module 5 relaxations for generics** (5.3.2.2, 5.3.3.1, 5.3.5.4 → NR; 5.3.7 → O): confirm they apply to pending dossiers once v6 is effective.
16. **Annex 2 undertaking** still cites «موافقة طلب الاستعلام (للمستحضرات الجديدة)». Is the "Inquiry" approval still part of the new-registration flow, and in which folder?

---

## 8. Gaps and limits of this extraction

- **Consultation window:** "15/10/2026–29/10/2026" comes from the EDA download page / task brief. It is not printed in either PDF, and the site was not re-checked here. PDF creation is 15 Oct 2026.
- **Image-only content:** Figures 1 and 2 (A pp.6–7) were read from rendered images. They show folder names, not file-level detail.
- **Arabic text:** pdftotext breaks lam-alif ligatures. The Annex 2 undertaking and Templates 1–6 were corrected against rendered page images. Spelling inside the templates (e.g. «مسؤليتها», «علي») is kept as printed.
- **No comparison** of A Annex 3 with the variation guideline GL.CAPP.026 v6 forms, or with GL.Bioinn.004 Annexes I/II. The claim that the omitted nodes are biologics-specific is an inference from titles only.
- The EG M1 eCTD Specification draft was used only for node numbers, titles and directories of 1.0, 1.2.x, 1.3.x and 1.4–1.10. Its envelope, XML and file-naming rules are not summarised here (see `ECTD-KNOWLEDGE-BASE.md`).
