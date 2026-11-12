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
from ..writers import ctd, ectd32, ectd40
from ..writers.ectd32 import WriterError
from ..generate import letters
from ..generate.docx_kit import to_pdf, basic_pdf
from ..validators import ectd32 as v32, ectd40 as v40, report as vreport


class ExportError(Exception):
    def __init__(self, status, code, en, ar, **extra):
        self.status, self.code, self.en, self.ar, self.extra = status, code, en, ar, extra


def _zip(src_root, rel_folder, out):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted((src_root / rel_folder).rglob('*')):
            if f.is_file():
                zf.write(f, f.relative_to(src_root))


def next_seq(hist, output):
    if not hist:
        return '0000' if output == 'ectd32' else 1
    last = hist[-1]['seq']
    return f'{int(last) + 1:04d}' if output == 'ectd32' else int(last) + 1


def export(st, did, outputs, ack, sub, p40, ig_zip):
    g = st.gate(did)
    if not g['ok']:
        raise ExportError(409, 'E-GATE', 'Export blocked: required documents are missing or non-conforming.',
                          'التصدير متوقف: فيه مستندات مطلوبة ناقصة أو غير مطابقة.', gate=g)
    egypt = st.pack(st.dossier(did)['pack']).egypt
    if not egypt:                                        # the regional eCTD backbone is written for Egypt; every other authority gets the CTD folders
        if list(outputs) == ['ctd', 'ectd32', 'ectd40']:                     # nothing was asked: what this authority has
            outputs = ['ctd']
        elif {'ectd32', 'ectd40'} & set(outputs):
            raise ExportError(422, 'E-OUTPUT-AUTHORITY', "The eCTD package is written for Egypt's regional Module 1 only; this dossier exports as CTD folders.",
                              'حزمة الـ eCTD مكتوبة لموديول ١ المصري بس؛ الملف ده بيتصدّر كمجلدات CTD.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and not ack:
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
            p = work / f"{doc['id']}.pdf"
            shutil.copyfile(st.blob_path(doc['sha256']), p)
            files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **doc['meta'], 'doc_id': doc['id']})
    docs_all, ctd_only = docs_for(slots, prof, files) if egypt else ([], [])
    current_ids = {x.doc_id for x in docs_all}
    eff = {k: v for k, v in files.items() if not k.startswith('M1-44')}
    docs_ectd = [x for x in docs_for(slots, prof, eff)[0]] if egypt else []
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
            unit = sub.get('unit') or 'initial'
            activity = seq if unit == 'initial' else sub.get('activity') or (hist[-1].get('activity') if hist else seq)
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
            steps = plan(hist, docs, current_ids | {tdoc.doc_id})
            tracking = [sub.get('tracking') or env['tracking']]
            if out == 'ectd32':
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
            done.append((out, seq, activity, getattr(e, 'submission_uuid', None),
                         {'type': stype, 'unit': unit, 'description': desc, 'tracking': tracking[0]}, r['history'], r['path']))
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
        (base / 'validation-report.html').write_text(vreport.render(d['name'], reports), encoding='utf-8')
    st.db.execute('insert into export values (?,?,?,?,?,?)', (exp_id, did, json.dumps(outputs), str(base), int(ack), time.time()))
    st.db.commit()
    st.audit(did, 'export', id=exp_id, outputs=outputs, acknowledged=ack, sequences=seqinfo,
             validation={k: r['counts'] for k, r in reports.items()})
    return {'id': exp_id, 'downloads': zips, 'ctd_only': ctd_only, 'sequences': seqinfo,
            'validation': {k: {'ok': r['ok'], 'counts': r['counts'], 'coverage': r['coverage'], 'label': r['label']}
                           for k, r in reports.items()},
            'report': f'/api/dossiers/{did}/exports/{exp_id}/validation-report.html' if reports else None,
            'label': 'Conforms to EDA drafts + ICH (provisional EG profiles) — not «EDA-valid».' if egypt else
                     f"CTD folders in the order of {st.pack(d['pack']).authority['name']['en']}'s Module 1 and the common CTD — the authority's own submission rules (portal, file naming, eCTD) still apply."}
