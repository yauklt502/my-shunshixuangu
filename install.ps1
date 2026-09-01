# Shunshi Trading - PowerShell deploy (use if .bat double-click fails)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "============================================"
Write-Host "  Shunshi Trading - PowerShell Deploy"
Write-Host "============================================"
Write-Host ""

$Target = if (Test-Path "E:\") { "E:\shunshi-trading" } elseif (Test-Path "D:\") { "D:\shunshi-trading" } else { "C:\shunshi-trading" }
$Source = $PSScriptRoot

Write-Host "Target: $Target"
Write-Host "Source: $Source"
Write-Host ""

New-Item -ItemType Directory -Force -Path $Target | Out-Null

Write-Host "[1/4] Copy files..."
robocopy $Source $Target /E /XD .git .venv __pycache__ .cache data /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "Copy failed: $LASTEXITCODE" }

Write-Host "[2/4] Find Python..."
$py = $null
if (Get-Command python -ErrorAction SilentlyContinue) { $py = "python" }
elseif (Get-Command py -ErrorAction SilentlyContinue) { $py = "py -3" }
else { throw "Python not found. Install from https://www.python.org/downloads/" }

Write-Host "[3/4] Create venv + install..."
Set-Location $Target
if (-not (Test-Path ".venv\Scripts\python.exe")) { Invoke-Expression "$py -m venv .venv" }
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
$env:PIP_DEFAULT_TIMEOUT = "120"
Write-Host "       使用清华镜像，首次约 1-3 分钟，请勿关闭..."
& ".venv\Scripts\pip.exe" install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --prefer-binary
if ($LASTEXITCODE -ne 0) {
    Write-Host "       清华镜像失败，尝试阿里云..."
    & ".venv\Scripts\pip.exe" install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com --prefer-binary
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "       尝试官方 PyPI..."
    & ".venv\Scripts\pip.exe" install -r requirements.txt --prefer-binary
}
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "[4/4] Done"
Write-Host ""
Write-Host "Deploy OK: $Target"
Write-Host "Run: $Target\start.bat"
Write-Host "URL: http://127.0.0.1:8000"
Write-Host ""
$ans = Read-Host "Start now? (Y/N)"
if ($ans -eq "Y" -or $ans -eq "y") { Start-Process "$Target\start.bat" }
Read-Host "Press Enter to exit"
