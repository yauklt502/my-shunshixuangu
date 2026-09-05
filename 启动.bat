@echo off
REM Double-click this. Same idea as TSP: keep window open, show errors.
setlocal EnableExtensions
cd /d "%~dp0"
title Three Discipline Dashboard

echo ========================================
echo   Three Discipline Dashboard
echo   One-click start
echo ========================================
echo Folder: %CD%
echo.

if not exist "%~dp0start.cmd" (
  echo [ERROR] start.cmd not found.
  echo Please UNZIP the full package first, then open the inner folder.
  echo.
  pause
  exit /b 1
)

REM Prefer Python venv [1/4]..[4/4]; if no Python, try Node zero-install.
set "HAS_PY="
where py >nul 2>&1
if not errorlevel 1 set "HAS_PY=1"
if not defined HAS_PY (
  where python >nul 2>&1
  if not errorlevel 1 set "HAS_PY=1"
)

if defined HAS_PY (
  call "%~dp0start.cmd"
  goto :done
)

where node >nul 2>&1
if not errorlevel 1 (
  echo [INFO] Python not found. Falling back to Node.js ...
  echo.
  call "%~dp0start-node.cmd"
  goto :done
)

echo [ERROR] Neither Python nor Node.js found.
echo.
echo Install ONE of:
echo   1) Python 3.10+  https://www.python.org/downloads/windows/
echo      IMPORTANT: check "Add python.exe to PATH"
echo   2) Node.js LTS   https://nodejs.org/
echo.
echo Then close this window and double-click 启动.bat again.
echo.
pause
exit /b 1

:done
echo.
echo Launcher finished. Window stays open so you can read errors.
pause
endlocal
