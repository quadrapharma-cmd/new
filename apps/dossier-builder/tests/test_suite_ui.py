"""Browser journey for the product file (suite module 1): create parties and a product, register a document,
see it on the dashboard as expired with the affected product, replace it, see the item turn valid."""
import os, socket, threading, time
from datetime import date, timedelta
import pytest
import uvicorn
from dossier_engine.app.api import create_app

pw = pytest.importorskip('playwright.sync_api')


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    port = free_port()
    app = create_app(tmp_path_factory.mktemp('ws'))
    srv = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning'))
    th = threading.Thread(target=srv.run, daemon=True); th.start()
    for _ in range(50):
        try:
            socket.create_connection(('127.0.0.1', port), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


@pytest.mark.parametrize('width', [1440, 390])
def test_product_file_journey(server, width, tmp_path):
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': width, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(server + '/suite/#/parties')
        sup = f'Supplier {width}'
        page.click('#npy'); page.fill('#pa-name', sup); page.select_option('#pa-kind', 'supplier'); page.click('#paSave')
        page.wait_for_selector(f'text={sup}')
        page.goto(server + '/suite/#/products'); page.click('#np')
        page.fill('#pf-name', f'Prod {width}'); page.fill('#pf-reg_date', '2022-11-10'); page.click('#pfSave')
        page.wait_for_selector('.ring')
        page.click('text=الأطراف >> nth=-1') if width < 800 else page.click('.tabs >> text=الأطراف')
        page.select_option('#lp-party', label=sup); page.select_option('#lp-role', 'api_supplier'); page.fill('#lp-api', 'Glycine')
        page.click('#lpGo'); page.wait_for_selector(f'td >> text={sup}')
        page.click('.tabs >> text=الملف المطلوب')
        page.locator('.need', has_text='GMP').locator('[data-reg]').click()
        page.fill('#df-valid', (date.today() - timedelta(days=2)).isoformat())
        page.fill('#df-url', 'https://drive.google.com/file/d/abc/view')
        page.click('#dfSave'); page.wait_for_timeout(500)
        assert page.locator('.need', has_text='GMP').locator('.chip.s-expired').count() == 1
        page.goto(server + '/suite/#/'); page.wait_for_selector('.issue')
        row = page.locator('.issue', has_text=sup).first
        assert row.locator('.chip.s-expired').count() == 1 and row.locator('.pchip', has_text=f'Prod {width}').count() == 1
        row.locator('[data-replace]').click()
        page.fill('#df-valid', (date.today() + timedelta(days=700)).isoformat())
        page.fill('#df-url', 'https://drive.google.com/file/d/new/view'); page.click('#dfSave'); page.wait_for_timeout(500)
        assert page.locator('.issue', has_text=sup).locator('.chip.s-expired').count() == 0
        assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
        page.click('#l-en'); page.wait_for_selector('text=Dashboard')
        assert errors == []
        b.close()


def test_a_product_and_a_document_are_deleted_from_the_page(server, tmp_path):
    """A product nobody wants any more is deleted for good with its name typed; a library document in two presses. What other
    products use stays."""
    import io, json
    import httpx
    H = {'X-DB': '1'}
    a = httpx.post(f'{server}/api/suite/products', json={'name': 'Dermacure A'}, headers=H).json()
    b_ = httpx.post(f'{server}/api/suite/products', json={'name': 'Dermacure B'}, headers=H).json()
    post = lambda meta: httpx.post(f'{server}/api/suite/documents', data={'meta': json.dumps(meta)}, files={'file': ('cert.pdf', io.BytesIO(b'%PDF-1.4 dermacure'), 'application/pdf')}, headers=H).json()
    own = post({'doc_type': 'pricing_certificate', 'title': 'Pricing of A', 'products': [a['id']]})
    both = post({'doc_type': 'registration_licence', 'title': 'Licence of A and B', 'products': [a['id'], b_['id']]})
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(f"{server}/suite/#/p/{a['id']}/data")
        page.wait_for_selector('#delP')
        page.click('#delP')
        page.wait_for_selector('#cfType')
        assert page.is_disabled('#cfOk') and 'Dermacure A' in page.inner_text('#dBody')
        page.fill('#cfType', 'Dermacure A'); page.click('#cfOk')
        page.wait_for_function("() => location.hash === '#/products'")
        assert httpx.get(f"{server}/api/suite/products/{a['id']}").status_code == 404
        left = {d['id'] for d in httpx.get(f'{server}/api/suite/documents').json()}
        assert own['id'] not in left and both['id'] in left                                 # only its own document went with it
        page.goto(f'{server}/suite/#/docs')
        page.wait_for_selector(f"[data-editdoc=\"{both['id']}\"]")
        page.click(f"[data-editdoc=\"{both['id']}\"]")
        page.wait_for_selector('#edDel')
        page.click('#edDel')                                                                # one press only asks
        assert 'Sure' in page.inner_text('#edDel') and both['id'] in {d['id'] for d in httpx.get(f'{server}/api/suite/documents').json()}
        page.click('#edDel')
        page.wait_for_function(f"() => !document.querySelector('[data-editdoc=\"{both['id']}\"]')")
        assert both['id'] not in {d['id'] for d in httpx.get(f'{server}/api/suite/documents').json()}
        assert httpx.get(f"{server}/api/suite/products/{b_['id']}").status_code == 200
        assert errors == []
        b.close()
