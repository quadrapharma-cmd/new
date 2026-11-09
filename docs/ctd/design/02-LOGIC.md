# 02 — Logic specification

All behaviour below is driven by rule packs (§3). Nothing here hard-codes an EDA requirement. Citations for facts are in the knowledge base (`../CTD-KNOWLEDGE-BASE.md`, `../ECTD-KNOWLEDGE-BASE.md`, `../ectd/*`).

## 1. Core concepts

| Concept | Definition |
|---|---|
| **Workspace** | One company (applicant/MAH): its parties, users, licence and dossiers |
| **Dossier** | One application for **one strength and one dosage form**. This mirrors the eCTD draft rule «one eCTD per strength or dosage form». It has a fixed UUID |
| **Profile** | The facts about the dossier that decide what is required (§4) |
| **Rule pack** | A versioned, cited set of requirements, checks, vocabularies, templates and folder maps |
| **Requirement (slot)** | A document the dossier needs, resolved from the profile. It holds 0..n documents |
| **Document** | A file plus metadata, with a class that decides what may be done to it (§6). Versions are immutable |
| **Check** | A rule evaluated on a document, a slot or the whole dossier. Result: pass / warn / fail / not-applicable, with a message, a reason, an action and a source |
| **Sequence** | A submission event (0000, 0001…). It has a type, a unit, a mode, a related sequence and leaf operations |
| **Package** | An export of a sequence through a writer (CTD / eCTD 3.2.2 / eCTD 4.0) |

## 2. Data model (entities and key fields)

```
Workspace(id, name, legal_name_en, legal_name_ar, letterhead_template, signatories[], licence)
  Party(id, role[MAH|manufacturer|packager|batch_releaser|store|toll|api_manufacturer|cro|stability_site],
        name, address_full (unit/block), country, gmp_ref, licence_refs[])
  User(id, name, roles[Preparer|Reviewer|Approver|Viewer|Admin])
Dossier(uuid, workspace, product, profile, rule_pack_set[], status, created, owner)
  Product(trade_name_en, trade_name_ar, inn, salt, strength, unit, dosage_form, route, physical_chars,
          shelf_life, storage, pack, price, atc, therapeutic_group, indication, reference_product)
  Profile(§4)
  API(id, inn, form) → APIManufacturer(party, option[CEP|DMF|PQ|FULL], cep_no, cep_date, dmf_ap_ver, dmf_rp_ver,
                                         loa, importation_approval, spec_ref, psd_controlled, polymorph_controlled)
  Formula(unit_rows[component, qty, unit, function, standard, grade, layer], batch_sizes[], overage)
  Batch(no, strength, size, scale[pilot|production|smaller], date, site, api_source, uses[], bmr_scan_doc, numeric_results)
  Spec(scope[API|FPP|excipient|packaging], tests[test, limit_release, limit_shelf, method_ref, chapter_ref])
  StabilityStudy(batch, condition, container, intervals[], results[], photostability, in_use, commitment)
  Slot(req_id, status, documents[], waived_reason?)
  Document(id, slot, class, origin[generated|company|third_party|eda], file_hash, versions[], checks[], lock)
  Sequence(no, type, unit, mode, related[], description, leaf_ops[], tracking_row)
  Variation(id, catalogue_ref, pac, grouped_with[], ctd_sections[], studies[], status)
AuditEvent(ts, user, action, object, before_hash, after_hash)
```

### 2.5 Permissions

| Action | Preparer | Reviewer | Approver | Viewer |
|---|---|---|---|---|
| Edit data, upload, generate | ✔ | — | — | — |
| Comment, mark «reviewed» | ✔ | ✔ | ✔ | — |
| Approve sequence for export | — | — | ✔ | — |
| Export package | ✔ (draft watermark) | — | ✔ (final) | — |
| View | ✔ | ✔ | ✔ | ✔ |

In single-user mode one person holds every role. The approval step still exists as a deliberate confirmation.

### 2.6 Storage

- **Local mode:** the workspace folder holds a SQLite DB, a content-addressed file store (SHA-256), and logs.
- **Team mode:** a server DB and an object store.
- An adapter interface keeps both modes identical to the engine.

## 3. Rule packs

**Format.** Each pack is a folder with:
- `pack.yaml`: id, title, source docs (code, version, issue, effective, status in-force|draft|derived), supersedes, valid_from, valid_to;
- `requirements.yaml`;
- `checks.yaml`;
- `vocab/*.yaml`;
- `folders.yaml`;
- `templates/*.docx`.

**Requirement record:**
```yaml
- id: M1.1.1.13            # stable id
  title: {en: "CPP / eCPP", ar: "شهادة المستحضر الصيدلي"}
  ctd: {nta065_v5: "1.1.13", ectd_m1: "1.2.6.1"}      # numbering per output
  applies: "origin == 'imported' or (origin == 'local' and licence == 'under_licence')"
  required: {I: R, G_IMP: R, G_LOC: R}                # matrix from the source
  doc_class: third_party_certificate
  acceptance: [cpp.valid, cpp.egypt_importing, cpp.marketed_1y, cpp.composition, cpp.legalised_or_ecpp]
  source: {doc: NP.CAPP.065, ver: 5, sec: "1.1.13", page: 4-5}
```

**Expression language.** A small, safe boolean language over profile fields, using `and`, `or`, `not`, `in` and comparisons. No code execution.

**Pack set per dossier.** The user chooses the pack set, e.g. *in-force* (v5) or *preview of drafts* (v6 + M1 guidance). Changing the set triggers re-resolution with a diff report (§5.3).

## 4. Profile (the facts that drive requirements)

| Field | Values | Notes |
|---|---|---|
| dossier_kind | innovator / generic | |
| origin | local / imported | |
| licence | own / toll / f_toll / under_licence / imported / imported_bulk | `f_toll` appears in the draft M1 guidance and is undefined there, so the UI asks for confirmation |
| activity | new / re_registration / renewal / variation / preliminary_reregistration | |
| route | one_submission (default) / rolling (legacy, read-only after 01/12/2026) | |
| decree_case | 450-Case1 / Case2-TrackA / B / C / Case3 / 820-2016 / other | Affects timelines and forms |
| reference_status | referenced / non_referenced | |
| pharmacopoeial | yes / no | |
| dosage_specifics | coated, capsule_hard, pellets, premix, powder_inj_with_solvent, sterile, modified_release, inhalation | Multi-select |
| leaflet | english / non_english / pil_only | |
| store_separate_from_factory | yes / no | |
| api[] options | CEP / DMF / PQ / FULL, per manufacturer | |
| biological | yes / no | Out of scope v1 → shows a «not supported yet» banner |

**Validation of the profile itself.** Contradictions are blocked with an explanation, e.g.:
- local + imported_bulk;
- innovator + local generic column;
- rolling selected after closure;
- biological = yes.

## 5. Requirement resolution

### 5.1 Algorithm

```
for each requirement in pack_set:
    if not eval(applies, profile): skip (not applicable, record reason)
    level = required[column(profile)]          # R / NR / O / R* (conditional)
    if level == NR: mark not-required (visible in «why not required»)
    else create/keep slot(level)
slots per API manufacturer and per option are expanded (e.g. CEP-route S-sections, DMF LoA)
re-registration replaces new-registration acceptance rules with GL.CAPP.039 relaxations
```

The column is `I`, `G_IMP` or `G_LOC`. An imported innovator uses `I`. A local innovator is not in the source matrix, so it falls back to `I` with an «assumption» flag.

### 5.2 Slot status (derived, never typed by the user)

| Status | Condition |
|---|---|
| ⚪ Not started | No document |
| 🔵 Received | ≥1 document, checks pending |
| 🟢 Conforming | All blocking checks pass |
| 🟠 Needs attention | Only warnings (best practice) |
| 🔴 Non-conforming | ≥1 blocking failure |
| ⚫ Not applicable | Profile excludes it, or a justified waiver approved by a Reviewer |
| 🟣 Waiting on third party | The user marked it as requested from the issuer (with a date); a reminder is due |

### 5.3 Profile or pack change

1. Recompute the slots.
2. Show a diff: added, removed and changed-acceptance slots.
3. Documents in removed slots are moved to «unassigned», never deleted.

## 6. Document classes and the rebuild policy (decision table)

| Class | Examples | May edit content? | Allowed technical ops | When non-conforming |
|---|---|---|---|---|
| `generated` | Annex I, cover letter, tracking table, M3 tables, QOS, commitments, justifications | ✔ (regenerate) | All | **Rebuild from data.** If data is missing, ask for the exact fields |
| `company_letter` | Declarations, composition certificate | ✔ via template | All | **Rebuild from template + data** → sign/stamp/scan step |
| `company_technical` | Development report, validation report, methods, stability raw data | ✘ text, ✔ tables generated alongside | Split/merge, bookmarks, OCR, PDF-version normalise | **Partly:** build structure/tables; request missing raw data by name |
| `third_party_certificate` | GMP, CPP, CEP, licences, CoA of supplier, LoA | **✘ locked** | Rename, place, page split/merge, bookmarks; never alter pixels/text | **Re-obtain:** generate a request letter to the issuer; mark 🟣 |
| `eda_document` | Approvals, pricing certificate, inspection report | **✘ locked** | Same as above | Re-obtain from EDA |
| `executed_record` | Executed BMR | **✘ locked** | Scan placement only | Re-scan legibly; never retype |
| `signed_scan` | Wet-signed generated letter | **✘ locked** after upload | Placement | Regenerate the source, re-sign |

**Hard guard.** Any operation on a locked class that changes content returns `E-LOCKED` and is logged as an audit event.

## 7. Checks (pipeline)

The pipeline runs per document on upload and on change, incrementally:
1. **Intake:** type sniffing (PDF/DOCX/XLSX/image); hash; duplicate detection (same hash in another slot gives a warning, with a «reuse» option).
2. **Technical (pack `tech.*`):**
   - PDF version 1.4–1.7 / PDF/A-1/2 (≤1.3 fails);
   - encryption/permissions;
   - portfolio/embedded files;
   - fonts embedded;
   - text layer present, with OCR required unless the class is exempt;
   - bookmarks when a TOC exists;
   - page size;
   - file-name characters and length (≤64);
   - projected path length (≤180).
3. **Classification:** propose the slot from the file name and content keywords; the user confirms.
4. **Content (pack-specific):** text extraction plus regex/keyword rules, e.g.:
   - «Conform» as a result;
   - missing «Q =» in a dissolution spec;
   - fewer than 2 batches in a batch-analysis table;
   - missing general-chapter column;
   - missing «nitrosamine» or «Q3D» statement;
   - CPP missing «Egypt»;
   - CEP not current (date vs EDQM — manual confirmation step, no live call).
5. **Cross-document (dossier-level):** the 11 cross-checks from the Excel (CPP sites ↔ P.3.1; composition ↔ CPP ↔ 1.2.1; spec ↔ batch; GMP address ↔ Annex I; pack ↔ pricing; batch numbers consistent…).
6. **Verdict:** each check gives severity `blocking` / `warning` / `info`, a message (AR/EN), a reason, an action (`fix_auto` | `rebuild` | `request_data:{fields}` | `reobtain:{issuer}` | `waive_with_justification`) and a source.

Auto-fixes never run without showing a before/after preview, and they create a new version.

## 8. Generation

Templates are `.docx` with placeholders. Data comes from the model, and each template declares its required fields:
- if a field is missing, the action is a `request_data` list;
- arithmetic (salt factor, % composition, subtotals) is computed by the engine and shown with its formula.

Outputs:
- DOCX for review;
- PDF (LibreOffice) for the package;
- generated letters are watermarked «DRAFT — unsigned» until a signed scan is uploaded.

## 9. Writers (export)

| Writer | Structure | Notes |
|---|---|---|
All three writers ship in the first release and read the same dossier model. Each eCTD writer loads its **regional profile pack** (provisional EG v0 now, official EG later).

| `ctd.nta065` | Folders `Module 1/1.1.x …`, `Module 3/3.2.S/...` with titles; variation approvals in one sub-folder per variation (NP.CAPP.065 1.1.7); `index.html` navigator; readiness report | Today's One Submission (upload through the EDA Google Forms) |
| `ectd.322` | `NNNN/` + `index.xml` (ICH DTD) + `index-md5.txt` + `util/dtd`, `util/style` + `m1/eg/eg-regional.xml` (profile) + ICH App. 4 names; `NNNN-workingdocuments/` | Leaf ops new/replace/delete; modified-file = `../NNNN/index.xml#id` |
| `ectd.40` | `N/submissionunit.xml` + `sha256.txt` | Context of use from ICH CV; keywords; UUID reuse |

**Pre-export gate.** The export is blocked if:
- any **blocking** check fails in a slot that is required;
- the Approver has not approved;
- a provisional profile is used and the user has not acknowledged the «provisional» banner.

## 10. Sequences and lifecycle (eCTD)

- **First eCTD:** sequence `0000`; for a dossier already filed in another format, a **baseline** (type `none`, unit `reformat`) comes first.
- **Related sequence:** equals the own number for `initial` and `reformat`; otherwise the sequence that started the activity.
- **Replace/delete** are only allowed within the same CTD element and the same repeatable attributes (substance, manufacturer, product-name, dosageform, indication).
- **A misplaced leaf** is fixed with `delete` plus `new`, pointing to the original file.
- **Parallel variations:** option 2, «Approved» plus «Proposed» documents for the SmPC/RMP.
- **Rejected or withdrawn activity:** a consolidation sequence (unit `response`).
- **The tracking table** is rebuilt automatically on every sequence.

## 11. Variation engine

1. **Picker:** search the catalogue (EDA tool, 90 human rows + v6) by group, type or free text. It shows PAC, conditions and requirements.
2. **Condition checklist:** the user ticks each condition. If one is not met, the engine suggests the next class (as the guideline's footnotes do) or blocks.
3. **Grouping:** the class is the highest of the group (v6 §2.5.3); the mode is single or grouping.
4. **Sections:** the NP.CAPP.112 map gives the CTD sections to update, which open slots as «to update in this sequence».
5. **Studies:** CADC, stability, dissolution/BE requirements create tasks with external dependencies.
6. **Output:** the variation form plus declarations (draft M1 guidance Annex 3), the updated sections, and a sequence with replace operations.

## 12. Edge cases (must be handled, each with a defined behaviour)

| # | Case | Behaviour |
|---|---|---|
| E1 | Same file uploaded to two slots | Warn; offer «reuse» (eCTD: one file, two leaves only if allowed, otherwise copy) |
| E2 | Scanned third-party PDF with no text | Allowed (OCR-exempt classes); a company technical doc → OCR offered |
| E3 | PDF ≤ 1.3 that is third-party | Convert the container version without re-rendering content; if impossible → re-obtain |
| E4 | Encrypted third-party PDF | Cannot unlock → re-obtain an unsecured copy (letter generated) |
| E5 | File name in Arabic or with spaces | Rename to an ICH-safe name; the original name is kept as the title |
| E6 | Path > 180 | Shorten the variable parts; show a preview |
| E7 | Two API manufacturers, one CEP and one DMF | Two m32s plus one applicant m32s; different slots per option |
| E8 | Combination product (2 APIs) | One S-part per API |
| E9 | Product with diluent/solvent | Separate P-part; solvent licence slot (1.1.18) |
| E10 | Profile changes after documents were added | Diff; orphans go to «unassigned», never deleted |
| E11 | Pack changes v5 → v6 (draft adopted) | Diff report; per-slot «what changed» with sources |
| E12 | CEP expired or withdrawn | Blocking; switch the option to DMF/FULL with a diff of the required S-sections |
| E13 | Re-registration product with old molecule | GL.CAPP.039 relaxations; justification generator |
| E14 | Generated letter edited by hand after signing | The signed scan is locked; to change it, regenerate and re-sign (new version) |
| E15 | Export interrupted (disk full or crash) | Atomic temporary folder; resume; never a half package |
| E16 | Duplicate trade names across dossiers | Allowed; dossiers are keyed by UUID |
| E17 | Rolling-route dossier opened after 01/12/2026 | Read-only legacy; a «convert to One Submission» wizard |
| E18 | Biological product | «Not supported in v1» banner; profile saved |
| E19 | Mixed languages (non-English leaflet) | Translation-declaration slot appears |
| E20 | User lacks the role for an action | The button is disabled with a tooltip giving the reason |
| E21 | Two users editing the same slot (team mode) | Optimistic locking; merge prompt |
| E22 | Licence expired | Read and export of existing packages stay allowed; no new dossier |
