"""Lifecycle-aware export (P1 + P3).

eCTD outputs live in a per-dossier lifecycle folder that accumulates sequences
(<workspace>/lifecycle/<dossier>/ectd-3.2.2/0000, 0001… and ectd-4.0/<app>/1, 2…),
exactly like a company's eCTD archive. Each export computes the next sequence from
the submission history: only new / replaced / deleted documents go into it; the
tracking table (M1-44) is rebuilt from the history every time. The download zip
holds just the new sequence (what is uploaded to the portal)."""
import json, shutil, tempfile, time, uuid, zipfile
from pathlib import Path
from ..assemble import docs_for
from ..lifecycle import plan, to_ectd32, to_ectd40
from ..profile import Profile
from ..writers import ctd, ectd32, ectd32_eu, ectd40
from ..writers.ectd32 import WriterError
from ..generate import letters
from ..generate.docx_kit import to_pdf, basic_pdf
from ..validators import ectd32 as v32, ectd32_eu as v32eu, ectd40 as v40, report as vreport


class ExportError(Exception):
    def __init__(self, status, code, en, ar, **extra):
        self.status, self.code, self.en, self.ar, self.extra = status, code, en, ar, extra


def _zip(src_root, rel_folder, out):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted((src_root / rel_folder).rglob('*')):
            if f.is_file():
                zf.write(f, f.relative_to(src_root))


def _working_copy(st, did, g):
    d = st.dossier(did)
    slots = st.slots(did)
    exp_id = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6] + '-working'
    base = st.root / 'exports' / did / exp_id
    work = base / '_files'
    work.mkdir(parents=True)
    files, n_docs = {}, 0
    for s in slots:
        for doc in st.documents(did, s.slot_id) if s.active else []:
            if (doc.get('meta') or {}).get('external'):
                continue
            ext = '.' + doc['filename'].rsplit('.', 1)[-1].lower() if '.' in doc['filename'][-6:] else '.pdf'
            p = work / f"{doc['id']}{ext}"
            shutil.copyfile(st.blob_path(doc['sha256']), p)
            orig = doc['filename'].rsplit('.', 1)[0] if '.' in doc['filename'][-6:] else doc['filename']
            files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **doc['meta'], 'doc_id': doc['id'], 'ext': ext, 'orig': orig})
            n_docs += 1
    missing = len(g.get('missing_required') or [])
    note = {'en': f"WORKING COPY — NOT FOR SUBMISSION. {n_docs} document(s) in place; {missing} required item(s) still missing, "
                  f"{len(g.get('non_conforming') or [])} to fix, {len(g.get('unsigned') or [])} draft(s) to sign. See 00-MISSING.txt.",
            'ar': f"نسخة عمل — ليست للتقديم. {n_docs} مستند في مكانه؛ {missing} بند مطلوب لسه ناقص، {len(g.get('non_conforming') or [])} محتاج تصليح، "
                  f"{len(g.get('unsigned') or [])} مسودة محتاجة توقيع. شوف 00-MISSING.txt."}
    try:
        res = ctd.write(base / 'ctd', d['name'] + ' - WORKING COPY', slots, files, working=note)
        _zip(Path(res['path']).parent, Path(res['path']).name, base / 'ctd-working.zip')
    except (WriterError, OSError) as ex:
        shutil.rmtree(base, ignore_errors=True)
        raise ExportError(422, 'E-WRITER', f'Export failed: {ex}', f'التصدير فشل: {ex}')
    shutil.rmtree(work, ignore_errors=True)
    st.db.execute('insert into export values (?,?,?,?,?,?)', (exp_id, did, json.dumps(['ctd-working']), str(base), 0, time.time()))
    st.db.commit()
    st.audit(did, 'export.working', id=exp_id, documents=n_docs, missing_required=missing)
    return {'id': exp_id, 'working': True, 'downloads': {'ctd-working': f'/api/dossiers/{did}/exports/{exp_id}/ctd-working.zip'}, 'documents': n_docs,
            'missing_required': missing, 'non_conforming': len(g.get('non_conforming') or []), 'unsigned': len(g.get('unsigned') or []),
            'sequences': {}, 'validation': {}, 'report': None, 'ctd_only': [], 'label': note['en'], 'label_ar': note['ar']}


def ectd_files(files):
    """The files an eCTD takes: PDF. A Word document (the proposed leaflet, asked in Word for the One Submission) goes in as its PDF —
    the one the item holds beside it with the same language and type, else converted here (LibreOffice); without either the eCTD
    export stops and says so (it never writes a Word file under a .pdf name)."""
    out = {}
    for sid, fs in files.items():
        keep = []
        for f in fs:
            if f.get('ext', '.pdf') == '.pdf':
                keep.append(f)
                continue
            twin = next((g for g in fs if g.get('ext', '.pdf') == '.pdf' and g.get('pi_type') == f.get('pi_type') and g.get('lang') == f.get('lang')), None)
            if twin:
                continue                                  # its PDF is in the item: that one goes in
            try:
                pdf = to_pdf(Path(f['file']))
            except Exception:                             # no LibreOffice here, or it failed on this file
                raise ExportError(422, 'E-WORD-PDF', f"«{f.get('title')}» is a Word file and an eCTD takes PDF: add its PDF to the item "
                                  '(save it as PDF from Word), or export on a machine with LibreOffice.',
                                  f"«{f.get('title')}» ملف Word والـ eCTD بياخد PDF: ضيف الـ PDF بتاعه في البند (احفظه PDF من Word)، "
                                  'أو صدّر من جهاز عليه LibreOffice.')
            keep.append(dict(f, file=str(pdf), ext='.pdf'))
        out[sid] = keep
    return out


def next_seq(hist, output):
    if not hist:
        return '0000' if output == 'ectd32' else 1
    last = hist[-1]['seq']
    return f'{int(last) + 1:04d}' if output == 'ectd32' else int(last) + 1


def eu_countries(d, prof, sub=None, hist=None):
    """(procedure, envelope countries) of an EU dossier: 'ema' in the centralised procedure; otherwise the countries named for this
    sequence, else those of the last one, else the dossier's own country (a national procedure keeps one)."""
    env = d['envelope']
    proc = ectd32_eu.PROCEDURE.get((prof.extra or {}).get('eu_procedure') or 'dcp', 'decentralised')
    if proc == 'centralised':
        return proc, ['ema']
    named = (sub or {}).get('countries') or (hist[-1]['envelope'].get('countries') if hist else None) or env.get('eu_countries') \
        or [env.get('country')]
    out = []
    for c in named:
        c = ectd32_eu.code(c)
        if c and c not in out:
            out.append(c)
    return proc, out[:1] if proc == 'national' else out


def eu_envelope(d, prof, sub, hist, seq, stype, unit, activity, desc, tracking):
    """The EU envelope(s) of a sequence from the dossier, its answers and the follow-on's details (SPEC 3.1.1 §Envelope)."""
    env, pr = d['envelope'], d['product']
    proc, countries = eu_countries(d, prof, sub, hist)
    values = ectd32_eu.default_profile().values
    if not countries:
        raise ExportError(422, 'E-ENVELOPE', 'Name the countries of the procedure (the EU envelopes).', 'حدّد دول الإجراء (الـ envelope الأوروبي).')
    bad = [c for c in countries if c not in values['env_countries']]
    if bad:
        raise ExportError(422, 'E-ENVELOPE', f'Not an EU M1 destination: {bad}.', f'دي مش دولة في موديول ١ الأوروبي: {bad}.')
    if stype not in values['submission_types']:
        raise ExportError(422, 'E-SUBMISSION', f'An EU submission type is one of: {", ".join(values["submission_types"])}.',
                          'نوع التقديم الأوروبي واحد من: ' + '، '.join(values['submission_types']) + '.')
    if unit not in values['units']:
        raise ExportError(422, 'E-SUBMISSION', f'An EU submission unit is one of: {", ".join(values["units"])}.',
                          'نوع الوحدة الأوروبي واحد من: ' + '، '.join(values['units']) + '.')
    applicant = env.get('applicant') or pr.get('manufacturer')
    if not applicant:
        raise ExportError(422, 'E-ENVELOPE', "The envelope needs the applicant's name.", 'الـ envelope محتاج اسم مقدّم الطلب.')
    mode = (sub or {}).get('mode') or 'single' if stype.startswith('var-') or stype == 'extension' else None
    if not desc:                                       # mandatory in the EU envelope; said plainly when the dossier gives none
        desc = ('Initial marketing authorisation application' if stype == 'maa' and unit == 'initial' else
                f"{stype.replace('-', ' ')} — {unit.replace('-', ' ')}")
    return ectd32_eu.EnvelopeEU(identifier=env['application_uuid'], procedure=proc, countries=countries, submission_type=stype, unit=unit,
                                applicant=applicant, invented_names=[env.get('invented_name') or d['name']],
                                inn=env.get('inn') or [a.name for a in prof.apis if a.name], tracking=tracking, sequence=seq,
                                related_sequence=[activity], description=desc, mode=mode, number=(sub or {}).get('number'),
                                agencies={ectd32_eu.code(k): v for k, v in (env.get('eu_agencies') or {}).items()},
                                legal_basis=(prof.extra or {}).get('eu_legal_basis'))


def export(st, did, outputs, ack, sub, p40, ig_zip, working=False):
    """working: a working copy — the CTD folders with what the dossier holds now and the list of what is missing, whatever the gate
    says; never an eCTD sequence, never recorded as a submission."""
    g = st.gate(did)
    if working:
        return _working_copy(st, did, g)
    if not g['ok']:
        raise ExportError(409, 'E-GATE', 'Export blocked: required documents are missing or non-conforming.',
                          'التصدير متوقف: فيه مستندات مطلوبة ناقصة أو غير مطابقة.', gate=g)
    pk = st.pack(st.dossier(did)['pack'])
    egypt, region = pk.egypt, pk.ectd_region      # the regional eCTD backbone: Egypt's (provisional) and the EU's; others get the CTD folders
    if list(outputs) == ['ctd', 'ectd32', 'ectd40']:                         # nothing was asked: what this authority has
        outputs = list(pk.outputs)
    elif set(outputs) - set(pk.outputs):
        if region == 'eu':
            raise ExportError(422, 'E-OUTPUT-AUTHORITY', 'eCTD 4.0 is written for Egypt only; an EU dossier exports as CTD folders and eCTD 3.2.2 '
                              '(EU Module 1 v3.1.1).', 'الـ eCTD 4.0 مكتوب لمصر بس؛ الملف الأوروبي بيتصدّر كمجلدات CTD و eCTD 3.2.2 (موديول ١ الأوروبي 3.1.1).', gate=g)
        raise ExportError(422, 'E-OUTPUT-AUTHORITY', "The eCTD package is written for Egypt's and the EU's Module 1; this dossier exports as CTD folders.",
                          'حزمة الـ eCTD مكتوبة لموديول ١ المصري والأوروبي بس؛ الملف ده بيتصدّر كمجلدات CTD.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and g.get('ectd_blocking'):
        raise ExportError(409, 'E-GATE-ECTD', 'eCTD readiness: some documents carry restrictions, a Portfolio or JavaScript (the eCTD rules). '
                          'Fix them (auto-fix for company documents, a new copy from the issuer otherwise), or export the CTD folders only.',
                          'جاهزية الـ eCTD: فيه مستندات عليها قيود أو Portfolio أو JavaScript (قواعد الـ eCTD). صلّحها (إصلاح تلقائي لمستندات الشركة، '
                          'ونسخة جديدة من الجهة لغيرها)، أو صدّر مجلدات CTD بس.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and not ack and egypt:            # the EG profiles are provisional; the EU's is the EMA's own
        raise ExportError(409, 'E-PROVISIONAL-ACK', 'eCTD outputs use the provisional EG profiles; acknowledge before export.',
                          'مخرجات eCTD مبنية على ملف تعريف مصري مؤقت؛ لازم توافق قبل التصدير.', gate=g)
    sub = sub or {}
    d = st.dossier(did)
    slots = st.slots(did)
    prof = Profile.from_dict(d['profile'])
    pr, env = d['product'], d['envelope']
    product = ectd32.Product(pr['name'], pr['dosageform'], pr['manufacturer'], pr.get('indication'))
    exp_id = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
    base = st.root / 'exports' / did / exp_id
    work = base / '_files'
    work.mkdir(parents=True)
    files = {}
    for s in slots:
        for doc in st.documents(did, s.slot_id) if s.active else []:
            ext = '.' + doc['filename'].rsplit('.', 1)[-1].lower() if '.' in doc['filename'][-6:] else '.pdf'
            ext = ext if ext in ('.pdf', '.docx', '.doc', '.rtf', '.odt') else '.pdf'
            p = work / f"{doc['id']}{ext}"
            shutil.copyfile(st.blob_path(doc['sha256']), p)
            files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **doc['meta'], 'doc_id': doc['id'], 'ext': ext})
    try:
        files_e = ectd_files(files) if region and {'ectd32', 'ectd40'} & set(outputs) else files      # an eCTD takes PDF only
    except ExportError:
        shutil.rmtree(base, ignore_errors=True)
        raise
    docs_all, ctd_only = docs_for(slots, prof, files_e) if region else ([], [])
    current_ids = {x.doc_id for x in docs_all}
    eff = {k: v for k, v in files_e.items() if not k.startswith('M1-44')}
    docs_ectd = [x for x in docs_for(slots, prof, eff)[0]] if region else []
    results, reports, zips, seqinfo, done = {}, {}, {}, {}, []
    lc = st.root / 'lifecycle' / did
    try:
        if 'ctd' in outputs:
            results['ctd'] = ctd.write(base / 'ctd', d['name'], slots, files)['path']
            _zip(Path(results['ctd']).parent, Path(results['ctd']).name, base / 'ctd.zip')
            zips['ctd'] = f'/api/dossiers/{did}/exports/{exp_id}/ctd.zip'
        for out in [o for o in ('ectd32', 'ectd40') if o in outputs]:
            hist = st.history(did, out)
            seq = next_seq(hist, out)
            follow = bool(hist)
            if follow:
                if not sub.get('type'):
                    raise ExportError(422, 'E-SUBMISSION', 'A follow-on sequence needs its submission type (e.g. var-pac-b).',
                                      'التسلسل التالي محتاج نوع التقديم (مثلاً var-pac-b).')
                submitted = {lf['doc_id'] for h in hist for lf in h['leaves']}
                covers = [x for x in docs_ectd if x.node == '1.0' and x.name != 'tracking']
                if not covers or all(c.doc_id in submitted for c in covers):
                    raise ExportError(409, 'E-COVER', f'Generate the cover letter for sequence {seq} first (a new cover letter goes in every sequence).',
                                      f'ولّد خطاب التغطية للتسلسل {seq} الأول (كل تسلسل له خطاب تغطية جديد).')
            stype = sub.get('type') or env.get('submission_type', 'maa')
            if region == 'eu' and not follow and stype not in ectd32_eu.default_profile().values['submission_types']:
                stype = 'maa'                             # the dossier's first sequence: a marketing authorisation application
            unit = sub.get('unit') or 'initial'
            activity = seq if unit in ('initial', 'reformat') else sub.get('activity') or (hist[-1].get('activity') if hist else seq)
            act_row = next((h for h in hist if h['seq'] == activity), None)
            # tracking table rebuilt from the history (M1-44, tool-generated)
            rows = [{'sequence': str(h['seq']), 'related': str(h.get('activity') or ''), 'description': h['envelope'].get('description', ''),
                     'type': h['envelope'].get('type', ''), 'unit': h['envelope'].get('unit', ''),
                     'date': time.strftime('%Y-%m-%d', time.localtime(h['created'])), 'tracking': env.get('tracking', ''),
                     'status': 'Submitted'} for h in hist]
            desc = sub.get('description') or (env.get('description') if not follow else stype)
            rows.append({'sequence': str(seq), 'related': str(activity), 'description': desc, 'type': stype, 'unit': unit,
                         'date': time.strftime('%Y-%m-%d'), 'tracking': sub.get('tracking') or env.get('tracking', ''),
                         'status': 'This sequence'})
            tdir = Path(tempfile.mkdtemp())
            letters.tracking_table({'trade_name': env.get('invented_name') or d['name'], 'sequences': rows}, tdir / 'tracking.docx')
            try:
                tpdf = to_pdf(tdir / 'tracking.docx')
            except RuntimeError:                         # no LibreOffice (browser edition): a text-only PDF of the same table
                tpdf = basic_pdf(tdir / 'tracking.docx')
            tdoc = ectd32.Doc('1.0', str(tpdf), f'Tracking table — sequence {seq}', name='tracking', doc_id=f'tracking-{out}-{seq}')
            docs = docs_ectd + [tdoc]
            if region == 'eu':
                tracking = [sub.get('tracking') or env.get('tracking') or 'to be advised']
                e = eu_envelope(d, prof, sub, hist, seq, stype, unit, activity, desc, tracking)
                docs = ectd32_eu.resolve(docs, e)            # each document's country before the plan: one location per document
            steps = plan(hist, docs, current_ids | {tdoc.doc_id})
            if region != 'eu':
                tracking = [sub.get('tracking') or env['tracking']]
            if out == 'ectd32' and region == 'eu':
                root = lc / 'ectd-3.2.2'
                r = ectd32_eu.write(root, e, product, to_ectd32(steps))
                prev = sorted(p for p in root.iterdir() if p.is_dir() and p.name != seq)
                reports['eCTD 3.2.2 (EU M1 3.1.1)'] = v32eu.validate(r['path'], ectd32_eu.DEFAULT_PROFILE, previous=prev)
                _zip(root, seq, base / 'ectd32.zip')
            elif out == 'ectd32':
                root = lc / 'ectd-3.2.2'
                e = ectd32.Envelope(identifier=env['application_uuid'], submission_type=stype, tracking=tracking, unit=unit,
                                    applicant=env['applicant'], invented_name=env.get('invented_name', d['name']),
                                    registration=ectd32.REG_TYPE[prof.licence], marketing=env.get('marketing', 'local'),
                                    inn=env.get('inn', []), sequence=seq, related_sequence=[activity],
                                    description=desc, mode=sub.get('mode') if stype.startswith('var-') else None)
                r = ectd32.write(root, e, product, to_ectd32(steps))
                prev = sorted(p for p in root.iterdir() if p.is_dir() and p.name != seq)
                reports['eCTD 3.2.2'] = v32.validate(r['path'], ectd32.DEFAULT_PROFILE, previous=prev)
                _zip(root, seq, base / 'ectd32.zip')
            else:
                root = lc / 'ectd-4.0'
                suuid = str(uuid.uuid4()) if unit == 'initial' else (act_row or {}).get('submission_uuid') or str(uuid.uuid4())
                e4 = ectd40.Envelope4(application_uuid=env['application_uuid'], submission_uuid=suuid, tracking=tracking[0],
                                      submission_type=stype, unit=unit, sequence=seq, title=desc, applicant=env['applicant'],
                                      applicant_portal_id=env.get('portal_id', 'UNKNOWN'),
                                      product_name=env.get('invented_name', d['name']), inn=env.get('inn', []),
                                      registration=ectd32.REG_TYPE[prof.licence], marketing=env.get('marketing', 'local'))
                docs4, suspend = to_ectd40(steps)
                r = ectd40.write(root, e4, product, docs4, profile=p40, suspend=suspend)
                reports['eCTD 4.0'] = v40.validate(r['path'], p40, ig_zip, st.root / 'cache')
                _zip(root, f"{env['application_uuid'].lower()}/{seq}", base / 'ectd40.zip')
                e = e4
            shutil.rmtree(tdir, ignore_errors=True)
            results[out] = r['path']
            zips[out] = f'/api/dossiers/{did}/exports/{exp_id}/{out}.zip'
            seqinfo[out] = {'sequence': seq, 'operations': {k: sum(1 for s_ in steps if s_.op == k) for k in ('new', 'replace', 'delete')}}
            envj = {'type': stype, 'unit': unit, 'description': desc, 'tracking': tracking[0]}
            if region == 'eu':
                envj |= {'procedure': e.procedure, 'countries': e.countries}
            done.append((out, seq, activity, getattr(e, 'submission_uuid', None), envj, r['history'], r['path']))
    except WriterError as ex:
        shutil.rmtree(base, ignore_errors=True)
        for out, seq, *_rest, path in done:
            shutil.rmtree(path, ignore_errors=True)          # no half-recorded sequence
        raise ExportError(422, 'E-WRITER', f'Export failed: {ex}', f'التصدير فشل: {ex}')
    except ExportError:
        shutil.rmtree(base, ignore_errors=True)
        for out, seq, *_rest, path in done:
            shutil.rmtree(path, ignore_errors=True)
        raise
    for out, seq, activity, suuid, envj, history, path in done:
        st.record_submission(did, out, seq, activity, suuid, envj, history, path)
    shutil.rmtree(work, ignore_errors=True)
    if reports:
        (base / 'validation-report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding='utf-8')
        (base / 'validation-report.html').write_text(vreport.render(d['name'], reports, vreport.EU_NOTE if region == 'eu' else vreport.EG_NOTE),
                                                     encoding='utf-8')
    st.db.execute('insert into export values (?,?,?,?,?,?)', (exp_id, did, json.dumps(outputs), str(base), int(ack), time.time()))
    st.db.commit()
    st.audit(did, 'export', id=exp_id, outputs=outputs, acknowledged=ack, sequences=seqinfo,
             validation={k: r['counts'] for k, r in reports.items()})
    return {'id': exp_id, 'downloads': zips, 'ctd_only': ctd_only, 'sequences': seqinfo,
            'validation': {k: {'ok': r['ok'], 'counts': r['counts'], 'coverage': r['coverage'], 'label': r['label']}
                           for k, r in reports.items()},
            'report': f'/api/dossiers/{did}/exports/{exp_id}/validation-report.html' if reports else None,
            'label': 'Conforms to EDA drafts + ICH (provisional EG profiles) — not «EDA-valid».' if egypt else
                     'eCTD 3.2.2 with EU Module 1 v3.1.1 (the EMA\'s DTD), checked here against the EU validation criteria v8.2 — run an '
                     'EMA-accepted validator before submission; and the CTD folders.' if region == 'eu' and 'ectd32' in outputs else
                     f"CTD folders in the order of {st.pack(d['pack']).authority['name']['en']}'s Module 1 and the common CTD — the authority's own submission rules (portal, file naming, eCTD) still apply."}
