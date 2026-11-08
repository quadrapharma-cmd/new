"""Regulatory Reviewer endpoints: /api/dossiers/{did}/review/… and /api/review/pack."""
import shutil
import tempfile
import time
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from ..review import pack as packmod, run as runmod, storage, letters, ai as aimod, evidence, checks

MEDIA = {'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'pdf': 'application/pdf'}


def err(status, code, en, ar, **extra):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar, **extra})


class RunReq(BaseModel):
    strictness: str = 'international'
    track: str | None = None
    departments: list | None = None
    reliance: bool = False
    ai: bool = True
    actor: str | None = None


class FindingAct(BaseModel):
    action: str            # confirm | override | withdraw | reopen | dismiss_ai
    verdict: str | None = None
    reason: str | None = None
    by: str | None = None


class RespReq(BaseModel):
    text: str
    doc_ids: list = []
    by: str | None = None


class SignReq(BaseModel):
    role: str              # assessor | peer
    by: str


class AiAnswers(BaseModel):
    answers: dict | str


def install(app, st):
    from ..review import docreview
    storage.ensure(st)
    docreview.ensure(st)
    PACK = packmod.load()
    REQ = st.pack(PACK.meta['requirements_pack'])

    def _run(did, rid):
        r = storage.run(st, rid)
        if not r or r['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Review run not found.', 'جولة المراجعة غير موجودة.')
        return r

    def _finding(rid, fid):
        f = storage.finding(st, fid)
        if not f or f['run_id'] != rid:
            err(404, 'E-NOT-FOUND', 'Finding not found.', 'الملاحظة غير موجودة.')
        return f

    @app.get('/api/review/pack')
    def pack_info():
        depts = PACK.departments()
        return {'id': PACK.id, 'version': PACK.version, 'status': PACK.meta.get('status'), 'counts': PACK.counts(), 'departments': depts,
                'layers': PACK.meta['layers'], 'strictness': PACK.meta['strictness'], 'severity': PACK.meta['severity'], 'tracks': PACK.meta['tracks'],
                'sources': PACK.meta['sources'], 'unread': PACK.meta.get('unread', []), 'lint': packmod.lint(PACK, REQ, checks.CHECKS),
                'questions': [{k: q.get(k) for k in ('id', 'dept', 'layer', 'ctd', 'title', 'question', 'severity', 'applies', 'source', 'anchor', 'provisional', 'auto')} for q in PACK.questions]}

    @app.post('/api/dossiers/{did}/review', status_code=201)
    def run_review(did: str, body: RunReq):
        st.dossier(did)
        run, findings = runmod.run_review(st, did, body.model_dump(exclude={'actor'}), actor=body.actor, pack=PACK)
        return {'run': run, 'findings': findings}

    @app.get('/api/dossiers/{did}/review')
    def list_runs(did: str):
        st.dossier(did)
        return {'runs': storage.runs(st, did)}

    @app.get('/api/dossiers/{did}/review/latest')
    def latest(did: str):
        st.dossier(did)
        r = storage.latest(st, did)
        if not r:
            return {'run': None, 'findings': []}
        return {'run': r, 'findings': storage.findings(st, r['id'])}

    @app.get('/api/dossiers/{did}/review/{rid}')
    def get_run(did: str, rid: str, dept: str = None, verdict: str = None, severity: str = None, status: str = None):
        r = _run(did, rid)
        return {'run': r, 'findings': storage.findings(st, rid, dept=dept, verdict=verdict, severity=severity, status=status)}

    @app.post('/api/dossiers/{did}/review/{rid}/findings/{fid}')
    def act(did: str, rid: str, fid: str, body: FindingAct):
        _run(did, rid)
        f = _finding(rid, fid)
        by = body.by or 'reviewer'
        if body.action == 'confirm':
            f = aimod.confirm(storage, st, f, by) if f['payload'].get('ai') else (storage.update_finding(st, fid, confirmed_by=by, confirmed_at=time.time()) or storage.finding(st, fid))
            st.audit(did, 'review.finding.confirmed', finding=fid, by=by)
        elif body.action == 'override':
            if body.verdict not in packmod.VERDICTS or not (body.reason or '').strip():
                err(422, 'E-OVERRIDE', 'An override needs a verdict and a reason.', 'التعديل اليدوي يحتاج حكماً وسبباً.')
            payload = dict(f['payload'], needs_review=False)
            status = 'closed' if body.verdict == 'adequate' else 'open'
            storage.update_finding(st, fid, verdict=body.verdict, origin='human', confirmed_by=by, confirmed_at=time.time(), status=status, payload=payload,
                                   override={'by': by, 'reason': body.reason, 'at': time.time(), 'from': f['verdict']})
            st.audit(did, 'review.finding.override', finding=fid, by=by, verdict=body.verdict, reason=body.reason)
            f = storage.finding(st, fid)
        elif body.action == 'withdraw':
            if not (body.reason or '').strip():
                err(422, 'E-OVERRIDE', 'Withdrawing a finding needs a reason.', 'سحب الملاحظة يحتاج سبباً.')
            storage.update_finding(st, fid, status='withdrawn', override={'by': by, 'reason': body.reason, 'at': time.time(), 'from': f['status']})
            st.audit(did, 'review.finding.withdrawn', finding=fid, by=by, reason=body.reason)
            f = storage.finding(st, fid)
        elif body.action == 'reopen':
            storage.update_finding(st, fid, status='open')
            f = storage.finding(st, fid)
        elif body.action == 'dismiss_ai':
            payload = dict(f['payload'])
            payload.pop('ai', None)
            storage.update_finding(st, fid, payload=payload)
            f = storage.finding(st, fid)
        else:
            err(422, 'E-ACTION', f'Unknown action {body.action}.', 'إجراء غير معروف.')
        run = runmod.refresh(st, did, rid, PACK)
        return {'finding': f, 'run': run}

    @app.post('/api/dossiers/{did}/review/{rid}/findings/{fid}/responses', status_code=201)
    def respond(did: str, rid: str, fid: str, body: RespReq):
        _run(did, rid)
        f = _finding(rid, fid)
        if not body.text.strip():
            err(422, 'E-RESPONSE', 'The response text is empty.', 'نص الرد فارغ.')
        round_no = len(f.get('responses') or []) + 1
        resp = storage.add_response(st, fid, rid, body.text.strip(), body.doc_ids, actor=body.by, round_no=round_no)
        storage.update_finding(st, fid, status='answered')
        st.audit(did, 'review.response', finding=fid, by=body.by, round=round_no)
        run = runmod.refresh(st, did, rid, PACK)
        return {'response': resp, 'finding': storage.finding(st, fid), 'run': run}

    @app.post('/api/dossiers/{did}/review/{rid}/findings/{fid}/reassess')
    def reassess(did: str, rid: str, fid: str):
        run = _run(did, rid)
        f = _finding(rid, fid)
        nf = runmod.reassess(st, did, run, f, PACK)
        st.audit(did, 'review.finding.reassessed', finding=fid, verdict=nf['verdict'], status=nf['status'])
        return {'finding': nf, 'run': storage.run(st, rid)}

    @app.post('/api/dossiers/{did}/review/{rid}/sign')
    def sign(did: str, rid: str, body: SignReq):
        run = _run(did, rid)
        if body.role not in ('assessor', 'peer'):
            err(422, 'E-SIGN', 'Role must be assessor or peer.', 'الدور يجب أن يكون مُقيِّماً أو مُقيِّماً ثانياً.')
        signed = dict(run.get('signed') or {})
        if body.role == 'peer' and signed.get('assessor', {}).get('by') == body.by:
            err(422, 'E-SIGN', 'The second assessor must be a different person.', 'المُقيِّم الثاني يجب أن يكون شخصاً مختلفاً.')
        signed[body.role] = {'by': body.by, 'at': time.strftime('%Y-%m-%d %H:%M')}
        storage.update_run(st, rid, signed=signed)
        for f in storage.findings(st, rid):
            if f['question_id'] == 'IN-GREVP-01':
                runmod.reassess(st, did, storage.run(st, rid), f, PACK)
        st.audit(did, 'review.signed', run=rid, role=body.role, by=body.by)
        return {'run': storage.run(st, rid)}

    def _doc(did, rid, dept, kind):
        run = _run(did, rid)
        if not PACK.dept(dept):
            err(404, 'E-DEPT', f'Unknown department {dept}.', 'إدارة غير معروفة.')
        dossier = st.dossier(did)
        findings = storage.findings(st, rid)
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / f"{kind}-{dept}.docx"
            (letters.deficiency_letter if kind == 'letter' else letters.assessment_report)(out, dossier, run, PACK, dept, findings)
            docx = out.read_bytes()
            pdf = None
            try:
                pdf = letters.pdf_of(out).read_bytes()
            except Exception:
                pdf = None
            meta = {'docx': st.put_blob(docx), 'pdf': st.put_blob(pdf) if pdf else None, 'created': time.time(), 'items': len(letters.letter_items(findings, dept)) if kind == 'letter' else len([f for f in findings if f['dept'] == dept])}
            ls = dict(run.get('letters') or {})
            ls[f"{kind}:{dept}"] = meta
            storage.update_run(st, rid, letters=ls)
            st.audit(did, f'review.{kind}', run=rid, dept=dept)
            return meta
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @app.post('/api/dossiers/{did}/review/{rid}/letters/{dept}', status_code=201)
    def make_letter(did: str, rid: str, dept: str):
        return _doc(did, rid, dept, 'letter')

    @app.post('/api/dossiers/{did}/review/{rid}/reports/{dept}', status_code=201)
    def make_report(did: str, rid: str, dept: str):
        return _doc(did, rid, dept, 'report')

    @app.get('/api/dossiers/{did}/review/{rid}/{kind}/{dept}/file')
    def letter_file(did: str, rid: str, kind: str, dept: str, fmt: str = 'docx'):
        run = _run(did, rid)
        k = {'letters': 'letter', 'reports': 'report'}.get(kind)
        meta = (run.get('letters') or {}).get(f"{k}:{dept}")
        if not meta or not meta.get(fmt):
            err(404, 'E-NOT-FOUND', 'Generate the document first.', 'ولّد المستند أولاً.')
        data = st.blob_path(meta[fmt]).read_bytes()
        name = f"{k}-{dept}-{rid}.{fmt}"
        return Response(data, media_type=MEDIA.get(fmt, 'application/octet-stream'), headers={'content-disposition': f'attachment; filename="{name}"'})

    @app.post('/api/dossiers/{did}/documents/{doc_id}/review', status_code=201)
    def doc_review_run(did: str, doc_id: str):
        """One document against its rubric, by the rules (keywords, dates, validity); the rest is left to the Assistant."""
        st.dossier(did)
        try:
            return docreview.run_rules(st, did, doc_id, PACK)
        except KeyError:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')

    @app.get('/api/dossiers/{did}/documents/{doc_id}/review')
    def doc_review_get(did: str, doc_id: str):
        st.dossier(did)
        try:
            rb = docreview.rubric(st, did, doc_id, PACK)
        except KeyError:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        return {'latest': docreview.latest(st, doc_id), 'history': len(docreview.history(st, doc_id)), 'rules': len(rb['rules']),
                'is_docx': rb['document']['is_docx'], 'third_party': rb['document']['third_party'], 'generated': rb['document']['generated'],
                'memos': docreview.memos_for(st, did, doc_id)}

    @app.get('/api/dossiers/{did}/documents/{doc_id}/rubric')
    def doc_rubric(did: str, doc_id: str):
        st.dossier(did)
        try:
            return docreview.rubric(st, did, doc_id, PACK)
        except KeyError:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')

    @app.get('/api/dossiers/{did}/review/{rid}/ai')
    def ai_prompt(did: str, rid: str, dept: str = None, ctd: str = None, ids: str = None):
        _run(did, rid)
        findings = aimod.section_findings(storage.findings(st, rid), dept, ctd, set(ids.split(',')) if ids else None)
        if not findings:
            err(422, 'E-AI-EMPTY', 'No questions in this section.', 'لا توجد أسئلة في هذا القسم.')
        board = st.board(did)
        docs = aimod.documents_for(findings, board)
        text = evidence.DocText(st)
        texts = []
        for dmeta in docs:
            d = st.document(dmeta['doc_id'])
            pages = text.pages(d)
            texts.append({'filename': d['filename'], 'doc_id': d['id'], 'scanned': text.scanned(d), 'pages': [{'page': n, 'text': t} for n, t in pages]})
        prompt = aimod.build_prompt(findings, texts)
        return {'prompt': prompt, 'documents': [{**x, 'scanned': t['scanned']} for x, t in zip(docs, texts)], 'findings': [f['id'] for f in findings]}

    @app.post('/api/dossiers/{did}/review/{rid}/ai')
    def ai_apply(did: str, rid: str, body: AiAnswers):
        _run(did, rid)
        try:
            answers = aimod.parse_answers(body.answers)
        except (ValueError, KeyError):
            err(502, 'E-AI-JSON', 'The answers are not in the expected JSON shape.', 'الإجابات ليست بالشكل المتوقع.')
        findings = {f['id']: f for f in storage.findings(st, rid)}
        board = st.board(did)
        text = evidence.DocText(st)
        texts = []
        for dmeta in aimod.documents_for(list(findings.values()), board):
            d = st.document(dmeta['doc_id'])
            texts.append({'filename': d['filename'], 'pages': [{'page': n, 'text': t} for n, t in text.pages(d)]})
        out = []
        for fid, a in answers.items():
            f = findings.get(fid)
            if not f:
                continue
            out.append(aimod.suggest(storage, st, f, aimod.verify_excerpts(a, texts)))
        st.audit(did, 'review.ai.suggested', run=rid, count=len(out))
        run = runmod.refresh(st, did, rid, PACK)
        return {'findings': out, 'run': run}

    @app.post('/api/dossiers/{did}/review/{rid}/ai/server')
    def ai_server(did: str, rid: str, dept: str = None, ctd: str = None, ids: str = None):
        p = ai_prompt(did, rid, dept, ctd, ids)
        pairs = []
        for dmeta in p['documents']:
            d = st.document(dmeta['doc_id'])
            if d['filename'].lower().endswith('.pdf'):
                pairs.append((d['filename'], st.blob_path(d['sha256']).read_bytes()))
        try:
            text = aimod.assess_server(p['prompt'], pairs)
        except RuntimeError as e:
            if str(e) == 'E-NO-AI':
                err(501, 'E-NO-AI', 'Set ANTHROPIC_API_KEY on this computer to let Claude assess the documents.', 'اضبط ANTHROPIC_API_KEY على الجهاز ده عشان Claude يقيّم المستندات.')
            err(422, 'E-AI-REFUSED', 'Claude declined to assess these documents.', 'Claude اعتذر عن تقييم المستندات دي.')
        return ai_apply(did, rid, AiAnswers(answers=text))
