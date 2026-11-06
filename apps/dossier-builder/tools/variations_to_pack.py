#!/usr/bin/env python3
"""Bootstrap the variations pack from the EDA Variation Self-Guided Tool snapshot (Human section only).
  python3 tools/variations_to_pack.py ../../docs/ctd/data/EDA_VariationTool_2026-11-06.csv rulepacks/eda.variations.gl026.v6"""
import csv, re, sys, pathlib, yaml


def split(txt):
    txt = (txt or '').strip()
    if not txt or re.match(r'^1\.\s*No requirements needed', txt, re.I):
        return []
    parts = re.split(r'(?:^|\n|\s)(?=\d{1,2}\s*[.)-]\s*[A-Z(])', txt)
    out = [re.sub(r'^\d{1,2}\s*[.)-]\s*', '', p).strip(' ,;\n') for p in parts]
    return [p for p in out if p]


src, dst = sys.argv[1], pathlib.Path(sys.argv[2])
rows = [r for r in csv.DictReader(open(src, encoding='utf-8-sig')) if r['Section'] == 'Human']
items = []
for r in rows:
    pac = r['Procedure type (PAC)'].strip().upper().replace(' ', '')
    assert pac in ('PAC-N', 'PAC-A', 'PAC-B', 'PAC-II'), (r['ID'], pac)
    items.append({'id': f"H-{int(r['ID']):02d}", 'group': r['Main group'].strip(), 'type': r['Variation type'].strip(),
                  'request': r['Variation request'].strip(), 'pac': pac, 'conditions': split(r['Conditions to be fulfilled']),
                  'requirements': split(r['Requirements to be fulfilled']),
                  'source': {'doc': 'EDA Variation Self-Guided Tool (snapshot 06/11/2026)', 'row': int(r['ID'])}})
dst.mkdir(parents=True, exist_ok=True)
(dst / 'pack.yaml').write_text(yaml.safe_dump({
    'id': 'eda.variations.gl026.v6', 'status': 'in-force',
    'title': {'en': 'EDA human variations — classes, conditions, requirements', 'ar': 'تغييرات المستحضرات البشرية — التصنيف والشروط والمتطلبات'},
    'sources': ['GL.CAPP.026 v6 (variations, 6th ed.)', 'EDA Variation Self-Guided Tool v1.0 (eservices.edaegypt.gov.eg/EDAVariationTool/)',
                'NP.CAPP.112 v1 (variation → CTD sections)', 'EG eCTD TG draft Annex 6 (submission types)'],
    'class_order': ['PAC-N', 'PAC-A', 'PAC-B', 'PAC-II'],
    'grouping_rule': {'en': 'A group of variations is classified by its highest class.', 'source': 'GL.CAPP.026 v6'},
    'ectd_submission_type': {'PAC-N': 'var-pac-n', 'PAC-A': 'var-pac-a', 'PAC-B': 'var-pac-b', 'PAC-II': 'var-pac-ii'},
}, allow_unicode=True, sort_keys=False), encoding='utf-8')
with open(dst / 'variations.yaml', 'w', encoding='utf-8') as f:
    f.write('# Generated from docs/ctd/data/EDA_VariationTool_2026-11-06.csv (Human, 90 rows) by tools/variations_to_pack.py\n')
    yaml.safe_dump(items, f, allow_unicode=True, sort_keys=False, width=110)
print(len(items), 'variations')
