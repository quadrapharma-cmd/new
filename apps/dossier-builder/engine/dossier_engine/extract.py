"""«Upload the documents and the forms fill themselves» (intake).

Two layers over the same text. This module's RULES read the PDF text (pypdf) with regular expressions: document
kind, certificate numbers, issuers, dates, the product's names and strength, active substances, manufacturers,
batch numbers, CEP numbers… They work everywhere, with no network. The AI layer (Claude: the `sample`
capability in the browser edition, or the API with a key) reads the same text — or the page images when the
document is a scan — against SCHEMA and returns the same shape. Every value is shown for review before it is
used; nothing is written without the user's confirmation."""
import re
from io import BytesIO
from . import arabic, intake_eda

KINDS = [  # (kind, keywords in lower-case text or file name); first match wins, in this order
    ('cadc', ['notification letter', 'statement of conformity', 'sample identification code', 'qf:cadc', 'شهادة مطابقة']),
    ('cpp', ['certificate of pharmaceutical product', 'who certification scheme', ' cpp']),
    ('cep', ['certificate of suitability', 'r1-cep', 'r0-cep', 'edqm']),
    ('gmp', ['good manufacturing practice', 'gmp certificate', 'certificate of gmp', 'gmp compliance', 'gmp', 'التصنيع الجيد']),
    ('coa', ['certificate of analysis', 'analytical report', ' coa', 'c of a', 'شهادة تحليل', 'شهادة التحليل']),
    ('composition', ['composition certificate', 'unit formula', 'quantitative composition', 'شهادة التركيب', 'التركيب']),
    ('pricing', ['pricing certificate', 'price certificate', 'pricing policies', 'pricing', 'تسعير', 'التسعيرة', 'سعر البيع للجمهور', 'لجنة تسعير', 'سعر بيع الجمهور']),
    ('licence', ['registration licence', 'registration license', 'marketing authori', 'registration notification', 'final registration license', 'final registration licence', 'إخطار التسجيل', 'إخطار تسجيل', 'رخصة التسجيل', 'شهادة تسجيل',
                 'شهادة التسجيل', 'إخطار', 'اخطار', 'ترخيص']),
    ('annex1', ['annex i', 'application form', 'نموذج الطلب']),
    ('smpc', ['summary of product characteristics', 'smpc', 'package leaflet', 'patient information leaflet', 'النشرة']),
    ('factory', ['factory licence', 'factory license', 'manufacturing licence', 'manufacturing license', 'رخصة المصنع']),
    ('bmr', ['batch manufacturing record', 'executed batch', 'batch record']),
    ('stability', ['stability']),
    ('spec', ['specification', 'acceptance criteria']),
    ('loa', ['letter of access', 'drug master file', ' dmf']),
    ('poa', ['power of attorney', 'letter of attorney', 'توكيل']),
    ('commercial', ['commercial register', 'register of trade', 'سجل تجاري']),
    ('contract', ['agreement', 'contract', 'عقد']),
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
                   'issued': 'YYYY-MM-DD', 'valid_until': 'YYYY-MM-DD or null'}],
}
PRIORITY = ['licence', 'annex1', 'cpp', 'smpc', 'composition', 'pricing', 'spec', 'coa', 'cadc', 'cep', 'gmp', 'stability', 'bmr', 'factory', 'other']


def pdf_text(data, max_pages=12):
    """Text of the first pages; `scanned` when no page has text (an image-only PDF)."""
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
    return {'pages': n, 'text': text, 'scanned': n > 0 and len(re.sub(r'\s', '', text)) < 20}


def docx_text(data):
    try:
        import docx
        d = docx.Document(BytesIO(data))
        text = '\n'.join(p.text for p in d.paragraphs)
        for t in d.tables:
            for row in t.rows:
                text += '\n' + ' | '.join(c.text for c in row.cells)
        return text
    except Exception:
        return ''


def read_text(name, data, max_pages=12, ocr=True):
    """What one uploaded file says: a PDF's text layer, or OCR of its pages when it is a scan (tesseract ara+eng, local
    computers only), a DOCX's paragraphs and tables, or OCR of an image. `scanned` = image-only (the AI layer then
    reads the page images), `ocr` = the text came from OCR, `kind_of_file` = pdf | docx | image | other."""
    low = (name or '').lower()
    out = {'pages': 0, 'text': '', 'scanned': False, 'ocr': False, 'kind_of_file': 'other'}
    img = arabic.image_type(data or b'')
    if data[:4] == b'%PDF' or low.endswith('.pdf'):
        pt = pdf_text(data, max_pages)
        out.update(pt, kind_of_file='pdf')
        if pt['scanned'] and ocr:
            txt = arabic.ocr_pdf(data, pages=min(pt['pages'] or 1, 4))
            if len(re.sub(r'\s', '', txt)) >= 20:
                out.update(text=txt, ocr=True)
    elif img:
        out.update(pages=1, scanned=True, kind_of_file='image')
        if ocr:
            txt = arabic.ocr_image_bytes(data, '.' + img.split('/')[-1].replace('jpeg', 'jpg'))
            if len(re.sub(r'\s', '', txt)) >= 20:
                out.update(text=txt, ocr=True)
    elif data[:2] == b'PK' and low.endswith('.docx'):
        out.update(pages=1, text=docx_text(data), kind_of_file='docx')
    else:
        try:
            out.update(data.decode('utf-8'), pages=1) if False else out.update(text=data.decode('utf-8', 'ignore')[:60000], pages=1)
        except Exception:
            pass
    out['text'] = arabic.prepare(out['text'])
    out['arabic'] = arabic.has_arabic(out['text'])
    return out


def guess_kind(filename, text):
    hay = ' ' + (filename or '').lower().replace('_', ' ').replace('-', ' ') + ' ' + (text or '')[:4000].lower()
    for kind, words in KINDS:
        if any(w in hay for w in words):
            return kind
    return 'other'


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


def date_after(text, labels, window=90):
    for lab in labels:
        rx = r'(?<![A-Za-z\u0600-\u06FF])' + (arabic.label_rx(lab) if arabic.has_arabic(lab) else re.escape(lab))
        for m in re.finditer(rx, text, re.I):
            dm = DATE.search(text, m.end(), m.end() + window)
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
        if m and m.group(1).strip(' .,-:'):
            return m.group(1).strip(' .,-:')
        if arabic.has_arabic(lab):
            m = re.search(r'^([^\n]{2,80}?)\s*[:：\-]?\s*' + rx + r'\s*[:：]?\s*$', text[:60000], flags | re.M)
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
    product['dosage_form'] = after(t, ['Dosage form', 'Pharmaceutical form', 'Form', 'الشكل الصيدلي', 'الشكل الدوائي', 'الصورة الصيدلية', 'الشكل الصيدلاني']) \
        or next((f for f in FORMS if f in low), None) or arabic.form_en(t)
    product['dosage_form_en'] = arabic.form_en(product['dosage_form']) if product.get('dosage_form') and arabic.has_arabic(product['dosage_form']) else None
    st = re.search(r'(?<![\d.,])((?:[1-9]\d*(?:[.,]\d+)?|0[.,]\d+)\s?(?:mg|mcg|µg|g|iu|%|ml))\b(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s?)?(?:ml|tablet|capsule|dose|g))?', t, re.I)
    product['strength'] = after(t, ['Strength', 'التركيز', 'العيار', 'القوة']) or (st.group(0).strip() if st else None) or arabic.strength_en(t)
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
    apis = [_clean(x) for x in re.split(r'[,;/]|\band\b', after(t, ['Active ingredient', 'Active ingredients', 'Active substance', 'Active substances',
                                                                     'Active pharmaceutical ingredient', 'INN', 'Generic name', 'Generic Name',
                                                                     'المادة الفعالة', 'المواد الفعالة', 'المكونات الفعالة', 'الاسم العلمي']) or '') if _clean(x)]
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
    if 'toll' in low:
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
    if 'sterile' in low or 'injection' in form:
        specifics.append('sterile')
    if 'powder for injection' in form and 'solvent' in low:
        specifics.append('powder_inj_with_solvent')
    profile['dosage_specifics'] = specifics
    if re.search(r'\b(BP|USP|Ph\.? ?Eur\.?)\b', t):
        profile['pharmacopoeial'] = True
    batches = []
    for m in re.finditer(r'\b(?:batch|lot)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,19})\b', t, re.I):
        no = m.group(1)
        if no.lower() not in ('no', 'number', 'size') and no not in [b['no'] for b in batches]:
            batches.append({'no': no, 'kind': 'api' if kind in ('coa', 'cep') and apis and kind == 'cep' else 'fpp'})
    size = after(t, ['Batch size', 'Lot size'], r'([\d.,]+\s?(?:units|tablets|capsules|kg|g|l|ml|vials|bottles)?)')
    mfg = date_after(t, ['Date of manufacture', 'Manufacturing date', 'Mfg. date', 'Mfg date', 'Date of manufacturing'])
    for b in batches[:1]:
        if size:
            b['size'] = size
        if mfg:
            b['date'] = mfg
    results, specs = [], []
    if kind in ('coa', 'spec', 'stability'):
        for line in t.splitlines():
            ll = line.lower()
            test = next((x for x in TESTS if ll.startswith(x) or f' {x} ' in f' {ll} '), None)
            if not test:
                continue
            nums = re.findall(r'(?<![\w.])(\d+(?:[.,]\d+)?\s?%?)(?![\w.])', line)
            tail = line[ll.index(test) + len(test):].strip(' :\t')
            if kind == 'coa' and nums:
                results.append({'batch': batches[0]['no'] if batches else None, 'test': test.title() if test != 'ph' else 'pH', 'value': nums[-1].strip()})
            elif tail:
                specs.append({'test': test.title() if test != 'ph' else 'pH', 'limit': tail[:60], 'method': None})
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


def _standardise(out):
    """Controlled vocabularies: the dose form → its standard entry (and the route it implies), countries → ISO entries."""
    from . import vocab
    P = out.get('product') or {}
    std = vocab.match_form(P.get('dosage_form_en') or P.get('dosage_form') or '')
    if std:
        P['dosage_form_std'] = std['id']
        P['dosage_form_en'] = P.get('dosage_form_en') or std['en']
        out.setdefault('profile', {})
        if not out['profile'].get('admin_route'):
            out['profile']['admin_route'] = std['route']
    for a in out.get('apis') or []:
        c = vocab.match_country(a.get('country') or '')
        if c:
            a['country'], a['country_code'] = c['en'], c['code']
    c = vocab.match_country(P.get('manufacturer_country') or '')
    if c:
        P['manufacturer_country'], P['manufacturer_country_code'] = c['en'], c['code']


def merge(items):
    """Combine the readings of several documents into one fill (first non-empty value, by document priority)."""
    order = sorted(items, key=lambda it: PRIORITY.index(it['document']['kind']) if it['document']['kind'] in PRIORITY else 99)
    fill = {'product': {}, 'profile': {}, 'envelope': {}, 'registration': {}, 'apis': [], 'batches': [], 'specs': [], 'results': [], 'composition': [], 'documents': []}
    for it in order:
        for sec in ('product', 'profile', 'envelope', 'registration'):
            for k, v in it.get(sec, {}).items():
                if v not in (None, '', []) and not fill[sec].get(k):
                    fill[sec][k] = v
        for a in it.get('apis', []):
            a['name'] = _clean(a.get('name'))
        for a in it.get('apis', []):
            cur = next((x for x in fill['apis'] if x['name'].lower() == a['name'].lower()), None)
            if cur:
                cur.update({k: v for k, v in a.items() if v and not cur.get(k)})
            else:
                fill['apis'].append(dict(a))
        for b in it.get('batches', []):
            if b['no'] not in [x['no'] for x in fill['batches']]:
                fill['batches'].append(b)
        for key in ('specs', 'results', 'composition'):
            for row in it.get(key, []):
                if row not in fill[key]:
                    fill[key].append(row)
        fill['documents'].append(it['document'])
    return fill


def read_files(files):
    """files: [(filename, bytes)] -> per-file readings + the merged fill + the text the AI layer will read."""
    items, texts = [], []
    for name, data in files:
        pt = read_text(name, data)
        kind = guess_kind(name, pt['text'])
        items.append(fields_for(kind, name, pt['text']))
        texts.append({'filename': name, 'kind': kind, 'pages': pt['pages'], 'scanned': pt['scanned'], 'ocr': pt['ocr'], 'file': pt['kind_of_file'],
                      'arabic': pt['arabic'], 'chars': len(re.sub(r'\s', '', pt['text'])), 'text': pt['text'][:14000]})
    return {'files': texts, 'rules': merge(items)}


def read_texts(files):
    """Like read_files, for texts the browser already extracted (its own OCR of scans): files = [{filename, text, pages?, scanned?, ocr?, file?}]."""
    items, texts = [], []
    for f in files:
        name, text = f.get('filename') or 'document', f.get('text') or ''
        kind = guess_kind(name, text)
        items.append(fields_for(kind, name, text))
        texts.append({'filename': name, 'kind': kind, 'pages': int(f.get('pages') or 0), 'scanned': bool(f.get('scanned')), 'ocr': bool(f.get('ocr')),
                      'ocr_where': f.get('ocr_where'), 'file': f.get('file') or ('pdf' if name.lower().endswith('.pdf') else 'other'), 'arabic': arabic.has_arabic(text),
                      'chars': len(re.sub(r'\s', '', text)), 'text': text[:14000]})
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
            'سعر الجمهور، العبوة، مدة الصلاحية) and Arabic-Indic digits; text marked OCR may contain errors, trust the page images. Reply '
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
        body += f"\n=== Document {i}: {f['filename']} (kind guess: {f['kind']}, {f['pages']} pages{', SCANNED — read its page images' if f.get('scanned') else ''}{', text below is OCR' if f.get('ocr') else ''}) ===\n"
        body += (f.get('text') or '(no text layer)')[:14000] + '\n'
    return head + body
