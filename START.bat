@echo off
cd /d "%~dp0"
title Three Discipline Dashboard
echo ========================================
echo   Three Discipline Dashboard
echo ========================================
echo Folder: %CD%
echo.

if not exist "%~dp0start.cmd" (
  echo [ERROR] start.cmd missing. Unzip the FULL package first.
  echo.
  pause
  exit /b 1
)

call "%~dp0start.cmd"
echo.
echo --- finished ---
echo If the page did not open, read errors above.
echo Or double-click start-node.cmd if you have Node.js.
echo.
pause
