@echo off
REM 双击即可。第二次起不再下载依赖。
cd /d "%~dp0"
if exist "tsp\start.cmd" (
  cd /d "%~dp0tsp"
  call start.cmd
) else if exist "start.cmd" (
  call start.cmd
) else (
  echo [错误] 找不到启动文件，请解压完整压缩包后再试。
  pause
)
