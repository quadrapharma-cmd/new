"""Word files, old (.doc, Word 97-2003) and new (.docx), are read from the inside like every other document: their kind comes
from what is written in them, they are accepted wherever a document is, and they are stored as Word drafts.
The fixtures are made-up documents of the product «Dermacure», written by python-docx and saved as .doc by LibreOffice."""
import io, json, pathlib, re, shutil, subprocess, zipfile
import pytest
from fastapi.testclient import TestClient
from dossier_engine import extract, msdoc
from dossier_engine.app.api import create_app
from test_reading_cases import PROFILE, PRODUCT, ENV

DATA = pathlib.Path(__file__).parent / 'data'
PROTOCOL = (DATA / 'dermacure-protocol.doc').read_bytes()
UNDERTAKING = (DATA / 'dermacure-undertaking.doc').read_bytes()


@pytest.fixture()
def dossier(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    return c, did


def test_an_old_word_file_is_read_with_its_tables_where_they_stand():
    assert msdoc.is_doc(PROTOCOL)
    lines = msdoc.doc_text(PROTOCOL).split('\n')
    assert lines[0] == 'Stability Study Protocol'
    assert 'Test | Specification | Method' in lines and 'Assay of Neomycin sulphate | 90.0% – 110.0% | Microbiological' in lines
    assert lines.index('Test | Specification | Method') < lines.index('Testing frequency: 0, 3, 6, 9, 12, 18, 24 months.')
    assert not re.search(r'[\x00-\x08\x0b-\x1f]', '\n'.join(lines))                     # none of Word's marks is left in the text


def test_arabic_and_latin_in_an_old_word_file():
    text = msdoc.doc_text(UNDERTAKING)
    assert text.startswith('إقرار') and 'نتعهد ببدء دراسة الثبات' in text
    assert 'اسم الشركة | إكزامبل فارم' in text and 'Trade name | Dermacure' in text


def test_word_marks_become_plain_text():
    assert msdoc._clean('See \x13 HYPERLINK "http://example.com" \x14the site\x15 now\r') == 'See the site now'     # a field shows its result
    assert msdoc._clean('No \x13 PAGE \x15 here') == 'No here'                                                      # a field with no result shows nothing
    assert msdoc._clean('a\x07b\x07\x07c\x07d\x07\x07') == 'a | b\nc | d'                                           # cells and rows
    assert msdoc._clean('one\x0btwo\x0cthree\x1efour') == 'one\ntwo\nthree-four'


@pytest.mark.parametrize('name', ['protocol.doc', 'pricing certificate.doc', 'scan0001', 'renamed.pdf.docx'])
def test_the_kind_of_a_word_file_comes_from_inside_it_whatever_it_is_called(name):
    f = extract.read_files([(name, PROTOCOL)])['files'][0]
    assert f['kind'] == 'stability' and f['file'] == 'docx' and not f['scanned'] and f['chars'] > 200


def test_a_docx_is_word_by_its_content_not_by_its_extension(tmp_path):
    import docx
    d = docx.Document(); d.add_paragraph('Pricing Certificate'); d.add_paragraph('Trade name: Dermacure 500 mg tablets'); d.add_paragraph('Public price: 45.00 EGP')
    d.save(tmp_path / 'x.docx'); data = (tmp_path / 'x.docx').read_bytes()
    assert extract.word_kind(data) == 'docx' and extract.word_kind(PROTOCOL) == 'doc'
    f = extract.read_files([('document from drive', data)])['files'][0]                 # a Drive title with no extension
    assert f['kind'] == 'pricing' and f['file'] == 'docx'
    other = io.BytesIO()
    with zipfile.ZipFile(other, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook/>')
    assert extract.word_kind(other.getvalue()) is None                                   # a zip that is not a Word document
    assert extract.word_kind(b'%PDF-1.4 minimal') is None


def test_what_cannot_be_read_gives_nothing_never_an_error():
    assert msdoc.doc_text(b'') == '' and msdoc.doc_text(msdoc.MAGIC + b'\x00' * 3000) == '' and not msdoc.is_doc(msdoc.MAGIC + b'\x00' * 3000)
    assert msdoc.doc_text(PROTOCOL[:4000]) == ''                                         # a file cut short
    broken = bytearray(PROTOCOL); broken[0x200 + 0x0B] |= 0x01                           # (not the FIB itself: a flipped byte elsewhere still reads or gives '')
    assert isinstance(msdoc.doc_text(bytes(broken)), str)


def test_an_old_word_file_is_stored_as_a_word_draft_and_judged_by_its_content(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pricing.doc', PROTOCOL, 'application/msword')})
    assert r.status_code == 201, r.text
    rules = {f['rule']: f for f in r.json()['findings']}
    assert rules['DOC-KIND']['severity'] == 'block'                                      # a stability protocol in the pricing item: refused by its content
    assert 'DOCX-DRAFT' in rules                                                         # and a Word draft: the PDF replaces it
    r = c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('whatever.doc', PROTOCOL, 'application/msword')})
    assert r.status_code == 201, r.text
    assert [f['rule'] for f in r.json()['findings']] == ['DOCX-DRAFT']                   # in the stability item it is accepted
    got = c.get(f"/api/dossiers/{did}/documents/{r.json()['id']}/file")
    assert got.status_code == 200 and got.headers['content-type'].startswith('application/msword') and got.content == PROTOCOL


def test_bulk_placement_offers_a_word_file_its_home_by_content(dossier):
    c, did = dossier
    r = c.post(f'/api/dossiers/{did}/classify', files=[('files', ('scan0001.doc', PROTOCOL, 'application/msword'))]).json()[0]
    assert r['kind'] == 'stability' and r['suggestions'] and r['suggestions'][0]['slot_id'].startswith(('P-16', 'S-14', 'M1-34'))


def test_the_review_reads_an_old_word_file(dossier):
    from dossier_engine.review import evidence
    assert evidence._docx_pages(UNDERTAKING)[0][1].startswith('إقرار')


@pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice is not installed')
def test_an_old_word_file_becomes_docx_for_tracked_changes():
    from dossier_engine.generate.docx_kit import to_docx
    out = to_docx(UNDERTAKING)
    assert extract.word_kind(out) == 'docx' and 'Dermacure' in extract.docx_text(out)
