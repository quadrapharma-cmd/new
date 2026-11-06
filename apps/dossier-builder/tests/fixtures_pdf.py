"""Minimal valid PDF 1.4 files for writer tests (one page, text = label)."""


def make_pdf(path, label):
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
            b'/Resources << /Font << /F1 5 0 R >> >> >>',
            None,
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    text = label.replace('(', '').replace(')', '').encode('latin-1', 'replace')
    stream = b'BT /F1 14 Tf 72 770 Td (' + text + b') Tj ET'
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
