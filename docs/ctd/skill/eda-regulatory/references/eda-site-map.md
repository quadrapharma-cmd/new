# EDA Site Map & Navigation

Structure verified August 2026; guideline and NtA indexes re-read 29/09/2026 (CIP adoption notices now coded NP.CIP.00x; licensing coded GL.CALI / NP.CALI). **Treat every path below as a starting point, not a guarantee** — EDA re-slugs pages without notice. If a URL fails, navigate from the section index rather than guessing a replacement.

## Contents

1. Domain and URL conventions
2. The nine Central Administrations — routing table
3. Regulatory Guidelines tree
4. Notice to Applicant tree
5. Decrees, laws, and committee decisions
6. Databases, e-services, forms
7. Pharmacopoeia, formulary, monographs
8. Safety: recalls and alerts
9. Known URL inconsistencies

---

## 1. Domain and URL conventions

- Primary: `https://edaegypt.gov.eg/en/...` — `www.` also resolves; both appear in official links.
- Arabic mirror: `https://edaegypt.gov.eg/ar/...` with percent-encoded Arabic slugs.
- PDFs: `https://edaegypt.gov.eg/media/<hash>/<filename>.pdf`. The hash is opaque and changes when a document is re-uploaded, so **never construct a media URL** — always follow a link from a live page.
- Switch language by using the En/Ar toggle links on the page itself; the paths are not mechanical translations of each other.

## 2. The nine Central Administrations — routing table

| # | Central Administration | Owns |
|---|---|---|
| 1 | Pharmaceutical Policies & Market Access | Pricing, export support, investment promotion, importation and customs release |
| 2 | Biological, Innovative Products & Clinical Studies | Biologicals, biosimilars, vaccines, clinical trials |
| 3 | Pharmaceutical Products | Human pharma registration, variations, BA/BE, naming & mock-up, herbal, cosmetics, biocides, veterinary |
| 4 | Medical Devices | Device registration and market authorization |
| 5 | Pharmaceutical Care | Pharmacovigilance, leaflets/references, advertising & marketing materials, drug utilization |
| 6 | Inspection of Pharmaceutical Institutions | GMP inspection, GCP, GDP, establishment inspection |
| 7 | Drug Control | Laboratory testing, quality control, sample analysis (CADC) |
| 8 | Pharmaceutical Institutions Licensing | Factory, warehouse, pharmacy licensing |
| 9 | EDA Chairman's Office | Cross-cutting and chairman-level guidance |

Most Quadra/Medsinia/CETREVA work lands in **3** (registration/variation), **6** (GMP/inspection), **7** (sample failures, CADC notifications), **1** (pricing, export, free sale), and **8** (site licensing).

## 3. Regulatory Guidelines tree

Index: `/en/the-regulatory-reference-of-the-egyptian-drug-authority-eda/regulatory-guidelines/`

English nav slugs, all prefixed with the index path above:

- `ca-of-pharmaceutical-policies-and-market-access/`
- `ca-of-eda-s-chairman-office/`
- `ca-of-biological-innovation-products-and-clinical-studies/`
- `ca-of-pharmaceutical-products/`
- `ca-of-medical-device/`
- `ca-of-pharmaceutical-care/`
- `ca-of-inspection-of-pharmaceutical-institutions/`
- `ca-of-drug-control/`
- `ca-of-pharmaceutical-institutions-licensing/`

Under **CA of Pharmaceutical Products**, guidelines are grouped by General Administration:

- G.A. of Pharmaceutical Products Registration — registration of human pharmaceutical products; variation of human pharmaceutical products; bioavailability & bioequivalence studies; naming and mock-up.
- G.A. for Herbal Medicinal Products Registration
- G.A. for Cosmetic Products Registration
- G.A. of Biocides Registration
- G.A. of Veterinary Pharmaceuticals

Under **CA of Pharmaceutical Care**: marketing & advertising materials; pharmaceutical references and leaflets; pharmacovigilance; drug utilization and pharmacy practice.

Under **CA of Pharmaceutical Policies and Market Access**: export support and investment promotion; importation and customs release.

**Key documents to expect** (fetch current versions; do not cite editions from memory):

- Guidelines for the Management of Variations for Human Products — **6th Edition**, re-categorized to align with EMA to support the Reliance Evaluation Route. Confirm the edition is still current before citing.
- Guideline on Dossier Requirement of Human Pharmaceutical Product — CTD organization for the Egyptian file; references Chairman Decrees including 150/2022 and 450/2023.
- Guideline for Bioavailability and Bioequivalence Studies — contains the exemption clauses that matter for solutions and reconstitutable powders.

### The EDREX document code

EDA documents carry a code on the cover page — the most stable identifier available, since it survives re-uploads and slug changes:

`EDREX: <TYPE>.<ADMIN>.<NUMBER>`, plus **Version No. / year** and issue date.

- `GL` = Guideline, `NP` = Notice to Applicant
- `CAPP` = Central Administration of Pharmaceutical Products

Confirmed examples:

| Code | Document | Version |
|---|---|---|
| GL.CAPP.024 | Egyptian Guideline for Conducting Bioequivalence Studies for MA of Generic Products | 3/2023 |
| GL.CAPP.001 | Regulatory Guidelines for Centers Performing BA/BE Studies | 1/2015 |
| NP.CAPP.104 | Notice to Applicant — Guidance for In-Vitro Studies Submission (imported/local human pharmaceutical products) | 1/2025 |

Record the code and version whenever you open a document, and cite both. Searching the code itself is often the fastest way back to a document whose URL has moved.

## 4. Notice to Applicant tree

Index: `/en/the-regulatory-reference-of-the-egyptian-drug-authority-eda/notice-to-applicant/`

A **separate tree from Regulatory Guidelines**, carrying procedural submission requirements. Sub-pages exist for Policies & Market Access, Biological & Innovative Products, Pharmaceutical Products, Medical Devices, Pharmaceutical Care, Inspection of Pharmaceutical Establishments, and Pharmaceutical Institutions Licensing.

Check this tree whenever the question involves *how to submit* rather than *what the science requires*.

## 5. Decrees, laws, and committee decisions

- `/en/the-regulatory-reference-of-the-egyptian-drug-authority-eda/eda-chairman-decree/` — binding instruments; override guidelines on conflict.
- `/en/the-regulatory-reference-of-the-egyptian-drug-authority-eda/laws-and-executive-regulations/` — the establishing law and executive regulations.
- `.../committees-decisions/` — committee-level rulings.
- `.../guidance/` — general guidance.
- `.../egypt-s-national-drug-policy/` — policy framing; useful for advocacy and position papers, not for file requirements.

## 6. Databases, e-services, forms

- Registered drug search: `http://eservices.edaegypt.gov.eg/EDASearch/SearchRegDrugs.aspx` — verify registration number and status here.
- `/en/services/databases/` and `/en/services/quick-links/`
- `/en/services/track-and-trace/` — serialization and track-and-trace.
- `/en/publications-reports-and-eda-in-numbers/eda-publications/forms/` — official forms.
- `.../periodic-lists/` and `.../eda-faqs/`
- Public Assessment Reports (approved and refused) under Regulatory Reports — useful precedent for what EDA accepted or rejected.

## 7. Pharmacopoeia, formulary, monographs

- Egyptian Pharmacopoeia: `/en/egyptian-pharmacopoeia/`
- Egyptian Drug Formulary: `/en/the-regulatory-reference-of-the-egyptian-drug-authority-eda/the-egyptian-drug-formulary/` — chapter-by-chapter, including the National Antimicrobial Formulary.
- Monographs: `/en/publications-reports-and-eda-in-numbers/eda-publications/monograph/`

## 8. Safety: recalls and alerts

- `/en/awareness/recalls-alerts-and-awareness-letters/` — recall/alert notice letters and awareness letters, organized by year.
- `/en/awareness/who-alert/` — WHO alerts as adopted by EDA.

## 9. Known URL inconsistencies

The guidelines index page and the site navigation disagree. Observed:

- **CA of Pharmaceutical Products (#3), Inspection (#6), Drug Control (#7), Institutions Licensing (#8)** — the index links to **Arabic** URLs while the nav offers English slugs. The Arabic pages are sometimes more complete.
- **Pharmaceutical Care (#5)** — the index links to a legacy path under `/en/laws-decrees-regulatory-guidelines-and-notices/...`, an older tree that still resolves.
- **Biological & Innovative (#2)** — index slug `regulatory-guide-line-for-central-administration-for-biological-innovation-products-and-clinical-studies/` differs from the nav slug `ca-of-biological-innovation-products-and-clinical-studies/`.
- **Chairman's Office (#9)** — slug contains a typo: `central-adminstration-of-ceo/`.

Practical consequences:

1. A 404 means the slug moved, not that the guidance was withdrawn. Re-navigate from the index.
2. When the English page looks thin or outdated, **check the Arabic page before concluding anything**.
3. `site:edaegypt.gov.eg <topic>` is often faster than clicking through, but open the actual document — do not cite from a snippet.
