"""Deficiency letter and assessment report (DOCX; PDF through LibreOffice when present, else a text PDF).
Both carry the simulation statement: produced by the applicant's own review tool, never issued by EDA."""
import time
from pathlib import Path
from ..generate.docx_kit import new_doc, para, table, to_pdf, basic_pdf, find_soffice

SEV = {'critical': 'Critical', 'major': 'Major', 'minor': 'Minor', 'note': 'Note'}
SEV_AR = {'critical': 'حرج', 'major': 'رئيسي', 'minor': 'ثانوي', 'note': 'ملاحظة'}


def _dept(pack, dept_id):
    return next((d for d in pack.departments() if d['id'] == dept_id), {'id': dept_id, 'en': dept_id, 'ar': dept_id, 'body': {'en': '', 'ar': ''}})


def letter_items(findings, dept_id):
    return [f for f in findings if f['dept'] == dept_id and f['verdict'] == 'deficient' and f['severity'] != 'note'
            and f['status'] != 'withdrawn' and not (f['origin'] == 'ai' and not f.get('confirmed_by'))]


def _head(d, title_en, title_ar, dossier, run, pack, dept):
    para(d, 'SIMULATION — produced by the applicant’s review tool from EDA’s published documents. NOT an EDA letter.', bold=True)
    para(d, 'محاكاة — أعدّتها أداة المراجعة الخاصة بمقدم الطلب من مستندات الهيئة المنشورة. ليس خطاباً صادراً عن الهيئة.', ar=True, bold=True)
    para(d, f"{title_en} — {dept['en']}", bold=True, size=14)
    para(d, f"{title_ar} — {dept['ar']}", ar=True, bold=True, size=13)
    para(d, f"Simulated body: {dept['body']['en']} · knowledge pack {run['pack_version']} · run {run['id']} · {time.strftime('%Y-%m-%d', time.localtime(run['created']))}")
    env = dossier.get('envelope') or {}
    table(d, ['Item', 'Value'], [('Applicant', env.get('applicant') or dossier.get('product', {}).get('manufacturer') or ''),
                                 ('Product', dossier.get('name', '')), ('Tracking', ', '.join(env.get('tracking') or []) if isinstance(env.get('tracking'), list) else (env.get('tracking') or '')),
                                 ('Submission', f"{dossier['profile'].get('dossier_kind', '')} · {dossier['profile'].get('origin', '')} · {dossier['profile'].get('activity', '')} · {dossier['profile'].get('route', '')}"),
                                 ('Strictness', run['options'].get('strictness', '')), ('Clock', f"Stopped at technical evaluation — reply within {pack.meta['clock_stop']['fast_track_months']} months as supplementary documents (submission procedures, Step 3)")],
          widths=[4, 13])


def deficiency_letter(out, dossier, run, pack, dept_id, findings):
    dept = _dept(pack, dept_id)
    items = letter_items(findings, dept_id)
    signed = run.get('signed') or {}
    d = new_doc(draft=not signed.get('peer'))
    L = pack.meta['letters']['deficiency']
    _head(d, L['title']['en'], L['title']['ar'], dossier, run, pack, dept)
    para(d, '')
    para(d, 'Dear Sir / Madam,')
    para(d, L['intro']['en'])
    para(d, L['intro']['ar'], ar=True)
    n = 0
    for sec in sorted({f['ctd'] for f in items}):
        para(d, '')
        para(d, sec, bold=True)
        for f in [x for x in items if x['ctd'] == sec]:
            n += 1
            p = f['payload']
            para(d, f"{n}. {p['deficiency']['en']}", bold=True)
            para(d, p['deficiency']['ar'], ar=True)
            meta = [f"{f['question_id']}", SEV[f['severity']], f"Ref: {(p.get('source') or {}).get('code', '')} {(p.get('source') or {}).get('section', '')}".strip()]
            if p.get('anchor'):
                meta.append(f"International basis: {p['anchor'].get('code', '')} {p['anchor'].get('section', '')}".strip())
            if p.get('action') and p['action'].get('type') != 'none':
                meta.append(f"Requested: {p['action']['type'].replace('_', ' ')} {p['action'].get('target', '')}".strip())
            if p.get('provisional'):
                meta.append('provisional (source not fully read)')
            para(d, ' · '.join(meta), size=9)
            if p.get('detail'):
                para(d, f"Assessor note: {p['detail'].get('en', '')}", size=9)
    para(d, '')
    para(d, f"Open queries: {sum(1 for f in items if f['status'] in ('open', 'answered', 'not_accepted'))} of {len(items)} · Reply deadline: {pack.meta['clock_stop']['fast_track_months']} months after the date of this letter.")
    para(d, L['closing']['en'])
    para(d, L['closing']['ar'], ar=True)
    para(d, '')
    para(d, f"Assessor: {signed.get('assessor', {}).get('by', '______________________')}     Second assessor: {signed.get('peer', {}).get('by', '______________________')}")
    d.save(out)
    return Path(out)


def assessment_report(out, dossier, run, pack, dept_id, findings):
    dept = _dept(pack, dept_id)
    fs = [f for f in findings if f['dept'] == dept_id]
    signed = run.get('signed') or {}
    d = new_doc(landscape=True, draft=not signed.get('peer'))
    R = pack.meta['letters']['report']
    _head(d, R['title']['en'], R['title']['ar'], dossier, run, pack, dept)
    dv = (run.get('dept_verdicts') or {}).get(dept_id) or {}
    rec = R['recommendation'].get(dv.get('verdict'), {'en': '', 'ar': ''})
    para(d, '')
    para(d, f"Recommendation: {rec['en']}", bold=True, size=12)
    para(d, f"التوصية: {rec['ar']}", ar=True, bold=True, size=12)
    c = dv.get('counts') or {}
    para(d, f"Questions assessed: {len(fs)} · open critical {c.get('critical', 0)} · major {c.get('major', 0)} · minor {c.get('minor', 0)} · not assessable {dv.get('not_assessable', 0)}")
    para(d, '')
    para(d, '1. Assessment table', bold=True)
    rows = []
    for f in sorted(fs, key=lambda x: (x['ctd'], x['question_id'])):
        p = f['payload']
        ev = '; '.join((e.get('excerpt') or f"{e.get('field', '')}: {e.get('value', '')}" or e.get('filename', ''))[:120] for e in (p.get('evidence') or [])[:3])
        rows.append((f['question_id'], f['ctd'], p['question']['en'], f['verdict'], SEV[f['severity']], ev, f['origin'] + (' (unconfirmed)' if f['origin'] == 'ai' and not f.get('confirmed_by') else ''), f['status']))
    table(d, ['ID', 'CTD', 'Question', 'Verdict', 'Severity', 'Evidence', 'Origin', 'Status'], rows, widths=[2.2, 2.2, 7, 2, 1.8, 7, 2, 2])
    para(d, '')
    para(d, '2. Deficiencies and assessor comments', bold=True)
    for f in [x for x in fs if x['verdict'] != 'adequate']:
        p = f['payload']
        para(d, f"{f['question_id']} · {f['ctd']} · {SEV[f['severity']]} · {f['verdict']}", bold=True)
        para(d, p['question']['en'])
        if f['verdict'] == 'deficient':
            para(d, p['deficiency']['en'])
            para(d, p['deficiency']['ar'], ar=True)
        if p.get('detail'):
            para(d, f"Assessor note: {p['detail'].get('en', '')}", size=9)
        if f.get('override'):
            para(d, f"Manual override by {f['override'].get('by', '')}: {f['override'].get('reason', '')}", size=9)
        src = p.get('source') or {}
        para(d, f"Source: {src.get('code', '')} {src.get('section', '')}" + (f" — «{src['quote']}»" if src.get('quote') else '') + (f" · International basis: {p['anchor'].get('code', '')}" if p.get('anchor') else ''), size=9)
    para(d, '')
    para(d, '3. Sign-off (good review practice: a second assessor reviews the findings before the letter is final)', bold=True)
    para(d, f"Assessor: {signed.get('assessor', {}).get('by', '____________')}  {signed.get('assessor', {}).get('at', '')}")
    para(d, f"Second assessor: {signed.get('peer', {}).get('by', '____________')}  {signed.get('peer', {}).get('at', '')}")
    para(d, pack.meta['letters']['deficiency']['closing']['en'], size=9)
    d.save(out)
    return Path(out)


def pdf_of(docx_path):
    p = to_pdf(docx_path) if find_soffice() else basic_pdf(docx_path)
    return Path(p)
