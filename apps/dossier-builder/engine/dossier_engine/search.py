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
