@echo off
chcp 65001 >nul
setlocal EnableExtensions

set "OUT_DIR=E:\Cursor\reports"
set "REPO_ROOT=%~dp0.."
cd /d "%REPO_ROOT%"

echo.
echo ========================================
echo   生成晨报到 E:\Cursor\reports
echo ========================================
echo.

if not exist "%OUT_DIR%" (
    echo [1/3] 创建目录 %OUT_DIR%
    mkdir "%OUT_DIR%" 2>nul
    if not exist "%OUT_DIR%" (
        echo [错误] 无法创建 %OUT_DIR%
        echo 请手动新建文件夹 E:\Cursor\reports 后重试
        pause
        exit /b 1
    )
) else (
    echo [1/3] 目录已存在: %OUT_DIR%
)

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo [错误] 未找到 Python。请安装 https://www.python.org/downloads/
    echo 安装时勾选 "Add python.exe to PATH"
    pause
    exit /b 1
)

echo [2/3] 使用: %PY%
echo [3/3] 正在生成 HTML...
echo.

%PY% scripts\morning_report\run.py --output "%OUT_DIR%" --generate-only --no-browser
if errorlevel 1 (
    echo.
    echo [错误] 生成失败，请把上面报错截图发给我
    pause
    exit /b 1
)

echo.
if exist "%OUT_DIR%\latest.html" (
    echo [成功] 已生成:
    echo   %OUT_DIR%\latest.html
    echo.
    echo 正在用浏览器打开...
    start "" "%OUT_DIR%\latest.html"
) else (
    echo [错误] 生成完成但未找到 latest.html，请检查权限
    pause
    exit /b 1
)

echo.
echo 如需 HTTP 预览，再运行: scripts\start-morning-report.bat
pause
