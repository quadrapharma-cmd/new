"""Priority 2 of the updates list (docs/ctd/UPDATES.md) — what saves time: Word → PDF on the item (item 17), whole names in the CTD
folders and a company named the same with or without its address (item 16)."""
import io, json
import pytest
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from dossier_engine.generate.docx_kit import find_soffice

H = {'X-DB': '1'}
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', pharmacopoeial=True,
               apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')
office = pytest.mark.skipif(not find_soffice(), reason='needs LibreOffice')


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


@pytest.fixture()
def did(c):
    r = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT,
                                          envelope=dict(tracking='P-0001', applicant='Example Holder S.A.E.', invented_name='Dermacure')), headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


def word(*lines):
    import docx
    d = docx.Document()
    for ln in lines:
        d.add_paragraph(ln)
    buf = io.BytesIO(); d.save(buf)
    return buf.getvalue()


def up(c, did, sid, data, name, meta=None):
    r = c.post(f'/api/dossiers/{did}/slots/{sid}/documents', files={'file': (name, io.BytesIO(data), DOCX)},
               data={'meta': json.dumps(meta or {})}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def current(c, did, sid):
    s = next(x for x in c.get(f'/api/dossiers/{did}/board').json()['slots'] if x['slot_id'] == sid)
    return s['documents']


@office
def test_a_word_document_becomes_its_pdf_and_the_source_is_kept(c, did):
    doc = up(c, did, 'P-16', word('Stability summary and conclusions', 'Dermacure topical powder, 3 batches, 25 °C / 60 % RH'), 'stability.docx')
    assert any(f['rule'] == 'DOCX-DRAFT' for f in doc['findings'])
    r = c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/pdf', headers=H)
    assert r.status_code == 201, r.text
    new = r.json()['document']
    assert new['filename'] == 'stability.pdf' and new['meta']['converted_from'] == 'stability.docx' and not r.json()['beside']
    assert new['check_status'] == 'conforming' and not any(f['rule'] == 'DOCX-DRAFT' for f in new['findings'])
    assert [d['filename'] for d in current(c, did, 'P-16')] == ['stability.pdf']                 # the Word file is superseded, kept
    assert c.get(f'/api/dossiers/{did}/documents/{doc["id"]}/file').status_code == 200                # the source is still there
    ev = [e for e in c.get(f'/api/dossiers/{did}/audit').json() if e.get('event') == 'document.to_pdf']
    assert [e['detail']['doc'] for e in ev] == [doc['id']] and ev[0]['detail']['new'] == new['id']                # recorded: which, into which


@office
def test_the_leaflet_keeps_its_word_and_gets_its_pdf_beside(c, did):
    doc = up(c, did, 'M1-09', word('Summary of Product Characteristics', 'Dermacure topical powder'), 'smpc-en.docx', {'pi_type': 'spc', 'lang': 'en'})
    r = c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/pdf', headers=H).json()
    assert r['beside'] and r['document']['meta']['pi_type'] == 'spc' and r['document']['meta']['lang'] == 'en'
    assert sorted(d['filename'] for d in current(c, did, 'M1-09')) == ['smpc-en.docx', 'smpc-en.pdf']     # Word for the One Submission, PDF for the eCTD


def test_without_libreoffice_the_step_by_hand_and_a_pdf_is_no_source(c, did, monkeypatch, tmp_path):
    doc = up(c, did, 'P-16', word('Stability summary'), 'stability.docx')
    import dossier_engine.generate.docx_kit as kit
    monkeypatch.setattr(kit, 'find_soffice', lambda: None)
    r = c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/pdf', headers=H)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-NO-OFFICE' and 'حفظ باسم' in r.json()['detail']['ar']
    from fixtures_pdf import make_pdf_lines
    pdf = make_pdf_lines(tmp_path / 's.pdf', ['Stability summary'], 'Stability')
    p = c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('s.pdf', pdf.read_bytes(), 'application/pdf')},
               data={'meta': '{}', 'replaces': doc['id']}, headers=H).json()
    r = c.post(f'/api/dossiers/{did}/documents/{p["id"]}/pdf', headers=H)
    assert r.status_code == 422 and r.json()['detail']['code'] == 'E-NOT-SOURCE'
    assert 'office_pdf' in c.get('/api/capabilities').json()


def test_folder_names_end_on_whole_clauses():
    from dossier_engine.writers.ctd import clean
    assert clean('09 1.1.9 Leaflet — One Submission: proposed SmPC & PIL (EN + AR, Word) + most updated reference SmPC & PIL', 44) == '09 1.1.9 Leaflet - One Submission'
    assert clean('19 1.1.17.9 Licence-holder declaration specifying API manufacturers', 44) == '19 1.1.17.9 Licence-holder declaration'
    assert clean('12 1.1.17.6 Store licence (if different from factory licence)', 44) == '12 1.1.17.6 Store licence'
    assert clean('Examplol 500 mg FCT', 60) == 'Examplol 500 mg FCT' and clean('a/b:c', 10) == 'a b c' and clean('', 5) == 'x'
    for n in (20, 30, 44, 56):
        name = clean('03 1.1.3 Action Letter & Name Approval (new) / Re-registration approval letter', n)
        assert len(name) <= n and name.count('(') == name.count(')') and name.split()[-1].lower() not in ('of', 'the', 'and', '&', '-')


def test_a_company_is_the_same_with_or_without_its_address():
    from dossier_engine import extract
    assert extract.org_key('Medis S.A., Nabeul, Tunisia') == ['medis'] == extract.org_key('Medis S.A.')
    assert extract.org_key('Granules India Ltd (Unit II)') == ['granules']
    text = 'GMP Certificate\nManufacturer: Medis S.A.\nEgyptian Drug Authority'
    assert extract.gmp_whose(text, 'Medis S.A., Nabeul, Tunisia', ['Unichem Laboratories']) == 'fpp'


def slot_of(c, did, req):
    return next(x for x in c.get(f'/api/dossiers/{did}/board').json()['slots'] if x['req_id'] == req and x['level'] in ('R', 'O'))


def pdf_up(c, did, sid, data, name='same.pdf'):
    r = c.post(f'/api/dossiers/{did}/slots/{sid}/documents', files={'file': (name, data, 'application/pdf')}, data={'meta': '{}'}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()


def test_the_same_file_in_two_items_is_a_note_and_for_an_imported_product_it_stops(c, did, tmp_path):
    from fixtures_pdf import make_pdf_lines
    data = make_pdf_lines(tmp_path / 'comp.pdf', ['Composition certificate', 'Dermacure topical powder, per 1 g'], 'Composition').read_bytes()
    a, b = slot_of(c, did, 'M1-31')['slot_id'], slot_of(c, did, 'P-01')['slot_id']
    pdf_up(c, did, a, data); pdf_up(c, did, b, data)
    dup = [f for f in c.get(f'/api/dossiers/{did}/board').json()['cross'] if f['id'] == 'XC-DUP']
    assert len(dup) == 1 and dup[0]['severity'] == 'warn' and dup[0]['slots'] == [a, b] and 'same.pdf' in dup[0]['ar']    # a local product: a note
    assert slot_of(c, did, 'M1-31')['status'] != 'non_conforming'
    imp = dict(PROFILE, origin='imported', licence='imported')
    did2 = c.post('/api/dossiers', json=dict(name='Dermacure imported', profile=imp, product=PRODUCT,
                                             envelope=dict(tracking='P-0002', applicant='Example Holder S.A.E.', invented_name='Dermacure')), headers=H).json()['id']
    a2, b2 = slot_of(c, did2, 'M1-31')['slot_id'], slot_of(c, did2, 'P-01')['slot_id']
    pdf_up(c, did2, a2, data); pdf_up(c, did2, b2, data)
    dup2 = [f for f in c.get(f'/api/dossiers/{did2}/board').json()['cross'] if f['id'] == 'XC-DUP']
    assert dup2[0]['severity'] == 'block' and dup2[0]['source'] == 'NP.CAPP.065 v5 general note 3'      # imported: one module only
    assert slot_of(c, did2, 'M1-31')['status'] == 'non_conforming' and not c.get(f'/api/dossiers/{did2}/gate').json()['ok']


def test_one_manufacturers_certificate_for_two_of_its_substances_is_no_repeat(c, tmp_path):
    from fixtures_pdf import make_pdf_lines
    two = dict(PROFILE, origin='imported', licence='imported', apis=[dict(name='Glycine', manufacturer='Northwind Amino Co., Ltd', option='FULL'),
                                                                    dict(name='Threonine', manufacturer='Northwind Amino Co., Ltd', option='FULL')])
    did = c.post('/api/dossiers', json=dict(name='Two APIs', profile=two, product=PRODUCT, envelope={}), headers=H).json()['id']
    gmp = make_pdf_lines(tmp_path / 'gmp.pdf', ['GMP Certificate', 'Northwind Amino Co., Ltd'], 'GMP').read_bytes()
    sids = [x['slot_id'] for x in c.get(f'/api/dossiers/{did}/board').json()['slots'] if x['req_id'] == 'M1-38' and x['level'] in ('R', 'O')]
    assert len(sids) == 2
    for s in sids:
        pdf_up(c, did, s, gmp, 'gmp.pdf')
    assert not [f for f in c.get(f'/api/dossiers/{did}/board').json()['cross'] if f['id'] == 'XC-DUP']


def test_search_finds_the_words_in_every_document_with_its_page(c, did, tmp_path):
    from fixtures_pdf import make_pdf_lines
    stab = make_pdf_lines(tmp_path / 'stab.pdf', ['Stability summary', 'Batch AYBGE211102 was stored at 25 C / 60 % RH', 'Table 3: assay results'], 'Stability')
    pdf_up(c, did, slot_of(c, did, 'P-16')['slot_id'], stab.read_bytes(), 'stability.pdf')
    up(c, did, 'P-01', word('Composition', 'Batch  aybge211102 used for the formula'), 'composition.docx')
    r = c.get(f'/api/dossiers/{did}/search', params={'q': 'AYBGE211102'}, headers=H).json()
    assert r['pending'] == 0 and r['total'] == 2 and r['matches'] == 2                         # case does not count
    hit = next(h for h in r['hits'] if h['filename'] == 'stability.pdf')
    m = hit['matches'][0]
    assert hit['slot_id'] == 'P-16' and hit['ctd'] and m['page'] == 1 and m['snippet'][m['start']:m['start'] + m['length']] == 'AYBGE211102'
    assert c.get(f'/api/dossiers/{did}/search', params={'q': 'table   3'}, headers=H).json()['matches'] == 1   # spacing does not count
    assert c.get(f'/api/dossiers/{did}/search', params={'q': 'not in any file'}, headers=H).json()['hits'] == []
    assert c.get(f'/api/dossiers/{did}/search', params={'q': 'x'}, headers=H).json()['detail']['code'] == 'E-QUERY'


def test_search_reads_arabic_as_people_type_it(tmp_path):
    from dossier_engine import search
    pages = ['شهادة التسعير رقم ١٢٣٤ للمستحضر', 'إقرار الشركة']
    rx = search.pattern('اقرار')
    assert [h['page'] for h in search.find(pages, rx)] == [2]                                    # hamza forms are one letter
    assert search.find(pages, search.pattern('1234'))[0]['page'] == 1                           # Arabic-Indic digits are digits


def test_a_drive_folder_is_listed_with_its_name(tmp_path):
    """Item 14: several folders for one product are listed each under its own name (the page joins them)."""
    import json as _json, urllib.parse
    from dossier_engine import drive

    def http(method, url, headers, data):
        u = urllib.parse.urlparse(url)
        if u.path == '/drive/v3/files/folderAxxxxxxxxxxx':
            return 200, 'application/json', _json.dumps({'id': 'folderAxxxxxxxxxxx', 'name': 'Wouncure — Module 3', 'mimeType': drive.FOLDER}).encode()
        if u.path == '/drive/v3/files':
            return 200, 'application/json', _json.dumps({'files': [{'id': 'f9', 'name': 'stability.pdf', 'mimeType': 'application/pdf', 'size': '5'}]}).encode()
        return 500, 'text/plain', b'unexpected'
    drive.HTTP = http
    try:
        c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
        assert c.put('/api/drive/settings', json={'api_key': 'AIzaTESTKEY0000000000'}, headers=H).status_code == 200
        r = c.post('/api/drive/list', json={'link': 'https://drive.google.com/drive/folders/folderAxxxxxxxxxxx'}, headers=H).json()
        assert r['name'] == 'Wouncure — Module 3' and [f['name'] for f in r['files']] == ['stability.pdf']
        assert c.get('/api/capabilities').json()['drive']['mode'] == 'api_key'         # the page sends a large file through the key
    finally:
        drive.HTTP = None


def combined(tmp_path):
    from fixtures_pdf import make_pdf_lines
    from dossier_engine import pages
    lic = make_pdf_lines(tmp_path / 'a.pdf', ['Final Registration License', 'Trade Name: Dermacure', 'Egyptian Drug Authority'], 'Licence').read_bytes()
    price = make_pdf_lines(tmp_path / 'b.pdf', ['Pricing Certificate', 'Price: EGP 45.00', 'Pack: jar 10 g'], 'Pricing').read_bytes()
    coa1 = make_pdf_lines(tmp_path / 'c.pdf', ['Certificate of Analysis', 'Product: Glycine', 'Batch No: AGLYH211108', 'Assay: 99.5 %'], 'CoA').read_bytes()
    coa2 = make_pdf_lines(tmp_path / 'd.pdf', ['Certificate of Analysis', 'Product: Threonine', 'Batch No: TH2201', 'Assay: 99.1 %'], 'CoA').read_bytes()
    more = make_pdf_lines(tmp_path / 'e.pdf', ['Microbial limits', 'Total aerobic count: complies'], 'CoA').read_bytes()
    return pages.merge([lic, price, coa1, coa2, more])


def test_a_file_of_several_documents_is_cut_where_each_starts(tmp_path):
    from dossier_engine import pages, packs
    data = combined(tmp_path)
    r = pages.propose(data, packs.load('eda.ctd.nta065.v5'))
    assert r['pages'] == 5 and [(p['from'], p['to'], p['kind']) for p in r['parts']] == [(1, 1, 'licence'), (2, 2, 'pricing'), (3, 3, 'coa'), (4, 5, 'coa')]
    assert r['parts'][1]['homes'] == ['M1-05'] and r['page_info'][4]['starts'] is False                     # a page with no title of its own continues
    assert pages.ranges_from_starts([3, 1, 4, 99], 5) == [(1, 2), (3, 3), (4, 5)]
    with pytest.raises(ValueError):
        pages.split(data, [(1, 2), (4, 5)])                                                                    # a page left out: refused


def test_split_sends_each_part_to_the_unplaced_box_and_merge_joins_pages(c, did, tmp_path):
    from fixtures_pdf import make_pdf_lines
    doc = pdf_up(c, did, 'M1-05', combined(tmp_path), 'licence + pricing + CoAs.pdf')
    prop = c.get(f'/api/dossiers/{did}/documents/{doc["id"]}/split', headers=H).json()
    starts = [p['from'] for p in prop['parts']]
    assert starts == [1, 2, 3, 4]
    r = c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/split', json={'starts': starts}, headers=H)
    assert r.status_code == 201, r.text
    names = [p['filename'] for p in r.json()['parts']]
    assert names == ['licence + pricing + CoAs (p1).pdf', 'licence + pricing + CoAs (p2).pdf', 'licence + pricing + CoAs (p3).pdf', 'licence + pricing + CoAs (p4-5).pdf']
    board = c.get(f'/api/dossiers/{did}/board', headers=H).json()
    assert sorted(d['filename'] for d in board['unassigned']) == sorted(names) and not current(c, did, 'M1-05')    # the original withdrawn
    assert c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/split', json={'starts': [1]}, headers=H).status_code == 404     # it is gone from the item
    p1 = make_pdf_lines(tmp_path / 'p1.pdf', ['Stability summary', 'page one'], 'Stability').read_bytes()
    p2 = make_pdf_lines(tmp_path / 'p2.pdf', ['Stability summary', 'page two'], 'Stability').read_bytes()
    a, b = pdf_up(c, did, 'P-16', p1, 'scan-1.pdf'), pdf_up(c, did, 'P-16', p2, 'scan-2.pdf')
    m = c.post(f'/api/dossiers/{did}/slots/P-16/merge', json={'doc_ids': [a['id'], b['id']]}, headers=H)
    assert m.status_code == 201, m.text
    from pypdf import PdfReader
    now = current(c, did, 'P-16')
    assert [d['filename'] for d in now] == ['scan-1.pdf'] and now[0]['meta']['merged_from'] == [a['id'], b['id']]
    pdf = c.get(f'/api/dossiers/{did}/documents/{now[0]["id"]}/file', headers=H).content
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 2
    assert c.post(f'/api/dossiers/{did}/slots/P-16/merge', json={'doc_ids': [now[0]['id']]}, headers=H).json()['detail']['code'] == 'E-MERGE'


def test_a_new_version_keeps_the_attributes_of_the_one_it_replaces_and_an_item_closes_at_once(c, did, tmp_path):
    """Item 42: a «replace» never loses the leaflet's type and language; «close the item» withdraws all its documents."""
    from fixtures_pdf import make_pdf_lines
    pdf1 = make_pdf_lines(tmp_path / 'spc1.pdf', ['Summary of Product Characteristics', 'Dermacure'], 'SmPC').read_bytes()
    first = c.post(f'/api/dossiers/{did}/slots/M1-09/documents', files={'file': ('smpc.pdf', pdf1, 'application/pdf')},
                   data={'meta': json.dumps({'pi_type': 'spc', 'lang': 'ar'}), 'title': 'Arabic SmPC'}, headers=H).json()
    pdf2 = make_pdf_lines(tmp_path / 'spc2.pdf', ['Summary of Product Characteristics', 'Dermacure, updated'], 'SmPC').read_bytes()
    new = c.post(f'/api/dossiers/{did}/slots/M1-09/documents', files={'file': ('smpc-v2.pdf', pdf2, 'application/pdf')},
                 data={'meta': '{}', 'replaces': first['id']}, headers=H).json()
    assert new['meta']['pi_type'] == 'spc' and new['meta']['lang'] == 'ar' and new['title'] == 'Arabic SmPC' and new['version'] == 2
    pdf_up(c, did, 'P-16', make_pdf_lines(tmp_path / 's.pdf', ['Stability summary, batch one'], 'S').read_bytes(), 's1.pdf')
    pdf_up(c, did, 'P-16', make_pdf_lines(tmp_path / 't.pdf', ['Stability summary, batch two'], 'S').read_bytes(), 's2.pdf')
    assert c.post(f'/api/dossiers/{did}/slots/P-16/withdraw-all', headers=H).json() == {'withdrawn': 2}
    assert current(c, did, 'P-16') == []


def test_the_same_product_for_another_country_and_documents_from_another_product(c, did, tmp_path):
    """Items 21 and 43: a dossier copied to another country takes Modules 2–5 as they are (not Module 1); another product's
    dossier gives its active substance's sections where substance and manufacturer match; nothing is overwritten."""
    from fixtures_pdf import make_pdf_lines
    stab = make_pdf_lines(tmp_path / 'st.pdf', ['Stability summary and conclusion', 'Dermacure, 3 batches'], 'S').read_bytes()
    spec = make_pdf_lines(tmp_path / 'sp.pdf', ['Specification of Neomycin sulphate', 'Assay 95-105 %'], 'S').read_bytes()
    comp = make_pdf_lines(tmp_path / 'co.pdf', ['Composition certificate', 'Dermacure per 1 g'], 'S').read_bytes()
    pdf_up(c, did, slot_of(c, did, 'P-16')['slot_id'], stab, 'stability.pdf')
    s_spec = slot_of(c, did, 'S-08')['slot_id']
    pdf_up(c, did, s_spec, spec, 'api-spec.pdf')
    pdf_up(c, did, slot_of(c, did, 'M1-31')['slot_id'], comp, 'composition.pdf')
    r = c.post(f'/api/dossiers/{did}/clone', json={'country': 'SA'}, headers=H)
    assert r.status_code == 201, r.text
    new = r.json()['id']
    assert r.json()['pack'] != c.get(f'/api/dossiers/{did}', headers=H).json()['pack'] and r.json()['copied'] == 2
    names = {d['filename'] for s in c.get(f'/api/dossiers/{new}/board', headers=H).json()['slots'] for d in s['documents']}
    assert names == {'stability.pdf', 'api-spec.pdf'}                                          # Module 1 stays behind
    other = c.post('/api/dossiers', json=dict(name='Dermacure cream', profile=PROFILE, product=dict(PRODUCT, dosageform='cream'), envelope={}), headers=H).json()['id']
    got = c.post(f'/api/dossiers/{other}/copy-from', json={'source': did, 'scope': 'api'}, headers=H).json()
    assert [x['filename'] for x in got['copied']] == ['api-spec.pdf']                          # only the substance's own sections
    again = c.post(f'/api/dossiers/{other}/copy-from', json={'source': did, 'scope': 'api'}, headers=H).json()
    assert again['copied'] == [] and again['kept']                                             # nothing overwritten
    assert c.post(f'/api/dossiers/{other}/copy-from', json={'source': other}, headers=H).json()['detail']['code'] == 'E-SAME'


def test_a_document_is_compared_with_the_version_it_replaced(c, did, tmp_path):
    """Item 36: what was removed and what was added, with the page — word by word with PdfCraft (and a copy with the changes marked),
    line by line where it is not."""
    from fixtures_pdf import make_pdf_lines
    v1 = make_pdf_lines(tmp_path / 'v1.pdf', ['Stability summary', 'Shelf life: 24 months', 'Store below 30 C'], 'S').read_bytes()
    v2 = make_pdf_lines(tmp_path / 'v2.pdf', ['Stability summary', 'Shelf life: 36 months', 'Store below 30 C'], 'S').read_bytes()
    a = pdf_up(c, did, 'P-16', v1, 'stab.pdf')
    b = c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('stab-v2.pdf', v2, 'application/pdf')},
               data={'meta': '{}', 'replaces': a['id']}, headers=H).json()
    r = c.get(f"/api/dossiers/{did}/documents/{b['id']}/compare", headers=H).json()
    assert r['old']['id'] == a['id'] and not r['same']
    if r['engine'] == 'pdfcraft':                         # word by word, each change in its line and with its place on the page
        assert [(x['op'], x['text'], x['line']) for x in r['changes']] == [('removed', '24', 'Shelf life: 24 months'),
                                                                          ('added', '36', 'Shelf life: 36 months')]
        assert all(x['rects'] for x in r['changes']) and r['marked']
        m = c.get(f"/api/dossiers/{did}/documents/{b['id']}/compare.pdf", headers=H)
        assert m.status_code == 200 and m.content[:5] == b'%PDF-' and 'changes' in m.headers['content-disposition']
    else:
        assert [(x['op'], x['text']) for x in r['changes']] == [('removed', 'Shelf life: 24 months'), ('added', 'Shelf life: 36 months')]
    assert all(x['page'] == 1 for x in r['changes'])
    assert c.get(f"/api/dossiers/{did}/documents/{a['id']}/compare", headers=H).json()['detail']['code'] == 'E-NO-VERSION'


def test_team_notes_on_a_document_are_counted_until_resolved(c, did, tmp_path):
    """Item 37: a note for the team on a document (with its page), counted on the item and listed by the gate until resolved."""
    from fixtures_pdf import make_pdf_lines
    d = pdf_up(c, did, 'P-16', make_pdf_lines(tmp_path / 's.pdf', ['Stability summary and conclusion', 'three batches'], 'S').read_bytes(), 's.pdf')
    n = c.post(f"/api/dossiers/{did}/documents/{d['id']}/comments", json={'text': 'Check the 6-month data of batch 2', 'page': 3}, headers=H).json()
    assert n['page'] == 3 and not n['resolved']
    assert slot_of(c, did, 'P-16')['notes_open'] == 1 and 'P-16' in c.get(f'/api/dossiers/{did}/gate', headers=H).json()['notes_open']
    c.put(f"/api/dossiers/{did}/comments/{n['id']}", json={'resolved': True}, headers=H)
    assert slot_of(c, did, 'P-16')['notes_open'] == 0 and c.get(f'/api/dossiers/{did}/gate', headers=H).json()['notes_open'] == []
    assert c.post(f"/api/dossiers/{did}/documents/{d['id']}/comments", json={'text': ' '}, headers=H).json()['detail']['code'] == 'E-TEXT'


def test_a_module_or_the_whole_dossier_as_one_pdf_with_bookmarks(c, did, tmp_path):
    """Item 38: one PDF for a review or for printing; a bookmark for each module, item and document."""
    from fixtures_pdf import make_pdf_lines
    from pypdf import PdfReader
    pdf_up(c, did, 'P-16', make_pdf_lines(tmp_path / 's.pdf', ['Stability summary and conclusion', 'three batches'], 'S').read_bytes(), 'stab.pdf')
    pdf_up(c, did, slot_of(c, did, 'M1-31')['slot_id'], make_pdf_lines(tmp_path / 'c.pdf', ['Composition certificate', 'per 1 g'], 'S').read_bytes(), 'comp.pdf')
    up(c, did, 'P-01', word('Description and composition', 'Dermacure topical powder'), 'p1.docx')
    r = c.get(f'/api/dossiers/{did}/single.pdf', headers=H)
    assert r.status_code == 200 and r.content[:5] == b'%PDF-'
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 3 and 'Left out (not PDF)' in rd.pages[0].extract_text() and 'p1.docx' in rd.pages[0].extract_text()
    top = [o.title for o in rd.outline if not isinstance(o, list)]
    assert top == ['Module 1', 'Module 3']
    m3 = c.get(f'/api/dossiers/{did}/single.pdf', params={'module': 3}, headers=H)
    assert len(PdfReader(io.BytesIO(m3.content)).pages) == 2
    assert c.get(f'/api/dossiers/{did}/single.pdf', params={'module': 5}, headers=H).status_code == 404
