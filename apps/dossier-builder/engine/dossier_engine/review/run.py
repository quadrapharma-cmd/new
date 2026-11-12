"""The review pipeline: resolve → completeness → technical → data gates → text evidence → aggregate → clock → diff.
Deterministic: the same dossier, data and pack give the same findings (the AI layer is separate and never automatic)."""
import time
from datetime import date
from .. import expr
from ..profile import Profile, Api
from . import pack as packmod, evidence, checks, storage

DEFAULTS = {'strictness': 'international', 'track': None, 'departments': None, 'reliance': False, 'ai': True}
SEV_ORDER = ['critical', 'major', 'minor', 'note']
OPEN = ('open', 'answered', 'not_accepted')
DEPT_BY_MODULE = {1: 'screening', 2: 'quality', 3: 'quality', 4: 'clinical', 5: 'be'}
ABBREVIATED = ('quality', 'cadc', 'stability')      # reliance route: the full technical assessment is abbreviated


class Ctx:
    def __init__(self, st, dossier, board, env, opts, today):
        self.st, self.dossier, self.board, self.env, self.opts, self.today = st, dossier, board, env, opts, today
        self.data = dossier.get('data') or {}
        self.text = evidence.DocText(st)
        prof_apis = {f"{a.get('name')}|{a.get('manufacturer')}": dict(a) for a in (dossier['profile'].get('apis') or [])}
        for a in self.data.get('apis') or []:
            prof_apis.setdefault(f"{a.get('name')}|{a.get('manufacturer')}", {}).update(a)
        self.apis = list(prof_apis.values())


def _profile(d):
    p = dict(d['profile'])
    apis = [Api(**{k: a[k] for k in ('name', 'manufacturer', 'option') if k in a}) for a in p.pop('apis', [])]
    return Profile(**{k: v for k, v in p.items() if k in Profile.__dataclass_fields__}, apis=apis)


def _bi(en, ar):
    return {'en': en, 'ar': ar}


def _finding(q, verdict, ev, detail, origin, slot_id=None, severity=None, extra=None):
    f = {'id': storage.new_id('F'), 'question_id': q['id'], 'key': f"{q['id']}|{slot_id or ''}", 'dept': q['dept'], 'layer': q.get('layer', 'eda'),
         'ctd': q['ctd'], 'slot_id': slot_id, 'severity': severity or q['severity'], 'verdict': verdict, 'origin': origin,
         'status': 'closed' if verdict == 'adequate' else 'open',
         'payload': {'title': q['title'], 'question': q['question'], 'deficiency': q['deficiency'], 'adequate': q.get('adequate'),
                     'evidence': ev, 'detail': detail, 'action': q.get('action'), 'source': q.get('source'), 'anchor': q.get('anchor'),
                     'provisional': bool(q.get('provisional')), 'needs_review': verdict == 'not_assessable' and origin == 'manual',
                     'slots': (q.get('evidence') or {}).get('slots') or [], 'keywords': (q.get('evidence') or {}).get('keywords') or []}}
    if extra:
        f['payload'].update(extra)
    return f


def assess_question(q, ctx):
    """One question → one finding (rule, data, text or slot evidence)."""
    auto = q.get('auto') or {'kind': 'none'}
    ev_spec = q.get('evidence') or {}
    kind = auto['kind']
    if kind == 'data':
        fn = checks.CHECKS.get(auto.get('check'))
        if not fn:
            return _finding(q, 'not_assessable', [], _bi(f"Unknown check {auto.get('check')}", f"فحص غير معروف {auto.get('check')}"), 'rule')
        verdict, ev, detail = fn(ctx)
        return _finding(q, verdict, ev, detail, 'data')
    slots, docs = evidence.slot_documents(ctx.board, ev_spec.get('slots') or [])
    doc_ev = [{'doc_id': d['id'], 'filename': d['filename'], 'slot_id': s['slot_id'], 'ctd': s['ctd']} for s, d in docs]
    if kind == 'slot':
        if docs:
            return _finding(q, 'adequate', doc_ev, _bi(f"{len(docs)} document(s) present.", f"{len(docs)} مستند(اً) موجود."), 'slot')
        if any(s.get('request') for s in slots):
            return _finding(q, 'not_assessable', doc_ev, _bi('Requested from the issuer; not received yet.', 'مطلوب من الجهة المُصدِرة ولم يصل بعد.'), 'slot')
        return _finding(q, 'deficient', doc_ev, _bi('No document in ' + ', '.join(s['ctd'] for s in slots), 'لا يوجد مستند في ' + '، '.join(s['ctd'] for s in slots)), 'slot')
    if kind == 'text':
        if not docs:
            if not slots or all(s['level'] in ('NA', 'NR') for s in slots):
                return _finding(q, 'not_assessable', [], _bi('The section does not apply to this product.', 'القسم لا ينطبق على هذا المنتج.'), 'text')
            return _finding(q, 'not_assessable', doc_ev, _bi('No document to read yet in ' + ', '.join(s['ctd'] for s in slots) + ' (see the missing-item finding).',
                                                            'لا يوجد مستند للقراءة بعد في ' + '، '.join(s['ctd'] for s in slots) + ' (انظر ملاحظة البند الناقص).'), 'text')
        readable, scanned, hits, pages_read = [], [], [], 0
        for s, d in docs:
            pages = ctx.text.pages(d)
            if ctx.text.scanned(d):
                scanned.append(d['filename'])
                continue
            readable.append(d)
            pages_read += len(pages)
            for h in evidence.find(pages, ev_spec.get('keywords') or []):
                hits.append({**h, 'doc_id': d['id'], 'filename': d['filename'], 'slot_id': s['slot_id']})
        found = {h['keyword'].lower() for h in hits}
        need = auto.get('min_hits', 1)
        if len(found) >= need:
            return _finding(q, 'adequate', hits[:8], _bi(f"Found {len(found)} of {len(ev_spec.get('keywords') or [])} indicators in {pages_read} page(s).", f"وُجد {len(found)} من {len(ev_spec.get('keywords') or [])} مؤشراً في {pages_read} صفحة."), 'text')
        if not readable:
            return _finding(q, 'not_assessable', doc_ev, _bi('Scanned without a text layer: ' + ', '.join(scanned) + '. EDA requires searchable PDFs: replace it with a copy made searchable when scanning, then re-assess.', 'ممسوح بدون طبقة نصية: ' + '، '.join(scanned) + '. الهيئة طالبة PDF قابل للبحث: استبدله بنسخة اتعمل لها OCR وقت المسح، وبعدين أعد التقييم.'), 'text',
                            extra={'needs_text': True})
        detail = _bi(f"Searched {pages_read} page(s) of {len(readable)} document(s) for: {', '.join(ev_spec.get('keywords') or [])} — found {len(found)} (need {need})." + (f" Unreadable scans: {', '.join(scanned)}." if scanned else ''),
                     f"بُحث في {pages_read} صفحة من {len(readable)} مستند عن: {'، '.join(ev_spec.get('keywords') or [])} — وُجد {len(found)} (المطلوب {need})." + (f" مسوحات غير مقروءة: {'، '.join(scanned)}." if scanned else ''))
        return _finding(q, 'deficient', hits + doc_ev[:4], detail, 'text')
    # kind none: manual / AI only
    return _finding(q, 'not_assessable', doc_ev, _bi('Needs an assessor (human or AI) to read the documents.', 'يحتاج مُقيِّماً (بشرياً أو ذكاءً اصطناعياً) لقراءة المستندات.'), 'manual')


def completeness_findings(ctx, enabled):
    out = []
    for s in ctx.board['slots']:
        if s['level'] != 'R' or s['status'] not in ('not_started', 'waiting') or (s['status'] == 'waiting' and s['documents']):
            continue
        dept = DEPT_BY_MODULE.get(s['module'], 'quality')
        if dept == 'be' and ctx.env.get('dossier_kind') == 'innovator':
            dept = 'clinical'
        if dept not in enabled:
            continue
        q = {'id': f"MISSING-{s['req_id']}", 'dept': dept, 'layer': 'eda', 'ctd': s['ctd'], 'severity': 'critical' if s['module'] == 1 else 'major',
             'title': s['title'], 'question': _bi(f"Is «{s['title']['en']}» ({s['ctd']}) provided?", f"هل «{s['title']['ar']}» ({s['ctd']}) مقدَّم؟"),
             'deficiency': _bi(f"«{s['title']['en']}» ({s['ctd']}) is required for this product and has not been provided.", f"«{s['title']['ar']}» ({s['ctd']}) مطلوب لهذا المنتج ولم يُقدَّم."),
             'action': {'type': 'upload', 'target': s['slot_id']}, 'source': {'code': 'NP.CAPP.065 v5/2025', 'section': s['ctd'], 'quote': '; '.join(r.get('en', '') for r in s['reasons'][:1])},
             'evidence': {'slots': [s['req_id']]}}
        if s['status'] == 'waiting':
            out.append(_finding(q, 'not_assessable', [], _bi(f"Requested from {s['request']['issuer']}; not received yet.", f"مطلوب من {s['request']['issuer']}؛ لم يصل بعد."), 'slot', slot_id=s['slot_id']))
        else:
            out.append(_finding(q, 'deficient', [], _bi('No document in the slot.', 'لا يوجد مستند في الخانة.'), 'slot', slot_id=s['slot_id']))
    return out


def technical_findings(ctx, enabled):
    if 'technical' not in enabled:
        return []
    out = []
    for s in ctx.board['slots']:
        for d in s['documents']:
            bad = [f for f in d.get('findings') or []]
            if not bad:
                continue
            blocks = [f for f in bad if f.get('severity') == 'block']
            sev = 'critical' if blocks else 'minor'
            q = {'id': f"TECH-{s['req_id']}", 'dept': 'technical', 'layer': 'eda', 'ctd': s['ctd'], 'severity': sev, 'title': s['title'],
                 'question': _bi(f"Does «{d['filename']}» conform to the technical PDF profile?", f"هل «{d['filename']}» مطابق للملف الفني لملفات PDF؟"),
                 'deficiency': _bi('; '.join(f.get('en', '') for f in bad[:4]), '؛ '.join(f.get('ar', '') for f in bad[:4])),
                 'action': {'type': 'fix' if any(f.get('action') == 'auto_fix' for f in bad) else 'rebuild', 'target': s['slot_id']},
                 'source': {'code': bad[0].get('source') or 'EDA eCTD technical guidance (DRAFT v1/2026) · ICH eCTD', 'section': bad[0].get('rule', '')},
                 'evidence': {'slots': [s['req_id']]}}
            ev = [{'doc_id': d['id'], 'filename': d['filename'], 'slot_id': s['slot_id'], 'ctd': s['ctd'], 'rules': [f.get('rule') for f in bad]}]
            out.append(_finding(q, 'deficient', ev, _bi(f"{len(blocks)} blocking, {len(bad) - len(blocks)} warning(s).", f"{len(blocks)} مانع، {len(bad) - len(blocks)} تحذير."), 'rule', slot_id=s['slot_id']))
    return out


def cross_findings(ctx, enabled):
    out = []
    for i, f in enumerate(ctx.board.get('cross') or []):
        dept = 'quality'
        if f['id'] in ('XC-07', 'XC-10'):
            dept = 'screening' if f['id'] == 'XC-07' else 'labelling'
        if dept not in enabled:
            continue
        sev = 'critical' if f.get('severity') == 'block' else 'major'
        slots = f.get('slots') or []
        q = {'id': f['id'], 'dept': dept, 'layer': 'eda', 'ctd': ', '.join(slots[:3]) or '3.2', 'severity': sev, 'title': _bi(f"Cross-check {f['id']}", f"فحص التطابق {f['id']}"),
             'question': _bi(f"Cross-check {f['id']}: are the related data consistent across the dossier?", f"فحص التطابق {f['id']}: هل البيانات المرتبطة متسقة عبر الملف؟"),
             'deficiency': _bi(f['en'], f['ar']), 'action': {'type': {'rebuild': 'rebuild', 'request_data': 'edit_data'}.get(f.get('action'), 'edit_data'), 'target': slots[0] if slots else 'data'},
             'source': {'code': f.get('source') or 'NP.CAPP.040 v1/2022'}, 'evidence': {'slots': slots}}
        if f.get('needs'):
            out.append(_finding(q, 'not_assessable', [{'field': 'needs', 'value': ', '.join(map(str, f['needs']))}], _bi('Needs data: ' + ', '.join(map(str, f['needs'])), 'يحتاج بيانات: ' + '، '.join(map(str, f['needs']))), 'data', slot_id=slots[0] if slots else None))
        else:
            out.append(_finding(q, 'deficient', [{'field': 'cross', 'value': f['en']}], _bi(f['en'], f['ar']), 'data', slot_id=slots[0] if slots else None))
        out[-1]['key'] = f"{f['id']}#{i}"
    return out


def dept_verdicts(findings, enabled):
    out = {}
    for d in enabled:
        fs = [f for f in findings if f['dept'] == d]
        opened = [f for f in fs if f['verdict'] == 'deficient' and f['status'] in OPEN and not (f['origin'] == 'ai' and not f.get('confirmed_by'))]
        sev = {s: sum(1 for f in opened if f['severity'] == s) for s in SEV_ORDER}
        pending = sum(1 for f in fs if f['verdict'] == 'not_assessable')
        v = 'reject' if sev['critical'] else 'clock_stop' if sev['major'] else 'comments' if sev['minor'] else 'approve'
        out[d] = {'verdict': v, 'counts': sev, 'not_assessable': pending, 'total': len(fs), 'pending_review': v == 'approve' and pending > 0}
    return out


def overall(dv, enabled):
    if 'screening' in dv and dv['screening']['verdict'] == 'reject':
        return 'not_ready', _bi('The dossier would not pass screening: a critical Module 1 finding stops the file before the technical departments see it.',
                                'الملف لن يعدي الفحص الأولي: ملاحظة حرجة في الوحدة 1 توقف الملف قبل أن تراه الإدارات الفنية.')
    vs = [x['verdict'] for d, x in dv.items() if d in enabled]
    if 'reject' in vs:
        return 'not_ready', _bi('At least one department would reject the dossier or require resubmission.', 'إدارة واحدة على الأقل سترفض الملف أو تطلب إعادة تقديم.')
    if 'clock_stop' in vs:
        return 'ready_with_risks', _bi('At least one deficiency round (clock stop) is expected.', 'متوقع جولة استيفاء واحدة على الأقل (إيقاف الساعة).')
    return 'ready', _bi('Every department approves, with or without comments.', 'كل الإدارات موافقة، مع ملاحظات أو بدونها.')


def clock_plan(pack, env, opts, dv):
    key = opts.get('track') or ('c2_track_c_ref' if env.get('origin') == 'imported' and opts.get('reliance') else 'c2_track_c')
    tr = pack.track(key) or pack.track('c2_track_c')
    names = pack.meta['stage_names']['six' if len(tr['stages']) == 6 else 'four']
    stops = [d for d, x in dv.items() if d not in ('screening', 'technical') and x['verdict'] in ('clock_stop', 'reject')]
    screening_reject = dv.get('screening', {}).get('verdict') == 'reject'
    return {'track': key, 'label': {'en': tr['en'], 'ar': tr['ar']}, 'decree': tr['decree'], 'total_months': tr.get('total_months'),
            'stages': [{'label': n, 'wds': w} for n, w in zip(names, tr['stages'])], 'clock_stop_months': pack.meta['clock_stop']['fast_track_months'],
            'expected_rounds': len(stops), 'stopping_departments': stops, 'screening_reject': screening_reject,
            'note': _bi('Published working days per stage; a deficiency round is the company’s maximum reply time, not EDA time.', 'أيام العمل المنشورة لكل مرحلة؛ جولة الاستيفاء هي أقصى مهلة للشركة لا مدة الهيئة.')}


def counts_of(findings):
    opened = [f for f in findings if f['verdict'] == 'deficient' and f['status'] in OPEN]
    c = {s: sum(1 for f in opened if f['severity'] == s) for s in SEV_ORDER}
    c.update({'not_assessable': sum(1 for f in findings if f['verdict'] == 'not_assessable'), 'adequate': sum(1 for f in findings if f['verdict'] == 'adequate'),
              'total': len(findings), 'open': len(opened), 'needs_review': sum(1 for f in findings if f['payload'].get('needs_review')),
              'ai_pending': sum(1 for f in findings if f['payload'].get('ai') and not f.get('confirmed_by'))})
    return c


def diff_runs(prev_findings, findings):
    def opened(fs):
        return {f['key'] for f in fs if f['verdict'] == 'deficient' and f['status'] in OPEN}
    a, b = opened(prev_findings or []), opened(findings)
    return {'closed': sorted(a - b), 'new': sorted(b - a), 'still_open': sorted(a & b)}


def aggregate(run, findings, pack, env):
    enabled = run['options'].get('departments') or [d['id'] for d in pack.departments()]
    dv = dept_verdicts(findings, enabled)
    verdict, why = overall(dv, enabled)
    run.update({'dept_verdicts': dv, 'verdict': verdict, 'why': why, 'counts': counts_of(findings), 'clock': clock_plan(pack, env, run['options'], dv)})
    return run


def run_review(st, did, options=None, actor=None, pack=None, today=None):
    pack = pack or packmod.load()
    opts = {**DEFAULTS, **(options or {})}
    today = today or st.today()
    dossier = st.dossier(did)
    prof = _profile(dossier)
    env = prof.env()
    env.update({'reliance': bool(opts.get('reliance')), 'strictness': opts['strictness']})
    board = st.board(did)
    ctx = Ctx(st, dossier, board, env, opts, today)
    layers = pack.layers_for(opts['strictness'])
    enabled = opts.get('departments') or [d['id'] for d in pack.departments()]
    if not opts.get('reliance'):
        enabled = [d for d in enabled if d != 'reliance']
    opts['departments'] = enabled
    findings = completeness_findings(ctx, enabled) + technical_findings(ctx, enabled) + cross_findings(ctx, enabled)
    for q in pack.questions:
        if q.get('layer', 'eda') not in layers or q['dept'] not in enabled:
            continue
        try:
            if not expr.evaluate(q.get('applies', 'true'), env):
                continue
        except expr.ExprError:
            continue
        f = assess_question(q, ctx)
        if opts.get('reliance') and q['dept'] in ABBREVIATED and f['severity'] == 'critical':
            f['severity'] = 'major'
            f['payload']['abbreviated'] = True
        findings.append(f)
    prev = storage.latest(st, did)
    prev_findings = storage.findings(st, prev['id']) if prev else []
    run = {'id': storage.new_id('R'), 'dossier_id': did, 'created': time.time(), 'actor': actor, 'options': opts, 'pack_version': f"{pack.id} {pack.version}",
           'status': 'done', 'previous_run_id': prev['id'] if prev else None, 'signed': {}, 'letters': {}}
    aggregate(run, findings, pack, env)
    run['diff'] = diff_runs(prev_findings, findings)
    run['options']['env'] = {k: env[k] for k in ('dossier_kind', 'origin', 'activity', 'admin_route') if k in env}
    storage.save_run(st, run, findings)
    st.audit(did, 'review.run', run=run['id'], verdict=run['verdict'], open=run['counts']['open'])
    return run, findings


def reassess(st, did, run, finding, pack=None, today=None):
    """Re-run one question on the current documents and data; close the finding when it became adequate."""
    pack = pack or packmod.load()
    dossier = st.dossier(did)
    env = _profile(dossier).env()
    env.update({'reliance': bool(run['options'].get('reliance')), 'strictness': run['options'].get('strictness', 'international')})
    ctx = Ctx(st, dossier, st.board(did), env, {**run['options'], 'signed': run.get('signed') or {}}, today or st.today())
    qid = finding['question_id']
    q = pack.by_id.get(qid)
    if q is None:                                   # completeness / technical / cross findings: rebuild from the board
        fresh = {f['key']: f for f in completeness_findings(ctx, run['options']['departments']) + technical_findings(ctx, run['options']['departments']) + cross_findings(ctx, run['options']['departments'])}
        nf = fresh.get(finding['key'])
        verdict = nf['verdict'] if nf else 'adequate'
        ev, detail = (nf['payload']['evidence'], nf['payload']['detail']) if nf else ([], _bi('Resolved: the condition no longer applies.', 'تم الحل: الشرط لم يعد قائماً.'))
        origin = finding['origin']
    else:
        nf = assess_question(q, ctx)
        verdict, ev, detail, origin = nf['verdict'], nf['payload']['evidence'], nf['payload']['detail'], nf['origin']
    responses = finding.get('responses') or []
    if verdict == 'adequate':
        status = 'accepted' if responses else 'closed'
    elif responses:
        status = 'not_accepted'
    else:
        status = 'open'
    payload = dict(finding['payload'], evidence=ev, detail=detail, reassessed_at=time.time())
    storage.update_finding(st, finding['id'], verdict=verdict, status=status, payload=payload, origin=origin, confirmed_by=None, confidence=None)
    if responses:                                   # the latest response carries the outcome of this re-assessment
        storage.set_response_result(st, responses[-1]['id'], 'accepted' if verdict == 'adequate' else 'not_accepted')
    refresh(st, did, run['id'], pack)
    return storage.finding(st, finding['id'])


def refresh(st, did, rid, pack=None):
    """Recompute the run's aggregates from its findings (after confirmations, overrides, responses)."""
    pack = pack or packmod.load()
    run = storage.run(st, rid)
    findings = storage.findings(st, rid)
    env = _profile(st.dossier(did)).env()
    env.update({'reliance': bool(run['options'].get('reliance')), 'strictness': run['options'].get('strictness', 'international')})
    aggregate(run, findings, pack, env)
    storage.update_run(st, rid, dept_verdicts=run['dept_verdicts'], verdict=run['verdict'], counts=run['counts'], clock=run['clock'])
    return run
