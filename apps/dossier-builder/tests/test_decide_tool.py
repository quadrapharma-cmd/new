"""Claude in a cloud session takes the «decide» stage's decisions through decide/tool.py, one command a call and no API key: the
made-up dossier and the decisions of tests/test_decide.py, sent as a session sends them. The same refusals with the same reasons,
the same decisions file, cut and findings as through the API (the stand-in of tests/claude_script.py), and the program goes on to
the eCTD sequence and the reports. No network, no key, no cost."""
import contextlib
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'engine'
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(HERE))

from dossier_engine.combined import assemble, checks, decide, ocr, read, repeats, report, split  # noqa: E402
from dossier_engine.combined.common import Work  # noqa: E402
from dossier_engine.combined.decide import tool  # noqa: E402

import combined_fixture  # noqa: E402
from claude_script import ScriptedClient  # noqa: E402
from test_decide import M2, MOCK, NEED, SCRIPT, SUBST  # noqa: E402

pytestmark = pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')


def made(root):
    """The made-up dossier read, cut and checked, as tests/test_decide.py makes it."""
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    read.run(root / 'received', w)
    repeats.run(w)
    ocr.run(w)
    split.run(w)
    assemble.run(w)
    checks.run(w)
    (w.root / 'dossier.json').write_text(json.dumps({'ctd_folder': 'Zentorix dossier', 'ectd': {'today': '2026-11-22'}}),
                                         encoding='utf-8')
    assemble.run(w)
    return w


def cli(w, *args):
    """One command as the session sends it: (exit code, what it printed)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = tool.main([str(w.root), *args])
    return code, buf.getvalue()


def refusal(out):
    """The reason of a refusal: the last thing a refused command prints, whole."""
    i = out.find('REFUSED: ')
    return out[i + len('REFUSED: '):].rstrip('\n') if i >= 0 else None


@pytest.fixture(scope='module')
def both(tmp_path_factory):
    root = tmp_path_factory.mktemp('decide-tool')
    # through the session: every task's brief, then the script's calls one by one
    w = made(root / 'session')
    sent = []                                         # (task, tool, exit code, refusal or None)
    for task in decide.TASKS:
        code, out = cli(w, 'brief', task)
        assert code == 0 and '===== the case file =====' in out and 'RECEIVED FILES' in out, out[-800:]
        for turn in SCRIPT[task]:
            for name, inp in turn:
                if name == 'finish':
                    code, out = cli(w, 'finish', task, inp['summary'])
                    sent.append((task, name, code, refusal(out)))
                    if code and refusal(out).startswith('Not finished:'):       # left out on purpose: finish again
                        code, out = cli(w, 'finish', task, inp['summary'])
                        sent.append((task, name, code, refusal(out)))
                else:
                    code, out = cli(w, 'call', task, name, json.dumps(inp, ensure_ascii=False))
                    sent.append((task, name, code, refusal(out)))
    # through the API's stand-in, on a second copy
    a = made(root / 'api')
    (a.root / 'decide.json').write_text('{}', encoding='utf-8')
    client = ScriptedClient(SCRIPT, a)
    rec = decide.run(a, client=client, budget_usd=5)
    return w, sent, a, client, rec


def plain(dec):
    """A decisions file without what is made new on each run (the envelope's random identifier)."""
    dec = json.loads(json.dumps(dec))
    (dec.get('ectd') or {}).get('envelope', {}).pop('identifier', None)
    return dec


def test_the_same_decisions_as_through_the_api(both):
    w, _, a, _, rec = both
    assert rec['finished']
    assert plain(w.decisions()) == plain(a.decisions())
    assert w.load('decisions/pi-content.json') == a.load('decisions/pi-content.json')
    assert [(d['ctd'], d['path'], d['pages'], d.get('by')) for d in w.load('plan.json')['docs']] == \
           [(d['ctd'], d['path'], d['pages'], d.get('by')) for d in a.load('plan.json')['docs']]
    assert w.load('findings.json') == a.load('findings.json')
    leaves = lambda x: sorted((l['doc'], l['title'], Path(l['source']).name) for l in x.load('ectd.json')['leaves'])   # noqa: E731
    assert leaves(w) == leaves(a)


def test_every_refusal_with_its_reason(both):
    _, sent, _, client, _ = both
    errs = [r for _, _, code, r in sent if code]
    assert all(code in (0, 2) for _, _, code, _ in sent)
    api = [e for e in client.errors() if not e.startswith('Not finished:')]
    assert len(api) == 7
    assert [e for e in errs if not e.startswith('Not finished:')] == api            # the same seven, word for word, in order
    # finish with a refused decision never made again: refused once (task 1's repeated page), accepted when asked again
    nf = [(t, r) for t, n, code, r in sent if n == 'finish' and code]
    assert nf == [('documents', 'Not finished: 1 refused decision(s) since the last finish were not made again (leave_out). '
                                'Correct them; or, if you leave them out on purpose, call finish again.')]
    finishes = [(t, code) for t, n, code, _ in sent if n == 'finish']
    assert finishes == [('documents', 2), ('documents', 0), ('product', 0), ('pi', 0), ('review', 0), ('sequence', 0), ('sequence', 0)]


def test_the_record_and_the_log(both):
    w, _, _, _, _ = both
    rec = w.load('decide.json')
    assert rec['finished'] and rec['model'] == 'session' and 'skipped' not in rec
    assert all(rec['tasks'][t]['finished'] and rec['tasks'][t]['by'] == 'session' for t in decide.TASKS)
    assert rec['tasks']['sequence']['summary'] == 'Two titles; the bad file name dropped.'
    log = [json.loads(l) for l in (w.root / 'decide' / 'log.jsonl').read_text(encoding='utf-8').splitlines()]
    assert all(e['by'] == 'session' for e in log)
    assert sum(1 for e in log if not e['ok']) == 8
    code, out = cli(w, 'status')
    assert code == 0 and out.count('done') == 5


def test_the_tasks_go_in_their_order(tmp_path):
    w = Work(tmp_path / 'w')
    code, out = cli(w, 'call', 'product', 'set_titles', '{}')
    assert code == 2 and refusal(out).startswith('finish the task «documents» first')
    code, out = cli(w, 'tools', 'sequence')                                         # the tools can be read at any time
    assert code == 0 and {t['name'] for t in json.loads(out)} >= {'read_pages', 'view_page', 'search_text', 'set_leaf'}
    assert cli(w, 'nothing')[0] == 1 and cli(w, 'brief', 'nothing')[0] == 1


def test_wrong_inputs_are_refused_with_the_reason(both):
    w, _, _, _, _ = both
    code, out = cli(w, 'call', 'review', 'read_pages', '{"pages": ')
    assert code == 2 and refusal(out).startswith('the input is not JSON')
    code, out = cli(w, 'call', 'review', 'read_pages', '{}')
    assert code == 2 and 'input.pages is missing' in refusal(out)
    code, out = cli(w, 'call', 'review', 'set_leaf', '{}')
    assert code == 2 and refusal(out).startswith('No tool «set_leaf» in the task «review»')
    code, out = cli(w, 'call', 'review', 'finish', '{"summary": "x"}')
    assert code == 2 and 'its own command' in refusal(out)
    code, out = cli(w, 'call', 'review', 'read_pages', '["1"]')
    assert code == 2 and 'JSON object' in refusal(out)
    code, out = cli(w, 'finish', 'review', '  ')
    assert code == 2 and 'summary' in refusal(out)


def test_a_long_input_from_a_file_or_stdin(both, tmp_path, monkeypatch):
    w, _, _, _, _ = both
    f = tmp_path / 'in.json'
    f.write_text('{"pages": "1"}', encoding='utf-8')
    code, out = cli(w, 'call', 'review', 'read_pages', '@' + str(f))
    assert code == 0 and '— page 1 —' in out
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{"pages": "2"}'))
    code, out = cli(w, 'call', 'review', 'read_pages', '-')
    assert code == 0 and '— page 2 —' in out
    code, out = cli(w, 'call', 'review', 'read_pages', '@' + str(tmp_path / 'none.json'))
    assert code == 2 and refusal(out).startswith('the input file could not be read')


def test_a_page_is_read_and_seen(both):
    w, _, _, _, _ = both
    code, out = cli(w, 'call', 'review', 'read_pages', '{"pages": "1-2"}')
    assert code == 0 and '— page 1 —' in out and '— page 2 —' in out
    code, out = cli(w, 'call', 'review', 'view_page', '{"page": 3}')
    png = w.root / 'decide' / 'view-3.png'
    assert code == 0 and str(png) in out and 'page 3 (of ' in out
    head = png.read_bytes()[:24]
    assert head[:8] == b'\x89PNG\r\n\x1a\n' and max(struct.unpack('>II', head[16:24])) <= 1600
    code, out = cli(w, 'call', 'review', 'search_text', '{"text": "zentorine"}')
    assert code == 0 and out.strip()


def test_the_sequence_and_the_reports(both):
    w, _, _, _, _ = both
    failed = [r['rule'] for r in w.load('validation.json') if not r['ok'] and r['kind'] == 'P/F']
    assert failed == ['EG-PF-E06']                                                  # only the tracking number EDA gives
    e = w.load('ectd.json')
    leaf = next(l for l in e['leaves'] if l['doc'] == M2)
    assert leaf['title'] == 'Introduction to the dossier' and leaf['source'].endswith('.fixed.pdf')
    assert any(x[3] == 'Mock-ups of the current packs - Egyptian artwork to follow' for x in e['m1'])
    assert any(d['path'].startswith(SUBST) for d in w.load('plan.json')['docs'])
    out = report.run(w)
    assert Path(out['ctd']['pdf']).stat().st_size > 5000 and Path(out['ectd']['pdf']).exists()


def test_a_persons_decisions_are_left_as_they_are(tmp_path):
    w = Work(tmp_path / 'w')
    (w.root / 'dossier.json').write_text(json.dumps({'plan': [{'pages': '1', 'drop': 'cover'}]}), encoding='utf-8')
    code, out = cli(w, 'brief', 'documents')
    assert code == 2 and 'a person made' in refusal(out) and not (w.root / 'decide.json').exists()


def test_the_command_itself(both):
    w, _, _, _, _ = both
    env = {**os.environ, 'PYTHONPATH': str(ENGINE)}
    p = subprocess.run([sys.executable, '-m', 'dossier_engine.combined.decide.tool', str(w.root), 'status'],
                       capture_output=True, text=True, env=env, cwd=str(ENGINE), timeout=120)
    assert p.returncode == 0 and p.stdout.count('done') == 5, p.stderr[-800:]
    p = subprocess.run([sys.executable, '-m', 'dossier_engine.combined.decide.tool'], capture_output=True, text=True, env=env,
                       cwd=str(ENGINE), timeout=120)
    assert p.returncode == 1 and 'brief <task>' in p.stdout
