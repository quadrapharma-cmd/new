"""PDF technical checks. Each finding: rule, severity (block / warn), message
(en/ar), action, source. Severity can depend on the document class, e.g. a scan
without OCR is accepted for third-party certificates (EU/EG exception list) but
blocks for company documents (NP.CAPP.065 general note 4: «searchable PDF»)."""
import os, re
from dataclasses import dataclass, field

LOCKED = {'third_party_certificate', 'eda_document', 'executed_record', 'signed_scan'}
SCAN_OK = {'third_party_certificate', 'eda_document', 'executed_record', 'signed_scan'}
NAME_OK = re.compile(r'^[a-z0-9][a-z0-9-]*\.pdf$')


@dataclass
class Finding:
    rule: str
    severity: str        # block | warn
    en: str
    ar: str
    action: str          # auto_fix | rebuild | re_obtain | user_fix | none
    source: str

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class Report:
    path: str
    findings: list = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def status(self):
        if any(f.severity == 'block' for f in self.findings):
            return 'non_conforming'
        return 'needs_attention' if self.findings else 'conforming'


def check(path, doc_class='company_technical', ectd_name=False):
    r = Report(path)
    add = r.findings.append
    name = os.path.basename(path)
    size = os.path.getsize(path) if os.path.exists(path) else -1
    if size <= 0:
        add(Finding('EG-PF-16.5', 'block', 'The file is empty (0 bytes).', 'الملف فاضي (0 بايت).',
                    're_obtain' if doc_class in LOCKED else 'user_fix', 'EU VC 16.5 via EG provisional profile'))
        return r
    if len(name) > 64:
        add(Finding('EG-PF-15.4', 'block', f'File name has {len(name)} characters (max 64).',
                    f'اسم الملف {len(name)} حرف (الحد 64).', 'auto_fix', 'EG eCTD TG draft p.12 l.275'))
    if ectd_name and not NAME_OK.match(name):
        add(Finding('ICH-NAME', 'warn', 'eCTD file names use only a-z, 0-9 and "-" (the tool renames on export).',
                    'أسماء ملفات eCTD حروف صغيرة وأرقام و"-" فقط (الأداة بتعيد التسمية عند التصدير).',
                    'auto_fix', 'ICH eCTD SPEC 3.2.2 p.2-3'))
    with open(path, 'rb') as fh:
        head = fh.read(1024)
        fh.seek(max(0, size - 2048))
        tail = fh.read()
    m = re.match(rb'%PDF-(\d)\.(\d)', head)
    if not m:
        add(Finding('EG-PF-16.5', 'block', 'Not a PDF file (no %PDF header).', 'الملف مش PDF.',
                    'user_fix', 'EU VC 16.5'))
        return r
    ver = (int(m[1]), int(m[2]))
    r.info['header_version'] = f'{ver[0]}.{ver[1]}'
    if b'%%EOF' not in tail:
        add(Finding('EG-PF-16.5', 'block', 'The file is truncated or corrupt (no end-of-file marker).',
                    'الملف ناقص أو تالف.', 're_obtain' if doc_class in LOCKED else 'user_fix', 'EU VC 16.5'))
        return r
    try:
        from pypdf import PdfReader
        rd = PdfReader(path, strict=False)
        encrypted = rd.is_encrypted
        if encrypted:
            try:
                ok = rd.decrypt('')
            except Exception:
                ok = 0
            if not ok:
                add(Finding('EG-PF-16.2', 'block', 'The PDF needs a password to open.', 'الملف محتاج باسورد عشان يتفتح.',
                            're_obtain' if doc_class in LOCKED else 'user_fix', 'EG eCTD TG draft; EU VC 16.2'))
                return r
            add(Finding('EG-PF-16.3', 'block', 'The PDF has security restrictions (printing/copying). Remove them; '
                        'digitally signed documents may keep printing and copying allowed only.',
                        'الملف عليه قيود حماية (طباعة/نسخ). لازم تتشال؛ الموقّع رقمياً يسمح بالطباعة والنسخ على الأقل.',
                        're_obtain' if doc_class in LOCKED else 'auto_fix', 'EG eCTD TG draft; EU VC 16.3'))
        pages = len(rd.pages)
        r.info['pages'] = pages
        root = rd.trailer['/Root']
        if '/Collection' in root:
            add(Finding('EG-BP-E23', 'block', 'PDF Portfolio is not allowed; submit each document as its own PDF.',
                        'ملفات الـ Portfolio ممنوعة؛ كل مستند PDF لوحده.', 'user_fix', 'EG eCTD TG draft (EG-BP-E23)'))
        names = root.get('/Names') or {}
        if '/JavaScript' in names or ('/OpenAction' in root and '/JS' in str(root['/OpenAction'])):
            add(Finding('PDF-JS', 'block', 'The PDF contains JavaScript.', 'الملف فيه JavaScript.',
                        're_obtain' if doc_class in LOCKED else 'auto_fix', 'ICH eCTD SPEC App. 7 (no active content)'))
        cat_ver = root.get('/Version')
        eff = ver
        if cat_ver:
            mv = re.match(r'/?(\d)\.(\d)', str(cat_ver))
            if mv:
                eff = max(ver, (int(mv[1]), int(mv[2])))
        r.info['version'] = f'{eff[0]}.{eff[1]}'
        if eff < (1, 4):
            add(Finding('EG-PF-16.1', 'block', f'PDF version {eff[0]}.{eff[1]} — EDA requires 1.4 to 1.7.',
                        f'إصدار PDF {eff[0]}.{eff[1]} — المطلوب من 1.4 لـ 1.7.',
                        'auto_fix', 'EG eCTD TG draft; EU VC 16.1'))
        elif eff > (1, 7):
            add(Finding('EG-BP-16.BP1', 'warn', f'PDF version {eff[0]}.{eff[1]}; 1.4–1.7 recommended.',
                        f'إصدار PDF {eff[0]}.{eff[1]}؛ المفضل 1.4–1.7.', 'auto_fix', 'EG eCTD TG draft (BP1)'))
        try:
            has_outline = bool(rd.outline)
        except Exception:
            has_outline = False
        r.info['bookmarks'] = has_outline
        if pages >= 10 and not has_outline:
            add(Finding('NTA065-BM', 'warn', f'{pages} pages and no bookmarks; long documents need bookmarks to navigate.',
                        f'{pages} صفحة من غير bookmarks؛ المستندات الطويلة لازم يبقى فيها bookmarks.',
                        'auto_fix', 'EG eCTD TG draft (bookmarks for documents with a TOC); ICH eCTD SPEC App. 7'))
        text_pages = 0
        for pg in rd.pages[:min(pages, 5)]:
            try:
                if (pg.extract_text() or '').strip():
                    text_pages += 1
            except Exception:
                pass
        r.info['text_pages_sampled'] = text_pages
        if pages and text_pages == 0:
            if doc_class in SCAN_OK:
                add(Finding('EG-BP-E23', 'warn', 'Scanned without a text layer. Accepted for this document type; '
                            'an OCR layer can be added without changing the page image.',
                            'مسكان من غير طبقة نص. مقبول للنوع ده؛ ممكن نضيف طبقة OCR من غير ما نغيّر صورة الصفحة.',
                            'auto_fix', 'NP.CAPP.065 general note 4; EU/EG scan exception list'))
            else:
                add(Finding('NTA065-N4', 'block', 'Not text-searchable. EDA requires searchable PDFs; '
                            'rebuild from the source or add OCR.',
                            'الملف مش قابل للبحث. الهيئة طالبة PDF قابل للبحث؛ اعمله من المصدر أو ضيف OCR.',
                            'rebuild' if doc_class in ('generated', 'company_letter') else 'auto_fix',
                            'NP.CAPP.065 v5 general note 4'))
    except Exception as e:  # pypdf could not parse
        add(Finding('EG-PF-16.5', 'block', f'The PDF cannot be read ({type(e).__name__}).', 'الملف مش بيتقري (تالف).',
                    're_obtain' if doc_class in LOCKED else 'user_fix', 'EU VC 16.5'))
    return r
