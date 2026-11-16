"""Put the formal-Arabic texts into the engine's Python files: every Arabic string token that equals a listed old text is replaced
by its new one at its exact place. Checked before writing: the same {…} fields, no quote that would end the string, no new
backslash; and every changed file still parses.   python3 apply_py.py <ids.json> <tm,tm…> <dir-or-file>… [--dry]"""
import ast, io, json, pathlib, re, sys, tokenize

args = [a for a in sys.argv[1:] if a != '--dry']
dry = '--dry' in sys.argv
ids = json.loads(pathlib.Path(args[0]).read_text(encoding='utf-8'))
tm = {}
SEP = ' ⇒ '
for f in args[1].split(','):
    for line in pathlib.Path(f).read_text(encoding='utf-8').split('\n'):
        if not line.strip() or line.startswith('#'):
            continue
        i = line.index(SEP)
        k, new = line[:i].strip(), line[i + len(SEP):]
        assert k in ids, (f, k)
        assert tm.get(ids[k], new) == new, (f, k, 'given twice, differently')
        tm[ids[k]] = new
AR = re.compile(r'[؀-ۿ]')
FIELD = re.compile(r'\{[^{}]*\}')
problems, n, files, used = [], 0, 0, set()
for a in args[2:]:
    p = pathlib.Path(a)
    for path in (sorted(p.rglob('*.py')) if p.is_dir() else [p]):
        src = path.read_text(encoding='utf-8')
        if not AR.search(src):
            continue
        lines = src.splitlines(keepends=True)
        off, o = [], 0
        for ln in lines:
            off.append(o)
            o += len(ln)
        reps = []
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type != tokenize.STRING or not AR.search(t.string):
                continue
            m = re.match(r'(?i)([rbuf]*)(\'\'\'|"""|\'|")', t.string)
            prefix, q = m.group(1), m.group(2)
            s, e = off[t.start[0] - 1] + t.start[1] + len(prefix) + len(q), off[t.end[0] - 1] + t.end[1] - len(q)
            old = src[s:e]
            if old not in tm or tm[old] == old:
                continue
            new = tm[old]
            used.add(old)
            where = f'{path.name}:{t.start[0]}'
            if sorted(FIELD.findall(old)) != sorted(FIELD.findall(new)):
                problems.append(f'{where} the {{…}} fields differ\n   old: {old[:150]}\n   new: {new[:150]}')
            if len(q) == 1 and re.search(r'(^|[^\\])' + re.escape(q), new):
                problems.append(f'{where} an unescaped {q} in the new text: {new[:120]}')
            if '\\' in new and '\\' not in old:
                problems.append(f'{where} a new backslash: {new[:120]}')
            if ('\n' in new) != ('\n' in old):
                problems.append(f'{where} line breaks differ')
            reps.append((s, e, new))
        if not reps:
            continue
        out = src
        for s, e, new in sorted(reps, reverse=True):
            out = out[:s] + new + out[e:]
        try:
            ast.parse(out)
        except SyntaxError as ex:
            problems.append(f'{path.name} would not parse: {ex}')
            continue
        n += len(reps)
        files += 1
        if not dry and not problems:
            path.write_text(out, encoding='utf-8')
if problems:
    print('\n'.join(problems))
    print(len(problems), 'problem(s)' + ('' if dry else ': files with problems were not all written — fix and run again'))
    sys.exit(1)
unused = [t for t in tm if t not in used]
print(('would replace' if dry else 'replaced'), n, 'text(s) in', files, 'file(s);', len(tm), 'in the list,', len(unused), 'not found')
for t in unused[:15]:
    print('  not found:', t[:90])
