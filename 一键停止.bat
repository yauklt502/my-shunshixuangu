@echo off
chcp 65001 >nul
title 顺势选股 · 停止服务
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py --stop
  goto :done
)
where python >nul 2>nul
if not errorlevel 1 (
  python launcher.py --stop
  goto :done
)

REM fallback: kill by port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8010" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>nul
echo 已尝试按端口停止。

:done
if /I "%~1"=="nopause" goto :eof
pause
