"""The Assistant in the browser (Playwright, Arabic): the floating button on a dossier, the settings form when no key is set,
saving the key, a message that ends in an approval card (export), the user's decision and the Assistant's closing report."""
import socket, threading, time
import pytest
from dossier_engine.assistant import runner
from test_assistant import FakeClient, msg

pw = pytest.importorskip('playwright.sync_api')
OUT = '/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/arabic'


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    cfg = uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error')
    srv = uvicorn.Server(cfg)
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


@pytest.fixture(scope='module')
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def test_assistant_drawer_journey(server, browser, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    fake = FakeClient([lambda kw: msg([{'type': 'text', 'text': 'هصدّر الملف دلوقتي.'},
                                       {'type': 'tool_use', 'id': 'e1', 'name': 'export_dossier', 'input': {'rationale': 'طلب المستخدم', 'outputs': ['ctd']}}], 'tool_use'),
                       lambda kw: msg([{'type': 'text', 'text': 'خلصت. التصدير اترفض منك، والملف زي ما هو.'}])])
    runner.CLIENT_FACTORY = lambda key: fake
    try:
        import json, urllib.request
        req = urllib.request.Request(server + '/api/dossiers', data=json.dumps({
            'name': 'Dermacure 10 g', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical', 'leaflet': 'english',
                                                 'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'Sichuan Example', 'option': 'FULL'}]},
            'product': {'name': 'Dermacure', 'dosage_form': 'Topical Powder'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}}).encode(),
            headers={'content-type': 'application/json', 'X-DB': '1'})
        did = json.loads(urllib.request.urlopen(req).read())['id']
        page = browser.new_page(viewport={'width': 1440, 'height': 960}, device_scale_factor=2)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(server + '/')
        assert page.query_selector('#asstFab') is None                      # not on the home page
        page.goto(server + f'/#/d/{did}/board')
        page.wait_for_selector('#asstFab')
        page.click('#asstFab')
        page.wait_for_selector('#asstSetBox')                                # no key yet → the settings form
        assert 'مفتاح' in page.inner_text('#asstBody')
        page.fill('#asstKey', 'sk-ant-test-0123456789abcdef')
        page.click('#asstSave')
        page.wait_for_selector('text=المفتاح شغّال')
        page.wait_for_selector('#asstSend:not([disabled])', timeout=10000)
        page.locator('#drawer').screenshot(path=f'{OUT}/asst_ready_ar.png')
        page.fill('#asstText', 'صدّر الملف')
        page.click('#asstSend')
        page.wait_for_selector('[data-apv][data-dec=deny]', timeout=20000)   # the Assistant asked to export → approval card
        body = page.inner_text('#asstBody')
        assert 'المساعد عايز يعمل الخطوة دي' in body and 'تصدير الملف' in body and 'هصدّر الملف دلوقتي' in body
        page.locator('#drawer').screenshot(path=f'{OUT}/asst_approval_ar.png')
        page.click('[data-apv][data-dec=deny]')
        page.wait_for_selector('text=التصدير اترفض منك', timeout=20000)
        page.wait_for_selector('#asstSend:not([disabled])', timeout=10000)
        page.locator('#drawer').screenshot(path=f'{OUT}/asst_done_ar.png')
        assert not errors, errors
        page.close()
    finally:
        runner.CLIENT_FACTORY = None
