"""Evidence: per-page text of the dossier's documents and keyword hits with page numbers and excerpts.
Absence is never inferred from a scan without a text layer: such documents are reported as not assessable."""
import io
import re

MAX_PAGES = 120
EXCERPT = 110


def pages_of(data, max_pages=MAX_PAGES):
    """[(page_no, text)] of a PDF; [] for non-PDF bytes. Text extraction only — no OCR here."""
    if not data or data[:4] != b'%PDF':
        return []
    from .. import pdfcraft
    got = pdfcraft.page_texts(data, max_pages=max_pages)
    if got is not None:
        return list(enumerate(got, 1))
    try:
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        out = []
        for i, p in enumerate(r.pages[:max_pages], 1):
            try:
                out.append((i, p.extract_text() or ''))
            except Exception:
                out.append((i, ''))
        return out
    except Exception:
        return []


def is_scanned(pages):
    if not pages:
        return True
    chars = sum(len(re.sub(r'\s', '', t)) for _, t in pages)
    return chars < 20 * len(pages)


def find(pages, keywords):
    """Distinct keywords found (case-insensitive substrings) with one hit each: {keyword, page, excerpt}."""
    hits = []
    for kw in keywords:
        k = kw.lower()
        for no, text in pages:
            i = text.lower().find(k)
            if i >= 0:
                a, b = max(0, i - EXCERPT), min(len(text), i + len(kw) + EXCERPT)
                ex = re.sub(r'\s+', ' ', text[a:b]).strip()
                hits.append({'keyword': kw, 'page': no, 'excerpt': ex})
                break
    return hits


class DocText:
    """Lazy, cached page text per document sha."""
    def __init__(self, store):
        self.store = store
        self._cache = {}

    def pages(self, doc):
        sha = doc['sha256']
        if sha not in self._cache:
            try:
                data = self.store.blob_path(sha).read_bytes()
            except OSError:
                data = b''
            self._cache[sha] = pages_of(data) if doc['filename'].lower().endswith('.pdf') or data[:5] == b'%PDF-' else _docx_pages(data, doc['filename'])
        return self._cache[sha]

    def scanned(self, doc):
        return doc['filename'].lower().endswith('.pdf') and is_scanned(self.pages(doc))


def _docx_pages(data, name=''):
    """The text of a source file (Word, Excel, PowerPoint, OpenDocument, RTF, text — old format or new) as one page."""
    try:
        from .. import extract
        text = extract.read_text(name, data)['text'] if extract.source_family(name, data) else ''
        return [(1, text)] if text else []
    except Exception:
        return []


def slot_documents(board, slot_ids):
    """Documents of the board slots whose req_id (or slot_id) is in slot_ids; per-API slots (req@api) are included."""
    want = set(slot_ids or [])
    out, slots = [], []
    for s in board['slots']:
        if s['req_id'] in want or s['slot_id'] in want:
            slots.append(s)
            for d in s['documents']:
                if not d['meta'].get('external'):
                    out.append((s, d))
    return slots, out
