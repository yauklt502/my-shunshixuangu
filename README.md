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

## Windows + miniQMT

Use `.cursor/mcp.windows.json.example` and `.env.windows.example`.

```powershell
# 1) 修改 scripts/setup-qmt-windows.ps1 顶部路径变量
# 2) 以管理员或普通 PowerShell 运行：
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\setup-qmt-windows.ps1

# 可选 HTTP 模式（与 stdio 二选一）：
.\scripts\start-qmt-mcp-http.ps1
```

Cursor config path on Windows: `%USERPROFILE%\.cursor\mcp.json`

miniQMT checklist:
- Login with「极简模式 / 独立交易模式」
- Keep miniQMT running in background
- Set `QMT_PATH` to `...\userdata_mini`
- Set `PYTHONPATH` to `...\bin.x64\Lib\site-packages`

## Akshare only (no Tushare token)

```powershell
.\scripts\setup-akshare-only-windows.ps1
```

Or copy `.cursor/mcp.akshare-only.windows.json.example` to `%USERPROFILE%\.cursor\mcp.json`.
