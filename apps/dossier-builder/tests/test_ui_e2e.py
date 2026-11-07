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


def test_publisher_view(server, browser, tmp_path):
    import httpx, json
    pdf = make_pdf(tmp_path / 'c.pdf', 'Composition').read_bytes()
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Pub test', profile=prof, product=dict(
        name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma'), envelope={})).json()['id']
    httpx.post(f'{server}/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('comp.pdf', pdf, 'application/pdf')},
               data={'meta': '{}'})
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/publisher')
    page.wait_for_selector('[data-node="M1-31"]')
    page.click('[data-node="M1-31"]')
    page.wait_for_selector('.props')
    assert 'm1-2-8-1-compositcert' in page.inner_text('.props')
    assert 'm1/eg/12-form/128-composit/1281-compositcert/compositcert.pdf' in page.inner_text('.props')
    page.click('[data-out=ectd40]')
    page.wait_for_selector('.props:has-text("eg_1.2.8.1")')
    assert 'm1/compositcert.pdf' in page.inner_text('.props')
    page.click('[data-out=ctd]')
    page.wait_for_selector('.props:has-text("Module 1")')
    # drag-and-drop a file onto a section (DataTransfer built in the page)
    page.evaluate("""async (b64) => {
        const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const dt = new DataTransfer(); dt.items.add(new File([bin], 'loa.pdf', {type: 'application/pdf'}));
        const n = document.querySelector('[data-node="M1-02"]');
        n.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
    }""", __import__('base64').b64encode(pdf).decode())
    page.wait_for_selector('[data-node="M1-02"].sel')
    page.wait_for_selector('#leafPane tr.leaf')
    assert page.locator('[data-node="M1-02"] .dot.d-conforming').count() == 1


def test_generate_from_ui(server, browser):
    import httpx
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new', dosage_specifics=['coated'],
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Gen test', profile=prof, product=dict(
        name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma'),
        envelope=dict(applicant='Example Pharma S.A.E.', tracking='P-MAA-0001', invented_name='Examplol 500 mg'))).json()['id']
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('tbody tr')
    page.locator('tr', has_text='Composition certificate').locator('[data-why]').click()
    page.click('[data-gen=composition]')
    page.wait_for_selector('.gform')
    assert page.input_value('[data-p=trade_name]') == 'Examplol 500 mg'          # prefilled
    page.click('#genGo')                                                       # missing -> highlighted
    page.wait_for_selector('.gform .miss')
    page.fill('[data-p="components.0.name"]', 'Paracetamol')
    page.fill('[data-p="components.0.function"]', 'API')
    page.fill('[data-p="components.0.qty_mg"]', '500')
    page.fill('[data-p="components.0.standard"]', 'Ph. Eur.')
    page.click('[data-add=components]')
    page.fill('[data-p="components.1.name"]', 'Opadry II')
    page.fill('[data-p="components.1.function"]', 'Film coat')
    page.fill('[data-p="components.1.qty_mg"]', '15')
    page.fill('[data-p="components.1.standard"]', 'In-house')
    page.select_option('[data-p="components.1.part"]', 'coat')
    page.fill('[data-p=signatory]', 'A. Example')
    page.fill('[data-p=signatory_title]', 'Managing Director')
    page.click('#genGo')
    page.wait_for_selector('#toast:has-text("Generated")', timeout=60000)
    page.click('[data-f=all]')
    row = page.locator('tr', has_text='Composition certificate')
    assert 'composition.pdf' in row.inner_text()


def test_bulk_classify(server, browser, tmp_path):
    import httpx
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Bulk test', profile=prof, product=dict(
        name='Examplol 500 mg', dosageform='tablet', manufacturer='Example Pharma'), envelope={})).json()['id']
    files = [make_pdf(tmp_path / n, n) for n in ('GMP certificate Example Pharma.pdf', 'Pricing certificate.pdf', 'IMG_2041.pdf')]
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('#bulkBtn')
    with page.expect_file_chooser() as fc:
        page.click('#bulkBtn')
    fc.value.set_files([str(f) for f in files])
    page.wait_for_selector('[data-bulk]')
    vals = page.eval_on_selector_all('[data-bulk]', 'els => els.map(e => e.value)')
    assert vals == ['M1-37', 'M1-05', '']                     # unknown file: no guess
    page.click('#bulkGo')
    page.wait_for_selector('#toast:has-text("2 files added")')
    board = httpx.get(f'{server}/api/dossiers/{did}/board').json()
    st = {s['slot_id']: s['status'] for s in board['slots']}
    assert st['M1-37'] == 'conforming' and st['M1-05'] == 'conforming'


def test_product_data_page(server, browser):
    import httpx
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Data test', profile=prof, product=dict(
        name='Examplol 500 mg', dosageform='tablet', manufacturer='Example Pharma'), envelope={'applicant': 'Example Pharma'})).json()['id']
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/data')
    page.wait_for_selector('#dSave')
    assert page.input_value('[data-d="apis.0.manufacturer"]') == 'Granules India'      # prefilled from the profile
    page.click('[data-dadd=batches]')
    page.fill('[data-d="batches.0.no"]', 'EX0001')
    page.click('[data-dadd="specs.product"]')
    page.fill('[data-d="specs.product.0.test"]', 'Assay')
    page.fill('[data-d="specs.product.0.limit"]', '95.0–105.0 %')
    page.click('#dSave')
    page.wait_for_selector('#crossBox .finding')
    txt = page.inner_text('#crossBox')
    assert 'NP040-P54' in txt and 'NP040-S44' in txt                    # 1 FPP batch, 0 API batches
    page.fill('[data-r="EX0001"][data-t2="Assay"]', 'Conforms')
    page.click('#dSave')
    page.wait_for_selector('#crossBox:has-text("NP040-NUM")')


def test_variations_page(server, browser):
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/variations')
    page.wait_for_selector('[data-v]')
    page.fill('#vq', 'new manufacturer for Active Substance')
    page.wait_for_function("document.querySelectorAll('[data-v]').length <= 3")
    page.check('[data-v="H-05"]')
    page.wait_for_selector('.kpi:has-text("PAC-II")')
    assert 'var-pac-ii' in page.inner_text('#view')


def test_rebuild_loop_ui(server, browser, tmp_path):
    import httpx
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Loop test', profile=prof, product=dict(
        name='Examplol 500 mg', dosageform='tablet', manufacturer='Example Pharma'),
        envelope={'applicant': 'Example Pharma S.A.E.', 'tracking': 'P-MAA-0001', 'invented_name': 'Examplol'})).json()['id']
    bad = make_pdf(tmp_path / 'gmp.pdf', 'GMP').read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1)
    httpx.post(f'{server}/api/dossiers/{did}/slots/M1-37/documents', files={'file': ('gmp.pdf', bad, 'application/pdf')}, data={'meta': '{}'})
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('tbody tr')
    page.locator('tr', has_text='GMP certificate(s) of FPP').locator('[data-why]').click()
    page.click('[data-fix]')
    page.wait_for_function("document.querySelector('#dBody').innerText.includes('v 2')", timeout=60000)
    assert 'Non-conforming' not in page.inner_text('#dBody')
    page.keyboard.press('Escape')
    # request from issuer for a missing third-party document
    page.click('[data-f=all]')
    page.locator('tr', has_text='Register of trade').locator('[data-why]').click()
    page.click('[data-req]')
    page.fill('#rqIssuer', 'Commercial Registry Office')
    page.fill('#rqSig', 'A. Example')
    page.fill('#rqSigT', 'Regulatory Affairs Manager')
    with page.context.expect_page() as newp:
        page.click('#rqGo')
    newp.value.close()
    page.wait_for_selector('tr:has-text("Register of trade") .chip.c-wait')


def test_upload_asks_replace(server, browser, tmp_path):
    import httpx
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
    did = httpx.post(server + '/api/dossiers', json=dict(name='Replace test', profile=prof, product=dict(
        name='Examplol', dosageform='tablet', manufacturer='Example Pharma'), envelope={})).json()['id']
    pdf = make_pdf(tmp_path / 'c.pdf', 'Composition')
    httpx.post(f'{server}/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('c1.pdf', pdf.read_bytes(), 'application/pdf')}, data={'meta': '{}'})
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('tbody tr')
    page.click('[data-f=all]')
    page.locator('tr', has_text='Composition certificate').locator('[data-up]').click()
    page.wait_for_selector('[data-rp]')
    with page.expect_file_chooser() as fc:
        page.click('[data-rp]')
    fc.value.set_files(str(pdf))
    page.wait_for_selector('#toast:not([hidden])')
    page.wait_for_timeout(500)
    s = next(x for x in httpx.get(f'{server}/api/dossiers/{did}/board').json()['slots'] if x['slot_id'] == 'M1-31')
    assert [d['version'] for d in s['documents']] == [2]                    # v1 superseded, not duplicated
