@echo off
REM ASCII launcher - avoids Chinese filename / encoding issues on some PCs
cd /d "%~dp0"
title QingXing LongTou Screener
setlocal EnableExtensions

echo ========================================
echo   QingXing LongTou - starting...
echo   Dir: %CD%
echo ========================================
echo.

REM Prefer "py -3" (Windows Python Launcher), then python, then python3
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY where python3 >nul 2>nul && set "PY=python3"

if not defined PY (
  echo [ERROR] Python not found.
  echo 1^) Install Python 3.11/3.12 x64 from https://www.python.org/downloads/
  echo 2^) CHECK "Add python.exe to PATH"
  echo 3^) Reopen this folder and run INSTALL.bat
  echo.
  echo If Microsoft Store pops up, disable "App execution aliases" for python:
  echo   Settings -^> Apps -^> Advanced app settings -^> App execution aliases
  echo   Turn OFF python.exe / python3.exe
  echo.
  pause
  exit /b 1
)

echo Using: %PY%
%PY% -c "import sys; print('Python', sys.version)"
if errorlevel 1 (
  echo [ERROR] Python launcher failed. Disable Store aliases or reinstall Python.
  pause
  exit /b 1
)

echo.
echo Checking dependencies...
%PY% -c "import requests,PIL,dotenv,tkinter" 2>nul
if errorlevel 1 (
  echo Dependencies missing. Running INSTALL.bat ...
  echo.
  call "%~dp0INSTALL.bat"
  if errorlevel 1 (
    echo [ERROR] Install failed.
    pause
    exit /b 1
  )
)

echo.
echo Launching GUI...
echo Log file: "%~dp0start_log.txt"
%PY% "%~dp0run.py" 1>"%~dp0start_log.txt" 2>&1
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo [ERROR] Exit code %EC%. See start_log.txt:
  echo ----------------------------------------
  type "%~dp0start_log.txt"
  echo ----------------------------------------
  pause
  exit /b %EC%
)

REM If GUI closed normally, keep window if user wants to see log
echo.
echo Program exited. Last log:
type "%~dp0start_log.txt"
echo.
pause
endlocal
