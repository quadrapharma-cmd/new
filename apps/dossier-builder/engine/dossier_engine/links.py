"""Links between the dossier's documents (updates list, item 25).

A link is made where the document is written — in Word («Insert › Link» to the other file), or in the PDF. Whatever it points to
on the author's disk (C:\\Dossier\\3.2.P.8 stability.docx, ../stability.pdf, file:///…/batch-analyses.pdf), the program finds
the dossier's document of that name or title, and when it writes a sequence it turns the link into the relative link the eCTD
needs (a PDF opening another PDF: GoToR) from the file's place to the target's place in this sequence — or in an earlier one
(../0000/m3/…), where an unchanged document stayed. The places come from the sequence being written, so a link follows its target
when the target's name or folder changes. Web links (http, https, mailto) are left alone; a file link with no document of that
name in the dossier is reported, not guessed."""
import io, posixpath, re
from urllib.parse import unquote, urlparse

WEB = ('http:', 'https:', 'mailto:', 'ftp:', 'tel:')


def key(name):
    """«C:\\Dossier\\3.2.P.8 Stability.DOCX#page=2» → «3-2-p-8-stability»: the file's stem, lower-case, in letters and digits."""
    s = unquote(str(name or '')).split('#', 1)[0].split('?', 1)[0].replace('\\', '/')
    stem = posixpath.basename(s.rstrip('/'))
    stem = re.sub(r'\.(pdf|docx?|rtf|odt)$', '', stem, flags=re.I)
    return re.sub(r'[^a-z0-9\u0600-\u06ff]+', '-', stem.lower()).strip('-')


def _target(action):
    """The file a link action points to, or None (a web link, a link inside the same document)."""
    s = action.get('/S')
    if s == '/URI':
        uri = str(action.get('/URI') or '')
        if uri.lower().startswith(WEB):
            return None
        return urlparse(uri).path if uri.lower().startswith('file:') else uri
    if s in ('/GoToR', '/Launch'):
        f = action.get('/F')
        if f is None:
            return None
        f = f.get_object() if hasattr(f, 'get_object') else f
        if isinstance(f, dict) or hasattr(f, 'get'):
            f = f.get('/UF') or f.get('/F')
        return str(f) if f else None
    return None


def _index(entries):
    """entries: [(doc_id, names, path)] → ({key: {path}} by file name, {key: {path}} by title): a file name answers before a title."""
    by_file, by_title = {}, {}
    for _, names, path in entries:
        names = list(names or ())
        for i, n in enumerate(names[:2]):
            k = key(n)
            if k:
                (by_file if i == 0 else by_title).setdefault(k, set()).add(path)
    return by_file, by_title


def _resolve(k, index):
    """The one path a link's key names, or (None, why)."""
    for m in index:
        hit = m.get(k)
        if hit:
            return (next(iter(hit)), None) if len(hit) == 1 else (None, f'{len(hit)} documents have this name')
    return None, 'no document of the dossier has this name'


def relink(base, placed, earlier=None):
    """Rewrite the links of every PDF written in the sequence folder `base`. placed: [(Doc, rel)] of this sequence (a Doc carries
    `aliases`: its uploaded file name, then its title); earlier: [(doc_id, names, path from the sequence folder '../0000/m3/…')] of
    the documents sent before and not in this sequence. A link is rewritten only when exactly one document answers its name.
    → {'rewritten': n, 'unresolved': [{'file', 'link', 'why'}]}"""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, BooleanObject, DictionaryObject, NameObject, NumberObject, TextStringObject
    here = {getattr(d, 'doc_id', None) for d, rel in placed if rel}
    entries = [(d.doc_id, getattr(d, 'aliases', None) or (), rel) for d, rel in placed if rel]
    entries += [e for e in (earlier or []) if e[0] not in here]
    index = _index(entries)
    out = {'rewritten': 0, 'unresolved': []}
    for d, rel in placed:
        if not rel or getattr(d, 'ref', None) or not rel.lower().endswith('.pdf'):
            continue
        path = base / rel
        try:
            r = PdfReader(str(path))
            w = PdfWriter(clone_from=r)
            w.pdf_header = r.pdf_header if r.pdf_header >= '%PDF-1.4' else '%PDF-1.7'   # a copy keeps the file's version (pypdf writes 1.3)
        except Exception:
            continue
        changed = False
        for page in w.pages:
            for a in page.get('/Annots') or []:
                ann = a.get_object()
                if ann.get('/Subtype') != '/Link' or '/A' not in ann:
                    continue
                t = _target(ann['/A'].get_object())
                if not t:
                    continue
                dest, why = _resolve(key(t), index)
                if not dest:
                    out['unresolved'].append({'file': rel, 'link': t, 'why': why})
                    continue
                to = posixpath.relpath(dest, posixpath.dirname(rel) or '.')
                ann[NameObject('/A')] = DictionaryObject({NameObject('/S'): NameObject('/GoToR'), NameObject('/F'): TextStringObject(to),
                                                          NameObject('/D'): ArrayObject([NumberObject(0), NameObject('/Fit')]),
                                                          NameObject('/NewWindow'): BooleanObject(True)})
                changed = True
                out['rewritten'] += 1
        if changed:
            buf = io.BytesIO()
            w.write(buf)
            path.write_bytes(buf.getvalue())
    return out


def earlier_targets(history, names_of):
    """[(doc_id, names, '../<seq>/<href>')] for the current documents of earlier sequences (the newest leaf of each), so a link reaches
    a document that stayed in the sequence it was sent in. history: the writer's sequences [{seq, leaves}]; names_of: {doc_id: [file
    name, title]} of the dossier's current documents."""
    last = {}
    for h in history:
        for lf in h['leaves']:
            if lf.get('op') == 'delete' or not lf.get('href') or lf.get('doc_id') not in names_of:
                continue
            last[lf['doc_id']] = f"../{h['seq']}/{lf['href']}"
    return [(i, names_of[i], p) for i, p in last.items()]
