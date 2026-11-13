# US Module 1 — what is here, and what is still missing (updates list, item 39)

**Here (taken 13/11/2026 from fda.gov — US government works, public):**

| File | What it is |
|---|---|
| `docs/ctd/sources/ectd/FDA_eCTD_Backbone_Module1_Specification_v2.6.pdf` | The eCTD Backbone Files Specification for Module 1, v2.6 (SHA-256 `1adcbc40…87f2`) |
| `docs/ctd/sources/ectd/FDA_Specifications_eCTD_Validation_Criteria.pdf` | FDA Specifications for eCTD Validation Criteria |
| `docs/ctd/sources/ectd/FDA_Comprehensive_TOC_Headings_Hierarchy.pdf` | Comprehensive Table of Contents Headings and Hierarchy |
| `docs/ctd/sources/ectd/FDA_eCTD_Technical_Conformance_Guide.pdf` | eCTD Technical Conformance Guide |
| `docs/ctd/sources/ectd/FDA_Example_Submissions_Module1.pdf` | Example submissions using the Module 1 specification |
| `us-regional-v3-3.dtd` (this folder) | The us-regional DTD 3.3, **rebuilt from Appendix 1 of the Module 1 specification v2.6** (the text the FDA prints there), with the page headers taken out and the words the PDF split across lines joined again. It parses (174 elements). SHA-256 `2488d13b…b586`. Compare it with the FDA's own `us-regional-v3-3.dtd` when `www.accessdata.fda.gov` is reachable, and keep the FDA's. |

**Missing — and why the US eCTD is not written yet:** the coded values the us-regional.xml must carry (application type,
submission type and sub-type, contact and telephone types, form types…) are kept by the FDA in separate files
(`application-type.xml`, `submission-type.xml`, `submission-sub-type.xml`, `applicant-contact-type.xml`,
`telephone-number-type.xml`, `form-type.xml`, …) on `www.accessdata.fda.gov/static/eCTD/`, which this environment cannot reach.
The specification shows codes in its examples (fdaat1, fdast1, fdasst4 …) but not their full lists or meanings; a writer built on
guessed meanings would file wrong codes. With the lists, the US writer follows the EU one: the admin block (D-U-N-S® id, company,
contacts, application and submission information), the m1-regional headings of the DTD, the study tagging files
(`engine/dossier_engine/writers/stf.py`, required by the FDA), and the FDA validation criteria.

The Gulf (SFDA, `www.sfda.gov.sa`) and Jordan (JFDA, `www.jfda.jo`) Module 1 specifications are not reachable from here either.
