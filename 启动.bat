@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 三条纪律看板

echo.
echo  ========================================
echo    三条纪律看板
echo  ========================================
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo 未找到 Node.js。请先安装并勾选 Add to PATH：
  echo   https://nodejs.org/
  echo.
  pause
  exit /b 1
)

echo 正在打开浏览器 http://127.0.0.1:5177/
echo 关闭本窗口即停止服务。
echo.
start "" "http://127.0.0.1:5177/"
node server\index.mjs
echo.
pause
