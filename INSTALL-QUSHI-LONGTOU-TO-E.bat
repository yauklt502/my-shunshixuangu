@echo off
setlocal
cd /d "%~dp0"

set "SRC=%~dp0e-drive-qslt"
if not exist "%SRC%\index.html" (
  echo ERROR: cannot find e-drive-qslt\index.html
  pause
  exit /b 1
)

set "DEST=E:\QuShiLongTou"
if not exist "E:\" set "DEST=%USERPROFILE%\Desktop\QuShiLongTou"

if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%\index.html" "%DEST%\index.html" >nul
copy /Y "%SRC%\start-server.ps1" "%DEST%\start-server.ps1" >nul
copy /Y "%SRC%\open.bat" "%DEST%\open.bat" >nul

echo.
echo Copied to %DEST%
echo Port 3002 - parallel to ShunshiWatch and LongTou88
echo.
cd /d "%DEST%"
call "%DEST%\open.bat"
