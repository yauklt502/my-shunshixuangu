#!/usr/bin/env bash
# XianBiDu Tick Stock Panel one-click start
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
PORT="${TSP_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"
LOG="$ROOT/startup.log"

echo "========================================"
echo "  XianBiDu / Tick Stock Panel"
echo "  One-click start"
echo "========================================"
echo "Working dir: $ROOT"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Install Python 3.10+ first."
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "[1/4] Creating venv..."
  python3 -m venv .venv
else
  echo "[1/4] venv exists"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/4] Installing dependencies (first run may take a few minutes)..."
python -m pip install -U pip | tee -a "$LOG"
python -m pip install -r requirements.txt | tee -a "$LOG"

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export TDX_HOST="${TDX_HOST:-115.238.90.165:7709}"

if command -v lsof >/dev/null 2>&1; then
  OLD_PID="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${OLD_PID}" ]]; then
    echo "[INFO] Port ${PORT} busy, killing ${OLD_PID}"
    kill ${OLD_PID} 2>/dev/null || true
    sleep 1
  fi
fi

echo "[3/4] Starting ${URL}"
echo "[4/4] Browser will open when ready"
echo "Keep this terminal open. Ctrl+C to stop."
echo "----------------------------------------"

(
  for _ in $(seq 1 20); do
    if curl -sf "${URL}/api/health" >/dev/null 2>&1; then
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${URL}" >/dev/null 2>&1 || true
      elif command -v open >/dev/null 2>&1; then
        open "${URL}" >/dev/null 2>&1 || true
      fi
      break
    fi
    sleep 0.5
  done
) &

exec python -m uvicorn backend.app:app --host 127.0.0.1 --port "${PORT}"
