"""The EU eCTD in the browser (Playwright): the EU leaflet item asks for the EU's own PI types, languages and country; the export page
offers the EU sequence with the procedure's countries and number, and no Egyptian acknowledgement."""
import json, socket, threading, time, urllib.request
import pytest

pw = pytest.importorskip('playwright.sync_api')

GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')],
               extra={'eu_procedure': 'dcp', 'eu_legal_basis': 'generic'})
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


def test_the_eu_leaflet_details_and_the_eu_export(server):
    did = post(server, '/api/dossiers', dict(name='Dermacure EU', country='DE', profile=GENERIC, product=PRODUCT,
                                              envelope=dict(applicant='Example Pharm Co.', invented_name='Dermacure')))['id']
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','en')")
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_function("() => typeof S !== 'undefined' && S.board && S.board.slots && S.board.slots.length > 0")
        page.evaluate("startUpload('EU-1.3.1')")
        page.wait_for_selector('#mType')
        types = page.eval_on_selector('#mType', 's => [...s.options].map(o => o.value)')
        langs = page.eval_on_selector('#mLang', 's => [...s.options].map(o => o.value)')
        countries = page.eval_on_selector('#mCountry', 's => [...s.options].map(o => o.value)')
        assert types == ['spc', 'annex2', 'outer', 'interpack', 'impack', 'other', 'pl', 'combined']
        assert len(langs) == 26 and page.input_value('#mLang') == 'en' and 'ar' not in langs
        assert countries[0] == '' and {'de', 'fr', 'el'} <= set(countries) and 'ema' not in countries
        page.select_option('#mCountry', 'de')
        assert page.evaluate("metaOf('pi')") == {'pi_type': 'spc', 'lang': 'en', 'eu_country': 'de'}
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#euEnv')
        outs = page.inner_text('#view')
        assert 'EU M1 3.1.1' in outs and 'eCTD 4.0' not in outs
        assert page.locator('#ctdOnly').count() == 0 and not page.is_visible('#ack')
        checked = page.eval_on_selector_all('#euCs input:checked', 'xs => xs.map(x => x.value)')
        assert checked == ['de']                                          # the dossier's own country, the others ticked by the user
        assert page.locator('#euTrack').count() == 1
        page.screenshot(path='/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/eu/export-eu.png', full_page=True)
        b.close()
    assert not errors, errors
