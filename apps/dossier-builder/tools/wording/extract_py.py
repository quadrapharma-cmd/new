"""Every Arabic string literal of the engine's Python files, with its exact place and a guess of what it is:
   'msg'   — a message a person reads (an error's Arabic text, a finding, a hint): the second of an (en, ar) pair, or a dict's 'ar'
   'other' — anything else (reading keywords, regular expressions, prompts, the wording of generated letters): looked at by hand.
   python3 extract_py.py <out.json> <dir-or-file>..."""
import ast, io, json, pathlib, re, sys, tokenize

AR = re.compile(r'[؀-ۿ]')
out = []


def offsets(src):
    lines = src.splitlines(keepends=True)
    acc, o = [], 0
    for ln in lines:
        acc.append(o)
        o += len(ln)
    return acc


def scan(path):
    src = path.read_text(encoding='utf-8')
    if not AR.search(src):
        return
    off = offsets(src)
    pos = lambda r, c: off[r - 1] + c                                    # tokenize columns are in characters
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print('does not parse', path, e)
        return
    # what each string constant is: by its parent in the tree
    role = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == 'ar':
                    for c in ast.walk(v):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str):
                            role[(c.lineno, c.col_offset)] = 'msg'
        elif isinstance(node, ast.Call):
            name = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None) or ''
            for kw in node.keywords:
                if kw.arg == 'ar':
                    for c in ast.walk(kw.value):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str):
                            role[(c.lineno, c.col_offset)] = 'msg'
            if name in ('StoreError', 'ExportError', 'Refused', 'err', 'HTTPException', 'ApiError', 'fail', 'bad', 'finding', 'Finding', 'bi', 'L', 'say', 'msg', 'both', 'two', 'T', 'tr', 'note', 'warn', 'ReadError', 'DriveError', 'PackError', 'BundleError', 'LockedError', 'ValueError', 'RuntimeError'):
                for a in node.args:
                    for c in ast.walk(a):
                        if isinstance(c, ast.Constant) and isinstance(c.value, str):
                            role.setdefault((c.lineno, c.col_offset), 'msg:' + name)
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    for t in toks:
        if t.type != tokenize.STRING or not AR.search(t.string):
            continue
        m = re.match(r'(?i)([rbuf]*)(\'\'\'|"""|\'|")', t.string)
        prefix, q = m.group(1), m.group(2)
        s, e = pos(*t.start) + len(prefix) + len(q), pos(*t.end) - len(q)
        r = role.get((t.start[0], len(src.splitlines()[t.start[0] - 1][:t.start[1]].encode('utf-8'))), None)
        out.append({'file': str(path), 'kind': r or 'other', 'q': q, 'prefix': prefix, 'start': s, 'end': e, 'line': t.start[0], 'text': src[s:e]})


for a in sys.argv[2:]:
    p = pathlib.Path(a)
    for f in (sorted(p.rglob('*.py')) if p.is_dir() else [p]):
        scan(f)
pathlib.Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
by = {}
for u in out:
    k = pathlib.Path(u['file']).name
    by.setdefault(k, {}).setdefault(u['kind'].split(':')[0], 0)
    by[k][u['kind'].split(':')[0]] += 1
for k, v in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
    print(f'{sum(v.values()):5d}  {k:28s} {v}')
print('units', len(out), 'unique', len({u['text'] for u in out}), 'chars', sum(len(u['text']) for u in out))
