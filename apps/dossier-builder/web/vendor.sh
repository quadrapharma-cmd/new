#!/bin/bash
# Fetch the browser runtime once (not committed: ~20 MB): Pyodide 0.27.7 + the wasm wheels the engine needs, and the pure wheels.
# No OCR anywhere (no tesseract.js, no pdf.js, no image decoders): a document without text is refused at the upload gate.
#   web/vendor.sh        the runtime, then the public RAR samples for the archive tests
#   web/vendor.sh tests  the RAR samples only
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
# public RAR samples for the archive tests (not committed): libarchive's own test files, stored there uuencoded — old format and RAR5,
# split in parts, solid, the text method, filters, a self-extracting one, and damaged ones that must be refused
A="$HERE/vendor/arch/test"; mkdir -p "$A"
RARS="test_read_format_rar.rar test_read_format_rar_compress_normal.rar test_read_format_rar_compress_best.rar test_read_format_rar_unicode.rar
test_read_format_rar_filter.rar test_read_format_rar_binary_data.rar test_read_format_rar_windows.rar test_read_format_rar_noeof.rar
test_read_format_rar_subblock.rar test_read_format_rar_sfx.exe test_read_format_rar_encryption_header.rar
test_read_format_rar_encryption_partially.rar test_rar_multivolume_multiple_files.part1.rar test_rar_multivolume_multiple_files.part2.rar
test_rar_multivolume_multiple_files.part3.rar test_rar_multivolume_multiple_files.part4.rar test_rar_multivolume_multiple_files.part5.rar
test_rar_multivolume_multiple_files.part6.rar test_read_format_rar5_arm.rar test_read_format_rar5_multiarchive_solid.part01.rar
test_read_format_rar5_multiarchive_solid.part02.rar test_read_format_rar5_multiarchive_solid.part03.rar
test_read_format_rar5_multiarchive_solid.part04.rar test_read_format_rar5_hardlink.rar test_read_format_rar5_symlink.rar
test_read_format_rar5_blake2.rar test_read_format_rar5_win32.rar test_read_format_rar5_multiple_files_solid.rar test_read_format_rar5_compressed.rar
test_read_format_rar5_stored.rar test_read_format_rar5_truncated_huff.rar test_read_format_rar5_distance_overflow.rar
test_read_format_rar5_readtables_overflow.rar test_read_format_rar5_leftshift1.rar test_read_format_rar5_invalid_dict_reference.rar"
for f in $RARS; do
  curl -sS -f -L "https://raw.githubusercontent.com/libarchive/libarchive/v3.7.2/libarchive/test/$f.uu" | python3 -c "
import binascii, sys
out = b''
for line in sys.stdin.buffer.read().splitlines()[1:]:
    if line.strip() in (b'end', b'\`', b''):
        break
    try:
        out += binascii.a2b_uu(line)
    except binascii.Error:
        out += binascii.a2b_uu(line[:(((line[0] - 32) & 63) * 4 + 5) // 3])
sys.stdout.buffer.write(out)" > "$A/$f"
done
ls "$A" | wc -l
