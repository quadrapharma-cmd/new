"""The desk's work sessions run the program with Python 3.11 (28/11/2026: an f-string quoting inside itself, which needs 3.12,
stopped the eCTD stage of a real dossier there). Every file of the program must compile with 3.11."""
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
PY311 = shutil.which('python3.11')


@pytest.mark.skipif(not PY311, reason='python3.11 is not installed here')
def test_every_file_compiles_with_python_311():
    code = ("import pathlib,sys\nbad=[]\n"
            "for p in sorted(pathlib.Path(sys.argv[1]).rglob('*.py')):\n"
            "    if any(x in p.parts for x in ('.cache','node_modules','vendor','dist')): continue\n"
            "    try: compile(p.read_text(encoding='utf-8'), str(p), 'exec')\n"
            "    except SyntaxError as e: bad.append(f'{p}:{e.lineno}: {e.msg}')\n"
            "print('\\n'.join(bad)); sys.exit(1 if bad else 0)\n")
    r = subprocess.run([PY311, '-I', '-c', code, str(APP)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
