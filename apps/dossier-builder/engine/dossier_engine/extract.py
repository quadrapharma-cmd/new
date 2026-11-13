"""«Upload the documents and the forms fill themselves» (intake).

Two layers over the same text. This module's RULES read the PDF text (pypdf) with regular expressions: document
kind, certificate numbers, issuers, dates, the product's names and strength, active substances, manufacturers,
batch numbers, CEP numbers… They work everywhere, with no network. The AI layer (Claude: the `sample`
capability in the browser edition, or the API with a key) reads the same text — or the page images when the
document is a scan — against SCHEMA and returns the same shape. Every value is shown for review before it is
used; nothing is written without the user's confirmation."""
import json
import re
from io import BytesIO
from pathlib import Path
from . import arabic, imagefiles, intake_eda, msdoc, officefiles

KINDS = [  # (kind, keywords in lower-case text or file name); see guess_kind for how a match is chosen
    ('cadc', ['notification letter', 'statement of conformity', 'sample identification code', 'qf:cadc', 'شهادة مطابقة']),
    ('cpp', ['certificate of pharmaceutical product', 'who certification scheme', ' cpp']),
    ('cep', ['certificate of suitability', 'r1-cep', 'r0-cep', 'edqm']),
    ('gmp', ['good manufacturing practice', 'gmp certificate', 'certificate of gmp', 'gmp compliance', 'gmp', 'التصنيع الجيد']),
    ('coa', ['certificate of analysis', 'analytical report', ' coa', 'c of a', 'شهادة تحليل', 'شهادة التحليل']),
    ('composition', ['composition certificate', 'unit formula', 'quantitative composition', 'شهادة التركيب', 'التركيب']),
    ('import', ['import approval', 'annual import approval', 'importation approval', 'import permit', 'customs release', 'موافقة استيرادية',
                'الموافقة الاستيرادية', 'موافقة استيراد', 'إذن استيراد', 'الإفراج الجمركي']),
    ('pricing', ['pricing certificate', 'price certificate', 'pricing policies', 'pricing', 'تسعير', 'التسعيرة', 'سعر البيع للجمهور', 'لجنة تسعير', 'سعر بيع الجمهور']),
    ('variation', ['variation approval', 'type of variation', 'variation decision', 'variation committee', 'variations unit', 'pack addition',
                   'الموافقة المبدئية على تغيير', 'الموافقة النهائية على تغيير', 'موافقة تغيير', 'موافقة المتغيرات', 'لجنة المتغيرات', 'إدارة المتغيرات',
                   'إضافة عبوة']),
    ('licence', ['registration licence', 'registration license', 'marketing authorisation', 'marketing authorization', 'registration notification', 'final registration license', 'final registration licence', 'إخطار التسجيل', 'إخطار تسجيل', 'رخصة التسجيل', 'شهادة تسجيل',
                 'شهادة التسجيل', 'ترخيص تداول', 'ترخيص التداول', 'رخصة تداول', 'إخطار', 'اخطار', 'ترخيص']),
    ('annex1', ['annex i', 'application form', 'نموذج الطلب']),
    ('smpc', ['summary of product characteristics', 'name of the medicinal product', 'therapeutic indications', 'posology and method of administration', 'smpc',
              'package leaflet', 'patient information leaflet', 'النشرة']),
    ('factory', ['factory licence', 'factory license', 'manufacturing licence', 'manufacturing license', 'رخصة المصنع']),
    ('bmr', ['batch manufacturing record', 'executed batch', 'batch record']),
    ('validation', ['analytical method validation', 'method validation', 'validation protocol', 'validation report', 'validation of analytical', 'stability indicating assay',
                    'forced degradation', 'chromatogram', 'acq. operator', 'acq. method', 'injection volume', 'inj volume', 'processing method', 'report method', 'peak table',
                    'system suitability']),
    ('method', ['method of analysis', 'methods of analysis', 'analytical procedure', 'analytical method', 'test method', 'testing method', 'in-house monograph', 'monograph',
                'طريقة التحليل', 'طرق التحليل']),
    ('stability', ['stability', 'الثبات', 'للثبات', 'دراسة ثبات', 'دراسات ثبات', 'موافقة ثبات', 'بيانات ثبات']),
    ('spec', ['specification', 'acceptance criteria']),
    ('loa', ['letter of access', 'drug master file', ' dmf']),
    ('poa', ['power of attorney', 'letter of attorney', 'توكيل']),
    ('commercial', ['commercial register', 'register of trade', 'سجل تجاري']),
    ('receipt', ['payment receipt', 'fees receipt', 'قسيمة', 'إيصال', 'ايصال']),
    ('refstd', ['working standard', 'reference standard', 'secondary standard', 'primary standard', 'مادة مرجعية', 'المواد المرجعية', 'مواد مرجعية']),
    ('sampling', ['sampling form', 'sample sending form', 'sample-sending form', 'استمارة سحب', 'سحب عينة', 'سحب عينات', 'استمارة إرسال عينة']),
    ('contract', ['manufacturing agreement', 'toll manufacturing', 'first party', 'second party', 'تم الاتفاق بين', 'الطرف الأول', 'الطرف الاول', 'الطرف الثاني', 'ملحق عقد',
                  'agreement', 'contract', 'اتفاقية', 'عقد']),
]
MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}
DATE = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})|(\d{1,2})[./\-\s]+([A-Za-z]{3,9}|\d{1,2})[./\-\s,]+(\d{4})')
FORMS = ['film-coated tablet', 'film coated tablet', 'coated tablet', 'effervescent tablet', 'chewable tablet', 'orodispersible tablet',
         'prolonged-release tablet', 'extended release tablet', 'tablet', 'hard capsule', 'soft capsule', 'capsule', 'oral suspension',
         'suspension', 'oral solution', 'syrup', 'solution for injection', 'powder for injection', 'injection', 'infusion', 'cream',
         'ointment', 'gel', 'eye drops', 'ear drops', 'nasal spray', 'inhaler', 'inhalation', 'suppository', 'sachet', 'granules',
         'powder for oral suspension', 'topical powder', 'dusting powder', 'powder', 'lotion', 'drops', 'spray', 'emulsion', 'solution', 'foam', 'shampoo', 'patch']
ROUTE = {'oral': ['tablet', 'capsule', 'syrup', 'suspension', 'oral', 'sachet', 'granules', 'drops'], 'parenteral': ['injection', 'infusion'],
         'topical': ['cream', 'ointment', 'gel', 'lotion', 'topical', 'dusting', 'shampoo', 'patch', 'foam'], 'ophthalmic': ['eye'], 'inhalation': ['inhal', 'nasal']}
ISSUERS = ['Egyptian Drug Authority', 'EDA', 'EDQM', 'Ministry of Health', 'Ministry of Health and Population', 'MHRA', 'FDA', 'WHO',
           'Central Drugs Standard Control Organization', 'CDSCO', 'ANVISA', 'Saudi Food and Drug Authority', 'SFDA', 'TGA', 'Swissmedic',
           'BfArM', 'AIFA', 'AEMPS', 'ANSM', 'Health Canada', 'HPRA', 'MFDS', 'PMDA', 'Jordan Food and Drug Administration', 'JFDA',
           'General Authority for Investment', 'Commercial Registry', 'Chamber of Commerce', 'هيئة الدواء المصرية', 'وزارة الصحة']
TESTS = ['assay', 'dissolution', 'uniformity of dosage units', 'content uniformity', 'related substances', 'impurities', 'water content',
         'loss on drying', 'hardness', 'friability', 'disintegration', 'identification', 'description', 'appearance', 'ph', 'microbial',
         'residual solvents', 'particle size', 'sterility', 'bacterial endotoxins', 'average weight', 'uniformity of mass', 'viscosity']

SCHEMA = {
    'product': {'name': 'trade name as registered (Latin)', 'name_ar': 'trade name in Arabic as printed', 'dosage_form': 'pharmaceutical form', 'strength': 'strength per unit, e.g. 500 mg',
                'manufacturer': 'finished-product manufacturer (legal name)', 'manufacturer_address': 'site address as on the GMP certificate',
                'indication': 'main indication, few words'},
    'profile': {'dossier_kind': 'generic | innovator', 'origin': 'local | imported', 'licence': 'own | toll | f_toll | under_licence | imported | imported_bulk',
                'activity': 'new | re_registration', 'admin_route': 'oral | topical | parenteral | ophthalmic | inhalation | other',
                'leaflet': 'english | non_english', 'dosage_specifics': '[coated, capsule_hard, pellets, premix, powder_inj_with_solvent, sterile]',
                'pharmacopoeial': 'true if the product is a pharmacopoeial (BP/USP/Ph. Eur.) product'},
    'apis': [{'name': 'INN of the active substance (one entry per active substance; salt as printed)', 'strength': 'amount per unit as printed, e.g. 3.5 mg (3300 unit)',
              'manufacturer': 'the API manufacturer printed for THIS substance (e.g. under «Manufacturer Of active substance», the line after the substance name)',
              'country': 'country of that manufacturer', 'alternatives': ['other approved suppliers named for this substance, if any'], 'address_gmp': 'API site address',
              'option': 'CEP | DMF | PQ | FULL', 'cep_no': 'e.g. R1-CEP 2010-123-Rev 02', 'cep_status': 'valid | suspended | withdrawn | expired',
              'spec_standard': 'Ph. Eur. | USP | BP | in-house', 'coa_name': 'name on the supplier CoA'}],
    'envelope': {'applicant': 'applicant / MA holder legal name', 'tracking': 'EDA procedure tracking number', 'inn': ['INN list']},
    'batches': [{'no': 'batch number', 'kind': 'fpp | api', 'api': 'API name for API batches', 'size': 'batch size with unit',
                 'scale': 'pilot | production | smaller', 'date': 'YYYY-MM-DD', 'expiry': 'YYYY-MM-DD', 'site': 'manufacturing site', 'conformity': 'Conform | Non-conform (CADC letter)'}],
    'specs': [{'test': 'test name', 'limit': 'acceptance criterion', 'method': 'method / reference'}],
    'results': [{'batch': 'batch number', 'test': 'test name', 'value': 'numeric result as printed (not «complies»)'}],
    'registration': {'reg_no': 'registration / licence number', 'reg_date': 'YYYY-MM-DD', 'valid_until': 'YYYY-MM-DD (invalidation date)', 'shelf_life': 'e.g. 36 months',
                     'storage': 'storage condition', 'price': 'public price', 'prices': [{'price': 'e.g. 34 EGP', 'pack': 'pack it applies to'}], 'packs': ['pack sizes'],
                     'licence_type': 'toll | own | under_licence', 'marketing': 'local | export'},
    'composition': [{'name': 'ingredient as printed', 'amount': 'per unit, e.g. 3.5 mg', 'standard': 'BP 2018 | USP | Ph. Eur. | in-house', 'role': 'active | excipient',
                     'equivalent': 'e.g. equivalent to 3300 units/g'}],
    'documents': [{'filename': 'as given', 'kind': 'cpp | gmp | cep | coa | cadc | composition | licence | pricing | annex1 | smpc | factory | bmr | stability | spec | loa | poa | commercial | contract | other',
                   'title': 'document title', 'number': 'certificate / licence number', 'issuer': 'issuing authority or company',
                   'issued': 'YYYY-MM-DD', 'valid_until': 'YYYY-MM-DD or null', 'product_name': 'the product name as printed in it, if any',
                   'language': 'ar | en | ar+en | the other language it is written in',
                   'letterhead': 'true / false: on the issuing company\'s letterhead (only when you can see the page)',
                   'signed': 'true / false: a handwritten or electronic signature is on it (only when you can see the page)',
                   'stamped': 'true / false: an official stamp or seal is on it (only when you can see the page)',
                   'legalized': 'true / false: an embassy or consulate legalisation stamp, or an apostille, is on it (only when you can see the page)',
                   'production_lines': 'the production lines it names, if any', 'batch': 'batch number, for a CoA',
                   'manufactured': 'YYYY-MM-DD, for a CoA', 'expiry': 'YYYY-MM-DD expiry or retest date, for a CoA',
                   'one_document': 'false when the file holds several separate documents'}],
}
PRIORITY = ['licence', 'annex1', 'variation', 'cpp', 'smpc', 'composition', 'pricing', 'cadc', 'spec', 'coa', 'stability', 'method', 'validation', 'cep', 'gmp',
            'bmr', 'factory', 'loa', 'contract', 'poa', 'commercial', 'receipt', 'other']
IDENTITY = ('licence', 'annex1', 'variation', 'cpp', 'smpc', 'composition', 'pricing', 'cadc', 'contract')     # documents that state what the product is
ABOUT_PRODUCT = ('spec', 'coa', 'stability', 'method', 'validation', 'bmr')                                     # technical documents: they name the product at their top


def pdf_text(data, max_pages=12):
    """Text of the first pages; `scanned` when no page has text (an image-only PDF). Read by PdfCraft (the lines in reading order,
    Arabic in its order); by pypdf where PdfCraft is not (the browser edition)."""
    from . import pdfcraft
    got = pdfcraft.pdf_pages(data, max_pages)
    if got is not None:
        n, pages = got
        text = '\n'.join(pages)
        return {'pages': n, 'text': text, 'scanned': n > 0 and len(re.sub(r'\s', '', text)) < 20, 'reader': 'pdfcraft'}
    from pypdf import PdfReader
    pages = []
    try:
        rd = PdfReader(BytesIO(data), strict=False)
        for p in rd.pages[:max_pages]:
            try:
                pages.append(p.extract_text() or '')
            except Exception:
                pages.append('')
        n = len(rd.pages)
    except Exception:
        n = 0
    text = '\n'.join(pages)
    return {'pages': n, 'text': text, 'scanned': n > 0 and len(re.sub(r'\s', '', text)) < 20, 'reader': 'pypdf'}


def docx_text(data):
    try:
        import docx
        d = docx.Document(BytesIO(data))
        text = '\n'.join(p.text for p in d.paragraphs)
        for t in d.tables:
            for row in t.rows:
                cells = []
                for c in row.cells:
                    v = re.sub(r'\s*\n+\s*', ' ', c.text).strip()
                    if not cells or v != cells[-1]:                 # a merged cell is handed over once per column it spans
                        cells.append(v)
                text += '\n' + ' | '.join(cells)
        return text
    except Exception:
        return _docx_xml_text(data)


def _docx_xml_text(data):
    """A Word file python-docx will not open (a template, a macro-enabled document): the paragraphs of its document part."""
    try:
        import zipfile
        from lxml import etree
        w = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        root = etree.fromstring(zipfile.ZipFile(BytesIO(data)).read('word/document.xml'))
        return '\n'.join(''.join(t.text or '' for t in p.iter(w + 't')) for p in root.iter(w + 'p'))
    except Exception:
        return ''


def word_kind(data):
    """'docx' | 'doc' | None — a Word file by what is inside it, whatever its name says: a zip with a Word document part, or the
    Word 97-2003 container."""
    k = officefiles.sniff('', data or b'')
    return k if k in ('docx', 'doc') else None


def source_family(filename, data):
    """'word' | 'excel' | 'powerpoint' | 'text' | None — an editable source file (old or new format) rather than the PDF the dossier takes."""
    return officefiles.FAMILY.get(officefiles.sniff(filename, data or b''))


def is_word(filename, data=None):
    """Is this file a Word document? By its bytes when they are at hand, by its name otherwise."""
    if data is not None:
        return bool(word_kind(data))
    return (filename or '').lower().endswith(('.docx', '.doc', '.docm', '.dotx', '.dot'))


# ---- a file is read once: its reading is kept by the file's SHA-256, in memory and in the workspace's cache folder
READ_DIR = None            # set by the app (workspace/cache/text): a restart, or the next item's template, does not read the file again
READ_FORMAT = 6            # the reader's own version: raise it when what a reading holds changes, so that readings kept on disk by an older reader are made again (3: no OCR; 4: PdfCraft reads the PDFs; 5: PdfCraft reads scans too; 6: the reading of a scan checks itself — accurate models, a second reader for the words Tesseract is unsure of — and says how sure it is)
_READ = {}                 # (sha, extension, max_pages) → the reading
_READ_MAX = 300


def _sha(data):
    import hashlib
    return hashlib.sha256(data or b'').hexdigest()


def _cache_file(key):
    return None if READ_DIR is None else Path(READ_DIR) / (f'r{READ_FORMAT}-' + '-'.join(str(k) for k in key) + '.json')


def read_text(name, data, max_pages=12):
    """What one uploaded file says — read once: the same bytes asked the same way give the kept reading (see _read_text)."""
    data = data or b''
    from . import pdfcraft
    sha, tag = _sha(data), _ocr_tag()
    if tag == 'no-ocr' and browser_reading(sha):                  # read in the page (the browser edition): a reading of its own
        tag = 'browser-' + str(browser_reading(sha).get('tag') or 'ocr')
    key = (sha, (name or '').lower().rsplit('.', 1)[-1][:6] if '.' in (name or '') else '', max_pages, pdfcraft.reader(), tag)
    if key in _READ:
        return dict(_READ[key])
    f = _cache_file(key)
    if f is not None:
        try:
            if f.exists():
                _READ[key] = json.loads(f.read_text(encoding='utf-8'))
                return dict(_READ[key])
        except (OSError, ValueError):
            pass
    out = _read_text(name, data, max_pages)
    if len(_READ) >= _READ_MAX:
        _READ.pop(next(iter(_READ)))
    _READ[key] = dict(out)
    if f is not None and len(data) > 200000:                          # a large file's reading is kept on disk too
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
        except OSError:
            pass
    return dict(out)


def page_count(name, data):
    """A file's pages, as the reader counts them (a PDF's pages, a TIFF's, 1 for another image or a Word file)."""
    return int(read_text(name, data).get('pages') or 0)


def has_text(name, data):
    """The upload gate's question — NP.CAPP.065 v5 general note 4: «All submitted documents should be scanned and searchable PDF
    files». None when the file has text of its own (a PDF with a text layer, Word, Excel…); else why not: 'image' (a photo or an
    image file) or 'scan' (a PDF whose pages are images only). Such a file is kept, not refused: PdfCraft reads it (OCR, Arabic and
    English) and the «make searchable» fix adds its text layer; where PdfCraft is not (the browser edition) the item says what to do."""
    r = read_text(name, data)
    if r['kind_of_file'] == 'image':
        return 'image'
    if r['kind_of_file'] == 'pdf' and r['scanned']:
        return 'scan'
    return None


def _read_text(name, data, max_pages=12):
    """What one uploaded file says: a PDF's text layer, or an office file's text (Word, Excel, PowerPoint, OpenDocument, RTF, HTML,
    text: old formats and new — officefiles). No OCR anywhere: a PDF whose pages are images only, or an image, gives no text and is
    marked `scanned`. `kind_of_file` = pdf | docx | image | xlsx | xls | pptx | … | other."""
    low = (name or '').lower()
    out = {'pages': 0, 'text': '', 'scanned': False, 'kind_of_file': 'other'}
    data = data or b''
    what = officefiles.sniff(name, data)                 # what the file is, by its bytes
    img = arabic.image_type(data)
    if data[:4] == b'%PDF' or what == 'pdf' or (low.endswith('.pdf') and what in ('other', 'text')):
        out.update(pdf_text(data, max_pages), kind_of_file='pdf')
        if out.get('scanned'):                           # pages that are images: PdfCraft reads them (OCR, Arabic and English) where it can,
            _ocr_into(out, data, max_pages)              # the page itself in the browser edition (_browser_into)
            if not out.get('ocr'):
                _browser_into(out, data, max_pages)
    elif img or what == 'image':                         # an image of any kind (imagefiles): no text of its own
        fmt = imagefiles.image_format(data)
        out.update(pages=imagefiles.tiff_pages(data) if fmt == 'tiff' else 1, scanned=True, kind_of_file='image')
        from . import pdfcraft
        page = pdfcraft.image_to_pdf(data, name or 'image.png') if pdfcraft.ocr_info() else None
        if page:
            _ocr_into(out, page, max_pages)
        if not out.get('ocr'):
            _browser_into(out, data, max_pages)
    elif what in ('docx', 'doc'):                        # Word, new or old: its paragraphs and tables
        out.update(pages=1, text=docx_text(data) if what == 'docx' else msdoc.doc_text(data), kind_of_file='docx')
    elif what in officefiles.OFFICE:                     # Excel, PowerPoint, OpenDocument, RTF, HTML, plain text — old formats and new
        out.update(pages=1, text=officefiles.text(what, data, name), kind_of_file=what)
    out['text'] = arabic.prepare(out['text'])
    out['arabic'] = arabic.has_arabic(out['text'])
    return out


def _ocr_tag():
    """Which recognition reads scans here — its languages, the accurate models, the second reader — so that a reading kept by
    another one is made again: 'ar+en+best+paddle', or 'no-ocr'."""
    from . import paddle_rec, pdfcraft
    info = pdfcraft.ocr_info()
    if not info:
        return 'no-ocr'
    return info['language'] + ('+best' if info.get('models') == 'best 4.1.0' else '') + ('+paddle' if paddle_rec.available() else '')


def ocr_summary(rep):
    """How sure a recognition is, for the people who check it: the pages still hard to read, the words the second reader put
    right (was → now), and the numbers still read with low confidence (page, text)."""
    q = (rep or {}).get('quality') or {}
    return {'weak': list((rep or {}).get('weak') or []), 'corrected': (rep or {}).get('second_reader') or 0,
            'changed': [{'page': p, **c} for p, v in sorted(q.items()) for c in (v.get('second') or {}).get('changed') or []][:30],
            'doubtful': [{'page': p, 'text': t} for p, v in sorted(q.items()) for t in v.get('numbers') or []][:30],
            'straightened': [p for p, v in sorted(q.items()) if v.get('read') == 'straightened']}


def _ocr_into(out, pdf, max_pages):
    """The text PdfCraft's recognition reads from a PDF whose pages are images (Tesseract: Arabic and English, checked by the
    second reader): the reading of a scan for its information, and how sure it is (ocr_quality). The file itself is not changed
    here — making it searchable is a fix (fixes «make_searchable»)."""
    from . import pdfcraft
    info = pdfcraft.ocr_info()
    if not info:
        return
    key = (_sha(pdf), max_pages, _ocr_tag())               # one recognition per file, whatever name it comes under
    if key not in _OCR_READ:
        try:
            got = pdfcraft.ocr(pdf, pages=list(range(1, max_pages + 1)) if max_pages else None)
        except pdfcraft.PdfCraftError:
            got = None
        if len(_OCR_READ) >= 64:
            _OCR_READ.pop(next(iter(_OCR_READ)))
        _OCR_READ[key] = (got[1], ocr_summary(got[2])) if got else None
    texts, quality = _OCR_READ[key] or (None, None)
    if texts and any(t.strip() for t in texts):
        out.update(text='\n'.join(texts), ocr=True, reader='pdfcraft-ocr', ocr_language=info['language'], ocr_quality=quality)


_OCR_READ = {}


# ---- scans read in the page (the browser edition, ui/assets/ocr.js): the same reading as pdfcraft.ocr — Tesseract with the accurate
# models, the second reader (PaddleOCR) for the words it is unsure of, pages turned upright — done by the browser, where this engine
# (Pyodide) has no PdfCraft. The page sends what it read with the file's SHA-256; the reading is kept beside the other readings
# (READ_DIR/browser/<sha>.json) and read_text takes it as it takes PdfCraft's.
BROWSER = {}
BROWSER_MAX_PAGES, BROWSER_MAX_CHARS = 200, 400000


def _browser_file(sha):
    return None if READ_DIR is None else Path(READ_DIR) / 'browser' / f'{sha}.json'


def browser_reading(sha):
    """The page's reading of the file with this SHA-256 ({'texts', 'rep', 'tag'}), or None."""
    if not re.fullmatch(r'[0-9a-f]{64}', sha or ''):
        return None
    key = (str(READ_DIR), sha)
    if key not in BROWSER:
        f = _browser_file(sha)
        try:
            BROWSER[key] = json.loads(f.read_text(encoding='utf-8')) if f is not None and f.exists() else None
        except (OSError, ValueError):
            BROWSER[key] = None
        if len(BROWSER) > 512:
            BROWSER.pop(next(iter(BROWSER)))
    return BROWSER[key]


def _layout(layout, pages):
    """The words' places the page read (ui/assets/ocr.js), checked: per page {'words': [[text, x, y, w, h, line], …] in points, in
    reading order; 'rotated': 0/90/180/270; 'deskew': radians}. None when not given."""
    import math
    if layout is None:
        return None
    if not isinstance(layout, list) or len(layout) != pages:
        raise ValueError('layout: one entry per page read')
    out = []
    for pg in layout:
        if not isinstance(pg, dict) or not isinstance(pg.get('words') or [], list) or len(pg.get('words') or []) > 6000:
            raise ValueError('layout: a page is {words, rotated, deskew}, at most 6000 words')
        words = []
        for wd in pg.get('words') or []:
            if not isinstance(wd, list) or len(wd) < 5 or not isinstance(wd[0], str) or len(wd[0]) > 200:
                raise ValueError('layout: a word is [text, x, y, w, h, line]')
            nums = [float(v) for v in wd[1:5]]
            if not all(math.isfinite(v) and abs(v) < 1e6 for v in nums):
                raise ValueError('layout: a word\'s place is four numbers')
            words.append([wd[0], *nums, int(wd[5]) if len(wd) > 5 and str(wd[5]).lstrip('-').isdigit() else 0])
        rot, sk = int(pg.get('rotated') or 0), float(pg.get('deskew') or 0)
        if rot not in (0, 90, 180, 270) or not math.isfinite(sk) or abs(sk) > 0.8:
            raise ValueError('layout: rotated is 0, 90, 180 or 270; deskew a small angle')
        out.append({'words': words, 'rotated': rot, 'deskew': sk})
    return out


def reads_in_browser():
    """The browser edition with its scan reader: the engine runs in the page (Pyodide) and the build carries ui/assets/ocr.js and its
    files (web/build.py leaves the BROWSER_OCR mark beside this module)."""
    import sys
    return sys.platform == 'emscripten' and (Path(__file__).parent / 'BROWSER_OCR').exists()


def keep_browser_reading(sha, texts, rep, tag, layout=None):
    """Keep what the page read from a scan (ui/assets/ocr.js), checked for shape and size: texts — one per page, in order; rep — as
    pdfcraft.ocr's report (words, pages, quality by page, second_reader, weak, models); tag — what read it ('ara+eng+best+paddle').
    The readings made before for the same bytes are made again on their next use."""
    if not re.fullmatch(r'[0-9a-f]{64}', sha or ''):
        raise ValueError('sha256: 64 hexadecimal characters')
    if not isinstance(texts, list) or not texts or len(texts) > BROWSER_MAX_PAGES or not all(isinstance(t, str) for t in texts):
        raise ValueError(f'texts: 1–{BROWSER_MAX_PAGES} pages of text')
    if sum(len(t) for t in texts) > BROWSER_MAX_CHARS:
        raise ValueError(f'texts: at most {BROWSER_MAX_CHARS} characters')
    rep = rep if isinstance(rep, dict) else {}
    quality = {}
    for k, v in ((rep.get('quality') or {}).items() if isinstance(rep.get('quality'), dict) else []):
        if str(k).isdigit() and isinstance(v, dict):
            q = {'words': int(v.get('words') or 0), 'low': float(v.get('low') or 0), 'mean': float(v.get('mean') or 0),
                 'numbers': [str(x)[:40] for x in (v.get('numbers') or [])][:20], 'read': str(v.get('read') or 'as scanned')[:20]}
            second = v.get('second') if isinstance(v.get('second'), dict) else None
            if second:
                q['second'] = {'read': int(second.get('read') or 0),
                               'changed': [{'was': str(c.get('was') or '')[:80], 'now': str(c.get('now') or '')[:80]}
                                           for c in (second.get('changed') or []) if isinstance(c, dict)][:30]}
            quality[int(k)] = q
    clean = {'words': int(rep.get('words') or 0), 'pages': [{'page': p, 'words': q['words']} for p, q in sorted(quality.items())],
             'quality': quality, 'second_reader': int(rep.get('second_reader') or 0),
             'weak': sorted(int(p) for p in (rep.get('weak') or []) if str(p).isdigit()), 'models': str(rep.get('models') or '')[:40]}
    rec = {'texts': texts, 'rep': clean, 'tag': re.sub(r'[^a-z0-9+]', '', str(tag or 'ocr').lower())[:40] or 'ocr'}
    lay = _layout(layout, len(texts))
    if lay is not None:
        rec['layout'] = lay
    BROWSER[(str(READ_DIR), sha)] = rec
    f = _browser_file(sha)
    if f is not None:
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
        except OSError:
            pass
    for k in [k for k in _READ if k[0] == sha]:
        _READ.pop(k, None)
    return rec


def carry_browser_reading(old_sha, new_data):
    """The page's reading of a file kept for a copy of it with the same pages (its version line set to 1.7, a fix): the copy is
    not read again."""
    rec = browser_reading(old_sha)
    new_sha = _sha(new_data)
    if rec and new_sha != old_sha and not browser_reading(new_sha):
        keep_browser_reading(new_sha, rec['texts'], rec['rep'], rec['tag'], rec.get('layout'))


def _browser_into(out, data, max_pages):
    """The page's reading of this file, where it has one: as a reading by PdfCraft (text, ocr, how sure it is), said to be the
    browser's (reader 'browser-ocr')."""
    rec = browser_reading(_sha(data))
    if not rec:
        return
    texts = rec['texts'][:max_pages] if max_pages else rec['texts']
    if any(t.strip() for t in texts):
        rep = dict(rec['rep'])                           # kept as JSON: the pages' numbers come back as text
        rep['quality'] = {int(p): q for p, q in (rep.get('quality') or {}).items() if not max_pages or int(p) <= max_pages}
        rep['weak'] = [int(p) for p in rep.get('weak') or [] if not max_pages or int(p) <= max_pages]
        out.update(text='\n'.join(texts), ocr=True, reader='browser-ocr', ocr_language='ara+eng', ocr_quality=ocr_summary(rep),
                   ocr_pages=len(rec['texts']))


AR_CLITIC = '(?:ال|وال|بال|فال|لل|و|ب|ل|ف)?'


def _kw_rx(word):
    """One keyword as a whole word: «coa» is not the start of «coated», «gmp» not part of a longer token, «عقد» not inside
    «المنعقدة». Latin keywords take an optional plural «s»; an Arabic keyword of more than three letters may sit inside a
    word (ال / و / ب attach to it), a short one only after those proclitics."""
    w = word.strip()
    if arabic.has_arabic(w):
        if len(w.replace(' ', '')) <= 3:
            return re.compile(r'(?<![\u0600-\u06ff])' + AR_CLITIC + re.escape(w) + r'(?![\u0600-\u06ff])')
        return re.compile(re.escape(w))
    return re.compile(r'(?<![a-z])' + re.escape(w) + r's?(?![a-z])')


KIND_GENERIC = {'إخطار', 'اخطار', 'ترخيص'}         # «a notification», «a licence»: every EDA letter says them, so they decide only when nothing else does


def _tier(word):
    return 2 if word.strip() in KIND_GENERIC else (0 if len(word.split()) > 1 else 1)     # 0 a phrase, 1 a single word, 2 a generic word


KIND_RX = [(kind, [(_kw_rx(w), _tier(w)) for w in words]) for kind, words in KINDS]


def _head(text, lines=10, chars=800):
    """The top of the page, where a document says what it is (authority, department, title)."""
    out = [ln for ln in (text or '').splitlines() if ln.strip()][:lines]
    return '\n'.join(out)[:chars]


CITE_BEFORE = re.compile(r'(?:رقم|برقم|no\.?|number|№)\s*[:\-]?\s*$')                 # «رقم إخطار التسجيل: 123»: a field label, not a title
CITE_AFTER = re.compile(r'^\s*(?:رقم|برقم|no\.?|number|#|№)\s*[:.\-]?\s*[\d\u0660-\u0669]')   # «… المسجل بإخطار التسجيل رقم 123», «…, Registration License No. 123»


def _cited(hay, m):
    """The keyword only cites another document by its number: preceded by «رقم» / «No.», or followed by «رقم 123» / «No. 123» in the
    middle of a line (a title can also carry a number, «إخطار تسجيل رقم 123» at the start of its line — that one stays a title)."""
    before, after = hay[max(0, m.start() - 16):m.start()], hay[m.end():m.end() + 24]
    if CITE_BEFORE.search(before):
        return True
    return bool(before.rsplit('\n', 1)[-1].strip(' \t:،,-')) and bool(CITE_AFTER.match(after))


def _first_kind(hay, tiers, cited):
    """The kind named first in `hay` by a keyword of these tiers (ties: the KINDS order); `cited` picks whether the number references
    («Registration License No. 123») are the keywords looked at or the ones skipped."""
    best = None
    for i, (kind, rxs) in enumerate(KIND_RX):
        for rx, tier in rxs:
            if tier in tiers:
                for m in rx.finditer(hay):
                    if _cited(hay, m) != cited:
                        continue
                    if best is None or (m.start(), i) < best[:2]:
                        best = (m.start(), i, kind)
                    break
    return best[2] if best else None


DECISIVE = [  # an authority's own title or department, a document's own heading: it settles the kind wherever it stands in the first pages
    ('licence', ['final registration license', 'final registration licence', 'إخطار تسجيل نهائي', 'إخطار تسجيل نهائى', 'اخطار تسجيل نهائي', 'اخطار تسجيل نهائى']),
    ('variation', ['الموافقة المبدئية على تغيير', 'الموافقة النهائية على تغيير', 'variation decision', 'variation committee', 'variations unit',
                   'لجنة المتغيرات', 'pack addition']),
    ('import', ['import & customs release', 'import and customs release', 'annual import approval', 'موافقة استيرادية', 'الموافقة الاستيرادية',
                'الإفراج الجمركي']),
    ('stability', ['الإدارة العامة للثبات', 'الادارة العامة للثبات', 'موافقة الثبات', 'stability approval']),
    ('validation', ['analytical method validation', 'method validation protocol', 'stability indicating assay']),
]


HEAD_DECISIVE = [  # a title that settles the kind only at the top of the document: a CoA's body may well name a reference standard
    ('refstd', ['working standard', 'reference standard', 'secondary standard', 'مادة مرجعية', 'المواد المرجعية']),
    ('sampling', ['sampling form', 'sample sending form', 'استمارة سحب', 'استمارة إرسال عينة']),
]


def _decisive(t, table=None):
    best = None
    for kind, phrases in table or DECISIVE:
        for p in phrases:
            i = t.find(p)
            if i >= 0 and (best is None or i < best[0]):
                best = (i, kind)
    return best[1] if best else None


def guess_kind(filename, text):
    """The document's kind from what it says about itself: its title (the top lines) before its body, the keyword printed first within
    them («شهادة تسعير» on line 2 beats «رقم إخطار التسجيل» on line 4), a reference to another document by its number («المسجل بإخطار
    التسجيل رقم 123», «Registration License No. 123») and a generic word («إخطار», «ترخيص») only when nothing else is named anywhere,
    the content before the file name."""
    t = (text or '')[:4000].lower()
    head = _head(t)
    name = ' ' + (filename or '').lower().replace('_', ' ').replace('-', ' ') + ' '
    k = _decisive(t) or _decisive(head, HEAD_DECISIVE)
    if k:
        return k
    for hay, tiers, cited in ((head, (0, 1), False), (t, (0, 1), False), (head, (0, 1), True), (t, (0, 1), True), (t, (2,), False), (t, (2,), True), (name, (0, 1, 2), False)):
        k = hay.strip() and _first_kind(hay, tiers, cited)
        if k:
            return k
    return 'other'


def content_kind(text):
    """What a document is, from what is written inside it — never from the name its file was given."""
    return guess_kind('', text)


def name_hint(filename):
    """What the file's name suggests: a hint for where to offer a file that could not be read, never a verdict about what it is."""
    k = guess_kind(filename, '')
    return None if k == 'other' else k


def iso_date(m):
    if m.group(1):
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    d, mo, y = m.group(4), m.group(5), m.group(6)
    if mo.isalpha():
        mo = MONTHS.get(mo[:3].lower())
        if not mo:
            return None
    try:
        d, mo = int(d), int(mo)
    except ValueError:
        return None
    if not (1 <= d <= 31 and 1 <= mo <= 12):
        return None
    return f'{y}-{mo:02d}-{d:02d}'


QUALIFIED_DATE = re.compile(r'(?:invalidation|expir\w*|valid\w*|revision|rev\.?|re-?test|analysis|mfg\.?|manufactur\w*|exp\.?|effective|injection|printed|review|انتهاء|الانتهاء)\s*$', re.I)
BARE_DATE = {'date:', 'date', 'dated', 'التاريخ', 'تاريخ', 'بتاريخ'}


def date_after(text, labels, window=90, near=None):
    """The date printed after one of the labels. A bare «Date:» that belongs to another field («Invalidation Date:», «Analysis
    Date:») is not the document's date; `near`: the date must start within that many characters of the label (a table cell's own
    value, not the next cell's)."""
    for lab in labels:
        rx = r'(?<![A-Za-z\u0600-\u06FF])' + (arabic.label_rx(lab) if arabic.has_arabic(lab) else re.escape(lab))
        for m in re.finditer(rx, text, re.I):
            if lab.lower() in BARE_DATE and QUALIFIED_DATE.search(text[max(0, m.start() - 18):m.start()]):
                continue
            dm = DATE.search(text, m.end(), m.end() + window)
            if dm and near is not None and dm.start() - m.end() > near:
                dm = None
            if dm:
                v = iso_date(dm)
                if v:
                    return v
    return None


def after(text, labels, pattern=r'([^\n:]{2,80})', window=120, flags=re.I):
    """The value printed after one of the labels (same line, after an optional colon). Arabic labels match leniently
    (alef / yaa / taa-marbuta variants); when nothing follows an Arabic label on its line, the value printed before it
    (visual order of some extractors) is taken."""
    for lab in labels:
        rx = r'(?<![A-Za-z\u0600-\u06FF])' + (arabic.label_rx(lab) if arabic.has_arabic(lab) else re.escape(lab) + r'(?![A-Za-z])')
        m = re.search(rx + r'\s*[:：\-]?\s*' + pattern, text[:60000], flags)
        if m and '\n' in text[m.start():m.start(1)] and text[m.end(1):m.end(1) + 1] in (':', '：'):
            m = None                                        # the labels of a table printed as a column: the «value» is the next label
        if m and m.group(1).strip(' .,-:'):
            return m.group(1).strip(' .,-:')
        if arabic.has_arabic(lab):
            m = re.search(r'^([^\n]{2,80}?)\s*[:：\-]?\s*' + rx + r'\s*[:：]?\s*$', text[:60000], flags | re.M)
            if m and m.group(1).strip(' .,-:'):
                return m.group(1).strip(' .,-:')
    return None


def label_value(text, labels):
    """The value of a labelled field in Latin script: the label opens its line or its table cell (a number or a bullet may precede it)
    and a colon or a dash follows it. «…the excretion of the active ingredients in human milk» is a sentence, not a field."""
    for lab in labels:
        m = re.search(r'(?im)(?:^|[|\t]|[^\S\n]{2,})[^\S\n]*(?:\d{1,2}[.)][^\S\n]*|[-•*][^\S\n]*)?' + re.escape(lab) + r'(?:\(s\)|s)?(?![A-Za-z])'
                      r'[^\S\n]*[:：\-|][^\S\n]*([^\n:|]{2,80})', text[:60000])
        if m and m.group(1).strip(' .,-:'):
            return m.group(1).strip(' .,-:')
    return None


def line_of(text, labels):
    """The whole line that carries one of the labels (for values printed elsewhere on that line)."""
    for lab in labels:
        rx = arabic.label_rx(lab) if arabic.has_arabic(lab) else re.escape(lab)
        m = re.search(r'^.*' + rx + r'.*$', text[:60000], re.I | re.M)
        if m:
            return m.group(0)
    return ''


def _clean(s):
    return re.sub(r'\s+', ' ', arabic.BIDI.sub('', s or '')).strip(' .,;:-')


FPP_TESTS = ('uniformity of dosage units', 'content uniformity', 'dissolution', 'average weight', 'disintegration', 'friability', 'hardness',
             'fill weight', 'uniformity of mass', 'deliverable volume', 'weight variation', 'minimum fill')
API_TESTS = ('retest date', 're-test date', 'retest', 'specific rotation', 'specific optical rotation', 'residue on ignition', 'sulphated ash',
             'sulfated ash', 'heavy metals', 'on dried basis', 'on the dried basis', 'on anhydrous basis')
FPP_FORMS = tuple(f for f in FORMS if f not in ('powder', 'solution', 'drops', 'spray', 'emulsion', 'foam', 'granules', 'patch', 'lotion', 'shampoo', 'gel'))


def coa_whose(kind, text, product=None):
    """A certificate of analysis is the finished product's ('fpp': a dosage form, its own tests) or a raw material's ('api': a supplier's
    material tests — retest date, specific rotation, residue on ignition — and nothing of a dosage form); None when it shows neither."""
    if kind != 'coa':
        return None
    low = (text or '').lower()
    head = _head(low, lines=14, chars=1400)
    fpp = bool((product or {}).get('dosage_form')) or any(w in low for w in FPP_TESTS) or any(f in head for f in FPP_FORMS)
    api = any(w in low for w in API_TESTS)
    return 'api' if api and not fpp else 'fpp' if fpp else None


def _material_name(name):
    """«Glycine BP 2018» → «Glycine»: the substance a supplier's CoA is about, without its monograph."""
    if not name:
        return None
    n = re.sub(r'\b(?:BP|USP|EP|Ph\.?\s?Eur\.?|JP)\b.*$', '', name, flags=re.I).strip(' -–,')
    return n or None


def fields_for(kind, filename, text):
    """The rules' reading of one document; keys follow SCHEMA, values are strings or lists."""
    t = text or ''
    low = t.lower()
    out = {'document': {'filename': filename, 'kind': kind}}
    doc = out['document']
    doc['number'] = after(t, ['Certificate No', 'Certificate Number', 'Certificate no', 'Cert. No', 'Licence No', 'License No', 'Registration No',
                              'Registration Number', 'Reg. No', 'Approval No', 'Authorisation No', 'Notification No', 'رقم الشهادة', 'رقم الترخيص', 'رقم التسجيل',
                              'رقم الإخطار', 'رقم الطلب', 'رقم الملف', 'رقم القيد', 'رقم الموافقة', 'إخطار رقم', 'رقم المرجع'],
                     r'([A-Z0-9][A-Z0-9\-/.]{2,30})', flags=0)
    for name in ISSUERS:
        if re.search(r'(?<![A-Za-z])' + re.escape(name.lower()) + r'(?![A-Za-z])', low):
            doc['issuer'] = name
            break
    doc['issuer'] = doc.get('issuer') or after(t, ['Issued by', 'Issuing authority', 'Competent authority', 'Certifying authority'])
    doc['issued'] = date_after(t, ['Date of issue', 'Issued on', 'Issue date', 'Date of issuance', 'Dated', 'Date:', 'تاريخ الإصدار', 'تاريخ الإخطار', 'تاريخ الموافقة',
                                   'تاريخ التسجيل', 'التاريخ', 'بتاريخ', 'تحريرا في', 'صادر في', 'تاريخ'])
    doc['valid_until'] = date_after(t, ['Valid until', 'Valid to', 'Expiry date', 'Expires on', 'Date of expiry', 'Validity', 'Valid through',
                                        'صالح حتى', 'صالحة حتى', 'ساري حتى', 'سارية حتى', 'تاريخ الانتهاء', 'ينتهي في', 'ينتهي', 'حتى تاريخ', 'الصلاحية حتى', 'نهاية الصلاحية'])
    cep = re.search(r'R\d-CEP\s?\d{4}-\d{3}(?:-Rev\s?\d{2})?', t)
    product = {}
    product['name'] = after(t, ['Trade name', 'Brand name', 'Proprietary name', 'Product name', 'Name of the product', 'Name of product',
                                'Invented name', 'الاسم التجاري', 'اسم المستحضر', 'اسم الدواء', 'اسم المنتج', 'المستحضر'])
    NAME_LABELS = ['Trade name', 'Brand name', 'Proprietary name', 'Product name', 'Invented name', 'الاسم التجاري', 'اسم المستحضر', 'اسم الدواء', 'اسم المنتج']
    if product.get('name') and re.search(r'سعر|التاريخ|رقم|الشكل|المادة|الشركة|^\W*$', product['name']):   # a table header, not a name
        product['name'] = None
    product['name_en'] = (arabic.latin_in(product['name']) or arabic.latin_in(line_of(t, NAME_LABELS))) if product.get('name') and arabic.has_arabic(product['name']) else None
    if product.get('name') and arabic.has_arabic(product['name']):
        product['name'] = re.sub(r'\s*\(?[A-Za-z][A-Za-z0-9 .,\-/%]{2,80}\)?\s*$', '', product['name']).strip() or product['name']
    if product.get('name') and (len(product['name'].split()) > 8 or re.search('طبقا|المذكور|سيادتكم|بموجب|وافق|اللجنة', product['name'])):
        product['name'] = None                                          # a sentence from the Arabic notes is not a trade name
    ident = kind in IDENTITY
    from . import vocab as _vocab
    product['dosage_form'] = after(t, ['Dosage form', 'Pharmaceutical form', 'الشكل الصيدلي', 'الشكل الدوائي', 'الصورة الصيدلية', 'الشكل الصيدلاني']) or label_value(t, ['Form'])
    if not product['dosage_form'] and (ident or kind in ABOUT_PRODUCT):          # the title names the form («Specifications of X powder for oral solution»)
        product['dosage_form'] = _form_in_title(_head(t, lines=14, chars=1400))
    if not product['dosage_form'] and ident:                                     # an identity document may state it in running text
        product['dosage_form'] = next((f for f in FORMS if f in low), None) or arabic.form_en(t)
    product['dosage_form_en'] = arabic.form_en(product['dosage_form']) if product.get('dosage_form') and arabic.has_arabic(product['dosage_form']) else None
    st = re.search(r'(?<![\d.,])((?:[1-9]\d*(?:[.,]\d+)?|0[.,]\d+)\s?(?:mg|mcg|µg|g|iu|%|ml))\b(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s?)?(?:ml|tablet|capsule|dose|g))?', t, re.I) if ident else None
    product['strength'] = (after(t, ['Strength', 'التركيز', 'العيار', 'القوة']) if ident else label_value(t, ['Strength'])) or (st.group(0).strip() if st else None) or (arabic.strength_en(t) if ident else None)      # in a technical document only a real field «Strength: …», never the word in a sentence
    if product.get('strength') and arabic.has_arabic(product['strength']):
        product['strength'] = arabic.strength_en(product['strength']) or product['strength']
    if product.get('strength') and not re.search(r'\d', product['strength']):
        product['strength'] = None
    product['manufacturer'] = after(t, ['Manufacturer', 'Manufactured by', 'Manufacturing site', 'Name of manufacturer', 'Name and address of the manufacturer',
                                        'Manufacturer name', 'الشركة المصنعة', 'الشركة المنتجة', 'جهة التصنيع', 'مكان التصنيع', 'اسم المصنع', 'المصنع'])
    product['manufacturer_address'] = after(t, ['Site address', 'Address of manufacturer', 'Manufacturing site address', 'Address', 'عنوان المصنع', 'عنوان الشركة', 'العنوان'])
    if product.get('manufacturer_address') and (re.search('هيئة الدواء|وزارة الصحة', product['manufacturer_address'])
                                                or any(re.search(r'(?<![A-Za-z])' + re.escape(i) + r'(?![A-Za-z])', product['manufacturer_address']) for i in ISSUERS if len(i) > 4)):
        product['manufacturer_address'] = None                                         # the authority's address in a letter footer
    apis = [_clean(x) for x in re.split(r'[,;/+]|\band\b|\.\s+(?=[A-Z])', label_value(t, ['Active ingredient', 'Active substance', 'Active pharmaceutical ingredient', 'INN', 'Generic name'])
                                        or after(t, ['المادة الفعالة', 'المواد الفعالة', 'المكونات الفعالة', 'الاسم العلمي']) or '') if _clean(x)]
    API_LABELS = ['Active ingredient', 'Active substance', 'INN', 'Generic name', 'المادة الفعالة', 'المواد الفعالة', 'المكونات الفعالة', 'الاسم العلمي']
    if apis and all(arabic.has_arabic(a) and not arabic.latin_in(a) for a in apis) and len(apis) == 1 and arabic.latin_in(line_of(t, API_LABELS)):
        apis = [arabic.latin_in(line_of(t, API_LABELS))]
    apis = [arabic.latin_in(a) or re.sub(r'\s*\d.*$', '', a).strip() or a for a in apis]      # «باراسيتامول 500 مجم (Paracetamol)» → Paracetamol
    apis = [a for a in apis if not re.match(r'^(?:each|every|&|and)\b', a, re.I)]
    if cep and not apis:
        m = re.search(r'for\s+([A-Z][a-z]+(?:\s[a-z]+)?)', t)
        if m:
            apis = [m.group(1)]
    envelope = {'applicant': after(t, ['Applicant', 'Marketing authorisation holder', 'Marketing authorization holder', 'MA holder', 'Licence holder',
                                      'License holder', 'Holder', 'Registrant', 'مقدم الطلب', 'صاحب الترخيص', 'الشركة صاحبة الترخيص', 'صاحب التسجيل',
                                      'الشركة المالكة', 'الشركة الطالبة', 'اسم الشركة', 'الوكيل', 'المستورد', 'الشركة']),
                'tracking': (re.search(r'\bP-[A-Z]{2,5}-\d{3,6}\b', t) or [None])[0] if re.search(r'\bP-[A-Z]{2,5}-\d{3,6}\b', t) else None}
    profile = {}
    if ident:                                              # what kind of licence it is, is said by the documents that state the product — not by a word in a method
        if re.search(r'(?<![a-z])toll(?![a-z])', low):
            profile['licence'] = 'toll'
        if 'imported' in low or kind == 'cpp' or 'country of import' in low or 'مستورد' in t:
            profile['origin'] = 'imported'
        elif re.search(r'\blocal\b', low) or 'محلي' in t:
            profile['origin'] = 'local'
        if 'generic' in low or 'مثيل' in t or 'جنيس' in t:
            profile['dossier_kind'] = 'generic'
        elif 'innovator' in low or 'مبتكر' in t:
            profile['dossier_kind'] = 'innovator'
        if re.search(r're-?registration|renewal', low) or re.search(arabic.label_rx('إعادة تسجيل') + '|' + arabic.label_rx('إعادة التسجيل') + '|تجديد', t):
            profile['activity'] = 're_registration'
    form = (product.get('dosage_form_en') or product.get('dosage_form') or '').lower()
    profile['admin_route'] = next((r for r, ws in ROUTE.items() if any(w in form for w in ws)), None)
    specifics = []
    if 'coated' in form:
        specifics.append('coated')
    if 'hard capsule' in form or 'capsule' in form:
        specifics.append('capsule_hard')
    if 'injection' in form or 'infusion' in form or (ident and re.search(r'(?<![a-z])sterile(?![a-z])', low)):      # «sterile peptone water» in a test is not the product
        specifics.append('sterile')
    if 'powder for injection' in form and 'solvent' in low:
        specifics.append('powder_inj_with_solvent')
    profile['dosage_specifics'] = specifics
    if ident and re.search(r'\b(BP|USP|Ph\.? ?Eur\.?)\b', t):
        profile['pharmacopoeial'] = True
    batches = []
    whose = coa_whose(kind, t, product) if kind == 'coa' else None          # a supplier's CoA of a raw material, or the finished product's
    material = None
    if whose == 'api':
        material = _material_name(product.get('name')) or next((_material_name(a) for a in apis if a), None)
    for m in re.finditer(r'\b(?:batch|lot)\s*(?:no\.?|number|#)?\s*[:\-]?\s*(?=[A-Z0-9\-/]*\d)([A-Z0-9][A-Z0-9\-/]{2,19})\b', t if kind in ('coa', 'cadc', 'bmr', 'stability') else '', re.I):
        no = m.group(1)                                     # a batch number has a digit in it: «Batch Weight», «Batch Size» are not numbers
        if no.lower() not in ('no', 'number', 'size') and no not in [b['no'] for b in batches]:
            api_batch = (kind == 'cep' and apis) or whose == 'api'
            batches.append({'no': no, 'kind': 'api' if api_batch else 'fpp', **({'api': material} if api_batch and material else {})})
    size = after(t, ['Batch size', 'Lot size'], r'([\d.,]+\s?(?:units|tablets|capsules|kg|g|l|ml|vials|bottles)?)')
    MFG, EXP = ['Date of manufacture', 'Manufacturing date', 'Mfg. date', 'Mfg date', 'Date of manufacturing'], ['Expiry date', 'Exp. date', 'Exp date', 'Date of expiry']
    mfg = date_after(t, MFG, near=14) or _month_after(t, MFG)
    exp = date_after(t, EXP, near=14) or _month_after(t, EXP)
    for b in batches[:1]:
        if size:
            b['size'] = size
        if mfg:
            b['date'] = mfg
        if exp:
            b['expiry'] = exp
    results, specs = [], []
    if kind in ('coa', 'spec', 'stability'):
        for col, rows in spec_tables(t):                    # the document's own tables: test | specification | result | method
            for rc in rows:
                test = _cell(rc, col.get('test'))
                if not test or test.lower() in ('test', 'tests'):
                    continue
                limit, value, method = _cell(rc, col.get('limit')), _cell(rc, col.get('result')), _cell(rc, col.get('method'))
                if 'result' in col and not value and len(rc) >= 2:
                    value = rc[-1].strip()                  # a row with a merged cell: its result is still its last cell
                if limit or method:
                    specs.append({'test': test[:120], 'limit': limit[:400], 'method': method[:120] or None})
                if kind == 'coa' and value:
                    results.append({'batch': batches[0]['no'] if batches else None, 'test': test[:120], 'value': value[:120]})
        if not specs and not results and len(t) < 6000:      # a short sheet printed as lines (a PDF): a known test name at the start of a line
            for line in t.splitlines():
                ll = line.lower()
                test = next((x for x in TESTS if ll.startswith(x)), None)
                if not test:
                    continue
                nums = re.findall(r'(?<![\w.])(\d+(?:[.,]\d+)?\s?%?)(?![\w.])', line)
                tail = line[len(test):].strip(' :\t')
                if kind == 'coa' and nums:
                    results.append({'batch': batches[0]['no'] if batches else None, 'test': test.title() if test != 'ph' else 'pH', 'value': nums[-1].strip()})
                elif tail and re.search(r'\d|complies|conform|white|clear|nmt|not more|not less', tail, re.I):
                    specs.append({'test': test.title() if test != 'ph' else 'pH', 'limit': tail[:120], 'method': None})
    registration = {}
    if kind in ('licence', 'pricing', 'annex1'):
        registration = {'reg_no': doc.get('number'), 'reg_date': doc.get('issued'),
                        'shelf_life': after(t, ['Shelf life', 'Shelf-life', 'مدة الصلاحية'], r'(\d{1,3}\s?(?:months|month|years|year|شهر|سنة|سنوات))'),
                        'storage': after(t, ['Storage condition', 'Storage', 'Store', 'ظروف التخزين', 'التخزين', 'يحفظ', 'الحفظ']),
                        'price': after(t, ['Public price', 'Price', 'سعر الجمهور', 'سعر البيع للجمهور', 'السعر', 'سعر'], r'([\d.,]+\s?(?:EGP|LE|L\.E\.|جنيه|ج\.م)?)'),
                        'packs': [p for p in [after(t, ['Pack size', 'Pack', 'Presentation', 'حجم العبوة', 'العبوة', 'التعبئة'])] if p]}
    out.update({'product': {k: _clean(v) if isinstance(v, str) else v for k, v in product.items() if v},
                'profile': {k: v for k, v in profile.items() if v not in (None, [], '')},
                'apis': [{'name': a, **({'cep_no': cep.group(0), 'option': 'CEP'} if cep else {})} for a in apis],
                'envelope': {k: _clean(v) for k, v in envelope.items() if v}, 'batches': batches, 'specs': specs, 'results': results,
                'registration': {k: v for k, v in registration.items() if v}, 'composition': []})
    eda = intake_eda.read(t)
    if eda:
        for sec in ('product', 'envelope', 'registration', 'profile'):
            for k, v in eda.get(sec, {}).items():
                if v not in (None, '', []):
                    out[sec][k] = v
        if eda.get('apis'):
            out['apis'] = eda['apis']
            if len(eda['apis']) > 1 and not eda['product'].get('strength'):
                out['product'].pop('strength', None)                    # a combination: the strengths live on the substances
            form = (out['product'].get('dosage_form_en') or out['product'].get('dosage_form') or '').lower()
            out['profile']['admin_route'] = out['profile'].get('admin_route') or next((r for r, ws in ROUTE.items() if any(w in form for w in ws)), None)
        if eda.get('batches'):                                   # the form's batch row (expiry, conformity) joins what the generic rules read (size, date)
            merged = []
            for eb in eda['batches']:
                g = next((b for b in batches if b['no'] == eb['no']), None)
                merged.append({**g, **{k: v for k, v in eb.items() if v}} if g else eb)
            out['batches'] = merged + [b for b in batches if b['no'] not in {x['no'] for x in merged}]
            if whose == 'api':                                   # a supplier's CoA: every batch it lists is the substance's, whichever reader found it
                out['batches'] = [dict(b, kind='api', **({'api': b.get('api') or material} if (b.get('api') or material) else {})) for b in out['batches']]
        if eda.get('composition'):
            out['composition'] = eda['composition']
        for k, v in eda.get('document', {}).items():
            if v:
                doc[k] = v
        if eda.get('suppliers'):
            doc['suppliers'] = eda['suppliers']
        out['profile'] = {k: v for k, v in out['profile'].items() if v not in (None, [], '')}
    _standardise(out)
    return out


def _form_in_title(head):
    """The dose form a document's title names: a form of two words or more («powder for oral solution», «film-coated tablet»). A
    single word at the top of a page is too often something else («Injection date» on a chromatogram, «Solution» in a method)."""
    from . import vocab
    low, best = ' ' + re.sub(r'\s+', ' ', (head or '').lower()) + ' ', None
    for f in vocab.forms():
        for n in [f['en']] + list(f.get('syn') or []):
            nn = re.sub(r'\s+', ' ', n.lower()).strip()
            if len(nn.split()) >= 2 and re.search(r'(?<![a-z])' + re.escape(nn) + r'(?![a-z])', low) and (best is None or len(nn) > best[0]):
                best = (len(nn), f['en'])
    return best[1] if best else None


def _month_after(text, labels):
    """«Mfg. date : 06/2023» → «2023-06»: a month printed right after its label."""
    for lab in labels:
        m = re.search(r'(?<![A-Za-z])' + re.escape(lab) + r'[^\S\n]*[:.\-]?[^\S\n]*(\d{1,2})[^\S\n]*[/\-.][^\S\n]*(\d{4})(?![\d/\-.])', text or '', re.I)
        if m and 1 <= int(m.group(1)) <= 12:
            return f'{m.group(2)}-{int(m.group(1)):02d}'
    return None


def _cell(row, i):
    return row[i].strip() if i is not None and i < len(row) else ''


def spec_tables(text):
    """The specification / result tables of a document whose table rows are single lines «cell | cell | cell» (Word files):
    [({column name: index}, [rows of cells])] — a header row names the test and its specification (and its result, its method)."""
    out, lines, i = [], (text or '').splitlines(), 0
    while i < len(lines):
        cells = [c.strip() for c in lines[i].split('|')]
        low = [re.sub(r'[^a-z ]', '', c.lower()).strip() for c in cells]
        if len(cells) >= 2 and any(re.fullmatch(r'tests?|test items?|test parameters?|parameters?|items?', c) for c in low) and \
                any(re.search(r'specification|limit|acceptance|criteria|requirement', c) for c in low):
            col = {}
            for k, c in enumerate(low):
                for name, rx in (('test', r'tests?|test items?|test parameters?|parameters?|items?'), ('limit', r'.*(?:specification|limit|acceptance|criteria|requirement).*'),
                                 ('result', r'.*results?.*'), ('method', r'.*(?:method|procedure).*'), ('reference', r'.*reference.*')):
                    if name not in col and re.fullmatch(rx, c):
                        col[name] = k
                        break
            rows, j = [], i + 1
            while j < len(lines) and '|' in lines[j]:
                rows.append([c.strip() for c in lines[j].split('|')])
                j += 1
            if 'test' in col and rows:
                out.append((col, rows))
            i = j
        else:
            i += 1
    return out


def _standardise(out):
    """Controlled vocabularies: the dose form → its standard entry (and the route it implies), countries → ISO entries."""
    from . import vocab
    P = out.get('product') or {}
    printed = re.sub('[\u0600-\u06ff]+', ' ', P.get('dosage_form') or '').strip()     # the form as printed (its Latin part) before a translation of its Arabic
    std = vocab.match_form(printed) or vocab.match_form(P.get('dosage_form_en') or '') or vocab.match_form(P.get('dosage_form') or '')
    if std:
        P['dosage_form_std'] = std['id']
        P['dosage_form_en'] = std['en'] if vocab.match_form(printed) else (P.get('dosage_form_en') or std['en'])
        out.setdefault('profile', {})
        if not out['profile'].get('admin_route'):
            out['profile']['admin_route'] = std['route']
    out['apis'] = clean_apis(out.get('apis') or [])
    for a in out.get('apis') or []:
        c = vocab.match_country(a.get('country') or '')
        if c:
            a['country'], a['country_code'] = c['en'], c['code']
    c = vocab.match_country(P.get('manufacturer_country') or '')
    if c:
        P['manufacturer_country'], P['manufacturer_country_code'] = c['en'], c['code']


# ---- active substances: one plausible entry per substance
API_STOP = {'each', 'every', 'contains', 'contain', 'containing', 'tablet', 'tablets', 'capsule', 'capsules', 'and', 'or', 'of', 'the', 'per', 'with', 'film', 'coated',
            'powder', 'solution', 'for', 'injection', 'active', 'ingredient', 'ingredients', 'substance', 'substances', 'strength', 'strengths', 'equivalent', 'to', 'as',
            'base', 'dose', 'excipients', 'excipient', 'manufacturer', 'manufactured', 'by', 'label', 'claim', 'product', 'name', 'trade', 'form', 'dosage', 'composition',
            'unit', 'units', 'iu', 'mg', 'g', 'ml', 'mcg', 'µg', 'qs', 'q.s', 'ad', 'other', 'inactive', 'inactives', 'actives', 'total', 'weight',
            'topical', 'cutaneous', 'oral', 'cream', 'ointment', 'gel', 'suspension', 'syrup', 'drops', 'spray', 'use', 'dusting', 'lotion'}
# what a form or a leaflet prints near its substances and is never one: a table heading, a section title, an empty answer
API_HEADERS = {'quantity', 'quantities', 'specification', 'specifications', 'description', 'appearance', 'reference', 'function', 'standard', 'amount', 'item', 'items',
               'posology', 'indications', 'contraindications', 'overdose', 'overdosage', 'management', 'none', 'nil', 'n/a', 'not relevant', 'not applicable', 'no data',
               'none known', 'method of administration', 'pregnancy and lactation', 'symptoms and signs', 'generic name', 'trade name', 'physical character', 'shelf life'}
API_SENTENCE = re.compile(r'(?<![A-Za-z])(?:should|must|may|is|are|was|were|not|see|this|that|which|has|have|been|will|can)(?![A-Za-z])', re.I)
API_LEAD = {'in', 'on', 'of', 'for', 'with', 'by', 'to', 'from', 'at', 'as', 'the', 'a', 'an', 'no', 'and', 'or'}      # «in human milk» is the tail of a sentence
API_LOOKS = {'white', 'off', 'yellow', 'yellowish', 'colourless', 'colorless', 'clear', 'transparent', 'pale', 'pink', 'brown', 'homogenous', 'homogeneous', 'opaque',
             'plastic', 'crystalline', 'fine', 'odourless', 'odorless', 'almost', 'light'}                              # an appearance: «White homogenous powder»
ROMAN = re.compile(r'\((I{1,3}|IV|V|VI)\)')
API_SALTS = {'sulphate', 'sulfate', 'hydrochloride', 'hcl', 'sodium', 'potassium', 'zinc', 'calcium', 'magnesium', 'acetate', 'citrate', 'maleate', 'fumarate', 'tartrate',
             'mesylate', 'besylate', 'succinate', 'phosphate', 'nitrate', 'bromide', 'chloride', 'trihydrate', 'dihydrate', 'monohydrate', 'hydrate', 'anhydrous', 'base',
             'usp', 'bp', 'ep', 'ph', 'eur', 'micronized', 'micronised'}
# a substance that is itself a salt (sodium chloride, magnesium sulphate, aluminium hydroxide): its metal and its acid part ARE the name
API_CATIONS = {'sodium', 'potassium', 'zinc', 'calcium', 'magnesium', 'aluminium', 'aluminum', 'ferrous', 'ferric', 'lithium', 'ammonium', 'silver', 'copper', 'cupric', 'barium'}
API_ANIONS = {'chloride', 'sulphate', 'sulfate', 'acetate', 'citrate', 'phosphate', 'nitrate', 'bromide', 'iodide', 'fluoride', 'carbonate', 'bicarbonate', 'hydrogen',
              'hydroxide', 'oxide', 'gluconate', 'lactate', 'fumarate', 'tartrate', 'succinate', 'maleate', 'trisilicate', 'glycerophosphate', 'picosulfate', 'picosulphate'}
API_GENERIC = {'vitamin', 'vitamins', 'acid', 'oil', 'extract', 'insulin'}
API_COMPANY = re.compile(r'(?<![A-Za-z])(?:ltd|limited|inc|gmbh|pharma\w*|industr\w*|laborator\w*|labs?|chemicals?|corp\w*|llc|plc|pvt|srl|biotech\w*)(?![A-Za-z])'
                         r'|(?<![A-Za-z])(?:co|s\.a|s\.p\.a)\.', re.I)          # «Unichem Laboratories», «X Co. Ltd» — never «Co-trimoxazole»
API_BAD_WORDS = re.compile(r'\b(contains?|each|every|per\s|manufactur\w*|licen[cs]\w*|holder|dated?|certificat\w*|approv\w*|registration|price[sd]?|pack\w*|shelf|storage'
                           r'|batch(?:es)?|lots?|expiry|valid\w*)\b', re.I)
AR_SENTENCE = ('في', 'من', 'على', 'إلى', 'الى', 'التي', 'الذي', 'يحتوي', 'تحتوي', 'كل', 'مع', 'عن', 'هذا', 'هذه', 'يكون', 'تكون', 'أو', 'او', 'ثم', 'لكل')
STRENGTH_RX = re.compile(r'(\d+(?:[.,]\d+)?\s*(?:mg|g|mcg|µg|iu|i\.u\.|ml|%|units?|ملجم|مجم|جم|مل|وحدة)(?:\s*\([^)]*\))?(?:\s*/\s*\d*\s*(?:g|ml|mg|جم|مل))?)', re.I)


def _salt_substance(words):
    """«Sodium chloride», «Magnesium sulphate»: a metal and an acid part and nothing else — a whole substance, not a salt suffix."""
    return any(w in API_CATIONS for w in words) and any(w in API_ANIONS for w in words) and all(w in API_CATIONS or w in API_ANIONS or w in API_SALTS for w in words)


def api_key(name):
    """The substance behind a printed name: no salt, no strength, no brackets, lower case — «NEOMYCIN SULPHATE 3.500 mg (3300 unit)» → «neomycin».
    The digits of a name stay («vitamin b1» ≠ «vitamin b12»), and a substance that is itself a salt keeps its words («magnesium hydroxide»)."""
    low = re.sub(r'\(.*?\)', ' ', (name or '').lower())
    low = low.replace('sulph', 'sulf').replace('aluminium', 'aluminum').replace('oestr', 'estr').replace('haem', 'hem')     # one substance, two spellings
    low = STRENGTH_RX.sub(' ', low)
    low = re.sub(r'[^a-z0-9\u0600-\u06ff ]+', ' ', low)
    toks = [w for w in low.split() if not w.isdigit()]
    if _salt_substance([w for w in toks if w not in API_STOP]):
        return ' '.join(w for w in toks if w not in API_STOP)
    words = [w for w in toks if w not in API_SALTS and w not in API_STOP]
    return ' '.join(words) or ' '.join(toks)


def _typo(a, b):
    """One slip of the typist: two neighbouring letters swapped («bactiracin» for «bacitracin»)."""
    if len(a) != len(b) or len(a) < 8:
        return False
    d = [i for i in range(len(a)) if a[i] != b[i]]
    return len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]]


def _same_substance(a, b):
    """Two keys name one substance: equal, or one's words all inside the other's («hyoscine» / «hyoscine butylbromide», «vitamin a» /
    «vitamin a palmitate») when the shorter is a name of its own: a real word (not just «vitamin» or «acid»), or a vitamin with its
    letter. Letters inside a word never count: «carbonate» is not «bicarbonate», «vitamin b1» is not «vitamin b12»."""
    if a == b or _typo(a, b):
        return True
    wa, wb = set(a.split()), set(b.split())
    small, big = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    named = any(len(w) >= 4 and w not in API_GENERIC for w in small) or ('vitamin' in small and any(re.fullmatch(r'[a-z]\d{0,2}', w) for w in small))
    return bool(small) and small <= big and named


def plausible_api(name, dosed=False):
    """dosed: a strength was printed with it («Calcium 500 mg», «Zinc 10 mg»): a metal alone is then the substance."""
    n = _clean(name)
    if not n or len(n) < 3 or len(n) > 70:
        return False
    stripped = _clean(STRENGTH_RX.sub(' ', re.sub(r'\(.*?\)', ' ', n)))
    words = stripped.split()
    if not words or len(words) > 6:
        return False
    if len(re.sub(r'[^A-Za-z\u0600-\u06ff]', '', stripped)) < 3:
        return False
    if API_BAD_WORDS.search(stripped) or API_COMPANY.search(stripped):             # a label, a pack, a company («Unichem Laboratories»)
        return False
    if arabic.has_arabic(stripped) and not arabic.latin_in(stripped):
        return len(words) <= 4 and not any(w in AR_SENTENCE for w in words)
    low = [w.lower() for w in words]
    if ' '.join(low) in intake_eda.COUNTRIES:                                       # «India» after «…, manufactured by X, India»
        return False
    if ' '.join(low).strip('.:') in API_HEADERS or low[0] in API_LEAD or API_SENTENCE.search(stripped):
        return False                                                                # a heading, the tail of a sentence, a sentence
    if all(w.strip('.,') in API_LOOKS or w in API_STOP for w in low):               # «White homogenous powder», «Transparent pale pink solution»
        return False
    if all(w in API_STOP or w in API_SALTS for w in low):
        named = [w for w in low if w not in API_STOP]
        return _salt_substance(named) or (dosed and len(named) == 1 and named[0] in API_CATIONS)
    return True


def clean_apis(apis):
    """Plausible, de-duplicated active substances: a strength glued to the name moves to `strength`, spellings / salts / strengths of one
    substance become one entry (the richest wins), ordinary text is dropped; at most 40 (a multivitamin has two dozen)."""
    out, flat = [], []
    for a in apis or []:
        a = dict(a) if isinstance(a, dict) else {'name': str(a)}
        parts = re.split(r'(?<=[a-z]{4})\.\s+(?=[A-Z][a-z]{3})', str(a.get('name') or ''))       # «threonine. Neomycin sulphate»: two names glued
        flat += [{'name': x} for x in parts[:-1]] + [{**a, 'name': parts[-1]}]
    for a in flat:
        name = _clean(str(a.get('name') or ''))
        m = STRENGTH_RX.search(ROMAN.sub(lambda r: '\x01' + r.group(1) + '\x02', name))
        if m and (m.start() > 2 or name[m.end():].strip()):
            if not a.get('strength'):
                a['strength'] = _clean(m.group(1))
            name = _clean(name[:m.start()] if m.start() > 2 else name[m.end():])     # «500 mg Paracetamol» → Paracetamol
        name = ROMAN.sub(lambda r: '\x01' + r.group(1) + '\x02', name)                      # «Iron (III) hydroxide»: the bracket is part of the name
        name = re.sub(r'\s*[(（][^)）]*[)）]\s*(?=[A-Za-z\u0600-\u06ff])', ' ', name)           # a remark inside the name goes, the name's tail stays
        name = (re.sub(r'\s*[(（].*$', '', name).strip(' -:;,') or name).replace('\x01', '(').replace('\x02', ')')
        if not plausible_api(name, dosed=bool(m or a.get('strength'))):
            continue
        if name.isupper() and len(name) > 3:
            name = name.title()
        key = api_key(name)
        cur = next((x for x in out if _same_substance(x['_k'], key)), None)
        if cur:
            for k, v in a.items():
                if v and not cur.get(k) and k != 'name':
                    cur[k] = v
            if len(name) > len(cur['name']) and set(cur['_k'].split()) <= set(key.split()):
                cur['name'], cur['_k'] = name, key
        else:
            out.append({**a, 'name': name, '_k': key})
    for x in out:
        x.pop('_k', None)
    return out[:40]


def merge(items):
    """Combine the readings of several documents into one fill (first non-empty value, by document priority)."""
    order = sorted(items, key=lambda it: PRIORITY.index(it['document']['kind']) if it['document']['kind'] in PRIORITY else 99)
    fill = {'product': {}, 'profile': {}, 'envelope': {}, 'registration': {}, 'apis': [], 'batches': [], 'specs': [], 'results': [], 'composition': [], 'documents': []}
    for it in order:
        ident = it['document']['kind'] in IDENTITY
        for sec in ('product', 'profile', 'envelope', 'registration'):
            if sec in ('profile', 'registration') and not ident:
                continue                                     # the product's profile and registration are what the documents that state the product say
            for k, v in it.get(sec, {}).items():
                if sec == 'product' and k in ('dosage_form_en', 'dosage_form_std'):
                    continue                                 # they travel with the form they belong to (below)
                if sec == 'product' and k == 'strength' and not ident:
                    continue                                 # a strength is stated by the licence / the form, not picked from a method
                if v not in (None, '', []) and not fill[sec].get(k):
                    fill[sec][k] = v
                    if sec == 'product' and k == 'dosage_form':
                        for kk in ('dosage_form_en', 'dosage_form_std'):
                            if it['product'].get(kk):
                                fill['product'][kk] = it['product'][kk]
        for a in it.get('apis', []):
            a['name'] = _clean(a.get('name'))
        stated = bool(fill['apis']) and any(x['document']['kind'] in IDENTITY and x.get('apis') for x in order)
        for a in it.get('apis', []):
            cur = next((x for x in fill['apis'] if x['name'].lower() == a['name'].lower() or _same_substance(api_key(x['name']), api_key(a['name']))), None)
            if cur:
                cur.update({k: v for k, v in a.items() if v and not cur.get(k)})
            elif ident or not stated:                        # the actives are the ones the licence / application states; a method that names a reagent adds nothing
                fill['apis'].append(dict(a))
        for b in it.get('batches', []):
            if b['no'] not in [x['no'] for x in fill['batches']]:
                fill['batches'].append(b)
        if it.get('specs') and not fill['specs']:            # one specification: the first document (by priority) that holds its table
            fill['specs'] = list(it['specs'])
        for row in it.get('results', []):
            if row not in fill['results']:
                fill['results'].append(row)
        if len(it.get('composition') or []) >= 2 and not fill['composition'] and (ident or len(it['composition']) >= 3):      # a composition is a table (one stray row is not one)
            fill['composition'] = list(it['composition'])
        fill['documents'].append(it['document'])
    fill['apis'] = clean_apis(fill['apis'])
    if len(fill['apis']) > 1:
        fill['product'].pop('strength', None)                # a combination: the strengths live on the substances
    if fill['product'].get('dosage_form_std'):               # the route follows the form the product was read as
        from . import vocab as _vocab
        f = next((x for x in _vocab.forms() if x['id'] == fill['product']['dosage_form_std']), None)
        if f:
            fill['profile']['admin_route'] = f['route']
    return fill


TEXT_BACK = 60000       # the reading handed back to the page (it sends it again when the rules re-run): enough for the 12 pages read


def read_files(files):
    """files: [(filename, bytes)] -> per-file readings + the merged fill + the text the AI layer will read."""
    items, texts = [], []
    for name, data in files:
        pt = read_text(name, data)
        kind = content_kind(pt['text'])
        items.append(fields_for(kind, name, pt['text']))
        texts.append({'filename': name, 'kind': kind, 'kind_hint': name_hint(name) if kind == 'other' else None, 'pages': pt['pages'], 'scanned': pt['scanned'], 'file': pt['kind_of_file'],
                      'arabic': pt['arabic'], 'chars': len(re.sub(r'\s', '', pt['text'])), 'text': pt['text'][:TEXT_BACK], 'found': found_fields(items[-1]),
                      **({'ocr': True, 'ocr_language': pt.get('ocr_language'), 'ocr_quality': pt.get('ocr_quality'), 'reader': pt.get('reader')} if pt.get('ocr') else {})})
    return {'files': texts, 'rules': merge(items)}


# ---- the document-kind rule: which items a recognised kind of document belongs to (an upload elsewhere is refused)
KIND_HOME = {'pricing': ['M1-05'], 'gmp': ['M1-37', 'M1-38'], 'cpp': ['M1-14'], 'cep': ['M1-39', 'S-16'], 'coa': ['M1-35', 'S-10', 'P-11'],
             'licence': ['M1-04', 'M1-28'], 'commercial': ['M1-19'], 'poa': ['M1-02'], 'contract': ['M1-24'], 'smpc': ['M1-09', 'M1-42'],
             'cadc': ['M1-34', 'P-11'], 'composition': ['M1-31', 'P-01'], 'spec': ['M1-36', 'S-08', 'P-09', 'P-08'], 'annex1': ['M1-01'],
             'loa': ['M1-30'], 'factory': ['M1-18'], 'bmr': ['R-01', 'R-02'], 'stability': ['M1-34', 'P-16', 'S-14'],
             'method': ['P-10', 'S-09'], 'validation': ['P-10', 'S-09'], 'receipt': ['M1-03'], 'variation': ['M1-07'],
             'import': ['M1-13'], 'refstd': ['S-12', 'P-14'], 'sampling': []}
PER_API_ONLY = ('M1-38', 'M1-13', 'S-12')      # items kept one per active substance: an unresolved document is offered among them, not elsewhere
TECHNICAL = ('spec', 'method', 'validation')        # one document often holds two of them (a specification with its test methods): any of their items takes it
KIND_NAMES = {'pricing': {'en': 'pricing certificate', 'ar': 'شهادة تسعير'}, 'gmp': {'en': 'GMP certificate', 'ar': 'شهادة GMP'}, 'cpp': {'en': 'CPP', 'ar': 'شهادة CPP'},
              'cep': {'en': 'CEP', 'ar': 'شهادة CEP'}, 'coa': {'en': 'certificate of analysis', 'ar': 'شهادة تحليل'}, 'licence': {'en': 'registration licence / notification', 'ar': 'إخطار / رخصة تسجيل'},
              'commercial': {'en': 'commercial register', 'ar': 'سجل تجاري'}, 'poa': {'en': 'power of attorney', 'ar': 'توكيل'}, 'contract': {'en': 'agreement', 'ar': 'عقد'},
              'smpc': {'en': 'SmPC / leaflet', 'ar': 'نشرة / SmPC'}, 'cadc': {'en': 'CADC conformity letter', 'ar': 'خطاب مطابقة CADC'}, 'composition': {'en': 'composition certificate', 'ar': 'شهادة تركيب'},
              'spec': {'en': 'specification', 'ar': 'مواصفات'}, 'annex1': {'en': 'application form (Annex I)', 'ar': 'نموذج الطلب'}, 'loa': {'en': 'letter of access / DMF', 'ar': 'خطاب سماح / DMF'},
              'factory': {'en': 'factory licence', 'ar': 'رخصة مصنع'}, 'bmr': {'en': 'batch record', 'ar': 'سجل تشغيلة'}, 'stability': {'en': 'stability document', 'ar': 'مستند ثبات'},
              'method': {'en': 'method of analysis', 'ar': 'طريقة تحليل'}, 'validation': {'en': 'method validation / chromatograms', 'ar': 'تحقق من طريقة التحليل / كروماتوجرام'},
              'receipt': {'en': 'fees receipt', 'ar': 'إيصال رسوم'}, 'variation': {'en': 'variation approval', 'ar': 'موافقة تغيير'},
              'import': {'en': 'import approval', 'ar': 'موافقة استيرادية'}, 'refstd': {'en': 'reference / working standard certificate', 'ar': 'شهادة مادة مرجعية'},
              'sampling': {'en': 'sampling form (not a dossier document)', 'ar': 'استمارة سحب عينة (مش مستند في الملف)'}}
ORG_STOP = {'pharmaceutical', 'pharmaceuticals', 'pharma', 'pharm', 'company', 'co', 'ltd', 'limited', 'inc', 'corp', 'corporation', 'group',
            'industries', 'industry', 'industrial', 'for', 'the', 'and', 'of', 'gmbh', 'sae', 'laboratories', 'laboratory', 'labs', 'chemical',
            'chemicals', 'biochemical', 'biochemistry', 'biotech', 'international', 'egypt', 'china', 'india', 'plc', 'llc', 'spa', 'srl',
            'pvt', 'private', 'factory', 'works', 'شركة', 'للصناعات', 'الدوائية', 'للأدوية', 'للادوية', 'مصنع'}


def org_key(name):
    """The words that tell a company apart: «Tianjin Tianyao Pharmaceutical Co., Ltd» → [tianjin, tianyao]; «Badr Pharma» → [badr].
    An address after the name is not the name: «Medis S.A., Nabeul, Tunisia» → [medis] (the first comma, «-» or bracket ends it)."""
    def key(s):
        return [w for w in re.findall(r'[a-z\u0600-\u06ff]{3,}', (s or '').lower()) if w not in ORG_STOP][:2]
    head = re.split(r'[,،;(]|\s[-–—]\s', name or '', maxsplit=1)[0]
    return key(head) or key(name)


def names_org(text, name):
    """Does the text name this company (every word that tells it apart)?"""
    key = org_key(name)
    low = (text or '').lower()
    return bool(key) and all(re.search(r'(?<![a-z\u0600-\u06ff])' + re.escape(w) + r'(?![a-z\u0600-\u06ff])', low) for w in key)


def gmp_whose(text, fpp, makers):
    """A GMP certificate is the finished product's manufacturer's ('fpp') or an active substance's ('api'), by the company it names;
    None when it names both or neither — then nothing is placed on a guess."""
    top = (text or '')[:6000]
    fpp_hit = names_org(top, fpp)
    api_hit = any(names_org(top, m) for m in makers if m and org_key(m) != org_key(fpp))
    return 'fpp' if fpp_hit and not api_hit else 'api' if api_hit and not fpp_hit else None


def names_product(text, product):
    """Does the document say, at its top or in a «Product name» field, that it is about the product itself (its trade name)?"""
    word = (re.findall(r'[a-z\u0600-\u06ff]{4,}', (product or '').lower()) or [None])[0]
    if not word or not text:
        return False
    low = text.lower()
    rx = r'(?<![a-z])' + re.escape(word) + r'(?![a-z])'
    if re.search(rx, _head(low, lines=14, chars=1400)):
        return True
    return bool(re.search(r'(?:product\s*name|name\s*of\s*(?:the\s*)?product|trade\s*name|اسم\s*المستحضر|الاسم\s*التجاري)[^\n]{0,40}' + rx, low))


def from_authority(text):
    """An authority's own letter (its name at the top), not a company's or a laboratory's document."""
    top = (text or '')[:1500].lower()
    return any(p in top for p in ('egyptian drug authority', 'هيئة الدواء المصرية', 'ministry of health', 'وزارة الصحة', 'decision letter'))


def kind_homes(kind, pack=None, text=None, product=None, substances=(), fpp=None, makers=()):
    """The items a document of this kind belongs in, the likeliest first. Egypt's table above names its own items; another
    authority's items say it themselves (`kinds` in the requirement). With a pack: only items that pack has. With the document's
    text: a certificate of analysis or a specification that names the product at its top is the finished product's own
    (3.2.P.5.4, 3.2.P.5.1) and not an active substance's; a stability document under an authority's letterhead is the approval,
    any other is the study."""
    homes = list(KIND_HOME.get(kind, []))
    if text is not None:
        first = None
        if kind in ('coa', 'spec') and names_product(text, product):
            first = {'coa': ['P-11'], 'spec': ['P-09']}[kind]
        elif kind == 'stability' and not from_authority(text):       # the company's or a supplier's study: the substance's own when its title names a substance and not the product
            head = _head(text.lower(), lines=14, chars=1400)
            api_first = not names_product(text, product) and any(s and re.search(r'(?<![a-z])' + re.escape(s.lower()) + r'(?![a-z])', head) for s in substances)
            first = ['S-14', 'P-16'] if api_first else ['P-16', 'S-14']
        elif kind == 'gmp' and (fpp or makers):                     # whose certificate: the company it names
            first = {'api': ['M1-38', 'M1-37'], 'fpp': ['M1-37', 'M1-38']}.get(gmp_whose(text, fpp, makers))
        elif kind == 'refstd' and names_product(text, product):
            first = ['P-14', 'S-12']
        if first:
            homes = [h for h in first if h in homes] + [h for h in homes if h not in first]
        if pack is not None:                                         # the section a document prints in its heading decides among the kind's items
            from .classify import _ctd_tokens, _norm
            from .resolver import number
            nums = _ctd_tokens(_norm(text)[:400])
            printed = [h for h in homes if h in pack.by_id and ({number(pack.by_id[h]).split(' ')[0].lower()} |
                                                                {x.lower() for x in (pack.by_id[h].get('ectd') or {}).get('nodes') or []}) & nums]
            if printed:
                homes = printed + [h for h in homes if h not in printed]
    if pack is None:
        return homes
    own = [r['id'] for r in pack.requirements if kind in (r.get('kinds') or ())]             # the authority's own item first, as Egypt's table has it
    return own + [h for h in homes if h in pack.by_id and h not in own]


def kind_check(req_id, filename, data_or_text, known_kind=None, pack=None):
    """Is this file the document the item expects? → {'kind', 'ok', 'homes', 'unread'}. The file is judged by what is written inside
    it, never by its name: its text layer, or — a file with no text — the kind an earlier reading gave it (`known_kind`). Unknown kinds and kinds without a fixed home pass; a recognised kind whose home items
    do not include the target fails (a stability approval in the pricing slot). `unread`: nothing could be read, so nothing was judged."""
    if isinstance(data_or_text, str):
        text = data_or_text
    else:
        text = read_text(filename, data_or_text, max_pages=2)['text']
    kind = content_kind(text)
    if kind == 'other' and known_kind in KIND_HOME:
        kind = known_kind                                   # the file says nothing itself: an earlier reading of it does
    homes = kind_homes(kind, pack, text)
    family = {h for k in TECHNICAL for h in kind_homes(k, pack)} if kind in TECHNICAL else set()
    return {'kind': kind, 'homes': homes, 'ok': kind == 'other' or not homes or req_id in homes or req_id in family, 'kind_name': KIND_NAMES.get(kind),
            'unread': kind == 'other' and len(re.sub(r'\s', '', text)) < 20}


def found_fields(reading):
    """What one document's reading yielded, as short keys the page can name: product.name, apis×2, registration.number …"""
    out = []
    for sec in ('product', 'profile', 'envelope', 'registration'):
        for k, v in (reading.get(sec) or {}).items():
            if v not in (None, '', []):
                out.append(f'{sec}.{k}')
    for sec in ('apis', 'batches', 'specs', 'results', 'composition'):
        n = len(reading.get(sec) or [])
        if n:
            out.append(f'{sec}×{n}')
    d = reading.get('document') or {}
    for k in ('number', 'issuer', 'issued', 'valid_until'):
        if d.get(k):
            out.append(f'document.{k}')
    return out


def read_texts(files):
    """Like read_files, for texts already read (the page sends back what the engine read, to merge again without reading the files
    again): files = [{filename, text, pages?, scanned?, file?}]."""
    items, texts = [], []
    for f in files:
        name, text = f.get('filename') or 'document', f.get('text') or ''
        kind = content_kind(text)
        items.append(fields_for(kind, name, text))
        texts.append({'filename': name, 'kind': kind, 'kind_hint': name_hint(name) if kind == 'other' else None, 'pages': int(f.get('pages') or 0), 'scanned': bool(f.get('scanned')),
                      'ocr': bool(f.get('ocr')), 'file': f.get('file') or ('pdf' if name.lower().endswith('.pdf') else 'other'), 'arabic': arabic.has_arabic(text),
                      'chars': len(re.sub(r'\s', '', text)), 'text': text[:TEXT_BACK], 'found': found_fields(items[-1])})
    return {'files': texts, 'rules': merge(items)}


def ai_prompt(texts, target='dossier'):
    """The instruction the AI layer reads, in the browser (sample) or through the API: the schema + the document texts.
    Images, when a document is scanned, are described by the caller. Output must be one JSON object."""
    import json
    want = {k: SCHEMA[k] for k in (('documents',) if target == 'document' else SCHEMA.keys())}
    head = ('You are a regulatory affairs assistant for the Egyptian Drug Authority (EDA). Read the company documents below '
            '(certificates, licences, EDA letters such as the registration notification «إخطار تسجيل», CoAs, specifications, application '
            'forms, leaflets) and extract the facts needed to register a pharmaceutical product. Documents are often in Arabic: read '
            'Arabic labels (اسم المستحضر، المادة الفعالة، الشكل الصيدلي، الشركة المنتجة، صاحب الترخيص، رقم الإخطار، التاريخ، ساري حتى، '
            'سعر الجمهور، العبوة، مدة الصلاحية) and Arabic-Indic digits. Reply '
            'with ONLY one JSON object with exactly these keys (omit a key or value you cannot find; never guess; copy numbers and names '
            'exactly as printed, keep Arabic names in Arabic and add the Latin name when printed; dates as YYYY-MM-DD; INN in English). '
            'EDA forms are label:value tables. In the Final Registration License, «Active Ingredient(s) & Strength(s)» lists one active substance per line '
            'after «Each 1g contains:» — return one apis entry per substance with its strength; «Manufacturer Of active substance» lists each substance '
            'name followed by its manufacturer and country on the next line (two names may share one manufacturer) — pair them; the Arabic notes may '
            'name other approved or not-permitted suppliers — put approved ones in alternatives; «License Holder» is the applicant; «Manufacturer» is '
            'the finished-product manufacturer; «Invalidation Date» is valid_until; «Type of License: Toll» is licence_type toll; «Price» lines give '
            'one price per pack. In a CADC Notification Letter, return the batch with its expiry and conformity. In a pricing letter the «Each 1g contains» '
            'line separates substances with «+».:\n'
            + json.dumps(want, ensure_ascii=False, indent=1)
            + '\nAlso add "sources": {"<key>": "<filename>"} naming the document each top-level section came from.\n\nDOCUMENTS:\n')
    body = ''
    for i, f in enumerate(texts, 1):
        note = (', SCANNED — read by OCR: check names, numbers and dates against the page' if f.get('ocr') else ', SCANNED — no text layer') if f.get('scanned') else ''
        body += f"\n=== Document {i}: {f['filename']} (kind guess: {f['kind']}, {f['pages']} pages{note}) ===\n"
        body += (f.get('text') or '(no text layer)')[:14000] + '\n'
    return head + body
