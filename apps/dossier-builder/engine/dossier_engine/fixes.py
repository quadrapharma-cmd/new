"""Automatic technical fixes (02-LOGIC §6 «allowed technical ops»). No OCR: a PDF without text is refused at upload and its
text layer is made when scanning.

PdfCraft makes the fixes where it is here (docs/ctd/PDFCRAFT-INTEGRATION.md): it repairs a damaged file, removes security, document
JavaScript, attachments and comments, redacts for real under faux-redaction boxes, makes bookmarks from the document's tagged headings,
or its numbered headings at their place on the page, or its heading type styles, sets how the document opens and its properties, and
draws the pages for the page-for-page comparison. pypdf does them where PdfCraft is not (the browser edition), and two things PdfCraft
has no tool for: keeping a link's place while its zoom becomes the reader's, and removing restrictions a file was given without an
owner password (the company's own documents only).

Each finding whose action is auto_fix maps to an operation. Every operation is
checked by the guard for the document's class, and for read-only evidence
(third-party, EDA, executed, signed scans) the result must be page-for-page
pixel-identical to the original — otherwise the fix is discarded and the user is
told to re-obtain the document. Digitally signed PDFs are never rewritten
(it would break the signature). The original is never modified: the caller
stores the result as a new version."""
import io, re, shutil, subprocess, tempfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from .guard import assert_allowed, LockedError
from .checks.pdf import LOCKED, check

RULE_TO_OP = {'EG-PF-16.1': 'pdf_version_normalise', 'EG-PF-16.3': 'remove_security', 'PDF-JS': 'remove_javascript',
              'NTA065-BM': 'add_bookmarks', 'PDF-VIEW': 'show_bookmarks', 'PDF-ZOOM': 'inherit_zoom', 'PDF-INFO': 'doc_info',
              'PDF-REPAIR': 'repair', 'PDF-ATTACH': 'remove_attachments', 'PDF-ANNOT': 'remove_comments', 'PDF-REDACT': 'apply_redaction',
              'PDF-SIZE': 'reduce_size'}
ORDER = ['repair', 'remove_security', 'remove_javascript', 'remove_attachments', 'remove_comments', 'apply_redaction', 'pdf_version_normalise',
         'add_bookmarks', 'show_bookmarks', 'inherit_zoom', 'doc_info', 'reduce_size']
GUARD_OP = {'apply_redaction': 'redact'}             # the guard's name for an operation, where it differs
HEADER = re.compile(rb'%PDF-1\.[0-3]')
HEADING = re.compile(r'^\s*((?:\d{1,2}|[A-Z])(?:\.(?:\d{1,2}|[A-Z])){1,7}\.?|\d{1,2}[.)]|[IVX]{1,4}\.)\s+(\S.{2,90})$')
LABEL = {'remove_security': ('Security restrictions removed', 'تمت إزالة قيود الحماية'),
         'remove_javascript': ('JavaScript removed', 'تمت إزالة JavaScript'),
         'pdf_version_normalise': ('Version line set to PDF 1.7 (nothing else in the file changed)',
                                   'رقم الإصدار في أول سطر بقى 1.7 (ولا حاجة تانية في الملف اتغيّرت)'),
         'add_bookmarks': ('Bookmarks added from the document headings', 'تمت إضافة bookmarks من عناوين المستند'),
         'show_bookmarks': ('Opens with the bookmarks panel', 'بيفتح ولوحة الـ bookmarks ظاهرة'),
         'inherit_zoom': ('Links keep the reader\'s zoom', 'الروابط بتسيب زووم القارئ'),
         'doc_info': ('Title and subject set in the document\'s properties', 'العنوان والموضوع اتكتبوا في خصائص المستند'),
         'repair': ('A clean copy written from the damaged file (PdfCraft)', 'اتكتبت نسخة سليمة من الملف التالف (PdfCraft)'),
         'remove_attachments': ('Attached files removed', 'المرفقات اتشالت'),
         'remove_comments': ('Comments and mark-ups removed', 'التعليقات والعلامات اتشالت'),
         'apply_redaction': ('Redacted for real: the text under the boxes removed for good (PdfCraft checked nothing readable is left)',
                             'إخفاء حقيقي: النص اللي تحت المستطيلات اتشال نهائي (PdfCraft اتأكد إن مفيش حاجة فاضلة بتتقري)'),
         'reduce_size': ('A smaller file: images above 225 ppi brought to 150 ppi', 'الملف بقى أصغر: الصور اللي فوق 225 نقطة/بوصة بقت 150')}
DOC_INFO = {}                                         # the title and subject an apply() call gives the document (set by the caller)


def set_version_17(data):
    """The PDF's version line («%PDF-1.3») changed to «%PDF-1.7» in place: the same length, every other byte of the file identical, so
    nothing on the pages can change (1.7 reads everything 1.0–1.3 wrote). None when there is nothing to change, or when the file is
    digitally signed (the signature covers those bytes too)."""
    data = data or b''
    m = HEADER.search(data[:1024])
    if not m or b'/ByteRange' in data:
        return None
    i = m.start() + 7
    return data[:i] + b'7' + data[i + 1:]


def ops_for(findings):
    ops = {RULE_TO_OP[f['rule']] for f in findings if f.get('action') == 'auto_fix' and f['rule'] in RULE_TO_OP}
    return [o for o in ORDER if o in ops]


def is_signed(path):
    """A signed file is never rewritten. PdfCraft's signature list where it is here; the signature flag and a /ByteRange anywhere in
    the file otherwise — or as well (better refuse a fix than break a signature)."""
    from . import pdfcraft
    q = pdfcraft.query(Path(path).read_bytes(), [('sign_list', {})]) if pdfcraft.available() else None
    if q and int((q.get('sign_list') or {}).get('count') or 0) > 0:
        return True
    try:
        rd = PdfReader(str(path), strict=False)
        if rd.is_encrypted:
            rd.decrypt('')
        af = rd.trailer['/Root'].get('/AcroForm')
        if af and int(af.get_object().get('/SigFlags', 0)) & 1:
            return True
    except Exception:
        pass
    return b'/ByteRange' in Path(path).read_bytes()


def _rewrite(src, dst, op):
    rd = PdfReader(str(src), strict=False)
    if rd.is_encrypted and not rd.decrypt(''):
        raise RuntimeError('password required to open')
    w = PdfWriter(clone_from=rd)
    if op == 'remove_javascript':
        root = w._root_object
        names = root.get('/Names')
        if names is not None and '/JavaScript' in names.get_object():
            del names.get_object()[NameObject('/JavaScript')]
        if '/OpenAction' in root and '/JS' in str(root['/OpenAction']):
            del root[NameObject('/OpenAction')]
        if '/AA' in root:
            del root[NameObject('/AA')]
    if op == 'show_bookmarks':
        w.page_mode = '/UseOutlines'
    if op == 'inherit_zoom':
        from pypdf.generic import NullObject, ArrayObject
        for pg in w.pages:
            for a in (pg.get('/Annots') or []):
                a = a.get_object()
                if a.get('/Subtype') != '/Link':
                    continue
                act = a.get('/A')
                dest = a.get('/Dest') if a.get('/Dest') is not None else (act.get_object().get('/D') if act is not None else None)
                d = dest.get_object() if dest is not None and hasattr(dest, 'get_object') else dest
                if isinstance(d, ArrayObject) and len(d) >= 5 and str(d[1]) == '/XYZ':
                    d[4] = NullObject()
    if op == 'doc_info':
        info = {k: v for k, v in DOC_INFO.items() if v}
        if info:
            w.add_metadata(info)
    w.pdf_header = '%PDF-1.7'
    with open(dst, 'wb') as f:
        w.write(f)


def headings(path):
    """Numbered headings per page (first occurrence), e.g. «3.2.P.5.1 Specification», «2.1 Introduction»."""
    rd = PdfReader(str(path), strict=False)
    if rd.is_encrypted:
        rd.decrypt('')
    out, seen = [], set()
    for i, pg in enumerate(rd.pages):
        try:
            lines = (pg.extract_text() or '').splitlines()
        except Exception:
            continue
        for ln in lines:
            m = HEADING.match(ln)
            if m and ln.strip() not in seen:
                num = m.group(1).rstrip('.)')
                if not re.search(r'\d', num) or re.fullmatch(r'\d{1,2}\.\d{1,2}', num) and re.search(r'\d\.\d+\s*(mg|%|g|ml)', ln, re.I):
                    continue                      # not a heading (e.g. «1.5 mg»)
                seen.add(ln.strip())
                out.append((i, ln.strip()[:120], num.count('.') + 1))
    return out


def _bookmarks(src, dst):
    hs = headings(src)
    if len(hs) < 2:
        raise RuntimeError('no numbered headings detected — add bookmarks in the source document')
    rd = PdfReader(str(src), strict=False)
    if rd.is_encrypted:
        rd.decrypt('')
    w = PdfWriter(clone_from=rd)
    parents = {}
    for page, title, level in hs:
        par = next((parents[l] for l in range(level - 1, 0, -1) if l in parents), None)
        item = w.add_outline_item(title, page, parent=par)
        parents[level] = item
        for l in [k for k in parents if k > level]:
            del parents[l]
    w.page_mode = '/UseOutlines'
    w.pdf_header = '%PDF-1.7'
    with open(dst, 'wb') as f:
        w.write(f)


def _raster(path, outdir, tag):
    gs = shutil.which('gs')
    if not gs:
        raise RuntimeError('ghostscript not available for the pixel check')
    subprocess.run([gs, '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER', '-sDEVICE=pnggray', '-r60',
                    f'-sOutputFile={outdir}/{tag}-%04d.png', str(path)], check=True, capture_output=True, timeout=300)
    return sorted(Path(outdir).glob(f'{tag}-*.png'))


def same_pixels(a, b):
    try:
        from PIL import Image, ImageChops
    except ImportError:                                  # the browser edition has no image library: the fix is refused, never a crash
        raise RuntimeError('no image library on this machine for the pixel check')
    with tempfile.TemporaryDirectory() as d:
        pa, pb = _raster(a, d, 'a'), _raster(b, d, 'b')
        if len(pa) != len(pb):
            return False
        for x, y in zip(pa, pb):
            ia, ib = Image.open(x), Image.open(y)
            if ia.size != ib.size or ImageChops.difference(ia, ib).getbbox() is not None:
                return False
    return True


def _pc_job(src, dst, steps):
    """Open src in PdfCraft, run the steps on it (document 1), and write the result to dst (a full, clean rewrite)."""
    from . import pdfcraft
    _res, out = pdfcraft.run([('doc_open', {'path': 'in.pdf'})] + steps + [('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})],
                             {'in.pdf': Path(src).read_bytes()}, read=('out.pdf',))
    Path(dst).write_bytes(out['out.pdf'])


def _pc_headings(data):
    """The numbered headings PdfCraft reads, each at its place: [(page, title, level, top)] — the lines in reading order with their
    size, so «3.2.P.5.1» is read whole and a heading set smaller than the text around it is not taken for one."""
    from . import pdfcraft
    n = pdfcraft.page_count(data) or 0
    res, _ = pdfcraft.run([('doc_open', {'path': 'in.pdf'})] + [('text_lines', {'doc': 1, 'page': p}) for p in range(1, n + 1)], {'in.pdf': data})
    lines = [(p, ln) for p, r in enumerate(res[1:], 1) for ln in ((pdfcraft.first(r) or {}).get('lines') or [])]
    sizes = sorted(float(ln.get('size') or 0) for _, ln in lines if ln.get('size'))
    body = sizes[len(sizes) // 2] if sizes else 0
    out, seen = [], set()
    for p, ln in lines:
        text = ' '.join(str(ln.get('text') or '').split())
        m = HEADING.match(text)
        if not m or text in seen or (ln.get('size') and float(ln['size']) < body - 0.5):
            continue
        num = m.group(1).rstrip('.)')
        if not re.search(r'\d', num) or re.fullmatch(r'\d{1,2}\.\d{1,2}', num) and re.search(r'\d\.\d+\s*(mg|%|g|ml)', text, re.I):
            continue                                       # not a heading (e.g. «1.5 mg»)
        seen.add(text)
        rect = ln.get('rect') or [0, 0]
        out.append((p, text[:120], num.count('.') + 1, max(0.0, float(rect[1]) - 6)))
    return out


def _pc_bookmarks(src, dst):
    """Bookmarks by PdfCraft: from the document's tagged headings (a Word document saved as a tagged PDF) — the headings at the top
    level, not under PdfCraft's «Untitled» — else from its numbered headings at their place on the page, else from the type styles its
    headings are set in. Then it opens with the bookmarks panel."""
    from . import pdfcraft
    data = Path(src).read_bytes()
    view = [('doc_initial_view', {'doc': 1, 'navigation': 'bookmarks'})]
    try:
        res, _ = pdfcraft.run([('doc_open', {'path': 'in.pdf'}), ('bookmark_from_structure', {'doc': 1}), ('bookmark_list', {'doc': 1, 'limit': 1000})],
                              {'in.pdf': data})
        top = ((pdfcraft.first(res[2]) or {}).get('bookmarks') or [{}])[0]
        kids = len(top.get('children') or [])
        if kids:
            _pc_job(src, dst, [('bookmark_from_structure', {'doc': 1})]
                    + [('bookmark_move', {'doc': 1, 'path': [1, 1]})] * kids + [('bookmark_delete', {'doc': 1, 'path': [1]})] + view)
            return 'structure'
    except pdfcraft.PdfCraftError:
        pass                                               # no tagged headings
    hs = _pc_headings(data)
    if len(hs) >= 2:
        steps, stack, kids = [], [], {(): 0}
        for page, title, level, top in hs:
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1] if stack else ()
            kids[parent] = kids.get(parent, 0) + 1
            path = parent + (kids[parent],)
            steps.append(('bookmark_add', {'doc': 1, 'title': title, 'page': page, 'top': top, **({'parent': list(parent)} if parent else {})}))
            stack.append((level, path))
        _pc_job(src, dst, steps + view)
        return 'numbered headings'
    q = pdfcraft.query(data, [('text_styles', {})]) or {}
    styles = (q.get('text_styles') or {}).get('styles') or []
    if styles:
        body = max(styles, key=lambda x: x.get('lines') or 0)
        heads = [x for x in styles if float(x.get('size') or 0) > float(body.get('size') or 0) + 0.5 and (x.get('lines') or 0) <= max(2, (body.get('lines') or 0) // 3)]
        heads = sorted(heads, key=lambda x: -float(x['size']))[:3]
        if heads and sum(x.get('lines') or 0 for x in heads) >= 2:
            _pc_job(src, dst, [('bookmark_from_text_styles', {'doc': 1, 'levels': [{'font': x['font'], 'size': x['size'], 'bold': bool(x.get('bold'))} for x in heads]})] + view)
            return 'heading styles'
    raise RuntimeError('no headings found (tagged, numbered or set in a heading style) — add bookmarks in the source document')


def _pc_remove_javascript(src, dst):
    from . import pdfcraft
    data = Path(src).read_bytes()
    q = pdfcraft.query(data, [('js_document_scripts', {})]) or {}
    names = [x.get('name') for x in ((q.get('js_document_scripts') or {}).get('scripts') or []) if x.get('name')]
    _pc_job(src, dst, [('js_set_document_script', {'doc': 1, 'name': n}) for n in names])
    left = pdfcraft.query(Path(dst).read_bytes(), [('doc_info', {})]) or {}
    if (left.get('doc_info') or {}).get('has_javascript'):    # an opening action or an annotation's script: removed as before
        tmp = Path(dst).with_suffix('.js.pdf')
        _rewrite(dst, tmp, 'remove_javascript')
        if ((pdfcraft.query(tmp.read_bytes(), [('doc_info', {})]) or {}).get('doc_info') or {}).get('has_javascript'):
            raise RuntimeError('JavaScript is left in the file (in its fields): the document has to be made again without it')
        shutil.move(tmp, dst)


def _pc_remove_security(src, dst):
    """PdfCraft removes the security as Acrobat does, with the permissions password; a file restricted without one (no password
    needed to open it) — the company's own documents only, the guard sees to that — has the restrictions dropped as before."""
    from . import pdfcraft
    try:
        _pc_job(src, dst, [('doc_unprotect', {'doc': 1})])
    except pdfcraft.PdfCraftError:
        _rewrite(src, dst, 'remove_security')


def _pc_op(cur, nxt, op, findings):
    """The operation by PdfCraft; False when PdfCraft has no tool for it (the pypdf way is used)."""
    from . import pdfcraft
    if op == 'repair':
        _pc_job(cur, nxt, [])
    elif op == 'remove_security':
        _pc_remove_security(cur, nxt)
    elif op == 'remove_javascript':
        _pc_remove_javascript(cur, nxt)
    elif op in ('remove_attachments', 'remove_comments'):
        _pc_job(cur, nxt, [('doc_remove_hidden', {'doc': 1, 'categories': ['attachments' if op == 'remove_attachments' else 'comments']})])
    elif op == 'apply_redaction':
        q = pdfcraft.query(Path(cur).read_bytes(), [('doc_audit_redactions', {})]) or {}
        marks = [f for f in ((q.get('doc_audit_redactions') or {}).get('findings') or []) if f.get('rect') and f.get('page')]
        if not marks:
            raise RuntimeError('no faux redaction found to redact')
        _pc_job(cur, nxt, [('redact_mark', {'doc': 1, 'page': int(f['page']), 'rect': [float(v) for v in f['rect']]}) for f in marks]
                + [('redact_apply', {'doc': 1})])
    elif op == 'add_bookmarks':
        _pc_bookmarks(cur, nxt)
    elif op == 'show_bookmarks':
        _pc_job(cur, nxt, [('doc_initial_view', {'doc': 1, 'navigation': 'bookmarks'})])
    elif op == 'doc_info':
        info = {k: v for k, v in DOC_INFO.items() if v}
        _pc_job(cur, nxt, [('doc_set_info', {'doc': 1, 'key': k.lstrip('/'), 'value': str(v)}) for k, v in info.items()])
    elif op == 'reduce_size':
        small, rep = pdfcraft.reduce(Path(cur).read_bytes())
        if not small or len(small) >= Path(cur).stat().st_size:
            raise RuntimeError('the file cannot be made smaller (its images are already at 150 ppi or below)')
        Path(nxt).write_bytes(small)
    else:
        return False                                       # inherit_zoom: PdfCraft's link tool would drop the place the link goes to
    return True


PDFCRAFT_ONLY = {'repair', 'remove_attachments', 'remove_comments', 'apply_redaction', 'reduce_size'}


def apply(path, findings, doc_class):
    """Returns {'data': bytes|None, 'done': [...], 'refused': [...], 'report': check Report of the result}."""
    from . import pdfcraft
    ops = ops_for(findings)
    done, refused = [], []
    if not ops:
        return {'data': None, 'done': [], 'refused': [], 'report': None}
    if is_signed(path):
        return {'data': None, 'done': [], 'report': None, 'refused': [{'op': o, 'en': 'Digitally signed PDF: rewriting it would break the signature. Ask the signer for a conforming copy.',
                                                                      'ar': 'ملف موقّع رقمياً: أي تعديل هيبطل التوقيع. اطلب نسخة مطابقة من الموقّع.'} for o in ops]}
    with tempfile.TemporaryDirectory() as d:
        cur = Path(d) / 'v0.pdf'
        shutil.copyfile(path, cur)
        for i, op in enumerate(ops, 1):
            try:
                assert_allowed(doc_class, GUARD_OP.get(op, op))
            except LockedError:
                refused.append({'op': op, 'en': 'Only the issuer may change this on a third-party/EDA document — re-obtain it.',
                                'ar': 'التعديل ده على مستند جهة خارجية/الهيئة من حق الجهة المصدرة بس — اطلبه منها.'})
                continue
            nxt = Path(d) / f'v{i}.pdf'
            if op == 'pdf_version_normalise':              # the version line only: every other byte stays, so no pixel check is needed
                v17 = set_version_17(cur.read_bytes())
                if v17 is None and re.match(rb'%PDF-(1\.[4-7]|2\.0)', cur.read_bytes()[:16]) and cur.name != 'v0.pdf':
                    done.append({'op': op, 'en': 'PDF version 1.4 or later (the file was written again by an earlier fix)',
                                 'ar': 'إصدار PDF بقى 1.4 أو أحدث (الملف اتكتب من جديد في تصليح قبله)'})
                    continue
                if v17 is None:
                    refused.append({'op': op, 'en': 'The version line could not be changed.', 'ar': 'رقم الإصدار ما ينفعش يتغيّر.'})
                    continue
                nxt.write_bytes(v17)
                cur = nxt
                done.append({'op': op, 'en': LABEL[op][0], 'ar': LABEL[op][1]})
                continue
            try:
                if not (pdfcraft.available() and _pc_op(cur, nxt, op, findings)):
                    if op in PDFCRAFT_ONLY:
                        raise RuntimeError('this needs PdfCraft, which is not on this machine')
                    {'add_bookmarks': lambda: _bookmarks(cur, nxt)}.get(op, lambda: _rewrite(cur, nxt, op))()
            except Exception as e:
                refused.append({'op': op, 'en': f'Could not apply: {type(e).__name__}: {e}'[:300], 'ar': 'تعذّر التطبيق.'})
                continue
            if doc_class in LOCKED:
                try:
                    identical = pdfcraft.same_pixels(cur.read_bytes(), nxt.read_bytes()) if pdfcraft.available() else None
                    if identical is None:
                        identical = same_pixels(cur, nxt)
                except RuntimeError as e:                 # no ghostscript here (browser edition): never touch evidence unverified
                    refused.append({'op': op, 'en': f'Cannot verify the page images on this machine ({e}); the original is kept.',
                                    'ar': 'مش ممكن نتأكد إن شكل الصفحات ما اتغيّرش على الجهاز ده؛ الأصل محفوظ.'})
                    continue
                if not identical:
                    refused.append({'op': op, 'en': 'The result would not be pixel-identical to the original; discarded.',
                                    'ar': 'النتيجة كانت هتغيّر شكل الصفحة؛ اتلغت.'})
                    continue
            cur = nxt
            done.append({'op': op, 'en': LABEL[op][0], 'ar': LABEL[op][1]})
        if not done:
            return {'data': None, 'done': [], 'refused': refused, 'report': None}
        rep = check(str(cur), doc_class)
        return {'data': cur.read_bytes(), 'done': done, 'refused': refused, 'report': rep}
