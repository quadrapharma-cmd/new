"""Priority 1 of the updates list (docs/ctd/UPDATES.md) — what the Wouncure trial caught, fixed: whose GMP certificate it is, the
import approval, the variation, the reference standard and the sampling form each in their place (or offered, never placed on a
guess); a file is judged by its text, never its name; «it is in the right place»; moving a document to any item."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import extract
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}
APIS = [dict(name='Glycine', manufacturer='Northwind Amino Co., Ltd', option='FULL'),
        dict(name='Threonine', manufacturer='Northwind Amino Co., Ltd', option='FULL'),
        dict(name='Bacitracin zinc', manufacturer='Eastfield Biochem Pharmaceutical Co.', option='FULL')]
PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', pharmacopoeial=True, apis=APIS)
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='P-0001', applicant='Example Holder S.A.E.', invented_name='Dermacure topical powder', inn=['glycine'])


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


@pytest.fixture()
def did(c):
    r = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV), headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def file_of(tmp_path, name, lines):
    """English text as a PDF; Arabic as a Word file (the test PDF maker writes no Arabic glyphs)."""
    if any('؀' <= ch <= 'ۿ' for ln in lines for ch in ln):
        import docx
        d = docx.Document()
        for ln in lines:
            d.add_paragraph(ln)
        buf = io.BytesIO()
        d.save(buf)
        return name.rsplit('.', 1)[0] + '.docx', buf.getvalue(), DOCX
    return name, make_pdf_lines(tmp_path / 'f.pdf', lines, 'Document').read_bytes(), 'application/pdf'


def classify(c, did, tmp_path, name, lines):
    fname, data, ctype = file_of(tmp_path, name, lines)
    r = c.post(f'/api/dossiers/{did}/classify', files={'files': (fname, io.BytesIO(data), ctype)}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()[0]


def slot(c, did, sid):
    return next(s for s in c.get(f'/api/dossiers/{did}/board', headers=H).json()['slots'] if s['slot_id'] == sid)


def test_an_api_manufacturers_gmp_goes_to_its_substance_not_the_products_item(c, did, tmp_path):
    api_gmp = classify(c, did, tmp_path, 'gmp-1.pdf', ['CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER', 'Name of manufacturer: Eastfield Biochem Pharmaceutical Co.',
                                                       'Good Manufacturing Practice for active substances'])
    assert api_gmp['kind'] == 'gmp' and api_gmp['auto'] and api_gmp['auto'].startswith('M1-38') and 'Bacitracin' in api_gmp['auto'], api_gmp
    shared = classify(c, did, tmp_path, 'gmp-2.pdf', ['GMP CERTIFICATE', 'Manufacturer: Northwind Amino Co., Ltd', 'Good Manufacturing Practice'])
    assert shared['auto'] is None                                         # one maker of two substances: offered for both, placed for neither
    assert {s['slot_id'].split('@')[1].split('|')[0] for s in shared['suggestions'][:2]} == {'Glycine', 'Threonine'}
    fpp = classify(c, did, tmp_path, 'gmp-3.pdf', ['GMP CERTIFICATE', 'Manufacturer: Example Pharm Co.', 'Good Manufacturing Practice, lines: powders'])
    assert fpp['auto'] == 'M1-37'
    nobody = classify(c, did, tmp_path, 'gmp-4.pdf', ['GMP CERTIFICATE', 'Manufacturer: Someone Else Ltd', 'Good Manufacturing Practice'])
    assert nobody['auto'] is None                                         # names neither: never placed on a guess


PACK_ADDITION = ['Egyptian Drug Authority', 'Central Administration of Pharmaceutical Products - Variations unit',
                 'Request: Pack Addition (current 10 g jar; proposed 20 g jar)', 'Variation Committee: approved',
                 'Requirement: accelerated stability 6 months on one production batch']


def test_variation_import_reference_standard_and_sampling_form_each_where_they_belong(c, did, tmp_path):
    var = classify(c, did, tmp_path, 'Stability_x.pdf', PACK_ADDITION)
    assert var['kind'] == 'variation' and var['auto'] is None and var['suggestions'] == []      # a new registration has no item for it: nothing else offered
    rereg = c.post('/api/dossiers', json=dict(name='Dermacure', profile={**PROFILE, 'activity': 're_registration'}, product=PRODUCT, envelope=ENV),
                   headers=H).json()['id']
    var = classify(c, rereg, tmp_path, 'Stability_x.pdf', PACK_ADDITION)
    assert var['kind'] == 'variation' and var['auto'] == 'M1-07', var
    imp = classify(c, did, tmp_path, 'pricing.pdf', ['Egyptian Drug Authority - Pharmaceutical Policies & Market Access', 'Import & Customs Release',
                                                     'Annual import approval serial 175/2025: Glycine and Threonine BP for Dermacure'])
    assert imp['kind'] == 'import' and imp['auto'] is None                # names two substances: offered for both
    assert all(s['req_id'] == 'M1-13' for s in imp['suggestions'][:2]) and all(s['req_id'] != 'M1-05' for s in imp['suggestions'])
    ws = classify(c, did, tmp_path, 'coa-neo.pdf', ['WORKING STANDARD CERTIFICATE', 'Certificate of analysis of the working standard: Bacitracin zinc',
                                                    'Assay against the primary reference standard'])
    assert ws['kind'] == 'refstd' and ws['auto'] and ws['auto'].startswith('S-12'), ws
    sampling = classify(c, did, tmp_path, 'import approval.pdf', ['استمارة سحب عينة', 'المادة الخام: Glycine', 'سبب السحب: إعادة تحليل'])
    assert sampling['kind'] == 'sampling' and sampling['auto'] is None and sampling['suggestions'] == []


def test_the_reasons_speak_the_users_language_and_the_name_is_never_evidence(c, did, tmp_path):
    receipt = classify(c, did, tmp_path, 'Registration License renewal.pdf', ['إيصال سداد رسوم', 'متابعة طلب التجديد'])
    assert receipt['kind'] == 'receipt' and all(not s['req_id'].startswith('M1-04') for s in receipt['suggestions'][:1])
    why = receipt['suggestions'][0]['why'][0]
    assert isinstance(why, dict) and why['ar'].startswith('شكله') and 'document kind' not in json.dumps(receipt)


def test_it_is_in_the_right_place_and_move_to_any_item(c, did, tmp_path):
    fname, data, ctype = file_of(tmp_path, 'a.pdf', ['هيئة الدواء المصرية', 'الإدارة العامة للثبات', 'موافقة الثبات للمستحضر ديرماكيور'])
    up = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': (fname, io.BytesIO(data), ctype)},
                data={'meta': '{}'}, headers=H).json()
    assert any(f['rule'] == 'DOC-KIND' for f in up['findings']) and up['check_status'] == 'non_conforming'
    ok = c.post(f"/api/dossiers/{did}/documents/{up['id']}/confirm-kind", headers=H).json()
    assert not any(f['rule'] == 'DOC-KIND' for f in ok['findings']) and ok['check_status'] != 'non_conforming'
    assert ok['meta']['kind_confirmed']['rule_said'] == 'stability'
    assert any(a['event'] == 'document.kind_confirmed' for a in c.get(f'/api/dossiers/{did}/audit', headers=H).json())
    off = c.post(f"/api/dossiers/{did}/documents/{up['id']}/move", json={'slot_id': 'M1-34'}, headers=H)
    assert off.status_code == 422 and off.json()['detail']['code'] == 'E-SLOT-INACTIVE'                   # not an item of this dossier: refused, nothing moves
    mv = c.post(f"/api/dossiers/{did}/documents/{up['id']}/move", json={'slot_id': 'P-16'}, headers=H)
    assert mv.status_code == 200 and mv.json()['slot_id'] == 'P-16'
    assert slot(c, did, 'P-16')['documents'] and not slot(c, did, 'M1-05')['documents']


def test_org_names_are_matched_by_the_words_that_tell_them_apart():
    assert extract.org_key('Tianjin Example Pharmaceutical Co., Ltd') == ['tianjin', 'example']
    assert extract.names_org('Manufacturer: TIANJIN EXAMPLE PHARMACEUTICAL', 'Tianjin Example Pharmaceutical Co., Ltd')
    assert not extract.names_org('Manufacturer: Tianjin Other Co.', 'Tianjin Example Pharmaceutical Co., Ltd')
    assert extract.gmp_whose('GMP certificate - Example Pharm Co.', 'Example Pharm Co.', ['Northwind Amino']) == 'fpp'


def test_a_raw_materials_coa_gives_the_substance_a_batch_not_the_product():
    supplier = ('CERTIFICATE OF ANALYSIS\nProduct name: Glycine BP 2018\nManufacturer: Northwind Amino Co., Ltd\nBatch No: AGLY211108\n'
                'Manufacturing date: 2021-11-08\nRetest date: 2023-11-07\nAssay (on dried basis) 99.6%; Loss on drying 0.1%; Residue on ignition 0.02%')
    assert extract.fields_for('coa', 'x.pdf', supplier)['batches'] == [{'no': 'AGLY211108', 'kind': 'api', 'api': 'Glycine', 'date': '2021-11-08'}]
    product = ('CERTIFICATE OF ANALYSIS\nProduct name: Dermacure 500 mg film-coated tablets\nBatch No: DC24001\n'
               'Assay 99.8%; Dissolution 92%; Uniformity of dosage units AV 3.1')
    assert extract.fields_for('coa', 'y.pdf', product)['batches'][0]['kind'] == 'fpp'


def test_the_salt_form_has_a_row_per_salt_only_with_its_strength(c, tmp_path):
    apis = [dict(name='Neomycin sulphate', manufacturer='Eastfield Biochem Pharmaceutical Co.', option='FULL'),
            dict(name='Glycine', manufacturer='Northwind Amino Co., Ltd', option='FULL'),
            dict(name='Cysteine hydrochloride monohydrate', manufacturer='Northwind Amino Co., Ltd', option='FULL'),
            dict(name='Sodium chloride', manufacturer='Salt Works Co.', option='FULL')]
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile={**PROFILE, 'apis': apis}, product=PRODUCT, envelope=ENV), headers=H).json()['id']
    c.put(f'/api/dossiers/{did}/data', json={'apis': [{'name': 'Neomycin sulphate', 'strength': '3.5 mg'}, {'name': 'Glycine', 'strength': '10 mg'},
                                                      {'name': 'Cysteine HCl', 'strength': '2 mg'}]}, headers=H)
    rows = c.get(f'/api/dossiers/{did}/generate/salt/prefill', headers=H).json()['apis']
    assert [r['name_salt'] for r in rows] == ['Neomycin sulphate', 'Cysteine hydrochloride monohydrate']        # no glycine, no sodium chloride
    assert rows[0] == {'name_salt': 'Neomycin sulphate', 'name_base': 'Neomycin', 'label_claim_mg': 3.5}
    assert rows[1]['name_base'] == 'Cysteine' and rows[1]['label_claim_mg'] == 2.0


def upload(c, did, tmp_path, sid, lines, meta=None, name='doc.pdf'):
    fname, data, ctype = file_of(tmp_path, name, lines)
    r = c.post(f'/api/dossiers/{did}/slots/{sid}/documents', files={'file': (fname, io.BytesIO(data), ctype)}, data={'meta': json.dumps(meta or {})}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def test_validity_is_read_from_the_document_and_edas_pricing_exception_applies(c, did, tmp_path):
    gmp = upload(c, did, tmp_path, 'M1-37', ['GMP CERTIFICATE', 'Manufacturer: Example Pharm Co.', 'Good Manufacturing Practice', 'Valid until: 2020-01-31'])
    assert gmp['meta']['valid_until'] == '2020-01-31' and gmp['meta']['valid_until_read']
    assert slot(c, did, 'M1-37')['status'] == 'non_conforming'                       # expired: read, not typed
    price = upload(c, did, tmp_path, 'M1-05', ['Egyptian Drug Authority', 'Pricing certificate', 'Dermacure jar 10 g', 'Valid until: 2021-05-31'])
    assert price['meta']['valid_until'] == '2021-05-31' and slot(c, did, 'M1-05')['status'] == 'non_conforming'
    req = upload(c, did, tmp_path, 'M1-05', ['Request for renewal of the price of Dermacure', 'Submitted to the Pricing Administration', 'Receipt no. 1204023468'],
                 name='request.pdf')
    assert req['meta']['renewal_request'] and not any(f['rule'] == 'DOC-KIND' for f in req['findings'])
    s = slot(c, did, 'M1-05')
    assert s['status'] == 'needs_attention'                                            # accepted with the request (NP.CAPP.065 v5 1.1.5)
    assert any(f['rule'] == 'DOC-EXPIRED-RENEWAL' for d in s['documents'] for f in d['findings'])


def test_an_api_coa_shows_its_batch_and_dates(c, did, tmp_path):
    sid = next(s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board', headers=H).json()['slots'] if s['req_id'] == 'M1-35' and 'Glycine' in s['slot_id'])
    bare = upload(c, did, tmp_path, sid, ['CERTIFICATE OF ANALYSIS', 'Product name: Glycine BP', 'Batch No: AGLY211108', 'Assay (on dried basis) 99.6%'])
    gap = next(f for f in bare['findings'] if f['rule'] == 'COA-DATA')
    shown = gap['en'].split(' — ')[0]
    assert 'manufacturing date' in shown and 'expiry or retest date' in shown and 'batch number' not in shown
    full = upload(c, did, tmp_path, sid, ['CERTIFICATE OF ANALYSIS', 'Product name: Glycine BP', 'Batch No: AGLY211108', 'Manufacturing date: 2021-11-08',
                                          'Retest date: 2023-11-07', 'Assay (on dried basis) 99.6%'])
    assert not any(f['rule'] == 'COA-DATA' for f in full['findings'])


def test_the_items_one_question_signed_stamped_legalised(c, tmp_path):
    imported = c.post('/api/dossiers', json=dict(name='Dermacure', profile={**PROFILE, 'origin': 'imported', 'licence': 'own'}, product=PRODUCT, envelope=ENV),
                      headers=H).json()['id']
    board = c.get(f'/api/dossiers/{imported}/board', headers=H).json()['slots']
    cpp = next(s['slot_id'] for s in board if s['req_id'] == 'M1-14' and s['status'] != 'not_applicable')
    upload(c, imported, tmp_path, cpp, ['CERTIFICATE OF A PHARMACEUTICAL PRODUCT', 'This certificate conforms to the WHO certification scheme'])
    s = slot(c, imported, cpp)
    assert s['attest_need'] == ['legalized'] and s['attest'] is None
    assert cpp in c.get(f'/api/dossiers/{imported}/gate', headers=H).json()['to_confirm']
    c.post(f'/api/dossiers/{imported}/slots/{cpp}/attest', json={'answer': 'no'}, headers=H)
    g = c.get(f'/api/dossiers/{imported}/gate', headers=H).json()
    assert cpp in g['non_conforming'] and cpp not in g['to_confirm']                    # «not yet» stops the export
    c.post(f'/api/dossiers/{imported}/slots/{cpp}/attest', json={'answer': 'yes'}, headers=H)
    g = c.get(f'/api/dossiers/{imported}/gate', headers=H).json()
    assert cpp not in g['non_conforming'] and cpp not in g['to_confirm']
    assert c.post(f'/api/dossiers/{imported}/slots/{cpp}/attest', json={'answer': 'maybe'}, headers=H).status_code == 422


def test_the_leaflet_item_takes_word_and_the_ectd_gets_its_pdf(c, did, tmp_path):
    from dossier_engine.app import exporter
    from dossier_engine.generate.docx_kit import find_soffice
    import docx
    d = docx.Document(); d.add_paragraph('Summary of Product Characteristics'); d.add_paragraph('Dermacure topical powder')
    buf = io.BytesIO(); d.save(buf)
    up = c.post(f'/api/dossiers/{did}/slots/M1-09/documents', files={'file': ('smpc.docx', io.BytesIO(buf.getvalue()), DOCX)},
                data={'meta': json.dumps({'pi_type': 'spc', 'lang': 'en'})}, headers=H).json()
    assert not any(f['rule'] == 'DOCX-DRAFT' for f in up['findings']) and up['check_status'] == 'conforming'     # the format the item asks
    assert [f['scope'] for f in up['findings'] if f['rule'] == 'ECTD-WORD'] == ['ectd']
    word = tmp_path / 'leaflet.docx'; word.write_bytes(buf.getvalue())
    twin = make_pdf_lines(tmp_path / 'leaflet.pdf', ['Summary of Product Characteristics'], 'SmPC')
    both = {'M1-09': [{'file': str(word), 'ext': '.docx', 'pi_type': 'spc', 'lang': 'en', 'title': 'SmPC'},
                      {'file': str(twin), 'ext': '.pdf', 'pi_type': 'spc', 'lang': 'en', 'title': 'SmPC (PDF)'}]}
    assert [f['file'] for f in exporter.ectd_files(both)['M1-09']] == [str(twin)]          # its own PDF goes in
    alone = {'M1-09': [{'file': str(word), 'ext': '.docx', 'pi_type': 'spc', 'lang': 'en', 'title': 'SmPC'}]}
    if find_soffice():
        assert exporter.ectd_files(alone)['M1-09'][0]['file'].endswith('.pdf')
    else:
        with pytest.raises(exporter.ExportError) as e:
            exporter.ectd_files(alone)
        assert e.value.code == 'E-WORD-PDF' and e.value.ar


def test_each_documents_conditions_are_shown_before_anything_is_uploaded(c):
    """Item 1: what each item's file must be (form) and hold (content), from the rules in force — one source for the wizard's
    document cards, its requirements step and the item drawer."""
    j = c.get('/api/conditions?country=EG').json()
    assert j['pack'] == 'eda.ctd.nta065.v5'
    kinds = lambda rid: [x['kind'] for x in j['items'][rid]]
    texts = lambda rid: ' | '.join(x['en'] for x in j['items'][rid] if x['kind'] != 'source')
    assert j['items']['M1-09'][0]['en'].startswith('Word (.docx)') and 'searchable PDF' not in texts('M1-09')      # 1.1.9 asks Word
    assert 'searchable PDF' in texts('M1-35') and 'batch number' in texts('M1-35')                               # the API CoA's data
    assert 'Valid on the day of submission' in texts('M1-37') and 'production lines' in texts('M1-37')          # GMP: valid, its lines
    assert 'Legalised' in texts('M1-14')                                                                        # the CPP: legalised
    assert 'request for updating the price' in texts('M1-05') and 'translation' not in texts('M1-05')          # pricing: EDA's exception
    assert "company's letterhead" in texts('M1-01') and 'Dated' in texts('M1-01')                               # the application form
    assert "letterhead" not in texts('S-10') and "letterhead" not in texts('M1-44')                            # technical text, the auto table
    assert kinds('P-16')[-1] == 'source' and all(x['ar'] for x in j['items']['P-16'])                         # the source's wording kept
    assert any('Valid on the day' in x['en'] for x in j['kinds']['gmp'])                                       # the cards: by kind of document
    eu = c.get('/api/conditions?country=DE').json()
    assert eu['pack'] != j['pack'] and not any('NP.CAPP' in x['source'] for v in eu['items'].values() for x in v if x['kind'] != 'source')
