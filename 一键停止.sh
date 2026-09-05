#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/launcher.py" --stop
elif command -v python >/dev/null 2>&1; then
  exec python "$ROOT/launcher.py" --stop
else
  # fallback
  for p in 8010 5173; do
    if command -v lsof >/dev/null 2>&1; then
      pids="$(lsof -tiTCP:$p -sTCP:LISTEN 2>/dev/null || true)"
      [[ -n "$pids" ]] && kill $pids 2>/dev/null || true
    fi
  done
  echo "已尝试停止。"
fi
