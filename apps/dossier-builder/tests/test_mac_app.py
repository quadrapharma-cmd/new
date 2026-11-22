"""The Mac program's page and its local server (dossier_engine/combined/mac): only this computer and only with its token, the
Claude key kept in a file only the account can read, the settings, a dossier started, followed, resumed and opened — on the
made-up dossier, without a key (the program goes on with its rules), then finished with a person's decisions. No network."""
import json
import os
import shutil
import stat
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'engine'))
sys.path.insert(0, str(HERE))

import combined_fixture  # noqa: E402
from dossier_engine.combined.mac import app  # noqa: E402

NEED = [t for t in ('ocrmypdf', 'tesseract', 'pdftoppm', 'pdftotext', 'soffice') if not shutil.which(t)]


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv('EBOX_HOME', str(tmp_path / 'Documents' / 'eBOX'))
    monkeypatch.setenv('EBOX_SUPPORT', str(tmp_path / 'Support'))
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.setenv('PYTHONPATH', str(HERE.parent / 'engine') + os.pathsep + os.environ.get('PYTHONPATH', ''))
    combined_fixture.build(tmp_path / 'received')
    opened = []
    httpd, url = app.serve(open_browser=False, choose=lambda: {'ok': True, 'path': str(tmp_path / 'received'), 'files': 2, 'mb': 0.1},
                           opener=opened.append, check=lambda k: '' if k.endswith('good' * 8) else 'المفتاح غير صالح: لم يقبله Claude.')
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield httpd, url, tmp_path, opened
    httpd.app['runner'].stop()
    httpd.shutdown()


def call(url, path, body=None, token=None):
    base = url.split('/?')[0]
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', **({'X-EBOX-Token': token} if token else {})},
                                 method='GET' if body is None else 'POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b'{}') if 'json' in r.headers.get('Content-Type', '') else r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, None


def test_only_with_its_token(server):
    httpd, url, *_ = server
    token = httpd.app['token']
    assert call(url.split('?')[0], '')[0] == 403                                    # the page without the token
    with urllib.request.urlopen(url) as r:
        page = r.read().decode()
    assert 'eBOX' in page and token in page and 'الوحدة' not in page
    assert call(url, '/api/state')[0] == 403
    assert call(url, '/api/state', token='wrong')[0] == 403
    code, s = call(url, '/api/state', token=token)
    assert code == 200 and s['key'] is False and s['settings']['budget_usd'] == 25.0


def test_the_key_and_the_settings(server):
    httpd, url, tmp, _ = server
    t = httpd.app['token']
    assert call(url, '/api/key', {'key': 'abc'}, t)[1]['ok'] is False                # not a key's form
    r = call(url, '/api/key', {'key': 'sk-ant-api03-' + 'bad' * 8}, t)[1]
    assert r == {'ok': False, 'why': 'المفتاح غير صالح: لم يقبله Claude.'}
    assert call(url, '/api/key', {'key': 'sk-ant-api03-' + 'good' * 8}, t)[1] == {'ok': True}
    f = tmp / 'Support' / 'claude-api-key'
    assert stat.S_IMODE(f.stat().st_mode) == 0o600 and f.read_text() == 'sk-ant-api03-' + 'good' * 8
    assert call(url, '/api/state', token=t)[1]['key'] is True
    assert call(url, '/api/settings', {'budget_usd': 1000}, t)[1]['ok'] is False
    assert call(url, '/api/settings', {'budget_usd': 30}, t)[1] == {'ok': True}
    assert call(url, '/api/state', token=t)[1]['settings']['budget_usd'] == 30
    assert call(url, '/api/key/forget', {}, t)[1] == {'ok': True} and not f.exists()


def wait(url, t, most=400):
    for _ in range(most):
        s = call(url, '/api/state', token=t)[1]
        if s['current'] and not s['current']['running']:
            return s
        time.sleep(1)
    raise AssertionError('the run did not end')


@pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')
def test_a_dossier_started_resumed_and_opened(server):
    httpd, url, tmp, opened = server
    t = httpd.app['token']
    chosen = call(url, '/api/choose', {}, t)[1]
    r = call(url, '/api/start', {'source': chosen['path']}, t)[1]
    assert r['ok'] and r['id'].startswith('received ')
    s = wait(url, t)['current']
    # without a key: the rules alone, up to the eCTD, which needs the envelope Claude (or a person) records
    assert s['claude']['skipped'] == 'no key' and not s['finished']
    assert s['done'] == ['read', 'repeats', 'ocr', 'split', 'assemble', 'checks', 'decide', 'fix'] and s['exit'] != 0
    assert any('envelope' in l for l in s['log'])
    work = tmp / 'Documents' / 'eBOX' / r['id'] / 'work'
    dec = json.loads((work / 'dossier.json').read_text(encoding='utf-8'))
    assert dec['ctd_folder'].startswith('received - eBOX ')
    dec['ectd'].update({'envelope': {'identifier': '0a7c1c1e-5b8a-4d6e-9f10-3c2b1a0d9e8f', 'submission_type': 'maa', 'tracking': 'EDA-TEST-1',
                                     'unit': 'initial', 'applicant': 'Example Pharma Ltd.', 'invented_name': 'Zentorix',
                                     'registration': 'imported-finished', 'marketing': 'local', 'inn': ['zentorine'],
                                     'description': 'A made-up product for the tests'},
                        'manufacturer': 'example pharma ltd.', 'indication': 'example indication',
                        'product': {'product-name': 'zentorix', 'dosageform': 'film-coated tablet', 'manufacturer': 'example pharma ltd.'},
                        'substances': {'Zentorine': {'folder': 'zentorine-ex', 'substance': 'zentorine'}}})
    (work / 'dossier.json').write_text(json.dumps(dec), encoding='utf-8')
    assert call(url, '/api/start', {'resume': r['id']}, t)[1]['ok']                 # «متابعة من حيث توقّف»
    s = wait(url, t)['current']
    assert s['finished'] and s['exit'] == 0 and s['done'][-1] == 'report'
    assert call(url, '/api/open', {'id': r['id'], 'what': 'deliver'}, t)[1] == {'ok': True}
    assert call(url, '/api/open', {'id': r['id'], 'what': 'report'}, t)[1] == {'ok': True}
    assert Path(opened[0]).is_dir() and opened[1].endswith('ctd-report.pdf')
    assert call(url, '/api/open', {'id': '../x', 'what': 'folder'}, t)[0] == 404      # nothing outside the dossiers' folder
    runs = call(url, '/api/state', token=t)[1]['runs']
    assert runs[0]['id'] == r['id'] and runs[0]['finished']


def test_opened_twice_the_same_page(server):
    httpd, url, tmp, _ = server
    f = tmp / 'Support' / 'server.json'
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({'pid': os.getpid(), 'url': url}), encoding='utf-8')
    assert app.running_page() == url                                                # a second launch opens this page
    f.write_text(json.dumps({'pid': 999999, 'url': url}), encoding='utf-8')
    assert app.running_page() is None                                               # the first is gone: start anew
