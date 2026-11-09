"""Biowaiver logic: a generic that acts locally (topical, ophthalmic…), a simple aqueous solution or a BCS case
needs no in-vivo BE study; 5.3.1.2 then holds the waiver justification and the other study items drop out."""
from dossier_engine import packs
from dossier_engine.profile import Profile, Api
from dossier_engine.resolver import resolve

PACK = packs.load('eda.ctd.nta065.v5')
BASE = dict(dossier_kind='generic', origin='local', licence='toll', activity='re_registration',
            apis=[Api('Neomycin sulphate', 'X', 'FULL')])
STUDY = ['M5-02', 'M5-03', 'M5-05', 'M5-06', 'M5-07', 'M5-08', 'M5-10']


def levels(**kw):
    return {s.req_id: s for s in resolve(Profile(**{**BASE, **kw}), PACK) if '@' not in s.slot_id}


def test_oral_tablet_needs_be_study():
    s = levels(admin_route='oral')
    assert s['M5-04'].level == 'R' and len(s['M5-04'].reasons) == 1
    assert all(s[k].level in ('R', 'O') for k in STUDY)


def test_topical_locally_acting_powder_is_not_exempt():
    """EDA GL.CAPP.024 v4 §3.13: only solutions are exempt; a locally acting powder/cream needs equivalence data."""
    s = levels(admin_route='topical', local_action=True)
    assert s['M5-04'].level == 'R' and '§3.13' in s['M5-04'].reasons[-1]['source']
    assert 'in-vitro' in s['M5-04'].reasons[-1]['en'] and 'موضعي' in s['M5-04'].reasons[-1]['ar']
    assert s['M5-06'].level == 'R'


def test_aqueous_solutions_are_exempt_on_every_route():
    for route in ('parenteral', 'oral', 'ophthalmic', 'nasal', 'topical'):
        s = levels(admin_route=route, aqueous_solution=True)
        assert s['M5-06'].level == 'NR' and '§2.2' in s['M5-04'].reasons[-1]['source'], route
    assert levels(admin_route='topical', local_action=True, aqueous_solution=True)['M5-06'].level == 'NR'


def test_bcs_oral_only():
    assert levels(admin_route='oral', bcs_waiver=True)['M5-06'].level == 'NR'
    assert levels(admin_route='topical', bcs_waiver=True)['M5-06'].level == 'R'       # BCS is for oral only


def test_innovator_never_waived():
    s = {x.req_id: x for x in resolve(Profile(dossier_kind='innovator', origin='imported', licence='imported',
                                              admin_route='topical', local_action=True,
                                              apis=[Api('A', 'B', 'FULL')]), PACK) if '@' not in x.slot_id}
    assert s['M5-06'].level == 'R'


def test_bad_route_rejected():
    import pytest
    from dossier_engine.profile import ProfileError
    with pytest.raises(ProfileError):
        Profile(**{**BASE, 'admin_route': 'magic'}).validate()
