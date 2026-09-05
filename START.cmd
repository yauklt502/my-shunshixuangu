@echo off
REM Root launcher - double-click this
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
  echo Unzip the FULL zip, then open the inner folder and run START.cmd
  echo.
  pause
  exit /b 1
)

cd /d "%~dp0tsp"
call start.cmd
echo.
echo Launcher finished. Window stays open so you can read errors.
pause
