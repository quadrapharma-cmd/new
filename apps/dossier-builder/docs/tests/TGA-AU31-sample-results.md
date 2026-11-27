# TGA AU 3.1 eCTD sample: results of the Dossier Builder eCTD check

Run on 27 November 2026 (UTC), program at commit f90b8af (branch `claude/new-session-8nmyo7`), Python 3.13.18, in a cloud container.
None of the TGA's files are in git. This report is the only file committed.

## Summary

- The download worked. The TGA folder lists the zip, which is 3,782,597 bytes and holds 3 sequences in 2 applications.
- The program reads every sequence as region `au` (authority TGA). It has no TGA criteria of its own, so only the ICH layer ran (23 of 23 rules).
- Every sequence gets the same result: **pass 21 · fail 1 · warning 1 · not run 0**, and the verdict is "Fails an ICH check".
- **The one failure (ICH-Q36-13, "No file in m1-m5 is left without a leaf") is a false alarm by the program.** Every file it flags
  is present on disk and is referenced by a leaf in `m1/au/au-regional.xml`: 49 of 49, 4 of 4 and 4 of 4. The AU regional XML puts
  its elements in the default namespace `tga_ectd`, so lxml sees its leaves as `{tga_ectd}leaf`. The rule collects leaves with
  `tree.iter('leaf')` (engine/dossier_engine/validators/global_ectd.py, the loop over `(idx, tree), (reg, rtree)`), and that finds
  0 leaves in each AU regional XML (see "Evidence for the false alarm"). As a result, every Module 1 file reads as "without a leaf".
  The same un-namespaced `iter('leaf')` is in `package.leaves()`.
- The warning (ICH-FMT-03, fonts not embedded: Tahoma or Times New Roman) is what the PDFs report. This report does not judge it.
- Package check: in its `sequences` rows the two `0000` sequences cannot be told apart, because a row carries no application folder.
  Sequences are ordered by folder name only, and the "previous" list builds up across applications. On this run `e000222/0000` was
  checked with `e000111/0000` as its previous, and `e000111/0001` with both. The counts did not change.
- `tests/test_global_ectd.py` failed to collect with only `mac/requirements.txt` installed (`No module named 'fastapi'`). It passed (22 passed)
  after installing the test-only packages listed in `requirements-dev.txt`.

## 1. Setup and machine check

| Step | Time |
|---|---|
| `python3 -m pip install -q --disable-pip-version-check --ignore-installed -r apps/dossier-builder/mac/requirements.txt` | 18.5 s (succeeded; only pip's "running as root" warning) |
| `python -m pytest -q tests/test_global_ectd.py` (first run) | 1.1 s, **collection error** |
| extra: `pip install fastapi python-multipart httpx uvicorn openpyxl jsonschema pypdf` (from requirements-dev.txt), then the same pytest | 4.2 s, **22 passed** |

First pytest run:

```

==================================== ERRORS ====================================
__________________ ERROR collecting tests/test_global_ectd.py __________________
ImportError while importing test module '/home/user/new/apps/dossier-builder/tests/test_global_ectd.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_global_ectd.py:12: in <module>
    from test_ectd32_eu import envelope, docs, PROD          # noqa: F401  (the EU fixture)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_ectd32_eu.py:6: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fastapi'
=========================== short test summary info ============================
ERROR tests/test_global_ectd.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.26s

```

Second pytest run (after the extra packages): `22 passed in 3.68s`.

`mac/requirements.txt` does not list `fastapi`, but `tests/test_ectd32_eu.py` (which `test_global_ectd.py` imports) needs it.

## 2. Download

- Folder listing: `curl https://apps.tga.gov.au/downloads/ectd-31/`. The first try ended with `curl: (35) Recv failure: Connection reset by peer`
  after 11.6 s. The agent proxy reported `apps.tga.gov.au:443 — ws_closed_mid_exchange` (the tunnel closed). That is not a policy block,
  and a plain retry of the same URL got HTTP 200 (1,771 bytes). The listing shows (dates as the server gives them):
  - `10/17/2017 3:49 PM  3782597  au-3-1-ectd-sample-submissions.zip`
  - also there, not downloaded: au-regional-specification-validation-criteria-3-1.xlsx (5,996,487), au-regional.xsd, au-regional.xsl, codes.xsl,
    document-matrix.xml/.xsl, reg-activity-lead.xml, sequence-description.xml, sequence-matrix.xml/.xsl, sequence-type.xml, xlink.xsd, xml.xsd.
- Downloaded: **https://apps.tga.gov.au/downloads/ectd-31/au-3-1-ectd-sample-submissions.zip**, HTTP 200, `application/x-zip-compressed`, 4.6 s.
  - Size **3,782,597 bytes** (matches the listing).
  - SHA-256 **d66eadc39e071846e6173398af7424d74483daa07395ecd7e0b63cb63888321a**.
  - Zip, stored (no compression). 177 entries, 4,222,657 bytes uncompressed, 86 files. No absolute, `..` or symlink entries.
- Unzipped into `/tmp/tga/data` (0.04 s). Sequence folders (four digits with an index.xml), oldest first per application:
  - `AU 3.1 eCTD Sample Submissions/e000111/0000`
  - `AU 3.1 eCTD Sample Submissions/e000111/0001` (previous: e000111/0000)
  - `AU 3.1 eCTD Sample Submissions/e000222/0000`

## 3. Command-line check per sequence

Run from `apps/dossier-builder/engine`. `$R` = `/tmp/tga/data/AU 3.1 eCTD Sample Submissions`.

### e000111-0000

```
region: au · TGA · its criteria: TGA
1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH — pass 21 · fail 1 · warning 1 · not run 0
   ICH-Q36-13: ['m1/au/100-correspondence/1001-cover/cover.pdf', 'm1/au/100-correspondence/1002-tracking/tracking.pdf', 'm1/au/102-admin-info/1021-app-form/app-form.pdf']
the authority's own criteria are not in the program: only the ICH layer was run
report: /tmp/tga/e000111-0000.html

real	0m2.258s
user	0m2.215s
sys	0m0.028s
exit 2
```

### e000111-0001

```
region: au · TGA · its criteria: TGA
1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH — pass 21 · fail 1 · warning 1 · not run 0
   ICH-Q36-13: ['m1/au/100-correspondence/1001-cover/cover.pdf', 'm1/au/100-correspondence/1002-tracking/tracking.pdf', 'm1/au/100-correspondence/1003-response/response.pdf']
the authority's own criteria are not in the program: only the ICH layer was run
report: /tmp/tga/e000111-0001.html

real	0m0.417s
user	0m0.387s
sys	0m0.020s
exit 2
```

### e000222-0000

```
region: au · TGA · its criteria: TGA
1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH — pass 21 · fail 1 · warning 1 · not run 0
   ICH-Q36-13: ['m1/au/100-correspondence/1001-cover/cover.pdf', 'm1/au/100-correspondence/1002-tracking/tracking.pdf', 'm1/au/102-admin-info/1021-app-form/app-form.pdf']
the authority's own criteria are not in the program: only the ICH layer was run
report: /tmp/tga/e000222-0000.html

real	0m0.453s
user	0m0.424s
sys	0m0.028s
exit 2
```

Each run wrote its HTML report to `/tmp/tga/<seq>.html` (not committed). Exit status 2 means "not ok".

## 4. Non-pass results per layer and sequence (Python `G.validate(seq, previous=[...])`)

Every sequence has only one layer, `1 · ICH — every country`, because `own_criteria_run` is False for `au`. Each failure list is capped at 50
entries by the program. Below, the rule, status, severity, text, the failures (first 50) and the reason come from the program's result.

```
=== e000111/0000 (previous=[]) 2.12s region=au country=AU authority=TGA criteria=TGA own_criteria_run=False ok=False
  layer 1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH counts={'pass': 21, 'fail': 1, 'warning': 1, 'not_run': 0} coverage=23/23
    {"rule": "ICH-Q36-13", "status": "fail", "severity": "pass_fail", "text": "No file in m1-m5 is left without a leaf · لا ملف في m1-m5 بلا ورقة تشير إليه", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf", "m1/au/100-correspondence/1002-tracking/tracking.pdf", "m1/au/102-admin-info/1021-app-form/app-form.pdf", "m1/au/102-admin-info/1022-pre-sub/pre-submission-details.pdf", "m1/au/102-admin-info/1023-patent/patent-certification.pdf", "m1/au/103-med-info/1031-pi/10311-pi-clean/pi-clean.pdf", "m1/au/103-med-info/1031-pi/10312-pi-annotated/pi-annotated.pdf", "m1/au/103-med-info/1031-pi/10313-pi-approved/pi-approved.pdf", "m1/au/103-med-info/1031-pi/10314-pack-ins/10mg-capsul-package-insert.pdf", "m1/au/103-med-info/1031-pi/10314-pack-ins/10mg-tablet-package-insert.pdf", "m1/au/103-med-info/1031-pi/10314-pack-ins/5mg-capsul-package-insert.pdf", "m1/au/103-med-info/1031-pi/10314-pack-ins/5mg-tablet-package-insert.pdf", "m1/au/103-med-info/1032-cmi/10321-cmi-clean/cmi-clean.pdf", "m1/au/103-med-info/1032-cmi/10322-cmi-annotated/cmi-annotated.pdf", "m1/au/103-med-info/1032-cmi/10323-cmi-approved/cmi-approved.pdf", "m1/au/103-med-info/1033-mockup/10331-mockup-clean/mockup-clean.pdf", "m1/au/103-med-info/1033-mockup/10332-mockup-annotated/mockup-annotated.pdf", "m1/au/103-med-info/1033-mockup/10333-mockup-approved/mockup-approved.pdf", "m1/au/104-expert/1041-quality/quality.pdf", "m1/au/104-expert/1042-nonclinical/nonclinical.pdf", "m1/au/104-expert/1043-clinical/clinical.pdf", "m1/au/105-specific/1051-lit-based/lit-based.pdf", "m1/au/105-specific/1052-orphan/orphan-drug-designation.pdf", "m1/au/105-specific/1053-gmo/gmo-consents.pdf", "m1/au/105-specific/1054-add-tradename/add-tradename.pdf", "m1/au/105-specific/1055-co-marketed/co-marketed.pdf", "m1/au/105-specific/1056-comb-med/comb-med-cons.pdf", "m1/au/105-specific/1057-otc-prod-assurance/otc-prod-assurance.pdf", "m1/au/105-specific/1058-analyt-val-sum/analyt-val-sum.pdf", "m1/au/106-master-files/1061-external-sources/external-sources.pdf", "m1/au/106-master-files/1062-app-decl/app-decl.pdf", "m1/au/106-master-files/1063-loa/loa.pdf", "m1/au/107-compliance/1071-pre-sub-outcomes/pre-sub-outcomes.pdf", "m1/au/107-compliance/1072-additional-data/additional-data.pdf", "m1/au/107-compliance/1073-pre-sub-planning/pre-sub-planning.pdf", "m1/au/108-pharmacovigilance/1081-phvig-system/phvigsystem.pdf", "m1/au/108-pharmacovigilance/1082-riskmgt-system/riskmgtsystem.pdf", "m1/au/109-sum-biopharm/1091-sum-ba-be/summary-of-bioavailability-or-bioequival.pdf", "m1/au/109-sum-biopharm/1092-justif-no-study/justification-for-not-providing-biopharm.pdf", "m1/au/110-paediatrics/paediatrics.pdf", "m1/au/111-foreign/1111-reg-status/foreign-reg-status.pdf", "m1/au/111-foreign/1112-pi/foreign-pi-1.pdf", "m1/au/111-foreign/1112-pi/foreign-pi-2.pdf", "m1/au/111-foreign/1112-pi/foreign-pi-3.pdf", "m1/au/111-foreign/1113-similarities/similarities.pdf", "m1/au/111-foreign/1114-eval-reports/eval-reports-1.pdf", "m1/au/111-foreign/1114-eval-reports/eval-reports-2.pdf", "m1/au/111-foreign/1114-eval-reports/eval-reports-3.pdf", "m1/au/112-antibiotic/antibiotic-resistance-data.pdf"], "reason": null}
    {"rule": "ICH-FMT-03", "status": "warning", "severity": "best_practice", "text": "Fonts are embedded · الخطوط مضمَّنة", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/100-correspondence/1002-tracking/tracking.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/102-admin-info/1021-app-form/app-form.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/102-admin-info/1022-pre-sub/pre-submission-details.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/102-admin-info/1023-patent/patent-certification.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10311-pi-clean/pi-clean.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10312-pi-annotated/pi-annotated.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10314-pack-ins/10mg-capsul-package-insert.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10314-pack-ins/10mg-tablet-package-insert.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10314-pack-ins/5mg-capsul-package-insert.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1031-pi/10314-pack-ins/5mg-tablet-package-insert.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1032-cmi/10321-cmi-clean/cmi-clean.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1032-cmi/10322-cmi-annotated/cmi-annotated.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1032-cmi/10323-cmi-approved/cmi-approved.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1033-mockup/10331-mockup-clean/mockup-clean.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1033-mockup/10332-mockup-annotated/mockup-annotated.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/103-med-info/1033-mockup/10333-mockup-approved/mockup-approved.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/104-expert/1041-quality/quality.pdf: Fonts not embedded: Times New Roman, Times New Roman,Bold. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/104-expert/1042-nonclinical/nonclinical.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/104-expert/1043-clinical/clinical.pdf: Fonts not embedded: Times New Roman, Times New Roman,Bold. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1051-lit-based/lit-based.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1052-orphan/orphan-drug-designation.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1053-gmo/gmo-consents.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1054-add-tradename/add-tradename.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1055-co-marketed/co-marketed.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1056-comb-med/comb-med-cons.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1057-otc-prod-assurance/otc-prod-assurance.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/105-specific/1058-analyt-val-sum/analyt-val-sum.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/106-master-files/1061-external-sources/external-sources.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/106-master-files/1062-app-decl/app-decl.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/106-master-files/1063-loa/loa.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/107-compliance/1071-pre-sub-outcomes/pre-sub-outcomes.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/107-compliance/1072-additional-data/additional-data.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/107-compliance/1073-pre-sub-planning/pre-sub-planning.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/108-pharmacovigilance/1081-phvig-system/phvigsystem.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/108-pharmacovigilance/1082-riskmgt-system/riskmgtsystem.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/109-sum-biopharm/1091-sum-ba-be/summary-of-bioavailability-or-bioequival.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/109-sum-biopharm/1092-justif-no-study/justification-for-not-providing-biopharm.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/110-paediatrics/paediatrics.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1111-reg-status/foreign-reg-status.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1112-pi/foreign-pi-1.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1112-pi/foreign-pi-2.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1112-pi/foreign-pi-3.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1113-similarities/similarities.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1114-eval-reports/eval-reports-1.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1114-eval-reports/eval-reports-2.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/111-foreign/1114-eval-reports/eval-reports-3.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/112-antibiotic/antibiotic-resistance-data.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m2/22-intro/introduction.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages)."], "reason": null}
=== e000111/0001 (previous=['e000111/0000']) 0.20s region=au country=AU authority=TGA criteria=TGA own_criteria_run=False ok=False
  layer 1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH counts={'pass': 21, 'fail': 1, 'warning': 1, 'not_run': 0} coverage=23/23
    {"rule": "ICH-Q36-13", "status": "fail", "severity": "pass_fail", "text": "No file in m1-m5 is left without a leaf · لا ملف في m1-m5 بلا ورقة تشير إليه", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf", "m1/au/100-correspondence/1002-tracking/tracking.pdf", "m1/au/100-correspondence/1003-response/response.pdf", "m1/au/104-expert/1041-quality/quality.pdf"], "reason": null}
    {"rule": "ICH-FMT-03", "status": "warning", "severity": "best_practice", "text": "Fonts are embedded · الخطوط مضمَّنة", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/100-correspondence/1002-tracking/tracking.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/100-correspondence/1003-response/response.pdf: Fonts not embedded: Times New Roman, Times New Roman,Bold. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/104-expert/1041-quality/quality.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages)."], "reason": null}
=== e000222/0000 (previous=[]) 0.13s region=au country=AU authority=TGA criteria=TGA own_criteria_run=False ok=False
  layer 1 · ICH — every country: Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH counts={'pass': 21, 'fail': 1, 'warning': 1, 'not_run': 0} coverage=23/23
    {"rule": "ICH-Q36-13", "status": "fail", "severity": "pass_fail", "text": "No file in m1-m5 is left without a leaf · لا ملف في m1-m5 بلا ورقة تشير إليه", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf", "m1/au/100-correspondence/1002-tracking/tracking.pdf", "m1/au/102-admin-info/1021-app-form/app-form.pdf", "m1/au/104-expert/1043-clinical/clinical.pdf"], "reason": null}
    {"rule": "ICH-FMT-03", "status": "warning", "severity": "best_practice", "text": "Fonts are embedded · الخطوط مضمَّنة", "failures": ["m1/au/100-correspondence/1001-cover/cover.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/100-correspondence/1002-tracking/tracking.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/102-admin-info/1021-app-form/app-form.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).", "m1/au/104-expert/1043-clinical/clinical.pdf: Fonts not embedded: Tahoma. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages)."], "reason": null}
```

`reason` is null for every non-pass result. ICH-Q36-13 shows 49, 4 and 4 failures, and ICH-FMT-03 shows 49, 4 and 4 warnings, all under the
cap of 50.

### Evidence for the false alarm (ICH-Q36-13)

For each sequence, this check tested every flagged file for presence on disk and for an `xlink:href` in `m1/au/au-regional.xml`
(resolved from that file's folder):

| Sequence | Flagged | Present on disk | Referenced by a leaf in au-regional.xml | Leaves in index.xml | Leaves in au-regional.xml |
|---|---|---|---|---|---|
| e000111/0000 | 49 | 49 | 49 | 2 | 49 |
| e000111/0001 | 4 | 4 | 4 | 1 | 7 |
| e000222/0000 | 4 | 4 | 4 | 1 | 4 |

lxml, counting leaves in each au-regional.xml:

```
e000111/0000 iter(leaf)= 0 iter({tga_ectd}leaf)= 49 root tag= {tga_ectd}tga_ectd
e000111/0001 iter(leaf)= 0 iter({tga_ectd}leaf)= 7 root tag= {tga_ectd}tga_ectd
e000222/0000 iter(leaf)= 0 iter({tga_ectd}leaf)= 4 root tag= {tga_ectd}tga_ectd
```

The root element is `<tga_ectd ... xmlns="tga_ectd" ...>`, so each leaf's tag is `{tga_ectd}leaf`, and the program's `iter('leaf')` finds
none of them. The same blind spot means the program does not run its leaf checks (ICH-Q36-04 attributes, Q36-11 MD5, Q36-12 target present,
Q36-20 titles) on the AU regional leaves. Those rules "pass" here without having seen those leaves. For e000111/0001, the 7 regional leaves (operation, href, modified-file)
are these. The program read none of them:

```
new     100-correspondence/1001-cover/cover.pdf
replace 100-correspondence/1002-tracking/tracking.pdf      modified-file ../../../0000/m1/au/au-regional.xml#Nc4942ce9f6074ad08fbb137d42e7513a
new     100-correspondence/1003-response/response.pdf
new     104-expert/1041-quality/quality.pdf
new     104-expert/1041-quality/quality.pdf                (the same href a second time)
new     ../../../0000/m1/au/104-expert/1042-nonclinical/nonclinical.pdf          (in the earlier sequence)
new     ../../../../e000222/0000/m1/au/104-expert/1043-clinical/clinical.pdf     (in the other application, e000222)
```

## 5. Diagnostics per sequence

All three sequences have the same backbone header:

- DOCTYPE: `<!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd"[]>`
- Root: `<ectd:ectd dtd-version="3.2" xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">`
- `xmlns:xlink` in index.xml: `http://www.w3c.org/1999/xlink` (the value the ICH DTD fixes). au-regional.xml instead declares
  `xmlns:xlink="http://www.w3.org/1999/xlink"`.
- Regional XML: `m1/au/au-regional.xml`, no DOCTYPE, `xsi:schemaLocation="tga_ectd ../../util/dtd/au-regional.xsd"`.
  The program's `regional_xml()` returns `('au', .../m1/au/au-regional.xml)` for each.
- util/ files (path, MD5, bytes), the same in all three:

| File | MD5 | Bytes |
|---|---|---|
| util/dtd/au-regional.xsd | 4fd79acbc42fe34ee27d05e144b1d844 | 13805 |
| util/dtd/ich-ectd-3-2.dtd | 1d6f631cc6b6357f0f4fe378e5f79a27 | 31400 |
| util/dtd/xlink.xsd | 52d1a3b8596e4fb61d3ec1cde24be16a | 9261 |
| util/dtd/xml.xsd | 382b0a4f7529d2c5f7b0af0aa713b0a5 | 5516 |
| util/style/au-regional.xsl | e646b82d36a2273dbbd90138b6fc367b | 31408 |
| util/style/ectd-2-0.xsl | 3a07a202455e954a2eb203c5bb443f77 | 2049 |

Files per module folder:

| Sequence | m1 | m2 | m3 | m4 | m5 |
|---|---|---|---|---|---|
| e000111/0000 | 50 | 1 | 0 | 0 | 0 |
| e000111/0001 | 5 | 0 | 0 | 0 | 0 |
| e000222/0000 | 5 | 0 | 0 | 0 | 0 |

(m1 counts include au-regional.xml itself.)

The full diagnostic output, with the first 60 lines of each regional XML, follows (line 1 starts with a UTF-8 byte-order mark):

```

===== e000111/0000
DOCTYPE: <!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd"[]>
root element: <ectd:ectd dtd-version="3.2" xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">
xmlns:xlink values: ['http://www.w3c.org/1999/xlink']
util files:
   util/dtd/au-regional.xsd 4fd79acbc42fe34ee27d05e144b1d844 13805
   util/dtd/ich-ectd-3-2.dtd 1d6f631cc6b6357f0f4fe378e5f79a27 31400
   util/dtd/xlink.xsd 52d1a3b8596e4fb61d3ec1cde24be16a 9261
   util/dtd/xml.xsd 382b0a4f7529d2c5f7b0af0aa713b0a5 5516
   util/style/au-regional.xsl e646b82d36a2273dbbd90138b6fc367b 31408
   util/style/ectd-2-0.xsl 3a07a202455e954a2eb203c5bb443f77 2049
regional XML: m1/au/au-regional.xml
  DOCTYPE: (none)
  xsi:schemaLocation: ['tga_ectd ../../util/dtd/au-regional.xsd']
  first 60 lines:
    1| ﻿<?xml version="1.0" encoding="utf-8"?>
    2| <?xml-stylesheet href="../../util/style/au-regional.xsl" type="text/xsl"?>
    3| <tga_ectd schema-version="3.1" xsi:schemaLocation="tga_ectd ../../util/dtd/au-regional.xsd" xmlns="tga_ectd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink">
    4|   <au-envelope>
    5| 	<esub-id>e000111</esub-id>
    6| 	<client-id>Pharma Inc.</client-id>
    7|     <aan>olea europaea</aan>
    8|     <aan>allium sativum</aan>
    9|     <product-name>incrediPill Rx 111</product-name>
   10|     <product-name>incrediPill OTC 111</product-name>
   11|     <artg-number>123456</artg-number>
   12|     <artg-number>654321</artg-number>
   13| 	<submission-number>PM-2017-12345-1-5</submission-number>
   14| 	<submission-number>PV</submission-number>
   15| 	<sequence-number>0000</sequence-number>
   16| 	<related-sequence-number>0000</related-sequence-number>
   17| 	<reg-activity-lead code-version="3.0" code="reg-act-lead-6" />
   18| 	<sequence-type code-version="3.0" code="seq-type-1" >
   19| 		<sequence-description code-version="3.0" code="seq-desc-2" />
   20| 	</sequence-type>
   21| 	<submission-mode>single</submission-mode>
   22| 	<email>mycontact@mai1l.com</email>  
   23|   </au-envelope>
   24|   <m1-au>
   25|     <m1-0-correspondence>
   26|       <m1-0-1-cover>
   27|         <leaf ID="Na0436adb7a2142ed80b066a6ab6f0fae" operation="new" xlink:href="100-correspondence/1001-cover/cover.pdf" checksum="b8804afc82154f4c40d373742f7d7b65" checksum-type="MD5">
   28|           <title>0000 Initial Application</title>
   29|         </leaf>
   30|       </m1-0-1-cover>
   31|       <m1-0-2-tracking-table>
   32|         <leaf ID="Nc4942ce9f6074ad08fbb137d42e7513a" operation="new" xlink:href="100-correspondence/1002-tracking/tracking.pdf" checksum="db0e5bbe667b84fb3698d1101bd20264" checksum-type="MD5">
   33|           <title>Lifecycle management tracking table</title>
   34|         </leaf>
   35|       </m1-0-2-tracking-table>
   36|     </m1-0-correspondence>
   37|     <m1-2-admin-info>
   38|       <m1-2-1-app-form>
   39|         <leaf ID="Ndc7864666be54120ad7502e49d76faec" operation="new" xlink:href="102-admin-info/1021-app-form/app-form.pdf" checksum="db4e336c3cdf91ef72dd12d922b3747d" checksum-type="MD5">
   40|           <title>0000 Application form</title>
   41|         </leaf>
   42|       </m1-2-1-app-form>
   43|       <m1-2-2-pre-sub-details>
   44|         <leaf ID="N1d78d74641fc4671b469a5bed7b2f804" operation="new" xlink:href="102-admin-info/1022-pre-sub/pre-submission-details.pdf" checksum="30a103ced3deef2aff1d89e66299f3d0" checksum-type="MD5">
   45|           <title>Pre-submission details</title>
   46|         </leaf>
   47|       </m1-2-2-pre-sub-details>
   48|       <m1-2-3-pat-cert>
   49|         <leaf ID="N9e0c360ae521426688146e5e0cbb3c58" operation="new" xlink:href="102-admin-info/1023-patent/patent-certification.pdf" checksum="0d994cdcb0cc7abf863e6f3ad938a832" checksum-type="MD5">
   50|           <title>Patent certification</title>
   51|         </leaf>
   52|       </m1-2-3-pat-cert>
   53|     </m1-2-admin-info>
   54|     <m1-3-med-info>
   55|       <m1-3-1-pi>
   56|         <m1-3-1-1-pi-clean>
   57|           <leaf ID="Na6aaaf4275f04e7daf62eba3caa04800" operation="new" xlink:href="103-med-info/1031-pi/10311-pi-clean/pi-clean.pdf" checksum="4a06148827ff2203ed298f2a680270ca" checksum-type="MD5">
   58|             <title>Product information - clean</title>
   59|           </leaf>
   60|         </m1-3-1-1-pi-clean>
regional_xml() returns: ('au', PosixPath('/tmp/tga/data/AU 3.1 eCTD Sample Submissions/e000111/0000/m1/au/au-regional.xml'))
files per module: {'m1': 50, 'm2': 1, 'm3': 0, 'm4': 0, 'm5': 0}
ICH-Q36-13 failures shown: 49 (list capped at 50)
  of these, present on disk: 49; referenced by an xlink:href leaf in the regional XML: 49; not referenced there: []
  index.xml leaves: 2; regional XML leaves: 49; sample regional hrefs: ['100-correspondence/1001-cover/cover.pdf', '100-correspondence/1002-tracking/tracking.pdf', '102-admin-info/1021-app-form/app-form.pdf']
  m1-m5 files on disk: 51; m1 files: 50
ICH-FMT-03 warnings shown: 49

===== e000111/0001
DOCTYPE: <!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd"[]>
root element: <ectd:ectd dtd-version="3.2" xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">
xmlns:xlink values: ['http://www.w3c.org/1999/xlink']
util files:
   util/dtd/au-regional.xsd 4fd79acbc42fe34ee27d05e144b1d844 13805
   util/dtd/ich-ectd-3-2.dtd 1d6f631cc6b6357f0f4fe378e5f79a27 31400
   util/dtd/xlink.xsd 52d1a3b8596e4fb61d3ec1cde24be16a 9261
   util/dtd/xml.xsd 382b0a4f7529d2c5f7b0af0aa713b0a5 5516
   util/style/au-regional.xsl e646b82d36a2273dbbd90138b6fc367b 31408
   util/style/ectd-2-0.xsl 3a07a202455e954a2eb203c5bb443f77 2049
regional XML: m1/au/au-regional.xml
  DOCTYPE: (none)
  xsi:schemaLocation: ['tga_ectd ../../util/dtd/au-regional.xsd']
  first 60 lines:
    1| ﻿<?xml version="1.0" encoding="utf-8"?>
    2| <?xml-stylesheet href="../../util/style/au-regional.xsl" type="text/xsl"?>
    3| <tga_ectd schema-version="3.1" xsi:schemaLocation="tga_ectd ../../util/dtd/au-regional.xsd" xmlns="tga_ectd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink">
    4|   <au-envelope>
    5|     <esub-id>e000111</esub-id>
    6|     <client-id>Pharma Inc.</client-id>
    7|     <aan>olea europaea</aan>
    8|     <aan>allium sativum</aan>
    9|     <product-name>incrediPill Rx 111</product-name>
   10|     <product-name>incrediPill OTC 111</product-name>
   11|     <artg-number>123456</artg-number>
   12|     <artg-number>654321</artg-number>
   13| 	<submission-number>PM-2017-12345-1-5</submission-number>
   14|     <sequence-number>0001</sequence-number>
   15|     <related-sequence-number>0000</related-sequence-number>
   16|     <reg-activity-lead code-version="3.0" code="reg-act-lead-6" />
   17|     <sequence-type code-version="3.0" code="seq-type-45">
   18| 	    <sequence-description code-version="3.0" code="seq-desc-5">
   19| 			<data use="date">2015-04-01</data>
   20| 		</sequence-description>
   21| 	</sequence-type>
   22| 	<submission-mode>single</submission-mode>
   23| 	<email>mycontact@mail.com</email>  
   24|   </au-envelope>
   25|   <m1-au>
   26|     <m1-0-correspondence>
   27|       <m1-0-1-cover>
   28|         <leaf ID="N93ffe0519dd14703b6149317038a0852" operation="new" xlink:href="100-correspondence/1001-cover/cover.pdf" checksum="a10ee83120a068db534bd0072c7320e8" checksum-type="MD5">
   29|           <title>0001 Response to Screening</title>
   30|         </leaf>
   31|       </m1-0-1-cover>
   32|       <m1-0-2-tracking-table>
   33|         <leaf ID="Nc4942ce9f6074ad08fbb137d42e7513a" operation="replace" xlink:href="100-correspondence/1002-tracking/tracking.pdf" checksum="0dc096a17b58895008a041b1697cbbef" checksum-type="MD5" modified-file="../../../0000/m1/au/au-regional.xml#Nc4942ce9f6074ad08fbb137d42e7513a">
   34|           <title>Lifecycle management tracking table</title>
   35|         </leaf>
   36|       </m1-0-2-tracking-table>
   37|       <m1-0-3-response>
   38|         <leaf ID="Nd4942ce9f6074ad08fbb137d42e7513a" operation="new" xlink:href="100-correspondence/1003-response/response.pdf" checksum="c7c9249d578e1ff9f0980ebdd92f6c12" checksum-type="MD5">
   39|           <title>Response</title>
   40|         </leaf>
   41|       </m1-0-3-response>
   42|     </m1-0-correspondence>
   43|     <m1-4-experts>
   44|       <m1-4-1-quality>
   45|         <leaf ID="N5afdfc34ef76433cae16dfc3456dc541" operation="new" xlink:href="104-expert/1041-quality/quality.pdf" checksum="84bb1d0f34241377b395b41be4c96842" checksum-type="MD5">
   46|           <title>Expert Dr. A. Jones</title>
   47|         </leaf>
   48|       </m1-4-1-quality>
   49|       <m1-4-3-clinical>
   50|         <leaf ID="N32c04822abdb4f79b269f81751ae924f" operation="new" xlink:href="104-expert/1041-quality/quality.pdf" checksum="84bb1d0f34241377b395b41be4c96842" checksum-type="MD5">
   51|           <title>Expert Dr. A. Jones</title>
   52|         </leaf>
   53|         <leaf ID="Nba9e2cd05ca04ca39fb33e41277be3aa" operation="new" xlink:href="../../../0000/m1/au/104-expert/1042-nonclinical/nonclinical.pdf" checksum="7ef64a29ff976baf1dfd9f8652e228f5" checksum-type="MD5">
   54|           <title>Expert Dr. B. Schmidt</title>
   55|         </leaf>
   56|         <leaf ID="N88345a5375e449f080c68fc58f015a9c" operation="new" xlink:href="../../../../e000222/0000/m1/au/104-expert/1043-clinical/clinical.pdf" checksum="922833d161180729ad59c23ba2e0444e" checksum-type="MD5">
   57|           <title>Expert Dr. C. Smith</title>
   58|         </leaf>
   59|       </m1-4-3-clinical>
   60|     </m1-4-experts>
regional_xml() returns: ('au', PosixPath('/tmp/tga/data/AU 3.1 eCTD Sample Submissions/e000111/0001/m1/au/au-regional.xml'))
files per module: {'m1': 5, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0}
ICH-Q36-13 failures shown: 4 (list capped at 50)
  of these, present on disk: 4; referenced by an xlink:href leaf in the regional XML: 4; not referenced there: []
  index.xml leaves: 1; regional XML leaves: 7; sample regional hrefs: ['100-correspondence/1001-cover/cover.pdf', '100-correspondence/1002-tracking/tracking.pdf', '100-correspondence/1003-response/response.pdf']
  m1-m5 files on disk: 5; m1 files: 5
ICH-FMT-03 warnings shown: 4

===== e000222/0000
DOCTYPE: <!DOCTYPE ectd:ectd SYSTEM "util/dtd/ich-ectd-3-2.dtd"[]>
root element: <ectd:ectd dtd-version="3.2" xmlns:ectd="http://www.ich.org/ectd" xmlns:xlink="http://www.w3c.org/1999/xlink">
xmlns:xlink values: ['http://www.w3c.org/1999/xlink']
util files:
   util/dtd/au-regional.xsd 4fd79acbc42fe34ee27d05e144b1d844 13805
   util/dtd/ich-ectd-3-2.dtd 1d6f631cc6b6357f0f4fe378e5f79a27 31400
   util/dtd/xlink.xsd 52d1a3b8596e4fb61d3ec1cde24be16a 9261
   util/dtd/xml.xsd 382b0a4f7529d2c5f7b0af0aa713b0a5 5516
   util/style/au-regional.xsl e646b82d36a2273dbbd90138b6fc367b 31408
   util/style/ectd-2-0.xsl 3a07a202455e954a2eb203c5bb443f77 2049
regional XML: m1/au/au-regional.xml
  DOCTYPE: (none)
  xsi:schemaLocation: ['tga_ectd ../../util/dtd/au-regional.xsd']
  first 60 lines:
    1| ﻿<?xml version="1.0" encoding="utf-8"?><?xml-stylesheet href="../../util/style/au-regional.xsl" type="text/xsl"?>
    2| <tga_ectd schema-version="3.1" xsi:schemaLocation="tga_ectd ../../util/dtd/au-regional.xsd" xmlns="tga_ectd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xlink="http://www.w3.org/1999/xlink">
    3|   <au-envelope>
    4|     <esub-id>e000222</esub-id>
    5|     <client-id>Pharma Inc.</client-id>
    6|     <aan>olea europaea</aan>
    7|     <aan>allium sativum</aan>
    8|     <product-name>incrediPill Rx 222</product-name>
    9|     <product-name>incrediPill OTC 222</product-name>
   10| 	<submission-number>PM-2017-22222-1-5</submission-number>
   11| 	<sequence-number>0000</sequence-number>
   12| 	<related-sequence-number>0000</related-sequence-number>
   13|     <reg-activity-lead code-version="3.0" code="reg-act-lead-6" />
   14|     <sequence-type code-version="3.0" code="seq-type-6">
   15| 		<sequence-description code-version="3.0" code="seq-desc-2" />
   16| 	</sequence-type> 
   17| 	<submission-mode>single</submission-mode>
   18| 	<email>mycontact@mail.com</email>  
   19|   </au-envelope>
   20|   <m1-au>
   21|     <m1-0-correspondence>
   22|       <m1-0-1-cover>
   23|         <leaf ID="Ncda86abd82a0429ba8dd61adb9111f17" operation="new" xlink:href="100-correspondence/1001-cover/cover.pdf" checksum="0c6ec67029e7181cdc235eb0fd5d49d2" checksum-type="MD5">
   24|           <title>0000 Cover letter</title>
   25|         </leaf>
   26|       </m1-0-1-cover>
   27|       <m1-0-2-tracking-table>
   28|         <leaf ID="N874d9776bea94b52968b8bdd1510212a" operation="new" xlink:href="100-correspondence/1002-tracking/tracking.pdf" checksum="cc40d9a0780d9b114f19a79f6cb9762b" checksum-type="MD5">
   29|           <title>Lifecycle management tracking table</title>
   30|         </leaf>
   31|       </m1-0-2-tracking-table>
   32|     </m1-0-correspondence>
   33|     <m1-2-admin-info>
   34|       <m1-2-1-app-form>
   35|         <leaf ID="N08b624b4c1d14546ac573ff616c4af25" operation="new" xlink:href="102-admin-info/1021-app-form/app-form.pdf" checksum="60986fdb13f1fa9aef98d60d83a98d8f" checksum-type="MD5">
   36|           <title>0000 Application form</title>
   37|         </leaf>
   38|       </m1-2-1-app-form>
   39|     </m1-2-admin-info>
   40|     <m1-4-experts>
   41|       <m1-4-3-clinical>
   42|         <leaf ID="Ne0eeb59ae2f74ba5832965154db4cc13" operation="new" xlink:href="104-expert/1043-clinical/clinical.pdf" checksum="922833d161180729ad59c23ba2e0444e" checksum-type="MD5">
   43|           <title>Expert Dr. C. Smith</title>
   44|         </leaf>
   45|       </m1-4-3-clinical>
   46|     </m1-4-experts>
   47|   </m1-au>
   48| </tga_ectd>
regional_xml() returns: ('au', PosixPath('/tmp/tga/data/AU 3.1 eCTD Sample Submissions/e000222/0000/m1/au/au-regional.xml'))
files per module: {'m1': 5, 'm2': 0, 'm3': 0, 'm4': 0, 'm5': 0}
ICH-Q36-13 failures shown: 4 (list capped at 50)
  of these, present on disk: 4; referenced by an xlink:href leaf in the regional XML: 4; not referenced there: []
  index.xml leaves: 1; regional XML leaves: 4; sample regional hrefs: ['100-correspondence/1001-cover/cover.pdf', '100-correspondence/1002-tracking/tracking.pdf', '102-admin-info/1021-app-form/app-form.pdf']
  m1-m5 files on disk: 5; m1 files: 5
ICH-FMT-03 warnings shown: 4
```

## 6. Whole-package check

`package.validate_files([(name, bytes) for each of the 86 files in the zip], 'tga-au31')`: 2.23 s, `ok=False`, HTML of 15,779 characters.

`sequences` rows:

```
{"sequence": "0000", "region": "ich", "m1": "au", "ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23", "ich": {"ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23"}}
{"sequence": "0000", "region": "ich", "m1": "au", "ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23", "ich": {"ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23"}}
{"sequence": "0001", "region": "ich", "m1": "au", "ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23", "ich": {"ok": false, "counts": {"pass": 21, "fail": 1, "warning": 1, "not_run": 0}, "coverage": "23/23"}}
```

The order in which `package.sequences()` put them on this run, with the `previous` list each one was given:

```
AU 3.1 eCTD Sample Submissions/e000111/0000 <- previous passed: []
AU 3.1 eCTD Sample Submissions/e000222/0000 <- previous passed: ['AU 3.1 eCTD Sample Submissions/e000111/0000']
AU 3.1 eCTD Sample Submissions/e000111/0001 <- previous passed: ['AU 3.1 eCTD Sample Submissions/e000111/0000', 'AU 3.1 eCTD Sample Submissions/e000222/0000']
```

`region` is `ich` because only the ICH layer ran. `m1` is `au`. The rows match the per-sequence results above. The first two rows are both
`0000`, and the program gives nothing that says which application each belongs to. The order of the two `0000` folders comes from
`Path.rglob` order followed by a stable sort on the folder name.

## 7. Time per step

| Step | Time |
|---|---|
| pip install (mac/requirements.txt) | 18.5 s |
| pytest test_global_ectd.py | 1.1 s (error); 4.2 s (22 passed, after the extra packages) |
| folder listing | 11.6 s reset, then a successful retry |
| zip download | 4.6 s |
| unzip | 0.04 s |
| CLI e000111/0000, e000111/0001, e000222/0000 | 2.26 s, 0.42 s, 0.45 s |
| Python validate (same order) | 2.12 s, 0.20 s, 0.13 s |
| package.validate_files | 2.23 s |

## 8. After the fixes (re-run at commit 90eaf8a, the same zip, SHA-256 confirmed)

What the run above found was fixed in two commits: daa8d67 (regional leaves read in any namespace; a leaf pointing into an earlier
sequence or another application followed to where it points; each application's lifecycle kept apart, rows naming their application)
and 90eaf8a (the «w3c.org» xlink rule applies to the ICH backbone only: the TGA's au-regional.xsd uses the W3C's own namespace, and
the package comparison reads those hrefs too). Each fix has a test that fails without it. The re-run, in the same work session:

| Sequence | previous | pass | fail | warning | not run | ok |
|---|---|---|---|---|---|---|
| e000111/0000 | — | 22 | 0 | 1 | 0 | yes |
| e000111/0001 | e000111/0000 | 22 | 0 | 1 | 0 | yes |
| e000222/0000 | — | 22 | 0 | 1 | 0 | yes |

- The only non-pass result left in each is ICH-FMT-03 (fonts not embedded: Tahoma, Times New Roman) — what the sample's PDFs are.
- ICH-Q36-07 and ICH-Q36-13 pass. The package check: ok, rows e000111/0000, e000111/0001, e000222/0000, each with its application.
- `package.leaves()` reads 51, 7 and 5 leaves' files (49, 6 and 4 regional); in e000111/0001 two «new» leaves point to the same file
  (104-expert/1041-quality/quality.pdf), which the specification allows (one file, several leaves), so it is not flagged.
