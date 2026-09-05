@echo off
chcp 65001 >nul
title 顺势选股
cd /d "%~dp0"

set PYTHONUNBUFFERED=1
where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py
  goto :end
)
where python >nul 2>nul
if not errorlevel 1 (
  python launcher.py
  goto :end
)

echo 未找到 Python。请安装 Python 3.10+，勾选 Add python.exe to PATH
echo https://www.python.org/downloads/
pause
exit /b 1

:end
if errorlevel 1 pause
