#!/usr/bin/env python3
"""One-time bootstrap: EDA company checklist (xlsx) -> rule pack eda.ctd.nta065.v5.

The generated YAML is the source of truth afterwards (rules are data). This
script is kept so the pack can be regenerated if the checklist is re-issued;
tests/test_pack_vs_checklist.py keeps the two in agreement.

Usage: python3 tools/xlsx_to_pack.py <checklist.xlsx> <out_dir>
"""
import sys, pathlib, re
import openpyxl, yaml

SHEET = 'قائمة المستندات Checklist'

# ---- logic the matrix cannot express (from the checklist "Condition" column) ----
# applies: safe expression over the profile (engine/dossier_engine/expr.py)
APPLIES = {
    'M1-07': "activity == 're_registration'",
    'M1-10': "leaflet == 'non_english'",
    'M1-13': "column == 'G_LOC'",
    'M1-14': "column != 'G_LOC' or licence == 'under_licence'",
    'M1-18': "column == 'G_LOC' or licence == 'imported_bulk'",
    'M1-20': "licence in ['toll', 'f_toll']",
    'M1-23': "store_separate_from_factory",
    'M1-25': "licence in ['toll', 'f_toll']",
    'M1-26': "licence == 'under_licence'",
    'M1-27': "activity == 're_registration'",
    'M1-27b': "licence == 'imported_bulk'",
    'M1-28': "'powder_inj_with_solvent' in dosage_specifics",
    'M1-29': "pharmacopoeial",
    'M1-30': "'DMF' in api_options",
    'M1-33': "'coated' in dosage_specifics or 'capsule_hard' in dosage_specifics or 'pellets' in dosage_specifics or 'premix' in dosage_specifics",
    'M1-34': "route == 'rolling'",
    'M1-39': "'CEP' in api_options",
    'M1-40': "'CEP' in api_options",
    'S-16': "'CEP' in api_options",
    'A-02': "biological_origin_materials",
    'A-03': "novel_excipient",
}
# level cases evaluated before the matrix cell (first match wins)
CASES = {
    'M1-12': {'I': [{'when': "activity == 're_registration'", 'level': 'R'}, {'level': 'NR'}],
              'G_IMP': [{'when': "activity == 're_registration'", 'level': 'R'}, {'level': 'NR'}]},
    # The matrix marks CEP items "O" because the CEP route itself is optional;
    # once the company chooses a CEP for an API they are mandatory.
    'M1-39': {c: [{'when': "'CEP' in api_options", 'level': 'R'}, {'level': 'O'}] for c in ('I', 'G_IMP', 'G_LOC')},
    'M1-40': {c: [{'when': "'CEP' in api_options", 'level': 'R'}, {'level': 'O'}] for c in ('I', 'G_IMP', 'G_LOC')},
}
# per-item expansion (one slot per API manufacturer, optionally filtered)
PER = {k: {'over': 'apis'} for k in
       ['M1-13', 'M1-35', 'M1-38'] + [f'S-{i:02d}' for i in range(1, 16)]}
PER.update({'M1-30': {'over': 'apis', 'where': "option == 'DMF'"},
            'M1-39': {'over': 'apis', 'where': "option == 'CEP'"},
            'M1-40': {'over': 'apis', 'where': "option == 'CEP'"},
            'S-16': {'over': 'apis', 'where': "option == 'CEP'"}})
# per-API option variants (CTD Quality guideline v2 §S, KB §Option 2)
ITEM_CASES = {
    'S-05': [{'when': "option == 'CEP'", 'level': 'NR',
              'reason': {'en': 'Covered by the CEP (manufacture is assessed by EDQM).',
                         'ar': 'مغطى بشهادة الـ CEP (التصنيع مُقيَّم من EDQM).'},
              'provenance': 'ASSUMPTION'}],
    'S-07': [{'when': "option == 'CEP'", 'level': 'NR',
              'reason': {'en': 'Impurity profile covered by the CEP; add only impurities not controlled by it under S.4.1.',
                         'ar': 'الشوائب مغطاة بالـ CEP؛ أضف فقط ما لا تضبطه الشهادة في S.4.1.'},
              'provenance': 'ASSUMPTION'}],
}
CONFIRM = {'M5-07'}  # "R if applicable" -> required, user confirms applicability
OVERRIDE_CLASS = {'M1-01': 'generated', 'R-01': 'executed_record', 'M1-36': 'company_letter'}
LETTERS = {'M1-10', 'M1-15', 'M1-25', 'M1-31', 'M1-32', 'M1-40'}


def norm_cell(v):
    v = (v or '').strip()
    if v in ('R', 'NR', 'O'):
        return v
    if v == '—':
        return 'R'           # tool-generated, always present
    if v == 'R*':
        return 'R'           # condition carried by `applies`
    if v == 'R if applicable':
        return 'R'
    if v == 'NR (new) / R (re-reg)':
        return 'CASES'
    raise ValueError(f'unknown matrix cell {v!r}')


def doc_class(rid, produced, rebuild, module):
    if rid in OVERRIDE_CLASS:
        return OVERRIDE_CLASS[rid]
    if produced == 'Third party':
        return 'third_party_certificate'
    if produced == 'EDA':
        return 'eda_document'
    if produced.startswith('Tool'):
        return 'generated'
    if rid in LETTERS:
        return 'company_letter'
    if rebuild.startswith('Yes'):
        return 'generated'
    return 'company_technical'


def parse_source(s):
    out = []
    for part in [p.strip() for p in (s or '').split(';') if p.strip()]:
        out.append(part)
    return out


def main(xlsx, out_dir):
    wb = openpyxl.load_workbook(xlsx)
    ws = wb[SHEET]
    reqs, section = [], None
    for row in ws.iter_rows(min_row=2, values_only=True):
        rid = row[0]
        if rid and not row[1] and str(rid).startswith(('MODULE',)):
            section = str(rid)
            continue
        if not rid:
            continue
        rid = str(rid).strip()
        cells = {'I': row[5], 'G_IMP': row[6], 'G_LOC': row[7]}
        matrix = {k: str(v).strip() for k, v in cells.items()}
        required = {}
        for col, v in matrix.items():
            n = norm_cell(v)
            if rid in CASES and col in CASES[rid]:
                required[col] = {'cases': CASES[rid][col]}
            elif n == 'CASES':
                raise ValueError(f'{rid}/{col}: compound cell without CASES entry')
            else:
                required[col] = n
        produced = str(row[10] or '').strip()
        rebuild = str(row[12] or '').strip()
        r = {
            'id': rid,
            'module': int(row[1]),
            'group': section,
            'ctd': {'nta065_v5': str(row[2]).strip()},
            'title': {'en': str(row[3]).strip(), 'ar': str(row[4]).strip()},
            'matrix': matrix,
            'applies': APPLIES.get(rid, 'true'),
            'required': required,
            'doc_class': doc_class(rid, produced, rebuild, int(row[1])),
            'produced_by': produced,
            'rebuild': {'verdict': rebuild, 'needs': str(row[13] or '').strip()},
            'condition_note': str(row[9] or '').strip() or None,
            'acceptance_text': str(row[11] or '').strip() or None,
            'sources': parse_source(row[14]),
            'provenance': 'EG-IN-FORCE' if 'NP.CAPP.065' in str(row[14]) or 'guideline v2' in str(row[14]) else 'EG-DRAFT',
        }
        if rid in PER:
            r['per'] = PER[rid]
        if rid in ITEM_CASES:
            r['item_cases'] = ITEM_CASES[rid]
        if rid in CONFIRM:
            r['confirm_applicability'] = True
        if r['applies'] != 'true' or rid in CASES or rid in ITEM_CASES:
            r['logic_provenance'] = 'checklist condition column' if rid not in ITEM_CASES else 'CTD Quality guideline v2 (CEP route) — ASSUMPTION for NR'
        reqs.append({k: v for k, v in r.items() if v is not None})

    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    hdr = ('# Generated once from docs/ctd/checklist/EDA-eCTD-Company-Checklist.xlsx by\n'
           '# tools/xlsx_to_pack.py, then maintained as data. Matrix cells are verbatim\n'
           '# from NP.CAPP.065 v5 (columns I / G-Imp / G-Loc).\n')
    with open(out / 'requirements.yaml', 'w', encoding='utf-8') as f:
        f.write(hdr)
        yaml.safe_dump(reqs, f, allow_unicode=True, sort_keys=False, width=110)
    print(f'{len(reqs)} requirements -> {out / "requirements.yaml"}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
