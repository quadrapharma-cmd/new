"""The desk's worker helper (desk/worker.py) on the made-up dossier, as a desk session uses it (desk/WORKER.md): the stages run
one by one and recorded, Claude's decisions taken through the decide tool, the numbers and what is needed for the page, the
patch the session sends; a failed stage said plainly; Claude's decisions kept and restored into a new work folder."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
APP = HERE.parent
sys.path.insert(0, str(APP / 'engine'))
sys.path.insert(0, str(HERE))

from dossier_engine.combined import decide  # noqa: E402
from dossier_engine.combined.common import Work  # noqa: E402

import combined_fixture  # noqa: E402
from test_decide import NEED, SCRIPT  # noqa: E402
from test_decide_tool import cli, refusal  # noqa: E402

pytestmark = pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')
WORKER = APP / 'desk' / 'worker.py'
FIELDS = {'status', 'headline', 'stages', 'notes', 'log', 'summary', 'needs', 'results', 'session', 'kept', 'updated'}


def wk(*args):
    p = subprocess.run([sys.executable, str(WORKER), *map(str, args)], capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


def patch(w):
    return json.loads((Path(w) / 'desk' / 'patch.json').read_text(encoding='utf-8'))


def decisions_by_session(w):
    """Claude's five tasks through the decide tool, as tests/test_decide_tool.py sends them."""
    for task in decide.TASKS:
        assert cli(w, 'brief', task)[0] == 0
        for turn in SCRIPT[task]:
            for name, inp in turn:
                if name == 'finish':
                    code, out = cli(w, 'finish', task, inp['summary'])
                    if code and refusal(out).startswith('Not finished:'):
                        code, out = cli(w, 'finish', task, inp['summary'])
                    assert code == 0, out
                else:
                    cli(w, 'call', task, name, json.dumps(inp, ensure_ascii=False))


@pytest.fixture(scope='module')
def run(tmp_path_factory):
    root = tmp_path_factory.mktemp('desk-worker')
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    seen = {}
    code, out = wk('start', w.root, 'session_test')
    assert code == 0, out
    seen['start'] = patch(w.root)
    for s in ('read', 'repeats', 'ocr', 'split', 'assemble', 'checks'):
        code, out = wk('stage', w.root, s, *([root / 'received'] if s == 'read' else []))
        assert code == 0, out
        seen[s] = patch(w.root)
    decisions_by_session(w)
    assert wk('mark', w.root, 'decide', 'done', 'اتُّخذت القرارات الخمس.')[0] == 0
    seen['decide'] = patch(w.root)
    for s in ('fix', 'ectd', 'report'):
        code, out = wk('stage', w.root, s)
        assert code == 0, out
    code, out = wk('summary', w.root)
    assert code == 0, out
    handed = json.loads(out[out.index('{'):])
    seen['summary'] = patch(w.root)
    return root, w, seen, handed


def test_the_stages_one_by_one(run):
    root, w, seen, _ = run
    first = seen['start']
    assert set(first) <= FIELDS and first['status'] == 'running' and first['session'] == 'session_test'
    assert first['stages']['read'] == 'running' and all(first['stages'][s] == 'waiting' for s in ('repeats', 'report'))
    assert seen['read']['stages']['read'] == 'done' and seen['read']['stages']['repeats'] == 'running' and seen['read']['notes']['read']
    assert seen['checks']['stages']['decide'] == 'running'                       # the session's own stage comes next
    assert seen['decide']['stages']['fix'] == 'running' and seen['decide']['notes']['decide'] == 'اتُّخذت القرارات الخمس.'
    last = seen['summary']
    assert all(v == 'done' for v in last['stages'].values()) and len(last['log']) <= 40
    for p in seen.values():                                                      # no machine's paths in what the page shows
        assert str(w.root) not in json.dumps(p, ensure_ascii=False) and str(root) not in json.dumps(p, ensure_ascii=False)
    assert (w.root / 'desk' / 'ocr.log').read_text(encoding='utf-8').strip()      # the whole output kept for the session


def test_the_numbers_and_what_is_needed(run):
    _, _, seen, handed = run
    last = seen['summary']
    assert last['summary'] == {'pages': 47, 'documents': 21, 'left_out': 6, 'findings': 5, 'leaves': 23, 'failed_rules': 1,
                               'ectd40_failed_rules': 0, 'ectd40_left_out': 0, 'ctd_required_missing': 56, 'ctd_unplaced': 0,
                               'review_critical': 26, 'review_major': 67, 'parties_asked': 3}
    assert last['needs'] == ['رقم التتبع الذي تعطيه الهيئة: يُكتب في التسلسل حين يصل.',
                             'تأكيد المتقدم: «Example Pharma Ltd.» — يُغيَّر إن كان المتقدم الوكيل المصري',
                             'شهادة GMP — من الشركة المصنعة، لـ Module 1، البند 1.2.4',
                             '1.1.1 نموذج الطلب والتعهد (غير موجود) — من الشركة']
    assert [r['title'] for r in handed['reports']] == ['تقرير الملف (CTD)', 'تقرير تسلسل eCTD 0000']
    assert all(Path(r['file']).stat().st_size == r['bytes'] > 5000 and r['fits_page'] for r in handed['reports'])
    assert handed['zip'] and Path(handed['zip']['file']).exists() and handed['zip']['bytes'] > 10000


def test_results_status_and_needs(run, tmp_path):
    _, w, _, handed = run
    work = tmp_path / 'w'
    (work / 'desk').mkdir(parents=True)
    (work / 'desk' / 'state.json').write_text((w.root / 'desk' / 'state.json').read_text(encoding='utf-8'), encoding='utf-8')
    assert wk('result', work, 'تقرير الملف (CTD)', 'PDF', '--asset', 'a' * 32)[0] == 0
    assert wk('result', work, 'تقرير الملف (CTD)', 'PDF · نسخة ثانية', '--asset', 'b' * 32)[0] == 0   # one entry a title
    assert wk('result', work, 'مجلد التسليم', 'في Drive', '--url', 'https://drive.google.com/x')[0] == 0
    assert patch(work)['results'] == [{'title': 'تقرير الملف (CTD)', 'note': 'PDF · نسخة ثانية', 'asset': 'b' * 32},
                                      {'title': 'مجلد التسليم', 'note': 'في Drive', 'url': 'https://drive.google.com/x'}]
    for i in range(12):
        assert wk('need', work, f'بند {i}')[0] == 0
    n = patch(work)['needs']
    assert len(n) == 13 and n[0] == 'بند 0' and n[-1] == 'وبنود أخرى في تقرير الملف (العدد: 4).'
    assert wk('status', work, 'finished', 'اكتمل إعداد الملف.')[0] == 0
    p = patch(work)
    assert p['status'] == 'finished' and p['headline'] == 'اكتمل إعداد الملف.' and p['log'][-1] == 'اكتمل إعداد الملف.'
    assert wk('status', work, 'done')[0] == 1 and wk('mark', work, 'nothing', 'done')[0] == 1 and wk('result', work, 'x', 'y', '--asset')[0] == 1


def test_private_shows_the_progress_only(run, tmp_path):
    _, w, seen, _ = run
    work = tmp_path / 'w'
    (work / 'desk').mkdir(parents=True)
    (work / 'desk' / 'state.json').write_text((w.root / 'desk' / 'state.json').read_text(encoding='utf-8'), encoding='utf-8')
    assert wk('need', work, 'الوصول إلى مجلد Drive')[0] == 0
    assert wk('private', work, 'on')[0] == 0
    p = patch(work)
    assert p['stages'] == seen['summary']['stages'] and p['notes'] == {} and p['summary'] == {}
    assert p['needs'] == ['الوصول إلى مجلد Drive']                                # the session's own, not the dossier's
    names = {'— ' + n for n in ('قراءة الملفات الواردة صفحةً صفحة', 'الكتل المكررة', 'التعرف الضوئي على الصفحات الممسوحة',
                                'تقسيم الملف إلى مستندات CTD', 'بناء مجلد CTD ومطابقة كل صفحة بأصلها', 'الفحوص',
                                'التصحيحات ومعلومات المستحضر', 'تسلسل eCTD والتحقق منه', 'التقريران والتسليم')}
    assert set(p['log']) <= names | {'بدأ العمل على الملف.'} and len(p['log']) == 10
    assert not any(ch.isdigit() for line in p['log'] for ch in line)
    assert wk('private', work, 'off')[0] == 0
    p = patch(work)
    assert p['summary'] == seen['summary']['summary'] and p['notes'] == seen['summary']['notes']
    assert wk('start', tmp_path / 'x', 's', '--private')[0] == 0 and patch(tmp_path / 'x')['log'] == ['بدأ العمل على الملف.']
    assert wk('start', tmp_path / 'y', 's', '--open')[0] == 1 and wk('private', work, 'maybe')[0] == 1


def test_a_stop_leaves_no_stage_running(tmp_path):
    w = tmp_path / 'w'
    assert wk('start', w, 'session_x')[0] == 0
    assert wk('status', w, 'stopped', 'توقّف بطلبك.')[0] == 0
    p = patch(w)
    assert p['status'] == 'stopped' and 'running' not in p['stages'].values()
    assert wk('start', w, 'session_y')[0] == 0                                    # resumed in another session
    p = patch(w)
    assert p['session'] == 'session_y' and p['headline'] == 'استُؤنف إعداد الملف.'


def test_a_failed_stage_said_plainly(tmp_path):
    w = tmp_path / 'w'
    assert wk('start', w, 'session_x')[0] == 0
    code, out = wk('stage', w, 'read', tmp_path / 'nothing-here')                 # a download that brought nothing
    p = patch(w)
    assert code == 2 and 'FAILED: no file in' in out
    assert p['status'] == 'failed' and p['stages']['read'] == 'failed' and p['headline'] == 'تعذّرت مرحلة «قراءة الملفات الواردة صفحةً صفحة».'
    assert p['notes']['read'] == 'لا ملفات في المجلد الوارد، فلم يُقرأ شيء.'
    odd = tmp_path / 'odd'
    odd.mkdir()
    (odd / 'readme.txt').write_text('no pages here', encoding='utf-8')
    code, out = wk('stage', w, 'read', odd)                                       # files, but not one page
    assert code == 2 and patch(w)['notes']['read'] == 'لم تُقرأ أي صفحة من الملفات الواردة.'
    v = tmp_path / 'v'
    assert wk('start', v, 'session_x')[0] == 0
    code, out = wk('stage', v, 'repeats')                                         # the program itself stops
    p = patch(v)
    assert code == 2 and 'FAILED: exit' in out and (v / 'desk' / 'repeats.log').exists()
    assert p['stages']['repeats'] == 'failed' and p['notes']['repeats'] == 'تعذّرت هذه المرحلة؛ يشرح Claude السبب في المحادثة.'
    assert 'Traceback' not in json.dumps(p) and 'Error' not in json.dumps(p)
    assert wk('stage', w, 'decide')[0] == 1                                      # the session takes it, with the decide tool
    assert wk('stage', w, 'read')[0] == 1                                        # read needs its source


def test_the_decisions_kept_and_restored(run, tmp_path):
    _, w, _, _ = run
    code, out = wk('keep', w.root)
    kept = Path(out.split('decisions: ')[1].strip())
    assert code == 0 and kept.exists()
    assert wk('kept', w.root, 'c' * 32)[0] == 0 and patch(w.root)['kept']['asset'] == 'c' * 32
    new = tmp_path / 'again'
    new.mkdir()
    assert wk('restore', new, kept)[0] == 0
    for name in ('dossier.json', 'decide.json', 'decisions/pi-content.json'):
        assert json.loads((new / name).read_text(encoding='utf-8')) == json.loads((w.root / name).read_text(encoding='utf-8'))
    bad = tmp_path / 'bad.json'
    bad.write_text('{"kind": "other"}', encoding='utf-8')
    assert wk('restore', new, bad)[0] == 2
