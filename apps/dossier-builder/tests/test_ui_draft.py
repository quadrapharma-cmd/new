"""The board in the browser (Playwright): every item has «Template», draftable items have «Make it for me»; the item drawer shows
the template panel (kind, what an acceptable copy shows, sections, base documents present); «Make it for me» stores an unsigned
Word draft with its gaps — from the data alone on a plain server, and from claude.ai's model when the page has it (stub)."""
import socket, threading, time, urllib.request, json
import pytest
from test_api import PROFILE, PRODUCT, ENV

pw = pytest.importorskip('playwright.sync_api')
OUT = '/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/arabic'


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


def call(url, path, body=None, method=None):
    req = urllib.request.Request(url + path, method=method or ('POST' if body is not None else 'GET'), data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def test_templates_and_make_it_for_me(server):
    did = call(server, '/api/dossiers', dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV))['id']
    call(server, f'/api/dossiers/{did}/data', {'composition': [{'name': 'Neomycin sulphate', 'role': 'active', 'standard': 'Ph. Eur.', 'amount': '3.5 mg'}]}, method='PUT')
    board = call(server, f'/api/dossiers/{did}/board')
    p01 = next(s for s in board['slots'] if s['req_id'] == 'P-01')
    gmp = next(s for s in board['slots'] if s['req_id'] == 'M1-37')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960}, device_scale_factor=2)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_selector(f'[data-tpl="{p01["slot_id"]}"]')
        assert page.locator('[data-tpl]').count() >= 20                                        # a template button in front of every shown item
        assert page.locator(f'[data-draft="{p01["slot_id"]}"]').count() == 1                   # the program drafts P-01 fully
        assert page.locator(f'[data-draft="{gmp["slot_id"]}"]').count() == 0                   # never a GMP certificate
        # the template panel of a third-party document: what an acceptable copy shows
        page.click(f'[data-tpl="{gmp["slot_id"]}"]')
        page.wait_for_function("() => document.querySelector('#tplPanel') && document.querySelector('#tplPanel').textContent.includes('جهة خارجية')")
        assert 'production lines specified' in page.inner_text('#tplPanel')
        page.click('#dClose')
        # the template panel of an authored document, then «make it for me» from the data alone (no model on this server)
        page.click(f'[data-tpl="{p01["slot_id"]}"]')
        page.wait_for_selector('#tplPanel .docprev')
        panel = page.inner_text('#tplPanel')
        assert 'البرنامج بيكتب مسودة المستند ده' in panel and 'راجعها قبل' in panel and 'التركيب (تركيبة الوحدة)' in panel and 'مفيش موديل هنا' in panel
        assert 'Neomycin sulphate' in panel and 'Ph. Eur.' in panel                         # the live page already carries the product's own data
        assert page.locator('#tplPanel .docprev .ex').count() >= 1                           # and grey examples where nothing is known yet
        page.locator('#drawer').screenshot(path=f'{OUT}/template_live_ar.png')
        page.click('#dpFill')                                                                # «make it for me»: fills the page (no model here: from the data)
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('الصفحة اتملت')")
        page.click('#tplPanel .docprev .dp-sec[data-sec=\"removed\"] .dp-p')                 # the user types the part the documents lack
        page.keyboard.type('None removed during manufacture.')
        page.click('#dpSave')
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('المسودة اتضافت')")
        page.wait_for_function("() => document.querySelector('#dBody') && document.querySelector('#dBody').textContent.includes('P-01-draft.docx')")
        page.wait_for_function("() => /اللي لسه ناقص|احفظ مسودة Word/.test(document.querySelector('#dBody').textContent)", timeout=20000)      # the item's panel is drawn after the list (it comes back faster since the rule packs are read faster)
        body = page.inner_text('#dBody')
        assert 'اللي لسه ناقص' in body or 'احفظ مسودة Word' in body
        docs = call(server, f'/api/dossiers/{did}/board')
        d = next(s for s in docs['slots'] if s['req_id'] == 'P-01')['documents'][0]
        assert d['meta']['generated'] == 'draft' and d['meta']['draft_how'] == 'answers'     # saved from the page the user edited
        b.close()
    assert not errors, errors


def test_make_it_for_me_with_the_pages_model(server):
    """claude.ai's model in the page (stand-in): the answers go to the engine, which renders and stores the Word draft."""
    did = call(server, '/api/dossiers', dict(name='Dermacure 2', profile=PROFILE, product=PRODUCT, envelope=ENV))['id']
    board = call(server, f'/api/dossiers/{did}/board')
    m136 = next(s for s in board['slots'] if s['req_id'] == 'M1-36')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 960})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.add_init_script("""window.__asked=[]; window.DBAI={ available: async()=>true, extract: async()=>null,
          ask: async(prompt)=>{ window.__asked.push(prompt); return {sections:{actives:{rows:[['Neomycin sulphate','Assay','90.0–110.0 %','HPLC','Ph. Eur.']]}}, gaps:[{what:'Other markets',why:'no document lists them',ar:'أسواق أخرى'}], sources:{actives:'coa.pdf'}}; } };""")
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_selector(f'[data-draft="{m136["slot_id"]}"]')
        page.click(f'[data-draft="{m136["slot_id"]}"]')                                          # straight from the row
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('اتملت بموديل claude.ai')")
        asked = page.evaluate("() => window.__asked")
        assert len(asked) == 1 and 'M1-36' in asked[0] and 'JSON' in asked[0]                     # the engine's prompt went to the page's model
        docs = call(server, f'/api/dossiers/{did}/board')
        d = next(s for s in docs['slots'] if s['req_id'] == 'M1-36')['documents'][0]
        assert d['meta']['draft_how'] == 'answers' and d['meta']['gaps'][0]['what'] == 'Other markets' and d['meta']['sources'] == {'actives': 'coa.pdf'}
        b.close()
    assert not errors, errors
