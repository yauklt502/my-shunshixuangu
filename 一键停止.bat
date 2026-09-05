@echo off
chcp 65001 >nul
title 顺势选股 · 停止服务
cd /d "%~dp0"

set BACKEND_PORT=8010
set FRONTEND_PORT=5173

echo 正在停止后端 / 前端进程...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul

taskkill /FI "WINDOWTITLE eq SSP-Backend*" /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq SSP-Frontend*" /F >nul 2>nul

echo 已尝试停止 %BACKEND_PORT% / %FRONTEND_PORT% 端口服务。
if /I "%~1"=="nopause" goto :eof
pause
