"""In the browser (Playwright): the export page offers a working copy while the gate is closed and hands over its zip; the wizard
has a card for methods of analysis and their validation, and one for fees receipts."""
import io, json, socket, threading, time, urllib.request, zipfile
import pytest
from fixtures_pdf import make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')
PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='FULL')])
PRODUCT = dict(name='Dermacure', dosageform='Cutaneous powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin'])


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


def call(url, path, body):
    req = urllib.request.Request(url + path, method='POST', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-DB': '1'})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def test_a_working_copy_from_the_export_page(server, tmp_path):
    did = call(server, '/api/dossiers', dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV))['id']
    pdf = make_pdf_lines(tmp_path / 'g.pdf', ['CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER', 'Example Pharm Co.']).read_bytes()
    boundary = '----x'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="gmp.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode() + pdf + \
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="meta"\r\n\r\n{{}}\r\n--{boundary}--\r\n'.encode()
    urllib.request.urlopen(urllib.request.Request(f'{server}/api/dossiers/{did}/slots/M1-37/documents', data=body, method='POST',
                                                  headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-DB': '1'}), timeout=30).read()
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True).new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#wkGo')
        assert page.locator('#go').is_disabled() and 'ليست للتقديم' in page.inner_text('#wkCard')       # the real export waits; the working copy does not
        gate = page.inner_text('#gateCard')                                                             # what stops the export, in the dossier's own words
        assert '1.1.1' in gate and 'نموذج الطلب' in gate and 'Neomycin sulphate' in gate and 'M1-01' not in gate and '@' not in gate
        page.click('#wkGo')
        page.wait_for_selector('#wkDl', timeout=60000)
        assert '1 مستند في مكانه' in page.inner_text('#wkRes')
        with page.expect_download(timeout=60000) as dl:
            page.click('#wkDl')
        out = tmp_path / 'w.zip'
        dl.value.save_as(out)
        names = zipfile.ZipFile(out).namelist()
        assert any(n.endswith('00-MISSING.txt') for n in names) and any('/Module 1/' in n and n.endswith('.pdf') for n in names)
        # the wizard's cards
        page.goto(f'{server}/#/new')
        page.wait_for_selector('.doccards')
        assert page.locator('[data-updoc="analytical_methods"]').count() == 1 and page.locator('[data-updoc="fees_receipt"]').count() == 1
        assert 'للمادة الفعالة أو لتشغيلة المنتج' in page.inner_text('.doccards')
        b.close()
    assert not errors, errors
