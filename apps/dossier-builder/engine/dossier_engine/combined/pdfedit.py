"""A minimal correction inside a PDF page that has its own text: the glyphs of one phrase are removed from the content stream
(the font's ToUnicode map tells which code is which letter; «/ToUnicode /Identity-H» means the two-byte codes are the letters),
nothing else on the page is touched.
   edit_page(pdf, page_index, [(old, new), ...]) -> list of what was changed
Only deletions of characters (e.g. «1.25 mcg» -> «1.25 mg», «P.2.1» -> «P.1»): the glyphs left keep their codes, so no glyph is
needed that the page did not already use. Each phrase must be on the page exactly once."""
import re
import pikepdf


def tounicode(font):
    """code (bytes) -> unicode text, from the font's ToUnicode CMap (bfchar and bfrange)."""
    tu = font.get('/ToUnicode')
    if tu is None:
        if font.get('/Subtype') in ('/Type1', '/TrueType', '/MMType1'):      # a simple font: one byte a letter, WinAnsi
            return {bytes([b]): bytes([b]).decode('cp1252', 'replace') for b in range(32, 256)}
        return {}
    if isinstance(tu, pikepdf.Name):            # «/ToUnicode /Identity-H»: the 2-byte codes are the Unicode values
        return IDENTITY if str(tu) == '/Identity-H' else {}
    data = tu.read_bytes().decode('latin-1')
    m = {}
    for block in re.findall(r'beginbfchar(.*?)endbfchar', data, re.S):
        for src, dst in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', block):
            m[bytes.fromhex(src)] = bytes.fromhex(dst).decode('utf-16-be', 'replace')
    for block in re.findall(r'beginbfrange(.*?)endbfrange', data, re.S):
        for a, b, rest in re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]+>)', block):
            lo, hi, w = int(a, 16), int(b, 16), len(a) // 2
            if rest.startswith('['):
                dsts = re.findall(r'<([0-9A-Fa-f]+)>', rest)
                for k, d in enumerate(dsts):
                    m[(lo + k).to_bytes(w, 'big')] = bytes.fromhex(d).decode('utf-16-be', 'replace')
            else:
                base = int(rest.strip('<>'), 16)
                for k in range(hi - lo + 1):
                    m[(lo + k).to_bytes(w, 'big')] = chr(base + k)
    return m


class _Identity(dict):
    def __missing__(self, code):
        return chr(int.from_bytes(code, 'big'))

    def __bool__(self):
        return True


IDENTITY = _Identity({b'\x00\x00': '\x00'})       # one entry so the code width (2) can be read from it


def drawn_text(pdf, index):
    """A page's text in the order its content stream draws it: what edit_page looks for a phrase in."""
    page = pdf.pages[index]
    fonts = page.obj.Resources.get('/Font') or {}
    maps = {str(k): tounicode(fonts[k]) for k in fonts.keys()}
    font, out = None, []
    for operands, op in pikepdf.parse_content_stream(page):
        name = str(op)
        if name == 'Tf':
            font = str(operands[0])
        elif name in ('Tj', "'", '"', 'TJ'):
            cmap = maps.get(font, {})
            width = 2 if cmap and len(next(iter(cmap))) == 2 else 1
            for it in (operands[0] if name == 'TJ' else [operands[-1]]):
                if isinstance(it, pikepdf.String):
                    raw = bytes(it)
                    out += [cmap[raw[k:k + width]] if isinstance(cmap, _Identity) else cmap.get(raw[k:k + width], '?')
                            for k in range(0, len(raw), width)]
    return ''.join(out)


def edit_page(pdf, index, edits):
    page = pdf.pages[index]
    fonts = page.obj.Resources.Font
    maps = {str(k): tounicode(fonts[k]) for k in fonts.keys()}
    ops = pikepdf.parse_content_stream(page)
    font = None
    # every shown string with its decoded text: (op index, operand path, codes list, text list)
    shown = []
    for i, (operands, op) in enumerate(ops):
        name = str(op)
        if name == 'Tf':
            font = str(operands[0])
        elif name in ('Tj', "'", '"', 'TJ'):
            cmap = maps.get(font, {})
            width = 2 if cmap and len(next(iter(cmap))) == 2 else 1
            items = operands[0] if name == 'TJ' else [operands[-1]]
            for j, it in enumerate(items):
                if isinstance(it, pikepdf.String):
                    raw = bytes(it)
                    codes = [raw[k:k + width] for k in range(0, len(raw), width)]
                    shown.append((i, j, name, codes, [cmap[c] if isinstance(cmap, _Identity) else cmap.get(c, '?') for c in codes]))
    stream_text = ''.join(''.join(s[4]) for s in shown)
    done = []
    for old, new in edits:
        pos = stream_text.find(old)
        if pos < 0 or stream_text.find(old, pos + 1) >= 0:
            raise ValueError(f'«{old}» وُجدت {stream_text.count(old)} مرة في الصفحة {index + 1}، والمطلوب مرة واحدة')
        # characters of old that new drops (new must be old with some characters removed)
        keep, k = [], 0
        for ch in old:
            if k < len(new) and new[k] == ch:
                keep.append(True)
                k += 1
            else:
                keep.append(False)
        if k != len(new):
            raise ValueError(f'«{new}» ليست «{old}» بعد حذف حروف منها: هذه الأداة تحذف ولا تضيف')
        drop = {pos + n for n, kp in enumerate(keep) if not kp}
        # walk the shown strings and remove the dropped codes
        at = 0
        for (i, j, name, codes, texts) in shown:
            n = len(texts)
            hit = [c for c in range(n) if at + c in drop]
            if hit:
                operands, op = ops[i]
                new_codes = b''.join(codes[c] for c in range(n) if c not in hit)
                if name == 'TJ':
                    arr = operands[0]
                    arr[j] = pikepdf.String(new_codes)
                else:                                           # a Tj's operands are a copy: the instruction is made again
                    operands = list(operands)
                    operands[-1] = pikepdf.String(new_codes)
                    ops[i] = pikepdf.ContentStreamInstruction(operands, op)
                codes[:] = [codes[c] for c in range(n) if c not in hit]
                texts[:] = [texts[c] for c in range(n) if c not in hit]
            at += n
        stream_text = ''.join(''.join(s[4]) for s in shown)
        done.append((old, new))
    page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(ops))
    return done
