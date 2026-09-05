@echo off
cd /d "%~dp0"

REM Re-open in a window that never auto-closes (fixes flash-and-gone)
if /I not "%~1"=="KEEP" (
  start "SSP" cmd /k call "%~f0" KEEP
  exit /b 0
)

title SSP
echo.
echo ========================================
echo   SSP one-click start
echo ========================================
echo.

set "PY="
where python >nul 2>nul
if not errorlevel 1 set "PY=python"
if not defined PY (
  where py >nul 2>nul
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  echo [ERROR] Python not found.
  echo Install Python 3.10+ and CHECK "Add python.exe to PATH"
  echo https://www.python.org/downloads/
  goto END
)

echo [1/4] Creating / checking venv ...
if not exist "backend\.venv\Scripts\python.exe" (
  echo       creating venv ...
  %PY% -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] venv failed
    goto END
  )
)

echo [2/4] Installing dependencies (first run 1-3 min) ...
"backend\.venv\Scripts\python.exe" -c "import uvicorn,fastapi,httpx"
if errorlevel 1 (
  "backend\.venv\Scripts\python.exe" -m pip install -U pip
  "backend\.venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] pip install failed
    goto END
  )
) else (
  echo       already installed, skip.
)

if not exist "web\index.html" (
  echo [ERROR] missing web\index.html  -- unzip the full ZIP
  goto END
)

echo [3/4] Starting server ...
echo [4/4] Opening browser ...
echo.
echo   URL must be:  http://127.0.0.1:5173
echo   Do not close this window.
echo.

set "VPY=%~dp0backend\.venv\Scripts\python.exe"
set "PYTHONPATH=%~dp0backend"

start /b "open-browser" "%VPY%" "%~dp0scripts\open_when_ready.py" "http://127.0.0.1:5173/"

cd /d "%~dp0backend"
"%VPY%" -m uvicorn app.main:app --host 0.0.0.0 --port 5173

echo.
echo Server stopped.
goto END

:END
echo.
pause
