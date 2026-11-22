#!/bin/bash
# The combined-dossier program's tests on a Mac, with the runtime built by build-runtime.sh (its tools first on the PATH):
# the made-up dossier through every stage, Claude's part with its stand-in, the Mac page and server, the formal Arabic, and the
# outputs compared with those of the cloud edition (tests/expected/mac-same).   bash apps/dossier-builder/mac/test.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cat "$HERE/RUNTIME_VERSION")"
RT="/Users/Shared/eBOX/runtime-$V"
export PATH="$RT/env/bin:$RT/LibreOffice.app/Contents/MacOS:$PATH"
export TESSDATA_PREFIX="$RT/tessdata" PLAYWRIGHT_BROWSERS_PATH="$RT/ms-playwright" PYTHONNOUSERSITE=1
cd "$HERE/.."
"$RT/env/bin/python" -m pytest -q -p no:cacheprovider tests/test_combined.py tests/test_formal_arabic.py tests/test_decide.py \
  tests/test_mac_app.py tests/test_mac_same.py "$@"
