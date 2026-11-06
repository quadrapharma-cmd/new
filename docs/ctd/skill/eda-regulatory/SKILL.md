---
name: "eda-regulatory"
description: Answer Egyptian Drug Authority (EDA) and related regulatory questions from the live authority sources, not memory, then turn the finding into a bilingual deliverable — position memo, reply letter, requirements checklist, or waiver argument. Use for registration, variations, renewals, CTD/eCTD dossiers, pricing, free sale, stability, EDA letters or comments, tracking IDs, decrees and guideline editions, cosmetic notification, NFSA supplements, and export markets (SFDA, MOHAP, Dubai Municipality, JFDA). Use equally for GMP inspection work — observations to answer, CAPA replies to EDA, which WHO/PIC/S/ICH/ISO or pharmacopoeia edition applies, water systems, validation, data integrity, site master file, technical operating licence or change of site/production/QC manager — and for EDA-vs-EMA/FDA/WHO comparisons or reliance-route arguments. Trigger even when EDA is not named ('do we need a BE study', 'what do they want for the site transfer', 'reply to this inspection report'); stale answers get files rejected.
---

# EDA & Corresponding Authorities — Regulatory Navigator

Regulatory answers fail in two ways: they are confidently out of date, or they are correct but unusable because they never become the document that actually gets filed. This skill closes both gaps — verify against the live source, then produce the deliverable.

## The non-negotiable rule

**Never state an EDA requirement from memory.** EDA revises guidelines and issues Chairman decrees continuously; the Variation Guidelines are already in their 6th Edition and were re-categorized to align with EMA. A requirement recalled from training data is a plausible-sounding guess, and in this domain a plausible-sounding guess gets a file rejected or a deadline missed.

Every substantive requirement must be traced to a fetched source with its **edition/version, decree number, and date**. If it cannot be traced, say so explicitly rather than filling the gap — see *Handling what you cannot find*.

## Workflow

### 1. Classify before searching

Identify three things from the request. Ask only if genuinely ambiguous; usually they are inferable.

- **Product class** — human pharmaceutical, biological/innovative, herbal, cosmetic, biocide, medical device, veterinary, food/supplement (NFSA, not EDA).
- **Action** — new registration, variation (and its type), renewal, pricing, import/export release, free sale certificate, establishment licensing, inspection/GMP, pharmacovigilance, advertising, recall.
- **Jurisdiction** — Egypt domestic, export market, or a reference authority being invoked for comparison or reliance.

Product class + action determine which of EDA's nine Central Administrations owns the answer. Route with `references/eda-site-map.md`, which maps administrations to their guideline pages and lists the known-unstable URLs.

### 2. Locate the source

Work down this ladder, stopping when you have the authoritative text:

1. **Regulatory Guidelines** — the technical/scientific requirements, per administration.
2. **Notice to Applicant** — a separate tree from Guidelines, and the one people most often miss. It carries the procedural submission requirements: what to attach, in what order, to whom.
3. **EDA Chairman Decrees** — the binding instrument. When a guideline and a decree conflict, the decree governs; cite it by number and year (e.g. Decree 450/2023).
4. **Committees' Decisions, Guidance, Forms, Periodic Lists** — for committee-level rulings, official forms, and status lists.
5. **e-services / databases** — to verify a product's actual registration record, number, and status.

Search the site with `site:edaegypt.gov.eg <topic>` when the navigation path is unclear, and fetch the PDF itself rather than relying on a search snippet — snippets routinely truncate the conditions and exemptions that decide the case.

**Expect the English and Arabic trees to diverge.** Slugs differ, some English pages redirect into Arabic, and legacy paths survive in places. The Arabic tree is sometimes the more current of the two. If an English page looks thin, stale, or 404s, check the Arabic equivalent before concluding the guidance does not exist.

### 3. Verify what you fetched

Before using a document, confirm:

- **Edition/version** — is this the current one? A 5th Edition answer is wrong once the 6th is published.
- **Effective date and supersession** — what it replaced, and whether transitional provisions apply to files already in flight.
- **Scope** — does it actually cover this product class and dosage form? Guidelines often carve out solutions, reconstitutable powders, or topicals.
- **Exemptions** — the exemption clause is usually where the useful argument lives.

### 3b. For GMP and inspection questions, use the adopted-standards ladder

Registration and inspection run on different source trees. A GMP question answered from the
registration guidelines, or from EU GMP alone, is answered against the wrong document.

Since 2026 EDA's inspection administration (CIP) publishes **three adoption notices**, and they —
not recall, not EudraLex — decide which reference governs:

- **NP.CIP.001/2026, Version 04 (07/2026)** — Adopted List of WHO Norms and Standards. Replaces
  NP.CAO.004/2023 v2/2024. States that an alternative approach is acceptable only on objective
  evidence and a documented risk assessment, with the burden on the establishment.
- **NP.CIP.003/2026, Version 02 (11/06/2026)** — **Adoption of the PIC/S GMP Guide** (lists
  PE 009-17). EDA "will closely monitor compliance" during factory inspections.
- **NP.CIP.002, Version 3/2026 (05/2026)** — **Adoption of ICH Q1–Q14** as binding technical
  references.

The ladder for any GMP question:

1. **Egyptian law, decrees and EDA guidelines** on the point (GSDP, managers, sampling, recall).
2. **WHO TRS 986 Annex 2** (verified in `references/gmp-core.md`) plus the **topic annex** from
   the v04 list (full table in `references/gmp-standards.md`).
3. **PIC/S PE 009** — now EDA-adopted, citable in its own right. EDA names **-17**; PIC/S moved to
   **-18 on 24/09/2026** (Annex 19 only).
4. **ICH** — adopted; always with the revision suffix. The consolidated Q1 is still a draft.
   PIC/S **PI** documents (e.g. **PI 006-4 qualification & validation, in force 01/10/2026**; PI 040-1
   deficiency classification; PI 009-4 utilities; PI 023-2 QC labs) are inspector guidance — not
   covered by EDA's adoption notice, but they show how the inspection will be run.
5. **The pharmacopoeia in the registration file**, with edition/issue.
6. **EudraLex, MHRA, FDA, ISPE, ISO** — supporting only. EU GMP was *not* adopted.

ISO is not what EDA inspects against. A GMP document whose only reference is ISO 9001 is a
quality-management document wearing a GMP label. And ISO 9001 and 14001 were both reissued in
2026 — a list still showing the 2015 editions as current is stale on its face.

For water systems go straight to `references/water-systems.md` — TRS 1033 Annex 3 verified clause
by clause; its §15.2 makes the annex the basis of the inspection tour.

Two checks that repeatedly catch errors: confirm the **annex and year** against the **v04** list
(v04 dropped 885 A5, 961 A6, 961 A7 and the 2015 HVAC text, and added 1052/1060/1067 texts), and
run the eight currency checks at the end of `references/reference-catalogue.md`. Citing a
superseded guideline in a reply to an inspection finding produces the finding again.

### 3c. For CTD / dossier-building questions, open `references/ctd-dossier.md` first

It holds, verified 06/11/2026:
- **NP.CAPP.065 v5 (01/11/2025)**: the Module 1–5 requirement matrix for innovator / imported generic / local generic, with every M1 condition (toll, under-licence, imported bulk, One Submission vs Rolling) and the Annex I application-form fields.
- **The EDA CTD Quality Module guideline v2 (12/03/2023)**: the four S-part options, what a CEP does *not* cover, and the 3.2.R contents.
- **NP.CAPP.040**: the common Module 3 deficiencies, used as a pre-submission check.
- **NP.CAPP.112 v1 (07/2026)**: variation type → CTD sections.
- **The draft eCTD technical guidance (v1/2026, not in force)**: naming ≤ 64, path ≤ 180, PDF 1.4–1.7, UUID, sequences, EG submission types, EG M1.2 tree.
- **ICH M4(R4) granularity.**
- **WHO QOS-PD/QIS templates, the WHO screening checklist and TRS 986 A6**: batch and stability numbers.

Two facts that change how a file is built:
- **One Submission has been mandatory for locally registered human products since 01/11/2025.** Items marked "Rolling" in NP.CAPP.065 (CADC certificate, stability, BE and Technical Affairs approvals, approved leaflet and layout) do not apply to it. It needs the proposed EN+AR SmPC/PIL **in Word** and the coloured stamped layout.
- **Generics file no Module 2** ("incorporated in Modules 3, 4 & 5"). Module 4 is optional (literature). Module 5 is partial: BE, bioanalytical methods, healthy-subject PK, other reports, CRFs, literature.

The EG Module 1 eCTD specification (`eg-regional.xml`), the EG validation criteria and the accepted-formats list were **not published** when checked. Do not generate eCTD regional XML from memory.

### 4. Bring in corresponding authorities where they carry weight

EDA has deliberately aligned with EMA and WHO to support its Reliance Evaluation Route, which makes reference-authority positions genuinely persuasive in an Egyptian file rather than merely interesting. Use `references/authorities.md` for entry points and what each body is good for.

Invoke a comparator when it does real work:

- **Reliance route** — an approval or assessment from a reference authority can reduce the Egyptian evaluation burden.
- **Waiver or objection arguments** — strongest when built on EDA's *own* guideline exemption first, with EMA/WHO/FDA cited as corroboration. An argument resting only on foreign practice is weak; an argument resting on EDA's own text and echoed by EMA is hard to refuse.
- **Export filings** — SFDA, UAE, and JFDA each have their own dossier and CPP expectations; do not assume the Egyptian pack transfers unchanged.

Never present a foreign requirement as though it were an Egyptian one. Label every requirement with the authority that imposes it.

### 5. Produce the deliverable

Lookup alone is half the job. Unless the user only wanted a fact, carry the finding into the artifact they will actually use. Pick the form that fits:

- **Regulatory position memo** — for a decision: what applies, what it requires, options, recommendation.
- **Submission or reply letter** — for correspondence with an authority, including replies to EDA comments and waiver requests.
- **Requirements checklist** — for assembling a file: every item, its source, and its status.
- **Comparative table** — when the question is genuinely EDA-versus-others.

Templates are in `references/deliverable-templates.md`.

**If the deliverable is a controlled GMP document** on company letterhead — protocol, deviation, destruction record, validation/calibration protocol, SOP — hand off to the `cetreva-gmp-doc` skill instead of rebuilding that format here. This skill supplies the regulatory basis and citations; that one supplies the controlled-document shell.

## Output conventions

**Bilingual by default: English and Arabic.** English is the working language of the dossier; formal Arabic is what goes to EDA in correspondence. Produce both unless the user asks for one.

- Structure bilingual output so each section is complete in both languages — a side-by-side table for short content, sequential EN then AR blocks for prose. Do not interleave sentence-by-sentence; nobody can file that.
- Arabic addressed to an authority uses formal register and the correct administration name and title. Arabic for internal use can follow the user's Egyptian-Arabic working style.
- Keep drug names, INNs, registration numbers, decree numbers, and pharmacopoeial terms in their original form in both versions. Do not translate a product name into Arabic.
- Dates as DD/MM/YYYY, matching Egyptian convention.

Lead with the answer and its citation. Keep caveats short and at the end — a regulatory reader wants the requirement first, not three paragraphs of throat-clearing.

## Citation format

Cite so the user can hand the reference to a colleague and have them find it.

**Use the EDREX code whenever the document carries one.** EDA guidelines and notices are coded on their cover page in the form `EDREX: GL.CAPP.024` (Guideline, Central Administration of Pharmaceutical Products, document 024) or `EDREX: NP.CAPP.104` (Notice to Applicant), with a version/year. The code survives re-uploads and re-slugging, so it is the most stable identifier available — far more durable than a media URL.

> Egyptian Guideline for Conducting Bioequivalence Studies for Marketing Authorization of Generic Products — EDREX: GL.CAPP.024, Version 3/2023, Section X.Y [URL]

For decrees: `EDA Chairman Decree No. 450/2023, Article X`. For a comparator: `EMA Guideline on [title], Section X` — always with the authority named.

Always give version/year alongside the code. Two documents can share an EDREX code across versions, and the version is what determines whether the requirement you are citing is still the operative one.

## Handling what you cannot find

Regulatory gaps are normal and stating one plainly is far more useful than inventing a requirement. When the site does not answer the question:

1. Say what you searched and where.
2. Give the closest applicable provision, clearly labelled as adjacent rather than directly on point.
3. Name who to ask — the specific administration — and suggest the mechanism (formal enquiry, pre-submission meeting).

Distinguish sharply between "the guideline is silent" (an argument can be built) and "I could not locate the guideline" (more searching needed). These lead to opposite actions, so never blur them.

## Traps worth knowing

- **Guidelines vs. Notice to Applicant** — technical requirements and procedural requirements live in different trees. Answering from only one produces a file that is scientifically complete and procedurally rejected.
- **Decrees override guidelines** and often post-date them. A guideline can be current and still superseded on a specific point.
- **Edition drift** — always confirm the edition number; re-categorization between editions changes a variation's type, and with it the fees, timeline, and documentation.
- **Class determines authority** — a product with a cosmetic claim, a drug claim, or a supplement claim goes to three different bodies with different limits. Concentration ceilings frequently make an intended class unworkable; check the limit before assuming the pathway.
- **Fees and timelines change independently** of technical guidance — verify separately, and note that fee schedules are often Arabic-only.
- **A registration number is not a status.** Verify against the e-services database rather than assuming a file is live.
- **Inspection and licensing are different desks.** GMP inspection sits with the Central Administration of Inspection on Pharmaceutical Institutions (CIP); the technical operating licence sits with the General Administration of Factories Licensing (CALI). The licence now has a **7-year validity** (GL.CALI.007 v01/2026) — renewal must be filed at least 6 months before expiry. Correspondence with one does not reach the other, and a licence amendment does not answer an inspection finding.
- **The licence is a live document, not a certificate.** It names the registered site, production and QC managers with syndicate numbers. When one of them leaves, the change must be notified — a clearance request is due **within 48 hours**; if the factory manager leaves, the registered production manager acts for a **maximum of three calendar months** before the site must be closed administratively; if the production or QC manager leaves, the factory manager covers for three months, after which **EDA suspends circulation** of the factory's products (GL.CALI.005 v2/2025). A quality system that names people the licence does not is the first contradiction an inspector finds.
- **الشخص المفوّض إليه is the legal representative, not a technical role.** They appear on the licence without a syndicate number and do not certify batches. Putting them in a batch-release procedure is an error; so is leaving the actual releaser undefined.

## Reference files

- `references/document-register.md` — **check here first.** Catalogue of EDA documents with EDREX codes, versions, and verified clauses, plus a **live-index snapshot (29/09/2026)** of current versions across CAPP, Stability, CADC and CIP/CALI (e.g. BE guideline **v04 06/2026**, Variations **6th ed. 12/2025**, site-transfer guideline **v03 03/2026**, CADC file assessment **v2 05/2024**). Each entry is marked VERIFIED (read in full), INDEXED (seen in a search result only), or SUPERSEDED? Only VERIFIED entries may be cited directly; INDEXED entries are leads to be opened and confirmed. Add to it whenever you open a new document.
- `references/eda-site-map.md` — EDA structure, the nine Central Administrations, guideline and Notice-to-Applicant entry points, the EDREX coding scheme, e-services, and the specific URL inconsistencies to expect.
- `references/authorities.md` — NFSA, SFDA, UAE MOHAP/Dubai Municipality, JFDA, EMA, FDA, WHO: what each governs, entry points, and how each is properly used in an Egyptian argument.
- `references/licensing.md` — **adding or modifying a production line**: GL.CALI.001 v2/2025 and NP.CALI.001 v2/2026 verified — layout review, two-sheet layout rules, IDA joint inspection, timelines, per-line fee. Open before any licensing, layout-committee or new-line question.
- `references/gmp-standards.md` — **the GMP layer, re-verified 29/09/2026.** The three CIP adoption notices (WHO list **NP.CIP.001/2026 v04**, PIC/S **NP.CIP.003/2026**, ICH **NP.CIP.002 v3/2026**); the full v04 WHO table and what changed from v2/2024; supersession traps; TRS 1033 Annex 4 (data integrity) verified clause-by-clause; **key clauses of TRS 996 A4 (inspection report and deficiency classification), 961 A14 (SMF), 1010 A8 + 1019 A2 (HVAC), 1019 A3 (validation) and 1052 A4 (QC labs)**; the verified licensing instruments (managers GL.CALI.005 — 48-hour clearance and 3-month acting rule; licence renewal GL.CALI.007 — 7-year validity; GSDP GL.CIP.005). Open this before any inspection, GMP, utilities, validation, licensing or data-integrity question.
- `references/reference-catalogue.md` — **everything outside the WHO list, currency-swept 29/09/2026.** PIC/S PE 009 (EDA-adopted -17; PIC/S current **-18, 24/09/2026**) with chapter/annex map and PI series; EudraLex Vol. 4 with the status of Annex 19 (revised 23/06/2026) and the **draft** Chapter 4 / Annex 11 / Annex 22; ICH table with current revisions and draft status; pharmacopoeias with current editions (**Egyptian Ph. 5th ed.**, **Ph. Eur. 12.x → 13.1 on 01/01/2027**, **BP 2026 → 2027 on 01/01/2027**, **USP–NF 2026 Issue 5**); **ISO** with the 2026 editions of 9001 and 14001; industry standards; Egyptian instruments; and **eight currency checks to run before citing anything**.
- `references/gmp-core.md` — **WHO TRS 986 Annex 2 (2014), verified clause by clause.** The primary GMP guideline in Egypt. Key personnel and their qualifications (§9.6–9.7), the authorized person and the ten release checks (§9.11–9.15), the whole documentation chapter including retention at expiry plus one year (§15.8) and the mandatory SOP list (§15.31), product quality review with no batch threshold (§1.10), qualification and validation (§4), self-inspection's fifteen items (§8.2), equipment (§13), production (§16), and a table of the clauses that most often go unmet. Open this for any GMP question before anything else.
- `references/water-systems.md` — **WHO TRS 1033 Annex 3 (2021), verified clause by clause.** Design and construction (§7.2.1 — orbital welding documentation, threaded joints prohibited, passivation, spray-ball test, inline TOC), chemical sanitization and proven agent removal (§8.4), the three-phase qualification with its 12-month total (§11.3), monitoring and trending (§12), the annual review team and its thirteen items (§14), and a 21-point checklist for reading a P&ID against the annex. Open this for any water, utility or qualification question.
- `references/ctd-dossier.md` — **CTD dossier building (verified 06/11/2026).** NP.CAPP.065 v5 M1–M5 matrix and Annex I form; CTD Quality guideline v2/2023 (S-part options, CEP gaps, 3.2.R); NP.CAPP.040 deficiencies; NP.CAPP.112 variation→sections; draft eCTD guidance 2026 (file rules, EG M1.2 tree, submission types); ICH M4(R4) granularity; WHO QOS-PD/QIS/screening checklist/TRS 986 A6 numbers; worked examples; list of what is still unpublished.
- `references/deliverable-templates.md` — bilingual templates for the memo, letter, checklist, and comparative table.

A search snippet is not a source. Snippets truncate exactly the conditions, applicability limits, and footnotes that decide a case — and the same document often exists in several versions at different URLs, so an indexed hit may be a superseded edition. Open the document, read the clause and its footnotes, confirm the version on the cover page, then cite. If you report a finding without having opened the document, say so plainly.
