"""The browser edition's scan reading — the same reading as the desktop and company editions, in the page (the owner, 13/11/2026:
«all the improvements must work in the browser»). Fetched at fixed versions and checked (npm's integrity, SHA-256 for the models)
into web/vendor/ocr/, then published with the page by web/build.py under assets/ocr/ (loaded the first time a scan is read, then
kept on the device). Every licence here lets a closed commercial program ship it unchanged: Apache-2.0 and MIT, their texts beside.

  tess/    tesseract.js 7.0.0 and its single-file Tesseract 5 cores (WebAssembly inside the script), the accurate («best») Arabic
           model and the English «fast» one (English reads the same with either on our measures; «best» is too big for one file
           of the page), as gzip in base64 text: web/ocr/worker.boot.js decodes them inside tesseract.js's worker
  pdfjs/   pdf.js 4.10.38, the pages drawn at 300 dpi
  img/     UTIF.js 3.1.0 and pako's inflate 2.1.0: the pages of a TIFF scan (the browser draws PNG, JPEG, GIF, BMP and WebP itself)
  ort/     onnxruntime-web 1.31.1 (WebAssembly only), the second reader's runtime
  paddle/  PaddleOCR's Arabic recognition model (from vendor/paddle, tools/ocr/fetch.py) and its characters
The binary files (the runtime's .wasm, the model's .onnx) are written as gzip in base64 text (<name>.gz.b64.txt): the artifact
host serves text, and a file of the page may hold 16 MB at most (the runtime alone is 14.8 MB, 19.8 MB in base64).

Usage: python web/ocr_assets.py   (needs tools/ocr/fetch.py first, for the models)
"""
import base64
import gzip
import hashlib
import io
import json
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent
OUT = HERE / 'vendor' / 'ocr'
NPM = {   # package: (version, integrity, {member in the tarball: name under OUT})
    'tesseract.js': ('7.0.0', 'sha512-exPBkd+z+wM1BuMkx/Bjv43OeLBxhL5kKWsz/9JY+DXcXdiBjiAch0V49QR3oAJqCaL5qURE0vx9Eo+G5YE7mA==',
                     {'package/dist/tesseract.min.js': 'tess/tesseract.min.js', 'package/dist/worker.min.js': 'tess/worker.min.js',
                      'package/LICENSE.md': 'tess/LICENSE.tesseract.js.md'}),
    'tesseract.js-core': ('6.1.2', 'sha512-pv4GjmramjdObhDyR1q85Td8X60Puu/lGQn7Kw2id05LLgHhAcWgnz6xSdMCSxBMWjQDmMyDXPTC2aqADdpiow==',
                          {'package/tesseract-core-simd-lstm.wasm.js': 'tess/tesseract-core-simd-lstm.wasm.js',
                           'package/tesseract-core-lstm.wasm.js': 'tess/tesseract-core-lstm.wasm.js',
                           'package/LICENSE': 'tess/LICENSE.tesseract.js-core.txt'}),
    'pdfjs-dist': ('4.10.38', 'sha512-/Y3fcFrXEAsMjJXeL9J8+ZG9U01LbuWaYypvDW2ycW1jL269L3js3DVBjDJ0Up9Np1uqDXsDrRihHANhZOlwdQ==',
                   {'package/build/pdf.min.mjs': 'pdfjs/pdf.min.mjs', 'package/build/pdf.worker.min.mjs': 'pdfjs/pdf.worker.min.mjs',
                    'package/LICENSE': 'pdfjs/LICENSE.pdf.js.txt'}),
    'utif': ('3.1.0', 'sha512-WEo4D/xOvFW53K5f5QTaTbbiORcm2/pCL9P6qmJnup+17eYfKaEhDeX9PeQkuyEoIxlbGklDuGl8xwuXYMrrXQ==',
             {'package/UTIF.js': 'img/UTIF.js', 'package/LICENSE': 'img/LICENSE.utif.txt'}),
    'pako': ('2.1.0', 'sha512-w+eufiZ1WuJYgPXbV/PO3NCMEc3xqylkKHzp8bxp1uW4qaSNQUkwmLLEc3kKsfz8lpV1F8Ht3U1Cm+9Srog2ug==',
             {'package/dist/pako_inflate.min.js': 'img/pako_inflate.min.js', 'package/LICENSE': 'img/LICENSE.pako.txt'}),
    'onnxruntime-web': ('1.31.1', 'sha512-5GeH+bWQ+HxM10z7erGlsWqryrwMbSvm/1tkIsKTT48g0fI19VXVVC435t4t7VsPdSQeS7NmuZPXrQ73k82URw==',
                        {'package/dist/ort.wasm.bundle.min.mjs': 'ort/ort.wasm.bundle.min.mjs',
                         'package/dist/ort-wasm-simd-threaded.wasm': 'ort/ort-wasm-simd-threaded.wasm',
                         'package/README.md': None}),
}
FAST = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4.1.0/'
MODELS = {   # name under OUT: (where from, SHA-256 of the raw file)
    'tess/ara.traineddata': (APP / 'vendor' / 'tessdata' / 'ara.traineddata', 'ab9d157d8e38ca00e7e39c7d5363a5239e053f5b0dbdb3167dde9d8124335896'),
    'tess/eng.traineddata': (FAST + 'eng.traineddata', '7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'),
    'tess/LICENSE.tessdata.txt': (APP / 'vendor' / 'tessdata' / 'LICENSE', 'a6cba85bc92e0cff7a450b1d873c0eaa2e9fc96bf472df0247a26bec77bf3ff9'),
    'paddle/arabic_PP-OCRv5_rec_mobile.onnx': (APP / 'vendor' / 'paddle' / 'arabic_PP-OCRv5_rec_mobile.onnx',
                                               'c1192e632d0baa9146ae5b756a0e635e3dc63c1733737ebfd1629e87144e9295'),
    'paddle/LICENSE-PaddleOCR': (APP / 'vendor' / 'paddle' / 'LICENSE-PaddleOCR', '3840c5c0c61c294264d2dd77b8777be6ddd90121ef4e0e64abcd22edea581d6e'),
    'paddle/LICENSE-RapidOCR': (APP / 'vendor' / 'paddle' / 'LICENSE-RapidOCR', '3e0af25fdd06aa9586ae97adb00ea927ebe5a3805ac77d2d3a81ce5f55693333'),
}
ORT_LICENSE = 'MIT License — Copyright (c) Microsoft Corporation. https://github.com/microsoft/onnxruntime/blob/main/LICENSE\n'


def get(url):
    with urllib.request.urlopen(url, timeout=300) as r:
        return r.read()


def npm(name, version, integrity, members):
    data = get(f'https://registry.npmjs.org/{name}/-/{name.split("/")[-1]}-{version}.tgz')
    algo, want = integrity.split('-', 1)
    if base64.b64encode(hashlib.new(algo, data).digest()).decode() != want:
        sys.exit(f'{name} {version}: the tarball is not the one npm signs — not used')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        names = set(t.getnames())
        for member, dest in members.items():
            if dest is None:
                continue
            if member not in names:
                sys.exit(f'{name} {version}: {member} is not in the package')
            (OUT / dest).parent.mkdir(parents=True, exist_ok=True)
            (OUT / dest).write_bytes(t.extractfile(member).read())
    print(f'{name} {version}: checked')


def model(dest, src, want):
    data = src.read_bytes() if isinstance(src, Path) else get(src)
    if hashlib.sha256(data).hexdigest() != want:
        sys.exit(f'{dest}: SHA-256 is not the pinned one — not used (run tools/ocr/fetch.py)')
    (OUT / dest).parent.mkdir(parents=True, exist_ok=True)
    if dest.endswith('.traineddata'):                       # gzip in base64 text: the worker shim decodes it (web/ocr/worker.boot.js)
        packed(dest, data)
    else:
        (OUT / dest).write_bytes(data)
    print(f'{dest}: checked')


def packed(dest, data):
    """<dest>.gz.b64.txt: gzip (no time stamp, so the same input gives the same file) in base64 text."""
    (OUT / dest).parent.mkdir(parents=True, exist_ok=True)
    (OUT / (dest + '.gz.b64.txt')).write_text(base64.b64encode(gzip.compress(data, 9, mtime=0)).decode('ascii'))


def characters():
    """The second reader's characters, from the model's own metadata (the page cannot read ONNX metadata)."""
    import onnxruntime as ort
    s = ort.InferenceSession(str(OUT / 'paddle' / 'arabic_PP-OCRv5_rec_mobile.onnx'), providers=['CPUExecutionProvider'])
    chars = s.get_modelmeta().custom_metadata_map['character'].splitlines()
    (OUT / 'paddle' / 'characters.json').write_text(json.dumps(chars, ensure_ascii=False))
    print(f'paddle/characters.json: {len(chars)} characters')


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name, (version, integrity, members) in NPM.items():
        npm(name, version, integrity, members)
    for dest, (src, want) in MODELS.items():
        model(dest, src, want)
    (OUT / 'ort' / 'LICENSE.onnxruntime.txt').write_text(ORT_LICENSE)
    shutil.copy(HERE / 'ocr' / 'worker.boot.js', OUT / 'tess' / 'worker.boot.js')
    characters()
    for dest in ('ort/ort-wasm-simd-threaded.wasm', 'paddle/arabic_PP-OCRv5_rec_mobile.onnx'):
        packed(dest, (OUT / dest).read_bytes())
        (OUT / dest).unlink()
    total = sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file())
    print(f'{OUT}: {total / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
