"""End-to-end: seed profile -> resolver -> one PDF per active slot -> eCTD 3.2.2 0000 -> DTD-valid."""
import shutil, subprocess
from datetime import date
import pytest
from fixtures_pdf import make_pdf
from dossier_engine import packs
from dossier_engine.profile import Profile, Api
from dossier_engine.resolver import resolve
from dossier_engine.assemble import docs_for
from dossier_engine.writers.ectd32 import write, Envelope, Product, REG_TYPE

XMLLINT = shutil.which('xmllint')


@pytest.mark.skipif(not XMLLINT, reason='xmllint not installed')
def test_seed_dossier_exports_valid_ectd32(tmp_path):
    prof = Profile(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True,
                   dosage_specifics=['coated'],
                   apis=[Api('Paracetamol', 'Granules India', 'CEP'), Api('Paracetamol', 'Anqiu Luan', 'FULL')])
    slots = resolve(prof, packs.load('eda.ctd.nta065.v5'), today=date(2026, 11, 6))
    files = {}
    for s in slots:
        if not s.active:
            continue
        f = make_pdf(tmp_path / (s.slot_id.replace('|', '_').replace('@', '_').replace(' ', '') + '.pdf'), s.slot_id)
        if s.req_id == 'M1-09':
            files[s.slot_id] = [dict(file=str(f), title='SmPC (English)', pi_type='spc', lang='en'),
                                dict(file=str(f), title='Package leaflet (Arabic)', pi_type='pl', lang='ar')]
        else:
            files[s.slot_id] = [dict(file=str(f))]
    docs, unplaced = docs_for(slots, prof, files)
    assert unplaced == ['M5-01']                    # TOC exists only in the CTD output
    env = Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['P-MAA-0001'],
                   unit='initial', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg',
                   registration=REG_TYPE[prof.licence], marketing='local', inn=['paracetamol'], description='Initial MAA')
    rep = write(tmp_path / 'out', env, Product('Examplol 500 mg', 'film-coated tablet', 'Example Pharma', indication='pain-and-fever'), docs)
    base = tmp_path / 'out' / '0000'
    for x in ('index.xml', 'm1/eg/eg-regional.xml'):
        r = subprocess.run([XMLLINT, '--noout', '--valid', str(base / x)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[:2000]
    assert rep['leaves'] == len(docs) + 1
    assert len(docs) > 80
