@echo off
REM One-click start for Windows (ASCII only). Auto-opens browser when ready.
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
echo [%DATE% %TIME%] start > "%LOG%"

REM Prefer 3.12, then 3.11, then default py -3
set "PYCMD="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1 && set "PYCMD=py -3.12" && goto :have_py
  py -3.11 -c "import sys" >nul 2>&1 && set "PYCMD=py -3.11" && goto :have_py
  py -3 -c "import sys" >nul 2>&1 && set "PYCMD=py -3" && goto :have_py
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

echo [ERROR] Python not found.
echo Install Python 3.10+ from https://www.python.org/downloads/windows/
echo Check: Add python.exe to PATH
echo.
pause
exit /b 1

:have_py
echo [OK] Using: %PYCMD%
%PYCMD% -c "import sys; print('[OK] Python', sys.version.split()[0])"
echo [%DATE% %TIME%] python=%PYCMD% >> "%LOG%"

if "%TSP_PORT%"=="" set "TSP_PORT=8765"
if "%TDX_HOST%"=="" set "TDX_HOST=115.238.90.165:7709"
set "URL=http://127.0.0.1:%TSP_PORT%"

if not exist "requirements.txt" (
  echo [ERROR] requirements.txt missing. Unzip the FULL package.
  pause
  exit /b 1
)
if not exist "backend\app.py" (
  echo [ERROR] backend\app.py missing. Run from tsp folder or use root START.cmd
  pause
  exit /b 1
)

echo [1/4] Creating / checking venv ...
if not exist ".venv\Scripts\python.exe" (
  %PYCMD% -m venv .venv >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [ERROR] venv create failed. See %LOG%
    type "%LOG%"
    pause
    exit /b 1
  )
) else (
  echo       venv already exists
)

set "VENV_PY=%CD%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [ERROR] %VENV_PY% missing
  pause
  exit /b 1
)

echo [2/4] Installing dependencies (first run 1-3 min) ...
"%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [WARN] pip failed, deleting .venv and retrying once ...
  rmdir /s /q .venv >nul 2>&1
  %PYCMD% -m venv .venv >> "%LOG%" 2>&1
  set "VENV_PY=%CD%\.venv\Scripts\python.exe"
  "%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
  "%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
)
if errorlevel 1 (
  echo [ERROR] pip install failed.
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 60"
  echo Full log: %LOG%
  echo.
  echo Tip: delete the .venv folder and run again.
  pause
  exit /b 1
)

REM optional; ignore errors on Python ^< 3.12
if exist "requirements-optional.txt" (
  "%VENV_PY%" -m pip install -r requirements-optional.txt >> "%LOG%" 2>&1
)

"%VENV_PY%" -c "import fastapi,uvicorn,httpx,eltdx; print('[OK] deps ready')" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [ERROR] Core packages missing after install. Delete .venv and retry.
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 40"
  pause
  exit /b 1
)

set "PYTHONPATH=%CD%"
set "TDX_HOST=%TDX_HOST%"
echo [3/4] Starting server: %URL%
echo [4/4] Browser will open automatically when ready.
echo.
echo *** KEEP THIS WINDOW OPEN ***
echo Press Ctrl+C to stop.
echo ----------------------------------------
echo [%DATE% %TIME%] uvicorn start >> "%LOG%"

REM Wait for health then open browser; fallback open anyway
start "" cmd /c "for /l %%i in (1,1,40) do (ping -n 2 127.0.0.1 >nul & curl -sf %URL%/api/health >nul 2>&1 && start %URL% && exit /b 0) & start %URL%"

"%VENV_PY%" -m uvicorn backend.app:app --host 127.0.0.1 --port %TSP_PORT%
set "ERR=!ERRORLEVEL!"
echo.
echo Server stopped. exit=!ERR!
echo [%DATE% %TIME%] uvicorn exit=!ERR! >> "%LOG%"
if not "!ERR!"=="0" (
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 40"
  pause
)
endlocal & exit /b %ERR%
