@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Shunshi Leader Confirm - Local Start
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ and check "Add to PATH".
  echo Download: https://www.python.org/downloads/
  goto :END
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    goto :END
  )
)

echo [2/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -U pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [WARN] Default PyPI failed, trying Tsinghua mirror...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo [ERROR] pip install failed
    goto :END
  )
)

set "PYTHONPATH=%CD%"
set "PORT=8765"

echo [3/3] Starting server...
echo Open browser: http://127.0.0.1:%PORT%
echo Press Ctrl+C to stop.
echo.

".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port %PORT%

:END
echo.
pause
endlocal
