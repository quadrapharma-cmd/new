"""Automatic technical fixes (02-LOGIC §6 «allowed technical ops»). No OCR: a PDF without text is refused at upload and its
text layer is made when scanning.

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
              'NTA065-BM': 'add_bookmarks', 'PDF-VIEW': 'show_bookmarks', 'PDF-ZOOM': 'inherit_zoom', 'PDF-INFO': 'doc_info'}
ORDER = ['remove_security', 'remove_javascript', 'pdf_version_normalise', 'add_bookmarks', 'show_bookmarks', 'inherit_zoom', 'doc_info']
HEADER = re.compile(rb'%PDF-1\.[0-3]')
HEADING = re.compile(r'^\s*((?:\d{1,2}|[A-Z])(?:\.(?:\d{1,2}|[A-Z])){1,7}\.?|\d{1,2}[.)]|[IVX]{1,4}\.)\s+(\S.{2,90})$')
LABEL = {'remove_security': ('Security restrictions removed', 'تمت إزالة قيود الحماية'),
         'remove_javascript': ('JavaScript removed', 'تمت إزالة JavaScript'),
         'pdf_version_normalise': ('Version line set to PDF 1.7 (nothing else in the file changed)',
                                   'رقم الإصدار في أول سطر بقى 1.7 (ولا حاجة تانية في الملف اتغيّرت)'),
         'add_bookmarks': ('Bookmarks added from the document headings', 'تمت إضافة bookmarks من عناوين المستند'),
         'show_bookmarks': ('Opens with the bookmarks panel', 'بيفتح ولوحة الـ bookmarks ظاهرة'),
         'inherit_zoom': ('Links keep the reader\'s zoom', 'الروابط بتسيب زووم القارئ'),
         'doc_info': ('Title and subject set in the document\'s properties', 'العنوان والموضوع اتكتبوا في خصائص المستند')}
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


def apply(path, findings, doc_class):
    """Returns {'data': bytes|None, 'done': [...], 'refused': [...], 'report': check Report of the result}."""
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
                assert_allowed(doc_class, op)
            except LockedError:
                refused.append({'op': op, 'en': 'Only the issuer may change this on a third-party/EDA document — re-obtain it.',
                                'ar': 'التعديل ده على مستند جهة خارجية/الهيئة من حق الجهة المصدرة بس — اطلبه منها.'})
                continue
            nxt = Path(d) / f'v{i}.pdf'
            if op == 'pdf_version_normalise':              # the version line only: every other byte stays, so no pixel check is needed
                v17 = set_version_17(cur.read_bytes())
                if v17 is None:
                    refused.append({'op': op, 'en': 'The version line could not be changed.', 'ar': 'رقم الإصدار ما ينفعش يتغيّر.'})
                    continue
                nxt.write_bytes(v17)
                cur = nxt
                done.append({'op': op, 'en': LABEL[op][0], 'ar': LABEL[op][1]})
                continue
            try:
                {'add_bookmarks': lambda: _bookmarks(cur, nxt)}.get(op, lambda: _rewrite(cur, nxt, op))()
            except Exception as e:
                refused.append({'op': op, 'en': f'Could not apply: {type(e).__name__}: {e}'[:300], 'ar': 'تعذّر التطبيق.'})
                continue
            if doc_class in LOCKED:
                try:
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
