@echo off
chcp 65001 >nul
title 顺势选股 Role Ladder 一键启动
cd /d "%~dp0"

set BACKEND_PORT=8010
set FRONTEND_PORT=5173
set RUN_DIR=%~dp0.run
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"

echo.
echo ========================================
echo   顺势选股 · Role Ladder 一键启动
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo [错误] 未找到 Python。请安装 Python 3.10+ 并勾选「Add to PATH」
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
  )
  set PY=py -3
) else (
  set PY=python
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 npm。请安装 Node.js 18+
  echo 下载: https://nodejs.org/
  pause
  exit /b 1
)

echo [0/4] 清理旧进程（如有）...
call "%~dp0一键停止.bat" nopause >nul 2>nul

echo [1/4] 检查后端虚拟环境...
if not exist "backend\.venv\Scripts\python.exe" (
  echo     首次创建虚拟环境并安装依赖，请稍候...
  %PY% -m venv backend\.venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
  )
  call backend\.venv\Scripts\activate.bat
  python -m pip install -U pip
  pip install -r backend\requirements.txt
  if errorlevel 1 (
    echo [错误] 后端依赖安装失败
    pause
    exit /b 1
  )
) else (
  call backend\.venv\Scripts\activate.bat
  echo     虚拟环境已就绪
)

echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules\vite" (
  echo     首次 npm install，请稍候...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    echo [错误] npm install 失败
    pause
    exit /b 1
  )
  popd
) else (
  echo     前端依赖已就绪
)

echo [3/4] 启动后端 http://127.0.0.1:%BACKEND_PORT%
set PYTHONPATH=%~dp0backend
start "SSP-Backend" /min cmd /c "cd /d ""%~dp0backend"" && set PYTHONPATH=%~dp0backend && ""%~dp0backend\.venv\Scripts\uvicorn.exe"" app.main:app --host 0.0.0.0 --port %BACKEND_PORT% > ""%RUN_DIR%\backend.log"" 2>&1"

echo [4/4] 启动前端 http://127.0.0.1:%FRONTEND_PORT%
start "SSP-Frontend" /min cmd /c "cd /d ""%~dp0frontend"" && npm run dev -- --host 0.0.0.0 --port %FRONTEND_PORT% > ""%RUN_DIR%\frontend.log"" 2>&1"

echo.
echo 等待服务就绪（最多约 90 秒）...
set READY=0
for /L %%i in (1,1,90) do (
  powershell -NoProfile -Command "try { $a=(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%BACKEND_PORT%/api/health -TimeoutSec 1).StatusCode; $b=(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:%FRONTEND_PORT%/ -TimeoutSec 1).StatusCode; if($a -eq 200 -and $b -eq 200){exit 0} else {exit 1} } catch { exit 1 }" >nul 2>nul
  if not errorlevel 1 (
    set READY=1
    goto :ready
  )
  timeout /t 1 /nobreak >nul
)

:ready
if "%READY%"=="0" (
  echo.
  echo [警告] 等待超时。请查看日志：
  echo   %RUN_DIR%\backend.log
  echo   %RUN_DIR%\frontend.log
  echo 仍尝试打开浏览器...
) else (
  echo 前后端均已就绪。
)

echo.
echo ========================================
echo   启动完成
echo   页面: http://127.0.0.1:%FRONTEND_PORT%
echo   API : http://127.0.0.1:%BACKEND_PORT%/api/health
echo   日志: %RUN_DIR%
echo ========================================
echo.
echo 关闭本窗口不会自动停服务。
echo 停止请双击「一键停止.bat」
echo.

start "" "http://127.0.0.1:%FRONTEND_PORT%"
pause
