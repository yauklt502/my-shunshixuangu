@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   顺势选股 · 龙头确认 本地启动
echo ========================================

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python，请先安装 Python 3.10+ 并勾选 Add to PATH
  echo 下载: https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 创建虚拟环境...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
)

echo [2/3] 安装/更新依赖...
".venv\Scripts\python.exe" -m pip install -U pip -q
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [提示] 默认源失败，尝试清华镜像...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)

set PYTHONPATH=%cd%
set PORT=8765

echo [3/3] 启动服务 http://127.0.0.1:%PORT%
echo 浏览器打开上述地址；按 Ctrl+C 可停止
echo.
".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port %PORT%
pause
