@echo off
setlocal
cd /d "%~dp0"

set "SRC=%~dp0e-drive"
if not exist "%SRC%\index.html" (
  echo ERROR: cannot find e-drive\index.html
  echo Unzip the whole folder first, then double-click INSTALL-TO-E.bat
  pause
  exit /b 1
)

set "DEST=E:\ShunshiWatch"
if not exist "E:\" set "DEST=%USERPROFILE%\Desktop\ShunshiWatch"

if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%SRC%\index.html" "%DEST%\index.html" >nul
copy /Y "%SRC%\start-server.ps1" "%DEST%\start-server.ps1" >nul
copy /Y "%SRC%\open.bat" "%DEST%\open.bat" >nul
if exist "%SRC%\fuyao-key.txt" copy /Y "%SRC%\fuyao-key.txt" "%DEST%\fuyao-key.txt" >nul

echo.
echo Copied to %DEST%
echo Next time just double-click open.bat in that folder.
echo Keep the black window open.
echo.
cd /d "%DEST%"
call "%DEST%\open.bat"
