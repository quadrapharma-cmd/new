# المعرفة — Knowledge

كل اللي البرنامج يعرفه عن الهيئات موجود هنا كملفات بيانات. **كل سجل لازم يستند لمصدر مسجّل**، والبناء بيقف لو فيه سجل من غير مصدر أو مرجع مكسور.

Everything the program knows about the authorities lives here as data. **Every record rests on a registered source**; the build stops on a record without one or on any broken reference.

## الملفات — Files

| File | What it holds |
|---|---|
| `authorities.yaml` | The authorities (EG-EDA, EG-GOV, EU, GCC, US-FDA, ICH, WHO, STANDARDS, OTHER). |
| `sources.yaml` | Every guideline, specification, law or data set a record may cite: code, version, dates, status, the copy kept in the repository, when it was last checked, and the ways older records wrote it (`aliases`). |
| `sets.yaml` | The sets of records, the file each lives in, and the sources each set rests on as a whole. |
| `requirements/*.yaml` | What a dossier must hold, per authority (EDA Module 1–5; ICH Modules 2–5; EU, GCC and US Module 1; a general Module 1). |
| `review/eg-eda.yaml` | The questions EDA's assessors ask (screening, quality, CADC, stability, BE, re-registration, labelling, clinical, gates, international layer). |
| `variations/eg-eda.yaml` | EDA's variations: class (PAC), conditions and documents, from EDA's own tool. |
| `documents/eg-eda-validity.yaml` | The documents a file keeps, and how long each stays valid. |
| `countries.yaml` | What each country or region takes (formats, Module 1, validation criteria). |
| `ectd/` | The eCTD tables as published (ICH 3.2.2 Appendix 4, the 4.0 controlled vocabularies, STF), with `index.yaml` citing them. |
| `recognition/`, `templates/`, `vocab/` | The program's own aids (recognition keywords, the template in front of each item, dose forms and countries; `vocab/glossary.yaml`: the words of the trade in Arabic and English, so a search in one language finds the other). |
| `checks/citations.json` | **Generated** by `tools/verify-sources.mjs`: what the check found for every citation (never edit by hand). |
| `checks/findings.yaml` | What each review found and what was done, written by hand; the library's «Review» page shows it. |
| `checks/eda-site.json` | **Generated** by `tools/check-eda-site.mjs --save`: every document EDA's website published at the last check (the baseline the next check compares with). |

## شكل السجل — A record

```yaml
- id: EG-EDA/M1-01            # unique across all knowledge
  kind: requirement           # requirement · rule · variation · doctype · country · table
  authority: EG-EDA
  set: eg-eda-ctd
  title: {en: …, ar: …}
  status: in-force            # in-force · draft · derived · assumption · general
  cite:                       # at least one; each names a registered source
    - src: eda-np-capp-065-v5
      at: Annex I             # the place in the source (section, page, row)
      quote: …                # the source's own words, where kept
  ectd_cite: […]              # where the eCTD placement comes from (requirements)
  anchor_cite: […]            # the international reference a review rule leans on
  check: {verdict: …, note: {en, ar}}   # what a review changed or found in this record, said plainly
```

A citation can also carry `gist` (what the source says, in our words — never shown as its words), `note` (a remark about the
place) and `read: {how: page image, on: …}` (a page whose text layer cannot be read by machine, read from its image). A variation
names its item in the guideline (`guideline: {section, heading, item, pac}`); its `pac` is the guideline's class, and `pac_tool`
keeps EDA's tool's class where the two differ. A source carries `latest` (the last check on the authority's website),
`superseded_by` when replaced, `url` (its page on the authority's site) and `numbering: true` when it sets the section numbers.

## المراجعة — The review (`tools/verify-sources.mjs`)

Reads the text of every source kept in the project (PDF, Word, Excel, zip) and checks each citation:
- a **quote** must be in the source word for word (spacing and punctuation aside) or nearly, and on the page the citation names;
- a **place** (section number, page, annex, option, step) must exist in the source;
- a record's own **CTD number** must exist in a source that sets the numbers; a **variation's** class must be the class the guideline
  prints right after its item, and its row in EDA's table must match its wording.

Results: `verified` (the words are there), `located` (the place is there), `read` (read from a page image), `nothing-to-check`
(a copy is kept but no place is named), `no-copy` (no copy kept: only the version and date were checked). `partly` and `not-found`
must not stay: the tests fail on them. Run `node tools/verify-sources.mjs` after changing any citation; `node tools/find-in-source.mjs
<source> <words>` shows where words sit in a source.

## القواعد — Rules the build enforces (`core/validate.js`)

1. Every record cites at least one source, and every cited source is registered.
2. Every id is unique; every authority, set and evidence slot a record names exists.
3. A source's aliases never name two sources.
4. A requirement in force never rests on drafts alone (a draft is never cited as a requirement).
5. Every copy of a source kept in the repository exists and matches `docs/ctd/sources/MANIFEST.json`.

## التعديل — Editing

Edit the YAML here, then run `npm run build` and `npm test`. The records were ported once from the old program
(`tools/port-v1.mjs`); that script now refuses to run again without `--force`, so it cannot overwrite edits made here.
