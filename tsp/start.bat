@echo off
chcp 65001 >nul
cd /d %~dp0
setlocal
title 先比独 · Tick Stock Panel 一键启动

echo ========================================
echo   先比独 · Tick Stock Panel 一键启动
echo ========================================

where py >nul 2>&1
if %errorlevel%==0 (
  set PY=py -3
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set PY=python
  ) else (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
  )
)

if "%TSP_PORT%"=="" set TSP_PORT=8765
if "%TDX_HOST%"=="" set TDX_HOST=115.238.90.165:7709
set URL=http://127.0.0.1:%TSP_PORT%

if not exist .venv (
  echo [1/4] 创建虚拟环境…
  %PY% -m venv .venv
) else (
  echo [1/4] 虚拟环境已存在
)

call .venv\Scripts\activate.bat
echo [2/4] 安装依赖（首次较慢）…
python -m pip install -q -U pip
pip install -q -r requirements.txt

set PYTHONPATH=%cd%

echo [3/4] 启动服务 %URL%
echo [4/4] 即将自动打开浏览器
echo 按 Ctrl+C 可停止服务
echo ----------------------------------------

start "" cmd /c "timeout /t 2 /nobreak >nul & start %URL%"
python -m uvicorn backend.app:app --host 127.0.0.1 --port %TSP_PORT%
if errorlevel 1 pause
endlocal
