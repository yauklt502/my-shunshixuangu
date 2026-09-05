#!/usr/bin/env bash
# 先比独 · Tick Stock Panel 一键启动
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
PORT="${TSP_PORT:-8765}"
URL="http://127.0.0.1:${PORT}"

echo "========================================"
echo "  先比独 · Tick Stock Panel 一键启动"
echo "========================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未找到 python3，请先安装 Python 3.10+"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "[1/4] 创建虚拟环境…"
  python3 -m venv .venv
else
  echo "[1/4] 虚拟环境已存在"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/4] 安装依赖（首次较慢）…"
pip install -q -U pip
pip install -q -r requirements.txt

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export TDX_HOST="${TDX_HOST:-115.238.90.165:7709}"

# 若端口被占用，先尝试结束旧进程（仅本机本端口）
if command -v lsof >/dev/null 2>&1; then
  OLD_PID="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${OLD_PID}" ]]; then
    echo "[提示] 端口 ${PORT} 被占用，结束旧进程 ${OLD_PID}"
    kill ${OLD_PID} 2>/dev/null || true
    sleep 1
  fi
fi

echo "[3/4] 启动服务 ${URL}"
echo "[4/4] 浏览器将自动打开（若未打开请手动访问上面地址）"
echo "按 Ctrl+C 可停止服务"
echo "----------------------------------------"

# 后台延迟打开浏览器
(
  for _ in 1 2 3 4 5 6 7 8 9 10; do
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
