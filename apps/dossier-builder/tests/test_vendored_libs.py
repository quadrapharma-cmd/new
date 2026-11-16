"""The browser edition runs the engine on the libraries it ships (web/vendor/wheels), not on the ones installed here. A newer
pypdf took calls away (7.0: add_js) and the edition failed where the tests, on the local pypdf, passed. So the engine's own scripted
checks (the qualification's OQ: the PDF checks, the fixes, the writers, the export gate) are run once on the wheels the browser
edition ships, in a process of their own. Skipped where the wheels were not fetched (web/vendor.sh)."""
import json, pathlib, subprocess, sys
import pytest

APP = pathlib.Path(__file__).resolve().parents[1]
WHEELS = APP / 'web' / 'vendor' / 'wheels'
PURE = ('pypdf', 'python_docx')                                     # pure-Python wheels the engine calls directly: importable from the wheel itself

RUN = r'''
import json, sys
wheels, engine = sys.argv[1:-1], sys.argv[-1]
for w in wheels:
    sys.path.insert(0, w)
sys.path.insert(0, engine)
import pypdf, docx
from dossier_engine import qualification
rows = qualification.oq()
print(json.dumps({'pypdf': pypdf.__version__, 'pypdf_file': pypdf.__file__, 'docx_file': docx.__file__,
                  'failed': [r for r in rows if r['result'] == 'fail'], 'passed': sum(1 for r in rows if r['result'] == 'pass')}))
'''


def wheels():
    out = []
    for name in PURE:
        hit = sorted(WHEELS.glob(f'{name}-*-py3-none-any.whl')) if WHEELS.is_dir() else []
        if not hit:
            pytest.skip(f'{name} wheel not vendored (web/vendor.sh)')
        out.append(str(hit[-1]))
    return out


def test_the_scripted_checks_pass_on_the_libraries_the_browser_edition_ships():
    ws = wheels()
    r = subprocess.run([sys.executable, '-c', RUN, *ws, str(APP / 'engine')], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-3000:]
    j = json.loads(r.stdout.strip().splitlines()[-1])
    assert '.whl' in j['pypdf_file'] and '.whl' in j['docx_file'], j                 # really the shipped ones
    assert not j['failed'], j['failed']
    assert j['passed'] >= 10, j
