"""Writer 1 (CTD One Submission): folders, navigator, checklist, missing items, safety."""
import csv
from datetime import date
import pytest
from fixtures_pdf import make_pdf
from dossier_engine import packs
from dossier_engine.profile import Profile, Api
from dossier_engine.resolver import resolve
from dossier_engine.writers.ctd import write
from dossier_engine.writers.ectd32 import WriterError


@pytest.fixture()
def slots():
    p = Profile(licence='own', activity='re_registration', dosage_specifics=['coated'], pharmacopoeial=True,
                apis=[Api('Paracetamol', 'Granules India', 'CEP')])
    return resolve(p, packs.load('eda.ctd.nta065.v5'), today=date(2026, 11, 6))


def test_package(tmp_path, slots):
    f = str(make_pdf(tmp_path / 'x.pdf', 'x'))
    files = {s.slot_id: [dict(file=f)] for s in slots if s.active and s.req_id not in ('M1-07', 'P-07')}
    files['M1-07'] = [dict(file=f, variation='Addition of API manufacturer', date='2024-03-01'),
                      dict(file=f, variation='Change in batch size', date='2025-07-15')]
    rep = write(tmp_path / 'out', 'Examplol 500 mg FCT', slots, files)
    fs = rep['files']
    assert rep['missing'] == ['P-07']                        # process validation not uploaded
    assert any(x.startswith('Module 1/01 1.1.1 ') for x in fs)
    assert any('2024-03-01 Addition of API manufacturer' in x for x in fs)   # 1.1.7 one folder per variation
    assert any(x.startswith('Module 3/3.2.S Paracetamol - Granules India/') for x in fs)
    assert all(len('Examplol 500 mg FCT/' + x) <= 180 for x in fs)
    rows = list(csv.reader(open(tmp_path / 'out' / 'Examplol 500 mg FCT' / '00-checklist.csv', encoding='utf-8-sig')))
    st = {r[0]: r[6] for r in rows[1:] if '@' not in r[0]}
    assert st['P-07'] == 'Missing' and st['M1-14'] == 'Not applicable' and st['M2-02'] == 'Not required'
    nav = (tmp_path / 'out' / 'Examplol 500 mg FCT' / '00-navigator.html').read_text()
    assert 'dir="ltr"' in nav and 'عربي' in nav and 'Missing' in nav and 'ناقص' in nav


def test_never_overwrites(tmp_path, slots):
    write(tmp_path, 'A', slots, {})
    with pytest.raises(WriterError):
        write(tmp_path, 'A', slots, {})


def test_windows_safe_names(tmp_path, slots):
    rep = write(tmp_path, 'Bad:Name?*', slots, {})
    assert 'Bad Name' in rep['path']
