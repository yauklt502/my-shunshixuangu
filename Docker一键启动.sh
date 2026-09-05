#!/usr/bin/env bash
# Docker 一键启动（需已安装 Docker）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

command -v docker >/dev/null 2>&1 || { echo "未找到 Docker，请先安装 Docker Desktop"; exit 1; }

echo "正在用 Docker 构建并启动（首次较慢）..."
docker compose up --build -d

URL="http://127.0.0.1:5173"
echo
echo "启动完成：$URL"
echo "停止：docker compose down"
if command -v open >/dev/null 2>&1; then open "$URL" || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" || true
fi
