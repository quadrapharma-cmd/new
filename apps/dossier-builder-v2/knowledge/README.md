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
| `recognition/`, `templates/`, `vocab/` | The program's own aids (recognition keywords, the template in front of each item, dose forms and countries). |

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
```

## القواعد — Rules the build enforces (`core/validate.js`)

1. Every record cites at least one source, and every cited source is registered.
2. Every id is unique; every authority, set and evidence slot a record names exists.
3. A source's aliases never name two sources.
4. A requirement in force never rests on drafts alone (a draft is never cited as a requirement).
5. Every copy of a source kept in the repository exists and matches `docs/ctd/sources/MANIFEST.json`.

## التعديل — Editing

Edit the YAML here, then run `npm run build` and `npm test`. The records were ported once from the old program
(`tools/port-v1.mjs`); that script now refuses to run again without `--force`, so it cannot overwrite edits made here.
