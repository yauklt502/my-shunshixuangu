@echo off
setlocal
echo Stopping KaiPanLa on port 3000...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":3000 .*LISTENING"') do (
  echo Killing PID %%P
  taskkill /F /PID %%P >nul 2>&1
)
echo Done.
timeout /t 2 /nobreak >nul
