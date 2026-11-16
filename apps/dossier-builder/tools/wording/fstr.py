"""Arabic f-strings of Python files (Python 3.12+ tokenizes them apart from plain strings, so the first pass missed them).
   list :  python3 fstr.py list <out-prefix> <dir-or-file>…          → <prefix>.txt (id, place, body) and <prefix>.ids.json
   apply:  python3 fstr.py apply <prefix>.ids.json <tm,tm…> <dir-or-file>… [--dry]
The body is what stands between the quotes, with its {…} fields as written. Checked before writing: the same {…} fields, no quote
that would end the string, no new backslash, the same line breaks; and every changed file still parses."""
import ast, hashlib, io, json, pathlib, re, sys, tokenize

AR = re.compile(r'[؀-ۿ]')
FIELD = re.compile(r'\{[^{}]*\}')
SEP = ' ⇒ '


def bodies(path):
    src = path.read_text(encoding='utf-8')
    if not AR.search(src):
        return src, []
    lines = src.splitlines(keepends=True)
    off, o = [], 0
    for ln in lines:
        off.append(o)
        o += len(ln)
    pos = lambda rc: off[rc[0] - 1] + rc[1]
    out, stack = [], []
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type == tokenize.FSTRING_START:
            stack.append(t)
        elif t.type == tokenize.FSTRING_END:
            st = stack.pop()
            if stack:
                continue                                                  # an f-string inside another's field: part of the outer one
            s, e = pos(st.end), pos(t.start)
            body = src[s:e]
            if AR.search(body):
                out.append({'file': str(path), 'line': st.start[0], 'start': s, 'end': e, 'q': t.string, 'text': body})
    return src, out


def files(args):
    for a in args:
        p = pathlib.Path(a)
        for f in (sorted(p.rglob('*.py')) if p.is_dir() else [p]):
            if '__pycache__' not in str(f):
                yield f


mode = sys.argv[1]
if mode == 'list':
    prefix = sys.argv[2]
    ids, rows = {}, []
    for f in files(sys.argv[3:]):
        _, units = bodies(f)
        for u in units:
            t = u['text']
            h = hashlib.sha1(t.encode('utf-8')).hexdigest()
            k = 7
            while h[:k] in ids and ids[h[:k]] != t:
                k += 1
            if h[:k] not in ids:
                ids[h[:k]] = t
                rows.append(f"{h[:k]}\t{pathlib.Path(u['file']).name}:{u['line']}\t{t}")
    pathlib.Path(prefix + '.ids.json').write_text(json.dumps(ids, ensure_ascii=False, indent=0), encoding='utf-8')
    pathlib.Path(prefix + '.txt').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(len(rows), 'f-string(s) with Arabic →', prefix + '.txt')
else:
    args = [a for a in sys.argv[2:] if a != '--dry']
    dry = '--dry' in sys.argv
    ids = json.loads(pathlib.Path(args[0]).read_text(encoding='utf-8'))
    tm = {}
    for f in args[1].split(','):
        for line in pathlib.Path(f).read_text(encoding='utf-8').split('\n'):
            if not line.strip() or line.startswith('#'):
                continue
            i = line.index(SEP)
            k, new = line[:i].strip(), line[i + len(SEP):]
            assert k in ids, (f, k)
            assert tm.get(ids[k], new) == new, (f, k, 'given twice, differently')
            tm[ids[k]] = new
    problems, n, nfiles, used = [], 0, 0, set()
    for path in files(args[2:]):
        src, units = bodies(path)
        reps = []
        for u in units:
            old = u['text']
            if old not in tm or tm[old] == old:
                continue
            new = tm[old]
            used.add(old)
            where = f"{path.name}:{u['line']}"
            if sorted(FIELD.findall(old)) != sorted(FIELD.findall(new)):
                problems.append(f'{where} the {{…}} fields differ\n   old: {old[:160]}\n   new: {new[:160]}')
            outside = FIELD.sub('', new)
            if len(u['q']) == 1 and u['q'] in outside:
                problems.append(f"{where} an unescaped {u['q']} in the new text: {new[:120]}")
            if '\\' in new and '\\' not in old:
                problems.append(f'{where} a new backslash: {new[:120]}')
            if ('\n' in new) != ('\n' in old):
                problems.append(f'{where} line breaks differ')
            reps.append((u['start'], u['end'], new))
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
        nfiles += 1
        if not dry and not problems:
            path.write_text(out, encoding='utf-8')
    if problems:
        print('\n'.join(problems))
        print(len(problems), 'problem(s)' + ('' if dry else ': files with problems were not all written — fix and run again'))
        sys.exit(1)
    unused = [t for t in tm if t not in used]
    print(('would replace' if dry else 'replaced'), n, 'f-string(s) in', nfiles, 'file(s);', len(tm), 'in the list,', len(unused), 'not found')
    for t in unused[:15]:
        print('  not found:', t[:90])
