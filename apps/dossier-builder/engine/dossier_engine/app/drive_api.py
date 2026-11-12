"""Drive source endpoints: settings (admin), list a folder link, read a file (proxied bytes), stage files into a dossier."""
from fastapi import HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from .. import drive as _drive
from ..assistant import storage as astorage


def err(status, code, en, ar, **extra):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar, **extra})


class DriveSettings(BaseModel):
    api_key: str | None = None
    service_account: dict | str | None = None


class ListReq(BaseModel):
    link: str
    recursive: bool = False


class StageReq(BaseModel):
    files: list                    # [{id, name, mime}]


def install(app, st):
    def _admin_only(request):
        if app.state.auth.enabled and getattr(request.state, 'role', None) != 'admin':
            err(403, 'E-ROLE', 'Only an administrator can change the Drive settings.', 'إعدادات Drive للمدير بس.')

    def _client():
        return _drive.Drive(_drive.load(st.root))

    def _raise(e):
        err(e.status, e.code, e.en, e.ar)

    @app.get('/api/drive/settings')
    def get_settings():
        return _drive.status(st.root)

    @app.put('/api/drive/settings')
    def put_settings(body: DriveSettings, request: Request):
        _admin_only(request)
        if _drive.status(st.root)['browser'] and body.service_account not in (None, '', {}):
            err(501, 'E-BROWSER', 'A service account key stays on a server; the browser edition uses an API key.', 'مفتاح حساب الخدمة بيفضل على الخادم؛ نسخة المتصفح بتستخدم مفتاح API.')
        try:
            out = _drive.save(st.root, body.api_key, body.service_account)
        except _drive.DriveError as e:
            _raise(e)
        except ValueError:
            err(422, 'E-DRIVE-SA', 'The service account must be valid JSON.', 'حساب الخدمة لازم يكون JSON صحيح.')
        st.audit(None, 'drive.settings', keys=[k for k, v in body.model_dump().items() if v is not None], by=getattr(request.state, 'user', None) or 'local')
        return out

    @app.post('/api/drive/list')
    async def list_link(body: ListReq):
        link = _drive.parse_link(body.link)
        if not link:
            err(422, 'E-DRIVE-LINK', 'Not a Google Drive folder or file link.', 'ده مش لينك فولدر أو ملف على Google Drive.')
        d = _client()
        try:
            if link['kind'] == 'folder':
                files = await d.list_folder(link['id'], body.recursive)
            else:
                m = await d.meta(link['id'])
                files = [m] if m else [{'id': link['id'], 'name': link['id'], 'mimeType': {'doc': 'application/vnd.google-apps.document', 'sheet': 'application/vnd.google-apps.spreadsheet',
                                                                                                 'slides': 'application/vnd.google-apps.presentation'}.get(link['native'], 'application/pdf'),
                                        'size': None, 'modified': None, 'kind': 'file', 'usable': True, 'path': link['id'], 'export': None}]
        except _drive.DriveError as e:
            _raise(e)
        return {'link': link, 'mode': d.mode, 'files': files, 'usable': sum(1 for f in files if f['usable'])}

    @app.get('/api/drive/files/{file_id}')
    async def get_file(file_id: str, name: str = None, mime: str = None):
        try:
            fname, data, mt = await _client().fetch(file_id, name, mime)
        except _drive.DriveError as e:
            _raise(e)
        return Response(data, media_type=mt, headers={'Content-Disposition': f'attachment; filename="{fname.encode("ascii", "replace").decode()}"', 'X-Filename': fname.encode('utf-8').hex()})

    @app.post('/api/dossiers/{did}/drive/stage', status_code=201)
    async def stage(did: str, body: StageReq):
        """Read Drive files into the dossier as unplaced documents (the Assistant or the user places them)."""
        st.dossier(did)
        d = _client()
        out = []
        for f in body.files:
            try:
                fname, data, mt = await d.fetch(f.get('id'), f.get('name'), f.get('mime'))
            except _drive.DriveError as e:
                out.append({'id': f.get('id'), 'error': e.en})
                continue
            doc = astorage.stage_document(st, did, fname, data, meta={'from_drive': f.get('id')})
            out.append({'id': f.get('id'), 'doc_id': doc['id'], 'filename': fname, 'bytes': len(data)})
        return out
