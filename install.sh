#!/usr/bin/env bash
# Rencora installer for macOS / Linux:  bash install.sh
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 && \
       "$c" -c 'import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)'; then
        PY="$c"; break
    fi
done
if [ -z "$PY" ]; then
    echo "[ERROR] Python 3.11 or 3.12 not found. Install it (python.org, brew, or your package manager) and rerun."
    exit 1
fi
echo "Using: $PY"

[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install chromium || echo "[WARN] Playwright browser not installed."

echo
echo "Done! Start Rencora with:  bash start.sh"
echo "On first start, open http://127.0.0.1:8000/setup and enter your Gemini API key."
