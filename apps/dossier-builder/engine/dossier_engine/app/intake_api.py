"""Intake drafts — the new-dossier wizard keeps its work on the server as it goes (fields, the uploaded files, what was read from
them including their readings), so a page refresh, a closed tab or another computer picks up where it stopped. One draft per wizard
run; it stays (and shows in the projects list as a draft) until the dossier is created or the user deletes it. A draft that was
deleted never comes back through a late save: writing to it answers 404."""
import uuid

from fastapi import File, Form, HTTPException, UploadFile
from fastapi.responses import Response


def err(status, code, en, ar):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar})


def install(app, st):
    @app.get('/api/intake/drafts')
    def drafts():
        return st.drafts()

    @app.post('/api/intake/drafts', status_code=201)
    def draft_create(body: dict = None):
        did = uuid.uuid4().hex[:12]
        return st.draft_save(did, (body or {}).get('state') or {})

    @app.get('/api/intake/drafts/{draft_id}')
    def draft_get(draft_id: str):
        d = st.draft_get(draft_id)
        if not d:
            err(404, 'E-DRAFT', 'No such draft.', 'المسودة دي مش موجودة.')
        return d

    @app.put('/api/intake/drafts/{draft_id}')
    def draft_put(draft_id: str, body: dict):
        state = body.get('state') if isinstance(body, dict) else None
        if not isinstance(state, dict):
            err(422, 'E-STATE', 'state must be an object.', 'state لازم يكون كائن.')
        if not st.draft_get(draft_id):
            err(404, 'E-DRAFT', 'No such draft.', 'المسودة دي مش موجودة.')
        return st.draft_save(draft_id, state)

    @app.post('/api/intake/drafts/{draft_id}/files', status_code=201)
    async def draft_add_file(draft_id: str, file: UploadFile = File(...), kind: str = Form(None)):
        data = await file.read()                             # no limit on its size: the machine's own memory is the only one
        if not st.draft_get(draft_id):
            err(404, 'E-DRAFT', 'No such draft.', 'المسودة دي مش موجودة.')
        return st.draft_add_file(draft_id, file.filename, data, kind)

    @app.get('/api/intake/drafts/{draft_id}/files/{filename:path}')
    def draft_file(draft_id: str, filename: str):
        data = st.draft_file(draft_id, filename)
        if data is None:
            err(404, 'E-FILE', 'No such file in the draft.', 'الملف ده مش في المسودة.')
        return Response(data, media_type='application/octet-stream')

    @app.delete('/api/intake/drafts/{draft_id}/files/{filename:path}')
    def draft_remove_file(draft_id: str, filename: str):
        freed = st.draft_remove_file(draft_id, filename)
        return {'ok': True, 'files_removed': freed['files']}

    @app.delete('/api/intake/drafts/{draft_id}')
    def draft_delete(draft_id: str, free: int = 0):
        """`free=1`: the user discarded the draft, so its files leave the disk too (when nothing else uses them)."""
        freed = st.draft_delete(draft_id, free=bool(free))
        return {'ok': True, 'files_removed': freed['files']}
