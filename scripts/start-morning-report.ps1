# 美股 × A股 盘前晨报 — 生成并启动 HTTP 预览
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host ""
Write-Host "========================================"
Write-Host "  美股 x A股 盘前晨报"
Write-Host "  输出: E:\Cursor\reports"
Write-Host "  预览: http://127.0.0.1:8765/latest.html"
Write-Host "========================================"
Write-Host ""

python scripts/morning_report/run.py
