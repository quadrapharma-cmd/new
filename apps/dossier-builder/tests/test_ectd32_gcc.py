"""The Gulf's eCTD (updates list, item 39): GCC Module 1 v1.5 (SFDA, 2015) — its DTD (the specification's Appendix 6), its folders
and names (Appendix 2), its envelopes and codes (Appendices 1 and 5) — written and read back."""
import io, json, zipfile
import pytest
from lxml import etree
from fixtures_pdf import make_pdf
from dossier_engine.writers import ectd32_gcc as G
from dossier_engine.writers.ectd32 import Doc, Product, WriterError
from dossier_engine.validators import ectd32_gcc as V
from test_authorities import c, new                                                   # noqa: F401


def env(**k):
    return G.EnvelopeGCC(**{**dict(countries=['sa', 'ae'], application=['GCC-APP-0001'], applicant='Example Pharm Co.', submission_type='new-gen',
                                   unit='initial', procedure='gcc', invented_names=['Examplol 500 mg'], inn=['paracetamol'], atc=['N02BE01'],
                                   description='Initial application'), **k})


@pytest.fixture
def seq(tmp_path):
    f = str(make_pdf(tmp_path / 'a.pdf', 'x'))
    docs = [Doc('1.0', f, 'Cover letter', country='sa'), Doc('1.0', f, 'Cover letter', country='ae'), Doc('1.2', f, 'Application form', country='sa'),
            Doc('1.3.1', f, 'SPC', lang='en'), Doc('1.3.3', f, 'Leaflet (Arabic)', lang='ar', country='sa'), Doc('1.7.6', f, 'Pork-content declaration'),
            Doc('3.2.S.4.1', f, 'Specification', substance='paracetamol', manufacturer='Example API Co.'), Doc('3.2.P.1', f, 'Description and composition')]
    G.write(tmp_path / 'out', env(), Product('Examplol 500 mg', 'tablet', 'Example Pharm Co.'), docs)
    return tmp_path / 'out' / '0000'


def test_a_gulf_sequence_is_written_as_the_specification_says(seq):
    r = V.validate(seq)
    assert r['ok'], [x for x in r['results'] if x['status'] == 'fail']
    files = {p.relative_to(seq).as_posix() for p in seq.rglob('*') if p.is_file()}
    assert {'m1/gc/10-cover/sa/sa-cover.pdf', 'm1/gc/10-cover/ae/ae-cover.pdf', 'm1/gc/13-pi/133-leaflet/sa/ar/sa-leaflet.pdf',
            'm1/gc/17-certificates/176-pork-content/common-porkcontent.pdf', 'm1/gc/gc-regional.xml', 'util/dtd/gc-regional.dtd'} <= files
    x = etree.parse(str(seq / 'm1' / 'gc' / 'gc-regional.xml'))
    assert [(e.get('country'), e.find('agency').get('code')) for e in x.iter('envelope')] == [('sa', 'SA-SFDA'), ('ae', 'AE-MOH')]
    assert x.find('.//pi-doc').get('type') == 'spc'


def test_the_checks_catch_what_the_specification_does_not_allow(seq, tmp_path):
    reg = seq / 'm1' / 'gc' / 'gc-regional.xml'
    reg.write_text(reg.read_text().replace('country="ae">', 'country="kw">', 1).replace('<agency code="AE-MOH"/>', '<agency code="SA-SFDA"/>'))
    bad = {x['rule'] for x in V.validate(seq)['results'] if x['status'] == 'fail'}
    assert {'GCC-8', 'GCC-9'} <= bad                                                    # the wrong agency, and «ae» sections without an envelope
    with pytest.raises(WriterError):
        G.write(tmp_path / 'o2', env(submission_type='maa'), Product('x', 'tablet', 'y'), [])   # not a GCC submission type (App. 5)


def test_a_gulf_dossier_exports_its_ectd(c, tmp_path):
    did = new(c, 'SA')['id']
    pdf = make_pdf(tmp_path / 'd.pdf', 'content').read_bytes()
    assert c.get(f'/api/dossiers/{did}').json()['authority']['outputs'] == ['ctd', 'ectd32', 'nees']
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] == 'R':
            assert c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                          data={'meta': json.dumps({'signed': True})}).status_code == 201
    assert all(r['path'] for r in c.get(f'/api/dossiers/{did}/preview?output=ectd32').json()['rows'] if r.get('node'))
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd32']})
    assert r.status_code == 201, r.text
    assert r.json()['validation']['eCTD 3.2.2 (GCC M1 1.5)']['ok'], r.json()['validation']
    names = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['ectd32']).content)).namelist()
    assert '0000/m1/gc/gc-regional.xml' in names and any(n.startswith('0000/m1/gc/10-cover/sa/') for n in names)
