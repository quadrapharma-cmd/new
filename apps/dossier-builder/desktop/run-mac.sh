#!/bin/bash
# تشغيل منشئ الملفات على macOS من السورس (بدون بناء)
# Run Dossier Builder on macOS from source (no build needed)
#
# الخطوات:
# 1) نزّل Python 3.12 من: https://www.python.org/downloads/
# 2) نزّل الكود: https://github.com/quadrapharma-cmd/new/archive/refs/heads/claude/new-session-8nmyo7.zip
#    فك الضغط → هتلاقي فولدر new-claude-new-session-8nmyo7
# 3) افتح Terminal واكتب:
#      cd ~/Downloads/new-claude-new-session-8nmyo7/apps/dossier-builder/desktop
#      bash run-mac.sh
#
# البيانات بتتحفظ في: ~/Documents/DossierBuilder

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENV="$REPO/.venv-dossier"

echo "=== منشئ الملفات — Dossier Builder ==="
echo ""

# find a suitable python
PY=""
for p in python3.12 python3 python; do
    if command -v "$p" &>/dev/null; then
        ver=$("$p" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PY="$p"; break
        fi
    fi
done
if [ -z "$PY" ]; then
    echo "خطأ: محتاج Python 3.10 أو أحدث."
    echo "Error: Python 3.10+ is required."
    echo "نزّله من / Download from: https://www.python.org/downloads/"
    exit 1
fi
echo "Python: $($PY --version)"

# create venv if needed
if [ ! -d "$VENV" ]; then
    echo "بنجهّز البيئة (أول مرة بس — ممكن تاخد دقيقة)..."
    echo "Setting up (first time only — may take a minute)..."
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip -q
    "$VENV/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q
    echo "تم — Done."
fi

echo ""
echo "البرنامج بيشتغل..."
echo "Starting..."
"$VENV/bin/python" "$SCRIPT_DIR/launcher.py" "$@"
