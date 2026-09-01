@echo off
chcp 65001 >nul
title 停止顺时选股服务
echo 正在停止 8000 端口服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
echo 已停止。
timeout /t 2 >nul
