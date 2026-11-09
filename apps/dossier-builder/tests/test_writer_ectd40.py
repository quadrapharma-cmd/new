"""Writer 3 (eCTD 4.0): XSD-valid submission unit, SHA-256, CoU + keywords, EG rules."""
import hashlib, shutil, subprocess, zipfile
from datetime import date
import pytest
from conftest import REPO
from fixtures_pdf import make_pdf
from dossier_engine.writers.ectd32 import Doc, Product, WriterError
from dossier_engine.writers.ectd40 import write, Envelope4

XMLLINT = shutil.which('xmllint')
IG_ZIP = REPO / 'docs' / 'ctd' / 'sources' / 'ectd' / 'ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip'
NS = {'h': 'urn:hl7-org:v3'}
ENV = Envelope4(application_uuid='0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11', submission_uuid='6f1f0c0e-1d0a-4f8e-8b8c-0b9a3c2d1e01',
                tracking='P-MAA-0001', submission_type='maa', unit='initial', sequence=1,
                title='Initial MAA for Examplol 500 mg film-coated tablets', applicant='Example Pharma S.A.E.',
                applicant_portal_id='EXAMPLE-0001', product_name='Examplol 500 mg film-coated tablets',
                inn=['paracetamol'], registration='local', marketing='local')
PROD = Product('Examplol 500 mg', 'film-coated tablet', 'Example Pharma', indication='pain-and-fever')
API = dict(substance='paracetamol', manufacturer='Granules India')


@pytest.fixture(scope='module')
def xsd(tmp_path_factory):
    d = tmp_path_factory.mktemp('xsd')
    with zipfile.ZipFile(IG_ZIP) as z:
        z.extractall(d)
    hits = list(d.rglob('PORP_IN000001UV.xsd'))
    if not hits:                      # nested zip
        for inner in d.rglob('*.zip'):
            with zipfile.ZipFile(inner) as z:
                z.extractall(inner.parent)
        hits = list(d.rglob('PORP_IN000001UV.xsd'))
    return hits[0]


def build(tmp_path, nodes, env=ENV):
    src = tmp_path / 'src'
    src.mkdir(parents=True, exist_ok=True)
    docs = []
    for i, (node, title, kw) in enumerate(nodes):
        docs.append(Doc(node=node, file=str(make_pdf(src / f'd{i}.pdf', f'{node} {title}')), title=title, **kw))
    return write(tmp_path / 'out', env, PROD, docs)


NODES = [('1.0', 'Cover Letter', {}), ('1.2.1', 'Application Form', {}), ('1.2.2.3', 'GMP – FPP', {}),
         ('1.2.2.3', 'GMP – API', {}), ('1.3.1', 'SmPC (English)', dict(pi_type='spc', lang='en')),
         ('1.3.1', 'النشرة الداخلية', dict(pi_type='pl', lang='ar')),
         ('3.2.S.1.1', 'Nomenclature', API), ('3.2.S.4.1', 'Specification', API),
         ('3.2.P.1', 'Description and Composition', {}), ('3.2.R', 'CEP', {}),
         ('5.3.1.2', 'BE study EXM-BE-01', dict(study='EXM-BE-01 Bioequivalence of Examplol 500 mg', doc_type='ich_document_type_2'))]


@pytest.mark.skipif(not XMLLINT, reason='xmllint not installed')
def test_xsd_valid_and_hashes(tmp_path, xsd):
    rep = build(tmp_path, NODES)
    base = tmp_path / 'out' / ENV.application_uuid / '1'
    r = subprocess.run([XMLLINT, '--noout', '--schema', str(xsd), str(base / 'submissionunit.xml')],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:3000]
    assert (base / 'sha256.txt').read_text() == hashlib.sha256((base / 'submissionunit.xml').read_bytes()).hexdigest()
    from lxml import etree
    t = etree.parse(str(base / 'submissionunit.xml'))
    refs = t.xpath('//h:document/h:text', namespaces=NS)
    assert len(refs) == len(NODES)
    for tx in refs:
        ref = tx.find('h:reference', NS).get('value')
        assert hashlib.sha256((base / ref).read_bytes()).hexdigest() == tx.find('h:integrityCheck', NS).text
    # every document is used by exactly one CoU; every file is referenced (eCTD4-069)
    doc_ids = {d.get('root') for d in t.xpath('//h:document/h:id', namespaces=NS)}
    used = {d.get('root') for d in t.xpath('//h:contextOfUse/h:derivedFrom//h:id', namespaces=NS)}
    assert doc_ids == used
    content = {f for f in rep['files'] if f.startswith('m')}
    assert content == {tx.find('h:reference', NS).get('value') for tx in refs}


def test_layout_and_codes(tmp_path):
    rep = build(tmp_path, NODES)
    f = set(rep['files'])
    assert {'m1/cover.pdf', 'm1/form-af.pdf', 'm1/gmpcert.pdf', 'm1/gmpcert-2.pdf', 'm1/spc-en.pdf', 'm1/pl-ar.pdf'} <= f
    assert not any(x.startswith(('util', 'm1/eg')) or x.endswith(('index.xml', 'md5.txt')) for x in f)   # EG-V4-007/011
    xml = (tmp_path / 'out' / ENV.application_uuid / '1' / 'submissionunit.xml').read_text()
    assert 'code="ich_3.2.s.1"' in xml                     # 3.2.S.1.1 -> v4 merges S.1 subsections
    assert 'code="eg_1.3.1"' in xml and 'code="eg_st_maa"' in xml and 'extension="EG-EDA"' in xml
    assert 'language="ar"' in xml
    assert 'displayName value="Granules India"' in xml     # sender-defined keyword
    assert xml.count('<keywordDefinition>') == rep['keyword_definitions'] >= 4


def test_required_keyword_missing(tmp_path):
    with pytest.raises(WriterError, match='eCTD4-070'):
        build(tmp_path, [('1.0', 'Cover', {}), ('5.3.1.2', 'BE', {})])
    with pytest.raises(WriterError, match='eCTD4-070'):      # study id given, document type missing
        build(tmp_path / 'b', [('5.3.1.2', 'BE', dict(study='EXM-BE-01'))])


def test_folder_only_heading_refused(tmp_path):
    with pytest.raises(WriterError, match='EG-V4-022'):
        build(tmp_path, [('1.2.2', 'Legal', {})])


def test_vocab_checks(tmp_path):
    from dataclasses import replace
    for bad in (dict(submission_type='var-pac-II'), dict(unit='consolidating'), dict(registration='own'), dict(sequence=0)):
        with pytest.raises(WriterError):
            build(tmp_path / str(len(str(bad))), NODES[:1], env=replace(ENV, **bad))


def test_document_uuid_reuse(tmp_path):
    """Same document across sequences keeps its UUID (lifecycle / FC reuse)."""
    from dataclasses import replace
    build(tmp_path, NODES[:2])
    build(tmp_path, NODES[:2], env=replace(ENV, sequence=2, unit='response'))
    a = (tmp_path / 'out' / ENV.application_uuid / '1' / 'submissionunit.xml').read_text()
    b = (tmp_path / 'out' / ENV.application_uuid / '2' / 'submissionunit.xml').read_text()
    import re
    ids = lambda x: re.findall(r'<document>\s*<id root="([^"]+)"', x)
    assert ids(a) == ids(b)
