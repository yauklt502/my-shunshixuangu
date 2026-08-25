#!/usr/bin/env bash
# Generate Cursor MCP config for Fuyao from .env / FUYAO_API_KEY.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

KEY="${FUYAO_API_KEY:-${API_KEY:-}}"
if [[ -z "$KEY" || "$KEY" == sk-fuyao-your-key-here ]]; then
  echo "Set FUYAO_API_KEY in .env first (cp .env.example .env)." >&2
  exit 2
fi

write_mcp() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  cat >"$dest" <<EOF
{
  "mcpServers": {
    "fuyao-a-share": {
      "type": "http",
      "url": "https://fuyao.aicubes.cn/mcp/a-share",
      "headers": {
        "X-api-key": "${KEY}"
      }
    },
    "fuyao-a-share-index": {
      "type": "http",
      "url": "https://fuyao.aicubes.cn/mcp/a-share-index",
      "headers": {
        "X-api-key": "${KEY}"
      }
    },
    "fuyao-fund": {
      "type": "http",
      "url": "https://fuyao.aicubes.cn/mcp/fund",
      "headers": {
        "X-api-key": "${KEY}"
      }
    },
    "fuyao-meta": {
      "type": "http",
      "url": "https://fuyao.aicubes.cn/mcp/meta",
      "headers": {
        "X-api-key": "${KEY}"
      }
    }
  }
}
EOF
  echo "Wrote $dest"
}

write_mcp "$ROOT/.cursor/mcp.json"
write_mcp "${HOME}/.cursor/mcp.json"

echo
echo "Done. Restart Cursor (or reload MCP) so fuyao-* servers show Connected."
echo "Then ask: 「贵州茅台今天涨多少？」"
