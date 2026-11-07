"""Automatic technical fixes (02-LOGIC §6 «allowed technical ops»).

Each finding whose action is auto_fix maps to an operation. Every operation is
checked by the guard for the document's class, and for read-only evidence
(third-party, EDA, executed, signed scans) the result must be page-for-page
pixel-identical to the original — otherwise the fix is discarded and the user is
told to re-obtain the document. Digitally signed PDFs are never rewritten
(it would break the signature). The original is never modified: the caller
stores the result as a new version."""
import io, shutil, subprocess, tempfile
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from .guard import assert_allowed, LockedError
from .checks.pdf import LOCKED, check

RULE_TO_OP = {'EG-PF-16.1': 'pdf_version_normalise', 'EG-BP-16.BP1': 'pdf_version_normalise',
              'EG-PF-16.3': 'remove_security', 'PDF-JS': 'remove_javascript',
              'NTA065-N4': 'add_ocr_layer', 'EG-BP-E23': 'add_ocr_layer'}
ORDER = ['remove_security', 'remove_javascript', 'pdf_version_normalise', 'add_ocr_layer']
LABEL = {'remove_security': ('Security restrictions removed', 'تمت إزالة قيود الحماية'),
         'remove_javascript': ('JavaScript removed', 'تمت إزالة JavaScript'),
         'pdf_version_normalise': ('Saved as PDF 1.7', 'تم الحفظ كـ PDF 1.7'),
         'add_ocr_layer': ('Searchable text layer added (OCR, Arabic + English); page images unchanged',
                           'تمت إضافة طبقة نص قابلة للبحث (OCR عربي + إنجليزي)؛ صور الصفحات كما هي')}


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
    w.pdf_header = '%PDF-1.7'
    with open(dst, 'wb') as f:
        w.write(f)


def _ocr(src, dst):
    import ocrmypdf
    ocrmypdf.ocr(str(src), str(dst), language=['ara', 'eng'], skip_text=True, optimize=0, output_type='pdf',
                 progress_bar=False)


def _raster(path, outdir, tag):
    gs = shutil.which('gs')
    if not gs:
        raise RuntimeError('ghostscript not available for the pixel check')
    subprocess.run([gs, '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER', '-sDEVICE=pnggray', '-r60',
                    f'-sOutputFile={outdir}/{tag}-%04d.png', str(path)], check=True, capture_output=True, timeout=300)
    return sorted(Path(outdir).glob(f'{tag}-*.png'))


def same_pixels(a, b):
    from PIL import Image, ImageChops
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
            try:
                _ocr(cur, nxt) if op == 'add_ocr_layer' else _rewrite(cur, nxt, op)
            except Exception as e:
                refused.append({'op': op, 'en': f'Could not apply: {type(e).__name__}: {e}'[:300], 'ar': 'تعذّر التطبيق.'})
                continue
            if doc_class in LOCKED and not same_pixels(cur, nxt):
                refused.append({'op': op, 'en': 'The result would not be pixel-identical to the original; discarded.',
                                'ar': 'النتيجة كانت هتغيّر شكل الصفحة؛ اتلغت.'})
                continue
            cur = nxt
            done.append({'op': op, 'en': LABEL[op][0], 'ar': LABEL[op][1]})
        if not done:
            return {'data': None, 'done': [], 'refused': refused, 'report': None}
        rep = check(str(cur), doc_class)
        return {'data': cur.read_bytes(), 'done': done, 'refused': refused, 'report': rep}
