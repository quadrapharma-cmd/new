"""Browser cases from the logic review (November 2026): what the user typed outlives a refresh and a new upload, a file the kind rule
refused is not lost when the dossier is created, and the page cleans the active substances exactly as the engine does."""
import socket, threading, time
import pytest
from fixtures_pdf import make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')


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


def docs(tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', ['Certificate of Pharmaceutical Product', 'Certificate No: CPP-2024-0117', 'Trade name: Cardiolol 10 mg',
                         'Dosage form: film-coated tablet', 'Active ingredient: Bisoprolol fumarate', 'Manufacturer: Medis S.A., Nabeul, Tunisia',
                         'Marketing authorisation holder: Medis S.A.', 'Date of issue: 12 March 2025', 'Valid until: 11 March 2027'], 'WHO Certification Scheme')
    gmp = make_pdf_lines(tmp_path / 'gmp certificate.pdf', ['GMP Certificate', 'Certificate Number: EG/GMP/2024/55', 'Manufacturer: Medis S.A.',
                         'Egyptian Drug Authority', 'Date of issue: 01/06/2024', 'Valid until: 31/05/2027'])
    pricing = make_pdf_lines(tmp_path / 'price letter.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Cardiolol 10 mg', 'Public price: 45.00 EGP', 'Pack: 30 tablets'], 'Pricing')
    return cpp, gmp, pricing


def start(server, browser, files):
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(server + '/#/new')
    page.wait_for_selector('#intakeBtn')
    with page.expect_file_chooser() as fc:
        page.click('#intakeBtn')
    fc.value.set_files([str(f) for f in files])
    page.wait_for_selector('#intakeReview', timeout=120000)
    return page


def trade_value(page):
    if not page.locator('[data-in=trade]').count():
        page.click('#wizNext')
    page.wait_for_selector('[data-in=trade]', timeout=20000)
    return page.input_value('[data-in=trade]')


def test_typed_value_survives_a_refresh_and_a_new_upload(server, browser, tmp_path):
    cpp, gmp, _ = docs(tmp_path)
    page = start(server, browser, [cpp])
    assert trade_value(page) == 'Cardiolol 10 mg'
    page.fill('[data-in=trade]', 'Cardiolol Forte 10 mg')
    page.dispatch_event('[data-in=trade]', 'change')
    page.wait_for_timeout(1500)
    page.wait_for_function("() => /\\d/.test((document.querySelector('#wizSaved') || {}).textContent || '')", timeout=20000)
    page.reload()
    page.wait_for_selector('#wizNext, #intakeReview', timeout=60000)
    page.wait_for_timeout(2500)                                           # let any re-reading after the restore finish
    assert trade_value(page) == 'Cardiolol Forte 10 mg', 'the refresh put the reading back over the typed value'
    # a new document after the correction must not undo it either
    if not page.locator('[data-updoc="gmp_certificate"]').count():
        for _ in range(4):
            if page.locator('[data-updoc="gmp_certificate"]').count():
                break
            if page.locator('#wizBack').count():
                page.click('#wizBack')
            else:
                break
    if page.locator('[data-updoc="gmp_certificate"]').count():
        with page.expect_file_chooser() as fc:
            page.click('[data-updoc="gmp_certificate"]')
        fc.value.set_files([str(gmp)])
        page.wait_for_function("() => document.querySelector('.doccards') && document.querySelector('.doccards').innerText.includes('gmp certificate.pdf')", timeout=60000)
        page.wait_for_timeout(2500)
        assert trade_value(page) == 'Cardiolol Forte 10 mg', 'a new upload put the reading back over the typed value'
    page.close()


def test_refused_file_is_not_lost_at_creation(server, browser, tmp_path):
    import httpx
    cpp, gmp, pricing = docs(tmp_path)
    page = start(server, browser, [cpp, gmp])
    with page.expect_file_chooser() as fc:
        page.click('[data-updoc="gmp_certificate"]')
    fc.value.set_files([str(pricing)])
    page.wait_for_selector('[data-mvdoc="price letter.pdf"]', timeout=120000)          # refused under the GMP card; left as it is
    page.click('#intakeReview')
    page.wait_for_selector('#intakeApply')
    page.fill('[data-rva="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.click('#intakeApply')
    page.wait_for_selector('#toast:not([hidden])')
    for _ in range(3):
        page.click('#wizNext')
        page.wait_for_timeout(300)
    page.click('#wizCreate')
    page.wait_for_selector('text=Requirements board', timeout=60000)
    did = page.url.split('/d/')[1].split('/')[0]
    where = {}
    for _ in range(60):
        b = httpx.get(f'{server}/api/dossiers/{did}/board').json()
        where = {d['filename']: s['slot_id'] for s in b['slots'] for d in s['documents']}
        where.update({d['filename']: 'unplaced' for d in b['unassigned']})
        if 'cpp.pdf' in where and 'price letter.pdf' in where:
            break
        time.sleep(1)
    assert where.get('cpp.pdf') == 'M1-14', where
    assert 'price letter.pdf' in where, f'the refused file vanished: {where}'
    assert where['price letter.pdf'] in ('M1-05', 'unplaced'), where              # in its own item or waiting in the box, never under GMP
    page.close()


NAMES = ['NEOMYCIN SULPHATE 3.500 mg (3300 unit)', 'Neomycin Sulphate', 'neomycin', 'Bacitracin Zinc 500 IU', 'Bactiracin Zinc', 'Each 1g contains', 'Quantity', 'Specification',
         'White homogenous powder', 'White opaque plastic', 'Topical powder', 'Powder for cutaneous use', 'in human milk', 'Not applicable', 'Posology',
         'Dermacure Powder should not be diluted', 'threonine. Glycine 10 mg', 'Iron (III) hydroxide polymaltose complex', 'Paracetamol (micronised) granules',
         'Amoxicillin (as trihydrate) 500 mg', 'Sodium chloride', 'Potassium chloride', 'Vitamin B1', 'Vitamin B12', 'Salicylic acid', 'Acetylsalicylic acid',
         'Metformin HCl', 'Metformin Hydrochloride', 'Egypt', 'Example Pharma S.A.E.', 'Diclofenac sodium', 'Zinc 10 mg', 'باراسيتامول', 'كل قرص يحتوي على', 'Manufacturer']


def test_the_page_cleans_active_substances_as_the_engine_does(server, browser):
    from dossier_engine import extract as X
    page = browser.new_page()
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.goto(server + '/#/')
    page.wait_for_selector('#btnNew')
    got = page.evaluate("names => cleanApis(names.map(n => ({name: n}))).map(a => [a.name, a.strength || null])", NAMES)
    want = [[a['name'], a.get('strength')] for a in X.clean_apis([{'name': n} for n in NAMES])]
    assert got == want
    assert [n for n, _ in want] == ['Neomycin Sulphate', 'Bacitracin Zinc', 'threonine', 'Glycine', 'Iron (III) hydroxide polymaltose complex', 'Paracetamol granules',
                                    'Amoxicillin', 'Sodium chloride', 'Potassium chloride', 'Vitamin B1', 'Vitamin B12', 'Salicylic acid', 'Acetylsalicylic acid',
                                    'Metformin Hydrochloride', 'Diclofenac sodium', 'Zinc', 'باراسيتامول']
    page.close()
