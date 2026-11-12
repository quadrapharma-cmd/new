"""Arabic documents in the intake: text normalisation, Arabic-Indic digits, lenient label matching, dosage-form names,
and OCR (tesseract ara+eng) for scans and images when the tools exist on the computer. Nothing here needs the network."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

AR_DIGITS = {ord(c): str(i) for i, c in enumerate('٠١٢٣٤٥٦٧٨٩')}
AR_DIGITS.update({ord(c): str(i) for i, c in enumerate('۰۱۲۳۴۵۶۷۸۹')})
BIDI = re.compile('[‎‏‪-‮⁦-⁩؜﻿]')
DIACRITICS = re.compile('[ً-ْٰـ]')
AR_RUN = re.compile('[٠-٩۰-۹][٠-٩۰-۹/\\-.:]*')
YEAR = re.compile(r'(19|20)\d\d')
ARABIC = re.compile('[؀-ۿ]')
IMAGE_MAGIC = ((b'\x89PNG', 'image/png'), (b'\xff\xd8', 'image/jpeg'), (b'GIF8', 'image/gif'), (b'RIFF', 'image/webp'), (b'II*\x00', 'image/tiff'), (b'MM\x00*', 'image/tiff'), (b'BM', 'image/bmp'))

# dosage forms as printed on Egyptian documents → the English form the rules already understand
FORMS_AR = [('أقراص مغلفة', 'film-coated tablet'), ('اقراص مغلفة', 'film-coated tablet'), ('أقراص فوارة', 'effervescent tablet'), ('أقراص للمضغ', 'chewable tablet'),
            ('أقراص ممتدة المفعول', 'prolonged-release tablet'), ('أقراص', 'tablet'), ('اقراص', 'tablet'), ('قرص', 'tablet'), ('كبسولات جيلاتينية رخوة', 'soft capsule'),
            ('كبسولات', 'hard capsule'), ('كبسول', 'hard capsule'), ('شراب', 'syrup'), ('معلق', 'oral suspension'), ('مستحلب', 'emulsion'), ('نقط للفم', 'oral drops'),
            ('قطرة للعين', 'eye drops'), ('قطرة عين', 'eye drops'), ('قطرة للأذن', 'ear drops'), ('قطرة', 'drops'), ('نقط', 'drops'), ('حقن', 'injection'), ('أمبول', 'injection'),
            ('امبول', 'injection'), ('فيال', 'injection'), ('محلول للحقن', 'solution for injection'), ('مسحوق للحقن', 'powder for injection'), ('محلول وريدي', 'infusion'),
            ('كريم', 'cream'), ('مرهم', 'ointment'), ('جل', 'gel'), ('لوشن', 'lotion'), ('بخاخ للأنف', 'nasal spray'), ('بخاخ', 'spray'), ('استنشاق', 'inhalation'),
            ('لبوس', 'suppository'), ('أكياس', 'sachet'), ('اكياس', 'sachet'), ('حبيبات', 'granules'), ('مسحوق', 'powder'), ('محلول', 'solution')]
STRENGTH_AR = re.compile(r'(\d+(?:[.,]\d+)?)\s?(مجم|ملجم|مللجم|ملليجرام|ملليغرام|ميكروجرام|ميكروغرام|جم|جرام|غرام|مل|وحدة دولية|وحدة|%)')
UNIT_AR = {'مجم': 'mg', 'ملجم': 'mg', 'مللجم': 'mg', 'ملليجرام': 'mg', 'ملليغرام': 'mg', 'ميكروجرام': 'mcg', 'ميكروغرام': 'mcg', 'جم': 'g', 'جرام': 'g', 'غرام': 'g',
           'مل': 'ml', 'وحدة دولية': 'IU', 'وحدة': 'IU', '%': '%'}


def _digits(run):
    conv = run.translate(AR_DIGITS)
    rev = conv[::-1]
    # pypdf often emits an Arabic-Indic run in visual order (reversed); keep the reading that makes a date or ends with a year
    if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', rev) and not re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', conv):
        return rev
    if YEAR.search(rev[-4:]) and not YEAR.search(conv[-4:]) and not YEAR.match(conv):
        return rev
    return conv


def prepare(text):
    """Normalised text: compatibility forms decomposed, bidi marks and diacritics removed, Arabic-Indic digits → ASCII."""
    if not text:
        return ''
    t = unicodedata.normalize('NFKC', text)
    t = BIDI.sub('', t)
    t = DIACRITICS.sub('', t)
    t = AR_RUN.sub(lambda m: _digits(m.group(0)), t)
    return t


def label_rx(label):
    """A label as a lenient regex: alef / yaa / taa-marbuta variants and flexible inner spaces."""
    out = []
    for ch in label:
        if ch in 'اأإآ':
            out.append('[اأإآ]')
        elif ch in 'يى':
            out.append('[يى]')
        elif ch in 'ةه':
            out.append('[ةه]')
        elif ch == ' ':
            out.append(r'\s+')
        else:
            out.append(re.escape(ch))
    return ''.join(out)


def has_arabic(text):
    return bool(ARABIC.search(text or ''))


def latin_in(text):
    """The Latin phrase on a line (e.g. the English name in parentheses after the Arabic one)."""
    m = re.search(r'\(([A-Za-z][A-Za-z0-9 .,\-/%]{2,80})\)', text or '')
    if m:
        return m.group(1).strip()
    m = re.search(r'([A-Z][A-Za-z]+(?:[ \-][A-Za-z0-9.%]+){0,8})', text or '')
    return m.group(1).strip() if m and len(m.group(1)) >= 3 else None


def form_en(text):
    low = (text or '').lower()
    for ar, en in FORMS_AR:
        if ar in low:
            return en
    return None


def strength_en(text):
    m = STRENGTH_AR.search(prepare(text or ''))
    if not m:
        return None
    return f"{m.group(1)} {UNIT_AR.get(m.group(2), m.group(2))}"


def image_type(data):
    for magic, mt in IMAGE_MAGIC:
        if data[:len(magic)] == magic:
            return mt
    return None


# ---------------- OCR (local tools only; never in the browser)
_LANGS = None


def ocr_available():
    return sys.platform != 'emscripten' and shutil.which('tesseract') is not None


def ocr_langs():
    global _LANGS
    if _LANGS is None:
        try:
            r = subprocess.run(['tesseract', '--list-langs'], capture_output=True, text=True, timeout=30)
            langs = set(re.findall(r'^\w+$', r.stdout + r.stderr, re.M))
        except Exception:
            langs = set()
        _LANGS = 'ara+eng' if 'ara' in langs and 'eng' in langs else 'ara' if 'ara' in langs else 'eng'
    return _LANGS


def ocr_image(path):
    try:
        r = subprocess.run(['tesseract', str(path), 'stdout', '-l', ocr_langs(), '--psm', '6'], capture_output=True, text=True, timeout=180)
        return r.stdout if r.returncode == 0 else ''
    except Exception:
        return ''


def ocr_image_bytes(data, suffix='.png'):
    if not ocr_available():
        return ''
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'img' + suffix)
        with open(p, 'wb') as f:
            f.write(data)
        return ocr_image(p)


def ocr_pdf(data, pages=4, dpi=200):
    """OCR of the first pages of an image-only PDF (pdftoppm → tesseract). '' when the tools are missing."""
    if not ocr_available() or not shutil.which('pdftoppm'):
        return ''
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, 'doc.pdf')
        with open(src, 'wb') as f:
            f.write(data)
        try:
            subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-f', '1', '-l', str(pages), src, os.path.join(d, 'p')], capture_output=True, timeout=180, check=True)
        except Exception:
            return ''
        out = []
        for name in sorted(x for x in os.listdir(d) if x.endswith('.png')):
            out.append(ocr_image(os.path.join(d, name)))
        return '\n\f\n'.join(out)
