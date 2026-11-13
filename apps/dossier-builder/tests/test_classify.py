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


@pytest.mark.parametrize('name,text,expected', [          # a file is what its text says: the name is never read
    ('scan_0007.pdf', 'GMP certificate Example Pharma', 'M1-37'),
    ('scan_0008.pdf', 'Pricing certificate', 'M1-05'),
    ('scan_0001.pdf', 'CERTIFICATE OF ANALYSIS Paracetamol batch 123 Granules India', 'M1-35@Paracetamol|Granules India'),
    ('scan_0009.pdf', '3.2.P.5.1 Specification of the finished product', 'P-09'),
    ('scan_0010.pdf', 'Composition certificate signed', 'M1-31'),
    ('scan_0011.pdf', 'cover letter sequence 0000', 'M1-43'),
    ('scan_0012.pdf', 'شهادة التسعير', 'M1-05'),
    ('BE study report EXM-BE-01.pdf', 'bioequivalence study of paracetamol', 'M5-04'),
    # real-dossier regressions (a local toll product, 11/2026): reference leaflets in German, committee letters
    ('7-9451__DOTC_FACH_INFO.pdf', 'Fachinformation reference SmPC', 'M1-42'),
    ('8-9451__DMTC_GEBR_INFO_BF.pdf', 'Gebrauchsinformation', 'M1-42'),
    ('14-pharmacology committee approvaL.pdf', 'pharmacology committee approval', 'M1-06'),
])
def test_suggestions(ctx, name, text, expected):
    assert top(ctx, name, text) == expected


def test_the_file_name_is_never_read(ctx):
    assert ctx[0].suggest('3.2.P.5.1 Specification GMP pricing certificate.pdf', '', ctx[1]) == []


def test_inactive_slots_never_suggested(ctx):
    s = ctx[0].suggest('scan.pdf', 'CPP certificate of pharmaceutical product', ctx[1])
    assert all(x['req_id'] != 'M1-14' for x in s)       # CPP not applicable to a local own product


def test_unknown_file_no_guess(ctx):
    assert ctx[0].suggest('IMG_2041.pdf', '', ctx[1]) == []
