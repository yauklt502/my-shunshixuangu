#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo "  顺势选股 · 龙头确认 本地启动"
echo "========================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未找到 python3，请先安装 Python 3.10+"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[1/3] 创建虚拟环境..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 安装/更新依赖..."
python -m pip install -U pip -q
if ! python -m pip install -r requirements.txt; then
  echo "[提示] 默认源失败，尝试清华镜像..."
  python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

export PYTHONPATH="$(pwd)"
PORT="${PORT:-8654}"

echo "[3/3] 启动服务 http://127.0.0.1:${PORT}"
echo "浏览器打开上述地址；按 Ctrl+C 可停止"
echo
exec python -m uvicorn server:app --host 127.0.0.1 --port "${PORT}"
