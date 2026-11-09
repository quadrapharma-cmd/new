import shutil
import pytest
from conftest import REPO
from fixtures_pdf import make_pdf
from dossier_engine.writers.ectd32 import Doc, Product
from dossier_engine.writers.ectd40 import write, Envelope4, Profile40
from dossier_engine.validators.ectd40 import validate

IG = REPO / 'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
ENV = Envelope4(application_uuid='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_uuid='6f1f0c0e-1d0a-4f8e-8b8c-0b9a3c2d1e01',
                tracking='P-MAA-0001', submission_type='maa', unit='initial', sequence=1, title='Initial MAA',
                applicant='Example Pharma S.A.E.', applicant_portal_id='X-1', product_name='Examplol 500 mg',
                inn=['paracetamol'], registration='local', marketing='local')


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp('v4')
    f = str(make_pdf(d / 'a.pdf', 'x'))
    docs = [Doc('1.0', f, 'Cover'), Doc('1.2.1', f, 'Application form'), Doc('1.3.1', f, 'SmPC', pi_type='spc', lang='en'),
            Doc('3.2.P.1', f, 'Description and composition')]
    write(d / 'out', ENV, Product('Examplol 500 mg', 'tablet', 'Example Pharma'), docs)
    return d / 'out' / ENV.application_uuid / '1', d


@pytest.fixture(scope='module')
def p40():
    return Profile40()


def test_clean(built, p40):
    r = validate(built[0], p40, IG, built[1])
    assert r['ok'], [x for x in r['results'] if x['status'] == 'fail']
    assert any(x['status'] == 'warning' and 'placeholder' in x['failures'][0] for x in r['results'])


@pytest.mark.parametrize('rule,fn', [
    ('eCTD4-062', lambda b: (b / 'sha256.txt').write_text('0' * 64)),
    ('eCTD4-064', lambda b: (b / 'm1/form-af.pdf').write_bytes(b'%PDF-1.4 x %%EOF')),
    ('eCTD4-069', lambda b: (b / 'm1/extra.pdf').write_bytes(b'%PDF-1.4\n%%EOF')),
    ('eCTD4-063', lambda b: (b / 'm1/cover.pdf').unlink()),
    ('EG-V4-011', lambda b: (b / 'index.xml').write_text('<x/>')),
])
def test_defects(built, p40, tmp_path, rule, fn):
    dst = tmp_path / ENV.application_uuid / '1'
    shutil.copytree(built[0], dst)
    fn(dst)
    r = validate(dst, p40, IG, built[1])
    st = {x['rule']: x['status'] for x in r['results']}
    assert st[rule] == 'fail' and not r['ok']
