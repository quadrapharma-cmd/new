#!/usr/bin/env python3
"""Build a demo eCTD 3.2.2 sequence 0000 for a profile, with one placeholder PDF
per required slot, then validate it with xmllint.

  python3 tools/build_demo_ectd32.py examples/examplol.yaml /tmp/out
"""
import pathlib, shutil, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'engine'), str(ROOT / 'tests')]
import yaml
from fixtures_pdf import make_pdf
from dossier_engine import packs
from dossier_engine.profile import Profile
from dossier_engine.resolver import resolve
from dossier_engine.assemble import docs_for
from dossier_engine.writers.ectd32 import write, Envelope, Product, REG_TYPE

prof_path, out = sys.argv[1], pathlib.Path(sys.argv[2])
prof = Profile.from_dict(yaml.safe_load(open(prof_path, encoding='utf-8')))
slots = resolve(prof, packs.load('eda.ctd.nta065.v5'))
src = out / '_placeholders'
src.mkdir(parents=True, exist_ok=True)
files = {}
for s in slots:
    if not s.active:
        continue
    f = make_pdf(src / (''.join(c if c.isalnum() else '_' for c in s.slot_id) + '.pdf'),
                 f'PLACEHOLDER {s.slot_id} - {s.title["en"][:60]}')
    files[s.slot_id] = ([dict(file=str(f), title='SmPC (English)', pi_type='spc', lang='en'),
                         dict(file=str(f), title='Package Leaflet (Arabic)', pi_type='pl', lang='ar')]
                        if s.req_id == 'M1-09' else [dict(file=str(f))])
docs, unplaced = docs_for(slots, prof, files)
env = Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['P-MAA-0001'],
               unit='initial', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg film-coated tablets',
               registration=REG_TYPE[prof.licence], marketing='local', inn=sorted({a.name.lower() for a in prof.apis}),
               description='Initial MAA (demo, placeholder PDFs)')
rep = write(out / 'ectd', env, Product('Examplol 500 mg', 'film-coated tablet', 'Example Pharma', 'pain-and-fever'), docs)
shutil.rmtree(src)
ok = True
for x in ('index.xml', 'm1/eg/eg-regional.xml'):
    r = subprocess.run(['xmllint', '--noout', '--valid', str(pathlib.Path(rep['path']) / x)], capture_output=True, text=True)
    print(f"{x}: {'VALID' if r.returncode == 0 else 'INVALID'}")
    ok &= r.returncode == 0
print(f"{rep['leaves']} leaves, {len(rep['files'])} files -> {rep['path']}; CTD-only (not placed): {unplaced}")
sys.exit(0 if ok else 1)
