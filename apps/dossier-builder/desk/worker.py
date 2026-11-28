#!/usr/bin/env python3
"""The eBOX desk's worker helper: one dossier's progress kept beside its work folder, and the patch a desk session sends to
the dossier's document in the desk page (apps/dossier-builder/desk/WORKER.md says when).

  python3 desk/worker.py start   <work> <session id> [--private]   the session took the dossier (--private: see below)
  python3 desk/worker.py stage   <work> <stage> [<source folder>]  one stage of the program run and recorded (read: the source)
  python3 desk/worker.py mark    <work> <stage> <state> [<note>]   a stage's state set by the session (the decide stage, a stop)
  python3 desk/worker.py status  <work> <status> [<headline>]
  python3 desk/worker.py need    <work> <text>                     what the owner must give or decide
  python3 desk/worker.py result  <work> <title> <note> [--asset <id> | --url <link>]
  python3 desk/worker.py summary <work>                            the numbers, what is needed, and the files to hand over
  python3 desk/worker.py keep    <work>                            Claude's decisions in one JSON file, to keep
  python3 desk/worker.py kept    <work> <asset id>                 where that file was kept
  python3 desk/worker.py restore <work> <decisions file>           Claude's decisions back into a new work folder
  python3 desk/worker.py country <work> <code>                     the country the dossier is for (EG, SA, DE …; Egypt's outputs always)
  python3 desk/worker.py private <work> on|off                      the page shows the work's progress only, or everything

Each command rewrites <work>/desk/patch.json: the progress fields of dossiers/<id> (status, headline, stages, notes, log,
summary, needs, results, session, kept, updated), whole; the session sends it with ArtifactData (action update, file_path,
if_version). The texts it writes are the program's, in formal Arabic. Nothing here reaches the network or the page.
Private (until the owner says yes to a real dossier's numbers and reports in the page): the patch carries the stages and
their states, the worker's own lines and the session's own needs, without the program's notes, log lines and numbers."""
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'engine'
STAGES = ('read', 'repeats', 'ocr', 'split', 'assemble', 'checks', 'decide', 'fix', 'build', 'ectd', 'report')
NAMES = {'read': 'قراءة الملفات الواردة صفحةً صفحة', 'repeats': 'الكتل المكررة', 'ocr': 'التعرف الضوئي على الصفحات الممسوحة',
         'split': 'تقسيم الملف إلى مستندات CTD', 'assemble': 'بناء مجلد CTD ومطابقة كل صفحة بأصلها', 'checks': 'الفحوص',
         'decide': 'قرارات Claude', 'fix': 'التصحيحات ومعلومات المستحضر', 'build': 'بناء المستندات الناقصة', 'ectd': 'تسلسل eCTD والتحقق منه',
         'report': 'التقريران والتسليم'}                                     # as the page names them (desk/index.html)
STATUSES = ('requested', 'queued', 'running', 'needs', 'finished', 'stopped', 'failed')
STATES = ('done', 'running', 'waiting', 'failed', 'skipped', 'needs')
FIELDS = ('status', 'headline', 'stages', 'notes', 'log', 'summary', 'needs', 'results', 'session', 'kept', 'updated')
LOG_MOST = 40                                                               # the page keeps the last 40 lines
NEEDS_MOST = 12
TIME = re.compile(r'^\d\d:\d\d:\d\d ')
RULE_NEEDS = {'EG-PF-E06': 'رقم التتبع الذي تعطيه الهيئة: يُكتب في التسلسل حين يصل.'}
ASSET_MOST = 20 * 1048576                                                   # the page's asset store takes files up to 20 MiB


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def where(work):
    d = Path(work).resolve() / 'desk'
    d.mkdir(parents=True, exist_ok=True)
    return d


def load(work):
    p = where(work) / 'state.json'
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return {'status': 'running', 'headline': '', 'stages': {s: 'waiting' for s in STAGES}, 'notes': {}, 'log': [], 'summary': {},
            'needs': [], 'needs_own': [], 'needs_found': [], 'results': []}


def write(p, obj):
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')
    os.replace(tmp, p)


def save(work, st):
    st['updated'] = now()
    st['log'] = st['log'][-LOG_MOST:]
    every = list(dict.fromkeys(st.get('needs_own', []) + st.get('needs_found', [])))
    st['needs'] = every[:NEEDS_MOST] + ([f'وبنود أخرى في تقرير الملف (العدد: {len(every) - NEEDS_MOST}).'] if len(every) > NEEDS_MOST else [])
    st['log_plain'] = st.setdefault('log_plain', [])[-LOG_MOST:]
    out = {k: st[k] for k in FIELDS if k in st}
    if st.get('private'):
        own = list(dict.fromkeys(st.get('needs_own', [])))
        out.update({'notes': {}, 'summary': {}, 'log': st['log_plain'], 'needs': own[:NEEDS_MOST]})
    d = where(work)
    write(d / 'state.json', st)
    write(d / 'patch.json', out)
    print(f'patch: {d / "patch.json"}' + (' (private)' if st.get('private') else ''))


def plain(st, line):
    """A line of the worker's own (no dossier data): shown even while private."""
    st['log'].append(line)
    st.setdefault('log_plain', []).append(line)


def advance(st, stage):
    """The stage after this one shown as running, when it has not started."""
    i = STAGES.index(stage)
    if i + 1 < len(STAGES) and st['stages'].get(STAGES[i + 1], 'waiting') == 'waiting':
        st['stages'][STAGES[i + 1]] = 'running'


def start(work, session, private=None):
    if private not in (None, '--private'):
        print(__doc__)
        return 1
    st = load(work)
    st['private'] = private == '--private'
    again = 'started' in st
    st.update({'status': 'running', 'session': session, 'headline': 'استُؤنف إعداد الملف.' if again else 'بدأ إعداد الملف.'})
    st.setdefault('started', now())
    nxt = next((s for s in STAGES if st['stages'].get(s) != 'done'), None)          # where the work goes on
    if nxt and 'running' not in st['stages'].values():
        st['stages'][nxt] = 'running'
    plain(st, 'استُؤنف العمل في جلسة جديدة.' if again else 'بدأ العمل على الملف.')
    save(work, st)
    return 0


def stage(work, name, source=None):
    if name == 'decide':
        print('The decide stage is taken by the session with the decide tool (WORKER.md, step 5), not run here.')
        return 1
    if name == 'read' and not source:
        print('read needs the folder of the received files: stage <work> read <source folder>')
        return 1
    w = Path(work).resolve()
    st = load(w)
    plain(st, f'— {NAMES[name]}')
    if name == 'read' and not any(f.is_file() for f in Path(source).rglob('*')):
        return failed(w, st, name, 'لا ملفات في المجلد الوارد، فلم يُقرأ شيء.', [], f'no file in {source}')
    args = [sys.executable, '-m', 'dossier_engine.combined', name] + ([str(Path(source).resolve())] if name == 'read' else []) + [str(w)]
    p = subprocess.run(args, cwd=str(ENGINE), capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(ENGINE)})
    (where(w) / f'{name}.log').write_text(p.stdout + ('\n--- stderr ---\n' + p.stderr if p.stderr.strip() else ''), encoding='utf-8')
    said = [TIME.sub('', l).replace(str(w), '…') for l in p.stdout.splitlines() if l.strip()]
    said = [l for l in said if not l.startswith('— المرحلة')]
    if p.returncode:
        return failed(w, st, name, 'تعذّرت هذه المرحلة؛ يشرح Claude السبب في المحادثة.', said[-10:],
                      f'exit {p.returncode}; the whole output: {where(w) / (name + ".log")}\n' + '\n'.join(p.stderr.strip().splitlines()[-25:]))
    if name == 'read' and not json.loads((w / 'read' / 'pages.json').read_text(encoding='utf-8')):
        return failed(w, st, name, 'لم تُقرأ أي صفحة من الملفات الواردة.', said[-10:], 'the read stage found no page')
    st['stages'][name] = 'done'
    st['notes'][name] = said[-1] if said else ''
    st['log'].extend(said)
    advance(st, name)
    save(w, st)
    print(f'done: {st["notes"][name]}')
    return 0


def failed(w, st, name, note, said, detail):
    """A stage that did not do its work: said plainly on the page, the reason for the session."""
    st['stages'][name] = 'failed'
    st['notes'][name] = note
    st['status'] = 'failed'
    st['headline'] = f'تعذّرت مرحلة «{NAMES[name]}».'
    st['log'].extend(said)
    plain(st, f'تعذّرت مرحلة «{NAMES[name]}»: {note}')
    save(w, st)
    print(f'FAILED: {detail}')
    return 2


def mark(work, name, state, note=None):
    if name not in STAGES or state not in STATES:
        print(f'A stage: {", ".join(STAGES)}; a state: {", ".join(STATES)}')
        return 1
    st = load(work)
    st['stages'][name] = state
    if note is not None:
        st['notes'][name] = note
        st['log'].append(note)
    if state == 'done':
        advance(st, name)
    save(work, st)
    return 0


def status(work, value, headline=None):
    if value not in STATUSES:
        print('A status: ' + ', '.join(STATUSES))
        return 1
    st = load(work)
    st['status'] = value
    if value in ('stopped', 'failed'):
        st['stages'] = {k: ('waiting' if v == 'running' else v) for k, v in st['stages'].items()}
    if value == 'finished':
        st['finished'] = now()
    if headline is not None:
        st['headline'] = headline
        plain(st, headline)
    save(work, st)
    return 0


def need(work, text):
    st = load(work)
    st.setdefault('needs_own', [])
    if text not in st['needs_own']:
        st['needs_own'].append(text)
    save(work, st)
    return 0


def result(work, title, note, kind=None, value=None):
    st = load(work)
    r = {'title': title, 'note': note}
    if kind == '--asset':
        r['asset'] = value
    elif kind == '--url':
        r['url'] = value
    st['results'] = [x for x in st['results'] if x.get('title') != title] + [r]
    save(work, st)
    return 0


def cells(row, n):
    row = list(row) if isinstance(row, (list, tuple)) else [row]
    return [str(x) for x in (row + [''] * n)[:n]]


def summary(work):
    sys.path.insert(0, str(ENGINE))
    from dossier_engine.combined.common import Work
    w = Work(work)
    plan, e = w.load('plan.json', {}) or {}, w.load('ectd.json', {}) or {}
    val, fnd = w.load('validation.json', []) or [], w.load('findings.json', []) or []
    rec, rep = w.load('decide.json', {}) or {}, w.decisions().get('report') or {}
    s = {'pages': len(w.pages_text('read/ocr.txt')) or len(w.pages_text()), 'documents': len(plan.get('docs', [])),
         'left_out': len(plan.get('removed', [])), 'findings': len(fnd), 'leaves': len(e.get('leaves', [])) + len(e.get('m1', [])),
         'failed_rules': sum(1 for r in val if not r['ok'] and r.get('kind') == 'P/F')}
    if rec.get('model') not in (None, 'session') and rec.get('spent_usd_total') is not None:
        s['spent_usd'] = round(float(rec['spent_usd_total']), 2)             # Claude through the API; a session's decisions cost none
    found = [RULE_NEEDS.get(r['rule'], f'قاعدة راسبة في التحقق: {r["rule"]} (تفاصيلها في تقرير التسلسل).')
             for r in val if not r['ok'] and r.get('kind') == 'P/F']
    for item, value, why in (cells(x, 3) for x in rep.get('to_confirm', [])):            # [item, the value recorded, why]
        found.append(f'تأكيد {item}: «{value}» — {why}')
    for item, place, who in (cells(x, 3) for x in rep.get('company_gaps', [])):          # [what, where it is needed, who]
        found.append(f'{item} — من {who}، لـ {place}')
    bd = w.load('build.json', {}) or {}                                                 # the build stage: what was written, what is left
    done_ctd = {x['ctd'] for x in bd.get('items') or [] if x['state'] == 'built' and x.get('ctd')}
    for item, state, who in (cells(x, 3) for x in rep.get('eg_m1_needs', [])):           # [Module 1 item, its state, who]
        if str(item).split(' ', 1)[0] not in done_ctd:                                   # written since by the build stage: not needed
            found.append(f'{item} ({state}) — من {who}')
    for x in bd.get('items') or []:
        name = (x.get('title') or {}).get('ar') or (x.get('title') or {}).get('en') or x['req']
        if x['state'] == 'built' and x.get('sign'):
            found.append(f'توقيع الشركة وختمها على «{name}» ({x["req"]}): كتبه البرنامج جاهزًا للتوقيع.')
        if x['state'] == 'built' and x.get('gaps'):
            what = '؛ '.join(str((g.get('ar') or g.get('what')) if isinstance(g, dict) else g) for g in x['gaps'][:4])
            found.append(f'بيانات ناقصة في «{name}» ({x["req"]}) التي كتبها البرنامج: {what}')
        if x['state'] == 'cannot' and x.get('by') == 'claude':
            found.append(f'«{name}» ({x["req"]}) — من الشركة: {x.get("note")}')
        if x['state'] == 'later' and x.get('by') == 'claude':
            found.append(f'«{name}» ({x["req"]}) لم يُكتب في هذا التشغيل: {x.get("note")}')
    reports = sum(1 for x in bd.get('items') or [] if x['state'] == 'cannot' and x.get('by') == 'program')
    if reports:
        found.append(f'تقارير دراسات وسجلات تشغيلات مطلوبة يقدّمها أصحابها: {reports} (تفاصيلها في تقرير التسلسل).')
    todo = sum(1 for x in bd.get('items') or [] if x['state'] == 'to do')
    if todo:
        found.append(f'مستندات ناقصة تُصدرها الشركة لم تُكتب بعد: {todo} (مرحلة «بناء المستندات الناقصة»).')
    st = load(work)
    st['summary'] = s
    st['needs_found'] = found
    rj = w.load('report.json', {}) or {}
    seq = Path(e['sequence']).name if e.get('sequence') else '0000'
    files = []
    if rj.get('ctd'):
        files.append({'title': 'تقرير الملف (CTD)', 'note': 'PDF · ما فُعل في كل مستند، والملاحظات، وما يحتاج إلى تأكيد',
                      'file': rj['ctd']['pdf']})
    if rj.get('ectd'):
        files.append({'title': f'تقرير تسلسل eCTD {seq}', 'note': 'PDF · محتوى التسلسل، والتصحيحات، ونتيجة التحقق قاعدةً قاعدة',
                      'file': rj['ectd']['pdf']})
    for f in files:
        f['bytes'] = Path(f['file']).stat().st_size
        f['fits_page'] = f['bytes'] <= ASSET_MOST
    dl = rj.get('deliver') or {}
    z = dl.get('zip')
    e4, cz = w.load('ectd40.json', {}) or {}, w.load('ctdzip.json', {}) or {}
    if e4:
        s['ectd40_failed_rules'] = e4['validation']['fail']
        s['ectd40_left_out'] = len(e4.get('left_out') or [])
    if w.load('outputs-failed.json') is not None:          # always written, empty too: a fault of an earlier run never stays on the desk
        s['outputs_failed'] = sorted(w.load('outputs-failed.json') or {})
    rv = w.load('review.json', {}) or {}
    if rv:
        s['review_critical'] = rv['counts'].get('critical', 0)
        s['review_major'] = rv['counts'].get('major', 0)
        s['parties_asked'] = sum(1 for p in rv.get('parties') or [] if p.get('letter'))
    if bd:
        s['built'] = sum(1 for x in bd.get('items') or [] if x['state'] == 'built')
        s['built_to_sign'] = sum(1 for x in bd.get('items') or [] if x['state'] == 'built' and x.get('sign'))
        s['left_to_company'] = sum(1 for x in bd.get('items') or [] if x['state'] == 'cannot')
    g = e.get('global') or {}
    if g.get('layers'):
        s['global_failed_rules'] = sum(v.get('fail', 0) for v in g['layers'].values())
    if cz:
        s['ctd_required_missing'] = len(cz.get('required_missing', []))
        s['ctd_unplaced'] = len(cz.get('unplaced', []))
    st['summary'] = s
    save(work, st)
    outs = {k: {'file': dl[k], 'bytes': Path(dl[k]).stat().st_size} for k in ('zip', 'ectd40_zip', 'ctd_zip') if dl.get(k) and Path(dl[k]).exists()}
    for f in sorted(Path(dl['country_outputs']).iterdir()) if dl.get('country_outputs') else []:     # another country's (eBOX's full program)
        outs[f'country:{f.name}'] = {'file': str(f), 'bytes': f.stat().st_size}
    for x in bd.get('items') or [] if bd else []:                                       # what the build stage wrote: PDF and Word
        for k in ('pdf', 'docx'):
            if x['state'] == 'built' and x.get(k) and Path(x[k]).exists():
                outs[f'built:{Path(x[k]).name}'] = {'file': x[k], 'bytes': Path(x[k]).stat().st_size}
    for f in sorted(Path(dl['review']).iterdir()) if dl.get('review') else []:          # the assessor's reports and letters, the requests
        if f.suffix == '.pdf':
            outs[f'review:{f.name}'] = {'file': str(f), 'bytes': f.stat().st_size}
    print(json.dumps({'summary': s, 'needs': st['needs'], 'reports': files, 'zip': outs.get('zip'), 'outputs': outs},
                     ensure_ascii=False, indent=1))
    return 0


def keep(work):
    w = Path(work).resolve()
    rd = lambda n: json.loads((w / n).read_text(encoding='utf-8')) if (w / n).exists() else None   # noqa: E731
    out = where(w) / 'decisions.json'
    write(out, {'kind': 'ebox-decisions', 'version': 1, 'kept': now(), 'dossier': rd('dossier.json'), 'decide': rd('decide.json'),
                'pi_content': rd('decisions/pi-content.json')})
    print(f'decisions: {out}')
    return 0


def kept(work, asset):
    st = load(work)
    st['kept'] = {'asset': asset, 'at': now()}
    save(work, st)
    return 0


def restore(work, file):
    d = json.loads(Path(file).read_text(encoding='utf-8'))
    if d.get('kind') != 'ebox-decisions':
        print('This is not a decisions file kept by the desk (keep).')
        return 2
    w = Path(work).resolve()
    for name, key in (('dossier.json', 'dossier'), ('decide.json', 'decide'), ('decisions/pi-content.json', 'pi_content')):
        if d.get(key) is not None:
            (w / name).parent.mkdir(parents=True, exist_ok=True)
            write(w / name, d[key])
    print(f'restored into {w}: the decisions of {d.get("kept")}')
    return 0


def private(work, value):
    if value not in ('on', 'off'):
        print(__doc__)
        return 1
    st = load(work)
    st['private'] = value == 'on'
    save(work, st)
    return 0


def country(work, code):
    """The country the page asked for (dossiers/<id>.country): kept as country.json, read by the ectd stage's hand-over to eBOX's
    full program. Egypt's three outputs are made whatever it is."""
    code = (code or 'EG').strip().upper()
    if not re.fullmatch(r'[A-Z]{2}', code):
        print('A country is two letters, such as EG, SA or DE.')
        return 1
    w = Path(work).resolve()
    w.mkdir(parents=True, exist_ok=True)
    (w / 'country.json').write_text(json.dumps({'code': code}), encoding='utf-8')
    print(f'country {code}')
    return 0


def main(argv):
    cmds = {'private': (private, 2, 2), 'start': (start, 2, 3), 'stage': (stage, 2, 3), 'mark': (mark, 3, 4), 'status': (status, 2, 3), 'need': (need, 2, 2),
            'result': (result, 3, 5), 'summary': (summary, 1, 1), 'keep': (keep, 1, 1), 'kept': (kept, 2, 2), 'restore': (restore, 2, 2),
            'country': (country, 2, 2)}
    if not argv or argv[0] not in cmds:
        print(__doc__)
        return 1
    fn, least, most = cmds[argv[0]]
    args = argv[1:]
    if not least <= len(args) <= most or (argv[0] == 'result' and len(args) == 4):
        print(__doc__)
        return 1
    return fn(*args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
