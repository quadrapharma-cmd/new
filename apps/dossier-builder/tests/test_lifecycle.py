"""P3 lifecycle: sequence 0000, then 0001 with replace / delete / new — DTD-valid (3.2.2), XSD-valid (4.0)."""
import shutil, subprocess, zipfile
from dataclasses import replace
import pytest
from conftest import REPO
from fixtures_pdf import make_pdf
from dossier_engine.lifecycle import plan, to_ectd32, to_ectd40, current_view
from dossier_engine.writers.ectd32 import write, Envelope, Doc, Product, DEFAULT_PROFILE
from dossier_engine.writers import ectd40
from dossier_engine.validators.ectd32 import validate

XMLLINT = shutil.which('xmllint')
PROD = Product('Examplol 500 mg', 'tablet', 'Example Pharma')
ENV = Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['P-MAA-0001'],
               unit='initial', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg', registration='local',
               marketing='local', inn=['paracetamol'], description='Initial MAA')
API = dict(substance='paracetamol', manufacturer='Granules India')


@pytest.fixture()
def world(tmp_path):
    f = lambda n: str(make_pdf(tmp_path / f'{n}.pdf', n))
    v1 = [Doc('1.0', f('cover0'), 'Cover letter', doc_id='cover0'), Doc('1.0', f('track0'), 'Tracking table', name='tracking', doc_id='track0'),
          Doc('1.2.1', f('af1'), 'Application form', doc_id='af1'), Doc('3.2.P.1', f('p1'), 'Description and composition', doc_id='p1'),
          Doc('3.2.S.4.1', f('s41'), 'Specification', doc_id='s41', **API),
          Doc('1.3.1', f('spc1'), 'SmPC', pi_type='spc', lang='en', doc_id='spc1')]
    return tmp_path, f, v1


def test_plan_replace_delete_new(world):
    tmp, f, v1 = world
    rep = write(tmp / 'app', ENV, PROD, v1)
    hist = [{'seq': '0000', 'leaves': rep['history']}]
    # changes after approval: new application form version, SmPC withdrawn, new stability summary; new cover/tracking
    v2 = [Doc('1.0', f('cover1'), 'Cover letter 0001', doc_id='cover1'), Doc('1.0', f('track1'), 'Tracking table', name='tracking', doc_id='track1'),
          Doc('1.2.1', f('af2'), 'Application form', doc_id='af2'), Doc('3.2.P.1', '', 'Description and composition', doc_id='p1'),
          Doc('3.2.S.4.1', '', 'Specification', doc_id='s41', **API), Doc('3.2.P.8.1', f('p81'), 'Stability summary', doc_id='p81')]
    current = {d.doc_id for d in v2}
    steps = plan(hist, v2, current)
    ops = sorted((s.op, (s.doc or None) and s.doc.doc_id or s.prior['doc_id']) for s in steps)
    assert ops == [('delete', 'spc1'), ('new', 'cover1'), ('new', 'p81'), ('new', 'track1'), ('replace', 'af2')]
    docs = to_ectd32(steps)
    rep2 = write(tmp / 'app', replace(ENV, sequence='0001', submission_type='var-pac-b', mode='single', unit='initial',
                                      related_sequence=['0001'], description='Variation PAC-B'), PROD, docs)
    base = tmp / 'app' / '0001'
    reg = (base / 'm1/eg/eg-regional.xml').read_text()
    af_old = next(l['leaf_id'] for l in rep['history'] if l['doc_id'] == 'af1')
    assert f'operation="replace"' in reg and f'modified-file="../../../0000/m1/eg/eg-regional.xml#{af_old}"' in reg
    assert 'operation="delete" checksum="" checksum-type=""' in reg
    assert 'compositcert' not in reg and '32p1' not in (base / 'index.xml').read_text()        # unchanged: not resent
    if XMLLINT:
        for x in ('index.xml', 'm1/eg/eg-regional.xml'):
            r = subprocess.run([XMLLINT, '--noout', '--valid', str(base / x)], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
    v = validate(base, DEFAULT_PROFILE, previous=[tmp / 'app' / '0000'])
    assert v['ok'], [x for x in v['results'] if x['status'] == 'fail']
    st = {x['rule']: x['status'] for x in v['results']}
    assert st['EG-PF-11.9'] == 'pass' and st['EG-PF-9.8'] == 'pass' and st['EG-PF-13.2'] == 'pass'
    view = current_view(hist + [{'seq': '0001', 'leaves': rep2['history']}])
    assert {l['doc_id'] for l in view.values()} >= {'af2', 'p1', 's41', 'p81'} and 'spc1' not in {l['doc_id'] for l in view.values()}


def test_lifecycle_validator_catches_bad_modified_file(world):
    tmp, f, v1 = world
    write(tmp / 'app', ENV, PROD, v1)
    docs = [Doc('1.0', f('c'), 'Cover', doc_id='c'), Doc('1.0', f('t'), 'Tracking', name='tracking', doc_id='t'),
            Doc('1.2.1', f('af9'), 'AF', operation='replace', modified_file='0000#idDOESNOTEXIST')]
    write(tmp / 'app', replace(ENV, sequence='0001', submission_type='var-pac-n', mode='single', related_sequence=['0001']), PROD, docs)
    v = validate(tmp / 'app' / '0001', DEFAULT_PROFILE, previous=[tmp / 'app' / '0000'])
    st = {x['rule']: x['status'] for x in v['results']}
    assert st['EG-PF-11.9'] == 'fail' and not v['ok']


def test_v4_replace_and_suspend_xsd_valid(world, tmp_path):
    tmp, f, v1 = world
    env4 = ectd40.Envelope4(application_uuid=ENV.identifier, submission_uuid='6f1f0c0e-1d0a-4f8e-8b8c-0b9a3c2d1e01',
                            tracking='P-MAA-0001', submission_type='maa', unit='initial', sequence=1, title='Initial MAA',
                            applicant='Example Pharma S.A.E.', applicant_portal_id='X-1', product_name='Examplol',
                            inn=['paracetamol'], registration='local', marketing='local')
    r1 = ectd40.write(tmp / 'v4', env4, PROD, v1)
    hist = [{'seq': 1, 'leaves': r1['history']}]
    v2 = [Doc('1.0', f('c1'), 'Cover', doc_id='c1'), Doc('1.2.1', f('af2'), 'Application form', doc_id='af2'),
          Doc('3.2.P.1', '', 'P1', doc_id='p1'), Doc('3.2.S.4.1', '', 'S41', doc_id='s41', **API)]
    steps = plan(hist, v2, {d.doc_id for d in v2})
    docs, suspend = to_ectd40(steps)
    assert len(suspend) == 1                                           # the SmPC (1.0 cover/tracking are never suspended)
    r2 = ectd40.write(tmp / 'v4', replace(env4, sequence=2, submission_type='var-pac-b', unit='initial',
                                          submission_uuid='7a1f0c0e-1d0a-4f8e-8b8c-0b9a3c2d1e02'), PROD, docs, suspend=suspend)
    xml = (tmp / 'v4' / ENV.identifier / '2' / 'submissionunit.xml').read_text()
    old_cou = next(l['cou_id'] for l in r1['history'] if l['doc_id'] == 'af1')
    assert f'<relatedContextOfUse><id root="{old_cou}"/>' in xml and 'statusCode code="suspended"' in xml
    xsd_dir = tmp_path / 'xsd'
    with zipfile.ZipFile(REPO / 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip') as z:
        z.extractall(xsd_dir)
    if XMLLINT:
        r = subprocess.run([XMLLINT, '--noout', '--schema', str(next(xsd_dir.rglob('PORP_IN000001UV.xsd'))),
                            str(tmp / 'v4' / ENV.identifier / '2' / 'submissionunit.xml')], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
