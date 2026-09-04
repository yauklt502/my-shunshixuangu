@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 三条纪律看板

where node >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 Node.js。
  echo 请先安装 Node.js LTS： https://nodejs.org/
  echo 安装时勾选 “Add to PATH”，然后重新打开本窗口。
  pause
  exit /b 1
)

if not exist "node_modules\iconv-lite" (
  echo 首次启动，正在安装依赖...
  call npm install --omit=dev
  if errorlevel 1 (
    echo 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
  )
)

echo.
echo 正在启动三条纪律看板...
echo 浏览器打开: http://127.0.0.1:5177/
echo 按 Ctrl+C 可停止服务
echo.
start "" "http://127.0.0.1:5177/"
node server/index.mjs
pause
