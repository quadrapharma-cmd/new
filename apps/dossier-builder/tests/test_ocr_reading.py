"""The reading of scans (the owner, 13/11/2026: keep the document as it was; read it better; «switch between them if one fails»).
Tesseract reads each page as scanned with the accurate models; a page with many low-confidence words is read again straightened and
the better reading kept, page by page; the runs of words Tesseract is unsure of are read again by PaddleOCR's Arabic model (the
second reader) and its reading written where it is sure. The page always looks as it was. Fictional documents only."""
import io
import pytest
from dossier_engine import extract, paddle_rec, pdfcraft
from test_extract_arabic import notice_pdf                    # noqa: F401 — the fictional registration notice (python-docx + LibreOffice)

OCR = bool(pdfcraft.ocr_info())
BOTH = OCR and paddle_rec.available()
AR2EN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


# ---------------- the second reader's own rules (no model needed)
def test_a_right_to_left_reading_is_put_back_in_reading_order():
    assert paddle_rec.to_logical('إكزامبلول'[::-1]) == 'إكزامبلول'                            # drawn right to left, read left to right
    assert paddle_rec.to_logical('١٢٣٤٥/٢٠٢٥') == '١٢٣٤٥/٢٠٢٥'                             # a number keeps its own order
    assert paddle_rec.to_logical('Examplol 500 mg') == 'Examplol 500 mg'                       # no Arabic: as read
    assert paddle_rec.to_logical('٢٠٢٥/٠٣/١٥ خيراتلا') == 'التاريخ ٢٠٢٥/٠٣/١٥'             # the word turned, the date kept


def test_the_cuts_agree_and_a_date_keeps_its_slashes():
    assert paddle_rec.vote([('abc', 0.9), ('abd', 0.95), ('abc', 0.8)]) == ('abc', pytest.approx(0.85))      # most cuts agree
    got = paddle_rec.vote([('١٥١٠٣٢٠٢٥', 0.92), ('١٥١٠٣٢٠٢٥', 0.81), ('١٥/٠٣/٢٠٢٥', 0.86), ('١٥١٠٣٢٠٢٥', 0.91)])
    assert got[0] == '١٥/٠٣/٢٠٢٥'                                                           # the «/» read as «١» by most cuts
    assert paddle_rec.vote([('١٢٣٤٥/٢٠٢٥', 0.97), ('١٢٣٤٥٢٠٢٥', 0.9)])[0] == '١٢٣٤٥/٢٠٢٥'   # «number/year», as EDA numbers its papers
    assert paddle_rec.vote([('١٥/٠٣/٢٠٢٥', 0.5), ('١٥١٠٣٢٠٢٥', 0.9)])[0] == '١٥١٠٣٢٠٢٥'      # a shape read without confidence does not lead
    assert paddle_rec.vote([]) == ('', 0.0)


def test_low_confidence_words_side_by_side_on_a_line_are_read_together():
    w = lambda text, conf, x, y=100: {'text': text, 'confidence': conf, 'box': [x, y, 30, 12]}
    words = [w('رقم', 95, 500), w('vo', 0, 460), w('1760/7', 9.6, 420), w('التاريخ', 96, 500, 130), w('10/7/17', 0, 460, 130),
             w('ok', 92, 300, 130), w('x', 10, 100, 400)]
    got = paddle_rec.spans(words)
    assert [(a, b) for a, b, _ in got] == [(2, 3), (5, 5), (7, 7)]                      # Tesseract cut «١٢٣٤٥/٢٠٢٥» in two: one run
    assert got[0][2] == [420, 100, 490, 112]


# ---------------- the reading itself (Tesseract and the second reader on this machine)
def scan(pdf_bytes, dpi=200, angle=0, pages=1):
    from PIL import Image
    im = Image.open(io.BytesIO(pdfcraft.page_png(pdf_bytes, 1, dpi))).convert('L')
    imgs = [im.rotate(angle, expand=True, fillcolor=255) if (angle and i == pages - 1) else im for i in range(pages)]
    b = io.BytesIO()
    imgs[0].save(b, 'PDF', resolution=dpi, save_all=True, append_images=imgs[1:])
    return b.getvalue()


@pytest.mark.skipif(not BOTH, reason='needs PdfCraft with Tesseract and the second reader (tools/ocr/fetch.py)')
@pytest.mark.parametrize('dpi', [150, 200, 300])
def test_arabic_indic_numbers_misread_by_tesseract_are_put_right_by_the_second_reader(notice_pdf, dpi):
    s = scan(notice_pdf.read_bytes(), dpi)
    made, texts, rep = pdfcraft.ocr(s)
    layer = ''.join(' '.join(pdfcraft.page_texts(made)).split()).translate(AR2EN)
    assert '12345/2025' in layer and '15/03/2025' in layer, rep['quality']                 # the notice's number and date, in the file
    assert rep['second_reader'] >= 2 and rep['quality'][1]['read'] == 'as scanned'
    assert any(c['now'] == '١٢٣٤٥/٢٠٢٥' for c in rep['quality'][1]['second']['changed'])  # what was put right is said
    assert pdfcraft.same_pixels(s, made)                                                  # the page as it was
    f = extract.read_files([('scan.pdf', s)])
    assert f['rules']['registration']['reg_date'] == '2025-03-15'                         # the information taken from it
    assert f['files'][0]['ocr_quality']['corrected'] >= 2


@pytest.mark.skipif(not OCR, reason='needs PdfCraft with Tesseract')
def test_a_sideways_page_is_read_straightened_and_a_straight_one_as_scanned(notice_pdf):
    s = scan(notice_pdf.read_bytes(), 200, angle=90, pages=2)                             # page 1 straight, page 2 sideways
    made, texts, rep = pdfcraft.ocr(s)
    q = rep['quality']
    assert q[1]['read'] == 'as scanned' and q[2]['read'] == 'straightened', q
    assert '34567/2025' in texts[1] and 'إكزامبلول' in texts[1]                            # the sideways page read
    assert pdfcraft.same_pixels(s, made)


@pytest.mark.skipif(not OCR, reason='needs PdfCraft with Tesseract')
def test_a_blank_scan_is_left_as_it_was_and_said_to_be_hard_to_read():
    from PIL import Image
    b = io.BytesIO()
    Image.new('L', (1654, 2339), 255).save(b, 'PDF', resolution=200)
    made, texts, rep = pdfcraft.ocr(b.getvalue())
    assert made == b.getvalue() and not ''.join(texts).strip() and rep['weak'] == [1] and rep['words'] == 0


def test_the_models_are_the_programs_own_where_it_ships_them(monkeypatch, tmp_path):
    for name in ('ara.traineddata', 'eng.traineddata', 'configs/tsv'):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b'x')
    monkeypatch.setenv('DOSSIER_TESSDATA', str(tmp_path))
    monkeypatch.delenv('TESSDATA_PREFIX', raising=False)
    monkeypatch.setattr(pdfcraft, '_found', {})
    assert pdfcraft.tessdata() == str(tmp_path)
    assert pdfcraft._tess_env({})['TESSDATA_PREFIX'].rstrip('/\\') == str(tmp_path)        # Tesseract reads with them
    assert pdfcraft._tess_env({'TESSDATA_PREFIX': '/elsewhere/'})['TESSDATA_PREFIX'] == '/elsewhere/'   # unless told otherwise
    (tmp_path / 'configs' / 'tsv').unlink()
    monkeypatch.setattr(pdfcraft, '_found', {})
    assert pdfcraft.tessdata() != str(tmp_path)                                           # an incomplete folder is not used
