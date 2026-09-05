@echo off
cd /d "%~dp0"
if /I not "%~1"=="KEEP" (
  start "SSP-STOP" cmd /k call "%~f0" KEEP
  exit /b 0
)
echo Stopping port 5173 ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /F /PID %%a
echo Done.
pause
