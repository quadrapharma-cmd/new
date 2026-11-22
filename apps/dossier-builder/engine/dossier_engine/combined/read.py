"""Stage 1 — what was received, page by page.

Every PDF of the source folder is one run of pages, numbered across the files in their natural order (one combined file: its
own page numbers). For each page: its text as the file carries it (pdftotext, no layout — the headings are read from it), the
number of characters, its byte signature (content stream and pictures: two pages with the same signature are the same page),
and a picture of it at 24 dpi in grey (two pages drawn alike at 24 dpi are the same page recompressed). The bookmarks are read
with the page each opens. Word files (by their content: RTF, Word 97–2003, Word 2007+) are made PDF by LibreOffice and, when a
combined PDF came with them, kept aside and compared with it: their words against the PDF's blocks.

Writes read/files.json, read/pages.json, read/outline.json, read/text.txt and read/thumbs/p00001.png …"""
import concurrent.futures as cf
import difflib
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pikepdf
from PIL import Image

from .common import NO_TEXT, Work, natural, pdftext, say, sha256_file, soffice_pdf, tool

WORD_EXT = {'.doc', '.docx', '.rtf', '.dot', '.dotx', '.odt'}


def kind_of(path):
    head = path.read_bytes()[:8] if path.stat().st_size else b''
    if head.startswith(b'%PDF'):
        return 'pdf'
    if head.startswith(b'{\\rtf'):
        return 'rtf'
    if head.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):
        return 'doc'
    if head.startswith(b'PK') and path.suffix.lower() in ('.docx', '.dotx', '.odt'):
        return 'docx'
    if path.suffix.lower() == '.pdf':
        return 'pdf'
    if path.suffix.lower() in WORD_EXT:
        return 'doc'
    return 'other'


def proper_name(path, kind):
    """The name a received file is kept under: its own, with the extension its content has (an RTF named «.doc» becomes «.rtf»)."""
    ext = {'rtf': '.rtf', 'doc': '.doc', 'docx': path.suffix.lower() if path.suffix.lower() in ('.docx', '.dotx', '.odt') else '.docx'}.get(kind)
    if ext and path.suffix.lower() != ext:
        return path.stem + ext
    return path.name


def signature(page):
    """The page's content stream and its pictures, by their bytes (the same reading as the hand-built dossier's)."""
    h = hashlib.sha256()
    c = page.obj.get('/Contents')
    if c is not None:
        try:
            h.update(b''.join(x.read_bytes() for x in c) if isinstance(c, pikepdf.Array) else c.read_bytes())
        except Exception:
            pass
    res = page.obj.get('/Resources')
    if res is not None and '/XObject' in res:
        for k in sorted(res.XObject.keys()):
            try:
                h.update(res.XObject[k].read_raw_bytes())
            except Exception:
                pass
    return h.hexdigest()


def images_on(page):
    n = 0

    def walk(res, depth=0):
        nonlocal n
        if res is None or depth > 4 or '/XObject' not in res:
            return
        for k in res.XObject.keys():
            x = res.XObject[k]
            st = x.get('/Subtype')
            if st == '/Image':
                n += 1
            elif st == '/Form':
                walk(x.get('/Resources'), depth + 1)
    try:
        walk(page.obj.get('/Resources'))
    except Exception:
        pass
    return n


def outline_of(pdf, offset):
    """The bookmarks: [{level, title, page}] with the page in the run's numbering (None when the bookmark opens nothing)."""
    index = {p.objgen: i for i, p in enumerate(pdf.pages)}
    named = {}
    try:
        names = pdf.Root.get('/Names')
        if names is not None and '/Dests' in names:
            nt = pikepdf.NameTree(names.Dests)
            for k in nt.keys():
                named[str(k)] = nt[k]
        dests = pdf.Root.get('/Dests')
        if dests is not None:
            for k in dests.keys():
                named[str(k)[1:] if str(k).startswith('/') else str(k)] = dests[k]
    except Exception:
        pass

    def page_of(item):
        d = item.destination
        if d is None and item.action is not None and item.action.get('/S') == '/GoTo':
            d = item.action.get('/D')
        if isinstance(d, (pikepdf.String, pikepdf.Name, str)):
            d = named.get(str(d)[1:] if isinstance(d, pikepdf.Name) else str(d))
            if isinstance(d, pikepdf.Dictionary):
                d = d.get('/D')
        try:
            if isinstance(d, pikepdf.Array) and len(d):
                return index.get(d[0].objgen, None) + 1 + offset if d[0].objgen in index else None
            if isinstance(d, int):
                return int(d) + 1 + offset
        except Exception:
            return None
        return None

    out = []

    def walk(items, level):
        for it in items:
            out.append({'level': level, 'title': ' '.join(str(it.title or '').split()), 'page': page_of(it)})
            walk(it.children, level + 1)
    try:
        with pdf.open_outline() as ol:
            walk(ol.root, 0)
    except Exception:
        pass
    return out


def thumbs(pdf_path, first_global, n_pages, outdir, jobs=4):
    """Every page drawn at 24 dpi in grey: read/thumbs/p00001.png … (the global page number)."""
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = outdir / f'_{first_global}'
    tmp.mkdir(exist_ok=True)
    step = max(1, -(-n_pages // jobs))
    chunks = [(a, min(n_pages, a + step - 1)) for a in range(1, n_pages + 1, step)]

    def one(ch):
        a, b = ch
        subprocess.run([tool('pdftoppm'), '-r', '24', '-gray', '-png', '-f', str(a), '-l', str(b), str(pdf_path), str(tmp / f'c{a:06d}')],
                       check=True, capture_output=True)
        return ch
    with cf.ThreadPoolExecutor(jobs) as ex:
        list(ex.map(one, chunks))
    for f in sorted(tmp.iterdir()):
        m = re.search(r'-(\d+)\.png$', f.name)
        if m:
            f.replace(outdir / f'p{first_global + int(m.group(1)) - 1:05d}.png')
    shutil.rmtree(tmp)


def thumb_hash(path):
    try:
        im = Image.open(path).convert('L')
        return hashlib.sha1(im.tobytes() + str(im.size).encode()).hexdigest()
    except Exception:
        return None


def to_pdf(src, name, outdir):
    """A Word file made PDF by LibreOffice, from a copy under the name its content calls for (a «.doc» holding RTF is opened as
    the RTF it is)."""
    outdir.mkdir(parents=True, exist_ok=True)
    work = outdir / '_in'
    work.mkdir(exist_ok=True)
    tmp = work / name
    shutil.copyfile(src, tmp)
    soffice_pdf(tmp, outdir, timeout=900)
    tmp.unlink()
    work.rmdir()
    out = outdir / (tmp.stem + '.pdf')
    return out if out.exists() else None


def words(text):
    return re.findall(r'[A-Za-z0-9]+', text.lower())


def run(src, work, jobs=4):
    w = work if isinstance(work, Work) else Work(work)
    src = Path(src).resolve()
    items = [src] if src.is_file() else sorted((p for p in src.rglob('*') if p.is_file()), key=lambda p: natural(p.relative_to(src)))
    files, texts, pages, outline = [], [], [], []
    n = 0
    for p in items:
        k = kind_of(p)
        rec = {'name': p.name, 'path': str(p), 'kind': k, 'size': p.stat().st_size, 'sha256': sha256_file(p),
               'keep_as': proper_name(p, k)}
        if k == 'pdf':
            say(f'قراءة {p.name}')
            pdf = pikepdf.open(p)
            count = len(pdf.pages)
            rec.update({'pages': count, 'from': n + 1, 'to': n + count, 'version': pdf.pdf_version})
            t = pdftext(p)
            t += [''] * (count - len(t))
            texts += t[:count]
            for i, pg in enumerate(pdf.pages):
                box = pg.mediabox
                pages.append({'n': n + i + 1, 'file': len(files), 'index': i + 1, 'chars': len(t[i].strip()),
                              'images': images_on(pg), 'sig': signature(pg),
                              'w': round(float(box[2]) - float(box[0]), 1), 'h': round(float(box[3]) - float(box[1]), 1),
                              'rotate': int(pg.obj.get('/Rotate', 0) or 0)})
            outline += outline_of(pdf, n)
            pdf.close()
            say(f'رسم الصفحات بدقة 24 نقطة في البوصة ({count} صفحة)')
            thumbs(p, n + 1, count, w.read / 'thumbs', jobs)
            n += count
        files.append(rec)
    for pg in pages:
        pg['thumb'] = thumb_hash(w.read / 'thumbs' / f"p{pg['n']:05d}.png")
    # Word files: made PDF; kept aside when a PDF came with them, compared with the PDF's top blocks
    has_pdf = any(f['kind'] == 'pdf' for f in files)
    tops = [o for o in outline if o['level'] == 0 and o['page']]
    for f in files:
        if f['kind'] not in ('rtf', 'doc', 'docx'):
            continue
        say(f'تحويل {f["name"]} إلى PDF')
        pdf = None
        try:
            pdf = to_pdf(Path(f['path']), f['keep_as'], w.read / 'word')
        except Exception as e:                           # noqa: BLE001 — said in the record
            f['convert_error'] = str(e)[:200]
        f['pdf'] = str(pdf) if pdf else None
        f['aside'] = has_pdf
        if pdf and has_pdf:
            mine = words(' '.join(pdftext(pdf)))
            f['words'] = len(mine)
            best = None
            for i, t in enumerate(tops):
                end = tops[i + 1]['page'] - 1 if i + 1 < len(tops) else n
                theirs = words(' '.join(texts[t['page'] - 1:end]))
                common = len(set(mine) & set(theirs))
                if best is None or common > best[0]:
                    best = (common, t, end, theirs)
            if best:
                sm = difflib.SequenceMatcher(None, best[3], mine, autojunk=False)
                same = sum(b.size for b in sm.get_matching_blocks())
                f['matches'] = {'block': best[1]['title'], 'from': best[1]['page'], 'to': best[2], 'same_words': same,
                                'block_words': len(best[3])}
    (w.read / 'text.txt').write_text('\f'.join(texts), encoding='utf-8')
    w.save('read/files.json', files)
    w.save('read/pages.json', pages)
    w.save('read/outline.json', outline)
    no_text = sum(1 for p in pages if p['chars'] < NO_TEXT)
    say(f'{len(files)} ملفًا · {n} صفحة · {no_text} صفحة بلا نص · {len(outline)} إشارة مرجعية')
    return {'files': len(files), 'pages': n, 'no_text': no_text, 'bookmarks': len(outline)}
