@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在打开龙头盯盘，请稍等几秒...
echo 这个黑窗口不要关，关掉就等于关掉盯盘。
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-server.ps1"
if errorlevel 1 (
  echo 打开失败。可再双击一次试试。
  pause
)
