"""Assessor knowledge pack: loading, linting and the question model.

For any authority (the review is global): a question is «core» when an assessor of any authority asks it — its basis is an ICH, WHO,
EMA, FDA or pharmacopoeial text (its `anchor`), its wording names nothing Egyptian, and it reads only the common CTD's items
(Modules 2–5, the same in every country's pack); every other question is EDA's own («eda»). A dossier for EDA gets every question,
as before; a dossier for another authority gets the core questions, with the departments named for any authority, and the
authority's own Module 1 items come from its requirements pack (the missing-item findings)."""
import json
import pathlib
import re
import yaml
from dossier_engine.yamlfast import load as yload
from .. import expr, packs

REVIEW_FIELDS = packs.PROFILE_FIELDS | {'reliance', 'strictness'}
EGYPT_ID = 'EG-EDA'
EGYPT_DEPTS = {'gates', 'reliance'}            # Egypt's gates (inspection, pharmacovigilance, pricing) and its reliance route
EGYPT_ONLY_Q = {'screening'} | EGYPT_DEPTS      # its Module 1 screening desk asks EDA's own checklist (NP.CAPP.065)
EGYPT_FIELDS = {'reliance', 'store_separate_from_factory', 'licence'}
EG_WORDS = re.compile(r'\b(EDA|Egypt|Egyptian|CADC|decree|NODCAR)\b|مصر|المصري|هيئة الدواء'
                      r'|\bAnnex (?:I|II|III|IV|V|VI|VII|VIII|IX|X)\b|\bGuide (?:I|II|III)\b|\bsections? \d+\.\d+', re.I)
# (an EDA guideline's own annexes — Roman numerals, «Guide I/II» — and its section numbers make a question EDA's: WHO numbers its
# annexes, and ICH's sections are cited in the anchor, never in the question)
INTL = re.compile(r'\s*(ICH|WHO|EMA|FDA|USP|Ph\.?\s?Eur|PIC/S)', re.I)
COMMON_PACK = 'ich.ctd.m4.v1'                   # the common CTD (Modules 2–5) every authority's pack stands on
SEVERITIES = ['critical', 'major', 'minor', 'note']
VERDICTS = ['adequate', 'deficient', 'not_assessable']


class ReviewPack:
    def __init__(self, meta, questions, path, common=None):
        self.meta, self.questions, self.path = meta, questions, path
        self.by_id = {q['id']: q for q in questions}
        self.common = common                    # the ids of the common CTD's items (None: not known, the slot rule is not applied)
        self._scope = {}

    def scope(self, q):
        """'core' (any authority) or 'eda' (EDA's own); an explicit `scope` in the pack wins."""
        if q['id'] not in self._scope:
            self._scope[q['id']] = q.get('scope') or scope_of(q, self.common)
        return self._scope[q['id']]

    def questions_for(self, authority=None):
        """The questions an assessor of this authority asks: every question for EDA, the core ones for any other."""
        if is_egypt(authority):
            return self.questions
        return [q for q in self.questions if self.scope(q) == 'core']

    def departments_for(self, authority=None):
        """EDA's departments for EDA; for any other authority the same desks named for any authority (pack.yaml
        `departments_any`), without Egypt's gates and reliance route."""
        if is_egypt(authority):
            return self.departments()
        names = self.meta.get('departments_any') or {}
        return [{**d, **names[d['id']]} for d in self.departments() if d['id'] not in EGYPT_DEPTS and d['id'] in names]

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

    def counts(self, authority=None):
        by_dept, by_layer, by_scope = {}, {}, {}
        for q in self.questions:
            by_scope[self.scope(q)] = by_scope.get(self.scope(q), 0) + 1
        qs = self.questions_for(authority)
        for q in qs:
            by_dept[q['dept']] = by_dept.get(q['dept'], 0) + 1
            by_layer[q['layer']] = by_layer.get(q['layer'], 0) + 1
        return {'total': len(qs), 'by_dept': by_dept, 'by_layer': by_layer, 'by_scope': by_scope,
                'provisional': sum(1 for q in qs if q.get('provisional'))}


def authority_label(authority):
    """The authority's name for a letter or a prompt: «the receiving authority» for the general pack of any other country."""
    if not authority:
        return {'en': 'the Egyptian Drug Authority', 'ar': 'هيئة الدواء المصرية'}
    if authority.get('id') == 'OTHER':
        return {'en': 'the receiving authority', 'ar': 'الجهة المستقبِلة'}
    return authority.get('name') or {'en': authority.get('id', ''), 'ar': authority.get('id', '')}


def is_egypt(authority):
    """No authority given is EDA (the pack's own); else its id."""
    return not authority or (authority.get('id') if isinstance(authority, dict) else authority) == EGYPT_ID


def scope_of(q, common=None):
    """'core' when an assessor of any authority asks the question: an ICH/WHO/EMA/FDA/pharmacopoeial basis (its anchor), no
    Egyptian department, field or wording, and only the common CTD's items as evidence; else 'eda'."""
    if q.get('dept') in EGYPT_ONLY_Q or not INTL.match((q.get('anchor') or {}).get('code') or ''):
        return 'eda'
    text = ' '.join(str((q.get(k) or {}).get(lang, '')) for k in ('title', 'question', 'deficiency', 'adequate') for lang in ('en', 'ar'))
    if EG_WORDS.search(text):
        return 'eda'
    try:
        if expr.names(q.get('applies', 'true')) & EGYPT_FIELDS:
            return 'eda'
    except expr.ExprError:
        return 'eda'
    slots = (q.get('evidence') or {}).get('slots') or []
    if common is not None and any(s not in common for s in slots):
        return 'eda'
    return 'core'


def load(pack_id='eda.review.v1', packs_dir=packs.PACKS_DIR):
    d = pathlib.Path(packs_dir) / pack_id
    meta = yload((d / 'pack.yaml').read_text(encoding='utf-8'))
    questions = []
    for name in meta['files']:
        p = d / name
        if not p.exists():
            continue
        items = yload(p.read_text(encoding='utf-8')) or []
        for q in items:
            q['_file'] = name
            questions.append(q)
    try:
        common = {r['id'] for r in packs.load(COMMON_PACK, packs_dir).requirements}
    except Exception:                                   # noqa: BLE001 — without the common CTD the slot rule is not applied
        common = None
    return ReviewPack(meta, questions, d, common)


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
