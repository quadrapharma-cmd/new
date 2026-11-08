"""Assessor knowledge pack: loading, linting and the question model."""
import json
import pathlib
import yaml
from .. import expr, packs

REVIEW_FIELDS = packs.PROFILE_FIELDS | {'reliance', 'strictness'}
SEVERITIES = ['critical', 'major', 'minor', 'note']
VERDICTS = ['adequate', 'deficient', 'not_assessable']


class ReviewPack:
    def __init__(self, meta, questions, path):
        self.meta, self.questions, self.path = meta, questions, path
        self.by_id = {q['id']: q for q in questions}

    @property
    def id(self):
        return self.meta['id']

    @property
    def version(self):
        return str(self.meta.get('version', ''))

    def departments(self):
        return self.meta['departments']

    def dept(self, dept_id):
        return next((d for d in self.meta['departments'] for _ in [0] if d['id'] == dept_id), None)

    def layers_for(self, strictness):
        s = self.meta['strictness'].get(strictness) or self.meta['strictness']['international']
        return set(s['layers'])

    def track(self, key):
        return self.meta['tracks'].get(key)

    def counts(self):
        by_dept, by_layer = {}, {}
        for q in self.questions:
            by_dept[q['dept']] = by_dept.get(q['dept'], 0) + 1
            by_layer[q['layer']] = by_layer.get(q['layer'], 0) + 1
        return {'total': len(self.questions), 'by_dept': by_dept, 'by_layer': by_layer,
                'provisional': sum(1 for q in self.questions if q.get('provisional'))}


def load(pack_id='eda.review.v1', packs_dir=packs.PACKS_DIR):
    d = pathlib.Path(packs_dir) / pack_id
    meta = yaml.safe_load((d / 'pack.yaml').read_text(encoding='utf-8'))
    questions = []
    for name in meta['files']:
        p = d / name
        if not p.exists():
            continue
        items = yaml.safe_load(p.read_text(encoding='utf-8')) or []
        for q in items:
            q['_file'] = name
            questions.append(q)
    return ReviewPack(meta, questions, d)


def schema(pack):
    return json.loads((pack.path / 'schema.json').read_text(encoding='utf-8'))


def lint(pack, requirements_pack=None, checks=None):
    """Problems as strings (empty = clean). Every question needs a source; the international layer needs an anchor;
    expressions must compile against the review fields; slots must exist in the requirements pack; data checks must exist."""
    import jsonschema
    v = jsonschema.Draft202012Validator(schema(pack))
    req_ids = {r['id'] for r in requirements_pack.requirements} if requirements_pack else None
    problems, ids = [], set()
    for q in pack.questions:
        qid = q.get('id', '?')
        body = {k: v_ for k, v_ in q.items() if not k.startswith('_')}
        for e in v.iter_errors(body):
            problems.append(f"{qid} ({q.get('_file')}): schema: {e.message}")
        if qid in ids:
            problems.append(f'{qid}: duplicate id')
        ids.add(qid)
        try:
            names = expr.names(q.get('applies', 'true'))
            unknown = names - REVIEW_FIELDS
            if unknown:
                problems.append(f'{qid}: applies reads unknown fields {sorted(unknown)}')
        except expr.ExprError as e:
            problems.append(f'{qid}: applies: {e}')
        if not (q.get('source') or {}).get('code'):
            problems.append(f'{qid}: no source')
        if q.get('layer') == 'intl' and not (q.get('anchor') or {}).get('code'):
            problems.append(f'{qid}: international layer without an anchor')
        ev, auto = q.get('evidence') or {}, q.get('auto') or {'kind': 'none'}
        if auto['kind'] == 'text' and not ev.get('keywords'):
            problems.append(f'{qid}: text check without keywords')
        if auto['kind'] in ('text', 'slot') and not ev.get('slots'):
            problems.append(f"{qid}: {auto['kind']} check without slots")
        if auto['kind'] == 'data':
            if not auto.get('check'):
                problems.append(f'{qid}: data check without a check name')
            elif checks is not None and auto['check'] not in checks:
                problems.append(f"{qid}: unknown data check {auto['check']}")
        if req_ids is not None:
            for s in ev.get('slots') or []:
                if s not in req_ids:
                    problems.append(f'{qid}: unknown slot {s}')
    return problems
