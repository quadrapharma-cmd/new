"""A made-up combined dossier for the combined-file program's tests (rule 7: no real company or product).

«Zentorix 10 mg tablets» of the made-up «Example Pharma Ltd.»: one PDF of 47 pages with top-level bookmarks — a drug substance
block (table of contents, a separator page, sections with CTD headings, a picture-only page), a drug product block (a page whose
printed number disagrees with its title), an annexure block of pictures, the same annexure block again (half the pages the same
bytes, half drawn again: «(reduced)»), Module 2, Module 1 — and the Module 1 as a Word file (RTF named «.doc»).
    python3 tests/combined_fixture.py <folder>"""
import io
import sys
from pathlib import Path

import pikepdf
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PRODUCT = 'Zentorix 10 mg film-coated tablets'
COMPANY = 'EXAMPLE PHARMA LTD.'
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'


def text_page(c, lines, header=True):
    y = 800
    if header:
        c.setFont('Helvetica', 8)
        c.drawString(40, y, COMPANY)
        y -= 12
        c.drawString(40, y, f'CTD - {PRODUCT}')
        y -= 24
    for i, l in enumerate(lines):
        c.setFont('Helvetica-Bold' if i == 0 else 'Helvetica', 12 if i == 0 else 10)
        c.drawString(50, y, l)
        y -= 16
    c.showPage()


def picture_page(c, words):
    """A page that is a picture only (a scan): words drawn into an image."""
    im = Image.new('L', (1240, 1754), 255)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 34)
    y = 120
    for w in words:
        d.text((110, y), w, font=f, fill=0)
        y += 60
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    buf.seek(0)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(buf), 0, 0, width=A4[0], height=A4[1])
    c.showPage()


def build(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    marks = []                                                  # (title, first page)
    # --- 1–12 drug substance «zentorine» (pages 1–2 its table of contents)
    marks.append(('Zentorine-Drug Substance', 1))
    text_page(c, ['TABLE OF CONTENTS', '3.2.S.1 General information ........ 3', '3.2.S.2 Manufacture ........ 5',
                  '3.2.S.4 Control of drug substance ........ 8', '3.2.S.7 Stability ........ 11'])
    text_page(c, ['TABLE OF CONTENTS (continued)', '3.2.S.7.3 Stability data ........ 12'])
    text_page(c, ['3.2.S.1.1 Nomenclature', 'INN: zentorine', 'Chemical name: 2-example-ethyl zentorate'])
    text_page(c, ['3.2.S.1.2 Structure', 'Molecular formula C12H14N2O2', 'Relative molecular mass 218.25'])
    text_page(c, ['3.2.S.2 MANUFACTURE ( Zentorine, Example Pharma Ltd. )', '3.2.S.2 Manufacture'])           # separator
    text_page(c, ['3.2.S.2.1 Manufacturer(s)', 'Example Pharma Ltd., 12 Sample Road, Exampletown'])
    text_page(c, ['3.2.S.2.2 Description of Manufacturing Process and Process Controls', 'Step 1: synthesis of the zentorate.'])
    picture_page(c, ['Batch manufacturing flow chart', 'Reactor R-101 -> filter F-2 -> dryer D-3'])
    text_page(c, ['3.2.S.4.1 Specification', 'Assay 98.0 - 102.0 %', 'Water not more than 0.5 %'])
    text_page(c, ['3.2.S.4.4 Batch Analyses', 'Batches ZX001, ZX002, ZX003 comply.'])
    text_page(c, ['3.2.S.7.1 Stability Summary and Conclusions', 'Re-test period 36 months.'])
    text_page(c, ['3.2.S.7.3 Stability Data', 'Long-term 25 C / 60 % RH, 36 months.'])
    # --- 13–19 drug product
    marks.append(('Zentorix - Drug Product', 13))
    text_page(c, ['TABLE OF CONTENTS', '3.2.P.1 Description and composition ........ 14'])
    text_page(c, ['3.2.P.2.1 Description and Composition of the Drug Product', 'Each tablet contains zentorine 10 mg.',
                  'Magnesium stearate 1.25 mg'])
    text_page(c, ['3.2.P.3.1 Manufacturer(s)', 'Example Pharma Ltd.'])
    text_page(c, ['3.2.P.5.1 Specification(s)', 'Assay 95.0 - 105.0 %'])
    text_page(c, ['3.2.P.5.4 Batch Analyses', 'Batches T001, T002 comply.'])
    text_page(c, ['3.2.P.8.1 Stability Summary and Conclusion', 'Shelf life 24 months from the date of manufacture.'])
    text_page(c, ['3.2.P.8.3 Stability Data', '24 months long-term data.'])
    # --- 20–29 annexures (pictures)
    marks.append(('Annexures for Module III', 20))
    annex = [['Annexure 1 - Certificates of analysis', f'Certificate {i}', f'Material M-{i:02d} complies'] for i in range(1, 11)]
    for words in annex:
        picture_page(c, words)
    # --- 30–39 the same annexures again
    marks.append(('Annexures for Module III (reduced)', 30))
    for words in annex:
        picture_page(c, words)                                   # drawn again: other bytes, the same picture
    # --- 40–44 Module 2
    marks.append(('MODULE II', 40))
    text_page(c, ['MODULE 2', 'COMMON TECHNICAL DOCUMENT SUMMARIES'], header=False)
    text_page(c, ['2.2 CTD Introduction', f'{PRODUCT} contains zentorine 10 mg.', 'Magnesium stearate 1.25 mcg'])
    text_page(c, ['2.3 Quality Overall Summary', 'Introduction'])
    text_page(c, ['2.4 Nonclinical Overview', 'Not applicable: a known substance.'])
    text_page(c, ['2.5 Clinical Overview', 'Bioequivalence with the reference product.'])
    # --- 45–47 Module 1
    marks.append(('MODULE I', 45))
    text_page(c, ['Module 1', 'ADMINISTRATIVE INFORMATION'], header=False)
    text_page(c, ['1.3 PRODUCT INFORMATION', '1.3.1 SPC, Labelling & Package Leaflet', 'Each tablet contains zentorine 10 mg'])
    text_page(c, ['1.3.2 Mock-up', 'Carton of 30 tablets'])
    c.save()
    pdf = pikepdf.open(io.BytesIO(buf.getvalue()))
    # half the second annexure copy: the very same page bytes as the first copy
    for i in range(5):
        pdf.pages[29 + i] = pdf.pages[19 + i]
    with pdf.open_outline() as ol:
        for title, page in marks:
            ol.root.append(pikepdf.OutlineItem(title, page - 1))
    out = folder / 'Combined dossier.pdf'
    pdf.save(out)
    rtf = ('{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Arial;}}\\f0\\fs22 Module 1\\par ADMINISTRATIVE INFORMATION\\par '
           '1.3 PRODUCT INFORMATION\\par 1.3.1 SPC, Labelling & Package Leaflet\\par Each tablet contains zentorine 10 mg\\par '
           '1.3.2 Mock-up\\par Carton of 30 tablets\\par}')
    (folder / 'MODULE - I ZENTORIX.doc').write_text(rtf, encoding='ascii')
    return out


if __name__ == '__main__':
    print(build(sys.argv[1]))
