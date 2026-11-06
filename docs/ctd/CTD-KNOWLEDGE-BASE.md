# CTD Knowledge Base — Egypt (EDA) human pharmaceuticals

Collected 06/11/2026 for the future CTD-builder tool. **Knowledge and examples only — no tool built yet.**
Every requirement below was read in the source document itself (stored in `docs/ctd/sources/`), not from memory.
Status labels: **VERIFIED** = read in full · **DRAFT** = official but not in force · **NOT FOUND** = searched, not located.

## الخلاصة بالعربي

- **التقديم الحالي:** نظام **One Submission** بقى إلزامي لكل المستحضرات البشرية المحلية (CTD) من **01/11/2025**. الملف بيتسلّم لإدارة الشؤون التنظيمية في الإدارة العامة للتسجيل حسب الـ checklist المنشور. المصدر: إعلان الهيئة بتاريخ 19/08/2025.
- **المتطلبات بالتفصيل:** المرجع الحاكم هو **NP.CAPP.065 الإصدار 5 (01/11/2025)**. فيه متطلبات Module 1 لحد Module 5 في جدول بثلاث خانات:
  - مبتكر (I)
  - جنيس مستورد (G-Imp)
  - جنيس محلي (G-Loc)
- **الجنيس:** Module 2 مش مطلوب (بيتغطّى جوه 3 و4 و5)، وModule 4 اختياري، وModule 5 مطلوب جزئياً (BE والطرق التحليلية).
- **Module 3:** المرجع دليل الهيئة لـ CTD Quality **الإصدار 2 (12/03/2023)**. بيحدد أربع طرق لتقديم الـ API:
  - Prequalification
  - CEP
  - DMF
  - تفاصيل كاملة

  ومع الـ CEP فيه أقسام لازم تتقدّم برضه.
- **أشهر أسباب الرفض في Module 3:** موجودة في **NP.CAPP.040**، وجمعتها كـ checklist تحت.
- **التغييرات (Variations):** **NP.CAPP.112 الإصدار 1 (07/2026)** بيحدد أقسام الـ CTD المطلوبة لكل نوع، 13 تغيير في الـ API و27 في المنتج النهائي.
- **الـ eCTD:** لسه **مسودة** (2026، والتواريخ فاضية). جواها قواعد التسمية والـ PDF والتسلسل وهيكل Module 1.2 المصري. مواصفة الـ EG M1 نفسها (`eg-regional.xml`) **مش منشورة** على الموقع.
- **الأمثلة:** نموذج QOS-PD ونموذج QIS بتوع منظمة الصحة العالمية (يناير 2025)، وقائمة الفرز بتاعتهم، ودليل TRS 986 Annex 6 اللي دليل الهيئة بيستشهد بيه، وفيه أرقام التشغيلات والثبات.

---

## 1. Source register

| # | Document | Code | Version / date | Status | File in `sources/` |
|---|---|---|---|---|---|
| S1 | Submission Guidance for the CTD for Human Pharmaceutical Products Registration (Notice to Applicant) | EDREX:NP.CAPP.065 | **v5, issued & effective 01/11/2025** (v1 14/08/2023 → v2 21/12/2023 → v3 31/03/2024 → v4 23/07/2024) | VERIFIED | EDA_NP.CAPP.065_v5_2025_… |
| S2 | Egyptian Guidelines on CTD Quality Module for Human Pharmaceuticals | (no EDREX code on cover) | **v2, issued 12/03/2023** | VERIFIED | EDA_CTD-Quality-Module-guideline_v2_2023.pdf |
| S3 | Guidance on Quality Module File — Most Common Deficiencies (NtA) | EDREX:NP.CAPP.040 | v1, 09/03/2022 | VERIFIED | EDA_NP.CAPP.040_… |
| S4 | Relevant Sections of CTD File for Human Pharmaceutical Variations (NtA) | EDREX:NP.CAPP.112 | **v1, 01/07/2026** | VERIFIED | EDA_NP.CAPP.112_… |
| S5 | File Content of Stability Study Dossier (NtA, General Administration for Stability) | EDREX:NP.CAPP.090 | **v2, 06/08/2026** | VERIFIED (structure skimmed, not every row) | EDA_NP.CAPP.090_… |
| S6 | Technical Guidance for eCTD Submissions in Egypt | code blank | **v1.0/2026 — DRAFT, issue/effective dates blank** (public consultation) | DRAFT | EDA_eCTD-technical-guidance_DRAFT_v1_2026.pdf |
| S7 | Announcement: One Submission for locally registered human pharmaceuticals (CTD) | — | 19/08/2025 (Chairman directive 13/08/2025) | VERIFIED | (web page) |
| S8 | ICH M4(R4) Organisation of the CTD + Annex: Granularity Document | ICH M4(R4) | 2016 (granularity revised) | VERIFIED | ICH_M4_R4_… |
| S9 | ICH M4Q(R1) CTD Quality | ICH M4Q(R1) | 2002 | Downloaded, the guideline S2 restates its headings | ICH_M4Q_R1.pdf |
| S10 | WHO TRS 986 Annex 6 — Guidelines on submission of documentation for a multisource (generic) FPP: quality part | WHO TRS 986 A6 | 2014 | Key passages VERIFIED (71 pp.) | WHO_TRS986_Annex6_… |
| S11 | WHO PQ Module 2.3 QOS-PD template | — | January 2025 | VERIFIED (full text) | WHO_PQ_QOS-PD_template_Jan2025.docx |
| S12 | WHO PQ Quality Information Summary (QIS) template | — | January 2025 | Downloaded | WHO_PQ_QIS_template_Jan2025.docx |
| S13 | WHO PQ Bioequivalence Trial Information Form (BTIF) | — | 13/01/2023 | Downloaded | WHO_PQ_BTIF_Jan2023.docx |
| S14 | WHO PQ Screening checklist for generic products | — | May 2021 | VERIFIED | WHO_PQ_screening-checklist_May2021.doc |

URLs: S1 `edaegypt.gov.eg/media/bsmpjjz0/…_np.pdf` · S2 `edaegypt.gov.eg/media/qh0jhugj/…` · S3 `/media/shmbx5of/…` ·
S4 `/media/xmifvevo/final-sections-parts-final_2026.pdf` · S5 `/media/xxwbprte/…` · S6 `/media/lxkorhfo/…` ·
S8 `database.ich.org/sites/default/files/M4_R4__Guideline.pdf` · S10 `cdn.who.int/…/trs986-annex6.pdf` ·
S11–S14 `extranet.who.int/prequal/sites/default/files/document_files/…`. All are linked from the EDA "Third Notice to Applicant — CAPP" index page.

**Leads, not yet opened:**
- Guideline on Dossier Requirements — Registration & Re-registration (v04, 12/2023).
- Egyptian Guidelines on Quality Module for re-registration products (v01, 04/2025).
- Regulatory Guides to Decrees 450/2023 (v05) and 150/2022 (v07).
- Guidance on submission of APIs for evaluation (listing/using API).
- Fast-track NtA 2024.

**NOT FOUND** (searched EDA site and web):
- EG Module 1 eCTD Specification (`eg-regional.xml`, DTD, folder names below `m1/eg/`).
- EG eCTD validation criteria.
- "EG Accepted File Formats for eCTD".
- EDA eCTD baseline guidance.
- Controlled-vocabulary files.

The draft S6 refers to all of these as published "on EDA's webpage", but none are on the site yet.

---

## 2. How a CTD reaches EDA today

- **One Submission** (S7, S1 note 5): the whole registration dossier is submitted at once, following international guidelines.
  - Optional from 01/09/2025 for products not yet presented to any EDA central department for technical study or CADC analysis.
  - **Mandatory from 01/11/2025** for all locally registered human pharmaceuticals (CTD).
  - The file goes to the Regulatory Affairs Department for Human Pharmaceuticals (General Administration for Registration) "in accordance with the checklist published on the official EDA website". It is then forwarded to the technical departments.
  - The company does the CADC analysis **after** receiving the registration notification, against the specifications approved by Technical Affairs.
  - It does **not** apply to products already submitted to a central department for technical study or analysis.
- **Rolling Submission** (S1 note 5): data submitted in stages as it becomes available, with ongoing feedback. Items marked "In case of Rolling Submission" in S1 (CADC certificate, stability approval, BE approval, Technical Affairs approval, approved leaflet and layout) belong to that route.
- **General notes in S1:**
  1. The soft copy must be complete for the file to be accepted for assessment.
  2. Originals are submitted in hard copy after the assessment period, for issuing the MA licence.
  3. For imported products, do not resubmit a document already provided in another module.
  4. **All documents must be scanned and searchable PDF.**
- **eCTD (S6, DRAFT):**
  - The draft says eCTD will be mandatory for all submissions, via the portal `https://reg-submit.edaegypt.gov.eg` (pre-registered users only).
  - It is not yet in force.
  - Hard copies still required alongside the eCTD: **legalised CPP** and **labelling (outer and inner pack, SmPC, PIL)**.

---

## 3. Module 1 — EDA administrative requirements (S1, NP.CAPP.065 v5)

Columns:
- **I** = innovator (imported).
- **G-Imp** = generic, imported.
- **G-Loc** = generic, local.

Values: R = required, NR = not required, O = optional (EDA may ask at any time).

### 1.1 Administrative requirements

| No. | Item | I | G-Imp | G-Loc | Conditions and notes |
|---|---|---|---|---|---|
| 1.1.1 | Application form | R | R | R | On company letterhead, signed, stamped, dated. **Annex I** form (fields listed in §3.4). |
| 1.1.2 | Letter of Attorney for company representative | R | R | R | |
| 1.1.3 | Fees payment receipt | R | R | R | For all relevant services, e.g. leaflet, bioequivalence, registration dossier submissions. |
| 1.1.4 | Action Letter & Name Approval (new products) / Registration Licence & Preliminary Approval (re-registration) | R | R | R | The item depends on new vs re-registration. |
| 1.1.5 | Pricing Certificate | R | R | R | Must be valid. If expired, give evidence of the pricing-update request (e.g. screenshot). If re-evaluation is required, submit it. |
| 1.1.6 | Any pre-approved EDA letters concerning the product | R | R | R | E.g. Technical Committee decisions, extension approval. |
| 1.1.7 | Variation approvals (re-registration) | R | R | R | Arranged by date. **Each variation in its own sub-folder named with the variation type** (e.g. "Addition of Manufacturer of API", "composition change"), plus all required studies. |
| 1.1.8 | Pharmacovigilance approval | R | R | R | |
| 1.1.9 | Leaflet | R | R | R | See the leaflet rules below this table. |
| 1.1.10 | Layout | R | R | R | Rolling → approved layout. One Submission → see the layout rules below this table. |
| 1.1.11 | Inspection report — pilot/production batches (new) | NR | NR | R | |
| 1.1.11 | Inspection report — valid, marketed batch (re-registration) | R | R | R | |
| 1.1.12 | Importation approval for each API | NR | NR | R | |
| 1.1.13 | CPP / eCPP from the competent authority in the country of origin | R | R | R (under-licence) | See the CPP rules below this table. |
| 1.1.14 | List of countries where registered & marketed | R | R | NR | |
| 1.1.15 | Sameness letter | R | R | NR | |
| 1.1.16 | Unredacted assessment report | O | O | NR | |
| 1.1.17.1 | Factory licence for manufacturer & IDA licence | R (imported bulk only) | R (imported bulk only) | R | |
| 1.1.17.2 | Register of trade (valid) | R | R | R | |
| 1.1.17.3 | Toll manufacturer licence (valid) | NR | NR | R | Toll products. |
| 1.1.17.4 | Scientific office licence | R | R | NR | |
| 1.1.17.5 | Importers register licence | R | R | NR | |
| 1.1.17.6 | Store licence (if different from factory) | R | R | R | |
| 1.1.17.7 | Agreements | R | R | R | See the agreement rules below this table. |
| 1.1.17.8 | Declaration listing registered and under-registration products owned by the toll company | NR | NR | R | Toll; letterhead, signed, stamped, dated. |
| 1.1.17.9 | Licence-holder declaration specifying the API manufacturers | NR | NR | R | Under-licence products; legalised if a different entity. |
| 1.1.17.10 | Licence-holder declaration of API manufacturers (name and address) + Module 3 | O | O | O | Re-registration; legalised (chamber + embassy) for under-licence. |
| 1.1.17.11 | Licence-holder declaration of the form of bulk (strips, capsules…) | R | R | NR | Imported bulk; legalised. |
| 1.1.18 | Registration licence of the solvent | NR | NR | R | Powder for injection with a solvent attached. |
| 1.1.19 | Latest pharmacopoeia for the finished product | NR | NR | R | Pharmacopoeial products. |
| 1.1.20 | Letter of Access (API master file) | NR | NR | R | |

**1.1.9 Leaflet rules.**
- Rolling Submission: the approved, valid and updated leaflet.
- One Submission:
  - the **proposed leaflet in English and Arabic, in Word format (SmPC and PIL)**;
  - the most updated reference for both the SmPC and the PIL.
- Imported and innovator products with a PIL only: a legalised letter from the country of origin. It must state that the attached PIL (trade name, generic name, concentration, version date and number) is marketed and registered there, and will be translated into Arabic.
- Non-English leaflets, one of:
  - a licence-holder declaration (signature and stamp) that the translation is an authorised medical translation, on the holder's responsibility; or
  - a legalised head-office letter making the scientific office responsible for the translation. The 2-language translation is then signed and stamped by the scientific office, and the office declares the letter will be legalised **within 6 months**.
- Non-referenced product: committee approval(s).
- Non-English reference: an authorised translation of the reference.
- Check the pharmacology guidelines for warnings and exceptions.

**1.1.10 Layout rules (One Submission).**
1. The coloured, stamped outer and inner layout (an editable PDF is preferred).
2. The product monograph from the latest pharmacopoeia (compendial products).
3. A complete image of the original pack (imported and under-licence products).

If the soft layout is accepted, the hard coloured stamped layout is given to the unit administrator for signing and stamping.

**1.1.13 CPP rules.**
- The certificate must be:
  - valid;
  - from the country of origin;
  - issued and authenticated by the competent authority;
  - signed and stamped by the chamber of commerce, a notary public or foreign affairs, and **legalised by the Egyptian Embassy**.
  - **An eCPP is exempt from legalisation.**
- It must name Egypt as the importing country.
- It must show:
  - the date of issue;
  - the trade name;
  - the dosage form(s) and strength(s);
  - the licence holder's address, city and country.
- The product must have been marketed in the country of origin for **at least one year**, or the lack of marketing must be explained.
- The composition must give:
  - each active ingredient by its salt or hydrate, with its quantity per unit dose;
  - the inactive ingredients with their quantities (an attachment is acceptable);
  - the capsule-shell composition, for capsules.
- If the name in Egypt differs, the CPP must say so. Otherwise a separate legalised declaration on licence-holder letterhead is needed.

**1.1.17.7 Agreement rules.**
- **Manufacturing agreement** (applicant ↔ manufacturer): authenticated by the bank or EDA legal department. Imported products are exempt.
- **Storage agreement:** authenticated by the bank or EDA legal department. For imported products it is legalised by the chamber of commerce and the Egyptian embassy.
- **Packaging agreement** (imported bulk): authenticated by the bank and the EDA legal department.
- **Authorisation letter / agency agreement** (under-licence and imported): legalised by the chamber of commerce and the Egyptian embassy.

### 1.2 Technical studies / approvals

| No. | Item | I | G-Imp | G-Loc | Conditions and notes |
|---|---|---|---|---|---|
| 1.2.1 | Composition certificate | R | R | R | See the composition rules below this table. |
| 1.2.2.1 | CADC certificate + CADC composition (+ renewal certificate for re-registration) | R | R | R | Rolling Submission only. Must show trade name and strength, FPP manufacturer and licence holder, API manufacturer, batch number, and the chemical, physical and microbiological tests. |
| 1.2.2.2 | Stability approval | R | R | R | Rolling only. Must show trade name and strength, FPP manufacturer and licence holder, API manufacturer, batch, and purpose. Attach the composition and the FP specification, which must comply with EDA lab analysis. |
| 1.2.2.3 | BE / comparative in-vitro study and approval, if applicable | R | R | R | Rolling only. Same identity fields as 1.2.2.2, plus purpose and composition. |
| 1.2.2.4 | Technical Affairs approval | R | R | R | Rolling only. |
| 1.2.3.1 | API certificate of analysis | R | R | R | On supplier letterhead, signed and stamped, with manufacture date, expiry date and batch number. |
| 1.2.3.2 | Specifications | R | R | R | The recent edition of the pharmacopoeial and/or in-house specifications of all actives. In-house specifications of all inactives on company letterhead, signed and stamped. |
| 1.2.4.1 | GMP of the FPP manufacturer(s) | R | R | R | Valid; production lines specified. |
| 1.2.4.2 | GMP of the API manufacturer(s) | R | R | R | |
| 1.2.4.3 | CEP, including any annexes | O | O | O | If applicable. Add a **written commitment** for when the CEP is revised, renewed or withdrawn by EDQM. |
| 1.2.5.1 | Reference (online or textbook) **or** Non-Reference Approval | R | R | R | Latest edition of the textbook (e.g. BNF), or a recent online reference: FDA, MHRA, EMA, ANSM, Swissmedic, TGA, PMDA, etc. The reference product must be registered and marketed, and identical in active ingredient, concentration and dosage form. Otherwise a Non-Reference Approval from the evaluation unit of scientific data and drug development. |
| 1.2.5.2 | Leaflet of the reference product | R | R | R | |

**1.2.1 Composition rules.**
- The composition is the one on which the studies were run, with updated specifications. It is on letterhead, signed and stamped, and gives the trade name, the dosage form, each active (hydrate and salt) per unit, and the inactives per unit.
- Local products: on manufacturer or applicant letterhead.
- Under-licence products: on applicant letterhead if the composition is attached to the CPP. Otherwise a legalised composition on licence-holder or manufacturer letterhead.
- N.B. points from the source:
  1. The active must be identical to the supplier CoA; otherwise submit the synonyms.
  2. Give the **equivalence calculation** on signed, stamped letterhead, with a reference for the molecular weight.
  3. Separate actives from inactives.
  4. State any overage.
  5. **Coated tablets:** give core and coat separately with the tablet weight, plus the coating composition (e.g. Opadry) on supplier letterhead.
  6. **Hard gelatin capsules:** give body and cap separately with the capsule size, plus the shell composition on supplier letterhead.
  7. **Pellets:** give the supplier composition and the pellets calculation (weight per capsule) on company letterhead.
  8. **Premix:** give the supplier composition.

### 3.4 Annex I — application form fields (S1 pp. 26–30)

The form is addressed in Arabic to «السيد الدكتور/ رئيس هيئة الدواء المصرية».

Fields:
- **Product:**
  - Trade name (English and Arabic)
  - Registration request number / registration number
  - Active ingredient(s) and strength(s)
  - Dosage form
  - Route
  - Physical characters
  - Shelf life
  - Storage condition
  - Approved price pack (number of units per the Pricing Certificate, packaging material per the Stability Approval) and price
- **Reference product** (per the BE approval):
  - Reference drug product (name — RLD, RS…)
  - MAH, manufacturer and country of origin
  - Reference link
  - Therapeutic group
  - ATC code
  - Approved indication
- **Parties and sites:**
  - Applicant and company-profile username
  - MAH / licence holder
  - Manufacturer
  - Manufacturer of solvent or accessories
  - Packager
  - Batch releaser
  - Storage site and address
- **Registration:**
  - Type of registration
  - Market status
  - EDA Chairman decree
  - Batch type and batch numbers
- **API information**, repeated for each API:
  - Submitted as: □ Prequalification □ DMF □ CEP □ Full details in the PD
  - CEP number and issue date
  - API name, form and specs
  - Manufacturer and country, with the address **as in the manufacturer's GMP certificate**
  - Studies performed on each API manufacturer
- **Contact:** person, telephone, e-mail.

The Arabic undertaking signed by the chairman, managing director or authorised signatory commits the company to:
- the accuracy of the data;
- IP Law 82/2002;
- printing the manufacturer, owner (or MAH per the CPP), production date, expiry date, batch number, registration number and price on the outer pack;
- notifying all distributors, which must follow GSP/GDP;
- no change of API source without approval from the General Administration for Human Pharmaceuticals Registration;
- full responsibility for storage, manufacture and conformity, with toll manufacturing only at licensed sites under Ministerial Decree 539/2007 (Egyptian GMP code);
- no transfer of site or ownership without approval;
- for local products, **no ownership transfer before 3 years** of local circulation (Decree 425/2015 and Decree 450/2023 Case 1) **or 5 years** (Decree 645/2018 and Decree 450/2023 Case 3);
- the CADC analysis file matching the registration file;
- submitting the GMP certificate and CoA when importing the API;
- PSUR and pharmacovigilance obligations;
- naming the distributors.

It also states which re-registration studies were done with which API source, and lists the variations as Type, From, To, Status (Final / Conditioned).

---

## 4. Modules 2–5 — what each product type must file (S1)

| Module | I | G-Imp | G-Loc |
|---|---|---|---|
| **1** | R | R | R |
| **2** (2.1 TOC → 2.7.6, full ICH headings) | R | NR — "incorporated in Modules 3, 4 & 5" | NR |
| **3** (3.1 TOC, 3.2.S, 3.2.P, 3.2.A, 3.2.R, 3.3) | R | R | R |
| **4** (4.1 TOC, 4.2 study reports) | R | NR | NR |
| 4.3 Literature references | R | O | O |
| **5** | R | **Partial** (rows below) | Partial |

Module 5 rows (I / G-Imp / G-Loc):

| Section | Title | I | G-Imp | G-Loc |
|---|---|---|---|---|
| 5.1 | Table of contents | R | R | R |
| 5.2 | Tabular listing of all clinical studies | R | R | R |
| 5.3.1.1 | BA study reports | R | O | O |
| **5.3.1.2** | **Comparative BA & BE study reports** | **R** | **R** | **R** |
| 5.3.1.3 | IVIVC | R | O | O |
| **5.3.1.4** | **Bioanalytical and analytical methods** | **R** | **R** | **R** |
| 5.3.2.1 | Plasma protein binding | R | R if applicable | R if applicable |
| 5.3.2.2 | Hepatic metabolism and interaction | R | R if applicable | R if applicable |
| 5.3.2.3 | Other human biomaterials | R | NR | NR |
| 5.3.3.1 | Healthy subject PK and initial tolerability | R | R | R |
| 5.3.3.2 to 5.3.3.5 | Patient, intrinsic, extrinsic and population PK | R | NR | NR |
| 5.3.4 | PD | R | NR | NR |
| 5.3.5.1 to 5.3.5.3 | Efficacy and safety studies | R | NR | NR |
| 5.3.5.4 | Other study reports | R | R | R |
| 5.3.6 | Post-marketing experience | R | NR | NR |
| 5.3.7 | CRFs and individual listings | R | R | R |
| 5.4 | Literature references | R | R | R |

Module 3 is **R for every type at every heading**, from 3.2.S.1.1 down to 3.3, including 3.2.A.1–3 and 3.2.R.1.1/1.2/3.2.R.2. Module 2 sections (all R for innovators, NR for generics):
- 2.1, 2.2
- 2.3.S.1–7, 2.3.P.1–8, 2.3.A.1–3, 2.3.R.1.1/1.2/2
- 2.4
- 2.5.1–2.5.7
- 2.6.1–2.6.7, with every written-summary subsection
- 2.7.1–2.7.6, with every subsection

---

## 5. Module 3 — the Egyptian Quality guideline (S2) and how to present the API

**Structure:** ICH M4Q headings exactly. S2 §4.1.1 lists them and cites ICH M4(R4).

**The four options for the S-part** (S2 "Options for S-part submission"). The applicant must **state at the start of 3.2.S, for each API manufacturer**, which option is used:
1. Confirmation of API **prequalification** document.
2. **CEP** (Certificate of Suitability of the Ph. Eur.).
3. **API master file (APIMF/DMF)**.
4. **Full details** in the product dossier.

**Option 2 — CEP: what is still required** (S2):
- A complete copy of the CEP **with all annexes**. The CEP holder fills in the **declaration of access** for the applicant or FPP manufacturer.
- A written **commitment** to inform EDA of changes or withdrawal of the CEP, acknowledging that withdrawal triggers full 3.2.S data requirements.
- **3.2.S.1.3:** properties not controlled by the CEP or Ph. Eur., e.g. solubilities and polymorphs.
- **3.2.S.3.1:** polymorph studies (unless the CEP specifies the form) and particle size distribution, where applicable.
- **3.2.S.4.1:** the **FPP manufacturer's** API specification, covering all CEP and Ph. Eur. tests plus any extra tests (polymorph, PSD).
- **3.2.S.4.2/4.3:** methods and validation for any test beyond the CEP and monograph.
- **3.2.S.4.4:** results from **two batches of at least pilot scale** against the FPP manufacturer's API specification.
- **3.2.S.5:** the FPP manufacturer's reference standards.
- **3.2.S.6:** packaging specifications. Exception: the CEP specifies the container and the FPP manufacturer declares it uses the same one.
- **3.2.S.7:** exception when the CEP retest period is the same or longer and its storage conditions the same or higher temperature/RH than proposed.
- Sterile API: sterilisation process data, including validation.

**Option 3 — DMF/ASMF** (S2 definition; S6 draft §3.4.1/§4.4):
- **Open part** = Applicant's Part, which the licence holder needs to assess quality.
- **Closed part** = Restricted Part, confidential and disclosed only to the authority.
- The **Letter of Access** goes in Module 1 (S1 1.1.20; S6 places it in m1.2).
- The QOS on the applicant's part sits in 2.3. Under eCTD, the suffix `-ap` is recommended on these files.

**API mix** (API plus one or more excipients, e.g. an antioxidant): see the "Quality Working Party Q&A on API mix" cited in S2.

**Section-level content highlights** (S2):

| Section | Content |
|---|---|
| S.1.1 | INN, compendial name, chemical names, company code, USAN/JAN/BAN, **CAS number**. |
| S.1.2 | Structural formula **with relative and absolute stereochemistry**, molecular formula, relative molecular mass. |
| S.2.2 | A synthetic flow diagram (molecular formulae, weights, yield ranges, structures of starting materials, intermediates and reagents, operating conditions, solvents) **plus** a sequential narrative at commercial batch scale: quantities, critical steps, IPCs, equipment, T/P/pH/time. Alternate processes are described to the same detail. Reprocessing is justified. |
| P.1 | Dosage form; the composition per unit including overages, with function and quality standard; the reconstitution diluent; container and closure. |
| P.3.3 | A flow diagram showing material entry, critical steps and IPC points, plus a narrative including packaging. Equipment is given at least by type and working capacity. Parameters are given as ranges, with critical ranges justified in P.3.4. Environmental conditions are stated (e.g. low RH for effervescents). |
| P.3.5 | Validation or evaluation for critical steps and assays (e.g. sterilisation, aseptic filling). |
| 3.2.A.1 | **Not applicable** for these human-pharmaceutical files. |
| 3.2.A.3 | Large excipient data packages, e.g. novel or non-compendial excipients. A novel excipient is new to approved products, a new route, or above the IID or Handbook level. |
| **3.2.R.1.1** | Executed production documents. Pilot or primary batches by a procedure **fully representative of production scale**. Copies are given for the **batches used in the BE or biowaiver studies**, with English translations where relevant. |
| **3.2.R.1.2** | Master production documents **for each strength, commercial batch size and site**. See the list below this table. |
| **3.2.R.2** | **Tabular** summaries of analytical procedures and validation from S.4.2, S.4.3, S.4.4, S.7.3, P.5.2 and P.5.3. |
| 3.3 | Literature references. |

**3.2.R.1.2 master production documents** must include:
- (a) the master formula;
- (b) dispensing, processing and packaging steps;
- (c) calculations (assay or anhydrous adjustment);
- (d) equipment by type and capacity, with make, model and number where possible;
- (e) process parameters, as target and range;
- (f) the IPC list and specifications;
- (g) the sampling plan: steps, number of samples, frequency;
- (h) precautions (T/RH, maximum hold times);
- (i) for sterile products, SOP references with a list of all SOPs at the end;
- (j) theoretical and actual yield.

**References EDA names for evaluation** (S2 §5):
- ICH Q1A/B/D/E, Q2(R2), Q3A(R2), Q3B(R2), Q3C(R8), Q3D, Q6A, Q8(R2), Q11, M7, M4(R4), M4Q(R1).
- WHO TRS 986 A6; TRS 1010 A10 (stability); TRS 929 A5 Table A.1 (stress studies).
- FDA container-closure guidance (1999) and BCS high-solubility dissolution guidance (2018).
- EMA guidelines: chiral substances; process validation for finished products; sterilisation; dissolution specification for generic IR; in-use stability; inhalation and nasal; oral modified release; IV micellar; declaration of storage conditions; antibiotics impurities.
- Pharmacopoeias: USP, Ph. Eur., BP, JP, Ph. Int.
- To be read together with S2: EDA "Quality Module Submission Guidance" and "**Soft File Arrangement Guidance**". The latter was **not yet located** as a standalone document.

---

## 5b. Module 3 for **re-registration** — GL.CAPP.039 v1 (VERIFIED, read in full)

**Identity:** EDREX: GL.CAPP.039, Version 1. Issued 30/04/2025, **effective 01/01/2026**. 22 pp. Scope: any human product whose Quality Module is evaluated in re-registration. Archived as `sources/EDA_GL.CAPP.039_v1_2025_QM-re-registration.pdf`; the copy the owner uploaded is byte-identical (SHA-256 match).

**Structure:** the same ICH M4Q headings and the same four S-part options as the new-registration guideline v2/2023 (§5 above). It lists Option 3 (DMF) first. The CEP-route rules are **unchanged** from v2: full CEP with annexes, holder's declaration of access, written commitment, the FPP maker's API spec, **2 pilot-scale API batches**, and the S.6/S.7 exceptions.

**What re-registration relaxes, compared with new registration (v2/2023):**

| Section | Re-registration rule (GL.CAPP.039) | p. |
|---|---|---|
| 3.2.S.2.2 | «**Brief** information» on process and controls | 10 |
| 3.2.S.2.1–2.6 | **If data aren't available (e.g. a well-established or old molecule), submit a justification** | 10 |
| 3.2.S.3.1 | Structure confirmation by spectral analyses; **a reference to the identification test in 3.2.S.4 can be accepted** | 10 |
| 3.2.S.4.2 / 4.3 / 4.5 | **Pharmacopoeial API: a reference to the monograph is acceptable** | 11 |
| 3.2.S.4.4 | Results of **recent** batch analyses (the number of batches is not stated for the full/DMF route) | 11 |
| 3.2.S.5, 3.2.S.7.2 | Justification accepted if data are not available (old molecule) | 12 |
| 3.2.S.6 | **Brief** description and materials of the primary packaging (no specification demand stated for the DMF/full route) | 12 |
| 3.2.S.7.3 | Results of **recent** stability studies | 12 |
| 3.2.P.2 (all subsections) | **Brief description** of development studies; **a reference to studies already assessed or to EDA approvals is accepted**; justification if not available | 15 |
| 3.2.P.3.3 | Flow diagram and narrative (no equipment/parameter detail demanded) | 15 |
| 3.2.P.3.4 | Justification accepted for a well-established manufacturing process | 16 |
| 3.2.P.4.1 | **CoAs could be accepted** as excipient specifications | 16 |
| 3.2.P.4.2–4.4, 3.2.P.5.2 / 5.3 / 5.6 | **Pharmacopoeial: reference to the monograph is acceptable** | 16–18 |
| 3.2.P.5.4 | Results of **recent** batch analyses | 17 |
| 3.2.P.5.5 | **Reference to the specification (3.2.P.5.1) could be accepted** | 18 |
| 3.2.P.6, 3.2.P.8.2, 3.3 | Justification if data are not available | 18–20 |
| 3.2.P.7 | Description, materials and specification (description + identification); **CoAs could be accepted** | 18 |
| 3.2.R.1.1 | Executed records of batches **fully representative of a production-scale batch** (no BE-batch wording) | 20 |
| 3.2.R.1.2 | Master documents per strength, batch size and site; **a reference to 3.2.R.1.1 could be accepted** (no (a)–(j) content list) | 20 |

**General notice (p. 20):**
- Data must represent the **current** API and FPP quality **including all approved variations**.
- EDA may ask for anything more «regardless of the current status [of] previously issued EDA approval or assessed parts».

**Carried-over errors from v2:**
- «3.2.P.4 Control of FPP» should read 3.2.P.5.
- 3.2.R.2 cites «2.3.S.4.4, 2.3.S.7.3» where it means 3.2.S.
- «Soft File Arrangement Guidance» is cited but was not found as a published document.

**For the tool:**
- Re-registration is a separate rule set with relaxed acceptance criteria.
- A new document type is needed: the **«justification for unavailable data (well-established molecule / process)»** letter, rebuildable from data. This applies to S.2, S.5, S.7.2, P.3.4, P.6, P.8.2 and 3.3.
- Where the guideline accepts a **monograph reference** or a **CoA**, that satisfies the slot.

## 6. Most common Module 3 deficiencies (S3, NP.CAPP.040) — use as a pre-submission checklist

**3.2.S**
- **S.1.1:** chemical/IUPAC name missing; wrong CAS.
- **S.1.2:** chiral centre not shown; molecular mass of the hydrate missing.
- **S.1.3:** not discussed — pH-solubility, organic-solvent solubility, PSD (low-solubility API), hygroscopicity, polymorphism (low-solubility API).
- **S.2.1:** no responsibility stated for each manufacturer.
- **S.2.2:** the flow diagram does not show all steps and CPPs.
- **S.2.3:** not all raw materials controlled; starting-material preparation details missing; starting-material specification lacks purity or related substances.
- **S.2.5:** no validation of API aseptic processing or sterilisation.
- **S.2.6:** development not submitted.
- **S.3.1:**
  - essential techniques missing;
  - unclear spectra;
  - no interpretation table;
  - **no enumerated structure or zoomed spectra for NMR**.
- **S.3.2:**
  - potential impurities not discussed (non-compendial API);
  - compendial specified impurities excluded without justification;
  - limits above ICH Q3A without justification;
  - starting-material carry-over not discussed;
  - **no elemental (Q3D) or genotoxic (M7) risk assessment**;
  - early-step solvents not controlled without a risk assessment;
  - **no risk assessment for benzene in solvents**.
- **S.4.1:**
  - a universal test is missing (description, ID, assay, impurities);
  - **no reference column with general-chapter numbers** for compendial methods;
  - the FPP manufacturer's API specification is missing;
  - **identification relies on a single chromatographic retention time**.
- **S.4.2/4.3:** procedures missing; **no verification report for compendial methods**; validation missing; no chromatograms for specificity, forced degradation or system suitability.
- **S.4.4:** **fewer than two recent batches**; S.4.1 vs S.4.4 discrepancy; batch number, size, date, type or site missing.
- **S.4.5:** no justification for impurity or solvent limits or for non-routine tests.
- **S.5:**
  - no CoA of the working standard;
  - no **concomitant IR of primary vs secondary standard**;
  - no structure elucidation of the primary-standard batch;
  - impurity standards not discussed.
- **S.6:** incomplete description or specifications; **no IR of reference vs test packaging material**; suitability not justified; no packaging CoA.
- **S.7:**
  - storage conclusion not stated;
  - protocol data incomplete (batch type and size, container, start date, period covered);
  - no results summary;
  - **no commitment letters**;
  - data not up to date;
  - no ongoing study on recent batches;
  - **no forced degradation with chromatograms**.
- **CEP route:**
  - CEP withdrawn or suspended;
  - annexes missing;
  - **the authorisation box not filled or signed by the CEP holder**;
  - no applicant commitment letter;
  - sections not covered by the CEP missing (e.g. S.6 or S.7);
  - a standard other than Ph. Eur. declared;
  - no API specification;
  - **fewer than 2 API batch analyses**.

**3.2.P**
- **P.1:**
  - the API standard does not match the S-part;
  - **excipient grades not declared**;
  - API equivalence (salt) missing or wrong;
  - potency note missing;
  - overage not stated;
  - ingredients removed in process not noted;
  - shell or coating composition missing;
  - **the composition differs from the CPP or any approval**.
- **P.2:**
  - reference product not named;
  - **QTPP, CQAs and CPPs not identified**;
  - no API–excipient compatibility study when excipients differ from the reference product;
  - no formulation comparison with the reference;
  - overage not justified step by step;
  - choice of sterilisation not justified;
  - no compatibility with diluent or device.
- **P.3:**
  - manufacturer responsibilities not stated;
  - **imported: manufacturers differ from the CPP**;
  - the batch formula does not cover all commercial sizes, overage or overfill, or the potency calculation;
  - incomplete flow diagram;
  - **hold times not stated or not supported by stability data**;
  - no transfer and storage precautions between sites;
  - CPPs not discussed;
  - **no process validation on 3 batches (if applicable)** or for all batch sizes.
- **P.4:** no in-house excipient specifications; **no TSE/BSE certificates** for excipients of animal or human origin.
- **P.5:**
  - no general-chapter reference column;
  - a universal test missing;
  - single-RT identification;
  - **dissolution "Q" missing**;
  - in-house method or its validation missing, or no chromatograms;
  - batch description missing;
  - **only 1 batch (minimum 2)**;
  - **"Conform" instead of numeric results**;
  - P.5.1 vs P.5.4 discrepancy;
  - batches not recent;
  - **no Q3D risk assessment**;
  - degradation and synthetic impurity info missing;
  - limit justification missing.
- **P.6:** primary-standard lot missing; working-standard CoA, the primary lot it was standardised against, and concomitant IR missing.
- **P.7:** same gaps as S.6.
- **P.8:**
  - no results summary;
  - storage conclusion missing;
  - incomplete protocol data;
  - **no photostability**;
  - no commitment letters;
  - not up to date;
  - no ongoing batches;
  - **no in-use stability**.

**3.2.R.1.1** — the **executed records of the three manufactured batches** are absent.

---

## 7. Variations → which CTD sections to file (S4, NP.CAPP.112 v1/2026)

S-part headings are titled "[name, manufacturer]". P-part headings are titled "(name, dosage form)". The source notes that EDA may require additional data.

**Drug substance (S-part)**

| # | Change | Sections |
|---|---|---|
| 1 | Name or address of the API, starting-material, reagent or intermediate manufacturer | 3.2.S.2.1; LOA if the API manufacturer changes |
| 2 | Deletion of part of the API manufacturer address (unit, plot) | 3.2.S.2.1, LOA |
| 3A | New or replacement manufacturer of an intermediate or starting material | 3.2.S.2.3 (starting material) / 3.2.S.2.4 (intermediate) |
| 3B.1 | **New or replacement API manufacturer** | S: **new DMF (AP & RP) + LOA**. P: 3.2.P.1, 3.2.P.2.2.1 (if required), **3.2.P.5.4, 3.2.P.8** |
| 3B.2 | API QC testing site | 3.2.S.2.1 |
| 3B.3 | API micronisation site | 3.2.S.2.1; 3.2.S.4.4 if the PSD differs |
| 4 | API manufacturing process | S: updated 3.2.S.2 (RP) + summary of change, S.3.2, S.4, S.7. P: P.8 if required |
| 5 | API batch size | updated 3.2.S.2 (RP), S.4.4 |
| 6 | API in-process tests or limits | S.2.4; P.5.4 if required |
| 7 | API specification parameters or limits | S.4, S.7, S.3.2 if required; P.2.2.1 and P.8 if required |
| 8 | API analytical procedure | S.4.2, S.4.3, S.5 if required |
| 9 | API immediate packaging | S.6, S.7 |
| 10–11 | API packaging specification or method | S.6 |
| 12 | API retest period or storage | S.7; an **extension needs a cover page directly from the supplier** |
| 13 | New, updated or deleted CEP | updated CEP + the updated applicant part concerned (e.g. S.4, S.6, S.7) |

**Finished product (P-part)**

| # | Change | Sections |
|---|---|---|
| 1 | Imprints, embossing/debossing, inks | P.1, P.2.1.2 (if required), P.4 (ink), P.5.1, P.5.4 |
| 2 | Shape or dimensions | P.1, P.5.1, P.5.4 (if required) |
| 3 | **Excipient composition** | P.1, P.2.1.2, P.2.2.1 (if required), P.3.2, P.3.3, P.4, P.5.1, P.5.4, P.8 |
| 4 | Coating weight or capsule-shell weight | P.1, P.2.2.1, P.3.2, P.5.1, P.5.4, P.8 (if required) |
| 5 | **Manufacturing site** | Manufacturing: P.3, P.2.2.1 (if required), P.5.4, P.8, **3.2.R.1.1 + 3.2.R.1.2**. Batch release: P.3.1. Packaging: P.3.1, with P.5.4 and P.8 (if required) for primary packaging. Storage: P.3.1 |
| 6 | Manufacturing process, including an intermediate | P.2.3, P.3.3, P.3.4, P.3.5, P.5.4, P.8, 3.2.R.1.1, 3.2.R.1.2 |
| 7 | Batch size (scale up or down) | P.2.2.1 (if required), P.3, P.5.4 (if required), P.8 (if required), 3.2.R.1.1, 3.2.R.1.2 |
| 8 | IPC tests or limits | P.3.3, P.3.4, P.3.5, P.5.4 |
| 9–10 | Deletion, name or address of a site | updated P.3.1 |
| 11 | Solvent or diluent manufacturer (local/UL) | P.1, P.2.6, P.8 (in-use) |
| 12 | Excipient specification | P.4 |
| 13 | FPP specification | P.5; P.8 if stability-indicating |
| 14 | FPP analytical procedure | P.5.1, P.5.2, P.5.3, P.5.4; P.8 if stability-indicating |
| 15 | Immediate packaging | P.1, P.2.4, P.5.4 (sterile), P.7, P.8 |
| 16–17 | Packaging specification or method | P.7 |
| 18 | Container shape | P.1, P.7, P.8 (if required) |
| 19 | **Pack size** | P.1, P.7, P.8 (if required) |
| 20 | Primary packaging part not in contact | P.1, P.7 |
| 21 | Packaging-component manufacturer or sterilisation | P.7 |
| 22 | Secondary packaging | P.1, P.7 |
| 23 | Shelf-life reduction or extension, storage, in-use | P.8 |
| 24 | Salt equivalence or crystalline form (hydrate, solvate, polymorph) | See the rows below this table |
| 25 | Particle size of a water-insoluble or sparingly soluble API | See the rows below this table |
| 26 | Manufacturing solvents (e.g. purified water, ethanol, methanol) | P.1, P.2.1.2, P.2.2.1 (solvent in core), P.3.2, P.5; P.8 if stability-indicating |
| 27 | Colour | P.1, P.4, P.5.1, P.5.4 |

**Row 24 — salt equivalence or crystalline form.**
- Change: updated supplier DMF with a summary of change, plus P.1, P.2.1.1, P.2.2.1, P.3.2, P.5.4, P.8.
- Clarification: P.1, P.3.2, P.5.4, P.8 (old batches). If the current supplier DMF was evaluated by EDA, also S.1.3, S.3.1, S.7.

**Row 25 — particle size** (the PSD must appear on the supplier CoA as D90 or mesh).
- Change: S.1.3, S.3.1, S.4.4, S.7 (if required), plus P.1, P.2.1.1, P.2.2.1, P.3.2, P.5.4, P.8.
- Clarification: P.1, P.3.2, P.2.2.1, P.5.4 (old batches), plus the S-part if the DMF was evaluated.

Also in force for variations: Variations Guidelines **6th ed. 12/2025**; NtA Type II variations (12/2025); NtA administrative documents and time frame (01/2026). These are in the skill's document register, listed but not opened here.

---

## 8. eCTD — EDA draft technical guidance (S6, DRAFT v1/2026)

Use this to make files **eCTD-ready now**. Do not present it as in force.

**Scope and structure**
- **Scope:** all human medicinal, biological and innovative products, for MAA, variations, renewals, ASMF, PMF and withdrawals.
- **One eCTD per strength or dosage form.** No sequence may cover more than one. No cross-reference between eCTDs (e.g. for the drug substance).
- **Standards:** ICH M2 eCTD **v3.2.2**, the EG eCTD Module 1 Specification, and ICH guidelines.

**Dossier identifier and sequences**
- A random **UUID** (8-4-4-4-12 hex) per dossier, set on the first sequence and constant for life. A new UUID only on re-baselining.
- The first eCTD is **0000**, even after earlier non-eCTD numbering. Next sequences are 0001, 0002…
- A technically invalid sequence is resubmitted **with the same number**. A content or regulatory error gets the **next** number.
- **Related sequence:**
  - unit `initial` or `reformat` → related = own number;
  - otherwise → related = the sequence that started the regulatory activity.
- **Switching to eCTD:** first a **baseline** (0000, submission type `none`, unit `reformat`). Its cover letter states the content is unchanged and only the format changed. Good scanned images with OCR are acceptable. The first new activity is 0001.
- **Re-baselining** (broken lifecycle, e.g. MA transfer or a tool change): new UUID, type `none`, unit `reformat`, all leaves `new`, restart at 0000, cover letter explains why.

**Lifecycle operations**
- Operations are `new`, `replace` and `delete`. **Avoid `append`.**
- **No lifecycle across CTD sections.** Repeatable attributes must match:
  - `m2-3-s` / `m3-2-s`: substance + manufacturer;
  - `m2-3-p` / `m3-2-p`: product-name + dosage form + manufacturer;
  - `m2-7-3` / `m5-3-5`: indication.
- A misplaced leaf is fixed with `delete` plus a `new` that points `xlink:href` to the original file.

**Files and PDF rules**
- **File names ≤ 64 characters** including the extension. **Folder names ≤ 64.** **Total path ≤ 180**, counted from the first digit of the sequence folder.
- No illegal characters (e.g. `%`, `/`, `<`). Multiple files in one section use the `name-var.pdf` convention.
- **PDF 1.4–1.7 or PDF/A-1/-2.**
  - PDF 1.3 or earlier is refused, no exceptions.
  - Text-searchable: produced from a text source; scans with OCR.
  - Scans **without** OCR are accepted for GMP certificates, CoAs, licences, CEPs, manufacturing authorisations, foreign-language originals (the English translation must be searchable), literature, the blank CRF, patient listings, CRFs, and signature-only pages.
  - Embed fonts; tagged PDF preferred; Fast Web View; **no PDF Portfolio**.
- **Security:** no passwords or security settings. If unavoidable (digital signatures), printing and copying must at least be allowed. Electronic signatures are not used. Virus-check every file.
- **Bookmarks:** any document with a TOC has bookmarks. Avoid hyperlink overuse.
- **Node extensions:**
  - per study in Module 5 — use them for all CSRs;
  - in m1-responses, per regulatory activity;
  - no extra folders in m1-responses.
- **Working documents:** Word copies (product information, Module 2) go in `xxxx-workingdocuments` beside the sequence. They are never leaves. **Do not include validation reports.**

**Module 1 placement**
- **Cover letter:** always `new`, with a descriptive leaf title (e.g. "Cover Letter for Sequence 0000").
- **Tracking table:** an annex to the cover letter in every submission. Named **`tracking-var.pdf`** and placed in **`/XXXX/m1/eg/10-cover/`**. Columns: Sequence number, Submission description, Submission type, Submission date.
- **Application form:** `form-af.pdf`, or `form-af-10mg`, `form-af-20mg` when there are several. Always `new`, except `replace` to correct it. Documents that do not fit M2–M5 go as separate files in **m1.2**.
- **Responses:**
  - the full list of questions is the first leaf;
  - split the responses by Quality, Non-clinical and Clinical;
  - file names follow `responses-<activity>-<n>-<content>.pdf` (e.g. `responses-maa-2nd-clin.pdf`, `responses-var03-qual.pdf`);
  - group them under a node extension per activity.
- "Not applicable" M1 documents are left out. A justification goes in the section concerned.

**Module 2 and Module 3 placement**
- **QOS:** one `qos-var.pdf`, or split into `introduction-`, `drug-substance-`, `drug-product-`, `appendices-` and `regional-information-var.pdf`. One QOS per ASMF, with a front page showing version and date.
- **Module 3 structure rules:**
  - One `m32s` per ASMF (applicant's part).
  - **One** applicant `m32s` per API covering all API manufacturers (the FPP manufacturer's control of the API).
  - With a CEP, each CEP goes in 3.2.R, with an `m32s` per manufacturer for data not covered.
  - Combination product: one `m32s` per API.
  - **Only one `m32p`**, even with several FPP manufacturers (manufacturer attribute "all" or "applicant"). The manufacturing process is one document in 3.2.P.3.3.
  - Excipients of human or animal origin and novel excipients go under an attribute such as `animal-human-novel`. Files such as `excipients.pdf` sit directly in `32p4-contr-excip`.
  - Example: `m3-2-s-drug-substance [manufacturer: X|Y|Applicant] [substance: INN]` and `m3-2-p-drug-product [manufacturer: All] [product name: INN] [dosage form: 400-mg-FCT]`.

**Modules 4 and 5**
- An FDA STF need not be reorganised. A US NDA reused for EDA puts each study under a node extension; remove the STF XML and datasets.
- Multiple indications: one `m535` per indication and one 2.7.3 per indication.
- The CCDS goes in 5.3.6.
- Synopses: either copies in 2.7.6, or links to Module 5 plus a listing with hyperlinks.

**Parallel variations (Annex 4)**
- Option 1: replace the document.
- Option 2: keep the "Approved Version" and add "… – Proposed" documents as `new`. Recommended for the SmPC and RMP.
- On approval, delete the proposals and replace the approved document. One consolidated document if several are approved together.

**Withdrawal or rejection**
- Rejected or withdrawn activity: a **consolidation sequence** (unit `response`) restores the current view. A sequence cannot be deleted.
- Withdrawing the whole MA: a new sequence with the cover letter only, type `withdrawal`.

**EG submission types** (Annex 6):
- **Human pharmaceuticals:**
  - `maa`;
  - `var-pac-n` (notification);
  - `var-pac-a` (annual, within **12 months** of implementation);
  - `var-pac-b` (minor);
  - `var-pac-ii` (major);
  - `renewal`, `asmf`, `cep`, `none`;
  - `preass` (pre-assessment);
  - post-MA commitments: `pacstab`, `paccadc`, `paci`, `pacqr`;
  - `5yr` (fifth-year report, otherwise marketing is suspended);
  - `appeal`;
  - `preappinq` (preliminary approval inquiry).
- **Biologics and innovative products:**
  - `renewal`, `none`, `pacstab`, `paccadc`, `pacqr`, `paci`, `PMF`, `withdrawal`;
  - innovative: `maa-inn`, `ipv-admc`, `ipv-admlc`, `ipv-tlc`, `ipv-pu`, `ipv-safeffc`, `imv-majvar`, `imv-minvar`, `imv-not`, `ibv-majqualc`, `ibv-modqualc`, `ibv-minqualc`, `ibv-qcnoimp`;
  - biologicals: `maa-nt`, `maa-ft`, `maa-sb`, `maa-rl1`, `maa-rl2`, `maa-bios`, `np-*`, `rp-*`, `rl-pilc`, `not-*`.
- **Submission modes:** single, grouping, parallel single, parallel grouping (imported, assessed in parallel with the country of origin).
- **Submission units:** initial, validation-response, response, additional-info, corrigendum (only agreed in advance), reformat, re-examination.

**Envelope fields**
- Identifier (UUID), submission type, submission unit, submission mode (variations only), submission number (grouping only), **procedure tracking number** (always).
- Applicant (spelled consistently), authority code **`EDA`**, invented name, INN, sequence, related sequence, submission description.
- **Registration type** (e.g. Imported Finished, Imported Bulk) and **marketing type** (e.g. Local, Tender & Export).

### EG Module 1.2 structure in the eCTD draft (Annex 5, S6)

- **1.2.1 Application form**
- **1.2.2 Legal documents**
  1. Letter of attorney
  2. Manufacturing & IDA licence
  3. GMP certificate(s) / alternatives
  4. Register of trade
  5. Toll manufacturer licence
  6. Scientific office licence
  7. Importers register
  8. Store licence
  9. Authorisation letter / agency agreement
  10. Manufacturing agreement
  11. Packaging agreement
  12. Storage agreement
  13. Other agreements
  14. Termination / waiver
  15. Tax card
  16. List of distributors
  17. IP Law 82/2002 commitment
  18. New local MA legal agreement
  19. Letter of authorisation for a new applicant
  20. PV agreement MAH–provider
  21. GMP certificate
- **1.2.3 EDA approvals**
  1. Registration request
  2. Inquiry
  3. Name
  4. Registration licence
  5. Preliminary
  6. Non-reference
  7. Exemption
  8. Pricing certificate
  9. PV
  10. Inspection report
  11. Importation approval per API
  12. CADC report
  13. Stability study approval
  14. Stability protocol approval
  15. Module 3 approval
  16. Module 5 approval
  17. Pre-approved letters
  18. Variation approvals
  19. Innovative products scientific committee
  20. Solvent registration licence
- **1.2.4 Declarations**
  1. Toll company product list
  2. API manufacturers
  3. Approved pack
  4. Bulk form
  5. API-maker change notification
  6. API supplier
  7. Site addition
  8. All variations & justification
  9. Other
  10. Countries registered/marketed
  11. Ph. Eur. TSE CEP
  12. TSE/BSE supplier declaration
  13. Raw-material storage responsibility (local)
  14. Excipient supplier & origin
  15. Albumin stabiliser trade name
  16. Albumin batch release
  17. Plasma derivative commitment
  18. No-change-of-address declaration
  19. Pack type
  20. Insert declaration
  21. SMF declaration
  22. Storage at 25 °C declaration
- **1.2.5 Reference / compendial**
  1. Reference product documents
  2. Scientific reference
  3. Trade-name change reference
  4. Latest pharmacopoeia
- **1.2.6 Imported products**
  1. CPP
  2. Affiliates list
- **1.2.7 Reliance**
  1. Sameness letter
  2. Unredacted AR
  3. RRA variation application
  4. Correspondence with the reference agency
  5. Changes since the first EMA/FDA MA
  6. Rejection or amendment reporting commitment
- **1.2.8 Composition**
  1. Certificate
  2. Specifications
  3. Calculations
  4. Pellets / premix
  5. Opadry / coating premix
  6. Capsule shell
  7. Synonyms evidence
- **1.2.9 Certificate of analysis**
- **1.2.10 Post-approval change**
  1. COO approval (imported)
  2. Summary of change
  3. Justification
  4. Other
- **1.2.11 Proof of payment**
- **1.2.12 Biologicals analysis**
  1. SOPs
  2. Summary protocol for vaccines and plasma products
- **1.2.13 Plasma-derived**
  1. PMF
  2. Plasma batch release certificate
  3. PMF approval in the country of origin
- **1.2.14 Scientific advice report**
- **1.2.15 PV**
  1. PSMF assessment or receipt e-mail
  2. PSMF/PSSF summary
  3. Latest PSUR (or ACO for renewal)
  4. EU/global RMP
  5. Egyptian display of the RMP
- **1.2.16 Inspection**
  1. SMF of all manufacturers
  2. Latest SRA full inspection reports (3 years)
  3. One executed BMR + BPR
  4. Recalls for quality defects (3 years)
  5. Warning letters (line-specific)
  6. Last APQR
  7. Cold-chain storage & transport with allowed excursions

**Note:** the draft eCTD M1 numbering (1.2.x) **differs** from the current CTD Module 1 numbering in NP.CAPP.065 (1.1.x administrative / 1.2.x technical). A tool must keep both maps.

---

## 9. ICH M4(R4) formatting and granularity (S8)

**Formatting**
- Five modules. Module 1 is regional. Do not modify the overall organisation. Formats inside the non-clinical and clinical summaries may be adapted.
- **Times New Roman 12 pt** recommended for narrative text.
- Margins must suit both **A4** and **US Letter**, with a wide left margin for binding.
- Every page is numbered according to the granularity document.
- Define acronyms at first use **in each module**.
- Cite references per **ICMJE** Uniform Requirements.

**Granularity**
- **Document = file.** In paper, a document is a set of sequentially numbered pages separated by a tab.
- Once a granularity is chosen, **keep it for the life of the dossier**, because replacements are whole documents.
- Module 2.3 (eCTD v3.2.2 / paper, Table 1):
  - one document at 2.3 Introduction;
  - the QOS at 2.3.S / 2.3.P level, or by section;
  - **one 2.3.S per drug substance**;
  - a diluent gets its own 2.3.P;
  - one 2.7.3 per indication.
- Module 3 (Table 2):
  - documents at the lowest numbered level (e.g. 3.2.S.1.1… 3.2.P.8.3);
  - P.2.x sub-headings are unlikely to be separate files;
  - control-strategy summaries may sit at 3.2.S.4 or 3.2.P.5;
  - multi-API products get a full S per API;
  - a diluent gets its own P;
  - **3.3 = one file per reference**;
  - 3.2.R follows regional guidance.

---

## 10. Worked examples and real templates (WHO, cited by EDA)

### 10.1 What a professional QOS (Module 2.3) looks like (S11 — WHO QOS-PD template, Jan 2025)

**Introduction**
- Product names, API with form (salt/hydrate/polymorph), applicant, dosage form, strengths, route, indications, contacts.
- **Pharmacopoeial status table** for the API and FPP: Ph. Int., USP plus Pharmacopeial Forum, Ph. Eur. plus Pharmeuropa, BP, JP, each with the edition consulted. Example entry: "USP 38 — monograph exists".

**2.3.S (per API and manufacturer)**
- An API-option box (PQ / CEP with commitment / APIMF with LoA and open/closed-part versions / full) and API-manufacturer declarations:
  - all S.2 information was given to the FPP maker;
  - the FPP maker will be informed of changes.
- **S.1.3:** a quantitative **pH 1.2–6.8 solubility profile at 37 °C** and a **dose/solubility volume** using the highest single dose per ICH M9.
- **S.3.2:**
  - API-related and process-related impurity tables (name, structure, origin);
  - **maximum daily dose → ICH reporting, identification and qualification thresholds**;
  - observed levels per batch with its use (BE, stability);
  - a **nitrosamine risk-assessment declaration**, with the RA expected in S.2.6, S.3.2 and S.4.5 when a risk is found.
- **S.4.1:** a table of Test, Acceptance criteria, Analytical procedure (type/source/version) with the standard and spec reference.
- **S.4.4:** batch number, size, date and site, and use.
- **S.7:**
  - a stress table (heat, humidity, oxidation, photolysis, acid, base) with mass balance and peak purity;
  - an accelerated and long-term table (condition, batch, size, container, intervals completed and proposed);
  - the storage statement and retest period;
  - three protocols: **primary batches**, **commitment batches (at least 3 production batches)** and **ongoing (at least 1 production batch per year per container)**.

**2.3.P**
- **P.1:** a unit composition table (component and standard and grade, function, quantity per unit and %) by core, coat and subtotals, plus the composition of purchased mixtures (colourants, coatings, shells, inks).
- **P.2.2.1:** a batch-number map (BE or biowaiver batch, dissolution, stability primary and production per pack, validation). A formulation comparison across BE, stability, validation and commercial batches (quantity per batch and %). Multipoint dissolution in **3 BCS media**. Scoring rationale.
- **P.3.2:** a batch formula for **every** commercial batch size with the master record reference.
- **P.3.4:** controls per step, and **validated hold times for intermediates and bulk**.
- **P.3.5:** validation protocol and report codes. Each API supplier is used in at least one validation batch. Dissolution of all primary batches (12 units) is compared with the BE batch.
- **P.5.1:** release **and** shelf-life limits.
- **P.5.5:** degradation products with (Q)SAR per M7; nitrosamine declaration; **Q3D declaration** (none > 30% PDE, or controls listed); residual-solvent declaration (Q3C option I).
- **P.7:** a pack table (description, strength, count, container size) and component specifications (HDPE bottle, PP cap, induction liner, blister films, aluminium foil).
- **P.8:** same structure as S.7, plus in-use, hold-time and transport studies, and bracketing/matrixing justification.

**2.3.R**
- The list of executed batch records.
- A **table of differences between the biobatch record and the proposed commercial master record** (process, equipment make/model/capacity, settings).
- **2.3.R.2:** an HPLC method summary and a validation summary for each method:
  - columns, mobile phase, detector, flow, injection volume, sample/reference/system-suitability concentrations as % of "A", SST criteria;
  - specificity, linearity (slope, intercept, r²), accuracy, repeatability, intermediate precision, LOD/LOQ, robustness, solution stability.

### 10.2 The assessor's screening checklist (S14 — WHO, May 2021)

These are checks a reviewer runs **before** assessment. All of them map onto EDA expectations.
- The cover letter says the data are **"true, complete and correct"**.
- A valid manufacturing licence or GMP certificate for the FPP.
- PQ-API, LoA or CEP present. **Check the CEP is the valid version on the EDQM site.**
- Full-route API from another group: declarations (a) all S.2 information given and (b) changes will be notified.
- QOS and QIS **as Word, in the latest template, unaltered**, with volume and page cross-references.
- Nitrosamine RA declared.
- BE: the BTIF in Word, AUC and Cmax data in Excel, comparator purchase, shipping and storage documents, and **a list of all BE studies, including failed and pilot studies**. A biowaiver form if one is claimed.
- Data for all FPP sites and, preferably, all API sources.
- The composition table filled with section titles and excipient standards.
- **Stability at submission: ≥ 6 months accelerated + ≥ 6 months long-term on ≥ 2 pilot-scale FPP batches (3 pilot batches of the API).** For uncomplicated FPPs, one pilot batch plus one smaller batch.
- Contract-manufacturing responsibilities defined.
- Technology-transfer validation.
- A prospective validation protocol or data for **3 consecutive production batches of the largest size**.
- Executed biobatch records and the blank master record.
- Analytical validation.
- Pilot and production batch sizes and composition.
- **The full site address including unit and block.**

**Sterile products (Part C):**
- media-fill results;
- container integrity (microbial or dye ingress);
- rubber stopper testing (USP <381>, <87>/<88>) and freedom from 2-MCBT and nitrosamines;
- transport simulation;
- blank and executed BMR with sterilisation, aseptic and IPC SOPs;
- filter validation (compatibility, extractables/leachables, bacterial retention);
- environmental grades and pressures;
- sterilisation and depyrogenation validation;
- **inverted-orientation stability** for rubber closures;
- hold times.

### 10.3 The numbers that decide a generic Module 3 (S10, WHO TRS 986 A6 — cited in S2)

- **Pilot scale** for solid orals: at least **1/10 of production or 100 000 units, whichever is larger**.
- **API retest period:** at least **3 batches of at least pilot scale**, same synthetic route.
- **API batch analysis with a CEP or APIMF:** 2 batches of at least pilot scale. S2 sets the same for the CEP route.
- **FPP batch analysis and shelf life:** at least **2 batches of at least pilot scale**. For an *uncomplicated* FPP (IR solid, non-sterile solution): 1 pilot batch + 1 smaller batch (e.g. **25 000 or 50 000 units**), for each strength. Use different API batches where possible. Test every strength, dosage form and container unless bracketing or matrixing is justified.
- **Extrapolation (ICH Q1E):** if there is no significant change at 6 months accelerated and little variability, the shelf life may be up to **2 × the long-term data, but not more than long-term + 12 months**.
- **Commitments:**
  - a signed, dated commitment to continue the primary batches;
  - **3 production batches of each strength per container**;
  - ongoing studies on **1 batch per year** per strength and container.
- **3.2.R.1.1:** a minimum of 2 batches per strength (or 1 + 1 smaller for an uncomplicated FPP). Executed records of the **BE or biowaiver batch**, with legible operator notations.
- **Reporting:** numeric results, not "conforms". Dissolution as the mean **and the range** of individual results. Sterility at the start and end of shelf life. Sub-visible particles periodically for parenterals.
- **Storage conditions:** refer to WHO TRS 953 Annex 2 (2009). S2 also cites the TRS 1010 Annex 10 (2018) stability guideline. **The long-term condition required for Egypt was not read in this session.** Take it from the EDA stability guidance (S5 and the Stability Submission Guide v02) before stating it.

### 10.4 Example — which items apply (illustrative, built only from S1 and S2)

**Example A — local generic, film-coated tablet, One Submission, new registration, API from 2 manufacturers (one CEP, one DMF).**
- **M1:**
  - 1.1.1–1.1.6, 1.1.8;
  - 1.1.9 proposed EN and AR SmPC and PIL in **Word** plus the latest reference;
  - 1.1.10 coloured stamped layout plus a monograph if compendial;
  - **1.1.11 inspection report for the pilot/production batches**;
  - **1.1.12 importation approval for each API**;
  - 1.1.17.1, 1.1.17.2, 1.1.17.6 if the store differs, 1.1.17.7 manufacturing and storage agreements;
  - 1.1.19 if pharmacopoeial;
  - **1.1.20 LoA for the DMF source**;
  - 1.2.1 composition with **core and coat separated, tablet weight, and the Opadry composition on supplier letterhead**, plus the salt-equivalence calculation;
  - 1.2.3.1 API CoA and 1.2.3.2 specifications;
  - 1.2.4.1 and 1.2.4.2 GMP for **both** API makers;
  - 1.2.4.3 the CEP with annexes **plus the CEP commitment letter**;
  - 1.2.5 reference or non-reference approval, and the reference leaflet.
  - **Not applicable:** 1.1.7 (re-registration only), 1.2.2.x (Rolling only), 1.1.13–1.1.16 (imported only, unless under-licence).
- **M2:** not required. **M4:** optional literature only.
- **M3:**
  - In 3.2.S, declare the option per manufacturer.
  - CEP maker: the CEP-route sections in §5.
  - DMF maker: the applicant's part.
  - Plus the applicant's control of the API.
- **M5:** 5.1, 5.2, **5.3.1.2 BE report**, **5.3.1.4 bioanalytical methods**, 5.3.3.1, 5.3.5.4, 5.3.7, 5.4. Also 5.3.2.1/5.3.2.2 if applicable.

**Example B — imported generic, hard capsule, re-registration.**
- **M1:**
  - 1.1.4 registration licence and preliminary approval;
  - **1.1.7 every variation approval in its own named sub-folder, in date order**;
  - 1.1.11 inspection report for a valid marketed batch;
  - **1.1.13 legalised CPP (or eCPP)** showing Egypt, marketed ≥ 1 year, with the shell composition;
  - 1.1.14 countries list;
  - 1.1.15 sameness letter;
  - 1.1.16 optional unredacted AR;
  - 1.1.17.2, 1.1.17.4 scientific office licence, 1.1.17.5 importers register;
  - 1.1.17.7 storage agreement legalised by chamber and embassy, and the agency agreement legalised;
  - 1.2.1 composition with **body and cap separated, capsule size, and the shell composition on supplier letterhead**.
- **M3:** in full.
- **M5:** partial, as in Example A.

---

## 11. Stability dossier — a separate file (S5, NP.CAPP.090 v2, 06/08/2026)

Submitted to the **General Administration for Stability**, not inside the CTD registration file. Columns: re-registration / registration licence or post-approval / variation.

**Regulatory documents folder**
1. Administrative:
   - registration licence and attachments;
   - preliminary re-registration approval;
   - (e)CPP or free sale with the SmPC or insert;
   - packaging-material supplier CoAs for all pack sizes.
2. EDA reports:
   - previous stability approvals;
   - variation approvals;
   - CAO report;
   - **CADC detailed final report**;
   - CADC renewal certificate;
   - P-part quality approval.
3. Applicant documents: a review of all changes, a review of stability-monitoring results, and the list of validated procedures with revalidation dates.
4. Applicant commitments: Annex II form. The API maker must be as in **3.2.S.2.1**.
5. Outsourcing:
   - the licence of the stability performer;
   - a legalised contract and product annex;
   - a microbiology-testing contract (2 options).
6. Fees, when shelf life, storage or in-use changes.

**Technical documents folder**
- Composition (Annex I).
- The brand leaflet or SmPC with shelf life, storage and in-use highlighted.

Other rows (data, protocols, batches) were not read row by row in this session.

---

## 12. What a CTD tool would need from this (notes for later)

1. **Two section maps:** today's CTD M1 (NP.CAPP.065 1.1.x/1.2.x) and the draft eCTD M1.2 (1.2.1–1.2.16). The ICH M2–M5 headings are common to both.
2. **Profile drivers** found in the sources:
   - innovator / imported generic / local generic;
   - new / re-registration;
   - One Submission / Rolling;
   - toll; under-licence; imported bulk; store separate from factory;
   - powder for injection with solvent; pharmacopoeial product; PIL-only; non-English leaflet; non-referenced; non-English reference;
   - API option per manufacturer (PQ / CEP / DMF / full);
   - dosage-form specifics (coated, capsule, pellets, premix, sterile).
3. **File checks** grounded in sources:
   - PDF searchable (S1 note 4);
   - eCTD-readiness: PDF ≥ 1.4, no encryption, name ≤ 64, path ≤ 180, no illegal characters, no portfolio (S6 draft).
4. **Quality gates** from S3, S10 and S14:
   - ≥ 2 batches;
   - numeric results;
   - dissolution Q;
   - general-chapter reference column;
   - concomitant IR of the standards;
   - Q3D, M7, nitrosamine and benzene risk assessments;
   - photostability and in-use studies;
   - commitment letters;
   - hold times;
   - process validation on 3 batches;
   - executed BE-batch records;
   - CEP authorisation box signed;
   - CPP–dossier site consistency.
5. **Generated documents** whose fields are fixed by sources:
   - Annex I application form (S1);
   - CEP commitment (S2);
   - stability commitments (S10 / S3);
   - leaflet translation declaration (S1);
   - tracking table (S6);
   - module TOCs (S8).
6. **Not yet available — do not invent:** the EG M1 eCTD specification and `eg-regional.xml`, the EG validation criteria and accepted-formats list. Check the EDA eCTD webpage before any eCTD XML work.
