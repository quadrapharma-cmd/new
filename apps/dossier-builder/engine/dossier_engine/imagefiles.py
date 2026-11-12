"""Images of every kind. An image is told by its bytes, whatever the file is called: JPEG (JFIF/Exif), PNG, GIF, BMP, TIFF (also
multi-page and BigTIFF), WebP, HEIC/HEIF (iPhone photos), AVIF, JPEG 2000, PNM, PSD, ICO. This module says what a file is, how
many pages a TIFF has, which way up a phone photo is, and hands the OCR engine a form it can open. It also wraps JPEG pages into a
PDF (the dossier takes PDF), with the standard library only."""
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

MIME = {'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'bmp': 'image/bmp', 'tiff': 'image/tiff', 'webp': 'image/webp', 'heic': 'image/heic',
        'avif': 'image/avif', 'jp2': 'image/jp2', 'pnm': 'image/x-portable-anymap', 'psd': 'image/vnd.adobe.photoshop', 'ico': 'image/x-icon',
        'pcx': 'image/x-pcx', 'tga': 'image/x-tga'}
EXT = {'jpeg': '.jpg', 'png': '.png', 'gif': '.gif', 'bmp': '.bmp', 'tiff': '.tif', 'webp': '.webp', 'heic': '.heic', 'avif': '.avif', 'jp2': '.jp2',
       'pnm': '.pnm', 'psd': '.psd', 'ico': '.ico', 'pcx': '.pcx', 'tga': '.tga'}
EXTENSIONS = ('.jpg', '.jpeg', '.jfif', '.jpe', '.png', '.gif', '.bmp', '.dib', '.tif', '.tiff', '.webp', '.heic', '.heif', '.avif', '.jp2', '.j2k', '.jpx', '.jpf',
              '.pbm', '.pgm', '.ppm', '.pnm', '.psd', '.ico', '.pcx', '.tga')
TESS_READS = {'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'jp2', 'pnm'}          # what tesseract opens by itself (leptonica)
HEIF_BRANDS = (b'heic', b'heix', b'hevc', b'hevx', b'heim', b'heis', b'mif1', b'msf1')


def image_format(data):
    """'jpeg' | 'png' | 'gif' | 'bmp' | 'tiff' | 'webp' | 'heic' | 'avif' | 'jp2' | 'pnm' | 'psd' | 'ico' | 'pcx' | 'tga' | None — by the bytes."""
    d = data or b''
    if d[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if d[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if d[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if d[:4] in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        return 'tiff'
    if d[:4] == b'RIFF' and d[8:12] == b'WEBP':
        return 'webp'
    if d[4:8] == b'ftyp' and len(d) >= 16:
        size = min(struct.unpack_from('>I', d, 0)[0], 256)
        brands = d[8:12] + d[16:max(16, size)]
        if b'avif' in brands or b'avis' in brands:
            return 'avif'
        if any(b in brands for b in HEIF_BRANDS):
            return 'heic'
    if d[:12] == b'\x00\x00\x00\x0cjP  \r\n\x87\n' or d[:4] == b'\xff\x4f\xff\x51':
        return 'jp2'
    if d[:2] == b'BM' and len(d) >= 30:                                   # two letters are not enough: the header has to make sense
        size, reserved, offset, dib = struct.unpack_from('<IIII', d, 2)
        if reserved == 0 and dib in (12, 40, 52, 56, 64, 108, 124) and 14 + dib <= offset <= len(d) and (size == 0 or abs(size - len(d)) <= 4096):
            return 'bmp'
    if d[:4] == b'8BPS' and d[4:6] in (b'\x00\x01', b'\x00\x02'):
        return 'psd'
    if d[:4] in (b'\x00\x00\x01\x00', b'\x00\x00\x02\x00') and len(d) >= 22:
        n = struct.unpack_from('<H', d, 4)[0]
        if 0 < n <= 64 and len(d) >= 6 + 16 * n:
            size, offset = struct.unpack_from('<II', d, 6 + 8)
            if 0 < size and 6 + 16 * n <= offset and offset + size <= len(d):
                return 'ico'
    if re.match(rb'P[1-6]\s+(?:#[^\n]*\n\s*)*\d{1,6}\s+\d{1,6}\s', d[:300]):
        return 'pnm'
    if len(d) >= 128 and d[0] == 0x0A and d[1] in (0, 2, 3, 4, 5) and d[2] == 1 and d[3] in (1, 2, 4, 8) and d[64] == 0 and d[65] in (1, 3, 4):
        x0, y0, x1, y1 = struct.unpack_from('<4H', d, 4)
        if x0 <= x1 and y0 <= y1:
            return 'pcx'
    if d[-18:] == b'TRUEVISION-XFILE.\x00' and len(d) > 44 and d[2] in (1, 2, 3, 9, 10, 11) and d[16] in (8, 15, 16, 24, 32):
        return 'tga'
    return None


def image_mime(data):
    return MIME.get(image_format(data))


def tiff_pages(data):
    """How many pages a TIFF holds (reduced-resolution copies of a page are not pages)."""
    try:
        order = '<' if data[:2] == b'II' else '>'
        big = struct.unpack_from(order + 'H', data, 2)[0] == 43
        pos = struct.unpack_from(order + ('Q' if big else 'I'), data, 8 if big else 4)[0]
        pages, seen = 0, set()
        while pos and pos not in seen and len(seen) < 3000:
            seen.add(pos)
            n = struct.unpack_from(order + ('Q' if big else 'H'), data, pos)[0]
            entry, first = (20, pos + 8) if big else (12, pos + 2)
            reduced = False
            for i in range(min(n, 400)):
                tag, typ = struct.unpack_from(order + 'HH', data, first + i * entry)
                if tag == 254:
                    v = struct.unpack_from(order + ('I' if typ == 4 else 'H'), data, first + i * entry + (12 if big else 8))[0]
                    reduced = bool(v & 1)
            pages += 0 if reduced else 1
            pos = struct.unpack_from(order + ('Q' if big else 'I'), data, first + n * entry)[0]
        return max(1, pages)
    except (struct.error, IndexError):
        return 1


def exif_orientation(data):
    """The EXIF orientation of a JPEG (1 = as stored, 3/6/8 = turned, 2/4/5/7 = mirrored); None when the file does not say."""
    try:
        if data[:2] != b'\xff\xd8':
            return None
        pos = 2
        while pos + 4 <= len(data) and pos < 262144:
            if data[pos] != 0xFF:
                return None
            marker, size = data[pos + 1], struct.unpack_from('>H', data, pos + 2)[0]
            if marker == 0xE1 and data[pos + 4:pos + 10] == b'Exif\x00\x00':
                t = pos + 10
                order = '<' if data[t:t + 2] == b'II' else '>'
                ifd = t + struct.unpack_from(order + 'I', data, t + 4)[0]
                for i in range(struct.unpack_from(order + 'H', data, ifd)[0]):
                    tag, typ, _count = struct.unpack_from(order + 'HHI', data, ifd + 2 + 12 * i)
                    if tag == 0x0112:
                        v = struct.unpack_from(order + 'H', data, ifd + 2 + 12 * i + 8)[0]
                        return v if 1 <= v <= 8 else None
                return None
            if marker in (0xDA, 0xD9):
                return None
            pos += 2 + size
    except (struct.error, IndexError):
        pass
    return None


def _run(cmd, dst):
    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
        with open(dst, 'rb') as f:
            out = f.read()
        return out if out[:8] == b'\x89PNG\r\n\x1a\n' else None
    except Exception:
        return None


def to_png(data):
    """The image as an upright PNG the OCR engine opens: Pillow when it is installed (with its HEIF plugin when that is), else the
    converter the machine has (sips on macOS, ImageMagick, heif-convert, ffmpeg). None when nothing here can open it."""
    fmt = image_format(data)
    if not fmt or sys.platform == 'emscripten':
        return None
    try:
        from PIL import Image, ImageOps
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except Exception:
            pass
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im) or im
        if im.mode in ('RGBA', 'LA', 'PA') or (im.mode == 'P' and 'transparency' in im.info):
            im = im.convert('RGBA')
            white = Image.new('RGB', im.size, 'white')
            white.paste(im, mask=im.split()[-1])
            im = white
        elif im.mode not in ('RGB', 'L'):
            im = im.convert('RGB')
        buf = io.BytesIO()
        im.save(buf, 'PNG')
        return buf.getvalue()
    except Exception:
        pass
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, 'in' + EXT[fmt]), os.path.join(d, 'out.png')
        with open(src, 'wb') as f:
            f.write(data)
        if sys.platform == 'darwin' and shutil.which('sips'):
            out = _run(['sips', '-s', 'format', 'png', src, '--out', dst], dst)
            if out:
                return out
        magick = shutil.which('magick') or (None if sys.platform == 'win32' else shutil.which('convert'))   # «convert» on Windows is another program
        if magick:
            coder = {'jpeg': 'jpeg', 'tiff': 'tiff', 'jp2': 'jp2'}.get(fmt, fmt)
            out = _run([magick, f'{coder}:{src}[0]', '-auto-orient', '-background', 'white', '-alpha', 'remove', f'png:{dst}'], dst)   # the coder is named: no guessing on an untrusted file
            if out:
                return out
        if fmt == 'heic' and shutil.which('heif-convert'):
            out = _run(['heif-convert', src, dst], dst)
            if out:
                return out
        if shutil.which('ffmpeg'):
            out = _run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-frames:v', '1', dst], dst)
            if out:
                return out
    return None


def for_model(data):
    """(media type, bytes) of the image in a form a vision model takes (JPEG, PNG, GIF, WebP), converting the others; None when it cannot be."""
    fmt = image_format(data)
    if fmt in ('jpeg', 'png', 'gif', 'webp'):
        return MIME[fmt], data
    png = to_png(data) if fmt else None
    return ('image/png', png) if png else None


# ---------------------------------------------------------------- JPEG pages → one PDF (the dossier takes PDF)
A4 = (595.276, 841.89)


def jpeg_info(data):
    """(width, height, components, dpi or None, Adobe marker) of a JPEG, from its frame header and its JFIF density."""
    if data[:2] != b'\xff\xd8':
        raise ValueError('not a JPEG')
    pos, dpi, adobe = 2, None, False
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        size = struct.unpack_from('>H', data, pos + 2)[0]
        if marker == 0xE0 and data[pos + 4:pos + 9] == b'JFIF\x00' and size >= 14:
            unit, xd, yd = struct.unpack_from('>BHH', data, pos + 11)
            if unit in (1, 2) and xd == yd and xd > 0:
                dpi = xd if unit == 1 else xd * 2.54
        if marker == 0xEE and data[pos + 4:pos + 9] == b'Adobe':
            adobe = True
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            _bits, h, w, comps = struct.unpack_from('>BHHB', data, pos + 4)
            if w and h and comps in (1, 3, 4):
                return w, h, comps, dpi, adobe
            raise ValueError('unusual JPEG frame')
        pos += 2 + size
    raise ValueError('no JPEG frame found')


def page_size(w, h, dpi=None):
    """The page of an image: its own size when it says a sensible resolution and fits A3, else fitted on A4 (upright or on its side)."""
    if dpi and 90 <= dpi <= 1200:
        pw, ph = w * 72.0 / dpi, h * 72.0 / dpi
        if max(pw, ph) <= 1200 and min(pw, ph) >= 100:
            return pw, ph, 0.0, 0.0, pw, ph
    pw, ph = A4 if h >= w else (A4[1], A4[0])
    scale = min(pw / w, ph / h)
    iw, ih = w * scale, h * scale
    return pw, ph, (pw - iw) / 2, (ph - ih) / 2, iw, ih


def jpegs_pdf(pages, title=None, rotate=None):
    """A PDF (1.4) with one page for each JPEG, the image stored as it is (no re-compression). `rotate` = degrees clockwise for
    each page (a phone photo its EXIF says is on its side is shown upright without touching its pixels)."""
    if not pages:
        raise ValueError('no pages')
    objs = []                                                             # object bodies; object n is objs[n - 1]

    def add(body):
        objs.append(body)
        return len(objs)

    catalog, tree = add(b''), add(b'')
    kids = []
    for k, jpg in enumerate(pages):
        w, h, comps, dpi, adobe = jpeg_info(jpg)
        turn = (rotate[k] if rotate and k < len(rotate) else 0) % 360
        space = {1: b'/DeviceGray', 3: b'/DeviceRGB', 4: b'/DeviceCMYK'}[comps]
        decode = b' /Decode [1 0 1 0 1 0 1 0]' if comps == 4 and adobe else b''      # Adobe CMYK JPEGs store inverted values
        img = add(b'<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter /DCTDecode%s /Length %d >>\nstream\n' % (
            w, h, space, decode, len(jpg)) + jpg + b'\nendstream')
        pw, ph, x, y, iw, ih = page_size(w, h, dpi)
        content = zlib.compress(b'q %.3f 0 0 %.3f %.3f %.3f cm /Im0 Do Q' % (iw, ih, x, y))
        stream = add(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(content) + content + b'\nendstream')
        kids.append(add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.3f %.3f]%s /Resources << /XObject << /Im0 %d 0 R >> >> /Contents %d 0 R >>' % (
            tree, pw, ph, b' /Rotate %d' % turn if turn in (90, 180, 270) else b'', img, stream)))
    objs[catalog - 1] = b'<< /Type /Catalog /Pages %d 0 R >>' % tree
    objs[tree - 1] = b'<< /Type /Pages /Count %d /Kids [%s] >>' % (len(kids), b' '.join(b'%d 0 R' % k for k in kids))
    info = add(b'<< /Producer (Dossier Builder) /Title %s >>' % _pdf_text(title or 'Scanned document'))
    out, offsets = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'), []
    for n, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % n + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offsets)
    out += b'trailer\n<< /Size %d /Root %d 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, catalog, info, xref)
    return bytes(out)


def _pdf_text(s):
    return b'<FEFF' + s.encode('utf-16-be').hex().upper().encode('ascii') + b'>'


def to_jpegs(data, max_pages=None):
    """The pages of an image as upright JPEGs (a TIFF page by page), through Pillow; None when it is not installed or cannot open the file."""
    if sys.platform == 'emscripten':
        return None
    try:
        from PIL import Image, ImageOps
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except Exception:
            pass
        im = Image.open(io.BytesIO(data))
        n = getattr(im, 'n_frames', 1) if image_format(data) == 'tiff' else 1
        out = []
        for i in range(n if max_pages is None else min(n, max_pages)):
            if n > 1:
                im.seek(i)
            fr = ImageOps.exif_transpose(im) or im
            if fr.mode in ('RGBA', 'LA', 'PA') or (fr.mode == 'P' and 'transparency' in fr.info):
                fr = fr.convert('RGBA')
                white = Image.new('RGB', fr.size, 'white')
                white.paste(fr, mask=fr.split()[-1])
                fr = white
            else:
                fr = fr.convert('L' if fr.mode in ('1', 'L', 'I', 'I;16', 'F') else 'RGB')
            dpi = im.info.get('dpi')
            ok = dpi and all(isinstance(v, (int, float)) or hasattr(v, '__float__') for v in dpi) and 90 <= float(dpi[0]) <= 1200 and abs(float(dpi[0]) - float(dpi[1])) < 1
            buf = io.BytesIO()
            fr.save(buf, 'JPEG', quality=90, **({'dpi': (round(float(dpi[0])), round(float(dpi[1])))} if ok else {}))
            out.append(buf.getvalue())
        return out or None
    except Exception:
        return None


def image_pdf(data, title=None):
    """An image as the PDF the dossier takes: a JPEG is wrapped as it is (turned the way its EXIF says, pixels untouched); any other
    kind goes through Pillow where it is installed. None when this machine cannot do it (the page then does it, before it uploads)."""
    fmt = image_format(data)
    try:
        if fmt == 'jpeg':
            return jpegs_pdf([data], title, rotate=[{3: 180, 6: 90, 8: 270}.get(exif_orientation(data), 0)])
        pages = to_jpegs(data) if fmt else None
        return jpegs_pdf(pages, title) if pages else None
    except Exception:
        return None
