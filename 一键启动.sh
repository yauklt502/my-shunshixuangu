#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/launcher.py" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$ROOT/launcher.py" "$@"
else
  echo "未找到 Python3。请先安装 Python 3.10+"
  exit 1
fi
