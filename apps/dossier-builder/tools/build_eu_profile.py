#!/usr/bin/env python3
"""Build the EU eCTD 3.2.2 regional profile (EU Module 1 v3.1.1) from the official EMA files kept in docs/ctd/sources/ectd:

    python3 apps/dossier-builder/tools/build_eu_profile.py

  util/dtd, util/style    copied byte for byte from EU_M1_util_v3.1.zip (EMA eSubmission, the files a sequence must carry)
  validation-criteria.csv every criterion of EU_M1_Validation_Criteria_v8.2.xlsx (sheet «eCTD Validation Criteria»), word for word
  util-md5.txt            the MD5 of each util file: the published values the criteria 1.3–6.3 compare with

m1.csv (the Module 1 folder and file names of SPEC 3.1.1 Appendix 2, checked against the criteria's «File-Folder Structure & Names»
sheet) is kept by hand next to these files; this script does not touch it."""
import csv, hashlib, io, pathlib, zipfile

REPO = pathlib.Path(__file__).resolve().parents[3]
SRC = REPO / 'docs' / 'ctd' / 'sources' / 'ectd'
OUT = REPO / 'docs' / 'ctd' / 'ectd' / 'EU-M1-3.1.1-PROFILE'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md5s = []
    with zipfile.ZipFile(SRC / 'EU_M1_util_v3.1.zip') as z:
        for name in sorted(z.namelist()):
            if name.endswith('/'):
                continue
            data = z.read(name)
            dst = OUT / name                              # util/dtd/… and util/style/…
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            md5s.append(f'{hashlib.md5(data).hexdigest()}  {name}')
    (OUT / 'util-md5.txt').write_text('\n'.join(md5s) + '\n', encoding='ascii')

    import openpyxl
    wb = openpyxl.load_workbook(SRC / 'EU_M1_Validation_Criteria_v8.2.xlsx', read_only=True, data_only=True)
    rows = list(wb['eCTD Validation Criteria'].iter_rows(values_only=True))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['rule_id', 'number', 'category', 'type', 'rule_text', 'comments', 'lifecycle_needed', 'source'])
    n = 0
    for r in rows[1:]:
        num = str(r[0]).strip() if r[0] is not None else ''
        if not num or not num[0].isdigit():
            continue
        clean = lambda v: ' '.join(str(v or '').split())
        typ = clean(r[3])
        w.writerow([f'EU-{num}', num, clean(r[1]), 'Pass/Fail' if typ == 'P/F' else 'Best Practice', clean(r[2]), clean(r[5]),
                    'Y' if clean(r[4]).upper().startswith('Y') else '', f'EU eCTD Validation Criteria v8.2 (June 2025), criterion {num}'])
        n += 1
    (OUT / 'validation-criteria.csv').write_text(buf.getvalue(), encoding='utf-8')
    print(f'{OUT}: {len(md5s)} util files, {n} criteria')


if __name__ == '__main__':
    main()
