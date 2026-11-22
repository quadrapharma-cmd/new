#!/bin/bash
# The Mac runtime of eBOX: the outside programs the combined-dossier program uses, in the versions it was measured with in the
# cloud edition (tesseract 5.3.4 with the tessdata_fast 4.1.0 language files, ghostscript 10.02.1, poppler 24.02.0, Python 3.13
# and the libraries of requirements.txt, LibreOffice 24.2.7.2, Playwright 1.63's Chromium), at a fixed place so that nothing in it
# needs rewriting when it is unpacked on the person's Mac: /Users/Shared/eBOX/runtime-<RUNTIME_VERSION>.
# Runs on a Mac (GitHub's runners, .github/workflows/ebox-mac.yml):  bash apps/dossier-builder/mac/build-runtime.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cat "$HERE/RUNTIME_VERSION")"
RT="/Users/Shared/eBOX/runtime-$V"
case "$(uname -m)" in
  arm64)  PLAT=osx-arm64; LODIR=aarch64; LOFILE=aarch64 ;;
  x86_64) PLAT=osx-64;    LODIR=x86_64;  LOFILE=x86-64 ;;
  *) echo "unknown machine $(uname -m)"; exit 1 ;;
esac
TMP="$(mktemp -d)"
mkdir -p /Users/Shared/eBOX
if [ -e "$RT" ]; then mv "$RT" "$TMP/old-runtime"; fi
mkdir -p "$RT"

echo "== 1. the tools from conda-forge ($PLAT)"
curl -fsSL "https://micro.mamba.pm/api/micromamba/$PLAT/latest" | tar -xj -C "$TMP" bin/micromamba
"$TMP/bin/micromamba" --version
export MAMBA_ROOT_PREFIX="$TMP/mamba"
EXTRA=""
# PyPI has no Intel-Mac wheel of pikepdf 10.17.0 (it would be built without qpdf's headers): conda-forge's build of it
if [ "$PLAT" = osx-64 ]; then EXTRA="pikepdf=10.17.0"; fi
"$TMP/bin/micromamba" create -y -p "$RT/env" -c conda-forge --override-channels \
  python=3.13 tesseract=5.3.4 ghostscript=10.02.1 poppler=24.02.0 $EXTRA
"$RT/env/bin/python" -m pip install --no-cache-dir --disable-pip-version-check -r "$HERE/requirements.txt"
"$RT/env/bin/tesseract" --version | head -1
"$RT/env/bin/gs" --version
"$RT/env/bin/pdftotext" -v 2>&1 | head -1

echo "== 2. the OCR language files (the cloud edition's: Debian's tesseract-ocr-ara/eng 1:4.1.0-2 = tessdata_fast 4.1.0)"
# (no osd.traineddata: it serves page-rotation detection, which the program never asks OCRmyPDF for)
mkdir -p "$RT/tessdata"
curl -fsSL -o "$RT/tessdata/ara.traineddata" https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/ara.traineddata
curl -fsSL -o "$RT/tessdata/eng.traineddata" https://github.com/tesseract-ocr/tessdata_fast/raw/4.1.0/eng.traineddata
(cd "$RT/tessdata" && shasum -a 256 -c "$HERE/tessdata.sha256")
# tesseract's own files beside the language files, as in the cloud edition's tessdata: its configs (OCRmyPDF asks for «hocr»,
# «txt»…) and the glyphless font of the text layer (pdf.ttf)
for f in configs tessconfigs pdf.ttf; do
  if [ -e "$RT/env/share/tessdata/$f" ]; then cp -R "$RT/env/share/tessdata/$f" "$RT/tessdata/"; else echo "no $f in the tesseract package"; exit 1; fi
done
ls "$RT/tessdata" "$RT/tessdata/configs"

echo "== 3. LibreOffice 24.2.7.2 (The Document Foundation's own build, signed by it)"
curl -fsSL -o "$TMP/lo.dmg" \
  "https://downloadarchive.documentfoundation.org/libreoffice/old/24.2.7.2/mac/$LODIR/LibreOffice_24.2.7.2_MacOS_$LOFILE.dmg"
shasum -a 256 "$TMP/lo.dmg"
if [ -f "$HERE/libreoffice.sha256" ] && grep -q "$LOFILE" "$HERE/libreoffice.sha256"; then
  (cd "$TMP" && grep "$LOFILE" "$HERE/libreoffice.sha256" | sed "s#LibreOffice_24.2.7.2_MacOS_$LOFILE.dmg#lo.dmg#" | shasum -a 256 -c -)
fi
hdiutil attach -nobrowse -readonly -mountpoint "$TMP/lo" "$TMP/lo.dmg" >/dev/null
ditto "$TMP/lo/LibreOffice.app" "$RT/LibreOffice.app"
hdiutil detach "$TMP/lo" >/dev/null
"$RT/LibreOffice.app/Contents/MacOS/soffice" --version
ls "$RT/LibreOffice.app/Contents/Resources/fonts/truetype" | grep -E "^(Liberation|Carlito|Caladea)" || echo "no Liberation/Carlito/Caladea in LibreOffice"

echo "== 4. Chromium for the printed pages (Playwright's, pinned by playwright==1.63.0)"
PLAYWRIGHT_BROWSERS_PATH="$RT/ms-playwright" "$RT/env/bin/python" -m playwright install --only-shell chromium

echo "$V" > "$RT/version"
du -sh "$RT"/env "$RT"/tessdata "$RT"/LibreOffice.app "$RT"/ms-playwright
rm -rf "$TMP"
