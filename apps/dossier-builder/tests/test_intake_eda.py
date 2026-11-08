"""Intake on EDA forms: the Final Registration License table (actives with strengths, API manufacturers paired to each
substance, holder, manufacturer, registration number, dates, prices), the PPMA pricing letter («Each 1g contains: A + B …»)
and the CADC Notification Letter (batch · expiry · conformity) — on clean text and on OCR-like noisy text. Fictional product."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import extract, intake_eda
from dossier_engine.app.api import create_app

LICENCE = ['Arab Republic of Egypt', 'Egyptian Drug Authority', 'Central Administration for Pharmaceutical Products', 'Final Registration License for Pharmaceutical Product',
           'Trade Name: Dermacure', 'Dosage Form: Topical Powder', 'Active Ingredient(s) & Each 1g contains:',
           'Strength(s): NEOMYCIN SULPHATE 3.500 mg ( 3300 unit )', 'Bacitracin Zinc 4.200 mg (250 unit )', 'CYSTEINE 2.000 mg', 'GLYCINE 10.000 mg', 'THREONINE 1.000 mg',
           'Physical Character: White homogenous powder', 'Shelf Life: 36 Months', 'Storage Condition: Store at a temperature not exceeding 30C in dry place.',
           'Approved Pack: White opaque plastic (HDPE) jar containing 10 g or 20 g powder with insert leaflet.',
           'Price: 34 L.E. / 1 Box/ 1 Bottle/ 10 Gm ;', '60 L.E. / 1 Box/ 1 Jar/ 20 Gm ;', 'Type of License: Toll Type of Marketing: Local',
           'Registration No.: 29925/2022 Invalidation Date: 10-11-2032', 'License Holder : EXAMPLE PHARM-EGYPT,EGYPT', 'Manufacturer : Example Industries for pharmaceutical industries,EGYPT',
           'Packager: Example Industries for pharmaceutical industries,EGYPT', 'Storage Site: Example Industries for pharmaceutical industries,EGYPT',
           'Manufacturer Of active substance: NEOMYCIN SULPHATE', 'Sichuan Example Pharmaceutical Co.Ltd,CHINA', 'Bacitracin Zinc', 'North Example Pharmaceutical Huasheng Co. LTD,CHINA',
           'THREONINE', 'GLYCINE', 'Hubei Example Pharmaceuticals and Chemicals Share Co.,Ltd ,CHINA', 'Issue Date: 26/7/2022']
NOISY = ['i Active Ingredient(s) & Each 1g contains:', '1 Strength(s): NEOMYCIN SULPHATE 3.500 mg ( 3300 unit )\u200f1', '| Bacitracin Zine 4.200 mg (250 unit )', 'CYSTEINE 2.000 mg\u200f1',
         'GLYCINE 10,000 mg', 'THREONINE 1,000 mg 1 7', '| Trade Name: Dermacure ‘a 07 ديرماكيور', 'ioe ‘License Holder : EXAMPLE PHARM-EGYPT,EGYPT',
         'i Manufacturer + : Example Industries for gharmaceutical industries, EGYPT 1 1 1', 'be Manufacturer Of active substance: NEOMYCIN SULPHATE',
         'ee Sichuan Example Pharmaceutical Co.Ltd,CHINA', 'ad Bacitracin Zine', 'North Example Pharmaceutical Huasheng Co. LTD,CHINA', 'i THREONINE', 'GLYCINE',
         'Hubei Example Pharmaceuticals and Chemicals Share Co.,Ltd ,CHINA', 'Registration No.: 29925/2022 Invalidation Date: 40-11-2032', '5 Type of License: Toll Type of Marketing: Local',
         'Each 1 gram Contains:-', 'Neomycin Sulphate   quivalent to 3300 units / 2529     282018', 'Bacitracin Zinc (Equivalent to 250 unit 81              BP2018              [42mg |']   # the composition table as the browser OCR reads it
PRICING = ['Egyptian Drug Authority — Pricing Policies Administration', 'اسم المستحضر سعر البيع للجمهور', 'Dermacure Topical Powder قرش جنيه', 'Jar of 10gm 00 51',
           'Each 1g contains:', 'NEOMYCIN SULPHATE 3.5 mg + Bacitracin Zinc 4.2 mg + CYSTEINE 2 mg +', 'GLYCINE 10 mg + THREONINE 1 mg', 'Applicant: EXAMPLE PHARM; للعبوه 10 جرام',
           'العنوان: منطقة الخدمات زهراء المعادي - مبنى هيئة الدواء المصرية 7316 Tel.: +202']
CADC = ['Egyptian Drug Authority — Central Administration of drug control', 'Notification Letter', 'Product Name: Dermacure Topical Powder', 'Sample Identification Code: 2308/1LHF23',
        'Company Name: Example Industries for EXAMPLE PHARM', 'Below, you will find the statement of conformity/ non-conformity of the tested batches, according to CADC guidelines:',
        'Batch Number [, || 2206004 [Expiry date /Re-tespidate: | 31-08-2025 1 1 Conform', '(QF:CADC.002.02.12) Issue Date: 28 /12/2022']


def _apis(f):
    return {a['name']: a for a in f['apis']}


def test_licence_table_is_read_in_full():
    f = extract.fields_for('licence', 'licence.txt', '\n'.join(LICENCE))
    a = _apis(f)
    assert list(a) == ['Neomycin Sulphate', 'Bacitracin Zinc', 'Cysteine', 'Glycine', 'Threonine']
    assert a['Neomycin Sulphate']['strength'] == '3.500 mg' and a['Neomycin Sulphate']['equivalent'] == '3300 unit'
    assert a['Neomycin Sulphate']['manufacturer'] == 'Sichuan Example Pharmaceutical Co.Ltd' and a['Neomycin Sulphate']['country'] == 'China'
    assert a['Bacitracin Zinc']['manufacturer'].startswith('North Example') and a['Glycine']['manufacturer'] == a['Threonine']['manufacturer'] == 'Hubei Example Pharmaceuticals and Chemicals Share Co.,Ltd'
    assert 'manufacturer' not in a['Cysteine'] and 'equivalent' not in a['Cysteine']   # the licence names none for it: nothing is invented
    assert f['product']['name'] == 'Dermacure' and f['product']['dosage_form'] == 'Topical Powder' and 'strength' not in f['product']
    assert f['product']['manufacturer'] == 'Example Industries for pharmaceutical industries' and f['product']['manufacturer_country'] == 'Egypt'
    assert f['envelope']['applicant'] == 'EXAMPLE PHARM-EGYPT'
    assert f['profile']['licence'] == 'toll' and f['profile']['origin'] == 'local' and f['profile']['admin_route'] == 'topical'
    r = f['registration']
    assert r['reg_no'] == '29925/2022' and r['reg_date'] == '2022-07-26' and r['shelf_life'] == '36 Months'
    assert r['prices'] == [{'price': '34 EGP', 'pack': '1 Box/ 1 Bottle/ 10 Gm'}, {'price': '60 EGP', 'pack': '1 Box/ 1 Jar/ 20 Gm'}]
    assert f['document']['valid_until'] == '2032-11-10' and f['document']['issued'] == '2022-07-26' and f['document']['issuer'] == 'Egyptian Drug Authority'


def test_ocr_noise_is_tolerated():
    f = extract.fields_for('licence', 'scan.txt', '\n'.join(NOISY))
    a = _apis(f)
    assert list(a) == ['Neomycin Sulphate', 'Bacitracin Zinc', 'Cysteine', 'Glycine', 'Threonine']     # «Zine» repaired, junk prefixes dropped
    assert a['Bacitracin Zinc']['manufacturer'] == 'North Example Pharmaceutical Huasheng Co. LTD'       # «Co.» never splits a company
    assert a['Threonine']['manufacturer'].startswith('Hubei Example') and a['Neomycin Sulphate']['manufacturer'] == 'Sichuan Example Pharmaceutical Co.Ltd'
    assert f['product']['name'] == 'Dermacure' and f['product']['name_ar'] == 'ديرماكيور'
    assert f['product']['manufacturer'] == 'Example Industries for pharmaceutical industries' and f['product']['manufacturer_country'] == 'Egypt'
    assert f['registration']['reg_no'] == '29925/2022' and f['document']['valid_until'] is None            # «40-11-2032» is not a date: left empty, never guessed
    assert a['Glycine']['strength'] == '10.000 mg' and a['Threonine']['strength'] == '1.000 mg'             # OCR comma for the point, repaired from the form's 3-decimal style
    assert intake_eda.actives(['NEOMYCIN SULPHATE 3.5 mg + THREONINE 1! mg'])[0][1]['strength'] == '1 mg'  # a stray OCR mark after the number
    assert intake_eda.norm_name('BACITRACIN ZINE') == 'Bacitracin Zinc' and intake_eda.norm_name('Bisoprolol fumarate') == 'Bisoprolol fumarate'   # mixed case stays as printed


def test_pricing_letter_inline_list_and_table_row():
    txt = '\n'.join(PRICING)
    assert extract.guess_kind('price.pdf', txt) == 'pricing'
    f = extract.fields_for('pricing', 'price.pdf', txt)
    assert [a['name'] for a in f['apis']] == ['Neomycin Sulphate', 'Bacitracin Zinc', 'Cysteine', 'Glycine', 'Threonine']
    assert f['apis'][4]['strength'] == '1 mg' and f['product']['name'] == 'Dermacure Topical Powder'
    assert f['envelope']['applicant'] == 'EXAMPLE PHARM' and f['registration']['price'] == '51.00 EGP' and f['registration']['packs'] == ['Jar of 10gm']
    assert 'manufacturer_address' not in f['product']                                                       # the authority's footer address is not the manufacturer's
    f2 = extract.fields_for('pricing', 'price.pdf', txt + '\nJar of 20gm 00 88')                             # page 2 of the letter: the second pack
    assert f2['registration']['prices'] == [{'price': '51.00 EGP', 'pack': 'Jar of 10gm'}, {'price': '88.00 EGP', 'pack': 'Jar of 20gm'}]
    assert f2['registration']['packs'] == ['Jar of 10gm', 'Jar of 20gm']


def test_cadc_notification_letter_batch_row():
    txt = '\n'.join(CADC)
    assert extract.guess_kind('conf.pdf', txt) == 'cadc'
    f = extract.fields_for('cadc', 'conf.pdf', txt)
    assert f['batches'] == [{'no': '2206004', 'kind': 'fpp', 'expiry': '2025-08-31', 'conformity': 'Conform'}]
    assert f['product']['name'] == 'Dermacure Topical Powder' and f['envelope']['applicant'] == 'Example Industries for EXAMPLE PHARM'
    assert f['document']['sample_code'] == '2308/1LHF23' and f['document']['issued'] == '2022-12-28' and f['document']['issuer'] == 'Egyptian Drug Authority'


def test_composition_table_rows():
    rows = intake_eda.composition('\n'.join(['Each 1 gram Contains:-', 'Ingredient Specification Quantity', 'Active Ingredients',
                                             'Neomycin Sulphate (Equivalent to 3300 units / gm) BP2018 3.5 mg', 'Bacitracin Zinc (Equivalent to 250 unit /gm BP2018 4.2 mg',
                                             'Glycine BP2018 10 mg', 'Inactive Ingredients', 'maize starch BP2018 977 mg']))
    assert [(r['name'], r['standard'], r['amount'], r['role']) for r in rows] == [('Neomycin Sulphate', 'BP2018', '3.5 mg', 'active'), ('Bacitracin Zinc', 'BP2018', '4.2 mg', 'active'),
                                                                               ('Glycine', 'BP2018', '10 mg', 'active'), ('Maize Starch', 'BP2018', '977 mg', 'excipient')]
    assert rows[0]['equivalent'] == 'Equivalent to 3300 units / gm'


def test_three_documents_merge_into_one_fill(tmp_path):
    lic = make_pdf_lines(tmp_path / 'licence.pdf', LICENCE, 'Final Registration License')
    pr = make_pdf_lines(tmp_path / 'price.pdf', [x for x in PRICING if not any('؀' <= ch <= 'ۿ' for ch in x)], 'Pricing')
    cadc = make_pdf_lines(tmp_path / 'conf.pdf', CADC, 'Notification Letter')
    c = TestClient(create_app(tmp_path / 'ws'))
    r = c.post('/api/extract', files=[('files', (p.name, io.BytesIO(p.read_bytes()), 'application/pdf')) for p in (lic, pr, cadc)])
    assert r.status_code == 200, r.text
    fill = r.json()['rules']
    assert [a['name'] for a in fill['apis']] == ['Neomycin Sulphate', 'Bacitracin Zinc', 'Cysteine', 'Glycine', 'Threonine']
    assert fill['apis'][0]['manufacturer'].startswith('Sichuan') and fill['apis'][0]['strength'] == '3.500 mg'
    assert fill['product']['name'] == 'Dermacure' and fill['envelope']['applicant'] == 'EXAMPLE PHARM-EGYPT' and fill['registration']['reg_no'] == '29925/2022'
    assert fill['batches'][0]['no'] == '2206004' and fill['batches'][0]['conformity'] == 'Conform'
    assert [d['kind'] for d in fill['documents']] == ['licence', 'pricing', 'cadc']
    assert 'Manufacturer Of active substance' in r.json()['prompt'] and 'one apis entry per substance' in r.json()['prompt']
