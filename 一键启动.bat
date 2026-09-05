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
  echo [错误] 未找到 python，请先安装 Python 3.10+
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 npm，请先安装 Node.js 18+
  pause
  exit /b 1
)

echo [1/4] 检查后端虚拟环境...
if not exist "backend\.venv\Scripts\python.exe" (
  echo     首次创建虚拟环境并安装依赖，请稍候...
  python -m venv backend\.venv
  call backend\.venv\Scripts\activate.bat
  python -m pip install -U pip
  pip install -r backend\requirements.txt
) else (
  call backend\.venv\Scripts\activate.bat
  echo     虚拟环境已就绪
)

echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules" (
  echo     首次 npm install，请稍候...
  pushd frontend
  call npm install
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
echo 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   启动完成
echo   页面: http://127.0.0.1:%FRONTEND_PORT%
echo   API : http://127.0.0.1:%BACKEND_PORT%/api/health
echo   日志: %RUN_DIR%
echo ========================================
echo.
echo 已尝试打开浏览器。关闭本窗口不会自动停服务。
echo 如需停止：运行「一键停止.bat」或关掉 SSP-Backend / SSP-Frontend 窗口。
echo.

start "" "http://127.0.0.1:%FRONTEND_PORT%"
pause