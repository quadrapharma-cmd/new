"""The country in the browser (Playwright): the wizard opens with «where will this dossier be submitted?»; the country sets the
authority, its Module 1 and its own questions; the board, the item drawer, the publisher and the export follow the dossier's
authority; Egypt stays as it was."""
import socket, threading, time, urllib.request, json
import pytest

pw = pytest.importorskip('playwright.sync_api')
OUT = '/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/arabic'


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws'), auth_enabled=False), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


def call(url, path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url + path, headers={'X-DB': '1'}), timeout=30).read())


def open_page(p, server, errors):
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': 1440, 'height': 1000})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','ar')")
    return b, page


def test_the_wizard_starts_with_the_country_and_builds_for_its_authority(server):
    errors = []
    with pw.sync_playwright() as p:
        b, page = open_page(p, server, errors)
        page.goto(f'{server}/#/new')
        page.wait_for_selector('#auCountry')
        # Egypt first, as it always was: its own documents cards, eCTD among the outputs
        assert page.input_value('#auCountry') == 'EG' and 'هيئة الدواء المصرية' in page.inner_text('#auName')
        assert 'eCTD 3.2.2' in page.inner_text('#auCard') and page.locator('[data-updoc="analysis_conformity"]').count() == 1
        first = page.eval_on_selector('#auCountry optgroup', 'g => [...g.querySelectorAll("option")].map(o => o.value)')
        assert first[0] == 'EG' and {'SA', 'AE', 'KW', 'DE', 'US'} <= set(first) and 'JO' not in first
        # Saudi Arabia: the Gulf Module 1, written from the SFDA and GCC texts
        page.select_option('#auCountry', 'SA')
        page.wait_for_function("() => document.querySelector('#auName').textContent.includes('SFDA')")
        card = page.inner_text('#auCard')
        assert 'موديول ١ من النص المنشور للهيئة' in card and 'SFDA' in card and 'v4.0' in card and 'مجلدات CTD' in card and 'eCTD 3.2.2' not in card
        assert page.locator('[data-updoc="analysis_conformity"]').count() == 0                  # the Egyptian laboratory's certificate is Egypt's card
        page.wait_for_function("() => document.querySelector('#pvAu') && document.querySelector('#pvAu').textContent.includes('SFDA')")
        page.click('#wizNext')
        assert 'السعودية' in page.inner_text('#auLine')
        page.fill('[data-in="name"]', 'Dermacure KSA'); page.fill('[data-in="trade"]', 'Dermacure'); page.fill('[data-in="man"]', 'Example Pharm Co.')
        page.click('#wizNext')
        body = page.inner_text('#wizBody')
        assert 'مصنّع في دولة التسجيل ولا مستورد ليها؟' in body and page.locator('[data-k="licence"]').count() == 0 and page.locator('[data-k="activity"]').count() == 0
        assert page.locator('[data-auq="gcc_agency"]').input_value() == 'SA'                    # the receiving authority follows the country
        page.click('[data-k="origin"][data-v="imported"]')
        page.click('#wizNext')
        page.fill('[data-api="0"][data-f="name"]', 'Neomycin sulphate'); page.fill('[data-api="0"][data-f="manufacturer"]', 'Example API Co.')
        page.select_option('[data-api="0"][data-f="option"]', 'DMF')
        page.click('#wizNext')
        page.fill('[data-in="applicant"]', 'Example Pharm Co.'); page.fill('[data-in="tracking"]', 'T-0001')
        page.wait_for_function("() => /1\\.7\\.5/.test(document.querySelector('#pvBody').textContent)")           # the alcohol declaration is in the list before anything is created
        assert 'M1-01' not in page.inner_text('#pvBody')
        page.click('#wizCreate')
        page.wait_for_selector('[data-tpl="GCC-1.7.5"]', timeout=20000)
        did = page.url.split('/d/')[1].split('/')[0]
        d = call(server, f'/api/dossiers/{did}')
        assert d['pack'] == 'gcc.ctd.m1.v1' and d['authority']['country'] == 'SA' and d['profile']['extra'] == {'gcc_agency': 'SA'}
        assert 'السعودية' in page.inner_text('#crumbAu') and page.locator('#navReview').is_hidden()
        assert page.locator('[data-draft="GCC-1.7.5"]').count() == 1 and page.locator('[data-draft="GCC-1.7.1"]').count() == 0     # a declaration is drafted, a certificate never
        # the item says where its level comes from when the source does not
        page.click('[data-why="GCC-1.4.2"]')
        page.wait_for_selector('[data-levelnote]')
        assert 'راجعه مع الهيئة' in page.inner_text('[data-levelnote]')
        page.click('#dClose')
        # the template of a Gulf declaration, built from what SFDA asks it to say
        page.click('[data-tpl="GCC-1.7.6"]')
        page.wait_for_selector('#tplPanel .docprev')
        assert 'pork' in page.inner_text('#tplPanel')
        page.click('#dClose')
        assert 'موديول ١ بتاع الهيئة' in page.inner_text('.head .sub')
        # the guide speaks of CTD folders, not of Egypt's eCTD
        page.goto(f'{server}/#/d/{did}/guide')
        page.wait_for_selector('.outcard')
        assert page.locator('.outcard').count() == 1 and 'eCTD 3.2.2' not in page.inner_text('#view')
        # publisher and export: CTD folders only
        page.goto(f'{server}/#/d/{did}/publisher')
        page.wait_for_selector('[data-out="ctd"]')
        assert page.locator('[data-out="ectd32"]').count() == 0
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#ctdOnly')
        assert page.locator('input[data-out]').count() == 2 and page.locator('input[data-out="ctd"]').count() == 1 and page.locator('input[data-out="nees"]').count() == 1
        page.screenshot(path=f'{OUT}/country-export.png')
        # the projects list names the country
        page.goto(f'{server}/#/dossiers')
        page.wait_for_selector('[data-au="GCC"]')
        b.close()
    assert not errors, errors


def test_each_authority_asks_its_own_questions_and_a_general_module_1_says_so(server):
    errors = []
    with pw.sync_playwright() as p:
        b, page = open_page(p, server, errors)
        page.goto(f'{server}/#/new')
        page.wait_for_selector('#auCountry')
        # Germany: the EU Module 1, by legal basis and procedure
        page.select_option('#auCountry', 'DE')
        page.wait_for_function("() => document.querySelector('#auName').textContent.includes('EMA')")
        page.click('#wizNext'); page.click('#wizNext')
        assert page.locator('[data-auq="eu_legal_basis"]').input_value() == 'generic' and page.locator('[data-auq="eu_procedure"]').input_value() == 'dcp'
        page.wait_for_function("() => /1\\.5\\.2/.test(document.querySelector('#pvBody').textContent)")
        assert '1.10' not in [x.strip() for x in page.locator('#pvBody .code').all_inner_texts()]
        page.select_option('[data-auq="eu_legal_basis"]', 'full')
        page.wait_for_function("() => [...document.querySelectorAll('#pvBody .code')].some(e => e.textContent.trim() === '1.10')")       # a full application: paediatrics
        assert '1.5.2' not in [x.strip() for x in page.locator('#pvBody .code').all_inner_texts()]
        assert page.locator('[data-auq="eu_legal_basis"]').input_value() == 'full'                # the answer stays after the page redraws
        # the United States: by type of application
        page.click('#auGo')
        page.select_option('#auCountry', 'US')
        page.wait_for_function("() => document.querySelector('#auName').textContent.includes('FDA')")
        page.click('#wizNext'); page.click('#wizNext')
        assert page.locator('[data-auq="us_application"]').input_value() == 'anda' and page.locator('[data-auq="eu_legal_basis"]').count() == 0
        page.wait_for_function("() => /356h/.test(document.querySelector('#pvBody').textContent)")
        # any other country: a general Module 1, said plainly
        page.click('#auGo')
        page.select_option('#auCountry', 'JO')
        page.wait_for_function("() => document.querySelector('#auCard').textContent.includes('موديول ١ عام')")
        assert 'لسه ما اتكتبش' in page.inner_text('#auCard')
        page.wait_for_function("() => document.querySelector('#pvAu') && document.querySelector('#pvAu').textContent.includes('موديول ١ عام')")
        page.screenshot(path=f'{OUT}/country-wizard.png')
        # back to Egypt: its own questions are back
        page.select_option('#auCountry', 'EG')
        page.wait_for_function("() => document.querySelector('#auName').textContent.includes('المصرية')")
        page.click('#wizNext'); page.click('#wizNext')
        assert page.locator('[data-k="licence"]').count() >= 4 and page.locator('[data-auq]').count() == 0
        page.wait_for_function("() => /1\\.1\\.1|Annex/.test(document.querySelector('#pvBody').textContent)")
        b.close()
    assert not errors, errors


def test_home_names_the_countries(server):
    errors = []
    with pw.sync_playwright() as p:
        b, page = open_page(p, server, errors)
        page.goto(f'{server}/#/')
        page.wait_for_selector('#homeAu')
        text = page.inner_text('#homeAu')
        assert 'SFDA' in text and 'FDA' in text and 'هيئة الدواء المصرية' in text and 'أي دولة تانية' in text
        b.close()
    assert not errors, errors
