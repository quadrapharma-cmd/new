"""Any eCTD package, made anywhere (updates list, item 18): a ZIP is checked sequence by sequence by its region's criteria, a region
without criteria here gets the ICH checks every eCTD must pass, and two packages are compared."""
import io, zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from dossier_engine.writers import ectd32_eu as eu
from dossier_engine.validators import package
from test_ectd32_eu import envelope, docs, PROD          # noqa: F401  (the EU fixture)


def zipped(root, rename=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for p in sorted(Path(root).rglob('*')):
            if p.is_file():
                name = p.relative_to(root).as_posix()
                z.writestr(rename(name) if rename else name, p.read_bytes())
    return buf.getvalue()


@pytest.fixture()
def seq(tmp_path, docs):
    e = envelope()
    eu.write(tmp_path / 'out', e, PROD, eu.resolve(docs, e))
    return tmp_path / 'out'


def test_a_package_made_anywhere_is_checked_by_its_regions_criteria(tmp_path, seq):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    r = c.post('/api/package/validate', files={'file': ('dermacure.zip', zipped(seq, lambda n: 'Dermacure eCTD/' + n), 'application/zip')}).json()
    assert r['sequences'] == [{'sequence': '0000', 'region': 'eu', 'ok': True, 'counts': r['sequences'][0]['counts'], 'coverage': '108/111'}]
    assert r['ok'] and 'Not an EMA-accepted validator' in r['html']
    other = tmp_path / 'other'
    (other / 'docs').mkdir(parents=True)
    (other / 'docs' / 'note.txt').write_text('no sequence here')
    bad = c.post('/api/package/validate', files={'file': ('x.zip', zipped(other), 'application/zip')})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-NO-SEQUENCE' and bad.json()['detail']['ar']


def test_a_region_without_criteria_gets_the_ich_checks(tmp_path, seq):
    s = seq / '0000'
    (s / 'm1' / 'eu' / 'eu-regional.xml').rename(s / 'm1' / 'eu' / 'xx-regional.xml')       # a region this program has no criteria for
    stray = s / 'm3' / 'stray.pdf'
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b'%PDF-1.4 stray')
    r = package.validate_files([(p.relative_to(seq).as_posix(), p.read_bytes()) for p in seq.rglob('*') if p.is_file()], 'other')
    row = r['sequences'][0]
    assert row['region'] == 'ich' and not row['ok']
    assert 'ICH-EXTRA' in r['html'] and 'stray.pdf' in r['html']


def test_two_packages_are_compared_leaf_by_leaf(tmp_path, seq, docs):
    a = [(p.relative_to(seq).as_posix(), p.read_bytes()) for p in seq.rglob('*') if p.is_file()]
    b = []
    for name, data in a:
        if name.endswith('common-spc.pdf'):
            data = data + b'\n%changed'
        b.append((name, data))
    assert package.compare_files(a, a)['same']
    diff = package.compare_files(a, b)
    ch = diff['sequences'][0]['changes']
    assert not diff['same'] and [x['change'] for x in ch] == ['changed'] and ch[0]['href'].endswith('common-spc.pdf')   # the file itself changed
    c = TestClient(create_app(tmp_path / 'ws2', auth_enabled=False))
    r = c.post('/api/package/compare', files={'a': ('a.zip', zipped(seq), 'application/zip'), 'b': ('b.zip', zipped(seq), 'application/zip')}).json()
    assert r['same'] is True
