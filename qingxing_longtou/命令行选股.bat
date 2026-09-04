@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 清醒龙头战法 - CLI
where python >nul 2>nul || (echo 未找到 python & pause & exit /b 1)
python "%~dp0cli.py" --source auto --limit 30
echo.
pause
