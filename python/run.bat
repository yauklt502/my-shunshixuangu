@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python --version >nul 2>&1 || (
  echo 未找到 python，请先安装 Python 3.10+ 并勾选 Add to PATH
  pause
  exit /b 1
)
pip install -q -r requirements.txt
python python\leader_watch.py %*
pause
