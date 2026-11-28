#!/bin/bash
# eBOX desk: the tools the program adds to the cloud machine, as on the machine where its results were measured (Ubuntu 24.04:
# tesseract 5.3.4 with the language files 4.1.0, ghostscript 10.02, the Noto fonts) and its Python packages at their pinned
# versions. Run from the folder that holds the repository (the environment's setup script runs this file).
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng ghostscript fonts-noto-core
if [ -d new/apps/dossier-builder ]; then
  # --ignore-installed: PyYAML and packaging came with the machine from Debian, and pip cannot uninstall them otherwise
  python3 -m pip install -q --disable-pip-version-check --ignore-installed -r new/apps/dossier-builder/mac/requirements.txt
  # eBOX's full program's interface, which the desk's last stages call in-process (combined/ebox.py, combined/assess.py)
  python3 -m pip install -q --disable-pip-version-check fastapi httpx python-multipart
fi
tesseract --list-langs 2>&1 | grep -qx ara && tesseract --list-langs 2>&1 | grep -qx eng
echo "eBOX tools ready: $(tesseract --version 2>&1 | head -1), ghostscript $(gs --version)"
