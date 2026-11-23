"""Claude in a cloud session takes the «decide» stage's decisions itself, through the same tools and the same checks as Claude
through the API (decide/run.py), one tool call a command. For the desk's sessions (apps/dossier-builder/desk/WORKER.md): there
the session is Claude, and no API key is needed.

  python -m dossier_engine.combined.decide.tool <work> status
  python -m dossier_engine.combined.decide.tool <work> brief <task>      the task's instructions and its case file
  python -m dossier_engine.combined.decide.tool <work> tools <task>      the task's tools, with the JSON schema of each input
  python -m dossier_engine.combined.decide.tool <work> call <task> <tool> '<json input>'
                                                                         one call: its result, or «REFUSED: why» and exit 2
                                                                         (a long input: @<file> or - for stdin; an argument
                                                                         is cut at 128 KB by the system)
  python -m dossier_engine.combined.decide.tool <work> finish <task> '<summary>'
                                                                         the task done; the stages it changes are made again

The tasks, in their order: documents, product, pi, review, sequence (a task waits for the ones before it). Before the sequence
task the corrections and the sequence are made, as the program does before Claude's last task. view_page saves the page's
picture as <work>/decide/view-<page>.png and prints its path: look at it. Every call goes to <work>/decide/log.jsonl.
A refused decision is corrected, or dropped on purpose: finish is refused once while a refused decision since the last finish
has no later accepted call of the same tool, and accepted when asked again. A dossier whose decisions a person made is left as
it is unless --again is given."""
import base64
import datetime
import json
import sys
import time
from pathlib import Path

from ..common import Work
from .brain import ToolError, brief, misfit
from .case import READ_TOOLS, Case, read_handlers
from .run import NAMES_AR, TASKS, after, made_by_person
from .store import Store
from .tasks import PREAMBLE, TASK_TEXT, TOOLS, first_message, handlers

COMMANDS = ('status', 'brief', 'tools', 'call', 'finish')


def record(w):
    rec = w.load('decide.json', {}) or {}
    rec.setdefault('tasks', {})
    return rec


def log_path(w):
    return w.root / 'decide' / 'log.jsonl'


def log(w, entry):
    p = log_path(w)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'by': 'session', **entry}, ensure_ascii=False) + '\n')


def waiting_for(rec, task):
    """The first task before this one that is not finished, or None."""
    return next((t for t in TASKS[:TASKS.index(task)] if not rec['tasks'].get(t, {}).get('finished')), None)


def prepare(w, task):
    """Before the sequence task: the corrections and the sequence, made once (decide/run.py does the same before Claude's
    last task); made again if an earlier task is finished again."""
    rec = record(w)
    if task == 'sequence' and not rec['tasks'].get('sequence', {}).get('prepared'):
        after('before-sequence', w)
        rec = record(w)
        rec['tasks'].setdefault('sequence', {})['prepared'] = True
        w.save('decide.json', rec)


def show(w, out, page=None):
    """A tool's result as text; a page's picture saved beside the work, and its path given."""
    if not isinstance(out, list):
        return str(out)
    lines = []
    for b in out:
        if b.get('type') == 'image':
            d = w.root / 'decide'
            d.mkdir(parents=True, exist_ok=True)
            p = d / (f'view-{page}.png' if page else f'view-{len(list(d.glob("view-*.png"))) + 1}.png')
            p.write_bytes(base64.standard_b64decode(b['source']['data']))
            lines.append(f'(the page\'s picture, to look at: {p})')
        elif b.get('type') == 'text':
            lines.append(b['text'])
    return '\n'.join(lines)


def call(w, task, tool, inp):
    """One tool call, checked as Claude's calls through the API are: (ok, text)."""
    if tool == 'finish':
        return False, 'finish is its own command: finish <task> \'<summary>\''
    tools = {t['name']: t.get('input_schema') for t in READ_TOOLS + TOOLS[task]}
    if tool not in tools:
        return False, f'No tool «{tool}» in the task «{task}»: ' + ', '.join(tools)
    if not isinstance(inp, dict):
        return False, 'The input is a JSON object: {"name": value, ...}'
    why = misfit(tools[tool], inp)
    if why:
        log(w, {'task': task, 'tool': tool, 'input': brief(inp), 'ok': False, 'error': why})
        return False, f'This input does not fit the tool: {why}. Send it again, whole.'
    case = Case(w)
    run = {**read_handlers(case), **handlers(task, Store(w, case))}[tool]
    try:
        out = run(inp)
    except ToolError as e:
        log(w, {'task': task, 'tool': tool, 'input': brief(inp), 'ok': False, 'error': brief(str(e), 600)})
        return False, str(e)
    except (KeyError, IndexError, TypeError, ValueError) as e:      # an input the schema allows but the program cannot use
        why = f'{type(e).__name__}: {e}'
        log(w, {'task': task, 'tool': tool, 'input': brief(inp), 'ok': False, 'error': 'not usable: ' + brief(why, 600)})
        return False, f'This input could not be used ({brief(why, 300)}). Check it and send it again.'
    text = show(w, out, inp.get('page') if tool == 'view_page' else None)
    log(w, {'task': task, 'tool': tool, 'input': brief(inp), 'ok': True, 'result': brief(text, 200)})
    return True, text


def uncorrected(w, task):
    """The refused calls of this task since its last finish (asked or done) with no later accepted call of the same tool."""
    p = log_path(w)
    entries = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()] if p.exists() else []
    entries = [e for e in entries if e.get('task') == task and e.get('by') == 'session' and e.get('tool')]
    last = max((i for i, e in enumerate(entries) if e['tool'] == 'finish'), default=-1)
    open_ = []
    for e in entries[last + 1:]:
        if e['ok']:
            open_ = [x for x in open_ if x != e['tool']]
        else:
            open_.append(e['tool'])
    return open_


def finish(w, task, summary):
    """(ok, text): the task recorded as done and the stages it changes made again; refused while a decision is left refused."""
    if not summary.strip():
        return False, 'A short summary of what you decided is needed.'
    left = uncorrected(w, task)
    if left:
        log(w, {'task': task, 'tool': 'finish', 'ok': False, 'error': f'{len(left)} refused, not corrected'})
        return False, (f'Not finished: {len(left)} refused decision(s) since the last finish were not made again ({", ".join(left)}). '
                       'Correct them; or, if you leave them out on purpose, call finish again.')
    rec = record(w)
    rec.pop('skipped', None)
    rec['model'] = 'session'
    rec['tasks'][task] = {**rec['tasks'].get(task, {}), 'finished': True, 'summary': summary, 'by': 'session',
                          'at': datetime.datetime.now().isoformat(timespec='seconds')}
    if task != 'sequence':
        rec['tasks'].get('sequence', {}).pop('prepared', None)
    rec['finished'] = all(rec['tasks'].get(t, {}).get('finished') for t in TASKS)
    w.save('decide.json', rec)
    log(w, {'task': task, 'tool': 'finish', 'ok': True, 'result': brief(summary, 200)})
    after(task, w)
    return True, f'«{NAMES_AR[task]}»: done.' + (
        ' The five tasks are done: the program goes on with the corrections, the eCTD and the reports '
        '(python -m dossier_engine.combined run <source> <work>).' if rec['finished'] else '')


def main(argv):
    again = '--again' in argv
    argv = [a for a in argv if a != '--again']
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    w, cmd = Work(Path(argv[0])), argv[1]
    rec = record(w)
    if cmd == 'status':
        for t in TASKS:
            x = rec['tasks'].get(t, {})
            print(f"{t:10} {'done' if x.get('finished') else 'to do'}  {NAMES_AR[t]}" + (f" — {x['summary']}" if x.get('summary') else ''))
        return 0
    if len(argv) < 3 or argv[2] not in TASKS:
        print('A task: ' + ', '.join(TASKS))
        return 1
    task = argv[2]
    if cmd == 'tools':
        print(json.dumps([{'name': t['name'], 'description': t['description'], 'input': t.get('input_schema')}
                          for t in READ_TOOLS + TOOLS[task]], ensure_ascii=False, indent=1))
        return 0
    if made_by_person(w) and not again:
        print('REFUSED: a person made this dossier\'s decisions (dossier.json): they are left as they are. '
              'Only when told to change them: add --again.')
        return 2
    first = waiting_for(rec, task)
    if first:
        print(f'REFUSED: finish the task «{first}» first (the tasks go in this order: {", ".join(TASKS)}).')
        return 2
    if not (w.root / 'decide.json').exists():
        w.save('decide.json', rec)                  # the program's own start: from here on, not a person's decisions
    prepare(w, task)
    if cmd == 'brief':
        print(PREAMBLE + TASK_TEXT[task])
        print('\n===== the case file =====\n')
        print(first_message(task, w, Case(w)))
        return 0
    if cmd == 'call':
        if len(argv) < 4:
            print('call <task> <tool> \'<json input>\'')
            return 1
        raw = argv[4] if len(argv) > 4 else '{}'
        try:
            if raw == '-':                          # a long input (a whole leaflet) from stdin, or from a file: @<path>
                raw = sys.stdin.read()
            elif raw.startswith('@'):
                raw = Path(raw[1:]).read_text(encoding='utf-8')
            inp = json.loads(raw)
        except OSError as e:
            print(f'REFUSED: the input file could not be read ({e}).')
            return 2
        except json.JSONDecodeError as e:
            print(f'REFUSED: the input is not JSON ({e}). Send it again, whole.')
            return 2
        ok, text = call(w, task, argv[3], inp)
    else:
        ok, text = finish(w, task, argv[3] if len(argv) > 3 else '')
    print(text if ok else 'REFUSED: ' + text)
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
