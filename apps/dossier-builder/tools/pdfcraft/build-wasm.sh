#!/usr/bin/env bash
# PdfCraft for the browser edition: the same command-line program, from the same pinned commit and patches as build.sh, built for
# WebAssembly with a file system of its own (WASI). The browser runs it in the engine's thread over an in-memory folder
# (web/pdfcraft.wasi.js) with the WASI shim of @bjorn3/browser_wasi_shim (MIT OR Apache-2.0). Writes web/vendor/pdfcraft/ (not in
# git), which web/build.py publishes under assets/pdfcraft/.
#   PDFCRAFT_SRC      where the source is kept (default .cache/pdfcraft-src beside this app; build.sh checks it out)
#   PDFCRAFT_WASM_OUT where the files go (default web/vendor/pdfcraft)
#   CARGO_TARGET_DIR and CARGO_BUILD_JOBS are honoured.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
app="$(cd "$here/../.." && pwd)"
pin="$(tr -d '[:space:]' < "$here/PIN")"
src="${PDFCRAFT_SRC:-$app/.cache/pdfcraft-src}"
out="${PDFCRAFT_WASM_OUT:-$app/web/vendor/pdfcraft}"
SHIM_VERSION=0.4.2
SHIM_INTEGRITY='sha512-/iHkCVUG3VbcbmEHn5iIUpIrh7a7WPiwZ3sHy4HZKZzBdSadwdddYDZAII2zBvQYV0Lfi8naZngPCN7WPHI/hA=='

test -d "$src/.git" || { echo "no PdfCraft source at $src: run tools/pdfcraft/build.sh first" >&2; exit 1; }
test "$(git -C "$src" rev-parse HEAD)" = "$pin" || { echo "PdfCraft source is not at the pinned commit $pin: run build.sh" >&2; exit 1; }
for p in "$here"/patches/*.patch; do                       # the same patches as the desktop's program, already applied by build.sh
  [ -e "$p" ] || continue
  git -C "$src" apply --reverse --check --whitespace=nowarn "$p" 2>/dev/null || { echo "patch $(basename "$p") is not applied: run build.sh" >&2; exit 1; }
done
rustup target add wasm32-wasip1 >/dev/null
target="${CARGO_TARGET_DIR:-$src/target}"
(cd "$src" && CARGO_PROFILE_RELEASE_STRIP=symbols CARGO_TARGET_DIR="$target" cargo build --release --locked --target wasm32-wasip1 -p pdfcraft-cli --no-default-features)

rm -rf "$out" && mkdir -p "$out/wasi"
gzip -9 -n -c "$target/wasm32-wasip1/release/pdfcraft-cli.wasm" > "$out/pdfcraft-cli.wasm.gz"
cp "$src/LICENSE-MIT" "$src/LICENSE-APACHE" "$src/NOTICE" "$out/"
python3 "$here/licenses.py" "$src" "$out" wasm32-wasip1
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
curl -sS -f -L -o "$tmp/shim.tgz" "https://registry.npmjs.org/@bjorn3/browser_wasi_shim/-/browser_wasi_shim-$SHIM_VERSION.tgz"
python3 - "$tmp/shim.tgz" "$SHIM_INTEGRITY" <<'PY'
import base64, hashlib, sys
algo, want = sys.argv[2].split('-', 1)
if base64.b64encode(hashlib.new(algo, open(sys.argv[1], 'rb').read()).digest()).decode() != want:
    sys.exit('the WASI shim is not the one npm signs — not used')
PY
tar -xzf "$tmp/shim.tgz" -C "$tmp"
cp "$tmp"/package/dist/*.js "$tmp/package/LICENSE-MIT" "$tmp/package/LICENSE-APACHE" "$out/wasi/"
echo "PdfCraft $(git -C "$src" describe --tags 2>/dev/null || echo "$pin") for the browser → $out ($(du -h "$out/pdfcraft-cli.wasm.gz" | cut -f1) packed)"
