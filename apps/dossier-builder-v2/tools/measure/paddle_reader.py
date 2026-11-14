"""PaddleOCR's Arabic recognition model (PP-OCRv5 mobile, Apache-2.0; its ONNX by RapidOCR, Apache-2.0) as a reader for the
measure (tools/measure/readers.mjs), the way the old program used it (apps/dossier-builder/engine/dossier_engine/paddle_rec.py):
  python3 -I tools/measure/paddle_reader.py lines <page.png>    every line with Arabic read by PaddleOCR, its numbers and dates
                                                                read again on their own; a line with none, Tesseract's reading
  python3 -I tools/measure/paddle_reader.py second <page.png>   Tesseract's reading, its unsure words read again by PaddleOCR
The model reads one line (or a few words) at a time; it does not find them. Tesseract («best» models, vendor/ocr/tessdata) finds
the lines and words, after the page is turned upright (Tesseract's orientation detection) and straightened (the angle at which
its rows of text are sharpest). Prints the text. Needs numpy, onnxruntime and Pillow, and the model from tools/ocr/fetch.mjs.
"""
import csv
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'vendor' / 'ocr' / 'paddle' / 'arabic_PP-OCRv5_rec_mobile.onnx'
BEST = ROOT / 'vendor' / 'ocr' / 'tessdata'
SYSTEM = Path('/usr/share/tesseract-ocr/5/tessdata')        # its orientation model (osd)
HEIGHT, MIN_WIDTH = 48, 320                                  # the model's input height; narrower pictures are padded, as PaddleOCR does
ONE = {**os.environ, 'OMP_THREAD_LIMIT': '1'}                # one core, like the Tesseract readers in the measure
_S = {}


def tesseract(img, *args):
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'page.png')
        img.save(f)
        return subprocess.run(['tesseract', f, 'stdout', *args], capture_output=True, text=True, env=ONE).stdout


def upright(img):
    """Turned upright by Tesseract's orientation detection; the turn is checked by asking again."""
    for _ in range(2):
        m = re.search(r'Rotate: (\d+)', tesseract(img, '--tessdata-dir', str(SYSTEM), '--psm', '0'))
        turn = int(m.group(1)) if m else 0
        if not turn:
            return img
        img = img.rotate(-turn, expand=True, fillcolor='white')     # Tesseract's «Rotate» is clockwise; PIL turns the other way
    return img


def straight(img):
    """Straightened: the small angle (±5°) at which the rows of ink are sharpest (the variance of the row sums is largest)."""
    g = img.convert('L')
    small = g.resize((800, max(1, round(800 * g.height / g.width))))
    ink = Image.fromarray(((np.asarray(small) < 128) * 255).astype(np.uint8))
    best, angle = -1.0, 0.0
    for a in np.arange(-5.0, 5.01, 0.25):
        rows = np.asarray(ink.rotate(float(a), fillcolor=0), dtype=np.float32).sum(axis=1)
        if rows.var() > best:
            best, angle = rows.var(), float(a)
    return img.rotate(angle, expand=False, fillcolor='white', resample=Image.BICUBIC) if angle else img


def layout(img):
    """Tesseract's words [{text, confidence, box, line}] and lines [{box}], boxes [x0, y0, x1, y1] in pixels, in reading order."""
    rows = csv.DictReader(io.StringIO(tesseract(img, '--tessdata-dir', str(BEST), '-l', 'ara+eng', '-c', 'tessedit_create_tsv=1')),
                          delimiter='\t', quoting=csv.QUOTE_NONE)
    words, lines = [], {}
    for r in rows:
        try:
            level, x, y, w, h = (int(r[k]) for k in ('level', 'left', 'top', 'width', 'height'))
        except (TypeError, ValueError):
            continue
        key = (r['block_num'], r['par_num'], r['line_num'])
        if level == 4:
            lines[key] = {'box': [x, y, x + w, y + h]}
        elif level == 5 and (r.get('text') or '').strip():
            words.append({'text': r['text'], 'confidence': float(r['conf']), 'box': [x, y, x + w, y + h], 'line': key})
    return words, lines


def _session():
    if 'sess' not in _S:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = so.inter_op_num_threads = 1
        so.log_severity_level = 3
        sess = ort.InferenceSession(str(MODEL), sess_options=so, providers=['CPUExecutionProvider'])
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
    """One line or a few words, as a picture → (text in reading order, confidence 0–1)."""
    sess, chars = _session()
    im = img.convert('RGB')
    w = max(1, int(round(im.width * HEIGHT / max(1, im.height))))
    im = im.resize((w, HEIGHT), Image.BILINEAR)
    x = ((np.asarray(im, dtype=np.float32)[:, :, ::-1] / 255.0 - 0.5) / 0.5).transpose(2, 0, 1)   # BGR, as PaddleOCR reads
    if w < MIN_WIDTH:
        x = np.concatenate([x, np.zeros((3, HEIGHT, MIN_WIDTH - w), dtype=np.float32)], axis=2)
    out = sess.run(None, {sess.get_inputs()[0].name: x[None]})[0][0]
    best, prob = out.argmax(-1), out.max(-1)
    text, conf, prev = [], [], 0
    for k, p in zip(best.tolist(), prob.tolist()):
        if k and k != prev and k < len(chars):
            text.append(chars[k])
            conf.append(p)
        prev = k
    return to_logical(''.join(text).strip()), (sum(conf) / len(conf) if conf else 0.0)


def cut(img, box, margin):
    x0, y0, x1, y1 = box
    m = margin * (y1 - y0)
    return img.crop((max(0, int(x0 - m)), max(0, int(y0 - m)), min(img.width, int(x1 + m)), min(img.height, int(y1 + m))))


def spans(words, low=70.0):
    """Runs of neighbouring low-confidence words on one line: [(first, last, box)], 1-based word positions."""
    out, cur = [], None
    for i, w in enumerate(words, 1):
        if w['confidence'] >= low:
            cur = None
            continue
        box = list(w['box'])
        if cur and i == cur[1] + 1 and words[cur[1] - 1]['line'] == w['line']:
            b = cur[2]
            cur[1], cur[2] = i, [min(b[0], box[0]), min(b[1], box[1]), max(b[2], box[2]), max(b[3], box[3])]
            continue
        cur = [i, i, box]
        out.append(cur)
    return [tuple(s) for s in out]


PADS = (0.15, 0.25, 0.35)                                     # margins around a run, as parts of its height
SHAPES = (re.compile(r'^\d{1,2}[/.\-]\d{1,2}[/.\-](\d{2}|\d{4})$'),    # a date, day first or year first (\d takes ٠–٩ too)
          re.compile(r'^\d{4}[/.\-]\d{1,2}[/.\-]\d{1,2}$'),
          re.compile(r'^\d+/\d{4}$'))                                   # a number of a year: 12345/2025, as EDA numbers its papers


def vote(readings, sure=0.8):
    """The reading most of the cuts agree on (a date or a «number/year» read so with confidence first); at a tie the surer."""
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


def _held(run, found):
    it = iter(c for c in found if c.isdigit())
    return all(c in it for c in run)


NUM = re.compile(r'\d[\d/.\-]*\d')


def numbers(page, line, words, text):
    """The line's numbers read again on their own: its words that hold digits, side by side, cut out at the line's height with three
    side margins (Tesseract's box can miss a thin «١» at the edge), the number in each reading, and the one most cuts agree on taken
    when it is a date or a «number/year» read with confidence. It replaces the run of digits in the line's reading that it holds:
    reading a whole line, the model drops the «/» of «١٢٣٤٥/٢٠٢٥» and digits beside it."""
    groups, cur = [], None
    for w in words:
        if any(c.isdigit() for c in w['text']):
            if cur is None:
                cur = list(w['box'])
                groups.append(cur)
            else:
                cur[:] = [min(cur[0], w['box'][0]), min(cur[1], w['box'][1]), max(cur[2], w['box'][2]), max(cur[3], w['box'][3])]
        else:
            cur = None
    h = line[3] - line[1]
    for box in groups:
        readings = []
        for m in (0.3, 0.6, 0.9):
            t, c = read(page.crop((max(0, int(box[0] - m * h)), max(0, int(line[1] - 0.15 * h)),
                                   min(page.width, int(box[2] + m * h)), min(page.height, int(line[3] + 0.15 * h)))))
            found = NUM.findall(t)
            readings.append((max(found, key=len) if found else '', c))
        found, conf = vote(readings)
        if conf < 0.8 or not any(m.match(found) for m in SHAPES):
            continue
        for run in re.finditer(r'\d+', text):
            around = text[max(0, run.start() - 1):run.end() + 1]
            if len(run.group()) >= 4 and '/' not in around and _held(run.group(), found):
                text = text[:run.start()] + ' ' + found + ' ' + text[run.end():]
                break
    return text


def by_lines(words, texts):
    out, last = [], None
    for w, t in zip(words, texts):
        if not t:
            continue
        if w['line'] != last and out:
            out.append('\n')
        elif out:
            out.append(' ')
        out.append(t)
        last = w['line']
    return ''.join(out)


def main(mode, file):
    page = straight(upright(Image.open(file).convert('RGB')))
    words, lines = layout(page)
    if mode == 'lines':
        out = []
        for key, l in lines.items():
            mine = [w for w in words if w['line'] == key]
            text = read(cut(page, l['box'], 0.2))[0]
            # a line without Arabic: Tesseract's own reading (the Arabic model takes 0 for o in English and runs table cells together)
            out.append(' '.join(w['text'] for w in mine) if mine and not any(_rtl(c) for c in text) else numbers(page, l['box'], mine, text))
        return '\n'.join(out)
    texts = [w['text'] for w in words]
    for first, last, box in spans(words):
        text, conf = vote([read(cut(page, box, m)) for m in PADS])
        if conf >= 0.8 and text and text != ' '.join(texts[first - 1:last]):
            texts[first - 1] = text
            for i in range(first, last):
                texts[i] = ''
    return by_lines(words, texts)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('lines', 'second'):
        sys.exit('python3 -I tools/measure/paddle_reader.py lines|second <page.png>')
    print(main(sys.argv[1], sys.argv[2]))
