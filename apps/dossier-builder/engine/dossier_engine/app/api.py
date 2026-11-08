"""HTTP API on localhost (D1). Errors always carry code + en + ar (+ action)."""
import json, shutil, tempfile, time, uuid, zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ..profile import Profile, ProfileError
from ..resolver import resolve
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


def create_app(workspace, auth_enabled=None):
    import os
    from .auth import Auth, install
    st = Store(workspace)
    app = FastAPI(title='Dossier Builder', version='0.2', docs_url=None, redoc_url=None, openapi_url=None)
    if auth_enabled is None:
        auth_enabled = os.environ.get('DB_MODE') == 'cloud' or os.environ.get('DB_AUTH') == '1'
    app.state.auth = Auth(workspace, auth_enabled)
    install(app, app.state.auth, st)

    @app.exception_handler(StoreError)
    def _store_err(_, e):
        return JSONResponse(status_code=404 if e.code == 'E-NOT-FOUND' else 422,
                            content={'detail': {'code': e.code, 'en': e.en, 'ar': e.ar, **e.extra}})

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
    def list_dossiers():
        return st.list_dossiers()

    @app.post('/api/dossiers', status_code=201)
    def new_dossier(body: NewDossier):
        did = st.create_dossier(body.name, body.profile, body.product, body.envelope)
        return {'id': did, **st.board(did)['counts']}

    @app.get('/api/dossiers/{did}')
    def get_dossier(did: str):
        return st.dossier(did)

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
        return st.add_document(did, slot_id, file.filename, data, title, json.loads(meta or '{}'), supersede=replaces or None)

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
        docx = d['filename'].lower().endswith('.docx')
        return FileResponse(st.blob_path(d['sha256']), filename=d['filename'],
                            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document' if docx else 'application/pdf')

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
        pack = st.pack('eda.ctd.nta065.v5')
        by_module, by_class = {}, {}
        for r in pack.requirements:
            by_module[str(r['module'])] = by_module.get(str(r['module']), 0) + 1
            by_class[r['doc_class']] = by_class.get(r['doc_class'], 0) + 1
        rules40 = sorted(set(re.findall(r"'(eCTD4-[0-9A-Za-z/.-]+)'", inspect.getsource(v40))))
        cross_ids = sorted(set(re.findall(r"'((?:XC|NP040)-[A-Z0-9]+)'", inspect.getsource(crosschecks))))
        doc_types = yaml.safe_load(TYPES_FILE.read_text(encoding='utf-8'))['types']
        return {'version': app.version, 'workspace': str(st.root),
                'dossiers': st.db.execute('select count(*) from dossier').fetchone()[0],
                'pack': {'id': pack.id, 'title': pack.meta['title'], 'status': pack.meta['status'],
                         'valid_from': pack.meta['valid_from'], 'sources': pack.meta['sources']},
                'requirements': {'total': len(pack.requirements), 'by_module': by_module, 'by_class': by_class},
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
        return {'files': [{k: v for k, v in f.items() if k != 'text'} for f in r['files']], 'rules': r['rules'],
                'prompt': _extract.ai_prompt(r['files'], target), 'ai_server': bool(os.environ.get('ANTHROPIC_API_KEY'))}

    def _dossier_pdfs(did):
        out = []
        for d in st.documents(did):
            if d['filename'].lower().endswith('.pdf') and not d['meta'].get('external'):
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
        return {'ai': ai, 'rules': r['rules'], 'files': [{k: v for k, v in f.items() if k != 'text'} for f in r['files']]}

    @app.post('/api/extract/ai')
    async def extract_ai(files: list[UploadFile] = File(...), target: str = 'dossier'):
        return _ai_read([(f.filename, await f.read()) for f in files], target)

    @app.post('/api/dossiers/{did}/extract/ai')
    def extract_dossier_ai(did: str, target: str = 'dossier'):
        return _ai_read([(n, b) for n, b, _ in _dossier_pdfs(did)], target)

    @app.post('/api/profile/preview')
    def profile_preview(profile: dict):
        """The requirements a profile would produce, before any dossier exists (the wizard's last step)."""
        prof = Profile.from_dict(profile)
        try:
            prof.validate()
        except ProfileError as e:                       # a wizard without its APIs yet still gets the non-API items
            rest = [p for p in e.problems if p['code'] != 'P-NO-API']
            if rest:
                raise ProfileError(rest)
        slots = [s.to_dict() for s in resolve(prof, st.pack('eda.ctd.nta065.v5'), validate=False)]
        gen = {v['req'] for v in letters.SCHEMAS.values() if v.get('req')}
        counts = {k: sum(1 for s in slots if s['level'] == k) for k in ('R', 'O', 'NR', 'NA')}
        by_module = {}
        for s in slots:
            m = by_module.setdefault(str(s['module']), {'R': 0, 'O': 0, 'NR': 0, 'NA': 0})
            m[s['level']] += 1
        col, assumed = prof.column()
        return {'slots': slots, 'counts': counts, 'by_module': by_module, 'column': col, 'column_assumed': assumed,
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

    @app.post('/api/dossiers/{did}/classify')
    async def classify(did: str, files: list[UploadFile] = File(...)):
        """Suggest a slot for each file (nothing is stored until the user confirms)."""
        from io import BytesIO
        from pypdf import PdfReader
        d = st.dossier(did)
        clf = Classifier(st.pack(d['pack']))
        slots = st.slots(did)
        out = []
        for f in files:
            data = await f.read()
            text = ''
            try:
                rd = PdfReader(BytesIO(data), strict=False)
                text = ' '.join((p.extract_text() or '') for p in rd.pages[:1])
            except Exception:
                pass
            out.append({'filename': f.filename, 'size': len(data), 'suggestions': clf.suggest(f.filename, text, slots)})
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
        app.mount('/', StaticFiles(directory=STATIC, html=True), name='ui')
    app.state.store = st
    return app
