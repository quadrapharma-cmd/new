"""HTTP API on localhost (D1). Errors always carry code + en + ar (+ action)."""
import json, shutil, tempfile, time, uuid, zipfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ..profile import Profile, ProfileError
from ..guard import assert_allowed, LockedError
from ..assemble import docs_for
from ..classify import Classifier
from ..validators import ectd32 as v32, ectd40 as v40, report as vreport
from ..writers import ctd, ectd32, ectd40
from ..writers.ectd32 import WriterError
from ..generate import letters
from ..generate.docx_kit import MissingData, to_pdf
from .store import Store, StoreError

STATIC = Path(__file__).resolve().parents[3] / 'ui'
GEN = {  # kind -> (function, requirement id)
    'annex1': ('annex1', 'M1-01'), 'composition': ('composition_certificate', 'M1-31'),
    'salt': ('salt_calc_letter', 'M1-32'), 'cep_commitment': ('cep_commitment', 'M1-40'),
    'translation': ('translation_declaration', 'M1-10'), 'cover': ('cover_letter', 'M1-43'),
    'tracking': ('tracking_table', 'M1-44'), 'stability_commitment': ('stability_commitment', 'P-16'),
    'justification': ('justification', None),
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


class GenReq(BaseModel):
    data: dict
    ctx: dict = {}
    slot_id: str = None


class OpReq(BaseModel):
    op: str


def create_app(workspace):
    st = Store(workspace)
    app = FastAPI(title='Dossier Builder (local)', version='0.1')

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
                     meta: str = Form('{}')):
        data = await file.read()
        return st.add_document(did, slot_id, file.filename, data, title, json.loads(meta or '{}'))

    @app.get('/api/dossiers/{did}/documents/{doc_id}/file')
    def get_file(did: str, doc_id: str):
        d = st.document(doc_id)
        return FileResponse(st.blob_path(d['sha256']), media_type='application/pdf', filename=d['filename'])

    @app.post('/api/dossiers/{did}/documents/{doc_id}/withdraw')
    def withdraw(did: str, doc_id: str, reason: str = 'user'):
        return st.withdraw(did, doc_id, reason)

    @app.post('/api/dossiers/{did}/documents/{doc_id}/restore')
    def restore(did: str, doc_id: str):
        return st.restore(did, doc_id)

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
            fn = getattr(letters, fn_name)
            out = tmp / f'{kind}.docx'
            try:
                if kind == 'annex1':
                    ctx = {**d['profile'], **body.ctx}
                    fn(body.data, ctx, out)
                else:
                    fn(body.data, out)
            except MissingData as e:
                err(422, 'E-MISSING-DATA', 'Some data is missing: ' + ', '.join(e.fields),
                    'فيه بيانات ناقصة: ' + '، '.join(e.fields), request_data=e.fields)
            pdf = to_pdf(out)
            doc = st.add_document(did, slot.slot_id, f'{kind}.pdf', pdf.read_bytes(), meta={
                'generated': kind, 'draft_unsigned': True, 'data': body.data})
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
                     ctd=by_slot[r['slot_id']].ctd, module=by_slot[r['slot_id']].module)
        return {'output': output, 'rows': rows}

    @app.get('/api/generators')
    def generators():
        return {k: {kk: v[kk] for kk in ('req', 'title', 'fields')} for k, v in letters.SCHEMAS.items()}

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
        g = st.gate(did)
        if not g['ok']:
            err(409, 'E-GATE', 'Export blocked: required documents are missing or non-conforming.',
                'التصدير متوقف: فيه مستندات مطلوبة ناقصة أو غير مطابقة.', gate=g)
        if {'ectd32', 'ectd40'} & set(body.outputs) and not body.acknowledge_provisional:
            err(409, 'E-PROVISIONAL-ACK', 'eCTD outputs use the provisional EG profiles; acknowledge before export.',
                'مخرجات eCTD مبنية على ملف تعريف مصري مؤقت؛ لازم توافق قبل التصدير.', gate=g)
        d = st.dossier(did)
        slots = st.slots(did)
        exp_id = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
        base = st.root / 'exports' / did / exp_id
        work = base / '_files'
        work.mkdir(parents=True)
        files = {}
        for s in slots:
            for doc in st.documents(did, s.slot_id) if s.active else []:
                p = work / f"{doc['id']}.pdf"
                shutil.copyfile(st.blob_path(doc['sha256']), p)
                files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **doc['meta']})
        prof = Profile.from_dict(d['profile'])
        docs, ctd_only = docs_for(slots, prof, files)
        pr, env = d['product'], d['envelope']
        product = ectd32.Product(pr['name'], pr['dosageform'], pr['manufacturer'], pr.get('indication'))
        results = {}
        try:
            if 'ctd' in body.outputs:
                results['ctd'] = ctd.write(base / 'ctd', d['name'], slots, files)['path']
            if 'ectd32' in body.outputs:
                results['ectd32'] = ectd32.write(base / 'ectd-3.2.2', ectd32.Envelope(
                    identifier=env['application_uuid'], submission_type=env.get('submission_type', 'maa'),
                    tracking=[env['tracking']], unit=env.get('unit', 'initial'), applicant=env['applicant'],
                    invented_name=env.get('invented_name', d['name']), registration=ectd32.REG_TYPE[prof.licence],
                    marketing=env.get('marketing', 'local'), inn=env.get('inn', []),
                    sequence=env.get('sequence', '0000'), description=env.get('description', d['name'])),
                    product, docs)['path']
            if 'ectd40' in body.outputs:
                results['ectd40'] = ectd40.write(base / 'ectd-4.0', ectd40.Envelope4(
                    application_uuid=env['application_uuid'],
                    submission_uuid=env.setdefault('submission_uuid', str(uuid.uuid4())), tracking=env['tracking'],
                    submission_type=env.get('submission_type', 'maa'), unit=env.get('unit', 'initial'),
                    sequence=int(env.get('sequence_v4', 1)), title=env.get('description', d['name']),
                    applicant=env['applicant'], applicant_portal_id=env.get('portal_id', 'UNKNOWN'),
                    product_name=env.get('invented_name', d['name']), inn=env.get('inn', []),
                    registration=ectd32.REG_TYPE[prof.licence], marketing=env.get('marketing', 'local')),
                    product, docs)['path']
        except (WriterError, KeyError) as e:
            shutil.rmtree(base, ignore_errors=True)
            err(422, 'E-WRITER', f'Export failed: {e}', f'التصدير فشل: {e}')
        shutil.rmtree(work)
        reports = {}
        if 'ectd32' in results:
            reports['eCTD 3.2.2'] = v32.validate(results['ectd32'], ectd32.DEFAULT_PROFILE)
        if 'ectd40' in results:
            p40 = getattr(app.state, 'p40', None) or ectd40.Profile40()
            app.state.p40 = p40
            ig = Path(__file__).resolve().parents[5] / 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
            reports['eCTD 4.0'] = v40.validate(results['ectd40'], p40, ig, st.root / 'cache')
        if reports:
            (base / 'validation-report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding='utf-8')
            (base / 'validation-report.html').write_text(vreport.render(d['name'], reports), encoding='utf-8')
        zips = {}
        for k, p in results.items():
            z = base / f'{k}.zip'
            root = Path(p).parent if k != 'ectd40' else Path(p).parent.parent
            with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in sorted(Path(root).rglob('*')):
                    if f.is_file():
                        zf.write(f, f.relative_to(root.parent))
            zips[k] = f'/api/dossiers/{did}/exports/{exp_id}/{k}.zip'
        st.db.execute('insert into export values (?,?,?,?,?,?)', (exp_id, did, json.dumps(body.outputs), str(base),
                                                                  int(body.acknowledge_provisional), time.time()))
        st.db.commit()
        st.audit(did, 'export', id=exp_id, outputs=body.outputs, acknowledged=body.acknowledge_provisional,
                 validation={k: r['counts'] for k, r in reports.items()})
        summary = {k: {'ok': r['ok'], 'counts': r['counts'], 'coverage': r['coverage'], 'label': r['label']}
                   for k, r in reports.items()}
        return {'id': exp_id, 'downloads': zips, 'ctd_only': ctd_only, 'validation': summary,
                'report': f'/api/dossiers/{did}/exports/{exp_id}/validation-report.html' if reports else None,
                'label': 'Conforms to EDA drafts + ICH (provisional EG profiles) — not «EDA-valid».'}

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

    if STATIC.exists():
        app.mount('/', StaticFiles(directory=STATIC, html=True), name='ui')
    app.state.store = st
    return app
