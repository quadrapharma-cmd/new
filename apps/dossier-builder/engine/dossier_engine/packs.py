"""Rule-pack loading and linting.

A dossier is built for one authority. Its pack gives that authority's Module 1 — the regional part: its structure, its numbering,
what each section must hold, the source it was written from — and names the common CTD it stands on (`extends`): Modules 2 to 5
are the ICH CTD, the same for every authority, with the authority's own levels where it says otherwise (`overrides`) and its own
regional items (3.2.R). The Egyptian pack is whole in itself, as it always was."""
import json
import pathlib
import yaml
from dossier_engine.yamlfast import load as yload
from . import expr

ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKS_DIR = ROOT / 'rulepacks'
PROFILE_FIELDS = {'dossier_kind', 'origin', 'licence', 'activity', 'route', 'reference_status',
                  'pharmacopoeial', 'dosage_specifics', 'leaflet', 'store_separate_from_factory',
                  'biological', 'biological_origin_materials', 'novel_excipient',
                  'column', 'api_options', 'api_count',
                  'admin_route', 'local_action', 'aqueous_solution', 'bcs_waiver', 'biowaiver', 'local_equivalence'}
API_FIELDS = {'name', 'manufacturer', 'option'}


EGYPT = {'id': 'EG-EDA', 'countries': ['EG'], 'name': {'en': 'Egyptian Drug Authority (EDA)', 'ar': 'هيئة الدواء المصرية'}}


def number(r):
    """The section number a requirement is shown under."""
    c = r.get('ctd') or {}
    return c.get('number') or c.get('nta065_v5') or next(iter(c.values()), '')


class Pack:
    def __init__(self, meta, requirements, path, base=None):
        self.meta, self.requirements, self.path, self.base = meta, requirements, path, base
        self.by_id = {r['id']: r for r in requirements}

    @property
    def id(self):
        return self.meta['id']

    @property
    def authority(self):
        """Who the dossier is for: {id, countries, name}. The Egyptian pack predates the field."""
        return self.meta.get('authority') or EGYPT

    @property
    def egypt(self):
        return self.authority.get('id') == 'EG-EDA'

    @property
    def ectd_region(self):
        """The regional eCTD 3.2.2 Module 1 the program writes for this authority: 'eg' (the provisional EG profile), 'eu' (EU Module 1
        v3.1.1, the EMA's own DTD and validation criteria v8.2), or None (CTD folders only)."""
        return {'EG-EDA': 'eg', 'EU': 'eu', 'GCC': 'gcc'}.get(self.authority.get('id'))

    @property
    def outputs(self):
        """What the program writes for this authority: its eCTD where it has one; otherwise the CTD folders, a NeeS where the countries
        table does not say «no», the ACTD where it says «yes» (rulepacks/countries.yaml)."""
        if self.ectd_region:
            return {'eg': ['ctd', 'ectd32', 'ectd40'], 'eu': ['ctd', 'ectd32'], 'gcc': ['ctd', 'ectd32', 'nees']}[self.ectd_region]
        cs = [c for c in (self.authority.get('countries') or []) if c]
        if '*' in cs:
            return ['ctd', 'nees', 'actd']                    # «any country»: the dossier's own country decides (outputs_for)
        rows = [formats_for(c) for c in cs]
        nees = not rows or any(f.get('nees', 'unknown') != 'no' for f in rows)
        actd = any(f.get('actd') == 'yes' for f in rows)
        return ['ctd'] + (['nees'] if nees else []) + (['actd'] if actd else [])

    def outputs_for(self, country=None):
        """The outputs of a dossier for `country`, as the countries table says that country takes them."""
        outs = self.outputs
        if self.ectd_region:
            return outs
        f = formats_for(country) if country else {}
        if not country and '*' in (self.authority.get('countries') or []):
            return [o for o in outs if o != 'actd']           # a country not named yet: no ACTD
        return [o for o in outs if not (o == 'nees' and f.get('nees') == 'no') and not (o == 'actd' and country and f.get('actd') != 'yes')]

    @property
    def questions(self):
        """What this authority asks beyond the common profile: [{id, title, options: [{id, en, ar}], default}]."""
        return self.meta.get('questions') or []

    def matrix_name(self):
        return self.meta.get('matrix') or {'en': 'NP.CAPP.065 matrix', 'ar': 'مصفوفة NP.CAPP.065'}


ASEAN = {'BN', 'KH', 'ID', 'LA', 'MY', 'MM', 'PH', 'SG', 'TH', 'VN'}       # the member states that take the ACTD
_COUNTRIES = None


def countries_table():
    """The countries table (rulepacks/countries.yaml, updates list item 41): what each authority takes, with its source."""
    global _COUNTRIES
    if _COUNTRIES is None:
        _COUNTRIES = yaml.safe_load((PACKS_DIR / 'countries.yaml').read_text(encoding='utf-8'))
    return _COUNTRIES


def country_row(code):
    """The table's row for a country (by its code, or as one of a group's countries), or None."""
    code = (code or '').upper()
    for r in countries_table()['countries']:
        if r['code'] == code or code in (r.get('countries') or []):
            return r
    return None


def formats_for(code):
    """{ctd, ectd32, ectd40, nees, actd: yes|no|optional|planned|unknown} for a country; {} when the table does not have it."""
    r = country_row(code)
    return dict(r['formats']) if r else {}


def load(pack_id, packs_dir=PACKS_DIR):
    d = pathlib.Path(packs_dir) / pack_id
    meta = yload((d / 'pack.yaml').read_text(encoding='utf-8'))
    reqs = yload((d / 'requirements.yaml').read_text(encoding='utf-8')) or []
    base = None
    if meta.get('extends'):                                # the common CTD under this authority's Module 1
        base = load(meta['extends'], packs_dir)
        own, over, drop = {r['id'] for r in reqs}, meta.get('overrides') or {}, set(meta.get('drop') or [])
        common = [{k: v for k, v in {**r, **over.get(r['id'], {})}.items() if v is not None}            # an override of None takes the key away
                  for r in base.requirements if r['id'] not in own and r['id'] not in drop]
        order = {id(r): i for i, r in enumerate(reqs + common)}
        reqs = sorted(reqs + common, key=lambda r: (r['module'], order[id(r)]))          # Module 1 first; each module in its own order
    return Pack(meta, reqs, d, base)


def available(packs_dir=PACKS_DIR):
    """The packs a dossier can be built on (one per authority), in the order they are offered."""
    out = []
    for d in sorted(pathlib.Path(packs_dir).iterdir()):
        if not (d / 'pack.yaml').exists() or not (d / 'requirements.yaml').exists():
            continue
        meta = yload((d / 'pack.yaml').read_text(encoding='utf-8'))
        if meta.get('kind') == 'base' or not (meta.get('authority') or meta.get('columns')):
            continue
        out.append(meta)
    return sorted(out, key=lambda m: (m.get('order', 50), m['id']))


def for_country(code, packs_dir=PACKS_DIR):
    """The pack of the authority a country's dossier goes to: the one that names the country, else the general one ('*')."""
    code, rest = (code or '').strip().upper(), None
    for m in available(packs_dir):
        countries = (m.get('authority') or EGYPT)['countries']
        if code and code in countries:
            return m
        if '*' in countries:
            rest = m
    return rest


def authorities(packs_dir=PACKS_DIR):
    """What the page offers when a dossier is started: each authority with its countries, its own questions, the sources its Module 1
    was written from and whether it is the authority's own text (`verified`) or a general layout."""
    out = []
    for m in available(packs_dir):
        au = m.get('authority') or EGYPT
        pk = load(m['id'], packs_dir)
        by_module = {}
        for r in pk.requirements:
            by_module[str(r['module'])] = by_module.get(str(r['module']), 0) + 1
        out.append({'pack': m['id'], 'id': au['id'], 'name': au['name'], 'countries': au['countries'], 'title': m['title'], 'status': m.get('status'),
                    'verified': m.get('verified', au['id'] == 'EG-EDA'), 'egypt': au['id'] == 'EG-EDA', 'questions': m.get('questions') or [],
                    'columns': m.get('columns') or {}, 'note': m.get('note'), 'valid_from': m.get('valid_from'),
                    'sources': [{k: s.get(k) for k in ('code', 'title', 'version', 'date', 'url', 'gives') if s.get(k)} for s in m.get('sources') or []],
                    'requirements': {'total': len(pk.requirements), 'by_module': by_module},
                    'outputs': pk.outputs})
    return out


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
        fields = PROFILE_FIELDS | {q['id'] for q in pack.questions}
        exprs = [('applies', r.get('applies', 'true'), fields)]
        for col, cell in (r.get('required') or {}).items():
            if isinstance(cell, dict):
                cases = cell.get('cases', [])
                if 'when' in cases[-1]:
                    problems.append(f'{rid}/{col}: last case must be the default (no when)')
                exprs += [(f'required.{col}', c['when'], fields) for c in cases if 'when' in c]
        per = r.get('per')
        if per and 'where' in per:
            exprs.append(('per.where', per['where'], API_FIELDS))
        for c in r.get('item_cases', []):
            exprs.append(('item_cases', c['when'], API_FIELDS | fields))
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
    note = pack.meta.get('module1_note')
    if note:
        try:
            unknown = expr.names(note.get('when', 'true')) - (PROFILE_FIELDS | {q['id'] for q in pack.questions})
            if unknown or not note.get('en') or not note.get('ar'):
                problems.append(f'module1_note: unknown field(s) {sorted(unknown)} or a missing text')
        except expr.ExprError as e:
            problems.append(f'module1_note: {e}')
    return problems
