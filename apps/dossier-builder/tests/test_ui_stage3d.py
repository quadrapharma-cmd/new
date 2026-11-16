"""eBOX stage 3 (16/11/2026), what goes with stations 5 to 7: a newer copy of a certificate offered on the proposed tree as its new
version (the earlier one kept); an item's point and the source of its conditions on station 5; «التنفيذ التلقائي» — the owner's «سيبها
عليّ» — on the tree and on the product card; the target submission date on the product card; the validity date Claude read on a
scan's pages in «القراءة والفرز» carried with the file. In a real browser, on the program served by its own engine, with made-up files."""
import datetime
import json
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
import httpx
from fixtures_pdf import make_pdf_lines, make_pdf
from test_ui_priority2 import server, dossier, page_of, upload          # noqa: F401 — the shared server fixture
from test_ui_vault import call
from wizard_steps import to_card

GMP = ['Certificate of GMP compliance of a manufacturer', 'Example Pharm Co., 1 Made-up Street', 'Certificate No. GMP-0001', 'made up for a test']
H = {'X-DB': '1'}
TODAY = datetime.date.today()


def stage(server, did, name, data, **said):
    r = httpx.post(f'{server}/api/dossiers/{did}/unplaced', files={'files': (name, data)}, data={'meta': json.dumps({name: said} if said else {})}, headers=H)
    assert r.status_code in (200, 201), r.text[:300]
    return r.json()[0]['id']


def board(server, did):
    return call(server, f'/api/dossiers/{did}/board')


def open_tree(b, server, did, errors, bad, lang='ar'):
    page = page_of(b, server, lang)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    page.goto(f'{server}/#/d/{did}/tree')
    page.wait_for_function("() => typeof S === 'object' && !!S.tree && !!document.getElementById('treeSum') && !S.prepWaitP", timeout=120000)
    return page


def gmp_with_a_newer_copy(server, tmp_path):
    did = dossier(server)
    old = upload(server, did, 'M1-37', 'made-up-gmp-old.pdf', make_pdf_lines(tmp_path / 'old.pdf', GMP + ['the earlier copy'], 'old').read_bytes())
    call(server, f'/api/dossiers/{did}/documents/{old["id"]}/validity', {'valid_until': (TODAY + datetime.timedelta(days=100)).isoformat()}, method='PUT')
    later = (TODAY + datetime.timedelta(days=800)).isoformat()
    new = stage(server, did, 'made-up-gmp-new.pdf', make_pdf_lines(tmp_path / 'new.pdf', GMP + ['the later copy'], 'new').read_bytes(), kind='gmp', valid_until=later)
    return did, old['id'], new, later


def test_a_newer_copy_is_offered_as_the_new_version_of_its_document(server, tmp_path):
    did, old, new, later = gmp_with_a_newer_copy(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_tree(b, server, did, errors, bad)
        box = page.locator(f'[data-tbeside="{new}"]')
        box.wait_for(timeout=60000)
        text = box.inner_text()
        assert 'في هذا البند الآن:' in text and 'made-up-gmp-old.pdf' in text and 'وهذا الملف صالح حتى ' + page.evaluate('d => dateL(d)', later) in text
        # the program proposes it is a newer copy (it is valid later): that choice is the one ticked, and said why
        assert page.is_checked(f'[data-trp="{new}"][value="{old}"]') and not page.is_checked(f'[data-trp="{new}"][value=""]')
        assert 'يقترح البرنامج أنه نسخة أحدث' in page.inner_text(f'[data-tbeside="{new}"] [data-tnewer]')
        assert 'نسخة أحدث من «made-up-gmp-old.pdf»: تحل محله، ويُحفظ السابق' in text
        # «beside it» chosen, then the proposal again: the choice is kept on this device while it differs from the proposal
        page.check(f'[data-trp="{new}"][value=""]')
        page.wait_for_function(f"() => {{ const r = document.querySelector('[data-trp=\"{new}\"][value=\"\"]'); return r && r.checked; }}", timeout=30000)
        assert page.evaluate(f"() => JSON.parse(localStorage.getItem('db.treeRp.{did}'))") == {new: ''}
        page.check(f'[data-trp="{new}"][value="{old}"]')
        page.wait_for_function(f"() => {{ const r = document.querySelector('[data-trp=\"{new}\"][value=\"{old}\"]'); return r && r.checked; }}", timeout=30000)
        assert page.evaluate(f"() => JSON.parse(localStorage.getItem('db.treeRp.{did}') || '{{}}')") == {}
        # approved: the new file takes the document's place as its version 2; the earlier one is kept in its history
        page.click('#treeGo')
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)
        docs = next(s for s in board(server, did)['slots'] if s['slot_id'] == 'M1-37')['documents']
        assert len(docs) == 1 and docs[0]['version'] == 2 and docs[0]['filename'] == 'made-up-gmp-new.pdf' and docs[0]['meta']['claude_valid_until'] == later
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_beside_it_keeps_both_documents_in_the_item(server, tmp_path):
    did, old, new, later = gmp_with_a_newer_copy(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_tree(b, server, did, errors, bad)
        page.wait_for_selector(f'[data-tbeside="{new}"]', timeout=60000)
        page.check(f'[data-trp="{new}"][value=""]')
        page.wait_for_function(f"() => {{ const r = document.querySelector('[data-trp=\"{new}\"][value=\"\"]'); return r && r.checked && !!document.getElementById('treeGo'); }}", timeout=30000)
        page.click('#treeGo')
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)
        docs = next(s for s in board(server, did)['slots'] if s['slot_id'] == 'M1-37')['documents']
        # both stay current in the item (its versions are numbered per item: the one added beside it is its second)
        assert sorted((d['filename'], d['version']) for d in docs) == [('made-up-gmp-new.pdf', 2), ('made-up-gmp-old.pdf', 1)]
        assert page.evaluate(f"() => localStorage.getItem('db.treeRp.{did}')") in (None, '{}')                   # nothing left behind
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_station_5_says_an_items_point_and_opens_its_conditions(server, tmp_path):
    did = dossier(server)
    upload(server, did, 'M1-05', 'made-up-pricing.pdf', make_pdf_lines(tmp_path / 'p.pdf', ['Pricing Certificate', 'Dermacure', 'Price: EGP 45.00'], 'p').read_bytes())
    stage(server, did, 'IMG_2041.pdf', make_pdf(tmp_path / 'IMG_2041.pdf', 'IMG_2041.pdf').read_bytes())
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_tree(b, server, did, errors, bad)
        row = page.locator('[data-titem="M1-05"]')
        row.wait_for(timeout=60000)
        assert row.locator('[data-point]').inner_text().strip() == 'مفتوح: لم يُجهَّز بعد'
        row.locator('[data-lib]').click()
        page.wait_for_selector('#drawer #libHead', timeout=30000)
        assert page.inner_text('#dTitle').strip() == 'شروط البند ومصدرها' and '1.1.5' in page.inner_text('#libHead')
        assert page.evaluate('() => location.hash').endswith('/tree')                                 # the station is still under it
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_run_it_for_me_places_what_is_sure_prepares_it_and_leaves_the_rest(server, tmp_path):
    did = dossier(server)
    upload(server, did, 'M1-37', 'made-up-gmp-old.pdf', make_pdf_lines(tmp_path / 'old.pdf', GMP + ['the copy in the item'], 'old').read_bytes())
    sure = stage(server, did, 'Pricing certificate.pdf', make_pdf(tmp_path / 'Pricing certificate.pdf', 'Pricing certificate.pdf').read_bytes())
    unknown = stage(server, did, 'IMG_2041.pdf', make_pdf(tmp_path / 'IMG_2041.pdf', 'IMG_2041.pdf').read_bytes())
    asks = stage(server, did, 'made-up-gmp-again.pdf', make_pdf_lines(tmp_path / 'again.pdf', GMP + ['another copy, no date'], 'again').read_bytes(), kind='gmp')
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_tree(b, server, did, errors, bad)
        places = page.evaluate("() => Object.fromEntries(S.tree.waiting.map(w => [w.id, [w.place, w.auto, (w.beside || []).length]]))")
        assert places[sure][0] == places[sure][1] == 'M1-05' and places[unknown][0] is None and places[asks][0] == 'M1-37' and places[asks][2] == 1, places
        assert 'التنفيذ التلقائي' in page.inner_text('#treeAuto') and 'يبقى هنا' in page.inner_text('#treeAutoSub')
        page.click('#treeAuto')
        # placed what is sure, then on to station 6, which prepares it — and says what was left on the tree
        page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)
        page.wait_for_function("() => /ملفات بقيت في «الشجرة المقترحة» تنتظر قرارك: 2/.test(document.getElementById('toast').textContent)", timeout=60000)
        page.wait_for_function("() => !S.prepBusy && !S.prepDoing && S.prep && S.prep.placed.length === 2 && S.prep.placed.every(d => d.prepared)", timeout=240000)
        slots = {s['slot_id']: s for s in board(server, did)['slots']}
        assert [d['filename'] for d in slots['M1-05']['documents']] == ['Pricing certificate.pdf']
        assert [d['filename'] for d in slots['M1-37']['documents']] == ['made-up-gmp-old.pdf']        # the one that asked «beside or newer?» was not decided for him
        assert sorted(u['id'] for u in board(server, did)['unassigned']) == sorted([unknown, asks])
        assert 'بانتظار تحديد الموضع: مستندان' in page.inner_text('[data-rs="waiting"]')
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_the_product_card_takes_the_target_date_and_runs_it_for_me(server, tmp_path):
    errors, bad = [], []
    target = (TODAY + datetime.timedelta(days=120)).isoformat()
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 and '/intake/drafts' not in r.url else None)
        page.goto(f'{server}/#/new')
        to_card(page)
        page.fill('[data-in="name"]', 'Dermacure (made up)'); page.fill('[data-in="trade"]', 'Dermacure'); page.fill('[data-in="man"]', 'Example Pharm Co.')
        page.fill('[data-api="0"][data-f="name"]', 'Neomycin sulphate'); page.fill('[data-api="0"][data-f="manufacturer"]', 'Example API Co.')
        page.fill('[data-in="applicant"]', 'Example Pharm Co.'); page.fill('[data-in="tracking"]', 'T-0001')
        assert page.inner_text('label:has(#cardTarget) span').strip() == 'تاريخ التقديم المستهدف'
        page.fill('#cardTarget', target)
        assert page.inner_text('#wizAuto').strip() == 'اعتماد البطاقة والتنفيذ التلقائي'
        page.click('#wizAuto')
        # made, nothing to place, and on to station 6 by itself
        page.wait_for_function("() => /\\/d\\/[^/]+\\/prepare$/.test(location.hash) && !!document.getElementById('readyT') && document.getElementById('readyT').textContent.trim() !== '…'", timeout=120000)
        did = page.evaluate("() => location.hash.split('/')[2]")
        assert call(server, f'/api/dossiers/{did}')['envelope']['target_date'] == target
        assert page.inner_text('#readyT').strip() == 'لا يوجد مستند في البنود بعد'
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_selector('#boardSign')
        assert page.input_value('#targetDate') == target and 'الأيام المتبقية حتى هذا التاريخ: 120.' in page.inner_text('#targetNote')
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_the_date_claude_read_on_a_scan_goes_with_the_file(server, tmp_path):
    """Seen in stage 2: a scan whose validity date Claude read in «القراءة والفرز» arrived on the tree without it (the engine cannot
    read a scan). Only Claude's dates go with a file: a date read from a file's own text is read again at its preparation, and a date
    no reading gave is never said."""
    did = dossier(server)
    data = make_pdf_lines(tmp_path / 'scan.pdf', ['A made-up certificate', 'Dermacure'], 'scan').read_bytes()
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_tree(b, server, did, errors, bad)
        dates = page.evaluate("""() => wizDates({intakeFill: {documents: [{filename: 'made-up-scan.pdf', valid_until: '2030-01-31', issued: '2025-02-01'},
            {filename: 'made-up-text.pdf', valid_until: '2031-03-31'}, {filename: 'made-up-ocr.pdf', valid_until: '2032-04-30'}]},
            ocrRead: {'made-up-scan.pdf': 'model', 'made-up-ocr.pdf': 'browser'}})""")
        assert dates == {'made-up-scan.pdf': {'valid_until': '2030-01-31', 'issued': '2025-02-01'}}
        page.evaluate("""async ([did, b64, dates]) => { const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
            await stageFiles(did, [new File([bytes], 'made-up-scan.pdf', {type: 'application/pdf'})], {dates}); }""",
                      [did, __import__('base64').b64encode(data).decode(), dates])
        w = call(server, f'/api/dossiers/{did}/tree')['waiting']
        assert [(x['filename'], x['valid_until']) for x in w] == [('made-up-scan.pdf', '2030-01-31')]
        b.close()
    assert not errors, errors
    assert not bad, bad
