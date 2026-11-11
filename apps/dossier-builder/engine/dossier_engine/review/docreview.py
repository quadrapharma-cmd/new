"""Review of ONE document per the rules, and the record of it.

The rubric of a document = the review pack's questions that point at its CTD item (by requirement id, slot id or CTD number,
filtered by the dossier's profile) + general document rules by document class (text layer, product named, signed and dated,
validity, issuer). `run_rules` answers what keywords can answer; the Assistant answers the rest by reading the document and
records its findings with `record`. Every review is kept (doc_review table) with its origin: rules | assistant | reviewer."""
import json
import re
import time

from . import evidence, pack as packmod, storage as rstorage
from .. import expr

SCHEMA = '''
create table if not exists doc_review(id text primary key, dossier_id text not null, doc_id text not null, created real not null, actor text,
  origin text not null, summary text, verdict text, counts text not null default '{}', findings text not null default '[]');
create index if not exists doc_review_doc on doc_review(doc_id, created);
'''
COMPANY = {'company_technical', 'company_letter', 'generated', 'executed_record'}
THIRD = {'third_party_certificate', 'eda_document'}
VERDICTS = {'adequate', 'deficient', 'not_assessable', 'not_applicable'}
SEVERITIES = {'critical', 'major', 'minor', 'note'}
DATE_RX = re.compile(r'\b(\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d\d|(?:19|20)\d\d-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(?:19|20)\d\d)\b', re.I)


def _bi(en, ar):
    return {'en': en, 'ar': ar}


GENERIC = [
    {'id': 'DOC-TEXT', 'classes': None, 'severity': 'major', 'title': _bi('Searchable text', 'نص قابل للبحث'),
     'question': _bi('Does the document carry a text layer (not an image-only scan)?', 'هل المستند يحمل طبقة نص (ليس صورة ممسوحة فقط)؟'),
     'deficiency': _bi('The document is an image-only scan: add an OCR text layer (Fix) or obtain a text copy.', 'المستند صورة ممسوحة بلا نص: أضف طبقة OCR (إصلاح) أو احصل على نسخة نصية.'),
     'source': 'NP.CAPP.065 v5 general notes (PDF)'},
    {'id': 'DOC-NAME', 'classes': None, 'severity': 'minor', 'title': _bi('Product named', 'اسم المنتج مذكور'),
     'question': _bi('Does the document name the product (trade name) it belongs to?', 'هل يذكر المستند اسم المنتج التجاري الذي يخصه؟'),
     'deficiency': _bi('The document does not name the product; add the product name as registered.', 'المستند لا يذكر اسم المنتج؛ أضف الاسم التجاري كما هو مسجل.'),
     'source': 'dossier consistency'},
    {'id': 'DOC-SIGN', 'classes': COMPANY, 'severity': 'minor', 'title': _bi('Signed', 'موقَّع'),
     'question': _bi('Is the company document signed by a named, titled person?', 'هل مستند الشركة موقَّع من شخص مسمّى بصفته؟'),
     'keywords': ['signature', 'signed by', 'signed', 'name:', 'title:', 'توقيع', 'التوقيع', 'الاسم:'],
     'deficiency': _bi('No signature block: add the signatory\'s name, title, signature and stamp.', 'لا يوجد توقيع: أضف اسم الموقّع وصفته وتوقيعه وختم الشركة.'),
     'source': 'NP.CAPP.065 v5 (company documents)'},
    {'id': 'DOC-DATE', 'classes': COMPANY, 'severity': 'minor', 'title': _bi('Dated', 'مؤرَّخ'),
     'question': _bi('Does the document carry a date?', 'هل يحمل المستند تاريخًا؟'),
     'deficiency': _bi('No date found: date the document.', 'لا يوجد تاريخ: أرِّخ المستند.'), 'source': 'NP.CAPP.065 v5 (company documents)'},
    {'id': 'DOC-VALID', 'classes': THIRD, 'severity': 'major', 'title': _bi('Validity', 'الصلاحية'),
     'question': _bi('Is the certificate/licence within its validity on the day of submission?', 'هل الشهادة/الترخيص ساري الصلاحية يوم التقديم؟'),
     'deficiency': _bi('The document has expired or its validity is unknown: record the expiry date or obtain a valid copy.', 'المستند منتهي أو صلاحيته غير معروفة: سجّل تاريخ الانتهاء أو احصل على نسخة سارية.'),
     'source': 'NP.CAPP.065 v5 (validity of certificates)'},
    {'id': 'DOC-ISSUER', 'classes': THIRD, 'severity': 'minor', 'title': _bi('Issuer identified', 'الجهة المصدِرة محددة'),
     'question': _bi('Is the issuing authority or body clearly identified?', 'هل الجهة المصدِرة محددة بوضوح؟'),
     'keywords': ['authority', 'ministry', 'edqm', 'certificate', 'issued by', 'هيئة', 'وزارة', 'صادر'],
     'deficiency': _bi('The issuer is not identifiable: obtain a copy on the issuer\'s letterhead with its seal.', 'الجهة المصدِرة غير واضحة: احصل على نسخة على ورق الجهة بختمها.'),
     'source': 'WHO CPP scheme / NP.CAPP.065 v5'},
]


def ensure(st):
    st.db.executescript(SCHEMA)


def _slot_of(st, did, doc):
    board = st.board(did)
    s = next((x for x in board['slots'] if x['slot_id'] == doc.get('slot_id')), None)
    return s, board


def _env(st, did):
    from .run import _profile
    env = _profile(st.dossier(did)).env()
    env.update({'reliance': False, 'strictness': 'international'})
    return env


def rubric(st, did, doc_id, pack=None):
    """The rules one document must satisfy, with their sources."""
    pack = pack or packmod.load()
    doc = st.document(doc_id)
    if doc['dossier_id'] != did:
        raise KeyError('document')
    s, board = _slot_of(st, did, doc)
    env = _env(st, did)
    rules = []
    if s:
        want = {s['req_id'], s['slot_id']}
        for q in pack.questions:
            slots = (q.get('evidence') or {}).get('slots') or []
            if not (want & set(slots) or q['ctd'] == s['ctd']):
                continue
            try:
                if not expr.evaluate(q.get('applies', 'true'), env):
                    continue
            except expr.ExprError:
                continue
            rules.append({'id': q['id'], 'kind': 'pack', 'dept': q['dept'], 'severity': q['severity'], 'title': q['title'], 'question': q['question'],
                          'deficiency': q['deficiency'], 'adequate': q.get('adequate'), 'keywords': (q.get('evidence') or {}).get('keywords') or [],
                          'source': q.get('source'), 'auto': (q.get('auto') or {}).get('kind', 'none')})
    cls = doc.get('doc_class') or (s or {}).get('doc_class')
    for g in GENERIC:
        if g['classes'] is None or cls in g['classes']:
            rules.append({'id': g['id'], 'kind': 'generic', 'dept': 'document', 'severity': g['severity'], 'title': g['title'], 'question': g['question'],
                          'deficiency': g['deficiency'], 'keywords': g.get('keywords') or [], 'source': {'code': g['source']}, 'auto': 'text'})
    d = st.dossier(did)
    return {'document': {'id': doc['id'], 'filename': doc['filename'], 'title': doc.get('title'), 'doc_class': cls, 'slot_id': doc.get('slot_id'), 'version': doc.get('version'),
                         'valid_until': doc['meta'].get('valid_until'), 'generated': doc['meta'].get('generated'), 'is_docx': doc['filename'].lower().endswith(('.docx', '.doc')),
                         'third_party': cls in THIRD},
            'slot': s and {k: s.get(k) for k in ('slot_id', 'req_id', 'ctd', 'title', 'doc_class', 'level', 'acceptance', 'sources', 'how')},
            'product': d.get('product'), 'rules': rules}


def _norm_finding(f, rules_by_id):
    r = rules_by_id.get(f.get('rule')) or {}
    verdict = f.get('verdict') if f.get('verdict') in VERDICTS else 'not_assessable'
    sev = f.get('severity') if f.get('severity') in SEVERITIES else r.get('severity', 'minor')
    where = [{'page': w.get('page'), 'excerpt': str(w.get('excerpt', ''))[:300]} for w in (f.get('where') or []) if isinstance(w, dict)]
    def bi(v, default):
        if isinstance(v, dict):
            return {'en': str(v.get('en') or v.get('ar') or ''), 'ar': str(v.get('ar') or v.get('en') or '')}
        if isinstance(v, str) and v:
            return {'en': v, 'ar': v}
        return default
    return {'rule': f.get('rule') or 'NOTE', 'title': r.get('title') or bi(f.get('title'), _bi(f.get('rule') or 'Note', f.get('rule') or 'ملاحظة')), 'severity': sev,
            'verdict': verdict, 'where': where, 'finding': bi(f.get('finding'), _bi('', '')), 'change': bi(f.get('change'), _bi('', '')),
            'source': (r.get('source') or {}).get('code') if isinstance(r.get('source'), dict) else r.get('source') or f.get('source')}


def _verdict(findings):
    if any(f['verdict'] == 'deficient' for f in findings):
        return 'deficient'
    if any(f['verdict'] == 'not_assessable' for f in findings):
        return 'partly_assessed'
    return 'adequate' if findings else 'no_rules'


def _save(st, did, doc_id, findings, summary, actor, origin):
    rid = rstorage.new_id('DR')
    counts = {}
    for f in findings:
        counts[f['verdict']] = counts.get(f['verdict'], 0) + 1
    verdict = _verdict(findings)
    st.db.execute('insert into doc_review(id, dossier_id, doc_id, created, actor, origin, summary, verdict, counts, findings) values (?,?,?,?,?,?,?,?,?,?)',
                  (rid, did, doc_id, time.time(), actor, origin, summary, verdict, json.dumps(counts), json.dumps(findings, ensure_ascii=False)))
    st.db.commit()
    st.audit(did, 'document.reviewed', doc=doc_id, review=rid, origin=origin, verdict=verdict, counts=counts)
    return get(st, rid)


def get(st, rid):
    r = st.db.execute('select * from doc_review where id=?', (rid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d['counts'], d['findings'] = json.loads(d['counts'] or '{}'), json.loads(d['findings'] or '[]')
    return d


def latest(st, doc_id):
    r = st.db.execute('select id from doc_review where doc_id=? order by created desc limit 1', (doc_id,)).fetchone()
    return get(st, r['id']) if r else None


def history(st, doc_id):
    return [get(st, r['id']) for r in st.db.execute('select id from doc_review where doc_id=? order by created desc', (doc_id,)).fetchall()]


def run_rules(st, did, doc_id, pack=None, actor='rules'):
    """What the keywords and the record can decide; everything else is left for the Assistant / the reviewer."""
    rb = rubric(st, did, doc_id, pack)
    doc = st.document(doc_id)
    dt = evidence.DocText(st)
    pages = dt.pages(doc)
    scanned = doc['filename'].lower().endswith('.pdf') and evidence.is_scanned(pages)
    text = ' '.join(t for _, t in pages)
    product = ((rb.get('product') or {}).get('name') or '').strip()
    today = st.today()
    out = []
    for r in rb['rules']:
        f = {'rule': r['id'], 'severity': r['severity']}
        if r['id'] == 'DOC-TEXT':
            f['verdict'] = 'deficient' if scanned else 'adequate'
            f['finding'] = _bi('Image-only scan, no text layer.', 'صورة ممسوحة بلا طبقة نص.') if scanned else _bi('Text layer present.', 'طبقة النص موجودة.')
        elif r['id'] == 'DOC-VALID':
            vu = doc['meta'].get('valid_until')
            if not vu:
                f.update(verdict='not_assessable', finding=_bi('No validity date recorded for this document.', 'لا يوجد تاريخ صلاحية مسجَّل لهذا المستند.'))
            elif vu < today:
                f.update(verdict='deficient', finding=_bi(f'Expired on {vu}.', f'انتهت صلاحيته في {vu}.'))
            else:
                f.update(verdict='adequate', finding=_bi(f'Valid until {vu}.', f'ساري حتى {vu}.'))
        elif scanned:
            f.update(verdict='not_assessable', finding=_bi('Image-only scan: the text cannot be checked by the rules; the Assistant reads the pages.', 'صورة ممسوحة: لا تستطيع القواعد فحص النص؛ المساعد يقرأ الصفحات.'))
        elif r['id'] == 'DOC-NAME':
            hit = bool(product) and product.lower() in text.lower()
            f.update(verdict='adequate' if hit else ('not_assessable' if not product else 'deficient'),
                     finding=_bi(f'Product «{product}» named.', f'اسم المنتج «{product}» مذكور.') if hit else _bi(f'Product «{product}» not found in the text.', f'اسم المنتج «{product}» غير موجود في النص.'))
            if hit:
                f['where'] = evidence.find(pages, [product])
        elif r['id'] == 'DOC-DATE':
            m = DATE_RX.search(text)
            f.update(verdict='adequate' if m else 'deficient', finding=_bi(f'Date found: {m.group(0)}', f'تاريخ موجود: {m.group(0)}') if m else _bi('No date found.', 'لا يوجد تاريخ.'))
        elif r.get('keywords') and r.get('auto') in ('text', 'slot'):
            hits = evidence.find(pages, r['keywords'])
            f.update(verdict='adequate' if hits else 'deficient', where=hits, finding=_bi('Required wording found.', 'الصياغة المطلوبة موجودة.') if hits else
                     _bi('Required wording not found: ' + ' / '.join(f'«{k}»' for k in r['keywords'][:3]), 'الصياغة المطلوبة غير موجودة: ' + ' / '.join(f'«{k}»' for k in r['keywords'][:3])))
        else:
            f.update(verdict='not_assessable', finding=_bi('Needs reading and judgement (the Assistant or the reviewer).', 'يحتاج قراءة وحكمًا (المساعد أو المراجع).'))
        if f['verdict'] == 'deficient':
            f['change'] = r['deficiency']
        out.append(f)
    rules_by_id = {r['id']: r for r in rb['rules']}
    findings = [_norm_finding(f, rules_by_id) for f in out]
    summary = f"{len(findings)} rules: " + ', '.join(f"{k} {v}" for k, v in sorted(_counts(findings).items()))
    return _save(st, did, doc_id, findings, summary, actor, 'rules')


def _counts(findings):
    c = {}
    for f in findings:
        c[f['verdict']] = c.get(f['verdict'], 0) + 1
    return c


def record(st, did, doc_id, findings, summary=None, actor='claude', origin='assistant', pack=None):
    """The Assistant's (or the reviewer's) reading of the document against the rubric."""
    rb = rubric(st, did, doc_id, pack)
    rules_by_id = {r['id']: r for r in rb['rules']}
    norm = [_norm_finding(f, rules_by_id) for f in (findings or []) if isinstance(f, dict)]
    if not norm:
        raise ValueError('no findings')
    return _save(st, did, doc_id, norm, summary or f"{len(norm)} findings", actor, origin)


def memos_for(st, did, doc_id):
    out = []
    for d in st.documents(did):
        if d['meta'].get('memo_for') == doc_id:
            out.append({'id': d['id'], 'filename': d['filename'], 'title': d.get('title'), 'created': d.get('created')})
    return out
