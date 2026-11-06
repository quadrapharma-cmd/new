"""UI journey in a real browser (Playwright): wizard -> board -> upload -> why -> export gate, AR + EN, desktop + phone."""
import socket, threading, time
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    cfg = uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error')
    srv = uvicorn.Server(cfg)
    th = threading.Thread(target=srv.run, daemon=True); th.start()
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


def test_journey(server, browser, tmp_path):
    pdf = make_pdf(tmp_path / 'composition.pdf', 'Composition certificate')
    old = tmp_path / 'gmp-old.pdf'
    old.write_bytes(pdf.read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1))
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.goto(server + '/#/')
    assert page.locator('html').get_attribute('dir') == 'rtl'          # Arabic first
    page.click('#lang-en')
    page.click('#btnNew')
    page.fill('[data-in=name]', 'Examplol 500 mg FCT')
    page.fill('[data-in=trade]', 'Examplol 500 mg')
    page.fill('[data-in=man]', 'Example Pharma')
    page.click('#wizNext')
    page.click('[data-k=licence][data-v=toll]')
    page.check('[data-spec=coated]')
    page.click('#wizNext')
    page.fill('[data-api="0"][data-f=name]', 'Paracetamol')
    page.fill('[data-api="0"][data-f=manufacturer]', 'Granules India')
    page.click('#wizNext')
    page.fill('[data-in=applicant]', 'Example Pharma S.A.E.')
    page.fill('[data-in=tracking]', 'P-MAA-0001')
    page.click('#wizCreate')
    page.wait_for_selector('text=Requirements board')
    assert page.locator('tbody tr', has_text='Toll manufacturer licence').count() == 1   # toll -> required
    # upload a conforming document
    with page.expect_file_chooser() as fc:
        page.locator('tr', has_text='Composition certificate').locator('[data-up]').first.click()
    fc.value.set_files(str(pdf))
    page.wait_for_selector('#toast:not([hidden])')
    page.wait_for_function("!document.querySelector('tbody').innerText.includes('Composition certificate')")  # left the to-do list
    page.click('[data-f=all]')
    page.wait_for_selector('tr:has-text("Composition certificate") .chip.c-ok', state='attached')
    page.click('[data-f=todo]')
    # upload a PDF 1.3 GMP certificate -> non-conforming, drawer explains + locked note
    with page.expect_file_chooser() as fc:
        page.locator('tr', has_text='GMP certificate(s) of FPP').locator('[data-up]').first.click()
    fc.value.set_files(str(old))
    page.wait_for_selector('#drawer:not([hidden])')
    body = page.inner_text('#dBody')
    assert 'PDF version 1.3' in body and 'fix this automatically' in body and 'read-only' in body   # version normalise = technical op, allowed
    page.keyboard.press('Escape')
    # export gate blocked
    page.click('#navExport')
    page.wait_for_selector('text=Export is blocked')
    assert page.locator('#go').is_disabled()
    # Arabic + phone width: no horizontal overflow
    page.click('#lang-ar')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(page.url.replace('/export', '/board'))
    page.wait_for_selector('text=لوحة المتطلبات')
    sw = page.evaluate('document.documentElement.scrollWidth')
    assert sw <= 390, sw
    page.screenshot(path=str(tmp_path / 'ar-390.png'))
    assert errors == []
