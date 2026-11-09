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
