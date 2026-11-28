"""The «decide» stage: Claude makes, through the Claude API, the decisions a person would make by hand — task by
task, the program's stages run again after each task whose decisions change them. A dossier whose decisions file was made by a
person is left as it is (unless told again). Without a key the program goes on with its rules alone, and says so."""
import datetime
import json
import os
import time

from ..common import Work, say
from .brain import MODEL, Budget, Stop, converse
from .case import READ_TOOLS, Case, read_handlers
from .store import Store
from .tasks import FINISH, PREAMBLE, TASK_TEXT, TOOLS, first_message, handlers

TASKS = ('documents', 'product', 'pi', 'review', 'sequence')
NAMES_AR = {'documents': 'المستندات وأماكنها', 'product': 'بيانات المستحضر و Module 1 المصرية', 'pi': 'معلومات المستحضر وترجمتها',
            'review': 'ملاحظات المراجع', 'sequence': 'أوراق تسلسل eCTD'}
DEFAULT_BUDGET_USD = 25.0


def client_from_env():
    if not os.environ.get('ANTHROPIC_API_KEY'):
        return None
    import anthropic
    return anthropic.Anthropic(max_retries=4)


def made_by_person(w):
    d = w.decisions()
    return bool(d.get('plan') or (d.get('ectd') or {}).get('envelope')) and not (w.root / 'decide.json').exists()


def after(task, w):
    """The stages a task's decisions change, made again."""
    from .. import assemble, checks, ectd, fix, split
    if task == 'documents':
        split.run(w)
        assemble.run(w)
        checks.run(w)
    elif task == 'review':
        checks.run(w)
    elif task == 'before-sequence':
        fix.run(w)
        ectd.run(w)
    elif task == 'sequence':
        ectd.run(w)


def run(work, client=None, budget_usd=None, again=False, only=None):
    w = work if isinstance(work, Work) else Work(work)
    if made_by_person(w) and not again:
        say('ملف القرارات أعدّه شخص: لا يغيّره Claude (اطلب ذلك صراحةً بالخيار --again).')
        return {'skipped': 'decisions made by a person'}
    rec = w.load('decide.json', {}) or {}
    tasks = rec.setdefault('tasks', {})
    if client is None:
        client = client_from_env()
    if client is None:
        say('لا مفتاح لـ Claude (ANTHROPIC_API_KEY): لم يتخذ Claude القرارات، ويمضي البرنامج بقواعده وحدها.')
        rec['skipped'] = 'no key'
        w.save('decide.json', rec)
        return rec
    rec.pop('skipped', None)
    budget = Budget(budget_usd or float(os.environ.get('EBOX_CLAUDE_BUDGET_USD', DEFAULT_BUDGET_USD)))
    logp = w.root / 'decide' / 'log.jsonl'
    logp.parent.mkdir(parents=True, exist_ok=True)

    def log(e):
        with open(logp, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'time': time.strftime('%Y-%m-%d %H:%M:%S'), **e}, ensure_ascii=False) + '\n')

    rec.update({'model': MODEL, 'started': datetime.datetime.now().isoformat(timespec='seconds')})
    before = float(rec.get('spent_usd_total', 0))
    stopped = None
    for t in (only or TASKS):
        if tasks.get(t, {}).get('finished') and not again:
            say(f'Claude: «{NAMES_AR[t]}» منجزة من قبل.')
            continue
        if t == 'sequence':
            after('before-sequence', w)
        case = Case(w)
        store = Store(w, case)
        say(f'Claude: {NAMES_AR[t]}')
        t0 = time.time()
        try:
            res = converse(client, t, PREAMBLE + TASK_TEXT[t], READ_TOOLS + TOOLS[t] + [FINISH], first_message(t, w, case),
                           {**read_handlers(case), **handlers(t, store), 'finish': lambda a: 'Done.'}, budget, log,
                           max_tokens=64000 if t == 'pi' else 32000)
            tasks[t] = {'finished': True, 'summary': res['summary'], 'turns': res['turns'], 'minutes': round((time.time() - t0) / 60, 1)}
        except Stop as e:
            tasks[t] = {'finished': False, 'stopped': e.why, 'detail': str(e)}
            stopped = e
        rec['budget'] = budget.record()
        rec['spent_usd_total'] = round(before + budget.spent, 4)
        w.save('decide.json', rec)
        say(f'Claude: {NAMES_AR[t]} — ' + ('تمّت' if tasks[t]['finished'] else f'توقفت ({tasks[t]["stopped"]})') +
            f' · التكلفة حتى الآن {budget.spent:.2f} دولار')
        if stopped:
            break
        after(t, w)
    rec['finished'] = all(tasks.get(t, {}).get('finished') for t in TASKS)
    w.save('decide.json', rec)
    return rec
