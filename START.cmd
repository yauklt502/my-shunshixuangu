@echo off
REM Root launcher - ASCII filename recommended: double-click START.cmd
setlocal EnableExtensions
cd /d "%~dp0"
title XianBiDu Start

echo ========================================
echo   XianBiDu one-click start
echo ========================================
echo Folder: %CD%
echo.

if not exist "%~dp0tsp\start.cmd" (
  echo [ERROR] tsp\start.cmd not found.
  echo Unzip the FULL zip, then open the inner folder:
  echo   my-shunshixuangu-...\START.cmd
  echo.
  pause
  exit /b 1
)

REM Stay open: run start.cmd in this same window
cd /d "%~dp0tsp"
call start.cmd
echo.
echo Launcher finished. Window stays open so you can read errors.
pause
