"""Named data checks for questions with auto.kind == data. Each returns (verdict, evidence, detail) where evidence is a
list of {field, value} items shown to the user and detail is a short bilingual note {en, ar}. Nothing is inferred from
missing data: a check that lacks its inputs answers not_assessable and says which data would decide it."""
import re
from datetime import date, timedelta

NON_NUMERIC = re.compile(r'^\s*(conform\w*|complies|pass(es)?|ok|meets|within limits?|يطابق|مطابق)\s*$', re.I)
UNIVERSAL = {'description': ['description', 'appearance', 'الوصف'], 'identification': ['identification', 'identity', 'التعرف'],
             'assay': ['assay', 'content', 'المعايرة'], 'impurities': ['impurit', 'related substance', 'degradation', 'الشوائب']}
EP_WORDS = ('ph. eur', 'ph.eur', 'pheur', 'european pharmacopoeia', 'ep ', 'ph eur')


def _n(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().lower()


def _ev(field, value):
    return {'field': field, 'value': value if isinstance(value, str) else str(value)}


def _d(en, ar):
    return {'en': en, 'ar': ar}


def m1_complete(ctx):
    missing = [s for s in ctx.board['slots'] if s['module'] == 1 and s['level'] == 'R' and s['status'] == 'not_started']
    waiting = [s for s in ctx.board['slots'] if s['module'] == 1 and s['status'] == 'waiting' and not s['documents']]
    ev = [_ev('board.missing_required', ', '.join(s['slot_id'] for s in missing) or 'none'),
          _ev('board.waiting', ', '.join(s['slot_id'] for s in waiting) or 'none')]
    if missing:
        return 'deficient', ev, _d(f"{len(missing)} required Module 1 item(s) have no document: " + ', '.join(f"{s['ctd']} {s['title']['en']}" for s in missing[:8]),
                                   f"{len(missing)} بند(اً) مطلوباً في الوحدة 1 بلا مستند: " + '، '.join(f"{s['ctd']} {s['title']['ar']}" for s in missing[:8]))
    if waiting:
        return 'not_assessable', ev, _d(f"{len(waiting)} item(s) requested from their issuer and not yet received.", f"{len(waiting)} بند(اً) مطلوب من جهته ولم يصل بعد.")
    return 'adequate', ev, _d('Every required Module 1 item has a document.', 'كل بند مطلوب في الوحدة 1 له مستند.')


def pdfs_searchable(ctx):
    bad, total = [], 0
    for s in ctx.board['slots']:
        for d in s['documents']:
            if d['meta'].get('external') or not d['filename'].lower().endswith('.pdf'):
                continue
            total += 1
            if s['doc_class'] not in ('third_party_certificate', 'eda_document', 'executed_record', 'signed_scan') and ctx.text.scanned(d):
                bad.append(f"{s['ctd']} {d['filename']}")
    ev = [_ev('documents.company_pdfs', total), _ev('documents.without_text_layer', ', '.join(bad) or 'none')]
    if not total:
        return 'not_assessable', ev, _d('No PDF documents yet.', 'لا توجد مستندات PDF بعد.')
    if bad:
        return 'deficient', ev, _d(f"{len(bad)} company document(s) have no text layer.", f"{len(bad)} مستند(اً) للشركة بلا طبقة نصية.")
    return 'adequate', ev, _d(f'All {total} company PDFs are searchable (third-party scans are allowed).', f'كل ملفات PDF الخاصة بالشركة ({total}) قابلة للبحث (مسموح بمسح شهادات الغير).')


def certificates_valid(ctx):
    today, soon = ctx.today, ctx.today + timedelta(days=90)
    expired, expiring, dated = [], [], 0
    for s in ctx.board['slots']:
        for d in s['documents']:
            vu = d['meta'].get('valid_until')
            if not vu:
                continue
            dated += 1
            try:
                dt = date.fromisoformat(str(vu)[:10])
            except ValueError:
                continue
            label = f"{s['ctd']} {d['filename']} ({vu})"
            if dt < today:
                expired.append(label)
            elif dt <= soon:
                expiring.append(label)
    ev = [_ev('documents.dated', dated), _ev('documents.expired', ', '.join(expired) or 'none'), _ev('documents.expiring_90d', ', '.join(expiring) or 'none')]
    if not dated:
        return 'not_assessable', ev, _d('No validity dates recorded on the documents (set them on each certificate).', 'لا توجد تواريخ صلاحية مسجلة على المستندات (سجّلها على كل شهادة).')
    if expired:
        return 'deficient', ev, _d(f"{len(expired)} certificate(s) expired.", f"{len(expired)} شهادة منتهية الصلاحية.")
    if expiring:
        return 'deficient', ev, _d(f"{len(expiring)} certificate(s) expire within 90 days.", f"{len(expiring)} شهادة تنتهي خلال 90 يوماً.")
    return 'adequate', ev, _d(f'All {dated} dated certificates are valid.', f'كل الشهادات المؤرخة ({dated}) سارية.')


def cep_valid(ctx):
    ceps = [a for a in ctx.apis if (a.get('option') or '').upper() == 'CEP']
    if not ceps:
        return 'not_assessable', [], _d('No CEP-covered API.', 'لا توجد مادة فعالة مغطاة بشهادة CEP.')
    ev, bad, unknown = [], [], []
    for a in ceps:
        st = (a.get('cep_status') or '').lower()
        ev.append(_ev(f"apis[{a.get('name')}].cep", f"{a.get('cep_no') or '—'} · status: {st or 'not recorded'}"))
        if st in ('suspended', 'withdrawn', 'expired'):
            bad.append(a.get('name'))
        elif st != 'valid':
            unknown.append(a.get('name'))
    if bad:
        return 'deficient', ev, _d(f"CEP not usable for: {', '.join(bad)}.", f"شهادة CEP غير صالحة للاستخدام لـ: {'، '.join(bad)}.")
    if unknown:
        return 'not_assessable', ev, _d('Record the EDQM status of each CEP in the product data; the signed authorisation box is confirmed on the certificate itself.', 'سجّل حالة كل شهادة CEP على EDQM في بيانات المنتج؛ ويُتحقق من توقيع مربع التفويض على الشهادة نفسها.')
    return 'adequate', ev, _d('CEP status valid; confirm the signed authorisation box on the certificate.', 'حالة CEP سارية؛ تأكد من توقيع مربع التفويض على الشهادة.')


def sites_consistent(ctx):
    xc = [f for f in ctx.board.get('cross', []) if f['id'] == 'XC-06']
    ev = [_ev('cross.XC-06', f['en']) for f in xc]
    if xc:
        return 'deficient', ev, _d('Site addresses differ between documents (cross-check XC-06).', 'عناوين المواقع مختلفة بين المستندات (فحص التطابق XC-06).')
    if not any(a.get('address_gmp') for a in ctx.apis):
        return 'not_assessable', [_ev('apis[*].address_gmp', 'not recorded')], _d('Record the site address of each API manufacturer as on its GMP certificate.', 'سجّل عنوان موقع كل مصنّع للمادة الفعالة كما في شهادة GMP.')
    return 'adequate', [_ev('apis[*].address_gmp', '; '.join(a.get('address_gmp', '') for a in ctx.apis))], _d('Site addresses consistent.', 'عناوين المواقع متسقة.')


def cep_route(ctx):
    ceps = [a for a in ctx.apis if (a.get('option') or '').upper() == 'CEP']
    if not ceps:
        return 'not_assessable', [], _d('No CEP-covered API.', 'لا توجد مادة فعالة مغطاة بشهادة CEP.')
    ev, problems = [], []
    batches = ctx.data.get('batches') or []
    for a in ceps:
        std = _n(a.get('spec_standard'))
        ev.append(_ev(f"apis[{a.get('name')}].spec_standard", a.get('spec_standard') or 'not recorded'))
        if std and not any(w in std for w in EP_WORDS):
            problems.append(f"{a.get('name')}: standard «{a.get('spec_standard')}» is not Ph. Eur.")
        n = sum(1 for b in batches if b.get('kind') == 'api' and _n(b.get('api')) in (_n(a.get('name')), _n(f"{a.get('name')}|{a.get('manufacturer')}"), _n(a.get('manufacturer'))))
        ev.append(_ev(f"batches.api[{a.get('name')}]", n))
        if n < 2:
            problems.append(f"{a.get('name')}: {n} API batch analyses (2 required)")
    if problems:
        return 'deficient', ev, _d('; '.join(problems), '؛ '.join(problems))
    return 'adequate', ev, _d('Ph. Eur. declared and two API batches recorded.', 'المرجع دستور الأدوية الأوروبي وتشغيلتان مسجلتان.')


def composition_complete(ctx):
    comp = ctx.data.get('composition') or []
    if not comp:
        return 'not_assessable', [_ev('composition', 'empty')], _d('Enter the composition in the product data.', 'أدخل التركيب في بيانات المنتج.')
    miss = []
    for c in comp:
        gaps = [k for k in ('standard', 'function', 'grade') if not c.get(k)]
        if gaps:
            miss.append(f"{c.get('name')}: {', '.join(gaps)}")
    ev = [_ev('composition.rows', len(comp)), _ev('composition.gaps', '; '.join(miss) or 'none')]
    if miss:
        return 'deficient', ev, _d(f'{len(miss)} ingredient(s) lack standard, function or grade.', f'{len(miss)} مكوِّن(اً) ينقصه المرجع أو الوظيفة أو الدرجة.')
    return 'adequate', ev, _d('Every ingredient has a standard, a function and a grade.', 'لكل مكوِّن مرجع ووظيفة ودرجة.')


def fpp_spec_universal(ctx):
    spec = (ctx.data.get('specs') or {}).get('product') or []
    if not spec:
        return 'not_assessable', [_ev('specs.product', 'empty')], _d('Enter the FPP specification in the product data.', 'أدخل مواصفة المنتج النهائي في بيانات المنتج.')
    tests = [_n(t.get('test')) for t in spec]
    missing = [k for k, words in UNIVERSAL.items() if not any(w in t for t in tests for w in words)]
    oral_solid = ctx.env.get('admin_route') == 'oral' and not ctx.env.get('aqueous_solution')
    diss = [t for t in spec if 'dissolution' in _n(t.get('test'))]
    q_missing = oral_solid and (not diss or not any(re.search(r'\bq\b', _n(t.get('limit'))) for t in diss))
    ev = [_ev('specs.product.tests', ', '.join(t.get('test', '') for t in spec)[:300]), _ev('specs.product.universal_missing', ', '.join(missing) or 'none')]
    if oral_solid:
        ev.append(_ev('specs.product.dissolution_Q', 'present' if not q_missing else 'missing'))
    if missing or q_missing:
        en = ('missing universal tests: ' + ', '.join(missing) if missing else '') + ('; dissolution Q missing' if q_missing else '')
        ar = ('اختبارات شاملة ناقصة: ' + '، '.join(missing) if missing else '') + ('؛ حد الذوبان Q غير موجود' if q_missing else '')
        return 'deficient', ev, _d(en.strip('; '), ar.strip('؛ '))
    return 'adequate', ev, _d('Universal tests present' + (' with a dissolution Q.' if oral_solid else '.'), 'الاختبارات الشاملة موجودة' + (' مع حد الذوبان Q.' if oral_solid else '.'))


def fpp_batches_min_2(ctx):
    batches = [b for b in (ctx.data.get('batches') or []) if (b.get('kind') or 'fpp') == 'fpp']
    if not batches:
        return 'not_assessable', [_ev('batches.fpp', 'none recorded')], _d('Record the FPP batches in the product data.', 'سجّل تشغيلات المنتج النهائي في بيانات المنتج.')
    results = ctx.data.get('results') or {}
    ev = [_ev('batches.fpp', '; '.join(f"{b.get('no')} · {b.get('size') or '?'} · {b.get('scale') or '?'}" for b in batches))]
    problems = []
    if len(batches) < 2:
        problems.append('only one batch (at least two of at least pilot scale, or one pilot + one smaller for an uncomplicated FPP)')
    smaller = [b.get('no') for b in batches if b.get('scale') == 'smaller']
    if smaller and not ctx.data.get('uncomplicated_fpp'):
        problems.append(f"batch {', '.join(smaller)} is below pilot scale and the FPP is not declared uncomplicated")
    spec = (ctx.data.get('specs') or {}).get('product') or []
    qual = {_n(t.get('test')) for t in spec if t.get('qualitative') in (True, 'yes', 'true', 1)}
    QUAL_WORDS = ('description', 'identification', 'identity', 'appearance', 'odour', 'odor', 'colour', 'color', 'الوصف', 'التعرف')
    words = []
    for b in batches:
        for test, val in (results.get(b.get('no')) or {}).items():
            if _n(test) in qual or any(w in _n(test) for w in QUAL_WORDS):
                continue
            if NON_NUMERIC.match(str(val)):
                words.append(f"{b.get('no')}/{test}")
    if words:
        problems.append('non-numeric results: ' + ', '.join(words[:6]))
        ev.append(_ev('results.non_numeric', ', '.join(words[:10])))
    desc = [b.get('no') for b in batches if not all(b.get(k) for k in ('no', 'size', 'date', 'site'))]
    if desc:
        problems.append('batch description incomplete (size, date, site): ' + ', '.join(str(x) for x in desc))
    if problems:
        return 'deficient', ev, _d('; '.join(problems), '؛ '.join(problems))
    return 'adequate', ev, _d(f'{len(batches)} batches with numeric results and full description.', f'{len(batches)} تشغيلة بنتائج رقمية ووصف كامل.')


def stability_batches(ctx):
    stab = (ctx.data.get('stability') or {})
    rows = stab.get('batches') or []
    if not rows:
        return 'not_assessable', [_ev('stability.batches', 'none recorded')], _d('Record the stability batches (long-term and accelerated months) in the product data.', 'سجّل تشغيلات الثبات (أشهر طويلة الأمد والمعجَّلة) في بيانات المنتج.')
    ev = [_ev('stability.batches', '; '.join(f"{r.get('no')} · LT {r.get('long_term_months', '?')} m · ACC {r.get('accelerated_months', '?')} m" for r in rows))]
    problems = []
    if len(rows) < 2:
        problems.append('fewer than two primary batches')
    short = [r.get('no') for r in rows if (r.get('long_term_months') or 0) < 6 or (r.get('accelerated_months') or 0) < 6]
    if short:
        problems.append('less than 6 months accelerated or long-term on: ' + ', '.join(str(x) for x in short))
    if problems:
        return 'deficient', ev, _d('; '.join(problems), '؛ '.join(problems))
    return 'adequate', ev, _d(f'{len(rows)} primary batches with ≥ 6 months at both conditions.', f'{len(rows)} تشغيلة أساسية بستة أشهر على الأقل في الحالتين.')


def leaflet_set(ctx):
    slots = {s['req_id']: s for s in ctx.board['slots']}
    pi = slots.get('M1-09', {}).get('documents', [])
    ref = slots.get('M1-42', {}).get('documents', [])
    ev = [_ev('slots[M1-09].documents', ', '.join(d['filename'] for d in pi) or 'none'), _ev('slots[M1-42].documents', ', '.join(d['filename'] for d in ref) or 'none')]
    if len(pi) >= 2 and ref:
        return 'adequate', ev, _d('Proposed SmPC/PIL and the reference leaflet are present.', 'النشرة المقترحة ونشرة المرجع موجودتان.')
    if not pi and not ref:
        return 'deficient', ev, _d('No leaflet documents.', 'لا توجد مستندات نشرة.')
    return 'deficient', ev, _d('The leaflet set is incomplete (SmPC + PIL in EN and AR, plus the reference leaflet).', 'مجموعة النشرة غير مكتملة (SmPC + PIL بالإنجليزية والعربية، مع نشرة المرجع).')


def peer_signed(ctx):
    signed = (ctx.opts or {}).get('signed') or {}
    ev = [_ev('run.signed', ', '.join(f"{k}: {v.get('by')}" for k, v in signed.items()) or 'none')]
    if signed.get('peer'):
        return 'adequate', ev, _d('Second assessor signed.', 'وقّع المُقيِّم الثاني.')
    return 'deficient', ev, _d('Not yet signed by a second assessor.', 'لم يوقّع مُقيِّم ثانٍ بعد.')


CHECKS = {f.__name__: f for f in (m1_complete, pdfs_searchable, certificates_valid, cep_valid, sites_consistent, cep_route, composition_complete,
                                   fpp_spec_universal, fpp_batches_min_2, stability_batches, leaflet_set, peer_signed)}
