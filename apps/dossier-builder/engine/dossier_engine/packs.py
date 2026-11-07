"""Rule-pack loading and linting."""
import json
import pathlib
import yaml
from . import expr

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKS_DIR = ROOT / 'rulepacks'
PROFILE_FIELDS = {'dossier_kind', 'origin', 'licence', 'activity', 'route', 'reference_status',
                  'pharmacopoeial', 'dosage_specifics', 'leaflet', 'store_separate_from_factory',
                  'biological', 'biological_origin_materials', 'novel_excipient',
                  'column', 'api_options', 'api_count',
                  'admin_route', 'local_action', 'aqueous_solution', 'bcs_waiver', 'biowaiver', 'local_equivalence'}
API_FIELDS = {'name', 'manufacturer', 'option'}


class Pack:
    def __init__(self, meta, requirements, path):
        self.meta, self.requirements, self.path = meta, requirements, path
        self.by_id = {r['id']: r for r in requirements}

    @property
    def id(self):
        return self.meta['id']


def load(pack_id, packs_dir=PACKS_DIR):
    d = pathlib.Path(packs_dir) / pack_id
    meta = yaml.safe_load((d / 'pack.yaml').read_text(encoding='utf-8'))
    reqs = yaml.safe_load((d / 'requirements.yaml').read_text(encoding='utf-8'))
    return Pack(meta, reqs, d)


def schema():
    return json.loads((PACKS_DIR / 'schema' / 'requirement.schema.json').read_text())


def lint(pack):
    """Returns a list of problems (empty = clean)."""
    import jsonschema
    problems = []
    v = jsonschema.Draft202012Validator(schema())
    ids = set()
    for r in pack.requirements:
        rid = r.get('id', '?')
        for e in v.iter_errors(r):
            problems.append(f'{rid}: schema: {e.message}')
        if rid in ids:
            problems.append(f'{rid}: duplicate id')
        ids.add(rid)
        exprs = [('applies', r.get('applies', 'true'), PROFILE_FIELDS)]
        for col, cell in (r.get('required') or {}).items():
            if isinstance(cell, dict):
                cases = cell.get('cases', [])
                if 'when' in cases[-1]:
                    problems.append(f'{rid}/{col}: last case must be the default (no when)')
                exprs += [(f'required.{col}', c['when'], PROFILE_FIELDS) for c in cases if 'when' in c]
        per = r.get('per')
        if per and 'where' in per:
            exprs.append(('per.where', per['where'], API_FIELDS))
        for c in r.get('item_cases', []):
            exprs.append(('item_cases', c['when'], API_FIELDS | PROFILE_FIELDS))
        if r.get('item_cases') and not per:
            problems.append(f'{rid}: item_cases without per')
        for where, src, allowed in exprs:
            try:
                unknown = expr.names(src) - allowed
            except expr.ExprError as e:
                problems.append(f'{rid}: {where}: {e}')
                continue
            if unknown:
                problems.append(f'{rid}: {where}: unknown field(s) {sorted(unknown)}')
        if not r.get('sources'):
            problems.append(f'{rid}: no source citation')
    return problems
