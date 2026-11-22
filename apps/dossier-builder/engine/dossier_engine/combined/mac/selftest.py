"""The shipped program's own check («eBOX --self-test»): every outside tool it carries runs, on a made-up page set — the page
reader and renderer (poppler), the OCR (OCRmyPDF, Tesseract with Arabic and English), LibreOffice with the program's font table,
Chromium with the program's fonts, the Claude library — and the first stages of the program on a made-up dossier. No network."""
import io
import shutil
import sys
import tempfile
from pathlib import Path

import pikepdf

from ..common import FONTS, Work, soffice_pdf, tool


def fonts_in(pdf):
    names = set()
    with pikepdf.open(pdf) as p:
        for page in p.pages:
            for f in (page.obj.Resources.get('/Font') or {}).values():
                names.add(str(f.get('/BaseFont', '')).split('+')[-1])
    return names


def made_up(folder):
    """Three pages: a text page, a picture page (a scan), a Module 2 page; and a Word file."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, 780, '3.2.P.1 Description and composition of the drug product')
    c.setFont('Helvetica', 10)
    c.drawString(50, 760, 'Each tablet contains 10 mg of examplamine.')
    c.showPage()
    im = Image.new('L', (1240, 1754), 255)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(FONTS / 'LiberationSans-Regular.ttf'), 40)
    for i, w in enumerate(['CERTIFICATE OF ANALYSIS', 'Batch EX-0042', 'Assay 99.8 %']):
        d.text((110, 140 + 70 * i), w, font=f, fill=0)
    b = io.BytesIO()
    im.save(b, 'PNG')
    b.seek(0)
    c.drawImage(ImageReader(b), 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, 780, '2.5 Clinical overview')
    c.showPage()
    c.save()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'Dossier.pdf').write_bytes(buf.getvalue())


def main():
    results = []

    def check(name, fn):
        try:
            note = fn()
            results.append((True, name, note or ''))
        except Exception as e:                                       # noqa: BLE001 — every failure is reported
            results.append((False, name, f'{type(e).__name__}: {e}'[:300]))

    tmp = Path(tempfile.mkdtemp(prefix='ebox-selftest-'))
    try:
        check('الأدوات', lambda: ' · '.join(Path(tool(t)).name for t in ('pdftoppm', 'pdftotext', 'tesseract', 'ocrmypdf', 'soffice')))

        def langs():
            import subprocess
            out = subprocess.run([tool('tesseract'), '--list-langs'], capture_output=True, text=True).stdout.split()
            if not {'ara', 'eng'} <= set(out):
                raise RuntimeError(f'لغات Tesseract: {out}')
            return 'ara, eng'
        check('لغات التعرف الضوئي', langs)

        def stages():
            from .. import assemble, ocr, read, repeats, split
            made_up(tmp / 'received')
            w = Work(tmp / 'work')
            read.run(tmp / 'received', w)
            repeats.run(w)
            ocr.run(w)
            text = w.pages_text('read/ocr.txt')
            if 'CERTIFICATE' not in text[1].upper():
                raise RuntimeError(f'لم تُقرأ صفحة الصورة: {text[1][:80]!r}')
            split.run(w)
            res = assemble.run(w)
            if res['wrong']:
                raise RuntimeError(f'صفحات لا تطابق أصلها: {res["wrong"]}')
            return f"{res['pages_checked']} صفحات مطابقة لأصلها، وقُرئت صفحة الصورة"
        check('مراحل البرنامج الأولى', stages)

        def libreoffice():
            from docx import Document
            doc = Document()
            run = doc.add_paragraph().add_run('Each tablet contains 10 mg.')
            run.font.name = 'Times New Roman'
            doc.save(tmp / 'pi.docx')
            pdf = soffice_pdf(tmp / 'pi.docx', tmp)
            f = fonts_in(pdf)
            if 'LiberationSerif' not in f:
                raise RuntimeError(f'الخطوط: {sorted(f)}')
            return 'Times New Roman → Liberation Serif'
        check('LibreOffice', libreoffice)

        def chromium():
            from ..fix import print_html
            html = tmp / 'ar.html'
            html.write_text('<html dir="rtl"><body style="font-family:\'Noto Naskh Arabic\'"><h1>النشرة الداخلية</h1>'
                            '<p>يحتوي كل قرص على 10 mg.</p></body></html>', encoding='utf-8')
            print_html(html, tmp / 'ar.pdf')
            f = fonts_in(tmp / 'ar.pdf')
            if not any(x.startswith('NotoNaskhArabic') for x in f):
                raise RuntimeError(f'الخطوط: {sorted(f)}')
            return ', '.join(sorted(f))
        check('Chromium والخط العربي', chromium)

        def claude():
            import anthropic
            anthropic.Anthropic(api_key='sk-ant-selftest-not-a-key')
            return f'anthropic {anthropic.__version__}'
        check('مكتبة Claude', claude)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for ok, name, note in results:
        print(('✓ ' if ok else '✗ ') + name + (f' — {note}' if note else ''), flush=True)
    bad = sum(1 for r in results if not r[0])
    print('الفحص الذاتي: ' + ('كل شيء يعمل.' if not bad else f'{bad} من {len(results)} لم تنجح.'), flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
