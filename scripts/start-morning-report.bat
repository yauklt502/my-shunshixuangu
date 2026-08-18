@echo off
chcp 65001 >nul
title A股晨报 - HTTP 预览服务
cd /d "%~dp0.."

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo ========================================
echo   美股 x A股 盘前晨报
echo   输出目录: E:\Cursor\reports
echo   预览地址: http://127.0.0.1:8765/latest.html
echo ========================================
echo.

python scripts\morning_report\run.py
pause
