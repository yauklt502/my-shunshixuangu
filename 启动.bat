@echo off
chcp 65001 >nul 2>&1
title 真龙识别 · 盘中盯盘卡
echo.
echo   真龙识别 · 正在启动...
echo   浏览器会自动打开 http://127.0.0.1:8765/
echo   关闭此窗口即可停止服务
echo.

cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel%==0 (
    start "" "http://127.0.0.1:8765/"
    python server.py
) else (
    where python3 >nul 2>&1
    if %errorlevel%==0 (
        start "" "http://127.0.0.1:8765/"
        python3 server.py
    ) else (
        echo.
        echo   [错误] 未找到 Python，请先安装 Python 3.9+
        echo   下载地址: https://www.python.org/downloads/
        echo.
        pause
    )
)
