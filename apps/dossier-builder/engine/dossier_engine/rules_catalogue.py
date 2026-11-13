"""The catalogue of every rule the program checks (updates list, item 20): each with its source, the source's version and its status —
«in force» (the authority's rule today), «draft» (a draft guidance, e.g. the EDA eCTD technical guidance v1.0/2026), or «policy»
(the program's own practice, said as such) — and where it runs (upload, cross-document, eCTD validator). The official sources are
listed with their SHA-256 and the day they were taken (docs/ctd/sources/MANIFEST.json, written by tools/sources_manifest.py), so a
report can say which text a rule came from. A report never says «conforming» without saying against which rules."""
import csv, json
from pathlib import Path
from .checks.pdf import ECTD_DRAFT

REPO = Path(__file__).resolve().parents[4]
SOURCES = REPO / 'docs' / 'ctd' / 'sources' / 'MANIFEST.json'
PROFILES = {'ectd32': REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v0',
            'ectd32_eu': REPO / 'docs' / 'ctd' / 'ectd' / 'EU-M1-3.1.1-PROFILE'}

# the checks at upload and across the dossier: id → (en, ar, source, status, stage)
UPLOAD = {
    'NTA065-N4': ('A searchable PDF: its own text layer, made when it was scanned.', 'PDF قابل للبحث: عليه طبقة نص من وقت المسح.', 'NP.CAPP.065 v5, general note 4', 'in_force', 'upload'),
    'EG-PF-16.5': ('The PDF opens: not damaged, not password-protected for opening.', 'الـ PDF بيفتح: مش بايظ ومش عليه كلمة سر للفتح.', 'EU VC 16.5 via the EG provisional profile; NP.CAPP.065 v5 general note 4', 'in_force', 'upload'),
    'DOCX-DRAFT': ('A Word, Excel, PowerPoint or text file is a source: the dossier takes its PDF.', 'ملف Word أو Excel أو PowerPoint أو نص ده مصدر: الملف بياخد الـ PDF بتاعه.', 'NP.CAPP.065 v5, general note 4', 'in_force', 'upload'),
    'ECTD-WORD': ('The proposed leaflet is asked in Word (1.1.9); an eCTD takes its PDF.', 'النشرة المقترحة مطلوبة Word (1.1.9)؛ والـ eCTD بياخد الـ PDF بتاعها.', 'NP.CAPP.065 v5 1.1.9; EG eCTD TG draft', 'in_force', 'upload'),
    'DOC-KIND': ('The document is the one the item asks for, judged by what is written in it (never by the file name).', 'المستند هو اللي البند طالبه، من اللي مكتوب فيه (مش من اسم الملف).', 'NP.CAPP.065 v5 (the item\'s content)', 'policy', 'upload'),
    'DOC-EXPIRED': ('Valid on the day of submission (the date read from the document).', 'ساري يوم التقديم (التاريخ المقروء من المستند).', 'NP.CAPP.065 v5 (valid certificates); eda.doc-validity.v1', 'in_force', 'upload'),
    'DOC-EXPIRED-RENEWAL': ('An expired pricing certificate with its request for updating: accepted.', 'شهادة تسعير منتهية ومعاها طلب التحديث: مقبولة.', 'NP.CAPP.065 v5 1.1.5', 'in_force', 'upload'),
    'DOC-EXPIRING': ('Ends within 90 days: start the renewal.', 'هينتهي خلال 90 يوم: ابدأ التجديد.', 'eda.doc-validity.v1 (the program\'s reminder)', 'policy', 'upload'),
    'COA-DATA': ('The API certificate of analysis shows its batch, manufacture and expiry (or retest) dates.', 'شهادة تحليل المادة الفعالة فيها التشغيلة وتاريخ التصنيع والانتهاء (أو إعادة التحليل).', 'NP.CAPP.065 v5 1.2.3.1', 'in_force', 'upload'),
    'XC-DUP': ('The same file in two items: for an imported product, not in two modules.', 'نفس الملف في بندين: للمستورد مش في موديولين.', 'NP.CAPP.065 v5, general note 3', 'in_force', 'cross'),
    'EG-PF-16.2': ('No security settings (eCTD readiness).', 'من غير إعدادات أمان (جاهزية eCTD).', 'EG eCTD TG draft; EU VC 16.2', 'draft', 'upload'),
    'EG-PF-16.3': ('No PDF Portfolio or attachments (eCTD readiness).', 'من غير Portfolio أو مرفقات (جاهزية eCTD).', 'EG eCTD TG draft; EU VC 16.3', 'draft', 'upload'),
    'EG-BP-E23': ('PDF version 1.4–1.7 or PDF/A (eCTD readiness).', 'إصدار PDF من 1.4 لـ 1.7 أو PDF/A (جاهزية eCTD).', 'EG eCTD TG draft (EG-BP-E23)', 'draft', 'upload'),
    'PDF-JS': ('No JavaScript or active content (eCTD readiness).', 'من غير JavaScript أو محتوى نشط (جاهزية eCTD).', 'ICH eCTD SPEC App. 7 (no active content)', 'draft', 'upload'),
    'EG-PF-16.1': ('The file is a PDF the eCTD accepts (eCTD readiness).', 'الملف PDF الـ eCTD بيقبله (جاهزية eCTD).', 'EG eCTD TG draft; EU VC 16.1', 'draft', 'upload'),
    'EG-BP-16.BP1': ('Fonts embedded (eCTD readiness).', 'الخطوط مدمجة (جاهزية eCTD).', 'EG eCTD TG draft; EU VC 16.BP1', 'draft', 'upload'),
    'NTA065-BM': ('Bookmarks for a long document with a table of contents (eCTD readiness).', 'Bookmarks للمستند الطويل اللي له فهرس (جاهزية eCTD).', 'EG eCTD TG draft; ICH eCTD SPEC App. 7', 'draft', 'upload'),
    'EG-PF-15.4': ('A file name of at most 64 characters — the export gives each file its eCTD name.', 'اسم الملف 64 حرف بالكتير — التصدير بيدّي كل ملف اسمه في الـ eCTD.', 'EG eCTD TG draft p.12 l.275', 'draft', 'upload'),
    'ICH-NAME': ('ICH file naming — the export gives each file its eCTD name.', 'أسماء الملفات حسب ICH — التصدير بيدّي كل ملف اسمه.', 'ICH eCTD SPEC 3.2.2 p.2-3', 'draft', 'upload'),
}
CROSS_SOURCE = {'XC': ('Consistency across the dossier (WHO QOS-PD; NP.CAPP.040)', 'in_force'), 'NP040': ('NP.CAPP.040 v1 (common deficiencies of the quality module)', 'in_force')}


def _profile_rules(output):
    root = PROFILES[output]
    if not (root / 'validation-criteria.csv').exists():
        return []
    if output == 'ectd32':
        from .validators import ectd32 as v
        auto, not_run = set(v.RULES), {}
    else:
        from .validators import ectd32_eu as v
        auto, not_run = set(v.RULES) | set(v.SAME), dict(v.NOT_RUN)
    out = []
    for r in csv.DictReader(open(root / 'validation-criteria.csv', encoding='utf-8')):
        rid = r.get('rule_id')
        if not rid:
            continue
        run = 'automated' if rid in auto else 'not_run'
        out.append({'id': rid, 'en': r.get('rule_text') or '', 'ar': r.get('rule_text') or '', 'source': r.get('source') or '',
                    'status': 'draft' if output == 'ectd32' else 'in_force', 'stage': output, 'run': run,
                    'why_not': not_run.get(rid) or (None if run == 'automated' else 'needs a person or an earlier sequence to judge')})
    return out


def sources():
    """The official texts behind the rules, with their SHA-256 and the day they were taken (when the manifest exists)."""
    try:
        return json.loads(SOURCES.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []


def catalogue():
    """{rules: [...], counts: {stage: {status: n}}, sources: [...]} — every rule with its source, status and stage."""
    rules = [{'id': k, 'en': v[0], 'ar': v[1], 'source': v[2], 'status': v[3], 'stage': v[4], 'run': 'automated',
              'scope': 'ectd' if k in ECTD_DRAFT else 'all'} for k, v in UPLOAD.items()]
    from . import crosschecks
    import inspect, re
    for rid in sorted(set(re.findall(r"XFinding\('([A-Z0-9-]+)'", inspect.getsource(crosschecks)))):
        src, status = CROSS_SOURCE['NP040' if rid.startswith('NP040') else 'XC']
        rules.append({'id': rid, 'en': f'Cross-document check {rid}', 'ar': f'فحص عبر المستندات {rid}', 'source': src, 'status': status,
                      'stage': 'cross', 'run': 'automated', 'scope': 'all'})
    for out in ('ectd32', 'ectd32_eu'):
        rules += _profile_rules(out)
    counts = {}
    for r in rules:
        c = counts.setdefault(r['stage'], {})
        c[r['status']] = c.get(r['status'], 0) + 1
        if r.get('run') == 'not_run':
            c['not_run'] = c.get('not_run', 0) + 1
    return {'rules': rules, 'counts': counts, 'sources': sources()}

