@echo off
setlocal EnableExtensions
chcp 65001 >nul
title 短线寻龙
cd /d "%~dp0"

echo.
echo  ========================================
echo    短线寻龙 · 同花顺金融数据终端
echo  ========================================
echo.

call :find_runtime
if errorlevel 1 (
  echo 未找到 Python 或 Node.js。
  echo 请先安装其中一个，并勾选 Add to PATH：
  echo   Python  https://www.python.org/downloads/
  echo   Node.js https://nodejs.org/
  echo.
  pause
  exit /b 1
)

echo 正在打开浏览器 http://127.0.0.1:8010/  （短线寻龙，避开顺势选股的 8000 端口）
start "" "http://127.0.0.1:8010/"
echo 关闭本窗口即停止服务。
echo.

if /I "%RUNTIME%"=="python" (
  "%PY%" serve.py
) else (
  "%NODE%" serve.js
)
echo.
pause
exit /b 0

:find_runtime
set "RUNTIME="
set "PY="
set "NODE="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py"
if defined PY (
  set "RUNTIME=python"
  exit /b 0
)
where node >nul 2>&1 && set "NODE=node"
if defined NODE (
  set "RUNTIME=node"
  exit /b 0
)
exit /b 1
