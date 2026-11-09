"""Writer 2 (eCTD 3.2.2): the seed dossier exports to a DTD-valid sequence 0000."""
import hashlib, shutil, subprocess
import pytest
from fixtures_pdf import make_pdf
from dossier_engine.writers.ectd32 import write, Envelope, Doc, Product, WriterError, REG_TYPE

XMLLINT = shutil.which('xmllint')

ENV = Envelope(identifier='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_type='maa', tracking=['P-MAA-0001'],
               unit='initial', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg film-coated tablets',
               registration=REG_TYPE['own'], marketing='local', inn=['paracetamol'],
               description='Initial MAA for Examplol 500 mg film-coated tablets')
PROD = Product('Examplol 500 mg', 'film-coated tablet', 'Example Pharma, 6th of October City, Egypt')
API = dict(substance='paracetamol', manufacturer='Granules India')

NODES = [
    ('1.0', 'Cover Letter', {}), ('1.2.1', 'Application Form (Annex I)', {}), ('1.2.11', 'Proof of Payment', {}),
    ('1.2.2.1', 'Letter of Attorney', {}), ('1.2.2.3', 'GMP Certificate – FPP manufacturer', {}),
    ('1.2.2.3', 'GMP Certificate – Granules India', {}), ('1.2.3.8', 'Pricing Certificate', {}),
    ('1.2.8.1', 'Composition Certificate', {}), ('1.2.9', 'API Certificate of Analysis', {}),
    ('1.3.1', 'Summary of Product Characteristics (English)', dict(pi_type='spc', lang='en')),
    ('1.3.1', 'النشرة الداخلية', dict(pi_type='pl', lang='ar')),
    ('3.2.S', 'Statement of S-part option (CEP)', API), ('3.2.S.1.3', 'General Properties', API),
    ('3.2.S.4.1', 'Specification', API), ('3.2.S.4.4', 'Batch Analyses', API),
    ('3.2.P.1', 'Description and Composition', {}), ('3.2.P.3.3', 'Manufacturing Process', {}),
    ('3.2.P.4', 'Control of Excipients', {}), ('3.2.P.8.1', 'Stability Summary and Conclusions', {}),
    ('3.2.R', 'Certificate of Suitability (CEP)', {}), ('3.2.R', 'Executed Batch Records – BE batch', {}),
    ('5.3.1.2', 'Bioequivalence Study Report', {}), ('5.2', 'Tabular Listing of Clinical Studies', {}),
]


@pytest.fixture()
def seq(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    docs = []
    for i, (node, title, kw) in enumerate(NODES):
        f = make_pdf(src / f'd{i}.pdf', f'{node} {title}')
        docs.append(Doc(node=node, file=str(f), title=title, **kw))
    rep = write(tmp_path / 'out', ENV, PROD, docs)
    return tmp_path / 'out' / '0000', rep


@pytest.mark.skipif(not XMLLINT, reason='xmllint not installed')
def test_dtd_valid(seq):
    base, _ = seq
    for f in ('index.xml', 'm1/eg/eg-regional.xml'):
        r = subprocess.run([XMLLINT, '--noout', '--valid', str(base / f)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_checksums(seq):
    base, _ = seq
    assert (base / 'index-md5.txt').read_text() == hashlib.md5((base / 'index.xml').read_bytes()).hexdigest()
    from lxml import etree
    for xml, prefix in (('index.xml', ''), ('m1/eg/eg-regional.xml', 'm1/eg/')):
        t = etree.parse(str(base / xml))
        leaves = t.xpath('//leaf')
        assert leaves
        for lf in leaves:
            href = lf.get('{http://www.w3c.org/1999/xlink}href')
            assert hashlib.md5((base / (prefix + href)).read_bytes()).hexdigest() == lf.get('checksum')


def test_no_unreferenced_files(seq):
    base, rep = seq
    from lxml import etree
    refs = set()
    for xml, prefix in (('index.xml', ''), ('m1/eg/eg-regional.xml', 'm1/eg/')):
        for lf in etree.parse(str(base / xml)).xpath('//leaf'):
            refs.add(prefix + lf.get('{http://www.w3c.org/1999/xlink}href'))
    content = {f for f in rep['files'] if f.startswith(('m1/', 'm2/', 'm3/', 'm4/', 'm5/'))}
    assert content == refs


def test_layout(seq):
    base, rep = seq
    f = set(rep['files'])
    assert 'm1/eg/10-cover/cover.pdf' in f
    assert 'm1/eg/12-form/121-af/form-af.pdf' in f
    assert 'm1/eg/13-pi/131-spclabelpl/ar/pl.pdf' in f
    assert 'm1/eg/12-form/122-legal/1223-gmpcert/gmpcert-2.pdf' in f       # second doc in one heading
    assert any(x.startswith('m3/32-body-data/32s-drug-sub/paracetamol-granules-india/') for x in f)
    assert any(x.startswith('m3/32-body-data/32p-drug-prod/examplol-500-mg/') for x in f)
    assert {'util/dtd/eg-regional.dtd', 'util/dtd/ich-ectd-3-2.dtd', 'util/style/eg-regional.xsl'} <= f
    for x in f:
        assert len('0000/' + x) <= 180 and all(len(p) <= 64 for p in x.split('/'))
        assert x == x.lower()


def test_m3_attributes(seq):
    base, _ = seq
    t = (base / 'index.xml').read_text()
    assert 'substance="paracetamol" manufacturer="Granules India"' in t
    assert 'product-name="Examplol 500 mg" dosageform="film-coated tablet"' in t


def test_never_overwrites(seq, tmp_path):
    with pytest.raises(WriterError, match='never overwritten'):
        write(tmp_path / 'out', ENV, PROD, [])


def test_cover_letter_mandatory(tmp_path):
    f = make_pdf(tmp_path / 'a.pdf', 'x')
    with pytest.raises(WriterError, match='cover letter'):
        write(tmp_path / 'o', ENV, PROD, [Doc('1.2.1', str(f), 'AF')])


def test_rejects_folder_only_heading(tmp_path):
    f = make_pdf(tmp_path / 'a.pdf', 'x')
    with pytest.raises(WriterError, match='not a document heading'):
        write(tmp_path / 'o', ENV, PROD, [Doc('1.2.2', str(f), 'Legal')])


def test_path_limit(tmp_path):
    f = make_pdf(tmp_path / 'a.pdf', 'x')
    docs = [Doc('1.0', str(f), 'Cover'), Doc('3.2.S.2.2', str(f), 'Process', substance='a' * 20,
                                          manufacturer='b' * 20, name='c' * 70)]
    with pytest.raises(WriterError, match='EG-PF-15.4'):
        write(tmp_path / 'o', ENV, PROD, docs)


def test_indication_required(tmp_path):
    f = make_pdf(tmp_path / 'a.pdf', 'x')
    with pytest.raises(WriterError, match='indication'):
        write(tmp_path / 'o', ENV, PROD, [Doc('1.0', str(f), 'Cover'), Doc('5.3.5.4', str(f), 'Dissolution')])
