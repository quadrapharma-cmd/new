"""Lifecycle-aware export (P1 + P3).

eCTD outputs live in a per-dossier lifecycle folder that accumulates sequences
(<workspace>/lifecycle/<dossier>/ectd-3.2.2/0000, 0001… and ectd-4.0/<app>/1, 2…),
exactly like a company's eCTD archive. Each export computes the next sequence from
the submission history: only new / replaced / deleted documents go into it; the
tracking table (M1-44) is rebuilt from the history every time. The download zip
holds just the new sequence (what is uploaded to the portal)."""
import json, shutil, tempfile, time, uuid, zipfile
from types import SimpleNamespace
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


WORKING = {'en': 'WORKING COPY — NOT FOR SUBMISSION', 'ar': 'نسخة عمل — ليست للتقديم'}
WORKING_NOTE = '00-WORKING-COPY-NOT-FOR-SUBMISSION.txt'
WHY_NOT_PDF = {'en': 'an eCTD takes PDF only', 'ar': 'eCTD يأخذ ملفات PDF فقط'}
WHY_WORD = {'en': 'a Word file: add its PDF to the item (save it as PDF from Word)', 'ar': 'ملف Word: أضف نسخة PDF منه في البند (احفظه بصيغة PDF من Word)'}
WHY_WRITER = (                                    # the eCTD writers' own reasons for a document, said in Arabic too
    ('needs pi_type and lang', 'نوع النشرة (SmPC أو PIL) ولغتها ناقصان: افتح البند واخترهما'),
    ('needs substance and manufacturer', 'المادة الفعالة ومصنّعها ناقصان لمستند 3.2.S هذا'),
    ('needs an indication', 'دواعي الاستعمال (indication) ناقصة في بيانات المنتج'),
    ('needs its country', 'الدولة التي يخصها هذا المستند ناقصة'),
    ('the language is one of', 'لغة المستند ناقصة أو ليست من لغات الجهة الرقابية'),
    ('not a document heading', 'هذا البند ليس له موضع مستند في Module 1 الخاص بـ eCTD'),
)


def _why(msg):
    msg = str(msg)
    return {'en': msg, 'ar': next((ar for key, ar in WHY_WRITER if key in msg), 'موضعه في eCTD يحتاج إلى تفاصيل: ' + msg)}


def _zip(src_root, rel_folder, out, note=None):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        if note:                                          # a working copy says what it is beside its sequence, never inside it
            zf.writestr(WORKING_NOTE, note)
        for f in sorted((src_root / rel_folder).rglob('*')):
            if f.is_file():
                zf.write(f, f.relative_to(src_root))


def _working_text(note, left_out):
    """What goes beside a working copy's eCTD sequence in its zip: what it is, in both languages."""
    lines = [WORKING['en'], WORKING['ar'], '',
             "This eCTD sequence is written from what the dossier holds now, by the program's own eCTD writer, so that its XML "
             "(index.xml and the regional XML) can be seen before the dossier is complete. It is not recorded as a submission: the next "
             "real export takes the same sequence number. Required documents still missing are not in it (00-MISSING.txt in the CTD "
             "working copy lists them).",
             'كُتب هذا التسلسل مما في الملف الآن، بكاتب eCTD نفسه في البرنامج، لتطّلع على ملفات XML (index.xml وملف XML الإقليمي) '
             'قبل اكتمال الملف. غير مسجَّل على أنه تقديم: التصدير الفعلي التالي يأخذ رقم التسلسل نفسه. المستندات المطلوبة الناقصة ليست فيه '
             '(قائمتها في 00-MISSING.txt ضمن نسخة العمل الخاصة بـ CTD).', '', note['en'], note['ar']]
    if left_out:
        lines += ['', 'Left out of this eCTD / تُرك خارج هذا الـ eCTD:'] + [f"- {t['name']}: {t['why']['en']} / {t['why']['ar']}" for t in left_out]
    return '\n'.join(lines) + '\n'


def _working_ectd(st, did, d, slots, base, exp_id, sub, p40, ig_zip, note):
    """The working copy's eCTD: the sequence(s) this authority takes (3.2.2 with its own Module 1; 4.0 for Egypt), written from what
    the dossier holds now by the real export's own code (_sequences, working) — the XML the real export will write — beside the
    export, never recorded. Only PDFs go in (a Word file through its PDF, as in the real export); anything else stays in the CTD
    folders and is named. Each output on its own: one that cannot be written says why, and the others are still written. None when
    the authority takes no eCTD."""
    pk = st.pack(d['pack'])
    region = pk.ectd_region
    if not region:
        return None
    env, pr = d.get('envelope') or {}, d.get('product') or {}
    outs = [o for o in pk.outputs_for(env.get('country')) if o in ('ectd32', 'ectd40')]
    prof = Profile.from_dict(d['profile'])
    product = ectd32.Product(pr.get('name') or d['name'], pr.get('dosageform') or 'to be advised',
                             pr.get('manufacturer') or env.get('applicant') or 'to be advised', pr.get('indication'))
    work = base / '_ectd_files'
    work.mkdir(parents=True, exist_ok=True)
    files, left_out = {}, []
    for s in slots:
        for doc in st.documents(did, s.slot_id) if s.active else []:
            meta = doc.get('meta') or {}
            if meta.get('external'):
                continue
            ext = '.' + doc['filename'].rsplit('.', 1)[-1].lower() if '.' in doc['filename'][-6:] else ''
            src = st.blob_path(doc['sha256'])
            if ext not in ('.pdf', '.docx', '.doc', '.rtf', '.odt'):
                with open(src, 'rb') as fh:
                    if fh.read(5) != b'%PDF-':           # a spreadsheet, a picture…: the CTD folders keep it, the eCTD does not take it
                        left_out.append({'name': _named(doc['title'], doc['filename']), 'why': WHY_NOT_PDF})
                        continue
                ext = '.pdf'
            p = work / f"{doc['id']}{ext}"
            shutil.copyfile(src, p)
            ref = meta.get('reference') or {}
            files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **meta, 'doc_id': doc['id'], 'ext': ext,
                                                    'orig': doc['filename'],
                                                    **({'ref': f"../{ref['seq']}/{ref['href']}"} if ref.get('output') == 'ectd32' else {})})
    files_e = ectd_files(files, left_out=left_out)
    docs_all, _ = docs_for(slots, prof, files_e)
    eff = {k: v for k, v in files_e.items() if not k.startswith('M1-44')}
    x = SimpleNamespace(d=d, env=env, pr=pr, prof=prof, product=product, region=region, slots=slots, files_e=files_e,
                        docs_ectd=list(docs_for(slots, prof, eff)[0]), current_ids={y.doc_id for y in docs_all})
    res = {'region': region, 'downloads': {}, 'sequences': {}, 'reports': {}, 'skipped': {}, 'left_out': left_out}
    for o in outs:
        docs, r = list(x.docs_ectd), None
        for attempt in (1, 2):
            y = SimpleNamespace(**{**vars(x), 'docs_ectd': docs})
            try:
                r = _sequences(st, did, y, [o], sub, base, exp_id, p40, ig_zip, working=_working_text(note, left_out))
                break
            except ExportError as ex:
                res['skipped'][o] = {'en': ex.en, 'ar': ex.ar}
            except WriterError as ex:                 # a document the writer cannot take: each one tried alone, those left out, the rest written
                bad = _cannot_take(st, did, y, o, sub, base, exp_id, p40, ig_zip, note) if attempt == 1 else None
                if bad:
                    for doc in [d for d in docs if d.doc_id in bad]:
                        entry = {'name': _named(doc.title, (doc.aliases or (None,))[0]), 'why': _why(bad[doc.doc_id])}
                        if entry not in left_out:
                            left_out.append(entry)
                    docs = [d for d in docs if d.doc_id not in bad]
                    shutil.rmtree(base / ('ectd-3.2.2' if o == 'ectd32' else 'ectd-4.0'), ignore_errors=True)   # what the refused try left
                    continue
                res['skipped'][o] = {'en': f'Not written: {ex}', 'ar': f'لم يُكتب: {_why(ex)["ar"]}'}
            except Exception as ex:                   # the CTD folders are still given; this output says why it is not
                res['skipped'][o] = {'en': f'Not written: {ex}', 'ar': f'لم يُكتب: {ex}'}
            break
        if r:
            res['downloads'].update(r['zips'])
            res['sequences'].update(r['seqinfo'])
            res['reports'].update(r['reports'])
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(base / '_probe', ignore_errors=True)
    return res


def _cannot_take(st, did, x, o, sub, base, exp_id, p40, ig_zip, note):
    """The documents an output's sequence cannot take, each written alone beside a plain tracking page, without the checks:
    {doc_id: the writer's reason}. Empty when even a sequence without them is refused (then the sequence itself is the problem)."""
    tdir = Path(tempfile.mkdtemp())
    letters.tracking_table({'trade_name': x.d['name'], 'sequences': [{'sequence': '0000', 'related': '0000', 'description': WORKING['en'],
                                                                      'type': '', 'unit': '', 'date': time.strftime('%Y-%m-%d'),
                                                                      'tracking': '', 'status': 'Working copy'}]}, tdir / 'tracking.docx')
    tp = basic_pdf(tdir / 'tracking.docx')

    def refused(docs):
        probe = base / '_probe'
        try:
            _sequences(st, did, SimpleNamespace(**{**vars(x), 'docs_ectd': docs}), [o], sub, probe, exp_id, p40, ig_zip,
                       working=_working_text(note, []), check=False, tracking_pdf=tp)
            return None
        except (WriterError, ExportError) as ex:
            return str(ex) if isinstance(ex, WriterError) else ex.en
        finally:
            shutil.rmtree(probe, ignore_errors=True)
    try:
        if refused([]):
            return {}
        return {d.doc_id: why for d in x.docs_ectd for why in [refused([d])] if why}
    finally:
        shutil.rmtree(tdir, ignore_errors=True)


def _working_copy(st, did, g, sub=None, p40=None, ig_zip=None):
    """The CTD folders with what the dossier holds now and the list of what is missing, and — where the authority takes an eCTD — its
    sequence with its XML, all marked «not for submission» and never recorded (_working_ectd)."""
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
            'ar': f"نسخة عمل — ليست للتقديم. {n_docs} مستند في موضعه؛ {missing} بند مطلوب ما زال ناقصًا، {len(g.get('non_conforming') or [])} يحتاج إلى إصلاح، "
                  f"{len(g.get('unsigned') or [])} مسودة تحتاج إلى توقيع. راجع 00-MISSING.txt."}
    try:
        res = ctd.write(base / 'ctd', d['name'] + ' - WORKING COPY', slots, files, working=note)
        _zip(Path(res['path']).parent, Path(res['path']).name, base / 'ctd-working.zip')
    except (WriterError, OSError) as ex:
        shutil.rmtree(base, ignore_errors=True)
        raise ExportError(422, 'E-WRITER', f'Export failed: {ex}', f'فشل التصدير: {ex}')
    shutil.rmtree(work, ignore_errors=True)
    try:
        ectd = _working_ectd(st, did, d, slots, base, exp_id, sub or {}, p40, ig_zip, note)
    except Exception as ex:                           # the CTD working copy is given whatever happens to its eCTD
        ectd = {'region': st.pack(d['pack']).ectd_region, 'downloads': {}, 'sequences': {}, 'reports': {}, 'left_out': [],
                'skipped': {'ectd': {'en': f'Not written: {ex}', 'ar': f'لم يُكتب: {ex}'}}}
    downloads = {'ctd-working': f'/api/dossiers/{did}/exports/{exp_id}/ctd-working.zip', **(ectd['downloads'] if ectd else {})}
    reports = ectd['reports'] if ectd else {}
    if reports:
        (base / 'validation-report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding='utf-8')
        (base / 'validation-report.html').write_text(vreport.render(f"{d['name']} — {WORKING['en']}", reports,
                                                                    vreport.EU_NOTE if ectd['region'] == 'eu' else vreport.EG_NOTE), encoding='utf-8')
    sequences = ectd['sequences'] if ectd else {}
    st.db.execute('insert into export values (?,?,?,?,?,?)', (exp_id, did, json.dumps(list(downloads)), str(base), 0, time.time()))
    st.db.commit()
    st.audit(did, 'export.working', id=exp_id, documents=n_docs, missing_required=missing,
             ectd={o: v['sequence'] for o, v in sequences.items()})
    return {'id': exp_id, 'working': True, 'downloads': downloads, 'documents': n_docs,
            'missing_required': missing, 'non_conforming': len(g.get('non_conforming') or []), 'unsigned': len(g.get('unsigned') or []),
            'sequences': sequences,
            'validation': {k: {'ok': r['ok'], 'counts': r['counts'], 'coverage': r['coverage'], 'label': r['label']} for k, r in reports.items()},
            'report': f'/api/dossiers/{did}/exports/{exp_id}/validation-report.html' if reports else None,
            'ectd': {k: ectd[k] for k in ('region', 'left_out', 'skipped')} if ectd else None,
            'ctd_only': [], 'label': note['en'], 'label_ar': note['ar']}


def _named(title, filename):
    """A document as a person finds it: its item's title and its own file name."""
    return f'{title} ({filename})' if title and filename and title != filename else (title or filename or '')


def ectd_files(files, left_out=None):
    """The files an eCTD takes: PDF. A Word document (the proposed leaflet, asked in Word for the One Submission) goes in as its PDF —
    the one the item holds beside it with the same language and type, else converted here (LibreOffice); without either the eCTD
    export stops and says so (it never writes a Word file under a .pdf name). A working copy passes `left_out` (a list): such a
    Word file is then left out of its eCTD and named there, and the rest is still written."""
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
                if left_out is not None:
                    left_out.append({'name': _named(f.get('title'), f.get('orig')), 'why': WHY_WORD})
                    continue
                raise ExportError(422, 'E-WORD-PDF', f"«{f.get('title')}» is a Word file and an eCTD takes PDF: add its PDF to the item "
                                  '(save it as PDF from Word), or export on a machine with LibreOffice.',
                                  f"«{f.get('title')}» ملف Word و eCTD لا يقبل إلا PDF: أضف نسخة PDF منه إلى البند (احفظه بصيغة PDF من Word)، "
                                  'أو صدِّر من نسخة الحاسوب التي تحوّل ملفات Word تلقائيًا.')
            keep.append(dict(f, file=str(pdf), ext='.pdf'))
        out[sid] = keep
    return out


def last_tracking(hist):
    """The envelope fills itself from the sequence before it (updates list, item 44): the same application keeps its tracking /
    procedure number unless this sequence names another."""
    for h in reversed(hist or []):
        tr = (h.get('envelope') or {}).get('tracking')
        if tr and tr != 'to be advised':
            return tr
    return None


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


def gcc_envelope(d, sub, seq, stype, unit, activity, desc, hist):
    """The GCC envelopes (App. 1): one per destination — the ones asked for, else the dossier's country — with the application
    number(s) the GCC issued, the submission and unit types of App. 5, and the procedure (gcc for several states, national for one)."""
    from ..writers import ectd32_gcc
    env = d['envelope'] or {}
    values = ectd32_gcc.default_profile().values
    cs = [c.lower() for c in (sub.get('countries') or [env.get('country') or 'sa'])]
    cs = [c for c in cs if c in ectd32_gcc.AGENCY] or ['sa']
    if stype not in values['submission_types']:
        stype = 'new-gen' if not hist else 'var-type1'
    if unit not in values['units']:
        unit = 'initial'
    number = sub.get('tracking') or last_tracking(hist) or env.get('tracking')
    return ectd32_gcc.EnvelopeGCC(countries=cs, application=[number] if number and number != 'to be advised' else [],
                                  applicant=env.get('applicant') or d['name'], submission_type=stype, unit=unit,
                                  procedure=sub.get('procedure') or ('gcc' if len(cs) > 1 else 'national'),
                                  invented_names=[env.get('invented_name') or d['name']], inn=env.get('inn') or [], atc=env.get('atc') or [],
                                  sequence=seq, related_sequence=[activity] if hist else None, description=desc)


def gcc_docs(docs, files, slots):
    """The leaflet's language from its item (1.3.3.1 Arabic, 1.3.3.2 English) where the document does not say it."""
    from dataclasses import replace
    lang = {}
    for s in slots:
        for f in files.get(s.slot_id, []):
            lang[f.get('doc_id')] = 'ar' if s.req_id.endswith('1.3.3.1') else 'en'
    return [replace(x, lang=x.lang or lang.get(x.doc_id)) if x.node in ('1.3.1', '1.3.2', '1.3.3') else x for x in docs]


def eu_envelope(d, prof, sub, hist, seq, stype, unit, activity, desc, tracking):
    """The EU envelope(s) of a sequence from the dossier, its answers and the follow-on's details (SPEC 3.1.1 §Envelope)."""
    env, pr = d['envelope'], d['product']
    proc, countries = eu_countries(d, prof, sub, hist)
    values = ectd32_eu.default_profile().values
    if not countries:
        raise ExportError(422, 'E-ENVELOPE', 'Name the countries of the procedure (the EU envelopes).', 'حدِّد دول الإجراء (الـ envelope الأوروبي).')
    bad = [c for c in countries if c not in values['env_countries']]
    if bad:
        raise ExportError(422, 'E-ENVELOPE', f'Not an EU M1 destination: {bad}.', f'ليست من دول Module 1 الأوروبي: {bad}.')
    if stype not in values['submission_types']:
        raise ExportError(422, 'E-SUBMISSION', f'An EU submission type is one of: {", ".join(values["submission_types"])}.',
                          'نوع التقديم الأوروبي واحد من: ' + '، '.join(values['submission_types']) + '.')
    if unit not in values['units']:
        raise ExportError(422, 'E-SUBMISSION', f'An EU submission unit is one of: {", ".join(values["units"])}.',
                          'نوع الوحدة الأوروبي واحد من: ' + '، '.join(values['units']) + '.')
    applicant = env.get('applicant') or pr.get('manufacturer')
    if not applicant:
        raise ExportError(422, 'E-ENVELOPE', "The envelope needs the applicant's name.", 'يحتاج الـ envelope إلى اسم مقدّم الطلب.')
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


def _earlier(st, did, hist):
    """Where the documents of the earlier sequences are, by the names a link may use for them (links.earlier_targets)."""
    from .. import links
    names_of = {d['id']: [d['filename'], d['title']] for d in st.documents(did)}       # current documents: a replaced one is in this sequence
    return links.earlier_targets(hist, names_of)


def _previous(lroot, seq):
    """The sequences of the dossier's lifecycle folder before `seq`, for the lifecycle checks."""
    return sorted(p for p in lroot.iterdir() if p.is_dir() and p.name != seq) if lroot.is_dir() else []


def _sequences(st, did, x, outputs, sub, base, exp_id, p40, ig_zip, replace_last=False, working=None, check=True, tracking_pdf=None):
    """The eCTD sequence of each of `outputs` (ectd32, ectd40), from x: the dossier (d, env, pr, prof, product, region, slots) and its
    documents for the eCTD (files_e, docs_ectd, current_ids). A real export writes each sequence into the dossier's lifecycle folder
    under the next number of its history, and the caller records it (`done`). A working copy (`working`: the note that goes beside
    it) writes it beside the export instead, under the number the next real sequence would take, its envelope's description
    beginning «WORKING COPY — NOT FOR SUBMISSION», without the follow-on's checks (its type, its new cover letter), and nothing is
    recorded: the history, the lifecycle folder and the next number stay as they were."""
    d, env, prof, product, region = x.d, x.env, x.prof, x.product, x.region
    lc = st.root / 'lifecycle' / did
    applicant = (env.get('applicant') or x.pr.get('manufacturer') or d['name']) if working else None
    results, reports, zips, seqinfo, done = {}, {}, {}, {}, []
    try:
        for out in [o for o in ('ectd32', 'ectd40') if o in outputs]:
            hist = st.history(did, out)
            zname = f'{out}-working' if working else out
            if replace_last and not working and hist and not hist[-1]['frozen']:       # the last one never went: this export takes its number
                st.discard_sequence(did, out, hist[-1]['seq'])
                hist = st.history(did, out)
            seq = next_seq(hist, out)
            follow = bool(hist)
            if follow and not working:                    # a working copy asks neither the follow-on's type nor its new cover letter
                if not sub.get('type'):
                    raise ExportError(422, 'E-SUBMISSION', 'A follow-on sequence needs its submission type (e.g. var-pac-b).',
                                      'يحتاج التسلسل التالي إلى نوع التقديم (مثلًا var-pac-b).')
                submitted = {lf['doc_id'] for h in hist for lf in h['leaves']}
                covers = [c for c in x.docs_ectd if c.node == '1.0' and c.name != 'tracking']
                if not covers or all(c.doc_id in submitted for c in covers):
                    raise ExportError(409, 'E-COVER', f'Generate the cover letter for sequence {seq} first (a new cover letter goes in every sequence).',
                                      f'ولِّد خطاب التغطية للتسلسل {seq} أولًا (لكل تسلسل خطاب تغطية جديد).')
            stype = sub.get('type') or env.get('submission_type', 'maa')
            if region == 'eu' and not follow and stype not in ectd32_eu.default_profile().values['submission_types']:
                stype = 'maa'                             # the dossier's first sequence: a marketing authorisation application
            unit = sub.get('unit') or 'initial'
            activity = seq if unit in ('initial', 'reformat') else sub.get('activity') or (hist[-1].get('activity') if hist else seq)
            act_row = next((h for h in hist if h['seq'] == activity), None)
            # tracking table rebuilt from the history (M1-44, tool-generated)
            rows = [{'sequence': str(h['seq']), 'related': str(h.get('activity') or ''), 'description': h['envelope'].get('description', ''),
                     'type': h['envelope'].get('type', ''), 'unit': h['envelope'].get('unit', ''),
                     'date': time.strftime('%Y-%m-%d', time.localtime(h['created'])), 'tracking': h['envelope'].get('tracking') or env.get('tracking', ''),
                     'status': 'Submitted'} for h in hist]
            desc = sub.get('description') or (env.get('description') if not follow else stype) or (
                'Initial marketing authorisation application' if not follow else stype)          # the envelope never goes without its description
            if working:                                   # the XML itself says what it is
                desc = f"{WORKING['en']} — {desc}"
            rows.append({'sequence': str(seq), 'related': str(activity), 'description': desc, 'type': stype, 'unit': unit,
                         'date': time.strftime('%Y-%m-%d'), 'tracking': sub.get('tracking') or last_tracking(hist) or env.get('tracking', ''),
                         'status': 'Working copy — not for submission' if working else 'This sequence'})
            tdir = Path(tempfile.mkdtemp())
            if tracking_pdf:                             # a working copy's probe of one document: any tracking page does
                tpdf = tracking_pdf
            else:
                letters.tracking_table({'trade_name': env.get('invented_name') or d['name'], 'sequences': rows}, tdir / 'tracking.docx')
                try:
                    tpdf = to_pdf(tdir / 'tracking.docx')
                except RuntimeError:                     # no LibreOffice (browser edition): a text-only PDF of the same table
                    tpdf = basic_pdf(tdir / 'tracking.docx')
            tdoc = ectd32.Doc('1.0', str(tpdf), f'Tracking table — sequence {seq}', name='tracking', doc_id=f'tracking-{out}-{seq}')
            docs = x.docs_ectd + [tdoc]
            if region == 'eu':
                tracking = [sub.get('tracking') or last_tracking(hist) or env.get('tracking') or 'to be advised']
                e = eu_envelope(d, prof, sub, hist, seq, stype, unit, activity, desc, tracking)
                docs = ectd32_eu.resolve(docs, e)            # each document's country before the plan: one location per document
            if region == 'gcc':
                e = gcc_envelope(d, sub, seq, stype, unit, activity, desc, hist)
                docs = gcc_docs(docs, x.files_e, x.slots)
            steps = plan(hist, docs, x.current_ids | {tdoc.doc_id})
            if region != 'eu':
                tracking = [sub.get('tracking') or last_tracking(hist) or env.get('tracking') or 'to be advised']
            if out == 'ectd32' and region == 'gcc':           # the Gulf: GCC Module 1 v1.5 (SFDA), its DTD and structure
                from ..writers import ectd32_gcc
                from ..validators import ectd32_gcc as v32gcc
                root = base / 'ectd-3.2.2' if working else lc / 'ectd-3.2.2'
                r = ectd32_gcc.write(root, e, product, to_ectd32(steps), links=_earlier(st, did, hist))
                if check:
                    reports['eCTD 3.2.2 (GCC M1 1.5)'] = v32gcc.validate(r['path'])
                _zip(root, seq, base / f'{zname}.zip', note=working)
            elif out == 'ectd32' and region == 'eu':
                root = base / 'ectd-3.2.2' if working else lc / 'ectd-3.2.2'
                r = ectd32_eu.write(root, e, product, to_ectd32(steps), links=_earlier(st, did, hist))
                if check:
                    reports['eCTD 3.2.2 (EU M1 3.1.1)'] = v32eu.validate(r['path'], ectd32_eu.DEFAULT_PROFILE, previous=_previous(lc / 'ectd-3.2.2', seq))
                _zip(root, seq, base / f'{zname}.zip', note=working)
            elif out == 'ectd32':
                root = base / 'ectd-3.2.2' if working else lc / 'ectd-3.2.2'
                e = ectd32.Envelope(identifier=env['application_uuid'], submission_type=stype, tracking=tracking, unit=unit,
                                    applicant=applicant or env['applicant'], invented_name=env.get('invented_name', d['name']),
                                    registration=ectd32.REG_TYPE[prof.licence], marketing=env.get('marketing', 'local'),
                                    inn=env.get('inn', []), sequence=seq, related_sequence=[activity],
                                    description=desc, mode=sub.get('mode') if stype.startswith('var-') else None)
                r = ectd32.write(root, e, product, to_ectd32(steps), links=_earlier(st, did, hist))
                if check:
                    reports['eCTD 3.2.2'] = v32.validate(r['path'], ectd32.DEFAULT_PROFILE, previous=_previous(lc / 'ectd-3.2.2', seq))
                _zip(root, seq, base / f'{zname}.zip', note=working)
            else:
                root = base / 'ectd-4.0' if working else lc / 'ectd-4.0'
                suuid = str(uuid.uuid4()) if unit == 'initial' else (act_row or {}).get('submission_uuid') or str(uuid.uuid4())
                e4 = ectd40.Envelope4(application_uuid=env['application_uuid'], submission_uuid=suuid, tracking=tracking[0],
                                      submission_type=stype, unit=unit, sequence=seq, title=desc, applicant=applicant or env['applicant'],
                                      applicant_portal_id=env.get('portal_id', 'UNKNOWN'),
                                      product_name=env.get('invented_name', d['name']), inn=env.get('inn', []),
                                      registration=ectd32.REG_TYPE[prof.licence], marketing=env.get('marketing', 'local'))
                docs4, suspend = to_ectd40(steps)
                r = ectd40.write(root, e4, product, docs4, profile=p40, suspend=suspend)
                if check:
                    reports['eCTD 4.0'] = v40.validate(r['path'], p40, ig_zip, st.root / 'cache')
                _zip(root, f"{env['application_uuid'].lower()}/{seq}", base / f'{zname}.zip', note=working)
                e = e4
            shutil.rmtree(tdir, ignore_errors=True)
            results[out] = r['path']
            zips[zname] = f'/api/dossiers/{did}/exports/{exp_id}/{zname}.zip'
            seqinfo[out] = {'sequence': seq, 'operations': {k: sum(1 for s_ in steps if s_.op == k) for k in ('new', 'replace', 'delete')}}
            if r.get('links') and (r['links']['rewritten'] or r['links']['unresolved']):
                seqinfo[out]['links'] = r['links']        # links made relative, and the file links no document of the dossier answers
            envj = {'type': stype, 'unit': unit, 'description': desc, 'tracking': tracking[0]}
            if region == 'eu':
                envj |= {'procedure': e.procedure, 'countries': e.countries}
            done.append((out, seq, activity, getattr(e, 'submission_uuid', None), envj, r['history'], r['path']))
    except (WriterError, ExportError):
        for out, seq, *_rest, path in done:
            shutil.rmtree(path, ignore_errors=True)          # no half-recorded sequence
        raise
    return {'results': results, 'reports': reports, 'zips': zips, 'seqinfo': seqinfo, 'done': done}


def export(st, did, outputs, ack, sub, p40, ig_zip, working=False, replace_last=False):
    """working: a working copy — the CTD folders with what the dossier holds now and the list of what is missing, and the authority's
    eCTD sequence with its XML, whatever the gate says; all marked «not for submission», never recorded as a submission."""
    g = st.gate(did)
    if working:
        return _working_copy(st, did, g, sub, p40, ig_zip)
    if not g['ok']:
        raise ExportError(409, 'E-GATE', 'Export blocked: required documents are missing or non-conforming.',
                          'التصدير متوقف: توجد مستندات مطلوبة ناقصة أو غير مطابقة.', gate=g)
    pk = st.pack(st.dossier(did)['pack'])
    egypt, region = pk.egypt, pk.ectd_region      # the regional eCTD backbone: Egypt's (provisional) and the EU's; others get the CTD folders
    country = (st.dossier(did).get('envelope') or {}).get('country')
    if list(outputs) == ['ctd', 'ectd32', 'ectd40']:                         # nothing was asked: what this authority has
        outputs = list(pk.outputs_for(country))
    elif set(outputs) - set(pk.outputs):
        if region == 'eu':
            raise ExportError(422, 'E-OUTPUT-AUTHORITY', 'eCTD 4.0 is written for Egypt only; an EU dossier exports as CTD folders and eCTD 3.2.2 '
                              '(EU Module 1 v3.1.1).', 'eCTD 4.0 معدّ لمصر فقط؛ الملف الأوروبي يُصدَّر على هيئة مجلدات CTD و eCTD 3.2.2 (Module 1 الأوروبي 3.1.1).', gate=g)
        raise ExportError(422, 'E-OUTPUT-AUTHORITY', "The eCTD package is written for Egypt's and the EU's Module 1; this dossier exports as CTD folders.",
                          'حزمة eCTD معدّة لـ Module 1 المصري والأوروبي فقط؛ يُصدَّر هذا الملف على هيئة مجلدات CTD.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and g.get('ectd_blocking'):
        raise ExportError(409, 'E-GATE-ECTD', 'eCTD readiness: some documents carry restrictions, a Portfolio or JavaScript (the eCTD rules). '
                          'Fix them (auto-fix for company documents, a new copy from the issuer otherwise), or export the CTD folders only.',
                          'جاهزية eCTD: توجد مستندات عليها قيود أو Portfolio أو JavaScript (قواعد eCTD). أصلِحها (إصلاح تلقائي لمستندات الشركة، '
                          'ونسخة جديدة من الجهة لغيرها)، أو صدِّر مجلدات CTD فقط.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and g.get('ectd_indication'):    # ICH eCTD DTD 3.2: m2-7-3 and m5-3-5 «indication #REQUIRED»
        raise ExportError(409, 'E-GATE-INDICATION', "The eCTD needs the product's indication: the clinical summary (2.7.3) and the efficacy and "
                          'safety studies (5.3.5) carry it (ICH eCTD DTD, required). Write it on this page, or export the CTD folders only.',
                          'يحتاج eCTD إلى دواعي استعمال المستحضر: ملخص الفعالية (2.7.3) ودراسات الفعالية والأمان (5.3.5) تحملها (وهي مطلوبة في '
                          'الـ DTD الخاص بـ ICH). اكتبها في هذه الصفحة، أو صدِّر مجلدات CTD فقط.', gate=g)
    if {'ectd32', 'ectd40'} & set(outputs) and not ack and egypt:            # the EG profiles are provisional; the EU's is the EMA's own
        raise ExportError(409, 'E-PROVISIONAL-ACK', 'eCTD outputs use the provisional EG profiles; acknowledge before export.',
                          'مخرجات eCTD مبنية على ملف تعريف مصري مؤقت؛ يجب أن توافق قبل التصدير.', gate=g)
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
            ref = (doc['meta'].get('reference') or {})
            files.setdefault(s.slot_id, []).append({'file': str(p), 'title': doc['title'], **doc['meta'], 'doc_id': doc['id'], 'ext': ext,
                                                    'orig': doc['filename'],
                                                    **({'ref': f"../{ref['seq']}/{ref['href']}"} if ref.get('output') == 'ectd32' else {})})
    try:
        files_e = ectd_files(files) if region and {'ectd32', 'ectd40'} & set(outputs) else files      # an eCTD takes PDF only
    except ExportError:
        shutil.rmtree(base, ignore_errors=True)
        raise
    docs_all, ctd_only = docs_for(slots, prof, files_e) if region else ([], [])
    current_ids = {x.doc_id for x in docs_all}
    eff = {k: v for k, v in files_e.items() if not k.startswith('M1-44')}
    docs_ectd = [x for x in docs_for(slots, prof, eff)[0]] if region else []
    results, reports, zips = {}, {}, {}
    x = SimpleNamespace(d=d, env=env, pr=pr, prof=prof, product=product, region=region, slots=slots, files_e=files_e, docs_ectd=docs_ectd,
                        current_ids=current_ids)
    try:
        if 'nees' in outputs:                           # the eCTD's folders and names with PDF tables of contents (updates list, item 40)
            from ..writers import nees
            cc = (env.get('country') or (pk.authority.get('countries') or ['xx'])[0]).lower().replace('*', 'xx')
            rn = nees.write(base / 'nees', str(sub.get('nees_sequence') or '0000'), slots, files, pr.get('name') or d['name'], cc,
                            env.get('invented_name') or d['name'])
            reports['NeeS'] = nees.check(rn['path'])
            reports['NeeS']['left_out'] = rn['left_out']
            _zip(Path(rn['path']).parent, Path(rn['path']).name, base / 'nees.zip')
            results['nees'] = rn['path']
            zips['nees'] = f'/api/dossiers/{did}/exports/{exp_id}/nees.zip'
        if 'actd' in outputs:                           # the same content in the ASEAN CTD's four parts (updates list, item 45)
            from ..writers import actd
            results['actd'] = actd.write(base / 'actd', d['name'], slots, files)['path']
            _zip(Path(results['actd']).parent, Path(results['actd']).name, base / 'actd.zip')
            zips['actd'] = f'/api/dossiers/{did}/exports/{exp_id}/actd.zip'
        if 'ctd' in outputs:
            results['ctd'] = ctd.write(base / 'ctd', d['name'], slots, files)['path']
            _zip(Path(results['ctd']).parent, Path(results['ctd']).name, base / 'ctd.zip')
            zips['ctd'] = f'/api/dossiers/{did}/exports/{exp_id}/ctd.zip'
        seqs = _sequences(st, did, x, outputs, sub, base, exp_id, p40, ig_zip, replace_last=replace_last)
    except WriterError as ex:
        shutil.rmtree(base, ignore_errors=True)
        raise ExportError(422, 'E-WRITER', f'Export failed: {ex}', f'فشل التصدير: {ex}')
    except ExportError:
        shutil.rmtree(base, ignore_errors=True)
        raise
    results.update(seqs['results'])
    reports.update(seqs['reports'])
    zips.update(seqs['zips'])
    seqinfo = seqs['seqinfo']
    for out, seq, activity, suuid, envj, history, path in seqs['done']:
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
