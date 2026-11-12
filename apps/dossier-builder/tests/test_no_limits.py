"""«Do not put a limit on what is uploaded»: nothing of the program's own stops a large file, a long scan or a large draft — a file
over the old 60 MB of a draft, a wizard state over the old six million characters, a scan of more pages than the old 300. What a
machine cannot hold is an answer in words (E-MEMORY), never a crash; and a file taken out of a draft frees its space at once.
Made-up data («Dermacure»)."""
import io, struct
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from pypdf import PdfReader
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV

H = {'X-DB': '1'}
DATA = __import__('pathlib').Path(__file__).parent / 'data' / 'images'


@pytest.fixture()
def ws(tmp_path):
    return tmp_path / 'ws'


@pytest.fixture()
def c(ws):
    return TestClient(create_app(ws), raise_server_exceptions=False)


def blobs(ws):
    return {p.name for p in (ws / 'blobs').iterdir()}


def scan(mb):
    """A file of `mb` megabytes that does not repeat: a long scan."""
    block = bytes(range(256)) * 4096
    return b'%PDF-1.4\n' + b''.join(block[:-4] + struct.pack('>I', i) for i in range(mb))


def test_a_draft_takes_a_file_of_any_size_and_a_state_of_any_length(c, ws):
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0}}, headers=H).json()['id']
    big = scan(75)                                                                          # over the old 60 MB of a draft file
    r = c.post(f'/api/intake/drafts/{dr}/files', files={'file': ('stability scans 2019-2024.pdf', io.BytesIO(big), 'application/pdf')}, data={'kind': 'stability'}, headers=H)
    assert r.status_code == 201 and r.json()['size'] == len(big)
    assert c.get(f'/api/intake/drafts/{dr}/files/stability scans 2019-2024.pdf').content == big
    texts = {f'report {i}.pdf': {'text': 'Stability Study Report. Dermacure 2 % cream. ' * 900} for i in range(200)}      # what two hundred read documents leave in the wizard
    state = {'step': 2, 'd': {'name': 'Dermacure 2 % cream'}, 'texts': texts}
    assert len(str(state)) > 6_000_000
    assert c.put(f'/api/intake/drafts/{dr}', json={'state': state}, headers=H).status_code == 200
    assert len(c.get(f'/api/intake/drafts/{dr}').json()['state']['texts']) == 200


def test_a_file_taken_out_of_a_draft_frees_its_space(c, ws, tmp_path):
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    shared = make_pdf(tmp_path / 'pricing.pdf', 'Pricing Certificate').read_bytes()
    kept = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pricing.pdf', shared, 'application/pdf')}).json()
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0}}, headers=H).json()['id']
    big = scan(12)
    for name, data in (('scans.pdf', big), ('pricing.pdf', shared)):
        assert c.post(f'/api/intake/drafts/{dr}/files', files={'file': (name, io.BytesIO(data), 'application/pdf')}, data={'kind': 'other'}, headers=H).status_code == 201
    before = blobs(ws)
    r = c.delete(f'/api/intake/drafts/{dr}/files/scans.pdf', headers=H).json()
    assert r == {'ok': True, 'files_removed': 1} and len(before - blobs(ws)) == 1               # its 12 MB left the disk at once
    r = c.delete(f'/api/intake/drafts/{dr}/files/pricing.pdf', headers=H).json()
    assert r == {'ok': True, 'files_removed': 0} and kept['sha256'] in blobs(ws)                # the one a project uses stays
    assert c.delete(f'/api/intake/drafts/{dr}/files/never there.pdf', headers=H).json() == {'ok': True, 'files_removed': 0}
    assert c.get(f'/api/intake/drafts/{dr}').json()['files'] == []


def test_a_long_scan_keeps_every_page(c):
    page = (DATA / 'page.jpg').read_bytes()
    r = c.post('/api/images/pdf', files=[('files', (f'p{i}.jpg', page, 'image/jpeg')) for i in range(1100)], data={'title': 'fax.tif'})      # more than the old 300 pages, and than the framework's own 1000 files of one request
    assert r.status_code == 200 and len(PdfReader(io.BytesIO(r.content)).pages) == 1100


def test_a_large_batch_with_its_readings_is_taken_whole(c):
    """The readings that go with documents not placed yet are text fields of the request: together they pass the megabyte the
    framework allowed one field, and the batch used to be refused whole — with every file in it."""
    import json
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    names = [f'batch record {i}.txt' for i in range(260)]
    meta = {n: {'kind': 'other', 'text': ('Dermacure cream, batch record %d. ' % i) * 180} for i, n in enumerate(names)}
    assert len(json.dumps(meta)) > 1_300_000
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', (n, io.BytesIO(b'Dermacure batch record'), 'text/plain')) for n in names], data={'meta': json.dumps(meta)})
    assert r.status_code == 201 and len(r.json()) == 260
    assert len(c.get(f'/api/dossiers/{did}/board').json()['unassigned']) == 260


def test_memory_that_runs_out_is_an_answer_in_words(c, monkeypatch):
    from dossier_engine.app import store
    dr = c.post('/api/intake/drafts', json={'state': {'step': 0}}, headers=H).json()['id']

    def no_memory(*a, **k):
        raise MemoryError()
    monkeypatch.setattr(store.Store, 'put_blob', no_memory)                                 # while the file is being stored
    r = c.post(f'/api/intake/drafts/{dr}/files', files={'file': ('scans.pdf', io.BytesIO(b'%PDF-1.4 x'), 'application/pdf')}, data={'kind': 'other'}, headers=H)
    assert r.status_code == 507 and r.json()['detail']['code'] == 'E-MEMORY' and 'memory' in r.json()['detail']['en'] and 'ذاكرة' in r.json()['detail']['ar']
    monkeypatch.undo()
    from starlette import formparsers
    monkeypatch.setattr(formparsers.MultiPartParser, 'parse', no_memory)                    # while the upload's body is being read
    r = c.post(f'/api/intake/drafts/{dr}/files', files={'file': ('scans.pdf', io.BytesIO(b'%PDF-1.4 x'), 'application/pdf')}, data={'kind': 'other'}, headers=H)
    assert r.status_code == 507 and r.json()['detail']['code'] == 'E-MEMORY'
    monkeypatch.undo()
    assert c.get('/api/nothing-here').status_code == 404                                    # other errors answer as they always did
    assert c.get(f'/api/intake/drafts/{dr}/files/none.pdf').json()['detail']['code'] == 'E-FILE'
