@echo off
setlocal EnableDelayedExpansion
title Shunshi - Deploy to E:

echo.
echo ============================================
echo   Shunshi Trading - Deploy to E:
echo ============================================
echo.

if not exist E:\ (
    echo [ERROR] Drive E: not found.
    echo Please mount drive E: or use deploy.bat for auto drive pick.
    goto FAIL
)

set "TARGET=E:\shunshi-trading"
set "SOURCE=%~dp0"
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

echo Target: %TARGET%
echo Source: %SOURCE%
echo.

if not exist "%TARGET%" mkdir "%TARGET%"

echo [1/5] Copy files...
robocopy "%SOURCE%" "%TARGET%" /E /XD .git .venv __pycache__ .cache data /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
set RC=!ERRORLEVEL!
if !RC! GEQ 8 (
    echo [ERROR] Copy failed, code !RC!
    goto FAIL
)
echo OK

echo [2/5] Find Python...
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo [ERROR] Python not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install.
    goto FAIL
)
%PY% --version
if errorlevel 1 goto FAIL

echo [3/5] Create venv...
cd /d "%TARGET%"
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto FAIL
)

echo [4/5] 安装依赖（国内镜像，请稍候）...
call "%~dp0install_deps.bat"
if errorlevel 1 goto FAIL
echo OK

echo [5/5] Copy start scripts...
copy /Y "%SOURCE%\start.bat" "%TARGET%\start.bat" >nul
copy /Y "%SOURCE%\stop.bat" "%TARGET%\stop.bat" >nul
copy /Y "%SOURCE%\install_deps.bat" "%TARGET%\install_deps.bat" >nul
if exist "%SOURCE%\一键启动.bat" copy /Y "%SOURCE%\一键启动.bat" "%TARGET%\一键启动.bat" >nul

echo.
echo ============================================
echo   DEPLOY SUCCESS
echo ============================================
echo   Folder : %TARGET%
echo   Next   : double-click start.bat
echo   URL    : http://127.0.0.1:8000
echo ============================================
echo.
choice /C YN /M "Start now"
if errorlevel 2 goto OK
if errorlevel 1 start "" "%TARGET%\start.bat"
goto OK

:FAIL
echo.
echo Deploy failed. You can also try:
echo   1. Right-click - Run as administrator
echo   2. Run install.ps1 in PowerShell
echo.
pause
exit /b 1

:OK
pause
exit /b 0
