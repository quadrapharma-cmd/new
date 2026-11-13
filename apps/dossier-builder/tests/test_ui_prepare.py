"""The preparation page in the browser (Playwright): files put in at once — a scan among them — are read (the scan by OCR), placed in
their items under the dossier's names, checked and fixed; what is still asked for is listed."""
import io
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.ocr_info(), reason='needs PdfCraft with Tesseract (Arabic and English)')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, page_of          # noqa: F401 — the shared server fixture

SPEC = ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white powder',
        'Assay: 95.0 - 105.0 per cent of the labelled amount', 'Microbial limits: TAMC not more than 100 cfu/g']
STAB = ['Stability summary and conclusion', '3.2.P.8.1 Stability summary', 'Three primary batches at 25 C / 60 % RH, 12 months',
        'Shelf life: 24 months, store below 30 C']


def test_files_are_read_placed_fixed_and_named(server, tmp_path):
    from PIL import Image
    did = dossier(server)
    spec = make_pdf_lines(tmp_path / 'spec.pdf', SPEC, 'Specification').read_bytes()
    png = pdfcraft.page_png(spec, 1, 200)
    scan = tmp_path / 'scan0001.pdf'
    Image.open(io.BytesIO(png)).convert('L').save(scan, 'PDF', resolution=200)                    # a scan: its pages are pictures
    stab = make_pdf_lines(tmp_path / 'stability.pdf', STAB, 'Stability')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server, 'ar')
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/prepare')
        page.wait_for_selector('#prepFiles', state='attached')
        assert 'Tesseract' in page.inner_text('#prepOcr')
        page.set_input_files('#prepFiles', [str(scan), str(stab)])
        page.wait_for_function("() => document.querySelectorAll('[data-pw]').length === 2", timeout=120000)
        assert 'اتقرى بالـ OCR' in page.inner_text('#prepOut')                                      # the scan was read by OCR
        page.click('#prepAll')
        page.wait_for_function("() => S.prep && S.prep.waiting.length === 0 && S.prep.placed.length >= 2", timeout=300000)
        out = page.inner_text('#prepOut')
        assert 'scan0001.pdf' in out and 'اسمه في الملف' in out
        r = page.evaluate('S.prep')
        spec_doc = next(d for d in r['placed'] if d['original_name'] == 'scan0001.pdf')
        assert spec_doc['ctd'].startswith('3.2.P.5') and not spec_doc['fixable'], spec_doc                # placed and made searchable
        assert all(not d['names'].get('ctd', '').endswith(d['original_name']) for d in r['placed'])  # named as the dossier names them
        assert r['requested']                                                                       # what is still asked for
        b.close()
    assert not errors, errors
