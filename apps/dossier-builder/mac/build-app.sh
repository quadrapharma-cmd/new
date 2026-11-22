#!/bin/bash
# eBOX.app: the launcher, the program's code (the engine, its rule packs, the Egyptian eCTD profile, its fonts) and the runtime
# built by build-runtime.sh, packed. Runs on a Mac after build-runtime.sh:  bash apps/dossier-builder/mac/build-app.sh <out folder>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
V="$(cat "$HERE/RUNTIME_VERSION")"
RT="/Users/Shared/eBOX/runtime-$V"
OUT="${1:-dist}"
APP="$OUT/eBOX.app"
C="$APP/Contents"
[ -f "$RT/version" ] || { echo "no runtime at $RT: run build-runtime.sh first"; exit 1; }
rm -rf "$APP"
mkdir -p "$C/MacOS" "$C/Resources/code/apps/dossier-builder/vendor" "$C/Resources/code/docs/ctd/ectd"

cp "$HERE/launcher.sh" "$C/MacOS/eBOX"
chmod 755 "$C/MacOS/eBOX"
VERSION="1.0.$(git -C "$REPO" rev-list --count HEAD)"
sed -e "s/__VERSION__/$VERSION/" -e "s/__BUILD__/$(git -C "$REPO" rev-parse --short HEAD)/" "$HERE/Info.plist" > "$C/Info.plist"
echo "$V" > "$C/Resources/runtime-version"
uname -m > "$C/Resources/runtime-arch"

# the code the program reads (common.py finds them where they are in the repository)
rsync -a --exclude '__pycache__' --exclude '*.pyc' "$REPO/apps/dossier-builder/engine" "$C/Resources/code/apps/dossier-builder/"
rsync -a "$REPO/apps/dossier-builder/rulepacks" "$C/Resources/code/apps/dossier-builder/"
rsync -a "$REPO/apps/dossier-builder/vendor/fonts" "$C/Resources/code/apps/dossier-builder/vendor/"
rsync -a "$REPO/docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0" "$C/Resources/code/docs/ctd/ectd/"
cp "$HERE/README-AR.txt" "$C/Resources/"

# the icon: «eBOX» on the program's green, drawn with its own Python and fonts
ICONSET="$(mktemp -d)/eBOX.iconset"
mkdir -p "$ICONSET"
"$RT/env/bin/python" - "$ICONSET" "$REPO/apps/dossier-builder/vendor/fonts/LiberationSans-Bold.ttf" <<'PY'
import sys
from PIL import Image, ImageDraw, ImageFont
out, font = sys.argv[1], sys.argv[2]
def icon(s):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((s * .06, s * .06, s * .94, s * .94), radius=s * .2, fill=(15, 107, 92, 255))
    f = ImageFont.truetype(font, max(4, int(s * .27)))
    w = d.textlength('eBOX', font=f)
    d.text(((s - w) / 2, s * .34), 'eBOX', font=f, fill=(255, 255, 255, 255))
    return im
for base in (16, 32, 128, 256, 512):                      # the names iconutil takes, and no other
    icon(base).save(f'{out}/icon_{base}x{base}.png')
    icon(base * 2).save(f'{out}/icon_{base}x{base}@2x.png')
PY
iconutil -c icns -o "$C/Resources/eBOX.icns" "$ICONSET"

# the runtime, packed as it lies (no macOS metadata)
COPYFILE_DISABLE=1 tar -C "$RT" --exclude ./.complete -czf "$C/Resources/runtime.tar.gz" .
du -sh "$C/Resources/runtime.tar.gz" "$APP"
