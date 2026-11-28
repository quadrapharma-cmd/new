"""Stage 12 — the assessor's review, and what is missing by the party that issues it, as eBOX's full program gives them.

On the dossier the hand-over made (ebox.py, `ebox/`), through the full program's own interface (`app/api.py`, in this process):
- the review (`POST …/review`): the authority's own questions and desks — EDA's for Egypt, the core questions for any other —
  each finding with its question, verdict, severity, evidence and source; then each desk's assessment report and deficiency
  letter (Word and PDF), marked as the applicant's own simulation, never the authority's;
- the missing items by issuer (`GET …/missing`): every required item still open, under who issues its document (the company, the
  authority, each drug substance's manufacturer, the other parties), and one request letter for each party (`POST …/requests`).
Everything is written to review/ and review.json; the desk's delivery carries the letters and reports."""
import re
import shutil
from pathlib import Path

from .common import Work, say

DESK_VERDICT_AR = {'approve': 'موافقة', 'comments': 'موافقة مع ملاحظات', 'clock_stop': 'استيفاء (إيقاف الساعة)', 'reject': 'رفض أو إعادة تقديم'}
VERDICT_AR = {'ready': 'جاهز', 'ready_with_risks': 'جاهز مع مخاطر (جولة استيفاء متوقعة)', 'not_ready': 'غير جاهز'}
KIND_AR = {'company': 'الشركة', 'authority': 'الجهة الرقابية', 'api': 'مصنّع المادة الفعالة', 'other': 'جهة أخرى'}


def _client(store_root):
    from fastapi.testclient import TestClient
    from ..app.api import create_app
    return TestClient(create_app(store_root, auth_enabled=False))


def _save(c, url, dst):
    r = c.get(url)
    if r.status_code != 200:
        return None
    dst.write_bytes(r.content)
    return str(dst)


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    eb = w.load('ebox.json')
    if not eb:
        raise SystemExit('لم يُسلَّم الملف لبرنامج eBOX الكامل بعد (ebox.json).')
    did = eb['dossier']
    c = _client(eb['store'])
    out_dir = w.root / 'review'
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    say('مراجعة المقيّم: أسئلة الجهة الرقابية وإداراتها')
    r = c.post(f'/api/dossiers/{did}/review', json={})
    r.raise_for_status()
    run_, findings = r.json()['run'], r.json()['findings']
    rid = run_['id']
    from ..review import pack as rpack
    names = {d['id']: d for d in rpack.load().departments_for((run_.get('options') or {}).get('authority'))}
    desks = []
    for dept, dv in (run_.get('dept_verdicts') or {}).items():
        files = {}
        for kind, path in (('report', 'reports'), ('letter', 'letters')):
            if kind == 'letter' and not any(f['dept'] == dept and f['verdict'] == 'deficient' for f in findings):
                continue
            if c.post(f'/api/dossiers/{did}/review/{rid}/{path}/{dept}').status_code != 201:
                continue
            for fmt in ('pdf', 'docx'):
                got = _save(c, f'/api/dossiers/{did}/review/{rid}/{path}/{dept}/file?fmt={fmt}', out_dir / f'{kind}-{dept}.{fmt}')
                if got:
                    files[f'{kind}_{fmt}'] = got
        desks.append({'dept': dept, 'name': (names.get(dept) or {}).get('ar') or dept, 'verdict': dv['verdict'], 'counts': dv['counts'], 'not_assessable': dv['not_assessable'],
                      'files': files})
    say('النواقص حسب الجهة المُصدِرة، وخطاب طلب واحد لكل جهة')
    m = c.get(f'/api/dossiers/{did}/missing').json()
    parties = []
    built = {x['item'] for x in (w.load('build.json', {}) or {}).get('items') or [] if x['state'] == 'built'}
    for g in m.get('parties') or []:
        mine = [i for i in g['items'] if i['slot_id'] in built]           # written by the build stage: there, to be signed
        g = {**g, 'items': [i for i in g['items'] if i['slot_id'] not in built]}
        if not g['items'] and not mine:
            continue
        ids = [i['slot_id'] for i in g['items'] if not i.get('request')]
        p = {'kind': g['kind'], 'name': g['name'] if isinstance(g['name'], str) else (g['name'] or {}).get('ar') or (g['name'] or {}).get('en'),
             'items': [{'ctd': i.get('ctd'), 'title': (i.get('title') or {}).get('ar') or (i.get('title') or {}).get('en'),
                        'en': (i.get('title') or {}).get('en'), 'generable': i.get('generable')} for i in g['items']], 'built': len(mine)}
        if ids and g['kind'] != 'company':                    # the company's own papers are written, not asked for
            sign = (w.load('dossier.json', {}) or {}).get('signatory') or {}       # who signs for the company: blank lines to sign until it is said
            q = c.post(f'/api/dossiers/{did}/requests', json={'issuer': p['name'] or KIND_AR[g['kind']], 'slot_ids': ids, 'lang': 'en',
                                                              'signatory': sign.get('name') or '____________________',
                                                              'signatory_title': sign.get('title') or '____________________'})
            if q.status_code == 201:
                got = _save(c, q.json()['letter'], out_dir / f"request-{re.sub(r'[^A-Za-z0-9._-]+', '-', g['key']).strip('-.')[:60]}.pdf")
                p['letter'] = got
            else:
                p['letter_refused'] = (q.json().get('detail') or {}).get('ar') if q.headers.get('content-type', '').startswith('application/json') else q.text[:200]
        parties.append(p)
    out = {'verdict': run_['verdict'], 'why': run_['why'], 'counts': run_['counts'], 'clock': run_.get('clock'),
           'authority': (run_.get('options') or {}).get('authority'), 'desks': desks, 'parties': parties,
           'findings': [{'question': f['question_id'], 'dept': f['dept'], 'ctd': f['ctd'], 'severity': f['severity'], 'verdict': f['verdict'],
                         'en': f['payload']['question']['en'], 'ar': f['payload']['question'].get('ar'),
                         'deficiency': (f['payload'].get('deficiency') or {}).get('ar') or (f['payload'].get('deficiency') or {}).get('en')}
                        for f in findings if f['verdict'] == 'deficient' and f['status'] == 'open']}
    w.save('review.json', out)
    cn = run_['counts']
    say(f"المراجعة: {VERDICT_AR.get(run_['verdict'], run_['verdict'])} · مفتوحة: حرجة {cn.get('critical', 0)}، رئيسية {cn.get('major', 0)}، "
        f"ثانوية {cn.get('minor', 0)} · الجهات المطلوب منها مستندات: {len(parties)}")
    return out
