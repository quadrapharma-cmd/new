"""«Upload the documents and the forms fill themselves» (intake).

Two layers over the same text. This module's RULES read the PDF text (pypdf) with regular expressions: document
kind, certificate numbers, issuers, dates, the product's names and strength, active substances, manufacturers,
batch numbers, CEP numbers… They work everywhere, with no network. The AI layer (Claude: the `sample`
capability in the browser edition, or the API with a key) reads the same text — or the page images when the
document is a scan — against SCHEMA and returns the same shape. Every value is shown for review before it is
used; nothing is written without the user's confirmation."""
import re
from io import BytesIO

KINDS = [  # (kind, keywords in lower-case text or file name); first match wins, in this order
    ('cpp', ['certificate of pharmaceutical product', 'who certification scheme', ' cpp']),
    ('cep', ['certificate of suitability', 'r1-cep', 'r0-cep', 'edqm']),
    ('gmp', ['good manufacturing practice', 'gmp certificate', 'certificate of gmp', 'gmp compliance', 'gmp']),
    ('coa', ['certificate of analysis', 'analytical report', ' coa', 'c of a']),
    ('composition', ['composition certificate', 'unit formula', 'quantitative composition', 'شهادة التركيب']),
    ('licence', ['registration licence', 'registration license', 'marketing authori', 'إخطار التسجيل', 'رخصة التسجيل', 'إخطار']),
    ('pricing', ['pricing certificate', 'price certificate', 'pricing', 'تسعير']),
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
DATE = re.compile(r'(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[./\-\s]+([A-Za-z]{3,9}|\d{1,2})[./\-\s,]+(\d{4})')
FORMS = ['film-coated tablet', 'film coated tablet', 'coated tablet', 'effervescent tablet', 'chewable tablet', 'orodispersible tablet',
         'prolonged-release tablet', 'extended release tablet', 'tablet', 'hard capsule', 'soft capsule', 'capsule', 'oral suspension',
         'suspension', 'oral solution', 'syrup', 'solution for injection', 'powder for injection', 'injection', 'infusion', 'cream',
         'ointment', 'gel', 'eye drops', 'ear drops', 'nasal spray', 'inhaler', 'inhalation', 'suppository', 'sachet', 'granules',
         'powder for oral suspension', 'lotion', 'drops', 'spray']
ROUTE = {'oral': ['tablet', 'capsule', 'syrup', 'suspension', 'oral', 'sachet', 'granules', 'drops'], 'parenteral': ['injection', 'infusion'],
         'topical': ['cream', 'ointment', 'gel', 'lotion'], 'ophthalmic': ['eye'], 'inhalation': ['inhal', 'nasal']}
ISSUERS = ['Egyptian Drug Authority', 'EDA', 'EDQM', 'Ministry of Health', 'Ministry of Health and Population', 'MHRA', 'FDA', 'WHO',
           'Central Drugs Standard Control Organization', 'CDSCO', 'ANVISA', 'Saudi Food and Drug Authority', 'SFDA', 'TGA', 'Swissmedic',
           'BfArM', 'AIFA', 'AEMPS', 'ANSM', 'Health Canada', 'HPRA', 'MFDS', 'PMDA', 'Jordan Food and Drug Administration', 'JFDA',
           'General Authority for Investment', 'Commercial Registry', 'Chamber of Commerce', 'هيئة الدواء المصرية', 'وزارة الصحة']
TESTS = ['assay', 'dissolution', 'uniformity of dosage units', 'content uniformity', 'related substances', 'impurities', 'water content',
         'loss on drying', 'hardness', 'friability', 'disintegration', 'identification', 'description', 'appearance', 'ph', 'microbial',
         'residual solvents', 'particle size', 'sterility', 'bacterial endotoxins', 'average weight', 'uniformity of mass', 'viscosity']

SCHEMA = {
    'product': {'name': 'trade name as registered', 'dosage_form': 'pharmaceutical form', 'strength': 'strength per unit, e.g. 500 mg',
                'manufacturer': 'finished-product manufacturer (legal name)', 'manufacturer_address': 'site address as on the GMP certificate',
                'indication': 'main indication, few words'},
    'profile': {'dossier_kind': 'generic | innovator', 'origin': 'local | imported', 'licence': 'own | toll | f_toll | under_licence | imported | imported_bulk',
                'activity': 'new | re_registration', 'admin_route': 'oral | topical | parenteral | ophthalmic | inhalation | other',
                'leaflet': 'english | non_english', 'dosage_specifics': '[coated, capsule_hard, pellets, premix, powder_inj_with_solvent, sterile]',
                'pharmacopoeial': 'true if the product is a pharmacopoeial (BP/USP/Ph. Eur.) product'},
    'apis': [{'name': 'INN of the active substance', 'manufacturer': 'API manufacturer legal name', 'address_gmp': 'API site address',
              'option': 'CEP | DMF | PQ | FULL', 'cep_no': 'e.g. R1-CEP 2010-123-Rev 02', 'cep_status': 'valid | suspended | withdrawn | expired',
              'spec_standard': 'Ph. Eur. | USP | BP | in-house', 'coa_name': 'name on the supplier CoA'}],
    'envelope': {'applicant': 'applicant / MA holder legal name', 'tracking': 'EDA procedure tracking number', 'inn': ['INN list']},
    'batches': [{'no': 'batch number', 'kind': 'fpp | api', 'api': 'API name for API batches', 'size': 'batch size with unit',
                 'scale': 'pilot | production | smaller', 'date': 'YYYY-MM-DD', 'site': 'manufacturing site'}],
    'specs': [{'test': 'test name', 'limit': 'acceptance criterion', 'method': 'method / reference'}],
    'results': [{'batch': 'batch number', 'test': 'test name', 'value': 'numeric result as printed (not «complies»)'}],
    'registration': {'reg_no': 'registration / licence number', 'reg_date': 'YYYY-MM-DD', 'shelf_life': 'e.g. 36 months',
                     'storage': 'storage condition', 'price': 'public price', 'packs': ['pack sizes']},
    'documents': [{'filename': 'as given', 'kind': 'cpp | gmp | cep | coa | composition | licence | pricing | annex1 | smpc | factory | bmr | stability | spec | loa | poa | commercial | contract | other',
                   'title': 'document title', 'number': 'certificate / licence number', 'issuer': 'issuing authority or company',
                   'issued': 'YYYY-MM-DD', 'valid_until': 'YYYY-MM-DD or null'}],
}
PRIORITY = ['licence', 'annex1', 'cpp', 'smpc', 'composition', 'pricing', 'spec', 'coa', 'cep', 'gmp', 'stability', 'bmr', 'factory', 'other']


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
        for m in re.finditer(re.escape(lab), text, re.I):
            dm = DATE.search(text, m.end(), m.end() + window)
            if dm:
                v = iso_date(dm)
                if v:
                    return v
    return None


def after(text, labels, pattern=r'([^\n:]{2,80})', window=120, flags=re.I):
    """The value printed after one of the labels (same line, after an optional colon)."""
    for lab in labels:
        m = re.search(re.escape(lab) + r'\s*[:：\-]?\s*' + pattern, text[:60000], flags)
        if m and m.group(1).strip(' .,-'):
            return m.group(1).strip(' .,-')
    return None


def _clean(s):
    return re.sub(r'\s+', ' ', s or '').strip(' .,;:-')


def fields_for(kind, filename, text):
    """The rules' reading of one document; keys follow SCHEMA, values are strings or lists."""
    t = text or ''
    low = t.lower()
    out = {'document': {'filename': filename, 'kind': kind}}
    doc = out['document']
    doc['number'] = after(t, ['Certificate No', 'Certificate Number', 'Certificate no', 'Cert. No', 'Licence No', 'License No', 'Registration No',
                              'Registration Number', 'Reg. No', 'Approval No', 'Authorisation No', 'رقم الشهادة', 'رقم الترخيص', 'رقم التسجيل'],
                     r'([A-Z0-9][A-Z0-9\-/.]{2,30})', flags=0)
    for name in ISSUERS:
        if name.lower() in low:
            doc['issuer'] = name
            break
    doc['issuer'] = doc.get('issuer') or after(t, ['Issued by', 'Issuing authority', 'Competent authority', 'Certifying authority'])
    doc['issued'] = date_after(t, ['Date of issue', 'Issued on', 'Issue date', 'Date of issuance', 'Dated', 'Date:', 'تاريخ الإصدار'])
    doc['valid_until'] = date_after(t, ['Valid until', 'Valid to', 'Expiry date', 'Expires on', 'Date of expiry', 'Validity', 'Valid through',
                                        'صالح حتى', 'صالحة حتى', 'تاريخ الانتهاء', 'ينتهي'])
    cep = re.search(r'R\d-CEP\s?\d{4}-\d{3}(?:-Rev\s?\d{2})?', t)
    product = {}
    product['name'] = after(t, ['Trade name', 'Brand name', 'Proprietary name', 'Product name', 'Name of the product', 'Name of product',
                                'Invented name', 'الاسم التجاري', 'اسم المستحضر'])
    product['dosage_form'] = after(t, ['Dosage form', 'Pharmaceutical form', 'Form', 'الشكل الصيدلي']) or next((f for f in FORMS if f in low), None)
    st = re.search(r'\b(\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|g|iu|%|ml))(?:\s*/\s*(?:\d+(?:[.,]\d+)?\s?)?(?:ml|tablet|capsule|dose|g))?', t, re.I)
    product['strength'] = after(t, ['Strength', 'التركيز']) or (st.group(0).strip() if st else None)
    product['manufacturer'] = after(t, ['Manufacturer', 'Manufactured by', 'Manufacturing site', 'Name of manufacturer', 'Name and address of the manufacturer',
                                        'Manufacturer name', 'الشركة المصنعة', 'المصنع'])
    product['manufacturer_address'] = after(t, ['Site address', 'Address of manufacturer', 'Manufacturing site address', 'Address', 'العنوان'])
    apis = [_clean(x) for x in re.split(r'[,;/]|\band\b', after(t, ['Active ingredient', 'Active ingredients', 'Active substance', 'Active substances',
                                                                     'Active pharmaceutical ingredient', 'INN', 'Generic name', 'Generic Name',
                                                                     'المادة الفعالة', 'المواد الفعالة']) or '') if _clean(x)]
    if cep and not apis:
        m = re.search(r'for\s+([A-Z][a-z]+(?:\s[a-z]+)?)', t)
        if m:
            apis = [m.group(1)]
    envelope = {'applicant': after(t, ['Applicant', 'Marketing authorisation holder', 'Marketing authorization holder', 'MA holder', 'Licence holder',
                                      'License holder', 'Holder', 'Registrant', 'مقدم الطلب', 'صاحب الترخيص', 'صاحب التسجيل']),
                'tracking': (re.search(r'\bP-[A-Z]{2,5}-\d{3,6}\b', t) or [None])[0] if re.search(r'\bP-[A-Z]{2,5}-\d{3,6}\b', t) else None}
    profile = {}
    if 'toll' in low:
        profile['licence'] = 'toll'
    if 'imported' in low or kind == 'cpp' or 'country of import' in low:
        profile['origin'] = 'imported'
    if 'generic' in low:
        profile['dossier_kind'] = 'generic'
    form = (product.get('dosage_form') or '').lower()
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
                        'storage': after(t, ['Storage', 'Store', 'Storage condition', 'التخزين']), 'price': after(t, ['Price', 'Public price', 'السعر'], r'([\d.,]+\s?(?:EGP|LE|L\.E\.|جنيه)?)')}
    out.update({'product': {k: _clean(v) if isinstance(v, str) else v for k, v in product.items() if v},
                'profile': {k: v for k, v in profile.items() if v not in (None, [], '')},
                'apis': [{'name': a, **({'cep_no': cep.group(0), 'option': 'CEP'} if cep else {})} for a in apis],
                'envelope': {k: _clean(v) for k, v in envelope.items() if v}, 'batches': batches, 'specs': specs, 'results': results,
                'registration': {k: v for k, v in registration.items() if v}})
    return out


def merge(items):
    """Combine the readings of several documents into one fill (first non-empty value, by document priority)."""
    order = sorted(items, key=lambda it: PRIORITY.index(it['document']['kind']) if it['document']['kind'] in PRIORITY else 99)
    fill = {'product': {}, 'profile': {}, 'envelope': {}, 'registration': {}, 'apis': [], 'batches': [], 'specs': [], 'results': [], 'documents': []}
    for it in order:
        for sec in ('product', 'profile', 'envelope', 'registration'):
            for k, v in it.get(sec, {}).items():
                if v not in (None, '', []) and not fill[sec].get(k):
                    fill[sec][k] = v
        for a in it.get('apis', []):
            cur = next((x for x in fill['apis'] if x['name'].lower() == a['name'].lower()), None)
            if cur:
                cur.update({k: v for k, v in a.items() if v and not cur.get(k)})
            else:
                fill['apis'].append(dict(a))
        for b in it.get('batches', []):
            if b['no'] not in [x['no'] for x in fill['batches']]:
                fill['batches'].append(b)
        for key in ('specs', 'results'):
            for row in it.get(key, []):
                if row not in fill[key]:
                    fill[key].append(row)
        fill['documents'].append(it['document'])
    return fill


def read_files(files):
    """files: [(filename, bytes)] -> per-file readings + the merged fill + the text the AI layer will read."""
    items, texts = [], []
    for name, data in files:
        pt = pdf_text(data)
        kind = guess_kind(name, pt['text'])
        items.append(fields_for(kind, name, pt['text']))
        texts.append({'filename': name, 'kind': kind, 'pages': pt['pages'], 'scanned': pt['scanned'], 'text': pt['text'][:14000]})
    return {'files': texts, 'rules': merge(items)}


def ai_prompt(texts, target='dossier'):
    """The instruction the AI layer reads, in the browser (sample) or through the API: the schema + the document texts.
    Images, when a document is scanned, are described by the caller. Output must be one JSON object."""
    import json
    want = {k: SCHEMA[k] for k in (('documents',) if target == 'document' else SCHEMA.keys())}
    head = ('You are a regulatory affairs assistant for the Egyptian Drug Authority (EDA). Read the company documents below '
            '(certificates, licences, CoAs, specifications, application forms, leaflets) and extract the facts needed to register a '
            'pharmaceutical product. Reply with ONLY one JSON object with exactly these keys (omit a key or value you cannot find; never '
            'guess; copy numbers and names exactly as printed; dates as YYYY-MM-DD; INN in English):\n'
            + json.dumps(want, ensure_ascii=False, indent=1)
            + '\nAlso add "sources": {"<key>": "<filename>"} naming the document each top-level section came from.\n\nDOCUMENTS:\n')
    body = ''
    for i, f in enumerate(texts, 1):
        body += f"\n=== Document {i}: {f['filename']} (kind guess: {f['kind']}, {f['pages']} pages{', SCANNED — read its page images' if f.get('scanned') else ''}) ===\n"
        body += (f.get('text') or '(no text layer)')[:14000] + '\n'
    return head + body
