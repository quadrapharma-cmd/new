"""Generators: no guessing (request_data), correct arithmetic, Arabic survives to PDF."""
import shutil, subprocess
from decimal import Decimal
import pytest
from docx import Document
from dossier_engine.generate import letters
from dossier_engine.generate.docx_kit import MissingData, to_pdf

SOFFICE = shutil.which('soffice')

ANNEX = dict(trade_name='Examplol 500 mg film-coated tablets / إكزامبلول ٥٠٠ مجم', registration_number='REQ-2026-0001',
             actives_strengths='Paracetamol 500 mg', dosage_form='Film-coated tablet', route='Oral',
             physical_characters='White oblong film-coated tablet', shelf_life='36 months', storage='Store below 30 °C',
             price_pack='2 Alu/PVC blisters × 10 tablets', price='EGP 45', ref_name='Panadol 500 mg',
             ref_mah='GSK, UK', ref_link='https://example.invalid/ref', therapeutic_group='Analgesic', atc='N02BE01',
             indication='Mild to moderate pain; fever', applicant='Example Pharma S.A.E.', portal_username='examplepharma',
             mah='Example Pharma S.A.E.', manufacturer='Example Pharma, 6th of October City', packager='Example Pharma',
             batch_releaser='Example Pharma', storage_site='6th of October City', registration_type='Local',
             market_status='New', decree='450/2023 Case 1', batch_type='Pilot', batch_numbers='P001, P002',
             contact_person='Dr. A. Example', telephone='+20 2 0000 0000', email='ra@example.invalid',
             signatory='أحمد مثال', signatory_title='العضو المنتدب', company='إكزامبل فارما', distributors='شركة التوزيع المثالية')
CTX = dict(origin='local', activity='new', decree_case='450-Case1',
           apis=[dict(option='CEP', cep='R1-CEP 2015-123-Rev 02 (2024-05-01)', name_form_specs='Paracetamol / powder / Ph. Eur.',
                      manufacturer_gmp_address='Granules India Ltd, Hyderabad, India', studies='BE, stability, CADC')])


def text(docx):
    return '\n'.join(p.text for p in Document(docx).paragraphs) + '\n'.join(
        c.text for t in Document(docx).tables for r in t.rows for c in r.cells)


def test_annex1_requests_missing_data(tmp_path):
    with pytest.raises(MissingData) as e:
        letters.annex1({**ANNEX, 'atc': '', 'price': None}, {**CTX, 'apis': [dict(option='CEP')]}, tmp_path / 'a.docx')
    assert {'atc', 'price', 'apis[0].name_form_specs', 'apis[0].manufacturer_gmp_address'} <= set(e.value.fields)


def test_annex1_content_and_conditions(tmp_path):
    p = letters.annex1(ANNEX, CTX, tmp_path / 'a.docx')
    t = text(p)
    assert 'بأن كافة البيانات المذكورة أعلاه صحيحة ودقيقة وكاملة.' in t
    assert 'ثلاث سنوات' in t and 'خمس سنوات' not in t                     # decree case 1 only
    assert 'لم يتم عمل أي متغيرات' in t                                    # no variations
    assert '☒ CEP' in t and '☐ DMF' in t
    assert 'إعادة التسجيل (تحليل' not in t                                 # re-registration clause off
    t3 = text(letters.annex1({**ANNEX, 'rereg_studies_api_source': 'Granules India'},
                             {**CTX, 'decree_case': '450-Case3', 'activity': 're_registration',
                              'variations': [dict(type='PAC-B', **{'from': '10 kg', 'to': '20 kg'}, status='Final')]},
                             tmp_path / 'b.docx'))
    assert 'خمس سنوات' in t3 and 'ثلاث سنوات' not in t3 and 'تم عمل المتغيرات' in t3 and 'PAC-B' in t3
    assert 'Granules India' in t3


def test_rtl_markup(tmp_path):
    p = letters.annex1(ANNEX, CTX, tmp_path / 'a.docx')
    xml = Document(p).element.xml
    assert '<w:bidi/>' in xml and '<w:rtl/>' in xml


def test_salt_equivalence():
    r = letters.salt_equivalence(dict(name_base='amlodipine', name_salt='amlodipine besilate', label_claim_mg=5,
                                      mw_salt=567.1, mw_base=408.9, mw_ref='Ph. Eur. monograph 1491', assay_pct=99.5))
    assert round(r['salt_mg'], 3) == Decimal('6.934')
    assert round(r['adjusted_mg'], 3) == Decimal('6.969')
    assert '5 mg × 567.1 / 408.9' in r['formula']
    with pytest.raises(MissingData) as e:
        letters.salt_equivalence(dict(name_base='x', name_salt='y', label_claim_mg=5, mw_salt=1, mw_base=1))
    assert e.value.fields == ['mw_ref']


def test_composition(tmp_path):
    comps = [dict(name='Paracetamol', function='API', qty_mg=500, standard='Ph. Eur.'),
             dict(name='Povidone K30', function='Binder', qty_mg=15, standard='Ph. Eur.'),
             dict(name='Magnesium stearate', function='Lubricant', qty_mg=5, standard='Ph. Eur.'),
             dict(name='Opadry II White 85F18422', function='Film coat', qty_mg=15.6, standard='In-house', part='coat')]
    p, total = letters.composition_certificate(dict(trade_name='Examplol 500 mg', dosage_form='Film-coated tablet',
                                                    components=comps, signatory='A', signatory_title='MD'), tmp_path / 'c.docx')
    assert total == Decimal('535.6')
    t = text(p)
    assert 'Core' in t and 'Coating' in t and '535.6' in t and '96.15' in t      # 500/520 = 96.15 %


def test_letters_need_their_fields(tmp_path):
    for fn in (letters.cep_commitment, letters.translation_declaration, letters.cover_letter):
        with pytest.raises(MissingData):
            fn({}, tmp_path / 'x.docx')


@pytest.mark.skipif(not SOFFICE, reason='LibreOffice not installed')
def test_pdf_arabic_and_draft(tmp_path):
    p = letters.annex1(ANNEX, CTX, tmp_path / 'annex1.docx')
    pdf = to_pdf(p)
    txt = subprocess.run(['pdftotext', '-raw', str(pdf), '-'], capture_output=True, text=True).stdout
    assert 'هيئة' in txt and 'الدواء' in txt and 'المصرية' in txt         # Arabic glyphs mapped back to text
    assert 'DRAFT' in txt
    from dossier_engine.checks.pdf import check
    assert check(str(pdf), 'generated').status in ('conforming', 'needs_attention')
