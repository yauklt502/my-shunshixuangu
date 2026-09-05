#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/launcher.py" --stop
elif command -v python >/dev/null 2>&1; then
  exec python "$ROOT/launcher.py" --stop
else
  echo "未找到 Python3"
  exit 1
fi
