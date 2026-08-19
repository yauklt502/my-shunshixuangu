#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURSOR_DIR="${HOME}/.cursor"
MCP_CONFIG="${CURSOR_DIR}/mcp.json"

echo "==> A-share MCP setup (A research + B broker + C self-hosted)"
echo

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

echo "[1/5] Checking prerequisites..."
need_cmd python3
need_cmd node
need_cmd npm

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi
need_cmd uv

echo
echo "[2/5] Installing A-layer MCP runtimes..."
uv tool install --force china-a-stock-mcp[tushare] || true
npm install -g tushare-mcp-server || true

echo
echo "[3/5] Installing C-layer self-hosted MCP server..."
cd "${ROOT}/mcp-servers/my-data-server"
uv sync

echo
echo "[4/5] Creating Cursor MCP config..."
mkdir -p "${CURSOR_DIR}"
if [[ -f "${MCP_CONFIG}" ]]; then
  backup="${MCP_CONFIG}.bak.$(date +%Y%m%d-%H%M%S)"
  cp "${MCP_CONFIG}" "${backup}"
  echo "Backed up existing config to ${backup}"
fi

if [[ ! -f "${ROOT}/.cursor/mcp.json" ]]; then
  cp "${ROOT}/.cursor/mcp.json.example" "${MCP_CONFIG}"
  echo "Created ${MCP_CONFIG} from template."
  echo "Edit it and replace YOUR_TUSHARE_TOKEN and other placeholders."
else
  echo "Project-local .cursor/mcp.json already exists; skipped global copy."
fi

echo
echo "[5/5] Optional services to start manually:"
cat <<'EOF'

A层 - 研究（stdio，Cursor 自动拉起，无需手动启动）:
  - china-stock  -> uvx china-a-stock-mcp[tushare]
  - tushare      -> npx -y tushare-mcp-server

A层 - 可选 ashare HTTP:
  git clone https://github.com/CharmYue/ashare-mcp
  cd ashare-mcp && uv sync && uv run ashare-mcp --transport streamable-http

B层 - miniQMT（本机）:
  git clone https://github.com/beamof/qmt-mcp-server
  # 配置 QMT_PATH / QMT_ACCOUNT / MCP_API_TOKEN 后启动 HTTP 服务

B层 - 掘金（本机）:
  git clone https://github.com/Wangshengyang2004/myquant-mcp
  # 启动后 Cursor 连接 http://127.0.0.1:8001/mcp/

C层 - 自建数据服务:
  cd mcp-servers/my-data-server
  export MY_DATA_MCP_TOKEN='change-me'
  uv run my-data-server

Then restart Cursor -> Settings -> MCP -> verify green Connected status.
EOF

echo
echo "Done."
