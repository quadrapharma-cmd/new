"""A failure nobody expected is answered in words, in every edition (16/11/2026). Before: the desktop and cloud editions answered a
bare «Internal Server Error», and the browser edition's English text was the Python traceback itself. Now the engine answers
{code: E-INTERNAL, en, ar, where}: a plain sentence for the person, and for the faults record («سجل الأعطال») the kind of error
and the engine's own lines — never the error's message, which may quote a document."""
import ast, pathlib, re
from fastapi.testclient import TestClient
from dossier_engine.app import api
from dossier_engine.app.store import Store

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_an_unexpected_failure_is_said_plainly_and_names_what_failed(tmp_path, monkeypatch):
    c = TestClient(api.create_app(tmp_path / 'ws'), raise_server_exceptions=False)

    def boom(self, *a, **k):
        raise RuntimeError('quoted from a made-up document: Dermacure 20 mg, batch 240101')
    monkeypatch.setattr(Store, 'list_dossiers', boom)
    r = c.get('/api/dossiers', headers={'X-DB': '1'})
    d = r.json()['detail']
    assert r.status_code == 500 and d['code'] == 'E-INTERNAL'
    assert re.fullmatch(r'RuntimeError @ api\.py:\d+ \w+( < [\w.]+:\d+ \w+)*', d['where']), d['where']      # the kind of error and the engine's lines
    assert 'Dermacure' not in str(d) and '240101' not in str(d) and 'Traceback' not in str(d)               # never what the error quotes
    assert 'سجل الأعطال' in d['ar'] and 'faults record' in d['en']


def test_the_browser_bridge_gives_the_engines_own_answer():
    """The bridge (web/pybridge.py runs only inside Pyodide) no longer writes an answer of its own."""
    src = (ROOT / 'web' / 'pybridge.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == 'dossier_engine.app.api' for a in n.names}
    assert 'internal_error' in names and 'format_exc' not in src
    assert "chunks = [json.dumps({'detail': internal_error(exc)}).encode()]" in src
