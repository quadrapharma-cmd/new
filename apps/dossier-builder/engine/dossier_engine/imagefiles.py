"""Images of every kind. An image is told by its bytes, whatever the file is called: JPEG (JFIF/Exif), PNG, GIF, BMP, TIFF (also
multi-page and BigTIFF), WebP, HEIC/HEIF (iPhone photos), AVIF, JPEG 2000, PNM, PSD, ICO. This module says what a file is, how
many pages a TIFF has, which way up a phone photo is, and turns one into PNG for a model that takes only the common kinds. An image
is not a document: the upload gate refuses it (no OCR, no wrapping into a PDF — NP.CAPP.065 v5 general note 4)."""
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

MIME = {'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'bmp': 'image/bmp', 'tiff': 'image/tiff', 'webp': 'image/webp', 'heic': 'image/heic',
        'avif': 'image/avif', 'jp2': 'image/jp2', 'pnm': 'image/x-portable-anymap', 'psd': 'image/vnd.adobe.photoshop', 'ico': 'image/x-icon',
        'pcx': 'image/x-pcx', 'tga': 'image/x-tga'}
EXT = {'jpeg': '.jpg', 'png': '.png', 'gif': '.gif', 'bmp': '.bmp', 'tiff': '.tif', 'webp': '.webp', 'heic': '.heic', 'avif': '.avif', 'jp2': '.jp2',
       'pnm': '.pnm', 'psd': '.psd', 'ico': '.ico', 'pcx': '.pcx', 'tga': '.tga'}
EXTENSIONS = ('.jpg', '.jpeg', '.jfif', '.jpe', '.png', '.gif', '.bmp', '.dib', '.tif', '.tiff', '.webp', '.heic', '.heif', '.avif', '.jp2', '.j2k', '.jpx', '.jpf',
              '.pbm', '.pgm', '.ppm', '.pnm', '.psd', '.ico', '.pcx', '.tga')
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
    """The image as an upright PNG (for a model that takes only the common kinds): Pillow when it is installed (with its HEIF plugin when that is), else the
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
