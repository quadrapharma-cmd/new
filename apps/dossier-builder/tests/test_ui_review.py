"""Regulatory Reviewer in a real browser: run → desk → workspace (evidence, override) → screening gate → letter (generate + download link)
→ responses (respond) → verdict (sign) → settings (strictness, run again); Arabic RTL, no page errors, no horizontal overflow at 390px."""
import io, json, socket, threading, time
import pytest
from fixtures_pdf import make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')
requests = pytest.importorskip('requests')
PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', pharmacopoeial=True, dosage_specifics=['coated'],
               apis=[dict(name='Paracetamol', manufacturer='Granules India', option='CEP')])
DATA = {'apis': [dict(name='Paracetamol', manufacturer='Granules India', option='CEP', spec_standard='Ph. Eur. 11.5', cep_no='R1-CEP 2019-123', cep_status='valid', address_gmp='Plot 1, Hyderabad')],
        'batches': [dict(no='EX-23-001', kind='fpp', size='120000', scale='pilot', date='2025-02-10', site='Cairo'), dict(no='PA-001', kind='api', api='Paracetamol', size='50 kg'), dict(no='PA-002', kind='api', api='Paracetamol', size='50 kg')],
        'specs': {'product': [dict(test='Description', limit='white tablets'), dict(test='Identification', limit='IR + HPLC'), dict(test='Assay', limit='95.0–105.0%'), dict(test='Related substances', limit='NMT 0.2%'), dict(test='Dissolution', limit='NLT 80% (Q) in 30 min')]},
        'results': {'EX-23-001': {'Description': 'white tablets', 'Identification': 'complies', 'Assay': '99.1', 'Related substances': '0.05', 'Dissolution': '94'}},
        'composition': [dict(name='Paracetamol', standard='Ph. Eur.', function='active', grade='powder'), dict(name='Opadry II white', standard='in-house', function='', grade='85F18422')]}
H = {'X-DB': '1'}


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


@pytest.fixture(scope='module')
def dossier(server, tmp_path_factory):
    tmp = tmp_path_factory.mktemp('docs')
    did = requests.post(server + '/api/dossiers', headers=H, json=dict(name='Examplol 500 mg FCT', profile=PROFILE,
                        product=dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharma', indication='pain-and-fever'),
                        envelope=dict(tracking='P-MAA-0001', applicant='Example Pharma S.A.E.', invented_name='Examplol 500 mg', inn=['paracetamol'], description='Initial MAA', portal_id='EXAMPLE-0001'))).json()['id']
    for slot, name, lines, title in [('M1-43', 'cover.pdf', ['Cover letter', 'We confirm that the submitted data are true, complete and correct.'], 'Cover letter'),
                                     ('P-12', 'imp.pdf', ['Impurities', 'Elemental impurities risk assessment per ICH Q3D. Mutagenic impurities per ICH M7. Nitrosamine risk assessed.'], '3.2.P.5.5'),
                                     ('P-07', 'pv.pdf', ['Process validation', 'Summary of results for one batch only.'], '3.2.P.3.5')]:
        pdf = make_pdf_lines(tmp / name, lines, title)
        r = requests.post(f'{server}/api/dossiers/{did}/slots/{slot}/documents', headers=H, files={'file': (name, pdf.read_bytes(), 'application/pdf')}, data={'meta': '{}'})
        assert r.status_code == 201, r.text
    assert requests.put(f'{server}/api/dossiers/{did}/data', headers=H, json=DATA).status_code == 200
    return did


def test_review_journey(server, browser, dossier):
    did = dossier
    page = browser.new_page(viewport={'width': 1280, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','ar')")
    page.goto(f'{server}/#/d/{did}/review')
    page.wait_for_selector('#runBtn')
    assert page.locator('html').get_attribute('dir') == 'rtl'
    page.click('#runBtn')
    page.wait_for_selector('.vstrip', state='attached', timeout=90000)
    assert 'غير جاهز' in page.inner_text('.vstrip')                       # 26 required Module 1 items are missing → will not pass screening
    assert page.locator('.dept').count() >= 8
    # workspace: evidence viewer + manual override with a reason
    page.click('[data-rdept="quality"]')
    page.wait_for_selector('.qcard', state='attached')
    page.click('.qcard .evi')
    assert page.locator('#rviewer .page, #rviewer .code').count() >= 1
    page.click('[data-rf="open"]')
    page.wait_for_selector('.qcard', state='attached')
    page.click('.qcard [data-rovr]')
    page.wait_for_selector('#ovSave')
    page.click('#ovSave')                                                   # no reason → stays open
    assert page.locator('#ovSave').count() == 1
    page.fill('#ovR', 'evidence in annex')
    page.click('#ovSave')
    page.wait_for_selector('#toast:not([hidden])')
    page.wait_for_selector('.qcard .otag.human', state='attached')
    # screening gate + rejection preview
    page.goto(f'{server}/#/d/{did}/review/screening')
    page.wait_for_selector('.gate.bad')
    page.click('#rejPrev')
    page.wait_for_selector('#drawer:not([hidden]) .letter')
    assert 'In-completed' in page.inner_text('#drawer')
    page.keyboard.press('Escape')
    # letter: generated on the server, download links appear
    page.goto(f'{server}/#/d/{did}/review/letter')
    page.wait_for_selector('.letter')
    assert 'SIMULATION' in page.inner_text('.letter')
    page.click('[data-rgen="letters"]')
    page.wait_for_selector('a[href*="/letters/"][href*="fmt=docx"]', timeout=90000)
    # responses: respond then re-assess (nothing changed → not accepted)
    page.goto(f'{server}/#/d/{did}/review/responses')
    page.wait_for_selector('.rtable')
    page.click('[data-rresp]')
    page.wait_for_selector('#rsSave')
    page.fill('#rsT', 'Second batch will be added.')
    page.click('#rsSave')
    page.wait_for_selector('#toast:not([hidden])')
    page.wait_for_selector('.rtable .chip.c-info', state='attached')
    page.click('[data-rre]')
    page.wait_for_selector('.rtable .chip.c-bad', state='attached')
    # verdict: assessor sign-off
    page.goto(f'{server}/#/d/{did}/review/verdict')
    page.wait_for_selector('.tl')
    page.fill('#signName', 'Mona')
    page.click('[data-rsign="assessor"]')
    page.wait_for_selector('#toast:not([hidden])')
    page.wait_for_selector('[data-rsign="assessor"]:has-text("Mona")')
    # settings: EDA-only strictness and a second run
    page.goto(f'{server}/#/d/{did}/review/settings')
    page.wait_for_selector('#rtrack')
    page.click('[data-rstrict="eda"]')
    page.wait_for_selector('[data-rstrict="eda"].on')
    page.click('#runBtn')
    page.wait_for_function("document.querySelector('#toast') && document.querySelector('#toast').textContent.includes('R-')", timeout=90000)
    runs = requests.get(f'{server}/api/dossiers/{did}/review', headers=H).json()['runs']
    assert len(runs) == 2 and runs[0]['options']['strictness'] == 'eda'
    assert not errors, errors
    # phone width: no horizontal overflow
    phone = browser.new_page(viewport={'width': 390, 'height': 844})
    phone.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    phone.add_init_script("localStorage.setItem('db.lang','ar')")
    for h in ('review', 'review/assess', 'review/letter'):
        phone.goto(f'{server}/#/d/{did}/{h}')
        phone.wait_for_selector('.vstrip, .ws, .letter', state='attached')
        phone.wait_for_timeout(300)
        assert phone.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') == 0, h
    phone.close()
    page.close()
