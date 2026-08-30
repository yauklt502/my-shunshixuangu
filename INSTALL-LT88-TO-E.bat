@echo off
setlocal
cd /d "%~dp0"

set "SRC=%~dp0e-drive-lt88"
if not exist "%SRC%\index.html" (
  echo ERROR: cannot find e-drive-lt88\index.html
  pause
  exit /b 1
)

set "DEST=E:\LongTou88"
if not exist "E:\" set "DEST=%USERPROFILE%\Desktop\LongTou88"

if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%\index.html" "%DEST%\index.html" >nul
copy /Y "%SRC%\start-server.ps1" "%DEST%\start-server.ps1" >nul
copy /Y "%SRC%\open.bat" "%DEST%\open.bat" >nul

echo.
echo Copied to %DEST%
echo Next time double-click open.bat in that folder.
echo Port 3001 - does not overwrite E:\ShunshiWatch
echo.
cd /d "%DEST%"
call "%DEST%\open.bat"
