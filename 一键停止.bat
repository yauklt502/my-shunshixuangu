@echo off
chcp 65001 >nul
title 顺势选股 · 停止服务
cd /d "%~dp0"

echo 正在停止后端 / 前端进程...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul

taskkill /FI "WINDOWTITLE eq SSP-Backend*" /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq SSP-Frontend*" /F >nul 2>nul

echo 已尝试停止 8010 / 5173 端口服务。
pause