"""Requirement resolver (02-LOGIC §5.1): profile + pack -> slots with reasons."""
from dataclasses import dataclass, field
from . import expr

LEVEL_RANK = {'NR': 0, 'O': 1, 'R': 2}


@dataclass
class Slot:
    req_id: str
    slot_id: str            # req_id or req_id@<api key>
    level: str              # R / O / NR / NA
    title: dict
    ctd: str
    doc_class: str
    module: int
    item: dict = None       # the API this slot is for (per-API expansion)
    reasons: list = field(default_factory=list)   # [{en, ar, source}]
    flags: list = field(default_factory=list)     # ASSUMPTION, CONFIRM_APPLICABILITY…

    @property
    def active(self):
        return self.level in ('R', 'O')

    def to_dict(self):
        return {k: getattr(self, k) for k in
                ('req_id', 'slot_id', 'level', 'title', 'ctd', 'doc_class', 'module', 'item', 'reasons', 'flags')}


def _cell_level(cell, env):
    if isinstance(cell, str):
        return cell, None
    for case in cell['cases']:
        if 'when' not in case or expr.evaluate(case['when'], env):
            return case['level'], case.get('when')
    raise ValueError('no default case')  # pragma: no cover (lint forbids it)


def resolve(profile, pack, validate=True, today=None):
    if validate:
        profile.validate(today=today)
    env = profile.env()
    col, col_assumed = profile.column()
    slots = []
    for r in pack.requirements:
        base = dict(req_id=r['id'], title=r['title'], ctd=r['ctd']['nta065_v5'],
                    doc_class=r['doc_class'], module=r['module'])
        src = '; '.join(r['sources'])
        flags = ['ASSUMPTION_LOCAL_INNOVATOR'] if col_assumed else []
        if r.get('confirm_applicability'):
            flags.append('CONFIRM_APPLICABILITY')
        if not expr.evaluate(r['applies'], env):
            slots.append(Slot(slot_id=r['id'], level='NA', flags=flags, reasons=[{
                'en': f"Does not apply to this product ({r['applies']})."
                      + (f" Condition: {r['condition_note']}" if r.get('condition_note') else ''),
                'ar': 'لا ينطبق على هذا المنتج'
                      + (f" — الشرط: {r['condition_note']}" if r.get('condition_note') else '.'),
                'rule': r['applies'], 'source': src}], **base))
            continue
        level, why = _cell_level(r['required'][col], env)
        reasons = [{'en': f"NP.CAPP.065 matrix column {col}: {r['matrix'][col]}"
                          + (f" (case: {why})" if why else ''),
                    'ar': f"مصفوفة NP.CAPP.065 العمود {col}: {r['matrix'][col]}", 'source': src}]
        per = r.get('per')
        if not per:
            slots.append(Slot(slot_id=r['id'], level=level, reasons=reasons, flags=flags, **base))
            continue
        items = [a for a in profile.apis
                 if 'where' not in per or expr.evaluate(per['where'], {**env, **_api_env(a)})]
        for a in items:
            ienv = {**env, **_api_env(a)}
            lvl, rs, fl = level, list(reasons), list(flags)
            for c in r.get('item_cases', []):
                if expr.evaluate(c['when'], ienv):
                    if lvl != 'NR' and c['level'] != lvl:
                        lvl = c['level']
                        rs.append({**c.get('reason', {}), 'rule': c['when'], 'source': src})
                        if c.get('provenance') == 'ASSUMPTION':
                            fl.append('ASSUMPTION')
                    break
            slots.append(Slot(slot_id=f"{r['id']}@{a.key}", level=lvl, item=_api_env(a),
                              reasons=rs, flags=fl, **base))
    return slots


def _api_env(a):
    return {'name': a.name, 'manufacturer': a.manufacturer, 'option': a.option}


def summary(slots):
    out = {'R': 0, 'O': 0, 'NR': 0, 'NA': 0}
    for s in slots:
        out[s.level] += 1
    return out


def diff(old, new):
    """02-LOGIC §5.3: added / removed / changed slots between two resolutions."""
    o = {s.slot_id: s for s in old if s.active}
    n = {s.slot_id: s for s in new if s.active}
    return {
        'added': sorted(set(n) - set(o)),
        'removed': sorted(set(o) - set(n)),
        'changed': sorted(k for k in set(o) & set(n) if o[k].level != n[k].level),
    }
