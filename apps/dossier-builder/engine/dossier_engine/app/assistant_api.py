"""Assistant endpoints: settings (the key never leaves the server), the conversation per dossier, approvals, stop, usage."""
import time
from fastapi import HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from ..assistant import settings as asettings, storage, runner
from ..officefiles import sniff as _sniff


def err(status, code, en, ar, **extra):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar, **extra})


class SettingsReq(BaseModel):
    api_key: str | None = None
    model: str | None = None
    effort: str | None = None
    budget_tokens: int | None = None
    max_steps: int | None = None
    never_send: list | None = None


class Decision(BaseModel):
    decision: str                   # approve | deny
    note: str | None = None


def install(app, st):
    storage.ensure(st)

    def _user(request):
        return getattr(request.state, 'user', None) or 'local'

    def _admin_only(request):
        if app.state.auth.enabled and getattr(request.state, 'role', None) != 'admin':
            err(403, 'E-ROLE', 'Only an administrator can change the Assistant settings.', 'إعدادات المساعد للمدير بس.')

    @app.get('/api/assistant/settings')
    def get_settings():
        return asettings.status(st.root)

    @app.put('/api/assistant/settings')
    def put_settings(body: SettingsReq, request: Request):
        _admin_only(request)
        if asettings.status(st.root)['browser']:
            err(501, 'E-BROWSER', 'The Assistant runs in the desktop and cloud editions, not in the browser edition.',
                'المساعد بيشتغل في نسخة سطح المكتب والسحابة، مش في نسخة المتصفح.')
        out = asettings.save(st.root, **body.model_dump())
        st.audit(None, 'assistant.settings', keys=[k for k, v in body.model_dump().items() if v is not None], by=_user(request))
        return out

    @app.post('/api/assistant/settings/test')
    def test_settings(request: Request):
        """One cheap call to the API with the stored key: tells the user whether the key works before any dossier work."""
        _admin_only(request)
        if not asettings.api_key(st.root):
            err(501, 'E-NO-AI', 'No Anthropic API key is set.', 'مفيش مفتاح Anthropic متسجّل.')
        try:
            client = runner.client_for(st.root)
            m = client.models.retrieve(asettings.load(st.root)['model'])
            return {'ok': True, 'model': getattr(m, 'id', None) or asettings.load(st.root)['model'], 'display_name': getattr(m, 'display_name', None)}
        except Exception as e:
            name = type(e).__name__
            status = getattr(e, 'status_code', None)
            if status == 401 or 'authentication' in name.lower():
                err(401, 'E-AI-KEY', 'The API key was refused.', 'المفتاح مرفوض.')
            err(502, 'E-AI', f'{name}: {str(e)[:300]}', 'تعذّر الاتصال بـ Anthropic.')

    def _state(did):
        run = storage.latest_run(st, did)
        return {'messages': runner.render(st, did), 'run': run and {k: run.get(k) for k in ('id', 'status', 'started', 'ended', 'error', 'usage', 'steps', 'partial')},
                'approvals': [{k: a.get(k) for k in ('id', 'tool', 'args', 'created', 'status')} for a in storage.approvals(st, did, status='pending')],
                'usage': storage.usage_total(st, did), 'readings': len(storage.readings(st, did)), 'settings': asettings.status(st.root)}

    @app.get('/api/dossiers/{did}/assistant')
    def get_state(did: str):
        st.dossier(did)
        return _state(did)

    @app.post('/api/dossiers/{did}/assistant/messages', status_code=201)
    async def post_message(did: str, request: Request, text: str = Form(''), files: list[UploadFile] = File(default=[])):
        st.dossier(did)
        status = asettings.status(st.root)
        if status['browser']:
            err(501, 'E-BROWSER', 'The Assistant runs in the desktop and cloud editions.', 'المساعد بيشتغل في نسخة سطح المكتب والسحابة.')
        if not status['configured']:
            err(501, 'E-NO-AI', 'Set the Anthropic API key in the Assistant settings first.', 'سجّل مفتاح Anthropic في إعدادات المساعد الأول.')
        if storage.active_run(st, did):
            err(409, 'E-ASSISTANT-BUSY', 'The Assistant is still working on the previous message.', 'المساعد لسه شغّال على الرسالة اللي فاتت.')
        staged = []
        for f in files or []:
            data = await f.read()
            if not data:
                continue
            if _sniff(f.filename, data) in ('other', 'archive'):
                err(422, 'E-FILE', f'{f.filename}: PDF, Office (Word, Excel, PowerPoint), text or image files only.', f'{f.filename}: ملفات PDF أو Office (Word، Excel، PowerPoint) أو نصوص أو صور بس.')
            staged.append(storage.stage_document(st, did, f.filename, data))
        if not (text or '').strip() and not staged:
            err(422, 'E-EMPTY', 'Write a message or attach files.', 'اكتب رسالة أو أرفق ملفات.')
        try:
            rid = runner.send(app, st, did, _user(request), text, staged)
        except RuntimeError:
            err(409, 'E-ASSISTANT-BUSY', 'The Assistant is still working.', 'المساعد لسه شغّال.')
        return {'run_id': rid, 'staged': [{'id': d['id'], 'filename': d['filename']} for d in staged], **_state(did)}

    @app.post('/api/dossiers/{did}/assistant/approvals/{aid}')
    def approve(did: str, aid: str, body: Decision, request: Request):
        st.dossier(did)
        if body.decision not in ('approve', 'deny'):
            err(422, 'E-DECISION', 'decision must be approve or deny.', 'القرار لازم يكون approve أو deny.')
        try:
            res = runner.decide(app, st, did, aid, body.decision, _user(request), body.note)
        except KeyError:
            err(404, 'E-NOT-FOUND', 'Approval not found.', 'طلب الموافقة غير موجود.')
        except ValueError:
            err(409, 'E-DECIDED', 'Already decided.', 'اتقرر فيه قبل كده.')
        return {'result': res, **_state(did)}

    @app.post('/api/dossiers/{did}/assistant/stop')
    def stop(did: str):
        st.dossier(did)
        return {'stopped': runner.stop(st, did), **_state(did)}

    @app.delete('/api/dossiers/{did}/assistant')
    def clear(did: str, request: Request):
        st.dossier(did)
        if storage.active_run(st, did):
            err(409, 'E-ASSISTANT-BUSY', 'Stop the Assistant first.', 'وقّف المساعد الأول.')
        storage.clear(st, did)
        st.audit(did, 'assistant.cleared', by=_user(request))
        return _state(did)

    @app.get('/api/dossiers/{did}/assistant/readings')
    def readings(did: str, doc_id: str = None):
        st.dossier(did)
        return storage.readings(st, did, doc_id)
