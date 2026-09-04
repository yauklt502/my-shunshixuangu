@echo off
setlocal
echo Stopping KaiPanLa on ports 3000 / 8790...
for %%PORT in (3000 8790) do (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%%PORT .*LISTENING"') do (
    echo Killing PID %%P ^(port %%PORT^)
    taskkill /F /PID %%P >nul 2>&1
  )
)
echo Done.
timeout /t 2 /nobreak >nul
