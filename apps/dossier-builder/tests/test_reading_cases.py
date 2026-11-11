"""Cases from the logic review (November 2026): what a document says it is (the kind rule), which names are active substances,
where a file goes after the dossier is created, and the «not placed yet» box. All texts are made up (the product is «Dermacure»)."""
import json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine import extract as X
from dossier_engine.app.api import create_app

STAB_EN = 'Stability Study Report\nProduct: Dermacure 500 mg film coated tablets\nStorage condition: 30 C / 65 % RH\nTime points: 0, 3, 6, 9, 12 months\nConclusion: the product is stable'
PRICE_EN = 'Egyptian Drug Authority\nPricing Certificate\nTrade name: Dermacure 500 mg film coated tablets\nPack: 20 film coated tablets\nPublic price: 45.00 EGP'
PRICE_AR = 'هيئة الدواء المصرية\nشهادة تسعير مستحضر\nبالإشارة إلى إخطار التسجيل رقم 12345 بتاريخ 2024/01/15\nاسم المستحضر: ديرماكيور 500 مجم أقراص\nسعر الجمهور: 45 جنيها'
STAB_AR = 'هيئة الدواء المصرية\nالإدارة العامة للثبات\nموافقة ثبات\nاسم المستحضر: ديرماكيور 500 مجم أقراص\nتمت الموافقة على دراسة الثبات المقدمة ومدة الصلاحية 24 شهرا'
STAB_APPROVAL_EN = 'Egyptian Drug Authority\nStability Approval\nProduct: Dermacure 500 mg tablets\nThe submitted stability study is approved. Shelf life: 24 months'
COA_FP = 'Certificate of Analysis\nProduct: Dermacure 500 mg film coated tablets\nBatch No.: 240101\nTest | Specification | Result\nAssay | 95.0 - 105.0 % | 99.6 %\nDissolution | NLT 80 % | 92 %'
CONTRACT = 'Toll Manufacturing Agreement\nThis agreement is made between Example Pharma S.A.E. (the licence holder) and Dermacure Industries (the manufacturer).\nThe manufacturer shall hold a valid manufacturing licence and a GMP certificate.'
SMPC = 'SUMMARY OF PRODUCT CHARACTERISTICS\n1. NAME OF THE MEDICINAL PRODUCT\nDermacure 500 mg film-coated tablets\n2. QUALITATIVE AND QUANTITATIVE COMPOSITION\nEach film-coated tablet contains 500 mg paracetamol\n4.1 Therapeutic indications\n6.3 Shelf life\n24 months\n6.4 Special precautions for storage'
GMP = 'CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER\nPart 1\nIssued following an inspection in accordance with national law.\nThe competent authority confirms the following: the manufacturer Example Pharma, manufacturing licence no. 1234, has been inspected.'
CPP = 'Certificate of a Pharmaceutical Product\nThis certificate conforms to the format recommended by the World Health Organization\nName and dosage form of the product: Dermacure 500 mg film coated tablets\nIs this product licensed to be placed on the market for use in the exporting country? yes'
NOTIF_AR = 'هيئة الدواء المصرية\nإخطار تسجيل مستحضر صيدلي بشري\nرقم التسجيل: 12345\nاسم المستحضر: ديرماكيور 500 مجم أقراص\nسعر الجمهور: 45 جنيها\nمدة الصلاحية: 24 شهرا\nالتركيب: كل قرص يحتوي على باراسيتامول 500 مجم'
COMP = 'Composition Certificate\nProduct: Dermacure 500 mg film coated tablets\nEach film coated tablet contains:\nParacetamol 500 mg\nExcipients: starch, povidone, magnesium stearate'


@pytest.mark.parametrize('req,text,ok', [
    ('M1-05', PRICE_EN, True),             # a pricing certificate of a coated product («coa» is not the start of «coated»)
    ('M1-05', PRICE_AR, True),             # it cites the registration notification by its number: still a pricing letter
    ('M1-05', STAB_AR, False),             # the owner's case: an Arabic stability approval in the pricing item
    ('M1-05', STAB_APPROVAL_EN, False),
    ('M1-05', COA_FP, False),
    ('M1-37', PRICE_EN, False),
    ('P-11', COA_FP, True),
    ('M1-24', CONTRACT, True),             # «the licence holder» in a contract does not make it a licence
    ('M1-09', SMPC, True),                 # «composition», «shelf life» and «storage» are sections of a leaflet
    ('M1-37', GMP, True),
    ('M1-14', CPP, True),
    ('M1-04', NOTIF_AR, True),             # a notification states the price and the shelf life as fields
    ('M1-31', COMP, True),
])
def test_kind_rule_judges_a_document_by_its_title(req, text, ok):
    assert X.kind_check(req, 'document.pdf', text)['ok'] is ok


def test_kind_names():
    assert X.guess_kind('study.pdf', STAB_EN) == 'stability'
    assert X.guess_kind('document.pdf', PRICE_EN) == 'pricing'
    assert X.guess_kind('document.pdf', COA_FP) == 'coa'


def names(lst):
    return [a['name'] for a in X.clean_apis(lst)]


@pytest.mark.parametrize('lst,n', [
    (['Vitamin B1', 'Vitamin B12', 'Vitamin B6'], 3),
    (['Salicylic acid', 'Acetylsalicylic acid'], 2),
    (['Sodium chloride', 'Potassium chloride'], 2),
    (['Hydrocortisone', 'Cortisone'], 2),
    (['Chlorpheniramine maleate', 'Pheniramine maleate'], 2),
    (['Neomycin sulphate', 'Polymyxin B sulphate', 'Bacitracin zinc'], 3),
    (['Vitamin D3', 'Coenzyme Q10', 'Omega-3 fatty acids'], 3),
    (['Amoxicillin trihydrate', 'Clavulanate potassium'], 2),
    (['Metformin HCl', 'Metformin Hydrochloride', 'Metformin hydrochloride BP'], 1),
    (['Paracetamol', 'Paracetamol 500 mg', 'PARACETAMOL'], 1),
    (['Bacitracin Zinc', 'Bactiracin Zinc'], 1),                                   # two letters swapped by the typist
    (['Each tablet contains', 'Manufacturer', 'Manufactured by Example Pharma', 'Packaging', 'Composition', 'Active ingredients', 'Excipients q.s.',
      'Storage conditions', 'Shelf life 24 months', 'Product name', 'Batch number'], 0),
    (['Quantity', 'Specification', 'White homogenous powder', 'White opaque plastic', 'Transparent pale pink solution', 'Topical powder', 'Powder for cutaneous use',
      'in human milk', 'Not relevant', 'No data', 'Not applicable', 'Posology', 'Method of administration', 'Pregnancy and lactation', 'Symptoms and signs',
      'Dermacure Powder should not be diluted'], 0),                                # table headings, appearances, the tail of a sentence, section titles
])
def test_active_substances_count(lst, n):
    assert len(X.clean_apis(lst)) == n, names(lst)


def test_active_substances_details():
    assert all(len(X.clean_apis([x])) == 1 for x in ['Sodium chloride', 'Calcium carbonate', 'Magnesium sulfate', 'Sodium bicarbonate', 'Zinc sulfate', 'Potassium citrate'])
    out = X.clean_apis([{'name': 'Neomycin sulphate 3.5 mg'}, {'name': 'NEOMYCIN SULPHATE'}, {'name': 'Polymyxin B sulphate 5000 IU'}])
    assert [(a['name'].lower().split()[0], a['strength']) for a in out] == [('neomycin', '3.5 mg'), ('polymyxin', '5000 IU')]
    assert [x.lower() for x in names(['Egypt', 'Example Pharma S.A.E.', 'Paracetamol'])] == ['paracetamol']
    assert 'sodium' in names(['Diclofenac sodium'])[0].lower()
    assert names(['Iron (III) hydroxide polymaltose complex']) == ['Iron (III) hydroxide polymaltose complex']
    assert names(['Paracetamol (micronised) granules']) == ['Paracetamol granules']
    one = X.clean_apis(['Amoxicillin (as trihydrate) 500 mg'])
    assert len(one) == 1 and one[0]['name'] == 'Amoxicillin' and '500' in one[0]['strength']
    assert names(['كل قرص يحتوي على', 'باراسيتامول']) == ['باراسيتامول']
    assert names(['threonine. Neomycin sulphate']) == ['threonine', 'Neomycin sulphate']       # two names glued by a full stop


# ---- where a file goes after the dossier is created
PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True, dosage_specifics=['coated'],
               apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP'), dict(name='Caffeine', manufacturer='Shandong Xinhua', option='DMF')])
PRODUCT = dict(name='Dermacure 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma', indication='pain-and-fever')
ENV = dict(tracking='P-MAA-0001', applicant='Example Pharma S.A.E.', invented_name='Dermacure 500 mg film-coated tablets', inn=['paracetamol', 'caffeine'],
           description='Initial MAA', portal_id='EXAMPLE-0001')


@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    slots = {s['slot_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    return c, did, slots


def auto(dossier, filename, text):
    c, did, slots = dossier
    r = c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': filename, 'text': text}]}).json()[0]
    return slots.get(r['auto']) if r['auto'] else None


def test_a_file_goes_to_the_item_of_the_substance_it_names(dossier):
    s = auto(dossier, 'coa.pdf', 'Certificate of Analysis\nProduct: Caffeine anhydrous\nManufacturer: Shandong Xinhua\nBatch No. 123\nAssay 99.8 %')
    assert s['item']['name'] == 'Caffeine'
    s = auto(dossier, 'certificate.pdf', 'Certificate of Analysis\nMaterial: Caffeine anhydrous BP\nBatch No. 77\nAssay 99.8 %')
    assert s['item']['name'] == 'Caffeine'                                         # the manufacturer is not printed: the substance decides
    s = auto(dossier, 'cep.pdf', 'Certificate of Suitability\nR1-CEP 2001-123-Rev 02\nName of the substance: Paracetamol\nHolder: Granules India')
    assert s['item']['name'] == 'Paracetamol' and s['req_id'] in ('M1-39', 'S-16')
    assert auto(dossier, 'certificate.pdf', 'Certificate of Analysis\nBatch No. 77\nAssay 99.8 %') is None      # names neither active: the user decides


def test_product_documents_go_to_the_product_items(dossier):
    assert auto(dossier, 'smpc.pdf', SMPC)['req_id'] == 'M1-09'                    # the product's leaflet, not the reference product's
    assert auto(dossier, 'composition certificate.pdf', COMP)['req_id'] == 'M1-31'
    assert auto(dossier, 'price.pdf', PRICE_EN)['req_id'] == 'M1-05'
    s = auto(dossier, 'coa finished product.pdf', COA_FP)
    assert s['req_id'] == 'P-11' and s['item'] is None                              # it names the product and none of its actives


# ---- the «not placed yet» box
def staged(dossier, tmp_path, name, text, kind):
    c, did, _ = dossier
    pdf = make_pdf(tmp_path / name, 'Scanned page').read_bytes()
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', (name, pdf, 'application/pdf'))], data={'meta': json.dumps({name: {'kind': kind, 'text': text}})})
    assert r.status_code == 201, r.text
    return r.json()[0]


def test_placing_from_the_box(dossier, tmp_path):
    c, did, _ = dossier
    d = staged(dossier, tmp_path, 'scan 0007.pdf', PRICE_EN, 'pricing')
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/place", json={'slot_id': 'M1-05'})
    assert r.status_code == 200 and r.json()['title'] == 'Pricing Certificate'      # the item's title, not «scan 0007.pdf» (it becomes the eCTD leaf title)
    assert not any(f['rule'] == 'DOC-KIND' for f in r.json()['findings'])
    # a scan has no text of its own: the reading the wizard made of it (browser OCR) still decides whether it is the right document
    d = staged(dossier, tmp_path, 'approval.pdf', STAB_AR, 'stability')
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/place", json={'slot_id': 'M1-05'})
    assert r.status_code == 200 and any(f['rule'] == 'DOC-KIND' and f['severity'] == 'block' for f in r.json()['findings'])
    # the leaflet item needs the leaflet's type and language (the eCTD writers do): asked for, then stored
    d = staged(dossier, tmp_path, 'leaflet en.pdf', SMPC, 'smpc')
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/place", json={'slot_id': 'M1-09'})
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-META'
    r = c.post(f"/api/dossiers/{did}/documents/{d['id']}/place", json={'slot_id': 'M1-09', 'meta': {'pi_type': 'spc', 'lang': 'en'}})
    assert r.status_code == 200 and r.json()['meta']['pi_type'] == 'spc'


# ---- a document is known by what is written inside it, never by the name of its file
def test_the_kind_comes_from_inside_the_file_never_from_its_name(dossier, tmp_path):
    assert X.kind_check('M1-05', 'stability approval.pdf', PRICE_EN)['ok']            # the name lies: inside it is a pricing certificate
    assert not X.kind_check('M1-05', 'pricing certificate.pdf', STAB_AR)['ok']        # the name says pricing: inside it is a stability approval
    r = X.kind_check('M1-37', 'pricing certificate.pdf', '')
    assert r['ok'] and r['kind'] == 'other' and r['unread']                           # nothing could be read: nothing is judged, least of all by the name
    f = X.read_texts([{'filename': 'gmp certificate.pdf', 'text': ''}])['files'][0]
    assert f['kind'] == 'other' and f['kind_hint'] == 'gmp'                           # the name only hints where to offer the file
    f = X.read_texts([{'filename': 'gmp certificate.pdf', 'text': PRICE_EN}])['files'][0]
    assert f['kind'] == 'pricing' and f['kind_hint'] is None
    c, did, _ = dossier
    r = c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': 'pricing certificate.pdf', 'text': ''}]}).json()[0]
    assert r['auto'] is None and r['suggestions'][0]['req_id'] == 'M1-05'             # offered there, never placed on its name alone
    r = c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': 'gmp certificate.pdf', 'text': PRICE_EN}]}).json()[0]
    assert r['kind'] == 'pricing' and r['auto'] == 'M1-05'                            # what is written inside decides


def test_an_upload_is_judged_by_the_reading_that_comes_with_it(dossier, tmp_path):
    c, did, _ = dossier
    pdf = make_pdf(tmp_path / 'scan.pdf', 'Scanned page of a certificate').read_bytes()
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pricing certificate.pdf', pdf, 'application/pdf')},
               data={'meta': json.dumps({'text': STAB_AR})})
    assert r.status_code == 201, r.text
    assert any(f['rule'] == 'DOC-KIND' and f['severity'] == 'block' for f in r.json()['findings']) and 'text' not in r.json()['meta']
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('stability approval.pdf', pdf, 'application/pdf')},
               data={'meta': json.dumps({'text': PRICE_EN})})
    assert not any(f['rule'] == 'DOC-KIND' for f in r.json()['findings'])             # a pricing certificate under a misleading file name is accepted
