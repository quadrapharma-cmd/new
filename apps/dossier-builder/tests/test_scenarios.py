"""Scenario tests: realistic profiles -> expected requirement levels."""
from datetime import date
import pytest
from dossier_engine import packs
from dossier_engine.profile import Profile, Api, ProfileError
from dossier_engine.resolver import resolve, diff, summary

TODAY = date(2026, 11, 6)


@pytest.fixture(scope='module')
def pack():
    return packs.load('eda.ctd.nta065.v5')


def lv(slots):
    return {s.slot_id: s.level for s in slots}


def seed(**kw):
    """Seed product «Examplol 500 mg FCT» — local generic, own licence, new, One Submission."""
    d = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
             dosage_specifics=['coated'], pharmacopoeial=True,
             apis=[Api('Paracetamol', 'Granules India', 'CEP'), Api('Paracetamol', 'Anqiu Lu’an', 'FULL')])
    d.update(kw)
    return Profile(**d)


def test_seed_local_generic(pack):
    s = lv(resolve(seed(), pack, today=TODAY))
    assert s['M1-01'] == 'R'
    assert s['M1-07'] == 'NA'            # variation approvals: re-registration only
    assert s['M1-10'] == 'NA'            # leaflet is English
    assert s['M1-12'] == 'R'             # G-Loc: inspection report always
    assert s['M1-14'] == 'NA'            # CPP: local own product
    assert s['M1-15'] == 'NR'            # list of countries: imported only
    assert s['M1-20'] == 'NA' and s['M1-25'] == 'NA'   # not toll
    assert s['M1-29'] == 'R'             # pharmacopoeial
    assert s['M1-33'] == 'R'             # coated -> coating premix composition
    assert s['M1-34'] == 'NA'            # rolling-only approvals
    assert s['M1-30'] == 'NA'            # no DMF
    assert s['M2-02'] == 'NR'            # QOS: innovators only
    # per-API expansion
    assert s['M1-13@Paracetamol|Granules India'] == 'R'
    assert s['M1-13@Paracetamol|Anqiu Lu’an'] == 'R'
    assert s['M1-39@Paracetamol|Granules India'] == 'R'      # CEP chosen -> mandatory
    assert 'M1-39@Paracetamol|Anqiu Lu’an' not in s           # FULL manufacturer: no CEP slot
    assert s['S-16@Paracetamol|Granules India'] == 'R'
    assert s['S-05@Paracetamol|Granules India'] == 'NR'      # covered by CEP
    assert s['S-05@Paracetamol|Anqiu Lu’an'] == 'R'
    assert s['S-10@Paracetamol|Granules India'] == 'R'       # CEP route still needs 2 batches


def test_cep_nr_is_flagged_assumption(pack):
    slot = next(x for x in resolve(seed(), pack, today=TODAY) if x.slot_id == 'S-05@Paracetamol|Granules India')
    assert 'ASSUMPTION' in slot.flags
    assert any('CEP' in r.get('en', '') for r in slot.reasons)


def test_imported_generic_reregistration(pack):
    p = seed(origin='imported', licence='imported', activity='re_registration',
             apis=[Api('Paracetamol', 'X', 'DMF')])
    s = lv(resolve(p, pack, today=TODAY))
    assert s['M1-07'] == 'R'
    assert s['M1-12'] == 'R'             # NR (new) / R (re-reg)
    assert s['M1-13'] == 'NA'   # importation approval: G-Loc only (NA recorded once, not per API)
    assert s['M1-14'] == 'R'             # CPP
    assert s['M1-15'] == 'R' and s['M1-21'] == 'R'
    assert s['M1-18'] == 'NA'            # not imported bulk
    assert s['M1-27'] == 'O'
    assert s['M1-30@Paracetamol|X'] == 'NR'  # v5 matrix: LoA NR for imported (R for G-Loc)
    assert s['M1-39'] == 'NA'


def test_imported_generic_new_inspection_not_required(pack):
    p = seed(origin='imported', licence='imported', apis=[Api('A', 'B', 'FULL')])
    assert lv(resolve(p, pack, today=TODAY))['M1-12'] == 'NR'


def test_imported_bulk(pack):
    s = lv(resolve(seed(origin='imported', licence='imported_bulk'), pack, today=TODAY))
    assert s['M1-18'] == 'R' and s['M1-27b'] == 'R'


def test_under_licence_local(pack):
    s = lv(resolve(seed(licence='under_licence'), pack, today=TODAY))
    assert s['M1-14'] == 'R' and s['M1-26'] == 'R'


def test_toll(pack):
    s = lv(resolve(seed(licence='toll'), pack, today=TODAY))
    assert s['M1-20'] == 'R' and s['M1-25'] == 'R'


def test_conditional_flags(pack):
    s = lv(resolve(seed(leaflet='non_english', store_separate_from_factory=True,
                        dosage_specifics=['powder_inj_with_solvent', 'sterile'],
                        biological_origin_materials=True, novel_excipient=True), pack, today=TODAY))
    assert s['M1-10'] == 'R' and s['M1-23'] == 'R' and s['M1-28'] == 'R'
    assert s['M1-33'] == 'NA'
    assert s['A-02'] == 'R' and s['A-03'] == 'R'


def test_rolling_before_and_after_closure(pack):
    p = seed(route='rolling')
    assert lv(resolve(p, pack, today=date(2026, 11, 30)))['M1-34'] == 'R'
    with pytest.raises(ProfileError) as e:
        resolve(p, pack, today=date(2026, 12, 1))
    assert e.value.problems[0]['code'] == 'P-ROLLING-CLOSED'


def test_innovator_imported_full_modules(pack):
    p = seed(dossier_kind='innovator', origin='imported', licence='imported')
    s = lv(resolve(p, pack, today=TODAY))
    assert s['M2-02'] == 'R' and s['M4-01'] == 'R' and s['M5-12'] == 'R'


def test_local_innovator_flagged(pack):
    slots = resolve(seed(dossier_kind='innovator'), pack, today=TODAY)
    assert all('ASSUMPTION_LOCAL_INNOVATOR' in s.flags for s in slots)


def test_confirm_applicability(pack):
    slot = next(x for x in resolve(seed(), pack, today=TODAY) if x.slot_id == 'M5-07')
    assert slot.level == 'R' and 'CONFIRM_APPLICABILITY' in slot.flags


@pytest.mark.parametrize('kw,code', [
    (dict(licence='imported_bulk'), 'P-CONTRA'),
    (dict(origin='imported', licence='toll'), 'P-CONTRA'),
    (dict(biological=True), 'P-UNSUPPORTED'),
    (dict(apis=[]), 'P-NO-API'),
    (dict(apis=[Api('A', 'B'), Api('A', 'B')]), 'P-DUP-API'),
    (dict(activity='renewel'), 'P-ENUM'),
    (dict(apis=[Api('A', 'B', 'ASMF')]), 'P-ENUM'),
])
def test_profile_contradictions(pack, kw, code):
    with pytest.raises(ProfileError) as e:
        resolve(seed(**kw), pack, today=TODAY)
    assert code in [p['code'] for p in e.value.problems]
    assert all(p['ar'] for p in e.value.problems)     # bilingual messages


def test_every_na_and_nr_explains_why(pack):
    for s in resolve(seed(), pack, today=TODAY):
        assert s.reasons and s.reasons[0]['en'] and s.reasons[0]['source']


def test_diff_on_profile_change(pack):
    a = resolve(seed(), pack, today=TODAY)
    b = resolve(seed(licence='toll', activity='re_registration'), pack, today=TODAY)
    d = diff(a, b)
    assert {'M1-07', 'M1-20', 'M1-25', 'M1-27'} <= set(d['added'])
    assert d['removed'] == []


def test_summary_counts(pack):
    slots = resolve(seed(), pack, today=TODAY)
    c = summary(slots)
    assert sum(c.values()) == len(slots) and c['R'] > 50


def test_dmf_letter_of_access_local(pack):
    s = lv(resolve(seed(apis=[Api('A', 'B', 'DMF')]), pack, today=TODAY))
    assert s['M1-30@A|B'] == 'R'
