"""Slots + uploaded files -> writer documents (eCTD 3.2.2 placement)."""
from .writers.ectd32 import Doc


def node_for(slot, profile):
    """Pick the eCTD node of a slot when the requirement maps to several."""
    nodes = slot.ectd
    if not nodes:
        return None
    if slot.req_id == 'M1-04':
        return '1.2.3.3' if profile.activity == 'new' else '1.2.3.4'
    return nodes[0]


def docs_for(slots, profile, files):
    """files: {slot_id: [ {file, title?, pi_type?, lang?, node?} ]}. Only active slots are placed."""
    out, unplaced = [], []
    for s in slots:
        if not s.active:
            continue
        for f in files.get(s.slot_id, []):
            node = f.get('node') or node_for(s, profile)
            if node is None:
                unplaced.append(s.slot_id)       # CTD-only item (e.g. M5 TOC)
                continue
            kw = {}
            if s.item and node.startswith(('3.2.S', '2.3.S')):
                kw = dict(substance=s.item['name'], manufacturer=s.item['manufacturer'])
            extra = {k: f[k] for k in ('pi_type', 'lang', 'study', 'doc_type', 'control', 'indication', 'excipient', 'uuid', 'name', 'doc_id')
                     if f.get(k)}
            if f.get('eu_country'):
                extra['country'] = f['eu_country']              # EU M1: the country folder / specific@country it is filed under
            if f.get('ref'):
                extra['ref'] = f['ref']                       # submitted before: the leaf points there
            if s.req_id == 'M1-44':
                extra.setdefault('name', 'tracking')          # EG-PF-15.12: tracking.pdf / tracking-<var>.pdf
            out.append(Doc(node=node, file=f['file'], title=f.get('title') or s.title['en'][:120], **extra, **kw))
    return out, unplaced
