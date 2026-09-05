#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export TDX_HOST="${TDX_HOST:-115.238.90.165:7709}"
exec python -m uvicorn backend.app:app --host 127.0.0.1 --port "${TSP_PORT:-8765}"
