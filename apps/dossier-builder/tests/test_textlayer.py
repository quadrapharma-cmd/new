"""The invisible text layer under a scanned page (textlayer: the browser edition's «make searchable»). Words written where they were
read, in text drawn invisibly after the page's own content: the page is the same (pixel for pixel where PdfCraft can draw it, and by
the file's structure everywhere), its text reads in reading order — Arabic as from a document a word processor made — and a layer that
would change the page is caught. Fictional files."""
import io
import pytest
from pypdf import PdfReader, PdfWriter
from dossier_engine import pdfcraft, textlayer

LINES = [['رقم', 'الإخطار:', '١٢٣٤٥/٢٠٢٥'], ['التاريخ:', '١٥/٠٣/٢٠٢٥'], ['Assay:', '95.0', '-', '105.0', 'per', 'cent']]


def scan(rotate=0):
    """A page that is an image only (lines of «ink» where the words are), at 100 dpi on a US Letter page; /Rotate as given."""
    from PIL import Image, ImageDraw
    im = Image.new('L', (850, 1100), 255)
    d = ImageDraw.Draw(im)
    for i in range(3):
        d.rectangle([150, 100 + 60 * i, 700, 130 + 60 * i], fill=0)
    buf = io.BytesIO()
    im.save(buf, 'PDF', resolution=100)
    if not rotate:
        return buf.getvalue()
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(buf.getvalue())))
    w.pages[0].rotate(rotate)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def layout(width=612):
    """The words as the page read them: points from the top left of the page as drawn, in reading order, line by line (an Arabic line
    right to left: its first word at the right)."""
    words = []
    for i, line in enumerate(LINES):
        y, rtl = 72 + 43.2 * i, i < 2
        x = width - 108 if rtl else 108
        for w in line:
            span = 9 * len(w)
            if rtl:
                x -= span
                words.append([w, x, y, span, 21.6, i])
                x -= 9
            else:
                words.append([w, x, y, span, 21.6, i])
                x += span + 9
    return {1: {'words': words, 'rotated': 0, 'deskew': 0.0}}


def test_the_words_go_under_the_page_and_read_in_order():
    data = scan()
    out = textlayer.write(data, layout())
    assert textlayer.invisible_only(data, out)
    if pdfcraft.available():
        assert pdfcraft.same_pixels(data, out)                                   # nothing drawn
        text = pdfcraft.page_texts(out)[0]
        assert 'رقم الإخطار: ١٢٣٤٥/٢٠٢٥' in ' '.join(text.split()) and 'التاريخ: ١٥/٠٣/٢٠٢٥' in ' '.join(text.split())
    plain = ' '.join(PdfReader(io.BytesIO(out)).pages[0].extract_text().split())
    assert 'Assay: 95.0 - 105.0 per cent' in plain and 'الإخطار' in plain and 'التاريخ' in plain   # as pypdf reads a word processor's PDF
    from dossier_engine import arabic
    assert '15/03/2025' in arabic.prepare(plain) and '12345/2025' in arabic.prepare(plain)


def test_a_turned_page_gets_its_words_where_they_are_seen():
    """A page stored sideways (/Rotate 90) is drawn upright for reading; its words go back to the page's own space."""
    data = scan(rotate=90)
    out = textlayer.write(data, layout(width=792))
    assert textlayer.invisible_only(data, out)
    if pdfcraft.available():
        assert pdfcraft.same_pixels(data, out)
        assert 'Assay: 95.0 - 105.0 per cent' in ' '.join(pdfcraft.page_texts(out)[0].split())
    page = PdfReader(io.BytesIO(out)).pages[0]
    import re
    tms = [list(map(float, m.group(1).split())) for m in re.finditer(rb'([-\d. ]+) Tm', page['/Contents'][-1].get_object().get_data())]
    assert tms and all(0 <= tm[4] <= 612 and 0 <= tm[5] <= 792 for tm in tms)          # on the page
    assert all(abs(tm[0]) < 1e-6 and tm[1] > 0 for tm in tms)                          # running up the stored page, as it is seen turned


def test_a_layer_that_would_change_the_page_is_caught():
    data = scan()
    out = textlayer.write(data, layout())
    assert not textlayer.invisible_only(data, out.replace(b'3 Tr', b'0 Tr', 1))         # text that is drawn
    s = out.split(b'BT', 1)
    assert not textlayer.invisible_only(data, s[0] + b'0 0 10 10 re f BT' + s[1])        # a drawing
    other = scan(rotate=0).replace(b'/ImageB', b'/ImageC', 1)
    assert not textlayer.invisible_only(other, out)                                     # not the same page underneath
    with pytest.raises(ValueError):
        textlayer.write(data, {1: {'words': [], 'rotated': 0, 'deskew': 0}})
