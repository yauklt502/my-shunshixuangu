@echo off
cd /d "%~dp0"
if exist "tsp\start.cmd" (
  cd /d "%~dp0tsp"
  call start.cmd
) else if exist "start.cmd" (
  call start.cmd
) else (
  echo [ERROR] start.cmd not found. Unzip the FULL package.
  pause
)
pause
