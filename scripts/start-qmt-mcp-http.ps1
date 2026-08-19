#Requires -Version 5.1
<#
.SYNOPSIS
  以 HTTP/SSE 模式启动 qmt-mcp-server（供 Cursor url 方式连接）

  使用前修改下方路径变量，并确保 miniQMT 已登录。
#>

$ErrorActionPreference = "Stop"

$QmtInstallDir   = "D:\国金QMT交易端"
$QmtAccount      = "88888888"
$QmtMcpDir       = "C:\Tools\qmt-mcp-server"
$McpApiToken     = "change-me-to-a-strong-secret"
$McpPort         = 8765

$QmtPath         = Join-Path $QmtInstallDir "userdata_mini"
$XtquantPath     = Join-Path $QmtInstallDir "bin.x64\Lib\site-packages"

$env:QMT_ACCOUNT     = $QmtAccount
$env:QMT_PATH        = $QmtPath
$env:QMT_ACCOUNT_TYPE = "STOCK"
$env:PYTHONPATH      = $XtquantPath
$env:MCP_HOST        = "127.0.0.1"
$env:MCP_PORT        = "$McpPort"
$env:MCP_API_TOKEN   = $McpApiToken

$ServerScript = Get-ChildItem -Path $QmtMcpDir -Filter "qmt-mcp-server.py" -Recurse | Select-Object -First 1
if (-not $ServerScript) { throw "未找到 qmt-mcp-server.py，请先运行 setup-qmt-windows.ps1" }

Write-Host "启动 QMT MCP HTTP 服务..."
Write-Host "  端点: http://127.0.0.1:$McpPort/sse"
Write-Host "  Token: $McpApiToken"
Write-Host "  miniQMT 路径: $QmtPath"
Write-Host ""
Write-Host "Cursor mcp.json 使用 qmt-http 条目（见 mcp.windows.json.example）"
Write-Host "按 Ctrl+C 停止服务"
Write-Host ""

python $ServerScript.FullName --http
