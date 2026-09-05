@echo off
cd /d "%~dp0"
title Three Discipline Dashboard
echo ========================================
echo   Three Discipline Dashboard
echo ========================================
echo Folder: %CD%
echo.
if not exist "%~dp0start.cmd" (
  echo [ERROR] start.cmd missing. Unzip FULL package.
  pause
  exit /b 1
)
call "%~dp0start.cmd"
echo.
echo --- finished ---
pause
