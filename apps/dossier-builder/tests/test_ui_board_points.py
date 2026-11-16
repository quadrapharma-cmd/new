"""Station 7 «شجرة الملف والنواقص» (eBOX stage 3, 16/11/2026): the whole tree, each required point said closed or open with its
reason in the words of stations 5 and 6; one count on the sign, the path bar and the home; what has to be obtained set out under
who issues it, with how each is obtained (in Arabic in the Arabic page) and one request to a party for everything asked of it; a
target submission date on which every certificate is judged; documents added the proposed tree's way.
In a real browser, on the program served by its own engine, with made-up files."""
import base64
import datetime
import json
import urllib.request
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, page_of, upload          # noqa: F401 — the shared server fixture
from test_ui_vault import made_up, prepare_all, call, lines_of

SIGN = "() => document.getElementById('bsT').textContent.trim()"
ROWS = "() => [...document.querySelectorAll('tbody tr[data-brow]')].map(x => [x.dataset.brow, (x.querySelector('[data-point]') || {dataset: {}}).dataset.point || null])"


def put(server, path, body):
    return call(server, path, body, method='PUT')


def open_board(b, server, did, errors, bad, lang='ar', width=1440, height=1000):
    page = b.new_page(viewport={'width': width, 'height': height})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('#boardSign', timeout=60000)
    return page


def test_the_tree_says_each_point_closed_or_open_and_every_screen_counts_the_same(server, tmp_path):
    did = made_up(server, tmp_path)
    prepare_all(server, did)
    call(server, f'/api/dossiers/{did}/slots/M1-31/attest', {'answer': 'yes'})         # the composition certificate: on letterhead, signed — its point closes
    board = call(server, f'/api/dossiers/{did}/board')
    P = board['points']
    by = {s['slot_id']: s for s in board['slots']}
    assert by['M1-31']['point'] == 'closed' and P['closed'] >= 1 and P['open'] == P['required'] - P['closed']
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_board(b, server, did, errors, bad)
        assert page.inner_text('#view h1').strip() == 'شجرة الملف والنواقص'
        # the sign, the path bar and the home say the same count: closed points of the required ones
        assert page.evaluate(SIGN) == f'النقاط المغلقة: {P["closed"]} من {P["required"]}'
        assert page.get_attribute('#boardSign', 'data-closed') == str(P['closed']) and page.get_attribute('#boardSign .meter', 'aria-valuenow') == str(P['closed'])
        assert page.inner_text('#pathbar a[data-st="7"] .code').strip() == f'{P["closed"]}/{P["required"]}'
        # the open points by reason: each reason with the number of points it holds
        open_req = [s for s in board['slots'] if s['level'] == 'R' and s['point'] == 'open']
        want = {k: sum(1 for s in open_req if k in s['open_why']) for k in ('missing', 'needs_you', 'to_check', 'cross')}
        got = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#bsWhy [data-bwhy]')].map(x => [x.dataset.bwhy, +x.textContent.split(':').pop().trim()]))")
        assert got == {k: v for k, v in want.items() if v}, (got, want)
        assert page.inner_text('#bsWhy [data-bwhy="missing"]').strip() == f'بلا مستند: {want["missing"]}'
        # the tree, open points first: every row says «مفتوح» with its reason; the closed one is under «المغلقة»
        rows = page.evaluate(ROWS)
        assert rows and all(x[1] == 'open' for x in rows) and 'M1-31' not in [x[0] for x in rows]
        assert page.get_attribute('[data-f="todo"]', 'aria-pressed') == 'true' and page.inner_text('[data-f="todo"]').split()[-1] == str(len(rows))
        assert page.inner_text('tr[data-brow="M1-05"] [data-point]').strip() == 'مفتوح: بلا مستند'
        assert page.inner_text('tr[data-brow="M1-37"] [data-point]').strip() == 'مفتوح: أمر يحتاج إلى تحقُّقك'
        # help on an open row: who issues its document and how it is obtained — in Arabic in the Arabic page
        help_ = page.inner_text('tr[data-brow="M1-05"] [data-bhelp]')
        assert 'يصدر من: هيئة الدواء المصرية' in help_ and 'كيفية الحصول عليه: من هيئة الدواء المصرية.' in help_
        assert 'يُعاد استخراجه من السلطة التي أصدرته.' in page.inner_text('tr[data-brow="M1-37"] [data-bhelp]')
        assert not page.evaluate("() => /From EDA|Re-obtain|Output: print/.test(document.getElementById('view').innerText)")
        page.click('[data-f="closed"]')
        closed = page.evaluate(ROWS)
        assert ['M1-31', 'closed'] in closed and all(x[1] == 'closed' for x in closed)
        assert page.inner_text('tr[data-brow="M1-31"] [data-point]').strip() == 'مُغلق' and page.locator('tr[data-brow="M1-31"] [data-bhelp]').count() == 0
        # a reason pressed: the tree shows the open points of that reason; pressed again, all the open ones
        page.click('#bsWhy [data-bwhy="to_check"]')
        assert page.get_attribute('#bsWhy [data-bwhy="to_check"]', 'aria-pressed') == 'true' and page.get_attribute('[data-f="todo"]', 'aria-pressed') == 'true'
        shown = [x[0] for x in page.evaluate(ROWS)]
        assert sorted(shown) == sorted(s['slot_id'] for s in open_req if 'to_check' in s['open_why']) and 'M1-37' in shown
        page.click('#bsWhy [data-bwhy="to_check"]')
        assert len(page.evaluate(ROWS)) == len(rows)
        # the file still waiting for a place: said once, with the way to the proposed tree — no box of its own here
        assert 'بانتظار تحديد الموضع: مستند واحد' in page.inner_text('#unplacedNote') and page.get_attribute('#unplacedNote a', 'href') == f'#/d/{did}/tree'
        assert page.locator('#unplacedBox').count() == 0 and page.get_attribute('#bulkBtn', 'href') == f'#/d/{did}/tree'
        # the item's panel says the point in the same words
        page.click('tr[data-brow="M1-37"] [data-why]')
        page.wait_for_selector('#drawer:not([hidden]) [data-point="open"]')
        assert 'مفتوح: أمر يحتاج إلى تحقُّقك' in page.inner_text('#dBody')
        page.evaluate('() => closeDrawer()')
        # the home: the same count for this dossier
        page.goto(f'{server}/#/')
        page.wait_for_function(f"() => {{ const e = document.querySelector('[data-ready=\"{did}\"] .code'); return e && /%/.test(e.textContent); }}", timeout=60000)
        assert page.inner_text(f'[data-ready="{did}"] .code').strip() == f'{round(100 * P["closed"] / P["required"])}%'
        # in English: the same page, its names
        en = open_board(b, server, did, errors, bad, lang='en')
        assert en.evaluate(SIGN) == f'Points closed: {P["closed"]} of {P["required"]}'
        assert en.inner_text('[data-f="todo"]').startswith('Open') and en.inner_text('[data-f="closed"]').startswith('Closed')
        assert en.inner_text('tr[data-brow="M1-05"] [data-point]').strip() == 'open: no document'
        h = en.inner_text('tr[data-brow="M1-05"] [data-bhelp]')
        assert 'Issued by:' in h and 'How to get it: From EDA.' in h
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_what_is_missing_is_set_out_by_who_issues_it_and_one_request_covers_a_party(server, tmp_path):
    did = made_up(server, tmp_path, waiting=False)
    prepare_all(server, did)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_board(b, server, did, errors, bad)
        board = call(server, f'/api/dossiers/{did}/board')
        to_get = [s for s in board['slots'] if s['level'] == 'R' and s['point'] == 'open' and set(s['open_why']) & {'missing', 'non_conforming', 'unsigned', 'external', 'waiting'}]
        assert page.inner_text('[data-bv="parties"]').split()[-1] == str(len(to_get))
        page.click('[data-bv="parties"]')
        page.wait_for_selector('#partiesOut [data-party]')
        kinds = page.evaluate("() => [...document.querySelectorAll('[data-party]')].map(x => x.dataset.pkind)")
        assert kinds == sorted(kinds, key=['company', 'authority', 'api', 'other'].index) and set(kinds) == {'company', 'authority', 'api', 'other'}, kinds
        assert page.locator('#partiesOut [data-pitem]').count() == len(to_get)
        names = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('[data-party]')].map(x => [x.dataset.pkind, x.querySelector('h3').innerText.replace(/\\s+/g, ' ').trim()]))")
        assert names['company'].startswith('شركتك') and names['authority'].startswith('هيئة الدواء المصرية') and 'Example API Co.' in names['api'] and names['other'].startswith('جهات أخرى')
        # the points that are open though their documents are here are not «missing»: said in one line, with where they are finished
        hand = [s for s in board['slots'] if s['level'] == 'R' and s['point'] == 'open' and s not in to_get]
        assert hand and page.inner_text('#bsHand').strip().startswith(f'نقاط مفتوحة ومستنداتها موجودة: {len(hand)}') and page.get_attribute('#bsHand a', 'href') == f'#/d/{did}/prepare'
        assert page.locator('[data-pitem="M1-37"]').count() == 0                         # the GMP certificate is in the vault: not listed as missing
        # the company's own documents: made here — generated or drafted — or uploaded; nobody is asked for them
        assert page.locator('[data-pkind="company"] [data-preq]').count() == 0
        assert page.locator('[data-pkind="company"] [data-pgen]').count() >= 1 and page.locator('[data-pkind="company"] [data-draft]').count() >= 1
        assert page.inner_text('[data-pitem="M1-05"] [data-phow]').strip() == 'كيفية الحصول عليه: من هيئة الدواء المصرية.'
        # the item's conditions and their source, beside the station
        page.click('[data-pitem="M1-05"] [data-lib]')
        page.wait_for_selector('#drawer #libHead')
        assert 'مفتوح: بلا مستند' in page.inner_text('#libHead')
        page.evaluate('() => closeDrawer()')
        # one request to the authority for what it issues: every item ticked, the letter in Arabic, the issuer named
        page.click('[data-pkind="authority"] [data-preq]')
        page.wait_for_selector('#prGo')
        assert page.inner_text('#dTitle').strip() == 'طلب واحد من الجهة المُصدِرة'
        assert page.input_value('#prIssuer') == 'هيئة الدواء المصرية' and page.input_value('#prLang') == 'ar' and page.input_value('#prDue') == '21'
        ticks = page.evaluate("() => [...document.querySelectorAll('#prItems [data-pri]')].map(x => [x.dataset.pri, x.checked])")
        assert len(ticks) >= 3 and all(x[1] for x in ticks)
        # none ticked: said, nothing sent
        page.evaluate("() => document.querySelectorAll('#prItems [data-pri]').forEach(x => { x.checked = false; })")
        page.click('#prGo')
        page.wait_for_selector('#prErr .alert')
        assert page.inner_text('#prErr').strip() == 'حدِّد بندًا واحدًا على الأقل.'
        page.check('#prItems [data-pri="M1-05"]'); page.check('#prItems [data-pri="M1-03"]')
        page.fill('#prSig', 'A. Example'); page.fill('#prSigT', 'Regulatory Affairs Manager')
        with page.context.expect_page(timeout=90000) as letter:                           # the one letter, opened
            page.click('#prGo')
        letter.value.close()
        page.wait_for_function("() => document.querySelectorAll('[data-pkind=\"authority\"] [data-breq]').length === 2", timeout=60000)
        assert 'أُنشئ الطلب. البنود التي بانتظار جهتها الآن: 2' in page.inner_text('#toast')
        assert page.inner_text('[data-pkind="authority"] [data-pasked]').strip() == 'طُلب بالفعل: 2'
        line = page.inner_text('[data-pitem="M1-05"] [data-breq]')
        assert 'تم الطلب من' in line and 'هيئة الدواء المصرية' in line and page.get_attribute('[data-pitem="M1-05"] [data-breq] a', 'href').endswith('/letter')
        assert 'طُلب من الجهة المُصدِرة' in page.inner_text('[data-pitem="M1-05"] [data-point]')
        after = {s['slot_id']: s for s in call(server, f'/api/dossiers/{did}/board')['slots']}
        r5, r3 = after['M1-05']['request'], after['M1-03']['request']
        assert r5 and r3 and r5['batch'] and r5['batch'] == r3['batch'] and r5['issuer'] == 'هيئة الدواء المصرية' and not after['M1-04'].get('request')
        # asked again: the items already asked for are not offered
        page.click('[data-pkind="authority"] [data-preq]')
        page.wait_for_selector('#prGo')
        again = page.evaluate("() => [...document.querySelectorAll('#prItems [data-pri]')].map(x => x.dataset.pri)")
        assert 'M1-05' not in again and 'M1-03' not in again and 'M1-04' in again
        page.evaluate('() => closeDrawer()')
        # «جهات أخرى» are several parties: nothing is ticked for the person — he ticks what one party issues
        page.click('[data-pkind="other"] [data-preq]')
        page.wait_for_selector('#prGo')
        assert page.input_value('#prIssuer') == '' and not any(x for x in page.evaluate("() => [...document.querySelectorAll('#prItems [data-pri]')].map(x => x.checked)"))
        page.evaluate('() => closeDrawer()')
        # back in the tree: the request stands on its row
        page.click('[data-bv="tree"]')
        assert 'هيئة الدواء المصرية' in page.inner_text('tr[data-brow="M1-05"] [data-breq]')
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_a_certificate_is_judged_on_the_target_submission_date(server, tmp_path):
    did = dossier(server)
    doc = upload(server, did, 'M1-37', 'made-up-gmp.pdf', make_pdf_lines(tmp_path / 'g.pdf', lines_of('the GMP certificate'), 'g').read_bytes())
    cur = call(server, f'/api/dossiers/{did}/prepare/{doc["id"]}', {})['document']['id']
    today = datetime.date.today()
    put(server, f'/api/dossiers/{did}/documents/{cur}/validity', {'valid_until': (today + datetime.timedelta(days=120)).isoformat()})   # past the 90 days' warning
    call(server, f'/api/dossiers/{did}/documents/{cur}/confirm', {'cond': 'lines', 'answer': 'yes'})
    point = lambda: next(s for s in call(server, f'/api/dossiers/{did}/board')['slots'] if s['slot_id'] == 'M1-37')
    assert point()['point'] == 'closed'                                                # valid today and for 120 days, nothing asked of the person
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_board(b, server, did, errors, bad)
        assert page.input_value('#targetDate') == '' and 'لم يُحدَّد تاريخ بعد' in page.inner_text('#targetNote')
        page.click('[data-f="closed"]')
        assert page.inner_text('tr[data-brow="M1-37"] [data-point]').strip() == 'مُغلق'
        # the dossier is meant to be submitted in 150 days: the certificate will have expired by then — its point opens, and says so
        target = (today + datetime.timedelta(days=150)).isoformat()
        page.fill('#targetDate', target)
        page.click('#targetSave')
        page.wait_for_function("() => /الأيام المتبقية حتى هذا التاريخ: 150\\./.test((document.getElementById('targetNote') || {}).textContent || '')", timeout=60000)
        assert 'حُفظ تاريخ التقديم المستهدف.' in page.inner_text('#toast') and page.input_value('#targetDate') == target
        assert point()['point'] == 'open' and call(server, f'/api/dossiers/{did}/board')['target_date'] == target
        page.click('[data-f="todo"]')
        assert page.inner_text('tr[data-brow="M1-37"] [data-point]').strip().startswith('مفتوح:')
        page.click('tr[data-brow="M1-37"] [data-why]')
        page.wait_for_selector('#drawer:not([hidden])')
        assert 'قبل تاريخ التقديم المستهدف' in page.inner_text('#dBody')
        page.evaluate('() => closeDrawer()')
        # the date taken away: judged on today again
        page.fill('#targetDate', '')
        page.click('#targetSave')
        page.wait_for_function("() => /لم يُحدَّد تاريخ بعد/.test((document.getElementById('targetNote') || {}).textContent || '')", timeout=60000)
        assert 'أُزيل تاريخ التقديم المستهدف.' in page.inner_text('#toast') and point()['point'] == 'closed'
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_files_dropped_on_the_board_are_added_on_the_proposed_tree(server, tmp_path):
    did = dossier(server)
    data = make_pdf_lines(tmp_path / 'p.pdf', ['Pricing Certificate', 'Dermacure', 'Price: EGP 45.00'], 'Pricing').read_bytes()
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_board(b, server, did, errors, bad)
        page.evaluate("""b64 => { const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const dt = new DataTransfer();
            dt.items.add(new File([bytes], 'made-up-pricing.pdf', {type: 'application/pdf'}));
            document.getElementById('view').dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true})); }""", base64.b64encode(data).decode())
        page.wait_for_function("() => location.hash.endsWith('/tree')", timeout=30000)
        page.wait_for_function("() => document.querySelectorAll('[data-pw]').length === 1", timeout=120000)
        assert 'made-up-pricing.pdf' in page.inner_text('[data-pw]')
        board = call(server, f'/api/dossiers/{did}/board')
        assert len(board['unassigned']) == 1 and all(not s['documents'] for s in board['slots'])          # waiting for its place: not placed by the drop
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_station_7_fits_a_phone_in_both_views(server, tmp_path):
    did = made_up(server, tmp_path)
    prepare_all(server, did)
    errors, bad = [], []
    fits = "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ('ar', 'en'):
            page = open_board(b, server, did, errors, bad, lang=lang, width=390, height=844)
            assert page.evaluate(fits), lang
            page.click('[data-bv="parties"]')
            page.wait_for_selector('#partiesOut [data-party]')
            assert page.evaluate(fits), lang
            wide = page.evaluate("() => [...document.querySelectorAll('#boardSign, #partiesOut [data-party], #partiesOut [data-pitem], #bsHand')].filter(x => { const r = x.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; }).length")
            assert wide == 0, (lang, wide)
            page.close()
        b.close()
    assert not errors, errors
    assert not bad, bad
