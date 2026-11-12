"""What a real product's trial found (November 2026), kept as tests on fictional documents:
a file is read once; a document's kind and place follow what it says; what the product IS comes from the documents that state it,
never from a word in a method; tables are read as tables; a working copy can be exported at any time."""
import io, json, zipfile
import pytest
from docx import Document
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import extract, intake_eda, msdoc, packs
from dossier_engine.app.api import create_app

PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='re_registration',
               apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='FULL'), dict(name='Bacitracin zinc', manufacturer='Other API Ltd', option='FULL')])
PRODUCT = dict(name='Dermacure', dosageform='Cutaneous powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin', 'bacitracin'])

LICENCE = """Arab Republic of Egypt
Egyptian Drug Authority
Final Registration License for Pharmaceutical Product
| Trade Name: |DERMACURE درماكيور
| Dosage Form: |Topical powder مسحوق للاستعمال الخارجي
Active Ingredient(s) & Each 1 g contains:
Strength(s): NEOMYCIN SULPHATE 3.500 mg
0 gett 24 كلت ZINC 4.200 mg 1 1 3
Physical Character: | White homogenous powder
Shelf Life: [24 Months 1
Storage Condition: |Store at temperature not exceeding 30°C, in a dry place
Approved Pack: Carton box containing a bottle of 20 g powder
Price: |18 L.E. / bottle
| Type of License: \\Toll | Type of Marketing: |Local
Registration No.: 12345/2021 Invalidation Date: 09-12-2031
| License Holder : |EXAMPLE PHARM-EGYPT,EGYPT
| Manufacturer : 1 8 0 دح International for Dermatology Products,EGYPT
Storage Site: Samplex International for Dermatology Products,EGYPT
Manufacturer Of active substance: For NEOMYCIN SULPHATE: 1
| Example API Co,INDIA
For BACITRACIN ZINC:
| Other API Ltd,CHINA
"""
METHOD = """MONOGRAPH
Title: | Dermacure Topical Powder
Document number: | MON-PRD-0001
OBJECTIVE:
To provide an in-house monograph for analysis of Dermacure Topical Powder
Calculate the weight variation for each tablet as per the formula.
Wash each filter with sterile peptone water. Injection volume 20 µl. Strength of the standard solution 363.7 mg per litre.
Assay of Neomycin sulfate: dilute with 5 % methanol.
"""
PRINTOUT = """=====================================================================
Acq. Operator   : admin                          Seq. Line :   1
Acq. Instrument : HPLC                            Location : P1-A-01
Injection Date  : 14/06/2023 09:46:48                  Inj :   1
Inj Volume : 20.000 µl
Sample Name : Dermacure assay sterile filtered
"""


def docx_bytes(build):
    d = Document()
    build(d)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def table(d, rows):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            t.cell(i, j).text = v


COA = docx_bytes(lambda d: (d.add_paragraph('CERTIFICATE OF ANALYSIS'), table(d, [['Product name : Dermacure Topical powder', 'Batch No. : DC23008'], ['Mfg. date : 06/2023', 'Analysis Date : 09/07/2025'], ['Exp. date : 06/2026', '']]),
                           d.add_paragraph('Batch Weight 50 kg'),
                           table(d, [['TEST', 'SPECIFICATION', 'RESULT'], ['Description', 'White homogenous powder', 'Conform'], ['Water content', 'Not more than 5.0 %', '0.39%'],
                                     ['1- Identification for\nA- neomycin sulphate\nB- bacitracin zinc', 'The retention time matches the standard', 'Positive'],
                                     ['Assay of neomycin sulphate', '90 – 110 % of the labeled amount', '98.25 %'], ['Assay of bacitracin zinc', '90 – 110 % of the labeled amount', '99.16 %']])))
SPEC = docx_bytes(lambda d: (d.add_paragraph('Specifications of Dermacure Topical powder'),
                            table(d, [['TEST', 'SPECIFICATION', 'Method of analysis', 'Reference'], ['Description', 'White homogenous powder', 'Visual', 'In-House'],
                                      ['Water content', 'Not more than 5.0 %', 'Karl Fischer', 'USP'], ['Assay of neomycin sulphate', '90 – 110 % of the labeled amount', 'HPLC', 'In-House']])))


# ---------------- a file is read once
def test_a_file_is_read_once_and_a_scan_is_said_to_be_one(tmp_path, monkeypatch):
    calls = []
    real = extract._read_text

    def counted(name, data, max_pages=12):
        calls.append(name)
        if data.startswith(b'SCAN'):
            return {'pages': 2, 'text': '', 'scanned': True, 'kind_of_file': 'pdf', 'arabic': False}
        return real(name, data, max_pages)

    monkeypatch.setattr(extract, '_read_text', counted)
    monkeypatch.setattr(extract, 'READ_DIR', tmp_path / 'cache')
    extract._READ.clear()
    pdf = make_pdf_lines(tmp_path / 'a.pdf', ['Certificate of Analysis', 'Assay 99.8 %']).read_bytes()
    a = extract.read_text('a.pdf', pdf)
    b = extract.read_text('a.pdf', pdf)
    assert a == b and calls == ['a.pdf'] and 'Certificate of Analysis' in a['text']
    scan = b'SCAN of a licence'
    r = extract.read_text('scan.pdf', scan)
    assert r['text'] == '' and r['scanned'] and 'ocr' not in r                     # no OCR: a scan is said to be one, nothing is guessed
    assert extract.has_text('scan.pdf', scan) == 'scan' and extract.has_text('a.pdf', pdf) is None
    assert calls == ['a.pdf', 'scan.pdf']                                           # the gate's question is answered from the same reading


def test_a_reading_of_the_first_pages_is_not_taken_for_the_whole_file(tmp_path, monkeypatch):
    asked = []

    def fake(name, data, max_pages=12):
        asked.append(max_pages)
        return {'pages': 6, 'text': ' '.join(f'page-{i + 1} of the stability study report' for i in range(min(6, max_pages))), 'scanned': False, 'kind_of_file': 'pdf', 'arabic': False}

    monkeypatch.setattr(extract, '_read_text', fake)
    monkeypatch.setattr(extract, 'READ_DIR', tmp_path / 'cache')
    doc = b'%PDF-1.7 six pages'
    one = extract.read_text('s.pdf', doc, max_pages=1)['text']                     # the kind rule reads the first page
    assert 'page-1' in one and 'page-2' not in one
    whole = extract.read_text('s.pdf', doc)['text']                                # the reader's usual pages: read again, not the first page's answer
    assert 'page-6' in whole and asked == [1, 12]
    assert extract.read_text('s.pdf', doc)['text'] == whole and asked == [1, 12]   # asked again the same way: the kept reading


def test_a_reading_kept_by_an_older_reader_is_made_again(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, 'READ_DIR', tmp_path / 'cache')
    pdf = b'%PDF-1.7 ' + b'x' * 250000                                              # a large file: its reading is kept on disk
    monkeypatch.setattr(extract, '_read_text', lambda *a, **k: {'pages': 1, 'text': 'the old reader', 'scanned': False, 'kind_of_file': 'pdf', 'arabic': False})
    assert extract.read_text('big.pdf', pdf)['text'] == 'the old reader'
    extract._READ.clear()
    monkeypatch.setattr(extract, '_read_text', lambda *a, **k: {'pages': 1, 'text': 'the new reader', 'scanned': False, 'kind_of_file': 'pdf', 'arabic': False})
    assert extract.read_text('big.pdf', pdf)['text'] == 'the old reader'      # the same reader: its reading is kept across a restart
    extract._READ.clear()
    monkeypatch.setattr(extract, 'READ_FORMAT', extract.READ_FORMAT + 1)       # a newer reader does not trust it
    assert extract.read_text('big.pdf', pdf)['text'] == 'the new reader'


# ---------------- what a document is
@pytest.mark.parametrize('text, kind', [
    (METHOD, 'method'), (PRINTOUT, 'validation'),
    ('Analytical Method Validation\nNeomycin in Dermacure\nTopical Powder\n4. Method description:', 'validation'),
    ('STABILITY INDICATING ASSAY\n(Forced degradation using Acid, Base, Hydrogen peroxide, Light and Heat)\nOf\nNeomycin in Dermacure', 'validation'),
    ('Arab Republic of Egypt\nAppeal/Request Decision Letter\nProduct Name: Dermacure\nبشأن إلتماس سيادتكم عن إمكانية تعديل Finished product specification المرفقة بموافقة الثبات\nعلى الإدارة العامة للثبات', 'stability'),
    ('جمهورية مصر العربية\nهيئة الدواء المصرية\nالموافقة المبدئية على تغيير بيان التركيب للمستحضر\nTrade Name: Dermacure', 'variation'),
    ('Specifications of Dermacure Topical powder\nTEST | SPECIFICATION | Method of analysis', 'spec'),
    (LICENCE + '\nدراسة الثبات المعجلة ... موافقة الثبات', 'licence'),
])
def test_a_document_says_what_it_is(text, kind):
    assert extract.content_kind(text) == kind


def test_the_home_of_a_kind_follows_what_the_document_is_about():
    pk = packs.load('eda.ctd.nta065.v5')
    coa_product = 'CERTIFICATE OF ANALYSIS\nProduct name : Dermacure Topical powder | Batch No. : DC23008\nAssay of neomycin sulphate 98 %'
    coa_api = 'Certificate of Analysis\nMaterial: Neomycin sulphate BP\nBatch No. 77\nAssay 99.8 %'
    assert extract.kind_homes('coa', pk, coa_product, 'Dermacure')[0] == 'P-11'          # it names the product at its top: the product's batch analyses
    assert extract.kind_homes('coa', pk, coa_api, 'Dermacure')[0] == 'M1-35'             # a supplier's certificate
    assert extract.kind_homes('spec', pk, 'Specifications of Dermacure Topical powder', 'Dermacure')[0] == 'P-09'
    assert extract.kind_homes('spec', pk, 'Specification of Neomycin sulphate BP', 'Dermacure')[0] == 'M1-36'
    assert extract.kind_homes('stability', pk, 'Egyptian Drug Authority\nStability Study Approval', 'Dermacure')[0] == 'M1-34'
    assert extract.kind_homes('stability', pk, 'Stability study report of Dermacure\nLong term 30/65', 'Dermacure')[0] == 'P-16'
    assert extract.kind_homes('stability', pk, 'Stability data of Neomycin sulphate\nRetest period 36 months', 'Dermacure', substances=['neomycin'])[0] == 'S-14'
    assert extract.kind_homes('stability', pk, 'Egyptian Drug Authority\nStability Study Approval', 'Dermacure')[:2] == ['M1-34', 'P-16']     # where the approvals item does not apply: 3.2.P.8, never a substance's
    assert extract.kind_homes('method', pk)[0] == 'P-10' and extract.kind_homes('validation', pk)[0] == 'P-10' and extract.kind_homes('receipt', pk) == ['M1-03']
    ok = lambda req, text: extract.kind_check(req, 'x.pdf', text, pack=pk)['ok']
    assert ok('P-10', METHOD) and ok('P-09', METHOD)                                     # a specification with its methods: any of their items takes it
    assert not ok('M1-05', METHOD) and not ok('M1-05', PRINTOUT)                         # never the pricing certificate's


# ---------------- where a file goes
@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, did


def place(dossier, name, text):
    c, did = dossier
    return c.post(f'/api/dossiers/{did}/classify/text', json={'files': [{'filename': name, 'text': text}]}).json()[0]


def test_documents_go_to_their_own_items_and_nothing_is_placed_on_a_guess(dossier):
    assert place(dossier, 'scan-01.doc', METHOD)['auto'] == 'P-10'                       # the method of analysis: 3.2.P.5.2
    assert place(dossier, 'data.pdf', PRINTOUT)['auto'] == 'P-10'                        # chromatograms: 3.2.P.5.3 — not an active substance's stability
    coa = extract.docx_text(COA)
    r = place(dossier, 'coa.docx', coa)
    assert r['kind'] == 'coa' and r['auto'] == 'P-11', r                                 # it names both actives in its tests, and the product at its top
    r = place(dossier, 'neomycin.pdf', 'Certificate of Analysis\nMaterial: Neomycin sulphate BP\nBatch No. 77\nAssay 99.8 %')
    assert r['auto'].startswith('M1-35@Neomycin')                                        # a supplier's certificate: the substance it names
    r = place(dossier, 'notes about validation of the process.pdf', 'Minutes of the meeting held on Monday about the process and its validation plan for next year.')
    assert r['auto'] is None                                                             # a few keywords are a suggestion, not a place


def test_a_fixed_copy_keeps_the_verdict_of_its_document(dossier, tmp_path):
    c, did = dossier
    from dossier_engine.app.store import Store
    gmp = make_pdf_lines(tmp_path / 'g.pdf', ['CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER', 'Example Pharm Co. complies with Good Manufacturing Practice']).read_bytes()
    r = c.post(f'/api/dossiers/{did}/slots/M1-37/documents', files={'file': ('gmp.pdf', io.BytesIO(gmp), 'application/pdf')}, data={'meta': '{}'}).json()
    assert not any(f['rule'] == 'DOC-KIND' for f in r['findings'])
    other = make_pdf_lines(tmp_path / 'h.pdf', ['Stability study report', 'Long term 30/65', 'stability stability stability']).read_bytes()
    st = c.app.state.store if hasattr(c.app.state, 'store') else Store(tmp_path / 'ws')
    new = st.add_document(did, 'M1-37', 'gmp.pdf', other, meta={'fixed_from': r['id'], 'fixes': ['pdf_version_normalise']}, supersede=r['id'])
    assert not any(f['rule'] == 'DOC-KIND' for f in new['findings'])                     # a fixed copy is not judged again: it is the same document
    bad = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('x.pdf', io.BytesIO(other), 'application/pdf')}, data={'meta': '{}'}).json()
    assert bad['findings'][0]['rule'] == 'DOC-KIND'
    copy = st.add_document(did, 'M1-05', 'x.pdf', gmp, meta={'fixed_from': bad['id'], 'fixes': ['pdf_version_normalise']}, supersede=bad['id'])
    assert copy['findings'][0]['rule'] == 'DOC-KIND' and copy['findings'][0]['extra']['kind'] == 'stability'      # …and a misfiled one stays misfiled


# ---------------- what the product is
def test_identity_comes_from_the_documents_that_state_it():
    lic = extract.fields_for(extract.content_kind(LICENCE), 'licence.pdf', LICENCE)
    assert lic['product']['dosage_form'] == 'Topical powder' and lic['product']['dosage_form_std'] == 'powder-topical'
    assert lic['product']['manufacturer'] == 'Samplex International for Dermatology Products'       # the first word the OCR lost, as printed on the storage-site line
    apis = {a['name']: a for a in lic['apis']}
    assert list(apis) == ['Neomycin Sulphate', 'Bacitracin Zinc']                                    # the second one's strength line was garbled: the «For …:» block names it
    assert apis['Bacitracin Zinc']['strength'] == '4.200 mg' and apis['Bacitracin Zinc']['manufacturer'] == 'Other API Ltd' and apis['Neomycin Sulphate']['country'] == 'India'
    assert lic['registration']['shelf_life'] == '24 Months' and lic['registration']['reg_no'] == '12345/2021'
    assert lic['document']['valid_until'] == '2031-12-09' and lic['document'].get('issued') != '2031-12-09'      # the invalidation date is not the date of issue
    met = extract.fields_for('method', 'method.doc', METHOD)
    assert met['product'].get('dosage_form') == 'Cutaneous powder' and 'strength' not in met['product']          # its title names the form; «363.7 mg per litre» is not a strength
    assert met['profile'].get('dosage_specifics') in (None, []) and not met['batches']
    out = extract.fields_for('validation', 'run.pdf', PRINTOUT)
    assert not out['product'].get('dosage_form') and out['profile'].get('dosage_specifics') in (None, [])        # «Injection date» is not a dose form
    fill = extract.merge([extract.fields_for('validation', 'run.pdf', PRINTOUT), met, lic, extract.fields_for('method', 'new method.doc', METHOD.replace('sulfate', 'sulphate'))])
    assert fill['product']['dosage_form_std'] == 'powder-topical' and fill['profile'].get('dosage_specifics') in (None, []) and fill['profile']['licence'] == 'toll'
    assert [a['name'] for a in fill['apis']] == ['Neomycin Sulphate', 'Bacitracin Zinc'] and 'strength' not in fill['product']     # two spellings, one substance; a combination has no single strength
    assert fill['profile']['admin_route'] == 'topical' and 'reg_date' not in fill['registration']


def test_spellings_and_noise():
    assert extract.api_key('Neomycin sulphate') == extract.api_key('NEOMYCIN SULFATE 10.000 mg')
    assert intake_eda.repair_company('1 8 0 دح International for Dermatology Products,EGYPT', LICENCE).startswith('Samplex International for Dermatology Products')
    assert intake_eda.repair_company('Example Pharm Co.', LICENCE) == 'Example Pharm Co.'
    assert extract.date_after('Registration No.: 1/2021 Invalidation Date: 09-12-2031', ['Date:']) is None
    assert extract.date_after('Date: 09-12-2021', ['Date:']) == '2021-12-09'
    assert extract._month_after('Mfg. date : 06/2023 | Analysis Date : 09/07/2025', ['Mfg. date']) == '2023-06'


# ---------------- tables are read as tables
def test_a_certificate_and_a_specification_are_read_from_their_tables():
    text = extract.docx_text(COA)
    assert '1- Identification for A- neomycin sulphate B- bacitracin zinc | The retention time matches the standard | Positive' in text      # a cell's own lines stay in its row
    r = extract.fields_for('coa', 'coa.docx', text)
    assert r['batches'] == [{'no': 'DC23008', 'kind': 'fpp', 'date': '2023-06', 'expiry': '2026-06'}]            # «Batch Weight» is not a batch; the manufacture date is not the analysis date
    res = {x['test']: x['value'] for x in r['results']}
    assert res['Assay of neomycin sulphate'] == '98.25 %' and res['Assay of bacitracin zinc'] == '99.16 %' and res['Water content'] == '0.39%' and res['Description'] == 'Conform'
    s = extract.fields_for('spec', 'fps.docx', extract.docx_text(SPEC))
    assert [(x['test'], x['limit'], x['method']) for x in s['specs']] == [('Description', 'White homogenous powder', 'Visual'), ('Water content', 'Not more than 5.0 %', 'Karl Fischer'),
                                                                          ('Assay of neomycin sulphate', '90 – 110 % of the labeled amount', 'HPLC')]
    long_method = 'Specification And Test Method\n' + '\n'.join(f'pH {i}: dissolve 2.3 g of disodium phosphate in 1 L of water, adjust with phosphoric acid.' for i in range(200))
    assert extract.fields_for('spec', 'monograph.pdf', long_method)['specs'] == []                              # sentences of a method are not specification rows
    fill = extract.merge([r, s])
    assert len(fill['specs']) == 3 and fill['specs'][0]['method'] == 'Visual'                                    # one specification: the specification document's own


def test_old_word_tables_keep_their_rows():
    stream = 'Heading\rTEST\x07SPECIFICATION\x07RESULT\x07\x07Assay\x0790 – 110 %\rof the labeled amount\x0798.2 %\x07\x071- Identification\rA- first\rB- second\x07Positive\x07Positive\x07\x07After the table\r'
    lines = [ln.strip() for ln in msdoc._rows(stream).replace('\r', '\n').split('\n') if ln.strip()]
    assert lines == ['Heading', 'TEST | SPECIFICATION | RESULT', 'Assay | 90 – 110 % of the labeled amount | 98.2 %', '1- Identification A- first B- second | Positive | Positive', 'After the table']


# ---------------- a working copy at any time
def test_a_working_copy_is_exported_while_the_gate_is_closed(dossier, tmp_path):
    c, did = dossier
    gmp = make_pdf_lines(tmp_path / 'g.pdf', ['CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER', 'Example Pharm Co.']).read_bytes()
    assert c.post(f'/api/dossiers/{did}/slots/M1-37/documents', files={'file': ('gmp.pdf', io.BytesIO(gmp), 'application/pdf')}, data={'meta': '{}'}).status_code == 201
    assert c.post(f'/api/dossiers/{did}/slots/P-09/documents', files={'file': ('fps.docx', io.BytesIO(SPEC), 'application/msword')}, data={'meta': '{}'}).status_code == 201
    refused = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ctd']})
    assert refused.status_code == 409 and refused.json()['detail']['code'] == 'E-GATE'                           # the real export still waits for a complete dossier
    r = c.post(f'/api/dossiers/{did}/export', json={'working': True})
    assert r.status_code == 201, r.text
    w = r.json()
    assert w['working'] and w['documents'] == 2 and w['missing_required'] > 50 and 'NOT FOR SUBMISSION' in w['label'] and 'ليست للتقديم' in w['label_ar']
    z = zipfile.ZipFile(io.BytesIO(c.get(w['downloads']['ctd-working']).content))
    names = z.namelist()
    assert any('/Module 1/' in n and n.endswith('.pdf') for n in names) and any('/Module 3/' in n and n.endswith('.docx') for n in names)       # a Word draft stays Word
    missing = z.read(next(n for n in names if n.endswith('00-MISSING.txt'))).decode('utf-8')
    assert 'WORKING COPY' in missing and 'Pricing Certificate' in missing and 'GMP certificate(s) of FPP' not in missing
    assert 'WORKING COPY' in z.read(next(n for n in names if n.endswith('00-navigator.html'))).decode('utf-8')
    assert c.get(f'/api/dossiers/{did}/submissions').json() == {'ectd32': [], 'ectd40': []}                       # never recorded as a submission
