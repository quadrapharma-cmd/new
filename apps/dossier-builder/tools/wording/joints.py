"""Two pieces of one sentence written as adjacent string literals (Python joins them as they are): lists every joint where the
first piece ends with a letter or closing mark and the second begins with a letter, with no space between — two words run together.
   python3 joints.py <dir-or-file>…"""
import io, pathlib, re, sys, tokenize

AR = re.compile(r'[؀-ۿ]')
LETTER = r'[ء-يً-ْA-Za-z0-9»)\]]'
n = 0
for a in sys.argv[1:]:
    p = pathlib.Path(a)
    for path in (sorted(p.rglob('*.py')) if p.is_dir() else [p]):
        if '__pycache__' in str(path):
            continue
        src = path.read_text(encoding='utf-8')
        if not AR.search(src):
            continue
        lines = src.splitlines(keepends=True)
        off, o = [], 0
        for ln in lines:
            off.append(o)
            o += len(ln)
        pos = lambda rc: off[rc[0] - 1] + rc[1]
        pieces, stack, last = [], [], None                         # (line, body, end token index)
        toks = [t for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type not in (tokenize.NL, tokenize.COMMENT, tokenize.NEWLINE)]
        i = 0
        prev = None                                                # the piece just before, if the next token is another string
        for k, t in enumerate(toks):
            body = None
            if t.type == tokenize.STRING:
                m = re.match(r'(?i)([rbuf]*)(\'\'\'|"""|\'|")', t.string)
                body = t.string[len(m.group(0)):-len(m.group(2))]
                start = k
            elif t.type == tokenize.FSTRING_START:
                stack.append(k)
                continue
            elif t.type == tokenize.FSTRING_END:
                s = stack.pop()
                if stack:
                    continue
                body = src[pos(toks[s].end):pos(t.start)]
                start = s
            elif stack:
                continue
            if body is None:
                prev = None
                continue
            if prev is not None and prev[2] == start - 1:
                left, right = prev[1], body
                if AR.search(left + right) and re.search(LETTER + r'$', left) and re.match(r'[ء-يA-Za-z«(]', right):
                    n += 1
                    print(f'{path}:{toks[start].start[0]}  …{left[-45:]!r} + {right[:45]!r}…')
            prev = (toks[start].start[0], body, k)
print(n, 'joint(s) without a space')
