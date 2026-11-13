"""The browser edition reads scans in the page (ui/assets/ocr.js: the desktop's reading — Tesseract with the accurate Arabic model,
PaddleOCR's second reader, pages turned upright — done by the browser), and the engine keeps that reading by the file's SHA-256
(extract.keep_browser_reading): read_text then takes it as it takes PdfCraft's. Here the engine is told it has no OCR of its own, as in
the browser (Pyodide); the page's reading is given as web/boot.js sends it. Fictional files."""
import io
import pytest
from fastapi.testclient import TestClient
from dossier_engine import extract, pdfcraft
from dossier_engine.app.api import create_app
from test_extract_arabic import LINES

REP = {'words': 120, 'pages': [{'page': 1, 'words': 120}], 'second_reader': 3, 'weak': [], 'models': 'best 4.1.0',
       'quality': {'1': {'words': 120, 'low': 1.7, 'mean': 88.2, 'numbers': ['10/7/17'], 'read': 'as scanned',
                         'second': {'read': 3, 'changed': [{'was': '\\YPEO/Y-YO', 'now': '١٢٣٤٥/٢٠٢٥'}, {'was': '١10/١1/17', 'now': '١٥/٠٣/٢٠٢٥'}]}}}}
TAG = 'ara+eng+best+paddle'


def scan(version=b'1.4', seed=0):
    """A PDF whose one page is an image only — what a scanner gives; `version` its header line."""
    from PIL import Image, ImageDraw
    im = Image.new('L', (850, 1100), 255)
    d = ImageDraw.Draw(im)
    for i in range(12):
        d.rectangle([60, 80 + 70 * i, 60 + 500 + 13 * ((i + seed) % 7), 110 + 70 * i], fill=0)
    buf = io.BytesIO()
    im.save(buf, 'PDF', resolution=100)
    data = buf.getvalue()
    assert data.startswith(b'%PDF-1.4')
    return data.replace(b'%PDF-1.4', b'%PDF-' + version, 1)


@pytest.fixture()
def browser(monkeypatch):
    """The engine as in the browser edition: no OCR of its own."""
    monkeypatch.setattr(pdfcraft, 'ocr_info', lambda: None)


def test_the_pages_reading_is_taken_as_the_reading_of_the_scan(browser, tmp_path):
    extract.READ_DIR = tmp_path / 'text'
    data = scan()
    f = extract.read_files([('scan0001.pdf', data)])['files'][0]
    assert f['scanned'] and not f.get('ocr') and f['chars'] == 0                       # not read yet: nothing is guessed
    extract.keep_browser_reading(extract._sha(data), ['\n'.join(LINES)], REP, TAG)
    r = extract.read_files([('scan0001.pdf', data)])
    f, rules = r['files'][0], r['rules']
    assert f['ocr'] and f['reader'] == 'browser-ocr' and f['scanned'] and f['kind'] == 'licence' and f['chars'] > 300
    assert rules['registration']['reg_no'] == '34567/2025' and rules['registration']['reg_date'] == '2025-03-15'
    assert rules['product']['name'].startswith('إكزامبلول') and rules['documents'][0]['valid_until'] == '2030-03-14'
    q = f['ocr_quality']
    assert q['corrected'] == 3 and q['changed'][0] == {'page': 1, 'was': '\\YPEO/Y-YO', 'now': '١٢٣٤٥/٢٠٢٥'}
    assert q['doubtful'] == [{'page': 1, 'text': '10/7/17'}] and q['weak'] == []
    assert 'SCANNED — read by OCR' in extract.ai_prompt(r['files'])
    extract._READ.clear(); extract.BROWSER.clear()                                      # kept on disk: a new session finds it
    assert extract.read_files([('again.pdf', data)])['files'][0]['reader'] == 'browser-ocr'


def test_a_reading_is_checked_before_it_is_kept(browser, tmp_path):
    extract.READ_DIR = tmp_path / 'text'
    sha = extract._sha(scan())
    for bad in [('x' * 64, ['t']), (sha, []), (sha, 'text'), (sha, [1, 2]), (sha, ['a'] * 201), (sha, ['a' * 400001])]:
        with pytest.raises(ValueError):
            extract.keep_browser_reading(bad[0], bad[1], REP, TAG)
    with pytest.raises(ValueError):                                                     # a page's numbers that are not numbers
        extract.keep_browser_reading(sha, ['ok'], {'quality': {'1': {'words': 'x'}}}, TAG)
    rec = extract.keep_browser_reading(sha, ['ok'], {'quality': {'1': {'words': 3, 'low': 0}, 'two': {}}, 'weak': ['1', 'a']}, 'ARA+eng<script>')
    assert rec['tag'] == 'ara+engscript' and rec['rep']['weak'] == [1] and list(rec['rep']['quality']) == [1]   # only what a reading holds


def test_the_page_asks_reads_and_the_engine_keeps_it_api(browser, tmp_path):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    data = scan(seed=1)
    chk = c.post('/api/ocr/check', files=[('file', ('scan.pdf', io.BytesIO(data), 'application/pdf'))]).json()
    assert chk == {'sha256': extract._sha(data), 'why': 'scan', 'here': False, 'read': 0, 'pages': 1}
    text = c.post('/api/ocr/check', files=[('file', ('spec.txt', io.BytesIO(b'Assay 98.0 %'), 'text/plain'))]).json()
    assert text['why'] is None                                                          # a file with text of its own is not read
    r = c.post('/api/ocr/browser', json={'sha256': chk['sha256'], 'texts': ['\n'.join(LINES)], 'rep': REP, 'tag': TAG})
    assert r.status_code == 200 and r.json() == {'kept': True, 'pages': 1, 'tag': TAG}
    assert c.post('/api/ocr/check', files=[('file', ('scan.pdf', io.BytesIO(data), 'application/pdf'))]).json()['read'] == 1
    f = c.post('/api/extract', files=[('files', ('scan.pdf', io.BytesIO(data), 'application/pdf'))]).json()['files'][0]
    assert f['ocr'] and f['reader'] == 'browser-ocr' and f['kind'] == 'licence' and f['ocr_quality']['corrected'] == 3
    bad = c.post('/api/ocr/browser', json={'sha256': 'nope', 'texts': ['x']})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-OCR-READING'


def test_a_stored_copy_keeps_the_reading_of_its_pages(browser, tmp_path):
    """A scanner's PDF 1.3 is stored with its version line set to 1.7 (other bytes the same): the page's reading goes with it, so
    the preparation stage reads the stored file without the page reading it again."""
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    data = scan(version=b'1.3', seed=2)
    c.post('/api/ocr/browser', json={'sha256': extract._sha(data), 'texts': ['\n'.join(LINES)], 'rep': REP, 'tag': TAG})
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                 apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')]),
                 product=dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain'),
                 envelope=dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol']))).json()['id']
    up = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('scan0002.pdf', io.BytesIO(data), 'application/pdf'))], data={'meta': '{}'})
    assert up.status_code == 201, up.text
    doc = up.json()[0]
    w = next(x for x in c.get(f'/api/dossiers/{did}/prepare').json()['waiting'] if x['id'] == doc['id'])
    assert w['reading']['reader'] == 'ocr' and w['reading']['chars'] > 300 and w['reading']['ocr_quality']['corrected'] == 3
    slot = w['auto'] or w['suggestions'][0]['slot_id']                                  # placed by what it says, not by its name
    r = c.post(f"/api/dossiers/{did}/prepare/{doc['id']}", json={'slot_id': slot, 'fix': False}).json()
    stored = c.get(f"/api/dossiers/{did}/documents/{r['document']['id']}/file").content
    assert stored.startswith(b'%PDF-1.7') and extract._sha(stored) != extract._sha(data)     # only the version line changed …
    assert r['steps'][:2] == ['placed', 'read_ocr'] and r['reading']['chars'] > 300            # … and its reading went with it


def test_where_the_engine_reads_scans_itself_the_pages_reading_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(pdfcraft, 'ocr_info', lambda: {'language': 'ar+en', 'arabic': True})
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    r = c.post('/api/ocr/browser', json={'sha256': extract._sha(scan()), 'texts': ['x'], 'rep': REP, 'tag': TAG})
    assert r.status_code == 409 and r.json()['detail']['code'] == 'E-OCR-HERE'


LAYOUT = [{'words': [['رقم', 400, 80, 30, 20, 0], ['التسجيل:', 330, 80, 60, 20, 0], ['34567/2025', 240, 80, 80, 20, 0]], 'rotated': 0, 'deskew': 0}]


def test_in_the_browser_a_scan_is_made_searchable_from_the_pages_reading(browser, tmp_path, monkeypatch):
    """«Make searchable» in the browser edition: the page's reading, each word at its place, written invisibly under the image — on a
    third party's document too, proved unchanged by the file's structure (no page can be drawn there to compare)."""
    from io import BytesIO
    from pypdf import PdfReader
    from dossier_engine import fixes, textlayer
    monkeypatch.setattr(extract, 'reads_in_browser', lambda: True)
    extract.READ_DIR = tmp_path / 'text'
    data = scan(seed=3)
    path = tmp_path / 'scan.pdf'
    path.write_bytes(data)
    findings = [{'rule': 'NTA065-N4', 'action': 'auto_fix'}]
    r = fixes.apply(path, findings, 'third_party_certificate')
    assert r['data'] is None and 'not been read' in r['refused'][0]['en'] and r['refused'][0]['ar']      # not read yet: why, not a guess
    extract.keep_browser_reading(extract._sha(data), ['رقم التسجيل: 34567/2025'], REP, TAG, LAYOUT)
    r = fixes.apply(path, findings, 'third_party_certificate')
    assert [x['op'] for x in r['done']] == ['make_searchable'] and not r['refused'], r
    assert textlayer.invisible_only(data, r['data']) and '34567/2025' in PdfReader(BytesIO(r['data'])).pages[0].extract_text()
    if pdfcraft.available():
        assert pdfcraft.same_pixels(data, r['data'])
    assert 'NTA065-N4' not in {f.rule for f in r['report'].findings}


def test_a_scan_read_only_in_part_is_not_made_searchable(browser, tmp_path, monkeypatch):
    from PIL import Image
    from dossier_engine import fixes
    monkeypatch.setattr(extract, 'reads_in_browser', lambda: True)
    extract.READ_DIR = tmp_path / 'text'
    buf = io.BytesIO()
    Image.new('L', (850, 1100), 255).save(buf, 'PDF', resolution=100, save_all=True, append_images=[Image.new('L', (850, 1100), 200)])
    path = tmp_path / 'two.pdf'
    path.write_bytes(buf.getvalue())
    extract.keep_browser_reading(extract._sha(buf.getvalue()), ['رقم التسجيل: 34567/2025'], REP, TAG, LAYOUT)
    r = fixes.apply(path, [{'rule': 'NTA065-N4', 'action': 'auto_fix'}], 'eda_document')
    assert r['data'] is None and 'Only 1 of its 2 pages' in r['refused'][0]['en']


def test_the_page_learns_what_to_read_before_a_fix_api(browser, tmp_path, monkeypatch):
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    data = scan(seed=4)
    did = c.post('/api/dossiers', json=dict(name='Examplol', profile=dict(dossier_kind='generic', origin='local', licence='own', activity='new',
                 apis=[dict(name='Paracetamol', manufacturer='Example API Co.', option='CEP')]),
                 product=dict(name='Examplol 500 mg', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='pain'),
                 envelope=dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['paracetamol']))).json()['id']
    doc = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('scan0003.pdf', io.BytesIO(data), 'application/pdf'))], data={'meta': '{}'}).json()[0]
    info = c.get(f"/api/ocr/document/{did}/{doc['id']}").json()
    assert info == {'sha256': extract._sha(data), 'why': 'scan', 'here': False, 'pages': 1, 'read': 0, 'layout': False,
                    'filename': 'scan0003.pdf', 'url': f"/api/dossiers/{did}/documents/{doc['id']}/file"}
    assert c.post('/api/ocr/browser', json={'sha256': info['sha256'], 'texts': ['x y'], 'rep': REP, 'tag': TAG, 'layout': LAYOUT}).status_code == 200
    info = c.get(f"/api/ocr/document/{did}/{doc['id']}").json()
    assert info['read'] == 1 and info['layout']
    bad = c.post('/api/ocr/browser', json={'sha256': info['sha256'], 'texts': ['x'], 'layout': [{'words': [['w', 'x', 0, 1, 1]]}]})
    assert bad.status_code == 422                                                       # a place that is not numbers
    assert c.get(f"/api/ocr/document/nope/{doc['id']}").status_code == 404
