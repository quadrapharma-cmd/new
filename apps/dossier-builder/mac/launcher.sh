#!/bin/bash
# eBOX on a Mac (eBOX.app/Contents/MacOS/eBOX). The first launch unpacks the program's own tools into
# /Users/Shared/eBOX/runtime-<version> (no password is asked: that folder is open to the Mac's users); then the page opens in
# the browser. «--self-test» runs the program's own check instead, in the Terminal.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
RES="$(cd "$HERE/../Resources" && pwd)"
V="$(cat "$RES/runtime-version")"
WANT="$(cat "$RES/runtime-arch")"
ROOT=/Users/Shared/eBOX
RT="$ROOT/runtime-$V"
SELFTEST=0
for a in "$@"; do [ "$a" = "--self-test" ] && SELFTEST=1; done

tell() {   # $1: alert | note, $2: the text (formal Arabic)
  if [ "$SELFTEST" = 1 ]; then echo "$2"; return; fi
  if [ "$1" = alert ]; then osascript -e "display alert \"eBOX\" message \"$2\"" >/dev/null 2>&1
  else osascript -e "display notification \"$2\" with title \"eBOX\"" >/dev/null 2>&1; fi
}

if [ "$WANT" = arm64 ] && [ "$(uname -m)" != arm64 ]; then
  tell alert "هذه النسخة لأجهزة Mac ذات معالج Apple (M1 وما بعده)، وهذا الجهاز بمعالج Intel: نزِّل نسخة Intel من البرنامج."
  exit 1
fi

if [ ! -f "$RT/.complete" ]; then
  tell note "يُجهَّز البرنامج للمرة الأولى، وقد يستغرق ذلك بضع دقائق."
  # read through a pipe: macOS's tar gives every file it unpacks the «downloaded» mark of an archive it opens by name, and then
  # stops each tool of the program when it runs. The tools are a part of this app, which the person approved when first opening
  # it (System Settings ← Privacy & Security ← Open Anyway); the app itself keeps its mark.
  mkdir -p "$ROOT" && rm -rf "$RT.part" && mkdir "$RT.part" \
    && cat "$RES/runtime.tar.gz" | tar -xzf - -C "$RT.part" \
    && rm -rf "$RT" && mv "$RT.part" "$RT" && touch "$RT/.complete" \
    || { rm -rf "$RT.part"; tell alert "تعذّر تجهيز البرنامج: لا مساحة كافية على القرص (يلزم نحو 3 غيغابايت)، أو لا إذن بالكتابة في المجلد /Users/Shared."; exit 1; }
  # the previous version's tools, by its exact name (never a wildcard)
  if [ -f "$ROOT/current-version" ]; then
    P="$(cat "$ROOT/current-version")"
    if [ -n "$P" ] && [ "$P" != "$V" ] && [ -d "$ROOT/runtime-$P" ]; then rm -rf "$ROOT/runtime-$P"; fi
  fi
  echo "$V" > "$ROOT/current-version"
fi

export PATH="$RT/env/bin:$RT/LibreOffice.app/Contents/MacOS:/usr/bin:/bin:/usr/sbin:/sbin"
export TESSDATA_PREFIX="$RT/tessdata" PLAYWRIGHT_BROWSERS_PATH="$RT/ms-playwright" PYTHONNOUSERSITE=1
export PYTHONPATH="$RES/code/apps/dossier-builder/engine"
if [ "$SELFTEST" = 1 ]; then
  exec "$RT/env/bin/python3" -m dossier_engine.combined.mac --self-test
fi
mkdir -p "$HOME/Library/Logs"
exec "$RT/env/bin/python3" -m dossier_engine.combined.mac >>"$HOME/Library/Logs/eBOX.log" 2>&1
