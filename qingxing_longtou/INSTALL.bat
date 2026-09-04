@echo off
cd /d "%~dp0"
title QingXing LongTou - Install
setlocal EnableExtensions

echo ========================================
echo   Install dependencies
echo ========================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY where python3 >nul 2>nul && set "PY=python3"

if not defined PY (
  echo [ERROR] Python not found. Install Python 3.11/3.12 x64 and check PATH.
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Using: %PY%
%PY% -c "import sys; print(sys.version); print(sys.executable)"
if errorlevel 1 (
  echo [ERROR] Bad python. Disable Windows Store python aliases.
  pause
  exit /b 1
)

echo.
echo [1/2] Offline wheels (Python 3.11/3.12 preferred)...
%PY% -m pip install --upgrade pip
%PY% -m pip install --no-index --find-links="%~dp0wheels_win" -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo Offline install failed, trying online pip...
  %PY% -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
  )
)

echo.
echo [2/2] Verify imports...
%PY% -c "import requests,PIL,dotenv,tkinter; print('OK: requests/Pillow/dotenv/tkinter')"
if errorlevel 1 (
  echo [ERROR] Import check failed. tkinter missing? Reinstall Python with Tcl/Tk.
  pause
  exit /b 1
)

if not exist "%~dp0.env" (
  copy /Y "%~dp0.env.example" "%~dp0.env" >nul
  echo Created .env
)

echo.
echo DONE. Double-click START.bat to run.
pause
endlocal
exit /b 0
