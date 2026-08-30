@echo off
cd /d "%~dp0"
echo Starting LongTou 88 board...
echo Do NOT close this window. Closing it stops the board.
echo Browser will open at http://127.0.0.1:3001
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-server.ps1"
echo.
pause
