"""What the owner's human-level trial on two real products found (13/11/2026), held so it stays fixed — on fictional data:

- the wizard merges the documents' readings in their order of authority (the licence first) and shows where another document says
  something else, instead of letting the last answer win; one substance in two spellings is one substance;
- a file Claude saw as several documents waits to be cut instead of being placed whole; the cut dialog starts from Claude's cuts;
- kept-in-place data: the same price in two currencies' spellings is not a difference, a scan's stray quotes are dropped, a
  technical document does not contradict the product, the wizard's product is what is written;
- the licence's Arabic name is not the Arabic dosage form beside it;
- a Word document is prepared without asking for a PDF cut; a document without headings is not an error;
- Claude can name a part a carton artwork (layout) or a reference standard."""
import io, json
import pytest
from fastapi.testclient import TestClient
from dossier_engine import absorb, extract, intake_eda, fixes, pdfcraft
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')
from test_ui_priority2 import server, page_of          # noqa: F401 — the shared server fixture

PRODUCT = dict(name='Examplol', dosageform='Powder for oral solution', manufacturer='Example Pharm Co.')
PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')])
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol'])


def doc_with(fields, kind=None):
    return {'id': 'd1', 'filename': 'x.pdf', 'meta': {**({'kind': kind} if kind else {}), 'extracted': {'fields': fields}}}


def test_one_price_two_spellings_and_stray_quotes_are_not_differences():
    data = {'registration': {'price': '18 L.E.'}, 'product': {'dosage_form': 'Powder for oral solution'}}
    got = absorb.absorb(data, doc_with({'registration': {'price': '18 EGP'}, 'product': {'dosage_form': '‘Powder for oral solution'}}, 'licence'))
    assert not got['conflicts'] and not data.get('conflicts')
    assert absorb._same('١٨ جنيه'.replace('١٨', '18'), '18 L.E.') and not absorb._same('18 L.E.', '27 EGP')
    fill = {}
    absorb.absorb(fill, doc_with({'product': {'name': '‘Examplol’'}}, 'licence'))
    assert fill['product']['name'] == 'Examplol'


def test_a_technical_document_fills_the_product_but_never_contradicts_it():
    data = {'product': {'dosage_form': 'Powder for oral solution'}}
    got = absorb.absorb(data, doc_with({'product': {'dosage_form': 'Oral powder', 'manufacturer': 'Example Pharm Co.'}}, 'validation'))
    assert not got['conflicts'] and data['product']['dosage_form'] == 'Powder for oral solution' and data['product']['manufacturer'] == 'Example Pharm Co.'
    got = absorb.absorb(data, doc_with({'product': {'manufacturer': 'Another Site Co.'}}, 'licence'))
    assert got['conflicts'] and got['conflicts'][0]['field'] == 'product.manufacturer'          # the licence still does


def test_the_arabic_name_is_not_the_arabic_dosage_form_beside_it():
    lines = ['Final Registration License for Pharmaceutical Product', 'Trade Name: EXAMPLOL بودرة لعمل محلول للتناول عن طريق الفم إكزامبلول',
             'Dosage Form: Powder for oral solution', 'Registration No.: 11111/2021 Invalidation Date: 09-12-2031']
    f = intake_eda.read('\n'.join(lines))
    assert f['product'].get('name_ar') == 'إكزامبلول'


def test_claude_can_name_a_carton_artwork_and_a_reference_standard():
    parts = extract.parse_split({'parts': [{'from': 1, 'to': 1, 'kind': 'licence'}, {'from': 2, 'to': 3, 'kind': 'layout', 'title': 'Carton'},
                                           {'from': 4, 'to': 4, 'kind': 'refstd'}]}, 4)
    assert [p['kind'] for p in parts] == ['licence', 'layout', 'refstd'] and parts[1]['kind_name']['en'].startswith('carton')
    assert extract.KIND_HOME['layout'] == ['M1-11'] and 'layout' in extract.SCHEMA['documents'][0]['kind']


@pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
def test_a_document_without_headings_is_told_plainly(tmp_path):
    src = make_pdf_lines(tmp_path / 'plain.pdf', ['A short letter.', 'Nothing here is a heading.'], 'Letter')
    with pytest.raises(fixes.Refused) as e:
        fixes._pc_bookmarks(str(src), str(tmp_path / 'out.pdf'))
    assert 'عناوين' in e.value.ar and 'headings' in e.value.en


@pytest.fixture
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False), headers={'X-DB': '1'})


def test_a_word_document_is_prepared_and_the_wizards_product_is_what_is_written(c, tmp_path):
    from docx import Document
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    d = Document(); d.add_paragraph('Specification of the finished product'); d.add_paragraph('Assay: 95.0 - 105.0 per cent'); buf = io.BytesIO(); d.save(buf)
    up = c.post(f'/api/dossiers/{did}/slots/P-09/documents', files={'file': ('spec.docx', buf.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert up.status_code == 201, up.text
    r = c.post(f'/api/dossiers/{did}/prepare/{up.json()["id"]}', json={})
    assert r.status_code == 200, r.text                                                   # no «PDF files only» on the way
    lic = make_pdf_lines(tmp_path / 'lic.pdf', ['Final Registration License for Pharmaceutical Product', 'Trade Name: Examplol', 'Dosage Form: Powder for oral solution',
                                                 'Manufacturer : Another Site Co.,EGYPT', 'Registration No.: 22222/2024 Invalidation Date: 01-01-2034'], 'Licence')
    up = c.post(f'/api/dossiers/{did}/slots/M1-04/documents', files={'file': ('licence.pdf', lic.read_bytes(), 'application/pdf')})
    c.post(f'/api/dossiers/{did}/prepare/{up.json()["id"]}', json={})
    data = c.get(f'/api/dossiers/{did}').json()['data']
    assert data['product']['manufacturer'] == 'Example Pharm Co.'                        # the dossier's own, not the document's
    assert any(x['field'] == 'product.manufacturer' and 'Another Site' in x['read'] for x in data.get('conflicts') or [])


def test_the_wizard_merges_by_authority_and_shows_what_differs(server):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'en')
        page.goto(server + '/#/')
        page.wait_for_function('() => typeof mergeReads === "function"')
        r = page.evaluate("""() => {
            const stab = {files: ['stability.pdf'], ai: {documents: [{filename: 'stability.pdf', kind: 'stability'}], product: {name: 'Examplol', manufacturer: 'New Site Co.'}, envelope: {applicant: 'Example Pharm'}}};
            const lic = {files: ['licence.pdf'], ai: {documents: [{filename: 'licence.pdf', kind: 'licence'}], product: {name: 'EXAMPLOL', manufacturer: 'Example Pharm Co.'}, envelope: {applicant: 'EXAMPLE PHARM-EGYPT'}}};
            const m = mergeReads([stab, lic]);                       // the stability letter's answer came first
            return {man: m.product.manufacturer, name: m.product.name, app: m.envelope.applicant, diffs: m._diffs.map(d => [d.field, d.other, d.other_from]),
                    same: sameWords('Quadra Pharma', 'QUADRA PHARM-EGYPT'), key: apiKey('Sodium picosulphate') === apiKey('Sodium picosulfate'),
                    apis: cleanApis([{name: 'Sodium picosulfate', strength: '10 mg'}, {name: 'Sodium picosulphate'}]).map(a => a.name)}; }""")
        b.close()
    assert r['man'] == 'Example Pharm Co.' and r['name'] == 'EXAMPLOL' and r['app'] == 'EXAMPLE PHARM-EGYPT'
    assert r['diffs'] == [['product.manufacturer', 'New Site Co.', 'stability.pdf']]           # «Examplol» / «EXAMPLOL», «Example Pharm» are not differences
    assert r['same'] and r['key'] and r['apis'] == ['Sodium picosulfate']


DIST_PDFJS = __import__('pathlib').Path(__file__).resolve().parents[1] / 'web' / 'dist' / 'assets' / 'ocr' / 'pdfjs'


@pytest.mark.skipif(not (DIST_PDFJS / 'pdf.min.mjs').exists(), reason='pdf.js for the page is fetched by the browser build')
def test_a_long_combined_file_is_shown_to_claude_whole(tmp_path):
    """A 150-page file: every page on the pictures Claude is shown (it stopped at page 96)."""
    import functools, http.server, shutil, threading
    from pypdf import PdfWriter
    site = tmp_path / 'site'; (site / 'ocr').mkdir(parents=True)
    shutil.copytree(DIST_PDFJS, site / 'ocr' / 'pdfjs')
    shutil.copy(__import__('pathlib').Path(__file__).resolve().parents[1] / 'ui' / 'assets' / 'ocr.js', site / 'ocr.js')
    (site / 'index.html').write_text("<!doctype html><meta charset=utf-8><script>window.DB_OCR_BASE='ocr/'</script><script src='ocr.js'></script>")
    w = PdfWriter()
    for _ in range(150):
        w.add_blank_page(width=595, height=842)
    buf = io.BytesIO(); w.write(buf)
    (site / 'long.pdf').write_bytes(buf.getvalue())
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site)); h.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch(); page = b.new_page()
            page.goto(f'http://127.0.0.1:{srv.server_port}/index.html')
            r = page.evaluate("""async () => { const f = new File([await (await fetch('long.pdf')).blob()], 'long.pdf', {type: 'application/pdf'});
                const s = await window.DBOCR.contactSheets(f, {budget: 8}); return s.map(x => [x.from, x.to, x.pages]); }""")
            b.close()
    finally:
        srv.shutdown()
    assert len(r) <= 8 and r[0][0] == 1 and r[-1][1] == 150 and all(x[2] == 150 for x in r)
    assert all(r[k][0] == r[k - 1][1] + 1 for k in range(1, len(r)))                # consecutive, none left out


def test_misread_batches_headings_and_other_spellings_do_not_become_data():
    data = {'apis': [{'name': 'Sodium picosulfate'}, {'name': 'Citric acid monohydrate'}], 'product': {'manufacturer': 'Example Industries for Pharmaceuticals and Nutraceuticals'}}
    spec = doc_with({'apis': [{'name': 'Sodium picosulphate'}, {'name': 'Citric acid anhydrous'}, {'name': 'Ascorbic acid'}, {'name': 'Item Specification'}],
                     'batches': [{'no': 'SYYOFYNOA'}, {'no': 'HPD23008'}]}, 'spec')
    got = absorb.absorb(data, spec)
    assert [a['name'] for a in data['apis']] == ['Sodium picosulfate', 'Citric acid monohydrate']      # no new substance from a specification
    assert [b['no'] for b in data['batches']] == ['HPD23008'] and not got['conflicts']
    lic = doc_with({'apis': [{'name': 'Item Specification'}, {'name': 'Light magnesium oxide', 'strength': '3.500 gm'}],
                    'product': {'manufacturer': '5294 (Example Industries for Pharmaceuticals & Nutraceuticals (EXI'}}, 'licence')
    got = absorb.absorb(data, lic)
    assert [a['name'] for a in data['apis']] == ['Sodium picosulfate', 'Citric acid monohydrate', 'Light magnesium oxide'] and not got['conflicts']
    assert not extract.plausible_api('Item Specification') and extract.plausible_api('Light magnesium oxide')


@pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
def test_improving_a_file_that_cannot_be_smaller_is_tried_once(c, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    pdf = make_pdf_lines(tmp_path / 'spec.pdf', ['Specification of the finished product', 'Assay: 95.0 - 105.0 per cent'], 'Specification')
    up = c.post(f'/api/dossiers/{did}/slots/P-09/documents', files={'file': ('spec.pdf', pdf.read_bytes(), 'application/pdf')}).json()
    c.post(f'/api/dossiers/{did}/prepare/{up["id"]}', json={})
    placed = {d['id']: d for d in c.get(f'/api/dossiers/{did}/prepare').json()['placed']}
    doc = next(d for d in placed.values() if d['original_name'] == 'spec.pdf' or d.get('filename', '').endswith('.pdf'))
    assert doc['improvable'] is False                                                    # tried, nothing to gain: not offered again


def test_a_scanned_certificate_waits_with_claudes_reading_and_goes_to_its_active(c, tmp_path):
    """A scan has no words of its own: what Claude read on it (its title, issuer) chooses the active substance's item."""
    from pypdf import PdfWriter
    prof = dict(PROFILE, apis=[dict(name='Neomycin sulphate', manufacturer='Example Long March Co.', option='FULL'),
                               dict(name='Glycine', manufacturer='Example Amino Co.', option='FULL')])
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=prof, product=PRODUCT, envelope=ENV)).json()['id']
    w = PdfWriter(); w.add_blank_page(width=595, height=842); buf = io.BytesIO(); w.write(buf)
    up = c.post(f'/api/dossiers/{did}/unplaced', files={'files': ('GlycinE_COA.pdf', buf.getvalue(), 'application/pdf')},
                data={'meta': json.dumps({'GlycinE_COA.pdf': {'kind': 'coa'}})})
    assert up.status_code == 201, up.text
    doc = up.json()[0]
    before = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['waiting'] if x['id'] == doc['id'])
    r = c.post(f'/api/dossiers/{did}/documents/{doc["id"]}/model-reading',
               json={'ai': {'documents': [{'filename': 'GlycinE_COA.pdf', 'kind': 'coa', 'title': 'Certificate of analysis — Glycine', 'issuer': 'Example Amino Co.'}]}, 'by': 'claude.ai'})
    assert r.status_code == 200, r.text
    after = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['waiting'] if x['id'] == doc['id'])
    assert before['auto'] is None                                                        # its own words name no active
    assert after['auto'] and 'Glycine' in after['auto'], after                           # Claude's reading does


def test_a_read_dose_form_matches_the_lists_synonyms_and_a_combination_has_no_strength_in_its_name(server):
    from dossier_engine import vocab
    f = next(x for x in vocab.payload(None)['forms'] if x['id'] == 'powder-topical')
    assert 'topical powder' in f['syn']
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'en')
        page.goto(server + '/#/')
        page.wait_for_function('() => typeof vocFind === "function"')
        r = page.evaluate("""async () => { await vocab();
            const w = {d: {}, typed: {}, fromDoc: {}};
            applyFillData(w, {product: {name: 'Examplol', strength: '3.5 mg', dosage_form: 'Topical Powder'}, apis: [{name: 'Neomycin sulphate'}, {name: 'Glycine'}]});
            const one = {d: {}, typed: {}, fromDoc: {}};
            applyFillData(one, {product: {name: 'Examplol', strength: '500 mg', dosage_form: 'Tablet'}, apis: [{name: 'Paracetamol'}]});
            return {form: (vocFind(VOC().forms, 'id', 'Topical Powder') || {}).id, name: w.d.name, single: one.d.name}; }""")
        b.close()
    assert r['form'] == 'powder-topical'
    assert '3.5' not in r['name'] and r['name'].startswith('Examplol') and '500 mg' in r['single']
