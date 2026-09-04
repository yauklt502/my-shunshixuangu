@echo off
setlocal
cd /d "%~dp0"
title KaiPanLa

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js 18+ is required.
  echo Download: https://nodejs.org/
  start https://nodejs.org/
  pause
  exit /b 1
)

if not exist "node_modules\" (
  echo Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)

if not exist "dist\index.html" (
  echo Building production UI...
  call npm run build
  if errorlevel 1 (
    echo npm run build failed.
    pause
    exit /b 1
  )
)

set NODE_ENV=production
set PORT=3000
set HOST=127.0.0.1
echo.
echo KaiPanLa running at http://127.0.0.1:3000
echo Close this window to stop the server.
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:3000"
node server\index.mjs
if errorlevel 1 pause
