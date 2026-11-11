"""Review fixes (November 2026): the document-kind rule reads the title as whole words (a coated product's licence is not a CoA, an
Arabic stability approval is a stability document), the active substances keep salts that are the substance, combinations and the
digits of a name and drop labels, companies and countries, the kind's home never pushes a document into another API's item, and
a leaflet or a study placed from the «not placed yet» box or moved by the kind rule carries the details the eCTD writers need.
Fictional product «Dermacure»."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf, make_pdf_lines
from dossier_engine import extract, intake_eda
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}
FCT_LICENCE = ['Arab Republic of Egypt', 'Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure 500 mg',
               'Dosage Form: Film coated tablet', 'Registration No.: 29925/2022']
AR_STABILITY = ['هيئة الدواء المصرية', 'الإدارة العامة للتسجيل', 'بالإشارة إلى طلب الموافقة على دراسة الثبات للمستحضر ديرماكيور',
                'نحيط سيادتكم علما بموافقة اللجنة بجلستها المنعقدة بتاريخ 2025/03/10 على مدة صلاحية 24 شهر', 'رقم الترخيص: 29925/2022']


@pytest.mark.parametrize('name, lines, kind', [
    ('licence.pdf', FCT_LICENCE, 'licence'),                                                         # «coated» is not «coa»
    ('pricing.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Dermacure 500 mg film coated tablets', 'Public price: 45 EGP'], 'pricing'),
    ('smpc.pdf', ['Summary of Product Characteristics', 'Dermacure 500 mg film coated tablets'], 'smpc'),
    ('composition.pdf', ['Composition Certificate', 'Each film coated tablet contains: Paracetamol 500 mg', 'Film coating: Opadry white'], 'composition'),
    ('spec.pdf', ['Finished Product Specification', 'Dermacure 500 mg film coated tablets', 'Assay 95-105 %'], 'spec'),
    ('stability.pdf', ['Stability Study Report', 'Dermacure 500 mg film coated tablets'], 'stability'),
    ('pricing2.pdf', ['Pricing Certificate', 'The product is manufactured under GMP', 'Public price 45 EGP'], 'pricing'),   # a mention in the body is not the title
    ('scan.pdf', AR_STABILITY, 'stability'),                                                          # Arabic stability approval; «المنعقدة» is not «عقد»
    ('scan2.pdf', ['إخطار بالموافقة على دراسة الثبات للمستحضر ديرماكيور'], 'stability'),               # «إخطار» alone does not make it a licence
    ('x.pdf', ['إخطار تسجيل مستحضر'], 'licence'), ('x.pdf', ['شهادة تحليل'], 'coa'), ('x.pdf', ['عقد تصنيع لدى الغير'], 'contract'),
    ('coa_bacitracin.pdf', [], 'coa'), ('CoA.pdf', [], 'coa'),                                         # the file name still counts when the page has no text
    ('x.pdf', ['هيئة الدواء المصرية', 'ترخيص تداول مستحضر صيدلي', 'يصرف مع النشرة الداخلية'], 'licence'),   # a licence that mentions the leaflet
    # a document that cites the registration notification / licence by its number is still what its title says
    ('scan.pdf', ['هيئة الدواء المصرية', 'شهادة تسعير', 'اسم المستحضر: ديرماكيور أقراص', 'رقم إخطار التسجيل: 29925/2022', 'سعر البيع للجمهور: 45 جنيه'], 'pricing'),
    ('scan.pdf', ['هيئة الدواء المصرية', 'شهادة تسعير', 'اسم المستحضر: ديرماكيور أقراص', 'رخصة التسجيل رقم: 29925/2022'], 'pricing'),
    ('scan.pdf', ['Egyptian Drug Authority', 'Pricing Department', 'Product: Dermacure 500 mg tablets', 'Registration License No.: 29925/2022', 'Public price: 45 EGP'], 'pricing'),
    ('scan.pdf', ['Egyptian Drug Authority', 'GMP Inspection Report', 'Site: Example Pharma', 'Manufacturing Licence No. 55/2019', 'The site complies with GMP'], 'gmp'),
    ('scan.pdf', ['هيئة الدواء المصرية', 'الإدارة المركزية للمستحضرات الصيدلية', 'السيد الدكتور / مدير شركة إكزامبل فارما', 'تحية طيبة وبعد،',
                  'بالإشارة إلى طلبكم نفيدكم بالموافقة على دراسة الثبات للمستحضر ديرماكيور المسجل بإخطار التسجيل رقم 29925/2022 لمدة 24 شهر'], 'stability'),
    ('scan.pdf', ['هيئة الدواء المصرية', 'بالإشارة إلى المستحضر ديرماكيور المسجل بإخطار التسجيل رقم 29925/2022 نفيدكم بالموافقة على دراسة الثبات لمدة 24 شهر'], 'stability'),
    ('scan.pdf', ['Egyptian Drug Authority', 'Subject: Approval of the stability study of Dermacure 500 mg tablets, Registration License No. 29925/2022',
                  'The stability study submitted is approved for a shelf life of 24 months.'], 'stability'),
    ('scan.pdf', ['Egyptian Drug Authority', 'Ref: Dermacure 500 mg tablets, Registration License No. 29925/2022', 'Subject: approval of the stability study'], 'stability'),
    ('scan.pdf', ['هيئة الدواء المصرية', 'إخطار تسجيل رقم 29925/2022', 'اسم المستحضر: ديرماكيور أقراص', 'التركيب: باراسيتامول 500 مجم'], 'licence'),   # a number in the title is still the title
    ('scan.pdf', ['Egyptian Drug Authority', 'Registration License No. 29925/2022', 'Trade name: Dermacure 500 mg film coated tablets', 'Composition: Paracetamol 500 mg',
                  'GMP certificate of the site: EG-GMP-12'], 'licence'),
    ('scan.pdf', ['Egyptian Drug Authority', 'GMP Certificate No. EG-GMP-12', 'Site: Example Pharma, Manufacturing Licence No. 55/2019', 'The site complies with good manufacturing practice'], 'gmp'),
    ('scan.pdf', ['Example Pharma Quality Control', 'Certificate of Analysis', 'Product: Paracetamol BP', 'Test | Specification | Result', 'Assay | 99.0-101.0 % | 99.8 %'], 'coa'),
])
def test_kind_rule_reads_whole_words_and_the_title_first(name, lines, kind):
    assert extract.guess_kind(name, '\n'.join(lines)) == kind


def test_kind_rule_refuses_an_arabic_stability_approval_in_the_pricing_item():
    k = extract.kind_check('M1-05', 'scan.pdf', '\n'.join(AR_STABILITY))
    assert k['kind'] == 'stability' and not k['ok'] and 'M1-34' in k['homes']
    assert extract.kind_check('M1-04', 'licence.pdf', '\n'.join(FCT_LICENCE))['ok']                    # the right licence in its item passes
    pricing = 'هيئة الدواء المصرية\nشهادة تسعير\nاسم المستحضر: ديرماكيور أقراص\nرقم إخطار التسجيل: 29925/2022\nسعر البيع للجمهور: 45 جنيه'
    assert extract.kind_check('M1-05', 'scan.pdf', pricing)['ok'] and not extract.kind_check('M1-04', 'scan.pdf', pricing)['ok']   # a pricing certificate that cites the notification number stays a pricing certificate
    approval = 'هيئة الدواء المصرية\nبالإشارة إلى المستحضر ديرماكيور المسجل بإخطار التسجيل رقم 29925/2022 نفيدكم بالموافقة على دراسة الثبات لمدة 24 شهر'
    assert extract.kind_check('M1-34', 'scan.pdf', approval)['ok'] and not extract.kind_check('M1-04', 'scan.pdf', approval)['ok']   # and a stability approval is not the licence it cites


def _names(apis):
    return [(a['name'], a.get('strength')) for a in apis]


def test_active_substances_that_are_salts_or_combinations_are_kept_apart():
    assert _names(extract.clean_apis([{'name': 'Sodium chloride', 'strength': '2.6 g'}, {'name': 'Potassium chloride', 'strength': '1.5 g'},
                                      {'name': 'Sodium citrate', 'strength': '2.9 g'}, {'name': 'Glucose anhydrous', 'strength': '13.5 g'}])) == [
        ('Sodium chloride', '2.6 g'), ('Potassium chloride', '1.5 g'), ('Sodium citrate', '2.9 g'), ('Glucose anhydrous', '13.5 g')]
    assert _names(extract.clean_apis([{'name': 'Aluminium hydroxide', 'strength': '200 mg'}, {'name': 'Magnesium hydroxide', 'strength': '200 mg'}])) == [
        ('Aluminium hydroxide', '200 mg'), ('Magnesium hydroxide', '200 mg')]
    assert [a['name'] for a in extract.clean_apis([{'name': 'Sodium alginate'}, {'name': 'Sodium bicarbonate'}, {'name': 'Calcium carbonate'}])] == [
        'Sodium alginate', 'Sodium bicarbonate', 'Calcium carbonate']
    assert _names(extract.clean_apis([{'name': 'Vitamin B1 (Thiamine nitrate) 100 mg'}, {'name': 'Vitamin B6 200 mg'}, {'name': 'Vitamin B12 200 mcg'}])) == [
        ('Vitamin B1', '100 mg'), ('Vitamin B6', '200 mg'), ('Vitamin B12', '200 mcg')]
    # one substance printed several ways is still one entry; fragments are not substances
    one = extract.clean_apis([{'name': 'NEOMYCIN SULPHATE 3.500 mg (3300 unit)'}, {'name': 'Neomycin sulfate', 'manufacturer': 'Sichuan Example'}, {'name': 'Neomycin'},
                              {'name': '500 mg Paracetamol'}, {'name': 'Paracetamol'}, {'name': 'Sodium'}, {'name': 'HCl BP'}])
    assert _names(one) == [('Neomycin Sulphate', '3.500 mg (3300 unit)'), ('Paracetamol', '500 mg')] and one[0]['manufacturer'] == 'Sichuan Example'
    # a vitamin and its ester are one substance («vitamin a» is a name of its own), in either order; the letter still tells B1 from B12
    assert _names(extract.clean_apis([{'name': 'Vitamin A palmitate', 'strength': '5000 IU'}, {'name': 'Vitamin A (as palmitate) 5000 IU'}])) == [('Vitamin A palmitate', '5000 IU')]
    assert _names(extract.clean_apis([{'name': 'Vitamin A (as palmitate) 5000 IU'}, {'name': 'Vitamin A palmitate', 'strength': '5000 IU'}])) == [('Vitamin A palmitate', '5000 IU')]
    assert _names(extract.clean_apis([{'name': 'Vitamin E nicotinate', 'strength': '100 mg'}, {'name': 'Vitamin E (as nicotinate) 100 mg'}])) == [('Vitamin E nicotinate', '100 mg')]
    assert [a['name'] for a in extract.clean_apis([{'name': 'Vitamin B1'}, {'name': 'Vitamin B12'}, {'name': 'Vitamin B'}])] == ['Vitamin B1', 'Vitamin B12', 'Vitamin B']


def test_ordinary_text_is_not_an_active_substance():
    t = '\n'.join(['Certificate of Pharmaceutical Product', 'Trade name: Cardiolol 10 mg',
                   'Active ingredient: Bisoprolol fumarate, manufactured by Unichem Laboratories, India'])
    assert [a['name'] for a in extract.fields_for('cpp', 'cpp.pdf', t)['apis']] == ['Bisoprolol fumarate']
    t = '\n'.join(['Specification', 'Active ingredients: Neomycin sulphate and Bacitracin zinc / Packaging'])
    assert [a['name'] for a in extract.fields_for('spec', 'spec.pdf', t)['apis']] == ['Neomycin sulphate', 'Bacitracin zinc']
    for junk in ('Manufactured by Dermacure Pharma', 'Packaging', 'Batches', 'Certificates of analysis', 'Validity', 'India'):
        assert not extract.plausible_api(junk), junk
    assert [a['name'] for a in extract.clean_apis([{'name': 'Co-trimoxazole 480 mg'}, {'name': 'Calcium 500 mg'}, {'name': 'Zinc', 'strength': '10 mg'}, {'name': 'Zinc'}])] == [
        'Co-trimoxazole', 'Calcium', 'Zinc']                                                       # a BAN «Co-» name is not a company; a dosed metal is a substance


def test_eda_form_reads_substances_whose_names_carry_digits():
    lic = ['Final Registration License', 'Trade Name: Neurocure', 'Dosage Form: Film coated tablet', 'Active Ingredient(s) & Each tablet contains:',
           'Strength(s): Vitamin B1 100 mg', 'Vitamin B6 200 mg', 'Vitamin B12 200 mcg', 'Registration No.: 1234/2024']
    f = extract.fields_for('licence', 'lic.txt', '\n'.join(lic))
    assert _names(f['apis']) == [('Vitamin B1', '100 mg'), ('Vitamin B6', '200 mg'), ('Vitamin B12', '200 mcg')]
    got, _ = intake_eda.actives(['Calcium carbonate 1250 mg', 'Cholecalciferol (Vitamin D3) 400 IU'])
    assert [(a['name'], a['strength']) for a in got] == [('Calcium carbonate', '1250 mg'), ('Cholecalciferol', '400 iu')]
    ors = ['Final Registration License', 'Trade Name: Rehydra', 'Dosage Form: Powder for oral solution', 'Active Ingredient(s) & Each sachet contains:',
           'Strength(s): Sodium chloride 2.6 g', 'Potassium chloride 1.5 g', 'Sodium citrate 2.9 g', 'Glucose anhydrous 13.5 g', 'Registration No.: 1235/2024']
    assert [a['name'] for a in extract.fields_for('licence', 'ors.txt', '\n'.join(ors))['apis']] == ['Sodium chloride', 'Potassium chloride', 'Sodium citrate', 'Glucose anhydrous']


TWO_APIS = dict(dossier_kind='generic', origin='local', licence='own', activity='new', admin_route='topical',
                apis=[dict(name='Neomycin sulphate', manufacturer='Sichuan Example Pharmaceutical', option='CEP'),
                      dict(name='Bacitracin zinc', manufacturer='North Example Pharmaceutical', option='CEP')])


def test_kind_home_never_moves_a_document_to_another_apis_item(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=TWO_APIS, product=dict(name='Dermacure', dosageform='topical powder', manufacturer='Example'),
                                            envelope={}), headers=H).json()['id']
    cep = ('Certificate of suitability to the monographs of the European Pharmacopoeia\nR1-CEP 2015-123-Rev 02\nSubstance: Bacitracin zinc\n'
           'Holder: North Example Pharmaceutical Huasheng Co. Ltd, China\nEDQM')
    coa = 'Certificate of Analysis\nBacitracin zinc BP\nBatch No: BZ2401\nManufacturer: North Example Pharmaceutical Huasheng Co. Ltd'
    lic = 'Final Registration License\nTrade Name: Dermacure'
    r = c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': 'cep bacitracin.pdf', 'text': cep, 'kind': 'cep'},
                                                                      {'filename': 'coa bacitracin.pdf', 'text': coa, 'kind': 'coa'},
                                                                      {'filename': 'scan.pdf', 'text': lic}]}, headers=H).json()
    best = [x['suggestions'][0]['slot_id'] for x in r]
    assert best[0] == 'M1-39@Bacitracin zinc|North Example Pharmaceutical' and best[1] == 'M1-35@Bacitracin zinc|North Example Pharmaceutical'
    assert best[2] == 'M1-04' and r[2]['kind'] == 'licence'
    unnamed = 'Certificate of suitability\nR1-CEP 2016-001-Rev 00\nEDQM'                              # names neither API: no guess between their items
    r = c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': 'x.pdf', 'text': unnamed, 'kind': 'cep'}]}, headers=H).json()[0]
    assert r['auto'] is None and len({x['slot_id'] for x in r['suggestions'][:2]}) == 2 and r['suggestions'][0]['score'] == r['suggestions'][1]['score']   # the page leaves it in the box
    # both actives from ONE manufacturer: the substance the document names decides, never the alphabetical order of the items
    same = dict(TWO_APIS, apis=[dict(a, manufacturer='Sichuan Example Pharmaceutical') for a in TWO_APIS['apis']])
    did2 = c.post('/api/dossiers', json=dict(name='Dermacure 2', profile=same, product=dict(name='Dermacure', dosageform='topical powder', manufacturer='Example'),
                                             envelope={}), headers=H).json()['id']
    cep_n = 'Certificate of suitability\nR1-CEP 2015-123-Rev 02\nSubstance: Neomycin sulphate\nHolder: Sichuan Example Pharmaceutical Co. Ltd, China\nEDQM'
    coa_n = 'Certificate of Analysis\nNeomycin sulphate BP\nBatch No: NS2401\nManufacturer: Sichuan Example Pharmaceutical Co. Ltd'
    r = c.post(f'/api/dossiers/{did2}/classify/text', json={'files': [{'filename': 'cep neomycin.pdf', 'text': cep_n, 'kind': 'cep'}, {'filename': 'coa neomycin.pdf', 'text': coa_n, 'kind': 'coa'},
                                                                       {'filename': 'x.pdf', 'text': unnamed, 'kind': 'cep'}]}, headers=H).json()
    assert [x['auto'] for x in r] == ['M1-39@Neomycin sulphate|Sichuan Example Pharmaceutical', 'M1-35@Neomycin sulphate|Sichuan Example Pharmaceutical', None]
    one = dict(TWO_APIS, apis=TWO_APIS['apis'][:1])                                                     # one active: the unnamed CEP has only one home
    did3 = c.post('/api/dossiers', json=dict(name='Dermacure 3', profile=one, product=dict(name='Dermacure', dosageform='topical powder', manufacturer='Example'),
                                             envelope={}), headers=H).json()['id']
    r = c.post(f'/api/dossiers/{did3}/classify/text', json={'files': [{'filename': 'x.pdf', 'text': unnamed, 'kind': 'cep'}]}, headers=H).json()[0]
    assert r['auto'] == 'M1-39@Neomycin sulphate|Sichuan Example Pharmaceutical'


PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True,
               dosage_specifics=['coated'], apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
PRODUCT = dict(name='Dermacure 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma', indication='pain-and-fever')
ENV = dict(tracking='P-MAA-0001', applicant='Example Pharma S.A.E.', invented_name='Dermacure 500 mg film-coated tablets',
           inn=['paracetamol'], description='Initial MAA', portal_id='EXAMPLE-0001')


def test_a_leaflet_placed_or_moved_into_its_item_carries_its_details_and_exports(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV), headers=H).json()['id']
    pdf = make_pdf(tmp_path / 'doc.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started' and s['req_id'] != 'M1-09':
            meta = {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {}
            assert c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                          data={'meta': json.dumps(meta)}, headers=H).status_code == 201, s['slot_id']
    leaflet = make_pdf_lines(tmp_path / 'leaflet.pdf', ['Summary of Product Characteristics', 'Dermacure 500 mg film-coated tablets'], 'SmPC').read_bytes()
    c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('leaflet.pdf', io.BytesIO(leaflet), 'application/pdf'))], data={'meta': '{}'}, headers=H)
    doc = c.get(f'/api/dossiers/{did}/unplaced', headers=H).json()[0]
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/place", json={'slot_id': 'M1-09'}, headers=H)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-META' and r.json()['detail']['ar']      # without the details: refused, nothing moves
    r = c.post(f"/api/dossiers/{did}/documents/{doc['id']}/place", json={'slot_id': 'M1-09', 'meta': {'pi_type': 'spc', 'lang': 'en'}}, headers=H)
    assert r.status_code == 200 and r.json()['meta']['pi_type'] == 'spc' and r.json()['meta']['lang'] == 'en'
    # the kind rule's «move» into the leaflet item asks for the same details
    other = c.post(f"/api/dossiers/{did}/slots/M1-05/documents", files={'file': ('smpc.pdf', io.BytesIO(leaflet), 'application/pdf')}, data={'meta': '{}'}, headers=H).json()
    mv = c.post(f"/api/dossiers/{did}/documents/{other['id']}/move", json={'slot_id': 'M1-09'}, headers=H)
    assert mv.status_code == 422 and mv.json()['detail']['code'] == 'E-META'
    mv = c.post(f"/api/dossiers/{did}/documents/{other['id']}/move", json={'slot_id': 'M1-09', 'meta': {'pi_type': 'pl', 'lang': 'ar'}}, headers=H)
    assert mv.status_code == 200 and mv.json()['meta']['pi_type'] == 'pl'
    ex = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True}, headers=H)
    assert ex.status_code == 201, ex.text                                                                # before the fix: E-WRITER «1.3.1 needs pi_type and lang»
