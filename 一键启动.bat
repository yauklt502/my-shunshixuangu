@echo off
REM Chinese-named shortcut -> same as START.cmd, always pause
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "%~dp0tsp\start.cmd" (
  echo [ERROR] tsp\start.cmd not found. Unzip full package.
  pause
  exit /b 1
)
cd /d "%~dp0tsp"
call start.cmd
pause
