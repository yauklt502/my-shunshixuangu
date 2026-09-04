# Shunshi Leader Confirm - Windows PowerShell launcher
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "========================================"
Write-Host " Shunshi Leader Confirm - Local Start"
Write-Host "========================================"

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "[ERROR] Python not found. Install Python 3.10+ and add to PATH."
  Write-Host "https://www.python.org/downloads/"
  Read-Host "Press Enter to exit"
  exit 1
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "[1/3] Creating virtual environment..."
  python -m venv .venv
}

Write-Host "[2/3] Installing dependencies..."
& ".venv\Scripts\python.exe" -m pip install -U pip
try {
  & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
} catch {
  Write-Host "[WARN] Default PyPI failed, trying Tsinghua mirror..."
  & ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
}

& ".venv\Scripts\python.exe" -m pip install tzdata | Out-Null

$env:PYTHONPATH = (Get-Location).Path
$port = 8654

Write-Host "[3/4] Preflight import check..."
& ".venv\Scripts\python.exe" -c "import server; print('import ok')"

Write-Host "[4/4] Starting server http://127.0.0.1:$port"
Write-Host "Keep this window OPEN while using. Press Ctrl+C to stop."
try {
  & ".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port $port
} finally {
  Write-Host ""
  Write-Host "Server stopped. If there was an error, read the traceback above."
  Read-Host "Press Enter to close"
}