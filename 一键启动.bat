@echo off
chcp 65001 >nul
title 顺时选股交易系统

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

if not exist ".venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境。
    echo 请先双击运行「一键部署到E盘.bat」完成部署。
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
set DATA_SOURCE=eastmoney

echo.
echo  ============================================
echo    顺时选股交易系统
echo  ============================================
echo    看板地址 : http://localhost:8000
echo    数据端口 : 东方财富实时
echo    停止服务 : 运行「停止服务.bat」或 Ctrl+C
echo  ============================================
echo.

start "" /min cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
python -m src.main --mode api --port 8000

pause
