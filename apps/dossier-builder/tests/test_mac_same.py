"""The made-up dossier made ready on this computer, against what the cloud edition made of it (tests/expected/mac-same): each
page's reading, the cut, the pages left out, the findings, the corrections, the product information and the reports (their
text, fonts and pages drawn, compared within a few grey levels), the eCTD sequence and its validation. On a Mac this says that
the Mac makes the same dossier. EBOX_RECORD=1 records what this computer makes (done in the cloud edition)."""
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pikepdf
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'engine'))
sys.path.insert(0, str(HERE))

from dossier_engine.combined import assemble, checks, decide, ocr, read, repeats, report, split  # noqa: E402
from dossier_engine.combined.common import Work  # noqa: E402

import combined_fixture  # noqa: E402
from claude_script import ScriptedClient  # noqa: E402
from test_decide import SCRIPT  # noqa: E402

EXPECTED = HERE / 'expected' / 'mac-same'
RECORD = os.environ.get('EBOX_RECORD') == '1'
NEED = [t for t in ('ocrmypdf', 'tesseract', 'pdftoppm', 'pdftotext', 'soffice') if not shutil.which(t)]
pytestmark = pytest.mark.skipif(bool(NEED) or not (RECORD or EXPECTED.exists()), reason='tools or the recorded outputs missing')
DPI = 40
GREY = 48               # a drawn pixel differs when its grey differs by more than this
MOST = 0.004            # the share of a page's pixels that may differ (antialiasing, not words)


@pytest.fixture(scope='module')
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp('same')
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    read.run(root / 'received', w)
    repeats.run(w)
    ocr.run(w)
    split.run(w)
    assemble.run(w)
    checks.run(w)
    (w.root / 'dossier.json').write_text(json.dumps({'ctd_folder': 'Zentorix dossier', 'deliver': {'name': 'Zentorix eCTD', 'zip': 'z.zip'},
                                                     'ectd': {'today': '2026-11-22', 'envelope': {
                                                         'identifier': '0a7c1c1e-5b8a-4d6e-9f10-3c2b1a0d9e8f'}}}), encoding='utf-8')
    (w.root / 'decide.json').write_text('{}', encoding='utf-8')
    assemble.run(w)
    decide.run(w, client=ScriptedClient(SCRIPT, w), budget_usd=5)
    report.run(w)
    return w


def norm(t, w):
    return re.sub(r'\s+', ' ', (t or '').replace(str(w.root), '<work>')).strip()


def sha(t):
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:16]


def outputs(w):
    rep = w.load('report.json')
    pdfs = sorted(w.pi.glob('*.pdf')) + sorted(w.fixed.rglob('*.pdf')) + [Path(rep['ctd']['pdf']), Path(rep['ectd']['pdf'])]
    return [p for p in pdfs if p.exists()]


def fonts(pdf):
    out = set()
    with pikepdf.open(pdf) as p:
        for page in p.pages:
            for f in (page.obj.Resources.get('/Font') or {}).values():
                out.add(str(f.get('/BaseFont', '')).split('+')[-1])
    return sorted(out)


def drawn(pdf):
    from PIL import Image
    tmp = Path(str(pdf) + '.render')
    tmp.mkdir(exist_ok=True)
    subprocess.run(['pdftoppm', '-r', str(DPI), '-gray', '-png', str(pdf), str(tmp / 'p')], check=True)
    pages = [Image.open(f).convert('L') for f in sorted(tmp.glob('p-*.png'))]
    shutil.rmtree(tmp)
    return pages


def fingerprint(w):
    plan = w.load('plan.json')
    e = w.load('ectd.json')
    fp = {'ocr': [sha(norm(t, w)) for t in w.pages_text('read/ocr.txt')],
          'plan': [[d['path'], d['ctd'], d['pages']] for d in plan['docs']],
          'removed': [[r['page'], r['why']] for r in plan['removed']],
          'findings': [[f['rule'], f['severity'], f.get('where', '')] for f in w.load('findings.json')],
          'leaves': [[l['code'], f"{l['folder']}/{l['file']}", l['title']] for l in e['leaves']],
          'm1': [[m[0], m[2], m[3]] for m in e['m1']],
          'validation': [[r['rule'], r['ok']] for r in w.load('validation.json')],
          'pdfs': {}}
    for p in outputs(w):
        text = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(p), '-'], capture_output=True).stdout.decode('utf-8', 'replace')
        with pikepdf.open(p) as pdf:
            n = len(pdf.pages)
        fp['pdfs'][p.name] = {'pages': n, 'text': sha(norm(text, w)), 'fonts': fonts(p)}
    return fp


def differs(a, b):
    """The share of pixels whose grey differs by more than GREY (pages of different sizes: all of them)."""
    if a.size != b.size:
        return 1.0
    from PIL import ImageChops
    d = ImageChops.difference(a, b).point(lambda v: 255 if v > GREY else 0)
    return sum(d.histogram()[255:]) / (a.size[0] * a.size[1])


def test_the_same_dossier_as_the_cloud_edition(made):
    w = made
    fp = fingerprint(w)
    if RECORD:
        EXPECTED.mkdir(parents=True, exist_ok=True)
        (EXPECTED / 'fingerprint.json').write_text(json.dumps(fp, ensure_ascii=False, indent=1), encoding='utf-8')
        for p in outputs(w):
            for i, im in enumerate(drawn(p), 1):
                im.save(EXPECTED / f'{p.stem}-{i}.png', optimize=True)
        pytest.skip('recorded')
    want = json.loads((EXPECTED / 'fingerprint.json').read_text(encoding='utf-8'))
    diffs = []
    for k in ('plan', 'removed', 'findings', 'leaves', 'm1', 'validation'):
        if fp[k] != want[k]:
            diffs.append(f'{k}: here {fp[k]} | cloud {want[k]}'[:1500])
    pages = [i + 1 for i, (a, b) in enumerate(zip(fp['ocr'], want['ocr'])) if a != b]
    if pages or len(fp['ocr']) != len(want['ocr']):
        texts = w.pages_text('read/ocr.txt')
        diffs.append('OCR differs on pages ' + ', '.join(map(str, pages)) + ': '
                     + ' | '.join(f'p {p}: {norm(texts[p - 1], w)[:160]!r}' for p in pages[:5]))
    for name, x in want['pdfs'].items():
        y = fp['pdfs'].get(name)
        if not y:
            diffs.append(f'{name}: not made here')
            continue
        for k in ('pages', 'text', 'fonts'):
            if x[k] != y[k]:
                diffs.append(f'{name} {k}: here {y[k]} | cloud {x[k]}')
    from PIL import Image
    for p in outputs(w):
        for i, im in enumerate(drawn(p), 1):
            ref = EXPECTED / f'{p.stem}-{i}.png'
            if ref.exists():
                share = differs(im, Image.open(ref).convert('L'))
                if share > MOST:
                    diffs.append(f'{p.name} page {i}: {share:.4f} of its pixels drawn otherwise')
    assert not diffs, '\n'.join(diffs)
