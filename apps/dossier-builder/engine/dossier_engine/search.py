"""Full-text search in a dossier's documents (updates list, item 35): a batch number, a study's name, «Table 3». Each file's text is
read once, page by page, and kept by its SHA-256 (the store's doc_text table), so a search never reads a file twice. Case does not
count, nor alef / hamza forms, alef maqsura, ta marbuta, Arabic-Indic digits, or the spacing and line breaks between the words."""
import re
from io import BytesIO
from . import extract

_LIGHT = str.maketrans({'إ': 'ا', 'أ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ى': 'ي', 'ة': 'ه',
                        **{chr(0x660 + i): str(i) for i in range(10)}, **{chr(0x6F0 + i): str(i) for i in range(10)}})
MAX_HITS = 200          # a whole search: enough to see, never the whole dossier
PER_DOC = 8             # the matches shown for one document


def light(s):
    """One character for one: the matched span is the same span in the original text (the snippet keeps its own spelling)."""
    return (s or '').translate(_LIGHT)


def pattern(q):
    words = light(q).split()
    return re.compile(r'\s+'.join(re.escape(w) for w in words), re.I) if words else None


def pages_of(name, data):
    """The text of each page: a PDF page by page (a page number is what a person looks for); any other file as one page."""
    if (data or b'')[:5] == b'%PDF-':
        from pypdf import PdfReader
        try:
            rd = PdfReader(BytesIO(data), strict=False)
        except Exception:
            return ['']
        out = []
        for p in rd.pages:
            try:
                out.append(p.extract_text() or '')
            except Exception:
                out.append('')
        return out
    return [extract.read_text(name, data, max_pages=1).get('text') or '']


def diff(pages_a, pages_b, limit=400):
    """What changed from A to B, line by line: [{'op': 'removed'|'added', 'text', 'page'}] (the page in A for a removed line, in B for an
    added one). Spacing and line breaks inside a line do not count."""
    import difflib
    def lines(pages):
        out = []
        for i, p in enumerate(pages, 1):
            for ln in (p or '').splitlines():
                ln = ' '.join(ln.split())
                if ln:
                    out.append((ln, i))
        return out
    a, b = lines(pages_a), lines(pages_b)
    sm = difflib.SequenceMatcher(None, [x[0] for x in a], [x[0] for x in b], autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ('replace', 'delete'):
            out += [{'op': 'removed', 'text': t, 'page': pg} for t, pg in a[i1:i2]]
        if op in ('replace', 'insert'):
            out += [{'op': 'added', 'text': t, 'page': pg} for t, pg in b[j1:j2]]
        if len(out) >= limit:
            break
    return out[:limit]


def find(pages, rx, limit=PER_DOC):
    """[{page, snippet, start, length}] — `start`/`length` mark the match inside the snippet."""
    hits = []
    for i, txt in enumerate(pages):
        for m in rx.finditer(light(txt)):
            a, b = max(0, m.start() - 70), min(len(txt), m.end() + 70)
            lead = '…' if a else ''
            snippet = lead + re.sub(r'\s', ' ', txt[a:b]) + ('…' if b < len(txt) else '')
            hits.append({'page': i + 1, 'snippet': snippet, 'start': len(lead) + m.start() - a, 'length': m.end() - m.start()})
            if len(hits) >= limit:
                return hits
    return hits
