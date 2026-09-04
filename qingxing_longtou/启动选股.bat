@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 清醒龙头战法选股

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 python，请先运行「安装依赖.bat」或安装 Python。
  pause
  exit /b 1
)

python -c "import requests,PIL,dotenv" 2>nul
if errorlevel 1 (
  echo 依赖未安装，正在自动执行安装...
  call "%~dp0安装依赖.bat"
)

python "%~dp0run.py"
if errorlevel 1 (
  echo.
  echo 程序异常退出。若提示无显示/截屏相关错误，请确认在桌面图形界面运行。
  pause
)
