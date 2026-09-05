@echo off
chcp 65001 >nul
title 顺势选股 · 停止
cd /d "%~dp0"
echo 正在停止服务...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
echo 已停止。
if /I not "%~1"=="nopause" pause
