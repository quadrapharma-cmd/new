"""Each document's conditions before upload, in the browser (Playwright): under the wizard's base-document cards, «Each document's
conditions» for every item of the dossier by module, and in the item drawer."""
import json, socket, threading, time, urllib.request
import pytest

pw = pytest.importorskip('playwright.sync_api')

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


def post(url, path, body):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-DB': '1'}, method='POST')
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


@pytest.mark.parametrize('lang', ['ar', 'en'])
def test_conditions_before_upload(server, lang):
    did = post(server, '/api/dossiers', dict(name='Dermacure', profile=PROFILE, product=PRODUCT,
                                              envelope=dict(tracking='P-0001', applicant='Example Holder S.A.E.', invented_name='Dermacure')))['id']
    preview = post(server, '/api/profile/preview?country=EG', PROFILE)
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 390, 'height': 900} if lang == 'ar' else {'width': 1440, 'height': 1000})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
        page.goto(f'{server}/#/new')
        page.wait_for_selector('.doccard details.cond')
        cards = page.locator('.doccard details.cond').count()
        assert cards >= 10
        for _ in range(3):                                   # the wizard may paint its cards again just after the first paint: click the card that stays
            page.locator('.doccard details.cond summary').first.click()
            try:
                page.wait_for_selector('.doccard details.cond[open]', timeout=3000)
                break
            except pw.TimeoutError:
                pass
        first = page.inner_text('.doccard details.cond >> nth=0')
        assert ('PDF' in first) and (('شروطه' in first) if lang == 'ar' else ('conditions' in first))
        page.evaluate("s => openCondAll(s, 'country=EG')", preview['slots'])
        page.wait_for_selector('#dBody ul.cond')
        drawer = page.inner_text('#dBody')
        assert ('1.2.3.1' in drawer) and (('الشكل' in drawer and 'المحتوى' in drawer) if lang == 'ar' else ('Form' in drawer and 'Content' in drawer))
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')        # nothing wider than the screen
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_function("() => typeof S !== 'undefined' && S.board && S.board.slots && S.board.slots.length > 0")
        page.evaluate("openWhy('M1-37')")
        page.wait_for_selector('#itemCond ul.cond')
        item = page.inner_text('#itemCond')
        assert ('خطوط الإنتاج' in item) if lang == 'ar' else ('production lines' in item)
        b.close()
    assert not errors, errors
