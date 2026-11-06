from dossier_engine.variations import Variations


def test_pack_matches_snapshot():
    v = Variations()
    assert len(v.items) == 90
    from collections import Counter
    assert Counter(x['pac'] for x in v.items) == {'PAC-N': 38, 'PAC-A': 20, 'PAC-B': 18, 'PAC-II': 14}


def test_spot_checks_against_gl026_v6():
    v = Variations()
    api_new = [x for x in v.search('new manufacturer') if x['request'].startswith('Introduction of a new manufacturer for Active Substance')]
    assert len(api_new) == 1 and api_new[0]['pac'] == 'PAC-II'                # v6 §3.2.1
    sm = [x for x in v.search('new manufacturer starting material')]
    assert sm and sm[0]['pac'] == 'PAC-A'                                     # starting material/intermediate: lower class


def test_grouping_takes_highest_class():
    v = Variations()
    n = next(x['id'] for x in v.items if x['pac'] == 'PAC-N')
    b = next(x['id'] for x in v.items if x['pac'] == 'PAC-B')
    p = v.plan([n, b])
    assert p['class'] == 'PAC-B' and p['submission_type'] == 'var-pac-b' and p['mode'] == 'grouping'
    assert v.plan([n])['mode'] == 'single' and v.plan(['H-99'])['ok'] is False


def test_api(tmp_path):
    from fastapi.testclient import TestClient
    from dossier_engine.app.api import create_app
    c = TestClient(create_app(tmp_path))
    r = c.get('/api/variations?q=batch size').json()
    assert r['items'] and all('batch' in x['request'].lower() for x in r['items'])
    p = c.post('/api/variations/plan', json=[r['items'][0]['id']]).json()
    assert p['ok'] and p['submission_type'].startswith('var-pac-')
