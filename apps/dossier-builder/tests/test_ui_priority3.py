"""The page for the updates list's Priority 3 items that have their own controls: the backups card with its restore drill (28), the
documents sheet with its plan before anything is done (47) and the import of earlier eCTD sequences (24)."""
import csv, io, json, socket, threading, time, urllib.request
import pytest

pw = pytest.importorskip('playwright.sync_api')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import PROFILE, PRODUCT, upload, page_of


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


def dossier(server):
    req = urllib.request.Request(server + '/api/dossiers', data=json.dumps(dict(name='Dermacure', profile=PROFILE, product=PRODUCT,
                                 envelope=dict(tracking='P-0001', applicant='Example Holder S.A.E.', invented_name='Dermacure'))).encode(),
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=30).read())['id']


def test_backup_now_and_its_restore_drill(server, tmp_path):
    did = dossier(server)
    upload(server, did, 'P-16', 'stability.pdf', make_pdf_lines(tmp_path / 's.pdf', ['Stability summary', 'three batches'], 'S').read_bytes())
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/users')
        page.wait_for_selector('#bkCard #bkList')
        page.wait_for_function("() => !document.querySelector('#bkList').textContent.includes('…')")
        page.click('#bkMake')
        page.wait_for_selector('#bkTable [data-drill]')
        assert page.locator('#bkTable a[download]').first.get_attribute('href').startswith('/api/backups/backup-')
        page.click('#bkTable [data-drill]')
        page.wait_for_selector('#bkOut .alert.ok')
        assert 'سليمة' in page.inner_text('#bkOut')
        b.close()
    assert not errors, errors


def test_the_sheet_shows_its_plan_then_applies_it(server, tmp_path):
    did = dossier(server)
    upload(server, did, 'P-16', 'stability.pdf', make_pdf_lines(tmp_path / 's.pdf', ['Stability summary', 'three batches'], 'S').read_bytes())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows([['file', 'item', 'title'], ['stability.pdf', 'P-16', 'Stability — three batches'], ['nothing.pdf', 'P-16', '']])
    sheet = tmp_path / 'docs.csv'
    sheet.write_text(buf.getvalue(), encoding='utf-8')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/board')
        page.click('#sheetBtn')
        page.wait_for_selector('#drawer:not([hidden]) #shFile')
        assert page.locator('#drawer a[download]').get_attribute('href').endswith('/metadata-sheet.csv')
        page.set_input_files('#shFile', str(sheet))
        page.wait_for_selector('#shTable tbody tr')
        assert [page.locator('#shTable tbody tr').nth(i).get_attribute('data-act') for i in range(2)] == ['update', 'error']
        page.click('#shApply')
        page.wait_for_selector('#drawer', state='hidden')
        b.close()
    with urllib.request.urlopen(f'{server}/api/dossiers/{did}/board', timeout=30) as r:
        slot = next(s for s in json.loads(r.read())['slots'] if s['slot_id'] == 'P-16')
    assert slot['documents'][0]['title'] == 'Stability — three batches'
    assert not errors, errors


def test_import_says_what_is_wrong_with_a_file_that_holds_no_sequence(server, tmp_path):
    did = dossier(server)
    import zipfile
    z = tmp_path / 'not-ectd.zip'
    with zipfile.ZipFile(z, 'w') as f:
        f.writestr('readme.txt', 'no sequence here')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#importSeq')
        with page.expect_file_chooser() as fc:
            page.click('#importSeq')
        fc.value.set_files(str(z))
        page.wait_for_function("() => document.body.innerText.includes('No eCTD sequence')")
        b.close()
    assert not errors, errors
