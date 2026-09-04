@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Shunshi Leader Confirm - Local Start
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ and check "Add to PATH".
  echo Download: https://www.python.org/downloads/
  goto :FAIL
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    goto :FAIL
  )
) else (
  echo [1/4] Virtual environment OK
)

echo [2/4] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -U pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [WARN] Default PyPI failed, trying Tsinghua mirror...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo [ERROR] pip install failed
    goto :FAIL
  )
)
".venv\Scripts\python.exe" -m pip install tzdata >nul

set "PYTHONPATH=%CD%"
set "PORT=8654"

echo [3/4] Preflight import check...
".venv\Scripts\python.exe" -c "import server; print('import ok')"
if errorlevel 1 (
  echo [ERROR] Cannot import server.py
  echo Make sure you downloaded the LATEST zip from GitHub.
  goto :FAIL
)

echo [4/4] Starting server...
echo.
echo ========================================
echo  Open browser: http://127.0.0.1:%PORT%
echo  Keep this window OPEN while using.
echo  Press Ctrl+C to stop the server.
echo ========================================
echo.

".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port %PORT%
set "ERR=%ERRORLEVEL%"

echo.
echo ========================================
if not "%ERR%"=="0" (
  echo  SERVER EXITED WITH ERROR code %ERR%
  echo  Read the traceback ABOVE.
  echo  Common fix: re-download latest zip, then run start.bat again.
) else (
  echo  Server stopped normally.
)
echo  Browser was: http://127.0.0.1:%PORT%
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
goto :EOF

:FAIL
echo.
echo ========================================
echo  START FAILED - window stays for reading
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
endlocal
exit /b 1
