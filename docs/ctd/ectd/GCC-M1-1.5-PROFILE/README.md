# GCC Module 1 v1.5 — the profile the Gulf eCTD is written on (updates list, item 39)

**Source:** GCC Module 1 Specifications v1.5, Saudi Food & Drug Authority, November 2015
(`docs/ctd/sources/ectd/SFDA_GCC_Module1_Specifications_v1.5_2015.pdf`, from `www.sfda.gov.sa`, taken 13/11/2026).

| File | From |
|---|---|
| `util/dtd/gc-regional.dtd`, `gc-envelope.mod`, `gc-leaf.mod` | Appendix 6 «Modularized DTD for GCC Module 1» (DTD 1.1, envelope 1.2), as the specification prints it — page footers taken out, nothing else changed. They parse (58 elements) and the writer's output is valid against them. The specification gives the official files' checksums for v1.4; compare with SFDA's own files when available, and keep SFDA's. |
| `util/dtd/ich-ectd-3-2.dtd`, `util/style/ectd-2-0.xsl` | ICH (the same files as the other profiles) |
| `m1.csv` | Appendix 2 «Directory / file structure»: each heading's DTD element, folder and file name. Where Appendix 2 names an element differently from the DTD (m1-2-application-form / m1-2-form, m1-3-product-information / m1-3-pi, m1-6-pharmacovigilance-system / m1-6-1-pharmacovigilance-system) the DTD's name is used — it is what a validator reads. |

**What the writer applies** (`engine/dossier_engine/writers/ectd32_gcc.py`): the envelope of Appendix 1 with the codes of Appendix 5
(one envelope per Gulf state, each with its receiving agency: SA-SFDA, AE-MOH, KW-MOH, BH-MOH, OM-MOH, QA-NHA, YE-MOPHP); 1.0, 1.2,
1.3.4, 1.3.5, 1.9 and additional data under `specific/@country`; 1.3.1–1.3.3 under `pi-doc` (language en|ar, type spc|label|pil);
«CC» in a name is the state's code or `common` (a document for every GCC state).

**What the validator checks** (`engine/dossier_engine/validators/ectd32_gcc.py`): the specification publishes no list of validation
criteria, so the checks are what its texts and the ICH specification decide — both backbones valid against their DTDs, every
leaf's file there with its MD5, index-md5.txt, names and paths within the ICH limits, one envelope per state with its agency, no
country section without an envelope.

**Not here:** the GCC stylesheet (`gc-regional.xsl`, only its checksum is printed) and a newer SFDA eCTD specification (version 2.x,
2025, reported by secondary sources — not read here). When SFDA's current text is read, this profile is replaced, not edited.
