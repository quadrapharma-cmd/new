"""Intake on Arabic EDA documents: a registration notification («إخطار تسجيل») as a text PDF is read; as a scan or a photo it is said
to have no text where PdfCraft does not read scans, and is read by OCR where it does. The fixture is made with python-docx + LibreOffice (skipped where
soffice is missing)."""
import io, shutil, subprocess
import pytest
from fastapi.testclient import TestClient
from dossier_engine import extract, arabic
from dossier_engine.app.api import create_app

LINES = ['هيئة الدواء المصرية', 'الإدارة المركزية للمستحضرات الصيدلية', 'إخطار تسجيل مستحضر صيدلي', 'رقم الإخطار: ١٢٣٤٥/٢٠٢٥', 'التاريخ: ١٥/٠٣/٢٠٢٥',
         'اسم المستحضر: إكزامبلول 500 مجم أقراص مغلفة (Examplol 500 mg film-coated tablets)', 'المادة الفعالة: باراسيتامول 500 مجم (Paracetamol)',
         'الشكل الصيدلي: أقراص مغلفة', 'الشركة المنتجة: شركة إكزامبل فارما للصناعات الدوائية - مدينة السادس من أكتوبر', 'صاحب الترخيص: شركة إكزامبل فارما ش.م.م',
         'رقم التسجيل: 34567/2025', 'مدة الصلاحية: 36 شهر', 'العبوة: شريط به 10 أقراص', 'سعر الجمهور: 45 جنيه', 'ساري حتى: 14/03/2030', 'المنتج محلي الصنع']


def test_arabic_digits_dates_labels_forms():
    assert arabic.prepare('رقم الإخطار: ٥٢٠٢/٥٤٣٢١ | التاريخ: ٥٢٠٢/٣٠/٥١') == 'رقم الإخطار: 12345/2025 | التاريخ: 15/03/2025'   # reversed runs from pypdf
    assert arabic.prepare('١٢٣٤٥/٢٠٢٥ · ١٥/٠٣/٢٠٢٥ · ٣٦ شهر') == '12345/2025 · 15/03/2025 · 36 شهر'                        # already in order
    assert arabic.prepare('‏مجم‎ ـــ') == 'مجم '
    assert extract.date_after('التاريخ: 15/03/2025', ['التاريخ']) == '2025-03-15'
    assert extract.date_after('صالحه حتى 2030/03/14', ['صالحة حتى']) == '2030-03-14'
    assert extract.after('اسم المستحضر: اكزامبلول', ['اسم المستحضر']) == 'اكزامبلول'            # alef without hamza still matches
    assert extract.after('(Paracetamol) المادة الفعالة', ['المادة الفعالة']) == '(Paracetamol)'  # value before the label (visual order)
    assert arabic.form_en('أقراص مغلفة') == 'film-coated tablet' and arabic.form_en('كبسولات') == 'hard capsule' and arabic.form_en('قطرة للعين') == 'eye drops'
    assert arabic.strength_en('إكزامبلول ٥٠٠ مجم') == '500 mg' and arabic.strength_en('كبسولات 250 ملجم') == '250 mg' and arabic.strength_en('أقراص') is None
    assert arabic.latin_in('إكزامبلول 500 مجم (Examplol 500 mg film-coated tablets)') == 'Examplol 500 mg film-coated tablets'
    assert extract.guess_kind('x.pdf', 'إخطار تسجيل مستحضر') == 'licence' and extract.guess_kind('x.pdf', 'شهادة تحليل') == 'coa'


@pytest.fixture(scope='module')
def notice_pdf(tmp_path_factory):
    if not shutil.which('soffice'):
        pytest.skip('LibreOffice not installed')
    import docx
    d = tmp_path_factory.mktemp('ar')
    doc = docx.Document()
    for line in LINES:
        p = doc.add_paragraph(line)
        p.alignment = 2
    doc.save(d / 'ekhtar.docx')
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', str(d), str(d / 'ekhtar.docx')], capture_output=True, timeout=240)
    p = d / 'ekhtar.pdf'
    if not p.exists():
        pytest.skip('LibreOffice could not convert')
    return p


def test_arabic_registration_notice_text_pdf(notice_pdf):
    r = extract.read_files([('ekhtar.pdf', notice_pdf.read_bytes())])
    f, meta = r['rules'], r['files'][0]
    assert meta['arabic'] and not meta['scanned'] and meta['kind'] == 'licence' and meta['file'] == 'pdf'
    assert f['product']['name'].startswith('إكزامبلول') and f['product']['name_en'] == 'Examplol 500 mg film-coated tablets'
    assert f['product']['dosage_form_en'] == 'film-coated tablet' and f['product']['strength'] == '500 mg'
    assert f['product']['manufacturer'].startswith('شركة إكزامبل فارما') and f['envelope']['applicant'] == 'شركة إكزامبل فارما ش.م.م'
    assert f['apis'][0]['name'] == 'Paracetamol'
    assert f['profile']['origin'] == 'local' and f['profile']['admin_route'] == 'oral' and 'coated' in f['profile']['dosage_specifics']
    assert f['registration'] == {'reg_no': '34567/2025', 'reg_date': '2025-03-15', 'shelf_life': '36 شهر', 'price': '45 جنيه', 'packs': ['شريط به 10 أقراص']}
    d = f['documents'][0]
    assert d['kind'] == 'licence' and d['issuer'] == 'هيئة الدواء المصرية' and d['issued'] == '2025-03-15' and d['valid_until'] == '2030-03-14'
    assert 'إخطار تسجيل' in extract.ai_prompt(r['files'])


@pytest.fixture(scope='module')
def notice_scan(notice_pdf, tmp_path_factory):
    if not shutil.which('pdftoppm'):
        pytest.skip('pdftoppm not installed')
    PIL = pytest.importorskip('PIL.Image')
    d = tmp_path_factory.mktemp('scan')
    subprocess.run(['pdftoppm', '-r', '200', '-png', '-f', '1', '-l', '1', str(notice_pdf), str(d / 'p')], capture_output=True, timeout=120, check=True)
    png = next(d.glob('p*.png'))
    img = PIL.open(png).convert('RGB')
    img.save(d / 'scan.pdf', 'PDF', resolution=200.0)
    return d / 'scan.pdf', png


def test_a_scanned_notice_is_read_by_ocr_where_pdfcraft_reads_scans(notice_scan):
    """The scan of the Arabic registration notice: PdfCraft reads it (Tesseract, Arabic and English) and the rules take its
    information as from the PDF itself; where it cannot (the browser edition) the file is said to have no text."""
    from dossier_engine import pdfcraft
    scan_pdf, png = notice_scan
    r = extract.read_files([('scan.pdf', scan_pdf.read_bytes()), ('photo.png', png.read_bytes())])
    a, b = r['files']
    assert a['scanned'] and a['file'] == 'pdf' and b['scanned'] and b['file'] == 'image' and b['pages'] == 1
    assert extract.has_text('scan.pdf', scan_pdf.read_bytes()) == 'scan' and extract.has_text('photo.png', png.read_bytes()) == 'image'
    if pdfcraft.ocr_info() and pdfcraft.ocr_info()['arabic']:
        assert a['ocr'] and b['ocr'] and a['chars'] > 200 and a['arabic']
        f = r['rules']
        assert f['product']['name'].startswith('إكزامبلول') and f['registration']['reg_no'] == '34567/2025'
        assert f['documents'][0]['kind'] == 'licence' and f['documents'][0]['valid_until'] == '2030-03-14'
        assert f['registration']['shelf_life'] == '36 شهر' and f['registration']['price'] == '45 جنيه'
        # Tesseract misreads Arabic-Indic digits («١٥/٠٣/٢٠٢٥») with both its «fast» and its «best» models (measured 13/11/2026);
        # the second reader (PaddleOCR's Arabic model, paddle_rec) reads them, and the notice's own date is then taken from the scan
        from dossier_engine import paddle_rec
        if paddle_rec.available():
            assert f['registration']['reg_date'] == '2025-03-15'
        assert 'SCANNED — read by OCR' in extract.ai_prompt(r['files'])
    else:
        assert a['chars'] == 0 and b['chars'] == 0 and 'ocr' not in a and r['rules']['product'] == {}      # nothing is guessed from pictures
        assert 'SCANNED — no text layer' in extract.ai_prompt(r['files'])


def test_extract_endpoint_accepts_images_and_reports_what_was_read(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    png = (b'\x89PNG\r\n\x1a\n' + b'\x00' * 64)                       # not a readable image: reported, never crashes
    r = c.post('/api/extract', files=[('files', ('IMG_0001.png', io.BytesIO(png), 'image/png'))])
    assert r.status_code == 200, r.text
    f = r.json()['files'][0]
    assert f['file'] == 'image' and f['scanned'] and f['pages'] == 1 and f['chars'] == 0 and 'ocr' not in f
