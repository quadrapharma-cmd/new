"""Station 6 «التجهيز والمراجعة» with «الخزنة» (eBOX stage 3, 16/11/2026). The owner's words: «عايز خزنة للملفات اللي اتقرت و اتقطعت و
اتجهزت اشوفها و اطلع عليها ذاخل البرنامج بدون تنزيل و ابقي شايف قبل ما ندخل علي التكوين اني جاهز». So:
  - a sign that says the documents are ready for the dossier to be composed, or what is left — each line leading to what it counts;
  - every document once, under its tree point (said closed, or open with its reason), with what was done to it on its way;
  - «عرض ومراجعة»: the document over the whole page, its pages or its words, with nothing downloaded; what was read from it and its
    conditions beside it, answered there; the document before and after it one press away;
  - the item's conditions and their source in the side panel, without leaving the station;
  - while «تجهيز الكل» runs, a document's own buttons wait and say so.
In a real browser, on the program served by its own engine, with made-up files."""
import io
import json
import urllib.request
import pytest
from dossier_engine import pdfcraft, pages as _pages

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, page_of, upload          # noqa: F401 — the shared server fixture

SHOWN = "() => { const i = document.getElementById('pgImg'); return !!i && i.complete && i.naturalWidth > 0 && !document.getElementById('reader').hidden; }"
CLOSED = "() => document.getElementById('reader').hidden"
STATS = "() => document.getElementById('readyStats').textContent.trim()"
LINES = "() => [...document.querySelectorAll('#readyLines [data-rs]')].map(x => x.dataset.rs)"
BUCKETS = "() => [...document.querySelectorAll('#offList [data-pdoc]')].map(x => [x.dataset.vslot, x.dataset.bucket])"
POINT = "sid => { const c = document.querySelector(`#offList .vpoint[data-vpoint=\"${sid}\"] [data-point]`); return c ? [c.dataset.point, c.textContent.trim()] : null; }"
DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def call(server, path, body=None, method=None):
    req = urllib.request.Request(server + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'}, method=method or ('GET' if body is None else 'POST'))
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def lines_of(what):
    return [f'A made-up document for {what}', 'Dermacure topical powder (made up)', 'Example Pharm Co.', 'Neomycin sulphate', 'dated 01/02/2026']


def made_up(server, tmp_path, waiting=True):
    """Four documents in their items — a company letter (asked whether it is on letterhead), a two-page stability summary, a GMP
    certificate (its validity date and production lines are for the person), a Word file where a PDF is asked — and one still
    waiting for a place."""
    import docx
    import httpx
    did = dossier(server)
    upload(server, did, 'M1-31', 'made-up-composition.pdf', make_pdf_lines(tmp_path / 'c.pdf', lines_of('the composition certificate'), 'c').read_bytes())
    two = _pages.merge([make_pdf_lines(tmp_path / 's1.pdf', lines_of('the stability summary'), 's1').read_bytes(),
                        make_pdf_lines(tmp_path / 's2.pdf', ['Second page of the made-up stability summary', 'Stored at 30 C / 65 % RH for a made-up while'], 's2').read_bytes()])
    upload(server, did, 'P-16', 'made-up-stability.pdf', two)
    upload(server, did, 'M1-37', 'made-up-gmp.pdf', make_pdf_lines(tmp_path / 'g.pdf', lines_of('the GMP certificate'), 'g').read_bytes())
    d = docx.Document(); d.add_paragraph('Made-up justification of the specification'); d.add_paragraph('The limits follow the made-up pharmacopoeia.')
    buf = io.BytesIO(); d.save(buf)
    upload(server, did, 'P-13', 'made-up-justification.docx', buf.getvalue(), DOCX)
    if waiting:
        r = httpx.post(f'{server}/api/dossiers/{did}/unplaced', files={'files': ('made-up-waiting.pdf', make_pdf_lines(tmp_path / 'w.pdf', ['A note about nothing in particular'], 'w').read_bytes())},
                       data={'meta': '{}'}, headers={'X-DB': '1'})
        assert r.status_code in (200, 201), r.text[:300]
    return did


def prepare_all(server, did):
    for d in call(server, f'/api/dossiers/{did}/prepare')['placed']:
        call(server, f'/api/dossiers/{did}/prepare/{d["id"]}', {})


def open_station(b, server, did, errors, bad, n, lang='ar', width=1440, height=1000):
    page = b.new_page(viewport={'width': width, 'height': height})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('response', lambda r: bad.append(f'{r.status} {r.url}') if r.status >= 400 else None)
    page.goto(f'{server}/#/d/{did}/prepare')
    page.wait_for_function(f"() => document.querySelectorAll('#offList [data-pdoc]').length === {n} && !!document.getElementById('readyStats').textContent", timeout=60000)
    return page


def test_the_sign_says_what_is_left_and_the_vault_holds_every_document_once(server, tmp_path):
    did = made_up(server, tmp_path)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_station(b, server, did, errors, bad, 4)
        assert page.inner_text('#view h1').strip() == 'التجهيز والمراجعة'
        # the sign: not ready, and what is left — each line leads to what it counts
        assert page.get_attribute('#readySign', 'data-ready') == 'no' and page.inner_text('#readyT').strip() == 'غير جاهز بعد لتكوين الملف'
        assert page.evaluate(STATS) == 'في الخزنة: 4 · جاهز: 0 · تحتاج إجراءً منك: 0 · لم يُجهَّز بعد: 4'
        assert page.evaluate(LINES) == ['not_prepared', 'waiting', 'missing']
        assert page.inner_text('[data-rs="not_prepared"]').strip().startswith('لم يُجهَّز بعد: 4')
        assert 'بانتظار تحديد الموضع: مستند واحد' in page.inner_text('[data-rs="waiting"]') and page.get_attribute('[data-rs="waiting"] a', 'href') == f'#/d/{did}/tree'
        assert 'بنود مطلوبة بلا مستند' in page.inner_text('[data-rs="missing"]') and page.get_attribute('[data-rs="missing"] a', 'href') == f'#/d/{did}/board'
        assert page.is_hidden('#readyNext')
        # «الخزنة»: every document once, under its module and its tree point; the point is said open, with its reason
        assert page.inner_text('#office h3').strip().startswith('الخزنة') and page.inner_text('#offN').strip() == '4'
        cards = page.evaluate("() => [...document.querySelectorAll('#view [data-pdoc]')].map(x => x.dataset.pdoc)")
        assert len(cards) == 4 == len(set(cards)), cards
        assert page.evaluate("() => [...document.querySelectorAll('#offList .vmod')].map(x => x.textContent.trim())") == ['Module 1', 'Module 3']
        assert page.evaluate("() => [...document.querySelectorAll('#offList .vpoint')].map(x => x.dataset.vpoint)") == ['M1-31', 'M1-37', 'P-13', 'P-16']
        for sid in ('M1-31', 'M1-37', 'P-13', 'P-16'):
            assert page.evaluate(POINT, sid) == ['open', 'مفتوح: لم يُجهَّز بعد'], sid
        assert page.locator('#offList [data-vread]').count() == 0                       # not prepared yet is said once, by the document's state
        assert page.inner_text('[data-vslot="P-16"] [data-vname]').strip() == 'made-up-stability.pdf'
        assert page.inner_text('[data-vslot="P-16"] [data-vleaf]').strip().startswith('3.2.P.8') and 'اسمه في الملف' in page.inner_text('[data-vslot="P-16"]')
        assert page.locator('#offList .chip:has-text("لم يُجهَّز بعد")').count() >= 4
        # «عرضها» on the line: the list shows the documents that line counts
        page.click('[data-rsf="not_prepared"]')
        assert page.get_attribute('[data-vf="not_prepared"]', 'aria-pressed') == 'true' and page.locator('#offList [data-pdoc]').count() == 4
        assert page.evaluate("() => [...document.querySelectorAll('#vaultF [data-vf]')].map(x => x.textContent.replace(/\\s+/g, ' ').trim())") == ['الكل 4', 'تحتاج إجراءً منك 0', 'جاهز 0', 'لم يُجهَّز بعد 4']
        # «تجهيز الكل»: read, fixed, checked — and the sign counts again
        page.click('#prepAll')
        page.wait_for_function("() => !S.prepBusy && !S.prepDoing && S.prep && S.prep.placed.length === 4 && S.prep.placed.every(d => d.prepared) && document.getElementById('readyStats').textContent.includes('لم يُجهَّز بعد: 0')", timeout=240000)
        assert page.evaluate(STATS) == 'في الخزنة: 4 · جاهز: 1 · تحتاج إجراءً منك: 3 · لم يُجهَّز بعد: 0'
        assert page.evaluate(LINES) == ['needs_you', 'waiting', 'cross', 'missing'] and page.get_attribute('#readySign', 'data-ready') == 'no'
        # the documents he was looking at have all moved on: the list is not left empty under the choice he had made
        assert page.get_attribute('[data-vf="all"]', 'aria-pressed') == 'true'
        assert sorted(page.evaluate(BUCKETS)) == [['M1-31', 'needs_you'], ['M1-37', 'needs_you'], ['P-13', 'needs_you'], ['P-16', 'ready']]
        # ready, and the card says what was done to the document on its way. Its point is still open: the stability summary was
        # read as one, and the cross-document check now asks for the batches — said on the point, and on the sign with where it
        # is looked at (a point stayed open under a «ready» document, and nothing said why)
        page.click('[data-vf="ready"]')
        assert page.evaluate(BUCKETS) == [['P-16', 'ready']] and page.evaluate(POINT, 'P-16') == ['open', 'مفتوح: ملاحظة من فحوص التطابق بين المستندات']
        assert page.inner_text('[data-rs="cross"]').strip().startswith('ملاحظات فحوص التطابق بين المستندات على هذه المستندات: 1') and page.get_attribute('[data-rs="cross"] a', 'href') == f'#/d/{did}/checks'
        assert page.inner_text('[data-vslot="P-16"] [data-vread="text"]').strip() == 'قُرئ من نصه'
        assert page.inner_text('[data-vslot="P-16"] [data-vfixed]').strip() == 'إصلاحات البرنامج: 1'
        assert 'جاهز' in page.inner_text('[data-vslot="P-16"]') and not page.evaluate("() => document.querySelector('[data-vslot=\"P-16\"] details[data-vcond]').open")
        # needs you: the reason on the point, and the conditions open on the card
        page.click('[data-rsf="needs_you"]')
        assert page.get_attribute('[data-vf="needs_you"]', 'aria-pressed') == 'true'
        assert sorted(x[0] for x in page.evaluate(BUCKETS)) == ['M1-31', 'M1-37', 'P-13']
        assert page.evaluate("() => [...document.querySelectorAll('#offList details[data-vcond]')].every(x => x.open)")
        assert page.evaluate(POINT, 'M1-31') == ['open', 'مفتوح: أمر يحتاج إلى تحقُّقك']
        assert page.evaluate(POINT, 'P-13') == ['open', 'مفتوح: مستند يحتاج إجراءً منك، أمر يحتاج إلى تحقُّقك']
        # a choice that matches nothing says so
        page.click('[data-vf="not_prepared"]')
        assert page.inner_text('#vaultNone').strip() == 'لا يوجد مستند يطابق اختيارك.'
        page.click('[data-vf="all"]')
        page.fill('#offQ', 'stability')
        page.wait_for_function("() => document.querySelectorAll('#offList [data-pdoc]').length === 1")
        assert page.evaluate(BUCKETS) == [['P-16', 'ready']]
        page.fill('#offQ', '')
        page.wait_for_function("() => document.querySelectorAll('#offList [data-pdoc]').length === 4")
        # an answer given on the card: the document is ready, its point closes, the sign counts again
        page.click('[data-vslot="M1-31"] [data-pslotans][data-ans="yes"]')
        page.wait_for_function("() => (document.querySelector('[data-vslot=\"M1-31\"]') || {dataset: {}}).dataset.bucket === 'ready'", timeout=60000)
        assert page.evaluate(STATS) == 'في الخزنة: 4 · جاهز: 2 · تحتاج إجراءً منك: 2 · لم يُجهَّز بعد: 0'
        assert page.evaluate(POINT, 'M1-31') == ['closed', 'مُغلق']
        assert page.evaluate('() => location.hash').endswith('/prepare')
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_the_sign_turns_ready_and_leads_to_the_dossier_tree(server, tmp_path):
    did = dossier(server)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_station(b, server, did, errors, bad, 0)
        # nothing in an item yet: said, with where documents are added
        assert page.inner_text('#readyT').strip() == 'لا يوجد مستند في البنود بعد' and page.is_hidden('#readyNext')
        assert 'أضِف مستنداتك من «الشجرة المقترحة»' in page.inner_text('#vaultEmpty') and page.get_attribute('#prepAdd', 'href') == f'#/d/{did}/tree'
        for sid, name in (('P-16', 'made-up-one.pdf'), ('P-05', 'made-up-two.pdf')):          # their words name no kind of document: nothing is read into the data
            upload(server, did, sid, name, make_pdf_lines(tmp_path / name, lines_of(sid), name).read_bytes())
        page.evaluate('() => paintPrepare()')
        page.wait_for_function("() => document.querySelectorAll('#offList [data-pdoc]').length === 2", timeout=60000)
        assert page.get_attribute('#readySign', 'data-ready') == 'no' and 'pri' in page.get_attribute('#prepAll', 'class')
        page.click('#prepAll')
        page.wait_for_function("() => document.getElementById('readySign').dataset.ready === 'yes' && !S.prepBusy && !S.prepDoing", timeout=240000)
        # ready: said in the sign, with the way on — what is still missing belongs to the next station, and is said so
        assert 'المستندات جاهزة لتكوين الملف' in page.inner_text('#readyT') and 'ok' in page.get_attribute('#readySign', 'class')
        assert page.evaluate(STATS) == 'في الخزنة: 2 · جاهز: 2 · تحتاج إجراءً منك: 0 · لم يُجهَّز بعد: 0'
        assert page.evaluate(LINES) == ['missing'] and 'تُستكمل في المحطة التالية' in page.inner_text('[data-rs="missing"]')
        assert page.is_visible('#readyNext') and page.get_attribute('#readyNext', 'href') == f'#/d/{did}/board'
        assert page.inner_text('#readyNext').strip().startswith('التالي: شجرة الملف والنواقص')
        assert 'pri' not in page.get_attribute('#prepAll', 'class').split()             # nothing left for «تجهيز الكل» to do: the way on is the main button
        assert page.locator('#offList [data-pgo]').count() == 0
        page.click('#readyNext')
        page.wait_for_selector('h1:has-text("شجرة الملف والنواقص")', timeout=60000)
        # the same station in English: its names
        en = open_station(b, server, did, errors, bad, 2, lang='en')
        assert en.inner_text('#view h1').strip() == 'Preparation and review' and en.inner_text('#office h3').strip().startswith('The vault')
        assert 'The documents are ready for the dossier to be composed' in en.inner_text('#readyT')
        assert en.evaluate(STATS) == 'In the vault: 2 · Ready: 2 · Need you: 0 · Not prepared yet: 0'
        assert en.evaluate(POINT, 'P-16') == ['closed', 'closed'] and en.inner_text('[data-vslot="P-16"] [data-offpages]').strip() == 'View and review'
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_view_and_review_shows_a_document_inside_the_program_with_nothing_downloaded(server, tmp_path):
    did = made_up(server, tmp_path, waiting=False)
    prepare_all(server, did)
    errors, bad, downloads, opened = [], [], [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_station(b, server, did, errors, bad, 4)
        page.on('download', lambda d: downloads.append(d.suggested_filename))
        page.context.on('page', lambda x: opened.append(x.url))
        # «عرض ومراجعة»: the document over the whole page, drawn here
        page.click('[data-vslot="P-16"] [data-offpages]')
        page.wait_for_function(SHOWN, timeout=60000)
        assert page.evaluate("() => { const r = document.getElementById('reader').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width) === innerWidth, Math.round(r.height) === innerHeight]; }") == [0, 0, True, True]
        assert page.get_attribute('#reader', 'role') == 'dialog' and page.get_attribute('#reader', 'aria-label') == 'عرض ومراجعة'
        assert page.evaluate("() => document.getElementById('pgImg').src.startsWith('blob:')")
        leaf = page.evaluate("() => docLeaf(S.prep.placed.find(x => x.slot_id === 'P-16'))")
        assert page.inner_text('#rdName').strip() == 'made-up-stability.pdf'             # headed by the file's own name, as its card is
        assert leaf and '3.2.P.8' in page.inner_text('#rdSub') and f'اسمه في الملف: {leaf}' in page.inner_text('#rdSub')
        assert page.inner_text('#rdDocNo').strip() == '4 من 4' and page.is_disabled('#rdNextDoc') and page.is_enabled('#rdPrevDoc')
        assert 'جاهز' in page.inner_text('#rdState')
        assert page.is_visible('#rdSide') and 'ما قُرئ منه، وشروطه' in page.inner_text('#rdSide') and 'قُرئ من نصه' in page.inner_text('#rdSide')
        # its pages: two — the buttons, the slider and the keyboard turn them over
        assert page.inner_text('#pgNo').strip() == '1 من 2' and page.is_disabled('#pgPrev') and page.is_visible('#pgSlide')
        page.keyboard.press('PageDown')
        page.wait_for_function("() => document.getElementById('pgNo').textContent.trim() === '2 من 2'")
        page.wait_for_function(SHOWN, timeout=60000)
        assert page.is_disabled('#pgNext')
        page.keyboard.press('ArrowRight')                                              # in a right-to-left page the page before is to the right
        page.wait_for_function("() => document.getElementById('pgNo').textContent.trim() === '1 من 2'")
        page.wait_for_function(SHOWN, timeout=60000)
        # larger, and back
        w0 = page.evaluate("() => document.getElementById('pgImg').naturalWidth")
        page.click('#pgZoom')
        page.wait_for_function("w => document.getElementById('pgImg').naturalWidth > w", arg=w0, timeout=60000)
        assert page.evaluate("() => document.getElementById('rdPage').classList.contains('zoom')") and page.inner_text('#pgZoom').strip() == 'ملء العرض'
        page.click('#pgZoom')
        page.wait_for_function("w => document.getElementById('pgImg').naturalWidth === w", arg=w0, timeout=60000)
        assert page.inner_text('#pgZoom').strip() == 'تكبير'
        # a word found in it: its page shown, its place lit
        page.fill('#pgQ', 'made-up while')
        page.press('#pgQ', 'Enter')
        page.wait_for_selector('.pghit', timeout=60000)
        assert page.inner_text('#pgHits').strip() == 'المواضع: 1' and page.inner_text('#pgNo').strip() == '2 من 2'
        # the document before it, one press away: a Word file — its words, said to be its words
        page.click('#rdPrevDoc')
        page.wait_for_function("() => (document.getElementById('pgText') || {hidden: true}).hidden === false && /Made-up justification/.test(document.getElementById('pgText').textContent)", timeout=60000)
        assert page.inner_text('#rdDocNo').strip() == '3 من 4' and '3.2.P.5.6' in page.inner_text('#rdSub') and page.inner_text('#rdName').strip() == 'made-up-justification.docx'
        assert page.inner_text('#pgAsText').strip() == 'هذا نص المستند؛ أما شكله فيُرى بفتحه في برنامجه.'
        assert page.is_hidden('#pgWrap') and page.locator('#pgTurn').count() == 0 and page.locator('#pgZoom').count() == 0
        word = page.evaluate("() => S.prep.placed.find(x => x.slot_id === 'P-13').id")
        assert page.get_attribute('#rdFile', 'href').endswith(f'/documents/{word}/file') and page.get_attribute('#rdFile', 'target') == '_blank'
        assert 'يحتاج إجراءً منك' in page.inner_text('#rdState')
        # Escape closes it, and the station is as it was
        page.keyboard.press('Escape')
        page.wait_for_function(CLOSED)
        assert page.evaluate('() => location.hash').endswith('/prepare') and page.locator('#offList [data-pdoc]').count() == 4
        # a third party's certificate: looked at and turned, never cut or reordered — and its conditions answered beside its pages
        page.click('[data-vslot="M1-37"] [data-vthumb]')                                # the small page on the card opens it too
        page.wait_for_function(SHOWN, timeout=60000)
        assert page.locator('#pgTurn').count() == 1 and page.locator('#pgDel').count() == 0 and page.locator('#pgFirst').count() == 0
        assert page.locator('#rdSide .prepcond[data-st="check"]').count() == 2
        page.fill('#rdSide [data-pdate]', '2031-01-31')
        page.click('#rdSide [data-pdatego]')
        page.wait_for_function("() => document.querySelectorAll('#rdSide .prepcond[data-st=\"check\"]').length === 1", timeout=60000)
        assert not page.evaluate(CLOSED) and page.evaluate(SHOWN)                       # still on the document
        page.click('#rdSide [data-pconf][data-cond="lines"][data-ans="yes"]')
        page.wait_for_function("() => /جاهز/.test(document.getElementById('rdState').textContent) && !document.querySelector('#rdSide .prepcond[data-st=\"check\"]')", timeout=60000)
        assert 'أكّدتَه أنت' in page.inner_text('#rdSide')
        page.click('#pgBack')
        page.wait_for_function(CLOSED)
        page.wait_for_function("() => (document.querySelector('[data-vslot=\"M1-37\"]') || {dataset: {}}).dataset.bucket === 'ready'", timeout=60000)
        assert page.evaluate(POINT, 'M1-37') == ['closed', 'مُغلق']
        assert page.evaluate(STATS) == 'في الخزنة: 4 · جاهز: 2 · تحتاج إجراءً منك: 2 · لم يُجهَّز بعد: 0'
        b.close()
    assert downloads == [] and opened == [], (downloads, opened)                         # nothing was downloaded, nothing opened outside the program
    assert not errors, errors
    assert not bad, bad


def test_the_items_conditions_and_their_source_open_beside_the_station(server, tmp_path):
    did = made_up(server, tmp_path, waiting=False)
    errors, bad = [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_station(b, server, did, errors, bad, 4)
        page.click('.vpoint[data-vpoint="M1-37"] [data-lib]')
        page.wait_for_selector('#drawer #libHead', timeout=30000)
        assert page.inner_text('#dTitle').strip() == 'شروط البند ومصدرها'
        head = page.inner_text('#libHead')
        assert '1.2.4.1' in head and 'مفتوح: لم يُجهَّز بعد' in head
        page.wait_for_function("() => { const c = document.getElementById('itemCond'); return !c || !c.querySelector('.skeleton'); }", timeout=30000)
        body = page.inner_text('#dBody')
        assert 'شروطه قبل الرفع' in body and 'NP.CAPP.065' in page.inner_text('#itemCond'), body[:300]      # each condition with the source that says it
        assert page.locator('#dBody .finding .code').count() >= 1 and page.inner_text('#dBody .finding .code').strip()      # why it is required, with its source
        if page.locator('#libItem').count():
            assert page.get_attribute('#libItem', 'target') == '_blank' and '#r-' in page.get_attribute('#libItem', 'href')       # its record in the library, in a tab of its own
        assert page.evaluate('() => location.hash').endswith('/prepare') and page.locator('#offList [data-pdoc]').count() == 4   # the station is still under it
        page.click('#libToItem')
        page.wait_for_selector('#drawer [data-pgv]', timeout=30000)                      # the item itself, from there
        page.evaluate('() => closeDrawer()')
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_while_everything_is_being_prepared_a_documents_buttons_wait_and_say_so(server, tmp_path):
    did = made_up(server, tmp_path, waiting=False)
    errors, bad, posts = [], [], []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = open_station(b, server, did, errors, bad, 4)
        held = []

        def hold(r):
            if r.request.method == 'POST':
                posts.append(r.request.url)
                if not held:
                    held.append(r)                                                    # the first document's preparation takes its time
                    return
            r.continue_()
        page.route('**/api/dossiers/*/prepare/*', hold)
        page.click('#prepAll')
        for _ in range(100):
            if held:
                break
            page.wait_for_timeout(100)
        assert held and page.evaluate('() => !!S.prepBusy')
        said = "() => /جارٍ تجهيز المستندات الآن/.test(document.getElementById('toast').textContent) && !document.getElementById('toast').hidden"
        gone = "() => { document.getElementById('toast').hidden = true; document.getElementById('toast').textContent = ''; }"
        # «تجهيز الكل» pressed again: one run at a time
        page.click('#prepAll')
        page.wait_for_function(said)
        page.evaluate(gone)
        # «تجهيز» of another document: waits, and says so — the button is not left dead
        other = page.locator('[data-vslot="P-16"] [data-pgo]')
        other.click()
        page.wait_for_function(said)
        assert other.is_enabled()
        page.evaluate(gone)
        # the library's panel is only read: it opens meanwhile
        page.click('.vpoint[data-vpoint="P-16"] [data-lib]')
        page.wait_for_selector('#drawer #libHead', timeout=30000)
        page.evaluate('() => closeDrawer()')
        held[0].continue_()
        page.wait_for_function("() => !S.prepBusy && !S.prepDoing && S.prep.placed.every(d => d.prepared)", timeout=240000)
        assert len(posts) == 4 == len(set(posts)), posts                                 # each document prepared once
        b.close()
    assert not errors, errors
    assert not bad, bad


def test_station_6_and_the_reader_fit_a_phone(server, tmp_path):
    did = made_up(server, tmp_path)
    prepare_all(server, did)
    errors, bad = [], []
    fits = "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ('ar', 'en'):
            page = open_station(b, server, did, errors, bad, 4, lang=lang, width=390, height=844)
            assert page.evaluate(fits), lang                                           # the page does not scroll sideways
            wide = page.evaluate("() => [...document.querySelectorAll('#readySign, #office, #offList .vdoc, #offList .vpoint, #vaultF')].filter(x => { const r = x.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; }).map(x => x.id || x.className)")
            assert wide == [], (lang, wide)
            page.click('[data-vslot="P-16"] [data-offpages]')
            page.wait_for_function(SHOWN, timeout=60000)
            out = page.evaluate("() => [...document.querySelectorAll('#reader .rd-top > *, #reader .rd-main > *, #pgImg, #rdSide')].filter(x => x.offsetParent !== null).filter(x => { const r = x.getBoundingClientRect(); return r.left < -1 || r.right > innerWidth + 1; }).map(x => x.id || x.className || x.tagName)")
            assert out == [], (lang, out)
            box = page.locator('#pgBack').bounding_box()
            assert box and box['y'] >= 0 and box['y'] + box['height'] <= 844 and box['x'] >= 0 and box['x'] + box['width'] <= 390, box   # the way out is in sight
            page.click('#pgBack')
            page.wait_for_function(CLOSED)
            page.close()
        b.close()
    assert not errors, errors
    assert not bad, bad
