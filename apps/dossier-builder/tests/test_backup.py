"""Backups and their restore drill (updates list, item 28): one ZIP of the database (consistent while the program runs), the stored
files and the submitted sequences — no secrets; one made by itself each day, seven kept; the drill restores into a fresh folder and
checks the database, every document's file and the activity log's chain."""
import io, os, time, zipfile
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine import backup
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}
PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])


def dossier_with_a_document(tmp_path):
    ws = tmp_path / 'ws'
    c = TestClient(create_app(ws, auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=dict(name='Dermacure'), envelope={}), headers=H).json()['id']
    pdf = make_pdf_lines(tmp_path / 's.pdf', ['Stability summary and conclusion', 'three batches'], 'S').read_bytes()
    assert c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('s.pdf', pdf, 'application/pdf')}, data={'meta': '{}'}, headers=H).status_code == 201
    (ws / 'drive.json').write_text('{"api_key": "AIzaSECRET"}')
    return ws, c


def test_a_backup_holds_the_workspace_not_its_secrets_and_the_drill_proves_it(tmp_path):
    ws, c = dossier_with_a_document(tmp_path)
    p = backup.make(ws)
    names = zipfile.ZipFile(p).namelist()
    assert 'workspace.sqlite' in names and 'MANIFEST.json' in names and any(n.startswith('blobs/') for n in names)
    assert 'drive.json' not in names and b'AIzaSECRET' not in p.read_bytes()
    d = backup.drill(p)
    assert d['ok'] and d['documents'] >= 1 and d['integrity'] == 'ok' and d['audit_ok']
    # a backup whose stored file was changed is caught
    bad = tmp_path / 'bad.zip'
    with zipfile.ZipFile(p) as zin, zipfile.ZipFile(bad, 'w') as zout:
        for i in zin.infolist():
            data = zin.read(i)
            zout.writestr(i, data + b'x' if i.filename.startswith('blobs/') else data)
    d2 = backup.drill(bad)
    assert not d2['ok'] and d2['altered']


def test_one_backup_a_day_by_itself_and_seven_kept(tmp_path):
    ws, c = dossier_with_a_document(tmp_path)
    first = backup.auto(ws)
    assert first and backup.auto(ws) is None                                       # the newest is fresh: none made
    os.utime(first, (time.time() - 2 * 86400, time.time() - 2 * 86400))
    for i in range(9):
        p = backup.make(ws)
        os.utime(p, (time.time() - (20 - i) * 3600 * 30, time.time() - (20 - i) * 3600 * 30))
        time.sleep(1.01)
    backup.prune(ws)
    assert len(backup.listing(ws)) == 7


def test_backups_from_the_program_for_an_administrator(tmp_path):
    ws, c = dossier_with_a_document(tmp_path)
    r = c.get('/api/backups').json()
    assert r['items'] == [] and r['auto'] is False and r['keep'] == 7                  # the tests run without the automatic thread
    made = c.post('/api/backups', headers=H)
    assert made.status_code == 201
    name = made.json()['name']
    assert [x['name'] for x in c.get('/api/backups').json()['items']] == [name]
    z = c.get(f'/api/backups/{name}')
    assert z.status_code == 200 and z.content[:2] == b'PK' and 'workspace.sqlite' in zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    d = c.post(f'/api/backups/{name}/drill', headers=H).json()
    assert d['ok'] and d['documents'] >= 1
    for bad in ('../workspace.sqlite', 'backup-x.zip', 'drive.json'):                   # nothing outside the backups folder is ever served
        assert c.get(f'/api/backups/{bad}').status_code == 404
    events = [e['event'] for e in c.get('/api/audit').json()] if c.get('/api/audit').status_code == 200 else []
    assert not events or {'backup.made', 'backup.drill'} <= set(events)


def test_backups_are_refused_to_an_editor_when_sign_in_is_on(tmp_path):
    ws = tmp_path / 'ws'
    c = TestClient(create_app(ws, auth_enabled=True))
    from dossier_engine.app.auth import Auth
    Auth(ws, True).add_user('editor1', 'a-long-password-1', 'editor')
    assert c.post('/api/login', json={'username': 'editor1', 'password': 'a-long-password-1'}, headers=H).status_code == 200
    assert c.get('/api/backups').status_code == 403 and c.post('/api/backups', headers=H).status_code == 403


def test_the_automatic_backup_runs_on_its_own_thread(tmp_path):
    ws, c = dossier_with_a_document(tmp_path)
    backup.start_auto(ws, lambda: True, every=3600, delay=0)
    for _ in range(100):
        if backup.listing(ws):
            break
        time.sleep(0.1)
    assert len(backup.listing(ws)) == 1


def test_the_qualification_package_runs_iq_and_oq_here(tmp_path):
    ws, c = dossier_with_a_document(tmp_path)
    r = c.post('/api/qualification', headers=H)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['summary']['oq']['fail'] == 0 and j['summary']['oq']['pass'] >= 10, [x for x in j['oq'] if x['result'] != 'pass']
    assert j['summary']['iq']['fail'] == 0, [x for x in j['iq'] if x['result'] == 'fail']
    d = c.get(f"/api/qualification/{j['docx']}")
    assert d.status_code == 200 and d.content[:2] == b'PK'
    import docx
    text = '\n'.join(p.text for p in docx.Document(io.BytesIO(d.content)).paragraphs)
    assert 'Performance qualification' in text and 'Approved by (head of quality)' in text
    assert c.get('/api/qualification/../workspace.sqlite').status_code == 404
