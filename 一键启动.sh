#!/usr/bin/env bash
# 顺势选股 · 一键启动（macOS / Linux）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_LOG="$ROOT/.run/backend.log"
FRONTEND_LOG="$ROOT/.run/frontend.log"
PID_DIR="$ROOT/.run"

mkdir -p "$PID_DIR"

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
info() { echo "${CYAN}▶${RESET} $*"; }
ok() { echo "${GREEN}✓${RESET} $*"; }
warn() { echo "${YELLOW}!${RESET} $*"; }
die() { echo "${RED}✗${RESET} $*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "未找到命令：$1。请先安装后再运行。"
}

cleanup() {
  echo
  info "正在停止服务..."
  [[ -f "$PID_DIR/backend.pid" ]] && kill "$(cat "$PID_DIR/backend.pid")" 2>/dev/null || true
  [[ -f "$PID_DIR/frontend.pid" ]] && kill "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
  # 子进程兜底
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT}" 2>/dev/null || true
  pkill -f "vite --host 0.0.0.0 --port ${FRONTEND_PORT}" 2>/dev/null || true
  ok "已退出"
}
trap cleanup EXIT INT TERM

echo
echo "${BOLD}顺势选股 · Role Ladder 一键启动${RESET}"
echo "----------------------------------------"

need python3
need npm
need curl

# --- 后端依赖 ---
info "检查后端虚拟环境..."
if [[ ! -d "$ROOT/backend/.venv" ]]; then
  info "创建 Python 虚拟环境并安装依赖（首次较慢）..."
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -U pip
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
else
  ok "后端虚拟环境已存在"
fi

# --- 前端依赖 ---
info "检查前端依赖..."
if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  info "npm install（首次较慢）..."
  (cd "$ROOT/frontend" && npm install)
else
  ok "前端依赖已存在"
fi

# --- 启动后端 ---
info "启动后端 http://127.0.0.1:${BACKEND_PORT}"
export PYTHONPATH="$ROOT/backend"
(
  cd "$ROOT/backend"
  exec "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
) >"$BACKEND_LOG" 2>&1 &
echo $! >"$PID_DIR/backend.pid"

# --- 启动前端 ---
info "启动前端 http://127.0.0.1:${FRONTEND_PORT}"
(
  cd "$ROOT/frontend"
  exec npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
) >"$FRONTEND_LOG" 2>&1 &
echo $! >"$PID_DIR/frontend.pid"

# --- 等待就绪 ---
info "等待服务就绪..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then
    ok "前后端均已就绪"
    break
  fi
  if [[ $i -eq 60 ]]; then
    warn "等待超时，请查看日志："
    echo "  后端: $BACKEND_LOG"
    echo "  前端: $FRONTEND_LOG"
  fi
  sleep 1
done

URL="http://127.0.0.1:${FRONTEND_PORT}"
echo
echo "${BOLD}${GREEN}启动完成${RESET}"
echo "  打开页面: ${BOLD}${URL}${RESET}"
echo "  后端 API: http://127.0.0.1:${BACKEND_PORT}/api/health"
echo "  日志目录: $PID_DIR"
echo
echo "按 Ctrl+C 停止全部服务"
echo "----------------------------------------"

# 自动打开浏览器
if command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait