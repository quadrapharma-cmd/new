#!/usr/bin/env bash
# Builds PdfCraft's command-line program — the program's PDF engine — from its pinned commit, without its MCP server
# (docs/ctd/PDFCRAFT-INTEGRATION.md). The result goes to vendor/pdfcraft/ (not in git), where the engine finds it.
#   PDFCRAFT_SRC   where the source is kept (default .cache/pdfcraft-src beside this app)
#   PDFCRAFT_OUT   where the program goes (default vendor/pdfcraft)
#   CARGO_TARGET_DIR is honoured.
# Needs git, Rust 1.95 or newer and a C compiler (the signing part builds aws-lc). On Windows set AWS_LC_SYS_PREBUILT_NASM=1
# when NASM is not installed.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
app="$(cd "$here/../.." && pwd)"
pin="$(tr -d '[:space:]' < "$here/PIN")"
src="${PDFCRAFT_SRC:-$app/.cache/pdfcraft-src}"
out="${PDFCRAFT_OUT:-$app/vendor/pdfcraft}"
exe=""
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) exe=".exe" ;; esac

if [ ! -d "$src/.git" ]; then
  mkdir -p "$(dirname "$src")"
  git init -q "$src"
  git -C "$src" remote add origin https://github.com/storytold/pdfcraft
fi
if ! git -C "$src" cat-file -e "$pin^{commit}" 2>/dev/null; then
  git -C "$src" fetch -q --depth 1 origin "$pin"
fi
git -C "$src" -c advice.detachedHead=false checkout -q --detach "$pin"
test "$(git -C "$src" rev-parse HEAD)" = "$pin" || { echo "PdfCraft source is not at the pinned commit $pin" >&2; exit 1; }
# our changes to PdfCraft (patches/, each one described in its file and in docs/ctd/PDFCRAFT-INTEGRATION.md), on a clean checkout
if ! git -C "$src" diff --quiet; then git -C "$src" checkout -q -- .; fi
for p in "$here"/patches/*.patch; do
  [ -e "$p" ] || continue
  git -C "$src" apply --whitespace=nowarn "$p" || { echo "patch $(basename "$p") does not apply to $pin" >&2; exit 1; }
  echo "applied $(basename "$p")"
done

target="${CARGO_TARGET_DIR:-$src/target}"
(cd "$src" && CARGO_TARGET_DIR="$target" cargo build --release --locked -p pdfcraft-cli --no-default-features)

mkdir -p "$out"
cp "$target/release/pdfcraft-cli$exe" "$out/"
for f in LICENSE-MIT LICENSE-APACHE NOTICE ATTRIBUTION.md; do cp "$src/$f" "$out/"; done
rm -rf "$out/licenses" && cp -R "$src/licenses" "$out/licenses"
py="$(command -v python || command -v python3)"        # «python» first: on Windows «python3» can be the Store's stub
"$py" "$here/licenses.py" "$src" "$out"            # every crate compiled in, with its licence and notice files
echo "$pin" > "$out/PIN"
cp "$here"/patches/*.patch "$out/" 2>/dev/null || true      # the changes made to PdfCraft travel with it (its licence asks a modified file to say so)
"$out/pdfcraft-cli$exe" --version
echo "PdfCraft $pin → $out/pdfcraft-cli$exe"
