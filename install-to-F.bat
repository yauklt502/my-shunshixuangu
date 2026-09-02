@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Deploy KaiPanLa to F:\kaipanla

if not exist F:\ (
  echo [ERROR] Drive F: was not found. Plug in / mount the disk, then retry.
  pause
  exit /b 1
)

set "DEST=F:\kaipanla"
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%DEST%" (
  echo [ERROR] Could not create %DEST%
  pause
  exit /b 1
)

echo Copying project to %DEST% ...
robocopy "%CD%" "%DEST%" /E /XD node_modules .git release .vite /XF *.log /NFL /NDL /NJH /NJS /R:2 /W:1
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo [ERROR] Copy failed, robocopy exit %RC%
  pause
  exit /b 1
)

echo.
echo Deployed to %DEST%
echo Starting local server...
echo.
cd /d "%DEST%"
call "%DEST%\start.bat"
