"""Priority 2 in the browser (Playwright): the checks page's «Auto-fix» fixes (it only opened the drawer), an upload never opens the
drawer by itself, «Turn it into PDF» on a Word file, and the search page finds a batch number with its page."""
import io, json, socket, threading, time, urllib.request
import pytest

pw = pytest.importorskip('playwright.sync_api')
from fixtures_pdf import make_pdf_lines, make_pdf
from dossier_engine.generate.docx_kit import find_soffice

PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', pharmacopoeial=True,
               apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')


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


def upload(server, did, sid, name, data, ctype='application/pdf'):
    import httpx
    r = httpx.post(f'{server}/api/dossiers/{did}/slots/{sid}/documents', files={'file': (name, data, ctype)}, data={'meta': '{}'}, headers={'X-DB': '1'})
    assert r.status_code == 201, r.text
    return r.json()


def page_of(b, server, lang='en'):
    page = b.new_page(viewport={'width': 1440, 'height': 1000})
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    return page


def test_checks_autofix_fixes_and_search_finds_the_page(server, tmp_path):
    from pypdf import PdfWriter
    did = dossier(server)
    w = PdfWriter(clone_from=str(make_pdf(tmp_path / 'lay.pdf', 'Appendix 4'))); w.add_js('app.alert(1);')
    buf = io.BytesIO(); w.write(buf)
    upload(server, did, 'M1-11', 'layout.pdf', buf.getvalue())                                  # JavaScript: an auto-fix
    stab = make_pdf_lines(tmp_path / 'stab.pdf', ['Stability summary', 'Batch AYBGE211102 at 25 C / 60 % RH', 'Table 3: assay'], 'Stability')
    upload(server, did, 'P-16', 'stability.pdf', stab.read_bytes())
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/checks')
        page.wait_for_selector('[data-cfix]')
        page.click('[data-cfix]')
        page.wait_for_function("() => !document.querySelector('[data-cfix]')", timeout=60000)    # fixed: the row has nothing left to fix
        assert page.is_hidden('#drawer')                                                            # and no drawer was opened for it
        page.goto(f'{server}/#/d/{did}/search')
        page.fill('#srchQ', 'aybge211102')
        page.press('#srchQ', 'Enter')
        page.wait_for_selector('#srchOut mark')
        out = page.inner_text('#srchOut')
        assert 'stability.pdf' in out and 'page 1' in out and page.inner_text('#srchOut mark') == 'AYBGE211102'
        page.click('#srchOut [data-why]')
        page.wait_for_selector('#drawer:not([hidden]) #dBody')
        b.close()
    assert not errors, errors


def test_an_upload_does_not_open_the_drawer_and_word_turns_into_pdf(server, tmp_path):
    import docx
    did = dossier(server)
    d = docx.Document(); d.add_paragraph('Stability summary and conclusions'); d.add_paragraph('Dermacure, 3 batches')
    buf = io.BytesIO(); d.save(buf)
    word = tmp_path / 'stability.docx'; word.write_bytes(buf.getvalue())
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_function("() => typeof S !== 'undefined' && S.board && S.board.slots && S.board.slots.length > 0")
        page.click('[data-f=all]')
        with page.expect_file_chooser() as fc:
            page.locator('tr', has_text='3.2.P.8').locator('[data-up]').first.click()              # P-16 asks nothing first: the file chooser
        fc.value.set_files(str(word))
        page.wait_for_selector('#toast:not([hidden])')
        page.wait_for_function("() => S.board && S.board.slots.find(s => s.slot_id === 'P-16').documents.length === 1", timeout=30000)
        page.wait_for_timeout(400)
        assert page.is_hidden('#drawer')                                                            # the drawer opens when the person opens it
        page.evaluate("openWhy('P-16')")
        page.wait_for_selector('#dBody')
        if find_soffice():
            page.click('[data-topdf]')
            page.wait_for_function("() => S.board.slots.find(s => s.slot_id === 'P-16').documents[0].filename === 'stability.pdf'", timeout=120000)
        else:
            assert 'حفظ باسم' in page.inner_text('#dBody')
        b.close()
    assert not errors, errors


def test_draft_them_all_writes_every_draft_with_progress(server):
    did = dossier(server)
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_selector('#draftAllBtn')
        todo = page.evaluate("S.board.slots.filter(s => draftable(s) && !genFor(s) && s.status === 'not_started').length")
        assert todo >= 3
        page.click('#draftAllBtn')
        page.click('#cfOk')                                                                           # the question asked in the page
        page.wait_for_selector('#draftAllBox')
        page.wait_for_function("() => !document.querySelector('#draftAllBox') && S.board", timeout=300000)
        left = page.evaluate("S.board.slots.filter(s => draftable(s) && !genFor(s) && s.status === 'not_started').length")
        drafted = page.evaluate("S.board.slots.filter(s => s.documents.some(d => d.meta && d.meta.generated === 'draft')).length")
        assert left == 0 and drafted == todo and page.is_hidden('#drawer')
        assert page.locator('#draftAllBtn').count() == 0                                            # nothing left to draft: no button
        b.close()
    assert not errors, errors


def test_two_drive_folders_of_one_product_are_listed_each_under_its_name(server, tmp_path):
    import urllib.parse
    from dossier_engine import drive
    names = {'folderAAAAAAAAAAAAA': 'Module 1 docs', 'folderBBBBBBBBBBBBB': 'Module 3 docs'}
    kids = {'folderAAAAAAAAAAAAA': [{'id': 'a1', 'name': 'licence.pdf', 'mimeType': 'application/pdf', 'size': '50'},
                                    {'id': 'same', 'name': 'shared.pdf', 'mimeType': 'application/pdf', 'size': '50'}],
            'folderBBBBBBBBBBBBB': [{'id': 'b1', 'name': 'stability.pdf', 'mimeType': 'application/pdf', 'size': '50'},
                                    {'id': 'same', 'name': 'shared.pdf', 'mimeType': 'application/pdf', 'size': '50'}]}

    def http(method, url, headers, data):
        u = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(u.query)
        if u.path == '/drive/v3/files':
            fid = next(k for k in kids if k in q['q'][0])
            return 200, 'application/json', json.dumps({'files': kids[fid]}).encode()
        fid = u.path.rsplit('/', 1)[-1]
        if fid in names:
            return 200, 'application/json', json.dumps({'id': fid, 'name': names[fid], 'mimeType': drive.FOLDER}).encode()
        return 500, 'text/plain', b'unexpected'
    drive.HTTP = http
    try:
        with pw.sync_playwright() as p:
            b = p.chromium.launch()
            page = page_of(b, server)
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(server + '/#/new')
            page.wait_for_selector('#intakeDrive'); page.click('#intakeDrive'); page.wait_for_selector('#drvLink')
            page.click('#drvGear'); page.wait_for_selector('#drvKey'); page.fill('#drvKey', 'AIzaTESTKEY0000000000'); page.click('#drvSave')
            page.wait_for_selector('#drvKey', state='detached')
            page.fill('#drvLink', 'https://drive.google.com/drive/folders/folderAAAAAAAAAAAAA https://drive.google.com/drive/folders/folderBBBBBBBBBBBBB')
            page.click('#drvList')
            page.wait_for_selector('[data-drvsel]')
            rows = page.inner_text('#drvFiles')
            assert 'Module 1 docs' in rows and 'Module 3 docs' in rows and 'licence.pdf' in rows and 'stability.pdf' in rows
            assert rows.count('shared.pdf') == 1 and page.locator('[data-drvsel]').count() == 3        # a file in both folders: once
            assert not errors, errors
            b.close()
    finally:
        drive.HTTP = None


def test_split_a_combined_file_from_the_unplaced_box_and_join_pages(server, tmp_path):
    import base64
    from dossier_engine import pages
    lic = make_pdf_lines(tmp_path / 'a.pdf', ['Final Registration License', 'Trade Name: Dermacure', 'Egyptian Drug Authority'], 'Licence').read_bytes()
    price = make_pdf_lines(tmp_path / 'b.pdf', ['Pricing Certificate', 'Price: EGP 45.00'], 'Pricing').read_bytes()
    did = dossier(server)
    doc = upload(server, did, 'M1-05', 'licence and pricing.pdf', pages.merge([lic, price]))
    p1 = upload(server, did, 'P-16', 'scan-1.pdf', make_pdf_lines(tmp_path / 's1.pdf', ['Stability summary', 'one'], 'Stability').read_bytes())
    p2 = upload(server, did, 'P-16', 'scan-2.pdf', make_pdf_lines(tmp_path / 's2.pdf', ['Stability summary', 'two'], 'Stability').read_bytes())
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_function("() => typeof S !== 'undefined' && S.board && S.board.slots && S.board.slots.length > 0")
        page.evaluate("openWhy('M1-05')")
        page.click(f'[data-split="{doc["id"]}"]')
        page.wait_for_selector('[data-start="2"]')
        assert page.is_checked('[data-start="2"]') and 'مستند 2' not in page.inner_text('#splitSum') and '2' in page.inner_text('#splitSum')
        page.click('#splitGo')
        page.wait_for_selector('#unplacedBox')
        box = page.inner_text('#unplacedBox')
        assert 'licence and pricing (p1).pdf' in box and 'licence and pricing (p2).pdf' in box
        page.evaluate("openWhy('P-16')")
        page.click('#mergeBtn')
        page.click('#cfOk')
        page.wait_for_function("() => S.board && S.board.slots.find(s => s.slot_id === 'P-16').documents.length === 1", timeout=30000)
        assert not errors, errors
        b.close()


def test_the_checks_page_lists_the_rules_with_their_status_and_source(server):
    did = dossier(server)
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/checks')
        page.wait_for_selector('#rulesBtn')
        page.click('#rulesBtn')
        page.wait_for_selector('#dBody details')
        page.locator('#dBody details summary').first.click()
        body = page.inner_text('#dBody')
        assert 'NTA065-N4' in body and 'ساري' in body and 'مسودة' in body and 'NP.CAPP.065 v5' in body
        assert 'النصوص الرسمية (SHA-256)' in body
        b.close()
    assert not errors, errors


def test_the_package_page_checks_an_ectd_zip_made_anywhere(server, tmp_path):
    import zipfile
    from dossier_engine.writers import ectd32_eu as eu
    from test_ectd32_eu import envelope, PROD, NODES
    from dossier_engine.writers.ectd32 import Doc
    src = tmp_path / 'src'; src.mkdir()
    ds = [Doc(node=n, file=str(make_pdf(src / f'd{i}.pdf', f'{n} {t}')), title=t, doc_id=f'doc{i}', **kw) for i, (n, t, kw) in enumerate(NODES)]
    e = envelope()
    eu.write(tmp_path / 'out', e, PROD, eu.resolve(ds, e))
    z = tmp_path / 'pkg.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        for p in (tmp_path / 'out').rglob('*'):
            if p.is_file():
                zf.write(p, p.relative_to(tmp_path / 'out').as_posix())
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/package')
        page.wait_for_selector('#pkgFile')
        page.set_input_files('#pkgFile', str(z))
        page.click('#pkgGo')
        page.wait_for_selector('#pkgOut table')
        out = page.inner_text('#pkgOut')
        assert '0000' in out and 'أوروبا' in out and '108/111' in out
        page.set_input_files('#pkgA', str(z)); page.set_input_files('#pkgB', str(z))
        page.click('#cmpGo')
        page.wait_for_selector('#cmpOut .alert')
        assert 'زي بعض' in page.inner_text('#cmpOut')
        b.close()
    assert not errors, errors
