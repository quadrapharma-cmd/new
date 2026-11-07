"""Small python-docx toolkit with correct Arabic (RTL) paragraphs and runs."""
import shutil, subprocess, tempfile
from pathlib import Path
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor

AR_FONT = 'Arial'          # Word/LibreOffice substitute a font with Arabic glyphs if missing
DRAFT = 'DRAFT — unsigned · مسودة — غير موقّعة'


class MissingData(ValueError):
    def __init__(self, fields):
        self.fields = fields
        super().__init__('missing data: ' + ', '.join(fields))


def new_doc(landscape=False, letterhead=None, draft=True):
    d = Document()
    s = d.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    if landscape:
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = s.page_height, s.page_width
    for m in ('left_margin', 'right_margin'):
        setattr(s, m, Cm(2))
    s.top_margin, s.bottom_margin = Cm(2), Cm(1.8)
    st = d.styles['Normal']
    st.font.name, st.font.size = 'Arial', Pt(10.5)
    st.element.rPr.rFonts.set(qn('w:cs'), AR_FONT)
    hp = s.header.paragraphs[0]
    if letterhead:
        hp.text = letterhead
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if draft:
        p = s.header.add_paragraph()
        r = p.add_run(DRAFT)
        r.font.size, r.font.bold, r.font.color.rgb = Pt(9), True, RGBColor(0xB4, 0x23, 0x18)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return d


def _rtl(p):
    ppr = p._p.get_or_add_pPr()
    b = OxmlElement('w:bidi')
    ppr.append(b)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT


def _run_rtl(r):
    rpr = r._r.get_or_add_rPr()
    rtl = OxmlElement('w:rtl')
    rpr.append(rtl)
    r.font.name = AR_FONT
    rpr.rFonts.set(qn('w:cs'), AR_FONT)


def para(doc_or_cell, text, ar=False, bold=False, size=None, align=None, bullet=False):
    p = doc_or_cell.add_paragraph()
    if ar:
        _rtl(p)
    if bullet:
        text = ('\u200f● ' if ar else '● ') + text
    r = p.add_run(text)
    r.bold = bold
    if size:
        r.font.size = Pt(size)
        if ar:
            r._r.get_or_add_rPr().append(_szcs(size))
    if ar:
        _run_rtl(r)
    if align == 'center':
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def _szcs(size):
    e = OxmlElement('w:szCs')
    e.set(qn('w:val'), str(int(size * 2)))
    return e


def table(doc, header, rows, widths=None, ar=False):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = 'Table Grid'
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    if ar:
        tblpr = t._tbl.tblPr
        b = OxmlElement('w:bidiVisual')
        tblpr.append(b)
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ''
        para(c, str(h), ar=ar, bold=True)
        c.paragraphs[0]._p.getparent().remove(c.paragraphs[0]._p)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ''
            para(cells[i], '' if v is None else str(v), ar=ar and _has_ar(str(v)))
            cells[i].paragraphs[0]._p.getparent().remove(cells[i].paragraphs[0]._p)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    return t


def _has_ar(s):
    return any('؀' <= ch <= 'ۿ' for ch in s)


def require(data, keys):
    miss = [k for k in keys if data.get(k) in (None, '', [])]
    if miss:
        raise MissingData(miss)


def find_soffice():
    """LibreOffice on PATH, or in its standard place on macOS / Windows (desktop builds)."""
    import os, sys
    exe = shutil.which('soffice') or shutil.which('libreoffice')
    if exe:
        return exe
    cands = ['/Applications/LibreOffice.app/Contents/MacOS/soffice'] if sys.platform == 'darwin' else []
    if os.name == 'nt':
        for base in (os.environ.get('PROGRAMFILES', r'C:\Program Files'), os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')):
            cands.append(os.path.join(base, 'LibreOffice', 'program', 'soffice.exe'))
    return next((c for c in cands if os.path.exists(c)), None)


def to_pdf(docx_path, out_dir=None):
    """LibreOffice headless conversion (Arabic shaping by the layout engine)."""
    exe = find_soffice()
    if not exe:
        raise RuntimeError('LibreOffice not found — install it free from https://www.libreoffice.org/download/ '
                           '(لازم LibreOffice علشان الخطابات تتحول لـ PDF؛ نزّله مجانًا من libreoffice.org)')
    docx_path = Path(docx_path)
    out_dir = Path(out_dir or docx_path.parent)
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([exe, f'-env:UserInstallation={Path(prof).as_uri()}', '--headless', '--convert-to', 'pdf',
                        '--outdir', str(out_dir), str(docx_path)], check=True, capture_output=True, timeout=180)
    pdf = out_dir / (docx_path.stem + '.pdf')
    if not pdf.exists():
        raise RuntimeError(f'conversion failed for {docx_path}')
    return pdf
