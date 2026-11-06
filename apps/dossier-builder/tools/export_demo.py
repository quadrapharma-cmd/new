#!/usr/bin/env python3
"""Export one dossier to all three outputs (P1): CTD, eCTD 3.2.2, eCTD 4.0.
Placeholder PDFs stand in for the company's documents; both eCTD outputs are
validated (xmllint DTD / ICH XSD).

  python3 tools/export_demo.py examples/examplol.yaml /tmp/out
"""
import pathlib, subprocess, sys, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path[:0] = [str(ROOT / 'engine'), str(ROOT / 'tests')]
import yaml
from fixtures_pdf import make_pdf
from dossier_engine import packs
from dossier_engine.profile import Profile
from dossier_engine.resolver import resolve, summary
from dossier_engine.assemble import docs_for
from dossier_engine.writers import ctd, ectd32, ectd40

prof_path, out = sys.argv[1], pathlib.Path(sys.argv[2])
prof = Profile.from_dict(yaml.safe_load(open(prof_path, encoding='utf-8')))
slots = resolve(prof, packs.load('eda.ctd.nta065.v5'))
src = out / '_placeholders'
src.mkdir(parents=True, exist_ok=True)
files = {}
for s in slots:
    if not s.active:
        continue
    f = str(make_pdf(src / (''.join(c if c.isalnum() else '_' for c in s.slot_id) + '.pdf'),
                     f'PLACEHOLDER {s.slot_id} - {s.title["en"][:60]}'))
    if s.req_id == 'M1-09':
        files[s.slot_id] = [dict(file=f, title='SmPC (English)', pi_type='spc', lang='en'),
                            dict(file=f, title='Package Leaflet (Arabic)', pi_type='pl', lang='ar')]
    elif s.module == 5:
        files[s.slot_id] = [dict(file=f, study='EXM-BE-01', doc_type='ich_document_type_2')]
    else:
        files[s.slot_id] = [dict(file=f)]
docs, ctd_only = docs_for(slots, prof, files)
product = ectd32.Product('Examplol 500 mg', 'film-coated tablet', 'Example Pharma', indication='pain-and-fever')
app_uuid = '0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11'
inn = sorted({a.name.lower() for a in prof.apis})
reg = ectd32.REG_TYPE[prof.licence]

r1 = ctd.write(out / 'ctd', 'Examplol 500 mg FCT', slots, files)
r2 = ectd32.write(out / 'ectd-3.2.2', ectd32.Envelope(
    identifier=app_uuid, submission_type='maa', tracking=['P-MAA-0001'], unit='initial', applicant='Example Pharma S.A.E.',
    invented_name='Examplol 500 mg film-coated tablets', registration=reg, marketing='local', inn=inn,
    description='Initial MAA (demo, placeholder PDFs)'), product, docs)
r3 = ectd40.write(out / 'ectd-4.0', ectd40.Envelope4(
    application_uuid=app_uuid, submission_uuid='6f1f0c0e-1d0a-4f8e-8b8c-0b9a3c2d1e01', tracking='P-MAA-0001',
    submission_type='maa', unit='initial', sequence=1, title='Initial MAA (demo, placeholder PDFs)',
    applicant='Example Pharma S.A.E.', applicant_portal_id='EXAMPLE-0001', product_name='Examplol 500 mg',
    inn=inn, registration=reg, marketing='local'), product, docs)
import shutil; shutil.rmtree(src)

ok = True
def check(cmd, label):
    global ok
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"  {label}: {'VALID' if r.returncode == 0 else 'INVALID ' + r.stderr[:300]}")
    ok &= r.returncode == 0

print(f'Requirements: {summary(slots)}')
print(f"CTD:        {r1['path']}  ({len(r1['files'])} files, missing R: {r1['missing'] or 'none'})")
print(f"eCTD 3.2.2: {r2['path']}  ({r2['leaves']} leaves)")
check(['xmllint', '--noout', '--valid', r2['path'] + '/index.xml'], 'index.xml (ICH DTD)')
check(['xmllint', '--noout', '--valid', r2['path'] + '/m1/eg/eg-regional.xml'], 'eg-regional.xml (EG provisional DTD)')
print(f"eCTD 4.0:   {r3['path']}  ({r3['documents']} documents, {r3['keyword_definitions']} keyword definitions)")
xsd_dir = out / '_xsd'
with zipfile.ZipFile(REPO / 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip') as z:
    z.extractall(xsd_dir)
check(['xmllint', '--noout', '--schema', str(next(xsd_dir.rglob('PORP_IN000001UV.xsd'))), r3['path'] + '/submissionunit.xml'],
      'submissionunit.xml (ICH XSD)')
shutil.rmtree(xsd_dir)
print(f'CTD-only items (no eCTD node): {ctd_only}')
print('PROVISIONAL EG profiles: conforms to EDA drafts + ICH; not "EDA-valid".')
sys.exit(0 if ok else 1)
