@echo off
setlocal
title Shunshi - Start

set "APP=%~dp0"
cd /d "%APP%"

if not exist "%APP%deploy.bat" (
    echo [ERROR] deploy.bat not found in: %APP%
    pause
    exit /b 1
)

call "%APP%deploy.bat"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" pause
exit /b %ERR%
