@echo off
chcp 65001 >nul
title 顺势选股 · 一键启动
cd /d "%~dp0"

echo.
echo 正在启动顺势选股（请保持本窗口打开）...
echo.

where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py
  goto :after
)

where python >nul 2>nul
if not errorlevel 1 (
  python launcher.py
  goto :after
)

echo [错误] 未找到 Python。
echo 请安装 Python 3.10+，安装时勾选「Add python.exe to PATH」
echo 下载: https://www.python.org/downloads/
echo.
pause
exit /b 1

:after
echo.
echo 服务已结束。若刚才启动失败，请查看 .run\backend.log 与 .run\frontend.log
pause
