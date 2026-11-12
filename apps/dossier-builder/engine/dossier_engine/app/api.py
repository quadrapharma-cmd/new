"""HTTP API on localhost (D1). Errors always carry code + en + ar (+ action)."""
import errno, json, shutil, sys, tempfile, time, uuid, zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from fastapi.exception_handlers import http_exception_handler as _default_http_error
from starlette.exceptions import HTTPException as _AnyHTTPError          # what FastAPI itself raises while it reads a request's body
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ..profile import Profile, ProfileError
from ..resolver import resolve
from .. import arabic as _arabic
from .. import packs as _packs
from .. import extract as _extract
from .. import officefiles as _officefiles, imagefiles as _imagefiles
from ..guard import assert_allowed, LockedError
from ..assemble import docs_for
from ..classify import Classifier
from ..variations import Variations
from ..validators import ectd32 as v32, ectd40 as v40, report as vreport
from ..writers import ctd, ectd32, ectd40
from ..writers.ectd32 import WriterError
from ..generate import letters, m3tables
from ..generate.docx_kit import MissingData, to_pdf, find_soffice
from .store import Store, StoreError
from . import exporter

STATIC = Path(__file__).resolve().parents[3] / 'ui'
GEN = {  # kind -> (function, requirement id)
    'annex1': ('annex1', 'M1-01'), 'composition': ('composition_certificate', 'M1-31'),
    'salt': ('salt_calc_letter', 'M1-32'), 'cep_commitment': ('cep_commitment', 'M1-40'),
    'translation': ('translation_declaration', 'M1-10'), 'cover': ('cover_letter', 'M1-43'),
    'tracking': ('tracking_table', 'M1-44'), 'stability_commitment': ('stability_commitment', 'P-16'),
    'justification': ('justification', None),
    'p51': ('m3', 'P-09'), 'p54': ('m3', 'P-11'), 's41': ('m3', 'S-08'), 's44': ('m3', 'S-10'),
}


def err(status, code, en, ar, **extra):
    raise HTTPException(status, detail={'code': code, 'en': en, 'ar': ar, **extra})


class NewDossier(BaseModel):
    name: str
    profile: dict
    product: dict
    envelope: dict = {}
    pack: str | None = None             # the authority's pack …
    country: str | None = None          # … or the country the dossier is for (ISO code): its authority's pack is taken


class ExportReq(BaseModel):
    outputs: list = ['ctd', 'ectd32', 'ectd40']
    acknowledge_provisional: bool = False
    submission: dict = None      # follow-on sequence: {type, unit, mode, description, activity, tracking}


class GenReq(BaseModel):
    data: dict
    ctx: dict = {}
    slot_id: str = None


class OpReq(BaseModel):
    op: str


class ReqReq(BaseModel):
    issuer: str
    lang: str = 'en'
    due_days: int = 21
    company: str = None
    signatory: str = None
    signatory_title: str = None


class _OpenRequest(Request):
    """No limit of the framework's own on an upload: the files of one request (it was 1000), its fields, the size of a text field
    (it was 1 MB: the readings that go with a large batch of documents are longer)."""

    def form(self, **kw):
        return super().form(max_files=float('inf'), max_fields=float('inf'), max_part_size=1 << 40)


class _OpenRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def open_handler(request):
            return await handler(_OpenRequest(request.scope, request.receive))
        return open_handler


def create_app(workspace, auth_enabled=None):
    import os
    from .auth import Auth, install
    st = Store(workspace)
    app = FastAPI(title='Dossier Builder', version='0.2', docs_url=None, redoc_url=None, openapi_url=None)
    app.router.route_class = _OpenRoute                     # before any route is added
    if auth_enabled is None and (os.environ.get('DB_MODE') == 'cloud' or os.environ.get('DB_AUTH') == '1'):
        auth_enabled = True                                  # otherwise None: the workspace's own switch (Users screen) decides, default off
    import secrets
    app.state.internal_token = secrets.token_hex(24)        # in-process calls by the Assistant (never sent to a browser)
    app.state.auth = Auth(workspace, auth_enabled)
    install(app, app.state.auth, st)
    from . import review_api, assistant_api, drive_api, draft_api, intake_api
    review_api.install(app, st)
    assistant_api.install(app, st)
    drive_api.install(app, st)
    draft_api.install(app, st)                           # templates + «make it for me»
    intake_api.install(app, st)                          # the wizard's work in progress, kept on the server

    def _pack_of(pack=None, country=None):
        """The pack a request means: the one it names, else the one of the country it names, else Egypt's."""
        if pack:
            try:
                if st.pack(pack).meta.get('kind') != 'base':
                    return pack
            except (FileNotFoundError, NotADirectoryError, OSError):
                pass
            err(422, 'E-PACK', f'Unknown authority pack {pack}.', 'الهيئة دي مش موجودة في البرنامج.')
        if country:
            m = _packs.for_country(country)
            if m:
                return m['id']
        return 'eda.ctd.nta065.v5'

    def _authority(pack_id, envelope=None):
        """Who a dossier is for, as the page needs it: the authority, the country, what it asks, what can be exported."""
        pk = st.pack(pack_id)
        au, code = pk.authority, ((envelope or {}).get('country') or '').upper() or None
        if not code and len(au['countries']) == 1 and au['countries'][0] != '*':
            code = au['countries'][0]
        from .. import vocab as _vocab
        name = next(({'en': c['en'], 'ar': c['ar']} for c in _vocab.countries() if c['code'] == code), None) if code else None
        return {'pack': pk.id, 'id': au['id'], 'name': au['name'], 'egypt': pk.egypt, 'verified': pk.meta.get('verified', pk.egypt), 'country': code, 'country_name': name,
                'questions': pk.questions, 'note': pk.meta.get('note'), 'matrix': pk.matrix_name(), 'columns': pk.meta.get('columns') or {},
                'title': pk.meta.get('title'), 'sources': pk.meta.get('sources') or [], 'outputs': ['ctd', 'ectd32', 'ectd40'] if pk.egypt else ['ctd']}

    @app.exception_handler(StoreError)
    def _store_err(_, e):
        return JSONResponse(status_code=404 if e.code == 'E-NOT-FOUND' else 422,
                            content={'detail': {'code': e.code, 'en': e.en, 'ar': e.ar, **e.extra}})

    def _memory_answer():
        if sys.platform == 'emscripten':                    # the browser edition: the page's memory, not the machine's
            return JSONResponse(status_code=507, content={'detail': {'code': 'E-MEMORY', 'en': 'A file this large does not fit in the memory the browser gives the page. Close other tabs and try again, split the file, or use the desktop program, which takes it whole.',
                                                                     'ar': 'ملف بالحجم ده أكبر من الذاكرة اللي المتصفح بيديها للصفحة. اقفل تبويبات تانية وجرّب تاني، أو قسّم الملف، أو استخدم برنامج سطح المكتب — بياخده كامل.'}})
        return JSONResponse(status_code=507, content={'detail': {
            'code': 'E-MEMORY', 'en': 'This machine does not have the memory for a file this large. Close other programs or tabs and try again, or split the file.',
            'ar': 'ذاكرة الجهاز ما كفتش لملف بالحجم ده. اقفل برامج أو تبويبات تانية وجرّب تاني، أو قسّم الملف.'}})

    @app.exception_handler(MemoryError)
    async def _no_memory(request, exc):                     # a file larger than what this machine can hold at once: said, not a crash
        return _memory_answer()

    @app.exception_handler(FileNotFoundError)
    async def _file_gone(request, exc):                     # a stored document whose own file is not in the storage: said, with what to do
        if 'blobs' not in str(getattr(exc, 'filename', '') or '').replace('\\', '/').split('/'):
            raise exc                                       # anything else missing is a fault of the program: as it always was
        return JSONResponse(status_code=410, content={'detail': {
            'code': 'E-FILE-GONE', 'en': 'The file itself is no longer in the storage (it was not saved completely, or was removed from the disk). Upload it again.',
            'ar': 'الملف نفسه مش موجود في التخزين (ما اتحفظش كامل، أو اتشال من القرص). ارفعه تاني.'}})

    def _no_room(exc):
        """The answer for a write the machine refused for lack of room — memory, or the disk — else None."""
        if isinstance(exc, MemoryError) or (isinstance(exc, OSError) and exc.errno == errno.ENOMEM):
            return _memory_answer()
        if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
            return JSONResponse(status_code=507, content={'detail': {
                'code': 'E-DISK-FULL', 'en': 'The disk has no room left for this file. Free some space and try again.',
                'ar': 'القرص مفيهوش مساحة للملف ده. فضّي مساحة وجرّب تاني.'}})
        return None

    @app.exception_handler(OSError)
    async def _os_err(request, exc):                        # the disk is full, or (the browser edition) the page's memory is: said in words
        answer = _no_room(exc)
        if answer is None:
            raise exc
        return answer

    @app.exception_handler(_AnyHTTPError)
    async def _http_err(request, exc):                      # the same when the room ran out while the upload's body was being read
        return _no_room(exc.__cause__) or await _default_http_error(request, exc)

    @app.exception_handler(ProfileError)
    def _prof_err(_, e):
        return JSONResponse(status_code=422, content={'detail': {'code': 'E-PROFILE', 'problems': e.problems,
                                                                 'en': str(e), 'ar': '؛ '.join(p['ar'] for p in e.problems)}})

    @app.get('/api/health')
    def health():
        return {'ok': True, 'workspace': str(st.root)}

    VAR = Variations()

    @app.get('/api/variations')
    def var_search(q: str = '', group: str = None, pac: str = None):
        return {'items': VAR.search(q, group, pac), 'groups': sorted({v['group'] for v in VAR.items}),
                'classes': VAR.order, 'source': VAR.meta['sources']}

    @app.post('/api/variations/plan')
    def var_plan(ids: list[str]):
        return VAR.plan(ids)

    @app.get('/api/dossiers')
    def list_dossiers(deleted: int = 0):
        return st.list_dossiers(deleted=bool(deleted))

    def _may_delete(request, for_good=False):
        """The Assistant never deletes a project or a product; with sign-in on, deleting for good is for administrators."""
        role = getattr(request.state, 'role', None)
        if role == 'assistant':
            err(403, 'E-ROLE', 'Deleting a project is for a person, not the Assistant.', 'حذف المشروع لشخص، مش للمساعد.')
        if for_good and role not in (None, 'admin'):
            err(403, 'E-ROLE', 'Only an administrator deletes for good.', 'الحذف النهائي للمدير بس.')

    @app.delete('/api/dossiers/{did}')
    def delete_dossier(did: str, request: Request, permanent: int = 0, confirm: str = ''):
        """A project goes to the trash (it comes back with /restore). `permanent=1` deletes it for good: from the trash, or straight
        away when `confirm` repeats its name."""
        _may_delete(request, bool(permanent))
        if not permanent:
            return st.trash_dossier(did)
        d = st.dossier(did)
        if not d.get('deleted') and confirm.strip() != d['name'].strip():
            err(422, 'E-CONFIRM', 'Type the project\'s name to delete it for good.', 'اكتب اسم المشروع عشان يتحذف نهائيًا.')
        return st.purge_dossier(did)

    @app.post('/api/dossiers/{did}/restore')
    def restore_dossier(did: str, request: Request):
        _may_delete(request)
        return st.restore_dossier(did)

    @app.post('/api/dossiers', status_code=201)
    def new_dossier(body: NewDossier):
        pack, env = _pack_of(body.pack, body.country), dict(body.envelope or {})
        if body.country:
            env['country'] = body.country.strip().upper()
        did = st.create_dossier(body.name, body.profile, body.product, env, pack=pack)
        return {'id': did, 'pack': st.dossier(did)['pack'], **st.board(did)['counts']}

    @app.get('/api/dossiers/{did}')
    def get_dossier(did: str):
        d = st.dossier(did)
        return {**d, 'authority': _authority(d['pack'], d['envelope'])}

    @app.get('/api/authorities')
    def authorities():
        """Who a dossier can be built for: each authority with its countries, its own questions, the sources its Module 1 was written
        from, and whether that is the authority's own text or a general layout. `default`: the pack a country without one gets."""
        if not getattr(app.state, 'authorities', None):
            app.state.authorities = _packs.authorities()
        rest = next((a['pack'] for a in app.state.authorities if '*' in a['countries']), None)
        from .. import vocab as _vocab
        return {'authorities': app.state.authorities, 'default': rest, 'countries': [{k: c[k] for k in ('code', 'en', 'ar')} for c in _vocab.countries()]}

    @app.get('/api/dossiers/{did}/data')
    def get_data(did: str):
        return st.dossier(did)['data']

    @app.put('/api/dossiers/{did}/data')
    def put_data(did: str, data: dict):
        return {'cross': st.set_data(did, data)}

    @app.get('/api/dossiers/{did}/board')
    def board(did: str):
        return st.board(did)

    @app.put('/api/dossiers/{did}/profile')
    def put_profile(did: str, profile: dict):
        return st.update_profile(did, profile)

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/documents', status_code=201)
    async def upload(did: str, slot_id: str, file: UploadFile = File(...), title: str = Form(None),
                     meta: str = Form('{}'), replaces: str = Form(None)):
        """replaces: id of the current document this file supersedes (a new version → «replace» in the next sequence)."""
        data = await file.read()
        if replaces:
            old = st.document(replaces)
            if old['dossier_id'] != did or old['slot_id'] != slot_id or old['state'] != 'current':
                err(422, 'E-REPLACES', 'The replaced document must be a current document of the same section.',
                    'المستند المستبدَل لازم يكون مستند حالي في نفس القسم.')
        m = json.loads(meta or '{}')
        known = m.pop('text', None) if isinstance(m, dict) else None       # the reading the page made of a scan: the kind rule judges the file by it
        return st.add_document(did, slot_id, file.filename, data, title, m, supersede=replaces or None, text=known)

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/references', status_code=201)
    def add_reference(did: str, slot_id: str, body: dict):
        """Register a document that exists elsewhere (company Drive) before its file is uploaded."""
        return st.add_reference(did, slot_id, body.get('title'), body.get('url'), body.get('source') or 'drive',
                                body.get('note'), body.get('ref_id'), body.get('valid_until'))

    @app.put('/api/dossiers/{did}/documents/{doc_id}/validity')
    def set_validity(did: str, doc_id: str, body: dict):
        """Expiry date of a certificate / licence / approval; expired evidence blocks the item."""
        return st.set_validity(did, doc_id, body.get('valid_until'), body.get('issued'), body.get('note'))

    @app.get('/api/dossiers/{did}/documents/{doc_id}/file')
    def get_file(did: str, doc_id: str):
        d = st.document(doc_id)
        if d['meta'].get('external'):
            err(404, 'E-EXTERNAL', 'This is an external reference; open its link.', 'ده مرجع خارجي؛ افتح الرابط بتاعه.')
        path = st.blob_path(d['sha256'])
        with open(path, 'rb') as fh:
            head = fh.read(8)
        mt = 'application/pdf' if head[:5] == b'%PDF-' or d['filename'].lower().endswith('.pdf') else _officefiles.media_type(d['filename'], head)
        return FileResponse(path, filename=d['filename'], media_type=mt)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/move')
    def move_document(did: str, doc_id: str, body: dict):
        """A misfiled document goes to the item it belongs to (new version there, old one withdrawn)."""
        slot_id = (body or {}).get('slot_id')
        if not slot_id:
            err(422, 'E-SLOT', 'slot_id is required.', 'لازم تحدد البند.')
        return st.move_document(did, doc_id, slot_id, (body or {}).get('meta'))

    @app.post('/api/dossiers/{did}/documents/{doc_id}/withdraw')
    def withdraw(did: str, doc_id: str, reason: str = 'user'):
        return st.withdraw(did, doc_id, reason)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/restore')
    def restore(did: str, doc_id: str):
        return st.restore(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/fix')
    def fix(did: str, doc_id: str):
        """Apply the allowed automatic fixes; the result is a new version, the original is kept (superseded)."""
        return st.fix_document(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/ocr-layer', status_code=201)
    async def ocr_layer(did: str, doc_id: str, pages: list[UploadFile] = File(...)):
        """Readable copy of a scan: text-only PDF pages produced by the browser's OCR, laid over the original pages."""
        blobs = [await p.read() for p in pages]
        if not blobs or len(blobs) > 400:
            err(422, 'E-PAGES', 'Send one text-only PDF page per page (1–400).', 'ابعت صفحة PDF نصية لكل صفحة (1–400).')
        if any(b[:4] != b'%PDF' for b in blobs if b):
            err(422, 'E-PAGES', 'Each page must be a PDF.', 'كل صفحة لازم تكون PDF.')
        return st.add_ocr_layer(did, doc_id, blobs, where='browser')

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/request', status_code=201)
    def request_reobtain(did: str, slot_id: str, body: ReqReq):
        """Letter to the issuer + «waiting on third party» status with a due date (02-LOGIC §5.2 🟣)."""
        d = st.dossier(did)
        s = next((x for x in st.board(did)['slots'] if x['slot_id'] == slot_id), None)
        if not s or s['level'] not in ('R', 'O'):
            err(422, 'E-SLOT-INACTIVE', 'This item is not required for this product.', 'البند ده مش مطلوب للمنتج ده.')
        req = next(r for r in st.pack(d['pack']).requirements if r['id'] == s['req_id'])
        problems = []
        for doc in s['documents']:
            problems += [f[body.lang if body.lang in f else 'en'] for f in doc['findings'] if f['severity'] == 'block']
        problems += [f[body.lang if body.lang in f else 'en'] for f in s['cross']]
        last = {}
        for doc in st.documents(did):
            if doc['meta'].get('data', {}).get('signatory'):
                last = doc['meta']['data']
        data = {'issuer': body.issuer, 'document': s['title'][body.lang if body.lang in s['title'] else 'en'],
                'trade_name': d['envelope'].get('invented_name') or d['product'].get('name'), 'problems': problems,
                'acceptance': req.get('acceptance_text'), 'lang': body.lang,
                'company': body.company or d['envelope'].get('applicant'),
                'signatory': body.signatory or last.get('signatory'), 'signatory_title': body.signatory_title or last.get('signatory_title')}
        tmp = Path(tempfile.mkdtemp())
        try:
            try:
                letters.reobtain_request(data, tmp / 'request.docx')
            except MissingData as e:
                err(422, 'E-MISSING-DATA', 'Some data is missing: ' + ', '.join(e.fields), 'فيه بيانات ناقصة: ' + '، '.join(e.fields),
                    request_data=e.fields)
            sha = st.put_blob(to_pdf(tmp / 'request.docx').read_bytes() if find_soffice() else (tmp / 'request.docx').read_bytes())
            st.put_blob((tmp / 'request.docx').read_bytes())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rid = st.open_request(did, slot_id, body.issuer, body.lang, body.due_days, sha, problems)
        return {'request_id': rid, 'letter': f'/api/dossiers/{did}/requests/{rid}/letter', 'problems': problems}

    @app.get('/api/dossiers/{did}/requests')
    def list_requests(did: str, state: str = 'open'):
        return st.requests(did, state)

    @app.get('/api/dossiers/{did}/requests/{rid}/letter')
    def request_letter(did: str, rid: str):
        r = st.db.execute('select letter_sha from request where id=? and dossier_id=?', (rid, did)).fetchone()
        if not r:
            err(404, 'E-NOT-FOUND', 'Request not found.', 'الطلب غير موجود.')
        p = st.blob_path(r['letter_sha'])
        if p.read_bytes()[:4] == b'%PDF':
            return FileResponse(p, media_type='application/pdf', filename='request-letter.pdf')
        return FileResponse(p, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            filename='request-letter.docx')

    @app.post('/api/dossiers/{did}/documents/{doc_id}/ops')
    def op(did: str, doc_id: str, body: OpReq):
        d = st.document(doc_id)
        audit = []
        try:
            assert_allowed(d['doc_class'], body.op, audit)
        except LockedError as e:
            for a in audit:
                st.audit(did, a['event'], doc=doc_id, op=body.op, doc_class=d['doc_class'])
            err(403, 'E-LOCKED', str(e), 'المستند ده دليل من جهة خارجية ومينفعش يتعدّل محتواه؛ اطلبه من مصدره.',
                action='re_obtain')
        except ValueError as e:
            err(422, 'E-OP', str(e), 'عملية غير معروفة.')
        st.audit(did, 'document.op', doc=doc_id, op=body.op)
        return {'allowed': True, 'op': body.op}

    @app.post('/api/dossiers/{did}/generate/{kind}', status_code=201)
    def generate(did: str, kind: str, body: GenReq):
        if kind not in GEN:
            err(404, 'E-GEN', f'Unknown generator {kind}.', 'مولّد غير معروف.')
        fn_name, req_id = GEN[kind]
        slots = [s for s in st.slots(did) if (s.req_id == req_id or (req_id is None and s.slot_id == body.slot_id))
                 and s.active]
        slot = next((s for s in slots if s.slot_id == (body.slot_id or s.slot_id)), None)
        if not slot:
            err(422, 'E-SLOT-INACTIVE', f'{req_id} is not required for this product.', 'البند ده مش مطلوب للمنتج ده.')
        d = st.dossier(did)
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / f'{kind}.docx'
            try:
                if fn_name == 'm3':
                    m3tables.build(kind, d['data'], out, item=slot.item, product_name=d['product'].get('name'))
                elif kind == 'annex1':
                    letters.annex1(body.data, {**d['profile'], **body.ctx}, out)
                else:
                    getattr(letters, fn_name)(body.data, out)
            except MissingData as e:
                err(422, 'E-MISSING-DATA', 'Some data is missing: ' + ', '.join(e.fields),
                    'فيه بيانات ناقصة: ' + '، '.join(e.fields), request_data=e.fields)
            from .store import SIGN_KINDS
            if find_soffice():
                fname, blob = f'{kind}.pdf', to_pdf(out).read_bytes()
            else:                                      # no LibreOffice (browser edition): the Word draft itself, replaced by the PDF the user uploads
                fname, blob = f'{kind}.docx', out.read_bytes()
            doc = st.add_document(did, slot.slot_id, fname, blob, meta={
                'generated': kind, 'draft_unsigned': kind in SIGN_KINDS or fname.endswith('.docx'),
                'draft_docx': fname.endswith('.docx'), 'data': body.data})
            st.put_blob(out.read_bytes())
            return doc
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @app.get('/api/dossiers/{did}/preview')
    def preview(did: str, output: str = 'ectd32'):
        """Publisher view: where every current document will go, per output, without writing anything."""
        if output not in ('ctd', 'ectd32', 'ectd40'):
            err(422, 'E-OUTPUT', 'Unknown output.', 'مخرج غير معروف.')
        d = st.dossier(did)
        if output != 'ctd' and not st.pack(d['pack']).egypt:
            err(422, 'E-OUTPUT-AUTHORITY', "The eCTD package is written for Egypt's regional Module 1 only; this dossier exports as CTD folders.",
                'حزمة الـ eCTD مكتوبة لموديول ١ المصري بس؛ الملف ده بيتصدّر كمجلدات CTD.')
        slots = st.slots(did)
        by_slot = {s.slot_id: s for s in slots}
        files, docmeta = {}, {}
        for s in slots:
            for doc in st.documents(did, s.slot_id) if s.active else []:
                files.setdefault(s.slot_id, []).append({'file': doc['id'], 'title': doc['title'], **doc['meta']})
                docmeta[doc['id']] = doc
        rows = []
        if output == 'ctd':
            plan = ctd.write('/nonexistent', d['name'], slots, files, dry_run=True)
            for sid, paths in plan['plan'].items():
                for f, path in zip(files[sid], paths):
                    rows.append(dict(slot_id=sid, doc_id=f['file'], node=by_slot[sid].ctd, target=by_slot[sid].ctd,
                                     path=f"{plan['root']}/{path}"))
        else:
            prof = Profile.from_dict(d['profile'])
            pr = d['product']
            product = ectd32.Product(pr['name'], pr['dosageform'], pr['manufacturer'], pr.get('indication'))
            p32 = app.state.p32 = getattr(app.state, 'p32', None) or ectd32.Profile32()
            p40 = getattr(app.state, 'p40', None)
            if output == 'ectd40' and p40 is None:
                p40 = app.state.p40 = ectd40.Profile40(v32=p32)
            used = set()
            for s in slots:
                if not s.active:
                    continue
                for f in files.get(s.slot_id, []):
                    one, _ = docs_for([s], prof, {s.slot_id: [f]})
                    if not one:
                        rows.append(dict(slot_id=s.slot_id, doc_id=f['file'], node=None, target=None, path=None,
                                         note='CTD only'))
                        continue
                    doc = one[0]
                    try:
                        if output == 'ectd32':
                            rel = ectd32.rel_path(doc, product, p32)
                            target = p32.m1[doc.node]['element'] if doc.node.startswith('1.') else p32.ich_element(doc.node)
                        else:
                            code, _, spec = p40.cou(doc.node)
                            target = code
                            rel = ectd32.rel_path(doc, product, p32)
                            if doc.node.startswith('1.'):
                                stem = rel.rsplit('/', 1)[1][:-4]
                                rel = f"m1/{f'{doc.pi_type}-{doc.lang}' if doc.node == '1.3.1' else stem}.pdf"
                        n, k = rel, 2
                        while n in used:
                            n = rel[:-4] + f'-{k}.pdf'
                            k += 1
                        used.add(n)
                        rows.append(dict(slot_id=s.slot_id, doc_id=f['file'], node=doc.node, target=target, path=n))
                    except WriterError as e:
                        rows.append(dict(slot_id=s.slot_id, doc_id=f['file'], node=doc.node, target=None, path=None,
                                         note=str(e)))
        for r in rows:
            m = docmeta[r['doc_id']]
            r.update(title=m['title'], filename=m['filename'], version=m['version'], sha256=m['sha256'],
                     check_status=m['check_status'], operation='new', doc_class=m['doc_class'],
                     ctd=by_slot[r['slot_id']].ctd, module=by_slot[r['slot_id']].module,
                     external=m['meta'].get('url') if m['meta'].get('external') else None)
        return {'output': output, 'rows': rows}

    @app.get('/api/generators')
    def generators():
        return {k: {kk: v[kk] for kk in ('req', 'title', 'fields')} for k, v in letters.SCHEMAS.items()}

    @app.get('/api/capabilities')
    def capabilities():
        """What the program can do, counted from the engine itself (rule packs, generators, checks, validators)."""
        import inspect, re
        from .. import crosschecks, fixes
        from .suite import TYPES_FILE
        import yaml
        from dossier_engine.yamlfast import load as yload
        pack = st.pack('eda.ctd.nta065.v5')
        by_module, by_class = {}, {}
        for r in pack.requirements:
            by_module[str(r['module'])] = by_module.get(str(r['module']), 0) + 1
            by_class[r['doc_class']] = by_class.get(r['doc_class'], 0) + 1
        rules40 = sorted(set(re.findall(r"'(eCTD4-[0-9A-Za-z/.-]+)'", inspect.getsource(v40))))
        cross_ids = sorted(set(re.findall(r"'((?:XC|NP040)-[A-Z0-9]+)'", inspect.getsource(crosschecks))))
        doc_types = yload(TYPES_FILE.read_text(encoding='utf-8'))['types']
        from ..assistant import settings as _asettings
        import importlib.util
        return {'version': app.version, 'workspace': str(st.root), 'assistant': _asettings.status(st.root),
                'ocr_server': bool(_arabic.ocr_available() and importlib.util.find_spec('ocrmypdf')),
                'ocr_browser': bool(getattr(app.state, 'ocr_browser', False)), 'drive': __import__('dossier_engine.drive', fromlist=['status']).status(st.root),
                'dossiers': st.db.execute('select count(*) from dossier').fetchone()[0],
                'pack': {'id': pack.id, 'title': pack.meta['title'], 'status': pack.meta['status'],
                         'valid_from': pack.meta['valid_from'], 'sources': pack.meta['sources']},
                'requirements': {'total': len(pack.requirements), 'by_module': by_module, 'by_class': by_class},
                'authorities': [{k: a[k] for k in ('pack', 'id', 'name', 'countries', 'verified', 'requirements', 'outputs')} for a in _packs.authorities()],
                'variations': {'total': len(VAR.items), 'classes': VAR.order, 'source': VAR.meta['sources']},
                'generators': [{'kind': k, 'req': v.get('req'), 'title': v['title']} for k, v in letters.SCHEMAS.items()],
                'checks': {'cross': cross_ids, 'fixes': fixes.ORDER,
                           'pdf': ['EG-PF-16.1', 'EG-PF-16.2', 'EG-PF-16.3', 'EG-PF-16.5', 'EG-PF-15.4', 'EG-BP-E23',
                                   'EG-BP-16.BP1', 'PDF-JS', 'NTA065-N4', 'NTA065-BM', 'ICH-NAME']},
                'validators': {'ectd32': {'automated': len(v32.RULES), 'profile': 'EG eCTD 3.2.2 provisional v0'},
                               'ectd40': {'rules': rules40, 'profile': 'EG eCTD 4.0 provisional v0'}},
                'doc_types': len(doc_types), 'outputs': ['ctd', 'ectd32', 'ectd40'],
                'ai_server': bool(os.environ.get('ANTHROPIC_API_KEY'))}

    from .. import extract as _extract

    @app.post('/api/extract')
    async def extract_files(files: list[UploadFile] = File(...), target: str = 'dossier'):
        """Intake: read uploaded PDFs with the rules and prepare the AI prompt; nothing is stored."""
        pairs = [(f.filename, await f.read()) for f in files]
        r = _extract.read_files(pairs)
        return {'files': [dict(f) for f in r['files']], 'rules': r['rules'],
                'prompt': _extract.ai_prompt(r['files'], target), 'ai_server': bool(os.environ.get('ANTHROPIC_API_KEY'))}

    def _dossier_pdfs(did):
        out = []
        for d in st.documents(did):
            if (d['filename'].lower().endswith(_officefiles.EXTENSIONS) or '.' not in d['filename']) and not d['meta'].get('external'):
                out.append((d['filename'], st.blob_path(d['sha256']).read_bytes(), d['id']))
        return out

    @app.post('/api/dossiers/{did}/extract')
    def extract_dossier(did: str, target: str = 'dossier'):
        """Intake from the documents already in the dossier (the product-data page)."""
        docs = _dossier_pdfs(did)
        r = _extract.read_files([(n, b) for n, b, _ in docs])
        files = [dict({k: v for k, v in f.items() if k != 'text'}, doc_id=d[2]) for f, d in zip(r['files'], docs)]
        return {'files': files, 'rules': r['rules'], 'prompt': _extract.ai_prompt(r['files'], target),
                'ai_server': bool(os.environ.get('ANTHROPIC_API_KEY'))}

    def _ai_read(pairs, target):
        """Claude reads the PDFs themselves (scans included) against the intake schema — the API edition of the
        browser's «sample» layer. Needs ANTHROPIC_API_KEY on this computer."""
        if not os.environ.get('ANTHROPIC_API_KEY'):
            err(501, 'E-NO-AI', 'Set ANTHROPIC_API_KEY on this computer to let Claude read the documents.',
                'اضبط ANTHROPIC_API_KEY على الجهاز ده عشان Claude يقرأ المستندات.')
        import base64
        import anthropic
        r = _extract.read_files(pairs)
        content = [{'type': 'document', 'title': name, 'source': {'type': 'base64', 'media_type': 'application/pdf',
                    'data': base64.standard_b64encode(data).decode()}} for name, data in pairs if data[:4] == b'%PDF']
        for name, data in pairs:                      # photos / scans uploaded as images
            im = _imagefiles.for_model(data)
            if im:
                content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': im[0], 'data': base64.standard_b64encode(im[1]).decode()}})
        content.append({'type': 'text', 'text': _extract.ai_prompt([dict(f, text='(the PDF is attached above)') for f in r['files']], target)})
        client = anthropic.Anthropic()
        with client.beta.messages.stream(model='claude-opus-5-5', max_tokens=16000, output_config={'effort': 'medium'},
                                         betas=['server-side-fallback-2026-07-01'], fallbacks='default',
                                         messages=[{'role': 'user', 'content': content}]) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == 'refusal':
            err(422, 'E-AI-REFUSED', 'Claude declined to read these documents.', 'Claude اعتذر عن قراءة المستندات دي.')
        text = ''.join(b.text for b in msg.content if b.type == 'text')
        try:
            ai = json.loads(text[text.index('{'):text.rindex('}') + 1])
        except ValueError:
            err(502, 'E-AI-JSON', 'Claude did not return the expected JSON.', 'Claude ما رجّعش البيانات بالشكل المتوقع.')
        return {'ai': ai, 'rules': r['rules'], 'files': [dict(f) for f in r['files']]}

    @app.get('/api/vocab')
    def vocab_lists():
        """Dropdown vocabularies (dose forms with routes, countries, units, API options) and the names this workspace already uses."""
        from .. import vocab as _vocab
        return _vocab.payload(st)

    @app.post('/api/archives/unpack')
    def archive_unpack(file: UploadFile = File(...)):
        """A compressed file (ZIP, TAR, GZ everywhere; RAR and 7z where the machine has an unpacker) → the files inside it, in one body
        the page cuts back into files (`archives.frame`). Nothing is stored."""
        from .. import archives as _archives
        try:
            return Response(_archives.frame(_archives.unpack(file.filename or 'archive', file.file.read())), media_type='application/octet-stream')
        except _archives.ArchiveError as e:
            err(422, e.code, e.en, e.ar)

    @app.post('/api/images/pdf')
    async def images_pdf(files: list[UploadFile] = File(...), title: str = Form('')):
        """JPEG pages (decoded by the page: a TIFF's pages, a HEIC photo, a BMP…) → one PDF, each image stored as it came."""
        pages = [await f.read() for f in files]             # every page: a long fax is not cut
        if not pages or any(_imagefiles.image_format(p) != 'jpeg' for p in pages):
            err(422, 'E-IMAGE', 'The pages must be JPEG images.', 'الصفحات لازم تكون صور JPEG.')
        try:
            pdf = _imagefiles.jpegs_pdf(pages, title or None)
        except ValueError as e:
            err(422, 'E-IMAGE', f'A page could not be used ({e}).', 'فيه صفحة ما اتقبلتش.')
        return Response(pdf, media_type='application/pdf')

    @app.post('/api/images/png')
    async def image_png(file: UploadFile = File(...)):
        """An image the browser cannot decode (JPEG 2000, PSD, PCX, PNM…), as PNG — where this machine has Pillow or a converter."""
        png = _imagefiles.to_png(await file.read())
        if not png:
            err(422, 'E-IMAGE', 'This machine cannot open that kind of image either.', 'الجهاز ده كمان مش بيفتح نوع الصورة ده.')
        return Response(png, media_type='image/png')

    @app.post('/api/extract/text')
    def extract_texts(body: dict, target: str = 'dossier'):
        """The rules on texts the browser extracted itself (OCR of scans in the browser): same shape as /api/extract."""
        files = body.get('files') or []
        if not isinstance(files, list) or len(files) > 300:
            err(422, 'E-FILES', 'files must be a list of at most 300 items.', 'files لازم تكون قائمة بحد أقصى 300 عنصر.')
        r = _extract.read_texts([f for f in files if isinstance(f, dict)])
        return {'files': [{k: v for k, v in f.items() if k != 'text'} | {'text': f['text']} for f in r['files']], 'rules': r['rules'],
                'prompt': _extract.ai_prompt(r['files'], target), 'ai_server': bool(os.environ.get('ANTHROPIC_API_KEY'))}

    @app.post('/api/extract/ai')
    async def extract_ai(files: list[UploadFile] = File(...), target: str = 'dossier'):
        return _ai_read([(f.filename, await f.read()) for f in files], target)

    @app.post('/api/dossiers/{did}/extract/ai')
    def extract_dossier_ai(did: str, target: str = 'dossier'):
        return _ai_read([(n, b) for n, b, _ in _dossier_pdfs(did)], target)

    @app.post('/api/profile/preview')
    def profile_preview(profile: dict, pack: str = None, country: str = None):
        """The requirements a profile would produce, before any dossier exists (the wizard's last step). `pack` or `country`: the
        authority the dossier is for; Egypt's when neither is given."""
        pk = st.pack(_pack_of(pack, country))
        prof = Profile.from_dict(profile)
        try:
            prof.validate(pack=pk)
        except ProfileError as e:                       # a wizard without its APIs yet still gets the non-API items
            rest = [p for p in e.problems if p['code'] != 'P-NO-API']
            if rest:
                raise ProfileError(rest)
        slots = [s.to_dict() for s in resolve(prof, pk, validate=False)]
        notes = {r['id']: r['level_note'] for r in pk.requirements if r.get('level_note')}
        for s in slots:
            s['group'] = pk.by_id[s['req_id']].get('group')
            if s['req_id'] in notes:
                s['note'] = notes[s['req_id']]
        gen = {v['req'] for v in letters.SCHEMAS.values() if v.get('req')}
        counts = {k: sum(1 for s in slots if s['level'] == k) for k in ('R', 'O', 'NR', 'NA')}
        by_module = {}
        for s in slots:
            m = by_module.setdefault(str(s['module']), {'R': 0, 'O': 0, 'NR': 0, 'NA': 0})
            m[s['level']] += 1
        col, assumed = prof.column()
        return {'slots': slots, 'counts': counts, 'by_module': by_module, 'column': col, 'column_assumed': assumed and pk.egypt,
                'authority': _authority(pk.id, {'country': country}),
                'generable': [s['slot_id'] for s in slots if s['level'] in ('R', 'O') and s['req_id'] in gen],
                'third_party': [s['slot_id'] for s in slots if s['level'] in ('R', 'O') and
                                s['doc_class'] in ('third_party_certificate', 'eda_document')]}

    @app.get('/api/dossiers/{did}/generate/{kind}/prefill')
    def prefill(did: str, kind: str, slot_id: str = None):
        """What the dossier already knows for this generator — the UI asks only for the rest."""
        if kind not in GEN:
            err(404, 'E-GEN', f'Unknown generator {kind}.', 'مولّد غير معروف.')
        d = st.dossier(did)
        pr, env, prof = d['product'], d['envelope'], d['profile']
        last = {}
        for doc in st.documents(did):
            if doc['meta'].get('generated') == kind and doc['meta'].get('data'):
                last = doc['meta']['data']                           # most recent wins (ordered by created)
        base = {'trade_name': env.get('invented_name') or pr.get('name'), 'dosage_form': pr.get('dosageform'),
                'company': env.get('applicant'), 'applicant': env.get('applicant'), 'tracking': env.get('tracking'),
                'sequence': env.get('sequence', '0000'), 'submission_type': env.get('submission_type', 'maa'),
                'unit': env.get('unit', 'initial'), 'description': env.get('description'),
                'manufacturer': pr.get('manufacturer'), 'indication': pr.get('indication')}
        if kind == 'salt':
            base['apis'] = [{'name_base': n} for n in dict.fromkeys(a['name'] for a in prof.get('apis', []))]
        if kind == 'cep_commitment' and slot_id and '@' in slot_id:
            name, man = slot_id.split('@', 1)[1].split('|', 1)
            base.update(api=name, cep_holder=man)
        if kind == 'tracking':
            seqs = [{'sequence': env.get('sequence', '0000'), 'description': env.get('description') or 'Initial MAA',
                     'type': env.get('submission_type', 'maa'), 'unit': env.get('unit', 'initial'),
                     'tracking': env.get('tracking'), 'status': 'Submitted'}]
            base['sequences'] = seqs
        if kind == 'justification' and slot_id:
            s = next((x for x in st.slots(did) if x.slot_id == slot_id), None)
            if s:
                base.update(section=s.ctd, item=s.title['en'])
        out = {k: v for k, v in {**base, **last}.items() if v not in (None, '', [])}
        keys = {f['key'] for f in letters.SCHEMAS[kind]['fields']}
        return {k: v for k, v in out.items() if k in keys}

    def _suggest_with_kind(clf, slots, filename, text, kind=None, product=None):
        """The classifier's suggestions, with the document kind's home item first (a licence goes to the licence item whatever the keywords say),
        and `auto`: the one item the file may go into without asking. Among the per-API items (CEP, CoA, GMP of each active) the substance
        the document names decides; when two items of different actives tie — the document names neither — nothing is automatic:
        `auto` is None and the file waits in the «not placed yet» box for the user."""
        unread = len(''.join((text or '').split())) < 20 and not kind
        kind = kind or _extract.content_kind(text)
        by_name = False
        if kind == 'other' and _extract.name_hint(filename):                # nothing inside says what it is: the name only hints where to offer it
            kind, by_name = _extract.name_hint(filename), True
        sugg = clf.suggest(filename, text, slots)
        homes = _extract.kind_homes(kind, clf.pack)
        by_id = {s.slot_id: s for s in slots}
        if homes and not any(x['req_id'] in homes for x in sugg):
            cands = sorted((s for s in slots if s.active and s.req_id in homes), key=lambda s: homes.index(s.req_id))
            first = [s for s in cands if s.req_id == cands[0].req_id] if cands else []
            if len(first) == 1:                                                     # the only item of that kind (the licence item, the one API's CEP item)
                sugg.insert(0, {'slot_id': first[0].slot_id, 'req_id': first[0].req_id, 'score': 9, 'why': [f'document kind: {kind}']})
        if homes:
            sugg.sort(key=lambda x: (0 if x['req_id'] in homes else 1, -x['score']))
        if kind == 'coa' and product and not any('substance' in w for x in sugg for w in x['why']):
            # a certificate of analysis that names the product and none of its actives is the finished product's: its batch analyses item
            import re as _re
            word = (_re.findall(r'[a-z\u0600-\u06ff]{4,}', product.lower()) or [None])[0]
            fp = next((x for x in slots if x.active and x.req_id == 'P-11'), None)
            if word and fp and _re.search(r'(?<![a-z])' + _re.escape(word) + r'(?![a-z])', (filename + ' ' + text).lower()):
                sugg = [{'slot_id': fp.slot_id, 'req_id': fp.req_id, 'score': 10, 'why': ['names the product, none of its active substances']}] + \
                       [x for x in sugg if x['slot_id'] != fp.slot_id]
        auto = sugg[0]['slot_id'] if sugg else None
        if len(sugg) > 1:
            a, b = by_id.get(sugg[0]['slot_id']), by_id.get(sugg[1]['slot_id'])
            if a and b and a.item and b.item and sugg[0]['score'] == sugg[1]['score'] and \
                    _extract.api_key(a.item.get('name') or '') != _extract.api_key(b.item.get('name') or ''):
                auto = None                                                         # a tie between two actives: never a guess
        if by_name or unread:
            auto = None                                                             # a file that was not read is offered, never placed on its name
        return kind, sugg, auto

    @app.post('/api/dossiers/{did}/classify/text')
    def classify_text(did: str, body: dict):
        """Suggest a slot for files whose text the page already has (its own OCR of scans): [{filename, text, kind?}] → suggestions."""
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for f in (body or {}).get('files') or []:
            if not isinstance(f, dict):
                continue
            kind, sugg, auto = _suggest_with_kind(clf, slots, f.get('filename') or 'document', f.get('text') or '', f.get('kind'), (d.get('product') or {}).get('name'))
            out.append({'filename': f.get('filename'), 'kind': kind, 'suggestions': sugg, 'auto': auto})
        return out

    @app.get('/api/dossiers/{did}/unplaced')
    def unplaced_list(did: str):
        """Uploaded files that are not in an item yet, each with where the program thinks it belongs."""
        from io import BytesIO
        from pypdf import PdfReader
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for doc in st.board(did)['unassigned']:
            text = ''
            try:
                data = st.blob_path(doc['sha256']).read_bytes()
                rd = PdfReader(BytesIO(data), strict=False)
                text = ' '.join((p.extract_text() or '') for p in rd.pages[:2])
            except Exception:
                pass
            text = text or (doc.get('meta') or {}).get('text') or ''
            kind, sugg, auto = _suggest_with_kind(clf, slots, doc['filename'], text, (doc.get('meta') or {}).get('kind'), (d.get('product') or {}).get('name'))
            out.append({'id': doc['id'], 'filename': doc['filename'], 'kind': kind, 'suggestions': sugg, 'auto': auto, 'created': doc.get('created')})
        return out

    @app.post('/api/dossiers/{did}/unplaced', status_code=201)
    async def unplaced_add(did: str, files: list[UploadFile] = File(...), meta: str = Form('{}')):
        """Keep uploaded files the program could not place: they show on the board as «not placed yet» — nothing uploaded is lost."""
        from ..assistant import storage as _storage
        extra = json.loads(meta or '{}')
        out = []
        for f in files:
            data = await f.read()
            m = {'staged_by': 'user'}
            fx = extra.get(f.filename) if isinstance(extra, dict) else None
            if isinstance(fx, dict):
                m.update({k: fx[k] for k in ('kind', 'text') if fx.get(k)})
            doc = _storage.stage_document(st, did, f.filename, data, meta=m)
            out.append(doc)
        return out

    @app.post('/api/dossiers/{did}/documents/{doc_id}/place')
    def place_document(did: str, doc_id: str, body: dict):
        """An unplaced (or misplaced) document into an item: a new checked version there, the old row withdrawn."""
        slot_id = (body or {}).get('slot_id')
        if not slot_id:
            err(422, 'E-SLOT', 'slot_id is required.', 'لازم تحدد البند.')
        d0 = st.document(doc_id)
        if d0['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if d0['meta'].get('external'):
            err(422, 'E-EXTERNAL', 'An external reference cannot be placed; upload its file.', 'المرجع الخارجي ما ينفعش يتحط؛ ارفع ملفه.')
        data = st.blob_path(d0['sha256']).read_bytes()
        meta = {k: v for k, v in d0['meta'].items() if k not in ('placed_from', 'text')} | {'placed_by': 'user', 'placed_from': d0.get('slot_id')}
        meta |= {k: v for k, v in ((body or {}).get('meta') or {}).items() if k in st.ITEM_META and v}       # the leaflet's type + language, the study
        st.check_item_meta(did, slot_id, meta)
        title = (body or {}).get('title') or d0.get('title')
        if title == d0['filename']:
            title = None                                    # a staged file's title is its file name: the item's own title names it in the dossier
        new = st.add_document(did, slot_id, d0['filename'], data, title, meta, text=d0['meta'].get('text'), kind=d0['meta'].get('kind'))
        if d0['state'] == 'current':
            st.withdraw(did, doc_id, 'placed')
        return new

    @app.post('/api/dossiers/{did}/classify')
    async def classify(did: str, files: list[UploadFile] = File(...)):
        """Suggest a slot for each file (nothing is stored until the user confirms)."""
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for f in files:
            data = await f.read()
            try:                                        # what is written in the file: a PDF's text layer, a Word file (.docx or .doc)
                text = _extract.read_text(f.filename, data, max_pages=2, ocr=False)['text']
            except Exception:
                text = ''
            kind, sugg, auto = _suggest_with_kind(clf, slots, f.filename, text, None, (d.get('product') or {}).get('name'))
            out.append({'filename': f.filename, 'size': len(data), 'kind': kind, 'suggestions': sugg, 'auto': auto})
        return out

    @app.get('/api/dossiers/{did}/gate')
    def gate(did: str):
        return st.gate(did)

    @app.post('/api/dossiers/{did}/export', status_code=201)
    def export(did: str, body: ExportReq):
        p40 = getattr(app.state, 'p40', None) or ectd40.Profile40()
        app.state.p40 = p40
        ig = Path(__file__).resolve().parents[5] / 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
        try:
            return exporter.export(st, did, body.outputs, body.acknowledge_provisional, body.submission, p40, ig)
        except exporter.ExportError as e:
            err(e.status, e.code, e.en, e.ar, **e.extra)

    @app.get('/api/dossiers/{did}/submissions')
    def submissions(did: str):
        return {o: [{k: h[k] for k in ('seq', 'activity', 'envelope', 'created')} | {'documents': len(h['leaves'])}
                    for h in st.history(did, o)] for o in ('ectd32', 'ectd40')}

    @app.get('/api/dossiers/{did}/exports/{exp_id}/{name}')
    def download(did: str, exp_id: str, name: str):
        p = st.root / 'exports' / did / exp_id / name
        if '/' in name or not p.is_file():
            err(404, 'E-NOT-FOUND', 'Export not found.', 'التصدير غير موجود.')
        return FileResponse(p, filename=name)

    @app.get('/api/dossiers/{did}/audit')
    def audit(did: str):
        return [dict(r) | {'detail': json.loads(r['detail'])}
                for r in st.db.execute('select * from audit where dossier_id=? order by id', (did,))]

    from . import suite as _suite
    _suite.install(app, st, err)

    @app.get('/api/activity')
    def activity(limit: int = 300):
        rows = st.db.execute('select id, ts, dossier_id, event, detail, actor from audit order by id desc limit ?',
                             (min(int(limit), 2000),)).fetchall()
        ok, bad_id = st.verify_audit()
        return {'chain_ok': ok, 'first_bad': bad_id,
                'rows': [dict(r) | {'detail': json.loads(r['detail'] or '{}')} for r in rows]}

    import os as _os
    if _os.environ.get('DB_HOME') == 'suite':          # local / company install: open on the product file
        from fastapi.responses import RedirectResponse as _RR

        @app.get('/', include_in_schema=False)
        def _home():
            return _RR('/suite/', status_code=307)

    if STATIC.exists():
        VENDOR = Path(__file__).resolve().parents[3] / 'web' / 'vendor'
        for sub in ('tess', 'pdfjs', 'img'):                   # browser OCR and page rendering (fetched by web/vendor.sh; not in git)
            if (VENDOR / sub).is_dir():
                app.mount(f'/assets/{sub}', StaticFiles(directory=VENDOR / sub), name=f'vendor-{sub}')
        app.state.ocr_browser = (VENDOR / 'tess' / 'tesseract.min.js').exists() and (VENDOR / 'pdfjs' / 'pdf.min.mjs').exists()
        app.mount('/', StaticFiles(directory=STATIC, html=True), name='ui')
    app.state.store = st
    return app
