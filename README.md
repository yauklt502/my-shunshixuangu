# A-share MCP Setup

Cursor MCP configuration for A-share analysis in three layers:

- **A** Research: `china-stock-mcp`, `tushare-mcp-server`, optional `ashare-mcp`
- **B** Broker/Quant: `qmt-mcp-server`, optional `myquant-mcp` (local only)
- **C** Self-hosted: `mcp-servers/my-data-server`

## Quick start

```bash
cp .env.example .env          # fill in tokens
bash scripts/setup-mcp.sh     # install runtimes
cp .cursor/mcp.json.example ~/.cursor/mcp.json
# edit placeholders, restart Cursor
```

Start the self-hosted server (C layer):

```bash
cd mcp-servers/my-data-server
export MY_DATA_MCP_TOKEN='your-secret'
uv run my-data-server
```

Remove unused `mcpServers` entries from `~/.cursor/mcp.json` if a service is not running.
