"""Suggest the requirement slot for an uploaded file (P1 «auto-classify»).
Signals: CTD/eCTD number in the file name (e.g. 3.2.P.5.1, 32p51, 1.1.13), the
pack's keyword list (classify.yaml) and the requirement titles, matched in the
file name and in the first page's text. Output is a ranked suggestion list; the
user always confirms."""
import re
import yaml
from dossier_engine.yamlfast import load as yload
from dossier_engine.packs import number

STOP = {'and', 'or', 'of', 'the', 'for', 'in', 'on', 'to', 'a', 'an', 'by', 'with', 'per', 'all', 'if', 'any', 'each',
        'new', 're', 'reg', 'incl', 'including', 'etc', 'from', 'one', 'only', 'other', 'study', 'reports', 'report'}


def _norm(s):
    s = (s or '').lower().replace('_', ' ').replace('-', ' ')
    return re.sub(r'\s+', ' ', s)


def _ctd_tokens(name):
    """CTD numbers in a file name: '3.2.P.5.1' / '3_2_p_5_1' / '1.1.13' (separated) and the ICH
    App. 4 compact form '32p51' (single digits after the letter) -> '3.2.p.5.1'."""
    out = set()
    for m in re.finditer(r'(?<![\w.])([1-5](?:[._ ](?:\d{1,2}|[spar]))+)(?![\w])', name, re.I):
        out.add('.'.join(re.split(r'[._ ]', m.group(1).lower())))
    for m in re.finditer(r'(?<![a-z0-9])([1-5])([1-9])([spar])?(\d*)(?![0-9])', name, re.I):
        parts = [m[1], m[2]] + ([m[3].lower()] if m[3] else []) + list(m[4])
        if m[3] or m[4]:
            out.add('.'.join(parts))
    return out


class Classifier:
    def __init__(self, pack):
        self.pack = pack
        kw = {}
        for src in ([pack.base] if getattr(pack, 'base', None) else []) + [pack]:      # the common CTD's keywords, then the authority's own
            try:
                kw.update(yload(open(src.path / 'classify.yaml', encoding='utf-8')) or {})
            except FileNotFoundError:
                pass
        self.reqs = {}
        for r in pack.requirements:
            words = {w for w in re.findall(r'[a-z]{4,}', _norm(r['title']['en'])) if w not in STOP}
            secs = {x.lower() for x in [number(r).split(' ')[0]] + r['ectd']['nodes']}
            self.reqs[r['id']] = {'phrases': [_norm(p) for p in kw.get(r['id'], [])], 'words': words, 'secs': secs}

    def suggest(self, filename, text, slots, top=3):
        fn, tx = _norm(filename), _norm(text)[:6000]
        nums = _ctd_tokens(filename.lower())
        scored = []
        for s in slots:
            if not s.active:
                continue
            r = self.reqs.get(s.req_id)
            if not r:
                continue
            score, why = 0, []
            for sec in r['secs']:
                if sec in nums:
                    score += 6
                    why.append(f'section {sec} in file name')
            for p in r['phrases']:
                if re.search(r'(?<![a-z])' + re.escape(p) + r'(?![a-z])', fn):
                    score += 4
                    why.append(f'«{p}» in file name')
                elif p and re.search(r'(?<![a-z])' + re.escape(p) + r'(?![a-z])', tx):
                    score += 3
                    why.append(f'«{p}» in text')
            hits = [w for w in r['words'] if w in fn or w in tx]
            score += min(len(hits), 3)
            if s.item:     # per-API slot: prefer the item whose substance, then whose manufacturer, the document names
                from .extract import api_key
                sub = _norm(api_key(s.item.get('name') or ''))
                if sub and re.search(r'(?<![a-z])' + re.escape(sub) + r'(?![a-z])', fn + ' ' + tx):
                    score += 3
                    why.append(f"substance «{s.item['name']}»")
                man = _norm(s.item['manufacturer'])
                if man and (man in fn or man in tx):
                    score += 3
                    why.append(f"manufacturer «{s.item['manufacturer']}»")
            if score >= 3:
                scored.append({'slot_id': s.slot_id, 'req_id': s.req_id, 'score': score, 'why': why[:4]})
        scored.sort(key=lambda x: (-x['score'], x['slot_id']))
        return scored[:top]
