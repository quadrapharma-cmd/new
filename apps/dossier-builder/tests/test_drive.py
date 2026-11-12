"""Google Drive as a source, against a stand-in for Google's HTTP: link parsing, listing a folder (two pages, sub-folders,
what is usable), reading files and exporting Google Docs to Word, the service-account token flow, settings that never return the
key, the endpoints, and the Assistant reading a Drive file into the dossier."""
import io, json, os, re, urllib.parse
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import drive
from dossier_engine.app.api import create_app
from dossier_engine.assistant import runner
from test_assistant import FakeClient, msg, _results, _wait

PDF = None
DOCX = b'PK\x03\x04 fake docx'
FOLDER = drive.FOLDER
FILES_P1 = {'files': [{'id': 'sub1', 'name': 'Module 3', 'mimeType': FOLDER}, {'id': 'f1', 'name': 'licence.pdf', 'mimeType': 'application/pdf', 'size': '12345', 'modifiedTime': '2026-01-02T00:00:00Z'},
                      {'id': 'g1', 'name': 'Specification', 'mimeType': 'application/vnd.google-apps.document'}], 'nextPageToken': 'p2'}
FILES_P2 = {'files': [{'id': 'x1', 'name': 'backup.rar', 'mimeType': 'application/rar', 'size': '10'}]}
SUB = {'files': [{'id': 'f2', 'name': 'stability.pdf', 'mimeType': 'application/pdf', 'size': '5'}]}


def fake_http(calls):
    def http(method, url, headers, data):
        calls.append((method, url, dict(headers or {}), data))
        u = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(u.query)
        if u.netloc == 'oauth2.googleapis.com':
            body = urllib.parse.parse_qs(data.decode())
            assert body['grant_type'][0] == 'urn:ietf:params:oauth:grant-type:jwt-bearer' and body['assertion'][0].count('.') == 2
            return 200, 'application/json', json.dumps({'access_token': 'tok-123', 'expires_in': 3600}).encode()
        if u.path == '/drive/v3/files':
            if "'sub1'" in q['q'][0]:
                return 200, 'application/json', json.dumps(SUB).encode()
            return 200, 'application/json', json.dumps(FILES_P2 if q.get('pageToken') == ['p2'] else FILES_P1).encode()
        if u.path == '/drive/v3/files/f1' and q.get('alt') == ['media']:
            return 200, 'application/pdf', PDF
        if u.path == '/drive/v3/files/f1':
            return 200, 'application/json', json.dumps({'id': 'f1', 'name': 'licence.pdf', 'mimeType': 'application/pdf', 'size': '12345'}).encode()
        if u.path == '/drive/v3/files/g1/export':
            assert q['mimeType'][0].endswith('wordprocessingml.document')
            return 200, q['mimeType'][0], DOCX
        if u.path == '/drive/v3/files/nope':
            return 404, 'application/json', b'{}'
        if u.path == '/drive/v3/files/secret':
            return 403, 'application/json', b'{}'
        return 500, 'text/plain', b'unexpected ' + url.encode()
    return http


@pytest.fixture(autouse=True)
def transport(tmp_path):
    global PDF
    PDF = make_pdf_lines(tmp_path / 'lic.pdf', ['Final Registration License', 'Trade Name: Dermacure'], 'Licence').read_bytes()
    calls = []
    drive.HTTP = fake_http(calls)
    yield calls
    drive.HTTP = None


def test_links():
    assert drive.parse_link('https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUv?usp=sharing') == {'kind': 'folder', 'id': '1AbCdEfGhIjKlMnOpQrStUv', 'native': None}
    assert drive.parse_link('https://drive.google.com/drive/u/0/folders/1AbCdEfGhIjKlMnOpQrStUv')['id'] == '1AbCdEfGhIjKlMnOpQrStUv'
    assert drive.parse_link('https://drive.google.com/file/d/1XyZ_abcDEF-ghiJKLmnop/view?usp=drive_link') == {'kind': 'file', 'id': '1XyZ_abcDEF-ghiJKLmnop', 'native': None}
    assert drive.parse_link('https://docs.google.com/document/d/1DocIdAbcdefghijklmnop/edit')['native'] == 'doc'
    assert drive.parse_link('https://drive.google.com/open?id=1OpenIdAbcdefghijklmn')['kind'] == 'file'
    assert drive.parse_link('1AbCdEfGhIjKlMnOpQrStUvWxYz') == {'kind': 'folder', 'id': '1AbCdEfGhIjKlMnOpQrStUvWxYz', 'native': None}
    assert drive.parse_link('https://example.com/x') is None and drive.parse_link('') is None


def test_api_key_lists_and_reads(transport):
    import asyncio
    asyncio.run(_api_key_lists_and_reads(transport))


async def _api_key_lists_and_reads(transport):
    d = drive.Drive({'api_key': 'AIzaTESTKEY0000000000'}, browser=False)
    assert d.mode == 'api_key'
    files = await d.list_folder('root1')
    assert [f['name'] for f in files] == ['Module 3', 'licence.pdf', 'Specification', 'backup.rar']
    assert [f['kind'] for f in files] == ['folder', 'file', 'file', 'file'] and [f['usable'] for f in files] == [False, True, True, False]
    assert files[1]['size'] == 12345 and files[2]['export'] == '.docx'
    assert all('key=AIzaTESTKEY0000000000' in c[1] for c in transport if 'googleapis' in c[1])
    deep = await d.list_folder('root1', recursive=True)
    assert [f['path'] for f in deep] == ['Module 3', 'Module 3/stability.pdf', 'licence.pdf', 'Specification', 'backup.rar']
    name, data, mt = await d.fetch('f1')
    assert name == 'licence.pdf' and data[:4] == b'%PDF' and mt == 'application/pdf'
    name, data, mt = await d.fetch('g1', 'Specification', 'application/vnd.google-apps.document')
    assert name == 'Specification.docx' and data == DOCX and mt.endswith('wordprocessingml.document')
    with pytest.raises(drive.DriveError) as e:
        await d.fetch('nope', 'x.pdf', 'application/pdf')
    assert e.value.code == 'E-DRIVE-404'
    with pytest.raises(drive.DriveError) as e:
        await d.fetch('secret', 'x.pdf', 'application/pdf')
    assert e.value.code == 'E-DRIVE-FORBIDDEN'


def test_service_account_token_flow(transport):
    import asyncio
    asyncio.run(_service_account_token_flow(transport))


async def _service_account_token_flow(transport):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    d = drive.Drive({'service_account': {'client_email': 'bot@proj.iam.gserviceaccount.com', 'private_key': pem, 'token_uri': 'https://oauth2.googleapis.com/token'}}, browser=False)
    assert d.mode == 'service_account'
    files = await d.list_folder('root1')
    assert len(files) == 4
    auth = [c for c in transport if 'googleapis.com/drive' in c[1]]
    assert all(c[2].get('Authorization') == 'Bearer tok-123' for c in auth) and not any('key=' in c[1] for c in auth)
    assert sum(1 for c in transport if 'oauth2' in c[1]) == 1                        # the token is cached
    await d.fetch('f1')
    assert sum(1 for c in transport if 'oauth2' in c[1]) == 1
    assert drive.Drive({'service_account': {'client_email': 'x', 'private_key': pem, 'token_uri': 'u'}}, browser=True).mode == 'public'   # never in a browser


def test_public_folder_without_any_key(transport):
    html = ('<div class="flip-entry" id="entry-AAA11111111111111111"><div class="flip-entry-info"><div class="flip-entry-title">licence.pdf</div></div></div>'
            '<div class="flip-entry" id="entry-BBB22222222222222222"><div class="flip-entry-folder"></div><div class="flip-entry-title">Module 3</div></div>')
    def http(method, url, headers, data):
        if 'embeddedfolderview' in url:
            return 200, 'text/html', html.encode()
        if 'uc?export=download' in url:
            return 200, 'application/pdf', PDF
        return 500, '', b''
    drive.HTTP = http
    import asyncio
    d = drive.Drive({}, browser=False)
    files = asyncio.run(d.list_folder('ROOT'))
    assert [(f['name'], f['kind'], f['usable']) for f in files] == [('licence.pdf', 'file', True), ('Module 3', 'folder', False)]
    name, data, mt = asyncio.run(d.fetch('AAA11111111111111111', 'licence.pdf', 'application/pdf'))
    assert data[:4] == b'%PDF' and mt == 'application/pdf'
    with pytest.raises(drive.DriveError) as e:
        asyncio.run(drive.Drive({}, browser=True).list_folder('ROOT'))
    assert e.value.code == 'E-DRIVE-KEY'


def test_endpoints_settings_list_and_file(tmp_path, transport):
    c = TestClient(create_app(tmp_path / 'ws'))
    s = c.get('/api/drive/settings').json()
    assert s['mode'] == 'public' and s['configured'] is True and s['browser'] is False
    assert c.get('/api/capabilities').json()['drive']['mode'] == 'public'
    r = c.put('/api/drive/settings', json={'api_key': 'AIzaTESTKEY0000000000'})
    assert r.status_code == 200 and r.json()['mode'] == 'api_key' and 'AIzaTESTKEY0000000000' not in r.text and r.json()['api_key_hint'].startswith('AIzaTE')
    assert (os.stat(tmp_path / 'ws' / 'drive.json').st_mode & 0o777) == 0o600
    assert c.put('/api/drive/settings', json={'service_account': {'client_email': 'bot@x'}}).status_code == 422          # no private key
    assert c.post('/api/drive/list', json={'link': 'https://example.com/nothing'}).status_code == 422
    r = c.post('/api/drive/list', json={'link': 'https://drive.google.com/drive/folders/root1xxxxxxxxxxxx'})
    assert r.status_code == 200 and r.json()['usable'] == 2 and r.json()['link']['kind'] == 'folder' and [f['name'] for f in r.json()['files']][1] == 'licence.pdf'
    r = c.get('/api/drive/files/f1?name=licence.pdf&mime=application/pdf')
    assert r.status_code == 200 and r.content[:4] == b'%PDF' and 'licence.pdf' in r.headers['content-disposition']
    r = c.get('/api/drive/files/g1?name=Specification&mime=application/vnd.google-apps.document')
    assert r.content == DOCX and bytes.fromhex(r.headers['x-filename']).decode() == 'Specification.docx'
    assert c.get('/api/drive/files/secret?name=x.pdf&mime=application/pdf').status_code == 403
    did = c.post('/api/dossiers', json={'name': 'Dermacure', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical', 'leaflet': 'english',
                                                                       'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'X', 'option': 'FULL'}]},
                                        'product': {'name': 'Dermacure'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}}).json()['id']
    r = c.post(f'/api/dossiers/{did}/drive/stage', json={'files': [{'id': 'f1', 'name': 'licence.pdf', 'mime': 'application/pdf'}, {'id': 'nope', 'name': 'x.pdf', 'mime': 'application/pdf'}]})
    assert r.status_code == 201 and r.json()[0]['filename'] == 'licence.pdf' and 'error' in r.json()[1]
    board = c.get(f'/api/dossiers/{did}/board').json()
    assert [d['filename'] for d in board['unassigned']] == ['licence.pdf']


def test_assistant_reads_a_drive_folder(tmp_path, transport, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    c = TestClient(create_app(tmp_path / 'ws'))
    c.put('/api/assistant/settings', json={'api_key': 'sk-ant-test-0123456789abcdef'})
    c.put('/api/drive/settings', json={'api_key': 'AIzaTESTKEY0000000000'})
    did = c.post('/api/dossiers', json={'name': 'Dermacure', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical', 'leaflet': 'english',
                                                                       'dosage_specifics': [], 'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'X', 'option': 'FULL'}]},
                                        'product': {'name': 'Dermacure'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}}).json()['id']
    def s1(kw):
        return msg([{'type': 'tool_use', 'id': 'd1', 'name': 'drive_list', 'input': {'link': 'https://drive.google.com/drive/folders/root1xxxxxxxxxxxx', 'recursive': True}}], 'tool_use')
    def s2(kw):
        lst = json.loads(_results(kw)['d1']['content'])
        assert [f['name'] for f in lst['files']][:2] == ['Module 3', 'stability.pdf']
        return msg([{'type': 'tool_use', 'id': 'd2', 'name': 'drive_fetch', 'input': {'file_id': 'f1', 'name': 'licence.pdf', 'mime': 'application/pdf', 'rationale': 'the registration licence'}}], 'tool_use')
    def s3(kw):
        res = json.loads(_results(kw)['d2']['content'])
        assert res['document']['filename'] == 'licence.pdf'
        return msg([{'type': 'text', 'text': 'جبت الإخطار من Drive وحطيته في الملف كمستند غير موضوع.'}])
    fake = FakeClient([s1, s2, s3])
    runner.CLIENT_FACTORY = lambda key: fake
    try:
        assert c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'اقرأ فولدر Drive ده وهات الإخطار'}).status_code == 201
        s = _wait(c, did, states=('done', 'error'))
    finally:
        runner.CLIENT_FACTORY = None
    assert s['run']['status'] == 'done', s['run']
    board = c.get(f'/api/dossiers/{did}/board').json()
    assert [d['filename'] for d in board['unassigned']] == ['licence.pdf'] and board['unassigned'][0]['meta']['from_drive'] == 'f1'
