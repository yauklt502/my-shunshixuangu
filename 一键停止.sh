#!/usr/bin/env bash
# 顺势选股 · 一键停止（macOS / Linux）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT/.run"
BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "正在停止顺势选股服务..."

if [[ -f "$PID_DIR/backend.pid" ]]; then
  kill "$(cat "$PID_DIR/backend.pid")" 2>/dev/null || true
  kill -- -"$(cat "$PID_DIR/backend.pid")" 2>/dev/null || true
fi
if [[ -f "$PID_DIR/frontend.pid" ]]; then
  kill "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
  kill -- -"$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
fi

if command -v lsof >/dev/null 2>&1; then
  for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    [[ -n "$pids" ]] && kill $pids 2>/dev/null || true
  done
fi

pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" 2>/dev/null || true
pkill -f "vite --host 0.0.0.0 --port ${FRONTEND_PORT}" 2>/dev/null || true

rm -f "$PID_DIR/backend.pid" "$PID_DIR/frontend.pid" 2>/dev/null || true
echo "已停止（端口 ${BACKEND_PORT} / ${FRONTEND_PORT}）。"
