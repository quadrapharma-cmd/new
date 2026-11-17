"""Stage 2 — the pages received twice.

A top block (a top-level bookmark, or a file) whose pages are, nearly all and in the same order, the pages of an earlier block
is a second copy: it is left out, the first copy kept. Two pages are the same page when their bytes are the same (signature) or
when they are drawn alike at 24 dpi in grey: no pixel differs by 16 levels or more beyond one in five hundred, and none by 8 or
more beyond one in a hundred (a copy recompressed, «(reduced)», differs by a few levels in places). The earlier block is found
by the pages that share their bytes or a coarse picture (16 × 16 means), then every pair is compared. Identical pages that are not a whole repeated
block stay where they are and are listed for the report (the same page in three drug substances may be meant).

Writes repeats.json: blocks, dropped blocks (with the earlier copy and how many pairs are the same by bytes and by picture), the
kept page runs (split where a file ends) and the groups of identical pages among the kept ones."""
from collections import Counter, defaultdict

from PIL import Image, ImageChops

from .common import Work, say

MIN_BLOCK = 10          # a repeated block is at least this many pages
COVER = 0.98            # and at least this share of its pages are the earlier block's, in order
MIN_RUN = 50            # without bookmarks: a run of identical pages this long is a repeated copy


def ahash(path):
    try:
        im = Image.open(path).convert('L').resize((16, 16), Image.BOX)
        return bytes(v // 16 for v in im.tobytes()).hex()
    except Exception:
        return None


def alike(pa, pb):
    """Two pictures at 24 dpi drawn alike (sizes within 2 pixels: the common part compared)."""
    try:
        a, b = Image.open(pa).convert('L'), Image.open(pb).convert('L')
    except Exception:
        return False
    if abs(a.size[0] - b.size[0]) > 2 or abs(a.size[1] - b.size[1]) > 2:
        return False
    w, h = min(a.size[0], b.size[0]), min(a.size[1], b.size[1])
    hist = ImageChops.difference(a.crop((0, 0, w, h)), b.crop((0, 0, w, h))).histogram()
    n = w * h
    return sum(hist[16:]) <= n * 0.002 and sum(hist[8:]) <= n * 0.01


def blocks_of(pages, outline, files):
    starts = {}
    for o in outline:
        if o['level'] == 0 and o['page']:
            starts.setdefault(o['page'], o['title'])
    for f in files:
        if f.get('kind') == 'pdf' and f.get('from'):
            starts.setdefault(f['from'], f['name'])
    total = len(pages)
    s = sorted(starts)
    blocks = [{'from': a, 'to': s[i + 1] - 1 if i + 1 < len(s) else total, 'title': starts[a]} for i, a in enumerate(s)]
    if total and (not blocks or blocks[0]['from'] > 1):
        blocks.insert(0, {'from': 1, 'to': (s[0] - 1) if s else total, 'title': ''})
    return blocks


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    pages = w.load('read/pages.json')
    outline = w.load('read/outline.json', [])
    files = w.load('read/files.json', [])
    P = {p['n']: p for p in pages}
    thumb = lambda n: w.read / 'thumbs' / f'p{n:05d}.png'
    by_sig, by_hash = defaultdict(list), defaultdict(list)
    for p in pages:
        by_sig[p['sig']].append(p['n'])
        p['_ah'] = ahash(thumb(p['n']))
        if p['_ah']:
            by_hash[p['_ah']].append(p['n'])
    cache = {}

    def same(a, b):
        if P[a]['sig'] == P[b]['sig']:
            return True
        if (a, b) not in cache:
            cache[(a, b)] = alike(thumb(a), thumb(b))
        return cache[(a, b)]

    def earlier(q):
        out = {p for p in by_sig[P[q]['sig']] if p < q}
        if P[q].get('_ah') and len(by_hash[P[q]['_ah']]) <= 50:          # a blank page's picture is everywhere: not a clue
            out |= {p for p in by_hash[P[q]['_ah']] if p < q}
        return out

    blocks = blocks_of(pages, outline, files)
    dropped, gone = [], set()
    for b in blocks:
        n = b['to'] - b['from'] + 1
        if n < MIN_BLOCK:
            continue
        offs = Counter()
        for q in range(b['from'], b['to'] + 1):
            for p in earlier(q):
                offs[q - p] += 1
        for d, _ in offs.most_common(3):
            a1, a2 = b['from'] - d, b['to'] - d
            if a1 < 1 or a2 >= b['from'] or any(x in gone for x in range(a1, a2 + 1)):
                continue
            pairs = [(q - d, q) for q in range(b['from'], b['to'] + 1)]
            by_pic = sum(1 for x, y in pairs if same(x, y))
            if by_pic < COVER * n:
                continue
            by_bytes = sum(1 for x, y in pairs if P[x]['sig'] == P[y]['sig'])
            src = next((x for x in blocks if x['from'] <= a1 <= x['to']), None)
            dropped.append({'from': b['from'], 'to': b['to'], 'title': b['title'], 'pages': n, 'same_as': [a1, a2],
                            'same_as_title': src['title'] if src else '', 'same_bytes': by_bytes, 'same_24dpi': by_pic})
            gone |= set(range(b['from'], b['to'] + 1))
            break
    if not dropped and len(blocks) <= 1:                    # no bookmarks: long runs of pages seen before
        run_len, best = {}, []
        for q in range(1, len(pages) + 1):
            for p in earlier(q):
                if same(p, q):
                    run_len[(p, q)] = run_len.get((p - 1, q - 1), 0) + 1
        ends = sorted(((L, p, q) for (p, q), L in run_len.items() if L >= MIN_RUN and run_len.get((p + 1, q + 1), 0) == 0), reverse=True)
        for L, p, q in ends:
            r = set(range(q - L + 1, q + 1))
            if r & gone or p >= q - L + 1:
                continue
            dropped.append({'from': q - L + 1, 'to': q, 'title': '', 'pages': L, 'same_as': [p - L + 1, p], 'same_as_title': '',
                            'same_bytes': sum(1 for i in range(L) if P[p - i]['sig'] == P[q - i]['sig']), 'same_24dpi': L})
            gone |= r
        dropped.sort(key=lambda x: x['from'])
    # the kept pages, as runs that do not cross a file's end
    file_of = {p['n']: p['file'] for p in pages}
    kept, cur = [], None
    for q in range(1, len(pages) + 1):
        if q in gone:
            cur = None
            continue
        if cur and cur[1] == q - 1 and file_of[cur[1]] == file_of[q]:
            cur[1] = q
        else:
            cur = [q, q]
            kept.append(cur)
    for p in pages:
        p.pop('_ah', None)
    groups = defaultdict(list)
    for p in pages:
        if p['n'] not in gone:
            groups[p['sig']].append(p['n'])
    identical = [g for g in groups.values() if len(g) > 1]
    w.save('repeats.json', {'blocks': blocks, 'dropped': dropped, 'kept': kept, 'identical_groups': identical})
    say(f'{len(dropped)} كتلة مكررة تُركت ({sum(x["pages"] for x in dropped)} صفحة) · '
        f'{len(identical)} مجموعة صفحات متطابقة بقيت ({sum(len(g) for g in identical)} صفحة) · الأجزاء الباقية: '
        + ', '.join(f'{a}–{b}' for a, b in kept))
    return {'dropped': dropped, 'kept': kept}
