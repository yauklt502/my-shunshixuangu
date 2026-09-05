@echo off
REM Check Python / PATH before launching
setlocal
cd /d "%~dp0"
title Check environment
echo === Environment check ===
echo.
where py 2>nul && echo [OK] py launcher found
where python 2>nul && echo [OK] python found
where python3 2>nul && echo [OK] python3 found
echo.
python --version 2>nul
if errorlevel 1 (
  py -3 --version 2>nul
  if errorlevel 1 (
    echo [FAIL] No working Python on PATH.
    echo Install from https://www.python.org/downloads/windows/
    echo Check: Add python.exe to PATH
  )
) else (
  echo [OK] python --version works
)
echo.
echo If Python is OK, double-click START.cmd to launch.
echo.
pause
