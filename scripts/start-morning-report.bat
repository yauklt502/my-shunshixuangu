@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "OUT_DIR=E:\Cursor\reports"
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo [错误] 未找到 Python，请先运行 scripts\generate-report-to-e-cursor.bat 查看安装提示
    pause
    exit /b 1
)

if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

echo.
echo ========================================
echo   美股 x A股 盘前晨报 - HTTP 预览
echo   输出: %OUT_DIR%
echo   地址: http://127.0.0.1:8765/latest.html
echo ========================================
echo.

%PY% scripts\morning_report\run.py --output "%OUT_DIR%"
pause
