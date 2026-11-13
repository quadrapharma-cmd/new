"""PDF technical checks. Each finding: rule, severity (block / warn), message
(en/ar), action, source. A PDF without text blocks whatever the document is:
NP.CAPP.065 v5 general note 4 wants every submitted document a scanned and
searchable PDF (the eCTD draft's list of scans accepted without OCR is not in
force). Where PdfCraft reads scans (OCR, Arabic and English) the fix «make
searchable» adds the text layer under the page image; elsewhere the text layer
is made when scanning."""
import os, re
from dataclasses import dataclass, field
from pathlib import Path

LOCKED = {'third_party_certificate', 'eda_document', 'executed_record', 'signed_scan'}
NAME_OK = re.compile(r'^[a-z0-9][a-z0-9-]*\.pdf$')
NO_TEXT_EN = ('No text: the pages are images only. EDA requires every document as a searchable PDF (NP.CAPP.065 v5, general note 4). '
              'The desktop and company editions read it (OCR, Arabic and English) and make it searchable themselves (PdfCraft); here, make the '
              'text layer when scanning — the scanner\'s software, Acrobat, or a phone app that saves searchable PDFs.')
NO_TEXT_AR = ('الملف ده من غير نص: صفحاته صور بس. الهيئة طالبة كل مستند PDF قابل للبحث (NP.CAPP.065 v5، الملاحظة 4). '
              'نسخة الكمبيوتر ونسخة الشركة بيقروه (OCR عربي وإنجليزي) ويخلّوه قابل للبحث لوحدهم (PdfCraft)؛ هنا اعمل النص وقت المسح — '
              'من برنامج السكانر أو Acrobat أو تطبيق موبايل بيحفظ PDF قابل للبحث.')
OCR_FIX_EN = ('No text layer: the pages are images. EDA requires every document as a searchable PDF (NP.CAPP.065 v5, general note 4). '
              'PdfCraft reads the pages (OCR, Arabic and English) and adds their text under the image — the page looks the same, and the '
              'document becomes searchable: «Fix» does it.')
OCR_FIX_AR = ('الملف ده مالوش طبقة نص: صفحاته صور. الهيئة طالبة كل مستند PDF قابل للبحث (NP.CAPP.065 v5، الملاحظة 4). '
              'PdfCraft بيقرا الصفحات (OCR عربي وإنجليزي) ويحط نصها تحت الصورة — شكل الصفحة ما بيتغيرش والمستند بيبقى قابل للبحث: «صلّح» بيعملها.')
NO_TEXT_IMAGE_EN = ('An image, not a PDF. EDA requires every document as a searchable PDF (NP.CAPP.065 v5, general note 4). The desktop and '
                    'company editions turn a PNG, JPEG, TIFF, GIF or BMP into a searchable PDF themselves (PdfCraft); here, scan it as a PDF, '
                    'or save the photo as JPEG or PNG, and upload it again.')
NO_TEXT_IMAGE_AR = ('ده صورة مش PDF. الهيئة طالبة كل مستند PDF قابل للبحث (NP.CAPP.065 v5، الملاحظة 4). نسخة الكمبيوتر ونسخة الشركة '
                    'بيحوّلوا صورة PNG أو JPEG أو TIFF أو GIF أو BMP لـ PDF قابل للبحث لوحدهم (PdfCraft)؛ هنا امسحه PDF، أو احفظ الصورة JPEG أو PNG وارفعها تاني.')


ECTD_DRAFT = {'EG-PF-15.4', 'ICH-NAME', 'EG-PF-16.3', 'EG-BP-E23', 'PDF-JS', 'EG-PF-16.1', 'EG-BP-16.BP1', 'NTA065-BM', 'ECTD-WORD',
              'PDF-FONTS', 'PDF-VIEW', 'PDF-ZOOM', 'PDF-INFO', 'PDF-ATTACH', 'PDF-ANNOT', 'PDF-SIZE'}
FMT = 'ICH M2 eCTD file formats v1.3 §2.1 (no JavaScript, attachments or annotations)'
SIZE_LIMIT = 100 * 1000 * 1000                         # ICH eCTD specification App. 7: 100 MB a file
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


BASE14 = {'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic', 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique',
          'Helvetica-BoldOblique', 'Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique', 'Symbol', 'ZapfDingbats'}


def fonts_state(rd, max_pages=50):
    """'embedded' | 'not_embedded' | 'unknown' — every font of the first pages carries its font file, one does not, or it could not
    be told (an unusual font dictionary). The 14 standard PDF fonts (Times, Helvetica, Courier, Symbol, ZapfDingbats) every reader
    has need no embedding."""
    seen_any, missing = False, []
    try:
        for pg in rd.pages[:max_pages]:
            res = pg.get('/Resources')
            fonts = res.get_object().get('/Font') if res is not None else None
            if fonts is None:
                continue
            for _, ref in fonts.get_object().items():
                f = ref.get_object()
                seen_any = True
                desc = f.get('/FontDescriptor')
                if desc is None and f.get('/DescendantFonts') is not None:
                    desc = f['/DescendantFonts'].get_object()[0].get_object().get('/FontDescriptor')
                if f.get('/Subtype') == '/Type3':
                    continue                              # drawn with the page's own glyph procedures: nothing to embed
                base = str(f.get('/BaseFont', '?')).lstrip('/').split('+')[-1]
                if base.split(',')[0] in BASE14:
                    continue
                if desc is None or not any(k in desc.get_object() for k in ('/FontFile', '/FontFile2', '/FontFile3')):
                    missing.append(base)
    except Exception:
        return 'unknown', []
    return ('not_embedded' if missing else 'embedded') if seen_any else 'embedded', sorted(set(missing))[:8]


def _fixed_zoom(rd, max_pages=200):
    """Links or bookmarks that set their own zoom (/XYZ with a zoom) instead of keeping the reader's."""
    def fixed(dest):
        try:
            d = dest.get_object() if hasattr(dest, 'get_object') else dest
            if isinstance(d, dict):
                d = d.get('/D') or d.get('/Dest')
            if isinstance(d, list) and len(d) >= 5 and str(d[1]) == '/XYZ':
                z = d[4]
                return z is not None and str(z) not in ('null', '0', 'None') and float(z) != 0
        except Exception:
            return False
        return False
    n = 0
    try:
        for pg in rd.pages[:max_pages]:
            for a in (pg.get('/Annots') or []):
                a = a.get_object()
                if a.get('/Subtype') == '/Link':
                    act = a.get('/A')
                    dest = a.get('/Dest') or (act.get_object().get('/D') if act is not None else None)
                    n += bool(dest is not None and fixed(dest))
    except Exception:
        pass
    return n


def props(rd, r, add, has_outline, doc_class='company_technical'):
    """The PDF properties an eCTD looks at (ICH eCTD Specification, Appendix 7; EU eCTD guidance): all eCTD readiness."""
    src = 'ICH eCTD SPEC App. 7 (PDF properties); EU harmonised eCTD guidance'
    state, missing = fonts_state(rd)
    r.info['fonts'] = state
    try:
        r.info['fast_web_view'] = b'/Linearized' in open(r.path, 'rb').read(2048)   # said, not fixed: linearising needs a tool this program does not carry
    except OSError:
        pass
    if state == 'not_embedded':
        add(Finding('PDF-FONTS', 'warn', f"Fonts not embedded: {', '.join(missing)}. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).",
                    f"خطوط مش مدمجة: {', '.join(missing)}. اعمل الـ PDF تاني والخطوط كلها مدمجة (ما ينفعش يتعمل من غير ما الصفحات تترسم تاني).", 'user_fix', src))
    elif state == 'unknown':
        add(Finding('PDF-FONTS', 'warn', 'Whether the fonts are embedded could not be told from this file.', 'مش قادرين نعرف من الملف ده إذا كانت الخطوط مدمجة.', 'none', src))
    try:
        mode = str(rd.trailer['/Root'].get('/PageMode') or '')
    except Exception:
        mode = ''
    if has_outline and mode != '/UseOutlines':
        add(Finding('PDF-VIEW', 'warn', 'It has bookmarks but does not open with the bookmarks panel.', 'فيه bookmarks بس مش بيفتح ولوحة الـ bookmarks ظاهرة.', 'auto_fix', src))
    z = _fixed_zoom(rd)
    r.info['fixed_zoom_links'] = z
    if z:
        add(Finding('PDF-ZOOM', 'warn', f'{z} link(s) set their own zoom; links keep the reader\'s zoom («inherit zoom»).',
                    f'{z} رابط بيغيّر الزووم؛ الروابط المفروض تسيب زووم القارئ («inherit zoom»).', 'auto_fix', src))
    try:
        info = rd.metadata or {}
        title = str(info.get('/Title') or '').strip()
    except Exception:
        title = ''
    r.info['title'] = title
    if not title and doc_class not in LOCKED:            # the company's own documents: offered (another's are as their issuer made them)
        add(Finding('PDF-INFO', 'warn', 'The document has no title in its properties (File → Properties).', 'المستند مالوش عنوان في خصائصه (File ← Properties).', 'auto_fix',
                    src + '; EU VC 8.2 16.BP11 (1.3.1, centralised procedure)'))


def check(path, doc_class='company_technical', ectd_name=False):
    r = Report(path)
    add = r.findings.append
    name = os.path.basename(path)
    size = os.path.getsize(path) if os.path.exists(path) else -1
    if size <= 0:
        add(Finding('EG-PF-16.5', 'block', 'The file is empty (0 bytes).', 'الملف فاضي (0 بايت).',
                    're_obtain' if doc_class in LOCKED else 'user_fix', 'EU VC 16.5 via EG provisional profile'))
        return r
    if size > SIZE_LIMIT:
        add(Finding('PDF-SIZE', 'warn', f'{size / 1e6:.0f} MB; an eCTD file is at most 100 MB (ICH) — PdfCraft can make it smaller (images above 225 ppi brought to 150 ppi), or split it.',
                    f'{size / 1e6:.0f} ميجا؛ ملف الـ eCTD بالكتير 100 ميجا (ICH) — PdfCraft ممكن يصغّره (الصور اللي فوق 225 نقطة/بوصة تبقى 150)، أو قسّمه.',
                    'user_fix' if doc_class in LOCKED else 'auto_fix', 'ICH eCTD specification App. 7 (100 MB a file); ICH M2 file formats v1.3 §2.3 (500 MB)'))
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
    from .. import pdfcraft
    q = pdfcraft.inspect(Path(path).read_bytes()) if pdfcraft.available() else None
    if q is not None:                                    # PdfCraft reads the file: its checks (a damaged file it repairs is said so)
        r.info['engine'] = 'pdfcraft'
        _pdfcraft_checks(r, add, path, q, ver, doc_class)
        return r
    r.info['engine'] = 'pypdf'
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
        props(rd, r, add, has_outline, doc_class)
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


def _pdfcraft_checks(r, add, path, q, ver, doc_class):
    """The checks on what PdfCraft read (pdfcraft.inspect): the same rules as the pypdf reading, and what only PdfCraft sees — a damaged
    file it repaired, faux redactions, attachments and comments (ICH M2 file formats §2.1), signatures that no longer match."""
    locked = doc_class in LOCKED
    info, opened = q.get('doc_info') or {}, q.get('_open') or {}
    pages = int(q.get('pages') or opened.get('pages') or 0)
    r.info['pages'] = pages
    repairs = list(info.get('repairs') or [])
    if repairs or info.get('unreadable_objects'):
        r.info['repairs'] = repairs[:6]
        add(Finding('PDF-REPAIR', 'warn', f"The file is damaged ({'; '.join(repairs[:2]) or 'objects that cannot be read'}). PdfCraft reads it; "
                    'a clean copy can be written — the pages are compared with the original to look the same.',
                    'الملف فيه تلف. PdfCraft قادر يقراه؛ ممكن نكتب منه نسخة سليمة — وبنقارن الصفحات بالأصل عشان نتأكد إن شكلها ما اتغيّرش.',
                    'auto_fix', 'EU VC 16.5 (a PDF that opens); PdfCraft tolerant reading'))
    sec = info.get('security') or {}
    if sec.get('protected'):
        add(Finding('EG-PF-16.3', 'block', 'The PDF has security restrictions (printing/copying). Remove them; '
                    'digitally signed documents may keep printing and copying allowed only.',
                    'الملف عليه قيود حماية (طباعة/نسخ). لازم تتشال؛ الموقّع رقمياً يسمح بالطباعة والنسخ على الأقل.',
                    're_obtain' if locked else 'auto_fix', 'EG eCTD TG draft; EU VC 16.3'))
    if info.get('portfolio'):
        add(Finding('EG-BP-E23', 'block', 'PDF Portfolio is not allowed; submit each document as its own PDF.',
                    'ملفات الـ Portfolio ممنوعة؛ كل مستند PDF لوحده.', 'user_fix', 'EG eCTD TG draft (EG-BP-E23)'))
    scripts = (q.get('js_document_scripts') or {}).get('scripts') or []
    if info.get('has_javascript') or scripts:
        add(Finding('PDF-JS', 'block', 'The PDF contains JavaScript.', 'الملف فيه JavaScript.',
                    're_obtain' if locked else 'auto_fix', 'ICH eCTD SPEC App. 7 (no active content); ' + FMT))
    sigs = q.get('sign_list') or {}
    r.info['signatures'] = int(sigs.get('count') or 0)
    signed = r.info['signatures'] > 0 or b'/ByteRange' in Path(path).read_bytes()
    for sg in (sigs.get('signatures') or []):
        if sg.get('status') == 'invalid':
            who = sg.get('signer') or sg.get('name') or ''
            add(Finding('PDF-SIG', 'warn', f'A digital signature no longer matches the document — it changed after signing{": " + str(who) if who else ""}. Ask the signer for the signed copy.',
                        f'توقيع رقمي مابقاش مطابق للمستند — المستند اتغيّر بعد التوقيع{": " + str(who) if who else ""}. اطلب النسخة الموقّعة من صاحب التوقيع.',
                        're_obtain' if locked else 'user_fix', 'PdfCraft signature validation (PAdES)'))
            break
    try:
        iv = tuple(int(x) for x in str(info.get('pdf_version') or '').split('.')[:2])
    except ValueError:
        iv = ()
    eff = max(ver, iv) if len(iv) == 2 else ver
    r.info['version'] = f'{eff[0]}.{eff[1]}'
    if eff < (1, 4):
        add(Finding('EG-PF-16.1', 'warn' if signed else 'block',
                    f'PDF version {eff[0]}.{eff[1]} — eCTD takes 1.4 to 1.7 (EDA eCTD technical guidance, draft).'
                    + (' Digitally signed: the version line is left as it is, changing it would break the signature.' if signed else ''),
                    f'إصدار PDF {eff[0]}.{eff[1]} — الـ eCTD بياخد من 1.4 لـ 1.7 (مسودة الهيئة).'
                    + (' الملف موقّع رقميًا: رقم الإصدار متساب زي ما هو، تغييره يبوّظ التوقيع.' if signed else ''),
                    'none' if signed else 'auto_fix', 'EG eCTD technical guidance v1.0/2026 (DRAFT, not in force); EU VC 16.1'))
    elif eff > (1, 7):
        add(Finding('EG-BP-16.BP1', 'warn', f'PDF version {eff[0]}.{eff[1]}; eCTD prefers 1.4–1.7 (EDA eCTD technical guidance, draft).',
                    f'إصدار PDF {eff[0]}.{eff[1]}؛ الـ eCTD بيفضّل 1.4–1.7 (مسودة الهيئة).', 'none', 'EG eCTD technical guidance v1.0/2026 (DRAFT)'))
    has_outline = bool(info.get('outline'))
    r.info['bookmarks'] = has_outline
    src = 'ICH eCTD SPEC App. 7 (PDF properties); EU harmonised eCTD guidance'
    missing = []
    for f in info.get('fonts') or []:
        name = str(f.get('name') or '?').split('+')[-1]
        if f.get('embedded') or f.get('kind') == 'Type3' or name.split(',')[0] in BASE14 or 'standard 14' in str(f.get('substitution') or ''):
            continue
        missing.append(name)
    r.info['fonts'] = 'not_embedded' if missing else 'embedded'
    if missing:
        add(Finding('PDF-FONTS', 'warn', f"Fonts not embedded: {', '.join(sorted(set(missing))[:8])}. Make the PDF again with all fonts embedded (it cannot be done without redrawing the pages).",
                    f"خطوط مش مدمجة: {', '.join(sorted(set(missing))[:8])}. اعمل الـ PDF تاني والخطوط كلها مدمجة (ما ينفعش يتعمل من غير ما الصفحات تترسم تاني).", 'user_fix', src))
    nav = ((q.get('doc_initial_view') or {}).get('initial_view') or {}).get('navigation')
    if has_outline and nav != 'Bookmarks':
        add(Finding('PDF-VIEW', 'warn', 'It has bookmarks but does not open with the bookmarks panel.', 'فيه bookmarks بس مش بيفتح ولوحة الـ bookmarks ظاهرة.', 'auto_fix', src))
    links = (q.get('link_list') or {}).get('links') or []
    z = sum(1 for k in links if k.get('to_page') and isinstance(k.get('zoom'), (int, float)) and k.get('zoom'))
    r.info['fixed_zoom_links'] = z
    if z:
        add(Finding('PDF-ZOOM', 'warn', f'{z} link(s) set their own zoom; links keep the reader\'s zoom («inherit zoom»).',
                    f'{z} رابط بيغيّر الزووم؛ الروابط المفروض تسيب زووم القارئ («inherit zoom»).', 'auto_fix', src))
    title = str(info.get('title') or '').strip()
    r.info['title'] = title
    if not title and not locked:
        add(Finding('PDF-INFO', 'warn', 'The document has no title in its properties (File → Properties).', 'المستند مالوش عنوان في خصائصه (File ← Properties).', 'auto_fix',
                    src + '; EU VC 8.2 16.BP11 (1.3.1, centralised procedure)'))
    hidden = {c.get('category'): int(c.get('count') or 0) for c in ((q.get('doc_hidden_info') or {}).get('categories') or [])}
    if hidden.get('attachments'):
        n = hidden['attachments']
        add(Finding('PDF-ATTACH', 'warn', f'{n} file(s) attached inside the PDF; eCTD documents carry no attachments.',
                    f'فيه {n} ملف مرفق جوه الـ PDF؛ مستندات الـ eCTD ما يبقاش فيها مرفقات.', 're_obtain' if locked else 'auto_fix', FMT))
    if hidden.get('comments'):
        n = hidden['comments']
        add(Finding('PDF-ANNOT', 'warn', f'{n} comment(s) or mark-up(s) on the pages; eCTD documents carry none (annotated CRFs aside).',
                    f'فيه {n} تعليق أو علامة على الصفحات؛ مستندات الـ eCTD ما يبقاش فيها تعليقات (غير الـ CRF المعلّق عليها).', 're_obtain' if locked else 'auto_fix', FMT))
    faux = (q.get('doc_audit_redactions') or {}).get('findings') or []
    if faux:
        f0 = faux[0]
        seen = str(f0.get('covered_text') or '')[:60]
        r.info['faux_redactions'] = [{'page': f.get('page'), 'rect': f.get('rect'), 'kind': f.get('kind')} for f in faux[:50]]
        add(Finding('PDF-REDACT', 'warn', f'Faux redaction: {len(faux)} dark box(es) cover text that can still be read and copied (page {f0.get("page")}: «{seen}»). '
                    'A real redaction removes the text under the boxes for good.',
                    f'إخفاء مزيّف: {len(faux)} مستطيل غامق فوق نص لسه بيتقري وبيتنسخ (صفحة {f0.get("page")}: «{seen}»). الإخفاء الحقيقي بيشيل النص اللي تحت المستطيل نهائي.',
                    're_obtain' if locked else 'auto_fix', 'PdfCraft redaction audit (opaque boxes painted over extractable text)'))
    if pages >= 10 and not has_outline:
        add(Finding('NTA065-BM', 'warn', f'{pages} pages and no bookmarks; long documents need bookmarks to navigate.',
                    f'{pages} صفحة من غير bookmarks؛ المستندات الطويلة لازم يبقى فيها bookmarks.',
                    'auto_fix', 'EG eCTD TG draft (bookmarks for documents with a TOC); ICH eCTD SPEC App. 7'))
    chars = len(re.sub(r'\s', '', ''.join(q.get('texts') or [])))
    r.info['searchable'] = chars >= 20
    if pages and chars < 20:
        from .. import pdfcraft
        if pdfcraft.ocr_info():                          # PdfCraft reads the scan and adds its text layer: a fix, on every kind of document
            add(Finding('NTA065-N4', 'block', OCR_FIX_EN, OCR_FIX_AR, 'auto_fix', 'NP.CAPP.065 v5 general note 4; PdfCraft OCR'))
        else:
            add(Finding('NTA065-N4', 'block', NO_TEXT_EN, NO_TEXT_AR,
                        'rebuild' if doc_class in ('generated', 'company_letter') else 'user_fix', 'NP.CAPP.065 v5 general note 4'))
