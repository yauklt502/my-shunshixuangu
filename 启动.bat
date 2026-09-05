@echo off
cd /d "%~dp0"
title Three Discipline Dashboard
echo Starting...
if not exist "%~dp0start.cmd" (
  echo [ERROR] start.cmd not found. Unzip the FULL package first.
  pause
  exit /b 1
)
call "%~dp0start.cmd"
echo.
echo --- finished ---
pause
