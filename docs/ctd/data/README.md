# EDA Variation Self-Guided Tool — snapshot 06/11/2026

**Source:** EDA's official tool `https://eservices.edaegypt.gov.eg/EDAVariationTool/` (footer «Version 1.0, Copyright © 2026 EDA (PIS)»). It was first announced 14/09/2023. Captured by direct postbacks to the page's search and paging, without changing any text.

| Section | Rows | Notes |
|---|---|---|
| Human | **90** (ID 1–90, complete) | PAC-N 38 · PAC-A 20 · PAC-B 18 · PAC-II 14 |
| Herbal | 58 (ID 1–58, complete) | PAC-N 30 · PAC-B 15 · PAC-II 8 · PAC-A 5 |
| Veterinary | 52 of IDs 1–64 (**12 missing**) | **The column layout differs**, so the procedure-type column holds conditions text. Re-check before use |
| Medical devices | — | Not captured: the page has no search |

**CSV columns:** Section, ID, Main group (Drug Substance / Drug Product), Variation type (14 groups, e.g. Manufacturing site, Formulation, Container closure system), Variation request, Procedure type (PAC), Conditions to be fulfilled, Requirements to be fulfilled.

**What the site has but the CSV doesn't:** the submission link, the time frame/workflow and the submission guidance for each row are buttons that open links, and their URLs were not captured.

**Spot check against Variations Guidelines v6 (GL.CAPP.026):** two items match.
- A new manufacturer of the active substance is **PAC-II** in both (v6 §3.2.1, «Addition or Replacement of a new manufacturer»).
- Increase or reduction in the flavouring/colouring system is **PAC-B** in both (v6 §3.2.2.3 a-2).

The tool appears to reflect the 6th edition, but **it was not compared row by row**.

**Use for the tool:** this is a ready-made reference table. For each variation it gives the PAC class, the conditions and the requirements. Combined with NP.CAPP.112, which says which CTD sections to update, it can drive building a variation file automatically.
