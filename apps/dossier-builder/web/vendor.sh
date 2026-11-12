#!/bin/bash
# Fetch the browser runtime once (not committed: ~20 MB): Pyodide 0.27.7 + the wasm wheels the engine needs, and the pure wheels,
# plus pdf.js, tesseract.js and the image decoders (reading scanned documents and photos in the browser).
#   web/vendor.sh        everything (the browser edition)
#   web/vendor.sh ocr    pdf.js + tesseract.js + image decoders only (the desktop build: scans are read in the user's browser, no system tesseract)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; V=0.27.7; MODE="${1:-all}"
b64() { base64 | tr -d '\n'; }          # GNU and BSD/macOS base64 alike (no -w0 on macOS)
if [ "$MODE" = "all" ]; then
mkdir -p "$HERE/vendor/pyodide" "$HERE/vendor/wheels"
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
fi
# pdf.js (page images of scanned PDFs for the AI intake)
mkdir -p "$HERE/vendor/pdfjs" && curl -sS -L "https://registry.npmjs.org/pdfjs-dist/-/pdfjs-dist-4.10.38.tgz" | tar -xz -C /tmp package/build/pdf.min.mjs package/build/pdf.worker.min.mjs && cp /tmp/package/build/pdf.min.mjs /tmp/package/build/pdf.worker.min.mjs "$HERE/vendor/pdfjs/"
# tesseract.js (OCR in the browser: Arabic + English): the library, its single-file LSTM cores, and the fast language data as base64 text
T="$HERE/vendor/tess"; mkdir -p "$T" /tmp/tessjs
curl -sS -L "https://registry.npmjs.org/tesseract.js/-/tesseract.js-7.0.0.tgz" | tar -xz -C /tmp/tessjs package/dist/tesseract.min.js package/dist/worker.min.js package/dist/tesseract.min.js.LICENSE.txt
curl -sS -L "https://registry.npmjs.org/tesseract.js-core/-/tesseract.js-core-6.1.2.tgz" | tar -xz -C /tmp/tessjs package/tesseract-core-simd-lstm.wasm.js package/tesseract-core-lstm.wasm.js package/LICENSE
cp /tmp/tessjs/package/dist/tesseract.min.js /tmp/tessjs/package/dist/worker.min.js /tmp/tessjs/package/tesseract-core-simd-lstm.wasm.js /tmp/tessjs/package/tesseract-core-lstm.wasm.js "$T/"
cp /tmp/tessjs/package/dist/tesseract.min.js.LICENSE.txt "$T/LICENSE.tesseract.js.txt"; cp /tmp/tessjs/package/LICENSE "$T/LICENSE.tesseract.js-core.txt"
for l in ara eng; do curl -sS -L -o /tmp/$l.traineddata "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/$l.traineddata"; gzip -9 -c /tmp/$l.traineddata | b64 > "$T/$l.traineddata.gz.b64.txt"; done
cp "$HERE/tess/worker.boot.js" "$T/"      # decodes the base64 language data inside the worker (tracked in git)
ls -la "$T"
# image decoders for the browser (ocr.js): TIFF pages (UTIF.js + pako's inflate) and HEIC/HEIF photos (libheif, WebAssembly inside one file)
I="$HERE/vendor/img"; mkdir -p "$I" /tmp/imgjs/utif /tmp/imgjs/pako /tmp/imgjs/heif
curl -sS -L "https://registry.npmjs.org/utif/-/utif-3.1.0.tgz" | tar -xz -C /tmp/imgjs/utif package/UTIF.js package/LICENSE
curl -sS -L "https://registry.npmjs.org/pako/-/pako-2.1.0.tgz" | tar -xz -C /tmp/imgjs/pako package/dist/pako_inflate.min.js package/LICENSE
curl -sS -L "https://registry.npmjs.org/libheif-js/-/libheif-js-1.23.5.tgz" | tar -xz -C /tmp/imgjs/heif package/libheif-wasm/libheif-bundle.js package/libheif-wasm/LICENSE
cp /tmp/imgjs/utif/package/UTIF.js /tmp/imgjs/pako/package/dist/pako_inflate.min.js /tmp/imgjs/heif/package/libheif-wasm/libheif-bundle.js "$I/"
cp /tmp/imgjs/utif/package/LICENSE "$I/LICENSE.utif.txt"; cp /tmp/imgjs/pako/package/LICENSE "$I/LICENSE.pako.txt"; cp /tmp/imgjs/heif/package/libheif-wasm/LICENSE "$I/LICENSE.libheif.txt"
mkdir -p "$I/test" && curl -sS -L -o "$I/test/example.heic" "https://raw.githubusercontent.com/strukturag/libheif/master/examples/example.heic"   # a public sample for the HEIC test (not committed)
ls -la "$I"

# public RAR samples for the archive tests (not committed): libarchive's own test files, stored there uuencoded
A="$HERE/vendor/arch/test"; mkdir -p "$A"
for n in test_read_format_rar_compress_normal test_read_format_rar5_compressed test_read_format_rar5_stored; do
  curl -sS -L "https://raw.githubusercontent.com/libarchive/libarchive/v3.7.2/libarchive/test/$n.rar.uu" | python3 -c "
import binascii, sys
out = b''
for line in sys.stdin.buffer.read().splitlines()[1:]:
    if line.strip() in (b'end', b'\`', b''):
        break
    out += binascii.a2b_uu(line)
sys.stdout.buffer.write(out)" > "$A/$n.rar"
done
ls -la "$A"
