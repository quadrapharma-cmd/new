"""PDF technical checks. Each finding: rule, severity (block / warn), message
(en/ar), action, source. A PDF without text blocks whatever the document is:
NP.CAPP.065 v5 general note 4 wants every submitted document a scanned and
searchable PDF (the eCTD draft's list of scans accepted without OCR is not in
force). The program does no OCR; the text layer is made when scanning."""
import os, re
from dataclasses import dataclass, field

LOCKED = {'third_party_certificate', 'eda_document', 'executed_record', 'signed_scan'}
NAME_OK = re.compile(r'^[a-z0-9][a-z0-9-]*\.pdf$')
NO_TEXT_EN = ('No text: the pages are images only. EDA requires every document as a searchable PDF (NP.CAPP.065 v5, general note 4). '
              'Make the text layer when scanning — the scanner\'s software, Acrobat, or a phone app that saves searchable PDFs — and upload it again.')
NO_TEXT_AR = ('الملف ده من غير نص: صفحاته صور بس. الهيئة طالبة كل مستند PDF قابل للبحث (NP.CAPP.065 v5، الملاحظة 4). '
              'اعمل النص وقت المسح — من برنامج السكانر أو Acrobat أو تطبيق موبايل بيحفظ PDF قابل للبحث — وارفعه تاني.')
NO_TEXT_IMAGE_EN = ('An image, not a document. EDA requires every document as a searchable PDF (NP.CAPP.065 v5, general note 4): scan it, '
                    'or photograph it with an app that saves searchable PDFs, and upload the PDF.')
NO_TEXT_IMAGE_AR = ('ده صورة مش مستند. الهيئة طالبة كل مستند PDF قابل للبحث (NP.CAPP.065 v5، الملاحظة 4): امسحه بالسكانر، '
                    'أو صوّره بتطبيق بيحفظ PDF قابل للبحث، وارفع الـ PDF.')


ECTD_DRAFT = {'EG-PF-15.4', 'ICH-NAME', 'EG-PF-16.3', 'EG-BP-E23', 'PDF-JS', 'EG-PF-16.1', 'EG-BP-16.BP1', 'NTA065-BM', 'ECTD-WORD'}
# the draft eCTD guidance's rules (EDA eCTD technical guidance v1.0/2026, not in force) and ICH's: they decide eCTD readiness, not
# whether a document conforms for the One Submission in force (NP.CAPP.065 v5 asks a searchable PDF that opens)


@dataclass
class Finding:
    rule: str
    severity: str        # block | warn
    en: str
    ar: str
    action: str          # auto_fix | rebuild | re_obtain | user_fix | move | none
    source: str
    extra: dict = field(default_factory=dict)      # e.g. the item a misfiled document belongs to
    scope: str = 'all'   # 'ectd': an eCTD-readiness finding — it stops only an eCTD export

    def __post_init__(self):
        if self.rule in ECTD_DRAFT:
            self.scope = 'ectd'

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class Report:
    path: str
    findings: list = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def status(self):
        """Conformity for the submission in force: eCTD-readiness findings do not count here."""
        return status_of(self.findings)


def status_of(findings):
    """findings: Finding objects or their dicts. eCTD-readiness ones (scope 'ectd') leave the status alone."""
    own = [f for f in findings if (f.get('scope') if isinstance(f, dict) else f.scope) != 'ectd'
           and (f.get('rule') if isinstance(f, dict) else f.rule) not in ECTD_DRAFT]
    if any((f.get('severity') if isinstance(f, dict) else f.severity) == 'block' for f in own):
        return 'non_conforming'
    return 'needs_attention' if own else 'conforming'


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
        add(Finding('EG-PF-15.4', 'warn', f'File name has {len(name)} characters; an eCTD name has at most 64 — the export gives the file its eCTD name.',
                    f'اسم الملف {len(name)} حرف؛ اسم الـ eCTD بالكتير 64 — التصدير بيدّي الملف اسمه في الـ eCTD.', 'none', 'EG eCTD TG draft p.12 l.275'))
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
            signed = b'/ByteRange' in open(path, 'rb').read()
            add(Finding('EG-PF-16.1', 'warn' if signed else 'block',
                        f'PDF version {eff[0]}.{eff[1]} — eCTD takes 1.4 to 1.7 (EDA eCTD technical guidance, draft).'
                        + (' Digitally signed: the version line is left as it is, changing it would break the signature.' if signed else ''),
                        f'إصدار PDF {eff[0]}.{eff[1]} — الـ eCTD بياخد من 1.4 لـ 1.7 (مسودة الهيئة).'
                        + (' الملف موقّع رقميًا: رقم الإصدار متساب زي ما هو، تغييره يبوّظ التوقيع.' if signed else ''),
                        'none' if signed else 'auto_fix', 'EG eCTD technical guidance v1.0/2026 (DRAFT, not in force); EU VC 16.1'))
        elif eff > (1, 7):
            add(Finding('EG-BP-16.BP1', 'warn', f'PDF version {eff[0]}.{eff[1]}; eCTD prefers 1.4–1.7 (EDA eCTD technical guidance, draft).',
                        f'إصدار PDF {eff[0]}.{eff[1]}؛ الـ eCTD بيفضّل 1.4–1.7 (مسودة الهيئة).', 'none', 'EG eCTD technical guidance v1.0/2026 (DRAFT)'))
        try:
            has_outline = bool(rd.outline)
        except Exception:
            has_outline = False
        r.info['bookmarks'] = has_outline
        if pages >= 10 and not has_outline:
            add(Finding('NTA065-BM', 'warn', f'{pages} pages and no bookmarks; long documents need bookmarks to navigate.',
                        f'{pages} صفحة من غير bookmarks؛ المستندات الطويلة لازم يبقى فيها bookmarks.',
                        'auto_fix', 'EG eCTD TG draft (bookmarks for documents with a TOC); ICH eCTD SPEC App. 7'))
        chars = 0                                        # the same measure as the upload gate: some text in the first 12 pages
        for pg in rd.pages[:min(pages, 12)]:
            try:
                chars += len(re.sub(r'\s', '', pg.extract_text() or ''))
            except Exception:
                pass
            if chars >= 20:
                break
        r.info['searchable'] = chars >= 20
        if pages and chars < 20:
            add(Finding('NTA065-N4', 'block', NO_TEXT_EN, NO_TEXT_AR,
                        'rebuild' if doc_class in ('generated', 'company_letter') else 'user_fix', 'NP.CAPP.065 v5 general note 4'))
    except Exception as e:  # pypdf could not parse
        add(Finding('EG-PF-16.5', 'block', f'The PDF cannot be read ({type(e).__name__}).', 'الملف مش بيتقري (تالف).',
                    're_obtain' if doc_class in LOCKED else 'user_fix', 'EU VC 16.5'))
    return r
