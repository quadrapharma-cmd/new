"""Minimal valid PDF 1.4 files for writer tests (one page: the label at the top, and a line of neutral filler at the foot — every
real document has text of its own, and the upload gate refuses a PDF with fewer than 20 characters of it). The text stays inside the
page, as on a real document: each line of the label on a line of its own, long lines wrapped (PdfCraft reads what is on the page)."""
import textwrap

FILLER = b'Lorem ipsum dolor sit amet, consectetur adipiscing elit.'      # names no kind of document


def make_pdf(path, label):
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
            b'/Resources << /Font << /F1 5 0 R >> >> >>',
            None,
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    lines = [w for ln in label.replace('(', '').replace(')', '').split('\n') for w in (textwrap.wrap(ln, 60) or [''])]
    first, rest = lines[0].encode('latin-1', 'replace'), [x.encode('latin-1', 'replace') for x in lines[1:]]
    stream = (b'BT /F1 14 Tf 72 770 Td (' + first + b') Tj ET\n'
              + (b'BT /F1 11 Tf 14 TL 72 748 Td ' + b' '.join(b'(' + x + b') Tj T*' for x in rest) + b' ET\n' if rest else b'')
              + b'BT /F1 8 Tf 72 40 Td (' + FILLER + b') Tj ET')
    objs[3] = b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream'
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    path.write_bytes(bytes(out))
    return path


def make_pdf_lines(path, lines, title='Document'):
    """A one-page PDF with several text lines (one text object per line, so pypdf keeps the line breaks)."""
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
            b'/Resources << /Font << /F1 5 0 R >> >> >>',
            None,
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    esc = lambda s: s.encode('cp1252', 'replace').replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')
    wrapped = [w for ln in [title] + list(lines) for w in (textwrap.wrap(ln, 90) or [''])]
    stream = b'BT /F1 11 Tf 14 TL 50 790 Td ' + b' '.join(b'(' + esc(ln) + b') Tj T*' for ln in wrapped) + b' ET'
    objs[3] = b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream'
    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    path.write_bytes(bytes(out))
    return path
