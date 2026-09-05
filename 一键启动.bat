@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title 顺势选股
cd /d "%~dp0"

echo.
echo ========================================
echo   顺势选股 · 一键启动
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
  echo [ERROR] 未找到 Python。请安装 Python 3.10+ 并勾选 Add python.exe to PATH
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)

echo [1/4] Creating / checking venv ...
if not exist "backend\.venv\Scripts\python.exe" (
  %PY% -m venv backend\.venv
  if errorlevel 1 (
    echo [ERROR] 创建虚拟环境失败
    pause
    exit /b 1
  )
)

echo [2/4] Installing dependencies (first run 1-3 min) ...
backend\.venv\Scripts\python.exe -c "import uvicorn,fastapi,httpx" 2>nul
if errorlevel 1 (
  backend\.venv\Scripts\python.exe -m pip install -U pip
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo [ERROR] 依赖安装失败
    pause
    exit /b 1
  )
) else (
  echo       already installed, skip.
)

if not exist "web\index.html" (
  echo [ERROR] 缺少 web\index.html，请重新解压完整 ZIP
  pause
  exit /b 1
)

echo [3/4] Starting server ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
set "PYTHONPATH=%~dp0backend"
if not exist ".run" mkdir ".run"

echo [4/4] Opening browser ...
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start "" http://127.0.0.1:5173/"

echo.
echo   URL: http://127.0.0.1:5173
echo   请不要关闭本窗口。
echo.

cd /d "%~dp0backend"
"%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 5173
echo.
echo 服务已结束。
pause
