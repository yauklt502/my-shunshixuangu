@echo off
REM Root Chinese-named launcher -> keep window open
setlocal
cd /d "%~dp0"
if exist "tsp\start.cmd" (
  cmd /k "cd /d ""%~dp0tsp"" && call start.cmd"
) else (
  echo [ERROR] tsp\start.cmd not found. Unzip the full package first.
  pause
)
