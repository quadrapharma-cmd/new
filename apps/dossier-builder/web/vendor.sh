#!/bin/bash
# Fetch the browser runtime once (not committed: ~20 MB): Pyodide 0.27.7 + the wasm wheels the engine needs, and the pure wheels.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; V=0.27.7; mkdir -p "$HERE/vendor/pyodide" "$HERE/vendor/wheels"
NEED="pyodide.js pyodide.asm.js pyodide.asm.wasm python_stdlib.zip pyodide-lock.json
lxml-5.2.1-cp312-cp312-pyodide_2024_0_wasm32.whl pyyaml-6.0.2-cp312-cp312-pyodide_2024_0_wasm32.whl typing_extensions-4.11.0-py3-none-any.whl
pydantic_core-2.27.2-cp312-cp312-pyodide_2024_0_wasm32.whl annotated_types-0.6.0-py3-none-any.whl pydantic-2.10.5-py3-none-any.whl
six-1.16.0-py2.py3-none-any.whl attrs-23.2.0-py3-none-any.whl pyrsistent-0.20.0-cp312-cp312-pyodide_2024_0_wasm32.whl
rpds_py-0.18.0-cp312-cp312-pyodide_2024_0_wasm32.whl referencing-0.34.0-py3-none-any.whl jsonschema_specifications-2023.12.1-py3-none-any.whl
jsonschema-4.21.1-py3-none-any.whl sqlite3-1.0.0-cp312-cp312-pyodide_2024_0_wasm32.whl openssl-1.1.1w.zip hashlib-1.0.0-cp312-cp312-pyodide_2024_0_wasm32.whl
ssl-1.0.0-cp312-cp312-pyodide_2024_0_wasm32.whl"
for f in $NEED; do echo "pyodide/$f"; done > /tmp/pyodide-members.txt
curl -sS -L "https://github.com/pyodide/pyodide/releases/download/$V/pyodide-$V.tar.bz2" | tar -xj -C "$HERE/vendor/pyodide" --strip-components=1 -T /tmp/pyodide-members.txt
pip download -q --no-deps --only-binary=:all: --python-version 3.12 --platform any -d "$HERE/vendor/wheels" \
  "fastapi==0.115.12" "starlette==0.46.2" "anyio==4.6.2.post1" "sniffio==1.3.1" "idna==3.10" "python-multipart==0.0.20" \
  "typing_extensions==4.12.2" "pypdf==7.0.0" "python-docx==1.2.0"
ls -la "$HERE/vendor/pyodide" "$HERE/vendor/wheels"
# pdf.js (page images of scanned PDFs for the AI intake)
mkdir -p "$HERE/vendor/pdfjs" && curl -sS -L "https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-4.10.38.tgz" | tar -xz -C /tmp package/build/pdf.min.mjs package/build/pdf.worker.min.mjs && cp /tmp/package/build/pdf.min.mjs /tmp/package/build/pdf.worker.min.mjs "$HERE/vendor/pdfjs/"
# tesseract.js (OCR in the browser: Arabic + English): the library, its single-file LSTM cores, and the fast language data as base64 text
T="$HERE/vendor/tess"; mkdir -p "$T" /tmp/tessjs
curl -sS -L "https://registry.npmjs.org/tesseract.js/-/tesseract.js-7.0.0.tgz" | tar -xz -C /tmp/tessjs package/dist/tesseract.min.js package/dist/worker.min.js package/dist/tesseract.min.js.LICENSE.txt
curl -sS -L "https://registry.npmjs.org/tesseract.js-core/-/tesseract.js-core-6.1.2.tgz" | tar -xz -C /tmp/tessjs package/tesseract-core-simd-lstm.wasm.js package/tesseract-core-lstm.wasm.js package/LICENSE
cp /tmp/tessjs/package/dist/tesseract.min.js /tmp/tessjs/package/dist/worker.min.js /tmp/tessjs/package/tesseract-core-simd-lstm.wasm.js /tmp/tessjs/package/tesseract-core-lstm.wasm.js "$T/"
cp /tmp/tessjs/package/dist/tesseract.min.js.LICENSE.txt "$T/LICENSE.tesseract.js.txt"; cp /tmp/tessjs/package/LICENSE "$T/LICENSE.tesseract.js-core.txt"
for l in ara eng; do curl -sS -L -o /tmp/$l.traineddata "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/$l.traineddata"; gzip -9 -c /tmp/$l.traineddata | base64 -w0 > "$T/$l.traineddata.gz.b64.txt"; done
cp "$HERE/tess/worker.boot.js" "$T/"      # decodes the base64 language data inside the worker (tracked in git)
ls -la "$T"
