"""Split and merge pages (updates list, item 12). A file that holds several documents (a licence, a pricing certificate and two
certificates of analysis scanned into one PDF) is cut where a new document starts; a document scanned as separate files is joined
into one. The program proposes the cuts — a page that reads as another kind of document, or that says it is «page 1 of …» — and the
person confirms or moves them; nothing is cut on a guess."""
import re
from io import BytesIO
from . import extract, search

FIRST_PAGE = re.compile(r'(?:\bpage\s*1\s*(?:of|/)\s*\d+\b|صفحة\s*[1١]\s*(?:من|/)\s*[\d٠-٩]+)', re.I)


def head_line(text):
    """The first line a person would read as the page's title."""
    for ln in (text or '').splitlines():
        ln = re.sub(r'\s+', ' ', ln).strip()
        if len(re.sub(r'[\W\d_]', '', ln)) >= 4:
            return ln[:90]
    return ''


def propose(data, pack=None):
    """{pages, parts: [{from, to, kind, title, homes}], page_info: [{page, kind, title, starts}]} — a part starts at page 1, at a page
    that reads as a different kind of document than the part it would join, and at a page that says «page 1 of N»; a page whose kind
    is not recognised continues the part before it."""
    pages = search.pages_of('file.pdf', data)
    info, parts = [], []
    for i, txt in enumerate(pages, 1):
        kind = extract.content_kind(txt) if txt.strip() else 'other'
        cur = parts[-1] if parts else None
        if cur is None:
            starts = True
        elif FIRST_PAGE.search(txt[:3000]):
            starts = True                                  # «page 1 of 3»: a document begins here
        elif kind != 'other' and cur['kind'] != 'other':
            starts = kind != cur['kind'] or bool(batch_of(txt) and cur.get('batch') and batch_of(txt) != cur['batch'])   # another kind, or another batch's certificate
        else:
            starts = kind != 'other' and _strong(txt)      # after pages that were not recognised: a page titled as a document
        info.append({'page': i, 'kind': kind, 'kind_name': extract.KIND_NAMES.get(kind), 'title': head_line(txt), 'starts': bool(starts)})
        if starts:
            parts.append({'from': i, 'to': i, 'kind': kind, 'title': head_line(txt), 'batch': batch_of(txt)})
        else:
            cur['to'] = i
            cur['batch'] = cur.get('batch') or batch_of(txt)
            if cur['kind'] == 'other' and kind != 'other':
                cur['kind'] = kind
    for p in parts:
        p['homes'] = extract.kind_homes(p['kind'], pack) if p['kind'] != 'other' else []
        p['kind_name'] = extract.KIND_NAMES.get(p['kind'])
    return {'pages': len(pages), 'parts': parts, 'page_info': info}


BATCH = re.compile(r'(?:batch|lot)\s*(?:no\.?|number|#)?\s*[:：.]?\s*([A-Z0-9][A-Z0-9/-]{2,})', re.I)


def batch_of(text):
    m = BATCH.search(text or '')
    return m.group(1).upper() if m else None


def _strong(text):
    """A page whose top names a document (a certificate, a licence, a report): the start of one, after unrecognised pages."""
    top = (text or '')[:400].lower()
    return any(w in top for w in ('certificate', 'licence', 'license', 'report', 'approval', 'شهادة', 'إخطار', 'اخطار', 'موافقة', 'تقرير'))


def ranges_from_starts(starts, n):
    """[1, 3, 6] with 8 pages → [(1, 2), (3, 5), (6, 8)]."""
    s = sorted({int(x) for x in starts if 1 <= int(x) <= n} | {1})
    return [(a, (s[k + 1] - 1) if k + 1 < len(s) else n) for k, a in enumerate(s)]


def count(data):
    """The number of pages (PdfCraft; pypdf where it is not)."""
    from . import pdfcraft
    n = pdfcraft.page_count(data)
    if n is not None:
        return n
    from pypdf import PdfReader
    return len(PdfReader(BytesIO(data), strict=False).pages)


def split(data, ranges):
    """The PDF of each page range (1-based, inclusive). Ranges must cover the pages in order without overlap. PdfCraft copies each
    part with the links, bookmarks and fields of its pages; pypdf, where PdfCraft is not, copies the pages."""
    from . import pdfcraft
    n = count(data)
    want = 1
    for a, b in ranges:
        if a != want or b < a or b > n:
            raise ValueError(f'pages {a}–{b} do not continue from page {want} (the file has {n} pages)')
        want = b + 1
    if want != n + 1:
        raise ValueError(f'pages {want}–{n} are left out')
    if pdfcraft.available():
        return pdfcraft.split(data, ranges)
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(BytesIO(data), strict=False)
    out = []
    for a, b in ranges:
        w = PdfWriter()
        for k in range(a - 1, b):
            w.add_page(rd.pages[k])
        buf = BytesIO()
        w.write(buf)
        out.append(buf.getvalue())
    return out


def bound(parts, title, left_out=()):
    """One PDF for reading: a first page with the title and what was left out, then each part's pages, every module, item and
    document a bookmark. parts: [(module_label, item_label, doc_label, pdf_bytes)]."""
    import tempfile
    from pathlib import Path
    from . import pdfcraft
    from .generate.docx_kit import text_pdf
    tmp = Path(tempfile.mkdtemp()) / 'first.pdf'
    first = Path(text_pdf([title, ''] + ([f'Left out (not PDF): {x}' for x in left_out] or ['Every document is included.']), tmp)).read_bytes()
    if pdfcraft.available():
        try:
            return _bound_pdfcraft(first, parts)
        except pdfcraft.PdfCraftError:
            pass                                           # the earlier way below
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for p in PdfReader(BytesIO(first)).pages:
        w.add_page(p)
    marks, cur_mod, cur_item = {}, None, None
    for mod, item, doc, data in parts:
        try:
            rd = PdfReader(BytesIO(data), strict=False)
            start = len(w.pages)
            for p in rd.pages:
                w.add_page(p)
        except Exception:
            continue
        if mod != cur_mod:
            marks['mod'] = w.add_outline_item(mod, start)
            cur_mod, cur_item = mod, None
        if item != cur_item:
            marks['item'] = w.add_outline_item(item, start, parent=marks['mod'])
            cur_item = item
        w.add_outline_item(doc, start, parent=marks['item'])
    w.page_mode = '/UseOutlines'
    buf = BytesIO()
    w.write(buf)
    return buf.getvalue()


def _bound_pdfcraft(first, parts):
    """The reading copy by PdfCraft: the files combined, each document's own bookmarks kept under its entry, the entries arranged as
    module ▸ item ▸ document, and the copy opening with its bookmarks."""
    from . import pdfcraft
    ok = []
    for mod, item, doc, data in parts:
        n = pdfcraft.page_count(data)
        if n:                                              # a part that cannot be read is left out, as before
            ok.append((mod, item, doc, data, n))
    with pdfcraft.Job() as j:
        names = [j.put('p0000.pdf', first)] + [j.put(f'p{k:04d}.pdf', d[3]) for k, d in enumerate(ok, 1)]
        j.steps.append({'tool': 'doc_combine', 'args': {'paths': names, 'out': 'combined.pdf', 'open': False}})
        j.step('doc_open', path='combined.pdf')
        j.step('bookmark_delete', doc=1, path=[1])           # the first page's own entry
        page = 1 + pdfcraft.page_count(first)
        mods, cur_mod, cur_item, items = 0, None, None, 0
        for mod, item, doc, data, n in ok:
            if mod != cur_mod:
                mods += 1
                j.step('bookmark_add', doc=1, title=mod, page=page, position=mods)
                cur_mod, cur_item, items = mod, None, 0
            if item != cur_item:
                items += 1
                j.step('bookmark_add', doc=1, title=item, page=page, parent=[mods])
                cur_item = item
            j.step('bookmark_rename', doc=1, path=[mods + 1], title=doc)        # this file's entry: the first after the modules
            j.step('bookmark_move', doc=1, path=[mods + 1], parent=[mods, items])
            page += n
        j.step('doc_initial_view', doc=1, navigation='bookmarks')
        j.step('doc_save', doc=1, path='bound.pdf', full=True)
        j.run()
        return j.read('bound.pdf')


def merge(datas):
    """One PDF of all the given PDFs' pages, in the order given (PdfCraft keeps each file's bookmarks; pypdf where it is not)."""
    from . import pdfcraft
    if pdfcraft.available():
        return pdfcraft.combine(list(datas))
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter()
    for data in datas:
        for p in PdfReader(BytesIO(data), strict=False).pages:
            w.add_page(p)
    buf = BytesIO()
    w.write(buf)
    return buf.getvalue()
