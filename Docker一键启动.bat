@echo off
chcp 65001 >nul
title 顺势选股 · Docker 一键启动
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Docker。请先安装 Docker Desktop：
  echo https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

echo 正在用 Docker 构建并启动（首次较慢）...
docker compose up --build -d
if errorlevel 1 (
  echo [错误] docker compose 失败
  pause
  exit /b 1
)

echo.
echo 启动完成：http://127.0.0.1:5173
echo 停止：docker compose down
start "" "http://127.0.0.1:5173"
pause
