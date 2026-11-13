# EU eCTD 3.2.2 regional profile — EU Module 1 v3.1.1

What the program writes and checks an EU eCTD sequence against. Every file here is the EMA's own text or is built from it; nothing
is provisional (unlike `../EG-PROVISIONAL-PROFILE-v0`, which stands in for an EDA DTD that is not published).

| file | what it is | from |
|---|---|---|
| `util/dtd/ich-ectd-3-2.dtd`, `util/dtd/eu-regional.dtd`, `util/dtd/eu-envelope.mod`, `util/dtd/eu-leaf.mod`, `util/style/ectd-2-0.xsl`, `util/style/eu-regional.xsl` | the files every sequence carries in `util/` (VC 1.x–6.x) | `docs/ctd/sources/ectd/EU_M1_util_v3.1.zip` (EMA eSubmission, EU M1 3.1 util package), byte for byte |
| `util-md5.txt` | their MD5 — the published values the criteria compare with (VC 1.3 `1d6f631c…`, 3.3 `f8e47324…`, 6.3 `474f3fe1…`) | computed from the files above |
| `validation-criteria.csv` | all 111 criteria (83 Pass/Fail, 28 Best Practice), text and comments word for word, with the «lifecycle needed» flag | `docs/ctd/sources/ectd/EU_M1_Validation_Criteria_v8.2.xlsx`, sheet «eCTD Validation Criteria» (v8.2, in force 1 December 2025) |
| `m1.csv` | each Module 1 section: its element, folder and fixed file-name component (alternatives after `\|`, the first is the default); `{cc}` country folder, `{ll}` language folder, `{pidoc}` PI type, `{basis}` generic / hybrid / biosimilar | EU M1 Specification v3.1.1 (June 2025) Appendix 2, checked row by row against the criteria's sheet «File-Folder Structure & Names» |

Rebuild the first three from the sources with `python3 apps/dossier-builder/tools/build_eu_profile.py`; `m1.csv` is kept by hand.

## The rules the writer follows (`engine/dossier_engine/writers/ectd32_eu.py`)

- `eu-regional.xml` at `m1/eu/`, root `eu:eu-backbone` (`dtd-version="3.1"`), the DTD and the stylesheet referenced in `../../util/`.
- **Envelopes** (SPEC 3.1.1 §Envelope, VC 14.x): centralised → one envelope `ema` (agency `EU-EMA`); national → one envelope for the
  country; decentralised / mutual recognition → one envelope per country in the procedure. The UUID is the application's, the same in
  every envelope and every sequence (VC 9.7–9.9). `related-sequence` is the sequence itself for `initial` / `reformat`, otherwise the
  sequence that started the activity (VC 14.6/14.7). The tracking number is «to be advised» until the procedure number is known.
- **Country and language** (SPEC «Country-specific folders»): 1.0, 1.2, 1.3.1–1.3.5, responses and additional data sit in a country
  folder — `ema` in the centralised procedure, `common` for what is shared in DCP / MRP, the country itself in a national procedure —
  and each leaf is wrapped in `specific country="…"`. 1.3.1 adds a language folder and `pi-doc xml:lang type country`.
- **File names** (SPEC «File Naming Convention»): lower case, `cc-fixed[-var].pdf`; the tracking table is `cc-tracking.pdf` in
  `10-cover/cc` (VC 15.11/15.12); a second file under the same heading takes `-2`, `-3` (the optional variable part).
- `index.xml` refers to `m1/eu/eu-regional.xml` («EU Module 1»), `index-md5.txt` holds its MD5, `util/` is copied whole.

## What the validator checks (`engine/dossier_engine/validators/ectd32_eu.py`)

It reads the written sequence back from disk and runs the criteria it can decide from the files; each criterion it does not decide is
listed with the reason. It is not an EMA-accepted validation tool: run one (e.g. the national agencies' or a commercial validator on
VC 8.2) before submission.
