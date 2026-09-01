@echo off
cd /d "%~dp0"
title Shunshi Trading

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] Virtual env not found.
    echo Please run deploy.bat or 一键部署到E盘.bat first.
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
set DATA_SOURCE=eastmoney
set PYTHONIOENCODING=utf-8

echo.
echo ============================================
echo   Shunshi Trading System
echo ============================================
echo   URL  : http://127.0.0.1:8000
echo   Data : eastmoney (switch in dashboard)
echo   Stop : stop.bat or Ctrl+C
echo ============================================
echo.

start "" cmd /c "ping 127.0.0.1 -n 4 >nul & start http://127.0.0.1:8000/"
python -m src.main --mode api --host 127.0.0.1 --port 8000
echo.
pause
