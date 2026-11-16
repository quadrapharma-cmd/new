"""«الخزنة» of station 6 and the reader work on the documents as they are now (16/11/2026, found by the click sweep, when the list
was «المكتب» below the prepare cards; since stage 3 the two are one list, each document one card, and the reader covers the page).
Every change to a document makes a new version, with a new id. Three things went wrong around that:
  - «المكتب» kept the list it had asked for before the change («تجهيز الكل» on several files: an answer on its way came back after
    the change and was kept), so its buttons worked on versions no longer current — «الصفحات» answered 422 and showed nothing;
  - the viewer asked for a page by the id it was opened with, even once that version had been replaced;
  - after a change made from an item's drawer or from the viewer, opened on the prepare page, the board was drawn in the page's
    place (under the address of the prepare page).
In a real browser, on the program served by its own engine, with made-up files."""
import json
import urllib.request
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, page_of, upload          # noqa: F401 — the shared server fixture

OFFICE = "() => [...document.querySelectorAll('#offList [data-offdoc]')].map(x => x.dataset.offdoc).sort()"
SHOWN = "() => { const i = document.getElementById('pgImg'); return !!i && i.complete && i.naturalWidth > 0; }"


def call(server, path, body=None):
    req = urllib.request.Request(server + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'}, method='GET' if body is None else 'POST')
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def current(server, did):
    return sorted(d['id'] for s in call(server, f'/api/dossiers/{did}/board')['slots'] for d in s['documents'])


def two_documents(server, tmp_path):
    did = dossier(server)
    slots = [s['slot_id'] for s in call(server, f'/api/dossiers/{did}/board')['slots']
             if s.get('doc_class') == 'company_technical' and s.get('level') == 'R' and not s['documents']][:2]
    a = upload(server, did, slots[0], 'made-up-composition.pdf',
               make_pdf_lines(tmp_path / 'a.pdf', ['Composition certificate', 'Dermacure 20 mg cream (made up)', 'Exampletine 20 mg'], 'Composition').read_bytes())
    b = upload(server, did, slots[1], 'made-up-coa.pdf',
               make_pdf_lines(tmp_path / 'b.pdf', ['Certificate of Analysis', 'Dermacure 20 mg cream (made up)', 'Batch No.: 240101'], 'CoA').read_bytes())
    return did, slots, a['id'], b['id']


def open_prepare(b, server, did, errors, bad):
    page = page_of(b, server, 'ar')
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    page.goto(f'{server}/#/d/{did}/prepare')
    page.wait_for_function("() => document.querySelectorAll('#offList [data-offdoc]').length === 2", timeout=60000)
    return page


def test_the_office_list_is_asked_for_again_after_every_change(server, tmp_path):
    did, slots, a, b_ = two_documents(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_prepare(b, server, did, errors, bad)
        assert page.evaluate(OFFICE) == sorted([a, b_])
        # each document stands once, and its small pages are drawn on its card: one page each, and none asked for that is not there
        # (before: four asked, three refused, and the file's kind shown in the pages' place)
        assert page.locator('#prepOut [data-pdoc]').count() == 2 and page.locator('#offList [data-pdoc]').count() == 2
        page.wait_for_function("() => { const s = [...document.querySelectorAll('#offList [data-pdoc] .pv-strip')]; return s.length === 2 && s.every(x => x.querySelectorAll('img.pv-th').length === 1 && [...x.querySelectorAll('img.pv-th')].every(i => i.complete && i.naturalWidth > 0)); }", timeout=60000)
        assert page.locator('#prepOut .pv-kind').count() == 0
        # the list the page holds is not the documents any more (what an answer that came back late left behind): drawing the page
        # again asks the engine, and does not trust what it holds
        page.evaluate("async () => { S.board.slots.forEach(s => s.documents.forEach(d => { d.id = 'stale-' + d.id; })); await paintPrepare(true); }")
        assert page.evaluate(OFFICE) == sorted([a, b_])
        # a document changed behind the page (another tab, a program): the next drawing shows its new version
        new = call(server, f'/api/dossiers/{did}/documents/{a}/pages', {'op': 'rotate', 'pages': [1], 'degrees': 90})['document']['id']
        page.evaluate('() => paintPrepare(true)')
        assert page.evaluate(OFFICE) == sorted([new, b_]) == current(server, did)
        # typing in the search box filters the list it holds, without asking again
        asked = []
        page.on('request', lambda r: asked.append(r.url) if r.url.endswith('/board') else None)
        page.fill('#offQ', 'coa')
        page.wait_for_function("() => document.querySelectorAll('#offList [data-offdoc]').length === 1")
        assert page.evaluate(OFFICE) == [b_] and not asked
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_the_viewer_and_the_item_drawer_work_on_the_current_version_and_keep_the_page(server, tmp_path):
    did, slots, a, b_ = two_documents(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_prepare(b, server, did, errors, bad)
        v2 = call(server, f'/api/dossiers/{did}/documents/{a}/pages', {'op': 'rotate', 'pages': [1], 'degrees': 90})['document']['id']
        assert a in page.evaluate(OFFICE) and v2 != a                                    # the page still holds the version before
        # «عرض ومراجعة» on that card: the reader is shown the document as it is now…
        page.click(f'#offList [data-offpages="{a}"]')
        page.wait_for_function(SHOWN, timeout=60000)
        assert 'تعذّر' not in page.inner_text('#pgNo') and page.inner_text('#pgNo').strip().startswith('1')
        assert page.get_attribute('#pgNotes', 'href').endswith(f'/documents/{v2}/notes.pdf')   # …and follows it: its links are the current version's
        # …and what it does next is done to that version (before: «هذه نسخة سابقة من المستند»)
        page.click('#pgTurn')
        page.wait_for_function(f"() => !document.querySelector('#offList [data-offdoc=\"{a}\"]') && !document.querySelector('#offList [data-offdoc=\"{v2}\"]')", timeout=60000)
        v3 = next(d for s in call(server, f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == slots[0] for d in s['documents'])
        assert v3['version'] == 3 and page.evaluate(OFFICE) == sorted([v3['id'], b_])
        page.wait_for_function(SHOWN, timeout=60000)
        # the page under the viewer is still the prepare page (before: the board was drawn in its place)
        assert page.evaluate('() => location.hash').endswith('/prepare') and page.locator('#prepOut').count() == 1 and page.locator('#offList').count() == 1
        assert page.inner_text('#view h1').strip() == 'التجهيز والمراجعة'
        page.click('#pgBack')
        page.wait_for_function("() => document.getElementById('reader').hidden && document.getElementById('drawer').hidden")
        # the same from an item's drawer opened on this page: «فتح البند» → «الصفحات» → a page turned → back to the drawer
        page.click(f'#offList [data-offitem="{slots[0]}"]')
        page.wait_for_selector('#drawer [data-pgv]', timeout=30000)
        assert page.get_attribute('#drawer [data-pgv]', 'data-pgv') == v3['id']
        page.click('#drawer [data-pgv]')
        page.wait_for_function(SHOWN, timeout=60000)
        page.click('#pgTurn')
        page.wait_for_function(f"() => !document.querySelector('#offList [data-offdoc=\"{v3['id']}\"]')", timeout=60000)
        v4 = next(d for s in call(server, f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == slots[0] for d in s['documents'])
        assert v4['version'] == 4 and page.evaluate(OFFICE) == sorted([v4['id'], b_])
        page.wait_for_function(SHOWN, timeout=60000)
        page.click('#pgBack')
        page.wait_for_function("() => document.getElementById('reader').hidden")
        page.wait_for_selector('#drawer [data-pgv]', timeout=30000)                      # the item's drawer again, on the version it has now
        assert page.get_attribute('#drawer [data-pgv]', 'data-pgv') == v4['id']
        assert page.evaluate('() => location.hash').endswith('/prepare') and page.locator('#prepOut').count() == 1
        assert page.inner_text('#view h1').strip() == 'التجهيز والمراجعة'
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_the_office_says_why_while_documents_are_being_prepared_and_is_never_silent(server, tmp_path):
    """Stage 2 (16/11/2026): the documents are in their items before «تجهيز الكل», so «المكتب» lists them while they are being
    prepared. Its buttons looked each document up in the page's copy of the board — dropped after every document prepared — and,
    not finding it, did nothing and said nothing. Now: said while the preparation runs (the pages can still be looked at), and
    afterwards each button asks the file how the document stands before it acts."""
    did, slots, a, b_ = two_documents(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_prepare(b, server, did, errors, bad)
        held = []
        page.route('**/api/dossiers/*/prepare/*', lambda r: held.append(r) if r.request.method == 'POST' and not held else r.continue_())   # the first document's preparation takes its time
        page.click('#prepAll')
        for _ in range(100):
            if held:
                break
            page.wait_for_timeout(100)
        assert held and page.evaluate('() => !!S.prepBusy')
        # its item: not opened under a preparation that may change it — and the reason is said
        page.click(f'#offList [data-offitem="{slots[0]}"]')
        page.wait_for_function("() => /جارٍ تجهيز المستندات الآن/.test(document.getElementById('toast').textContent) && !document.getElementById('toast').hidden")
        assert page.evaluate("() => document.getElementById('drawer').hidden")
        # its pages: shown, to look at only
        page.click(f'#offList [data-offpages="{a}"]')
        page.wait_for_function(SHOWN, timeout=60000)
        assert 'للعرض فقط' in page.inner_text('#pgLook') and page.locator('#pgTurn').count() == 0 and page.locator('#pgDel').count() == 0
        assert page.locator('#rdSide [data-pgo]').count() == 0 and page.evaluate("() => document.querySelector('#rdSide [data-rdconds]').inert")   # and its conditions are not answered from here meanwhile
        page.click('#pgBack')
        page.wait_for_function("() => document.getElementById('reader').hidden && document.getElementById('drawer').hidden")
        held[0].continue_()
        page.wait_for_function("() => !S.prepBusy && !S.prepDoing", timeout=120000)
        page.wait_for_function("ids => { const now = [...document.querySelectorAll('#offList [data-offdoc]')].map(x => x.dataset.offdoc).sort(); return now.length === 2 && JSON.stringify(now) === JSON.stringify(ids); }",
                               arg=current(server, did), timeout=60000)
        now = current(server, did)
        first = next(d['id'] for s in call(server, f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == slots[0] for d in s['documents'])
        # prepared: the pages can be turned again, and the item opens
        page.click(f'#offList [data-offpages="{first}"]')
        page.wait_for_function(SHOWN, timeout=60000)
        assert page.locator('#pgTurn').count() == 1 and page.locator('#pgLook').count() == 0
        page.click('#pgBack')
        page.wait_for_function("() => document.getElementById('reader').hidden && document.getElementById('drawer').hidden")
        # the page's copy of the board is away (as it is between a change and the next drawing): the button asks the file, and acts
        page.evaluate('() => { S.board = null; }')
        page.click(f'#offList [data-offitem="{slots[0]}"]')
        page.wait_for_selector('#drawer [data-pgv]', timeout=30000)
        assert page.get_attribute('#drawer [data-pgv]', 'data-pgv') == first
        page.evaluate('() => closeDrawer()')
        # a row whose item is not in the file any more: said, and the list drawn again as the file is
        page.evaluate("() => { const x = document.querySelector('#offList [data-offitem]'); x.dataset.offitem = 'no-such-item'; x.id = 'gone'; }")
        page.click('#gone')
        page.wait_for_function("() => /تغيّر هذا المستند للتو/.test(document.getElementById('toast').textContent)")
        page.wait_for_function("() => !document.getElementById('gone')", timeout=30000)
        assert page.evaluate(OFFICE) == now and page.evaluate("() => document.getElementById('drawer').hidden")
        b.close()
    assert not errors, errors
    assert not bad, bad
