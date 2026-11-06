"""3.2.2 validator: clean export passes; each injected defect fails its rule (negative tests)."""
import shutil
import pytest
from fixtures_pdf import make_pdf
from dossier_engine.validators.ectd32 import validate
from dossier_engine.writers.ectd32 import write, Envelope, Doc, Product, DEFAULT_PROFILE

ENV = Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['P-MAA-0001'],
               unit='initial', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg', registration='local',
               marketing='local', inn=['paracetamol'], description='Initial MAA')


@pytest.fixture(scope='module')
def clean(tmp_path_factory):
    d = tmp_path_factory.mktemp('v')
    f = str(make_pdf(d / 'a.pdf', 'x'))
    docs = [Doc('1.0', f, 'Cover letter'), Doc('1.0', f, 'Tracking table', name='tracking'), Doc('1.2.1', f, 'Application form'),
            Doc('1.3.1', f, 'SmPC', pi_type='spc', lang='en'),
            Doc('3.2.S.4.1', f, 'Specification', substance='paracetamol', manufacturer='Granules India'),
            Doc('3.2.P.1', f, 'Description and composition')]
    write(d / 'out', ENV, Product('Examplol 500 mg', 'tablet', 'Example Pharma'), docs)
    return d / 'out' / '0000'


def run(seq):
    r = validate(seq, DEFAULT_PROFILE)
    return r, {x['rule']: x['status'] for x in r['results']}


def broken(clean, tmp_path, fn):
    seq = tmp_path / '0000'
    shutil.copytree(clean, seq)
    fn(seq)
    return run(seq)


def test_clean_passes(clean):
    r, st = run(clean)
    assert r['ok'], [x for x in r['results'] if x['status'] == 'fail']
    assert r['counts']['pass'] >= 85 and 'not «EDA-valid»' in r['label']
    assert st['EG-PF-9.8'] == 'not_run'                                  # lifecycle rule: explicit, not silently passed


def _replace(p, a, b):
    p.write_text(p.read_text().replace(a, b, 1))


@pytest.mark.parametrize('rule,fn', [
    ('EG-PF-15.11', lambda s: (s / 'm1/eg/10-cover/tracking.pdf').unlink()),
    ('EG-PF-11.2', lambda s: (s / 'm1/eg/12-form/121-af/form-af.pdf').write_bytes(b'%PDF-1.4 changed %%EOF')),
    ('EG-PF-15.8', lambda s: (s / 'm3' / 'stray.pdf').write_bytes(b'%PDF-1.4\n%%EOF')),
    ('EG-PF-8.3', lambda s: (s / 'index-md5.txt').write_text('0' * 32)),
    ('EG-PF-9.4', lambda s: _replace(s / 'm1/eg/eg-regional.xml', 'code="EG-EDA"', 'code="EDA"')),
    ('EG-PF-7.3', lambda s: (s / 'index.xml').write_text('<ectd:ectd')),
    ('EG-PF-15.10', lambda s: (s / 'm5').mkdir()),
    ('EG-PF-15.9', lambda s: (s / 'notes.txt').write_text('x')),
    ('EG-PF-13.3', lambda s: _replace(s / 'm1/eg/eg-regional.xml', '<sequence>0000</sequence>', '<sequence>0001</sequence>')),
    ('EG-PF-15.6', lambda s: (s / 'm1/eg/12-form/121-af/form-af.pdf').rename(s / 'm1/eg/12-form/121-af/Form AF.pdf')),
])
def test_defect_detected(clean, tmp_path, rule, fn):
    r, st = broken(clean, tmp_path, fn)
    assert st[rule] == 'fail', (rule, [x for x in r['results'] if x['rule'] == rule])
    assert not r['ok']


def test_pdf_13_detected(clean, tmp_path):
    def f(s):
        p = s / 'm1/eg/12-form/121-af/form-af.pdf'
        p.write_bytes(p.read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1))
    r, st = broken(clean, tmp_path, f)
    assert st['EG-PF-16.1'] == 'fail' and st['EG-PF-11.2'] == 'fail'      # content changed after packaging, too
