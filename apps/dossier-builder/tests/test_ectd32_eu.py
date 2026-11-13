"""EU eCTD 3.2.2: EU Module 1 v3.1.1 on the EMA's own DTD, the folders and names of the specification, the envelopes per procedure,
the EU validation criteria v8.2 read back from disk, the lifecycle, and the export of an EU dossier through the API."""
import io, json, shutil, zipfile
import pytest
from lxml import etree
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from dossier_engine.lifecycle import plan, to_ectd32
from dossier_engine.writers.ectd32 import Doc, Product, WriterError
from dossier_engine.writers import ectd32_eu as eu
from dossier_engine.validators import ectd32_eu as veu

UUID = '0b6c2f6e-3c1a-4c55-9a40-2f7e1d5b9c11'
PROD = Product('Dermacure 500 mg', 'film-coated tablet', 'Example Pharm Co.', 'skin infections')
API = dict(substance='neomycin sulphate', manufacturer='Example API Co.')
NODES = [('1.0', 'Cover letter', {}), ('1.0', 'Tracking table', dict(name='tracking')), ('1.2', 'Application form', {}),
         ('1.2', 'Proof of payment', {}),
         ('1.3.1', 'Summary of Product Characteristics', dict(pi_type='spc', lang='en')),
         ('1.3.1', 'Package leaflet', dict(pi_type='pl', lang='en')),
         ('1.3.1', 'Fachinformation', dict(pi_type='spc', lang='de', country='DE')),
         ('1.3.2', 'Mock-up', {}), ('1.3.6', 'Braille', {}), ('1.4.1', 'Quality expert', {}), ('1.5.2', 'Generic application', {}),
         ('1.6.1', 'Environmental risk assessment', {}), ('1.8.2', 'Risk management plan', {}), ('responses', 'Responses', {}),
         ('additional-data', 'French national data', dict(country='FR')),
         ('3.2.S.4.1', 'Specification', API), ('3.2.P.1', 'Description and Composition', {}), ('3.2.R', 'Process validation scheme', {}),
         ('5.3.1.2', 'Bioequivalence study report', dict(study='EXM-BE-01'))]


def envelope(procedure='decentralised', countries=('de', 'fr'), **kw):
    return eu.EnvelopeEU(**{'identifier': UUID, 'procedure': procedure, 'countries': list(countries), 'submission_type': 'maa', 'unit': 'initial',
                            'applicant': 'Example Pharm Co.', 'invented_names': ['Dermacure'], 'inn': ['neomycin sulphate'],
                            'description': 'Initial marketing authorisation application', 'legal_basis': 'generic', **kw})


@pytest.fixture()
def docs(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    return [Doc(node=n, file=str(make_pdf(src / f'd{i}.pdf', f'{n} {t}')), title=t, doc_id=f'doc{i}', **kw) for i, (n, t, kw) in enumerate(NODES)]


def dtd_valid(base, rel):
    t = etree.parse(str(base / rel), etree.XMLParser(load_dtd=False, no_network=True))
    dtd = etree.DTD(str((base / rel).parent / t.docinfo.system_url))
    assert dtd.validate(t), dtd.error_log.filter_from_errors()
    return t.getroot()


def test_a_dcp_sequence_is_valid_on_the_ema_dtd_and_named_as_the_spec_says(tmp_path, docs):
    e = envelope()
    r = eu.write(tmp_path / 'out', e, PROD, eu.resolve(docs, e))
    base = tmp_path / 'out' / '0000'
    reg = dtd_valid(base, 'm1/eu/eu-regional.xml')
    dtd_valid(base, 'index.xml')
    files = set(r['files'])
    for f in ('m1/eu/10-cover/common/common-cover.pdf', 'm1/eu/10-cover/common/common-tracking.pdf',
              'm1/eu/12-form/common/common-form-eaf.pdf', 'm1/eu/12-form/common/common-form-eaf-2.pdf',
              'm1/eu/13-pi/131-spclabelpl/common/en/common-spc.pdf', 'm1/eu/13-pi/131-spclabelpl/common/en/common-pl.pdf',
              'm1/eu/13-pi/131-spclabelpl/de/de/de-spc.pdf', 'm1/eu/13-pi/132-mockup/common/common-mockup.pdf',
              'm1/eu/13-pi/136-braille/braille.pdf', 'm1/eu/14-expert/141-quality/quality.pdf',
              'm1/eu/15-specific/152-generic-hybrid-bio-similar/generic.pdf', 'm1/eu/16-environrisk/161-nongmo/nongmo.pdf',
              'm1/eu/18-pharmacovigilance/182-riskmgt-system/riskmgtsystem.pdf', 'm1/eu/responses/common/common-responses.pdf',
              'm1/eu/additional-data/fr/fr-additionaldata.pdf', 'util/dtd/eu-regional.dtd', 'util/style/eu-regional.xsl', 'index-md5.txt'):
        assert f in files, f
    assert any(f.startswith('m5/53-clin-stud-rep/531-rep-biopharm-stud/5312-compar-ba-be-stud-rep/exm-be-01/') for f in files)   # a study's own folder
    assert reg.get('dtd-version') == '3.1' and reg.tag == '{http://europa.eu.int}eu-backbone'
    envs = reg.findall('.//envelope')
    assert [x.get('country') for x in envs] == ['de', 'fr'] and [x.find('agency').get('code') for x in envs] == ['DE-BFARM', 'FR-ANSM']
    assert {x.findtext('identifier') for x in envs} == {UUID} and all(x.find('procedure').get('type') == 'decentralised' for x in envs)
    assert all(x.findtext('submission/procedure-tracking/number') == 'to be advised' for x in envs)
    assert all([n.text for n in x.findall('related-sequence')] == ['0000'] for x in envs)
    pi = {(p.get('{http://www.w3.org/XML/1998/namespace}lang'), p.get('type'), p.get('country')) for p in reg.iter('pi-doc')}
    assert pi == {('en', 'spc', 'common'), ('en', 'pl', 'common'), ('de', 'spc', 'de')}
    assert reg.find('.//m1-0-cover/specific').get('country') == 'common'
    assert reg.find('.//m1-additional-data/specific').get('country') == 'fr'
    idx = etree.parse(str(base / 'index.xml')).getroot()
    m1 = idx.find('m1-administrative-information-and-prescribing-information/leaf')
    assert m1.get('{http://www.w3c.org/1999/xlink}href') == 'm1/eu/eu-regional.xml'


@pytest.mark.parametrize('procedure,countries,agency,folder', [('centralised', ['ema'], 'EU-EMA', 'ema'), ('national', ['de'], 'DE-BFARM', 'de')])
def test_centralised_and_national_have_one_envelope_and_their_own_folder(tmp_path, docs, procedure, countries, agency, folder):
    e = envelope(procedure, countries)
    shared = [d for d in docs if not d.country]
    r = eu.write(tmp_path / 'out', e, PROD, eu.resolve(shared, e))
    reg = dtd_valid(tmp_path / 'out' / '0000', 'm1/eu/eu-regional.xml')
    assert [(x.get('country'), x.find('agency').get('code')) for x in reg.findall('.//envelope')] == [(countries[0], agency)]
    assert f'm1/eu/10-cover/{folder}/{folder}-tracking.pdf' in r['files']
    assert f'm1/eu/13-pi/131-spclabelpl/{folder}/en/{folder}-spc.pdf' in r['files']


def test_the_writer_refuses_what_the_specification_forbids(tmp_path, docs):
    shared = [d for d in docs if not d.country]
    cases = [
        (envelope('national', ['de']), docs, 'no envelope'),                                   # a French document in a German national procedure (VC 14.5)
        (envelope('centralised', ['de']), shared, 'one envelope, ema'),                        # VC 14.1
        (envelope('national', ['de', 'fr']), shared, 'one envelope, for its country'),         # VC 14.3
        (envelope(related_sequence=['0001']), shared, 'relates to itself'),                    # VC 14.6
    ]
    for i, (e, ds, msg) in enumerate(cases):
        with pytest.raises(WriterError, match=msg):
            eu.write(tmp_path / f'o{i}', e, PROD, eu.resolve(ds, e))
    e = envelope()
    gmo = shared + [Doc(node='1.6.2', file=shared[0].file, title='GMO', doc_id='g')]
    with pytest.raises(WriterError, match='1.6.1'):
        eu.write(tmp_path / 'gmo', e, PROD, eu.resolve(gmo, e))
    bad_pi = shared + [Doc(node='1.3.1', file=shared[0].file, title='Leaflet', pi_type='leaflet', lang='en', doc_id='x')]
    with pytest.raises(WriterError, match='PI type'):
        eu.write(tmp_path / 'pi', e, PROD, eu.resolve(bad_pi, e))
    with pytest.raises(WriterError, match='submission type'):
        eu.write(tmp_path / 'st', eu.EnvelopeEU(**{**envelope().__dict__, 'submission_type': 'new-registration'}), PROD, eu.resolve(shared, e))


def results(v):
    return {x['rule']: x for x in v['results']}


def test_the_validator_passes_the_sequence_and_says_what_it_did_not_run(tmp_path, docs):
    e = envelope()
    r = eu.write(tmp_path / 'out', e, PROD, eu.resolve(docs, e))
    v = veu.validate(r['path'], eu.DEFAULT_PROFILE, previous=[])
    assert v['ok'] and v['counts']['fail'] == 0, [x for x in v['results'] if x['status'] == 'fail']
    assert len(v['results']) == 111 and v['coverage'] == '108/111'
    res = results(v)
    assert {k for k, x in res.items() if x['status'] == 'not_run'} == {'EU-16.6', 'EU-16.7', 'EU-16.BP10'}
    assert all(res[k]['reason'] for k in ('EU-16.6', 'EU-16.7', 'EU-16.BP10'))
    for k in ('EU-3.3', 'EU-6.3', 'EU-9.4', 'EU-9.9', 'EU-14.2', 'EU-14.5', 'EU-14.6', 'EU-14.8', 'EU-15.11', 'EU-15.12', 'EU-15.BP2',
              'EU-15.BP3', 'EU-15.BP4', 'EU-15.BP5', 'EU-11.4', 'EU-10.1'):
        assert res[k]['status'] == 'pass', (k, res[k]['failures'])
    assert res['EU-14.BP6']['status'] == 'warning'                     # «to be advised»: the procedure number goes in once it is given
    assert 'Not an EMA-accepted validator' in v['label']
    # without the earlier sequences the lifecycle criteria are not run, and say so
    v0 = veu.validate(r['path'], eu.DEFAULT_PROFILE)
    assert results(v0)['EU-11.9']['status'] == 'not_run' and 'lifecycle' in results(v0)['EU-11.9']['reason']


def test_the_validator_catches_a_changed_dtd_a_stray_file_and_a_stray_folder(tmp_path, docs):
    e = envelope()
    r = eu.write(tmp_path / 'out', e, PROD, eu.resolve(docs, e))
    base = tmp_path / 'out' / '0000'
    with open(base / 'util/dtd/eu-regional.dtd', 'a', encoding='utf-8') as f:
        f.write('\n<!-- edited -->\n')
    shutil.copyfile(base / 'm1/eu/10-cover/common/common-cover.pdf', base / 'm1/eu/10-cover/common/notes.pdf')
    (base / 'm1/eu/14-expert/141-quality/extra').mkdir()
    shutil.copyfile(base / 'm1/eu/14-expert/141-quality/quality.pdf', base / 'm1/eu/14-expert/141-quality/extra/quality.pdf')
    res = results(veu.validate(r['path'], eu.DEFAULT_PROFILE, previous=[]))
    assert res['EU-3.3']['status'] == 'fail' and 'published' in res['EU-3.3']['failures'][0]
    assert res['EU-15.8']['status'] == 'fail' and 'm1/eu/10-cover/common/notes.pdf' in res['EU-15.8']['failures']
    assert res['EU-15.BP3']['status'] == 'warning' and any('notes.pdf' in f for f in res['EU-15.BP3']['failures'])
    assert res['EU-15.BP2']['status'] == 'warning' and any('141-quality/extra' in f for f in res['EU-15.BP2']['failures'])


def test_a_follow_on_replaces_the_smpc_in_its_own_country_section(tmp_path, docs):
    e = envelope()
    first = eu.resolve(docs, e)
    r0 = eu.write(tmp_path / 'lc', e, PROD, to_ectd32(plan([], first, {d.doc_id for d in first})))
    hist = [{'seq': '0000', 'leaves': r0['history']}]
    src = tmp_path / 'src'
    new_smpc = Doc(node='1.3.1', file=str(make_pdf(src / 'smpc2.pdf', 'SmPC revised')), title='SmPC (revised)', pi_type='spc', lang='en',
                   doc_id='smpc2')
    cover = Doc(node='1.0', file=str(make_pdf(src / 'cover2.pdf', 'Cover 0001')), title='Cover letter 0001', doc_id='cover2')
    track = Doc(node='1.0', file=str(make_pdf(src / 'track2.pdf', 'Tracking 0001')), title='Tracking table', name='tracking', doc_id='track2')
    current = [d for d in docs if d.doc_id not in ('doc0', 'doc1', 'doc4')] + [new_smpc, cover, track]
    e1 = envelope(unit='response', sequence='0001', related_sequence=['0000'])
    nxt = eu.resolve(current, e1)
    steps = plan(hist, nxt, {d.doc_id for d in nxt})
    assert [(s.op, s.doc.doc_id if s.doc else s.prior['doc_id']) for s in steps if s.op != 'new'] == [('replace', 'smpc2')]
    r1 = eu.write(tmp_path / 'lc', e1, PROD, to_ectd32(steps))
    reg = dtd_valid(tmp_path / 'lc' / '0001', 'm1/eu/eu-regional.xml')
    rep = [lf for lf in reg.iter('leaf') if lf.get('operation') == 'replace']
    assert len(rep) == 1 and rep[0].get('modified-file').startswith('../../../0000/m1/eu/eu-regional.xml#')
    assert rep[0].getparent().get('country') == 'common' and rep[0].getparent().get('type') == 'spc'
    v = veu.validate(r1['path'], eu.DEFAULT_PROFILE, previous=[tmp_path / 'lc' / '0000'])
    res = results(v)
    for k in ('EU-9.8', 'EU-11.9', 'EU-11.10', 'EU-11.12', 'EU-13.2', 'EU-14.7', 'EU-1.4', 'EU-3.4'):
        assert res[k]['status'] == 'pass', (k, res[k]['failures'])
    assert v['ok'], [x for x in v['results'] if x['status'] == 'fail']


# ---------------------------------------------------------------- through the API
GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin sulphate'])


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def test_an_eu_dossier_exports_an_ectd_sequence_checked_against_the_eu_criteria(c, tmp_path):
    r = c.post('/api/dossiers', json=dict(name='Dermacure', country='DE', profile={**GENERIC, 'extra': {'eu_procedure': 'dcp', 'eu_legal_basis': 'generic'}},
                                         product=PRODUCT, envelope=ENV))
    assert r.status_code == 201, r.text
    did = r.json()['id']
    au = c.get(f'/api/dossiers/{did}').json()['authority']
    assert au['outputs'] == ['ctd', 'ectd32'] and au['ectd_region'] == 'eu' and 'combined' in au['ectd_values']['pi_types']
    pdf = make_pdf(tmp_path / 'd.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] != 'R':
            continue
        meta = {'signed': True}
        if s['req_id'] == 'EU-1.3.1':
            meta |= {'pi_type': 'spc', 'lang': 'en'}
        if s['module'] == 5:
            meta |= {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'}
        up = c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                    data={'meta': json.dumps(meta)})
        assert up.status_code == 201, (s['slot_id'], up.text)
    rows = c.get(f'/api/dossiers/{did}/preview?output=ectd32').json()['rows']
    assert rows and any(x['path'] and x['path'].startswith('m1/eu/10-cover/common/common-cover') for x in rows)
    assert c.get(f'/api/dossiers/{did}/preview?output=ectd40').json()['detail']['code'] == 'E-OUTPUT-AUTHORITY'
    g = c.get(f'/api/dossiers/{did}/gate').json()
    assert g['ok'], g
    bad = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd40']})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-OUTPUT-AUTHORITY' and bad.json()['detail']['ar']
    ex = c.post(f'/api/dossiers/{did}/export', json={'submission': {'countries': ['DE', 'FR']}})      # no acknowledgement: the EU profile is the EMA's own
    assert ex.status_code == 201, ex.text
    out = ex.json()
    assert sorted(out['downloads']) == ['ctd', 'ectd32'] and 'EU Module 1 v3.1.1' in out['label']
    val = out['validation']['eCTD 3.2.2 (EU M1 3.1.1)']
    assert val['ok'], val
    z = zipfile.ZipFile(io.BytesIO(c.get(out['downloads']['ectd32']).content))
    names = z.namelist()
    assert '0000/m1/eu/eu-regional.xml' in names and '0000/m1/eu/10-cover/common/common-tracking.pdf' in names
    reg = etree.fromstring(z.read('0000/m1/eu/eu-regional.xml'))
    assert [x.get('country') for x in reg.iter('envelope')] == ['de', 'fr']
    assert {x.findtext('inn') for x in reg.iter('envelope')} == {'neomycin sulphate'}
    report = c.get(out['report']).text
    assert 'EU Module 1 v3.1.1' in report and 'Provisional EG' not in report
    subs = c.get(f'/api/dossiers/{did}/submissions').json()['ectd32']
    assert subs[0]['envelope']['countries'] == ['de', 'fr'] and subs[0]['envelope']['procedure'] == 'decentralised'


def test_the_eu_leaflet_item_asks_for_its_type_and_language(c, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Dermacure', country='FR', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    pdf = make_pdf(tmp_path / 'smpc.pdf', 'Summary of Product Characteristics').read_bytes()
    doc = c.post(f'/api/dossiers/{did}/slots/EU-1.3.2/documents', files={'file': ('smpc.pdf', io.BytesIO(pdf), 'application/pdf')},
                 data={'meta': '{}'}).json()
    assert c.post(f"/api/dossiers/{did}/documents/{doc['id']}/move", json={'slot_id': 'EU-1.3.1'}).json()['detail']['code'] == 'E-META'
    bad = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/move", json={'slot_id': 'EU-1.3.1', 'meta': {'pi_type': 'smpc', 'lang': 'en'}})
    assert bad.status_code == 422 and 'spc' in bad.json()['detail']['en']
    ok = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/move", json={'slot_id': 'EU-1.3.1', 'meta': {'pi_type': 'spc', 'lang': 'fr'}})
    assert ok.status_code == 200 and ok.json()['meta']['lang'] == 'fr'
