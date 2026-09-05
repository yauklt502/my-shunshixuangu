@echo off
REM Double-click start. Second run onwards: no download, open browser directly.
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title 先比独选股

set "LOG=%CD%\startup.log"
set "TSP_PORT=8765"
if not "%TSP_PORT%"=="" set "TSP_PORT=%TSP_PORT%"
if "%TDX_HOST%"=="" set "TDX_HOST=115.238.90.165:7709"
set "URL=http://127.0.0.1:%TSP_PORT%"
set "VENV_PY=%CD%\.venv\Scripts\python.exe"

echo ========================================
echo   先比独选股 - 一键启动
echo ========================================
echo.

REM ---------- Fast path: already prepared ----------
if exist "%VENV_PY%" (
  "%VENV_PY%" -c "import fastapi,uvicorn,httpx,eltdx" >nul 2>&1
  if not errorlevel 1 (
    echo 环境已就绪，正在打开网页...
    goto :run_server
  )
)

REM ---------- First-time prepare (only once) ----------
echo 首次使用，正在自动准备环境（只需一次，请稍等）...
echo [%DATE% %TIME%] first-time setup > "%LOG%"

set "PYCMD="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1 && set "PYCMD=py -3.12" && goto :got_py
  py -3.11 -c "import sys" >nul 2>&1 && set "PYCMD=py -3.11" && goto :got_py
  py -3 -c "import sys" >nul 2>&1 && set "PYCMD=py -3" && goto :got_py
)
where python >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    echo %%I | findstr /i "WindowsApps\\python.exe" >nul
    if errorlevel 1 (
      set "PYCMD=%%I"
      goto :got_py
    )
  )
)

echo [错误] 未找到 Python。
echo 请安装 Python 3.10+ ：https://www.python.org/downloads/windows/
echo 安装时勾选 Add python.exe to PATH
echo.
pause
exit /b 1

:got_py
echo 使用 Python: %PYCMD%
if not exist "requirements.txt" (
  echo [错误] 缺少 requirements.txt，请解压完整压缩包。
  pause
  exit /b 1
)
if not exist "backend\app.py" (
  echo [错误] 缺少 backend\app.py
  pause
  exit /b 1
)

if not exist "%VENV_PY%" (
  %PYCMD% -m venv .venv >> "%LOG%" 2>&1
  if errorlevel 1 (
    echo [错误] 创建环境失败，详见 startup.log
    type "%LOG%"
    pause
    exit /b 1
  )
)

"%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 (
  echo 安装失败，正在重试一次...
  rmdir /s /q .venv >nul 2>&1
  %PYCMD% -m venv .venv >> "%LOG%" 2>&1
  set "VENV_PY=%CD%\.venv\Scripts\python.exe"
  "%VENV_PY%" -m pip install -U pip >> "%LOG%" 2>&1
  "%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
)
if errorlevel 1 (
  echo [错误] 依赖安装失败。
  powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 50"
  pause
  exit /b 1
)

"%VENV_PY%" -c "import fastapi,uvicorn,httpx,eltdx" >nul 2>&1
if errorlevel 1 (
  echo [错误] 依赖校验失败，请删除 tsp\.venv 后再试。
  pause
  exit /b 1
)

echo 准备完成。以后双击将直接打开，不再下载。
echo.

:run_server
set "PYTHONPATH=%CD%"
set "TDX_HOST=%TDX_HOST%"

REM Open browser as soon as service is up
start "" cmd /c "for /l %%i in (1,1,30) do (ping -n 2 127.0.0.1 >nul & curl -sf %URL%/api/health >nul 2>&1 && start %URL% && exit /b 0) & start %URL%"

echo 正在启动，浏览器稍后自动打开：
echo   %URL%
echo.
echo 请保持本窗口打开。关闭窗口 = 退出软件。
echo ----------------------------------------

"%VENV_PY%" -m uvicorn backend.app:app --host 127.0.0.1 --port %TSP_PORT%
set "ERR=!ERRORLEVEL!"
if not "!ERR!"=="0" (
  echo.
  echo 启动失败 exit=!ERR!
  if exist "%LOG%" powershell -NoProfile -Command "Get-Content -LiteralPath '%LOG%' -Tail 40"
  pause
)
exit /b %ERR%
