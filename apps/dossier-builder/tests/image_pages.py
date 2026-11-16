"""Which page of a TIFF each page of the PDF made from it shows — both drawn small and grey, the nearest taken (the fixture's pages
differ ten times more from each other than a page does from its own PDF page). Needs PdfCraft (it draws the PDF) and Pillow (it opens
the TIFF's pages): `shows` raises ImportError without Pillow."""
import io

from dossier_engine import pdfcraft


def shows(pdf, tif):
    from PIL import Image, ImageChops, ImageSequence
    small = lambda im: im.convert('L').resize((120, 170))
    far = lambda a, b: sum(i * n for i, n in enumerate(ImageChops.difference(a, b).histogram()))
    pages = [small(f.copy()) for f in ImageSequence.Iterator(Image.open(io.BytesIO(tif)))]
    out = []
    for png in pdfcraft.render(pdf, dpi=60):
        d = [far(small(Image.open(io.BytesIO(png))), p) for p in pages]
        out.append(d.index(min(d)) + 1)
    return out
