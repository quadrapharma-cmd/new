"""Writer — NeeS, the Non-eCTD electronic Submission (updates list, item 40), for the authorities that still take one.

A NeeS is the eCTD's folders and file names without its XML backbone: the reviewer finds the documents through tables of contents
in PDF whose entries link to the files. The layout follows the EU NeeS guidance, which the GCC and other authorities took over:

  <sequence>/ctd-toc.pdf               the dossier's table of contents: each module, linked to the module's own table
  <sequence>/m1/m1-toc.pdf … m5/…      each section of the module and its documents, each linked to its file
  folders and names                     the eCTD's: ICH Appendix 4 for Modules 2–5 (a substance folder per substance and
                                        manufacturer, a product folder), m1/<country>/<section> for Module 1; lower case, no spaces

Links are relative (a PDF opens another PDF: GoToR), so the package works from any disk or CD. Every table is text with bookmarks.
There is no index.xml, no regional XML and no checksum file. An authority's own NeeS guidance can name Module 1 differently: the
countries table (updates list, item 41) says which authority takes a NeeS and by which guidance — check it before filing."""
import io, posixpath, re, shutil
from pathlib import Path
from .ectd32 import Profile32, WriterError

MAX_NAME = 64                                            # ICH eCTD folder / file name length, kept for a NeeS too
_NOT = re.compile(r'[^a-z0-9]+')


def clean(s, n=40):
    """«Stability (summary, protocol & commitment)» → «stability-summary-protocol-commitment»: a-z, 0-9 and hyphens only."""
    out = _NOT.sub('-', (s or '').lower()).strip('-')[:n].strip('-')
    return out or 'document'


def _ich(profile, node):
    try:
        el = profile.ich_element(node)
        return profile.ich_location(el)
    except WriterError:
        return None


def placement(slots, files, product_name, country, profile=None):
    """[(slot, file, path inside the sequence)] for every PDF of every active item, in the dossier's order. A document that is not a PDF
    (a Word draft) is left out and said: a NeeS takes PDF only."""
    profile = profile or Profile32()
    out, taken, left = [], set(), []
    cc = clean(country or 'xx', 8)
    for s in slots:
        if not s.active:
            continue
        got = files.get(s.slot_id, [])
        node = (s.ectd or [None])[0] or s.ctd.split(' (')[0]
        loc = _ich(profile, node) if s.module in (2, 3, 4, 5) and node else None
        for i, f in enumerate(got):
            if not str(f.get('file', '')).lower().endswith('.pdf') and (f.get('ext') or '.pdf') != '.pdf':
                left.append({'slot_id': s.slot_id, 'file': f.get('title') or s.title['en'], 'why': 'not a PDF'})
                continue
            if loc:
                d, default = loc
                if s.item:                               # one folder per substance and manufacturer, as the eCTD
                    d = d.replace('substance-1-manufacturer-1', clean(f"{s.item['name']}-{s.item['manufacturer']}", 60))
                d = d.replace('product-1', clean(product_name or 'product', 60))
                name = default if (default and len(got) == 1) else clean(f.get('title') or s.title['en']) + '.pdf'
            else:
                sec = s.ctd.split(' (')[0]
                d = f"m{s.module}/{cc}/{clean(sec, 16)}" if s.module == 1 else f"m{s.module}/{clean(sec, 16)}"
                name = clean(f.get('title') or s.title['en']) + '.pdf'
            path, k = posixpath.join(d, name), 2
            while path in taken:                         # a second document of the same name: -2, -3…
                path = posixpath.join(d, name[:-4][:MAX_NAME - 7] + f'-{k}.pdf')
                k += 1
            taken.add(path)
            out.append((s, f, path))
    return out, left


def _ascii(s):
    return (s or '').encode('latin-1', 'replace').decode('latin-1')


def _pdf_str(s):
    b = _ascii(s).encode('latin-1', 'replace')
    return b.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')


def _toc_pdf(title, entries, here):
    """A table of contents as PDF bytes (A4, Helvetica — no other library than pypdf, so the browser edition makes it too):
    `entries` [(level, text, target path or None)]; each line with a target is a link to it, relative to the table's folder
    `here` (GoToR, the first page, whole); the section lines are the bookmarks."""
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, BooleanObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject,
                               NumberObject, TextStringObject)
    W, H, TOP, BOTTOM, LEFT = 595.0, 842.0, 790.0, 50.0, 50.0
    pages, cur, y = [], [], TOP - 26
    for level, text, target in entries:
        size, step = (11, 16) if level == 0 else (9.5, 13)
        if y - step < BOTTOM:
            pages.append(cur); cur, y = [], TOP - 26
        cur.append((level, text, target, y, size))
        y -= step
    pages.append(cur)
    w = PdfWriter()
    f1 = w._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                                         NameObject('/BaseFont'): NameObject('/Helvetica'), NameObject('/Encoding'): NameObject('/WinAnsiEncoding')}))
    f2 = w._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                                         NameObject('/BaseFont'): NameObject('/Helvetica-Bold'), NameObject('/Encoding'): NameObject('/WinAnsiEncoding')}))
    marks = []
    for pi, lines in enumerate(pages):
        page = w.add_blank_page(W, H)
        ops = [b'BT /F2 13 Tf %.1f %.1f Td (' % (LEFT, TOP) + _pdf_str(title)[:110] + b') Tj ET']
        annots = ArrayObject()
        for level, text, target, ly, size in lines:
            x = LEFT + 14 * level
            room = int((W - x - LEFT) / (size * 0.52))       # Helvetica's average width: keep the line on the page
            s = text if len(text) <= room else text[:max(room - 3, 8)] + '...'
            ops.append(b'BT %s %.1f Tf %s rg %.1f %.1f Td (' % (b'/F2' if level == 0 else b'/F1', size, b'0 0 0.55' if target else b'0 0 0', x, ly)
                       + _pdf_str(s) + b') Tj ET')
            if target:
                rel = posixpath.relpath(target, here) if here else target
                annots.append(w._add_object(DictionaryObject({
                    NameObject('/Type'): NameObject('/Annot'), NameObject('/Subtype'): NameObject('/Link'),
                    NameObject('/Rect'): ArrayObject([FloatObject(x), FloatObject(ly - 2), FloatObject(min(W - LEFT, x + len(s) * size * 0.52)), FloatObject(ly + size)]),
                    NameObject('/Border'): ArrayObject([NumberObject(0)] * 3),
                    NameObject('/A'): DictionaryObject({NameObject('/S'): NameObject('/GoToR'), NameObject('/F'): TextStringObject(rel),
                                                        NameObject('/D'): ArrayObject([NumberObject(0), NameObject('/Fit')]),
                                                        NameObject('/NewWindow'): BooleanObject(True)})})))
            if level == 0:
                marks.append((pi, s))
        content = DecodedStreamObject()
        content.set_data(b'\n'.join(ops))
        page[NameObject('/Contents')] = w._add_object(content)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): f1, NameObject('/F2'): f2})})
        if annots:
            page[NameObject('/Annots')] = annots
    for pi, s in marks:
        w.add_outline_item(_ascii(s), pi)
    w.add_metadata({'/Title': _ascii(title)})
    w.page_mode = '/UseOutlines'
    w.pdf_header = '%PDF-1.7'                            # PDF 1.4–1.7, as the eCTD's files (pypdf would write 1.3)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def write(out_dir, seq, slots, files, product_name, country='xx', title=''):
    """The NeeS sequence folder `out_dir/<seq>`: the documents at their places, the module tables and the dossier's table.
    → {'path', 'files', 'left_out', 'tocs'}"""
    root = Path(out_dir) / seq
    if root.exists():
        raise WriterError(f'{root} exists — an export is never overwritten')
    placed, left = placement(slots, files, product_name, country)
    by_mod = {}
    for s, f, path in placed:
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f['file'], dest)
        by_mod.setdefault(s.module, []).append((s, f, path))
    tocs = []
    for m in sorted(by_mod):
        entries, last = [], None
        for s, f, path in by_mod[m]:
            sec = s.ctd.split(' (')[0] + (f" — {s.item['name']} ({s.item['manufacturer']})" if s.item else '')
            if sec != last:
                entries.append((0, f"{sec}  {s.title['en']}", None))
                last = sec
            entries.append((1, f.get('title') or s.title['en'], path))
        toc = f'm{m}/m{m}-toc.pdf'
        (root / toc).parent.mkdir(parents=True, exist_ok=True)
        (root / toc).write_bytes(_toc_pdf(f'{title or product_name} — Module {m} table of contents', entries, f'm{m}'))
        tocs.append(toc)
    names = {1: 'Administrative information', 2: 'Summaries', 3: 'Quality', 4: 'Nonclinical study reports', 5: 'Clinical study reports'}
    (root / 'ctd-toc.pdf').write_bytes(_toc_pdf(f'{title or product_name} — CTD table of contents (sequence {seq})',
                                                [(0, f'Module {m} — {names.get(m, "")}', f'm{m}/m{m}-toc.pdf') for m in sorted(by_mod)], ''))
    return {'path': str(root), 'files': sorted(p for _, _, p in placed), 'left_out': left, 'tocs': ['ctd-toc.pdf'] + tocs}


def check(seq_dir):
    """The NeeS read back from the disk: every table's link reaches its file, names are the eCTD's (a-z, 0-9, hyphens, ≤ 64), paths
    ≤ 180, no XML backbone. → the report shape of the eCTD validators ({ok, counts, coverage, label, results})."""
    from pypdf import PdfReader
    root = Path(seq_dir)
    res = []

    def rule(rid, text, fails):
        res.append({'rule': rid, 'severity': 'pass_fail', 'text': text, 'provenance': 'EU NeeS guidance', 'source': 'NeeS',
                    'status': 'fail' if fails else 'pass', 'failures': fails[:20]})
    tocs = [root / 'ctd-toc.pdf'] + sorted(root.glob('m*/m*-toc.pdf'))
    rule('NEES-1', 'The CTD table of contents (ctd-toc.pdf) is in the sequence folder and each module has its own table.',
         [] if (root / 'ctd-toc.pdf').is_file() and len(tocs) > 1 else ['ctd-toc.pdf or a module table missing'])
    broken, links = [], 0
    for toc in tocs:
        if not toc.is_file():
            continue
        for page in PdfReader(str(toc)).pages:
            for a in page.get('/Annots') or []:
                a = a.get_object()
                act = a.get('/A') or {}
                if act.get('/S') == '/GoToR':
                    links += 1
                    target = (toc.parent / str(act.get('/F'))).resolve()
                    if not target.is_file() or root.resolve() not in target.parents:
                        broken.append(f'{toc.relative_to(root)} → {act.get("/F")}')
    rule('NEES-2', 'Every entry of every table links to its file by a relative link that reaches it.', broken)
    bad, longp, xml = [], [], []
    for f in root.rglob('*'):
        rel = f.relative_to(root).as_posix()
        if f.is_file() and f.suffix.lower() == '.xml':
            xml.append(rel)
        part = f.name
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*(\.pdf)?', part) or len(part) > MAX_NAME:
            bad.append(rel)
        if len(f'{root.name}/{rel}') > 180:
            longp.append(rel)
    rule('NEES-3', 'Folder and file names: lower-case letters, digits and hyphens, at most 64 characters.', bad)
    rule('NEES-4', 'Paths at most 180 characters from the sequence folder.', longp)
    rule('NEES-5', 'No XML backbone (a NeeS is not an eCTD).', xml)
    n_fail = sum(1 for r in res if r['status'] == 'fail')
    return {'ok': not n_fail, 'counts': {'pass': len(res) - n_fail, 'fail': n_fail, 'warning': 0, 'not_run': 0}, 'coverage': f'{len(res)}/{len(res)}',
            'label': f'NeeS: {links} links checked.' if not n_fail else 'NeeS: does not pass its own checks.', 'results': res}
