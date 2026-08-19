#Requires -Version 5.1
<#
.SYNOPSIS
  Windows miniQMT + qmt-mcp-server 一键准备脚本

.DESCRIPTION
  1. 检查 Python / miniQMT / xtquant
  2. clone qmt-mcp-server（若不存在）
  3. 生成 %USERPROFILE%\.cursor\mcp.json（基于 Windows 模板）

  使用前请：
  - 已安装并登录 miniQMT（勾选「极简模式 / 独立交易模式」）
  - 券商已开通程序化交易权限
  - 修改脚本顶部的路径变量
#>

$ErrorActionPreference = "Stop"

# ========== 按你的环境修改 ==========
$QmtInstallDir   = "D:\国金QMT交易端"
$QmtAccount      = "88888888"
$QmtMcpDir       = "C:\Tools\qmt-mcp-server"
$QmtMcpRepo      = "https://github.com/beamof/qmt-mcp-server.git"
$TushareToken    = "YOUR_TUSHARE_TOKEN"
# ====================================

$QmtPath         = Join-Path $QmtInstallDir "userdata_mini"
$XtquantPath     = Join-Path $QmtInstallDir "bin.x64\Lib\site-packages"
$CursorMcpDir    = Join-Path $env:USERPROFILE ".cursor"
$CursorMcpFile   = Join-Path $CursorMcpDir "mcp.json"
$ProjectRoot     = Split-Path $PSScriptRoot -Parent
$TemplateFile    = Join-Path $ProjectRoot ".cursor\mcp.windows.json.example"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

Write-Step "检查 Python"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw "未找到 python，请先安装 Python 3.10+ 并勾选 Add to PATH" }
python --version

Write-Step "检查 miniQMT 路径"
if (-not (Test-Path $QmtPath)) {
    throw "找不到 userdata_mini: $QmtPath`n请修改脚本中的 `$QmtInstallDir"
}
Write-Host "QMT_PATH OK: $QmtPath"

Write-Step "检查 xtquant"
$env:PYTHONPATH = $XtquantPath
python -c "import xtquant; print('xtquant OK:', xtquant.__file__)"
if ($LASTEXITCODE -ne 0) {
    throw "xtquant 导入失败。请确认 miniQMT 已安装，或执行: pip install xtquant"
}

Write-Step "准备 qmt-mcp-server"
if (-not (Test-Path $QmtMcpDir)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $QmtMcpDir) | Out-Null
    git clone $QmtMcpRepo $QmtMcpDir
} else {
    Write-Host "已存在: $QmtMcpDir"
}

$ServerScript = Get-ChildItem -Path $QmtMcpDir -Filter "qmt-mcp-server.py" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $ServerScript) {
    throw "在 $QmtMcpDir 未找到 qmt-mcp-server.py，请检查仓库结构"
}
Write-Host "MCP 脚本: $($ServerScript.FullName)"

Write-Step "写入 Cursor MCP 配置"
New-Item -ItemType Directory -Force -Path $CursorMcpDir | Out-Null

$mcp = @{
    mcpServers = @{
        "china-stock" = @{
            command = "uvx"
            args    = @("china-a-stock-mcp[tushare]")
            env     = @{
                CSM_TUSHARE_TOKEN = $TushareToken
                CSM_CACHE_DIR     = "$env:USERPROFILE\.cache\china-stock-mcp"
                CSM_LOG_LEVEL     = "INFO"
            }
        }
        "tushare" = @{
            command = "npx"
            args    = @("-y", "tushare-mcp-server")
            env     = @{
                TUSHARE_TOKEN = $TushareToken
            }
        }
        "qmt" = @{
            command = "python"
            args    = @($ServerScript.FullName)
            env     = @{
                QMT_ACCOUNT          = $QmtAccount
                QMT_PATH             = $QmtPath
                QMT_ACCOUNT_TYPE     = "STOCK"
                PYTHONPATH           = $XtquantPath
            }
        }
    }
}

if (Test-Path $CursorMcpFile) {
    $backup = "$CursorMcpFile.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $CursorMcpFile $backup
    Write-Host "已备份旧配置: $backup"
}

($mcp | ConvertTo-Json -Depth 8) | Set-Content -Path $CursorMcpFile -Encoding UTF8
Write-Host "已写入: $CursorMcpFile"

Write-Step "完成"
Write-Host @"

下一步：
1. 保持 miniQMT 登录（极简模式）
2. 重启 Cursor
3. Settings -> MCP -> 确认 china-stock / tushare / qmt 为 Connected
4. 在对话中测试：「用 QMT MCP 查我的账户持仓」

若 qmt 连接失败，检查：
- miniQMT 是否已启动并登录账号 $QmtAccount
- QMT_PATH 是否指向 userdata_mini
- PYTHONPATH 是否包含 xtquant 目录

HTTP 模式（可选）：运行 scripts\start-qmt-mcp-http.ps1
"@
