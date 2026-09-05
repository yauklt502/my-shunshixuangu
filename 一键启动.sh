#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONUNBUFFERED=1
if command -v python3 >/dev/null 2>&1; then
  exec python3 ./launcher.py "$@"
fi
exec python ./launcher.py "$@"
