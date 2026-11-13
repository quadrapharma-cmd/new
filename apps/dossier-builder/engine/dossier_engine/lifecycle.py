"""Lifecycle planner (P3): what goes into the next sequence.

The «current view» of an application is the fold of every submitted sequence.
Each submitted leaf/CoU is remembered with the dossier document it carried. For
the next sequence, per location (same node + same section-defining attributes —
ICH SPEC p. 6-3: replace/delete in the same backbone location):
  * a submitted, still-active leaf whose document is still current → unchanged (not resent, EG-BP-E29)
  * a submitted leaf whose document was superseded/withdrawn + a current document
    not yet submitted at that location → replace (paired in order)
  * left-over submitted leaves → delete (3.2.2) / suspend (4.0)
  * left-over current documents → new
"""
from dataclasses import dataclass


def location_key(doc):
    """Section-defining attributes (EU HTG 2.9.6 Table 5 / ICH SPEC): node + substance/manufacturer/pi-doc, and in the EU Module 1
    the country (specific/@country, pi-doc/@country): a German SmPC never replaces the common one. Only an EU document has one, so
    every other key is what it always was."""
    key = (doc.node, doc.substance or '', doc.manufacturer or '', doc.pi_type or '', doc.lang or '')
    return key + (doc.country,) if getattr(doc, 'country', None) else key


@dataclass
class Step:
    op: str                 # new | replace | delete
    doc: object = None      # writer Doc (new/replace)
    prior: dict = None      # history leaf (replace/delete)


def current_view(history):
    """history: submissions oldest→newest, each {'seq', 'leaves': [{doc_id, key, leaf_id, href, xml, op, cou_id, doc_uuid}]}.
    Returns active leaves (not deleted/replaced) keyed by (key, leaf_id)."""
    active = {}
    for sub in history:
        for lf in sub['leaves']:
            if lf['op'] in ('replace', 'delete') and lf.get('replaces'):
                active.pop(lf['replaces'], None)
            if lf['op'] != 'delete':
                active[lf['leaf_id']] = dict(lf, seq=sub['seq'], key=tuple(lf['key']))
    return active


def plan(history, docs, current_doc_ids):
    """docs: writer Docs for the current dossier, each with .doc_id; current_doc_ids: ids of current documents."""
    active = current_view(history)
    submitted_ids = {lf['doc_id'] for lf in active.values()}
    steps = []
    by_key = {}
    for d in docs:
        by_key.setdefault(location_key(d), []).append(d)
    old_by_key = {}
    for lf in active.values():
        old_by_key.setdefault(lf['key'], []).append(lf)
    for key in sorted(set(by_key) | set(old_by_key), key=str):
        news = [d for d in by_key.get(key, []) if d.doc_id not in submitted_ids]
        if key[0] == '1.0':               # cover letter / tracking table: always «new», never replaced or deleted
            steps += [Step('new', d, None) for d in news]
            continue
        stale = [lf for lf in sorted(old_by_key.get(key, []), key=lambda x: (x['seq'], x['leaf_id']))
                 if lf['doc_id'] not in current_doc_ids]
        for lf, d in zip(stale, news):
            steps.append(Step('replace', d, lf))
        for lf in stale[len(news):]:
            steps.append(Step('delete', None, lf))
        for d in news[len(stale):]:
            steps.append(Step('new', d, None))
    return steps


def to_ectd32(steps):
    """Plan steps -> 3.2.2 writer Docs (operation + modified_file 'SSSS#ID')."""
    from dataclasses import replace as dc_replace
    from .writers.ectd32 import Doc
    out = []
    for st in steps:
        if st.op == 'new':
            out.append(dc_replace(st.doc, operation='new', modified_file=None))
        elif st.op == 'replace':
            out.append(dc_replace(st.doc, operation='replace', modified_file=f"{st.prior['seq']}#{st.prior['leaf_id']}"))
        else:
            node, sub, man, pi, lang, country = (list(st.prior['key']) + [''] * 6)[:6]
            out.append(Doc(node=node, file='', title=st.prior.get('title') or node, substance=sub or None,
                           manufacturer=man or None, pi_type=pi or None, lang=lang or None, operation='delete',
                           modified_file=f"{st.prior['seq']}#{st.prior['leaf_id']}", country=country or None))
    return out


def to_ectd40(steps):
    """Plan steps -> (4.0 writer Docs, suspend list)."""
    from dataclasses import replace as dc_replace
    docs, suspend = [], []
    for st in steps:
        if st.op == 'new':
            docs.append(dc_replace(st.doc, operation='new', cou_replaces=None))
        elif st.op == 'replace':
            docs.append(dc_replace(st.doc, operation='replace', cou_replaces=st.prior['cou_id']))
        else:
            suspend.append({'cou_id': st.prior['cou_id'], 'priority': st.prior.get('priority')})
    return docs, suspend
