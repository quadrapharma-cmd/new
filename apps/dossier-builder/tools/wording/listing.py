"""The Arabic texts of the page's files as a numbered list to read (each different text once, in the order it first appears), and
the map id → text kept beside it.  python3 listing.py <units.json> <out-prefix> [per-file]"""
import hashlib, json, pathlib, sys

units = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
prefix = sys.argv[2]
seen, order = {}, []
for u in units:
    t = u['text']
    if t not in seen:
        seen[t] = {'n': 0, 'file': pathlib.Path(u['file']).name, 'kind': u['kind'], 'line': u.get('line')}
        order.append(t)
    seen[t]['n'] += 1
ids = {}
for t in order:
    h = hashlib.sha1(t.encode('utf-8')).hexdigest()
    k = 7
    while h[:k] in ids and ids[h[:k]] != t:
        k += 1
    ids[h[:k]] = t
by_text = {t: i for i, t in ids.items()}
pathlib.Path(prefix + '.ids.json').write_text(json.dumps(ids, ensure_ascii=False, indent=0), encoding='utf-8')
lines = []
for t in order:
    m = seen[t]
    lines.append(f"{by_text[t]}\t{t}")
pathlib.Path(prefix + '.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(len(order), 'texts;', sum(len(t) for t in order), 'chars →', prefix + '.txt')
