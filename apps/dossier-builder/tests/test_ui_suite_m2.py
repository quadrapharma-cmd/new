"""The suite's module 2 in the browser (Playwright): a letter from the authority is added with its PDF, its numbered questions and the
time it gives appear as questions with a due date; answering them closes it and offers the reply letter; a commitment; the dashboard
lists the deadlines, the overdue first."""
import json, socket, threading, time
from datetime import date, timedelta
import pytest
from fixtures_pdf import make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')


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


@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_letters_questions_commitments_and_deadlines(server, tmp_path, lang):
    import httpx
    pid = httpx.post(f'{server}/api/suite/products', json={'name': 'Dermacure'}, headers={'X-DB': '1'}).json()['id']
    pdf = make_pdf_lines(tmp_path / 'eda.pdf', ['Egyptian Drug Authority', 'Subject: Comments on Dermacure', 'Please reply within 30 days:',
                                                '1- Submit the updated stability data for 3 batches', '2- Clarify the source of Glycine.'], 'EDA')
    late = (date.today() - timedelta(days=2)).isoformat()
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 390, 'height': 900} if lang == 'ar' else {'width': 1440, 'height': 1000})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
        page.goto(f'{server}/suite/#/letters')
        page.wait_for_selector('#newLetter')
        page.click('#newLetter')
        page.select_option('#lfProd', pid)
        page.set_input_files('#lfFile', str(pdf))
        page.click('#lfGo')
        page.wait_for_selector('[data-q]')
        assert page.locator('[data-q]').count() == 2 and 'Comments on Dermacure' in page.inner_text('h1')
        assert page.input_value('[data-qdue]') != ''                                              # the due date read from «within 30 days»
        for qa, text in zip(page.locator('[data-qa]').all(), ['Attached in 3.2.P.8.', 'Tianjin Tianyao, GMP attached.']):
            qa.fill(text)
        for k in range(2):
            page.locator('[data-qdone]:not([disabled])').first.click()
            page.wait_for_function(f"document.querySelectorAll('[data-qdone][disabled]').length === {k + 1}")
        href = page.get_attribute('#replyDoc', 'href')
        assert href and '/reply.docx' in href and httpx.get(server + href).content[:2] == b'PK'
        page.goto(f'{server}/suite/#/commitments')
        page.wait_for_selector('#cForm')
        before = page.locator('[data-cdone]').count()
        page.fill('#cText', 'Submit 12-month stability data of the first 3 batches')
        page.fill('#cDue', late)
        page.click('#cForm button[type=submit]')
        page.wait_for_function(f"document.querySelectorAll('[data-cdone]').length === {before + 1}")
        page.goto(f'{server}/suite/#/')
        page.wait_for_selector('#deadlines')
        dl = page.inner_text('#deadlines')
        assert '12-month stability' in dl and ('متأخر' in dl if lang == 'ar' else 'overdue' in dl)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
        b.close()
    assert not errors, errors
