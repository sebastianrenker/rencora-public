#!/usr/bin/env bash
# Start Rencora (macOS / Linux):  bash start.sh
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo "Rencora is not installed yet - run: bash install.sh"
    exit 1
fi
exec .venv/bin/python run_headless.py --local --open
