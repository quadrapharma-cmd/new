"""The library («المكتبة», Dossier Builder v2's Part 1: every rule with its source, checked word for word) inside the program: a
button beside the language, and in each item's drawer a link that opens the library at that item's own record. The library took
these packs over with their ids («<authority>/<id>»), so every item of every authority must have its record there — the authority's
own item, or the common CTD's it stands on — under a link name the library gives no other record."""
import json, pathlib, re, socket, threading, time, urllib.request
import pytest
import yaml
from dossier_engine import packs

pw = pytest.importorskip('playwright.sync_api')
LIBRARY = pathlib.Path(__file__).resolve().parents[2] / 'dossier-builder-v2' / 'knowledge' / 'requirements'
LIB_URL = 'https://claude.ai/artifact/6sSh9Tgi3jXji54PJbYcxf'
slug = lambda rid: 'r-' + re.sub(r'^-+|-+$', '', re.sub(r'[^A-Za-z0-9]+', '-', rid))       # the library's own link name (library/app.js)


def library_ids():
    ids = []
    for f in sorted(LIBRARY.glob('*.yaml')):
        ids += [r['id'] for r in yaml.safe_load(f.read_text(encoding='utf-8'))]
    return ids


@pytest.mark.skipif(not LIBRARY.exists(), reason='the library (apps/dossier-builder-v2) is not in this checkout')
def test_every_item_of_every_authority_has_its_record_in_the_library():
    have = library_ids()
    assert len(set(map(slug, have))) == len(have)                          # no two records share a link name (none gets a «-b»)
    have = set(have)
    for meta in packs.available():
        pack = packs.load(meta['id'])
        missing = [r['id'] for r in pack.requirements if pack.library_id(r['id']) not in have]
        assert not missing, (meta['id'], missing[:10])
    gcc = packs.load('gcc.ctd.m1.v1')
    assert gcc.library_id('GCC-3.2.R') == 'GCC/GCC-3.2.R' and gcc.library_id('S-01') == 'ICH/S-01'       # own (even in Module 3) / common
    assert packs.load('eda.ctd.nta065.v5').library_id('P-09') == 'EG-EDA/P-09' and gcc.library_id('no-such-item') is None


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


def call(url, path, body=None):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-DB': '1', 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Exampletine', manufacturer='Example API Co.', option='CEP')])


def test_the_button_and_each_items_link_open_the_library(server):
    eg = call(server, '/api/dossiers', dict(name='Dermacure EG', profile=PROFILE, product=dict(name='Dermacure 20 mg', dosageform='cream', manufacturer='Example Pharm'), envelope={}))['id']
    sa = call(server, '/api/dossiers', dict(name='Dermacure KSA', country='SA', profile={**PROFILE, 'origin': 'imported'},
                                            product=dict(name='Dermacure 20 mg', dosageform='cream', manufacturer='Example Pharm'), envelope={}))['id']
    board = {x['slot_id']: x['library'] for x in call(server, f'/api/dossiers/{eg}/board')['slots']}
    assert board['M1-11'] == 'EG-EDA/M1-11' and board['P-09'] == 'EG-EDA/P-09'
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(f'{server}/#/d/{eg}/board')
        page.wait_for_selector('[data-why="M1-11"]', timeout=20000)
        btn = page.locator('#libBtn')
        assert btn.inner_text().strip() == 'المكتبة' and btn.get_attribute('href') == LIB_URL and btn.get_attribute('target') == '_blank'
        page.click('[data-why="M1-11"]')
        page.wait_for_selector('#libItem')
        link = page.locator('#libItem')
        assert link.get_attribute('href') == LIB_URL + '#r-EG-EDA-M1-11' and link.get_attribute('target') == '_blank'
        assert 'فتح هذا البند في المكتبة' in link.inner_text()
        page.click('#dClose')
        page.click('#lang-en')
        assert page.locator('#libBtn').inner_text().strip() == 'Library'
        page.goto(f'{server}/#/d/{sa}/board')                               # a Gulf dossier: its own items, and the common CTD's
        page.wait_for_selector('#boardSign', timeout=20000)
        page.click('[data-f="all"]')                                         # an optional item is not a point to close: under «الكل»
        page.wait_for_selector('[data-why="GCC-1.4.2"]', timeout=20000)
        page.click('[data-why="GCC-1.4.2"]')
        page.wait_for_selector('#libItem')
        assert page.locator('#libItem').get_attribute('href') == LIB_URL + '#r-GCC-GCC-1-4-2'
        page.click('#dClose')
        common = next(x for x in call(server, f'/api/dossiers/{sa}/board')['slots'] if (x['library'] or '').startswith('ICH/'))
        page.evaluate('id => openWhy(id)', common['slot_id'])            # the drawer an item's click opens (Modules 2–5 sit folded on the board)
        page.wait_for_selector('#libItem')
        assert page.locator('#libItem').get_attribute('href') == LIB_URL + '#' + slug(common['library'])
        b.close()
    assert errors == [], errors
