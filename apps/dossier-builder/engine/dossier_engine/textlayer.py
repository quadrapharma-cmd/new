"""The invisible text layer under a scanned page — the browser edition's «make searchable» (fixes: make_searchable where PdfCraft is
not). The words the page read (ui/assets/ocr.js: Tesseract with the accurate Arabic model, PaddleOCR's second reader, pages turned
upright), each at its place on the page, are written in text render mode 3 (neither filled nor stroked: nothing is drawn) after the
page's own content, which is kept byte for byte and closed in q … Q. A word with Arabic letters is written as word processors write
it in a PDF — its letters in the order they are drawn, left to right — so every reader of PDFs puts it back in reading order as it does
for any Arabic document (a mirrored text matrix, as Tesseract writes them, is read backwards by most). The font is a Type 3 font whose
glyphs draw nothing, with a ToUnicode map for every letter.

invisible_only(old, new) proves it before a third party's document is touched: the page's own content streams byte for byte the same
and in their order, its boxes, turn and drawing resources the same, and what was added only text drawn invisibly."""
import math
import re
from io import BytesIO

AR_LETTER = re.compile(r'[ء-يٮ-ۓەۮۯۺ-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]')
FONT = '/DBOCR'
BIDI_MARKS = re.compile('[\u200e\u200f\u202a-\u202e\u2066-\u2069]')
ALLOWED = {b'q', b'Q', b'BT', b'ET', b'Tr', b'Tf', b'Tm', b'Tj', b'Tc', b'Tw', b'Tz', b'Ts'}


def reading_map(view, rotate, extra=0, deskew=0.0):
    """The map from a point of the page as it was read — points from the top left, y down: the page's view box drawn by pdf.js turned
    by /Rotate + extra (a page the reader turned upright), then turned by `deskew` radians about its centre (Tesseract's straightening)
    — to the page's own user space (X, Y). pdf.js's viewport, inverted."""
    x0, y0, x1, y1 = (float(v) for v in view)
    rot = (int(rotate) + int(extra)) % 360
    A, B, C, D = {0: (1, 0, 0, -1), 90: (0, 1, 1, 0), 180: (-1, 0, 0, 1), 270: (0, -1, -1, 0)}[rot]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if A == 0:
        ox, oy, W, H = abs(cy - y0), abs(cx - x0), y1 - y0, x1 - x0
    else:
        ox, oy, W, H = abs(cx - x0), abs(cy - y0), x1 - x0, y1 - y0
    E, F = ox - A * cx - C * cy, oy - B * cx - D * cy
    det = A * D - B * C
    cs, sn = math.cos(-deskew), math.sin(-deskew)

    def to_page(u, v):
        if deskew:
            du, dv = u - W / 2, v - H / 2
            u, v = W / 2 + cs * du - sn * dv, H / 2 + sn * du + cs * dv
        u, v = u - E, v - F
        return (D * u - C * v) / det, (-B * u + A * v) / det
    return to_page


def visual(word):
    """An Arabic word as it is drawn, left to right: its letters reversed, a run of digits or Latin letters inside it kept in its own
    order — how word processors write Arabic in a PDF, and so how every reader of PDFs expects to find it."""
    from .paddle_rec import to_logical
    return to_logical(word)


def _num(x):
    s = f'{x:.3f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def _cmap(chars):
    """A ToUnicode map: one byte per letter, in the order given."""
    out = ['/CIDInit /ProcSet findresource begin', '12 dict begin', 'begincmap',
           '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def', '/CMapName /Adobe-Identity-UCS def', '/CMapType 2 def',
           '1 begincodespacerange', '<00> <FF>', 'endcodespacerange']
    pairs = [f'<{i:02X}> <{ch.encode("utf-16-be").hex().upper()}>' for i, ch in enumerate(chars)]
    for k in range(0, len(pairs), 100):
        part = pairs[k:k + 100]
        out += [f'{len(part)} beginbfchar', *part, 'endbfchar']
    out += ['endcmap', 'CMapName currentdict /CMap defineresource pop', 'end', 'end']
    return '\n'.join(out).encode('ascii')


def _font(w, chars):
    """A Type 3 font of len(chars) ≤ 256 glyphs that draw nothing, each half an em wide, with its ToUnicode map."""
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject, NumberObject)
    glyph = DecodedStreamObject()
    glyph.set_data(b'500 0 d0')
    gref = w._add_object(glyph)
    tu = DecodedStreamObject()
    tu.set_data(_cmap(chars))
    names = [NameObject(f'/g{i}') for i in range(len(chars))]
    font = DictionaryObject({
        NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type3'),
        NameObject('/FontBBox'): ArrayObject([NumberObject(0), NumberObject(-200), NumberObject(500), NumberObject(800)]),
        NameObject('/FontMatrix'): ArrayObject([FloatObject(0.001), NumberObject(0), NumberObject(0), FloatObject(0.001), NumberObject(0), NumberObject(0)]),
        NameObject('/CharProcs'): DictionaryObject({n: gref for n in names}),
        NameObject('/Encoding'): DictionaryObject({NameObject('/Type'): NameObject('/Encoding'),
                                                   NameObject('/Differences'): ArrayObject([NumberObject(0), *names])}),
        NameObject('/FirstChar'): NumberObject(0), NameObject('/LastChar'): NumberObject(len(chars) - 1),
        NameObject('/Widths'): ArrayObject([NumberObject(500)] * len(chars)),
        NameObject('/Resources'): DictionaryObject(), NameObject('/ToUnicode'): w._add_object(tu)})
    return w._add_object(font)


def write(data, layout):
    """data: a PDF; layout: {page number: {'words': [[text, x, y, w, h, line], …] (points, as read; in reading order, line by
    line), 'rotated': 0|90|180|270, 'deskew': radians}}. → the PDF with each page's words under its image, written in reading order
    with a space after each, nothing else changed. ValueError when there is nothing to write."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject
    r = PdfReader(BytesIO(data))
    w = PdfWriter(clone_from=r)
    chars = sorted({ch for pg in layout.values() for wd in pg.get('words') or [] for ch in BIDI_MARKS.sub('', str(wd[0])) if not ch.isspace()} | {' '})
    if len(chars) < 2:
        raise ValueError('no words to write')
    fonts = [_font(w, chars[k:k + 256]) for k in range(0, len(chars), 256)]
    code = {ch: (i // 256, i % 256) for i, ch in enumerate(chars)}
    written = 0
    for n, page in enumerate(w.pages, 1):
        pg = layout.get(n) or layout.get(str(n))
        words = [wd for wd in (pg or {}).get('words') or [] if str(wd[0]).strip() and float(wd[3]) > 0 and float(wd[4]) > 0]
        if not words:
            continue
        view = page.cropbox if '/CropBox' in page else page.mediabox
        to_page = reading_map([view.left, view.bottom, view.right, view.top], page.get('/Rotate', 0) or 0, pg.get('rotated') or 0,
                              float(pg.get('deskew') or 0))
        res = page.get('/Resources')
        res = res.get_object() if res is not None else DictionaryObject()
        fdict = res.get('/Font')
        fdict = fdict.get_object() if fdict is not None else DictionaryObject()
        base = FONT
        while any(f'{base}{i}' in fdict for i in range(len(fonts))):
            base += 'x'
        for i, ref in enumerate(fonts):
            fdict[NameObject(f'{base}{i}')] = ref
        res[NameObject('/Font')] = fdict
        page[NameObject('/Resources')] = res
        ops = ['q', 'BT', '3 Tr', '0 Tc', '0 Tw', '100 Tz', '0 Ts']
        for text, bx, by, bw, bh in ((BIDI_MARKS.sub('', str(wd[0])), *(float(v) for v in wd[1:5])) for wd in words):
            letters = [ch for ch in (visual(text) if AR_LETTER.search(text) else text) if not ch.isspace()]
            if not letters:
                continue
            a, d = 2 * bw / len(letters), bh
            rtl = bool(AR_LETTER.search(text))         # a space after each word, as a reader expects it: at the left of an Arabic word
            glyphs = [' '] + letters if rtl else letters + [' ']
            u0, v0 = (bx - 0.5 * a if rtl else bx), by + 0.8 * bh
            ox, oy = to_page(u0, v0)
            ex = [a - b for a, b in zip(to_page(u0 + 1, v0), (ox, oy))]
            ey = [a - b for a, b in zip(to_page(u0, v0 - 1), (ox, oy))]
            ops.append(f'{_num(ex[0] * a)} {_num(ex[1] * a)} {_num(ey[0] * d)} {_num(ey[1] * d)} {_num(ox)} {_num(oy)} Tm')
            run, font = [], None
            for ch in glyphs:
                f, c = code[ch]
                if f != font and run:
                    ops.append(f'<{"".join(run)}> Tj')
                    run = []
                if f != font:
                    ops.append(f'{base}{f} 1 Tf')
                    font = f
                run.append(f'{c:02X}')
            ops.append(f'<{"".join(run)}> Tj')
            written += 1
        ops += ['ET', 'Q']
        contents = page.get('/Contents')
        old = [contents] if contents is not None and not isinstance(contents.get_object(), ArrayObject) else list(contents.get_object() if contents is not None else [])
        streams = []
        for body in (b'q', b'Q', '\n'.join(ops).encode('ascii')):
            s = DecodedStreamObject()
            s.set_data(body)
            streams.append(w._add_object(s))
        page[NameObject('/Contents')] = ArrayObject([streams[0], *old, streams[1], streams[2]])
    if not written:
        raise ValueError('no words to write')
    out = BytesIO()
    w.write(out)
    return out.getvalue()


def _same(a, b, depth=0):
    """Two PDF objects the same: dictionaries and arrays by their content, streams by their bytes."""
    from pypdf.generic import ArrayObject, DictionaryObject, StreamObject
    a, b = a.get_object() if hasattr(a, 'get_object') else a, b.get_object() if hasattr(b, 'get_object') else b
    if depth > 12:
        return True
    if isinstance(a, StreamObject) or isinstance(b, StreamObject):
        return isinstance(a, StreamObject) and isinstance(b, StreamObject) and a.get_data() == b.get_data() and _same(
            DictionaryObject({k: v for k, v in a.items() if k not in ('/Length', '/Filter', '/DecodeParms')}),
            DictionaryObject({k: v for k, v in b.items() if k not in ('/Length', '/Filter', '/DecodeParms')}), depth + 1)
    if isinstance(a, DictionaryObject) or isinstance(b, DictionaryObject):
        return (isinstance(a, DictionaryObject) and isinstance(b, DictionaryObject) and set(a) == set(b)
                and all(k == '/Parent' or _same(a[k], b[k], depth + 1) for k in a))
    if isinstance(a, ArrayObject) or isinstance(b, ArrayObject):
        return isinstance(a, ArrayObject) and isinstance(b, ArrayObject) and len(a) == len(b) and all(_same(x, y, depth + 1) for x, y in zip(a, b))
    return a == b


def invisible_only(old, new):
    """True when `new` is `old` with only invisible text added: every page's own content streams the same bytes in the same order
    (closed in q … Q), the same boxes, turn and drawing resources (fonts may be added), and every added stream nothing but text in
    render mode 3. A proof by the file's structure — where no page can be drawn to compare (the browser edition)."""
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, ContentStream
    a, b = PdfReader(BytesIO(old)), PdfReader(BytesIO(new))
    if len(a.pages) != len(b.pages):
        return False
    for pa, pb in zip(a.pages, b.pages):
        for key in ('/MediaBox', '/CropBox', '/Rotate', '/UserUnit', '/Annots', '/Group'):
            if (key in pa) != (key in pb) or (key in pa and not _same(pa[key], pb[key])):
                return False
        ra, rb = pa.get('/Resources'), pb.get('/Resources')
        ra, rb = ra.get_object() if ra is not None else {}, rb.get_object() if rb is not None else {}
        if set(ra) - set(rb) or set(rb) - set(ra) - {'/Font'}:
            return False
        for k in ra:
            if k == '/Font':
                fa, fb = ra[k].get_object(), rb[k].get_object()
                if set(fa) - set(fb) or not all(_same(fa[x], fb[x]) for x in fa):
                    return False
            elif not _same(ra[k], rb[k]):
                return False
        ca = pa.get('/Contents')
        old_s = [] if ca is None else ([ca] if not isinstance(ca.get_object(), ArrayObject) else list(ca.get_object()))
        cb = pb.get('/Contents')
        new_s = [] if cb is None else ([cb] if not isinstance(cb.get_object(), ArrayObject) else list(cb.get_object()))
        if len(new_s) == len(old_s):
            if not all(x.get_object().get_data() == y.get_object().get_data() for x, y in zip(old_s, new_s)):
                return False
            continue
        if len(new_s) != len(old_s) + 3 or new_s[0].get_object().get_data().strip() != b'q' or new_s[-2].get_object().get_data().strip() != b'Q':
            return False
        if not all(x.get_object().get_data() == y.get_object().get_data() for x, y in zip(old_s, new_s[1:-2])):
            return False
        mode = None
        for operands, op in ContentStream(new_s[-1].get_object(), b).operations:
            if op not in ALLOWED:
                return False
            if op == b'Tr':
                mode = int(operands[0])
            if op == b'Tj' and mode != 3:
                return False
    return True
