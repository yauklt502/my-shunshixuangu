@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python3 >nul 2>&1 && set "PY=python3"

if not defined PY (
    echo.
    echo [ERROR] Python 3.9+ not found.
    echo Install: https://www.python.org/downloads/
    echo Tick "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
)

echo.
echo Zhenlong review server starting...
echo Browser will open: http://127.0.0.1:8765/
echo Close this window to stop.
echo.

%PY% server.py --open
if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start.
    pause
    exit /b 1
)
