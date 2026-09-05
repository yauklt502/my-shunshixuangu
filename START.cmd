@echo off
cd /d "%~dp0"
if exist "tsp\start.cmd" (
  cd /d "%~dp0tsp"
  call start.cmd
) else (
  echo [错误] 找不到 tsp\start.cmd，请解压完整压缩包。
  pause
)
