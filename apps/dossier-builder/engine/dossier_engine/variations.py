"""Variation picker (P3 start): search the EDA variation list and plan a submission.
Classification and wording come from the pack (EDA Variation Self-Guided Tool snapshot,
GL.CAPP.026 v6); the only computation is the grouping rule (highest class) and the
eCTD submission type/mode mapping (EG TG draft Annex 6)."""
import re
import yaml
from .packs import PACKS_DIR

PACK = PACKS_DIR / 'eda.variations.gl026.v6'


class Variations:
    def __init__(self, root=PACK):
        self.meta = yaml.safe_load(open(root / 'pack.yaml', encoding='utf-8'))
        self.items = yaml.safe_load(open(root / 'variations.yaml', encoding='utf-8'))
        self.by_id = {v['id']: v for v in self.items}
        self.order = self.meta['class_order']

    def search(self, q='', group=None, pac=None):
        words = [w for w in re.findall(r'\w+', (q or '').lower()) if len(w) > 1]
        out = []
        for v in self.items:
            if group and v['group'] != group or pac and v['pac'] != pac:
                continue
            hay = f"{v['request']} {v['type']} {v['group']}".lower()
            if all(w in hay for w in words):
                out.append(v)
        return out

    def plan(self, ids):
        chosen = [self.by_id[i] for i in ids if i in self.by_id]
        unknown = [i for i in ids if i not in self.by_id]
        if not chosen:
            return {'ok': False, 'unknown': unknown}
        top = max((v['pac'] for v in chosen), key=self.order.index)
        return {
            'ok': True, 'unknown': unknown, 'class': top,
            'submission_type': self.meta['ectd_submission_type'][top],
            'mode': 'single' if len(chosen) == 1 else 'grouping',
            'rule': self.meta['grouping_rule'],
            'items': [{'id': v['id'], 'request': v['request'], 'pac': v['pac'], 'conditions': v['conditions'],
                       'requirements': v['requirements'], 'source': v['source']} for v in chosen],
        }
