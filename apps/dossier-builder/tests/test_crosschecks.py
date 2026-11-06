"""P2 cross-document checks: a seeded «bad» dossier triggers its findings; a clean one triggers none."""
import copy
from dossier_engine.crosschecks import run
from dossier_engine.profile import Profile, Api

PROF = Profile(apis=[Api('Paracetamol', 'Granules India', 'CEP')])
K = 'Paracetamol|Granules India'
GOOD = {
    'product': {'shelf_life': '36 months', 'storage': 'Store below 30 °C'},
    'apis': [{'name': 'Paracetamol', 'manufacturer': 'Granules India', 'option': 'CEP', 'cep_no': 'R1-CEP 2015-123-Rev 02',
              'cep_status': 'valid', 'spec_standard': 'Ph. Eur. 11', 'coa_name': 'Paracetamol',
              'address_gmp': 'Plot 1, Gagillapur, Hyderabad', 'address_annex': 'Plot 1, Gagillapur, Hyderabad'}],
    'composition': [{'name': 'Paracetamol', 'standard': 'Ph. Eur.'}, {'name': 'Povidone K30', 'standard': 'Ph. Eur.'}],
    'batches': [{'no': 'EX0001', 'size': '100,000', 'date': '2026-01', 'site': 'A', 'scale': 'pilot', 'executed_bmr': True},
                {'no': 'EX0002', 'size': '100,000', 'date': '2026-02', 'site': 'A', 'scale': 'pilot'},
                {'no': 'A1', 'kind': 'api', 'api': K}, {'no': 'A2', 'kind': 'api', 'api': K}],
    'specs': {'product': [{'test': 'Assay', 'limit': '95.0–105.0 %'}, {'test': 'Dissolution', 'limit': 'Q = 80 % in 30 min'},
                          {'test': 'Description', 'limit': 'White oblong tablet', 'qualitative': True}],
              'api': {K: [{'test': 'Assay', 'limit': '99.0–101.0 %'}]}},
    'results': {'EX0001': {'Assay': '99.8', 'Dissolution': '92 (88–95)', 'Description': 'Complies'},
                'EX0002': {'Assay': '100.4', 'Dissolution': '90 (86–94)', 'Description': 'Complies'},
                'A1': {'Assay': '99.9'}, 'A2': {'Assay': '100.1'}},
    'be_batches': ['EX0001'], 'stability_batches': ['EX0001', 'EX0002'],
    'pack': {'units_annex': '2 x 10', 'units_pricing': '2 x 10', 'material_annex': 'Alu/PVC', 'material_stability': 'Alu/PVC'},
    'applicant_names': {'envelope': 'Example Pharma S.A.E.', 'annex1': 'Example Pharma S.A.E.'},
    'leaflet': {'shelf_life': '36 months'},
}


def ids(data):
    return sorted({f.id for f in run(data, PROF)})


def test_clean_dossier_has_no_findings():
    assert run(GOOD, PROF) == []


def test_bad_dossier_triggers_each_check():
    bad = copy.deepcopy(GOOD)
    bad['composition'][0]['standard'] = 'USP 2025'                         # XC-03
    bad['apis'][0]['coa_name'] = 'Acetaminophen'                           # XC-04
    bad['results']['EX0002'].pop('Assay')                                  # XC-05
    bad['results']['EX0001']['Assay'] = 'Conforms'                         # NP040-NUM
    bad['specs']['product'][1]['limit'] = 'NLT 80 % in 30 min'             # NP040-Q
    bad['batches'] = [b for b in bad['batches'] if b['no'] != 'A2']        # NP040-S44
    bad['apis'][0]['address_annex'] = 'Plot 1, Hyderabad'                  # XC-06
    bad['pack']['units_pricing'] = '1 x 10'                                # XC-07
    bad['apis'][0]['cep_status'] = 'Suspended'                             # XC-08
    bad['be_batches'] = ['EX0009']                                         # XC-09
    bad['applicant_names']['cover'] = 'Example Pharma'                     # XC-11
    bad['leaflet']['shelf_life'] = '24 months'                             # XC-10
    found = ids(bad)
    expected = {'XC-03', 'XC-04', 'XC-05', 'NP040-NUM', 'NP040-Q', 'NP040-S44', 'XC-06', 'XC-07', 'XC-08', 'XC-09', 'XC-10', 'XC-11'}
    assert expected <= set(found), expected - set(found)
    assert len(expected & set(found)) / len(expected) >= 0.9               # 01-PLAN P2 acceptance (≥ 90 %)


def test_one_batch_and_missing_bmr():
    bad = copy.deepcopy(GOOD)
    bad['batches'] = [dict(bad['batches'][0], executed_bmr=False)] + bad['batches'][2:]
    bad['stability_batches'] = ['EX0001']
    f = ids(bad)
    assert 'NP040-P54' in f and 'NP040-R11' in f


def test_findings_are_explained():
    bad = copy.deepcopy(GOOD)
    bad['pack']['units_pricing'] = '1 x 10'
    f = run(bad, PROF)[0]
    assert f.ar and f.en and f.source and f.slots == ['M1-01', 'M1-05']
