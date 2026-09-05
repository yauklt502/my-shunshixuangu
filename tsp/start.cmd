@echo off
REM Tick Stock Panel one-click start (ASCII-only, Windows-safe)
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title XianBiDu Tick Stock Panel

echo ========================================
echo   XianBiDu / Tick Stock Panel
echo   One-click start
echo ========================================
echo.
echo Working dir: %CD%
echo.

set "LOG=%CD%\startup.log"
echo [%DATE% %TIME%] start > "%LOG%" 2>&1

REM ---- find Python (skip Windows Store stub) ----
set "PYCMD="
where py >nul 2>&1
if not errorlevel 1 (
  set "PYCMD=py -3"
  goto :have_py
)

where python >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    echo %%I | findstr /i "WindowsApps\\python.exe" >nul
    if errorlevel 1 (
      set "PYCMD=%%I"
      goto :have_py
    )
  )
)

echo [ERROR] Python not found on PATH.
echo.
echo Install Python 3.10+ :
echo   https://www.python.org/downloads/windows/
echo.
echo On the installer first screen, CHECK:
echo   [x] Add python.exe to PATH
echo Then reopen this window and run again.
echo.
echo [%DATE% %TIME%] no python >> "%LOG%"
echo.
pause
exit /b 1

:have_py
echo [OK] Using: %PYCMD%
echo [%DATE% %TIME%] python=%PYCMD% >> "%LOG%"

if "%TSP_PORT%"=="" set "TSP_PORT=8765"
if "%TDX_HOST%"=="" set "TDX_HOST=115.238.90.165:7709"
set "URL=http://127.0.0.1:%TSP_PORT%"

if not exist "requirements.txt" (
  echo [ERROR] requirements.txt missing.
  echo Make sure you unzipped the FULL folder.
  echo Current: %CD%
  pause
  exit /b 1
)

if not exist "backend\app.py" (
  echo [ERROR] backend\app.py missing.
  echo You must run this from the tsp folder, or use START.cmd in the repo root.
  pause
  exit /b 1
)

echo [1/4] Creating / checking venv ...
if not exist ".venv\Scripts\python.exe" (
  %PYCMD% -m venv .venv >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    echo Often caused by missing Python or no write permission.
    echo See: %LOG%
    type "%LOG%"
    pause
    exit /b 1
  )
) else (
  echo       venv already exists
)

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv\Scripts\python.exe still missing after venv create.
  pause
  exit /b 1
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
echo [2/4] Installing dependencies (first run 1-3 min, please wait) ...
"%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] pip install failed.
  echo ----------------------------------------
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 50"
  echo ----------------------------------------
  echo Full log: %LOG%
  pause
  exit /b 1
)

set "PYTHONPATH=%CD%"
set "TDX_HOST=%TDX_HOST%"
echo [3/4] Starting server: %URL%
echo [4/4] Browser opens in ~3 seconds.
echo.
echo *** KEEP THIS WINDOW OPEN ***
echo Press Ctrl+C to stop the server.
echo ----------------------------------------
echo [%DATE% %TIME%] uvicorn start port=%TSP_PORT% >> "%LOG%"

start "" cmd /c "ping -n 4 127.0.0.1 >nul & start %URL%"

"%VENV_PY%" -m uvicorn backend.app:app --host 127.0.0.1 --port %TSP_PORT%
set "ERR=!ERRORLEVEL!"
echo.
echo Server stopped. exit code=!ERR!
echo [%DATE% %TIME%] uvicorn exit=!ERR! >> "%LOG%"
if not "!ERR!"=="0" (
  echo.
  echo Something went wrong. Last log lines:
  echo ----------------------------------------
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 40"
  echo ----------------------------------------
)
echo.
pause
endlocal
exit /b %ERR%
