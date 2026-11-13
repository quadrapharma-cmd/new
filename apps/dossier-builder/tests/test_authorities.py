"""A dossier is built for a country: Module 1 is the chosen authority's own (its structure, numbering and contents from the text it
published), Modules 2 to 5 are the common CTD. Egypt stays as it was; the Gulf (GCC / SFDA), the European Union and the United
States have their Module 1; any other country gets a general Module 1 that says so on every item."""
import io, json
import pytest
from docx import Document
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine import packs, extract
from dossier_engine.app.api import create_app
from dossier_engine.classify import Classifier
from dossier_engine.generate import draft as _draft
from dossier_engine.profile import Profile, ProfileError
from dossier_engine.resolver import resolve

GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin'])
PACKS = ['eda.ctd.nta065.v5', 'gcc.ctd.m1.v1', 'eu.ctd.m1.v1', 'us.ctd.m1.v1', 'intl.ctd.m1.v1']


def slots_of(pack_id, **over):
    prof = Profile.from_dict({**GENERIC, **over})
    return {s.slot_id: s for s in resolve(prof, packs.load(pack_id))}


# ---------------- the packs
@pytest.mark.parametrize('pid', PACKS + ['ich.ctd.m4.v1'])
def test_every_pack_is_clean(pid):
    assert packs.lint(packs.load(pid)) == []


def test_egypt_is_untouched_and_offered_first():
    eg = packs.load('eda.ctd.nta065.v5')
    assert len(eg.requirements) == 101 and eg.egypt and eg.base is None
    offered = [m['id'] for m in packs.available()]
    assert offered[0] == 'eda.ctd.nta065.v5' and offered[-1] == 'intl.ctd.m1.v1'
    assert 'ich.ctd.m4.v1' not in offered                                   # the common CTD is what the others stand on, not a choice


def test_a_country_picks_its_authority():
    want = {'EG': 'eda', 'SA': 'gcc', 'AE': 'gcc', 'KW': 'gcc', 'BH': 'gcc', 'OM': 'gcc', 'QA': 'gcc', 'YE': 'gcc', 'DE': 'eu', 'FR': 'eu', 'NO': 'eu', 'US': 'us',
            'JO': 'intl', 'NG': 'intl', 'IN': 'intl'}
    for code, start in want.items():
        assert packs.for_country(code)['id'].startswith(start + '.'), code
    assert packs.for_country('sa')['id'] == 'gcc.ctd.m1.v1'                 # however it is written


def test_module_1_is_the_authoritys_and_modules_2_to_5_are_common():
    base = {r['id'] for r in packs.load('ich.ctd.m4.v1').requirements}
    for pid in PACKS[1:]:
        pk = packs.load(pid)
        m1 = [r for r in pk.requirements if r['module'] == 1]
        assert m1 and not {r['id'] for r in m1} & base
        assert base <= {r['id'] for r in pk.requirements}                    # nothing of the common CTD is lost
        assert [r['module'] for r in pk.requirements] == sorted(r['module'] for r in pk.requirements)
    gcc = packs.load('gcc.ctd.m1.v1')
    assert [packs.number(r) for r in gcc.requirements if r['module'] == 1][:6] == ['1.0', '1.1', '1.2', '1.3.1', '1.3.2', '1.3.3.1']
    us = {packs.number(r): r for r in packs.load('us.ctd.m1.v1').requirements}
    assert us['1.1.2']['title']['en'] == 'Application form: FDA form 356h' and us['1.12.11']['title']['en'] == 'ANDA basis for submission statement'
    eu = {packs.number(r): r for r in packs.load('eu.ctd.m1.v1').requirements if r['module'] == 1}
    assert eu['1.3.6']['title']['en'] == 'Braille' and eu['1.8.2']['title']['en'] == 'Risk-management system'


def test_each_item_names_its_source():
    for pid in PACKS[1:]:
        for r in packs.load(pid).requirements:
            assert r['sources'] and r['title']['en'] and r['title']['ar'], r['id']
    gcc = packs.load('gcc.ctd.m1.v1').by_id
    assert 'SFDA Data Requirements for Human Drugs Submission v4.0' in gcc['GCC-1.7.5']['sources'][0]
    assert all(r.get('level_note') for r in packs.load('intl.ctd.m1.v1').requirements if r['module'] == 1)      # the general Module 1 says it is general, item by item


# ---------------- what a product needs, per authority
def test_gulf_levels_follow_the_receiving_authority():
    sa, kw = slots_of('gcc.ctd.m1.v1', extra={'gcc_agency': 'SA'}), slots_of('gcc.ctd.m1.v1', extra={'gcc_agency': 'KW'})
    assert sa['GCC-1.7.2'].level == 'O' and 'optional' in sa['GCC-1.7.2'].reasons[1]['en']         # SFDA v4.0: the CPP is no longer required for new applications
    assert kw['GCC-1.7.2'].level == 'R' and 'CONFIRM_LEVEL' in kw['GCC-1.7.2'].flags and 'CONFIRM_LEVEL' not in sa['GCC-1.7.2'].flags
    # the contents are SFDA's: outside Saudi Arabia every Module 1 item says to check the authority's own guidance; in Saudi Arabia only the
    # items whose level the SFDA text does not state
    noted = lambda sl: {k for k, s in sl.items() if s.active and s.module == 1 and any(r.get('note') for r in s.reasons)}
    assert noted(kw) == {k for k, s in kw.items() if s.active and s.module == 1} and 'SFDA' in kw['GCC-1.7.5'].reasons[-1]['en']
    assert noted(sa) == {'GCC-1.4.2', 'GCC-1.4.3', 'GCC-1.5.1', 'GCC-1.6.2'}
    assert 'Generic products' in sa['M2-NCO'].reasons[0]['source'] and not any(r.get('note') for r in sa['M2-CO'].reasons)      # SFDA says which Module 2 sections a generic holds
    assert sa['GCC-1.7.5'].level == sa['GCC-1.7.6'].level == 'R'                                   # alcohol and pork declarations
    assert sa['GCC-1.7.10@Neomycin sulphate|Example API Co.'].level == 'R'                         # the letter of access, per active substance
    local = slots_of('gcc.ctd.m1.v1', origin='local', extra={'gcc_agency': 'SA'})
    assert local['GCC-1.7.2'].level == 'NR'                                                        # made in the country: no country of origin to certify it
    assert sa['M2-NCO'].level == 'NR' and sa['M2-CO'].level == 'R' and sa['M2-02'].level == 'R'     # SFDA, generics: 2.3 and 2.5, not 2.4


def test_europe_follows_the_legal_basis():
    g = slots_of('eu.ctd.m1.v1')                                              # generic, Art. 10(1): the default
    assert g['EU-1.5.2'].level == 'R' and g['EU-1.5.1'].level == 'NA' and g['EU-1.10'].level == 'NA'
    full = slots_of('eu.ctd.m1.v1', dossier_kind='innovator', extra={'eu_legal_basis': 'full', 'eu_procedure': 'cp'})
    assert full['EU-1.10'].level == 'R' and full['EU-1.5.2'].level == 'NA' and full['EU-1.5.5'].level == 'O' and full['EU-1.3.5'].level == 'NA'
    weu = slots_of('eu.ctd.m1.v1', extra={'eu_legal_basis': 'weu'})
    assert weu['EU-1.5.1'].level == 'R'


def test_united_states_follows_the_application():
    anda = slots_of('us.ctd.m1.v1')
    assert anda['US-1.1.2'].level == 'R' and anda['US-1.1.1'].level == 'NA' and anda['US-1.12.11'].level == 'R' and anda['US-1.14.3.1'].level == 'R'
    assert anda['US-1.4.1@Neomycin sulphate|Example API Co.'].level == 'R' and anda['US-3.2.R-EBR'].level == 'R'
    ind = slots_of('us.ctd.m1.v1', dossier_kind='innovator', extra={'us_application': 'ind'})
    assert ind['US-1.1.1'].level == 'R' and ind['US-1.1.2'].level == 'NA' and ind['US-1.20'].level == 'R' and ind['US-1.12.11'].level == 'NA'


def test_an_answer_the_authority_does_not_offer_is_refused_and_egypts_rules_stay_egypts():
    with pytest.raises(ProfileError) as e:
        Profile.from_dict({**GENERIC, 'extra': {'eu_legal_basis': 'whatever'}}).validate(pack=packs.load('eu.ctd.m1.v1'))
    assert e.value.problems[0]['code'] == 'P-ENUM'
    odd = Profile.from_dict({**GENERIC, 'origin': 'imported', 'licence': 'toll'})                  # a contradiction in Egypt's licence kinds only
    with pytest.raises(ProfileError):
        odd.validate(pack=packs.load('eda.ctd.nta065.v5'))
    assert odd.validate(pack=packs.load('gcc.ctd.m1.v1'))


# ---------------- placing documents: the kind's home and the keywords, per authority
def test_a_documents_kind_finds_its_place_in_each_authority():
    gcc, eg, us = packs.load('gcc.ctd.m1.v1'), packs.load('eda.ctd.nta065.v5'), packs.load('us.ctd.m1.v1')
    assert extract.kind_homes('gmp', gcc) == ['GCC-1.7.1'] and extract.kind_homes('cpp', gcc) == ['GCC-1.7.2']
    assert extract.kind_homes('coa', gcc) == ['GCC-1.7.3', 'S-10', 'P-11'] and extract.kind_homes('licence', gcc) == []
    assert extract.kind_homes('gmp', eg) == ['M1-37', 'M1-38'] == extract.kind_homes('gmp')         # Egypt as it was
    assert extract.kind_homes('bmr', us) == ['US-3.2.R-EBR']
    slots = list(slots_of('gcc.ctd.m1.v1').values())
    c = Classifier(gcc)
    top = lambda name, text='': c.suggest(name, text, slots)[0]['slot_id']
    assert top('x.pdf', 'alcohol free declaration') == 'GCC-1.7.5' and top('y.pdf', '1.3.1 SPC summary of product characteristics') == 'GCC-1.3.1'
    assert top('report.pdf', 'stability study protocol and report') == 'P-16'                       # the common CTD's keywords come along


# ---------------- the program, through its API
@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def new(c, country, **profile):
    r = c.post('/api/dossiers', json=dict(name='Dermacure', country=country, profile={**GENERIC, **profile}, product=PRODUCT, envelope=ENV))
    assert r.status_code == 201, r.text
    return r.json()


def test_the_authorities_are_listed_for_the_wizard(c):
    r = c.get('/api/authorities').json()
    by = {a['id']: a for a in r['authorities']}
    assert list(by) == ['EG-EDA', 'GCC', 'EU', 'US-FDA', 'OTHER'] and r['default'] == 'intl.ctd.m1.v1'
    assert by['GCC']['verified'] and not by['OTHER']['verified'] and by['EG-EDA']['outputs'] == ['ctd', 'ectd32', 'ectd40'] and by['GCC']['outputs'] == ['ctd', 'nees']
    assert [q['id'] for q in by['EU']['questions']] == ['eu_legal_basis', 'eu_procedure'] and by['US-FDA']['questions'][0]['default'] == 'anda'
    assert by['GCC']['sources'][1]['version'] == '4.0' and by['GCC']['requirements']['by_module']['1'] == 30
    assert {x['code'] for x in r['countries']} >= {'EG', 'SA', 'DE', 'US', 'JO'}
    caps = c.get('/api/capabilities').json()
    assert len(caps['authorities']) == 5 and caps['pack']['id'] == 'eda.ctd.nta065.v5'


def test_a_dossier_is_created_for_its_country(c):
    sa = new(c, 'SA')
    assert sa['pack'] == 'gcc.ctd.m1.v1'
    d = c.get(f"/api/dossiers/{sa['id']}").json()
    assert d['authority']['id'] == 'GCC' and d['authority']['country'] == 'SA' and d['authority']['country_name']['en'] == 'Saudi Arabia'
    assert d['authority']['outputs'] == ['ctd', 'nees'] and not d['authority']['egypt'] and d['envelope']['country'] == 'SA'
    board = {s['slot_id']: s for s in c.get(f"/api/dossiers/{sa['id']}/board").json()['slots']}
    assert board['GCC-1.0']['ctd'] == '1.0' and board['GCC-1.7.6']['level'] == 'R' and 'M1-01' not in board and 'P-01' in board
    assert board['GCC-1.4.2']['note']['ar'] and any(r.get('note') for r in board['GCC-1.4.2']['reasons'])        # where the level comes from, said with the item
    assert new(c, 'DE')['pack'] == 'eu.ctd.m1.v1' and new(c, 'US')['pack'] == 'us.ctd.m1.v1' and new(c, 'JO')['pack'] == 'intl.ctd.m1.v1'
    eg = c.post('/api/dossiers', json=dict(name='x', profile={**GENERIC, 'origin': 'local'}, product=PRODUCT, envelope=ENV)).json()
    assert eg['pack'] == 'eda.ctd.nta065.v5'                                 # no country named: Egypt, as before
    rows = {x['id']: x for x in c.get('/api/dossiers').json()}
    assert rows[sa['id']]['authority'] == {'id': 'GCC', 'name': d['authority']['name'], 'country': 'SA'} and rows[eg['id']]['authority']['id'] == 'EG-EDA'
    bad = c.post('/api/dossiers', json=dict(name='x', pack='ich.ctd.m4.v1', profile=GENERIC, product=PRODUCT))
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-PACK'


def test_the_preview_is_the_countrys_own_list(c):
    p = c.post('/api/profile/preview?country=SA', json={**GENERIC, 'extra': {'gcc_agency': 'SA'}}).json()
    assert p['authority']['id'] == 'GCC' and p['by_module']['1']['R'] >= 15 and not p['column_assumed']
    assert next(s for s in p['slots'] if s['req_id'] == 'GCC-1.7.2')['level'] == 'O'
    eg = c.post('/api/profile/preview', json={**GENERIC, 'origin': 'local'}).json()
    assert eg['authority']['egypt'] and any(s['req_id'] == 'M1-01' for s in eg['slots'])
    bad = c.post('/api/profile/preview?country=DE', json={**GENERIC, 'extra': {'eu_procedure': 'x'}})
    assert bad.status_code == 422


def test_templates_and_make_it_for_me_work_for_any_authority(c, monkeypatch):
    did = new(c, 'SA')['id']
    v = c.get(f'/api/dossiers/{did}/slots/GCC-1.7.5/template').json()                               # the alcohol-content declaration
    assert v['template']['draft'] == 'full' and v['template']['kind'] == 'letter' and v['template']['letterhead']
    assert [s['id'] for s in v['template']['sections']] == ['addressee', 'subject', 'body', 'enclosures', 'signature']
    assert 'free from alcohol' in v['template']['sections'][2]['hint']['en']                        # what the authority asks the declaration to say
    assert 'GCC' in v['prompt'].splitlines()[0] and 'Egyptian' not in v['prompt'] and 'EDA' not in v['prompt'].split('TEMPLATE')[0]
    assert c.get(f'/api/dossiers/{did}/slots/GCC-1.7.1/template').json()['template']['draft'] == 'none'      # a certificate is uploaded, never typed
    seen = {}
    monkeypatch.setattr(_draft, 'ASK', lambda prompt: seen.update(p=prompt) or {'sections': {'body': 'We declare that Dermacure is free from alcohol.'}, 'gaps': []})
    monkeypatch.setattr(_draft, '_server_key', lambda st: 'k')
    r = c.post(f'/api/dossiers/{did}/slots/GCC-1.7.5/draft', json={'lang': 'en'})
    assert r.status_code == 201, r.text
    doc = r.json()['document']
    blob = c.get(f"/api/dossiers/{did}/documents/{doc['id']}/file").content
    text = '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)
    assert 'free from alcohol' in text and 'Alcohol-content declaration' in text and 'Saudi Arabia' in seen['p'] or 'SA' in seen['p']
    jo = new(c, 'JO')['id']
    assert 'general practice' in c.get(f'/api/dossiers/{jo}/slots/X-1.0/template').json()['prompt']          # the model is told the Module 1 is a general layout


def test_a_file_goes_to_its_place_and_a_wrong_kind_is_caught(c, tmp_path):
    did = new(c, 'SA')['id']
    gmp = make_pdf(tmp_path / 'g.pdf', 'CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER\nThe competent authority confirms the manufacturer Example Pharm Co. '
                                         'complies with Good Manufacturing Practice. Certificate No: GMP/2026/0042').read_bytes()
    s = c.post(f'/api/dossiers/{did}/classify', files={'files': ('scan-001.pdf', io.BytesIO(gmp), 'application/pdf')}).json()[0]
    assert s['kind'] == 'gmp' and s['suggestions'][0]['slot_id'] == 'GCC-1.7.1' and s['auto'] == 'GCC-1.7.1', s
    r = c.post(f'/api/dossiers/{did}/slots/GCC-1.7.2/documents', files={'file': ('scan-001.pdf', io.BytesIO(gmp), 'application/pdf')}, data={'meta': '{}'})
    assert r.status_code == 201, r.text
    kind = next(f for f in r.json()['findings'] if f['rule'] == 'DOC-KIND')
    assert kind['action'] == 'move' and kind['extra']['suggested_slot'] == 'GCC-1.7.1'             # a GMP certificate in the CPP item: sent to its own


def test_other_countries_export_ctd_folders_and_egypt_keeps_its_ectd(c, tmp_path):
    did = new(c, 'JO')['id']
    pdf = make_pdf(tmp_path / 'd.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] == 'R':
            r = c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')}, data={'meta': json.dumps({'signed': True})})
            assert r.status_code == 201, r.text
    assert c.get(f'/api/dossiers/{did}/preview?output=ectd32').json()['detail']['code'] == 'E-OUTPUT-AUTHORITY'
    rows = c.get(f'/api/dossiers/{did}/preview?output=ctd').json()['rows']
    assert any(x['path'].split('/')[1] == 'Module 1' and ' 1.0 Cover letter' in x['path'] for x in rows)
    g = c.get(f'/api/dossiers/{did}/gate').json()
    assert g['ok'], g
    if g['ok']:
        r = c.post(f'/api/dossiers/{did}/export', json={})                                          # nothing asked: what this authority has
        assert r.status_code == 201, r.text
        assert sorted(r.json()['downloads']) == ['ctd', 'nees'] and 'EDA' not in r.json()['label']
        import zipfile
        nz = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['nees']).content))
        assert '0000/ctd-toc.pdf' in nz.namelist() and r.json()['validation']['NeeS']['ok'], r.json()['validation']
        z = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['ctd']).content))
        names = z.namelist()
        assert any('/Module 1/' in n and '1.0 Cover letter' in n for n in names) and any('/Module 3/' in n for n in names) and any(n.endswith('00-checklist.csv') for n in names)
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd32'], 'acknowledge_provisional': True})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-OUTPUT-AUTHORITY' and r.json()['detail']['ar']
