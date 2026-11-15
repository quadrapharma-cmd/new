"""The program's EDA review questions cite what the library («المكتبة», apps/dossier-builder-v2/knowledge) checked against each
source word for word: the in-force GL.CADC.002 version 3 and its sections, the corrected sections and quotes. tools/library_sync.py
brings them over; this fails when the library and the program part again (run the tool, then look at what it changed)."""
import pathlib, sys
import pytest
import yaml

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'tools'))
import library_sync  # noqa: E402

pytestmark = pytest.mark.skipif(not library_sync.LIBRARY.exists(), reason='the library (apps/dossier-builder-v2) is not in this checkout')


def test_every_review_question_cites_what_the_library_checked():
    changed, missing = library_sync.sync(write=False)
    assert missing == [] and changed == [], [(c[1], c[3]) for c in changed[:5]]


def test_no_review_question_cites_the_superseded_cadc_guideline():
    old = [r['id'] for f in (HERE / 'rulepacks' / 'eda.review.v1').glob('*.yaml') if f.name != 'pack.yaml'
           for r in yaml.safe_load(f.read_text(encoding='utf-8')) or [] if 'GL.CADC.002 v02' in str((r.get('source') or {}).get('code'))]
    assert old == []
    q = {r['id']: r for r in yaml.safe_load((HERE / 'rulepacks' / 'eda.review.v1' / 'cadc.yaml').read_text(encoding='utf-8'))}
    assert q['CD-65-01']['source'] == {'code': 'GL.CADC.002 v3/2026', 'section': '§5.6.2',
                                       'quote': 'Whenever a pharmacopeia is used as a reference, this shall always refer to the most recent version thereof.'}
