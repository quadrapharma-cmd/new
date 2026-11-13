"""The text-recognition models the program ships, fetched at fixed releases and checked against their SHA-256 (files already in
place are kept). Both under Apache-2.0: shipping them asks only for their licence beside them — nothing of the program is shared.

  vendor/tessdata  Tesseract's accurate («best») Arabic and English models, tessdata_best 4.1.0, with the one setting PdfCraft's
                   reading asks for (configs/tsv). On a fictional registration notice scanned at 200 dpi: 3.1 % of the characters
                   wrong instead of 14.7 % with the «fast» models a Tesseract installer brings.
  vendor/paddle    PaddleOCR's Arabic recognition model (PP-OCRv5 mobile, ONNX conversion of RapidOCR v3.10.0), the second reader
                   for the words Tesseract is unsure of: it reads the Arabic-Indic digits Tesseract misreads (engine/dossier_engine/
                   paddle_rec.py).

Usage: python tools/ocr/fetch.py [--out VENDOR_DIR]
"""
import argparse
import hashlib
import sys
import tempfile
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
TESS = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/4.1.0/'
SETS = {
    'tessdata': {
        'ara.traineddata': (TESS + 'ara.traineddata', 'ab9d157d8e38ca00e7e39c7d5363a5239e053f5b0dbdb3167dde9d8124335896'),
        'eng.traineddata': (TESS + 'eng.traineddata', '8280aed0782fe27257a68ea10fe7ef324ca0f8d85bd2fd145d1c2b560bcb66ba'),
        'LICENSE': (TESS + 'LICENSE', 'a6cba85bc92e0cff7a450b1d873c0eaa2e9fc96bf472df0247a26bec77bf3ff9'),
    },
    'paddle': {
        'arabic_PP-OCRv5_rec_mobile.onnx': (
            'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/PP-OCRv5/rec/arabic_PP-OCRv5_rec_mobile.onnx',
            'c1192e632d0baa9146ae5b756a0e635e3dc63c1733737ebfd1629e87144e9295'),
        'LICENSE-PaddleOCR': ('https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/v3.0.0/LICENSE',
                              '3840c5c0c61c294264d2dd77b8777be6ddd90121ef4e0e64abcd22edea581d6e'),
        'LICENSE-RapidOCR': ('https://raw.githubusercontent.com/RapidAI/RapidOCR/v3.10.0/LICENSE',
                             '3e0af25fdd06aa9586ae97adb00ea927ebe5a3805ac77d2d3a81ce5f55693333'),
    },
}
WRITTEN = {'tessdata': {'configs/tsv': 'tessedit_create_tsv 1\n'}}   # PdfCraft runs «tesseract page.png stdout -l ara+eng tsv»


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(vendor):
    vendor = Path(vendor)
    for folder, files in SETS.items():
        out = vendor / folder
        out.mkdir(parents=True, exist_ok=True)
        for name, (url, want) in files.items():
            dest = out / name
            if dest.exists() and sha256(dest) == want:
                print(f'{folder}/{name}: in place')
                continue
            with tempfile.NamedTemporaryFile(dir=out, delete=False) as tmp:
                with urllib.request.urlopen(url, timeout=300) as r:
                    while chunk := r.read(1 << 20):
                        tmp.write(chunk)
            got = sha256(tmp.name)
            if got != want:
                Path(tmp.name).unlink()
                sys.exit(f'{folder}/{name}: SHA-256 {got} is not the pinned {want} — not used')
            Path(tmp.name).replace(dest)
            dest.chmod(0o644)                                    # read by the program's own user too (the company image runs as «app»)
            print(f'{folder}/{name}: fetched and checked')
        for rel, text in WRITTEN.get(folder, {}).items():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            (out / rel).write_text(text)
        (out / 'SOURCE.txt').write_text(''.join(f'{name}  {url}  sha256 {h}\n' for name, (url, h) in files.items())
                                        + ''.join(f'{rel}  written by tools/ocr/fetch.py\n' for rel in WRITTEN.get(folder, {})))
    return vendor


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(APP / 'vendor'))
    print(fetch(ap.parse_args().out))
