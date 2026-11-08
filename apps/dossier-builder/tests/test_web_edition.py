"""The browser edition (web/dist): the same engine runs inside Chromium through Pyodide, with no server.
Needs `python3 web/build.py` first (vendor.sh fetches the runtime once); skipped when dist is absent."""
import functools, http.server, pathlib, socket, threading
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')
DIST = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'dist'
pytestmark = pytest.mark.skipif(not (DIST / 'index.local.html').exists(), reason='web/dist not built')


@pytest.fixture(scope='module')
def site():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{port}'
    srv.shutdown()


def test_in_browser_journey(site, tmp_path):
    pdf = make_pdf(tmp_path / 'composition.pdf', 'Composition certificate')
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True)
        page = ctx.new_page()
        errors, console = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(site + '/index.local.html#/')
        page.wait_for_selector('#boot', state='detached', timeout=180000)            # engine booted inside the browser
        try:
            page.wait_for_selector('.caps .cap', timeout=120000)
        except Exception:
            raise AssertionError('home did not render; view=' + page.inner_text('#view')[:800] + ' console=' + ' | '.join(console)[:800] + ' errors=' + ' | '.join(errors)[:400])
        assert '101' in page.inner_text('.caps')                                      # capabilities read from the in-browser engine
        page.click('#btnNew')
        page.fill('[data-in=name]', 'Examplol 500 mg FCT')
        page.fill('[data-in=man]', 'Example Pharma')
        page.click('#wizNext'); page.click('[data-k=licence][data-v=toll]')
        page.wait_for_function("(n=>n && +n.innerText > 50)(document.querySelector('#pvBody .n'))", timeout=60000)
        page.click('#wizNext')
        page.fill('[data-api="0"][data-f=name]', 'Paracetamol'); page.fill('[data-api="0"][data-f=manufacturer]', 'Granules India')
        page.click('#wizNext')
        page.fill('[data-in=applicant]', 'Example Pharma S.A.E.'); page.fill('[data-in=tracking]', 'P-MAA-0001')
        page.click('#wizCreate')
        page.wait_for_selector('text=Requirements board', timeout=60000)
        with page.expect_file_chooser() as fc:
            page.locator('tr', has_text='Composition certificate').locator('[data-up]').first.click()
        fc.value.set_files(str(pdf))
        page.wait_for_selector('#toast:not([hidden])', timeout=60000)
        page.click('[data-f=all]')
        page.wait_for_selector('tr:has-text("Composition certificate") .chip.c-ok', state='attached', timeout=60000)
        # a document download goes through the browser (outside claude.ai) — the blob is the stored PDF
        page.locator('tr', has_text='Composition certificate').locator('[data-why]').first.click()
        with page.expect_download(timeout=60000) as dl:
            page.click('#dBody a[href*="/file"]')
        assert dl.value.suggested_filename == 'composition.pdf'
        page.keyboard.press('Escape')
        # the guide computes the next step from the in-browser engine
        page.click('#navGuide')
        page.wait_for_selector('.journey', timeout=60000)
        assert page.locator('.jbar a').count() == 6
        # the workspace persists in this browser: reload (still on the guide), the dossier is still there
        page.reload()
        page.wait_for_selector('#boot', state='detached', timeout=180000)
        page.wait_for_selector('.journey', timeout=120000)
        assert 'Examplol 500 mg FCT' in page.inner_text('#view') and page.locator('.jbar a').count() == 6
        assert errors == [], errors
        b.close()
