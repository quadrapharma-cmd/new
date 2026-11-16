"""Station 5, «الشجرة المقترحة», in a real browser (eBOX stage 2, 16/11/2026 — the owner: every document «يتعرض عليا في شكل نقاط الشجرة قبل ما
يتكون الملف»). The page of the files that are in the dossier and not in an item yet: each shown under the item proposed for it with
the name it will carry there; a place changed, kept, taken back; a file removed; a combined file cut where its documents start as it
arrives; an item that needs a document's own details asking for them at approval — and nothing placed before «اعتماد الشجرة».
On the program served by its own engine, with made-up files."""
import json
import urllib.request
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, page_of          # noqa: F401 — the shared server fixture
from test_priority2 import combined

WAITING = "() => [...document.querySelectorAll('#treeOut [data-pw]')].map(x => x.dataset.pw)"
HERE = "() => [...document.querySelectorAll('#pathbar .sts a.here')].map(a => +a.dataset.st)"


def call(server, path, body=None):
    req = urllib.request.Request(server + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'}, method='GET' if body is None else 'POST')
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def board(server, did):
    b = call(server, f'/api/dossiers/{did}/board')
    return {d['filename']: s['slot_id'] for s in b['slots'] for d in s['documents']}, sorted(d['filename'] for d in b['unassigned'])


def opened(b, server, did, errors, bad, lang='ar'):
    page = page_of(b, server, lang)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    page.goto(f'{server}/#/d/{did}/tree')
    page.wait_for_selector('#treeSum')
    return page


def test_each_file_is_shown_at_its_proposed_place_and_nothing_is_placed_before_approval(server, tmp_path):
    did = dossier(server)
    api = call(server, f'/api/dossiers/{did}')['profile']['apis'][0]['name']
    coa = make_pdf_lines(tmp_path / 'made-up-coa.pdf', ['Certificate of Analysis', api, 'Batch No.: 240101', 'Assay 99.6 %'], 'CoA')
    spec = make_pdf_lines(tmp_path / 'made-up-spec.pdf', ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white cream'], 'Spec')
    note = make_pdf_lines(tmp_path / 'made-up-note.pdf', ['A note about nothing in particular', 'made up'], 'Note')
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = opened(b, server, did, errors, bad)
        # nothing added yet: said, with the way on; the path's fifth station is this page
        assert page.inner_text('#treeSumT').startswith('لا يوجد مستند بانتظار الاعتماد') and page.get_attribute('#treeNext', 'href').endswith('/prepare')
        assert page.evaluate(HERE) == [5] and page.inner_text('#view h1').strip() == 'الشجرة المقترحة'
        page.set_input_files('#prepFiles', [str(coa), str(spec), str(note)])
        page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 3", timeout=120000)
        assert page.inner_text('#treeSumT') == '3 مستندات بانتظار اعتمادك'
        s = page.inner_text('#treeSum')
        assert 'لها موضع مقترح: 2' in s and 'بلا موضع بعد: 1' in s and 'البنود المطلوبة التي سيكون لها مستند: 2 من' in s
        # each file under the item proposed for it, with what it is, what was read from it and the name it will carry there
        item = page.locator('[data-titem^="M1-35@"]')
        assert item.count() == 1 and 'made-up-coa.pdf' in item.inner_text() and 'نوعه: شهادة تحليل' in item.inner_text() and 'قُرئ منه' in item.inner_text()
        assert '1.2.3.1' in item.locator('[data-tname]').inner_text() and 'اسمه في الملف' in item.inner_text()
        assert 'made-up-spec.pdf' in page.inner_text('[data-titem="P-09"]') and '3.2.P.5.1' in page.inner_text('[data-titem="P-09"] [data-tname]')
        # the file nothing is sure about: apart, with no place invented for it
        loose = page.inner_text('#treeLoose')
        assert 'made-up-note.pdf' in loose and 'لم يتبيّن نوعه' in loose and page.locator('#treeLoose [data-tname]').count() == 0
        # the path's fifth station says how many wait; nothing is in an item yet; the prepare page sends here and offers none of them
        assert page.inner_text('#pathbar .sts a[data-st="5"] .code').strip() == '3'
        assert board(server, did) == ({}, ['made-up-coa.pdf', 'made-up-note.pdf', 'made-up-spec.pdf'])
        page.click('#navPrepare')
        page.wait_for_selector('#prepWaitNote')
        assert 'بانتظار تحديد الموضع: 3 مستندات' in page.inner_text('#prepWaitNote') and page.locator('#prepOut [data-pw]').count() == 0 and page.locator('#prepFiles').count() == 0
        page.click('#prepWaitNote a')
        page.wait_for_function("() => location.hash.endsWith('/tree') && document.querySelectorAll('#treeOut [data-pw]').length === 3", timeout=60000)
        # a place chosen by the person: the file moves under that item, marked as his choice, with its name there — and the choice is kept
        nid = page.get_attribute('#treeLoose [data-pw]', 'data-pw')
        page.select_option(f'[data-tplace="{nid}"]', 'M1-03')
        page.wait_for_function("() => !document.getElementById('treeLoose')", timeout=30000)
        there = page.inner_text('[data-titem="M1-03"]')
        assert 'made-up-note.pdf' in there and 'باختيارك' in there and page.locator('[data-titem="M1-03"] [data-tname]').count() == 1
        assert 'لها موضع مقترح: 3' in page.inner_text('#treeSum') and board(server, did)[0] == {}
        page.reload()
        page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 3", timeout=60000)
        assert 'made-up-note.pdf' in page.inner_text('[data-titem="M1-03"]')
        # taken back: «بلا موضع الآن» — it waits apart again; then removed (asked twice)
        page.select_option(f'[data-tplace="{nid}"]', '')
        page.wait_for_selector('#treeLoose')
        assert 'made-up-note.pdf' in page.inner_text('#treeLoose')
        page.click(f'[data-tdel="{nid}"]')
        assert 'متأكد' in page.inner_text(f'[data-tdel="{nid}"]') and len(page.evaluate(WAITING)) == 3
        page.click(f'[data-tdel="{nid}"]')
        page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 2", timeout=30000)
        assert page.inner_text('#treeSumT') == 'مستندان بانتظار اعتمادك'
        # approved: each into its item, as it is — and on to preparing them
        page.click('#treeGo')
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)
        page.wait_for_function("() => document.querySelectorAll('#prepOut [data-pdoc]').length === 2", timeout=60000)
        placed, waiting = board(server, did)
        assert placed['made-up-spec.pdf'] == 'P-09' and placed['made-up-coa.pdf'].startswith('M1-35@') and waiting == []
        assert page.locator('#prepWaitNote').count() == 0 and page.evaluate('() => S.prep.placed.every(d => !d.prepared)')   # placed, not prepared: that is this station's work
        # back on the tree: nothing waits, and the two show in their items
        page.click('#navTree')
        page.wait_for_selector('#treeSum')
        assert page.inner_text('#treeSumT').startswith('لا يوجد مستند بانتظار الاعتماد') and page.locator('#treeOut [data-tplaced]').count() == 2
        assert 'موضوع في بنده' in page.inner_text('[data-titem="P-09"]') and page.locator('#pathbar .sts a[data-st="5"].done').count() == 1
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_a_combined_file_is_cut_where_its_documents_start_as_it_arrives(server, tmp_path):
    did = dossier(server)
    f = tmp_path / 'scan0042.pdf'
    f.write_bytes(combined(tmp_path))                                                   # five pages: a licence, a pricing certificate, two certificates of analysis
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = opened(b, server, did, errors, bad, 'en')
        page.set_input_files('#prepFiles', [str(f)])
        page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 4", timeout=120000)
        page.wait_for_function("() => !S.prepWaitP")
        names = sorted(page.evaluate("() => [...document.querySelectorAll('#treeOut [data-pw] b bdi')].map(x => x.textContent)"))
        assert names == ['scan0042 (p1).pdf', 'scan0042 (p2).pdf', 'scan0042 (p3).pdf', 'scan0042 (p4-5).pdf']
        assert 'pages 1–1' in page.inner_text('[data-titem="M1-04"]') and 'scan0042 (p1).pdf' in page.inner_text('[data-titem="M1-04"]')     # the licence at its item
        assert 'scan0042 (p2).pdf' in page.inner_text('[data-titem="M1-05"]')                                                             # the pricing certificate at its own
        assert board(server, did) == ({}, names)                                                                                           # cut, shown — and nothing placed
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_an_item_that_needs_the_documents_own_details_asks_for_them_at_approval(server, tmp_path):
    did = dossier(server)
    leaflet = make_pdf_lines(tmp_path / 'made-up-leaflet.pdf', ['Package leaflet: information for the user', 'Dermacure 20 mg cream (made up)', 'Read all of this leaflet carefully'], 'PIL')
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = opened(b, server, did, errors, bad)
        page.set_input_files('#prepFiles', [str(leaflet)])
        page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 1", timeout=120000)
        lid = page.evaluate(WAITING)[0]
        assert page.input_value(f'[data-tplace="{lid}"]') == 'M1-09' and page.locator('[data-titem="M1-09"] [data-pw]').count() == 1   # proposed for the leaflet's item
        assert 'عند الاعتماد ستُسأل عن نوع النشرة ولغتها' in page.inner_text('[data-titem="M1-09"]')     # said before it is asked
        page.click('#treeGo')
        page.wait_for_selector('#mType')
        assert 'made-up-leaflet.pdf' in page.inner_text('#dBody')
        page.click('#mSkip')                                                            # skipped for now: it stays waiting, nothing placed
        page.wait_for_function("() => document.getElementById('drawer').hidden && !S.treeBusy")
        assert board(server, did) == ({}, ['made-up-leaflet.pdf']) and page.evaluate('() => location.hash').endswith('/tree')
        page.wait_for_function("() => document.getElementById('treeGo') && !document.getElementById('treeGo').disabled")
        page.click('#treeGo')
        page.wait_for_selector('#mType')
        page.select_option('#mType', 'pl'); page.select_option('#mLang', 'ar')
        page.click('#mGo')
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)
        docs = [d for s in call(server, f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == 'M1-09' for d in s['documents']]
        assert len(docs) == 1 and docs[0]['meta']['pi_type'] == 'pl' and docs[0]['meta']['lang'] == 'ar'
        b.close()
    assert not errors, errors
    assert not [x for x in bad if '/place' not in x], bad
