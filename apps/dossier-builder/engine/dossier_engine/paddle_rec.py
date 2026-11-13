"""The second reader, for the words Tesseract is unsure of (the owner, 13/11/2026: «switch between them if one fails»).

Tesseract reads the page and places every word (PdfCraft writes the searchable layer from it). A run of words it read with low
confidence is cut out of the page image and read again here by PaddleOCR's Arabic recognition model (PP-OCRv5 mobile — it reads
Arabic, Arabic-Indic digits and Latin), run by onnxruntime; the more confident reading is kept. On a fictional registration notice
the number and the date written in Arabic-Indic digits («١٢٣٤٥/٢٠٢٥», «١٥/٠٣/٢٠٢٥»), which Tesseract reads as «1760/7» and
«10/7/17» with low confidence, come back right (docs/ctd/PDFCRAFT-INTEGRATION.md).

Licences: the model Apache-2.0 (PaddleOCR; ONNX conversion by RapidOCR, Apache-2.0), onnxruntime MIT, numpy BSD — nothing that asks
the program's own code to be shared. The right-to-left order is put back here (to_logical), not by a library under a share-alike
licence. Not in the browser edition (no onnxruntime there): available() is False and nothing changes.
"""
import os
import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]                    # apps/dossier-builder
MODEL = 'arabic_PP-OCRv5_rec_mobile.onnx'
SHA256 = 'c1192e632d0baa9146ae5b756a0e635e3dc63c1733737ebfd1629e87144e9295'
HEIGHT, MIN_WIDTH = 48, 320                                   # the model's input height; narrower pictures are padded, as PaddleOCR does
_S = {}


def model_path():
    """DOSSIER_PADDLE_REC, the desktop bundle's «paddle» folder, or vendor/paddle beside the program (tools/ocr/fetch.py)."""
    places = [os.environ.get('DOSSIER_PADDLE_REC')]
    base = getattr(sys, '_MEIPASS', None)
    if base:
        places.append(str(Path(base) / 'paddle' / MODEL))
    places.append(str(APP / 'vendor' / 'paddle' / MODEL))
    return next((p for p in places if p and os.path.isfile(p)), None)


def available():
    if sys.platform == 'emscripten' or os.environ.get('PADDLE_REC') == '0' or not model_path():
        return False
    try:
        import numpy, onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def _session():
    if 'sess' not in _S:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = so.inter_op_num_threads = 1   # one core, like Tesseract's readings: several at once share the processor
        so.log_severity_level = 3
        sess = ort.InferenceSession(model_path(), sess_options=so, providers=['CPUExecutionProvider'])
        chars = sess.get_modelmeta().custom_metadata_map.get('character', '').splitlines()
        _S['sess'], _S['chars'] = sess, ['\u0000'] + chars + [' ']   # index 0: the blank; the last: the space
    return _S['sess'], _S['chars']


def _rtl(c):
    o = ord(c)
    return 0x0590 <= o <= 0x08FF or 0xFB1D <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF


def _ltr(c):
    return c.isdigit() or ('a' <= c.lower() <= 'z') or c in '%°µ'


def to_logical(s):
    """The model reads left to right as the line is drawn: an Arabic word comes out reversed, a number in its own order. Back to
    reading order: the line reversed, then each run of digits and Latin letters (with the / . , : - between them) put back."""
    if not any(_rtl(c) for c in s):
        return s
    r, out, i = s[::-1], [], 0
    while i < len(r):
        if _ltr(r[i]):
            k = i
            while k < len(r) and (_ltr(r[k]) or (r[k] in '/.,:-+ ' and k + 1 < len(r) and _ltr(r[k + 1]))):
                k += 1
            out.append(r[i:k][::-1])
            i = k
        else:
            out.append(r[i])
            i += 1
    return ''.join(out)


def read(img):
    """One word or a few words, as a picture (PIL) → (text in reading order, confidence 0–1)."""
    import numpy as np
    from PIL import Image
    sess, chars = _session()
    im = img.convert('RGB')
    w = max(1, int(round(im.width * HEIGHT / max(1, im.height))))
    im = im.resize((w, HEIGHT), Image.BILINEAR)
    x = (np.asarray(im, dtype=np.float32)[:, :, ::-1] / 255.0 - 0.5) / 0.5      # BGR, as PaddleOCR reads images
    x = x.transpose(2, 0, 1)
    if w < MIN_WIDTH:
        x = np.concatenate([x, np.zeros((3, HEIGHT, MIN_WIDTH - w), dtype=np.float32)], axis=2)
    out = sess.run(None, {sess.get_inputs()[0].name: x[None]})[0][0]          # [steps, classes]: probabilities
    best, prob = out.argmax(-1), out.max(-1)
    text, conf, prev = [], [], 0
    for k, p in zip(best.tolist(), prob.tolist()):
        if k and k != prev and k < len(chars):
            text.append(chars[k])
            conf.append(p)
        prev = k
    return to_logical(''.join(text).strip()), (sum(conf) / len(conf) if conf else 0.0)


def spans(words, low=70.0):
    """Runs of neighbouring low-confidence words on one line (Tesseract cuts «١٢٣٤٥/٢٠٢٥» in two): [(first, last, box)], 1-based
    word positions, box [x0, y0, x1, y1] in the page's points."""
    out, cur = [], None
    for i, w in enumerate(words, 1):
        x, y, bw, bh = w.get('box') or (0, 0, 0, 0)
        if (w.get('confidence') or 0) >= low or not (w.get('text') or '').strip() or bw <= 0 or bh <= 0:
            cur = None
            continue
        box = [x, y, x + bw, y + bh]
        if cur and i == cur[1] + 1:
            b = cur[2]
            over = min(b[3], box[3]) - max(b[1], box[1])
            gap = max(box[0] - b[2], b[0] - box[2], 0)
            if over > 0.5 * min(b[3] - b[1], box[3] - box[1]) and gap < 2.0 * max(b[3] - b[1], box[3] - box[1]):
                cur[1], cur[2] = i, [min(b[0], box[0]), min(b[1], box[1]), max(b[2], box[2]), max(b[3], box[3])]
                continue
        cur = [i, i, box]
        out.append(cur)
    return [tuple(s) for s in out]


PADS = (0.15, 0.25, 0.35)                                     # margins around a run, as parts of its height
SHAPES = (re.compile(r'^\d{1,2}[/.\-]\d{1,2}[/.\-](\d{2}|\d{4})$'),   # a date: day/month/year (any digits: \d takes ٠–٩ too)
          re.compile(r'^\d+/\d{4}$'))                                  # a number of a year: 12345/2025, as EDA numbers its papers


def vote(readings, sure=0.8):
    """The reading most of the cuts agree on; at a tie, the more confident. A number the shape of a date or of «number/year»
    goes first when some cut reads it so with confidence: the «/» of a date in Arabic-Indic digits is easily read as «١» (one),
    and it is the cuts that keep the «/» that read it right. readings: [(text, confidence)] → (text, confidence)."""
    shaped = [(t, c) for t, c in readings if t and c >= sure and any(m.match(t) for m in SHAPES)]
    tally = {}
    for text, conf in shaped or readings:
        if text:
            n, c = tally.get(text, (0, 0.0))
            tally[text] = (n + 1, c + conf)
    if not tally:
        return '', 0.0
    text, (n, c) = max(tally.items(), key=lambda kv: (kv[1][0], kv[1][1] / kv[1][0]))
    return text, c / n


def second_reading(pages_png, words, low=70.0, sure=0.8):
    """Corrections for one page read as scanned: each run of low-confidence words read again from the page image, cut with three
    margins from each rendering (pages_png: {dpi: PNG}) — one pixel more or less can turn a «/» into a «١» — and the reading most
    of the cuts agree on taken; where it is sure (≥ sure) and different, the run's first word takes it and the others are emptied.
    → ([{'word', 'text'}], [{'tesseract', 'paddle', 'confidence', 'agree'}])."""
    from io import BytesIO
    from PIL import Image
    pages = [(Image.open(BytesIO(png)), dpi / 72.0) for dpi, png in sorted(pages_png.items())]
    fixes, seen = [], []
    for first, last, (x0, y0, x1, y1) in spans(words, low):
        h, readings = y1 - y0, []
        for page, k in pages:
            for m in PADS:
                crop = page.crop((max(0, int((x0 - m * h) * k)), max(0, int((y0 - m * h) * k)),
                                  min(page.width, int((x1 + m * h) * k)), min(page.height, int((y1 + m * h) * k))))
                if crop.width >= 4 and crop.height >= 4:
                    readings.append(read(crop))
        text, conf = vote(readings, sure)
        old = ' '.join(words[i - 1].get('text') or '' for i in range(first, last + 1))
        agree = sum(1 for t, _ in readings if t == text)
        seen.append({'tesseract': old, 'paddle': text, 'confidence': round(conf, 3), 'agree': f'{agree}/{len(readings)}'})
        if conf >= sure and text and text != old:
            fixes.append({'word': first, 'text': text})
            fixes += [{'word': i, 'text': ''} for i in range(first + 1, last + 1)]
    return fixes, seen
