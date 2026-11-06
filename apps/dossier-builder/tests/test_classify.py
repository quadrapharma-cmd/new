from datetime import date
import pytest
from dossier_engine import packs
from dossier_engine.classify import Classifier, _ctd_tokens
from dossier_engine.profile import Profile, Api
from dossier_engine.resolver import resolve


@pytest.fixture(scope='module')
def ctx():
    pack = packs.load('eda.ctd.nta065.v5')
    p = Profile(licence='own', dosage_specifics=['coated'], pharmacopoeial=True,
                apis=[Api('Paracetamol', 'Granules India', 'CEP'), Api('Paracetamol', 'Anqiu', 'FULL')])
    return Classifier(pack), resolve(p, pack, today=date(2026, 11, 6))


def top(ctx, name, text=''):
    s = ctx[0].suggest(name, text, ctx[1])
    return s[0]['slot_id'] if s else None


def test_ctd_numbers():
    assert '3.2.p.5.1' in _ctd_tokens('32p51-spec.pdf')
    assert '3.2.p.5.1' in _ctd_tokens('3.2.P.5.1 Specification.pdf')
    assert '1.1.13' in _ctd_tokens('1.1.13 CPP.pdf')


@pytest.mark.parametrize('name,text,expected', [
    ('GMP certificate Example Pharma.pdf', '', 'M1-37'),
    ('Pricing certificate.pdf', '', 'M1-05'),
    ('scan_0001.pdf', 'CERTIFICATE OF ANALYSIS Paracetamol batch 123 Granules India', 'M1-35@Paracetamol|Granules India'),
    ('3.2.P.5.1 Specification.pdf', '', 'P-09'),
    ('Composition certificate signed.pdf', '', 'M1-31'),
    ('cover letter seq 0000.pdf', '', 'M1-43'),
    ('شهادة التسعير.pdf', '', 'M1-05'),
    ('BE study report EXM-BE-01.pdf', 'bioequivalence study of paracetamol', 'M5-04'),
])
def test_suggestions(ctx, name, text, expected):
    assert top(ctx, name, text) == expected


def test_inactive_slots_never_suggested(ctx):
    s = ctx[0].suggest('CPP certificate of pharmaceutical product.pdf', '', ctx[1])
    assert all(x['req_id'] != 'M1-14' for x in s)       # CPP not applicable to a local own product


def test_unknown_file_no_guess(ctx):
    assert ctx[0].suggest('IMG_2041.pdf', '', ctx[1]) == []
