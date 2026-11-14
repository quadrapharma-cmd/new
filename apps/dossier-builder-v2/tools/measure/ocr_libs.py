"""The open-source OCR programs the owner listed on 13/11/2026 (PaddleOCR, Surya, EasyOCR, RapidOCR, docTR, Tesseract), each read
with its own whole pipeline — its own text finder and its own reader — on the made-up scanned pages (tools/measure/pages.mjs):
  python3 tools/measure/ocr_libs.py <engine> [out.json]      engines: rapidocr, paddleocr, easyocr, doctr, surya
Writes {page file: {text, seconds}} (default .cache/measure/texts-<engine>.json); tools/measure/score-texts.mjs scores it with
the same facts as every other reader. The model is loaded once, before the clock starts; each page's seconds are its reading
alone, on all the machine's cores. Each program runs in a Python environment of its own (they are measured here, not shipped).
Lines are put together the same way for all: the program's boxes grouped by height, a line with Arabic read from the right.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / '.cache' / 'measure' / 'pages'
ARABIC = re.compile(r'[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
LATIN = re.compile(r'[A-Za-z]')


def lines_of(items):
    """[(x0, y0, x1, y1, text)] → the page's text, a line per line: boxes whose middles fall within one another's height are one
    line; a line with more Arabic than Latin letters is read from the right."""
    rows = []
    for it in sorted(items, key=lambda b: (b[1] + b[3]) / 2):
        mid = (it[1] + it[3]) / 2
        for row in rows:
            if row['y0'] <= mid <= row['y1']:
                row['items'].append(it)
                break
        else:
            rows.append({'y0': it[1], 'y1': it[3], 'items': [it]})
    out = []
    for row in rows:
        text = ' '.join(t for *_, t in row['items'])
        rtl = len(ARABIC.findall(text)) > len(LATIN.findall(text))
        out.append(' '.join(t for *_, t in sorted(row['items'], key=lambda b: b[0], reverse=rtl)))
    return '\n'.join(out)


def box(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def rapidocr():
    from rapidocr import RapidOCR, LangDet, LangRec, OCRVersion, ModelType
    # PaddleOCR's own models (PP-OCRv5: its text finder and its Arabic reader, which also reads Latin letters and digits)
    engine = RapidOCR(params={'Global.log_level': 'error', 'Det.ocr_version': OCRVersion.PPOCRV5, 'Det.lang_type': LangDet.CH,
                              'Det.model_type': ModelType.MOBILE, 'Rec.ocr_version': OCRVersion.PPOCRV5,
                              'Rec.lang_type': LangRec.ARABIC, 'Rec.model_type': ModelType.MOBILE})
    def read(path):
        r = engine(str(path))
        if r.txts is None:
            return ''
        return lines_of([(*box(b), t) for b, t in zip(r.boxes, r.txts)])
    return read


def paddleocr():
    os.environ.setdefault('PADDLE_PDX_MODEL_SOURCE', 'huggingface')
    from paddleocr import PaddleOCR
    # PaddlePaddle 3.3's oneDNN path stops on these models on a processor («ConvertPirAttribute2RuntimeAttribute not support»): off.
    # Its default text finder works on the page at full size and asks for 20 GB here: the page's long side is held at 1,280.
    engine = PaddleOCR(lang='ar', use_doc_orientation_classify=True, use_doc_unwarping=False, use_textline_orientation=True,
                       enable_mkldnn=False, text_det_limit_type='max', text_det_limit_side_len=1280)
    def read(path):
        res = engine.predict(str(path))[0]
        return lines_of([(*box(p), t) for p, t in zip(res['rec_polys'], res['rec_texts'])])
    return read


def easyocr():
    import easyocr as e
    engine = e.Reader(['ar', 'en'], gpu=False, verbose=False)
    def read(path):
        return lines_of([(*box(b), t) for b, t, _ in engine.readtext(str(path))])
    return read


def doctr():
    # docTR's own models through OnnxTR (the same models as ONNX, by a docTR maintainer, Apache-2.0): docTR's model host
    # (doctr-static.mindee.com) is not reachable from here. Its pretrained reader knows the French alphabet, not Arabic.
    try:
        from onnxtr.io import DocumentFile
        from onnxtr.models import ocr_predictor
        engine = ocr_predictor(det_arch='fast_base', reco_arch='parseq', assume_straight_pages=False, detect_orientation=True)
    except ImportError:
        from doctr.io import DocumentFile
        from doctr.models import ocr_predictor
        engine = ocr_predictor(pretrained=True, assume_straight_pages=False, detect_orientation=True)
    def read(path):
        page = engine(DocumentFile.from_images(str(path))).export()['pages'][0]
        h, w = page['dimensions']
        items = []
        for b in page['blocks']:
            for line in b['lines']:
                for wd in line['words']:
                    g = wd['geometry']
                    pts = g if len(g) > 2 else [g[0], g[1]]
                    items.append((*box([(x * w, y * h) for x, y in pts]), wd['value']))
        return lines_of(items)
    return read


def surya():
    # Surya 0.24 (Apache-2.0 code) reads a page with its own vision-language model (datalab-to/surya-ocr-2.5, under Datalab's
    # modified OpenRAIL-M licence) served by llama.cpp's llama-server on this machine: LLAMA_CPP_BINARY,
    # SURYA_GGUF_LOCAL_MODEL_PATH and SURYA_GGUF_LOCAL_MMPROJ_PATH name them. Full-page mode: the layout and the text in one go,
    # the blocks in Surya's own reading order.
    import html as h
    from PIL import Image
    from surya.inference import SuryaInferenceManager
    from surya.recognition import RecognitionPredictor
    rec = RecognitionPredictor(SuryaInferenceManager())
    def plain(block):
        t = re.sub(r'</(td|th)>', ' ', block)
        t = re.sub(r'<br\s*/?>|</(p|tr|li|h[1-6]|div)>', '\n', t)
        return h.unescape(re.sub(r'<[^>]+>', '', t)).strip()
    def read(path):
        page = rec([Image.open(path).convert('RGB')], full_page=True)[0]
        return '\n'.join(plain(b.html) for b in sorted(page.blocks, key=lambda b: b.reading_order) if not b.skipped and b.html)
    return read


ENGINES = {'rapidocr': rapidocr, 'paddleocr': paddleocr, 'easyocr': easyocr, 'doctr': doctr, 'surya': surya}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ENGINES:
        sys.exit(f'python3 tools/measure/ocr_libs.py <{"|".join(ENGINES)}> [out.json]')
    name = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / '.cache' / 'measure' / f'texts-{name}.json'
    t0 = time.time()
    read = ENGINES[name]()
    print(f'{name}: loaded in {time.time() - t0:.1f} s', file=sys.stderr)
    texts = {}
    for f in sorted(PAGES.glob('*.png')):
        t = time.time()
        try:
            text, error = read(f), None
        except Exception as e:  # a page the program cannot read is a result, not the end of the measure
            text, error = '', f'{type(e).__name__}: {e}'[:300]
        texts[f.name] = {'text': text, 'seconds': round(time.time() - t, 1), **({'error': error} if error else {})}
        print(f'{name}: {f.name} {texts[f.name]["seconds"]} s{" " + error if error else ""}', file=sys.stderr)
    out.write_text(json.dumps(texts, ensure_ascii=False, indent=1), encoding='utf-8')
    print(out)
