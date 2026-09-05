@echo off
REM Zero-install Node fallback (no npm install).
setlocal EnableExtensions
cd /d "%~dp0"
title Three Discipline Dashboard (Node)

echo ========================================
echo   Three Discipline Dashboard
echo   Node.js start (no npm install)
echo ========================================
echo.
echo Working dir: %CD%
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js not found.
  echo Install LTS from https://nodejs.org/ and retry.
  exit /b 1
)

if not exist "server\index.mjs" (
  echo [ERROR] server\index.mjs missing. Unzip the FULL package.
  exit /b 1
)
if not exist "web\index.html" (
  echo [ERROR] web\index.html missing. Unzip the FULL package.
  exit /b 1
)

if "%TD_PORT%"=="" set "TD_PORT=5177"
set "URL=http://127.0.0.1:%TD_PORT%"
set "PORT=%TD_PORT%"

echo [OK] Node:
node -v
echo Starting: %URL%
echo.
echo *** KEEP THIS WINDOW OPEN ***
echo Press Ctrl+C to stop.
echo ----------------------------------------

start "" cmd /c "ping -n 3 127.0.0.1 >nul & start %URL%"

node server\index.mjs
set "ERR=%ERRORLEVEL%"
echo.
echo Server stopped. exit=%ERR%
endlocal & exit /b %ERR%
