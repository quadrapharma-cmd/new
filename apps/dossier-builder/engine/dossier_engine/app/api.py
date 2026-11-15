"""HTTP API on localhost (D1). Errors always carry code + en + ar (+ action)."""
import errno, json, re, shutil, sys, tempfile, time, uuid, zipfile
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
from .. import conditions as _conditions
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



def _cd(name, inline=False):
    """Content-Disposition for a file name in any script (Arabic included): an ASCII stand-in and the UTF-8 name (RFC 6266/5987)."""
    from urllib.parse import quote
    ascii_name = ''.join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else '_' for ch in name) or 'file'
    return f"{'inline' if inline else 'attachment'}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}"

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
    outputs: list = ['ctd', 'ectd32', 'ectd40']           # this default means «what the authority has»; 'nees' is asked by name
    acknowledge_provisional: bool = False
    working: bool = False        # a working copy: what is in the dossier now + the list of what is missing, whatever the gate says
    submission: dict = None      # follow-on sequence: {type, unit, mode, description, activity, tracking}
    replace_last: bool = False   # the last sequence was not submitted: this export takes its number (a submitted one never)


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


class _ReadingsOfThisWorkspace:
    """The reader keeps what it read in the workspace's cache folder (extract.read_text). A process may hold more than one
    workspace, so the app that answers a request claims the folder first."""

    def __init__(self, app, store):
        self.app, self.store = app, store

    async def __call__(self, scope, receive, send):
        self.store.claim_readings()
        await self.app(scope, receive, send)


def create_app(workspace, auth_enabled=None):
    import os
    from .auth import Auth, install
    st = Store(workspace)
    app = FastAPI(title='Dossier Builder', version='0.2', docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(_ReadingsOfThisWorkspace, store=st)
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
                'title': pk.meta.get('title'), 'sources': pk.meta.get('sources') or [], 'outputs': pk.outputs_for(code), 'ectd_region': pk.ectd_region,
                'ectd_values': _eu_values() if pk.ectd_region == 'eu' else _gcc_values() if pk.ectd_region == 'gcc' else None}

    def _gcc_values():
        """What the page offers for a Gulf dossier, read from the GCC Module 1 v1.5 DTD: destinations, submission and unit types."""
        from ..writers.ectd32_gcc import default_profile
        v = default_profile().values
        return {'countries': [c for c in v['env_countries'] if c != 'common'], 'submission_types': v['submission_types'], 'units': v['units'],
                'procedures': v['procedures'], 'languages': v['languages']}

    def _eu_values():
        """What the page offers for an EU dossier, read from the EMA's DTD: countries, languages, PI types, submission and unit types."""
        from ..writers.ectd32_eu import default_profile
        v = default_profile().values
        return {k: v[k] for k in ('countries', 'env_countries', 'languages', 'pi_types', 'submission_types', 'units', 'modes')}

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

    from .. import backup as _backup
    app.state.auto_backup = sys.platform != 'emscripten' and os.environ.get('DB_BACKUP', '1') != '0'
    if app.state.auto_backup:                            # a backup of its own every day, the last seven kept (updates list, item 28)
        _backup.start_auto(st.root, lambda: bool(st.list_dossiers()))

    def _backups_admin(request):
        if getattr(request.state, 'role', None) not in (None, 'admin'):
            err(403, 'E-ROLE', 'Backups are for an administrator.', 'النسخ الاحتياطية للمدير بس.')

    def _backup_named(name):
        p = _backup.path_of(st.root, name)
        if not p:
            err(404, 'E-NOT-FOUND', 'No backup with this name.', 'مفيش نسخة احتياطية بالاسم ده.')
        return p

    @app.get('/api/backups')
    def backups(request: Request):
        """The workspace's backups, newest first, and how the automatic one runs."""
        _backups_admin(request)
        return {'items': _backup.listing(st.root), 'auto': app.state.auto_backup, 'every_hours': _backup.EVERY // 3600, 'keep': _backup.KEEP}

    @app.post('/api/backups', status_code=201)
    def backup_now(request: Request):
        _backups_admin(request)
        p = _backup.make(st.root)
        _backup.prune(st.root)
        st.audit(None, 'backup.made', name=p.name, size=p.stat().st_size)
        return {'name': p.name, 'size': p.stat().st_size}

    @app.get('/api/backups/{name}')
    def backup_file(name: str, request: Request):
        _backups_admin(request)
        return FileResponse(_backup_named(name), media_type='application/zip', filename=name)

    @app.post('/api/backups/{name}/drill')
    def backup_drill(name: str, request: Request):
        """The restore drill: the backup opened in a fresh folder as a restore would, and checked."""
        _backups_admin(request)
        r = _backup.drill(_backup_named(name))
        st.audit(None, 'backup.drill', name=name, ok=r['ok'], documents=r['documents'])
        return r

    QUAL = re.compile(r'^qualification-\d{8}-\d{6}\.(docx|json)$')

    @app.post('/api/qualification', status_code=201)
    def qualification_run(request: Request):
        """IQ and OQ run here and now (the OQ in a workspace of its own), with the PQ protocol: the package for the quality unit
        (updates list, item 33)."""
        _backups_admin(request)
        from .. import qualification as _q
        r = _q.package(st, st.root / 'qualification')
        st.audit(None, 'qualification.run', docx=r['docx'], iq=r['summary']['iq'], oq=r['summary']['oq'])
        return r

    @app.get('/api/qualification/{name}')
    def qualification_file(name: str, request: Request):
        _backups_admin(request)
        p = st.root / 'qualification' / name
        if not QUAL.match(name) or not p.is_file():
            err(404, 'E-NOT-FOUND', 'No qualification package with this name.', 'مفيش حزمة تأهيل بالاسم ده.')
        return FileResponse(p, filename=name)

    @app.get('/api/health')
    def health():
        return {'ok': True, 'workspace': str(st.root)}

    VAR = Variations()

    @app.get('/api/countries')
    def countries():
        """The countries table: what each authority takes (CTD, eCTD 3.2.2 / 4.0, NeeS, ACTD), its Module 1 and criteria, and the source
        (updates list, knowledge item 41)."""
        return _packs.countries_table()

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

    class CloneReq(BaseModel):
        country: str
        name: str = None

    @app.post('/api/dossiers/{did}/clone', status_code=201)
    def clone(did: str, body: CloneReq):
        """The same product for another country (updates list, item 21): its profile, product and data, and Modules 2–5 as they are;
        Module 1 is the new authority's own, made in the new dossier."""
        d = st.dossier(did)
        pack = _pack_of(None, body.country)
        env = {k: v for k, v in (d['envelope'] or {}).items() if k in ('applicant', 'invented_name', 'inn')}
        env['country'] = body.country.strip().upper()
        new = st.create_dossier(body.name or f"{d['name']} — {env['country']}", d['profile'], d['product'], env, pack=pack)
        if d['data']:
            st.set_data(new, d['data'])
        r = st.copy_documents(new, did, 'm2-5')
        st.audit(new, 'dossier.cloned', source=did, country=env['country'])
        return {'id': new, 'pack': st.dossier(new)['pack'], 'copied': len(r['copied']), 'not_here': r['not_here']}

    class CopyReq(BaseModel):
        source: str
        scope: str = 'm2-5'

    @app.post('/api/dossiers/{did}/copy-from')
    def copy_from(did: str, body: CopyReq):
        """Documents from another product's dossier (updates list, item 43): Modules 2–5, or only the active substances' sections."""
        return st.copy_documents(did, body.source, body.scope)

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
        if isinstance(m, dict):
            m.pop('text', None)                         # an older page sent its reading along: the file's own text is what counts
        if replaces and isinstance(m, dict):            # the new version keeps what the old one was (a «replace» keeps its attributes)
            for k in st.ITEM_META:
                if not m.get(k) and old['meta'].get(k):
                    m[k] = old['meta'][k]
            title = title or old['title']
        return st.add_document(did, slot_id, file.filename, data, title, m, supersede=replaces or None)

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/withdraw-all')
    def withdraw_all(did: str, slot_id: str):
        """«Close the item»: every current document of it withdrawn at once (a «delete» each in the next sequence)."""
        docs = st.documents(did, slot_id)
        for x in docs:
            st.withdraw(did, x['id'], 'item closed')
        st.audit(did, 'slot.closed', slot=slot_id, documents=[x['id'] for x in docs])
        return {'withdrawn': len(docs)}

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

    @app.post('/api/dossiers/{did}/slots/{slot_id}/attest')
    def attest(did: str, slot_id: str, body: dict):
        """The item's one question — signed and stamped / legalised: {answer: 'yes' | 'no'}."""
        return st.attest(did, slot_id, (body or {}).get('answer'))

    @app.post('/api/dossiers/{did}/documents/{doc_id}/confirm-kind')
    def confirm_kind(did: str, doc_id: str):
        """«It is in the right place»: the kind rule's objection to this file is set aside (recorded in the audit)."""
        return st.confirm_kind(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/withdraw')
    def withdraw(did: str, doc_id: str, reason: str = 'user'):
        return st.withdraw(did, doc_id, reason)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/restore')
    def restore(did: str, doc_id: str):
        return st.restore(did, doc_id)

    class SplitReq(BaseModel):
        starts: list[int]
        kinds: list[str] = []          # what each part is, where it is known (the reading of its pages): its item is suggested from it
        titles: list[str] = []
        by: str = 'person'             # who found the cuts: the person, the rules, the model

    class MergeReq(BaseModel):
        doc_ids: list[str]

    @app.get('/api/dossiers/{did}/documents/{doc_id}/split')
    def split_proposal(did: str, doc_id: str):
        """Where a file that holds several documents would be cut: each page's kind and title, the parts proposed."""
        return st.split_proposal(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/split', status_code=201)
    def split_doc(did: str, doc_id: str, body: SplitReq):
        """Cut the file at the pages where documents start: the parts go to the unplaced box, each with its own reading (and its kind,
        where the cuts came with one)."""
        return st.split_document(did, doc_id, body.starts, body.kinds, body.titles, body.by)

    @app.get('/api/dossiers/{did}/documents/{doc_id}/split-prompt')
    def split_prompt(did: str, doc_id: str):
        """What the page asks claude.ai's model when it shows it a combined file's pages (DBAI.bundle): {pages, prompt}."""
        from .. import pages as _pages
        doc = st.document(doc_id)
        if doc['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        n = _pages.count(st.blob_path(doc['sha256']).read_bytes())
        return {'pages': n, 'prompt': _extract.split_prompt(n, pictures=True)}

    @app.post('/api/dossiers/{did}/documents/{doc_id}/split-check')
    def split_check(did: str, doc_id: str, body: dict):
        """The model's answer made sound (consecutive parts from page 1 to the last, known kinds): {pages, parts, by: 'model'}."""
        from .. import pages as _pages
        doc = st.document(doc_id)
        if doc['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        n = _pages.count(st.blob_path(doc['sha256']).read_bytes())
        return {'pages': n, 'parts': _extract.parse_split((body or {}).get('answer') or {}, n), 'by': 'model'}

    @app.post('/api/dossiers/{did}/documents/{doc_id}/split-by-model')
    def split_by_model(did: str, doc_id: str):
        """Where the documents of a combined file start, as Claude reads its pages (server editions, with the key): the parts proposed,
        nothing cut. → {pages, parts: [{from, to, kind, title}], by: 'model'}"""
        key = _ai_key()
        if not key:
            err(501, 'E-NO-AI', "Save the Anthropic API key (the Assistant's settings) to let Claude read the documents.",
                'سجّل مفتاح Anthropic (من إعدادات المساعد) عشان Claude يقرأ المستندات.')
        doc = st.document(doc_id)
        if doc['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        import base64
        import anthropic
        from ..assistant import settings as _aset
        from .. import pages as _pages
        data = st.blob_path(doc['sha256']).read_bytes()
        n = _pages.count(data)
        pdf = data if len(data) <= 24_000_000 else None
        if pdf is None:
            err(413, 'E-TOO-BIG', 'Too large to send whole to the model: cut it by hand.', 'كبير قوي إنه يتبعت كله للموديل: قسّمه بإيدك.')
        client = anthropic.Anthropic(api_key=key)
        with client.beta.messages.stream(model=_aset.load(st.root).get('model') or 'claude-opus-5-5', max_tokens=8000, output_config={'effort': 'medium'},
                                         betas=['server-side-fallback-2026-07-01'], fallbacks='default',
                                         messages=[{'role': 'user', 'content': [
                                             {'type': 'document', 'title': doc['filename'], 'source': {'type': 'base64', 'media_type': 'application/pdf',
                                                                                                     'data': base64.standard_b64encode(pdf).decode()}},
                                             {'type': 'text', 'text': _extract.split_prompt(n)}]}]) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == 'refusal':
            err(422, 'E-AI-REFUSED', 'Claude declined to read this file.', 'Claude اعتذر عن قراءة الملف ده.')
        text = ''.join(b.text for b in msg.content if b.type == 'text')
        try:
            parts = _extract.parse_split(json.loads(text[text.index('{'):text.rindex('}') + 1]), n)
        except ValueError:
            err(502, 'E-AI-JSON', 'Claude did not return the expected JSON.', 'Claude ما رجّعش البيانات بالشكل المتوقع.')
        return {'pages': n, 'parts': parts, 'by': 'model'}

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/merge', status_code=201)
    def merge_docs(did: str, slot_id: str, body: MergeReq):
        """Join the item's PDFs into one document, in the order given."""
        return st.merge_documents(did, slot_id, body.doc_ids)

    class RefReq(BaseModel):
        seq: str
        href: str
        output: str = 'ectd32'

    @app.post('/api/dossiers/{did}/slots/{slot_id:path}/reference', status_code=201)
    def reference(did: str, slot_id: str, body: RefReq):
        """The item's document from an earlier submitted sequence: referred to there, not sent again (updates list, item 22)."""
        return st.reference_document(did, slot_id, body.output, body.seq, body.href)

    @app.get('/api/dossiers/{did}/views')
    def views(did: str, output: str = 'ectd32'):
        """The submitted dossier four ways: cumulative, by sequence, by activity, by study (updates list, item 23)."""
        if output not in ('ectd32', 'ectd40'):
            err(422, 'E-OUTPUT', 'ectd32 or ectd40.', 'ectd32 أو ectd40.')
        return st.views(did, output)

    @app.get('/api/pdf-engine')
    def pdf_engine():
        """Which engine reads and changes the PDFs here: PdfCraft (desktop and company editions) or pypdf (the browser edition)."""
        from .. import pdfcraft as _pdfcraft
        return _pdfcraft.status()

    @app.get('/api/dossiers/{did}/documents/{doc_id}/pages/{page}.png')
    def page_png(did: str, doc_id: str, page: int, dpi: int = 96):
        """One page of a document drawn as a picture (PdfCraft) — the viewer."""
        return Response(st.page_image(did, doc_id, page, dpi), media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})

    @app.get('/api/dossiers/{did}/documents/{doc_id}/find')
    def find_in_doc(did: str, doc_id: str, q: str = ''):
        """Where a phrase is in one document: page and rectangles, to light it up on the page (PdfCraft)."""
        return st.find_in_document(did, doc_id, q)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/redact', status_code=201)
    def redact_doc(did: str, doc_id: str, body: dict):
        """Real redaction of words or phrases in a company document (PdfCraft removes them for good and checks nothing readable is left):
        a new version."""
        return st.pdf_operation(did, doc_id, 'redact', words=list(body.get('words') or []))

    @app.post('/api/dossiers/{did}/documents/{doc_id}/pages', status_code=201)
    def pages_op(did: str, doc_id: str, body: dict):
        """Turn (every document), remove or move (the company's own) pages: {op: rotate|delete|move, pages: [..], degrees, to}."""
        return st.page_operation(did, doc_id, str(body.get('op') or ''), body.get('pages') or [], body.get('degrees', 90), body.get('to'))

    @app.get('/api/dossiers/{did}/documents/{doc_id}/notes.pdf')
    def notes_pdf(did: str, doc_id: str):
        """The document with the team's notes as PDF comments on their pages — for reading or a review, never filed."""
        data, name = st.notes_copy(did, doc_id)
        stem = name.rsplit('.', 1)[0] if '.' in name else name
        return Response(data, media_type='application/pdf', headers={'Content-Disposition': _cd(f'{stem} (notes).pdf')})

    @app.post('/api/dossiers/{did}/documents/{doc_id}/reduce', status_code=201)
    def reduce_doc(did: str, doc_id: str):
        """A smaller file (PdfCraft: images above 225 ppi brought to 150 ppi): a new version, when it is smaller."""
        return st.pdf_operation(did, doc_id, 'reduce_size')

    @app.post('/api/dossiers/{did}/documents/{doc_id}/sign', status_code=201)
    async def sign_doc(did: str, doc_id: str, p12: UploadFile = File(...), password: str = Form(''), reason: str = Form(''),
                       location: str = Form('')):
        """EU only: sign a company document with the person's own digital ID (.p12/.pfx), used for this call and never kept."""
        return st.pdf_operation(did, doc_id, 'sign', p12=await p12.read(), password=password, reason=reason, location=location)

    @app.get('/api/dossiers/{did}/single.pdf')
    def single_pdf(did: str, module: int = None, watermark: str = None):
        """The whole dossier (or one module) as one PDF for a review or for printing, with a bookmark for every module, item and
        document (updates list, item 38)."""
        from .. import pages as _pages
        d = st.dossier(did)
        parts, left = [], []
        for s in sorted((x for x in st.slots(did) if x.active and (module is None or x.module == module)), key=lambda x: (x.module, _sec_key(x.ctd))):
            for doc in st.documents(did, s.slot_id):
                if doc['meta'].get('external'):
                    continue
                data = st.blob_path(doc['sha256']).read_bytes()
                if data[:5] != b'%PDF-':
                    left.append(f"{s.ctd} {doc['filename']}")
                    continue
                parts.append((f'Module {s.module}', f"{s.ctd} {s.title['en']}"[:120], doc['title'] or doc['filename'], data))
        if not parts:
            err(404, 'E-EMPTY', 'No PDF documents there yet.', 'مفيش مستندات PDF هنا لسه.')
        title = f"{d['name']} — " + (f'Module {module}' if module else 'the whole dossier')
        out = _pages.bound(parts, title, left)
        if watermark:                                    # a reading copy that says so on every page (PdfCraft)
            from .. import pdfcraft as _pdfcraft
            if _pdfcraft.available():
                out = _pdfcraft.watermark(out, watermark[:80]) or out
        name = re.sub(r'[^\w.-]+', '_', d['name'])[:60] + (f'-module-{module}' if module else '-dossier') + '.pdf'
        return Response(out, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="{name}"'})

    def _sec_key(sec):
        return [int(x) if x.isdigit() else x for x in re.split(r'[.\s–-]+', str(sec).split(' (')[0]) if x]

    @app.get('/api/dossiers/{did}/documents/{doc_id}/comments')
    def comments(did: str, doc_id: str):
        return st.comments(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/comments', status_code=201)
    def add_comment(did: str, doc_id: str, body: dict):
        """A note on the document for the team's own review (its page when given)."""
        return st.add_comment(did, doc_id, body.get('text'), body.get('page'))

    @app.put('/api/dossiers/{did}/comments/{cid}')
    def resolve_comment(did: str, cid: str, body: dict):
        return st.resolve_comment(did, cid, bool(body.get('resolved', True)))

    @app.get('/api/dossiers/{did}/documents/{doc_id}/compare')
    def compare_versions(did: str, doc_id: str, against: str = None):
        """What changed from the version this document replaced (or `against`): removed and added lines with their pages."""
        return st.compare_versions(did, doc_id, against)

    @app.get('/api/dossiers/{did}/documents/{doc_id}/compare.pdf')
    def compare_marked(did: str, doc_id: str, against: str = None):
        """The newer version with the changes marked on its pages (PdfCraft)."""
        data, name = st.compare_marked(did, doc_id, against)
        stem = name.rsplit('.', 1)[0] if '.' in name else name
        return Response(data, media_type='application/pdf', headers={'Content-Disposition': _cd(f'{stem} (changes).pdf', inline=True)})

    @app.get('/api/dossiers/{did}/search')
    def search_docs(did: str, q: str = '', budget: float = 6.0):
        """Search the text of every document of the dossier (a batch number, a study, «Table 3»): the item, the file, the page."""
        st.dossier(did)
        return st.search(did, q, max(0.5, min(budget, 20.0)))

    @app.post('/api/dossiers/{did}/documents/{doc_id}/pdf', status_code=201)
    def to_pdf_doc(did: str, doc_id: str):
        """Word / Excel / PowerPoint / text → its PDF, on a computer with LibreOffice (a new version; 1.1.9's leaflet gets it beside)."""
        return st.pdf_of_document(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/fix')
    def fix(did: str, doc_id: str):
        """Apply the allowed automatic fixes; the result is a new version, the original is kept (superseded)."""
        return st.fix_document(did, doc_id)

    @app.get('/api/dossiers/{did}/documents/{doc_id}/export.docx')
    def export_word(did: str, doc_id: str):
        """«As Word»: an editable Word copy of a stored PDF (PdfCraft's PDF → Word), to amend a document that exists only as a PDF;
        the stored document is not changed."""
        from .. import pdfcraft as _pc
        d = st.document(doc_id)
        if d['dossier_id'] != did or d['meta'].get('external'):
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        if not _pc.available():
            err(409, 'E-PDFCRAFT', 'This needs PdfCraft, which is not ready here yet.', 'ده محتاج PdfCraft، ولسه مش جاهز هنا.')
        data = st.blob_path(d['sha256']).read_bytes()
        if data[:5] != b'%PDF-':
            err(422, 'E-NOT-PDF', 'Only a PDF is turned into Word.', 'الـ PDF بس هو اللي بيتحوّل لـ Word.')
        try:
            docx = _pc.to_word(data)
        except _pc.PdfCraftError as e:
            err(422, 'E-WORD', f'It could not be turned into Word: {e}'[:300], 'ما اتحوّلش لـ Word.')
        if not docx:
            err(422, 'E-WORD', 'It could not be turned into Word.', 'ما اتحوّلش لـ Word.')
        stem = d['filename'].rsplit('.', 1)[0] if '.' in d['filename'] else d['filename']
        from urllib.parse import quote
        return Response(docx, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(stem)}.docx"})

    @app.post('/api/dossiers/{did}/documents/{doc_id}/split-size')
    def split_size(did: str, doc_id: str):
        """A file over 100 MB cut into parts that fit, in the same item (the original withdrawn, kept in the history)."""
        return st.split_large(did, doc_id)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/improve')
    def improve(did: str, doc_id: str):
        """«Improve the file» (PdfCraft's optimizer): a smaller, cleaner new version when it clearly is, the pages the same."""
        return st.improve_document(did, doc_id)

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
        pk = st.pack(d['pack'])
        if output not in pk.outputs:
            err(422, 'E-OUTPUT-AUTHORITY', "The eCTD package is written for Egypt's and the EU's Module 1 (eCTD 4.0 for Egypt only); "
                "this dossier exports as " + ' and '.join(pk.outputs) + '.',
                'حزمة الـ eCTD مكتوبة لموديول ١ المصري والأوروبي بس (والـ 4.0 لمصر بس)؛ الملف ده بيتصدّر كـ ' + ' و'.join(pk.outputs) + '.')
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
            eu = None
            if pk.ectd_region == 'eu':
                from ..writers import ectd32_eu
                from .exporter import eu_countries
                proc, cs = eu_countries(d, prof, None, st.history(did, 'ectd32'))
                peu = ectd32_eu.default_profile()
                eu = (ectd32_eu, peu, ectd32_eu.EnvelopeEU(identifier='', procedure=proc, countries=cs or ['common'], submission_type='maa',
                                                          unit='initial', applicant='', invented_names=[''],
                                                          legal_basis=(prof.extra or {}).get('eu_legal_basis')))
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
                        if output == 'ectd32' and pk.ectd_region == 'gcc':      # the Gulf: GCC Module 1 v1.5 folders and names
                            from ..writers import ectd32_gcc as _g
                            pg = _g.default_profile()
                            eg_ = _g.EnvelopeGCC(countries=[((d.get('envelope') or {}).get('country') or 'sa').lower()], application=[], applicant='',
                                                 submission_type='new-gen', unit='initial', procedure='national', invented_names=[''])
                            rel = _g.rel_path(doc, eg_, product, pg)
                            target = pg.m1[doc.node]['element'] if doc.node in pg.m1 else pg.ich_element(doc.node)
                        elif output == 'ectd32' and eu:
                            mod, peu, e = eu
                            doc = mod.resolve([doc], e, peu)[0]
                            if doc.node in peu.m1:
                                rel, target = mod.m1_rel_path(doc, e, peu), peu.m1[doc.node]['element']
                            else:
                                rel, target = mod.m25_rel_path(doc, product, peu), peu.ich_element(doc.node)
                        elif output == 'ectd32':
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
        from ..validators import ectd32_eu as _v32eu
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
        from .. import pdfcraft as _pdfcraft
        return {'version': app.version, 'workspace': str(st.root), 'assistant': _asettings.status(st.root), 'pdf_engine': _pdfcraft.status(),
                'drive': __import__('dossier_engine.drive', fromlist=['status']).status(st.root),
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
                               'ectd32_eu': {'automated': len(_v32eu.RULES) + len(_v32eu.SAME), 'criteria': 111,
                                             'profile': 'EU Module 1 v3.1.1 + EU eCTD validation criteria v8.2'},
                               'ectd40': {'rules': rules40, 'profile': 'EG eCTD 4.0 provisional v0'}},
                'doc_types': len(doc_types), 'outputs': ['ctd', 'ectd32', 'ectd40'], 'office_pdf': bool(find_soffice()),
                'ai_server': bool(_ai_key())}

    from .. import extract as _extract

    @app.post('/api/extract')
    async def extract_files(files: list[UploadFile] = File(...), target: str = 'dossier'):
        """Intake: read uploaded PDFs with the rules and prepare the AI prompt; nothing is stored."""
        pairs = [(f.filename, await f.read()) for f in files]
        r = _extract.read_files(pairs)
        return {'files': [dict(f) for f in r['files']], 'rules': r['rules'],
                'prompt': _extract.ai_prompt(r['files'], target), 'ai_server': bool(_ai_key())}

    @app.post('/api/ocr/check')
    async def ocr_check(file: UploadFile = File(...)):
        """For the browser edition's scan reader (ui/assets/ocr.js, called by web/boot.js before a file reaches the engine): whether the
        file is a scan or an image (why), whether this engine reads scans itself (here), its pages, and how many pages of it the page
        has read already. Nothing is stored."""
        from .. import pdfcraft as _pc
        data = await file.read()
        why = _extract.has_text(file.filename, data)
        sha = _extract._sha(data)
        rec = _extract.browser_reading(sha)
        return {'sha256': sha, 'why': why, 'here': bool(_pc.ocr_info()), 'read': len(rec['texts']) if rec else 0,
                'pages': _extract.read_text(file.filename, data).get('pages') or 0}

    @app.post('/api/ocr/browser')
    def ocr_browser(body: dict = None):
        """What the page read from a scan (the browser edition: the same reading as the desktop's, in the browser), kept for the file's
        SHA-256: {sha256, texts: [one per page], rep: as pdfcraft.ocr's report, tag}. Refused where this engine reads scans itself."""
        from .. import pdfcraft as _pc
        if _pc.ocr_info():
            err(409, 'E-OCR-HERE', 'This program reads scans itself.', 'البرنامج ده بيقرا الملفات الممسوحة بنفسه.')
        body = body or {}
        try:
            rec = _extract.keep_browser_reading(str(body.get('sha256') or '').lower(), body.get('texts'), body.get('rep'), body.get('tag'),
                                                body.get('layout'))
        except ValueError as e:
            err(422, 'E-OCR-READING', f'Not a reading of a scan: {e}.', f'دي مش قراية ملف ممسوح: {e}.')
        return {'kept': True, 'pages': len(rec['texts']), 'tag': rec['tag']}

    @app.get('/api/ocr/document/{did}/{doc_id}')
    def ocr_document(did: str, doc_id: str):
        """Before a fix in the browser edition (web/boot.js): whether a stored document is a scan, how many pages it has and how many
        of them the page has read with their words' places (the «make searchable» fix writes those words under the pages)."""
        from .. import pdfcraft as _pc
        d = st.document(doc_id)
        if d['dossier_id'] != did or d['meta'].get('external'):
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        data = st.blob_path(d['sha256']).read_bytes()
        rec = _extract.browser_reading(d['sha256'])
        return {'sha256': d['sha256'], 'why': _extract.has_text(d['filename'], data), 'here': bool(_pc.ocr_info()),
                'pages': _extract.page_count(d['filename'], data), 'read': len(rec['texts']) if rec else 0,
                'layout': bool(rec and rec.get('layout')), 'filename': d['filename'], 'url': f'/api/dossiers/{did}/documents/{doc_id}/file'}

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
                'ai_server': bool(_ai_key())}

    def _ai_key():
        """The Anthropic key this edition reads with: the environment's, or the one saved in the Assistant's settings (on this
        computer, mode 0600). None in the browser edition, where claude.ai's own model reads in the page (DBAI)."""
        if sys.platform == 'emscripten':
            return None
        from ..assistant import settings as _aset
        return _aset.api_key(st.root)

    def _for_model(name, data):
        """A PDF as the model takes it: whole up to 24 MB (the API takes 32 MB a request, base64 included); a larger one — a long
        scan — its first 20 pages, where a document's kind and its information are."""
        if len(data) <= 24_000_000:
            return data
        try:
            from .. import pdfcraft as _pc
            return _pc.split(data, [(1, min(20, max(1, _pc.page_count(data))))])[0]
        except Exception:
            return None

    def _ai_read(pairs, target):
        """Claude reads the PDFs themselves (scans included: the API reads each page as an image too) against the intake schema —
        the server editions' side of the browser's «sample» layer. Needs an Anthropic key on this computer (the environment, or the
        Assistant's settings)."""
        key = _ai_key()
        if not key:
            err(501, 'E-NO-AI', "Save the Anthropic API key (the Assistant's settings) to let Claude read the documents.",
                'سجّل مفتاح Anthropic (من إعدادات المساعد) عشان Claude يقرأ المستندات.')
        import base64
        import anthropic
        from ..assistant import settings as _aset
        r = _extract.read_files(pairs)
        content = []
        for name, data in pairs:
            if data[:4] != b'%PDF':
                continue
            pdf = _for_model(name, data)
            if pdf:
                content.append({'type': 'document', 'title': name, 'source': {'type': 'base64', 'media_type': 'application/pdf',
                                'data': base64.standard_b64encode(pdf).decode()}})
        for name, data in pairs:                      # photos / scans uploaded as images
            im = _imagefiles.for_model(data)
            if im:
                content.append({'type': 'image', 'source': {'type': 'base64', 'media_type': im[0], 'data': base64.standard_b64encode(im[1]).decode()}})
        content.append({'type': 'text', 'text': _extract.ai_prompt([dict(f, text='(the PDF is attached above)') for f in r['files']], target)})
        client = anthropic.Anthropic(api_key=key)
        with client.beta.messages.stream(model=_aset.load(st.root).get('model') or 'claude-opus-5-5', max_tokens=16000,
                                         output_config={'effort': 'medium'}, betas=['server-side-fallback-2026-07-01'], fallbacks='default',
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

    @app.post('/api/extract/text')
    def extract_texts(body: dict, target: str = 'dossier'):
        """The rules on texts already read (the page sends back what /api/extract gave it, to merge again without reading the files
        again): same shape as /api/extract."""
        files = body.get('files') or []
        if not isinstance(files, list) or len(files) > 300:
            err(422, 'E-FILES', 'files must be a list of at most 300 items.', 'files لازم تكون قائمة بحد أقصى 300 عنصر.')
        r = _extract.read_texts([f for f in files if isinstance(f, dict)])
        return {'files': [{k: v for k, v in f.items() if k != 'text'} | {'text': f['text']} for f in r['files']], 'rules': r['rules'],
                'prompt': _extract.ai_prompt(r['files'], target), 'ai_server': bool(_ai_key())}

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

    def _package_files(name, data):
        from .. import archives as _arch
        from ..validators.package import PackageError
        try:
            return _arch.unpack(name, data, depth=2)['files']
        except _arch.ArchiveError as e:
            raise PackageError(e.code, e.en, e.ar)

    @app.exception_handler(__import__('dossier_engine.validators.package', fromlist=['PackageError']).PackageError)
    def _package_err(_, e):
        return JSONResponse(status_code=422, content={'detail': {'code': e.code, 'en': e.en, 'ar': e.ar}})

    @app.post('/api/package/validate')
    async def package_validate(file: UploadFile = File(...)):
        """Check an eCTD package made anywhere (a ZIP of one sequence or several): each sequence by its region's validator, or the ICH
        checks where the program has no region criteria (updates list, item 18)."""
        from ..validators import package as _pkg
        data = await file.read()
        return _pkg.validate_files(_package_files(file.filename, data), file.filename)

    @app.get('/api/dossiers/{did}/metadata-sheet.csv')
    def metadata_sheet(did: str):
        """The sheet of the dossier's documents (file, item, title, attributes) to fill in Excel and upload again (updates list, item 47)."""
        from .. import sheet as _sheet
        st.dossier(did)
        return Response(('\ufeff' + _sheet.template(st, did)).encode('utf-8'), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="documents-sheet.csv"'})

    @app.post('/api/dossiers/{did}/metadata-sheet')
    async def metadata_sheet_apply(did: str, file: UploadFile = File(...), apply: int = 0):
        """What the filled sheet would do, row by row; with apply=1 it is done (the rows that cannot be done are left as they are)."""
        from .. import sheet as _sheet
        st.dossier(did)
        rows = _sheet.parse(file.filename, await file.read())
        if not rows:
            err(422, 'E-SHEET', 'The sheet has no rows under its header (file, item, title, pi_type, lang, study, doc_type, eu_country).',
                'الشيت مفيهوش صفوف تحت العناوين (file، item، title، pi_type، lang، study، doc_type، eu_country).')
        steps = _sheet.plan(st, did, rows)
        out = {'plan': steps, 'counts': {a: sum(1 for p in steps if p['action'] == a) for a in ('place', 'move', 'update', 'none', 'error')}}
        if apply:
            out['done'] = _sheet.apply(st, did, steps)
            st.audit(did, 'sheet.applied', rows=len(rows), done=len(out['done']))
        return out

    @app.post('/api/dossiers/{did}/import-ectd', status_code=201)
    async def import_ectd(did: str, file: UploadFile = File(...)):
        """An application's earlier eCTD sequences (a ZIP) into this dossier: documents into their items, the sequences into its
        submitted history, so the next sequence continues the lifecycle (updates list, item 24)."""
        st.dossier(did)
        return st.import_ectd(did, _package_files(file.filename, await file.read()))

    @app.post('/api/package/compare')
    async def package_compare(a: UploadFile = File(...), b: UploadFile = File(...)):
        """What changed from package A to package B (e.g. what we made and what the consultant delivered), sequence by sequence."""
        from ..validators import package as _pkg
        return _pkg.compare_files(_package_files(a.filename, await a.read()), _package_files(b.filename, await b.read()))

    @app.get('/api/rules')
    def rules():
        """Every rule the program checks — its source, version and status (in force / draft / policy) and where it runs — and the
        official texts behind them with their SHA-256 (updates list, item 20)."""
        from .. import rules_catalogue
        return rules_catalogue.catalogue()

    @app.get('/api/conditions')
    def conditions(pack: str = None, country: str = None):
        """What each document must be before it is uploaded — its form and its content — for every item of the authority's pack
        (`items`), and for the item each kind of base document goes to (`kinds`, the wizard's document cards)."""
        pk = st.pack(_pack_of(pack, country))
        return {'pack': pk.id, 'items': {r['id']: _conditions.for_requirement(r, pk) for r in pk.requirements},
                'kinds': {k: _conditions.for_kinds(pk, [k]) for k in _extract.KIND_HOME}}

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
        for doc in st.documents(did):                                 # who signs is asked once: any document already generated remembers it
            data0 = doc['meta'].get('data') or {}
            for k in ('signatory', 'signatory_title'):
                if data0.get(k):
                    base[k] = data0[k]
        for k in ('signatory', 'signatory_title'):
            if env.get(k):
                base[k] = env[k]
        data, reg = d.get('data') or {}, (d.get('data') or {}).get('registration') or {}
        if kind == 'stability_commitment':                            # what the licence already said
            base.update(shelf_life=reg.get('shelf_life'), containers=(reg.get('packs') or [None])[0],
                        strengths=' + '.join(f"{a.get('name')} {a.get('strength')}" for a in (data.get('apis') or []) if a.get('strength')) or None)
        if kind == 'composition' and len(data.get('composition') or []) >= 2:
            def mg(v):
                m = re.match(r'\s*([\d.,]+)\s*(mg|g|gm|mcg|µg)\b', str(v or ''), re.I)
                if not m:
                    return None
                x = float(m.group(1).replace(',', ''))
                return round(x * {'mg': 1, 'g': 1000, 'gm': 1000, 'mcg': 0.001, 'µg': 0.001}[m.group(2).lower()], 4)
            base['components'] = [{'name': c.get('name'), 'function': c.get('function') or c.get('role') or '', 'qty_mg': mg(c.get('amount')), 'standard': c.get('standard') or ''}
                                  for c in data['composition'] if c.get('name')]
        if kind == 'salt':
            base['apis'] = salt_rows(prof.get('apis', []), data)
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

    def salt_rows(apis, data):
        """One row per substance declared as a salt or hydrate (neomycin sulphate, bacitracin zinc, cysteine hydrochloride) — not for a
        substance that is not one (glycine), nor for one that is itself a salt with no base (sodium chloride): its full name, its base
        and the strength the dossier's data gives (mg)."""
        salt_words = {w for w in _extract.API_SALTS if w not in ('usp', 'bp', 'ep', 'ph', 'eur', 'micronized', 'micronised', 'base', 'anhydrous')}
        strength = {}
        for a in (data.get('apis') or []):
            if a.get('name') and a.get('strength'):
                strength[_extract.api_key(a['name'])] = a['strength']
        for c in (data.get('composition') or []):
            if c.get('name') and (c.get('amount') or c.get('qty')):
                strength.setdefault(_extract.api_key(c['name']), c.get('amount') or c.get('qty'))
        rows = []
        for name in dict.fromkeys(a['name'] for a in apis if a.get('name')):
            words = re.findall(r'[a-z]+', name.lower())
            if not set(words) & salt_words or _extract._salt_substance([w for w in words if w not in _extract.API_STOP]):
                continue
            row = {'name_salt': name, 'name_base': _extract.api_key(name).title()}
            m = re.match(r'\s*([\d.,]+)\s*(mg|g|gm|mcg|µg)\b', str(strength.get(_extract.api_key(name)) or ''), re.I)
            if m:
                x = float(m.group(1).replace(',', ''))
                row['label_claim_mg'] = round(x * {'mg': 1, 'g': 1000, 'gm': 1000, 'mcg': 0.001, 'µg': 0.001}[m.group(2).lower()], 4)
            rows.append(row)
        return rows

    def _suggest_with_kind(clf, slots, filename, text, kind=None, product=None, fpp=None):
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
        makers = [s.item.get('manufacturer') for s in slots if s.item and s.item.get('manufacturer')]
        homes = _extract.kind_homes(kind, clf.pack, text, product,      # the likeliest first: by what the document is about, not only its kind
                                    substances=[_extract.api_key(s.item.get('name') or '') for s in slots if s.item], fpp=fpp, makers=makers)
        kn = _extract.KIND_NAMES.get(kind) or {'en': kind, 'ar': kind}
        said = {'en': f"it reads as a {kn['en']}", 'ar': f"شكله {kn['ar']}"}
        by_id = {s.slot_id: s for s in slots}
        if kind in _extract.KIND_HOME and not any(s.active and s.req_id in homes for s in slots):
            return kind, [], None          # recognised, and this dossier has no item for it (a sampling form; a variation approval in a new
                                           # registration): nothing else is offered in its place — the user decides, or removes it
        decided = unsure = False                                         # decided: the document names the active substance its item is for
        if kind == 'gmp' and (fpp or makers) and _extract.gmp_whose(text, fpp, makers) is None:
            unsure = True                                                # it names neither the product's manufacturer nor an API's: offered, never placed
        for req in homes:                                                # the kind's own item leads, whatever the keywords say
            cands = [s for s in slots if s.active and s.req_id == req]
            if not cands:
                continue
            if len(cands) > 1:                                           # one item per active substance: the substance the document names, else its manufacturer
                named = [s for s in cands if s.item and _extract.api_key(s.item.get('name') or '') and
                         _extract.api_key(s.item.get('name') or '').lower() in (text or '').lower()]
                if len(named) != 1:
                    by_maker = [s for s in cands if s.item and _extract.names_org(text, s.item.get('manufacturer'))]
                    named = by_maker if len(by_maker) == 1 else named
                    if len(named) != 1 and (by_maker or req in _extract.PER_API_ONLY):
                        pool = by_maker or named or cands               # several actives' items and nothing singles one out: offer them, place nothing
                        ids = {s.slot_id for s in pool}
                        sugg = [{'slot_id': s.slot_id, 'req_id': req, 'score': 8, 'why': [said]} for s in pool] + [x for x in sugg if x['slot_id'] not in ids]
                        unsure = True
                        break
                cands, decided = (named, True) if len(named) == 1 else ([], False)
                unsure = unsure or not cands                             # its likelier home is one of several actives' items and it names none: what follows is a guess
            if len(cands) == 1:
                why = next((x['why'] for x in sugg if x['slot_id'] == cands[0].slot_id), [])
                sugg = [{'slot_id': cands[0].slot_id, 'req_id': req, 'score': 9, 'why': [said] + why[:3]}] + [x for x in sugg if x['slot_id'] != cands[0].slot_id]
                break
        if homes:
            first = sugg[0]['slot_id'] if sugg and sugg[0]['req_id'] in homes and sugg[0]['score'] == 9 else None
            sugg.sort(key=lambda x: (0 if x['slot_id'] == first else 1 if x['req_id'] in homes else 2, homes.index(x['req_id']) if x['req_id'] in homes else 99, -x['score']))
        # placed without asking only on real evidence: the home of the kind the document was recognised as, or a strong match (a section
        # number in the file's name, its keyword in the name and the text); anything weaker is offered in the «not placed yet» box
        auto = sugg[0]['slot_id'] if sugg and (sugg[0]['req_id'] in homes or sugg[0]['score'] >= 6) else None
        if len(sugg) > 1 and not decided:
            a, b = by_id.get(sugg[0]['slot_id']), by_id.get(sugg[1]['slot_id'])
            if a and b and a.item and b.item and sugg[0]['score'] == sugg[1]['score'] and \
                    _extract.api_key(a.item.get('name') or '') != _extract.api_key(b.item.get('name') or ''):
                auto = None                                                         # a tie between two actives: never a guess
        if by_name or unread or (unsure and not decided):
            auto = None                                                             # a file that was not read, or that names none of the actives its kind belongs to, is offered — never placed on a guess
        return kind, sugg, auto

    @app.post('/api/dossiers/{did}/classify/text')
    def classify_text(did: str, body: dict):
        """Suggest a slot for files whose text the page already has (the wizard's reading): [{filename, text, kind?}] → suggestions."""
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for f in (body or {}).get('files') or []:
            if not isinstance(f, dict):
                continue
            kind, sugg, auto = _suggest_with_kind(clf, slots, f.get('filename') or 'document', f.get('text') or '', f.get('kind'), (d.get('product') or {}).get('name'),
                                                  (d.get('product') or {}).get('manufacturer'))
            out.append({'filename': f.get('filename'), 'kind': kind, 'suggestions': sugg, 'auto': auto})
        return out

    @app.get('/api/dossiers/{did}/unplaced')
    def unplaced_list(did: str):
        """Uploaded files that are not in an item yet, each with where the program thinks it belongs."""
        from .. import search as _search
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for doc in st.board(did)['unassigned']:
            text = ''
            try:
                data = st.blob_path(doc['sha256']).read_bytes()
                text = _extract.read_text(doc['filename'], data, max_pages=2)['text']      # PdfCraft's reading; a scan read by OCR
            except Exception:
                pass
            text = text or (doc.get('meta') or {}).get('text') or ''
            kind, sugg, auto = _suggest_with_kind(clf, slots, doc['filename'], text, (doc.get('meta') or {}).get('kind'), (d.get('product') or {}).get('name'),
                                                  (d.get('product') or {}).get('manufacturer'))
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
        new = st.add_document(did, slot_id, d0['filename'], data, title, meta, kind=d0['meta'].get('kind'))
        if d0['state'] == 'current':
            st.withdraw(did, doc_id, 'placed')
        return new

    # ---------------- the preparation stage (the owner, 13/11/2026): the documents asked for, each file read (a scan by OCR), its
    # information kept, placed in its item under the name the dossier gives it, checked, and fixed where it can be
    def _names(did):
        """Each placed document's name and place in the dossier: the CTD folders and, where the authority takes one, the eCTD."""
        d = st.dossier(did)
        pk = st.pack(d['pack'])
        out = {}
        for o in ('ctd', 'ectd32'):
            if o not in pk.outputs:
                continue
            try:
                for r in preview(did, o)['rows']:
                    if r.get('path'):
                        out.setdefault(r['doc_id'], {})[o] = r['path']
            except Exception:                                  # noqa: BLE001 — a name that cannot be made yet is said by the preview itself
                pass
        return out

    def _prep_left(doc):
        """What is left on a placed document: the fixes the program can still make (by rule), and what needs the user — the blocking
        findings it has no fix for, and the blocking ones whose fix it tried and could not make (with why: a blank scan has no words to
        read), so the same fix is not offered again until a new version comes."""
        from .. import fixes as _fixes
        refused = {x['op']: x for x in (doc.get('meta') or {}).get('fix_refused') or []}
        fixable, left = [], []
        for f in doc.get('findings') or []:
            if f.get('action') == 'auto_fix':
                why = refused.get(_fixes.RULE_TO_OP.get(f['rule']))
                if not why:
                    fixable.append(f['rule'])
                elif f.get('severity') == 'block':
                    left.append({'rule': f['rule'], 'en': why.get('en') or f.get('en'), 'ar': why.get('ar') or f.get('ar'), 'action': 'refused'})
            elif f.get('severity') == 'block' and f.get('scope') != 'ectd':
                left.append({'rule': f['rule'], 'en': f.get('en'), 'ar': f.get('ar'), 'action': f.get('action')})
        return fixable, left

    def _reading(name, data):
        """What the program read from a file: the reader (PdfCraft, its OCR, pypdf), pages, and the information it found in it."""
        r = _extract.read_files([(name, data)])
        f = r['files'][0]
        return {'reader': 'ocr' if f.get('ocr') else ('text' if f.get('chars') else 'none'), 'pages': f.get('pages'), 'chars': f.get('chars'),
                'scanned': bool(f.get('scanned')), 'ocr_language': f.get('ocr_language'), 'ocr_quality': f.get('ocr_quality'), 'kind': f.get('kind'),
                'found': f.get('found') or [], 'arabic': bool(f.get('arabic')), 'text': (f.get('text') or '')[:4000], 'rules': r['rules']}

    def _prep_ctx(did):
        """What every document's verdict in one dossier needs, read once: the dossier, its pack, its items by id."""
        d = st.dossier(did)
        return d, st.pack(d['pack']), {x.slot_id: x for x in st.slots(did)}

    def _req_of(did, doc, slot_id=None, ctx=None):
        """The requirement a placed document answers, its pack, and the person's answer to its item's question."""
        slot_id = slot_id or doc.get('slot_id')
        if not slot_id:
            return None, None, None
        d, pk, slots = ctx or _prep_ctx(did)
        slot = slots.get(slot_id)
        req = pk.by_id.get(slot.req_id) if slot else None
        attest = ((d.get('data') or {}).get('attest') or {}).get(slot_id)
        return req, pk, attest

    def _verdict(did, doc, reading=None, slot_id=None, ctx=None):
        """The document against its item's conditions (prepare.py): [lines], {counts, ready}."""
        from .. import prepare as _prep
        req, pk, attest = _req_of(did, doc, slot_id, ctx)
        if pk is None:
            return [], {}
        lines = _prep.verdict(doc, req, pk, reading=reading if reading is not None else (doc.get('meta') or {}).get('extracted') or {},
                              attest=attest, today=st.today())
        return lines, _prep.summary(lines)

    def _wants_model(did, doc, reading=None, slot_id=None, ctx=None):
        """Whether Claude should look at this document's pages: a scan with no text of its own, or an item whose conditions only eyes
        can check (letterhead, signed, stamped, legalised, a CoA's data) — and it has not looked yet, and its class may be sent."""
        meta = doc.get('meta') or {}
        if meta.get('model'):
            return False
        from ..assistant import settings as _aset
        if doc.get('doc_class') and doc['doc_class'] in (_aset.load(st.root).get('never_send') or []):
            return False
        rd = reading if reading is not None else meta.get('extracted') or {}
        if (rd.get('scanned') and not rd.get('chars')) or doc['filename'].lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.gif', '.bmp', '.webp')):
            return True
        req, pk, _ = _req_of(did, doc, slot_id, ctx)
        ids = {c.get('id') for c in (_conditions.for_requirement(req, pk) if req else [])}
        return bool(ids & {'letterhead', 'legalized', 'coa', 'translation'})

    def _read_by_model(did, doc):
        """Claude reads this document's pages through the key (server editions) and the reading is kept with it."""
        data = st.blob_path(doc['sha256']).read_bytes()
        ai = _ai_read([(doc['filename'], data)], 'document')['ai']
        return st.keep_model_reading(did, doc['id'], ai, 'api')

    @app.post('/api/dossiers/{did}/documents/{doc_id}/model-reading')
    def keep_model_reading(did: str, doc_id: str, body: dict):
        """What claude.ai's model read on this document's pages in the browser edition (DBAI.extract, target «document»), kept with it."""
        ai = (body or {}).get('ai')
        if not isinstance(ai, dict):
            err(422, 'E-AI', 'The reading must be a JSON object.', 'القراءة لازم تكون JSON.')
        try:
            doc = st.keep_model_reading(did, doc_id, ai, (body or {}).get('by') or 'claude.ai')
        except StoreError as e:
            err(404, e.code, e.en, e.ar)
        got = st.absorb_document(did, doc_id) if doc.get('slot_id') else {'added': [], 'conflicts': []}   # placed: what it says goes to its place
        doc = st.document(doc_id)
        lines, state = _verdict(did, doc)
        return {'document': doc, 'conditions': lines, 'state': state, 'absorbed': got}

    @app.post('/api/dossiers/{did}/data/choose')
    def choose_value(did: str, body: dict):
        """Where a document says something else than the data: the value the person keeps."""
        try:
            return st.choose_value(did, (body or {}).get('field'), (body or {}).get('value'), (body or {}).get('doc_id'))
        except StoreError as e:
            err(422, e.code, e.en, e.ar)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/confirm')
    def confirm_condition(did: str, doc_id: str, body: dict):
        """The person's answer to a condition the program could not see on this document → its conditions again."""
        try:
            doc = st.confirm_condition(did, doc_id, (body or {}).get('cond'), (body or {}).get('answer'))
        except StoreError as e:
            err(422 if e.code == 'E-ANSWER' else 404, e.code, e.en, e.ar)
        lines, state = _verdict(did, doc)
        return {'document': doc, 'conditions': lines, 'state': state}

    @app.post('/api/dossiers/{did}/documents/{doc_id}/read-by-model')
    def read_by_model(did: str, doc_id: str):
        """Claude reads this document's pages now (server editions, with the key)."""
        doc = st.document(doc_id)
        if doc['dossier_id'] != did:
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        doc = _read_by_model(did, doc)
        lines, state = _verdict(did, doc)
        return {'document': doc, 'conditions': lines, 'state': state}

    @app.get('/api/dossiers/{did}/prepare')
    def prepare_overview(did: str):
        """The preparation stage at a glance: the items still asking for a document, the files waiting to be placed (each read — a scan
        by OCR — with the item it belongs to), and every placed document with what can still be fixed and its name in the dossier."""
        from .. import pdfcraft as _pc
        board = st.board(did)
        names = _names(did)
        requested = [{'slot_id': s['slot_id'], 'ctd': s.get('ctd'), 'title': s.get('title'), 'level': s.get('level'), 'doc_class': s.get('doc_class')}
                     for s in board['slots'] if s.get('level') == 'R' and not s.get('documents') and s.get('status') not in ('not_applicable',)]
        waiting = []
        for u in unplaced_list(did):
            doc = st.document(u['id'])
            rd = _reading(doc['filename'], st.blob_path(doc['sha256']).read_bytes())
            md = ((doc.get('meta') or {}).get('model') or {}).get('doc') or {}
            waiting.append({**u, 'reading': {k: v for k, v in rd.items() if k not in ('rules', 'text')}, 'model': md or None,
                            'model_wanted': not md and bool(rd.get('scanned') and not rd.get('chars')),
                            'split_from': (doc.get('meta') or {}).get('split_from'), 'pages_of': (doc.get('meta') or {}).get('pages'),
                            'split_title': (doc.get('meta') or {}).get('split_title')})
        placed, ctx = [], _prep_ctx(did)
        for s in board['slots']:
            for doc in s.get('documents') or []:
                if (doc.get('meta') or {}).get('external'):
                    continue
                fx, left = _prep_left(doc)
                lines, state = _verdict(did, doc, slot_id=s['slot_id'], ctx=ctx)
                placed.append({'id': doc['id'], 'slot_id': s['slot_id'], 'ctd': s.get('ctd'), 'item': s.get('title'), 'filename': doc['filename'],
                               'conditions': lines, 'state': state, 'prepared': bool(((doc.get('meta') or {}).get('extracted') or {}).get('reader')),
                               'model': ((doc.get('meta') or {}).get('model') or {}).get('doc') or None, 'model_wanted': _wants_model(did, doc, slot_id=s['slot_id'], ctx=ctx),
                               'absorbed': (doc.get('meta') or {}).get('absorbed') or None, 'doc_class': s.get('doc_class'),
                               'version': doc.get('version'), 'improved': bool((doc.get('meta') or {}).get('optimized')),
                               'original_name': (doc.get('meta') or {}).get('original_name') or doc['filename'], 'version': doc.get('version'),
                               'status': doc.get('check_status'), 'fixable': fx, 'needs_you': left, 'names': names.get(doc['id'], {}),
                               'extracted': (doc.get('meta') or {}).get('extracted', {}).get('found', []),
                               'ocr_quality': (doc.get('meta') or {}).get('extracted', {}).get('ocr_quality'),
                               'optimized': (doc.get('meta') or {}).get('optimized'),
                               'improvable': bool(_pc.available() and doc['filename'].lower().endswith('.pdf')
                                                  and not (doc.get('meta') or {}).get('optimized'))})
        open_conf = [c for c in ((ctx[0].get('data') or {}).get('conflicts') or []) if isinstance(c, dict)]
        return {'requested': requested, 'waiting': waiting, 'placed': placed, 'engine': _pc.status(), 'ocr': _pc.ocr_info(),
                'model': 'server' if _ai_key() else None, 'conflicts': open_conf}

    @app.post('/api/dossiers/{did}/prepare/{doc_id}')
    def prepare_one(did: str, doc_id: str, body: dict = None):
        """One file through the preparation stage: placed in its item (the one given, or the one the program is sure of), its information
        read and kept with it (a scan read by OCR), checked, fixed where the program can (a new version; evidence only where its pages
        stay the same), and named as the dossier names it. → {document, steps, reading, names, needs_you}."""
        body = body or {}
        d0 = st.document(doc_id)
        if d0['dossier_id'] != did or d0['state'] != 'current':
            err(404, 'E-NOT-FOUND', 'Document not found.', 'المستند غير موجود.')
        steps, doc = [], d0
        if not d0.get('slot_id'):                            # a file waiting to be placed
            slot_id, u = body.get('slot_id'), {}
            if not slot_id:
                u = next((x for x in unplaced_list(did) if x['id'] == doc_id), None) or {}
                slot_id = u.get('auto')
            if not slot_id:
                return {'document': d0, 'steps': ['needs_item'], 'suggestions': u.get('suggestions') or []}
            doc = place_document(did, doc_id, {'slot_id': slot_id})
            steps.append('placed')
        data = st.blob_path(doc['sha256']).read_bytes()
        rd = _reading(doc['filename'], data)
        keep = {'found': rd['found'], 'reader': rd['reader'], 'ocr_language': rd['ocr_language'], 'ocr_quality': rd['ocr_quality'],
                'fields': rd['rules'], 'chars': rd['chars'], 'scanned': rd['scanned'], 'arabic': rd['arabic'], 'text': rd['text']}
        doc = st.keep_reading(did, doc['id'], keep)
        steps.append('read_ocr' if rd['reader'] == 'ocr' else 'read')
        if body.get('model', True) and _ai_key() and _wants_model(did, doc, keep):       # Claude looks at its pages (server editions)
            try:
                doc = _read_by_model(did, doc)
                steps.append('read_model')
            except HTTPException as e:
                steps.append({'model_failed': (e.detail or {}).get('en') if isinstance(e.detail, dict) else str(e.detail)})
            except Exception as e:                       # no network, a refusal: the rest of the preparation goes on
                steps.append({'model_failed': str(e)[:200]})
        absorbed = st.absorb_document(did, doc['id'])                     # every value it gave, kept in its place in the data
        doc = st.document(doc['id'])
        if absorbed['added'] or absorbed['conflicts']:
            steps.append({'absorbed': {'added': len(absorbed['added']), 'conflicts': len(absorbed['conflicts'])}})
        if body.get('fix', True) and any(f.get('action') == 'auto_fix' for f in doc.get('findings') or []):
            r = st.fix_document(did, doc['id'])
            if r.get('document'):
                doc = st.keep_reading(did, r['document']['id'], keep)
            doc = st.keep_fix_refused(did, doc['id'], r['refused'])      # what could not be fixed, with why: asked of the user, not offered again
            steps.append({'fixed': [x['op'] for x in r['done']], 'refused': [{'op': x['op'], 'en': x['en'], 'ar': x['ar']} for x in r['refused']]})
        if body.get('improve', True) and not (doc.get('meta') or {}).get('optimized'):
            imp = st.improve_document(did, doc['id'])                     # «improve the file»: smaller and cleaner, the same pages
            if imp.get('document'):
                doc = st.keep_reading(did, imp['document']['id'], keep)
                steps.append({'improved': {'before': imp['before'], 'after': imp['after']}})
        if body.get('split', True):
            cut = st.split_large(did, doc['id'])                          # over 100 MB still: cut into parts that fit, in the same item
            if cut['parts']:
                steps.append({'split': {'parts': len(cut['parts'])}})
                lines, state = _verdict(did, cut['parts'][0], keep)
                return {'document': cut['parts'][0], 'parts': cut['parts'], 'steps': steps,
                        'reading': {k: v for k, v in rd.items() if k not in ('rules', 'text')}, 'names': _names(did).get(cut['parts'][0]['id'], {}),
                        'fixable': [], 'needs_you': [], 'conditions': lines, 'state': state}
        fixable, left = _prep_left(doc)
        lines, state = _verdict(did, doc, keep)
        return {'document': doc, 'steps': steps, 'reading': {k: v for k, v in rd.items() if k not in ('rules', 'text')}, 'names': _names(did).get(doc['id'], {}),
                'fixable': fixable, 'needs_you': left, 'conditions': lines, 'state': state, 'absorbed': absorbed}

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
                text = _extract.read_text(f.filename, data, max_pages=2)['text']
            except Exception:
                text = ''
            kind, sugg, auto = _suggest_with_kind(clf, slots, f.filename, text, None, (d.get('product') or {}).get('name'),
                                                  (d.get('product') or {}).get('manufacturer'))
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
            return exporter.export(st, did, body.outputs, body.acknowledge_provisional, body.submission, p40, ig, working=body.working,
                                   replace_last=body.replace_last)
        except exporter.ExportError as e:
            err(e.status, e.code, e.en, e.ar, **e.extra)

    @app.get('/api/dossiers/{did}/submissions')
    def submissions(did: str):
        return {o: [{k: h[k] for k in ('seq', 'activity', 'envelope', 'created', 'receipt', 'frozen')} | {'documents': len(h['leaves'])}
                    for h in st.history(did, o)] for o in ('ectd32', 'ectd40')}

    @app.post('/api/dossiers/{did}/submissions/{output}/{seq}/submitted')
    async def submitted(did: str, output: str, seq: str, meta: str = Form('{}'), file: UploadFile = File(None)):
        """The sequence went to the authority: the day, the tracking number, the technical acceptance, the decision, the receipt file.
        From now on it is frozen."""
        return st.mark_submitted(did, output, seq, json.loads(meta or '{}'), await file.read() if file else None, file.filename if file else None)

    @app.delete('/api/dossiers/{did}/submissions/{output}/{seq}')
    def discard_seq(did: str, output: str, seq: str):
        st.discard_sequence(did, output, seq)
        return {'ok': True}

    @app.get('/api/dossiers/{did}/submissions/{output}/{seq}/receipt')
    def receipt(did: str, output: str, seq: str):
        h = next((x for x in st.history(did, output) if str(x['seq']) == seq), None)
        if not h or not h['receipt'].get('receipt_sha'):
            err(404, 'E-NO-FILE', 'No receipt file for this sequence.', 'مفيش ملف إيصال للتسلسل ده.')
        return FileResponse(st.blob_path(h['receipt']['receipt_sha']), filename=h['receipt'].get('receipt_name') or 'receipt.pdf')

    @app.get('/api/dossiers/{did}/exports/{exp_id}/{name}')
    def download(did: str, exp_id: str, name: str):
        p = st.root / 'exports' / did / exp_id / name
        if '/' in name or not p.is_file():
            err(404, 'E-NOT-FOUND', 'Export not found.', 'التصدير غير موجود.')
        return FileResponse(p, filename=name)

    @app.post('/api/dossiers/{did}/exports/{exp_id}/compare-report')
    async def compare_report(did: str, exp_id: str, file: UploadFile = File(...), output: str = 'eCTD 3.2.2'):
        """Another validator's report of this export's sequence beside ours: where both agree, and why they differ (updates list, item 27)."""
        from ..validators import compare_report as _cr
        from ..writers.ectd32 import DEFAULT_PROFILE
        row = st.db.execute('select path from export where id=? and dossier_id=?', (exp_id, did)).fetchone()
        if not row:
            err(404, 'E-NOT-FOUND', 'Export not found.', 'التصدير غير موجود.')
        ours = _cr.ours_of(row['path'], output)
        if not ours:
            err(422, 'E-NO-REPORT', 'This export has no validation report of its own (CTD folders only): export the eCTD first.',
                'التصدير ده مفيهوش تقرير تحقق خاص بيه (مجلدات CTD بس): صدّر الـ eCTD الأول.')
        theirs = _cr.read(file.filename, await file.read())
        if not theirs:
            err(422, 'E-REPORT-UNREAD', 'No validation criterion with a result was found in this report (a line naming a criterion such as 14.5 '
                'and saying failed / passed). Export their report as PDF, Excel, CSV or HTML.',
                'ملقيناش في التقرير ده قاعدة تحقق ومعاها نتيجتها (سطر فيه رقم القاعدة زي 14.5 وجنبه failed أو passed). صدّر تقريرهم PDF أو Excel أو CSV أو HTML.')
        return _cr.compare(theirs, ours, _cr.eg_refs(DEFAULT_PROFILE))

    @app.get('/api/dossiers/{did}/audit')
    def audit(did: str):
        return [dict(r) | {'detail': json.loads(r['detail'])}
                for r in st.db.execute('select * from audit where dossier_id=? order by id', (did,))]

    from . import suite as _suite
    _suite.install(app, st, err)
    from . import suite_m2 as _m2                       # the authority's letters, questions, commitments and deadlines
    _m2.install(app, st, err)

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
        app.mount('/', StaticFiles(directory=STATIC, html=True), name='ui')
    app.state.store = st
    return app
