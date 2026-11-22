#!/bin/bash
# The packed eBOX.app, checked as it will reach the person: on a Mac with no runtime yet, its archive marked as downloaded from
# the internet (quarantine), started by its launcher with «--self-test»; then: the tools it unpacked are not marked, so macOS will
# not stop each of them. Runs on a Mac after build-app.sh:  bash apps/dossier-builder/mac/smoke.sh <eBOX.app>
set -euo pipefail
APP="$1"
V="$(cat "$APP/Contents/Resources/runtime-version")"
RT="/Users/Shared/eBOX/runtime-$V"
KEEP="$(mktemp -d)/runtime-built"
mv "$RT" "$KEEP"
rm -f /Users/Shared/eBOX/current-version
xattr -w com.apple.quarantine "0083;$(printf '%x' "$(date +%s)");Safari;" "$APP/Contents/Resources/runtime.tar.gz"
"$APP/Contents/MacOS/eBOX" --self-test
if xattr -p com.apple.quarantine "$RT/env/bin/python3" >/dev/null 2>&1 || \
   xattr -p com.apple.quarantine "$RT/LibreOffice.app/Contents/MacOS/soffice" >/dev/null 2>&1; then
  echo "the unpacked tools carry the quarantine mark"; exit 1
fi
echo "the unpacked tools carry no quarantine mark"
xattr -d com.apple.quarantine "$APP/Contents/Resources/runtime.tar.gz"
rm -rf "$RT"
mv "$KEEP" "$RT"
