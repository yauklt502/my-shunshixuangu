#Requires -Version 5.1
<#
.SYNOPSIS
  Akshare-only MCP setup for Cursor on Windows (no Tushare token required)
#>

$ErrorActionPreference = "Stop"

Write-Host "==> Akshare-only MCP setup (no Tushare token)" -ForegroundColor Cyan

function Need-Cmd($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Missing command: $name"
    }
}

Need-Cmd python
python --version

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
Need-Cmd uv

Write-Host "Installing china-a-stock-mcp..."
uv tool install --force china-a-stock-mcp

$cursorDir = Join-Path $env:USERPROFILE ".cursor"
$mcpFile = Join-Path $cursorDir "mcp.json"
$cacheDir = Join-Path $env:USERPROFILE ".cache\china-stock-mcp"

New-Item -ItemType Directory -Force -Path $cursorDir | Out-Null
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

$mcp = @{
    mcpServers = @{
        "china-stock" = @{
            command = "uvx"
            args    = @("china-a-stock-mcp")
            env     = @{
                CSM_CACHE_DIR = $cacheDir
                CSM_LOG_LEVEL = "INFO"
            }
        }
    }
}

if (Test-Path $mcpFile) {
    $backup = "$mcpFile.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $mcpFile $backup
    Write-Host "Backed up existing config: $backup"
}

($mcp | ConvertTo-Json -Depth 6) | Set-Content -Path $mcpFile -Encoding UTF8

Write-Host ""
Write-Host "Done. Wrote: $mcpFile" -ForegroundColor Green
Write-Host "Restart Cursor, then check Settings -> MCP -> china-stock is Connected."
Write-Host "Try: 用 MCP 查 600519 近 60 日 K 线和 MACD"
