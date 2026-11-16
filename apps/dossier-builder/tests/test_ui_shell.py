"""eBOX's shell (stage 1, 16/11/2026): the name, the home with the library beside «ملفاتي», the path of nine stations with one «التالي»,
and the menu ordered as the path (the other tools under their own headings). In a real browser, in Arabic, on a desk and on a phone."""
import socket, threading, time
import pytest

pw = pytest.importorskip('playwright.sync_api')
PROFILE = {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]}


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


@pytest.fixture(scope='module')
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def new_page(browser, errors, width=1440, height=900):
    page = browser.new_page(viewport={'width': width, 'height': height})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    return page


BOX = "s => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"
HERE = "() => [...document.querySelectorAll('#pathbar .sts a.here')].map(a => +a.dataset.st)"


def test_home_has_the_library_beside_my_dossiers(server, browser):
    errors = []
    page = new_page(browser, errors)
    page.goto(server + '/#/')
    page.wait_for_selector('#homeAu .librow')
    assert page.title() == 'eBOX' and 'eBOX' in page.inner_text('.logo') and page.inner_text('#view .hero .eyebrow').strip() == 'eBOX'
    assert page.inner_text('#view h1').strip() == 'تجهيز ملفات التسجيل الموحّد بذكاء'
    # the two cards side by side: the library («المكتبة التنظيمية») and «ملفاتي»
    au, mine = page.evaluate(BOX, '#homeAu'), page.evaluate(BOX, '#homeMine')
    assert abs(au[1] - mine[1]) < 4 and (au[2] <= mine[0] + 1 or mine[2] <= au[0] + 1), (au, mine)
    assert 'المكتبة التنظيمية' in page.inner_text('#homeAu h2') and 'ملفاتي' in page.inner_text('#homeMine h2')
    # every authority the program builds for: its guidelines open in the library (another tab), and a dossier can be started for it
    lib = page.get_attribute('#libAll', 'href')
    assert lib.startswith('https://claude.ai/') and page.get_attribute('#libAll', 'target') == '_blank'
    rows = page.locator('#libList .librow')
    assert rows.count() >= 5
    for i in range(rows.count()):
        a = rows.nth(i).locator('a')
        assert a.get_attribute('href').startswith(lib + '#') and a.get_attribute('target') == '_blank' and rows.nth(i).locator('[data-libnew]').count() == 1
    # the list is searched by country or authority, in either language
    shown = "() => [...document.querySelectorAll('#libList .librow')].filter(x => !x.hidden).length"
    page.fill('#libQ', 'SFDA')
    assert page.evaluate(shown) == 1 and 'SFDA' in page.inner_text('#libList .librow:not([hidden])')
    page.fill('#libQ', 'السعودية')
    assert page.evaluate(shown) == 1
    page.fill('#libQ', 'no such country')
    assert page.evaluate(shown) == 0 and page.is_visible('#libNone') and page.inner_text('#libNone') == 'لا توجد دولة أو جهة مطابقة.'
    page.fill('#libQ', '')
    assert page.evaluate(shown) == rows.count() and not page.is_visible('#libNone')
    # the path: nine stations, this screen the first
    assert page.locator('#pathbar .sts a').count() == 9 and page.evaluate(HERE) == [1] and page.locator('#pathNext').count() == 0
    assert [page.locator('#pathbar .sts a').nth(i).inner_text().split('\n')[-1].strip() for i in (0, 1, 8)] == ['الرئيسية', 'الدولة', 'التصدير']
    # «بدء ملف لهذه الدولة»: the wizard opens with the country already chosen, on the stations of the country, the upload and the reading
    page.fill('#libQ', 'SFDA')
    page.click('#libList .librow:not([hidden]) [data-libnew]')
    page.wait_for_selector('#auCard')
    assert page.evaluate('() => location.hash') == '#/new' and 'SFDA' in page.inner_text('#auName')
    assert page.input_value('#auCountry') not in ('', 'EG') and page.evaluate(HERE) == [2, 3, 4]
    page.click('#wizNext')
    page.wait_for_function("() => document.querySelectorAll('#pathbar .sts a.here').length === 1")
    assert page.evaluate(HERE) == [5]                                                  # the product and its answers decide the proposed tree
    assert not errors, errors
    page.close()


def test_home_stacks_on_a_phone(server, browser):
    errors = []
    page = new_page(browser, errors, 390, 844)
    page.goto(server + '/#/')
    page.wait_for_selector('#homeAu .librow')
    au, mine = page.evaluate(BOX, '#homeAu'), page.evaluate(BOX, '#homeMine')
    assert mine[1] >= au[3] - 1, (au, mine)                                            # one above the other
    assert page.evaluate('() => document.documentElement.scrollWidth - window.innerWidth') <= 2
    assert page.locator('#pathbar .sts a').count() == 9                                # the path stays, scrolling inside its own bar
    assert not errors, errors
    page.close()


def test_the_menu_follows_the_path(server, browser):
    errors = []
    page = new_page(browser, errors)
    page.goto(server + '/#/')
    page.wait_for_selector('#homeAu .librow')
    assert not page.is_visible('#navD')                                                # no dossier open: its pages are not offered
    main = [a.get_attribute('data-r') for a in page.locator('#nav > a').all()]
    assert main[:3] == ['home', 'dossiers', 'library'] and {'variations', 'package', 'suite', 'faults'} <= set(main[3:]), main
    assert page.get_attribute('#nav a[data-r="library"]', 'target') == '_blank'
    did = page.evaluate("""async p => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
        body: JSON.stringify({name: 'Dermacure (made up)', profile: p, product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""", PROFILE)
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('h1:has-text("شجرة الملف والنواقص")')
    page.wait_for_selector('#pathNext')
    assert page.is_visible('#navD')
    # the dossier's pages carry the number of their station; the tools that are on no station come after, without one
    stations = {a.get_attribute('data-r'): a.locator('.stn').inner_text() for a in page.locator('#navD a').all() if a.locator('.stn').count()}
    assert stations == {'prepare': '6', 'office': '6', 'board': '7', 'checks': '8', 'review': '8', 'export': '9'}, stations
    tools = [a.get_attribute('data-r') for a in page.locator('#navD a').all() if not a.locator('.stn').count()]
    assert tools == ['guide', 'data', 'publisher', 'search', 'audit'], tools
    names = {a.get_attribute('data-r'): a.inner_text().split('\n')[-1].strip() for a in page.locator('#navD a').all()}
    assert names['office'] == 'مراجعة المستندات وتعديلها' and names['board'] == 'شجرة الملف والنواقص' and names['guide'] == 'الخطوة التالية' and names['publisher'] == 'هيكل المخرجات'
    # the path: the first five stations are behind an open dossier, this screen is the seventh, and there is one «التالي»
    assert page.evaluate(HERE) == [7] and page.locator('#pathbar .sts a.done').count() >= 5 and page.locator('#pathNext').count() == 1
    nxt = page.inner_text('#pathNext')
    assert nxt.startswith('التالي: التحقق') and page.get_attribute('#pathNext', 'href') == f'#/d/{did}/checks'
    page.click('#pathNext')
    page.wait_for_function("() => [...document.querySelectorAll('#pathbar .sts a.here')].map(a => a.dataset.st).join() === '8'")
    assert page.get_attribute('#nav a[aria-current="page"]', 'data-r') == 'checks'
    page.click('#pathbar .sts a[data-st="6"]')                                         # a station is a way back, too
    page.wait_for_function("() => location.hash.endsWith('/prepare')")
    assert not errors, errors
    page.close()


FIT = """() => { const bar = document.getElementById('pathbar'), s = bar.querySelector('.sts'), box = s.getBoundingClientRect();
  const st = [...s.querySelectorAll('a')].map(a => { const r = a.getBoundingClientRect(), nm = a.querySelector('.nm');
    return { n: +a.dataset.st, here: a.classList.contains('here'), inside: r.left >= box.left - 1 && r.right <= box.right + 1, named: !!nm && getComputedStyle(nm).display !== 'none', label: a.getAttribute('aria-label') }; });
  return { over: s.scrollWidth - s.clientWidth, fit: [...bar.classList].filter(c => c.startsWith('fit')), st, next: (document.getElementById('pathNext') || {}).innerText || '' }; }"""


@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_the_path_bar_shows_its_nine_stations_at_every_width(server, browser, lang):
    """At 1366 and 1280 px (an ordinary laptop) the last stations were out of sight, in a bar with no scrollbar. Now the bar tightens
    in steps while the names do not fit: the stations behind keep their mark, then «التالي» alone, then only this screen's station
    is named — every station stays in sight, with its name for a screen reader and in its tooltip. A phone's bar scrolls."""
    errors = []
    page = new_page(browser, errors, 1920, 900)
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    page.goto(server + '/#/')
    page.wait_for_selector('#homeAu .librow')
    did = page.evaluate("""async p => (await (await fetch('/api/dossiers', {method: 'POST', headers: {'X-DB': '1', 'Content-Type': 'application/json'},
        body: JSON.stringify({name: 'Dermacure (made up)', profile: p, product: {name: 'Dermacure 20 mg', dosageform: 'cream', manufacturer: 'Example Pharm'}, envelope: {}})})).json()).id""", PROFILE)
    page.goto(f'{server}/#/d/{did}/prepare')                                           # the longest «التالي» of all the screens
    page.wait_for_selector('#pathNext')
    for width in (1920, 1440, 1366, 1280, 1100):
        page.set_viewport_size({'width': width, 'height': 900})
        page.wait_for_timeout(400)                                                     # the bar fits itself again a moment after a resize
        m = page.evaluate(FIT)
        assert m['over'] <= 1 and all(x['inside'] for x in m['st']), (width, m)
        assert [x['n'] for x in m['st']] == list(range(1, 10)) and all(x['label'] for x in m['st'])
        assert [x['n'] for x in m['st'] if x['here']] == [6] and all(x['named'] for x in m['st'] if x['here']), (width, m)
        assert m['next'].strip(), (width, m)
        if width == 1920:
            assert m['fit'] == [] and all(x['named'] for x in m['st']), m                # room for every name
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(400)
    m = page.evaluate(FIT)
    assert all(x['inside'] for x in m['st'] if x['here']) and len(m['st']) == 9, m       # a phone: this screen's station in sight, the rest by scrolling
    assert page.evaluate('() => document.documentElement.scrollWidth - window.innerWidth') <= 2
    assert not errors, errors
    page.close()
