"""Module 3 tables built from structured data (P2): 3.2.P.5.1, 3.2.P.5.4, 3.2.S.4.1, 3.2.S.4.4.
Values are printed exactly as entered (no rounding, no 'complies' substitution);
results that are words for a quantitative test are flagged by the cross-checks."""
from pathlib import Path
from .docx_kit import new_doc, para, table, MissingData


def _need(cond, fields):
    if not cond:
        raise MissingData(fields)


def spec_table(title, section, spec, out, product=None):
    _need(spec, ['specs'])
    d = new_doc(draft=False)
    para(d, f'{section} {title}', bold=True, size=13)
    if product:
        para(d, product)
    table(d, ['Test', 'Acceptance criteria', 'Analytical procedure'],
          [(t.get('test'), t.get('limit'), t.get('method', '')) for t in spec])
    d.save(out)
    return Path(out)


def batch_table(title, section, spec, batches, results, out, product=None):
    _need(spec, ['specs'])
    _need(batches, ['batches'])
    d = new_doc(landscape=True, draft=False)
    para(d, f'{section} {title}', bold=True, size=13)
    if product:
        para(d, product)
    table(d, ['Batch', 'Size', 'Scale', 'Manufacture date', 'Site', 'Use'],
          [(b.get('no'), b.get('size', ''), b.get('scale', ''), b.get('date', ''), b.get('site', ''), b.get('use', ''))
           for b in batches])
    para(d, '')
    table(d, ['Test', 'Acceptance criteria'] + [b['no'] for b in batches],
          [[t.get('test'), t.get('limit')] + [str((results.get(b['no']) or {}).get(t.get('test'), '—')) for b in batches]
           for t in spec])
    d.save(out)
    return Path(out)


def build(kind, data, out, item=None, product_name=None):
    specs, results, batches = data.get('specs') or {}, data.get('results') or {}, data.get('batches') or []
    if kind == 'p51':
        return spec_table('Specification(s)', '3.2.P.5.1', specs.get('product'), out, product_name)
    if kind == 'p54':
        fpp = [b for b in batches if b.get('kind', 'fpp') == 'fpp']
        return batch_table('Batch analyses', '3.2.P.5.4', specs.get('product'), fpp, results, out, product_name)
    key = f"{item['name']}|{item['manufacturer']}" if item else None
    api_spec = (specs.get('api') or {}).get(key)
    label = f"{item['name']} — {item['manufacturer']}" if item else None
    if kind == 's41':
        return spec_table('Specification', '3.2.S.4.1', api_spec, out, label)
    if kind == 's44':
        api_b = [b for b in batches if b.get('kind') == 'api' and b.get('api') == key]
        return batch_table('Batch analyses', '3.2.S.4.4', api_spec, api_b, results, out, label)
    raise ValueError(kind)
