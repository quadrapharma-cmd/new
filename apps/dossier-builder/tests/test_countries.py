"""The countries table (updates list, knowledge item 41): what each authority takes, with the source and how sure it is; the outputs a
dossier is offered follow it."""
from fastapi.testclient import TestClient
from dossier_engine import packs
from dossier_engine.app.api import create_app

FORMATS = {'ctd', 'ectd32', 'ectd40', 'nees', 'actd'}
VALUES = {'yes', 'no', 'optional', 'planned', 'unknown'}


def test_every_row_says_what_it_takes_and_where_that_is_written():
    tb = packs.countries_table()
    assert tb['reviewed']
    codes = set()
    for r in tb['countries']:
        assert set(r['formats']) == FORMATS and set(r['formats'].values()) <= VALUES, r['code']
        assert r['source'] and r['evidence'] in ('official', 'official-draft', 'secondary'), r['code']
        assert r['code'] not in codes
        codes.add(r['code'])
    assert packs.country_row('DE')['code'] == 'EU' and packs.country_row('KW')['code'] == 'GCC' and packs.country_row('ZZ') is None
    assert packs.formats_for('US')['nees'] == 'no' and packs.formats_for('EG')['ectd32'] == 'planned'


def test_the_outputs_follow_the_table():
    gcc, us, intl = packs.load('gcc.ctd.m1.v1'), packs.load('us.ctd.m1.v1'), packs.load('intl.ctd.m1.v1')
    assert gcc.outputs_for('SA') == ['ctd', 'ectd32', 'nees'] and us.outputs_for('US') == ['ctd']
    assert intl.outputs_for('TH') == ['ctd', 'nees', 'actd'] and intl.outputs_for('JO') == ['ctd', 'nees'] and intl.outputs_for(None) == ['ctd', 'nees']
    assert packs.load('eda.ctd.nta065.v5').outputs_for('EG') == ['ctd', 'ectd32', 'ectd40']


def test_the_table_is_served(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    r = c.get('/api/countries').json()
    assert any(x['code'] == 'EU' and x['evidence'] == 'official' for x in r['countries'])
