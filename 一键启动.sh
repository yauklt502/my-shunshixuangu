#!/usr/bin/env bash
# 顺势选股 · 一键启动（macOS / Linux）
# 用法：双击 一键启动.command，或终端执行 ./一键启动.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PID_DIR="$ROOT/.run"
BACKEND_LOG="$PID_DIR/backend.log"
FRONTEND_LOG="$PID_DIR/frontend.log"

mkdir -p "$PID_DIR"

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; CYAN=$'\033[36m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
info() { echo "${CYAN}▶${RESET} $*"; }
ok() { echo "${GREEN}✓${RESET} $*"; }
warn() { echo "${YELLOW}!${RESET} $*"; }
die() { echo "${RED}✗${RESET} $*" >&2; exit 1; }

need() {
  command -v "$1" >/dev/null 2>&1 || die "未找到命令：$1。请先安装后再运行。"
}

port_busy() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :$port" 2>/dev/null | grep -q ":$port"
  else
    return 1
  fi
}

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    [[ -n "$pids" ]] && kill $pids 2>/dev/null || true
  fi
  pkill -f "uvicorn app.main:app --host 0.0.0.0 --port ${port}" 2>/dev/null || true
  pkill -f "vite --host 0.0.0.0 --port ${port}" 2>/dev/null || true
}

cleanup() {
  echo
  info "正在停止服务..."
  [[ -f "$PID_DIR/backend.pid" ]] && kill "$(cat "$PID_DIR/backend.pid")" 2>/dev/null || true
  [[ -f "$PID_DIR/frontend.pid" ]] && kill "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
  # 杀进程组，避免 npm/vite 子进程残留
  if [[ -f "$PID_DIR/backend.pid" ]]; then
    kill -- -"$(cat "$PID_DIR/backend.pid")" 2>/dev/null || true
  fi
  if [[ -f "$PID_DIR/frontend.pid" ]]; then
    kill -- -"$(cat "$PID_DIR/frontend.pid")" 2>/dev/null || true
  fi
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
  rm -f "$PID_DIR/backend.pid" "$PID_DIR/frontend.pid"
  ok "已退出"
}
trap cleanup EXIT INT TERM

echo
echo "${BOLD}顺势选股 · Role Ladder 一键启动${RESET}"
echo "----------------------------------------"

need python3
need npm

# python3 -m venv 需要 ensurepip；部分系统用 python3.12 等
PY=python3
need curl

# 端口占用时先清理旧实例，保证「再点一次也能启动」
if port_busy "$BACKEND_PORT" || port_busy "$FRONTEND_PORT"; then
  warn "检测到端口占用，正在清理旧进程..."
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
  sleep 1
fi

# --- 后端依赖 ---
info "检查后端虚拟环境..."
if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  info "创建 Python 虚拟环境并安装依赖（首次较慢）..."
  "$PY" -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -U pip
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
else
  ok "后端虚拟环境已存在"
  # 轻量自愈：缺 uvicorn 时补装
  if ! "$ROOT/backend/.venv/bin/python" -c "import uvicorn" 2>/dev/null; then
    info "补装后端依赖..."
    "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
  fi
fi

# --- 前端依赖 ---
info "检查前端依赖..."
if [[ ! -d "$ROOT/frontend/node_modules/vite" ]]; then
  info "npm install（首次较慢）..."
  (cd "$ROOT/frontend" && npm install)
else
  ok "前端依赖已存在"
fi

# --- 启动后端（必须在当前 shell 后台启动，勿用 $() 子进程）---
info "启动后端 http://127.0.0.1:${BACKEND_PORT}"
: >"$BACKEND_LOG"
export PYTHONPATH="$ROOT/backend"
(
  cd "$ROOT/backend"
  if command -v setsid >/dev/null 2>&1; then
    exec setsid "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
  else
    exec "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$BACKEND_PORT"
  fi
) >"$BACKEND_LOG" 2>&1 &
echo $! >"$PID_DIR/backend.pid"

# --- 启动前端 ---
info "启动前端 http://127.0.0.1:${FRONTEND_PORT}"
: >"$FRONTEND_LOG"
(
  cd "$ROOT/frontend"
  if command -v setsid >/dev/null 2>&1; then
    exec setsid npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
  else
    exec npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
  fi
) >"$FRONTEND_LOG" 2>&1 &
echo $! >"$PID_DIR/frontend.pid"

# --- 等待就绪 ---
info "等待服务就绪..."
READY=0
for i in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/api/health" >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1:${FRONTEND_PORT}/" >/dev/null 2>&1; then
    READY=1
    ok "前后端均已就绪"
    break
  fi
  # 提前失败：进程已挂
  if ! kill -0 "$(cat "$PID_DIR/backend.pid")" 2>/dev/null; then
    warn "后端启动失败，最近日志："
    tail -n 40 "$BACKEND_LOG" || true
    die "后端未能启动"
  fi
  if ! kill -0 "$(cat "$PID_DIR/frontend.pid")" 2>/dev/null; then
    warn "前端启动失败，最近日志："
    tail -n 40 "$FRONTEND_LOG" || true
    die "前端未能启动"
  fi
  sleep 1
done

if [[ "$READY" -ne 1 ]]; then
  warn "等待超时，请查看日志："
  echo "  后端: $BACKEND_LOG"
  echo "  前端: $FRONTEND_LOG"
  die "服务未在预期时间内就绪"
fi

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
