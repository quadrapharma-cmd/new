"""Every document format, old and new, is read from the inside: Excel (.xlsx, .xls), PowerPoint (.pptx, .ppt), OpenDocument, RTF,
HTML, text, the XML of Office 2003. A file is what its bytes say, whatever it is called; its kind comes from its text like any other
document's; in an item it is a source file that the PDF replaces. Fixtures: made-up «Dermacure» documents converted by LibreOffice."""
import gzip, io, json, pathlib, struct, zipfile
import pytest
from fastapi.testclient import TestClient
from dossier_engine import drive, extract, msdoc, officefiles as O
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV

FX = pathlib.Path(__file__).parent / 'data' / 'office'


def fx(name):
    data = (FX / (name + '.gz' if name == 'slides.ppt' else name)).read_bytes()
    return gzip.decompress(data) if name == 'slides.ppt' else data


LETTER = ['Pricing Certificate', 'شهادة تسعير مستحضر ديرماكيور', 'Trade name: Dermacure Topical Powder — “quoted” text, 30 °C ± 2 °C', 'Issued by the Egyptian Drug Authority']
LETTER_FULL = LETTER[:3] + ['Pack | 10 g bottle', 'سعر الجمهور | 45.00 EGP'] + LETTER[3:]          # the table where it stands in the letter
SHEET = ['Product | Dermacure Topical Powder', 'اسم المستحضر | ديرماكيور بودرة موضعية', 'Batch No. | DC-001', 'Manufacturing date | 2026-03-01',
         'Test | Specification | 0 months | 3 months | 6 months', 'Assay of Neomycin sulphate | 90.0% - 110.0% | 99.6 | 98.9 | 98.25',
         'Appearance | White powder | Complies | | Complies', 'Total viable count | NMT 100 cfu/g | 10 | 20 | 15']
SECOND_SHEET = ['Batch | Size (kg)', 'DC-001 | 150', 'DC-002 | 150.5', 'DC-003 | 1234567']
SLIDES = ['Dermacure Topical Powder', 'Product overview for registration', 'تركيب المستحضر: نيومايسين سلفات', 'Composition: Neomycin sulphate 3.5 mg per gram', 'Stability data',
          'Shelf life: 24 months at 30 C / 65% RH']


@pytest.mark.parametrize('name,what,lines', [
    ('letter.rtf', 'rtf', LETTER_FULL), ('letter.odt', 'odt', LETTER_FULL), ('letter.html', 'html', LETTER_FULL),
    ('letter2003.xml', 'text', LETTER_FULL), ('letter.txt', 'text', LETTER),
    ('sheet.xlsx', 'xlsx', SHEET + SECOND_SHEET), ('sheet.xls', 'xls', SHEET + SECOND_SHEET), ('sheet.ods', 'ods', SHEET + SECOND_SHEET),
    ('sheet2003.xml', 'text', SHEET + SECOND_SHEET), ('sheet.csv', 'text', SHEET), ('sheet.html', 'html', SHEET),
    ('slides.pptx', 'pptx', SLIDES), ('slides.ppt', 'ppt', SLIDES), ('slides.odp', 'odp', SLIDES)])
def test_every_format_gives_the_same_lines(name, what, lines):
    data = fx(name)
    assert O.sniff(name, data) == what
    got = O.text(what, data, name).split('\n')
    missing = [ln for ln in lines if ln not in got]
    assert not missing, (missing, got)
    assert [got.index(ln) for ln in lines] == sorted(got.index(ln) for ln in lines)          # in the document's own order


@pytest.mark.parametrize('name,called,kind', [('sheet.xls', 'pricing certificate.xls', 'stability'), ('sheet.xlsx', 'scan0001', 'stability'),
                                              ('letter.rtf', 'stability study.doc', 'pricing'), ('letter.odt', 'x.pdf.bin', 'pricing'), ('slides.ppt', 'pricing.ppt', 'stability')])
def test_the_kind_comes_from_inside_the_file_whatever_it_is_called(name, called, kind):
    f = extract.read_files([(called, fx(name))])['files'][0]
    assert f['kind'] == kind and not f['scanned'] and f['chars'] > 100, f


def test_a_file_is_what_its_bytes_say():
    assert O.sniff('report.pdf', fx('sheet.xls')) == 'xls' and O.sniff('a.doc', fx('slides.ppt')) == 'ppt' and O.sniff('a.txt', fx('letter.odt')) == 'odt'
    z = io.BytesIO()
    with zipfile.ZipFile(z, 'w') as f:
        f.writestr('photos/a.jpg', b'x')
    assert O.sniff('dossier.zip', z.getvalue()) == 'archive' and O.sniff('a.rar', b'Rar!\x1a\x07\x00rest') == 'archive'
    assert O.sniff('Thumbs.db', msdoc.MAGIC + b'\x00' * 2000) == 'other' and O.sniff('x.bin', bytes(range(256)) * 20) == 'other'
    assert O.sniff('notes', 'شهادة تسعير\nPricing'.encode('utf-16')) == 'text' and O.sniff('page', b'<!DOCTYPE html><html><body>x</body></html>') == 'html'
    assert O.sniff('photo.heic', b'\x00\x00\x00\x18ftypheic' + b'\x00' * 40) == 'image' and O.sniff('x.bmp', b'BM' + b'\x00' * 40) == 'image'
    assert extract.read_text('photo.heic', b'\x00\x00\x00\x18ftypheic' + b'\x00' * 40, ocr=False)['scanned']                 # an image the engine cannot open: unread, not an error
    assert extract.read_text('dossier.zip', z.getvalue())['text'] == '' and O.text('xls', b'not a workbook') == ''


def test_text_files_in_the_encodings_egyptian_offices_use():
    ar = 'شهادة تسعير مستحضر\nالسعر: 45 جنيه'
    for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'cp1256'):
        assert O.text('text', ar.encode(enc), 'a.txt') == ar, enc
    assert O.text('text', 'Café crème à 30 °C'.encode('cp1252'), 'a.txt') == 'Café crème à 30 °C'
    assert O.text('text', 'Test;Result\nAssay;99.6\n'.encode(), 'r.csv') == 'Test | Result\nAssay | 99.6'
    assert O.text('text', b'Test\tResult\nAssay\t99.6\n', 'r.tsv') == 'Test | Result\nAssay | 99.6'


def test_rtf_escapes_fonts_and_what_is_not_text():
    rtf = ("{@rtf1@ansi@ansicpg1252{@fonttbl{@f0@fcharset0 Arial;}{@f1@fcharset178 Simplified Arabic;}}{@info{@title Secret title}}"
           "{@*@generator Riched20;}@f1 @'d4@'e5@'c7@'cf@'c9@par @f0 caf@'e9 @u1587?@u1593@'3f {@pict@bin4 }{{}}{ x}@par a@cell b@cell@row @{ok@}@~@_@emdash@par}").replace('@', chr(92)).encode('latin-1')
    assert O.text('rtf', rtf).split('\n') == ['شهادة', 'café سع x', 'a | b', '{ok} -—']
    assert 'Secret' not in O.text('rtf', rtf) and 'Riched' not in O.text('rtf', rtf)


def test_html_tables_scripts_and_charset():
    html = '<html><head><meta charset="windows-1256"><title>t</title><style>p{}</style></head><body><h1>شهادة تحليل</h1><table><tr><td><p>Assay</p></td><td>99.6&nbsp;%</td></tr></table><script>var x="no";</script></body></html>'
    assert O.text('html', html.encode('cp1256')).split('\n') == ['شهادة تحليل', 'Assay | 99.6 %']


def rec(rt, body):
    return struct.pack('<HH', rt, len(body)) + body


def test_excel_95_strings_and_numbers():
    """BIFF5 (Excel 5/95): strings are bytes in the workbook's code page, there is no shared-string table."""
    name = 'تسعير'.encode('cp1256')
    globals_ = rec(0x0809, struct.pack('<HHHH', 0x0500, 0x0005, 0, 0)) + rec(0x0042, struct.pack('<H', 1256))
    sheet_at = len(globals_) + 4 + 7 + len(name) + 4
    wb = globals_ + rec(0x0085, struct.pack('<IBBB', sheet_at, 0, 0, len(name)) + name) + rec(0x000A, b'')
    label = 'سعر الجمهور'.encode('cp1256')
    wb += (rec(0x0809, struct.pack('<HHHH', 0x0500, 0x0010, 0, 0)) + rec(0x0204, struct.pack('<HHHH', 0, 0, 0, len(label)) + label)
           + rec(0x0203, struct.pack('<HHHd', 0, 1, 0, 45.5)) + rec(0x027E, struct.pack('<HHHI', 1, 0, 0, (1234 << 2) | 2)) + rec(0x027E, struct.pack('<HHHI', 1, 1, 0, (995 << 2) | 3))
           + rec(0x000A, b''))
    assert O.biff_text(wb).split('\n') == ['سعر الجمهور | 45.5', '1234 | 9.95']


def test_shared_strings_that_run_over_into_the_next_record():
    """BIFF8: a string split by a CONTINUE record goes on after a flags byte, and its characters may change width there."""
    first = struct.pack('<II', 2, 2) + struct.pack('<HB', 5, 0) + b'Der'            # «Dermacure…» starts as one byte a character
    cont = b'\x01' + 'ma'.encode('utf-16-le') + struct.pack('<HB', 3, 1) + 'سعر'.encode('utf-16-le')
    wb = (rec(0x0809, struct.pack('<HHHH', 0x0600, 0x0005, 0, 0)) + rec(0x00FC, first) + rec(0x003C, cont) + rec(0x000A, b'')
          + rec(0x0809, struct.pack('<HHHH', 0x0600, 0x0010, 0, 0)) + rec(0x00FD, struct.pack('<HHHI', 0, 0, 0, 0)) + rec(0x00FD, struct.pack('<HHHI', 0, 1, 0, 1)) + rec(0x000A, b''))
    assert O.biff_text(wb) == 'Derma | سعر'


def test_word_95_text_in_the_language_of_the_document():
    text = 'إقرار\rنقر نحن شركة إكزامبل فارم\r'.encode('cp1256')
    wd = bytearray(0x300)
    struct.pack_into('<HH', wd, 0, 0xA5DC, 104)
    struct.pack_into('<H', wd, 0x06, 0x0401)                                        # Arabic
    struct.pack_into('<II', wd, 0x18, 0x300, 0x300 + len(text))
    assert msdoc._word6(bytes(wd) + text, 0) == 'إقرار\nنقر نحن شركة إكزامبل فارم'
    assert msdoc._word6(bytes(wd) + text, 0x0004) == ''                             # a fast-saved file is not guessed at


@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, did


def test_an_excel_file_in_an_item_is_a_source_file_judged_by_its_content(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pricing.xls', fx('sheet.xls'), 'application/vnd.ms-excel')})
    assert r.status_code == 201, r.text
    rules = {f['rule']: f for f in r.json()['findings']}
    assert rules['DOC-KIND']['severity'] == 'block' and 'Excel' in rules['DOCX-DRAFT']['en']         # a stability sheet in the pricing item; and the PDF is what the dossier takes
    r = c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('summary sheet.xlsx', fx('sheet.xlsx'), 'application/octet-stream')})
    assert [f['rule'] for f in r.json()['findings']] == ['DOCX-DRAFT']
    got = c.get(f"/api/dossiers/{did}/documents/{r.json()['id']}/file")
    assert got.headers['content-type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') and got.content == fx('sheet.xlsx')
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('letter.rtf', fx('letter.rtf'), 'application/rtf')})
    assert [f['rule'] for f in r.json()['findings']] == ['DOCX-DRAFT'] and 'Word' in r.json()['findings'][0]['en']


def test_the_intake_and_bulk_placement_read_every_format(dossier):
    c, did = dossier
    r = c.post('/api/extract?target=dossier', files=[('files', ('slides.ppt', fx('slides.ppt'), 'application/vnd.ms-powerpoint')), ('files', ('letter', fx('letter.odt'), 'application/octet-stream'))]).json()
    assert [(f['file'], f['kind']) for f in r['files']] == [('ppt', 'stability'), ('odt', 'pricing')]
    r = c.post(f'/api/dossiers/{did}/classify', files=[('files', ('scan0001.xls', fx('sheet.xls'), 'application/vnd.ms-excel'))]).json()[0]
    assert r['kind'] == 'stability' and r['suggestions']


def test_the_drive_listing_offers_every_readable_type_and_no_system_file():
    usable = lambda name, mt='': drive.Drive._entry({'id': 'x', 'name': name, 'mimeType': mt})['usable']
    for name, mt in (('a.xls', 'application/vnd.ms-excel'), ('a.pptx', ''), ('a.ppt', 'application/vnd.ms-powerpoint'), ('a.rtf', 'application/rtf'), ('a.odt', ''), ('a.csv', 'text/csv'),
                     ('notes.txt', 'text/plain'), ('a.bmp', 'image/bmp'), ('a.doc', 'application/msword'), ('a.html', 'text/html')):
        assert usable(name, mt), name
    for name, mt in (('Thumbs.db', 'application/octet-stream'), ('~$report.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'), ('backup.rar', 'application/rar'),
                     ('film.mp4', 'video/mp4'), ('desktop.ini', 'text/plain')):
        assert not usable(name, mt), name
